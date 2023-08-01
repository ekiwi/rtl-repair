#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# creates the tables for the evaluation section of the RTL-Repair paper

import sys
from pathlib import Path
from dataclasses import dataclass

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
import benchmarks

# map benchmark to short name
project_short_names = {
    "decoder_3_to_8": "decoder",
    "first_counter_overflow": "counter",
    "flip_flop": "flop",
    "fsm_full": "fsm",
    "lshift_reg": "shift",
    "mux_4_1": "mux",
    "i2c_slave": "i2c",
    "i2c_master": "i2c",
    "sha3_keccak": "sha3",
    "sha3_padder": "sha3",
    "pairing": "pairing",
    "reed_solomon_decoder": "reed",
    "sdram_controller": "sdram",
}
to_short_name = {}
for project_name, entry in benchmarks.benchmark_to_cirfix_paper_table_3.items():
    to_short_name[project_name] = {}
    short = project_short_names[project_name]
    for bug in entry.keys():
        to_short_name[project_name][bug] = short + "_" + bug[0] + bug[-1]


@dataclass
class Config:
    working_dir: Path
    osdd_toml: Path
