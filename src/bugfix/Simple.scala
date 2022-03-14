package bugfix

import maltese.mc._
import maltese.smt._

// playing around with a simple repair
object Simple {
  def main(args: Array[String]): Unit = {
    // load the simples benchmark
    val sys = Btor2.load(os.pwd / "benchmarks" / "cirfix" / "decoder_3_to_8" / "decoder_3_to_8_wadden_buggy1.btor")


    // print benchmark
    // println(sys.serialize)

    // replace literals in system
    val (synSys, synSyms) = replaceConstants(sys)
    println(synSys.serialize)

    // load system and communicate to solver
    val encoding = new CompactEncoding(synSys)
    val ctx = Z3SMTLib.createContext(true)
    ctx.setLogic("ALL")
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // add soft constraints to change as few constants as possible
    synSyms.foreach { case (sym, value) =>
      ctx.softAssert(BVEqual(sym, BVLiteral(value, sym.width)))
    }

    // unroll and compare results
    val tb = Seq(
//      en=0 ABC=000 Y=11111111
//      en=1 ABC=000 Y=11111110
//      en=1 ABC=010 Y=11111011
//      en=1 ABC=100 Y=11101111
//      en=1 ABC=110 Y=10111111
//      en=0 ABC=110 Y=11111111
    )


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
