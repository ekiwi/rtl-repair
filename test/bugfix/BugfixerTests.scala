// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>


package bugfix

import maltese.smt.OptiMathSatSMTLib
import org.scalatest.flatspec.AnyFlatSpec

class BugfixerFirstCounterOverflowTests extends AnyFlatSpec {
  behavior of "Bugfixer"

  private val Dir = os.pwd / "benchmarks" / "cirfix" / "first_counter_overflow"
  private val DefaultConfig = Config()
  private val VerboseConfig = DefaultConfig.copy(verbose = true, debugSolver = true)

  it should "fix first_counter_overflow_kgoliya_buggy1 with original testbench" in {
    // TODO: this erroneously completes because we do not properly deal with uninitialized state (or inputs)
    val res = Bugfixer.repair(Dir / "first_counter_overflow_kgoliya_buggy1.btor", Dir / "orig_tb.csv", VerboseConfig)
    assert(res.nonEmpty)
  }
}


class BugfixerDecoderTests extends AnyFlatSpec {
  behavior of "Bugfixer"

  private val CirFixDir = os.pwd / "benchmarks" / "cirfix"
  private val DefaultConfig = Config()

  it should "fix decoder_3_to_8_wadden_buggy1 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_min_tb.csv", DefaultConfig)
    assert(res.nonEmpty)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_tb.csv", DefaultConfig)
    assert(res.nonEmpty)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "complete_min_tb.csv", DefaultConfig)
    assert(res.nonEmpty)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "orig_min_tb.csv", DefaultConfig)
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.nonEmpty)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "orig_tb.csv", DefaultConfig)
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.nonEmpty)
  }

  // WARN: with z3 this test takes around 40s!
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "complete_min_tb.csv", DefaultConfig)
    assert(res.nonEmpty)
  }

  // same as above, but much faster using OptiMathSAT instead of Z3
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench with optimathsat" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val config = DefaultConfig.copy(solver = OptiMathSatSMTLib)
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "complete_min_tb.csv", config)
    assert(res.nonEmpty)
  }
}
