// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix

import bugfix.templates._
import maltese.mc._
import maltese.smt._

object Bugfixer {
  def main(args: Array[String]): Unit = {
    val parser = new ArgumentParser()
    val arguments = parser.parse(args, Arguments(None, None)).get
    val repaired = repair(arguments.design.get, arguments.testbench.get, arguments.config)
    // print result
    repaired match {
      case NoRepairNecessary => println("Nothing to repair.")
      case CannotRepair      => println("FAILED to repair.")
      case RepairSuccess(_)  => println("Repaired!")
    }
  }

  def repair(design: os.Path, testbench: os.Path, config: Config): RepairResult = {
    // load design and testbench and validate them
    val sys = Btor2.load(design)
    val tbRaw = Testbench.removeRow("time", Testbench.load(testbench))
    val tb = Testbench.checkSignals(sys, tbRaw, verbose = config.verbose)

    // do repair
    if (config.verbose) println(s"Trying to repair: ${design.baseName}")
    val repaired = doRepair(sys, tb, config)

    // print out results
    repaired match {
      case NoRepairNecessary =>
      case CannotRepair      =>
      case RepairSuccess(repairedSys) =>
        if (false) {
          println("BEFORE:")
          println(sys.serialize)
          println("")
          println("AFTER:")
          println(repairedSys.serialize)
        }
    }

    repaired
  }

  private def doRepair(sys: TransitionSystem, tb: Testbench, config: Config): RepairResult = {
    // create solver context
    val solver = config.solver
    val ctx = solver.createContext(debugOn = config.debugSolver)
    ctx.setLogic("ALL")
    val namespace = Namespace(sys)

    // find free variables for the original system and declare them
    val freeVars = FreeVars.findFreeVars(sys, tb, namespace)
    freeVars.allSymbols.foreach(sym => ctx.runCommand(DeclareFunction(sym, List())))

    // find assignments to free variables that will make the testbench fail
    val freeVarAssignment = findFreeVarAssignment(ctx, sys, tb, freeVars, config) match {
      case Some(value) => value
      case None        => return NoRepairNecessary // testbench does not in fact fail
    }

    // use the failing assignment for free vars
    freeVars.addConstraints(ctx, freeVarAssignment)

    // apply repair templates
    val (transformedSys, templateApplications) = applyTemplates(sys, namespace, config.templates)
    val synthesisConstants = templateApplications.flatMap(_.consts)
    val softConstraints = templateApplications.flatMap(_.softConstraints)

    // instantiate testbench constraints
    synthesisConstants.foreach(c => ctx.runCommand(DeclareFunction(c, Seq())))
    instantiateTestbench(ctx, transformedSys, tb, freeVars, assertDontAssumeOutputs = false)

    // add soft constraints
    softConstraints.foreach(ctx.softAssert(_))

    // try to synthesize constants
    ctx.check() match {
      case IsSat => if (config.verbose) println("Solution found:")
      case IsUnSat =>
        if (config.verbose) println("No possible solution found. Cannot repair. :(")
        return CannotRepair
      case IsUnknown => throw new RuntimeException(s"Unknown result from solver.")
    }

    val results = synthesisConstants.map(c => c.name -> ctx.getValue(c).get).toMap
    ctx.close()

    // do repair
    val repaired = repairWithTemplates(transformedSys, results, templateApplications, verbose = config.verbose)
    if (repaired.changed) {} else {
      if (config.verbose) println("No change necessary")
    }

    RepairSuccess(repaired.sys)
  }

  /** find assignments to free variables that will make the testbench fail */
  private def findFreeVarAssignment(
    ctx:      SolverContext,
    sys:      TransitionSystem,
    tb:       Testbench,
    freeVars: FreeVars,
    config:   Config
  ): Option[Seq[(String, BigInt)]] = {
    ctx.push()
    instantiateTestbench(ctx, sys, tb, freeVars, assertDontAssumeOutputs = true)
    ctx.check() match {
      case IsSat => // OK
      case IsUnSat =>
        if (config.verbose)
          println(s"Original system is correct for all starting states and undefined inputs. Nothing to do.")
        return None
      case IsUnknown => throw new RuntimeException(s"Unknown result from solver.")
    }
    val freeVarAssignment = freeVars.readValues(ctx)
    if (config.verbose) {
      println("Assignment for free variables which makes the testbench fail:")
      freeVarAssignment.foreach { case (name, value) => println(s" - $name = $value") }
    }
    ctx.pop()
    Some(freeVarAssignment)
  }

  /** Unrolls the system and adds all testbench constraints. Returns symbols for all undefined initial states and inputs. */
  private def instantiateTestbench(
    ctx:                     SolverContext,
    sys:                     TransitionSystem,
    tb:                      Testbench,
    freeVars:                FreeVars,
    assertDontAssumeOutputs: Boolean
  ): Unit = {
    val sysWithInitVars = FreeVars.addStateInitFreeVars(sys, freeVars)

    // load system and communicate to solver
    val encoding = new CompactEncoding(sysWithInitVars)

    // define synthesis constants
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // get some meta data for testbench application
    val signalWidth = (
      sysWithInitVars.inputs.map(i => i.name -> i.width) ++
        sysWithInitVars.signals.filter(_.lbl == IsOutput).map(s => s.name -> s.e.asInstanceOf[BVExpr].width)
    ).toMap
    val tbSymbols = tb.signals.map(name => BVSymbol(name, signalWidth(name)))
    val isInput = sysWithInitVars.inputs.map(_.name).toSet
    val getFreeInputVar = freeVars.inputs.toMap

    // unroll system k-1 times
    tb.values.drop(1).foreach(_ => encoding.unroll(ctx))

    // collect input assumption and assert them
    val inputAssumptions = tb.values.zipWithIndex.flatMap { case (values, ii) =>
      values.zip(tbSymbols).flatMap {
        case (value, sym) if isInput(sym.name) =>
          val signal = encoding.getSignalAt(sym, ii)
          value match {
            case None => // assign arbitrary value if input is X
              val freeVar = getFreeInputVar(sym.name -> ii)
              Some(BVEqual(signal, freeVar))
            case Some(num) =>
              Some(BVEqual(signal, BVLiteral(num, sym.width)))
          }
        case _ => None
      }
    }.toList
    ctx.assert(BVAnd(inputAssumptions))

    // collect output constraints and either assert or assume them
    val outputAssertions = tb.values.zipWithIndex.flatMap { case (values, ii) =>
      values.zip(tbSymbols).flatMap {
        case (value, sym) if !isInput(sym.name) =>
          val signal = encoding.getSignalAt(sym, ii)
          value match {
            case Some(num) =>
              Some(BVEqual(signal, BVLiteral(num, sym.width)))
            case None => None // no constraint
          }
        case _ => None
      }
    }.toList
    if (assertDontAssumeOutputs) {
      ctx.assert(BVNot(BVAnd(outputAssertions)))
    } else {
      ctx.assert(BVAnd(outputAssertions))
    }
  }

  private def applyTemplates(
    sys:       TransitionSystem,
    namespace: Namespace,
    templates: Seq[RepairTemplate]
  ): (TransitionSystem, Seq[TemplateApplication]) = {
    val base = IdentityTemplate.apply(sys, namespace)
    val transformed = templates.scanLeft[(TransitionSystem, TemplateApplication)](base) { case (prev, template) =>
      template.apply(prev._1, namespace)
    }
    val transformedSys = transformed.last._1
    val applications = transformed.map(_._2)
    (transformedSys, applications)
  }

  private def repairWithTemplates(
    transformedSys: TransitionSystem,
    results:        Map[String, BigInt],
    applications:   Seq[TemplateApplication],
    verbose:        Boolean
  ): TemplateRepairResult = {
    val base = TemplateRepairResult(transformedSys, changed = false)
    val res = applications.scanRight[TemplateRepairResult](base) { case (app, prev) =>
      app.performRepair(prev.sys, results, verbose = verbose)
    }
    val anyChanged = res.exists(_.changed)
    val repairedSys = res.head.sys
    TemplateRepairResult(repairedSys, anyChanged)
  }
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
case class RepairSuccess(sys: TransitionSystem) extends RepairResult {
  override def isSuccess: Boolean = true
}
