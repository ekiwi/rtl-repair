# Copyright 2023-2024 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import math

from rtlrepair.repair import RepairTemplate
from rtlrepair.analysis import InferWidths, AnalysisResults, get_lvars
from rtlrepair.templates.assign_const import ProcessAnalyzer
from rtlrepair.utils import Namespace, ensure_block
import pyverilog.vparser.ast as vast


def add_guard(ast: vast.Source, analysis: AnalysisResults):
    """ Adds a condition to a boolean expression. """
    namespace = Namespace(ast)
    ag = AddGuard(analysis)
    ag.apply(namespace, ast)
    return ag.blockified


tru = vast.IntConst("1'b1")
fals = vast.IntConst("1'b0")


class AddGuard(RepairTemplate):
    def __init__(self, analysis: AnalysisResults):
        super().__init__(name="add_guard")
        self.a = analysis
        self.in_proc = False
        # we use this list to track which new blocks we introduced in order to minimize the diff between
        # buggy and repaired version
        self.blockified = []

    def visit_Initial(self, node: vast.Initial):
        # ignore initial blocks
        return node

    def visit_Decl(self, node: vast.Decl):
        # ignore declarations
        return node

    def visit_Assign(self, node: vast.Assign):
        # assignments outside of a process
        if self.in_proc:
            return node  # unexpected
        # check to see if this is a 1-bit assignment
        if self.a.widths[node.left.var] != 1:
            return node
        atoms = find_atoms(get_lvars(node.left), self.a)
        node.right.var = self.build_guard(node.right.var, atoms)
        return node

    def visit_Always(self, node: vast.Always):
        self.in_proc = True
        node.statement = self.visit(node.statement)
        self.in_proc = False
        return node

    def visit_IfStatement(self, node: vast.IfStatement):
        # we are not interested in if statements outside of processes
        if not self.in_proc:
            return node
        # first we visit the children
        node.true_statement = self.visit(node.true_statement)
        node.false_statement = self.visit(node.false_statement)
        # see which variables are assigned in this statement
        analysis = ProcessAnalyzer()
        analysis.visit(node.true_statement)
        analysis.visit(node.false_statement)
        if analysis.blocking_count > 0:
            lvars = set.union(*[get_lvars(a) for a in analysis.assigned_vars])
        else:
            lvars = set()
        atoms = find_atoms(lvars, self.a)
        node.cond = self.build_guard(node.cond, atoms)
        return node


    def build_guard(self, expr: vast.Node, atoms: list[vast.Node]) -> vast.Node:
        """
        Our template is essentially: (!?)(...) && ((!)?a || (!?)b)
        Cost is:
            - 1 for inverting the original condition
            - 1 for adding guard a
            - 1 for adding guard b
        """
        do_invert = self.make_change_var()
        may_invert = vast.Xor(vast.Identifier(do_invert), expr)
        if len(atoms) == 0:
            return may_invert
        a = self.build_guard_item(atoms)
        b = self.build_guard_item(atoms)
        may_b = self.make_change(b, fals)  # false is the neutral element
        a_or_b = vast.Or(a, may_b)
        may_a_or_b = self.make_change(a_or_b, tru)  # true is the neutral element
        return vast.And(may_invert, may_a_or_b)

    def build_guard_item(self, atoms: list[vast.Node]) -> vast.Node:
        assert len(atoms) > 0
        out = atoms[0]
        if len(atoms) > 1:
            # select one atom
            select_width = int(math.ceil(math.log2(len(atoms))))
            selector = vast.Identifier(self.make_synth_var(select_width))
            for ii, other in enumerate(atoms[1:]):
                ident = vast.IntConst(f"{select_width}'b{ii:b}")
                out = vast.Cond(vast.Eq(selector, ident), other, out)
        # may invert for free
        do_invert = self.make_synth_var(1)
        return vast.Xor(vast.Identifier(do_invert), out)


def find_atoms(lvars: set[str], a: AnalysisResults) -> list[vast.Node]:
    verbose = False
    atoms = []
    l_deps = set() if len(lvars) == 0 else set.union(*[a.vars[v].depends_on for v in lvars])
    if verbose:
        print(f"l_deps={l_deps}")
    for var in a.vars.values():
        # we are only interested in 1-bit vars
        if var.width != 1:
            continue
        # ignore clock signals
        if var.is_clock:
            continue

        # check which only mater for comb assignments
        if len(lvars) > 0 and len(var.depends_on) > 0:
            # check to see if the variable would create a loop
            lvar_deps = lvars & var.depends_on
            if len(lvar_deps) > 0 or var.name in lvars:
                continue
            # check to see if we would create a new dependency
            if verbose:
                print(f"{var.name}.depends_on = {var.depends_on}")
            new_deps = (var.depends_on | {var.name}) - l_deps
            if len(new_deps) > 0:
                continue
        # otherwise this might be a good candidate
        atoms.append(vast.Identifier(var.name))
    return atoms
