# Copyright 2023-2024 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


from rtlrepair.repair import RepairTemplate
from rtlrepair.templates.assign_const import ProcessAnalyzer
from rtlrepair.analysis import AnalysisResults, VarInfo, get_rvars, get_lvars
from rtlrepair.utils import Namespace, ensure_block
import pyverilog.vparser.ast as vast


def conditional_overwrite(ast: vast.Source, analysis: AnalysisResults):
    namespace = Namespace(ast)
    repl = ConditionalOverwrite(analysis)
    repl.apply(namespace, ast)
    return repl.blockified


tru = vast.IntConst("1'b1")
fals = vast.IntConst("1'b0")

class ConditionalOverwrite(RepairTemplate):
    def __init__(self, analysis: AnalysisResults):
        super().__init__(name="conditional_overwrite")
        self.widths = analysis.widths
        self.cond_res = analysis.cond_res
        self.vars = analysis.vars
        self.use_blocking = False
        self.assigned_vars = []
        # we use this list to track which new blocks we introduced in order to minimize the diff between
        # buggy and repaired version
        self.blockified = []
        # remember all 1-bit registers
        self.bool_registers = set()

    def visit_Always(self, node: vast.Always):
        analysis = ProcessAnalyzer()
        analysis.run(node)
        if analysis.non_blocking_count > 0 and analysis.blocking_count > 0:
            print("WARN: single always process seems to mix blocking and non-blocking assignment. Skipping.")
            return node
        # collect local condition atoms
        conditions = collect_condition_atoms(analysis.conditions)
        # note: we are ignoring pointer for now since these might contain loop vars that may not always be in scope..
        assigned_vars = [var for var in analysis.assigned_vars if isinstance(var, vast.Identifier)]
        self.use_blocking = analysis.blocking_count > 0
        # add conditional overwrites to the end of the process
        stmts = []
        for var in assigned_vars:
            lvars = get_lvars(var)
            filtered_conditions = filter_atom(conditions, lvars, self.vars)
            filtered_case_inputs = filter_atom(analysis.case_inputs, lvars, self.vars)
            if len(filtered_conditions) > 0 or len(filtered_case_inputs) > 0:
                cond = self.gen_condition(filtered_conditions, filtered_case_inputs)
                assignment = self.make_assignment(var)
                inner = vast.IfStatement(cond, assignment, None)
                stmts.append(self.make_change_stmt(inner, 0))
        # append statements
        node.statement = ensure_block(node.statement, self.blockified)
        node.statement.statements = tuple(list(node.statement.statements) + stmts)
        return node

    def gen_condition(self, conditions: list, case_inputs: list) -> vast.Node:
        atoms = conditions + [vast.Eq(ci, vast.Identifier(self.make_synth_var(self.widths[ci]))) for ci in case_inputs]
        # atoms can be inverted
        atoms_or_inv = [self.make_synth_choice(aa, vast.Ulnot(aa)) for aa in atoms]
        # atoms do not need to be used
        atoms_optional = [self.make_change(aa, tru) for aa in atoms_or_inv]
        # combine all atoms together
        node = atoms_optional[0]
        for aa in atoms_optional[1:]:
            node = vast.And(node, aa)
        return node

    def make_synth_choice(self, a, b):
        name = self.make_synth_var(1)
        return vast.Cond(vast.Identifier(name), a, b)

    def make_assignment(self, var):
        width = self.widths[var]
        const = vast.Identifier(self.make_synth_var(width))
        if self.use_blocking:
            assign = vast.BlockingSubstitution(vast.Lvalue(var), vast.Rvalue(const))
        else:
            assign = vast.NonblockingSubstitution(vast.Lvalue(var), vast.Rvalue(const))
        return assign


def filter_atom(atoms: list, lvars: set[str], info: dict[str, VarInfo]) -> list:
    # we can only use something as a condition, if it does not depend on any of the lvalues
    out = []
    for atom in atoms:
        atom_vars = get_rvars(atom)
        if atom_dep_ok(atom_vars, lvars, info):
            out.append(atom)
    return out


def atom_dep_ok(atom_vars: set[str], lvars: set[str], info: dict[str, VarInfo]) -> bool:
    for av in atom_vars:
        ai = info[av]
        if len(lvars & info[av].depends_on) > 0:
            return False
    return True


def collect_condition_atoms(conditions: list) -> list:
    atoms = set()
    for cond in conditions:
        atoms |= destruct_to_atom(cond)
    return list(atoms)


def destruct_to_atom(expr: list) -> set:
    """ conjunction and negation is already part of our template, thus we want to exclude it from our atoms """
    if isinstance(expr, vast.UnaryOperator):
        return destruct_to_atom(expr.right)
    elif isinstance(expr, vast.Land):
        return destruct_to_atom(expr.left) | destruct_to_atom(expr.right)
    else:
        return { expr }
