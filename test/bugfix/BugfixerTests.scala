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

class BugfixerFsmFullTests extends BugFixerSpec {
  behavior.of("Bugfixer on FsmFull")
  private val Dir = CirFixDir / "fsm_full"

  it should "find that no repair is necessary for fsm_full" in {
    val res = Bugfixer.repair(Dir / "fsm_full.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fail to fix fsm_full_wadden_buggy1 with original testbench" in {
    val res = Bugfixer.repair(Dir / "fsm_full_wadden_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }

  it should "fail to fix fsm_full_ssscrazy_buggy2 with original testbench" ignore { // TODO: it seems like this can actually be solved by twiddeling with constants ...?
    val res = Bugfixer.repair(Dir / "fsm_full_ssscrazy_buggy2.btor", Dir / "orig_tb.csv", DefaultConfig.copy(solver = OptiMathSatSMTLib))
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }
}

class BugfixerFlipFlopTests extends BugFixerSpec {
  behavior.of("Bugfixer on FlipFlop")
  private val Dir = CirFixDir / "flip_flop"

  it should "find that no repair is necessary for tff" in {
    val res = Bugfixer.repair(Dir / "tff.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fail to fix tff_wadden_buggy1 with original testbench" in {
    val res = Bugfixer.repair(Dir / "tff_wadden_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }

  it should "fail to fix tff_wadden_buggy2 with original testbench" in {
    val res = Bugfixer.repair(Dir / "tff_wadden_buggy2.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }
}

class BugfixerFirstCounterOverflowTests extends BugFixerSpec {
  behavior.of("Bugfixer on FirstCounterOverflow")
  private val Dir = CirFixDir / "first_counter_overflow"

  it should "find that no repair is necessary for first_counter_overflow" in {
    val res = Bugfixer.repair(Dir / "first_counter_overflow.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fail to fix first_counter_overflow_kgoliya_buggy1 with original testbench" in {
    val res = Bugfixer.repair(Dir / "first_counter_overflow_kgoliya_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }

  it should "fail to fix first_counter_overflow_wadden_buggy2 with original testbench" in {
    val res = Bugfixer.repair(Dir / "first_counter_overflow_wadden_buggy2.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }
}

class BugfixerDecoderTests extends BugFixerSpec {
  behavior.of("Bugfixer on Decoder")

  it should "find that no repair is necessary for decoder3_to_8" in {
    val dir = CirFixDir / "decoder_3_to_8"
    val res = Bugfixer.repair(dir / "decoder_3_to_8.btor", dir / "orig_min_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

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
