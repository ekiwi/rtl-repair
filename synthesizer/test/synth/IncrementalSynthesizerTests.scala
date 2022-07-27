// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

class IncrementalSynthesizerTests extends SynthesizerSpec {
  behavior.of("IncrementalSynthesizer")

  it should "synthesize a solution for sdram_controller_wadden_buggy2_replace_literals with original testbench" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_wadden_buggy2_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().useIncremental() // .showSolverCommunication()
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_wadden_buggy1 with original testbench and literal replacer template" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_wadden_buggy1_with_literals_replaced.btor",
      CirFixDir / "decoder_3_to_8" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().useIncremental()
    )
    assert(r.isSuccess)
  }

  it should "report no solution for sdram_controller_wadden_buggy1_replace_literals with original testbench" in {
    // this is relatively fast because the first disagreement is at step 2
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_wadden_buggy1_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().useIncremental() // .showSolverCommunication()
    )
    assert(r.cannotRepair)
  }

  it should "fail to synthesize a solution for sdram_controller_wadden_buggy1_assign_const with original testbench" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_wadden_buggy1_assign_const.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().useIncremental() // .showSolverCommunication()
    )
    // this version of assign constant should not be solvable
    assert(r.cannotRepair)
  }

  it should "synthesize a solution for sdram_controller_wadden_buggy1_assign_const_fixed with original testbench" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_wadden_buggy1_assign_const_fixed.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().useIncremental() // .showSolverCommunication()
    )
    // this version of assign constant assigns at the end of blocks and thus should work
    assert(r.isSuccess)
  }

  it should "signal no repair for (linter cleaned) sdram_controller_kgoliya_buggy2_replace_literals" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_kgoliya_buggy2_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").useIncremental()
    )
    assert(r.noRepairNecessary)
  }

  it should "signal no repair for i2c_master_top with no changes and replace literals" in {
    val r = Synthesizer.run(
      BenchmarkDir / "i2c_master_top_replace_literals.btor",
      CirFixDir / "opencores" / "i2c" / "fixed_x_prop_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").useIncremental()
    )
    assert(r.noRepairNecessary)
  }

  // TODO: currently the simulator is too slow to solve this in a reasonable time
  //       we are simulating at around 10Hz and need to execute ~160k cycles just to check a solution
  it should "signal no repair for original (not buggy) reed solomon decoder" ignore {
    val r = Synthesizer.run(
      BenchmarkDir / "reed_BM_lamda_orig_tb_replace_literals.btor",
      CirFixDir / "opencores" / "reed_solomon_decoder" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").useIncremental().makeVerbose()
    )
    assert(r.noRepairNecessary)
  }
}
