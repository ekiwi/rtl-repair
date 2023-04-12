#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# Tries to identify all state, i.e. registers and memories in the design.
# Note: currently this assumes that there will be no latches, only FFs in the design!

import argparse
import json
import tempfile
from pathlib import Path
from dataclasses import dataclass

from benchmarks import Design, load_project
from benchmarks.yosys import to_json



@dataclass
class Module:
    name: str
    instances: list
    state: list

def parse_yosys_output(out_json: Path) -> list:
    with open(out_json) as ff:
        dd = json.load(ff)
    rr = []
    # print(dd)
    module_names = set(dd["modules"].keys())
    for name, module in dd["modules"].items():
        rr.append(parse_module(module_names, name, module))
    return rr


def bits_to_key(bits: list) -> str:
    return str(sorted(bits))

def parse_module(module_names: set, name: str, module: dict) -> Module:
    # create a dictionary to look up signal names
    bits_to_name = {bits_to_key(dd['bits']): nn for nn, dd in module["netnames"].items()}
    # look through all cells to identify submodules, registers and memories
    state = []
    instances = []
    # keep track of memory read and write ports
    read_mems = set()
    write_mems = set()
    def get_mem_name(_cell: dict) -> str:
        _raw = _cell['parameters']['MEMID']
        _out = _raw[1:] # skip `\`
        return _out
    for cell_name, cell in module["cells"].items():
        tpe = cell["type"]
        if tpe == "$dff":
            bits = cell['connections']['Q']
            width = len(bits)
            signal_name = bits_to_name[bits_to_key(bits)]
            state.append((signal_name, width))
        elif tpe in {"$memrd_v2", "$memrd"}:
            read_mems.add(get_mem_name(cell))
        elif tpe in {"$memwr_v2", "$memwr"}:
            write_mems.add(get_mem_name(cell))
        elif tpe in module_names:
            instances.append((cell_name, tpe))


    # iterate over memories
    if "memories" in module:
        for mem_name, mem in module["memories"].items():
            # we can tell what kind of memory it is by looking at the read/write ports
            is_read = mem_name in read_mems
            is_written = mem_name in write_mems
            tpe = ("r" if is_read else "") + ("w" if is_written else "")
            assert tpe in {'r', 'rw'} , "expected `r` or `rw`"
            # extract size
            width = mem['width']
            depth = mem['size']
            state.append((mem_name, (width, depth, tpe)))

    return Module(name, instances, state)

def find_state(working_dir: Path, design: Design):
    yosys_json = to_json(working_dir, working_dir / f"{design.top}.json", design.sources, design.top)
    modules = parse_yosys_output(yosys_json)
    flattened = flatten_states(design.top, modules)
    print(flattened)


def flatten_states(top: str, modules: list) -> list:
    by_name = {m.name: m for m in modules}
    assert top in by_name, f"could not find top `{top}` in {list(by_name.keys())}"
    return flatten_states_rec(prefix="", name=top, mods_by_name=by_name)


def flatten_states_rec(prefix: str, name: str, mods_by_name: dict) -> list:
    mod = mods_by_name[name]
    state = [(f"{prefix}{name}", data) for name, data in mod.state]
    for instance_name, instance_mod in mod.instances:
        state += flatten_states_rec(f"{prefix}{instance_name}.", instance_mod, mods_by_name)
    return state

def parse_args() -> Design:
    parser = argparse.ArgumentParser(description='Find all registers and memory in a design.')
    parser.add_argument('project_file_name')
    args = parser.parse_args()
    proj = load_project(Path(args.project_file_name))
    return proj.design

def main():
    design = parse_args()
    # use temporary working dir
    with tempfile.TemporaryDirectory() as wd_name:
        working_dir = Path(wd_name)
        find_state(working_dir, design)

if __name__ == '__main__':
    main()