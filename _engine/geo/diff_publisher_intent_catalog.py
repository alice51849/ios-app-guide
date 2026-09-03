#!/usr/bin/env python3
"""Prove a publisher-intent catalog rewrite touched copy only.

The delivery matrix matches catalog rows on identity -- `record_id`
(`<locale>:<app_key>:<slug>`), `app_store_id`, `canonical_app_store_url`,
`canonical_guide_url`, `verified_live`, `locale_count`, `record_count`.  If a
copy edit moves any of those, all 46 apps fall out of the mcp_catalog channel.

This tool diffs two catalog JSON files and fails unless

  * every identity field is byte-identical on every record,
  * the only record field that moved is one of COPY_FIELDS,
  * record ids are exactly the same set,
  * record_count / locale_count / app_count and the locale list are unchanged.

Usage:
    python3 diff_publisher_intent_catalog.py before.json after.json [--samples 8]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

# Fields the delivery matrix and the App Store links depend on.  None of these
# may move when only the wording of a page changed.
IDENTITY_FIELDS: tuple[str, ...] = (
    "record_id",
    "locale",
    "app_key",
    "app_name",
    "app_store_id",
    "publisher_query",
    "purchase_model",
    "one_time_option",
    "source_persona_query",
    "canonical_guide_url",
    "canonical_app_store_url",
    "app_store_url",
    "app_store_cta_label",
    "publisher_disclosure",
    "query_origin",
    "measured_search_volume",
    "is_ranking",
    "verified_live",
)

# The only fields a copy rewrite is allowed to change.
COPY_FIELDS: frozenset[str] = frozenset({"decision_context"})

# Header fields that must survive a copy rewrite unchanged.
HEADER_INVARIANTS: tuple[str, ...] = (
    "$schema",
    "identifier",
    "url",
    "license",
    "creator",
    "query_origin",
    "measured_search_volume",
    "is_ranking",
    "ordering",
    "app_count",
    "locale_count",
    "record_count",
    "locales",
)

EXPECTED_RECORDS = 2300
EXPECTED_LOCALES = 50


def _records(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["record_id"]): row for row in doc["records"]}


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []

    for field in HEADER_INVARIANTS:
        if before.get(field) != after.get(field):
            problems.append(
                f"header field moved: {field}: "
                f"{before.get(field)!r} -> {after.get(field)!r}"
            )

    if after.get("record_count") != EXPECTED_RECORDS:
        problems.append(f"record_count is {after.get('record_count')}")
    if after.get("locale_count") != EXPECTED_LOCALES:
        problems.append(f"locale_count is {after.get('locale_count')}")
    if len(after["records"]) != EXPECTED_RECORDS:
        problems.append(f"records array holds {len(after['records'])} rows")
    if len({row["locale"] for row in after["records"]}) != EXPECTED_LOCALES:
        problems.append("records do not cover 50 locales")

    old, new = _records(before), _records(after)
    if set(old) != set(new):
        missing = sorted(set(old) - set(new))[:5]
        added = sorted(set(new) - set(old))[:5]
        problems.append(f"record ids moved: missing={missing} added={added}")

    changed: list[dict[str, Any]] = []
    for record_id in sorted(set(old) & set(new)):
        a, b = old[record_id], new[record_id]
        if set(a) != set(b):
            problems.append(f"{record_id}: field set changed")
            continue
        moved = [f for f in a if a[f] != b[f]]
        for field in moved:
            if field in IDENTITY_FIELDS:
                problems.append(
                    f"{record_id}: IDENTITY field {field} moved: "
                    f"{a[field]!r} -> {b[field]!r}"
                )
            elif field not in COPY_FIELDS:
                problems.append(f"{record_id}: unexpected field {field} moved")
        if moved:
            changed.append(
                {
                    "record_id": record_id,
                    "locale": a["locale"],
                    "app_key": a["app_key"],
                    "fields": moved,
                    "old": {f: a[f] for f in moved},
                    "new": {f: b[f] for f in moved},
                }
            )

    return {
        "problems": problems,
        "changed": changed,
        "record_count": len(new),
        "locale_count": len({row["locale"] for row in after["records"]}),
        "app_count": len({row["app_key"] for row in after["records"]}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--samples", type=int, default=0,
                        help="Print one before/after pair every Nth locale.")
    parser.add_argument("--json", type=Path, help="Write the full report.")
    args = parser.parse_args()

    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    report = compare(before, after)

    print(f"records: {report['record_count']}  "
          f"locales: {report['locale_count']}  apps: {report['app_count']}")
    print(f"rows with copy changes: {len(report['changed'])}")
    locales_touched = {row["locale"] for row in report["changed"]}
    print(f"locales touched: {len(locales_touched)}")

    if args.samples:
        seen: list[str] = []
        for locale in sorted({row["locale"] for row in after["records"]}):
            if len(seen) % args.samples == 0:
                row = next(
                    (c for c in report["changed"] if c["locale"] == locale),
                    None,
                )
                if row is not None:
                    print(f"\n### {locale}  ({row['app_key']})")
                    print(f"  before: {row['old']['decision_context']}")
                    print(f"  after : {row['new']['decision_context']}")
            seen.append(locale)

    if args.json:
        args.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    if report["problems"]:
        print(f"\nFAIL: {len(report['problems'])} problem(s)")
        for line in report["problems"][:40]:
            print(f"  - {line}")
        return 1
    print("\nOK: identity preserved; only copy fields moved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
