; SMT-LIBv2 description generated by Yosys 0.18+29 (git sha1 b2408df31, clang 10.0.0-4ubuntu1 -fPIC -Os)
; yosys-smt2-module test
(declare-sort |test_s| 0)
(declare-fun |test_is| (|test_s|) Bool)
(declare-fun |test#0| (|test_s|) (_ BitVec 1)) ; \read
; test#1 = ite(read, 0, 1)
(define-fun |test#1| ((state |test_s|)) (_ BitVec 1) (ite (= ((_ extract 0 0) (|test#0| state)) #b1) #b0 #b1)) ; $ternary$test.sv:5$1_Y
; yosys-smt2-output out 1
; io = ite(read, 0, 1)
(define-fun |test_n out| ((state |test_s|)) Bool (= ((_ extract 0 0) (|test#1| state)) #b1))
; yosys-smt2-input io 1
; yosys-smt2-output io 1
; io = ite(read, 0, 1)
(define-fun |test_n io| ((state |test_s|)) Bool (= ((_ extract 0 0) (|test#1| state)) #b1))
; yosys-smt2-input read 1
(define-fun |test_n read| ((state |test_s|)) Bool (= ((_ extract 0 0) (|test#0| state)) #b1))
(define-fun |test_a| ((state |test_s|)) Bool true)
(define-fun |test_u| ((state |test_s|)) Bool true)
(define-fun |test_i| ((state |test_s|)) Bool true)
(define-fun |test_h| ((state |test_s|)) Bool true)
(define-fun |test_t| ((state |test_s|) (next_state |test_s|)) Bool true) ; end of module test
; yosys-smt2-topmod test
; end of yosys output