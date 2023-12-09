// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use easy_smt as smt;
use libpatron::ir::*;
use libpatron::mc::{get_smt_value, Simulator, TransitionSystemEncoding, WitnessValue};
use libpatron::sim::interpreter::Value;
use num_bigint::BigUint;
use num_traits::identities::Zero;
use serde_json::json;
use std::str::FromStr;

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
        smt_ctx: &mut smt::Context,
        enc: &impl TransitionSystemEncoding,
    ) -> RepairAssignment {
        let mut change = Vec::with_capacity(self.change.len());
        for sym in self.change.iter() {
            // repair variables do not change, thus we can just always read the value at cycle 0
            let smt_sym = enc.get_at(smt_ctx, *sym, 0);
            let res = get_smt_value(smt_ctx, smt_sym).expect("Failed to read change variable!");
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
            let smt_sym = enc.get_at(smt_ctx, *sym, 0);
            let res = get_smt_value(smt_ctx, smt_sym).expect("Failed to read free variable!");
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
