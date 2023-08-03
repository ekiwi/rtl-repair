#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# creates the tables for the evaluation section of the RTL-Repair paper

import sys
import argparse
import tomli
from pathlib import Path
from dataclasses import dataclass

from benchmarks.result import load_result

# add root dir in order to be able to load "benchmarks" module
_script_dir = Path(__file__).parent.resolve()
sys.path.append(str(_script_dir.parent))
import benchmarks
from benchmarks import assert_file_exists, assert_dir_exists

# map benchmark to short name
project_short_names = {
    "decoder_3_to_8": "decoder",
    "first_counter_overflow": "counter",
    "flip_flop": "flop",
    "fsm_full": "fsm",
    "lshift_reg": "shift",
    "mux_4_1": "mux",
    "i2c_slave": "i2c",
    "i2c_master": "i2c",
    "sha3_keccak": "sha3",
    "sha3_padder": "sha3",
    "pairing": "pairing",
    "reed_solomon_decoder": "reed",
    "sdram_controller": "sdram",
}
to_short_name = {}
def _calc_short_names():
    for project_name, entry in benchmarks.benchmark_to_cirfix_paper_table_3.items():
        to_short_name[project_name] = {}
        short = project_short_names[project_name]
        for bug in entry.keys():
            to_short_name[project_name][bug] = short + "_" + bug[0].lower() + bug[-1].lower()
_calc_short_names()
def get_short_name(project: str, bug: str):
    return to_short_name[project][bug]
all_short_names = [name for entry in to_short_name.values() for name in entry.values()]

@dataclass
class Config:
    working_dir: Path
    osdd_toml: Path
    baseline_toml: Path
    cirfix_result_dir: Path
    rtlrepair_result_dir: Path


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Generate tables for the RTL-Repair paper')
    parser.add_argument('--working-dir', help='Output directory.', required=True)
    parser.add_argument('--osdd-toml', help='Path to osdd.toml generated by calc_osdd.py.', required=True)
    parser.add_argument('--baseline-toml', help='Path to baseline_results.toml generated by generate_vcd_traces.py.', required=True)
    parser.add_argument('--cirfix-result-dir',
                        help='Path to the directory generated by check_repairs.py.', required=True)
    parser.add_argument('--rtlrepair-result-dir',
                        help='Path to the directory generated by check_repairs.py.', required=True)



    args = parser.parse_args()
    conf = Config(Path(args.working_dir), Path(args.osdd_toml), Path(args.baseline_toml),
                  Path(args.cirfix_result_dir), Path(args.rtlrepair_result_dir))

    assert_dir_exists("working directory parent", conf.working_dir.parent)
    assert_file_exists("osdd toml", conf.osdd_toml)
    assert_file_exists("baseline results toml", conf.baseline_toml)
    assert_dir_exists("cirfix result directory", conf.cirfix_result_dir)
    assert_dir_exists("rtl-repair result directory", conf.rtlrepair_result_dir)
    return conf

def _render_latex_row(column_width: list[int], row: list[str], is_last: bool, right_cols_to_comment: int, separator: str = "\\\\") -> str:
    padded = [cell.ljust(width, ' ') for width, cell in zip(column_width, row)]
    content = padded if right_cols_to_comment == 0 else padded[0:-right_cols_to_comment]
    comments = [] if right_cols_to_comment == 0 else padded[-right_cols_to_comment:]
    comment_sep = "" if len(comments) == 0 else "  % "
    line = " & ".join(content) + " " + separator + comment_sep + " & ".join(comments)
    return line

NoRepair = "○"
Success  = "✔"
Fail     = "✖"

def _fontspec(character: str) -> str:
    code = f"{ord(character):x}".upper()
    return '{\\fontspec{Symbola}\\symbol{"' + code + '}}'

EmojiMapping = {
    "○": _fontspec("○"),
    "✔": _fontspec("✔"),
    "✖": _fontspec("✖"),
}

def _latex_escape(cell: str) -> str:
    for e, r in EmojiMapping.items():
        cell = cell.replace(e, r)
    cell = cell.replace('_', '\\_')
    return cell

def render_latex(table: list[list[str]], has_header: bool, right_cols_to_comment: int = 0) -> str:
    if len(table) == 0:
        return ""
    column_count = len(table[0])
    assert column_count > right_cols_to_comment >= 0

    # stringify and escape all cells
    table = [[_latex_escape(str(cell)) for cell in row] for row in table]

    # determine number and size of columns
    column_width = [0] * column_count
    for row in table:
        assert len(row) == len(column_width),\
        f"Expected all rows to have {len(column_width)} columns, but this one has {len(row)}"
        for ii, cell in enumerate(row):
            column_width[ii] = max(column_width[ii], len(cell))

    if has_header:
        header = table[0]
        table = table[1:]

    last_col_ii = column_count - 1
    rows = [_render_latex_row(column_width, row, (ii==last_col_ii), right_cols_to_comment)
            for ii, row in enumerate(table)]
    table_str = "\n".join(rows) + "\n"

    if has_header:
        table_str = _render_latex_row(column_width, header, len(rows) == 0, right_cols_to_comment, separator="\\\\ \\midrule") + "\n" + table_str

    # add tabular environment
    start_tab = "\\begin{tabular}{" + ''.join('r' * len(column_width)) +"}"
    end_tab = "\\end{tabular}"
    table_str = start_tab + "\n" + table_str + end_tab + "\n"

    return table_str


def write_to(filename: Path, content: str):
    with open(filename, 'w') as ff:
        ff.write(content)


def benchmark_description_table(conf: Config) -> list[list[str]]:
    header = ["Project", "Defect", "Short Name"]
    rows = [header]
    for project_name, entry in benchmarks.benchmark_to_cirfix_paper_table_3.items():
        for bug, (description, _category, _time, _status) in entry.items():
            row = [project_name, description, get_short_name(project_name, bug)]
            rows.append(row)
    return rows

def load_toml(filename: Path) -> dict:
    with open(filename, 'rb') as ff:
        return tomli.load(ff)

def _combine_values(kind: str, preferred: int, other: int):
    if preferred == -1:
        return other
    if other != -1 and preferred != other:
        print(f"Disagreement on {kind}: {preferred} =/= {other}")
    return preferred

def osdd_table(conf: Config, results: dict) -> list[list[str]]:
    header = ["Benchmark", "Testbench Cycles", "First Output Div.", "OSDD", "Repair Window", "RTL-Repair", "CirFix", "Note"]
    def num_to_str(num: int) -> str:
        return "" if num < 0 else str(num)

    osdds = load_toml(conf.osdd_toml)['osdds']

    rows = []
    for osdd in osdds:
        name = get_short_name(osdd['project'], osdd['bug'])
        cycles_from_osdd = osdd['ground_truth_testbench_cycles']
        cycles_from_oracle = results[name]['tb_cycles'] if 'tb_cycles' in results[name] else -1
        cycles = _combine_values(f"testbench cycles for {name}", cycles_from_osdd, cycles_from_oracle)
        fail_at_from_osdd = osdd['first_output_disagreement']
        fail_at_from_oracle = results[name]['tb_fail_at'] if 'tb_fail_at' in results[name] else -1
        fail_at = _combine_values(f"fail at for {name}", fail_at_from_osdd, fail_at_from_oracle)
        delta = num_to_str(osdd['delta'])
        repairs = results[name][RtlRepair]['repairs']
        if len(repairs) > 0 and 'past_k' in repairs[0] and repairs[0]['past_k'] >= 0:
            rtl_repair_data = repairs[0]
            window_start = "0" if rtl_repair_data['past_k'] == 0 else str(-rtl_repair_data['past_k'])
            window = f"[{window_start} .. {rtl_repair_data['future_k']}]"
        else:
            window = ""
        rtl_repair_success = results[name][RtlRepair]['success']
        cirfix_success = results[name][CirFix]['success']
        note = osdd['notes']
        rows.append([name, num_to_str(cycles), num_to_str(fail_at), delta, window, rtl_repair_success, cirfix_success, note])

    sorted_rows = sort_rows_by_benchmark_column(f"{conf.osdd_toml}", rows)
    return [header] + sorted_rows

def sort_rows_by_benchmark_column(what: str, rows: list[list[str]]) -> list[list[str]]:
    """ assumes that the header is excluded and the benchmark names are all in the left most column """
    by_name = {r[0]: r for r in rows}
    # make sure we always use the same order of benchmarks!
    sorted_rows = [by_name[name] for name in all_short_names if name in by_name]
    missing_benchmarks = [name for name in all_short_names if not name in by_name]
    if len(missing_benchmarks) > 0:
        print(f"WARN: {what} did not contain an entry for {missing_benchmarks}")
    return sorted_rows

def multicol(num: int, value: str) -> str:
    return "\multirow[t]{" + str(num) + "}{*}{" + value + "}"

def check_to_emoji(checked_repairs: list, check_name: str) -> str:
    assert check_name in Checks
    res = [r[check_name] for r in checked_repairs]
    all_pass = all(r == 'pass' for r in res)
    all_fail = all(r == 'fail' for r in res)
    only_pass_fail = all(r == 'fail' or r == 'pass' for r in res)
    at_least_once_pass = 'pass' in res
    if not only_pass_fail:
        assert not at_least_once_pass, f"Check {check_name} was not available for one repair but passed for the other {res}"
        return ""
    # for one benchmark, CirFix provides a solution that fails, but passes after minimization
    return Success if at_least_once_pass else Fail

def correctness_table(results: dict) -> list[list[str]]:
    header = ["Benchmark", "Tool", "Tool Status", "Sim", "CirFix Author", "Gate-Level", "iVerilog", "Extended", "Overall"]
    rows = []
    skipped = []
    for name in all_short_names:
        # we skip benchmarks were neither of the tools offered a solution
        cirfix_tool_success = 'result' in results[name][CirFix] and results[name][CirFix]['result']['success']
        rtlrepair_tool_success = 'result' in results[name][RtlRepair] and results[name][RtlRepair]['result']['success']
        if not cirfix_tool_success and not rtlrepair_tool_success:
            skipped += [name]
            continue

        benchmark = multicol(2, name)
        for tool in [RtlRepair, CirFix]:
            tool_res = results[name][tool]
            row = [benchmark, tool]
            benchmark = ""

            # tool status: does the tool think that it provided a correct repair?
            tool_success = 'result' in tool_res and tool_res['result']['success']
            row += [Success if tool_success else NoRepair]

            # if the tool has no solution, we skip all checks
            if not tool_success:
                row += [""] * 5
            else:
                checked_repairs = results[name][tool]['checks']
                row += [check_to_emoji(checked_repairs, 'rtl-sim')]
                if tool == CirFix:
                    row += [check_to_emoji(checked_repairs, 'cirfix-author')]
                else:
                    row += [""]
                for check_name in ['gate-sim', 'iverilog-sim', 'extended-sim']:
                    row += [check_to_emoji(checked_repairs, check_name)]
            row += [tool_res['success']]


            rows.append(row)

    print(f"Correctness: skipped {skipped} benchmarks for which neither tool had a solution.")


    return [header] + rows


CirFix = 'cirfix'
RtlRepair = 'rtlrepair'




Checks = ['cirfix-tool', 'cirfix-author', 'rtl-sim', 'gate-sim', 'extended-sim', 'iverilog-sim']
def _summarize_checks(checks: dict, cirfix: bool) -> bool:
    # skip cirfix specific checks for rtl repair
    considered_checks = Checks if cirfix else Checks[2:]
    status = [checks[cc] for cc in considered_checks]
    for s in status:
        assert s in {'pass', 'fail', 'na', 'indeterminate'}
    fails = [s == 'fail' for s in status]
    return not True in fails


def create_repair_summary(results):
    """ analyzes the results of our check_repair.py script to come up with an overall assessment """
    for name in all_short_names:
        for tool in [CirFix, RtlRepair]:
            tool_res = results[name][tool]
            # i.e. does the tool think it created a correct repair?
            tool_success = 'result' in tool_res and tool_res['result']['success']
            if not tool_success:
                results[name][tool]['success'] = NoRepair
            else:
                checked_repairs = results[name][tool]['checks']
                # we are happy if any of the repairs pass (in one case a CirFix repair only passes in its minimized form)
                check_successes = [_summarize_checks(cc, tool == CirFix) for cc in checked_repairs]
                check_success = True in check_successes
                results[name][tool]['success'] = Success if check_success else Fail



def _try_load_one_result(directory: Path, tool: str, results: dict) -> bool:
    check_toml = directory / "check.toml"
    result_toml = directory / "result.toml"
    if not check_toml.exists() or not result_toml.exists():
        return False
    dd = load_toml(result_toml)
    res, custom = dd['result'], dd['custom']
    benchmark_name = get_short_name(res['project'], res['bug'])
    repairs = dd['repairs'] if 'repairs' in dd else []
    dd = load_toml(check_toml)
    checks = dd['checks'] if 'checks' in dd else []
    results[benchmark_name][tool]['result'] = res
    results[benchmark_name][tool]['repairs'] = repairs
    results[benchmark_name][tool]['custom'] = custom
    results[benchmark_name][tool]['checks'] = checks



def _load_results(directory: Path, tool: str, results: dict):
    found_result = _try_load_one_result(directory, tool, results)
    if not found_result:
        for filename in directory.iterdir():
            if filename.is_dir():
                _load_results(filename, tool, results)

def _load_baseline_results(baseline_toml: Path, results: dict):
    dd = load_toml(baseline_toml)
    for res in dd['results']:
        name = get_short_name(res['project'], res['bug'])
        results[name]['tb_cycles'] = res['cycles']
        results[name]['tb_fail_at'] = res['failed_at']


def load_results(conf: Config) -> dict:
    results = {}
    for name in all_short_names:
        results[name] = {CirFix: {}, RtlRepair: {}}
    _load_results(conf.cirfix_result_dir, CirFix, results)
    _load_results(conf.rtlrepair_result_dir, RtlRepair, results)
    _load_baseline_results(conf.baseline_toml, results)
    create_repair_summary(results)
    return results

def main():
    conf = parse_args()

    # create working directory if it does not exist already
    if not conf.working_dir.exists():
        conf.working_dir.mkdir()

    results = load_results(conf)

    write_to(conf.working_dir / "benchmark_description_table.tex",
             render_latex(benchmark_description_table(conf), has_header=True))

    write_to(conf.working_dir / "osdd_table.tex",
             render_latex(osdd_table(conf, results), has_header=True, right_cols_to_comment=1))

    write_to(conf.working_dir / "correctness_table.tex",
             render_latex(correctness_table(results), has_header=True))



if __name__ == '__main__':
    main()
