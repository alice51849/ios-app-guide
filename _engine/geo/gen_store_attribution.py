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
  • Only ``<a href>`` and the share block's ``data-app-store-url`` are
    touched — the two surfaces a visitor can actually click.  JSON-LD ``url``/``sameAs``,
    feeds and APIs keep the clean canonical URL, because a tracking query string
    there would break entity identity for search and AI engines.
  • Generator-minted campaigns are re-stamped (see "single authority" below),
    except publisher-managed surfaces: Web Stories own ``iag_story`` and the
    localized visual collection owns ``iag_visual_<locale>``.
  • The original ``&`` / ``&amp;`` escaping of the href is preserved, so the
    rewrite never changes how a page is parsed.

    python geo/gen_store_attribution.py           # apply
    python geo/gen_store_attribution.py --check   # report only
"""
from __future__ import annotations

import argparse
import hashlib
import html
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
    normalize_app_store_campaign_url,
    resolve_provider_token,
)

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
# Web Stories and publisher intent visuals carry their own per-surface
# campaigns. Their generators and gates validate those links as atomic
# collections, so a generic final pass must not mutate them.
EXCLUDED_PARTS = {
    ".git",
    "_engine",
    "node_modules",
    "stories",
    "visuals",
}
ANCHOR_HREF_RE = re.compile(
    r'(?P<prefix><a\b[^>]*?\bhref=")'
    r"(?P<url>https://apps\.apple\.com/[^\"]*)"
    r'(?P<suffix>")',
    flags=re.IGNORECASE,
)
# The share block (gen_app_store_share_ctas.py) hands this URL to the Web Share
# API, so a visitor's shared link carries whatever campaign is in the attribute.
# It is the same measurement surface as an anchor and must carry the same token,
# otherwise 27k links keep reporting under a legacy campaign.
SHARE_URL_RE = re.compile(
    r'(?P<prefix>\bdata-app-store-url=")'
    r"(?P<url>https://apps\.apple\.com/[^\"]*)"
    r'(?P<suffix>")',
    flags=re.IGNORECASE,
)
STORE_URL_PATTERNS = (ANCHOR_HREF_RE, SHARE_URL_RE)
CAMPAIGN_SAFE_RE = re.compile(r"[^A-Za-z0-9_]")
MAX_TOKEN = 30
TOKEN_PREFIX = "geo_"

# --------------------------------------------------------------------------- #
# Campaign taxonomy — deliberately three buckets, on ONE axis
#
# Apple only reports a campaign once it has produced first-time downloads from
# at least five individual users inside the report window, and the row is
# namespaced per app.  The real unit is therefore the (app, campaign) cell, and
# the budget that has to fill those cells is tiny:
#
#   * Web-referrer first-time downloads, whole portfolio, 30 days: 29–30
#     (reports/geo_performance_history.jsonl, 2026-08-17..19 — an earlier
#     version of this comment read that as ~29/DAY, which was wrong by 30x).
#   * The Campaign column only exists in the "App Downloads Detailed" report,
#     and Apple only generates that report for apps that clear their own
#     privacy floor: 12 of 42 apps today (reports/referrer_sources.json).
#     Of those 12, six have any web-referrer download at all, and one (Mochi,
#     14/month) is 58% of the eligible volume.
#
# So the honest budget is ~24 attributable downloads/month spread over the apps
# Apple will report on.  Before this rewrite the site emitted 703 distinct
# campaign tokens (89 minted here plus ~614 generator-minted iag_* ones), i.e.
# ~29,500 (app, campaign) cells for ~24 downloads/month — nothing could ever
# reach five, and the biggest token by far (iag_decision, 108k links) was not
# reversible into a page type, so even if it did report it answered nothing.
#
# What survives in the token: ONE axis, content intent, three values.  It is the
# only axis we can act on editorially (write more of what converts).
#
# What is deliberately NOT in the token, because Apple already gives it back as
# a free dimension on the very same report rows:
#   * app     — Analytics reports are pulled per app (acquisition_feedback.py).
#   * market  — "Territory" is a column on the download rows; encoding a locale
#               group as well multiplied the buckets 7x for data we already had.
#   * page / tool identity — unaffordable at this volume; folded into the three.
#
# Token shape: geo_ask | geo_pick | geo_learn.
# --------------------------------------------------------------------------- #

ASK = "ask"      # question / problem intent — the AEO surface
PICK = "pick"    # browse & choose: hubs, roundups, comparisons, reviews
LEARN = "learn"  # how-to, workflow, tools, media — instructional intent
BUCKETS = (ASK, PICK, LEARN)

# Directory name -> bucket.  PICK is also the residual: hub and locale-home
# pages, theme roundups (pay-once / gifting / no-account / switching …) and any
# page type nobody has classified yet are all "browse a curated set of apps"
# surfaces, so they belong there rather than in a fourth bucket.  A fourth
# bucket was measured and rejected: it would have held 13% of links, i.e. ~1.8
# downloads/month for even our biggest app — permanently under the threshold.
SECTION_BUCKETS = {
    "answers": ASK, "problems": ASK, "faq": ASK, "faqs": ASK,
    "questions": ASK,

    "vs": PICK, "cross": PICK, "alternatives": PICK, "best-for": PICK,
    "reviews": PICK, "review-hubs": PICK, "seasonal": PICK, "apps": PICK,
    "bundle": PICK, "compare": PICK, "hubs": PICK, "topic-hubs": PICK,
    "data": PICK,

    "guides": LEARN, "tutorials": LEARN, "workflow": LEARN, "scenario": LEARN,
    "tools": LEARN, "stories": LEARN, "videos": LEARN, "visuals": LEARN,
    "persona": LEARN, "publications": LEARN, "lessons": LEARN,
}

# Campaigns this pass must not touch.  Web Stories mint iag_story and
# validate_webstories.py checks it against the Smart App Banner meta tag; the
# stories/ directories are skipped anyway, this is the belt to that braces.
PROTECTED_CAMPAIGNS = frozenset({"iag_story"})

# Historical tokens -> the bucket they roll up into, so the report keeps one
# continuous series across the 2026-08-20 change instead of starting at zero.
# Legacy geo_<section>_<market> tokens are reversed through SECTION_BUCKETS;
# these prefixes cover the generator-minted iag_* family.  Longest match wins.
LEGACY_IAG_BUCKETS = (
    ("iag_ans", ASK),
    ("iag_blur_guide", LEARN),
    ("iag_alt", PICK),
    ("iag_bestfor", PICK),
    ("iag_bf", PICK),
    ("iag_bundle", PICK),
    ("iag_decision", PICK),
    ("iag_review", PICK),
    ("iag_seasonal", PICK),
    ("iag_vs", PICK),
    ("iag_find", LEARN),
    ("iag_guide", LEARN),
    ("iag_story", LEARN),
    ("iag_video", LEARN),
    ("iag_visual", LEARN),
    ("iag_data", PICK),
    ("iag_lp", PICK),
)


def _bucket_of(part: str) -> str | None:
    return SECTION_BUCKETS.get(part)


def campaign_token(rel: str) -> str:
    """Bucket a page path into one of four campaign tokens.

    ``rel`` is the page path relative to pages/, e.g. ``ja/answers/foo.html``
    or ``answers/foo.html`` (the English tree has no locale prefix).  The
    locale segment is ignored on purpose — market comes back for free as the
    Territory column of the download report.
    """
    parts = [part for part in rel.split("/") if part]
    directories = parts[:-1]
    bucket = PICK
    for part in directories:
        resolved = _bucket_of(part)
        if resolved is not None:
            bucket = resolved
            break
    token = TOKEN_PREFIX + CAMPAIGN_SAFE_RE.sub("_", bucket)
    return token[:MAX_TOKEN].rstrip("_") or "geo"


def parse_campaign_token(token: str) -> tuple[str, str] | None:
    """Reverse a campaign token into ``(bucket, legacy_market)``.

    Current tokens carry no market, so the second element is "" and callers
    should read the market off the report's Territory column instead.  Tokens
    minted before 2026-08-20 still reverse — ``geo_best_for_ja`` ->
    ``("pick", "ja")``, ``iag_decision`` -> ``("pick", "")`` — so history rolls
    up into the same three buckets rather than breaking the series.
    """
    if not token:
        return None
    if token.startswith("iag_"):
        match = max(
            (prefix for prefix, _ in LEGACY_IAG_BUCKETS
             if token == prefix or token.startswith(prefix + "_")),
            key=len,
            default=None,
        )
        if match is None:
            return PICK, ""
        return dict(LEGACY_IAG_BUCKETS)[match], ""
    if not token.startswith(TOKEN_PREFIX):
        return None
    body = token[len(TOKEN_PREFIX):]
    if body in BUCKETS:
        return body, ""
    section, _, market = body.rpartition("_")
    if not section or not market:
        return None
    # legacy sections were emitted with "_" swapped in for "-"
    bucket = _bucket_of(section.replace("_", "-")) or PICK
    return bucket, market


CAMPAIGN_PARAM_RE = re.compile(r"[?&]ct=([A-Za-z0-9_/]*)")


def existing_campaign(url: str) -> str | None:
    """The ct= token already on a URL, or None."""
    match = CAMPAIGN_PARAM_RE.search(url)
    return match.group(1) if match else None


def has_campaign(url: str) -> bool:
    return existing_campaign(url) is not None


def rewrite(text: str, token: str, provider: str | None) -> tuple[str, int]:
    """Re-stamp every store anchor in ``text`` with ``token``.

    This is the single authority on campaign tokens for the site tree.  Before
    2026-08-20 it skipped any URL a generator had already tagged, which left
    ~614 generator-minted tokens (108k links on iag_decision alone) outside the
    taxonomy and split the site so finely that no bucket could reach Apple's
    five-download disclosure threshold.  The one
    exception is PROTECTED_CAMPAIGNS, whose tokens are part of a contract that
    is checked elsewhere.
    """
    changes = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changes
        raw = match.group("url")
        # Half the tree writes the query as &amp;; decode before parsing and
        # re-encode afterwards so the rewrite never changes how a page parses.
        escaped = "&amp;" in raw
        url = raw.replace("&amp;", "&") if escaped else raw
        if existing_campaign(url) in PROTECTED_CAMPAIGNS:
            return match.group(0)
        try:
            updated = campaign_app_store_url(url, token, provider_token=provider)
        except ValueError:
            return match.group(0)  # never break a page over an odd URL
        if escaped:
            updated = updated.replace("&", "&amp;")
        if updated == raw:
            return match.group(0)
        changes += 1
        return match.group("prefix") + updated + match.group("suffix")

    for pattern in STORE_URL_PATTERNS:
        text = pattern.sub(replace, text)
    return text, changes


# --------------------------------------------------------------------------- #
# Fail-closed guard: gen_app_store_qr_ctas.py mints one SVG per *URL* and puts
# the sha256 of that URL in the file name, so a QR image is only correct for
# the exact link printed beside it.  This pass runs last and rewrites those
# links, which means any generator that mints a campaign token this pass does
# not agree with silently leaves 2,100+ pages whose QR code scans to a
# different campaign than the button next to it.  That is what happened on
# 2026-08-20, when gen_app_decision_cards.py still minted the pre-collapse
# `iag_decision` token: the only symptom was 2,100 opaque assertion failures
# in the growth-infra gate, hours after the fact.  Detect it here, at the
# moment the desynchronisation is created, and name the page.
# --------------------------------------------------------------------------- #
QR_CARD_LINK_RE = re.compile(
    r'app-store-qr-card__link"\s+href="(?P<href>[^"]+)"'
)
QR_CARD_IMAGE_RE = re.compile(
    r'app-store-qr-card__image"\s+src="[^"]*/'
    r'id(?P<app>\d+)-(?P<digest>[0-9a-f]{20})\.svg"'
)


def qr_card_desync(text: str) -> tuple[str, str, str] | None:
    """``(href, image_digest, expected_digest)`` when a QR image is stale.

    ``None`` when the page has no QR card, or when its image still encodes the
    very URL the card links to.
    """
    link = QR_CARD_LINK_RE.search(text)
    image = QR_CARD_IMAGE_RE.search(text)
    if not link or not image:
        return None
    try:
        url = normalize_app_store_campaign_url(
            html.unescape(link.group("href"))
        )
    except ValueError:
        return None
    expected = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    if expected == image.group("digest"):
        return None
    return link.group("href"), image.group("digest"), expected


class QrCardDesyncError(RuntimeError):
    """Raised when this pass would outdate a page's App Store QR image."""


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
        anchors = [
            match
            for pattern in STORE_URL_PATTERNS
            for match in pattern.findall(text)
        ]
        if not anchors:
            continue
        files_with_links += 1
        links_total += len(anchors)
        token = campaign_token(rel)
        updated, changes = rewrite(text, token, provider)
        if changes and qr_card_desync(updated) and not qr_card_desync(text):
            href, stale, expected = qr_card_desync(updated)
            raise QrCardDesyncError(
                "store attribution would outdate the App Store QR image on "
                f"{rel}: the card now links to {href} (sha {expected}) but its "
                f"QR image still encodes sha {stale}. Whichever generator "
                "minted that link must use gen_store_attribution."
                "campaign_token() so the URL is already final before "
                "gen_app_store_qr_ctas.py hashes it."
            )
        # Census the token for every anchor on the page, not just the ones this
        # run had to touch — otherwise a second (idempotent) run reports zero
        # campaigns and the taxonomy looks empty.
        if provider:
            tokens[token] += len(anchors)
        if changes:
            links_stamped += changes
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
        "links_by_campaign": dict(tokens.most_common()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stats = generate(args.pages_dir, args.check)
    by_campaign = stats.pop("links_by_campaign", {})
    print("store-attribution: " + " ".join(f"{k}={v}" for k, v in stats.items()))
    for campaign, count in by_campaign.items():
        print(f"store-attribution:   {campaign} links={count:,}")
    if not stats["provider_token_configured"]:
        print(
            f"store-attribution: {PROVIDER_TOKEN_ENV} is unset — links left clean; "
            "set it and re-run to attribute the whole site."
        )


if __name__ == "__main__":
    main()
