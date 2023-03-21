# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import subprocess
import json
from pathlib import Path
from rtlfix.utils import _root_dir, serialize
import pyverilog.vparser.ast as vast
from benchmarks.yosys import to_btor

# the synthesizer is written in Scala, the source code lives in src
_jar_rel = Path("target") / "scala-2.13" / "bug-fix-synthesizer-assembly-0.1.jar"
_synthesizer_dir = _root_dir / "synthesizer"
_jar = _synthesizer_dir / _jar_rel


def _check_jar():
    assert _jar.exists(), f"Failed to find JAR, did you run sbt assembly?\n{_jar}"


def _run_synthesizer(design: Path, testbench: Path, solver: str, init: str, incremental: bool):
    assert design.exists(), f"{design=} does not exist"
    assert testbench.exists(), f"{testbench=} does not exist"
    _check_jar()
    args = ["--design", str(design), "--testbench", str(testbench), "--solver", solver, "--init", init]
    if incremental:
        args += ["--incremental"]
    cmd = ["java", "-cp", _jar, "synth.Synthesizer"] + args
    cmd_str = ' '.join(str(p) for p in cmd)  # for debugging
    r = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    try:
        return json.loads(r.stdout.decode('utf-8'))
    except json.JSONDecodeError as e:
        print("Failed to parse synthesizer output as JSON:")
        print(r.stdout)
        raise e


class Synthesizer:
    """ generates assignments to synthesis variables which fix the design according to a provided testbench """

    def __init__(self):
        pass

    def run(self, name: str, working_dir: Path, ast: vast.Source, testbench: Path, solver: str, init: str,
            incremental: bool, additional_sources: list, top: str, include: Path) -> dict:
        synth_filename = working_dir / name
        with open(synth_filename, "w") as f:
            f.write(serialize(ast))

        # convert file and run synthesizer
        btor_filename = to_btor(working_dir, working_dir / (synth_filename.stem + ".btor"), [synth_filename] + additional_sources, top)
        result = _run_synthesizer(btor_filename, testbench, solver, init, incremental)
        status = result["status"]
        with open(working_dir / "status", "w") as f:
            f.write(status + "\n")

        return result
