# Copyright 2023-2024 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
from typing import Optional, Dict

import pyverilog.vparser.ast as vast
from rtlrepair.visitor import AstVisitor
from dataclasses import dataclass, field


@dataclass
class VarInfo:
    name: str
    clock: Optional[vast.Identifier] = None
    reset: Optional[vast.Identifier] = None
    is_input: bool = False
    is_output: bool = False
    is_parameter: bool = False
    depends_on: set = field(default_factory=set)

    def is_register(self) -> bool:
        return self.clock is not None


@dataclass
class ProcInfo:
    clock: Optional[vast.Identifier] = None
    reset: Optional[vast.Identifier] = None
    is_posedge: Optional[bool] = None

    def is_comb(self) -> bool:
        return self.clock is None

    def is_sync(self) -> bool:
        return not self.is_comb()


def analyze_dependencies(ast: vast.Source) -> list[VarInfo]:
    analysis = DependencyAnalysis()
    analysis.visit(ast)
    var_list = sorted(analysis.vars.values(), key=lambda x: x.name)
    return var_list


class DependencyAnalysis(AstVisitor):
    """ Analysis a Verilog module to find all combinatorial dependencies """

    def __init__(self):
        super().__init__()
        self.vars: Dict[str, VarInfo] = {}
        self.proc_info: Optional[ProcInfo] = None
        self.path_stack = []

    def visit_ModuleDef(self, node: vast.ModuleDef):
        self.vars = {}
        self.generic_visit(node)

    def visit_Parameter(self, node: vast.Parameter):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, is_parameter=True)

    def visit_Input(self, node: vast.Input):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, is_input=True)

    def visit_Output(self, node: vast.Output):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, is_output=True)

    def visit_Variable(self, node: vast.Variable):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name)

    def visit_Always(self, node: vast.Always):
        # try to see if this process implements synchronous logic
        self.proc_info = find_clock_and_reset(node.sens_list)
        assert len(self.path_stack) == 0
        self.visit(node.statement)
        assert len(self.path_stack) == 0
        self.proc_info = None

    def visit_NonblockingSubstitution(self, node: vast.NonblockingSubstitution):
        if self.proc_info.is_comb():
            print("WARN: non-blocking assignment in comb logic process!")
        else:
            name = get_lvar(node.left)
            self.vars[name].clock = self.proc_info.clock
            self.vars[name].reset = self.proc_info.reset

    def visit_IfStatement(self, node: vast.IfStatement):
        cond_vars = get_rvars(node.cond)
        self.path_stack.append(cond_vars)
        self.visit(node.true_statement)
        self.visit(node.false_statement)
        self.path_stack.pop()


def get_lvar(expr: vast.Node) -> str:
    """ returns variable that is being assigned """
    if isinstance(expr, vast.Lvalue):
        return get_lvar(expr.var)
    elif isinstance(expr, vast.Identifier):
        return expr.name
    else:
        raise NotImplementedError(f"TODO: implement get_lvar for {expr} : {type(expr)}")


def get_rvars(expr: vast.Node) -> set[str]:
    """ returns variables that are being read """
    if isinstance(expr, vast.Identifier):
        return set(expr.name)
    elif isinstance(expr, vast.UnaryOperator):
        return get_rvars(expr.right)
    else:
        raise NotImplementedError(f"TODO: implement get_rvars for {expr} : {type(expr)}")


def find_clock_and_reset(sens: vast.SensList) -> ProcInfo:
    """ tries to find clock and/or reset signals for a process """
    # if the senslist is not 1 or 2 in length we assume that it is a combinatorial process\
    if len(sens.list) < 1 or len(sens.list) > 2:
        return ProcInfo()
    # no we try to find an edge
    edges = [s.type for s in sens.list]
    if edges == ['posedge']:
        return ProcInfo(clock=sens.list[0].sig, is_posedge=True)
    else:
        raise NotImplementedError("{edges}")
