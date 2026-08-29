#!/usr/bin/env python3
"""Validate the out-of-tree canonical app portfolio Git checkout."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Any


RELATIVE_PATH = Path("app-portfolio.md")
SOURCE_LABEL = "00_Standards/app-portfolio.md"


class LedgerValidationError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise LedgerValidationError(
            f"Canonical ledger Git command failed: {' '.join(args)}"
        ) from error


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_checkout(
    checkout_root: Path,
    pinned_commit: str | None,
) -> dict[str, Any]:
    supplied_root = checkout_root.expanduser()
    if supplied_root.is_symlink():
        raise LedgerValidationError("Canonical ledger root cannot be a symlink")
    try:
        root = supplied_root.resolve(strict=True)
    except OSError as error:
        raise LedgerValidationError(
            "Canonical ledger checkout is missing or unreadable"
        ) from error
    top_level = Path(
        _git(root, "rev-parse", "--show-toplevel").decode().strip()
    ).resolve()
    if top_level != root:
        raise LedgerValidationError(
            "Canonical ledger root must be the Git checkout root"
        )
    if RELATIVE_PATH.is_absolute() or ".." in RELATIVE_PATH.parts:
        raise LedgerValidationError("Canonical ledger relative path is unsafe")
    ledger_path = root / RELATIVE_PATH
    if ledger_path.is_symlink():
        raise LedgerValidationError("Canonical ledger file cannot be a symlink")
    try:
        resolved_ledger = ledger_path.resolve(strict=True)
    except OSError as error:
        raise LedgerValidationError(
            "Canonical ledger file is missing or unreadable"
        ) from error
    if resolved_ledger.parent != root or not resolved_ledger.is_file():
        raise LedgerValidationError("Canonical ledger path escaped checkout")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    if pinned_commit is not None and head != pinned_commit:
        raise LedgerValidationError("Canonical ledger checkout commit differs")
    _git(root, "ls-files", "--error-unmatch", "--", RELATIVE_PATH.as_posix())
    dirty = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=no",
        "--",
        RELATIVE_PATH.as_posix(),
    )
    if dirty.strip():
        raise LedgerValidationError("Canonical ledger file is dirty")
    try:
        working_bytes = resolved_ledger.read_bytes()
    except OSError as error:
        raise LedgerValidationError(
            "Canonical ledger file is unreadable"
        ) from error
    commit = pinned_commit or head
    committed_bytes = _git(
        root,
        "show",
        f"{commit}:{RELATIVE_PATH.as_posix()}",
    )
    if working_bytes != committed_bytes:
        raise LedgerValidationError(
            "Canonical ledger working file differs from pinned Git blob"
        )
    blob_oid = _git(
        root,
        "rev-parse",
        f"{commit}:{RELATIVE_PATH.as_posix()}",
    ).decode().strip()
    return {
        "head_commit": head,
        "relative_path": RELATIVE_PATH.as_posix(),
        "source_label": SOURCE_LABEL,
        "blob_oid": blob_oid,
        "source_sha256": _sha256(working_bytes),
        "source_bytes": working_bytes,
        "lines": working_bytes.decode("utf-8").splitlines(),
    }
