#!/usr/bin/env python3
# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
# this script loads all benchmarks and performs some sanity checks + calculates statistics

import benchmarks


def run_tb():
    pass


def main():
    projects = benchmarks.load_all_projects()
    print(f"Loaded {len(projects)} projects")
    for name, proj in projects.items():
        benchmarks.validate_project(proj)
        assert proj.name == name, f"{proj.name} =/= {name}"
    print(f"Validated {len(projects)} project configurations")
    bbs = []
    for _, proj in projects.items():
        bbs += benchmarks.get_benchmarks(proj)
    print(f"Loaded {len(bbs)} benchmarks")
    cirfix_bbs = [bb for bb in bbs if benchmarks.is_cirfix_paper_benchmark(bb)]
    print(f"Found {len(cirfix_bbs)} benchmarks that were used in the CirFix paper.")
    assert len(cirfix_bbs) == 32, "the cirfix paper features 32 benchmarks"
    repaired_bbs = [bb for bb in cirfix_bbs if benchmarks.get_seed(bb) is not None]
    print(f"{len(repaired_bbs)}/{len(cirfix_bbs)} benchmarks are claimed 'repaired' by CirFix.")
    assert len(repaired_bbs) == 21, "the cirfix paper claims 21 repaired benchmarks"



if __name__ == '__main__':
    main()
