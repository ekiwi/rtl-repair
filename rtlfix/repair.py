# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import pyverilog.vparser.ast as vast
from rtlfix.utils import Namespace, serialize, parse_width
from rtlfix.visitor import AstVisitor

_synth_var_prefix = "__synth_"
_synth_change_prefix = "__synth_change_"


def _make_any_const(name: str, width: int) -> vast.Decl:
    assert width >= 1
    width_node = None if width == 1 else vast.Width(vast.IntConst(str(width - 1)), vast.IntConst("0"))
    return vast.Decl((
        vast.Reg(name, width=width_node),
        vast.Assign(
            left=vast.Lvalue(vast.Identifier(name)),
            right=vast.Rvalue(vast.SystemCall("anyconst", []))
        )
    ))


class RepairTemplate(AstVisitor):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.changed = []
        self.synth_vars = []
        self._namespace = None

    def apply(self, namespace: Namespace, ast: vast.Source):
        """ warn: modified in place! """
        # reset variables
        self.changed = []
        self.synth_vars = []
        self._namespace = namespace
        namespace.new_name(_synth_change_prefix + self.name)
        namespace.new_name(_synth_var_prefix + self.name)
        # visit AST
        self.visit(ast)
        # declare synthesis vars
        decls = self._declare_synth_regs()
        mod_def: vast.ModuleDef = ast.description.definitions[0]
        mod_def.items = tuple(decls + list(mod_def.items))

    def _declare_synth_regs(self) -> list:
        syms = [(name, 1) for name in self.changed] + self.synth_vars
        return [_make_any_const(name, width) for name, width in syms]

    def make_change(self, changed_expr: vast.Node, original_expr: vast.Node):
        name: str = self._namespace.new_name(_synth_change_prefix + self.name)
        self.changed.append(name)
        return vast.Cond(vast.Identifier(name), changed_expr, original_expr)

    def make_synth_var(self, width: int):
        name = self._namespace.new_name(_synth_var_prefix + self.name)
        self.synth_vars.append((name, width))
        return name


def do_repair(ast: vast.Source, assignment: dict) -> list:
    """ applies the repair generated by the synthesizer and returns a list of changes """
    return RepairPass().run(ast, assignment)


class RepairPass(AstVisitor):
    """ repairs an AST by applying the assignment generated by the synthesizer """

    def __init__(self):
        super().__init__()
        self.assignment = dict()
        self.width = dict()
        self.changes = []

    def run(self, ast: vast.Source, assignment: dict):
        self.changes = []
        self.assignment = assignment
        self.width = self._remove_synth_var_decl(ast)
        self.visit(ast)
        return self.changes

    def _remove_synth_var_decl(self, ast: vast.Source) -> dict:
        width = dict()
        mod_def: vast.ModuleDef = ast.description.definitions[0]
        items = []
        for entry in mod_def.items:
            is_synth_var = (
                    isinstance(entry, vast.Decl) and
                    isinstance(entry.list[0], vast.Reg) and
                    entry.list[0].name in self.assignment
            )
            if is_synth_var:
                assert len(entry.list) == 2
                reg = entry.list[0]
                width[reg.name] = parse_width(reg.width)
            else:
                items.append(entry)
        mod_def.items = tuple(items)
        return width

    def visit_Cond(self, node: vast.Cond):
        """ implement synthesizer choice (implement decision created by make_change) """
        if not isinstance(node.cond, vast.Identifier):
            return self.generic_visit(node)
        if not node.cond.name.startswith(_synth_change_prefix):
            return self.generic_visit(node)
        # we found a synthesis change, now we need to plug in the original or the old expression
        value = self.assignment[node.cond.name]
        if value == 1:
            # record the change
            changed = self.visit(node.true_value)
            line = str(node.false_value.lineno)
            self.changes.append((line, serialize(node.false_value), changed))
            return changed
        else:
            return self.visit(node.false_value)

    def visit_Identifier(self, node: vast.Identifier):
        """ substitute synthesis variable with value """
        if node.name not in self.assignment:
            return node
        value = self.assignment[node.name]
        width = self.width[node.name]
        prefix = "" if width is None else str(width)
        return vast.IntConst(f"{prefix}'b{value:b}")
