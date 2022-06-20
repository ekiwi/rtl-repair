# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import subprocess
import json
from pathlib import Path
from rtlfix import _root_dir, serialize
import pyverilog.vparser.ast as vast


# the synthesizer is written in Scala, the source code lives in src
_jar_rel = Path("target") / "scala-2.13" / "bug-fix-synthesizer-assembly-0.1.jar"
_synthesizer_dir = _root_dir / "synthesizer"
_jar = _synthesizer_dir / _jar_rel


def _check_jar():
    assert _jar.exists(), f"Failed to find JAR, did you run sbt assembly?\n{_jar}"


def _run_synthesizer(design: Path, testbench: Path, solver: str):
    assert design.exists(), f"{design=} does not exist"
    assert testbench.exists(), f"{testbench=} does not exist"
    _check_jar()
    args = ["--design", str(design), "--testbench", str(testbench), "--solver", solver]
    cmd = ["java", "-cp", _jar_rel, "synth.Synthesizer"] + args
    r = subprocess.run(cmd, cwd=_synthesizer_dir, check=True, stdout=subprocess.PIPE)
    return json.loads(r.stdout.decode('utf-8'))


def _to_btor(filename: Path):
    cwd = filename.parent
    assert cwd.exists(), f"directory {cwd} does not exist"
    r = subprocess.run(["yosys", "-version"], check=False, stdout=subprocess.PIPE)
    assert r.returncode == 0, f"failed to find yosys {r}"
    btor_name = filename.stem + ".btor"
    yosys_cmd = f"read_verilog {filename.name} ; proc ; write_btor -x {btor_name}"
    subprocess.run(["yosys", "-p", yosys_cmd], check=True, cwd=cwd, stdout=subprocess.PIPE)
    assert (cwd / btor_name).exists()
    return cwd / btor_name


class Synthesizer:
    """ generates assignments to synthesis variables which fix the design according to a provided testbench """
    def __init__(self):
        pass

    def run(self, name: str, working_dir: Path, ast: vast.Source, testbench: Path, solver: str) -> dict:
        synth_filename = working_dir / name
        with open(synth_filename, "w") as f:
            f.write(serialize(ast))

        # convert file and run synthesizer
        btor_filename = _to_btor(synth_filename)
        result = _run_synthesizer(btor_filename, testbench, solver)
        status = result["status"]
        with open(working_dir / "status", "w") as f:
            f.write(status + "\n")

        return result
