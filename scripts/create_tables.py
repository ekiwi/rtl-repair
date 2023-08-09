#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# creates the tables for the evaluation section of the RTL-Repair paper
import json
import math
import sys
import argparse
from typing import Optional

import tomli
import statistics as py_stats
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
    rtlrepair_all_templates_result_dir: Path
    rtlrepair_basic_synth_result_dir: Path


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Generate tables for the RTL-Repair paper')
    parser.add_argument('--working-dir', help='Output directory.', required=True)
    parser.add_argument('--osdd-toml', help='Path to osdd.toml generated by calc_osdd.py.', required=True)
    parser.add_argument('--baseline-toml', help='Path to baseline_results.toml generated by generate_vcd_traces.py.', required=True)
    parser.add_argument('--cirfix-result-dir',
                        help='Path to the directory generated by check_repairs.py.', required=True)
    parser.add_argument('--rtlrepair-result-dir',
                        help='Path to the directory generated by check_repairs.py.', required=True)
    parser.add_argument('--rtlrepair-all-templates-result-dir',
                        help='Path to the directory generated by check_repairs.py.', required=True)
    parser.add_argument('--rtlrepair-basic-synth-result-dir',
                        help='Path to the directory generated by check_repairs.py.', required=True)



    args = parser.parse_args()
    conf = Config(Path(args.working_dir), Path(args.osdd_toml), Path(args.baseline_toml),
                  Path(args.cirfix_result_dir), Path(args.rtlrepair_result_dir),
                  Path(args.rtlrepair_all_templates_result_dir), Path(args.rtlrepair_basic_synth_result_dir))

    assert_dir_exists("working directory parent", conf.working_dir.parent)
    assert_file_exists("osdd toml", conf.osdd_toml)
    assert_file_exists("baseline results toml", conf.baseline_toml)
    assert_dir_exists("cirfix result directory", conf.cirfix_result_dir)
    assert_dir_exists("rtl-repair result directory", conf.rtlrepair_result_dir)
    assert_dir_exists("rtl-repair all-templates result directory", conf.rtlrepair_all_templates_result_dir)
    assert_dir_exists("rtl-repair basic-synth result directory", conf.rtlrepair_basic_synth_result_dir)
    return conf

_MultiColStart = '\\multicolumn{'
def _analyze_multicol(cell: str) -> (Optional[int], str):
    stripped = cell.strip()
    has_multicol = stripped.startswith(_MultiColStart)
    if has_multicol:
        multicols = int(stripped[len(_MultiColStart):].split('}')[0])
        content = ''.join((''.join(cell.split('{')[3:])).split('}')[:-1])
        return multicols, content
    else:
        return None, None

def _join_latex_cells(cells: list[str]) -> str:
    """" Takes multicolumn cells into account and connects them with a space instead of a & """
    out = ""
    multicols = 0
    last_ii = len(cells) - 1
    for ii, cell in enumerate(cells):
        is_last = ii == last_ii
        out += cell
        if not is_last:
            multicol_param, _ = _analyze_multicol(cell)
            if multicol_param is not None:
                assert multicols == 0
                multicols = multicol_param - 1
            if multicols > 0:
                out += "   "
                multicols -= 1
            else:
                out += " & "
    return out

def _render_latex_row(column_width: list[int], row: list[str], is_last: bool, right_cols_to_comment: int, separator: str = "\\\\") -> str:
    padded = [cell.ljust(width, ' ') for width, cell in zip(column_width, row)]
    content = padded if right_cols_to_comment == 0 else padded[0:-right_cols_to_comment]
    comments = [] if right_cols_to_comment == 0 else padded[-right_cols_to_comment:]
    comment_sep = "" if len(comments) == 0 else "  % "
    line = _join_latex_cells(content) + " " + separator + comment_sep + _join_latex_cells(comments)
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

def _rot_centered(cell: str) -> str:
    """ makes the cell multicolumn if it is not already """
    if len(cell.strip()) == 0:
        return "" # nothing to rotate
    columns, content = _analyze_multicol(cell)
    if columns is None:
        columns, content = 1, cell
    return "\\multicolumn{" + str(columns) + "}{c}{\\rot{" + content + "}}"

def render_latex(table: list[list[str]], has_header: bool, right_cols_to_comment: int = 0, rot_header: bool = False) -> str:
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
        f"Expected all rows to have {len(column_width)} columns, but this one has {len(row)}:\n{row}"
        for ii, cell in enumerate(row):
            column_width[ii] = max(column_width[ii], len(cell))

    if has_header:
        header = table[0]
        if rot_header:
            # rotate AND center
            header = [header[0]] + [_rot_centered(h) for h in header[1:]]
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

def multirow(num: int, value: str) -> str:
    return "\multirow[t]{" + str(num) + "}{*}{" + value + "}"

def multicol(num: int, value: str) -> list[str]:
    assert num >= 1, str(num)
    return ["\multicolumn{" + str(num) + "}{c}{" + value + "}"] + [""] * (num - 1)

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

        benchmark = multirow(2, name)
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

def format_time_s(time_in_s: float) -> str:
    hours: float = time_in_s / 60 / 60
    minutes: float = time_in_s / 60
    seconds: float = time_in_s
    if hours >= 1.0:
        msg = f"{hours:.2f}h"
    elif minutes >= 1.0:
        msg = f"{minutes:.2f}min"
    else:
        if seconds > 0 and round(seconds, 2) == 0:
            msg = "0.01s"
        else:
            msg = f"{seconds:.2f}s"
    return msg

CirFixTimeout = 16 * 60 * 60
def get_time(tool_res: dict) -> int:
    # TODO: include benchmarks that time out in cirfix experiment
    return tool_res['result']['seconds'] if 'result' in tool_res else CirFixTimeout


def simulate_combination(rtl_repair_time: float, rtl_repair_success: str, cirfix_time: float, cirfix_success: str) -> (float, str):
    """ This predicts what would happen if we ran RTL-Repair first and then CirFix """
    # if RTL-Repair found a repair, we go with it
    if rtl_repair_success != NoRepair:
        return rtl_repair_time, rtl_repair_success
    # otherwise we go with CirFix
    return rtl_repair_time + cirfix_time, cirfix_success

def performance_table(results: dict, statistics: dict) -> list[list[str]]:
    header = ["Benchmark", "RTL-Repair", "CirFix", "Speedup"]
    rows = []
    for tool in [CirFix, RtlRepair, Combined]:
        statistics[tool] = {Success:[], Fail:[], NoRepair:[]}

    for name in all_short_names:
        row = [name]
        res = results[name]

        rtl_repair_time = get_time(res[RtlRepair])
        rtl_repair_success = res[RtlRepair]['success']
        statistics[RtlRepair][rtl_repair_success] += [rtl_repair_time]
        row += [rtl_repair_success + " (" + format_time_s(rtl_repair_time) + ")"]

        cirfix_time = get_time(res[CirFix])
        cirfix_success = res[CirFix]['success']
        statistics[CirFix][cirfix_success] += [cirfix_time]
        row += [cirfix_success + " (" + format_time_s(cirfix_time) + ")"]

        combined_time, combined_success = simulate_combination(rtl_repair_time, rtl_repair_success, cirfix_time, cirfix_success)
        statistics[Combined][combined_success] += [combined_time]

        # conservative speedup
        speedup = f"{int(math.floor(cirfix_time / rtl_repair_time)):,}x"
        if rtl_repair_success == Success and cirfix_success == Success:
            speedup = "\\textbf{" + speedup + "}"
        row += [speedup]

        rows.append(row)
    return [header] + rows

_stat_foo = {
    'max': max,
    'min': min,
    'median': py_stats.median,
    'avg.': py_stats.mean, 'avg': py_stats.mean, 'mean': py_stats.mean,
}

def _perf_row(title: str, success: str, statistics: dict, tools: list[str], stats: list[str]) -> list[str]:
    row = [title]
    for tool in tools:
        st = statistics[tool][success]
        row += [str(len(st))]
        for stat in stats:
            row += [format_time_s(_stat_foo[stat](st))]
    return row

def performance_statistics_table(statistics: dict) ->  list[list[str]]:
    include_combined = False
    stats = ['median', 'max']
    pad = [""] * (len(stats))
    header1 = [""] + multicol(len(pad) + 1, "RTL-Repair") + multicol(len(pad) + 1,"CirFix")
    if include_combined:
        header1 += multicol(len(pad) + 1, "Combined")
        tools = [RtlRepair, CirFix, Combined]
    else:
        tools = [RtlRepair, CirFix]
    header2 = [""] + (["\\#"] + stats) * len(tools)
    return [header1, header2,
        _perf_row(Success + " Correct Repairs", Success, statistics, tools, stats),
        _perf_row(Fail + " Wrong Repairs", Fail, statistics, tools, stats),
        _perf_row(NoRepair + " Cannot Repair", NoRepair, statistics, tools, stats),
    ]


def ablation_table(results: dict) ->  list[list[str]]:
    header = ["Benchmark"]
    for e in ["Preprocessing", "Replace Literals", "Assign Constant", "Invert Condition", "Basic Synthesizer", "RTL-Repair", "CirFix"]:
        header += multicol(2, e)
    header += ["Speedup"]
    rows = []

    for name in all_short_names:
        row = [name]
        res = results[name]

        stats = res[RtlRepairAllTemplates]['statistics']
        rtl_repair_success = res[RtlRepair]['success']

        preproc_changes = stats['preprocess']['changes']
        preproc_time = stats['preprocess']['time']
        preproc_status = NoRepair if preproc_changes == 0 else Success
        replace_lit_status = stats['replace_literals']['status']
        row +=  [f"{preproc_changes}", f"{format_time_s(preproc_time)}"]
        fixed_by_preproc = preproc_status == Success and replace_lit_status == 'NoRepair' and rtl_repair_success == Success

        if fixed_by_preproc:
            row += multicol(3*2, "Repaired by preprocessing")
        else:

            for template in ['replace_literals', 'assign_const', 'add_inversions']:
                if not template in stats:
                    row += multicol(2, "")
                    continue
                num_sols = stats[template]['solutions']
                time = stats[template]['template_time']
                smt_time = stats[template]['solver_time']
                if time > 59.0 and smt_time <= 0.0001:
                    row += multicol(2, "Timeout")
                    continue
                if num_sols == 0:
                    changes = ""
                    status = NoRepair
                else:
                    repairs = res[RtlRepairAllTemplates]['repairs']
                    repairs = [r for r in repairs if r['template'] == template]
                    assert len(repairs) == num_sols
                    assert len(repairs) == 1
                    repair = repairs[0]
                    changes = str(repair['changes']) + " "
                    checks = res[RtlRepairAllTemplates]['checks']
                    assert len(checks) == 1, "More than one repair (from different templates...)!"
                    check_passes = _summarize_checks(checks[0], cirfix=False)
                    if check_passes:
                        status = Success
                    else:
                        status = Fail
                row += [f"{changes}{status}", f"{format_time_s(time)}, {format_time_s(smt_time)}"]

        def outcome(tt: float, success: str, is_cirfix: bool) -> list[str]:
            if not is_cirfix and tt > 59.0: return  multicol(2, "Timeout")
            if tt > 15.9 * 60 * 60: return multicol(2, "Timeout")
            return [success, format_time_s(tt)]

        basic_success = _repair_summary_for_tool(name, RtlRepairBasicSynth, results)
        basic_time = get_time(res[RtlRepairBasicSynth])
        row += outcome(basic_time, basic_success, is_cirfix=False)

        rtl_repair_time = get_time(res[RtlRepair])
        row += outcome(rtl_repair_time, rtl_repair_success, is_cirfix=False)

        cirfix_time = get_time(res[CirFix])
        cirfix_success = res[CirFix]['success']
        row += outcome(cirfix_time, cirfix_success, is_cirfix=True)

        # conservative speedup
        speedup = f"{int(math.floor(cirfix_time / rtl_repair_time)):,}x"
        if rtl_repair_success == Success and cirfix_success == Success:
            speedup = "\\textbf{" + speedup + "}"
        row += [speedup]


        rows.append(row)




    return [header] + rows

CirFix = 'cirfix'
RtlRepair = 'rtlrepair'
Combined = 'combined'
RtlRepairAllTemplates = 'rtlrepair-all-templates'
RtlRepairBasicSynth = 'rtlrepair-basic-synth'
Checks = ['cirfix-tool', 'cirfix-author', 'rtl-sim', 'gate-sim', 'extended-sim', 'iverilog-sim']
def _summarize_checks(checks: dict, cirfix: bool) -> bool:
    # skip cirfix specific checks for rtl repair
    considered_checks = Checks if cirfix else Checks[2:]
    status = [checks[cc] for cc in considered_checks]
    for s in status:
        assert s in {'pass', 'fail', 'na', 'indeterminate'}
    fails = [s == 'fail' for s in status]
    return not True in fails


def _repair_summary_for_tool(benchmark_name: str, tool: str, results: dict):
    tool_res = results[benchmark_name][tool]
    # i.e. does the tool think it created a correct repair?
    tool_success = 'result' in tool_res and tool_res['result']['success']
    if not tool_success:
        return NoRepair
    else:
        checked_repairs = tool_res['checks']
        # we are happy if any of the repairs pass (in one case a CirFix repair only passes in its minimized form)
        check_successes = [_summarize_checks(cc, tool == CirFix) for cc in checked_repairs]
        check_success = True in check_successes
        return Success if check_success else Fail

def create_repair_summary(results):
    """ analyzes the results of our check_repair.py script to come up with an overall assessment """
    for name in all_short_names:
        for tool in [CirFix, RtlRepair]:
            results[name][tool]['success'] = _repair_summary_for_tool(name, tool, results)



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
    if 'statistics' in custom:
        results[benchmark_name][tool]['statistics'] = json.loads(custom['statistics'])



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
        results[name] = {CirFix: {}, RtlRepair: {}, RtlRepairAllTemplates: {}, RtlRepairBasicSynth: {}}
    _load_results(conf.cirfix_result_dir, CirFix, results)
    _load_results(conf.rtlrepair_result_dir, RtlRepair, results)
    _load_results(conf.rtlrepair_all_templates_result_dir, RtlRepairAllTemplates, results)
    _load_results(conf.rtlrepair_basic_synth_result_dir, RtlRepairBasicSynth, results)
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

    performance_statistics = {}
    write_to(conf.working_dir / "performance_table.tex",
             render_latex(performance_table(results, performance_statistics), has_header=True))
    write_to(conf.working_dir / "performance_statistics_table.tex",
             render_latex(performance_statistics_table(performance_statistics), has_header=True))

    write_to(conf.working_dir / "ablation_table.tex",
             render_latex(ablation_table(results), has_header=True, rot_header=True))
    pass

if __name__ == '__main__':
    main()
