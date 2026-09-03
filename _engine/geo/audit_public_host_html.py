#!/usr/bin/env python3
"""Fail when rendered Guide HTML still identifies itself on the Pages origin.

The owned public host is the only identity a page may claim in its
canonical, hreflang alternates, or microformat URLs.  Generators take the
host from site_config, but a page written by an older run (or edited by
hand) keeps whatever host it was rendered with, and nothing else in the
deploy path reads the rendered tree — this gate does.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from site_config import ORIGIN_SITE, PUBLIC_SITE  # noqa: E402

IDENTITY_PATTERNS = (
    re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I),
    re.compile(r'<link\s+rel="alternate"\s+hreflang="[^"]*"\s+href="([^"]+)"', re.I),
    re.compile(r'<data\s+class="u-url[^"]*"\s+value="([^"]+)"', re.I),
    re.compile(r'<meta\s+property="og:url"\s+content="([^"]+)"', re.I),
)
SKIP_DIRS = {"_engine", ".git", ".github", "node_modules"}


def iter_html(root: Path):
    for path in root.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def origin_identities(text: str, origin: str) -> list[str]:
    found = []
    for pattern in IDENTITY_PATTERNS:
        for url in pattern.findall(text):
            if url.startswith(origin + "/") or url == origin:
                found.append(url)
    return found


def audit(root: Path, origin: str = ORIGIN_SITE) -> dict[str, list[str]]:
    offenders: dict[str, list[str]] = {}
    for path in iter_html(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = origin_identities(text, origin)
        if hits:
            offenders[path.relative_to(root).as_posix()] = hits
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, default=Path(os.environ.get("GEO_PAGES", HERE / "pages")))
    parser.add_argument("--limit", type=int, default=20, help="offenders to print")
    args = parser.parse_args()
    if PUBLIC_SITE == ORIGIN_SITE:
        print("public host equals origin host; nothing to audit")
        return 0
    offenders = audit(args.site_root.resolve())
    scanned = sum(1 for _ in iter_html(args.site_root.resolve()))
    print(f"public-host-html: scanned={scanned} offenders={len(offenders)} origin={ORIGIN_SITE}")
    for relative, hits in sorted(offenders.items())[: args.limit]:
        print(f"  {relative}: {hits[0]}")
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
