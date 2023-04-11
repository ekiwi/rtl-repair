#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
from pathlib import Path
from dataclasses import dataclass
from rtlfix import to_btor

@dataclass
class Config:
    top: str
    sourceA: Path
    sourceB: Path
    working_dir: Path

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Compare two verilog files')
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    parser.add_argument('--source-a', '-a', dest='a', help='Verilog source file A.', required=True)
    parser.add_argument('--source-b', '-b', dest='b', help='Verilog source file B.', required=True)
    parser.add_argument('--top', help='Name of toplevel module..', required=True)

    args = parser.parse_args()
    return Config(args.top, Path(args.a), Path(args.b), Path(args.working_dir))

def main():
    conf = parse_args()

    # create working dir if it does not exist
    if not conf.working_dir.exists():
        conf.working_dir.mkdir()

    # convert both designs to a btor
    a_btor = to_btor(conf.working_dir, conf.working_dir / (conf.sourceA.stem + ".btor"), [conf.sourceA], conf.top)
    b_btor = to_btor(conf.working_dir, conf.working_dir / (conf.sourceB.stem + ".btor"), [conf.sourceB], conf.top)

if __name__ == '__main__':
    main()