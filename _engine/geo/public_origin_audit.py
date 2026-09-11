#!/usr/bin/env python3
"""Inventory every origin-host byte string in public artifacts, including root dotfiles."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from site_config import ORIGIN_HOST


INTERNAL_DIRECTORIES = frozenset({".git", ".github", "_engine", "node_modules"})


def audit_public_artifacts(root: Path, *, origin_host: str = ORIGIN_HOST) -> dict:
    needle = origin_host.lower().encode("ascii")
    checked = 0
    findings = []
    for directory, names, files in os.walk(root):
        names[:] = [name for name in names if name not in INTERNAL_DIRECTORIES]
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(f"Public artifact cannot be a symlink: {relative}")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = audit_public_artifacts(args.site_root)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "findings"}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
