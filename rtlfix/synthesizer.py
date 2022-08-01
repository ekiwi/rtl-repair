# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import copy
import subprocess
import json
from pathlib import Path
from rtlfix.utils import _root_dir, serialize
import pyverilog.vparser.ast as vast


# the synthesizer is written in Scala, the source code lives in src
from rtlfix.visitor import AstVisitor

_jar_rel = Path("target") / "scala-2.13" / "bug-fix-synthesizer-assembly-0.1.jar"
_synthesizer_dir = _root_dir / "synthesizer"
_jar = _synthesizer_dir / _jar_rel


def _check_jar():
    assert _jar.exists(), f"Failed to find JAR, did you run sbt assembly?\n{_jar}"


def _run_synthesizer(design: Path, testbench: Path, solver: str, init: str, incremental: bool):
    assert design.exists(), f"{design=} does not exist"
    assert testbench.exists(), f"{testbench=} does not exist"
    _check_jar()
    args = ["--design", str(design), "--testbench", str(testbench), "--solver", solver, "--init", init]
    if incremental:
        args += ["--incremental"]
    cmd = ["java", "-cp", _jar, "synth.Synthesizer"] + args
    cmd_str = ' '.join(str(p) for p in cmd) # for debugging
    r = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    try:
        return json.loads(r.stdout.decode('utf-8'))
    except json.JSONDecodeError as e:
        print("Failed to parse synthesizer output as JSON:")
        print(r.stdout)
        raise e


_minimal_btor_conversion = [
    "proc -noopt",
    "async2sync", # required for designs with async reset
    "flatten",
    "dffunmap",
]
# inspired by the commands used by SymbiYosys
_btor_conversion = [
    "proc",
    # common prep
    "async2sync",
    "opt_clean",
    "setundef -anyseq",
    "opt -keepdc -fast",
    "check",
    # "hierarchy -simcheck",
    # btor
    "flatten",
    "setundef -undriven -anyseq",
    "dffunmap",
]


def _to_btor(filename: Path, additional_sources: list, top: str):
    for src in additional_sources:
        assert src.exists(), f"{src} does not exist"
    assert filename.exists(), f"{filename} does not exist"
    cwd = filename.parent
    assert cwd.exists(), f"directory {cwd} does not exist"
    r = subprocess.run(["yosys", "-version"], check=False, stdout=subprocess.PIPE)
    assert r.returncode == 0, f"failed to find yosys {r}"
    btor_name = filename.stem + ".btor"
    conversion = _minimal_btor_conversion
    read_cmd = [f"read_verilog {filename.name}"] + [f"read_verilog {src.resolve()}" for src in additional_sources]
    if top is not None:
        read_cmd += [f"prep -top {top}"]
    yosys_cmd = read_cmd + conversion + [f"write_btor -x {btor_name}"]
    cmd = ["yosys", "-p", " ; ".join(yosys_cmd)]
    cmd_str = ' '.join(str(p) for p in cmd) # for debugging
    subprocess.run(cmd, check=True, cwd=cwd, stdout=subprocess.PIPE)
    assert (cwd / btor_name).exists()
    return cwd / btor_name


class Synthesizer:
    """ generates assignments to synthesis variables which fix the design according to a provided testbench """
    def __init__(self):
        pass

    def run(self, name: str, working_dir: Path, ast: vast.Source, testbench: Path, solver: str, init: str,
            incremental: bool, additional_sources: list, top: str, include: Path) -> dict:
        synth_filename = working_dir / name
        ast = _remove_async_reset(ast)
        with open(synth_filename, "w") as f:
            f.write(serialize(ast))

        # convert file and run synthesizer
        btor_filename = _to_btor(synth_filename, additional_sources, top)
        result = _run_synthesizer(btor_filename, testbench, solver, init, incremental)
        status = result["status"]
        with open(working_dir / "status", "w") as f:
            f.write(status + "\n")

        return result


def _remove_async_reset(ast: vast.Source) -> vast.Source:
    """ We need to turn asynchronous resets into synchronous resets in order to be able
        to synthesize our repair templates with yosys.
        This is OK since we need to make this change anyways (with the asyn2sync command).
        This function makes a copy of the AST and then analyzes all processes to find synchronous processes,
        distinguish between clock and reset (the clock is never used in the process) and then remove the
        reset from the sensitivity list.
        Example: always@(posedge clk or negedge rst) --> always@(posedge clk)
    """
    ast = copy.deepcopy(ast)
    phase1 = SyncReset()
    phase1.run(ast)
    phase2 = SyncResetMux(phase1.registers)
    phase2.run(ast)
    return ast


class SyncResetMux(AstVisitor):
    """ adds a mux to all r-value uses of a register with asynchronous reset """
    def __init__(self, registers: dict):
        super().__init__()
        self.registers = registers


    def run(self, ast: vast.Source):
        self.visit(ast)


    def visit_Lvalue(self, node: vast.Lvalue):
        """ ignore all l-values """
        return node

    def visit_Identifier(self, node: vast.Identifier):
        if node.name not in self.registers:
            return node
        # add mux
        (init_expr, reset_name, high_active) = self.registers[node.name]
        reset_expr = vast.Identifier(reset_name)
        if not high_active:
            reset_expr = vast.Ulnot(reset_expr)
        return vast.Cond(reset_expr, init_expr, node)


class SyncReset(AstVisitor):
    """ identifies all registers with asynchronous reset and removes the asynchronous reset from the sensitivity list """
    def __init__(self):
        super().__init__()
        self.registers = {}


    def run(self, ast: vast.Source):
        self.registers = {}
        self.visit(ast)


    def visit_Always(self, node: vast.Always):
        # check to see if there are exactly two posedge / negedge arguments in the sensitivity list
        types = { e.type for e in node.sens_list.list }
        is_edge_sensitive = 'posedge' in types or 'negedge' in types
        if not is_edge_sensitive or len(node.sens_list.list) < 2:
            return node

        # we have 2+ edge sensitive signals and need to determine which one is a reset and which one is a clock
        names = {e.sig.name for e in node.sens_list.list}
        assert len(names) == 2
        finder = ResetProcessAnalyzer(names)
        finder.visit(node.statement)
        assert finder.reset is not None, "failed to identify reset!"
        self.registers.update(finder.registers)

        # update sense list
        node.sens_list.list = [e for e in node.sens_list.list if e.sig.name != finder.reset]

        return node



class ResetProcessAnalyzer(AstVisitor):
    """ determines the reset signal name (from the sens list candidates) + registers and their reset values """
    def __init__(self, reset_candidates: set):
        super().__init__()
        self.candidates = reset_candidates
        self.reset = None
        self.high_active = True
        self.registers = {}

    def _is_reset_expr(self, node):
        if isinstance(node, vast.Identifier) and node.name in self.candidates:
            return node.name, True
        if isinstance(node, vast.Ulnot) or isinstance(node, vast.Unot):
            (name, high_active) = self._is_reset_expr(node.right)
            if name is not None:
                return name, not high_active
        return None, None

    def visit_IfStatement(self, node: vast.IfStatement):
        # check to see if this might be the reset if statement
        (name, high_active) = self._is_reset_expr(node.cond)
        if name is None:
            # we skip this block if the condition it is not a reset expression
            return
        if self.reset is not None:
            assert self.reset == name
            assert self.high_active == high_active
        else:
            self.reset = name
            self.high_active = high_active
        # visit reset block
        self.visit(node.true_statement)

    def visit_NonblockingSubstitution(self, node: vast.NonblockingSubstitution):
        """ this should only be visited in the context of a just discovered reset branch """
        reg_name = node.left.var.name
        init_value = node.right
        assert reg_name not in self.registers
        self.registers[reg_name] = (copy.deepcopy(init_value), self.reset, self.high_active)

