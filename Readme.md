# RTL-Repair: Fast Symbolic Repair of Hardware Design Code

## Installation

### Python

Please make sure that you have Python in version 3.10 or newer installed.


### Rust

Please make sure you have [a recent version of Rust installed](https://www.rust-lang.org/tools/install). When in doubt, please update your version to the latest (most commonly through `rustup update`).

### Open-Source Verilog Simulators and SMT Solver

Download [OSS CAD Suite version `2022-06-22` from github](https://github.com/YosysHQ/oss-cad-suite-build/releases/tag/2022-06-22) and put the binaries on your path.

_Note: newer versions of the OSS CAD Suite include Verilator 5. Unfortunately, the current implementation of RTL-Repair only works with Verilator 4._

Check to make sure that you have all tools that we require on your path in the correct version:

```sh
$ verilator --version
Verilator 4.225 devel rev v4.224-91-g0eeb40b9

$ bitwuzla --version
1.0-prerelease

$ yices-smt2 --version
Yices 2.6.4

$ iverilog -v
Icarus Verilog version 12.0 (devel) (s20150603-1556-g542da1166)
```

### Commercial Verilog Simulator: VCS

To perform a full evaluation, you need access to the [commercial VCS simulator from Synopsys](https://www.synopsys.com/verification/simulation/vcs.html). The setup for VCS may depend on the kind of licensing you use. Please contact your local computer support person for guidance.

While RTL-Repair works perfectly well without VCS, there are two reasons why VCS is required to perform the evaluation:

1. The CirFix tool that we compare against only works well with VCS. We did try to make it work with `iverilog`, however, the results were much worse.
2. Some of the benchmarks provided by CirFix only execute correctly on VCS. Unfortunately their tests or their designs were written in such a manner that they won't work on `iverilog`.

Thus we require VCS to evaluate CirFix, to execute benchmarks when we check repairs and to execute benchmarks in order to calculate the OSDD (output state divergence delta).

## Artifact Setup

First we need to create a virtual environment in the root folder of the repository. This virtual environment needs to be activated in all later steps.

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

We also need to build the synthesizer binary once.
```sh
cd synth
cargo build --release
```


## Artifact Instructions

### OSDD Measurements

To measure the output / state divergence delta (OSDD) we need to first generate VCD traces of all ground truth and buggy designs. To do so, run the following:

```sh
./scripts/generate_vcd_traces.py --sim=vcs --timeout=25 --verbose vcd-traces
./scripts/calc_osdd.py --working-dir=vcd-traces
```

**TODO** run calc osdd script!

### CirFix Repairs

We added a script which automatically runs CirFix on all benchmarks used in the original evaluation. This script can also parallelize the execution which speeds up the evaluation. Please use a conservative number of threads in order not to disadvantage CirFix. Half the number of physical cores on your machine is a good starting point, i.e., if your machine has 8 physical cores, use 4 threads.

From the root folder please run the following (where `$N` is the number of threads):
```sh
./cirfix/run.py --working-dir=cirfix-repairs --clear --experiment=cirfix-paper --simulator=vcs --thread=$N
```

### RTL-Repair Repairs

We run RTL-Repair on the CirFix benchmarks in three different configurations as well as on benchmarks from a paper on debugging FPGA hardware designs:

```sh
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-default --clear --experiment=default
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-all-templates --clear --experiment=all-templates
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-basic-synth --clear --experiment=basic-synth
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-fpga --clear --experiment=fpga
```

_Note: there is no parallelism since RTL-Repair runs very quickly anyways._ 

_Note 2: the `all-templates` and the `basic-synth` configuration are used in the ablation study in Table 5._

### Checking Repair Correctness

We provide a script that performs all the correctness tests listed in Table 4. We run that on all results from the CirFix benchmark set.

```sh
./scripts/check_repairs.py --results=cirfix-repairs --working-dir=cirfix-repairs-check --sim=vcs
./scripts/check_repairs.py --results=rtl-repair-repairs --working-dir=rtl-repair-repairs-check --sim=vcs
```

**TODO**: make this step use less space by not generating traces by default!

_Note: the checks do not work with the FPGA benchmark set because they rely on Verilog testbenches, whereas the FPGA benchmarks come with C++ testbenches for the Verilator simulator._

### Generating Tables

We provide a script that generates LaTex versions of Tables 1, 2, 4 and 5 from the data we previously collected.

```sh
./scripts/create_tables.py --working-dir=tables \
  --osdd-toml=vcd-traces/osdd.toml \
  --baseline-toml=vcd-traces/baseline_results.toml \
  --cirfix-result-dir=cirfix-repairs-check \
  --rtlrepair-result-dir=rtl-repair-default \
  --rtlrepair-all-templates-result-dir=rtl-repair-all-templates \
  --rtlrepair-basic-synth-result-dir=rtl-repair-basic-synth \
```