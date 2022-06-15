package bugfix

import maltese.mc._
import maltese.smt.{BVLiteral, _}

// playing around with a simple repair
object Simple {
  def repair(name: String, sys: TransitionSystem, tb: Testbench): Option[TransitionSystem] = {

    println(s"Trying to repair: $name")

    // try to synthesize a fix
    val fixedSys = fixConstants(sys, tb)

    fixedSys
  }


  // simple repair approach that tries to find a replacements for constants in the circuit
  private def fixConstants(sys: TransitionSystem, tb: Testbench, seed: Long = 0): Option[TransitionSystem] = {
    val rand = new scala.util.Random(seed)

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
    // define synthesis constants
    synSyms.foreach { case (sym, _) => ctx.runCommand(DeclareFunction(sym, Seq())) }
    encoding.defineHeader(ctx)
    encoding.init(ctx)

    // add soft constraints to change as few constants as possible
    synSyms.foreach { case (sym, value) =>
      ctx.softAssert(BVEqual(sym, BVLiteral(value, sym.width)))
    }

    // print out constants
    println(s"${sys.name} contains ${synSyms.length} constants.")
    println(synSyms.map(_._2).map(_.toLong.toBinaryString).mkString(", "))

    // get some meta data for testbench application
    val signalWidth = (
      sys.inputs.map(i => i.name -> i.width) ++
        sys.signals.filter(_.lbl == IsOutput).map(s => s.name -> s.e.asInstanceOf[BVExpr].width)
      ).toMap
    val tbSymbols = tb.signals.map(name => BVSymbol(name, signalWidth(name)))
    val isInput = sys.inputs.map(_.name).toSet

    // unroll and compare results
    tb.values.zipWithIndex.foreach { case (values, ii) =>
      values.zip(tbSymbols).foreach { case (value, sym) =>
        val signal = encoding.getSignalAt(sym, ii)
        value match {
          case None if isInput(sym.name) => // assign random value if input is X
            ctx.assert(BVEqual(signal, BVLiteral(BigInt(sym.width, rand), sym.width)))
          case Some(num) =>
            ctx.assert(BVEqual(signal, BVLiteral(num, sym.width)))
          case None => // ignore
        }
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
      case BVSymbol(name, width) if mapping.contains(name)  =>
        BVLiteral(mapping(name), width)
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
        sym
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
