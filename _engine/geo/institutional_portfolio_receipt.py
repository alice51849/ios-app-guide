#!/usr/bin/env python3
"""Create a pinned receipt from the canonical app portfolio."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

import institutional_ledger


HERE = Path(__file__).resolve().parent
PAGES = HERE.parents[1]
CATALOG = Path("data") / "verified-ios-app-finder-catalog.json"
OUTPUT = Path("_engine") / "geo" / "institutional_portfolio_receipt.json"
ROW_RE = re.compile(
    r"^\|\s*(?P<number>\d{2})\s*\|\s*"
    r"(?P<name>[^|]+?)\s*\|\s*`(?P<directory>[^`]+)`\s*\|\s*"
    r"(?P<bundle>[A-Za-z0-9.-]+)\s*\|\s*"
    r"(?P<app_id>\d{9,12}|—)\s*\|"
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(encoded)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9+]+", normalized))


def _brand_matches(left: str, right: str) -> bool:
    first = _normalize(left)
    second = _normalize(right)
    return (
        first == second
        or first.startswith(f"{second} ")
        or second.startswith(f"{first} ")
    )


def _portfolio_rows(source: str) -> list[dict[str, str]]:
    rows = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = ROW_RE.match(line)
        if match is None:
            continue
        row = {key: value.strip() for key, value in match.groupdict().items()}
        row["source_line_number"] = str(line_number)
        row["source_line_sha256"] = _sha256(line.encode("utf-8"))
        rows.append(row)
    return rows


def build(
    pages: Path,
    standards_root: Path,
    captured_on: str,
) -> dict[str, Any]:
    captured = date.fromisoformat(captured_on)
    anchor = institutional_ledger.validate_checkout(
        standards_root,
        pinned_commit=None,
    )
    source_bytes = anchor["source_bytes"]
    rows = _portfolio_rows(source_bytes.decode("utf-8"))
    catalog = json.loads((pages / CATALOG).read_text(encoding="utf-8"))
    apps = catalog.get("apps")
    if not isinstance(apps, list) or len(apps) != 46:
        raise ValueError("Verified live catalog must contain exactly 46 apps")
    by_id = {
        row["app_id"]: row
        for row in rows
        if row["app_id"] != "—"
    }
    records = []
    for app in apps:
        app_id = str(app["app_store_id"])
        row = by_id.get(app_id)
        if row is None:
            candidates = [
                candidate
                for candidate in rows
                if candidate["app_id"] == "—"
                and _brand_matches(candidate["name"], str(app["name"]))
            ]
            if len(candidates) != 1:
                raise ValueError(
                    f"Portfolio row is ambiguous for {app['key']}: {len(candidates)}"
                )
            row = candidates[0]
        records.append(
            {
                "app_key": str(app["key"]),
                "verified_app_store_id": app_id,
                "portfolio_app_store_id": (
                    None if row["app_id"] == "—" else row["app_id"]
                ),
                "canonical_name": str(app["name"]),
                "portfolio_name": row["name"],
                "directory": row["directory"],
                "bundle_id": row["bundle"],
                "source_line_number": int(row["source_line_number"]),
                "source_line_sha256": row["source_line_sha256"],
            }
        )
    payload = {
        "schema_version": 1,
        "source_kind": "canonical_app_portfolio_receipt",
        "source_label": anchor["source_label"],
        "source_relative_path": anchor["relative_path"],
        "pinned_commit": anchor["head_commit"],
        "source_blob_oid": anchor["blob_oid"],
        "source_sha256": _sha256(source_bytes),
        "captured_on": captured_on,
        "expires_on": (captured + timedelta(days=7)).isoformat(),
        "record_count": len(records),
        "records": records,
        "content_digest": "",
    }
    normalized = dict(payload)
    normalized.pop("content_digest")
    payload["content_digest"] = f"sha256:{_canonical_digest(normalized)}"
    output = pages / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--standards-root", type=Path, required=True)
    parser.add_argument("--captured-on", required=True)
    args = parser.parse_args()
    payload = build(
        args.pages.resolve(),
        args.standards_root,
        args.captured_on,
    )
    print(
        "INSTITUTIONAL_PORTFOLIO_RECEIPT "
        f"apps={payload['record_count']} captured_on={payload['captured_on']}"
    )


if __name__ == "__main__":
    main()
