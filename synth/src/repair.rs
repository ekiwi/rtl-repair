// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use easy_smt as smt;
use libpatron::ir::*;
use libpatron::mc::*;
use libpatron::sim::interpreter::{Value, ValueRef};
use num_bigint::BigUint;
use num_traits::identities::Zero;
use serde_json::json;
use std::str::FromStr;

pub type Result<T> = std::io::Result<T>;

pub struct RepairConfig {
    pub solver: SmtSolverCmd,
    pub verbose: bool,
    pub dump_file: Option<String>,
}

pub fn minimize_changes(
    ctx: &Context,
    smt_ctx: &mut smt::Context,
    solver: &SmtSolverCmd,
    change_count_ref: ExprRef,
    enc: &impl TransitionSystemEncoding,
) -> Result<u32> {
    let mut num_changes = 1u32;
    let change_count_expr = enc.get_at(ctx, smt_ctx, change_count_ref, 0);
    loop {
        let constraint = smt_ctx.eq(
            change_count_expr,
            smt_ctx.binary(CHANGE_COUNT_WIDTH as usize, num_changes),
        );
        match check_assuming(smt_ctx, constraint, solver)? {
            smt::Response::Sat => {
                // found a solution
                return Ok(num_changes);
            }
            smt::Response::Unsat => {}
            smt::Response::Unknown => panic!("SMT solver returned unknown!"),
        }
        // remove assertion for next round
        check_assuming_end(smt_ctx, solver)?;
        num_changes += 1;
    }
}

pub fn constrain_starting_state(
    ctx: &Context,
    sys: &TransitionSystem,
    synth_vars: &RepairVars,
    sim: &impl Simulator,
    enc: &impl TransitionSystemEncoding,
    smt_ctx: &mut smt::Context,
) -> Result<()> {
    for state in sys
        .states()
        .filter(|s| s.init.is_none() && !synth_vars.is_repair_var(s.symbol))
    {
        let value = sim.get(state.symbol).unwrap();
        let value_expr = value_to_smt_expr(smt_ctx, value);
        let symbol = enc.get_at(ctx, smt_ctx, state.symbol, 0);
        smt_ctx.assert(smt_ctx.eq(symbol, value_expr))?;
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
    set_logic(&mut smt_ctx, &solver)?;
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
    pub change: Vec<ExprRef>, // phi
    pub free: Vec<ExprRef>,   // alpha
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
            if name.starts_with(SYNTH_CHANGE_PREFIX) {
                assert_eq!(
                    state.symbol.get_bv_type(ctx).unwrap(),
                    1,
                    "all change variables need to be boolean"
                );
                change.push(state.symbol);
            } else if name.starts_with(SYNTH_VAR_PREFIX) {
                free.push(state.symbol);
            }
        }

        RepairVars { change, free }
    }

    pub fn is_repair_var(&self, other: ExprRef) -> bool {
        self.change.contains(&other) || self.free.contains(&other)
    }

    pub fn apply_to_sim(&self, sim: &mut impl Simulator, assignment: &RepairAssignment) {
        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            let num_value = if *value { 1 } else { 0 };
            sim.set(*sym, &Value::from_u64(num_value));
        }
        for (sym, value) in self.free.iter().zip(assignment.free.iter()) {
            sim.set(*sym, &Value::from_big_uint(value));
        }
    }

    pub fn clear_in_sim(&self, sim: &mut impl Simulator) {
        for sym in self.change.iter() {
            sim.set(*sym, &Value::from_u64(0));
        }
        for sym in self.free.iter() {
            sim.set(*sym, &Value::from_u64(0));
        }
    }

    pub fn to_json(&self, ctx: &Context, assignment: &RepairAssignment) -> serde_json::Value {
        //let mut out = IndexMap::with_capacity(self.change.len() + self.free.len());
        let mut out = serde_json::Map::with_capacity(self.change.len() + self.free.len());

        for (sym, value) in self.change.iter().zip(assignment.change.iter()) {
            let num_value = if *value { 1 } else { 0 };
            let sym_name = sym.get_symbol_name(ctx).unwrap().to_string();
            out.insert(sym_name, json!(num_value));
        }
        for (sym, value) in self.free.iter().zip(assignment.free.iter()) {
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
    ) -> RepairAssignment {
        let mut change = Vec::with_capacity(self.change.len());
        for sym in self.change.iter() {
            // repair variables do not change, thus we can just always read the value at cycle 0
            let smt_sym = enc.get_at(ctx, smt_ctx, *sym, 0);
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
        for sym in self.free.iter() {
            // repair variables do not change, thus we can just always read the value at cycle 0
            let smt_sym = enc.get_at(ctx, smt_ctx, *sym, 0);
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
}

pub struct RepairAssignment {
    pub change: Vec<bool>,
    pub free: Vec<BigUint>,
}

const CHANGE_COUNT_OUTPUT_NAME: &str = "__change_count";
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
    sys.add_signal(sum, SignalKind::Output, Some(name_ref));
    sum
}
