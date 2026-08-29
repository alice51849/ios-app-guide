#!/usr/bin/env python3
"""Reconcile English answer pages with the shared hreflang authority."""
from __future__ import annotations

import argparse
from pathlib import Path

import aeo_answers_i18n as I
import answer_hreflang


ROOT = I.ROOT
ANSWERS = ROOT / "answers"


def existing_locales(
    slug: str, root: Path = ROOT
) -> list[str]:
    return answer_hreflang.existing_locales(root, slug)


def build_block(
    slug: str,
    locales: list[str] | None = None,
    root: Path = ROOT,
) -> str:
    expected = answer_hreflang.build_block(root, slug)
    if locales is not None:
        actual = answer_hreflang.existing_locales(root, slug)
        if locales != actual:
            raise answer_hreflang.HreflangContractError(
                f"Caller locale inventory is stale: {locales!r} != {actual!r}"
            )
    return expected


def run(
    root: Path = ROOT,
    *,
    dry_run: bool = False,
    slugs: set[str] | None = None,
) -> dict[str, int]:
    answers = root / "answers"
    changed = already_ok = no_locale = 0
    for path in sorted(answers.glob("*.html")):
        slug = path.stem
        if slug == "index" or (slugs is not None and slug not in slugs):
            continue
        locales = answer_hreflang.existing_locales(root, slug)
        if not locales:
            no_locale += 1
            continue
        source = path.read_text(encoding="utf-8")
        expected = answer_hreflang.build_block(root, slug) + "\n"
        current = answer_hreflang.ALTERNATE_BLOCK_RE.search(source)
        if current is None:
            raise answer_hreflang.HreflangContractError(
                f"Missing hreflang block: {path}"
            )
        if current.group(0) == expected:
            already_ok += 1
            continue
        if not dry_run:
            path.write_text(
                answer_hreflang.reconcile_document(
                    source, root, slug
                ),
                encoding="utf-8",
            )
        changed += 1
    result = {
        "changed": changed,
        "already_ok": already_ok,
        "no_locale": no_locale,
    }
    print(
        f"{'DRY ' if dry_run else ''}"
        f"changed={changed} already_ok={already_ok} no_locale={no_locale}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--slug",
        action="append",
        default=[],
        help="Limit reconciliation to one answer slug; repeatable.",
    )
    args = parser.parse_args()
    run(
        dry_run=args.dry_run,
        slugs=set(args.slug) if args.slug else None,
    )


if __name__ == "__main__":
    main()
