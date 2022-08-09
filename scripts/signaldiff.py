#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


import argparse
from dataclasses import dataclass
from pathlib import Path
import vcdvcd
import tempfile
import typing

@dataclass
class Config:
    original: Path
    buggy: Path
    testbench: Path
    logfile: Path
    tmp_dir: Path

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Compare VCDs')
    parser.add_argument('--o', dest='original', help='original vcd', required=True)
    parser.add_argument('--b', dest='buggy', help='buggy vcd', required=True)
    parser.add_argument('--testbench', dest='testbench', help='Testbench in CSV format', required=True)
    parser.add_argument('--log', dest='logfile', help='File to log to.')
    parser.add_argument('--tmp', dest='tmp_dir', help='Working directory to store temporary files in.')
    args = parser.parse_args()
    logfile = None if args.logfile is None else Path(args.logfile)
    tmp_dir = None if args.tmp_dir is None else Path(args.tmp_dir)
    return Config(Path(args.original), Path(args.buggy), Path(args.testbench), logfile, tmp_dir)

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
    def __init__(self, out: typing.TextIO):
        super().__init__()
        self.out = out
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


def vcd_to_csv(vcd_path: Path, tmp_dir: typing.Optional[Path]) -> typing.TextIO:
    if tmp_dir is None:
        csv_file = tempfile.SpooledTemporaryFile(mode='wt')
    else:
        assert tmp_dir.exists() and tmp_dir.is_dir(), f"{tmp_dir} does not exists or is not a directory!"
        csv_file = tempfile.TemporaryFile(mode='wt', dir=tmp_dir)
    vcdvcd.VCDVCD(str(vcd_path.resolve()), callbacks=VCDConverter(csv_file), store_tvs=False)
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


def compare_line(ii: int, original: list, buggy: list, signals: list, externals: set) -> list:
    disagree = []
    for ((o, b), name) in zip(zip(original, buggy), signals):
        if o.lower() == 'x': # no constraint!
            continue
        if o.lower() != b.lower():
            disagree.append(Disagreement(ii, name, name in externals, o.lower(), b.lower()))
    return disagree


def compare(original: typing.TextIO, buggy: typing.TextIO, external: list):
    # make sure both VCDs include the same signals
    signals = parse_csv_line(original.readline())
    buggy_signals = parse_csv_line(buggy.readline())
    assert signals == buggy_signals, f"Mismatch!\n{signals}\n{buggy_signals}"
    signals = normalize_signals(signals)
    is_external = set(external)

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


def main():
    conf = parse_args()
    assert conf.original.exists(), f"Cannot find {conf.original}"
    assert conf.buggy.exists(), f"Cannot find {conf.buggy}"
    assert conf.testbench.exists(), f"Cannot find {conf.testbench}"
    start_logger(conf.logfile)
    # extract signal names from testbench
    external_signals = get_signal_names(conf.testbench)
    # filter out the "time" signal, which does not correspond to a circuit pin
    external_signals = [e for e in external_signals if e != "time"]

    # convert VCD files into CSV tables for easier (line-by-line) comparison
    original_vcd = vcd_to_csv(conf.original, conf.tmp_dir)
    buggy_vcd = vcd_to_csv(conf.buggy, conf.tmp_dir)

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
    original_vcd.close()
    buggy_vcd.close()



if __name__ == '__main__':
    main()