// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::repair::{RepairAssignment, RepairVars, CHANGE_COUNT_WIDTH};
use crate::testbench::Testbench;
use crate::Solver;
use easy_smt as smt;
use easy_smt::Response;
use libpatron::ir::*;
use libpatron::mc::{Simulator, SmtSolverCmd, TransitionSystemEncoding, UnrollSmtEncoding};
use libpatron::sim::interpreter::ValueRef;

type Result<T> = std::io::Result<T>;

pub struct BasicConfig {
    pub solver: Solver,
    pub verbose: bool,
    pub dump_file: Option<String>,
}

pub fn basic_repair(
    ctx: &Context,
    sys: &TransitionSystem,
    synth_vars: &RepairVars,
    sim: &impl Simulator,
    tb: &Testbench,
    conf: &BasicConfig,
    change_count_ref: ExprRef,
) -> Result<Option<Vec<RepairAssignment>>> {
    let mut smt_ctx = create_smt_ctx(&conf.solver, conf.dump_file.as_deref())?;

    // start encoding
    let mut enc = UnrollSmtEncoding::new(ctx, sys, true);
    enc.define_header(&mut smt_ctx)?;
    enc.init(&mut smt_ctx)?;

    // constrain starting state to that from the simulator
    constrain_starting_state(sys, synth_vars, sim, &enc, &mut smt_ctx)?;

    let start_unroll = std::time::Instant::now();
    // unroll system and constrain inputs and outputs
    for _ in 0..(tb.step_count() - 1) {
        enc.unroll(&mut smt_ctx)?;
    }
    if conf.verbose {
        println!(
            "Took {:?} to unroll",
            std::time::Instant::now() - start_unroll
        );
    }

    let start_apply_const = std::time::Instant::now();
    tb.apply_constraints(&mut smt_ctx, &enc)?;
    if conf.verbose {
        println!(
            "Took {:?} to apply constraints",
            std::time::Instant::now() - start_apply_const
        );
    }

    // check to see if a solution exists
    let start_check = std::time::Instant::now();
    let r = smt_ctx.check()?;
    let check_duration = std::time::Instant::now() - start_check;
    if conf.verbose {
        println!("Check-Sat took {check_duration:?}");
    }
    match r {
        // cannot find a repair
        Response::Unsat | Response::Unknown => return Ok(None),
        Response::Sat => {} // OK, continue
    }

    // find a minimal repair
    let min_num_changes = minimize_changes(&mut smt_ctx, change_count_ref, &enc)?;
    if conf.verbose {
        println!("Found a minimal solution with {min_num_changes} changes.")
    }

    let solution = synth_vars.read_assignment(&mut smt_ctx, &enc);
    Ok(Some(vec![solution]))
}

fn minimize_changes(
    smt_ctx: &mut smt::Context,
    change_count_ref: ExprRef,
    enc: &impl TransitionSystemEncoding,
) -> Result<u32> {
    let mut num_changes = 1u32;
    let change_count_expr = enc.get_at(smt_ctx, change_count_ref, 0);
    loop {
        let constraint = smt_ctx.eq(
            change_count_expr,
            smt_ctx.binary(CHANGE_COUNT_WIDTH as usize, num_changes),
        );
        match smt_ctx.check_assuming([constraint])? {
            Response::Sat => {
                // found a solution
                return Ok(num_changes);
            }
            Response::Unsat => {}
            Response::Unknown => panic!("SMT solver returned unknown!"),
        }
        num_changes += 1;
    }
}

fn constrain_starting_state(
    sys: &TransitionSystem,
    synth_vars: &RepairVars,
    sim: &impl Simulator,
    enc: &impl TransitionSystemEncoding,
    smt_ctx: &mut smt::Context,
) -> Result<()> {
    for state in sys
        .states()
        .filter(|s| s.init.is_none() && !synth_vars.is_repair_var(s.symbol))
    {
        let value = sim.get(state.symbol).unwrap();
        let value_expr = value_to_smt_expr(smt_ctx, value);
        let symbol = enc.get_at(smt_ctx, state.symbol, 0);
        smt_ctx.assert(smt_ctx.eq(symbol, value_expr))?;
    }
    Ok(())
}

fn value_to_smt_expr(smt_ctx: &mut smt::Context, value: ValueRef) -> smt::SExpr {
    // currently this will only work for scalar values
    let bits = value.to_bit_string();
    bit_string_to_smt(smt_ctx, &bits)
}

pub fn bit_string_to_smt(smt_ctx: &mut smt::Context, bits: &str) -> smt::SExpr {
    match bits {
        "0" => smt_ctx.false_(),
        "1" => smt_ctx.true_(),
        other => smt_ctx.atom(format!("#b{}", other)),
    }
}

fn create_smt_ctx(solver: &Solver, dump_file: Option<&str>) -> Result<smt::Context> {
    let cmd = solver.cmd();
    let replay_file = if let Some(filename) = dump_file {
        Some(std::fs::File::create(filename)?)
    } else {
        None
    };
    let mut smt_ctx = smt::ContextBuilder::new()
        .solver(cmd.name, cmd.args)
        .replay_file(replay_file)
        .build()?;
    set_logic(&mut smt_ctx, &cmd)?;
    Ok(smt_ctx)
}

/// sets the correct logic depending on the solver we are using
fn set_logic(smt_ctx: &mut smt::Context, cmd: &SmtSolverCmd) -> Result<()> {
    // z3 only supports the non-standard as-const array syntax when the logic is set to ALL
    let logic = if cmd.name == "z3" {
        "ALL"
    } else if cmd.supports_uf {
        "QF_AUFBV"
    } else {
        "QF_ABV"
    };
    smt_ctx.set_logic(logic)
}
