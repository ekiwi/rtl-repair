// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

/** Tries to synthesize a solution without completely unrolling the system. */
object IncrementalSynthesizer {
  import synth.Synthesizer.{initSys, isSynthName}

  def doRepair(
    sys:       TransitionSystem,
    tb:        Testbench,
    synthVars: SynthVars,
    config:    Config,
    rnd:       scala.util.Random
  ): RepairResult = {
    // randomly init system
    val initialized = initSys(sys, RandomInit, rnd)
    // disable all synthesis variables
    val noChange = noSynth(initialized)

    // execute testbench on system
    Testbench.run(noChange, tb)

    println(noChange.serialize)

    ???
  }

  private def noSynth(sys: TransitionSystem): TransitionSystem = {
    // this assumes that all synthesis variables states have already been removed and we just need to
    // set all uses to zero
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym: BVSymbol if isSynthName(sym.name) => BVLiteral(0, sym.width)
      case BVIte(cond, tru, fals) => // do some small constant prop
        onExpr(cond) match {
          case True()  => onExpr(tru)
          case False() => onExpr(fals)
          case cc: BVExpr => BVIte(cc, onExpr(tru).asInstanceOf[BVExpr], onExpr(fals).asInstanceOf[BVExpr])
        }
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(signals = signals)
  }

}
