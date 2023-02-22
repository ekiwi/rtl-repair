// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix

import maltese.smt.OptiMathSatSMTLib
import org.scalatest.flatspec.AnyFlatSpec

abstract class BugFixerSpec extends AnyFlatSpec {
  val BenchmarkDir = os.pwd / "test" / "bugfix" / "benchmarks"
  val DefaultConfig = Config()
  val VerboseConfig = DefaultConfig.copy(verbose = true, debugSolver = true)
}

class BugfixerMuxTests extends BugFixerSpec {
  behavior.of("Bugfixer on Mux 4 1")
  private val Dir = BenchmarkDir

  it should "find that no repair is necessary for mux_4_1" in {
    val res = Bugfixer.repair(Dir / "mux_4_1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "find that no repair is necessary for mux_4_1 with minimized testbench" in {
    val res = Bugfixer.repair(Dir / "mux_4_1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fail to fix mux_4_1_kgoliya_buggy1 with original testbench" in {
    // currently this throws an assertion error because the testbench value does not fit the size of the `out`
    // signal which has erroneously been reduced from 4-bit to 1-bit
    val e = intercept[AssertionError] {
      val res = Bugfixer.repair(Dir / "mux_4_1_kgoliya_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
      assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
    }
  }

  it should "fail to fix mux_4_1_wadden_buggy2 with original testbench" in {
    // TODO: this should actually be repairable by changing constants, however, things get optimized too much
    //       by the interning in the btor2 conversion and thus it isn't possible to repair with the ReplaceLiteral template
    val res = Bugfixer.repair(Dir / "mux_4_1_wadden_buggy2.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }

  it should "fail to fix mux_4_1_wadden_buggy1 with original testbench" in {
    // TODO: this should actually be repairable by changing constants, however, things get optimized too much
    //       by the interning in the btor2 conversion and thus it isn't possible to repair with the ReplaceLiteral template
    val res = Bugfixer.repair(Dir / "mux_4_1_wadden_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }
}

class BugfixerShiftRegTests extends BugFixerSpec {
  behavior.of("Bugfixer on ShiftReg")
  private val Dir = BenchmarkDir

  it should "find that no repair is necessary for lshift_reg" in {
    val res = Bugfixer.repair(Dir / "lshift_reg.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fail to fix lshift_reg_wadden_buggy1 with original testbench" in {
    val res = Bugfixer.repair(Dir / "lshift_reg_wadden_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }

  it should "fail to fix lshift_reg_wadden_buggy2 with original testbench" in {
    val res = Bugfixer.repair(Dir / "lshift_reg_wadden_buggy2.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }
}

class BugfixerFsmFullTests extends BugFixerSpec {
  behavior.of("Bugfixer on FsmFull")
  private val Dir = BenchmarkDir

  it should "find that no repair is necessary for fsm_full" in {
    val res = Bugfixer.repair(Dir / "fsm_full.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fail to fix fsm_full_wadden_buggy1 with original testbench" in {
    val res = Bugfixer.repair(Dir / "fsm_full_wadden_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.cannotRepair, res.toString) // cannot be repaired since we do not have the right template yet
  }

  // not sure what is happening here
  it should "fail to fix fsm_full_ssscrazy_buggy2 with original testbench" ignore {
    val res = Bugfixer.repair(
      Dir / "fsm_full_ssscrazy_buggy2.btor",
      Dir / "orig_tb.csv",
      DefaultConfig.copy(solver = OptiMathSatSMTLib)
    )
    // somehow it is possible to repair this bug by changing a lot of constants (38 in fact!)
    // this is not what we are really going for, but it is a repair non the less
    assert(res.isSuccess, res.toString)
  }
}

class BugfixerFlipFlopTests extends BugFixerSpec {
  behavior.of("Bugfixer on FlipFlop")
  private val Dir = BenchmarkDir

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
  private val Dir = BenchmarkDir

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
  private val Dir = BenchmarkDir

  it should "find that no repair is necessary for decoder3_to_8" in {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8.btor", Dir / "orig_min_tb.csv", DefaultConfig)
    assert(res.noRepairNecessary, res.toString)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with minimized testbench" in {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy1.btor", Dir / "orig_min_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with original testbench" in {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy1.btor", Dir / "orig_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  // ignored because it takes too long
  it should "fix decoder_3_to_8_wadden_buggy1 with complete minimized testbench" ignore {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy1.btor", Dir / "complete_min_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with minimized testbench" in {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy2.btor", Dir / "orig_min_tb.csv", DefaultConfig)
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.isSuccess, res.toString)
  }

  it should "not be able to fix decoder_3_to_8_wadden_buggy2 with original testbench" in {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy2.btor", Dir / "orig_tb.csv", DefaultConfig)
    // while we do return a result, it is in fact incorrect wrt the original description!
    assert(res.isSuccess, res.toString)
  }

  // currently ignored because z3 takes around 30-40s to solve this and it gets annoying
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench" ignore {
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy2.btor", Dir / "complete_min_tb.csv", DefaultConfig)
    assert(res.isSuccess, res.toString)
  }

  // same as above, but much faster using OptiMathSAT instead of Z3
  it should "fix decoder_3_to_8_wadden_buggy2 with complete minimized testbench with optimathsat" in {
    val config = DefaultConfig.copy(solver = OptiMathSatSMTLib)
    val res = Bugfixer.repair(Dir / "decoder_3_to_8_wadden_buggy2.btor", Dir / "complete_min_tb.csv", config)
    assert(res.isSuccess, res.toString)
  }
}
