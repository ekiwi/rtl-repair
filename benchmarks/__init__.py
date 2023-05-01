# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
# benchmark python library
import os.path
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import tomli

benchmark_dir = Path(__file__).parent.resolve()
_cirfix_benchmark_dir = benchmark_dir / "cirfix"
_opencores_dir = _cirfix_benchmark_dir / "opencores"
_sha3_dir = _opencores_dir / "sha3" / "low_throughput_core"

projects = {
    "decoder_3_to_8": _cirfix_benchmark_dir / "decoder_3_to_8",
    "first_counter_overflow": _cirfix_benchmark_dir / "first_counter_overflow",
    "flip_flop": _cirfix_benchmark_dir / "flip_flop",
    "fsm_full": _cirfix_benchmark_dir / "fsm_full",
    "lshift_reg": _cirfix_benchmark_dir / "lshift_reg",
    "mux_4_1": _cirfix_benchmark_dir / "mux_4_1",
    "sdram_controller": _cirfix_benchmark_dir / "sdram_controller",
    "i2c_master": _opencores_dir / "i2c" / "master.toml",
    "i2c_slave": _opencores_dir / "i2c" / "slave.toml",
    "pairing": _opencores_dir / "pairing",
    "reed_solomon_decoder": _opencores_dir / "reed_solomon_decoder",
    "sha3_f_permutation": _sha3_dir / "f_permutation.toml",
    "sha3_keccak": _sha3_dir / "keccak.toml",
    "sha3_padder": _sha3_dir / "padder.toml",
}

cirfix_seeds = {
    "decoder_3_to_8": {
        "wadden_buggy1": "repair_2021-07-16-11:18:47",  # should take around 13984.3s
        "wadden_buggy2": None,  # was not repaired
    },
    "first_counter_overflow": {
        "wadden_buggy1":  "repair_2020-09-23-11:24:14",  # should take around 19.8s
        "wadden_buggy2":  "repair_2020-10-23-11:15:58",  # should take around 27781.3s
        "kgoliya_buggy1": "repair_2020-09-23-11:26:48",  # should take around 32239.2s
    },
    "flip_flop": {
        "wadden_buggy1": "repair_2020-09-22-16:19:54",   # should take around 7.8s
        "wadden_buggy2": "repair_2020-09-22-16:20:32",   # should take around 923.5s
    },
    "fsm_full": {
        "wadden_buggy1":   None,                          # was not repaired
        "wadden_buggy2":   "repair_2020-09-22-16:43:18",  # should take around 1536.4s
        "ssscrazy_buggy1": "repair_2020-09-22-17:11:14",  # should take around 37.03s
        "ssscrazy_buggy2": "repair_2020-09-22-17:13:29",  # should take around 4282.2s
    },
    "lshift_reg": {
        "wadden_buggy1":  "repair_2020-09-22-16:13:12",  # should take around 14.6s
        "wadden_buggy2":  "repair_2020-09-22-16:16:14",  # should take around 33.74s
        "kgoliya_buggy1": "repair_2020-09-22-16:01:26",  # should take around 7.8s
    },
    "mux_4_1": {
        "wadden_buggy1":  "repair_2021-07-20-23:50:05",  # should take around 15387.87s
        "wadden_buggy2":  "repair_2021-07-21-07:22:28",  # should take around 10315.4s
        "kgoliya_buggy1": None,                          # was not repaired
    },
    "i2c_slave": {
        "wadden_buggy1": "repair_2020-09-24-09:43:26",   # should take around 183s
        "wadden_buggy2": "repair_2020-09-24-09:39:10",   # should take around 57.9s
    },
    "i2c_master": {
        "kgoliya_buggy1": "repair_2020-10-14-11:25:36",  # should take around 1560.61s
    },
    "sha3_keccak": {
        "wadden_buggy1": "repair_2020-09-24-09:48:40",   # should take around 50.4s
        "wadden_buggy2": None,                           # was not repaired
        "round_ssscrazy_buggy1": None,                   # was not repaired
    },
    "sha3_padder": {
        "ssscrazy_buggy1": "repair_2020-09-24-15:16:49",   # should take around 50s
    },
    "pairing": {
        "wadden_buggy1":  None,   # was not repaired
        "wadden_buggy2":  None,   # was not repaired
        "kgoliya_buggy1": None,   # was not repaired
    },
    "reed_solomon_decoder": {
        "BM_lamda_ssscrazy_buggy1": None,  # was not repaired
        "out_stage_ssscrazy_buggy1": "repair_2020-09-29-23:31:29",  # should take around 28547.81s
    },
    "sdram_controller": {
        "wadden_buggy1":  "repair_2020-09-30-23:15:14",  # should take around 16607.6s
        "wadden_buggy2":  None,   # was not repaired
        "kgoliya_buggy2": None,   # was not repaired
    },
}


@dataclass
class Bug:
    name: str
    original: Path
    buggy: Path

@dataclass
class Testbench:
    name: str


@dataclass
class VerilogOracleTestbench(Testbench):
    """ The style of testbench used by CirFix """
    sources: list[Path]
    output: str
    oracle: Path
    timeout: float = None


@dataclass
class TraceTestbench(Testbench):
    """ For RTL-Repair we use I/O traces that were pre-recorded from the Verilog testbench """
    table: Path

@dataclass
class Design:
    top: str
    directory: Path
    sources: list[Path]

@dataclass
class Project:
    name: str
    design: Design
    bugs: list[Bug]
    testbenches: list[Testbench]


@dataclass
class Benchmark:
    project_name: str
    design: Design
    bug: Bug
    testbench: Testbench
    @property
    def name(self):
        return f"{self.project_name}_{self.bug.name}_{self.testbench.name}"


def parse_path(path: str, base: Path = Path("."), must_exist: bool = False) -> Path:
    if os.path.isabs(path):
        path = Path(path)
    else:
        path = base / path
    if must_exist:
        assert path.exists(), f"{path} does not exist!"
    return path


def _load_bug(base_dir: Path, dd: dict) -> Bug:
    original = None
    if 'original' in dd and len(dd['original']) > 0:
        original = parse_path(dd['original'], base_dir, True)
    return Bug(
        name=dd['name'],
        original=original,
        buggy=parse_path(dd['buggy'], base_dir, True),
    )


def _load_testbench(base_dir: Path, dd: dict) -> Testbench:
    if 'oracle' in dd:
        tt = VerilogOracleTestbench(
            name=dd['name'],
            sources=[parse_path(pp, base_dir, True) for pp in dd['sources']],
            output=dd['output'],
            oracle=parse_path(dd['oracle'], base_dir, True),
        )
        if "timeout" in dd:
            tt.timeout = float(dd["timeout"])
    else:
        tt = TraceTestbench(name=dd['name'], table=parse_path(dd['table'], base_dir, True))
    return tt


def _load_list(project_dir: Path, dd: dict, name: str, load_foo) -> list:
    if name not in dd:
        return []
    return [load_foo(project_dir, ee) for ee in dd[name]]


def load_project(filename: Path) -> Project:
    # if a directory is provided, we try to open to project.toml
    if filename.is_dir(): # <-- this is the good case: the project specifies what it wants to be called
        name = filename.name
        filename = filename / "project.toml"
    else: # <-- ugly, hacky heuristics to get a "good" project name base on the filepath
        name = filename.stem
        # if we are given a path to a file name `project.toml` we assume that the directory is the project name
        if name == "project":
            name = filename.parent.name
    with open(filename, 'rb') as ff:
        dd = tomli.load(ff)
    assert 'project' in dd, f"{filename}: no project entry"
    project = dd['project']
    if 'name' in project:
        name = project['name']
    top = project['toplevel'] if 'toplevel' in project else None
    base_dir = filename.parent
    project_dir = parse_path(project['directory'], base_dir, must_exist=True)
    bugs = _load_list(base_dir, dd, "bugs", _load_bug)
    testbenches = _load_list(base_dir, dd, "testbenches", _load_testbench)
    assert len(testbenches) > 0, "No testbench in project.toml!"
    design = Design(
        top=top,
        directory=project_dir,
        sources=[parse_path(pp, base_dir, True) for pp in project['sources']],
    )
    return Project(name, design, bugs, testbenches)


def pick_testbench(project: Project, testbench: str = None) -> Testbench:
    assert len(project.testbenches) > 0
    if testbench is None:
        return project.testbenches[0]
    else:
        return next(t for t in project.testbenches if t.name == testbench)

def pick_oracle_testbench(project: Project, testbench: str = None) -> VerilogOracleTestbench:
    tbs = [tb for tb in project.testbenches if isinstance(tb, VerilogOracleTestbench)]
    assert len(tbs) > 0, f"No VerilogOracleTestbench available for project {project.name}."
    if testbench is None:
        return tbs[0]
    else:
        return next(t for t in tbs if t.name == testbench)
def pick_trace_testbench(project: Project, testbench: str = None) -> TraceTestbench:
    tbs = [tb for tb in project.testbenches if isinstance(tb, TraceTestbench)]
    assert len(tbs) > 0, f"No TraceTestbench available for project {project.name}."
    if testbench is None:
        return tbs[0]
    else:
        return next(t for t in tbs if t.name == testbench)

def get_benchmarks(project: Project, testbench: str = None) -> list:
    tb = pick_testbench(project, testbench)
    return [Benchmark(project.name, project.design, bb, tb) for bb in project.bugs]

def get_benchmark(project: Project, bug_name: str, testbench: str = None, use_trace_testbench: bool = False) -> Benchmark:
    if use_trace_testbench:
        tb = pick_trace_testbench(project, testbench)
    else:
        tb = pick_testbench(project, testbench)

    if bug_name is None:    # no bug --> create a benchmark from the original circuit
        original = project.design.sources[0]
        bb = Bug(name="original", original=original, buggy=original)
        return Benchmark(project.name, project.design, bb, tb)

    for bb in project.bugs:
        if bb.name == bug_name:
            return Benchmark(project.name, project.design, bb, tb)
    raise KeyError(f"Failed to find bug `{bug_name}`: {[bb.name for bb in project.bugs]}")

def get_other_sources(benchmark: Benchmark) -> list:
    """ returns a list of sources which are not the buggy source """
    return [s for s in benchmark.design.sources if s != benchmark.bug.original]

def get_benchmark_design(benchmark: Benchmark) -> Design:
    """ replaces the original file with the buggy one """
    orig = benchmark.design
    sources = get_other_sources(benchmark) + [benchmark.bug.buggy]
    return Design(top=orig.top, directory=orig.directory, sources=sources)

def get_seed(benchmark: Benchmark) -> Optional[str]:
    try:
        return cirfix_seeds[benchmark.project_name][benchmark.bug.name]
    except KeyError:
        return None


def is_cirfix_paper_benchmark(benchmark: Benchmark) -> bool:
    return (benchmark.project_name in cirfix_seeds and
            benchmark.bug.name in cirfix_seeds[benchmark.project_name])


def assert_file_exists(name: str, filename: Path):
    assert filename.exists(), f"{name}: {filename} not found!"
    assert filename.is_file(), f"{name}: {filename} is not a file!"


def assert_dir_exists(name: str, filename: Path):
    assert filename.exists(), f"{name}: {filename} not found!"
    assert filename.is_dir(), f"{name}: {filename} is not a directory!"


def validate_project(project: Project):
    assert_dir_exists(project.name, project.design.directory)
    for source in project.design.sources:
        assert_file_exists(project.name, source)
    for bug in project.bugs:
        validate_bug(project, bug)
    for tb in project.testbenches:
        validate_testbench(project, tb)


def validate_bug(project: Project, bug: Bug):
    name = f"{project.name}.{bug.name}"
    assert_file_exists(name, bug.original)
    assert_file_exists(name, bug.buggy)
    assert bug.original in project.design.sources, f"{name}: {bug.original} is not a project source!"


def validate_testbench(project: Project, testbench: Testbench):
    if isinstance(testbench, VerilogOracleTestbench):
        validate_oracle_testbench(project, testbench)


def validate_oracle_testbench(project: Project, testbench: VerilogOracleTestbench):
    name = f"{project.name}.{testbench.name}"
    for source in testbench.sources:
        assert_file_exists(name, source)
        assert source not in project.design.sources, f"{name}: {source} is already a project source!"
    assert_file_exists(name, testbench.oracle)

def load_all_projects() -> dict:
    pps = {}
    for name, directory in projects.items():
        pps[name] = load_project(directory)
    return pps

def load_benchmark_by_name(project_name: str, bug_name: str, tb_name: str = None) -> Benchmark:
    project = load_project(projects[project_name])
    bench = get_benchmark(project, bug_name, tb_name)
    return bench
