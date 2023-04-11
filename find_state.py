#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# Tries to identify all state, i.e. registers and memories in the design.
# Note: currently this assumes that there will be no latches, only FFs in the design!

import argparse
import re
from pathlib import Path
from dataclasses import dataclass

from benchmarks import Design, load_project
from benchmarks.yosys import run_cmds_and_capture_output


_proc_dff_needle = "Executing PROC_DFF pass"
_register_re = re.compile(r"Creating register for signal `([^']+)'")
def parse_yosys_output(out: str) -> list:
    searching_for_proc_dff = True
    lines = out.splitlines()
    states = set() # for memories, there might be several entries, we use a set to avoid duplicates
    for line in lines:
        # we want to find the start of the DFF pass output
        if searching_for_proc_dff:
            searching_for_proc_dff = _proc_dff_needle not in line
            continue
        m = _register_re.match(line)
        if m is not None:
            name = m.group(1)
            states.add(parse_state_name(name))

    # sorted to make this deterministic
    state_list = sorted(list(states))
    return state_list


def parse_state_name(orig_name: str) -> (str, str, str):
    # remove any backslashes
    name = orig_name.replace('\\', '')
    parts = name.split('.')
    module = parts[0]
    name = parts[1]
    # normal register name: module.reg
    if len(parts) == 2 and not name.startswith('$'):
        return module, name, 'reg'
    # memory port regs get a special name
    # note: this is a little hacky, but not sure how to identify memories otherwise since
    #       the actual array to memory inference does not seem to get a print out in my yosys
    #       version
    name_parts = name.split('$')[1:]
    if len(name_parts) > 1:
        kind = name_parts[0]
        name = name_parts[1]
        assert 'mem' in kind, f"unexpected kind `{kind}` for {module}.{name}"
        return module, name, 'mem'
    raise NotImplementedError(f"unexpected state name: {orig_name}")


def find_state(design: Design):
    cmd = ["proc -noopt"]
    yosys_out = run_cmds_and_capture_output(design.directory, design.sources, cmd, design.top)
    states = parse_yosys_output(yosys_out)
    print(states)



def parse_args() -> Design:
    parser = argparse.ArgumentParser(description='Find all registers and memory in a design.')
    parser.add_argument('project_file_name')
    args = parser.parse_args()
    proj = load_project(Path(args.project_file_name))
    return proj.design

def main():
    design = parse_args()
    find_state(design)

if __name__ == '__main__':
    main()