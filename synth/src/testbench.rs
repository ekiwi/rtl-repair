// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use crate::repair::{bit_string_to_smt, classify_state, CHANGE_COUNT_OUTPUT_NAME};
use libpatron::ir::*;
use libpatron::mc::{Simulator, TransitionSystemEncoding};
use libpatron::sim::interpreter::{InitKind, InitValueGenerator, ValueRef};
use num_bigint::BigUint;
use std::collections::HashMap;

pub type Result<T> = std::io::Result<T>;

// TODO: make Word in libpatron public
pub type Word = u64;

pub type StepInt = u64;

pub struct Testbench {
    /// contains for each time step: inputs, then outputs
    data: Vec<Word>,
    step_words: usize,
    ios: Vec<IOInfo>,
    /// signals to print for debugging
    signals_to_print: Vec<(String, ExprRef)>,
    missing_outputs: Vec<IOInfo>,
}

#[derive(Debug, Clone)]
struct IOInfo {
    expr: ExprRef,
    cell_id: usize,
    words: usize,
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
        let name_to_ref = sys.generate_name_to_ref(ctx);
        let mut ios = read_header(&header_tokens, &name_to_ref, ctx, sys, verbose)?;

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

        // derive data layout
        let step_words = ios.iter().map(|io| io.words).sum::<usize>();

        // generate signals to print if we are instructed to do so
        let mut signals_to_print = vec![];
        if verbose && trace_sim {
            for state in sys.states() {
                let expr = state.symbol;
                let name = expr.get_symbol_name(ctx).unwrap();
                if !classify_state(name).is_synth_var() && expr.get_type(ctx).is_bit_vector() {
                    signals_to_print.push((name.to_string(), expr));
                }
            }
            signals_to_print.sort_by_key(|(name, _)| name.clone());
        }

        let tb = Self {
            data,
            step_words,
            ios,
            signals_to_print,
            missing_outputs,
        };
        Ok(tb)
    }

    pub fn has_missing_outputs(&self) -> bool {
        !self.missing_outputs.is_empty()
    }

    /// Replaces all X assignments to inputs with a random or zero value.
    pub fn define_inputs(&mut self, kind: InitKind) {
        let mut gen = InitValueGenerator::from_kind(kind);
        for step_id in 0..self.step_count() {
            let range = self.step_range(step_id);
            let words = &mut self.data[range];
            let mut offset = 0;
            for io in self.ios.iter() {
                if io.is_input {
                    let io_words = &mut words[offset..(offset + io.words)];
                    if is_x(io_words) {
                        let data_words = &mut io_words[0..width_to_words(io.width)];
                        gen.assign(data_words, io.width, 1);
                    }
                }
                offset += io.words;
            }
        }
    }

    fn step_range(&self, step_id: StepInt) -> std::ops::Range<usize> {
        let usize_id = step_id as usize;
        (usize_id * self.step_words)..((usize_id + 1) * self.step_words)
    }

    pub fn step_count(&self) -> StepInt {
        self.data.len() as StepInt / self.step_words as StepInt
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
        words: &[Word],
        failures: &mut Vec<Failure>,
        verbose: bool,
    ) {
        // apply inputs
        let mut offset = 0;
        for io in self.ios.iter() {
            if io.is_input {
                let io_words = &words[offset..(offset + io.words)];
                if !is_x(io_words) {
                    let non_x_num_words = width_to_words(io.width);
                    let non_x_words = &io_words[0..non_x_num_words];
                    sim.set(io.expr, ValueRef::new(non_x_words, io.width));
                }
            }
            offset += io.words;
        }

        // calculate the output values
        sim.update();

        // print values if the option is enables
        if !self.signals_to_print.is_empty() {
            println!();
            for (name, expr) in self.signals_to_print.iter() {
                if let Some(value_ref) = sim.get(*expr) {
                    let value = value_ref.to_bit_string();
                    println!("{name}@{step_id} = {value}")
                }
            }
        }

        // check outputs
        let mut offset = 0;
        for io in self.ios.iter() {
            if !io.is_input {
                let io_words = &words[offset..(offset + io.words)];
                if !is_x(io_words) {
                    let actual_value = sim.get(io.expr).unwrap();
                    let non_x_num_words = width_to_words(io.width);
                    let non_x_words = &io_words[0..non_x_num_words];
                    let expected_value = ValueRef::new(non_x_words, io.width);
                    if expected_value != actual_value {
                        failures.push(Failure {
                            step: step_id,
                            signal: io.expr,
                        });
                        if verbose {
                            println!(
                                "{}@{step_id}: {} vs. {} (E/A)",
                                io.name,
                                expected_value.to_bit_string(),
                                actual_value.to_bit_string()
                            );
                        }
                    }
                }
            }
            offset += io.words;
        }
    }

    pub fn apply_constraints(
        &self,
        ctx: &Context,
        smt_ctx: &mut easy_smt::Context,
        enc: &impl TransitionSystemEncoding,
        start_step: StepInt,
        end_step: StepInt,
    ) -> std::io::Result<()> {
        for step_id in start_step..(end_step + 1) {
            let range = self.step_range(step_id);
            let words = &self.data[range];

            // apply all io constraints in this step
            let mut offset = 0;
            for io in self.ios.iter() {
                let io_words = &words[offset..(offset + io.words)];
                if !is_x(io_words) {
                    let non_x_num_words = width_to_words(io.width);
                    let non_x_words = &io_words[0..non_x_num_words];
                    let value = ValueRef::new(non_x_words, io.width).to_bit_string();
                    let value_expr = bit_string_to_smt(smt_ctx, &value);
                    let io_at_step = enc.get_at(ctx, smt_ctx, io.expr, step_id);
                    smt_ctx.assert(smt_ctx.eq(io_at_step, value_expr))?;
                }
                offset += io.words;
            }
        }
        Ok(())
    }
}

fn is_x(words: &[Word]) -> bool {
    words.iter().all(|w| *w == Word::MAX)
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
    for (sys_io, sys_io_info) in sys.get_signals(|s| s.is_input() || s.is_output()) {
        let included = ios.iter().any(|i| i.expr == sys_io);
        if !included {
            let name = sys_io
                .get_symbol_name(ctx)
                .unwrap_or_else(|| ctx.get(sys_io_info.name.unwrap()));
            if name != CHANGE_COUNT_OUTPUT_NAME {
                let width = sys_io.get_bv_type(ctx).unwrap();

                if verbose {
                    let tpe = if sys_io_info.is_input() {
                        "Input"
                    } else {
                        "Output"
                    };
                    println!("{tpe} `{name}` : bv<{width}> is missing from the testbench.");
                }
                out.push(IOInfo {
                    expr: sys_io,
                    cell_id: usize::MAX,
                    words: width_to_words(width + 1), // one extra bit to indicate X
                    width,
                    is_input: sys_io_info.is_input(),
                    name: name.to_string(),
                })
            }
        }
    }
    out
}

fn read_body(header_len: usize, mmap: memmap2::Mmap, ios: &[IOInfo]) -> Vec<Word> {
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
                    push_x(io, &mut data);
                } else {
                    let cell = tokens[io.cell_id];
                    if is_cell_x(cell) {
                        push_x(io, &mut data);
                    } else {
                        push_from_dec(io, &mut data, cell);
                    }
                }
            }
        }
    }
    data
}

fn push_x(io: &IOInfo, data: &mut Vec<Word>) {
    for _ in 0..io.words {
        data.push(Word::MAX);
    }
}

fn dec_cell_to_big_uint(cell: &[u8]) -> Option<BigUint> {
    let digits = cell.iter().map(|d| d - b'0').collect::<Vec<_>>();
    BigUint::from_radix_be(&digits, 10)
}

fn push_from_dec(io: &IOInfo, data: &mut Vec<Word>, dec_ascii: &[u8]) {
    let big = dec_cell_to_big_uint(dec_ascii).expect("Failed to parse cell data!");
    let mut word_count = 0;
    for digit in big.iter_u64_digits() {
        data.push(digit);
        word_count += 1;
    }
    debug_assert!(word_count <= io.words);
    // msb zeros
    for _ in word_count..io.words {
        data.push(0);
    }
}

fn read_header(
    tokens: &[&[u8]],
    name_to_ref: &HashMap<String, ExprRef>,
    ctx: &Context,
    sys: &TransitionSystem,
    verbose: bool,
) -> std::io::Result<Vec<IOInfo>> {
    let mut out = Vec::new();
    for (cell_id, cell) in tokens.iter().enumerate() {
        let name = String::from_utf8_lossy(cell);
        if let Some(signal_ref) = name_to_ref.get(name.as_ref()) {
            let signal = sys.get_signal(*signal_ref).unwrap();
            let is_io = signal.is_input() || signal.is_output();
            if signal.is_input() && signal.is_output() {
                todo!("deal correctly with signals that are both, input and output");
            }
            if is_io {
                let width = signal_ref.get_bv_type(ctx).unwrap();
                out.push(IOInfo {
                    expr: *signal_ref,
                    cell_id,
                    words: width_to_words(width + 1), // one extra bit to indicate X
                    width,
                    is_input: signal.kind == SignalKind::Input,
                    name: name.to_string(),
                })
            } else if verbose {
                println!("Ignoring column {name}.");
            }
        }
    }
    Ok(out)
}

fn width_to_words(width: WidthInt) -> usize {
    (width).div_ceil(Word::BITS) as usize
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

// debug function
#[allow(dead_code)]
pub fn print_states(ctx: &Context, sys: &TransitionSystem, sim: &impl Simulator) {
    for state in sys.states() {
        if state.symbol.get_type(ctx).is_bit_vector() {
            let value_ref = sim.get(state.symbol).unwrap();
            let value = value_ref.to_bit_string();
            let name = state.symbol.get_symbol_name(ctx).unwrap();
            if !classify_state(name).is_synth_var() {
                println!("{name} = {value}")
            }
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
    use num_traits::ToPrimitive;

    #[test]
    fn test_trim() {
        assert_eq!(trim(b"1234"), b"1234");
        assert_eq!(trim(b" 1234"), b"1234");
        assert_eq!(trim(b"1234  "), b"1234");
        assert_eq!(trim(b"   1234   "), b"1234");
        assert_eq!(trim(b"   12 34   "), b"12 34");
        assert_eq!(trim(b"   12  34   "), b"12  34");
    }

    #[test]
    fn test_big_uint_parse() {
        let inp = b"13476";
        let big = dec_cell_to_big_uint(inp).unwrap();
        assert_eq!(big.to_u64().unwrap(), 13476);
    }
}
