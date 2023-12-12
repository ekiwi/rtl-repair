// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::testbench::Testbench;
use easy_smt as smt;
use libpatron::ir::*;
use libpatron::mc::*;

use crate::repair::*;

pub fn incremental_repair(
    ctx: &mut Context,
    sys: &TransitionSystem,
    synth_vars: &RepairVars,
    sim: &impl Simulator,
    tb: &Testbench,
    conf: &RepairConfig,
    change_count_ref: ExprRef,
) -> Result<Option<Vec<RepairAssignment>>> {
    let mut smt_ctx = create_smt_ctx(&conf.solver, conf.dump_file.as_deref())?;

    todo!("implement incremental repair")
}
