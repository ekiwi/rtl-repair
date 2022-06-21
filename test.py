#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import unittest
import os
import subprocess
from pathlib import Path

root_dir = Path(__file__).parent.resolve()
working_dir = root_dir / "working-dir"
benchmark_dir = root_dir / "benchmarks"
decoder_dir = benchmark_dir / "cirfix" / "decoder_3_to_8"
flip_flop_dir = benchmark_dir / "cirfix" / "flip_flop"
counter_dir = benchmark_dir / "cirfix" / "first_counter_overflow"


def run_synth(source: Path, testbench: Path, solver='z3'):
    if not working_dir.exists():
        os.mkdir(working_dir)
    dir_name = source.stem + "_" + testbench.stem
    out_dir = working_dir / dir_name
    args = [
        "--source", str(source.resolve()),
        "--testbench", str(testbench.resolve()),
        "--solver", solver,
        "--working-dir", str(out_dir.resolve())
    ]
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
            changes = int(f.readlines()[0].strip())
    else:
        changes = 0
    return status, changes


class SynthesisTest(unittest.TestCase):

    def synth_success(self, dir: Path, design: str, testbench: str, solver: str = 'z3', max_changes: int = 2):
        status, changes = run_synth(dir / design, dir / testbench, solver)
        self.assertEqual(status, "success")
        self.assertLessEqual(changes, max_changes)

    def synth_no_repair(self, dir: Path, design: str, testbench: str, solver: str = 'z3'):
        self.assertEqual(run_synth(dir / design, dir / testbench, solver)[0], "no-repair")

    def synth_cannot_repair(self, dir: Path, design: str, testbench: str, solver: str = 'z3'):
        self.assertEqual(run_synth(dir / design, dir / testbench, solver)[0], "cannot-repair")


class TestFlipFlop(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(flip_flop_dir, "tff.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_tb(self):
        # cannot be repaired with just literal replacement
        self.synth_cannot_repair(flip_flop_dir, "tff_wadden_buggy1.v", "orig_tb.csv")

    def test_wadden_buggy2_orig_tb(self):
        # cannot be repaired with just literal replacement
        self.synth_cannot_repair(flip_flop_dir, "tff_wadden_buggy2.v", "orig_tb.csv")


class TestFirstCounter(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(counter_dir, "first_counter_overflow.v", "orig_tb.csv")

    # wadden_buggy1 is a sens list bug and thus won't be solvable by our approach

    def test_wadden_buggy2_orig_tb(self):
        # cannot be repaired with just literal replacement
        self.synth_cannot_repair(counter_dir, "first_counter_overflow_wadden_buggy2.v", "orig_tb.csv")

    def test_kgoliya_buggy1_orig_tb(self):
        # cannot be repaired with just literal replacement
        self.synth_cannot_repair(counter_dir, "first_counter_overflow_kgoliya_buggy1.v", "orig_tb.csv")


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
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy2.v", "complete_min_tb.csv",
                           solver="optimathsat", max_changes=8)

    def test_buggy_num_orig_tb(self):
        # this is not mentioned in the paper result, but essentially we just need to change one constant
        self.synth_success(decoder_dir, "decoder_3_to_8_buggy_num.v", "orig_tb.csv")

    def test_buggy_var_complete_min_tb(self):
        # we cannot repair this one with the current repair templates since we would need to replace a variable
        self.synth_cannot_repair(decoder_dir, "decoder_3_to_8_buggy_var.v", "complete_min_tb.csv", solver="optimathsat")


class TestTypeInference(unittest.TestCase):
    """ actual unittests for code in rtlfix/types.py """

    def test_flip_flop_types(self):
        from rtlfix import parse_verilog
        from rtlfix.types import infer_widths
        ast = parse_verilog(flip_flop_dir / "tff.v")
        widths = infer_widths(ast)
        self.assertEqual(len(widths), 5)
        for node, width in widths.items():
            self.assertEqual(width, 1, str(node))


if __name__ == '__main__':
    unittest.main()