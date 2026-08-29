#!/usr/bin/env python3
"""Single authority for answer-page hreflang clusters and reciprocity."""
from __future__ import annotations

from pathlib import Path
import re

from official_locales import OFFICIAL_LOCALES


BASE_URL = "https://alice51849.github.io/ios-app-guide"
ENGLISH_HREFLANG = "en"
ALTERNATE_BLOCK_RE = re.compile(
    r'(?:<link rel="alternate" hreflang="[^"]+" href="[^"]+">\s*)+'
)
ALTERNATE_RE = re.compile(
    r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">'
)


class HreflangContractError(ValueError):
    """Raised when an answer page has no exact reciprocal hreflang block."""


def page_url(
    slug: str, locale: str | None = None, base_url: str = BASE_URL
) -> str:
    if locale:
        return f"{base_url}/{locale}/answers/{slug}.html"
    return f"{base_url}/answers/{slug}.html"


def existing_locales(
    pages_root: Path, slug: str, current_locale: str | None = None
) -> list[str]:
    return [
        locale
        for locale in OFFICIAL_LOCALES
        if locale == current_locale
        or (
            pages_root
            / locale
            / "answers"
            / f"{slug}.html"
        ).is_file()
    ]


def alternate_pairs(
    pages_root: Path,
    slug: str,
    current_locale: str | None = None,
    base_url: str = BASE_URL,
) -> list[tuple[str, str]]:
    english = pages_root / "answers" / f"{slug}.html"
    pairs: list[tuple[str, str]] = []
    if current_locale is None or english.is_file():
        pairs.append((ENGLISH_HREFLANG, page_url(slug, base_url=base_url)))
    for locale in existing_locales(pages_root, slug, current_locale):
        pairs.append(
            (locale, page_url(slug, locale, base_url=base_url))
        )
    default_url = (
        page_url(slug, base_url=base_url)
        if current_locale is None or english.is_file()
        else page_url(slug, current_locale, base_url=base_url)
    )
    pairs.append(("x-default", default_url))
    return pairs


def build_block(
    pages_root: Path,
    slug: str,
    current_locale: str | None = None,
    base_url: str = BASE_URL,
) -> str:
    return "\n".join(
        f'<link rel="alternate" hreflang="{locale}" href="{url}">'
        for locale, url in alternate_pairs(
            pages_root, slug, current_locale, base_url
        )
    )


def extract_pairs(document: str) -> list[tuple[str, str]]:
    matches = list(ALTERNATE_BLOCK_RE.finditer(document))
    if len(matches) != 1:
        raise HreflangContractError(
            "Answer page must contain exactly one contiguous hreflang block"
        )
    return ALTERNATE_RE.findall(matches[0].group(0))


def validate_document(
    document: str,
    pages_root: Path,
    slug: str,
    current_locale: str | None = None,
    base_url: str = BASE_URL,
) -> None:
    current = extract_pairs(document)
    expected = alternate_pairs(
        pages_root, slug, current_locale, base_url
    )
    if current != expected:
        raise HreflangContractError(
            f"Hreflang mismatch for {slug}: {current!r} != {expected!r}"
        )


def reconcile_document(
    document: str,
    pages_root: Path,
    slug: str,
    current_locale: str | None = None,
    base_url: str = BASE_URL,
) -> str:
    matches = list(ALTERNATE_BLOCK_RE.finditer(document))
    if len(matches) != 1:
        raise HreflangContractError(
            "Cannot reconcile a missing or split hreflang block"
        )
    expected = build_block(
        pages_root, slug, current_locale, base_url
    ) + "\n"
    match = matches[0]
    return document[: match.start()] + expected + document[match.end() :]


def reconcile_path(
    path: Path,
    pages_root: Path,
    slug: str,
    current_locale: str | None = None,
    base_url: str = BASE_URL,
) -> bool:
    if not path.is_file():
        return False
    source = path.read_text(encoding="utf-8")
    updated = reconcile_document(
        source, pages_root, slug, current_locale, base_url
    )
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def validate_cluster(
    pages_root: Path, slug: str, base_url: str = BASE_URL
) -> int:
    checked = 0
    english = pages_root / "answers" / f"{slug}.html"
    if not english.is_file():
        raise HreflangContractError(f"Missing English answer page: {slug}")
    validate_document(
        english.read_text(encoding="utf-8"),
        pages_root,
        slug,
        base_url=base_url,
    )
    checked += 1
    for locale in existing_locales(pages_root, slug):
        path = pages_root / locale / "answers" / f"{slug}.html"
        validate_document(
            path.read_text(encoding="utf-8"),
            pages_root,
            slug,
            locale,
            base_url,
        )
        checked += 1
    return checked
