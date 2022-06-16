// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix

import maltese.smt.{Solver, Z3SMTLib}
import scopt.OptionParser

case class Arguments(
  design: Option[os.Path], // path to design btor
  testbench: Option[os.Path], // path to testbench CSV
  config: Config = Config(),
)

case class Config(
  solver: Solver = Z3SMTLib,
  // set debugSolver to true to see commands sent to SMT solver
  debugSolver: Boolean = false,
  verbose: Boolean = false,
  seed: Long = 0,
)

class ArgumentParser extends OptionParser[Arguments]("bugfixer") {
  head("bugfixer", "0.x")
  opt[String]("design")
    .required()
    .action((a, config) => config.copy(design = Some(os.Path(a, os.pwd))))
    .text("the design to be repaired in btor format")
  opt[String]("testbench")
    .required()
    .action((a, config) => config.copy(testbench = Some(os.Path(a, os.pwd))))
    .text("the testbench in CSV format")
}