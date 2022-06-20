// Copyright 2020-2021 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes

import maltese.mc._
import maltese.smt._
import scala.collection.mutable

/** Replaces RHS expressions if there is a signal that computes the same expression.
  *  This can be thought of the second part of a Common Subexpression Elimination pass, where
  *  the first part would have to split expressions into more signals.
  */
object ReplaceExpressionsWithSignals extends Pass {
  override def name: String = "ReplaceExpressionsWithSymbols"

  override def run(sys: TransitionSystem): TransitionSystem = {
    val exprToSignal = new ExprMap()
    val signals = sys.signals.map { s =>
      val e = onExpr(s.e, exprToSignal)
      exprToSignal(s.e) = s.name
      if (e.eq(s.e)) { s }
      else { s.copy(e = e) }
    }
    val states = sys.states.map { s =>
      val next = s.next.map(onExpr(_, exprToSignal))
      val init = s.init.map(onExpr(_, exprToSignal))
      s.copy(next = next, init = init)
    }
    sys.copy(signals = signals, states = states)
  }

  private type ExprMap = mutable.HashMap[SMTExpr, String]

  private def onExpr(e: SMTExpr, m: ExprMap): SMTExpr = m.get(e) match {
    case Some(name) => SMTSymbol.fromExpr(name, e)
    case None       => SMTExprMap.mapExpr(e, onExpr(_, m))
  }

}
