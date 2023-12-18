// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::testbench::{StepInt, Testbench};
use easy_smt as smt;
use libpatron::ir::*;
use libpatron::mc::*;
use libpatron::sim::interpreter::{Value, ValueRef};
use num_bigint::BigUint;
use num_traits::identities::Zero;
use serde_json::json;
use std::str::FromStr;

pub type Result<T> = std::io::Result<T>;

pub struct RepairContext<'a, S: Simulator, E: TransitionSystemEncoding> {
    pub ctx: &'a mut Context,
    pub sys: &'a TransitionSystem,
    pub sim: &'a mut S,
    pub synth_vars: &'a RepairVars,
    pub tb: &'a Testbench,
    pub change_count_ref: ExprRef,
    pub smt_ctx: &'a mut smt::Context,
    pub enc: &'a mut E,
    pub solver: SmtSolverCmd,
    pub verbose: bool,
}

pub fn minimize_changes<S: Simulator, E: TransitionSystemEncoding>(
    rctx: &mut RepairContext<S, E>,
    start_step: StepInt,
) -> Result<u32> {
    let mut num_changes = 1u32;
    let change_count_expr =
        rctx.enc
            .get_at(rctx.ctx, rctx.smt_ctx, rctx.change_count_ref, start_step);
    loop {
        let constraint = rctx.smt_ctx.eq(
            change_count_expr,
            rctx.smt_ctx
                .binary(CHANGE_COUNT_WIDTH as usize, num_changes),
        );
        match check_assuming(rctx.smt_ctx, constraint, &rctx.solver)? {
            smt::Response::Sat => {
                // found a solution
                return Ok(num_changes);
            }
            smt::Response::Unsat => {}
            smt::Response::Unknown => panic!("SMT solver returned unknown!"),
        }
        // remove assertion for next round
        check_assuming_end(rctx.smt_ctx, &rctx.solver)?;
        num_changes += 1;
    }
}

pub fn constrain_starting_state<S: Simulator, E: TransitionSystemEncoding>(
    rctx: &mut RepairContext<S, E>,
    start_step: StepInt,
) -> Result<()> {
    for state in rctx
        .sys
        .states()
        .filter(|s| s.init.is_none() && !rctx.synth_vars.is_repair_var(s.symbol))
    {
        let value = rctx.sim.get(state.symbol).unwrap();
        let value_expr = value_to_smt_expr(rctx.smt_ctx, value);
        let symbol = rctx
            .enc
            .get_at(rctx.ctx, rctx.smt_ctx, state.symbol, start_step);
        rctx.smt_ctx.assert(rctx.smt_ctx.eq(symbol, value_expr))?;
    }
    Ok(())
}

fn value_to_smt_expr(smt_ctx: &mut smt::Context, value: ValueRef) -> smt::SExpr {
    // currently this will only work for scalar values
    let bits = value.to_bit_string();
    bit_string_to_smt(smt_ctx, &bits)
}

pub fn bit_string_to_smt(smt_ctx: &mut smt::Context, bits: &str) -> smt::SExpr {
    match bits {
        "0" => smt_ctx.false_(),
        "1" => smt_ctx.true_(),
        other => smt_ctx.atom(format!("#b{}", other)),
    }
}

pub fn create_smt_ctx(solver: &SmtSolverCmd, dump_file: Option<&str>) -> Result<smt::Context> {
    let replay_file = if let Some(filename) = dump_file {
        Some(std::fs::File::create(filename)?)
    } else {
        None
    };
    let mut smt_ctx = smt::ContextBuilder::new()
        .solver(solver.name, solver.args)
        .replay_file(replay_file)
        .build()?;
    set_logic(&mut smt_ctx, solver)?;
    Ok(smt_ctx)
}

/// sets the correct logic depending on the solver we are using
fn set_logic(smt_ctx: &mut smt::Context, cmd: &SmtSolverCmd) -> Result<()> {
    // z3 only supports the non-standard as-const array syntax when the logic is set to ALL
    let logic = if cmd.name == "z3" {
        "ALL"
    } else if cmd.supports_uf {
        "QF_AUFBV"
    } else {
        "QF_ABV"
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

        for state in sys.states() {
            let name = state.symbol.get_symbol_name(ctx).unwrap();
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
        self.change.contains(&other) || self.free.iter().find(|(e, _)| *e == other).is_some()
    }

    pub fn apply_to_sim(&self, sim: &mut impl Simulator, assignment: &RepairAssignment) {
        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            let num_value = if *value { 1 } else { 0 };
            sim.set(*sym, ValueRef::new(&[num_value], 1));
        }
        for ((sym, width), value) in self.free.iter().zip(assignment.free.iter()) {
            sim.set(*sym, (&Value::from_big_uint(value, *width)).into());
        }
    }

    pub fn clear_in_sim(&self, sim: &mut impl Simulator) {
        for sym in self.change.iter() {
            sim.set(*sym, ValueRef::new(&[0], 1));
        }
        for (sym, width) in self.free.iter() {
            sim.set(
                *sym,
                (&Value::from_big_uint(&BigUint::zero(), *width)).into(),
            );
        }
    }

    pub fn to_json(&self, ctx: &Context, assignment: &RepairAssignment) -> serde_json::Value {
        let mut out = serde_json::Map::with_capacity(self.change.len() + self.free.len());

        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            let num_value = if *value { 1 } else { 0 };
            let sym_name = sym.get_symbol_name(ctx).unwrap().to_string();
            out.insert(sym_name, json!(num_value));
        }
        for ((sym, _width), value) in self.free.iter().zip(assignment.free.iter()) {
            let num_value = serde_json::Number::from_str(&value.to_string()).unwrap();
            let sym_name = sym.get_symbol_name(ctx).unwrap().to_string();
            out.insert(sym_name, json!(num_value));
        }

        serde_json::Value::Object(out)
    }

    pub fn read_assignment(
        &self,
        ctx: &Context,
        smt_ctx: &mut smt::Context,
        enc: &impl TransitionSystemEncoding,
        start_step: StepInt,
    ) -> RepairAssignment {
        let mut change = Vec::with_capacity(self.change.len());
        for sym in self.change.iter() {
            // repair variables do not change, we can just always read the value at the first cycle
            let smt_sym = enc.get_at(ctx, smt_ctx, *sym, start_step);
            let res = get_smt_value(smt_ctx, smt_sym, sym.get_type(ctx))
                .expect("Failed to read change variable!");
            if let WitnessValue::Scalar(value, width) = res {
                assert_eq!(width, 1);
                change.push(!value.is_zero());
            } else {
                panic!("should not get an array value!");
            }
        }
        let mut free = Vec::with_capacity(self.free.len());
        for (sym, _width) in self.free.iter() {
            // repair variables do not change, we can just always read the value at the first cycle
            let smt_sym = enc.get_at(ctx, smt_ctx, *sym, start_step);
            let res = get_smt_value(smt_ctx, smt_sym, sym.get_type(ctx))
                .expect("Failed to read free variable!");
            if let WitnessValue::Scalar(value, _) = res {
                free.push(value);
            } else {
                panic!("should not get an array value!");
            }
        }
        RepairAssignment { change, free }
    }

    pub fn block_assignment(
        &self,
        ctx: &Context,
        smt_ctx: &mut smt::Context,
        enc: &impl TransitionSystemEncoding,
        assignment: &RepairAssignment,
        start_step: StepInt,
    ) -> std::io::Result<()> {
        // disallow this particular combination of change variables
        let constraints = self
            .change
            .iter()
            .zip(assignment.change.iter())
            .map(|(sym, value)| {
                // repair variables do not change, we can just always read the value at the first cycle
                let smt_sym = enc.get_at(ctx, smt_ctx, *sym, start_step);
                if *value {
                    smt_sym
                } else {
                    smt_ctx.not(smt_sym)
                }
            })
            .collect::<Vec<_>>();
        let assignment_constraint = smt_ctx.and_many(constraints);
        let no_assignment = smt_ctx.not(assignment_constraint);
        smt_ctx.assert(no_assignment)
    }

    pub fn get_change_names(&self, ctx: &Context, assignment: &RepairAssignment) -> Vec<String> {
        let mut out = vec![];
        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            if *value {
                out.push(sym.get_symbol_name(ctx).unwrap().to_string());
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
    pub free: Vec<BigUint>,
}

pub const CHANGE_COUNT_OUTPUT_NAME: &str = "__change_count";
pub const CHANGE_COUNT_WIDTH: WidthInt = 16;

pub fn add_change_count(
    ctx: &mut Context,
    sys: &mut TransitionSystem,
    change: &[ExprRef],
) -> ExprRef {
    let width = CHANGE_COUNT_WIDTH;
    let sum = match change.len() {
        0 => ctx.bv_lit(0, width),
        1 => ctx.zero_extend(change[0], width - 1),
        _ => {
            let extended = change
                .iter()
                .map(|c| ctx.zero_extend(*c, width - 1))
                .collect::<Vec<_>>();
            extended.into_iter().reduce(|a, b| ctx.add(a, b)).unwrap()
        }
    };
    let name_ref = ctx.add_node(CHANGE_COUNT_OUTPUT_NAME);
    sys.add_signal(
        sum,
        SignalKind::Node,
        SignalLabels::output(),
        Some(name_ref),
    );
    sum
}
