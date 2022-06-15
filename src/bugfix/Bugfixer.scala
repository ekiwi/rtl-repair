// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix

import maltese.mc._

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
    // load design and testbench
    val sys = Btor2.load(design)
    val tb = removeRow("time", loadTestbench(testbench))
    checkTestbenchSignals(sys, tb)
    val repaired = Simple.repair(design.baseName, sys, tb, verbose)

    if(false) {
      println("BEFORE:")
      println(sys.serialize)
      println("")
      println("AFTER:")
      println(repaired.serialize)
    }

    Some(repaired)
  }

  // makes sure that all inputs and outputs are defined in the tb
  private def checkTestbenchSignals(sys: TransitionSystem, tb: Testbench): Unit = {
    val inputs = sys.inputs.map(_.name).toSet
    val outputs = sys.signals.filter(_.lbl == IsOutput).map(_.name).toSet
    val tbSignals = tb.signals.toSet - "time"
    val unknownSignals = tbSignals diff (inputs union outputs)
    val missingSignals = (inputs union outputs) diff tbSignals
    assert(unknownSignals.isEmpty, "Testbench contains unknown signals: " + unknownSignals.mkString(", "))
    assert(missingSignals.isEmpty, "Testbench is missing signals from the design: " + missingSignals.mkString(", "))
  }

  def loadTestbench(filename: os.Path): Testbench = {
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
    if(tb.signals.contains(name)) {
      val pos = tb.signals.indexOf(name)
      val values = tb.values.map { row =>
        // remove pos
        row.take(pos) ++ row.drop(pos + 1)
      }
      val signals = tb.signals.take(pos) ++ tb.signals.drop(pos + 1)
      tb.copy(signals = signals, values = values)
    } else { tb }
  }
}

case class Testbench(signals: Seq[String], values: Seq[Seq[Option[BigInt]]])
