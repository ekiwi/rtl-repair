#!/usr/bin/env bash

# sdram w2
../synth/target/release/synth \
  --design ../working-dir/sdram_controller_wadden_buggy2_oracle-full/1_replace_literals/sdram_controller_wadden_buggy2.no_tri_state.instrumented.btor \
  --testbench ../benchmarks/cirfix/sdram_controller/orig_tb.csv \
  --solver bitwuzla --init any --windowing --max-repair-window-size 512 > sdram_w2.log

