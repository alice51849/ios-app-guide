#!/usr/bin/env python3
"""Run every discovered GEO unittest while isolating CPU-heavy tree gates."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_START = HERE / "tests"
HEAVY_TESTS = (
    "test_growth_infra.GeneratorTests."
    "test_published_public_guides_share_one_premium_stylesheet",
    "test_growth_infra.GeneratorTests."
    "test_published_answers_pass_semantic_integrity_gate",
)


@dataclass(frozen=True)
class Lane:
    name: str
    tests: tuple[str, ...]


def _test_ids(suite: unittest.TestSuite) -> list[str]:
    ids: list[str] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            ids.extend(_test_ids(item))
        else:
            ids.append(item.id())
    return ids


def discover_tests(
    start_dir: Path = DEFAULT_START,
    pattern: str = "test_*.py",
) -> list[str]:
    suite = unittest.defaultTestLoader.discover(
        str(start_dir),
        pattern=pattern,
        top_level_dir=str(start_dir),
    )
    ids = _test_ids(suite)
    if not ids or len(ids) != len(set(ids)):
        raise RuntimeError("Unittest discovery returned no tests or duplicates")
    return sorted(ids)


def partition_tests(
    test_ids: list[str],
    jobs: int,
    heavy_tests: tuple[str, ...] = HEAVY_TESTS,
) -> list[Lane]:
    if jobs < 1:
        raise ValueError("jobs must be positive")
    if jobs == 1:
        return [Lane("all", tuple(test_ids))]
    missing = [test for test in heavy_tests if test not in test_ids]
    if missing:
        raise RuntimeError(
            "Required heavy gate was not discovered: " + ", ".join(missing)
        )
    heavy_lanes = [
        Lane(f"heavy-{index + 1}", (test,))
        for index, test in enumerate(heavy_tests[: jobs - 1])
    ]
    assigned = {test for lane in heavy_lanes for test in lane.tests}
    remaining = [test for test in test_ids if test not in assigned]
    tail_count = jobs - len(heavy_lanes)
    tails = [
        Lane(
            f"remainder-{index + 1}",
            tuple(remaining[index::tail_count]),
        )
        for index in range(tail_count)
    ]
    lanes = [*heavy_lanes, *tails]
    flattened = [test for lane in lanes for test in lane.tests]
    if len(flattened) != len(test_ids) or set(flattened) != set(test_ids):
        raise RuntimeError("Parallel unittest partition lost or duplicated tests")
    return [lane for lane in lanes if lane.tests]


def _run_lane(
    lane: Lane,
    *,
    start_dir: Path,
) -> tuple[Lane, int, float, str]:
    started = time.monotonic()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            (
                str(start_dir),
                str(ROOT),
                environment.get("PYTHONPATH", ""),
            ),
        )
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "-q",
            "-b",
            *lane.tests,
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return lane, result.returncode, time.monotonic() - started, output


def run_all(
    test_ids: list[str],
    jobs: int,
    *,
    start_dir: Path = DEFAULT_START,
) -> int:
    lanes = partition_tests(test_ids, jobs)
    with ThreadPoolExecutor(max_workers=len(lanes)) as executor:
        results = list(
            executor.map(
                partial(_run_lane, start_dir=start_dir),
                lanes,
            )
        )
    failed = False
    for lane, returncode, duration, output in results:
        if returncode:
            failed = True
            print(
                f"FAIL {lane.name} ({len(lane.tests)} tests, "
                f"{duration:.2f}s)",
                file=sys.stderr,
            )
            print(output, file=sys.stderr)
        else:
            print(
                f"PASS {lane.name}: {len(lane.tests)} tests "
                f"in {duration:.2f}s"
            )
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-dir", type=Path, default=DEFAULT_START)
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()
    tests = discover_tests(args.start_dir.resolve(), args.pattern)
    return run_all(
        tests,
        args.jobs,
        start_dir=args.start_dir.resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
