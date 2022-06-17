// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix.templates

import maltese.mc._
import maltese.smt._

/** a repair template that can be applied to an existing system */
trait RepairTemplate {
  // add repair template to the transition system
  def apply(sys: TransitionSystem, namespace: Namespace): (TransitionSystem, TemplateApplication)
}

trait TemplateApplication {
  /// synthesis constants used by repair template
  def consts: Seq[BVSymbol]
  /// synthesis soft constraints
  def softConstraints: Seq[BVExpr]
  /// handle to the template used to generate this application
  def performRepair(sys: TransitionSystem, results: Map[String, BigInt], verbose: Boolean): TemplateRepairResult
  // sanity check
  assert(softConstraints.forall(_.width == 1), "all soft constraints must be boolean formulas")
}

case class TemplateRepairResult(sys: TransitionSystem, changed: Boolean)
