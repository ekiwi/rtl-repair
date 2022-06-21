# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast


def replace_literals(ast: vast.Source, widths: dict):
    namespace = Namespace(ast)
    repl = LiteralReplacer()
    repl.apply(namespace, ast, widths)


_bases = {'b': 2, 'o': 8, 'h': 16, 'd': 10}


def _find_min_width(value: int) -> int:
    assert value >= 0
    return len(f"{value:b}")


def parse_verilog_int_literal(value: str) -> (int, int):
    if "'" in value:
        parts = value.split("'")
        width = int(parts[0])
        prefix = parts[1][0]
        if prefix in _bases:
            value = int(parts[1][1:], _bases[prefix])
        else:
            value = int(parts[1])
        return value, width
    else:
        value = int(value)
        # TODO: should this be a 32 (the integer default size in verilog) or
        #       the minimum width needed to hold the literal?
        return value, _find_min_width(value)


class LiteralReplacer(RepairTemplate):
    def __init__(self):
        super().__init__(name="literal")

    def visit_IntConst(self, node: vast.IntConst):
        value, bits = parse_verilog_int_literal(node.value)
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice
