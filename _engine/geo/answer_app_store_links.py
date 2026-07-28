#!/usr/bin/env python3
"""Parse direct App Store links from Answer page anchors."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.parse


APP_STORE_URL_RE = re.compile(
    r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/"
    r"(?:[-A-Za-z0-9._~%]+/)?id(?P<id>\d{9,12})"
    r"/?(?=$|[?#])",
    flags=re.IGNORECASE,
)
APP_STORE_PATH_RE = re.compile(
    r"/(?:(?P<country>[a-z]{2})/)?app/"
    r"(?:[-A-Za-z0-9._~%]+/)?id(?P<id>\d{9,12})/?",
    flags=re.IGNORECASE,
)
MANAGED_APP_STORE_BLOCK_RE = re.compile(
    r"\s*<!-- (?P<name>"
    r"app-decision-card|app-store-share|app-store-qr|"
    r"mobile-store-cta|smart-app-banner"
    r"):start -->.*?<!-- (?P=name):end -->\s*",
    flags=re.DOTALL,
)
MOBILE_APP_IDENTITY_BLOCK_RE = re.compile(
    r'\s*<script\b(?=[^>]*\bdata-mobile-app-(?:identity|webpage)="1")'
    r"[^>]*>.*?</script>\s*",
    flags=re.IGNORECASE | re.DOTALL,
)


class _DirectAppStoreLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.app_store_ids: set[str] = set()
        self.duplicate_href = False
        self.invalid_app_store_href: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "a":
            return
        hrefs = [
            value for key, value in attrs if key.casefold() == "href"
        ]
        if len(hrefs) > 1:
            self.duplicate_href = True
            return
        if not hrefs or hrefs[0] is None:
            return
        href = hrefs[0]
        if not href.casefold().startswith("https://apps.apple.com/"):
            return
        try:
            canonical = canonical_app_store_url(href)
        except ValueError:
            self.invalid_app_store_href = href
            return
        match = APP_STORE_URL_RE.match(canonical)
        if match:
            self.app_store_ids.add(match.group("id"))


def direct_app_store_ids(
    source: str,
    path: Path | str | None = None,
) -> set[str]:
    parser = _DirectAppStoreLinkParser()
    parser.feed(source)
    if parser.duplicate_href:
        label = f"{path} " if path is not None else ""
        raise ValueError(f"{label}has duplicate anchor href attributes")
    if getattr(parser, "invalid_app_store_href", None):
        label = f"{path} " if path is not None else ""
        raise ValueError(
            f"{label}has invalid direct App Store URL: "
            f"{parser.invalid_app_store_href}"
        )
    return parser.app_store_ids


def unmanaged_app_store_source(source: str) -> str:
    source = MANAGED_APP_STORE_BLOCK_RE.sub("\n", source)
    return MOBILE_APP_IDENTITY_BLOCK_RE.sub("\n", source)


def canonical_app_store_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    for raw_segment in parsed.path.split("/"):
        decoded_segment = urllib.parse.unquote(raw_segment)
        if (
            decoded_segment in {".", ".."}
            or "/" in decoded_segment
            or "\\" in decoded_segment
        ):
            raise ValueError(f"Invalid direct App Store URL: {value}")
    path = APP_STORE_PATH_RE.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc.casefold() != "apps.apple.com"
        or path is None
    ):
        raise ValueError(f"Invalid direct App Store URL: {value}")
    country = path.group("country")
    canonical_path = (
        f"/{country.casefold()}/app/id{path.group('id')}"
        if country
        else f"/app/id{path.group('id')}"
    )
    return urllib.parse.urlunsplit(
        ("https", "apps.apple.com", canonical_path, parsed.query, "")
    )
