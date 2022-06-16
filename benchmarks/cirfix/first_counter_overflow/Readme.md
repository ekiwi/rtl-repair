# First Counter Overflow

## Simulation/Synthesis Mismatch

The original benchmark has a x-optimism related
simulation/synthesis mismatch problem.

When the `counter_out` register starts at `15`,
one cycle of reset is not enough to ensure that `overflow_out`
will be `0` after reset goes low again.
In the original Verilog, this problem is hidden by the
`#1` delays which cannot be synthesized.
We fix the problem by removing all delays and adding `!reset`
as an additional condition to the branch that sets `overflow_out`.
This ensures that the bit is only set if the counter overflows and
reset is in-active.
