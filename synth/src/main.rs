// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
mod basic;
mod incremental;
mod repair;
mod testbench;

use crate::basic::basic_repair;
use crate::incremental::{IncrementalConf, IncrementalRepair};
use crate::repair::{add_change_count, RepairConfig, RepairContext, RepairVars};
use crate::testbench::*;
use clap::{arg, Parser, ValueEnum};
use libpatron::ir::{replace_anonymous_inputs_with_zero, simplify_expressions, SerializableIrNode};
use libpatron::mc::{Simulator, SmtSolverCmd, BITWUZLA_CMD, YICES2_CMD};
use libpatron::sim::interpreter::InitKind;
use libpatron::*;
use serde_json::json;
use std::collections::HashMap;

#[derive(Parser, Debug)]
#[command(name = "synth")]
#[command(author = "Kevin Laeufer <laeufer@berkeley.edu>")]
#[command(version)]
#[command(about = "Generates repair solutions.", long_about = None)]
struct Args {
    #[arg(
        long,
        required = true,
        help = "the design to be repaired with the template instantiated in btor format"
    )]
    design: String,
    #[arg(long, required = true, help = "the testbench in CSV format")]
    testbench: String,
    #[arg(long, help = "output debug messages")]
    verbose: bool,
    #[arg(long, help = "trace signals during simulation")]
    trace_sim: bool,
    #[arg(long, help = "use the incremental instead of the basic synthesizer")]
    incremental: bool,
    #[arg(
        long,
        value_enum,
        default_value = "bitwuzla",
        help = "the SMT solver to use"
    )]
    solver: Solver,
    #[arg(
        long,
        value_enum,
        default_value = "zero",
        help = "initialization strategy"
    )]
    init: Init,
    #[arg(
        long,
        default_value_t = 2u64,
        help = "step size for past-k in incremental solver"
    )]
    pask_k_step_size: u64,
    #[arg(
        long,
        default_value_t = 32u64,
        help = "the maximum repair window size before the incremental solver gives up"
    )]
    max_repair_window_size: u64,
    #[arg(long, help = "file to write all SMT commands to")]
    smt_dump: Option<String>,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
pub enum Solver {
    Bitwuzla,
    Yices2,
}

impl Solver {
    pub fn cmd(&self) -> SmtSolverCmd {
        match self {
            Solver::Bitwuzla => BITWUZLA_CMD,
            Solver::Yices2 => YICES2_CMD,
        }
    }
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
pub enum Init {
    Zero,
    Random,
    Any, // not really supported
}

fn main() {
    let args = Args::parse();

    // load system
    let (mut ctx, mut sys) = btor2::parse_file(&args.design).expect("Failed to load btor2 file!");

    // simplify system
    replace_anonymous_inputs_with_zero(&mut ctx, &mut sys);
    simplify_expressions(&mut ctx, &mut sys);

    // analyze system
    let synth_vars = RepairVars::from_sys(&ctx, &sys);
    if args.verbose {
        println!("Number of change vars: {}", synth_vars.change.len());
        println!("Number of free vars:   {}", synth_vars.free.len());
    }

    // add a change count to the system
    let change_count_ref = add_change_count(&mut ctx, &mut sys, &synth_vars.change);

    // print system
    if args.verbose {
        println!("Loaded: {}", sys.name);
        println!("{}", sys.serialize_to_str(&ctx));
    }

    let sim_ctx = ctx.clone();
    let mut sim = sim::interpreter::Interpreter::new(&sim_ctx, &sys);

    // load testbench
    let mut tb = Testbench::load(&ctx, &sys, &args.testbench, args.verbose, args.trace_sim)
        .expect("Failed to load testbench.");

    if tb.has_missing_outputs() {
        println!(
            "WARN: testbench is missing output! We do not have a way to check for correctness."
        );
        print_cannot_repair();
        return;
    }

    // init free variables
    match args.init {
        Init::Zero => {
            sim.init(InitKind::Zero);
            tb.define_inputs(InitKind::Zero);
        }
        Init::Random => {
            sim.init(InitKind::Random(0));
            tb.define_inputs(InitKind::Random(1));
        }
        Init::Any => {
            println!(
                "WARN: any init is not actually supported! Random init will be performed instead!"
            );
            sim.init(InitKind::Random(0));
            tb.define_inputs(InitKind::Random(1));
        }
    }
    // set all synthesis variables to zero
    synth_vars.clear_in_sim(&mut sim);

    // remember the starting state
    let start_state = sim.take_snapshot();

    // run testbench once to see if we can detect a bug
    let start_first_test = std::time::Instant::now();
    let res = tb.run(
        &mut sim,
        &RunConfig {
            start: 0,
            stop: StopAt::first_fail(),
        },
        args.verbose,
    );
    if args.verbose {
        let steps = res.first_fail_at.unwrap_or(tb.step_count());
        println!(
            "Executed {steps} steps in {:?}",
            std::time::Instant::now() - start_first_test
        )
    }

    // early exit in case we do not see any bug
    // (there could still be a bug in the original Verilog that was masked by the synthesis)
    if res.is_success() {
        if args.verbose {
            println!("Design seems to work.");
        }
        print_no_repair();
        return;
    }

    // early exit if there is a bug, but no synthesis variables to change the design

    if synth_vars.change.is_empty() {
        if args.verbose {
            println!("No changes possible.");
        }
        print_cannot_repair();
        return;
    }

    let error_snapshot = if args.incremental {
        Some(sim.take_snapshot())
    } else {
        None
    };

    // reset the simulator state
    sim.restore_snapshot(start_state);

    // call to the synthesizer
    let start_synth = std::time::Instant::now();
    let repair_conf = RepairConfig {
        solver: args.solver.cmd(),
        verbose: args.verbose,
        dump_file: args.smt_dump.clone(),
    };
    let repair_ctx = RepairContext {
        ctx: &mut ctx,
        sys: &sys,
        sim: &mut sim,
        synth_vars: &synth_vars,
        tb: &tb,
        conf: repair_conf.clone(),
        change_count_ref,
    };
    let repair = if args.incremental {
        let incremental_conf = IncrementalConf {
            fail_at: res.first_fail_at.unwrap(),
            pask_k_step_size: args.pask_k_step_size,
            max_repair_window_size: args.max_repair_window_size,
            max_solutions: 1,
        };
        let mut snapshots = HashMap::new();
        snapshots.insert(0, start_state);
        snapshots.insert(res.first_fail_at.unwrap(), error_snapshot.unwrap());
        let mut rep = IncrementalRepair::new(repair_ctx, &incremental_conf, snapshots)
            .expect("failed to create incremental solver");
        rep.run()
            .expect("failed to execute incremental synthesizer")
    } else {
        basic_repair(repair_ctx).expect("failed to execute basic synthesizer")
    };
    let synth_duration = std::time::Instant::now() - start_synth;
    if args.verbose {
        println!("Synthesizer took {synth_duration:?}");
    }

    // print status
    let solutions = match repair {
        None => {
            print_cannot_repair();
            return;
        }
        Some(assignments) => {
            let mut res = Vec::with_capacity(assignments.len());
            for aa in assignments.iter() {
                let assignment_json = synth_vars.to_json(&ctx, aa);
                res.push(json!({"assignment": assignment_json}));
            }
            json!(res)
        }
    };

    let res = json!({
        "status": "success",
        "solver-time": 0,
        "past-k": 0,
        "future-k": 0,
        "solutions": solutions,
    });

    print_result(&res);
}

fn print_cannot_repair() {
    let res = json!({
        "status": "cannot-repair",
        "solver-time": 0,
        "past-k": 0,
        "future-k": 0,
        "solutions": [],
    });

    print_result(&res);
}

fn print_no_repair() {
    let res = json!({
        "status": "no-repair",
        "solver-time": 0,
        "past-k": 0,
        "future-k": 0,
        "solutions": [],
    });

    print_result(&res);
}

fn print_result(res: &serde_json::Value) {
    println!("== RESULT =="); // needle to find the JSON output
    let j = serde_json::to_string(&res).unwrap();
    println!("{}", j);
}
