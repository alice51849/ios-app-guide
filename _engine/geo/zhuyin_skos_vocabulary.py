#!/usr/bin/env python3
"""Publish all 37 Zhuyin symbols as a bilingual SKOS linked-data vocabulary."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
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
from site_config import PUBLIC_SITE  # noqa: E402


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
SLUG = "zhuyin-bopomofo-vocabulary"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
LANDING_URL = f"{SITE}/data/{SLUG}.html"
VOCAB_NS = f"{LANDING_URL}#"
SCHEME_URI = f"{VOCAB_NS}scheme"
DATASET_URI = f"{VOCAB_NS}dataset"
ORG_URI = f"{SITE}/#organization"
SOURCE_DATASET = f"{SITE}/data/zhuyin-bopomofo.json"
SOURCE_PAGE = f"{SITE}/data/zhuyin-bopomofo.html"
ANKI_PAGE = f"{SITE}/tools/zhuyin-bopomofo-anki-deck.html"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/"
    "index.html"
)
UNICODE_CHART = "https://www.unicode.org/charts/PDF/U3100.pdf"
SKOS_REFERENCE = "https://www.w3.org/TR/skos-reference/"
JSON_LD_REFERENCE = "https://www.w3.org/TR/json-ld11/"
DCAT_REFERENCE = "https://www.w3.org/TR/vocab-dcat-3/"
VOID_REFERENCE = "https://www.w3.org/TR/void/"
SHACL_REFERENCE = "https://www.w3.org/TR/shacl/"
METADATA_FILENAME = f"{SLUG}.metadata.jsonld"
METADATA_URL = f"{SITE}/data/{METADATA_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_vocab.xml"
APP_KEY = "lumibopomofo"
APP_ID = "6773017109"
APP_NAME = "Lumi Bopomofo"
CONTENT_MODIFIED_RE = re.compile(
    r'"dcterms:modified"\s*:\s*"(\d{4}-\d{2}-\d{2})"'
)

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
DCTERMS = "http://purl.org/dc/terms/"
SCHEMA = "https://schema.org/"
DCAT = "http://www.w3.org/ns/dcat#"
VOID = "http://rdfs.org/ns/void#"
SH = "http://www.w3.org/ns/shacl#"

RDF_TYPE = f"{RDF}type"
RDF_PROPERTY = f"{RDF}Property"
RDFS_LABEL = f"{RDFS}label"
RDFS_DOMAIN = f"{RDFS}domain"
RDFS_RANGE = f"{RDFS}range"
RDFS_LITERAL = f"{RDFS}Literal"
SKOS_CONCEPT = f"{SKOS}Concept"
SKOS_COLLECTION = f"{SKOS}Collection"
SKOS_SCHEME = f"{SKOS}ConceptScheme"
SKOS_PREF_LABEL = f"{SKOS}prefLabel"
SKOS_ALT_LABEL = f"{SKOS}altLabel"
SKOS_DEFINITION = f"{SKOS}definition"
SKOS_NOTATION = f"{SKOS}notation"
SKOS_IN_SCHEME = f"{SKOS}inScheme"
SKOS_HAS_TOP = f"{SKOS}hasTopConcept"
SKOS_TOP_OF = f"{SKOS}topConceptOf"
SKOS_BROADER = f"{SKOS}broader"
SKOS_NARROWER = f"{SKOS}narrower"
SKOS_RELATED = f"{SKOS}related"
SKOS_BROADER_TRANSITIVE = f"{SKOS}broaderTransitive"
SKOS_EXACT_MATCH = f"{SKOS}exactMatch"
SKOS_BROAD_MATCH = f"{SKOS}broadMatch"
SKOS_RELATED_MATCH = f"{SKOS}relatedMatch"

PROPERTIES = {
    "pinyin": f"{VOCAB_NS}pinyin",
    "ipa": f"{VOCAB_NS}ipa",
    "exampleCharacter": f"{VOCAB_NS}exampleCharacter",
    "examplePinyin": f"{VOCAB_NS}examplePinyin",
    "exampleMeaning": f"{VOCAB_NS}exampleMeaning",
}

PREFIXES = {
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
    "skos": SKOS,
    "dcterms": DCTERMS,
    "schema": SCHEMA,
    "dcat": DCAT,
    "void": VOID,
    "sh": SH,
    "zhuyin": VOCAB_NS,
}
JSONLD_CONTEXT = {"@version": 1.1, **PREFIXES}

CATEGORIES = {
    "initial": {
        "id": "initials",
        "en": "Zhuyin initials",
        "zh-Hant": "注音聲母",
        "definition_en": "The 21 consonant initials in the Zhuyin system.",
        "definition_zh": "注音符號系統中的 21 個聲母。",
    },
    "medial": {
        "id": "medials",
        "en": "Zhuyin medials",
        "zh-Hant": "注音介音",
        "definition_en": "The three glide medials in the Zhuyin system.",
        "definition_zh": "注音符號系統中的 3 個介音。",
    },
    "final": {
        "id": "finals",
        "en": "Zhuyin finals",
        "zh-Hant": "注音韻母",
        "definition_en": "The 13 vowel finals in the Zhuyin system.",
        "definition_zh": "注音符號系統中的 13 個韻母。",
    },
}

ARTIFACT_SPECS = {
    "jsonld": {
        "filename": f"{SLUG}.jsonld",
        "media_type": "application/ld+json",
        "format": "JSON-LD 1.1",
        "format_iri": "http://www.w3.org/ns/formats/JSON-LD",
        "label_en": "JSON-LD vocabulary",
        "label_zh": "JSON-LD 詞彙",
    },
    "turtle": {
        "filename": f"{SLUG}.ttl",
        "media_type": "text/turtle",
        "format": "Turtle",
        "format_iri": "http://www.w3.org/ns/formats/Turtle",
        "label_en": "Turtle vocabulary",
        "label_zh": "Turtle 詞彙",
    },
    "ntriples": {
        "filename": f"{SLUG}.nt",
        "media_type": "application/n-triples",
        "format": "N-Triples",
        "format_iri": "http://www.w3.org/ns/formats/N-Triples",
        "label_en": "N-Triples vocabulary",
        "label_zh": "N-Triples 詞彙",
    },
    "shacl": {
        "filename": f"{SLUG}.shacl.ttl",
        "media_type": "text/turtle",
        "format": "SHACL",
        "format_iri": "http://www.w3.org/ns/formats/Turtle",
        "label_en": "SHACL validation shapes",
        "label_zh": "SHACL 驗證規則",
    },
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo SKOS Vocabulary - 37 Zhuyin Symbols as Linked Open Data",
        "description": (
            "Download a CC BY 4.0 SKOS vocabulary for all 37 Zhuyin symbols in "
            "JSON-LD, Turtle and N-Triples, with SHACL and DCAT/VoID metadata."
        ),
        "eyebrow": "Linked open vocabulary · SKOS · CC BY 4.0",
        "lead": (
            "Stable ASCII concept IRIs connect every Bopomofo symbol to Pinyin, "
            "broad IPA, category, Unicode notation and a Traditional Chinese example."
        ),
        "badges": (
            "37 symbols",
            "3 top concepts",
            "Equivalent RDF formats",
            "SHACL validated",
        ),
        "language": "繁體中文",
        "data": "Open data",
        "downloads": "Download the vocabulary",
        "download_text": (
            "All three RDF serializations describe the same graph. The separate SHACL "
            "file defines structural constraints, while DCAT/VoID metadata records "
            "checksums, sizes and graph statistics."
        ),
        "model": "Graph model",
        "model_text": (
            "The concept scheme has three top concepts: initials, medials and finals. "
            "Each symbol is a SKOS Concept with one English and one Traditional Chinese "
            "preferred label, a typed Unicode notation and exactly one broader category."
        ),
        "model_items": (
            "21 initials, 3 medials and 13 finals",
            "Stable hash IRIs based on Unicode code points",
            "Pinyin, broad IPA and example fields",
            "Bidirectional broader / narrower relationships",
            "No accounts, tracking, analytics or runtime APIs",
        ),
        "query": "Example SPARQL query",
        "query_text": "List every symbol with its Pinyin and broad IPA value:",
        "preview": "Preview all 37 symbol concepts",
        "symbol": "Symbol",
        "category": "Category",
        "pinyin": "Pinyin",
        "ipa": "IPA",
        "example": "Example",
        "sources": "Standards and provenance",
        "source_text": (
            "The vocabulary is generated from the site's open 37-symbol reference. "
            "SKOS structure follows the W3C recommendation; code points follow Unicode. "
            "External sources do not endorse this independent vocabulary."
        ),
        "source_dataset": "View the source dataset",
        "skos": "W3C SKOS Reference",
        "unicode": "Unicode Bopomofo chart",
        "license": "License and reuse",
        "license_text": (
            "The original vocabulary structure and metadata are reusable under CC BY "
            "4.0 with attribution to Lumi Apps - iOS App Guide. External standards and "
            "source materials retain their own terms."
        ),
        "privacy": "Machine-readable without tracking",
        "privacy_text": (
            "Every artifact is a static UTF-8 file. It contains no learner data, "
            "cookies, executable JavaScript, accounts or runtime network calls."
        ),
        "faq": "Questions",
        "faqs": (
            (
                "What is SKOS?",
                "SKOS is a W3C model for publishing taxonomies, controlled vocabularies "
                "and other knowledge organization systems as RDF.",
            ),
            (
                "Do the JSON-LD, Turtle and N-Triples files contain the same data?",
                "Yes. Automated graph-isomorphism checks verify that all three "
                "serializations contain the same RDF triples.",
            ),
            (
                "How are the concept IRIs kept stable?",
                "Each symbol uses its uppercase Unicode code point in an ASCII hash IRI, "
                "for example #u3105 for ㄅ.",
            ),
            (
                "Is this an official government vocabulary?",
                "No. It is an independent open-data vocabulary that cites official "
                "references for verification.",
            ),
        ),
        "app_title": "Optional game-based iPhone practice",
        "app_text": (
            "Lumi Bopomofo provides a separate on-device way to practise Zhuyin through "
            "short activities. The linked-data vocabulary remains free and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": "Independent linked open data for Bopomofo education and research.",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音符號 SKOS 詞彙｜37 符號 Linked Open Data",
        "description": (
            "免費下載完整 37 注音符號 SKOS 詞彙，提供 JSON-LD、Turtle、"
            "N-Triples、SHACL 與 DCAT/VoID 中繼資料。"
        ),
        "eyebrow": "Linked Open Data · SKOS · CC BY 4.0",
        "lead": (
            "以穩定 ASCII concept IRI 連結每個注音符號的漢語拼音、寬式 IPA、"
            "分類、Unicode notation 與繁體中文例字。"
        ),
        "badges": (
            "37 個符號",
            "3 個頂層概念",
            "等價 RDF 格式",
            "SHACL 驗證",
        ),
        "language": "English",
        "data": "開放資料",
        "downloads": "下載詞彙",
        "download_text": (
            "三種 RDF serialization 描述完全相同的 graph；獨立 SHACL 檔定義"
            "結構約束，DCAT/VoID 中繼資料則記錄校驗碼、檔案大小與 graph 統計。"
        ),
        "model": "Graph 模型",
        "model_text": (
            "Concept scheme 以聲母、介音與韻母為三個頂層概念。每個符號都是 "
            "SKOS Concept，具有英語及繁中 prefLabel、具型別的 Unicode notation，"
            "並且只連到一個 broader 分類。"
        ),
        "model_items": (
            "21 個聲母、3 個介音與 13 個韻母",
            "以 Unicode code point 建立穩定 hash IRI",
            "漢語拼音、寬式 IPA 與例字欄位",
            "雙向 broader / narrower 關係",
            "免帳號、無追蹤、無分析、無執行期 API",
        ),
        "query": "SPARQL 查詢範例",
        "query_text": "列出每個符號及其漢語拼音與寬式 IPA：",
        "preview": "預覽全部 37 個符號概念",
        "symbol": "符號",
        "category": "分類",
        "pinyin": "漢語拼音",
        "ipa": "IPA",
        "example": "例字",
        "sources": "標準與資料來源",
        "source_text": (
            "本詞彙由本站開放的 37 符號參考資料自動產生；SKOS 結構依 W3C "
            "Recommendation，code point 依 Unicode。外部來源不為本獨立詞彙背書。"
        ),
        "source_dataset": "查看來源資料集",
        "skos": "W3C SKOS Reference",
        "unicode": "Unicode 注音符號表",
        "license": "授權與再利用",
        "license_text": (
            "原創詞彙結構與中繼資料採 CC BY 4.0；標示 Lumi Apps - iOS App Guide "
            "後即可再利用。外部標準與來源資料仍依各自條款使用。"
        ),
        "privacy": "機器可讀且不追蹤",
        "privacy_text": (
            "所有 artifact 都是靜態 UTF-8 檔案，不含學習者資料、Cookie、可執行 "
            "JavaScript、帳號或執行期網路呼叫。"
        ),
        "faq": "常見問題",
        "faqs": (
            (
                "什麼是 SKOS？",
                "SKOS 是 W3C 用來把分類法、受控詞彙及其他知識組織系統發布成 "
                "RDF 的標準模型。",
            ),
            (
                "JSON-LD、Turtle 與 N-Triples 的資料相同嗎？",
                "相同。自動 graph-isomorphism 檢查會確認三種 serialization "
                "包含完全相同的 RDF triples。",
            ),
            (
                "Concept IRI 如何保持穩定？",
                "每個符號使用大寫 Unicode code point 建立 ASCII hash IRI；"
                "例如 ㄅ 使用 #u3105。",
            ),
            (
                "這是政府官方詞彙嗎？",
                "不是。這是獨立開放資料詞彙，並連結官方資料供查核。",
            ),
        ),
        "app_title": "選用的 iPhone 遊戲化練習",
        "app_text": (
            "Lumi 注音星球提供另一種在裝置上以短活動練習注音的方式；"
            "Linked Open Data 詞彙仍維持免費且獨立。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "提供注音教育與研究使用的獨立 Linked Open Data。",
    },
}


@dataclass(frozen=True)
class RDFObject:
    kind: str
    value: str
    language: str | None = None
    datatype: str | None = None


Triple = tuple[str, str, RDFObject]


def iri(value: str) -> RDFObject:
    return RDFObject("iri", value)


def literal(
    value: str,
    *,
    language: str | None = None,
    datatype: str | None = None,
) -> RDFObject:
    return RDFObject("literal", value, language, datatype)


def page_url(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}data/{SLUG}.html"


def artifact_url(filename: str) -> str:
    return f"{SITE}/data/{filename}"


def concept_uri(symbol: str) -> str:
    return f"{VOCAB_NS}u{ord(symbol):04X}"


def category_uri(category: str) -> str:
    return f"{VOCAB_NS}{CATEGORIES[category]['id']}"


def is_app_public(pages: Path = PAGES) -> bool:
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _add(
    triples: list[Triple],
    subject: str,
    predicate: str,
    obj: RDFObject,
) -> None:
    triples.append((subject, predicate, obj))


def build_triples(modified: str) -> list[Triple]:
    triples: list[Triple] = []
    _add(triples, SCHEME_URI, RDF_TYPE, iri(SKOS_SCHEME))
    _add(triples, SCHEME_URI, RDF_TYPE, iri(f"{SCHEMA}DefinedTermSet"))
    for value, language in (
        ("Bopomofo (Zhuyin) 37-Symbol Vocabulary", "en"),
        ("注音符號 37 符號詞彙", "zh-Hant"),
    ):
        _add(
            triples,
            SCHEME_URI,
            SKOS_PREF_LABEL,
            literal(value, language=language),
        )
        _add(
            triples,
            SCHEME_URI,
            f"{DCTERMS}title",
            literal(value, language=language),
        )
    for value, language in (
        (
            "A bilingual SKOS concept scheme for all 37 Bopomofo symbols, "
            "including Pinyin, broad IPA, Unicode notation and example words.",
            "en",
        ),
        (
            "完整涵蓋 37 個注音符號的雙語 SKOS concept scheme，包含漢語拼音、"
            "寬式 IPA、Unicode notation 與例字。",
            "zh-Hant",
        ),
    ):
        _add(
            triples,
            SCHEME_URI,
            f"{DCTERMS}description",
            literal(value, language=language),
        )
    _add(triples, SCHEME_URI, f"{DCTERMS}creator", iri(ORG_URI))
    _add(triples, SCHEME_URI, f"{DCTERMS}license", iri(LICENSE))
    _add(triples, SCHEME_URI, f"{DCTERMS}source", iri(SOURCE_DATASET))
    _add(triples, SCHEME_URI, f"{DCTERMS}source", iri(MOE_HANDBOOK))
    _add(triples, SCHEME_URI, f"{DCTERMS}source", iri(UNICODE_CHART))
    _add(triples, SCHEME_URI, f"{DCTERMS}conformsTo", iri(SKOS_REFERENCE))
    _add(
        triples,
        SCHEME_URI,
        f"{DCTERMS}created",
        literal(INITIAL_DATE, datatype=f"{XSD}date"),
    )
    _add(
        triples,
        SCHEME_URI,
        f"{DCTERMS}modified",
        literal(modified, datatype=f"{XSD}date"),
    )
    _add(
        triples,
        SCHEME_URI,
        f"{SCHEMA}numberOfItems",
        literal(str(len(ZHUYIN)), datatype=f"{XSD}integer"),
    )

    _add(triples, ORG_URI, RDF_TYPE, iri(f"{SCHEMA}Organization"))
    _add(
        triples,
        ORG_URI,
        f"{SCHEMA}name",
        literal("Lumi Apps - iOS App Guide"),
    )

    property_labels = {
        "pinyin": ("Hanyu Pinyin", "漢語拼音"),
        "ipa": ("broad IPA", "寬式 IPA"),
        "exampleCharacter": ("example character", "例字"),
        "examplePinyin": ("example Pinyin", "例字拼音"),
        "exampleMeaning": ("example meaning", "例字英文意思"),
    }
    for key, property_uri in PROPERTIES.items():
        _add(triples, property_uri, RDF_TYPE, iri(RDF_PROPERTY))
        _add(
            triples,
            property_uri,
            RDFS_LABEL,
            literal(property_labels[key][0], language="en"),
        )
        _add(
            triples,
            property_uri,
            RDFS_LABEL,
            literal(property_labels[key][1], language="zh-Hant"),
        )
        _add(triples, property_uri, RDFS_DOMAIN, iri(SKOS_CONCEPT))
        _add(triples, property_uri, RDFS_RANGE, iri(RDFS_LITERAL))

    records_by_category = defaultdict(list)
    for record in ZHUYIN:
        records_by_category[record[2]].append(record)

    for category, category_copy in CATEGORIES.items():
        uri = category_uri(category)
        _add(triples, SCHEME_URI, SKOS_HAS_TOP, iri(uri))
        _add(triples, uri, RDF_TYPE, iri(SKOS_CONCEPT))
        _add(
            triples,
            uri,
            SKOS_PREF_LABEL,
            literal(category_copy["en"], language="en"),
        )
        _add(
            triples,
            uri,
            SKOS_PREF_LABEL,
            literal(category_copy["zh-Hant"], language="zh-Hant"),
        )
        _add(
            triples,
            uri,
            SKOS_DEFINITION,
            literal(category_copy["definition_en"], language="en"),
        )
        _add(
            triples,
            uri,
            SKOS_DEFINITION,
            literal(category_copy["definition_zh"], language="zh-Hant"),
        )
        _add(
            triples,
            uri,
            SKOS_NOTATION,
            literal(category, datatype=f"{XSD}string"),
        )
        _add(triples, uri, SKOS_IN_SCHEME, iri(SCHEME_URI))
        _add(triples, uri, SKOS_TOP_OF, iri(SCHEME_URI))
        for record in records_by_category[category]:
            _add(triples, uri, SKOS_NARROWER, iri(concept_uri(record[0])))

    category_zh = {"initial": "聲母", "medial": "介音", "final": "韻母"}
    category_en = {"initial": "initial", "medial": "medial", "final": "final"}
    for symbol, pinyin, category, character, example_pinyin, meaning in ZHUYIN:
        uri = concept_uri(symbol)
        notation = f"U+{ord(symbol):04X}"
        ipa_value = ZHUYIN_IPA[symbol]
        _add(triples, uri, RDF_TYPE, iri(SKOS_CONCEPT))
        _add(triples, uri, RDF_TYPE, iri(f"{SCHEMA}DefinedTerm"))
        _add(
            triples,
            uri,
            SKOS_PREF_LABEL,
            literal(f"Bopomofo symbol {symbol}", language="en"),
        )
        _add(
            triples,
            uri,
            SKOS_PREF_LABEL,
            literal(symbol, language="zh-Hant"),
        )
        for label in (part.strip() for part in pinyin.split("/")):
            _add(
                triples,
                uri,
                SKOS_ALT_LABEL,
                literal(label, language="zh-Latn-pinyin"),
            )
        _add(
            triples,
            uri,
            SKOS_DEFINITION,
            literal(
                f"The Zhuyin {category_en[category]} {symbol}, corresponding to "
                f"Hanyu Pinyin {pinyin} and broad IPA [{ipa_value}]. Example: "
                f"{character} ({example_pinyin}), {meaning}.",
                language="en",
            ),
        )
        _add(
            triples,
            uri,
            SKOS_DEFINITION,
            literal(
                f"注音{category_zh[category]} {symbol}，對應漢語拼音 {pinyin} 與"
                f"寬式 IPA [{ipa_value}]；例字：{character}（{example_pinyin}）。",
                language="zh-Hant",
            ),
        )
        _add(
            triples,
            uri,
            SKOS_NOTATION,
            literal(notation, datatype=f"{XSD}string"),
        )
        _add(triples, uri, SKOS_IN_SCHEME, iri(SCHEME_URI))
        _add(triples, uri, SKOS_BROADER, iri(category_uri(category)))
        _add(triples, uri, f"{DCTERMS}identifier", literal(notation))
        _add(triples, uri, f"{SCHEMA}termCode", literal(notation))
        _add(
            triples,
            uri,
            PROPERTIES["pinyin"],
            literal(pinyin, language="zh-Latn-pinyin"),
        )
        _add(triples, uri, PROPERTIES["ipa"], literal(ipa_value))
        _add(
            triples,
            uri,
            PROPERTIES["exampleCharacter"],
            literal(character, language="zh-Hant"),
        )
        _add(
            triples,
            uri,
            PROPERTIES["examplePinyin"],
            literal(example_pinyin, language="zh-Latn-pinyin"),
        )
        _add(
            triples,
            uri,
            PROPERTIES["exampleMeaning"],
            literal(meaning, language="en"),
        )
    validate_triples(triples)
    return triples


def _objects_for(
    triples: list[Triple],
    subject: str,
    predicate: str,
) -> list[RDFObject]:
    return [
        obj
        for triple_subject, triple_predicate, obj in triples
        if triple_subject == subject and triple_predicate == predicate
    ]


def validate_triples(triples: list[Triple]) -> None:
    if len(triples) != len(set(triples)):
        raise ValueError("SKOS graph contains duplicate triples")
    expected_symbols = {concept_uri(record[0]) for record in ZHUYIN}
    symbol_subjects = {
        subject
        for subject, predicate, _ in triples
        if predicate == PROPERTIES["pinyin"]
    }
    if symbol_subjects != expected_symbols or len(symbol_subjects) != 37:
        raise ValueError("SKOS graph must contain exactly the canonical 37 symbols")
    expected_categories = {category_uri(category) for category in CATEGORIES}
    top_concepts = {
        obj.value for obj in _objects_for(triples, SCHEME_URI, SKOS_HAS_TOP)
    }
    if top_concepts != expected_categories:
        raise ValueError("SKOS scheme must expose exactly three top concepts")
    types = defaultdict(set)
    for subject, predicate, obj in triples:
        if predicate == RDF_TYPE and obj.kind == "iri":
            types[subject].add(obj.value)
    if any(
        SKOS_SCHEME in subject_types and SKOS_CONCEPT in subject_types
        for subject_types in types.values()
    ):
        raise ValueError("SKOS S9 forbids a resource being Scheme and Concept")
    if any(
        SKOS_COLLECTION in subject_types
        and (
            SKOS_CONCEPT in subject_types
            or SKOS_SCHEME in subject_types
        )
        for subject_types in types.values()
    ):
        raise ValueError("SKOS S37 makes Collection disjoint from Concept and Scheme")
    for subject in types:
        labels = {
            predicate: {
                (obj.value, obj.language)
                for obj in _objects_for(triples, subject, predicate)
            }
            for predicate in (
                SKOS_PREF_LABEL,
                SKOS_ALT_LABEL,
                f"{SKOS}hiddenLabel",
            )
        }
        if any(
            labels[left] & labels[right]
            for left, right in (
                (SKOS_PREF_LABEL, SKOS_ALT_LABEL),
                (SKOS_PREF_LABEL, f"{SKOS}hiddenLabel"),
                (SKOS_ALT_LABEL, f"{SKOS}hiddenLabel"),
            )
        ):
            raise ValueError(f"SKOS S13 label properties overlap: {subject}")
        preferred = _objects_for(triples, subject, SKOS_PREF_LABEL)
        languages = [obj.language or "" for obj in preferred]
        if len(languages) != len(set(languages)):
            raise ValueError(f"SKOS S14 repeats a preferred-label language: {subject}")
        related = {
            obj.value for obj in _objects_for(triples, subject, SKOS_RELATED)
        }
        broader_transitive = {
            obj.value
            for obj in _objects_for(
                triples,
                subject,
                SKOS_BROADER_TRANSITIVE,
            )
        }
        if related & broader_transitive:
            raise ValueError(f"SKOS S27 relation properties overlap: {subject}")
        exact = {
            obj.value for obj in _objects_for(triples, subject, SKOS_EXACT_MATCH)
        }
        broad_or_related = {
            obj.value
            for predicate in (SKOS_BROAD_MATCH, SKOS_RELATED_MATCH)
            for obj in _objects_for(triples, subject, predicate)
        }
        if exact & broad_or_related:
            raise ValueError(f"SKOS S46 mapping properties overlap: {subject}")
    for record in ZHUYIN:
        symbol = record[0]
        subject = concept_uri(symbol)
        preferred = _objects_for(triples, subject, SKOS_PREF_LABEL)
        if {obj.language for obj in preferred} != {"en", "zh-Hant"}:
            raise ValueError(f"SKOS preferred labels are incomplete: {symbol}")
        if len(preferred) != len({obj.language for obj in preferred}):
            raise ValueError(f"SKOS preferred labels repeat a language: {symbol}")
        broader = _objects_for(triples, subject, SKOS_BROADER)
        if broader != [iri(category_uri(record[2]))]:
            raise ValueError(f"SKOS broader category mismatch: {symbol}")
        notation = _objects_for(triples, subject, SKOS_NOTATION)
        expected_notation = f"U+{ord(symbol):04X}"
        if notation != [literal(expected_notation, datatype=f"{XSD}string")]:
            raise ValueError(f"SKOS Unicode notation mismatch: {symbol}")
        required = {
            PROPERTIES["pinyin"]: record[1],
            PROPERTIES["ipa"]: ZHUYIN_IPA[symbol],
            PROPERTIES["exampleCharacter"]: record[3],
            PROPERTIES["examplePinyin"]: record[4],
            PROPERTIES["exampleMeaning"]: record[5],
        }
        for predicate, value in required.items():
            objects = _objects_for(triples, subject, predicate)
            if len(objects) != 1 or objects[0].value != value:
                raise ValueError(f"SKOS field mismatch for {symbol}: {predicate}")
    for category in CATEGORIES:
        subject = category_uri(category)
        narrower = {
            obj.value for obj in _objects_for(triples, subject, SKOS_NARROWER)
        }
        expected = {
            concept_uri(record[0]) for record in ZHUYIN if record[2] == category
        }
        if narrower != expected:
            raise ValueError(f"SKOS narrower members mismatch: {category}")
        if _objects_for(triples, subject, SKOS_TOP_OF) != [iri(SCHEME_URI)]:
            raise ValueError(f"SKOS topConceptOf mismatch: {category}")
    encoded = repr(triples)
    for forbidden in ("apps.apple.com", APP_ID, APP_NAME, "SoftwareApplication"):
        if forbidden in encoded:
            raise ValueError(f"SKOS graph must remain app-independent: {forbidden}")


def _compact_iri(value: str, *, turtle: bool = False) -> str:
    for prefix, namespace in PREFIXES.items():
        if value.startswith(namespace):
            local = value[len(namespace) :]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", local):
                return f"{prefix}:{local}"
    return f"<{value}>" if turtle else value


def _escape_literal(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return "".join(
        f"\\u{ord(character):04X}"
        if ord(character) < 0x20 and character not in "\n\r\t"
        else character
        for character in escaped
    )


def _turtle_object(obj: RDFObject, *, compact: bool) -> str:
    if obj.kind == "iri":
        return _compact_iri(obj.value, turtle=True) if compact else f"<{obj.value}>"
    rendered = f'"{_escape_literal(obj.value)}"'
    if obj.language:
        return f"{rendered}@{obj.language}"
    if obj.datatype:
        datatype = (
            _compact_iri(obj.datatype, turtle=True)
            if compact
            else f"<{obj.datatype}>"
        )
        return f"{rendered}^^{datatype}"
    return rendered


def render_turtle(triples: list[Triple]) -> str:
    prefix_lines = "\n".join(
        f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in PREFIXES.items()
    )
    grouped: dict[str, dict[str, list[RDFObject]]] = {}
    for subject, predicate, obj in triples:
        grouped.setdefault(subject, {}).setdefault(predicate, []).append(obj)
    blocks = []
    for subject, predicates in grouped.items():
        rows = []
        for predicate, objects in predicates.items():
            predicate_term = (
                "a"
                if predicate == RDF_TYPE
                else _compact_iri(predicate, turtle=True)
            )
            rows.append(
                f"{predicate_term} "
                + ", ".join(
                    _turtle_object(obj, compact=True) for obj in objects
                )
            )
        blocks.append(
            f"{_compact_iri(subject, turtle=True)}\n    "
            + " ;\n    ".join(rows)
            + " ."
        )
    return f"{prefix_lines}\n\n" + "\n\n".join(blocks) + "\n"


def render_ntriples(triples: list[Triple]) -> str:
    rows = []
    for subject, predicate, obj in triples:
        rows.append(
            f"<{subject}> <{predicate}> {_turtle_object(obj, compact=False)} ."
        )
    return "\n".join(rows) + "\n"


def _jsonld_object(obj: RDFObject) -> dict:
    if obj.kind == "iri":
        return {"@id": _compact_iri(obj.value)}
    rendered = {"@value": obj.value}
    if obj.language:
        rendered["@language"] = obj.language
    if obj.datatype:
        rendered["@type"] = _compact_iri(obj.datatype)
    return rendered


def render_jsonld(triples: list[Triple]) -> str:
    grouped: dict[str, dict[str, list[RDFObject]]] = {}
    for subject, predicate, obj in triples:
        grouped.setdefault(subject, {}).setdefault(predicate, []).append(obj)
    graph = []
    for subject, predicates in grouped.items():
        node: dict = {"@id": _compact_iri(subject)}
        for predicate, objects in predicates.items():
            if predicate == RDF_TYPE:
                node["@type"] = [_compact_iri(obj.value) for obj in objects]
            else:
                node[_compact_iri(predicate)] = [
                    _jsonld_object(obj) for obj in objects
                ]
        graph.append(node)
    return (
        json.dumps(
            {"@context": JSONLD_CONTEXT, "@graph": graph},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def render_shapes() -> str:
    return f"""@prefix rdf: <{RDF}> .
@prefix xsd: <{XSD}> .
@prefix skos: <{SKOS}> .
@prefix dcterms: <{DCTERMS}> .
@prefix sh: <{SH}> .
@prefix zhuyin: <{VOCAB_NS}> .

zhuyin:SchemeShape a sh:NodeShape ;
    sh:targetNode zhuyin:scheme ;
    sh:not [ sh:class skos:Concept ] ;
    sh:not [ sh:class skos:Collection ] ;
    sh:property [
        sh:path rdf:type ;
        sh:hasValue skos:ConceptScheme
    ] ;
    sh:property [
        sh:path skos:hasTopConcept ;
        sh:minCount 3 ;
        sh:maxCount 3 ;
        sh:in ( zhuyin:initials zhuyin:medials zhuyin:finals )
    ] ;
    sh:property [
        sh:path dcterms:license ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:nodeKind sh:IRI
    ] ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:minCount 2 ;
        sh:maxCount 2 ;
        sh:uniqueLang true ;
        sh:languageIn ( "en" "zh-Hant" )
    ] .

zhuyin:CategoryShape a sh:NodeShape ;
    sh:targetObjectsOf skos:broader ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:minCount 2 ;
        sh:maxCount 2 ;
        sh:uniqueLang true ;
        sh:languageIn ( "en" "zh-Hant" )
    ] ;
    sh:property [
        sh:path skos:inScheme ;
        sh:hasValue zhuyin:scheme ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] ;
    sh:property [
        sh:path skos:narrower ;
        sh:minCount 1 ;
        sh:nodeKind sh:IRI
    ] .

zhuyin:SymbolShape a sh:NodeShape ;
    sh:targetSubjectsOf zhuyin:pinyin ;
    sh:property [
        sh:path rdf:type ;
        sh:hasValue skos:Concept
    ] ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:minCount 2 ;
        sh:maxCount 2 ;
        sh:uniqueLang true ;
        sh:languageIn ( "en" "zh-Hant" )
    ] ;
    sh:property [
        sh:path skos:notation ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:pattern "^U\\\\+[0-9A-F]{{4}}$"
    ] ;
    sh:property [
        sh:path skos:inScheme ;
        sh:hasValue zhuyin:scheme ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] ;
    sh:property [
        sh:path skos:broader ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:in ( zhuyin:initials zhuyin:medials zhuyin:finals )
    ] ;
    sh:property [ sh:path zhuyin:pinyin ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path zhuyin:ipa ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path zhuyin:exampleCharacter ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path zhuyin:examplePinyin ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path zhuyin:exampleMeaning ; sh:minCount 1 ; sh:maxCount 1 ] .

zhuyin:SkosLabelIntegrityShape a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:not [ sh:class skos:Collection ] ;
    sh:sparql [
        sh:message "SKOS S13: label properties must be pairwise disjoint."@en ;
        sh:select \"\"\"
            SELECT $this WHERE {{
                {{ $this skos:prefLabel ?label ; skos:altLabel ?label . }}
                UNION
                {{ $this skos:prefLabel ?label ; skos:hiddenLabel ?label . }}
                UNION
                {{ $this skos:altLabel ?label ; skos:hiddenLabel ?label . }}
            }}
        \"\"\"
    ] ;
    sh:sparql [
        sh:message "SKOS S27: related and broaderTransitive must be disjoint."@en ;
        sh:select \"\"\"
            SELECT $this WHERE {{
                $this skos:related ?target ;
                      skos:broaderTransitive ?target .
            }}
        \"\"\"
    ] ;
    sh:sparql [
        sh:message "SKOS S46: exactMatch must be disjoint from broadMatch and relatedMatch."@en ;
        sh:select \"\"\"
            SELECT $this WHERE {{
                {{ $this skos:exactMatch ?target ; skos:broadMatch ?target . }}
                UNION
                {{ $this skos:exactMatch ?target ; skos:relatedMatch ?target . }}
            }}
        \"\"\"
    ] .
"""


def make_graph_artifacts(
    modified: str,
) -> tuple[list[Triple], dict[str, dict]]:
    triples = build_triples(modified)
    contents = {
        "jsonld": render_jsonld(triples),
        "turtle": render_turtle(triples),
        "ntriples": render_ntriples(triples),
        "shacl": render_shapes(),
    }
    artifacts = {}
    for key, spec in ARTIFACT_SPECS.items():
        content = contents[key]
        data = content.encode("utf-8")
        artifacts[key] = {
            **spec,
            "url": artifact_url(spec["filename"]),
            "content": content,
            "bytes": data,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    validate_graph_artifacts(artifacts)
    return triples, artifacts


def validate_graph_artifacts(artifacts: dict[str, dict]) -> None:
    for key, artifact in artifacts.items():
        content = artifact["content"]
        if content.startswith("\ufeff"):
            raise ValueError(f"{key} artifact must be UTF-8 without a BOM")
        for forbidden in (
            "apps.apple.com",
            APP_ID,
            APP_NAME,
            "SoftwareApplication",
        ):
            if forbidden in content:
                raise ValueError(
                    f"Linked-data artifacts must remain app-independent: {forbidden}"
                )
    jsonld = json.loads(artifacts["jsonld"]["content"])
    if jsonld.get("@context") != JSONLD_CONTEXT or not jsonld.get("@graph"):
        raise ValueError("JSON-LD vocabulary requires a local context and graph")
    for symbol, *_ in ZHUYIN:
        expected = f"zhuyin:u{ord(symbol):04X}"
        if expected not in artifacts["jsonld"]["content"]:
            raise ValueError(f"JSON-LD vocabulary is missing {symbol}")
        if expected not in artifacts["turtle"]["content"]:
            raise ValueError(f"Turtle vocabulary is missing {symbol}")
        if concept_uri(symbol) not in artifacts["ntriples"]["content"]:
            raise ValueError(f"N-Triples vocabulary is missing {symbol}")


def metadata_graph(
    triples: list[Triple],
    artifacts: dict[str, dict],
    modified: str,
) -> dict:
    distributions = []
    distribution_refs = []
    for key, artifact in artifacts.items():
        distribution_id = f"{DATASET_URI}-{key}"
        distribution_refs.append({"@id": distribution_id})
        distributions.append(
            {
                "@id": distribution_id,
                "@type": "dcat:Distribution",
                "dcterms:title": artifact["format"],
                "dcterms:format": {"@id": artifact["format_iri"]},
                "dcat:accessURL": {"@id": LANDING_URL},
                "dcat:downloadURL": {"@id": artifact["url"]},
                "dcat:mediaType": artifact["media_type"],
                "dcat:byteSize": len(artifact["bytes"]),
                "schema:sha256": artifact["sha256"],
            }
        )
    data_dumps = [
        {"@id": artifacts[key]["url"]}
        for key in ("jsonld", "turtle", "ntriples")
    ]
    dataset = {
        "@id": DATASET_URI,
        "@type": ["dcat:Dataset", "void:Dataset", "schema:Dataset"],
        "dcterms:title": [
            {"@value": COPY["en"]["title"], "@language": "en"},
            {"@value": COPY["zh-Hant"]["title"], "@language": "zh-Hant"},
        ],
        "dcterms:description": [
            {"@value": COPY["en"]["description"], "@language": "en"},
            {
                "@value": COPY["zh-Hant"]["description"],
                "@language": "zh-Hant",
            },
        ],
        "dcterms:created": INITIAL_DATE,
        "dcterms:modified": modified,
        "dcterms:creator": {"@id": ORG_URI},
        "dcterms:license": {"@id": LICENSE},
        "dcterms:source": [
            {"@id": SOURCE_DATASET},
            {"@id": MOE_HANDBOOK},
            {"@id": UNICODE_CHART},
        ],
        "dcterms:conformsTo": [
            {"@id": SKOS_REFERENCE},
            {"@id": JSON_LD_REFERENCE},
            {"@id": DCAT_REFERENCE},
            {"@id": VOID_REFERENCE},
            {"@id": SHACL_REFERENCE},
        ],
        "dcterms:language": ["en", "zh-Hant", "zh-Latn-pinyin"],
        "dcat:landingPage": {"@id": LANDING_URL},
        "dcat:distribution": distribution_refs,
        "dcat:keyword": [
            "Bopomofo",
            "Zhuyin",
            "注音符號",
            "SKOS",
            "linked open data",
            "Mandarin phonetics",
        ],
        "void:uriSpace": VOCAB_NS,
        "void:triples": len(triples),
        "void:entities": len(
            {
                subject
                for subject, _, _ in triples
                if subject.startswith(VOCAB_NS)
            }
        ),
        "void:uriRegexPattern": f"^{re.escape(VOCAB_NS)}",
        "void:classPartition": {
            "@type": "void:Dataset",
            "void:class": {"@id": SKOS_CONCEPT},
            "void:entities": len(
                {
                    subject
                    for subject, predicate, obj in triples
                    if predicate == RDF_TYPE
                    and obj == iri(SKOS_CONCEPT)
                }
            ),
        },
        "void:properties": len({predicate for _, predicate, _ in triples}),
        "void:classes": len(
            {
                obj.value
                for _, predicate, obj in triples
                if predicate == RDF_TYPE and obj.kind == "iri"
            }
        ),
        "void:vocabulary": [
            {"@id": SKOS},
            {"@id": DCTERMS},
            {"@id": SCHEMA},
        ],
        "void:exampleResource": {"@id": concept_uri("ㄅ")},
        "void:dataDump": data_dumps,
        "schema:numberOfItems": len(ZHUYIN),
    }
    return {
        "@context": {
            "@version": 1.1,
            "dcterms": DCTERMS,
            "dcat": DCAT,
            "void": VOID,
            "schema": SCHEMA,
        },
        "@graph": [dataset, *distributions],
    }


def validate_metadata(
    metadata: dict,
    triples: list[Triple],
    artifacts: dict[str, dict],
) -> None:
    encoded = json.dumps(metadata, ensure_ascii=False)
    for forbidden in (
        "apps.apple.com",
        APP_ID,
        APP_NAME,
        "SoftwareApplication",
    ):
        if forbidden in encoded:
            raise ValueError(
                f"Vocabulary metadata must remain app-independent: {forbidden}"
            )
    graph = metadata.get("@graph", [])
    dataset = next(
        (node for node in graph if node.get("@id") == DATASET_URI),
        None,
    )
    if not dataset:
        raise ValueError("Vocabulary metadata is missing its DCAT/VoID dataset")
    if dataset.get("void:triples") != len(triples):
        raise ValueError("VoID triple count does not match the vocabulary graph")
    distributions = {
        node["@id"]: node
        for node in graph
        if node.get("@type") == "dcat:Distribution"
    }
    if len(distributions) != len(artifacts):
        raise ValueError("DCAT metadata must describe every downloadable artifact")
    for key, artifact in artifacts.items():
        distribution = distributions[f"{DATASET_URI}-{key}"]
        if (
            distribution.get("dcat:downloadURL", {}).get("@id")
            != artifact["url"]
            or distribution.get("dcat:byteSize") != len(artifact["bytes"])
            or distribution.get("schema:sha256") != artifact["sha256"]
        ):
            raise ValueError(f"DCAT distribution mismatch: {key}")


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _artifact_record(
    key: str,
    content: str,
    *,
    filename: str,
    media_type: str,
    format_name: str,
    label_en: str,
    label_zh: str,
) -> dict:
    data = content.encode("utf-8")
    return {
        "key": key,
        "filename": filename,
        "media_type": media_type,
        "format": format_name,
        "label_en": label_en,
        "label_zh": label_zh,
        "url": artifact_url(filename),
        "content": content,
        "bytes": data,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def write_versioned_artifacts(
    data_directory: Path,
) -> tuple[list[Triple], dict[str, dict], str]:
    metadata_path = data_directory / METADATA_FILENAME
    existing_metadata = (
        metadata_path.read_text(encoding="utf-8")
        if metadata_path.exists()
        else ""
    )
    match = CONTENT_MODIFIED_RE.search(existing_metadata)
    prior_date = match.group(1) if match else INITIAL_DATE

    def candidates(modified: str) -> tuple[list[Triple], dict[str, dict]]:
        triples, artifacts = make_graph_artifacts(modified)
        metadata_content = _json(metadata_graph(triples, artifacts, modified))
        metadata = _artifact_record(
            "metadata",
            metadata_content,
            filename=METADATA_FILENAME,
            media_type="application/ld+json",
            format_name="DCAT 3 + VoID metadata",
            label_en="DCAT / VoID metadata",
            label_zh="DCAT / VoID 中繼資料",
        )
        validate_metadata(
            json.loads(metadata_content),
            triples,
            artifacts,
        )
        return triples, {**artifacts, "metadata": metadata}

    triples, downloads = candidates(prior_date)
    unchanged = all(
        (data_directory / artifact["filename"]).exists()
        and (data_directory / artifact["filename"]).read_text(encoding="utf-8")
        == artifact["content"]
        for artifact in downloads.values()
    )
    if unchanged:
        return triples, downloads, prior_date

    triples, downloads = candidates(TODAY)
    for artifact in downloads.values():
        write_text_if_changed(
            data_directory / artifact["filename"],
            artifact["content"],
        )
    return triples, downloads, TODAY


def _page_schema(
    locale: str,
    downloads: dict[str, dict],
    modified: str,
    app_public: bool,
) -> dict:
    copy = COPY[locale]
    distributions = [
        {
            "@type": "DataDownload",
            "name": artifact["format"],
            "contentUrl": artifact["url"],
            "encodingFormat": artifact["media_type"],
            "contentSize": f"{len(artifact['bytes'])} bytes",
            "sha256": artifact["sha256"],
        }
        for artifact in downloads.values()
    ]
    graph = [
        {
            "@type": "WebPage",
            "@id": page_url(locale),
            "name": copy["title"],
            "description": copy["description"],
            "url": page_url(locale),
            "inLanguage": locale,
            "dateModified": modified,
            "mainEntity": {"@id": SCHEME_URI},
        },
        {
            "@type": ["Dataset", "DefinedTermSet"],
            "@id": SCHEME_URI,
            "name": copy["title"],
            "description": copy["description"],
            "url": page_url(locale),
            "datePublished": INITIAL_DATE,
            "dateModified": modified,
            "inLanguage": ["en", "zh-Hant"],
            "isAccessibleForFree": True,
            "license": LICENSE,
            "numberOfItems": len(ZHUYIN),
            "isBasedOn": SOURCE_DATASET,
            "conformsTo": [
                SKOS_REFERENCE,
                JSON_LD_REFERENCE,
                SHACL_REFERENCE,
            ],
            "distribution": distributions,
            "hasDefinedTerm": [
                {"@id": concept_uri(record[0]), "@type": "DefinedTerm"}
                for record in ZHUYIN
            ],
        },
        {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": answer,
                    },
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
                "url": appstore_url(APP_KEY, f"iag_skos_{locale.lower()}"),
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


def _preview_rows(locale: str) -> str:
    category_key = "en" if locale == "en" else "zh-Hant"
    return "".join(
        "<tr><td class=\"symbol\">{symbol}</td><td>{category}</td>"
        "<td>{pinyin}</td><td>[{ipa}]</td><td>{character} ({example})</td></tr>".format(
            symbol=html.escape(record[0]),
            category=html.escape(CATEGORIES[record[2]][category_key]),
            pinyin=html.escape(record[1]),
            ipa=html.escape(ZHUYIN_IPA[record[0]]),
            character=html.escape(record[3]),
            example=html.escape(record[4]),
        )
        for record in ZHUYIN
    )


def render_page(
    locale: str,
    downloads: dict[str, dict],
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    model_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["model_items"]
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
                appstore_url(APP_KEY, f"iag_skos_{locale.lower()}"),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    sparql = (
        f"PREFIX skos: <{SKOS}>\n"
        f"PREFIX zhuyin: <{VOCAB_NS}>\n\n"
        "SELECT ?symbol ?pinyin ?ipa WHERE {\n"
        "  ?concept a skos:Concept ;\n"
        "           skos:prefLabel ?symbol ;\n"
        "           zhuyin:pinyin ?pinyin ;\n"
        "           zhuyin:ipa ?ipa .\n"
        '  FILTER(LANG(?symbol) = "zh-Hant")\n'
        "}\nORDER BY ?concept"
    )
    schema = json.dumps(
        _page_schema(locale, downloads, modified, app_public),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    alternate_links = "".join(
        '<link rel="alternate" type="{media}" href="{url}">\n'.format(
            media=html.escape(downloads[key]["media_type"], quote=True),
            url=html.escape(downloads[key]["url"], quote=True),
        )
        for key in ("jsonld", "turtle", "ntriples")
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
{alternate_links}<link rel="describedby" type="application/ld+json" href="{html.escape(METADATA_URL, quote=True)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
<meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
<meta property="og:url" content="{html.escape(page_url(locale), quote=True)}">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#142033;--sub:#596579;--line:#dce4ee;--paper:#fff;--wash:#f4f7fb;--brand:#3158c8;--soft:#edf3ff;--mint:#e8f7f1;--code:#101827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1060px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.92);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:750;text-decoration:none;white-space:nowrap}}.links{{display:flex;gap:18px}}.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:960px}}.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:830px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}}
main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,55,98,.06)}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub);margin:8px 0}}.downloads{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.notice{{background:var(--mint);border-radius:14px;padding:14px 16px;color:#315c50}}ol,ul{{padding-left:24px}}li{{margin:8px 0}}pre{{background:var(--code);color:#dbe8ff;border-radius:16px;padding:18px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.symbol{{font-size:25px;font-weight:850}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:700;white-space:nowrap}}details{{border-top:1px solid var(--line);padding:12px 0}}summary{{cursor:pointer;font-weight:800}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:800;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#edf3ff)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:700px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{SITE}/data/">{html.escape(copy['data'])}</a><nav class="links"><a href="{html.escape(page_url(other_locale), quote=True)}">{html.escape(copy['language'])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, downloads)}</div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['model'])}</h2><p>{html.escape(copy['model_text'])}</p><ul>{model_items}</ul></article><article class="panel"><h2>{html.escape(copy['query'])}</h2><p>{html.escape(copy['query_text'])}</p><pre>{html.escape(sparql)}</pre></article></section>
<section class="wrap panel"><h2>{html.escape(copy['preview'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['symbol'])}</th><th>{html.escape(copy['category'])}</th><th>{html.escape(copy['pinyin'])}</th><th>{html.escape(copy['ipa'])}</th><th>{html.escape(copy['example'])}</th></tr></thead><tbody>{_preview_rows(locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['source_text'])}</p><div class="sources"><a href="{SOURCE_PAGE}">{html.escape(copy['source_dataset'])}</a><a href="{SKOS_REFERENCE}" rel="noopener">{html.escape(copy['skos'])}</a><a href="{UNICODE_CHART}" rel="noopener">{html.escape(copy['unicode'])}</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a><h2>{html.escape(copy['privacy'])}</h2><p>{html.escape(copy['privacy_text'])}</p></article></section>
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
    target = f"{SITE}/data/{SLUG}.html"
    card = (
        f'<a class="item" href="{target}">'
        "<h2>Bopomofo SKOS linked-data vocabulary</h2>"
        "<p>All 37 Zhuyin symbols as JSON-LD, Turtle and N-Triples with "
        "SHACL and DCAT/VoID metadata.</p>"
        '<span class="tag">Linked data · EN + zh-Hant · CC BY 4.0</span></a>'
    )
    existing = re.compile(
        r'<a class="item" href="'
        + re.escape(target)
        + r'">.*?</a>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    source_card = re.search(
        r'<a class="item" href="'
        + re.escape(f"{SITE}/data/zhuyin-bopomofo.html")
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
    distribution = []
    for artifact in (downloads or {}).values():
        distribution.append(
            {
                "@type": "DataDownload",
                "name": artifact["format"],
                "encodingFormat": artifact["media_type"],
                "contentUrl": artifact["url"],
            }
        )
    vocabulary_dataset = {
        "@type": ["Dataset", "DefinedTermSet"],
        "name": COPY["en"]["title"],
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "license": LICENSE,
        "distribution": distribution,
    }
    source_position = next(
        (
            offset + 1
            for offset, dataset in enumerate(datasets)
            if dataset.get("url") == SOURCE_PAGE
        ),
        0,
    )
    datasets.insert(source_position, vocabulary_dataset)
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
    _triples, downloads, artifact_modified = write_versioned_artifacts(
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
                downloads,
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    update_data_index(pages, downloads)
    write_text_if_changed(
        pages / "sitemap_vocab.xml",
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
        print(f"Zhuyin SKOS resource -> {output}")


if __name__ == "__main__":
    main()
