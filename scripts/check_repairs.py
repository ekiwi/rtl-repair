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
from enum import Enum
from pathlib import Path


# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
import benchmarks
from benchmarks import Benchmark, get_other_sources, VerilogOracleTestbench, get_benchmark, load_all_projects, Project, find_project_name_and_toml
from benchmarks.yosys import to_gatelevel_netlist
from benchmarks.run import run, RunConf, SimResult, check_against_oracle
from benchmarks.result import load_result, Result, Repair


@dataclass
class Config:
    working_dir: Path
    result_dir: Path
    sim: str
    skip_rtl_sim: bool


class TestResult(Enum):
    Pass = 0           # test passes with original and on the repaired version
    Fail = 1           # test passes with the original but not with the repaired version
    Indeterminate = 2  # test fails with the original and the repaired version (--> test result does not indicate anything)
    NA = 3             # test was not available

@dataclass
class RepairResult:
    rtl_sim: TestResult = TestResult.NA
    gatelevel_sim: TestResult = TestResult.NA
    extended_rtl_sim: TestResult = TestResult.NA
    iverilog_rtl_sim: TestResult = TestResult.NA


def _parse_csv_item(item: str) -> str:
    item = item.strip()
    if len(item) <= 1:
        return item
    if item[0] == '"' and item[-1] == '"':
        item = item[1:-1].strip()
    return item


def parse_csv_line(line: str) -> list:
    return [_parse_csv_item(n) for n in line.split(',')]


def check_sim(sim: str, working_dir: Path, logfile, benchmark: Benchmark, design_sources: list,
              max_cycles: int = None):
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    output = working_dir / benchmark.testbench.output
    # remove any previous output that might exist from a prior run
    if output.exists():
        os.remove(output)

    # copy over any memory initialization files from the testbench
    for init_file in benchmark.testbench.init_files:
        shutil.copy(init_file, working_dir)

    # run testbench
    tb_sources = benchmark.testbench.sources + design_sources
    run_conf = RunConf(include_dir=benchmark.design.directory,
                       verbose=False, show_stdout=False, logfile=logfile,
                       timeout=60 * 2, # 2 minutes max
                       # dump a trace for easier debugging
                       defines=[("DUMP_TRACE", 1)])
    if logfile:
        logfile.flush()
    run(working_dir, sim, tb_sources, run_conf)

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


def check_repair(conf: Config, working_dir: Path, logfile, project: Project, repair: Repair, bug_name: str, cirfix_tb: str,
                extended_tbs: list[str]) -> RepairResult:
    benchmark = get_benchmark(project, bug_name, cirfix_tb)
    result = RepairResult()
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    sys.stdout.flush()

    # if there is a manual port of the fix, then we want to use that instead of the original repair
    if repair.manual is not None:
        repair_filename = repair.manual
    else:
        repair_filename = repair.filename

    # copy over the oracle for easier debugging later
    shutil.copy(benchmark.testbench.oracle, working_dir)

    # by default, the gate level sim runs until it terminates
    max_cycles = None

    # first we just simulate and check the oracle
    if not conf.skip_rtl_sim:
        print(f"RTL Simulation with Oracle Testbench: {benchmark.testbench.name}", file=logfile)
        other_sources = get_other_sources(benchmark)
        run_logfile = working_dir / f"{repair_filename.stem}.sim.log"
        with open(run_logfile, 'w') as logff:
            sim_res = check_sim(conf.sim, working_dir, logff, benchmark, [repair_filename.resolve()] + other_sources)
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
        result.rtl_sim = TestResult.Pass if sim_res.is_success else TestResult.Fail

    # try to do the same simulation with iverilog as simulator
    # note: this could be skipped, if the script is configured to use iverilog instead of vcs
    #       however, in order to cover this code in our CI flow, we always execute this part
    if not conf.skip_rtl_sim:
        try:
            print(f"RTL Simulation with iVerilog and Oracle Testbench: {benchmark.testbench.name}", file=logfile)
            other_sources = get_other_sources(benchmark)
            run_logfile = working_dir / f"{repair_filename.stem}.sim.iverilog.log"
            with open(run_logfile, 'w') as logff:
                sim_res = check_sim("iverilog", working_dir, logff, benchmark, [repair_filename.resolve()] + other_sources)
            sys.stdout.write(f" iVerilog-RTL-sim {sim_res.emoji}")
            sys.stdout.flush()
            # rename output in order to preserve it
            try:
                shutil.move(working_dir / benchmark.testbench.output, working_dir / f"{benchmark.testbench.output}.iverilog.rtl")
            except:
                pass
            # rename trace
            if (working_dir / "dump.vcd").exists():
                shutil.move(working_dir / "dump.vcd", working_dir / "rtl.iverilog.vcd")
            result.iverilog_rtl_sim = TestResult.Pass if sim_res.is_success else TestResult.Fail
        except AssertionError: # if the whole iverilog thing does not work, well doesn't really matter
            result.iverilog_rtl_sim = TestResult.NA

    # synthesize to gates
    print(f"Synthesize to Gates: {benchmark.name}", file=logfile)
    other_sources = get_other_sources(benchmark)
    # synthesize
    gate_level = working_dir / f"{repair_filename.stem}.gatelevel.v"
    try:
        with open(working_dir / f"{repair_filename.stem}.synthesis.log", 'w') as gate_level_logfile:
            to_gatelevel_netlist(working_dir, gate_level, [repair_filename] + other_sources, top=benchmark.design.top,
                                 logfile=gate_level_logfile)
        synthesis_success = True
    except subprocess.CalledProcessError:
        synthesis_success = False
    sys.stdout.write(f" Synthesis {success_to_emoji(synthesis_success)}")
    sys.stdout.flush()

    # now we do the gate-level sim, do we get the same result?
    if synthesis_success:
        print(f"Gate-Level Simulation with Oracle Testbench: {benchmark.testbench.name}", file=logfile)
        run_logfile = working_dir / f"{repair_filename.stem}.gatelevel.sim.log"
        with open(run_logfile, 'w') as logff:
            gate_res = check_sim(conf.sim, working_dir, logff, benchmark, [gate_level.resolve()], max_cycles=max_cycles)
        sys.stdout.write(f" Gate-level {gate_res.emoji}")
        sys.stdout.flush()
        # rename trace
        if (working_dir / "dump.vcd").exists():
            shutil.move(working_dir / "dump.vcd", working_dir / "gatelevel.vcd")
        result.gatelevel_sim = TestResult.Pass if gate_res.is_success else TestResult.Fail

    # is there an extended testbench?
    for extended_name in extended_tbs:
        benchmark = get_benchmark(project, bug_name, extended_name)
        assert isinstance(benchmark.testbench, VerilogOracleTestbench)

        # copy over the oracle for easier debugging later
        shutil.copy(benchmark.testbench.oracle, working_dir)

        print(f"RTL Simulation with Extended Oracle Testbench: {benchmark.testbench.name}", file=logfile)
        other_sources = get_other_sources(benchmark)
        run_logfile = working_dir / f"{repair_filename.stem}.sim.{benchmark.testbench.name}.log"
        with open(run_logfile, 'w') as logff:
            sim_res = check_sim(conf.sim, working_dir, logff, benchmark, [repair_filename.resolve()] + other_sources)
        sys.stdout.write(f" Extended RTL-sim {sim_res.emoji}")
        sys.stdout.flush()
        # rename output in order to preserve it
        try:
            shutil.move(working_dir / benchmark.testbench.output, working_dir / f"{benchmark.testbench.output}.{benchmark.testbench.name}.rtl")
        except:
            pass
        # rename trace
        if (working_dir / "dump.vcd").exists():
            shutil.move(working_dir / "dump.vcd", working_dir / f"rtl.{benchmark.testbench.name}.vcd")
        result.extended_rtl_sim = TestResult.Pass if sim_res.is_success else TestResult.Fail
    return result


def find_benchmark(projects: dict, result: Result) -> Benchmark:
    project = projects[result.project_name]
    return get_benchmark(project, result.bug_name, use_trace_testbench=False)


def load_results(tomls: list[Path]) -> list[(Result, Path)]:
    res = []
    for toml in tomls:
        result_name = toml.parent.name
        res.append((load_result(toml, result_name), toml))
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


def combine_test_result(original: TestResult, repair: TestResult):
    assert original != TestResult.Indeterminate, "Indeterminate should only be used for repair results!"
    # if there is no original result, then we do not have a result at all
    if original == TestResult.NA:
        return TestResult.NA
    # if the test fails with the original, we cannot say anything about the quality of the repair
    if original == TestResult.Fail:
        return TestResult.Indeterminate
    # the test work with the original ground truth file
    assert original == TestResult.Pass
    return repair

def combine_repair_with_original_result(original: RepairResult, repair: RepairResult) -> RepairResult:
    return RepairResult(
        rtl_sim=combine_test_result(original.rtl_sim, repair.rtl_sim),
        gatelevel_sim=combine_test_result(original.gatelevel_sim, repair.gatelevel_sim),
        extended_rtl_sim=combine_test_result(original.extended_rtl_sim, repair.extended_rtl_sim),
        iverilog_rtl_sim=combine_test_result(original.iverilog_rtl_sim, repair.iverilog_rtl_sim),
    )

def write_check_toml(filename: Path, repair_check_results: dict[str,RepairResult], cirfix_table_3: str):
    with open(filename, 'w') as ff:
        print(f"# generated by a script: {__file__}", file=ff)
        for name, res in repair_check_results.items():
            print("", file=ff)
            print("[[checks]]", file=ff)
            print(f'name="{name}"', file=ff)
            print("# results of running Verilog testbenches", file=ff)
            print(f'rtl-sim="{res.rtl_sim.name.lower()}"', file=ff)
            print(f'gate-sim="{res.gatelevel_sim.name.lower()}"', file=ff)
            print(f'extended-sim="{res.extended_rtl_sim.name.lower()}"', file=ff)
            print(f'iverilog-sim="{res.iverilog_rtl_sim.name.lower()}"', file=ff)
            print("# reported result from the CirFix paper", file=ff)
            if cirfix_table_3 == 'correct':
                tool, human = TestResult.Pass, TestResult.Pass
            elif cirfix_table_3 == 'plausible':
                tool, human = TestResult.Pass, TestResult.Fail
            else:
                assert cirfix_table_3 == 'timeout'
                tool, human = TestResult.Fail, TestResult.Fail
            print(f'cirfix-tool="{tool.name.lower()}"', file=ff)
            print(f'cirfix-author="{human.name.lower()}"', file=ff)


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
    results = sorted(results, key=lambda r: r[0].name)

    # ensure that the working dir exists
    create_dir(conf.working_dir)

    # load all projects so that we can find the necessary info to evaluate repairs
    projects = load_all_projects()

    # check each result
    print("Checking Repairs:")
    for res, res_toml in results:
        print(res.name)

        # identify testbenches
        project = projects[res.project_name]
        tbs: list[VerilogOracleTestbench] = [tb for tb in project.testbenches if isinstance(tb, VerilogOracleTestbench)]
        cirfix_tbs = [tb for tb in tbs if "cirfix" in tb.tags]
        cirfix_tb = (tbs[0] if len(cirfix_tbs) == 0 else cirfix_tbs[0]).name
        extended_tbs = [tb.name for tb in tbs if "extended" in tb.tags]
        bug = next(bb for bb in project.bugs if bb.name == res.bug_name)

        # create a folder for this result
        result_working_dir = conf.working_dir / res.name
        create_dir(result_working_dir)

        # copy over project and result toml
        shutil.copy(src=res_toml, dst=result_working_dir)
        project_toml = find_project_name_and_toml(benchmarks.projects[project.name])[1]
        shutil.copy(src=project_toml, dst=result_working_dir)

        # open a log file
        logfile_name = conf.working_dir / f"{res.name}.log"

        # keep track of results
        repair_check_results = {}

        with open(logfile_name, 'w') as logfile:
            print(f"Checking: {res}", file=logfile)
            # if we have an original, we want to make sure that our tests work on that
            if bug.original is not None:
                fake_repair = Repair(filename=bug.original)
                print(f"Original: {fake_repair}", file=logfile)
                sys.stdout.write(f"  - {fake_repair.filename.name}:")
                repair_dir = result_working_dir / fake_repair.filename.stem
                create_dir(repair_dir)
                orig_res = check_repair(conf, repair_dir, logfile, project, fake_repair, bug.name, cirfix_tb, extended_tbs)
                print()
            else:
                orig_res = RepairResult()
            for repair in res.repairs:
                print(f"Repair: {repair}", file=logfile)
                sys.stdout.write(f"  - {repair.filename.name}:")
                repair_dir = result_working_dir / repair.filename.stem
                create_dir(repair_dir)
                res = check_repair(conf, repair_dir, logfile, project, repair, bug.name, cirfix_tb, extended_tbs)
                res = combine_repair_with_original_result(orig_res, res)
                repair_check_results[repair.filename.stem] = res
                print()

        # create a check.toml
        cirfix_table_3 = benchmarks.benchmark_to_cirfix_paper_table_3[project.name][bug.name]
        write_check_toml(result_working_dir / "check.toml", repair_check_results, cirfix_table_3=cirfix_table_3[3])


if __name__ == '__main__':
    main()
