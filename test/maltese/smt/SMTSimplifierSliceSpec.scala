// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

/** Slice simplification gets its own spec since it is so important
  *  for recovering boolean operations out of word level operations.
  */
class SMTSimplifierSliceSpec extends SMTSimplifierBaseSpec {
  behavior.of("SMTSimplifier")

  it should "simplify slice no-op" in {
    assert(simplify(BVSlice(bv("a", 3), 2, 0)) == bv("a", 3))
    assert(simplify(BVSlice(bv("a", 13), 12, 0)) == bv("a", 13))
  }

  it should "simplify slice of slice" in {
    assert(
      simplify(BVSlice(BVSlice(bv("a", 3), 2, 1), 1, 1)) ==
        BVSlice(bv("a", 3), 2, 2)
    )
    assert(
      simplify(BVSlice(BVSlice(BVSlice(bv("a", 5), 4, 1), 3, 1), 2, 2)) ==
        BVSlice(bv("a", 5), 4, 4)
    )
  }

  it should "simplify slice on a literal" in {
    assert(simplify(BVSlice(BVLiteral(3, 32), 31, 1)) == BVLiteral(1, 31))
  }

  it should "simplify non-overlapping slice of concat(3'b11, a : bv<2>)" in {
    val word = BVConcat(BVLiteral(3, 3), bv("a", 2))
    assert(word.toString == "concat(3'b11, a)")
    assert(simplify(BVSlice(word, 4, 2)).toString == "3'b11")
    assert(simplify(BVSlice(word, 4, 3)).toString == "2'b1")
    assert(simplify(BVSlice(word, 1, 0)).toString == "a")
    assert(simplify(BVSlice(word, 1, 1)).toString == "a[1]")
  }

  it should "simplify overlapping slice of concat(3'b11, a : bv<2>)" in {
    val word = BVConcat(BVLiteral(3, 3), bv("a", 2))
    assert(simplify(BVSlice(word, 4, 0)).toString == "concat(3'b11, a)")
    assert(simplify(BVSlice(word, 4, 1)).toString == "concat(3'b11, a[1])")
    assert(simplify(BVSlice(word, 3, 0)).toString == "concat(2'b11, a)")
  }

  it should "simplify non-overlapping slice of concat(a : BV<2>, 3'b11, b : bv<2>)" in {
    // There are two different ways to nest the concat of three values. Both should be simplified.
    val longLeft = BVConcat(BVConcat(bv("a", 2), BVLiteral(3, 3)), bv("b", 2))
    val longRight = BVConcat(bv("a", 2), BVConcat(BVLiteral(3, 3), bv("b", 2)))

    assert(simplify(BVSlice(longLeft, 6, 5)).toString == "a")
    assert(simplify(BVSlice(longRight, 6, 5)).toString == "a")

    assert(simplify(BVSlice(longLeft, 4, 2)).toString == "3'b11")
    assert(simplify(BVSlice(longRight, 4, 2)).toString == "3'b11")

    assert(simplify(BVSlice(longLeft, 1, 0)).toString == "b")
    assert(simplify(BVSlice(longRight, 1, 0)).toString == "b")
  }

  it should "simplify overlapping slice of concat(a : BV<2>, 3'b11, b : bv<2>)" in {
    // There are two different ways to nest the concat of three values. Both should be simplified.
    val longLeft = BVConcat(BVConcat(bv("a", 2), BVLiteral(3, 3)), bv("b", 2))
    val longRight = BVConcat(bv("a", 2), BVConcat(BVLiteral(3, 3), bv("b", 2)))

    assert(simplify(BVSlice(longLeft, 6, 2)).toString == "concat(a, 3'b11)")
    assert(simplify(BVSlice(longRight, 6, 2)).toString == "concat(a, 3'b11)")

    assert(simplify(BVSlice(longLeft, 6, 3)) == simplify(BVConcat(bv("a", 2), BVSlice(BVLiteral(3, 3), 2, 1))))
    assert(simplify(BVSlice(longRight, 6, 3)) == simplify(BVConcat(bv("a", 2), BVSlice(BVLiteral(3, 3), 2, 1))))

    assert(simplify(BVSlice(longLeft, 5, 2)).toString == "concat(a[0], 3'b11)")
    assert(simplify(BVSlice(longRight, 5, 2)).toString == "concat(a[0], 3'b11)")
  }

  it should "push slice into ite" in {
    val (a, b, c) = (bv("a", 4), bv("b", 4), bv("c", 1))
    assert(simplify(BVSlice(BVIte(c, a, b), 0, 0)).toString == "ite(c, a[0], b[0])")
  }

  it should "simplify concatenation of adjacent slices" in {
    val a = bv("a", 32)

    assert(simplify(BVConcat(BVSlice(a, 20, 19), BVSlice(a, 18, 0))) == BVSlice(a, 20, 0))
    assert(simplify(BVConcat(BVSlice(a, 31, 19), BVSlice(a, 18, 0))) == a)
  }

  Seq(Op.Add, Op.Sub, Op.Or, Op.And, Op.Xor).foreach { op =>
    it should s"push slice into ${op.toString}" in {
      val a = bv("a", 32)
      val b = bv("b", 32)

      assert(simplify(BVSlice(BVOp(op, a, b), 30, 0)) == BVOp(op, BVSlice(a, 30, 0), BVSlice(b, 30, 0)))
      if (op == Op.Add || op == Op.Sub) {
        // cannot cut off lsb since the information might flow into msb
        assert(simplify(BVSlice(BVOp(op, a, b), 30, 2)) == BVSlice(BVOp(op, a, b), 30, 2))
      } else {
        assert(simplify(BVSlice(BVOp(op, a, b), 30, 2)) == BVOp(op, BVSlice(a, 30, 2), BVSlice(b, 30, 2)))
      }
      // this is an example for when this optimization is useful
      assert(simplify(BVSlice(BVOp(op, BVExtend(a, 34, false), BVExtend(b, 34, false)), 31, 0)) == BVOp(op, a, b))
    }
  }

}
