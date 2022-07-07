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
    assert(
      r.cannotRepair
    ) // currently the incremental solver fails because looking at a single failure case is not enough
  }

  it should "signal no repair for (linter cleaned) sdram_controller_kgoliya_buggy2_replace_literals" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_kgoliya_buggy2_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").useIncremental()
    )
    assert(r.noRepairNecessary)
  }

}
