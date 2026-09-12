#!/usr/bin/env python3
"""Build a cached-live CEE content inventory and unpublished guide candidates.

Example (all paths are explicit, with no ASC or publishing calls):
    python3 geo/cee_content_candidates.py \
        --live-state geo/pages/.appstore_live_state.json \
        --output .local/cee/inventory.json --pages-output .local/cee/pages

The normal build_pages_i18n generator renders candidate HTML. Existing Guide
pages, shared layout, social queues, historical posts and receipts are not
written. The previews are source-review material, not publish-ready posts.
Dev.to remains N/A because none of these locales is en-US.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_pages_i18n as pages
from cee_locale_copy import CEE_LOCALES
from hebrew_bidi import social_preview

FIELDS = ("name", "subtitle", "description", "promotionalText", "keywords")


def keys_from_live_ids(live_ids: list[str]) -> list[str]:
    ids = [str(value) for value in live_ids]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Cached live IDs must be nonempty and unique")
    by_id = {
        str(pages.APPSTORE[key]): key
        for key in pages.APPS
        if key in pages.APPSTORE
    }
    unknown = set(ids) - set(by_id)
    if unknown:
        raise ValueError(f"Unknown cached live IDs: {sorted(unknown)}")
    return sorted(by_id[app_id] for app_id in ids)


def build_inventory(keys: list[str]) -> list[dict]:
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("Candidate apps must be nonempty and unique")
    records = []
    for key in sorted(keys):
        source = pages.load_app_locales(key)
        for locale in CEE_LOCALES:
            values = pages.external_localized_values(key, locale, source)
            records.append({
                "app_key": key,
                "app_id": str(pages.APPSTORE[key]),
                "locale": locale,
                "purchase_model": pages.APPS[key]["purchase_model"],
                **{field: values[field] for field in FIELDS},
                "social_preview": social_preview(
                    values["name"], values["subtitle"],
                    values["description"], locale,
                ),
                "publication_state": "unpublished_candidate",
                "social_receipt": None,
                "devto": "N/A (non-en-US)",
            })
    return records


def _candidate_path(path: Path) -> Path:
    resolved = path.resolve()
    for protected in (Path(pages.DATA).resolve(), Path(pages.PAGES).resolve()):
        if resolved == protected or protected in resolved.parents:
            raise ValueError("Candidates must not overwrite metadata or Guide pages")
    return path


def write_candidates(records: list[dict], destination: Path) -> int:
    destination = _candidate_path(destination)
    cells = set()
    for record in records:
        key, locale = record["app_key"], record["locale"]
        if (
            locale not in CEE_LOCALES
            or key not in pages.APPS
            or str(record["app_id"]) != str(pages.APPSTORE.get(key))
            or (key, locale) in cells
        ):
            raise ValueError("Candidates require unique CEE cells with exact App identity")
        cells.add((key, locale))
    keys = {key for key, _ in cells}
    if not cells or cells != {(key, locale) for key in keys for locale in CEE_LOCALES}:
        raise ValueError("Every candidate app must retain all ten CEE locales")
    original = pages.PAGES
    try:
        pages.PAGES = str(destination)
        for record in records:
            key = record["app_key"]
            pages.build_one(key, record["locale"], pages.all_locales_for(key))
    finally:
        pages.PAGES = original
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pages-output", type=Path)
    args = parser.parse_args()
    output = _candidate_path(args.output)
    live = json.loads(args.live_state.read_text(encoding="utf-8"))
    records = build_inventory(keys_from_live_ids(live["live_ids"]))
    if args.pages_output:
        write_candidates(records, args.pages_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"locales": CEE_LOCALES, "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "apps": len({row["app_key"] for row in records}),
        "locales": len(CEE_LOCALES),
        "cells": len(records),
        "published": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
