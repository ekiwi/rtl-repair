; note: the [...]' = [...] syntax is part of SMTLib
overflow' =
  (ite (= count (_ bv15 4)) true
  (ite reset false overflow))
count' =
  (ite reset count
  (ite enable (bvadd count (_ bv1 32))
  count))
