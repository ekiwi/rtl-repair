// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc.{IsOutput, TransitionSystem, TransitionSystemSim, TransitionSystemSimulator}
import maltese.smt.BVType

import java.io.PrintWriter
import scala.collection.mutable

case class Testbench(signals: Seq[String], values: Seq[Seq[Option[BigInt]]]) {
  def length: Int = values.length
  def slice(from: Int, until: Int): Testbench = copy(values = values.slice(from, until))
}

object Testbench {
  def load(filename: os.Path): Testbench = {
    val lines = os.read.lines(filename)
    val signals = lines.head.split(",").map(parseCsvItem)
    val values = lines
      .drop(1)
      .map { line =>
        val v = line
          .split(",")
          .map(parseCsvItem)
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

  private def parseCsvItem(item: String): String = {
    val trimmed = item.trim
    if (trimmed.length <= 1) {
      trimmed
    } else if (trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
      trimmed.drop(1).dropRight(1).trim
    } else {
      trimmed
    }
  }

  def save(filename: os.Path, tb: Testbench): Unit = {
    val out = new PrintWriter(os.write.outputStream(filename))
    def outLine(line: String): Unit = out.println(line)
    outLine(tb.signals.mkString(", "))
    tb.values.foreach { values =>
      val line = values.map {
        case Some(value) => value.toString(10)
        case None        => "x"
      }.mkString(", ")
      outLine(line)
    }
    out.close()
  }

  def removeColumn(name: String, tb: Testbench): Testbench = {
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

  /** extracts name and index of each input to the testbench */
  private def filterInputs(sys: TransitionSystem, tb: Testbench): Seq[(String, Int)] = {
    val isInput = sys.inputs.map(_.name).toSet
    tb.signals.zipWithIndex.filter(t => isInput(t._1))
  }

  /** extracts name and index of each output to the testbench */
  private def filterOutputs(sys: TransitionSystem, tb: Testbench): Seq[(String, Int)] = {
    val isOutput = sys.signals.filter(_.lbl == IsOutput).map(_.name).toSet
    tb.signals.zipWithIndex.filter(t => isOutput(t._1))
  }

  /**
    */
  private def getValueMap(signals: Seq[(String, Int)], values: Seq[Option[BigInt]]): Map[String, BigInt] = {
    signals.flatMap { case (name, ii) =>
      values(ii) match {
        case Some(value) => Some(name -> value)
        case None        => None
      }
    }.toMap
  }

  /** concretely execute the testbench on the given transition system */
  def run(
    sys:            TransitionSystem,
    tb:             Testbench,
    verbose:        Boolean,
    vcd:            Option[os.Path] = None,
    earlyExitAfter: Int = -1,
    traceState:     Boolean = false
  ): TestbenchResult = {
    // we need all starting states to be concrete
    sys.states.foreach(s => assert(s.init.isDefined, s"uninitialized state $s"))
    val traceStates = if (traceState) {
      sys.states.filter(s => !Synthesizer.isSynthName(s.name) && s.sym.tpe.isInstanceOf[BVType]).sortBy(_.name)
    } else { Seq() }
    val inputs = filterInputs(sys, tb)
    val outputs = filterOutputs(sys, tb)
    val sim = new TransitionSystemSim(sys, vcd)
    var failAt = -1
    val observed = mutable.ListBuffer[Map[String, BigInt]]()
    tb.values.foreach { values =>
      val step = sim.getStepCount
      // early exit
      if (earlyExitAfter >= 0 && failAt >= 0 && (step - failAt) > earlyExitAfter) {
        sim.finish()
        return TestbenchResult(observed.toSeq, failAt)
      }
      // apply input and evaluate signals
      sim.poke(getValueMap(inputs, values))
      sim.update()
      // print state
      traceStates.foreach { state =>
        val value = sim.peek(state.name).toString(2)
        val width = state.sym.tpe.asInstanceOf[BVType].width
        println(s"${state.name}@$step = ${value.padTo(width, '0')}")
      }
      if (traceStates.nonEmpty) {
        println()
      }
      // check outputs
      val outVals = outputs.map { case (name, ii) =>
        val actual = sim.peek(name)
        values(ii) match {
          case Some(expected) =>
            val correct = if (expected != actual) {
              if (failAt < 0) {
                failAt = step
              }
              if (step == failAt) {
                if (verbose) println(s"$expected != $actual $name@$step")
              }
              0
            } else { 1 }
            sim.printSignal(s"@${name}_correct", correct, 1)
          case None => // ignore
        }
        name -> actual
      }
      // copy state
      val state = sys.states.map(s => s.name -> sim.peek(s.name))
      // advance state
      sim.step()
      // report output and state values
      observed.append((outVals ++ state).toMap)
    }
    sim.finish()
    TestbenchResult(observed.toSeq, failAt)
  }

  /** adds a random value for every undefined (None) input */
  def addRandomInput(sys: TransitionSystem, tb: Testbench, rnd: scala.util.Random): Testbench = {
    val inputs = sys.inputs.map(ii => ii.name -> ii.width).toMap
    val values = tb.values.map { values =>
      values.zip(tb.signals).map {
        case (None, name) if inputs.contains(name) =>
          Some(BigInt(inputs(name), rnd))
        case (value, _) => value
      }
    }
    tb.copy(values = values)
  }

}

case class TestbenchResult(values: Seq[Map[String, BigInt]], failAt: Int = -1) {
  def failed: Boolean = failAt >= 0
}
