# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import rtlfix.visitor
import pyverilog.vparser.ast as vast
from pyverilog.utils.identifiervisitor import getIdentifiers

_synth_var_prefix = "__synth_"
_synth_change_prefix = "__synth_change_"


class Namespace:
    def __init__(self, ast=None):
        self._names = set()
        if ast is not None:
            ids = getIdentifiers(ast)
            self._names |= set(ids)

    def new_name(self, name):
        final_name = name
        counter = 0
        while final_name in self._names:
            final_name = f"{name}_{counter}"
            counter += 1
        self._names.add(final_name)
        return final_name


def _make_any_const(name: str, width: int) -> vast.Decl:
    assert width >= 1
    width_node = None if width == 1 else vast.Width(vast.IntConst(str(width-1)), vast.IntConst("0"))
    return vast.Decl((
      vast.Reg(name, width=width_node),
      vast.Assign(
          left=vast.Lvalue(vast.Identifier(name)),
          right=vast.Rvalue(vast.SystemCall("anyconst", []))
      )
    ))


class RepairTemplate(visitor.AstVisitor):
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
        name = self._namespace.new_name(_synth_change_prefix + self.name)
        self.changed.append(name)
        return vast.Cond(vast.Identifier(name), changed_expr, original_expr)

    def make_synth_var(self, width: int):
        name = self._namespace.new_name(_synth_var_prefix + self.name)
        self.synth_vars.append((name, width))
        return name
