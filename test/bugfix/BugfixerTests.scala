// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>


package bugfix

import org.scalatest.flatspec.AnyFlatSpec

class BugfixerFirstCounterOverflowTests extends AnyFlatSpec {
  behavior of "Bugfixer"

  private val Dir = os.pwd / "benchmarks" / "cirfix" / "first_counter_overflow"

  it should "fix first_counter_overflow_kgoliya_buggy1 with original testbench" ignore { // TODO: currently cannot fix!
    val res = Bugfixer.repair(Dir / "first_counter_overflow_kgoliya_buggy1.btor", Dir / "orig_tb.csv")
    assert(res.nonEmpty)
  }
}


class BugfixerDecoderTests extends AnyFlatSpec {
  behavior of "Bugfixer"

  private val CirFixDir = os.pwd / "benchmarks" / "cirfix"

  it should "fix decoder_3_to_8_wadden_buggy1 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_min_tb.csv")
    assert(res.nonEmpty)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_tb.csv")
    assert(res.nonEmpty)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "complete_min_tb.csv")
    assert(res.nonEmpty)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "orig_min_tb.csv")
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.nonEmpty)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "orig_tb.csv")
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.nonEmpty)
  }

  // WARN: with z3 this test takes around 40s!
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "complete_min_tb.csv")
    assert(res.nonEmpty)
  }
}
