#!/usr/bin/env bash

# c1
../../synth/target/release/synth \
  --design ../../working-dir/zipcpu-spi-c1-c3-d9_c1_csv/2_add_guard/llsdspi_bug_c1.instrumented.btor \
  --testbench ../../benchmarks/fpga-debugging/zipcpu-spi-c1-c3-d9/tb.csv \
  --solver bitwuzla --init zero --study-unrolling > c1_unroll.log

