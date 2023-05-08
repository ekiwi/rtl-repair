#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import copy
import os
import shutil
import subprocess
import time
from multiprocessing import Pool
from dataclasses import dataclass
from pathlib import Path

from benchmarks import Benchmark, load_project, get_benchmark
from benchmarks.result import create_buggy_and_original_diff, write_results
from rtlfix import parse_verilog, serialize, do_repair, Synthesizer, preprocess, SynthOptions, Status
from rtlfix.templates import *

_ToolName = "rtl-repair"

_supported_solvers = {'z3', 'cvc4', 'yices2', 'boolector', 'bitwuzla', 'optimathsat', 'btormc'}


@dataclass
class Options:
    show_ast: bool
    parallel: bool
    synth: SynthOptions
    single_solution: bool = False # restrict the number of solutions to one

@dataclass
class Config:
    working_dir: Path
    benchmark: Benchmark
    opts: Options

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Repair Verilog file')
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    # benchmark selection
    parser.add_argument('--project', help='Project TOML file.', required=True)
    parser.add_argument('--bug', help='Name of the bug from the project TOML.', default=None)
    parser.add_argument('--testbench', help='Name of the testbench from the project TOML.', default=None)

    # options
    parser.add_argument('--solver', dest='solver', help='z3 or optimathsat', default="z3")
    parser.add_argument('--init', dest='init', help='how should states be initialized? [any], zero or random',
                        default="any")
    parser.add_argument('--show-ast', dest='show_ast', help='show the ast before applying any transformation',
                        action='store_true')
    parser.add_argument('--parallel', dest='parallel', help='try to apply repair templates in parallel',
                        action='store_true')
    parser.add_argument('--incremental', dest='incremental', help='use incremental solver',
                        action='store_true')


    args = parser.parse_args()


    # benchmark selection
    project = load_project(Path(args.project))
    benchmark = get_benchmark(project, args.bug, testbench=args.testbench, use_trace_testbench=True)

    # options
    assert args.solver in _supported_solvers, f"unknown solver {args.solver}, try: {_supported_solvers}"
    assert args.init in {'any', 'zero', 'random'}
    synth_opts = SynthOptions(solver = args.solver, init=args.init, incremental=args.incremental)
    opts = Options(show_ast=args.show_ast, parallel=args.parallel, synth=synth_opts)

    return Config(Path(args.working_dir), benchmark, opts)


def create_working_dir(working_dir: Path):
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)


_templates = [replace_literals, assign_const, add_inversions, replace_variables]


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


def try_template(config: Config, ast, prefix: str, template) -> (Status, list):
    start_time = time.monotonic()

    # create a directory for this particular template
    template_name = template.__name__
    template_dir = config.working_dir / (prefix + template_name)
    if template_dir.exists():
        shutil.rmtree(template_dir)
    os.mkdir(template_dir)

    # apply template any try to synthesize a solution
    template(ast)

    # try to find a change that fixes the design
    synth_start_time = time.monotonic()
    synth = Synthesizer()
    status, assignments = synth.run(template_dir, config.opts.synth, ast, config.benchmark)
    synth_time = time.monotonic() - synth_start_time

    solutions = []
    if status == Status.Success:
        # pick first solution if only one was requested
        if config.opts.single_solution:
            assignments = assignments[:1]
        for ii, assignment in enumerate(assignments):
            # execute synthesized repair
            changes = do_repair(ast, assignment)
            prefix = f"{config.benchmark.bug.buggy.stem}.repaired.{ii}"
            with open(template_dir / f"{prefix}.changes.txt", "w") as f:
                f.write(f"{template_name}\n")
                f.write(f"{len(changes)}\n")
                f.write('\n'.join(f"{line}: {a} -> {b}" for line, a, b in changes))
                f.write('\n')
            repaired_filename = config.working_dir / f"{prefix}.v"
            with open(repaired_filename, "w") as f:
                f.write(serialize(ast))
            # meta info for the solution
            meta = { 'changes': len(changes), 'template': template_name, 'synth_time': synth_time,
                     'template_time':  time.monotonic() - start_time}
            solutions.append((repaired_filename, meta))

    return status, solutions


def try_templates_in_parallel(config: Config, ast) -> (Status, list):
    tmpls = [(f"{ii + 1}_", tmp) for ii, tmp in enumerate(_templates)]
    with Pool() as p:
        procs = [p.apply_async(try_template, (config, ast, prefix, tmp)) for prefix, tmp in tmpls]
        while len(procs) > 0:
            done, procs = partition(procs, lambda pp: pp.ready())
            for status, solutions in (pp.get() for pp in done):
                if status != Status.CannotRepair:
                    return status, solutions
    return Status.CannotRepair, []


def partition(elements: list, filter_foo):
    a, b = [], []
    for e in elements:
        if filter_foo(e):
            a.append(e)
        else:
            b.append(e)
    return a, b


def try_templates_in_sequence(config: Config, ast) -> (Status, list):
    # instantiate repair templates, one after another
    # note: when  we tried to combine replace_literals and add_inversion, tests started taking a long time
    for ii, template in enumerate(_templates):
        prefix = f"{ii + 1}_"
        # we need to deep copy the ast since the template is going to modify it in place!
        ast_copy = copy.deepcopy(ast)
        status, solutions = try_template(config, ast, prefix, template)
        if status != Status.CannotRepair:
            return status, solutions
        ast = ast_copy
    return Status.CannotRepair, []


def repair(config: Config):
    # preprocess the input file to fix some obvious problems that violate coding styles and basic lint rules
    filename, preprocess_changed = preprocess(config.working_dir, config.benchmark)

    ast = parse_verilog(filename, config.benchmark.design.directory)
    if config.opts.show_ast:
        ast.show()

    if config.opts.parallel:
        status, solutions = try_templates_in_parallel(config, ast)
    else:
        status, solutions = try_templates_in_sequence(config, ast)

    # create repaired file in the case where the synthesizer had to make no changes
    if status == Status.NoRepair:
        # make sure we copy over the repaired file
        repaired_dst = config.working_dir / f"{config.benchmark.bug.buggy.stem}.repaired.v"
        shutil.copy(src=filename, dst=repaired_dst)
        # if the preprocessor made a change and that resulted in not needing any change to fix the benchmark
        # then we successfully repaired the design with the preprocessor
        if preprocess_changed:
            solutions = [(repaired_dst, {'template': "preprocess", 'changes': -1})]
            status = Status.Success
        # otherwise the circuit was already correct
        else:
            solutions = [(repaired_dst, {'template': "", 'changes': 0})]

    return status, solutions

def main():
    config = parse_args()
    create_working_dir(config.working_dir)

    # create benchmark description to make results self-contained
    create_buggy_and_original_diff(config.working_dir, config.benchmark)

    # run repair
    start_time = time.monotonic()
    status, solutions = repair(config)
    delta_time = time.monotonic() - start_time

    # save results to disk
    success = status != Status.CannotRepair
    write_results(config.working_dir, config.benchmark, success,
                  repaired=solutions, seconds=delta_time, tool_name=_ToolName,
                  custom={'status': status.value})

if __name__ == '__main__':
    main()
