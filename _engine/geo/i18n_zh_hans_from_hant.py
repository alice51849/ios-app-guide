#!/usr/bin/env python3
"""Derive the zh-Hans translation dictionary from the curated zh-Hant one.

zh-Hant is by far the best-covered Chinese dictionary in ``geo/i18n_trans``.
Simplified Chinese is not a different translation job -- it is the same
translation in a different orthography plus a small set of mainland-vs-Taiwan
term choices.  OpenCC's ``tw2sp`` config already does both (it converts the
characters *and* maps Taiwan idioms such as 軟體 -> 软件, 影片 -> 视频), so this
script runs it and then applies a short override table for the handful of
conversions where OpenCC picks a dated mainland word.

Existing zh-Hans entries are never overwritten -- hand-authored translations win.

    python3 i18n_zh_hans_from_hant.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"

# OpenCC tw2sp output -> preferred contemporary mainland wording
POST_FIXES = (
    ("缺省", "默认"),
    ("信息安全", "信息安全"),
    ("移动应用程序", "移动应用"),
    ("鼠标", "鼠标"),
)

BOPOMOFO = re.compile(r"[ㄅ-ㄯㆠ-ㆿ]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        from opencc import OpenCC
    except ImportError:
        print("opencc-python-reimplemented is required: pip install opencc-python-reimplemented")
        return 2

    cc = OpenCC("tw2sp")
    hant = json.loads((TRANS / "zh-Hant.json").read_text(encoding="utf-8"))
    hans_path = TRANS / "zh-Hans.json"
    hans = json.loads(hans_path.read_text(encoding="utf-8")) if hans_path.exists() else {}

    added = skipped_existing = skipped_bopomofo = 0
    for source, target in hant.items():
        if source in hans:
            skipped_existing += 1
            continue
        converted = cc.convert(target)
        for bad, good in POST_FIXES:
            converted = converted.replace(bad, good)
        if BOPOMOFO.search(converted):
            # Bopomofo pages are Taiwan-only content; never ship the symbols to zh-Hans
            skipped_bopomofo += 1
            continue
        hans[source] = converted
        added += 1

    print(
        f"zh-Hant entries {len(hant)} -> zh-Hans +{added} new "
        f"({skipped_existing} already present, {skipped_bopomofo} skipped for Bopomofo); "
        f"total {len(hans)}"
    )
    if not args.dry_run:
        hans_path.write_text(json.dumps(hans, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
