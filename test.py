#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
import time
import unittest
import os
import subprocess
from collections import defaultdict
from pathlib import Path

_default_solver = 'yices2'
# _default_solver = 'bitwuzla'
_print_time = False
_parallel = False

root_dir = Path(__file__).parent.resolve()
working_dir = root_dir / "working-dir"
benchmark_dir = root_dir / "benchmarks"
decoder_dir = benchmark_dir / "cirfix" / "decoder_3_to_8"
flip_flop_dir = benchmark_dir / "cirfix" / "flip_flop"
counter_dir = benchmark_dir / "cirfix" / "first_counter_overflow"
fsm_dir = benchmark_dir / "cirfix" / "fsm_full"
left_shift_dir = benchmark_dir / "cirfix" / "lshift_reg"
sd_dir = benchmark_dir / "cirfix" / "sdram_controller"


def run_synth(source: Path, testbench: Path, solver='z3', init='any'):
    if not working_dir.exists():
        os.mkdir(working_dir)
    dir_name = source.stem + "_" + testbench.stem
    out_dir = working_dir / dir_name
    args = [
        "--source", str(source.resolve()),
        "--testbench", str(testbench.resolve()),
        "--solver", solver,
        "--working-dir", str(out_dir.resolve()),
        "--init", init
    ]
    if _parallel:
        args += ["--parallel"]
    cmd = ["./rtlfix.py"] + args
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, check=True, cwd=root_dir)
    except subprocess.CalledProcessError as r:
        print(f"Failed to execute command: {' '.join(cmd)}")
        raise r
    with open(out_dir / "status") as f:
        status = f.read().strip()
    if status == "success":
        with open(out_dir / "changes.txt") as f:
            lines = f.readlines()
            template = lines[0].strip()
            changes = int(lines[1].strip())
    else:
        changes = 0
        template = None
    return status, changes, template


class SynthesisTest(unittest.TestCase):

    def synth_success(self, dir: Path, design: str, testbench: str, solver: str = _default_solver, init='any', max_changes: int = 2):
        start = time.monotonic()
        status, changes, template = run_synth(dir / design, dir / testbench, solver, init)
        self.assertEqual("success", status)
        self.assertLessEqual(changes, max_changes)
        if _print_time:
            print(f"SUCCESS: {dir / design} w/ {solver} in {time.monotonic() - start}s")

    def synth_no_repair(self, dir: Path, design: str, testbench: str, solver: str = _default_solver, init='any'):
        start = time.monotonic()
        self.assertEqual("no-repair", run_synth(dir / design, dir / testbench, solver, init)[0])
        if _print_time:
            print(f"NO-REPAIR: {dir / design} w/ {solver} in {time.monotonic() - start}s")

    def synth_cannot_repair(self, dir: Path, design: str, testbench: str, solver: str = _default_solver, init='any'):
        start = time.monotonic()
        self.assertEqual("cannot-repair", run_synth(dir / design, dir / testbench, solver, init)[0])
        if _print_time:
            print(f"CANNOT-REPAIR: {dir / design} w/ {solver} in {time.monotonic() - start}s")


class TestSdRamController(SynthesisTest):

    def test_orig_orig_tb(self):
        # this only works with zero init because otherwise the original design has some x-prop issues
        self.synth_no_repair(sd_dir, "sdram_controller.v", "orig_tb.csv", init='zero')

    @unittest.skip("this is currently not terminating within 30min")
    def test_wadden_buggy2_orig_tb(self):
        # one messed up constant (READ_NOP1)
        self.synth_success(sd_dir, "sdram_controller_wadden_buggy2.v", "orig_tb.csv", init='zero')


class TestLeftShiftReg(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(left_shift_dir, "lshift_reg.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_tb(self):
        # blocking vs. non-blocking
        self.synth_success(left_shift_dir, "lshift_reg_wadden_buggy1.v", "orig_tb.csv")

    def test_wadden_buggy2_orig_tb(self):
        # blocking vs. non-blocking
        self.synth_success(left_shift_dir, "lshift_reg_wadden_buggy2.v", "orig_tb.csv")

    def test_kgoliya_buggy1_orig_tb(self):
        # since this is a negedge vs posedge issue which is outside the model used for model checking
        # our tool claims everything is OK, however that is not the case!
        # => this counts as "cannot-repair"
        self.synth_no_repair(left_shift_dir, "lshift_reg_kgoliya_buggy1.v", "orig_tb.csv")

    def test_buggy_num(self):
        # wrong number in a _for loop_
        # only way to repair this would be to synthesize the following:
        # q[1] <= q[0]
        # q[2] <= q[1]
        self.synth_cannot_repair(left_shift_dir, "lshift_reg_buggy_num.v", "orig_tb.csv")

    def test_buggy_var(self):
        self.synth_success(left_shift_dir, "lshift_reg_buggy_var.v", "orig_tb.csv")


class TestFsmFull(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(fsm_dir, "fsm_full.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_tb(self):
        # missing case
        self.synth_cannot_repair(fsm_dir, "fsm_full_wadden_buggy1.v", "orig_tb.csv")

    def test_ssscrazy_buggy2_orig_tb(self):
        # we repair this by fixing the blocking assignment lint warning
        self.synth_success(fsm_dir, "fsm_full_ssscrazy_buggy2.v", "orig_tb.csv")

    def test_wadden_buggy2_orig_tb(self):
        # latch bug
        # this is repaired (by accident) by our linter based preprocessing
        self.synth_success(fsm_dir, "fsm_full_wadden_buggy2.v", "orig_tb.csv")

    def test_ssscrazy_buggy1(self):
        # latch bug
        # this is repaired (by accident) by our linter based preprocessing
        self.synth_success(fsm_dir, "fsm_full_ssscrazy_buggy1.v", "orig_tb.csv")

    def test_buggy_num(self):
        self.synth_success(fsm_dir, "fsm_full_buggy_num.v", "orig_tb.csv")

    def test_buggy_var(self):
        # should be solvable by replacing a single variable
        self.synth_success(fsm_dir, "fsm_full_buggy_var.v", "orig_tb.csv", max_changes=1)

    def test_super_buggy(self):
        # this one contains a sens list bug which might be impossible to repair
        # TODO: check if the repair makes sense!
        self.synth_success(fsm_dir, "fsm_full_super_buggy.v", "orig_tb.csv", max_changes=4)


class TestFlipFlop(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(flip_flop_dir, "tff.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_tb(self):
        self.synth_success(flip_flop_dir, "tff_wadden_buggy1.v", "orig_tb.csv")

    def test_wadden_buggy2_orig_tb(self):
        self.synth_success(flip_flop_dir, "tff_wadden_buggy2.v", "orig_tb.csv")


class TestFirstCounter(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(counter_dir, "first_counter_overflow.v", "orig_tb.csv")

    # wadden_buggy1 is a sens list bug and thus won't be solvable by our approach
    def test_wadden_buggy1_orig_tb(self):
        self.synth_cannot_repair(counter_dir, "first_counter_overflow_wadden_buggy1.v", "orig_tb.csv")

    def test_wadden_buggy2_orig_tb(self):
        # cannot be repaired with just literal replacement
        # this would need an if() condition to modified
        self.synth_cannot_repair(counter_dir, "first_counter_overflow_wadden_buggy2.v", "orig_tb.csv")

    def test_kgoliya_buggy1_orig_tb(self):
        # this can be repaired through the assign_const template
        self.synth_success(counter_dir, "first_counter_overflow_kgoliya_buggy1.v", "orig_tb.csv")


class TestDecoder(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(decoder_dir, "decoder_3_to_8.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy1.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_min_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy1.v", "orig_min_tb.csv")

    def test_wadden_buggy1_complete_min_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy1.v", "complete_min_tb.csv")

    def test_wadden_buggy2_complete_min_tb(self):
        # this would take a lot longer if using z3
        # should be do-able by changing 8 constants
        # time with optimathsat: ~28s
        # time with btormc: ~2.1s
        # time with yices2: ~7.3s
        # time with bitwuzla: ~2.2s
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy2.v", "complete_min_tb.csv", max_changes=8)

    def test_buggy_num_orig_tb(self):
        # this is not mentioned in the paper result, but essentially we just need to change one constant
        self.synth_success(decoder_dir, "decoder_3_to_8_buggy_num.v", "orig_tb.csv")

    def test_buggy_num_complete_min_tb(self):
        # this is not mentioned in the paper result, but essentially we just need to change one constant
        self.synth_success(decoder_dir, "decoder_3_to_8_buggy_num.v", "complete_min_tb.csv")

    def test_buggy_var_complete_min_tb(self):
        # can be repaired with the replace variable template
        # note, this test takes ~17s with optimathsat, ~4.5s with btormc, ~4.2s with yices2, ~4.4s with bitwuzla
        self.synth_success(decoder_dir, "decoder_3_to_8_buggy_var.v", "complete_min_tb.csv")

    def test_buggy_var_orig_tb(self):
        # note: the repair is not actually correct since the testbench is incomplete
        self.synth_success(decoder_dir, "decoder_3_to_8_buggy_var.v", "orig_tb.csv")

    def test_super_buggy_complete_min_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_super_buggy.v", "complete_min_tb.csv", max_changes=6)

    def test_super_buggy_orig_tb(self):
        # note: the repair is not actually correct since the testbench is incomplete
        self.synth_success(decoder_dir, "decoder_3_to_8_super_buggy.v", "orig_tb.csv", max_changes=4)


def _make_histogram(widths: dict) -> dict:
    hist = defaultdict(int)
    for _, w in widths.items():
        hist[w] += 1
    return dict(hist)


class TestTypeInference(unittest.TestCase):
    """ actual unittests for code in rtlfix/types.py """

    def test_flip_flop_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(flip_flop_dir / "tff.v")
        widths = infer_widths(ast)
        self.assertEqual({None: 1, 1: 6}, _make_histogram(widths))

    def test_flip_flop_buggy1_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(flip_flop_dir / "tff_wadden_buggy1.v")
        widths = infer_widths(ast)
        self.assertEqual({None: 1, 1: 5}, _make_histogram(widths))

    def test_decoder_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(decoder_dir / "decoder_3_to_8.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 5, 4: 16, 8: 17}, hist)

    def test_counter_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(counter_dir / "first_counter_overflow.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 8, 4: 7}, hist)

    def test_fsm_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(fsm_dir / "fsm_full.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 19, 3: 8}, hist)

    def test_left_shift_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(left_shift_dir / "lshift_reg.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 3, 8: 7, 32: 6}, hist)

    def test_sdram_controller_widths(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(sd_dir / "sdram_controller.v")
        # ast.show()
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        expected = {None: 1, 32: 26, 5: 60, 8: 17, 2: 7, 13: 4, 1: 14, 10: 7, 4: 7, 24: 4, 16: 5, 9: 2, 3: 1}
        self.assertEqual(expected, hist)


if __name__ == '__main__':
    # ignore warnings because pyverilog is not good about closing some files it opens
    unittest.main(warnings='ignore')
