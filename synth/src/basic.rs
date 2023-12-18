// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use easy_smt as smt;
use libpatron::mc::*;

use crate::repair::*;
use crate::testbench::StepInt;

pub fn basic_repair<S: Simulator, E: TransitionSystemEncoding>(
    mut rctx: RepairContext<S, E>,
) -> Result<Option<Vec<RepairAssignment>>> {
    let res = generate_minimal_repair(&mut rctx, 0, None)?;
    match res {
        None => Ok(None), // no solution
        Some((repair, _)) => Ok(Some(vec![repair])),
    }
}

pub fn generate_minimal_repair<S: Simulator, E: TransitionSystemEncoding>(
    rctx: &mut RepairContext<S, E>,
    start_step: StepInt,
    end_step_option: Option<StepInt>,
) -> Result<Option<(RepairAssignment, u32)>> {
    let end_step = end_step_option.unwrap_or(rctx.tb.step_count() - 1);

    // start encoding
    rctx.enc.init_at(rctx.ctx, rctx.smt_ctx, start_step)?;

    // constrain starting state to that from the simulator
    constrain_starting_state(rctx, start_step)?;

    let start_unroll = std::time::Instant::now();
    // unroll system and constrain inputs and outputs
    for _ in start_step..end_step {
        rctx.enc.unroll(rctx.ctx, rctx.smt_ctx)?;
    }
    if rctx.verbose {
        println!(
            "Took {:?} to unroll",
            std::time::Instant::now() - start_unroll
        );
    }

    let start_apply_const = std::time::Instant::now();
    rctx.tb
        .apply_constraints(rctx.ctx, rctx.smt_ctx, rctx.enc, start_step, end_step)?;
    if rctx.verbose {
        println!(
            "Took {:?} to apply constraints",
            std::time::Instant::now() - start_apply_const
        );
    }

    // check to see if a solution exists
    let start_check = std::time::Instant::now();
    let r = rctx.smt_ctx.check()?;
    let check_duration = std::time::Instant::now() - start_check;
    if rctx.verbose {
        println!("Check-Sat took {check_duration:?}");
    }
    match r {
        // cannot find a repair
        smt::Response::Unsat | smt::Response::Unknown => {
            return Ok(None);
        }
        smt::Response::Sat => {} // OK, continue
    }

    // find a minimal repair
    let min_num_changes = minimize_changes(rctx, start_step)?;
    if rctx.verbose {
        println!("Found a minimal solution with {min_num_changes} changes.")
    }

    let solution = rctx
        .synth_vars
        .read_assignment(rctx.ctx, rctx.smt_ctx, rctx.enc, start_step);
    check_assuming_end(rctx.smt_ctx, &rctx.solver)?;
    Ok(Some((solution, min_num_changes)))
}
