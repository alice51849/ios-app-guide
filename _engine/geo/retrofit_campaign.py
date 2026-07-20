#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove legacy partial App Store campaign parameters from GEO pages."""
import os
import sys

from normalize_app_store_links import (
    assert_no_partial_campaigns,
    normalize_source,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")


def main():
    dry = "--write" not in sys.argv
    changed = 0
    scanned = 0
    for root, _dirs, files in os.walk(PAGES):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, PAGES)
            scanned += 1
            with open(path, encoding="utf-8") as f:
                source = f.read()
            updated, _ = normalize_source(source)
            assert_no_partial_campaigns(updated, rel)
            if updated != source:
                changed += 1
                if not dry:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(updated)
    mode = "DRY-RUN" if dry else "WRITE"
    print(f"[{mode}] scanned={scanned} changed={changed}")


if __name__ == "__main__":
    main()
