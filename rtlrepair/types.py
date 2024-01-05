# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import math

from rtlrepair.visitor import AstVisitor
from rtlrepair.utils import parse_verilog_int_literal
import pyverilog.vparser.ast as vast


def infer_widths(ast: vast.Source) -> dict:
    return InferWidths().run(ast)


_cmp_op = {vast.LessThan, vast.GreaterThan, vast.LessEq, vast.GreaterEq, vast.Eq, vast.NotEq, vast.Eql, vast.NotEql}
_context_dep_bops = {vast.Plus, vast.Minus, vast.Times, vast.Divide, vast.Mod, vast.And, vast.Or, vast.Xor, vast.Xnor}
_shift_ops = {vast.Srl, vast.Sra, vast.Sll, vast.Sla, vast.Power}

class InferWidths(AstVisitor):
    """ Very basic, very buggy version of type checking/inference for Verilog
        Some resources on how width inference for Verilog should actually work:
        - http://yangchangwoo.com/podongii_X2/html/technote/TOOL/MANUAL/21i_doc/data/fndtn/ver/ver4_4.htm
        - https://www.cs.utexas.edu/users/moore/acl2/manuals/current/manual/index-seo.php/VL2014____EXPRESSION-SIZING-INTRO
    """

    def __init__(self):
        super().__init__()
        self.widths = dict()  # ast node value -> width
        self.vars = dict()    # symbol name -> width
        self.params = dict()  # symbol name -> value

    def run(self, ast: vast.Source) -> dict:
        """ returns a mapping of node -> width """
        self.widths = {None: None}
        self.vars = dict()
        self.params = dict()
        self.visit(ast)
        return self.widths

    def expr_width(self, node, env_width) -> int:
        # caching
        if node in self.widths:
            return self.widths[node]

        if isinstance(node, vast.Identifier):
            width = self.vars[node.name]
        elif isinstance(node, vast.Pointer):
            width = self.expr_width(node.var, env_width)
            # visit the index (named ptr here for some reason?!)
            self.expr_width(node.ptr, None)
        elif isinstance(node, vast.IntConst):
            if "'" in node.value and not node.value.startswith("'"):
                width = int(node.value.split("'")[0])
            else:
                width = 32 if env_width is None else env_width
        elif isinstance(node, vast.UnaryOperator):
            #                        +          -            ~
            if type(node) in {vast.Uplus, vast.Uminus, vast.Unot}:
                width = self.expr_width(node.right, env_width)
            #                        |           &         !            ~&         ~|         ^          ~^
            elif type(node) in {vast.Uor, vast.Uand, vast.Ulnot, vast.Unand, vast.Unor, vast.Uxor, vast.Uxnor}:
                self.expr_width(node.right, None)
                width = 1
            else:
                raise NotImplementedError(f"TODO: deal with unary op {node} : {type(node)}")
        elif isinstance(node, vast.Cond):  # ite / (...)? (..) : (..)
            self.expr_width(node.cond, 1)
            width_left = self.expr_width(node.true_value, env_width)
            width_right = self.expr_width(node.false_value, env_width)
            width = max(width_left, width_right)
        elif isinstance(node, vast.Concat):
            widths = [self.expr_width(cc, None) for cc in node.list]
            width = max(widths)
        elif type(node) in {vast.Rvalue, vast.Lvalue}:
            return self.expr_width(node.var, env_width)
        elif type(node) in _context_dep_bops:
            width_left = self.expr_width(node.left, env_width)
            width_right = self.expr_width(node.right, env_width)
            width = max(width_left, width_right)
            if env_width is not None and env_width > width:
                width = env_width
        elif type(node) in _cmp_op:
            _width_left = self.expr_width(node.left, None)
            _width_right = self.expr_width(node.right, None)
            width = 1
        elif type(node) in _shift_ops:
            # shift and power ops have the width of the first expression
            _width_left = self.expr_width(node.left, None)
            _width_right = self.expr_width(node.right, None)
            width = _width_left
        elif isinstance(node, vast.Land) or isinstance(node, vast.Lor):
            # _L_ogical or/and (as opposed to bit-wise)
            _width_left = self.expr_width(node.left, None)
            _width_right = self.expr_width(node.right, None)
            width = 1
        elif isinstance(node, vast.Partselect):
            # this is a bit slice or bit select
            msb = self.eval(node.msb)
            lsb = self.eval(node.lsb)
            assert msb >= lsb >= 0, f"{msb}:{lsb}"
            width = msb - lsb + 1
        elif isinstance(node, vast.IndexedPartselect):
            stride = self.eval(node.stride)
            width = stride
        elif isinstance(node, vast.Repeat):
            value_width = self.expr_width(node.value, None)
            times = self.eval(node.times)
            width = value_width * times
        elif isinstance(node, vast.StringConst):
            width = None
        elif isinstance(node, vast.SystemCall):
            width = 32 # HACK: default integer width (TODO)
        else:
            raise NotImplementedError(f"TODO: deal with {node} : {type(node)}")
        self.widths[node] = width
        return width

    # tries to evaluate constants
    def eval(self, node: vast.Node) -> int:
        if node is None:
            value = None
        elif isinstance(node, vast.IntConst):
            # we do not deal with tri-state signals!
            if 'x' in node.value or 'z' in node.value:
                value = None
            else:
                value, _ = parse_verilog_int_literal(node.value)
        elif isinstance(node, vast.Identifier):
            if not node.name in self.params:
                print()
            # assert node.name in self.params, f"Value of {node.name} not known at compile time. Not a constant?"
            value = self.params[node.name]
        elif isinstance(node, vast.Rvalue):
            value = self.eval(node.var)
        elif isinstance(node, vast.Cond):
            cond = self.eval(node.cond)
            if cond == 0:
                value = self.eval(node.false_value)
            else:
                value = self.eval(node.true_value)
        elif isinstance(node, vast.GreaterThan):
            value = int(self.eval(node.left) > self.eval(node.right))
        elif isinstance(node, vast.Plus):
            value = self.eval(node.left) + self.eval(node.right)
        elif isinstance(node, vast.Minus):
            value = self.eval(node.left) - self.eval(node.right)
        elif isinstance(node, vast.Times):
            value = self.eval(node.left) * self.eval(node.right)
        elif isinstance(node, vast.Divide):
            value = self.eval(node.left) // self.eval(node.right)
        elif isinstance(node, vast.Width):
            msb = self.eval(node.msb)
            lsb = self.eval(node.lsb)
            if msb is None or lsb is None:
                value = None
            else:
                if msb >= lsb >= 0:
                    value = msb - lsb + 1
                else: # little endian?
                    value = lsb - msb + 1
        elif isinstance(node, vast.SystemCall):
            if node.syscall == 'clog2':
                inp = self.eval(node.args[0])
                assert inp >= 0
                if inp == 0:
                    value = 0
                else:
                    value = int(math.ceil(math.log2(inp)))
            else:
                raise NotImplementedError(f"TODO: constant prop: {node} : {type(node)}")
        elif isinstance(node, vast.Concat):
            value = 0
            for expr in node.list:
                expr_value = self.eval(expr)
                shift_amount = self.widths[expr]
                value = (value << shift_amount) | expr_value
        elif isinstance(node, vast.Repeat):
            expr_value = self.eval(node.value)
            shift_amount = self.widths[node.value]
            repetitions = self.eval(node.times)
            assert repetitions >= 0
            value = 0
            for ii in range(repetitions):
                value = (value << shift_amount) | expr_value
        elif isinstance(node, vast.StringConst):
            value = None
        else:
            raise NotImplementedError(f"TODO: constant prop: {node} : {type(node)}")
        return value

    def determine_var_width(self, node):
        assert isinstance(node, vast.Variable) or isinstance(node, vast.Parameter) or isinstance(node, vast.Input) or isinstance(node, vast.Output)
        explicit_width = self.eval(node.width)
        if explicit_width is not None:  # if there is an explicit width annotated, take that
            self.vars[node.name] = explicit_width
        elif node.value is not None:    # otherwise, check if the value has a determined width
            self.vars[node.name] = self.expr_width(node.value, None)
        else:                           # by default if we just declare a reg/wire etc. is will be 1-bit
            self.vars[node.name] = 1

    def generic_visit(self, node):
        if isinstance(node, vast.Variable) or isinstance(node, vast.Input)  or isinstance(node, vast.Output):
            self.determine_var_width(node)
        elif isinstance(node, vast.Parameter):
            self.determine_var_width(node)
            # TODO: we currently assume that the module will be instantiated with the
            #       default parameters, instead one might allow the user pass a parameter assignment
            self.params[node.name] = self.eval(node.value)
        elif isinstance(node, vast.Substitution):
            assert isinstance(node.left, vast.Lvalue)
            assert isinstance(node.right, vast.Rvalue)
            # check the lhs first because it might influence the lhs
            lhs_width = self.expr_width(node.left.var, None)
            rhs_width = self.expr_width(node.right.var, lhs_width)
        elif isinstance(node, vast.IfStatement):
            self.expr_width(node.cond, 1)
            self.visit(node.true_statement)
            self.visit(node.false_statement)
        elif isinstance(node, vast.CaseStatement):
            self.expr_width(node.comp, 1)
            for c in node.caselist:
                self.visit(c)
        elif isinstance(node, vast.Value) or isinstance(node, vast.Operator):
            self.expr_width(node, None)
        else:
            node = super().generic_visit(node)
        return node
