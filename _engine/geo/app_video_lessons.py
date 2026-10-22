#!/usr/bin/env python3
"""Publish verified localized app walkthroughs as VideoObject resources."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import html
import json
import os
from pathlib import Path
import re
from typing import Any
import urllib.parse
import xml.etree.ElementTree as ET

from app_store_storefronts import (
    PROVIDER_TOKEN_ENV,
    campaign_app_store_url,
    normalize_app_store_campaign_url,
    validated_app_store_url,
)
from gen_feed import feed_discovery_links
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog
from site_config import PUBLIC_SITE  # noqa: E402


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE",
    PUBLIC_SITE,
).rstrip("/")
SOURCE_PATH = HERE / "app_video_lesson_sources.json"
I18N_PATH = HERE / "app_video_lesson_i18n.json"
SLUG = "lumi-studio-app-video-lessons"
DATA_RELATIVE = Path("data") / f"{SLUG}.json"
SCHEMA_RELATIVE = Path("data") / f"{SLUG}.schema.json"
SITEMAP_NAME = "sitemap_video_lessons.xml"
VIDEO_ROOT = Path("videos")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
VIDEO_NS = "http://www.google.com/schemas/sitemap-video/1.1"
TODAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
KEY_RE = re.compile(r"[a-z0-9]+")
VIDEO_PATH_RE = re.compile(r"/[a-z0-9]+\.mp4")
VIDEO_FILENAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.mp4")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
SOURCE_RECORD_REQUIRED_KEYS = frozenset(
    {
        "app_key",
        "locale",
        "video_url",
        "duration_seconds",
        "published_on",
    }
)
SOURCE_RECORD_OPTIONAL_KEYS = frozenset({"width", "height", "sha256"})
UI_STRINGS = (
    "App walkthroughs",
    "Short, publisher-authored walkthroughs of real app screens.",
    "Video walkthrough",
    "Watch video",
    "Open the app guide",
    "Available walkthroughs",
    "Every video uses real app screens and is free to watch.",
)


def data_url(site: str = SITE) -> str:
    return f"{site}/{DATA_RELATIVE.as_posix()}"


def schema_url(site: str = SITE) -> str:
    return f"{site}/{SCHEMA_RELATIVE.as_posix()}"


def sitemap_url(site: str = SITE) -> str:
    return f"{site}/{SITEMAP_NAME}"


def hub_relative(locale: str | None = None) -> Path:
    if locale is None:
        return VIDEO_ROOT / "index.html"
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported video hub locale: {locale}")
    return VIDEO_ROOT / locale / "index.html"


def hub_url(locale: str | None = None, site: str = SITE) -> str:
    return f"{site}/{hub_relative(locale).as_posix().removesuffix('index.html')}"


def page_relative(app_key: str, locale: str) -> Path:
    if locale not in OFFICIAL_LOCALES or KEY_RE.fullmatch(app_key) is None:
        raise ValueError(f"Invalid video lesson path: {locale}/{app_key}")
    return VIDEO_ROOT / locale / f"{app_key}.html"


def page_url(app_key: str, locale: str, site: str = SITE) -> str:
    return f"{site}/{page_relative(app_key, locale).as_posix()}"


def markdown_relative(app_key: str, locale: str) -> Path:
    return page_relative(app_key, locale).with_suffix(".md")


def markdown_url(app_key: str, locale: str, site: str = SITE) -> str:
    return f"{site}/{markdown_relative(app_key, locale).as_posix()}"


def _single_line(value: object) -> str:
    result = publisher_intent_catalog.single_line(str(value))
    if not result or "\n" in result or "\r" in result:
        raise ValueError("Video lesson text must be a non-empty single line")
    return result


def _video_url(value: object) -> str:
    url = _single_line(value)
    parsed = urllib.parse.urlsplit(url)
    site = urllib.parse.urlsplit(SITE)
    first_party_prefix = site.path.rstrip("/") + "/media/app-videos/"
    first_party_filename = (
        parsed.path.removeprefix(first_party_prefix)
        if parsed.path.startswith(first_party_prefix)
        else ""
    )
    approved_catbox = (
        parsed.netloc == "files.catbox.moe"
        and VIDEO_PATH_RE.fullmatch(parsed.path) is not None
    )
    approved_first_party = (
        parsed.netloc == site.netloc
        and VIDEO_FILENAME_RE.fullmatch(first_party_filename) is not None
    )
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.query
        or parsed.fragment
        or not (approved_catbox or approved_first_party)
    ):
        raise ValueError(f"Invalid public video URL: {url}")
    return url


def _duration_iso(seconds: float) -> str:
    value = f"{seconds:.3f}".rstrip("0").rstrip(".")
    return f"PT{value}S"


def _published_at(value: str) -> str:
    published = _date_value(value, "video publication date")
    return f"{published.isoformat()}T00:00:00+00:00"


def _date_value(value: str, label: str) -> date:
    if TODAY_RE.fullmatch(value) is None:
        raise ValueError(f"Invalid {label}: {value}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Invalid {label}: {value}") from error
    if parsed.isoformat() != value:
        raise ValueError(f"Invalid {label}: {value}")
    return parsed


def load_sources(path: Path = SOURCE_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Invalid video lesson source manifest")
    profile = payload.get("media_profile")
    records = payload.get("records")
    if (
        not isinstance(profile, dict)
        or profile.get("encoding_format") != "video/mp4"
        or profile.get("codec") != "h264"
        or not isinstance(profile.get("width"), int)
        or int(profile["width"]) <= 0
        or not isinstance(profile.get("height"), int)
        or int(profile["height"]) <= 0
        or not isinstance(records, list)
        or not records
    ):
        raise ValueError("Video lesson source media profile is invalid")

    pairs: set[tuple[str, str]] = set()
    urls: set[str] = set()
    normalized = []
    for source in records:
        if not isinstance(source, dict):
            raise ValueError("Video lesson source record fields are invalid")
        source_keys = set(source)
        if (
            not SOURCE_RECORD_REQUIRED_KEYS.issubset(source_keys)
            or not source_keys.issubset(
                SOURCE_RECORD_REQUIRED_KEYS | SOURCE_RECORD_OPTIONAL_KEYS
            )
        ):
            raise ValueError("Video lesson source record fields are invalid")
        app_key = _single_line(source["app_key"])
        locale = _single_line(source["locale"])
        video_url = _video_url(source["video_url"])
        published_on = _single_line(source["published_on"])
        published_date = _date_value(
            published_on,
            "video publication date",
        )
        duration = source["duration_seconds"]
        width = source.get("width", profile["width"])
        height = source.get("height", profile["height"])
        checksum = source.get("sha256")
        first_party = urllib.parse.urlsplit(video_url).netloc == urllib.parse.urlsplit(
            SITE
        ).netloc
        if (
            KEY_RE.fullmatch(app_key) is None
            or locale not in OFFICIAL_LOCALES
            or not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not 1 <= float(duration) <= 300
            or not isinstance(width, int)
            or isinstance(width, bool)
            or width <= 0
            or not isinstance(height, int)
            or isinstance(height, bool)
            or height <= 0
            or (
                checksum is not None
                and (
                    not isinstance(checksum, str)
                    or SHA256_RE.fullmatch(checksum) is None
                )
            )
            or (first_party and checksum is None)
        ):
            raise ValueError(f"Invalid video lesson source: {source}")
        pair = (locale, app_key)
        if pair in pairs or video_url in urls:
            raise ValueError(f"Duplicate video lesson source: {pair}")
        pairs.add(pair)
        urls.add(video_url)
        normalized.append(
            {
                "app_key": app_key,
                "locale": locale,
                "video_url": video_url,
                "duration_seconds": float(duration),
                "published_on": published_date.isoformat(),
                "width": width,
                "height": height,
                **({"sha256": checksum} if checksum is not None else {}),
            }
        )
    return {
        "schema_version": 1,
        "source_repository": _single_line(payload["source_repository"]),
        "source_document": _single_line(payload["source_document"]),
        "media_profile": dict(profile),
        "records": normalized,
    }


def load_i18n(
    represented_locales: set[str],
    path: Path = I18N_PATH,
) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    localizations = payload.get("localizations")
    if (
        payload.get("schema_version") != 1
        or payload.get("source_locale") != "en-US"
        or payload.get("strings") != list(UI_STRINGS)
        or not isinstance(localizations, dict)
        or not represented_locales.issubset(localizations)
        or "en-US" not in localizations
    ):
        raise ValueError("Video lesson UI locale coverage is invalid")
    expected = set(UI_STRINGS)
    for locale, mapping in localizations.items():
        if not isinstance(mapping, dict) or set(mapping) != expected:
            raise ValueError(f"Incomplete video lesson UI: {locale}")
        for source, value in mapping.items():
            if source not in expected or _single_line(value) != value:
                raise ValueError(f"Invalid video lesson UI value: {locale}/{source}")
    return localizations


def _publisher_intents(pages: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], int]:
    path = pages / "data" / f"{publisher_intent_catalog.SLUG}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if (
        not isinstance(records, list)
        or not isinstance(payload.get("app_count"), int)
        or payload["app_count"] <= 0
    ):
        raise ValueError(f"Invalid publisher intent catalog: {path}")
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"Invalid publisher intent record: {path}")
        pair = (str(record.get("locale")), str(record.get("app_key")))
        if pair in index:
            raise ValueError(f"Duplicate publisher intent record: {pair}")
        index[pair] = record
    return index, int(payload["app_count"])


def _campaign_token(locale: str) -> str:
    token = f"iag_video_{locale.replace('-', '_').lower()}"
    if len(token) > 30 or re.fullmatch(r"[a-z0-9_]+", token) is None:
        raise ValueError(f"Invalid video campaign token: {token}")
    return token


def _store_url(intent: dict[str, Any], locale: str) -> str:
    app_id = str(intent["app_store_id"])
    provider_token = os.environ.get(PROVIDER_TOKEN_ENV, "").strip()
    normalized = normalize_app_store_campaign_url(
        str(intent["app_store_url"]),
        provider_token=provider_token,
    )
    validated_app_store_url(normalized, expected_app_id=app_id)
    return campaign_app_store_url(
        normalized,
        _campaign_token(locale),
        provider_token=provider_token,
    )


def build_records(
    pages: Path,
    source_payload: dict[str, Any],
    *,
    site: str = SITE,
) -> tuple[list[dict[str, Any]], int]:
    intents, portfolio_app_count = _publisher_intents(pages)
    profile = source_payload["media_profile"]
    records = []
    for source in source_payload["records"]:
        locale = str(source["locale"])
        app_key = str(source["app_key"])
        intent = intents.get((locale, app_key))
        if intent is None or intent.get("verified_live") is not True:
            raise ValueError(
                f"Video source has no verified live publisher intent: "
                f"{locale}/{app_key}"
            )
        thumbnail_path = pages / "social" / "img" / f"{app_key}-share.jpg"
        if not thumbnail_path.is_file() or thumbnail_path.stat().st_size == 0:
            raise FileNotFoundError(
                f"Video lesson thumbnail is missing: {thumbnail_path}"
            )
        published_on = str(source["published_on"])
        title = _single_line(intent["publisher_query"])
        description = _single_line(intent["decision_context"])
        if len(title) > 100 or len(description) > 2048:
            raise ValueError(f"Video sitemap text is too long: {locale}/{app_key}")
        records.append(
            {
                "record_id": f"{locale}:{app_key}",
                "locale": locale,
                "app_key": app_key,
                "app_name": _single_line(intent["app_name"]),
                "app_store_id": str(intent["app_store_id"]),
                "publisher_query": title,
                "decision_context": description,
                "video_url": str(source["video_url"]),
                "thumbnail_url": f"{site}/social/img/{app_key}-share.jpg",
                "encoding_format": str(profile["encoding_format"]),
                "codec": str(profile["codec"]),
                "width": int(source["width"]),
                "height": int(source["height"]),
                "duration": _duration_iso(float(source["duration_seconds"])),
                "duration_seconds": float(source["duration_seconds"]),
                "published_on": published_on,
                "published_at": _published_at(published_on),
                **(
                    {"content_sha256": str(source["sha256"])}
                    if source.get("sha256")
                    else {}
                ),
                "page_url": page_url(app_key, locale, site),
                "markdown_url": markdown_url(app_key, locale, site),
                "hub_url": hub_url(locale, site),
                "canonical_guide_url": str(intent["canonical_guide_url"]),
                "canonical_app_store_url": str(
                    intent["canonical_app_store_url"]
                ),
                "app_store_url": _store_url(intent, locale),
                "app_store_cta_label": _single_line(
                    intent["app_store_cta_label"]
                ),
                "publisher_disclosure": _single_line(
                    intent["publisher_disclosure"]
                ),
                "publisher_authored": True,
                "uses_real_app_screens": True,
                "verified_live": True,
            }
        )
    locale_rank = {locale: rank for rank, locale in enumerate(OFFICIAL_LOCALES)}
    records.sort(
        key=lambda record: (
            locale_rank[str(record["locale"])],
            str(record["app_name"]).casefold(),
            str(record["app_key"]),
        )
    )
    return records, portfolio_app_count


def _content_digest(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(
            records,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _generation_digest(content_digest: str, source_path: Path) -> str:
    digest = hashlib.sha256(content_digest.encode("ascii"))
    digest.update(source_path.read_bytes())
    digest.update(I18N_PATH.read_bytes())
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()


def _stable_modified(path: Path, generation_digest: str, today: str) -> str:
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return today
    modified = previous.get("dateModified")
    if previous.get("generation_digest") == generation_digest and isinstance(
        modified,
        str,
    ):
        try:
            modified_date = _date_value(modified, "stored modified date")
            today_date = _date_value(today, "video lesson build date")
        except ValueError:
            return today
        if modified_date <= today_date:
            return modified_date.isoformat()
    return today


def dataset_payload(
    records: list[dict[str, Any]],
    source_payload: dict[str, Any],
    portfolio_app_count: int,
    modified: str,
    content_digest: str,
    generation_digest: str,
    *,
    site: str = SITE,
) -> dict[str, Any]:
    apps = sorted({str(record["app_key"]) for record in records})
    campaign_states = []
    for record in records:
        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(str(record["app_store_url"])).query
        )
        campaign_states.append(
            bool(query.get("pt"))
            and bool(query.get("ct"))
            and query.get("mt") == ["8"]
        )
    if any(campaign_states) and not all(campaign_states):
        raise ValueError("Video App Store campaign attribution is inconsistent")
    campaign_ready = all(campaign_states)
    represented = [
        locale
        for locale in OFFICIAL_LOCALES
        if any(record["locale"] == locale for record in records)
    ]
    return {
        "$schema": schema_url(site),
        "name": "Lumi Studio App Video Lessons",
        "description": (
            "Publisher-authored localized walkthroughs built from real screens "
            "of verified live iOS apps."
        ),
        "identifier": data_url(site),
        "url": hub_url(None, site),
        "dateModified": modified,
        "content_digest": content_digest,
        "generation_digest": generation_digest,
        "license": publisher_intent_catalog.LICENSE_URL,
        "license_scope": "Metadata only; embedded videos remain publisher media.",
        "creator": {
            "@type": "Organization",
            "name": "Lumi Studio",
            "url": site,
        },
        "source": {
            "repository": source_payload["source_repository"],
            "document": source_payload["source_document"],
        },
        "app_store_link_policy": (
            "attributed_direct"
            if campaign_ready
            else "clean_direct_until_provider_token_available"
        ),
        "campaign_link_attribution_ready": campaign_ready,
        "coverage_status": "incremental_publisher_video_archive",
        "official_apple_locale_count": len(OFFICIAL_LOCALES),
        "portfolio_app_count": portfolio_app_count,
        "app_count": len(apps),
        "locale_count": len(represented),
        "video_count": len(records),
        "apps": apps,
        "locales": represented,
        "publisher_authored": True,
        "uses_real_app_screens": True,
        "is_ranking": False,
        "records": records,
    }


def schema_payload(site: str = SITE) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_url(site),
        "title": "Lumi Studio App Video Lessons",
        "type": "object",
        "required": [
            "name",
            "dateModified",
            "app_store_link_policy",
            "campaign_link_attribution_ready",
            "coverage_status",
            "portfolio_app_count",
            "app_count",
            "locale_count",
            "video_count",
            "records",
        ],
        "properties": {
            "name": {"const": "Lumi Studio App Video Lessons"},
            "dateModified": {"type": "string", "format": "date"},
            "app_store_link_policy": {
                "enum": [
                    "attributed_direct",
                    "clean_direct_until_provider_token_available",
                ]
            },
            "campaign_link_attribution_ready": {"type": "boolean"},
            "coverage_status": {
                "const": "incremental_publisher_video_archive"
            },
            "portfolio_app_count": {"type": "integer", "minimum": 1},
            "app_count": {"type": "integer", "minimum": 1},
            "locale_count": {"type": "integer", "minimum": 1, "maximum": 50},
            "video_count": {"type": "integer", "minimum": 1},
            "records": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "record_id",
                        "locale",
                        "app_key",
                        "app_store_id",
                        "video_url",
                        "thumbnail_url",
                        "duration",
                        "published_at",
                        "page_url",
                        "app_store_url",
                        "verified_live",
                    ],
                    "properties": {
                        "record_id": {"type": "string"},
                        "locale": {"enum": list(OFFICIAL_LOCALES)},
                        "app_key": {
                            "type": "string",
                            "pattern": "^[a-z0-9]+$",
                        },
                        "app_store_id": {
                            "type": "string",
                            "pattern": "^[0-9]+$",
                        },
                        "video_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "thumbnail_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "duration": {
                            "type": "string",
                            "pattern": "^PT[0-9]+(?:\\.[0-9]+)?S$",
                        },
                        "published_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "page_url": {"type": "string", "format": "uri"},
                        "app_store_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "verified_live": {"const": True},
                        "content_sha256": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{64}$",
                        },
                    },
                },
            },
        },
    }


def _json_script(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")


def structured_data(record: dict[str, Any], site: str = SITE) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "@id": f"{record['page_url']}#video",
        "url": record["page_url"],
        "name": record["publisher_query"],
        "description": record["decision_context"],
        "thumbnailUrl": record["thumbnail_url"],
        "uploadDate": record["published_at"],
        "datePublished": record["published_at"],
        "duration": record["duration"],
        "contentUrl": record["video_url"],
        "encodingFormat": record["encoding_format"],
        "width": record["width"],
        "height": record["height"],
        "inLanguage": record["locale"],
        "isAccessibleForFree": True,
        "isFamilyFriendly": True,
        "publisher": {
            "@type": "Organization",
            "@id": f"{site}/#organization",
            "name": "Lumi Studio",
            "url": site,
        },
        "isPartOf": {
            "@type": "Dataset",
            "@id": data_url(site),
            "name": "Lumi Studio App Video Lessons",
        },
        "about": {
            "@type": "MobileApplication",
            "name": record["app_name"],
            "operatingSystem": "iOS",
            "identifier": {
                "@type": "PropertyValue",
                "propertyID": "App Store ID",
                "value": record["app_store_id"],
            },
            "url": record["canonical_guide_url"],
            "downloadUrl": record["app_store_url"],
        },
        "potentialAction": [
            {
                "@type": "WatchAction",
                "target": record["page_url"],
            },
            {
                "@type": "InstallAction",
                "target": record["app_store_url"],
            },
        ],
    }


def _alternate_links(
    record: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    siblings = [
        candidate
        for candidate in records
        if candidate["app_key"] == record["app_key"]
    ]
    links = [
        f'<link rel="alternate" hreflang="{html.escape(str(candidate["locale"]), quote=True)}" '
        f'href="{html.escape(str(candidate["page_url"]), quote=True)}">'
        for candidate in siblings
    ]
    default = next(
        (
            candidate
            for candidate in siblings
            if candidate["locale"] == "en-US"
        ),
        siblings[0],
    )
    links.append(
        '<link rel="alternate" hreflang="x-default" '
        f'href="{html.escape(str(default["page_url"]), quote=True)}">'
    )
    return "\n".join(links)


def render_page(
    record: dict[str, Any],
    records: list[dict[str, Any]],
    ui: dict[str, str],
    modified: str,
) -> str:
    locale = str(record["locale"])
    direction = "rtl" if locale in publisher_intent_catalog.RTL_LOCALES else "ltr"
    esc = lambda value: html.escape(str(value), quote=True)
    schema = _json_script(structured_data(record))
    return f"""<!doctype html>
<html lang="{esc(locale)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(record["decision_context"])}">
<meta name="content-modified" content="{esc(modified)}">
<meta name="apple-itunes-app" content="app-id={esc(record["app_store_id"])}">
<meta property="og:type" content="video.other">
<meta property="og:title" content="{esc(record["publisher_query"])}">
<meta property="og:description" content="{esc(record["decision_context"])}">
<meta property="og:url" content="{esc(record["page_url"])}">
<meta property="og:image" content="{esc(record["thumbnail_url"])}">
<meta property="og:video" content="{esc(record["video_url"])}">
<meta property="og:video:secure_url" content="{esc(record["video_url"])}">
<meta property="og:video:type" content="video/mp4">
<meta property="og:video:width" content="{record["width"]}">
<meta property="og:video:height" content="{record["height"]}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(record["publisher_query"])}">
<meta name="twitter:description" content="{esc(record["decision_context"])}">
<meta name="twitter:image" content="{esc(record["thumbnail_url"])}">
<title>{html.escape(str(record["publisher_query"]))} | {html.escape(str(record["app_name"]))}</title>
<link rel="canonical" href="{esc(record["page_url"])}">
<link rel="alternate" type="text/markdown" href="{esc(record["markdown_url"])}">
<link rel="alternate" type="application/json" href="{esc(data_url())}">
<link rel="alternate" type="video/mp4" href="{esc(record["video_url"])}">
{_alternate_links(record, records)}
{feed_discovery_links()}
<script type="application/ld+json">{schema}</script>
<style>
:root{{--bg:#080b16;--card:#12182a;--ink:#f7f8ff;--muted:#c5cce5;--line:rgba(255,255,255,.12);--brand:#8b5cf6;--brand2:#38bdf8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100svh;color:var(--ink);background:radial-gradient(circle at 85% 5%,rgba(56,189,248,.18),transparent 28rem),radial-gradient(circle at 10% 15%,rgba(139,92,246,.2),transparent 30rem),var(--bg)}}
main{{width:min(74rem,calc(100% - 1.2rem));min-height:100svh;margin:auto;padding:.6rem 0;display:grid;grid-template-columns:minmax(15rem,25rem) minmax(0,1fr);gap:1rem;align-items:center}}
.player,.copy{{min-width:0;border:1px solid var(--line);background:rgba(18,24,42,.88);border-radius:1.6rem;box-shadow:0 24px 70px rgba(0,0,0,.38)}}
.player{{display:grid;place-items:center;padding:.55rem}}
video{{display:block;width:auto;max-width:100%;height:min(84svh,48rem);aspect-ratio:{record["width"]}/{record["height"]};border-radius:1.15rem;background:#000}}
.copy{{padding:clamp(1rem,3vw,2rem);display:grid;gap:1rem;overflow:hidden}}
.single{{display:block;max-width:100%;white-space:nowrap;overflow-x:auto;scrollbar-width:none}}
.single::-webkit-scrollbar{{display:none}}
.eyebrow{{color:#a5b4fc;font-size:.82rem;font-weight:850;letter-spacing:.06em}}
h1{{margin:0;font-size:clamp(1.15rem,4.2vw,3.5rem);line-height:1.04;letter-spacing:-.035em}}
.lead{{margin:0;color:var(--muted);font-size:clamp(.78rem,1.5vw,1.08rem)}}
.actions{{display:flex;gap:.7rem;overflow-x:auto;scrollbar-width:none}}
.button{{flex:0 0 auto;min-height:3rem;display:inline-flex;align-items:center;justify-content:center;padding:0 1rem;border:1px solid var(--line);border-radius:999px;color:var(--ink);font-weight:820;text-decoration:none;white-space:nowrap}}
.primary{{border:0;background:linear-gradient(120deg,var(--brand),var(--brand2))}}
.disclosure{{color:var(--muted);font-size:.78rem}}
@media(max-width:46rem){{main{{grid-template-columns:1fr;align-content:center}}video{{height:min(48svh,30rem)}}.copy{{gap:.7rem}}}}
</style>
</head>
<body><main>
<section class="player">
<video controls playsinline preload="none" poster="{esc(record["thumbnail_url"])}" aria-label="{esc(ui["Watch video"])}">
<source src="{esc(record["video_url"])}" type="video/mp4">
</video>
</section>
<section class="copy">
<a class="eyebrow single" href="{esc(record["hub_url"])}">{html.escape(ui["Video walkthrough"])}</a>
<h1 class="single" title="{esc(record["publisher_query"])}">{html.escape(str(record["publisher_query"]))}</h1>
<p class="lead single" title="{esc(record["decision_context"])}">{html.escape(str(record["decision_context"]))}</p>
<div class="actions">
<a class="button primary" rel="nofollow noopener" href="{esc(record["app_store_url"])}">{html.escape(str(record["app_store_cta_label"]))}</a>
<a class="button" href="{esc(record["canonical_guide_url"])}">{html.escape(ui["Open the app guide"])}</a>
</div>
<div class="disclosure single" title="{esc(record["publisher_disclosure"])}">{html.escape(str(record["publisher_disclosure"]))}</div>
</section>
</main></body></html>
"""


def _hub_schema(
    locale: str,
    canonical: str,
    records: list[dict[str, Any]],
    ui: dict[str, str],
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{canonical}#collection",
        "url": canonical,
        "name": ui["App walkthroughs"],
        "description": ui[
            "Short, publisher-authored walkthroughs of real app screens."
        ],
        "inLanguage": locale,
        "isAccessibleForFree": True,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(records),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "url": record["page_url"],
                    "name": record["publisher_query"],
                }
                for position, record in enumerate(records, start=1)
            ],
        },
    }


def render_hub(
    locale: str,
    records: list[dict[str, Any]],
    ui: dict[str, str],
    modified: str,
    *,
    root: bool,
) -> str:
    canonical = hub_url(None if root else locale)
    direction = "rtl" if locale in publisher_intent_catalog.RTL_LOCALES else "ltr"
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for record in records:
        cards.append(
            "".join(
                (
                    '<article class="card">',
                    f'<a class="poster" href="{esc(record["page_url"])}" '
                    f'aria-label="{esc(ui["Watch video"])}">',
                    f'<img src="{esc(record["thumbnail_url"])}" '
                    f'alt="{esc(record["publisher_query"])}" '
                    f'width="1200" height="630" loading="lazy" decoding="async">',
                    "</a>",
                    f'<div class="locale">{esc(record["locale"])}</div>',
                    f'<h2 title="{esc(record["publisher_query"])}">'
                    f'{html.escape(str(record["publisher_query"]))}</h2>',
                    f'<p title="{esc(record["decision_context"])}">'
                    f'{html.escape(str(record["decision_context"]))}</p>',
                    f'<a class="watch" href="{esc(record["page_url"])}">'
                    f'{html.escape(ui["Watch video"])}</a>',
                    "</article>",
                )
            )
        )
    locales = [
        candidate
        for candidate in OFFICIAL_LOCALES
        if any(record["locale"] == candidate for record in records)
    ]
    locale_links = []
    if not root:
        locale_links.append(
            f'<a href="{esc(hub_url())}">'
            f'{html.escape(ui["App walkthroughs"])}</a>'
        )
    locale_links.extend(
        f'<a href="{esc(hub_url(candidate))}">{esc(candidate)}</a>'
        for candidate in locales
    )
    schema = _json_script(_hub_schema(locale, canonical, records, ui))
    return f"""<!doctype html>
<html lang="{esc(locale)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(ui["Short, publisher-authored walkthroughs of real app screens."])}">
<meta name="content-modified" content="{esc(modified)}">
<title>{html.escape(ui["App walkthroughs"])} | Lumi Studio</title>
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" type="application/json" href="{esc(data_url())}">
{feed_discovery_links()}
<script type="application/ld+json">{schema}</script>
<style>
:root{{--bg:#f5f7ff;--card:#fff;--ink:#14182b;--muted:#59617a;--line:rgba(44,51,84,.12);--brand:#5b4ee6;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light dark}}
*{{box-sizing:border-box}}
body{{margin:0;color:var(--ink);background:radial-gradient(circle at 80% 0,rgba(91,78,230,.15),transparent 26rem),var(--bg)}}
main{{width:min(78rem,calc(100% - 1.2rem));margin:auto;padding:clamp(1rem,4vw,3rem) 0}}
.single,h1,p,h2{{white-space:nowrap;overflow-x:auto;scrollbar-width:none}}
.single::-webkit-scrollbar,h1::-webkit-scrollbar,p::-webkit-scrollbar,h2::-webkit-scrollbar{{display:none}}
h1{{margin:0;font-size:clamp(1.8rem,5vw,4rem);letter-spacing:-.045em}}
.lead{{color:var(--muted);font-size:clamp(.82rem,1.6vw,1.12rem)}}
.locales{{display:flex;gap:.5rem;overflow-x:auto;margin:1rem 0 1.4rem}}
.locales a{{flex:0 0 auto;padding:.42rem .7rem;border:1px solid var(--line);border-radius:999px;color:var(--ink);text-decoration:none;font-weight:750}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:1rem}}
.card{{min-width:0;padding:.75rem;border:1px solid var(--line);border-radius:1.35rem;background:var(--card);box-shadow:0 18px 45px rgba(39,44,82,.1)}}
.poster{{display:block;overflow:hidden;border-radius:.95rem}}
.poster img{{display:block;width:100%;height:auto}}
.locale{{margin-top:.65rem;color:var(--brand);font-size:.75rem;font-weight:850}}
h2{{margin:.35rem 0;font-size:1rem}}
.card p{{margin:.35rem 0;color:var(--muted);font-size:.82rem}}
.watch{{display:inline-flex;margin-top:.45rem;min-height:2.7rem;align-items:center;padding:0 .85rem;border-radius:999px;background:var(--brand);color:#fff;text-decoration:none;font-weight:820;white-space:nowrap}}
.note{{margin:1rem 0 0;color:var(--muted);font-size:.82rem}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0c1020;--card:#151b30;--ink:#f5f6ff;--muted:#c1c7df;--line:rgba(255,255,255,.12)}}}}
</style>
</head>
<body><main>
<h1>{html.escape(ui["App walkthroughs"])}</h1>
<p class="lead">{html.escape(ui["Short, publisher-authored walkthroughs of real app screens."])}</p>
<nav class="locales" aria-label="{esc(ui["Available walkthroughs"])}">{"".join(locale_links)}</nav>
<section class="grid">{"".join(cards)}</section>
<p class="note single">{html.escape(ui["Every video uses real app screens and is free to watch."])}</p>
</main></body></html>
"""


def _markdown_text(value: object) -> str:
    text = _single_line(value)
    return re.sub(r"([\\`*_[\]<>#])", r"\\\1", text)


def render_markdown(
    record: dict[str, Any],
    ui: dict[str, str],
    modified: str,
) -> str:
    frontmatter = {
        "title": record["publisher_query"],
        "lang": record["locale"],
        "canonical": record["page_url"],
        "modified": modified,
        "video_url": record["video_url"],
        "duration": record["duration"],
        "app_store_id": record["app_store_id"],
        "verified_live": True,
        "publisher": "Lumi Studio",
    }
    metadata = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in frontmatter.items()
    )
    return (
        f"---\n{metadata}\n---\n\n"
        f"# {_markdown_text(record['publisher_query'])}\n\n"
        f"{_markdown_text(record['decision_context'])}\n\n"
        f"[{_markdown_text(ui['Watch video'])}]({record['video_url']})\n\n"
        f"[{_markdown_text(record['app_store_cta_label'])}]"
        f"({record['app_store_url']})\n\n"
        f"[{_markdown_text(ui['Open the app guide'])}]"
        f"({record['canonical_guide_url']})\n\n"
        f"> {_markdown_text(record['publisher_disclosure'])}\n"
    )


def render_sitemap(records: list[dict[str, Any]], modified: str) -> str:
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("video", VIDEO_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    represented_locales = [
        locale
        for locale in OFFICIAL_LOCALES
        if any(record["locale"] == locale for record in records)
    ]
    for landing_url in (
        hub_url(),
        *(hub_url(locale) for locale in represented_locales),
    ):
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = landing_url
        ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = modified
    for record in records:
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = str(
            record["page_url"]
        )
        ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = modified
        video = ET.SubElement(url, f"{{{VIDEO_NS}}}video")
        ET.SubElement(video, f"{{{VIDEO_NS}}}thumbnail_loc").text = str(
            record["thumbnail_url"]
        )
        ET.SubElement(video, f"{{{VIDEO_NS}}}title").text = str(
            record["publisher_query"]
        )
        ET.SubElement(video, f"{{{VIDEO_NS}}}description").text = str(
            record["decision_context"]
        )
        ET.SubElement(video, f"{{{VIDEO_NS}}}content_loc").text = str(
            record["video_url"]
        )
        ET.SubElement(video, f"{{{VIDEO_NS}}}duration").text = str(
            round(float(record["duration_seconds"]))
        )
        ET.SubElement(video, f"{{{VIDEO_NS}}}publication_date").text = str(
            record["published_at"]
        )
        ET.SubElement(video, f"{{{VIDEO_NS}}}family_friendly").text = "yes"
        uploader = ET.SubElement(
            video,
            f"{{{VIDEO_NS}}}uploader",
            {"info": SITE},
        )
        uploader.text = "Lumi Studio"
        ET.SubElement(video, f"{{{VIDEO_NS}}}live").text = "no"
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def _write_text(path: Path, content: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except (FileNotFoundError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _remove_stale(video_root: Path, expected: set[Path]) -> None:
    if not video_root.is_dir():
        return
    for path in video_root.rglob("*"):
        if path.is_file() and path.suffix in {".html", ".md"} and path not in expected:
            path.unlink()
    directories = sorted(
        (path for path in video_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def llms_lines(*, full: bool) -> list[str]:
    path = PAGES / DATA_RELATIVE
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        "",
        "## Publisher-authored app video walkthroughs",
        f"- Gallery: {hub_url()}",
        f"- Video sitemap: {sitemap_url()}",
        f"- Machine-readable manifest: {data_url()}",
        f"- JSON Schema: {schema_url()}",
        f"- Current coverage: {payload['video_count']} videos, "
        f"{payload['app_count']}/{payload['portfolio_app_count']} verified live apps, "
        f"{payload['locale_count']}/{len(OFFICIAL_LOCALES)} official Apple locales",
    ]
    if full:
        lines.extend(
            f"  - {locale}: {hub_url(locale)}"
            for locale in payload["locales"]
        )
        lines.append(
            "- Coverage is incremental and includes only publisher-authored "
            "walkthroughs made from real app screens"
        )
    return lines


def build(
    pages: Path = PAGES,
    *,
    source_path: Path = SOURCE_PATH,
    today: str | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today().isoformat()
    today_date = _date_value(today, "video lesson build date")
    source_payload = load_sources(source_path)
    for source in source_payload["records"]:
        if _date_value(
            str(source["published_on"]),
            "video publication date",
        ) > today_date:
            raise ValueError(
                f"Video publication date is in the future: "
                f"{source['published_on']}"
            )
    represented_locales = {
        str(record["locale"]) for record in source_payload["records"]
    }
    i18n = load_i18n(represented_locales)
    records, portfolio_app_count = build_records(pages, source_payload)
    content_digest = _content_digest(records)
    generation_digest = _generation_digest(content_digest, source_path)
    output = pages / DATA_RELATIVE
    modified = _stable_modified(output, generation_digest, today)
    payload = dataset_payload(
        records,
        source_payload,
        portfolio_app_count,
        modified,
        content_digest,
        generation_digest,
    )
    _write_text(
        output,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    _write_text(
        pages / SCHEMA_RELATIVE,
        json.dumps(schema_payload(), ensure_ascii=False, indent=2) + "\n",
    )
    _write_text(pages / SITEMAP_NAME, render_sitemap(records, modified))

    expected = {pages / hub_relative()}
    _write_text(
        pages / hub_relative(),
        render_hub("en-US", records, i18n["en-US"], modified, root=True),
    )
    for locale in OFFICIAL_LOCALES:
        localized = [record for record in records if record["locale"] == locale]
        if not localized:
            continue
        hub_path = pages / hub_relative(locale)
        expected.add(hub_path)
        _write_text(
            hub_path,
            render_hub(locale, localized, i18n[locale], modified, root=False),
        )
    for record in records:
        locale = str(record["locale"])
        app_key = str(record["app_key"])
        html_path = pages / page_relative(app_key, locale)
        markdown_path = pages / markdown_relative(app_key, locale)
        expected.update((html_path, markdown_path))
        _write_text(
            html_path,
            render_page(record, records, i18n[locale], modified),
        )
        _write_text(
            markdown_path,
            render_markdown(record, i18n[locale], modified),
        )
    _remove_stale(pages / VIDEO_ROOT, expected)
    print(
        "APP_VIDEO_LESSONS "
        f"videos={len(records)} "
        f"apps={payload['app_count']}/{portfolio_app_count} "
        f"locales={payload['locale_count']}/{len(OFFICIAL_LOCALES)} "
        f"pages={len(expected)}",
        flush=True,
    )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        type=Path,
        default=PAGES,
        help="Pages repository root.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_PATH,
        help="Sanitized social video source manifest.",
    )
    parser.add_argument("--today", help="Stable test/build date.")
    args = parser.parse_args()
    build(
        args.pages.resolve(),
        source_path=args.source.resolve(),
        today=args.today,
    )


if __name__ == "__main__":
    main()
