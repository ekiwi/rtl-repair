#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import copy
import json
import os
import shutil
import subprocess
import time
from multiprocessing import Pool
from dataclasses import dataclass
from pathlib import Path
from rtlfix import parse_verilog, serialize, do_repair, Synthesizer, preprocess
from rtlfix.templates import *

_supported_solvers = {'z3', 'cvc4', 'yices2', 'boolector', 'bitwuzla', 'optimathsat', 'btormc'}
Success = "success"
CannotRepair = "cannot-repair"
NoRepair = "no-repair"

@dataclass
class Config:
    source: Path
    testbench: Path
    working_dir: Path
    solver: str
    show_ast: bool
    parallel: bool


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Repair Verilog file')
    parser.add_argument('--source', dest='source', help='Verilog source file', required=True)
    parser.add_argument('--testbench', dest='testbench', help='Testbench in CSV format', required=True)
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    parser.add_argument('--solver', dest='solver', help='z3 or optimathsat', default="z3")
    parser.add_argument('--show-ast', dest='show_ast', help='show the ast before applying any transformation',
                        action='store_true')
    parser.add_argument('--parallel', dest='parallel', help='try to apply repair templates in parallel',
                        action='store_true')
    args = parser.parse_args()
    assert args.solver in _supported_solvers, f"unknown solver {args.solver}, try: {_supported_solvers}"
    return Config(Path(args.source), Path(args.testbench), Path(args.working_dir), args.solver, args.show_ast,
                  args.parallel)


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


def try_template(config: Config, ast, prefix: str, template):
    start_time = time.monotonic()

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
    result["directory"] = template_dir.name
    status = result["status"]

    if status == Success:
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


def try_templates_in_parallel(config: Config, ast):
    tmpls = [(f"{ii + 1}_", tmp) for ii, tmp in enumerate(_templates)]
    with Pool() as p:
        procs = [p.apply_async(try_template, (config, ast, prefix, tmp)) for prefix, tmp in tmpls]
        while len(procs) > 0:
            done, procs = partition(procs, lambda pp: pp.ready())
            for res in (pp.get() for pp in done):
                if res["status"] in {Success, NoRepair}:
                    return res["status"], res
    return CannotRepair, None


def partition(elements: list, filter_foo):
    a, b = [], []
    for e in elements:
        if filter_foo(e):
            a.append(e)
        else:
            b.append(e)
    return a, b


def try_templates_in_sequence(config: Config, ast):
    # instantiate repair templates, one after another
    # note: when  we tried to combine replace_literals and add_inversion, tests started taking a long time
    for ii, template in enumerate(_templates):
        prefix = f"{ii + 1}_"
        # we need to deep copy the ast since the template is going to modify it in place!
        ast_copy = copy.deepcopy(ast)
        res = try_template(config, ast, prefix, template)
        if res["status"] in {Success, NoRepair}:
            return res["status"], res
        ast = ast_copy
    return CannotRepair, None


def main():
    start_time = time.monotonic()
    config = parse_args()
    create_working_dir(config.working_dir)

    # preprocess the input file to fix some obvious problems that violate coding styles and basic lint rules
    filename, preprocess_changed = preprocess(config.source, config.working_dir)

    ast = parse_verilog(filename)
    if config.show_ast:
        ast.show()

    if config.parallel:
        status, result = try_templates_in_parallel(config, ast)
    else:
        status, result = try_templates_in_sequence(config, ast)

    success = (status == Success) or (status == NoRepair and preprocess_changed)
    if success:
        # copy repaired file and result json to working dir
        if preprocess_changed:
            status = Success  # fixing things purely through the preprocessor is a kind of success!
            src_dir = config.working_dir / "0_preprocess"
            shutil.copy(filename, config.working_dir / (config.source.stem + ".repaired.v"))
        else:
            src_dir = config.working_dir / result["directory"]
            shutil.copy(src_dir / (config.source.stem + ".repaired.v"), config.working_dir)
        shutil.copy(src_dir / "changes.txt", config.working_dir)

    print(status)
    with open(config.working_dir / "status", "w") as f:
        f.write(status + "\n")
    delta_time = time.monotonic() - start_time
    with open(config.working_dir / "time", "w") as f:
        f.write(f"{delta_time:.3f}s\n")


if __name__ == '__main__':
    main()
