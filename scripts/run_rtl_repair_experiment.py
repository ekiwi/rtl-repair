#!/usr/bin/env python3
# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import tomli
import sys
import os
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass
import subprocess

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
_root_dir = _script_dir.parent
sys.path.append(str(_root_dir))
import benchmarks
from benchmarks import Benchmark

# global experiment default settings
_solver = 'bitwuzla'
_incremental = True
_init = 'random'  # the incremental solver always uses random init
_timeout = 60  # one minute timeout
_verbose_synth = True

@dataclass
class ExpConfig:
    incremental: bool
    timeout: int    # per template timeout when all_templates is true
    all_templates: bool

@dataclass
class Config:
    working_dir: Path
    skip_existing: bool
    experiment: str


# possible experiments:
ExpDefault = 'default'
ExpAllTemplates = 'all-templates'
ExpBasicSynth = 'basic-synth'
Exps = [ExpDefault, ExpAllTemplates, ExpBasicSynth]
Configs: dict[str, ExpConfig] = {
    ExpDefault: ExpConfig(incremental=True, timeout=_timeout, all_templates=False),
    ExpAllTemplates: ExpConfig(incremental=True, timeout=_timeout, all_templates=True),
    ExpBasicSynth: ExpConfig(incremental=False, timeout=_timeout, all_templates=False),
}

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='run repairs')
    parser.add_argument("--working-dir", dest="working_dir", required=True)
    parser.add_argument("--skip-existing", dest="skip", action="store_true", default=False)
    parser.add_argument("--clear", dest="clear", help="clear working dir", action="store_true", default=False)
    parser.add_argument("--experiment", help=f'Pick one of: {Exps}', default=ExpDefault)
    args = parser.parse_args()

    assert args.experiment in Exps, f"Invalid experiment {args.experiment}, pick one of: {Exps}"

    # parse and create working dir
    working_dir = Path(args.working_dir)
    parent_dir = working_dir.parent
    assert parent_dir.exists(), f"{parent_dir} does not exist"
    assert parent_dir.is_dir(), f"{parent_dir} is not a directory"
    if args.clear and working_dir.exists():
        shutil.rmtree(working_dir)
    if not working_dir.exists():
        os.mkdir(working_dir)

    return Config(working_dir, args.skip, args.experiment)


def run_rtl_repair(working_dir: Path, benchmark: Benchmark, project_toml: Path, bug: str, testbench: str, solver, init,
                   incremental, timeout=None, all_templates: bool = False):
    # determine the directory name from project and bug name
    out_dir = working_dir / benchmark.name
    args = [
        "--project", str(project_toml.resolve()),
        "--solver", solver,
        "--working-dir", str(out_dir.resolve()),
        "--init", init,
    ]
    if bug:  # bug is optional to allow for sanity-check "repairs" of the original design
        args += ["--bug", bug]
    if testbench:
        args += ["--testbench", testbench]
    if incremental:
        args += ["--incremental"]
    if all_templates:
        args += ["--run-all-templates"]
        if timeout is not None:
            args += [f"--template-timeout", str(timeout)]
    elif timeout is not None:
        args += [f"--timeout", str(timeout)]
    if _verbose_synth:
        args += ["--verbose-synthesizer"]

    cmd = ["./rtlrepair.py"] + args
    # for debugging:
    cmd_str = ' '.join(cmd)
    
    # run from working directory, this is necessary because PyVerilog creates some
    # temporary files that might otherwise conflict with other experiments that are
    # run in parallel
    cwd = working_dir

    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, check=True, cwd=cwd)
    except subprocess.CalledProcessError as r:
        print(f"Failed to execute command: {cmd_str}")
        return 'failed', 0, None

    with open(out_dir / "result.toml", 'rb') as ff:
        dd = tomli.load(ff)
    status = dd['custom']['status']
    if dd['result']['success']:
        repairs = dd['repairs']
        template = repairs[0]['template']
        changes = repairs[0]['changes']
    else:
        changes = 0
        template = None

    return status, changes, template


def run_all_cirfix_benchmarks(conf: Config, projects: dict):
    for name, project in projects.items():
        # overwrite for manual adjustments that we had to make
        if name in benchmarks.rtlrepair_replacements:
            project_toml = benchmarks.rtlrepair_replacements[name]
            project = benchmarks.load_project(project_toml)
        else:
            project_toml = benchmarks.projects[name]
        testbench = benchmarks.pick_trace_testbench(project)
        bbs = benchmarks.get_benchmarks(project)
        for bb in bbs:
            assert isinstance(bb, Benchmark)
            if not benchmarks.is_cirfix_paper_benchmark(bb):
                continue
            sys.stdout.write(f"{bb.name} w/ {testbench.name}")
            sys.stdout.flush()
            exp_conf = Configs[conf.experiment]
            status, changes, template = run_rtl_repair(conf.working_dir, bb, project_toml, bb.bug.name,
                                                       testbench=testbench.name, solver=_solver, init=_init,
                                                       incremental=exp_conf.incremental,
                                                       timeout=exp_conf.timeout,
                                                       all_templates=exp_conf.all_templates)
            print(f" --> {status}")

    pass


def main():
    conf = parse_args()
    projects = benchmarks.load_all_projects()
    run_all_cirfix_benchmarks(conf, projects)


if __name__ == '__main__':
    main()
