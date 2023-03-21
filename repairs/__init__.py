# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

# database of repairs from different tools

from dataclasses import dataclass
from pathlib import Path

from benchmarks import Benchmark, get_other_sources, VerilogOracleTestbench
from benchmarks.yosys import to_gatelevel_netlist
from benchmarks.run import run, RunConf


@dataclass
class Repair:
    benchmark: str
    bug: str


cirfix_repairs = {

}


repairs = {
    "cirfix": cirfix_repairs
}

def check_gatelevel_sim(working_dir: Path, benchmark: Benchmark, repaired: Path):
    assert working_dir.exists(), f"Does not exist: {working_dir.resolve()}"
    other_sources = get_other_sources(benchmark)
    # synthesize
    gate_level = working_dir / f"{repaired.stem}.gatelevel.v"
    to_gatelevel_netlist(working_dir, gate_level, [repaired] + other_sources, top=benchmark.project.top)
    # run testbench
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    tb_sources = [gate_level] + other_sources + benchmark.testbench.sources
    run(working_dir, 'iverilog', tb_sources, RunConf(verbose=True, show_stdout=True))
    # TODO: actually check the output of the testbench!



def _simple_test():
    # cirfix solution
    root_dir = Path(__file__).parent.parent.resolve()
    repaired = root_dir / "notes" / "repairs" / "mux_4_1_wadden_buggy1.cirfix.v"
    assert repaired.exists()

    # benchmark description
    from benchmarks import load_benchmark_by_name
    bench = load_benchmark_by_name("mux_4_1", "kgoliya_buggy1")

    # working dir
    working_dir = root_dir / "tmp"
    if not working_dir.exists():
        working_dir.mkdir()

    # check
    check_gatelevel_sim(working_dir, bench, repaired)

if __name__ == '__main__':
    _simple_test()

