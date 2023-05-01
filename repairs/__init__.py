# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

# database of repairs from different tools

from dataclasses import dataclass
from pathlib import Path

from benchmarks import Benchmark, get_other_sources, VerilogOracleTestbench, load_project, get_benchmark, \
    assert_file_exists, assert_dir_exists
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

def parse_csv_line(line: str) -> list:
    return [n.strip() for n in line.split(',')]

@dataclass
class SimResult:
    no_output: bool = False
    failed_at: int = -1
    fail_msg: str = ""
    @property
    def is_success(self): return self.failed_at == -1 and not self.no_output

def check_against_oracle(oracle_filename: Path, output_filename: Path):
    with open(oracle_filename) as oracle, open(output_filename) as output:
        oracle_header, output_header = parse_csv_line(oracle.readline()), parse_csv_line(output.readline())
        assert oracle_header == output_header, f"{oracle_header} != {output_header}"
        header = oracle_header[1:]

        # compare line by line
        for (ii, (expected, actual)) in enumerate(zip(oracle, output)):
            expected, actual = parse_csv_line(expected), parse_csv_line(actual)
            # remove first line (time)
            expected, actual = expected[1:], actual[1:]
            correct = expected == actual
            if not correct:
                msg = []
                for ee, aa, nn in zip(expected, actual, header):
                    if ee != aa:
                        msg.append(f"{nn}@{ii}: {aa} != {ee} (expected)")
                return SimResult(failed_at=ii, fail_msg='\n'.join(msg))

        # are we missing some output?
        remaining_oracle_lines = oracle.readlines()
        if len(remaining_oracle_lines) > 0:
            # we expected more output => fail!
            msg = f"Output stopped at {ii}. Expected {len(remaining_oracle_lines)} more lines."
            return SimResult(failed_at=ii, fail_msg=msg)

    return SimResult()



def check_gatelevel_sim(working_dir: Path, benchmark: Benchmark, repaired: Path):
    other_sources = get_other_sources(benchmark)
    # synthesize
    gate_level = working_dir / f"{repaired.stem}.gatelevel.v"
    to_gatelevel_netlist(working_dir, gate_level, [repaired] + other_sources, top=benchmark.project.design.top)
    # check
    return check_sim(working_dir, benchmark, [gate_level] + other_sources)

def check_sim(working_dir: Path, benchmark: Benchmark, design_sources: list):
    # run testbench
    assert isinstance(benchmark.testbench, VerilogOracleTestbench)
    tb_sources = design_sources + benchmark.testbench.sources
    conf = RunConf(include_dir=benchmark.project.design.directory, verbose=False, show_stdout=False)
    run(working_dir, 'iverilog', tb_sources, conf)

    # check the output
    output = working_dir / benchmark.testbench.output
    if not output.exists():
        # no output was produced --> fail
        msg = "No output was produced."
        return SimResult(no_output=True, fail_msg=msg)
    else:
        return check_against_oracle(benchmark.testbench.oracle, output)



def check_repair(working_dir: Path, project_file: Path, bug_name: str, repaired: Path):
    assert_file_exists("repaired Verilog", repaired)
    assert_dir_exists("working directory", working_dir)
    project = load_project(project_file)
    benchmark = get_benchmark(project, bug_name)

    # first we just simulate and check the oracle
    other_sources = get_other_sources(benchmark)
    sim_res = check_sim(working_dir, benchmark, [repaired] + other_sources)
    if not sim_res.is_success:
        print(f"RTL-sim: {sim_res}")

    # now we do the gate-level sim, do we get the same result?
    gate_res = check_gatelevel_sim(working_dir, benchmark, repaired)
    print(f"Gate-level: {gate_res}")



def _simple_test():
    # cirfix solution
    root_dir = Path(__file__).parent.parent.resolve()

    repaired = root_dir / "notes" / "repairs" / "mux_4_1_wadden_buggy1.cirfix.v"
    project = "mux_4_1"
    bug = "kgoliya_buggy1"

    # working dir
    working_dir = root_dir / "tmp"
    if not working_dir.exists():
        working_dir.mkdir()

    # benchmark description
    from benchmarks import projects
    proj = projects[project]
    check_repair(working_dir, proj, bug, repaired)

if __name__ == '__main__':
    _simple_test()

