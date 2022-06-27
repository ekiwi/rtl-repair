// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

/** Takes in a Transition System with synthesis variables +  a testbench and tries to find a valid synthesis assignment.
  * - this class encodes the synthesis problem as a series of transitions systems, allowing for the use of a bounded
  * model checker to solve it
  */
object ModelCheckerSynthesizer {

  import Synthesizer.{countChanges, countChangesInAssignment, isSynthName}

  def doRepair(sys: TransitionSystem, tb: Testbench, synthVars: SynthVars, config: Config): RepairResult = {
    // create model checker
    val checker: IsModelChecker = config.checker.get

    val freeInputs = findFreeInputs(sys, tb)

    // find assignment to the free variables that will make the original system fail
    val noChangeSys = performNChanges(sys, synthVars, 0)
    val freeVarAssignment = findFreeVarAssignment(checker, noChangeSys, tb, freeInputs, config.verbose) match {
      case Some(value) => value.toMap
      case None        => return NoRepairNecessary // testbench does not in fact fail
    }

    // check to see if any solution exists at all
    // (this prevents us from having to search through all possible numbers of solutions)
    val maxSolution = findSolution(checker, sys, tb, freeVarAssignment, config.verbose) match {
      case Some(solution) => solution // ok, a solution can be found, now we need to minimize it
      case None           => return CannotRepair // no way to repair this since no solution exists
    }

    // try to see if by accident we got a minimal solution without any constraints
    val maxSize = countChangesInAssignment(maxSolution)
    if (config.verbose) println(s"Solution with $maxSize changes found.")
    assert(maxSize > 0)
    if (maxSize == 1) { // if by chance we get a 1-change solution, there is not more need to search for a solution
      return RepairSuccess(maxSolution)
    }

    // try to solve with the minimal number of changes
    val ns = 1 until synthVars.change.length
    val solution = searchForSolution(checker, sys, tb, synthVars, freeVarAssignment, ns, config.verbose)

    solution match {
      case None                     => CannotRepair
      case Some(synthVarAssignment) =>
        // check to see if the synthesized constants work
        val sysWithSolution = applySynthVarAssignment(sys, synthVarAssignment.toMap)

        findFreeVarAssignment(checker, sysWithSolution, tb, freeInputs, config.verbose) match {
          case Some(value) =>
            throw new RuntimeException(
              s"TODO: the solution we found does not in fact work for all possible free variable assignments :(\n" +
                s"${synthVarAssignment}\n${value}"
            )
          case None => // all good, no more failure
        }
        RepairSuccess(synthVarAssignment)
    }
  }

  private def searchForSolution(
    checker:           IsModelChecker,
    sys:               TransitionSystem,
    tb:                Testbench,
    synthVars:         SynthVars,
    freeVarAssignment: Map[(Int, String), BigInt],
    ns:                Iterable[Int],
    verbose:           Boolean
  ): Option[List[(String, BigInt)]] = {
    ns.foreach { n =>
      val nChangeSys = performNChanges(sys, synthVars, n)
      if (verbose) println(s"Searching for solution with $n changes")
      findSolution(checker, nChangeSys, tb, freeVarAssignment, verbose) match {
        case Some(value) =>
          return Some(value)
        case None =>
      }
    }
    None
  }

  private def findSolution(
    checker:            IsModelChecker,
    sys:                TransitionSystem,
    tb:                 Testbench,
    freeVarAssignments: Map[(Int, String), BigInt],
    verbose:            Boolean
  ): Option[List[(String, BigInt)]] = {
    val withTB = instantiateTestbench(sys, tb, assertDontAssumeOutputs = false, freeVarAssignments)
    // TODO: place this in working directory instead of making a temporary file
    val temp = os.temp(suffix = ".btor")

    val k = tb.length // we need to go to the full length because the assertion is delayed by one cycle
    checker.check(withTB, kMax = k, fileName = Some(temp.toString())) match {
      case ModelCheckFail(witness) =>
        if (verbose) println("Solution found:")
        if (false) { // debugging code
          val vcdTemp = os.temp(suffix = ".vcd")
          val sim = new TransitionSystemSimulator(withTB)
          sim.run(witness, vcdFileName = Some(vcdTemp.toString()))
          println(vcdTemp)
          println(temp)
        }
        Some(readSynthVarAssignments(sys, witness))
      case ModelCheckSuccess() =>
        None
    }
  }

  private def applySynthVarAssignment(sys: TransitionSystem, assignment: Map[String, BigInt]): TransitionSystem = {
    val states = initStates(sys.states, assignment.get)
    sys.copy(states = states)
  }

  private def readSynthVarAssignments(sys: TransitionSystem, witness: Witness): List[(String, BigInt)] = {
    sys.states.zipWithIndex.filter { case (state, _) => isSynthName(state.name) }.flatMap { case (state, index) =>
      witness.regInit.get(index).map(i => state.name -> i)
    }
  }

  private def performNChanges(sys: TransitionSystem, synthVars: SynthVars, n: Int): TransitionSystem = {
    require(n >= 0)
    require(n <= synthVars.change.length)
    val sum = countChanges(synthVars)
    val constraint = Signal(s"change_exactly_$n", BVEqual(sum, BVLiteral(n, sum.width)), IsConstraint)
    sys.copy(signals = sys.signals :+ constraint)
  }

  private def findFreeVarAssignment(
    checker:    IsModelChecker,
    sys:        TransitionSystem,
    tb:         Testbench,
    freeInputs: Seq[(Int, BVSymbol)],
    verbose:    Boolean
  ): Option[Seq[((Int, String), BigInt)]] = {
    val withTB = instantiateTestbench(sys, tb, assertDontAssumeOutputs = true, freeVarAssignments = Map())
    // TODO: place this in working directory instead of making a temporary file
    val temp = os.temp(suffix = ".btor")

    val k = tb.length - 1
    checker.check(withTB, kMax = k, fileName = Some(temp.toString())) match {
      case ModelCheckFail(witness) =>
        Some(extractFreeVarAssignment(witness, sys, freeInputs))
      case ModelCheckSuccess() =>
        if (verbose)
          println(s"System is correct for all starting states and undefined inputs.")
        None
    }
  }

  private def extractFreeVarAssignment(
    witness:    Witness,
    sys:        TransitionSystem,
    freeInputs: Seq[(Int, BVSymbol)]
  ): Seq[((Int, String), BigInt)] = {
    val regStates = sys.states.filter(_.sym.tpe.isInstanceOf[BVType])
    assert(regStates.length == sys.states.length, "Array states are currently not supported!")
    val stateAssignments = regStates.zipWithIndex.filterNot { case (s, _) => isSynthName(s.name) }.flatMap {
      case (state, index) =>
        witness.regInit.get(index).map(value => (0, state.name) -> value)
    }
    val isFreeInput = freeInputs.toSet
    val inputAssignments = witness.inputs.zipWithIndex.flatMap { case (values, step) =>
      sys.inputs.zipWithIndex.filter { case (in, _) => isFreeInput((step, in)) }.map { case (in, index) =>
        (step, in.name) -> values(index)
      }
    }
    stateAssignments ++ inputAssignments
  }

  private def instantiateTestbench(
    sys:                     TransitionSystem,
    tb:                      Testbench,
    assertDontAssumeOutputs: Boolean,
    freeVarAssignments:      Map[(Int, String), BigInt]
  ): TransitionSystem = {
    // get some meta data for testbench application
    val signalWidth = (
      sys.inputs.map(i => i.name -> i.width) ++
        sys.signals.filter(_.lbl == IsOutput).map(s => s.name -> s.e.asInstanceOf[BVExpr].width)
    ).toMap
    val tbSymbols = tb.signals.map(name => BVSymbol(name, signalWidth(name)))
    val isInput = sys.inputs.map(_.name).toSet

    // create a counter that will tell us what step we are in
    val step = BVSymbol("step", 32)

    def inStep(ii: Int): BVExpr = BVEqual(step, BVLiteral(ii, step.width))

    val stepNext = Signal("step.next", BVOp(Op.Add, step, BVLiteral(1, step.width)), IsNext)
    val stepState = State(step, Some(BVLiteral(0, step.width)), Some(stepNext.sym))

    // collect input and output constraints
    val inputConstraints = collectConstraints(tb, tbSymbols, isInput, inStep, freeVarAssignments)
    val outputConstraints = collectConstraints(tb, tbSymbols, n => !isInput(n), inStep, Map())

    // create assumptions / assertions from constraints
    val inputAssumption = Signal("input_constraints", inputConstraints, IsConstraint)
    val (outputAssertionSignals, outputCheckerStates) = if (assertDontAssumeOutputs) {
      val wrongOutputIsBad = Signal("output_assertion", BVNot(outputConstraints), IsBad)
      (Seq(wrongOutputIsBad), Seq())
    } else {
      // we want to get a counter example (which is actually an assignment to our synthesis variables
      // iff all outputs are correct
      val trackerSym = BVSymbol("output_tracker_ok", 1)
      val trackerStateNext = Signal(trackerSym.name + ".next", BVAnd(trackerSym, outputConstraints))
      val trackerState = State(trackerSym, init = Some(BVLiteral(1, 1)), next = Some(trackerStateNext.sym))
      // in the final cycle, we need to check if the output was ok for all cycles of the execution
      val correctOutputIsBad = Signal("output_constraints", BVAnd(inStep(tb.length), trackerSym), IsBad)
      (Seq(trackerStateNext, correctOutputIsBad), Seq(trackerState))
    }

    // initialize **non-synthesis** states if the have a free variable assignment
    val (synthStates, otherStates) = sys.states.partition(s => isSynthName(s.name))
    val states = initStates(otherStates, name => freeVarAssignments.get((0, name)))

    // add counter and assumptions/assertions to system
    sys.copy(
      states = synthStates ++ states :+ stepState :++ outputCheckerStates,
      signals = stepNext +: sys.signals :+ inputAssumption :++ outputAssertionSignals
    )
  }

  private def initStates(states: List[State], getAssignment: String => Option[BigInt]): List[State] = states.map {
    state =>
      getAssignment(state.name) match {
        case Some(value) =>
          assert(state.init.isEmpty)
          val width = state.sym.asInstanceOf[BVSymbol].width
          state.copy(init = Some(BVLiteral(value, width)))
        case None => state
      }
  }

  def collectConstraints(
    tb:                 Testbench,
    tbSymbols:          Seq[BVSymbol],
    include:            String => Boolean,
    inStep:             Int => BVExpr,
    freeVarAssignments: Map[(Int, String), BigInt]
  ): BVExpr = {
    val constraints = tb.values.zipWithIndex.flatMap { case (values, ii) =>
      val constraints = values
        .zip(tbSymbols)
        .flatMap {
          case (value, sym) if include(sym.name) =>
            value match {
              case None =>
                freeVarAssignments.get((ii, sym.name)) match {
                  case Some(value) =>
                    Some(BVEqual(sym, BVLiteral(value, sym.width)))
                  case None => None
                }
              case Some(num) =>
                Some(BVEqual(sym, BVLiteral(num, sym.width)))
            }
          case _ => None
        }
        .toList
      if (constraints.isEmpty) {
        None
      } else {
        Some(BVImplies(inStep(ii), BVAnd(constraints)))
      }
    }.toList
    BVAnd(constraints)
  }

  private def findFreeInputs(sys: TransitionSystem, tb: Testbench): List[(Int, BVSymbol)] = {
    tb.values.zipWithIndex.flatMap { case (row, ii) =>
      val isDefined = row.zip(tb.signals).filter(_._1.isDefined).map(_._2).toSet
      // create free var for each undefined input
      sys.inputs.filterNot(i => isDefined(i.name)).map(input => ii -> input)
    }.toList
  }
}
