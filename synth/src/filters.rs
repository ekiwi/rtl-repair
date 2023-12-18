// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::repair::RepairContext;
use crate::testbench::StepInt;
use easy_smt::Response;
use libpatron::mc::{Simulator, TransitionSystemEncoding};

/// Quick check with no unrolling which can tell if there is no way to repair the design with
/// the provided repair variables.
/// This is done by starting the system from an unconstrained state and checking if there is
/// an assignment to the state and repair variables that will fix the output.
pub fn can_be_repaired_from_arbitrary_state<S: Simulator, E: TransitionSystemEncoding>(
    rctx: &mut RepairContext<S, E>,
    fail_at: StepInt,
) -> std::io::Result<bool> {
    // start new SMT context to make it easy to later revert everything
    rctx.smt_ctx.push_many(1)?;

    // start encoding
    rctx.enc.init_at(rctx.ctx, rctx.smt_ctx, fail_at)?;

    // apply output / input constraints
    rctx.tb
        .apply_constraints(rctx.ctx, rctx.smt_ctx, rctx.enc, fail_at, fail_at)?;

    // let's seee if a solution exists
    let r = rctx.smt_ctx.check()?;

    // clean up
    rctx.smt_ctx.pop_many(1)?;

    match r {
        Response::Sat | Response::Unknown => Ok(true), // can maybe be repaired
        Response::Unsat => Ok(false), // there is no way this system can be repaired!
    }
}
