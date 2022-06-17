#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
from rtlfix.visitor import AstVisitor
from pathlib import Path
from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import Source, IntConst
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

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
    modified = replace_literals(ast)
    # print(serialize(modified))


def parse_verilog(filename: Path) -> Source:
    ast, directives = parse([filename], preprocess_include=[], preprocess_define=[], outputdir=_parser_tmp_dir,
                            debug=False)
    return ast


def serialize(ast: Source) -> str:
    codegen = ASTCodeGenerator()
    source = codegen.visit(ast)
    return source


def replace_literals(ast: Source) -> Source:
    repl = LiteralReplacer()
    repl.visit(ast)
    return ast


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


_synth_var_prefix = "__synth_"
_synth_change_prefix = "__synth_change_"


class Namespace:
    def __init__(self):
        self._names = set()

    def new_name(self, name):
        if name not in self._names:
            pass
        return name


class LiteralReplacer(AstVisitor):
    def __init__(self):
        super().__init__()
        self.constants = []

    def visit_IntConst(self, node: IntConst):
        value, bits = parse_verilog_int_literal(node.value)

        print(node.value, value, bits)
        return node


if __name__ == '__main__':
    main()
