#!/usr/bin/env python3
"""Run one command with a platform-independent exit-124 timeout contract."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys


TIMEOUT_EXIT = 124


def shell_exit_code(returncode: int) -> int:
    if returncode < 0:
        return 128 + abs(returncode)
    return returncode


def signal_process_group(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def stop_timed_out_process(
    process: subprocess.Popen[bytes],
    grace_seconds: float,
) -> None:
    signal_process_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        signal_process_group(process, signal.SIGKILL)
        process.wait()
    else:
        # The group leader may exit before a descendant that ignored SIGTERM.
        signal_process_group(process, signal.SIGKILL)


def run(command: list[str], seconds: float, grace_seconds: float) -> int:
    try:
        process = subprocess.Popen(command, start_new_session=True)
    except OSError as exc:
        print(
            f"bounded timeout could not start {command[0]}: {exc}",
            file=sys.stderr,
        )
        return 127

    try:
        return shell_exit_code(process.wait(timeout=seconds))
    except subprocess.TimeoutExpired:
        stop_timed_out_process(process, grace_seconds)
        return TIMEOUT_EXIT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--grace-seconds", type=float, default=2.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.seconds <= 0 or args.grace_seconds < 0:
        parser.error("timeout must be positive and grace period non-negative")
    if not command:
        parser.error("a command is required after --")
    return run(command, args.seconds, args.grace_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
