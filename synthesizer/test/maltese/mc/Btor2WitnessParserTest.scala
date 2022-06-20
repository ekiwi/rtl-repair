package maltese.mc

import org.scalatest.flatspec.AnyFlatSpec

class Btor2WitnessParserTest extends AnyFlatSpec {
  behavior.of("Btor2WitnessParser")

  val noStateWitness =
    """sat
      |b0
      |@0
      |0 0 reset@0
      |1 11111011 a@0
      |2 00000101 b@0
      |.
      |
      |""".stripMargin

  it should "parse a witness without state" in {
    val witnesses = Btor2WitnessParser.read(noStateWitness.split("\n"))

    assert(witnesses.length == 1, "there is only a single counter example")
    val w = witnesses.head
    assert(w.memInit.isEmpty, "there are no memories in the design")
    assert(w.regInit.isEmpty, "there are no states in the design")
    assert(w.inputs.head == Map(0 -> 0, 1 -> BigInt("11111011", 2), 2 -> BigInt("101", 2)))
    assert(w.inputs.length == 1, "there is only a single cycle")
  }

  val fsmWitness =
    """sat
      |b0
      |#0
      |0 00 state#0
      |@0
      |0 1 reset@0
      |1 1 in@0
      |@1
      |0 0 reset@1
      |1 1 in@1
      |.
      |
      |""".stripMargin

  it should "parse a witness with state" in {
    val witnesses = Btor2WitnessParser.read(fsmWitness.split("\n"))

    assert(witnesses.length == 1, "there is only a single counter example")
    val w = witnesses.head
    assert(w.memInit.isEmpty, "there are no memories in the design")
    assert(w.regInit(0) == 0, "state register is initialized to zero")
    assert(w.inputs(0) == Map(0 -> 1, 1 -> 1), "both reset (0) and in (1) are high in the first cycle")
    assert(w.inputs(1) == Map(0 -> 0, 1 -> 1), "reset is low in the second cycle")
  }

  val multipleWitnesses =
    """sat
      |b0
      |#0
      |0 0 state0#0
      |2 0 state2#0
      |3 0 state3#0
      |4 0 state4#0
      |6 1 state6#0
      |7 0 state7#0
      |8 0 state8#0
      |9 0 state9#0
      |10 0 state10#0
      |11 0 state11#0
      |12 1 state12#0
      |@0
      |0 0 clock@0
      |1 1 in@0
      |2 1 reset@0
      |#1
      |8 0 state8#1
      |9 0 state9#1
      |10 0 state10#1
      |11 0 state11#1
      |12 0 state12#1
      |@1
      |0 0 clock@1
      |1 0 in@1
      |2 0 reset@1
      |#2
      |8 0 state8#2
      |9 0 state9#2
      |10 0 state10#2
      |11 0 state11#2
      |12 0 state12#2
      |@2
      |0 0 clock@2
      |1 0 in@2
      |2 0 reset@2
      |.
      |sat
      |b1
      |#0
      |0 0 state0#0
      |2 0 state2#0
      |3 0 state3#0
      |4 0 state4#0
      |6 1 state6#0
      |7 0 state7#0
      |8 0 state8#0
      |9 0 state9#0
      |10 0 state10#0
      |11 0 state11#0
      |12 1 state12#0
      |@0
      |0 0 clock@0
      |1 1 in@0
      |2 1 reset@0
      |#1
      |8 0 state8#1
      |9 0 state9#1
      |10 0 state10#1
      |11 0 state11#1
      |12 0 state12#1
      |@1
      |0 0 clock@1
      |1 1 in@1
      |2 0 reset@1
      |#2
      |8 0 state8#2
      |9 0 state9#2
      |10 0 state10#2
      |11 0 state11#2
      |12 0 state12#2
      |@2
      |0 0 clock@2
      |1 0 in@2
      |2 0 reset@2
      |#3
      |8 0 state8#3
      |9 0 state9#3
      |10 0 state10#3
      |11 0 state11#3
      |12 0 state12#3
      |@3
      |0 0 clock@3
      |1 0 in@3
      |2 0 reset@3
      |.
      |sat
      |b2
      |#0
      |0 0 state0#0
      |2 0 state2#0
      |3 0 state3#0
      |4 0 state4#0
      |6 1 state6#0
      |7 0 state7#0
      |8 0 state8#0
      |9 0 state9#0
      |10 0 state10#0
      |11 0 state11#0
      |12 1 state12#0
      |@0
      |0 0 clock@0
      |1 1 in@0
      |2 1 reset@0
      |#1
      |8 0 state8#1
      |9 0 state9#1
      |10 0 state10#1
      |11 0 state11#1
      |12 0 state12#1
      |@1
      |0 0 clock@1
      |1 1 in@1
      |2 0 reset@1
      |#2
      |8 0 state8#2
      |9 0 state9#2
      |10 0 state10#2
      |11 0 state11#2
      |12 1 state12#2
      |@2
      |0 0 clock@2
      |1 1 in@2
      |2 0 reset@2
      |#3
      |8 0 state8#3
      |9 0 state9#3
      |10 0 state10#3
      |11 0 state11#3
      |12 0 state12#3
      |@3
      |0 0 clock@3
      |1 0 in@3
      |2 0 reset@3
      |#4
      |8 0 state8#4
      |9 0 state9#4
      |10 0 state10#4
      |11 0 state11#4
      |12 0 state12#4
      |@4
      |0 0 clock@4
      |1 0 in@4
      |2 0 reset@4
      |.
      |
      |""".stripMargin

  it should "parse multiple witnesses" ignore { // TODO: add support for non-det registers
    val witnesses = Btor2WitnessParser.read(multipleWitnesses.split("\n"))

    assert(witnesses.length == 1, "there is only a single counter example")
  }
}
