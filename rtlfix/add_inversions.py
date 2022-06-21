# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.types import infer_widths
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast


def add_inversions(ast: vast.Source):
    namespace = Namespace(ast)
    widths = infer_widths(ast)
    Inverter(widths).apply(namespace, ast)


_skip_nodes = {vast.Lvalue, vast.Decl, vast.SensList, vast.Portlist}


class Inverter(RepairTemplate):
    def __init__(self, widths: dict):
        super().__init__(name="invert")
        self.widths = widths

    def generic_visit(self, node):
        # skip nodes that contain declarations or senselists
        if type(node) in _skip_nodes:
            return node
        # ignore constants as they are already covered by the literal replacer template
        if isinstance(node, vast.Constant):
            return node
        # visit children
        node = super().generic_visit(node)
        # if it is a 1-bit node, add the possibility to invert
        if node in self.widths and self.widths[node] == 1:
            # add possibility to invert boolean expression
            node = self.make_change(vast.Ulnot(node), node)
        return node
