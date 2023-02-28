package synth

import maltese.mc.{IsOutput, TransitionSystem}
import maltese.smt.SolverContext

import scala.collection.mutable
import scala.util.control.Breaks.{break, breakable}

object SolutionFilter {
  import synth.Synthesizer.applySynthAssignment

  /** Sort solutions in order to make results more deterministic
    * (across solvers, or in case the solver is not fully deterministic).
    */
  def sort(solutions: Seq[Solution]): Seq[Solution] = {
    val solutionsWithKey = solutions.map(s => toKey(s) -> s)
    solutionsWithKey.sortBy(_._1).map(_._2)
  }

  private def toKey(sol: Solution): String = {
    sol.assignments.map { case (name, value) => s"$name -> $value" }.mkString("|")
  }

  def run(
    ctx:       SolverContext,
    sys:       TransitionSystem,
    tb:        Testbench,
    config:    Config,
    solutions: Seq[Solution]
  ): Seq[Solution] = {
    // generate repaired system for each solutions
    val all = solutions.map(sol => Data(sol, applySynthAssignment(sys, sol.assignments)))

    // filter out solutions that generate exactly the same system
    val synFiltered = syntacticFilter(all)
    if (synFiltered.length < all.length && config.verbose) {
      println(s"Syntactic filter removed ${all.length - synFiltered.length}/${all.length}")
    }

    // filter out solutions that are combinatorially equivalent
    val combEquivFiltered = combEquivFilter(ctx, config.verbose, synFiltered)
    if (combEquivFiltered.length < synFiltered.length && config.verbose) {
      println(s"Syntactic filter removed ${synFiltered.length - combEquivFiltered.length}/${synFiltered.length}")
    }

    combEquivFiltered.map(_.solution)
  }

  private case class Data(solution: Solution, sys: TransitionSystem)

  /** Remove solutions that result in exactly the same system code. (same syntax!) */
  private def syntacticFilter(solutions: Seq[Data]): Seq[Data] = {
    val seen = mutable.HashSet[String]()
    solutions.filter { s =>
      val key = s.sys.serialize
      val isDuplicate = seen.contains(key)
      seen.add(key)
      !isDuplicate
    }
  }

  /** Remove duplicates that are combinatorially equivalent, i.e, all output and next functions are the same. */
  private def combEquivFilter(ctx: SolverContext, verbose: Boolean, solutions: Seq[Data]): Seq[Data] = {
    var unique = List[Data]()
    solutions.foreach { newSolution =>
      breakable {
        unique.foreach { oldSolution =>
          if (isCombEquiv(ctx, verbose, oldSolution, newSolution)) {
            break // we are done here, this is a duplicate
          }
        }
        // no duplicate
        unique = unique :+ newSolution
      }
    }
    // return all unique solutions
    unique
  }

  private def isCombEquiv(ctx: SolverContext, verbose: Boolean, a: Data, b: Data): Boolean = {
    // first we check to make sure that all states and outputs have the same name
    val outputs = a.sys.signals.filter(_.lbl == IsOutput).map(o => o.name -> o.e.tpe)
    val outputsB = b.sys.signals.filter(_.lbl == IsOutput).map(o => o.name -> o.e.tpe)
    if (outputs != outputsB) {
      if (verbose) println(s"Outputs do not match: $outputs vs $outputsB")
      return false
    }
    val states = a.sys.states.map(s => s.name -> s.sym.tpe)
    val statesB = b.sys.states.map(s => s.name -> s.sym.tpe)
    if (states != statesB) {
      if (verbose) println(s"States do not match: $states vs $statesB")
      return false
    }

    // check output equivalence

    false
  }

}
