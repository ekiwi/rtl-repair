// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._
import synth.SmtSynthesizer.instantiateTestbench
import synth.Synthesizer.{encodeSystem, initSys, startSolver}

import scala.collection.mutable

/** Tries to identify the minimal number of signals/expressions that need to be changed through the use of
  * angelic values.
  */
object AngelicSynthesizer {

  def doRepair(sys: TransitionSystem, tb: Testbench, config: Config, rnd: scala.util.Random): RepairResult = {
    // randomly init system
    val initialized = initSys(sys, RandomInit, rnd)
    // random undefined inputs
    val randInputTb = Testbench.addRandomInput(sys, tb, rnd)

    // sanity check: is there a need to repair?
    val exec = Testbench.run(initialized, randInputTb, verbose = true, vcd = Some(os.pwd / "fsm_full.vcd"))
    if (!exec.failed) {
      if (config.verbose) println("No failure. System seems to work without any changes.")
      return NoRepairNecessary
    }

    // add angelic instrumentation
    val (angelicSys, angelicVars) = new AngelicInstrumentation().run(initialized)

    // declare angelic change variables
    val ctx = startSolver(config)
    angelicVars.vars.foreach(v => ctx.runCommand(DeclareFunction(v.changeSym, Seq())))
    val enc = encodeSystem(angelicSys, ctx, config)

    // instantiate the testbench with inputs _and_ outputs assumed to be correct
    instantiateTestbench(ctx, enc, angelicSys, randInputTb, noUninitialized _, assertDontAssumeOutputs = false)

    // try to minimize the number of changes while fixing the problem

    println(angelicSys.serialize)

    ???
  }

  /** throws an error if called, can be used with instantiateTestbench if no inputs should be "free" */
  private def noUninitialized(sym: BVSymbol, ii: Int): Option[BVExpr] =
    throw new RuntimeException(s"Uninitialized input $sym@$ii")
}

private case class AngelicVars(vars: Seq[AngelicVar])

private case class AngelicVar(change: String, value: String, width: Int, isCond: Boolean) {
  require(width > 0)
  def changeSym: BVSymbol = BVSymbol(change, 1)
  def valueSym:  BVSymbol = BVSymbol(value, width)
}

private class AngelicInstrumentation() {
  private var counter = 0
  private val vars = mutable.ListBuffer[AngelicVar]()

  /** adds angelic variables to a transition system
    * - we add values for
    *   - 1) assignments to named signals not starting with `_`
    *   - 2) conditional assignments
    */
  def run(sys: TransitionSystem): (TransitionSystem, AngelicVars) = {
    counter = 0; vars.clear()

    val iteSignals = mutable.HashSet[String]()
    val signals = sys.signals.map { s =>
      if (s.e.isInstanceOf[BVIte]) { iteSignals.add(s.name) }
      val visitedE = onExpr(s.e, iteSignals).asInstanceOf[BVExpr]
      val e = if (s.name.startsWith("_")) { visitedE }
      else { makeVar(visitedE, iteSignals) }
      s.copy(e = e)
    }

    // turn value vars into inputs
    val inputs = sys.inputs ++ vars.map(_.valueSym)

    (sys.copy(signals = signals, inputs = inputs), AngelicVars(vars.toList))
  }

  private def onExpr(e: SMTExpr, isIteSignal: String => Boolean): SMTExpr = e match {
    case BVIte(cond, a, b) =>
      val visitedA = onExpr(a, isIteSignal).asInstanceOf[BVExpr]
      val visitedB = onExpr(b, isIteSignal).asInstanceOf[BVExpr]
      BVIte(makeCondVar(cond), makeVar(visitedA, isIteSignal), makeVar(visitedB, isIteSignal))
    case other => SMTExprMap.mapExpr(other, onExpr(_, isIteSignal))

  }

  private def makeVar(expr: BVExpr, isIteSignal: String => Boolean): BVExpr =
    if (isIte(expr, isIteSignal)) { expr }
    else { makeVar(expr, isCond = false) }

  private def isIte(e: SMTExpr, isIteSignal: String => Boolean): Boolean = e match {
    case _: BVIte | _: ArrayIte => true
    case SMTSymbol(name) if isIteSignal(name) => true
    case _                                    => false
  }

  private def makeCondVar(expr: BVExpr): BVExpr = makeVar(expr, isCond = true)

  private def makeVar(expr: BVExpr, isCond: Boolean): BVExpr = {
    val change = s"_p$counter"
    val value = s"_a$counter"
    counter += 1
    val v = AngelicVar(change, value, expr.width, isCond)
    vars.append(v)
    BVIte(v.changeSym, v.valueSym, expr)
  }
}
