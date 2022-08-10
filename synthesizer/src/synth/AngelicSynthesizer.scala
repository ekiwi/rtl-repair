// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import synth.Synthesizer.{initSys, inlineAndRemoveDeadCode, setAnonymousInputsToZero}

/** Tries to identify the minimal number of signals/expressions that need to be changed through the use of
  * angelic values.
  */
object AngelicSynthesizer {

  def doRepair(sys: TransitionSystem, tb: Testbench, config: Config, rnd: scala.util.Random): RepairResult = {
    println(sys.serialize)

    ???
  }
}
