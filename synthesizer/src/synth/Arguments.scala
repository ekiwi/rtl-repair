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
  solver:              Solver = Z3SMTLib,
  init:                InitType = AnyInit,
  incremental:         Boolean = false, // selects incremental synthesis that does not unroll the complete testbench
  angelic:             Boolean = false, // selects angelic synthesis, does not require any synthesis variables
  seed:                Long = 0, // currently used to seed random state init if the option is selected
  sampleUpToSize:      Option[Int] = None, // None => return first solution
  pastKStepSize:       Int = 2, // for the incremental solver
  maxRepairWindowSize: Int = 32, // for the incremental solver
  // Some(0) => return all solutions that have the minimal number of changes
  checkCorrectForAll: Boolean = false, // performs a formal check to see if there are any starting states or
  // free inputs that would make a solution fail
  // set debugSolver to true to see commands sent to SMT solver
  filterSolutions: Boolean = false, // filters out solutions that result in the exact same circuit
  debugSolver:     Boolean = false,
  unroll:          Boolean = false,
  verbose:         Boolean = false) {
  require(!(angelic && incremental), "Angelic and incremental solver are mutually exclusive!")
  require(sampleUpToSize.isEmpty || sampleUpToSize.get >= 0, "Cannot sample up to a negative size!")
  def changeSolver(name: String): Config = {
    name match {
      case "z3"          => copy(solver = Z3SMTLib)
      case "cvc4"        => copy(solver = CVC4SMTLib)
      case "yices2"      => copy(solver = Yices2SMTLib)
      case "boolector"   => copy(solver = BoolectorSMTLib)
      case "bitwuzla"    => copy(solver = BitwuzlaSMTLib)
      case "optimathsat" => copy(solver = OptiMathSatSMTLib)
      case other         => throw new RuntimeException(s"Unknown solver $other")
    }
  }
  def showSolverCommunication(): Config = copy(debugSolver = true)
  def makeVerbose():             Config = copy(verbose = true)
  def forceUnroll():             Config = copy(unroll = true)
  def changeInit(tpe: InitType): Config = copy(init = tpe)
  def useIncremental(): Config = copy(incremental = true)
  def useAngelic():     Config = copy(angelic = true)
  def doSampleSolutionsUpTo(ii: Int): Config = copy(sampleUpToSize = Some(ii))
  def doCheckCorrectForAll(): Config = copy(checkCorrectForAll = true)
  def doFilterSolutions():    Config = copy(filterSolutions = true)
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
  opt[Unit]("incremental")
    .action((_, args) => args.copy(config = args.config.useIncremental()))
    .text(
      "use incremental solver"
    )
  opt[Unit]("angelic")
    .action((_, args) => args.copy(config = args.config.useAngelic()))
    .text(
      "use angelic solver (requires circuit without repair template / synthesis variables)"
    )
  opt[Unit]("verbose")
    .action((_, args) => args.copy(config = args.config.makeVerbose()))
    .text("output debug messages")
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
  opt[Int]("sample-solutions").action { (i, args) =>
    args.copy(config = args.config.doSampleSolutionsUpTo(i))
  }
    .text("sample more than one solution")
  opt[Unit]("check-correct-for-all")
    .action((_, args) => args.copy(config = args.config.doCheckCorrectForAll()))
    .text(
      "make the basic synthesizer check to see if there exists a starting state or undefined input that will make the repaired system fail"
    )
  opt[Unit]("filter-solutions")
    .action((_, args) => args.copy(config = args.config.doFilterSolutions()))
    .text("check to see if solutions result in the same circuit and if so, discard any duplicates")
  opt[Int]("past-k-step-size").action { (i, args) =>
    args.copy(config = args.config.copy(pastKStepSize = i))
  }
    .text("the step size for incrementing the pastK value in the incremental solver")
  opt[Int]("max-repair-window-size").action { (i, args) =>
    args.copy(config = args.config.copy(maxRepairWindowSize = i))
  }
    .text("the maximum repair window size before the incremental solver gives up")
}
