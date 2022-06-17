#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
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
    args = parser.parse_args()
    return Path(args.source)


def main():
    filename = parse_args()
    ast = parse_verilog(filename)
    replace_literals(ast)
    print(serialize(ast))


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
