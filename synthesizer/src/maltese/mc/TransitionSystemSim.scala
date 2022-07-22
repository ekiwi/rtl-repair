// Copyright 2020-2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import maltese.smt._
import treadle.vcd

import scala.collection.mutable

/** A new and improved transition system simulator. */
class TransitionSystemSim(sys: TransitionSystem, vcdFilename: Option[os.Path]) {
  private val allSymbols = sys.inputs ++ sys.states.map(_.sym) ++ sys.signals.map(_.sym)
  private val bvSymbols = allSymbols.collect{ case b: BVSymbol => b }
  private val arraySymbols = allSymbols.collect{ case a: ArraySymbol => a }
  private val data = mutable.HashMap[String, BigInt]()
  private val memData = mutable.HashMap[String, Memory]()
  private var stepCount = -1
  def getStepCount: Int = stepCount

  private def getDefault(width: Int): BigInt = 0
  private def assignDefault(name: String, tpe: SMTType): Unit = tpe match {
    case BVType(width) => data(name) = getDefault(width)
    case ArrayType(indexWidth, dataWidth) =>
      memData(name) = evalCtx.constArray(indexWidth, getDefault(dataWidth)).asInstanceOf[Memory]
  }

  private def init(): Unit = {
    stepCount = 0
    // init inputs to their default value
    sys.inputs.foreach { in =>
      data(in.name) = getDefault(in.width)
    }
    // initialize all states to a default value in order to be able to update the signals
    sys.states.foreach(st => assignDefault(st.name, st.sym.tpe))
    // update signals because memory init might depend on it
    updateSignals()
    // init states to their init value or default
    sys.states.foreach { st =>
      st.init match {
        case Some(value) => assignSignal(st.name, value)
        case None => assignDefault(st.name, st.sym.tpe)
      }
    }
    vcdWriter.foreach(updateVcd)
    vcdWriter.foreach(_.incrementTime())
    // update signals
    updateSignals()
  }

  def poke(name:   String, value: BigInt): Unit = {
    assert(data.contains(name))
    data(name) = value
  }
  def poke(inputs: Map[String, BigInt]): Unit = inputs.foreach { case (name, value) => poke(name, value) }

  def update(): Unit = {
    // update signals
    updateSignals()
    vcdWriter.foreach(updateVcd)
  }

  def step(): Unit = {
    vcdWriter.foreach(_.incrementTime())
    // update states to next step
    sys.states.foreach { st =>
      st.next match {
        case Some(value) =>
          assignSignal(st.name, value)
        case None => // ignore TODO: should get some sort of default value
      }
    }
    stepCount += 1
    vcdWriter.foreach(updateVcd)
    vcdWriter.foreach(_.incrementTime())
  }

  def peek(name: String): BigInt = data(name)
  def peekMem(name: String): IndexedSeq[BigInt] = memData(name).data

  def getSnapshot(): StateSnapshot = {
    Snapshot(data.toMap, memData.toMap.map{ case (n, v) => n -> v.data })
  }
  def restoreSnapshot(snapshot: StateSnapshot): Unit = {
    val snap = snapshot.asInstanceOf[Snapshot]
    data.clear() ; data ++= snap.data
    memData.clear()
    snap.mem.foreach { case (n, v) => memData(n) = new Memory(v) }
  }

  // adds an arbitrary signal and value to the output vcd if one is being produced, ignored otherwise
  def printSignal(name: String, value: BigInt, width: Int = 1): Unit =
    vcdWriter.foreach(_.wireChanged(name, value, width))

  def finish(): Unit = {
    updateSignals()
    vcdWriter.foreach { writer =>
      writer.incrementTime()
      writer.write(vcdFilename.get.toString())
    }
  }

  private def updateSignals(): Unit = {
    sys.signals.foreach { s => assignSignal(s.name, s.e) }
  }

  // update a signal, works with both BV and Array signals
  private def assignSignal(name: String, expr: SMTExpr): Unit = expr match {
    case e: BVExpr => data(name) = eval(e)
    case e: ArrayExpr => memData(name) = evalArray(e)
  }

  private val CheckWidths = true
  private def eval(expr: BVExpr): BigInt = {
    val value = SMTExprEval.eval(expr)(evalCtx)
    if (CheckWidths) {
      val mask = (BigInt(1) << expr.width) - 1
      if ((value & mask) != value) {
        throw new RuntimeException(s"Failed to evaluate $expr!\nvalue $value does not fit into ${expr.width} bits!")
      }
    }
    value
  }
  private def evalArray(expr: ArrayExpr): Memory = SMTExprEval.evalArray(expr)(evalCtx).asInstanceOf[Memory]
  private def arrayDepth(indexWidth: Int): Int = (BigInt(1) << indexWidth).toInt

  private val evalCtx: SMTEvalCtx = new SMTEvalCtx {
    override def getBVSymbol(name:        String): BigInt = data(name)
    override def getArraySymbol(name:     String): ArrayValue = memData(name)
    override def startVariableScope(name: String, value: BigInt): Unit = ???
    override def endVariableScope(name:   String): Unit = ???
    override def constArray(indexWidth:   Int, value: BigInt): ArrayValue =
      Memory(IndexedSeq.fill(arrayDepth(indexWidth))(value))
  }

  // VCD support
  private val vcdWriter = vcdFilename.map(_ => initVcd())

  private def initVcd(): vcd.VCD = {
    val vv = vcd.VCD(sys.name)
    vv.addWire("Step", 64)
    bvSymbols.foreach(s => vv.addWire(s.name, s.width))
    vv
  }

  /** update the Vcd right before taking the next step */
  private def updateVcd(write: vcd.VCD): Unit = {
    write.wireChanged("Step", stepCount)
    data.foreach { case (name, value) => write.wireChanged(name, value) }
  }

  // start with initialized data
  init()
}

sealed trait StateSnapshot
private case class Snapshot(data: Map[String, BigInt], mem: Map[String, IndexedSeq[BigInt]]) extends StateSnapshot

private case class Memory(data: IndexedSeq[BigInt]) extends ArrayValue {
  def depth: Int = data.size
  def write(index: Option[BigInt], value: BigInt): Memory = {
    index match {
      case None => Memory(IndexedSeq.fill(depth)(value))
      case Some(ii) =>
        assert(ii >= 0 && ii < depth, s"index ($ii) needs to be non-negative smaller than the depth ($depth)!")
        Memory(data.updated(ii.toInt, value))
    }
  }
  def read(index: BigInt): BigInt = {
    assert(index >= 0 && index < depth, s"index ($index) needs to be non-negative smaller than the depth ($depth)!")
    data(index.toInt)
  }
  def ==(other: ArrayValue): Boolean = {
    assert(other.isInstanceOf[Memory])
    other.asInstanceOf[Memory].data == this.data
  }
}