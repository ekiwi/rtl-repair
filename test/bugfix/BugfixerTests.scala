// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>


package bugfix

import org.scalatest.flatspec.AnyFlatSpec

class BugfixerTests extends AnyFlatSpec {
  behavior of "Bugfixer"

  private val CirFixDir = os.pwd / "benchmarks" / "cirfix"

  it should "fix decoder_3_to_8_wadden_buggy1 with minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_min_tb.csv")
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with original testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "orig_tb.csv")
  }

  it should "fix decoder_3_to_8_wadden_buggy1 with complete minimized testbench" in {
    val dir = CirFixDir / "decoder_3_to_8"
    Bugfixer.repair(dir / "decoder_3_to_8_wadden_buggy1.btor", dir / "complete_min_tb.csv")
  }
}
