#!/usr/bin/env bash

../../synth/target/release/synth \
  --design ../../working-dir/i2c_master_kgoliya_buggy1_fixed_x_prop_tb/3_conditional_overwrite/i2c_master_bit_ctrl_kgoliya_buggy1.sync_reset.instrumented.btor \
  --testbench ../../benchmarks/cirfix/opencores/i2c/fixed_x_prop_tb.csv \
  --solver bitwuzla --init any --study-unrolling > i2c_k1_unroll.log

