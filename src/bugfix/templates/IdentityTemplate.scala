// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix.templates
import maltese.mc._
import maltese.smt._

case object IdentityTemplateApplication extends TemplateApplication {
  override def consts: Seq[BVSymbol] = Seq()
  override def softConstraints: Seq[BVExpr] = Seq()
  override def performRepair(sys: TransitionSystem, results: Map[String, BigInt]): RepairResult =
    RepairResult(sys, changed = false)

}

/** Does not actually repair anything but can be useful to determine that the system is correct without any changes. */
object IdentityTemplate extends RepairTemplate {
  override def apply(sys: TransitionSystem, namespace: Namespace): (TransitionSystem, TemplateApplication) = {
    (sys, IdentityTemplateApplication)
  }
}
