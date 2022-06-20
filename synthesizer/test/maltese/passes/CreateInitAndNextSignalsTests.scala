package maltese.passes

class CreateInitAndNextSignalsTests extends PassSpec(CreateInitAndNextSignals) {

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

  it should "create init and next symbols, even when we parse with inline=true" in {
    val expected =
      """input turn : bv<1>
        |bad _bad_0 : bv<1> = and(eq(a, 2'b11), eq(b, 2'b11))
        |node a.init : bv<2> = 2'b0
        |node a.next : bv<2> = ite(turn, a, add(a, 2'b1))
        |node b.init : bv<2> = 2'b0
        |node b.next : bv<2> = ite(not(turn), b, add(b, 2'b1))
        |state a : bv<2>
        |  [init] a.init
        |  [next] a.next
        |state b : bv<2>
        |  [init] b.init
        |  [next] b.next
        |""".stripMargin
    check(twocount2, expected, inlineSignals = true)
  }

}
