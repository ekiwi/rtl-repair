#!/usr/bin/env python3
# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
from dataclasses import dataclass
from pathlib import Path
import vcdvcd
import typing

import benchmarks
from benchmarks import Benchmark, load_project, get_benchmark, get_benchmark_design
from find_state import find_state_and_outputs


# list of benchmarks that are out of scope for this metric since they are non synthesizable
out_of_scope = {
    ('first_counter_overflow', 'wadden_buggy1'): "missing posedge",
    ('lshift_reg', 'kgoliya_buggy1'): "posedge changed to negedge",
    ('i2c_slave', 'wadden_buggy1'): "non-synthesizable testbench model",
    ('i2c_slave', 'wadden_buggy2'): "non-synthesizable testbench model",
    ('mux_4_1', 'wadden_buggy1'): "buggy design has a latch, but no clock that we can use to sample",
    ('mux_4_1', 'wadden_buggy2'): "buggy design has a latch, but no clock that we can use to sample",
}

@dataclass
class Config:
    working_dir: Path
    benchmark: Benchmark

def assert_exists(filename: Path):
    assert filename.exists(), f"{filename} ({filename.resolve()}) does not exist!"

@dataclass
class Disagreement:
    step: int
    signal: str
    is_state: bool
    is_output: bool
    expected: str
    actual: str


@dataclass
class Result:
    project: str
    bug: str
    delta: int
    first_output_disagreement: int
    notes: str

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


def remove_size_from_name(name: str) -> str:
    """ changes e.g. "state[2:0]" to "state" """
    return name.split('[')[0]


def find_str_prefix(aa: str, bb: str) -> str:
    prefix = ''
    for a, b in zip(aa, bb):
        if a == b:
            prefix += a
        else:
            return prefix
    return prefix


def find_common_prefix(names: list) -> str:
    prefixes = { '.'.join(nn.split('.')[:-1]) for nn in names }
    sorted_prefixes = sorted(list(prefixes), key = lambda n: len(n))
    prefix = sorted_prefixes[0]
    for entry in sorted_prefixes[1:]:
        if not entry.startswith(prefix):
            prefix = find_str_prefix(prefix, entry)
            if len(prefix) == 0: return "" # early exit (performance optimization)
    return prefix + "."

class EarlyVcdParserExit(Exception):
    pass

class VCDConverter(vcdvcd.StreamParserCallbacks):
    def __init__(self, out: typing.TextIO, interesting_signals: list, max_depth: int = -1):
        super().__init__()
        self.max_depth = max_depth
        self.out = out
        self.interesting_signals: list = interesting_signals
        self.signals = dict()
        self.id_to_index = dict()
        self.values = []
        self.clock = None
        self.clock_id = None
        self.sample_at = None
        self.sample_count = 0

    def enddefinitions(self, vcd, signals, cur_sig_vals):
        # convert references to list and sort by name
        refs = [ (k,v) for k,v in vcd.references_to_ids.items() ]
        refs = sorted(refs, key=lambda e: e[0])
        names = [remove_size_from_name(e[0]) for e in refs]
        info(f"Found {len(refs)} signals")

        # identify clock signal
        self.clock = find_clock(names)
        self.clock_id = vcd.references_to_ids[self.clock]

        # ensure that all interesting signals are in the VCD
        prefix = find_common_prefix(names)
        interesting_with_prefix = [ prefix + ii for ii in self.interesting_signals]
        # are any interesting signals missing from the VCD?
        missing = set(interesting_with_prefix) - set(names)
        if len(missing) > 0:
            # this is normally about Verilog arrays which aren't included in the VCD by default
            print(f"WARN: Interesting signals are missing from the VCD: {list(missing)}.\nAvailable:{names}")
            interesting_with_prefix = [ii for ii in interesting_with_prefix if ii not in missing]

        # we only track the interesting signals
        refs_by_name = { remove_size_from_name(e[0]): e for e in refs }
        refs = [refs_by_name[ii] for ii in interesting_with_prefix]
        refs = [refs_by_name[self.clock]] + refs
        self.id_to_index = { e[1]: i for i,e  in enumerate(refs) }
        self.values = ["x"] * len(refs)
        clock_index = self.id_to_index[self.clock_id]
        info(f"{clock_index=} {len(self.values)=}")
        self.values[clock_index] = "0"

        header = ', '.join(self.interesting_signals)
        self.out.write(header + '\n')
        self.sample_count = 0

    def write_to_file(self, time):
        if self.sample_at is None: return
        # at the next timestep after a rising edge, we need to write all samples to disk
        if time > self.sample_at:
            self.sample_at = None
            # skip clock
            values = self.values[1:]
            line = ', '.join(f"{v}" for v in values)
            self.out.write(line + "\n")
            self.sample_count += 1
            if self.max_depth >= 0 and self.sample_count > self.max_depth:
                raise EarlyVcdParserExit()

    def value(self, vcd, time, value, identifier_code, cur_sig_vals):
        # ignore signals that we are not interested in
        if identifier_code not in self.id_to_index: return

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


def vcd_to_csv(working_dir: Path, interesting_signals: list, vcd_path: Path, max_depth: int = -1):
    assert_exists(working_dir)
    assert working_dir.is_dir(), f"{working_dir} is not a directory!"
    csv_file = open(vcd_path.parent / f"{vcd_path.stem}.csv", 'w+t')
    converter = VCDConverter(csv_file, interesting_signals, max_depth=max_depth)
    try:
        vcdvcd.VCDVCD(str(vcd_path.resolve()), callbacks=converter, store_tvs=False)
    except EarlyVcdParserExit:
        pass # early exits are implemented via an exception, but also part of the normal operation
    csv_file.seek(0)
    return csv_file, converter.sample_count

def get_signal_names(testbench: Path) -> list:
    with open(testbench, 'r') as f:
        header = f.readline()
    return parse_csv_line(header)

def parse_csv_line(line: str) -> list:
    return [n.strip() for n in line.split(',')]

def compare_line(ii: int, original: list, buggy: list, signals: list, is_state: set, is_output: set) -> list:
    disagree = []
    for ((o, b), name) in zip(zip(original, buggy), signals):
        if o.lower() == 'x': # no constraint!
            continue
        if o.lower() != b.lower():
            disagree.append(Disagreement(ii, name, name in is_state, name in is_output, o.lower(), b.lower()))
    return disagree


def compare(original: typing.TextIO, buggy: typing.TextIO, is_state: set, is_output: set):
    original_signals = parse_csv_line(original.readline())
    buggy_signals = parse_csv_line(buggy.readline())
    assert original_signals == buggy_signals, f"{original_signals} != {buggy_signals}"
    signals = original_signals

    # iterate over lines together
    ii = 0

    first_state_disagreement = -1
    first_output_disagreement = -1


    for o_line, b_line in zip(original, buggy):
        o = parse_csv_line(o_line)
        b = parse_csv_line(b_line)
        disagree = compare_line(ii, o, b, signals, is_state, is_output)
        state_disagree = [d for d in disagree if d.is_state]
        output_disagree = [d for d in disagree if d.is_output]
        if first_state_disagreement == -1 and len(state_disagree) > 0:
            first_state_disagreement = ii
        if first_output_disagreement == -1 and len(output_disagree) > 0:
            first_output_disagreement  = ii
        # print info
        for d in disagree:
            if d.is_state and d.is_output: ext = " (O+S)"
            elif d.is_state: ext = " (S)"
            elif d.is_output: ext = " (O)"
            else: ext = ""
            info(f"{d.signal}@{d.step}: {d.actual} != {d.expected}{ext}")

        # early exit for when we find the first external divergence
        if first_output_disagreement > -1:
            break
        ii += 1

    return first_state_disagreement, first_output_disagreement

def common_list(a: list, b: list) -> list:
    return sorted(list(set(a) & set(b)))

def union_list(a: list, b: list) -> list:
    return sorted(list(set(a) | set(b)))

def filer_mem_regs(states: list) -> list:
    """ yosys will generate some registers that serve to hold memory read or write signals, we chose to ignore these here """
    return [st for st in states if '/' not in st[0]]

def compare_traces(conf: Config) -> Result:
    res = Result(project=conf.benchmark.project.name, bug=conf.benchmark.bug.name,
                 delta=-1, first_output_disagreement=-1, notes="")

    # check to see if this is a project where our OSDD metric does not make sense
    if (res.project, res.bug) in out_of_scope:
        res.notes = "OSDD does not apply because " + out_of_scope[(res.project, res.bug)]
        return res

    # extract state and outputs from ground truth design
    gt_design = conf.benchmark.project.design
    gt_states, gt_outputs = find_state_and_outputs(conf.working_dir, gt_design)
    gt_states = filer_mem_regs(gt_states)

    # extract state and outputs from buggy design
    buggy_design = get_benchmark_design(conf.benchmark)
    buggy_states, buggy_outputs = find_state_and_outputs(conf.working_dir, buggy_design)
    buggy_states = filer_mem_regs(buggy_states)


    # if there is no state in the design, OSDD is always 0
    gt_no_state, buggy_no_state = len(gt_states) == 0, len(buggy_states) == 0
    if gt_no_state and buggy_no_state:
        res.delta = 0
        res.notes = "no state => delta=0"
        return res

    # compare states, see if they are the same
    if not gt_states == buggy_states:
        # if the buggy design adds state, we can try to see if (i.e. hope that) the same signal
        # exists in the ground truth design as a signal wire
        # TODO: how is the repair for something like this represented in the synthesized design
        #       with change templates applied?
        only_additional_buggy_states = set(gt_states).issubset(set(buggy_states))
        if only_additional_buggy_states:
            gt_states = buggy_states
        else:
            states_missing_from_buggy = set(gt_states) - set(buggy_states)
            print(f"WARN: states are not the same!\nMissing states in buggy design: {states_missing_from_buggy}")
            buggy_states = gt_states

    # display warning if outputs are not the same
    if not gt_outputs == buggy_outputs:
        print(f"WARN: outputs are not the same")
        print(f"Missing in buggy: {list(set(gt_outputs) - set(buggy_outputs))}")
        print(f"Additional in buggy: {list(set(buggy_outputs) - set(gt_outputs))}")

    # we are only interested in signals that are contained in both circuits, but the widths are allowed to differ
    interesting_states  = common_list([n for n, _ in gt_states], [n for n, _ in buggy_states])
    interesting_outputs = common_list([n for n, _ in gt_outputs], [n for n, _ in buggy_outputs])
    interesting_signals = union_list(interesting_states, interesting_outputs)

    # VCD names used in the `generate_vcd_traces.py` script
    gt_vcd = conf.working_dir / f"{conf.benchmark.project.name}.groundtruth.vcd"
    buggy_vcd = conf.working_dir / f"{conf.benchmark.project.name}.{conf.benchmark.bug.name}.vcd"
    assert_exists(gt_vcd)
    assert_exists(buggy_vcd)

    # derive logfile name from benchmark
    logfile: Path = conf.working_dir / f"{conf.benchmark.project.name}.{conf.benchmark.bug.name}.log"

    # look at the VCDs now
    start_logger(logfile)

    # convert VCD files into CSV tables for easier (line-by-line) comparison
    gt_csv, gt_samples = vcd_to_csv(conf.working_dir, interesting_signals, gt_vcd)
    # sometimes the buggy code runs longer than the ground truth, however there is no reason to sample that far!
    buggy_csv, _ = vcd_to_csv(conf.working_dir, interesting_signals, buggy_vcd, max_depth=gt_samples)

    # debug code to print out CSV
    #print(original_vcd.read())
    #original_vcd.seek(0)

    # do the comparison
    (first_state, first_output)  = compare(original=gt_csv, buggy=buggy_csv,
      is_state=set(interesting_states), is_output=set(interesting_outputs))

    if first_output == -1:
        res.notes = "no disagreement found"
    else:
        assert first_state <= first_output
        res.first_output_disagreement = first_output
        if first_state == -1:
            delta = 0
        else:
            delta = first_output - first_state + 1
        res.delta = delta

    # release resources
    end_logger()
    gt_csv.close()
    buggy_csv.close()
    return res

def print_result(res: Result):
    note = "" if len(res.notes) == 0 else f" ({res.notes})"
    print(f"{res.project}.{res.bug}: failed at {res.first_output_disagreement} w/ osdd={res.delta}{note}")

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Calculate output / state divergence delta')
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory. Should contain the output from `generate_vcd_traces.py`', required=True)
    parser.add_argument('--project', help='Project TOML')
    parser.add_argument('--bug', help='Bug name.')

    args = parser.parse_args()
    if args.project is None:
        benchmark = None
        assert args.bug is None, f"Cannot specify a bug `{args.bug}` without a project!"
    else:
        assert args.bug is not None, f"Need to specify a bug together with the project!"
        project = load_project(Path(args.project))
        benchmark = get_benchmark(project, args.bug)

    conf =  Config(Path(args.working_dir), benchmark)

    assert_exists(conf.working_dir)
    return conf

def diff_all(working_dir: Path):
    print("No project+bug specified, thus we are diffing all CirFix benchmarks.")
    projects = benchmarks.load_all_projects()
    results = []

    for proj in projects.values():
        gt_vcd = working_dir / f"{proj.name}.groundtruth.vcd"
        if not gt_vcd.exists():
            print(f"{gt_vcd} does not exist. Skipping project `{proj.name}`")
            continue
        for bb in benchmarks.get_benchmarks(proj):
            # skip bugs that are not part of the cirfix paper
            if not benchmarks.is_cirfix_paper_benchmark(bb):
                continue
            # check to see if the VCD is available:
            buggy_vcd = working_dir / f"{proj.name}.{bb.bug.name}.vcd"
            if not buggy_vcd.exists():
                print(f"{buggy_vcd} does not exist. Skipping bug `{bb.bug.name}` in project `{proj.name}`")
                continue
            conf = Config(working_dir, bb)
            print(f"Comparing traces for {proj.name} {bb.bug.name}")
            res = compare_traces(conf)
            print_result(res)
            results.append(res)

    return results


def main():
    conf = parse_args()

    if conf.benchmark is None:
        diff_all(conf.working_dir)
    else:
        res = compare_traces(conf)
        print_result(res)


if __name__ == '__main__':
    main()