// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.passes._
import maltese.smt._
import synth.BasicSynthesizer.Assignment

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
      case NoRepairNecessary(stats) => println(toJson("no-repair", stats))
      case CannotRepair(stats)      => println(toJson("cannot-repair", stats))
      case RepairSuccess(solutions, stats) =>
        val solutionJSON = solutions.map { case Solution(assignments) =>
          val assignmentJSON = assignments.map { case (name, value) => s"""     "$name": $value""" }.mkString(",\n")
          s"""  { "assignment" : {
             |$assignmentJSON
             |   }
             |  }
             |""".stripMargin
        }.mkString(",\n")

        println("""{"status":"success",""")
        println(f""""solver-time": ${stats.solverTimeNs},""")
        println(f""""past-k": ${stats.pastK},""")
        println(f""""future-k": ${stats.futureK},""")
        println(""" "solutions": [""")
        println(solutionJSON)
        println(" ]")
        println("}")
    }
  }

  private def toJson(status: String, stats: RepairStats): String = {
    f"""{"status":"$status", "solver-time": ${stats.solverTimeNs}, "past-k": ${stats.pastK}, "future-k": ${stats.futureK} }"""
  }

  def run(design: os.Path, testbench: os.Path, config: Config): RepairResult = {
    // load design and transform circuit
    val sys = inlineAndRemoveDeadCode(Btor2.load(design))
    // yosys will model some uncertainty in the Verilog, mostly relate to X-propagation, by adding
    // auxiliary inputs. We remove them and instead create a node that is equivalent to zero
    // since we want to ignore any non-determinism in the circuit when trying to repair it.
    val sysWithoutUndef = setAnonymousInputsToZero(sys)
    // All our testbenches have a `time` column which we do not care about.
    val tbRaw = Testbench.removeColumn("time", Testbench.load(testbench))
    // We validate that the testbench actually matches the design we just loaded.
    val tb = Testbench.checkSignals(sysWithoutUndef, tbRaw, verbose = config.verbose)

    // Create a new random number generator that will be used for the repair operation.
    val rnd = new scala.util.Random(config.seed)

    // initialize unconstrained states according to config
    val initializedSys = initSys(sysWithoutUndef, config.init, rnd)

    // find synthesis variables and remove them from the system for now
    val (noSynthVarSys, synthVars) = collectSynthesisVars(initializedSys)

    // run repair
    val result = doRepair(noSynthVarSys, tb, synthVars, config, rnd)

    result match {
      case r: NoRepairNecessary => r
      case r: CannotRepair      => r
      case RepairSuccess(solutions, stats) =>
        val sortedSolutions = SolutionFilter.sort(solutions)
        if (config.filterSolutions) {
          val ctx = startSolver(config) // TODO: consider re-using the solver context from the synthesis
          val filtered = SolutionFilter.run(ctx, noSynthVarSys, tb, config, sortedSolutions)
          ctx.close()
          RepairSuccess(filtered, stats)
        } else {
          RepairSuccess(sortedSolutions, stats)
        }
    }
  }

  private def doRepair(
    noSynthVarSys: TransitionSystem,
    tb:            Testbench,
    synthVars:     SynthVars,
    config:        Config,
    rnd:           scala.util.Random
  ): RepairResult = {
    if (config.incremental) {
      IncrementalSynthesizer.doRepair(noSynthVarSys, tb, synthVars, config, rnd)
    } else if (config.angelic) {
      assert(
        synthVars.isEmpty,
        f"Cannot use angelic solver with system that had a repair template applied:\n$synthVars"
      )
      AngelicSynthesizer.doRepair(noSynthVarSys, tb, config, rnd)
    } else {
      BasicSynthesizer.doRepair(noSynthVarSys, tb, synthVars, config)
    }
  }

  /** Remove any inputs named `_input_[...]` and replace their use with a literal zero.
    * This essentially gets rid of all undefined value modelling by yosys.
    */
  private def setAnonymousInputsToZero(sys: TransitionSystem): TransitionSystem = {
    def isAnonymousInput(input: BVSymbol): Boolean = input.name.startsWith("_input_")
    val inputs = sys.inputs.filterNot(isAnonymousInput)
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym: BVSymbol if isAnonymousInput(sym) => BVLiteral(0, sym.width)
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(inputs = inputs, signals = signals)
  }

  /** Initialized the starting states (reg/mem content) of the system to random values, zero or nothing at all. */
  def initSys(sys: TransitionSystem, tpe: InitType, rnd: scala.util.Random): TransitionSystem = tpe match {
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
            case None =>
              state.sym match {
                case BVSymbol(_, width)                    => getValue(width)
                case ArraySymbol(_, indexWidth, dataWidth) =>
                  // TODO: consider different values for different entries
                  ArrayConstant(getValue(dataWidth), indexWidth)
              }
          }
          state.copy(init = Some(init))
        }
      }
      sys.copy(states = states)
    // nothing to do, the synthesizer will have to assign value in a CEGAR loop
    case AnyInit => sys
  }

  def isSynthName(name: String): Boolean = {
    val suffix = name.split('.').last
    suffix.startsWith(SynthVarPrefix) || suffix.startsWith(SynthChangePrefix)
  }

  def isFreeSynthName(name: String): Boolean = {
    val suffix = name.split('.').last
    suffix.startsWith(SynthVarPrefix) && !suffix.startsWith(SynthChangePrefix)
  }

  def isChangeSynthName(name: String): Boolean = {
    val suffix = name.split('.').last
    suffix.startsWith(SynthChangePrefix)
  }

  def collectSynthesisVars(sys: TransitionSystem): (TransitionSystem, SynthVars) = {
    val changed = sys.states.map(_.sym).filter(s => isChangeSynthName(s.name)).map(_.asInstanceOf[BVSymbol])
    val free =
      sys.states.map(_.sym).filter(s => isFreeSynthName(s.name))
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

  def countChanges(minimize: Seq[BVExpr]): BVExpr = {
    require(minimize.nonEmpty)
    val width = log2Ceil(minimize.length)
    val sum = minimize.map { sym =>
      if (width > 1) { BVExtend(sym, width - 1, signed = false) }
      else { sym }
    }.reduce[BVExpr] { case (a: BVExpr, b: BVExpr) => BVOp(Op.Add, a, b) }
    sum
  }

  def countChangesInAssignment(assignment: Seq[(String, BigInt)]): Int =
    assignment.filter(t => isChangeSynthName(t._1)).map(_._2).sum.toInt

  def getChangesInAssignment(assignment: Seq[(String, BigInt)]): Seq[String] =
    assignment.filter(_._2 == 1).map(_._1).filter(isChangeSynthName)

  def startSolver(config: Config): SolverContext = {
    // create solver context
    val solver = config.solver
    val ctx = solver.createContext(debugOn = config.debugSolver)
    if (solver.name.contains("z3")) {
      ctx.setLogic("ALL")
    } else if (solver.supportsUninterpretedSorts) {
      ctx.setLogic("QF_AUFBV")
    } else {
      ctx.setLogic("QF_ABV")
    }
    ctx
  }

  def encodeSystem(sys: TransitionSystem, ctx: SolverContext, config: Config): TransitionSystemSmtEncoding = {
    val doUnroll = ctx.solver.supportsUninterpretedSorts || config.unroll
    val encoding = if (doUnroll) {
      new CompactSmtEncoding(sys)
    } else {
      new UnrollSmtEncoding(sys)
    }
    encoding.defineHeader(ctx)
    encoding.init(ctx)
    encoding
  }

  def applySynthAssignment(sys: TransitionSystem, assignment: Assignment): TransitionSystem = {
    val nameToValue = assignment.toMap

    // this assumes that all synthesis variables states have already been removed
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym: BVSymbol if isSynthName(sym.name) =>
        val value = nameToValue(sym.name)
        BVLiteral(value, sym.width)
      case BVIte(cond, tru, fals) => // do some small constant prop
        onExpr(cond) match {
          case True()  => onExpr(tru)
          case False() => onExpr(fals)
          case cc: BVExpr => BVIte(cc, onExpr(tru).asInstanceOf[BVExpr], onExpr(fals).asInstanceOf[BVExpr])
        }
      case other => SMTExprMap.mapExpr(other, onExpr)
    }

    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(signals = signals)
  }
}

case class RepairStats(solverTimeNs: Long, pastK: Int = -1, futureK: Int = -1)

sealed trait RepairResult {
  def isSuccess:         Boolean = false
  def noRepairNecessary: Boolean = false
  def cannotRepair:      Boolean = false
  def stats: RepairStats
}

/** indicates that the provided system and testbench pass for all possible unconstraint inputs and initial states */
case class NoRepairNecessary(stats: RepairStats) extends RepairResult {
  override def noRepairNecessary: Boolean = true
}

/** indicates that no repair was found, this probably due to constraints in our repair templates */
case class CannotRepair(stats: RepairStats) extends RepairResult {
  override def cannotRepair: Boolean = true
}

/** indicates that the repair was successful and provides the repaired system */
case class RepairSuccess(solutions: Seq[Solution], stats: RepairStats) extends RepairResult {
  require(solutions.nonEmpty, "A success requires at least one solution.")
  override def isSuccess: Boolean = true
}

/** A solution to the repair problem. */
case class Solution(assignments: Seq[(String, BigInt)])
