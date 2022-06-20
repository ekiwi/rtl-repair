package maltese.passes

import maltese.mc.TransitionSystem

trait Pass {
  def run(sys: TransitionSystem): TransitionSystem
  def name: String
}
