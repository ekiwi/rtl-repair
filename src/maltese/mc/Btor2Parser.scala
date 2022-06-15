// Copyright 2020-2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import maltese.mc
import maltese.smt._

import scala.collection.mutable

object Btor2 {
  def load(file: os.Path): TransitionSystem = load(file, inlineSignals = false)
  def load(file: os.Path, inlineSignals: Boolean): TransitionSystem = {
    val defaultName = file.last.split('.').dropRight(1).mkString(".")
    Btor2Parser.read(os.read.lines(file), inlineSignals, defaultName)
  }
  def read(src: String, inlineSignals: Boolean = false, defaultName: String = "Unknown"): TransitionSystem = {
    val lines = src.split('\n')
    Btor2Parser.read(lines, inlineSignals, defaultName)
  }
}

private object Btor2Parser {
  val unary = Set("not", "inc", "dec", "neg", "redand", "redor", "redxor")
  val binary = Set(
    "iff",
    "implies",
    "sgt",
    "ugt",
    "sgte",
    "ugte",
    "slt",
    "ult",
    "slte",
    "ulte",
    "and",
    "nand",
    "nor",
    "or",
    "xnor",
    "xor",
    "rol",
    "ror",
    "sll",
    "sra",
    "srl",
    "add",
    "mul",
    "sdiv",
    "udiv",
    "smod",
    "srem",
    "urem",
    "sub",
    "saddo",
    "uaddo",
    "sdivo",
    "udivo",
    "smulo",
    "umulo",
    "ssubo",
    "usubo",
    "concat"
  )

  // splits line into code and comment (trimmed!)
  private def splitLine(line: String): (String, String) = {
    val parts = line.trim.split(';')
    val code = parts.head.trim
    val comment = parts.tail.mkString(";").trim
    (code, comment)
  }

  def read(lines: Iterable[String], inlineSignals: Boolean, defaultName: String): TransitionSystem = {
    val bvSorts = new mutable.HashMap[Int, Int]()
    val arraySorts = new mutable.HashMap[Int, (Int, Int)]()
    val states = new mutable.HashMap[Int, State]()
    val inputs = new mutable.ArrayBuffer[BVSymbol]()
    val signals = new mutable.LinkedHashMap[Int, Signal]()
    val comments = new mutable.ArrayBuffer[(String, String)]()
    var header = ""
    val namespace = Namespace()

    // unique name generator
    def isUnique(name:         String): Boolean = !namespace.contains(name)
    def nameFromPrefix(prefix: String): String =
      namespace.newName(Iterator.from(0).map(i => s"_${prefix}_$i").filter(isUnique).next())

    // while not part of the btor2 spec, yosys annotates the system's name
    var name: Option[String] = None

    def parseSort(id: Int, parts: Array[String]): Unit = {
      lazy val i3 = Integer.parseInt(parts(3))
      lazy val i4 = Integer.parseInt(parts(4))
      if (parts(2) == "bitvec") {
        bvSorts(id) = i3
      } else {
        assert(parts(2) == "array")
        arraySorts(id) = (bvSorts(i3), bvSorts(i4))
      }
    }

    /** yosys sometimes provides comments with human readable names for i/o/ and state signals * */
    def parseYosysComment(comment: String): Unit = {
      // yosys module name annotation
      if (comment.contains("Yosys") && comment.contains("for module ")) {
        val start = comment.indexOf("for module ")
        val mod_name = comment.substring(start + "for module ".length).dropRight(1)
        name = Some(mod_name)
        header = comment.trim
      }
    }

    def parseLine(line: String): Unit = {
      val (code, comment) = splitLine(line)
      if (comment.nonEmpty) { parseYosysComment(comment) }
      if (code.isEmpty) { return }

      val parts = code.split(" ")
      val id = Integer.parseInt(parts.head)

      // nodes besides output that feature nid
      def expr(offset: Int): SMTExpr = {
        assert(parts.length > 3 + offset, s"parts(${3 + offset}) does not exist! ${parts.mkString(", ")}")
        val nid = Integer.parseInt(parts(3 + offset))
        val absNid = math.abs(nid)
        assert(signals.contains(absNid), s"Unknown node #$absNid")
        val sig = signals(absNid)
        val e = if (inlineSignals) { sig.e }
        else { sig.toSymbol }
        if (nid < 0) { BVNot(e.asInstanceOf[BVExpr]) }
        else { e }
      }
      def bvExpr(offset:    Int) = expr(offset).asInstanceOf[BVExpr]
      def arrayExpr(offset: Int) = expr(offset).asInstanceOf[ArrayExpr]

      lazy val sortId = Integer.parseInt(parts(2))

      def width: Int = {
        assert(bvSorts.contains(sortId), s"Not a bit vector sort: $line")
        bvSorts(sortId)
      }

      def indexWidth: Int = {
        assert(arraySorts.contains(sortId), s"Not a array sort: $line")
        arraySorts(sortId)._1
      }

      def dataWidth: Int = {
        assert(arraySorts.contains(sortId), s"Not a array sort: $line")
        arraySorts(sortId)._2
      }

      def checkSort(e: SMTExpr): Option[SMTExpr] = e match {
        case b: BVExpr =>
          assert(b.width == width, s"Expected $width-bit value, got ${b.width}-bit value! $line")
          Some(b)
        case a: ArrayExpr =>
          assert(a.indexWidth == indexWidth, s"Expected $indexWidth-bit index, got ${a.indexWidth}-bit index! $line")
          assert(a.dataWidth == dataWidth, s"Expected $dataWidth-bit data, got ${a.dataWidth}-bit data! $line")
          Some(a)
      }

      def getLabelName(prefix: String): String =
        if (parts.length > 3) { namespace.newName(parts(3)) }
        else if (comment.nonEmpty) {
          // firrtl will put the output name into a comment, sometimes followed by a file info marked by @
          namespace.newName(comment.split('@').head.trim)
        } else { nameFromPrefix(prefix) }

      def toSymbolOrExpr(name: String, e: SMTExpr): SMTExpr = if (inlineSignals) e else SMTSymbol.fromExpr(name, e)

      def isArray: Boolean = arraySorts.contains(sortId)

      val cmd = parts(1)
      var name:  Option[String] = None
      var label: SignalLabel = IsNode
      val new_expr = cmd match {
        case "sort" => parseSort(id, parts); None
        case "input" =>
          name = Some(getLabelName("input"))
          val input = BVSymbol(name.get, width)
          inputs.append(input)
          Some(input)
        case lbl @ ("output" | "bad" | "constraint" | "fair") =>
          name = Some(getLabelName(lbl))
          label = SignalLabel.stringToLabel(lbl)
          Some(expr(-1))
        case "state" =>
          name = Some(getLabelName("state"))
          val sym = if (isArray) ArraySymbol(name.get, indexWidth, dataWidth) else BVSymbol(name.get, width)
          states.put(id, State(sym, None, None))
          Some(sym)
        case "next" =>
          val stateId = Integer.parseInt(parts(3))
          val state = states(stateId)
          name = Some(namespace.newName(state.sym.name + ".next"))
          label = IsNext
          val nextExpr = expr(1)
          states.put(stateId, state.copy(next = Some(toSymbolOrExpr(name.get, nextExpr))))
          Some(nextExpr)
        case "init" =>
          val stateId = Integer.parseInt(parts(3))
          val state = states(stateId)
          name = Some(namespace.newName(state.sym.name + ".init"))
          label = IsInit
          val initExpr = expr(1)
          states.put(stateId, state.copy(init = Some(toSymbolOrExpr(name.get, initExpr))))
          Some(initExpr)
        case format @ ("const" | "constd" | "consth" | "zero" | "one") =>
          val value = if (format == "zero") { BigInt(0) }
          else if (format == "one") { BigInt(1) }
          else { parseConst(format, parts(3)) }
          checkSort(BVLiteral(value, width))
        case "ones" =>
          checkSort(BVLiteral((BigInt(1) << width) - 1, width))
        case ext @ ("uext" | "sext") =>
          val by = Integer.parseInt(parts(4))
          checkSort(BVExtend(bvExpr(0), by, signed = ext.startsWith("s")))
        case "slice" =>
          val msb = Integer.parseInt(parts(4))
          val lsb = Integer.parseInt(parts(5))
          checkSort(BVSlice(bvExpr(0), msb, lsb))
        case op if unary.contains(op) =>
          checkSort(parseUnary(op, bvExpr(0)))
        case "eq" =>
          checkSort(SMTEqual(expr(0), expr(1)))
        case "neq" =>
          checkSort(BVNot(SMTEqual(expr(0), expr(1))))
        case "concat" =>
          checkSort(BVConcat(bvExpr(0), bvExpr(1)))
        case op if binary.contains(op) =>
          checkSort(parseBinary(op, bvExpr(0), bvExpr(1)))
        case "read" =>
          checkSort(ArrayRead(arrayExpr(0), bvExpr(1)))
        case "write" =>
          checkSort(ArrayStore(arrayExpr(0), bvExpr(1), bvExpr(2)))
        case "ite" =>
          checkSort(SMTIte(bvExpr(0), expr(1), expr(2)))
        case other =>
          throw new RuntimeException(s"Unknown command: $other")

      }
      new_expr match {
        case Some(expr) =>
          val n = name.getOrElse(namespace.newName("s" + id))
          if(comment.nonEmpty) {
            comments.append(n -> comment.trim)
          }
          signals.put(id, mc.Signal(n, expr, label))
        case _ =>
      }
    }

    lines.foreach { ll => parseLine(ll.trim) }


    // we want to ignore state and input signals
    val isInputOrState = (inputs.map(_.name) ++ states.values.map(_.sym.name)).toSet

    // if we are inlining, we are ignoring all node signals
    val keep = if (inlineSignals) { s: Signal =>
      s.lbl != IsNode && s.lbl != IsNext && s.lbl != IsInit && !isInputOrState(s.name)
    } else { s: Signal => !isInputOrState(s.name) }
    val finalSignals = signals.values.filter(keep).toList

    val sysName = name.getOrElse(defaultName)
    TransitionSystem(sysName, inputs = inputs.toList, states = states.values.toList, signals = finalSignals,
      comments = comments.toMap, header = header)
  }

  private def parseConst(format: String, str: String): BigInt = format match {
    case "const"  => BigInt(str, 2)
    case "constd" => BigInt(str)
    case "consth" => BigInt(str, 16)
  }

  private def parseUnary(op: String, expr: BVExpr): BVExpr = op match {
    case "not"    => BVNot(expr)
    case "inc"    => BVOp(Op.Add, expr, BVLiteral(1, expr.width))
    case "dec"    => BVOp(Op.Sub, expr, BVLiteral(1, expr.width))
    case "neg"    => BVNegate(expr)
    case "redand" => Reduce.and(expr)
    case "redor"  => Reduce.or(expr)
    case "redxor" => Reduce.xor(expr)
    case other    => throw new RuntimeException(s"Unknown unary op $other")
  }

  private def parseBinary(op: String, a: BVExpr, b: BVExpr): BVExpr = op match {
    case "ugt"         => BVComparison(Compare.Greater, a, b, signed = false)
    case "ugte"        => BVComparison(Compare.GreaterEqual, a, b, signed = false)
    case "ult"         => BVNot(BVComparison(Compare.GreaterEqual, a, b, signed = false))
    case "ulte"        => BVNot(BVComparison(Compare.Greater, a, b, signed = false))
    case "sgt"         => BVComparison(Compare.Greater, a, b, signed = true)
    case "sgte"        => BVComparison(Compare.GreaterEqual, a, b, signed = true)
    case "slt"         => BVNot(BVComparison(Compare.GreaterEqual, a, b, signed = true))
    case "slte"        => BVNot(BVComparison(Compare.Greater, a, b, signed = true))
    case "and"         => BVAnd(a, b)
    case "nand"        => BVNot(BVAnd(a, b))
    case "nor"         => BVNot(BVOr(a, b))
    case "or"          => BVOr(a, b)
    case "xnor"        => BVNot(BVOp(Op.Xor, a, b))
    case "xor"         => BVOp(Op.Xor, a, b)
    case "rol" | "ror" => throw new NotImplementedError("TODO: implement rotates on bv<N>")
    case "sll"         => BVOp(Op.ShiftLeft, a, b)
    case "sra"         => BVOp(Op.ArithmeticShiftRight, a, b)
    case "srl"         => BVOp(Op.ShiftRight, a, b)
    case "add"         => BVOp(Op.Add, a, b)
    case "mul"         => BVOp(Op.Mul, a, b)
    case "sdiv"        => BVOp(Op.SignedDiv, a, b)
    case "udiv"        => BVOp(Op.UnsignedDiv, a, b)
    case "smod"        => BVOp(Op.SignedMod, a, b)
    case "srem"        => BVOp(Op.SignedRem, a, b)
    case "urem"        => BVOp(Op.UnsignedRem, a, b)
    case "sub"         => BVOp(Op.Sub, a, b)
    case "implies"     => implies(a, b)
    case "iff"         => iff(a, b)
    case other         => throw new RuntimeException(s"Unknown binary op $other")
  }

  private def implies(a: BVExpr, b: BVExpr): BVExpr = {
    assert(a.width == 1 && b.width == 1, s"Both arguments need to be 1-bit!")
    BVOr(BVNot(a), b)
  }

  private def iff(a: BVExpr, b: BVExpr): BVExpr = {
    assert(a.width == 1 && b.width == 1, s"Both arguments need to be 1-bit!")
    BVEqual(a, b)
  }
}
