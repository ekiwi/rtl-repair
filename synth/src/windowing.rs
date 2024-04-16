// Copyright 2024 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
//
// This is not a real synthesizer implementation.
// Instead we are trying to find out which windows sizes can solve a synthesis problem.

use crate::repair::{RepairContext, RepairResult, Result};
use crate::testbench::StepInt;
use libpatron::mc::{Simulator, TransitionSystemEncoding};
use std::fmt::Debug;

pub struct WindowingConf {
    /// Information about the first cycle in which the bug manifests.
    pub fail_at: StepInt,
    /// The maximum size of the repair window.
    pub max_repair_window_size: StepInt,
}

pub struct Windowing<'a, S: Simulator, E: TransitionSystemEncoding> {
    rctx: RepairContext<'a, S, E>,
    conf: WindowingConf,
}

impl<'a, S: Simulator, E: TransitionSystemEncoding> Windowing<'a, S, E>
where
    S: Simulator,
    <S as Simulator>::SnapshotId: Clone + Debug,
{
    pub fn new(rctx: RepairContext<'a, S, E>, conf: WindowingConf) -> crate::repair::Result<Self> {
        Ok(Self { rctx, conf })
    }

    pub fn run(&mut self) -> Result<RepairResult> {
        todo!()
    }
}
