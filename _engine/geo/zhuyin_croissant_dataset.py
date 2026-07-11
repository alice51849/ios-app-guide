#!/usr/bin/env python3
"""Publish all 37 Zhuyin symbols as an MLCommons Croissant 1.1 dataset."""

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
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import (  # noqa: E402
    render_versioned_page,
    write_text_if_changed,
)
from gen_data_hub import ZHUYIN, ZHUYIN_IPA  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from zhuyin_skos_vocabulary import (  # noqa: E402
    CATEGORIES,
    MOE_HANDBOOK,
    PROPERTIES,
    UNICODE_CHART,
    category_uri,
    concept_uri,
)


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-bopomofo-ml-dataset"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
VERSION = "1.0.0"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
LANDING_URL = f"{SITE}/data/{SLUG}.html"
ZH_LANDING_URL = f"{SITE}/zh-Hant/data/{SLUG}.html"
CSV_FILENAME = f"{SLUG}.csv"
JSONL_FILENAME = f"{SLUG}.jsonl"
METADATA_FILENAME = f"{SLUG}.croissant.jsonld"
CSV_URL = f"{SITE}/data/{CSV_FILENAME}"
JSONL_URL = f"{SITE}/data/{JSONL_FILENAME}"
METADATA_URL = f"{SITE}/data/{METADATA_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_croissant.xml"
SOURCE_DATASET = f"{SITE}/data/zhuyin-bopomofo.json"
SOURCE_PAGE = f"{SITE}/data/zhuyin-bopomofo.html"
SKOS_PAGE = f"{SITE}/data/zhuyin-bopomofo-vocabulary.html"
API_PAGE = f"{SITE}/api/v1/bopomofo-symbols/"
API_OPENAPI = f"{API_PAGE}openapi.json"
DATA_CATALOG = f"{SITE}/data/"
ORG_URI = f"{SITE}/#organization"
CROISSANT_SPEC = "http://mlcommons.org/croissant/1.1"
CROISSANT_MEDIA_TYPE = (
    'application/ld+json; profile="http://mlcommons.org/croissant/1.1"'
)
APP_KEY = "lumibopomofo"
APP_ID = "6773017109"
APP_NAME = "Lumi Bopomofo"
CONTENT_MODIFIED_RE = re.compile(
    r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"'
)

FIELD_NAMES = (
    "order",
    "symbol_id",
    "concept_uri",
    "symbol",
    "unicode",
    "pinyin",
    "ipa",
    "category",
    "category_uri",
    "example_character",
    "example_pinyin",
    "example_meaning_en",
)

CROISSANT_CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "sc": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "dct": "http://purl.org/dc/terms/",
    "prov": "http://www.w3.org/ns/prov#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "annotation": "cr:annotation",
    "arrayShape": "cr:arrayShape",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "containedIn": "cr:containedIn",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "description": {"@container": "@language"},
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "excludes": "cr:excludes",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isArray": "cr:isArray",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "name": {"@container": "@language"},
    "parentField": "cr:parentField",
    "path": "cr:path",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "readLines": "cr:readLines",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sdVersion": "cr:sdVersion",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "unArchive": "cr:unArchive",
    "value": "cr:value",
}

ARTIFACT_SPECS = {
    "csv": {
        "filename": CSV_FILENAME,
        "url": CSV_URL,
        "media_type": "text/csv",
        "format": "UTF-8 CSV",
        "label_en": "CSV table",
        "label_zh": "CSV 表格",
    },
    "jsonl": {
        "filename": JSONL_FILENAME,
        "url": JSONL_URL,
        "media_type": "application/x-ndjson",
        "format": "JSON Lines",
        "label_en": "JSONL records",
        "label_zh": "JSONL 紀錄",
    },
    "metadata": {
        "filename": METADATA_FILENAME,
        "url": METADATA_URL,
        "media_type": CROISSANT_MEDIA_TYPE,
        "format": "MLCommons Croissant 1.1",
        "label_en": "Croissant metadata",
        "label_zh": "Croissant 中繼資料",
    },
}

FIELD_SPECS = {
    "order": (
        "sc:Integer",
        "Stable educational display order from 1 to 37.",
        None,
    ),
    "symbol_id": (
        "sc:Text",
        "ASCII identifier derived from the uppercase Unicode code point.",
        None,
    ),
    "concept_uri": (
        "sc:URL",
        "Stable IRI for the symbol in the companion SKOS vocabulary.",
        "https://schema.org/url",
    ),
    "symbol": (
        "sc:Text",
        "The Bopomofo character.",
        "http://www.w3.org/2004/02/skos/core#prefLabel",
    ),
    "unicode": (
        "sc:Text",
        "Unicode notation in U+XXXX form.",
        "http://www.w3.org/2004/02/skos/core#notation",
    ),
    "pinyin": (
        "sc:Text",
        "Hanyu Pinyin correspondence.",
        PROPERTIES["pinyin"],
    ),
    "ipa": (
        "sc:Text",
        "Broad IPA transcription without brackets.",
        PROPERTIES["ipa"],
    ),
    "category": (
        "sc:Text",
        "One of initial, medial or final.",
        None,
    ),
    "category_uri": (
        "sc:URL",
        "IRI for the broader SKOS category concept.",
        "http://www.w3.org/2004/02/skos/core#broader",
    ),
    "example_character": (
        "sc:Text",
        "Traditional Chinese example character.",
        PROPERTIES["exampleCharacter"],
    ),
    "example_pinyin": (
        "sc:Text",
        "Tone-marked Pinyin for the example.",
        PROPERTIES["examplePinyin"],
    ),
    "example_meaning_en": (
        "sc:Text",
        "Short English meaning for the example.",
        PROPERTIES["exampleMeaning"],
    ),
}

CATEGORY_NAMES = {
    "en": {
        "initial": "Initial",
        "medial": "Medial",
        "final": "Final",
    },
    "zh-Hant": {
        "initial": "聲母",
        "medial": "介音",
        "final": "韻母",
    },
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo ML Dataset - All 37 Zhuyin Symbols in Croissant 1.1",
        "description": (
            "Download a CC BY 4.0 table of all 37 Bopomofo symbols as CSV and "
            "JSONL with MLCommons Croissant 1.1 metadata, stable SKOS IRIs and "
            "documented provenance."
        ),
        "eyebrow": "ML-ready metadata · Croissant 1.1 · CC BY 4.0",
        "lead": (
            "A small, deterministic reference dataset for AI agents, data catalogs "
            "and language-tool developers working with Taiwan Mandarin phonetics."
        ),
        "badges": (
            "37 records",
            "12 documented fields",
            "CSV + JSONL",
            "Croissant 1.1 validated",
        ),
        "language": "繁體中文",
        "data": "Open data",
        "downloads": "Download the dataset",
        "download_text": (
            "CSV is the canonical table loaded by the Croissant RecordSet. JSONL "
            "contains the same records, while the metadata file declares fields, "
            "checksums, stable identifiers and provenance."
        ),
        "schema": "Dataset schema",
        "schema_text": (
            "Each row represents one symbol. symbol_id is the unique key; concept_uri "
            "and category_uri connect the table to the companion SKOS vocabulary."
        ),
        "field": "Field",
        "type": "Type",
        "meaning": "Meaning",
        "preview": "Preview all 37 records",
        "order": "Order",
        "symbol": "Symbol",
        "category": "Category",
        "pinyin": "Pinyin",
        "ipa": "IPA",
        "example": "Example",
        "load": "Load with mlcroissant",
        "load_text": (
            "The official Python reader can validate the metadata, fetch the CSV and "
            "yield each row from the symbols RecordSet."
        ),
        "uses": "Intended uses",
        "use_items": (
            "Bopomofo-aware text processing and Unicode normalization tests",
            "Educational search, glossary and knowledge-graph prototypes",
            "Data-catalog demonstrations and small interoperability fixtures",
            "Joining tabular records to stable SKOS concept IRIs",
        ),
        "limits": "Limitations and non-uses",
        "limit_items": (
            "Not an audio, speech or acoustic-training corpus",
            "Not sufficient to train or benchmark Mandarin pronunciation models",
            "Not a learner assessment or diagnostic dataset",
            "Example mappings are compact reference aids, not full phonological rules",
        ),
        "sources": "Provenance and standards",
        "source_text": (
            "The table is generated deterministically from the site's open 37-symbol "
            "reference. Croissant structure follows MLCommons 1.1; code points follow "
            "Unicode, and the source page cites Taiwan's Ministry of Education."
        ),
        "source_dataset": "View the source dataset",
        "skos": "Open the SKOS vocabulary",
        "api": "Open the no-key symbol API",
        "croissant": "MLCommons Croissant 1.1 specification",
        "license": "License and privacy",
        "license_text": (
            "The dataset and original metadata are reusable under CC BY 4.0 with "
            "attribution to Lumi Apps - iOS App Guide."
        ),
        "privacy_text": (
            "No people, learner records, personal data, cookies, executable JavaScript "
            "or runtime API are included in the downloadable artifacts."
        ),
        "faq": "Questions",
        "faqs": (
            (
                "What is Croissant?",
                "Croissant is an MLCommons JSON-LD format that describes dataset files, "
                "record structure, fields, provenance and usage conditions.",
            ),
            (
                "Do the CSV and JSONL files contain the same records?",
                "Yes. Automated checks compare all 37 records and field values.",
            ),
            (
                "Does this dataset contain every Bopomofo symbol?",
                "Yes. It contains 21 initials, 3 medials and 13 finals: 37 symbols.",
            ),
            (
                "Can this train a speech model?",
                "No. It is a compact symbolic reference without audio, recordings or "
                "enough observations for speech-model training.",
            ),
        ),
        "app_title": "Optional game-based iPhone practice",
        "app_text": (
            "Lumi Bopomofo offers a separate on-device way to practise Zhuyin through "
            "short activities. The open dataset remains free and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": "Independent, machine-readable Bopomofo reference data.",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音符號 ML 資料集｜完整 37 符號 Croissant 1.1",
        "description": (
            "免費下載完整 37 注音符號 CSV、JSONL 與 MLCommons Croissant 1.1 "
            "中繼資料，包含穩定 SKOS IRI、校驗碼及資料來源。"
        ),
        "eyebrow": "ML-ready 中繼資料 · Croissant 1.1 · CC BY 4.0",
        "lead": (
            "提供 AI agent、資料目錄及台灣華語語言工具開發者使用的小型、"
            "可重現注音參考資料集。"
        ),
        "badges": (
            "37 筆紀錄",
            "12 個完整欄位",
            "CSV＋JSONL",
            "Croissant 1.1 驗證",
        ),
        "language": "English",
        "data": "開放資料",
        "downloads": "下載資料集",
        "download_text": (
            "CSV 是 Croissant RecordSet 載入的標準表格；JSONL 收錄完全相同的"
            "紀錄，中繼資料則定義欄位、校驗碼、穩定識別碼與來源。"
        ),
        "schema": "資料欄位",
        "schema_text": (
            "每列代表一個注音符號；symbol_id 是唯一鍵，concept_uri 與 "
            "category_uri 可連到配套 SKOS 詞彙。"
        ),
        "field": "欄位",
        "type": "型別",
        "meaning": "說明",
        "preview": "預覽全部 37 筆紀錄",
        "order": "順序",
        "symbol": "符號",
        "category": "分類",
        "pinyin": "漢語拼音",
        "ipa": "IPA",
        "example": "例字",
        "load": "使用 mlcroissant 載入",
        "load_text": (
            "官方 Python reader 可驗證中繼資料、下載 CSV，並逐筆讀取 symbols "
            "RecordSet。"
        ),
        "uses": "適合用途",
        "use_items": (
            "支援注音的文字處理與 Unicode 正規化測試",
            "教育搜尋、詞彙表與知識圖譜原型",
            "資料目錄示範及小型互通性測試資料",
            "以穩定 SKOS concept IRI 串接表格紀錄",
        ),
        "limits": "限制與不適用情境",
        "limit_items": (
            "不是音訊、語音或聲學訓練語料",
            "不足以訓練或評測華語發音模型",
            "不是學習者能力評量或診斷資料",
            "精簡對照僅供參考，不代表完整語音規則",
        ),
        "sources": "資料來源與標準",
        "source_text": (
            "表格由本站開放的 37 符號參考資料確定性產生；Croissant 結構依 "
            "MLCommons 1.1，code point 依 Unicode，來源頁並引用台灣教育部資料。"
        ),
        "source_dataset": "查看來源資料集",
        "skos": "開啟 SKOS 詞彙",
        "api": "開啟免金鑰符號 API",
        "croissant": "MLCommons Croissant 1.1 規格",
        "license": "授權與隱私",
        "license_text": (
            "資料集及原創中繼資料採 CC BY 4.0；標示 Lumi Apps - iOS App Guide "
            "後即可再利用。"
        ),
        "privacy_text": (
            "下載 artifact 不含人物、學習者紀錄、個資、Cookie、可執行 "
            "JavaScript 或執行期 API。"
        ),
        "faq": "常見問題",
        "faqs": (
            (
                "什麼是 Croissant？",
                "Croissant 是 MLCommons 的 JSON-LD 格式，用來描述資料檔、紀錄"
                "結構、欄位、來源與使用條件。",
            ),
            (
                "CSV 與 JSONL 的紀錄相同嗎？",
                "相同。自動檢查會逐欄比較全部 37 筆紀錄。",
            ),
            (
                "資料集包含全部注音符號嗎？",
                "包含，共 21 個聲母、3 個介音及 13 個韻母，合計 37 個符號。",
            ),
            (
                "可以拿來訓練語音模型嗎？",
                "不適合。這是沒有音訊或錄音的精簡符號參考，資料量也不足以訓練"
                "語音模型。",
            ),
        ),
        "app_title": "選用的 iPhone 遊戲化練習",
        "app_text": (
            "Lumi 注音星球提供另一種在裝置上以短活動練習注音的方式；"
            "開放資料集仍維持免費且獨立。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "提供注音教育與開發使用的獨立機器可讀參考資料。",
    },
}


def page_url(locale: str) -> str:
    return LANDING_URL if locale == "en" else ZH_LANDING_URL


def records() -> list[dict]:
    output = []
    for order, record in enumerate(ZHUYIN, start=1):
        symbol, pinyin, category, character, example_pinyin, meaning = record
        output.append(
            {
                "order": order,
                "symbol_id": f"u{ord(symbol):04X}",
                "concept_uri": concept_uri(symbol),
                "symbol": symbol,
                "unicode": f"U+{ord(symbol):04X}",
                "pinyin": pinyin,
                "ipa": ZHUYIN_IPA[symbol],
                "category": category,
                "category_uri": category_uri(category),
                "example_character": character,
                "example_pinyin": example_pinyin,
                "example_meaning_en": meaning,
            }
        )
    return output


def validate_records(rows: list[dict]) -> None:
    if len(rows) != 37:
        raise ValueError(f"Expected 37 Zhuyin records, found {len(rows)}")
    if any(tuple(row) != FIELD_NAMES for row in rows):
        raise ValueError("Croissant rows do not use the canonical field order")
    if len({row["symbol_id"] for row in rows}) != 37:
        raise ValueError("symbol_id values must be unique")
    if len({row["symbol"] for row in rows}) != 37:
        raise ValueError("Zhuyin symbols must be unique")
    expected_codepoints = set(range(0x3105, 0x312A))
    if {ord(row["symbol"]) for row in rows} != expected_codepoints:
        raise ValueError("Rows must cover exactly Unicode U+3105 through U+3129")
    if [row["order"] for row in rows] != list(range(1, 38)):
        raise ValueError("Record order must be the stable range 1 through 37")
    category_counts = {
        category: sum(row["category"] == category for row in rows)
        for category in CATEGORIES
    }
    if category_counts != {"initial": 21, "medial": 3, "final": 13}:
        raise ValueError(f"Unexpected category counts: {category_counts}")
    for row in rows:
        if row["concept_uri"] != concept_uri(row["symbol"]):
            raise ValueError(f"Invalid concept URI for {row['symbol']}")
        if row["category_uri"] != category_uri(row["category"]):
            raise ValueError(f"Invalid category URI for {row['symbol']}")


def render_csv(rows: list[dict]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=FIELD_NAMES,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render_jsonl(rows: list[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )


def _artifact(key: str, content: str) -> dict:
    spec = ARTIFACT_SPECS[key]
    raw = content.encode("utf-8")
    return {
        **spec,
        "content": content,
        "bytes": raw,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def make_data_artifacts(rows: list[dict] | None = None) -> dict[str, dict]:
    rows = records() if rows is None else rows
    validate_records(rows)
    artifacts = {
        "csv": _artifact("csv", render_csv(rows)),
        "jsonl": _artifact("jsonl", render_jsonl(rows)),
    }
    validate_data_artifacts(artifacts, rows)
    return artifacts


def validate_data_artifacts(
    artifacts: dict[str, dict],
    expected_rows: list[dict],
) -> None:
    csv_rows = list(csv.DictReader(io.StringIO(artifacts["csv"]["content"])))
    normalized_csv = [
        {**row, "order": int(row["order"])}
        for row in csv_rows
    ]
    jsonl_rows = [
        json.loads(line)
        for line in artifacts["jsonl"]["content"].splitlines()
        if line
    ]
    if normalized_csv != expected_rows or jsonl_rows != expected_rows:
        raise ValueError("CSV, JSONL and source records must be identical")
    for artifact in artifacts.values():
        if artifact["content"].startswith("\ufeff"):
            raise ValueError(f"{artifact['filename']} must not contain a UTF-8 BOM")
        if hashlib.sha256(artifact["bytes"]).hexdigest() != artifact["sha256"]:
            raise ValueError(f"Invalid checksum for {artifact['filename']}")
        forbidden = ("apps.apple.com", APP_ID, APP_NAME, "SoftwareApplication")
        if any(value in artifact["content"] for value in forbidden):
            raise ValueError(f"App promotion leaked into {artifact['filename']}")


def _field_metadata(name: str) -> dict:
    data_type, description, equivalent_property = FIELD_SPECS[name]
    field = {
        "@type": "cr:Field",
        "@id": f"symbols/{name}",
        "name": name,
        "description": description,
        "dataType": data_type,
        "source": {
            "fileObject": {"@id": CSV_FILENAME},
            "extract": {"column": name},
        },
    }
    if equivalent_property:
        field["equivalentProperty"] = equivalent_property
    return field


def croissant_metadata(
    rows: list[dict],
    artifacts: dict[str, dict],
    modified: str,
) -> dict:
    distributions = []
    for key, alternate in (("csv", "jsonl"), ("jsonl", "csv")):
        artifact = artifacts[key]
        distributions.append(
            {
                "@type": "cr:FileObject",
                "@id": artifact["filename"],
                "name": artifact["filename"],
                "description": (
                    "Canonical UTF-8 table for the symbols RecordSet."
                    if key == "csv"
                    else "The same 37 records serialized as newline-delimited JSON."
                ),
                "contentUrl": artifact["url"],
                "contentSize": f"{len(artifact['bytes'])} B",
                "encodingFormat": artifact["media_type"],
                "sha256": artifact["sha256"],
                "sameAs": artifacts[alternate]["url"],
            }
        )
    return {
        "@context": CROISSANT_CONTEXT,
        "@id": LANDING_URL,
        "@type": "sc:Dataset",
        "conformsTo": CROISSANT_SPEC,
        "name": {
            "en": COPY["en"]["title"],
            "zh-Hant": COPY["zh-Hant"]["title"],
        },
        "description": {
            "en": COPY["en"]["description"],
            "zh-Hant": COPY["zh-Hant"]["description"],
        },
        "license": LICENSE,
        "url": LANDING_URL,
        "creator": {
            "@id": ORG_URI,
            "@type": "sc:Organization",
            "name": "Lumi Apps - iOS App Guide",
            "url": SITE,
        },
        "publisher": {"@id": ORG_URI},
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "version": VERSION,
        "sdVersion": VERSION,
        "isLiveDataset": False,
        "isAccessibleForFree": True,
        "inLanguage": ["en", "zh-Hant", "zh-Latn-pinyin"],
        "keywords": [
            "Bopomofo",
            "Zhuyin",
            "注音符號",
            "Taiwan Mandarin",
            "phonetics",
            "Unicode",
            "MLCommons Croissant",
            "language dataset",
        ],
        "identifier": LANDING_URL,
        "includedInDataCatalog": DATA_CATALOG,
        "isBasedOn": [SOURCE_DATASET, SKOS_PAGE],
        "conditionsOfAccess": "Open access; no account or API key required.",
        "measurementTechnique": (
            "Deterministic tabular projection of the complete 37-symbol reference."
        ),
        "citeAs": (
            "@misc{lumi_bopomofo_croissant_2026, "
            "title={Bopomofo ML Dataset - All 37 Zhuyin Symbols}, "
            "author={Lumi Apps - iOS App Guide}, year={2026}, "
            f"url={{{LANDING_URL}}}}}"
        ),
        "prov:wasDerivedFrom": [
            {"@id": SOURCE_DATASET},
            {"@id": MOE_HANDBOOK},
            {"@id": UNICODE_CHART},
        ],
        "prov:wasGeneratedBy": {
            "@id": f"{LANDING_URL}#generation",
            "@type": "prov:Activity",
            "name": "Deterministic Zhuyin table generation",
            "prov:used": [
                {"@id": SOURCE_DATASET},
                {"@id": SKOS_PAGE},
            ],
            "prov:wasAssociatedWith": {"@id": ORG_URI},
        },
        "distribution": distributions,
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "symbols",
                "name": "symbols",
                "description": (
                    "One record for each of the 37 standard Bopomofo symbols."
                ),
                "dataType": "skos:Concept",
                "key": {"@id": "symbols/symbol_id"},
                "examples": rows[:2],
                "field": [_field_metadata(name) for name in FIELD_NAMES],
            }
        ],
    }


def validate_metadata(
    metadata: dict,
    rows: list[dict],
    artifacts: dict[str, dict],
) -> None:
    required = {
        "@context",
        "@type",
        "conformsTo",
        "description",
        "license",
        "name",
        "url",
        "creator",
        "datePublished",
    }
    missing = required - set(metadata)
    if missing:
        raise ValueError(f"Croissant metadata is missing required fields: {missing}")
    if metadata["@type"] != "sc:Dataset":
        raise ValueError("Croissant top-level type must be sc:Dataset")
    if metadata["conformsTo"] != CROISSANT_SPEC:
        raise ValueError("Croissant metadata must conform to version 1.1")
    if metadata["@context"] != CROISSANT_CONTEXT:
        raise ValueError("Croissant metadata must use the canonical extended context")
    distributions = {
        distribution["@id"]: distribution
        for distribution in metadata["distribution"]
    }
    if set(distributions) != {CSV_FILENAME, JSONL_FILENAME}:
        raise ValueError("Croissant metadata must describe CSV and JSONL files")
    for key in ("csv", "jsonl"):
        artifact = artifacts[key]
        distribution = distributions[artifact["filename"]]
        if distribution["contentUrl"] != artifact["url"]:
            raise ValueError(f"Invalid content URL for {artifact['filename']}")
        if distribution["sha256"] != artifact["sha256"]:
            raise ValueError(f"Invalid metadata checksum for {artifact['filename']}")
        if distribution["contentSize"] != f"{len(artifact['bytes'])} B":
            raise ValueError(f"Invalid metadata size for {artifact['filename']}")
    record_sets = metadata["recordSet"]
    if len(record_sets) != 1 or record_sets[0]["@id"] != "symbols":
        raise ValueError("Croissant metadata must define the symbols RecordSet")
    record_set = record_sets[0]
    if record_set["key"] != {"@id": "symbols/symbol_id"}:
        raise ValueError("symbol_id must be the RecordSet key")
    fields = record_set["field"]
    if [field["name"] for field in fields] != list(FIELD_NAMES):
        raise ValueError("Croissant fields do not match the tabular schema")
    for field in fields:
        if field["source"]["fileObject"] != {"@id": CSV_FILENAME}:
            raise ValueError(f"{field['name']} must source the canonical CSV")
        if field["source"]["extract"] != {"column": field["name"]}:
            raise ValueError(f"{field['name']} uses the wrong CSV column")
    if record_set["examples"] != rows[:2]:
        raise ValueError("Croissant examples must match source records")
    encoded = json.dumps(metadata, ensure_ascii=False)
    forbidden = ("apps.apple.com", APP_ID, APP_NAME, "SoftwareApplication")
    if any(value in encoded for value in forbidden):
        raise ValueError("App promotion leaked into Croissant metadata")


def _metadata_artifact(metadata: dict) -> dict:
    content = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    return _artifact("metadata", content)


def _prior_modified(path: Path) -> str:
    if not path.exists():
        return INITIAL_DATE
    match = CONTENT_MODIFIED_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else INITIAL_DATE


def _candidates(modified: str) -> tuple[list[dict], dict, dict[str, dict]]:
    rows = records()
    artifacts = make_data_artifacts(rows)
    metadata = croissant_metadata(rows, artifacts, modified)
    validate_metadata(metadata, rows, artifacts)
    downloads = {**artifacts, "metadata": _metadata_artifact(metadata)}
    return rows, metadata, downloads


def write_versioned_artifacts(
    data_directory: Path,
) -> tuple[list[dict], dict, dict[str, dict], str]:
    metadata_path = data_directory / METADATA_FILENAME
    prior_date = _prior_modified(metadata_path)
    rows, metadata, downloads = _candidates(prior_date)
    logical_change = any(
        (data_directory / artifact["filename"]).exists()
        and (data_directory / artifact["filename"]).read_text(encoding="utf-8")
        != artifact["content"]
        for artifact in downloads.values()
    )
    if logical_change:
        rows, metadata, downloads = _candidates(TODAY)
        modified = TODAY
    else:
        modified = prior_date
    for artifact in downloads.values():
        write_text_if_changed(
            data_directory / artifact["filename"],
            artifact["content"],
        )
    return rows, metadata, downloads, modified


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match the registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _auxiliary_schema(locale: str, app_public: bool) -> dict:
    copy = COPY[locale]
    graph = [
        {
            "@type": "WebPage",
            "@id": page_url(locale),
            "name": copy["title"],
            "description": copy["description"],
            "url": page_url(locale),
            "inLanguage": locale,
            "mainEntity": {"@id": LANDING_URL},
        },
        {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
                for question, answer in copy["faqs"]
            ],
        },
    ]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "applicationCategory": "EducationApplication",
                "operatingSystem": "iOS",
                "url": appstore_url(
                    APP_KEY,
                    f"iag_croissant_{locale.lower()}",
                ),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(locale: str, downloads: dict[str, dict]) -> str:
    label_key = "label_en" if locale == "en" else "label_zh"
    return "".join(
        '<a class="download" href="{url}" download>'
        "<strong>{label}</strong>"
        "<span>{format_name} · {size:,} bytes · SHA-256 {sha}…</span>"
        "</a>".format(
            url=html.escape(artifact["url"], quote=True),
            label=html.escape(artifact[label_key]),
            format_name=html.escape(artifact["format"]),
            size=len(artifact["bytes"]),
            sha=artifact["sha256"][:12],
        )
        for artifact in downloads.values()
    )


def _field_rows(locale: str) -> str:
    copy = COPY[locale]
    return "".join(
        "<tr><td><code>{name}</code></td><td>{data_type}</td><td>{meaning}</td></tr>".format(
            name=html.escape(name),
            data_type=html.escape(FIELD_SPECS[name][0]),
            meaning=html.escape(FIELD_SPECS[name][1]),
        )
        for name in FIELD_NAMES
    )


def _preview_rows(locale: str, rows: list[dict]) -> str:
    return "".join(
        "<tr><td>{order}</td><td class=\"symbol\">{symbol}</td>"
        "<td>{category}</td><td>{pinyin}</td><td>[{ipa}]</td>"
        "<td>{character} ({example})</td></tr>".format(
            order=row["order"],
            symbol=html.escape(row["symbol"]),
            category=html.escape(CATEGORY_NAMES[locale][row["category"]]),
            pinyin=html.escape(row["pinyin"]),
            ipa=html.escape(row["ipa"]),
            character=html.escape(row["example_character"]),
            example=html.escape(row["example_pinyin"]),
        )
        for row in rows
    )


def render_page(
    locale: str,
    rows: list[dict],
    metadata: dict,
    downloads: dict[str, dict],
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    uses = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["use_items"]
    )
    limits = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["limit_items"]
    )
    faqs = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in copy["faqs"]
    )
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel app"><h2>{title}</h2><p>{text}</p>'
            '<a class="button" href="{url}" rel="nofollow noopener">{cta}</a>'
            "</section>"
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(
                    APP_KEY,
                    f"iag_croissant_{locale.lower()}",
                ),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    croissant_schema = json.dumps(
        metadata,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    auxiliary_schema = json.dumps(
        _auxiliary_schema(locale, app_public),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    load_example = (
        "import mlcroissant as mlc\n\n"
        f'dataset = mlc.Dataset(jsonld="{METADATA_URL}")\n'
        'records = dataset.records(record_set="symbols")\n'
        "first = next(iter(records))"
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
<link rel="alternate" hreflang="en" href="{html.escape(page_url('en'), quote=True)}">
<link rel="alternate" hreflang="zh-Hant" href="{html.escape(page_url('zh-Hant'), quote=True)}">
<link rel="alternate" hreflang="x-default" href="{html.escape(page_url('en'), quote=True)}">
<link rel="describedby" type="{html.escape(CROISSANT_MEDIA_TYPE, quote=True)}" href="{METADATA_URL}">
<link rel="alternate" type="text/csv" href="{CSV_URL}">
<link rel="alternate" type="application/x-ndjson" href="{JSONL_URL}">
<link rel="service-desc" type="application/vnd.oai.openapi+json;version=3.1" href="{API_OPENAPI}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
<meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
<meta property="og:url" content="{html.escape(page_url(locale), quote=True)}">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{croissant_schema}</script>
<script type="application/ld+json">{auxiliary_schema}</script>
<style>
:root{{--ink:#172039;--sub:#59657a;--line:#dfe5ef;--paper:#fff;--wash:#f4f7fc;--brand:#3159c9;--soft:#edf3ff;--mint:#e8f8f2;--code:#101827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1060px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.92);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:750;text-decoration:none;white-space:nowrap}}.links{{display:flex;gap:18px}}.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:970px}}.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:830px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}}
main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,55,98,.06)}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub);margin:8px 0}}.downloads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}ol,ul{{padding-left:24px}}li{{margin:8px 0}}pre{{background:var(--code);color:#dbe8ff;border-radius:16px;padding:18px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.symbol{{font-size:25px;font-weight:850}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:700;white-space:nowrap}}details{{border-top:1px solid var(--line);padding:12px 0}}summary{{cursor:pointer;font-weight:800}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:800;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#edf3ff)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:760px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{DATA_CATALOG}">{html.escape(copy['data'])}</a><nav class="links"><a href="{html.escape(page_url(other_locale), quote=True)}">{html.escape(copy['language'])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, downloads)}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['schema'])}</h2><p>{html.escape(copy['schema_text'])}</p><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['field'])}</th><th>{html.escape(copy['type'])}</th><th>{html.escape(copy['meaning'])}</th></tr></thead><tbody>{_field_rows(locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['load'])}</h2><p>{html.escape(copy['load_text'])}</p><pre>{html.escape(load_example)}</pre></article><article class="panel"><h2>{html.escape(copy['uses'])}</h2><ul>{uses}</ul><h2>{html.escape(copy['limits'])}</h2><ul>{limits}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['preview'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['order'])}</th><th>{html.escape(copy['symbol'])}</th><th>{html.escape(copy['category'])}</th><th>{html.escape(copy['pinyin'])}</th><th>{html.escape(copy['ipa'])}</th><th>{html.escape(copy['example'])}</th></tr></thead><tbody>{_preview_rows(locale, rows)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['source_text'])}</p><div class="sources"><a href="{SOURCE_PAGE}">{html.escape(copy['source_dataset'])}</a><a href="{SKOS_PAGE}">{html.escape(copy['skos'])}</a><a href="{API_PAGE}">{html.escape(copy['api'])}</a><a href="{CROISSANT_SPEC}" rel="noopener">{html.escape(copy['croissant'])}</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a><p>{html.escape(copy['privacy_text'])}</p></article></section>
<section class="wrap panel"><h2>{html.escape(copy['faq'])}</h2>{faqs}</section>
<div class="wrap">{app_section}</div>
</main>
<footer class="footer">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def update_data_index(
    pages: Path = PAGES,
    downloads: dict[str, dict] | None = None,
) -> bool:
    index = pages / "data" / "index.html"
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    card = (
        f'<a class="item" href="{LANDING_URL}">'
        "<h2>Bopomofo ML dataset with Croissant 1.1</h2>"
        "<p>All 37 Zhuyin symbols as CSV and JSONL with documented fields, "
        "checksums, provenance and stable SKOS IRIs.</p>"
        '<span class="tag">AI/ML data · EN + zh-Hant · CC BY 4.0</span></a>'
    )
    existing = re.compile(
        r'<a class="item" href="'
        + re.escape(LANDING_URL)
        + r'">.*?</a>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    source_card = re.search(
        r'<a class="item" href="'
        + re.escape(SOURCE_PAGE)
        + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if not source_card:
        raise RuntimeError("data/index.html is missing the Zhuyin source card")
    position = source_card.end()
    updated = updated[:position] + card + updated[position:]
    schema_pattern = re.compile(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        re.DOTALL,
    )
    schema_match = schema_pattern.search(updated)
    if not schema_match:
        raise RuntimeError("data/index.html is missing its DataCatalog JSON-LD")
    schema = json.loads(schema_match.group(2))
    datasets = [
        dataset
        for dataset in schema.get("dataset", [])
        if dataset.get("url") != LANDING_URL
    ]
    dataset_entry = {
        "@type": "Dataset",
        "name": COPY["en"]["title"],
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "license": LICENSE,
        "conformsTo": CROISSANT_SPEC,
        "distribution": [
            {
                "@type": "DataDownload",
                "name": artifact["format"],
                "encodingFormat": artifact["media_type"],
                "contentUrl": artifact["url"],
            }
            for artifact in (downloads or {}).values()
        ],
    }
    source_position = next(
        (
            offset + 1
            for offset, dataset in enumerate(datasets)
            if dataset.get("url") == SOURCE_PAGE
        ),
        0,
    )
    datasets.insert(source_position, dataset_entry)
    schema["dataset"] = datasets
    encoded_schema = json.dumps(schema, ensure_ascii=False)
    updated = (
        updated[: schema_match.start()]
        + schema_match.group(1)
        + encoded_schema
        + schema_match.group(3)
        + updated[schema_match.end() :]
    )
    return write_text_if_changed(index, updated)


def render_sitemap(
    page_modified: dict[str, str],
    artifact_modified: str,
    downloads: dict[str, dict],
) -> str:
    entries = [
        (page_url("en"), page_modified["en"]),
        (page_url("zh-Hant"), page_modified["zh-Hant"]),
        *[
            (artifact["url"], artifact_modified)
            for artifact in downloads.values()
        ],
    ]
    rows = "\n".join(
        f"  <url><loc>{url}</loc><lastmod>{modified}</lastmod></url>"
        for url, modified in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    data_directory = pages / "data"
    zh_data_directory = pages / "zh-Hant" / "data"
    data_directory.mkdir(parents=True, exist_ok=True)
    zh_data_directory.mkdir(parents=True, exist_ok=True)
    rows, metadata, downloads, artifact_modified = write_versioned_artifacts(
        data_directory
    )
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, directory in (
        ("en", data_directory),
        ("zh-Hant", zh_data_directory),
    ):
        page_modified[locale] = render_versioned_page(
            directory / f"{SLUG}.html",
            lambda modified, locale=locale: render_page(
                locale,
                rows,
                metadata,
                downloads,
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    update_data_index(pages, downloads)
    write_text_if_changed(
        pages / "sitemap_croissant.xml",
        render_sitemap(page_modified, artifact_modified, downloads),
    )
    return [
        page_url("en"),
        page_url("zh-Hant"),
        *[artifact["url"] for artifact in downloads.values()],
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin Croissant resource -> {output}")


if __name__ == "__main__":
    main()
