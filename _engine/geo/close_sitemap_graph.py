#!/usr/bin/env python3
"""Close locale indexation and link hubs over one shared site inventory."""

from __future__ import annotations

import argparse
from pathlib import Path

import gen_link_hubs
import gen_locale_indexation
from site_tree_index import SiteTreeIndex


def close_graph(
    pages: Path,
    *,
    check: bool = False,
) -> dict[str, int]:
    pages = pages.resolve()
    tree = SiteTreeIndex.scan(pages)
    first = gen_locale_indexation.run_indexation(
        pages,
        check=check,
        tree=tree,
    )
    gen_locale_indexation.print_result(first)
    hubs = gen_link_hubs.run_link_hubs(
        pages,
        check=check,
        tree=tree,
    )

    if check:
        return {
            "html_files": len(tree.html_relatives()),
            "hub_changes": len(hubs["changed"]),
            "second_indexation": 0,
            "verification_changes": 0,
        }

    after_relatives = gen_locale_indexation.indexable_pages(
        pages,
        first.dead_locales,
        tree,
    )
    after_canonicals = gen_locale_indexation.indexable_canonical_map(
        pages,
        after_relatives,
        tree,
    )
    second_indexation = 0
    if (
        after_relatives != first.indexable_relatives
        or after_canonicals != first.canonical_by_relative
    ):
        second = gen_locale_indexation.run_indexation(
            pages,
            tree=tree,
            rewrite_html=False,
        )
        gen_locale_indexation.print_result(second)
        second_indexation = 1

    verification_changes: list[str] = []
    if hubs["changed"]:
        verification = gen_link_hubs.run_link_hubs(
            pages,
            check=True,
            tree=tree,
        )
        verification_changes = verification["changed"]
        if verification_changes:
            samples = ", ".join(verification_changes[:10])
            raise RuntimeError(
                "Link hubs did not converge after generation: "
                f"{len(verification_changes)} changes ({samples})"
            )
    return {
        "html_files": len(tree.html_relatives()),
        "hub_changes": len(hubs["changed"]),
        "second_indexation": second_indexation,
        "verification_changes": len(verification_changes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages-dir",
        type=Path,
        default=gen_locale_indexation.PAGES,
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stats = close_graph(args.pages_dir, check=args.check)
    print(
        "sitemap-graph-closure: "
        + " ".join(f"{key}={value}" for key, value in stats.items())
    )
    return int(args.check and stats["hub_changes"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
