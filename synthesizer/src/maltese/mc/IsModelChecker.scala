// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

trait ModelCheckResult {
  def isFail: Boolean
  def isSuccess: Boolean = !isFail
}
case class ModelCheckSuccess() extends ModelCheckResult { override def isFail: Boolean = false }
case class ModelCheckFail(witness: Witness) extends ModelCheckResult { override def isFail: Boolean = true }

trait IsModelChecker {
  val name:          String
  val prefix:        String
  val fileExtension: String
  val supportsUF:          Boolean = false
  val supportsQuantifiers: Boolean = false
  def check(sys: TransitionSystem, kMax: Int = -1, fileName: Option[String] = None, kMin: Int = -1): ModelCheckResult
}

case class Witness(
  failed:  Seq[String],
  regInit: Map[Int, BigInt],
  memInit: Map[Int, Seq[(Option[BigInt], BigInt)]],
  inputs:  Seq[Map[Int, BigInt]])
