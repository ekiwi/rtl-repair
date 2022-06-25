# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


from pathlib import Path
import pyverilog.vparser.ast as vast
from pyverilog.utils.identifiervisitor import getIdentifiers
from pyverilog.vparser.parser import parse
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

_script_dir = Path(__file__).parent.resolve()
_root_dir = _script_dir.parent.resolve()
_parser_tmp_dir = _root_dir / ".pyverilog"


def parse_verilog(filename: Path) -> vast.Source:
    ast, directives = parse([filename],
                            preprocess_include=[],
                            preprocess_define=[],
                            outputdir=".",
                            debug=True)
    return ast


# shared global codegen, no reason to construct this anew every time
_codegen = ASTCodeGenerator()


def serialize(ast) -> str:
    if ast is None:
        return "None"
    source = _codegen.visit(ast)
    return source


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


def parse_width(width) -> int:
    if width is None:
        return 1
    assert isinstance(width, vast.Width)
    msb = int(width.msb.value)
    lsb = int(width.lsb.value)
    assert msb >= lsb
    return msb - lsb + 1


def ensure_block(stmt: vast.Node) -> vast.Block:
    if isinstance(stmt, vast.Block):
        return stmt
    return vast.Block(tuple([stmt]))
