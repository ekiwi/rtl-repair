// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.passes
import maltese.mc
import maltese.smt
import maltese.smt.SMTExprMap

import scala.collection.mutable

/** Eliminates quantifiers by expanding them, thus there might be a significant blowup of the formula.
  * We assume that all quantified variables are used in the same signal that defines the original quantifier.
  *
  * @param expandMax maximum number of expansions we are allowed to make
  */
class ExpandQuantifiers(expandMax: Int = 2048) extends Pass {
  override def name = "ExpandQuantifiers"

  override def run(sys: mc.TransitionSystem): mc.TransitionSystem = {
    val signals = sys.signals.flatMap(expand)
    // if there are quantifiers, the expand function guarantees that the number of signals will increase
    if (signals.length > sys.signals.length) {
      sys.copy(signals = signals)
    } else { sys }
  }

  private def expand(signal: mc.Signal): Iterable[mc.Signal] = {
    val others = mutable.ArrayBuffer[mc.Signal]()
    val e = expand(signal.e, signal.name, Map(), others)
    if (others.isEmpty) { List(signal) }
    else {
      others :+ signal.copy(e = e)
    }
  }

  private def expand(
    expr:     smt.SMTExpr,
    prefix:   String,
    bindings: Map[String, smt.BVExpr],
    others:   mutable.ArrayBuffer[mc.Signal]
  ): smt.SMTExpr = expr match {
    case smt.BVForall(variable, e) =>
      val range = BigInt(1) << variable.width
      assert(
        range <= expandMax,
        s"$variable can take on $range different valued. This is more than the maximum $expandMax!"
      )
      val signals = (0 until range.toInt).map { ii =>
        val name = s"${prefix}_${variable.name}_$ii"
        val bb = bindings ++ Map(variable.name -> smt.BVLiteral(ii, variable.width))
        mc.Signal(name, expand(e, name, bb, others))
      }
      others ++= signals
      smt.BVAnd((0 until range.toInt).map(ii => smt.BVSymbol(s"${prefix}_${variable.name}_$ii", 1)).toList)
    case smt.BVSymbol(name, _) if bindings.contains(name) => bindings(name)
    case other                                            => SMTExprMap.mapExpr(other, expand(_, prefix, bindings, others))
  }
}
