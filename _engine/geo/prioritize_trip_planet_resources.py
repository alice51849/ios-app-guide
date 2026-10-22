#!/usr/bin/env python3
"""Keep Trip Planet's free resources first in the generated tools catalog."""

from __future__ import annotations

import re
from pathlib import Path

from family_travel_dataset import write_text_if_changed


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
PRIORITY_HREFS = (
    "family-travel-mission-card-generator.html",
    "family-travel-observation-passport.html",
)
GRID_MARKER = '<section class="wrap grid">'


def prioritize(pages: Path = PAGES) -> bool:
    index = pages / "tools" / "index.html"
    text = index.read_text(encoding="utf-8")
    cards = []
    updated = text
    for href in PRIORITY_HREFS:
        pattern = re.compile(
            r'<article class="card third"><h2><a href="'
            + re.escape(href)
            + r'">.*?</article>',
            re.DOTALL,
        )
        match = pattern.search(updated)
        if not match:
            raise RuntimeError(f"tools/index.html is missing priority card: {href}")
        cards.append(match.group(0))
        updated, count = pattern.subn("", updated, count=1)
        if count != 1 or pattern.search(updated):
            raise RuntimeError(f"tools/index.html contains duplicate priority card: {href}")
    if GRID_MARKER not in updated:
        raise RuntimeError("tools/index.html is missing its main grid marker")
    updated = updated.replace(GRID_MARKER, GRID_MARKER + "".join(cards), 1)
    return write_text_if_changed(index, updated)


def main() -> None:
    changed = prioritize()
    print(f"Trip Planet tool priority -> {'updated' if changed else 'unchanged'}")


if __name__ == "__main__":
    main()
