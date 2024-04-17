#!/usr/bin/env bash

# sdram w1
../synth/target/release/synth \
  --design ../working-dir/sdram_controller_wadden_buggy1_oracle-full/3_conditional_overwrite/sdram_controller_wadden_buggy1.no_tri_state.instrumented.btor \
  --testbench ../benchmarks/cirfix/sdram_controller/orig_tb.csv \
  --solver bitwuzla --init any --windowing --max-repair-window-size 512 > sdram_w1.log

