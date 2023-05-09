#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

# check repairs

import os
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
from benchmarks import Benchmark, get_other_sources, VerilogOracleTestbench, get_benchmark, load_all_projects
from benchmarks.yosys import to_gatelevel_netlist
from benchmarks.run import run, RunConf
from benchmarks.result import load_result, Result, Repair

@dataclass
class Config:
    working_dir: Path
    result_dir: Path
    sim: str

def parse_csv_line(line: str) -> list:
    return [n.strip() for n in line.split(',')]

@dataclass
class SimResult:
    no_output: bool = False
    failed_at: int = -1
    fail_msg: str = ""
    @property
    def is_success(self): return self.failed_at == -1 and not self.no_output
    @property
    def emoji(self): return "✔️" if self.is_success else "❌"

def check_against_oracle(oracle_filename: Path, output_filename: Path):
    with open(oracle_filename) as oracle, open(output_filename) as output:
        oracle_header, output_header = parse_csv_line(oracle.readline()), parse_csv_line(output.readline())
        assert oracle_header == output_header, f"{oracle_header} != {output_header}"
        header = oracle_header[1:]

        # compare line by line
        for (ii, (expected, actual)) in enumerate(zip(oracle, output)):
            expected, actual = parse_csv_line(expected), parse_csv_line(actual)
            # remove first line (time)
            expected, actual = expected[1:], actual[1:]
            correct = expected == actual
            if not correct:
                msg = []
                for ee, aa, nn in zip(expected, actual, header):
                    if ee != aa:
                        msg.append(f"{nn}@{ii}: {aa} != {ee} (expected)")
                return SimResult(failed_at=ii, fail_msg='\n'.join(msg))

        # are we missing some output?
        remaining_oracle_lines = oracle.readlines()
        if len(remaining_oracle_lines) > 0:
            # we expected more output => fail!
            msg = f"Output stopped at {ii}. Expected {len(remaining_oracle_lines)} more lines."
            return SimResult(failed_at=ii, fail_msg=msg)

    return SimResult()



def check_gatelevel_sim(conf: Config, logfile, benchmark: Benchmark, repaired: Path):
    other_sources = get_other_sources(benchmark)
    # synthesize
    gate_level = conf.working_dir / f"{repaired.stem}.gatelevel.v"
    to_gatelevel_netlist(conf.working_dir, gate_level, [repaired] + other_sources, top=benchmark.design.top, logfile=None)
    # check
    return check_sim(conf, logfile, benchmark, [gate_level.resolve()] + other_sources)

def check_sim(conf: Config, logfile, benchmark: Benchmark, design_sources: list):
    # run testbench
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    tb_sources = benchmark.testbench.sources + design_sources
    run_conf = RunConf(include_dir=benchmark.design.directory, verbose=False, show_stdout=False, logfile=logfile)
    logfile.flush()
    run(conf.working_dir, conf.sim, tb_sources, run_conf)

    # check the output
    output = conf.working_dir / benchmark.testbench.output
    if not output.exists():
        # no output was produced --> fail
        msg = "No output was produced."
        res = SimResult(no_output=True, fail_msg=msg)
    else:
        res = check_against_oracle(benchmark.testbench.oracle, output)
    print(res, file=logfile)
    return res



def check_repair(conf: Config, logfile, benchmark: Benchmark, repair: Repair):
    # first we just simulate and check the oracle
    print(f"RTL Simulation with Oracle Testbench: {benchmark.testbench.name}", file=logfile)
    other_sources = get_other_sources(benchmark)
    sim_res = check_sim(conf, logfile, benchmark, [repair.filename.resolve()] + other_sources)
    sys.stdout.write(f" RTL-sim {sim_res.emoji}")

    # now we do the gate-level sim, do we get the same result?
    print(f"Gate-Level Simulation with Oracle Testbench: {benchmark.testbench.name}", file=logfile)
    gate_res = check_gatelevel_sim(conf, logfile, benchmark, repair.filename)
    sys.stdout.write(f" Gate-level {gate_res.emoji}")


def find_benchmark(projects: dict, result: Result) -> Benchmark:
    project = projects[result.project_name]
    return get_benchmark(project, result.bug_name, use_trace_testbench=False)

def load_results(tomls: list[Path]) -> list[Result]:
    return [load_result(toml) for toml in tomls]

def find_result_toml(directory: Path) -> list[Path]:
    rr = []
    for filename in directory.iterdir():
        if filename.is_dir():
            rr += find_result_toml(filename)
        elif filename.name == "result.toml":
            rr.append(filename)
    return rr

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Check solutions produced by a repair tool.')
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    parser.add_argument('--results', help='Directory containing the result.toml files.', required=True)
    parser.add_argument("--simulator", default="vcs")
    args = parser.parse_args()
    assert args.simulator in {'vcs', 'iverilog'}, f"unknown simulator: {args.simulator}"
    return Config(Path(args.working_dir), Path(args.results), sim=args.simulator)

def create_working_dir(working_dir: Path):
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)
def main():
    conf = parse_args()

    # check result dir
    assert conf.result_dir.exists(), f"{conf.result_dir.resolve()} does not exist"
    assert conf.result_dir.is_dir(), f"{conf.result_dir.resolve()} is not a directory"

    # find all result files
    result_tomls = find_result_toml(conf.result_dir)
    print(f"Found {len(result_tomls)} result.toml files in {conf.result_dir}")
    if len(result_tomls) == 0:
        return # done
    results = load_results(result_tomls)

    # sort results to ensure deterministic results
    results = sorted(results, key=lambda r: r.result_name)

    # ensure that the working dir exists
    create_working_dir(conf.working_dir)

    # load all projects so that we can find the necessary info to evaluate repairs
    projects = load_all_projects()

    # check each result
    print("Checking Repairs:")
    for res in results:
        print(res.result_name)
        bb = find_benchmark(projects, res)
        # skip for debugging
        if res.project_name != "mux_4_1":
            continue
        # open a log file
        logfile_name = conf.working_dir / f"{res.result_name}.log"
        with open(logfile_name, 'w') as logfile:
            print(f"Checking: {res}", file=logfile)
            for repair in res.repairs:
                print(f"Repair: {repair}", file=logfile)
                sys.stdout.write(f"  - {repair.filename.name}:")
                check_repair(conf, logfile, bb, repair)
                print()


if __name__ == '__main__':
    main()

