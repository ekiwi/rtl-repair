# Copyright 2023-2024 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


from rtlrepair.repair import RepairTemplate
from rtlrepair.types import InferWidths
from rtlrepair.utils import Namespace, ensure_block
import pyverilog.vparser.ast as vast


def add_guard(ast: vast.Source):
    """ Adds a condition to a boolean expression. """
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = AddGuard(infer.widths)
    repl.apply(namespace, ast)
    return repl.blockified


class AddGuard(RepairTemplate):
    def __init__(self, widths):
        super().__init__(name="add_guard")
        self.widths = widths
        self.use_blocking = False
        self.assigned_vars = []
        # we use this list to track which new blocks we introduced in order to minimize the diff between
        # buggy and repaired version
        self.blockified = []
        # remember all 1-bit registers
        self.bool_registers = set()

