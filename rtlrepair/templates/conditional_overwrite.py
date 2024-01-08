# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


from rtlrepair.repair import RepairTemplate
from rtlrepair.templates.assign_const import ProcessAnalyzer, RegisterFinder
from rtlrepair.types import InferWidths
from rtlrepair.utils import Namespace, ensure_block
import pyverilog.vparser.ast as vast


def conditional_overwrite(ast: vast.Source):
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = ConditionalOverwrite(infer.widths)
    repl.apply(namespace, ast)
    return repl.blockified


class ConditionalOverwrite(RepairTemplate):
    def __init__(self, widths):
        super().__init__(name="conditional_overwrite")
        self.widths = widths
        self.use_blocking = False
        self.assigned_vars = []
        # we use this list to track which new blocks we introduced in order to minimize the diff between
        # buggy and repaired version
        self.blockified = []
        # remember all 1-bit registers
        self.bool_registers = set()

    def visit_ModuleDef(self, node: vast.ModuleDef):
        finder = RegisterFinder()
        finder.visit(node)
        self.bool_registers = set()
        for reg in finder.registers:
            if self.widths[reg] == 1:
                self.bool_registers.add(reg)
        return self.generic_visit(node)

    def visit_Always(self, node: vast.Always):
        analysis = ProcessAnalyzer()
        analysis.run(node)
        if analysis.non_blocking_count > 0 and analysis.blocking_count > 0:
            print("WARN: single always process seems to mix blocking and non-blocking assignment. Skipping.")
            return node
        # collect local condition atoms
        conditions = collect_condition_atoms(analysis.conditions, self.bool_registers)
        # note: we are ignoring pointer for now since these might contain loop vars that may not always be in scope..
        assigned_vars = [var for var in analysis.assigned_vars if isinstance(var, vast.Identifier)]
        self.use_blocking = analysis.blocking_count > 0
        # add conditional overwrites to the end of the process
        stmts = []
        for var in assigned_vars:
            cond = self.gen_condition(conditions, analysis.case_inputs)
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
        tru = vast.IntConst("1'b1")
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


def collect_condition_atoms(conditions: list, regs: set) -> list:
    atoms = set()
    for cond in conditions:
        atoms |= destruct_to_atom(cond)
    atoms |= regs
    return list(atoms)


def destruct_to_atom(expr: list) -> set:
    """ conjunction and negation is already part of our template, thus we want to exclude it from our atoms """
    if isinstance(expr, vast.Unot) or isinstance(expr, vast.Ulnot):
        return destruct_to_atom(expr.right)
    elif isinstance(expr, vast.Land) or isinstance(expr, vast.Uand):
        return destruct_to_atom(expr.left) | destruct_to_atom(expr.right)
    else:
        return { expr }
