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
    val exec = Testbench.run(noChange, tb, verbose = true)
    if (!exec.failed) {
      if (config.verbose) println("No failure. System seems to work without any changes.")
      return NoRepairNecessary
    }

    // start k steps before failure
    val k = 2
    val start = Seq(exec.failAt - k, 0).max
    val startValues = exec.values(start)
    val sysWithStartValues = setInitValues(sys, startValues)

    // start solver and declare system
    val ctx = startSolver(config)
    // declare synthesis variables
    synthVars.declare(ctx)
    val enc = encodeSystem(sys, ctx, config)

    // unroll for k, applying the appropriate inputs and outputs
    val shortTb = tb.slice(start, start + k)
    def zeroByDefault(sym: BVSymbol, ii: Int): Option[BVExpr] = Some(BVLiteral(0, sym.width))
    instantiateTestbench(ctx, enc, sysWithStartValues, shortTb, zeroByDefault _, assertDontAssumeOutputs = false)

    // make sure that the shortened system actually fails!
    ctx.push()
    performNChanges(ctx, synthVars, 0)
    assert(ctx.check().isUnSat, "Found a solution that does not require any changes at all!")
    ctx.pop()

    // check to see if a fix to the system exists that will make the outputs not fail
    synthesize(ctx, synthVars, config.verbose) match {
      case Some(value) =>
        println(s"Found solution: $value")
        val changes = value.filter(_._2 == 1).map(_._1).filter(_.startsWith(SynthChangePrefix))
        println(changes.mkString(", "))
      case None =>
        throw new NotImplementedError("TODO: do something if there is no solution!")
    }

    val solutions = synthesizeMultiple(ctx, synthVars, config.verbose)
    println(s"Found ${solutions.size} unique minimal solutions")
    solutions.foreach(s => getChangesInAssignment(s).mkString(", "))

    // println(noChange.serialize)

    ???
  }

  private def setInitValues(sys: TransitionSystem, values: Map[String, BigInt]): TransitionSystem = {
    val states = sys.states.map { st =>
      st.init match {
        case Some(_) => st
        case None =>
          val sym = st.sym.asInstanceOf[BVSymbol]
          st.copy(init = Some(BVLiteral(values(sym.name), sym.width)))
      }
    }
    sys.copy(states = states)
  }

  /** tries to enumerate all minimal solutions */
  private def synthesizeMultiple(
    ctx:       SolverContext,
    synthVars: SynthVars,
    verbose:   Boolean
  ): List[List[(String, BigInt)]] = {
    val solution = synthesize(ctx, synthVars, verbose) match {
      case Some(values) => values
      case None         => return List() // no solution
    }

    // check size of solution
    val size = countChangesInAssignment(solution)
    // restrict size of solution to known minimal size
    ctx.push()
    performNChanges(ctx, synthVars, size)

    // block and remember original solution
    blockSolution(ctx, solution)
    var solutions = List(solution)

    // search for new solutions until none left
    var done = false
    while (!done) {
      ctx.check() match {
        case IsSat =>
          val assignment = synthVars.readAssignment(ctx)
          blockSolution(ctx, assignment)
          solutions = assignment +: solutions
        case IsUnSat   => done = true
        case IsUnknown => done = true
      }
    }
    ctx.pop()
    // return all solutions found
    solutions
  }

  private def blockSolution(ctx: SolverContext, assignment: List[(String, BigInt)]): Unit = {
    val changes = assignment.filter(_._1.startsWith(SynthChangePrefix)).map {
      case (name, value) if value == 0 => BVNot(BVSymbol(name, 1))
      case (name, _)                   => BVSymbol(name, 1)
    }
    val constraint = BVNot(BVAnd(changes))
    ctx.assert(constraint)
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
