// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc.Btor2
import org.scalatest.flatspec.AnyFlatSpec
import synth.Synthesizer.initSys

class TestbenchSimulatorTests extends AnyFlatSpec {
  behavior.of("Testbench Simulator")

  val BenchmarkDir = os.pwd / "test" / "synth" / "benchmarks"
  val CirFixDir = os.pwd / os.up / "benchmarks" / "cirfix"

  it should "correctly execute i2c master testbench" in {
    val tb = Testbench.load(CirFixDir / "opencores" / "i2c" / "orig_tb.csv")
    assert(tb.length == 171957)

    val sys = Btor2.load(BenchmarkDir / "i2c_master.btor")

    // pick random starting state
    val seed: Long = 0
    val rnd = new scala.util.Random(seed)
    val initialized = initSys(sys, RandomInit, rnd)

    val r = Testbench.run(initialized, tb, verbose = true)
    assert(!r.failed)
  }

}
