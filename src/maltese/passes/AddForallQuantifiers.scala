// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes
import maltese.mc
import maltese.smt

case class QuantifiedVariable(sym: smt.BVSymbol, start: Int, end: Int)

object AddForallQuantifiers {
  def name = "AddForallQuantifiers"

  def run(sys: mc.TransitionSystem, quantified: Iterable[QuantifiedVariable]): mc.TransitionSystem = {
    if (quantified.isEmpty) return sys
    val variables: Map[smt.SMTSymbol, QuantifiedVariable] = quantified.map(v => v.sym -> v).toMap

    // We will only be able to properly generate btor and SMT if the forall and the variable are in the same
    // expression.
    // E.g. `node x : bv<1> = forall(i : bv<2>, eq(i, i))` is ok,
    // `node y : bv<1> = eq(i,i) ; node x : bv<1> = forall(i : bv<2>, y)` is not.
    // For simplicity's sake we just inline all nodes
    val eliminate = new DeadCodeElimination()
    val inlinedSys = eliminate.run(new Inline(inlineEverything = true).run(sys))

    // we remove all inputs that are actually quantified variables
    val inputs = inlinedSys.inputs.filterNot(variables.contains)

    // we quantify over any variable that is part of the expression
    val signals = inlinedSys.signals.map {
      case s @ mc.Signal(_, e: smt.BVExpr, mc.IsBad) =>
        s.copy(e = smt.BVNot(addAllQuantifiers(variables)(smt.BVNot(e))))
      case s @ mc.Signal(_, e: smt.BVExpr, _) if e.width == 1 => s.copy(e = addAllQuantifiers(variables)(e))
      case s => assertNoVars(s.e, variables.keySet); s
    }

    // check that there are no quantified state updates
    inlinedSys.states.foreach { s =>
      s.init.foreach(assertNoVars(_, variables.keySet))
      s.next.foreach(assertNoVars(_, variables.keySet))
    }

    inlinedSys.copy(inputs = inputs, signals = signals)
  }

  private def assertNoVars(e: smt.SMTExpr, variables: Set[smt.SMTSymbol]): Unit = {
    val symbols = Analysis.findSymbols(e).toSet
    assert(symbols.intersect(variables).isEmpty)
  }

  private def addAllQuantifiers(variables: Map[smt.SMTSymbol, QuantifiedVariable])(e: smt.BVExpr): smt.BVExpr = {
    val symbols = Analysis.findSymbols(e).toSet
    val localVariables = symbols.intersect(variables.keySet)
    localVariables.foldLeft(e)((expr, v) => addQuantifier(e, variables(v)))
  }

  private def addQuantifier(e: smt.BVExpr, v: QuantifiedVariable): smt.BVExpr = {
    val guard = variableGuard(v)
    if (guard == smt.True()) {
      smt.BVForall(v.sym, e)
    } else {
      smt.BVForall(v.sym, smt.BVImplies(guard, e))
    }
  }

  private def variableGuard(v: QuantifiedVariable): smt.BVExpr = {
    val max = (1 << v.sym.width) - 1
    val lower = if (v.start > 0) {
      smt.BVComparison(smt.Compare.GreaterEqual, v.sym, smt.BVLiteral(v.start, v.sym.width), signed = false)
    } else { smt.True() }
    val upper = if (v.end < max) {
      smt.BVNot(smt.BVComparison(smt.Compare.Greater, v.sym, smt.BVLiteral(v.end, v.sym.width), signed = false))
    } else { smt.True() }
    smt.BVAnd(List(lower, upper))
  }
}
