#!/usr/bin/env python3
"""Fail publication unless every live app has a complete 50-locale Web Story."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402

from appstore_live import live_app_keys  # noqa: E402
from build_pages_i18n import RTL, base_lang, get_ui  # noqa: E402
from gen_webstories_i18n import validated_localizations  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
HREFLANG_RE = re.compile(
    r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)">',
    re.IGNORECASE,
)
CANONICAL_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="([^"]+)">',
    re.IGNORECASE,
)
JSON_LD_RE = re.compile(
    r'<script\s+type="application/ld\+json">(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
APP_META_RE = re.compile(
    r'<meta\s+name="apple-itunes-app"\s+content="'
    r'app-id=(\d+),\s*app-argument=([^"]+)">',
    re.IGNORECASE,
)
PAGE_ID_RE = re.compile(r'<amp-story-page\s+id="([^"]+)">', re.IGNORECASE)


def story_url(key, locale=None):
    prefix = f"/{locale}" if locale else ""
    return f"{SITE}{prefix}/stories/{key}.html"


def index_url(locale=None):
    prefix = f"/{locale}" if locale else ""
    return f"{SITE}{prefix}/stories/"


def expected_alternates(relative_path):
    root_url = f"{SITE}{relative_path}"
    alternates = {"x-default": root_url, "en": root_url}
    alternates.update(
        {
            locale: f"{SITE}/{locale}{relative_path}"
            for locale in OFFICIAL_LOCALES
        }
    )
    return alternates


def require_alternates(document, expected, label):
    pairs = HREFLANG_RE.findall(document)
    actual = dict(pairs)
    if len(pairs) != len(actual):
        raise ValueError(f"{label}: duplicate hreflang entries")
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        raise ValueError(
            f"{label}: invalid hreflang set; "
            f"missing={missing}, unexpected={unexpected}"
        )


def require_mobile_identity(document, key, canonical, label):
    objects = []
    for source in JSON_LD_RE.findall(document):
        payload = json.loads(source)
        objects.extend(payload if isinstance(payload, list) else [payload])
    apps = [
        item
        for item in objects
        if isinstance(item, dict) and item.get("@type") == "MobileApplication"
    ]
    if len(apps) != 1:
        raise ValueError(f"{label}: expected one MobileApplication, found {len(apps)}")
    app = apps[0]
    store_url = f"https://apps.apple.com/app/id{APPSTORE[key]}"
    expected = {
        "@id": store_url,
        "url": store_url,
        "installUrl": store_url,
        "downloadUrl": store_url,
    }
    for field, value in expected.items():
        if app.get(field) != value:
            raise ValueError(f"{label}: invalid MobileApplication.{field}")
    identifier = app.get("identifier", {})
    if identifier.get("value") != APPSTORE[key]:
        raise ValueError(f"{label}: invalid App Store identifier")
    if app.get("mainEntityOfPage") != {"@id": f"{canonical}#webpage"}:
        raise ValueError(f"{label}: invalid mainEntityOfPage")


def validate_story(path, key, locale=None, localization=None):
    label = f"{locale or 'root'}/{key}"
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"{label}: missing or empty Story")
    document = path.read_text(encoding="utf-8")
    canonical = story_url(key, locale)
    canonical_matches = CANONICAL_RE.findall(document)
    if canonical_matches != [canonical]:
        raise ValueError(f"{label}: invalid canonical URL")
    require_alternates(
        document,
        expected_alternates(f"/stories/{key}.html"),
        label,
    )
    # The attribute is HTML-escaped in the document, so a campaign URL with
    # "&pt=...&ct=...&mt=8" arrives here as "&amp;". Compare the decoded value.
    meta_matches = [
        (app_id, html.unescape(argument))
        for app_id, argument in APP_META_RE.findall(document)
    ]
    campaign_url = appstore_url(key, "iag_story")
    if meta_matches != [(APPSTORE[key], campaign_url)]:
        raise ValueError(f"{label}: invalid Smart App Banner campaign URL")
    if f'href="{html.escape(campaign_url, quote=True)}"' not in document:
        raise ValueError(f"{label}: missing direct App Store CTA")
    require_mobile_identity(document, key, canonical, label)

    if "<html amp " not in document:
        raise ValueError(f"{label}: missing AMP html attribute")
    expected_language = locale or "en"
    if f'lang="{expected_language}"' not in document:
        raise ValueError(f"{label}: invalid html language")
    expected_direction = "rtl" if locale and base_lang(locale) in RTL else "ltr"
    if locale and f'dir="{expected_direction}"' not in document:
        raise ValueError(f"{label}: invalid text direction")
    required_fragments = (
        '<script async src="https://cdn.ampproject.org/v0.js"></script>',
        'custom-element="amp-story"',
        "<style amp-boilerplate>",
        "<noscript><style amp-boilerplate>",
        "<style amp-custom>",
        "<amp-story standalone ",
        "<amp-story-cta-layer>",
    )
    for fragment in required_fragments:
        if fragment not in document:
            raise ValueError(f"{label}: missing AMP fragment {fragment}")
    page_ids = PAGE_ID_RE.findall(document)
    if len(page_ids) != 4 or len(set(page_ids)) != 4 or "cta" not in page_ids:
        raise ValueError(f"{label}: invalid AMP Story page IDs")

    if locale:
        name = localization["name"].strip()
        expected_cta = html.escape(get_ui(locale)["get"].format(name=name))
        if expected_cta not in document:
            raise ValueError(f"{label}: missing native-language CTA")


def validate_index(path, keys, locale=None):
    label = f"{locale or 'root'}/stories/index"
    document = path.read_text(encoding="utf-8")
    if CANONICAL_RE.findall(document) != [index_url(locale)]:
        raise ValueError(f"{label}: invalid canonical URL")
    require_alternates(document, expected_alternates("/stories/"), label)
    for key in keys:
        if story_url(key, locale) not in document:
            raise ValueError(f"{label}: missing {key}")


def validate_sitemap(keys):
    expected = {
        story_url(key, locale)
        for key in keys
        for locale in (None, *OFFICIAL_LOCALES)
    }
    expected.update(index_url(locale) for locale in (None, *OFFICIAL_LOCALES))
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(PAGES / "sitemap_stories.xml")
    entries = root.findall("s:url", namespace)
    actual = [
        entry.findtext("s:loc", namespaces=namespace)
        for entry in entries
    ]
    if len(actual) != len(set(actual)):
        raise ValueError("sitemap_stories.xml contains duplicate URLs")
    if set(actual) != expected:
        raise ValueError(
            "sitemap_stories.xml does not match the complete Story matrix"
        )
    return len(actual)


def validate_site():
    live_keys = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    keys = [key for key in APPS if key in live_keys and appstore_url(key)]
    expected_keys = set(keys)
    root_keys = {
        path.stem
        for path in (PAGES / "stories").glob("*.html")
        if path.name != "index.html"
    }
    if root_keys != expected_keys:
        raise ValueError("Root Web Stories do not match the live app portfolio")
    locale_dirs = {
        path.parent.name
        for path in PAGES.glob("*/stories")
        if path.is_dir()
    }
    if locale_dirs != set(OFFICIAL_LOCALES):
        raise ValueError("Localized Web Story directories must match 50 locales")

    localizations_by_key = {
        key: validated_localizations(key)
        for key in keys
    }
    validate_index(PAGES / "stories" / "index.html", keys)
    for key in keys:
        validate_story(PAGES / "stories" / f"{key}.html", key)
    for locale in OFFICIAL_LOCALES:
        stories = PAGES / locale / "stories"
        locale_keys = {
            path.stem
            for path in stories.glob("*.html")
            if path.name != "index.html"
        }
        if locale_keys != expected_keys:
            raise ValueError(f"{locale}: Stories do not match live apps")
        validate_index(stories / "index.html", keys, locale)
        for key in keys:
            validate_story(
                stories / f"{key}.html",
                key,
                locale,
                localizations_by_key[key][locale],
            )
    if not (PAGES / "stories" / "img" / "publisher-logo.jpg").is_file():
        raise FileNotFoundError("Missing Web Story publisher logo")
    for key in keys:
        poster = PAGES / "stories" / "img" / f"{key}-poster.jpg"
        if not poster.is_file() or poster.stat().st_size == 0:
            raise FileNotFoundError(f"Missing Web Story poster for {key}")
    sitemap_urls = validate_sitemap(keys)
    return {
        "apps": len(keys),
        "locales": len(OFFICIAL_LOCALES),
        "localized_stories": len(keys) * len(OFFICIAL_LOCALES),
        "sitemap_urls": sitemap_urls,
    }


def main():
    result = validate_site()
    print(
        "✓ Web Stories gate: "
        f"apps={result['apps']} locales={result['locales']} "
        f"localized_stories={result['localized_stories']} "
        f"sitemap_urls={result['sitemap_urls']}"
    )


if __name__ == "__main__":
    main()
