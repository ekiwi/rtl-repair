// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.sym

import com.github.javabdd.BDD
import maltese.smt._
import maltese.bdd._

class SymbolicContext(val opts: Options) {
  private val solver = opts.solver.createContext()
  solver.setLogic("QF_AUFBV")

  def isUnSat(bdd: BDD): Boolean = isUnSat(bddConverter.bddToSmt(bdd))
  def isUnSat(expr: BVExpr): Boolean = {
    assert(expr.width == 1, "satisfiability checks require a boolean formula")
    // TODO: add optimizations and caching
    // println()
    // println(expr)
    solver.check(expr, false).isUnSat
  }
  def isSat(value: BVValueSummary): Boolean = {
    assert(value.width == 1, "satisfiability checks require a boolean formula")
    value.value match {
      case Some(v) => v == 1
      case None    => solver.check(value.symbolic, produceModel = false).isSat
    }
  }
  def isValid(value: BVValueSummary): Boolean = {
    assert(value.width == 1, "validity checks require a boolean formula")
    value.value match {
      case Some(v) => v == 1
      case None    =>
        // if the inverted value cannot be true, then the original value is always valid
        solver.check(BVNot(value.symbolic), produceModel = false).isUnSat
    }
  }
  def declare(s: SMTSymbol): Unit = {
    solver.runCommand(DeclareFunction(s, Seq()))
  }

  ///////////////// BDDs
  private val bddConverter = new BDDToSMTConverter(opts.makeBdds(), opts.ConvertBooleanOpsInSmtToBdd)
  def smtToBdd(ee:  BVExpr): BDD = bddConverter.smtToBdd(ee)
  def bddToSmt(bdd: BDD):    BVExpr = bddConverter.bddToSmt(bdd)
  val tru: BDD = bddConverter.tru

  def printStatistics(): Unit = {
    println("Atoms: " + bddConverter.getCacheSize)
  }

}
