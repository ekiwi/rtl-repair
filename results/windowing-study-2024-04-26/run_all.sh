#!/usr/bin/env bash

./c1.sh &
./i2c_k1.sh &
./sdram_w1.sh &
./sdram_w2.sh &
./c1_unroll.sh &
./i2c_k1_unroll.sh &
./sdram_w1_unroll.sh &
./sdram_w2_unroll.sh
