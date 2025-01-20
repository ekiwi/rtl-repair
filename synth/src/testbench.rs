// Copyright 2023-2024 The Regents of the University of California
// Copyright 2025 Cornell University
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cornell.edu>

use crate::repair::{classify_state, CHANGE_COUNT_OUTPUT_NAME};
use baa::{BitVecOps, BitVecValue, Value};
use patronus::expr::{Context, ExprRef, Type, TypeCheck, WidthInt};
use patronus::mc::TransitionSystemEncoding;
use patronus::sim::{InitKind, InitValueGenerator, Simulator};
use patronus::smt::SolverContext;
use patronus::system::TransitionSystem;

pub type Result<T> = std::io::Result<T>;
pub type StepInt = u64;

pub struct Testbench {
    /// contains for each time step: inputs, then outputs
    /// `None` indicates that the value is not constraint, i.e., it is `x`
    data: Vec<Option<BitVecValue>>,
    ios: Vec<IOInfo>,
    /// signals to print for debugging
    signals_to_print: Vec<(String, ExprRef)>,
    missing_outputs: Vec<IOInfo>,
}

#[derive(Debug, Clone)]
struct IOInfo {
    expr: ExprRef,
    cell_id: usize,
    width: WidthInt,
    is_input: bool,
    name: String,
}

pub struct RunResult {
    pub first_fail_at: Option<StepInt>,
}

struct Failure {
    step: StepInt,
    #[allow(dead_code)]
    signal: ExprRef,
}

impl RunResult {
    pub fn is_success(&self) -> bool {
        self.first_fail_at.is_none()
    }
}

#[derive(Debug)]
pub struct RunConfig {
    pub start: StepInt,
    pub stop: StopAt,
}

#[derive(Debug)]
pub struct StopAt {
    at_first_fail: bool,
    at_step: Option<StepInt>,
}

impl StopAt {
    #[allow(dead_code)]
    pub fn end() -> Self {
        Self {
            at_first_fail: false,
            at_step: None,
        }
    }
    pub fn first_fail() -> Self {
        Self {
            at_first_fail: true,
            at_step: None,
        }
    }
    pub fn step(step: StepInt) -> Self {
        Self {
            at_first_fail: false,
            at_step: Some(step),
        }
    }
    pub fn first_fail_or_step(step: StepInt) -> Self {
        Self {
            at_first_fail: true,
            at_step: Some(step),
        }
    }
}

impl Testbench {
    pub fn load(
        ctx: &Context,
        sys: &TransitionSystem,
        filename: &str,
        verbose: bool,
        trace_sim: bool,
    ) -> Result<Self> {
        // memory map file
        let input_file = std::fs::File::open(filename)?;
        let mmap = unsafe { memmap2::Mmap::map(&input_file).expect("failed to memory map file") };

        // read header to find I/O mapping
        let mut header_tokens = Vec::new();
        let header_len = parse_line(&mmap, &mut header_tokens);
        let mut ios = read_header(&header_tokens, ctx, sys, verbose)?;

        // see if we are missing any inputs from the testbench
        let missing_ios = find_missing_ios(ctx, sys, &ios, verbose);
        let missing_inputs = missing_ios.iter().filter(|io| io.is_input).cloned();
        ios.extend(missing_inputs);
        let missing_outputs = missing_ios
            .iter()
            .filter(|io| !io.is_input)
            .cloned()
            .collect::<Vec<_>>();

        // read data
        let data = read_body(header_len, mmap, &ios);

        // generate signals to print if we are instructed to do so
        let mut signals_to_print = vec![];
        if verbose && trace_sim {
            for state in sys.states.iter() {
                let expr = state.symbol;
                let name = ctx.get_symbol_name(expr).unwrap();
                if !classify_state(name).is_synth_var() && expr.get_type(ctx).is_bit_vector() {
                    signals_to_print.push((name.to_string(), expr));
                }
            }
            signals_to_print.sort_by_key(|(name, _)| name.clone());
        }

        let tb = Self {
            data,
            ios,
            signals_to_print,
            missing_outputs,
        };
        Ok(tb)
    }

    #[allow(dead_code)]
    pub fn has_missing_outputs(&self) -> bool {
        !self.missing_outputs.is_empty()
    }

    /// Replaces all X assignments to inputs with a random or zero value.
    pub fn define_inputs(&mut self, kind: InitKind) {
        let mut gen = InitValueGenerator::from_kind(kind);
        for step_id in 0..self.step_count() {
            let range = self.step_range(step_id);
            let values = &mut self.data[range];
            debug_assert_eq!(self.ios.len(), values.len());
            for (io, value) in self.ios.iter().zip(values.iter_mut()) {
                if io.is_input {
                    if value.is_none() {
                        *value = Some(gen.gen(Type::BV(io.width)).try_into().unwrap());
                    }
                }
            }
        }
    }

    fn step_range(&self, step_id: StepInt) -> std::ops::Range<usize> {
        let usize_id = step_id as usize;
        let values_per_step = self.ios.len();
        (usize_id * values_per_step)..((usize_id + 1) * values_per_step)
    }

    pub fn step_count(&self) -> StepInt {
        let values_per_step = self.ios.len();
        self.data.len() as StepInt / values_per_step as StepInt
    }

    pub fn run(&self, sim: &mut impl Simulator, conf: &RunConfig, verbose: bool) -> RunResult {
        let mut failures = Vec::new();
        let last_step_plus_one = match conf.stop.at_step {
            Some(step) => {
                assert!(step < self.step_count());
                step + 1
            }
            None => self.step_count(),
        };
        assert!(conf.start < last_step_plus_one);

        for step_id in conf.start..last_step_plus_one {
            // if this is not the first step, we need to advance the simulation
            if step_id > conf.start {
                sim.step();
            }

            let range = self.step_range(step_id);
            self.do_step(
                step_id as StepInt,
                sim,
                &self.data[range],
                &mut failures,
                verbose,
            );
            // early exit
            if !failures.is_empty() && conf.stop.at_first_fail {
                return RunResult {
                    first_fail_at: Some(step_id as StepInt),
                };
            }
        }
        RunResult {
            first_fail_at: failures.first().map(|f| f.step),
        }
    }

    fn do_step(
        &self,
        step_id: StepInt,
        sim: &mut impl Simulator,
        io_values: &[Option<BitVecValue>],
        failures: &mut Vec<Failure>,
        verbose: bool,
    ) {
        // apply inputs
        debug_assert_eq!(io_values.len(), self.ios.len());
        for (io, maybe_value) in self.ios.iter().zip(io_values.iter()) {
            if io.is_input {
                if let Some(value) = maybe_value {
                    sim.set(io.expr, value);
                }
            }
        }

        // calculate the output values
        sim.update();

        // print values if the option is enabled
        if !self.signals_to_print.is_empty() {
            println!();
            for (name, expr) in self.signals_to_print.iter() {
                if let Value::BitVec(value) = sim.get(*expr) {
                    println!("{name}@{step_id} = {}", value.to_bit_str())
                }
            }
        }

        // check outputs
        debug_assert_eq!(io_values.len(), self.ios.len());
        for (io, maybe_value) in self.ios.iter().zip(io_values.iter()) {
            if !io.is_input {
                if let Some(expected_value) = maybe_value {
                    let actual_value: BitVecValue = sim.get(io.expr).try_into().unwrap();
                    if *expected_value != actual_value {
                        failures.push(Failure {
                            step: step_id,
                            signal: io.expr,
                        });
                        if verbose {
                            println!(
                                "{}@{step_id}: {} vs. {} (E/A)",
                                io.name,
                                expected_value.to_bit_str(),
                                actual_value.to_bit_str()
                            );
                        }
                    }
                }
            }
        }
    }

    pub fn apply_constraints(
        &self,
        ctx: &mut Context,
        smt_ctx: &mut impl SolverContext,
        enc: &impl TransitionSystemEncoding,
        start_step: StepInt,
        end_step: StepInt,
    ) -> patronus::smt::Result<()> {
        for step_id in start_step..(end_step + 1) {
            let range = self.step_range(step_id);
            let io_values = &self.data[range];

            // we can encode everything into a single assert or into multiple asserts
            let single_assert = false;

            // apply all io constraints in this step
            let mut constraints = Vec::with_capacity(self.ios.len());
            debug_assert_eq!(io_values.len(), self.ios.len());
            for (io, maybe_value) in self.ios.iter().zip(io_values.iter()) {
                if let Some(value) = maybe_value {
                    let value_expr = ctx.bv_lit(value);
                    let io_at_step = enc.get_at(ctx, io.expr, step_id);
                    let constraint = ctx.equal(io_at_step, value_expr);
                    if single_assert {
                        constraints.push(constraint);
                    } else {
                        smt_ctx.assert(ctx, constraint)?;
                    }
                }
            }
            if !constraints.is_empty() {
                let constr = constraints
                    .into_iter()
                    .reduce(|a, b| ctx.and(a, b))
                    .unwrap();
                smt_ctx.assert(ctx, constr)?;
            }
        }
        Ok(())
    }
}

fn is_cell_x(token: &[u8]) -> bool {
    matches!(token, b"x" | b"X")
}

fn find_missing_ios(
    ctx: &Context,
    sys: &TransitionSystem,
    ios: &[IOInfo],
    verbose: bool,
) -> Vec<IOInfo> {
    let mut out = Vec::new();
    let inputs = sys
        .inputs
        .iter()
        .map(|&i| (i, ctx.get_symbol_name(i).unwrap(), true));
    let outputs = sys
        .outputs
        .iter()
        .map(|o| (o.expr, ctx[o.name].as_str(), false));
    for (io_expr, io_name, is_input) in inputs.chain(outputs) {
        let included = ios.iter().any(|i| i.expr == io_expr);
        if !included {
            if io_name != CHANGE_COUNT_OUTPUT_NAME {
                let width = io_expr.get_bv_type(ctx).unwrap();

                if verbose {
                    let tpe = if is_input { "Input" } else { "Output" };
                    println!("{tpe} `{io_name}` : bv<{width}> is missing from the testbench.");
                }
                out.push(IOInfo {
                    expr: io_expr,
                    cell_id: usize::MAX,
                    width,
                    is_input,
                    name: io_name.to_string(),
                })
            }
        }
    }
    out
}

fn read_body(header_len: usize, mmap: memmap2::Mmap, ios: &[IOInfo]) -> Vec<Option<BitVecValue>> {
    let mut data = Vec::new();
    let mut pos = header_len;
    let mut tokens = Vec::with_capacity(32);
    while pos < mmap.len() {
        tokens.clear();
        pos += parse_line(&mmap[pos..], &mut tokens);
        if !tokens.is_empty() {
            for io in ios.iter() {
                // read and write words to data
                let is_missing = io.cell_id == usize::MAX;
                if is_missing {
                    data.push(None);
                } else {
                    let cell = tokens[io.cell_id];
                    if is_cell_x(cell) {
                        data.push(None);
                    } else {
                        let cell = std::str::from_utf8(cell).unwrap();
                        let value = BitVecValue::from_str_radix(cell, 10, io.width)
                            .expect("failed to parse decimal value");
                        data.push(Some(value));
                    }
                }
            }
        }
    }
    data
}

fn read_header(
    tokens: &[&[u8]],
    ctx: &Context,
    sys: &TransitionSystem,
    verbose: bool,
) -> std::io::Result<Vec<IOInfo>> {
    let mut out = Vec::new();
    for (cell_id, cell) in tokens.iter().enumerate() {
        let name = String::from_utf8_lossy(cell);
        let input = sys.lookup_input(ctx, &name);
        let output = sys.lookup_output(ctx, &name);
        let expr_ref = input.or(output);

        if let Some(expr_ref) = expr_ref {
            if input.is_some() && output.is_some() {
                todo!("deal correctly with signals that are both, input and output");
            }
            let width = expr_ref.get_bv_type(ctx).unwrap();
            out.push(IOInfo {
                expr: expr_ref,
                cell_id,
                width,
                is_input: input.is_some(),
                name: name.to_string(),
            })
        } else if verbose {
            println!("Ignoring column {name}.");
        }
    }
    Ok(out)
}

fn parse_line<'a>(data: &'a [u8], out: &mut Vec<&'a [u8]>) -> usize {
    assert!(out.is_empty());
    let mut token_start = 0usize;
    let mut found_end = false; // this is to deal with new lines that consist of two characters
    for (offset, bb) in data.iter().enumerate() {
        if found_end {
            return match bb {
                b'\r' | b'\n' => offset + 1, // two character new line => skip
                _ => offset, // one character new line => do not include this character
            };
        }
        match bb {
            b'\r' | b'\n' => {
                out.push(trim(&data[token_start..offset]));
                found_end = true;
            }
            b',' => {
                out.push(trim(&data[token_start..offset]));
                token_start = offset + 1;
            }
            _ => {}
        }
    }
    // end of the file
    let offset = data.len();
    out.push(trim(&data[token_start..offset]));
    offset
}

// remove any whitespace around the edges
fn trim(data: &[u8]) -> &[u8] {
    let first_non_whitespace = data.iter().position(|c| !is_whitespace(*c));
    match first_non_whitespace {
        None => &[], // the complete string consists of white space
        Some(start) => {
            let from_end = data.iter().rev().position(|c| !is_whitespace(*c)).unwrap();
            let end = data.len() - from_end;
            &data[start..end]
        }
    }
}

#[inline]
fn is_whitespace(c: u8) -> bool {
    matches!(c, b' ')
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trim() {
        assert_eq!(trim(b"1234"), b"1234");
        assert_eq!(trim(b" 1234"), b"1234");
        assert_eq!(trim(b"1234  "), b"1234");
        assert_eq!(trim(b"   1234   "), b"1234");
        assert_eq!(trim(b"   12 34   "), b"12 34");
        assert_eq!(trim(b"   12  34   "), b"12  34");
    }
}
