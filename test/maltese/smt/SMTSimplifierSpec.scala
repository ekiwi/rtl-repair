// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

import org.scalatest.flatspec.AnyFlatSpec

class SMTSimplifierSpec extends SMTSimplifierBaseSpec {
  behavior.of("SMTSimplifier")

  it should "simplify boolean and" in {

    assert(simplify(and(b, fals)) == fals)
    assert(simplify(and(fals, c)) == fals)

    assert(simplify(and(b, tru)) == b)
    assert(simplify(and(tru, c)) == c)

    assert(simplify(and(b, c)) == and(b, c))
  }

  // it isn't clear if simplifying these patterns is worth it
  it should "simplified advanced and patterns" ignore {
    assert(simplify(and(b, b)) == b)
    assert(simplify(and(c, c)) == c)

    assert(simplify(and(b, not(b))) == fals)
    assert(simplify(and(not(c), c)) == fals)

    assert(simplify(and(not(b), not(b))) == not(b))
  }

  it should "simplify boolean or" in {
    assert(simplify(or(b, fals)) == b)
    assert(simplify(or(fals, c)) == c)

    assert(simplify(or(b, tru)) == tru)
    assert(simplify(or(tru, c)) == tru)

    assert(simplify(or(b, c)) == or(b, c))
  }

  // it isn't clear if simplifying these patterns is worth it
  it should "simplified advanced or patterns" ignore {
    assert(simplify(or(b, b)) == b)
    assert(simplify(or(c, c)) == c)

    assert(simplify(or(b, not(b))) == tru)
    assert(simplify(or(not(c), c)) == tru)

    assert(simplify(or(not(b), not(b))) == not(b))
  }

  it should "simplify equality for booleans" in {
    // this used to trigger a bug in the Firrtl specific simplification passes
    assert(simplify(BVEqual(b, tru)) == b)
    assert(simplify(BVEqual(b, fals)) == not(b))
  }

  it should "simplify negations" in {
    assert(simplify(not(b)) == not(b))
    assert(simplify(not(not(b))) == b)
    assert(simplify(not(not(not(b)))) == not(b))
    assert(simplify(not(not(not(not(b))))) == b)
  }

  it should "simplify ITE" in {
    assert(simplify(BVIte(tru, c, b)) == c)
    assert(simplify(BVIte(fals, c, b)) == b)
    assert(simplify(BVIte(b, c, c)) == c)
  }

  it should "simplify comparison to concat(..., ...)" in {
    val (a, b, c) = (bv("a", 2), bv("b", 3), bv("c", 5))

    assert(simplify(BVEqual(c, BVConcat(a, b))).toString == "and(eq(a, c[4:3]), eq(b, c[2:0]))")
    assert(simplify(BVEqual(BVConcat(a, b), c)).toString == "and(eq(a, c[4:3]), eq(b, c[2:0]))")

    val (a0, a1) = (bv("a0", 1), bv("a1", 1))
    assert(
      simplify(BVEqual(c, BVConcat(BVConcat(a1, a0), b))).toString ==
        "and(and(eq(a1, c[4]), eq(a0, c[3])), eq(b, c[2:0]))"
    )
  }

  it should "simplify bit masks, i.e. bitwise and with a constant" in {
    val (a, b) = (bv("a", 2), bv("b", 3))

    assert(simplify(BVAnd(BVConcat(a, b), BVLiteral("b11000"))).toString == "concat(a, 3'b0)")

    assert(simplify(BVAnd(BVConcat(a, b), BVLiteral("b10000"))).toString == "concat(a[1], 4'b0)")
    assert(simplify(BVAnd(BVConcat(a, b), BVLiteral("b01000"))).toString == "concat(concat(1'b0, a[0]), 3'b0)")
    assert(simplify(BVAnd(BVConcat(a, b), BVLiteral("b00100"))).toString == "concat(concat(2'b0, b[2]), 2'b0)")
    assert(simplify(BVAnd(BVConcat(a, b), BVLiteral("b00010"))).toString == "concat(concat(3'b0, b[1]), 1'b0)")
    assert(simplify(BVAnd(BVConcat(a, b), BVLiteral("b00001"))).toString == "concat(4'b0, b[0])")
  }

  it should "simplify shifts by constants" in {
    val a = bv("a", 32)

    assert(simplify(BVOp(Op.ShiftLeft, a, BVLiteral(0, 32))) == a)
    assert(simplify(BVOp(Op.ShiftLeft, a, BVLiteral(4, 32))) == BVConcat(BVSlice(a, 27, 0), BVLiteral(0, 4)))
    assert(simplify(BVOp(Op.ShiftRight, a, BVLiteral(0, 32))) == a)
    assert(simplify(BVOp(Op.ShiftRight, a, BVLiteral(4, 32))) == BVConcat(BVLiteral(0, 4), BVSlice(a, 31, 4)))
  }

  it should "turn zero extension into a concat" in {
    val a = bv("a", 4)

    assert(simplify(BVExtend(a, 4, false)) == BVConcat(BVLiteral(0, 4), a))
    assert(simplify(BVExtend(a, 0, false)) == a)
  }

  it should "turn multiple zero extensions into a single concat" in {
    val a = bv("a", 4)

    assert(simplify(BVExtend(BVExtend(a, 4, false), 3, false)) == BVConcat(BVLiteral(0, 7), a))
  }

  it should "combine multiple sign extensions" in {
    val a = bv("a", 4)
    assert(simplify(BVExtend(BVExtend(a, 4, true), 3, true)) == BVExtend(a, 7, true))
  }

  it should "simplify a slice on a sign extension" in {
    val a = bv("a", 4)
    assert(simplify(BVSlice(BVExtend(a, 2, true), 3, 0)) == a)
    assert(simplify(BVSlice(BVExtend(a, 2, true), 3, 1)) == BVSlice(a, 3, 1))
    assert(simplify(BVSlice(BVExtend(a, 2, true), 2, 1)) == BVSlice(a, 2, 1))
    assert(simplify(BVSlice(BVExtend(a, 2, true), 4, 0)) == BVExtend(a, 1, true))
    assert(simplify(BVSlice(BVExtend(a, 2, true), 5, 0)) == BVExtend(a, 2, true))
    assert(simplify(BVSlice(BVExtend(a, 2, true), 4, 1)) == BVExtend(BVSlice(a, 3, 1), 1, true))
  }

  it should "simplify or with zero, no matter the bitwidth" in {
    val a1 = bv("a1", 1)
    val a32 = bv("a32", 32)
    assert(simplify(BVOr(a1, BVLiteral(0, 1))) == a1)
    assert(simplify(BVOr(BVLiteral(0, 1), a1)) == a1)
    assert(simplify(BVOr(a32, BVLiteral(0, 32))) == a32)
    assert(simplify(BVOr(BVLiteral(0, 32), a32)) == a32)
  }

  it should "simplify add with zero" in {
    val a = bv("a", 4)
    assert(simplify(BVOp(Op.Add, a, BVLiteral(0, 4))) == a)
    assert(simplify(BVOp(Op.Add, BVLiteral(0, 4), a)) == a)
  }
}

abstract class SMTSimplifierBaseSpec extends AnyFlatSpec {
  protected def simplify(e: SMTExpr): SMTExpr = SMTSimplifier.simplify(e)
  protected val tru = BVLiteral(1, 1)
  protected val fals = BVLiteral(0, 1)
  protected val (b, c) = (BVSymbol("b", 1), BVSymbol("c", 1))
  protected def and(a:   BVExpr, b:     BVExpr):  BVExpr = BVAnd(a, b)
  protected def or(a:    BVExpr, b: BVExpr): BVExpr = BVOr(a, b)
  protected def not(a:   BVExpr): BVExpr = BVNot(a)
  protected def bv(name: String, width: Int = 4): BVSymbol = BVSymbol(name, width)
}
