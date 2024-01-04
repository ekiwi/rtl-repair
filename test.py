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

import tomli

from benchmarks import load_project, get_benchmark

_default_solver = 'yices2'
# _default_solver = 'bitwuzla'
_print_time = False

root_dir = Path(__file__).parent.resolve()
working_dir = root_dir / "working-dir"
benchmark_dir = root_dir / "benchmarks"
decoder_dir = benchmark_dir / "cirfix" / "decoder_3_to_8"
flip_flop_dir = benchmark_dir / "cirfix" / "flip_flop"
counter_dir = benchmark_dir / "cirfix" / "first_counter_overflow"
fsm_dir = benchmark_dir / "cirfix" / "fsm_full"
left_shift_dir = benchmark_dir / "cirfix" / "lshift_reg"
mux_dir = benchmark_dir / "cirfix" / "mux_4_1"
sd_dir = benchmark_dir / "cirfix" / "sdram_controller"
opencores_dir = benchmark_dir / "cirfix" / "opencores"
reed_dir = opencores_dir / "reed_solomon_decoder"
sha_dir = opencores_dir / "sha3" / "low_throughput_core"
i2c_dir = opencores_dir / "i2c"
chisel_dir = benchmark_dir / "chisel"
chisel_counter_dir = chisel_dir / "counter"
paper_example_dir = benchmark_dir / "paper_example"
fpga_debug_dir = benchmark_dir / "fpga-debugging"
s3_dir = fpga_debug_dir / "axis-adapter-s3"
d4_dir = fpga_debug_dir / "axis-fifo-d4"
d13_dir = fpga_debug_dir / "axis-frame-len-d13"
d12_dir = fpga_debug_dir / "axis-fifo-d12"


def run_synth(project_path: Path, bug: str, testbench: str = None, solver='z3', init='any', incremental=True, timeout=None, old_synthesizer=False):
    if not working_dir.exists():
        os.mkdir(working_dir)
    # determine the directory name from project and bug name
    project = load_project(project_path)
    benchmark = get_benchmark(project, bug, testbench)
    out_dir = working_dir / benchmark.name

    args = [
        "--project", str(project_path.resolve()),
        "--solver", solver,
        "--working-dir", str(out_dir.resolve()),
        "--init", init,
        "--verbose-synthesizer",
    ]
    if bug: # bug is optional to allow for sanity-check "repairs" of the original design
        args += ["--bug", bug]
    if testbench:
        args += ["--testbench", testbench]
    if incremental:
        args += ["--incremental"]
    if timeout:
        args += ["--timeout", str(timeout)]
    if old_synthesizer:
        args += ["--old-synthesizer"]

    cmd = ["./rtlrepair.py"] + args
    # for debugging:
    cmd_str = ' '.join(cmd)
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, check=True, cwd=root_dir)
    except subprocess.CalledProcessError as r:
        print(f"Failed to execute command: {cmd_str}")
        raise r

    with open(out_dir / "result.toml", 'rb') as ff:
        dd = tomli.load(ff)
    status = dd['custom']['status']
    if dd['result']['success']:
        repairs = dd['repairs']
        template = repairs[0]['template']
        changes = repairs[0]['changes']
    else:
        changes = 0
        template = None

    # check file format
    if not dd['result']['success']:
        assert status in {'cannot-repair', 'timeout'}

    return status, changes, template


class SynthesisTest(unittest.TestCase):

    def synth_success(self, project_path: Path, bug: str=None, testbench=None, solver: str = _default_solver, init='any',
                      incremental: bool = False, timeout: int = None, max_changes: int = 2, old_synthesizer: bool = False):
        start = time.monotonic()
        status, changes, template = run_synth(project_path, bug, testbench, solver, init, incremental, timeout, old_synthesizer)
        self.assertEqual("success", status)
        self.assertLessEqual(changes, max_changes)
        if _print_time:
            print(f"SUCCESS: {project_path} w/ {solver} in {time.monotonic() - start}s")
        return changes

    def synth_no_repair(self, project_path: Path, bug: str=None, testbench=None, solver: str = _default_solver, init='any',
                      incremental: bool = False, timeout: int = None, max_changes: int = 2, old_synthesizer: bool = False):
        start = time.monotonic()
        status, _, _ = run_synth(project_path, bug, testbench, solver, init, incremental, timeout, old_synthesizer)
        self.assertEqual("no-repair", status)
        if _print_time:
            print(f"NO-REPAIR: {project_path} w/ {solver} in {time.monotonic() - start}s")

    def synth_cannot_repair(self, project_path: Path, bug: str=None, testbench=None, solver: str = _default_solver, init='any',
                      incremental: bool = False, timeout: int = None, max_changes: int = 2, old_synthesizer: bool = False):
        start = time.monotonic()
        status, _, _ = run_synth(project_path, bug, testbench, solver, init, incremental, timeout, old_synthesizer)
        self.assertEqual("cannot-repair", status)
        if _print_time:
            print(f"CANNOT-REPAIR: {project_path} w/ {solver} in {time.monotonic() - start}s")

class TestFpgaDebugBenchmarks(SynthesisTest):

    def test_s3(self):
        """ AXIS Adapter with incorrect last cycle detection """
        self.synth_cannot_repair(s3_dir, "s3", solver="yices2", init="zero", incremental=True, timeout=60)

    def test_d4(self):
        """ AXIS Fifo with overflow bug """
        self.synth_cannot_repair(d4_dir, "d4", solver="yices2", init="zero", incremental=True, timeout=60)

    def test_d13(self):
        """ simple AXIS frame len circuit with wrong calculatio / state update """
        self.synth_cannot_repair(d13_dir, "d13", solver="yices2", init="zero", incremental=True, timeout=60)

    def test_d12(self):
        """ AXIS Fifo with one-line fixable bug """
        self.synth_cannot_repair(d12_dir, "d12", solver="yices2", init="zero", incremental=True, timeout=60)

class TestCirFixBenchmarksIncremental(SynthesisTest):
    """ Makes sure that we can handle all benchmarks from the cirfix paper in incremental mode. """
    solver: str = 'bitwuzla'
    incremental: bool = True
    init: str = 'random'
    timeout: int = 60

    def test_decoder_wadden1(self):
        # CirFix: incorrect repair
        changes = self.synth_success(decoder_dir, "wadden_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(2, changes)

    def test_decoder_wadden2(self):
        # CirFix: timeout
        changes = self.synth_success(decoder_dir, "wadden_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout, max_changes=5)
        self.assertEqual(5, changes)
        # note: our repair is only correct for the part that is actually tested

    def test_counter_kgoliya1(self):
        # CirFix: correct repair
        changes = self.synth_success(counter_dir, "kgoliya_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(1, changes)

    def test_counter_wadden1(self):
        # CirFix: correct repair
        self.synth_cannot_repair(counter_dir, "wadden_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_counter_wadden2(self):
        # CirFix: correct repair
        self.synth_cannot_repair(counter_dir, "wadden_buggy2", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_flip_flop_wadden1(self):
        # CirFix: correct repair
        changes = self.synth_success(flip_flop_dir, "wadden_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(1, changes)

    def test_flip_flop_wadden2(self):
        # CirFix: correct repair
        changes = self.synth_success(flip_flop_dir, "wadden_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(2, changes)

    def test_fsm_full_ssscrazy1(self):
        # CirFix: incorrect repair
        changes = self.synth_success(fsm_dir, "ssscrazy_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(2, changes) # repaired by pre-processing!

    def test_fsm_full_ssscrazy2(self):
        # CirFix: incorrect repair
        changes = self.synth_success(fsm_dir, "ssscrazy_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout, max_changes=20)
        self.assertEqual(15, changes) # repaired by pre-processing!

    @unittest.skip("need to set _ENABLE_NEW_CASE_STATEMENT for this to work")
    def test_fsm_full_wadden1(self):
        # CirFix: timed out
        self.synth_success(fsm_dir, "wadden_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)
        # repaired by extended assign const

    def test_fsm_full_wadden2(self):
        # CirFix: incorrect repair
        changes = self.synth_success(fsm_dir, "wadden_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout, max_changes=10)
        # "repaired" by pre-processing
        # however, the repair is not actually correct because of the simulation-synthesis-mismatch nature of the bug
        self.assertEqual(3, changes)

    def test_lshift_reg_kgoliya1(self):
        # CirFix: correct repair
        # RTL-Repair: the posedge -> negedge change means that after synthesis it looks like everything works
        self.synth_no_repair(left_shift_dir, "kgoliya_buggy1", solver=self.solver, init=self.init,
                             incremental=self.incremental, timeout=self.timeout)

    def test_lshift_reg_wadden1(self):
        # CirFix: correct repair
        changes = self.synth_success(left_shift_dir, "wadden_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout, max_changes=10)
        self.assertEqual(4, changes)  # repaired by pre-processing!

    def test_lshift_reg_wadden2(self):
        # CirFix: correct repair
        changes = self.synth_success(left_shift_dir, "wadden_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(1, changes)

    def test_mux_kgoliya1(self):
        # CirFix: timeout
        # RTL-Repair: synthesizer crashes because expected output value is too big for 1-bit output signal
        self.synth_cannot_repair(mux_dir, "kgoliya_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_mux_wadden1(self):
        # CirFix: timeout
        changes = self.synth_success(mux_dir, "wadden_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout, max_changes=3)
        self.assertEqual(3, changes)

    def test_mux_wadden2(self):
        # CirFix: timeout
        changes = self.synth_success(mux_dir, "wadden_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(2, changes)

    def test_reed_BM_lambda(self):
        # CirFix: timeout
        self.synth_cannot_repair(reed_dir, "BM_lamda_ssscrazy_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_reed_out_stage(self):
        # CirFix: incorrect repair
        self.synth_cannot_repair(reed_dir, "out_stage_ssscrazy_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_sdram_wadden1(self):
        # CirFix: correct repair (minimization fails)
        changes = self.synth_success(sd_dir / "no_tri_state.toml", "wadden_buggy1", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(1, changes)

    def test_sdram_wadden2(self):
        # CirFix: timeout
        changes = self.synth_success(sd_dir / "no_tri_state.toml", "wadden_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(2, changes)

    def test_sdram_kgoliya2(self):
        # CirFix: timeout
        changes = self.synth_success(sd_dir / "no_tri_state.toml", "kgoliya_buggy2", solver=self.solver, init=self.init,
                                     incremental=self.incremental, timeout=self.timeout)
        self.assertEqual(1, changes)  # repaired by pre-processing + assign const!

    def test_i2c_master_kgoliya1(self):
        # CirFix: incorrect repair
        changes = self.synth_success(i2c_dir / "master_sync_reset.toml", "kgoliya_buggy1", "fixed_x_prop_tb",
                                     solver=self.solver, init=self.init, incremental=self.incremental,
                                     timeout=(self.timeout * 2)) # TODO: this benchmark has become very slow!
        self.assertEqual(1, changes)

    def test_i2c_slave_wadden1(self):
        # CirFix: correct repair
        # RTL-Repair: cannot repair since I2C-Slave is not synthesizable
        self.synth_cannot_repair(i2c_dir / "slave.toml", "wadden_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_i2c_slave_wadden2(self):
        # CirFix: incorrect repair
        # RTL-Repair: cannot repair since I2C-Slave is not synthesizable
        self.synth_cannot_repair(i2c_dir / "slave.toml", "wadden_buggy2", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_sha3_keccak_wadden1(self):
        # CirFix: correct repair
        self.synth_cannot_repair(sha_dir / "keccak.toml", "wadden_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_sha3_keccak_wadden2(self):
        # CirFix: timeout
        self.synth_cannot_repair(sha_dir / "keccak.toml", "wadden_buggy2", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_sha3_round_ssscrazy1(self):
        # CirFix: timeout
        # RTL-Repair: current _replace literal_ instrumentation leads to non-synthesizable `if generate`
        self.synth_cannot_repair(sha_dir / "keccak.toml", "round_ssscrazy_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

    def test_sha3_padder_ssscrazy1(self):
        # CirFix: incorrect repair
        # RTL-Repair: current _replace variables_ instrumentation leads to topological loop
        self.synth_cannot_repair(sha_dir / "padder.toml", "ssscrazy_buggy1", solver=self.solver, init=self.init,
                                 incremental=self.incremental, timeout=self.timeout)

class TestPaperExample(SynthesisTest):
    def test_tb(self):
        self.synth_success(paper_example_dir, "buggy", init='random')

class TestChiselCounter(SynthesisTest):
    def test_full_tb(self):
        self.synth_success(chisel_counter_dir, "bug", "full")

    def test_formal_tb(self):
        self.synth_success(chisel_counter_dir, "bug", "formal")

    def test_random_tb(self):
        self.synth_success(chisel_counter_dir, "bug", "rand")


class TestSdRamController(SynthesisTest):

    def test_orig_orig_tb(self):
        # this only works with zero init because otherwise the original design has some x-prop issues
        self.synth_no_repair(sd_dir / "no_tri_state.toml", init='zero')

    def test_wadden_buggy2_orig_tb(self):
        # one messed up constant (READ_NOP1)
        # requires two changes since the constant is used in two places
        # only completes in a resonable amount of time when using the incremental solver
        # TODO: currently the solver replaces b10000 with b11100, instead of the expected b10001
        #       but that might be OK after all since it does it in both locations
        self.synth_success(sd_dir / "no_tri_state.toml", "wadden_buggy2", incremental=True)

    def test_wadden_buggy1_orig_tb(self):
        # missing reset (only one of the two removed is actually needed)
        self.synth_success(sd_dir / "no_tri_state.toml", "wadden_buggy1", incremental=True)

    def test_kgoliya_buggy2_orig_tb(self):
        # missing default case
        self.synth_success(sd_dir / "no_tri_state.toml", "kgoliya_buggy2", incremental=True)


class TestI2C(SynthesisTest):

    def test_orig_fixed_x_prop_tb(self):
        self.synth_no_repair(i2c_dir / "master_sync_reset.toml", testbench="fixed_x_prop_tb", init='zero', incremental=True)


    def test_kgoliya_buggy1(self):
        self.synth_success(i2c_dir / "master_sync_reset.toml", "kgoliya_buggy1", "fixed_x_prop_tb", init='zero', incremental=True)


class TestReedSolomon(SynthesisTest):

    @unittest.skip("Takes ~30k cycles to first failure and our simulator is just too slow for that.")
    def test_orig_orig_tb(self):
        self.synth_no_repair(reed_dir, "original", "orig_tb", init='zero')


class TestMux(SynthesisTest):

    def test_orig_orig_tb(self):
        # the blocking assignment is turned into a non-blocking one, which is why a "SUCCESS" is reported
        self.synth_success(mux_dir, max_changes=4)

    def test_wadden_buggy1_orig_tb(self):
        self.synth_success(mux_dir, "wadden_buggy1", max_changes=3)

    def test_wadden_buggy2_orig_tb(self):
        self.synth_success(mux_dir, "wadden_buggy2")


class TestLeftShiftReg(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(left_shift_dir)

    def test_wadden_buggy1_orig_tb(self):
        # blocking vs. non-blocking
        self.synth_success(left_shift_dir, "wadden_buggy1", max_changes=4)

    def test_wadden_buggy2_orig_tb(self):
        # blocking vs. non-blocking
        self.synth_success(left_shift_dir, "wadden_buggy2")

    def test_kgoliya_buggy1_orig_tb(self):
        # since this is a negedge vs posedge issue which is outside the model used for model checking
        # our tool claims everything is OK, however that is not the case!
        # => this counts as "cannot-repair"
        self.synth_no_repair(left_shift_dir, "kgoliya_buggy1")

    def test_buggy_num(self):
        # wrong number in a _for loop_
        # only way to repair this would be to synthesize the following:
        # q[1] <= q[0]
        # q[2] <= q[1]
        self.synth_cannot_repair(left_shift_dir, "buggy_num")

    def test_buggy_var(self):
        self.synth_success(left_shift_dir, "buggy_var")


class TestFsmFull(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(fsm_dir)

    def test_wadden_buggy1_orig_tb(self):
        # missing case
        self.synth_cannot_repair(fsm_dir, "wadden_buggy1")

    def test_ssscrazy_buggy2_orig_tb(self):
        # we repair this by fixing the blocking assignment lint warning
        self.synth_success(fsm_dir, "ssscrazy_buggy2", max_changes=15)

    def test_wadden_buggy2_orig_tb(self):
        # latch bug
        # this is repaired (by accident) by our linter based preprocessing
        self.synth_success(fsm_dir, "wadden_buggy2", max_changes=3)

    def test_ssscrazy_buggy1(self):
        # latch bug
        # this is repaired (by accident) by our linter based preprocessing
        self.synth_success(fsm_dir, "ssscrazy_buggy1")

    def test_buggy_num(self):
        self.synth_success(fsm_dir, "buggy_num")

    def test_buggy_var(self):
        # should be solvable by replacing a single variable
        self.synth_success(fsm_dir, "buggy_var", max_changes=1)

    def test_super_buggy(self):
        # this one contains a sens list bug which might be impossible to repair
        # TODO: check if the repair makes sense!
        self.synth_success(fsm_dir, "super_buggy", max_changes=6)


class TestFlipFlop(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(flip_flop_dir)

    def test_wadden_buggy1_orig_tb(self):
        self.synth_success(flip_flop_dir, "wadden_buggy1")

    def test_wadden_buggy2_orig_tb(self):
        self.synth_success(flip_flop_dir, "wadden_buggy2")


class TestFirstCounter(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(counter_dir, testbench="orig_tb", init='random')

    # wadden_buggy1 is a sens list bug and thus won't be solvable by our approach
    def test_wadden_buggy1_orig_tb(self):
        # self.synth_cannot_repair(counter_dir, "first_counter_overflow_wadden_buggy1.v")
        # TODO: deal with this problem more gracefully
        pass

    def test_wadden_buggy2_orig_tb(self):
        # cannot be repaired with just literal replacement
        # this would need an if() condition to modified
        self.synth_cannot_repair(counter_dir, "wadden_buggy2", "orig_tb", init='random')

    def test_kgoliya_buggy1_orig_tb(self):
        # this can be repaired through the assign_const template
        # however the repair is incorrect, since it makes the enable signal behave incorrectly
        self.synth_success(counter_dir, "kgoliya_buggy1", "orig_tb", init='random')

    def test_kgoliya_buggy1_en_test_tb(self):
        # this uses an updated testbench that actually tests the enable signal
        # the solution correctly adds the assignment to zero to the reset block
        self.synth_success(counter_dir, "kgoliya_buggy1", "en_test_tb", init='random')

    def test_buggy_counter_orig_tb(self):
        # can be solved by a literal replacement
        self.synth_success(counter_dir, "buggy_counter", "orig_tb", init='random')

    def test_buggy_overflow_orig_tb(self):
        # can be solved by a literal replacement
        self.synth_success(counter_dir, "buggy_overflow", "orig_tb", init='random')

    def test_buggy_all_orig_tb(self):
        # can be solved by three literal replacements
        self.synth_success(counter_dir, "buggy_all", "orig_tb", max_changes=3, init='random')


class TestDecoder(SynthesisTest):

    def test_orig_orig_tb(self):
        self.synth_no_repair(decoder_dir, testbench="orig_tb")

    def test_wadden_buggy1_orig_tb(self):
        self.synth_success(decoder_dir, "wadden_buggy1", "orig_tb")

    def test_wadden_buggy1_orig_min_tb(self):
        self.synth_success(decoder_dir, "wadden_buggy1", "orig_min_tb")

    def test_wadden_buggy1_complete_min_tb(self):
        self.synth_success(decoder_dir, "wadden_buggy1", "complete_min_tb")

    def test_wadden_buggy2_complete_min_tb(self):
        # this would take a lot longer if using z3
        # should be do-able by changing 8 constants
        # time with optimathsat: ~28s
        # time with btormc: ~2.1s
        # time with yices2: ~7.3s
        # time with bitwuzla: ~2.2s
        self.synth_success(decoder_dir, "wadden_buggy2", "complete_min_tb", max_changes=8)

    def test_buggy_num_orig_tb(self):
        # this is not mentioned in the paper result, but essentially we just need to change one constant
        self.synth_success(decoder_dir, "buggy_num", "orig_tb")

    def test_buggy_num_complete_min_tb(self):
        # this is not mentioned in the paper result, but essentially we just need to change one constant
        self.synth_success(decoder_dir, "buggy_num", "complete_min_tb")

    def test_buggy_var_complete_min_tb(self):
        # can be repaired with the replace variable template
        # note, this test takes ~17s with optimathsat, ~4.5s with btormc, ~4.2s with yices2, ~4.4s with bitwuzla
        self.synth_success(decoder_dir, "buggy_var", "complete_min_tb")

    def test_buggy_var_orig_tb(self):
        # note: the repair is not actually correct since the testbench is incomplete
        self.synth_success(decoder_dir, "buggy_var", "orig_tb")

    def test_super_buggy_complete_min_tb(self):
        self.synth_success(decoder_dir, "super_buggy", "complete_min_tb", max_changes=6)

    def test_super_buggy_orig_tb(self):
        # note: the repair is not actually correct since the testbench is incomplete
        self.synth_success(decoder_dir, "super_buggy", "orig_tb", max_changes=4)


def _make_histogram(widths: dict) -> dict:
    hist = defaultdict(int)
    for _, w in widths.items():
        hist[w] += 1
    return dict(hist)


class TestTypeInference(unittest.TestCase):
    """ actual unittests for code in rtlrepair/types.py """

    def test_flip_flop_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(flip_flop_dir / "tff.v")
        widths = infer_widths(ast)
        self.assertEqual({None: 1, 1: 6}, _make_histogram(widths))

    def test_flip_flop_buggy1_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(flip_flop_dir / "tff_wadden_buggy1.v")
        widths = infer_widths(ast)
        self.assertEqual({None: 1, 1: 5}, _make_histogram(widths))

    def test_decoder_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(decoder_dir / "decoder_3_to_8.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 13, 4: 8, 8: 17}, hist)

    def test_counter_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(counter_dir / "first_counter_overflow.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 8, 4: 5}, hist)

    def test_fsm_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(fsm_dir / "fsm_full.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 19, 3: 8}, hist)

    def test_left_shift_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(left_shift_dir / "lshift_reg.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        self.assertEqual({None: 1, 1: 4, 8: 7, 32: 5}, hist)

    def test_sdram_controller_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(sd_dir / "sdram_controller.no_tri_state.v")
        # ast.show()
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        expected = {None: 1, 32: 24, 5: 50, 8: 17, 2: 7, 13: 4, 1: 26, 10: 7, 4: 7, 24: 4, 16: 5, 9: 2, 3: 1}
        self.assertEqual(expected, hist)

    def test_reed_solomon_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(reed_dir / "BM_lamda.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        expected = {None: 1, 1: 26, 3: 1, 4: 5, 5: 4, 8: 99, 9: 9, 32: 32}
        self.assertEqual(expected, hist)

    def test_i2c_bit_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(i2c_dir / "i2c_master_bit_ctrl.sync_reset.v", i2c_dir)
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        expected = {None: 1, 1: 69, 2: 15, 3: 11, 4: 5, 14: 4, 16: 6, 18: 19, 32: 2}
        self.assertEqual(expected, hist)

    def test_mux_widths(self):
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(mux_dir / "mux_4_1.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        expected = {None: 1, 2: 5, 4: 5}
        self.assertEqual(expected, hist)

    def test_axis_adapter_widths(self):
        """ This file contains the `indexed part selector`: [... +: ... ] """
        from rtlrepair import parse_verilog
        from rtlrepair.types import infer_widths
        ast = parse_verilog(s3_dir / "axis_adapter.v")
        widths = infer_widths(ast)
        hist = _make_histogram(widths)
        expected = {None: 4, 1: 69, 3: 5, 8: 11, 32: 27}
        self.assertEqual(expected, hist)

class TestExposeBranches(unittest.TestCase):
    """ unittests for code in rtlrepair/expose_branches.py """

    def test_flip_flop(self):
        from rtlrepair import parse_verilog
        from rtlrepair.expose_branches import expose_branches
        ast = parse_verilog(flip_flop_dir / "tff.v")
        expose_branches(ast)


if __name__ == '__main__':
    # ignore warnings because pyverilog is not good about closing some files it opens
    unittest.main(warnings='ignore')
