// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

sealed trait SMTCommand
sealed trait SMTFunctionCommand extends SMTCommand { def name: String }
case class Comment(msg: String) extends SMTCommand
case class SetLogic(logic: String) extends SMTCommand
case class DefineFunction(name: String, args: Seq[SMTSymbol], e: SMTExpr) extends SMTFunctionCommand
case class DeclareFunction(sym: SMTSymbol, args: Seq[SMTType]) extends SMTFunctionCommand {
  override def name: String = sym.name
}
case class DeclareUninterpretedSort(name: String) extends SMTCommand
