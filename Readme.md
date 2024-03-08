# RTL-Repair: Fast Symbolic Repair of Hardware Design Code

## Installation

### Python

Please make sure that you have Python in version 3.10 or newer installed.


### Rust

Please make sure you have [a recent version of Rust installed](https://www.rust-lang.org/tools/install). When in doubt, please update your version to the latest (most commonly through `rustup update`).

### Verilog Simulators and SMT Solver

Download [OSS CAD Suite version `2022-06-22` from github](https://github.com/YosysHQ/oss-cad-suite-build/releases/tag/2022-06-22) and put the binaries on your path.

_Note: newer versions of the OSS CAD Suite include Verilator 5. Unfortunately, the current implementation of RTL-Repair only works with Verilator 4._

Check to make sure that you have all tools that we require on your path in the correct version:

```.sh
$ verilator --version
Verilator 4.225 devel rev v4.224-91-g0eeb40b9

$ bitwuzla --version
1.0-prerelease

$ yices-smt2 --version
Yices 2.6.4

$ iverilog -v
Icarus Verilog version 12.0 (devel) (s20150603-1556-g542da1166)

```


## Artifact Instructions

### OSDD Measurements

To measure the output / state divergence delta (OSDD) you need to first
generate VCD traces of all ground truth and buggy designs.
To do so, run the following:
```commandline
python3 generate_vcd_traces.py --timeout=25 -v data
```