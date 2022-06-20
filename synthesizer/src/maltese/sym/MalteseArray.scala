package maltese.sym

import maltese.smt._

sealed trait MalteseArray {
  def hasConcreteData:    Boolean
  def hasConcreteIndices: Boolean
  def indexWidth:         Int
  def dataWidth:          Int
  def load(index: BVExpr, isUnSat: Option[BVExpr => Boolean] = None): BVExpr
  def symbolic: ArrayExpr
  def store(index: BVExpr, data: BVExpr): MalteseArray = {
    require(index.width == indexWidth)
    index match {
      case BVLiteral(value, _) =>
        new SparseConcreteArray(this, Map(value -> data))
      case symbolic =>
        new SymbolicArray(this, List(symbolic -> data))
    }
  }
  def toConcrete: Option[BigIntArray]
}

object MalteseArray {
  def apply(name: String, indexWidth: Int, dataWidth: Int): MalteseArray =
    new BaseArraySym(ArraySymbol(name, indexWidth, dataWidth))

  def apply(value: BigInt, indexWidth: Int, dataWidth: Int): MalteseArray =
    new BaseArrayConst(ArrayConstant(BVLiteral(value, dataWidth), indexWidth))
}

/** an array can either start as an ArrayConst or an ArraySymbol */
class BaseArrayConst(expr: ArrayConstant) extends MalteseArray {
  override def hasConcreteData = expr.e.isInstanceOf[BVLiteral]
  override def hasConcreteIndices = true
  override def indexWidth = expr.indexWidth
  override def dataWidth = expr.dataWidth
  override def load(index: BVExpr, isUnSat: Option[BVExpr => Boolean] = None): BVExpr = {
    require(index.width == indexWidth)
    expr.e
  }
  override def symbolic: ArrayExpr = expr
  override def toConcrete: Option[BigIntArray] = expr.e match {
    case BVLiteral(value, _) => Some(BigIntArray(value, indexWidth))
    case _                   => None
  }
}

/** an array can either start as an ArrayConst or an ArraySymbol */
class BaseArraySym(expr: ArraySymbol) extends MalteseArray {
  override def hasConcreteData = false
  override def hasConcreteIndices = true
  override def indexWidth = expr.indexWidth
  override def dataWidth = expr.dataWidth
  override def load(index: BVExpr, isUnSat: Option[BVExpr => Boolean] = None): BVExpr = ArrayRead(expr, index)
  override def symbolic:   ArrayExpr = expr
  override def toConcrete: Option[BigIntArray] = None
}

/** represents an array where all entries have a concrete address */
class SparseConcreteArray(base: MalteseArray, private val entries: Map[BigInt, BVExpr] = Map()) extends MalteseArray {

  override def hasConcreteData = base.hasConcreteData && entries.forall(_._2.isInstanceOf[BVLiteral])
  override def hasConcreteIndices = base.hasConcreteIndices
  override def indexWidth = base.indexWidth
  override def dataWidth = base.dataWidth

  override def load(index: BVExpr, isUnSat: Option[BVExpr => Boolean] = None): BVExpr = {
    require(index.width == indexWidth)
    index match {
      case BVLiteral(value, _) =>
        entries.getOrElse(value, base.load(index, isUnSat))
      case symIndex =>
        ArrayRead(symbolic, symIndex)
    }
  }

  override def store(index: BVExpr, data: BVExpr): MalteseArray = {
    require(index.width == indexWidth)
    index match {
      case BVLiteral(value, _) =>
        val allEntries = entries + (value -> data)
        new SparseConcreteArray(base, allEntries)
      case symbolic =>
        // copy all entries over to the new symbolic array to enable better optimizations
        val entryList: List[(BVExpr, BVExpr)] = entries.toList.map { case (i, v) =>
          (BVLiteral(i, indexWidth): BVExpr) -> v
        }
        new SymbolicArray(base, entryList :+ (symbolic -> data))
    }
  }

  override def symbolic: ArrayExpr = {
    entries.foldLeft(base.symbolic) { case (prev, (index, data)) =>
      ArrayStore(prev, BVLiteral(index, indexWidth), data)
    }
  }

  override def toConcrete: Option[BigIntArray] = {
    base.toConcrete.flatMap { array =>
      val concreteEntries = entries.collect { case (index, BVLiteral(value, _)) => index -> value }
      if (concreteEntries.size < entries.size) { None }
      else {
        Some(array ++ concreteEntries)
      }
    }
  }
}

/** represents an array with entries that have a symbolic address */
class SymbolicArray(base: MalteseArray, entries: List[(BVExpr, BVExpr)]) extends MalteseArray {
  override def hasConcreteData = base.hasConcreteData && entries.forall(_._2.isInstanceOf[BVLiteral])
  override def hasConcreteIndices = false
  override def indexWidth = base.indexWidth
  override def dataWidth = base.dataWidth

  import SymbolicArray._

  override def load(index: BVExpr, isUnSat: Option[BVExpr => Boolean] = None): BVExpr = {
    require(index.width == indexWidth)

    // chose address comparison functions depending on whether we use the solver or not
    val (may, must) = isUnSat match {
      case Some(isUnSat) => (mayAliasSolver(isUnSat, _, _), definitelyAliasSolver(isUnSat, _, _))
      case None          => (mayAlias(_, _), definitelyAlias(_, _))
    }

    // we iterate through the entries from most recent to first to see if the first entry that
    // may alias also definitely aliases
    val first_possible_alias = entries.reverseIterator.find(e => may(e._1, index))
    val res = first_possible_alias.filter(e => must(e._1, index))
    res match {
      case Some((_, value)) => value
      case None             =>
        // since there is no definitely result, let's collect all possible ones
        val candidates = entries.filter(e => may(e._1, index))
        val array = candidates.foldLeft(base.symbolic) { case (prev, (index, data)) =>
          ArrayStore(prev, index, data)
        }
        ArrayRead(array, index)
    }
  }

  override def symbolic: ArrayExpr = {
    entries.foldLeft(base.symbolic) { case (prev, (index, data)) =>
      ArrayStore(prev, index, data)
    }
  }

  override def toConcrete: Option[BigIntArray] = None
}

object SymbolicArray {
  private def mayAlias(a: BVExpr, b: BVExpr): Boolean = !definitelyNoAlias(a, b)
  // if a and b are exactly the same formula, than they do alias!
  private def definitelyAlias(a:   BVExpr, b: BVExpr): Boolean = a == b
  private def definitelyNoAlias(a: BVExpr, b: BVExpr): Boolean = (a, b) match {
    case (e1: BVLiteral, e2: BVLiteral) => e1.value != e2.value
    case _ => false
  }
  private def mayAliasSolver(isUnSat:        BVExpr => Boolean, a: BVExpr, b: BVExpr): Boolean = !isUnSat(BVEqual(a, b))
  private def definitelyAliasSolver(isUnSat: BVExpr => Boolean, a: BVExpr, b: BVExpr): Boolean = isUnSat(
    BVNot(BVEqual(a, b))
  )
  private def isTrue(e: BVExpr): Boolean = SMTSimplifier.simplify(e) match {
    case l: BVLiteral => l.value == 1
    case _ => false
  }
}

class BigIntArray private (default: BigInt, entries: Map[BigInt, BigInt], indexWidth: Int) {
  val maxEntries = BigInt(1) << indexWidth
  def +(that: (BigInt, BigInt)): BigIntArray = {
    requireInRange(that._1)
    new BigIntArray(default, entries + that, indexWidth)
  }
  def ++(that: Map[BigInt, BigInt]): BigIntArray = {
    new BigIntArray(default, entries ++ that, indexWidth)
  }
  def apply(index: BigInt): BigInt = {
    requireInRange(index)
    entries.getOrElse(index, default)
  }
  private def requireInRange(index: BigInt): Unit = {
    require(index >= 0, s"Index cannot be negative: $index")
    require(index < maxEntries, s"Index may not exceed ${maxEntries - 1}: $index")
  }

  def toIndexedSeq: IndexedSeq[BigInt] = {
    require(indexWidth <= 16, s"It is a bad idea to turn an array with $maxEntries entries into an IndexedSeq!")
    IndexedSeq.tabulate(maxEntries.toInt)(apply(_))
  }

  def toMap: (BigInt, Map[BigInt, BigInt]) = (default, entries)
}

object BigIntArray {
  def apply(default: BigInt, indexWidth: Int): BigIntArray = new BigIntArray(default, Map(), indexWidth)
}
