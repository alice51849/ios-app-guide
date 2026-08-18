#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stamp Apple campaign attribution on every outbound App Store link, in one place.

Only ~15 generators route their URLs through ``campaign_app_store_url``; the rest
emit plain ``https://apps.apple.com/app/id...`` strings, so even with a provider
token configured most of the site would still be unattributed and we could never
tell which page earns a download.  Patching every generator does not scale (the
tree has 250+ of them and they are actively edited).  This is the choke point
instead: it runs after all generators and rewrites the *anchors* they produced.

Rules that keep it safe:
  • No provider token (``APP_STORE_PROVIDER_TOKEN``, else
    ``~/.growth-private/app-store-provider-token``) => every URL is returned
    unchanged, so this is a no-op until Apple's token is configured.
  • Only ``<a href>`` targets in HTML are touched.  JSON-LD ``url``/``sameAs``,
    feeds and APIs keep the clean canonical URL, because a tracking query string
    there would break entity identity for search and AI engines.
  • Links that already carry a ``ct`` campaign from a generator are left alone.

    python geo/gen_store_attribution.py           # apply
    python geo/gen_store_attribution.py --check   # report only
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from app_store_storefronts import (  # noqa: E402
    PROVIDER_TOKEN_ENV,
    campaign_app_store_url,
    resolve_provider_token,
)

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
# Web Stories carry their own per-surface campaign (iag_story), which their
# AMP gate verifies against the Smart App Banner meta tag; re-stamping them
# here would break that contract for no measurement gain.
EXCLUDED_PARTS = {".git", "_engine", "node_modules", "stories"}
ANCHOR_HREF_RE = re.compile(
    r'(?P<prefix><a\b[^>]*?\bhref=")'
    r"(?P<url>https://apps\.apple\.com/[^\"]*)"
    r'(?P<suffix>")',
    flags=re.IGNORECASE,
)
CAMPAIGN_SAFE_RE = re.compile(r"[^A-Za-z0-9_]")
MAX_TOKEN = 30
TOKEN_PREFIX = "geo_"

# --------------------------------------------------------------------------- #
# Campaign taxonomy
#
# Apple only shows a campaign once it has produced first-time downloads from at
# least five individual users, so the taxonomy has to stay COARSE or every
# bucket dies under that privacy threshold and we learn nothing.  Budget: the
# site currently earns ~29 web-referrer downloads/day (~870/month).  Splitting
# that over more than ~100 campaigns would leave almost every one invisible.
#
# Two axes, deliberately:
#   section      - the page type.  This is the axis we act on (write more of
#                  what converts), so it stays granular.
#   locale group - markets bucketed down to six.  Per-locale tokens would mean
#                  1,000+ campaigns (the tree has 1,043 language directories).
#
# The App axis is NOT in the token on purpose: acquisition_feedback.py already
# pulls Analytics per app, so every campaign row arrives namespaced by app for
# free.  Encoding it again would multiply the buckets ~40x for no new signal.
#
# Token shape: geo_<section>_<group>, e.g. geo_answers_ja, geo_best_for_en.
# parse_campaign_token() reverses it (group never contains "_", so rsplit works
# even for hyphenated sections like best-for -> best_for).
# --------------------------------------------------------------------------- #

# Page types worth telling apart, measured against the real tree.  Anything
# else collapses into "other" rather than inventing a long tail of dead
# campaigns.
KNOWN_SECTIONS = {
    "answers", "guides", "alternatives", "hubs", "stories", "tools", "apps",
    "vs", "workflow", "best-for", "reviews", "seasonal",
}
# Directory names that are sections in spirit but should roll up.
SECTION_ALIASES = {
    "topic-hubs": "hubs",
    "review-hubs": "reviews",
    "tutorials": "guides",
    "videos": "stories",
    "visuals": "stories",
    "persona": "stories",
    "scenario": "workflow",
    "cross": "vs",
    "bundle": "apps",
    "publications": "stories",
    "problems": "answers",
    "data": "other",
}
OTHER_SECTION = "other"
HOME_SECTION = "home"

# Seven market buckets.  Everything not listed is "intl".  "sea" is split out
# because ms/th/vi/id are four of the fifteen largest locale trees on the site;
# leaving them inside "intl" made one bucket carry ~19% of all store links.
LOCALE_GROUPS = {
    "sea": {"ms", "th", "vi", "id", "fil", "tl", "km", "lo", "my", "jv", "su"},
    "zh": {"zh", "zh-Hant", "zh-Hans", "zh-TW", "zh-CN", "zh-HK", "yue", "wuu",
           "nan", "hak"},
    "ja": {"ja", "ja-JP"},
    "ko": {"ko", "ko-KR"},
    "eu": {"de-DE", "de", "de-AT", "de-CH", "fr-FR", "fr", "fr-CA", "fr-BE",
           "es-ES", "es", "es-MX", "es-419", "it", "it-IT", "nl-NL", "nl",
           "pt-PT", "pt-BR", "pt", "pl", "ru", "sv", "uk", "fi", "da", "nb",
           "no", "cs", "el", "hu", "ro", "sk", "hr", "ca", "bg", "et", "lt",
           "lv", "sl", "sr", "is", "ga", "cy", "eu", "gl"},
}
ENGLISH_LOCALES = {"en", "en-US", "en-GB", "en-AU", "en-CA", "en-IN", "en-NZ",
                   "en-ZA", "en-IE", "en-SG"}
DEFAULT_GROUP = "intl"


def locale_group(locale: str) -> str:
    """Seven coarse market buckets; unknown/long-tail languages become 'intl'."""
    if not locale or locale in ENGLISH_LOCALES:
        return "en"
    for group, members in LOCALE_GROUPS.items():
        if locale in members:
            return group
    return DEFAULT_GROUP


def _section_of(part: str) -> str | None:
    if part in KNOWN_SECTIONS:
        return part
    return SECTION_ALIASES.get(part)


def campaign_token(rel: str) -> str:
    """Stable per-section/per-market campaign token, <=30 chars of [A-Za-z0-9_/].

    ``rel`` is the page path relative to pages/, e.g.
    ``ja/answers/foo.html`` or ``answers/foo.html`` (the English tree has no
    locale prefix — the old code read "answers" as the locale there and emitted
    geo_answers_answers).
    """
    parts = [part for part in rel.split("/") if part]
    directories = parts[:-1]
    if not directories:
        return TOKEN_PREFIX + HOME_SECTION + "_en"

    # A leading directory is the locale only when it is not itself a section.
    first = directories[0]
    if _section_of(first) is not None:
        locale, rest = "en", directories
    else:
        locale, rest = first, directories[1:]

    section = OTHER_SECTION
    for part in rest:
        resolved = _section_of(part)
        if resolved is not None:
            section = resolved
            break
    else:
        if not rest:
            section = HOME_SECTION

    token = "{}{}_{}".format(
        TOKEN_PREFIX,
        CAMPAIGN_SAFE_RE.sub("_", section),
        CAMPAIGN_SAFE_RE.sub("_", locale_group(locale)),
    )
    return token[:MAX_TOKEN].rstrip("_") or "geo"


def parse_campaign_token(token: str) -> tuple[str, str] | None:
    """Reverse campaign_token(): 'geo_best_for_ja' -> ('best_for', 'ja')."""
    if not token.startswith(TOKEN_PREFIX):
        return None
    body = token[len(TOKEN_PREFIX):]
    if "_" not in body:
        return None
    section, _, group = body.rpartition("_")
    if not section or not group:
        return None
    return section, group


def has_campaign(url: str) -> bool:
    return "ct=" in url


def rewrite(text: str, token: str, provider: str | None) -> tuple[str, int]:
    changes = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changes
        url = match.group("url")
        if has_campaign(url):
            return match.group(0)
        try:
            updated = campaign_app_store_url(url, token, provider_token=provider)
        except ValueError:
            return match.group(0)  # never break a page over an odd URL
        if updated == url:
            return match.group(0)
        changes += 1
        return match.group("prefix") + updated + match.group("suffix")

    return ANCHOR_HREF_RE.sub(replace, text), changes


def iter_html(pages: Path):
    for path in pages.rglob("*.html"):
        if EXCLUDED_PARTS.intersection(path.relative_to(pages).parts):
            continue
        yield path.relative_to(pages).as_posix(), path


def generate(pages: Path, check: bool) -> dict[str, object]:
    provider = resolve_provider_token() or None
    files_with_links = 0
    files_changed = 0
    links_total = 0
    links_stamped = 0
    tokens: Counter = Counter()
    for rel, path in iter_html(pages):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "apps.apple.com" not in text:
            continue
        anchors = ANCHOR_HREF_RE.findall(text)
        if not anchors:
            continue
        files_with_links += 1
        links_total += len(anchors)
        token = campaign_token(rel)
        updated, changes = rewrite(text, token, provider)
        if changes:
            links_stamped += changes
            tokens[token] += changes
            files_changed += 1
            if not check:
                path.write_text(updated, encoding="utf-8")
    return {
        "provider_token_configured": bool(provider),
        "pages_with_store_anchors": files_with_links,
        "store_anchors": links_total,
        "anchors_stamped": links_stamped,
        "pages_changed": files_changed,
        "distinct_campaigns": len(tokens),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stats = generate(args.pages_dir, args.check)
    print("store-attribution: " + " ".join(f"{k}={v}" for k, v in stats.items()))
    if not stats["provider_token_configured"]:
        print(
            f"store-attribution: {PROVIDER_TOKEN_ENV} is unset — links left clean; "
            "set it and re-run to attribute the whole site."
        )


if __name__ == "__main__":
    main()
