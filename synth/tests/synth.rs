// Copyright 2023 The Regents of the University of California
// released under BSD 3-Clause License
// author: Kevin Laeufer <laeufer@berkeley.edu>

use std::path::Path;
use std::process::Command;

fn do_test(design: &str, tb: &str, init: &str, solver: &str, incremental: bool) {
    let input_dir = Path::new("tests/inputs");
    assert!(input_dir.exists());

    // check to make sure inputs exists
    let design_path = input_dir.join(design);
    let tb_path = input_dir.join(tb);
    assert!(design_path.exists(), "{design_path:?} not found!");
    assert!(tb_path.exists(), "{tb_path:?} not found!");

    // check to see that binary exists
    let bin_path = Path::new("target/debug/synth");
    assert!(bin_path.exists(), "Binary {bin_path:?} missing.");

    // call binary
    let mut command = Command::new(bin_path);
    command
        .arg("--design")
        .arg(design_path)
        .arg("--testbench")
        .arg(tb_path)
        .arg("--solver")
        .arg(solver)
        .arg("--init")
        .arg(init);
    if incremental {
        command.arg("--incremental");
    }
    let res = command.output().expect("failed to run synth");
    assert!(res.status.success(), "Failed to execute: {command:?}");
    println!("{}", String::from_utf8_lossy(&res.stdout));
}

#[test]
fn test_decoder_original() {
    do_test(
        "decoder.original.replace_literals.btor",
        "decoder.orig_tb.csv",
        "any",
        "yices2",
        false,
    );
}
