#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stamp Apple campaign attribution on every outbound App Store link, in one place.

Only ~15 generators route their URLs through ``campaign_app_store_url``; the rest
emit plain ``https://apps.apple.com/app/id...`` strings, so even with a provider
token configured most of the site would still be unattributed and we could never
tell which page earns a download.  Patching every generator does not scale (the
tree has 250+ of them and they are actively edited).  This is the choke point
instead: it runs after the HTML generators. The final audit also checks feeds,
APIs and downloadable artifacts emitted later in the pipeline.

Rules that keep it safe:
  • A valid provider token is mandatory; missing configuration fails closed.
  • Anchors, share URLs, Smart App Banners and embedded tool/download payloads
    are attributed. Canonical/hreflang, entity IDs and sameAs remain clean.
    Standalone API/feed/download files are validated by audit_store_attribution
    after all generators; their content digests are never patched after the fact.
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
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from app_store_storefronts import (  # noqa: E402
    APP_STORE_PATH_RE,
    LOCALE_STOREFRONTS,
    PROVIDER_TOKEN_ENV,
    PROVIDER_TOKEN_RE,
    is_clean_app_store_developer_url,
    load_storefront_availability,
    normalize_app_store_campaign_url,
    required_campaign_app_store_url,
    resolve_provider_token,
    storefront_locale_for_url,
)

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
# Web Stories and publisher intent visuals carry their own per-surface
# campaigns. Their generators and gates validate those links as atomic
# collections, so a generic final pass must not mutate them.
EXCLUDED_PARTS = {
    ".git",
    "_engine",
    "node_modules",
}
PROTECTED_PARTS = {"stories", "visuals"}
ANCHOR_HREF_RE = re.compile(
    r"""(?P<prefix><(?:a|area)\b[^>]*?\bhref\s*=\s*(?P<quote>["']?))"""
    r"""(?P<url>(?:https?://|itms-apps://|//)apps\.apple\.com[^\s"'<>]*)"""
    r"(?P<suffix>(?P=quote))",
    flags=re.IGNORECASE,
)
# The share block (gen_app_store_share_ctas.py) hands this URL to the Web Share
# API, so a visitor's shared link carries whatever campaign is in the attribute.
# It is the same measurement surface as an anchor and must carry the same token,
# otherwise 27k links keep reporting under a legacy campaign.
SHARE_URL_RE = re.compile(
    r"""(?P<prefix>\bdata-app-store-url\s*=\s*(?P<quote>["']?))"""
    r"""(?P<url>(?:https?://|itms-apps://|//)apps\.apple\.com[^\s"'<>]*)"""
    r"(?P<suffix>(?P=quote))",
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
HIGH_INTENT_BUCKETS = {
    "problem_aware": ASK,
    "alternative": PICK,
    "workflow": LEARN,
    "privacy_pay_once": PICK,
}
HIGH_INTENT_META_RE = re.compile(
    r'<meta\s+name="growth-attribution-intent"\s+content="'
    r'(?P<intent>[a-z_]+)">',
    flags=re.IGNORECASE,
)

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
STORY_CAMPAIGN = "iag_story"
PROTECTED_CAMPAIGNS = frozenset({STORY_CAMPAIGN})

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


def campaign_token_for_intent(intent: str) -> str:
    """Map a reviewed high-intent route onto the shared three-token contract."""
    try:
        bucket = HIGH_INTENT_BUCKETS[intent]
    except KeyError as error:
        raise ValueError(f"Unsupported attribution intent: {intent}") from error
    token = TOKEN_PREFIX + bucket
    if len(token) > MAX_TOKEN:
        raise ValueError(f"Campaign token exceeds {MAX_TOKEN} characters: {token}")
    return token


def campaign_token(rel: str, page_text: str | None = None) -> str:
    """Bucket a page path into one of three campaign tokens.

    ``rel`` is the page path relative to pages/, e.g. ``ja/answers/foo.html``
    or ``answers/foo.html`` (the English tree has no locale prefix).  The
    locale segment is ignored on purpose — market comes back for free as the
    Territory column of the download report. High-intent decision pages carry
    an explicit reviewed intent marker so the final site-wide stamping pass
    deterministically preserves the generator's intent mapping.
    """
    if page_text is not None:
        marker = HIGH_INTENT_META_RE.search(page_text)
        if marker:
            return campaign_token_for_intent(marker.group("intent"))
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


def align_storefront(url: str, locale: str | None, availability=None) -> str:
    """Send a page's readers to their own storefront, never another country's.

    Legacy generators minted some links on a fixed storefront (Lumi apps on
    ``/tw/`` inside English answer pages). validated_app_store_url rejects
    that as a storefront mismatch, so the single stamper authority moves the
    link onto the page locale's storefront when the app is verified there and
    otherwise falls back to the global (country-less) link. Pages outside the
    official locales and links without a country are left untouched.
    """
    if locale not in LOCALE_STOREFRONTS:
        return url
    parsed = urllib.parse.urlsplit(url)
    match = APP_STORE_PATH_RE.fullmatch(parsed.path)
    if match is None or match["country"] is None:
        return url
    target = LOCALE_STOREFRONTS[locale]
    if match["country"] == target or match["country"] not in LOCALE_STOREFRONTS.values():
        # Only a *known* foreign storefront is re-homed; an unknown country code
        # is corrupt input and must keep failing closed downstream.
        return url
    app_id = match["app_id"]
    if availability is None or app_id in availability.get(target, frozenset()):
        path = f"/{target}/app/id{app_id}"
    else:
        path = f"/app/id{app_id}"
    return urllib.parse.urlunsplit(parsed._replace(path=path))


def final_store_url(
    url: str, token: str, provider: str | None, *,
    locale: str | None = None, availability=None, app_id: str | None = None,
) -> str:
    """The exact link the stamper will leave on a page: storefront aligned to
    the page locale, then the page campaign (protected campaigns kept).
    Generators that hash a link (QR cards) must mint from this, never from
    the pre-stamp CTA, or the QR desync gate rejects the whole tree."""
    if is_clean_app_store_developer_url(url):
        return url
    url = align_storefront(url, locale, availability)
    existing = existing_campaign(url)
    campaign = existing if existing in PROTECTED_CAMPAIGNS else token
    return required_campaign_app_store_url(
        url, campaign, provider_token=provider,
        expected_locale=storefront_locale_for_url(url, locale),
        expected_app_id=app_id, availability=availability,
    )


def rewrite(
    text: str, token: str, provider: str | None, *,
    locale: str | None = None, availability=None,
) -> tuple[str, int]:
    """Re-stamp every store anchor in ``text`` with ``token``.

    This is the single authority on campaign tokens for the site tree.  Before
    2026-08-20 it skipped any URL a generator had already tagged, which left
    ~614 generator-minted tokens (108k links on iag_decision alone) outside the
    taxonomy and split the site so finely that no bucket could reach Apple's
    five-download disclosure threshold.  The one
    exception is PROTECTED_CAMPAIGNS, whose tokens are part of a contract that
    is checked elsewhere.
    """
    from audit_store_attribution import (
        SCRIPT_RE, STORE_TEXT_RE, identity_field, is_store_url, js_strings,
        schema_node, schema_value_field,
    )

    if locale is None:
        # Root-level pages have no locale directory; the read-only audit
        # derives their storefront from <html lang>, so the stamper must too.
        from audit_store_attribution import _locale

        declared = re.search(r"""<html\b[^>]*\blang\s*=\s*["']([^"']+)["']""", text, re.I)
        if declared is not None:
            candidate = _locale(declared.group(1), None)
            if candidate in LOCALE_STOREFRONTS:
                locale = candidate
    changes = 0

    def retarget(url: str, local=locale, app_id=None) -> str:
        return final_store_url(
            url, token, provider, locale=local, availability=availability, app_id=app_id,
        )

    def replace(match: re.Match[str]) -> str:
        nonlocal changes
        raw = match.group("url")
        # Half the tree writes the query as &amp;; decode before parsing and
        # re-encode afterwards so the rewrite never changes how a page parses.
        escaped = html.unescape(raw) != raw
        url = html.unescape(raw)
        updated = retarget(url)
        if escaped:
            updated = updated.replace("&", "&amp;")
        if updated == raw:
            return match.group(0)
        changes += 1
        return match.group("prefix") + updated + match.group("suffix")

    def json_value(value, *, field="", parent=None, local=locale, app_id=None, schema=False):
        nonlocal changes
        # Provenance/identity fields and JSON Schema sample or regex keywords
        # are mirrored by audit_store_attribution: neither is a CTA to stamp.
        if identity_field(field, parent) or schema_value_field(field, parent, schema):
            return value
        if isinstance(value, dict):
            schema = schema_node(value, schema)
            local = value.get("locale", value.get("page_language", local))
            local = "en-US" if local == "en" else local
            app_id = str(value["app_store_id"]) if "app_store_id" in value else app_id
            return {
                key: json_value(
                    child, field=key, parent=value, local=local, app_id=app_id, schema=schema
                )
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [
                json_value(child, field=field, local=local, app_id=app_id, schema=schema)
                for child in value
            ]
        if isinstance(value, str) and is_store_url(value):
            updated = STORE_TEXT_RE.sub(
                lambda match: retarget(match.group(), local, app_id), value
            )
            changes += int(updated != value)
            return updated
        return value

    def script(match):
        nonlocal changes
        body = match["body"]
        if re.search(r"""type\s*=\s*["']application/(?:ld\+)?json["']""", match["open"], re.I):
            payload = json.loads(body)
            updated = json_value(payload)
            if updated != payload:
                body = json.dumps(updated, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")
        else:
            replacements = []
            for literal, value, field in js_strings(body):
                if not is_store_url(value) or identity_field(field):
                    continue
                updated = STORE_TEXT_RE.sub(lambda item: retarget(item.group()), value)
                if updated != value:
                    changes += 1
                    replacements.append((literal.start(), literal.end(), json.dumps(updated, ensure_ascii=False)))
            for start, end, replacement in reversed(replacements):
                body = body[:start] + replacement + body[end:]
        return match["open"] + body + match["close"]

    def banner(match):
        nonlocal changes
        source = match.group()
        if not re.search(r"""name\s*=\s*["']apple-itunes-app["']""", source, re.I):
            return source
        content = re.search(r"""content\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)""", source, re.I)
        if content is None:
            raise ValueError("Smart App Banner has no content")
        fields = dict(
            item.strip().split("=", 1)
            for item in html.unescape(content["value"]).split(",") if "=" in item
        )
        app_id = fields.get("app-id", "")
        url = retarget(f"https://apps.apple.com/app/id{app_id}")
        fields["affiliate-data"] = urllib.parse.urlsplit(url).query
        updated = html.escape(", ".join(f"{key}={value}" for key, value in fields.items()), quote=True)
        if updated != content["value"]:
            changes += 1
            source = source[:content.start("value")] + updated + source[content.end("value"):]
        return source

    def markup(source):
        for pattern in STORE_URL_PATTERNS:
            source = pattern.sub(replace, source)
        return re.sub(r"<meta\b[^>]*>", banner, source, flags=re.I)

    pieces = []
    previous = 0
    for match in SCRIPT_RE.finditer(text):
        pieces.extend((markup(text[previous:match.start()]), script(match)))
        previous = match.end()
    pieces.append(markup(text[previous:]))
    return "".join(pieces), changes


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
    if not link and not image:
        return None
    if not link or not image:
        raise QrCardDesyncError("App Store QR card is missing its link or image")
    url = normalize_app_store_campaign_url(
        html.unescape(link.group("href"))
    )
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


def page_token(rel: str, text: str) -> str | None:
    """The single campaign a page may carry: stories use the protected story
    campaign, publisher visuals are left to their own generator (None), every
    other surface gets the taxonomy bucket for its path."""
    parts = set(Path(rel).parts)
    if "stories" in parts:
        return STORY_CAMPAIGN
    if PROTECTED_PARTS.intersection(parts):
        return None
    return campaign_token(rel, text)


def generate(pages: Path, check: bool) -> dict[str, object]:
    from audit_store_attribution import audit_source, locale_of

    provider = resolve_provider_token() or None
    if provider is None or PROVIDER_TOKEN_RE.fullmatch(provider) is None:
        raise ValueError(f"{PROVIDER_TOKEN_ENV} must be configured for publication")
    if not pages.is_dir():
        raise ValueError(f"Missing generated pages directory: {pages}")
    availability = load_storefront_availability(pages) or None
    files_with_links = 0
    files_changed = 0
    links_total = 0
    links_stamped = 0
    tokens: Counter = Counter()
    pending = []
    for rel, path in iter_html(pages):
        text = path.read_text(encoding="utf-8")
        if not any(marker in text for marker in (
            "apps.apple.com", "apple-itunes-app", "data-app-store-url",
            "app_store_url", "app-store-qr-card",
        )):
            continue
        anchors = [
            match
            for pattern in STORE_URL_PATTERNS
            for match in pattern.findall(text)
        ]
        protected = bool(PROTECTED_PARTS.intersection(Path(rel).parts))
        files_with_links += int(bool(anchors) and not protected)
        links_total += len(anchors)
        token = page_token(rel, text)
        # Every failure names the page: a whole-tree run must point straight at
        # the offending file instead of leaving the operator to bisect 80k pages.
        try:
            # Web Stories keep their own iag_story campaign but still carry
            # machine-readable MobileApplication url/installUrl/downloadUrl
            # that gen_mobile_app_identity emits clean; stamp those with the
            # story campaign so the page has exactly one attributable token.
            # Publisher visuals mint per-locale atomic campaigns and stay untouched.
            updated, changes = (text, 0) if protected and token is None else rewrite(
                text, token, provider, locale=locale_of(rel), availability=availability
            )
            desync = qr_card_desync(updated)
        except QrCardDesyncError as error:
            raise QrCardDesyncError(f"{rel}: {error}") from error
        except ValueError as error:
            raise ValueError(f"{rel}: {error}") from error
        if desync:
            href, stale, expected = desync
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
        try:
            refs = audit_source(updated, rel, provider=provider, availability=availability)
        except ValueError as error:
            raise ValueError(f"{rel}: {error}") from error
        for ref in refs:
            if not ref.identity:
                tokens[existing_campaign(ref.url)] += 1
        if changes:
            links_stamped += changes
            files_changed += 1
            if not check:
                pending.append((rel, path, hashlib.sha256(text.encode("utf-8")).digest()))
    # Validate the entire input before changing any page. Do not retain a whole
    # site's HTML in memory, and never overwrite a concurrently changed page.
    for rel, path, digest in pending:
        text = path.read_text(encoding="utf-8")
        if hashlib.sha256(text.encode("utf-8")).digest() != digest:
            raise ValueError(f"Page changed during attribution preflight: {rel}")
        try:
            updated, _ = rewrite(
                text, page_token(rel, text), provider,
                locale=locale_of(rel), availability=availability,
            )
        except ValueError as error:
            raise ValueError(f"{rel}: {error}") from error
        path.write_text(updated, encoding="utf-8")
    return {
        "provider_token_configured": bool(provider),
        "pages_with_store_anchors": files_with_links,
        "store_anchors": links_total,
        "attributed_links": sum(tokens.values()),
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
    if args.check and stats["pages_changed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
