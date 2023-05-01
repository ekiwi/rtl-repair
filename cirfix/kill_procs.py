#!/usr/bin/env python3
# Copyright 2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

import argparse
import getpass
import signal
import time
import psutil
from dataclasses import dataclass


@dataclass
class Config:
    limits: dict
    dry_run: bool

@dataclass
class ProcLimit:
    max_time_s: float
    max_mem_mib: float
    # When not none, the process is killed as soon as non of the parents have the expected name
    required_parent: str = None

_default_limits = {
    # The actual VCS binary is called `vcs1`. `vcs` is just a shell script.
    # Limit to 15min and 4GiB
    'vcs1': ProcLimit(max_time_s=15 * 60.0, max_mem_mib=4 * 1024, required_parent="python3"),
    # Limit any simulation run to 15min and 4GiB
    'simv': ProcLimit(max_time_s=10 * 60.0, max_mem_mib=4 * 1024, required_parent="python3"),
}

def parse_limit(value: str):
    parts = [p.strip() for p in value.split(':')]
    assert len(parts) == 3 or len(parts) == 4, f"Invalid limit: {value}"
    limit = ProcLimit(max_time_s=float(parts[1]), max_mem_mib=float(parts[2]))
    if len(parts) > 3:
        limit.required_parent = parts[3]
    return parts[0], limit


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description='kill runaway vcs')
    # The actual VCS binary is called `vcs1`. `vcs` is just a shell script.
    parser.add_argument('-l', '--limits', help="name:max_time_s:max_mem_mib", nargs='*')
    parser.add_argument('--dry-run', action="store_true", default=False, help="Print out instead of killing process.")
    args = parser.parse_args()

    limits = {**_default_limits} # shallow copy defaults
    if args.limits is not None:
        for value in args.limits:
            name, limit = parse_limit(value)
            limits[name] = limit

    return Config(limits, dry_run=args.dry_run)


def kill_proc(dry_run: bool, p: psutil.Process, reason: str):
    if dry_run:
        print(f"KILL {p.name()}: {reason}")
    else:
        try:
            sig = signal.SIGTERM
            timeout = 10
            procs  = p.children(recursive=True) + [p]
            name = p.name()
            cmd = p.cmdline()
            for p in procs:
                try:
                    p.send_signal(sig)
                except psutil.NoSuchProcess:
                    pass
            gone, alive = psutil.wait_procs(procs, timeout=timeout, callback=None)
            assert len(alive) == 0, f"Failed to terminate {name} for {reason}.\n" \
            f"Still alive: {[pp.name() for pp in alive]}."
            print(f"KILLED {name}: {reason}\n{cmd}")
        except psutil.NoSuchProcess:
            pass # ignore if process is already dead


def get_parent_names(p: psutil.Process) -> list:
    try:
        parents = p.parents()
    except psutil.NoSuchProcess:
        return []
    names = []
    for parent in parents:
        try:
            names.append(parent.name())
        except psutil.NoSuchProcess:
            pass # ignore if parent is dead
    return names


def monitor_procs(conf: Config):
    """ Sometimes VCS or the simulation will escape from being a child process and thus ignore our timeout.
        This function checks to see if there are any such runaway processes and then terminates them.
    """
    # username to only look at our processes
    current_user = getpass.getuser()

    # the process attributes that we are interested in
    attributes = ['name', 'username', 'memory_info', 'cpu_times']

    while True: # TODO: what is a good way to terminate this?
        for p in psutil.process_iter(attributes):
            info = p.info
            # skip processes from other users
            if info['username'] != current_user:
                continue

            # skip processes that do not match the
            if info['name'] not in conf.limits:
                continue

            # extract data
            total_time_s = info['cpu_times'].user + info['cpu_times'].system
            total_mem_mb = (info['memory_info'].rss // 1024) / 1024
            name = info['name']
            limit = conf.limits[name]

            # printout info for now:
            # print(f"{name}: {total_time_s}s, {total_mem_bytes_mb}MiB, limit={limit}")

            # check for limits
            if total_time_s > limit.max_time_s:
                kill_proc(conf.dry_run, p, f"Exceeded maximum execution time {limit.max_time_s:.1f}s < {total_time_s:.1f}s")
            elif total_mem_mb > limit.max_mem_mib:
                kill_proc(conf.dry_run, p, f"Exceeded maximum memory {limit.max_mem_mib:.1f}MiB < {total_mem_mb:.1f}MiB")
            elif limit.required_parent is not None:
                parents = get_parent_names(p)
                # when parents is the empty list, that normally indicates that the process has already died
                if len(parents) > 0 and limit.required_parent not in parents:
                    kill_proc(conf.dry_run, p, f"No longer a child of {limit.required_parent}. Parents: {parents}")

        # sleep
        time.sleep(1.0)


def main():
    conf = parse_args()
    monitor_procs(conf)


if __name__ == '__main__':
    main()
