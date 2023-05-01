#!/usr/bin/env python3
# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import os
import sys
import random
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
import concurrent.futures

# check to make sure we have the correct venv activated
import pyverilog

_root_dir = Path(__file__).parent.resolve()
_prototype_dir = _root_dir / "prototype"
_repair_py = _prototype_dir / "repair.py"


# add _repository_ root to python path to find `benchmarks` module
sys.path.append(str(_root_dir.parent))
import benchmarks

@dataclass
class Config:
    working_dir: Path
    skip_existing: bool
    experiment: str
    threads: int
    simulator: str


@dataclass
class Run:
    name: str
    working_dir: Path
    project: Path
    bug: str
    seed: str
    timeout: float


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='run repairs')
    parser.add_argument("--working-dir", dest="working_dir", required=True)
    parser.add_argument("--skip-existing", dest="skip", action="store_true", default=False)
    parser.add_argument("--clear", dest="clear", help="clear working dir", action="store_true", default=False)
    parser.add_argument("--experiment", default="cirfix-paper")
    parser.add_argument("--threads", default="1")
    parser.add_argument("--simulator", default="vcs")
    args = parser.parse_args()

    # check seed option
    assert args.experiment in experiments, f"{args.experiment} is not supported, try: {list(experiments.keys())}"

    # parse and create working dir
    working_dir = Path(args.working_dir)
    parent_dir = working_dir.parent
    assert parent_dir.exists(), f"{parent_dir} does not exist"
    assert parent_dir.is_dir(), f"{parent_dir} is not a directory"
    if args.clear and working_dir.exists():
        shutil.rmtree(working_dir)
    if not working_dir.exists():
        os.mkdir(working_dir)

    #
    threads = int(args.threads)
    assert threads >= 1, f"{threads} < 1!"

    #
    simulator = args.simulator
    assert simulator in {'iverilog', 'vcs'}, simulator

    return Config(
        working_dir=working_dir,
        skip_existing=args.skip,
        experiment=args.experiment,
        threads=threads,
        simulator=simulator,
    )


def check_exists(working_dir: Path) -> bool:
    if not working_dir.exists():
        return False
    if not working_dir.is_dir():
        return False
    time = working_dir / "time.txt"
    if not time.exists():
        return False
    return True


_vcs_files = ["csrc", "simv", "simv.daidir", "ucli.key"]
_pyverilog_files = ["parser.out", "parsetab.py"]
_python_files = ["__pycache__"]

def cleanup_files(working_dir: Path, files: list):
    """ deletes directories and files in the working dir if they exist """
    for filename in files:
        ff = working_dir / filename
        if ff.exists():
            if ff.is_file():
                os.remove(ff)
            else:
                shutil.rmtree(ff)
        else:
            pass


def find_output_txt(working_dir: Path) -> list:
    """ tries to identify the testbench output file in the working dir """
    candidates = list(working_dir.glob("output_*.txt"))
    if len(candidates) == 1:
        return [candidates[0].name]
    else:
        return []


def do_run(conf: Config, run: Run) -> bool:
    cmd = [
        _repair_py,
        "--project", str(run.project.resolve()),
        "--bug", run.bug,
        "--log",
        "--working-dir", str(run.working_dir.resolve()),
        "--seed", run.seed,
        "--simulator", conf.simulator,
    ]

    # skip existing
    if conf.skip_existing and check_exists(run.working_dir):
        return True

    # delete working dir if it does exist
    if run.working_dir.exists():
        assert run.working_dir.is_dir()
        shutil.rmtree(run.working_dir)
    # create a new working dir
    os.mkdir(run.working_dir)

    stdout_file = conf.working_dir / f"{run.name}.log"

    try:
        with open(stdout_file, "wb") as stdout:
            stdout.write(" ".join(str(p) for p in cmd).encode('utf-8') + b"\n")
            stdout.flush()
            r = subprocess.run(cmd, cwd=run.working_dir, stdout=stdout, stderr=subprocess.STDOUT, timeout=run.timeout)
            success = r.returncode == 0
    except TimeoutError:
        print(f"{run.name}: timeout after {run.timeout}")
        success = False

    # cleanup temporary files in order to safe diskspace
    files_to_clean = _pyverilog_files + _python_files
    if conf.simulator == "vcs":
        files_to_clean += _vcs_files
    files_to_clean += find_output_txt(run.working_dir)
    cleanup_files(run.working_dir, files_to_clean)

    return success


def make_run(conf: Config, bb: benchmarks.Benchmark, seed: str, project_toml: Path, timeout_s: float) -> Run:
    """ helper function to construct a run from common parameters """
    name = f"{bb.project.name}_{bb.bug.name}_{seed}"
    return Run(
        name=name,
        working_dir=conf.working_dir / name,
        project=project_toml,
        bug=bb.bug.name,
        seed=seed,
        timeout=timeout_s,
    )

def cirfix_paper_experiment(conf: Config, projects: dict) -> list:
    """ Reproduce the CirFix Paper numbers (for benchmarks that did not time out) with the right seeds """
    runs = []
    timeout_h = 16  # 16h instead of 12h since our machine is slower
    timeout_s = timeout_h * 60 * 60.0

    for name, project in projects.items():
        project_toml = benchmarks.projects[name]
        bbs = benchmarks.get_benchmarks(project)
        for bb in bbs:
            seed = benchmarks.get_seed(bb)
            if seed is None:
                continue
            runs.append(make_run(conf, bb, seed, project_toml, timeout_s))
    return runs

def cirfix_with_10_seeds_experiment(conf: Config, projects: dict) -> list:
    """ run each cirfix repair experiment 10 times with different seeds """
    runs = []
    timeout_h = 16  # 16h instead of 12h since our machine is slower
    timeout_s = timeout_h * 60 * 60.0
    number_of_runs = 10

    for name, project in projects.items():
        project_toml = benchmarks.projects[name]
        bbs = benchmarks.get_benchmarks(project)
        for bb in bbs:
            for ii in range(number_of_runs):
                seed = f"{ii}"
                runs.append(make_run(conf, bb, seed, project_toml, timeout_s))
    return runs


def single_benchmark_experiment(project_name: str, conf: Config, projects: dict, bug_name: str = None) -> list:
    runs = []
    timeout_h = 16  # 16h instead of 12h since our machine is slower
    timeout_s = timeout_h * 60 * 60.0

    project = projects[project_name]
    project_toml = benchmarks.projects[project_name]
    bbs = benchmarks.get_benchmarks(project)
    for bb in bbs:
        seed = benchmarks.get_seed(bb)
        if seed is None:
            seed = "0"
        if bug_name is None or bb.bug.name == bug_name:
            runs.append(make_run(conf, bb, seed, project_toml, timeout_s))
    return runs


def sha3_permutation_experiment(conf: Config, projects: dict) -> list:
    """ There seem to be some problems with this benchmark, this config helps us debug. """
    return single_benchmark_experiment("sha3_f_permutation", conf, projects)


def first_counter_overflow_wadden_buggy1_experiment(conf: Config, projects: dict) -> list:
    """ Simple benchmark that can be solved quickly for testing things out. """
    return single_benchmark_experiment("first_counter_overflow", conf, projects, "wadden_buggy1")


def mux_checks_experiment(conf: Config, projects: dict) -> list:
    """ Two mux_4_1 benchmarks did not yield a solution for the seeds in the 10-seed experiment
        Here we re-run some of these seeds + the original seed from the CirFix paper to check what is going on.
    """
    runs = []
    timeout_h = 16  # 16h instead of 12h since our machine is slower
    timeout_s = timeout_h * 60 * 60.0
    number_of_runs = 4 # 4 numberic seeds + original seed
    name = "mux_4_1"
    bugs = {"wadden_buggy1", "wadden_buggy2"}
    project = projects[name]

    project_toml = benchmarks.projects[name]
    bbs = benchmarks.get_benchmarks(project)
    for bb in bbs:
        if bb.bug.name not in bugs:
            continue
        for ii in range(number_of_runs):
            seed = f"{ii}"
            runs.append(make_run(conf, bb, seed, project_toml, timeout_s))
        seed = benchmarks.get_seed(bb)
        runs.append(make_run(conf, bb, seed, project_toml, timeout_s))
    return runs

experiments = {
    'cirfix-paper': cirfix_paper_experiment,
    '10-seeds': cirfix_with_10_seeds_experiment,
    'sha3-permutation': sha3_permutation_experiment,
    'first-counter-wadden-1': first_counter_overflow_wadden_buggy1_experiment,
    'mux-checks': mux_checks_experiment,
}


def get_time_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def do_run_with_msg(conf: Config, run: Run) -> (bool, float):
    print(f"➡️[{get_time_str()}] {run.name} started")
    start = time.time()
    success = do_run(conf, run)
    status = "finished" if success else "failed"
    status_icon = "✔️" if success else "❌"
    delta = time.time() - start
    print(f"{status_icon}[{get_time_str()}] {run.name} {status} after {delta}s")
    return status, delta


def execute_in_parallel(conf: Config, runs: list[Run]):
    # (deterministically) randomise runs in order to not cluster the same experiment
    random.Random(4).shuffle(runs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=conf.threads) as executor:
        results = []
        for run in runs:
            r = executor.submit(do_run_with_msg, conf, run)
            results.append((run, r))


def main():
    conf = parse_args()
    projects = benchmarks.load_all_projects()
    bbs = []
    for _, proj in projects.items():
        bbs += benchmarks.get_benchmarks(proj)
    runs = experiments[conf.experiment](conf, projects)
    print(f"Running Experiment: {conf.experiment}")
    execute_in_parallel(conf, runs)


if __name__ == '__main__':
    main()
