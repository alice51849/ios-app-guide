#!/usr/bin/env python3
"""Small, dependency-free helpers for same-site HTML canonical URLs."""
from __future__ import annotations

from pathlib import Path
import re


LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
ATTRIBUTE_RE = re.compile(
    r"""([:\w-]+)\s*=\s*(["'])(.*?)\2""",
    re.IGNORECASE | re.DOTALL,
)


def declared_canonical(text: str) -> str | None:
    for tag in LINK_TAG_RE.findall(text):
        attributes = {
            name.lower(): value.strip()
            for name, _, value in ATTRIBUTE_RE.findall(tag)
        }
        if "canonical" in attributes.get("rel", "").lower().split():
            return attributes.get("href") or None
    return None


def same_site_canonical(text: str, site: str) -> str | None:
    canonical = declared_canonical(text)
    base = site.rstrip("/")
    if canonical == base:
        return f"{base}/"
    if canonical and canonical.startswith(f"{base}/"):
        return canonical
    return None


def content_relative(url: str, site: str) -> str | None:
    prefix = f"{site.rstrip('/')}/"
    if not url.startswith(prefix):
        return None
    relative = url[len(prefix) :]
    if not relative or relative.endswith("/"):
        return f"{relative}index.html"
    return relative


def canonical_url_for_html(
    path: Path,
    fallback: str,
    site: str,
) -> str:
    try:
        with path.open(encoding="utf-8", errors="ignore") as page:
            head = page.read(262144)
    except OSError:
        return fallback
    return same_site_canonical(head, site) or fallback
