# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import os
import shutil
import re
from dataclasses import dataclass
from pathlib import Path
import subprocess

from rtlfix import parse_verilog, serialize
from rtlfix.visitor import AstVisitor
import pyverilog.vparser.ast as vast


def preprocess(filename: Path, working_dir: Path) -> Path:
    """ runs a linter on the verilog file and tries to address some issues """
    # create directory
    assert working_dir.exists()
    preprocess_dir = working_dir / "0_preprocess"
    if preprocess_dir.exists():
        shutil.rmtree(preprocess_dir)
    os.mkdir(preprocess_dir)

    # run linter up to two times
    for ii in range(2):
        warnings = run_linter(filename, preprocess_dir)

        if len(warnings) == 0:
            return filename  # no warnings -> nothing to fix

        # parse ast and fix if necessary
        fixed_filename = preprocess_dir / f"{filename.stem}.{ii}.v"
        ast = parse_verilog(filename)
        fixer = LintFixer(warnings)
        fixer.apply(ast)
        with open(fixed_filename, "w") as f:
            f.write(serialize(ast))
        filename = fixed_filename

    # return path to preprocessed file
    return filename


def _check_for_verilator():
    r = subprocess.run(["verilator", "-version"], stdout=subprocess.PIPE)
    assert r.returncode == 0, "failed to find verilator"


_verilator_lint_flags = ["--lint-only", "-Wno-fatal", "-Wall", "-Wno-style"]
_verilator_re = re.compile(r"%Warning-([A-Z]+): ([^:]+):(\d+):(\d+):([^\n]+)")


def remove_blank_lines(lines: list) -> list:
    return [ll.strip() for ll in lines if len(ll.strip()) > 0]


@dataclass
class LintWarning:
    tpe: str
    filename: str
    line: int
    col: int
    msg: str


def parse_linter_output(lines: list) -> list:
    out = []
    for line in lines:
        m = _verilator_re.search(line)
        if m is not None:
            (tpe, filename, line, col, msg) = m.groups()
            out.append(LintWarning(tpe, filename, int(line), int(col), msg.strip()))
        elif len(out) > 0:
            out[0].msg += "\n" + line
    return out


def run_linter(filename: Path, preprocess_dir: Path) -> list:
    """ Things we are interested in:
        - ASSIGNDLY: Unsupported: Ignoring timing control on this assignment
        - CASEINCOMPLETE: Case values incompletely covered (example pattern 0x5)
          - we might need to fix this to get the actual latch warning from verilator...
        - BLKSEQ: Blocking assignment '=' in sequential logic process
        - LATCH: Latch inferred for signal 'fsm_full.next_state'
                 (not all control paths of combinational always assign a value)
        - BLKANDNBLK: Unsupported: Blocked and non-blocking assignments to same variable: 'fsm_full.state'
    """
    _check_for_verilator()
    r = subprocess.run(["verilator"] + _verilator_lint_flags + [str(filename.resolve())],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info = (r.stdout + r.stderr).decode('utf-8').splitlines()
    info = remove_blank_lines(info)
    if len(info) == 0:
        return []
    # output raw info
    with open(preprocess_dir / "linter.txt", "w") as f:
        f.write("\n".join(info) + "\n")
    # parse
    return parse_linter_output(info)


_fix_warnings = {"ASSIGNDLY", "CASEINCOMPLETE", "BLKSEQ", "LATCH"}


def filter_warnings(warnings: list) -> list:
    out = []
    for warn in warnings:
        if warn.tpe in _fix_warnings:
            out.append(warn)
        else:
            raise RuntimeWarning(f"Unknown warning type: {warn}")
    return out


_latch_re = re.compile(r"Latch inferred for signal '([^']+)'")


def assign_latch_signal(latch_warning: LintWarning):
    m = _latch_re.search(latch_warning.msg)
    assert m is not None, latch_warning.msg
    signal_parts = m.group(1).split(".")
    ident = vast.Identifier(signal_parts[-1].strip())
    return vast.BlockingSubstitution(vast.Lvalue(ident), vast.Rvalue(vast.IntConst("'d0")))


def ensure_block(stmt: vast.Node) -> vast.Block:
    if isinstance(stmt, vast.Block):
        return stmt
    return vast.Block(tuple([stmt]))


class LintFixer(AstVisitor):
    """ This class addressed the following lint warning:
        - ASSIGNDLY: Unsupported: Ignoring timing control on this assignment
        - CASEINCOMPLETE: Case values incompletely covered (example pattern 0x5)
        - BLKSEQ: Blocking assignment '=' in sequential logic process
    """

    def __init__(self, warnings: list):
        super().__init__()
        self.warnings = filter_warnings(warnings)

    def _find_warnings(self, tpe: str, line: int):
        out = []
        for warn in self.warnings:
            if warn.tpe == tpe and warn.line == line:
                out.append(warn)
        return out

    def apply(self, ast: vast.Source):
        return self.visit(ast)

    def visit_CaseStatement(self, node: vast.CaseStatement):
        node = self.generic_visit(node)
        # add empty default case to fix incomplete cases (this will reveal LATCH warnings in verilator)
        if len(self._find_warnings("CASEINCOMPLETE", node.lineno)) > 0:
            default = vast.Case(None, vast.Block(tuple([])))
            node.caselist = tuple(list(node.caselist) + [default])
        return node

    def visit_Always(self, node: vast.Always):
        node = self.generic_visit(node)
        # add a default assignment if a latch is unintentionally created
        latches = self._find_warnings("LATCH", node.lineno)
        if len(latches) == 0:
            return node
        assignments = [assign_latch_signal(ll) for ll in latches]
        stmt = ensure_block(node.statement)
        stmt.statements = tuple(assignments + list(stmt.statements))
        node.statement = stmt
        return node
