// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import scala.collection.mutable
import maltese.smt

import java.io.PrintWriter

/** Encodes a TransitionSystem in the format of the Uclid5 model checking system.
  *  https://github.com/uclid-org/uclid
  */
object Uclid5Serializer {
  def serialize(sys: TransitionSystem): Iterable[String] = {
    new Uclid5Serializer().run(sys)
  }
}

/** Doesn't actually call uclid, just generates the files. */
object Uclid5PseudoMC extends IsModelChecker {
  override val name = "Uclid5 Backend"
  override val prefix:        String = "uclid"
  override val fileExtension: String = ".ucl"

  override def check(sys: TransitionSystem, kMax: Int, fileName: Option[String], kMin: Int = -1): ModelCheckResult = {
    println("WARN: Uclid5 backend will only generate a uclid5 file, but not actually call uclid to check it!")
    fileName match {
      case None => throw new NotImplementedError("Currently only file based model checking is supported!")
      case Some(file) =>
        val writer = new PrintWriter(file)
        val lines = Uclid5Serializer.serialize(sys)
        lines.foreach { l => writer.println(l) }
        writer.close()
        println(file)
        ModelCheckSuccess()
    }
  }
}

class Uclid5Serializer private () {
  import Uclid5ExprSerializer._
  def run(sys: TransitionSystem): Iterable[String] = {
    val lines = mutable.ArrayBuffer[String]()

    lines += s"module ${escapeIdentifier(sys.name)} {"
    lines += "  // inputs"
    lines ++= sys.inputs.map(i => s"  input ${serializeWithType(i)};")
    lines += "  // state"
    lines ++= sys.states.map(s => s"  var ${serializeWithType(s.sym)};")
    lines += "  // signals"
    lines ++= sys.signals.map(s => s"  var ${serializeWithType(s.sym)}; // ${s.lbl}")
    lines += ""
    lines += "  init {"
    evaluateSignals(sys, lines)
    lines ++= sys.states.map { state =>
      state.init match {
        case Some(init) => s"    ${escapeIdentifier(state.name)} = ${serialize(init)};"
        case None       => s"    havoc ${escapeIdentifier(state.name)};"
      }
    }
    lines += "  }"
    lines += ""
    lines += "  next {"
    evaluateSignals(sys, lines)
    lines ++= sys.states.map { state =>
      state.next match {
        case Some(init) => s"    ${escapeIdentifier(state.name)}' = ${serialize(init)};"
        case None       => s"    havoc ${escapeIdentifier(state.name)}';"
      }
    }
    lines += "  }"
    lines += "}"
  }

  private def evaluateSignals(sys: TransitionSystem, lines: mutable.ArrayBuffer[String]): Unit = {
    lines ++= sys.signals.flatMap { s =>
      List(s"    ${escapeIdentifier(s.name)} = ${serialize(s.e)};") ++ (s.lbl match {
        case IsConstraint => List(s"    assume(${escapeIdentifier(s.name)});")
        case IsBad        => List(s"    assert(!${escapeIdentifier(s.name)});")
        case _            => List()
      })
    }
  }
}

private object Uclid5ExprSerializer {
  def serialize(e: smt.SMTExpr): String = e match {
    case b: smt.BVExpr    => serialize(b)
    case a: smt.ArrayExpr => serialize(a)
  }

  def serialize(t: smt.SMTType): String = t match {
    case smt.BVType(width)                    => serializeBitVectorType(width)
    case smt.ArrayType(indexWidth, dataWidth) => serializeArrayType(indexWidth, dataWidth)
  }

  def serializeWithType(sym: smt.SMTSymbol): String =
    s"${escapeIdentifier(sym.name)} : ${serialize(sym.tpe)}"

  private def serialize(e: smt.BVExpr): String = e match {
    case smt.BVLiteral(value, width) =>
      val mask = (BigInt(1) << width) - 1
      val twosComplement = if (value < 0) { ((~(-value)) & mask) + 1 }
      else value
      if (width == 1) {
        if (twosComplement == 1) "true" else "false"
      } else {
        s"${twosComplement}bv$width"
      }
    case smt.BVSymbol(name, _)                                => escapeIdentifier(name)
    case smt.BVExtend(e, 0, _)                                => serialize(e)
    case smt.BVExtend(smt.BVLiteral(value, width), by, false) => serialize(smt.BVLiteral(value, width + by))
    case smt.BVExtend(e, by, signed) =>
      val foo = if (signed) "bv_sign_extend" else "bv_zero_extend"
      s"$foo($by, (${asBitVector(e)}))"
    case smt.BVSlice(e, hi, lo) =>
      if (lo == 0 && hi == e.width - 1) { serialize(e) }
      else {
        val bits = s"${asBitVector(e)}[$hi:$lo]"
        // 1-bit extracts need to be turned into a boolean
        if (lo == hi) { toBool(bits) }
        else { bits }
      }
    case smt.BVNot(smt.BVEqual(a, b)) if a.width == 1 => s"(${serialize(a)}) != (${serialize(b)})"
    case smt.BVNot(smt.BVNot(e))                      => serialize(e)
    case smt.BVNot(e) =>
      if (e.width == 1) { s"!(${serialize(e)})" }
      else { s"~(${serialize(e)})" }
    case smt.BVNegate(e)                                         => s"-(${asBitVector(e)})"
    case smt.BVImplies(smt.BVLiteral(v, 1), b) if v == 1         => serialize(b)
    case smt.BVImplies(a, b)                                     => s"(${serialize(a)}) ==> (${serialize(b)})"
    case smt.BVEqual(a, b)                                       => s"(${serialize(a)}) == (${serialize(b)})"
    case smt.ArrayEqual(a, b)                                    => s"(${serialize(a)}) == (${serialize(b)})"
    case smt.BVComparison(smt.Compare.Greater, a, b, false)      => s"(${asBitVector(a)}) >_u (${asBitVector(b)})"
    case smt.BVComparison(smt.Compare.GreaterEqual, a, b, false) => s"(${asBitVector(a)}) >=_u (${asBitVector(b)})"
    case smt.BVComparison(smt.Compare.Greater, a, b, true)       => s"(${asBitVector(a)}) > (${asBitVector(b)})"
    case smt.BVComparison(smt.Compare.GreaterEqual, a, b, true)  => s"(${asBitVector(a)}) >= (${asBitVector(b)})"
    // boolean operations get a special treatment for 1-bit vectors aka bools
    case smt.BVAnd(a, b) if a.width == 1            => s"(${serialize(a)}) && (${serialize(b)})"
    case smt.BVOr(a, b) if a.width == 1             => s"(${serialize(a)}) || (${serialize(b)})"
    case smt.BVOp(smt.Op.Xor, a, b) if a.width == 1 => s"(${serialize(a)}) ^ (${serialize(b)})"
    case smt.BVOp(op, a, b) if a.width == 1         => toBool(s"(${asBitVector(a)}) ${serialize(op)} (${asBitVector(b)})")
    case smt.BVOp(op, a, b)                         => s"(${serialize(a)}) ${serialize(op)} (${serialize(b)})"
    case smt.BVConcat(a, b)                         => s"(${asBitVector(a)}) ++ (${asBitVector(b)})"
    case smt.ArrayRead(array, index)                => s"(${serialize(array)})[${asBitVector(index)}]"
    case smt.BVIte(cond, tru, fals)                 => s"if (${serialize(cond)}) then (${serialize(tru)}) else (${serialize(fals)})"
    case smt.BVFunctionCall(name, args, _)          => throw new NotImplementedError("function call")
    case smt.BVForall(variable, e) =>
      s"(forall (${escapeIdentifier(variable.name)} : ${serialize(variable.tpe)}) :: (${serialize(e)}))"
  }

  private def serialize(e: smt.ArrayExpr): String = e match {
    case smt.ArraySymbol(name, _, _)             => escapeIdentifier(name)
    case smt.ArrayStore(array, index, data)      => s"(${serialize(array)})[(${serialize(index)}) -> (${serialize(data)})]"
    case smt.ArrayIte(cond, tru, fals)           => s"if (${serialize(cond)}) then (${serialize(tru)}) else (${serialize(fals)})"
    case c @ smt.ArrayConstant(e, _)             => s"const(${serialize(e)}, ${serializeArrayType(c.indexWidth, c.dataWidth)});"
    case smt.ArrayFunctionCall(name, args, _, _) => throw new NotImplementedError("function call")
  }

  private def serializeArrayType(indexWidth: Int, dataWidth: Int): String =
    s"[${serializeBitVectorType(indexWidth)}]${serializeBitVectorType(dataWidth)}"
  private def serializeBitVectorType(width: Int): String =
    if (width == 1) { "boolean" }
    else { assert(width > 1); s"bv$width" }

  private def serialize(op: smt.Op.Value): String = op match {
    case smt.Op.Xor                  => "^"
    case smt.Op.ArithmeticShiftRight => throw new NotImplementedError("ashr")
    case smt.Op.ShiftRight           => throw new NotImplementedError("lshr")
    case smt.Op.ShiftLeft            => throw new NotImplementedError("lshl")
    case smt.Op.Add                  => "+"
    case smt.Op.Mul                  => "*"
    case smt.Op.Sub                  => "-"
    case smt.Op.SignedDiv            => throw new NotImplementedError("sdiv")
    case smt.Op.UnsignedDiv          => throw new NotImplementedError("udiv")
    case smt.Op.SignedMod            => throw new NotImplementedError("smod")
    case smt.Op.SignedRem            => "%"
    case smt.Op.UnsignedRem          => "%_u"
  }

  private def toBool(e: String): String = s"$e == 1bv1"

  private val bvZero = "0bv1"
  private val bvOne = "1bv1"
  private def asBitVector(e: smt.BVExpr): String =
    if (e.width > 1) { serialize(e) }
    else { s"if (${serialize(e)}) then ($bvOne) else ($bvZero)" }

  def escapeIdentifier(name: String): String = name // TODO
}
