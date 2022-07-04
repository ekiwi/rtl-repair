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
    val sysWithoutUndef = setAnonymousInputsToZero(sys)
    val tbRaw = Testbench.removeRow("time", Testbench.load(testbench))
    val tb = Testbench.checkSignals(sysWithoutUndef, tbRaw, verbose = config.verbose)
    val rnd = new scala.util.Random(config.seed)

    // initialize unconstrained states according to config
    val initializedSys = initSys(sysWithoutUndef, config.init, rnd)

    // find synthesis variables and remove them from the system for now
    val (noSynthVarSys, synthVars) = collectSynthesisVars(initializedSys)

    // println(noSynthVarSys.serialize)

    if (config.solver.isDefined) {
      if (config.incremental) {
        IncrementalSynthesizer.doRepair(noSynthVarSys, tb, synthVars, config)
      } else {
        SmtSynthesizer.doRepair(noSynthVarSys, tb, synthVars, config)
      }
    } else {
      assert(!config.incremental)
      assert(config.checker.isDefined)
      // it is important that we pass the system _with_ synthesis variables!
      ModelCheckerSynthesizer.doRepair(initializedSys, tb, synthVars, config)
    }
  }

  /** Remove any inputs named `_input_[...]` and replace their use with a literal zero.
    * This essentially gets rid of all undefined value modelling by yosys.
    */
  def setAnonymousInputsToZero(sys: TransitionSystem): TransitionSystem = {
    def isAnonymousInput(input: BVSymbol): Boolean = input.name.startsWith("_input_")
    val inputs = sys.inputs.filterNot(isAnonymousInput)
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym: BVSymbol if isAnonymousInput(sym) => BVLiteral(0, sym.width)
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(inputs = inputs, signals = signals)
  }

  private def initSys(sys: TransitionSystem, tpe: InitType, rnd: scala.util.Random): TransitionSystem = tpe match {
    case ZeroInit | RandomInit =>
      val getValue = if (tpe == ZeroInit) { (width: Int) =>
        BVLiteral(0, width)
      } else { (width: Int) =>
        BVLiteral(BigInt(width, rnd), width)
      }
      val states = sys.states.map { state =>
        if (isSynthName(state.name)) {
          state
        } else {
          val init = state.init match {
            case Some(value) => value
            case None        => getValue(state.sym.asInstanceOf[BVSymbol].width)
          }
          state.copy(init = Some(init))
        }
      }
      sys.copy(states = states)
    case AnyInit => sys
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

  private def log2Ceil(value: BigInt): Int = {
    require(value > 0)
    (value - 1).bitLength
  }

  def countChanges(synthVars: SynthVars): BVExpr = {
    require(synthVars.change.nonEmpty)
    val width = log2Ceil(synthVars.change.length)
    val sum = synthVars.change.map { sym =>
      if (width > 1) { BVExtend(sym, width - 1, signed = false) }
      else { sym }
    }.reduce[BVExpr] { case (a: BVExpr, b: BVExpr) => BVOp(Op.Add, a, b) }
    sum
  }

  def countChangesInAssignment(assignment: List[(String, BigInt)]): Int =
    assignment.filter(t => isSynthName(t._1)).map(_._2).sum.toInt
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
