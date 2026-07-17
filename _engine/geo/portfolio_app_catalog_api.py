#!/usr/bin/env python3
"""Build a 50-locale, read-only API for every verified live iOS app."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import write_text_if_changed  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    require_official_locale_coverage,
)
import portfolio_app_finder  # noqa: E402
from static_api_catalog import build_api_discovery  # noqa: E402
from videogen.registry import (  # noqa: E402
    APPSTORE,
    VALID_PURCHASE_MODELS,
    appstore_url,
)


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
API_VERSION = "1.1.0"
SLUG = "ios-app-catalog"
API_PATH = Path("api") / "v1" / SLUG
API_BASE = f"{SITE}/{API_PATH.as_posix()}"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
JSON_FEED_VERSION = "https://jsonfeed.org/version/1.1"
FEED_MAX_BYTES = 250_000
TODAY = dt.date.today().isoformat()
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")

COPY = {
    "en": {
        "lang": "en",
        "title": "Verified iOS App Catalog API",
        "description": (
            "A free, read-only OpenAPI catalog for every verified live app, with "
            "localized summaries, search terms and direct App Store links in 50 locales."
        ),
        "eyebrow": "OpenAPI 3.1 · 50 locales · no API key",
        "lead": (
            "Give an assistant a locale-specific catalog so it can match a real task "
            "to a verified app without inventing prices, ratings or rankings."
        ),
        "switch": "繁體中文",
        "finder": "Interactive app finder",
        "openapi": "OpenAPI 3.1",
        "feed": "JSON Feed 1.1",
        "index": "API index",
        "schema": "Catalog schema",
        "locales": "Locale catalogs",
        "apps": "Verified live apps",
        "store": "View on the App Store",
        "usage": "Use from an agent or script",
        "usage_text": (
            "Choose one official App Store locale, fetch its static JSON file, then "
            "match the user's task against summary and search_terms. Preserve the "
            "returned app_store_url so downloads remain directly attributable."
        ),
        "contract": "Trust contract",
        "contract_text": (
            "Availability is inherited from the four-market Apple lookup gate. Results "
            "are alphabetical, never ranked, and contain no fabricated offer, price, "
            "rating, review or outcome claim. The API accepts and stores no user data."
        ),
        "footer": (
            "CC BY 4.0 covers the original catalog compilation, not Apple or app trademarks."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "已驗證 iOS App 目錄 API",
        "description": (
            "免費唯讀 OpenAPI，收錄所有已驗證上架 App，提供 50 個 locale 的在地化摘要、"
            "搜尋詞與 App Store 直達連結。"
        ),
        "eyebrow": "OpenAPI 3.1 · 50 個 locale · 免 API 金鑰",
        "lead": (
            "讓 AI 助理依使用者所在地讀取對應目錄，以真實需求配對已驗證 App，"
            "不捏造價格、評分或排行。"
        ),
        "switch": "English",
        "finder": "互動式 App 篩選器",
        "openapi": "OpenAPI 3.1",
        "feed": "JSON Feed 1.1",
        "index": "API 索引",
        "schema": "目錄 Schema",
        "locales": "各語系目錄",
        "apps": "已驗證上架 App",
        "store": "前往 App Store 查看",
        "usage": "供 Agent 或程式使用",
        "usage_text": (
            "先選擇 Apple 官方 locale 並讀取對應的靜態 JSON，再用 summary 與 "
            "search_terms 配對使用者需求；請保留回傳的 app_store_url，讓下載可正確歸因。"
        ),
        "contract": "可信度契約",
        "contract_text": (
            "上架狀態沿用 Apple 四市場 lookup gate；結果依名稱排序、絕非排行榜，"
            "不包含虛構的優惠、價格、評分、評論或成果宣稱，也不接收或儲存使用者資料。"
        ),
        "footer": "CC BY 4.0 僅涵蓋原創目錄彙編，不涵蓋 Apple 或各 App 商標。",
    },
}


def api_url(path: str = "") -> str:
    return f"{API_BASE}/{path}" if path else f"{API_BASE}/"


def locale_url(locale: str) -> str:
    return api_url(f"locales/{locale}.json")


def feed_url(locale: str) -> str:
    return api_url(f"feeds/{locale}.json")


def _channel_campaign(channel: str, locale: str) -> str:
    value = f"iag_{channel}_{locale.replace('-', '_').lower()}"
    if len(value) > 30 or not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"Invalid catalog campaign token: {value}")
    return value


def _campaign(locale: str) -> str:
    return _channel_campaign("api", locale)


def _feed_campaign(locale: str) -> str:
    return _channel_campaign("feed", locale)


def _localized_directory_title(pages: Path, locale: str) -> str:
    path = pages / locale / "index.html"
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Missing localized app directory: {path}") from error
    match = re.search(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    if not match:
        raise ValueError(f"Missing localized directory title: {path}")
    title = " ".join(html.unescape(match.group(1)).split())
    if not title or "<" in title or ">" in title:
        raise ValueError(f"Invalid localized directory title: {path}")
    return title


def _meta_content(path: Path, name: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Missing localized app guide: {path}") from error
    match = re.search(
        rf'<meta\s+name=["\']{re.escape(name)}["\']\s+'
        r'content=(["\'])(.*?)\1',
        text,
        flags=re.I | re.S,
    )
    if not match:
        raise ValueError(f"Missing {name} metadata: {path}")
    value = html.unescape(match.group(2)).strip()
    if not value:
        raise ValueError(f"Empty {name} metadata: {path}")
    return value


def _search_terms(path: Path) -> list[str]:
    terms = [
        term.strip()
        for term in _meta_content(path, "keywords").split(",")
        if term.strip()
    ]
    unique = list(dict.fromkeys(terms))
    if not unique:
        raise ValueError(f"No localized search terms: {path}")
    return unique


def _localized_summary(path: Path, app_id: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Missing localized app guide: {path}") from error
    scripts = re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>'
        r"(.*?)</script>",
        text,
        flags=re.I | re.S,
    )
    for source in scripts:
        try:
            payload = json.loads(source)
        except json.JSONDecodeError:
            continue
        pending = [payload]
        while pending:
            node = pending.pop()
            if isinstance(node, list):
                pending.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            pending.extend(node.values())
            node_type = node.get("@type")
            if isinstance(node_type, str):
                types = {node_type}
            elif isinstance(node_type, list):
                types = {
                    value for value in node_type if isinstance(value, str)
                }
            else:
                types = set()
            identity = " ".join(
                str(node.get(field, ""))
                for field in ("@id", "url", "installUrl", "downloadUrl")
            )
            description = node.get("description")
            if (
                "MobileApplication" in types
                and f"id{app_id}" in identity
                and isinstance(description, str)
            ):
                for paragraph in re.split(r"\n\s*\n", description):
                    summary = " ".join(paragraph.split())
                    if len(summary) >= 20:
                        return summary
    return _meta_content(path, "description")


def localized_record(
    record: dict[str, object],
    locale: str,
    pages: Path = PAGES,
) -> dict[str, object]:
    path = pages / locale / f"{record['key']}.html"
    app_id = str(record["app_store_id"])
    return {
        "key": record["key"],
        "app_store_id": app_id,
        "name": record["name"],
        "summary": _localized_summary(path, app_id),
        "category": record["category"],
        "search_terms": _search_terms(path),
        "purchase_model": record["purchase_model"],
        "one_time_option": record["one_time_option"],
        "capabilities": record["capabilities"],
        "app_store_url": appstore_url(
            str(record["key"]),
            _campaign(locale),
        ),
        "guide_url": f"{SITE}/{locale}/{record['key']}.html",
        "verified_live": True,
    }


def _content_digest(localized: dict[str, list[dict[str, object]]]) -> str:
    encoded = json.dumps(
        {"api_version": API_VERSION, "localized": localized},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stable_modified(pages: Path, digest: str) -> str:
    path = pages / API_PATH / "index.json"
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return TODAY
    date = previous.get("date_modified")
    if (
        previous.get("content_digest") == digest
        and isinstance(date, str)
        and DATE_RE.fullmatch(date)
    ):
        return date
    return TODAY


def catalog_payload(
    locale: str,
    apps: list[dict[str, object]],
    modified: str,
    digest: str,
) -> dict[str, object]:
    return {
        "$schema": api_url("catalog.schema.json"),
        "api_version": API_VERSION,
        "date_modified": modified,
        "content_digest": digest,
        "locale": locale,
        "license": LICENSE_URL,
        "ordering": "alphabetical_by_app_name_not_a_ranking",
        "record_count": len(apps),
        "apps": apps,
    }


def feed_payload(
    locale: str,
    title: str,
    apps: list[dict[str, object]],
    modified: str,
    digest: str,
) -> dict[str, object]:
    timestamp = f"{modified}T00:00:00Z"
    return {
        "version": JSON_FEED_VERSION,
        "title": title,
        "home_page_url": f"{SITE}/{locale}/index.html",
        "feed_url": feed_url(locale),
        "language": locale,
        "authors": [{"name": "Lumi Studio", "url": f"{SITE}/about.html"}],
        "_lumi_catalog": {
            "apiVersion": API_VERSION,
            "dateModified": modified,
            "contentDigest": digest,
            "license": LICENSE_URL,
            "ordering": "alphabetical_by_app_name_not_a_ranking",
            "recordCount": len(apps),
        },
        "items": [
            {
                "id": (
                    f"https://apps.apple.com/app/id{app['app_store_id']}"
                ),
                "url": app["guide_url"],
                "external_url": appstore_url(
                    str(app["key"]),
                    _feed_campaign(locale),
                ),
                "title": app["name"],
                "content_text": app["summary"],
                "date_modified": timestamp,
                "tags": app["search_terms"],
                "language": locale,
            }
            for app in apps
        ],
    }


def index_payload(
    records: list[dict[str, object]],
    modified: str,
    digest: str,
) -> dict[str, object]:
    return {
        "$schema": api_url("index.schema.json"),
        "api_version": API_VERSION,
        "date_modified": modified,
        "content_digest": digest,
        "name": "Verified Independent iOS App Catalog API",
        "description": COPY["en"]["description"],
        "license": LICENSE_URL,
        "default_locale": "en-US",
        "locale_count": len(OFFICIAL_LOCALES),
        "record_count": len(records),
        "ordering": "alphabetical_by_app_name_not_a_ranking",
        "availability_verification": {
            "source": "Apple iTunes Lookup API",
            "markets": ["US", "TW", "JP", "GB"],
            "retirement_rule": "Retire after three consecutive verified misses",
        },
        "documentation": {
            "en": api_url(),
            "zh-Hant": f"{SITE}/zh-Hant/{API_PATH.as_posix()}/",
        },
        "openapi": api_url("openapi.json"),
        "catalog_schema": api_url("catalog.schema.json"),
        "feed_schema": api_url("feed.schema.json"),
        "locales": [
            {
                "locale": locale,
                "url": locale_url(locale),
                "feed": feed_url(locale),
            }
            for locale in OFFICIAL_LOCALES
        ],
    }


def index_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("index.schema.json"),
        "title": "Verified iOS App Catalog API index",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "api_version",
            "date_modified",
            "content_digest",
            "name",
            "description",
            "license",
            "default_locale",
            "locale_count",
            "record_count",
            "ordering",
            "availability_verification",
            "documentation",
            "openapi",
            "catalog_schema",
            "feed_schema",
            "locales",
        ],
        "properties": {
            "$schema": {"const": api_url("index.schema.json")},
            "api_version": {"const": API_VERSION},
            "date_modified": {"type": "string", "format": "date"},
            "content_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "name": {"type": "string", "minLength": 1},
            "description": {"type": "string", "minLength": 1},
            "license": {"const": LICENSE_URL},
            "default_locale": {"const": "en-US"},
            "locale_count": {"const": len(OFFICIAL_LOCALES)},
            "record_count": {"type": "integer", "minimum": 1},
            "ordering": {
                "const": "alphabetical_by_app_name_not_a_ranking"
            },
            "availability_verification": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "markets", "retirement_rule"],
                "properties": {
                    "source": {"type": "string", "minLength": 1},
                    "markets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "uniqueItems": True,
                    },
                    "retirement_rule": {"type": "string", "minLength": 1},
                },
            },
            "documentation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["en", "zh-Hant"],
                "properties": {
                    "en": {"type": "string", "format": "uri"},
                    "zh-Hant": {"type": "string", "format": "uri"},
                },
            },
            "openapi": {"const": api_url("openapi.json")},
            "catalog_schema": {"const": api_url("catalog.schema.json")},
            "feed_schema": {"const": api_url("feed.schema.json")},
            "locales": {
                "type": "array",
                "minItems": len(OFFICIAL_LOCALES),
                "maxItems": len(OFFICIAL_LOCALES),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["locale", "url", "feed"],
                    "properties": {
                        "locale": {"enum": list(OFFICIAL_LOCALES)},
                        "url": {"type": "string", "format": "uri"},
                        "feed": {"type": "string", "format": "uri"},
                    },
                },
            },
        },
    }


def catalog_schema() -> dict[str, object]:
    capabilities = (
        "offline",
        "no_account",
        "no_ads",
        "no_tracking",
        "private_or_on_device",
        "widget",
        "apple_watch",
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("catalog.schema.json"),
        "title": "Localized verified iOS app catalog",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "api_version",
            "date_modified",
            "content_digest",
            "locale",
            "license",
            "ordering",
            "record_count",
            "apps",
        ],
        "properties": {
            "$schema": {"const": api_url("catalog.schema.json")},
            "api_version": {"const": API_VERSION},
            "date_modified": {"type": "string", "format": "date"},
            "content_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "locale": {"enum": list(OFFICIAL_LOCALES)},
            "license": {"const": LICENSE_URL},
            "ordering": {
                "const": "alphabetical_by_app_name_not_a_ranking"
            },
            "record_count": {"type": "integer", "minimum": 1},
            "apps": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "key",
                        "app_store_id",
                        "name",
                        "summary",
                        "category",
                        "search_terms",
                        "purchase_model",
                        "one_time_option",
                        "capabilities",
                        "app_store_url",
                        "guide_url",
                        "verified_live",
                    ],
                    "properties": {
                        "key": {"type": "string", "minLength": 1},
                        "app_store_id": {
                            "type": "string",
                            "pattern": "^[0-9]{9,12}$",
                        },
                        "name": {"type": "string", "minLength": 1},
                        "summary": {"type": "string", "minLength": 1},
                        "category": {"type": "string", "minLength": 1},
                        "search_terms": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "purchase_model": {
                            "enum": sorted(VALID_PURCHASE_MODELS),
                        },
                        "one_time_option": {"type": "boolean"},
                        "capabilities": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": list(capabilities),
                            "properties": {
                                key: {"type": "boolean"}
                                for key in capabilities
                            },
                        },
                        "app_store_url": {
                            "type": "string",
                            "format": "uri",
                            "pattern": (
                                "^https://apps\\.apple\\.com/app/id[0-9]+"
                            ),
                        },
                        "guide_url": {"type": "string", "format": "uri"},
                        "verified_live": {"const": True},
                    },
                },
            },
        },
    }


def feed_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("feed.schema.json"),
        "title": "Localized verified iOS app JSON Feed",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "title",
            "home_page_url",
            "feed_url",
            "language",
            "authors",
            "_lumi_catalog",
            "items",
        ],
        "properties": {
            "version": {"const": JSON_FEED_VERSION},
            "title": {"type": "string", "minLength": 1},
            "home_page_url": {"type": "string", "format": "uri"},
            "feed_url": {"type": "string", "format": "uri"},
            "language": {"enum": list(OFFICIAL_LOCALES)},
            "authors": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "url"],
                    "properties": {
                        "name": {"const": "Lumi Studio"},
                        "url": {"type": "string", "format": "uri"},
                    },
                },
            },
            "_lumi_catalog": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "apiVersion",
                    "dateModified",
                    "contentDigest",
                    "license",
                    "ordering",
                    "recordCount",
                ],
                "properties": {
                    "apiVersion": {"const": API_VERSION},
                    "dateModified": {"type": "string", "format": "date"},
                    "contentDigest": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$",
                    },
                    "license": {"const": LICENSE_URL},
                    "ordering": {
                        "const": "alphabetical_by_app_name_not_a_ranking"
                    },
                    "recordCount": {"type": "integer", "minimum": 1},
                },
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "url",
                        "external_url",
                        "title",
                        "content_text",
                        "date_modified",
                        "tags",
                        "language",
                    ],
                    "properties": {
                        "id": {
                            "type": "string",
                            "format": "uri",
                            "pattern": (
                                "^https://apps\\.apple\\.com/app/id[0-9]+$"
                            ),
                        },
                        "url": {"type": "string", "format": "uri"},
                        "external_url": {
                            "type": "string",
                            "format": "uri",
                            "pattern": (
                                "^https://apps\\.apple\\.com/app/id[0-9]+"
                            ),
                        },
                        "title": {"type": "string", "minLength": 1},
                        "content_text": {"type": "string", "minLength": 1},
                        "date_modified": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "tags": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "language": {"enum": list(OFFICIAL_LOCALES)},
                    },
                },
            },
        },
    }


def openapi_document() -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Verified iOS App Catalog API",
            "summary": (
                "Match user needs to verified live iOS apps in 50 locales."
            ),
            "description": (
                "Read-only static catalogs with localized summaries, localized search "
                "terms, factual capabilities and directly attributable App Store links. "
                "Records are alphabetical and are not rankings."
            ),
            "version": API_VERSION,
            "license": {"name": "CC BY 4.0", "url": LICENSE_URL},
        },
        "servers": [{"url": API_BASE, "description": "GitHub Pages static API"}],
        "externalDocs": {
            "description": "Human-readable catalog and filtering tool",
            "url": portfolio_app_finder.canonical("en"),
        },
        "tags": [
            {
                "name": "Verified iOS apps",
                "description": (
                    "Live App Store records with no fabricated price, rating or review."
                ),
            }
        ],
        "paths": {
            "/index.json": {
                "get": {
                    "tags": ["Verified iOS apps"],
                    "summary": "List all available locale catalogs",
                    "operationId": "listVerifiedIosAppCatalogLocales",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "API index and locale endpoints.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "./index.schema.json"}
                                }
                            },
                        }
                    },
                }
            },
            "/locales/{locale}.json": {
                "get": {
                    "tags": ["Verified iOS apps"],
                    "summary": "Get the verified app catalog for one locale",
                    "operationId": "getLocalizedVerifiedIosAppCatalog",
                    "security": [],
                    "parameters": [
                        {
                            "name": "locale",
                            "in": "path",
                            "required": True,
                            "description": "Apple App Store locale identifier.",
                            "schema": {
                                "type": "string",
                                "enum": list(OFFICIAL_LOCALES),
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": (
                                "Alphabetical localized catalog with direct App Store links."
                            ),
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "./catalog.schema.json"}
                                }
                            },
                        }
                    },
                }
            },
            "/feeds/{locale}.json": {
                "get": {
                    "tags": ["Verified iOS apps"],
                    "summary": (
                        "Get the localized catalog as a JSON Feed 1.1 document"
                    ),
                    "operationId": "getLocalizedVerifiedIosAppJsonFeed",
                    "security": [],
                    "parameters": [
                        {
                            "name": "locale",
                            "in": "path",
                            "required": True,
                            "description": "Apple App Store locale identifier.",
                            "schema": {
                                "type": "string",
                                "enum": list(OFFICIAL_LOCALES),
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": (
                                "Localized JSON Feed with direct App Store links."
                            ),
                            "content": {
                                "application/feed+json": {
                                    "schema": {"$ref": "./feed.schema.json"}
                                },
                                "application/json": {
                                    "schema": {"$ref": "./feed.schema.json"}
                                },
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "IndexResponse": {"$ref": "./index.schema.json"},
                "CatalogResponse": {"$ref": "./catalog.schema.json"},
                "FeedResponse": {"$ref": "./feed.schema.json"},
            }
        },
        "security": [],
        "x-static-read-only": True,
        "x-personal-data-requested": False,
        "x-result-order": "alphabetical_by_app_name_not_a_ranking",
    }


def _schema_graph(
    locale: str,
    records: list[dict[str, object]],
    modified: str,
) -> dict[str, object]:
    copy = COPY[locale]
    canonical = (
        api_url()
        if locale == "en"
        else f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
    )
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "TechArticle",
                "@id": f"{canonical}#docs",
                "headline": copy["title"],
                "description": copy["description"],
                "url": canonical,
                "inLanguage": copy["lang"],
                "dateModified": modified,
                "mainEntity": {
                    "@type": "Dataset",
                    "name": "Verified Independent iOS App Catalog",
                    "description": copy["description"],
                    "url": canonical,
                    "license": LICENSE_URL,
                    "isAccessibleForFree": True,
                    "distribution": {
                        "@type": "DataDownload",
                        "encodingFormat": (
                            "application/vnd.oai.openapi+json;version=3.1"
                        ),
                        "contentUrl": api_url("openapi.json"),
                    },
                },
            },
            {
                "@type": "ItemList",
                "name": "Verified live iOS apps in alphabetical order",
                "numberOfItems": len(records),
                "itemListOrder": (
                    "https://schema.org/ItemListOrderAscending"
                ),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "url": record["canonical_app_store_url"],
                        "item": {
                            "@type": "MobileApplication",
                            "name": record["name"],
                            "operatingSystem": "iOS",
                            "applicationCategory": record["category"],
                            "url": record["canonical_app_store_url"],
                        },
                    }
                    for record in records
                ],
            },
        ],
    }


def render_docs(
    locale: str,
    records: list[dict[str, object]],
    modified: str,
) -> str:
    copy = COPY[locale]
    canonical = (
        api_url()
        if locale == "en"
        else f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
    )
    alternate = (
        f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
        if locale == "en"
        else api_url()
    )
    finder_locale = "en" if locale == "en" else "zh-Hant"
    locale_links = "".join(
        f'<a href="{html.escape(locale_url(item), quote=True)}">{item}</a>'
        for item in OFFICIAL_LOCALES
    )
    app_links = "".join(
        '<article><h3>{name}</h3><a rel="nofollow noopener" '
        'href="{url}">{store}</a></article>'.format(
            name=html.escape(str(record["name"])),
            url=html.escape(
                appstore_url(
                    str(record["key"]),
                    _campaign("en-US" if locale == "en" else "zh-Hant"),
                ),
                quote=True,
            ),
            store=html.escape(copy["store"]),
        )
        for record in records
    )
    schema = json.dumps(
        _schema_graph(locale, records, modified),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    sample_locale = "en-US" if locale == "en" else "zh-Hant"
    return f"""<!doctype html>
<html lang="{copy['lang']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title><meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{modified}"><link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{api_url()}"><link rel="alternate" hreflang="zh-Hant" href="{SITE}/zh-Hant/{API_PATH.as_posix()}/">
<link rel="alternate" hreflang="x-default" href="{api_url()}">
<link rel="alternate" type="application/feed+json" title="Lumi Studio · {sample_locale}" href="{feed_url(sample_locale)}">
<link rel="service" type="application/vnd.oai.openapi+json;version=3.1" href="{api_url('openapi.json')}">
<script type="application/ld+json">{schema}</script>
<style>:root{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#16211e}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 10% 0,#e5fff4,transparent 30%),#f7faf9;line-height:1.6}}main,footer{{width:min(1040px,calc(100% - 32px));margin:auto}}header{{border-bottom:1px solid #dbe8e2;background:#ffffffdc;backdrop-filter:blur(14px)}}nav{{width:min(1040px,calc(100% - 32px));min-height:62px;margin:auto;display:flex;align-items:center;justify-content:space-between}}a{{color:#176c57;font-weight:800;text-decoration:none}}.hero{{padding:58px 0 24px}}.eyebrow,h1,h2,h3{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.eyebrow{{color:#176c57;font-size:.78rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase}}h1{{margin:.15em 0;font-size:clamp(1.75rem,5vw,3.7rem);line-height:1.08}}.lead{{max-width:820px;color:#5d6965;font-size:1.1rem}}.actions,.locales{{display:flex;flex-wrap:wrap;gap:10px}}.actions a,.locales a{{border:1px solid #cfe0d9;border-radius:999px;padding:9px 13px;background:#fff}}section{{margin:22px 0;padding:24px;border:1px solid #dbe8e2;border-radius:24px;background:#ffffffea;box-shadow:0 16px 42px rgba(29,73,60,.07)}}pre{{overflow:auto;border-radius:16px;background:#14201c;color:#dffbef;padding:18px}}.apps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}article{{min-width:0;border:1px solid #dbe8e2;border-radius:16px;padding:15px;background:#fff}}article h3{{margin:0 0 8px;font-size:1rem}}footer{{padding:18px 0 48px;color:#64706c;font-size:.9rem}}</style></head>
<body><header><nav><a href="{SITE}/index.html">iOS App Guide</a><a href="{alternate}">{html.escape(copy['switch'])}</a></nav></header>
<main><div class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p>
<div class="actions"><a href="{api_url('openapi.json')}">{html.escape(copy['openapi'])}</a><a href="{feed_url(sample_locale)}">{html.escape(copy['feed'])}</a><a href="{api_url('index.json')}">{html.escape(copy['index'])}</a><a href="{api_url('catalog.schema.json')}">{html.escape(copy['schema'])}</a><a href="{portfolio_app_finder.canonical(finder_locale)}">{html.escape(copy['finder'])}</a></div></div>
<section><h2>{html.escape(copy['usage'])}</h2><p>{html.escape(copy['usage_text'])}</p><pre><code>curl -fsSL {locale_url(sample_locale)}</code></pre></section>
<section><h2>{html.escape(copy['locales'])}</h2><div class="locales">{locale_links}</div></section>
<section><h2>{html.escape(copy['contract'])}</h2><p>{html.escape(copy['contract_text'])}</p></section>
<section><h2>{html.escape(copy['apps'])}</h2><div class="apps">{app_links}</div></section></main>
<footer>{html.escape(copy['footer'])}</footer></body></html>
"""


def validate_artifacts(
    records: list[dict[str, object]],
    index: dict[str, object],
    catalogs: dict[str, dict[str, object]],
    feeds: dict[str, dict[str, object]],
    openapi: dict[str, object],
) -> None:
    require_official_locale_coverage("ios-app-catalog-api", catalogs)
    require_official_locale_coverage("ios-app-catalog-feeds", feeds)
    expected_keys = [str(record["key"]) for record in records]
    expected_ids = [
        f"https://apps.apple.com/app/id{record['app_store_id']}"
        for record in records
    ]
    if index["locale_count"] != len(OFFICIAL_LOCALES):
        raise ValueError("API locale count does not match official locales")
    if [item["locale"] for item in index["locales"]] != list(
        OFFICIAL_LOCALES
    ):
        raise ValueError("API index locale order drifted")
    if [item["feed"] for item in index["locales"]] != [
        feed_url(locale) for locale in OFFICIAL_LOCALES
    ]:
        raise ValueError("API index feed discovery drifted")
    if not SHA256_RE.fullmatch(str(index["content_digest"])):
        raise ValueError("API content digest must be SHA-256")
    for locale, payload in catalogs.items():
        if payload["locale"] != locale:
            raise ValueError(f"Locale payload mismatch: {locale}")
        if payload["content_digest"] != index["content_digest"]:
            raise ValueError(f"Content digest mismatch: {locale}")
        apps = payload["apps"]
        if payload["record_count"] != len(records):
            raise ValueError(f"Record count mismatch: {locale}")
        if [str(app["key"]) for app in apps] != expected_keys:
            raise ValueError(f"App order or coverage mismatch: {locale}")
        for app in apps:
            app_id = str(app["app_store_id"])
            if not str(app["app_store_url"]).startswith(
                f"https://apps.apple.com/app/id{app_id}?"
            ):
                raise ValueError(
                    f"Missing direct App Store campaign link: {locale}/{app['key']}"
                )
            if not str(app["guide_url"]).startswith(f"{SITE}/{locale}/"):
                raise ValueError(
                    f"Localized guide mismatch: {locale}/{app['key']}"
                )
            if not app["summary"] or not app["search_terms"]:
                raise ValueError(
                    f"Missing localized discovery text: {locale}/{app['key']}"
                )
        feed = feeds[locale]
        if feed["language"] != locale or feed["feed_url"] != feed_url(locale):
            raise ValueError(f"JSON Feed locale mismatch: {locale}")
        extension = feed["_lumi_catalog"]
        if (
            extension["contentDigest"] != index["content_digest"]
            or extension["recordCount"] != len(records)
        ):
            raise ValueError(f"JSON Feed catalog metadata mismatch: {locale}")
        items = feed["items"]
        if [str(item["id"]) for item in items] != expected_ids:
            raise ValueError(f"JSON Feed app order or coverage mismatch: {locale}")
        for app, item in zip(apps, items, strict=True):
            if item["language"] != locale:
                raise ValueError(f"JSON Feed item language mismatch: {locale}")
            if item["url"] != app["guide_url"]:
                raise ValueError(f"JSON Feed guide mismatch: {locale}")
            if item["content_text"] != app["summary"]:
                raise ValueError(f"JSON Feed summary mismatch: {locale}")
            if "ct=iag_feed_" not in str(item["external_url"]):
                raise ValueError(f"JSON Feed campaign link missing: {locale}")
        if len(_json(feed).encode("utf-8")) > FEED_MAX_BYTES:
            raise ValueError(f"JSON Feed exceeds size budget: {locale}")
    if set(openapi["paths"]) != {
        "/index.json",
        "/locales/{locale}.json",
        "/feeds/{locale}.json",
    }:
        raise ValueError("OpenAPI paths do not match the static API surface")


def _json(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def build(
    pages: Path = PAGES,
    *,
    live_keys: set[str] | list[str],
) -> list[str]:
    records = portfolio_app_finder.catalog_records(live_keys, pages)
    localized = {
        locale: [
            localized_record(record, locale, pages)
            for record in records
        ]
        for locale in OFFICIAL_LOCALES
    }
    require_official_locale_coverage("ios-app-catalog-api", localized)
    digest = _content_digest(localized)
    modified = _stable_modified(pages, digest)
    catalogs = {
        locale: catalog_payload(locale, apps, modified, digest)
        for locale, apps in localized.items()
    }
    feed_titles = {
        locale: _localized_directory_title(pages, locale)
        for locale in OFFICIAL_LOCALES
    }
    feeds = {
        locale: feed_payload(
            locale,
            feed_titles[locale],
            apps,
            modified,
            digest,
        )
        for locale, apps in localized.items()
    }
    index = index_payload(records, modified, digest)
    openapi = openapi_document()
    validate_artifacts(records, index, catalogs, feeds, openapi)

    api = pages / API_PATH
    locales_dir = api / "locales"
    feeds_dir = api / "feeds"
    locales_dir.mkdir(parents=True, exist_ok=True)
    feeds_dir.mkdir(parents=True, exist_ok=True)
    expected_files = {f"{locale}.json" for locale in OFFICIAL_LOCALES}
    for directory in (locales_dir, feeds_dir):
        for path in directory.glob("*.json"):
            if path.name not in expected_files:
                path.unlink()

    write_text_if_changed(api / "index.json", _json(index))
    write_text_if_changed(api / "index.schema.json", _json(index_schema()))
    write_text_if_changed(api / "catalog.schema.json", _json(catalog_schema()))
    write_text_if_changed(api / "feed.schema.json", _json(feed_schema()))
    write_text_if_changed(api / "openapi.json", _json(openapi))
    for locale, payload in catalogs.items():
        write_text_if_changed(
            locales_dir / f"{locale}.json",
            _json(payload),
        )
    for locale, payload in feeds.items():
        write_text_if_changed(
            feeds_dir / f"{locale}.json",
            _json(payload),
        )
    write_text_if_changed(
        api / "index.html",
        render_docs("en", records, modified),
    )
    zh_docs = pages / "zh-Hant" / API_PATH / "index.html"
    zh_docs.parent.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(
        zh_docs,
        render_docs("zh-Hant", records, modified),
    )
    build_api_discovery(pages)
    return [
        api_url(),
        f"{SITE}/zh-Hant/{API_PATH.as_posix()}/",
        api_url("index.json"),
        api_url("index.schema.json"),
        api_url("catalog.schema.json"),
        api_url("feed.schema.json"),
        api_url("openapi.json"),
        *[locale_url(locale) for locale in OFFICIAL_LOCALES],
        *[feed_url(locale) for locale in OFFICIAL_LOCALES],
    ]


def main() -> None:
    live = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    urls = build(live_keys=live)
    print(
        f"verified iOS app catalog API -> {len(live)} apps × "
        f"{len(OFFICIAL_LOCALES)} locales ({len(urls)} URLs)"
    )


if __name__ == "__main__":
    main()
