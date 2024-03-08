#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# runs VCS in order to generate buggy and ground truth VCD traces for cirfix benchmarks

import sys
import argparse
import tempfile
import shutil
import time
from pathlib import Path

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
import benchmarks
from benchmarks import Project, Design, VerilogOracleTestbench, assert_file_exists
from benchmarks.run import run, RunConf, SimResult, check_against_oracle

def gen_trace(sim: str, verbose: bool, timeout: float, output_vcd: Path, output_trace: Path, design: Design, testbench: VerilogOracleTestbench):
    start = time.time()
    run_conf = RunConf(
        include_dir=design.directory,
        defines=[("DUMP_TRACE", "1")],
        timeout=timeout,
    )
    # use a temporary directory to avoid conflicts from multiple testbenches all creating a file called `dump.vcd`
    with tempfile.TemporaryDirectory() as wd_name:
        working_dir = Path(wd_name)
        # testbench sources have to go first because they often have a timescale defined
        sources = testbench.sources + design.sources
        run(working_dir=working_dir, sim=sim, files=sources, conf=run_conf)
        # copy over VCD trace
        dump_out = working_dir / "dump.vcd" # this is the hard-coded standard name
        assert_file_exists("VCD output", dump_out)
        shutil.move(dump_out, output_vcd)
        # copy over output
        output_filename = working_dir / testbench.output
        assert_file_exists("output TXT", output_filename)
        shutil.move(output_filename, output_trace)

    assert output_vcd.exists()
    assert output_trace.exists()
    delta_time = time.time() - start
    if verbose:
        print(f"Created: {output_vcd} in {delta_time:.03}s")


def gen_project_traces(output_dir: Path, sim: str, verbose: bool, timeout: float, proj: Project, results: list):
    testbench = [tb for tb in proj.testbenches if isinstance(tb, VerilogOracleTestbench)][0]
    gt_out_txt = output_dir / f"{proj.name}.groundtruth.output.txt"
    # ground truth
    gen_trace(sim, verbose, timeout, output_dir / f"{proj.name}.groundtruth.vcd", gt_out_txt, proj.design, testbench)

    # buggy traces
    for bb in benchmarks.get_benchmarks(proj):
        # skip bugs that are not part of the cirfix paper
        if not benchmarks.is_cirfix_paper_benchmark(bb):
            continue
        design = benchmarks.get_benchmark_design(bb)
        bug_out_txt = output_dir / f"{proj.name}.{bb.bug.name}.output.txt"
        gen_trace(sim, verbose, timeout, output_dir / f"{proj.name}.{bb.bug.name}.vcd", bug_out_txt, design, testbench)
        # compare traces
        try:
            res = check_against_oracle(gt_out_txt, bug_out_txt)
            results.append((proj.name, bb.bug.name, res))
        except AssertionError:
            # this generally means that one of the output files was corrupted (i.e. missing part of the header)
            pass

def save_results(filename: Path, results: list):
    with open(filename, 'w') as ff:
        print(f"# this file was generated by {__file__}", file=ff)
        print(f"# it contains the simulation results for the _baseline_ bugs", file=ff)
        for (project, bug, res) in results:
            assert isinstance(res, SimResult)
            print("", file=ff)
            print("[[results]]", file=ff)
            print(f'project="{project}"', file=ff)
            print(f'bug="{bug}"', file=ff)
            print(f'no_output={str(res.no_output).lower()}', file=ff)
            print(f'failed_at={str(res.failed_at)}', file=ff)
            print(f'fail_msg="""{res.fail_msg}"""', file=ff)
            print(f'cycles={str(res.cycles)}', file=ff)

def parse_args() -> (Path, str, bool, float):
    parser = argparse.ArgumentParser(description='Generate ground truth and buggy VCD traces.')
    parser.add_argument('output_dir')
    parser.add_argument('--sim', help='Change simulator', default='vcs')
    parser.add_argument('--timeout', help='Set a simulation timeout', default=60)
    parser.add_argument('--verbose', '-v', help='Verbose output', action='store_true')
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    verbose = args.verbose
    sim = args.sim
    assert sim in {'vcs', 'iverilog'}, f"unknown/unsupported simulator `{sim}`"
    timeout = float(args.timeout)
    assert 24*60*60 > timeout > 0, f"Timeout {timeout} out of expected range (up to 1day)"
    # try to create output_dir
    if not output_dir.exists():
        assert output_dir.parent.exists(), f"{output_dir.parent} ({output_dir.parent.resolve()}) does not exist!"
        output_dir.mkdir()
    assert output_dir.exists()
    return output_dir, sim, verbose, timeout

# i2c_slave is a event driven model, thus the OSDD metric does not apply
_skip_projects = {'i2c_slave'}
def main():
    output_dir, sim, verbose, timeout = parse_args()
    projects = benchmarks.load_all_projects()

    results = []

    for proj in projects.values():
        if proj.name in _skip_projects:
            if verbose: print(f"Skipping {proj.name}")
            continue
        if not benchmarks.is_cirfix_paper_project(proj):
            if verbose: print(f"Skipping {proj.name} because it is not a benchmark from the CirFix paper.")
            continue
        if verbose:
            print(f"Generating VCD traces for {proj.name}")
        gen_project_traces(output_dir, sim, verbose, timeout, proj, results)
    save_results(output_dir / "baseline_results.toml", results)


if __name__ == '__main__':
    main()