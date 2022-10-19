(declare-const reset@0 Bool)
(declare-const enable@0 Bool)
(declare-const count@0 (_ BitVec 4))
(declare-const overflow@0 Bool)
(declare-const phi0 Bool)
(declare-const phi1 Bool)
(declare-const alpha0 (_ BitVec 4))
(declare-const alpha1 (_ BitVec 4))

; random concrete initalization for state
(assert overflow@0)
(assert (= count@0 (_ bv8 4)))

; apply inputs from testbench
(assert reset@0)

; next state
(define-fun count@1 () (_ BitVec 4)
  (ite (and (= count@0 (_ bv15 4)) phi1) alpha1
  (ite (and reset@0 phi0) alpha0
  (ite (and (not reset@0) enable@0) (bvadd count@0 (_ bv1 4))
  count@0)))
)

; assert outputs
(assert (= count@1 (_ bv0 4)))

(check-sat)
(get-value (phi0))
(get-value (alpha0))
(get-value (phi1))
(get-value (alpha1))

; block solution
(assert (not (and phi0 (not phi1))))
(check-sat)
(get-value (phi0))
(get-value (alpha0))
(get-value (phi1))
(get-value (alpha1))