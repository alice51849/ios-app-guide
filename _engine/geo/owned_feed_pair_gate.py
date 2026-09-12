#!/usr/bin/env python3
"""Read-only paired-feature gate: source parity and forward-only Guide gitlinks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import owned_app_feeds as feeds

MIRRORS = (
    "owned_feed_pair_gate.py", "owned_app_feeds.md", "publish.py",
    "tests/owned_feed_fixtures.py", "tests/test_owned_app_feeds.py",
    "tests/test_owned_feed_delivery.py",
    "tests/test_owned_feed_receipts.py",
    "tests/test_owned_feed_reconciliation.py",
    "tests/test_owned_feed_release.py", "tests/test_notification_release.py",
    "tests/test_deployment_generation.py",
    "data/high_intent_guide_sync_contract.json",
    "tests/test_public_host_single_source.py",
    "tests/fixtures/owned_feed_receipts/websub-204.json",
    "tests/fixtures/owned_feed_receipts/rsscloud-200.json",
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def require_ancestor(guide: Path, ancestor: str, descendant: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(guide), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Guide gitlink would move backwards or sideways: {ancestor} -> {descendant}")


def gitlink(growth: Path, revision: str) -> str:
    fields = git(growth, "ls-tree", revision, "geo/pages").split()
    if len(fields) != 4 or fields[:2] != ["160000", "commit"] or fields[3] != "geo/pages":
        raise ValueError("Growth must retain the canonical Guide gitlink")
    return fields[2]


def validate(growth: Path, guide: Path, *, growth_base="origin/main", guide_base="origin/main") -> dict:
    for repo in (growth, guide):
        if not git(repo, "branch", "--show-current").startswith("feature/"):
            raise ValueError("This delivery must stay on paired feature branches")
        if git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError(f"Uncommitted paired source: {repo.name}")
    growth_sha, guide_sha = git(growth, "rev-parse", "HEAD"), git(guide, "rev-parse", "HEAD")
    if gitlink(growth, "HEAD") != guide_sha:
        raise ValueError("Growth does not pin this exact Guide candidate")
    require_ancestor(growth, git(growth, "rev-parse", growth_base), growth_sha)
    require_ancestor(guide, git(guide, "rev-parse", guide_base), guide_sha)
    require_ancestor(guide, gitlink(growth, growth_base), guide_sha)
    feeds.require_parity(growth / "geo", guide / "_engine/geo")
    for name in MIRRORS:
        if (growth / "geo" / name).read_bytes() != (guide / "_engine/geo" / name).read_bytes():
            raise ValueError(f"Paired source/test/documentation drift: {name}")
    report = feeds.build(
        guide, source=growth / "geo", check=True, reference_source=guide / "_engine/geo",
    )
    return {"growth_sha": growth_sha, "guide_sha": guide_sha, "parity": True,
            "forward_only_gitlink": True, **report}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--growth", type=Path, required=True)
    parser.add_argument("--guide", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(validate(args.growth, args.guide), sort_keys=True))


if __name__ == "__main__":
    main()
