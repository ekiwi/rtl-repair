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
    // random undefined inputs
    val randInputTb = Testbench.addRandomInput(sys, tb, rnd)
    // disable all synthesis variables
    val noChange = noSynth(initialized)

    // execute testbench on system
    if (config.verbose) println("Executing system with testbench to find first failing output")
    val exec = Testbench.run(
      noChange,
      randInputTb,
      verbose = config.verbose,
      earlyExitAfter = 4
      // vcd = Some(os.pwd / "fail.vcd")
    )
    if (!exec.failed) {
      if (config.verbose) println("No failure. System seems to work without any changes.")
      return NoRepairNecessary
    }

    var pastK = 0
    var futureK = 0
    def k = pastK + futureK
    val maxWindowSize = 32
    while (k <= maxWindowSize) {
      val candidates = findSolutionWithUnrolling(sys, initialized, randInputTb, config, synthVars, exec, pastK, futureK)
      candidates.find(_.correct) match {
        case Some(value) => // return correct solution if it exists
          return RepairSuccess(Seq(Solution(value.assignment)))
        case None => // otherwise, we analyze the solutions that did not work
          val failureDistance = candidates.map(c => c.failAt - exec.failAt)
          val maxFailureDistance = (0 +: failureDistance).max
          if (maxFailureDistance > futureK) {
            if (config.verbose) println(s"updating futureK from $futureK to $maxFailureDistance")
            futureK = maxFailureDistance
          } else {
            val newPastK = Seq(pastK + 2, exec.failAt).min // cannot go back more than the location of the original bug
            if (newPastK == pastK) {
              if (config.verbose) println(s"Cannot go back further in time => no solution found")
              return CannotRepair
            }
            if (config.verbose) println(s"updating pastK from $pastK to $newPastK")
            pastK = newPastK
          }
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
    pastK:       Int,
    futureK:     Int
  ): List[CandidateSolution] = {
    val k = pastK + futureK
    if (config.verbose) println(s"Searching for solution with unrolling of pastK=$pastK, futureK = $futureK, k=$k")

    // start k steps before failure
    val start = Seq(exec.failAt - pastK, 0).max
    val startValues = exec.values(start)
    val sysWithStartValues = setInitValues(sys, startValues)

    // ensure that we can concretely replay the failure
    val shortTb = tb.slice(start, start + k + 1)
    sanityCheckErrorWithSim(sysWithStartValues, shortTb, config.verbose, pastK)

    // start solver and declare system
    val ctx = startSolver(config)
    // declare synthesis variables
    synthVars.declare(ctx)
    val enc = encodeSystem(sysWithStartValues, ctx, config)

    // unroll for k, applying the appropriate inputs and outputs
    instantiateTestbench(ctx, enc, sysWithStartValues, shortTb, noUninitialized _, assertDontAssumeOutputs = false)
    sanityCheckErrorWithSolver(ctx, synthVars)

    // find a minimal solutions
    val candidates = synthesizeMultiple(ctx, synthVars, config.verbose, checkSolution(initialized, tb, config))
    ctx.close()

    candidates
  }

  /** throws an error if called, can be used with instantiateTestbench if no inputs should be "free" */
  private def noUninitialized(sym: BVSymbol, ii: Int): Option[BVExpr] =
    throw new RuntimeException(s"Uninitialized input $sym@$ii")

  private def checkSolution(
    initialized: TransitionSystem,
    tb:          Testbench,
    config:      Config
  )(assignment:  Assignment
  ): Int = {
    if (config.verbose) println(s"Solution: " + getChangesInAssignment(assignment).mkString(", "))
    val withFix = applySynthAssignment(initialized, assignment)
    val fixedExec =
      Testbench.run(withFix, tb, verbose = config.verbose, earlyExitAfter = 1) //, vcd = Some(os.pwd / "repaired.vcd"))
    if (fixedExec.failed) {
      if (config.verbose) println(s"New failure at ${fixedExec.failAt}")
      fixedExec.failAt
    } else {
      if (config.verbose) println("Works!")
      -1
    }
  }

  private def setInitValues(sys: TransitionSystem, values: Map[String, BigInt]): TransitionSystem = {
    val states = sys.states.map { st =>
      values.get(st.name) match {
        case Some(value) =>
          val sym = st.sym.asInstanceOf[BVSymbol]
          st.copy(init = Some(BVLiteral(value, sym.width)))
        case None => st
      }
    }
    sys.copy(states = states)
  }

  /** tries to enumerate all minimal solutions */
  private def synthesizeMultiple(
    ctx:           SolverContext,
    synthVars:     SynthVars,
    verbose:       Boolean,
    checkSolution: Assignment => Int
  ): List[CandidateSolution] = {
    val solution = synthesize(ctx, synthVars, verbose) match {
      case Some(values) => values
      case None         => return List() // no solution
    }

    // check size of solution
    val size = countChangesInAssignment(solution)

    findSolutionOfSize(ctx, synthVars, size, checkSolution)
  }

  type Assignment = List[(String, BigInt)]
  private case class CandidateSolution(assignment: Assignment, failAt: Int = -1) {
    def failed:  Boolean = failAt >= 0
    def correct: Boolean = !failed
  }

  /** Finds solutions of size [[size]]. Aborts as soon as a correct solution is found. */
  private def findSolutionOfSize(
    ctx:           SolverContext,
    synthVars:     SynthVars,
    size:          Int,
    checkSolution: Assignment => Int
  ): List[CandidateSolution] = {
    // restrict size of solution to known minimal size
    ctx.push()
    performNChanges(ctx, synthVars.change, size)

    // keep track of solutions
    var solutions = List[CandidateSolution]()

    // search for new solutions until none left
    var done = false
    while (!done) {
      ctx.check() match {
        case IsSat =>
          val assignment = synthVars.readAssignment(ctx)
          blockSolution(ctx, assignment)
          val failAt = checkSolution(assignment)
          val candidate = CandidateSolution(assignment, failAt)
          solutions = candidate +: solutions
          if (candidate.correct) {
            // early exit when a working solution is found
            done = true
          }
        case IsUnSat   => done = true
        case IsUnknown => done = true
      }
    }
    ctx.pop()

    // return evaluated candidate solutions
    solutions
  }

  private def blockSolution(ctx: SolverContext, assignment: Assignment): Unit = {
    val changes = assignment.filter(t => isChangeSynthName(t._1)).map {
      case (name, value) if value == 0 => BVNot(BVSymbol(name, 1))
      case (name, _)                   => BVSymbol(name, 1)
    }
    val constraint = BVNot(BVAnd(changes))
    ctx.assert(constraint)
  }

  private def applySynthAssignment(sys: TransitionSystem, assignment: Assignment): TransitionSystem = {
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

  private def sanityCheckErrorWithSolver(ctx: SolverContext, synthVars: SynthVars): Unit = {
    // make sure that the shortened system actually fails!
    // TODO: this check is not necessary and is only used for debugging
    ctx.push()
    performNChanges(ctx, synthVars.change, 0)
    assert(ctx.check().isUnSat, "Found a solution that does not require any changes at all!")
    ctx.pop()
  }

  private def sanityCheckErrorWithSim(
    sysWithStartValues: TransitionSystem,
    shortTb:            Testbench,
    verbose:            Boolean,
    pastK:              Int
  ): Unit = {
    val replayExec =
      Testbench.run(
        noSynth(sysWithStartValues),
        shortTb,
        verbose = verbose
      ) // , vcd = Some(os.pwd / "short_replay.vcd"))
    assert(replayExec.failed, "cannot replay failure!")
    assert(replayExec.failAt == pastK, s"the replay should always fail at exactly k=$pastK")
  }
}
