# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# contains code to save and load benchmark results in a unified format

import subprocess
import tomli
from dataclasses import dataclass, field
from pathlib import Path
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
from pyverilog.vparser.parser import parse
from benchmarks import Benchmark, assert_file_exists, assert_dir_exists, parse_path


@dataclass
class Repair:
    filename: Path
    diff: Path = None
    manual: Path = None  # manually ported patch
    meta: dict = field(default_factory=dict)


@dataclass
class Result:
    name: str
    tool: str
    project_name: str
    bug_name: str
    success: bool
    seconds: float
    buggy: Path = None
    original: Path = None
    repairs: list[Repair] = field(default_factory=list)
    custom: dict = field(default_factory=dict)


def collect_repair_meta(dd: dict) -> dict:
    return {k: v for k, v in dd.items() if k not in {'name', 'diff', 'manual'}}


def load_result(filename: Path, name: str = None) -> Result:
    assert_file_exists("result file", filename)
    with open(filename, 'rb') as ff:
        dd = tomli.load(ff)
    base_dir = filename.parent
    assert_dir_exists("base dir", base_dir)

    if 'repairs' not in dd: dd['repairs'] = []
    repairs = [Repair(
        filename=parse_path(rr['name'], base_dir, must_exist=True),
        diff=parse_path(rr['diff'], base_dir, must_exist=True) if 'diff' in rr else None,
        manual=parse_path(rr['manual'], base_dir, must_exist=True) if 'manual' in rr else None,
        meta=collect_repair_meta(rr),
    ) for rr in dd['repairs']]

    res = dd['result']
    # default name
    if name is None:
        name = f"{res['tool']}.{res['project']}.{res['bug']}"
    result = Result(
        name=name,
        tool=res['tool'],
        project_name=res['project'],
        bug_name=res['bug'],
        success=res['success'],
        seconds=res['seconds'],
        buggy=parse_path(res['buggy'], base_dir, must_exist=True) if 'buggy' in res else None,
        original=parse_path(res['original'], base_dir, must_exist=True) if 'original' in res else None,
        repairs=repairs,
        custom=dd['custom'] if 'custom' in dd else {},
    )
    return result


def write_result(working_dir: Path, benchmark: Benchmark, success: bool, repaired: list, seconds: float, tool_name: str,
                 custom: dict = None):
    """ Writes the results to the working directory. """
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
        if success: assert len(repaired) > 0, f"Successful, but a repair is missing!"
        for rep_info in repaired:
            print("\n[[repairs]]", file=ff)
            if isinstance(rep_info, Path):
                rep_file, meta_data = rep_info, None
            else:
                rep_file, meta_data = rep_info
            print_filename("name", rep_file)
            if buggy.exists():
                repair_diff = working_dir / f"{rep_file.stem}.diff.txt"
                do_diff(buggy, rep_file, repair_diff)
                print_filename("diff", repair_diff)
            if meta_data:
                print("# tool specific meta-data", file=ff)
                _print_custom_key_values(meta_data, ff)

        if custom is not None and len(custom) > 0:
            print("\n[custom]", file=ff)
            _print_custom_key_values(custom, ff)


def _print_custom_key_values(cc: dict, ff):
    for kk, vv in cc.items():
        print(f'{kk}={_to_toml_str(vv)}', file=ff)


def _to_toml_str(value) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, float):
        return str(value)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_to_toml_str(ii) for ii in value) + "]"
    # turn into string by default
    return f'"{value}"'
    # raise NotImplementedError(f"Unsupported type: {type(value)} ({value})")


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
