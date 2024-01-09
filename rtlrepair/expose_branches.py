# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


from rtlrepair.analysis import InferWidths
from rtlrepair.utils import Namespace, serialize
from rtlrepair.visitor import AstVisitor
import pyverilog.vparser.ast as vast


def expose_branches(ast: vast.Source):
    """
    Exposes all branch conditions as inputs and outputs.
    Naming scheme: input _b0, output _p0
    """
    # ast.show()
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = BranchExposer(infer.widths, infer.vars, infer.params)
    repl.apply(ast)
    # print("AFTER")
    # print(serialize(ast))


def make_input(name: str) -> vast.Ioport:
    return vast.Ioport(vast.Input(name))


def make_output(name: str) -> vast.Ioport:
    return vast.Ioport(vast.Output(name))


class BranchExposer(AstVisitor):
    def __init__(self, widths, vars, params):
        super().__init__()
        self.widths = widths
        self.vars = vars
        self.params = params
        self.branch_count = 0

    def apply(self, ast: vast.Source):
        self.visit(ast)

    def visit_ModuleDef(self, node: vast.ModuleDef):
        # reset list of branches / predicates
        self.branch_count = 0
        node = self.generic_visit(node)
        # add phi and alpha as inputs
        ports = list(node.portlist.ports)
        for ii in range(self.branch_count):
            ports += [make_input(f"_p{ii}"), make_input(f"_a{ii}")]
        node.portlist.ports = tuple(ports)

    def expose(self, cond):
        ii = self.branch_count
        self.branch_count += 1
        expr = vast.Cond(vast.Identifier(f"_p{ii}"), vast.Identifier(f"_a{ii}"), cond)
        return expr

    def visit_IfStatement(self, node: vast.IfStatement):
        # visit child nodes first since they might contain more branches
        node.true_statement = self.visit(node.true_statement)
        node.false_statement = self.visit(node.false_statement)
        else_cond = vast.Ulnot(node.cond)
        # expose true branch
        node.cond = self.expose(node.cond)
        # turn else branch into its own independent branch
        if node.false_statement is not None:
            else_cond = self.expose(else_cond)
            false_stmt = vast.IfStatement(else_cond, node.false_statement, None)
            node.false_statement = None
            node = vast.Block((node, false_stmt))
        return node

    def visit_Cond(self, node: vast.Cond):
        # visit child nodes first since they might contain more branches
        node.true_value = self.visit(node.true_value)
        node.false_value = self.visit(node.false_value)
        # expose true branch
        node.cond = self.expose(node.cond)
        return node
