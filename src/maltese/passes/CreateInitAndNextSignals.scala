package maltese.passes

import maltese.mc._
import maltese.smt._
import scala.collection.mutable

/** Ensures that the next and init expressions for every state are just symbols to ${state}.init / ${state}.next */
object CreateInitAndNextSignals extends Pass {
  override def name = "CreateInitAndNextSignals"

  override def run(sys: TransitionSystem): TransitionSystem = {
    val newSignals = mutable.ListBuffer[Signal]()
    val isTaken = TransitionSystem.getAllNames(sys).toSet
    val states = sys.states.map { state =>
      val init = state.init.map(ensureSymbol(state.name + ".init", _, newSignals, isTaken))
      val next = state.next.map(ensureSymbol(state.name + ".next", _, newSignals, isTaken))
      state.copy(init = init, next = next)
    }
    sys.copy(states = states, signals = sys.signals ++: newSignals.toList)
  }

  private def ensureSymbol(
    name:       String,
    e:          SMTExpr,
    newSignals: mutable.ListBuffer[Signal],
    isTaken:    String => Boolean
  ): SMTSymbol = e match {
    case s: SMTSymbol if s.name == name => s
    case other =>
      require(!isTaken(name), s"Cannot create new signal $name because the name is already in use!")
      newSignals.append(Signal(name, other))
      SMTSymbol.fromExpr(name, other)
  }
}
