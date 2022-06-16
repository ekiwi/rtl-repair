#!/usr/bin/env bash

yosys -p "read_verilog fsm_full.v ; proc -noopt ; write_btor -x fsm_full.btor"
yosys -p "read_verilog fsm_full_wadden_buggy1.v ; proc -noopt ; write_btor -x fsm_full_wadden_buggy1.btor"
yosys -p "read_verilog fsm_full_ssscrazy_buggy2.v ; proc -noopt ; write_btor -x fsm_full_ssscrazy_buggy2.btor"


