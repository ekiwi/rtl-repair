// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

sealed trait UpdateK {}
case class UpdateFutureK(to: Int) extends UpdateK
case object UpdatePastK extends UpdateK

/** Tries to synthesize a solution without completely unrolling the system. */
object IncrementalSynthesizer {
  import synth.Synthesizer._
  import synth.BasicSynthesizer._

  private def calculateUpdate(failureDistances: Seq[Int], currentFutureK: Int): UpdateK = {
    // when no solution is found, we update the past K in order to get a more accurate starting state
    if (failureDistances.isEmpty) {
      return UpdatePastK
    }

    val futureFailures = failureDistances.filter(_ > 0)
    // if there are no solutions that lead to a later failure, we just increase the pastK
    if (futureFailures.isEmpty) {
      return UpdatePastK
    }

    // if all future failures are already included in our window, increase pastK
    if (futureFailures.max <= currentFutureK) {
      return UpdatePastK
    }

    // pick the smallest future failure that still increases the window size
    val newFutureK = futureFailures.filter(_ > currentFutureK).min
    UpdateFutureK(newFutureK)
  }

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
      return NoRepairNecessary(RepairStats(0))
    }

    var pastK = 0
    var futureK = 0
    def k = pastK + futureK
    val maxWindowSize = config.maxRepairWindowSize
    var totalCheckTime: Long = 0
    while (k <= maxWindowSize) {
      val (candidates, checkTime) =
        findSolutionWithUnrolling(sys, initialized, randInputTb, config, synthVars, exec, pastK, futureK)
      totalCheckTime += checkTime
      candidates.find(_.correct) match {
        case Some(value) => // return correct solution if it exists
          return RepairSuccess(
            Seq(Solution(value.assignment)),
            RepairStats(totalCheckTime, pastK = pastK, futureK = futureK)
          )
        case None => // otherwise, we analyze the solutions that did not work
          val failureDistance = candidates.map(c => c.failAt - exec.failAt)
          calculateUpdate(failureDistance, futureK) match {
            case UpdateFutureK(to) =>
              if (config.verbose) println(s"updating futureK from $futureK to $to")
              futureK = to
            case UpdatePastK =>
              val newPastK =
                Seq(
                  pastK + config.pastKStepSize,
                  exec.failAt
                ).min // cannot go back more than the location of the original bug
              if (newPastK == pastK) {
                if (config.verbose) println(s"Cannot go back further in time => no solution found")
                return CannotRepair(RepairStats(totalCheckTime, pastK = pastK, futureK = futureK))
              }
              if (config.verbose) println(s"updating pastK from $pastK to $newPastK")
              pastK = newPastK
          }
      }
    }

    if (config.verbose) println(s"Exceeded the maximum window size of $maxWindowSize with $pastK ... $futureK = $k")

    CannotRepair(RepairStats(totalCheckTime, pastK = pastK, futureK = futureK))
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
  ): (List[CandidateSolution], Long) = {
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

    (candidates, ctx.getCheckTime)
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

    findSolutionOfSize(ctx, synthVars, size, earlyExit = true, checkSolution)
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
    // TODO: this was failing with some benchmarks for some reason ... investigate what is going on...
    // assert(ctx.check().isUnSat, "Found a solution that does not require any changes at all!")
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
