// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc.{Btor2, IsOutput, TransitionSystem, TransitionSystemSim}
import org.scalatest.flatspec.AnyFlatSpec
import synth.Synthesizer.initSys

class TestbenchSimulatorTests extends AnyFlatSpec {
  behavior.of("Testbench Simulator")

  val BenchmarkDir = os.pwd / "test" / "synth" / "benchmarks"
  val CirFixDir = os.pwd / os.up / "benchmarks" / "cirfix"

  it should "correctly execute i2c master testbench" in {
    val tb = Testbench.load(CirFixDir / "opencores" / "i2c" / "fixed_x_prop_tb.csv")
    assert(tb.length == 171957)

    val sys = Btor2.load(BenchmarkDir / "i2c_master.btor")

    // pick random starting state
    val seed: Long = 1
    val rnd = new scala.util.Random(seed)
    val initialized = initSys(sys, RandomInit, rnd)

    // pick random inputs for Xs
    val randInputTb = Testbench.addRandomInput(sys, tb, rnd)

    val r = Testbench.run(initialized, randInputTb, verbose = true)
    assert(!r.failed)
  }

  // this is the code we used to generate the x-prop fix
  it should "fix x-prop issues with the i2c testbench" in {
    val tb = Testbench.load(CirFixDir / "opencores" / "i2c" / "orig_tb_sync_reset.csv")
    assert(tb.length == 171957)

    val sys = Btor2.load(BenchmarkDir / "i2c_master.btor")

    // pick random starting state
    val seed: Long = 0
    val rnd = new scala.util.Random(seed)
    val initialized = initSys(sys, RandomInit, rnd)

    // fix X-prop issues
    val fixed = XInputConversion(initialized, tb, rnd, verbose = false)

    Testbench.save(CirFixDir / "opencores" / "i2c" / "fixed_x_prop_tb.csv", fixed)
  }

}

private object XInputConversion {

  /** Generates random inputs for all X-inputs and corrects specified (non-X) output where necessary.
    * The system needs to be the original, ground truth system without a bug.
    */
  def apply(sys: TransitionSystem, tb: Testbench, rnd: scala.util.Random, verbose: Boolean): Testbench = {
    // pick random inputs for Xs
    val randInputTb = Testbench.addRandomInput(sys, tb, rnd)

    // run the testbench
    val r = Testbench.run(sys, randInputTb, verbose = false)

    if (!r.failed) { return randInputTb }

    // analyze the failed outputs and patch them up
    val isOutput = sys.signals.filter(_.lbl == IsOutput).map(_.name).toSet
    val values = randInputTb.values.zip(r.values).zipWithIndex.map { case ((tbValues, rValues), ii) =>
      tbValues.zip(randInputTb.signals).map {
        case (Some(expected), name) if isOutput(name) =>
          val actual = rValues(name)
          if (expected != actual) {
            if (verbose) println(s"$name@$ii: $expected -> $actual")
          }
          Some(actual)
        case (other, _) => other
      }
    }

    randInputTb.copy(values = values)
  }
}
