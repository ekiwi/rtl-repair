# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
from rtlfix.visitor import AstVisitor
import pyverilog.vparser.ast as vast
from dataclasses import dataclass
from enum import Enum, auto


class VarType(Enum):
    Input = auto()
    Output = auto()
    Inout = auto()
    Reg = auto()
    Wire = auto()


@dataclass
class VarInfo:
    name: str
    tpe: VarType
    width: int



def infer_types(ast: vast.Source) -> dict:
    return InferTypes().run(ast)


class InferTypes(AstVisitor):
    """ Very basic, very buggy version of type checking/inference for Verilog """
    def __init__(self):
        super().__init__()
        self.widths = dict()
        self.vars = dict()

    def run(self, ast: vast.Source) -> dict:
        """ returns a mapping of node -> type """
        self.widths = dict()
        self.vars = dict()
        self.visit(ast)
        return self.types


    def visit_Input(self, node: vast.Input):
        info = VarInfo(name=node.name, tpe=VarType.Input)
        return node
