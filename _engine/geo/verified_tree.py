#!/usr/bin/env python3
"""Attest an exactly tested Git tree and fail closed on any content drift."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


VERSION = 1
OBJECT_LENGTHS = {"sha1": 40, "sha256": 64}
HEX_RE = re.compile(r"[0-9a-f]+")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr[-1000:]}"
        )
    return result.stdout


def _proof(status: str, suite: str, object_format: str, tree: str) -> str:
    payload = "\0".join(
        (str(VERSION), status, suite, object_format, tree)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _document(
    status: str,
    suite: str,
    object_format: str,
    tree: str,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": status,
        "suite": suite,
        "object_format": object_format,
        "tree": tree,
        "proof_sha256": _proof(status, suite, object_format, tree),
    }


def _load(path: Path, suite: str, status: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Unreadable verified-tree attestation: {error}"
        ) from error
    required = {
        "version",
        "status",
        "suite",
        "object_format",
        "tree",
        "proof_sha256",
    }
    if (
        not isinstance(document, dict)
        or set(document) != required
        or document.get("version") != VERSION
        or document.get("status") != status
        or document.get("suite") != suite
        or not isinstance(document.get("object_format"), str)
        or not isinstance(document.get("tree"), str)
        or document["object_format"] not in OBJECT_LENGTHS
        or len(document["tree"])
        != OBJECT_LENGTHS[document["object_format"]]
        or not HEX_RE.fullmatch(document["tree"])
        or not isinstance(document.get("proof_sha256"), str)
        or len(document["proof_sha256"]) != 64
        or not HEX_RE.fullmatch(document["proof_sha256"])
        or document.get("proof_sha256")
        != _proof(
            status,
            suite,
            document["object_format"],
            document["tree"],
        )
    ):
        raise ValueError("Invalid verified-tree attestation")
    return document


def _object_format(root: Path) -> str:
    return _git(root, "rev-parse", "--show-object-format").strip()


def _index_tree(root: Path) -> str:
    return _git(root, "write-tree").strip()


def prepare(root: Path, output: Path, suite: str) -> dict[str, Any]:
    try:
        output.resolve().relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Verified-tree attestation must be outside the repo")
    _git(root, "add", "-A")
    document = _document(
        "prepared",
        suite,
        _object_format(root),
        _index_tree(root),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def _worktree_matches_index(root: Path) -> bool:
    unstaged = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", "--"],
        check=False,
    )
    if unstaged.returncode not in (0, 1):
        raise RuntimeError("git diff failed while sealing verified tree")
    untracked = _git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )
    return unstaged.returncode == 0 and not untracked


def seal(root: Path, output: Path, suite: str) -> dict[str, Any]:
    prepared = _load(output, suite, "prepared")
    if not _worktree_matches_index(root):
        raise ValueError("Test execution changed the candidate tree")
    if _object_format(root) != prepared["object_format"]:
        raise ValueError("Git object format changed during test execution")
    if _index_tree(root) != prepared["tree"]:
        raise ValueError("Git index changed during test execution")
    document = _document(
        "sealed",
        suite,
        prepared["object_format"],
        prepared["tree"],
    )
    output.write_text(
        json.dumps(document, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def matches_head(root: Path, output: Path, suite: str) -> bool:
    try:
        sealed = _load(output, suite, "sealed")
    except ValueError as error:
        print(f"verified-tree miss: {error}", file=sys.stderr)
        return False
    if _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ):
        print("verified-tree miss: worktree is not clean", file=sys.stderr)
        return False
    if _object_format(root) != sealed["object_format"]:
        print("verified-tree miss: Git object format changed", file=sys.stderr)
        return False
    head_tree = _git(root, "rev-parse", "HEAD^{tree}").strip()
    if head_tree != sealed["tree"]:
        print("verified-tree miss: committed content changed", file=sys.stderr)
        return False
    print(
        f"verified-tree hit: {sealed['object_format']}:{head_tree} "
        f"suite={suite}"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "seal", "matches-head"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "prepare":
        prepare(root, args.output, args.suite)
        return 0
    if args.action == "seal":
        seal(root, args.output, args.suite)
        return 0
    return 0 if matches_head(root, args.output, args.suite) else 1


if __name__ == "__main__":
    raise SystemExit(main())
