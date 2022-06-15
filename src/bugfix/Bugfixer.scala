// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix

import maltese.mc._

object Bugfixer {
  def main(args: Array[String]): Unit = {
    val parser = new ArgumentParser()
    val conf = parser.parse(args, Arguments(None, None)).get
    val repaired = repair(conf.design.get, conf.testbench.get)
    // print result
    repaired match {
      case Some(value) =>
        println("Repaired!")
      case None =>
        println("FAILED to repair")
    }
  }

  def repair(design: os.Path, testbench: os.Path): Option[TransitionSystem] = {
    // load design and testbench
    val sys = Btor2.load(design)
    val tb = loadTestbench(testbench)
    checkTestbenchSignals(sys, tb)
    val repaired = Simple.repair(design.baseName, sys, tb)


    repaired.foreach { fixed =>
      println("BEFORE:")
      println(sys.serialize)
      println("")
      println("AFTER:")
      println(fixed.serialize)
    }

    repaired
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
}

case class Testbench(signals: Seq[String], values: Seq[Seq[Option[BigInt]]])
