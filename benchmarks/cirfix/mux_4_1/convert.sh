#!/usr/bin/env bash

yosys -p "read_verilog mux_4_1.v ; proc -noopt ; write_btor -x mux_4_1.btor"
yosys -p "read_verilog mux_4_1_kgoliya_buggy1.v ; proc -noopt ; write_btor -x mux_4_1_kgoliya_buggy1.btor"
yosys -p "read_verilog mux_4_1_wadden_buggy2.v ; proc -noopt ; write_btor -x mux_4_1_wadden_buggy2.btor"
yosys -p "read_verilog mux_4_1_wadden_buggy1.v ; proc -noopt ; write_btor -x mux_4_1_wadden_buggy1.btor"

