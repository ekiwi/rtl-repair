#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import os
import subprocess
import time
from pathlib import Path
from rtlfix import parse_verilog, serialize, do_repair, Synthesizer
from rtlfix.templates import *



def parse_args():
    parser = argparse.ArgumentParser(description='Repair Verilog file')
    parser.add_argument('--source', dest='source', help='Verilog source file', required=True)
    parser.add_argument('--testbench', dest='testbench', help='Testbench in CSV format', required=True)
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    parser.add_argument('--solver', dest='solver', help='z3 or optimathsat', default="z3")
    parser.add_argument('--show-ast', dest='show_ast', help='show the ast before applying any transformation',
                        action='store_true')
    args = parser.parse_args()
    assert args.solver in {'z3', 'optimathsat'}
    return Path(args.source), Path(args.testbench), Path(args.working_dir), args.solver, args.show_ast


def create_working_dir(working_dir: Path):
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)


_templates = [replace_literals, add_inversions, replace_variables]


def main():
    start_time = time.monotonic()
    filename, testbench, working_dir, solver, show_ast = parse_args()
    create_working_dir(working_dir)

    status = "cannot-repair"
    result = []
    ast = parse_verilog(filename)
    if show_ast:
        ast.show()

    # instantiate repair templates, one after another
    # note: when  we tried to combine replace_literals and add_inversion, tests started taking a long time
    for template in _templates:
        template(ast)
        synth = Synthesizer()
        result = synth.run(filename.name, working_dir, ast, testbench, solver)
        status = result["status"]
        if status == "success":
            result["template"] = template.__name__
            break
        # recreate AST since we destroyed (mutated) the old one
        ast = parse_verilog(filename)

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
        with open(working_dir / "template", "w") as f:
            f.write(result["template"] + "\n")
        repaired_filename = working_dir / (filename.stem + ".repaired.v")
        with open(repaired_filename, "w") as f:
            f.write(serialize(ast))
    print(status)
    delta_time = time.monotonic() - start_time
    with open(working_dir / "time", "w") as f:
        f.write(f"{delta_time}s\n")


if __name__ == '__main__':
    main()
