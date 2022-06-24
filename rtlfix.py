#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path
from rtlfix import parse_verilog, serialize, do_repair, Synthesizer, preprocess
from rtlfix.templates import *

_supported_solvers = {'z3', 'cvc4', 'yices2', 'boolector', 'bitwuzla', 'optimathsat', 'btormc'}


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
    assert args.solver in _supported_solvers, f"unknown solver {args.solver}, try: {_supported_solvers}"
    return Path(args.source), Path(args.testbench), Path(args.working_dir), args.solver, args.show_ast


def create_working_dir(working_dir: Path):
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)


_templates = [replace_literals, add_inversions, replace_variables]


def find_solver_version(solver: str) -> str:
    arg = ["--version"]
    if solver == "btormc":
        arg += ["-h"]  # without this btormc does not terminate
    if solver == 'yices2':
        solver = 'yices-smt2'
    if solver == 'optimathsat':
        arg = ["-version"]
    r = subprocess.run([solver] + arg, check=True, stdout=subprocess.PIPE)
    return r.stdout.decode('utf-8').splitlines()[0].strip()


def main():
    start_time = time.monotonic()
    filename, testbench, working_dir, solver, show_ast = parse_args()
    name = filename.name
    create_working_dir(working_dir)

    # preprocess the input file to fix some obvious problems that violate coding styles and basic lint rules
    filename = preprocess(filename, working_dir)

    status = "cannot-repair"
    result = []
    ast = parse_verilog(filename)
    if show_ast:
        ast.show()

    # instantiate repair templates, one after another
    # note: when  we tried to combine replace_literals and add_inversion, tests started taking a long time
    for template in _templates:
        # create a directory for this particular template
        template_name = template.__name__
        template_dir = working_dir / template_name
        if template_dir.exists():
            shutil.rmtree(template_dir)
        os.mkdir(template_dir)

        # apply template any try to synthesize a solution
        template(ast)
        synth = Synthesizer()
        result = synth.run(name, template_dir, ast, testbench, solver)
        status = result["status"]
        if status == "success":
            result["template"] = template_name
            break
        # nothing to repair, no need to try other templates
        if status == "no-repair":
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
            f.write(find_solver_version(solver) + "\n")
        with open(working_dir / "template", "w") as f:
            f.write(result["template"] + "\n")
        repaired_filename = working_dir / (filename.stem + ".repaired.v")
        with open(repaired_filename, "w") as f:
            f.write(serialize(ast))
    print(status)
    with open(working_dir / "status", "w") as f:
        f.write(status + "\n")
    delta_time = time.monotonic() - start_time
    with open(working_dir / "time", "w") as f:
        f.write(f"{delta_time}s\n")


if __name__ == '__main__':
    main()
