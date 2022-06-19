#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import unittest
import subprocess
from pathlib import Path

root_dir = Path(__file__).parent.resolve()
working_dir = root_dir / "working-dir"
benchmark_dir = root_dir / "benchmarks"
decoder_dir = benchmark_dir / "cirfix" / "decoder_3_to_8"


def run_synth(source: Path, testbench: Path, solver='z3') -> str:
    dir_name = source.stem + "_" + testbench.stem
    out_dir = working_dir / dir_name
    args = [
        "--source", str(source.resolve()),
        "--testbench", str(testbench.resolve()),
        "--solver", solver,
        "--working-dir", str(out_dir.resolve())
    ]
    r = subprocess.run(["./rtlfix.py"] + args, stdout=subprocess.PIPE, check=True, cwd=root_dir)
    with open(out_dir / "status") as f:
        status = f.read()
    return status.strip()


class SynthesisTest(unittest.TestCase):

    def synth_success(self, dir: Path, design: str, testbench: str, solver: str = 'z3'):
        self.assertEqual(run_synth(dir / design, dir / testbench, solver), "success")


class TestDecoder(SynthesisTest):

    def test_wadden_buggy1_orig_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy1.v", "orig_tb.csv")

    def test_wadden_buggy1_orig_min_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy1.v", "orig_min_tb.csv")

    def test_wadden_buggy1_complete_min_tb(self):
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy1.v", "complete_min_tb.csv")

    def test_wadden_buggy2_complete_min_tb(self):
        # this would take a lot longer if using z3
        self.synth_success(decoder_dir, "decoder_3_to_8_wadden_buggy2.v", "complete_min_tb.csv", "optimathsat")


if __name__ == '__main__':
    unittest.main()
