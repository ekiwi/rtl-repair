#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import os
import subprocess
from pathlib import Path
from rtlfix.literal_replacer import replace_literals
from rtlfix import parse_verilog, serialize, do_repair
from rtlfix.synthesizer import Synthesizer


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

    synth = Synthesizer()
    result = synth.run(filename.name, working_dir, ast, testbench, solver)
    status = result["status"]

    if status == "success":
        # execute synthesized repair
        changes = do_repair(ast, result["assignment"])
        with open(working_dir / "changes.txt", "w") as f:
            f.write(f"{len(changes)}\n")
            f.write('\n'.join(f"{line}: {a} -> {b}" for line, a, b in changes))
            f.write('\n')
        with open(working_dir / "solver", "w") as f:
            r = subprocess.run([solver, "-version"], check=True, stdout=subprocess.PIPE)
            f.write(r.stdout.decode('utf-8').strip() + "\n")
        repaired_filename = working_dir / (filename.stem + ".repaired.v")
        with open(repaired_filename, "w") as f:
            f.write(serialize(ast))
    print(status)


if __name__ == '__main__':
    main()
