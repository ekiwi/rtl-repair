#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
from rtlfix import RepairTemplate, Namespace
from pathlib import Path
from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Source, IntConst
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
import pyverilog.vparser.ast as vast

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


def replace_literals(ast: Source):
    namespace = Namespace(ast)
    repl = LiteralReplacer()
    repl.apply(namespace, ast)


_bases = {'b': 2, 'o': 8, 'h': 16, 'd': 10}


def parse_verilog_int_literal(value: str) -> (int, int):
    assert "'" in value, f"unsupported integer constant format: {value}"
    parts = value.split("'")
    width = int(parts[0])
    prefix = parts[1][0]
    if prefix in _bases:
        value = int(parts[1][1:], _bases[prefix])
    else:
        value = int(parts[1])
    return value, width


class LiteralReplacer(RepairTemplate):
    def __init__(self):
        super().__init__(name="literal")

    def visit_IntConst(self, node: IntConst):
        value, bits = parse_verilog_int_literal(node.value)
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice


if __name__ == '__main__':
    main()
