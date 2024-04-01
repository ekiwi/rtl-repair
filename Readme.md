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

$ iverilog -v
Icarus Verilog version 12.0 (devel) (s20150603-1556-g542da1166)

$ yosys -version
Yosys 0.18+29
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
# NOTE: if you are on a faster machine, you might experience fewer timeouts!

# takes ~4 min
./scripts/run_rtl_repair_experiment.py --working-dir=rtl-repair-fpga --clear --experiment=fpga
# expected final output line: defaultdict(<class 'int'>, {'success': 9, 'timeout': 3, 'cannot-repair': 1})
# NOTE: if you are on a faster machine, you might experience fewer timeouts!
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


### Port Repairs to Original Code

_This step should take around 3 min._

As mentioned in our paper "We had to manually remove a tri-state bus and an asynchronous reset for two benchmarks as these constructs are not supported by RTL-Repair.". Thus, for the `i2c` and `sdram` benchmarks, RTL-Repair will work with a version of the benchmark where the tri-state bus or the asynchronous reset was manually removed. Unfortunately this means that the repair has to manually be ported to the original design.

To simplify this process we rely on the fact that repairs generated by RTL-Repair are always deterministic. We thus copied all repairs we expect you to get into the `results/manual-port` directory and also added a port of the repair to the original Verilog code. Now all you need to do to add these manual repairs is to run a script on your results like this:

```sh
./scripts/add_manually_ported_repairs.py --working-dir=rtl-repair-default
./scripts/add_manually_ported_repairs.py --working-dir=rtl-repair-all-templates
./scripts/add_manually_ported_repairs.py --working-dir=rtl-repair-basic-synth
```

This script will look through all rtl-repair results and if it finds one for a benchmark that has been ported it:
1. first checks to make sure that the repaired Verilog code matches the repair that we manually ported 100%
2. if it matches, the manual port of the repair to the original Verilog (with the async-reset / tri-state bus) is copied to the results directory
3. a `manual=` entry is added to the `result.toml` to indicate that there is a manual overwrite

### Checking Repair Correctness

_This step should take around 130 min (~40min if you can run the scripts in parallel)._

We provide a script that performs all the correctness tests listed in Table 4. We run that on all results from the CirFix benchmark set.

```sh
# takes ~40 min
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

### Compare Tables

Now we want to compare the results from the tables generated in the previous step to the results reported in the paper.

The performance numbers should roughly match the ones reported in the paper. Some variation is expected because the reproduction is run on a different machine. Different versions of VCS or different VCS license setups might also affect results.

#### Table 1: RTL-Repair vs State-of-the-Art Tool

```sh
cat tables/performance_statistics_table.txt
```

_Note: If your experiments ran on a faster machine, you might see fewer timeouts._

#### Table 2: Output / State Divergence Delta Evaluation

```sh
cat tables/osdd_table.txt
```


#### Table 4: Repair Correctness Evaluation

```sh
cat tables/correctness_table.txt
```

#### Table 5: Repair Speed Evaluation

```sh
cat tables/ablation_table.txt
```


_Note: If your experiments ran on a faster machine, you might see fewer timeouts._

#### Table 6: Open Source Bug Results

Unfortunately this table was created manually. To check the results, have a look at the `result.toml` in your `rtl-repair-fpga` folder.

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