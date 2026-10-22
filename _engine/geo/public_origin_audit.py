#!/usr/bin/env python3
"""Inventory every origin-host byte string in public artifacts, including root dotfiles."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from site_config import ORIGIN_HOST, public_reference_text


INTERNAL_DIRECTORIES = frozenset({".git", ".github", "_engine", "node_modules"})


def _public_files(root: Path):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Public artifact root must be a real directory")
    for directory, names, files in os.walk(root):
        names[:] = sorted(
            name for name in names if name not in INTERNAL_DIRECTORIES
        )
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(f"Public artifact cannot be a symlink: {relative}")
            yield path, relative


def audit_public_artifacts(root: Path, *, origin_host: str = ORIGIN_HOST) -> dict:
    needle = origin_host.lower().encode("ascii")
    checked = 0
    findings = []
    for path, relative in _public_files(root):
            body = path.read_bytes()
            checked += 1
            count = body.lower().count(needle)
            if count:
                findings.append({
                    "path": relative, "occurrences": count,
                    "sha256": hashlib.sha256(body).hexdigest(),
                })
    return {
        "schema_version": 1, "origin_host": origin_host,
        "files_checked": checked, "origin_occurrences": sum(r["occurrences"] for r in findings),
        "findings": sorted(findings, key=lambda row: row["path"]),
        "passed": not findings,
    }


def repair_public_artifacts(root: Path, *, origin_host: str = ORIGIN_HOST) -> dict:
    needle = origin_host.lower().encode("ascii")
    files_changed = 0
    occurrences_replaced = 0
    for path, relative in _public_files(root):
        body = path.read_bytes()
        occurrences = body.lower().count(needle)
        if not occurrences:
            continue
        try:
            source = body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(
                f"Origin reference appears in non-UTF-8 artifact: {relative}"
            ) from error
        updated = public_reference_text(source)
        if needle in updated.encode("utf-8").lower() or updated == source:
            raise ValueError(
                f"Origin reference is not a recognized owned URL: {relative}"
            )
        descriptor, pending_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.public-origin.",
        )
        pending = Path(pending_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(updated.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(pending, stat.S_IMODE(path.stat().st_mode))
            os.replace(pending, path)
        finally:
            if pending.exists():
                pending.unlink()
        files_changed += 1
        occurrences_replaced += occurrences
    return {
        "files_changed": files_changed,
        "origin_occurrences_replaced": occurrences_replaced,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    repair = repair_public_artifacts(args.site_root) if args.repair else None
    result = audit_public_artifacts(args.site_root)
    if repair is not None:
        result["repair"] = repair
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "findings"}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
