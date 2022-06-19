#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import os
from pathlib import Path
from rtlfix.literal_replacer import replace_literals
from rtlfix import parse_verilog, serialize, to_btor, run_synthesizer, do_repair


def parse_args():
    parser = argparse.ArgumentParser(description='Repair Verilog file')
    parser.add_argument('--source', dest='source', help='Verilog source file', required=True)
    parser.add_argument('--testbench', dest='testbench', help='Testbench in CSV format', required=True)
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    parser.add_argument('--solver', dest='solver', help='z3 or optimathsat', default="z3")
    args = parser.parse_args()
    assert args.solver in {'z3', 'optimathsat'}
    return Path(args.source), Path(args.testbench), Path(args.working_dir), args.solver


def create_working_dir(working_dir: Path):
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)


def main():
    filename, testbench, working_dir, solver = parse_args()
    create_working_dir(working_dir)

    # instantiate repair templates
    ast = parse_verilog(filename)
    replace_literals(ast)
    synth_filename = working_dir / filename.name
    with open(synth_filename, "w") as f:
        f.write(serialize(ast))

    # convert file and run synthesizer
    btor_filename = to_btor(synth_filename)
    result = run_synthesizer(btor_filename, testbench, solver)
    status = result["status"]
    with open(working_dir / "status", "w") as f:
        f.write(status + "\n")

    if status == "success":
        # execute synthesized repair
        do_repair(ast, result["assignment"])
        repaired_filename = working_dir / (filename.stem + ".repaired.v")
        with open(repaired_filename, "w") as f:
            f.write(serialize(ast))
    print(status)


if __name__ == '__main__':
    main()
