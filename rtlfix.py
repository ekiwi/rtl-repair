#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import os
import subprocess
from pathlib import Path
from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Source
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

from rtlfix.literalrepl import replace_literals

_script_dir = Path(__file__).parent.resolve()
_parser_tmp_dir = _script_dir / ".pyverilog"


def parse_args():
    parser = argparse.ArgumentParser(description='Repair Verilog file')
    parser.add_argument('--source', dest='source', help='Verilog source file', required=True)
    parser.add_argument('--working-dir', dest='working_dir', help='Working directory, files might be overwritten!',
                        required=True)
    args = parser.parse_args()
    return Path(args.source), Path(args.working_dir)


def create_working_dir(working_dir: Path):
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)


def to_btor(filename: Path):
    cwd = filename.parent
    assert cwd.exists(), f"directory {cwd} does not exist"
    r = subprocess.run(["yosys", "-version"], check=False, stdout=subprocess.PIPE)
    assert r.returncode == 0, f"failed to find yosys {r}"
    btor_name = filename.stem + ".btor"
    yosys_cmd = f"read_verilog {filename.name} ; proc ; write_btor -x {btor_name}"
    subprocess.run(["yosys", "-p", yosys_cmd], check=True, cwd=cwd, stdout=subprocess.PIPE)
    assert (cwd / btor_name).exists()
    return cwd / btor_name



def main():
    filename, working_dir = parse_args()
    create_working_dir(working_dir)
    ast = parse_verilog(filename)
    replace_literals(ast)
    synth_filename = working_dir / filename.name
    with open(synth_filename, "w") as f:
        f.write(serialize(ast))
    btor_filename = to_btor(synth_filename)
    print(btor_filename)


def parse_verilog(filename: Path) -> Source:
    ast, directives = parse([filename],
                            preprocess_include=[],
                            preprocess_define=[],
                            outputdir=_parser_tmp_dir,
                            debug=False)
    return ast


def serialize(ast: Source) -> str:
    codegen = ASTCodeGenerator()
    source = codegen.visit(ast)
    return source


if __name__ == '__main__':
    main()
