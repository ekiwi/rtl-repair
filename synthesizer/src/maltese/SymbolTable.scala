// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese

class SymbolTable private (nameToId: Seq[(String, Int)]) {}

object SymbolTable {
  def scan(sys: mc.TransitionSystem): SymbolTable = {
    new SymbolTable(Seq())
  }
}
