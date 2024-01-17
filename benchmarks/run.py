# Copyright 2022-2023 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
#
# contains code to execute benchmarks
import io
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
import os
from benchmarks import VerilogOracleTestbench


@dataclass
class RunConf:
    include_dir: Path = None
    timeout: float = None
    compile_timeout: float = None
    verbose: bool = False
    show_stdout: bool = False
    defines: list = field(default_factory=list)
    logfile: io.TextIOBase = None


def run_oracle_tb(working_dir: Path, sim: str, tb: VerilogOracleTestbench, conf: RunConf) -> bool:
    raise NotImplementedError("TODO")


def run(working_dir: Path, sim: str, files: list, conf: RunConf) -> bool:
    if sim == 'vcs':
        return run_with_vcs(working_dir, files, conf)
    elif sim == 'iverilog':
        return run_with_iverilog(working_dir, files, conf)
    else:
        raise NotImplementedError(f"Simulator `{sim}` is not supported! Try `vcs` or `iverilog`!")


def _print(conf: RunConf, msg: str):
    if conf.logfile is not None:
        print(msg, file=conf.logfile)
    if conf.verbose:
        print(msg)


def _conf_streams(conf: RunConf):
    if conf.logfile:
        return conf.logfile, conf.logfile
    stderr = None
    if conf.show_stdout:
        return None, stderr
    return subprocess.PIPE, stderr


def _flush_log(conf: RunConf):
    if conf.logfile:
        conf.logfile.flush()


def run_with_iverilog(working_dir: Path, files: list, conf: RunConf) -> bool:
    cmd = ['iverilog', '-g2012']
    if conf.include_dir is not None:
        cmd += ["-I", str(conf.include_dir.resolve())]
    for name, value in conf.defines:
        cmd += [f"-D{name}={value}"]
    cmd += files
    _print(conf, " ".join(str(c) for c in cmd))
    stdout, stderr = _conf_streams(conf)
    # while iverilog generally does not timeout, we add the timeout here for feature parity with the VCS version
    try:
        _flush_log(conf)
        r = subprocess.run(cmd, cwd=working_dir, check=False, stdout=stdout, stderr=stderr,
                           timeout=conf.compile_timeout)
        compiled_successfully = r.returncode == 0
    except subprocess.TimeoutExpired:
        compiled_successfully = False
    _flush_log(conf)
    # if the simulation does not compile, we won't run anything
    if compiled_successfully:
        try:
            _print(conf, './a.out')
            _flush_log(conf)
            r = subprocess.run(['./a.out'], cwd=working_dir, shell=True, timeout=conf.timeout, stdout=stdout,
                               stderr=stderr)
            success = r.returncode == 0
        except subprocess.TimeoutExpired:
            success = False  # failed
        _flush_log(conf)
        os.remove(os.path.join(working_dir, 'a.out'))
        return success
    else:
        return False  # failed to compile


_vcs_flags = ["-sverilog", "-full64"]


def run_with_vcs(working_dir: Path, files: list, conf: RunConf) -> bool:
    cmd = ["vcs"] + _vcs_flags
    if conf.include_dir is not None:
        cmd += [f"+incdir+{str(conf.include_dir.resolve())}"]
    for name, value in conf.defines:
        cmd += [f"+define+{name}={value}"]
    cmd += files
    _print(conf, " ".join(str(c) for c in cmd))
    stdout, stderr = _conf_streams(conf)
    # VCS can take hours to compile for some changes ...
    try:
        r = subprocess.run(cmd, cwd=working_dir, check=False, stdout=stdout, stderr=stderr,
                           timeout=conf.compile_timeout)
        compiled_successfully = r.returncode == 0
    except subprocess.TimeoutExpired:
        compiled_successfully = False
    # if the simulation does not compile, we won't run anything
    if compiled_successfully:
        try:
            _print(conf, './simv')
            r = subprocess.run(['./simv'], cwd=working_dir, shell=False, timeout=conf.timeout, stdout=stdout,
                               stderr=stderr)
            success = r.returncode == 0
        except subprocess.TimeoutExpired:
            success = False  # failed
        return success
    else:
        return False  # failed to compile

_OkEmoji = "✔️"
_FailEmoji = "❌"


def success_to_emoji(success: bool) -> str:
    return _OkEmoji if success else _FailEmoji


@dataclass
class SimResult:
    no_output: bool = False
    failed_at: int = -1
    fail_msg: str = ""
    cycles: int = None # number of cycles executed

    @property
    def is_success(self): return self.failed_at == -1 and not self.no_output

    @property
    def emoji(self): return success_to_emoji(self.is_success)


def _parse_csv_item(item: str) -> str:
    item = item.strip()
    if len(item) <= 1:
        return item
    if item[0] == '"' and item[-1] == '"':
        item = item[1:-1].strip()
    return item


def parse_csv_line(line: str) -> list:
    return [_parse_csv_item(n) for n in line.split(',')]

def check_against_oracle(oracle_filename: Path, output_filename: Path) -> SimResult:
    # check output length to determine the number of cycles
    with open(output_filename) as output:
        cycles = 0
        for _ in output:
            cycles += 1
    with open(oracle_filename) as oracle, open(output_filename) as output:
        oracle_header, output_header = parse_csv_line(oracle.readline()), parse_csv_line(output.readline())
        assert oracle_header == output_header, f"{oracle_header} != {output_header}"
        has_time = oracle_header[0].lower() == 'time'
        if has_time:
            header = oracle_header[1:]
        else:
            header = oracle_header

        # compare line by line
        for (ii, (expected, actual)) in enumerate(zip(oracle, output)):
            expected, actual = parse_csv_line(expected), parse_csv_line(actual)
            # remove first line (time)
            if has_time:
                expected, actual = expected[1:], actual[1:]
            msg = []
            for ee, aa, nn in zip(expected, actual, header):
                ee, aa = ee.lower(), aa.lower()
                if ee != 'x' and ee != aa:
                    msg.append(f"{nn}@{ii}: {aa} != {ee} (expected)")
            if len(msg) > 0:
                return SimResult(failed_at=ii, fail_msg='\n'.join(msg), cycles=cycles)

        # are we missing some output?
        remaining_oracle_lines = oracle.readlines()
        if len(remaining_oracle_lines) > 0:
            # we expected more output => fail!
            msg = f"Output stopped at {ii}. Expected {len(remaining_oracle_lines)} more lines."
            return SimResult(failed_at=ii, fail_msg=msg, cycles=cycles)

    return SimResult(cycles=cycles)
