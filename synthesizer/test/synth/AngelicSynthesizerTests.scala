// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

class AngelicSynthesizerTests extends SynthesizerSpec {
  behavior.of("AngelicSynthesizer")

  it should "diagnose fsm_full_wadden_buggy1" ignore { // TODO: wip
    Synthesizer.run(
      BenchmarkDir / "fsm_full_wadden_buggy1.btor",
      CirFixDir / "fsm_full" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").changeInit(RandomInit).copy(seed = 1).useAngelic()
    )
  }
}
