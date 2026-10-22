#!/usr/bin/env python3
"""Publish a static LDES 1.0 + TREE view for the Bopomofo symbol dataset."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Literal, RDF, URIRef
from rdflib.compare import isomorphic


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
    LICENSE,
    SITE,
)


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
VERSION = "1.0.0"
PACKAGE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-ldes"
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
STREAM_JSONLD_FILENAME = "bopomofo-event-stream.jsonld"
STREAM_TURTLE_FILENAME = "bopomofo-event-stream.ttl"
SHAPE_FILENAME = "bopomofo-event-member.shacl.ttl"
README_FILENAME = "README.txt"
LICENSE_FILENAME = "LICENSE.txt"
CHECKSUM_FILENAME = "checksums-sha256.txt"
METADATA_FILENAME = "metadata.jsonld"
BUNDLE_FILENAME = "bopomofo-37-symbols-ldes-tree.zip"
STREAM_URL = f"{PACKAGE_URL}{STREAM_JSONLD_FILENAME}"
STREAM_TURTLE_URL = f"{PACKAGE_URL}{STREAM_TURTLE_FILENAME}"
SHAPE_URL = f"{PACKAGE_URL}{SHAPE_FILENAME}"
METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
SOURCE_CSV_PATH = Path("data") / "zhuyin-bopomofo-ml-dataset.csv"
SOURCE_CSV_URL = f"{SITE}/{SOURCE_CSV_PATH.as_posix()}"
ORE_AGGREGATION_URI = (
    f"{SITE}/data/packages/zhuyin-bopomofo-oai-ore/"
    "bopomofo-resource-map.ore.rdf#aggregation"
)
SITEMAP_PATH = Path("sitemap_ldes.xml")
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"
CARD_START = "<!-- ldes-card:start -->"
CARD_END = "<!-- ldes-card:end -->"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

LDES_SPEC = (
    "https://semiceu.github.io/LinkedDataEventStreams/releases/1.0.0/"
)
LDES_VOCABULARY = f"{LDES_SPEC}vocabulary.html"
LDES_SERVER_PRIMER = f"{LDES_SPEC}server-primer.html"
TREE_SPEC = "https://w3id.org/tree/specification"
SHACL_SPEC = "https://www.w3.org/TR/shacl/"
JSONLD_SPEC = "https://www.w3.org/TR/json-ld11/"

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"
DCTERMS_NS = "http://purl.org/dc/terms/"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
SH_NS = "http://www.w3.org/ns/shacl#"
PROV_NS = "http://www.w3.org/ns/prov#"
SCHEMA_NS = "https://schema.org/"
DCAT_NS = "http://www.w3.org/ns/dcat#"
LDES_NS = "https://w3id.org/ldes#"
TREE_NS = "https://w3id.org/tree#"
ZHUYIN_NS = f"{SITE}/data/zhuyin-bopomofo-vocabulary.html#"
MEMBER_CLASS = f"{PACKAGE_URL}#BopomofoSymbolVersion"
PUBLISHER_URI = f"{PACKAGE_URL}#publisher"
RETENTION_POLICY_URI = f"{STREAM_URL}#retention"

NAMESPACES = {
    "rdf": RDF_NS,
    "rdfs": RDFS_NS,
    "xsd": XSD_NS,
    "dcterms": DCTERMS_NS,
    "skos": SKOS_NS,
    "sh": SH_NS,
    "prov": PROV_NS,
    "schema": SCHEMA_NS,
    "dcat": DCAT_NS,
    "ldes": LDES_NS,
    "tree": TREE_NS,
    "zhuyin": ZHUYIN_NS,
}

FORBIDDEN = (
    APP_ID,
    APP_NAME,
    "apps.apple.com",
    "SoftwareApplication",
    "official LDES endorsement",
    "external harvesting confirmed",
)


@dataclass(frozen=True)
class RDFValue:
    value: str
    kind: str = "literal"
    language: str | None = None
    datatype: str | None = None


@dataclass(frozen=True)
class NodeSpec:
    slug: str
    start: int
    stop: int

    @property
    def filename(self) -> str:
        return f"nodes/{self.slug}.jsonld"

    @property
    def url(self) -> str:
        return f"{PACKAGE_URL}{self.filename}"


Triple = tuple[str, str, RDFValue]
NODE_SPECS = (
    NodeSpec("page-001", 0, 13),
    NodeSpec("page-002", 13, 25),
    NodeSpec("page-003", 25, 37),
)


COPY = {
    "en": {
        "lang": "en",
        "title": "Static LDES 1.0 event stream for all 37 Bopomofo symbols",
        "description": (
            "Replicate a complete app-independent Bopomofo snapshot through "
            "LDES 1.0 and TREE using 37 immutable version members."
        ),
        "eyebrow": "LDES 1.0 · TREE hypermedia · Immutable RDF events",
        "lead": (
            "The stable entry point links three bounded JSON-LD nodes containing "
            "one immutable first-version event for every canonical Bopomofo symbol."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "download": "Download or start consuming",
        "download_text": (
            "Start with the JSON-LD event-stream IRI. Turtle is a static overview "
            "that links clients to the canonical JSON-LD root."
        ),
        "stream": "Canonical JSON-LD entry point",
        "turtle": "Turtle discovery overview",
        "shape": "SHACL member shape",
        "bundle": "Deterministic offline bundle",
        "checksums": "SHA-256 checksum list",
        "model": "What a client can rely on",
        "model_items": (
            "One ldes:EventStream with exactly one tree:view root.",
            "Thirty-seven immutable member IRIs linked with tree:member.",
            "dcterms:created is the chronological ldes:timestampPath.",
            "dcterms:isVersionOf links each event to its stable SKOS concept.",
            "Three immutable TREE nodes use paired inclusive-lower and exclusive-upper time bounds.",
            "Every node embeds its members and an inline JSON-LD context.",
        ),
        "nodes": "Immutable TREE nodes",
        "node_text": (
            "Clients follow the root relations and can prune by the published "
            "time intervals. Each node states ldes:immutable true."
        ),
        "validate": "Validation",
        "validate_text": (
            "Parse the entry point and every node as RDF, verify the SHACL paths, "
            "then compare the ZIP and source files with the published SHA-256 list."
        ),
        "limits": "Scope and limits",
        "limits_text": (
            "This is a publisher-authored static snapshot, not a live write API, "
            "registry listing, external replication proof, certification or "
            "community endorsement. GitHub Pages does not provide custom content "
            "negotiation; clients should follow the explicit JSON-LD links."
        ),
        "app_title": "Optional on-device practice",
        "app_text": (
            "The event stream, nodes, shape and bundle work without an app. If "
            "currently available, Lumi Bopomofo is an optional private practice layer."
        ),
        "app_cta": "View Lumi Bopomofo",
        "footer": (
            "CC BY 4.0 publisher metadata · Static files · No account · "
            "No claim of external harvesting"
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "完整 37 注音符號的靜態 LDES 1.0 事件流",
        "description": (
            "透過 LDES 1.0 與 TREE 複製完整且不依賴 App 的注音快照，"
            "包含 37 個 immutable version member。"
        ),
        "eyebrow": "LDES 1.0 · TREE hypermedia · Immutable RDF events",
        "lead": (
            "穩定 entry point 連至三個有時間邊界的 JSON-LD node；每個標準注音符號"
            "都有一筆 immutable 第一版事件。"
        ),
        "back": "開放資料",
        "language": "English",
        "download": "下載或開始讀取",
        "download_text": (
            "請從 JSON-LD event-stream IRI 開始；Turtle 是靜態 discovery overview，"
            "會將 client 導向 canonical JSON-LD root。"
        ),
        "stream": "Canonical JSON-LD entry point",
        "turtle": "Turtle discovery overview",
        "shape": "SHACL member shape",
        "bundle": "Deterministic 離線套件",
        "checksums": "SHA-256 checksum 清單",
        "model": "Client 可依賴的結構",
        "model_items": (
            "一個 ldes:EventStream，且只有一個 tree:view root。",
            "37 個 immutable member IRI，全部以 tree:member 連結。",
            "dcterms:created 是 chronological ldes:timestampPath。",
            "dcterms:isVersionOf 將每筆事件連至穩定 SKOS concept。",
            "三個 immutable TREE node 使用成對的含下界與不含上界時間範圍。",
            "每個 node 內嵌 member 與 inline JSON-LD context。",
        ),
        "nodes": "Immutable TREE nodes",
        "node_text": (
            "Client 可沿 root relation 走訪，並依已發布的時間範圍剪枝；"
            "每個 node 都明確標示 ldes:immutable true。"
        ),
        "validate": "驗證方式",
        "validate_text": (
            "將 entry point 與每個 node 解析為 RDF，檢查 SHACL path，"
            "再以 SHA-256 清單比對 ZIP 與來源檔案。"
        ),
        "limits": "範圍與限制",
        "limits_text": (
            "這是發布者自行建立的靜態快照，不是即時寫入 API、registry 登錄、"
            "外部複製證明、認證或社群背書。GitHub Pages 不提供自訂 content "
            "negotiation；client 應沿明確的 JSON-LD 連結讀取。"
        ),
        "app_title": "選用的裝置端練習",
        "app_text": (
            "事件流、node、shape 與 bundle 都不需要 App；若目前仍公開，"
            "Lumi 注音星球僅是選用的隱私練習層。"
        ),
        "app_cta": "查看 Lumi 注音星球",
        "footer": (
            "CC BY 4.0 發布者 metadata · 靜態檔案 · 免帳號 · "
            "不宣稱已被外部採集"
        ),
    },
}


def iri(value: str) -> RDFValue:
    return RDFValue(value, kind="iri")


def literal(
    value: str,
    *,
    language: str | None = None,
    datatype: str | None = None,
) -> RDFValue:
    return RDFValue(value, language=language, datatype=datatype)


def _add(
    triples: list[Triple],
    subject: str,
    predicate: str,
    *objects: RDFValue,
) -> None:
    triples.extend((subject, predicate, obj) for obj in objects)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _timestamp(value: str) -> dt.datetime:
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        raise ValueError(f"Invalid UTC timestamp: {value}")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(dt.timezone.utc)


def _timestamp_text(value: dt.datetime) -> str:
    return (
        value.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _new_timestamp(prior: str | None = None) -> str:
    value = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    minimum = dt.datetime.fromisoformat(
        f"{INITIAL_DATE}T00:00:00+00:00"
    )
    value = max(value, minimum)
    if prior is not None and value <= _timestamp(prior):
        value = _timestamp(prior) + dt.timedelta(seconds=1)
    return _timestamp_text(value)


def load_records(pages: Path) -> list[dict[str, str]]:
    path = pages / SOURCE_CSV_PATH
    if not path.is_file():
        raise FileNotFoundError(f"LDES source CSV is missing: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    if len(records) != 37:
        raise ValueError("LDES source CSV must contain exactly 37 rows")
    expected = list(range(1, 38))
    if [int(record["order"]) for record in records] != expected:
        raise ValueError("LDES source CSV order must be exactly 1 through 37")
    if len({record["concept_uri"] for record in records}) != 37:
        raise ValueError("LDES source concepts must be unique")
    for record in records:
        expected_id = f"u{ord(record['symbol']):04X}"
        if record["symbol_id"].lower() != expected_id.lower():
            raise ValueError(f"LDES symbol identifier mismatch: {record}")
        if record["unicode"] != f"U+{ord(record['symbol']):04X}":
            raise ValueError(f"LDES Unicode notation mismatch: {record}")
    return records


def event_timestamp(index: int) -> str:
    base = dt.datetime.fromisoformat(
        f"{INITIAL_DATE}T00:00:00+00:00"
    )
    return _timestamp_text(base + dt.timedelta(minutes=index))


def event_uri(node: NodeSpec, record: dict[str, str]) -> str:
    return f"{node.url}#event-{record['symbol_id'].lower()}-v1"


def entry_triples(modified: str, include_turtle_overview: bool = False) -> list[Triple]:
    _timestamp(modified)
    triples: list[Triple] = []
    _add(
        triples,
        STREAM_URL,
        f"{RDF_NS}type",
        iri(f"{LDES_NS}EventStream"),
        iri(f"{TREE_NS}Node"),
    )
    _add(
        triples,
        STREAM_URL,
        f"{DCTERMS_NS}title",
        literal("Bopomofo 37-symbol version event stream", language="en"),
        literal("注音 37 符號版本事件流", language="zh-Hant"),
    )
    _add(
        triples,
        STREAM_URL,
        f"{DCTERMS_NS}description",
        literal(
            "A complete static LDES view with 37 immutable first-version "
            "members partitioned across three TREE nodes.",
            language="en",
        ),
        literal(
            "完整靜態 LDES view，將 37 筆 immutable 第一版 member "
            "分布於三個 TREE node。",
            language="zh-Hant",
        ),
    )
    _add(
        triples,
        STREAM_URL,
        f"{DCTERMS_NS}issued",
        literal(f"{INITIAL_DATE}T00:00:00Z", datatype=f"{XSD_NS}dateTime"),
    )
    _add(
        triples,
        STREAM_URL,
        f"{DCTERMS_NS}modified",
        literal(modified, datatype=f"{XSD_NS}dateTime"),
    )
    _add(triples, STREAM_URL, f"{DCTERMS_NS}publisher", iri(PUBLISHER_URI))
    _add(triples, STREAM_URL, f"{DCTERMS_NS}license", iri(LICENSE))
    _add(
        triples,
        STREAM_URL,
        f"{DCTERMS_NS}conformsTo",
        iri(LDES_SPEC),
        iri(TREE_SPEC),
    )
    _add(triples, STREAM_URL, f"{DCTERMS_NS}hasFormat", iri(STREAM_TURTLE_URL))
    _add(triples, STREAM_URL, f"{DCTERMS_NS}isPartOf", iri(ORE_AGGREGATION_URI))
    _add(
        triples,
        STREAM_URL,
        f"{LDES_NS}timestampPath",
        iri(f"{DCTERMS_NS}created"),
    )
    _add(
        triples,
        STREAM_URL,
        f"{LDES_NS}versionOfPath",
        iri(f"{DCTERMS_NS}isVersionOf"),
    )
    _add(
        triples,
        STREAM_URL,
        f"{LDES_NS}versionCreatePath",
        iri(f"{RDF_NS}type"),
    )
    _add(
        triples,
        STREAM_URL,
        f"{LDES_NS}versionCreateObject",
        iri(MEMBER_CLASS),
    )
    _add(triples, STREAM_URL, f"{TREE_NS}shape", iri(SHAPE_URL))
    _add(triples, STREAM_URL, f"{TREE_NS}view", iri(STREAM_URL))
    _add(
        triples,
        STREAM_URL,
        f"{LDES_NS}retentionPolicy",
        iri(RETENTION_POLICY_URI),
    )
    _add(
        triples,
        RETENTION_POLICY_URI,
        f"{RDF_NS}type",
        iri(f"{LDES_NS}RetentionPolicy"),
    )
    _add(
        triples,
        RETENTION_POLICY_URI,
        f"{LDES_NS}startingFrom",
        literal(event_timestamp(0), datatype=f"{XSD_NS}dateTime"),
    )
    _add(
        triples,
        PUBLISHER_URI,
        f"{RDF_NS}type",
        iri(f"{PROV_NS}Organization"),
    )
    _add(
        triples,
        PUBLISHER_URI,
        f"{SCHEMA_NS}name",
        literal("iOS App Guide Open Resources"),
    )
    for node in NODE_SPECS:
        lower = event_timestamp(node.start)
        upper = event_timestamp(node.stop)
        for suffix, relation_type, boundary in (
            ("lower", "GreaterThanOrEqualToRelation", lower),
            ("upper", "LessThanRelation", upper),
        ):
            relation = f"{STREAM_URL}#to-{node.slug}-{suffix}"
            _add(
                triples,
                STREAM_URL,
                f"{TREE_NS}relation",
                iri(relation),
            )
            _add(
                triples,
                relation,
                f"{RDF_NS}type",
                iri(f"{TREE_NS}{relation_type}"),
            )
            _add(triples, relation, f"{TREE_NS}node", iri(node.url))
            _add(
                triples,
                relation,
                f"{TREE_NS}path",
                iri(f"{DCTERMS_NS}created"),
            )
            _add(
                triples,
                relation,
                f"{TREE_NS}value",
                literal(boundary, datatype=f"{XSD_NS}dateTime"),
            )
            _add(
                triples,
                relation,
                f"{TREE_NS}remainingItems",
                literal(
                    str(node.stop - node.start),
                    datatype=f"{XSD_NS}integer",
                ),
            )
    if include_turtle_overview:
        _add(
            triples,
            STREAM_TURTLE_URL,
            f"{RDF_NS}type",
            iri(f"{DCTERMS_NS}BibliographicResource"),
        )
        _add(
            triples,
            STREAM_TURTLE_URL,
            f"{DCTERMS_NS}isFormatOf",
            iri(STREAM_URL),
        )
        _add(
            triples,
            STREAM_TURTLE_URL,
            f"{TREE_NS}view",
            iri(STREAM_URL),
        )
    return sorted(
        triples,
        key=lambda item: (
            item[0],
            item[1],
            item[2].kind,
            item[2].value,
            item[2].language or "",
            item[2].datatype or "",
        ),
    )


def node_triples(
    node: NodeSpec,
    records: list[dict[str, str]],
) -> list[Triple]:
    triples: list[Triple] = []
    _add(triples, node.url, f"{RDF_NS}type", iri(f"{TREE_NS}Node"))
    _add(
        triples,
        node.url,
        f"{LDES_NS}immutable",
        literal("true", datatype=f"{XSD_NS}boolean"),
    )
    _add(triples, node.url, f"{DCTERMS_NS}isPartOf", iri(STREAM_URL))
    for index, record in enumerate(records[node.start : node.stop], node.start):
        event = event_uri(node, record)
        _add(triples, STREAM_URL, f"{TREE_NS}member", iri(event))
        _add(
            triples,
            event,
            f"{RDF_NS}type",
            iri(MEMBER_CLASS),
            iri(f"{PROV_NS}Entity"),
        )
        _add(
            triples,
            event,
            f"{DCTERMS_NS}created",
            literal(event_timestamp(index), datatype=f"{XSD_NS}dateTime"),
        )
        _add(
            triples,
            event,
            f"{DCTERMS_NS}isVersionOf",
            iri(record["concept_uri"]),
        )
        _add(
            triples,
            event,
            f"{DCTERMS_NS}identifier",
            literal(f"{record['symbol_id'].lower()}-v1"),
        )
        _add(triples, event, f"{DCTERMS_NS}source", iri(SOURCE_CSV_URL))
        _add(
            triples,
            event,
            f"{SKOS_NS}prefLabel",
            literal(record["symbol"], language="zh-Hant"),
        )
        _add(
            triples,
            event,
            f"{SKOS_NS}notation",
            literal(record["unicode"], datatype=f"{XSD_NS}string"),
        )
        _add(triples, event, f"{SKOS_NS}broader", iri(record["category_uri"]))
        for field, predicate in (
            ("pinyin", "pinyin"),
            ("ipa", "ipa"),
            ("example_character", "exampleCharacter"),
            ("example_pinyin", "examplePinyin"),
            ("example_meaning_en", "exampleMeaning"),
        ):
            language = "zh-Hant" if field == "example_character" else None
            if field == "example_meaning_en":
                language = "en"
            _add(
                triples,
                event,
                f"{ZHUYIN_NS}{predicate}",
                literal(record[field], language=language),
            )
    return sorted(
        triples,
        key=lambda item: (
            item[0],
            item[1],
            item[2].kind,
            item[2].value,
            item[2].language or "",
            item[2].datatype or "",
        ),
    )


def render_jsonld(triples: list[Triple]) -> bytes:
    grouped: dict[str, dict[str, list[RDFValue]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for subject, predicate, obj in triples:
        grouped[subject][predicate].append(obj)
    graph = []
    for subject in sorted(grouped):
        predicates = grouped[subject]
        item: dict[str, object] = {"@id": subject}
        types = predicates.pop(f"{RDF_NS}type", [])
        if types:
            item["@type"] = [value.value for value in types]
        for predicate in sorted(predicates):
            values = []
            for value in predicates[predicate]:
                if value.kind == "iri":
                    values.append({"@id": value.value})
                else:
                    rendered: dict[str, str] = {"@value": value.value}
                    if value.language:
                        rendered["@language"] = value.language
                    if value.datatype:
                        rendered["@type"] = value.datatype
                    values.append(rendered)
            item[predicate] = values
        graph.append(item)
    document = {
        "@context": NAMESPACES,
        "@graph": graph,
    }
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")


def _turtle_literal(value: RDFValue) -> str:
    rendered = json.dumps(value.value, ensure_ascii=False)
    if value.language:
        return f"{rendered}@{value.language}"
    if value.datatype:
        return f"{rendered}^^<{value.datatype}>"
    return rendered


def render_turtle(triples: list[Triple]) -> bytes:
    prefixes = "\n".join(
        f"@prefix {prefix}: <{namespace}> ."
        for prefix, namespace in NAMESPACES.items()
    )
    rows = []
    for subject, predicate, obj in triples:
        rendered = f"<{obj.value}>" if obj.kind == "iri" else _turtle_literal(obj)
        rows.append(f"<{subject}> <{predicate}> {rendered} .")
    return (f"{prefixes}\n\n" + "\n".join(rows) + "\n").encode("utf-8")


def render_shape() -> bytes:
    text = f"""@prefix sh: <{SH_NS}> .
@prefix rdf: <{RDF_NS}> .
@prefix xsd: <{XSD_NS}> .
@prefix dcterms: <{DCTERMS_NS}> .
@prefix skos: <{SKOS_NS}> .
@prefix zhuyin: <{ZHUYIN_NS}> .

<{SHAPE_URL}#MemberShape>
    a sh:NodeShape ;
    sh:targetClass <{MEMBER_CLASS}> ;
    sh:closed false ;
    sh:property [
        sh:path dcterms:created ;
        sh:datatype xsd:dateTime ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] ;
    sh:property [
        sh:path dcterms:isVersionOf ;
        sh:nodeKind sh:IRI ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:uniqueLang true ;
        sh:minCount 1
    ] ;
    sh:property [
        sh:path skos:notation ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] ;
    sh:property [
        sh:path zhuyin:pinyin ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] ;
    sh:property [
        sh:path zhuyin:ipa ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] .
"""
    return text.encode("utf-8")


def _readme_bytes() -> bytes:
    text = f"""Bopomofo LDES 1.0 + TREE event stream
========================================

Canonical entry point
---------------------
{STREAM_URL}

The entry point is both the ldes:EventStream and the mutable TREE root node.
It has exactly one tree:view pointing to itself and six typed relations: paired
inclusive lower and exclusive upper time bounds for each of three immutable
JSON-LD member nodes.

Member model
------------
- 37 immutable member IRIs
- ldes:timestampPath = dcterms:created
- ldes:versionOfPath = dcterms:isVersionOf
- ldes:versionCreatePath = rdf:type
- ldes:versionCreateObject = {MEMBER_CLASS}
- each event links one stable SKOS concept and carries the canonical CSV fields

Consumption
-----------
1. Dereference {STREAM_JSONLD_FILENAME}.
2. Confirm one tree:view and read the LDES context.
3. Follow each tree:relation/tree:node link that cannot be pruned.
4. Extract objects of tree:member from the event-stream IRI.
5. Verify each member against {SHAPE_FILENAME}.
6. Persist member IRIs so each immutable event is emitted only once.

Static-hosting note
-------------------
The Turtle file is a discovery overview whose tree:view links to the canonical
JSON-LD root. Node pages declare ldes:immutable true inside RDF. This host does
not claim content negotiation or custom Cache-Control headers.

Specifications
--------------
LDES 1.0: {LDES_SPEC}
LDES server primer: {LDES_SERVER_PRIMER}
TREE: {TREE_SPEC}
SHACL: {SHACL_SPEC}

Limits
------
This publisher-authored snapshot does not claim registry listing, external
replication, certification, institutional endorsement or LDES/TREE community
endorsement.

繁體中文
--------
此靜態事件流以三個 immutable JSON-LD node 發布完整 37 個注音符號的第一版
事件。請從 canonical JSON-LD entry point 開始，沿成對時間上下界 relation
走訪 node，檢查 tree:member、dcterms:created、dcterms:isVersionOf 與 SHACL
shape，並使用 checksums-sha256.txt 驗證下載 bytes。
"""
    return text.encode("utf-8")


def _license_bytes() -> bytes:
    return (
        "Bopomofo LDES and TREE publisher metadata\n"
        "Copyright (c) 2026 iOS App Guide Open Resources\n\n"
        "Licensed under the Creative Commons Attribution 4.0 International "
        "License (CC BY 4.0).\n"
        "License: https://creativecommons.org/licenses/by/4.0/\n\n"
        "Attribution: Bopomofo LDES 1.0 + TREE event stream, iOS App Guide "
        "Open Resources.\n\n"
        "The license applies to this publisher-authored metadata and package "
        "documentation. Referenced standards remain under their own terms.\n"
    ).encode("utf-8")


def _checksum_bytes(entries: dict[str, bytes]) -> bytes:
    return (
        "\n".join(f"{_sha256(entries[name])}  {name}" for name in sorted(entries))
        + "\n"
    ).encode("utf-8")


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entries[name])
    return stream.getvalue()


def make_artifacts(
    pages: Path,
    modified: str,
) -> dict[str, bytes]:
    records = load_records(pages)
    core = {
        STREAM_JSONLD_FILENAME: render_jsonld(entry_triples(modified)),
        STREAM_TURTLE_FILENAME: render_turtle(
            entry_triples(modified, include_turtle_overview=True)
        ),
        **{
            node.filename: render_jsonld(node_triples(node, records))
            for node in NODE_SPECS
        },
        SHAPE_FILENAME: render_shape(),
        README_FILENAME: _readme_bytes(),
        LICENSE_FILENAME: _license_bytes(),
    }
    checksums = _checksum_bytes(core)
    zip_entries = {**core, CHECKSUM_FILENAME: checksums}
    artifacts = {
        **zip_entries,
        BUNDLE_FILENAME: _zip_bytes(zip_entries),
    }
    validate_artifacts(pages, artifacts, modified)
    return artifacts


def _graph(data: bytes, format_name: str) -> Graph:
    return Graph().parse(data=data, format=format_name)


def validate_artifacts(
    pages: Path,
    artifacts: dict[str, bytes],
    modified: str,
) -> None:
    records = load_records(pages)
    expected_names = [
        STREAM_JSONLD_FILENAME,
        STREAM_TURTLE_FILENAME,
        *(node.filename for node in NODE_SPECS),
        SHAPE_FILENAME,
        README_FILENAME,
        LICENSE_FILENAME,
        CHECKSUM_FILENAME,
        BUNDLE_FILENAME,
    ]
    if list(artifacts) != expected_names:
        raise ValueError("LDES artifact order or membership is invalid")

    entry_json = _graph(artifacts[STREAM_JSONLD_FILENAME], "json-ld")
    entry_ttl = _graph(artifacts[STREAM_TURTLE_FILENAME], "turtle")
    stream = URIRef(STREAM_URL)
    turtle_overview = URIRef(STREAM_TURTLE_URL)
    turtle_core = Graph()
    for triple in entry_ttl:
        if triple[0] != turtle_overview:
            turtle_core.add(triple)
    if not isomorphic(entry_json, turtle_core):
        raise ValueError("LDES JSON-LD and Turtle entry graphs disagree")
    if (stream, RDF.type, URIRef(f"{LDES_NS}EventStream")) not in entry_json:
        raise ValueError("LDES entry point is not an EventStream")
    if set(entry_json.objects(stream, URIRef(f"{TREE_NS}view"))) != {stream}:
        raise ValueError("LDES entry point must have exactly one self TREE view")
    if set(
        entry_json.objects(stream, URIRef(f"{LDES_NS}timestampPath"))
    ) != {URIRef(f"{DCTERMS_NS}created")}:
        raise ValueError("LDES timestampPath is invalid")
    if set(
        entry_json.objects(stream, URIRef(f"{LDES_NS}versionOfPath"))
    ) != {URIRef(f"{DCTERMS_NS}isVersionOf")}:
        raise ValueError("LDES versionOfPath is invalid")
    if set(
        entry_json.objects(stream, URIRef(f"{TREE_NS}shape"))
    ) != {URIRef(SHAPE_URL)}:
        raise ValueError("LDES member shape link is invalid")
    relations = set(entry_json.objects(stream, URIRef(f"{TREE_NS}relation")))
    if len(relations) != 6:
        raise ValueError("LDES root must expose six bounded TREE relations")
    relation_targets: dict[URIRef, list[URIRef]] = defaultdict(list)
    for relation in relations:
        targets = list(entry_json.objects(relation, URIRef(f"{TREE_NS}node")))
        paths = list(entry_json.objects(relation, URIRef(f"{TREE_NS}path")))
        values = list(entry_json.objects(relation, URIRef(f"{TREE_NS}value")))
        if len(targets) != 1 or paths != [URIRef(f"{DCTERMS_NS}created")]:
            raise ValueError("LDES TREE relation target or path is invalid")
        if len(values) != 1 or values[0].datatype != URIRef(f"{XSD_NS}dateTime"):
            raise ValueError("LDES TREE relation boundary is invalid")
        relation_targets[targets[0]].append(relation)
    if {
        target: len(items) for target, items in relation_targets.items()
    } != {URIRef(node.url): 2 for node in NODE_SPECS}:
        raise ValueError("LDES TREE nodes must each have paired bounds")

    members: set[URIRef] = set()
    timestamps: list[dt.datetime] = []
    by_concept: dict[str, URIRef] = {}
    for node in NODE_SPECS:
        graph = _graph(artifacts[node.filename], "json-ld")
        node_uri = URIRef(node.url)
        if (
            node_uri,
            URIRef(f"{LDES_NS}immutable"),
            Literal(True),
        ) not in graph:
            raise ValueError(f"LDES node is not immutable: {node.filename}")
        node_members = set(graph.objects(stream, URIRef(f"{TREE_NS}member")))
        if len(node_members) != node.stop - node.start:
            raise ValueError(f"LDES node member count is invalid: {node.filename}")
        if members & node_members:
            raise ValueError("LDES member appears in multiple nodes")
        members |= node_members
        for member in node_members:
            if (member, RDF.type, URIRef(MEMBER_CLASS)) not in graph:
                raise ValueError(f"LDES member class is missing: {member}")
            created = list(
                graph.objects(member, URIRef(f"{DCTERMS_NS}created"))
            )
            version_of = list(
                graph.objects(member, URIRef(f"{DCTERMS_NS}isVersionOf"))
            )
            if len(created) != 1 or created[0].datatype != URIRef(
                f"{XSD_NS}dateTime"
            ):
                raise ValueError(f"LDES member timestamp is invalid: {member}")
            if len(version_of) != 1 or not isinstance(version_of[0], URIRef):
                raise ValueError(f"LDES member version target is invalid: {member}")
            timestamps.append(_timestamp(str(created[0])))
            by_concept[str(version_of[0])] = member
    if len(members) != 37 or len(by_concept) != 37:
        raise ValueError("LDES stream must contain 37 unique version members")
    expected_timestamps = {_timestamp(event_timestamp(index)) for index in range(37)}
    if set(timestamps) != expected_timestamps:
        raise ValueError("LDES timestamps must be unique and chronological")
    if set(by_concept) != {record["concept_uri"] for record in records}:
        raise ValueError("LDES member version targets do not match source concepts")

    shape = _graph(artifacts[SHAPE_FILENAME], "turtle")
    shapes = set(
        shape.subjects(
            URIRef(f"{SH_NS}targetClass"),
            URIRef(MEMBER_CLASS),
        )
    )
    if len(shapes) != 1:
        raise ValueError("LDES SHACL member shape is missing")
    expected_checksums = _checksum_bytes(
        {
            name: artifacts[name]
            for name in expected_names
            if name not in {CHECKSUM_FILENAME, BUNDLE_FILENAME}
        }
    )
    if artifacts[CHECKSUM_FILENAME] != expected_checksums:
        raise ValueError("LDES checksum list mismatch")
    with zipfile.ZipFile(io.BytesIO(artifacts[BUNDLE_FILENAME])) as archive:
        expected_zip_names = sorted(expected_names[:-1])
        if archive.namelist() != expected_zip_names:
            raise ValueError("LDES ZIP order or membership is invalid")
        for info in archive.infolist():
            if (
                info.date_time != ZIP_TIMESTAMP
                or info.compress_type != zipfile.ZIP_DEFLATED
                or info.external_attr >> 16 != 0o100644
                or archive.read(info.filename) != artifacts[info.filename]
            ):
                raise ValueError(f"Non-deterministic LDES ZIP entry: {info.filename}")
    for name in expected_names[:-1]:
        text = artifacts[name].decode("utf-8")
        for forbidden in FORBIDDEN:
            if forbidden.lower() in text.lower():
                raise ValueError(f"LDES artifact contains forbidden text: {name}")


def metadata_document(
    artifacts: dict[str, bytes],
    modified: str,
) -> dict:
    distribution = []
    labels = {
        STREAM_JSONLD_FILENAME: (
            "Canonical LDES JSON-LD entry point",
            "application/ld+json",
        ),
        STREAM_TURTLE_FILENAME: (
            "Turtle discovery overview",
            "text/turtle",
        ),
        **{
            node.filename: (
                f"Immutable TREE node {node.slug}",
                "application/ld+json",
            )
            for node in NODE_SPECS
        },
        SHAPE_FILENAME: ("SHACL member shape", "text/turtle"),
        CHECKSUM_FILENAME: ("SHA-256 checksum list", "text/plain"),
        BUNDLE_FILENAME: ("Deterministic offline bundle", "application/zip"),
    }
    for filename, (name, media_type) in labels.items():
        distribution.append(
            {
                "@type": "DataDownload",
                "name": name,
                "contentUrl": f"{PACKAGE_URL}{filename}",
                "encodingFormat": media_type,
                "contentSize": len(artifacts[filename]),
                "sha256": _sha256(artifacts[filename]),
            }
        )
    return {
        "@context": {
            "@vocab": "https://schema.org/",
            "url": {"@type": "@id"},
            "license": {"@type": "@id"},
            "contentUrl": {"@type": "@id"},
            "conformsTo": {"@type": "@id"},
            "isPartOf": {"@type": "@id"},
        },
        "@type": ["Dataset", "LearningResource"],
        "@id": STREAM_URL,
        "identifier": STREAM_URL,
        "name": "Bopomofo LDES 1.0 + TREE event stream",
        "alternateName": "注音 LDES 1.0 與 TREE 事件流",
        "description": COPY["en"]["description"],
        "url": PACKAGE_URL,
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "inLanguage": ["en", "zh-Hant"],
        "isAccessibleForFree": True,
        "license": LICENSE,
        "creator": {
            "@type": "Organization",
            "@id": PUBLISHER_URI,
            "name": "iOS App Guide Open Resources",
        },
        "conformsTo": [
            LDES_SPEC,
            TREE_SPEC,
            JSONLD_SPEC,
            SHACL_SPEC,
        ],
        "isPartOf": ORE_AGGREGATION_URI,
        "numberOfItems": 37,
        "keywords": [
            "Linked Data Event Streams",
            "LDES 1.0",
            "TREE hypermedia",
            "Bopomofo",
            "Zhuyin",
            "immutable RDF events",
        ],
        "distribution": distribution,
    }


def _metadata_bytes(
    artifacts: dict[str, bytes],
    modified: str,
) -> bytes:
    return (
        json.dumps(
            metadata_document(artifacts, modified),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def render_page(
    locale: str,
    artifacts: dict[str, bytes],
    modified: str,
    page_modified: str,
    app_public: bool,
) -> str:
    copy = COPY[locale]
    canonical = PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL
    alternate = ZH_PACKAGE_URL if locale == "en" else PACKAGE_URL
    schema_graph = [
        metadata_document(artifacts, modified),
        {
            "@type": "WebPage",
            "@id": canonical,
            "url": canonical,
            "name": copy["title"],
            "dateModified": page_modified,
            "inLanguage": copy["lang"],
            "mainEntity": {"@id": STREAM_URL},
        },
    ]
    if app_public:
        schema_graph.append(
            {
                "@type": "SoftwareApplication",
                "applicationCategory": "EducationApplication",
                "name": APP_NAME,
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_ldes_{locale.lower()}"),
            }
        )
    downloads = "".join(
        f'<a class="download{" primary" if filename == STREAM_JSONLD_FILENAME else ""}" '
        f'href="{PACKAGE_URL}{filename}"><strong>{html.escape(label)}</strong>'
        f"<span>{len(artifacts[filename]):,} bytes · "
        f"{_sha256(artifacts[filename])[:16]}…</span></a>"
        for filename, label in (
            (STREAM_JSONLD_FILENAME, copy["stream"]),
            (STREAM_TURTLE_FILENAME, copy["turtle"]),
            (SHAPE_FILENAME, copy["shape"]),
            (BUNDLE_FILENAME, copy["bundle"]),
            (CHECKSUM_FILENAME, copy["checksums"]),
        )
    )
    node_links = "".join(
        f'<a class="node" href="{node.url}"><strong>{node.slug}</strong>'
        f"<span>{node.stop - node.start} members · "
        f"{event_timestamp(node.start)} — {event_timestamp(node.stop)}</span></a>"
        for node in NODE_SPECS
    )
    model_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["model_items"]
    )
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel optional"><h2>'
            f'{html.escape(copy["app_title"])}</h2><p>{html.escape(copy["app_text"])}</p>'
            f'<a class="button" href="{appstore_url(APP_KEY, "iag_ldes")}">'
            f'{html.escape(copy["app_cta"])}</a></section>'
        )
    schema = json.dumps(
        {"@context": "https://schema.org", "@graph": schema_graph},
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
<link rel="alternate" hreflang="en" href="{PACKAGE_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_PACKAGE_URL}">
<link rel="alternate" hreflang="x-default" href="{PACKAGE_URL}">
<link rel="alternate" type="application/ld+json" href="{STREAM_URL}">
<link rel="alternate" type="text/turtle" href="{STREAM_TURTLE_URL}">
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#17243d;--muted:#5b6577;--line:#d8e0eb;--paper:#fff;--accent:#4153a6;--soft:#eef0ff}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.65 system-ui,sans-serif;color:var(--ink);background:linear-gradient(180deg,#f2f3ff,#fff)}}a{{color:#34479b}}.wrap{{width:min(1120px,calc(100% - 32px));margin:auto}}header{{padding:18px 0}}nav{{display:flex;justify-content:space-between;gap:12px}}nav a,.button,h1,h2,h3,p,li,span,strong,code{{white-space:nowrap}}p,li,.uri,.download,.node{{overflow-x:auto}}.hero{{padding:48px 0 22px}}.eyebrow{{font-weight:850;color:var(--accent);letter-spacing:.06em;text-transform:uppercase;overflow:auto}}h1{{font-size:clamp(2rem,6vw,3.8rem);line-height:1.04;margin:.2em 0;overflow:auto}}.lead{{font-size:1.12rem;color:var(--muted)}}.badges{{display:flex;gap:8px;overflow:auto}}.badge{{padding:6px 11px;border-radius:999px;background:var(--soft);font-weight:800}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 10px 34px rgba(50,65,145,.07);margin:18px 0;overflow:hidden}}.download,.node{{display:flex;justify-content:space-between;gap:14px;padding:14px 16px;border:1px solid var(--line);border-radius:14px;text-decoration:none;margin:10px 0}}.download span,.node span{{color:var(--muted);font-size:.86rem}}.download.primary{{background:var(--accent);color:#fff;border-color:var(--accent)}}.download.primary span{{color:#eef0ff}}.sources{{display:flex;gap:10px;overflow:auto}}.sources a,.button{{display:inline-block;padding:10px 15px;border-radius:999px;text-decoration:none;font-weight:800;background:var(--soft)}}.button{{background:var(--accent);color:#fff}}.optional{{border-style:dashed}}footer{{padding:32px 0;color:var(--muted);overflow:auto;white-space:nowrap}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.download,.node{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<header class="wrap"><nav><a href="{SITE}/data/">{html.escape(copy['back'])}</a><a href="{alternate}">{html.escape(copy['language'])}</a></nav></header>
<main>
<section class="hero wrap"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges"><span class="badge">LDES 1.0</span><span class="badge">TREE</span><span class="badge">37 immutable members</span><span class="badge">3 nodes</span></div></section>
<section class="wrap panel"><h2>EventStream IRI</h2><p class="uri"><code>{STREAM_URL}</code></p></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['download'])}</h2><p>{html.escape(copy['download_text'])}</p>{downloads}</article><article class="panel"><h2>{html.escape(copy['model'])}</h2><ul>{model_items}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['nodes'])}</h2><p>{html.escape(copy['node_text'])}</p>{node_links}</section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><div class="sources"><a href="{LDES_SPEC}">LDES 1.0</a><a href="{TREE_SPEC}">TREE</a><a href="{SHACL_SPEC}">SHACL</a></div></article><article class="panel"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limits_text'])}</p></article></section>
<div class="wrap">{app_section}</div>
</main>
<footer class="wrap">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def validate_page(page: str, locale: str, app_public: bool) -> None:
    canonical = PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL
    for required in (
        f'<html lang="{COPY[locale]["lang"]}">',
        f'<link rel="canonical" href="{canonical}">',
        STREAM_URL,
        STREAM_TURTLE_URL,
        SHAPE_URL,
        BUNDLE_URL,
        CHECKSUM_URL,
        LDES_SPEC,
        TREE_SPEC,
    ):
        if required not in page:
            raise ValueError(f"LDES landing is missing {required}")
    if ("apps.apple.com" in page) != app_public:
        raise ValueError("LDES optional app CTA does not match public availability")


def _prior_timestamp(metadata_path: Path) -> str | None:
    if not metadata_path.is_file():
        return None
    try:
        value = json.loads(metadata_path.read_text(encoding="utf-8"))["dateModified"]
        _timestamp(value)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Existing LDES metadata is invalid: {metadata_path}") from error
    return value


def _artifacts_changed(package_dir: Path, artifacts: dict[str, bytes]) -> bool:
    return any(
        not (package_dir / name).is_file()
        or (package_dir / name).read_bytes() != content
        for name, content in artifacts.items()
    )


def _write_bytes_if_changed(path: Path, content: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == content:
        return False
    path.write_bytes(content)
    return True


def update_data_index(
    pages: Path,
    artifacts: dict[str, bytes],
    modified: str,
) -> bool:
    index = pages / "data" / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"Data index must exist before LDES: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'{CARD_START}<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo LDES 1.0 + TREE event stream</h2>"
        "<p>Thirty-seven immutable version members across three bounded "
        "JSON-LD TREE nodes.</p>"
        '<span class="tag">LDES 1.0 · TREE · JSON-LD</span></a>'
        f"{CARD_END}"
    )
    updated = re.sub(
        re.escape(CARD_START) + r".*?" + re.escape(CARD_END),
        "",
        text,
        flags=re.DOTALL,
    )
    anchor = re.search(
        r'<a class="item" href="'
        + re.escape(f"{SITE}/data/packages/zhuyin-bopomofo-oai-ore/")
        + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if anchor:
        updated = updated[: anchor.end()] + card + updated[anchor.end() :]
    else:
        footer = updated.find('<p class="foot">')
        if footer < 0:
            raise RuntimeError("data/index.html has no LDES insertion anchor")
        updated = updated[:footer] + card + updated[footer:]

    match = re.search(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        updated,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("data/index.html is missing DataCatalog JSON-LD")
    catalog = json.loads(match.group(2))
    datasets = [
        item for item in catalog.get("dataset", []) if item.get("url") != PACKAGE_URL
    ]
    entry = metadata_document(artifacts, modified)
    position = next(
        (
            offset + 1
            for offset, item in enumerate(datasets)
            if item.get("url")
            == f"{SITE}/data/packages/zhuyin-bopomofo-oai-ore/"
        ),
        len(datasets),
    )
    datasets.insert(position, entry)
    catalog["dataset"] = datasets
    updated = (
        updated[: match.start()]
        + match.group(1)
        + json.dumps(catalog, ensure_ascii=False)
        + match.group(3)
        + updated[match.end() :]
    )
    return write_text_if_changed(index, updated)


def render_sitemap(modified: str, page_modified: dict[str, str]) -> str:
    artifact_names = (
        STREAM_JSONLD_FILENAME,
        STREAM_TURTLE_FILENAME,
        *(node.filename for node in NODE_SPECS),
        SHAPE_FILENAME,
        README_FILENAME,
        LICENSE_FILENAME,
        CHECKSUM_FILENAME,
        METADATA_FILENAME,
        BUNDLE_FILENAME,
    )
    urls = (
        (PACKAGE_URL, page_modified["en"]),
        (ZH_PACKAGE_URL, page_modified["zh-Hant"]),
        *((f"{PACKAGE_URL}{name}", modified[:10]) for name in artifact_names),
    )
    rows = "\n".join(
        f"  <url><loc>{html.escape(url)}</loc><lastmod>{lastmod}</lastmod></url>"
        for url, lastmod in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def _is_app_public(pages: Path) -> bool:
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    package_dir = pages / PACKAGE_PATH
    package_dir.mkdir(parents=True, exist_ok=True)
    prior = _prior_timestamp(package_dir / METADATA_FILENAME)
    modified = prior or _new_timestamp()
    artifacts = make_artifacts(pages, modified)
    if prior is not None:
        for node in NODE_SPECS:
            existing = package_dir / node.filename
            if existing.is_file() and existing.read_bytes() != artifacts[node.filename]:
                raise ValueError(
                    "Published immutable LDES node changed; use new versioned node IRIs"
                )
    if prior is not None and _artifacts_changed(package_dir, artifacts):
        modified = _new_timestamp(prior)
        artifacts = make_artifacts(pages, modified)
    metadata = _metadata_bytes(artifacts, modified)
    for name, content in artifacts.items():
        _write_bytes_if_changed(package_dir / name, content)
    _write_bytes_if_changed(package_dir / METADATA_FILENAME, metadata)

    public = _is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", package_dir / "index.html"),
        ("zh-Hant", pages / "zh-Hant" / PACKAGE_PATH / "index.html"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda changed, locale=locale: render_page(
                locale,
                artifacts,
                modified,
                changed,
                public,
            ),
            INITIAL_DATE,
        )
        validate_page(path.read_text(encoding="utf-8"), locale, public)
    update_data_index(pages, artifacts, modified)
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(modified, page_modified),
    )
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        STREAM_URL,
        STREAM_TURTLE_URL,
        *(node.url for node in NODE_SPECS),
        SHAPE_URL,
        CHECKSUM_URL,
        METADATA_URL,
        BUNDLE_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    urls = build()
    print(f"Published LDES 1.0 + TREE event stream ({len(urls)} URLs)")
    for url in urls:
        print(url)


if __name__ == "__main__":
    main()
