# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast


def add_inversions(ast: vast.Source):
    namespace = Namespace(ast)
    Inverter().apply(namespace, ast)


class Inverter(RepairTemplate):
    def __init__(self):
        super().__init__(name="invert")

    def visit_IntConst(self, node: vast.IntConst):
        value, bits = parse_verilog_int_literal(node.value)
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice

    def visit_Decl(self, node: vast.Decl):
        # ignore any declarations as not to instrument the integers of the width declaration
        return node
