// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import org.scalatest.ParallelTestExecution
import org.scalatest.flatspec.AnyFlatSpec

abstract class SynthesizerSpec extends AnyFlatSpec {
  val BenchmarkDir = os.pwd / "test" / "synth" / "benchmarks"
  val CirFixDir = os.pwd / os.up / "benchmarks" / "cirfix"
  val DemoDir = os.pwd / os.up / "demo" / "project"
  val PaperExampleDir = os.pwd / os.up / "benchmarks" / "paper_example"
  val DefaultConfig = Config()
}

class SynthesizerTests extends SynthesizerSpec with ParallelTestExecution {
  behavior.of("Synthesizer")

  it should "synthesize a fix for decoder_3_to_8_wadden_buggy1 with original testbench and literal replacer template" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_wadden_buggy1_with_literals_replaced.btor",
      CirFixDir / "decoder_3_to_8" / "orig_tb.csv",
      DefaultConfig
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

  // this is even a little faster (~1.1s)
  it should "recognize that there is not solution for decoder_3_to_8_buggy_var_replace_literals using yices2" in {
    val r = Synthesizer.run(
      BenchmarkDir / "decoder_3_to_8_buggy_var_replace_literals.btor",
      CirFixDir / "decoder_3_to_8" / "complete_min_tb.csv",
      DefaultConfig.changeSolver("yices2")
    )
    assert(r.cannotRepair)
  }

  it should "determine there is nothing to fix for sdram_controller with original testbench" in {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("yices2").makeVerbose().changeInit(ZeroInit)
    )
    assert(r.noRepairNecessary)
  }

  // this takes > 10min, not sure how long though
  it should "synthesize a solution for sdram_controller_wadden_buggy2_replace_literals with original testbench" ignore {
    val r = Synthesizer.run(
      BenchmarkDir / "sdram_controller_wadden_buggy2_replace_literals.btor",
      CirFixDir / "sdram_controller" / "orig_tb.csv",
      DefaultConfig.changeSolver("bitwuzla").makeVerbose().changeInit(ZeroInit)
    )
    assert(r.noRepairNecessary)
  }

  it should "synthesize a solution for first_counter_tb_paper_example" in {
    val r = Synthesizer.run(
      BenchmarkDir / "first_counter_tb_paper_example.btor",
      PaperExampleDir / "tb.csv",
      DefaultConfig.changeSolver("z3").makeVerbose().changeInit(RandomInit).copy(seed = 1)
    )
    assert(r.cannotRepair)
  }

  it should "synthesize multiple solutions for counter overflow kgoliya with assign const template and orig_tb" in {
    val r = Synthesizer.run(
      BenchmarkDir / "first_counter_overflow_kgoliya_buggy1_assign_const.btor",
      CirFixDir / "first_counter_overflow" / "orig_tb.csv",
      DefaultConfig
        .changeSolver("bitwuzla")
        .makeVerbose()
        .changeInit(RandomInit)
        .copy(seed = 1)
        .doSampleSolutionsUpTo(0)
        .doFilterSolutions()
    )
    println(r)
  }

  it should "synthesize multiple different solutions for a version of the demo counter" in {
    val r = Synthesizer.run(
      BenchmarkDir / "first_counter_demo_replace_lit.btor",
      DemoDir / "tb.csv",
      DefaultConfig
        .changeSolver("bitwuzla")
        .makeVerbose()
        .changeInit(AnyInit)
        .doSampleSolutionsUpTo(2)
        .doFilterSolutions()
    )
    println(r)
  }
}
