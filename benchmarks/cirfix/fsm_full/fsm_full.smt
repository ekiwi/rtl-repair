; SMT-LIBv2 description generated by Yosys 0.12+42 (git sha1 7407a7f3e, clang 10.0.0-4ubuntu1 -fPIC -Os)
; yosys-smt2-module fsm_full
(declare-sort |fsm_full_s| 0)
(declare-fun |fsm_full_is| (|fsm_full_s|) Bool)
(declare-fun |fsm_full#0| (|fsm_full_s|) (_ BitVec 3)) ; \state
; yosys-smt2-register state 3
(define-fun |fsm_full_n state| ((state |fsm_full_s|)) (_ BitVec 3) (|fsm_full#0| state))
(declare-fun |fsm_full#1| (|fsm_full_s|) (_ BitVec 1)) ; \gnt_3
; yosys-smt2-output gnt_3 1
; yosys-smt2-register gnt_3 1
(define-fun |fsm_full_n gnt_3| ((state |fsm_full_s|)) Bool (= ((_ extract 0 0) (|fsm_full#1| state)) #b1))
(declare-fun |fsm_full#2| (|fsm_full_s|) (_ BitVec 1)) ; \gnt_2
; yosys-smt2-output gnt_2 1
; yosys-smt2-register gnt_2 1
(define-fun |fsm_full_n gnt_2| ((state |fsm_full_s|)) Bool (= ((_ extract 0 0) (|fsm_full#2| state)) #b1))
(declare-fun |fsm_full#3| (|fsm_full_s|) (_ BitVec 1)) ; \gnt_1
; yosys-smt2-output gnt_1 1
; yosys-smt2-register gnt_1 1
(define-fun |fsm_full_n gnt_1| ((state |fsm_full_s|)) Bool (= ((_ extract 0 0) (|fsm_full#3| state)) #b1))
(declare-fun |fsm_full#4| (|fsm_full_s|) (_ BitVec 1)) ; \gnt_0
; yosys-smt2-output gnt_0 1
; yosys-smt2-register gnt_0 1
(define-fun |fsm_full_n gnt_0| ((state |fsm_full_s|)) Bool (= ((_ extract 0 0) (|fsm_full#4| state)) #b1))
(declare-fun |fsm_full#5| (|fsm_full_s|) Bool) ; \req_3
; yosys-smt2-input req_3 1
(define-fun |fsm_full_n req_3| ((state |fsm_full_s|)) Bool (|fsm_full#5| state))
(declare-fun |fsm_full#6| (|fsm_full_s|) Bool) ; \req_2
; yosys-smt2-input req_2 1
(define-fun |fsm_full_n req_2| ((state |fsm_full_s|)) Bool (|fsm_full#6| state))
(declare-fun |fsm_full#7| (|fsm_full_s|) Bool) ; \req_1
; yosys-smt2-input req_1 1
(define-fun |fsm_full_n req_1| ((state |fsm_full_s|)) Bool (|fsm_full#7| state))
(declare-fun |fsm_full#8| (|fsm_full_s|) Bool) ; \req_0
; yosys-smt2-input req_0 1
(define-fun |fsm_full_n req_0| ((state |fsm_full_s|)) Bool (|fsm_full#8| state))
(declare-fun |fsm_full#9| (|fsm_full_s|) Bool) ; \reset
; yosys-smt2-input reset 1
(define-fun |fsm_full_n reset| ((state |fsm_full_s|)) Bool (|fsm_full#9| state))
(declare-fun |fsm_full#10| (|fsm_full_s|) Bool) ; \clock
; yosys-smt2-input clock 1
; yosys-smt2-clock clock posedge
(define-fun |fsm_full_n clock| ((state |fsm_full_s|)) Bool (|fsm_full#10| state))
(define-fun |fsm_full#11| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b001)) ; $procmux$50_CMP
(define-fun |fsm_full#12| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$51_CMP
(define-fun |fsm_full#13| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#12| state) #b0 (ite (|fsm_full#11| state) #b1 (|fsm_full#4| state)))) ; $procmux$49_Y
(define-fun |fsm_full#14| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#9| state) #b0 (|fsm_full#13| state))) ; $procmux$53_Y
(define-fun |fsm_full#15| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b010)) ; $procmux$40_CMP
(define-fun |fsm_full#16| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$41_CMP
(define-fun |fsm_full#17| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#16| state) #b0 (ite (|fsm_full#15| state) #b1 (|fsm_full#3| state)))) ; $procmux$39_Y
(define-fun |fsm_full#18| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#9| state) #b0 (|fsm_full#17| state))) ; $procmux$43_Y
(define-fun |fsm_full#19| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b011)) ; $procmux$31_CMP
(define-fun |fsm_full#20| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$32_CMP
(define-fun |fsm_full#21| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#20| state) #b0 (ite (|fsm_full#19| state) #b1 (|fsm_full#2| state)))) ; $procmux$30_Y
(define-fun |fsm_full#22| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#9| state) #b0 (|fsm_full#21| state))) ; $procmux$34_Y
(define-fun |fsm_full#23| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b100)) ; $procmux$23_CMP
(define-fun |fsm_full#24| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$24_CMP
(define-fun |fsm_full#25| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#24| state) #b0 (ite (|fsm_full#23| state) #b1 (|fsm_full#1| state)))) ; $procmux$22_Y
(define-fun |fsm_full#26| ((state |fsm_full_s|)) (_ BitVec 1) (ite (|fsm_full#9| state) #b0 (|fsm_full#25| state))) ; $procmux$26_Y
(define-fun |fsm_full#27| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#5| state) #b1 #b0) #b0)) ; $eq$fsm_full.v:69$9_Y
(define-fun |fsm_full#28| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#27| state) #b000 #b100)) ; $procmux$57_Y
(define-fun |fsm_full#29| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b100)) ; $procmux$60_CMP
(define-fun |fsm_full#30| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#29| state) (|fsm_full#28| state) #b000)) ; $procmux$59_Y
(define-fun |fsm_full#31| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#6| state) #b1 #b0) #b0)) ; $eq$fsm_full.v:64$8_Y
(define-fun |fsm_full#32| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#31| state) #b000 #b011)) ; $procmux$64_Y
(define-fun |fsm_full#33| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b011)) ; $procmux$67_CMP
(define-fun |fsm_full#34| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#33| state) (|fsm_full#32| state) #b000)) ; $procmux$66_Y
(define-fun |fsm_full#35| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#7| state) #b1 #b0) #b0)) ; $eq$fsm_full.v:59$7_Y
(define-fun |fsm_full#36| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#35| state) #b000 #b010)) ; $procmux$72_Y
(define-fun |fsm_full#37| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b010)) ; $procmux$75_CMP
(define-fun |fsm_full#38| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#37| state) (|fsm_full#36| state) #b000)) ; $procmux$74_Y
(define-fun |fsm_full#39| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#8| state) #b1 #b0) #b0)) ; $eq$fsm_full.v:54$6_Y
(define-fun |fsm_full#40| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#39| state) #b000 #b001)) ; $procmux$81_Y
(define-fun |fsm_full#41| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b001)) ; $procmux$84_CMP
(define-fun |fsm_full#42| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#41| state) (|fsm_full#40| state) #b000)) ; $procmux$83_Y
(define-fun |fsm_full#43| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#5| state) #b1 #b0) #b1)) ; $eq$fsm_full.v:49$5_Y
(define-fun |fsm_full#44| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#43| state) #b100 #b000)) ; $procmux$91_Y
(define-fun |fsm_full#45| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#6| state) #b1 #b0) #b1)) ; $eq$fsm_full.v:47$4_Y
(define-fun |fsm_full#46| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#45| state) #b000 (|fsm_full#44| state))) ; $procmux$94_Y
(define-fun |fsm_full#47| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#7| state) #b1 #b0) #b1)) ; $eq$fsm_full.v:45$3_Y
(define-fun |fsm_full#48| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#47| state) #b000 (|fsm_full#46| state))) ; $procmux$97_Y
(define-fun |fsm_full#49| ((state |fsm_full_s|)) Bool (= (ite (|fsm_full#8| state) #b1 #b0) #b1)) ; $eq$fsm_full.v:43$2_Y
(define-fun |fsm_full#50| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#49| state) #b000 (|fsm_full#48| state))) ; $procmux$100_Y
(define-fun |fsm_full#51| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$103_CMP
(define-fun |fsm_full#52| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#51| state) (|fsm_full#50| state) #b000)) ; $procmux$102_Y
(define-fun |fsm_full#53| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#45| state) #b011 (|fsm_full#52| state))) ; $procmux$110_Y
(define-fun |fsm_full#54| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#47| state) #b000 (|fsm_full#53| state))) ; $procmux$113_Y
(define-fun |fsm_full#55| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#49| state) #b000 (|fsm_full#54| state))) ; $procmux$116_Y
(define-fun |fsm_full#56| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$119_CMP
(define-fun |fsm_full#57| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#56| state) (|fsm_full#55| state) #b000)) ; $procmux$118_Y
(define-fun |fsm_full#58| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#47| state) #b010 (|fsm_full#57| state))) ; $procmux$126_Y
(define-fun |fsm_full#59| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#49| state) #b000 (|fsm_full#58| state))) ; $procmux$129_Y
(define-fun |fsm_full#60| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$132_CMP
(define-fun |fsm_full#61| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#60| state) (|fsm_full#59| state) #b000)) ; $procmux$131_Y
(define-fun |fsm_full#62| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#49| state) #b001 (|fsm_full#61| state))) ; $procmux$139_Y
(define-fun |fsm_full#63| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$142_CMP
(define-fun |fsm_full#64| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#63| state) (|fsm_full#62| state) #b000)) ; $procmux$141_Y
(define-fun |fsm_full#65| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b100)) ; $procmux$145_CMP
(define-fun |fsm_full#66| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b011)) ; $procmux$146_CMP
(define-fun |fsm_full#67| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b010)) ; $procmux$147_CMP
(define-fun |fsm_full#68| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b001)) ; $procmux$148_CMP
(define-fun |fsm_full#69| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$149_CMP
(define-fun |fsm_full#70| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#69| state) (|fsm_full#64| state) (ite (|fsm_full#68| state) (|fsm_full#42| state) (ite (|fsm_full#67| state) (|fsm_full#38| state) (ite (|fsm_full#66| state) (|fsm_full#34| state) (ite (|fsm_full#65| state) (|fsm_full#30| state) #b000)))))) ; $procmux$144_Y
(define-fun |fsm_full#71| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b100)) ; $procmux$13_CMP
(define-fun |fsm_full#72| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b011)) ; $procmux$14_CMP
(define-fun |fsm_full#73| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b010)) ; $procmux$15_CMP
(define-fun |fsm_full#74| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b001)) ; $procmux$16_CMP
(define-fun |fsm_full#75| ((state |fsm_full_s|)) Bool (= (|fsm_full#0| state) #b000)) ; $procmux$17_CMP
(define-fun |fsm_full#76| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#75| state) (|fsm_full#70| state) (ite (|fsm_full#74| state) (|fsm_full#70| state) (ite (|fsm_full#73| state) (|fsm_full#70| state) (ite (|fsm_full#72| state) (|fsm_full#70| state) (ite (|fsm_full#71| state) (|fsm_full#70| state) #b000)))))) ; $procmux$12_Y
(define-fun |fsm_full#77| ((state |fsm_full_s|)) (_ BitVec 3) (ite (|fsm_full#9| state) #b000 (|fsm_full#76| state))) ; $procmux$19_Y
(define-fun |fsm_full_a| ((state |fsm_full_s|)) Bool true)
(define-fun |fsm_full_u| ((state |fsm_full_s|)) Bool true)
(define-fun |fsm_full_i| ((state |fsm_full_s|)) Bool true)
(define-fun |fsm_full_h| ((state |fsm_full_s|)) Bool true)
(define-fun |fsm_full_t| ((state |fsm_full_s|) (next_state |fsm_full_s|)) Bool (and
  (= (|fsm_full#14| state) (|fsm_full#4| next_state)) ; $procdff$150 \gnt_0
  (= (|fsm_full#18| state) (|fsm_full#3| next_state)) ; $procdff$151 \gnt_1
  (= (|fsm_full#22| state) (|fsm_full#2| next_state)) ; $procdff$152 \gnt_2
  (= (|fsm_full#26| state) (|fsm_full#1| next_state)) ; $procdff$153 \gnt_3
  (= (|fsm_full#77| state) (|fsm_full#0| next_state)) ; $procdff$154 \state
)) ; end of module fsm_full
; yosys-smt2-topmod fsm_full
; end of yosys output
