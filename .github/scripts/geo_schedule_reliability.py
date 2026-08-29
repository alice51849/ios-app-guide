#!/usr/bin/env python3
"""Audit and evidence helpers for the natural GEO schedule chain."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


CATEGORIES = (
    "success",
    "code/config",
    "timeout",
    "quota",
    "remote drift",
    "concurrency",
    "Pages",
    "IndexNow",
    "external service",
)

CRITICAL_REMOTE_PREFIXES = (
    ".github/scripts/",
    "_engine/data/",
    "_engine/geo/",
    "_engine/social/",
)
CRITICAL_REMOTE_FILES = {
    ".appstore_live_state.json",
    ".github/workflows/geo-daily.yml",
    "apps.json",
}


def _combined_signal(record: dict[str, Any]) -> str:
    parts = [
        str(record.get("conclusion") or ""),
        str(record.get("failing_step") or ""),
    ]
    parts.extend(str(item) for item in record.get("signals", []))
    return "\n".join(parts).lower()


def classify_record(record: dict[str, Any]) -> str:
    """Classify one schedule attempt from API metadata plus log signals."""
    conclusion = str(record.get("conclusion") or "").lower()
    signal = _combined_signal(record)
    if conclusion == "success":
        return "success"
    if conclusion == "cancelled":
        return "concurrency"
    if conclusion == "timed_out" or re.search(
        r"\b(timeout|timed out|exit 124|time limit)\b",
        signal,
    ):
        return "timeout"
    if re.search(
        r"\b(quota|rate limit|secondary rate|billing|http 429)\b",
        signal,
    ):
        return "quota"
    if "indexnow" in signal:
        return "IndexNow"
    if re.search(r"\b(pages deploy|deploy-pages|github pages)\b", signal):
        return "Pages"
    if re.search(
        (
            r"(failed to push|fetch first|main moved|remote contains work|"
            r"merge conflict|conflict \(|invalid git history date|"
            r"origin/main advanced|remote drift)"
        ),
        signal,
    ):
        return "remote drift"
    if re.search(
        (
            r"(could not resolve host|connection reset|connection refused|"
            r"temporary upstream|service unavailable|http 5\d\d|"
            r"standard\.site unavailable|app store lookup unavailable)"
        ),
        signal,
    ):
        return "external service"
    return "code/config"


def replay_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data["runs"]
    observed = Counter()
    mismatches = []
    for record in records:
        category = classify_record(record)
        observed[category] += 1
        if category != record["expected_category"]:
            mismatches.append(
                {
                    "run_id": record["run_id"],
                    "expected": record["expected_category"],
                    "actual": category,
                }
            )
    expected = Counter(data["expected_counts"])
    if len(records) != 28:
        mismatches.append(
            {"fixture": "run_count", "expected": 28, "actual": len(records)}
        )
    if observed != expected:
        mismatches.append(
            {
                "fixture": "category_counts",
                "expected": dict(expected),
                "actual": dict(observed),
            }
        )
    return {
        "window": data["window"],
        "run_count": len(records),
        "counts": {key: observed.get(key, 0) for key in CATEGORIES},
        "mismatches": mismatches,
    }


def _require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_workflow_contracts(
    geo: str,
    pages: str,
    indexnow: str,
) -> list[str]:
    """Return fail-closed contract errors for the natural root chain."""
    errors: list[str] = []
    trigger_block = geo.split("permissions:", 1)[0]
    _require(
        errors,
        "workflow_dispatch:" not in trigger_block,
        "GEO workflow must not expose workflow_dispatch",
    )
    _require(
        errors,
        trigger_block.count("- cron:") == 4,
        "GEO workflow must retain exactly four UTC schedules",
    )
    for cron in (
        "23 1 * * *",
        "23 7 * * *",
        "23 13 * * *",
        "23 19 * * *",
    ):
        _require(errors, cron in trigger_block, f"missing UTC cron {cron}")
    _require(
        errors,
        "github.event_name == 'schedule'" in geo
        and "github.run_attempt == 1" in geo,
        "generate job must gate schedule attempt 1",
    )
    _require(errors, "TZ: UTC" in geo, "workflow must force UTC")
    timeout_match = re.search(r"timeout-minutes:\s*(\d+)", geo)
    _require(errors, timeout_match is not None, "job timeout is missing")
    if timeout_match:
        _require(
            errors,
            0 < int(timeout_match.group(1)) < 360,
            "job timeout must finish before the next six-hour root",
        )
    _require(
        errors,
        "group: ios-app-guide-main-writer" in geo
        and "cancel-in-progress: false" in geo,
        "natural writer concurrency must serialize without cancellation",
    )
    checkout = geo.split("- uses: actions/checkout@v5", 1)
    _require(errors, len(checkout) == 2, "pinned checkout@v5 is missing")
    if len(checkout) == 2:
        checkout_block = checkout[1].split("- uses:", 1)[0]
        _require(
            errors,
            "ref: ${{ github.sha }}" in checkout_block,
            "GEO root must execute its recorded head_sha",
        )
        _require(
            errors,
            "ref: main" not in checkout_block,
            "GEO root must not drift to the latest main during checkout",
        )

    validate_only = (
        "REMOTE_FIRST_VALIDATE_ONLY=1 "
        "remote_first_publish reconcile_english_phase origin main 5"
    )
    _require(
        errors,
        validate_only in geo,
        "English phase must validate without publishing",
    )
    publish_calls = [
        line.strip()
        for line in geo.splitlines()
        if "remote_first_publish reconcile_" in line
    ]
    _require(
        errors,
        len(publish_calls) == 2,
        "workflow must have one validation call and one publish call",
    )
    if len(publish_calls) == 2:
        _require(
            errors,
            sum("REMOTE_FIRST_VALIDATE_ONLY=1" in line for line in publish_calls)
            == 1,
            "exactly one remote-first call must be validate-only",
        )
    _require(
        errors,
        "REMOTE_FIRST_MAX_ATTEMPTS: \"3\"" in geo,
        "publish retry count must be bounded to three",
    )

    markers = (
        "verified_tree.py seal",
        "- name: Upload sealed candidate evidence",
        "- name: Commit localized pages if any",
        "remote_first_publish reconcile_localized_phase origin main 5",
        "- name: Record machine-readable run evidence",
        "- name: Upload run evidence",
    )
    positions: list[int] = []
    for marker in markers:
        pos = geo.find(marker)
        _require(errors, pos >= 0, f"missing ordered marker: {marker}")
        positions.append(pos)
    if all(pos >= 0 for pos in positions):
        _require(
            errors,
            positions == sorted(positions),
            "seal, candidate artifact, publish, and run evidence are misordered",
        )
    run_evidence = geo.split(
        "- name: Record machine-readable run evidence",
        1,
    )
    if len(run_evidence) == 2:
        _require(
            errors,
            "if: always()" in run_evidence[1].split("- name:", 1)[0],
            "run evidence must execute on failures",
        )
    _require(
        errors,
        "run_bounded_retry" in geo,
        "external availability refresh must use bounded retry",
    )

    _require(
        errors,
        'workflows: ["Daily GEO content"]' in pages,
        "Pages must follow the completed GEO root",
    )
    _require(
        errors,
        "github.event.workflow_run.conclusion == 'success'" in pages,
        "Pages must reject failed GEO roots",
    )
    _require(
        errors,
        "github.event.workflow_run.event == 'schedule'" in pages
        and "github.event.workflow_run.run_attempt == 1" in pages,
        "Pages must reject dispatches and rerun attempts",
    )
    _require(
        errors,
        "actions/download-artifact@v4" in pages
        and "run-id: ${{ github.event.workflow_run.id }}" in pages,
        "Pages must download the exact upstream run evidence",
    )
    _require(
        errors,
        "published-sha.txt" in pages
        and "ref: ${{ steps.source.outputs.sha }}" in pages,
        "Pages must checkout the published SHA from upstream evidence",
    )
    pages_upload = pages.find("Upload artifact")
    pages_deploy = pages.find("Deploy to GitHub Pages")
    pages_verify = pages.find("Verify exact deployment is live")
    _require(
        errors,
        0 <= pages_upload < pages_deploy < pages_verify,
        "Pages artifact/deploy/exact-readback order is invalid",
    )

    _require(
        errors,
        'workflows: ["Deploy static site to Pages"]' in indexnow,
        "IndexNow must follow Pages",
    )
    _require(
        errors,
        "github.event.workflow_run.conclusion == 'success'" in indexnow,
        "IndexNow must reject failed Pages roots",
    )
    pin = indexnow.find("Pin exact deployed source tree")
    submit = indexnow.find("Submit changed public URLs to IndexNow")
    _require(
        errors,
        0 <= pin < submit,
        "IndexNow must pin public deployment before submission",
    )
    return errors


def _run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _changed_paths(repo: Path) -> dict[str, Any]:
    raw = _run_git(repo, "status", "--porcelain=v1", "-z")
    records = [item for item in raw.split("\0") if item]
    names = sorted(item[3:] for item in records)
    digest = hashlib.sha256("\0".join(names).encode()).hexdigest()
    return {
        "count": len(names),
        "path_digest": f"sha256:{digest}",
        "sample": names[:100],
        "sample_truncated": len(names) > 100,
    }


def write_run_evidence(output: Path, repo: Path) -> dict[str, Any]:
    milestones = {
        key.removeprefix("GEO_STEP_").lower(): value
        for key, value in sorted(os.environ.items())
        if key.startswith("GEO_STEP_") and value
    }
    published_sha = os.environ.get("GEO_PUBLISHED_SHA", "").strip()
    evidence = {
        "schema_version": 1,
        "kind": "geo-natural-schedule-run-evidence",
        "recorded_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "workflow": os.environ.get("GITHUB_WORKFLOW"),
        "event_name": os.environ.get("GITHUB_EVENT_NAME"),
        "scheduled_cron": os.environ.get("GEO_SCHEDULE_CRON"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "root_head_sha": os.environ.get("GITHUB_SHA"),
        "candidate_head_sha": _run_git(repo, "rev-parse", "HEAD"),
        "published_sha": published_sha or None,
        "job_status": os.environ.get("GEO_JOB_STATUS"),
        "milestones": milestones,
        "failed_milestones": sorted(
            key for key, value in milestones.items() if value == "failure"
        ),
        "working_tree": _changed_paths(repo),
        "truth_contract": {
            "pages_deploy_is_exposure": False,
            "indexnow_acceptance_is_exposure": False,
            "public_delivery_requires_exact_manifest_readback": True,
            "index_presence_requires_independent_crawler_evidence": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if published_sha:
        (output.parent / "published-sha.txt").write_text(
            f"{published_sha}\n",
            encoding="ascii",
        )
    return evidence


def check_remote_drift(
    repo: Path,
    root_sha: str,
    remote_sha: str,
    output: Path,
) -> dict[str, Any]:
    ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", root_sha, remote_sha],
            cwd=repo,
            check=False,
        ).returncode
        == 0
    )
    changed = []
    if ancestor and root_sha != remote_sha:
        changed = [
            path
            for path in _run_git(
                repo,
                "diff",
                "--name-only",
                f"{root_sha}..{remote_sha}",
            ).splitlines()
            if path
        ]
    critical = sorted(
        path
        for path in changed
        if path in CRITICAL_REMOTE_FILES
        or path.startswith(CRITICAL_REMOTE_PREFIXES)
    )
    result = {
        "schema_version": 1,
        "root_sha": root_sha,
        "remote_sha": remote_sha,
        "root_is_ancestor": ancestor,
        "changed_path_count": len(changed),
        "critical_paths": critical,
        "publishable": ancestor and not critical,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay")
    replay.add_argument("--fixture", type=Path, required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--geo", type=Path, required=True)
    validate.add_argument("--pages", type=Path, required=True)
    validate.add_argument("--indexnow", type=Path, required=True)

    evidence = sub.add_parser("evidence")
    evidence.add_argument("--output", type=Path, required=True)
    evidence.add_argument("--repo-root", type=Path, required=True)

    drift = sub.add_parser("check-remote-drift")
    drift.add_argument("--repo-root", type=Path, required=True)
    drift.add_argument("--root-sha", required=True)
    drift.add_argument("--remote-sha", required=True)
    drift.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "replay":
        result = replay_fixture(args.fixture)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["mismatches"] else 0
    if args.command == "validate":
        errors = validate_workflow_contracts(
            args.geo.read_text(encoding="utf-8"),
            args.pages.read_text(encoding="utf-8"),
            args.indexnow.read_text(encoding="utf-8"),
        )
        print(json.dumps({"errors": errors}, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    if args.command == "evidence":
        result = write_run_evidence(args.output, args.repo_root)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    result = check_remote_drift(
        args.repo_root,
        args.root_sha,
        args.remote_sha,
        args.output,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["publishable"] else 75


if __name__ == "__main__":
    sys.exit(main())
