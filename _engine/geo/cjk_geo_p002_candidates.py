#!/usr/bin/env python3
"""Generate only the twelve unpublished P0-02 owned-GEO candidates.

    python3 geo/cjk_geo_p002_candidates.py \
        --live-state geo/pages/.appstore_live_state.json \
        --output .local/cjk-p002-candidate

The exact47×10 inventory includes the other 458 cells unchanged. No social
card, receipt, existing generated page, metadata, CSS or other locale is written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_pages_i18n as pages
from cjk_geo_p002 import AUDIT_LOCALES, TARGET_CELLS

FIELDS = ("name", "subtitle", "description", "promotionalText", "keywords")


def live_keys(live_ids):
    ids = [str(value) for value in live_ids]
    by_id = {str(app_id): key for key, app_id in pages.APPSTORE.items() if key in pages.APPS}
    if len(ids) != 47 or len(set(ids)) != 47 or set(ids) - set(by_id):
        raise ValueError("P0-02 inventory requires the exact 47 cached live apps")
    return sorted(by_id[app_id] for app_id in ids)


def inventory(keys):
    if len(keys) != 47 or len(set(keys)) != 47:
        raise ValueError("P0-02 inventory must retain 47 unique apps")
    rows = []
    for key in sorted(keys):
        for locale in AUDIT_LOCALES:
            values = pages.external_localized_values(key, locale)
            rows.append({
                "app_key": key,
                "app_id": str(pages.APPSTORE[key]),
                "locale": locale,
                "purchase_model": pages.APPS[key]["purchase_model"],
                "repair_scope": "P0-02" if (key, locale) in TARGET_CELLS else "unchanged",
                "content": {field: values.get(field, "") for field in FIELDS},
                "publication_state": "unpublished_candidate" if (key, locale) in TARGET_CELLS else "not_regenerated",
                "social_receipt": None,
            })
    return rows


def generate(live_state, output):
    output = Path(output).resolve()
    protected = (Path(pages.PAGES).resolve(), Path(pages.DATA).resolve())
    if output.exists() or any(output == root or root in output.parents for root in protected):
        raise ValueError("Use a new candidate directory outside existing Guide pages and metadata")
    rows = inventory(live_keys(json.loads(Path(live_state).read_text())["live_ids"]))
    selected = [row for row in rows if row["repair_scope"] == "P0-02"]
    if {(row["app_key"], row["locale"]) for row in selected} != TARGET_CELLS:
        raise ValueError("P0-02 target set differs from the twelve reviewed cells")
    original_pages = pages.PAGES
    try:
        pages.PAGES = str(output)
        for row in selected:
            key = row["app_key"]
            pages.build_one(key, row["locale"], pages.all_locales_for(key))
    finally:
        pages.PAGES = original_pages
    (output / "content-inventory.json").write_text(
        json.dumps({"locales": AUDIT_LOCALES, "cells": rows}, ensure_ascii=False, indent=2) + "\n"
    )
    return {"inventory_cells": len(rows), "generated_pages": len(selected), "unchanged_cells": 458, "published": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.live_state, args.output)))


if __name__ == "__main__":
    main()
