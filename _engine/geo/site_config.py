#!/usr/bin/env python3
"""Single source of truth for the Guide's public host and its Pages origin.

Two different hosts serve the same bytes and they must never be confused:

``PUBLIC_SITE``
    The host every public identifier names: ``<link rel=canonical>``, ``og:url``,
    hreflang alternates, sitemaps, robots ``Sitemap:`` lines, feeds, ``llms.txt``,
    linksets, JSON-LD ``url``/``@id``, the static API catalogs, the MCP catalog and
    every IndexNow submission. Owned apex-adjacent hosting is what answer engines
    and LLM crawlers accept, so this is the only host that may appear in content.

``ORIGIN_SITE``
    The GitHub Pages deployment the public host proxies. Deployment verification
    only -- reading ``.well-known/deployment.json``, confirming a commit reached
    the CDN. It must never leak into a canonical, a sitemap or a submission.

Override either with ``GEO_PUBLIC_SITE`` / ``GEO_ORIGIN_SITE``. Generators that
already honour the older ``GEO_SITE`` variable keep doing so; ``PUBLIC_SITE`` is
their default, so the workflows can pin the host in one place.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlsplit, urlunsplit

DEFAULT_PUBLIC_SITE = "https://open.cait518.cc/ios-app-guide"
DEFAULT_ORIGIN_SITE = "https://alice51849.github.io/ios-app-guide"


def _normalise(value: str, fallback: str) -> str:
    cleaned = (value or "").strip().rstrip("/")
    if not cleaned:
        return fallback
    parsed = urlsplit(cleaned)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"Site override must be an https URL: {value!r}")
    return cleaned


PUBLIC_SITE = _normalise(os.environ.get("GEO_PUBLIC_SITE", ""), DEFAULT_PUBLIC_SITE)
PUBLIC_HOST = urlsplit(PUBLIC_SITE).netloc
PUBLIC_ROOT = f"https://{PUBLIC_HOST}"

ORIGIN_SITE = _normalise(os.environ.get("GEO_ORIGIN_SITE", ""), DEFAULT_ORIGIN_SITE)
ORIGIN_HOST = urlsplit(ORIGIN_SITE).netloc
ORIGIN_ROOT = f"https://{ORIGIN_HOST}"


def public_url(path: str = "") -> str:
    """Absolute public URL for a site-relative ``path``."""
    return f"{PUBLIC_SITE}/{path.lstrip('/')}" if path else PUBLIC_SITE


def public_reference_url(value: str) -> str:
    """Render an owned public link without altering external evidence or its path."""
    parsed = urlsplit(value)
    if parsed.hostname != urlsplit(ORIGIN_ROOT).hostname:
        return value
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("An owned public reference must be an unambiguous HTTPS URL")
    origin_path = urlsplit(ORIGIN_SITE).path.rstrip("/")
    if parsed.path == origin_path or parsed.path.startswith(origin_path + "/"):
        target = urlsplit(PUBLIC_SITE + parsed.path[len(origin_path):])
    else:
        target = urlsplit(PUBLIC_ROOT + parsed.path)
    return urlunsplit((target.scheme, target.netloc, target.path, parsed.query, parsed.fragment))


def public_reference_text(value: str) -> str:
    """Project only complete owned URLs at public serialization boundaries."""
    def replace(match: re.Match[str]) -> str:
        url = match.group()
        clean = url.rstrip(".,;!?)")
        return public_reference_url(clean) + url[len(clean):]

    return re.sub(r'https://[^\s<>"\'\\]+', replace, value)
