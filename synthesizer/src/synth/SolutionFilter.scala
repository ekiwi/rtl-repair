// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package synth

import maltese.mc._
import maltese.smt._
import synth.Synthesizer.encodeSystem

import scala.collection.mutable
import scala.util.control.Breaks._

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
    val combEquivFiltered = combEquivFilter(config, ctx, synFiltered)
    if (combEquivFiltered.length < synFiltered.length && config.verbose) {
      println(s"Semantic filter removed ${synFiltered.length - combEquivFiltered.length}/${synFiltered.length}")
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
  private def combEquivFilter(config: Config, ctx: SolverContext, solutions: Seq[Data]): Seq[Data] = {
    var unique = List[Data]()
    solutions.foreach { newSolution =>
      breakable {
        unique.foreach { oldSolution =>
          if (EquivalenceChecker.isCombEquiv(config, ctx, oldSolution.sys, newSolution.sys)) {
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
}
