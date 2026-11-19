#!/usr/bin/env python3
"""Name every public page whose App Store link the Daily GEO run would refuse (read-only).

geo-daily.yml runs _engine/geo/normalize_app_store_links.py three times; one link it cannot
normalize (an over-long ct token, a partial campaign link) raises and the whole daily run dies
20 minutes in, at most four times a day, with the page named only at the end of a long log.
2026-11-18/19 a 33-character ct token (limit 30) pushed with one page stopped three runs.

This check walks the same files with the same engine functions, writes nothing, and prints one
``::error file=...::`` per refused page, so the push that brings such a link is red within minutes.
Not covered: the Google Play pass that normalize_app_store_links.main() runs afterwards
(android_play.inject_tree); only the App Store link rules are checked here.

    python3 .github/scripts/store_link_preflight.py --pages . --engine _engine/geo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MAX_REPORTED = 20


def refused_pages(pages: Path, engine: Path) -> tuple[int, list[tuple[str, str]]]:
    """(files scanned, [(path relative to pages, reason)]) using the engine's own rules."""
    sys.path.insert(0, str(engine))
    import normalize_app_store_links as normalizer  # the module geo-daily runs

    scanned = 0
    refused: list[tuple[str, str]] = []
    for path in sorted(normalizer._public_text_files(pages)):
        scanned += 1
        try:
            updated, _ = normalizer.normalize_source(path.read_text(encoding="utf-8"))
            normalizer.assert_no_partial_campaigns(updated, path)
        except (ValueError, OSError) as error:  # exactly what stops normalize_tree; nothing is written
            refused.append((path.relative_to(pages).as_posix(), " ".join(str(error).split())[:300]))
    return scanned, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", type=Path, default=Path("."))
    parser.add_argument("--engine", type=Path, default=Path("_engine/geo"))
    args = parser.parse_args(argv)
    scanned, refused = refused_pages(args.pages.resolve(), args.engine.resolve())
    for relative, reason in refused[:MAX_REPORTED]:
        print(f"::error file={relative}::Daily GEO content would stop on this page: {reason}")
    if len(refused) > MAX_REPORTED:
        print(f"::error::{len(refused) - MAX_REPORTED} more page(s) refused (not listed)")
    print(f"App Store link preflight: scanned={scanned}, refused={len(refused)}")
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
