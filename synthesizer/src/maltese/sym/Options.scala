// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.sym

import com.github.javabdd.{BDDFactory, JFactory}
import maltese.smt.{Solver, Z3SMTLib}

case class Options(
  // MultiSE 3.2: without coalescing we get an algorithm that behaves essentially like conventional DSE
  DoNotCoalesce: Boolean,
  // This will slow down symbolic execution significantly, only enable for debugging
  //CrosscheckSmtAndConcrete : Boolean = false,
  // Do not use the SMT formula cache (this enforces a solver call for every isValid or isUnSat query)
  //DisableSmtCache: Boolean = false,
  // Encode memory reads as ITEs (in ValueSummary form) instead of using Array theory (Store/Select)
  //EncodeMemoryReadsAsValueSummary: Boolean = false,
  // call solver to check if memory index could be out of bounds while enable is high
  //MemoryCheckForOutOfBoundsWriteWithSolver: Boolean = true,
  // use heuristics to simplify [[ValueSummary]]s on the fly (no solver is invoked)
  //SimplifySymbolicValueSummariesWithHeuristics: Boolean = true,
  // make use of cached isUnSat/isValid results when converting smt expressions to BDDs
  //QuerySmtCacheInSmtToBdd: Boolean = true,
  // converts boolean ops in the SMT formula to BDD and only assigns literals in other theories to BDD variables
  // (has been observed to reduce the number of entries from 40 -> 28 in one instance)
  ConvertBooleanOpsInSmtToBdd: Boolean,
  // tries to discover relationship between atomic predicates and use them to simplify BDDs
  //MinePredicateTheoremsInSmtToBdd: Boolean = false,
  // runs a isUnSat query on every guard in the ValueSummary resulting from the ITE, unsat entries are discarded
  CheckITEConditionWithSmtSolver: Boolean,
  // Converts boolean SMT expressions into BDDs and imports them into the guard.
  // This way the value summary will always have max. two entries.
  ImportBooleanExpressionsIntoGuard: Boolean,
  // SMT solver to use
  solver: Solver,
  // BDD implementation
  makeBdds: () => BDDFactory)

object Options {
  val Default: Options = Options(
    DoNotCoalesce = false,
    ConvertBooleanOpsInSmtToBdd = true,
    CheckITEConditionWithSmtSolver = false,
    ImportBooleanExpressionsIntoGuard = true,
    solver = Z3SMTLib,
    makeBdds = () => JFactory.init(100, 100)
  )
}
