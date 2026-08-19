#!/usr/bin/env python3
"""Rank what is still worth translating, so the next pass starts at the top.

Every English string on the answer pages is weighted by
``len(string) x pages_containing_it x locales_still_missing_it``: the amount of
visible English a translation would remove across the whole site.  The output is
the queue an agent should work down, highest payoff first.

    python3 i18n_worklist.py --langs "ja ko zh-Hant" --limit 300 \
        --json reports/i18n_worklist.json
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

_spec = importlib.util.spec_from_file_location("_aeo_i18n", ROOT / "aeo_answers_i18n.py")
_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_i18n)

DEFAULT_LANGS = ["ja", "ko", "zh-Hant", "zh-Hans", "de-DE", "fr-FR", "es-ES", "pt-BR"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", help="space/comma separated locales")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--json", help="write the ranked queue here")
    args = ap.parse_args()

    langs = DEFAULT_LANGS
    if args.langs:
        langs = [x for x in re.split(r"[\s,]+", args.langs) if x]

    counts: collections.Counter[str] = collections.Counter()
    for path in (PAGES / "answers").glob("*.html"):
        if path.name == "index.html":
            continue
        strings, _, _ = _i18n.extract_strings(path.read_text(encoding="utf-8"))
        counts.update(strings)

    dicts = {}
    for lang in langs:
        p = TRANS / f"{lang}.json"
        dicts[lang] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    rows = []
    for source, pages in counts.items():
        missing = [l for l in langs if source not in dicts[l]]
        if not missing:
            continue
        rows.append(
            {
                "weight": len(source) * pages * len(missing),
                "pages": pages,
                "missing_in": missing,
                "en": source,
            }
        )
    rows.sort(key=lambda r: -r["weight"])

    total = sum(r["weight"] for r in rows)
    head = rows[: args.limit]
    print(f"{len(rows)} strings still untranslated in at least one of {len(langs)} locales")
    print(
        f"top {len(head)} carry {sum(r['weight'] for r in head) / max(total, 1) * 100:.1f}% "
        f"of the remaining weight ({sum(len(r['en']) for r in head):,} English characters to write)"
    )
    for r in head[:20]:
        print(f"  [{r['pages']}x, {len(r['missing_in'])} locales] {r['en'][:110]}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(head, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
