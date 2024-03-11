# RTL-Repair: Fast Symbolic Repair of Hardware Design Code

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10798649.svg)](https://doi.org/10.5281/zenodo.10798649)


This artifact includes:
- the code for our rtl-repair tool in: `rtlrepair` and `synth`
- repair benchmarks from the CirFix paper: `benchmarks/cirfix`
- the CirFix tool: `cirfix`
- repair benchmarks derived from reproducible bugs from "Debugging in the Brave New World of Reconfigurable Hardware" (ASPLOS'22): `benchmarks/fpga-debugging`
- benchmarking scripts `scripts`
- a small rtl-repair demo: `demo`

## Kick the Tires

To quickly test out that the artifact works on your machine we recommend going through the following steps which you should be able to complete in around 30min:
- [Installation](#installation) (~15min)
- [Artifact Setup](#artifact-setup) (~2min)
- [OSDD Measurements](#osdd-measurements) (~4min)
- [Default RTL Repair Evaluation](#rtl-repair-repairs) (run only the first command ~7min)
- [Demo (Optional)](#demo-optional) (play with the tool, min. 2min)


## Installation

### Python

Please make sure that you have Python in version 3.10 or newer installed. We have tested all scripts with `Python 3.10.6`.


### Rust

Please make sure you have [a recent version of Rust installed](https://www.rust-lang.org/tools/install). When in doubt, please update your version to the latest (most commonly through `rustup update`).

### Open-Source Verilog Simulators, SMT Solvers and the Yosys Synthesis Tool

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

$ yosys -version
Yosys 0.20+42 (git sha1 1c36f4cc2, clang 10.0.0-4ubuntu1 -fPIC -Os)
```

### Commercial Verilog Simulator: VCS

To perform a full evaluation, you need access to the [commercial VCS simulator from Synopsys](https://www.synopsys.com/verification/simulation/vcs.html). The setup for VCS may depend on the kind of licensing you use. Please contact your local computer support person for guidance.

While RTL-Repair works perfectly well without VCS, there are two reasons why VCS is required to perform the evaluation:

1. The CirFix tool that we compare against only works well with VCS. We did try to make it work with `iverilog`, however, the results were much worse.
2. Some of the benchmarks provided by CirFix only execute correctly on VCS. Unfortunately their tests or their designs were written in such a manner that they won't work on `iverilog`.

Thus we require VCS to evaluate CirFix, to execute benchmarks when we check repairs and to execute benchmarks in order to calculate the OSDD (output state divergence delta).

## Artifact Setup

_This step should take around 2 min._

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
cd ..
```

We implemented a VCD comparison for our OSDD measurement in rust as well:
```sh
cd scripts/osdd
cargo build --release
cd ../..
```


## Artifact Instructions

### OSDD Measurements

_This step should take around 4 min._


To measure the output / state divergence delta (OSDD) we need to first generate VCD traces of all ground truth and buggy designs. To do so, run the following:

```sh
./scripts/generate_vcd_traces.py --sim=vcs --timeout=25 --verbose vcd-traces
./scripts/calc_osdd.py --working-dir=vcd-traces
# delete VCD files after analysis to save disk space
rm vcd-traces/*.vcd
```


### CirFix Repairs

_This step should take around 14 h (with 8 threads on a 16-core CPU)._


We added a script which automatically runs CirFix on all benchmarks used in the original evaluation. This script can also parallelize the execution which speeds up the evaluation. Please use a conservative number of threads in order not to disadvantage CirFix. Half the number of physical cores on your machine is a good starting point, i.e., if your machine has 8 physical cores, use 4 threads.

From the root folder please run the following (where `$N` is the number of threads):
```sh
./cirfix/run.py --working-dir=cirfix-repairs --clear --experiment=cirfix-paper --simulator=vcs --threads=$N
```


### RTL-Repair Repairs

_This step should take around 40 min._


We run RTL-Repair on the CirFix benchmarks in three different configurations as well as on benchmarks from a paper on debugging FPGA hardware designs:

```sh
# takes ~7 min
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-default --clear --experiment=default
# expected final output line: defaultdict(<class 'int'>, {'success': 17, 'cannot-repair': 10, 'no-repair': 1, 'timeout': 4})

# takes ~14 min
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-all-templates --clear --experiment=all-templates
# expected final output line: defaultdict(<class 'int'>, {'success': 17, 'cannot-repair': 14, 'no-repair': 1})

# takes ~10 min
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-basic-synth --clear --experiment=basic-synth
# expected final output line: defaultdict(<class 'int'>, {'success': 16, 'cannot-repair': 8, 'no-repair': 1, 'timeout': 7})

# takes ~4 min
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-fpga --clear --experiment=fpga
# expected final output line: defaultdict(<class 'int'>, {'success': 9, 'timeout': 3, 'cannot-repair': 1})
```

_Note 1: there is no parallelism built into the run script. However, feel free to run all four experiments in parallel, which is safe since each has its own independent `working-dir`._ 

_Note 2: error messages from failing repair attempts are expected since the run script does not intercept `stderr`._

_Note 3: the `all-templates` and the `basic-synth` configuration are used in the ablation study in Table 5._


#### Explore Repairs

Have a look at some repair results. Like:

```sh
# machine readable results file for `sha3_s1` benchmark
cat rtl-repair-default/sha3_padder_ssscrazy_buggy1_oracle-full/result.toml
# diff of ground truth and buggy Verilog file
cat rtl-repair-default/sha3_padder_ssscrazy_buggy1_oracle-full/bug_diff.txt
# diff of buggy and repaired Verilog file
cat rtl-repair-default/sha3_padder_ssscrazy_buggy1_oracle-full/padder_ssscrazy_buggy1.repaired.0.diff.txt
```

_Note: Unfortunately there are some artifacts still left by our repair tool which makes the repair diff somewhat hard to read.
In the particular case mentioned above, we need to focus on the line starting with `assign update` and simplify the expression in our head._

### Checking Repair Correctness

_This step should take around 120 min (~40min if you can run the scripts in parallel)._

We provide a script that performs all the correctness tests listed in Table 4. We run that on all results from the CirFix benchmark set.

```sh
# takes ~39 min
./scripts/check_repairs.py --results=cirfix-repairs --working-dir=cirfix-repairs-check --sim=vcs
# takes ~30 min
./scripts/check_repairs.py --results=rtl-repair-default --working-dir=rtl-repair-default-check --sim=vcs
# takes ~30 min
./scripts/check_repairs.py --results=rtl-repair-all-templates --working-dir=rtl-repair-all-templates-check --sim=vcs
# takes ~30 min
./scripts/check_repairs.py --results=rtl-repair-basic-synth --working-dir=rtl-repair-basic-synth-check --sim=vcs

```

_Note 1: there is no parallelism built into the script. However, feel free to run all invocations in parallel, which is safe since each has its own independent `working-dir`. There are also no performance numbers taken in this step, so don't worry about interference from other tasks._ 

_Note 2: the checks do not work with the FPGA benchmark set because they rely on Verilog testbenches, whereas the FPGA benchmarks come with C++ testbenches for the Verilator simulator._


### Generate Tables

_This step should take around 2 min._

We provide a script that generates LaTex versions of Tables 1, 2, 4 and 5 from the data we previously collected.

```sh
./scripts/create_tables.py --working-dir=tables \
  --osdd-toml=vcd-traces/osdd.toml \
  --baseline-toml=vcd-traces/baseline_results.toml \
  --cirfix-result-dir=cirfix-repairs-check \
  --rtlrepair-result-dir=rtl-repair-default-check \
  --rtlrepair-all-templates-result-dir=rtl-repair-all-templates-check \
  --rtlrepair-basic-synth-result-dir=rtl-repair-basic-synth-check
```

### Demo (Optional)

_This step takes around 2 min. Longer, if you would like to play some more with the tool._

The artifact contains a small demo to explore the repair capabilities of RTL-Repair.
In the `demo` folder you find:

- a simple Verilog design from the CirFix benchmarks: `project/first_counter.v`
- a simple testbench in the CSV format: `project/tb.csv`
- a script to execute the testbench with `iverilog`: `./run_tb.py`
  - this script will write pass/fail information to stdout
  - this script also creates a wavedump in `project/dump.vcd` which can be viewer with [GTKWave](https://gtkwave.sourceforge.net/) or [Surfer](http://surfer-project.org/)
- a script to execute a repair with rtl-repair: `./do_repair.py`

To get started, try changing the reset condition in `project/first_counter.v`:
```diff
-  if(reset == 1'b1) begin
+  if(reset == 1'b0) begin
```

Then run `./do_repair.py` which should output:
```
success (0.32s)
0) Possible repair with 1 changes:
14c14
<     if(reset == 1'b0) begin
---
>     if(reset == 1'b1) begin

================================================================================
```