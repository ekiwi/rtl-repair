#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# runs the testbench with iverilog, producing a VCD

import sys
from dataclasses import dataclass
from pathlib import Path
from pyverilog.vparser.parser import parse
import pyverilog.vparser.ast as vast


# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
from benchmarks import TraceTestbench, Design, load_project, pick_trace_testbench, Benchmark, Bug, \
    VerilogOracleTestbench
from scripts.check_repairs import check_sim, parse_csv_line
from scripts import check_repairs
from rtlrepair.utils import parse_width

@dataclass
class ToplevelInfo:
    name: str
    inputs: list
    outputs: list


def analyze_toplevel(design: Design):
    ast, _ = parse(design.sources, preprocess_include=[design.directory])
    assert isinstance(ast, vast.Source)
    ports = []
    # find topmodule
    for definition in ast.description.definitions:
        if not isinstance(definition, vast.ModuleDef):
            continue
        if definition.name != design.top:
            continue
        for port in definition.portlist.ports:
            assert isinstance(port, vast.Ioport)
            if isinstance(port.first, vast.Input):
                ports.append(('in', port.first.name, parse_width(port.first.width)))
            elif isinstance(port.first, vast.Output):
                ports.append(('out', port.first.name, parse_width(port.first.width)))
            else:
                raise NotImplementedError(f"TODO: deal with port of type: {type(port.first)}")
    return ports


def find_clock(ports: list) -> str:
    for (direction, name, width) in ports:
        if direction == 'in' and width == 1 and name.lower() in {'clk', 'clock'}:
            return name
    raise RuntimeError(f"Could not find clock in {ports}")


def trace_tb_to_verilog(filename: Path, tb: TraceTestbench, top: str, ports: list) -> VerilogOracleTestbench:
    inst_name = top + "_dut"
    out_file_name = "trace.txt"
    with open(filename, 'w') as ff:
        print("module tb;", file=ff)

        # create I/O variables
        for (direction, name, width) in ports:
            kind = "reg" if direction == 'in' else "wire"
            ww = "" if width == 1 else f" [{width - 1}:0]"
            print(f"{kind}{ww} {name};", file=ff)

        # create instance
        print(f"{top} {inst_name}(", file=ff)
        for (_, name, _) in ports:
            comma = "" if name == ports[-1][1] else ","
            print(f"  .{name}({name}){comma}", file=ff)
        print(f");", file=ff)

        # init!
        print(f"initial begin", file=ff)

        # set inputs to zero
        for (direction, name, width) in ports:
            if direction == 'in':
                print(f"  {name} = 0;", file=ff)

        # dump to VCD
        print(f"  // VCD", file=ff)
        print(f"  $dumpfile(\"dump.vcd\");", file=ff)
        print(f"  $dumpvars(0, {inst_name});", file=ff)

        print(f"end // initial", file=ff)

        # generate clock
        clock = find_clock(ports)
        print(f"always #1 {clock} = !{clock};", file=ff)

        # dump to file
        print("integer f;", file=ff)
        print("initial begin", file=ff)
        print(f"  f = $fopen(\"{out_file_name}\");", file=ff)
        header = ",".join(name for _, name, _ in ports if name != clock)
        print(f"  $fwrite(f, \"time,{header}\\n\");", file=ff)
        print("  forever begin", file=ff)
        print(f"    @(posedge {clock});", file=ff)
        format_str = ",".join(["%g"] + ["%d"] * (len(ports) - 1))
        print(f"    $fwrite(f, \"{format_str}\\n\", $time, {header});", file=ff)
        print("  end // forever", file=ff)
        print("end // initial", file=ff)

        # apply inputs
        print("initial begin", file=ff)
        with open(tb.table) as oracle:
            header = parse_csv_line(oracle.readline())
            name_to_index = {k: v for v, k in enumerate(header)}
            for ii, step in enumerate(oracle):
                values = parse_csv_line(step)
                print(f"  // step {ii}", file=ff)
                for (direction, name, width) in ports:
                    if name == clock:
                        continue # skip clock
                    value = values[name_to_index[name]]
                    if direction == 'in':
                        print(f"  {name} <= 'd{value};", file=ff)
                    else:
                        if value.lower() != 'x':
                            print(f"  // assert {name} == 'd{value};", file=ff)
                print(f"  @(posedge {clock});", file=ff)
        print(f"  // wait one more step to ensure that the last step is committed to the output file", file=ff)
        print(f"  @(posedge {clock});", file=ff)
        print("  $fclose(f);", file=ff)
        print("  $finish;", file=ff)
        print("end // initial", file=ff)

        # end
        print("endmodule // tb", file=ff)

        return VerilogOracleTestbench("verilog_tb", [filename], out_file_name, tb.table)


def main() -> int:
    # load project data
    proj_dir = _script_dir / "project"
    proj = load_project(proj_dir / "project.toml")

    # generate a verilog testbench
    ports = analyze_toplevel(proj.design)
    trace_tb = pick_trace_testbench(proj)
    verilog_tb_file = _script_dir / "project" / "tb.v"
    verilog_tb = trace_tb_to_verilog(verilog_tb_file, trace_tb, proj.design.top, ports)

    # check the repair, i.e., the file the user is editing
    fake_bug = Bug("original", proj.design.sources[0], proj.design.sources[0])
    bench = Benchmark(proj.name, proj.design, fake_bug, verilog_tb)
    run_conf = check_repairs.Config(proj_dir, proj_dir, "iverilog", False)
    sim_res = check_sim(run_conf, None, bench, proj.design.sources)
    print(f"{sim_res.emoji} {sim_res.fail_msg}")
    return 0 if sim_res.is_success else 1


if __name__ == '__main__':
    sys.exit(main())
