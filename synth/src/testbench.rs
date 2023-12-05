// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use libpatron::ir::*;
use std::collections::HashMap;

pub type Result<T> = std::io::Result<T>;

pub struct Testbench {
    mmap: memmap2::Mmap,
    header_len: usize, // length of the first line of the CSV
    inputs: IOInfo,
    outputs: IOInfo,
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
        let tb = Self {
            mmap,
            header_len,
            inputs,
            outputs,
        };
        Ok(tb)
    }
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
    let start = data
        .iter()
        .position(|c| !is_whitespace(*c))
        .unwrap_or(data.len());
    if start == data.len() {
        return &[];
    }
    let end = data.iter().rev().position(|c| !is_whitespace(*c)).unwrap();
    &data[start..end]
}

#[inline]
fn is_whitespace(c: u8) -> bool {
    matches!(c, b' ')
}
