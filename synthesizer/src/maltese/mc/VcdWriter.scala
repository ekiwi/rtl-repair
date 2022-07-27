// Copyright 2022 The Regents of the University of California
// released under BSD 3-Clause License
// based on VCD code from treadle released under Apache 2.0 license
// see: https://github.com/chipsalliance/treadle/tree/master/src/main/scala/treadle/vcd
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.mc

import java.io.PrintWriter
import java.text.SimpleDateFormat
import java.util.{Date, TimeZone}

class VcdWriter(filename: os.Path) {
  import Vcd._
  private val writer = os.write.channel(filename)
  private var closed = false
  private def print(str: String): Unit = ???

  def writeHeader(moduleName: String, timeScale: String = "1ns"): Unit = {
    print(DateDeclaration + "\n")
    print(getNowString() + "\n")
    print(End + "\n")
    print(VersionDeclaration + "\n")
    print(Version + "\n")
    print(End + "\n")
    print(s"$TimeScaleDeclaration $timeScale  $End\n")

  }

  def close(): Unit = {
    require(!closed)
    writer.close()
    closed = true
  }

  private def getNowString(): String = {
    val tz = TimeZone.getTimeZone("UTC")
    val df = new SimpleDateFormat("yyyy-MM-dd'T'HH:mmZ")
    df.setTimeZone(tz)
    val nowAsISO = df.format(new Date())
    nowAsISO
  }
}

object Vcd {
  val Version = "0.2"

  val DateDeclaration:           String = "$date"
  val VersionDeclaration:        String = "$version"
  val CommentDeclaration:        String = "$comment"
  val TimeScaleDeclaration:      String = "$timescale"
  val ScopeDeclaration:          String = "$scope"
  val VarDeclaration:            String = "$var"
  val UpScopeDeclaration:        String = "$upscope"
  val EndDefinitionsDeclaration: String = "$enddefinitions"
  val DumpVarsDeclaration:       String = "$dumpvars"
  val End:                       String = "$end"
}
