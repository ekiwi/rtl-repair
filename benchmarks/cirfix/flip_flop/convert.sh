#!/usr/bin/env bash

yosys -p "read_verilog tff.v ; proc -noopt ; write_btor -x tff.btor"
yosys -p "read_verilog tff_wadden_buggy1.v ; proc -noopt ; write_btor -x tff_wadden_buggy1.btor"
yosys -p "read_verilog tff_wadden_buggy2.v ; proc -noopt ; write_btor -x tff_wadden_buggy2.btor"

