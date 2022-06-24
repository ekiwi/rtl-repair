// Copyright 2020-2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import maltese.smt._
import scala.collection.mutable

class CompactSmtEncoding(sys: TransitionSystem) extends TransitionSystemSmtEncoding {
  import SMTTransitionSystemEncoder._
  private def id(s: String): String = SMTLibSerializer.escapeIdentifier(s)
  private val stateType = id(sys.name + "_s")
  private val stateInitFun = id(sys.name + "_i")
  private val stateTransitionFun = id(sys.name + "_t")

  private val states = mutable.ArrayBuffer[UTSymbol]()

  def defineHeader(ctx: SolverContext): Unit = encode(sys).foreach(ctx.runCommand)

  private def appendState(ctx: SolverContext): UTSymbol = {
    val s = UTSymbol(s"s${states.length}", stateType)
    ctx.runCommand(DeclareFunction(s, List()))
    states.append(s)
    s
  }

  def init(ctx: SolverContext): Unit = {
    assert(states.isEmpty)
    val s0 = appendState(ctx)
    ctx.assert(BVFunctionCall(stateInitFun, List(s0), 1))
  }

  def unroll(ctx: SolverContext): Unit = {
    assert(states.nonEmpty)
    appendState(ctx)
    val tStates = states.takeRight(2).toList
    ctx.assert(BVFunctionCall(stateTransitionFun, tStates, 1))
  }

  /** returns an expression representing the constraint in the current state */
  def getConstraint(name: String): BVExpr = {
    assert(states.nonEmpty)
    val foo = id(name + "_f")
    BVFunctionCall(foo, List(states.last), 1)
  }

  /** returns an expression representing the assertion in the current state */
  def getAssertion(name: String): BVExpr = {
    assert(states.nonEmpty)
    val foo = id(name + "_f")
    BVFunctionCall(foo, List(states.last), 1)
  }

  def getSignalAt(sym: BVSymbol, k: Int): BVExpr = {
    assert(states.length > k, s"no state s$k")
    val state = states(k)
    val foo = id(sym.name + "_f")
    BVFunctionCall(foo, List(state), sym.width)
  }

  def getSignalAt(sym: ArraySymbol, k: Int): ArrayExpr = {
    assert(states.length > k, s"no state s$k")
    val state = states(k)
    val foo = id(sym.name + "_f")
    ArrayFunctionCall(foo, List(state), sym.indexWidth, sym.dataWidth)
  }
}

/** This Transition System encoding is directly inspired by yosys' SMT backend:
  * https://github.com/YosysHQ/yosys/blob/master/backends/smt2/smt2.cc
  * It if fairly compact, but unfortunately, the use of an uninterpreted sort for the state
  * prevents this encoding from working with boolector.
  * For simplicity reasons, we do not support hierarchical designs (no `_h` function).
  */
object SMTTransitionSystemEncoder {

  def encode(sys: TransitionSystem): Iterable[SMTCommand] = {
    val cmds = mutable.ArrayBuffer[SMTCommand]()
    val name = sys.name

    // declare UFs if necessary
    cmds ++= TransitionSystem.findUninterpretedFunctions(sys)

    // emit header as comments
    if (sys.header.nonEmpty) {
      cmds ++= sys.header.split('\n').map(Comment)
    }

    // declare state type
    val stateType = id(name + "_s")
    cmds += DeclareUninterpretedSort(stateType)

    // state symbol
    val State = UTSymbol("state", stateType)
    val StateNext = UTSymbol("state_n", stateType)

    // inputs and states are modelled as constants
    def declare(sym: SMTSymbol, kind: String): Unit = {
      cmds ++= toDescription(sym, kind, sys.comments.get)
      val s = SMTSymbol.fromExpr(sym.name + SignalSuffix, sym)
      cmds += DeclareFunction(s, List(State.tpe))
    }
    sys.inputs.foreach(i => declare(i, "input"))
    sys.states.foreach(s => declare(s.sym, "register"))

    // we need to know the names of all signals in order to decide whether
    // to replace a signal with a function call in replaceSymbols or not
    val isSignal = TransitionSystem.getAllNames(sys).toSet

    // signals are just functions of other signals, inputs and state
    def define(sym: SMTSymbol, e: SMTExpr, suffix: String = SignalSuffix): Unit = {
      val withReplacedSymbols = replaceSymbols(SignalSuffix, State, isSignal)(e)
      cmds += DefineFunction(sym.name + suffix, List(State), withReplacedSymbols)
    }
    sys.signals.foreach { signal =>
      val sym = signal.sym
      cmds ++= toDescription(sym, lblToKind(signal.lbl), sys.comments.get)
      val e = if (signal.lbl == IsBad) BVNot(signal.e.asInstanceOf[BVExpr]) else signal.e
      define(sym, e)
    }

    // define the next and init functions for all states
    sys.states.foreach { state =>
      assert(state.next.nonEmpty, "Next function required")
      define(state.sym, state.next.get, NextSuffix)
      // init is optional
      state.init.foreach { init =>
        define(state.sym, init, InitSuffix)
      }
    }

    def defineConjunction(e: List[BVExpr], suffix: String): Unit = {
      define(BVSymbol(name, 1), if (e.isEmpty) True() else BVAnd(e), suffix)
    }

    // the transition relation asserts that the value of the next state is the next value from the previous state
    // e.g., (reg state_n) == (reg_next state)
    val transitionRelations = sys.states.map { state =>
      val newState = replaceSymbols(SignalSuffix, StateNext, isSignal)(state.sym)
      val nextOldState = replaceSymbols(NextSuffix, State, isSignal)(state.sym)
      SMTEqual(newState, nextOldState)
    }
    // the transition relation is over two states
    val transitionExpr = if (transitionRelations.isEmpty) { True() }
    else {
      replaceSymbols(SignalSuffix, State, isSignal)(BVAnd(transitionRelations))
    }
    cmds += DefineFunction(name + "_t", List(State, StateNext), transitionExpr)

    // The init relation just asserts that all init function hold
    val initRelations = sys.states.filter(_.init.isDefined).map { state =>
      val stateSignal = replaceSymbols(SignalSuffix, State, isSignal)(state.sym)
      val initSignal = replaceSymbols(InitSuffix, State, isSignal)(state.sym)
      SMTEqual(stateSignal, initSignal)
    }
    defineConjunction(initRelations, "_i")

    // assertions and assumptions
    val assertions = sys.signals.filter(_.lbl == IsBad).map(a => replaceSymbols(SignalSuffix, State, isSignal)(a.sym))
    defineConjunction(assertions.map(_.asInstanceOf[BVExpr]), AssertionSuffix)
    val assumptions =
      sys.signals.filter(_.lbl == IsConstraint).map(a => replaceSymbols(SignalSuffix, State, isSignal)(a.sym))
    defineConjunction(assumptions.map(_.asInstanceOf[BVExpr]), AssumptionSuffix)

    cmds
  }

  private def id(s: String): String = SMTLibSerializer.escapeIdentifier(s)
  private val SignalSuffix = "_f"
  private val NextSuffix = "_next"
  private val InitSuffix = "_init"
  val AssertionSuffix = "_a"
  val AssumptionSuffix = "_u"
  private def lblToKind(lbl: SignalLabel): String = lbl match {
    case IsNode | IsInit | IsNext => "wire"
    case IsOutput                 => "output"
    // for the SMT encoding we turn bad state signals back into assertions
    case IsBad        => "assert"
    case IsConstraint => "assume"
    case IsFair       => "fair"
  }
  private def toDescription(sym: SMTSymbol, kind: String, comments: String => Option[String]): List[Comment] = {
    List(sym match {
      case BVSymbol(name, width) => Comment(s"firrtl-smt2-$kind $name $width")
      case ArraySymbol(name, indexWidth, dataWidth) =>
        Comment(s"firrtl-smt2-$kind $name $indexWidth $dataWidth")
    }) ++ comments(sym.name).map(Comment)
  }
  // All signals are modelled with functions that need to be called with the state as argument,
  // this replaces all Symbols with function applications to the state.
  private def replaceSymbols(
    suffix:   String,
    arg:      SMTSymbol,
    isSignal: Set[String],
    vars:     Set[String] = Set()
  )(e:        SMTExpr
  ): SMTExpr =
    e match {
      case BVSymbol(name, width) if isSignal(name) && !vars(name) => BVFunctionCall(id(name + suffix), List(arg), width)
      case ArraySymbol(name, indexWidth, dataWidth) if isSignal(name) && !vars(name) =>
        ArrayFunctionCall(id(name + suffix), List(arg), indexWidth, dataWidth)
      case fa @ BVForall(variable, _) =>
        SMTExprMap.mapExpr(fa, replaceSymbols(suffix, arg, isSignal, vars + variable.name))
      case other => SMTExprMap.mapExpr(other, replaceSymbols(suffix, arg, isSignal, vars))
    }
}
