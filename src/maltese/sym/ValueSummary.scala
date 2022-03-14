// Copyright 2020-2021 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@cs.berkeley.edu>

package maltese.sym

import maltese.smt._
import com.github.javabdd.BDD

sealed trait ValueSummary {
  def size: Int
  def isSymbolic: Boolean = !isConcrete
  def isConcrete: Boolean
}

object BVValueSummary {
  def apply(expr: BVExpr)(implicit ctx: SymbolicContext): BVValueSummary =
    new BVValueSummary(ctx, List(BVEntry(ctx.tru, expr)))
  def apply(value: BigInt, width: Int)(implicit ctx: SymbolicContext): BVValueSummary =
    apply(BVLiteral(value, width))
  def apply(value: Boolean)(implicit ctx: SymbolicContext): BVValueSummary =
    apply(if (value) 1 else 0, 1)

  def binary(a: BVValueSummary, b: BVValueSummary, op: (BVExpr, BVExpr) => BVExpr): BVValueSummary = {
    assert(a.ctx.eq(b.ctx))

    val pairs = makePairs(a, b)
    // TODO: should be coalesce only for ITE operations or also for boolean ops?
    val rawEntries = pairs.map { case (guard, a, b) => BVEntry(guard, simplify(op(a, b))) }
    val newEntries = if (a.ctx.opts.DoNotCoalesce) { rawEntries }
    else { coalesce(rawEntries) }
    importIntoGuard(new BVValueSummary(a.ctx, newEntries))
  }

  def makePairs(a: BVValueSummary, b: BVValueSummary): List[(BDD, BVExpr, BVExpr)] = {
    // TODO: we could probably make this faster by using BDDs as keys to a hash map
    //       this could accelerate the case where both a and b have matching guards
    //       which seems likely since case splits across the circuit should be similar
    a.entries.flatMap(makePairs(_, b.entries))
  }

  private def makePairs(a: BVEntry, b: List[BVEntry]): List[(BDD, BVExpr, BVExpr)] = {
    b.flatMap { case BVEntry(guard, value) =>
      // if the guards are exactly the same, we know that there is only a single pair, since all guards are
      // mutually exclusive
      if (guard.equals(a.guard)) { return List((a.guard, a.value, value)) }
      else {
        val conj = a.guard.and(guard)
        if (conj.isZero) { None }
        else { Some((conj, a.value, value)) }
      }
    }
  }

  def unary(a: BVValueSummary, op: BVExpr => BVExpr): BVValueSummary = {
    // all we need to do is to apply the operation to all entries + call simplify
    val newEntries = a.entries.map(e => e.copy(value = simplify(op(e.value))))
    importIntoGuard(new BVValueSummary(a.ctx, newEntries))
  }

  def ite(cond: BVValueSummary, tru: => BVValueSummary, fals: => BVValueSummary): BVValueSummary = {
    // if the condition is concrete, we only need to evaluate one side of the mux
    if (cond.isTrue) { assert(cond.ctx.eq(tru.ctx)); tru }
    else if (cond.isFalse) { assert(cond.ctx.eq(fals.ctx)); fals }
    else {
      val ctx = cond.ctx
      assert(ctx.eq(tru.ctx) && ctx.eq(fals.ctx))
      // TODO: integrate SMT solver for better filtering
      val isFalse: BDD => Boolean =
        if (ctx.opts.CheckITEConditionWithSmtSolver) { b => b.isZero || ctx.isUnSat(b) }
        else { b => b.isZero }

      // find all conditions under which the true/false branch will be taken
      val truCond = cond.entries.map(e => ctx.smtToBdd(e.value).and(e.guard)).filterNot(isFalse)
      val falsCond = cond.entries.map(e => ctx.smtToBdd(e.value).not().and(e.guard)).filterNot(isFalse)

      def combine(conds: List[BDD], entries: List[BVEntry]): List[BVEntry] =
        conds.flatMap(c =>
          entries.flatMap { e =>
            val combinedGuard = c.and(e.guard)
            if (isFalse(combinedGuard)) { None }
            else { Some(e.copy(guard = combinedGuard)) }
          }
        )

      val rawEntries = combine(truCond, tru.entries) ++ combine(falsCond, fals.entries)
      val newEntries = if (ctx.opts.DoNotCoalesce) { rawEntries }
      else { coalesce(rawEntries) }
      importIntoGuard(new BVValueSummary(ctx, newEntries))
    }
  }

  def read(array: ArrayValueSummary, index: BVValueSummary): BVValueSummary = {
    val pairs = ArrayValueSummary.makePairs(array, index.entries.map(e => e.guard -> e.value))
    // TODO: should be coalesce only for ITE operations or also for boolean ops?
    val rawEntries = pairs.map { case (guard, a, b) => BVEntry(guard, a.load(b, None)) }
    val newEntries = if (index.ctx.opts.DoNotCoalesce) { rawEntries }
    else { coalesce(rawEntries) }
    importIntoGuard(new BVValueSummary(index.ctx, newEntries))
  }

  private def coalesce(entries: List[BVEntry]): List[BVEntry] = {
    val (duplicate, others) = entries.groupBy(_.value).partition(_._2.size > 1)
    if (duplicate.isEmpty) {
      entries
    } else {
      (duplicate.map { case (_, entries) =>
        val combinedGuard = entries.map(_.guard).reduce((a, b) => a.or(b))
        entries.head.copy(guard = combinedGuard)
      } ++ others.map(_._2.head)).toList
    }
  }

  // TODO: we could get better performance by only simplifying one new expression
  private def simplify(expr: BVExpr): BVExpr = SMTSimplifier.simplify(expr).asInstanceOf[BVExpr]

  case class BVEntry(guard: BDD, value: BVExpr) {
    def width = value.width
  }

  private[maltese] def getEntries(vs: BVValueSummary): List[BVEntry] = vs.entries

  private def importIntoGuard(v: BVValueSummary): BVValueSummary =
    if (v.width != 1 || !v.ctx.opts.ImportBooleanExpressionsIntoGuard) {
      v
    } else {
      new BVValueSummary(v.ctx, importIntoGuard(v.ctx, v.entries))
    }

  private def importIntoGuard(ctx: SymbolicContext, entries: List[BVEntry]): List[BVEntry] = {
    val tru = entries.map(e => e.guard.and(ctx.smtToBdd(e.value))).reduce((a, b) => a.or(b))
    // putting the false entry first gives us a nicer print out when converting to SMT and serializing in `toString`
    val newEntries = List(BVEntry(tru.not(), False()), BVEntry(tru, True())).filterNot(_.guard.isZero)
    assert(newEntries.nonEmpty)
    newEntries
  }

  def toSMT(v: BVValueSummary): BVExpr = {
    if (v.entries.size == 1) {
      v.entries.head.value
    } else if (v.width == 1) { // for 1-bit values, we just build a boolean formula
      val ctx = v.ctx
      val tru = v.entries.map(e => e.guard.and(ctx.smtToBdd(e.value))).reduce((a, b) => a.or(b))
      ctx.bddToSmt(tru)
    } else {
      v.entries.drop(1).foldLeft(v.entries.head.value) { (a: BVExpr, b: BVEntry) =>
        val cond = v.ctx.bddToSmt(b.guard)
        val args = cond match {
          case BVNot(n_cond) => List(n_cond, a, b.value)
          case _             => List(cond, b.value, a)
        }
        BVIte(args(0), args(1), args(2))
      }
    }
  }
}

private object ArrayValueSummary {
  def apply(expr: ArrayExpr)(implicit ctx: SymbolicContext): ArrayValueSummary = {
    val array = expr match {
      case const: ArrayConstant => new BaseArrayConst(const)
      case sym:   ArraySymbol   => new BaseArraySym(sym)
      case other => throw new RuntimeException(s"Cannot create an array value from: $other")
    }
    new ArrayValueSummary(ctx, List(ArrayEntry(ctx.tru, array)))
  }

  def apply(value: BVValueSummary, indexWidth: Int)(implicit ctx: SymbolicContext): ArrayValueSummary = {
    val entries = BVValueSummary.getEntries(value).map { e =>
      ArrayEntry(e.guard, new BaseArrayConst(ArrayConstant(e.value, indexWidth)))
    }
    new ArrayValueSummary(ctx, entries)
  }

  case class ArrayEntry(guard: BDD, value: MalteseArray) {
    def indexWidth = value.indexWidth
    def dataWidth = value.dataWidth
  }

  def store(array: ArrayValueSummary, index: BVValueSummary, data: BVValueSummary): ArrayValueSummary = {
    val ctx = array.ctx
    // generate all feasible triplets of array, index and data
    val pairs = BVValueSummary.makePairs(index, data)
    val triplets = makeTriplets(array, pairs)
    val rawEntries = triplets.map { case (guard, a, b, c) => ArrayEntry(guard, a.store(b, c)) }
    val newEntries = if (ctx.opts.DoNotCoalesce) { rawEntries }
    else { coalesce(rawEntries) }
    new ArrayValueSummary(ctx, newEntries)
  }

  private def makeTriplets(
    array: ArrayValueSummary,
    pairs: List[(BDD, BVExpr, BVExpr)]
  ): List[(BDD, MalteseArray, BVExpr, BVExpr)] =
    array.entries.flatMap(makeTriplets(_, pairs))

  private def makeTriplets(
    array: ArrayEntry,
    pairs: List[(BDD, BVExpr, BVExpr)]
  ): List[(BDD, MalteseArray, BVExpr, BVExpr)] = {
    pairs.flatMap { case (guard, index, data) =>
      if (guard.equals(array.guard)) { return List((guard, array.value, index, data)) }
      val conj = array.guard.and(guard)
      if (conj.isZero) { None }
      else { Some((conj, array.value, index, data)) }
    }
  }

  // TODO: with better types, we should be able to have a single function for combining entries
  def makePairs(array: ArrayValueSummary, other: List[(BDD, BVExpr)]): List[(BDD, MalteseArray, BVExpr)] =
    array.entries.flatMap(makePairs(_, other))

  private def makePairs(array: ArrayEntry, other: List[(BDD, BVExpr)]): List[(BDD, MalteseArray, BVExpr)] = {
    other.flatMap { case (guard, data) =>
      if (guard.equals(array.guard)) { return List((guard, array.value, data)) }
      val conj = array.guard.and(guard)
      if (conj.isZero) { None }
      else { Some((conj, array.value, data)) }
    }
  }

  def ite(cond: BVValueSummary, tru: => ArrayValueSummary, fals: => ArrayValueSummary): ArrayValueSummary = {
    // if the condition is concrete, we only need to evaluate one side of the mux
    if (cond.isTrue) { tru }
    else if (cond.isFalse) { fals }
    else {
      val ctx = tru.ctx
      assert(ctx.eq(tru.ctx) && ctx.eq(fals.ctx))
      // TODO: integrate SMT solver for better filtering
      val isFalse: BDD => Boolean =
        if (ctx.opts.CheckITEConditionWithSmtSolver) { b => b.isZero || ctx.isUnSat(b) }
        else { b => b.isZero }

      // find all conditions under which the true/false branch will be taken
      val condEntries = BVValueSummary.getEntries(cond)
      val truCond = condEntries.map(e => ctx.smtToBdd(e.value).and(e.guard)).filterNot(isFalse)
      val falsCond = condEntries.map(e => ctx.smtToBdd(e.value).not().and(e.guard)).filterNot(isFalse)

      def combine(conds: List[BDD], entries: List[ArrayEntry]): List[ArrayEntry] =
        conds.flatMap(c =>
          entries.flatMap { e =>
            val combinedGuard = c.and(e.guard)
            if (isFalse(combinedGuard)) { None }
            else { Some(e.copy(guard = combinedGuard)) }
          }
        )

      val rawEntries = combine(truCond, tru.entries) ++ combine(falsCond, fals.entries)
      val newEntries = if (ctx.opts.DoNotCoalesce) { rawEntries }
      else { coalesce(rawEntries) }
      new ArrayValueSummary(ctx, newEntries)
    }
  }

  private def coalesce(entries: List[ArrayEntry]): List[ArrayEntry] = {
    val (duplicate, others) = entries.groupBy(_.value).partition(_._2.size > 1)
    if (duplicate.isEmpty) {
      entries
    } else {
      (duplicate.map { case (_, entries) =>
        val combinedGuard = entries.map(_.guard).reduce((a, b) => a.or(b))
        entries.head.copy(guard = combinedGuard)
      } ++ others.map(_._2.head)).toList
    }
  }

  def toConcrete(e: ArrayExpr): Option[BigIntArray] = e match {
    case ArrayStore(array, BVLiteral(index, _), BVLiteral(value, _)) =>
      toConcrete(array).map(_ + (index -> value))
    case ArrayConstant(BVLiteral(value, _), indexWidth) =>
      Some(BigIntArray(value, indexWidth))
    case foo: ArrayFunctionCall =>
      throw new RuntimeException(s"Array function calls are unsupported!\n$foo")
    case ite: ArrayIte =>
      throw new RuntimeException(s"Array ite s are unsupported! Should be part of the value summary instead.\n$ite")
    case _ => None
  }

  def toSMT(v: ArrayValueSummary): ArrayExpr = {
    if (v.entries.size == 1) {
      v.entries.head.value.symbolic
    } else {
      v.entries.drop(1).foldLeft(v.entries.head.value.symbolic) { (a: ArrayExpr, b: ArrayEntry) =>
        val cond: BVExpr = v.ctx.bddToSmt(b.guard)
        val (c, t, f) = cond match {
          case BVNot(n_cond) => (n_cond, a, b.value.symbolic)
          case _             => (cond, b.value.symbolic, a)
        }
        ArrayIte(c, t, f)
      }
    }
  }
}

class ArrayValueSummary private (
  private val ctx:     SymbolicContext,
  private val entries: List[ArrayValueSummary.ArrayEntry])
    extends ValueSummary {
  require(entries.nonEmpty)
  val indexWidth = entries.head.indexWidth
  require(entries.forall(_.indexWidth == indexWidth))
  val dataWidth = entries.head.dataWidth
  require(entries.forall(_.dataWidth == dataWidth))
  override def size: Int = entries.size
  override def isConcrete = (size == 1) && entries.head.value.toConcrete.isDefined
  def value: Option[BigIntArray] = if (size == 1) { entries.head.value.toConcrete }
  else { None }
  def symbolic: ArrayExpr = ArrayValueSummary.toSMT(this)
  override def toString = if (size < 100) {
    SMTSimplifier.simplify(ArrayValueSummary.toSMT(this)).toString
  } else { s"ValueSummary w/ $size entries" }
}

class BVValueSummary private (private val ctx: SymbolicContext, private val entries: List[BVValueSummary.BVEntry])
    extends ValueSummary {
  require(entries.nonEmpty)
  val width = entries.head.width
  require(entries.forall(_.width == width))
  def isTrue:  Boolean = entries.size == 1 && entries.head.value == True()
  def isFalse: Boolean = entries.size == 1 && entries.head.value == False()
  override def toString = if (size < 100) {
    SMTSimplifier.simplify(BVValueSummary.toSMT(this)).toString
  } else { s"ValueSummary w/ $size entries" }
  override def size: Int = entries.size
  override def isConcrete = (size == 1) && entries.head.value.isInstanceOf[BVLiteral]
  def value: Option[BigInt] = if (isConcrete) {
    Some(entries.head.value.asInstanceOf[BVLiteral].value)
  } else { None }
  def symbolic: BVExpr = BVValueSummary.toSMT(this)
  def isValid:  Boolean = ctx.isValid(this)
  def isSat:    Boolean = ctx.isSat(this)
}
