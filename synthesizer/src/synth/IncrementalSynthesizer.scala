// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

/** Tries to synthesize a solution without completely unrolling the system. */
object IncrementalSynthesizer {
  import synth.Synthesizer._
  import synth.SmtSynthesizer._

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
    val exec = Testbench.run(noChange, tb)
    if (!exec.failed) {
      if (config.verbose) println("No failure. System seems to work without any changes.")
      return NoRepairNecessary
    }

    // start solver and declare system
    val ctx = startSolver(config)
    // declare synthesis variables
    synthVars.declare(ctx)
    val enc = encodeSystem(sys, ctx, config)

    // start k steps before failure
    val k = 2
    val start = Seq(exec.failAt - k, 0).max
    val startValues = exec.values(start)
    sys.states.foreach { st =>
      val sym = st.sym.asInstanceOf[BVSymbol]
      val eq = BVEqual(enc.getSignalAt(sym, 0), BVLiteral(startValues(sym.name), sym.width))
      ctx.assert(eq)
    }

    // unroll for k, applying the appropriate inputs and outputs
    val shortTb = tb.slice(start, start + k)
    instantiateTestbench(ctx, enc, sys, shortTb, (a, b) => None, assertDontAssumeOutputs = false)

    // check to see if a fix to the system exists that will make the outputs not fail
    ctx.check() match {
      case IsSat =>
        println("Potential solutions found!")
      case IsUnSat =>
        println("No solution")
      case IsUnknown => ???
    }

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
