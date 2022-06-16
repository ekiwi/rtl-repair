#!/usr/bin/env bash

yosys -p "read_verilog first_counter_overflow.v ; proc -noopt ; write_btor -x first_counter_overflow.btor"
yosys -p "read_verilog first_counter_overflow_wadden_buggy2.v ; proc -noopt ; write_btor -x first_counter_overflow_wadden_buggy2.btor"
yosys -p "read_verilog first_counter_overflow_kgoliya_buggy1.v ; proc -noopt ; write_btor -x first_counter_overflow_kgoliya_buggy1.btor"
