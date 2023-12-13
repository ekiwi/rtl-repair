// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::basic::generate_minimal_repair;
use crate::testbench::{RunConfig, RunResult, StepInt, StopAt};
use easy_smt as smt;
use easy_smt::Response;
use libpatron::mc::*;
use std::collections::HashMap;
use std::fmt::Debug;

use crate::repair::*;

pub struct IncrementalConf {
    pub fail_at: StepInt,
    pub pask_k_step_size: StepInt,
    pub max_repair_window_size: StepInt,
    pub max_solutions: usize,
}

pub struct IncrementalRepair<'a, S: Simulator> {
    rctx: RepairContext<'a, S>,
    conf: &'a IncrementalConf,
    snapshots: HashMap<StepInt, S::SnapshotId>,
    smt_ctx: smt::Context,
}

impl<'a, S: Simulator> IncrementalRepair<'a, S>
where
    S: Simulator,
    <S as Simulator>::SnapshotId: Clone + Debug,
{
    pub fn new(
        rctx: RepairContext<'a, S>,
        conf: &'a IncrementalConf,
        snapshots: HashMap<StepInt, S::SnapshotId>,
    ) -> Result<Self> {
        let smt_ctx = create_smt_ctx(&rctx.conf.solver, rctx.conf.dump_file.as_deref())?;
        Ok(Self {
            rctx,
            snapshots,
            conf,
            smt_ctx,
        })
    }

    pub fn run(&mut self) -> Result<Option<Vec<RepairAssignment>>> {
        let mut window = RepairWindow::new();

        while window.len() <= self.conf.max_repair_window_size {
            let step_range = window.get_step_range(self.conf.fail_at);
            if self.verbose() {
                println!(
                    "Incremental: {} .. {} .. {}",
                    step_range.start, self.conf.fail_at, step_range.end
                );
            }

            // check to see if we can reproduce the error with the simulator
            self.update_sim_state_to_step(step_range.start);
            let conf = RunConfig {
                start: step_range.start,
                stop: StopAt::first_fail_or_step(step_range.end),
            };
            let res = self.rctx.tb.run(self.rctx.sim, &conf, self.verbose());
            assert_eq!(res.first_fail_at, Some(self.conf.fail_at), "{conf:?}");

            // start new SMT context to make it easy to later revert everything
            self.smt_ctx.push_many(1)?;

            // generate one minimal repair
            let r = generate_minimal_repair(
                &mut self.rctx,
                &mut self.smt_ctx,
                step_range.start,
                Some(step_range.end),
            )?;
            let mut failures_at = Vec::new();
            let mut correct_solutions = Vec::new();

            if let Some((r0, num_changes, enc)) = r {
                // add a "permanent" change count constraint
                self.constrain_changes(num_changes, &enc, step_range.start)?;

                // iterate over possible solutions
                let mut maybe_repair = Some(r0);
                while let Some(repair) = maybe_repair {
                    if self.verbose() {
                        println!(
                            "Solution: {:?}",
                            self.rctx
                                .synth_vars
                                .get_change_names(self.rctx.ctx, &repair)
                        );
                    }
                    match self.test_repair(&repair).first_fail_at {
                        None => {
                            // success, we found a solution
                            correct_solutions.push(repair.clone());
                            // early exit when we reached the max number of solutions
                            if correct_solutions.len() >= self.conf.max_solutions {
                                return Ok(Some(correct_solutions));
                            }
                        }
                        Some(fail) => {
                            if self.verbose() {
                                println!("New fail at: {fail}");
                            }
                            failures_at.push(fail);
                        }
                    }
                    // try to find a different solution
                    self.rctx.synth_vars.block_assignment(
                        self.rctx.ctx,
                        &mut self.smt_ctx,
                        &enc,
                        &repair,
                        step_range.start,
                    )?;
                    maybe_repair = match self.smt_ctx.check()? {
                        Response::Sat => Some(self.rctx.synth_vars.read_assignment(
                            self.rctx.ctx,
                            &mut self.smt_ctx,
                            &enc,
                            step_range.start,
                        )),
                        Response::Unsat | Response::Unknown => None,
                    };
                }
            } else {
                println!("No repair found for current window size!");
            }
            self.smt_ctx.pop_many(1)?;

            if !correct_solutions.is_empty() {
                return Ok(Some(correct_solutions));
            }

            // we did not find a repair and we continue on
            let progress =
                window.update(&failures_at, self.conf.fail_at, self.conf.pask_k_step_size);
            if !progress {
                if self.verbose() {
                    println!("Could not further increase the repair window.")
                }
                // we were not able to properly update the window
                return Ok(None);
            }
        }

        // exceeded maximum window size => no repair
        if self.verbose() {
            println!(
                "Exceeded the maximum window size of {}",
                self.conf.max_repair_window_size
            );
        }
        Ok(None)
    }

    fn verbose(&self) -> bool {
        self.rctx.conf.verbose
    }

    fn test_repair(&mut self, repair: &RepairAssignment) -> RunResult {
        let start_step = 0;
        self.update_sim_state_to_step(start_step);
        self.rctx.synth_vars.apply_to_sim(self.rctx.sim, repair);
        let conf = RunConfig {
            start: start_step,
            stop: StopAt::first_fail(),
        };
        self.rctx.tb.run(self.rctx.sim, &conf, false)
    }

    fn constrain_changes(
        &mut self,
        num_changes: u32,
        enc: &impl TransitionSystemEncoding,
        start_step: StepInt,
    ) -> Result<()> {
        let change_count_expr = enc.get_at(
            self.rctx.ctx,
            &mut self.smt_ctx,
            self.rctx.change_count_ref,
            start_step,
        );
        let constraint = self.smt_ctx.eq(
            change_count_expr,
            self.smt_ctx
                .binary(CHANGE_COUNT_WIDTH as usize, num_changes),
        );
        self.smt_ctx.assert(constraint)?;
        Ok(())
    }

    fn update_sim_state_to_step(&mut self, step: StepInt) {
        assert!(step < self.rctx.tb.step_count());
        if let Some(snapshot_id) = self.snapshots.get(&step) {
            self.rctx.sim.restore_snapshot(snapshot_id.clone());
        } else {
            // find nearest step, _before_ the step we are going for
            let mut nearest_step = 0;
            let mut nearest_id = self.snapshots[&0].clone();
            for (other_step, snapshot_id) in self.snapshots.iter() {
                if *other_step < step && *other_step > nearest_step {
                    nearest_step = *other_step;
                    nearest_id = snapshot_id.clone();
                }
            }

            // go from nearest snapshot to the point where we want to take a snapshot
            self.rctx.sim.restore_snapshot(nearest_id);
            let run_conf = RunConfig {
                start: nearest_step,
                stop: StopAt::step(step),
            };
            self.rctx.tb.run(self.rctx.sim, &run_conf, self.verbose());

            // remember the state in case we need to go back
            let new_snapshot = self.rctx.sim.take_snapshot();
            self.snapshots.insert(step, new_snapshot.clone());
        }
    }
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
struct RepairWindow {
    future_k: StepInt,
    past_k: StepInt,
}

impl RepairWindow {
    fn new() -> Self {
        Self {
            future_k: 0,
            past_k: 0,
        }
    }

    fn len(&self) -> StepInt {
        self.past_k + self.future_k
    }

    fn get_step_range(&self, fail_at: StepInt) -> std::ops::Range<StepInt> {
        let start = if self.past_k < fail_at {
            fail_at - self.past_k
        } else {
            0
        };
        let end = fail_at + self.future_k;
        start..end
    }

    fn update(
        &mut self,
        failures: &[StepInt],
        original_failure: StepInt,
        past_step_size: StepInt,
    ) -> bool {
        let old = self.clone();
        // when no solution is found, we update the past K
        // in order to get a more accurate starting state
        if failures.is_empty() {
            self.past_k = std::cmp::min(original_failure, past_step_size + self.past_k);
        } else {
            let max_future_failure = failures.iter().filter(|s| **s > original_failure).max();
            match max_future_failure {
                None => {
                    // if there are no solutions that lead to a later failure, we just increase the pastK
                    self.past_k = std::cmp::min(original_failure, past_step_size + self.past_k);
                }
                Some(max_future_failure) => {
                    // increase the window to the largest future K
                    self.future_k = *max_future_failure - original_failure;
                }
            }
        }
        self.future_k != old.future_k || self.past_k != old.past_k
    }
}
