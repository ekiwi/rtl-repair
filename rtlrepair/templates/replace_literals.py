# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlrepair.repair import RepairTemplate
from rtlrepair.analysis import AnalysisResults, VarInfo
from rtlrepair.utils import Namespace
import pyverilog.vparser.ast as vast


def replace_literals(ast: vast.Source, analysis: AnalysisResults):
    namespace = Namespace(ast)
    repl = LiteralReplacer(analysis.vars, analysis.widths)
    repl.apply(namespace, ast)


class LiteralReplacer(RepairTemplate):
    def __init__(self, vars: dict[str, VarInfo], widths: dict[vast.Node, int]):
        super().__init__(name="literal")
        self.vars = vars
        self.widths = widths

    def visit_Identifier(self, node: vast.Identifier):
        var = self.vars[node.name]
        if var.is_const:
            # we treat parameters like constants
            new_const = vast.Identifier(self.make_synth_var(var.width))
            choice = self.make_change(new_const, node)
            return choice
        else:
            return node

    def visit_IntConst(self, node: vast.IntConst):
        bits = self.widths[node]
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice
