# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import subprocess
import json
from dataclasses import dataclass
from pathlib import Path

from benchmarks import Benchmark, TraceTestbench, get_other_sources
from rtlfix.utils import _root_dir, serialize, Status, status_name_to_enum
import pyverilog.vparser.ast as vast
from benchmarks.yosys import to_btor

# the synthesizer is written in Scala, the source code lives in src
_jar_rel = Path("target") / "scala-2.13" / "bug-fix-synthesizer-assembly-0.1.jar"
_synthesizer_dir = _root_dir / "synthesizer"
_jar = _synthesizer_dir / _jar_rel


@dataclass
class SynthOptions:
    solver: str
    init: str
    incremental: bool

def _check_jar():
    assert _jar.exists(), f"Failed to find JAR, did you run sbt assembly?\n{_jar}"


def _run_synthesizer(working_dir: Path, design: Path, testbench: Path, opts: SynthOptions) -> dict:
    assert design.exists(), f"{design=} does not exist"
    assert testbench.exists(), f"{testbench=} does not exist"
    _check_jar()
    args = ["--design", str(design), "--testbench", str(testbench), "--solver", opts.solver, "--init", opts.init]
    if opts.incremental:
        args += ["--incremental"]
    # test: multiple solutions
    # args += ["--sample-solutions", "2"]
    cmd = ["java", "-cp", _jar, "synth.Synthesizer"] + args
    cmd_str = ' '.join(str(p) for p in cmd)  # for debugging
    r = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    output = r.stdout.decode('utf-8')
    # command write output to file for debugging
    with open(working_dir / "synth.txt", 'w') as ff:
        print(cmd_str, file=ff)
        ff.write(output)
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        print("Failed to parse synthesizer output as JSON:")
        print(r.stdout)
        raise e



class Synthesizer:
    """ generates assignments to synthesis variables which fix the design according to a provided testbench """

    def __init__(self):
        pass

    def run(self, working_dir: Path, opts: SynthOptions, instrumented_ast: vast.Source, benchmark: Benchmark) -> (Status, list):
        assert isinstance(benchmark.testbench, TraceTestbench), f"{benchmark.testbench} : {type(benchmark.testbench)} is not a TraceTestbench"

        # save instrumented AST to disk so that we can call yosys
        synth_filename = working_dir / f"{benchmark.bug.buggy.stem}.instrumented.v"
        with open(synth_filename, "w") as f:
            f.write(serialize(instrumented_ast))

        # convert file and run synthesizer
        additional_sources = get_other_sources(benchmark)
        btor_filename = to_btor(working_dir, working_dir / (synth_filename.stem + ".btor"),
                                [synth_filename] + additional_sources, benchmark.design.top)
        result = _run_synthesizer(working_dir, btor_filename, benchmark.testbench.table, opts)

        status = status_name_to_enum[result['status']]
        solutions = []
        if status == Status.Success:
            solutions = [s['assignment'] for s in result['solutions']]

        return status, solutions
