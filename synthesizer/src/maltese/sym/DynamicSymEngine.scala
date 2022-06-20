// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>
package maltese.sym

import maltese.mc._
import maltese.smt._

import scala.collection.mutable

object DynamicSymEngine {
  def apply(sys: TransitionSystem, noInit: Boolean = false): DynamicSymEngine =
    new DynamicSymEngine(sys, noInit)
}

class DynamicSymEngine private (sys: TransitionSystem, noInit: Boolean) {}
