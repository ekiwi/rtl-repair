// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

/** Tries to synthesize a solution without completely unrolling the system. */
object IncrementalSynthesizer {

  def doRepair(sys: TransitionSystem, tb: Testbench, synthVars: SynthVars, config: Config): RepairResult = {
    println(sys.serialize)

    ???
  }

}
