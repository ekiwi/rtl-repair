// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._
import synth.Synthesizer.{encodeSystem, isChangeSynthName}

/** Unrolls the system completely. This is the simplest approach, but has scalability issues for larger benchmarks. */
object BasicSynthesizer {
  import synth.Synthesizer.{countChanges, countChangesInAssignment, startSolver}

  def doRepair(sys: TransitionSystem, tb: Testbench, synthVars: SynthVars, config: Config): RepairResult = {
    val ctx = startSolver(config)
    val namespace = Namespace(sys)

    // declare synthesis variables
    synthVars.declare(ctx)

    // find free variables for the original system and declare them
    val freeVars = FreeVars.findFreeVars(sys, tb, namespace)
    freeVars.allSymbols.foreach(sym => ctx.runCommand(DeclareFunction(sym, List())))

    // find assignments to free variables that will make the testbench fail
    ctx.push()
    synthVars.assumeNoChange(ctx)
    val freeVarAssignment = findFreeVarAssignment(ctx, sys, tb, freeVars, config) match {
      case Some(value) => value
      case None        => ctx.close(); return NoRepairNecessary // testbench does not in fact fail
    }
    ctx.pop()
    assert(ctx.stackDepth == 0)

    ctx.push()
    // use the failing assignment for free vars
    freeVars.addConstraints(ctx, freeVarAssignment)

    // instantiate the testbench with inputs _and_ outputs assumed to be correct
    instantiateTestbench(ctx, sys, tb, freeVars, assertDontAssumeOutputs = false, config = config)

    // try to synthesize constants
    val minimalSolution = synthesize(ctx, synthVars, config.verbose) match {
      case Some(value) => Solution(value)
      case None        => return CannotRepair
    }

    val solutions = config.sampleUpToSize match {
      case Some(upTo) =>
        val size = countChangesInAssignment(minimalSolution.assignments)
        sampleMultipleSolutions(ctx, synthVars, size, size + upTo)
      case None => Seq(minimalSolution)
    }
    if (config.verbose) println(s"[Basic] found ${solutions.length} solutions")

    ctx.pop()

    // check to see if the synthesized constants work
    if (config.checkCorrectForAll) {
      checkCorrectForAll(ctx, synthVars, sys, tb, freeVars, config, solutions)
    }

    ctx.close()
    RepairSuccess(solutions)
  }

  private def checkCorrectForAll(
    ctx:       SolverContext,
    synthVars: SynthVars,
    sys:       TransitionSystem,
    tb:        Testbench,
    freeVars:  FreeVars,
    config:    Config,
    solutions: Seq[Solution]
  ): Unit = {
    solutions.foreach { case Solution(results) =>
      ctx.push()
      synthVars.assumeAssignment(ctx, results.toMap)
      findFreeVarAssignment(ctx, sys, tb, freeVars, config) match {
        case Some(value) =>
          throw new RuntimeException(
            s"TODO: the solution we found does not in fact work for all possible free variable assignments :("
          )
        case None => // all good, no more failure
      }
      ctx.pop()
    }
  }

  private def sampleMultipleSolutions(
    ctx:       SolverContext,
    synthVars: SynthVars,
    minSize:   Int,
    maxSize:   Int
  ): Seq[Solution] = {
    require(minSize > 0)
    require(maxSize >= minSize)
    var solutions = List[Solution]()
    (minSize to maxSize).foreach { size =>
      val candidates = findSolutionOfSize(ctx, synthVars, size, earlyExit = false)
      val newSolutions = candidates.filter(_.correct).map(c => Solution(c.assignment))
      solutions = solutions ++ newSolutions
    }
    solutions
  }

  type Assignment = Seq[(String, BigInt)]

  case class CandidateSolution(assignment: Assignment, failAt: Int = -1) {
    def failed: Boolean = failAt >= 0

    def correct: Boolean = !failed
  }

  /** Finds solutions of size `size`. If `earlyExit` is true, it will abort as soon as one working solution is found. */
  def findSolutionOfSize(
    ctx:           SolverContext,
    synthVars:     SynthVars,
    size:          Int,
    earlyExit:     Boolean,
    checkSolution: Assignment => Int = (_ => -1) // by default we assume that all solutions work
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
          if (candidate.correct && earlyExit) {
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

  def blockSolution(ctx: SolverContext, assignment: Assignment): Unit = {
    val changes = assignment.filter(t => isChangeSynthName(t._1)).map {
      case (name, value) if value == 0 => BVNot(BVSymbol(name, 1))
      case (name, _)                   => BVSymbol(name, 1)
    }
    val constraint = BVNot(BVAnd(changes))
    ctx.assert(constraint)
  }

  /** Searches for an assignment of free variables that minimizes the changes in the synthesis variables */
  def synthesize(
    ctx:       SolverContext,
    synthVars: SynthVars,
    verbose:   Boolean
  ): Option[List[(String, BigInt)]] = {
    val success = synthesize(ctx, synthVars.change, verbose = verbose)
    if (success) {
      val result = Some(synthVars.readAssignment(ctx))
      ctx.pop() // pop after reading
      result
    } else {
      if (verbose) println("No possible solution found. Cannot repair. :(")
      ctx.close()
      None
    }
  }

  /** Searches for an assignment of free variables that minimizes the number of true values in minimize */
  def synthesize(
    ctx:      SolverContext,
    minimize: Seq[BVExpr],
    verbose:  Boolean
  ): Boolean = {
    minimize.foreach(m => assert(m.width == 1, s"$m"))
    if (ctx.solver.supportsSoftAssert) { maxSmtSynthesis(ctx, minimize, verbose) }
    else { customSynthesis(ctx, minimize, verbose) }
  }

  private def maxSmtSynthesis(
    ctx:      SolverContext,
    minimize: Seq[BVExpr],
    verbose:  Boolean
  ): Boolean = {
    ctx.push()
    // try to minimize the change
    minimize.foreach(m => ctx.softAssert(BVNot(m)))

    // try to synthesize constants
    ctx.check() match {
      case IsSat   => true
      case IsUnSat => false
      case IsUnknown =>
        ctx.close()
        throw new RuntimeException(s"Unknown result from solver.")
    }
  }

  /** uses multiple calls to a regular SMT solver which does not support MaxSMT natively to minimize the number of changes in a solution */
  private def customSynthesis(
    ctx:      SolverContext,
    minimize: Seq[BVExpr],
    verbose:  Boolean
  ): Boolean = {
    // we expect there to be a frame that can be removed after exiting synthesis
    ctx.push()
    // first we check to see if any solution exists at all or if we cannot repair
    // (as is often the case if the repair template does not actually work for the problem we are trying to solve)
    val maxAssignment = ctx.check() match {
      case IsSat => // OK
        minimize.map(m => ctx.getValue(m).get)
      case IsUnSat =>
        return false
      case IsUnknown => ctx.close(); throw new RuntimeException(s"Unknown result from solver.")
    }
    val maxSize = maxAssignment.sum
    if (verbose) println(s"Solution with $maxSize changes found.")
    assert(maxSize > 0)
    if (maxSize == 1) { // if by chance we get a 1-change solution, there is not more need to search for a solution
      return true
    }

    // no we are going to search from 1 to N to find the smallest number of changes that will make this repair work
    val ns = 1 until minimize.length
    ns.foreach { n =>
      if (verbose) println(s"Searching for solution with $n changes")
      performNChanges(ctx, minimize, n)
      ctx.check() match {
        case IsSat     => return true
        case IsUnSat   => // continue
        case IsUnknown => ctx.close(); throw new RuntimeException(s"Unknown result from solver.")
      }
      ctx.pop()
      ctx.push()
    }
    throw new RuntimeException(s"Should not get here!")
  }

  def performNChanges(ctx: SolverContext, minimize: Seq[BVExpr], n: Int): Unit = {
    require(n >= 0)
    require(n <= minimize.length)
    val sum = countChanges(minimize)
    val constraint = BVEqual(sum, BVLiteral(n, sum.width))
    ctx.assert(constraint)
  }

  /** find assignments to free variables that will make the testbench fail */
  private def findFreeVarAssignment(
    ctx:      SolverContext,
    sys:      TransitionSystem,
    tb:       Testbench,
    freeVars: FreeVars,
    config:   Config
  ): Option[Seq[(String, BigInt)]] = {
    ctx.push()
    instantiateTestbench(ctx, sys, tb, freeVars, assertDontAssumeOutputs = true, config = config)
    ctx.check() match {
      case IsSat => // OK
      case IsUnSat =>
        return None
      case IsUnknown => throw new RuntimeException(s"Unknown result from solver.")
    }
    val freeVarAssignment = freeVars.readValues(ctx)
    if (config.verbose) {
      println("Assignment for free variables which makes the testbench fail:")
      val hideUnnamedInputs = true
      if (hideUnnamedInputs) {
        println("(hiding un-named inputs starting with _input)")
        freeVarAssignment.filterNot(_._1.startsWith("_input")).foreach { case (name, value) =>
          println(s" - $name = $value")
        }
      } else {
        freeVarAssignment.foreach { case (name, value) => println(s" - $name = $value") }
      }
    }
    ctx.pop()
    Some(freeVarAssignment)
  }

  /** Unrolls the system and adds all testbench constraints. */
  def instantiateTestbench(
    ctx:                     SolverContext,
    sys:                     TransitionSystem,
    tb:                      Testbench,
    freeVars:                FreeVars,
    assertDontAssumeOutputs: Boolean,
    config:                  Config
  ): Unit = {
    val sysWithInitVars = FreeVars.addStateInitFreeVars(sys, freeVars)

    // load system and communicate to solver
    val encoding = encodeSystem(sysWithInitVars, ctx, config)

    // get some meta data for testbench application
    val getFreeInputVar = freeVars.inputs.toMap
    def getFreeInputConstraint(sym: BVSymbol, ii: Int): Option[BVExpr] = Some(getFreeInputVar(sym.name -> ii))
    instantiateTestbench(ctx, encoding, sysWithInitVars, tb, getFreeInputConstraint _, assertDontAssumeOutputs)
  }

  /** Unrolls the system and adds all testbench constraints. Returns symbols for all undefined initial states and inputs. */
  def instantiateTestbench(
    ctx:                     SolverContext,
    encoding:                TransitionSystemSmtEncoding,
    sys:                     TransitionSystem,
    tb:                      Testbench,
    getFreeInputConstraint:  (BVSymbol, Int) => Option[BVExpr],
    assertDontAssumeOutputs: Boolean
  ): Unit = {

    // get some meta data for testbench application
    val signalWidth = (
      sys.inputs.map(i => i.name -> i.width) ++
        sys.signals.filter(_.lbl == IsOutput).map(s => s.name -> s.e.asInstanceOf[BVExpr].width)
    ).toMap
    val tbSymbols = tb.signals.map(name => BVSymbol(name, signalWidth(name)))
    val isInput = sys.inputs.map(_.name).toSet

    // unroll system k-1 times
    tb.values.drop(1).foreach(_ => encoding.unroll(ctx))

    // collect input assumption and assert them
    val inputAssumptions = tb.values.zipWithIndex.flatMap { case (values, ii) =>
      values.zip(tbSymbols).flatMap {
        case (value, sym) if isInput(sym.name) =>
          val signal = encoding.getSignalAt(sym, ii)
          value match {
            case None =>
              getFreeInputConstraint(sym, ii).map(v => BVEqual(signal, v))
            case Some(num) =>
              Some(BVEqual(signal, BVLiteral(num, sym.width)))
          }
        case _ => None
      }
    }.toList
    ctx.assert(BVAnd(inputAssumptions))

    // collect output constraints and either assert or assume them
    val outputAssertions = tb.values.zipWithIndex.flatMap { case (values, ii) =>
      values.zip(tbSymbols).flatMap {
        case (value, sym) if !isInput(sym.name) =>
          val signal = encoding.getSignalAt(sym, ii)
          value match {
            case Some(num) =>
              Some(BVEqual(signal, BVLiteral(num, sym.width)))
            case None => None // no constraint
          }
        case _ => None
      }
    }.toList
    if (assertDontAssumeOutputs) {
      ctx.assert(BVNot(BVAnd(outputAssertions)))
    } else {
      ctx.assert(BVAnd(outputAssertions))
    }
  }
}

case class SynthVars(change: List[BVSymbol], free: List[SMTSymbol]) {
  require(change.forall(_.width == 1), "change variables need to all be boolean")
  require(
    free.forall(_.isInstanceOf[BVSymbol]),
    "currently only BV symbols are supported, array support should be possible with some engineering work"
  )
  def declare(ctx:        SolverContext): Unit = vars.foreach(sym => ctx.runCommand(DeclareFunction(sym, List())))
  def assumeNoChange(ctx: SolverContext): Unit = change.foreach { sym =>
    ctx.assert(BVNot(sym))
  }
  def minimizeChange(ctx: SolverContext): Unit = change.foreach { sym =>
    ctx.softAssert(BVNot(sym))
  }
  def vars: List[BVSymbol] = change ++ free.map(_.asInstanceOf[BVSymbol])
  def readAssignment(ctx: SolverContext): List[(String, BigInt)] = vars.map { sym =>
    sym.name -> ctx.getValue(sym).get
  }
  def assumeAssignment(ctx: SolverContext, assignment: Map[String, BigInt]): Unit = vars.foreach { sym =>
    val value = assignment(sym.name)
    ctx.assert(BVEqual(sym, BVLiteral(value, sym.width)))
  }
  def isEmpty: Boolean = change.isEmpty && free.isEmpty
}
