// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use libpatron::ir::{ExprRef, TransitionSystem};

pub struct RepairVars {
    pub change: Vec<ExprRef>, // phi
    pub free: Vec<ExprRef>,   // alpha
}

// synchronized to the naming conventions used in the python frontend
const SYNTH_VAR_PREFIX: &str = "__synth_";
const SYNTH_CHANGE_PREFIX: &str = "__synth_change_";

impl RepairVars {
    pub fn from_sys(sys: &TransitionSystem) -> Self {
        //todo!()
        let change = Vec::new();
        let free = Vec::new();
        RepairVars { change, free }
    }
}
