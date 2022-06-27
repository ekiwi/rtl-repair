// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc.{IsOutput, TransitionSystem}

case class Testbench(signals: Seq[String], values: Seq[Seq[Option[BigInt]]]) {
  def length: Int = values.length
}

object Testbench {
  def load(filename: os.Path): Testbench = {
    val lines = os.read.lines(filename)
    val signals = lines.head.split(",").map(_.trim)
    val values = lines
      .drop(1)
      .map { line =>
        val v = line
          .split(",")
          .map(_.trim)
          .map {
            case "x" | "X" => None
            case num       => Some(BigInt(num, 10))
          }
          .toSeq
        assert(v.length == signals.length, s"expected ${signals.length} values, but got ${v.length} in line $line")
        v
      }
      .toSeq
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

  /** makes sure that all inputs and outputs are defined in the tb and adds `X` for any undefined signals of the system */
  def checkSignals(sys: TransitionSystem, tb: Testbench, verbose: Boolean): Testbench = {
    val inputs = sys.inputs.map(_.name).toSet
    val outputs = sys.signals.filter(_.lbl == IsOutput).map(_.name).toSet
    val tbSignals = tb.signals.toSet - "time"
    val unknownSignals = tbSignals.diff(inputs.union(outputs))
    val missingInputs = inputs.diff(tbSignals)
    val missingOutputs = outputs.diff(tbSignals)
    assert(unknownSignals.isEmpty, "Testbench contains unknown signals: " + unknownSignals.mkString(", "))
    if (verbose) {
      if (missingInputs.nonEmpty) {
        println(s"Design inputs missing from the testbench: " + missingInputs.mkString(", "))
      }
      if (missingOutputs.nonEmpty) {
        println(s"Design outputs missing from the testbench: " + missingOutputs.mkString(", "))
      }
    }
    val missingSignals = missingInputs.toList ++ missingOutputs.toList
    if (missingSignals.isEmpty) {
      tb // no need to add anything to the testbench
    } else {
      val signals = tb.signals ++ missingSignals
      val xs = missingSignals.map(_ => None)
      val values = tb.values.map(row => row ++ xs)
      tb.copy(signals = signals, values = values)
    }
  }
}
