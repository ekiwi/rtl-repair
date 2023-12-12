// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::testbench::Testbench;
use easy_smt as smt;
use libpatron::ir::*;
use libpatron::mc::*;

use crate::repair::*;

pub fn basic_repair(
    ctx: &mut Context,
    sys: &TransitionSystem,
    synth_vars: &RepairVars,
    sim: &impl Simulator,
    tb: &Testbench,
    conf: &RepairConfig,
    change_count_ref: ExprRef,
) -> Result<Option<Vec<RepairAssignment>>> {
    let mut smt_ctx = create_smt_ctx(&conf.solver, conf.dump_file.as_deref())?;

    // start encoding
    let mut enc = UnrollSmtEncoding::new(ctx, sys, true);
    enc.define_header(&mut smt_ctx)?;
    enc.init(ctx, &mut smt_ctx)?;

    // constrain starting state to that from the simulator
    constrain_starting_state(ctx, sys, synth_vars, sim, &enc, &mut smt_ctx)?;

    let start_unroll = std::time::Instant::now();
    // unroll system and constrain inputs and outputs
    for _ in 0..(tb.step_count() - 1) {
        enc.unroll(ctx, &mut smt_ctx)?;
    }
    if conf.verbose {
        println!(
            "Took {:?} to unroll",
            std::time::Instant::now() - start_unroll
        );
    }

    let start_apply_const = std::time::Instant::now();
    tb.apply_constraints(ctx, &mut smt_ctx, &enc)?;
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
        smt::Response::Unsat | smt::Response::Unknown => return Ok(None),
        smt::Response::Sat => {} // OK, continue
    }

    // find a minimal repair
    let min_num_changes =
        minimize_changes(ctx, &mut smt_ctx, &conf.solver, change_count_ref, &enc)?;
    if conf.verbose {
        println!("Found a minimal solution with {min_num_changes} changes.")
    }

    let solution = synth_vars.read_assignment(ctx, &mut smt_ctx, &enc);
    check_assuming_end(&mut smt_ctx, &conf.solver)?;
    Ok(Some(vec![solution]))
}
