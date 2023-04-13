#!/usr/bin/env python3
# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


import argparse
from dataclasses import dataclass
from pathlib import Path
import vcdvcd
import tempfile
import typing

from benchmarks import Benchmark, load_project, get_benchmark, get_benchmark_design
from find_state import find_state_and_outputs

@dataclass
class Config:
    working_dir: Path
    benchmark: Benchmark
    logfile: Path

def assert_exists(filename: Path):
    assert filename.exists(), f"{filename} ({filename.resolve()}) does not exist!"

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Calculate output / state divergence delta')
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory. Should contain the output from `generate_vcd_traces.py`', required=True)
    parser.add_argument('--project', help='Project TOML', required=True)
    parser.add_argument('--bug', help='Bug name.', required=True)
    parser.add_argument('--log', dest='logfile', help='File to log to.')

    args = parser.parse_args()
    logfile = None if args.logfile is None else Path(args.logfile)
    project = load_project(Path(args.project))
    benchmark = get_benchmark(project, args.bug)
    conf =  Config(Path(args.working_dir), benchmark, logfile)

    assert_exists(conf.working_dir)
    return conf

@dataclass
class Disagreement:
    step: int
    signal: str
    external: bool
    expected: str
    actual: str

_logfile: typing.Optional[typing.TextIO] = None
def info(msg: str):
    if _logfile is None:
        print(msg)
    else:
        _logfile.write(msg + "\n")
def start_logger(logfile: typing.Optional[Path]):
    global _logfile
    if logfile is not None:
        _logfile = open(logfile, "w")
def end_logger():
    global _logfile
    if _logfile is not None:
        _logfile.close()


def find_clock(names: list) -> str:
    candidates = ["clock", "clk"]
    # sort names from shortest to longest
    names = sorted(names, key = lambda n: len(n))
    # check to see if the name could be a clock
    for name in names:
        suffix = name.split('.')[-1]
        if suffix.strip().lower() in candidates:
            return name
    raise RuntimeError(f"Failed to find clock among signals: {names}")


class VCDConverter(vcdvcd.StreamParserCallbacks):
    def __init__(self, out: typing.TextIO, interesting_signals: set):
        super().__init__()
        self.out = out
        self.interesting_signals: set = interesting_signals
        self.signals = dict()
        self.id_to_index = dict()
        self.values = []
        self.clock = None
        self.clock_id = None
        self.sample_at = None

    def enddefinitions(self, vcd, signals, cur_sig_vals):
        # convert references to list and sort by name
        refs = [ (k,v) for k,v in vcd.references_to_ids.items() ]
        refs = sorted(refs, key=lambda e: e[0])
        self.id_to_index = { e[1]: i for i,e  in enumerate(refs) }
        self.values = ["x"] * len(refs)
        names = [e[0] for e in refs]
        info(f"Found {len(refs)} signals")
        self.clock = find_clock(names)
        self.clock_id = vcd.references_to_ids[self.clock]
        clock_index = self.id_to_index[self.clock_id]
        info(f"{clock_index=} {len(self.values)=}")
        self.values[clock_index] = "0"
        header = ', '.join(names)
        self.out.write(header + '\n')

    def write_to_file(self, time):
        if self.sample_at is None: return
        # at the next timestep after a rising edge, we need to write all samples to disk
        if time > self.sample_at:
            self.sample_at = None
            line = ', '.join(f"{v}" for v in self.values)
            self.out.write(line + "\n")

    def value(self, vcd, time, value, identifier_code, cur_sig_vals):
        # dump values if appropriate
        self.write_to_file(time)

        index = self.id_to_index[identifier_code]

        # detect rising edge on the clock
        if identifier_code == self.clock_id:
            rising_edge = self.values[index] == "0" and value == "1"
            if rising_edge:
                self.sample_at = time

        # update values
        self.values[self.id_to_index[identifier_code]] = value


def vcd_to_csv(working_dir: Path, interesting_signals: set, vcd_path: Path):
    assert_exists(working_dir)
    assert working_dir.is_dir(), f"{working_dir} is not a directory!"
    csv_file = tempfile.TemporaryFile(mode='wt', dir=working_dir)
    vcdvcd.VCDVCD(str(vcd_path.resolve()), callbacks=VCDConverter(csv_file, interesting_signals), store_tvs=False)
    csv_file.seek(0)
    return csv_file

def get_signal_names(testbench: Path) -> list:
    with open(testbench, 'r') as f:
        header = f.readline()
    return parse_csv_line(header)

def parse_csv_line(line: str) -> list:
    return [n.strip() for n in line.split(',')]

def find_str_prefix(aa: str, bb: str) -> str:
    prefix = ''
    for a, b in zip(aa, bb):
        if a == b:
            prefix += a
        else:
            return prefix
    return prefix

def find_prefix(ll: list) -> str:
    if len(ll) < 1: return ""
    prefix = ll[0]
    for entry in ll[1:]:
        if not entry.startswith(prefix):
            prefix = find_str_prefix(prefix, entry)
            if len(prefix) == 0:
                return prefix
    return prefix

def normalize_signals(signals: list) -> list:
    # remove any common prefix
    prefix = find_prefix(signals)
    if not prefix.endswith('.'):
        prefix = '.'.join(prefix.split('.')[:-1]) + '.'
    prefix_len = len(prefix)
    signals = [s[prefix_len:] for s in signals]

    # remove any bit width specifiers
    signals = [s.split('[')[0] for s in signals]

    return signals


def do_skip(values: list, skip: list) -> list:
    assert len(values) == len(skip)
    return [v for v,s in zip(values, skip) if not s]

def compare_line(ii: int, original: list, buggy: list, signals: list, externals: set) -> list:
    disagree = []
    for ((o, b), name) in zip(zip(original, buggy), signals):
        if o.lower() == 'x': # no constraint!
            continue
        if o.lower() != b.lower():
            disagree.append(Disagreement(ii, name, name in externals, o.lower(), b.lower()))
    return disagree

def create_skip_lists(signals: list, buggy_signals: list):
    in_a = set(signals)
    in_b = set(buggy_signals)
    skip_a = [s not in in_b for s in signals]
    skip_b = [s not in in_a for s in buggy_signals]
    common = [s for s in signals if s in in_b]
    return common, skip_a, skip_b



def compare(original: typing.TextIO, buggy: typing.TextIO, external: list):
    original_signals = parse_csv_line(original.readline())
    buggy_signals = parse_csv_line(buggy.readline())
    signals, skip_o, skip_b = create_skip_lists(original_signals, buggy_signals)
    signals = normalize_signals(signals)
    is_external = set(external)

    # is there any value we need to skip?
    need_to_skip = max(skip_o) or max(skip_b)

    # check to see if there are any internal signals
    internal_signals = [s for s in signals if not s in is_external]
    info(f"all signals: {signals}")
    info(f"external signals: {external}")
    info(f"internal signals: {internal_signals}")

    # iterate over lines together
    ii = 0

    first_internal_disagreement = -1
    first_external_disagreement = -1


    for o_line, b_line in zip(original, buggy):
        o = parse_csv_line(o_line)
        b = parse_csv_line(b_line)
        if need_to_skip:
            o = do_skip(o, skip_o)
            b = do_skip(b, skip_b)
        disagree = compare_line(ii, o, b, signals, is_external)
        if first_internal_disagreement == -1 and len(disagree) > 0:
            first_internal_disagreement = ii
        for d in disagree:
            if d.external:
                first_external_disagreement = ii
            ext = " (E)" if d.external else ""
            info(f"{d.signal}@{d.step}: {d.actual} != {d.expected}{ext}")

        # early exit for when we find the first external divergence
        if first_external_disagreement > -1:
            break
        ii += 1

    return first_internal_disagreement, first_external_disagreement


def write_output(conf: Config, osdd: int):
    print(f"TODO: OSDD = {osdd}")

def main():
    conf = parse_args()


    # extract state and outputs from ground truth design
    gt_design = conf.benchmark.project.design
    gt_states, gt_outputs = find_state_and_outputs(conf.working_dir, gt_design)

    # extract state and outputs from buggy design
    buggy_design = get_benchmark_design(conf.benchmark)
    buggy_states, buggy_outputs = find_state_and_outputs(conf.working_dir, buggy_design)


    # if there is no state in the design, OSDD is always 0
    gt_no_state, buggy_no_state = len(gt_states) == 0, len(buggy_states) == 0
    if gt_no_state and buggy_no_state:
        return write_output(conf, osdd=0)
    elif gt_no_state or buggy_no_state:
        raise NotImplementedError("TODO: what happens if only one of the designs has state?")

    # compare states, see if they are the same
    if not gt_states == buggy_states:
        raise NotImplementedError(f"TODO: states are not the same!\nground-truth: {gt_states}\nbuggy: {buggy_states}")

    # display warning if outputs are not the same
    if not gt_outputs == buggy_outputs:
        print(f"WARN: outputs are not the same")
        print(f"Missing in buggy: {list(set(gt_outputs) - set(buggy_outputs))}")
        print(f"Additional in buggy: {list(set(buggy_outputs) - set(gt_outputs))}")

    # we are only interested in signals that are contained in both circuits, but the widths are allowed to differ
    gt_signals = [n for n, _ in gt_states] + [n for n, _ in gt_outputs]
    buggy_signals = [n for n, _ in buggy_states] + [n for n, _ in buggy_outputs]
    interesting_signals = sorted(list(set(gt_signals) & set(buggy_signals)))

    # VCD names used in the `generate_vcd_traces.py` script
    gt_vcd = conf.working_dir / f"{conf.benchmark.project.name}.groundtruth.vcd"
    buggy_vcd = conf.working_dir / f"{conf.benchmark.project.name}.{conf.benchmark.bug.name}.vcd"
    assert_exists(gt_vcd)
    assert_exists(buggy_vcd)

    # look at the VCDs now
    start_logger(conf.logfile)

    # convert VCD files into CSV tables for easier (line-by-line) comparison
    gt_csv = vcd_to_csv(conf.working_dir, interesting_signals, gt_vcd)
    buggy_csv = vcd_to_csv(conf.working_dir, interesting_signals, buggy_vcd)

    # debug code to print out CSV
    #print(original_vcd.read())
    #original_vcd.seek(0)

    # do the comparison
    (first_internal, first_external)  = compare(original_vcd, buggy_vcd, external_signals)

    if first_internal == -1:
        print("no disagreements found")

    else:
        assert first_internal <= first_external

        print(f"first internal divergence: {first_internal}")
        print(f"first external divergence: {first_external}")
        print(f"delta: {first_external - first_internal}")

    # release resources
    end_logger()
    gt_csv.close()
    buggy_csv.close()



if __name__ == '__main__':
    main()