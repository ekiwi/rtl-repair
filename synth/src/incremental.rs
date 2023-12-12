// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::testbench::{StepInt, Testbench};
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

impl<'a, S: Simulator> IncrementalRepair<'a, S> {
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

        while past_k + future_k <= self.max_window {}

        todo!("implement incremental repair")
    }
}
