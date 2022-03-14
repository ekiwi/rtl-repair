// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt.solvers

import maltese.smt._
import org.scalatest.flatspec.AnyFlatSpec

// can be instantiated for every supported solver
abstract class BasicSolverSpec(sol: Solver) extends AnyFlatSpec {
  behavior.of(sol.name)

  // this is the example from the Yices2ApiSpec
  it should "check a small bitvector example" in {
    val (a, b) = (BVSymbol("a", 8), BVSymbol("b", 8))
    val a_gt_b = BVComparison(Compare.Greater, a, b, signed = false)
    val a_lt_2 = BVNot(BVComparison(Compare.GreaterEqual, a, BVLiteral(2, 8), signed = false))
    val b_gt_2 = BVComparison(Compare.Greater, b, BVLiteral(2, 8), signed = false)

    val solver = sol.createContext()
    solver.setLogic("QF_BV")
    solver.runCommand(DeclareFunction(a, Seq()))
    solver.runCommand(DeclareFunction(b, Seq()))

    // assert a > b and a < 2 and b > 2 --> UNSAT
    solver.assert(a_gt_b)
    solver.assert(a_lt_2)

    solver.push()
    solver.assert(b_gt_2)
    assert(solver.check(false).isUnSat)
    solver.pop()

    // the above is equivalent to
    assert(solver.check(b_gt_2, false).isUnSat)

    // assert a > b and a < 2 --> SAT
    assert(solver.check(true).isSat)

    // get the model
    val a_value = solver.queryModel(a).get
    val b_value = solver.queryModel(b).get

    assert(a_value < 2)
    assert(a_value > b_value)

    solver.close()
  }
}

class Z3SMTLibBasicSpec extends BasicSolverSpec(Z3SMTLib)
class Yices2SMTLibBasicSpec extends BasicSolverSpec(Yices2SMTLib)
class CVC4SMTLibBasicSpec extends BasicSolverSpec(CVC4SMTLib)
