#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# runs VCS in order to generate buggy and ground truth VCD traces for cirfix benchmarks

import argparse
import tempfile
import shutil
import time
from pathlib import Path

import benchmarks
from benchmarks import Project, Design, VerilogOracleTestbench
from benchmarks.run import run, RunConf

def gen_trace(sim: str, verbose: bool, output: Path, design: Design, testbench: VerilogOracleTestbench):
    start = time.time()
    run_conf = RunConf(include_dir=design.directory, defines=[("DUMP_TRACE", "1")])
    # use a temporary directory to avoid conflicts from multiple testbenches all creating a file called `dump.vcd`
    with tempfile.TemporaryDirectory() as wd_name:
        working_dir = Path(wd_name)
        # testbench sources have to go first because they often have a timescale defined
        sources = testbench.sources + design.sources
        run(working_dir=working_dir, sim=sim, files=sources, conf=run_conf)
        dump_out = working_dir / "dump.vcd" # this is the hard-coded standard name
        assert dump_out.exists(), f"Expected `{dump_out.resolve()}` to exist, but it does not!"
        shutil.move(dump_out, output)
    assert output.exists()
    delta_time = time.time() - start
    if verbose:
        print(f"Created: {output} in {delta_time:.03}s")


def gen_project_traces(output_dir: Path, sim: str, verbose: bool, proj: Project):
    testbench = [tb for tb in proj.testbenches if isinstance(tb, VerilogOracleTestbench)][0]
    # ground truth
    gen_trace(sim, verbose, output_dir / f"{proj.name}.groundtruth.vcd", proj.design, testbench)

    # buggy traces
    for bb in benchmarks.get_benchmarks(proj):
        # skip bugs that are not part of the cirfix paper
        if not benchmarks.is_cirfix_paper_benchmark(bb):
            continue
        design = benchmarks.get_benchmark_design(bb)
        gen_trace(sim, verbose, output_dir / f"{proj.name}.{bb.bug.name}.vcd", design, testbench)


def parse_args() -> (Path, str, bool):
    parser = argparse.ArgumentParser(description='Generate ground truth and buggy VCD traces.')
    parser.add_argument('output_dir')
    parser.add_argument('--sim', help='Change simulator', default='vcs')
    parser.add_argument('--verbose', '-v', help='Verbose output', action='store_true')
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    verbose = args.verbose
    sim = args.sim
    assert sim in {'vcs', 'iverilog'}, f"unknown/unsupported simulator `{sim}`"
    # try to create output_dir
    if not output_dir.exists():
        assert output_dir.parent.exists(), f"{output_dir.parent} ({output_dir.parent.resolve()}) does not exist!"
        output_dir.mkdir()
    assert output_dir.exists()
    return output_dir, sim, verbose


_skip_projects = {'i2c_slave'}
def main():
    output_dir, sim, verbose = parse_args()
    projects = benchmarks.load_all_projects()

    for proj in projects.values():
        if proj.name in _skip_projects:
            if verbose: print(f"Skipping {proj.name}")
            continue
        if verbose:
            print(f"Generating VCD traces for {proj.name}")
        gen_project_traces(output_dir, sim, verbose, proj)


if __name__ == '__main__':
    main()