// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix

import bugfix.templates.{ReplaceLiteral, TemplateApplication}
import maltese.mc._
import maltese.smt.{BVLiteral, _}

// playing around with a simple repair
object Simple {
  def repair(name: String, sys: TransitionSystem, tb: Testbench, verbose: Boolean): TransitionSystem = {
    if(verbose) println(s"Trying to repair: $name")
    // try to synthesize a fix
    fixConstants(sys, tb, verbose)
  }


  // simple repair approach that tries to find a replacements for constants in the circuit
  private def fixConstants(sys: TransitionSystem, tb: Testbench, verbose: Boolean, seed: Long = 0): TransitionSystem = {
    val rand = new scala.util.Random(seed)
    val namespace = Namespace(sys)

    // apply repair template
    val repair: TemplateApplication = ReplaceLiteral.apply(sys, namespace)


    // load system and communicate to solver
    val encoding = new CompactEncoding(repair.sys)
    // select solver
    val solver = if(true) { Z3SMTLib } else { OptiMathSatSMTLib }
    val ctx = solver.createContext(debugOn = false) // set debug to true to see commands sent to SMT solver
    ctx.setLogic("ALL")
    // define synthesis constants
    repair.consts.foreach(c => ctx.runCommand(DeclareFunction(c, Seq())))
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // add soft constraints to change as few constants as possible
    repair.softConstraints.foreach(ctx.softAssert(_))

    // get some meta data for testbench application
    val signalWidth = (
      sys.inputs.map(i => i.name -> i.width) ++
        sys.signals.filter(_.lbl == IsOutput).map(s => s.name -> s.e.asInstanceOf[BVExpr].width)
      ).toMap
    val tbSymbols = tb.signals.map(name => BVSymbol(name, signalWidth(name)))
    val isInput = sys.inputs.map(_.name).toSet

    // unroll and compare results
    tb.values.zipWithIndex.foreach { case (values, ii) =>
      values.zip(tbSymbols).foreach { case (value, sym) =>
        val signal = encoding.getSignalAt(sym, ii)
        value match {
          case None if isInput(sym.name) => // assign random value if input is X
            ctx.assert(BVEqual(signal, BVLiteral(BigInt(sym.width, rand), sym.width)))
          case Some(num) =>
            ctx.assert(BVEqual(signal, BVLiteral(num, sym.width)))
          case None => // ignore
        }
      }
      encoding.unroll(ctx)
    }

    // try to synthesize constants
    ctx.check() match {
      case IsSat => if(verbose) println("Solution found:")
      case IsUnSat => throw new RuntimeException(s"No possible solution could be found")
      case IsUnknown => throw new RuntimeException(s"Unknown result from solver.")
    }

    val newConstants = repair.consts.map(c => c.name -> ctx.getValue(c).get).toMap
    ctx.close()

    // do repair
    val repaired = ReplaceLiteral.repair(repair, newConstants)
    if(repaired.changed) {

    } else {
      if(verbose) println("No change necessary")
    }


    repaired.sys
  }



}
