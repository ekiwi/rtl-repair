// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

sealed trait SMTCommand
case class Comment(msg: String) extends SMTCommand
case class SetLogic(logic: String) extends SMTCommand
case class DefineFunction(name: String, args: Seq[SMTFunctionArg], e: SMTExpr) extends SMTCommand
case class DeclareFunction(sym: SMTSymbol, args: Seq[SMTFunctionArg]) extends SMTCommand
case class DeclareUninterpretedSort(name: String) extends SMTCommand
case class DeclareUninterpretedSymbol(name: String, tpe: String) extends SMTCommand
