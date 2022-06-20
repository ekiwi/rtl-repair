// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import org.scalatest.flatspec.AnyFlatSpec

class Btor2ParserSpec extends AnyFlatSpec {
  // this example if from the official btor2tools repository
  private val count2 =
    """1 sort bitvec 3
      |2 zero 1
      |3 state 1
      |4 init 1 3 2
      |5 one 1
      |6 add 1 3 5
      |7 next 1 3 6
      |8 ones 1
      |9 sort bitvec 1
      |10 eq 9 3 8
      |11 bad 10
      |""".stripMargin

  it should "parse count2 w/o inlining" in {
    val expected =
      """counter2
        |node s2 : bv<3> = 3'b0
        |init _state_0.init : bv<3> = s2
        |node s5 : bv<3> = 3'b1
        |node s6 : bv<3> = add(_state_0, s5)
        |next _state_0.next : bv<3> = s6
        |node s8 : bv<3> = 3'b111
        |node s10 : bv<1> = eq(_state_0, s8)
        |bad _bad_0 : bv<1> = s10
        |state _state_0 : bv<3>
        |  [init] _state_0.init
        |  [next] _state_0.next
        |""".stripMargin
    val sys = Btor2.read(count2, inlineSignals = false, defaultName = "counter2").serialize
    assert(sys.trim == expected.trim)
  }

  it should "parse count2 with inlining" in {
    val expected =
      """counter2
        |bad _bad_0 : bv<1> = eq(_state_0, 3'b111)
        |state _state_0 : bv<3>
        |  [init] 3'b0
        |  [next] add(_state_0, 3'b1)
        |""".stripMargin
    val sys = Btor2.read(count2, inlineSignals = true, defaultName = "counter2").serialize
    assert(sys.trim == expected.trim)
  }

  // this example if from the official btor2tools repository
  private val twocount2 =
    """1 sort bitvec 1
      |2 sort bitvec 2
      |3 input 1 turn
      |4 zero 2
      |5 state 2 a
      |6 state 2 b
      |7 init 2 5 4
      |8 init 2 6 4
      |9 one 2
      |10 add 2 5 9
      |11 add 2 6 9
      |12 ite 2 3 5 10
      |13 ite 2 -3 6 11
      |14 next 2 5 12
      |15 next 2 6 13
      |16 ones 2
      |17 eq 1 5 16
      |18 eq 1 6 16
      |19 and 1 17 18
      |20 bad 19
      |""".stripMargin

  it should "parse twocount2 which uses negative node ids" in {
    val expected =
      """twocount2
        |input turn : bv<1>
        |bad _bad_0 : bv<1> = and(eq(a, 2'b11), eq(b, 2'b11))
        |state a : bv<2>
        |  [init] 2'b0
        |  [next] ite(turn, a, add(a, 2'b1))
        |state b : bv<2>
        |  [init] 2'b0
        |  [next] ite(not(turn), b, add(b, 2'b1))
        |""".stripMargin

    val sys = Btor2.read(twocount2, inlineSignals = true, defaultName = "twocount2").serialize
    assert(sys.trim == expected.trim)
  }

}
