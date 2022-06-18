// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes

import maltese.smt._
import maltese.mc._

import scala.collection.mutable

/** Inlines signals:
  * - if the signal is only used once
  * - if it is a lead expression (symbol or constant)
  * This pass does not remove any symbols.
  * Use DeadCodeElimination to get rid of any unused signals after inlining.
  */
class Inline(inlineEverything: Boolean = false, conservative: Boolean = false) extends Pass {
  override def name: String = "Inline"

  // some setting to play around with
  private val InlineUseMax = 1
  private val InlineLeaves = true
  private val InlineIteInIte = false
  private val InlineConcatInSlice = !conservative
  private val InlineIteInSlice = !conservative

  override def run(sys: TransitionSystem): TransitionSystem = {
    val doInline = if (inlineEverything) {
      sys.signals.map(_.name).toSet
    } else {
      findSignalsToInline(sys)
    }

    if (doInline.isEmpty) {
      sys
    } else {
      val inlineExpr = mutable.HashMap[String, SMTExpr]()
      implicit val ctx: InliningContext = new InliningContext(doInline.contains, inlineExpr.get)
      val signals = sys.signals.map { signal =>
        val inlinedE = replaceSymbols(signal.e, false, false)
        inlineExpr(signal.name) = inlinedE
        signal.copy(e = inlinedE)
      }
      sys.copy(signals = signals)
    }
  }

  private class InliningContext(alwaysInline: String => Boolean, inlineExpr: String => Option[SMTExpr]) {
    def apply(name: String, inIte: Boolean, inSlice: Boolean): Option[SMTExpr] = (inIte, inSlice) match {
      case (_, _) if alwaysInline(name) => inlineExpr(name)
      case (true, false) => // in ite context
        inlineExpr(name) match {
          case Some(e @ (_: BVIte | _: ArrayIte)) if InlineIteInIte => Some(e)
          case _ => None
        }
      case (false, true) => // in slice context
        inlineExpr(name) match {
          case Some(e: BVConcat) if InlineConcatInSlice => Some(e)
          case Some(e: BVIte) if InlineIteInSlice => Some(e)
          case _ => None
        }
      case _ => None
    }
  }

  private def replaceSymbols(e: SMTExpr, inIte: Boolean, inSlice: Boolean)(implicit ctx: InliningContext): SMTExpr =
    e match {
      case s @ BVSymbol(name, _)       => ctx(name, inIte, inSlice).getOrElse(s)
      case s @ ArraySymbol(name, _, _) => ctx(name, inIte, inSlice).getOrElse(s)
      // context dependent inlining
      case ite:   BVIte   => SMTExprMap.mapExpr(ite, replaceSymbols(_, true, false))
      case slice: BVSlice => SMTExprMap.mapExpr(slice, replaceSymbols(_, false, true))
      case other => SMTExprMap.mapExpr(other, replaceSymbols(_, false, false))
    }

  protected def findSignalsToInline(sys: TransitionSystem): Set[String] = {
    // count how often a symbol is used
    val useCount = Analysis.countUses(sys.signals.map(_.e))
    val onlyUsedOnce = sys.signals.filter(s => useCount(s.name) <= InlineUseMax).map(_.name).toSet
    // we also want to inline signals that are only aliases
    val leafSignals = if (InlineLeaves) sys.signals.filter(s => isLeafExpr(s.e)).map(_.name).toSet else Set[String]()
    // only regular node signals can be inlined
    val canBeInlined = sys.signals.filter(_.lbl == IsNode).map(_.name).toSet

    onlyUsedOnce.union(leafSignals).intersect(canBeInlined)
  }

  private def isLeafExpr(e: SMTExpr): Boolean = e match {
    case _: BVSymbol      => true
    case _: BVLiteral     => true
    case _: ArraySymbol   => true
    case _: ArrayConstant => true
    case _ => false
  }
}
