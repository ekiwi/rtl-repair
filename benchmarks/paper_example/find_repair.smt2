(declare-const reset@0 Bool)
(declare-const enable@0 Bool)
(declare-const count@0 (_ BitVec 4))
(declare-const overflow@0 Bool)
(declare-const phi0 Bool)
(declare-const phi1 Bool)
(declare-const alpha0 (_ BitVec 4))
(declare-const alpha1 (_ BitVec 4))

; random concrete initial state
(assert (= overflow@0 true))
(assert (= count@0 (_ bv8 4)))

; next state
(define-fun count@1 () (_ BitVec 4)
  (ite (and (= count@0 (_ bv15 4)) phi1)
    alpha1
  (ite (and reset@0 phi0) alpha0
  (ite (and (not reset@0) enable@0)
    (bvadd count@0 (_ bv1 4))
  count@0))))

; I/O trace
(assert reset@0)
(assert (= count@1 (_ bv0 4)))

(check-sat)
(get-value (phi0))
(get-value (alpha0))
(get-value (phi1))
(get-value (alpha1))

; find solution with two changes
(assert (= #b10 (bvadd (ite phi1 #b01 #b00) (ite phi0 #b01 #b00))))
(check-sat)
(get-value (phi0))
(get-value (alpha0))
(get-value (phi1))
(get-value (alpha1))