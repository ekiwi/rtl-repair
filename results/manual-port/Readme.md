# Repairs the need manual porting

For two benchmarks (`i2c` and `sdram`) we had to manually remove
async reset and tri-state buses because these Verilog features are
not supported by `rtl-repair` at the moment.
We thus had to manually port the (one-line) repair back to the
original files for a fair comparison with CirFix.

This directory contains the automatic repair of the modified design
and the manual port of the fix to the original Verilog source.
