// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::repair::RepairContext;
use easy_smt as smt;
use libpatron::mc::{Simulator, TransitionSystemEncoding};

/// Quick check with no unrolling which can tell if there is no way to repair the design with
/// the provided repair variables.
/// This is done by starting the system from an unconstrained state and checking if there is
/// an assignment to the state and repair variables that will fix the output.
pub fn can_be_repaired_from_arbitrary_state<S: Simulator, E: TransitionSystemEncoding>(
    rctx: &mut RepairContext<S, E>,
    smt_ctx: &mut smt::Context,
) -> std::io::Result<bool> {
    // start new SMT context to make it easy to later revert everything
    smt_ctx.push_many(1)?;

    Ok(true)
}
