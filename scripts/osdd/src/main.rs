// Copyright 2022-2024 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

use clap::Parser;
use std::io::BufRead;
use wellen::*;
#[derive(Parser, Debug)]
#[command(name = "osdd")]
#[command(author = "Kevin Laeufer <laeufer@berkeley.edu>")]
#[command(version)]
#[command(about = "Calculates the OSDD.", long_about = None)]
struct Args {
    #[arg(long)]
    gt_wave: String,
    #[arg(long)]
    buggy_wave: String,
    #[arg(long)]
    signals: String,
}

fn fixup_signal_name(name: &str) -> Option<String> {
    // [ ] indicates an array value and these are not included in the VCS
    if name.contains('[') && name.contains(']') {
        None
    } else {
        Some(name.trim().to_string())
    }
}

fn load_signal_names(filename: &str) -> (Vec<String>, Vec<String>) {
    let file = std::fs::File::open(filename).expect("failed to open signal file.");
    let mut reader = std::io::BufReader::new(file);
    let mut state_line = String::new();
    reader
        .read_line(&mut state_line)
        .expect("failed to read states");
    let states: Vec<_> = state_line.split(',').flat_map(fixup_signal_name).collect();
    let mut output_line = String::new();
    reader
        .read_line(&mut output_line)
        .expect("failed to read outputs");
    let outputs: Vec<_> = output_line.split(',').flat_map(fixup_signal_name).collect();
    (states, outputs)
}

// filter out states which do not exist in the original design
fn filter_states(h: &Hierarchy, prefix: &str, states: &mut Vec<String>) {
    states.retain(|name| lookup_var(h, prefix, name.as_str()).is_some());
}

#[inline]
fn lookup_var(h: &Hierarchy, prefix: &str, name: &str) -> Option<VarRef> {
    let full_name = format!("{prefix}.{name}");
    let parts: Vec<_> = full_name.split('.').collect();
    h.lookup_var(&parts[..parts.len() - 1], parts.last().unwrap())
}

fn find_dut_name(h: &Hierarchy) -> String {
    let top = h.first_scope().expect("failed to open testbench scope");
    let dut = h.get(top.scopes(h).next().expect("failed to open dut scope"));
    assert!(
        dut.vars(h).next().is_some(),
        "dut vars are empty! {}",
        dut.full_name(h)
    );
    dut.full_name(h)
}

fn find_clock(h: &Hierarchy, dut: &str) -> Option<SignalRef> {
    let parts: Vec<_> = dut.split('.').collect();
    let scope = h.get(
        h.lookup_scope(&parts)
            .unwrap_or_else(|| panic!("failed to open scope {dut}!")),
    );
    for var_ref in scope.vars(h) {
        let var = h.get(var_ref);
        let name = var.name(h);
        if name == "clock" || name == "clk" {
            return Some(var.signal_ref());
        }
    }

    // if we could not find anything here, we search other scopes
    for scope_ref in scope.scopes(h) {
        let scope = h.get(scope_ref);
        let name = scope.full_name(h);
        let res = find_clock(h, &name);
        if res.is_some() {
            return res;
        }
    }

    None
}

fn create_signal_map(h: &Hierarchy, signals: &[String], prefix: &str) -> Vec<SignalRef> {
    signals
        .iter()
        .map(|name| {
            let full_name = format!("{prefix}.{name}");
            let parts: Vec<_> = full_name.split('.').collect();
            let var = match h.lookup_var(&parts[..parts.len() - 1], parts.last().unwrap()) {
                Some(var) => var,
                None => panic!("Failed to find {}", full_name),
            };
            h.get(var).signal_ref()
        })
        .collect()
}

/// we sample at the falling edge
fn find_sample_points(clock: &Signal) -> Vec<TimeTableIdx> {
    let mut prev = None;
    let mut sample_points = Vec::new();
    for (time_idx, value) in clock.iter_changes() {
        let next = match value.to_bit_string().unwrap().as_str() {
            "0" => Some(0u8),
            "1" => Some(1u8),
            "x" => None,
            other => panic!("unexpected clock value: {other}"),
        };
        if time_idx > 0 {
            let negedge = matches!((prev, next), (Some(1), Some(0)));
            let posedge = matches!((prev, next), (Some(0), Some(1)));

            // we sample one timestep after the rising edge
            if posedge {
                sample_points.push(time_idx + 1);
            }

            // TODO: it might make more sense to sample at the falling edge!
        }
        prev = next;
    }

    sample_points
}

fn get_value(waveform: &Waveform, signal: &SignalRef, idx: TimeTableIdx) -> String {
    let signal = waveform.get_signal(*signal).unwrap();
    let offset = signal.get_offset(idx).unwrap();
    signal
        .get_value_at(&offset, offset.elements - 1)
        .to_bit_string()
        .unwrap()
}

struct Disagreement {
    index: usize,
    expected: String,
    actual: String,
}

fn compare_signals(
    gt_wave: &Waveform,
    gt_idx: TimeTableIdx,
    gts: &[SignalRef],
    buggy_wave: &Waveform,
    buggy_idx: TimeTableIdx,
    buggys: &[SignalRef],
) -> Vec<Disagreement> {
    let mut out = Vec::new();

    for (index, (gt, buggy)) in gts.iter().zip(buggys.iter()).enumerate() {
        let expected = get_value(gt_wave, gt, gt_idx);
        let actual = get_value(&buggy_wave, buggy, buggy_idx);
        let gt_is_x = expected.contains('x');
        if !gt_is_x {
            if expected != actual {
                out.push(Disagreement {
                    index,
                    expected,
                    actual,
                });
            }
        }
    }

    out
}

fn main() {
    let args = Args::parse();

    // load signal names
    let (mut states, outputs) = load_signal_names(&args.signals);

    // load waves
    let mut gt_wave = vcd::read(&args.gt_wave).expect("failed to load ground truth VCD");
    let mut buggy_wave = vcd::read(&args.buggy_wave).expect("failed to load buggy VCD");

    let dut_path = find_dut_name(gt_wave.hierarchy());

    // filter out states which do not exist in the VCD of the original design
    // this addresses the issue of VCS not including memories
    filter_states(gt_wave.hierarchy(), &dut_path, &mut states);

    // sanity check
    assert_eq!(*gt_wave.time_table().first().unwrap(), 0);
    assert_eq!(*buggy_wave.time_table().first().unwrap(), 0);

    // map signals
    let gt_states = create_signal_map(gt_wave.hierarchy(), &states, &dut_path);
    let gt_outputs = create_signal_map(gt_wave.hierarchy(), &outputs, &dut_path);
    let buggy_states = create_signal_map(buggy_wave.hierarchy(), &states, &dut_path);
    let buggy_outputs = create_signal_map(buggy_wave.hierarchy(), &outputs, &dut_path);

    // find clocks and clock edges
    let gt_clock = find_clock(gt_wave.hierarchy(), &dut_path)
        .expect("failed to find clock signal in ground truth");
    gt_wave.load_signals(&[gt_clock]);
    let gt_sample_indices = find_sample_points(gt_wave.get_signal(gt_clock).unwrap());
    let ground_truth_testbench_cycles = gt_sample_indices.len() as u64;
    let buggy_clock = find_clock(buggy_wave.hierarchy(), &dut_path)
        .expect("failed to find clock signal in buggy design");
    buggy_wave.load_signals(&[buggy_clock]);
    let buggy_sample_indices = find_sample_points(buggy_wave.get_signal(buggy_clock).unwrap());

    // load signals
    gt_wave.load_signals(&gt_states);
    gt_wave.load_signals(&gt_outputs);
    buggy_wave.load_signals(&buggy_states);
    buggy_wave.load_signals(&buggy_outputs);

    // compare signals
    let mut first_state_div = None;
    let mut first_out_div = None;
    for (cycle, (gt_idx, buggy_idx)) in gt_sample_indices
        .iter()
        .zip(buggy_sample_indices.iter())
        .enumerate()
    {
        let out_div = compare_signals(
            &gt_wave,
            *gt_idx,
            &gt_outputs,
            &buggy_wave,
            *buggy_idx,
            &buggy_outputs,
        );
        let state_div = compare_signals(
            &gt_wave,
            *gt_idx,
            &gt_states,
            &buggy_wave,
            *buggy_idx,
            &buggy_states,
        );

        if first_out_div.is_none() && !out_div.is_empty() {
            first_out_div = Some(cycle);
        }
        if first_state_div.is_none() && !state_div.is_empty() {
            first_state_div = Some(cycle);
        }

        // early exit once we have all we are interested in
        if first_out_div.is_some() {
            break;
        }
    }

    // println!("first_state_div={first_state_div:?}");
    // println!("first_out_div={first_out_div:?}");

    let res = format!(
        "{}, {}",
        first_state_div
            .map(|v| format!("{v}"))
            .unwrap_or("-1".to_string()),
        first_out_div
            .map(|v| format!("{v}"))
            .unwrap_or("-1".to_string())
    );
    println!("{res}");
}
