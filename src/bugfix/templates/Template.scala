// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix.templates

import maltese.mc._
import maltese.smt._

/** a repair template that can be applied to an existing system */
trait Template {
  // add repair template to the transition system
  def apply(sys: TransitionSystem, namespace: Namespace): TemplateApplication
  // repair system from solver result
  def repair(app: TemplateApplication, results: Map[String, BigInt]): RepairResult
}

trait TemplateApplication {
  /// transition system with repair template applied
  def sys: TransitionSystem
  /// synthesis constants used by repair template
  def consts: Seq[BVSymbol]
  /// synthesis soft constraints
  def softConstraints: Seq[BVExpr]
  // sanity check
  assert(softConstraints.forall(_.width == 1), "all soft constraints must be boolean formulas")
}

case class RepairResult(sys: TransitionSystem, changed: Boolean)
