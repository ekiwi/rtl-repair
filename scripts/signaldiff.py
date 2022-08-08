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

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Compare VCDs')
    parser.add_argument('--o', dest='original', help='original vcd', required=True)
    parser.add_argument('--b', dest='buggy', help='buggy vcd', required=True)
    parser.add_argument('--testbench', dest='testbench', help='Testbench in CSV format', required=True)
    args = parser.parse_args()
    return Config(Path(args.original), Path(args.buggy), Path(args.testbench))



class VCDConverter(vcdvcd.StreamParserCallbacks):
    def __init__(self, out: typing.TextIO):
        super().__init__()
        self.out = out
        self.signals = dict()
        self.id_to_index = dict()
        self.last_write = -1
        self.values = []

    def enddefinitions(self, vcd, signals, cur_sig_vals):
        # convert references to list and sort by name
        refs = [ (k,v) for k,v in vcd.references_to_ids.items() ]
        refs = sorted(refs, key=lambda e: e[0])
        self.id_to_index = { e[1]: i for i,e  in enumerate(refs) }
        self.values = ["x"] * len(self.id_to_index)
        header = ', '.join(e[0] for e in refs)
        self.out.write(header + '\n')

    def write_to_file(self, time):
        while time > self.last_write:
            self.last_write += 2
            line = ', '.join(f"{v}" for v in self.values)
            self.out.write(line + "\n")

    def value(self, vcd, time, value, identifier_code, cur_sig_vals):
        self.write_to_file(time)
        if identifier_code in self.id_to_index:
            self.values[self.id_to_index[identifier_code]] = value


def vcd_to_csv(vcd_path: Path) -> typing.TextIO:
    csv_file = tempfile.SpooledTemporaryFile(mode='wt')
    vcdvcd.VCDVCD(str(vcd_path.resolve()), callbacks=VCDConverter(csv_file), store_tvs=False)
    csv_file.seek(0)
    return csv_file



def main():
    conf = parse_args()
    assert conf.original.exists(), f"Cannot find {conf.original}"
    assert conf.buggy.exists(), f"Cannot find {conf.buggy}"
    assert conf.testbench.exists(), f"Cannot find {conf.testbench}"
    # convert VCD files into CSV tables for easier (line-by-line) comparison
    forig = vcd_to_csv(conf.original)
    print(forig.read())






if __name__ == '__main__':
    main()