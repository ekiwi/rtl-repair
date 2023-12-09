// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
mod basic;
mod repair;
mod testbench;

use crate::basic::{basic_repair, BasicConfig};
use crate::repair::{add_change_count, RepairAssignment, RepairVars};
use crate::testbench::*;
use clap::{Parser, ValueEnum};
use libpatron::ir::SerializableIrNode;
use libpatron::mc::{Simulator, SmtSolverCmd, BITWUZLA_CMD};
use libpatron::sim::interpreter::InitKind;
use libpatron::*;
use serde_json::json;

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
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
pub enum Solver {
    Bitwuzla,
    Yices2,
}

pub const YICES2_CMD: SmtSolverCmd = SmtSolverCmd {
    name: "yices-smt2",
    args: &["--incremental"],
    supports_uf: false, // actually true, but ignoring for now
};

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

    let mut sim = sim::interpreter::Interpreter::new(&ctx, &sys);

    // load testbench
    let mut tb = Testbench::load(&ctx, &sys, &args.testbench, args.verbose)
        .expect("Failed to load testbench.");

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
    // remember the starting state
    let start_state = sim.take_snapshot();

    // run testbench once to see if we can detect a bug
    let res = tb.run(
        &mut sim,
        &RunConfig {
            stop: StopAt::FirstFail,
        },
        args.verbose,
    );

    // early exit in case we do not see any bug
    // (there could still be a bug in the original Verilog that was masked by the synthesis)
    if res.is_success() {
        print_no_repair();
        return;
    }

    // reset the simulator state
    sim.restore_snapshot(start_state);

    // call to the synthesizer
    let start_synth = std::time::Instant::now();
    let repair = if args.incremental {
        todo!("implement incremental synthesizer")
    } else {
        let conf = BasicConfig {
            solver: args.solver,
            verbose: args.verbose,
            dump_file: Some("basic.smt".to_string()),
        };
        basic_repair(&ctx, &sys, &synth_vars, &sim, &tb, &conf, change_count_ref)
            .expect("failed to execute basic synthesizer")
    };
    let synth_duration = std::time::Instant::now() - start_synth;
    if args.verbose {
        println!("Synthesizer took {synth_duration:?}");
    }

    // print status
    let (status, solutions) = match repair {
        None => ("cannot-repair", json!([])),
        Some(assignments) => {
            let mut res = Vec::with_capacity(assignments.len());
            for aa in assignments.iter() {
                let assignment_json = synth_vars.to_json(&ctx, aa);
                res.push(json!({"assignment": assignment_json}));
            }
            ("success", json!(res))
        }
    };

    let res = json!({
        "status": status,
        "solver-time": 0,
        "past-k": 0,
        "future-k": 0,
        "solutions": solutions,
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
