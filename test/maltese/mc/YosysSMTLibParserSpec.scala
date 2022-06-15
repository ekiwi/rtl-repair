// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import org.scalatest.flatspec.AnyFlatSpec

class YosysSMTLibParserSpec extends AnyFlatSpec {
  behavior of "YosysSMTLibParser"

  private def loadAndCheck(dir: os.Path, smtName: String, btorName: String): Unit = {
    val btorSys = Btor2.load(dir / btorName)
    println("Btor:")
    println(btorSys.serialize)

    println("\n\n")
    val smtSys = YosysSMTLibParser.load(dir / smtName)
    println("\n\nSMT:")
    println(smtSys.serialize)
  }

  it should "parse a simple decoder" ignore {
    val dir = os.pwd / "benchmarks" / "cirfix" / "decoder_3_to_8"
    loadAndCheck(dir, "decoder_3_to_8_wadden_buggy1.smt", "decoder_3_to_8_wadden_buggy1.btor")
  }

  it should "parse a simple counter" ignore {
    val dir = os.pwd / "benchmarks" / "cirfix" / "first_counter_overflow"
    loadAndCheck(dir, "first_counter_overflow.smt", "first_counter_overflow.btor")
  }

  it should "parse a simple fsm" ignore {
    val dir = os.pwd / "benchmarks" / "cirfix" / "fsm_full"
    loadAndCheck(dir, "fsm_full.smt", "fsm_full.btor")
  }
}
