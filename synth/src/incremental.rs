// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::testbench::{RunConfig, StepInt, StopAt, Testbench};
use easy_smt as smt;
use libpatron::ir::*;
use libpatron::mc::*;
use std::collections::HashMap;

use crate::repair::*;

pub struct IncrementalRepair<'a, S: Simulator> {
    ctx: &'a mut Context,
    sys: &'a TransitionSystem,
    sim: &'a mut S,
    synth_vars: &'a RepairVars,
    tb: &'a Testbench,
    change_count_ref: ExprRef,
    snapshots: HashMap<StepInt, S::SnapshotId>,
    fail_at: StepInt,
    max_window: StepInt,
    verbose: bool,
    smt_ctx: smt::Context,
}

impl<'a, S: Simulator> IncrementalRepair<'a, S>
where
    S: Simulator,
    <S as Simulator>::SnapshotId: Clone,
{
    pub fn new(
        ctx: &'a mut Context,
        sys: &'a TransitionSystem,
        synth_vars: &'a RepairVars,
        sim: &'a mut S,
        tb: &'a Testbench,
        conf: RepairConfig,
        change_count_ref: ExprRef,
        snapshots: HashMap<StepInt, S::SnapshotId>,
        fail_at: StepInt,
    ) -> Result<Self> {
        let smt_ctx = create_smt_ctx(&conf.solver, conf.dump_file.as_deref())?;
        Ok(Self {
            ctx,
            sys,
            synth_vars,
            sim,
            tb,
            change_count_ref,
            snapshots,
            fail_at,
            max_window: 32,
            verbose: conf.verbose,
            smt_ctx,
        })
    }

    pub fn run(&mut self) -> Result<Option<Vec<RepairAssignment>>> {
        let mut past_k = self.fail_at;
        let mut future_k = self.fail_at;

        while past_k + future_k <= self.max_window {
            assert!(past_k >= self.fail_at);
            let start_step = self.fail_at - past_k;
            let end_step = self.fail_at + future_k;

            // check to see if we can reproduce the error with the simulator
            self.update_sim_state_to_step(start_step);
            let conf = RunConfig {
                start: start_step,
                stop: StopAt::first_fail_or_step(end_step),
            };
            let res = self.tb.run(self.sim, &conf, false);
            assert_eq!(res.first_fail_at, Some(self.fail_at));

            // generate all possible minimal solutions

            todo!("synthesize solutions")
        }

        todo!("implement incremental repair")
    }

    fn update_sim_state_to_step(&mut self, step: StepInt) {
        assert!(step < self.tb.step_count());
        if let Some(snapshot_id) = self.snapshots.get(&step) {
            self.sim.restore_snapshot(snapshot_id.clone());
        } else {
            // find nearest step, _before_ the step we are going for
            let mut nearest_step = 0;
            let mut nearest_id = None;
            for (other_step, snapshot_id) in self.snapshots.iter() {
                if *other_step < step && *other_step > nearest_step {
                    nearest_step = *other_step;
                    nearest_id = Some(snapshot_id.clone());
                }
            }

            // go from nearest snapshot to the point where we want to take a snapshot
            self.sim.restore_snapshot(nearest_id.unwrap());
            let run_conf = RunConfig {
                start: nearest_step,
                stop: StopAt::step(step),
            };
            self.tb.run(self.sim, &run_conf, self.verbose);

            // remember the state in case we need to go back
            let new_snapshot = self.sim.take_snapshot();
            self.snapshots.insert(step, new_snapshot.clone());
        }
    }
}
