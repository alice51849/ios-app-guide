#!/usr/bin/env python3
"""Normalize public App Store links to clean or fully attributable URLs."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import urllib.parse

from app_store_storefronts import (
    normalize_app_store_campaign_url,
    validated_app_store_url,
)


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
TEXT_SUFFIXES = {
    ".csv",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".jsonld",
    ".md",
    ".mjs",
    ".svg",
    ".txt",
    ".xml",
}
EXCLUDED_PARTS = {".git", "_engine", "node_modules"}
APP_STORE_URL_RE = re.compile(
    r"https://apps\.apple\.com/"
    r"(?:(?P<country>[a-z]{2})/)?app/"
    r"(?:[-A-Za-z0-9._~%]+/)?id(?P<app_id>\d{9,12})"
    # "&(amp;)*" covers raw, HTML-escaped and doubly-escaped separators: an
    # Atom <content type="html"> block carries "&amp;amp;" between pt/ct/mt.
    # A query value may contain dots only *between* value characters: a
    # sentence period right after "mt=8" belongs to the prose, not the URL
    # (stamped links inside JSON-LD descriptions are followed by one).
    r"(?:\?(?:pt|ct|mt)=[A-Za-z0-9_/%+-]+(?:\.[A-Za-z0-9_/%+-]+)*"
    r"(?:&(?:amp;)*(?:pt|ct|mt)=[A-Za-z0-9_/%+-]+(?:\.[A-Za-z0-9_/%+-]+)*)*)?"
    # Refuse to stop inside a query value. With a bare "(?![?&])" the engine
    # backtracks into the middle of "pt=118326163", matches a truncated URL
    # and rewrites it — that is what shredded the decision feeds.
    r"(?![?&A-Za-z0-9_/%+-])",
    flags=re.IGNORECASE,
)
QUERY_APP_STORE_URL_RE = re.compile(
    r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/"
    r"(?:[-A-Za-z0-9._~%]+/)?id\d{9,12}"
    # Only characters that can legitimately belong to the query (or to an
    # invalid one we must reject) — an "everything but quotes" class swallows
    # whatever the surrounding document puts after the URL and then rejects a
    # perfectly valid campaign link: ")" ends a Markdown link target in every
    # generated README, and "," ends a CSV field in the published datasets.
    # ...and sentence punctuation right after the link (".", ";", ":", "!")
    # belongs to the prose: the last character must be one a query value can
    # legitimately end with.
    r"\?[-A-Za-z0-9._~%+=&;/:!*$#]*[-A-Za-z0-9_~%+=&/]",
    flags=re.IGNORECASE,
)


def _decode_ampersands(value: str) -> tuple[str, int]:
    """Undo every layer of "&amp;" escaping and report how many there were."""
    depth = 0
    while "&amp;" in value:
        value = value.replace("&amp;", "&")
        depth += 1
    return value, depth


def normalize_source(source: str) -> tuple[str, int]:
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        raw = match.group(0)
        decoded, escape_depth = _decode_ampersands(raw)
        parsed = urllib.parse.urlsplit(decoded)
        country = match.group("country")
        canonical_path = (
            f"/{country}/app/id{match.group('app_id')}"
            if country
            else f"/app/id{match.group('app_id')}"
        )
        canonical = urllib.parse.urlunsplit(
            parsed._replace(path=canonical_path, fragment="")
        )
        normalized = normalize_app_store_campaign_url(canonical)
        for _ in range(escape_depth):
            normalized = normalized.replace("&", "&amp;")
        changed += int(normalized != raw)
        return normalized

    return APP_STORE_URL_RE.sub(replace, source), changed


def assert_no_partial_campaigns(source: str, path: Path) -> None:
    for match in QUERY_APP_STORE_URL_RE.finditer(source):
        url, _ = _decode_ampersands(match.group(0))
        try:
            validated_app_store_url(url)
        except ValueError as error:
            raise ValueError(
                f"Partial or invalid App Store campaign URL in {path}: {url}"
            ) from error


def _public_text_files(pages: Path):
    for path in pages.rglob("*"):
        if (
            path.is_file()
            and path.suffix.lower() in TEXT_SUFFIXES
            and not EXCLUDED_PARTS.intersection(path.relative_to(pages).parts)
        ):
            yield path


def normalize_tree(pages: Path = PAGES) -> dict[str, int]:
    scanned = 0
    changed_files = 0
    changed_urls = 0
    for path in _public_text_files(pages):
        scanned += 1
        source = path.read_text(encoding="utf-8")
        updated, url_changes = normalize_source(source)
        assert_no_partial_campaigns(updated, path)
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
            changed_urls += url_changes
    return {
        "scanned": scanned,
        "changed_files": changed_files,
        "changed_urls": changed_urls,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    args = parser.parse_args()
    stats = normalize_tree(args.pages)
    print(
        "App Store links: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
