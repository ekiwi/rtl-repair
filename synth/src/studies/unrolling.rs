// Copyright 2024 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
//
// we study how the length of unrolling affects the basic synthesis approach

use crate::basic::generate_minimal_repair;
use crate::repair::{RepairContext, RepairResult, RepairStatus};
use crate::Stats;
use libpatron::mc::{Simulator, TransitionSystemEncoding};

pub fn unrolling<S: Simulator, E: TransitionSystemEncoding>(
    mut rctx: RepairContext<S, E>,
) -> crate::repair::Result<RepairResult> {
    let res = generate_minimal_repair(&mut rctx, 0, None)?;
    let stats = Stats::default();
    match res {
        None => Ok(RepairResult {
            status: RepairStatus::CannotRepair,
            stats,
            solutions: vec![],
        }), // no solution
        Some((repair, _)) => Ok(RepairResult {
            status: RepairStatus::Success,
            stats,
            solutions: vec![repair],
        }),
    }
}
