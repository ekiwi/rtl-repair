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
    if (config.verbose) println("Executing system with testbench to find first failing output")
    val exec = Testbench.run(noChange, tb, verbose = config.verbose)
    if (!exec.failed) {
      if (config.verbose) println("No failure. System seems to work without any changes.")
      return NoRepairNecessary
    }

    val ks = Seq(0, 2, 3, 4, 8, 16, 32)
    ks.filter(_ <= exec.failAt).foreach { k =>
      if (config.verbose) println(s"Searching for solution with unrolling of k=$k")
      findSolutionWithUnrolling(sys, initialized, tb, config, synthVars, exec, k) match {
        case Some(value) => return RepairSuccess(value)
        case None        =>
      }
    }

    CannotRepair
  }

  /** Try to find a solution while unrolling for up to [[k]] steps. */
  private def findSolutionWithUnrolling(
    sys:         TransitionSystem,
    initialized: TransitionSystem,
    tb:          Testbench,
    config:      Config,
    synthVars:   SynthVars,
    exec:        TestbenchResult,
    k:           Int
  ): Option[Assignment] = {
    // start k steps before failure
    val start = Seq(exec.failAt - k, 0).max
    val startValues = exec.values(start)
    val sysWithStartValues = setInitValues(sys, startValues)

    // ensure that we can concretely replay the failure
    val shortTb = tb.slice(start, start + k + 1)
    sanityCheckErrorWithSim(sysWithStartValues, shortTb, config.verbose, k)

    // start solver and declare system
    val ctx = startSolver(config)
    // declare synthesis variables
    synthVars.declare(ctx)
    val enc = encodeSystem(sysWithStartValues, ctx, config)

    // unroll for k, applying the appropriate inputs and outputs
    // TODO: zero by default might need to be updated if we do anything more fancy in the simulator
    def zeroByDefault(sym: BVSymbol, ii: Int): Option[BVExpr] = Some(BVLiteral(0, sym.width))
    instantiateTestbench(ctx, enc, sysWithStartValues, shortTb, zeroByDefault _, assertDontAssumeOutputs = false)

    sanityCheckErrorWithSolver(ctx, synthVars)

    // define how to check solution
    def checkSolution(assignment: Assignment): Boolean = {
      if (config.verbose) println(s"Solution: " + getChangesInAssignment(assignment).mkString(", "))
      val withFix = applySynthAssignment(initialized, assignment)
      val fixedExec = Testbench.run(withFix, tb, verbose = config.verbose)
      if (config.verbose) {
        if (fixedExec.failed) {
          println(s"Old failure was at ${exec.failAt}, new failure at ${fixedExec.failAt}")
        } else { println("Works!") }
      }
      !fixedExec.failed
    }

    // find a minimal solutions
    synthesizeMultiple(ctx, synthVars, config.verbose, checkSolution)
  }

  private def sanityCheckErrorWithSolver(ctx: SolverContext, synthVars: SynthVars): Unit = {
    // make sure that the shortened system actually fails!
    // TODO: this check is not necessary and is only used for debugging
    ctx.push()
    performNChanges(ctx, synthVars, 0)
    assert(ctx.check().isUnSat, "Found a solution that does not require any changes at all!")
    ctx.pop()
  }

  private def sanityCheckErrorWithSim(
    sysWithStartValues: TransitionSystem,
    shortTb:            Testbench,
    verbose:            Boolean,
    k:                  Int
  ): Unit = {
    val replayExec = Testbench.run(noSynth(sysWithStartValues), shortTb, verbose = verbose)
    assert(replayExec.failed, "cannot replay failure!")
    assert(replayExec.failAt == k, s"the replay should always fail at exactly k=$k")
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
    ctx:           SolverContext,
    synthVars:     SynthVars,
    verbose:       Boolean,
    checkSolution: Assignment => Boolean
  ): Option[Assignment] = {
    val solution = synthesize(ctx, synthVars, verbose) match {
      case Some(values) => values
      case None         => return None // no solution
    }

    // check size of solution
    val size = countChangesInAssignment(solution)

    findSolutionOfSize(ctx, synthVars, size, checkSolution)
  }

  type Assignment = List[(String, BigInt)]

  private def findSolutionOfSize(
    ctx:           SolverContext,
    synthVars:     SynthVars,
    size:          Int,
    checkSolution: Assignment => Boolean
  ): Option[Assignment] = {
    // restrict size of solution to known minimal size
    ctx.push()
    performNChanges(ctx, synthVars, size)

    // keep track of solutions
    var solutions = List[Assignment]()

    // search for new solutions until none left
    var done = false
    while (!done) {
      ctx.check() match {
        case IsSat =>
          val assignment = synthVars.readAssignment(ctx)
          blockSolution(ctx, assignment)
          solutions = assignment +: solutions
          val success = checkSolution(assignment)
          if (success) return Some(assignment)
        case IsUnSat   => done = true
        case IsUnknown => done = true
      }
    }
    ctx.pop()

    // none of the solutions seem to work on the complete testbench
    None
  }

  private def blockSolution(ctx: SolverContext, assignment: List[(String, BigInt)]): Unit = {
    val changes = assignment.filter(_._1.startsWith(SynthChangePrefix)).map {
      case (name, value) if value == 0 => BVNot(BVSymbol(name, 1))
      case (name, _)                   => BVSymbol(name, 1)
    }
    val constraint = BVNot(BVAnd(changes))
    ctx.assert(constraint)
  }

  private def applySynthAssignment(sys: TransitionSystem, assignment: List[(String, BigInt)]): TransitionSystem = {
    val nameToValue = assignment.toMap
    // this assumes that all synthesis variables states have already been removed
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym: BVSymbol if isSynthName(sym.name) =>
        val value = nameToValue(sym.name)
        BVLiteral(value, sym.width)
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
