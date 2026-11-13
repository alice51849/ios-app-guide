#!/usr/bin/env python3
"""Refuse a deploy when a restricted-copy app's own pages break its copy rules (Kumo, owner 2026-11-13).

Kumo touches health and medicines: its pages name no drug brand, promise no effect or weight result, give no
medical or dosing advice, show no price and offer no free trial (00_GrowthEngine ops/aso/kumo/README.md). The
word rules live in ONE place, the outbound-text core (ios-app-guide .github/scripts/download_links.py, mirrored
by 00_GrowthEngine lib/outbound_links.py); this gate reads the rendered tree and checks the visible text of
every page that belongs to such an app (<locale>/kumo.html, apps/kumo/...). Shared hub pages that list many
apps are not this app's copy and are not checked here.

    python3 _engine/geo/restricted_copy_pages.py --site-root .     # exit 1 + ::error:: lines on a hit
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP_DIRS = {"_engine", ".git", ".github", "node_modules"}
_INVISIBLE = re.compile(r"(?is)<(script|style|noscript|template)\b[^>]*>.*?</\1\s*>|<!--.*?-->")
_TAG = re.compile(r"<[^>]+>")


def load_core(site_root: Path):
    """The outbound-text core: the Guide's download_links.py, else 00_GrowthEngine's lib/outbound_links.py."""
    for path in (site_root / ".github" / "scripts" / "download_links.py",
                 HERE.parent / ".github" / "scripts" / "download_links.py",
                 HERE.parent.parent / ".github" / "scripts" / "download_links.py",
                 HERE.parent / "lib" / "outbound_links.py"):
        if path.is_file():
            spec = importlib.util.spec_from_file_location("restricted_copy_core", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "restricted_copy_hits"):
                return mod
    raise SystemExit("::error::restricted_copy_pages: the outbound-text core (restricted_copy_hits) was not found")


def visible_text(page: str) -> str:
    return html.unescape(_TAG.sub(" ", _INVISIBLE.sub(" ", page)))


def owned_pages(root: Path, keys):
    for path in sorted(root.rglob("*.html")):
        parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        if path.stem in keys or any(part in keys for part in parts[:-1]):
            yield path


def audit(root: Path, core=None):
    """[(relative path, category, matched text)] of every hit on the restricted-copy apps' own pages."""
    core = core or load_core(root)
    keys = set(core.RESTRICTED_COPY_APPS.values())
    out = []
    for path in owned_pages(root, keys):
        text = visible_text(path.read_text(encoding="utf-8", errors="replace"))
        out += [(str(path.relative_to(root)), c, hit) for c, hit in core.restricted_copy_hits(text)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site-root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.site_root).resolve()
    hits = audit(root)
    for rel, category, hit in hits:
        print(f"::error file={rel}::restricted copy ({category}): {hit[:60]!r}")
    if hits:
        print(f"restricted_copy_pages: {len(hits)} hit(s); fix the page copy, nothing is deployed", file=sys.stderr)
        return 1
    print("restricted_copy_pages: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
