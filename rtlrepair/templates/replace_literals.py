# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlrepair.repair import RepairTemplate
from rtlrepair.types import InferWidths
from rtlrepair.utils import Namespace
import pyverilog.vparser.ast as vast


def replace_literals(ast: vast.Source):
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = LiteralReplacer(infer.widths, infer.vars, infer.params)
    repl.apply(namespace, ast)


class LiteralReplacer(RepairTemplate):
    def __init__(self, widths, vars, params):
        super().__init__(name="literal")
        self.widths = widths
        self.vars = vars
        self.params = params

    def visit_Identifier(self, node: vast.Identifier):
        if node.name in self.params:
            # we treat parameters like constants
            bits = self.vars[node.name]
            new_const = vast.Identifier(self.make_synth_var(bits))
            choice = self.make_change(new_const, node)
            return choice
        else:
            return node

    def visit_IntConst(self, node: vast.IntConst):
        bits = self.widths[node]
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice
