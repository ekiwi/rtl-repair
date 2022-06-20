// Copyright 2021 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.sym

import maltese.mc
import maltese.mc._
import maltese.passes._
import maltese.smt

import scala.collection.mutable

class SymbolicSim(sys: TransitionSystem, renames: Map[String, String], ignoreAsserts: Boolean, seed: Long = 0) {
  private val rand = new scala.util.Random(seed)

  // we do not support assumptions at the moment
  private val assumptions = sys.signals.filter(_.lbl == IsConstraint)
  require(assumptions.isEmpty, "Assumptions are currently not supported!")

  // we need to assertion names if we want to check them
  private val assertions = sys.signals.filter(_.lbl == IsBad).map(_.name)

  // we need to cache the input assignment to retain the in the next cycle
  private val isInput = sys.inputs.map(_.name).toSet
  private val inputAssignments = mutable.HashMap[String, BVValueSummary]()

  // make the names of all inputs public
  val inputs: Seq[String] = sys.inputs.map(_.name)

  private val isMemory = sys.states.filter(_.sym.isInstanceOf[smt.ArraySymbol]).map(_.name).toSet

  private val engine = MultiSeSymEngine(sys, noInit = false)
  private var cycleCount = 0
  doCheckAsserts() // check assertions in initial state

  def step(n: Int): Unit = {
    require(n > 0)
    (0 until n).foreach { _ => step() }
  }

  def step(): Unit = {
    cycleCount += 1
    // apply any "sticky" pokes
    inputAssignments.foreach { case (signal, value) => engine.set(signal, cycleCount, value) }
    doCheckAsserts()
  }

  // convenience method
  def reset(): Unit = {
    poke("reset", 1)
    step()
    poke("reset", 0)
  }

  private def resolveSignal(signal: String): String = renames.getOrElse(signal, signal)

  def peek(signal: String): Value = {
    val name = resolveSignal(signal)
    new Value(engine.signalAt(name, cycleCount))
  }

  def peekMemory(signal: String, index: BigInt): Value = {
    val name = resolveSignal(signal)
    require(isMemory(name), s"Could not find memory $name!")
    new Value(engine.signalAt(name, index, cycleCount))
  }

  def pokeDontCare(signal: String): Unit = {
    val name = resolveSignal(signal)
    engine.invalidate(name, cycleCount)
    inputAssignments.remove(name)
  }

  def poke(signal: String, value: BigInt): Unit = {
    val name = resolveSignal(signal)
    val vs = engine.set(name, cycleCount, value)
    if (isInput(name)) { inputAssignments(name) = vs }
  }

  def poke(signal: String, value: smt.SMTExpr): Unit = {
    val name = resolveSignal(signal)
    val vs = engine.set(name, cycleCount, value)
    if (isInput(name)) { inputAssignments(name) = vs.asInstanceOf[BVValueSummary] }
  }

  def pokeMemory(signal: String, index: BigInt, value: BigInt): Unit = {
    val name = resolveSignal(signal)
    require(isMemory(name), s"Could not find memory $name!")
    engine.set(name, cycleCount, index, value)
  }

  def poke(signal: String, value: Value): Unit = {
    val name = resolveSignal(signal)
    val vs = Value.getValueSummary(value)
    engine.set(name, cycleCount, vs)
    if (isInput(name)) { inputAssignments(name) = vs.asInstanceOf[BVValueSummary] }
  }

  def makeSymbol(name: String, width: Int): Value = {
    new Value(engine.makeBVSymbol(name, width))
  }

  // assigns random concrete values to each state
  def randomizeStates(skipInitialized: Boolean = false): Unit = {
    sys.states.foreach {
      case s @ mc.State(sym: smt.BVSymbol, _, _) =>
        val value = BigInt(sym.width, rand)
        if (s.init.isEmpty || !skipInitialized) {
          poke(sym.name, value)
        }
      case s @ mc.State(sym: smt.ArraySymbol, _, _) =>
        val value = BigInt(sym.dataWidth, rand)
        val array = smt.ArrayConstant(smt.BVLiteral(value, sym.dataWidth), sym.indexWidth)
        if (s.init.isEmpty || !skipInitialized) {
          poke(sym.name, array)
        }
    }
  }

  def stepAndMonitor(n: Int, signals: Seq[String]): Unit = {
    require(n >= 0)
    (0 until n).foreach { _ =>
      printSignals(signals)
      step()
    }
    printSignals(signals)
  }

  private def printSignals(signals: Seq[String]): Unit = {
    println(s"--- Step #$cycleCount")
    signals.foreach { signal =>
      println(s"$signal: ${peek(signal)}")
    }
  }

  def assert(v: Value, msg: => String = ""): Unit = {
    val vs = Value.getValueSummary(v).asInstanceOf[BVValueSummary]
    if (vs.isSat) {
      if (vs.isConcrete) {
        throw new RuntimeException(s"Assertion always fails! $msg")
      } else {
        throw new RuntimeException(s"Assertion may fail! $msg")
      }
    }
  }

  private def doCheckAsserts(): Unit = if (!ignoreAsserts) {
    assertions.foreach { a =>
      assert(peek(a), s"$a in cycle $cycleCount")
    }
  }
}

class Value(private val e: ValueSummary) {
  def isSymbolic: Boolean = e.isSymbolic
  def isConcrete: Boolean = e.isConcrete
  def getValue: BigInt = e match {
    case b: BVValueSummary =>
      b.value match {
        case Some(v) => v
        case None    => throw new RuntimeException(s"Value is symbolic: ${b.symbolic}")
      }
    case _ =>
      throw new RuntimeException("Value is an array!")
  }

  def getSMT: smt.SMTExpr = e match {
    case b: BVValueSummary    => b.symbolic
    case a: ArrayValueSummary => a.symbolic
  }

  override def toString = e match {
    case a: ArrayValueSummary => "Value(" + a.toString + ")"
    case b: BVValueSummary =>
      b.value match {
        case Some(value) => "Value(" + value + ")"
        case None        => "Value(" + b.toString + ")"
      }
  }
}

private object Value {
  def getValueSummary(v: Value): ValueSummary = v.e
}

object SymbolicSim {
  def loadBtor(filename: os.Path): SymbolicSim = loadBtor(filename, false)

  def loadBtor(filename: os.Path, ignoreAsserts: Boolean): SymbolicSim = {
    // load transition system from file
    val sys = mc.Btor2.load(filename)
    val simplified = simplifySystem(sys)
    new SymbolicSim(simplified, renames = Map(), ignoreAsserts = ignoreAsserts)
  }

  def loadBtor(src: String, name: String): SymbolicSim = loadBtor(src, name, false)

  def loadBtor(src: String, name: String, ignoreAsserts: Boolean): SymbolicSim = {
    val sys = mc.Btor2.read(src = src, defaultName = name)
    val simplified = simplifySystem(sys)
    if (verbose) {
      println(simplified.serialize)
    }
    new SymbolicSim(simplified, renames = Map(), ignoreAsserts = ignoreAsserts)
  }

  private val verbose = false
  private def simplifySystem(sys: TransitionSystem): TransitionSystem = {
    val r = PassManager(passes).run(sys, trace = verbose)
    r
  }
  private val passes: Iterable[Pass] = Seq(
    Simplify,
    new Inline,
    new DeadCodeElimination(removeUnusedInputs = true),
    Simplify,
    new Inline,
    new DeadCodeElimination(removeUnusedInputs = true),
    Simplify
  )
}
