# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlrepair.repair import RepairTemplate
from rtlrepair.analysis import AnalysisResults, VarInfo
from rtlrepair.utils import Namespace, ensure_block
import pyverilog.vparser.ast as vast

from rtlrepair.visitor import AstVisitor


def assign_const(ast: vast.Source, anslysis: AnalysisResults):
    """ assign an arbitrary constant to a variable at the beginning of a block
        - we ensure that only variables are assigned that are normally assigned in that particular process
        - we pick blocking vs. non-blocking based on what is normally used in the particular process
    """
    namespace = Namespace(ast)
    repl = ConstAssigner(anslysis.widths)
    repl.apply(namespace, ast)
    return repl.blockified


_ENABLE_NEW_CASE_STATEMENT: bool = False

class ConstAssigner(RepairTemplate):
    def __init__(self, widths):
        super().__init__(name="assign")
        self.widths = widths
        self.use_blocking = False
        self.assigned_vars = []
        # we use this list to track which new blocks we introduced in order to minimize the diff between
        # buggy and repaired version
        self.blockified = []

    def visit_Always(self, node: vast.Always):
        analysis = ProcessAnalyzer()
        analysis.run(node)
        if analysis.non_blocking_count > 0 and analysis.blocking_count > 0:
            print("WARN: single always process seems to mix blocking and non-blocking assignment. Skipping.")
            return node
        # note: we are ignoring pointer for now since these might contain loop vars that may not always be in scope..
        self.assigned_vars = [var for var in analysis.assigned_vars if isinstance(var, vast.Identifier)]
        self.use_blocking = analysis.blocking_count > 0
        # add assignments to beginning of process
        node.statement = self.add_assignments(self.visit(node.statement))
        self.assigned_vars = []
        return node

    def visit_IfStatement(self, node: vast.IfStatement):
        if len(self.assigned_vars) > 0:
            node.true_statement = self.add_assignments(self.visit(node.true_statement))
            node.false_statement = self.add_assignments(self.visit(node.false_statement))
        return node

    def visit_Case(self, node: vast.Case):
        if len(self.assigned_vars) > 0:
            node.statement = self.add_assignments(self.visit(node.statement))
        return node

    def visit_CaseStatement(self, node: vast.CaseStatement):
        node: vast.CaseStatement = self.generic_visit(node)
        if len(self.assigned_vars) == 0 or not _ENABLE_NEW_CASE_STATEMENT:
            return node
        # try to insert a new case before the default case
        children = []
        width = self.widths[node.comp]
        for child in node.caselist:
            if child.cond is None:
                # insert right before the default statement
                cond = (vast.Identifier(self.make_synth_var(width)),)
                body = vast.Block(tuple(self.make_assignments(node.lineno)))
                children.append(vast.Case(cond, body))
            children.append(child)
        node.caselist = tuple(children)
        return node

    def add_assignments(self, stmt):
        if stmt is None:
            return None
        block = ensure_block(stmt, self.blockified)
        # add assignments to the beginning and to the end of the block
        block.statements = tuple(self.make_assignments(stmt.lineno) + list(block.statements) + self.make_assignments(stmt.lineno))
        return block

    def make_assignments(self, lineno: int):
        res = []
        for var in self.assigned_vars:
            width = self.widths[var]
            const = vast.Identifier(self.make_synth_var(width))
            if self.use_blocking:
                assign = vast.BlockingSubstitution(vast.Lvalue(var), vast.Rvalue(const))
            else:
                assign = vast.NonblockingSubstitution(vast.Lvalue(var), vast.Rvalue(const))
            res.append(self.make_change_stmt(assign, lineno))
        return res


class ProcessAnalyzer(AstVisitor):
    def __init__(self):
        super().__init__()
        self.assigned_vars = set()
        self.blocking_count = 0
        self.non_blocking_count = 0
        self.conditions = []
        self.case_inputs = []

    def run(self, proc: vast.Always):
        self.visit(proc)

    def visit_BlockingSubstitution(self, node: vast.BlockingSubstitution):
        self.generic_visit(node)
        self.blocking_count += 1
        self.assigned_vars.add(node.left.var)

    def visit_NonblockingSubstitution(self, node: vast.NonblockingSubstitution):
        self.generic_visit(node)
        self.non_blocking_count += 1
        self.assigned_vars.add(node.left.var)

    def visit_ForStatement(self, node: vast.ForStatement):
        # ignore the condition, pre and post of the for statement
        self.visit(node.statement)

    def visit_IfStatement(self, node: vast.IfStatement):
        self.conditions.append(node.cond)
        self.visit(node.true_statement)
        self.visit(node.false_statement)

    def visit_CaseStatement(self, node: vast.CaseStatement):
        self.case_inputs.append(node.comp)
        for cc in node.caselist:
            self.visit(cc)


class RegisterFinder(AstVisitor):
    """ collects the names of all variables that are updated in an always @ posedge process with only non-blocking
        assignments
    """
    def __init__(self):
        super().__init__()
        self.registers = set()

    def visit_Always(self, node: vast.Always):
        analysis = ProcessAnalyzer()
        analysis.run(node)
        if analysis.blocking_count > 0:
            if analysis.non_blocking_count > 0:
                print("WARN: single always process seems to mix blocking and non-blocking assignment. Skipping.")
            return node
        for var in analysis.assigned_vars:
            self.registers.add(var)
