package bugfix

import maltese.mc._
import maltese.smt.{BVLiteral, _}

// playing around with a simple repair
object Simple {
  def main(args: Array[String]): Unit = {
    val circuits = Seq(
      "decoder_3_to_8.btor",
      // expected change for buggy1 (bug -> fix):
      // 4'b1000 -> 4'b1010
      // 8'b0111_1111 -> 8'b1111_1111
      "decoder_3_to_8_wadden_buggy1.btor",
      // expected change for buggy2 (bug -> fix):
      // 8 constants should change (missing leading 1)
      // However, there are some missing test cases, so that we do not actually need
      // to change all the constants to pass the test bench.
      // Missing cases (for ABC, with en=1): 001, 011, 101, 111
      // TODO: how does CirFix deal with the fact that these are never covered by the TB?
      "decoder_3_to_8_wadden_buggy2.btor",
    )

    // define a testbench
    //val tbSymbols = Seq("en", "A", "B", "C", "Y0", "Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7")
    val tbSymbols = Seq("en", "A", "B", "C", "Y7", "Y6", "Y5", "Y4", "Y3", "Y2", "Y1", "Y0")
      .map(name => BVSymbol(name, 1))
    val tb = Seq(
      //      en=0 ABC=000 Y=11111111
      //      en=1 ABC=000 Y=11111110
      //      en=1 ABC=010 Y=11111011
      //      en=1 ABC=100 Y=11101111
      //      en=1 ABC=110 Y=10111111
      //      en=0 ABC=110 Y=11111111
      Seq(0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1),
      Seq(1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0),
      Seq(1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1),
      Seq(1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1),
      Seq(1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1),
      Seq(0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1),
    )

    circuits.foreach { name =>
      println(s"Trying to repair: $name")
      // note: the btor was crated with yosys using:
      // - read_verilog
      // - proc -noopt
      // - write_btor
      val sys = Btor2.load(os.pwd / "benchmarks" / "cirfix" / "decoder_3_to_8" / name)

      // try to synthesize a fix
      val fixedSys = fixConstants(sys, tbSymbols, tb)
      // print repaired system
      if(false) {
        fixedSys.foreach { fixed =>
          println("BEFORE:")
          println(sys.serialize)
          println("")
          println("AFTER:")
          println(fixed.serialize)
        }
      }
      println()
    }
  }


  // simple repair approach that tries to find a replacements for constants in the circuit
  private def fixConstants(sys: TransitionSystem, tbSymbols: Seq[BVSymbol], tb: Seq[Seq[Int]]): Option[TransitionSystem] = {
    // first inline constants which will have the effect of duplicating constants that are used more than once
    val sysInlineConst = inlineConstants(sys)

    // replace literals in system
    val (synSys, synSyms) = replaceConstants(sysInlineConst)
    // println(synSys.serialize)

    // load system and communicate to solver
    val encoding = new CompactEncoding(synSys)
    // select solver
    val solver = if(true) { Z3SMTLib } else { OptiMathSatSMTLib }
    val ctx = solver.createContext(debugOn = false) // set debug to true to see commands sent to SMT solver
    ctx.setLogic("ALL")
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // add soft constraints to change as few constants as possible
    synSyms.foreach { case (sym, value) =>
      ctx.softAssert(BVEqual(sym, BVLiteral(value, sym.width)))
    }

    // print out constants
    println(s"${sys.name} contains ${synSyms.length} constants.")
    println(synSyms.map(_._2).map(_.toLong.toBinaryString).mkString(", "))

    // unroll and compare results
    tb.zipWithIndex.foreach { case (values, ii) =>
      values.zip(tbSymbols).foreach { case (value, sym) =>
        val signal = encoding.getSignalAt(sym, ii)
        if(value == 1) { ctx.assert(signal) } else { ctx.assert(BVNot(signal)) }
      }
      encoding.unroll(ctx)
    }

    // try to synthesize constants
    ctx.check() match {
      case IsSat => println("Solution found:")
      case IsUnSat => throw new RuntimeException(s"No possible solution could be found")
      case IsUnknown => throw new RuntimeException(s"Unknown result from solver.")
    }

    val newConstants = synSyms.map(t => ctx.getValue(t._1).get)
    ctx.close()

    // print results
    val changedConstants = synSyms.zip(newConstants).flatMap { case ((sym, oldValue), newValue) =>
      if(oldValue != newValue) { Some((sym, oldValue, newValue)) } else { None }
    }
    if(changedConstants.isEmpty) {
      println("Nothing needs to change. The circuit was already working correctly!")
      None
    } else {
      changedConstants.foreach { case (sym, oldValue, newValue) =>
        println(s"${sym.name}: ${oldValue.toLong.toBinaryString} -> ${newValue.toLong.toBinaryString}")
      }
      // substitute constants
      val mapping = synSyms.zip(newConstants).map { case ((sym, _), newValue) => sym.name -> newValue }.toMap
      Some(subBackConstants(synSys, mapping))
    }
  }

  private def subBackConstants(sys: TransitionSystem, mapping: Map[String, BigInt]): TransitionSystem = {
    def onExpr(s: SMTExpr): SMTExpr = s match {
      case call @ BVFunctionCall(name, List(), width)  =>
        mapping.get(name) match {
          case Some(value) => BVLiteral(value, width)
          case None => call
        }
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(signals = signals)
  }

  private def replaceConstants(sys: TransitionSystem, prefix: String = "const_"): (TransitionSystem, Seq[(BVSymbol, BigInt)]) = {
    var counter = 0
    var consts: List[(BVSymbol, BigInt)] = List()
    def onExpr(s: SMTExpr): SMTExpr = s match {
      case BVLiteral(value, width) =>
        val sym = BVSymbol(prefix + counter, width)
        counter += 1
        consts =  (sym, value) +: consts
        BVFunctionCall(sym.name, List(), sym.width)
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = sys.signals.map(s => s.copy(e = onExpr(s.e)))
    (sys.copy(signals = signals), consts)
  }


  /** Inlines all nodes that are only a constant.
    * This can be very helpful for repairing constants, since we sometimes only want to fix one use of the constant
    * and not all of them.
    * */
  private def inlineConstants(sys: TransitionSystem): TransitionSystem = {
    val (const, nonConst) = sys.signals.partition { s => s.e match {
      case _ : BVLiteral => true
      case _ => false
    }}
    val lookup = const.map(s => s.name -> s.e).toMap
    def onExpr(e: SMTExpr): SMTExpr = e match {
      case sym : BVSymbol =>
        lookup.get(sym.name) match {
          case Some(value) => value
          case None => sym
        }
      case other => SMTExprMap.mapExpr(other, onExpr)
    }
    val signals = nonConst.map(s => s.copy(e = onExpr(s.e)))
    sys.copy(signals = signals)
  }

}
