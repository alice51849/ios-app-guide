#!/usr/bin/env python3
"""Publish all 37 Zhuyin symbols as a Frictionless Data Package 2.0."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
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
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from zhuyin_croissant_dataset import (  # noqa: E402
    APP_ID,
    APP_KEY,
    APP_NAME,
    FIELD_NAMES,
    LICENSE,
    SITE,
    VERSION,
    records,
    render_csv,
    validate_records,
)
from zhuyin_skos_vocabulary import MOE_HANDBOOK, UNICODE_CHART  # noqa: E402


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
PACKAGE_SLUG = "zhuyin-bopomofo"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
DESCRIPTOR_FILENAME = "datapackage.json"
SCHEMA_FILENAME = "table-schema.json"
CSV_FILENAME = "symbols.csv"
DESCRIPTOR_URL = f"{PACKAGE_URL}{DESCRIPTOR_FILENAME}"
SCHEMA_URL = f"{PACKAGE_URL}{SCHEMA_FILENAME}"
CSV_URL = f"{PACKAGE_URL}{CSV_FILENAME}"
DATA_PACKAGE_PROFILE = (
    "https://datapackage.org/profiles/2.0/datapackage.json"
)
DATA_RESOURCE_PROFILE = (
    "https://datapackage.org/profiles/2.0/dataresource.json"
)
TABLE_SCHEMA_PROFILE = (
    "https://datapackage.org/profiles/2.0/tableschema.json"
)
DATA_PACKAGE_SPEC = "https://datapackage.org/standard/data-package/"
CROISSANT_PAGE = f"{SITE}/data/zhuyin-bopomofo-ml-dataset.html"
ZH_CROISSANT_PAGE = (
    f"{SITE}/zh-Hant/data/zhuyin-bopomofo-ml-dataset.html"
)
CROISSANT_METADATA = (
    f"{SITE}/data/zhuyin-bopomofo-ml-dataset.croissant.jsonld"
)
SKOS_PAGE = f"{SITE}/data/zhuyin-bopomofo-vocabulary.html"
ZH_SKOS_PAGE = f"{SITE}/zh-Hant/data/zhuyin-bopomofo-vocabulary.html"
SKOS_JSONLD = f"{SITE}/data/zhuyin-bopomofo-vocabulary.jsonld"
DATA_CATALOG = f"{SITE}/data/"
SITEMAP_URL = f"{SITE}/sitemap_datapackage.xml"

FIELD_COPY = {
    "order": ("Order", "Stable pedagogical order from 1 through 37."),
    "symbol_id": (
        "Symbol ID",
        "Stable ASCII identifier derived from the Unicode code point.",
    ),
    "concept_uri": (
        "Concept URI",
        "Stable URI for the corresponding SKOS concept.",
    ),
    "symbol": ("Symbol", "The single Bopomofo character."),
    "unicode": ("Unicode", "Unicode code point in U+XXXX notation."),
    "pinyin": ("Pinyin", "Hanyu Pinyin correspondence."),
    "ipa": ("IPA", "Compact IPA correspondence for the symbol."),
    "category": (
        "Category",
        "One of initial, medial or final.",
    ),
    "category_uri": (
        "Category URI",
        "Stable URI for the SKOS category concept.",
    ),
    "example_character": (
        "Example character",
        "Traditional Chinese example character.",
    ),
    "example_pinyin": (
        "Example Pinyin",
        "Tone-marked Pinyin for the example.",
    ),
    "example_meaning_en": (
        "Example meaning",
        "Short English gloss for the example.",
    ),
}

FIELD_DESCRIPTION_ZH = {
    "order": "1 至 37 的穩定教學順序。",
    "symbol_id": "由 Unicode 碼位產生的穩定 ASCII 識別碼。",
    "concept_uri": "對應 SKOS 概念的穩定 URI。",
    "symbol": "單一注音符號字元。",
    "unicode": "U+XXXX 格式的 Unicode 碼位。",
    "pinyin": "對應漢語拼音。",
    "ipa": "符號的精簡 IPA 對照。",
    "category": "聲母、介音或韻母分類。",
    "category_uri": "SKOS 分類概念的穩定 URI。",
    "example_character": "繁體中文例字。",
    "example_pinyin": "例字的聲調拼音。",
    "example_meaning_en": "例字的精簡英文釋義。",
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo Frictionless Data Package 2.0",
        "description": (
            "A portable, validated Data Package 2.0 containing all 37 Zhuyin "
            "symbols, a strict Table Schema and UTF-8 CSV."
        ),
        "eyebrow": "Data Package 2.0 · Table Schema 2.0 · CC BY 4.0",
        "lead": (
            "Download one self-contained directory for ETL, notebooks, data "
            "catalogs and reproducible pipelines. No account or API key."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "badges": (
            "37 validated rows",
            "12 typed fields",
            "Portable relative paths",
            "SHA-256 verified",
        ),
        "downloads": "Package files",
        "download_text": (
            "The descriptor resolves its CSV and Table Schema by relative "
            "path, so the directory works online or after download."
        ),
        "descriptor": "Data Package descriptor",
        "schema": "Table Schema",
        "csv": "UTF-8 CSV",
        "validate": "Validate and load",
        "validate_text": (
            "Frictionless validates the descriptor, schema, primary key, "
            "types, constraints and every CSV row."
        ),
        "fields": "Portable field contract",
        "field": "Field",
        "type": "Type",
        "meaning": "Meaning",
        "uses": "Suitable uses",
        "use_items": (
            "ETL and data-quality checks",
            "Notebook and dataframe imports",
            "Catalog ingestion and reproducible builds",
            "Reference tables for language tooling",
        ),
        "limits": "Limitations",
        "limit_items": (
            "Not a pronunciation or speech dataset",
            "Not a text conversion API",
            "Not a learner assessment or curriculum",
            "Examples are compact references, not complete phonology rules",
        ),
        "preview": "Data preview",
        "order": "Order",
        "symbol": "Symbol",
        "category": "Category",
        "pinyin": "Pinyin",
        "ipa": "IPA",
        "example": "Example",
        "sources": "Standards and linked resources",
        "source_text": (
            "The package reuses the exact Croissant CSV bytes and links to "
            "the SKOS vocabulary rather than maintaining another dataset."
        ),
        "croissant": "Croissant data card",
        "skos": "SKOS vocabulary",
        "standard": "Data Package 2.0 standard",
        "license": "License and package independence",
        "license_text": (
            "The package is CC BY 4.0. Its descriptor, schema and CSV contain "
            "no App Store URL, app identifier or software promotion."
        ),
        "app_title": "Optional practice layer",
        "app_text": (
            "Lumi Bopomofo adds short, on-device activities. The open package "
            "remains free, portable and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Independent, portable reference data for education and software "
            "development."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音符號 Frictionless Data Package 2.0",
        "description": (
            "可攜且已驗證的 Data Package 2.0，完整包含 37 個注音符號、"
            "嚴格 Table Schema 與 UTF-8 CSV。"
        ),
        "eyebrow": "Data Package 2.0 · Table Schema 2.0 · CC BY 4.0",
        "lead": (
            "一個自含目錄即可用於 ETL、notebook、資料目錄與可重現流程；"
            "不需帳號或 API 金鑰。"
        ),
        "language": "English",
        "back": "開放資料",
        "badges": (
            "37 筆已驗證資料",
            "12 個型別欄位",
            "可攜相對路徑",
            "SHA-256 驗證",
        ),
        "downloads": "套件檔案",
        "download_text": (
            "descriptor 以相對路徑解析 CSV 與 Table Schema，因此線上或"
            "下載整個目錄後都能使用。"
        ),
        "descriptor": "Data Package descriptor",
        "schema": "Table Schema",
        "csv": "UTF-8 CSV",
        "validate": "驗證與載入",
        "validate_text": (
            "Frictionless 會驗證 descriptor、schema、主鍵、型別、約束與"
            "每一筆 CSV 資料。"
        ),
        "fields": "可攜欄位契約",
        "field": "欄位",
        "type": "型別",
        "meaning": "意義",
        "uses": "適合用途",
        "use_items": (
            "ETL 與資料品質檢查",
            "Notebook 與 dataframe 匯入",
            "資料目錄匯入與可重現建置",
            "語言工具的參考表",
        ),
        "limits": "限制",
        "limit_items": (
            "不是發音或語音資料集",
            "不是文字轉換 API",
            "不是學習者評量或課程",
            "例字是精簡參考，不代表完整語音規則",
        ),
        "preview": "資料預覽",
        "order": "順序",
        "symbol": "符號",
        "category": "分類",
        "pinyin": "拼音",
        "ipa": "IPA",
        "example": "例字",
        "sources": "標準與連結資源",
        "source_text": (
            "套件直接重用完全相同的 Croissant CSV bytes，並連結 SKOS "
            "詞彙，不另維護一份資料。"
        ),
        "croissant": "Croissant 資料卡",
        "skos": "SKOS 詞彙",
        "standard": "Data Package 2.0 標準",
        "license": "授權與套件獨立性",
        "license_text": (
            "套件採 CC BY 4.0；descriptor、schema 與 CSV 不含 App Store "
            "網址、App 識別碼或軟體宣傳。"
        ),
        "app_title": "選用練習層",
        "app_text": (
            "Lumi 注音星球提供裝置端短活動；開放套件仍維持免費、可攜且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": "供教育與軟體開發使用的獨立可攜參考資料。",
    },
}


def table_schema(rows: list[dict]) -> dict:
    ids = [row["symbol_id"] for row in rows]
    unicode_values = [row["unicode"] for row in rows]
    category_uris = sorted({row["category_uri"] for row in rows})
    fields = []
    for name in FIELD_NAMES:
        title, description = FIELD_COPY[name]
        field = {
            "name": name,
            "title": title,
            "description": description,
            "type": "integer" if name == "order" else "string",
            "constraints": {"required": True},
            "example": str(rows[0][name]),
        }
        constraints = field["constraints"]
        if name == "order":
            constraints.update(
                {"unique": True, "minimum": 1, "maximum": 37}
            )
        elif name == "symbol_id":
            constraints.update({"unique": True, "enum": ids})
        elif name == "concept_uri":
            field["format"] = "uri"
            constraints["unique"] = True
        elif name == "symbol":
            constraints.update(
                {"unique": True, "minLength": 1, "maxLength": 1}
            )
        elif name == "unicode":
            constraints.update({"unique": True, "enum": unicode_values})
        elif name == "category":
            constraints["enum"] = ["initial", "medial", "final"]
        elif name == "category_uri":
            field["format"] = "uri"
            constraints["enum"] = category_uris
        else:
            constraints["minLength"] = 1
        fields.append(field)
    return {
        "$schema": TABLE_SCHEMA_PROFILE,
        "missingValues": [],
        "primaryKey": ["symbol_id"],
        "fields": fields,
    }


def data_package(
    csv_bytes: bytes,
    csv_sha256: str,
) -> dict:
    return {
        "$schema": DATA_PACKAGE_PROFILE,
        "name": "zhuyin-bopomofo-symbols",
        "id": DESCRIPTOR_URL,
        "title": "Complete 37-symbol Zhuyin (Bopomofo) inventory",
        "description": (
            "A portable Data Package 2.0 with all 21 initials, 3 medials and "
            "13 finals, including Unicode, Pinyin, IPA and examples."
        ),
        "homepage": PACKAGE_URL,
        "version": VERSION,
        "created": f"{INITIAL_DATE}T00:00:00Z",
        "keywords": [
            "zhuyin",
            "bopomofo",
            "mandarin",
            "taiwan",
            "unicode",
            "pinyin",
            "ipa",
            "phonetics",
        ],
        "licenses": [
            {
                "name": "CC-BY-4.0",
                "path": LICENSE,
                "title": "Creative Commons Attribution 4.0 International",
            }
        ],
        "contributors": [
            {
                "title": "Lumi Apps",
                "path": f"{SITE}/",
                "roles": ["creator", "dataCurator"],
                "organization": "Lumi Apps",
            }
        ],
        "sources": [
            {
                "title": "Bopomofo Croissant 1.1 dataset",
                "path": CROISSANT_METADATA,
                "version": VERSION,
            },
            {
                "title": "Ministry of Education Mandarin Phonetic Symbols Handbook",
                "path": MOE_HANDBOOK,
            },
            {
                "title": "Unicode Bopomofo code chart",
                "path": UNICODE_CHART,
            },
        ],
        "resources": [
            {
                "$schema": DATA_RESOURCE_PROFILE,
                "name": "symbols",
                "path": CSV_FILENAME,
                "type": "table",
                "title": "All 37 Zhuyin symbols",
                "description": (
                    "Canonical UTF-8 table with 37 rows and 12 typed fields."
                ),
                "format": "csv",
                "mediatype": "text/csv",
                "encoding": "utf-8",
                "bytes": len(csv_bytes),
                "hash": f"sha256:{csv_sha256}",
                "schema": SCHEMA_FILENAME,
            }
        ],
    }


def make_artifacts(rows: list[dict]) -> dict[str, dict]:
    csv_content = render_csv(rows)
    csv_bytes = csv_content.encode("utf-8")
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
    schema = table_schema(rows)
    descriptor = data_package(csv_bytes, csv_sha256)
    return {
        "descriptor": {
            "filename": DESCRIPTOR_FILENAME,
            "content": json.dumps(
                descriptor, ensure_ascii=False, indent=2
            )
            + "\n",
            "url": DESCRIPTOR_URL,
            "media_type": "application/json",
            "label": "Data Package 2.0",
        },
        "schema": {
            "filename": SCHEMA_FILENAME,
            "content": json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            "url": SCHEMA_URL,
            "media_type": "application/json",
            "label": "Table Schema 2.0",
        },
        "csv": {
            "filename": CSV_FILENAME,
            "content": csv_content,
            "url": CSV_URL,
            "media_type": "text/csv",
            "label": "UTF-8 CSV",
            "sha256": csv_sha256,
        },
    }


def validate_artifacts(rows: list[dict], artifacts: dict[str, dict]) -> None:
    validate_records(rows)
    descriptor = json.loads(artifacts["descriptor"]["content"])
    schema = json.loads(artifacts["schema"]["content"])
    if descriptor.get("$schema") != DATA_PACKAGE_PROFILE:
        raise ValueError("Data Package must declare the 2.0 profile")
    if schema.get("$schema") != TABLE_SCHEMA_PROFILE:
        raise ValueError("Table Schema must declare the 2.0 profile")
    if [field["name"] for field in schema["fields"]] != list(FIELD_NAMES):
        raise ValueError("Table Schema fields drifted from the source table")
    if schema.get("primaryKey") != ["symbol_id"]:
        raise ValueError("symbol_id must be the package primary key")
    resource = descriptor["resources"][0]
    if (
        resource["path"] != CSV_FILENAME
        or resource["schema"] != SCHEMA_FILENAME
        or resource["bytes"]
        != len(artifacts["csv"]["content"].encode("utf-8"))
        or resource["hash"] != f"sha256:{artifacts['csv']['sha256']}"
    ):
        raise ValueError("Data Package resource metadata does not match CSV")
    encoded = "\n".join(item["content"] for item in artifacts.values())
    for forbidden in (
        "apps.apple.com",
        APP_ID,
        APP_NAME,
        "SoftwareApplication",
    ):
        if forbidden in encoded:
            raise ValueError(f"App promotion leaked into package: {forbidden}")


def _prior_artifact_modified(pages: Path) -> str:
    sitemap = pages / "sitemap_datapackage.xml"
    if not sitemap.exists():
        return INITIAL_DATE
    pattern = (
        r"<loc>"
        + re.escape(DESCRIPTOR_URL)
        + r"</loc><lastmod>(\d{4}-\d{2}-\d{2})</lastmod>"
    )
    match = re.search(pattern, sitemap.read_text(encoding="utf-8"))
    return match.group(1) if match else INITIAL_DATE


def write_artifacts(
    output: Path,
    artifacts: dict[str, dict],
    pages: Path = PAGES,
) -> str:
    output.mkdir(parents=True, exist_ok=True)
    prior = _prior_artifact_modified(pages)
    changed = False
    for artifact in artifacts.values():
        changed = (
            write_text_if_changed(
                output / artifact["filename"], artifact["content"]
            )
            or changed
        )
    return TODAY if changed else prior


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def page_url(locale: str) -> str:
    return PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL


def _schema_graph(
    locale: str,
    app_public: bool,
    modified: str,
    artifacts: dict[str, dict],
) -> dict:
    graph = [
        {
            "@type": "Dataset",
            "@id": f"{PACKAGE_URL}#dataset",
            "name": COPY[locale]["title"],
            "description": COPY[locale]["description"],
            "url": page_url(locale),
            "inLanguage": locale,
            "dateModified": modified,
            "version": VERSION,
            "license": LICENSE,
            "isBasedOn": [CROISSANT_METADATA, SKOS_JSONLD],
            "conformsTo": DATA_PACKAGE_SPEC,
            "distribution": [
                {
                    "@type": "DataDownload",
                    "name": artifact["label"],
                    "encodingFormat": artifact["media_type"],
                    "contentUrl": artifact["url"],
                }
                for artifact in artifacts.values()
            ],
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
                    APP_KEY, f"iag_datapackage_{locale.lower()}"
                ),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(
    locale: str,
    artifacts: dict[str, dict],
) -> str:
    copy = COPY[locale]
    labels = {
        "descriptor": copy["descriptor"],
        "schema": copy["schema"],
        "csv": copy["csv"],
    }
    return "".join(
        '<a class="download" href="{url}"><strong>{label}</strong>'
        "<span>{filename}</span></a>".format(
            url=html.escape(artifact["url"], quote=True),
            label=html.escape(labels[key]),
            filename=html.escape(artifact["filename"]),
        )
        for key, artifact in artifacts.items()
    )


def _field_rows(locale: str, schema: dict) -> str:
    type_labels = {
        "integer": "integer" if locale == "en" else "整數",
        "string": "string" if locale == "en" else "字串",
    }
    return "".join(
        "<tr><td><code>{name}</code></td><td>{type}</td><td>{text}</td></tr>".format(
            name=html.escape(field["name"]),
            type=html.escape(type_labels[field["type"]]),
            text=html.escape(
                field["description"]
                if locale == "en"
                else FIELD_DESCRIPTION_ZH[field["name"]]
            ),
        )
        for field in schema["fields"]
    )


def _preview_rows(rows: list[dict], locale: str) -> str:
    category_labels = {
        "initial": "聲母",
        "medial": "介音",
        "final": "韻母",
    }
    return "".join(
        "<tr><td>{order}</td><td class=\"symbol\">{symbol}</td>"
        "<td>{category}</td><td>{pinyin}</td><td>{ipa}</td>"
        "<td>{example} ({example_pinyin})</td></tr>".format(
            order=row["order"],
            symbol=html.escape(row["symbol"]),
            category=html.escape(
                row["category"]
                if locale == "en"
                else category_labels[row["category"]]
            ),
            pinyin=html.escape(row["pinyin"]),
            ipa=html.escape(row["ipa"]),
            example=html.escape(row["example_character"]),
            example_pinyin=html.escape(row["example_pinyin"]),
        )
        for row in rows
    )


def render_page(
    locale: str,
    rows: list[dict],
    artifacts: dict[str, dict],
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    schema_document = json.loads(artifacts["schema"]["content"])
    other_locale = "zh-Hant" if locale == "en" else "en"
    croissant_page = (
        CROISSANT_PAGE if locale == "en" else ZH_CROISSANT_PAGE
    )
    skos_page = SKOS_PAGE if locale == "en" else ZH_SKOS_PAGE
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    uses = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["use_items"]
    )
    limits = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["limit_items"]
    )
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel app"><h2>{title}</h2><p>{text}</p>'
            '<a class="button" href="{url}" rel="nofollow noopener">'
            "{cta}</a></section>"
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(
                    APP_KEY, f"iag_datapackage_{locale.lower()}"
                ),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _schema_graph(locale, app_public, modified, artifacts),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    cli_example = (
        "pip install frictionless==5.19.0\n"
        f"frictionless validate {DESCRIPTOR_URL}"
    )
    python_example = (
        "from frictionless import Package\n\n"
        f'package = Package("{DESCRIPTOR_URL}")\n'
        'with package.get_resource("symbols") as resource:\n'
        "    rows = resource.read_rows()"
    )
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
<link rel="canonical" href="{html.escape(page_url(locale), quote=True)}">
<link rel="alternate" hreflang="en" href="{PACKAGE_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_PACKAGE_URL}">
<link rel="alternate" hreflang="x-default" href="{PACKAGE_URL}">
<link rel="describedby" type="application/json" href="{DESCRIPTOR_URL}">
<link rel="alternate" type="text/csv" href="{CSV_URL}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#172039;--sub:#59657a;--line:#dfe5ef;--paper:#fff;--wash:#f4f7fc;--brand:#3159c9;--soft:#edf3ff;--code:#101827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1060px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.92);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:750;text-decoration:none;white-space:nowrap}}.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:970px}}.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:830px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}}
main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,55,98,.06)}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub);margin:8px 0}}.downloads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}ol,ul{{padding-left:24px}}li{{margin:8px 0}}pre{{background:var(--code);color:#dbe8ff;border-radius:16px;padding:18px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.symbol{{font-size:25px;font-weight:850}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:700;white-space:nowrap}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:800;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#edf3ff)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:760px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{DATA_CATALOG}">{html.escape(copy['back'])}</a><a href="{html.escape(page_url(other_locale), quote=True)}">{html.escape(copy['language'])}</a></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, artifacts)}</div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><pre>{html.escape(cli_example)}</pre></article><article class="panel"><h2>Python</h2><pre>{html.escape(python_example)}</pre></article></section>
<section class="wrap panel"><h2>{html.escape(copy['fields'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['field'])}</th><th>{html.escape(copy['type'])}</th><th>{html.escape(copy['meaning'])}</th></tr></thead><tbody>{_field_rows(locale, schema_document)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['uses'])}</h2><ul>{uses}</ul></article><article class="panel"><h2>{html.escape(copy['limits'])}</h2><ul>{limits}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['preview'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['order'])}</th><th>{html.escape(copy['symbol'])}</th><th>{html.escape(copy['category'])}</th><th>{html.escape(copy['pinyin'])}</th><th>{html.escape(copy['ipa'])}</th><th>{html.escape(copy['example'])}</th></tr></thead><tbody>{_preview_rows(rows, locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['source_text'])}</p><div class="sources"><a href="{croissant_page}">{html.escape(copy['croissant'])}</a><a href="{skos_page}">{html.escape(copy['skos'])}</a><a href="{DATA_PACKAGE_SPEC}" rel="noopener">{html.escape(copy['standard'])}</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a></article></section>
<div class="wrap">{app_section}</div>
</main>
<footer class="footer">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def update_data_index(
    pages: Path,
    artifacts: dict[str, dict],
) -> bool:
    index = pages / "data" / "index.html"
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    card = (
        f'<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo Frictionless Data Package 2.0</h2>"
        "<p>All 37 Zhuyin symbols in a portable directory with a strict "
        "Table Schema, primary key, constraints and SHA-256.</p>"
        '<span class="tag">Data engineering · EN + zh-Hant · CC BY 4.0</span></a>'
    )
    existing = re.compile(
        r'<a class="item" href="' + re.escape(PACKAGE_URL) + r'">.*?</a>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    anchor = re.search(
        r'<a class="item" href="'
        + re.escape(CROISSANT_PAGE)
        + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if not anchor:
        raise RuntimeError("data/index.html is missing the Croissant card")
    updated = updated[: anchor.end()] + card + updated[anchor.end() :]
    schema_pattern = re.compile(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        re.DOTALL,
    )
    schema_match = schema_pattern.search(updated)
    if not schema_match:
        raise RuntimeError("data/index.html is missing DataCatalog JSON-LD")
    catalog = json.loads(schema_match.group(2))
    datasets = [
        dataset
        for dataset in catalog.get("dataset", [])
        if dataset.get("url") != PACKAGE_URL
    ]
    entry = {
        "@type": "Dataset",
        "name": COPY["en"]["title"],
        "description": COPY["en"]["description"],
        "url": PACKAGE_URL,
        "license": LICENSE,
        "conformsTo": DATA_PACKAGE_SPEC,
        "distribution": [
            {
                "@type": "DataDownload",
                "name": artifact["label"],
                "encodingFormat": artifact["media_type"],
                "contentUrl": artifact["url"],
            }
            for artifact in artifacts.values()
        ],
    }
    position = next(
        (
            offset + 1
            for offset, dataset in enumerate(datasets)
            if dataset.get("url") == CROISSANT_PAGE
        ),
        0,
    )
    datasets.insert(position, entry)
    catalog["dataset"] = datasets
    updated = (
        updated[: schema_match.start()]
        + schema_match.group(1)
        + json.dumps(catalog, ensure_ascii=False)
        + schema_match.group(3)
        + updated[schema_match.end() :]
    )
    return write_text_if_changed(index, updated)


def render_sitemap(
    page_modified: dict[str, str],
    artifact_modified: str,
    artifacts: dict[str, dict],
) -> str:
    entries = [
        (PACKAGE_URL, page_modified["en"]),
        (ZH_PACKAGE_URL, page_modified["zh-Hant"]),
        *[
            (artifact["url"], artifact_modified)
            for artifact in artifacts.values()
        ],
    ]
    rows = "\n".join(
        f"  <url><loc>{url}</loc><lastmod>{modified}</lastmod></url>"
        for url, modified in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n</urlset>\n"
    )


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    rows = records()
    artifacts = make_artifacts(rows)
    validate_artifacts(rows, artifacts)
    output = pages / PACKAGE_PATH
    artifact_modified = write_artifacts(output, artifacts, pages)
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", output / "index.html"),
        ("zh-Hant", pages / "zh-Hant" / PACKAGE_PATH / "index.html"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_page(
                locale,
                rows,
                artifacts,
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    update_data_index(pages, artifacts)
    write_text_if_changed(
        pages / "sitemap_datapackage.xml",
        render_sitemap(page_modified, artifact_modified, artifacts),
    )
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        *[artifact["url"] for artifact in artifacts.values()],
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin Frictionless resource -> {output}")


if __name__ == "__main__":
    main()
