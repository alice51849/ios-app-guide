#!/usr/bin/env python3
"""Publish an OAI-ORE 1.0 Resource Map for the Bopomofo data collection."""

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
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from rdflib import Graph, Literal, Namespace, RDF, URIRef


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
PACKAGE_SLUG = "zhuyin-bopomofo-oai-ore"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"

RDFXML_FILENAME = "bopomofo-resource-map.ore.rdf"
TURTLE_FILENAME = "bopomofo-resource-map.ore.ttl"
JSONLD_FILENAME = "bopomofo-resource-map.ore.jsonld"
README_FILENAME = "README.txt"
LICENSE_FILENAME = "LICENSE.txt"
CHECKSUM_FILENAME = "checksums-sha256.txt"
METADATA_FILENAME = "metadata.jsonld"
BUNDLE_FILENAME = "bopomofo-37-symbols-oai-ore-bundle.zip"

RDFXML_URL = f"{PACKAGE_URL}{RDFXML_FILENAME}"
TURTLE_URL = f"{PACKAGE_URL}{TURTLE_FILENAME}"
JSONLD_URL = f"{PACKAGE_URL}{JSONLD_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
RESOURCE_MAP_URLS = (RDFXML_URL, TURTLE_URL, JSONLD_URL)
AGGREGATION_URI = f"{RDFXML_URL}#aggregation"
CREATOR_URI = f"{PACKAGE_URL}#publisher"

ORE_MODEL = "https://www.openarchives.org/ore/1.0/datamodel"
ORE_VOCABULARY = "https://www.openarchives.org/ore/1.0/vocabulary"
ORE_HTTP = "https://www.openarchives.org/ore/1.0/http"
ORE_RDFXML = "https://www.openarchives.org/ore/1.0/rdfxml"
SITEMAP_PATH = Path("sitemap_ore.xml")
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"
CARD_START = "<!-- oai-ore-card:start -->"
CARD_END = "<!-- oai-ore-card:end -->"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
ORE_NS = "http://www.openarchives.org/ore/terms/"
DCTERMS_NS = "http://purl.org/dc/terms/"
FOAF_NS = "http://xmlns.com/foaf/0.1/"
DCAT_NS = "http://www.w3.org/ns/dcat#"
SPDX_NS = "http://spdx.org/rdf/terms#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"
XML_NS = "http://www.w3.org/XML/1998/namespace"

NAMESPACES = {
    "rdf": RDF_NS,
    "ore": ORE_NS,
    "dcterms": DCTERMS_NS,
    "foaf": FOAF_NS,
    "dcat": DCAT_NS,
    "spdx": SPDX_NS,
    "xsd": XSD_NS,
}

ORE = Namespace(ORE_NS)
DCTERMS = Namespace(DCTERMS_NS)
FOAF = Namespace(FOAF_NS)
DCAT = Namespace(DCAT_NS)
SPDX = Namespace(SPDX_NS)
XSD = Namespace(XSD_NS)


@dataclass(frozen=True)
class SourceSpec:
    path: str
    title: str
    media_type: str


SOURCE_SPECS = (
    SourceSpec(
        "data/zhuyin-bopomofo.json",
        "Canonical 37-symbol Bopomofo JSON",
        "application/json",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "Canonical 37-row Bopomofo CSV",
        "text/csv",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "Equivalent Bopomofo JSON Lines records",
        "text/plain",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        "MLCommons Croissant 1.1 metadata",
        "application/ld+json",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "W3C CSVW metadata",
        "application/csvm+json",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "Bopomofo SKOS vocabulary in JSON-LD",
        "application/ld+json",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-vocabulary.ttl",
        "Bopomofo SKOS vocabulary in Turtle",
        "text/turtle",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-vocabulary.nt",
        "Bopomofo SKOS vocabulary in N-Triples",
        "application/n-triples",
    ),
    SourceSpec(
        "data/zhuyin-bopomofo-vocabulary.shacl.ttl",
        "SHACL validation shapes for the SKOS vocabulary",
        "text/turtle",
    ),
    SourceSpec(
        "data/packages/zhuyin-bopomofo/datapackage.json",
        "Frictionless Data Package 2.0 descriptor",
        "application/json",
    ),
    SourceSpec(
        "data/packages/zhuyin-bopomofo/table-schema.json",
        "Frictionless Table Schema 2.0",
        "application/json",
    ),
    SourceSpec(
        "data/packages/zhuyin-bopomofo/symbols.csv",
        "Frictionless package CSV resource",
        "text/csv",
    ),
    SourceSpec(
        "api/v1/bopomofo-symbols/index.json",
        "Static Bopomofo API collection",
        "application/json",
    ),
    SourceSpec(
        "api/v1/bopomofo-symbols/openapi.json",
        "OpenAPI 3.1 description for the static API",
        "application/vnd.oai.openapi+json;version=3.1",
    ),
    SourceSpec(
        "data/packages/zhuyin-bopomofo-ldes/bopomofo-event-stream.jsonld",
        "Canonical LDES 1.0 JSON-LD event-stream entry point",
        "application/ld+json",
    ),
    SourceSpec(
        "data/packages/zhuyin-bopomofo-ldes/bopomofo-event-stream.ttl",
        "Turtle discovery overview for the LDES event stream",
        "text/turtle",
    ),
)

MAP_SPECS = (
    (
        RDFXML_FILENAME,
        RDFXML_URL,
        "OAI-ORE Resource Map in RDF/XML",
        "application/rdf+xml",
        "xml",
    ),
    (
        TURTLE_FILENAME,
        TURTLE_URL,
        "OAI-ORE Resource Map in Turtle",
        "text/turtle",
        "turtle",
    ),
    (
        JSONLD_FILENAME,
        JSONLD_URL,
        "OAI-ORE Resource Map in JSON-LD",
        "application/ld+json",
        "json-ld",
    ),
)

FORBIDDEN = (
    APP_ID,
    APP_NAME,
    "apps.apple.com",
    "official OAI endorsement",
    "repository ingest confirmed",
)

COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo OAI-ORE 1.0 Resource Map",
        "description": (
            "A repository-readable OAI-ORE aggregation of sixteen reusable "
            "resources for the complete 37-symbol Bopomofo dataset."
        ),
        "eyebrow": "OAI-ORE 1.0 · Compound object · Linked data",
        "lead": (
            "Expose the boundary of one compound data object through "
            "RDF/XML, Turtle and JSON-LD Resource Maps with byte-level fixity."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "downloads": "Resource Maps",
        "download_text": (
            "The RDF/XML map is the hash-URI authority. Turtle and JSON-LD "
            "describe the same Aggregation Graph from distinct Resource Map URIs."
        ),
        "bundle": "Deterministic OAI-ORE bundle",
        "rdfxml": "RDF/XML Resource Map",
        "turtle": "Turtle Resource Map",
        "jsonld": "JSON-LD Resource Map",
        "checksums": "SHA-256 checksums",
        "metadata": "Package metadata",
        "model": "Aggregation contract",
        "model_items": (
            "One Resource Map describes exactly one Aggregation.",
            "The Aggregation enumerates sixteen protocol-based resource URIs.",
            "Every resource records media type, byte size and SHA-256.",
            "All three maps expose the same ore:aggregates boundary.",
            "The RDF/XML map plus #aggregation implements ORE's static hash-URI pattern.",
        ),
        "inventory": "Aggregated resources",
        "resource": "Resource",
        "format": "Media type",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "validate": "Validation",
        "validate_text": (
            "Each serialization is parsed as RDF, checked against ORE's "
            "structural constraints, compared at the Aggregation Graph level "
            "and verified against the published source bytes."
        ),
        "limits": "Scope and limits",
        "limits_text": (
            "This is a publisher-authored static Resource Map. It does not "
            "claim OAI endorsement, external repository ingest, DOI assignment, "
            "third-party certification, content negotiation or Atom conformance."
        ),
        "sources": "Specifications",
        "sources_text": (
            "The graph follows the OAI-ORE 1.0 Abstract Data Model, vocabulary, "
            "RDF/XML profile and no-server hash-URI implementation guidance."
        ),
        "app_title": "Optional practice layer",
        "app_text": (
            "After a repository or data tool has used the open resources, "
            "families can optionally continue Bopomofo practice on iPhone or iPad."
        ),
        "app_cta": "View Lumi Bopomofo",
        "footer": (
            "Publisher-authored open metadata. OAI-ORE and related names remain "
            "the property of their respective standards organizations."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音 OAI-ORE 1.0 資源聚合圖",
        "description": (
            "可供典藏庫讀取的 OAI-ORE 聚合圖，收錄完整 37 個注音符號資料集的 "
            "16 項可重用資源。"
        ),
        "eyebrow": "OAI-ORE 1.0 · 複合物件 · Linked Data",
        "lead": (
            "以 RDF/XML、Turtle 與 JSON-LD Resource Map 清楚界定同一個 "
            "複合資料物件，並提供 byte 層級 fixity。"
        ),
        "language": "English",
        "back": "開放資料",
        "downloads": "Resource Map",
        "download_text": (
            "RDF/XML map 是 hash URI 的權威入口；Turtle 與 JSON-LD 使用不同 "
            "Resource Map URI 描述完全相同的 Aggregation Graph。"
        ),
        "bundle": "Deterministic OAI-ORE 套件",
        "rdfxml": "RDF/XML Resource Map",
        "turtle": "Turtle Resource Map",
        "jsonld": "JSON-LD Resource Map",
        "checksums": "SHA-256 checksums",
        "metadata": "套件 metadata",
        "model": "聚合契約",
        "model_items": (
            "每個 Resource Map 恰好描述一個 Aggregation。",
            "Aggregation 列出 16 個使用 protocol-based URI 的資源。",
            "每個資源都記錄 media type、byte size 與 SHA-256。",
            "三份 map 公開完全相同的 ore:aggregates 邊界。",
            "RDF/XML map 加上 #aggregation，採用 ORE 靜態 hash URI 模式。",
        ),
        "inventory": "聚合資源",
        "resource": "資源",
        "format": "Media type",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "validate": "驗證方式",
        "validate_text": (
            "每種 serialization 都會解析成 RDF，檢查 ORE 結構限制、比對 "
            "Aggregation Graph，並逐一核對已發布來源檔的 bytes。"
        ),
        "limits": "範圍與限制",
        "limits_text": (
            "這是發布者自行建立的靜態 Resource Map，不宣稱獲 OAI 背書、已由外部 "
            "典藏庫匯入、取得 DOI、通過第三方認證、支援 content negotiation 或 "
            "符合 Atom serialization。"
        ),
        "sources": "規格來源",
        "sources_text": (
            "圖形依循 OAI-ORE 1.0 Abstract Data Model、vocabulary、RDF/XML "
            "profile 與不需伺服器設定的 hash URI 實作指引。"
        ),
        "app_title": "選用練習層",
        "app_text": (
            "典藏庫或資料工具使用完開放資源後，家庭可選擇在 iPhone 或 iPad "
            "繼續練習注音。"
        ),
        "app_cta": "查看 Lumi 注音星球",
        "footer": (
            "由發布者建立的開放 metadata；OAI-ORE 與相關名稱之權利歸各標準組織所有。"
        ),
    },
}


@dataclass(frozen=True)
class RDFValue:
    value: str
    kind: str
    datatype: str | None = None
    language: str | None = None


Triple = tuple[str, str, RDFValue]


def iri(value: str) -> RDFValue:
    return RDFValue(value=value, kind="iri")


def literal(
    value: str,
    *,
    datatype: str | None = None,
    language: str | None = None,
) -> RDFValue:
    return RDFValue(
        value=value,
        kind="literal",
        datatype=datatype,
        language=language,
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_url(spec: SourceSpec) -> str:
    return f"{SITE}/{spec.path}"


def _checksum_uri(spec: SourceSpec) -> str:
    return f"{_source_url(spec)}#sha256"


def _source_entries(pages: Path) -> dict[SourceSpec, bytes]:
    entries = {}
    for spec in SOURCE_SPECS:
        path = pages / spec.path
        if not path.is_file():
            raise FileNotFoundError(f"OAI-ORE source is missing: {path}")
        entries[spec] = path.read_bytes()
    return entries


def _timestamp(value: str) -> dt.datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError(f"Invalid UTC timestamp: {value}")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp_text(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _new_timestamp(prior: str | None = None) -> str:
    value = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    if prior is not None:
        previous = _timestamp(prior)
        if value <= previous:
            value = previous + dt.timedelta(seconds=1)
    return _timestamp_text(value)


def _add(
    triples: list[Triple],
    subject: str,
    predicate: str,
    obj: RDFValue,
) -> None:
    triples.append((subject, predicate, obj))


def build_triples(
    resource_map_url: str,
    sources: dict[SourceSpec, bytes],
    modified: str,
) -> list[Triple]:
    _timestamp(modified)
    triples: list[Triple] = []
    _add(triples, resource_map_url, f"{RDF_NS}type", iri(f"{ORE_NS}ResourceMap"))
    _add(triples, resource_map_url, f"{ORE_NS}describes", iri(AGGREGATION_URI))
    _add(triples, resource_map_url, f"{DCTERMS_NS}creator", iri(CREATOR_URI))
    _add(
        triples,
        resource_map_url,
        f"{DCTERMS_NS}created",
        literal(f"{INITIAL_DATE}T00:00:00Z", datatype=f"{XSD_NS}dateTime"),
    )
    _add(
        triples,
        resource_map_url,
        f"{DCTERMS_NS}modified",
        literal(modified, datatype=f"{XSD_NS}dateTime"),
    )
    _add(
        triples,
        resource_map_url,
        f"{DCTERMS_NS}rights",
        iri(LICENSE),
    )

    _add(triples, AGGREGATION_URI, f"{RDF_NS}type", iri(f"{ORE_NS}Aggregation"))
    _add(
        triples,
        AGGREGATION_URI,
        f"{DCTERMS_NS}title",
        literal("Bopomofo 37-symbol open-data aggregation", language="en"),
    )
    _add(
        triples,
        AGGREGATION_URI,
        f"{DCTERMS_NS}title",
        literal("注音 37 符號開放資料聚合", language="zh-Hant"),
    )
    _add(
        triples,
        AGGREGATION_URI,
        f"{DCTERMS_NS}description",
        literal(
            "A finite compound object containing sixteen machine-readable "
            "representations and metadata resources for all 37 Bopomofo symbols.",
            language="en",
        ),
    )
    _add(
        triples,
        AGGREGATION_URI,
        f"{DCTERMS_NS}description",
        literal(
            "包含完整 37 個注音符號之 16 項機器可讀資料與 metadata 的有限複合物件。",
            language="zh-Hant",
        ),
    )
    _add(triples, AGGREGATION_URI, f"{DCTERMS_NS}creator", iri(CREATOR_URI))
    _add(triples, AGGREGATION_URI, f"{DCTERMS_NS}rights", iri(LICENSE))
    _add(triples, AGGREGATION_URI, f"{DCTERMS_NS}conformsTo", iri(ORE_MODEL))
    _add(triples, AGGREGATION_URI, f"{DCTERMS_NS}conformsTo", iri(ORE_VOCABULARY))
    for url in RESOURCE_MAP_URLS:
        _add(triples, AGGREGATION_URI, f"{ORE_NS}isDescribedBy", iri(url))

    _add(triples, CREATOR_URI, f"{RDF_NS}type", iri(f"{DCTERMS_NS}Agent"))
    _add(triples, CREATOR_URI, f"{RDF_NS}type", iri(f"{FOAF_NS}Organization"))
    _add(
        triples,
        CREATOR_URI,
        f"{FOAF_NS}name",
        literal("iOS App Guide Open Resources"),
    )

    for spec, data in sources.items():
        url = _source_url(spec)
        checksum = _checksum_uri(spec)
        _add(triples, AGGREGATION_URI, f"{ORE_NS}aggregates", iri(url))
        _add(triples, url, f"{ORE_NS}isAggregatedBy", iri(AGGREGATION_URI))
        _add(triples, url, f"{DCTERMS_NS}title", literal(spec.title, language="en"))
        _add(triples, url, f"{DCTERMS_NS}format", literal(spec.media_type))
        _add(
            triples,
            url,
            f"{DCAT_NS}byteSize",
            literal(str(len(data)), datatype=f"{XSD_NS}decimal"),
        )
        _add(triples, url, f"{SPDX_NS}checksum", iri(checksum))
        _add(triples, checksum, f"{RDF_NS}type", iri(f"{SPDX_NS}Checksum"))
        _add(
            triples,
            checksum,
            f"{SPDX_NS}algorithm",
            iri(f"{SPDX_NS}checksumAlgorithm_sha256"),
        )
        _add(
            triples,
            checksum,
            f"{SPDX_NS}checksumValue",
            literal(_sha256(data), datatype=f"{XSD_NS}hexBinary"),
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


def _turtle_literal(value: RDFValue) -> str:
    text = json.dumps(value.value, ensure_ascii=False)
    if value.language:
        return f"{text}@{value.language}"
    if value.datatype:
        return f"{text}^^<{value.datatype}>"
    return text


def render_turtle(triples: list[Triple]) -> bytes:
    prefixes = "\n".join(
        f"@prefix {prefix}: <{namespace}> ." for prefix, namespace in NAMESPACES.items()
    )
    rows = []
    for subject, predicate, obj in triples:
        rendered = f"<{obj.value}>" if obj.kind == "iri" else _turtle_literal(obj)
        rows.append(f"<{subject}> <{predicate}> {rendered} .")
    return (f"{prefixes}\n\n" + "\n".join(rows) + "\n").encode("utf-8")


def _compact(value: str) -> str:
    for prefix, namespace in NAMESPACES.items():
        if value.startswith(namespace):
            return f"{prefix}:{value[len(namespace):]}"
    return value


def _jsonld_value(value: RDFValue) -> dict | str:
    if value.kind == "iri":
        return {"@id": value.value}
    if value.language:
        return {"@value": value.value, "@language": value.language}
    if value.datatype:
        return {"@value": value.value, "@type": value.datatype}
    return value.value


def render_jsonld(triples: list[Triple]) -> bytes:
    grouped: dict[str, dict[str, list[RDFValue]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for subject, predicate, obj in triples:
        grouped[subject][predicate].append(obj)
    graph = []
    for subject in sorted(grouped):
        node: dict[str, object] = {"@id": subject}
        for predicate in sorted(grouped[subject]):
            values = grouped[subject][predicate]
            if predicate == f"{RDF_NS}type":
                node["@type"] = [value.value for value in values]
            else:
                node[_compact(predicate)] = [_jsonld_value(value) for value in values]
        graph.append(node)
    document = {
        "@context": NAMESPACES,
        "@graph": graph,
    }
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _predicate_qname(predicate: str) -> str:
    for namespace in NAMESPACES.values():
        if predicate.startswith(namespace):
            return f"{{{namespace}}}{predicate[len(namespace):]}"
    raise ValueError(f"RDF/XML predicate namespace is not registered: {predicate}")


def render_rdfxml(triples: list[Triple]) -> bytes:
    for prefix, namespace in NAMESPACES.items():
        ET.register_namespace(prefix, namespace)
    root = ET.Element(f"{{{RDF_NS}}}RDF")
    grouped: dict[str, list[tuple[str, RDFValue]]] = defaultdict(list)
    for subject, predicate, obj in triples:
        grouped[subject].append((predicate, obj))
    for subject in sorted(grouped):
        description = ET.SubElement(
            root,
            f"{{{RDF_NS}}}Description",
            {f"{{{RDF_NS}}}about": subject},
        )
        for predicate, obj in sorted(
            grouped[subject],
            key=lambda item: (
                item[0],
                item[1].kind,
                item[1].value,
                item[1].language or "",
                item[1].datatype or "",
            ),
        ):
            element = ET.SubElement(description, _predicate_qname(predicate))
            if obj.kind == "iri":
                element.set(f"{{{RDF_NS}}}resource", obj.value)
            else:
                element.text = obj.value
                if obj.language:
                    element.set(f"{{{XML_NS}}}lang", obj.language)
                if obj.datatype:
                    element.set(f"{{{RDF_NS}}}datatype", obj.datatype)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _graph_bytes(
    resource_map_url: str,
    sources: dict[SourceSpec, bytes],
    modified: str,
    format_name: str,
) -> bytes:
    triples = build_triples(resource_map_url, sources, modified)
    if format_name == "xml":
        return render_rdfxml(triples)
    if format_name == "turtle":
        return render_turtle(triples)
    if format_name == "json-ld":
        return render_jsonld(triples)
    raise ValueError(f"Unsupported Resource Map format: {format_name}")


def _readme_bytes(modified: str) -> bytes:
    text = f"""Bopomofo OAI-ORE 1.0 Resource Map
=====================================

Aggregation URI
---------------
{AGGREGATION_URI}

This URI follows the OAI-ORE no-server hash-URI pattern. Dereferencing it
removes #aggregation and retrieves the authoritative RDF/XML Resource Map.

Resource Maps
-------------
- {RDFXML_FILENAME}  application/rdf+xml
- {TURTLE_FILENAME}  text/turtle
- {JSONLD_FILENAME}  application/ld+json

Each Resource Map has its own URI-R, describes the same URI-A and exposes the
same sixteen-member Aggregation Graph. The maps also record creator,
modification time, media type, byte size and SHA-256 for every aggregated
resource.

Validation
----------
1. Verify checksums-sha256.txt.
2. Parse each map as RDF.
3. Confirm one ore:describes triple from each URI-R to the Aggregation URI.
4. Confirm sixteen ore:aggregates objects and identical membership across maps.
5. Compare dcat:byteSize and SPDX SHA-256 values to each live resource.

Specification
-------------
Abstract Data Model: {ORE_MODEL}
Vocabulary: {ORE_VOCABULARY}
HTTP hash URI guidance: {ORE_HTTP}
RDF/XML profile: {ORE_RDFXML}

Limits
------
This publisher-authored map does not claim OAI endorsement, external repository
ingest, DOI assignment, third-party certification, content negotiation or Atom
serialization conformance.

Generated: {modified}

繁體中文
--------
本套件以 OAI-ORE Resource Map 描述完整 37 個注音符號資料的 16 項機器可讀
資源。Aggregation URI 採不需伺服器設定的 hash URI 模式；三份 RDF map
具有不同 URI-R，但公開相同的 Aggregation Graph。請先核對 SHA-256，再解析
RDF 並逐一比對 ore:aggregates、byte size 與來源檔案。
"""
    return text.encode("utf-8")


def _license_bytes() -> bytes:
    return (
        "Bopomofo OAI-ORE Resource Map metadata\n"
        "Copyright (c) 2026 iOS App Guide Open Resources\n\n"
        "Licensed under the Creative Commons Attribution 4.0 International "
        "License (CC BY 4.0).\n"
        "License: https://creativecommons.org/licenses/by/4.0/\n\n"
        "Attribution: Bopomofo OAI-ORE Resource Map, iOS App Guide Open "
        "Resources.\n\n"
        "The license applies to this publisher-authored metadata and package "
        "documentation. Referenced standards and external source materials "
        "remain under their respective terms.\n"
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
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return stream.getvalue()


def make_artifacts(pages: Path, modified: str) -> dict[str, bytes]:
    sources = _source_entries(pages)
    core: dict[str, bytes] = {}
    for filename, url, _, _, format_name in MAP_SPECS:
        core[filename] = _graph_bytes(url, sources, modified, format_name)
    core[README_FILENAME] = _readme_bytes(modified)
    core[LICENSE_FILENAME] = _license_bytes()
    checksums = _checksum_bytes(core)
    zip_entries = {**core, CHECKSUM_FILENAME: checksums}
    artifacts = {
        **zip_entries,
        BUNDLE_FILENAME: _zip_bytes(zip_entries),
    }
    validate_artifacts(pages, artifacts, modified)
    return artifacts


def _parse_graph(data: bytes, format_name: str) -> Graph:
    graph = Graph()
    graph.parse(data=data, format=format_name)
    return graph


def _assert_connected(graph: Graph, resource_map: URIRef) -> None:
    adjacency: dict[URIRef, set[URIRef]] = defaultdict(set)
    subjects: set[URIRef] = set()
    for subject, _, obj in graph:
        if isinstance(subject, URIRef):
            subjects.add(subject)
        if isinstance(subject, URIRef) and isinstance(obj, URIRef):
            adjacency[subject].add(obj)
            adjacency[obj].add(subject)
    seen = {resource_map}
    queue = deque([resource_map])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current] - seen:
            seen.add(neighbor)
            queue.append(neighbor)
    missing = subjects - seen
    if missing:
        raise ValueError(f"OAI-ORE graph is disconnected: {sorted(map(str, missing))}")


def validate_artifacts(
    pages: Path,
    artifacts: dict[str, bytes],
    modified: str,
) -> None:
    _timestamp(modified)
    expected_members = [
        RDFXML_FILENAME,
        TURTLE_FILENAME,
        JSONLD_FILENAME,
        README_FILENAME,
        LICENSE_FILENAME,
        CHECKSUM_FILENAME,
    ]
    if list(artifacts) != [*expected_members, BUNDLE_FILENAME]:
        raise ValueError("OAI-ORE artifact order or membership is invalid")

    sources = _source_entries(pages)
    parsed: dict[str, Graph] = {}
    aggregation_membership: set[URIRef] | None = None
    expected_resources = {URIRef(_source_url(spec)) for spec in SOURCE_SPECS}
    for filename, resource_map_url, _, _, format_name in MAP_SPECS:
        graph = _parse_graph(artifacts[filename], format_name)
        parsed[filename] = graph
        resource_map = URIRef(resource_map_url)
        aggregation = URIRef(AGGREGATION_URI)
        if set(graph.objects(resource_map, ORE.describes)) != {aggregation}:
            raise ValueError(f"OAI-ORE map must describe one Aggregation: {filename}")
        if (resource_map, RDF.type, ORE.ResourceMap) not in graph:
            raise ValueError(f"OAI-ORE ResourceMap type is missing: {filename}")
        if (aggregation, RDF.type, ORE.Aggregation) not in graph:
            raise ValueError(f"OAI-ORE Aggregation type is missing: {filename}")
        if set(graph.objects(resource_map, DCTERMS.creator)) != {
            URIRef(CREATOR_URI)
        }:
            raise ValueError(f"OAI-ORE creator is invalid: {filename}")
        if set(graph.objects(resource_map, DCTERMS.modified)) != {
            Literal(modified, datatype=XSD.dateTime)
        }:
            raise ValueError(f"OAI-ORE modified timestamp is invalid: {filename}")
        if set(graph.objects(aggregation, ORE.isDescribedBy)) != {
            URIRef(url) for url in RESOURCE_MAP_URLS
        }:
            raise ValueError(f"OAI-ORE alternate maps are incomplete: {filename}")
        members = set(graph.objects(aggregation, ORE.aggregates))
        if members != expected_resources:
            raise ValueError(f"OAI-ORE aggregation boundary is incomplete: {filename}")
        if aggregation_membership is None:
            aggregation_membership = members
        elif aggregation_membership != members:
            raise ValueError("OAI-ORE serializations disagree on Aggregation Graph")
        for spec, data in sources.items():
            resource = URIRef(_source_url(spec))
            checksum = URIRef(_checksum_uri(spec))
            if set(graph.objects(resource, ORE.isAggregatedBy)) != {aggregation}:
                raise ValueError(f"OAI-ORE inverse membership is missing: {spec.path}")
            if set(graph.objects(resource, DCTERMS["format"])) != {
                Literal(spec.media_type)
            }:
                raise ValueError(f"OAI-ORE media type mismatch: {spec.path}")
            if set(graph.objects(resource, DCAT.byteSize)) != {
                Literal(str(len(data)), datatype=XSD.decimal)
            }:
                raise ValueError(f"OAI-ORE byte size mismatch: {spec.path}")
            if set(graph.objects(resource, SPDX.checksum)) != {checksum}:
                raise ValueError(f"OAI-ORE checksum link is missing: {spec.path}")
            if set(graph.objects(checksum, SPDX.checksumValue)) != {
                Literal(_sha256(data), datatype=XSD.hexBinary)
            }:
                raise ValueError(f"OAI-ORE SHA-256 mismatch: {spec.path}")
        _assert_connected(graph, resource_map)

    csv_rows = list(
        csv.DictReader(
            io.StringIO(
                sources[
                    next(
                        spec
                        for spec in SOURCE_SPECS
                        if spec.path == "data/zhuyin-bopomofo-ml-dataset.csv"
                    )
                ].decode("utf-8")
            )
        )
    )
    if len(csv_rows) != 37:
        raise ValueError("OAI-ORE CSV source must contain exactly 37 rows")
    expected_checksums = _checksum_bytes(
        {name: artifacts[name] for name in expected_members[:-1]}
    )
    if artifacts[CHECKSUM_FILENAME] != expected_checksums:
        raise ValueError("OAI-ORE checksum list mismatch")
    with zipfile.ZipFile(io.BytesIO(artifacts[BUNDLE_FILENAME])) as archive:
        if archive.namelist() != expected_members:
            raise ValueError("OAI-ORE ZIP order or membership is invalid")
        for info in archive.infolist():
            if (
                info.date_time != ZIP_TIMESTAMP
                or info.compress_type != zipfile.ZIP_DEFLATED
                or info.external_attr >> 16 != 0o100644
                or archive.read(info.filename) != artifacts[info.filename]
            ):
                raise ValueError(f"Non-deterministic OAI-ORE ZIP entry: {info.filename}")
    for name in expected_members:
        text = artifacts[name].decode("utf-8")
        for forbidden in FORBIDDEN:
            if forbidden.lower() in text.lower():
                raise ValueError(f"OAI-ORE artifact contains forbidden text: {name}")


def metadata_document(
    artifacts: dict[str, bytes],
    sources: dict[SourceSpec, bytes],
    modified: str,
) -> dict:
    distribution = []
    for filename, _, title, media_type, _ in MAP_SPECS:
        distribution.append(
            {
                "@type": "DataDownload",
                "name": title,
                "contentUrl": f"{PACKAGE_URL}{filename}",
                "encodingFormat": media_type,
                "contentSize": len(artifacts[filename]),
                "sha256": _sha256(artifacts[filename]),
            }
        )
    for filename, title, media_type in (
        (CHECKSUM_FILENAME, "SHA-256 checksum list", "text/plain"),
        (README_FILENAME, "Bilingual validation guide", "text/plain"),
        (LICENSE_FILENAME, "CC BY 4.0 attribution notice", "text/plain"),
        (BUNDLE_FILENAME, "Complete deterministic bundle", "application/zip"),
    ):
        distribution.append(
            {
                "@type": "DataDownload",
                "name": title,
                "contentUrl": f"{PACKAGE_URL}{filename}",
                "encodingFormat": media_type,
                "contentSize": len(artifacts[filename]),
                "sha256": _sha256(artifacts[filename]),
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": ["Dataset", "LearningResource"],
        "@id": AGGREGATION_URI,
        "identifier": AGGREGATION_URI,
        "name": "Bopomofo OAI-ORE 1.0 Resource Map",
        "alternateName": "注音 OAI-ORE 1.0 資源聚合圖",
        "description": (
            "A repository-readable OAI-ORE aggregation of sixteen reusable "
            "resources for the complete 37-symbol Bopomofo dataset."
        ),
        "url": PACKAGE_URL,
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "inLanguage": ["en", "zh-Hant"],
        "isAccessibleForFree": True,
        "license": LICENSE,
        "creator": {
            "@type": "Organization",
            "@id": CREATOR_URI,
            "name": "iOS App Guide Open Resources",
        },
        "conformsTo": [ORE_MODEL, ORE_VOCABULARY, ORE_RDFXML],
        "keywords": [
            "OAI-ORE",
            "Resource Map",
            "compound digital object",
            "Bopomofo",
            "Zhuyin",
            "repository interoperability",
        ],
        "distribution": distribution,
        "hasPart": [
            {
                "@type": "DataDownload",
                "name": spec.title,
                "contentUrl": _source_url(spec),
                "encodingFormat": spec.media_type,
                "contentSize": len(data),
                "sha256": _sha256(data),
            }
            for spec, data in sources.items()
        ],
    }


def _metadata_bytes(
    artifacts: dict[str, bytes],
    sources: dict[SourceSpec, bytes],
    modified: str,
) -> bytes:
    return (
        json.dumps(
            metadata_document(artifacts, sources, modified),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_rows(sources: dict[SourceSpec, bytes]) -> str:
    return "".join(
        "<tr>"
        f'<td><a href="{html.escape(_source_url(spec), quote=True)}">'
        f"{html.escape(spec.path)}</a></td>"
        f"<td>{html.escape(spec.media_type)}</td>"
        f"<td>{len(data):,}</td>"
        f"<td><code>{_sha256(data)[:16]}…</code></td>"
        "</tr>"
        for spec, data in sources.items()
    )


def render_page(
    locale: str,
    artifacts: dict[str, bytes],
    sources: dict[SourceSpec, bytes],
    modified: str,
    page_modified: str,
    app_public: bool,
) -> str:
    copy = COPY[locale]
    canonical = PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL
    alternate = ZH_PACKAGE_URL if locale == "en" else PACKAGE_URL
    schema_graph = [
        metadata_document(artifacts, sources, modified),
        {
            "@type": "WebPage",
            "@id": canonical,
            "url": canonical,
            "name": copy["title"],
            "dateModified": page_modified,
            "inLanguage": copy["lang"],
            "mainEntity": {"@id": AGGREGATION_URI},
        },
    ]
    if app_public:
        schema_graph.append(
            {
                "@type": "SoftwareApplication",
                "applicationCategory": "EducationApplication",
                "name": APP_NAME,
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_ore_{locale.lower()}"),
            }
        )
    downloads = "".join(
        f'<a class="download{" primary" if filename == BUNDLE_FILENAME else ""}" '
        f'href="{PACKAGE_URL}{filename}"><strong>{html.escape(label)}</strong>'
        f"<span>{len(artifacts[filename]):,} bytes · "
        f"{_sha256(artifacts[filename])[:16]}…</span></a>"
        for filename, label in (
            (BUNDLE_FILENAME, copy["bundle"]),
            (RDFXML_FILENAME, copy["rdfxml"]),
            (TURTLE_FILENAME, copy["turtle"]),
            (JSONLD_FILENAME, copy["jsonld"]),
            (CHECKSUM_FILENAME, copy["checksums"]),
        )
    )
    downloads += (
        f'<a class="download" href="{METADATA_URL}"><strong>'
        f'{html.escape(copy["metadata"])}</strong>'
        "<span>Schema.org · JSON-LD</span></a>"
    )
    model_items = "".join(f"<li>{html.escape(item)}</li>" for item in copy["model_items"])
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel optional"><h2>'
            f'{html.escape(copy["app_title"])}</h2><p>{html.escape(copy["app_text"])}</p>'
            f'<a class="button" href="{appstore_url(APP_KEY, "iag_ore")}">'
            f'{html.escape(copy["app_cta"])}</a></section>'
        )
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
<link rel="resourcemap" type="application/rdf+xml" href="{RDFXML_URL}">
<link rel="resourcemap" type="text/turtle" href="{TURTLE_URL}">
<link rel="resourcemap" type="application/ld+json" href="{JSONLD_URL}">
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": schema_graph}, ensure_ascii=False)}</script>
<style>
:root{{--ink:#152238;--muted:#58677b;--line:#d9e2eb;--paper:#fff;--accent:#225a66;--soft:#e8f5f4}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.65 system-ui,sans-serif;color:var(--ink);background:linear-gradient(180deg,#f1f8f7,#fff)}}
a{{color:#0f6574}}.wrap{{width:min(1140px,calc(100% - 32px));margin:auto}}header{{padding:18px 0}}nav{{display:flex;justify-content:space-between;gap:12px}}nav a,.button{{white-space:nowrap}}
.hero{{padding:50px 0 22px}}.eyebrow{{font-weight:850;color:var(--accent);letter-spacing:.06em;text-transform:uppercase;white-space:nowrap;overflow:auto}}h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.04;margin:.2em 0}}.lead{{font-size:1.15rem;color:var(--muted);max-width:830px}}
.badges{{display:flex;gap:8px;flex-wrap:wrap}}.badge{{padding:6px 11px;border-radius:999px;background:var(--soft);font-weight:800;white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 10px 34px rgba(26,72,82,.07);margin:18px 0}}
.download{{display:flex;justify-content:space-between;gap:14px;align-items:center;padding:14px 16px;border:1px solid var(--line);border-radius:14px;text-decoration:none;margin:10px 0}}.download span{{color:var(--muted);font-size:.86rem;white-space:nowrap}}.download.primary{{background:var(--accent);color:#fff;border-color:var(--accent)}}.download.primary span{{color:#e8f5f4}}
table{{width:100%;border-collapse:collapse;display:block;overflow:auto}}th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}code{{font-size:.78rem}}.sources{{display:flex;gap:10px;flex-wrap:wrap}}.sources a,.button{{display:inline-block;padding:10px 15px;border-radius:999px;text-decoration:none;font-weight:800;white-space:nowrap}}.sources a{{background:var(--soft)}}.button{{background:var(--accent);color:#fff}}.uri{{overflow:auto;white-space:nowrap;padding:11px 14px;background:#f5f8fa;border-radius:12px}}.optional{{border-style:dashed}}footer{{padding:32px 0;color:var(--muted)}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.download{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<header class="wrap"><nav><a href="{SITE}/data/">{html.escape(copy['back'])}</a><a href="{alternate}">{html.escape(copy['language'])}</a></nav></header>
<main>
<section class="hero wrap"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges"><span class="badge">OAI-ORE 1.0</span><span class="badge">16 resources</span><span class="badge">SHA-256</span><span class="badge">37 symbols</span></div></section>
<section class="wrap panel"><h2>Aggregation URI</h2><p class="uri"><code>{html.escape(AGGREGATION_URI)}</code></p></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p>{downloads}</article><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><div class="sources"><a href="{ORE_MODEL}">OAI-ORE model</a><a href="{ORE_RDFXML}">RDF/XML profile</a></div></article></section>
<section class="wrap panel"><h2>{html.escape(copy['inventory'])}</h2><table><thead><tr><th>{html.escape(copy['resource'])}</th><th>{html.escape(copy['format'])}</th><th>{html.escape(copy['bytes'])}</th><th>{html.escape(copy['sha'])}</th></tr></thead><tbody>{_artifact_rows(sources)}</tbody></table></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['model'])}</h2><ul>{model_items}</ul></article><article class="panel"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limits_text'])}</p></article></section>
<section class="wrap panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['sources_text'])}</p><div class="sources"><a href="{ORE_MODEL}">Abstract Data Model</a><a href="{ORE_VOCABULARY}">Vocabulary</a><a href="{ORE_HTTP}">Hash URI guidance</a><a href="{LICENSE}" rel="license">CC BY 4.0</a></div></section>
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
        f'<link rel="resourcemap" type="application/rdf+xml" href="{RDFXML_URL}">',
        f'<link rel="resourcemap" type="text/turtle" href="{TURTLE_URL}">',
        f'<link rel="resourcemap" type="application/ld+json" href="{JSONLD_URL}">',
        AGGREGATION_URI,
        f'href="{BUNDLE_URL}"',
        f'href="{CHECKSUM_URL}"',
        f'href="{METADATA_URL}"',
        f'href="{ORE_MODEL}"',
        f'href="{ORE_HTTP}"',
    ):
        if required not in page:
            raise ValueError(f"OAI-ORE landing is missing {required}")
    if ("apps.apple.com" in page) != app_public:
        raise ValueError("OAI-ORE optional app CTA does not match public availability")


def _prior_timestamp(metadata_path: Path) -> str | None:
    if not metadata_path.is_file():
        return None
    try:
        value = json.loads(metadata_path.read_text(encoding="utf-8"))["dateModified"]
        _timestamp(value)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Existing OAI-ORE metadata is invalid: {metadata_path}") from error
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
    sources: dict[SourceSpec, bytes],
    modified: str,
) -> bool:
    index = pages / "data" / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"Data index must exist before OAI-ORE: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'{CARD_START}<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo OAI-ORE 1.0 Resource Map</h2>"
        "<p>Repository-readable compound-object boundary for sixteen core "
        "Bopomofo data, schema, vocabulary and API resources.</p>"
        '<span class="tag">OAI-ORE 1.0 · RDF · EN + zh-Hant</span></a>'
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
        + re.escape(f"{SITE}/data/packages/zhuyin-bopomofo-mets2-premis3/")
        + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if anchor:
        updated = updated[: anchor.end()] + card + updated[anchor.end() :]
    else:
        footer = updated.find('<p class="foot">')
        if footer < 0:
            raise RuntimeError("data/index.html has no OAI-ORE insertion anchor")
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
    entry = metadata_document(artifacts, sources, modified)
    position = next(
        (
            offset + 1
            for offset, item in enumerate(datasets)
            if item.get("url")
            == f"{SITE}/data/packages/zhuyin-bopomofo-mets2-premis3/"
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
    urls = (
        (PACKAGE_URL, page_modified["en"]),
        (ZH_PACKAGE_URL, page_modified["zh-Hant"]),
        *(
            (f"{PACKAGE_URL}{filename}", modified)
            for filename in (
                RDFXML_FILENAME,
                TURTLE_FILENAME,
                JSONLD_FILENAME,
                README_FILENAME,
                LICENSE_FILENAME,
                CHECKSUM_FILENAME,
                METADATA_FILENAME,
                BUNDLE_FILENAME,
            )
        ),
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
    if prior is not None and _artifacts_changed(package_dir, artifacts):
        modified = _new_timestamp(prior)
        artifacts = make_artifacts(pages, modified)
    sources = _source_entries(pages)
    metadata = _metadata_bytes(artifacts, sources, modified)
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
                sources,
                modified,
                changed,
                public,
            ),
            INITIAL_DATE,
        )
        validate_page(path.read_text(encoding="utf-8"), locale, public)
    update_data_index(pages, artifacts, sources, modified)
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(modified, page_modified),
    )
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        AGGREGATION_URI,
        *(
            f"{PACKAGE_URL}{name}"
            for name in (
                RDFXML_FILENAME,
                TURTLE_FILENAME,
                JSONLD_FILENAME,
                README_FILENAME,
                LICENSE_FILENAME,
                CHECKSUM_FILENAME,
                METADATA_FILENAME,
                BUNDLE_FILENAME,
            )
        ),
        SITEMAP_URL,
    ]


def main() -> None:
    urls = build()
    print(f"Published OAI-ORE Resource Map ({len(urls)} URLs)")
    for url in urls:
        print(url)


if __name__ == "__main__":
    main()
