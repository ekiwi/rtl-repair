# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast


def replace_literals(ast: vast.Source):
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

    def visit_IntConst(self, node: vast.IntConst):
        value, bits = parse_verilog_int_literal(node.value)
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice

