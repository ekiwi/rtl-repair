# Copyright 2022 The Regents of the University of California
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
class VerilogOracleTestbench:
    """ The style of testbench used by CirFix """
    name: str
    sources: list[Path]
    output: str
    oracle: Path
    timeout: float = None


@dataclass
class TraceTestbench:
    """ For RTL-Repair we use I/O traces that were pre-recorded from the Verilog testbench """


@dataclass
class Project:
    name: str
    directory: Path
    sources: list[Path]
    bugs: list[Bug]
    testbenches: list[Testbench]


@dataclass
class Benchmark:
    project: Project
    bug: Bug
    testbench: Testbench


def parse_path(path: str, base: Path = Path("."), must_exist: bool = False) -> Path:
    if os.path.isabs(path):
        path = Path(path)
    else:
        path = base / path
    if must_exist:
        assert path.exists(), f"{path} does not exist!"
    return path


def _load_bug(base_dir: Path, dd: dict) -> Bug:
    return Bug(
        name=dd['name'],
        original=parse_path(dd['original'], base_dir, True),
        buggy=parse_path(dd['buggy'], base_dir, True),
    )


def _load_testbench(base_dir: Path, dd: dict) -> Testbench:
    tt = Testbench(
        name=dd['name'],
        sources=[parse_path(pp, base_dir, True) for pp in dd['sources']],
        output=dd['output'],
        oracle=parse_path(dd['oracle'], base_dir, True),
    )
    if "timeout" in dd:
        tt.timeout = float(dd["timeout"])
    return tt


def _load_list(project_dir: Path, dd: dict, name: str, load_foo) -> list:
    if name not in dd:
        return []
    return [load_foo(project_dir, ee) for ee in dd[name]]


def load_project(filename: Path) -> Project:
    # if a directory is provided, we try to open to project.toml
    if filename.is_dir():
        name = filename.name
        filename = filename / "project.toml"
    else:
        name = filename.stem
    with open(filename, 'rb') as ff:
        dd = tomli.load(ff)
    assert 'project' in dd, f"{filename}: no project entry"
    project = dd['project']
    if 'name' in project:
        name = project['name']
    base_dir = filename.parent
    project_dir = parse_path(project['directory'], base_dir, must_exist=True)
    bugs = _load_list(base_dir, dd, "bugs", _load_bug)
    testbenches = _load_list(base_dir, dd, "testbenches", _load_testbench)
    assert len(testbenches) > 0, "No testbench in project.toml!"
    return Project(
        name=name,
        directory=project_dir,
        sources=[parse_path(pp, base_dir, True) for pp in project['sources']],
        bugs=bugs,
        testbenches=testbenches
    )


def pick_testbench(project: Project, testbench: str = None) -> Testbench:
    assert len(project.testbenches) > 0
    if testbench is None:
        return project.testbenches[0]
    else:
        return next(t for t in project.testbenches if t.name == testbench)


def get_benchmarks(project: Project, testbench: str = None) -> list:
    tb = pick_testbench(project, testbench)
    return [Benchmark(project, bb, tb) for bb in project.bugs]


def get_seed(benchmark: Benchmark) -> Optional[str]:
    try:
        return cirfix_seeds[benchmark.project.name][benchmark.bug.name]
    except KeyError:
        return None


def is_cirfix_paper_benchmark(benchmark: Benchmark) -> bool:
    return (benchmark.project.name in cirfix_seeds and
            benchmark.bug.name in cirfix_seeds[benchmark.project.name])


def _assert_file_exists(name: str, filename: Path):
    assert filename.exists(), f"{name}: {filename} not found!"
    assert filename.is_file(), f"{name}: {filename} is not a file!"


def _assert_dir_exists(name: str, filename: Path):
    assert filename.exists(), f"{name}: {filename} not found!"
    assert filename.is_dir(), f"{name}: {filename} is not a directory!"


def validate_project(project: Project):
    _assert_dir_exists(project.name, project.directory)
    for source in project.sources:
        _assert_file_exists(project.name, source)
    for bug in project.bugs:
        validate_bug(project, bug)
    for tb in project.testbenches:
        validate_testbench(project, tb)


def validate_bug(project: Project, bug: Bug):
    name = f"{project.name}.{bug.name}"
    _assert_file_exists(name, bug.original)
    _assert_file_exists(name, bug.buggy)
    assert bug.original in project.sources, f"{name}: {bug.original} is not a project source!"


def validate_testbench(project: Project, testbench: Testbench):
    name = f"{project.name}.{testbench.name}"
    for source in testbench.sources:
        _assert_file_exists(name, source)
        assert source not in project.sources, f"{name}: {source} is already a project source!"
    _assert_file_exists(name, testbench.oracle)


def load_all_projects() -> dict:
    pps = {}
    for name, directory in projects.items():
        pps[name] = load_project(directory)
    return pps