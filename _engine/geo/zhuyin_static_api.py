#!/usr/bin/env python3
"""Build a versioned, no-key static API for all 37 Zhuyin symbols."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import (  # noqa: E402
    render_versioned_page,
    write_text_if_changed,
)
from static_api_catalog import build_api_discovery  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from zhuyin_croissant_dataset import (  # noqa: E402
    APP_ID,
    APP_KEY,
    APP_NAME,
    FIELD_NAMES,
    LICENSE,
    SITE,
    SOURCE_PAGE,
    VERSION as DATASET_VERSION,
    records,
    validate_records,
)


PAGES = HERE / "pages"
API_VERSION = "1.0.0"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
SLUG = "bopomofo-symbols"
API_PATH = Path("api") / "v1" / SLUG
API_BASE = f"{SITE}/{API_PATH.as_posix()}"
DATASET_PAGE = f"{SITE}/data/zhuyin-bopomofo-ml-dataset.html"
DATASET_METADATA = (
    f"{SITE}/data/zhuyin-bopomofo-ml-dataset.croissant.jsonld"
)
SKOS_PAGE = f"{SITE}/data/zhuyin-bopomofo-vocabulary.html"
SKOS_JSONLD = f"{SITE}/data/zhuyin-bopomofo-vocabulary.jsonld"

COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo Symbols Static API",
        "description": (
            "A free, versioned OpenAPI interface for all 37 Zhuyin symbols "
            "with Unicode, Pinyin, IPA, categories and examples."
        ),
        "eyebrow": "OpenAPI 3.1.1 · Read-only · CC BY 4.0",
        "lead": (
            "Load one complete index or fetch a stable JSON endpoint for any "
            "symbol from U+3105 through U+3129. No API key or account."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "badges": (
            "No API key",
            "38 JSON endpoints",
            "37 complete symbols",
            "Versioned v1",
        ),
        "start": "Start here",
        "start_text": (
            "The index lists every endpoint. The OpenAPI document and JSON "
            "Schemas describe the complete, read-only response surface."
        ),
        "index": "API index",
        "openapi": "OpenAPI 3.1.1",
        "index_schema": "Index schema",
        "symbol_schema": "Symbol schema",
        "dataset": "Croissant dataset",
        "endpoints": "Symbol endpoints",
        "symbol": "Symbol",
        "endpoint": "Endpoint",
        "usage": "Minimal examples",
        "curl": "Command line",
        "browser": "Browser JavaScript",
        "scope": "Scope and non-uses",
        "scope_text": (
            "This API is a reference inventory, not a pronunciation service, "
            "text converter, speech model, learner assessment or curriculum."
        ),
        "operation": "Operational contract",
        "operation_text": (
            "Static, cacheable and read-only: no parameters, writes, accounts, "
            "tracking or uptime promise. Pin /v1/ and retain attribution."
        ),
        "provenance": "License and provenance",
        "provenance_text": (
            "The API is generated deterministically from the CC BY 4.0 "
            "Croissant table and stable SKOS concept identifiers."
        ),
        "source": "Canonical symbol table",
        "skos": "SKOS vocabulary",
        "app_title": "Optional practice layer",
        "app_text": (
            "Lumi Bopomofo adds short, on-device learning activities. The API "
            "and open dataset remain free and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Independent machine-readable reference data for education and "
            "software development."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音符號靜態 API",
        "description": (
            "免費、版本化的 OpenAPI 介面，完整提供 37 個注音符號的 Unicode、"
            "漢語拼音、IPA、分類與例字。"
        ),
        "eyebrow": "OpenAPI 3.1.1 · 唯讀 · CC BY 4.0",
        "lead": (
            "可一次載入完整索引，或依穩定網址取得 U+3105 至 U+3129 的任一"
            "注音符號 JSON；不需 API 金鑰或帳號。"
        ),
        "language": "English",
        "back": "開放資料",
        "badges": (
            "免 API 金鑰",
            "38 個 JSON 端點",
            "完整 37 符號",
            "版本化 v1",
        ),
        "start": "從這裡開始",
        "start_text": (
            "索引列出全部端點；OpenAPI 文件與 JSON Schema 描述完整唯讀"
            "回應格式。"
        ),
        "index": "API 索引",
        "openapi": "OpenAPI 3.1.1",
        "index_schema": "索引 schema",
        "symbol_schema": "符號 schema",
        "dataset": "Croissant 資料集",
        "endpoints": "符號端點",
        "symbol": "符號",
        "endpoint": "端點",
        "usage": "最小使用範例",
        "curl": "命令列",
        "browser": "瀏覽器 JavaScript",
        "scope": "範圍與不適用情境",
        "scope_text": (
            "本 API 是參考清單，不是發音服務、文字轉換器、語音模型、學習者"
            "評量或課程。"
        ),
        "operation": "運作契約",
        "operation_text": (
            "靜態、可快取且唯讀：沒有參數、寫入、帳號、追蹤或正常運作時間"
            "承諾。請固定使用 /v1/ 並保留來源標示。"
        ),
        "provenance": "授權與來源",
        "provenance_text": (
            "API 由 CC BY 4.0 Croissant 表格與穩定 SKOS 概念識別碼以固定"
            "流程產生。"
        ),
        "source": "標準符號表",
        "skos": "SKOS 詞彙",
        "app_title": "選用練習層",
        "app_text": (
            "Lumi 注音星球提供裝置端短活動；API 與開放資料仍維持免費且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": "供教育與軟體開發使用的獨立機器可讀參考資料。",
    },
}


def api_url(path: str = "") -> str:
    return f"{API_BASE}/{path}" if path else f"{API_BASE}/"


def symbol_url(symbol_id: str) -> str:
    return api_url(f"symbols/{symbol_id}.json")


def _scope(rows: list[dict]) -> dict:
    return {
        "symbolCount": len(rows),
        "initialCount": sum(row["category"] == "initial" for row in rows),
        "medialCount": sum(row["category"] == "medial" for row in rows),
        "finalCount": sum(row["category"] == "final" for row in rows),
        "unicodeRange": "U+3105-U+3129",
    }


def api_index(rows: list[dict]) -> dict:
    return {
        "$schema": api_url("index.schema.json"),
        "apiVersion": API_VERSION,
        "datasetVersion": DATASET_VERSION,
        "generatedFrom": DATASET_METADATA,
        "license": LICENSE,
        "languages": ["zh-Bopo", "zh-Latn", "en"],
        "scope": _scope(rows),
        "documentation": {
            "en": api_url(),
            "zh-Hant": f"{SITE}/zh-Hant/{API_PATH.as_posix()}/",
        },
        "openapi": api_url("openapi.json"),
        "symbols": [
            {
                "symbolId": row["symbol_id"],
                "symbol": row["symbol"],
                "unicode": row["unicode"],
                "pinyin": row["pinyin"],
                "category": row["category"],
                "url": symbol_url(row["symbol_id"]),
            }
            for row in rows
        ],
    }


def symbol_payload(row: dict) -> dict:
    return {
        "$schema": api_url("symbol.schema.json"),
        "apiVersion": API_VERSION,
        "datasetVersion": DATASET_VERSION,
        "license": LICENSE,
        "symbol": row,
        "provenance": {
            "concept": row["concept_uri"],
            "dataset": DATASET_METADATA,
            "vocabulary": SKOS_JSONLD,
        },
    }


def _symbol_id_pattern() -> str:
    return r"^u31(?:0[5-9A-F]|1[0-9A-F]|2[0-9])$"


def _unicode_pattern() -> str:
    return r"^U\+31(?:0[5-9A-F]|1[0-9A-F]|2[0-9])$"


def _ecma_regex_literal(value: str) -> str:
    metacharacters = frozenset(r"\.^$|?*+()[]{}")
    return "".join(
        f"\\{character}" if character in metacharacters else character
        for character in value
    )


def index_schema(rows: list[dict]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("index.schema.json"),
        "title": "Bopomofo Symbols API index",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "apiVersion",
            "datasetVersion",
            "generatedFrom",
            "license",
            "languages",
            "scope",
            "documentation",
            "openapi",
            "symbols",
        ],
        "properties": {
            "$schema": {"const": api_url("index.schema.json")},
            "apiVersion": {"const": API_VERSION},
            "datasetVersion": {"const": DATASET_VERSION},
            "generatedFrom": {"const": DATASET_METADATA},
            "license": {"const": LICENSE},
            "languages": {"const": ["zh-Bopo", "zh-Latn", "en"]},
            "scope": {"const": _scope(rows)},
            "documentation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["en", "zh-Hant"],
                "properties": {
                    "en": {"const": api_url()},
                    "zh-Hant": {
                        "const": f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
                    },
                },
            },
            "openapi": {"const": api_url("openapi.json")},
            "symbols": {
                "type": "array",
                "minItems": 37,
                "maxItems": 37,
                "uniqueItems": True,
                "items": {"$ref": "#/$defs/endpoint"},
            },
        },
        "$defs": {
            "endpoint": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "symbolId",
                    "symbol",
                    "unicode",
                    "pinyin",
                    "category",
                    "url",
                ],
                "properties": {
                    "symbolId": {
                        "type": "string",
                        "pattern": _symbol_id_pattern(),
                    },
                    "symbol": {
                        "type": "string",
                        "enum": [row["symbol"] for row in rows],
                    },
                    "unicode": {
                        "type": "string",
                        "pattern": _unicode_pattern(),
                    },
                    "pinyin": {"type": "string", "minLength": 1},
                    "category": {
                        "type": "string",
                        "enum": ["initial", "medial", "final"],
                    },
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "pattern": (
                            "^"
                            + _ecma_regex_literal(api_url("symbols/"))
                            + r"u31(?:0[5-9A-F]|1[0-9A-F]|2[0-9])"
                            + r"\.json$"
                        ),
                    },
                },
            }
        },
    }


def symbol_schema(rows: list[dict]) -> dict:
    category_uris = sorted({row["category_uri"] for row in rows})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("symbol.schema.json"),
        "title": "Bopomofo Symbols API response",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "apiVersion",
            "datasetVersion",
            "license",
            "symbol",
            "provenance",
        ],
        "properties": {
            "$schema": {"const": api_url("symbol.schema.json")},
            "apiVersion": {"const": API_VERSION},
            "datasetVersion": {"const": DATASET_VERSION},
            "license": {"const": LICENSE},
            "symbol": {"$ref": "#/$defs/symbol"},
            "provenance": {
                "type": "object",
                "additionalProperties": False,
                "required": ["concept", "dataset", "vocabulary"],
                "properties": {
                    "concept": {
                        "type": "string",
                        "format": "uri",
                        "pattern": "#u31",
                    },
                    "dataset": {"const": DATASET_METADATA},
                    "vocabulary": {"const": SKOS_JSONLD},
                },
            },
        },
        "$defs": {
            "symbol": {
                "type": "object",
                "additionalProperties": False,
                "required": list(FIELD_NAMES),
                "properties": {
                    "order": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 37,
                    },
                    "symbol_id": {
                        "type": "string",
                        "pattern": _symbol_id_pattern(),
                    },
                    "concept_uri": {
                        "type": "string",
                        "format": "uri",
                        "pattern": "#u31",
                    },
                    "symbol": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1,
                    },
                    "unicode": {
                        "type": "string",
                        "pattern": _unicode_pattern(),
                    },
                    "pinyin": {"type": "string", "minLength": 1},
                    "ipa": {"type": "string", "minLength": 1},
                    "category": {
                        "type": "string",
                        "enum": ["initial", "medial", "final"],
                    },
                    "category_uri": {
                        "type": "string",
                        "enum": category_uris,
                    },
                    "example_character": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "example_pinyin": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "example_meaning_en": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
            }
        },
    }


def _operation_id(symbol_id: str) -> str:
    return f"getBopomofo{symbol_id[1:].upper()}"


def openapi_document(rows: list[dict]) -> dict:
    paths = {
        "/index.json": {
            "get": {
                "tags": ["Bopomofo symbols"],
                "summary": "List all 37 Zhuyin symbols",
                "operationId": "listBopomofoSymbols",
                "security": [],
                "responses": {
                    "200": {
                        "description": "The complete Bopomofo API index.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "./index.schema.json"}
                            }
                        },
                    }
                },
            }
        }
    }
    for row in rows:
        paths[f"/symbols/{row['symbol_id']}.json"] = {
            "get": {
                "tags": ["Bopomofo symbols"],
                "summary": (
                    f"Get {row['symbol']} ({row['unicode']}) with "
                    "Pinyin, IPA and an example"
                ),
                "operationId": _operation_id(row["symbol_id"]),
                "security": [],
                "responses": {
                    "200": {
                        "description": "One Bopomofo symbol record.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "./symbol.schema.json"}
                            }
                        },
                    }
                },
            }
        }
    return {
        "openapi": "3.1.1",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Bopomofo Symbols Static API",
            "summary": "The complete 37-symbol Zhuyin inventory.",
            "description": (
                "Versioned, read-only JSON endpoints generated from a CC BY "
                "4.0 table. No authentication, tracking or personal data."
            ),
            "version": API_VERSION,
            "license": {"name": "CC BY 4.0", "url": LICENSE},
        },
        "servers": [
            {"url": API_BASE, "description": "GitHub Pages static API"}
        ],
        "externalDocs": {
            "description": "Dataset card, field definitions and provenance",
            "url": DATASET_PAGE,
        },
        "tags": [
            {
                "name": "Bopomofo symbols",
                "description": (
                    "All 21 initials, 3 medials and 13 finals from "
                    "Unicode U+3105 through U+3129."
                ),
            }
        ],
        "paths": paths,
        "components": {
            "schemas": {
                "IndexResponse": {"$ref": "./index.schema.json"},
                "SymbolResponse": {"$ref": "./symbol.schema.json"},
            }
        },
        "security": [],
        "x-static-read-only": True,
        "x-api-key-required": False,
        "x-personal-data-requested": False,
    }


def validate_artifacts(
    rows: list[dict],
    index: dict,
    payloads: dict[str, dict],
    openapi: dict,
    index_schema_document: dict,
    symbol_schema_document: dict,
) -> None:
    validate_records(rows)
    expected_ids = [row["symbol_id"] for row in rows]
    if [item["symbolId"] for item in index["symbols"]] != expected_ids:
        raise ValueError("API index order drifted from the canonical dataset")
    if set(payloads) != set(expected_ids):
        raise ValueError("API symbol files do not match the canonical dataset")
    expected_paths = {"/index.json"} | {
        f"/symbols/{symbol_id}.json" for symbol_id in expected_ids
    }
    if set(openapi["paths"]) != expected_paths:
        raise ValueError("OpenAPI paths do not match generated endpoints")
    operation_ids = [
        operation["get"]["operationId"]
        for operation in openapi["paths"].values()
    ]
    if len(operation_ids) != len(set(operation_ids)):
        raise ValueError("OpenAPI operationId values must be unique")
    source_rows = {row["symbol_id"]: row for row in rows}
    for symbol_id, payload in payloads.items():
        if payload["symbol"] != source_rows[symbol_id]:
            raise ValueError(f"Symbol payload drifted from source: {symbol_id}")
        expected_provenance = {
            "concept": payload["symbol"]["concept_uri"],
            "dataset": DATASET_METADATA,
            "vocabulary": SKOS_JSONLD,
        }
        if payload["provenance"] != expected_provenance:
            raise ValueError(f"Concept provenance mismatch: {symbol_id}")
    encoded = json.dumps(
        {
            "index": index,
            "payloads": payloads,
            "openapi": openapi,
            "indexSchema": index_schema_document,
            "symbolSchema": symbol_schema_document,
        },
        ensure_ascii=False,
    )
    for forbidden in (
        "apps.apple.com",
        "SoftwareApplication",
        APP_NAME,
        APP_ID,
        f"id{APP_ID}",
    ):
        if forbidden in encoded:
            raise ValueError(f"Static API must remain app-independent: {forbidden}")


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match the registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _schema_graph(locale: str, app_public: bool, modified: str) -> dict:
    canonical = (
        api_url()
        if locale == "en"
        else f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
    )
    graph = [
        {
            "@type": "TechArticle",
            "@id": f"{canonical}#docs",
            "headline": COPY[locale]["title"],
            "description": COPY[locale]["description"],
            "url": canonical,
            "inLanguage": locale,
            "dateModified": modified,
            "license": LICENSE,
            "isBasedOn": [DATASET_PAGE, SKOS_PAGE],
            "mainEntity": {
                "@type": "Dataset",
                "name": "Complete 37-symbol Zhuyin (Bopomofo) inventory",
                "url": DATASET_PAGE,
                "license": LICENSE,
                "distribution": {
                    "@type": "DataDownload",
                    "encodingFormat": (
                        "application/vnd.oai.openapi+json;version=3.1"
                    ),
                    "contentUrl": api_url("openapi.json"),
                },
            },
        }
    ]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "applicationCategory": "EducationApplication",
                "operatingSystem": "iOS",
                "url": appstore_url(
                    APP_KEY, f"iag_bopomofo_api_{locale.lower()}"
                ),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def render_docs(
    rows: list[dict],
    locale: str,
    app_public: bool = False,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    canonical = (
        api_url()
        if locale == "en"
        else f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
    )
    other = (
        f"{SITE}/zh-Hant/{API_PATH.as_posix()}/"
        if locale == "en"
        else api_url()
    )
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    endpoint_rows = "".join(
        "<tr><td><strong>{symbol}</strong> {unicode}</td>"
        '<td><a href="{url}"><code>{path}</code></a></td></tr>'.format(
            symbol=html.escape(row["symbol"]),
            unicode=html.escape(row["unicode"]),
            url=html.escape(symbol_url(row["symbol_id"]), quote=True),
            path=html.escape(f"/symbols/{row['symbol_id']}.json"),
        )
        for row in rows
    )
    curl_example = f"curl -s {api_url('index.json')}"
    fetch_example = (
        f"const response = await fetch('{symbol_url('u3105')}');\n"
        "const record = await response.json();\n"
        "console.log(record.symbol.pinyin, record.symbol.ipa);"
    )
    app_block = ""
    if app_public:
        app_block = (
            '<section class="app"><p class="kicker">{title}</p><p>{text}</p>'
            '<a href="{url}" rel="nofollow noopener">{cta} &rarr;</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(
                    APP_KEY, f"iag_bopomofo_api_{locale.lower()}"
                ),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _schema_graph(locale, app_public, modified),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<link rel="alternate" hreflang="en" href="{api_url()}">
<link rel="alternate" hreflang="zh-Hant" href="{SITE}/zh-Hant/{API_PATH.as_posix()}/">
<link rel="alternate" hreflang="x-default" href="{api_url()}">
<link rel="service-desc" type="application/vnd.oai.openapi+json;version=3.1" href="{api_url('openapi.json')}">
<link rel="describedby" type="application/schema+json" href="{api_url('index.schema.json')}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#15213a;--sub:#59677e;--line:#dce4ef;--brand:#315fc4;--bg:#f4f7fc;--paper:#fff;--soft:#edf3ff;--code:#101827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}.wrap{{max-width:1020px;margin:auto;padding:24px 20px 72px}}a{{color:var(--brand)}}.top{{display:flex;justify-content:space-between;gap:16px;font-size:14px}}.top a{{font-weight:750;text-decoration:none;white-space:nowrap}}
.hero{{padding:52px 0 28px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,56px);line-height:1.07;letter-spacing:-.035em;margin:10px 0 16px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:820px}}p{{color:var(--sub)}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:700;white-space:nowrap}}
section{{margin-top:34px}}.panel,.app{{background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:23px;box-shadow:0 12px 30px rgba(27,44,79,.05)}}.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:17px}}.links a{{border:1px solid var(--line);border-radius:13px;padding:14px;text-decoration:none;font-weight:760;background:#fbfcff}}
.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:15px;background:#fff}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft)}}tr:last-child td{{border-bottom:0}}code{{font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}}pre{{background:var(--code);color:#edf2ff;border-radius:14px;padding:17px;overflow:auto}}.examples,.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.app a{{font-weight:800;text-decoration:none}}footer{{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}}@media(max-width:680px){{.examples,.two{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{DATASET_PAGE}">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(other, quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></header>
<section class="panel"><h2>{html.escape(copy['start'])}</h2><p>{html.escape(copy['start_text'])}</p><div class="links"><a href="{api_url('index.json')}">{html.escape(copy['index'])} &rarr;</a><a href="{api_url('openapi.json')}">{html.escape(copy['openapi'])} &rarr;</a><a href="{api_url('index.schema.json')}">{html.escape(copy['index_schema'])} &rarr;</a><a href="{api_url('symbol.schema.json')}">{html.escape(copy['symbol_schema'])} &rarr;</a><a href="{DATASET_PAGE}">{html.escape(copy['dataset'])} &rarr;</a></div></section>
<section><h2>{html.escape(copy['endpoints'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['symbol'])}</th><th>{html.escape(copy['endpoint'])}</th></tr></thead><tbody>{endpoint_rows}</tbody></table></div></section>
<section><h2>{html.escape(copy['usage'])}</h2><div class="examples"><div><h3>{html.escape(copy['curl'])}</h3><pre><code>{html.escape(curl_example)}</code></pre></div><div><h3>{html.escape(copy['browser'])}</h3><pre><code>{html.escape(fetch_example)}</code></pre></div></div></section>
<section class="two"><article class="panel"><h2>{html.escape(copy['scope'])}</h2><p>{html.escape(copy['scope_text'])}</p></article><article class="panel"><h2>{html.escape(copy['operation'])}</h2><p>{html.escape(copy['operation_text'])}</p></article></section>
<section class="panel"><h2>{html.escape(copy['provenance'])}</h2><p>{html.escape(copy['provenance_text'])}</p><div class="links"><a href="{SOURCE_PAGE}">{html.escape(copy['source'])} &rarr;</a><a href="{SKOS_PAGE}">{html.escape(copy['skos'])} &rarr;</a><a href="{LICENSE}" rel="license noopener">CC BY 4.0 &rarr;</a></div></section>
{app_block}
<footer>{html.escape(copy['footer'])}</footer>
</main>
</body>
</html>
"""


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    rows = records()
    validate_records(rows)
    index = api_index(rows)
    payloads = {
        row["symbol_id"]: symbol_payload(row)
        for row in rows
    }
    openapi = openapi_document(rows)
    index_schema_document = index_schema(rows)
    symbol_schema_document = symbol_schema(rows)
    validate_artifacts(
        rows,
        index,
        payloads,
        openapi,
        index_schema_document,
        symbol_schema_document,
    )

    output = pages / API_PATH
    symbol_directory = output / "symbols"
    zh_output = pages / "zh-Hant" / API_PATH
    for directory in (output, symbol_directory, zh_output):
        directory.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(output / "index.json", _json(index))
    write_text_if_changed(
        output / "index.schema.json", _json(index_schema_document)
    )
    write_text_if_changed(
        output / "symbol.schema.json", _json(symbol_schema_document)
    )
    write_text_if_changed(output / "openapi.json", _json(openapi))
    for symbol_id, payload in payloads.items():
        write_text_if_changed(
            symbol_directory / f"{symbol_id}.json", _json(payload)
        )

    public = is_app_public(pages) if app_public is None else app_public
    render_versioned_page(
        output / "index.html",
        lambda modified: render_docs(rows, "en", public, modified),
        INITIAL_DATE,
        TODAY,
    )
    render_versioned_page(
        zh_output / "index.html",
        lambda modified: render_docs(rows, "zh-Hant", public, modified),
        INITIAL_DATE,
        TODAY,
    )
    build_api_discovery(pages)
    return [
        f"{SITE}/api/",
        api_url(),
        f"{SITE}/zh-Hant/{API_PATH.as_posix()}/",
        api_url("index.json"),
        api_url("openapi.json"),
        api_url("index.schema.json"),
        api_url("symbol.schema.json"),
        *[symbol_url(symbol_id) for symbol_id in payloads],
    ]


if __name__ == "__main__":
    build()
