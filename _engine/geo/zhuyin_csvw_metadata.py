#!/usr/bin/env python3
"""Publish standards-based CSVW metadata for the canonical Bopomofo table."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import sys
import zipfile
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
PACKAGE_SLUG = "zhuyin-bopomofo-csvw"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
CSV_FILENAME = "zhuyin-bopomofo-ml-dataset.csv"
CSVW_FILENAME = f"{CSV_FILENAME}-metadata.json"
BUNDLE_FILENAME = "bopomofo-37-symbols-csvw-bundle.zip"
CHECKSUM_FILENAME = "checksums-sha256.txt"
MANIFEST_FILENAME = "metadata.jsonld"
README_FILENAME = "README.md"
LICENSE_FILENAME = "LICENSE.txt"
CSV_URL = f"{SITE}/data/{CSV_FILENAME}"
CSVW_URL = f"{SITE}/data/{CSVW_FILENAME}"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
MANIFEST_URL = f"{PACKAGE_URL}{MANIFEST_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_csvw.xml"
DATA_CATALOG = f"{SITE}/data/"
CROISSANT_PAGE = f"{SITE}/data/zhuyin-bopomofo-ml-dataset.html"
ZH_CROISSANT_PAGE = f"{SITE}/zh-Hant/data/zhuyin-bopomofo-ml-dataset.html"
SKOS_PAGE = f"{SITE}/data/zhuyin-bopomofo-vocabulary.html"
ZH_SKOS_PAGE = f"{SITE}/zh-Hant/data/zhuyin-bopomofo-vocabulary.html"
SOURCE_DATASET = f"{SITE}/data/zhuyin-bopomofo.json"
ORG_URI = f"{SITE}/#organization"
CSVW_CONTEXT = "http://www.w3.org/ns/csvw"
CSVW_NAMESPACE = "http://www.w3.org/ns/csvw#"
CSVW_MEDIA_TYPE = "application/csvm+json"
CSV_MEDIA_TYPE = "text/csv"
CSVW_MODEL = (
    "https://www.w3.org/TR/2015/REC-tabular-data-model-20151217/"
)
CSVW_METADATA = (
    "https://www.w3.org/TR/2015/REC-tabular-metadata-20151217/"
)
CSVW_RDF = "https://www.w3.org/TR/2015/REC-csv2rdf-20151217/"
CSVW_RECOMMENDATIONS = (CSVW_MODEL, CSVW_METADATA, CSVW_RDF)
REFERENCE_DIR = HERE / "reference_datasets" / "csvw"
REFERENCE_SOURCES = REFERENCE_DIR / "sources.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


FIELD_COPY = {
    "order": {
        "title_en": "Order",
        "title_zh": "順序",
        "description_en": "Stable educational display order from 1 through 37.",
        "description_zh": "1 至 37 的穩定教學順序。",
        "datatype": {"base": "integer", "minimum": 1, "maximum": 37},
        "propertyUrl": "http://schema.org/position",
    },
    "symbol_id": {
        "title_en": "Symbol ID",
        "title_zh": "符號 ID",
        "description_en": (
            "ASCII identifier derived from the uppercase Unicode code point."
        ),
        "description_zh": "由大寫 Unicode 碼位產生的 ASCII 識別碼。",
        "datatype": {
            "base": "string",
            "format": r"^u31(?:0[5-9A-F]|1[0-9A-F]|2[0-9])$",
        },
        "propertyUrl": "http://purl.org/dc/terms/identifier",
    },
    "concept_uri": {
        "title_en": "Concept IRI",
        "title_zh": "概念 IRI",
        "description_en": "Stable IRI for the corresponding SKOS concept.",
        "description_zh": "對應 SKOS 概念的穩定 IRI。",
        "datatype": "anyURI",
        "suppressOutput": True,
    },
    "symbol": {
        "title_en": "Bopomofo symbol",
        "title_zh": "注音符號",
        "description_en": "One Bopomofo character.",
        "description_zh": "單一注音符號字元。",
        "datatype": {"base": "string", "length": 1},
        "lang": "zh-Bopo",
        "propertyUrl": "http://www.w3.org/2004/02/skos/core#prefLabel",
    },
    "unicode": {
        "title_en": "Unicode notation",
        "title_zh": "Unicode 表示",
        "description_en": "Unicode notation in U+XXXX form.",
        "description_zh": "U+XXXX 格式的 Unicode 碼位。",
        "datatype": {
            "base": "string",
            "format": r"^U\+31(?:0[5-9A-F]|1[0-9A-F]|2[0-9])$",
        },
        "propertyUrl": "http://www.w3.org/2004/02/skos/core#notation",
    },
    "pinyin": {
        "title_en": "Hanyu Pinyin",
        "title_zh": "漢語拼音",
        "description_en": "Hanyu Pinyin correspondence.",
        "description_zh": "對應漢語拼音。",
        "datatype": "string",
        "lang": "zh-Latn-pinyin",
        "propertyUrl": f"{SKOS_PAGE}#pinyin",
    },
    "ipa": {
        "title_en": "IPA",
        "title_zh": "國際音標",
        "description_en": "Broad IPA transcription without brackets.",
        "description_zh": "不含括號的概略 IPA 轉寫。",
        "datatype": "string",
        "propertyUrl": f"{SKOS_PAGE}#ipa",
    },
    "category": {
        "title_en": "Category",
        "title_zh": "分類",
        "description_en": "One of initial, medial or final.",
        "description_zh": "聲母、介音或韻母。",
        "datatype": {
            "base": "string",
            "format": r"^(initial|medial|final)$",
        },
        "propertyUrl": "http://schema.org/category",
    },
    "category_uri": {
        "title_en": "Category IRI",
        "title_zh": "分類 IRI",
        "description_en": "IRI for the broader SKOS category concept.",
        "description_zh": "較廣義 SKOS 分類概念的 IRI。",
        "datatype": "anyURI",
        "propertyUrl": "http://www.w3.org/2004/02/skos/core#broader",
        "valueUrl": "{category_uri}",
    },
    "example_character": {
        "title_en": "Example character",
        "title_zh": "例字",
        "description_en": "Traditional Chinese example character.",
        "description_zh": "繁體中文例字。",
        "datatype": {"base": "string", "length": 1},
        "lang": "zh-Hant",
        "propertyUrl": f"{SKOS_PAGE}#exampleCharacter",
    },
    "example_pinyin": {
        "title_en": "Example Pinyin",
        "title_zh": "例字拼音",
        "description_en": "Tone-marked Hanyu Pinyin for the example.",
        "description_zh": "例字的聲調漢語拼音。",
        "datatype": "string",
        "lang": "zh-Latn-pinyin",
        "propertyUrl": f"{SKOS_PAGE}#examplePinyin",
    },
    "example_meaning_en": {
        "title_en": "English meaning",
        "title_zh": "英文詞義",
        "description_en": "Short English meaning for the example.",
        "description_zh": "例字的精簡英文釋義。",
        "datatype": "string",
        "lang": "en",
        "propertyUrl": f"{SKOS_PAGE}#exampleMeaning",
    },
}


COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo CSVW Metadata for All 37 Zhuyin Symbols",
        "description": (
            "Download validated W3C CSVW metadata and a UTF-8 table covering "
            "all 37 Bopomofo symbols, with typed columns, a primary key, URI "
            "templates and deterministic checksums."
        ),
        "eyebrow": "W3C CSVW · 37 rows · 12 typed columns · CC BY 4.0",
        "lead": (
            "A machine-discoverable table contract for data catalogs, ETL "
            "pipelines, RDF tooling and reproducible language-data workflows."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "badges": (
            "Default metadata discovery",
            "Unique primary key",
            "Offline vocabulary validation",
            "Deterministic ZIP",
        ),
        "downloads": "Download and discover",
        "download_text": (
            "The metadata uses the standard <CSV URL>-metadata.json name and "
            "sits beside the CSV, so CSVW-aware tools can discover it directly."
        ),
        "csv": "Canonical UTF-8 CSV",
        "csvw": "CSVW metadata",
        "bundle": "Offline bundle",
        "checksums": "SHA-256 checksums",
        "manifest": "Dataset manifest",
        "validate": "Validate with a CSVW processor",
        "validate_text": (
            "The pinned command checks metadata syntax, column names, datatypes, "
            "required values, URI templates, the primary key and every row."
        ),
        "contract": "Machine-readable table contract",
        "field": "Column",
        "type": "Datatype",
        "meaning": "Meaning",
        "mapping": "RDF property",
        "uses": "Suitable uses",
        "use_items": (
            "CSV ingestion and schema-aware ETL",
            "Data-catalog metadata discovery",
            "Deterministic tabular quality checks",
            "CSV-to-RDF workflows using the declared mappings",
        ),
        "limits": "Scope and limitations",
        "limit_items": (
            "A compact symbol reference, not a pronunciation corpus",
            "No audio, learner records or behavioral data",
            "No claim of W3C certification or external catalog ingestion",
            "Examples do not replace a complete Mandarin phonology guide",
        ),
        "preview": "Preview all 37 rows",
        "order": "Order",
        "symbol": "Symbol",
        "category": "Category",
        "pinyin": "Pinyin",
        "ipa": "IPA",
        "example": "Example",
        "standards": "Standards and provenance",
        "standards_text": (
            "The metadata targets the immutable 17 December 2015 W3C "
            "Recommendations. Offline context and vocabulary snapshots are "
            "hash-pinned for deterministic validation."
        ),
        "croissant": "Croissant 1.1 profile",
        "skos": "SKOS vocabulary",
        "w3c": "CSVW Recommendation",
        "license": "License",
        "license_text": (
            "The table is reusable under CC BY 4.0 with attribution to Lumi "
            "Apps. W3C snapshots retain their own W3C terms."
        ),
        "app_title": "Optional practice companion",
        "app_text": (
            "Lumi Bopomofo offers a separate on-device way to practise the "
            "symbols. The CSVW table remains open, independent and usable "
            "without the app."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Independent open reference data for Bopomofo education and "
            "language tooling."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "完整 37 注音符號 CSVW 中繼資料",
        "description": (
            "下載涵蓋完整 37 注音符號的已驗證 W3C CSVW 中繼資料與 UTF-8 "
            "表格，包含型別欄位、主鍵、URI 模板及確定性校驗碼。"
        ),
        "eyebrow": "W3C CSVW · 37 列 · 12 個型別欄位 · CC BY 4.0",
        "lead": (
            "供資料目錄、ETL 流程、RDF 工具與可重現語言資料工作流程使用的"
            "機器可探索表格契約。"
        ),
        "language": "English",
        "back": "開放資料",
        "badges": (
            "標準中繼資料探索",
            "唯一主鍵",
            "離線詞彙驗證",
            "確定性 ZIP",
        ),
        "downloads": "下載與探索",
        "download_text": (
            "中繼資料採用標準的 <CSV URL>-metadata.json 命名並與 CSV "
            "相鄰，CSVW 工具可直接探索。"
        ),
        "csv": "標準 UTF-8 CSV",
        "csvw": "CSVW 中繼資料",
        "bundle": "離線套件",
        "checksums": "SHA-256 校驗碼",
        "manifest": "資料集清單",
        "validate": "以 CSVW 處理器驗證",
        "validate_text": (
            "固定版本指令會檢查中繼資料語法、欄名、資料型別、必填值、URI "
            "模板、主鍵與每一列。"
        ),
        "contract": "機器可讀表格契約",
        "field": "欄位",
        "type": "資料型別",
        "meaning": "意義",
        "mapping": "RDF 屬性",
        "uses": "適合用途",
        "use_items": (
            "CSV 匯入與 schema-aware ETL",
            "資料目錄中繼資料探索",
            "確定性表格品質檢查",
            "使用宣告 mapping 的 CSV-to-RDF 工作流程",
        ),
        "limits": "範圍與限制",
        "limit_items": (
            "這是精簡符號參考資料，不是發音語料庫",
            "不含音訊、學習者紀錄或行為資料",
            "不宣稱獲 W3C 認證或已被外部目錄收錄",
            "例字不能取代完整華語音韻指南",
        ),
        "preview": "預覽全部 37 列",
        "order": "順序",
        "symbol": "符號",
        "category": "分類",
        "pinyin": "拼音",
        "ipa": "IPA",
        "example": "例字",
        "standards": "標準與資料來源",
        "standards_text": (
            "中繼資料以 2015 年 12 月 17 日的固定版 W3C Recommendation "
            "為準，並保存 hash-pinned 離線 context 與詞彙快照供確定性驗證。"
        ),
        "croissant": "Croissant 1.1 profile",
        "skos": "SKOS 詞彙",
        "w3c": "CSVW Recommendation",
        "license": "授權",
        "license_text": (
            "表格依 CC BY 4.0 授權，標示 Lumi Apps 後可再利用；W3C "
            "快照維持其各自的 W3C 授權條款。"
        ),
        "app_title": "選用練習工具",
        "app_text": (
            "Lumi 注音星球提供另一種在裝置上練習符號的方式；CSVW 表格仍為"
            "開放、獨立且不需 App 即可使用。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "提供注音教育與語言工具使用的獨立開放參考資料。",
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def csvw_columns() -> list[dict]:
    columns = []
    for name in FIELD_NAMES:
        spec = FIELD_COPY[name]
        column = {
            "name": name,
            "titles": {
                "en": spec["title_en"],
                "zh-Hant": spec["title_zh"],
            },
            "dc:description": spec["description_en"],
            "datatype": spec["datatype"],
            "required": True,
        }
        for key in ("lang", "propertyUrl", "valueUrl", "suppressOutput"):
            if key in spec:
                column[key] = spec[key]
        columns.append(column)
    return columns


def csvw_document(modified: str) -> dict:
    return {
        "@context": [CSVW_CONTEXT, {"@language": "en"}],
        "@id": CSVW_URL,
        "url": CSV_FILENAME,
        "dc:title": {
            "en": "Complete 37-symbol Bopomofo table",
            "zh-Hant": "完整 37 符號注音表格",
        },
        "dc:description": {
            "en": (
                "A deterministic UTF-8 CSV table of all 37 standard Bopomofo "
                "symbols with Unicode, Pinyin, IPA, category and example fields."
            ),
            "zh-Hant": (
                "涵蓋全部 37 個標準注音符號的確定性 UTF-8 CSV 表格，包含 "
                "Unicode、拼音、IPA、分類與例字欄位。"
            ),
        },
        "dc:identifier": CSVW_URL,
        "dc:creator": {"@id": ORG_URI},
        "dc:publisher": {"@id": ORG_URI},
        "dc:license": {"@id": LICENSE},
        "dc:issued": {
            "@value": INITIAL_DATE,
            "@type": "http://www.w3.org/2001/XMLSchema#date",
        },
        "dc:modified": {
            "@value": modified,
            "@type": "http://www.w3.org/2001/XMLSchema#date",
        },
        "dc:language": ["en", "zh-Hant", "zh-Latn-pinyin"],
        "dc:conformsTo": [{"@id": value} for value in CSVW_RECOMMENDATIONS],
        "dc:source": [
            {"@id": SOURCE_DATASET},
            {"@id": MOE_HANDBOOK},
            {"@id": UNICODE_CHART},
        ],
        "dc:relation": [
            {"@id": PACKAGE_URL},
            {"@id": CROISSANT_PAGE},
            {"@id": SKOS_PAGE},
        ],
        "dcat:keyword": [
            "Bopomofo",
            "Zhuyin",
            "CSVW",
            "Mandarin phonetics",
            "open data",
        ],
        "dialect": {
            "encoding": "utf-8",
            "header": True,
            "headerRowCount": 1,
            "delimiter": ",",
            "quoteChar": '"',
            "doubleQuote": True,
            "lineTerminators": ["\n"],
            "skipBlankRows": False,
            "skipColumns": 0,
            "skipRows": 0,
            "trim": False,
        },
        "tableDirection": "auto",
        "tableSchema": {
            "aboutUrl": f"{SKOS_PAGE}#{{symbol_id}}",
            "primaryKey": "symbol_id",
            "columns": csvw_columns(),
        },
    }


def render_readme(csv_sha: str, csvw_sha: str) -> bytes:
    content = f"""# Bopomofo CSVW table

This deterministic bundle contains the complete 37-symbol Bopomofo (Zhuyin)
reference table and its W3C CSVW metadata.

## Validate

```sh
python3 -m pip install csvw==4.1.0
csvwvalidate {CSVW_FILENAME}
```

The metadata filename follows CSVW default discovery:
`{CSV_FILENAME}-metadata.json`.

## Integrity

- `{CSV_FILENAME}`: `{csv_sha}`
- `{CSVW_FILENAME}`: `{csvw_sha}`

Verify every bundled file with:

```sh
shasum -a 256 -c {CHECKSUM_FILENAME}
```

## Standards

- {CSVW_MODEL}
- {CSVW_METADATA}
- {CSVW_RDF}

The table is licensed under CC BY 4.0. The W3C Recommendations describe the
format but do not endorse this dataset or its publisher.
"""
    return content.encode("utf-8")


def render_license() -> bytes:
    return (
        "Bopomofo CSVW table\n"
        "Copyright 2026 Lumi Apps\n\n"
        "Licensed under Creative Commons Attribution 4.0 International "
        "(CC BY 4.0):\n"
        f"{LICENSE}\n\n"
        "Suggested attribution: Lumi Apps, Complete 37-symbol Bopomofo "
        f"table, {PACKAGE_URL}\n"
    ).encode("utf-8")


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for filename in sorted(entries):
            info = zipfile.ZipInfo(filename, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entries[filename])
    return buffer.getvalue()


def _artifact(
    filename: str,
    url: str,
    media_type: str,
    label: str,
    content: bytes,
) -> dict:
    return {
        "filename": filename,
        "url": url,
        "media_type": media_type,
        "label": label,
        "bytes": content,
        "sha256": _sha256(content),
    }


def _manifest(
    modified: str,
    downloadable: list[dict],
) -> bytes:
    distributions = []
    for artifact in downloadable:
        distributions.append(
            {
                "@type": "DataDownload",
                "name": artifact["filename"],
                "contentUrl": artifact["url"],
                "encodingFormat": artifact["media_type"],
                "contentSize": f"{len(artifact['bytes'])} B",
                "sha256": artifact["sha256"],
            }
        )
    document = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": f"{PACKAGE_URL}#dataset",
        "name": "Complete 37-symbol Bopomofo table with CSVW metadata",
        "description": (
            "A deterministic UTF-8 CSV and W3C CSVW metadata pair covering "
            "all 37 standard Bopomofo symbols."
        ),
        "url": PACKAGE_URL,
        "identifier": CSVW_URL,
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "license": LICENSE,
        "creator": {"@type": "Organization", "@id": ORG_URI, "name": "Lumi Apps"},
        "isAccessibleForFree": True,
        "inLanguage": ["en", "zh-Hant", "zh-Latn-pinyin"],
        "keywords": [
            "Bopomofo",
            "Zhuyin",
            "CSVW",
            "tabular metadata",
            "Mandarin phonetics",
        ],
        "conformsTo": list(CSVW_RECOMMENDATIONS),
        "isBasedOn": [SOURCE_DATASET, CROISSANT_PAGE, SKOS_PAGE],
        "distribution": distributions,
    }
    return _json_bytes(document)


def make_artifacts(modified: str) -> dict[str, dict]:
    rows = records()
    validate_records(rows)
    csv_bytes = render_csv(rows).encode("utf-8")
    csvw_bytes = _json_bytes(csvw_document(modified))
    readme_bytes = render_readme(_sha256(csv_bytes), _sha256(csvw_bytes))
    license_bytes = render_license()
    bundled = {
        CSV_FILENAME: csv_bytes,
        CSVW_FILENAME: csvw_bytes,
        README_FILENAME: readme_bytes,
        LICENSE_FILENAME: license_bytes,
    }
    checksums = "".join(
        f"{_sha256(content)}  {filename}\n"
        for filename, content in sorted(bundled.items())
    ).encode("utf-8")
    bundled[CHECKSUM_FILENAME] = checksums
    bundle_bytes = _zip_bytes(bundled)

    csv_artifact = _artifact(
        CSV_FILENAME,
        CSV_URL,
        CSV_MEDIA_TYPE,
        "UTF-8 CSV",
        csv_bytes,
    )
    csvw_artifact = _artifact(
        CSVW_FILENAME,
        CSVW_URL,
        CSVW_MEDIA_TYPE,
        "W3C CSVW metadata",
        csvw_bytes,
    )
    bundle_artifact = _artifact(
        BUNDLE_FILENAME,
        BUNDLE_URL,
        "application/zip",
        "Deterministic offline bundle",
        bundle_bytes,
    )
    checksum_artifact = _artifact(
        CHECKSUM_FILENAME,
        CHECKSUM_URL,
        "text/plain",
        "SHA-256 checksums",
        checksums,
    )
    manifest_bytes = _manifest(
        modified,
        [csv_artifact, csvw_artifact, bundle_artifact, checksum_artifact],
    )
    manifest_artifact = _artifact(
        MANIFEST_FILENAME,
        MANIFEST_URL,
        "application/ld+json",
        "Schema.org dataset manifest",
        manifest_bytes,
    )
    return {
        "csv": csv_artifact,
        "csvw": csvw_artifact,
        "bundle": bundle_artifact,
        "checksums": checksum_artifact,
        "manifest": manifest_artifact,
        "_readme": {"filename": README_FILENAME, "bytes": readme_bytes},
        "_license": {"filename": LICENSE_FILENAME, "bytes": license_bytes},
    }


def validate_reference_snapshots() -> None:
    sources = json.loads(REFERENCE_SOURCES.read_text(encoding="utf-8"))
    for item in sources["files"]:
        path = REFERENCE_DIR / item["filename"]
        if _sha256(path.read_bytes()) != item["sha256"]:
            raise ValueError(f"Pinned CSVW reference hash mismatch: {path.name}")
    context = json.loads(
        (REFERENCE_DIR / "csvw.jsonld").read_text(encoding="utf-8")
    )["@context"]
    required_terms = {
        "url",
        "dialect",
        "tableDirection",
        "tableSchema",
        "aboutUrl",
        "primaryKey",
        "columns",
        "name",
        "titles",
        "datatype",
        "required",
        "propertyUrl",
        "valueUrl",
        "suppressOutput",
    }
    missing = required_terms - set(context)
    if missing:
        raise ValueError(f"Pinned CSVW context is missing terms: {sorted(missing)}")
    ttl = (REFERENCE_DIR / "csvw.ttl").read_text(encoding="utf-8")
    if (
        f"@prefix csvw: <{CSVW_NAMESPACE}>" not in ttl
        or "csvw:Schema a rdfs:Class" not in ttl
        or "csvw:Dialect a rdfs:Class" not in ttl
    ):
        raise ValueError("Pinned CSVW Turtle vocabulary is incomplete")


def validate_artifacts(
    rows: list[dict],
    artifacts: dict[str, dict],
) -> None:
    validate_reference_snapshots()
    validate_records(rows)
    if artifacts["csv"]["bytes"] != render_csv(rows).encode("utf-8"):
        raise ValueError("CSVW CSV drifted from the canonical Croissant table")
    metadata = json.loads(artifacts["csvw"]["bytes"])
    if metadata["@context"] != [CSVW_CONTEXT, {"@language": "en"}]:
        raise ValueError("CSVW metadata must begin with the official context")
    if metadata["url"] != CSV_FILENAME:
        raise ValueError("CSVW metadata must resolve the adjacent canonical CSV")
    schema = metadata["tableSchema"]
    if schema["primaryKey"] != "symbol_id":
        raise ValueError("CSVW primary key must be symbol_id")
    if [item["name"] for item in schema["columns"]] != list(FIELD_NAMES):
        raise ValueError("CSVW column order drifted from the canonical table")
    if any(not item.get("required") for item in schema["columns"]):
        raise ValueError("Every CSVW column must be required")
    if {
        item["@id"] for item in metadata["dc:conformsTo"]
    } != set(CSVW_RECOMMENDATIONS):
        raise ValueError("CSVW metadata must pin all three Recommendations")
    parsed = list(
        csv.DictReader(
            io.StringIO(artifacts["csv"]["bytes"].decode("utf-8")),
            dialect="excel",
        )
    )
    if len(parsed) != 37 or tuple(parsed[0]) != FIELD_NAMES:
        raise ValueError("CSVW table must contain 37 rows and 12 named columns")
    if len({item["symbol_id"] for item in parsed}) != 37:
        raise ValueError("CSVW primary-key values must be unique")
    if any(not value for item in parsed for value in item.values()):
        raise ValueError("Required CSVW cells must not be empty")
    if [int(item["order"]) for item in parsed] != list(range(1, 38)):
        raise ValueError("CSVW integer order values must be 1 through 37")
    if any(
        item["concept_uri"] != f"{SKOS_PAGE}#{item['symbol_id']}"
        for item in parsed
    ):
        raise ValueError("CSVW row subjects must match canonical concept IRIs")
    expected_bundle = {
        CSV_FILENAME: artifacts["csv"]["bytes"],
        CSVW_FILENAME: artifacts["csvw"]["bytes"],
        README_FILENAME: artifacts["_readme"]["bytes"],
        LICENSE_FILENAME: artifacts["_license"]["bytes"],
        CHECKSUM_FILENAME: artifacts["checksums"]["bytes"],
    }
    with zipfile.ZipFile(io.BytesIO(artifacts["bundle"]["bytes"])) as archive:
        if archive.namelist() != sorted(expected_bundle):
            raise ValueError("CSVW ZIP file order or membership is not deterministic")
        for filename, content in expected_bundle.items():
            if archive.read(filename) != content:
                raise ValueError(f"CSVW ZIP content mismatch: {filename}")
            info = archive.getinfo(filename)
            if info.date_time != ZIP_TIMESTAMP:
                raise ValueError(f"CSVW ZIP timestamp is not fixed: {filename}")
    expected_checksums = "".join(
        f"{_sha256(content)}  {filename}\n"
        for filename, content in sorted(
            {
                CSV_FILENAME: artifacts["csv"]["bytes"],
                CSVW_FILENAME: artifacts["csvw"]["bytes"],
                README_FILENAME: artifacts["_readme"]["bytes"],
                LICENSE_FILENAME: artifacts["_license"]["bytes"],
            }.items()
        )
    ).encode("utf-8")
    if artifacts["checksums"]["bytes"] != expected_checksums:
        raise ValueError("CSVW checksum manifest does not match bundled files")
    manifest = json.loads(artifacts["manifest"]["bytes"])
    listed = {
        item["contentUrl"]: item
        for item in manifest["distribution"]
    }
    for key in ("csv", "csvw", "bundle", "checksums"):
        artifact = artifacts[key]
        item = listed.get(artifact["url"])
        if (
            not item
            or item["sha256"] != artifact["sha256"]
            or item["contentSize"] != f"{len(artifact['bytes'])} B"
            or item["encodingFormat"] != artifact["media_type"]
        ):
            raise ValueError(f"CSVW manifest drifted from {artifact['filename']}")
    machine_bytes = b"\n".join(
        artifacts[key]["bytes"]
        for key in (
            "csv",
            "csvw",
            "bundle",
            "checksums",
            "manifest",
            "_readme",
            "_license",
        )
    )
    for forbidden in (
        b"apps.apple.com",
        APP_ID.encode("ascii"),
        APP_NAME.encode("utf-8"),
        b"SoftwareApplication",
    ):
        if forbidden in machine_bytes:
            raise ValueError("App promotion leaked into CSVW machine artifacts")


def _prior_modified(pages: Path) -> str:
    path = pages / "data" / CSVW_FILENAME
    if not path.exists():
        return INITIAL_DATE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value["dc:modified"]["@value"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return INITIAL_DATE


def _output_paths(pages: Path) -> dict[str, Path]:
    package = pages / PACKAGE_PATH
    return {
        "csvw": pages / "data" / CSVW_FILENAME,
        "bundle": package / BUNDLE_FILENAME,
        "checksums": package / CHECKSUM_FILENAME,
        "manifest": package / MANIFEST_FILENAME,
    }


def _outputs_match(pages: Path, artifacts: dict[str, dict]) -> bool:
    for key, path in _output_paths(pages).items():
        if not path.exists() or path.read_bytes() != artifacts[key]["bytes"]:
            return False
    csv_path = pages / "data" / CSV_FILENAME
    return csv_path.exists() and csv_path.read_bytes() == artifacts["csv"]["bytes"]


def write_artifacts(
    pages: Path,
) -> tuple[dict[str, dict], str]:
    prior = _prior_modified(pages)
    artifacts = make_artifacts(prior)
    validate_artifacts(records(), artifacts)
    if _outputs_match(pages, artifacts):
        return artifacts, prior
    artifacts = make_artifacts(TODAY)
    validate_artifacts(records(), artifacts)
    paths = _output_paths(pages)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    for key, path in paths.items():
        if path.exists() and path.read_bytes() == artifacts[key]["bytes"]:
            continue
        path.write_bytes(artifacts[key]["bytes"])
    csv_path = pages / "data" / CSV_FILENAME
    if not csv_path.exists() or csv_path.read_bytes() != artifacts["csv"]["bytes"]:
        raise ValueError(
            "Canonical Croissant CSV must be generated before CSVW metadata"
        )
    return artifacts, TODAY


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def page_url(locale: str) -> str:
    return PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL


def _page_schema(
    locale: str,
    modified: str,
    artifacts: dict[str, dict],
    app_public: bool,
) -> dict:
    graph = [
        {
            "@type": "Dataset",
            "@id": f"{PACKAGE_URL}#dataset",
            "name": COPY[locale]["title"],
            "description": COPY[locale]["description"],
            "url": page_url(locale),
            "identifier": CSVW_URL,
            "datePublished": INITIAL_DATE,
            "dateModified": modified,
            "version": VERSION,
            "license": LICENSE,
            "isAccessibleForFree": True,
            "inLanguage": ["en", "zh-Hant", "zh-Latn-pinyin"],
            "conformsTo": list(CSVW_RECOMMENDATIONS),
            "isBasedOn": [SOURCE_DATASET, CROISSANT_PAGE, SKOS_PAGE],
            "distribution": [
                {
                    "@type": "DataDownload",
                    "name": artifacts[key]["label"],
                    "encodingFormat": artifacts[key]["media_type"],
                    "contentUrl": artifacts[key]["url"],
                    "contentSize": f"{len(artifacts[key]['bytes'])} B",
                    "sha256": artifacts[key]["sha256"],
                }
                for key in ("csv", "csvw", "bundle", "checksums", "manifest")
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
                    APP_KEY, f"iag_csvw_{locale.lower()}"
                ),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(locale: str, artifacts: dict[str, dict]) -> str:
    labels = {
        "csv": COPY[locale]["csv"],
        "csvw": COPY[locale]["csvw"],
        "bundle": COPY[locale]["bundle"],
        "checksums": COPY[locale]["checksums"],
        "manifest": COPY[locale]["manifest"],
    }
    return "".join(
        '<a class="download" href="{url}"><strong>{label}</strong>'
        "<span>{filename}</span></a>".format(
            url=html.escape(artifacts[key]["url"], quote=True),
            label=html.escape(labels[key]),
            filename=html.escape(artifacts[key]["filename"]),
        )
        for key in ("csv", "csvw", "bundle", "checksums", "manifest")
    )


def _field_rows(locale: str) -> str:
    def datatype_label(value: object) -> str:
        if isinstance(value, str):
            return value
        base = value["base"]
        facets = [
            f"{key}={val}"
            for key, val in value.items()
            if key != "base"
        ]
        return f"{base} ({', '.join(facets)})" if facets else base

    return "".join(
        "<tr><td><code>{name}</code></td><td>{datatype}</td>"
        "<td>{description}</td><td><code>{mapping}</code></td></tr>".format(
            name=html.escape(name),
            datatype=html.escape(datatype_label(FIELD_COPY[name]["datatype"])),
            description=html.escape(
                FIELD_COPY[name][
                    "description_en" if locale == "en" else "description_zh"
                ]
            ),
            mapping=html.escape(
                FIELD_COPY[name].get("propertyUrl", "suppressed")
            ),
        )
        for name in FIELD_NAMES
    )


def _preview_rows(locale: str) -> str:
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
        for row in records()
    )


def render_page(
    locale: str,
    artifacts: dict[str, dict],
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    croissant_page = CROISSANT_PAGE if locale == "en" else ZH_CROISSANT_PAGE
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
                appstore_url(APP_KEY, f"iag_csvw_{locale.lower()}"),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _page_schema(locale, modified, artifacts, app_public),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    cli_example = (
        "python3 -m pip install csvw==4.1.0\n"
        f"csvwvalidate {CSVW_URL}"
    )
    python_example = (
        "from csvw.metadata import Table\n\n"
        f'table = Table.from_file("{CSVW_URL}")\n'
        "rows = list(table)\n"
        'assert len(rows) == 37'
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
<link rel="describedby" type="{CSVW_MEDIA_TYPE}" href="{CSVW_URL}">
<link rel="alternate" type="{CSV_MEDIA_TYPE}" href="{CSV_URL}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#16213c;--sub:#59657a;--line:#dce4ef;--paper:#fff;--wash:#f3f7fb;--brand:#1d6d68;--soft:#eaf7f4;--code:#101827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1080px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.94);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:760;text-decoration:none;white-space:nowrap}}.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:980px}}.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:840px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}}
main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,55,98,.06)}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub);margin:8px 0}}.downloads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}ol,ul{{padding-left:24px}}li{{margin:8px 0}}pre{{background:var(--code);color:#dcecff;border-radius:16px;padding:18px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.symbol{{font-size:25px;font-weight:850}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:700;white-space:nowrap}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:800;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#eaf7f4)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:760px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{DATA_CATALOG}">{html.escape(copy['back'])}</a><a href="{html.escape(page_url(other_locale), quote=True)}">{html.escape(copy['language'])}</a></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, artifacts)}</div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><pre>{html.escape(cli_example)}</pre></article><article class="panel"><h2>Python</h2><pre>{html.escape(python_example)}</pre></article></section>
<section class="wrap panel"><h2>{html.escape(copy['contract'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['field'])}</th><th>{html.escape(copy['type'])}</th><th>{html.escape(copy['meaning'])}</th><th>{html.escape(copy['mapping'])}</th></tr></thead><tbody>{_field_rows(locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['uses'])}</h2><ul>{uses}</ul></article><article class="panel"><h2>{html.escape(copy['limits'])}</h2><ul>{limits}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['preview'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['order'])}</th><th>{html.escape(copy['symbol'])}</th><th>{html.escape(copy['category'])}</th><th>{html.escape(copy['pinyin'])}</th><th>{html.escape(copy['ipa'])}</th><th>{html.escape(copy['example'])}</th></tr></thead><tbody>{_preview_rows(locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['standards'])}</h2><p>{html.escape(copy['standards_text'])}</p><div class="sources"><a href="{html.escape(croissant_page, quote=True)}">{html.escape(copy['croissant'])}</a><a href="{html.escape(skos_page, quote=True)}">{html.escape(copy['skos'])}</a><a href="{CSVW_METADATA}" rel="noopener">{html.escape(copy['w3c'])}</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a></article></section>
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
        "<h2>Bopomofo CSVW table metadata</h2>"
        "<p>All 37 Zhuyin symbols with typed columns, a unique primary key, "
        "URI templates, default metadata discovery and SHA-256.</p>"
        '<span class="tag">W3C CSVW · EN + zh-Hant · CC BY 4.0</span></a>'
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
        item
        for item in catalog.get("dataset", [])
        if item.get("url") != PACKAGE_URL
    ]
    entry = {
        "@type": "Dataset",
        "name": COPY["en"]["title"],
        "description": COPY["en"]["description"],
        "url": PACKAGE_URL,
        "license": LICENSE,
        "conformsTo": list(CSVW_RECOMMENDATIONS),
        "distribution": [
            {
                "@type": "DataDownload",
                "name": artifacts[key]["label"],
                "encodingFormat": artifacts[key]["media_type"],
                "contentUrl": artifacts[key]["url"],
            }
            for key in ("csv", "csvw", "bundle", "checksums", "manifest")
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
            (artifacts[key]["url"], artifact_modified)
            for key in ("csvw", "bundle", "checksums", "manifest")
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
    artifacts, artifact_modified = write_artifacts(pages)
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", pages / PACKAGE_PATH / "index.html"),
        ("zh-Hant", pages / "zh-Hant" / PACKAGE_PATH / "index.html"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_page(
                locale,
                artifacts,
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    update_data_index(pages, artifacts)
    write_text_if_changed(
        pages / "sitemap_csvw.xml",
        render_sitemap(page_modified, artifact_modified, artifacts),
    )
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        CSVW_URL,
        BUNDLE_URL,
        CHECKSUM_URL,
        MANIFEST_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin CSVW resource -> {output}")


if __name__ == "__main__":
    main()
