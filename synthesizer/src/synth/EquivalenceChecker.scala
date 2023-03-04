// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

object EquivalenceChecker {
  import synth.Synthesizer.encodeSystem

  def isCombEquiv(config: Config, ctx: SolverContext, a: TransitionSystem, b: TransitionSystem): Boolean = {
    // first we check to make sure that all states and outputs have the same name
    val outputs = a.signals.filter(_.lbl == IsOutput).map(o => o.name -> o.e.tpe)
    val outputsB = b.signals.filter(_.lbl == IsOutput).map(o => o.name -> o.e.tpe)
    if (outputs != outputsB) {
      if (config.verbose) println(s"Outputs do not match: $outputs vs $outputsB")
      return false
    }
    val states = a.states.map(s => s.name -> s.sym.tpe)
    val statesB = b.states.map(s => s.name -> s.sym.tpe)
    if (states != statesB) {
      if (config.verbose) println(s"States do not match: $states vs $statesB")
      return false
    }

    // create a miter circuit
    val miter = buildMiter(statesToIO(a), statesToIO(b))

    // run combinatorial check
    val passed = combCheck(miter, ctx, config)
    passed
  }

  private val PrintDiff: Boolean = false

  /** Performs a combinatorial check only and returns true iff it passes. */
  private def combCheck(sys: TransitionSystem, ctx: SolverContext, config: Config): Boolean = {
    ctx.push()
    val encoding = encodeSystem(sys, ctx, config)
    // assume all constraints
    val constraints = sys.signals.filter(_.lbl == IsConstraint).map(s => encoding.getConstraint(s.name))
    constraints.foreach(ctx.assert)
    // can _any_ assert fail?
    val asserts = sys.signals.filter(_.lbl == IsBad).map(s => encoding.getAssertion(s.name))
    ctx.assert(BVNot(BVAnd(asserts)))
    val r = ctx.check()

    // only unsat means that all assertions hold
    r match {
      case IsSat =>
        if (PrintDiff) {
          sys.inputs.foreach { input =>
            println(s"${input.name} -> ${ctx.getValue(encoding.getSignalAt(input, 0)).get}")
          }
          sys.signals.filter(_.lbl == IsOutput).foreach { output =>
            println(
              s"${output.name} -> ${ctx.getValue(encoding.getSignalAt(output.sym.asInstanceOf[BVSymbol], 0)).get}"
            )
          }
          println("-------")
        }
        ctx.pop();
        false
      case IsUnSat   => ctx.pop(); true
      case IsUnknown => ctx.pop(); false
    }
  }
}

private object buildMiter {
  private val APref = "a_"
  private val BPref = "b_"

  /** This function requires that `a` and `b` have the exact same outputs. */
  def apply(a: TransitionSystem, b: TransitionSystem): TransitionSystem = {
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
    val outputsTheSame = b.signals.filter(_.lbl == IsOutput).map { origBSignal =>
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
    if (a.width == b.width) {
      BVEqual(a, b)
    } else if (a.width > b.width) {
      BVEqual(BVSlice(a, hi = b.width - 1, lo = 0), b)
    } else {
      BVEqual(a, BVSlice(b, hi = a.width - 1, lo = 0))
    }
  }

  /** Encodes the notion of output equivalence for our miter. */
  private def OutEq(a: BVExpr, b: BVExpr): BVExpr = {
    if (a.width == b.width) {
      BVEqual(a, b)
    } else if (a.width > b.width) {
      BVEqual(a, BVExtend(b, a.width - b.width, signed = false))
    } else {
      BVEqual(BVExtend(a, b.width - a.width, signed = false), b)
    }
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
