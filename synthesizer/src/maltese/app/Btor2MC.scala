// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.app

import java.io.File
import maltese.mc._
import maltese.smt
import maltese.smt.BitwuzlaSMTLib

/** simple interface to all supported model checkers */
object Btor2MC extends App {
  if (args.length < 1) {
    println(s"please provide the name of a btor file")
  } else {
    val filename = os.pwd / args.head
    val sys = Btor2.load(filename)
    //val checker = new BtormcModelChecker
    val checker = new SMTModelChecker(BitwuzlaSMTLib)
    check(checker, sys, kMax = -1)
  }

  private def check(
    checker:  IsModelChecker,
    sys:      TransitionSystem,
    kMax:     Int,
    printSys: Boolean = false,
    debug:    Iterable[smt.BVSymbol] = List()
  ): Boolean = {
    val btorFile = sys.name + ".btor2"
    val vcdFile = sys.name + ".vcd"

    val fullSys = if (debug.isEmpty) { sys }
    else { observe(sys, debug) }
    if (printSys) { println(fullSys.serialize) }
    val res = checker.check(fullSys, kMax = kMax, fileName = Some(btorFile))
    res match {
      case ModelCheckFail(witness) =>
        val sim = new TransitionSystemSimulator(fullSys)
        sim.run(witness, vcdFileName = Some(vcdFile))
        println(s"${fullSys.name} fails!")
        false
      case ModelCheckSuccess() =>
        println(s"${fullSys.name} works!")
        true
    }
  }

  private def observe(sys: TransitionSystem, signals: Iterable[smt.BVSymbol]): TransitionSystem = {
    val oState = signals.map(s => State(s.rename(s.name + "$o"), None, None))
    val constraints = signals.map(s => Signal(s.name + "$eq", smt.BVEqual(s, s.rename(s.name + "$o")), IsConstraint))
    sys.copy(states = sys.states ++ oState, signals = sys.signals ++ constraints)
  }
}
