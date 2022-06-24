// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>
package maltese.mc

import maltese.smt._

class UnrollSmtEncoding(sys: TransitionSystem) extends TransitionSystemSmtEncoding {
  override def defineHeader(ctx: SolverContext): Unit = ???

  override def init(ctx: SolverContext): Unit = ???

  override def unroll(ctx: SolverContext): Unit = ???

  override def getConstraint(name: String): BVExpr = ???

  override def getAssertion(name: String): BVExpr = ???

  override def getSignalAt(sym: BVSymbol, k: Int): BVExpr = ???

  override def getSignalAt(sym: ArraySymbol, k: Int): ArrayExpr = ???
}
