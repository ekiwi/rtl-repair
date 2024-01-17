#!/usr/bin/env bash
yosys -p "read_verilog /home/kevin/d/rtl-repair/tmp1/axis-adapter-s3_s3_csv/1_replace_literals/axis_adapter_bug_s3.instrumented.v ; hierarchy -top axis_adapter ; proc -noopt ; async2sync ; flatten ; dffunmap ; write_btor -x /home/kevin/d/rtl-repair/tmp1/axis-adapter-s3_s3_csv/1_replace_literals/axis_adapter_bug_s3.instrumented.btor"
