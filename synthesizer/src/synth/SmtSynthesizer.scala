// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._

/** Takes in a Transition System with synthesis variables +  a testbench and tries to find a valid synthesis assignment. */
object SmtSynthesizer {
  def doRepair(sys: TransitionSystem, tb: Testbench, synthVars: SynthVars, config: Config): RepairResult = {
    // create solver context
    val solver = config.solver.get
    val ctx = solver.createContext(debugOn = config.debugSolver)
    ctx.setLogic("ALL")
    val namespace = Namespace(sys)

    // declare synthesis variables
    synthVars.declare(ctx)

    // find free variables for the original system and declare them
    val freeVars = FreeVars.findFreeVars(sys, tb, namespace)
    freeVars.allSymbols.foreach(sym => ctx.runCommand(DeclareFunction(sym, List())))

    // find assignments to free variables that will make the testbench fail
    ctx.push()
    synthVars.assumeNoChange(ctx)
    val freeVarAssignment = findFreeVarAssignment(ctx, sys, tb, freeVars, config) match {
      case Some(value) => value
      case None        => ctx.close(); return NoRepairNecessary // testbench does not in fact fail
    }
    ctx.pop()

    ctx.push()
    // use the failing assignment for free vars
    freeVars.addConstraints(ctx, freeVarAssignment)

    // try to minimize the change
    synthVars.minimizeChange(ctx)
    instantiateTestbench(ctx, sys, tb, freeVars, assertDontAssumeOutputs = false)

    // try to synthesize constants
    ctx.check() match {
      case IsSat => if (config.verbose) println("Solution found:")
      case IsUnSat =>
        if (config.verbose) println("No possible solution found. Cannot repair. :(")
        ctx.close()
        return CannotRepair
      case IsUnknown =>
        ctx.close()
        throw new RuntimeException(s"Unknown result from solver.")
    }
    val results = synthVars.readAssignment(ctx)
    ctx.pop()

    // check to see if the synthesized constants work
    ctx.push()
    synthVars.assumeAssignment(ctx, results.toMap)
    findFreeVarAssignment(ctx, sys, tb, freeVars, config) match {
      case Some(value) =>
        throw new RuntimeException(
          s"TODO: the solution we found does not in fact work for all possible free variable assignments :("
        )
      case None => // all good, no more failure
    }
    ctx.pop()
    ctx.close()
    RepairSuccess(results)
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
}

case class SynthVars(change: List[BVSymbol], free: List[SMTSymbol]) {
  require(change.forall(_.width == 1), "change variables need to all be boolean")
  require(
    free.forall(_.isInstanceOf[BVSymbol]),
    "currently only BV symbols are supported, array support should be possible with some engineering work"
  )
  def declare(ctx:        SolverContext): Unit = vars.foreach(sym => ctx.runCommand(DeclareFunction(sym, List())))
  def assumeNoChange(ctx: SolverContext): Unit = change.foreach { sym =>
    ctx.assert(BVNot(sym))
  }
  def minimizeChange(ctx: SolverContext): Unit = change.foreach { sym =>
    ctx.softAssert(BVNot(sym))
  }
  def vars: List[BVSymbol] = change ++ free.map(_.asInstanceOf[BVSymbol])
  def readAssignment(ctx: SolverContext): List[(String, BigInt)] = vars.map { sym =>
    sym.name -> ctx.getValue(sym).get
  }
  def assumeAssignment(ctx: SolverContext, assignment: Map[String, BigInt]): Unit = vars.foreach { sym =>
    val value = assignment(sym.name)
    ctx.assert(BVEqual(sym, BVLiteral(value, sym.width)))
  }

}
