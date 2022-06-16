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
    val conf = parser.parse(args, Arguments(None, None)).get
    val repaired = repair(conf.design.get, conf.testbench.get, verbose = true)
    // print result
    repaired match {
      case Some(value) =>
        println("Repaired!")
      case None =>
        println("FAILED to repair")
    }
  }

  def repair(design: os.Path, testbench: os.Path, verbose: Boolean = false): Option[TransitionSystem] = {
    // load design and testbench and validate them
    val sys = Btor2.load(design)
    val tb = Testbench.removeRow("time", Testbench.load(testbench))
    Testbench.checkSignals(sys, tb)

    // do repair
    if (verbose) println(s"Trying to repair: ${design.baseName}")
    val templates = Seq(ReplaceLiteral)
    val repaired = doRepair(sys, tb, templates, verbose)


    // print out results
    if (false) {
      println("BEFORE:")
      println(sys.serialize)
      println("")
      println("AFTER:")
      println(repaired.serialize)
    }

    Some(repaired)
  }

  private def doRepair(sys: TransitionSystem, tb: Testbench, templates: Seq[RepairTemplate], verbose: Boolean, seed: Long = 0): TransitionSystem = {
    val rand = new scala.util.Random(seed)
    val namespace = Namespace(sys)

    // apply repair templates
    val (transformedSys, templateApplications) = applyTemplates(sys, namespace, templates)
    val synthesisConstants = templateApplications.flatMap(_.consts)
    val softConstraints = templateApplications.flatMap(_.softConstraints)


    // load system and communicate to solver
    val encoding = new CompactEncoding(transformedSys)
    // select solver
    val solver = if (true) {
      Z3SMTLib
    } else {
      OptiMathSatSMTLib
    }
    val ctx = solver.createContext(debugOn = false) // set debug to true to see commands sent to SMT solver
    ctx.setLogic("ALL")
    // define synthesis constants
    synthesisConstants.foreach(c => ctx.runCommand(DeclareFunction(c, Seq())))
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // add soft constraints to change as few constants as possible
    softConstraints.foreach(ctx.softAssert(_))

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
      case IsSat => if (verbose) println("Solution found:")
      case IsUnSat => throw new RuntimeException(s"No possible solution could be found")
      case IsUnknown => throw new RuntimeException(s"Unknown result from solver.")
    }

    val results = synthesisConstants.map(c => c.name -> ctx.getValue(c).get).toMap
    ctx.close()

    // do repair
    val repaired = repairWithTemplates(transformedSys, results, templateApplications)
    if (repaired.changed) {
    } else {
      if (verbose) println("No change necessary")
    }

    repaired.sys
  }


  private def applyTemplates(sys: TransitionSystem, namespace: Namespace, templates: Seq[RepairTemplate]): (TransitionSystem, Seq[TemplateApplication]) = {
    val base = IdentityTemplate.apply(sys, namespace)
    val transformed = templates.scanLeft[(TransitionSystem, TemplateApplication)](base) { case (prev, template) =>
      template.apply(prev._1, namespace)
    }
    val transformedSys = transformed.last._1
    val applications = transformed.map(_._2)
    (transformedSys, applications)
  }

  private def repairWithTemplates(transformedSys: TransitionSystem, results: Map[String, BigInt], applications: Seq[TemplateApplication]): RepairResult = {
    val base = RepairResult(transformedSys, changed = false)
    val res: Seq[RepairResult] = applications.scanRight[RepairResult](base) { case (app, prev) =>
      app.performRepair(prev.sys, results)
    }
    val anyChanged = res.exists(_.changed)
    val repairedSys = res.head.sys
    RepairResult(repairedSys, anyChanged)
  }


}

case class Testbench(signals: Seq[String], values: Seq[Seq[Option[BigInt]]])

object Testbench {
  def load(filename: os.Path): Testbench = {
    val lines = os.read.lines(filename)
    val signals = lines.head.split(",").map(_.trim)
    val values = lines.drop(1).map { line =>
      val v = line.split(",").map(_.trim).map {
        case "x" => None
        case num => Some(BigInt(num, 10))
      }.toSeq
      assert(v.length == signals.length,
        s"expected ${signals.length} values, but got ${v.length} in line $line")
      v
    }.toSeq
    Testbench(signals, values)
  }

  def removeRow(name: String, tb: Testbench): Testbench = {
    if (tb.signals.contains(name)) {
      val pos = tb.signals.indexOf(name)
      val values = tb.values.map { row =>
        // remove pos
        row.take(pos) ++ row.drop(pos + 1)
      }
      val signals = tb.signals.take(pos) ++ tb.signals.drop(pos + 1)
      tb.copy(signals = signals, values = values)
    } else {
      tb
    }
  }

  /** makes sure that all inputs and outputs are defined in the tb */
  def checkSignals(sys: TransitionSystem, tb: Testbench): Unit = {
    val inputs = sys.inputs.map(_.name).toSet
    val outputs = sys.signals.filter(_.lbl == IsOutput).map(_.name).toSet
    val tbSignals = tb.signals.toSet - "time"
    val unknownSignals = tbSignals diff (inputs union outputs)
    val missingSignals = (inputs union outputs) diff tbSignals
    assert(unknownSignals.isEmpty, "Testbench contains unknown signals: " + unknownSignals.mkString(", "))
    assert(missingSignals.isEmpty, "Testbench is missing signals from the design: " + missingSignals.mkString(", "))
  }
}
