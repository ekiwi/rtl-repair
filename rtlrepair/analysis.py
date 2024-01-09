# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import math

from typing import Optional, Dict
from dataclasses import dataclass, field
from rtlrepair.visitor import AstVisitor
from rtlrepair.utils import parse_verilog_int_literal
import pyverilog.vparser.ast as vast


@dataclass
class ProcInfo:
    clock: Optional[vast.Identifier] = None
    reset: Optional[vast.Identifier] = None
    is_posedge: Optional[bool] = None

    def is_comb(self) -> bool:
        return self.clock is None

    def is_sync(self) -> bool:
        return not self.is_comb()

    def render(self) -> str:
        if self.clock is None:
            return ""
        edge = "posedge" if self.is_posedge else "negedge"
        out = f"@{edge} {self.clock.name}"
        if self.reset is not None:
            out += f" {self.reset.name}"
        return out


@dataclass
class VarInfo:
    name: str
    width: int
    value: Optional[int] = None  # for constants
    clocking: Optional[ProcInfo] = None
    is_input: bool = False
    is_output: bool = False
    is_const: bool = False
    depends_on: set[str] = field(default_factory=set)

    def is_register(self) -> bool:
        return self.clocking is not None and self.clocking.is_sync()

    def render(self) -> str:
        out = ""
        if self.is_const:
            out += "const "
        if self.is_input:
            out += "inp "
        if self.is_output:
            out += "out "
        if self.is_register():
            out += f"reg ({self.clocking.render()}) "
        out += self.name + ": {"
        out += ", ".join(sorted(self.depends_on))
        out += "}"
        return out


@dataclass
class AnalysisResults:
    widths: dict[vast.Node, int]
    vars: dict[str, VarInfo]
    cond_res: Dict[vast.Node, int]

    def var_list(self) -> list[VarInfo]:
        return sorted(self.vars.values(), key=lambda i: i.name)


def analyze_ast(ast: vast.Source) -> AnalysisResults:
    # ast.show()
    infer = InferWidths()
    infer.run(ast)
    deps = DependencyAnalysis(infer.vars, infer.widths, infer.params)
    deps.visit(ast)
    resolve_transitory(deps.vars)
    return AnalysisResults(infer.widths, deps.vars, deps.cond_res)


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
        self.vars = dict()  # symbol name -> width
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
            width = 32  # HACK: default integer width (TODO)
        else:
            raise NotImplementedError(f"TODO: deal with {node} : {type(node)}")
        self.widths[node] = width
        return width

    def eval(self, node: vast.Node) -> Optional[int]:
        return eval_const_expr(node, self.params, self.widths)

    def determine_var_width(self, node):
        assert isinstance(node, vast.Variable) or isinstance(node, vast.Parameter) or isinstance(node,
                                                                                                 vast.Input) or isinstance(
            node, vast.Output)
        explicit_width = self.eval(node.width)
        if explicit_width is not None:  # if there is an explicit width annotated, take that
            self.vars[node.name] = explicit_width
        elif node.value is not None:  # otherwise, check if the value has a determined width
            self.vars[node.name] = self.expr_width(node.value, None)
        else:  # by default if we just declare a reg/wire etc. is will be 1-bit
            self.vars[node.name] = 1

    def generic_visit(self, node):
        if isinstance(node, vast.Variable) or isinstance(node, vast.Input) or isinstance(node, vast.Output):
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


def eval_const_expr(node: vast.Node, const_values: dict[str, int], widths: [vast.Node, int]) -> Optional[int]:
    if node is None:
        value = None
    elif isinstance(node, vast.IntConst):
        # we do not deal with tri-state signals!
        if 'x' in node.value or 'z' in node.value:
            value = None
        else:
            value, _ = parse_verilog_int_literal(node.value)
    elif isinstance(node, vast.Identifier):
        if node.name not in const_values:
            raise RuntimeError(f"{node.name} is not constant")
        else:
            value = const_values[node.name]
    elif isinstance(node, vast.Rvalue):
        value = eval_const_expr(node.var, const_values, widths)
    elif isinstance(node, vast.Cond):
        cond = eval_const_expr(node.cond, const_values, widths)
        if cond == 0:
            value = eval_const_expr(node.false_value, const_values, widths)
        else:
            value = eval_const_expr(node.true_value, const_values, widths)
    elif isinstance(node, vast.GreaterThan):
        value = int(eval_const_expr(node.left, const_values, widths) > eval_const_expr(node.right, const_values, widths))
    elif isinstance(node, vast.Plus):
        value = eval_const_expr(node.left, const_values, widths) + eval_const_expr(node.right, const_values, widths)
    elif isinstance(node, vast.Minus):
        value = eval_const_expr(node.left, const_values, widths) - eval_const_expr(node.right, const_values, widths)
    elif isinstance(node, vast.Times):
        value = eval_const_expr(node.left, const_values, widths) * eval_const_expr(node.right, const_values, widths)
    elif isinstance(node, vast.Divide):
        value = eval_const_expr(node.left, const_values, widths) // eval_const_expr(node.right, const_values, widths)
    elif isinstance(node, vast.Land):
        value = eval_const_expr(node.left, const_values, widths) & eval_const_expr(node.right, const_values, widths)
    elif isinstance(node, vast.Ulnot):
        value = ~eval_const_expr(node.left, const_values, widths)
    elif isinstance(node, vast.Width):
        msb = eval_const_expr(node.msb, const_values, widths)
        lsb = eval_const_expr(node.lsb, const_values, widths)
        if msb is None or lsb is None:
            value = None
        else:
            if msb >= lsb >= 0:
                value = msb - lsb + 1
            else:  # little endian?
                value = lsb - msb + 1
    elif isinstance(node, vast.SystemCall):
        if node.syscall == 'clog2':
            inp = eval_const_expr(node.args[0], const_values, widths)
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
            expr_value = eval_const_expr(expr, const_values, widths)
            shift_amount = widths[expr]
            value = (value << shift_amount) | expr_value
    elif isinstance(node, vast.Repeat):
        expr_value = eval_const_expr(node.value, const_values, widths)
        shift_amount = widths[node.value]
        repetitions = eval_const_expr(node.times, const_values, widths)
        assert repetitions >= 0
        value = 0
        for ii in range(repetitions):
            value = (value << shift_amount) | expr_value
    elif isinstance(node, vast.StringConst):
        value = None
    else:
        raise NotImplementedError(f"TODO: constant prop: {node} : {type(node)}")
    return value


def resolve_transitory(vars: dict[str, VarInfo]):
    for v in vars.values():
        old_size = len(v.depends_on)
        for other in list(v.depends_on):
            other_info = vars[other]
            if not other_info.is_register():
                v.depends_on |= other_info.depends_on
        if len(v.depends_on) == old_size:
            continue  # fixed point


class DependencyAnalysis(AstVisitor):
    """ Analysis a Verilog module to find all combinatorial dependencies """

    def __init__(self, widths: dict[str, int], expr_widths: dict[vast.Node, int], param_values: dict[str, int]):
        super().__init__()
        self.widths = widths
        self.expr_widths = expr_widths
        self.param_values = param_values
        self.vars: Dict[str, VarInfo] = {}
        self.cond_res: Dict[vast.Node, int] = {}
        self.proc_info: Optional[ProcInfo] = None
        self.path_stack = []
        self.in_initial = False

    def visit_ModuleDef(self, node: vast.ModuleDef):
        self.vars = {}
        self.generic_visit(node)

    def visit_Decl(self, node: vast.Decl):
        self.in_initial = True
        self.generic_visit(node)
        self.in_initial = False

    def visit_Initial(self, node: vast.Initial):
        pass # skip

    def visit_Parameter(self, node: vast.Parameter):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, self.widths[node.name], is_const=True,
                                       value=self.param_values[node.name])

    def visit_Localparam(self, node: vast.Localparam):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, self.widths[node.name], is_const=True,
                                       value=self.param_values[node.name])

    def visit_Input(self, node: vast.Input):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, self.widths[node.name], is_input=True)

    def visit_Output(self, node: vast.Output):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, self.widths[node.name], is_output=True)

    def visit_Variable(self, node: vast.Variable):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, self.widths[node.name])

    def visit_Integer(self, node: vast.Integer):
        assert node.name not in self.vars
        self.vars[node.name] = VarInfo(node.name, self.widths[node.name])

    def visit_Reg(self, node: vast.Reg):
        # reg can be used as a modifier
        if node.name not in self.vars:
            self.vars[node.name] = VarInfo(node.name, self.widths[node.name])

    def visit_Wire(self, node: vast.Wire):
        # wire can be used as a modifier
        if node.name not in self.vars:
            self.vars[node.name] = VarInfo(node.name, self.widths[node.name])

    def visit_Always(self, node: vast.Always):
        # try to see if this process implements synchronous logic
        self.proc_info = find_clock_and_reset(node.sens_list)
        self.visit(node.statement)
        self.proc_info = None

    def visit_NonblockingSubstitution(self, node: vast.NonblockingSubstitution):
        # if we are in an initial block, then this is an "init" assignment which we do not count for dependencies
        if self.in_initial:
            return
        self.visit_assignment(is_blocking=False, left=node.left, right=node.right)

    def visit_BlockingSubstitution(self, node: vast.BlockingSubstitution):
        # if we are in an initial block, then this is an "init" assignment which we do not count for dependencies
        if self.in_initial:
            return
        self.visit_assignment(is_blocking=True, left=node.left, right=node.right)

    def visit_Assign(self, node: vast.Assign):
        # if we are in an initial block, then this is an "init" assignment which we do not count for dependencies
        if self.in_initial:
            return
        # fake a proc info
        self.proc_info = ProcInfo()
        # treat like an blocking assignment in a comb process
        self.visit_assignment(is_blocking=True, left=node.left, right=node.right)
        self.proc_info = None

    def visit_assignment(self, is_blocking: bool, left: vast.Lvalue, right: vast.Node):
        # warn about mixed assignments
        if self.proc_info is None:
            print("TODO")
        if is_blocking and self.proc_info.is_sync():
            print("[DependencyAnalysis] WARN: blocking assignment in sync logic process!")
        if not is_blocking and self.proc_info.is_comb():
            print("[DependencyAnalysis] WARN: non-blocking assignment in comb logic process!")

        names = sorted(get_lvars(left))
        for name in names:
            vv = self.vars[name]
            if vv.clocking is None:
                vv.clocking = self.proc_info
            else:
                assert vv.clocking == self.proc_info, f"{name}: {vv.clocking} vs. {self.proc_info}"
            if is_blocking:
                # we only track comb dependencies
                vv.depends_on |= self.get_path_dependencies()
                vv.depends_on |= get_rvars(right)

    def get_path_dependencies(self) -> set:
        out = set()
        for dd in self.path_stack:
            out |= dd
        return out

    def visit_IfStatement(self, node: vast.IfStatement):
        # try to see if the condition is known at elaboration time
        if self.is_const_expr(node.cond):
            cond_res = eval_const_expr(node.cond, self.param_values, self.expr_widths)
            self.cond_res[node.cond] = cond_res
            if cond_res == 0:
                self.visit(node.false_statement)
            else:
                self.visit(node.true_statement)
        else:
            cond_vars = get_rvars(node.cond)
            self.path_stack.append(cond_vars)
            self.visit(node.true_statement)
            self.visit(node.false_statement)
            self.path_stack.pop()

    def is_const_expr(self, expr: vast.Node) -> bool:
        for var in get_rvars(expr):
            if not self.vars[var].is_const:
                return False
        return True

def get_lvars(expr: vast.Node) -> set[str]:
    """ returns variable that is being assigned """
    if isinstance(expr, vast.Lvalue):
        return get_lvars(expr.var)
    elif isinstance(expr, vast.Identifier):
        return {expr.name}
    elif isinstance(expr, vast.Concat) or isinstance(expr, vast.LConcat):
        out = set()
        for e in expr.list:
            out |= get_lvars(e)
        return out
    elif isinstance(expr, vast.IndexedPartselect):
        # here we do not care about the index since that is not actually being assigned to
        return get_lvars(expr.var)
    elif isinstance(expr, vast.Partselect):
        # here we do not care about the index since that is not actually being assigned to
        return get_lvars(expr.var)
    elif isinstance(expr, vast.Pointer):
        return get_lvars(expr.var)
    else:
        raise NotImplementedError(f"TODO: implement get_lvar for {expr} : {type(expr)}")


def get_rvars(expr: vast.Node) -> set[str]:
    """ returns variables that are being read """
    if isinstance(expr, vast.Identifier):
        return {expr.name}
    elif isinstance(expr, vast.Rvalue):
        return get_rvars(expr.var)
    else:
        out = set()
        for e in expr.children():
            out |= get_rvars(e)
        return out


def find_clock_and_reset(sens: vast.SensList) -> ProcInfo:
    """ tries to find clock and/or reset signals for a process """
    # if the senslist is not 1 or 2 in length we assume that it is a combinatorial process\
    if len(sens.list) < 1 or len(sens.list) > 2:
        return ProcInfo()
    # no we try to find an edge
    edges = [s.type for s in sens.list]

    if edges == ['all']:
        # @(*)
        return ProcInfo()
    elif edges == ['posedge']:
        return ProcInfo(clock=sens.list[0].sig, is_posedge=True)
    elif edges == ['negedge']:
        return ProcInfo(clock=sens.list[0].sig, is_posedge=False)
    elif edges == ['posedge', 'posedge']:
        # HACK: try to distinguish clock and reset by name
        if sens.list[0].sig.name.startswith('cl'):
            return ProcInfo(clock=sens.list[0].sig, is_posedge=True, reset=sens.list[1].sig)
        elif sens.list[1].sig.name.startswith('cl'):
            return ProcInfo(clock=sens.list[1].sig, is_posedge=True, reset=sens.list[0].sig)
        else:
            raise NotImplementedError(f"{sens.list}")
    else:
        raise NotImplementedError(f"{edges}")
