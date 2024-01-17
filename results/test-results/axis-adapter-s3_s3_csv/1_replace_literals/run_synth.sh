#!/usr/bin/env bash
/home/kevin/d/rtl-repair/synth/target/release/synth --design /home/kevin/d/rtl-repair/tmp1/axis-adapter-s3_s3_csv/1_replace_literals/axis_adapter_bug_s3.instrumented.btor --testbench /home/kevin/d/rtl-repair/benchmarks/fpga-debugging/axis-adapter-s3/tb.csv --solver yices2 --init zero --incremental --verbose --max-incorrect-solutions-per-window-size 4
