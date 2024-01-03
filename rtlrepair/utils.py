# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>


from pathlib import Path
from enum import Enum, unique
import pyverilog.vparser.ast as vast
from pyverilog.utils.identifiervisitor import getIdentifiers
from pyverilog.vparser.parser import parse
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

_script_dir = Path(__file__).parent.resolve()
_root_dir = _script_dir.parent.resolve()
_parser_tmp_dir = _root_dir / ".pyverilog"

@unique
class Status(Enum):
    NoRepair = 'no-repair'
    CannotRepair = 'cannot-repair'
    Success = 'success'
    Timeout = 'timeout'

status_name_to_enum = {e.value: e for e in Status}


def parse_verilog(filename: Path, include: Path = None) -> vast.Source:
    assert filename.exists(), f"cannot parse {filename}, does not exist"
    include = [] if include is None else [str(include.resolve())]
    ast, directives = parse([filename],
                            preprocess_include=include,
                            preprocess_define=[])
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


def ensure_block(stmt: vast.Node, blockify_tracker_list: list = None) -> vast.Block:
    if isinstance(stmt, vast.Block):
        return stmt
    else:
        new_block = vast.Block(tuple([stmt]))
        if blockify_tracker_list is not None:
            blockify_tracker_list.append(id(new_block))
        return new_block


_bases = {'b': 2, 'o': 8, 'h': 16, 'd': 10}


def parse_verilog_int_literal(value: str) -> (int, int):
    assert 'x' not in value, f"values containing 'x' like: {value} are not supported!"
    width = None
    if "'" in value:
        parts = value.split("'")
        if len(parts[0].strip()) > 0:
            width = int(parts[0])
        prefix = parts[1][0]
        if prefix in _bases:
            value = int(parts[1][1:], _bases[prefix])
        else:
            value = int(parts[1])
        return value, width
    else:
        value = int(value)
        return value, width
