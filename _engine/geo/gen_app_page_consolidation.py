#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collapse near-duplicate per-app GEO pages into one indexable page per locale.

Why (ShotInbox, 2026-10-14)
---------------------------
ShotInbox's answers pages are generated from a handful of category phrases
(sort / organize / clean up screenshots, screenshot organizer) crossed with
several templates ("best X", "X for iphone", "X for iphone free", "how to
choose a X").  Their text is 91-95% identical inside a locale, which reads as
scaled content to search engines and splits the signal across many URLs.  The
head-to-head "vs" comparison pages add little and are switched off as well.

What this does
--------------
Driven by ``app_page_consolidation_policy.json``.  For each app and every
locale (plus the English originals at the site root):

* answers pages that link only to that app's App Store id, other than the
  ``keep`` slugs, get ``<meta name="robots" content="noindex,follow">`` and are
  dropped from the sitemaps;
* pages matching ``noindex_globs`` (for example the ``vs`` comparison pages)
  get the same treatment.

Runs as a pipeline step after ``dedupe_locale_meta.py`` (same one-way noindex
semantics: it never flips an existing noindex back, and a re-render by the page
generators restores the page, so it must run on every publish).

    python gen_app_page_consolidation.py --check    # report only
    python gen_app_page_consolidation.py            # apply
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dedupe_locale_meta import PAGES, SITE, ROBOTS_RE, prune_sitemaps, set_robots  # noqa: E402

POLICY_PATH = HERE / "app_page_consolidation_policy.json"
STORE_ID_RE = re.compile(r"apps\.apple\.com/(?:[a-z]{2}(?:-[a-z]{2,4})?/)?app/(?:[^/\"'?#\s]*/)?id(\d+)", re.I)


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["apps"]


def site_roots(pages: Path) -> list[tuple[str, Path]]:
    """(url prefix, directory) for the English root and every locale directory."""
    roots = [("", pages)]
    for entry in sorted(os.listdir(pages)):
        p = pages / entry
        if p.is_dir() and not entry.startswith((".", "_")) and (
            (p / "answers").is_dir() or (p / "alternatives").is_dir()
        ):
            roots.append((entry, p))
    return roots


def should_noindex(rel: str, text: str, cfg: dict) -> bool:
    section, _, name = rel.partition("/")
    slug = name[:-5] if name.endswith(".html") else name
    for pattern in cfg.get("noindex_globs", []):
        if fnmatch.fnmatch(rel, pattern):
            return True
    if section == "answers" and slug not in cfg.get("keep", []):
        ids = set(STORE_ID_RE.findall(text))
        return ids == {cfg["store_id"]}
    return False


def run(pages: Path, policy: dict, apply: bool) -> dict:
    noindex_urls: set[str] = set()
    stats = {"apps": {}, "changed": 0}
    for app, cfg in policy.items():
        found = changed = 0
        for prefix, root in site_roots(pages):
            for section in ("answers", "alternatives"):
                d = root / section
                if not d.is_dir():
                    continue
                for p in d.glob("*.html"):
                    rel = f"{section}/{p.name}"
                    try:
                        text = p.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    if not should_noindex(rel, text, cfg):
                        continue
                    found += 1
                    url_path = f"{prefix}/{rel}" if prefix else rel
                    noindex_urls.add(f"{SITE}/{url_path}")
                    cur = ROBOTS_RE.search(text)
                    if cur and "noindex" in cur.group(1).lower():
                        continue
                    changed += 1
                    if apply:
                        p.write_text(set_robots(text, "noindex,follow"), encoding="utf-8")
        stats["apps"][app] = {"matched": found, "newly_noindexed": changed}
        stats["changed"] += changed
    if apply and noindex_urls:
        stats["sitemap_urls_removed"] = prune_sitemaps(noindex_urls)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--policy", type=Path, default=POLICY_PATH)
    args = ap.parse_args()
    stats = run(PAGES, load_policy(args.policy), apply=not args.check)
    for app, s in stats["apps"].items():
        print(f"{app}: matched={s['matched']} newly_noindexed={s['newly_noindexed']}")
    if "sitemap_urls_removed" in stats:
        print(f"sitemap URLs removed: {stats['sitemap_urls_removed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
