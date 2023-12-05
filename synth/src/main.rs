// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>
mod testbench;

use crate::testbench::Testbench;
use clap::{Parser, ValueEnum};
use libpatron::ir::*;
use libpatron::*;
use serde_json::json;

#[derive(Parser, Debug)]
#[command(name = "synth")]
#[command(author = "Kevin Laeufer <laeufer@berkeley.edu>")]
#[command(version)]
#[command(about = "Generates repair solutions.", long_about = None)]
struct Args {
    #[arg(
        long,
        required = true,
        help = "the design to be repaired with the template instantiated in btor format"
    )]
    design: String,
    #[arg(long, required = true, help = "the testbench in CSV format")]
    testbench: String,
    #[arg(long, help = "output debug messages")]
    verbose: bool,
    #[arg(long, help = "use the incremental instead of the basic synthesizer")]
    incremental: bool,
    #[arg(
        long,
        value_enum,
        default_value = "bitwuzla",
        help = "the SMT solver to use"
    )]
    solver: Solver,
    #[arg(
        long,
        value_enum,
        default_value = "zero",
        help = "initialization strategy"
    )]
    init: Init,
    #[arg(
        long,
        default_value_t = 2u64,
        help = "step size for past-k in incremental solver"
    )]
    pask_k_step_size: u64,
    #[arg(
        long,
        default_value_t = 32u64,
        help = "the maximum repair window size before the incremental solver gives up"
    )]
    max_repair_window_size: u64,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
enum Solver {
    Bitwuzla,
    Yices2,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum)]
enum Init {
    Zero,
    Random,
    Any, // not really supported
}

fn main() {
    let args = Args::parse();

    // load system
    let (ctx, sys) = btor2::parse_file(&args.design).expect("Failed to load btor2 file!");

    // load testbench
    let tb = Testbench::load(&ctx, &sys, &args.testbench).expect("Failed to load testbench.");

    // run testbench once to see if we can detect a bug

    let res = json!({
        "status": "cannot-repair",
        "solver-time": 0,
        "past-k": 0,
        "future-k": 0,
        "solutions": [],
    });

    println!("== RESULT =="); // needle to find the JSON output
    let j = serde_json::to_string(&res).unwrap();
    println!("{}", j);
}
