#!/usr/bin/env python3
"""Publish a METS 2.0 and PREMIS 3.0 package for the open Bopomofo data."""

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
from dataclasses import dataclass
from pathlib import Path

from lxml import etree


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import render_versioned_page, write_text_if_changed  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from zhuyin_croissant_dataset import (  # noqa: E402
    APP_ID,
    APP_KEY,
    APP_NAME,
    LICENSE,
    SITE,
)
from site_config import PUBLIC_SITE  # noqa: E402


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
VERSION = "1.0.0"

PACKAGE_SLUG = "zhuyin-bopomofo-mets2-premis3"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
OBJECT_ID = PACKAGE_URL
PUBLISHER_ID = f"{OBJECT_ID}#publisher"
GENERATOR_ID = f"{OBJECT_ID}#generator"
EVENT_ID = f"{OBJECT_ID}#event-package-generation"
RIGHTS_ID = f"{OBJECT_ID}#rights-cc-by-4.0"

METS_FILENAME = "mets.xml"
PREMIS_FILENAME = "premis.xml"
README_FILENAME = "README.txt"
LICENSE_FILENAME = "LICENSE.txt"
CHECKSUM_FILENAME = "checksums-sha256.txt"
METADATA_FILENAME = "metadata.jsonld"
BUNDLE_FILENAME = "bopomofo-37-symbols-mets2-premis3.zip"
SITEMAP_PATH = Path("sitemap_mets_premis.xml")
CARD_START = "<!-- bopomofo-mets-premis:start -->"
CARD_END = "<!-- bopomofo-mets-premis:end -->"

METS_URL = f"{PACKAGE_URL}{METS_FILENAME}"
PREMIS_URL = f"{PACKAGE_URL}{PREMIS_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"

METS_NS = "http://www.loc.gov/METS/v2"
PREMIS_NS = "http://www.loc.gov/premis/v3"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
METS_SCHEMA_URL = "https://www.loc.gov/standards/mets/mets2.xsd"
METS_GUIDE_URL = "https://mets.github.io/"
METS_REPOSITORY = "https://github.com/mets/METS-schema"
METS_COMMIT = "a89833cb0464299fdd22d7d3f0746eb4d13f5bf3"
METS_SCHEMA_SHA256 = "1ac4af428d9ab2099b19306344d56916a3dcd7bfd39d7d2276c1fbde24205c96"
PREMIS_SCHEMA_URL = "https://www.loc.gov/standards/premis/v3/premis-v3-0.xsd"
PREMIS_GUIDE_URL = "https://www.loc.gov/standards/premis/v3/"
PREMIS_REPOSITORY = "https://github.com/LibraryOfCongress/premis-v3-0"
PREMIS_COMMIT = "3b79c30136c0f6ed673dd6ec9c9830d55730d889"
PREMIS_SCHEMA_SHA256 = "03b8a77a20b32b882ad799e12262671d07ad18210c60233f4e613a1289491cba"
REFERENCE_DIR = HERE / "reference_datasets" / "mets2-premis3"
METS_SCHEMA_PATH = REFERENCE_DIR / "mets2.xsd"
PREMIS_SCHEMA_PATH = REFERENCE_DIR / "premis-v3-0.xsd"
SOURCES_PATH = REFERENCE_DIR / "sources.json"

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FORBIDDEN = ("apps.apple.com", "SoftwareApplication", APP_NAME, APP_ID)


@dataclass(frozen=True)
class PayloadSpec:
    source_path: str
    package_path: str
    name: str
    description: str
    media_type: str
    group: str = "DATA"


PAYLOAD_SPECS = (
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "Canonical 37-row Bopomofo table",
        "UTF-8 table with stable IDs, Unicode, Pinyin, IPA, categories and examples.",
        "text/csv",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "Equivalent Bopomofo JSON Lines records",
        "One UTF-8 JSON object per Bopomofo symbol in canonical display order.",
        "text/plain",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        "MLCommons Croissant 1.1 metadata",
        "Dataset fields, source provenance and reuse metadata for ML consumers.",
        "application/ld+json",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "W3C CSVW metadata",
        "Table dialect, typed columns, primary key and RDF mappings.",
        "application/csvm+json",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "Bopomofo SKOS vocabulary",
        "SKOS concept scheme with stable concept IRIs and bilingual labels.",
        "application/ld+json",
    ),
    PayloadSpec(
        README_FILENAME,
        README_FILENAME,
        "Bilingual preservation and validation guide",
        "Plain-text English and Traditional Chinese transfer instructions.",
        "text/plain",
        "DOCUMENTATION",
    ),
    PayloadSpec(
        LICENSE_FILENAME,
        LICENSE_FILENAME,
        "CC BY 4.0 attribution notice",
        "License URL, scope and requested attribution for the open data.",
        "text/plain",
        "DOCUMENTATION",
    ),
)

README_TEXT = """Bopomofo 37-Symbol METS 2.0 + PREMIS 3.0 Package
======================================================

This static transfer package describes the complete 37-symbol Bopomofo dataset
with a METS 2.0 file inventory and structure map plus PREMIS 3.0 preservation
Objects, fixity, Events, Agents and Rights.

Guide: {GUIDE}/data/packages/zhuyin-bopomofo-mets2-premis3/
Traditional Chinese guide: {GUIDE}/zh-Hant/data/packages/zhuyin-bopomofo-mets2-premis3/
METS schema: https://www.loc.gov/standards/mets/mets2.xsd
PREMIS schema: https://www.loc.gov/standards/premis/v3/premis-v3-0.xsd

Validation
----------
1. Verify checksums-sha256.txt.
2. Validate mets.xml with the pinned METS 2.0 XSD.
3. Validate premis.xml with the pinned PREMIS 3.0 XSD.
4. Confirm every METS file entry and PREMIS Object matches the local path,
   media type, byte size and SHA-256 digest.
5. Review local repository policy before ingest.

Scope and limits
----------------
The ZIP is a deterministic transfer wrapper, not a METS-defined archive format.
The package has no DOI and does not claim repository registration, external
ingest, certification, institutional endorsement or a digital signature.
Checksums provide fixity only.

繁體中文
--------
本靜態移轉套件以 METS 2.0 記錄完整 37 個注音符號資料的檔案清單與結構，
並以 PREMIS 3.0 記錄逐檔 Object、fixity、Event、Agent 與 Rights。

請先驗證 checksums-sha256.txt，再分別用固定版本的官方 XSD 驗證 mets.xml
與 premis.xml，並確認每個路徑、media type、byte size 與 SHA-256 完全一致。
ZIP 是 deterministic transfer wrapper，不是 METS 規範定義的封裝格式。本套件
沒有 DOI，也不宣稱已登錄或匯入典藏庫、通過第三方認證、獲機構背書或具有
數位簽章。
""".replace("{GUIDE}", PUBLIC_SITE)

LICENSE_TEXT = f"""Bopomofo open-data payload license
===================================

License: Creative Commons Attribution 4.0 International (CC BY 4.0)
URL: {LICENSE}

You may share and adapt the packaged Bopomofo data for any purpose with
appropriate attribution, a link to the license, and an indication of changes.

Suggested attribution:
Bopomofo 37-Symbol Open Reference Data, iOS App Guide Open Resources,
{PACKAGE_URL}

The METS and PREMIS schema snapshots retain their original notices and are not
relicensed by this file. METS 2.0 declares CC0 in its schema. The PREMIS schema
snapshot is an unmodified validation reference from the official Library of
Congress source; this package asserts no SPDX license identifier for that schema.

注音開放資料採 CC BY 4.0 授權。重製或改作時請保留適當姓名標示、授權連結，
並註明是否修改。官方 XSD 快照保留原始內容與來源，本檔不替它們重新授權。
"""

COPY = {
    "en": {
        "lang": "en",
        "title": "METS 2.0 + PREMIS 3.0 Preservation Package for Bopomofo",
        "description": (
            "Download a deterministic METS 2.0 and PREMIS 3.0 transfer package "
            "for all 37 Bopomofo symbols with per-file SHA-256 fixity."
        ),
        "eyebrow": "METS 2.0 · PREMIS 3.0 · 7 preserved files",
        "lead": (
            "A transparent repository-transfer object with a standards-valid "
            "file inventory, structure map, preservation provenance and rights."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "downloads": "Repository transfer files",
        "download_text": (
            "Download the deterministic ZIP or inspect its two core XML records "
            "and complete checksum list independently."
        ),
        "bundle": "Complete deterministic ZIP",
        "mets": "METS 2.0 record",
        "premis": "PREMIS 3.0 record",
        "checksums": "SHA-256 checksums",
        "metadata": "Machine-readable package metadata",
        "inventory": "Preserved file inventory",
        "path": "Path",
        "format": "Media type",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "validate": "Offline validation",
        "validate_text": (
            "Both XML records validate against exact official XSD snapshots "
            "pinned by commit, byte length and SHA-256."
        ),
        "model": "What the records express",
        "model_items": (
            "METS fileSec records path, media type, bytes and SHA-256 for seven files.",
            "METS structSec maps the five data files and two documentation files.",
            "PREMIS creates one File Object per preserved file with matching fixity.",
            "One generation Event links every Object to organization and software Agents.",
            "One CC BY 4.0 Rights statement links every preserved Object.",
        ),
        "limits": "Limits stated plainly",
        "limits_text": (
            "The ZIP is only a deterministic transfer wrapper. This resource "
            "does not claim a DOI, repository registration, external ingest, "
            "certification, endorsement or a digital signature."
        ),
        "sources": "Normative sources",
        "sources_text": (
            "METS 2.0 was finalized in March 2025. PREMIS 3.0 remains the current "
            "Data Dictionary and XML schema generation."
        ),
        "app_title": "Optional practice after repository work",
        "app_text": (
            "The open package works without an app. Lumi Bopomofo is an optional "
            "on-device activity layer after data review and preservation."
        ),
        "app_cta": "View Lumi Bopomofo",
        "footer": "Open data · CC BY 4.0 · no account, API key or repository claim",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音 METS 2.0 + PREMIS 3.0 數位典藏套件",
        "description": (
            "下載完整 37 個注音符號的 deterministic METS 2.0 與 PREMIS 3.0 "
            "移轉套件，提供逐檔 SHA-256 fixity。"
        ),
        "eyebrow": "METS 2.0 · PREMIS 3.0 · 7 個保存檔案",
        "lead": (
            "透明的 repository transfer object，具備符合標準的檔案清單、"
            "結構圖、保存 provenance 與 rights。"
        ),
        "back": "開放資料",
        "language": "English",
        "downloads": "Repository 移轉檔案",
        "download_text": (
            "可下載 deterministic ZIP，或分別檢查兩份核心 XML record 與完整 checksum。"
        ),
        "bundle": "完整 deterministic ZIP",
        "mets": "METS 2.0 record",
        "premis": "PREMIS 3.0 record",
        "checksums": "SHA-256 checksums",
        "metadata": "Machine-readable 套件 metadata",
        "inventory": "保存檔案清單",
        "path": "路徑",
        "format": "Media type",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "validate": "離線驗證",
        "validate_text": (
            "兩份 XML record 都會用依 commit、byte length 與 SHA-256 固定的"
            "官方 XSD 快照驗證。"
        ),
        "model": "Records 表達內容",
        "model_items": (
            "METS fileSec 記錄 7 個檔案的路徑、media type、bytes 與 SHA-256。",
            "METS structSec 映射 5 個 data files 與 2 個 documentation files。",
            "PREMIS 為每個保存檔案建立一個 fixity 完全相符的 File Object。",
            "一個 generation Event 將所有 Object 連到 organization 與 software Agent。",
            "一份 CC BY 4.0 Rights statement 連到所有保存 Object。",
        ),
        "limits": "誠實界線",
        "limits_text": (
            "ZIP 只是 deterministic transfer wrapper。本資源不宣稱 DOI、"
            "repository registration、外部 ingest、認證、背書或數位簽章。"
        ),
        "sources": "規範來源",
        "sources_text": (
            "METS 2.0 於 2025 年 3 月定稿；PREMIS 3.0 仍是目前的 "
            "Data Dictionary 與 XML schema generation。"
        ),
        "app_title": "完成典藏後的選用練習",
        "app_text": (
            "開放套件不需 App 即可使用。資料檢查與保存後，可選擇 Lumi Bopomofo "
            "作為裝置上的活動層。"
        ),
        "app_cta": "查看 Lumi Bopomofo",
        "footer": "開放資料 · CC BY 4.0 · 不需帳號或 API key，也不宣稱已登錄典藏庫",
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _timestamp_text(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _parse_timestamp(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Generation timestamp must include a UTC offset")
    return parsed.astimezone(dt.timezone.utc)


def _new_generation_timestamp(prior: str | None = None) -> str:
    current = _utc_now().astimezone(dt.timezone.utc).replace(microsecond=0)
    if prior:
        previous = _parse_timestamp(prior)
        if current <= previous:
            current = previous + dt.timedelta(seconds=1)
    return _timestamp_text(current)


def _q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _child(parent, namespace: str, name: str, text: str | None = None, **attrs):
    element = etree.SubElement(parent, _q(namespace, name), attrs)
    if text is not None:
        element.text = text
    return element


def _xml_bytes(root) -> bytes:
    return etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )


def _source_entries(pages: Path) -> dict[str, bytes]:
    entries = {
        README_FILENAME: README_TEXT.encode("utf-8"),
        LICENSE_FILENAME: LICENSE_TEXT.encode("utf-8"),
    }
    for spec in PAYLOAD_SPECS:
        if spec.source_path in entries:
            continue
        source = pages / spec.source_path
        if not source.is_file():
            raise FileNotFoundError(
                f"Build Bopomofo linked data before METS/PREMIS: {source}"
            )
        entries[spec.package_path] = source.read_bytes()
    return entries


def validate_reference_pin() -> None:
    expected = {
        "mets": (METS_SCHEMA_PATH, 88391, METS_SCHEMA_SHA256, METS_COMMIT),
        "premis": (PREMIS_SCHEMA_PATH, 52845, PREMIS_SCHEMA_SHA256, PREMIS_COMMIT),
    }
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    for key, (path, size, digest, commit) in expected.items():
        content = path.read_bytes()
        if len(content) != size or _sha256(content) != digest:
            raise ValueError(f"Pinned {key.upper()} schema bytes changed")
        if (
            sources[key]["bytes"] != size
            or sources[key]["sha256"] != digest
            or sources[key]["commit"] != commit
        ):
            raise ValueError(f"Pinned {key.upper()} provenance is inconsistent")


def _premis_identifier(parent, element: str, type_value: str, value: str) -> None:
    identifier = _child(parent, PREMIS_NS, element)
    prefix = element.removesuffix("Identifier")
    _child(identifier, PREMIS_NS, f"{prefix}IdentifierType", type_value)
    _child(identifier, PREMIS_NS, f"{prefix}IdentifierValue", value)


def render_premis(entries: dict[str, bytes], generated_at: str) -> bytes:
    root = etree.Element(
        _q(PREMIS_NS, "premis"),
        nsmap={"premis": PREMIS_NS, "xsi": XSI_NS},
        version="3.0",
    )
    object_ids = []
    for sequence, spec in enumerate(PAYLOAD_SPECS, 1):
        data = entries[spec.package_path]
        object_id = f"object-{sequence:03d}"
        object_ids.append(object_id)
        obj = _child(
            root,
            PREMIS_NS,
            "object",
            **{
                _q(XSI_NS, "type"): "premis:file",
                "xmlID": object_id,
                "version": "3.0",
            },
        )
        _premis_identifier(
            obj,
            "objectIdentifier",
            "URI",
            f"{PACKAGE_URL}{spec.package_path}",
        )
        characteristics = _child(obj, PREMIS_NS, "objectCharacteristics")
        _child(characteristics, PREMIS_NS, "compositionLevel", "0")
        fixity = _child(characteristics, PREMIS_NS, "fixity")
        _child(fixity, PREMIS_NS, "messageDigestAlgorithm", "SHA-256")
        _child(fixity, PREMIS_NS, "messageDigest", _sha256(data))
        _child(
            fixity,
            PREMIS_NS,
            "messageDigestOriginator",
            "iOS App Guide Open Resources",
        )
        _child(characteristics, PREMIS_NS, "size", str(len(data)))
        file_format = _child(characteristics, PREMIS_NS, "format")
        designation = _child(file_format, PREMIS_NS, "formatDesignation")
        _child(designation, PREMIS_NS, "formatName", spec.media_type)
        _child(obj, PREMIS_NS, "originalName", spec.package_path)
        storage = _child(obj, PREMIS_NS, "storage")
        location = _child(storage, PREMIS_NS, "contentLocation")
        _child(location, PREMIS_NS, "contentLocationType", "relative path")
        _child(location, PREMIS_NS, "contentLocationValue", spec.package_path)
        _child(storage, PREMIS_NS, "storageMedium", "deterministic ZIP entry")
        _premis_identifier(obj, "linkingEventIdentifier", "URI", EVENT_ID)
        _premis_identifier(
            obj,
            "linkingRightsStatementIdentifier",
            "URI",
            RIGHTS_ID,
        )

    event = _child(
        root,
        PREMIS_NS,
        "event",
        xmlID="event-package-generation",
        version="3.0",
    )
    _premis_identifier(event, "eventIdentifier", "URI", EVENT_ID)
    _child(event, PREMIS_NS, "eventType", "metadata creation")
    _child(event, PREMIS_NS, "eventDateTime", generated_at)
    detail = _child(event, PREMIS_NS, "eventDetailInformation")
    _child(
        detail,
        PREMIS_NS,
        "eventDetail",
        "Generated METS 2.0 and PREMIS 3.0 records and calculated SHA-256 fixity.",
    )
    outcome = _child(event, PREMIS_NS, "eventOutcomeInformation")
    _child(outcome, PREMIS_NS, "eventOutcome", "success")
    outcome_detail = _child(outcome, PREMIS_NS, "eventOutcomeDetail")
    _child(
        outcome_detail,
        PREMIS_NS,
        "eventOutcomeDetailNote",
        "All seven local files matched their recorded byte lengths and SHA-256 values.",
    )
    for value, role in (
        (PUBLISHER_ID, "implementer"),
        (GENERATOR_ID, "executing program"),
    ):
        identifier = _child(event, PREMIS_NS, "linkingAgentIdentifier")
        _child(identifier, PREMIS_NS, "linkingAgentIdentifierType", "URI")
        _child(identifier, PREMIS_NS, "linkingAgentIdentifierValue", value)
        _child(identifier, PREMIS_NS, "linkingAgentRole", role)
    for spec in PAYLOAD_SPECS:
        identifier = _child(event, PREMIS_NS, "linkingObjectIdentifier")
        _child(identifier, PREMIS_NS, "linkingObjectIdentifierType", "URI")
        _child(
            identifier,
            PREMIS_NS,
            "linkingObjectIdentifierValue",
            f"{PACKAGE_URL}{spec.package_path}",
        )
        _child(identifier, PREMIS_NS, "linkingObjectRole", "source")

    for xml_id, value, name, agent_type, role in (
        (
            "agent-publisher",
            PUBLISHER_ID,
            "iOS App Guide Open Resources",
            "organization",
            "implementer",
        ),
        (
            "agent-generator",
            GENERATOR_ID,
            "zhuyin_mets_premis_package.py",
            "software",
            "executing program",
        ),
    ):
        agent = _child(root, PREMIS_NS, "agent", xmlID=xml_id, version="3.0")
        _premis_identifier(agent, "agentIdentifier", "URI", value)
        _child(agent, PREMIS_NS, "agentName", name)
        _child(agent, PREMIS_NS, "agentType", agent_type)
        identifier = _child(agent, PREMIS_NS, "linkingEventIdentifier")
        _child(identifier, PREMIS_NS, "linkingEventIdentifierType", "URI")
        _child(identifier, PREMIS_NS, "linkingEventIdentifierValue", EVENT_ID)

    rights = _child(
        root,
        PREMIS_NS,
        "rights",
        xmlID="rights-cc-by-4-0",
        version="3.0",
    )
    statement = _child(rights, PREMIS_NS, "rightsStatement")
    _premis_identifier(
        statement,
        "rightsStatementIdentifier",
        "URI",
        RIGHTS_ID,
    )
    _child(statement, PREMIS_NS, "rightsBasis", "license")
    license_information = _child(statement, PREMIS_NS, "licenseInformation")
    documentation = _child(
        license_information,
        PREMIS_NS,
        "licenseDocumentationIdentifier",
    )
    _child(documentation, PREMIS_NS, "licenseDocumentationIdentifierType", "URI")
    _child(
        documentation,
        PREMIS_NS,
        "licenseDocumentationIdentifierValue",
        LICENSE,
    )
    _child(documentation, PREMIS_NS, "licenseDocumentationRole", "license")
    _child(
        license_information,
        PREMIS_NS,
        "licenseTerms",
        "Creative Commons Attribution 4.0 International (CC BY 4.0).",
    )
    for act in ("replicate", "migrate", "disseminate", "modify"):
        grant = _child(statement, PREMIS_NS, "rightsGranted")
        _child(grant, PREMIS_NS, "act", act)
        _child(
            grant,
            PREMIS_NS,
            "rightsGrantedNote",
            "Permitted with attribution and indication of changes under CC BY 4.0.",
        )
    for spec in PAYLOAD_SPECS:
        identifier = _child(statement, PREMIS_NS, "linkingObjectIdentifier")
        _child(identifier, PREMIS_NS, "linkingObjectIdentifierType", "URI")
        _child(
            identifier,
            PREMIS_NS,
            "linkingObjectIdentifierValue",
            f"{PACKAGE_URL}{spec.package_path}",
        )
        _child(identifier, PREMIS_NS, "linkingObjectRole", "governed object")
    return _xml_bytes(root)


def render_mets(
    entries: dict[str, bytes],
    premis_bytes: bytes,
    generated_at: str,
) -> bytes:
    root = etree.Element(
        _q(METS_NS, "mets"),
        nsmap={"mets": METS_NS, "xsi": XSI_NS},
        OBJID=OBJECT_ID,
        LABEL="Bopomofo 37-Symbol Open Reference Preservation Package",
        TYPE="Dataset",
    )
    root.set(
        _q(XSI_NS, "schemaLocation"),
        f"{METS_NS} {METS_SCHEMA_URL}",
    )
    header = _child(
        root,
        METS_NS,
        "metsHdr",
        CREATEDATE=generated_at,
        LASTMODDATE=generated_at,
        RECORDSTATUS="complete",
    )
    for role, agent_type, name in (
        ("CREATOR", "ORGANIZATION", "iOS App Guide Open Resources"),
        ("CREATOR", "SOFTWARE", "zhuyin_mets_premis_package.py"),
    ):
        agent = _child(header, METS_NS, "agent", ROLE=role, TYPE=agent_type)
        _child(agent, METS_NS, "name", name)
    _child(header, METS_NS, "metsDocumentID", METS_URL, TYPE="URI")

    metadata_section = _child(root, METS_NS, "mdSec")
    metadata = _child(
        metadata_section,
        METS_NS,
        "md",
        ID="md-premis",
        USE="TECHNICAL PROVENANCE RIGHTS",
        CREATED=generated_at,
        STATUS="current",
    )
    _child(
        metadata,
        METS_NS,
        "mdRef",
        MDTYPE="PREMIS",
        MDTYPEVERSION="3.0",
        LOCTYPE="URL",
        LOCREF=PREMIS_FILENAME,
        MIMETYPE="application/xml",
        SIZE=str(len(premis_bytes)),
        CHECKSUM=_sha256(premis_bytes),
        CHECKSUMTYPE="SHA-256",
        LABEL="Complete PREMIS 3.0 preservation metadata",
    )

    file_section = _child(root, METS_NS, "fileSec", ID="files")
    file_ids = {}
    for group_name in ("DATA", "DOCUMENTATION"):
        group_specs = [spec for spec in PAYLOAD_SPECS if spec.group == group_name]
        group = _child(
            file_section,
            METS_NS,
            "fileGrp",
            ID=f"group-{group_name.lower()}",
            USE=group_name,
            MDID="md-premis",
        )
        for spec in group_specs:
            sequence = PAYLOAD_SPECS.index(spec) + 1
            file_id = f"file-{sequence:03d}"
            file_ids[spec.package_path] = file_id
            data = entries[spec.package_path]
            file_element = _child(
                group,
                METS_NS,
                "file",
                ID=file_id,
                SEQ=str(sequence),
                MIMETYPE=spec.media_type,
                SIZE=str(len(data)),
                CHECKSUM=_sha256(data),
                CHECKSUMTYPE="SHA-256",
                OWNERID=f"{PACKAGE_URL}{spec.package_path}",
                MDID="md-premis",
                USE=group_name,
            )
            _child(
                file_element,
                METS_NS,
                "FLocat",
                LOCTYPE="URL",
                LOCREF=spec.package_path,
                USE="PRESERVATION",
            )

    structure_section = _child(root, METS_NS, "structSec", ID="structures")
    structure_map = _child(
        structure_section,
        METS_NS,
        "structMap",
        ID="struct-logical",
        TYPE="LOGICAL",
        LABEL="Bopomofo preservation package structure",
    )
    package_division = _child(
        structure_map,
        METS_NS,
        "div",
        ID="div-package",
        TYPE="DATASET",
        LABEL="Bopomofo 37-Symbol Open Reference Data",
        MDID="md-premis",
        CONTENTIDS=OBJECT_ID,
    )
    for group_name, label in (
        ("DATA", "Reusable data and standards metadata"),
        ("DOCUMENTATION", "Validation and attribution documentation"),
    ):
        division = _child(
            package_division,
            METS_NS,
            "div",
            ID=f"div-{group_name.lower()}",
            TYPE=group_name,
            LABEL=label,
            MDID="md-premis",
        )
        for spec in PAYLOAD_SPECS:
            if spec.group == group_name:
                _child(
                    division,
                    METS_NS,
                    "fptr",
                    FILEID=file_ids[spec.package_path],
                )
    return _xml_bytes(root)


def _checksum_bytes(entries: dict[str, bytes]) -> bytes:
    return (
        "\n".join(f"{_sha256(entries[path])}  {path}" for path in sorted(entries))
        + "\n"
    ).encode("ascii")


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path, content in entries.items():
            info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return stream.getvalue()


def make_artifacts(pages: Path, generated_at: str) -> dict[str, bytes]:
    _parse_timestamp(generated_at)
    validate_reference_pin()
    entries = _source_entries(pages)
    premis_bytes = render_premis(entries, generated_at)
    mets_bytes = render_mets(entries, premis_bytes, generated_at)
    ordered = {
        METS_FILENAME: mets_bytes,
        PREMIS_FILENAME: premis_bytes,
        README_FILENAME: entries[README_FILENAME],
        LICENSE_FILENAME: entries[LICENSE_FILENAME],
    }
    for spec in PAYLOAD_SPECS:
        if spec.group == "DATA":
            ordered[spec.package_path] = entries[spec.package_path]
    checksums = _checksum_bytes(ordered)
    members = {**ordered, CHECKSUM_FILENAME: checksums}
    artifacts = {**members, BUNDLE_FILENAME: _zip_bytes(members)}
    validate_artifacts(artifacts, generated_at)
    return artifacts


def _validate_xml(content: bytes, schema_path: Path):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(content, parser)
    schema = etree.XMLSchema(etree.parse(str(schema_path), parser))
    schema.assertValid(root)
    return root


def validate_artifacts(artifacts: dict[str, bytes], generated_at: str) -> None:
    _parse_timestamp(generated_at)
    validate_reference_pin()
    expected_members = [
        METS_FILENAME,
        PREMIS_FILENAME,
        README_FILENAME,
        LICENSE_FILENAME,
        *(spec.package_path for spec in PAYLOAD_SPECS if spec.group == "DATA"),
        CHECKSUM_FILENAME,
    ]
    if list(artifacts) != [*expected_members, BUNDLE_FILENAME]:
        raise ValueError("METS/PREMIS artifact order or membership is invalid")

    mets = _validate_xml(artifacts[METS_FILENAME], METS_SCHEMA_PATH)
    premis = _validate_xml(artifacts[PREMIS_FILENAME], PREMIS_SCHEMA_PATH)
    ns = {"mets": METS_NS, "premis": PREMIS_NS}
    if mets.get("OBJID") != OBJECT_ID or _q(METS_NS, "mets") != mets.tag:
        raise ValueError("METS root identifier or namespace is invalid")
    if "xlink" in artifacts[METS_FILENAME].decode("utf-8").lower():
        raise ValueError("METS 2 package must not rely on removed XLink attributes")
    md_ref = mets.find("mets:mdSec/mets:md/mets:mdRef", ns)
    if md_ref is None or md_ref.attrib != {
        "MDTYPE": "PREMIS",
        "MDTYPEVERSION": "3.0",
        "LOCTYPE": "URL",
        "LOCREF": PREMIS_FILENAME,
        "MIMETYPE": "application/xml",
        "SIZE": str(len(artifacts[PREMIS_FILENAME])),
        "CHECKSUM": _sha256(artifacts[PREMIS_FILENAME]),
        "CHECKSUMTYPE": "SHA-256",
        "LABEL": "Complete PREMIS 3.0 preservation metadata",
    }:
        raise ValueError("METS PREMIS mdRef is incomplete")

    file_elements = mets.findall("mets:fileSec/mets:fileGrp/mets:file", ns)
    if len(file_elements) != len(PAYLOAD_SPECS):
        raise ValueError("METS fileSec must inventory seven preserved files")
    file_ids = set()
    for element, spec in zip(file_elements, PAYLOAD_SPECS):
        data = artifacts[spec.package_path]
        location = element.find("mets:FLocat", ns)
        if (
            element.get("MIMETYPE") != spec.media_type
            or element.get("SIZE") != str(len(data))
            or element.get("CHECKSUM") != _sha256(data)
            or element.get("CHECKSUMTYPE") != "SHA-256"
            or location is None
            or location.get("LOCREF") != spec.package_path
        ):
            raise ValueError(f"METS file fixity mismatch: {spec.package_path}")
        file_ids.add(element.get("ID"))
    pointer_ids = {
        pointer.get("FILEID")
        for pointer in mets.findall(".//mets:structMap//mets:fptr", ns)
    }
    if pointer_ids != file_ids:
        raise ValueError("METS structMap must point to every file exactly once")

    objects = premis.findall("premis:object", ns)
    events = premis.findall("premis:event", ns)
    agents = premis.findall("premis:agent", ns)
    rights = premis.findall("premis:rights", ns)
    if (len(objects), len(events), len(agents), len(rights)) != (7, 1, 2, 1):
        raise ValueError("PREMIS entity counts are incomplete")
    object_identifiers = set()
    for obj, spec in zip(objects, PAYLOAD_SPECS):
        identifier_type = obj.findtext(
            "premis:objectIdentifier/premis:objectIdentifierType",
            namespaces=ns,
        )
        identifier_value = obj.findtext(
            "premis:objectIdentifier/premis:objectIdentifierValue",
            namespaces=ns,
        )
        object_identifiers.add((identifier_type, identifier_value))
        original = obj.findtext("premis:originalName", namespaces=ns)
        digest = obj.findtext(
            "premis:objectCharacteristics/premis:fixity/premis:messageDigest",
            namespaces=ns,
        )
        size = obj.findtext(
            "premis:objectCharacteristics/premis:size",
            namespaces=ns,
        )
        media_type = obj.findtext(
            (
                "premis:objectCharacteristics/premis:format/"
                "premis:formatDesignation/premis:formatName"
            ),
            namespaces=ns,
        )
        data = artifacts[spec.package_path]
        if (
            original != spec.package_path
            or digest != _sha256(data)
            or size != str(len(data))
            or media_type != spec.media_type
        ):
            raise ValueError(f"PREMIS Object mismatch: {spec.package_path}")
    event_links = {
        (
            element.findtext(
                "premis:linkingObjectIdentifierType",
                namespaces=ns,
            ),
            element.findtext(
                "premis:linkingObjectIdentifierValue",
                namespaces=ns,
            ),
        )
        for element in events[0].findall("premis:linkingObjectIdentifier", ns)
    }
    rights_links = {
        (
            element.findtext(
                "premis:linkingObjectIdentifierType",
                namespaces=ns,
            ),
            element.findtext(
                "premis:linkingObjectIdentifierValue",
                namespaces=ns,
            ),
        )
        for element in rights[0].findall(
            "premis:rightsStatement/premis:linkingObjectIdentifier",
            ns,
        )
    }
    if (
        event_links != object_identifiers
        or rights_links != object_identifiers
    ):
        raise ValueError("PREMIS Event and Rights must link every File Object")
    if (
        events[0].findtext("premis:eventDateTime", namespaces=ns)
        != generated_at
    ):
        raise ValueError("PREMIS event timestamp mismatch")

    expected_checksums = _checksum_bytes(
        {path: artifacts[path] for path in expected_members[:-1]}
    )
    if artifacts[CHECKSUM_FILENAME] != expected_checksums:
        raise ValueError("METS/PREMIS checksum list mismatch")
    with zipfile.ZipFile(io.BytesIO(artifacts[BUNDLE_FILENAME])) as archive:
        if archive.namelist() != expected_members:
            raise ValueError("METS/PREMIS ZIP membership or order is invalid")
        for info in archive.infolist():
            if (
                info.date_time != ZIP_TIMESTAMP
                or info.compress_type != zipfile.ZIP_DEFLATED
                or info.external_attr >> 16 != 0o100644
                or archive.read(info.filename) != artifacts[info.filename]
            ):
                raise ValueError(f"Non-deterministic ZIP entry: {info.filename}")
    csv_rows = list(
        csv.DictReader(
            io.StringIO(
                artifacts["data/zhuyin-bopomofo-ml-dataset.csv"].decode("utf-8")
            )
        )
    )
    jsonl_rows = [
        json.loads(line)
        for line in artifacts["data/zhuyin-bopomofo-ml-dataset.jsonl"]
        .decode("utf-8")
        .splitlines()
    ]
    if len(csv_rows) != 37 or len(jsonl_rows) != 37:
        raise ValueError("METS/PREMIS core data must contain all 37 symbols")
    for path in expected_members:
        text = artifacts[path].decode("utf-8")
        for forbidden in FORBIDDEN:
            if forbidden.lower() in text.lower():
                raise ValueError(
                    f"METS/PREMIS machine artifact contains forbidden text: {forbidden}"
                )


def metadata_document(artifacts: dict[str, bytes], generated_at: str) -> dict:
    formats = {
        BUNDLE_FILENAME: "application/zip",
        METS_FILENAME: "application/xml",
        PREMIS_FILENAME: "application/xml",
        CHECKSUM_FILENAME: "text/plain",
    }
    return {
        "@context": "https://schema.org",
        "@type": ["Dataset", "LearningResource"],
        "@id": OBJECT_ID,
        "identifier": OBJECT_ID,
        "name": "Bopomofo METS 2.0 and PREMIS 3.0 Preservation Package",
        "alternateName": "注音 METS 2.0 與 PREMIS 3.0 數位典藏套件",
        "description": (
            "A deterministic repository-transfer package for the complete "
            "37-symbol Bopomofo dataset with METS and PREMIS preservation metadata."
        ),
        "url": OBJECT_ID,
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": generated_at,
        "inLanguage": ["en", "zh-Hant"],
        "isAccessibleForFree": True,
        "license": LICENSE,
        "creator": {
            "@type": "Organization",
            "@id": PUBLISHER_ID,
            "name": "iOS App Guide Open Resources",
        },
        "conformsTo": [METS_SCHEMA_URL, PREMIS_GUIDE_URL],
        "keywords": [
            "METS 2.0",
            "PREMIS 3.0",
            "digital preservation",
            "repository transfer",
            "Bopomofo",
            "Zhuyin",
        ],
        "distribution": [
            {
                "@type": "DataDownload",
                "name": name,
                "contentUrl": f"{PACKAGE_URL}{filename}",
                "encodingFormat": formats[filename],
                "contentSize": len(artifacts[filename]),
                "sha256": _sha256(artifacts[filename]),
            }
            for filename, name in (
                (BUNDLE_FILENAME, "Complete deterministic ZIP"),
                (METS_FILENAME, "METS 2.0 record"),
                (PREMIS_FILENAME, "PREMIS 3.0 record"),
                (CHECKSUM_FILENAME, "SHA-256 checksum list"),
            )
        ],
        "hasPart": [
            {
                "@type": "DataDownload",
                "name": spec.name,
                "contentUrl": f"{PACKAGE_URL}{spec.package_path}",
                "encodingFormat": spec.media_type,
                "contentSize": len(artifacts[spec.package_path]),
                "sha256": _sha256(artifacts[spec.package_path]),
            }
            for spec in PAYLOAD_SPECS
        ],
    }


def _metadata_bytes(artifacts: dict[str, bytes], generated_at: str) -> bytes:
    return (
        json.dumps(
            metadata_document(artifacts, generated_at),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_rows(artifacts: dict[str, bytes], copy: dict) -> str:
    return "".join(
        "<tr>"
        f'<td><a href="{PACKAGE_URL}{html.escape(spec.package_path, quote=True)}">'
        f"{html.escape(spec.package_path)}</a></td>"
        f"<td>{html.escape(spec.media_type)}</td>"
        f"<td>{len(artifacts[spec.package_path]):,}</td>"
        f"<td><code>{_sha256(artifacts[spec.package_path])[:16]}…</code></td>"
        "</tr>"
        for spec in PAYLOAD_SPECS
    )


def render_page(
    locale: str,
    artifacts: dict[str, bytes],
    generated_at: str,
    page_modified: str,
    app_public: bool,
) -> str:
    copy = COPY[locale]
    canonical = PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL
    alternate = ZH_PACKAGE_URL if locale == "en" else PACKAGE_URL
    schema_graph = [
        metadata_document(artifacts, generated_at),
        {
            "@type": "WebPage",
            "@id": canonical,
            "url": canonical,
            "name": copy["title"],
            "dateModified": page_modified,
            "inLanguage": copy["lang"],
            "mainEntity": {"@id": OBJECT_ID},
        },
    ]
    if app_public:
        schema_graph.append(
            {
                "@type": "SoftwareApplication",
                "applicationCategory": "EducationApplication",
                "name": APP_NAME,
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_mets_premis_{locale.lower()}"),
            }
        )
    downloads = "".join(
        f'<a class="download{" primary" if filename == BUNDLE_FILENAME else ""}" '
        f'href="{PACKAGE_URL}{filename}"><strong>{html.escape(label)}</strong>'
        f"<span>{len(artifacts[filename]):,} bytes · {_sha256(artifacts[filename])[:16]}…"
        "</span></a>"
        for filename, label in (
            (BUNDLE_FILENAME, copy["bundle"]),
            (METS_FILENAME, copy["mets"]),
            (PREMIS_FILENAME, copy["premis"]),
            (CHECKSUM_FILENAME, copy["checksums"]),
        )
    )
    downloads += (
        f'<a class="download" href="{METADATA_URL}"><strong>'
        f'{html.escape(copy["metadata"])}</strong><span>JSON-LD · Schema.org</span></a>'
    )
    model_items = "".join(f"<li>{html.escape(item)}</li>" for item in copy["model_items"])
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel optional"><h2>'
            f'{html.escape(copy["app_title"])}</h2><p>{html.escape(copy["app_text"])}</p>'
            f'<a class="button" href="{appstore_url(APP_KEY, "iag_mets_premis")}">'
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
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<link rel="describedby" type="application/xml" href="{METS_URL}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": schema_graph}, ensure_ascii=False)}</script>
<style>
:root{{--ink:#152033;--muted:#5b6577;--line:#dce2ea;--paper:#fff;--accent:#285a70;--soft:#eaf5f5}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.65 system-ui,sans-serif;color:var(--ink);background:linear-gradient(180deg,#f3f8f8,#fff)}}
a{{color:#14637d}}.wrap{{width:min(1120px,calc(100% - 32px));margin:auto}}header{{padding:18px 0}}nav{{display:flex;justify-content:space-between;gap:12px}}nav a,.button{{white-space:nowrap}}
.hero{{padding:50px 0 22px}}.eyebrow{{font-weight:850;color:var(--accent);letter-spacing:.06em;text-transform:uppercase;white-space:nowrap;overflow:auto}}h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.04;margin:.2em 0}}.lead{{font-size:1.15rem;color:var(--muted);max-width:820px}}
.badges{{display:flex;gap:8px;flex-wrap:wrap}}.badge{{padding:6px 11px;border-radius:999px;background:var(--soft);font-weight:800;white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 10px 34px rgba(30,70,80,.07);margin:18px 0}}
.download{{display:flex;justify-content:space-between;gap:14px;align-items:center;padding:14px 16px;border:1px solid var(--line);border-radius:14px;text-decoration:none;margin:10px 0}}.download span{{color:var(--muted);font-size:.86rem;white-space:nowrap}}.download.primary{{background:var(--accent);color:#fff;border-color:var(--accent)}}.download.primary span{{color:#eaf5f5}}
table{{width:100%;border-collapse:collapse;display:block;overflow:auto}}th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}code{{font-size:.78rem}}.sources{{display:flex;gap:10px;flex-wrap:wrap}}.sources a,.button{{display:inline-block;padding:10px 15px;border-radius:999px;text-decoration:none;font-weight:800;white-space:nowrap}}.sources a{{background:var(--soft)}}.button{{background:var(--accent);color:#fff}}.optional{{border-style:dashed}}footer{{padding:32px 0;color:var(--muted)}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.download{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<header class="wrap"><nav><a href="{SITE}/data/">{html.escape(copy['back'])}</a><a href="{alternate}">{html.escape(copy['language'])}</a></nav></header>
<main>
<section class="hero wrap"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges"><span class="badge">METS 2.0</span><span class="badge">PREMIS 3.0</span><span class="badge">SHA-256</span><span class="badge">37 symbols</span></div></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p>{downloads}</article><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><div class="sources"><a href="{METS_SCHEMA_URL}">METS 2.0 XSD</a><a href="{PREMIS_SCHEMA_URL}">PREMIS 3.0 XSD</a></div></article></section>
<section class="wrap panel"><h2>{html.escape(copy['inventory'])}</h2><table><thead><tr><th>{html.escape(copy['path'])}</th><th>{html.escape(copy['format'])}</th><th>{html.escape(copy['bytes'])}</th><th>{html.escape(copy['sha'])}</th></tr></thead><tbody>{_artifact_rows(artifacts, copy)}</tbody></table></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['model'])}</h2><ul>{model_items}</ul></article><article class="panel"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limits_text'])}</p></article></section>
<section class="wrap panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['sources_text'])}</p><div class="sources"><a href="{METS_GUIDE_URL}">METS 2</a><a href="{METS_REPOSITORY}/commit/{METS_COMMIT}">METS source</a><a href="{PREMIS_GUIDE_URL}">PREMIS 3</a><a href="{PREMIS_REPOSITORY}/commit/{PREMIS_COMMIT}">PREMIS source</a><a href="{LICENSE}" rel="license">CC BY 4.0</a></div></section>
<div class="wrap">{app_section}</div>
</main>
<footer class="wrap">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def _prior_generation_timestamp(metadata_path: Path) -> str | None:
    if not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        value = metadata["dateModified"]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return None
        parsed = _parse_timestamp(value)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Existing METS/PREMIS metadata is invalid: {metadata_path}") from error
    return _timestamp_text(parsed)


def _artifacts_changed(package_dir: Path, artifacts: dict[str, bytes]) -> bool:
    return any(
        not (package_dir / path).is_file()
        or (package_dir / path).read_bytes() != content
        for path, content in artifacts.items()
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
    generated_at: str,
) -> bool:
    index = pages / "data" / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"Data index must exist before METS/PREMIS: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'{CARD_START}<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo METS 2.0 + PREMIS 3.0 preservation package</h2>"
        "<p>Repository-transfer inventory, structure, provenance, rights and "
        "per-file SHA-256 for the complete 37-symbol dataset.</p>"
        '<span class="tag">METS 2.0 · PREMIS 3.0 · EN + zh-Hant</span></a>'
        f"{CARD_END}"
    )
    updated = re.sub(
        re.escape(CARD_START) + r".*?" + re.escape(CARD_END),
        "",
        text,
        flags=re.DOTALL,
    )
    anchor = re.search(
        r'<a class="item" href="' + re.escape(
            f"{SITE}/data/packages/zhuyin-bopomofo-ro-crate/"
        ) + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if anchor:
        updated = updated[: anchor.end()] + card + updated[anchor.end() :]
    else:
        footer = updated.find('<p class="foot">')
        if footer < 0:
            raise RuntimeError("data/index.html has no METS/PREMIS insertion anchor")
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
    entry = metadata_document(artifacts, generated_at)
    position = next(
        (
            index + 1
            for index, item in enumerate(datasets)
            if item.get("url")
            == f"{SITE}/data/packages/zhuyin-bopomofo-ro-crate/"
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


def render_sitemap(generated_at: str, page_modified: dict[str, str]) -> str:
    urls = (
        (PACKAGE_URL, page_modified["en"]),
        (ZH_PACKAGE_URL, page_modified["zh-Hant"]),
        *(
            (f"{PACKAGE_URL}{filename}", generated_at)
            for filename in (
                METS_FILENAME,
                PREMIS_FILENAME,
                README_FILENAME,
                LICENSE_FILENAME,
                *(spec.package_path for spec in PAYLOAD_SPECS if spec.group == "DATA"),
                CHECKSUM_FILENAME,
                METADATA_FILENAME,
                BUNDLE_FILENAME,
            )
        ),
    )
    rows = "\n".join(
        f"  <url><loc>{html.escape(url)}</loc><lastmod>{modified}</lastmod></url>"
        for url, modified in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def _is_app_public(pages: Path) -> bool:
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    package_dir = pages / PACKAGE_PATH
    package_dir.mkdir(parents=True, exist_ok=True)
    prior_generated_at = _prior_generation_timestamp(
        package_dir / METADATA_FILENAME
    )
    generated_at = prior_generated_at or _new_generation_timestamp()
    artifacts = make_artifacts(pages, generated_at)
    if (
        prior_generated_at is None
        or _artifacts_changed(package_dir, artifacts)
    ):
        if prior_generated_at is not None:
            generated_at = _new_generation_timestamp(prior_generated_at)
            artifacts = make_artifacts(pages, generated_at)
    for relative, content in artifacts.items():
        _write_bytes_if_changed(package_dir / relative, content)
    _write_bytes_if_changed(
        package_dir / METADATA_FILENAME,
        _metadata_bytes(artifacts, generated_at),
    )

    public = _is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", package_dir / "index.html"),
        ("zh-Hant", pages / "zh-Hant" / PACKAGE_PATH / "index.html"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_page(
                locale,
                artifacts,
                generated_at,
                modified,
                public,
            ),
            INITIAL_DATE,
        )
    update_data_index(pages, artifacts, generated_at)
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(generated_at, page_modified),
    )
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        *(
            f"{PACKAGE_URL}{filename}"
            for filename in (
                METS_FILENAME,
                PREMIS_FILENAME,
                README_FILENAME,
                LICENSE_FILENAME,
                *(spec.package_path for spec in PAYLOAD_SPECS if spec.group == "DATA"),
                CHECKSUM_FILENAME,
                METADATA_FILENAME,
                BUNDLE_FILENAME,
            )
        ),
    ]


def main() -> None:
    urls = build()
    print(f"Published METS 2.0 + PREMIS 3.0 package ({len(urls)} URLs)")
    for url in urls:
        print(url)


if __name__ == "__main__":
    main()
