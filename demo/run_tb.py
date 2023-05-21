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

from rtlfix.utils import parse_width

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
from benchmarks import TraceTestbench, Design, load_project, pick_trace_testbench


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

def trace_tb_to_verilog(filename: Path, tb: TraceTestbench, top:str, ports: list):
    inst_name = top + "_dut"
    out_file_name = "trace.txt"
    with open(filename, 'w') as ff:
        print("module tb;", file=ff)

        # create I/O variables
        for (direction, name, width) in ports:
            kind = "reg" if direction == 'in' else "wire"
            ww = "" if width == 1 else f" [{width-1}:0]"
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
        header = ",".join(name for _, name, _ in ports)
        print(f"  $fwrite(f, \"time,{header}\\n\");", file=ff)
        print("  forever begin", file=ff)
        print(f"    @(posedge {clock});", file=ff)
        format_str = ",".join(["%g"] + ["%d"] * len(ports))
        print(f"    $fwrite(f, \"{format_str}\\n\", $time, {header});", file=ff)
        print("  end // forever", file=ff)
        print("end // initial", file=ff)

        # apply inputs
        print("initial begin", file=ff)
        
        print("end // initial", file=ff)


        # end
        print("endmodule // tb", file=ff)




def main():
    proj = load_project(_script_dir / "project" / "project.toml")
    ports = analyze_toplevel(proj.design)
    trace_tb = pick_trace_testbench(proj)
    trace_tb_to_verilog(_script_dir / "project" / "tb.v", trace_tb, proj.design.top, ports)



if __name__ == '__main__':
    main()
