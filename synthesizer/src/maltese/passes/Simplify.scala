// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes

import maltese.mc._
import maltese.smt.SMTSimplifier

/** simplifies signals where possible */
object Simplify extends Pass {
  override def name: String = "Simplify"

  override def run(sys: TransitionSystem): TransitionSystem = {
    sys.copy(signals = sys.signals.map(simplify))
  }
  private def simplify(s: Signal): Signal = s.copy(e = SMTSimplifier.simplify(s.e))
}
