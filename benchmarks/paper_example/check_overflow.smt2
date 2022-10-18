(declare-const reset@0 Bool)
(declare-const counter_out@0 (_ BitVec 4))
(declare-const overflow_out@0 Bool)


(define-fun overflow_out@1 () Bool
  (ite (= counter_out@0 (_ bv15 4)) true
  (ite reset@0 false overflow_out@0)))(assert reset@0) ; reset the circuit in the first step
(assert overflow_out@1) ; can the overflow be true?

(check-sat)
(get-model)
