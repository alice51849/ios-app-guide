#!/usr/bin/env python3
"""Publish repository-ready DCMI and LRMI metadata for the open Zhuyin EPUB."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from family_travel_dataset import render_versioned_page, write_text_if_changed
from videogen.registry import appstore_url
from zhuyin_croissant_dataset import APP_ID, APP_KEY, APP_NAME, LICENSE, SITE
from zhuyin_epub_opds import (
    EPUB_A11Y_SPEC,
    EPUB_SPEC,
    LANDING_URL as EPUB_LANDING_URL,
    METADATA_FILENAME as EPUB_METADATA_FILENAME,
    PACKAGE_PATH as EPUB_PACKAGE_PATH,
    is_app_public,
)
from zhuyin_library_catalog import (
    EDITIONS,
    _load_source as load_epub_source,
    _max_timestamp,
    _next_timestamp,
    _parse_timestamp,
    _sha256,
    _write_bytes_if_changed,
)


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
VERSION = "1.0.0"
SLUG = "zhuyin-bopomofo-oer-repository-metadata"
PACKAGE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-oer"
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}"
LANDING_PATH = Path("data") / f"{SLUG}.html"
ZH_LANDING_PATH = Path("zh-Hant") / LANDING_PATH
LANDING_URL = f"{SITE}/{LANDING_PATH.as_posix()}"
ZH_LANDING_URL = f"{SITE}/{ZH_LANDING_PATH.as_posix()}"
SITEMAP_PATH = Path("sitemap_oer_metadata.xml")
SOURCE_METADATA_PATH = EPUB_PACKAGE_PATH / EPUB_METADATA_FILENAME
SOURCE_METADATA_URL = f"{SITE}/{SOURCE_METADATA_PATH.as_posix()}"

OAI_DC_EN_FILENAME = "bopomofo-37-symbol-reference-en.oai-dc.xml"
OAI_DC_ZH_FILENAME = "bopomofo-37-symbol-reference-zh-hant.oai-dc.xml"
DCMI_FILENAME = "bopomofo-37-symbol-reference.dcmi-terms.jsonld"
LRMI_FILENAME = "bopomofo-37-symbol-reference.lrmi.jsonld"
BUNDLE_FILENAME = "bopomofo-37-symbol-oer-metadata-bundle.zip"
METADATA_FILENAME = "metadata.jsonld"
PRIMARY_FILENAMES = (
    OAI_DC_EN_FILENAME,
    OAI_DC_ZH_FILENAME,
    DCMI_FILENAME,
    LRMI_FILENAME,
)
DOWNLOAD_FILENAMES = (
    BUNDLE_FILENAME,
    *PRIMARY_FILENAMES,
    METADATA_FILENAME,
)

OAI_DC_NS = "http://www.openarchives.org/OAI/2.0/oai_dc/"
DC_ELEMENTS = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
DCMI_TYPE = "http://purl.org/dc/dcmitype/"
LRMI = "http://purl.org/dcx/lrmi-terms/"
LRMI_RESOURCE_TYPE = "http://purl.org/dcx/lrmi-vocabs/learningResourceType/"
LRMI_EDUCATIONAL_USE = "http://purl.org/dcx/lrmi-vocabs/educationalUse/"
SCHEMA = "https://schema.org/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
XSD = "http://www.w3.org/2001/XMLSchema#"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XML_NS = "http://www.w3.org/XML/1998/namespace"

OAI_DC_SCHEMA = "https://www.openarchives.org/OAI/2.0/oai_dc.xsd"
SIMPLE_DC_SCHEMA = (
    "https://www.dublincore.org/schemas/xmls/simpledc20021212.xsd"
)
DCMI_TERMS_SPEC = (
    "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/"
)
LRMI_SPEC = "https://www.dublincore.org/specifications/lrmi/"
LRMI_TERMS_SPEC = (
    "https://www.dublincore.org/specifications/lrmi/lrmi_terms/"
)
LRMI_RESOURCE_TYPE_SPEC = (
    "https://www.dublincore.org/specifications/lrmi/"
    "concept_schemes/learningResourceType/"
)
LRMI_EDUCATIONAL_USE_SPEC = (
    "https://www.dublincore.org/specifications/lrmi/"
    "concept_schemes/educationalUse/"
)
CREATOR = "Lumi Apps - iOS App Guide"
CREATOR_URL = f"{SITE}/#organization"
CARD_START = "<!-- oer-metadata-card:start -->"
CARD_END = "<!-- oer-metadata-card:end -->"

FORMATS = {
    OAI_DC_EN_FILENAME: ("OAI-DC XML - English", "application/xml"),
    OAI_DC_ZH_FILENAME: (
        "OAI-DC XML - Traditional Chinese",
        "application/xml",
    ),
    DCMI_FILENAME: ("DCMI Terms JSON-LD", "application/ld+json"),
    LRMI_FILENAME: ("LRMI JSON-LD", "application/ld+json"),
    BUNDLE_FILENAME: ("Complete ZIP bundle", "application/zip"),
    METADATA_FILENAME: ("Checksums and metadata", "application/ld+json"),
}

EDUCATION = {
    "en": {
        "description": (
            f"{EDITIONS['en']['summary']} It is a text-only supporting document "
            "for beginner reference and guided instruction."
        ),
        "scope": (
            "Text-only symbol reference; no audio, pronunciation scoring, "
            "diagnostic assessment, school-readiness judgement, formal standards "
            "alignment or complete Chinese course."
        ),
        "age": (
            "No fixed age range. Beginner learners of any age can use the "
            "reference; children should use it with a caregiver or educator."
        ),
        "subjects": (
            "Bopomofo (Zhuyin)",
            "Mandarin phonetic symbols",
            "Traditional Chinese literacy support",
        ),
    },
    "zh-Hant": {
        "description": (
            f"{EDITIONS['zh-Hant']['summary']} 這是一份純文字輔助文件，適合"
            "初學者查閱，亦可搭配引導式教學。"
        ),
        "scope": (
            "僅提供純文字符號參考；不含音訊、發音評分、診斷評量、入學準備"
            "判定、正式課綱對應或完整華語課程。"
        ),
        "age": (
            "不設定固定年齡範圍；任何年齡的注音初學者皆可使用，兒童應由"
            "照顧者或教師陪同。"
        ),
        "subjects": (
            "注音符號",
            "國語語音符號",
            "繁體中文識字輔助",
        ),
    },
}

COPY = {
    "en": {
        "lang": "en",
        "title": "OER repository metadata for a Bopomofo learning resource",
        "description": (
            "Download schema-valid OAI-DC and offline-parsable DCMI Terms and "
            "LRMI JSON-LD metadata for two open Bopomofo EPUB editions."
        ),
        "eyebrow": "OER metadata · DCMI + LRMI · English + zh-Hant",
        "lead": (
            "Repositories, school resource portals and open-education catalogs "
            "can describe the exact English and Traditional Chinese EPUB files "
            "without creating an account or depending on an app."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "badges": (
            "2 exact EPUB editions",
            "OAI-DC schema validation",
            "Offline JSON-LD parsing",
            "SHA-256 provenance",
        ),
        "download": "Download the OER metadata package",
        "download_text": (
            "Start with the deterministic ZIP, or select the syntax your "
            "repository accepts. Every record carries the source URL, byte "
            "length or fixity identifier, language, license and scope."
        ),
        "source": "Open the underlying EPUB resource",
        "formats": "Three interoperable metadata views",
        "format_items": (
            (
                "OAI-DC XML",
                "One standalone Simple Dublin Core record per language edition, "
                "validated offline against the official OAI-DC and DCMI schemas.",
            ),
            (
                "DCMI Terms JSON-LD",
                "A bilingual RDF graph with audience, education level, "
                "instructional method, rights, format, provenance and relations.",
            ),
            (
                "LRMI JSON-LD",
                "LearningResource and Book nodes using pinned LRMI terms plus "
                "official supportingDocument and instruction concept URIs.",
            ),
        ),
        "workflow": "Repository ingest workflow",
        "workflow_items": (
            "Download the ZIP or the individual metadata syntax.",
            "Verify SHA-256 and confirm the linked EPUB byte length.",
            "Map local subjects, audience fields and repository identifiers.",
            "Ingest into a staging collection and inspect language display.",
            "Publish only after the repository's own metadata review.",
        ),
        "audience": "Audience and age boundary",
        "audience_text": EDUCATION["en"]["age"],
        "verification": "Validation and provenance",
        "verification_text": (
            "The two XML records are validated with locally pinned official "
            "schemas. Both JSON-LD files use inline contexts and must parse "
            "without network access. DCMI and LRMI terms and the two controlled "
            "values are checked against pinned official RDF vocabularies. Source "
            "EPUB URLs, sizes, timestamps and SHA-256 values come only from the "
            "published EPUB manifest."
        ),
        "limits": "Protocol and scope limits",
        "limits_text": (
            "These are downloadable metadata records, not an OAI-PMH endpoint: "
            "no Identify, ListRecords or harvesting service is claimed. The "
            "package does not claim IMS or IEEE LOM conformance, universal "
            "repository compatibility, DOI or institutional approval. Strict "
            "URL importers may need a local download because static hosting can "
            "return generic XML or JSON Content-Types."
        ),
        "specs": "Official specifications and vocabularies",
        "license": "CC BY 4.0 license",
        "app_title": "Optional practice layer",
        "app_text": (
            "The open EPUB and metadata package work without an app. If available "
            "in your region, Lumi Bopomofo adds short on-device activities after "
            "the free repository resource."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "No account, analytics or learner profile is used. Review local "
            "repository policy before public ingest."
        ),
        "labels": {
            BUNDLE_FILENAME: "Complete deterministic ZIP",
            OAI_DC_EN_FILENAME: "English OAI-DC record",
            OAI_DC_ZH_FILENAME: "Traditional Chinese OAI-DC record",
            DCMI_FILENAME: "DCMI Terms JSON-LD graph",
            LRMI_FILENAME: "LRMI JSON-LD graph",
            METADATA_FILENAME: "Metadata manifest and checksums",
        },
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音學習資源的 OER 典藏庫 metadata",
        "description": (
            "下載兩個開放注音 EPUB 版本的 OAI-DC、DCMI Terms 與 LRMI "
            "metadata；XML 經 schema 驗證，JSON-LD 可離線解析。"
        ),
        "eyebrow": "OER metadata · DCMI + LRMI · 英文＋繁體中文",
        "lead": (
            "OER 典藏庫、學校資源平台與開放教育目錄可直接描述確切的英文及"
            "繁體中文 EPUB 檔案，不需帳號，也不依賴任何 App。"
        ),
        "back": "開放資料",
        "language": "English",
        "badges": (
            "2 個確切 EPUB 版本",
            "OAI-DC schema 驗證",
            "JSON-LD 離線解析",
            "SHA-256 來源驗證",
        ),
        "download": "下載 OER metadata 資料包",
        "download_text": (
            "可先下載可重現的完整 ZIP，或選擇典藏庫可接受的格式。每筆紀錄"
            "都包含來源網址、位元組長度或完整性識別碼、語言、授權與範圍。"
        ),
        "source": "開啟底層 EPUB 學習資源",
        "formats": "三種可互通 metadata",
        "format_items": (
            (
                "OAI-DC XML",
                "每個語言版本各有一筆獨立 Simple Dublin Core 紀錄，並以固定"
                "版本的官方 OAI-DC 與 DCMI schema 離線驗證。",
            ),
            (
                "DCMI Terms JSON-LD",
                "雙語 RDF 圖包含受眾、教育程度、教學方法、權利、格式、來源"
                "與版本關係。",
            ),
            (
                "LRMI JSON-LD",
                "LearningResource 與 Book 節點使用固定版本 LRMI 詞彙，以及"
                "官方 supportingDocument、instruction 概念 URI。",
            ),
        ),
        "workflow": "典藏庫匯入流程",
        "workflow_items": (
            "下載完整 ZIP 或個別 metadata 格式。",
            "驗證 SHA-256，並確認所連結 EPUB 的位元組長度。",
            "對應館內主題、受眾欄位與典藏庫識別碼。",
            "先匯入測試集合，檢查語言與文字顯示。",
            "完成典藏庫自身的 metadata 審查後再公開。",
        ),
        "audience": "受眾與年齡界線",
        "audience_text": EDUCATION["zh-Hant"]["age"],
        "verification": "驗證與來源",
        "verification_text": (
            "兩筆 XML 紀錄會以本機固定版本的官方 schema 驗證。兩份 JSON-LD "
            "皆使用 inline context，且必須在不連網時成功解析。DCMI、LRMI "
            "術語與兩個受控值會對照固定版本的官方 RDF 詞彙。EPUB 來源網址、"
            "大小、時間戳與 SHA-256 僅取自已發布的 EPUB manifest。"
        ),
        "limits": "協定與內容範圍",
        "limits_text": (
            "這些是可下載的 metadata 紀錄，不是 OAI-PMH endpoint；不宣稱提供 "
            "Identify、ListRecords 或即時 harvest 服務。資料包不宣稱符合 IMS "
            "或 IEEE LOM、普遍相容所有典藏庫、具有 DOI 或已獲機構核定。靜態"
            "主機可能回傳通用 XML／JSON Content-Type，嚴格的網址匯入器可先"
            "下載檔案再從本機匯入。"
        ),
        "specs": "官方規格與詞彙",
        "license": "CC BY 4.0 授權",
        "app_title": "選用的練習層",
        "app_text": (
            "開放 EPUB 與 metadata 資料包不需 App 即可使用。若所在地區可"
            "下載，Lumi 注音星球只會在免費典藏資源之後，提供裝置端短活動。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": (
            "不需帳號，不使用分析或學習者個人檔案；公開匯入前請審查館內政策。"
        ),
        "labels": {
            BUNDLE_FILENAME: "完整可重現 ZIP",
            OAI_DC_EN_FILENAME: "英文 OAI-DC 紀錄",
            OAI_DC_ZH_FILENAME: "繁體中文 OAI-DC 紀錄",
            DCMI_FILENAME: "DCMI Terms JSON-LD 圖",
            LRMI_FILENAME: "LRMI JSON-LD 圖",
            METADATA_FILENAME: "Metadata manifest 與校驗資訊",
        },
    },
}


def _dc(name: str) -> str:
    return f"{{{DC_ELEMENTS}}}{name}"


def _dc_text(root: ET.Element, name: str, value: str, language: str | None = None) -> None:
    attributes = {f"{{{XML_NS}}}lang": language} if language else {}
    ET.SubElement(root, _dc(name), attributes).text = value


def render_oai_dc(
    locale: str,
    source: dict,
    editions: dict[str, dict],
) -> bytes:
    ET.register_namespace("oai_dc", OAI_DC_NS)
    ET.register_namespace("dc", DC_ELEMENTS)
    ET.register_namespace("xsi", XSI_NS)
    root = ET.Element(
        f"{{{OAI_DC_NS}}}dc",
        {
            f"{{{XSI_NS}}}schemaLocation": (
                f"{OAI_DC_NS} {OAI_DC_SCHEMA} "
                f"{DC_ELEMENTS} {SIMPLE_DC_SCHEMA}"
            )
        },
    )
    copy = EDITIONS[locale]
    education = EDUCATION[locale]
    edition = editions[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    _dc_text(root, "title", copy["title"], locale)
    _dc_text(root, "creator", CREATOR)
    for subject in education["subjects"]:
        _dc_text(root, "subject", subject, locale)
    _dc_text(root, "description", education["description"], locale)
    _dc_text(root, "description", education["scope"], locale)
    _dc_text(root, "publisher", CREATOR)
    _dc_text(root, "date", source["datePublished"])
    _dc_text(root, "date", source["dateModified"])
    _dc_text(root, "type", "Text")
    _dc_text(root, "type", "LearningResource")
    _dc_text(root, "format", "application/epub+zip")
    _dc_text(root, "identifier", edition["contentUrl"])
    _dc_text(root, "identifier", copy["local_id"])
    _dc_text(root, "identifier", f"urn:sha256:{edition['sha256']}")
    _dc_text(root, "language", locale)
    _dc_text(root, "relation", editions[other_locale]["contentUrl"])
    _dc_text(root, "relation", EPUB_LANDING_URL)
    _dc_text(root, "relation", SOURCE_METADATA_URL)
    _dc_text(root, "rights", LICENSE)
    _dc_text(
        root,
        "rights",
        "Creative Commons Attribution 4.0 International",
        "en",
    )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _literal(value: str, language: str | None = None) -> dict:
    item = {"@value": value}
    if language:
        item["@language"] = language
    return item


def _iri(value: str) -> dict:
    return {"@id": value}


def _schema_context() -> dict:
    return {
        "@vocab": SCHEMA,
        "url": {"@id": f"{SCHEMA}url", "@type": "@id"},
        "license": {"@id": f"{SCHEMA}license", "@type": "@id"},
        "contentUrl": {
            "@id": f"{SCHEMA}contentUrl",
            "@type": "@id",
        },
        "isBasedOn": {
            "@id": f"{SCHEMA}isBasedOn",
            "@type": "@id",
        },
        "conformsTo": {
            "@id": f"{SCHEMA}conformsTo",
            "@type": "@id",
        },
    }


def _bilingual(en: str, zh_hant: str) -> list[dict]:
    return [_literal(en, "en"), _literal(zh_hant, "zh-Hant")]


def _shared_dcmi_nodes() -> list[dict]:
    return [
        {
            "@id": CREATOR_URL,
            "@type": "dcterms:Agent",
            "dcterms:title": _bilingual(
                CREATOR,
                "Lumi Apps iOS 應用指南",
            ),
        },
        {
            "@id": f"{LANDING_URL}#audience-learners",
            "@type": "dcterms:AgentClass",
            "dcterms:title": _bilingual(
                "Beginner Bopomofo learners of any age",
                "任何年齡的注音初學者",
            ),
            "dcterms:description": _bilingual(
                "Children should use the reference with a caregiver or educator.",
                "兒童應由照顧者或教師陪同使用。",
            ),
        },
        {
            "@id": f"{LANDING_URL}#audience-supporters",
            "@type": "dcterms:AgentClass",
            "dcterms:title": _bilingual(
                "Educators, caregivers, librarians and OER repository staff",
                "教師、照顧者、圖書館員與 OER 典藏庫人員",
            ),
        },
        {
            "@id": f"{LANDING_URL}#level-beginner",
            "@type": "dcterms:AgentClass",
            "dcterms:title": _bilingual("Beginner", "初學"),
        },
        {
            "@id": f"{LANDING_URL}#method-reference",
            "@type": "dcterms:MethodOfInstruction",
            "dcterms:title": _bilingual(
                "Self-paced lookup, guided review or classroom support",
                "自主查閱、引導式複習或課堂輔助",
            ),
        },
    ]


def render_dcmi_jsonld(
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> bytes:
    record_url = f"{PACKAGE_URL}/{DCMI_FILENAME}"
    graph = [
        *_shared_dcmi_nodes(),
        {
            "@id": record_url,
            "@type": "dcmiType:Dataset",
            "dcterms:title": _bilingual(
                "DCMI Terms metadata for the Bopomofo learning resource",
                "注音學習資源的 DCMI Terms metadata",
            ),
            "dcterms:description": _bilingual(
                "A bilingual linked-data record derived from the published EPUB manifest.",
                "依據已發布 EPUB manifest 建立的雙語 linked-data 記錄。",
            ),
            "dcterms:creator": _iri(CREATOR_URL),
            "dcterms:publisher": _iri(CREATOR_URL),
            "dcterms:issued": {
                "@value": INITIAL_DATE,
                "@type": "xsd:date",
            },
            "dcterms:modified": {
                "@value": modified,
                "@type": "xsd:dateTime",
            },
            "dcterms:format": "application/ld+json",
            "dcterms:identifier": record_url,
            "dcterms:source": _iri(SOURCE_METADATA_URL),
            "dcterms:references": [
                _iri(editions[locale]["contentUrl"])
                for locale in ("en", "zh-Hant")
            ],
            "dcterms:conformsTo": _iri(DCMI_TERMS_SPEC),
            "dcterms:license": _iri(LICENSE),
            "dcterms:isPartOf": _iri(
                f"{LANDING_URL}#metadata-package"
            ),
        },
    ]
    for locale in ("en", "zh-Hant"):
        copy = EDITIONS[locale]
        education = EDUCATION[locale]
        edition = editions[locale]
        other_locale = "zh-Hant" if locale == "en" else "en"
        graph.append(
            {
                "@id": edition["contentUrl"],
                "@type": [
                    "dcterms:BibliographicResource",
                    "dcmiType:Text",
                ],
                "dcterms:title": _literal(copy["title"], locale),
                "dcterms:alternative": _literal(copy["alternate"], other_locale),
                "dcterms:creator": _iri(CREATOR_URL),
                "dcterms:publisher": _iri(CREATOR_URL),
                "dcterms:subject": [
                    _literal(subject, locale) for subject in education["subjects"]
                ],
                "dcterms:description": [
                    _literal(education["description"], locale),
                    _literal(education["scope"], locale),
                    _literal(education["age"], locale),
                ],
                "dcterms:issued": {
                    "@value": source["datePublished"],
                    "@type": "xsd:date",
                },
                "dcterms:modified": {
                    "@value": source["dateModified"],
                    "@type": "xsd:dateTime",
                },
                "dcterms:type": _iri(
                    f"{LRMI_RESOURCE_TYPE}supportingDocument"
                ),
                "dcterms:format": "application/epub+zip",
                "dcterms:extent": f"{edition['size']} bytes",
                "dcterms:identifier": [
                    edition["contentUrl"],
                    copy["local_id"],
                    f"urn:sha256:{edition['sha256']}",
                ],
                "dcterms:language": locale,
                "dcterms:relation": _iri(editions[other_locale]["contentUrl"]),
                "dcterms:rights": _literal(
                    (
                        "Creative Commons Attribution 4.0 International; "
                        "open access with no account required."
                    )
                    if locale == "en"
                    else "採 Creative Commons 姓名標示 4.0 國際授權；開放存取且不需帳號。",
                    locale,
                ),
                "dcterms:license": _iri(LICENSE),
                "dcterms:accessRights": _literal(
                    "Open access" if locale == "en" else "開放存取",
                    locale,
                ),
                "dcterms:audience": [
                    _iri(f"{LANDING_URL}#audience-learners"),
                    _iri(f"{LANDING_URL}#audience-supporters"),
                ],
                "dcterms:educationLevel": _iri(
                    f"{LANDING_URL}#level-beginner"
                ),
                "dcterms:instructionalMethod": _iri(
                    f"{LANDING_URL}#method-reference"
                ),
                "dcterms:conformsTo": [
                    _iri(EPUB_SPEC),
                    _iri(EPUB_A11Y_SPEC),
                ],
                "dcterms:isReferencedBy": [
                    _iri(SOURCE_METADATA_URL),
                    _iri(EPUB_LANDING_URL),
                    _iri(record_url),
                ],
            }
        )
    document = {
        "@context": {
            "dcterms": DCTERMS,
            "dcmiType": DCMI_TYPE,
            "xsd": XSD,
        },
        "@graph": graph,
    }
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _shared_lrmi_nodes() -> list[dict]:
    return [
        {
            "@id": CREATOR_URL,
            "@type": "schema:Organization",
            "schema:name": _bilingual(
                CREATOR,
                "Lumi Apps iOS 應用指南",
            ),
            "schema:url": _iri(SITE),
        },
        {
            "@id": f"{LANDING_URL}#audience-learners",
            "@type": [
                "lrmi:EducationalAudience",
                "schema:EducationalAudience",
            ],
            "lrmi:educationalRole": "learner",
            "schema:name": _bilingual(
                "Beginner Bopomofo learners of any age",
                "任何年齡的注音初學者",
            ),
            "schema:description": _bilingual(
                "Children should use the reference with a caregiver or educator.",
                "兒童應由照顧者或教師陪同使用。",
            ),
        },
        {
            "@id": f"{LANDING_URL}#audience-educators",
            "@type": [
                "lrmi:EducationalAudience",
                "schema:EducationalAudience",
            ],
            "lrmi:educationalRole": [
                "teacher",
                "caregiver",
                "librarian",
                "repository manager",
            ],
            "schema:name": _bilingual(
                "Educators, caregivers, librarians and OER repository staff",
                "教師、照顧者、圖書館員與 OER 典藏庫人員",
            ),
        },
        {
            "@id": f"{LANDING_URL}#level-beginner",
            "@type": ["schema:DefinedTerm", "skos:Concept"],
            "schema:name": _bilingual("Beginner", "初學"),
            "skos:prefLabel": _bilingual("Beginner", "初學"),
        },
        {
            "@id": f"{LANDING_URL}#outcome-symbols",
            "@type": ["schema:DefinedTerm", "skos:Concept"],
            "schema:name": _bilingual(
                "Recognize and look up all 37 standard Bopomofo symbols",
                "辨識並查閱全部 37 個標準注音符號",
            ),
            "skos:prefLabel": _bilingual(
                "37-symbol Bopomofo recognition",
                "37 符號注音辨識",
            ),
        },
        {
            "@id": f"{LANDING_URL}#outcome-crosswalk",
            "@type": ["schema:DefinedTerm", "skos:Concept"],
            "schema:name": _bilingual(
                "Consult broad Pinyin and IPA correspondences",
                "查閱概略漢語拼音與 IPA 對照",
            ),
            "skos:prefLabel": _bilingual(
                "Bopomofo sound-reference crosswalk",
                "注音語音參考對照",
            ),
        },
        {
            "@id": f"{LANDING_URL}#outcome-examples",
            "@type": ["schema:DefinedTerm", "skos:Concept"],
            "schema:name": _bilingual(
                "Use example characters for guided symbol review",
                "以例字進行引導式符號複習",
            ),
            "skos:prefLabel": _bilingual(
                "Guided Bopomofo example lookup",
                "注音例字引導查閱",
            ),
        },
    ]


def render_lrmi_jsonld(
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> bytes:
    record_url = f"{PACKAGE_URL}/{LRMI_FILENAME}"
    graph = [
        *_shared_lrmi_nodes(),
        {
            "@id": record_url,
            "@type": "schema:Dataset",
            "schema:name": _bilingual(
                "LRMI metadata for the Bopomofo learning resource",
                "注音學習資源的 LRMI metadata",
            ),
            "schema:description": _bilingual(
                "A bilingual educational metadata record derived from the published EPUB manifest.",
                "依據已發布 EPUB manifest 建立的雙語教育 metadata 記錄。",
            ),
            "schema:creator": _iri(CREATOR_URL),
            "schema:publisher": _iri(CREATOR_URL),
            "schema:url": _iri(record_url),
            "schema:datePublished": {
                "@value": INITIAL_DATE,
                "@type": "xsd:date",
            },
            "schema:dateModified": {
                "@value": modified,
                "@type": "xsd:dateTime",
            },
            "schema:encodingFormat": "application/ld+json",
            "schema:license": _iri(LICENSE),
            "schema:isBasedOn": _iri(SOURCE_METADATA_URL),
            "schema:about": [
                _iri(editions[locale]["contentUrl"])
                for locale in ("en", "zh-Hant")
            ],
            "schema:conformsTo": _iri(LRMI_TERMS_SPEC),
            "schema:isPartOf": _iri(
                f"{LANDING_URL}#metadata-package"
            ),
        },
    ]
    for locale in ("en", "zh-Hant"):
        copy = EDITIONS[locale]
        education = EDUCATION[locale]
        edition = editions[locale]
        other_locale = "zh-Hant" if locale == "en" else "en"
        graph.append(
            {
                "@id": edition["contentUrl"],
                "@type": [
                    "lrmi:LearningResource",
                    "schema:Book",
                ],
                "schema:name": _literal(copy["title"], locale),
                "schema:alternateName": _literal(
                    copy["alternate"],
                    other_locale,
                ),
                "schema:description": _literal(
                    education["description"],
                    locale,
                ),
                "schema:creator": _iri(CREATOR_URL),
                "schema:publisher": _iri(CREATOR_URL),
                "schema:url": _iri(edition["contentUrl"]),
                "schema:mainEntityOfPage": _iri(EPUB_LANDING_URL),
                "schema:identifier": [
                    copy["local_id"],
                    f"urn:sha256:{edition['sha256']}",
                ],
                "schema:inLanguage": locale,
                "schema:datePublished": {
                    "@value": source["datePublished"],
                    "@type": "xsd:date",
                },
                "schema:dateModified": {
                    "@value": source["dateModified"],
                    "@type": "xsd:dateTime",
                },
                "schema:license": _iri(LICENSE),
                "schema:isAccessibleForFree": True,
                "schema:subjectOf": [
                    _iri(SOURCE_METADATA_URL),
                    _iri(record_url),
                ],
                "schema:conformsTo": [
                    _iri(EPUB_SPEC),
                    _iri(EPUB_A11Y_SPEC),
                ],
                "schema:keywords": [
                    "Bopomofo",
                    "Zhuyin",
                    "Mandarin phonetic symbols",
                    "Traditional Chinese",
                    "open educational resource",
                ],
                "schema:audience": [
                    _iri(f"{LANDING_URL}#audience-learners"),
                    _iri(f"{LANDING_URL}#audience-educators"),
                ],
                "schema:encoding": {
                    "@type": "schema:MediaObject",
                    "schema:contentUrl": _iri(edition["contentUrl"]),
                    "schema:encodingFormat": "application/epub+zip",
                    "schema:contentSize": f"{edition['size']} bytes",
                    "schema:sha256": edition["sha256"],
                    "schema:inLanguage": locale,
                },
                "schema:accessMode": "textual",
                "schema:accessModeSufficient": "textual",
                "schema:accessibilityFeature": [
                    "tableOfContents",
                    "readingOrder",
                    "structuralNavigation",
                ],
                "schema:accessibilityHazard": [
                    "noFlashingHazard",
                    "noMotionSimulationHazard",
                    "noSoundHazard",
                ],
                "schema:accessibilitySummary": _literal(
                    (
                        "Text-only publication with structural navigation and "
                        "no images, audio, scripts, flashing, motion simulation "
                        "or sound hazards. No accessibility certification is claimed."
                    )
                    if locale == "en"
                    else "純文字出版品，具結構化導覽，無圖片、音訊、script、閃爍、動態模擬或聲音危害；不宣稱取得無障礙認證。",
                    locale,
                ),
                "schema:additionalProperty": [
                    {
                        "@type": "schema:PropertyValue",
                        "schema:name": _literal(
                            "Age scope" if locale == "en" else "年齡範圍",
                            locale,
                        ),
                        "schema:value": _literal(education["age"], locale),
                    },
                    {
                        "@type": "schema:PropertyValue",
                        "schema:name": _literal(
                            "Scope boundary" if locale == "en" else "內容界線",
                            locale,
                        ),
                        "schema:value": _literal(education["scope"], locale),
                    },
                ],
                "lrmi:learningResourceType": _iri(
                    f"{LRMI_RESOURCE_TYPE}supportingDocument"
                ),
                "lrmi:educationalUse": _iri(
                    f"{LRMI_EDUCATIONAL_USE}instruction"
                ),
                "lrmi:educationalLevel": _iri(
                    f"{LANDING_URL}#level-beginner"
                ),
                "lrmi:teaches": [
                    _iri(f"{LANDING_URL}#outcome-symbols"),
                    _iri(f"{LANDING_URL}#outcome-crosswalk"),
                    _iri(f"{LANDING_URL}#outcome-examples"),
                ],
            }
        )
    document = {
        "@context": {
            "schema": SCHEMA,
            "lrmi": LRMI,
            "resourceType": LRMI_RESOURCE_TYPE,
            "educationalUse": LRMI_EDUCATIONAL_USE,
            "skos": SKOS,
            "xsd": XSD,
        },
        "@graph": graph,
    }
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


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
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> bytes:
    checksums = "".join(
        f"{_sha256(primary[filename])}  {filename}\n"
        for filename in sorted(primary)
    )
    readme = f"""Bopomofo OER repository metadata
=================================

This deterministic bundle describes the exact English and Traditional Chinese
editions of the open 37-symbol Bopomofo EPUB.

Files
-----
- {OAI_DC_EN_FILENAME}: standalone English OAI-DC record
- {OAI_DC_ZH_FILENAME}: standalone Traditional Chinese OAI-DC record
- {DCMI_FILENAME}: DCMI Terms RDF graph in JSON-LD
- {LRMI_FILENAME}: LRMI RDF graph in JSON-LD
- checksums.sha256: SHA-256 for the four metadata files

Validation and scope
--------------------
- OAI-DC XML is validated against pinned official OAI and DCMI schemas.
- JSON-LD uses inline contexts and is parsed without network access.
- LRMI controlled values are supportingDocument and instruction.
- These files are records, not an OAI-PMH endpoint or harvesting service.
- No IMS or IEEE LOM conformance, DOI, institutional approval or universal
  repository compatibility is claimed.
- The resource has no fixed learner age; it is for beginners of any age, with
  adult or educator support for children.

Source manifest: {SOURCE_METADATA_URL}
Source modified: {source["dateModified"]}
Metadata modified: {modified}
English EPUB: {editions["en"]["contentUrl"]}
English SHA-256: {editions["en"]["sha256"]}
Traditional Chinese EPUB: {editions["zh-Hant"]["contentUrl"]}
Traditional Chinese SHA-256: {editions["zh-Hant"]["sha256"]}
License: {LICENSE}
"""
    entries = {
        **primary,
        "README.txt": readme.encode("utf-8"),
        "checksums.sha256": checksums.encode("ascii"),
    }
    stamp = _parse_timestamp(modified)
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


def render_metadata(
    source: dict,
    editions: dict[str, dict],
    artifacts: list[dict],
    modified: str,
) -> bytes:
    metadata = {
        "@context": _schema_context(),
        "@type": ["Dataset", "CreativeWork"],
        "@id": f"{LANDING_URL}#metadata-package",
        "name": "Bopomofo OER repository metadata package",
        "alternateName": "注音 OER 典藏庫 metadata 資料包",
        "description": (
            "Standalone OAI-DC records plus offline-parsable DCMI Terms and "
            "LRMI JSON-LD for two exact open Bopomofo EPUB editions."
        ),
        "url": LANDING_URL,
        "identifier": "LUMI-ZHUYIN-OER-METADATA-2026",
        "version": VERSION,
        "datePublished": source["datePublished"],
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
        "audience": [
            "OER repositories",
            "school resource portals",
            "educators",
            "librarians",
        ],
        "isBasedOn": {
            "@type": "Book",
            "url": EPUB_LANDING_URL,
            "dateModified": source["dateModified"],
            "encoding": [
                {
                    "@type": "MediaObject",
                    "contentUrl": editions[locale]["contentUrl"],
                    "encodingFormat": "application/epub+zip",
                    "contentSize": f"{editions[locale]['size']} bytes",
                    "sha256": editions[locale]["sha256"],
                    "inLanguage": locale,
                }
                for locale in ("en", "zh-Hant")
            ],
        },
        "conformsTo": [
            OAI_DC_SCHEMA,
            SIMPLE_DC_SCHEMA,
            DCMI_TERMS_SPEC,
            LRMI_TERMS_SPEC,
            LRMI_RESOURCE_TYPE_SPEC,
            LRMI_EDUCATIONAL_USE_SPEC,
        ],
        "numberOfItems": 2,
        "keywords": [
            "Bopomofo",
            "Zhuyin",
            "OER metadata",
            "OAI-DC",
            "Dublin Core",
            "DCMI Terms",
            "LRMI",
            "open educational resources",
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
        "includedInDataCatalog": {
            "@type": "DataCatalog",
            "name": "Lumi Apps Open Data",
            "url": f"{SITE}/data/",
        },
    }
    return (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def render_package(
    source: dict,
    editions: dict[str, dict],
    modified: str,
) -> dict[str, bytes]:
    primary = {
        OAI_DC_EN_FILENAME: render_oai_dc("en", source, editions),
        OAI_DC_ZH_FILENAME: render_oai_dc("zh-Hant", source, editions),
        DCMI_FILENAME: render_dcmi_jsonld(source, editions, modified),
        LRMI_FILENAME: render_lrmi_jsonld(source, editions, modified),
    }
    bundle = render_bundle(primary, source, editions, modified)
    artifacts = [
        _artifact(BUNDLE_FILENAME, bundle),
        *[_artifact(filename, primary[filename]) for filename in PRIMARY_FILENAMES],
    ]
    metadata = render_metadata(source, editions, artifacts, modified)
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
        _parse_timestamp(modified)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
    return modified


def _package_matches(pages: Path, package: dict[str, bytes]) -> bool:
    return all(
        (pages / PACKAGE_PATH / filename).exists()
        and (pages / PACKAGE_PATH / filename).read_bytes() == content
        for filename, content in package.items()
    )


def validate_raw_package(package: dict[str, bytes], editions: dict[str, dict]) -> None:
    combined = b"\n".join(package.values())
    for forbidden in (
        b"apps.apple.com",
        APP_ID.encode("ascii"),
        APP_NAME.encode("utf-8"),
        b"SoftwareApplication",
        b"imsmd",
    ):
        if forbidden in combined:
            raise ValueError(
                "OER metadata package must remain app-independent: "
                + forbidden.decode("utf-8")
            )
    for filename in (OAI_DC_EN_FILENAME, OAI_DC_ZH_FILENAME):
        root = ET.fromstring(package[filename])
        if root.tag != f"{{{OAI_DC_NS}}}dc":
            raise ValueError(f"Invalid OAI-DC root element: {filename}")
        if len(root.findall(_dc("identifier"))) < 3:
            raise ValueError(f"OAI-DC record lacks fixity identifiers: {filename}")
    for filename in (DCMI_FILENAME, LRMI_FILENAME):
        document = json.loads(package[filename])
        if not isinstance(document.get("@context"), dict):
            raise ValueError(f"JSON-LD context must be inline: {filename}")
        if len(document.get("@graph", [])) < 2:
            raise ValueError(f"JSON-LD graph is incomplete: {filename}")
    for edition in editions.values():
        if edition["contentUrl"].encode("utf-8") not in combined:
            raise ValueError("Source EPUB URL is missing from OER metadata")
        if edition["sha256"].encode("ascii") not in combined:
            raise ValueError("Source EPUB SHA-256 is missing from OER metadata")
    with zipfile.ZipFile(io.BytesIO(package[BUNDLE_FILENAME])) as archive:
        expected = {*PRIMARY_FILENAMES, "README.txt", "checksums.sha256"}
        if set(archive.namelist()) != expected:
            raise ValueError("OER metadata ZIP does not contain the expected files")
        checksums = {}
        for line in archive.read("checksums.sha256").decode("ascii").splitlines():
            checksum, filename = line.split("  ", 1)
            checksums[filename] = checksum
        for filename in PRIMARY_FILENAMES:
            content = archive.read(filename)
            if content != package[filename]:
                raise ValueError(f"OER metadata ZIP mismatch: {filename}")
            if checksums.get(filename) != _sha256(content):
                raise ValueError(f"OER metadata checksum mismatch: {filename}")


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
            "mainEntity": {"@id": f"{LANDING_URL}#metadata-package"},
        },
        {
            "@type": ["Dataset", "CreativeWork"],
            "@id": f"{LANDING_URL}#metadata-package",
            "name": "Bopomofo OER repository metadata package",
            "alternateName": "注音 OER 典藏庫 metadata 資料包",
            "description": copy["description"],
            "url": LANDING_URL,
            "version": VERSION,
            "datePublished": INITIAL_DATE,
            "dateModified": package_modified,
            "inLanguage": ["en", "zh-Hant"],
            "license": LICENSE,
            "isAccessibleForFree": True,
            "isBasedOn": EPUB_LANDING_URL,
            "conformsTo": [
                OAI_DC_SCHEMA,
                DCMI_TERMS_SPEC,
                LRMI_TERMS_SPEC,
                LRMI_RESOURCE_TYPE_SPEC,
                LRMI_EDUCATIONAL_USE_SPEC,
            ],
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
                f"iag_bopomofo_oer_metadata_{locale.lower()}",
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
    labels = copy["labels"]
    badges = "".join(f"<span>{html.escape(item)}</span>" for item in copy["badges"])
    downloads = []
    for filename in DOWNLOAD_FILENAMES:
        info = package_info[filename]
        css = "download primary" if filename == BUNDLE_FILENAME else "download"
        downloads.append(
            f'<a class="{css}" href="{html.escape(info["url"], quote=True)}">'
            f"<strong>{html.escape(labels[filename])}</strong>"
            f"<span>{html.escape(filename)}</span>"
            f"<small>{info['size']:,} bytes · SHA-256 "
            f"{html.escape(info['sha256'][:16])}…</small></a>"
        )
    format_cards = "".join(
        f"<article><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></article>"
        for title, text in copy["format_items"]
    )
    workflow = "".join(
        f"<li><span>{index}</span>{html.escape(item)}</li>"
        for index, item in enumerate(copy["workflow_items"], 1)
    )
    specs = "".join(
        f'<a href="{url}" rel="noopener">{html.escape(label)}</a>'
        for label, url in (
            ("OAI-DC XML schema", OAI_DC_SCHEMA),
            ("DCMI Metadata Terms", DCMI_TERMS_SPEC),
            ("LRMI Terms", LRMI_TERMS_SPEC),
            ("LRMI resource types", LRMI_RESOURCE_TYPE_SPEC),
            ("LRMI educational uses", LRMI_EDUCATIONAL_USE_SPEC),
        )
    )
    app_block = ""
    if app_public:
        app_url = appstore_url(
            APP_KEY,
            f"iag_bopomofo_oer_metadata_{locale.lower()}",
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
<link rel="describedby" type="application/ld+json" href="{PACKAGE_URL}/{METADATA_FILENAME}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#152238;--sub:#5a677a;--line:#d8e1ec;--brand:#3c5fa7;--deep:#172f58;--bg:#f2f5f9;--paper:#fff;--soft:#eaf1fb;--gold:#b57b24}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}.wrap{{max-width:1060px;margin:auto;padding:24px 20px 74px}}a{{color:var(--brand)}}.top{{display:flex;justify-content:space-between;gap:16px;font-size:14px}}.top a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding:58px 0 32px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(33px,7vw,59px);line-height:1.06;letter-spacing:-.039em;margin:10px 0 17px;max-width:930px}}h2{{font-size:clamp(23px,4vw,32px);line-height:1.2;margin:0 0 10px}}h3{{font-size:18px;margin:0 0 7px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:850px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:730;white-space:nowrap}}section{{margin-top:34px}}.panel,.app{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(19px,4vw,29px);box-shadow:0 14px 35px rgba(26,49,82,.055)}}.downloads,.grid,.specs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:12px;margin-top:18px}}.download{{display:flex;min-width:0;flex-direction:column;gap:4px;border:1px solid var(--line);border-radius:15px;padding:16px;background:#fbfcfe;text-decoration:none;color:var(--ink)}}.download.primary{{grid-column:1/-1;background:var(--deep);border-color:var(--deep);color:#fff}}.download strong{{font-size:17px}}.download span,.download small{{overflow-wrap:anywhere;color:var(--sub)}}.download.primary span,.download.primary small{{color:#dbe8fa}}.grid article{{background:#fff;border:1px solid var(--line);border-radius:17px;padding:19px}}.grid p{{margin:0}}.steps{{list-style:none;padding:0;margin:18px 0 0;display:grid;gap:10px}}.steps li{{display:flex;align-items:flex-start;gap:12px;color:var(--sub)}}.steps span{{display:grid;place-items:center;flex:0 0 28px;height:28px;border-radius:50%;background:var(--deep);color:#fff;font-weight:850;font-size:13px}}.specs a{{background:var(--soft);border-radius:13px;padding:13px 15px;text-decoration:none;font-weight:780;white-space:nowrap}}.audience{{border-top:4px solid var(--brand)}}.notice{{border-left:4px solid var(--gold)}}.app a{{font-weight:820;text-decoration:none;white-space:nowrap}}footer{{margin-top:42px;padding-top:21px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}}@media(max-width:520px){{.wrap{{padding-left:16px;padding-right:16px}}.panel,.app{{border-radius:18px}}}}
</style>
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{SITE}/data/">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(other, quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></header>
<section class="panel"><h2>{html.escape(copy['download'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{''.join(downloads)}</div><p><a href="{EPUB_LANDING_URL}">{html.escape(copy['source'])} &rarr;</a></p></section>
<section><h2>{html.escape(copy['formats'])}</h2><div class="grid">{format_cards}</div></section>
<section class="panel"><h2>{html.escape(copy['workflow'])}</h2><ol class="steps">{workflow}</ol></section>
<section class="panel audience"><h2>{html.escape(copy['audience'])}</h2><p>{html.escape(copy['audience_text'])}</p></section>
<section class="panel"><h2>{html.escape(copy['verification'])}</h2><p>{html.escape(copy['verification_text'])}</p><h3>{html.escape(copy['specs'])}</h3><div class="specs">{specs}<a href="{LICENSE}" rel="license noopener">{html.escape(copy['license'])} &rarr;</a></div></section>
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
        '<span class="tag">OAI-DC · DCMI Terms · LRMI</span>'
        "<h2>Bopomofo OER repository metadata</h2>"
        "<p>Two exact EPUB editions with schema validation, offline JSON-LD "
        "parsing and SHA-256 provenance.</p></div>"
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
                    "@type": ["Dataset", "CreativeWork"],
                    "name": "Bopomofo OER repository metadata package",
                    "description": COPY["en"]["description"],
                    "url": LANDING_URL,
                    "dateModified": modified,
                    "license": LICENSE,
                    "conformsTo": [
                        OAI_DC_SCHEMA,
                        DCMI_TERMS_SPEC,
                        LRMI_TERMS_SPEC,
                    ],
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
    source, editions = load_epub_source(pages)
    source_modified = source["dateModified"]
    prior = _prior_modified(pages)
    base_modified = (
        _max_timestamp(prior, source_modified) if prior else source_modified
    )
    package = render_package(source, editions, base_modified)
    if prior and not _package_matches(pages, package):
        target_modified = (
            source_modified
            if _parse_timestamp(source_modified) > _parse_timestamp(prior)
            else _next_timestamp(prior)
        )
        package = render_package(source, editions, target_modified)
    else:
        target_modified = base_modified
    validate_raw_package(package, editions)

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
    print(f"Built {len(built)} OER repository metadata resources")
