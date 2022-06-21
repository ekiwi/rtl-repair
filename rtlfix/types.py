# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.visitor import AstVisitor
from rtlfix.utils import parse_width
import pyverilog.vparser.ast as vast


def infer_widths(ast: vast.Source) -> dict:
    return InferWidths().run(ast)


class ExpressionWidthChecker:
    def __init__(self, symbols: dict):
        self.symbols = symbols
        self.widths = dict()

    def visit(self, node, env_width) -> int:
        # caching
        if node in self.widths:
            return self.widths[node]

        if isinstance(node, vast.Identifier):
            width = self.symbols[node.name]
        elif isinstance(node, vast.IntConst):
            if "'" in node.value:
                width = int(node.value.split("'")[0])
            else:
                width = 32 if env_width is None else env_width
        elif isinstance(node, vast.UnaryOperator):
            #                        +          -            ~
            if type(node) in {vast.Uplus, vast.Uminus, vast.Unot}:
                width = self.visit(node.right, env_width)
            #                        |           &         !            ~&         ~|         ^          ~^
            elif type(node) in {vast.Uor, vast.Uand, vast.Ulnot, vast.Unand, vast.Unor, vast.Uxor, vast.Uxnor}:
                self.visit(node.right, 1)
                width = 1
            else:
                raise NotImplementedError(f"TODO: deal with unary op {node} : {type(node)}")
        else:
            raise NotImplementedError(f"TODO: deal with {node} : {type(node)}")
        self.widths[node] = width
        return width


class InferWidths(AstVisitor):
    """ Very basic, very buggy version of type checking/inference for Verilog
        Some resources on how width inference for Verilog should actually work:
        - http://yangchangwoo.com/podongii_X2/html/technote/TOOL/MANUAL/21i_doc/data/fndtn/ver/ver4_4.htm
        - https://www.cs.utexas.edu/users/moore/acl2/manuals/current/manual/index-seo.php/VL2014____EXPRESSION-SIZING-INTRO
    """

    def __init__(self):
        super().__init__()
        self.widths = dict()  # ast node value -> width
        self.vars = dict()  # symbol name -> width

    def run(self, ast: vast.Source) -> dict:
        """ returns a mapping of node -> width """
        self.widths = dict()
        self.vars = dict()
        self.visit(ast)
        return self.widths

    def _get_width(self, node, env_width) -> int:
        checker = ExpressionWidthChecker(self.vars)
        width = checker.visit(node, env_width)
        self.widths.update(checker.widths)
        return width

    def generic_visit(self, node):
        if isinstance(node, vast.Variable):
            self.vars[node.name] = parse_width(node.width)
        elif isinstance(node, vast.Substitution):
            assert isinstance(node.left, vast.Lvalue)
            assert isinstance(node.right, vast.Rvalue)
            # check the lhs first because it might influence the lhs
            lhs_width = self._get_width(node.left.var, None)
            rhs_width = self._get_width(node.right.var, lhs_width)
        elif isinstance(node, vast.Value) or isinstance(node, vast.Operator):
            self._get_width(node, None)
        else:
            node = super().generic_visit(node)
        return node
