// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use easy_smt as smt;
use libpatron::mc::*;

use crate::repair::*;

pub fn basic_repair<S: Simulator>(
    mut rctx: RepairContext<S>,
) -> Result<Option<Vec<RepairAssignment>>> {
    let mut smt_ctx = create_smt_ctx(&rctx.conf.solver, rctx.conf.dump_file.as_deref())?;

    let repairs = generate_repairs(&mut rctx, &mut smt_ctx)?;
    if repairs.is_empty() {
        Ok(None) // no solution
    } else {
        Ok(Some(repairs))
    }
}

fn generate_repairs<S: Simulator>(
    rctx: &mut RepairContext<S>,
    smt_ctx: &mut smt::Context,
) -> Result<Vec<RepairAssignment>> {
    // start encoding
    let mut enc = UnrollSmtEncoding::new(rctx.ctx, rctx.sys, true);
    enc.define_header(smt_ctx)?;
    enc.init(rctx.ctx, smt_ctx)?;

    // constrain starting state to that from the simulator
    constrain_starting_state(rctx.ctx, rctx.sys, rctx.synth_vars, rctx.sim, &enc, smt_ctx)?;

    let start_unroll = std::time::Instant::now();
    // unroll system and constrain inputs and outputs
    for _ in 0..(rctx.tb.step_count() - 1) {
        enc.unroll(rctx.ctx, smt_ctx)?;
    }
    if rctx.conf.verbose {
        println!(
            "Took {:?} to unroll",
            std::time::Instant::now() - start_unroll
        );
    }

    let start_apply_const = std::time::Instant::now();
    rctx.tb.apply_constraints(rctx.ctx, smt_ctx, &enc)?;
    if rctx.conf.verbose {
        println!(
            "Took {:?} to apply constraints",
            std::time::Instant::now() - start_apply_const
        );
    }

    // check to see if a solution exists
    let start_check = std::time::Instant::now();
    let r = smt_ctx.check()?;
    let check_duration = std::time::Instant::now() - start_check;
    if rctx.conf.verbose {
        println!("Check-Sat took {check_duration:?}");
    }
    match r {
        // cannot find a repair
        smt::Response::Unsat | smt::Response::Unknown => return Ok(vec![]),
        smt::Response::Sat => {} // OK, continue
    }

    // find a minimal repair
    let min_num_changes = minimize_changes(
        rctx.ctx,
        smt_ctx,
        &rctx.conf.solver,
        rctx.change_count_ref,
        &enc,
    )?;
    if rctx.conf.verbose {
        println!("Found a minimal solution with {min_num_changes} changes.")
    }

    let solution = rctx.synth_vars.read_assignment(rctx.ctx, smt_ctx, &enc);
    check_assuming_end(smt_ctx, &rctx.conf.solver)?;
    Ok(vec![solution])
}
