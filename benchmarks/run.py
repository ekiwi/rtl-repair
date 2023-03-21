# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# contains code to execute benchmarks

import subprocess
from pathlib import Path
from dataclasses import dataclass
import os

@dataclass
class RunConf:
    include_dir: Path = None
    timeout: float = None
    compile_timeout: float = None
    verbose: bool = False
    show_stdout: bool = False


def run(working_dir: Path, sim: str, files: list, conf: RunConf) -> bool:
    if sim == 'vcs':
        return run_with_vcs(working_dir, files, conf)
    elif sim == 'iverilog':
        run_with_iverilog(working_dir, files, conf)
    else:
        raise NotImplementedError(f"Simulator `{sim}` is not supported! Try `vcs` or `iverilog`!")


def run_with_iverilog(working_dir: Path, files: list, conf: RunConf) -> bool:
    cmd = ['iverilog', '-g2012']
    if conf.include_dir is not None:
        cmd += ["-I", str(conf.include_dir.resolve())]
    cmd += files
    if conf.verbose:
        print(" ".join(str(c) for c in cmd))
    stdout = None if conf.show_stdout else subprocess.PIPE
    # while iverilog generally does not timeout, we add the timeout here for feature parity with the VCS version
    try:
        r = subprocess.run(cmd, cwd=working_dir, check=False, stdout=stdout, timeout=conf.compile_timeout)
        compiled_successfully = r.returncode == 0
    except subprocess.TimeoutExpired:
        compiled_successfully = False
    # if the simulation does not compile, we won't run anything
    if compiled_successfully:
        try:
            if conf.verbose:
                print('./a.out')
            r = subprocess.run(['./a.out'], cwd=working_dir, shell=True, timeout=conf.timeout, stdout=stdout)
            success = r.returncode == 0
        except subprocess.TimeoutExpired:
            success = False  # failed
        os.remove(os.path.join(working_dir, 'a.out'))
        return  success
    else:
        return False # failed to compile


_vcs_flags = ["-sverilog", "-full64"]


def run_with_vcs(working_dir: Path, files: list, conf: RunConf) -> bool:
    cmd = ["vcs"] + _vcs_flags
    if conf.include_dir is not None:
        cmd += [f"+incdir+{str(conf.include_dir.resolve())}"]
    cmd += files
    if conf.verbose:
        print(" ".join(str(c) for c in cmd))
    stdout = None if conf.show_stdout else subprocess.PIPE
    # VCS can take hours to compile for some changes ...
    try:
        r = subprocess.run(cmd, cwd=working_dir, check=False, stdout=stdout, timeout=conf.compile_timeout)
        compiled_successfully = r.returncode == 0
    except subprocess.TimeoutExpired:
        compiled_successfully = False
    # if the simulation does not compile, we won't run anything
    if compiled_successfully:
        try:
            if conf.verbose:
                print('./simv')
            r = subprocess.run(['./simv'], cwd=working_dir, shell=False, timeout=conf.timeout, stdout=stdout)
            success = r.returncode == 0
        except subprocess.TimeoutExpired:
            success = False # failed
        return success
    else:
        return False # failed to compile