// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc.{BtormcModelChecker, IsModelChecker}
import maltese.smt._
import scopt.OptionParser

case class Arguments(
  design:    Option[os.Path], // path to design btor
  testbench: Option[os.Path], // path to testbench CSV
  config:    Config = Config())

case class Config(
  solver:  Option[Solver] = Some(Z3SMTLib),
  checker: Option[IsModelChecker] = None,
  init:    InitType = AnyInit,
  seed:    Long = 0, // currently used to seed random state init if the option is selected
  // set debugSolver to true to see commands sent to SMT solver
  debugSolver: Boolean = false,
  unroll:      Boolean = false,
  verbose:     Boolean = false) {
  require(solver.isEmpty != checker.isEmpty, "need exactly one checker OR solver, not both or neither")
  def changeSolver(name: String): Config = {
    name match {
      case "z3"          => copy(solver = Some(Z3SMTLib), checker = None)
      case "cvc4"        => copy(solver = Some(CVC4SMTLib), checker = None)
      case "yices2"      => copy(solver = Some(Yices2SMTLib), checker = None)
      case "boolector"   => copy(solver = Some(BoolectorSMTLib), checker = None)
      case "bitwuzla"    => copy(solver = Some(BitwuzlaSMTLib), checker = None)
      case "optimathsat" => copy(solver = Some(OptiMathSatSMTLib), checker = None)
      case "btormc"      => copy(solver = None, checker = Some(new BtormcModelChecker))
      case other         => throw new RuntimeException(s"Unknown solver $other")
    }
  }
  def makeVerbose(): Config = copy(verbose = true)
  def forceUnroll(): Config = copy(unroll = true)
  def changeInit(tpe: InitType): Config = copy(init = tpe)
}

sealed trait InitType
case object ZeroInit extends InitType
case object RandomInit extends InitType

/** creates an exists for all problem where the solution has to work for any initial state assignment */
case object AnyInit extends InitType

class ArgumentParser extends OptionParser[Arguments]("synthesizer") {
  head("synthesizer", "0.2")
  opt[String]("design")
    .required()
    .action((a, config) => config.copy(design = Some(os.Path(a, os.pwd))))
    .text("the design to be repaired with the template instantiated in btor format")
  opt[String]("testbench")
    .required()
    .action((a, config) => config.copy(testbench = Some(os.Path(a, os.pwd))))
    .text("the testbench in CSV format")
  opt[Unit]("debug-solver")
    .action((_, args) => args.copy(config = args.config.copy(debugSolver = true)))
    .text("print out stdlib commands that are sent to solver")
  opt[Unit]("force-unroll")
    .action((_, args) => args.copy(config = args.config.forceUnroll()))
    .text(
      "always unroll system instead of using the compact encoding. only has an effect for z3, optimathsat, cvc4 and yices2"
    )
  opt[String]("solver").action { (a, args) =>
    args.copy(config = args.config.changeSolver(a))
  }
    .text("z3 or optimathsat or btormc")
  opt[String]("init").action { (a, args) =>
    val tpe = a match {
      case "any"    => AnyInit
      case "zero"   => ZeroInit
      case "random" => RandomInit
      case other    => throw new RuntimeException(s"Un-supported init type: $other. Try: any, zero or random")
    }
    args.copy(config = args.config.changeInit(tpe))
  }
    .text("any, zero or random")
}
