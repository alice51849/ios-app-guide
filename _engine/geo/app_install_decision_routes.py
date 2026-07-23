#!/usr/bin/env python3
"""Build compact install-decision routes for every verified live app and locale."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

import app_install_decision_feeds
import app_store_storefronts
from family_travel_dataset import write_text_if_changed
from gen_feed import feed_discovery_links
import gen_mobile_app_identity
import gen_social_previews
from official_locales import OFFICIAL_LOCALES
import portfolio_app_finder
import publisher_intent_catalog


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE",
    "https://alice51849.github.io/ios-app-guide",
).rstrip("/")
SLUG = "app-install-decision-routes"
SITEMAP_NAME = "sitemap_app_install_decisions.xml"
DATA_RELATIVE = Path("data") / f"{SLUG}.json"
SCHEMA_RELATIVE = Path("data") / f"{SLUG}.schema.json"
LOCALE_DATA_DIR = Path("data") / SLUG / "locales"
OEMBED_DIR = Path("oembed") / "decision"
PRIORITY_APPS = ("maskmyfile", "wifiaid", "mochidonestamp")
PRIORITY_RANK = {key: index + 1 for index, key in enumerate(PRIORITY_APPS)}
TODAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def data_url() -> str:
    return f"{SITE}/{DATA_RELATIVE.as_posix()}"


def schema_url() -> str:
    return f"{SITE}/{SCHEMA_RELATIVE.as_posix()}"


def sitemap_url() -> str:
    return f"{SITE}/{SITEMAP_NAME}"


def locale_index_relative(locale: str) -> Path:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported install-decision locale: {locale}")
    return LOCALE_DATA_DIR / f"{locale}.json"


def locale_index_url(locale: str) -> str:
    return f"{SITE}/{locale_index_relative(locale).as_posix()}"


def decision_page_relative(app_key: str, locale: str) -> Path:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported install-decision locale: {locale}")
    return Path("apps") / app_key / "decision" / "l" / locale / "index.html"


def decision_page_url(app_key: str, locale: str) -> str:
    return f"{SITE}/{decision_page_relative(app_key, locale).as_posix()}"


def decision_oembed_relative(app_key: str, locale: str) -> Path:
    if locale not in OFFICIAL_LOCALES or re.fullmatch(
        r"[a-z0-9]+", app_key
    ) is None:
        raise ValueError(
            f"Invalid install-decision oEmbed path: {locale}/{app_key}"
        )
    return OEMBED_DIR / locale / f"{app_key}.json"


def decision_oembed_endpoint_url(app_key: str, locale: str) -> str:
    return f"{SITE}/{decision_oembed_relative(app_key, locale).as_posix()}"


def decision_oembed_url(app_key: str, locale: str) -> str:
    return gen_social_previews.oembed_discovery_url(
        decision_oembed_relative(app_key, locale).as_posix(),
        decision_page_url(app_key, locale),
        SITE,
    )


def _priority_key(app: dict[str, Any]) -> tuple[int, str, str]:
    key = str(app["key"])
    name = str(app["name"]).casefold()
    return (PRIORITY_RANK.get(key, len(PRIORITY_APPS) + 1), name, key)


def _privacy_facts(app: dict[str, Any]) -> list[str]:
    capabilities = app.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError(f"Missing capabilities for {app.get('key')}")
    return [
        key
        for key in (
            "offline",
            "no_account",
            "no_ads",
            "no_tracking",
            "private_or_on_device",
        )
        if capabilities.get(key) is True
    ]


def _device_surfaces(app: dict[str, Any]) -> list[str]:
    capabilities = app.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError(f"Missing capabilities for {app.get('key')}")
    return [
        key
        for key in ("widget", "apple_watch")
        if capabilities.get(key) is True
    ]


def _badge_labels(app: dict[str, Any], locale: str) -> list[str]:
    ui = portfolio_app_finder.UI[locale]
    category = str(app["category"])
    purchase_model = str(app["purchase_model"])
    badges = [
        str(
            ui["category_labels"].get(
                category,
                ui["category_labels"]["other"],
            )
        ),
        str(ui["purchase_labels"][purchase_model]),
    ]
    badges.extend(
        str(ui["capability_labels"][fact]) for fact in _privacy_facts(app)
    )
    badges.extend(
        str(ui["capability_labels"][surface])
        for surface in _device_surfaces(app)
    )
    return list(dict.fromkeys(badges))


def _source_surface(guide_url: str) -> str:
    return "answer_page" if "/answers/" in guide_url else "app_guide_page"


def _guide_page_path(pages: Path, guide_url: str) -> Path:
    parts = urlsplit(guide_url)
    site_parts = urlsplit(SITE)
    if (
        parts.scheme != site_parts.scheme
        or parts.netloc != site_parts.netloc
        or not parts.path.startswith(site_parts.path)
    ):
        raise ValueError(f"Unexpected guide URL: {guide_url}")
    relative = parts.path[len(site_parts.path) :].lstrip("/")
    return pages / relative


def _long_guide_description(path: Path, app_id: str, fallback: str) -> str:
    source = path.read_text(encoding="utf-8")
    for raw in re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        pending: list[Any] = [payload]
        while pending:
            node = pending.pop()
            if isinstance(node, list):
                pending.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            pending.extend(node.values())
            node_type = node.get("@type")
            types = (
                {node_type}
                if isinstance(node_type, str)
                else {
                    value for value in node_type if isinstance(value, str)
                }
                if isinstance(node_type, list)
                else set()
            )
            if not types & {"MobileApplication", "SoftwareApplication"}:
                continue
            identity = " ".join(
                str(node.get(field, ""))
                for field in ("@id", "url", "installUrl", "downloadUrl")
            )
            description = node.get("description")
            if (
                f"id{app_id}" in identity
                and isinstance(description, str)
                and len(" ".join(description.split())) >= 20
            ):
                return " ".join(description.split())
    return fallback


def _record(
    pages: Path,
    intent: dict[str, Any],
    app: dict[str, Any],
    storefront_details: dict[str, dict[str, dict[str, object]]],
) -> dict[str, Any]:
    locale = str(intent["locale"])
    key = str(intent["app_key"])
    badge_labels = _badge_labels(app, locale)
    app_store_id = str(intent["app_store_id"])
    country = app_store_storefronts.LOCALE_STOREFRONTS[locale]
    raw_storefront_facts = storefront_details.get(country, {}).get(
        app_store_id
    )
    storefront_facts = (
        app_store_storefronts.localized_storefront_detail(
            raw_storefront_facts,
            locale,
        )
        if raw_storefront_facts is not None
        else None
    )
    if storefront_facts is not None:
        badge_labels.append(
            f"App Store \u00b7 {storefront_facts['formatted_price']}"
        )
        if (
            "rating_value" in storefront_facts
            and "rating_count" in storefront_facts
        ):
            badge_labels.append(
                "\u2605 "
                f"{float(storefront_facts['rating_value']):.1f}/5 "
                "\u00b7 "
                f"{int(storefront_facts['rating_count'])}"
            )
    guide_url = str(intent["canonical_guide_url"])
    source_surface = _source_surface(guide_url)
    decision_context = str(intent["decision_context"])
    if source_surface == "app_guide_page":
        decision_context = _long_guide_description(
            _guide_page_path(pages, guide_url),
            str(intent["app_store_id"]),
            decision_context,
        )
    record = {
        "record_id": f"{locale}:{key}",
        "locale": locale,
        "app_key": key,
        "app_name": str(intent["app_name"]),
        "priority_rank": PRIORITY_RANK.get(key),
        "priority_group": (
            "launch_boost" if key in PRIORITY_RANK else "baseline_coverage"
        ),
        "publisher_query": str(intent["publisher_query"]),
        "decision_context": decision_context,
        "category": str(app["category"]),
        "category_label": str(
            portfolio_app_finder.UI[locale]["category_labels"].get(
                str(app["category"]),
                portfolio_app_finder.UI[locale]["category_labels"]["other"],
            )
        ),
        "purchase_model": str(app["purchase_model"]),
        "purchase_label": str(
            portfolio_app_finder.UI[locale]["purchase_labels"][
                str(app["purchase_model"])
            ]
        ),
        "one_time_option": bool(app["one_time_option"]),
        "privacy_facts": _privacy_facts(app),
        "privacy_labels": [
            str(portfolio_app_finder.UI[locale]["capability_labels"][fact])
            for fact in _privacy_facts(app)
        ],
        "device_surfaces": _device_surfaces(app),
        "device_labels": [
            str(portfolio_app_finder.UI[locale]["capability_labels"][surface])
            for surface in _device_surfaces(app)
        ],
        "badge_labels": badge_labels,
        "canonical_guide_url": guide_url,
        "decision_page_url": decision_page_url(key, locale),
        "oembed_url": decision_oembed_url(key, locale),
        "locale_index_url": locale_index_url(locale),
        "app_store_id": app_store_id,
        "canonical_app_store_url": str(intent["canonical_app_store_url"]),
        "app_store_url": str(intent["app_store_url"]),
        "app_store_cta_label": str(intent["app_store_cta_label"]),
        "storefront_facts": storefront_facts,
        "guide_cta_label": str(portfolio_app_finder.UI[locale]["guide"]),
        "publisher_disclosure": str(intent["publisher_disclosure"]),
        "source_persona_query": str(intent["source_persona_query"]),
        "source_surface": source_surface,
        "query_origin": str(intent["query_origin"]),
        "measured_search_volume": bool(intent["measured_search_volume"]),
        "is_ranking": bool(intent["is_ranking"]),
        "verified_live": bool(intent["verified_live"]),
    }
    if not record["verified_live"] or record["is_ranking"]:
        raise ValueError(f"Unsafe install decision record: {record['record_id']}")
    return record


def build_records(pages: Path = PAGES) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    intents, apps = publisher_intent_catalog.build_records(pages)
    storefront_details = app_store_storefronts.load_storefront_details(pages)
    app_keys = sorted(
        apps,
        key=lambda key: _priority_key(apps[key]),
    )
    by_pair = {
        (str(intent["locale"]), str(intent["app_key"])): intent for intent in intents
    }
    expected_pairs = {
        (locale, key)
        for locale in OFFICIAL_LOCALES
        for key in app_keys
    }
    if set(by_pair) != expected_pairs:
        raise ValueError(
            "Install decision coverage mismatch: "
            f"missing={len(expected_pairs - set(by_pair))}, "
            f"extra={len(set(by_pair) - expected_pairs)}"
        )
    records = [
        _record(
            pages,
            by_pair[(locale, key)],
            apps[key],
            storefront_details,
        )
        for locale in OFFICIAL_LOCALES
        for key in app_keys
    ]
    return records, apps


def _content_digest(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(
            records,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _generation_digest(content_digest: str) -> str:
    digest = hashlib.sha256()
    digest.update(content_digest.encode("ascii"))
    digest.update(Path(__file__).read_bytes())
    digest.update(Path(app_install_decision_feeds.__file__).read_bytes())
    digest.update(Path(gen_social_previews.__file__).read_bytes())
    digest.update(portfolio_app_finder.I18N_PATH.read_bytes())
    digest.update(publisher_intent_catalog.I18N_PATH.read_bytes())
    return digest.hexdigest()


def _stable_modified(path: Path, generation_digest: str, today: str) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return today
    value = payload.get("dateModified")
    if (
        payload.get("generation_digest") == generation_digest
        and isinstance(value, str)
        and TODAY_RE.fullmatch(value)
        and value <= today
    ):
        return value
    return today


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(path, content)


def _payload(
    records: list[dict[str, Any]],
    *,
    modified: str,
    content_digest: str,
    generation_digest: str,
) -> dict[str, Any]:
    return {
        "$schema": schema_url(),
        "schema_version": 1,
        "name": "Lumi Studio App Install Decision Routes",
        "description": (
            "First-party install decision routes for every verified live iOS app "
            "and Apple locale, with a direct App Store path, purchase model, "
            "privacy facts, device surfaces and provenance."
        ),
        "identifier": data_url(),
        "dateModified": modified,
        "content_digest": content_digest,
        "generation_digest": generation_digest,
        "publisher_disclosure": (
            "First-party decision-support material published by Lumi Studio, "
            "the developer of every listed app; not an independent ranking or "
            "measured search-volume product."
        ),
        "ordering": "official_locale_order_then_priority_then_alphabetical_app_name",
        "priority_app_keys": list(PRIORITY_APPS),
        "app_count": len(records) // len(OFFICIAL_LOCALES),
        "locale_count": len(OFFICIAL_LOCALES),
        "record_count": len(records),
        "locales": list(OFFICIAL_LOCALES),
        "syndication": app_install_decision_feeds.syndication_payload(),
        "records": records,
    }


def _schema_payload(apps: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_url(),
        "title": "Lumi Studio App Install Decision Routes",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "schema_version",
            "name",
            "description",
            "identifier",
            "dateModified",
            "content_digest",
            "generation_digest",
            "publisher_disclosure",
            "ordering",
            "priority_app_keys",
            "app_count",
            "locale_count",
            "record_count",
            "locales",
            "syndication",
            "records",
        ],
        "properties": {
            "$schema": {"const": schema_url()},
            "schema_version": {"const": 1},
            "name": {"const": "Lumi Studio App Install Decision Routes"},
            "description": {"type": "string", "minLength": 20},
            "identifier": {"type": "string", "format": "uri"},
            "dateModified": {"type": "string", "format": "date"},
            "content_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "generation_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "publisher_disclosure": {"type": "string", "minLength": 20},
            "ordering": {
                "const": (
                    "official_locale_order_then_priority_then_alphabetical_app_name"
                )
            },
            "priority_app_keys": {
                "type": "array",
                "items": {"enum": list(PRIORITY_APPS)},
                "minItems": len(PRIORITY_APPS),
                "maxItems": len(PRIORITY_APPS),
                "uniqueItems": True,
            },
            "app_count": {"const": len(apps)},
            "locale_count": {"const": len(OFFICIAL_LOCALES)},
            "record_count": {
                "const": len(apps) * len(OFFICIAL_LOCALES)
            },
            "locales": {
                "type": "array",
                "items": {"enum": list(OFFICIAL_LOCALES)},
                "minItems": len(OFFICIAL_LOCALES),
                "maxItems": len(OFFICIAL_LOCALES),
                "uniqueItems": True,
            },
            "syndication": {
                "type": "object",
                "additionalProperties": False,
                "required": ["formats", "locale_feeds"],
                "properties": {
                    "formats": {
                        "const": list(app_install_decision_feeds.FORMATS)
                    },
                    "locale_feeds": {
                        "type": "object",
                        "minProperties": len(OFFICIAL_LOCALES),
                        "maxProperties": len(OFFICIAL_LOCALES),
                        "propertyNames": {
                            "enum": list(OFFICIAL_LOCALES)
                        },
                        "additionalProperties": {
                            "$ref": "#/$defs/feed_set"
                        },
                    },
                },
            },
            "records": {
                "type": "array",
                "minItems": len(apps) * len(OFFICIAL_LOCALES),
                "maxItems": len(apps) * len(OFFICIAL_LOCALES),
                "items": {"$ref": "#/$defs/record"},
            },
        },
        "$defs": {
            "feed_set": {
                "type": "object",
                "additionalProperties": False,
                "required": list(app_install_decision_feeds.FORMATS),
                "properties": {
                    feed_format: {"type": "string", "format": "uri"}
                    for feed_format in app_install_decision_feeds.FORMATS
                },
            },
            "record": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "record_id",
                    "locale",
                    "app_key",
                    "app_name",
                    "priority_group",
                    "publisher_query",
                    "decision_context",
                    "category",
                    "category_label",
                    "purchase_model",
                    "purchase_label",
                    "one_time_option",
                    "privacy_facts",
                    "privacy_labels",
                    "device_surfaces",
                    "device_labels",
                    "badge_labels",
                    "canonical_guide_url",
                    "decision_page_url",
                    "oembed_url",
                    "locale_index_url",
                    "app_store_id",
                    "canonical_app_store_url",
                    "app_store_url",
                    "app_store_cta_label",
                    "storefront_facts",
                    "guide_cta_label",
                    "publisher_disclosure",
                    "source_persona_query",
                    "source_surface",
                    "query_origin",
                    "measured_search_volume",
                    "is_ranking",
                    "verified_live",
                ],
                "properties": {
                    "record_id": {
                        "type": "string",
                        "pattern": "^[A-Za-z0-9-]+:[a-z0-9-]+$",
                    },
                    "locale": {"enum": list(OFFICIAL_LOCALES)},
                    "app_key": {"enum": sorted(apps)},
                    "app_name": {"type": "string", "minLength": 1},
                    "priority_rank": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": len(PRIORITY_APPS),
                    },
                    "priority_group": {
                        "enum": ["launch_boost", "baseline_coverage"]
                    },
                    "publisher_query": {"type": "string", "minLength": 3},
                    "decision_context": {"type": "string", "minLength": 20},
                    "category": {"type": "string", "minLength": 1},
                    "category_label": {"type": "string", "minLength": 1},
                    "purchase_model": {"type": "string", "minLength": 1},
                    "purchase_label": {"type": "string", "minLength": 1},
                    "one_time_option": {"type": "boolean"},
                    "privacy_facts": {
                        "type": "array",
                        "items": {
                            "enum": [
                                "offline",
                                "no_account",
                                "no_ads",
                                "no_tracking",
                                "private_or_on_device",
                            ]
                        },
                        "uniqueItems": True,
                    },
                    "privacy_labels": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "device_surfaces": {
                        "type": "array",
                        "items": {"enum": ["widget", "apple_watch"]},
                        "uniqueItems": True,
                    },
                    "device_labels": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "badge_labels": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "minItems": 2,
                    },
                    "canonical_guide_url": {
                        "type": "string",
                        "format": "uri",
                    },
                    "decision_page_url": {
                        "type": "string",
                        "format": "uri",
                    },
                    "oembed_url": {
                        "type": "string",
                        "format": "uri",
                    },
                    "locale_index_url": {
                        "type": "string",
                        "format": "uri",
                    },
                    "app_store_id": {
                        "type": "string",
                        "pattern": "^[0-9]{9,12}$",
                    },
                    "canonical_app_store_url": {
                        "type": "string",
                        "format": "uri",
                    },
                    "app_store_url": {
                        "type": "string",
                        "format": "uri",
                    },
                    "app_store_cta_label": {
                        "type": "string",
                        "minLength": 3,
                    },
                    "storefront_facts": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "required": [
                            "price",
                            "currency",
                            "formatted_price",
                        ],
                        "properties": {
                            "price": {
                                "type": "string",
                                "pattern": r"^\d+(?:\.\d+)?$",
                            },
                            "currency": {
                                "type": "string",
                                "pattern": r"^[A-Z]{3}$",
                            },
                            "formatted_price": {
                                "type": "string",
                                "minLength": 1,
                            },
                            "rating_value": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 5,
                            },
                            "rating_count": {
                                "type": "integer",
                                "minimum": 1,
                            },
                        },
                    },
                    "guide_cta_label": {
                        "type": "string",
                        "minLength": 3,
                    },
                    "publisher_disclosure": {
                        "type": "string",
                        "minLength": 20,
                    },
                    "source_persona_query": {
                        "type": "string",
                        "minLength": 10,
                    },
                    "source_surface": {
                        "enum": ["answer_page", "app_guide_page"]
                    },
                    "query_origin": {
                        "const": "publisher_authored_editorially_localized"
                    },
                    "measured_search_volume": {"const": False},
                    "is_ranking": {"const": False},
                    "verified_live": {"const": True},
                },
            }
        },
    }


def locale_payload(
    locale: str,
    records: list[dict[str, Any]],
    *,
    modified: str,
    content_digest: str,
    generation_digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "Lumi Studio App Install Decision Routes",
        "locale": locale,
        "dateModified": modified,
        "content_digest": content_digest,
        "generation_digest": generation_digest,
        "priority_app_keys": list(PRIORITY_APPS),
        "record_count": len(records),
        "syndication": app_install_decision_feeds.feed_urls(locale),
        "records": records,
    }


def _feed_contexts(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    app_count = len(records) // len(OFFICIAL_LOCALES)
    contexts: dict[str, dict[str, str]] = {}
    for locale in OFFICIAL_LOCALES:
        locale_records = [
            record for record in records if record["locale"] == locale
        ]
        if len(locale_records) != app_count:
            raise ValueError(
                f"Install-decision feed context coverage mismatch: {locale}"
            )
        ui = portfolio_app_finder.UI[locale]
        publisher_disclosure = str(
            locale_records[0]["publisher_disclosure"]
        )
        contexts[locale] = {
            "title": str(ui["verified"]).format(count=app_count),
            "description": publisher_disclosure,
            "publisher_disclosure": publisher_disclosure,
        }
    return contexts


def sitemap_entries(
    records: list[dict[str, Any]],
) -> list[str]:
    page_urls = [str(record["decision_page_url"]) for record in records]
    expected_page_count = len(OFFICIAL_LOCALES) * (
        len(records) // len(OFFICIAL_LOCALES)
    )
    if len(page_urls) != expected_page_count:
        raise ValueError(
            "Install decision sitemap page coverage mismatch: "
            f"{len(page_urls)} != {expected_page_count}"
        )
    if len(set(page_urls)) != len(page_urls):
        raise ValueError("Install decision sitemap pages must be unique")
    oembed_urls = [
        decision_oembed_endpoint_url(
            str(record["app_key"]),
            str(record["locale"]),
        )
        for record in records
    ]
    if len(set(oembed_urls)) != len(oembed_urls):
        raise ValueError("Install decision oEmbed endpoints must be unique")
    locale_urls = [locale_index_url(locale) for locale in OFFICIAL_LOCALES]
    entries = [
        *page_urls,
        *oembed_urls,
        data_url(),
        schema_url(),
        *locale_urls,
        *app_install_decision_feeds.all_feed_urls(),
    ]
    if len(set(entries)) != len(entries):
        raise ValueError("Install decision sitemap URLs must be unique")
    return entries


def render_sitemap(records: list[dict[str, Any]], modified: str) -> str:
    entries = sitemap_entries(records)
    body = "\n".join(
        f"  <url><loc>{html.escape(url)}</loc><lastmod>{modified}</lastmod></url>"
        for url in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def _alternate_links(app_key: str, locale: str) -> str:
    links = [
        (
            f'<link rel="alternate" hreflang="{other}" '
            f'href="{decision_page_url(app_key, other)}">'
        )
        for other in OFFICIAL_LOCALES
    ]
    links.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{decision_page_url(app_key, "en-US")}">'
    )
    return "\n".join(links)


def _json_script(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")


def _share_image_url(record: dict[str, Any]) -> str:
    app_key = str(record["app_key"])
    if re.fullmatch(r"[a-z0-9]+", app_key) is None:
        raise ValueError(f"Invalid install-decision app key: {app_key}")
    return f"{SITE}/social/img/{app_key}-share.jpg"


def _oembed_document(
    pages: Path,
    record: dict[str, Any],
) -> dict[str, object]:
    app_key = str(record["app_key"])
    locale = str(record["locale"])
    image_path = pages / "social" / "img" / f"{app_key}-share.jpg"
    if not image_path.is_file() or image_path.stat().st_size == 0:
        raise FileNotFoundError(
            f"Install-decision share image is missing: {image_path}"
        )
    buyer_intent_url = gen_social_previews.available_buyer_intent_image(
        pages,
        app_key,
        locale,
        SITE,
    )
    if buyer_intent_url is None:
        raise FileNotFoundError(
            f"Install-decision buyer-intent visual is missing: "
            f"{locale}/{app_key}"
        )
    storefront_facts = record.get("storefront_facts")
    return gen_social_previews.oembed_document(
        str(record["publisher_query"]),
        _share_image_url(record),
        str(record["decision_page_url"]),
        str(record["app_store_url"]),
        locale,
        SITE,
        storefront=(
            storefront_facts if isinstance(storefront_facts, dict) else None
        ),
        buyer_intent_url=buyer_intent_url,
        source_kind="decision",
    )


def _structured_data(record: dict[str, Any]) -> dict[str, Any]:
    app = gen_mobile_app_identity.mobile_app_schema(
        str(record["app_store_id"]),
        str(record["app_name"]),
        str(record["category"]),
        str(record["decision_page_url"]),
    )
    app["url"] = str(record["app_store_url"])
    app["installUrl"] = str(record["app_store_url"])
    app["downloadUrl"] = str(record["app_store_url"])
    app["description"] = str(record["decision_context"])
    app["potentialAction"] = {
        "@type": "InstallAction",
        "target": str(record["app_store_url"]),
    }
    storefront_facts = record.get("storefront_facts")
    if isinstance(storefront_facts, dict):
        app["offers"] = {
            "@type": "Offer",
            "price": str(storefront_facts["price"]),
            "priceCurrency": str(storefront_facts["currency"]),
            "url": str(record["app_store_url"]),
            "availability": "https://schema.org/InStock",
        }
        if (
            "rating_value" in storefront_facts
            and "rating_count" in storefront_facts
        ):
            app["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": float(storefront_facts["rating_value"]),
                "ratingCount": int(storefront_facts["rating_count"]),
                "bestRating": 5,
                "worstRating": 1,
            }
    app["additionalProperty"] = [
        {
            "@type": "PropertyValue",
            "name": "Purchase model",
            "value": str(record["purchase_label"]),
        },
        *[
            {
                "@type": "PropertyValue",
                "name": "Published fact",
                "value": label,
            }
            for label in record["badge_labels"]
        ],
    ]
    image_url = _share_image_url(record)
    return {
        "@context": "https://schema.org",
        "@graph": [
            app,
            {
                "@type": "WebPage",
                "@id": f"{record['decision_page_url']}#webpage",
                "url": str(record["decision_page_url"]),
                "name": str(record["publisher_query"]),
                "description": str(record["decision_context"]),
                "inLanguage": str(record["locale"]),
                "about": {"@id": str(record["canonical_app_store_url"])},
                "isPartOf": {"@id": data_url()},
                "mainEntity": {"@id": str(record["canonical_app_store_url"])},
                "primaryImageOfPage": {
                    "@type": "ImageObject",
                    "@id": f"{image_url}#primaryimage",
                    "contentUrl": image_url,
                    "url": image_url,
                    "width": gen_social_previews.CARD_SIZE[0],
                    "height": gen_social_previews.CARD_SIZE[1],
                    "encodingFormat": "image/jpeg",
                    "caption": str(record["publisher_query"]),
                    "representativeOfPage": True,
                },
            },
            {
                "@type": "Dataset",
                "@id": data_url(),
                "name": "Lumi Studio App Install Decision Routes",
                "description": (
                    "First-party install decision routes for verified live iOS "
                    "apps in every official Apple locale."
                ),
                "url": data_url(),
                "distribution": {
                    "@type": "DataDownload",
                    "encodingFormat": "application/json",
                    "contentUrl": str(record["locale_index_url"]),
                },
            },
        ],
    }


def render_page(
    record: dict[str, Any],
    modified: str,
    feed_title: str,
) -> str:
    locale = str(record["locale"])
    icon = Path("stories") / "img" / f"{record['app_key']}-icon.jpg"
    icon_url = f"{SITE}/{icon.as_posix()}" if (PAGES / icon).is_file() else ""
    badge_html = "".join(
        f'<span class="fact">{html.escape(label)}</span>'
        for label in record["badge_labels"]
    )
    dir_attr = "rtl" if locale in portfolio_app_finder.RTL_LOCALES else "ltr"
    icon_block = (
        f'<img class="icon" src="{html.escape(icon_url, quote=True)}" alt="">'
        if icon_url
        else ""
    )
    storefront_facts = record.get("storefront_facts")
    social_metadata = gen_social_previews.metadata_block(
        str(record["app_key"]),
        str(record["publisher_query"]),
        str(record["decision_context"]),
        str(record["decision_page_url"]),
        str(record["app_name"]),
        SITE,
        locale=locale,
        endpoint_locale=locale,
        image_alt=str(record["publisher_query"]),
        storefront=(
            storefront_facts if isinstance(storefront_facts, dict) else None
        ),
        include_primary_image_schema=False,
        include_hero_style=False,
        oembed_href=str(record["oembed_url"]),
    )
    return f"""<!doctype html>
<html lang="{html.escape(locale)}" dir="{dir_attr}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="apple-itunes-app" content="app-id={html.escape(str(record["app_store_id"]), quote=True)}">
<meta name="description" content="{html.escape(str(record["decision_context"]), quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
{social_metadata}
<title>{html.escape(str(record["publisher_query"]))} | {html.escape(str(record["app_name"]))}</title>
<link rel="canonical" href="{html.escape(str(record["decision_page_url"]), quote=True)}">
<link rel="alternate" type="application/json" href="{html.escape(str(record["locale_index_url"]), quote=True)}">
<link rel="alternate" type="application/schema+json" href="{html.escape(schema_url(), quote=True)}">
{_alternate_links(str(record["app_key"]), locale)}
{feed_discovery_links()}
{app_install_decision_feeds.discovery_links(locale, feed_title)}
<script type="application/ld+json">{_json_script(_structured_data(record))}</script>
<script id="decision-record" type="application/json">{_json_script(record)}</script>
<style>
:root {{
  color-scheme: light dark;
  --bg: #f7f4ff;
  --card: rgba(255,255,255,.88);
  --ink: #17172a;
  --muted: #5b5b77;
  --line: rgba(61,55,111,.12);
  --brand: #4f46e5;
  --brand2: #9333ea;
  --shadow: rgba(40,31,92,.16);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background:
    radial-gradient(circle at 10% 10%, rgba(79,70,229,.18), transparent 24rem),
    radial-gradient(circle at 90% 0, rgba(147,51,234,.15), transparent 22rem),
    linear-gradient(180deg, #fcfbff, var(--bg));
}}
main {{
  width: min(68rem, calc(100% - 2rem));
  min-height: 100vh;
  display: grid;
  align-content: center;
  gap: 1rem;
  margin: 0 auto;
  padding: 2rem 0;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 1.75rem;
  box-shadow: 0 24px 64px var(--shadow);
  padding: clamp(1.2rem, 3vw, 2rem);
  backdrop-filter: blur(18px);
}}
.eyebrow {{
  display: inline-flex;
  align-items: center;
  gap: .8rem;
  max-inline-size: 100%;
  font-size: .85rem;
  font-weight: 850;
  letter-spacing: .05em;
  color: var(--brand);
  white-space: nowrap;
  overflow-x: auto;
}}
.icon {{
  inline-size: 2.6rem;
  block-size: 2.6rem;
  border-radius: 22%;
  border: 1px solid rgba(79,70,229,.15);
}}
h1 {{
  margin: .65rem 0 0;
  font-size: clamp(1.9rem, 5vw, 3.8rem);
  line-height: 1.02;
  letter-spacing: -.04em;
}}
.lead {{
  margin: 0;
  color: var(--muted);
  font-size: clamp(1rem, 2.1vw, 1.2rem);
}}
.facts {{
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
}}
.fact {{
  display: inline-flex;
  max-inline-size: 100%;
  padding: .42rem .72rem;
  border-radius: 999px;
  border: 1px solid rgba(79,70,229,.14);
  background: rgba(79,70,229,.08);
  font-size: .82rem;
  font-weight: 760;
  white-space: nowrap;
}}
.actions {{
  display: flex;
  flex-wrap: wrap;
  gap: .8rem;
}}
.button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
  padding: 0 .95rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.72);
  color: var(--ink);
  font-weight: 820;
  text-decoration: none;
  white-space: nowrap;
}}
.button.primary {{
  color: #fff;
  border: 0;
  background: linear-gradient(120deg, var(--brand), var(--brand2));
}}
footer {{
  color: var(--muted);
  font-size: .88rem;
}}
@media (max-width: 42rem) {{
  main {{ width: min(100%, calc(100% - 1rem)); padding: .5rem 0; }}
  .actions {{ flex-direction: column; }}
  .button {{ width: 100%; }}
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #12111f;
    --card: rgba(23,23,42,.86);
    --ink: #f5f4ff;
    --muted: #d2cfff;
    --line: rgba(227,224,255,.12);
    --shadow: rgba(0,0,0,.35);
  }}
  body {{
    background:
      radial-gradient(circle at 10% 10%, rgba(99,102,241,.2), transparent 24rem),
      radial-gradient(circle at 90% 0, rgba(192,132,252,.14), transparent 22rem),
      linear-gradient(180deg, #0f0d19, var(--bg));
  }}
  .fact {{ background: rgba(99,102,241,.12); }}
  .button {{ background: rgba(255,255,255,.06); color: var(--ink); }}
}}
</style></head><body><main>
<section class="card">
  <div class="eyebrow">{icon_block}<span>{html.escape(str(record["app_name"]))}</span></div>
  <h1>{html.escape(str(record["publisher_query"]))}</h1>
  <p class="lead">{html.escape(str(record["decision_context"]))}</p>
</section>
<section class="card">
  <div class="facts">{badge_html}</div>
</section>
<section class="card">
  <div class="actions">
    <a class="button primary" rel="nofollow noopener" href="{html.escape(str(record["app_store_url"]), quote=True)}">{html.escape(str(record["app_store_cta_label"]))}</a>
    <a class="button" href="{html.escape(str(record["canonical_guide_url"]), quote=True)}">{html.escape(str(record["guide_cta_label"]))}</a>
  </div>
</section>
<footer class="card">{html.escape(str(record["publisher_disclosure"]))}</footer>
</main></body></html>
"""


def llms_lines(*, full: bool) -> list[str]:
    if not (PAGES / DATA_RELATIVE).is_file():
        return []
    lines = [
        "",
        "## App install decision routes",
        f"- Sitemap: {sitemap_url()}",
        f"- Aggregate JSON: {data_url()}",
        f"- JSON Schema: {schema_url()}",
        f"- Official Apple locales: {len(OFFICIAL_LOCALES)}/{len(OFFICIAL_LOCALES)}",
    ]
    if full:
        lines.extend(
            f"  - {locale}: {locale_index_url(locale)}"
            for locale in OFFICIAL_LOCALES
        )
    return lines


def build(pages: Path = PAGES) -> list[str]:
    records, apps = build_records(pages)
    feed_contexts = _feed_contexts(records)
    content_digest = _content_digest(records)
    generation_digest = _generation_digest(content_digest)
    modified = _stable_modified(
        pages / DATA_RELATIVE,
        generation_digest,
        datetime.now(timezone.utc).date().isoformat(),
    )
    payload = _payload(
        records,
        modified=modified,
        content_digest=content_digest,
        generation_digest=generation_digest,
    )
    _write_text(
        pages / DATA_RELATIVE,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    _write_text(
        pages / SCHEMA_RELATIVE,
        json.dumps(_schema_payload(apps), ensure_ascii=False, indent=2) + "\n",
    )
    _write_text(
        pages / SITEMAP_NAME,
        render_sitemap(records, modified),
    )
    locale_urls = []
    for locale in OFFICIAL_LOCALES:
        locale_records = [
            record for record in records if record["locale"] == locale
        ]
        locale_path = pages / locale_index_relative(locale)
        _write_text(
            locale_path,
            json.dumps(
                locale_payload(
                    locale,
                    locale_records,
                    modified=modified,
                    content_digest=content_digest,
                    generation_digest=generation_digest,
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        locale_urls.append(locale_index_url(locale))
    feed_urls = app_install_decision_feeds.build(
        pages,
        records,
        modified,
        feed_contexts,
    )
    expected_oembed_paths: set[Path] = set()
    for record in records:
        oembed_path = pages / decision_oembed_relative(
            str(record["app_key"]),
            str(record["locale"]),
        )
        expected_oembed_paths.add(oembed_path)
        _write_text(
            oembed_path,
            json.dumps(
                _oembed_document(pages, record),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        _write_text(
            pages
            / decision_page_relative(
                str(record["app_key"]),
                str(record["locale"]),
            ),
            render_page(
                record,
                modified,
                feed_contexts[str(record["locale"])]["title"],
            ),
        )
    oembed_root = pages / OEMBED_DIR
    for stale in (
        oembed_root.rglob("*.json") if oembed_root.is_dir() else ()
    ):
        if stale not in expected_oembed_paths:
            stale.unlink()
    for directory in sorted(
        (
            path
            for path in oembed_root.rglob("*")
            if path.is_dir()
        ),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if not any(directory.iterdir()):
            directory.rmdir()
    return [
        data_url(),
        schema_url(),
        *locale_urls,
        *feed_urls,
        *(record["decision_page_url"] for record in records),
        *(
            decision_oembed_endpoint_url(
                str(record["app_key"]),
                str(record["locale"]),
            )
            for record in records
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    urls = build()
    decision_page_count = sum("/decision/l/" in url for url in urls)
    oembed_count = sum("/oembed/decision/" in url for url in urls)
    print(
        "app install decision routes -> "
        f"{len(PRIORITY_APPS)} priority apps, "
        f"{len(OFFICIAL_LOCALES)} locales, "
        f"{len(OFFICIAL_LOCALES) * len(app_install_decision_feeds.FORMATS)} "
        "locale feeds, "
        f"{decision_page_count} pages and "
        f"{oembed_count} rich embeds",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
