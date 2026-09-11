#!/usr/bin/env python3
"""Source-bound, exact-locale syndication for the canonical live App roster.

Only owned feeds, their directory, sitemap and marked directory-head discovery
links are written. App pages, conversion routes, ASC and social are never written.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import email.utils
from functools import lru_cache
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import regex

from live_app_manifest import canonical_manifest
from official_locales import OFFICIAL_LOCALES, require_official_locale_coverage
from rsscloud_config import (
    RSSCLOUD_DOMAIN, RSSCLOUD_NOTIFY_PATH, RSSCLOUD_PORT, RSSCLOUD_PROTOCOL,
)
from site_config import PUBLIC_SITE
from websub_config import WEBSUB_HUBS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
from videogen.registry import APPS, APPSTORE  # noqa: E402

SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
SCHEMA = "lumi.owned-app-feeds/v1"
INDEX = Path("feeds/owned-apps.json")
DIRECTORY = Path("feeds/index.html")
SITEMAP = Path("sitemap_owned_feeds.xml")
CATALOG = Path("api/v1/ios-app-catalog")
FORMATS = {
    "atom": ("feed.xml", "application/atom+xml"),
    "rss": ("rss.xml", "application/rss+xml"),
    "json_feed": ("feed.json", "application/feed+json"),
}
SERVED_TYPES = {
    "atom": ("application/atom+xml", "application/xml", "text/xml"),
    "rss": ("application/rss+xml", "application/xml", "text/xml"),
    "json_feed": ("application/feed+json", "application/json"),
}
MAX_FEED_BYTES = 400_000
ATOM = "http://www.w3.org/2005/Atom"
XML = "http://www.w3.org/XML/1998/namespace"
MODELS = {"paid_upfront", "free_with_lifetime_unlock"}
DISCLOSURE = (
    "This is first-party material published by Lumi Studio, the developer of "
    "every listed app."
)
PURCHASE_LABELS = {
    "paid_upfront": "Paid download",
    "free_with_lifetime_unlock": "Free to start · one-time unlock",
}
HEAD_START = "<!-- owned-app-feeds:discovery:start -->"
HEAD_END = "<!-- owned-app-feeds:discovery:end -->"
ROOT_LINK = (
    '<p data-owned-app-feeds="directory"><a href="'
    + SITE + '/feeds/index.html">RSS · Atom · JSON Feed</a></p>'
)
PRICE = re.compile(
    r"[$€£¥₹₩₽₺₫₱]\s*\d|\d[\d.,]*\s*(?:USD|EUR|GBP|CAD|AUD|€|\$)\b"
)
SHA256 = re.compile(r"[0-9a-f]{64}")
MIN_NATIVE_SCRIPT_RATIO = 0.60
NATIVE_SCRIPTS = {
    "ar-SA": ("Arabic",), "bn-BD": ("Bengali",), "el": ("Greek",),
    "gu-IN": ("Gujarati",), "he": ("Hebrew",), "hi": ("Devanagari",),
    "ja": ("Han", "Hiragana", "Katakana"), "kn-IN": ("Kannada",),
    "ko": ("Hangul",), "ml-IN": ("Malayalam",), "mr-IN": ("Devanagari",),
    "or-IN": ("Oriya",), "pa-IN": ("Gurmukhi",), "ru": ("Cyrillic",),
    "ta-IN": ("Tamil",), "te-IN": ("Telugu",), "th": ("Thai",),
    "uk": ("Cyrillic",), "ur-PK": ("Arabic",),
    "zh-Hans": ("Han", "Bopomofo"), "zh-Hant": ("Han", "Bopomofo"),
}
LATIN_BRANDS = ("Lumi Studio", "Lumi", "App Store", "Apple Watch",
                "iPhone", "iPad", "iOS", "Apple")
SCRIPT_NEUTRAL = regex.compile(r"[\p{Script=Common}\p{Script=Inherited}]")
SCRIPT_LETTERS = regex.compile(r"\p{L}")
SCRIPT_TEXT = regex.compile(r"[\p{L}\p{M}]")
LATIN_BRAND = regex.compile(r"[\p{Script=Latin}\p{N}\p{P}\p{Zs}\p{S}]+")
PAID_FREE_TERMS = {
    "ar": r"مجاني|مجانًا", "bn": r"বিনামূল্য|বিনা মূল্যে",
    "ca": r"\bgratuït", "cs": r"\bzdarma\b", "da": r"\bgratis\b",
    "de": r"\bkostenlos", "el": r"δωρεάν",
    "en": r"(?<![\w-])free(?![\w-])", "es": r"\bgratis\b|\bgratuit",
    "fi": r"\bilmais|\bilmainen\b", "fr": r"\bgratuit",
    "gu": r"મફત", "he": r"חינם", "hi": r"मुफ़्त|मुफ्त|निःशुल्क",
    "hr": r"\bbesplat", "hu": r"\bingyen", "id": r"\bgratis\b",
    "it": r"\bgratis\b|\bgratuit", "ja": r"無料", "kn": r"ಉಚಿತ",
    "ko": r"무료", "ml": r"സൗജന്യ", "mr": r"मोफत", "ms": r"\bpercuma\b",
    "nl": r"\bgratis\b", "no": r"\bgratis\b", "or": r"ମାଗଣା",
    "pa": r"ਮੁਫ਼ਤ|ਮੁਫਤ", "pl": r"\bbezpłat|\bdarmo\b",
    "pt": r"\bgrátis\b|\bgratuit", "ro": r"\bgratuit", "ru": r"бесплатн",
    "sk": r"\bzadarmo\b|\bbezplat", "sl": r"\bbrezplač",
    "sv": r"\bgratis\b|\bkostnadsfri", "ta": r"இலவச", "te": r"ఉచిత",
    "th": r"ฟรี", "tr": r"\bücretsiz", "uk": r"безкоштовн",
    "ur": r"مفت", "vi": r"miễn phí", "zh": r"免費|免费",
}


class FeedError(ValueError):
    pass


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FeedError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique)


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n").encode("utf-8")


def text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FeedError(f"Missing text: {field}")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in value):
        raise FeedError(f"Invalid XML control character: {field}")
    return " ".join(value.split())


@lru_cache(maxsize=8192)
def _script_assessment(value: str, scripts: tuple[str, ...],
                       brands: tuple[str, ...], calculate_ratio: bool):
    native = regex.compile("[" + "".join(r"\p{Script=" + s + "}" for s in scripts) + "]")
    allowed = regex.compile(
        r"[\p{Script=Latin}\p{Script=Common}\p{Script=Inherited}"
        + "".join(r"\p{Script=" + s + "}" for s in scripts) + "]"
    )
    normalized = unicodedata.normalize("NFKC", value)
    foreign = tuple(sorted({c for c in SCRIPT_TEXT.findall(normalized)
                            if not allowed.fullmatch(c)}))
    if foreign or not calculate_ratio:
        return foreign, None
    # Brand exemptions affect the ratio only; they cannot hide foreign script.
    for brand in brands:
        brand = unicodedata.normalize("NFKC", brand).strip()
        if brand and LATIN_BRAND.fullmatch(brand):
            normalized = re.sub(
                r"(?<![A-Za-z0-9])" + re.escape(brand) + r"(?![A-Za-z0-9])",
                "", normalized, flags=re.I,
            )
    letters = [c for c in SCRIPT_LETTERS.findall(normalized) if not SCRIPT_NEUTRAL.fullmatch(c)]
    ratio = sum(bool(native.fullmatch(c)) for c in letters) / len(letters) if letters else 0.0
    return foreign, ratio


def require_locale_script(value: str, locale: str, field: str, *,
                          brands=(), require_native: bool = True) -> float | None:
    if locale not in OFFICIAL_LOCALES:
        raise FeedError(f"Unsupported script-gate locale: {locale}")
    scripts = NATIVE_SCRIPTS.get(locale, ("Latin",))
    brand_key = tuple(sorted(set((*LATIN_BRANDS, *brands)), key=lambda v: (-len(v), v)))
    foreign, ratio = _script_assessment(
        value, scripts, brand_key, locale in NATIVE_SCRIPTS and require_native,
    )
    if foreign:
        codes = ",".join(f"U+{ord(c):04X}" for c in foreign[:8])
        raise FeedError(f"Foreign script in {locale}/{field}: {codes}")
    if ratio is not None and ratio < MIN_NATIVE_SCRIPT_RATIO:
        raise FeedError(
            f"Native script ratio below {MIN_NATIVE_SCRIPT_RATIO:.0%} in "
            f"{locale}/{field}: {ratio:.1%}"
        )
    return ratio


def timestamp(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise FeedError(f"Invalid feed timestamp: {value!r}")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def relative(locale: str, fmt: str) -> Path:
    if locale not in OFFICIAL_LOCALES or fmt not in FORMATS:
        raise FeedError(f"Unsupported feed: {locale}/{fmt}")
    return Path(locale) / FORMATS[fmt][0]


def feed_url(locale: str, fmt: str) -> str:
    return f"{SITE}/{relative(locale, fmt).as_posix()}"


def item_id(app_id: str, locale: str) -> str:
    return f"urn:lumi:app-store:{app_id}:locale:{locale}"


def _copy(source: Path) -> dict:
    publisher = read_json(source / "publisher_intent_catalog_i18n.json")
    finder = read_json(source / "portfolio_app_finder_i18n.json")
    for label, document in (("publisher", publisher), ("finder", finder)):
        if document.get("schema_version") != 1:
            raise FeedError(f"Invalid {label} i18n schema")
        require_official_locale_coverage(label, document.get("localizations", {}))
    result = {}
    for locale in OFFICIAL_LOCALES:
        p = publisher["localizations"][locale]
        f = finder["localizations"][locale]
        result[locale] = {
            "disclosure": text(p.get(DISCLOSURE), f"{locale}/disclosure"),
            "cta": text(f.get("View on the App Store"), f"{locale}/CTA"),
            "purchase_labels": {
                model: text(p.get(label), f"{locale}/{model}")
                for model, label in PURCHASE_LABELS.items()
            },
        }
        if not locale.startswith("en-") and (
            result[locale]["disclosure"] == DISCLOSURE
            or result[locale]["cta"] == "View on the App Store"
        ):
            raise FeedError(f"English wrapper fallback: {locale}")
        for field in ("disclosure", "cta"):
            require_locale_script(result[locale][field], locale, field)
        for model, label in result[locale]["purchase_labels"].items():
            require_locale_script(label, locale, model)
    return result


def _app_store_url(value, app_id: str) -> str:
    value = text(value, "App Store URL")
    parsed = urllib.parse.urlsplit(value)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https" or parsed.netloc != "apps.apple.com"
        or parsed.fragment
        or not re.fullmatch(r"/(?:[a-z]{2}/)?app/id" + re.escape(app_id), parsed.path)
        or set(query) != {"pt", "ct", "mt"}
        or any(len(v) != 1 for v in query.values())
        or not query["pt"][0].isdigit()
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", query["ct"][0])
        or query["mt"] != ["8"]
    ):
        raise FeedError(f"Invalid attributed App Store URL: {app_id}")
    return value


def load_sources(pages: Path, source: Path = HERE) -> tuple[dict, dict]:
    roster = canonical_manifest()
    copies = _copy(source)
    expected = set(roster["apps"])
    files = {p.stem for p in (pages / CATALOG / "locales").glob("*.json")}
    require_official_locale_coverage("owned feed source", files)
    result = {}
    for locale in OFFICIAL_LOCALES:
        catalog = read_json(pages / CATALOG / "locales" / f"{locale}.json")
        source_feed = read_json(pages / CATALOG / "feeds" / f"{locale}.json")
        apps = catalog.get("apps", [])
        if (
            catalog.get("locale") != locale
            or catalog.get("record_count") != len(expected)
            or source_feed.get("language") != locale
            or not isinstance(apps, list) or len(apps) != len(expected)
        ):
            raise FeedError(f"Locale/catalog count drift: {locale}")
        by_key = {}
        for app in apps:
            key = app.get("key")
            if key in by_key or key not in expected:
                raise FeedError(f"Duplicate/non-roster App: {locale}/{key}")
            app_id = roster["apps"][key]["app_id"]
            model = app.get("purchase_model")
            if (
                str(app.get("app_store_id")) != app_id
                or str(APPSTORE.get(key)) != app_id
                or model not in MODELS or model != APPS[key].get("purchase_model")
                or app.get("one_time_option") is not True
            ):
                raise FeedError(f"App identity/purchase model drift: {locale}/{key}")
            canonical = f"{SITE}/{locale}/{key}.html"
            if app.get("guide_url") != canonical:
                raise FeedError(f"Canonical locale drift: {locale}/{key}")
            summary = text(app.get("summary"), f"{locale}/{key}/summary")
            name = text(app.get("name"), f"{locale}/{key}/name")
            brands = (roster["apps"][key]["name"], APPS[key]["name"], name)
            require_locale_script(summary, locale, f"{key}/summary", brands=brands)
            require_locale_script(name, locale, f"{key}/name", require_native=False)
            if PRICE.search(summary):
                raise FeedError(f"Literal price in native summary: {locale}/{key}")
            if model == "paid_upfront" and re.search(
                PAID_FREE_TERMS[locale.split("-")[0]], summary, re.I
            ):
                raise FeedError(f"Free claim on paid download: {locale}/{key}")
            copy = copies[locale]
            by_key[key] = {
                "id": item_id(app_id, locale),
                "url": canonical,
                "external_url": _app_store_url(app.get("app_store_url"), app_id),
                "title": name,
                "summary": summary,
                "language": locale,
                "_owned_app": {
                    "app_key": key,
                    "app_store_id": app_id,
                    "canonical_app_store_url": f"https://apps.apple.com/app/id{app_id}",
                    "purchase_model": model,
                    "purchase_label": copy["purchase_labels"][model],
                    "free_core_available": model == "free_with_lifetime_unlock",
                    "one_time_purchase": True,
                    "publisher_disclosure": copy["disclosure"],
                    "app_store_cta_label": copy["cta"],
                    "source_locale": locale,
                    "source_catalog": f"{SITE}/{CATALOG}/locales/{locale}.json",
                    "independent_ranking": False,
                },
            }
        if set(by_key) != expected:
            raise FeedError(f"Incomplete App roster: {locale}")
        result[locale] = {
            "title": text(source_feed.get("title"), f"{locale}/feed title"),
            "disclosure": copies[locale]["disclosure"],
            "items": [by_key[key] for key in sorted(by_key)],
        }
        require_locale_script(result[locale]["title"], locale, "feed title",
                              require_native=False)
    english = {i["_owned_app"]["app_key"]: i["summary"]
               for i in result["en-US"]["items"]}
    for locale, channel in result.items():
        if not locale.startswith("en-"):
            for item in channel["items"]:
                if item["summary"] == english[item["_owned_app"]["app_key"]]:
                    raise FeedError(f"English summary fallback: {locale}/{item['id']}")
    return roster, result


def _content(item: dict) -> str:
    facts = item["_owned_app"]
    return (
        f'<p>{html.escape(item["summary"])}</p>'
        f'<p>{html.escape(facts["purchase_label"])}</p>'
        f'<p><a href="{html.escape(item["external_url"], quote=True)}">'
        f'{html.escape(facts["app_store_cta_label"])}</a></p>'
        f'<p>{html.escape(facts["publisher_disclosure"])}</p>'
    )


def _previous(pages: Path, locale: str) -> dict:
    path = pages / relative(locale, "json_feed")
    if not path.exists():
        return {}
    feed = read_json(path)
    if feed.get("language") != locale or feed.get("_owned_feed", {}).get("schema") != SCHEMA:
        raise FeedError(f"Refusing to overwrite an unowned feed: {path}")
    result = {}
    for item in feed.get("items", []):
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in result:
            raise FeedError(f"Duplicate/invalid previous item: {locale}")
        timestamp(item.get("date_published"))
        timestamp(item.get("date_modified"))
        if item["date_published"] > item["date_modified"]:
            raise FeedError(f"Reversed previous item dates: {identifier}")
        result[identifier] = item
    return result


def json_feed(locale: str, channel: dict, previous: dict, now: str) -> dict:
    items = []
    for record in channel["items"]:
        item = json.loads(json.dumps(record, ensure_ascii=False))
        item["content_html"] = _content(item)
        item["content_text"] = "\n\n".join((
            item["summary"], item["_owned_app"]["purchase_label"],
            item["_owned_app"]["app_store_cta_label"] + ": " + item["external_url"],
            item["_owned_app"]["publisher_disclosure"],
        ))
        content_digest = digest(item)
        old = previous.get(item["id"], {})
        comparable = json.loads(json.dumps(old))
        for field in ("date_published", "date_modified"):
            comparable.pop(field, None)
        old_digest = comparable.get("_owned_app", {}).pop("content_digest", None)
        if old and (old_digest != digest(comparable) or not SHA256.fullmatch(old_digest or "")):
            raise FeedError(f"Previous item content digest mismatch: {item['id']}")
        if old.get("date_modified", "") > now:
            raise FeedError(f"Previous feed is from the future: {item['id']}")
        modified = now
        if old_digest == content_digest:
            modified = old["date_modified"]
        item["_owned_app"]["content_digest"] = content_digest
        item["date_published"] = old.get("date_published", modified)
        item["date_modified"] = modified
        items.append(item)
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": channel["title"],
        "home_page_url": f"{SITE}/{locale}/index.html",
        "feed_url": feed_url(locale, "json_feed"),
        "description": channel["disclosure"],
        "language": locale,
        "authors": [{"name": "Lumi Studio", "url": f"{SITE}/about.html"}],
        "hubs": [{"type": "WebSub", "url": hub} for hub in WEBSUB_HUBS],
        "_owned_feed": {
            "schema": SCHEMA,
            "source_digest": digest(channel),
            "item_count": len(items),
            "last_modified": max(item["date_modified"] for item in items),
        },
        "items": items,
    }


def _xml_document(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def atom_feed(feed: dict) -> bytes:
    locale = feed["language"]
    root = ET.Element("feed", {"xmlns": ATOM, "xml:lang": locale})
    ET.SubElement(root, "id").text = feed_url(locale, "atom")
    ET.SubElement(root, "title").text = feed["title"]
    ET.SubElement(root, "subtitle").text = feed["description"]
    ET.SubElement(root, "updated").text = feed["_owned_feed"]["last_modified"]
    ET.SubElement(root, "link", {"rel": "self", "type": FORMATS["atom"][1],
                               "href": feed_url(locale, "atom")})
    ET.SubElement(root, "link", {"rel": "alternate", "type": "text/html",
                               "href": feed["home_page_url"], "hreflang": locale})
    for hub in WEBSUB_HUBS:
        ET.SubElement(root, "link", {"rel": "hub", "href": hub})
    author = ET.SubElement(root, "author")
    ET.SubElement(author, "name").text = "Lumi Studio"
    ET.SubElement(author, "uri").text = f"{SITE}/about.html"
    for item in feed["items"]:
        entry = ET.SubElement(root, "entry", {"xml:lang": locale})
        for field, value in (
            ("id", item["id"]), ("title", item["title"]),
            ("published", item["date_published"]), ("updated", item["date_modified"]),
        ):
            ET.SubElement(entry, field).text = value
        ET.SubElement(entry, "link", {"rel": "alternate", "href": item["url"],
                                     "type": "text/html", "hreflang": locale})
        ET.SubElement(entry, "link", {"rel": "related", "href": item["external_url"]})
        ET.SubElement(entry, "content", {"type": "html"}).text = item["content_html"]
    return _xml_document(root)


def _rss_date(value: str) -> str:
    return email.utils.format_datetime(
        datetime.fromisoformat(value.replace("Z", "+00:00")), usegmt=True
    )


def rss_feed(feed: dict) -> bytes:
    locale = feed["language"]
    root = ET.Element("rss", {"version": "2.0", "xmlns:atom": ATOM})
    channel = ET.SubElement(root, "channel")
    for key, value in (
        ("title", feed["title"]), ("link", feed["home_page_url"]),
        ("description", feed["description"]), ("language", locale),
        ("lastBuildDate", _rss_date(feed["_owned_feed"]["last_modified"])),
    ):
        ET.SubElement(channel, key).text = value
    ET.SubElement(channel, "atom:link", {"rel": "self", "type": FORMATS["rss"][1],
                                        "href": feed_url(locale, "rss")})
    for hub in WEBSUB_HUBS:
        ET.SubElement(channel, "atom:link", {"rel": "hub", "href": hub})
    ET.SubElement(channel, "cloud", {
        "domain": RSSCLOUD_DOMAIN, "port": RSSCLOUD_PORT,
        "path": RSSCLOUD_NOTIFY_PATH, "registerProcedure": "",
        "protocol": RSSCLOUD_PROTOCOL,
    })
    for item in feed["items"]:
        node = ET.SubElement(channel, "item")
        ET.SubElement(node, "guid", {"isPermaLink": "false"}).text = item["id"]
        ET.SubElement(node, "title").text = item["title"]
        ET.SubElement(node, "link").text = item["url"]
        ET.SubElement(node, "description").text = item["content_html"]
        ET.SubElement(node, "pubDate").text = _rss_date(item["date_published"])
        ET.SubElement(node, "atom:updated").text = item["date_modified"]
    return _xml_document(root)


def discovery_links(locale: str, title: str) -> str:
    lines = [HEAD_START]
    for fmt, (_, media_type) in FORMATS.items():
        lines.append(
            f'<link rel="alternate" type="{media_type}" hreflang="{locale}" '
            f'title="{html.escape(title, quote=True)}" href="{feed_url(locale, fmt)}">'
        )
    lines.append(HEAD_END)
    return "\n".join(lines)


def _inject_head(raw: str, block: str) -> str:
    if raw.count(HEAD_START) != raw.count(HEAD_END) or raw.count(HEAD_START) > 1:
        raise FeedError("Invalid owned-feed discovery markers")
    heads = list(re.finditer(r"<head\b[^>]*>", raw, re.I))
    if len(heads) != 1 or len(re.findall(r"</head\s*>", raw, re.I)) != 1:
        raise FeedError("Locale directory lacks a unique HTML head")
    pattern = re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END)
    if HEAD_START in raw:
        preceding = raw[heads[0].end():raw.index(HEAD_START)]
        if not preceding.strip():
            return re.sub(pattern, lambda _: block, raw, count=1, flags=re.S)
        raw = re.sub(pattern + r"\n?", "", raw, count=1, flags=re.S)
    return re.sub(r"<head\b[^>]*>", lambda m: m.group() + "\n" + block + "\n",
                  raw, count=1, flags=re.I)


def _sitemap_index(raw: str, modified: str) -> str:
    url = f"{SITE}/{SITEMAP}"
    block = f"<sitemap><loc>{url}</loc><lastmod>{modified[:10]}</lastmod></sitemap>"
    parsed = ET.fromstring(raw)
    if parsed.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex":
        raise FeedError("Owned feeds require the existing sitemap index")
    pattern = r"<sitemap\b[^>]*>\s*<loc>" + re.escape(url) + r"</loc>.*?</sitemap>"
    matches = re.findall(pattern, raw, re.S)
    if len(matches) > 1:
        raise FeedError("Duplicate owned feed sitemap entry")
    if matches:
        return re.sub(pattern, lambda _: block, raw, flags=re.S)
    return raw.replace("</sitemapindex>", block + "\n</sitemapindex>")


def _directory(feeds: dict) -> bytes:
    sections = []
    for locale, feed in feeds.items():
        links = " · ".join(
            f'<a type="{mime}" href="{feed_url(locale, fmt)}">{label}</a>'
            for (fmt, (_, mime)), label in zip(
                FORMATS.items(), ("Atom", "RSS 2.0", "JSON Feed 1.1")
            )
        )
        sections.append(
            f'<section lang="{locale}" dir="auto"><h2>'
            f'{html.escape(feed["title"])} <small>{locale}</small></h2>'
            f'<p>{html.escape(feed["description"])}</p><p>{links}</p></section>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Lumi Studio · RSS · Atom · JSON Feed</title>'
        f'<link rel="canonical" href="{SITE}/{DIRECTORY}">'
        '<style>body{font:1rem/1.6 system-ui;max-width:64rem;margin:2rem auto;'
        'padding:0 1rem}a{overflow-wrap:anywhere}small{font-size:.8em}</style>'
        '</head><body><h1>Lumi Studio · RSS · Atom · JSON Feed</h1>'
        + "\n".join(sections)
        + f'<p><a href="{SITE}/{INDEX}">JSON</a></p></body></html>\n'
    ).encode("utf-8")


def render(pages: Path, *, source: Path = HERE, now: str | None = None) -> tuple[dict, dict]:
    now = timestamp(now or _now())
    roster, channels = load_sources(pages, source)
    outputs = {}
    feeds = {}
    metadata = {}
    for locale, channel in channels.items():
        feed = json_feed(locale, channel, _previous(pages, locale), now)
        feeds[locale] = feed
        raw = {"atom": atom_feed(feed), "rss": rss_feed(feed),
               "json_feed": json_bytes(feed)}
        for fmt, content in raw.items():
            if len(content) > MAX_FEED_BYTES:
                raise FeedError(f"Feed exceeds subscriber/audit byte limit: {locale}/{fmt}")
            content.decode("utf-8", errors="strict")
            outputs[relative(locale, fmt)] = content
        metadata[locale] = {
            "language": locale,
            "record_count": len(feed["items"]),
            "source_catalog": f"{SITE}/{CATALOG}/locales/{locale}.json",
            "source_digest": feed["_owned_feed"]["source_digest"],
            "last_modified": feed["_owned_feed"]["last_modified"],
            "app_keys": [i["_owned_app"]["app_key"] for i in feed["items"]],
            "formats": {
                fmt: {"url": feed_url(locale, fmt), "sha256": sha256(raw[fmt]),
                      "media_type": FORMATS[fmt][1],
                      "accepted_content_types": list(SERVED_TYPES[fmt])}
                for fmt in FORMATS
            },
        }
        path = Path(locale) / "index.html"
        outputs[path] = _inject_head(
            (pages / path).read_text(encoding="utf-8"),
            discovery_links(locale, feed["title"]),
        ).encode("utf-8")
    modified = max(f["_owned_feed"]["last_modified"] for f in feeds.values())
    index = {
        "schema": SCHEMA,
        "home_page_url": f"{SITE}/{DIRECTORY}",
        "roster_digest": roster["roster_digest"],
        "generation_digest": digest({
            "schema": SCHEMA, "roster": roster["roster_digest"],
            "sources": {loc: m["source_digest"] for loc, m in metadata.items()},
            "hubs": WEBSUB_HUBS, "rsscloud": (
                RSSCLOUD_DOMAIN, RSSCLOUD_PORT, RSSCLOUD_NOTIFY_PATH, RSSCLOUD_PROTOCOL
            ),
        }),
        "last_modified": modified,
        "app_count": len(roster["apps"]),
        "locale_count": len(OFFICIAL_LOCALES),
        "record_count": len(roster["apps"]) * len(OFFICIAL_LOCALES),
        "purchase_models": dict(sorted(Counter(
            APPS[key]["purchase_model"] for key in roster["apps"]
        ).items())),
        "feeds": metadata,
    }
    outputs[INDEX] = json_bytes(index)
    outputs[DIRECTORY] = _directory(feeds)
    root_index = (pages / "index.html").read_text(encoding="utf-8")
    if 'data-owned-app-feeds="directory"' not in root_index:
        if "</body>" not in root_index:
            raise FeedError("Root directory lacks an HTML body")
        root_index = root_index.replace("</body>", ROOT_LINK + "\n</body>", 1)
    outputs[Path("index.html")] = root_index.encode("utf-8")
    sm = ET.Element("urlset", {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    urls = [f"{SITE}/{DIRECTORY}", f"{SITE}/{INDEX}"]
    urls += [feed_url(loc, fmt) for loc in OFFICIAL_LOCALES for fmt in FORMATS]
    for url in sorted(urls):
        node = ET.SubElement(sm, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = modified[:10]
    outputs[SITEMAP] = _xml_document(sm)
    sitemap_index = Path(
        "sitemap_index.xml" if (pages / "sitemap_index.xml").is_file() else "sitemap.xml"
    )
    outputs[sitemap_index] = _sitemap_index(
        (pages / sitemap_index).read_text(encoding="utf-8"), modified
    ).encode("utf-8")
    return index, outputs


def write_if_changed(path: Path, content: bytes) -> bool:
    if path.is_file() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name("." + path.name + f".owned-feed-{os.getpid()}")
    try:
        staging.write_bytes(content)
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)
    return True


def build(pages: Path, *, check: bool = False, source: Path = HERE,
          now: str | None = None) -> dict:
    index, outputs = render(pages, source=source, now=now)
    changed = [str(path) for path, raw in outputs.items()
               if not (pages / path).is_file() or (pages / path).read_bytes() != raw]
    if check and changed:
        raise FeedError(f"Owned feed contract drift ({len(changed)} files): {changed[:8]}")
    if not check:
        for path, raw in outputs.items():
            write_if_changed(pages / path, raw)
    validate(pages, index)
    return {
        "apps": index["app_count"], "locales": index["locale_count"],
        "app_locale_pairs": index["record_count"],
        "feeds": index["locale_count"] * len(FORMATS),
        "purchase_models": index["purchase_models"], "duplicates": 0,
        "generation_digest": index["generation_digest"], "changed_files": len(changed),
    }


def validate(pages: Path, index: dict | None = None) -> dict:
    index = read_json(pages / INDEX) if index is None else index
    roster = canonical_manifest()
    if index.get("schema") != SCHEMA or index.get("roster_digest") != roster["roster_digest"]:
        raise FeedError("Owned feed index/roster drift")
    require_official_locale_coverage("owned feed index", index.get("feeds", {}))
    copies = _copy(HERE)
    ids = set()
    for locale in OFFICIAL_LOCALES:
        expected_ids = {item_id(a["app_id"], locale) for a in roster["apps"].values()}
        meta = index["feeds"][locale]
        if meta["language"] != locale or set(meta["app_keys"]) != set(roster["apps"]):
            raise FeedError(f"Owned feed coverage drift: {locale}")
        parsed = {}
        for fmt in FORMATS:
            raw = (pages / relative(locale, fmt)).read_bytes()
            if len(raw) > MAX_FEED_BYTES or sha256(raw) != meta["formats"][fmt]["sha256"]:
                raise FeedError(f"Owned feed hash/size drift: {locale}/{fmt}")
            raw.decode("utf-8", errors="strict")
            parsed[fmt] = (json.loads(raw, object_pairs_hook=_unique)
                           if fmt == "json_feed" else ET.fromstring(raw))
        feed = parsed["json_feed"]
        if (
            feed["language"] != locale or feed["feed_url"] != feed_url(locale, "json_feed")
            or feed["_owned_feed"]["source_digest"] != meta["source_digest"]
            or feed["description"] != copies[locale]["disclosure"]
            or feed.get("hubs") != [{"type": "WebSub", "url": hub} for hub in WEBSUB_HUBS]
            or len(feed["items"]) != len(expected_ids)
            or {i["id"] for i in feed["items"]} != expected_ids
        ):
            raise FeedError(f"JSON Feed locale/identity drift: {locale}")
        if ids.intersection(expected_ids):
            raise FeedError("Cross-locale duplicate item IDs")
        ids.update(expected_ids)
        atom = parsed["atom"]
        atom_self = atom.find(f"{{{ATOM}}}link[@rel='self']")
        if (
            atom.get(f"{{{XML}}}lang") != locale or atom_self is None
            or atom_self.get("href") != feed_url(locale, "atom")
            or atom.findtext(f"{{{ATOM}}}id") != feed_url(locale, "atom")
        ):
            raise FeedError(f"Atom language drift: {locale}")
        entries = atom.findall(f"{{{ATOM}}}entry")
        if (
            len(entries) != len(expected_ids)
            or {e.findtext(f"{{{ATOM}}}id") for e in entries} != expected_ids
            or any(e.get(f"{{{XML}}}lang") != locale for e in entries)
        ):
            raise FeedError(f"Atom identity/language drift: {locale}")
        rss = parsed["rss"].find("channel")
        if rss is None or rss.findtext("language") != locale:
            raise FeedError(f"RSS language drift: {locale}")
        rss_self = rss.find(f"{{{ATOM}}}link[@rel='self']")
        if rss_self is None or rss_self.get("href") != feed_url(locale, "rss"):
            raise FeedError(f"RSS self discovery drift: {locale}")
        rss_items = rss.findall("item")
        if len(rss_items) != len(expected_ids) or {
            e.findtext("guid") for e in rss_items
        } != expected_ids:
            raise FeedError(f"RSS item coverage drift: {locale}")
        atom_items = {e.findtext(f"{{{ATOM}}}id"): e for e in entries}
        rss_by_id = {e.findtext("guid"): e for e in rss_items}
        for item in feed["items"]:
            facts = item["_owned_app"]
            key = facts["app_key"]
            if (
                facts["app_store_id"] != roster["apps"][key]["app_id"]
                or facts["purchase_model"] != APPS[key]["purchase_model"]
                or facts["source_locale"] != locale or item["language"] != locale
                or facts["publisher_disclosure"] != copies[locale]["disclosure"]
                or facts["purchase_label"] != copies[locale]["purchase_labels"][facts["purchase_model"]]
                or facts["app_store_cta_label"] != copies[locale]["cta"]
                or facts["one_time_purchase"] is not True
                or facts["independent_ranking"] is not False
                or facts["free_core_available"] != (facts["purchase_model"] == "free_with_lifetime_unlock")
                or item["url"] != f"{SITE}/{locale}/{key}.html"
            ):
                raise FeedError(f"Item contract drift: {locale}/{key}")
            _app_store_url(item["external_url"], facts["app_store_id"])
            if (
                item["content_html"] != _content(item)
                or atom_items[item["id"]].findtext(f"{{{ATOM}}}content") != item["content_html"]
                or rss_by_id[item["id"]].findtext("description") != item["content_html"]
                or atom_items[item["id"]].find(f"{{{ATOM}}}link[@rel='alternate']").get("href") != item["url"]
                or rss_by_id[item["id"]].findtext("link") != item["url"]
            ):
                raise FeedError(f"Cross-format content drift: {locale}/{key}")
            timestamp(item["date_modified"])
            timestamp(item["date_published"])
    if len(ids) != index["record_count"]:
        raise FeedError("Owned feed matrix denominator drift")
    return index


def verify_deployed(pages: Path, *, opener=urllib.request.urlopen,
                    timeout: float = 20, workers: int = 6) -> dict:
    index = validate(pages)
    jobs = [(loc, fmt) for loc in OFFICIAL_LOCALES for fmt in FORMATS]

    def check(job):
        locale, fmt = job
        request = urllib.request.Request(feed_url(locale, fmt), headers={
            "User-Agent": "Lumi-Owned-Feed-Contract/1.0", "Cache-Control": "no-cache",
        })
        with opener(request, timeout=timeout) as response:
            if response.status != 200:
                raise FeedError(f"Feed HTTP status: {locale}/{fmt}/{response.status}")
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset()
            if content_type not in SERVED_TYPES[fmt] or (
                charset is not None and charset.casefold() not in {"utf-8", "utf8"}
            ):
                raise FeedError(f"Feed MIME/charset drift: {locale}/{fmt}")
            raw = response.read(MAX_FEED_BYTES + 1)
        raw.decode("utf-8", errors="strict")
        if sha256(raw) != index["feeds"][locale]["formats"][fmt]["sha256"]:
            raise FeedError(f"Deployed feed differs from source: {locale}/{fmt}")
        return True

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as pool:
        verified = sum(pool.map(check, jobs))
    return {"verified_feeds": verified, "app_locale_pairs": index["record_count"]}


def western_readback(pages: Path, matrix: Path) -> dict:
    rows = read_json(matrix)
    failed = [r for r in rows if r.get("surface") == "rss_owned"
              and r.get("status") == "FAIL"]
    roster = canonical_manifest()["apps"]
    for row in failed:
        locale = row["locale"]
        key = row.get("app", row.get("app_key"))
        raw = (pages / relative(locale, "atom")).read_text(encoding="utf-8")
        if roster[key]["app_id"] not in raw[:400000]:
            raise FeedError(f"Unresolved western rss_owned cell: {locale}/{key}")
    return {"baseline_rss_owned_failures": len(failed), "resolved": len(failed), "remaining": 0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=Path(os.environ.get("GEO_PAGES", HERE / "pages")))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-deployed", action="store_true")
    parser.add_argument("--western-matrix", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.pages_dir, check=args.check)
        if args.verify_deployed:
            result.update(verify_deployed(args.pages_dir))
        if args.western_matrix:
            result.update(western_readback(args.pages_dir, args.western_matrix))
    except (FeedError, ValueError, KeyError, OSError) as error:
        print(f"Owned feed contract failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
