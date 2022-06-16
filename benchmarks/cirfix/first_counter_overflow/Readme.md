# First Counter Overflow

## Simulation/Synthesis Mismatch

The original benchmark has a x-optimism related
simulation/synthesis mismatch problem.

When the `counter_out` register starts at `15`,
one cycle of reset is not enough to ensure that `overflow_out`
will be `0` after reset goes low again.
In the original Verilog, this problem is hidden by the
`#1` delays which cannot be synthesized.
We fix the problem by removing all delays and adding an `else`
in order to ensure that the `overflow_out` bit is only set
if the counter overflows and we are not in reset.

Since this fix is similar to what was thought to be a bug in
`first_counter_overflow_wadden_buggy2.v` we change
that bug to the original file without the `#1` delays hiding the
bug in the original.
