# Comparing Solutions

Often, there exist multiple repair solutions. Currently, we just pick the first one that works on the
provided test bench. However, often the test benches do not test the complete behavior of the circuit
and thus some solutions might actually break untested functionality.
We do avoid this problem somewhat because we always search for the smallest "edit" first. However,
for some examples that is not enough.

_Note_: for now, ranking solutions that result in the exact same circuit is out of scope.

## Example: `first_counter_overflow` with `kgoliya` bug
The bug removes the reset value for the `counter_out` register.
The test bench never disables the counter while it is running, it only has enable set to
zero for one cycle after coming out of reset. Thus adding back the reset assignment outside
of the reset block is feasible. This sets `counter_out` to zero when: `!reset && !enable`.
This is not the intended behavior, since the original circuit expects the `counter_out` value
to stay the same when disabled and not to be reset to zero. The original circuit also
always resets the register to zero, even if `enable` stays true the whole time.
We can get the correct repair result by adding one cycle to the testbench where the value
stays the same because `!enable`.

## Ideas on how to rank / compare solutions

- can we detect holes in the testbench and thus decide which the more likely fix is?
  - this might be hard because we do not know what the ground truth output would be
- given two fixes, can we come up with a minimal testbench change to demonstrate the difference?
  - it is possible that both repairs are actually equivalent, then we can filter them out
  - if they are not the same, what would be the best way to present the difference to the user?
