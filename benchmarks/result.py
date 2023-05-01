# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# contains code to save and load benchmark results in a unified format

import subprocess
from dataclasses import dataclass
from pathlib import Path
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
from pyverilog.vparser.parser import parse
from benchmarks import Benchmark, assert_file_exists, assert_dir_exists


@dataclass
class Result:
    project_name: str
    bug_name: str
    success: bool
    seconds: float


def write_results(working_dir: Path, benchmark: Benchmark, success: bool, repaired: Path, seconds: float, tool_name: str, custom: dict):
    """ Writes the results to the working directory. """
    if success:
        assert_file_exists("repaired Verilog file", repaired)

    with open(working_dir / "result.toml", 'w') as ff:
        print("[result]", file=ff)
        print(f'tool="{tool_name}"', file=ff)
        print(f'project="{benchmark.project_name}"', file=ff)
        print(f'bug="{benchmark.bug.name}"', file=ff)
        print(f'success={str(success).lower()}', file=ff)
        print(f'seconds={seconds}', file=ff)

        # print file names relative to the working dir
        def print_filename(key: str, filename: Path):
            print(f'{key}="{filename.relative_to(working_dir)}"', file=ff)


        # these files should have been created by the `create_buggy_and_original_diff` function
        original = working_dir / benchmark.bug.original.name if benchmark.bug.original else None
        buggy = working_dir / benchmark.bug.buggy.name
        if buggy.exists():
            print_filename("buggy", buggy)
        if original and original.exists():
            print_filename("original", original)

        # do we have a repaired file?
        if success:
            print_filename("repaired", repaired)
            if original and original.exists():
                repair_diff = working_dir / "repair_diff.txt"
                do_diff(original, repaired, repair_diff)
                print_filename("repair", repair_diff)

        if custom is not None and len(custom) > 0:
            print("\n[custom]", file=ff)
            for key, value in custom.items():
                print(f'{key}={_to_toml_str(value)}', file=ff)

def _to_toml_str(value) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, float):
        return str(value)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    # turn into string by default
    return f'"{value}"'
    #raise NotImplementedError(f"Unsupported type: {type(value)} ({value})")

def create_buggy_and_original_diff(working_dir: Path, benchmark: Benchmark):
    """
        - copies the buggy file to the working directory with the Verilog reformatted with PyVerilog
        - if the original file (i.e. the ground truth) is available, that is copies as well with PyVerilog formatting,
          and we also create a bug diff between the two files
    """
    assert_file_exists("buggy file", benchmark.bug.buggy)
    assert_dir_exists("working dir", working_dir)
    buggy_copy = working_dir / benchmark.bug.buggy.name
    parse_and_serialize_to(benchmark.bug.buggy, buggy_copy, include=[benchmark.design.directory])

    if benchmark.bug.original and benchmark.bug.original.exists():
        original_copy = working_dir / benchmark.bug.original.name

        parse_and_serialize_to(benchmark.bug.original, original_copy, include=[benchmark.design.directory])
        bug_diff = working_dir / "bug_diff.txt"
        do_diff(original_copy, buggy_copy, bug_diff)


_codegen = ASTCodeGenerator()

def parse_and_serialize_to(src: Path, dst: Path, include=None, define=None):
    """ Makes a "copy" of the source file by parsing it with PyVerilog and serializing the AST to the destination file """
    assert_file_exists("Verilog source", src)
    ast, _ = parse([src], preprocess_include=include, preprocess_define=define)
    with open(dst, 'w') as ff:
        ff.write(_codegen.visit(ast))

def do_diff(file_a: Path, file_b: Path, output_file: Path):
    """ Calls the `diff` tool to compare two files and writes the result to a third file. """
    cmd = "diff"
    r = subprocess.run(["which", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode == 0:
        with open(output_file, 'wb') as f:
            subprocess.run(["diff", str(file_a.resolve()), str(file_b.resolve())], stdout=f)