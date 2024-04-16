// Copyright 2024 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
//
// This is not a real synthesizer implementation.
// Instead we are trying to find out which windows sizes can solve a synthesis problem.

use crate::repair::{RepairContext, RepairResult, Result};
use crate::testbench::StepInt;
use libpatron::mc::{Simulator, TransitionSystemEncoding};
use serde::Serialize;
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

#[derive(Debug, Serialize)]
struct Stats {
    /// time it took to sample the first minimal repair
    minimal_repair_candidate_ns: Option<u64>,
    /// number of minimal repairs sampled before we found a correct repair
    correct_repair_tries: Option<u64>,
    /// time to find a correct repair
    correct_repair_ns: Option<u64>,
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

impl<'a, S: Simulator, E: TransitionSystemEncoding> Windowing<'a, S, E>
where
    S: Simulator,
    <S as Simulator>::SnapshotId: Clone + Debug,
{
    pub fn new(rctx: RepairContext<'a, S, E>, conf: WindowingConf) -> Result<Self> {
        Ok(Self { rctx, conf })
    }

    pub fn run(&mut self) -> Result<RepairResult> {
        // iterate over all possible window sizes
        for window_size in 1..=self.conf.max_repair_window_size {
            // iterate over all window shifts that contain the output divergence step
            for offset in 0..window_size {
                // derive past and future k
                let past_k = window_size - 1 + offset;
                let future_k = window_size - 1 - past_k;
                assert_eq!(past_k + future_k + 1, window_size);
                let c = WindowConf {
                    past_k,
                    future_k,
                    window_size,
                    offset,
                };
                let (stats, _result) = self.inner(&c)?;
                let l = Line { conf: c, stats };
                println!("{}", serde_json::to_string(&l).unwrap());
            }
        }

        todo!()
    }

    fn inner(&mut self, window: &WindowConf) -> Result<(Stats, RepairResult)> {
        let step_range = window.get_step_range(self.conf.fail_at);

        todo!();
    }
}
