// Copyright 2024 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
//
// we study how the length of unrolling affects the basic synthesis approach

use crate::basic::generate_minimal_repair;
use crate::repair::{RepairContext, RepairResult, RepairStatus};
use crate::start_solver;
use crate::testbench::{RunConfig, StepInt, StopAt};
use libpatron::mc::{Simulator, SmtSolverCmd, UnrollSmtEncoding};
use serde::Serialize;
use std::time::Instant;

#[derive(Debug, Serialize)]
struct Stats {
    /// the maximum number of steps we looked at
    tb_len: StepInt,
    /// how many steps we unrolled for
    end_step: StepInt,
    /// whether a correct repair was found
    success: bool,
    /// for incorrect repairs, where did the test fail
    first_fail_at: Option<StepInt>,
    /// execution time in ns
    time_ns: u128,
    /// minimum number of changes, None if no repair found
    min_repair_size: Option<u64>,
}

pub fn unrolling<S>(
    mut rctx: RepairContext<S, UnrollSmtEncoding>,
    cmd: &SmtSolverCmd,
    dump_smt: Option<&str>,
    first_fail_at: StepInt,
) -> crate::repair::Result<RepairResult>
where
    S: Simulator,
    S::SnapshotId: Clone,
{
    // remember the starting state
    let start_state = rctx.sim.take_snapshot();
    let mut res = None;
    let tb_len = rctx.tb.step_count();
    for end_step in first_fail_at..tb_len {
        // start new smt solver to isolate performance
        (rctx.smt_ctx, rctx.enc) = start_solver(cmd, dump_smt, rctx.ctx, rctx.sys)?;
        let start = Instant::now();
        res = generate_minimal_repair(&mut rctx, 0, Some(end_step))?;
        let time_ns = start.elapsed().as_nanos();

        // check to see if we got a good repair
        let mut min_repair_size = None;
        let mut first_fail_at = None;
        if let Some((repair, min_num_changes)) = &res {
            min_repair_size = Some(*min_num_changes as u64);

            // try out repair to see if we were actually successful
            rctx.sim.restore_snapshot(start_state.clone());
            rctx.synth_vars.apply_to_sim(&mut rctx.sim, repair);
            let conf = RunConfig {
                start: 0,
                stop: StopAt::first_fail(),
            };
            first_fail_at = rctx.tb.run(&mut rctx.sim, &conf, false).first_fail_at;
        }

        let success = res.is_some() && first_fail_at.is_none();
        let s = Stats {
            tb_len,
            end_step,
            success,
            time_ns,
            min_repair_size,
            first_fail_at,
        };
        println!("{}", serde_json::to_string(&s).unwrap());
    }

    let stats = crate::Stats::default();
    match &res {
        None => Ok(RepairResult {
            status: RepairStatus::CannotRepair,
            stats,
            solutions: vec![],
        }), // no solution
        Some((repair, _)) => Ok(RepairResult {
            status: RepairStatus::Success,
            stats,
            solutions: vec![repair.clone()],
        }),
    }
}
