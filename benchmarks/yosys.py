# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# interface code for yosys

import subprocess
from pathlib import Path


_minimal_btor_conversion = [
    "proc -noopt",
    "async2sync",  # required for designs with async reset
    "flatten",
    "dffunmap",
]

# inspired by the commands used by SymbiYosys
_btor_conversion = [
    "proc",
    # common prep
    "async2sync",
    "opt_clean",
    "setundef -anyseq",
    "opt -keepdc -fast",
    "check",
    # "hierarchy -simcheck",
    # btor
    "flatten",
    "setundef -undriven -anyseq",
    "dffunmap",
]

def _check_exists(working_dir: Path, sources: list):
    for src in sources:
        assert src.exists(), f"{src} does not exist"
    if working_dir is not None:
        assert working_dir.exists(), f"directory {working_dir} does not exist"

def _require_yosys():
    r = subprocess.run(["yosys", "-version"], check=False, stdout=subprocess.PIPE)
    assert r.returncode == 0, f"failed to find yosys {r}"

def _read_sources(sources: list, top: str) -> list:
    read_cmd = [f"read_verilog {src.resolve()}" for src in sources]
    if top is not None:
        read_cmd += [f"hierarchy -top {top}"]
    return read_cmd

def _run_yosys(working_dir: Path, yosys_cmds: list, script_out: Path = None, logfile = None) -> str:
    cmd = ["yosys", "-p", " ; ".join(yosys_cmds)]
    if script_out is not None:
        with open(script_out, "w") as f:
            print("#!/usr/bin/env bash", file=f)
            print("yosys -p \"" + ' ; '.join(yosys_cmds) + '"', file=f)
    stderr = None if logfile is None else logfile
    r = subprocess.run(cmd, check=True, cwd=working_dir, stdout=subprocess.PIPE, stderr=stderr)
    stdout = r.stdout.decode('utf-8')
    if logfile is not None:
        print(stdout, file=logfile)
    return stdout

def to_btor(working_dir: Path, btor_name: Path, sources: list, top: str = None, script_out: Path = None):
    _check_exists(working_dir, sources)
    _require_yosys()
    conversion = _minimal_btor_conversion
    yosys_cmd = _read_sources(sources, top) + conversion + [f"write_btor -x {btor_name.resolve()}"]
    _run_yosys(working_dir, yosys_cmd, script_out=script_out)
    assert btor_name.exists()
    return btor_name

def to_gatelevel_netlist(working_dir: Path, output: Path, sources: list, top: str = None, logfile = None):
    _check_exists(working_dir, sources)
    _require_yosys()
    yosys_cmd = _read_sources(sources, top) + ["synth", f"write_verilog {output.resolve()}"]
    _run_yosys(working_dir, yosys_cmd, logfile)
    assert output.exists()
    return output


def to_json(working_dir: Path, output: Path, sources: list, top: str = None):
    _check_exists(working_dir, sources)
    _require_yosys()
    yosys_cmd = _read_sources(sources, top) + ["proc -noopt", f"write_json {output.resolve()}"]
    _run_yosys(working_dir, yosys_cmd)
    assert output.exists()
    return output
