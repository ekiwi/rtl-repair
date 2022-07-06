// Copyright 2020-2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import maltese.smt._
import treadle.vcd

import scala.collection.mutable

/** A new and improved transition system simulator. */
class TransitionSystemSim(sys: TransitionSystem, vcdFilename: Option[os.Path]) {
  sys.signals.foreach(s => assert(s.e.isInstanceOf[BVExpr], s"array signals are not supported! $s"))
  sys.states.foreach(s => assert(s.sym.isInstanceOf[BVExpr], s"array states are not supported! $s"))

  private val data = mutable.HashMap[String, BigInt]()
  private var stepCount = -1
  def getStepCount: Int = stepCount

  private def getDefault(width: Int): BigInt = 0

  private def init(): Unit = {
    stepCount = 0
    // init inputs to their default value
    sys.inputs.foreach { in =>
      data(in.name) = getDefault(in.width)
    }
    // init states to their init value or default
    sys.states.foreach { st =>
      data(st.name) = st.init match {
        case Some(value: BVExpr) => eval(value)
        case None => getDefault(st.sym.asInstanceOf[BVSymbol].width)
      }
    }
    vcdWriter.foreach(updateVcd)
    vcdWriter.foreach(_.incrementTime())
    // update signals
    updateSignals()
  }

  def poke(name:   String, value: BigInt): Unit = data(name) = value
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
        case Some(value: BVExpr) =>
          data(st.name) = eval(value)
        case None => // ignore
      }
    }
    stepCount += 1
    vcdWriter.foreach(updateVcd)
    vcdWriter.foreach(_.incrementTime())
  }

  def peek(name: String): BigInt = data(name)

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
    sys.signals.foreach { sig =>
      val value = eval(sig.e.asInstanceOf[BVExpr])
      data(sig.name) = value
    }
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

  private val evalCtx: SMTEvalCtx = new SMTEvalCtx {
    override def getBVSymbol(name:        String): BigInt = data(name)
    override def getArraySymbol(name:     String): ArrayValue = ???
    override def startVariableScope(name: String, value: BigInt): Unit = ???
    override def endVariableScope(name:   String): Unit = ???
    override def constArray(indexWidth:   Int, value: BigInt): ArrayValue = ???
  }

  // VCD support
  private val vcdWriter = vcdFilename.map(_ => initVcd())

  private def initVcd(): vcd.VCD = {
    val vv = vcd.VCD(sys.name)
    vv.addWire("Step", 64)
    val allBV = sys.inputs ++ sys.states.map(_.sym.asInstanceOf[BVSymbol]) ++ sys.signals.map(s =>
      BVSymbol(s.name, s.e.asInstanceOf[BVExpr].width)
    )
    allBV.foreach(s => vv.addWire(s.name, s.width))
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
