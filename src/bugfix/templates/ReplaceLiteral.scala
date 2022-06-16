// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package bugfix.templates
import maltese.mc._
import maltese.smt._

case class ReplaceLiteralTemplateApplication(synSymbols: Seq[(BVSymbol, BigInt)]) extends TemplateApplication {
  override def consts: Seq[BVSymbol] = synSymbols.map(_._1)
  // add soft constraints to change as few constants as possible
  override def softConstraints: Seq[BVExpr] = synSymbols.map { case (sym, value) =>
    BVEqual(sym, BVLiteral(value, sym.width))
  }
  override def performRepair(sys: TransitionSystem, results: Map[String, BigInt]): RepairResult =
    ReplaceLiteral.repair(sys, synSymbols, results)
}

/** Allows the solver to replace any literal in the circuit. Tries to minimize the number of literals that are changed. */
object ReplaceLiteral extends RepairTemplate {
  override def apply(sys: TransitionSystem, namespace: Namespace): (TransitionSystem, TemplateApplication) = {
    // first inline constants which will have the effect of duplicating constants that are used more than once
    val sysInlineConst = inlineConstants(sys)

    // replace literals in system
    val (synSys, synSyms) = replaceConstants(sysInlineConst, namespace)

    // print out constants
    if(false) {
      println(s"${sys.name} contains ${synSyms.length} constants.")
      println(synSyms.map(_._2).map(_.toLong.toBinaryString).mkString(", "))
    }

    (synSys, ReplaceLiteralTemplateApplication(synSyms))
  }

  def repair(sys: TransitionSystem, synSymbols: Seq[(BVSymbol, BigInt)], results: Map[String, BigInt]): RepairResult = {
    val changedConstants = synSymbols.flatMap { case (sym, oldValue) =>
      val newValue = results(sym.name)
      if(oldValue != newValue) { Some((sym, oldValue, newValue)) } else { None }
    }
    val mapping = synSymbols.map { case (sym, _) => sym.name -> results(sym.name) }.toMap
    val repairedSys = subBackConstants(sys, mapping)
    RepairResult(repairedSys, changed = changedConstants.nonEmpty)
  }


  def subBackConstants(sys: TransitionSystem, mapping: Map[String, BigInt]): TransitionSystem = {
    def onExpr(s: SMTExpr): SMTExpr = s match {
      case BVSymbol(name, width) if mapping.contains(name)  =>
        BVLiteral(mapping(name), width)
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(signals = signals)
  }

  def replaceConstants(sys: TransitionSystem, namespace: Namespace, prefix: String = "const"): (TransitionSystem, Seq[(BVSymbol, BigInt)]) = {
    namespace.reserve(prefix)
    var consts: List[(BVSymbol, BigInt)] = List()
    def onExpr(s: SMTExpr): SMTExpr = s match {
      case BVLiteral(value, width) =>
        val sym = BVSymbol(namespace.newName(prefix), width)
        consts =  (sym, value) +: consts
        sym
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    (sys.copy(signals = signals), consts)
  }


  /** Inlines all nodes that are only a constant.
    * This can be very helpful for repairing constants, since we sometimes only want to fix one use of the constant
    * and not all of them.
    * */
  def inlineConstants(sys: TransitionSystem): TransitionSystem = {
    val (const, nonConst) = sys.signals.partition { s => s.e match {
      case _ : BVLiteral => true
      case _ => false
    }}
    val lookup = const.map(s => s.name -> s.e).toMap
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym : BVSymbol =>
        lookup.get(sym.name) match {
          case Some(value) => value
          case None => sym
        }
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = nonConst.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(signals = signals)
  }
}
