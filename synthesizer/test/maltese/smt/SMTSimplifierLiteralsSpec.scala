// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

/** Constant Propagation */
class SMTSimplifierLiteralsSpec extends SMTSimplifierBaseSpec {
  behavior.of("SMTSimplifier with literals")

  import SMTSimplifierLiteralsSpec._

  it should "simplify BVExtend of literal" in {
    check(BVExtend(BVLiteral("b011"), 1, false), "4'b11")
    check(BVExtend(BVLiteral("b011"), 1, true), "4'b11")

    check(BVExtend(BVLiteral("b101"), 1, false), "4'b101")
    check(BVExtend(BVLiteral("b101"), 1, true), "4'b1101")

    check(BVExtend(BVLiteral("b101"), 3, false), "6'b101")
    check(BVExtend(BVLiteral("b101"), 3, true), "6'b111101")
  }

  it should "simplify BVSlice of literal" in {
    check(BVSlice(BVLiteral("b011"), 2, 2), "1'b0")
    check(BVSlice(BVLiteral("b011"), 1, 1), "1'b1")
    check(BVSlice(BVLiteral("b011"), 0, 0), "1'b1")
    check(BVSlice(BVLiteral("b011"), 1, 0), "2'b11")
    check(BVSlice(BVLiteral("b011"), 2, 1), "2'b1")
    check(BVSlice(BVLiteral("b011"), 2, 0), "3'b11")
  }

  it should "simplify BVNot of literal" in {
    check(BVNot(BVLiteral("b1")), "1'b0")
    check(BVNot(BVLiteral("b0")), "1'b1")
    check(BVNot(BVNot(BVLiteral("b0"))), "1'b0")

    check(BVNot(BVLiteral("b011")), "3'b100")
  }

  it should "simplify BVNegate of literal" in {
    // for 1-bit values, negation is the identity
    check(BVNegate(BVLiteral("b1")), "1'b1")
    check(BVNegate(BVLiteral("b0")), "1'b0")

    // neg(a) = add(not(a), 1)
    SomeLiterals.foreach { l =>
      check(BVNegate(l), BVOp(Op.Add, BVNot(l), BVLiteral(1, l.width)))
    }
  }

  it should "simplify BVEqual of literals" in {
    check(BVEqual(BVLiteral("b1011"), BVLiteral("b1011")), "1'b1")
    check(BVEqual(BVLiteral("b1011"), BVLiteral("b1001")), "1'b0")
  }

  // TODO: comparison

  it should "simplify add of literals" in {
    check(BVOp(Op.Add, BVLiteral("b1011"), BVLiteral("b1011")), "4'b110")
    check(BVOp(Op.Add, BVLiteral("b1011"), BVLiteral("b1001")), "4'b100")
  }

  private def check(in: SMTExpr, expected: String): Unit = {
    val actual = simplify(in).toString
    assert(actual == expected)
  }

  private def check(inA: SMTExpr, inB: SMTExpr): Unit = {
    val actual = simplify(inA).toString
    val expected = simplify(inB).toString
    assert(actual == expected)
  }
}

object SMTSimplifierLiteralsSpec {
  private val SomeLiterals = List(
    "b0",
    "b1",
    "b00",
    "b01",
    "b10",
    "b11",
    "b11111010101",
    "b111101011010101"
  ).map(BVLiteral(_))
}
