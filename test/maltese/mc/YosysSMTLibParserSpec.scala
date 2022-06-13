// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import org.scalatest.flatspec.AnyFlatSpec

class YosysSMTLibParserSpec extends AnyFlatSpec {
  behavior of "YosysSMTLibParser"

  it should "parse a simple decoder" ignore {
    val sys = YosysSMTLibParser.load(os.pwd / "benchmarks" / "cirfix" / "decoder_3_to_8" / "decoder_3_to_8_wadden_buggy1.smt")
  }
}
