// Copyright 2023-2024 The Regents of the University of California
// Copyright 2025 Cornell University
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cornell.edu>

use crate::repair::RepairContext;
use crate::testbench::StepInt;
use patronus::mc::TransitionSystemEncoding;
use patronus::sim::Simulator;
use patronus::smt::{CheckSatResponse, SolverContext};

/// Quick check with no unrolling which can tell if there is no way to repair the design with
/// the provided repair variables.
/// This is done by starting the system from an unconstrained state and checking if there is
/// an assignment to the state and repair variables that will fix the output.
pub fn can_be_repaired_from_arbitrary_state<
    S: Simulator,
    E: TransitionSystemEncoding,
    C: SolverContext,
>(
    rctx: &mut RepairContext<S, E, C>,
    fail_at: StepInt,
) -> patronus::smt::Result<bool> {
    // start new SMT context to make it easy to later revert everything
    rctx.smt_ctx.push()?;

    // start encoding
    rctx.enc.init_at(rctx.ctx, &mut rctx.smt_ctx, fail_at)?;

    // apply output / input constraints
    rctx.tb
        .apply_constraints(rctx.ctx, &mut rctx.smt_ctx, &rctx.enc, fail_at, fail_at)?;

    // let's seee if a solution exists
    let r = rctx.smt_ctx.check_sat()?;

    // clean up
    rctx.smt_ctx.pop()?;

    match r {
        CheckSatResponse::Sat | CheckSatResponse::Unknown => Ok(true), // can maybe be repaired
        CheckSatResponse::Unsat => Ok(false), // there is no way this system can be repaired!
    }
}
