# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.types import InferWidths
from rtlfix.utils import Namespace, ensure_block
import pyverilog.vparser.ast as vast

from rtlfix.visitor import AstVisitor


def assign_const(ast: vast.Source):
    """ assign an arbitrary constant to a variable at the beginning of a block
        - we ensure that only variables are assigned that are normally assigned in that particular process
        - we pick blocking vs. non-blocking based on what is normally used in the particular process
    """
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = ConstAssigner(infer.vars)
    repl.apply(namespace, ast)


class ConstAssigner(RepairTemplate):
    def __init__(self, vars):
        super().__init__(name="assign")
        self.vars = vars
        self.use_blocking = False
        self.assigned_vars = []

    def visit_Always(self, node: vast.Always):
        analysis = ProcessAnalyzer()
        analysis.run(node)
        if analysis.non_blocking_count > 0 and analysis.blocking_count > 0:
            print("WARN: single always process seems to mix blocking and non-blocking assignment. Skipping.")
            return node
        self.assigned_vars = list(analysis.assigned_vars)
        self.use_blocking = analysis.blocking_count > 0
        # add assignments to beginning of process
        node.statement = self.prepend_assignments(self.visit(node.statement))
        self.assigned_vars = []
        return node

    def visit_IfStatement(self, node: vast.IfStatement):
        if len(self.assigned_vars) > 0:
            node.true_statement = self.prepend_assignments(self.visit(node.true_statement))
            node.false_statement = self.prepend_assignments(self.visit(node.false_statement))
        return node

    def visit_Case(self, node: vast.Case):
        if len(self.assigned_vars) > 0:
            node.statement = self.prepend_assignments(self.visit(node.statement))
        return node

    def prepend_assignments(self, stmt):
        if stmt is None:
            return None
        block = ensure_block(stmt)
        # add assignments to beginning of process
        block.statements = tuple(self.make_assignments() + list(block.statements))
        return block

    def make_assignments(self):
        res = []
        for name in self.assigned_vars:
            width = self.vars[name]
            const = vast.Identifier(self.make_synth_var(width))
            if self.use_blocking:
                assign = vast.BlockingSubstitution(vast.Lvalue(vast.Identifier(name)), vast.Rvalue(const))
            else:
                assign = vast.NonblockingSubstitution(vast.Lvalue(vast.Identifier(name)), vast.Rvalue(const))
            res.append(self.make_change_stmt(assign))
        return res


class ProcessAnalyzer(AstVisitor):
    def __init__(self):
        super().__init__()
        self.assigned_vars = set()
        self.blocking_count = 0
        self.non_blocking_count = 0

    def run(self, proc: vast.Always):
        self.visit(proc)

    def visit_BlockingSubstitution(self, node: vast.BlockingSubstitution):
        self.generic_visit(node)
        self.blocking_count += 1
        self.assigned_vars.add(str(node.left.var.name))

    def visit_NonblockingSubstitution(self, node: vast.NonblockingSubstitution):
        self.generic_visit(node)
        self.non_blocking_count += 1
        self.assigned_vars.add(str(node.left.var.name))
