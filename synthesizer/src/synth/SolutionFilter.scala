package synth

import maltese.mc.{IsBad, IsConstraint, IsOutput, Signal, TransitionSystem}
import maltese.smt.{
  BVEqual,
  BVExpr,
  BVExtend,
  BVNot,
  BVSlice,
  BVSymbol,
  Namespace,
  SMTExpr,
  SMTExprMap,
  SMTSymbol,
  SolverContext
}

import scala.collection.mutable
import scala.util.control.Breaks.{break, breakable}

object SolutionFilter {
  import synth.Synthesizer.applySynthAssignment

  /** Sort solutions in order to make results more deterministic
    * (across solvers, or in case the solver is not fully deterministic).
    */
  def sort(solutions: Seq[Solution]): Seq[Solution] = {
    val solutionsWithKey = solutions.map(s => toKey(s) -> s)
    solutionsWithKey.sortBy(_._1).map(_._2)
  }

  private def toKey(sol: Solution): String = {
    sol.assignments.map { case (name, value) => s"$name -> $value" }.mkString("|")
  }

  def run(
    ctx:       SolverContext,
    sys:       TransitionSystem,
    tb:        Testbench,
    config:    Config,
    solutions: Seq[Solution]
  ): Seq[Solution] = {
    // generate repaired system for each solutions
    val all = solutions.map(sol => Data(sol, applySynthAssignment(sys, sol.assignments)))

    // filter out solutions that generate exactly the same system
    val synFiltered = syntacticFilter(all)
    if (synFiltered.length < all.length && config.verbose) {
      println(s"Syntactic filter removed ${all.length - synFiltered.length}/${all.length}")
    }

    // filter out solutions that are combinatorially equivalent
    val combEquivFiltered = combEquivFilter(ctx, config.verbose, synFiltered)
    if (combEquivFiltered.length < synFiltered.length && config.verbose) {
      println(s"Syntactic filter removed ${synFiltered.length - combEquivFiltered.length}/${synFiltered.length}")
    }

    combEquivFiltered.map(_.solution)
  }

  private case class Data(solution: Solution, sys: TransitionSystem)

  /** Remove solutions that result in exactly the same system code. (same syntax!) */
  private def syntacticFilter(solutions: Seq[Data]): Seq[Data] = {
    val seen = mutable.HashSet[String]()
    solutions.filter { s =>
      val key = s.sys.serialize
      val isDuplicate = seen.contains(key)
      seen.add(key)
      !isDuplicate
    }
  }

  /** Remove duplicates that are combinatorially equivalent, i.e, all output and next functions are the same. */
  private def combEquivFilter(ctx: SolverContext, verbose: Boolean, solutions: Seq[Data]): Seq[Data] = {
    var unique = List[Data]()
    solutions.foreach { newSolution =>
      breakable {
        unique.foreach { oldSolution =>
          if (isCombEquiv(ctx, verbose, oldSolution, newSolution)) {
            break // we are done here, this is a duplicate
          }
        }
        // no duplicate
        unique = unique :+ newSolution
      }
    }
    // return all unique solutions
    unique
  }

  private def isCombEquiv(ctx: SolverContext, verbose: Boolean, a: Data, b: Data): Boolean = {
    // first we check to make sure that all states and outputs have the same name
    val outputs = a.sys.signals.filter(_.lbl == IsOutput).map(o => o.name -> o.e.tpe)
    val outputsB = b.sys.signals.filter(_.lbl == IsOutput).map(o => o.name -> o.e.tpe)
    if (outputs != outputsB) {
      if (verbose) println(s"Outputs do not match: $outputs vs $outputsB")
      return false
    }
    val states = a.sys.states.map(s => s.name -> s.sym.tpe)
    val statesB = b.sys.states.map(s => s.name -> s.sym.tpe)
    if (states != statesB) {
      if (verbose) println(s"States do not match: $states vs $statesB")
      return false
    }

    // create a miter circuit
    val miter = buildMiter(statesToIO(a.sys), statesToIO(b.sys))

    // run combinatorial check

    false
  }

  private val APref = "a_"
  private val BPref = "b_"

  /** This function requires that `a` and `b` have the exact same outputs. */
  private def buildMiter(a: TransitionSystem, b: TransitionSystem): TransitionSystem = {
    require(a.states.isEmpty, "states should have been transformed into I/O")
    require(b.states.isEmpty, "states should have been transformed into I/O")

    // combine systems
    val aPref = prefixSys(APref)(a)
    val bPref = prefixSys(BPref)(b)
    val combined = combineSys("miter", aPref, bPref)
    val namespace = Namespace(combined)

    // we assume that all inputs take on the same value
    val aInputs = a.inputs.map(i => i.name -> i).toMap
    val inputConstraints = b.inputs
      // we only care about inputs that are available in both systems
      .filter(i => aInputs.contains(i.name))
      .map { origBInput =>
        val origAInput = aInputs(origBInput.name)
        val aInput = origAInput.rename(APref + origAInput.name)
        val bInput = origBInput.rename(BPref + origBInput.name)
        Signal(name = namespace.newName("inp_eq"), e = InEq(aInput, bInput), lbl = IsConstraint)
      }

    // we assert that all outputs are the same
    val aOutputs = a.signals.filter(_.lbl == IsOutput).map(s => s.name -> s).toMap
    val outputsTheSame = b.signals.map { origBSignal =>
      val origASignal = aOutputs(origBSignal.name)
      // TODO: make this work with arrays
      val aOutput = SMTSymbol.fromExpr(APref + origASignal.name, origASignal.e).asInstanceOf[BVSymbol]
      val bOutput = SMTSymbol.fromExpr(BPref + origBSignal.name, origBSignal.e).asInstanceOf[BVSymbol]
      Signal(name = namespace.newName("output_eq"), e = BVNot(OutEq(aOutput, bOutput)), lbl = IsBad)
    }

    val miter = combined.copy(signals = combined.signals ++ inputConstraints ++ outputsTheSame)
    miter
  }

  /** Encodes the notion of input equivalence for our miter. */
  private def InEq(a: BVExpr, b: BVExpr): BVExpr = {
    if (a.width == b.width) { BVEqual(a, b) }
    else if (a.width > b.width) { BVEqual(BVSlice(a, hi = b.width - 1, lo = 0), b) }
    else { BVEqual(a, BVSlice(b, hi = a.width - 1, lo = 0)) }
  }

  /** Encodes the notion of output equivalence for our miter. */
  private def OutEq(a: BVExpr, b: BVExpr): BVExpr = {
    if (a.width == b.width) { BVEqual(a, b) }
    else if (a.width > b.width) { BVEqual(a, BVExtend(b, a.width - b.width, signed = false)) }
    else { BVEqual(BVExtend(a, b.width - a.width, signed = false), b) }
  }

}

/** Turns the current state into an input and the next state into an output. */
private object statesToIO {
  def apply(sys: TransitionSystem): TransitionSystem = {
    val namespace = Namespace(sys)
    val nextOutputs = sys.states.flatMap { state =>
      state.next.map { next =>
        Signal(namespace.newName(state.name + "_next"), e = next, lbl = IsOutput)
      }
    }
    // TODO: this only works if there are no arrays in the system...
    val stateInputs = sys.states.map(_.sym).map(_.asInstanceOf[BVSymbol])
    sys.copy(states = List(), inputs = sys.inputs ++ stateInputs, signals = sys.signals ++ nextOutputs)
  }
}

/** Combines two systems into one. Does **not** resolve name conflicts! */
private object combineSys {
  def apply(name: String, a: TransitionSystem, b: TransitionSystem): TransitionSystem =
    TransitionSystem(
      name = name,
      inputs = a.inputs ++ b.inputs,
      signals = a.signals ++ b.signals,
      states = a.states ++ b.states
    )
}

/** Adds a prefix to all signals in the system. */
private object prefixSys {
  def apply(prefix: String)(sys: TransitionSystem): TransitionSystem = {
    val inputs = sys.inputs.map(i => i.copy(name = prefix + i.name))
    val states = sys.states.map(s => s.copy(sym = onExpr(prefix)(s.sym).asInstanceOf[SMTSymbol]))
    val signals = sys.signals.map(s => s.copy(name = prefix + s.name, e = onExpr(prefix)(s.e)))
    sys.copy(inputs = inputs, signals = signals, states = states)
  }

  private def onExpr(prefix: String)(e: SMTExpr): SMTExpr = e match {
    case sym: SMTSymbol => sym.rename(prefix + sym.name)
    case other => SMTExprMap.mapExpr(other, onExpr(prefix))
  }
}
