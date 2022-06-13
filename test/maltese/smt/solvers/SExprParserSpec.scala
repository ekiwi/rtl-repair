package maltese.smt.solvers

import maltese.smt._
import org.scalatest.flatspec.AnyFlatSpec

class SExprParserSpec extends AnyFlatSpec {
  behavior of "SExprParser"

  it should "deal with escaped identifiers and internal spaces correctly" in {
    val str = "(define-fun |decoder_3to8_n en| ((state |decoder_3to8_s|)) Bool (|decoder_3to8#0| state))"
    val expr = SExprParser.parse(str).asInstanceOf[SExprNode]
    // the space in the escaped identifier used to cause the number of children to be one too many (6)
    assert(expr.children.length == 5)
  }

}
