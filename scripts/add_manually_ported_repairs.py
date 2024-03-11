#!/usr/bin/env python3
# Copyright 2024 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# searches a results folder for repairs that on the `i2c_master` or `sdram` designs and
# tries to add a manual repair port if possible

import sys
import tomli
import argparse
import shutil
from pathlib import Path

from check_repairs import find_result_toml, load_results

# add root dir in order to be able to load "benchmarks" modules
_script_dir = Path(__file__).parent.resolve()
_root_dir  = _script_dir.parent
sys.path.append(str(_root_dir))

import benchmarks
import benchmarks.result
from benchmarks.run import success_to_emoji


def parse_args() -> Path:
    parser = argparse.ArgumentParser(description='finds repairs that need to manually be ported')
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory', required=True)
    args = parser.parse_args()
    return Path(args.working_dir)


projects = {'i2c_master', 'sdram_controller'}

_res_dir = _root_dir / 'results' / 'manual-port'
repairs = {
    'i2c_master': {
        'kgoliya_buggy1': (
            _res_dir / 'i2c_master_bit_ctrl_kgoliya_buggy1.sync_reset.repaired.0.v',
            _res_dir / 'i2c_master_bit_ctrl_kgoliya_buggy1.repaired.v'
        ),
    },
    'sdram_controller': {
        'kgoliya_buggy2': (
            _res_dir / 'sdram_controller_kgoliya_buggy2.no_tri_state.repaired.v',
            _res_dir / 'sdram_controller_kgoliya_buggy2.repaired.v'
        ),
        'wadden_buggy1': (
            _res_dir / 'sdram_controller_wadden_buggy1.no_tri_state.repaired.0.v',
            _res_dir / 'sdram_controller_wadden_buggy1.repaired.v'
        ),
        'wadden_buggy2': (
            _res_dir / 'sdram_controller_wadden_buggy2.no_tri_state.repaired.0.v',
            _res_dir / 'sdram_controller_wadden_buggy2.repaired.v'
        ),
    },
}

def main():
    working_dir = parse_args()
    assert working_dir.exists(), f"{working_dir.resolve()} does not exist"

    # find all result files
    result_tomls = find_result_toml(working_dir)
    if len(result_tomls) == 0:
        return  # done
    results = load_results(result_tomls)

    for res, res_toml in results:
        assert isinstance(res, benchmarks.result.Result)

        # match project name
        if res.project_name not in repairs:
            continue
        proj_repair = repairs[res.project_name]

        # match bug name
        if res.bug_name not in proj_repair:
            continue
        (original, ported) = proj_repair[res.bug_name]
        assert isinstance(ported, Path)

        # no repair
        if len(res.repairs) == 0:
            continue

        # check to see if repair matches expected
        repair = res.repairs[0]

        print(f"Found a repair for {res.project_name} ({res.bug_name}) in {repair.filename.parent}")

        if repair.manual is not None:
            print(f"- already manually ported to:\n{repair.manual}")
            continue

        # compare files
        with open(repair.filename) as f:
            repaired_verilog = f.read().strip()
        with open(original) as f:
            original_verilog = f.read().strip()
        if repaired_verilog == original_verilog:
            print(f"- {success_to_emoji(True)} repair ({repair.filename.name}) is the exact same as {original}")
        else:
            print(f"- {success_to_emoji(False)} repair ({repair.filename.name}) does not match the repair we expected")
            continue

        # add manual repair
        shutil.copy(src=ported, dst=repair.filename.parent)
        print(f"- {success_to_emoji(True)} copied {ported} to {repair.filename.parent}")

        # add manual repair to repair.toml
        with open(res_toml) as ff:
            toml_lines = [line.rstrip() for line in ff.readlines()]

        # find first repair
        repair_start_ii = next(ii for ii, line in enumerate(toml_lines) if line.strip() == '[[repairs]]')
        try:
            repair_end_ii = next(ii for ii, line in enumerate(toml_lines[repair_start_ii+1:]) if len(line.strip()) == 0 or line.strip().startswith('[')) + repair_start_ii + 1
        except StopIteration:
            repair_end_ii = len(toml_lines) - 1

        # add manual
        new_lines = [
            '# manual port of the repair to the original async-reset / tri-state bus version',
            '# inserted using the add_manually_ported_repairs.py script, manual port performed by Kevin Laeufer',
            f'manual="{ported.name}"'
        ]
        toml_lines = toml_lines[:repair_end_ii] + new_lines + toml_lines[repair_end_ii:]

        with open(res_toml, 'w') as ff:
            print('\n'.join(toml_lines), file=ff)
        print(f"- {success_to_emoji(True)} added manual port {ported.name} of repair to {res_toml}")





if __name__ == '__main__':
    main()
