// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import org.scalatest.flatspec.AnyFlatSpec

abstract class SynthesizerSpec extends AnyFlatSpec {
  val BenchmarkDir = os.pwd / "test" / "synth" / "benchmarks"
  val CirFixDir = os.pwd / os.up / "benchmarks" / "cirfix"
  val DefaultConfig = Config()
}

class SynthesizerDecoderTests extends SynthesizerSpec {
  behavior.of("Synthesizer on Decoder")

  it should "synthesize a fix for decoder_3_to_8_wadden_buggy1 with original testbench and literal replacer template" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_wadden_buggy1_with_literals_replaced.btor",
      CirFixDir / "decoder_3_to_8" / "orig_tb.csv",
      DefaultConfig
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_wadden_buggy1 with original testbench and literal replacer template using btormc" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_wadden_buggy1_with_literals_replaced.btor",
      CirFixDir / "decoder_3_to_8" / "orig_tb.csv",
      DefaultConfig.changeSolver("btormc")
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_buggy_var using optimathsat" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("optimathsat")
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_buggy_var using btormc" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("btormc")
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_buggy_var using cvc4" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("cvc4")
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_buggy_var using yices2" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("yices2")
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_buggy_var using boolector" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("boolector")
    )
    assert(r.isSuccess)
  }

  it should "synthesize a fix for decoder_3_to_8_buggy_var using bitwuzla" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("bitwuzla")
    )
    assert(r.isSuccess)
  }

  // this generally takes a while (~14s)
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using optimathsat" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("optimathsat")
    )
    assert(r.cannotRepair)
  }

  // this is a little faster with cvc4 much faster (~5s)
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using cvc4" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("cvc4")
    )
    assert(r.cannotRepair)
  }

  // takes around 2s
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using boolector" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("boolector")
    )
    assert(r.cannotRepair)
  }

  // takes around 1.6s
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using bitwuzla" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("bitwuzla")
    )
    assert(r.cannotRepair)
  }

  // this is generally much faster (~1.5s)
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using btormc" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("btormc")
    )
    assert(r.cannotRepair)
  }

  // this is even a little faster (~1.1s)
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using yices2" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("yices2")
    )
    assert(r.cannotRepair)
  }

  // this takes ~22s with yices2, ~28s with bitwuzla
  it should "determine there is nothing to fix for sdram_controller with original testbench" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb_output_x_until_reset.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().changeInit(ZeroInit)
    )
    assert(r.noRepairNecessary)
  }

}
