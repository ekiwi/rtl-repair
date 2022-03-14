// Copyright 2020-2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.sym

import maltese.mc._
import maltese.smt._

import scala.collection.mutable

object MultiSeSymEngine {
  def apply(sys: TransitionSystem, noInit: Boolean = false, opts: Options = Options.Default): MultiSeSymEngine =
    new MultiSeSymEngine(sys, noInit, opts)
}

class MultiSeSymEngine private (sys: TransitionSystem, noInit: Boolean, opts: Options) {
  private val inputs = sys.inputs.map(i => i.name -> i).toMap
  private val states = sys.states.map(s => s.sym.name -> s).toMap
  private val signals = sys.signals.map(s => s.name -> s).toMap
  private val validCellName = (sys.inputs.map(_.name) ++ sys.states.map(_.name) ++ sys.signals.map(_.name)).toSet
  private val getWidth = (sys.inputs.map(i => i.name -> i.width) ++
    sys.states.map(_.sym).collect { case BVSymbol(name, width) => name -> width } ++
    sys.signals.collect { case maltese.mc.Signal(name, e: BVExpr, _) => name -> e.width }).toMap
  private val mems =
    sys.states.map(_.sym).collect { case ArraySymbol(name, indexWidth, dataWidth) => name -> (indexWidth, dataWidth) }
  private val getIndexWidth = mems.map(m => m._1 -> m._2._1).toMap
  private val getDataWidth = mems.map(m => m._1 -> m._2._2).toMap
  private val results = mutable.ArrayBuffer[mutable.HashMap[String, ValueSummary]]()

  /** edges from result to arguments */
  private val uses = mutable.HashMap[Cell, List[Cell]]()
  private implicit val ctx = new SymbolicContext(opts)

  def signalAt(name: String, step: Int): ValueSummary = signalAt(Cell(name, step))
  def signalAt(name: String, index: BigInt, step: Int): BVValueSummary = {
    assert(validCellName(name), f"Unknown cell $name")
    val indexVs = BVValueSummary(BVLiteral(index, getIndexWidth(name)))
    val array = signalAt(Cell(name, step)).asInstanceOf[ArrayValueSummary]
    BVValueSummary.read(array, indexVs)
  }

  private def signalAt(cell: Cell): ValueSummary = {
    val frame = getFrame(cell.step)
    val r = frame.getOrElseUpdate(cell.signal, computeCell(cell))
    if (r.size > 1000) {
      println(s"WARN: ${cell.id}.size = ${r.size} > 1k")
    }
    // println(s"$name@$step: $r")
    r
  }

  /** removes the result from this cell as well as any cells that depend on it */
  private def invalidate(cell: Cell): Unit = {
    // if the step has not been computed yet, there is nothing to invalidate
    if (results.size < cell.step + 1) return

    // remove the result from the frame
    val frame = results(cell.step)
    frame.remove(cell.signal)

    // remove any cells that depend on this cell
    uses.get(cell) match {
      case None =>
      case Some(Nil) =>
        uses.remove(cell)
      case Some(u) =>
        u.foreach(invalidate)
        uses.remove(cell)
    }
  }

  /** allocates the frame if necessary */
  private def getFrame(step: Int): mutable.HashMap[String, ValueSummary] = {
    if (results.size < step + 1) {
      (0 to (step - results.size)).foreach(_ => results.append(mutable.HashMap()))
    }
    results(step)
  }

  // resets value of signal and any signals derived from it
  def invalidate(name: String, step: Int): Unit = {
    assert(validCellName(name), f"Unknown cell $name")
    val cell = Cell(name, step)
    invalidate(cell)
  }

  def set(name: String, step: Int, value: ValueSummary): Unit = {
    assert(validCellName(name), f"Unknown cell $name")
    val cell = Cell(name, step)
    invalidate(cell)
    val frame = getFrame(cell.step)
    frame(name) = value
  }

  def set(name: String, step: Int, value: BigInt): BVValueSummary = {
    assert(validCellName(name), f"Unknown cell $name")
    val vs = BVValueSummary(BVLiteral(value, getWidth(name)))
    set(name, step, vs)
    vs
  }

  def set(name: String, step: Int, value: SMTExpr): ValueSummary = {
    assert(validCellName(name), f"Unknown cell $name")
    val vs = value match {
      case a: ArrayExpr =>
        assert(a.indexWidth == getIndexWidth(name))
        assert(a.dataWidth == getDataWidth(name))
        ArrayValueSummary(a)
      case b: BVExpr =>
        assert(b.width == getWidth(name), s"value width is ${b.width}, signal $name expected ${getWidth(name)}")
        BVValueSummary(b)
    }
    set(name, step, vs)
    vs
  }

  def set(name: String, step: Int, index: BigInt, value: BigInt): Unit = {
    assert(validCellName(name), f"Unknown cell $name")
    val indexVs = BVValueSummary(BVLiteral(index, getIndexWidth(name)))
    val dataVs = BVValueSummary(BVLiteral(value, getDataWidth(name)))
    val cell = Cell(name, step)
    val old = signalAt(cell).asInstanceOf[ArrayValueSummary]
    invalidate(cell)
    val frame = getFrame(cell.step)
    frame(name) = ArrayValueSummary.store(old, indexVs, dataVs)
  }

  private def computeCell(cell: Cell): ValueSummary = {
    val name = cell.signal
    if (signals.contains(name)) {
      eval(signals(name).e, cell)
    } else if (inputs.contains(name)) {
      inputAt(cell)
    } else if (states.contains(name)) {
      stateAt(cell)
    } else {
      throw new RuntimeException(s"Unknown signal ${cell.id}")
    }
  }
  private def eval(expr: SMTExpr, cell: Cell): ValueSummary = expr match {
    case sym: SMTSymbol =>
      val prevCell = cell.copy(signal = sym.name)
      // track cell dependencies
      uses(prevCell) = cell +: uses.getOrElse(prevCell, List())
      signalAt(prevCell)
    case l: BVLiteral => BVValueSummary(l)
    case u: BVUnaryExpr => BVValueSummary.unary(eval(u.e, cell).asInstanceOf[BVValueSummary], u.reapply)
    case u: BVBinaryExpr =>
      BVValueSummary.binary(
        eval(u.a, cell).asInstanceOf[BVValueSummary],
        eval(u.b, cell).asInstanceOf[BVValueSummary],
        u.reapply
      )
    case BVIte(cond, tru, fals) =>
      BVValueSummary.ite(
        eval(cond, cell).asInstanceOf[BVValueSummary],
        eval(tru, cell).asInstanceOf[BVValueSummary],
        eval(fals, cell).asInstanceOf[BVValueSummary]
      )
    case ArrayIte(cond, tru, fals) =>
      ArrayValueSummary.ite(
        eval(cond, cell).asInstanceOf[BVValueSummary],
        eval(tru, cell).asInstanceOf[ArrayValueSummary],
        eval(fals, cell).asInstanceOf[ArrayValueSummary]
      )
    case ArrayRead(array, index) =>
      BVValueSummary.read(
        eval(array, cell).asInstanceOf[ArrayValueSummary],
        eval(index, cell).asInstanceOf[BVValueSummary]
      )
    case ArrayStore(array, index, data) =>
      ArrayValueSummary.store(
        eval(array, cell).asInstanceOf[ArrayValueSummary],
        eval(index, cell).asInstanceOf[BVValueSummary],
        eval(data, cell).asInstanceOf[BVValueSummary]
      )
    case ArrayConstant(e, indexWidth) => ArrayValueSummary(eval(e, cell).asInstanceOf[BVValueSummary], indexWidth)
    case other                        => throw new RuntimeException(s"Unexpected expression: $other")
  }

  private def stateAt(cell: Cell): ValueSummary = {
    val state = states(cell.signal)
    if (cell.step == 0) {
      if (state.init.isDefined && !noInit) {
        signalAt(state.name + ".init", 0)
      } else {
        stateInit(state)
      }
    } else {
      assert(cell.step > 0)
      signalAt(Cell(state.name + ".next", cell.step - 1))
    }
  }

  private def stateInit(state: State): ValueSummary = {
    val name = state.name + "@0"
    getSymbol(name, state.sym) match {
      case b: BVSymbol    => BVValueSummary(b)
      case a: ArraySymbol => ArrayValueSummary(a)
    }
  }

  private def getSymbol(name: String, template: SMTExpr): SMTSymbol = symbols.getOrElseUpdate(
    name, {
      val s = SMTSymbol.fromExpr(name, template)
      ctx.declare(s)
      s
    }
  )

  private def inputAt(cell: Cell): BVValueSummary = {
    val sym = getSymbol(cell.id, inputs(cell.signal)).asInstanceOf[BVSymbol]
    BVValueSummary(sym)
  }
  private def symbols = mutable.HashMap[String, SMTSymbol]()

  def makeBVSymbol(name: String, width: Int): BVValueSummary = {
    symbols.get(name) match {
      case Some(sym: BVSymbol) =>
        assert(sym.width == width)
        BVValueSummary(sym)
      case None =>
        val sym = BVSymbol(name, width)
        ctx.declare(sym)
        symbols(name) = sym
        BVValueSummary(sym)
    }
  }

  def printStatistics(): Unit = {
    ctx.printStatistics()
  }
}

private case class Cell(signal: String, step: Int) {
  def id: String = signal + "@" + step
}
