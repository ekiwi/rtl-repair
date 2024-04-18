// Copyright 2024 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
//
// This is not a real synthesizer implementation.
// Instead we are trying to find out which windows sizes can solve a synthesis problem.

use crate::basic::generate_minimal_repair;
use crate::incremental::{constrain_changes, test_repair, update_sim_state_to_step};
use crate::repair::{RepairAssignment, RepairContext, RepairResult, RepairStatus, Result};
use crate::start_solver;
use crate::testbench::{RunConfig, StepInt, StopAt};
use easy_smt::Response;
use libpatron::mc::{Simulator, SmtSolverCmd, TransitionSystemEncoding, UnrollSmtEncoding};
use serde::Serialize;
use std::collections::HashMap;
use std::fmt::Debug;
use std::time::Instant;

pub struct WindowingConf {
    pub cmd: SmtSolverCmd,
    pub dump_smt: Option<String>,
    /// Information about the first cycle in which the bug manifests.
    pub fail_at: StepInt,
    /// The maximum size of the repair window.
    pub max_repair_window_size: StepInt,
}

pub struct Windowing<'a, S: Simulator, E: TransitionSystemEncoding> {
    rctx: RepairContext<'a, S, E>,
    conf: WindowingConf,
    snapshots: HashMap<StepInt, S::SnapshotId>,
}

#[derive(Debug, Serialize)]
struct Stats {
    /// time it took to sample the first minimal repair
    minimal_repair_candidate_ns: Option<u128>,
    /// number of minimal repairs sampled before we found a correct repair
    correct_repair_tries: Option<u64>,
    /// time to find a correct repair
    correct_repair_ns: Option<u128>,
}

#[derive(Debug, Serialize)]
struct WindowConf {
    past_k: StepInt,
    future_k: StepInt,
    window_size: StepInt,
    offset: StepInt,
}

impl WindowConf {
    fn get_step_range(&self, fail_at: StepInt) -> std::ops::Range<StepInt> {
        let start = if self.past_k < fail_at {
            fail_at - self.past_k
        } else {
            0
        };
        let end = fail_at + self.future_k;
        start..end
    }
}

#[derive(Debug, Serialize)]
struct Line {
    conf: WindowConf,
    stats: Stats,
}

impl<'a, S: Simulator> Windowing<'a, S, UnrollSmtEncoding>
where
    S: Simulator,
    <S as Simulator>::SnapshotId: Clone + Debug,
{
    pub fn new(
        rctx: RepairContext<'a, S, UnrollSmtEncoding>,
        conf: WindowingConf,
        snapshots: HashMap<StepInt, S::SnapshotId>,
    ) -> Result<Self> {
        Ok(Self {
            rctx,
            snapshots,
            conf,
        })
    }
    pub fn run(&mut self) -> Result<RepairResult> {
        let mut result = RepairResult {
            status: RepairStatus::CannotRepair,
            stats: crate::Stats {
                final_past_k: 0,
                final_future_k: 0,
                solver_time: 0,
            },
            solutions: vec![],
        };

        // iterate over all possible window sizes
        for window_size in 1..=self.conf.max_repair_window_size {
            // iterate over all window shifts that contain the output divergence step
            for offset in 0..window_size {
                // derive past and future k
                let past_k = window_size - 1 - offset;
                if past_k >= self.conf.fail_at {
                    // window does not fit on the left
                    continue;
                }
                // println!("window_size={window_size}, past_k={past_k}, offset={offset}");
                let future_k = window_size - 1 - past_k;
                if self.conf.fail_at + future_k > self.rctx.tb.step_count() {
                    // window does not fit on the right
                    continue;
                }
                assert_eq!(past_k + future_k + 1, window_size);
                let c = WindowConf {
                    past_k,
                    future_k,
                    window_size,
                    offset,
                };
                let (stats, rr) = self.inner(&c)?;
                let l = Line { conf: c, stats };
                println!("{}", serde_json::to_string(&l).unwrap());
                if rr.status == RepairStatus::Success {
                    result = rr;
                }
            }
        }

        Ok(result)
    }

    fn inner(&mut self, window: &WindowConf) -> Result<(Stats, RepairResult)> {
        let start = Instant::now();
        let verbose = false;
        let step_range = window.get_step_range(self.conf.fail_at);

        // check to see if we can reproduce the error with the simulator
        update_sim_state_to_step(
            &mut self.rctx,
            &mut self.snapshots,
            verbose,
            step_range.start,
        );
        let conf = RunConfig {
            start: step_range.start,
            stop: StopAt::first_fail_or_step(step_range.end),
        };
        let res = self.rctx.tb.run(&mut self.rctx.sim, &conf, verbose);
        assert_eq!(res.first_fail_at, Some(self.conf.fail_at), "{conf:?}");

        // restore correct starting state for SMT encoding
        update_sim_state_to_step(
            &mut self.rctx,
            &mut self.snapshots,
            verbose,
            step_range.start,
        );

        // start new smt solver to isolate performance
        (self.rctx.smt_ctx, self.rctx.enc) = start_solver(
            &self.conf.cmd,
            self.conf.dump_smt.as_deref(),
            self.rctx.ctx,
            self.rctx.sys,
        )?;

        // generate one minimal repair
        let r = generate_minimal_repair(&mut self.rctx, step_range.start, Some(step_range.end))?;
        let minimal_repair_candidate_ns = start.elapsed().as_nanos();
        let mut failures_at = Vec::new();

        if let Some((r0, num_changes)) = r {
            // add a "permanent" change count constraint
            constrain_changes(&mut self.rctx, num_changes, step_range.start)?;

            // iterate over possible solutions
            let mut maybe_repair = Some(r0);
            while let Some(repair) = maybe_repair {
                match test_repair(&mut self.rctx, &mut self.snapshots, verbose, &repair)
                    .first_fail_at
                {
                    None => {
                        let correct_repair_ns = Some(start.elapsed().as_nanos());
                        let stats = Stats {
                            minimal_repair_candidate_ns: Some(minimal_repair_candidate_ns),
                            correct_repair_tries: Some((failures_at.len() + 1) as u64),
                            correct_repair_ns,
                        };
                        return Ok((stats, make_result(Some(repair), window)));
                    }
                    Some(fail) => {
                        if verbose {
                            println!("New fail at: {fail}");
                        }
                        failures_at.push(fail);
                    }
                }
                // try to find a different solution
                self.rctx.synth_vars.block_assignment(
                    self.rctx.ctx,
                    &mut self.rctx.smt_ctx,
                    &self.rctx.enc,
                    &repair,
                    step_range.start,
                )?;
                maybe_repair = match self.rctx.smt_ctx.check()? {
                    Response::Sat => Some(self.rctx.synth_vars.read_assignment(
                        self.rctx.ctx,
                        &mut self.rctx.smt_ctx,
                        &self.rctx.enc,
                        step_range.start,
                    )),
                    Response::Unsat | Response::Unknown => None,
                };
            }
            // no correct repair found
            let stats = Stats {
                minimal_repair_candidate_ns: Some(minimal_repair_candidate_ns),
                correct_repair_tries: None,
                correct_repair_ns: None,
            };
            Ok((stats, make_result(None, window)))
        } else {
            // no repair found
            let stats = Stats {
                minimal_repair_candidate_ns: None,
                correct_repair_tries: None,
                correct_repair_ns: None,
            };
            Ok((stats, make_result(None, window)))
        }
    }
}

fn make_result(solution: Option<RepairAssignment>, window: &WindowConf) -> RepairResult {
    RepairResult {
        status: if solution.is_none() {
            RepairStatus::CannotRepair
        } else {
            RepairStatus::Success
        },
        stats: crate::Stats {
            final_past_k: window.past_k,
            final_future_k: window.future_k,
            solver_time: 0,
        },
        solutions: solution.map(|s| vec![s]).unwrap_or_default(),
    }
}
