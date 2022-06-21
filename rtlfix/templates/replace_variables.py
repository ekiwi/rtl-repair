# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
from collections import defaultdict

from rtlfix.repair import RepairTemplate
from rtlfix.types import InferWidths
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast
from pyverilog.utils.identifiervisitor import getIdentifiers


def replace_variables(ast: vast.Source):
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = VariableReplacer(infer.vars)
    repl.apply(namespace, ast)


class VariableReplacer(RepairTemplate):
    def __init__(self, vars: dict):
        super().__init__(name="variable")
        self.vars = vars
        self.ignore = set()  # variables that should be ignored
        width_to_var = defaultdict(list)
        for name, width in self.vars.items():
            width_to_var[width] += [name]
        self.width_to_var = dict(width_to_var)

    def _visit_assign(self, left, right):
        """ we do not want to use any identifiers from the LHS on the RHS because it often leads to combinatorial loops
        """
        self.ignore = set(getIdentifiers(left))
        right = self.visit(right)
        self.ignore = set()
        return right

    def visit_Assign(self, node: vast.Assign):
        node.right = self._visit_assign(node.left, node.right)
        return node

    def visit_NonblockingSubstitution(self, node: vast.NonblockingSubstitution):
        node.right = self._visit_assign(node.left, node.right)
        return node

    def visit_BlockingSubstitution(self, node: vast.BlockingSubstitution):
        node.right = self._visit_assign(node.left, node.right)
        return node

    def visit_Identifier(self, node: vast.Identifier):
        width = self.vars[node.name]
        others = [name for name in self.width_to_var[width] if name != node.name and name not in self.ignore]
        if len(others) == 0:
            return node
        # put choices into ITE
        new_id = vast.Identifier(others[0])
        for name in others[1:]:
            var = vast.Identifier(self.make_synth_var(1))
            new_id = vast.Cond(var, vast.Identifier(name), new_id)
        return self.make_change(new_id, node)
