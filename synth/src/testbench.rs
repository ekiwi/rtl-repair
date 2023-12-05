// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use libpatron::ir::*;
use libpatron::mc::Simulator;
use libpatron::sim::interpreter::InitKind;
use num_bigint::BigUint;
use std::collections::HashMap;

pub type Result<T> = std::io::Result<T>;

pub struct Testbench {
    mmap: memmap2::Mmap,
    header_len: usize, // length of the first line of the CSV
    inputs: IOInfo,
    outputs: IOInfo,
    signals_to_print: Vec<(String, ExprRef)>,
}

pub struct RunResult {
    pub first_fail_at: Option<u64>,
}

struct Failure {
    step: u64,
    signal: ExprRef,
}

impl RunResult {
    pub fn is_success(&self) -> bool {
        self.first_fail_at.is_none()
    }
}

pub struct RunConfig {
    pub stop: StopAt,
}

pub enum StopAt {
    FirstFail,
    End,
}

impl Testbench {
    pub fn load(ctx: &Context, sys: &TransitionSystem, filename: &str) -> Result<Self> {
        // memory map file
        let input_file = std::fs::File::open(filename)?;
        let mmap = unsafe { memmap2::Mmap::map(&input_file).expect("failed to memory map file") };

        // read header to find I/O mapping
        let mut header_tokens = Vec::new();
        let header_len = parse_line(&mmap, &mut header_tokens);
        let name_to_ref = sys.generate_name_to_ref(&ctx);
        let (inputs, outputs) = read_header(&header_tokens, &name_to_ref, sys)?;

        // assembly testbench
        let signals_to_print = vec![];
        let tb = Self {
            mmap,
            header_len,
            inputs,
            outputs,
            signals_to_print,
        };
        Ok(tb)
    }

    pub fn run(&self, sim: &mut impl Simulator, conf: &RunConfig) -> RunResult {
        let mut failures = Vec::new();

        // make sure we start from the starting state
        sim.init(InitKind::Zero);

        let mut pos = self.header_len;
        let mut tokens = Vec::with_capacity(32);
        let mut step_id = 0;
        while pos < self.mmap.len() {
            tokens.clear();
            pos += parse_line(&self.mmap[pos..], &mut tokens);
            assert!(!tokens.is_empty());
            self.do_step(step_id, sim, tokens.as_slice(), &mut failures);

            // early exit
            if !failures.is_empty() && matches!(conf.stop, StopAt::FirstFail) {
                return RunResult {
                    first_fail_at: Some(step_id),
                };
            }

            step_id += 1;
        }
        // success
        RunResult {
            first_fail_at: None,
        }
    }

    fn do_step(
        &self,
        step_id: u64,
        sim: &mut impl Simulator,
        tokens: &[&[u8]],
        failures: &mut Vec<Failure>,
    ) {
        // apply inputs
        let mut input_iter = self.inputs.iter();
        if let Some(mut input) = input_iter.next() {
            for (cell_id, cell) in tokens.iter().enumerate() {
                if cell_id == input.0 {
                    // apply input
                    if !is_x(cell) {
                        let value =
                            u64::from_str_radix(&String::from_utf8_lossy(cell), 10).unwrap();
                        sim.set(input.1, value);
                    }

                    // get next input
                    if let Some(next_input) = input_iter.next() {
                        input = next_input;
                    } else {
                        break;
                    }
                }
            }
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
        let mut output_iter = self.outputs.iter();
        if let Some(mut output) = output_iter.next() {
            for (cell_id, cell) in tokens.iter().enumerate() {
                if cell_id == output.0 {
                    // apply input
                    if !is_x(cell) {
                        if let Ok(expected) =
                            u64::from_str_radix(&String::from_utf8_lossy(cell), 10)
                        {
                            let actual = sim.get(output.1).unwrap().to_u64().unwrap();
                            if expected != actual {
                                failures.push(Failure {
                                    step: step_id,
                                    signal: output.1,
                                })
                                // assert_eq!(expected, actual, "{}@{step_id}", output.2);
                            }
                        } else {
                            let expected = BigUint::from_radix_be(cell, 10).unwrap();
                            let actual = sim.get(output.1).unwrap().to_big_uint();
                            if expected != actual {
                                failures.push(Failure {
                                    step: step_id,
                                    signal: output.1,
                                })
                                // assert_eq!(expected, actual, "{}@{step_id}", output.2);
                            }
                        }
                    }

                    // get next output
                    if let Some(next_output) = output_iter.next() {
                        output = next_output;
                    } else {
                        break;
                    }
                }
            }
        }

        // advance simulation
        sim.step();
    }
}

fn is_x(token: &[u8]) -> bool {
    matches!(token, b"x" | b"X")
}

type IOInfo = Vec<(usize, ExprRef, String)>;

fn read_header(
    tokens: &[&[u8]],
    name_to_ref: &HashMap<String, ExprRef>,
    sys: &TransitionSystem,
) -> std::io::Result<(IOInfo, IOInfo)> {
    let mut inputs = Vec::new();
    let mut outputs = Vec::new();
    for (cell_id, cell) in tokens.iter().enumerate() {
        let name = String::from_utf8_lossy(cell);
        if let Some(signal_ref) = name_to_ref.get(name.as_ref()) {
            let signal = sys.get_signal(*signal_ref).unwrap();
            match signal.kind {
                SignalKind::Input => inputs.push((cell_id, *signal_ref, name.to_string())),
                SignalKind::Output => outputs.push((cell_id, *signal_ref, name.to_string())),
                _ => {} // ignore
            }
        }
    }
    Ok((inputs, outputs))
}

fn parse_line<'a>(data: &'a [u8], out: &mut Vec<&'a [u8]>) -> usize {
    assert!(out.is_empty());
    let mut token_start = 0usize;
    for (offset, bb) in data.iter().enumerate() {
        match bb {
            b'\n' => {
                out.push(trim(&data[token_start..offset]));
                return offset + 1;
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
            let out = &data[start..end];
            out
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
