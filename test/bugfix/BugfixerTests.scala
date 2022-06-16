// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>


package bugfix

import maltese.smt.OptiMathSatSMTLib
import org.scalatest.flatspec.AnyFlatSpec

abstract class BugFixerSpec extends AnyFlatSpec {
  val CirFixDir = os.pwd / "benchmarks" / "cirfix"
  val DefaultConfig = Config()
  val VerboseConfig = DefaultConfig.copy(verbose = true, debugSolver = true)
}

class BugfixerFirstCounterOverflowTests extends BugFixerSpec {
  behavior of "Bugfixer on FirstCounterOverflow"
  private val Dir = CirFixDir / "first_counter_overflow"

  it should "fix first_counter_overflow_kgoliya_buggy1 with original testbench" ignore {
    // TODO: this erroneously completes because we do not properly deal with uninitialized state (or inputs)
    val e = intercept[RuntimeException] {
      val res = Bugfixer.repair(Dir / "first_counter_overflow_kgoliya_buggy1.btor", Dir / "orig_tb.csv", VerboseConfig)
      assert(res.isSuccess, res.toString)
    }
  }
}


class BugfixerDecoderTests extends BugFixerSpec {
  behavior of "Bugfixer on Decoder"

  it should "fix decoder_3_to_8_wadden_buggy1 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_min_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "complete_min_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "orig_min_tb.csv", DefaultConfig)
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.isSuccess, res.toString)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "orig_tb.csv", DefaultConfig)
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.isSuccess, res.toString)
  }

  // WARN: with z3 this test takes around 40s!
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "complete_min_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  // same as above, but much faster using OptiMathSAT instead of Z3
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench with optimathsat" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val config = DefaultConfig.copy(solver = OptiMathSatSMTLib)
    val res = Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy2.btor", dir / "complete_min_tb.csv", config)
    assert(res.isSuccess, res.toString)
  }
}