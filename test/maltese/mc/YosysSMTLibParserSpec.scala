// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import org.scalatest.flatspec.AnyFlatSpec

class YosysSMTLibParserSpec extends AnyFlatSpec {
  behavior of "YosysSMTLibParser"

  it should "parse a simple decoder" ignore {
    val dir = os.pwd / "benchmarks" / "cirfix" / "decoder_3_to_8"
    val smtSys = YosysSMTLibParser.load(dir / "decoder_3_to_8_wadden_buggy1.smt")
    val btorSys = Btor2.load(dir / "decoder_3_to_8_wadden_buggy1.btor")

    println("SMT:")
    println(smtSys.serialize)
    println()
    println()
    println("Btor:")
    println(btorSys.serialize)
  }

  it should "parse a simple counter" ignore {
    val dir = os.pwd / "benchmarks" / "cirfix" / "first_counter_overflow"
    val smtSys = YosysSMTLibParser.load(dir / "first_counter_overflow.smt")
    val btorSys = Btor2.load(dir / "first_counter_overflow.btor")

    println("SMT:")
    println(smtSys.serialize)
    println()
    println()
    println("Btor:")
    println(btorSys.serialize)
  }
}
