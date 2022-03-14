// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes

import maltese.mc

object PassManager {
  def apply(passes: Iterable[Pass]): PassManager = new PassManager(passes)
}

class PassManager private (val passes: Iterable[Pass]) {
  def run(sys: mc.TransitionSystem, trace: Boolean = false): mc.TransitionSystem = {
    passes.foldLeft(sys) { case (sys, pass) =>
      val next = pass.run(sys)
      if (trace) {
        val didChange = sys.serialize != next.serialize
        if (didChange) {
          println(s"- ${pass.name}:")
          println("   - Signal Count: " + next.signals.size)
        } else {
          println(s"- ${pass.name}: NO CHANGE")
        }
      }
      next
    }
  }
}
