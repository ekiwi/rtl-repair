// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import maltese.mc._
import maltese.passes._
import maltese.smt.BVLiteral
import scopt.OptionParser

case class Args(filename: Option[os.Path] = None, simplify: Boolean = false, zeroUnnamed: Boolean = false)

class ArgumentParser extends OptionParser[Args]("btor-viewer") {
  head("btor-viewer", "0.2")
  arg[String]("<file>")
    .required()
    .action((a, args) => args.copy(filename = Some(os.Path(a, os.pwd))))
    .text("btor file to display")
  opt[Unit]('s', "simplify")
    .action((_, args) => args.copy(simplify = true))
    .text("simplify system before printing")
  opt[Unit]('z', "zero-unnamed-inputs")
    .action((_, args) => args.copy(zeroUnnamed = true))
    .text("replaces all unnamed inputs with constant zero")
}

object BtorViewer {
  def main(args: Array[String]): Unit = {
    val parser = new ArgumentParser()
    val arguments = parser.parse(args, Args()).get
    val s0 = Btor2.load(arguments.filename.get)
    val s1 = if (arguments.zeroUnnamed) { zeroUnnamedInputs(s0) }
    else { s0 }
    val s2 = if (arguments.simplify) { simplifySystem(s1) }
    else { s1 }
    println(s2.serialize)
  }

  private def simplifySystem(sys: TransitionSystem): TransitionSystem = PassManager(passes).run(sys, trace = false)

  private val passes: Iterable[Pass] = Seq(
    Simplify,
    new Inline,
    new DeadCodeElimination(removeUnusedInputs = true),
    Simplify,
    new Inline,
    new DeadCodeElimination(removeUnusedInputs = true),
    Simplify

    // PrintSystem,
  )

  private def zeroUnnamedInputs(sys: TransitionSystem): TransitionSystem = {
    val (unnamed, inputs) = sys.inputs.partition(_.name.startsWith("_input_"))
    val signals = unnamed.map(i => Signal(i.name, BVLiteral(0, i.width))) ++: sys.signals
    sys.copy(inputs = inputs, signals = signals)
  }
}
