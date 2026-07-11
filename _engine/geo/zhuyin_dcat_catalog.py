#!/usr/bin/env python3
"""Publish a static W3C DCAT 3 catalog for the open Bopomofo resources."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from family_travel_dataset import render_versioned_page, write_text_if_changed
from videogen.registry import appstore_url
from zhuyin_croissant_dataset import APP_ID, APP_KEY, APP_NAME, LICENSE, SITE
from zhuyin_epub_opds import is_app_public
from zhuyin_library_catalog import (
    _next_timestamp,
    _sha256,
    _write_bytes_if_changed,
)


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
VERSION = "1.0.0"

SLUG = "zhuyin-bopomofo-dcat3-open-data-catalog"
PACKAGE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-dcat3"
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}"
LANDING_PATH = Path("data") / f"{SLUG}.html"
ZH_LANDING_PATH = Path("zh-Hant") / LANDING_PATH
LANDING_URL = f"{SITE}/{LANDING_PATH.as_posix()}"
ZH_LANDING_URL = f"{SITE}/{ZH_LANDING_PATH.as_posix()}"
SITEMAP_PATH = Path("sitemap_dcat.xml")

JSONLD_FILENAME = "bopomofo-open-data-catalog.dcat.jsonld"
TURTLE_FILENAME = "bopomofo-open-data-catalog.dcat.ttl"
BUNDLE_FILENAME = "bopomofo-open-data-catalog-dcat3-bundle.zip"
METADATA_FILENAME = "metadata.jsonld"
PRIMARY_FILENAMES = (JSONLD_FILENAME, TURTLE_FILENAME)
DOWNLOAD_FILENAMES = (
    BUNDLE_FILENAME,
    *PRIMARY_FILENAMES,
    METADATA_FILENAME,
)

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"
DCAT = "http://www.w3.org/ns/dcat#"
DCTERMS = "http://purl.org/dc/terms/"
FOAF = "http://xmlns.com/foaf/0.1/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
SPDX = "http://spdx.org/rdf/terms#"

DCAT_SPEC = "https://www.w3.org/TR/vocab-dcat-3/"
DCAT_VOCAB = "https://www.w3.org/ns/dcat3.ttl"
SPDX_TERMS = "https://spdx.org/rdf/terms/"
OPENAPI_SPEC = "https://spec.openapis.org/oas/v3.1.1"
WEBPUB_SPEC = "https://readium.org/webpub-manifest/"
OPDS2_SPEC = "https://specs.opds.io/opds-2.0"
OPDS1_SPEC = "https://specs.opds.io/opds-1.2"
LANG_EN = "http://id.loc.gov/vocabulary/iso639-1/en"
LANG_ZH = "http://id.loc.gov/vocabulary/iso639-1/zh"
CREATOR = "Lumi Apps - iOS App Guide"
CREATOR_URL = f"{SITE}/#organization"
CATALOG_ID = f"{LANDING_URL}#catalog"
THEME_SCHEME = f"{LANDING_URL}#themes"
API_SERVICE = f"{SITE}/api/v1/bopomofo-symbols#service"
API_INDEX = f"{SITE}/api/v1/bopomofo-symbols/index.json"
API_OPENAPI = f"{SITE}/api/v1/bopomofo-symbols/openapi.json"
API_LANDING = f"{SITE}/api/v1/bopomofo-symbols/"
CARD_START = "<!-- dcat3-card:start -->"
CARD_END = "<!-- dcat3-card:end -->"

FORMATS = {
    JSONLD_FILENAME: ("DCAT 3 JSON-LD", "application/ld+json"),
    TURTLE_FILENAME: ("DCAT 3 Turtle", "text/turtle"),
    BUNDLE_FILENAME: ("Complete ZIP bundle", "application/zip"),
    METADATA_FILENAME: ("Checksums and package metadata", "application/ld+json"),
}

PREFIXES = {
    "dcat": DCAT,
    "dcterms": DCTERMS,
    "foaf": FOAF,
    "rdf": RDF,
    "rdfs": RDFS,
    "skos": SKOS,
    "spdx": SPDX,
    "xsd": XSD,
}


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    title_en: str
    title_zh: str
    description_en: str
    description_zh: str
    landing_path: str
    metadata_path: str
    distribution_paths: tuple[str, ...]
    keywords: tuple[str, ...]
    conforms_to: tuple[str, ...] = ()
    has_api_service: bool = False


@dataclass(frozen=True)
class Artifact:
    relative_path: str
    url: str
    media_type: str
    size: int
    sha256: str
    languages: tuple[str, ...]


@dataclass(frozen=True)
class Dataset:
    spec: DatasetSpec
    identifier: str
    record_identifier: str
    issued: str
    modified: str
    artifacts: tuple[Artifact, ...]


@dataclass(frozen=True)
class Iri:
    value: str


@dataclass(frozen=True)
class Literal:
    value: str
    language: str | None = None
    datatype: str | None = None


DATASETS = (
    DatasetSpec(
        key="symbols",
        title_en="Complete 37-symbol Bopomofo reference data",
        title_zh="完整 37 符號注音參考資料",
        description_en=(
            "The complete Bopomofo inventory with Unicode, Hanyu Pinyin, "
            "broad IPA, category and example fields."
        ),
        description_zh=(
            "完整注音符號清單，包含 Unicode、漢語拼音、概略 IPA、分類與例字欄位。"
        ),
        landing_path="data/zhuyin-bopomofo.html",
        metadata_path="data/zhuyin-bopomofo.json",
        distribution_paths=(
            "data/zhuyin-bopomofo.json",
            "api/v1/bopomofo-symbols/index.json",
        ),
        keywords=("Bopomofo", "Zhuyin", "Unicode", "Mandarin phonetics"),
        has_api_service=True,
    ),
    DatasetSpec(
        key="skos",
        title_en="Bopomofo SKOS linked-open-data vocabulary",
        title_zh="注音符號 SKOS Linked Open Data 詞彙",
        description_en=(
            "All 37 Bopomofo symbols as stable SKOS concepts in JSON-LD, "
            "Turtle and N-Triples, with SHACL validation shapes."
        ),
        description_zh=(
            "將全部 37 個注音符號建模為穩定 SKOS 概念，提供 JSON-LD、Turtle、"
            "N-Triples 與 SHACL 驗證形狀。"
        ),
        landing_path="data/zhuyin-bopomofo-vocabulary.html",
        metadata_path="data/zhuyin-bopomofo-vocabulary.metadata.jsonld",
        distribution_paths=(
            "data/zhuyin-bopomofo-vocabulary.jsonld",
            "data/zhuyin-bopomofo-vocabulary.ttl",
            "data/zhuyin-bopomofo-vocabulary.nt",
            "data/zhuyin-bopomofo-vocabulary.shacl.ttl",
            "data/zhuyin-bopomofo-vocabulary.metadata.jsonld",
        ),
        keywords=("SKOS", "linked open data", "Bopomofo", "SHACL"),
        conforms_to=(
            "https://www.w3.org/TR/skos-reference/",
            "https://www.w3.org/TR/json-ld11/",
            "https://www.w3.org/TR/shacl/",
        ),
    ),
    DatasetSpec(
        key="croissant",
        title_en="Bopomofo table with Croissant 1.1 and CSVW metadata",
        title_zh="附 Croissant 1.1 與 CSVW metadata 的注音表格資料集",
        description_en=(
            "A 37-row UTF-8 table in CSV and JSON Lines with MLCommons "
            "Croissant 1.1 and W3C CSVW metadata."
        ),
        description_zh=(
            "37 列 UTF-8 注音表格，提供 CSV、JSON Lines 與 MLCommons "
            "Croissant 1.1、W3C CSVW metadata。"
        ),
        landing_path="data/zhuyin-bopomofo-ml-dataset.html",
        metadata_path="data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        distribution_paths=(
            "data/zhuyin-bopomofo-ml-dataset.csv",
            "data/zhuyin-bopomofo-ml-dataset.jsonl",
            "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
            "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
            "data/packages/zhuyin-bopomofo-csvw/bopomofo-37-symbols-csvw-bundle.zip",
            "data/packages/zhuyin-bopomofo-csvw/checksums-sha256.txt",
            "data/packages/zhuyin-bopomofo-csvw/metadata.jsonld",
        ),
        keywords=(
            "Croissant",
            "CSVW",
            "CSV",
            "JSON Lines",
            "machine learning",
        ),
        conforms_to=(
            "http://mlcommons.org/croissant/1.1",
            "https://www.w3.org/TR/2015/REC-tabular-data-model-20151217/",
            "https://www.w3.org/TR/2015/REC-tabular-metadata-20151217/",
            "https://www.w3.org/TR/2015/REC-csv2rdf-20151217/",
        ),
    ),
    DatasetSpec(
        key="data-package",
        title_en="Bopomofo Frictionless Data Package 2.0",
        title_zh="注音 Frictionless Data Package 2.0",
        description_en=(
            "A portable Data Package 2.0 containing the complete typed "
            "37-symbol CSV table and its Table Schema."
        ),
        description_zh=(
            "可攜式 Data Package 2.0，包含完整 37 符號 CSV 型別表格與 Table Schema。"
        ),
        landing_path="data/packages/zhuyin-bopomofo/",
        metadata_path="data/packages/zhuyin-bopomofo/datapackage.json",
        distribution_paths=(
            "data/packages/zhuyin-bopomofo/datapackage.json",
            "data/packages/zhuyin-bopomofo/table-schema.json",
            "data/packages/zhuyin-bopomofo/symbols.csv",
        ),
        keywords=("Data Package", "Frictionless Data", "Table Schema", "CSV"),
        conforms_to=("https://datapackage.org/standard/data-package/",),
    ),
    DatasetSpec(
        key="bagit",
        title_en="Bopomofo RFC 8493 BagIt preservation package",
        title_zh="注音 RFC 8493 BagIt 數位保存套件",
        description_en=(
            "A deterministic BagIt 1.0 deposit package with ten preserved "
            "payload files, exact Payload-Oxum and SHA-256 and SHA-512 fixity."
        ),
        description_zh=(
            "Deterministic BagIt 1.0 deposit package，保存 10 個 payload 檔案，"
            "並提供精確 Payload-Oxum、SHA-256 與 SHA-512 fixity。"
        ),
        landing_path="data/packages/zhuyin-bopomofo-bagit/",
        metadata_path="data/packages/zhuyin-bopomofo-bagit/metadata.jsonld",
        distribution_paths=(
            "data/packages/zhuyin-bopomofo-bagit/bopomofo-37-symbols-bagit-rfc8493.zip",
            "data/packages/zhuyin-bopomofo-bagit/checksums-sha256.txt",
            "data/packages/zhuyin-bopomofo-bagit/metadata.jsonld",
        ),
        keywords=("BagIt", "RFC 8493", "digital preservation", "fixity"),
        conforms_to=("https://www.rfc-editor.org/rfc/rfc8493",),
    ),
    DatasetSpec(
        key="anki",
        title_en="Bopomofo Anki import decks",
        title_zh="注音 Anki 匯入牌組",
        description_en=(
            "English and Traditional Chinese UTF-8 tab-separated flashcard "
            "imports covering all 37 symbols."
        ),
        description_zh=(
            "英文與繁體中文 UTF-8 tab-separated 字卡匯入檔，完整涵蓋 37 個符號。"
        ),
        landing_path="tools/zhuyin-bopomofo-anki-deck.html",
        metadata_path="tools/zhuyin-bopomofo-anki-deck.metadata.json",
        distribution_paths=(
            "tools/zhuyin-bopomofo-anki-deck-en.tsv",
            "tools/zhuyin-bopomofo-anki-deck-zh-hant.tsv",
            "tools/zhuyin-bopomofo-anki-deck.metadata.json",
        ),
        keywords=("Anki", "flashcards", "Bopomofo practice", "TSV"),
    ),
    DatasetSpec(
        key="lms",
        title_en="Bopomofo LMS assessment bank",
        title_zh="注音 LMS 題庫",
        description_en=(
            "Thirty-seven symbol-recognition questions packaged for QTI 2.1 "
            "and Moodle XML, plus a CSV answer key."
        ),
        description_zh=(
            "37 題符號辨識題，提供 QTI 2.1、Moodle XML 與 CSV 答案表。"
        ),
        landing_path="data/zhuyin-bopomofo-lms-question-bank.html",
        metadata_path="data/packages/zhuyin-bopomofo-lms/metadata.jsonld",
        distribution_paths=(
            "data/packages/zhuyin-bopomofo-lms/bopomofo-qti-2.1-en.zip",
            "data/packages/zhuyin-bopomofo-lms/bopomofo-qti-2.1-zh-hant.zip",
            "data/packages/zhuyin-bopomofo-lms/bopomofo-moodle-en.xml",
            "data/packages/zhuyin-bopomofo-lms/bopomofo-moodle-zh-hant.xml",
            "data/packages/zhuyin-bopomofo-lms/answer-key.csv",
            "data/packages/zhuyin-bopomofo-lms/metadata.jsonld",
        ),
        keywords=("QTI 2.1", "Moodle XML", "assessment", "LMS"),
        conforms_to=(
            "https://www.imsglobal.org/question/qtiv2p1/imsqti_implv2p1.html",
            "https://docs.moodle.org/en/Import_questions",
        ),
    ),
    DatasetSpec(
        key="epub",
        title_en="Bopomofo EPUB 3.3 publication and OPDS catalogs",
        title_zh="注音 EPUB 3.3 出版品與 OPDS 目錄",
        description_en=(
            "English and Traditional Chinese EPUB 3.3 reference editions "
            "with Readium manifests and OPDS 2.0 and 1.2 catalogs."
        ),
        description_zh=(
            "英文與繁體中文 EPUB 3.3 參考書，附 Readium manifest、OPDS 2.0 "
            "與 OPDS 1.2 目錄。"
        ),
        landing_path="data/zhuyin-bopomofo-epub-reference.html",
        metadata_path="data/packages/zhuyin-bopomofo-epub/metadata.jsonld",
        distribution_paths=(
            "data/packages/zhuyin-bopomofo-epub/bopomofo-37-symbol-reference-en.epub",
            "data/packages/zhuyin-bopomofo-epub/bopomofo-37-symbol-reference-zh-hant.epub",
            "publications/bopomofo-37-symbol-reference/en/manifest.json",
            "publications/bopomofo-37-symbol-reference/zh-Hant/manifest.json",
            "opds/bopomofo-37-symbol-reference.json",
            "opds/bopomofo-37-symbol-reference.xml",
            "data/packages/zhuyin-bopomofo-epub/metadata.jsonld",
        ),
        keywords=("EPUB 3.3", "OPDS", "Readium", "accessible publication"),
        conforms_to=(
            "https://www.w3.org/TR/epub-33/",
            WEBPUB_SPEC,
            OPDS2_SPEC,
            OPDS1_SPEC,
        ),
    ),
    DatasetSpec(
        key="library",
        title_en="Bopomofo EPUB library catalog records",
        title_zh="注音 EPUB 圖書館書目紀錄",
        description_en=(
            "Candidate MARCXML, MODS 3.8 and BIBFRAME 2.0 records for the "
            "two exact open EPUB editions."
        ),
        description_zh=(
            "對應兩個開放 EPUB 版本的 MARCXML、MODS 3.8 與 BIBFRAME 2.0 "
            "候選書目紀錄。"
        ),
        landing_path="data/zhuyin-bopomofo-library-catalog-records.html",
        metadata_path="data/packages/zhuyin-bopomofo-library/metadata.jsonld",
        distribution_paths=(
            "data/packages/zhuyin-bopomofo-library/bopomofo-37-symbol-library-catalog-bundle.zip",
            "data/packages/zhuyin-bopomofo-library/bopomofo-37-symbol-reference.marcxml.xml",
            "data/packages/zhuyin-bopomofo-library/bopomofo-37-symbol-reference.mods.xml",
            "data/packages/zhuyin-bopomofo-library/bopomofo-37-symbol-reference.bibframe.jsonld",
            "data/packages/zhuyin-bopomofo-library/bopomofo-37-symbol-reference.bibframe.ttl",
            "data/packages/zhuyin-bopomofo-library/metadata.jsonld",
        ),
        keywords=("MARCXML", "MODS 3.8", "BIBFRAME 2.0", "library metadata"),
        conforms_to=(
            "https://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd",
            "https://www.loc.gov/standards/mods/v3/mods-3-8.xsd",
            "https://id.loc.gov/ontologies/bibframe.html",
        ),
    ),
    DatasetSpec(
        key="oer-metadata",
        title_en="Bopomofo OER repository metadata",
        title_zh="注音 OER 典藏庫 metadata",
        description_en=(
            "Standalone OAI-DC records and DCMI Terms and LRMI JSON-LD "
            "for the two exact open EPUB editions."
        ),
        description_zh=(
            "對應兩個開放 EPUB 版本的獨立 OAI-DC、DCMI Terms 與 LRMI "
            "JSON-LD metadata。"
        ),
        landing_path="data/zhuyin-bopomofo-oer-repository-metadata.html",
        metadata_path="data/packages/zhuyin-bopomofo-oer/metadata.jsonld",
        distribution_paths=(
            "data/packages/zhuyin-bopomofo-oer/bopomofo-37-symbol-oer-metadata-bundle.zip",
            "data/packages/zhuyin-bopomofo-oer/bopomofo-37-symbol-reference-en.oai-dc.xml",
            "data/packages/zhuyin-bopomofo-oer/bopomofo-37-symbol-reference-zh-hant.oai-dc.xml",
            "data/packages/zhuyin-bopomofo-oer/bopomofo-37-symbol-reference.dcmi-terms.jsonld",
            "data/packages/zhuyin-bopomofo-oer/bopomofo-37-symbol-reference.lrmi.jsonld",
            "data/packages/zhuyin-bopomofo-oer/metadata.jsonld",
        ),
        keywords=("OAI-DC", "DCMI Terms", "LRMI", "OER metadata"),
        conforms_to=(
            "https://www.openarchives.org/OAI/2.0/oai_dc.xsd",
            "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/",
            "https://www.dublincore.org/specifications/lrmi/lrmi_terms/",
        ),
    ),
)

COPY = {
    "en": {
        "lang": "en",
        "title": "DCAT 3 open-data catalog for Bopomofo resources",
        "description": (
            "Download a static W3C DCAT 3 catalog covering ten verified "
            "Bopomofo datasets and 48 exact distributions."
        ),
        "eyebrow": "W3C DCAT 3 · JSON-LD + Turtle · SHA-256",
        "lead": (
            "Open-data catalogs, libraries and research tools can harvest one "
            "machine-readable inventory for the Bopomofo data, API, vocabulary, "
            "learning packages and repository metadata."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "badges": (
            "10 catalogued datasets",
            "48 exact distributions",
            "SPDX SHA-256 fixity",
            "No account or API key",
        ),
        "download": "Download the DCAT 3 catalog",
        "download_text": (
            "Choose JSON-LD or Turtle, or download the deterministic ZIP. "
            "The package manifest records exact bytes and SHA-256 values."
        ),
        "labels": {
            BUNDLE_FILENAME: "Complete deterministic bundle",
            JSONLD_FILENAME: "DCAT 3 JSON-LD graph",
            TURTLE_FILENAME: "DCAT 3 Turtle graph",
            METADATA_FILENAME: "Package manifest and checksums",
        },
        "coverage": "What the catalog covers",
        "coverage_items": (
            (
                "Reference and linked data",
                "Core JSON, SKOS, SHACL, Croissant, CSVW, CSV, JSON Lines, "
                "Data Package 2.0 and RFC 8493 BagIt.",
            ),
            (
                "Learning and publication files",
                "Anki TSV, QTI, Moodle XML, EPUB, Readium and OPDS distributions.",
            ),
            (
                "Repository metadata",
                "MARCXML, MODS, BIBFRAME, OAI-DC, DCMI Terms and LRMI packages.",
            ),
            (
                "Static data service",
                "The versioned read-only JSON API is described as a DCAT DataService.",
            ),
        ),
        "workflow": "Harvesting workflow",
        "workflow_items": (
            "Download the JSON-LD or Turtle catalog and parse it as RDF.",
            "Read dcat:dataset and dcat:record; each record has one foaf:primaryTopic.",
            "Follow dcat:downloadURL for direct files or dcat:endpointURL for the API.",
            "Verify each distribution with its SPDX SHA-256 checksum and byte size.",
            "Map local themes and policy fields before publishing in another catalog.",
        ),
        "verification": "Validation and provenance",
        "verification_text": (
            "Both serializations describe the same RDF graph. DCAT terms are "
            "checked against a pinned unmodified W3C vocabulary, and every "
            "distribution is hashed from the published local bytes."
        ),
        "limits": "Scope and limits",
        "limits_text": (
            "This is a static DCAT 3 description, not portal registration, W3C "
            "certification, institutional endorsement or a guarantee that any "
            "external catalog has harvested it. Checksums detect byte changes but "
            "are served from the same site, so they are fixity—not independent authenticity."
        ),
        "app_title": "Optional on-device practice",
        "app_text": (
            "The catalog and all open files work without an app. If currently "
            "available, Lumi Bopomofo is an optional private practice layer."
        ),
        "app_cta": "View Lumi Bopomofo",
        "footer": (
            "CC BY 4.0 catalog metadata · Static files · No account · "
            "No claim of portal registration or W3C endorsement"
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音開放資源 DCAT 3 資料目錄",
        "description": (
            "下載靜態 W3C DCAT 3 目錄，收錄 10 組已驗證注音資料集與 48 個精確版本。"
        ),
        "eyebrow": "W3C DCAT 3 · JSON-LD＋Turtle · SHA-256",
        "lead": (
            "開放資料目錄、圖書館與研究工具可從單一 machine-readable inventory "
            "採集注音資料、API、詞彙、學習套件與典藏 metadata。"
        ),
        "back": "開放資料",
        "language": "English",
        "badges": (
            "10 組目錄資料集",
            "48 個精確版本",
            "SPDX SHA-256 fixity",
            "免帳號與 API key",
        ),
        "download": "下載 DCAT 3 資料目錄",
        "download_text": (
            "可選 JSON-LD、Turtle 或 deterministic ZIP；package manifest "
            "記錄精確 bytes 與 SHA-256。"
        ),
        "labels": {
            BUNDLE_FILENAME: "完整 deterministic bundle",
            JSONLD_FILENAME: "DCAT 3 JSON-LD graph",
            TURTLE_FILENAME: "DCAT 3 Turtle graph",
            METADATA_FILENAME: "Package manifest 與校驗資訊",
        },
        "coverage": "目錄涵蓋內容",
        "coverage_items": (
            (
                "參考資料與 linked data",
                "核心 JSON、SKOS、SHACL、Croissant、CSVW、CSV、JSON Lines、"
                "Data Package 2.0 與 RFC 8493 BagIt。",
            ),
            (
                "學習與出版檔案",
                "Anki TSV、QTI、Moodle XML、EPUB、Readium 與 OPDS distributions。",
            ),
            (
                "典藏 metadata",
                "MARCXML、MODS、BIBFRAME、OAI-DC、DCMI Terms 與 LRMI 套件。",
            ),
            (
                "靜態資料服務",
                "將版本化唯讀 JSON API 描述為 DCAT DataService。",
            ),
        ),
        "workflow": "採集流程",
        "workflow_items": (
            "下載 JSON-LD 或 Turtle 目錄並解析為 RDF。",
            "讀取 dcat:dataset 與 dcat:record；每筆 record 僅有一個 foaf:primaryTopic。",
            "直接檔案使用 dcat:downloadURL，API 使用 dcat:endpointURL。",
            "以 SPDX SHA-256 與 byte size 驗證每個 distribution。",
            "匯入其他目錄前，先對應當地 theme 與政策欄位。",
        ),
        "verification": "驗證與 provenance",
        "verification_text": (
            "兩種 serialization 描述相同 RDF graph；DCAT terms 對照固定的未修改 "
            "W3C vocabulary，且每個 distribution 都從已發布本機 bytes 計算 hash。"
        ),
        "limits": "範圍與限制",
        "limits_text": (
            "這是靜態 DCAT 3 描述，不代表已登錄外部 portal、取得 W3C 認證、"
            "機構背書或保證被任何外部目錄採集。Checksum 與檔案位於同一網站，"
            "可驗證 fixity，但不是獨立 authenticity 證明。"
        ),
        "app_title": "選用的裝置端練習",
        "app_text": (
            "資料目錄與開放檔案皆不需要 App；若目前仍公開，Lumi Bopomofo "
            "僅是選用的隱私練習層。"
        ),
        "app_cta": "查看 Lumi Bopomofo",
        "footer": (
            "CC BY 4.0 目錄 metadata · 靜態檔案 · 免帳號 · "
            "不宣稱 portal 登錄或 W3C 背書"
        ),
    },
}


def _iri(value: str) -> Iri:
    return Iri(value)


def _lit(
    value: str,
    language: str | None = None,
    datatype: str | None = None,
) -> Literal:
    return Literal(value, language, datatype)


def _date_literal(value: str) -> Literal:
    datatype = f"{XSD}date" if len(value) == 10 else f"{XSD}dateTime"
    return _lit(value, datatype=datatype)


def _add(
    triples: list[tuple[str, str, Iri | Literal]],
    subject: str,
    predicate: str,
    *objects: Iri | Literal,
) -> None:
    triples.extend((subject, predicate, item) for item in objects)


def _timestamp(value: str) -> dt.datetime:
    normalized = value if "T" in value else f"{value}T00:00:00Z"
    parsed = dt.datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _timestamp_text(value: str) -> str:
    return _timestamp(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_values(value, keys: tuple[str, ...]) -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                if isinstance(item, str):
                    found.append(item)
                elif isinstance(item, dict) and isinstance(item.get("@value"), str):
                    found.append(item["@value"])
            found.extend(_extract_values(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(_extract_values(item, keys))
    return found


def _source_dates(path: Path) -> tuple[str, str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read source metadata dates: {path}") from exc
    issued = _extract_values(
        document,
        ("datePublished", "dcterms:created", "dcterms:issued", "created"),
    )
    modified = _extract_values(
        document,
        ("dateModified", "dcterms:modified", "modified"),
    )
    issued_value = issued[0] if issued else INITIAL_DATE
    modified_value = max(modified or issued or [INITIAL_DATE], key=_timestamp)
    _timestamp(issued_value)
    _timestamp(modified_value)
    return issued_value, modified_value


def _media_type(relative_path: str) -> str:
    name = Path(relative_path).name.lower()
    if name.endswith(".csv-metadata.json"):
        return "application/csvm+json"
    if name.endswith(".croissant.jsonld") or name.endswith(".jsonld"):
        return "application/ld+json"
    if name.endswith(".shacl.ttl") or name.endswith(".ttl"):
        return "text/turtle"
    if name.endswith(".nt"):
        return "application/n-triples"
    if name.endswith(".jsonl"):
        return "text/plain"
    if name.endswith(".schema.json") or name == "table-schema.json":
        return "application/json"
    if name.endswith(".json"):
        if "openapi" in name:
            return "application/vnd.oai.openapi+json;version=3.1"
        return "application/json"
    if name.endswith(".marcxml.xml"):
        return "application/marcxml+xml"
    if name.endswith(".mods.xml"):
        return "application/mods+xml"
    if name == "bopomofo-37-symbol-reference.xml":
        return "application/atom+xml"
    if name.endswith(".xml"):
        return "application/xml"
    if name.endswith(".epub"):
        return "application/epub+zip"
    if name.endswith(".zip"):
        return "application/zip"
    if name.endswith(".csv"):
        return "text/csv"
    if name.endswith(".tsv"):
        return "text/tab-separated-values"
    if name.endswith(".txt"):
        return "text/plain"
    raise ValueError(f"Unknown DCAT distribution media type: {relative_path}")


def _media_type_iri(media_type: str) -> str:
    base = media_type.split(";", 1)[0]
    return f"https://www.iana.org/assignments/media-types/{base}"


def _artifact_languages(relative_path: str) -> tuple[str, ...]:
    lowered = relative_path.lower()
    if "zh-hant" in lowered:
        return (LANG_ZH,)
    if re.search(r"(^|[-/])en([./-]|$)", lowered):
        return (LANG_EN,)
    return (LANG_EN, LANG_ZH)


def load_datasets(pages: Path) -> tuple[Dataset, ...]:
    datasets = []
    seen_paths = set()
    for spec in DATASETS:
        issued, modified = _source_dates(pages / spec.metadata_path)
        artifacts = []
        for relative in spec.distribution_paths:
            if relative in seen_paths:
                raise ValueError(f"Duplicate DCAT distribution path: {relative}")
            seen_paths.add(relative)
            path = pages / relative
            if not path.exists():
                raise FileNotFoundError(
                    f"Build the source resource before DCAT: {path}"
                )
            content = path.read_bytes()
            if not content:
                raise ValueError(f"DCAT distribution is empty: {path}")
            artifacts.append(
                Artifact(
                    relative_path=relative,
                    url=f"{SITE}/{relative}",
                    media_type=_media_type(relative),
                    size=len(content),
                    sha256=_sha256(content),
                    languages=_artifact_languages(relative),
                )
            )
        datasets.append(
            Dataset(
                spec=spec,
                identifier=f"{LANDING_URL}#dataset-{spec.key}",
                record_identifier=f"{LANDING_URL}#record-{spec.key}",
                issued=issued,
                modified=modified,
                artifacts=tuple(artifacts),
            )
        )
    return tuple(datasets)


def render_triples(
    datasets: tuple[Dataset, ...],
    catalog_modified: str,
) -> list[tuple[str, str, Iri | Literal]]:
    triples: list[tuple[str, str, Iri | Literal]] = []
    themes = {
        "language": ("Language data", "語言資料"),
        "education": ("Educational resources", "教育資源"),
        "metadata": ("Metadata and catalogs", "Metadata 與目錄"),
    }

    _add(triples, CREATOR_URL, f"{RDF}type", _iri(f"{FOAF}Organization"))
    _add(
        triples,
        CREATOR_URL,
        f"{FOAF}name",
        _lit(CREATOR, "en"),
        _lit("Lumi Apps iOS 應用指南", "zh-Hant"),
    )
    _add(triples, CREATOR_URL, f"{FOAF}homepage", _iri(SITE))

    _add(triples, THEME_SCHEME, f"{RDF}type", _iri(f"{SKOS}ConceptScheme"))
    _add(
        triples,
        THEME_SCHEME,
        f"{SKOS}prefLabel",
        _lit("Bopomofo open-resource themes", "en"),
        _lit("注音開放資源主題", "zh-Hant"),
    )
    for key, labels in themes.items():
        theme = f"{LANDING_URL}#theme-{key}"
        _add(triples, theme, f"{RDF}type", _iri(f"{SKOS}Concept"))
        _add(
            triples,
            theme,
            f"{SKOS}prefLabel",
            _lit(labels[0], "en"),
            _lit(labels[1], "zh-Hant"),
        )
        _add(triples, theme, f"{SKOS}inScheme", _iri(THEME_SCHEME))

    _add(triples, CATALOG_ID, f"{RDF}type", _iri(f"{DCAT}Catalog"))
    _add(
        triples,
        CATALOG_ID,
        f"{DCTERMS}title",
        _lit("Bopomofo open-data catalog", "en"),
        _lit("注音開放資料目錄", "zh-Hant"),
    )
    _add(
        triples,
        CATALOG_ID,
        f"{DCTERMS}description",
        _lit(COPY["en"]["description"], "en"),
        _lit(COPY["zh-Hant"]["description"], "zh-Hant"),
    )
    _add(triples, CATALOG_ID, f"{DCTERMS}publisher", _iri(CREATOR_URL))
    _add(triples, CATALOG_ID, f"{DCTERMS}issued", _date_literal(INITIAL_DATE))
    _add(
        triples,
        CATALOG_ID,
        f"{DCTERMS}modified",
        _date_literal(catalog_modified),
    )
    _add(
        triples,
        CATALOG_ID,
        f"{DCTERMS}language",
        _iri(LANG_EN),
        _iri(LANG_ZH),
    )
    _add(triples, CATALOG_ID, f"{DCTERMS}license", _iri(LICENSE))
    _add(triples, CATALOG_ID, f"{DCTERMS}conformsTo", _iri(DCAT_SPEC))
    _add(triples, CATALOG_ID, f"{DCAT}version", _lit(VERSION))
    _add(triples, CATALOG_ID, f"{FOAF}homepage", _iri(LANDING_URL))
    _add(triples, CATALOG_ID, f"{DCAT}themeTaxonomy", _iri(THEME_SCHEME))
    _add(triples, CATALOG_ID, f"{DCAT}service", _iri(API_SERVICE))

    for dataset in datasets:
        spec = dataset.spec
        _add(triples, CATALOG_ID, f"{DCAT}dataset", _iri(dataset.identifier))
        _add(
            triples,
            CATALOG_ID,
            f"{DCAT}record",
            _iri(dataset.record_identifier),
        )

        _add(
            triples,
            dataset.record_identifier,
            f"{RDF}type",
            _iri(f"{DCAT}CatalogRecord"),
        )
        _add(
            triples,
            dataset.record_identifier,
            f"{DCTERMS}title",
            _lit(f"Catalog entry for {spec.title_en}", "en"),
            _lit(f"{spec.title_zh}目錄紀錄", "zh-Hant"),
        )
        _add(
            triples,
            dataset.record_identifier,
            f"{DCTERMS}issued",
            _date_literal(INITIAL_DATE),
        )
        _add(
            triples,
            dataset.record_identifier,
            f"{DCTERMS}modified",
            _date_literal(catalog_modified),
        )
        _add(
            triples,
            dataset.record_identifier,
            f"{DCTERMS}conformsTo",
            _iri(DCAT_SPEC),
        )
        _add(
            triples,
            dataset.record_identifier,
            f"{FOAF}primaryTopic",
            _iri(dataset.identifier),
        )

        _add(
            triples,
            dataset.identifier,
            f"{RDF}type",
            _iri(f"{DCAT}Dataset"),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}title",
            _lit(spec.title_en, "en"),
            _lit(spec.title_zh, "zh-Hant"),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}description",
            _lit(spec.description_en, "en"),
            _lit(spec.description_zh, "zh-Hant"),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}identifier",
            _lit(f"LUMI-ZHUYIN-DCAT-{spec.key.upper()}"),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}issued",
            _date_literal(dataset.issued),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}modified",
            _date_literal(dataset.modified),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}publisher",
            _iri(CREATOR_URL),
        )
        _add(
            triples,
            dataset.identifier,
            f"{DCTERMS}language",
            _iri(LANG_EN),
            _iri(LANG_ZH),
        )
        _add(triples, dataset.identifier, f"{DCTERMS}license", _iri(LICENSE))
        _add(
            triples,
            dataset.identifier,
            f"{DCAT}landingPage",
            _iri(f"{SITE}/{spec.landing_path}"),
        )
        for standard in spec.conforms_to:
            _add(
                triples,
                dataset.identifier,
                f"{DCTERMS}conformsTo",
                _iri(standard),
            )
        for keyword in spec.keywords:
            _add(
                triples,
                dataset.identifier,
                f"{DCAT}keyword",
                _lit(keyword, "en"),
            )
        for key in themes:
            _add(
                triples,
                dataset.identifier,
                f"{DCAT}theme",
                _iri(f"{LANDING_URL}#theme-{key}"),
            )

        for index, artifact in enumerate(dataset.artifacts, 1):
            distribution = (
                f"{LANDING_URL}#distribution-{spec.key}-{index}"
            )
            checksum = f"{distribution}-sha256"
            _add(
                triples,
                dataset.identifier,
                f"{DCAT}distribution",
                _iri(distribution),
            )
            _add(
                triples,
                distribution,
                f"{RDF}type",
                _iri(f"{DCAT}Distribution"),
            )
            _add(
                triples,
                distribution,
                f"{DCTERMS}title",
                _lit(Path(artifact.relative_path).name),
            )
            _add(triples, distribution, f"{DCTERMS}license", _iri(LICENSE))
            _add(triples, distribution, f"{DCAT}accessURL", _iri(artifact.url))
            _add(
                triples,
                distribution,
                f"{DCAT}downloadURL",
                _iri(artifact.url),
            )
            _add(
                triples,
                distribution,
                f"{DCAT}mediaType",
                _iri(_media_type_iri(artifact.media_type)),
            )
            _add(
                triples,
                distribution,
                f"{DCAT}byteSize",
                _lit(str(artifact.size), datatype=f"{XSD}nonNegativeInteger"),
            )
            for language in artifact.languages:
                _add(
                    triples,
                    distribution,
                    f"{DCTERMS}language",
                    _iri(language),
                )
            if artifact.media_type == "application/zip":
                _add(
                    triples,
                    distribution,
                    f"{DCAT}packageFormat",
                    _iri(_media_type_iri("application/zip")),
                )
            if spec.has_api_service and artifact.url == API_INDEX:
                _add(
                    triples,
                    distribution,
                    f"{DCAT}accessService",
                    _iri(API_SERVICE),
                )
            _add(triples, distribution, f"{SPDX}checksum", _iri(checksum))
            _add(
                triples,
                checksum,
                f"{RDF}type",
                _iri(f"{SPDX}Checksum"),
            )
            _add(
                triples,
                checksum,
                f"{SPDX}algorithm",
                _iri(f"{SPDX}checksumAlgorithm_sha256"),
            )
            _add(
                triples,
                checksum,
                f"{SPDX}checksumValue",
                _lit(artifact.sha256, datatype=f"{XSD}hexBinary"),
            )

    core_dataset = next(
        dataset.identifier
        for dataset in datasets
        if dataset.spec.key == "symbols"
    )
    _add(triples, API_SERVICE, f"{RDF}type", _iri(f"{DCAT}DataService"))
    _add(
        triples,
        API_SERVICE,
        f"{DCTERMS}title",
        _lit("Bopomofo symbols static JSON API", "en"),
        _lit("注音符號靜態 JSON API", "zh-Hant"),
    )
    _add(
        triples,
        API_SERVICE,
        f"{DCTERMS}description",
        _lit(
            "Versioned read-only JSON endpoints for all 37 Bopomofo symbols.",
            "en",
        ),
        _lit("完整 37 個注音符號的版本化唯讀 JSON endpoints。", "zh-Hant"),
    )
    _add(triples, API_SERVICE, f"{DCTERMS}license", _iri(LICENSE))
    _add(triples, API_SERVICE, f"{DCTERMS}conformsTo", _iri(OPENAPI_SPEC))
    _add(triples, API_SERVICE, f"{DCAT}endpointURL", _iri(API_INDEX))
    _add(
        triples,
        API_SERVICE,
        f"{DCAT}endpointDescription",
        _iri(API_OPENAPI),
    )
    _add(triples, API_SERVICE, f"{DCAT}landingPage", _iri(API_LANDING))
    _add(
        triples,
        API_SERVICE,
        f"{DCAT}servesDataset",
        _iri(core_dataset),
    )
    return triples


def _compact(value: str) -> str:
    for prefix, namespace in PREFIXES.items():
        if value.startswith(namespace):
            return f"{prefix}:{value[len(namespace):]}"
    return value


def render_jsonld(
    triples: list[tuple[str, str, Iri | Literal]],
) -> bytes:
    nodes: dict[str, dict[str, list]] = {}
    for subject, predicate, value in triples:
        node = nodes.setdefault(subject, {"@id": subject})
        key = "@type" if predicate == f"{RDF}type" else _compact(predicate)
        if isinstance(value, Iri):
            rendered = (
                _compact(value.value)
                if key == "@type"
                else {"@id": value.value}
            )
        else:
            rendered = {"@value": value.value}
            if value.language:
                rendered["@language"] = value.language
            if value.datatype:
                rendered["@type"] = _compact(value.datatype)
        node.setdefault(key, []).append(rendered)
    graph = []
    for node in nodes.values():
        normalized = {}
        for key, value in node.items():
            if key == "@id":
                normalized[key] = value
            else:
                normalized[key] = value[0] if len(value) == 1 else value
        graph.append(normalized)
    document = {
        "@context": PREFIXES,
        "@graph": graph,
    }
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _turtle_iri(value: str) -> str:
    compact = _compact(value)
    return compact if compact != value else f"<{value}>"


def _turtle_literal(value: Literal) -> str:
    rendered = json.dumps(value.value, ensure_ascii=False)
    if value.language:
        return f"{rendered}@{value.language}"
    if value.datatype:
        return f"{rendered}^^{_turtle_iri(value.datatype)}"
    return rendered


def render_turtle(
    triples: list[tuple[str, str, Iri | Literal]],
) -> bytes:
    grouped: dict[str, dict[str, list[Iri | Literal]]] = {}
    for subject, predicate, value in triples:
        grouped.setdefault(subject, {}).setdefault(predicate, []).append(value)
    lines = [
        *[
            f"@prefix {prefix}: <{namespace}> ."
            for prefix, namespace in PREFIXES.items()
        ],
        "",
    ]
    for subject, predicates in grouped.items():
        lines.append(f"<{subject}>")
        items = list(predicates.items())
        for index, (predicate, values) in enumerate(items):
            predicate_text = "a" if predicate == f"{RDF}type" else _turtle_iri(
                predicate
            )
            rendered_values = []
            for value in values:
                rendered_values.append(
                    _turtle_iri(value.value)
                    if isinstance(value, Iri)
                    else _turtle_literal(value)
                )
            ending = " ." if index == len(items) - 1 else " ;"
            lines.append(
                f"  {predicate_text} " + ",\n    ".join(rendered_values) + ending
            )
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _artifact(filename: str, content: bytes) -> dict:
    return {
        "filename": filename,
        "label": FORMATS[filename][0],
        "encodingFormat": FORMATS[filename][1],
        "url": f"{PACKAGE_URL}/{filename}",
        "size": len(content),
        "sha256": _sha256(content),
    }


def render_bundle(
    primary: dict[str, bytes],
    datasets: tuple[Dataset, ...],
    modified: str,
) -> bytes:
    checksums = "".join(
        f"{_sha256(primary[filename])}  {filename}\n"
        for filename in sorted(primary)
    )
    distribution_count = sum(len(dataset.artifacts) for dataset in datasets)
    readme = f"""Bopomofo DCAT 3 open-data catalog
====================================

This deterministic bundle describes {len(datasets)} Bopomofo datasets and
{distribution_count} exact published distributions as one static DCAT 3 graph.

Files
-----
- {JSONLD_FILENAME}: DCAT 3 graph in JSON-LD
- {TURTLE_FILENAME}: equivalent DCAT 3 graph in Turtle
- checksums.sha256: SHA-256 for both catalog serializations

Validation and scope
--------------------
- Both RDF serializations must parse to the same graph.
- DCAT terms are checked against a pinned unmodified W3C vocabulary.
- Every distribution records direct URL, IANA media-type IRI, byte size,
  CC BY 4.0 license and SPDX SHA-256 checksum.
- This is a static catalog description, not portal registration, W3C
  certification, institutional endorsement or proof of external harvesting.
- Checksums share the same host as the files and therefore provide fixity,
  not an independently protected authenticity channel.

DCAT 3 Recommendation: {DCAT_SPEC}
SPDX RDF terms: {SPDX_TERMS}
Catalog modified: {modified}
License: {LICENSE}
"""
    entries = {
        **primary,
        "README.txt": readme.encode("utf-8"),
        "checksums.sha256": checksums.encode("ascii"),
    }
    stamp = _timestamp(modified)
    zip_date = (
        max(1980, stamp.year),
        stamp.month,
        stamp.day,
        stamp.hour,
        stamp.minute,
        stamp.second,
    )
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for filename in sorted(entries):
            info = zipfile.ZipInfo(filename, zip_date)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entries[filename])
    return output.getvalue()


def _schema_context() -> dict:
    return {
        "@vocab": "https://schema.org/",
        "url": {
            "@id": "https://schema.org/url",
            "@type": "@id",
        },
        "license": {
            "@id": "https://schema.org/license",
            "@type": "@id",
        },
        "contentUrl": {
            "@id": "https://schema.org/contentUrl",
            "@type": "@id",
        },
        "conformsTo": {
            "@id": "https://schema.org/conformsTo",
            "@type": "@id",
        },
    }


def render_metadata(
    datasets: tuple[Dataset, ...],
    artifacts: list[dict],
    modified: str,
) -> bytes:
    metadata = {
        "@context": _schema_context(),
        "@type": "DataCatalog",
        "@id": CATALOG_ID,
        "name": "Bopomofo DCAT 3 open-data catalog",
        "alternateName": "注音 DCAT 3 開放資料目錄",
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "identifier": "LUMI-ZHUYIN-DCAT3-2026",
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "inLanguage": ["en", "zh-Hant"],
        "license": LICENSE,
        "isAccessibleForFree": True,
        "creator": {
            "@type": "Organization",
            "@id": CREATOR_URL,
            "name": CREATOR,
            "url": SITE,
        },
        "conformsTo": DCAT_SPEC,
        "numberOfItems": len(datasets),
        "dataset": [
            {
                "@type": "Dataset",
                "@id": dataset.identifier,
                "name": dataset.spec.title_en,
                "url": f"{SITE}/{dataset.spec.landing_path}",
                "dateModified": dataset.modified,
            }
            for dataset in datasets
        ],
        "distribution": [
            {
                "@type": "DataDownload",
                "name": item["label"],
                "encodingFormat": item["encodingFormat"],
                "contentUrl": item["url"],
                "contentSize": f"{item['size']} bytes",
                "sha256": item["sha256"],
            }
            for item in artifacts
        ],
    }
    return (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def render_package(
    datasets: tuple[Dataset, ...],
    modified: str,
) -> dict[str, bytes]:
    triples = render_triples(datasets, modified)
    primary = {
        JSONLD_FILENAME: render_jsonld(triples),
        TURTLE_FILENAME: render_turtle(triples),
    }
    bundle = render_bundle(primary, datasets, modified)
    artifacts = [
        _artifact(BUNDLE_FILENAME, bundle),
        *[_artifact(filename, primary[filename]) for filename in PRIMARY_FILENAMES],
    ]
    metadata = render_metadata(datasets, artifacts, modified)
    return {
        **primary,
        BUNDLE_FILENAME: bundle,
        METADATA_FILENAME: metadata,
    }


def _prior_modified(pages: Path) -> str | None:
    path = pages / PACKAGE_PATH / METADATA_FILENAME
    if not path.exists():
        return None
    try:
        modified = json.loads(path.read_text(encoding="utf-8"))["dateModified"]
        _timestamp(modified)
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None
    return modified


def _package_matches(pages: Path, package: dict[str, bytes]) -> bool:
    package_dir = pages / PACKAGE_PATH
    return all(
        (package_dir / filename).exists()
        and (package_dir / filename).read_bytes() == content
        for filename, content in package.items()
    )


def validate_raw_package(
    package: dict[str, bytes],
    datasets: tuple[Dataset, ...],
) -> None:
    raw = b"\n".join(package.values())
    for forbidden in (
        b"apps.apple.com",
        APP_ID.encode("ascii"),
        APP_NAME.encode("utf-8"),
        b"SoftwareApplication",
    ):
        if forbidden in raw:
            raise ValueError(
                "Raw DCAT package must remain app-independent: "
                f"{forbidden!r}"
            )
    expected_paths = {
        artifact.relative_path
        for dataset in datasets
        for artifact in dataset.artifacts
    }
    if len(expected_paths) != sum(len(item.artifacts) for item in datasets):
        raise ValueError("DCAT source distribution paths must be unique")
    document = json.loads(package[JSONLD_FILENAME])
    if document.get("@context") != PREFIXES or not document.get("@graph"):
        raise ValueError("DCAT JSON-LD must contain its inline context and graph")
    turtle = package[TURTLE_FILENAME]
    for required in (
        b"dcat:Catalog",
        b"dcat:CatalogRecord",
        b"dcat:Dataset",
        b"dcat:Distribution",
        b"dcat:DataService",
        b"spdx:checksumAlgorithm_sha256",
    ):
        if required not in turtle:
            raise ValueError(f"DCAT Turtle is missing {required!r}")
    with zipfile.ZipFile(io.BytesIO(package[BUNDLE_FILENAME])) as archive:
        expected = {*PRIMARY_FILENAMES, "README.txt", "checksums.sha256"}
        if set(archive.namelist()) != expected:
            raise ValueError("DCAT ZIP does not contain the expected files")
        checksum_lines = archive.read("checksums.sha256").decode("ascii").splitlines()
        checksums = {
            filename: checksum
            for checksum, filename in (line.split("  ", 1) for line in checksum_lines)
        }
        for filename in PRIMARY_FILENAMES:
            content = archive.read(filename)
            if content != package[filename]:
                raise ValueError(f"DCAT ZIP mismatch: {filename}")
            if checksums.get(filename) != _sha256(content):
                raise ValueError(f"DCAT ZIP checksum mismatch: {filename}")


def _page_schema(
    locale: str,
    package_info: dict[str, dict],
    package_modified: str,
    page_modified: str,
    app_public: bool,
) -> dict:
    copy = COPY[locale]
    canonical = LANDING_URL if locale == "en" else ZH_LANDING_URL
    graph = [
        {
            "@type": "WebPage",
            "@id": canonical,
            "name": copy["title"],
            "description": copy["description"],
            "url": canonical,
            "inLanguage": copy["lang"],
            "dateModified": page_modified,
            "mainEntity": {"@id": CATALOG_ID},
        },
        {
            "@type": "DataCatalog",
            "@id": CATALOG_ID,
            "name": "Bopomofo DCAT 3 open-data catalog",
            "alternateName": "注音 DCAT 3 開放資料目錄",
            "description": copy["description"],
            "url": LANDING_URL,
            "version": VERSION,
            "datePublished": INITIAL_DATE,
            "dateModified": package_modified,
            "inLanguage": ["en", "zh-Hant"],
            "license": LICENSE,
            "isAccessibleForFree": True,
            "conformsTo": DCAT_SPEC,
            "numberOfItems": len(DATASETS),
            "distribution": [
                {
                    "@type": "DataDownload",
                    "name": FORMATS[filename][0],
                    "encodingFormat": FORMATS[filename][1],
                    "contentUrl": package_info[filename]["url"],
                    "contentSize": f"{package_info[filename]['size']} bytes",
                    "sha256": package_info[filename]["sha256"],
                }
                for filename in DOWNLOAD_FILENAMES
            ],
        },
    ]
    if app_public:
        graph[1]["subjectOf"] = {
            "@type": "SoftwareApplication",
            "name": APP_NAME,
            "applicationCategory": "EducationApplication",
            "operatingSystem": "iOS",
            "url": appstore_url(
                APP_KEY,
                f"iag_bopomofo_dcat3_{locale.lower()}",
            ),
        }
    return {"@context": _schema_context(), "@graph": graph}


def render_landing(
    locale: str,
    package_info: dict[str, dict],
    package_modified: str,
    page_modified: str,
    app_public: bool,
) -> str:
    copy = COPY[locale]
    canonical = LANDING_URL if locale == "en" else ZH_LANDING_URL
    other = ZH_LANDING_URL if locale == "en" else LANDING_URL
    badges = "".join(f"<span>{html.escape(item)}</span>" for item in copy["badges"])
    downloads = []
    for filename in DOWNLOAD_FILENAMES:
        info = package_info[filename]
        css = "download primary" if filename == BUNDLE_FILENAME else "download"
        downloads.append(
            f'<a class="{css}" href="{html.escape(info["url"], quote=True)}">'
            f"<strong>{html.escape(copy['labels'][filename])}</strong>"
            f"<span>{html.escape(filename)}</span>"
            f"<small>{info['size']:,} bytes · SHA-256 "
            f"{html.escape(info['sha256'][:16])}…</small></a>"
        )
    coverage = "".join(
        f"<article><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></article>"
        for title, text in copy["coverage_items"]
    )
    workflow = "".join(
        f"<li><span>{index}</span>{html.escape(item)}</li>"
        for index, item in enumerate(copy["workflow_items"], 1)
    )
    app_block = ""
    if app_public:
        app_url = appstore_url(
            APP_KEY,
            f"iag_bopomofo_dcat3_{locale.lower()}",
        )
        app_block = (
            f'<section class="app"><h2>{html.escape(copy["app_title"])}</h2>'
            f'<p>{html.escape(copy["app_text"])}</p>'
            f'<a href="{html.escape(app_url, quote=True)}">'
            f'{html.escape(copy["app_cta"])} &rarr;</a></section>'
        )
    schema = json.dumps(
        _page_schema(
            locale,
            package_info,
            package_modified,
            page_modified,
            app_public,
        ),
        ensure_ascii=False,
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{copy['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{page_modified}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{LANDING_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_LANDING_URL}">
<link rel="alternate" hreflang="x-default" href="{LANDING_URL}">
<link rel="describedby" type="application/ld+json" href="{PACKAGE_URL}/{JSONLD_FILENAME}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#12233f;--sub:#5b687c;--line:#d8e2ef;--brand:#315f9d;--deep:#132f55;--bg:#f1f5fa;--paper:#fff;--soft:#e8f1fb;--gold:#ad771f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}.wrap{{max-width:1060px;margin:auto;padding:24px 20px 74px}}a{{color:var(--brand)}}.top{{display:flex;justify-content:space-between;gap:16px;font-size:14px}}.top a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding:58px 0 32px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(33px,7vw,59px);line-height:1.06;letter-spacing:-.039em;margin:10px 0 17px;max-width:930px}}h2{{font-size:clamp(23px,4vw,32px);line-height:1.2;margin:0 0 10px}}h3{{font-size:18px;margin:0 0 7px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:870px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:730;white-space:nowrap}}section{{margin-top:34px}}.panel,.app{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(19px,4vw,29px);box-shadow:0 14px 35px rgba(26,49,82,.055)}}.downloads,.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:12px;margin-top:18px}}.download{{display:flex;min-width:0;flex-direction:column;gap:4px;border:1px solid var(--line);border-radius:15px;padding:16px;background:#fbfcfe;text-decoration:none;color:var(--ink)}}.download.primary{{grid-column:1/-1;background:var(--deep);border-color:var(--deep);color:#fff}}.download strong{{font-size:17px}}.download span,.download small{{overflow-wrap:anywhere;color:var(--sub)}}.download.primary span,.download.primary small{{color:#dbe8fa}}.grid article{{background:#fff;border:1px solid var(--line);border-radius:17px;padding:19px}}.grid p{{margin:0}}.steps{{list-style:none;padding:0;margin:18px 0 0;display:grid;gap:10px}}.steps li{{display:flex;align-items:flex-start;gap:12px;color:var(--sub)}}.steps span{{display:grid;place-items:center;flex:0 0 28px;height:28px;border-radius:50%;background:var(--deep);color:#fff;font-weight:850;font-size:13px}}.verified{{border-top:4px solid var(--brand)}}.notice{{border-left:4px solid var(--gold)}}.app a{{font-weight:820;text-decoration:none;white-space:nowrap}}footer{{margin-top:42px;padding-top:21px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}}@media(max-width:520px){{.wrap{{padding-left:16px;padding-right:16px}}.panel,.app{{border-radius:18px}}}}
</style>
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{SITE}/data/">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(other, quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></header>
<section class="panel"><h2>{html.escape(copy['download'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{''.join(downloads)}</div></section>
<section><h2>{html.escape(copy['coverage'])}</h2><div class="grid">{coverage}</div></section>
<section class="panel"><h2>{html.escape(copy['workflow'])}</h2><ol class="steps">{workflow}</ol></section>
<section class="panel verified"><h2>{html.escape(copy['verification'])}</h2><p>{html.escape(copy['verification_text'])}</p><p><a href="{DCAT_SPEC}" rel="noopener">W3C DCAT 3 Recommendation &rarr;</a> · <a href="{SPDX_TERMS}" rel="noopener">SPDX RDF Terms &rarr;</a> · <a href="{LICENSE}" rel="license noopener">CC BY 4.0 &rarr;</a></p></section>
<section class="panel notice"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limits_text'])}</p></section>
{app_block}
<footer>{html.escape(copy['footer'])}</footer>
</main>
</body>
</html>
"""


def _update_data_index(
    pages: Path,
    package_info: dict[str, dict],
    modified: str,
) -> None:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index is missing: {index}")
    content = index.read_text(encoding="utf-8")
    block = (
        f'{CARD_START}<a class="item" href="{LANDING_URL}"><div>'
        '<span class="tag">W3C DCAT 3 · JSON-LD · Turtle</span>'
        "<h2>Bopomofo open-data catalog</h2>"
        "<p>Ten datasets and 48 exact distributions with SPDX SHA-256 "
        "fixity and bilingual metadata.</p></div>"
        f'<span class="arrow">&rarr;</span></a>{CARD_END}'
    )
    if CARD_START in content and CARD_END in content:
        updated = re.sub(
            re.escape(CARD_START) + r".*?" + re.escape(CARD_END),
            block,
            content,
            flags=re.DOTALL,
        )
    else:
        marker = '<p class="foot">'
        if marker not in content:
            raise RuntimeError("data/index.html is missing its footer marker")
        updated = content.replace(marker, block + marker, 1)

    schema_pattern = re.compile(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        re.DOTALL,
    )
    match = schema_pattern.search(updated)
    if match:
        try:
            catalog = json.loads(match.group(2))
        except json.JSONDecodeError:
            catalog = None
        if isinstance(catalog, dict) and catalog.get("@type") == "DataCatalog":
            datasets = [
                dataset
                for dataset in catalog.get("dataset", [])
                if dataset.get("url") != LANDING_URL
            ]
            datasets.append(
                {
                    "@type": "DataCatalog",
                    "name": "Bopomofo DCAT 3 open-data catalog",
                    "description": COPY["en"]["description"],
                    "url": LANDING_URL,
                    "dateModified": modified,
                    "license": LICENSE,
                    "conformsTo": DCAT_SPEC,
                    "distribution": [
                        {
                            "@type": "DataDownload",
                            "name": FORMATS[filename][0],
                            "encodingFormat": FORMATS[filename][1],
                            "contentUrl": package_info[filename]["url"],
                        }
                        for filename in (
                            BUNDLE_FILENAME,
                            *PRIMARY_FILENAMES,
                        )
                    ],
                }
            )
            catalog["dataset"] = datasets
            rendered = json.dumps(catalog, ensure_ascii=False)
            updated = (
                updated[: match.start()]
                + match.group(1)
                + rendered
                + match.group(3)
                + updated[match.end() :]
            )
    write_text_if_changed(index, updated)


def render_sitemap(
    package_info: dict[str, dict],
    package_modified: str,
    page_modified: dict[str, str],
) -> str:
    entries = [
        (LANDING_URL, page_modified["en"]),
        (ZH_LANDING_URL, page_modified["zh-Hant"]),
        *[
            (package_info[filename]["url"], package_modified[:10])
            for filename in DOWNLOAD_FILENAMES
        ],
    ]
    rows = "\n".join(
        f"  <url><loc>{xml_escape(url)}</loc><lastmod>{modified}</lastmod></url>"
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
    datasets = load_datasets(pages)
    source_modified = max(
        (_timestamp_text(dataset.modified) for dataset in datasets),
        key=_timestamp,
    )
    prior = _prior_modified(pages)
    base_modified = (
        max(prior, source_modified, key=_timestamp)
        if prior
        else source_modified
    )
    package = render_package(datasets, base_modified)
    if prior and not _package_matches(pages, package):
        target_modified = (
            source_modified
            if _timestamp(source_modified) > _timestamp(prior)
            else _next_timestamp(prior)
        )
        package = render_package(datasets, target_modified)
    else:
        target_modified = base_modified
    validate_raw_package(package, datasets)

    package_dir = pages / PACKAGE_PATH
    for filename, content in package.items():
        _write_bytes_if_changed(package_dir / filename, content)
    package_info = {
        filename: _artifact(filename, content)
        for filename, content in package.items()
    }

    live = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", pages / LANDING_PATH),
        ("zh-Hant", pages / ZH_LANDING_PATH),
    ):
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_landing(
                locale,
                package_info,
                target_modified,
                modified,
                live,
            ),
            INITIAL_DATE,
            TODAY,
        )
    _update_data_index(pages, package_info, target_modified)
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(package_info, target_modified, page_modified),
    )
    return [
        *(str(PACKAGE_PATH / filename) for filename in DOWNLOAD_FILENAMES),
        str(LANDING_PATH),
        str(ZH_LANDING_PATH),
        str(SITEMAP_PATH),
    ]


if __name__ == "__main__":
    built = build()
    print(f"Built {len(built)} DCAT 3 catalog resources")
