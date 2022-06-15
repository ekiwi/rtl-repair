// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import maltese.smt._

import javax.management.RuntimeErrorException
import scala.collection.mutable

/** Parses Transitions Systems serialized by yosys's `write_smt2` command
  *
  * special functions:
  * - $MODULE_is        : initial state predicate
  * - $MODULE_n $SIGNAL : access function for port, register and wires
  * - $MODULE_a         : assertions
  * - $MODULE_u         : assumptions
  * - $MODULE_i         : ???
  * - $MODULE_h         : design hierarchy (should be "true" for non hierarchical designs)
  * - $MODULE_t         : transition relation from one state to another
  *
  * */
object YosysSMTLibParser {
  def load(file: os.Path): TransitionSystem = {
    val defaultName = file.last.split('.').dropRight(1).mkString(".")
    read(os.read.lines(file), defaultName)
  }
  def read(lines: Iterable[String], defaultName: String = ""): TransitionSystem = {
    new YosysSMTLibParser(lines).read()
  }
}

private class YosysSMTLibParser(lines: Iterable[String]) {

  private var sysOption: Option[TransitionSystem] = None
  def read(): TransitionSystem = sysOption match {
    case Some(sys) => sys
    case None =>
      val sys = parse()
      sysOption = Some(sys)
      sys
  }

  private val YosysDescriptorPrefix = "yosys-smt2-"
  private def parse(): TransitionSystem = {
    val desc = (new YosysExpressionParser(lines)).parse()
    // determine the name of our system
    val sysName = findModuleName(desc)
    sys = sys.copy(name = sysName)
    // find state variables by looking at the transition function
    val states = findStates(desc)
    // find signals like wires, registers, inputs etc.
    parseSignals(desc, states)


    ??? // TODO!
  }

  private val namespace = Namespace()

  // finds the name of the module that was serialized and performs checks to make sure only a single module is contained
  // as we do not support hierarchical circuits (use yosys's flatten command to work around)
  private def findModuleName(desc: YosysSystemDescription): String = {
    val ModuleDesc = YosysDescriptorPrefix + "module"
    val allModules = desc.comments.filter(_.startsWith(ModuleDesc)).map(_.drop(ModuleDesc.length).trim).toList.distinct
    assert(allModules.size == 1, s"Expected to find exactly one module, not: ${allModules.mkString(",")}. Use yosys's flatten command!")
    val name = allModules.head
    val hierarchyFunction = desc.functions(name + "_h").asInstanceOf[DefineFunction]
    assert(hierarchyFunction.e == True(), s"Expected hierarchy function to be true, not: ${hierarchyFunction.e}. Did you forget to flatten?")
    name
  }

  private def findStates(desc: YosysSystemDescription): List[(SMTSymbol, SMTSymbol)] = {
    assert(sys.name.nonEmpty)
    val TransitionFun = sys.name + "_t"
    val foo = desc.functions(TransitionFun).asInstanceOf[DefineFunction]
    // the transition function is a large conjunction of equalities
    val entries = destructConjunction(foo.e.asInstanceOf[BVExpr])
    val states = entries.map {
      case BVEqual(
      BVFunctionCall(nextName, List(UTSymbol("state", _)), w1),     // the next state in the current state
      BVFunctionCall(name, List(UTSymbol("next_state", _)), w2)) => // the state in the next state (confusing, I know..)
        assert(w1 == w2)
        BVSymbol(name, w1) -> BVSymbol(nextName, w1)
      case ArrayEqual(
      ArrayFunctionCall(nextName, List(UTSymbol("state", _)), iw1, dw1),
      ArrayFunctionCall(name, List(UTSymbol("next_state", _)), iw2, dw2)) =>
        assert(iw1 == iw2 && dw1 == dw2)
        ArraySymbol(name, iw1, dw1) -> ArraySymbol(nextName, iw1, dw1)
      case other => throw new RuntimeException(s"Unexpected entry in transition function: $other")
    }
    // add states to system, creating anonymous names for now
    states
  }

  private def destructConjunction(e: BVExpr): List[BVExpr] = e match {
    case BVAnd(a, b) => List(a,b).flatMap(destructConjunction)
    case other => List(other)
  }

  private def parseSignals(desc: YosysSystemDescription, states: List[(SMTSymbol, SMTSymbol)]): Unit = {
    assert(sys.name.nonEmpty)
    val NextFun = sys.name + "_n"
    val TmpFun = sys.name + "#"
    val declarations = mutable.HashMap[String, SMTSymbol]()
    desc.entries.foreach {
      case YosysEntry(DeclareFunction(sym, args), comments) =>
        // collect the declarations of unnamed signals
        if(sym.name.startsWith(TmpFun)) {
          // often the real name is in a comment behind the signal, like (declare-fun ....) ; \test
          val realName = comments.lastOption.flatMap { comment =>
            if(comment.startsWith("\\")) { Some(comment.drop(1)) } else { None }
          }.getOrElse(sym.name)
          declarations(sym.name) = sym.rename(realName)
        } else if(sym.name.startsWith(sys.name + "_is")) {
            // ignore empty $MODULE_is function (for now)
        } else {
          println(s"TODO: deal with DECLARATION $sym, $args, $comments")
        }
      case YosysEntry(DefineFunction(sym, args, e), comments) =>
        val ds = parseYosysDescriptors(comments)
        ds.map(_.tpe).sorted match {
          case List("output", "register") =>
            println()
          case _ =>
            println(s"TODO: deal with DEFINITION $sym, $args, $e $comments,\n$ds")
        }


      case YosysEntry(DeclareUninterpretedSort(_), _) => // ignored
      case other =>
        throw new RuntimeException(s"Unexpected yosys entry: $other")

    }

    println()
  }

  private var sys = TransitionSystem("", List(), List(), List())

  //  private def parseLineContent(line: LineContent): Unit = {
//    // println(s"${line.expr}  ;;  ${line.comment}".trim)
//    if (line.expr.isEmpty) {
//      if (line.comments.head.startsWith(YosysDescriptorPrefix)) {
//        val suffix = line.comments.head.drop(YosysDescriptorPrefix.length)
//        val tpe = suffix.split(' ').head.trim
//        val value = suffix.split(' ').drop(1).mkString(" ")
//        tpe match {
//          case "module" =>
//            assert(sys.name.isEmpty, s"we are being asked to overwrite the system name ${sys.name} with $value")
//            sys = sys.copy(name = value.trim)
//          case "input" | "output" | "register" =>
//            val dd = Descriptor(tpe, value)
//            assert(lastDescriptor.isEmpty, s"About to overwrite unused descriptor: $lastDescriptor with $dd")
//            lastDescriptor = Some(dd)
//          case "topmod" =>
//            assert(value.trim == sys.name, "Only a single module is supported!")
//          case other => throw new NotImplementedError(s"unknown yosys descriptor: $other")
//        }
//      } else {
//        // println(s"Unknown comment: ${line.comment}")
//      }
//    } else { // we have a non-empty expression
//      val expr = parser.parseCommand(line.expr)
//      expr match {
//        case DeclareUninterpretedSort(name) =>
//          assert(line.comments.isEmpty, line.comments.mkString(":"))
//        // ignore data type declaration
//        case DeclareFunction(sym, args) =>
//          assert(args.length == 1, "expect every function to take the state as argument")
//          popDescriptor() match {
//            case Some(desc) => desc.tpe match {
//              case "input" => sys = sys.copy(inputs = sys.inputs :+ sym.asInstanceOf[BVSymbol])
//              case other => throw new RuntimeException(s"Unexpected descriptor $desc for $expr")
//            }
//            case None => // ignore declarations without a descriptor
//          }
//        case DefineFunction(name, args, e) =>
//          assert(name.startsWith(sys.name), s"unexpected function name, does not start with ${sys.name}: $name")
//          assert(args.length == 1 || args.length == 2)
//          popDescriptor() match {
//            case Some(desc) => desc.tpe match {
//              case "input" =>
//                // weird: we would expect all inputs to be declarations and not definitions .... but yosys sometimes
//                //        creates phantome symbols before defining the actual input as that symbol...
//                val sym = yosysDescriptorValueToBVSymbol(desc)
//                assert(name == sys.name + "_n " + sym.name, "unexpected next function name!")
//                sys = sys.copy(inputs = sys.inputs :+ sym)
//              case "output" =>
//                val sym = yosysDescriptorValueToBVSymbol(desc)
//                assert(name == sys.name + "_n " + sym.name, "unexpected next function name!")
//                val sig = Signal(sym.name, e, IsOutput)
//                sys = sys.copy(signals = sys.signals :+ sig)
//              case other => throw new RuntimeException(s"Unexpected descriptor $desc for $expr")
//            }
//            case None => // without a descriptor, we just make a normal node
//              val node = Signal("n" + name.drop(sys.name.length), e, IsNode)
//              sys = sys.copy(signals = sys.signals :+ node)
//
//          }
//      }
//    }
//  }
//
//  private def yosysDescriptorValueToBVSymbol(desc: Descriptor): BVSymbol = {
//    val parts = desc.value.split("\\s+")
//    assert(parts.size == 2)
//    BVSymbol(parts.head, parts(1).toInt)
//  }

  private def parseYosysDescriptors(comments: List[String]): List[YosysDescriptor] = comments.flatMap { comment =>
    if(comment.startsWith(YosysDescriptorPrefix)) {
      val parts = comment.split("\\s+")
      parts.head.drop(YosysDescriptorPrefix.length) match {
        case "module" => None // ignore, handled elsewhere
        case tpe @ ("input" | "output" | "register") =>
          assert(parts.length == 3)
          Some(YosysDescriptor(BVSymbol(parts(1), parts(2).toInt), tpe))
        case tpe @ "clock" =>
          assert(parts.length == 3)
          val event = parts(2)
          assert(event == "posedge", event)
          Some(YosysDescriptor(BVSymbol(parts(1), 1), tpe))
      }
    } else { None }
  }
  private case class YosysDescriptor(sym: SMTSymbol, tpe: String)


}



private case class YosysEntry(cmd: SMTCommand, comments: List[String])
private case class YosysSystemDescription(entries: List[YosysEntry], version: String) {
  def comments: Iterable[String] = entries.flatMap(_.comments)
  val functions: Map[String, SMTCommand] = entries
    .collect{ case YosysEntry(cmd : SMTFunctionCommand, _) => cmd.name -> cmd }.toMap
}

/** extracts s-expressions and associated comments from the yosys generated SMTLib description */
private class YosysExpressionParser(lines: Iterable[String]) {
  private val YosysHeaderPrefix = "SMT-LIBv2 description generated by Yosys"

  def parse(): YosysSystemDescription = {
    val ees = lines.flatMap(parseLine)
    // extract version
    val header = ees.head.comments.head
    assert(header.startsWith(YosysHeaderPrefix), s"unexpected header comment: $header")
    val yosysVersion = header.drop(YosysHeaderPrefix.length).trim
    // remove first comment
    val entries = ees.head.copy(comments = ees.head.comments.drop(1)) +: ees.drop(1).toList
    YosysSystemDescription(entries, yosysVersion)
  }


  // parser state, make sure to only run parser once!
  private val parser = new SMTLibParser
  private var exprBuf = ""
  private var comments = List[String]()

  /** note that we actually combine multiple lines if they contain a single S-expr */
  private def parseLine(line: String): Option[YosysEntry] = {
    println(line)
    val parts = line.split(';')
    exprBuf = (exprBuf + " " + parts.head).trim
    val comment = parts.drop(1).mkString(";").trim
    if(comment.nonEmpty) {
      comments = comments :+ comment
    }
    if(exprBuf.nonEmpty && SExprParser.hasBalancedParentheses(exprBuf)) {
      val sExpr = SExprParser.parse(exprBuf)
      val cmd = parser.parseCommand(sExpr)
      val entry = YosysEntry(cmd, comments = comments)
      exprBuf = "" ; comments = List()
      Some(entry)
    } else {
      None
    }
  }
}

class SMTLibParser {
  def resetState(): Unit = {
    symbols.clear()
    symbols.push(mutable.HashMap())
    sorts.clear()
  }
  def parseCommand(line: String): SMTCommand = parseCommand(SExprParser.parse(line))
  def parseCommand(expr: SExpr): SMTCommand = {
    expr match {
      case SExprNode(List(SExprLeaf("declare-sort"), SExprLeaf(name), SExprLeaf("0"))) =>
        assert(!sorts.contains(name), s"redeclaring uninterpreted sort $name")
        sorts.add(name)
        DeclareUninterpretedSort(SMTLibSerializer.unescapeIdentifier(name))
      case SExprNode(List(SExprLeaf("declare-fun"), SExprLeaf(name), SExprNode(args), retTpe)) =>
        val sym = SMTSymbol.fromType(SMTLibSerializer.unescapeIdentifier(name), parseType(retTpe))
        val argTpes = args.map(parseType)
        assert(argTpes.forall(_.isInstanceOf[UninterpretedSort]), s"expected only unintepreted sort args! $argTpes")
        addSymbol(sym)
        DeclareFunction(sym, argTpes)
      case SExprNode(List(SExprLeaf("define-fun"), SExprLeaf(name), SExprNode(argExprs), retTpe, body)) =>
        val sym = SMTSymbol.fromType(SMTLibSerializer.unescapeIdentifier(name), parseType(retTpe))
        val args = argExprs.map(parseArg)
        // add a new local scope before parsing the body
        symbols.push(mutable.HashMap())
        args.map(addSymbol)
        val expr = parseExpr(body)
        symbols.pop()
        assert(sym.tpe == expr.tpe)
        addSymbol(sym)
        DefineFunction(sym.name, args, expr)
      case other => throw new RuntimeException(s"Unexpected S-Expr: $other")
    }
  }

  private def parseType(expr: SExpr): SMTType = expr match {
    case SExprLeaf("Bool") => BVType(1)
    case SExprLeaf(name) => UninterpretedSort(SMTLibSerializer.unescapeIdentifier(name))
    case SExprNode(List(SExprLeaf("_"), SExprLeaf("BitVec"), SExprLeaf(bitStr))) =>
      BVType(bitStr.toInt)
    case other => throw new NotImplementedError(s"TODO: parse SMT type $other")
  }

  private def parseArg(expr: SExpr): SMTSymbol = expr match {
    case SExprNode(List(SExprLeaf(name), tpe)) => SMTSymbol.fromType(name, parseType(tpe))
    case other => throw new RuntimeException(s"Unexpected function argument S-Expr: $other")
  }

  private def parseExpr(expr: SExpr): SMTExpr = expr match {
    case SExprLeaf(funNameUnEscaped) =>
      parseBuiltInSymbol(funNameUnEscaped) match {
        case Some(e) => e
        case None => // user defined symbol?
          val funName = SMTLibSerializer.unescapeIdentifier(funNameUnEscaped)
          lookupSymbol(funName).getOrElse(throw new RuntimeException(s"unknown symbol $funName"))
      }
    case SExprNode(List(one)) =>
      parseExpr(one)
    case SExprNode(SExprLeaf(funNameUnEscaped) :: tail) =>
      assert(tail.nonEmpty)
      val args = tail.map(parseExpr)
      parseBuiltInFoo(funNameUnEscaped, args) match {
        case Some(e) => e
        case None => // user function call?
          val funName = SMTLibSerializer.unescapeIdentifier(funNameUnEscaped)
          val funSym = lookupSymbol(funName)
            .getOrElse(throw new RuntimeException(s"unknown function $funName"))
          funSym match {
            case BVSymbol(name, width) => BVFunctionCall(name, args, width)
            case ArraySymbol(name, indexWidth, dataWidth) => ArrayFunctionCall(name, args, indexWidth, dataWidth)
          }
      }
    case SExprNode(List(SExprNode(List(SExprLeaf("_"), SExprLeaf("extract"), SExprLeaf(msb), SExprLeaf(lsb))), expr)) =>
      BVSlice(parseExpr(expr).asInstanceOf[BVExpr], hi = msb.toInt, lo = lsb.toInt)
    case other => throw new NotImplementedError(s"Unexpected SMT Expression S-Expr: $other")
  }

  private def parseBuiltInSymbol(name: String): Option[SMTExpr] = {
    if(name.startsWith("#b")) {
      val value = BigInt(name.drop(2), 2)
      val bits = name.drop(2).length
      Some(BVLiteral(value, bits))
    } else if(name == "true") {
      Some(BVLiteral(1, 1))
    } else if(name == "false") {
      Some(BVLiteral(0, 1))
    } else {
      None
    }
  }

  private def parseBuiltInFoo(name: String, args: List[SMTExpr]): Option[SMTExpr] = (name, args) match {
    // binary
    case ("=", List(a, b)) => Some(SMTEqual(a, b))
    case ("concat", List(a: BVExpr, b: BVExpr)) => Some(BVConcat(a, b))
    case ("bvadd", List(a: BVExpr, b: BVExpr)) => Some(BVOp(Op.Add, a, b))
    case ("and", args) => Some(BVAnd(args.map(_.asInstanceOf[BVExpr])))
    // ternary
    case ("ite", List(c: BVExpr, a, b)) => Some(SMTIte(c, a, b))
    case _ => None
  }

  // keeps track of symbols on a stack to account for local symbols (i.e. functions args)
  private var symbols = mutable.Stack[mutable.HashMap[String, SMTSymbol]]()
  private def lookupSymbol(name: String): Option[SMTSymbol] =
  // go from top to bottom of stack
    symbols.flatMap(_.get(name)).headOption
  private def lookupLocalSymbol(name: String): Option[SMTSymbol] = symbols.head.get(name)
  private def addSymbol(sym: SMTSymbol): Unit = {
    val existing = lookupLocalSymbol(sym.name)
    assert(existing.isEmpty, s"Symbol $sym already declared as ${existing.get}!")
    symbols.head(sym.name) = sym
  }
  // keeps track of uninterpreted sorts
  private var sorts = mutable.HashSet[String]()
  // start with reset state
  resetState()
}