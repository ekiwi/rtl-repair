# RTL-Repair


## Artifact Instructions

### OSDD Measurements

To measure the output / state divergence delta (OSDD) you need to first
generate VCD traces of all ground truth and buggy designs.
To do so, run the following:
```commandline
python3 generate_vcd_traces.py --timeout=25 -v data
```