#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# runs rtlfix.py to generate a repair and presents the result to the user

import sys
from pathlib import Path
import subprocess
import tomli

_script_dir = Path(__file__).parent.resolve()
_root_dir = _script_dir.parent

sys.path.append(str(_script_dir.parent))
from benchmarks.result import load_result

# settings
solver = "bitwuzla"
init = "random"
timeout = 5


def main() -> int:
    proj_dir = _script_dir / "project"
    proj_toml = proj_dir / "project.toml"
    working_dir = proj_dir / "repair"

    cmd = ["./rtlfix.py",
           "--project", str(proj_toml.resolve()),
           "--solver", solver,
           "--init", init,
           "--working-dir", str(working_dir.resolve()),
           "--timeout", str(timeout)
           ]

    cmd_str = ' '.join(cmd)
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, check=True, cwd=_root_dir)
    except subprocess.CalledProcessError as r:
        print(f"Failed to execute command: {cmd_str}")
        raise r

    result = load_result(working_dir / "result.toml")
    status = result.custom['status']
    delta_seconds = result.seconds
    print(f"{status} ({delta_seconds:.02f}s)")
    if status == 'success':
        for ii, repair in enumerate(result.repairs):
            print(f"{ii}) Possible repair with {repair.meta['changes']} changes:")
            with open(repair.diff) as ff:
                print(ff.read())
            print("="*80)


    return 0


if __name__ == '__main__':
    sys.exit(main())
