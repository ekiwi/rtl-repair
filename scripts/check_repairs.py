#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

# check repairs

import os
import shutil
import subprocess
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
import benchmarks
from benchmarks import Benchmark, get_other_sources, VerilogOracleTestbench, get_benchmark, load_all_projects
from benchmarks.yosys import to_gatelevel_netlist
from benchmarks.run import run, RunConf
from benchmarks.result import load_result, Result, Repair


@dataclass
class Config:
    working_dir: Path
    result_dir: Path
    sim: str
    skip_rtl_sim: bool


def _parse_csv_item(item: str) -> str:
    item = item.strip()
    if len(item) <= 1:
        return item
    if item[0] == '"' and item[-1] == '"':
        item = item[1:-1].strip()
    return item


def parse_csv_line(line: str) -> list:
    return [_parse_csv_item(n) for n in line.split(',')]


OkEmoji = "✔️"
FailEmoji = "❌"


def success_to_emoji(success: bool) -> str:
    return OkEmoji if success else FailEmoji


@dataclass
class SimResult:
    no_output: bool = False
    failed_at: int = -1
    fail_msg: str = ""
    cycles: int = None # number of cycles executed

    @property
    def is_success(self): return self.failed_at == -1 and not self.no_output

    @property
    def emoji(self): return success_to_emoji(self.is_success)


def check_against_oracle(oracle_filename: Path, output_filename: Path):
    # check output length to determine the number of cycles
    with open(output_filename) as output:
        cycles = 0
        for _ in output:
            cycles += 1
    with open(oracle_filename) as oracle, open(output_filename) as output:
        oracle_header, output_header = parse_csv_line(oracle.readline()), parse_csv_line(output.readline())
        assert oracle_header == output_header, f"{oracle_header} != {output_header}"
        assert oracle_header[0].lower() == 'time', f"{oracle_header}"
        header = oracle_header[1:]

        # compare line by line
        for (ii, (expected, actual)) in enumerate(zip(oracle, output)):
            expected, actual = parse_csv_line(expected), parse_csv_line(actual)
            # remove first line (time)
            expected, actual = expected[1:], actual[1:]
            msg = []
            for ee, aa, nn in zip(expected, actual, header):
                ee, aa = ee.lower(), aa.lower()
                if ee != 'x' and ee != aa:
                    msg.append(f"{nn}@{ii}: {aa} != {ee} (expected)")
            if len(msg) > 0:
                return SimResult(failed_at=ii, fail_msg='\n'.join(msg), cycles=cycles)

        # are we missing some output?
        remaining_oracle_lines = oracle.readlines()
        if len(remaining_oracle_lines) > 0:
            # we expected more output => fail!
            msg = f"Output stopped at {ii}. Expected {len(remaining_oracle_lines)} more lines."
            return SimResult(failed_at=ii, fail_msg=msg, cycles=cycles)

    return SimResult(cycles=cycles)


def check_sim(conf: Config, working_dir: Path, logfile, benchmark: Benchmark, design_sources: list,
              max_cycles: int = None):
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    output = working_dir / benchmark.testbench.output
    # remove any previous output that might exist from a prior run
    if output.exists():
        os.remove(output)

    # run testbench
    tb_sources = benchmark.testbench.sources + design_sources
    run_conf = RunConf(include_dir=benchmark.design.directory, verbose=False, show_stdout=False, logfile=logfile,
                       timeout=60 * 2, # 2 minutes max
                       # dump a trace for easier debugging
                       defines=[("DUMP_TRACE", 1)])
    if logfile:
        logfile.flush()
    run(working_dir, conf.sim, tb_sources, run_conf)

    # check the output
    if not output.exists():
        # no output was produced --> fail
        msg = "No output was produced."
        res = SimResult(no_output=True, fail_msg=msg, cycles=0)
    else:
        res = check_against_oracle(benchmark.testbench.oracle, output)
    if logfile:
        print(res, file=logfile)
    return res


def check_repair(conf: Config, working_dir: Path, logfile, benchmark: Benchmark, repair: Repair):
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    sys.stdout.flush()
    # copy over the oracle for easier debugging later
    shutil.copy(benchmark.testbench.oracle, working_dir)

    # by default, the gate level sim runs until it terminates
    max_cycles = None

    # first we just simulate and check the oracle
    if not conf.skip_rtl_sim:
        print(f"RTL Simulation with Oracle Testbench: {benchmark.testbench.name}", file=logfile)
        other_sources = get_other_sources(benchmark)
        run_logfile = working_dir / f"{repair.filename.stem}.sim.log"
        with open(run_logfile, 'w') as logff:
            sim_res = check_sim(conf, working_dir, logff, benchmark, [repair.filename.resolve()] + other_sources)
        sys.stdout.write(f" RTL-sim {sim_res.emoji}")
        sys.stdout.flush()
        # rename output in order to preserve it
        try:
            shutil.move(working_dir / benchmark.testbench.output, working_dir / f"{benchmark.testbench.output}.rtl")
        except:
            pass
        # rename trace
        if (working_dir / "dump.vcd").exists():
            shutil.move(working_dir / "dump.vcd", working_dir / "rtl.vcd")
        max_cycles = sim_res.cycles

    # synthesize to gates
    print(f"Synthesize to Gates: {benchmark.name}", file=logfile)
    other_sources = get_other_sources(benchmark)
    # synthesize
    gate_level = working_dir / f"{repair.filename.stem}.gatelevel.v"
    try:
        with open(working_dir / f"{repair.filename.stem}.synthesis.log", 'w') as gate_level_logfile:
            to_gatelevel_netlist(working_dir, gate_level, [repair.filename] + other_sources, top=benchmark.design.top,
                                 logfile=gate_level_logfile)
        synthesis_success = True
    except subprocess.CalledProcessError:
        synthesis_success = False
    sys.stdout.write(f" Synthesis {success_to_emoji(synthesis_success)}")
    sys.stdout.flush()

    # now we do the gate-level sim, do we get the same result?
    if synthesis_success:
        print(f"Gate-Level Simulation with Oracle Testbench: {benchmark.testbench.name}", file=logfile)
        run_logfile = working_dir / f"{repair.filename.stem}.gatelevel.sim.log"
        with open(run_logfile, 'w') as logff:
            gate_res = check_sim(conf, working_dir, logff, benchmark, [gate_level.resolve()], max_cycles=max_cycles)
        sys.stdout.write(f" Gate-level {gate_res.emoji}")
        sys.stdout.flush()
        # rename trace
        if (working_dir / "dump.vcd").exists():
            shutil.move(working_dir / "dump.vcd", working_dir / "gatelevel.vcd")


def find_benchmark(projects: dict, result: Result) -> Benchmark:
    project = projects[result.project_name]
    # overwrite for manual adjustments that we had to make
    if result.tool == "rtl-repair" and result.project_name in benchmarks.rtlrepair_replacements:
        project_toml = benchmarks.rtlrepair_replacements[result.project_name]
        project = benchmarks.load_project(project_toml)
    return get_benchmark(project, result.bug_name, use_trace_testbench=False)


def load_results(tomls: list[Path]) -> list[Result]:
    res = []
    for toml in tomls:
        result_name = toml.parent.name
        res.append(load_result(toml, result_name))
    return res


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
    parser.add_argument("--skip-rtl-sim", default=False, action='store_true')
    args = parser.parse_args()
    assert args.simulator in {'vcs', 'iverilog'}, f"unknown simulator: {args.simulator}"
    return Config(Path(args.working_dir), Path(args.results), sim=args.simulator, skip_rtl_sim=args.skip_rtl_sim)


def create_dir(working_dir: Path):
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
        return  # done
    results = load_results(result_tomls)

    # sort results to ensure deterministic results
    results = sorted(results, key=lambda r: r.name)

    # ensure that the working dir exists
    create_dir(conf.working_dir)

    # load all projects so that we can find the necessary info to evaluate repairs
    projects = load_all_projects()

    # check each result
    print("Checking Repairs:")
    for res in results:
        print(res.name)
        bb = find_benchmark(projects, res)
        # create a folder for this result
        result_working_dir = conf.working_dir / res.name
        create_dir(result_working_dir)
        # open a log file
        logfile_name = conf.working_dir / f"{res.name}.log"
        with open(logfile_name, 'w') as logfile:
            print(f"Checking: {res}", file=logfile)
            # if we have an original, we want to make sure that our tests work on that
            if bb.bug.original is not None:
                fake_repair = Repair(filename=bb.bug.original)
                print(f"Original: {fake_repair}", file=logfile)
                sys.stdout.write(f"  - {fake_repair.filename.name}:")
                repair_dir = result_working_dir / fake_repair.filename.stem
                create_dir(repair_dir)
                check_repair(conf, repair_dir, logfile, bb, fake_repair)
                print()
            for repair in res.repairs:
                print(f"Repair: {repair}", file=logfile)
                sys.stdout.write(f"  - {repair.filename.name}:")
                repair_dir = result_working_dir / repair.filename.stem
                create_dir(repair_dir)
                check_repair(conf, repair_dir, logfile, bb, repair)
                print()


if __name__ == '__main__':
    main()
