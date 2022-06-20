// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese

import maltese.sym.{MultiSeSymEngine, Options}
import maltese.passes._
import maltese.mc.{IsBad, IsConstraint, TransitionSystem}

object MalteseApp extends App {
  if (args.length < 1) {
    // println(s"please provide the name of a btor file")
    val d = os.pwd / "benchmarks" / "hwmcc19" / "bv" / "goel" / "crafted" / "toy_lock_4.btor2"
    //val d = "benchmarks/hwmcc19/bv/goel/crafted/cal10.btor2"
    //val d = "benchmarks/hwmcc19/bv/wolf/2019A/picorv32_mutBX_nomem-p0.btor"
    Maltese.load(d)
  } else {
    Maltese.load(os.pwd / args.head)
  }
}

object Maltese {
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

  def load(filename: os.Path): Unit = {
    // load transition system from file
    val sys = mc.Btor2.load(filename)

    println(s"Loaded $filename")

    val simplified = simplifySystem(sys)

    //val e = getConstraints(simplified, doInit = false)
    val e = check(simplified, kMax = 1)
    //val e = check(sys)

    println()
    e.printStatistics()
  }

  def simplifySystem(sys: TransitionSystem): TransitionSystem = PassManager(passes).run(sys, trace = true)

  def check(sys: TransitionSystem, kMax: Int = 2, doInit: Boolean = true): MultiSeSymEngine = {
    val e = MultiSeSymEngine(sys, noInit = !doInit)

    val bad = sys.signals.filter(_.lbl == IsBad).map(_.name)
    bad.foreach { b =>
      (0 to kMax).foreach { step =>
        val r = e.signalAt(b, step)
        println(s"$b@$step: $r")
      }
    }

    e
  }

  def getConstraints(sys: TransitionSystem, doInit: Boolean): MultiSeSymEngine = {
    val opts = Options.Default.copy(ImportBooleanExpressionsIntoGuard = true)
    val e = MultiSeSymEngine(sys, !doInit, opts)
    val const = sys.signals.filter(_.lbl == IsConstraint).map(_.name)
    const.take(105).zipWithIndex.foreach { case (c, i) =>
      print(s"$i.")
      val step = 0
      val r = e.signalAt(c, step)
    /*val rString = r.toString
      if(rString.length < 200) {
        println(s"$c@$step: $rString")
      } else {
        println(s"skipping $c@$step because the resulting string is too big")
      }*/
    }
    e
  }
}
