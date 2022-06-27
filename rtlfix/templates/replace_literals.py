# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.types import InferWidths
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast


def replace_literals(ast: vast.Source):
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = LiteralReplacer(infer.widths)
    repl.apply(namespace, ast)


class LiteralReplacer(RepairTemplate):
    def __init__(self, widths):
        super().__init__(name="literal")
        self.widths = widths

    def visit_IntConst(self, node: vast.IntConst):
        bits = self.widths[node]
        new_const = vast.Identifier(self.make_synth_var(bits))
        choice = self.make_change(new_const, node)
        return choice
