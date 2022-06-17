#!/usr/bin/env bash

yosys -p "read_verilog sdram_controller.v ; proc -noopt ; write_btor -x sdram_controller.btor"
yosys -p "read_verilog sdram_controller_wadden_buggy2.v ; proc -noopt ; write_btor -x sdram_controller_wadden_buggy2.btor"
yosys -p "read_verilog sdram_controller_kgoliya_buggy2.v ; proc -noopt ; write_btor -x sdram_controller_kgoliya_buggy2.btor"
yosys -p "read_verilog sdram_controller_wadden_buggy1.v ; proc -noopt ; write_btor -x sdram_controller_wadden_buggy1.btor"

