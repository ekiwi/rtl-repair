#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from rtlfix import parse_verilog, serialize, do_repair, Synthesizer, preprocess
from rtlfix.templates import *

_supported_solvers = {'z3', 'cvc4', 'yices2', 'boolector', 'bitwuzla', 'optimathsat', 'btormc'}


@dataclass
class Config:
    source: Path
    testbench: Path
    working_dir: Path
    solver: str
    show_ast: bool


def parse_args() -> Config:
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
    return Config(Path(args.source), Path(args.testbench), Path(args.working_dir), args.solver, args.show_ast)


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


def try_template(config: Config, input_file: Path, prefix: str, template):
    start_time = time.monotonic()
    # parse file, the input file could be different from the original "source" because of preprocessing
    ast = parse_verilog(input_file)

    # create a directory for this particular template
    template_name = template.__name__
    template_dir = config.working_dir / (prefix + template_name)
    if template_dir.exists():
        shutil.rmtree(template_dir)
    os.mkdir(template_dir)

    # apply template any try to synthesize a solution
    template(ast)
    synth_start_time = time.monotonic()
    synth = Synthesizer()
    result = synth.run(config.source.name, template_dir, ast, config.testbench, config.solver)
    synth_time = time.monotonic() - synth_start_time
    # add some metadata to result
    result["template"] = template_name
    result["solver"] = find_solver_version(config.solver)
    status = result["status"]

    if status == "success":
        # execute synthesized repair
        changes = do_repair(ast, result["assignment"])
        result["num_changes"] = len(changes)
        with open(template_dir / "changes.txt", "w") as f:
            f.write(f"{template_name}\n")
            f.write(f"{len(changes)}\n")
            f.write('\n'.join(f"{line}: {a} -> {b}" for line, a, b in changes))
            f.write('\n')
        repaired_filename = template_dir / (config.source.stem + ".repaired.v")
        with open(repaired_filename, "w") as f:
            f.write(serialize(ast))

    # write result to disk
    result['synth_time'] = f"{synth_time:.3f}"
    result['total_time'] = f"{time.monotonic() - start_time:.3f}"
    with open(template_dir / "result.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def main():
    start_time = time.monotonic()
    config = parse_args()
    create_working_dir(config.working_dir)

    status = "cannot-repair"
    success_template = None

    # preprocess the input file to fix some obvious problems that violate coding styles and basic lint rules
    filename = preprocess(config.source, config.working_dir)
    if filename != config.source:
        # if the preprocessing changed the file, that might have already fixed the issue
        success_template = "0_preprocess"

    if config.show_ast:
        ast = parse_verilog(filename)
        ast.show()

    # instantiate repair templates, one after another
    # note: when  we tried to combine replace_literals and add_inversion, tests started taking a long time
    for ii, template in enumerate(_templates):
        prefix = f"{ii + 1}_"
        status = try_template(config, filename, prefix, template)['status']
        if status == 'success':
            success_template = prefix + template.__name__
            break
        if status == 'no-repair':
            break

    if success_template is not None:
        # copy repaired file and result json to working dir
        src_dir = config.working_dir / success_template
        shutil.copy(src_dir / "changes.txt", config.working_dir)
        if status == 'no-repair':  # this means that the preprocessor already fixed all our issues
            status = 'success'
            shutil.copy(filename, config.working_dir / (config.source.stem + ".repaired.v"))
        else:
            assert status == 'success'
            shutil.copy(src_dir / (config.source.stem + ".repaired.v"), config.working_dir)

    print(status)
    with open(config.working_dir / "status", "w") as f:
        f.write(status + "\n")
    delta_time = time.monotonic() - start_time
    with open(config.working_dir / "time", "w") as f:
        f.write(f"{delta_time:.3f}s\n")


if __name__ == '__main__':
    main()
