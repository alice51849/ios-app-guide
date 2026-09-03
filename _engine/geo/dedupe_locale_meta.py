#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""De-index localized pages that are still carrying English metadata.

Background (2026-08-08)
-----------------------
59,567 pages produced 18 downloads and US$0.00 over 30 days. Sampling found
~2/3 of localized pages shipping a <title> and meta description byte-identical
to the English original. That is the textbook cause of "Crawled - currently not
indexed": we are asking Google to index many near-identical copies of the same
document under different paths, so it indexes none of them and the English
original loses authority too.

The honest fix is to translate them. Until translation capacity exists, the
correct action is to stop competing with ourselves: a page that is not actually
localized should not be a separate indexable URL. This script marks those pages
`noindex,follow` (so link equity still flows) and drops them from the sitemaps,
concentrating crawl budget and authority on the pages that are genuinely
different.

Reversal is by re-rendering: aeo_answers_i18n.py rewrites these files wholesale
with `index,follow` once a real translation exists. This script never flips an
existing noindex back on — that flag may belong to another process.

    python dedupe_locale_meta.py --report          # measure only
    python dedupe_locale_meta.py --apply           # apply noindex + sitemaps
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from site_config import PUBLIC_SITE  # noqa: E402

HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
SITE = PUBLIC_SITE

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', re.S)
ROBOTS_RE = re.compile(r'<meta\s+name="robots"\s+content="([^"]*)"\s*/?>', re.I)

# Top-level content directories hold the English originals.
EN_DIRS = [
    "answers", "best-for", "workflow", "vs", "seasonal", "reviews", "tools",
    "alternatives", "hubs", "guides", "stories", "persona", "tutorials",
    "problems", "pay-once", "no-account", "family", "gifting", "switching",
    "choose",
]
# A locale directory is any top-level dir that is not an English content dir
# and is not infrastructure.
NON_LOCALE = set(EN_DIRS) | {
    ".git", ".github", "_engine", "assets", "data", "visuals", "apps",
    "topic-hubs", "review-hubs", "img", "css", "js",
}


def meta_of(path: Path) -> tuple[str | None, str | None, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None, ""
    t = TITLE_RE.search(text)
    d = DESC_RE.search(text)
    return (t.group(1).strip() if t else None,
            d.group(1).strip() if d else None,
            text)


def english_index() -> dict[str, tuple[str | None, str | None]]:
    idx: dict[str, tuple[str | None, str | None]] = {}
    for sub in EN_DIRS:
        d = PAGES / sub
        if not d.is_dir():
            continue
        for p in d.rglob("*.html"):
            t, ds, _ = meta_of(p)
            idx[str(p.relative_to(PAGES))] = (t, ds)
    return idx


def locale_dirs() -> list[str]:
    out = []
    for entry in sorted(os.listdir(PAGES)):
        p = PAGES / entry
        if not p.is_dir() or entry in NON_LOCALE or entry.startswith("."):
            continue
        out.append(entry)
    return out


def set_robots(text: str, value: str) -> str:
    if ROBOTS_RE.search(text):
        return ROBOTS_RE.sub(f'<meta name="robots" content="{value}">', text, count=1)
    return text.replace("<head>", f'<head><meta name="robots" content="{value}">', 1)


def scan(apply: bool) -> dict:
    en = english_index()
    locales = locale_dirs()
    stats = {"locales": {}, "total": 0, "dupes": 0, "changed": 0, "restored": 0}
    noindex_urls: set[str] = set()
    for loc in locales:
        root = PAGES / loc
        n = dup = changed = restored = 0
        for p in root.rglob("*.html"):
            rel = str(p.relative_to(root))
            t, d, text = meta_of(p)
            if t is None:
                continue
            n += 1
            et, ed = en.get(rel, (None, None))
            is_dupe = bool((et and t == et) or (ed and d == ed))
            if is_dupe:
                dup += 1
                url = f"{SITE}/{loc}/{rel.replace(os.sep, '/')}"
                noindex_urls.add(url)
            if not apply:
                continue
            current = ROBOTS_RE.search(text)
            current_val = (current.group(1) if current else "").lower()
            if is_dupe and "noindex" not in current_val:
                p.write_text(set_robots(text, "noindex,follow"), encoding="utf-8")
                changed += 1
            # Deliberately one-way. A page already carrying noindex was set that
            # way by another process (thin-content pruning, structured-data
            # cleanup); flipping it back would silently undo their decision.
            # Re-indexing happens when the i18n renderer rewrites the page with
            # a real translation, which emits index,follow itself.
        stats["locales"][loc] = {
            "pages": n, "duplicates": dup,
            "rate": round(100 * dup / n, 1) if n else 0.0,
            "noindexed": changed, "reindexed": restored,
        }
        stats["total"] += n
        stats["dupes"] += dup
        stats["changed"] += changed
        stats["restored"] += restored
    stats["duplicate_rate"] = (
        round(100 * stats["dupes"] / stats["total"], 1) if stats["total"] else 0.0
    )
    if apply:
        stats["sitemap_urls_removed"] = prune_sitemaps(noindex_urls)
    return stats


def prune_sitemaps(noindex_urls: set[str]) -> int:
    """Drop noindexed URLs from every sitemap. Asking Google to crawl a
    noindex URL wastes the crawl budget we are trying to reclaim."""
    removed = 0
    for sm in PAGES.glob("sitemap*.xml"):
        try:
            text = sm.read_text(encoding="utf-8")
        except OSError:
            continue
        if "<url>" not in text:
            continue  # sitemap index, not a URL set
        kept, dropped = [], 0
        for block in re.findall(r"<url>.*?</url>", text, re.S):
            loc = re.search(r"<loc>(.*?)</loc>", block, re.S)
            if loc and loc.group(1).strip() in noindex_urls:
                dropped += 1
                continue
            kept.append(block)
        if not dropped:
            continue
        body = "\n".join(kept)
        out = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}\n</urlset>\n"
        )
        sm.write_text(out, encoding="utf-8")
        removed += dropped
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    stats = scan(apply=args.apply)
    top = sorted(
        stats["locales"].items(), key=lambda kv: -kv[1]["duplicates"]
    )[:15]
    for loc, s in top:
        print(f"{loc:10} pages={s['pages']:5} dupes={s['duplicates']:5} "
              f"({s['rate']}%) noindexed={s['noindexed']}")
    print(f"TOTAL pages={stats['total']} duplicates={stats['dupes']} "
          f"({stats['duplicate_rate']}%) noindexed={stats['changed']} "
          f"reindexed={stats['restored']}")
    if "sitemap_urls_removed" in stats:
        print(f"sitemap URLs removed: {stats['sitemap_urls_removed']}")
    if args.json_out:
        args.json_out.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
