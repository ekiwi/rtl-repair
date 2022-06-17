#!/usr/bin/env bash

yosys -p "read_verilog lshift_reg.v ; proc -noopt ; write_btor -x lshift_reg.btor"
yosys -p "read_verilog lshift_reg_wadden_buggy1.v ; proc -noopt ; write_btor -x lshift_reg_wadden_buggy1.btor"
yosys -p "read_verilog lshift_reg_wadden_buggy2.v ; proc -noopt ; write_btor -x lshift_reg_wadden_buggy2.btor"

