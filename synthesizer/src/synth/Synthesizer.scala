// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.passes._
import maltese.smt._

/** Takes in a Transition System with synthesis variables +  a testbench and tries to find a valid synthesis assignment. */
object Synthesizer {
  // synchronized to the naming conventions used in the python frontend
  val SynthVarPrefix = "__synth_"
  val SynthChangePrefix = "__synth_change_"

  def main(args: Array[String]): Unit = {
    val parser = new ArgumentParser()
    val arguments = parser.parse(args, Arguments(None, None)).get
    val result = run(arguments.design.get, arguments.testbench.get, arguments.config)
    // print result
    result match {
      case NoRepairNecessary => println("""{"status":"no-repair"}""")
      case CannotRepair      => println("""{"status":"cannot-repair"}""")
      case RepairSuccess(assignments) =>
        println("""{"status":"success",""")
        println(""" "assignment": {""")
        println(assignments.map { case (name, value) =>
          s"""   "$name": $value"""
        }.mkString(",\n"))
        println(" }")
        println("}")
    }
  }

  def run(design: os.Path, testbench: os.Path, config: Config): RepairResult = {
    // load design and testbench and validate them
    val sys = inlineAndRemoveDeadCode(Btor2.load(design))
    val tbRaw = Testbench.removeRow("time", Testbench.load(testbench))
    val tb = Testbench.checkSignals(sys, tbRaw, verbose = config.verbose)

    // find synthesis variables and remove them from the system for now
    val (noSynthVarSys, synthVars) = collectSynthesisVars(sys)

    if (config.solver.isDefined) {
      SmtSynthesizer.doRepair(noSynthVarSys, tb, synthVars, config)
    } else {
      assert(config.checker.isDefined)
      // it is important that we pass the system _with_ synthesis variables!
      ModelCheckerSynthesizer.doRepair(sys, tb, synthVars, config)
    }
  }

  def isSynthName(name: String): Boolean =
    name.startsWith(SynthVarPrefix) || name.startsWith(SynthChangePrefix)

  def collectSynthesisVars(sys: TransitionSystem): (TransitionSystem, SynthVars) = {
    val changed = sys.states.map(_.sym).filter(_.name.startsWith(SynthChangePrefix)).map(_.asInstanceOf[BVSymbol])
    val free =
      sys.states.map(_.sym).filter(s => s.name.startsWith(SynthVarPrefix) && !s.name.startsWith(SynthChangePrefix))
    val isSynthVar = (changed ++ free).map(_.name).toSet
    val signals = sys.signals.filterNot(s => s.name.endsWith(".next") && isSynthVar(s.name.dropRight(".next".length)))
    val states = sys.states.filterNot(s => isSynthVar(s.name))
    val vars = SynthVars(changed, free)
    val noSynthVarSys = sys.copy(signals = signals, states = states)
    (noSynthVarSys, vars)
  }

  def inlineAndRemoveDeadCode(sys: TransitionSystem): TransitionSystem =
    PassManager(Seq(new Inline(conservative = true), new DeadCodeElimination(removeUnusedInputs = false))).run(sys)

}

sealed trait RepairResult {
  def isSuccess:         Boolean = false
  def noRepairNecessary: Boolean = false
  def cannotRepair:      Boolean = false
}

/** indicates that the provided system and testbench pass for all possible unconstraint inputs and initial states */
case object NoRepairNecessary extends RepairResult {
  override def noRepairNecessary: Boolean = true
}

/** indicates that no repair was found, this probably due to constraints in our repair templates */
case object CannotRepair extends RepairResult {
  override def cannotRepair: Boolean = true
}

/** indicates that the repair was successful and provides the repaired system */
case class RepairSuccess(assignments: Seq[(String, BigInt)]) extends RepairResult {
  override def isSuccess: Boolean = true
}
