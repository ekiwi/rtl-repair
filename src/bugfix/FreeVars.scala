package bugfix

import maltese.mc._
import maltese.smt._

case class FreeVars(stateInit: Seq[(String, SMTSymbol)], inputs: Seq[((String, Int), BVSymbol)]) {
  def allSymbols: Seq[BVSymbol] = stateInit.map(_._2.asInstanceOf[BVSymbol]) ++ inputs.map(_._2)
  def readValues(ctx: SolverContext): Seq[(String, BigInt)] = {
    allSymbols.map(s => s.name -> ctx.getValue(s).get)
  }
  def addConstraints(ctx: SolverContext, values: Seq[(String, BigInt)]): Unit = {
    val getSym = allSymbols.map(s => s.name -> s).toMap
    values.foreach { case (name, value) =>
      val sym = getSym(name)
      ctx.assert(BVEqual(sym, BVLiteral(value, sym.width)))
    }
  }
}

object FreeVars {
  /** Looks at the Transition System and Testbench to figure out what free variables are needed. */
  def findFreeVars(sys: TransitionSystem, tb: Testbench, namespace: Namespace): FreeVars = {
    val stateInit = sys.states.flatMap {
      case State(sym, None, _) =>
        val v = sym.rename(namespace.newName(sym.name + "_init"))
        Some(sym.name -> v)
      case _ => None
    }
    val inputs = tb.values.zipWithIndex.flatMap { case (row, ii) =>
      val isDefined = row.zip(tb.signals).filter(_._1.isDefined).map(_._2).toSet
      // create free var for each undefined input
      sys.inputs.filterNot(i => isDefined(i.name)).map{ i =>
        (i.name, ii) -> i.rename(namespace.newName(i.name + "_at_" + ii))
      }
    }
    FreeVars(stateInit, inputs)
  }

  /** add the state init free variables to the transition system */
  def addStateInitFreeVars(sys: TransitionSystem, vars: FreeVars): TransitionSystem = {
    val getStateVar = vars.stateInit.toMap
    val states = sys.states.map { state =>
      getStateVar.get(state.name) match {
        case Some(value) =>
          assert(state.init.isEmpty)
          state.copy(init = Some(value))
        case None => state
      }
    }
    sys.copy(states = states)
  }
}
