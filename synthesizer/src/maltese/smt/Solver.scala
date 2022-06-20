// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

trait Solver {
  // basic properties
  def name:                String
  def supportsQuantifiers: Boolean

  /** Constant Arrays are not required by SMTLib: https://rise4fun.com/z3/tutorialcontent/guide */
  def supportsConstArrays:            Boolean
  def supportsUninterpretedFunctions: Boolean

  def createContext(debugOn: Boolean = false): SolverContext
}

trait SolverContext {
  def solver: Solver

  // basic API
  def setLogic(logic: String): Unit = {
    val quantifierFree = logic.startsWith("QF_")
    require(solver.supportsQuantifiers || quantifierFree, s"${solver.name} does not support quantifiers!")
    val ufs = logic.contains("UF")
    require(solver.supportsUninterpretedFunctions || !ufs, s"${solver.name} does not support uninterpreted functions!")
    doSetLogic(logic)
    pLogic = Some(logic)
  }
  def getLogic: Option[String] = pLogic
  def stackDepth: Int // returns the size of the push/pop stack
  def push():     Unit
  def pop():      Unit
  def assert(expr:     BVExpr): Unit
  def softAssert(expr: BVExpr, weight: Int = 1): Unit
  final def check(produceModel: Boolean): SolverResult = {
    require(pLogic.isDefined, "Use `setLogic` to select the logic.")
    pCheckCount += 1
    doCheck(produceModel)
  }
  def runCommand(cmd: SMTCommand): Unit
  def queryModel(e:   BVSymbol):   Option[BigInt]
  def getValue(e:     BVExpr):     Option[BigInt]
  def getValue(e:     ArrayExpr):  Seq[(Option[BigInt], BigInt)]

  /** releases all native resources */
  def close(): Unit

  // convenience API
  def check(): SolverResult = check(true)
  def check(expr: BVExpr): SolverResult = check(expr, produceModel = true)
  def check(expr: BVExpr, produceModel: Boolean): SolverResult = {
    push()
    assert(expr)
    val res = check(produceModel)
    pop()
    res
  }

  // statistics
  def checkCount: Int = pCheckCount
  private var pCheckCount = 0

  // internal functions that need to be implemented by the solver
  private var pLogic: Option[String] = None
  protected def doSetLogic(logic:     String):  Unit
  protected def doCheck(produceModel: Boolean): SolverResult
}

sealed trait SolverResult {
  def isSat:   Boolean = false
  def isUnSat: Boolean = false
}
case object IsSat extends SolverResult { override def isSat = true }
case object IsUnSat extends SolverResult { override def isUnSat = true }
case object IsUnknown extends SolverResult
