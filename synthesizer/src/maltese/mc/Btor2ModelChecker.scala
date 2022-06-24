// Copyright 2020 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import maltese.passes.ExpandQuantifiers

import java.io.PrintWriter
import scala.collection.mutable
import scala.sys.process._

class BtormcModelChecker extends Btor2ModelChecker {
  // TODO: check to make sure binary exists
  override val name:           String = "btormc"
  override val prefix:         String = "btormc"
  override val supportsOutput: Boolean = false
  override protected def makeArgs(kMax: Int, inputFile: Option[String], kMin: Int): Seq[String] = {
    val kMaxArg = if (kMin >= 0) Seq(s"--kmax $kMax") else Seq()
    val kMinArg = if (kMin >= 0) Seq(s"--kmin $kMin") else Seq()
    val prefix = Seq("btormc") ++ kMinArg ++ kMaxArg
    inputFile match {
      case None       => prefix
      case Some(file) => prefix ++ Seq(s"$file")
    }
  }
  override protected def isFail(ret: Int, res: Iterable[String]): Boolean = {
    assert(ret == 0, s"We expect btormc to always return 0, not $ret. Maybe there was an error:\n" + res.mkString("\n"))
    super.isFail(ret, res)
  }
}

class Cosa2ModelChecker extends Btor2ModelChecker {
  // TODO: check to make sure binary exists
  override val name:                       String = "cosa2"
  override val prefix:                     String = "btormc"
  override val supportsOutput:             Boolean = true
  override val supportsMultipleProperties: Boolean = false
  override protected def makeArgs(kMax: Int, inputFile: Option[String], kMin: Int): Seq[String] = {
    require(kMin == -1, "kmin is currently not supported")
    val base = Seq("cosa2", "--engine bmc")
    val prefix = if (kMax > 0) base ++ Seq(s"--bound $kMax") else base
    inputFile match {
      case None       => throw new RuntimeException("cosa2 only supports file based input. Please supply a filename!")
      case Some(file) => prefix ++ Seq(s"$file")
    }
  }
  private val WrongUsage = 3
  private val Unknown = 2
  private val Sat = 1
  private val Unsat = 0
  override protected def isFail(ret: Int, res: Iterable[String]): Boolean = {
    assert(ret != WrongUsage, "There was an error trying to call cosa2:\n" + res.mkString("\n"))
    val fail = super.isFail(ret, res)
    if (fail) { assert(ret == Sat) }
    else { assert(ret == Unknown) /* bmc only returns unknown because it cannot prove unsat */ }
    fail
  }
}

abstract class Btor2ModelChecker extends IsModelChecker {
  override val name: String
  override val fileExtension: String = ".btor2"
  protected def makeArgs(kMax: Int, inputFile: Option[String] = None, kMin: Int = -1): Seq[String]
  val supportsOutput: Boolean
  val supportsMultipleProperties: Boolean = true
  override def check(
    sys:      TransitionSystem,
    kMax:     Int = -1,
    fileName: Option[String] = None,
    kMin:     Int = -1
  ): ModelCheckResult = {
    val hasQuantifiers = TransitionSystem.hasQuantifier(sys)
    val quantifierFree = if (hasQuantifiers) new ExpandQuantifiers().run(sys) else sys
    val checkSys = quantifierFree
    // TODO: combine properties!
    //  if (supportsMultipleProperties) quantifierFree else TransitionSystem.combineProperties(quantifierFree)
    fileName match {
      case None       => throw new NotImplementedError("Currently only file based model checking is supported!")
      case Some(file) => checkWithFile(file, checkSys, kMax, kMin)
    }
  }

  /* called to check the results of the solver */
  protected def isFail(ret: Int, res: Iterable[String]): Boolean = res.nonEmpty && res.head.startsWith("sat")

  private def checkWithFile(fileName: String, sys: TransitionSystem, kMax: Int, kMin: Int): ModelCheckResult = {
    val btorWrite = new PrintWriter(fileName)
    val lines = Btor2Serializer.serialize(sys, skipOutput = !supportsOutput)
    lines.foreach { l => btorWrite.println(l) }
    btorWrite.close()

    // execute model checker
    val cmd = makeArgs(kMax, Some(fileName), kMin).mkString(" ")
    val stdout = mutable.ArrayBuffer[String]()
    val stderr = mutable.ArrayBuffer[String]()
    val ret = cmd ! ProcessLogger(stdout.append(_), stderr.append(_))
    if (stderr.nonEmpty) { println(s"ERROR: ${stderr.mkString("\n")}") }

    // write stdout to file for debugging
    val res = stdout
    val resultFileName = fileName + ".out"
    val stdoutWrite = new PrintWriter(resultFileName)
    res.foreach(l => stdoutWrite.println(l))
    stdoutWrite.close()

    //print(cmd)
    //println(s" -> $ret")

    // check if it starts with sat
    if (isFail(ret, res)) {
      val witness = Btor2WitnessParser.read(res, 1).head
      ModelCheckFail(convertWitness(sys, witness))
    } else {
      ModelCheckSuccess()
    }
  }

  private def convertWitness(sys: TransitionSystem, bw: Btor2Witness): Witness = {
    val badNames = sys.signals.filter(_.lbl == IsBad).map(_.name).toIndexedSeq
    val failed = bw.failed.map(badNames)
    Witness(failed, bw.regInit, bw.memInit, bw.inputs)
  }
}
