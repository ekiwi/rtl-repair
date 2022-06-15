// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

import maltese.mc.{SignalLabel, TransitionSystem}

import scala.collection.mutable

class Namespace private (names: mutable.HashSet[String]) {
  names ++= Namespace.Reserved

  def newName(prefix: String): String = {
    val p = Namespace.fixCharacters(prefix)
    val candidates = Iterator(p) ++ Iterator.from(0).map(i => p + "_" + i)
    val name = candidates.find(!names.contains(_)).get
    names.add(name)
    name
  }
  def newName: String = newName(Namespace.TempNamePrefix)
  def contains(name: String): Boolean = names.contains(name)
  /** ensures that [[name]] will never be used */
  def reserve(name: String): Unit = names.add(name)
}

object Namespace {
  def apply(): Namespace = new Namespace(mutable.HashSet())
  def apply(sys: TransitionSystem): Namespace = {
    new Namespace(
      mutable.HashSet() ++
        sys.inputs.map(_.name) ++ sys.states.map(_.sym.name) ++ sys.signals.map(_.name)
    )
  }

  // try to replace/remove characters to get a sensible name
  def fixCharacters(name: String): String = if (name.isEmpty) { Namespace.TempNamePrefix }
  else {
    val start = if (!isAllowedStart(name.head)) { "_" + name }
    else { name }
    start.filter(isAllowed)
  }

  private val isAllowedStart = (('a' to 'z') ++ ('A' to 'Z') :+ '_').toSet
  private val OtherCharacters = Seq('_', '!', '#', '$', '%', '^', '&', '*', '-', '+', '.', ',')
  private val isAllowed = (('a' to 'z') ++ ('A' to 'Z') ++ ('0' to '9') ++ OtherCharacters).toSet

  private val TempNamePrefix = "_GEN"
  private val Keywords = List(
    "zext",
    "uext",
    "sext",
    "not",
    "neg",
    "eq",
    "ugt",
    "sgt",
    "ugeq",
    "sgeq",
    "concat",
    "eq",
    "ite",
    "select",
    "and",
    "or",
    "xor",
    "logical_shift_left",
    "arithmetic_shift_right",
    "logical_shift_right",
    "add",
    "mul",
    "sdiv",
    "udiv",
    "smod",
    "srem",
    "urem",
    "sub"
  ) ++ SignalLabel.labelStrings
  private val Reserved = Keywords :+ TempNamePrefix
}
