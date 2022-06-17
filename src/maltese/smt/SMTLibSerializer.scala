// Copyright 2020 SiFive, Inc.
// Copyright 2020-2022 The Regents of the University of California
// released under BSD 3-Clause License and Apache 2.0
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

import scala.util.matching.Regex
import scala.collection.mutable

/** Converts STM Expressions to a SMTLib compatible string representation.
  *  See http://smtlib.cs.uiowa.edu/
  *  Assumes well typed expression, so it is advisable to run the TypeChecker
  *  before serializing!
  *  Automatically converts 1-bit vectors to bool.
  */
object SMTLibSerializer {
  def serialize(e: SMTExpr): String = e match {
    case b: BVExpr    => serialize(b)
    case a: ArrayExpr => serialize(a)
    case u: UTSymbol  => escapeIdentifier(u.name)
  }

  def serialize(t: SMTType): String = t match {
    case BVType(width)                    => serializeBitVectorType(width)
    case ArrayType(indexWidth, dataWidth) => serializeArrayType(indexWidth, dataWidth)
    case UninterpretedSort(name)          => escapeIdentifier(name)
  }

  private def serialize(e: BVExpr): String = e match {
    case BVLiteral(value, width) =>
      val mask = (BigInt(1) << width) - 1
      val twosComplement = if (value < 0) { ((~(-value)) & mask) + 1 }
      else value
      if (width == 1) {
        if (twosComplement == 1) "true" else "false"
      } else {
        s"(_ bv$twosComplement $width)"
      }
    case BVSymbol(name, _)                            => escapeIdentifier(name)
    case BVExtend(e, 0, _)                            => serialize(e)
    case BVExtend(BVLiteral(value, width), by, false) => serialize(BVLiteral(value, width + by))
    case BVExtend(e, by, signed) =>
      val foo = if (signed) "sign_extend" else "zero_extend"
      s"((_ $foo $by) ${asBitVector(e)})"
    case BVSlice(e, hi, lo) =>
      if (lo == 0 && hi == e.width - 1) { serialize(e) }
      else {
        val bits = s"((_ extract $hi $lo) ${asBitVector(e)})"
        // 1-bit extracts need to be turned into a boolean
        if (lo == hi) { toBool(bits) }
        else { bits }
      }
    case BVNot(BVEqual(a, b)) if a.width == 1 => s"(distinct ${serialize(a)} ${serialize(b)})"
    case BVNot(BVNot(e))                      => serialize(e)
    case BVNot(e) =>
      if (e.width == 1) { s"(not ${serialize(e)})" }
      else { s"(bvnot ${serialize(e)})" }
    case BVNegate(e) => s"(bvneg ${asBitVector(e)})"
    case r: BVReduceAnd => serialize(Expander.expand(r))
    case r: BVReduceOr  => serialize(Expander.expand(r))
    case r: BVReduceXor => serialize(Expander.expand(r))
    case BVImplies(BVLiteral(v, 1), b) if v == 1         => serialize(b)
    case BVImplies(a, b)                                 => s"(=> ${serialize(a)} ${serialize(b)})"
    case BVEqual(a, b)                                   => s"(= ${serialize(a)} ${serialize(b)})"
    case ArrayEqual(a, b)                                => s"(= ${serialize(a)} ${serialize(b)})"
    case BVComparison(Compare.Greater, a, b, false)      => s"(bvugt ${asBitVector(a)} ${asBitVector(b)})"
    case BVComparison(Compare.GreaterEqual, a, b, false) => s"(bvuge ${asBitVector(a)} ${asBitVector(b)})"
    case BVComparison(Compare.Greater, a, b, true)       => s"(bvsgt ${asBitVector(a)} ${asBitVector(b)})"
    case BVComparison(Compare.GreaterEqual, a, b, true)  => s"(bvsge ${asBitVector(a)} ${asBitVector(b)})"
    // boolean operations get a special treatment for 1-bit vectors aka bools
    case BVAnd(a, b) if a.width == 1        => serializeAnd(a, b)
    case BVOr(a, b) if a.width == 1         => s"(or ${serialize(a)} ${serialize(b)})"
    case BVOp(Op.Xor, a, b) if a.width == 1 => s"(xor ${serialize(a)} ${serialize(b)})"
    case BVOp(op, a, b) if a.width == 1     => toBool(s"(${serialize(op)} ${asBitVector(a)} ${asBitVector(b)})")
    case BVOp(op, a, b)                     => s"(${serialize(op)} ${serialize(a)} ${serialize(b)})"
    case BVConcat(a, b)                     => s"(concat ${asBitVector(a)} ${asBitVector(b)})"
    case ArrayRead(array, index)            => s"(select ${serialize(array)} ${asBitVector(index)})"
    case BVIte(cond, tru, fals)             => s"(ite ${serialize(cond)} ${serialize(tru)} ${serialize(fals)})"
    case BVFunctionCall(name, List(), _)    => escapeIdentifier(name)
    case BVFunctionCall(name, args, _)      => args.map(serialize).mkString(s"($name ", " ", ")")
    case BVForall(variable, e)              => s"(forall ((${variable.name} ${serialize(variable.tpe)})) ${serialize(e)})"
  }


  // takes care if serializing potentially long and chains without recursion
  private def serializeAnd(a: BVExpr, b: BVExpr): String = {
    require(a.width == 1 && b.width == 1)
    val todo = mutable.Stack[BVExpr](a, b)
    var out = "(and"
    while(todo.nonEmpty) {
      todo.pop() match {
        case BVAnd(a, b) => todo.push(a) ; todo.push(b)
        case other => out += " " + serialize(other)
      }
    }
    out + ")"
  }


  private def serializeVariadic(op: String, terms: List[BVExpr]): String = terms match {
    case Seq() | Seq(_) => throw new RuntimeException(s"expected at least two elements in variadic op $op")
    case Seq(a, b)      => s"($op ${serialize(a)} ${serialize(b)})"
    case head :: tail   => s"($op ${serialize(head)} ${serializeVariadic(op, tail)})"
  }

  def serialize(e: ArrayExpr): String = e match {
    case ArraySymbol(name, _, _)               => escapeIdentifier(name)
    case ArrayStore(array, index, data)        => s"(store ${serialize(array)} ${serialize(index)} ${serialize(data)})"
    case ArrayIte(cond, tru, fals)             => s"(ite ${serialize(cond)} ${serialize(tru)} ${serialize(fals)})"
    case c @ ArrayConstant(e, _)               => s"((as const ${serializeArrayType(c.indexWidth, c.dataWidth)}) ${serialize(e)})"
    case ArrayFunctionCall(name, List(), _, _) => escapeIdentifier(name)
    case ArrayFunctionCall(name, args, _, _)   => args.map(serialize).mkString(s"($name ", " ", ")")
  }

  def serialize(c: SMTCommand): String = c match {
    case Comment(msg)                   => msg.split("\n").map("; " + _).mkString("\n")
    case DeclareUninterpretedSort(name) => s"(declare-sort ${escapeIdentifier(name)} 0)"
    case DefineFunction(name, args, e) =>
      val aa = args.map(a => s"(${serialize(a)} ${serialize(a.tpe)})").mkString(" ")
      s"(define-fun ${escapeIdentifier(name)} ($aa) ${serialize(e.tpe)} ${serialize(e)})"
    case DeclareFunction(sym, tpes) =>
      val aa = tpes.map(serialize).mkString(" ")
      s"(declare-fun ${escapeIdentifier(sym.name)} ($aa) ${serialize(sym.tpe)})"
    case SetLogic(logic) => s"(set-logic $logic)"
  }

  private def serializeArrayType(indexWidth: Int, dataWidth: Int): String =
    s"(Array ${serializeBitVectorType(indexWidth)} ${serializeBitVectorType(dataWidth)})"
  private def serializeBitVectorType(width: Int): String =
    if (width == 1) { "Bool" }
    else { assert(width > 1); s"(_ BitVec $width)" }

  private def serialize(op: Op.Value): String = op match {
    case Op.And                  => "bvand"
    case Op.Or                   => "bvor"
    case Op.Xor                  => "bvxor"
    case Op.ArithmeticShiftRight => "bvashr"
    case Op.ShiftRight           => "bvlshr"
    case Op.ShiftLeft            => "bvshl"
    case Op.Add                  => "bvadd"
    case Op.Mul                  => "bvmul"
    case Op.Sub                  => "bvsub"
    case Op.SignedDiv            => "bvsdiv"
    case Op.UnsignedDiv          => "bvudiv"
    case Op.SignedMod            => "bvsmod"
    case Op.SignedRem            => "bvsrem"
    case Op.UnsignedRem          => "bvurem"
  }

  private def toBool(e: String): String = s"(= $e (_ bv1 1))"

  private val bvZero = "(_ bv0 1)"
  private val bvOne = "(_ bv1 1)"
  private def asBitVector(e: BVExpr): String =
    if (e.width > 1) { serialize(e) }
    else { s"(ite ${serialize(e)} $bvOne $bvZero)" }

  // See <simple_symbol> definition in the Concrete Syntax Appendix of the SMTLib Spec
  private val simple: Regex = raw"[a-zA-Z\+-/\*\=%\?!\.$$_~&\^<>@][a-zA-Z0-9\+-/\*\=%\?!\.$$_~&\^<>@]*".r
  def escapeIdentifier(name: String): String = name match {
    case simple() => name
    case _        => if (name.startsWith("|") && name.endsWith("|")) name else s"|$name|"
  }
  def unescapeIdentifier(escaped: String): String = {
    val name = if (escaped.startsWith("|")) {
      assert(escaped.endsWith("|"), s"improperly escaped identifier: $escaped")
      escaped.drop(1).dropRight(1)
    } else { escaped }
    assert(!name.contains('|'), s"improperly escaped identifier: $escaped")
    name
  }
}

/** Expands expressions that are not natively supported by SMTLib */
private object Expander {
  def expand(r: BVReduceAnd): BVExpr = {
    if (r.e.width == 1) { r.e }
    else {
      val allOnes = (BigInt(1) << r.e.width) - 1
      BVEqual(r.e, BVLiteral(allOnes, r.e.width))
    }
  }
  def expand(r: BVReduceOr): BVExpr = {
    if (r.e.width == 1) { r.e }
    else {
      BVNot(BVEqual(r.e, BVLiteral(0, r.e.width)))
    }
  }
  def expand(r: BVReduceXor): BVExpr = {
    if (r.e.width == 1) { r.e }
    else {
      val bits = (0 until r.e.width).map(ii => BVSlice(r.e, ii, ii))
      bits.reduce[BVExpr]((a, b) => BVOp(Op.Xor, a, b))
    }
  }
}
