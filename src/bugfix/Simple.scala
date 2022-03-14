package bugfix

import maltese.mc._
import maltese.smt.{BVLiteral, _}

// playing around with a simple repair
object Simple {
  def main(args: Array[String]): Unit = {
    // load the simples benchmark
    val sys = Btor2.load(os.pwd / "benchmarks" / "cirfix" / "decoder_3_to_8" / "decoder_3_to_8_wadden_buggy1.btor")


    // print benchmark
    // println(sys.serialize)

    // replace literals in system
    val (synSys, synSyms) = replaceConstants(sys)
    // println(synSys.serialize)

    // load system and communicate to solver
    val encoding = new CompactEncoding(synSys)
    val ctx = Z3SMTLib.createContext(debugOn = false) // set debug to true to see commands sent to SMT solver
    ctx.setLogic("ALL")
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // add soft constraints to change as few constants as possible
    synSyms.foreach { case (sym, value) =>
      ctx.softAssert(BVEqual(sym, BVLiteral(value, sym.width)))
    }

    // unroll and compare results
    val tbSymbols = Seq("en", "A", "B", "C", "Y0", "Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7")
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
    synSyms.foreach { case (sym, oldValue) =>
      val newValue = ctx.getValue(sym).get
      if(oldValue != newValue) {
        println(s"${sym.name}: $oldValue -> $newValue")
      }
    }


    ctx.close()
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

}
