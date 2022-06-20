// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.smt

import scala.annotation.tailrec

object SMTLibResponseParser {
  def parseValue(v: String): Option[BigInt] = parseValue(SExprParser.parse(v))

  @tailrec
  private def parseValue(e: SExpr): Option[BigInt] = e match {
    case SExprNode(List(SExprNode(List(_, SExprLeaf(valueStr))))) => parseBVLiteral(valueStr)
    // example: (_ bv0 32)
    case SExprNode(List(SExprNode(List(_, SExprNode(List(SExprLeaf("_"), SExprLeaf(value), SExprLeaf(width)))))))
        if value.startsWith("bv") =>
      Some(BigInt(value.drop(2)))
    case SExprNode(List(one)) => parseValue(one)
    case _                    => throw new NotImplementedError(s"Unexpected response: $e")
  }

  type MemInit = Seq[(Option[BigInt], BigInt)]

  def parseMemValue(v: String): MemInit = {
    val tree = SExprParser.parse(v)
    tree match {
      case SExprNode(List(SExprNode(List(_, value)))) => parseMem(value, Map())
      case _                                          => throw new NotImplementedError(s"Unexpected response: $v")
    }
  }

  private def parseMem(value: SExpr, ctx: Map[String, MemInit]): MemInit = value match {
    case SExprNode(List(SExprNode(List(SExprLeaf("as"), SExprLeaf("const"), tpe)), SExprLeaf(valueStr))) =>
      // initialize complete memory to value
      List((None, parseBVLiteral(valueStr).get))
    case SExprNode(List(SExprLeaf("store"), array, SExprLeaf(indexStr), SExprLeaf(valueStr))) =>
      val (index, value) = (parseBVLiteral(indexStr), parseBVLiteral(valueStr))
      parseMem(array, ctx) :+ (Some(index.get), value.get)
    case SExprNode(List(SExprLeaf("let"), SExprNode(List(SExprNode(List(SExprLeaf(variable), array0)))), array1)) =>
      val newCtx = ctx ++ Seq(variable -> parseMem(array0, ctx))
      parseMem(array1, newCtx)
    case SExprLeaf(variable) =>
      assert(ctx.contains(variable), s"Undefined variable: $variable. " + ctx.keys.mkString(", "))
      ctx(variable)
    case SExprNode(
          List(
            SExprLeaf("lambda"),
            SExprNode(List(SExprNode(List(SExprLeaf(v0), indexTpe)))),
            SExprNode(List(SExprLeaf("="), SExprLeaf(v1), SExprLeaf(indexStr)))
          )
        ) if v0 == v1 =>
      // example: (lambda ((x!1 (_ BitVec 5))) (= x!1 #b00000))
      List((None, BigInt(0)), (Some(parseBVLiteral(indexStr).get), BigInt(1)))
    case other => throw new NotImplementedError(s"TODO implement parsing of SMT solver response: $other")
  }

  private def parseBVLiteral(valueStr: String): Option[BigInt] = {
    if (valueStr == "true") { Some(BigInt(1)) }
    else if (valueStr == "false") { Some(BigInt(0)) }
    else if (valueStr == "???") { None }
    else if (valueStr.startsWith("#b")) { Some(BigInt(valueStr.drop(2), 2)) }
    else if (valueStr.startsWith("#x")) { Some(BigInt(valueStr.drop(2), 16)) }
    else {
      throw new NotImplementedError(s"Unsupported number format: $valueStr")
    }
  }
}

sealed trait SExpr {
  def isEmpty: Boolean
}
case class SExprNode(children: List[SExpr]) extends SExpr {
  override def toString = children.mkString("(", " ", ")")
  override def isEmpty: Boolean = children.isEmpty || children.forall(_.isEmpty)
}
case class SExprLeaf(value: String) extends SExpr {
  override def toString = value
  override def isEmpty: Boolean = value.trim.isEmpty
}

/** simple S-Expression parser to make sense of SMTLib solver output */
object SExprParser {
  def parse(line: String): SExpr = {
    val tokens = tokenize(line)

    if (tokens.isEmpty) {
      SExprLeaf("")
    } else if (tokens.head == "(") {
      parseSExpr(tokens.tail)._1
    } else {
      assert(tokens.tail.isEmpty, s"multiple tokens, but not starting with a `(`:\n${tokens.mkString(" ")}")
      SExprLeaf(tokens.head)
    }
  }

  def hasBalancedParentheses(line: String): Boolean = {
    var count = 0
    var inEscape = false
    line.foreach {
      case '(' if !inEscape => count += 1
      case ')' if !inEscape => count -= 1
      case '|'              => inEscape = !inEscape
      case _                => // ignore
    }
    count == 0
  }

  // tokenization with | as escape character
  private def tokenize(line: String): List[String] = {
    var tokens: List[String] = List()
    var inEscape = false
    var tmp = ""
    def finish(): Unit = {
      if (tmp.nonEmpty) {
        tokens = tokens :+ tmp
        tmp = ""
      }
    }
    line.foreach {
      case '('                                   => finish(); tokens = tokens :+ "("
      case ')'                                   => finish(); tokens = tokens :+ ")"
      case '|' if inEscape                       => tmp += '|'; finish(); inEscape = false
      case '|' if !inEscape                      => finish(); inEscape = true; tmp = "|"
      case ' ' | '\t' | '\r' | '\n' if !inEscape => finish()
      case other                                 => tmp += other
    }
    finish()
    tokens
  }

  private def parseSExpr(tokens: List[String]): (SExpr, List[String]) = {
    var t = tokens
    var elements = List[SExpr]()
    while (t.nonEmpty) {
      t.head match {
        case "(" =>
          val (child, nt) = parseSExpr(t.tail)
          t = nt
          elements = elements :+ child
        case ")" =>
          return (SExprNode(elements), t.tail)
        case other =>
          elements = elements :+ SExprLeaf(other)
          t = t.tail
      }
    }
    (SExprNode(elements), List())
  }
}
