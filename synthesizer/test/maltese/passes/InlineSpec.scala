// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes

class InlineSpec extends PassSpec(new Inline) {

  it should "not inline a signal with more than one use" in {
    val src =
      """1 sort bitvec 1
        |2 input 1
        |3 not 1 2
        |4 not 1 3
        |5 not 1 3
        |""".stripMargin

    // s3 is used twice and thus should not be inlined
    val expected =
      """input _input_0 : bv<1>
        |node s3 : bv<1> = not(_input_0)
        |node s4 : bv<1> = not(s3)
        |node s5 : bv<1> = not(s3)
        |""".stripMargin
    check(src, expected)
  }

}
