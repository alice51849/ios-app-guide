#!/usr/bin/env python3
"""Build a versioned, read-only static API from the family-travel taxonomy."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
from pathlib import Path

from family_travel_dataset import (
    APP_ID,
    APP_KEY,
    APP_NAME,
    APP_SHORT_NAME,
    SITE,
    SOURCE_DIR,
    is_app_public,
    load_dataset,
    render_versioned_page,
    write_text_if_changed,
)
from static_api_catalog import build_api_discovery
from videogen.registry import appstore_url


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
API_VERSION = "1.0.0"
TODAY = dt.date.today().isoformat()
SLUG = "family-travel-missions"
API_PATH = Path("api") / "v1" / SLUG
API_BASE = f"{SITE}/{API_PATH.as_posix()}"
DATASET_PAGE = f"{SITE}/data/{SLUG}.html"
DATASET_JSON = f"{SITE}/data/{SLUG}.json"

COPY = {
    "en": {
        "lang": "en",
        "title": "Family Travel Missions Static API",
        "description": (
            "A free, versioned static API for 12 bilingual, privacy-first family "
            "travel mission settings. No key, account or personal data."
        ),
        "eyebrow": "OpenAPI 3.1 · Read-only · CC BY 4.0",
        "lead": (
            "Use one stable index and 12 scenario endpoints to add English and "
            "Traditional Chinese observation prompts to research, education or travel tools."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "badges": ("No API key", "13 JSON endpoints", "English + zh-Hant", "Versioned v1"),
        "start": "Start here",
        "start_text": (
            "The index lists every scenario endpoint. The OpenAPI document describes "
            "the complete read-only surface and response schemas."
        ),
        "index": "API index",
        "openapi": "OpenAPI 3.1",
        "index_schema": "Index schema",
        "scenario_schema": "Scenario schema",
        "source": "Canonical dataset",
        "endpoints": "Scenario endpoints",
        "settings": "setting",
        "privacy": "Privacy and safety contract",
        "privacy_text": (
            "Responses contain no name, age, destination, location, photo, itinerary "
            "or completion record. Every prompt is optional, adult-supervised, stationary "
            "or seated, photo-free and unavailable to drivers."
        ),
        "usage": "Minimal examples",
        "curl": "Command line",
        "browser": "Browser JavaScript",
        "limits": "Operational notes",
        "limits_text": (
            "This is a static, cacheable, read-only API. There are no query parameters, "
            "writes, accounts or uptime promises. Pin /v1/ and retain attribution."
        ),
        "license": "License and provenance",
        "license_text": (
            "Original bilingual data is available under CC BY 4.0. Official references "
            "support selected safety boundaries but do not endorse this API."
        ),
        "app_title": "Optional digital travel layer",
        "app_text": (
            "Lumi Trip Planet adds an optional on-device activity layer. The API and "
            "open dataset remain free and independent."
        ),
        "app_cta": "View Lumi Trip Planet on the App Store",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "親子旅行任務靜態 API",
        "description": (
            "免費、版本化的英繁雙語隱私優先親子旅行任務靜態 API，涵蓋 12 種情境，"
            "不需金鑰、帳號或個資。"
        ),
        "eyebrow": "OpenAPI 3.1 · 唯讀 · CC BY 4.0",
        "lead": (
            "透過一個穩定索引與 12 個情境端點，將英繁雙語觀察提示加入研究、"
            "教育或旅行工具。"
        ),
        "language": "English",
        "back": "開放資料",
        "badges": ("免 API 金鑰", "13 個 JSON 端點", "英文＋繁體中文", "版本化 v1"),
        "start": "從這裡開始",
        "start_text": (
            "索引列出全部情境端點；OpenAPI 文件則描述完整唯讀介面與回應 schema。"
        ),
        "index": "API 索引",
        "openapi": "OpenAPI 3.1",
        "index_schema": "索引 schema",
        "scenario_schema": "情境 schema",
        "source": "標準資料集",
        "endpoints": "情境端點",
        "settings": "種情境",
        "privacy": "隱私與安全契約",
        "privacy_text": (
            "回應不含姓名、年齡、目的地、位置、照片、行程或完成紀錄。每個提示都可"
            "自由跳過、需大人陪同、只在原地或坐好時使用、不拍照，且駕駛不可參與。"
        ),
        "usage": "最小使用範例",
        "curl": "命令列",
        "browser": "瀏覽器 JavaScript",
        "limits": "運作說明",
        "limits_text": (
            "這是可快取、唯讀的靜態 API，沒有查詢參數、寫入、帳號或正常運作時間"
            "承諾。請固定使用 /v1/ 並保留來源標示。"
        ),
        "license": "授權與來源",
        "license_text": (
            "原創英繁雙語資料採 CC BY 4.0 授權；官方參考只支援部分安全界線，"
            "不代表官方為本 API 背書。"
        ),
        "app_title": "選用數位旅行層",
        "app_text": (
            "Lumi Trip Planet 提供選用的裝置端活動層；API 與開放資料仍維持"
            "免費且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi Trip Planet",
    },
}


def api_url(path: str = "") -> str:
    return f"{API_BASE}/{path}" if path else f"{API_BASE}/"


def scenario_url(scenario_id: str) -> str:
    return api_url(f"scenarios/{scenario_id}.json")


def api_index(dataset: dict) -> dict:
    return {
        "$schema": api_url("index.schema.json"),
        "apiVersion": API_VERSION,
        "datasetVersion": dataset["version"],
        "generatedFrom": DATASET_JSON,
        "license": dataset["license"],
        "languages": dataset["languages"],
        "scope": dataset["scope"],
        "privacyDesign": dataset["privacyDesign"],
        "documentation": {
            "en": api_url(),
            "zh-Hant": f"{SITE}/zh-Hant/{API_PATH.as_posix()}/",
        },
        "openapi": api_url("openapi.json"),
        "scenarios": [
            {
                "scenarioId": scenario["id"],
                "name": scenario["name"],
                "url": scenario_url(scenario["id"]),
            }
            for scenario in dataset["scenarios"]
        ],
    }


def scenario_payload(dataset: dict, scenario: dict) -> dict:
    reference_ids = set(scenario["officialReferenceIds"])
    return {
        "$schema": api_url("scenario.schema.json"),
        "apiVersion": API_VERSION,
        "datasetVersion": dataset["version"],
        "license": dataset["license"],
        "scenario": scenario,
        "participationModes": dataset["participationModes"],
        "officialReferences": [
            reference
            for reference in dataset["officialReferences"]
            if reference["id"] in reference_ids
        ],
    }


def index_schema(dataset: dict, canonical_schema: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("index.schema.json"),
        "title": "Family Travel Missions API index",
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
            "privacyDesign",
            "documentation",
            "openapi",
            "scenarios",
        ],
        "properties": {
            "$schema": {"const": api_url("index.schema.json")},
            "apiVersion": {"const": API_VERSION},
            "datasetVersion": {"const": dataset["version"]},
            "generatedFrom": {"const": DATASET_JSON},
            "license": {"const": dataset["license"]},
            "languages": {"const": dataset["languages"]},
            "scope": canonical_schema["properties"]["scope"],
            "privacyDesign": canonical_schema["properties"]["privacyDesign"],
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
            "scenarios": {
                "type": "array",
                "minItems": dataset["scope"]["scenarioCount"],
                "maxItems": dataset["scope"]["scenarioCount"],
                "items": {"$ref": "#/$defs/endpoint"},
            },
        },
        "$defs": {
            "localizedString": canonical_schema["$defs"]["localizedString"],
            "endpoint": {
                "type": "object",
                "additionalProperties": False,
                "required": ["scenarioId", "name", "url"],
                "properties": {
                    "scenarioId": canonical_schema["$defs"]["id"],
                    "name": {"$ref": "#/$defs/localizedString"},
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "pattern": (
                            "^https://alice51849\\.github\\.io/ios-app-guide/api/v1/"
                            "family-travel-missions/scenarios/"
                        ),
                    },
                },
            },
        },
    }


def scenario_schema(dataset: dict, canonical_schema: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": api_url("scenario.schema.json"),
        "title": "Family Travel Mission API scenario response",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "apiVersion",
            "datasetVersion",
            "license",
            "scenario",
            "participationModes",
            "officialReferences",
        ],
        "properties": {
            "$schema": {"const": api_url("scenario.schema.json")},
            "apiVersion": {"const": API_VERSION},
            "datasetVersion": {"const": dataset["version"]},
            "license": {"const": dataset["license"]},
            "scenario": {"$ref": "#/$defs/scenario"},
            "participationModes": {
                "type": "array",
                "minItems": dataset["scope"]["participationModeCount"],
                "maxItems": dataset["scope"]["participationModeCount"],
                "items": {"$ref": "#/$defs/participationMode"},
            },
            "officialReferences": {
                "type": "array",
                "items": {"$ref": "#/$defs/officialReference"},
            },
        },
        "$defs": {
            key: canonical_schema["$defs"][key]
            for key in (
                "id",
                "localizedString",
                "target",
                "scenario",
                "participationMode",
                "officialReference",
            )
        },
    }


def _operation_id(scenario_id: str) -> str:
    words = re.split(r"[^a-z0-9]+", scenario_id)
    return "get" + "".join(word.title() for word in words) + "Mission"


def openapi_document(dataset: dict) -> dict:
    paths = {
        "/index.json": {
            "get": {
                "tags": ["Family travel missions"],
                "summary": "List all family travel mission scenarios",
                "operationId": "listFamilyTravelMissionScenarios",
                "security": [],
                "responses": {
                    "200": {
                        "description": "The bilingual API index.",
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
    for scenario in dataset["scenarios"]:
        path = f"/scenarios/{scenario['id']}.json"
        paths[path] = {
            "get": {
                "tags": ["Family travel missions"],
                "summary": f"Get the {scenario['name']['en']} mission setting",
                "operationId": _operation_id(scenario["id"]),
                "security": [],
                "responses": {
                    "200": {
                        "description": "One bilingual, safety-bounded scenario.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "./scenario.schema.json"}
                            }
                        },
                    }
                },
            }
        }
    return {
        "openapi": "3.1.0",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": "Family Travel Missions Static API",
            "summary": "Privacy-first bilingual family travel observation prompts.",
            "description": (
                "Versioned, read-only static JSON endpoints generated from the CC BY 4.0 "
                "family travel mission taxonomy. No authentication or personal data."
            ),
            "version": API_VERSION,
            "license": {
                "name": "CC BY 4.0",
                "url": dataset["license"],
            },
        },
        "servers": [{"url": API_BASE, "description": "GitHub Pages static API"}],
        "externalDocs": {
            "description": "Dataset landing page and provenance",
            "url": DATASET_PAGE,
        },
        "tags": [
            {
                "name": "Family travel missions",
                "description": (
                    "Optional, adult-supervised observation prompts with no photo tasks "
                    "or driver interaction."
                ),
            }
        ],
        "paths": paths,
        "components": {
            "schemas": {
                "IndexResponse": {"$ref": "./index.schema.json"},
                "ScenarioResponse": {"$ref": "./scenario.schema.json"},
            }
        },
        "security": [],
        "x-static-read-only": True,
        "x-personal-data-requested": False,
    }


def validate_artifacts(
    dataset: dict,
    index: dict,
    scenarios: dict[str, dict],
    openapi: dict,
    index_schema_document: dict,
    scenario_schema_document: dict,
) -> None:
    expected_ids = [scenario["id"] for scenario in dataset["scenarios"]]
    if [item["scenarioId"] for item in index["scenarios"]] != expected_ids:
        raise ValueError("API index scenario order drifted from the canonical dataset")
    if set(scenarios) != set(expected_ids):
        raise ValueError("API scenario files do not match the canonical dataset")
    expected_paths = {"/index.json"} | {
        f"/scenarios/{scenario_id}.json" for scenario_id in expected_ids
    }
    if set(openapi["paths"]) != expected_paths:
        raise ValueError("OpenAPI paths do not match generated static endpoints")
    operation_ids = [
        operation["get"]["operationId"] for operation in openapi["paths"].values()
    ]
    if len(operation_ids) != len(set(operation_ids)):
        raise ValueError("OpenAPI operationId values must be unique")
    for scenario_id, payload in scenarios.items():
        scenario = payload["scenario"]
        if scenario["id"] != scenario_id or len(scenario["targets"]) != 7:
            raise ValueError(f"Invalid scenario payload: {scenario_id}")
        if (
            not scenario["stationaryRequired"]
            or scenario["photoTaskAllowed"]
            or scenario["driverInteractionAllowed"]
            or not scenario["adultSupervisionRequired"]
            or not scenario["skipAllowed"]
        ):
            raise ValueError(f"Safety invariant failed: {scenario_id}")
        refs = {item["id"] for item in payload["officialReferences"]}
        if refs != set(scenario["officialReferenceIds"]):
            raise ValueError(f"Official-reference mismatch: {scenario_id}")
    encoded = json.dumps(
        {
            "index": index,
            "scenarios": scenarios,
            "openapi": openapi,
            "indexSchema": index_schema_document,
            "scenarioSchema": scenario_schema_document,
        },
        ensure_ascii=False,
    )
    for forbidden in (
        "apps.apple.com",
        "SoftwareApplication",
        APP_NAME,
        APP_SHORT_NAME,
        APP_ID,
        f"id{APP_ID}",
    ):
        if forbidden in encoded:
            raise ValueError(f"Static API must remain app-independent: {forbidden}")


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _schema_graph(
    dataset: dict, locale: str, app_public: bool, page_modified: str
) -> dict:
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
            "dateModified": page_modified,
            "license": dataset["license"],
            "isBasedOn": DATASET_PAGE,
            "mainEntity": {
                "@type": "Dataset",
                "name": dataset["nameLocalized"][locale],
                "url": DATASET_PAGE,
                "distribution": {
                    "@type": "DataDownload",
                    "encodingFormat": "application/vnd.oai.openapi+json;version=3.1",
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
                "applicationCategory": "TravelApplication",
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_static_api_{locale.lower()}"),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def render_docs(
    dataset: dict,
    locale: str,
    app_public: bool = False,
    page_modified: str | None = None,
) -> str:
    copy = COPY[locale]
    modified = page_modified or dataset["dateModified"]
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
    badges = "".join(f"<span>{html.escape(item)}</span>" for item in copy["badges"])
    endpoint_rows = "".join(
        '<tr><td>{name}</td><td><a href="{url}"><code>{path}</code></a></td></tr>'.format(
            name=html.escape(scenario["name"][locale]),
            url=html.escape(scenario_url(scenario["id"]), quote=True),
            path=html.escape(f"/scenarios/{scenario['id']}.json"),
        )
        for scenario in dataset["scenarios"]
    )
    curl_example = f"curl -s {api_url('index.json')}"
    fetch_example = (
        f"const response = await fetch('{scenario_url('airport')}');\n"
        "const mission = await response.json();\n"
        "console.log(mission.scenario.targets);"
    )
    app_block = ""
    if app_public:
        app_block = (
            '<section class="app"><p class="kicker">{title}</p><p>{text}</p>'
            '<a href="{url}">{cta} →</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(APP_KEY, f"iag_static_api_{locale.lower()}"),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _schema_graph(dataset, locale, app_public, modified),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<link rel="alternate" hreflang="en" href="{api_url()}">
<link rel="alternate" hreflang="zh-Hant" href="{SITE}/zh-Hant/{API_PATH.as_posix()}/">
<link rel="alternate" hreflang="x-default" href="{api_url()}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#142036;--sub:#5b687d;--line:#dce4ef;--brand:#315fc4;--bg:#f5f8fc;--paper:#fff;--code:#111827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}
.wrap{{max-width:940px;margin:auto;padding:24px 20px 72px}}a{{color:var(--brand)}}.top{{display:flex;justify-content:space-between;gap:16px;font-size:14px}}.top a{{font-weight:750;text-decoration:none}}
.hero{{padding:52px 0 28px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}
h1{{font-size:clamp(32px,7vw,55px);line-height:1.08;letter-spacing:-.035em;margin:10px 0 16px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}
.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:780px}}p{{color:var(--sub)}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:700;white-space:nowrap}}
section{{margin-top:34px}}.panel,.app{{background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:23px;box-shadow:0 12px 30px rgba(27,44,79,.05)}}
.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:17px}}.links a{{border:1px solid var(--line);border-radius:13px;padding:14px;text-decoration:none;font-weight:760;background:#fbfcff}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:15px;overflow:hidden;display:block}}tbody{{display:table;width:100%}}td{{padding:11px 14px;border-bottom:1px solid var(--line)}}tr:last-child td{{border-bottom:0}}td:first-child{{width:32%;font-weight:700}}
code{{font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}}pre{{background:var(--code);color:#edf2ff;border-radius:14px;padding:17px;overflow:auto}}.examples{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.app a{{font-weight:800;text-decoration:none}}
footer{{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}}@media(max-width:680px){{.examples{{grid-template-columns:1fr}}td{{display:block;width:100%!important;padding-bottom:6px}}td+td{{padding-top:0;overflow-wrap:anywhere}}}}
</style>
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{DATASET_PAGE}">← {html.escape(copy['back'])}</a><a href="{html.escape(other, quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></header>
<section class="panel"><h2>{html.escape(copy['start'])}</h2><p>{html.escape(copy['start_text'])}</p><div class="links"><a href="{api_url('index.json')}">{html.escape(copy['index'])} →</a><a href="{api_url('openapi.json')}">{html.escape(copy['openapi'])} →</a><a href="{api_url('index.schema.json')}">{html.escape(copy['index_schema'])} →</a><a href="{api_url('scenario.schema.json')}">{html.escape(copy['scenario_schema'])} →</a><a href="{DATASET_PAGE}">{html.escape(copy['source'])} →</a></div></section>
<section><h2>{html.escape(copy['endpoints'])}</h2><table><tbody>{endpoint_rows}</tbody></table></section>
<section class="panel"><h2>{html.escape(copy['privacy'])}</h2><p>{html.escape(copy['privacy_text'])}</p></section>
<section><h2>{html.escape(copy['usage'])}</h2><div class="examples"><div><h3>{html.escape(copy['curl'])}</h3><pre><code>{html.escape(curl_example)}</code></pre></div><div><h3>{html.escape(copy['browser'])}</h3><pre><code>{html.escape(fetch_example)}</code></pre></div></div></section>
<section class="panel"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limits_text'])}</p></section>
<section class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p></section>
{app_block}
<footer>{html.escape(copy['description'])}</footer>
</main>
</body>
</html>
"""


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    dataset = load_dataset()
    canonical_schema = json.loads(
        (SOURCE_DIR / f"{SLUG}.schema.json").read_text(encoding="utf-8")
    )
    index = api_index(dataset)
    scenarios = {
        scenario["id"]: scenario_payload(dataset, scenario)
        for scenario in dataset["scenarios"]
    }
    openapi = openapi_document(dataset)
    index_schema_document = index_schema(dataset, canonical_schema)
    scenario_schema_document = scenario_schema(dataset, canonical_schema)
    validate_artifacts(
        dataset,
        index,
        scenarios,
        openapi,
        index_schema_document,
        scenario_schema_document,
    )
    output = pages / API_PATH
    scenario_dir = output / "scenarios"
    zh_output = pages / "zh-Hant" / API_PATH
    for directory in (output, scenario_dir, zh_output):
        directory.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(output / "index.json", _json(index))
    write_text_if_changed(output / "index.schema.json", _json(index_schema_document))
    write_text_if_changed(
        output / "scenario.schema.json", _json(scenario_schema_document)
    )
    write_text_if_changed(output / "openapi.json", _json(openapi))
    for scenario_id, payload in scenarios.items():
        write_text_if_changed(scenario_dir / f"{scenario_id}.json", _json(payload))
    public = is_app_public(pages) if app_public is None else app_public
    render_versioned_page(
        output / "index.html",
        lambda modified: render_docs(dataset, "en", public, modified),
        dataset["dateModified"],
        TODAY,
    )
    render_versioned_page(
        zh_output / "index.html",
        lambda modified: render_docs(dataset, "zh-Hant", public, modified),
        dataset["dateModified"],
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
        api_url("scenario.schema.json"),
        *[scenario_url(scenario_id) for scenario_id in scenarios],
    ]


if __name__ == "__main__":
    build()
