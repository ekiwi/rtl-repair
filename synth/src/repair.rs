// Copyright 2023-2024 The Regents of the University of California
// Copyright 2025 Cornell University
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cornell.edu>

use crate::testbench::{StepInt, Testbench};
use crate::Stats;
use baa::{BitVecOps, BitVecValue};
use patronus::expr::{Context, ExprRef, TypeCheck, WidthInt};
use patronus::mc::*;
use patronus::sim::Simulator;
use patronus::smt::*;
use patronus::system::TransitionSystem;
use serde_json::json;
use std::str::FromStr;

pub type Result<T> = patronus::smt::Result<T>;

#[derive(Debug, PartialEq)]
pub enum RepairStatus {
    CannotRepair,
    NoRepair,
    Success,
}

pub struct RepairResult {
    pub status: RepairStatus,
    pub stats: Stats,
    pub solutions: Vec<RepairAssignment>,
}

pub struct RepairContext<'a, S: Simulator, E: TransitionSystemEncoding, C: SolverContext> {
    pub ctx: &'a mut Context,
    pub sys: &'a TransitionSystem,
    pub sim: S,
    pub synth_vars: &'a RepairVars,
    pub tb: &'a Testbench,
    pub change_count_ref: ExprRef,
    pub smt_ctx: C,
    pub enc: E,
    pub verbose: bool,
}

pub fn constrain_changes<S: Simulator, E: TransitionSystemEncoding, C: SolverContext>(
    rctx: &mut RepairContext<S, E, C>,
    num_changes: u32,
    start_step: StepInt,
) -> ExprRef {
    let change_count_width = rctx.change_count_ref.get_bv_type(rctx.ctx).unwrap();
    let change_count_expr = rctx.enc.get_at(rctx.ctx, rctx.change_count_ref, start_step);
    // constraint
    let num_changes_expr = rctx.ctx.bit_vec_val(num_changes, change_count_width);
    rctx.ctx.equal(change_count_expr, num_changes_expr)
}

pub fn minimize_changes<S: Simulator, E: TransitionSystemEncoding, C: SolverContext>(
    rctx: &mut RepairContext<S, E, C>,
    start_step: StepInt,
) -> Result<u32> {
    let mut num_changes = 1u32;
    loop {
        let constraint = constrain_changes(rctx, num_changes, start_step);
        match check_assuming(rctx.ctx, &mut rctx.smt_ctx, [constraint])? {
            CheckSatResponse::Sat => {
                // found a solution
                return Ok(num_changes);
            }
            CheckSatResponse::Unsat => {}
            CheckSatResponse::Unknown => panic!("SMT solver returned unknown!"),
        }
        // remove assertion for next round
        check_assuming_end(&mut rctx.smt_ctx)?;
        num_changes += 1;
    }
}

pub fn constrain_starting_state<S: Simulator, E: TransitionSystemEncoding, C: SolverContext>(
    rctx: &mut RepairContext<S, E, C>,
    start_step: StepInt,
) -> Result<()> {
    for state in rctx
        .sys
        .states
        .iter()
        .filter(|s| s.init.is_none() && !rctx.synth_vars.is_repair_var(s.symbol))
    {
        let symbol = rctx.enc.get_at(rctx.ctx, state.symbol, start_step);
        let value = rctx.sim.get(state.symbol);
        let smt_value = rctx.ctx.lit(value);
        let is_equal = rctx.ctx.equal(symbol, smt_value);
        rctx.smt_ctx.assert(rctx.ctx, is_equal)?;
    }
    Ok(())
}

pub fn create_smt_ctx(
    solver: &SmtLibSolver,
    dump_file: Option<&str>,
) -> Result<impl SolverContext + 'static> {
    let replay_file = if let Some(filename) = dump_file {
        Some(std::fs::File::create(filename)?)
    } else {
        None
    };
    let mut smt_ctx = solver.start(replay_file)?;
    set_logic(&mut smt_ctx)?;
    Ok(smt_ctx)
}

/// sets the correct logic depending on the solver we are using
pub fn set_logic(smt_ctx: &mut impl SolverContext) -> Result<()> {
    // z3 only supports the non-standard as-const array syntax when the logic is set to ALL
    let logic = if smt_ctx.name() == "z3" {
        Logic::All
    } else if smt_ctx.supports_uf() {
        Logic::QfAufbv
    } else {
        Logic::QfAbv
    };
    smt_ctx.set_logic(logic)
}

pub struct RepairVars {
    pub change: Vec<ExprRef>,           // phi
    pub free: Vec<(ExprRef, WidthInt)>, // alpha
}

// synchronized to the naming conventions used in the python frontend
const SYNTH_VAR_PREFIX: &str = "__synth_";
const SYNTH_CHANGE_PREFIX: &str = "__synth_change_";

impl RepairVars {
    pub fn from_sys(ctx: &Context, sys: &TransitionSystem) -> Self {
        let mut change = Vec::new();
        let mut free = Vec::new();

        for state in sys.states.iter() {
            let name = ctx.get_symbol_name(state.symbol).unwrap();
            match classify_state(name) {
                StateType::ChangeVar => {
                    assert_eq!(
                        state.symbol.get_bv_type(ctx).unwrap(),
                        1,
                        "all change variables need to be boolean"
                    );
                    change.push(state.symbol);
                }
                StateType::FreeVar => {
                    let width = state.symbol.get_bv_type(ctx).unwrap();
                    free.push((state.symbol, width));
                }
                StateType::Other => {} // nothing to do
            }
        }

        RepairVars { change, free }
    }

    pub fn is_repair_var(&self, other: ExprRef) -> bool {
        self.change.contains(&other) || self.free.iter().any(|(e, _)| *e == other)
    }

    pub fn apply_to_sim(&self, sim: &mut impl Simulator, assignment: &RepairAssignment) {
        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            if *value {
                sim.set(*sym, &BitVecValue::new_true());
            } else {
                sim.set(*sym, &BitVecValue::new_false());
            }
        }
        for ((sym, _), value) in self.free.iter().zip(assignment.free.iter()) {
            sim.set(*sym, value);
        }
    }

    pub fn clear_in_sim(&self, sim: &mut impl Simulator) {
        for sym in self.change.iter() {
            sim.set(*sym, &BitVecValue::new_false());
        }
        for (sym, width) in self.free.iter() {
            sim.set(*sym, &BitVecValue::zero(*width));
        }
    }

    pub fn to_json(&self, ctx: &Context, assignment: &RepairAssignment) -> serde_json::Value {
        let mut out = serde_json::Map::with_capacity(self.change.len() + self.free.len());

        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            let num_value = if *value { 1 } else { 0 };
            let sym_name = ctx.get_symbol_name(*sym).unwrap().to_string();
            out.insert(sym_name, json!(num_value));
        }
        for ((sym, _width), value) in self.free.iter().zip(assignment.free.iter()) {
            let num_value = serde_json::Number::from_str(&value.to_dec_str()).unwrap();
            let sym_name = ctx.get_symbol_name(*sym).unwrap().to_string();
            out.insert(sym_name, json!(num_value));
        }

        serde_json::Value::Object(out)
    }

    pub fn read_assignment(
        &self,
        ctx: &mut Context,
        smt_ctx: &mut impl SolverContext,
        enc: &impl TransitionSystemEncoding,
        start_step: StepInt,
    ) -> RepairAssignment {
        let mut change = Vec::with_capacity(self.change.len());
        for sym in self.change.iter() {
            // repair variables do not change, we can just always read the value at the first cycle
            let smt_sym = enc.get_at(ctx, *sym, start_step);
            let res =
                get_smt_value(ctx, smt_ctx, smt_sym).expect("Failed to read change variable!");
            if let baa::Value::BitVec(value) = res {
                assert_eq!(value.width(), 1);
                change.push(!value.is_zero());
            } else {
                panic!("should not get an array value!");
            }
        }
        let mut free = Vec::with_capacity(self.free.len());
        for (sym, _width) in self.free.iter() {
            // repair variables do not change, we can just always read the value at the first cycle
            let smt_sym = enc.get_at(ctx, *sym, start_step);
            let res = get_smt_value(ctx, smt_ctx, smt_sym).expect("Failed to read free variable!");
            if let baa::Value::BitVec(value) = res {
                free.push(value);
            } else {
                panic!("should not get an array value!");
            }
        }
        RepairAssignment { change, free }
    }

    pub fn block_assignment(
        &self,
        ctx: &mut Context,
        smt_ctx: &mut impl SolverContext,
        enc: &impl TransitionSystemEncoding,
        assignment: &RepairAssignment,
        start_step: StepInt,
    ) -> patronus::smt::Result<()> {
        // disallow this particular combination of change variables
        let constraints = self
            .change
            .iter()
            .zip(assignment.change.iter())
            .map(|(sym, value)| {
                // repair variables do not change, we can just always read the value at the first cycle
                let smt_sym = enc.get_at(ctx, *sym, start_step);
                if *value {
                    smt_sym
                } else {
                    ctx.not(smt_sym)
                }
            })
            .collect::<Vec<_>>();
        debug_assert!(!constraints.is_empty());
        let assignment_constraint = constraints
            .into_iter()
            .reduce(|a, b| ctx.and(a, b))
            .unwrap();
        let no_assignment = ctx.not(assignment_constraint);
        smt_ctx.assert(ctx, no_assignment)
    }

    pub fn get_change_names(&self, ctx: &Context, assignment: &RepairAssignment) -> Vec<String> {
        let mut out = vec![];
        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            if *value {
                out.push(ctx.get_symbol_name(*sym).unwrap().to_string());
            }
        }
        out
    }
}

pub enum StateType {
    ChangeVar,
    FreeVar,
    Other,
}

impl StateType {
    pub fn is_synth_var(&self) -> bool {
        !matches!(&self, StateType::Other)
    }
}

/// Determines whether a state is a synthesis variable and what kind by looking at the name.
pub fn classify_state(name: &str) -> StateType {
    let suffix = name.split('.').last().unwrap();
    // important to check the change prefix first
    // (since the var prefix is a prefix of the change prefix)
    if suffix.starts_with(SYNTH_CHANGE_PREFIX) {
        StateType::ChangeVar
    } else if suffix.starts_with(SYNTH_VAR_PREFIX) {
        StateType::FreeVar
    } else {
        StateType::Other
    }
}

#[derive(Debug, Clone)]
pub struct RepairAssignment {
    pub change: Vec<bool>,
    pub free: Vec<BitVecValue>,
}

pub const CHANGE_COUNT_OUTPUT_NAME: &str = "__change_count";

pub fn add_change_count(
    ctx: &mut Context,
    sys: &mut TransitionSystem,
    change: &[ExprRef],
) -> ExprRef {
    let max_change_count_value = change.len() as u64;
    let width = std::cmp::max(u64::BITS - max_change_count_value.leading_zeros(), 1);
    let sum = match change.len() {
        0 => ctx.zero(width),
        1 => ctx.zero_extend(change[0], width - 1),
        _ => {
            let extended = change
                .iter()
                .map(|c| ctx.zero_extend(*c, width - 1))
                .collect::<Vec<_>>();
            extended.into_iter().reduce(|a, b| ctx.add(a, b)).unwrap()
        }
    };
    sys.add_output(ctx, CHANGE_COUNT_OUTPUT_NAME.into(), sum);
    sum
}
