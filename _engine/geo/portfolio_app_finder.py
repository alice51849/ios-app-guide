#!/usr/bin/env python3
"""Generate a bilingual, local-only finder for every verified live app."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

import answer_portfolio  # noqa: E402
from appstore_live import LOOKUP_COUNTRIES, live_app_keys  # noqa: E402
import gen_app_catalog  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
import gen_mobile_app_identity  # noqa: E402
import queries  # noqa: E402
from videogen.registry import (  # noqa: E402
    APPS,
    APPSTORE,
    VALID_PURCHASE_MODELS,
    appstore_url,
)

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "private-pay-once-iphone-app-finder"
DATA_SLUG = "verified-ios-app-finder-catalog"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
CONTENT_DATE = answer_portfolio.CONTENT_DATE
APP_CATALOG_API = f"{SITE}/api/v1/ios-app-catalog"

UI = {
    "en": {
        "home": f"{SITE}/index.html",
        "tools": f"{SITE}/tools/",
        "switch": "繁體中文",
        "eyebrow": "Verified live portfolio · local-only filters",
        "verified": "{count} verified live apps",
        "alphabetical": "Alphabetical · never a ranking",
        "private": "No account, storage or analytics",
        "search": "What do you need to do?",
        "search_placeholder": "Try passport photo, kids math, PDF scan or sleep",
        "category": "Category",
        "purchase": "Purchase model",
        "privacy": "Privacy or offline fact",
        "device": "Apple surface",
        "all_categories": "Every category",
        "all_purchase": "Every current model",
        "one_time": "Any one-time option",
        "paid_upfront": "Paid download",
        "free_with_lifetime_unlock": "Free to start · lifetime unlock",
        "free": "Free",
        "flexible": "Flexible · check listing",
        "neutral": "Check current listing",
        "all_privacy": "Any published privacy fact",
        "offline": "Offline",
        "no_account": "No account",
        "no_ads": "No ads",
        "no_tracking": "No tracking",
        "private_or_on_device": "Private or on-device",
        "all_devices": "Any iPhone app",
        "widget": "Home Screen widget",
        "apple_watch": "Apple Watch",
        "clear": "Clear all filters",
        "count": "{shown} of {total} apps match",
        "empty": "No exact match. Clear one filter to broaden the verified results.",
        "why": "Why it may fit",
        "store": "View on the App Store",
        "category_labels": gen_app_catalog.L10N["en"]["categories"],
        "purchase_labels": {
            "paid_upfront": "Paid download",
            "free_with_lifetime_unlock": "Free to start · lifetime unlock",
            "free": "Free",
            "flexible": "Flexible · check listing",
            "neutral": "Check current listing",
        },
        "capability_labels": {
            "offline": "Offline",
            "no_account": "No account",
            "no_ads": "No ads",
            "no_tracking": "No tracking",
            "private_or_on_device": "Private / on-device",
            "widget": "Widget",
            "apple_watch": "Apple Watch",
        },
        "data_title": "Agent-readable verified catalogue",
        "data_text": (
            "Download the same alphabetical records as JSON with a JSON Schema. "
            "The catalogue contains no invented price, rank, rating or review."
        ),
        "download_json": "JSON catalogue",
        "download_schema": "JSON Schema",
        "download_openapi": "50-locale OpenAPI",
        "copy": "Copy finder link",
        "share": "Share finder",
        "copied": "Finder link copied.",
        "copy_failed": "Copy is unavailable. Copy the URL from the address bar.",
        "share_cancelled": "Sharing was cancelled.",
        "sources_title": "Specifications and attribution",
        "sources_text": (
            "App availability is checked against Apple's public lookup service in "
            "the US, Taiwan, Japan and UK. App links use Apple's campaign token. "
            "The machine graph uses ItemList and MobileApplication without fake offers or ratings."
        ),
        "apple_source": "Apple campaign-link guidance",
        "google_source": "Google software-app structured data",
        "schema_source": "Schema.org ItemList",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "Filter the verified live iOS app portfolio by task and published "
            "facts. Return alphabetical matches with truthful fit text and one "
            "attributed App Store URL per result; never treat the order as a ranking."
        ),
        "webmcp_query_description": (
            "Plain-language task or feature, such as passport photo, kids math, "
            "offline scan, travel plan or sleep."
        ),
        "license_text": (
            "CC BY 4.0 covers this original catalogue compilation, not Apple or app trademarks."
        ),
        "faq_title": "Questions",
        "index_title": "Private & Pay-Once iPhone App Finder",
        "index_description": (
            "Filter every verified live app by task, purchase model, privacy fact "
            "and Apple device surface."
        ),
        "footer": (
            "Free client-side finder. Results are alphabetical and factual, not a "
            "ranking, endorsement score or guarantee."
        ),
    },
    "zh-Hant": {
        "home": f"{SITE}/zh-Hant/index.html",
        "tools": f"{SITE}/zh-Hant/tools/",
        "switch": "English",
        "eyebrow": "已驗證上架組合 · 本機篩選",
        "verified": "{count} 款已驗證上架 App",
        "alphabetical": "依名稱排序 · 絕非排行榜",
        "private": "免帳號、不儲存、無分析",
        "search": "你想完成什麼？",
        "search_placeholder": "輸入證件照、兒童數學、PDF 掃描或睡眠",
        "category": "類別",
        "purchase": "購買模式",
        "privacy": "隱私或離線事實",
        "device": "Apple 使用介面",
        "all_categories": "全部類別",
        "all_purchase": "全部目前模式",
        "one_time": "任何一次性付費選項",
        "paid_upfront": "付費下載",
        "free_with_lifetime_unlock": "免費開始 · 永久解鎖",
        "free": "免費",
        "flexible": "彈性模式 · 查看上架頁",
        "neutral": "查看目前上架頁",
        "all_privacy": "任何已公開隱私事實",
        "offline": "離線使用",
        "no_account": "免帳號",
        "no_ads": "無廣告",
        "no_tracking": "無追蹤",
        "private_or_on_device": "隱私優先或裝置端",
        "all_devices": "任何 iPhone App",
        "widget": "主畫面小工具",
        "apple_watch": "Apple Watch",
        "clear": "清除全部篩選",
        "count": "符合 {shown}／{total} 款 App",
        "empty": "沒有完全符合的項目；清除一項篩選即可放寬已驗證結果。",
        "why": "可能適合的原因",
        "store": "前往 App Store 查看",
        "category_labels": gen_app_catalog.L10N["zh-Hant"]["categories"],
        "purchase_labels": {
            "paid_upfront": "付費下載",
            "free_with_lifetime_unlock": "免費開始 · 永久解鎖",
            "free": "免費",
            "flexible": "彈性模式 · 查看上架頁",
            "neutral": "查看目前上架頁",
        },
        "capability_labels": {
            "offline": "離線使用",
            "no_account": "免帳號",
            "no_ads": "無廣告",
            "no_tracking": "無追蹤",
            "private_or_on_device": "隱私優先／裝置端",
            "widget": "主畫面小工具",
            "apple_watch": "Apple Watch",
        },
        "data_title": "Agent 可讀的已驗證目錄",
        "data_text": "可下載相同的依名稱排序 JSON 資料與 JSON Schema；目錄不包含捏造的價格、名次、評分或評論。",
        "download_json": "JSON 目錄",
        "download_schema": "JSON Schema",
        "download_openapi": "50 語系 OpenAPI",
        "copy": "複製篩選器連結",
        "share": "分享篩選器",
        "copied": "已複製篩選器連結。",
        "copy_failed": "無法自動複製，請從網址列複製本頁連結。",
        "share_cancelled": "已取消分享。",
        "sources_title": "規格與歸因",
        "sources_text": (
            "App 供應狀態會透過 Apple 公開 lookup service 核對美國、台灣、日本與英國；App 連結使用 Apple campaign token。機器圖譜使用 ItemList 與 MobileApplication，不加入虛假 offers 或評分。"
        ),
        "apple_source": "Apple campaign link 指南",
        "google_source": "Google 軟體 App 結構化資料",
        "schema_source": "Schema.org ItemList",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "依任務與公開事實篩選已驗證上架的 iOS App；回傳依名稱排序的符合項目、"
            "真實適用原因及每筆一個可歸因 App Store 網址，不得把順序視為排名。"
        ),
        "webmcp_query_description": (
            "以白話描述任務或功能，例如證件照、兒童數學、離線掃描、旅遊規劃或睡眠。"
        ),
        "license_text": "CC BY 4.0 僅涵蓋這份原創目錄彙編，不涵蓋 Apple 或各 App 商標。",
        "faq_title": "常見問題",
        "index_title": "隱私優先、一次買斷 iPhone App 篩選器",
        "index_description": "依任務、購買模式、隱私事實與 Apple 使用介面，篩選每款已驗證上架 App。",
        "footer": "免費瀏覽器端篩選器。結果依事實與名稱排序，不是排行、推薦分數或成果保證。",
    },
}


def canonical(locale: str) -> str:
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def data_url(suffix: str) -> str:
    return f"{SITE}/data/{DATA_SLUG}{suffix}"


def _fact_text(app: dict[str, object]) -> str:
    values = [
        app.get("sub", ""),
        app.get("tag", ""),
        *app.get("cta_bullets", []),
        *app.get("keywords", []),
    ]
    return " ".join(str(value) for value in values if value).casefold()


def explicit_capabilities(app: dict[str, object]) -> dict[str, bool]:
    facts = _fact_text(app)
    return {
        "offline": "offline" in facts,
        "no_account": "no account" in facts,
        "no_ads": "no ads" in facts or "no third-party ads" in facts,
        "no_tracking": "no tracking" in facts,
        "private_or_on_device": (
            "private" in facts or "on-device" in facts
        ),
        "widget": (
            "home screen widget" in facts or "widget + watch" in facts
        ),
        "apple_watch": (
            "apple watch" in facts or "widget + watch" in facts
        ),
    }


def _campaign_url(key: str) -> str:
    campaign = f"iag_finder_{key}"
    if len(campaign) > 30 or not re.fullmatch(r"[A-Za-z0-9_]+", campaign):
        raise ValueError(f"Invalid finder campaign token: {campaign}")
    return appstore_url(key, campaign)


def localized_summary(key: str, locale: str, pages: Path) -> str:
    summary = gen_app_catalog.localized_summary(key, locale, pages)
    if (
        locale == "en-US"
        and len(summary) >= 145
        and not summary.endswith((".", "!", "?", "…", '"', "”", "'"))
    ):
        return str(APPS[key].get("sub") or summary).strip()
    return summary


def catalog_records(
    live_keys: set[str] | list[str],
    pages: Path = PAGES,
) -> list[dict[str, object]]:
    live = set(live_keys)
    if not live:
        raise ValueError("Portfolio finder requires at least one verified live app")
    unknown = live - set(APPS)
    if unknown:
        raise ValueError(f"Unknown verified app keys: {sorted(unknown)}")
    records = []
    for key in live:
        app = APPS[key]
        app_id = APPSTORE.get(key)
        if not app_id:
            raise ValueError(f"Verified app is missing an App Store ID: {key}")
        model = app.get("purchase_model", "neutral")
        if model not in VALID_PURCHASE_MODELS:
            raise ValueError(f"Invalid purchase model for {key}: {model}")
        bullets = [
            str(value).strip()
            for value in app.get("cta_bullets", [])
            if str(value).strip()
        ]
        keywords = [
            str(value).strip()
            for value in app.get("keywords", [])
            if str(value).strip()
        ]
        category = str(app.get("category", "other"))
        records.append(
            {
                "key": key,
                "app_store_id": str(app_id),
                "name": str(app["name"]),
                "category": category,
                "category_labels": {
                    "en": UI["en"]["category_labels"].get(
                        category, UI["en"]["category_labels"]["other"]
                    ),
                    "zh-Hant": UI["zh-Hant"]["category_labels"].get(
                        category,
                        UI["zh-Hant"]["category_labels"]["other"],
                    ),
                },
                "summaries": {
                    "en": localized_summary(key, "en-US", pages),
                    "zh-Hant": localized_summary(key, "zh-Hant", pages),
                },
                "purchase_model": model,
                "purchase_labels": {
                    "en": UI["en"]["purchase_labels"][model],
                    "zh-Hant": UI["zh-Hant"]["purchase_labels"][model],
                },
                "one_time_option": model
                in {"paid_upfront", "free_with_lifetime_unlock"},
                "features": bullets,
                "keywords": keywords,
                "capabilities": explicit_capabilities(app),
                "canonical_app_store_url": (
                    gen_mobile_app_identity.canonical_store_url(str(app_id))
                ),
                "verified_live": True,
            }
        )
    return sorted(
        records,
        key=lambda record: (
            str(record["name"]).casefold(),
            str(record["key"]),
        ),
    )


def dataset_payload(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "name": "Verified Independent iOS App Finder Catalogue",
        "description": answer_portfolio.COPY["en"]["description"],
        "question": answer_portfolio.PORTFOLIO_QUERY,
        "date_modified": CONTENT_DATE,
        "license": LICENSE_URL,
        "ordering": "alphabetical_by_app_name_not_a_ranking",
        "availability_verification": {
            "source": "Apple iTunes Lookup API",
            "markets": [country.upper() for country in LOOKUP_COUNTRIES],
            "retirement_rule": "Retire after three consecutive verified misses",
        },
        "record_count": len(records),
        "apps": records,
    }


def dataset_json(records: list[dict[str, object]]) -> str:
    return json.dumps(
        dataset_payload(records),
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def dataset_schema() -> str:
    app_required = [
        "key",
        "app_store_id",
        "name",
        "category",
        "category_labels",
        "summaries",
        "purchase_model",
        "purchase_labels",
        "one_time_option",
        "features",
        "keywords",
        "capabilities",
        "canonical_app_store_url",
        "verified_live",
    ]
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": data_url(".schema.json"),
        "title": "Verified Independent iOS App Finder Catalogue",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "name",
            "description",
            "question",
            "date_modified",
            "license",
            "ordering",
            "availability_verification",
            "record_count",
            "apps",
        ],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "question": {"const": answer_portfolio.PORTFOLIO_QUERY},
            "date_modified": {"type": "string", "format": "date"},
            "license": {"type": "string", "format": "uri"},
            "ordering": {
                "const": "alphabetical_by_app_name_not_a_ranking"
            },
            "availability_verification": {
                "type": "object",
                "required": ["source", "markets", "retirement_rule"],
                "properties": {
                    "source": {"type": "string"},
                    "markets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "uniqueItems": True,
                    },
                    "retirement_rule": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "record_count": {"type": "integer", "minimum": 1},
            "apps": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": app_required,
                    "properties": {
                        "key": {"type": "string", "minLength": 1},
                        "app_store_id": {
                            "type": "string",
                            "pattern": "^[0-9]{9,12}$",
                        },
                        "name": {"type": "string", "minLength": 1},
                        "category": {"type": "string", "minLength": 1},
                        "category_labels": {
                            "$ref": "#/$defs/localizedText"
                        },
                        "summaries": {"$ref": "#/$defs/localizedText"},
                        "purchase_model": {
                            "enum": sorted(VALID_PURCHASE_MODELS)
                        },
                        "purchase_labels": {
                            "$ref": "#/$defs/localizedText"
                        },
                        "one_time_option": {"type": "boolean"},
                        "features": {
                            "type": "array",
                            "items": {"type": "string"},
                            "uniqueItems": True,
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "uniqueItems": True,
                        },
                        "capabilities": {
                            "type": "object",
                            "required": [
                                "offline",
                                "no_account",
                                "no_ads",
                                "no_tracking",
                                "private_or_on_device",
                                "widget",
                                "apple_watch",
                            ],
                            "additionalProperties": False,
                            "properties": {
                                name: {"type": "boolean"}
                                for name in (
                                    "offline",
                                    "no_account",
                                    "no_ads",
                                    "no_tracking",
                                    "private_or_on_device",
                                    "widget",
                                    "apple_watch",
                                )
                            },
                        },
                        "canonical_app_store_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "verified_live": {"const": True},
                    },
                },
            },
        },
        "$defs": {
            "localizedText": {
                "type": "object",
                "required": ["en", "zh-Hant"],
                "additionalProperties": False,
                "properties": {
                    "en": {"type": "string", "minLength": 1},
                    "zh-Hant": {"type": "string", "minLength": 1},
                },
            }
        },
    }
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def structured_data(
    locale: str,
    records: list[dict[str, object]],
) -> str:
    copy = answer_portfolio.COPY[locale]
    app_items = []
    for record in records:
        entity = gen_mobile_app_identity.mobile_app_schema(
            record["app_store_id"],
            record["name"],
            record["category"],
        )
        entity.pop("@context")
        entity["description"] = record["summaries"][locale]
        entity["featureList"] = record["features"]
        entity["additionalProperty"] = [
            {
                "@type": "PropertyValue",
                "name": "Purchase model",
                "value": record["purchase_labels"][locale],
            },
            {
                "@type": "PropertyValue",
                "name": "Availability verification",
                "value": "Apple lookup: US, TW, JP and GB",
            },
        ]
        app_items.append(
            {
                "@type": "ListItem",
                "@id": f"{canonical(locale)}#app-{record['key']}",
                "url": record["canonical_app_store_url"],
                "item": entity,
            }
        )
    faq = [
        {
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        for question, answer in copy["faqs"]
    ]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{canonical(locale)}#webpage",
                "name": copy["title"],
                "description": copy["description"],
                "url": canonical(locale),
                "inLanguage": copy["html_lang"],
                "dateModified": CONTENT_DATE,
                "mainEntity": {
                    "@type": "ItemList",
                    "@id": f"{canonical(locale)}#verified-apps",
                    "name": "Verified apps in alphabetical order",
                    "numberOfItems": len(records),
                    "itemListOrder": (
                        "https://schema.org/ItemListOrderAscending"
                    ),
                    "itemListElement": app_items,
                },
            },
            {
                "@type": "Dataset",
                "name": "Verified Independent iOS App Finder Catalogue",
                "description": copy["description"],
                "url": canonical(locale),
                "license": LICENSE_URL,
                "isAccessibleForFree": True,
                "inLanguage": ["en", "zh-Hant"],
                "dateModified": CONTENT_DATE,
                "distribution": [
                    {
                        "@type": "DataDownload",
                        "encodingFormat": "application/json",
                        "contentUrl": data_url(".json"),
                    },
                    {
                        "@type": "DataDownload",
                        "encodingFormat": "application/schema+json",
                        "contentUrl": data_url(".schema.json"),
                    },
                ],
            },
            {
                "@type": "WebApplication",
                "name": copy["title"],
                "url": canonical(locale),
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Any modern browser",
                "browserRequirements": "JavaScript",
                "isAccessibleForFree": True,
                "inLanguage": copy["html_lang"],
                "dateModified": CONTENT_DATE,
                "featureList": [
                    "Local-only search and filtering",
                    "Alphabetical results without ranking",
                    "Verified live App Store portfolio",
                    "No account, submission, storage or analytics",
                    "Progressive read-only WebMCP tool for supporting browsers",
                ],
            },
            {
                "@type": "FAQPage",
                "inLanguage": copy["html_lang"],
                "mainEntity": faq,
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def category_options(locale: str, records: list[dict[str, object]]) -> str:
    copy = UI[locale]
    categories = sorted(
        {record["category"] for record in records},
        key=lambda value: copy["category_labels"].get(
            value, copy["category_labels"]["other"]
        ).casefold(),
    )
    return "\n".join(
        f'<option value="{html.escape(category)}">'
        f'{html.escape(copy["category_labels"].get(category, copy["category_labels"]["other"]))}'
        "</option>"
        for category in categories
    )


def webmcp_input_schema(
    locale: str,
    records: list[dict[str, object]],
) -> dict[str, object]:
    copy = UI[locale]
    categories = sorted({record["category"] for record in records})
    purchase_models = sorted(
        {record["purchase_model"] for record in records}
    )
    privacy_facts = sorted(
        {
            key
            for record in records
            for key, enabled in record["capabilities"].items()
            if enabled
            and key
            in {
                "offline",
                "no_account",
                "no_ads",
                "no_tracking",
                "private_or_on_device",
            }
        }
    )
    device_surfaces = sorted(
        {
            key
            for record in records
            for key in ("widget", "apple_watch")
            if record["capabilities"][key]
        }
    )
    properties = {
        "query": {
            "type": "string",
            "maxLength": 120,
            "description": copy["webmcp_query_description"],
        },
        "category": {
            "type": "string",
            "enum": categories,
            "description": copy["category"],
        },
        "purchase_model": {
            "type": "string",
            "enum": ["one_time", *purchase_models],
            "description": copy["purchase"],
        },
    }
    if privacy_facts:
        properties["privacy_fact"] = {
            "type": "string",
            "enum": privacy_facts,
            "description": copy["privacy"],
        }
    if device_surfaces:
        properties["device_surface"] = {
            "type": "string",
            "enum": device_surfaces,
            "description": copy["device"],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }


def _record_search_text(record: dict[str, object]) -> str:
    return " ".join(
        [
            record["key"],
            record["name"],
            record["category"],
            record["summaries"]["en"],
            record["summaries"]["zh-Hant"],
            *record["features"],
            *record["keywords"],
        ]
    ).casefold()


def _record_privacy_facts(record: dict[str, object]) -> list[str]:
    return [
        key
        for key, enabled in record["capabilities"].items()
        if enabled
        and key
        in {
            "offline",
            "no_account",
            "no_ads",
            "no_tracking",
            "private_or_on_device",
        }
    ]


def _record_device_surfaces(record: dict[str, object]) -> list[str]:
    return [
        key
        for key in ("widget", "apple_watch")
        if record["capabilities"][key]
    ]


def webmcp_records(
    locale: str,
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "search": _record_search_text(record),
            "category": record["category"],
            "purchase_model": record["purchase_model"],
            "one_time_option": record["one_time_option"],
            "privacy_facts": _record_privacy_facts(record),
            "device_surfaces": _record_device_surfaces(record),
            "name": record["name"],
            "why_it_may_fit": record["summaries"][locale],
            "app_store_url": _campaign_url(record["key"]),
        }
        for record in records
    ]


def app_cards(
    locale: str,
    records: list[dict[str, object]],
) -> str:
    copy = UI[locale]
    cards = []
    for record in records:
        capabilities = [
            key
            for key, enabled in record["capabilities"].items()
            if enabled
        ]
        badges = [
            copy["category_labels"].get(
                record["category"], copy["category_labels"]["other"]
            ),
            record["purchase_labels"][locale],
            *[
                copy["capability_labels"][key]
                for key in capabilities
            ],
        ]
        badge_html = "".join(
            f'<span class="fact">{html.escape(value)}</span>'
            for value in dict.fromkeys(badges)
        )
        search_text = _record_search_text(record)
        devices = ["iphone"]
        if record["capabilities"]["widget"]:
            devices.append("widget")
        if record["capabilities"]["apple_watch"]:
            devices.append("apple_watch")
        cards.append(
            f'<article class="app-card" data-app-card '
            f'data-search="{html.escape(search_text)}" '
            f'data-category="{html.escape(record["category"])}" '
            f'data-purchase="{html.escape(record["purchase_model"])}" '
            f'data-one-time="{str(record["one_time_option"]).lower()}" '
            f'data-privacy="{html.escape(" ".join(capabilities))}" '
            f'data-device="{html.escape(" ".join(devices))}">'
            f'<h2>{html.escape(record["name"])}</h2>'
            f'<div class="facts">{badge_html}</div>'
            f'<p class="why"><strong>{html.escape(copy["why"])}:</strong> '
            f'{html.escape(record["summaries"][locale])}</p>'
            f'<a class="store" rel="nofollow noopener" '
            f'href="{html.escape(_campaign_url(record["key"]))}">'
            f'{html.escape(copy["store"])}</a></article>'
        )
    return "\n".join(cards)


def render_page(
    locale: str,
    records: list[dict[str, object]],
) -> str:
    copy = UI[locale]
    answer = answer_portfolio.COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    method = "".join(
        f"<li>{html.escape(item)}</li>" for item in answer["method"]
    )
    boundaries = "".join(
        f"<li>{html.escape(item)}</li>" for item in answer["boundaries"]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(response)}</p></details>"
        for question, response in answer["faqs"]
    )
    js_copy = json.dumps(
        {
            "count": copy["count"],
            "empty": copy["empty"],
            "copied": copy["copied"],
            "copy_failed": copy["copy_failed"],
            "share_cancelled": copy["share_cancelled"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    page = r"""<!doctype html>
<html lang="__HTML_LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESCRIPTION__">
<link rel="canonical" href="__CANONICAL__">
<link rel="alternate" hreflang="en" href="__EN_URL__">
<link rel="alternate" hreflang="zh-Hant" href="__ZH_URL__">
<link rel="alternate" hreflang="x-default" href="__EN_URL__">
<link rel="service" type="application/vnd.oai.openapi+json;version=3.1" href="__OPENAPI_URL__">
__FEEDS__
<meta property="og:type" content="website">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESCRIPTION__">
<meta property="og:url" content="__CANONICAL__">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">__SCHEMA__</script>
<style>
:root{--ink:#17201d;--muted:#5d6864;--line:#dce7e2;--paper:#fff;--mint:#e9f8f1;--teal:#126b57;--violet:#6750c9;--shadow:0 22px 70px rgba(27,68,57,.11);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 7% 2%,#e3fff3 0,transparent 31%),radial-gradient(circle at 94% 9%,#eee9ff 0,transparent 34%),#f8fbf9;color:var(--ink);line-height:1.58}a{color:var(--teal)}.wrap{width:min(1180px,calc(100% - 30px));margin:auto}
.top{position:sticky;top:0;z-index:5;border-bottom:1px solid rgba(220,231,226,.84);background:rgba(248,251,249,.92);backdrop-filter:blur(18px)}.nav{min-height:64px;display:flex;align-items:center;justify-content:space-between;gap:12px}.nav a{font-weight:850;text-decoration:none;white-space:nowrap}
.hero{padding:64px 0 28px}.eyebrow{margin:0 0 9px;color:var(--teal);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}h1{margin:0;font-size:clamp(.78rem,4vw,3.65rem);line-height:1.05;letter-spacing:-.045em;white-space:nowrap}.lead{max-width:860px;margin:18px 0 0;color:var(--muted);font-size:clamp(1rem,2vw,1.2rem)}
.badges,.facts,.actions{display:flex;gap:8px;flex-wrap:wrap}.badges{margin-top:20px}.badge,.fact{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:rgba(255,255,255,.86);font-size:.8rem;font-weight:850;white-space:nowrap}.fact{padding:5px 9px;background:#f5faf7}
.card{border:1px solid var(--line);border-radius:28px;background:rgba(255,255,255,.94);box-shadow:var(--shadow);padding:clamp(20px,4vw,32px);margin-bottom:22px}.filters{display:grid;grid-template-columns:1fr;gap:14px}@media(min-width:700px){.filters{grid-template-columns:2fr 1fr 1fr}}@media(min-width:1020px){.filters{grid-template-columns:2fr 1fr 1fr 1fr 1fr}}
label{display:block;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}input,select{width:100%;min-height:50px;margin-top:6px;border:1px solid #c8d7d0;border-radius:15px;padding:11px 38px 11px 13px;background:#fff;color:var(--ink);font:inherit}
button,.download,.store{min-height:48px;border-radius:999px;padding:12px 18px;font:inherit;font-weight:900;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}button,.download{border:1px solid #c8d7d0;background:#fff;color:var(--teal)}.store{display:flex;align-items:center;justify-content:center;margin-top:auto;border:0;background:linear-gradient(135deg,var(--teal),#178c70);color:#fff!important;box-shadow:0 10px 28px rgba(18,107,87,.2)}
.clear{width:100%;margin-top:14px}.status{min-height:1.4em;margin:14px 0 0;color:var(--teal);font-weight:850}.results{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px;margin-bottom:22px}.app-card{display:flex;flex-direction:column;gap:13px;min-width:0;border:1px solid var(--line);border-radius:24px;background:rgba(255,255,255,.96);box-shadow:0 14px 40px rgba(27,68,57,.08);padding:22px}.app-card h2{margin:0;font-size:1.2rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.app-card p{margin:0;color:var(--muted)}.why strong{color:var(--ink)}[hidden]{display:none!important}
.two{display:grid;gap:20px}@media(min-width:820px){.two{grid-template-columns:1fr 1fr}}h2.section-title,.card>h2{margin:0 0 10px;font-size:clamp(1.35rem,3vw,2rem);letter-spacing:-.025em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.list{padding-left:1.25rem}.list li{margin:.58rem 0}.actions{margin-top:18px}.source a{font-weight:850}details{border-top:1px solid var(--line);padding:14px 0}summary{font-weight:850;cursor:pointer}footer{padding:28px 0 52px;color:var(--muted);font-size:.9rem}
button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid rgba(103,80,201,.42);outline-offset:3px}@media(max-width:520px){.card{border-radius:22px}.nav{font-size:.88rem}.results{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="__HOME__">iOS App Guide</a><nav><a href="__TOOLS__">__TOOLS_LABEL__</a> · <a href="__SWITCH_URL__">__SWITCH__</a></nav></div></header>
<main>
<section class="hero wrap"><p class="eyebrow">__EYEBROW__</p><h1>__HEADING__</h1><p class="lead">__LEAD__</p>
<div class="badges"><span class="badge">__VERIFIED__</span><span class="badge">__ALPHABETICAL__</span><span class="badge">__PRIVATE__</span></div></section>
<section class="wrap card">
  <div class="filters">
    <label>__SEARCH__<input id="search" type="search" autocomplete="off" placeholder="__SEARCH_PLACEHOLDER__"></label>
    <label>__CATEGORY__<select id="category"><option value="">__ALL_CATEGORIES__</option>__CATEGORY_OPTIONS__</select></label>
    <label>__PURCHASE__<select id="purchase"><option value="">__ALL_PURCHASE__</option><option value="one_time">__ONE_TIME__</option><option value="paid_upfront">__PAID_UPFRONT__</option><option value="free_with_lifetime_unlock">__LIFETIME__</option><option value="free">__FREE__</option><option value="flexible">__FLEXIBLE__</option><option value="neutral">__NEUTRAL__</option></select></label>
    <label>__PRIVACY_LABEL__<select id="privacy"><option value="">__ALL_PRIVACY__</option><option value="offline">__OFFLINE__</option><option value="no_account">__NO_ACCOUNT__</option><option value="no_ads">__NO_ADS__</option><option value="no_tracking">__NO_TRACKING__</option><option value="private_or_on_device">__PRIVATE_DEVICE__</option></select></label>
    <label>__DEVICE__<select id="device"><option value="">__ALL_DEVICES__</option><option value="widget">__WIDGET__</option><option value="apple_watch">__APPLE_WATCH__</option></select></label>
  </div>
  <button class="clear" id="clear" type="button">__CLEAR__</button>
  <p class="status" id="result-count" role="status"></p><p class="status" id="empty" hidden></p>
</section>
<section class="wrap results" id="results">__APP_CARDS__</section>
<section class="wrap two"><article class="card"><h2>__METHOD_TITLE__</h2><ul class="list">__METHOD__</ul></article><article class="card"><h2>__BOUNDARIES_TITLE__</h2><ul class="list">__BOUNDARIES__</ul></article></section>
<section class="wrap card"><h2>__DATA_TITLE__</h2><p>__DATA_TEXT__</p><div class="actions"><a class="download" href="__DATA_URL__" download>__DOWNLOAD_JSON__</a><a class="download" href="__SCHEMA_URL__">__DOWNLOAD_SCHEMA__</a><a class="download" href="__OPENAPI_URL__">__DOWNLOAD_OPENAPI__</a><button id="copy" type="button">__COPY__</button><button id="share" type="button">__SHARE__</button></div><p class="status" id="share-status" role="status"></p></section>
<section class="wrap card source"><h2>__SOURCES_TITLE__</h2><p>__SOURCES_TEXT__</p><p><a href="__APPLE_SOURCE_URL__">__APPLE_SOURCE__</a> · <a href="__GOOGLE_SOURCE_URL__">__GOOGLE_SOURCE__</a> · <a href="__SCHEMA_SOURCE_URL__">__SCHEMA_SOURCE__</a> · <a href="__WEBMCP_SOURCE_URL__">__WEBMCP_SOURCE__</a> · <a href="__LICENSE_URL__">CC BY 4.0</a></p><p>__LICENSE_TEXT__</p></section>
<section class="wrap card"><h2>__FAQ_TITLE__</h2>__FAQ__</section>
</main>
<footer><div class="wrap">__FOOTER__</div></footer>
<script>
const I18N=__JS_COPY__;
const WEBMCP_INPUT_SCHEMA=__WEBMCP_INPUT_SCHEMA__;
const WEBMCP_RECORDS=__WEBMCP_RECORDS__;
const WEBMCP_TOOL_DESCRIPTION=__WEBMCP_DESCRIPTION__;
const cards=[...document.querySelectorAll("[data-app-card]")];
const fields=["search","category","purchase","privacy","device"].map(id=>document.getElementById(id));
const count=document.getElementById("result-count");
const empty=document.getElementById("empty");
const shareStatus=document.getElementById("share-status");
function tokens(value){return value.split(" ").filter(Boolean);}
function update(){
  const query=fields[0].value.trim().toLocaleLowerCase();
  const category=fields[1].value;
  const purchase=fields[2].value;
  const privacy=fields[3].value;
  const device=fields[4].value;
  let shown=0;
  const matches=[];
  for(const card of cards){
    const purchaseMatch=!purchase||(purchase==="one_time"?card.dataset.oneTime==="true":card.dataset.purchase===purchase);
    const visible=(!query||card.dataset.search.includes(query))&&(!category||card.dataset.category===category)&&purchaseMatch&&(!privacy||tokens(card.dataset.privacy).includes(privacy))&&(!device||tokens(card.dataset.device).includes(device));
    card.hidden=!visible;if(visible){shown++;matches.push(card);}
  }
  count.textContent=I18N.count.replace("{shown}",String(shown)).replace("{total}",String(cards.length));
  empty.textContent=I18N.empty;empty.hidden=shown!==0;
  return matches;
}
function toolText(input,name){const value=input[name];if(value===undefined)return"";if(typeof value!=="string")throw new TypeError(`${name} must be a string.`);return value;}
function toolSelectValue(value,name){if(!value)return"";const values=WEBMCP_INPUT_SCHEMA.properties[name]?.enum||[];if(!values.includes(value))throw new RangeError(`${name} is not a supported filter value.`);return value;}
async function registerWebMcp(){
  if(!document.modelContext?.registerTool)return;
  await document.modelContext.registerTool({
    name:"find_verified_ios_apps",
    description:WEBMCP_TOOL_DESCRIPTION,
    inputSchema:WEBMCP_INPUT_SCHEMA,
    annotations:{readOnlyHint:true,untrustedContentHint:false},
    execute:async(input={})=>{
      if(input===null||typeof input!=="object"||Array.isArray(input))throw new TypeError("WebMCP input must be an object.");
      const query=toolText(input,"query").trim().toLocaleLowerCase();
      if(query.length>120)throw new RangeError("query exceeds 120 characters.");
      const category=toolSelectValue(toolText(input,"category"),"category");
      const purchase=toolSelectValue(toolText(input,"purchase_model"),"purchase_model");
      const privacy=toolSelectValue(toolText(input,"privacy_fact"),"privacy_fact");
      const device=toolSelectValue(toolText(input,"device_surface"),"device_surface");
      const matches=WEBMCP_RECORDS.filter(item=>
        (!query||item.search.includes(query))&&
        (!category||item.category===category)&&
        (!purchase||(purchase==="one_time"?item.one_time_option:item.purchase_model===purchase))&&
        (!privacy||item.privacy_facts.includes(privacy))&&
        (!device||item.device_surfaces.includes(device))
      );
      return JSON.stringify({
        result_type:"verified_ios_app_matches",
        ordering:"alphabetical_by_app_name_not_a_ranking",
        match_count:matches.length,
        matches:matches.map(({name,why_it_may_fit,app_store_url})=>({name,why_it_may_fit,app_store_url}))
      });
    }
  });
}
async function copyLink(){try{await navigator.clipboard.writeText("__CANONICAL__");shareStatus.textContent=I18N.copied;}catch(error){shareStatus.textContent=I18N.copy_failed;}}
async function shareLink(){if(navigator.share){try{await navigator.share({title:document.title,url:"__CANONICAL__"});return;}catch(error){if(error&&error.name==="AbortError"){shareStatus.textContent=I18N.share_cancelled;return;}}}await copyLink();}
for(const field of fields)field.addEventListener("input",update);
document.getElementById("clear").addEventListener("click",()=>{for(const field of fields)field.value="";update();fields[0].focus();});
document.getElementById("copy").addEventListener("click",copyLink);
document.getElementById("share").addEventListener("click",shareLink);
update();
registerWebMcp().catch(error=>console.error("WebMCP tool registration failed.",error));
</script>
</body></html>
"""
    replacements = {
        "__HTML_LANG__": html.escape(answer["html_lang"]),
        "__TITLE__": html.escape(answer["title"]),
        "__DESCRIPTION__": html.escape(answer["description"]),
        "__CANONICAL__": canonical(locale),
        "__EN_URL__": canonical("en"),
        "__ZH_URL__": canonical("zh-Hant"),
        "__FEEDS__": feed_discovery_links(),
        "__SCHEMA__": structured_data(locale, records),
        "__HOME__": html.escape(copy["home"]),
        "__TOOLS__": html.escape(copy["tools"]),
        "__TOOLS_LABEL__": "免費工具" if locale == "zh-Hant" else "Free tools",
        "__SWITCH_URL__": canonical(other_locale),
        "__SWITCH__": html.escape(copy["switch"]),
        "__EYEBROW__": html.escape(copy["eyebrow"]),
        "__HEADING__": html.escape(answer["heading"]),
        "__LEAD__": html.escape(answer["lead"]),
        "__VERIFIED__": html.escape(
            copy["verified"].replace("{count}", str(len(records)))
        ),
        "__ALPHABETICAL__": html.escape(copy["alphabetical"]),
        "__PRIVATE__": html.escape(copy["private"]),
        "__SEARCH__": html.escape(copy["search"]),
        "__SEARCH_PLACEHOLDER__": html.escape(copy["search_placeholder"]),
        "__CATEGORY__": html.escape(copy["category"]),
        "__PURCHASE__": html.escape(copy["purchase"]),
        "__PRIVACY_LABEL__": html.escape(copy["privacy"]),
        "__DEVICE__": html.escape(copy["device"]),
        "__ALL_CATEGORIES__": html.escape(copy["all_categories"]),
        "__CATEGORY_OPTIONS__": category_options(locale, records),
        "__ALL_PURCHASE__": html.escape(copy["all_purchase"]),
        "__ONE_TIME__": html.escape(copy["one_time"]),
        "__PAID_UPFRONT__": html.escape(copy["paid_upfront"]),
        "__LIFETIME__": html.escape(copy["free_with_lifetime_unlock"]),
        "__FREE__": html.escape(copy["free"]),
        "__FLEXIBLE__": html.escape(copy["flexible"]),
        "__NEUTRAL__": html.escape(copy["neutral"]),
        "__ALL_PRIVACY__": html.escape(copy["all_privacy"]),
        "__OFFLINE__": html.escape(copy["offline"]),
        "__NO_ACCOUNT__": html.escape(copy["no_account"]),
        "__NO_ADS__": html.escape(copy["no_ads"]),
        "__NO_TRACKING__": html.escape(copy["no_tracking"]),
        "__PRIVATE_DEVICE__": html.escape(copy["private_or_on_device"]),
        "__ALL_DEVICES__": html.escape(copy["all_devices"]),
        "__WIDGET__": html.escape(copy["widget"]),
        "__APPLE_WATCH__": html.escape(copy["apple_watch"]),
        "__CLEAR__": html.escape(copy["clear"]),
        "__APP_CARDS__": app_cards(locale, records),
        "__METHOD_TITLE__": html.escape(answer["method_title"]),
        "__METHOD__": method,
        "__BOUNDARIES_TITLE__": html.escape(answer["boundaries_title"]),
        "__BOUNDARIES__": boundaries,
        "__DATA_TITLE__": html.escape(copy["data_title"]),
        "__DATA_TEXT__": html.escape(copy["data_text"]),
        "__DATA_URL__": data_url(".json"),
        "__SCHEMA_URL__": data_url(".schema.json"),
        "__OPENAPI_URL__": f"{APP_CATALOG_API}/openapi.json",
        "__DOWNLOAD_JSON__": html.escape(copy["download_json"]),
        "__DOWNLOAD_SCHEMA__": html.escape(copy["download_schema"]),
        "__DOWNLOAD_OPENAPI__": html.escape(copy["download_openapi"]),
        "__COPY__": html.escape(copy["copy"]),
        "__SHARE__": html.escape(copy["share"]),
        "__SOURCES_TITLE__": html.escape(copy["sources_title"]),
        "__SOURCES_TEXT__": html.escape(copy["sources_text"]),
        "__APPLE_SOURCE_URL__": answer_portfolio.APPLE_CAMPAIGN_SOURCE,
        "__APPLE_SOURCE__": html.escape(copy["apple_source"]),
        "__GOOGLE_SOURCE_URL__": answer_portfolio.GOOGLE_SCHEMA_SOURCE,
        "__GOOGLE_SOURCE__": html.escape(copy["google_source"]),
        "__SCHEMA_SOURCE_URL__": answer_portfolio.SCHEMA_ITEM_LIST_SOURCE,
        "__SCHEMA_SOURCE__": html.escape(copy["schema_source"]),
        "__WEBMCP_SOURCE_URL__": answer_portfolio.WEBMCP_SOURCE,
        "__WEBMCP_SOURCE__": html.escape(copy["webmcp_source"]),
        "__LICENSE_URL__": LICENSE_URL,
        "__LICENSE_TEXT__": html.escape(copy["license_text"]),
        "__FAQ_TITLE__": html.escape(copy["faq_title"]),
        "__FAQ__": faq,
        "__FOOTER__": html.escape(copy["footer"]),
        "__JS_COPY__": js_copy,
        "__WEBMCP_INPUT_SCHEMA__": json.dumps(
            webmcp_input_schema(locale, records),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_RECORDS__": json.dumps(
            webmcp_records(locale, records),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_DESCRIPTION__": json.dumps(
            copy["webmcp_description"],
            ensure_ascii=False,
        ),
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    unresolved = sorted(set(re.findall(r"__[A-Z][A-Z_]+__", page)))
    if unresolved:
        raise ValueError(f"Unresolved template markers: {unresolved}")
    return page


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    copy = UI[locale]
    card = (
        f'<article class="card third" data-tool="{SLUG}">'
        f'<h2><a href="{SLUG}.html">{html.escape(copy["index_title"])}</a></h2>'
        f'<p>{html.escape(copy["index_description"])}</p></article>'
    )
    pattern = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>',
        re.S,
    )
    if pattern.search(text):
        updated = pattern.sub(card, text, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in text:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = text.replace(marker, marker + card, 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def build(
    pages: Path = PAGES,
    *,
    live_keys: set[str] | list[str],
) -> list[str]:
    if queries.PORTFOLIO_CURATED.count(
        answer_portfolio.PORTFOLIO_QUERY
    ) != 1:
        raise ValueError("Portfolio finder query must be unique")
    records = catalog_records(live_keys, pages)
    data_dir = pages / "data"
    write_text_if_changed(
        data_dir / f"{DATA_SLUG}.json",
        dataset_json(records),
    )
    write_text_if_changed(
        data_dir / f"{DATA_SLUG}.schema.json",
        dataset_schema(),
    )
    outputs = []
    for locale in UI:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, records),
        )
        outputs.append(canonical(locale))
    _update_one_index(pages / "tools" / "index.html", "en")
    _update_one_index(
        pages / "zh-Hant" / "tools" / "index.html",
        "zh-Hant",
    )
    return outputs


def main() -> None:
    live = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    for output in build(live_keys=live):
        print(f"portfolio app finder -> {output}")
    print(f"catalog JSON -> {data_url('.json')}")
    print(f"catalog schema -> {data_url('.schema.json')}")
    print(f"tools sitemap -> {write_tools_sitemap()} urls")


if __name__ == "__main__":
    main()
