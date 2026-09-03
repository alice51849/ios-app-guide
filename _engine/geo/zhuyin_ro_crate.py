#!/usr/bin/env python3
"""Publish an attached RO-Crate 1.3 package for the open Bopomofo data."""

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

from rdflib import Graph


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import write_text_if_changed  # noqa: E402
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
TODAY = dt.datetime.now(dt.timezone.utc).date().isoformat()
VERSION = "1.0.0"

PACKAGE_SLUG = "zhuyin-bopomofo-ro-crate"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
ROOT_ID = PACKAGE_URL
IDENTIFIER_ID = f"{ROOT_ID}#identifier"
PUBLISHER_ID = f"{ROOT_ID}#publisher"
MOE_REFERENCE_ID = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
MOE_PUBLISHER_ID = "https://www.edu.tw/"

METADATA_FILENAME = "ro-crate-metadata.json"
PREVIEW_FILENAME = "ro-crate-preview.html"
README_FILENAME = "README.txt"
LICENSE_FILENAME = "LICENSE.txt"
CHECKSUM_FILENAME = "checksums-sha256.txt"
BUNDLE_FILENAME = "bopomofo-37-symbols-ro-crate-1.3.zip"
SITEMAP_PATH = Path("sitemap_ro_crate_bopomofo.xml")
CARD_START = "<!-- bopomofo-ro-crate:start -->"
CARD_END = "<!-- bopomofo-ro-crate:end -->"

METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
PREVIEW_URL = f"{PACKAGE_URL}{PREVIEW_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"

PROFILE = "https://w3id.org/ro/crate/1.3"
CONTEXT = "https://w3id.org/ro/crate/1.3/context"
SPEC_URL = "https://www.researchobject.org/ro-crate/specification/1.3/"
SPEC_REPOSITORY = "https://github.com/ResearchObject/ro-crate"
SPEC_COMMIT = "4b4f939c18022550ae0b992b7ddfb2cb5b2e8608"
CONTEXT_SHA256 = "5a3df1a43185501db4d45cdde5a478c57eeb1d673eedfe400488fc4c4b21dd91"
REFERENCE_DIR = HERE / "reference_datasets" / "ro-crate-1.3"
CONTEXT_PATH = REFERENCE_DIR / "context.jsonld"
SOURCES_PATH = REFERENCE_DIR / "sources.json"

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
CONTENT_MODIFIED_RE = re.compile(
    r'<meta name="content-modified" content="(\d{4}-\d{2}-\d{2})">'
)
FORBIDDEN = (
    "apps.apple.com",
    "SoftwareApplication",
    APP_NAME,
    APP_ID,
)


@dataclass(frozen=True)
class PayloadSpec:
    source_path: str
    crate_path: str
    name: str
    description: str
    encoding_format: str
    conforms_to: str | None = None


PAYLOAD_SPECS = (
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "Canonical 37-row Bopomofo table",
        (
            "UTF-8 table covering all 37 Bopomofo symbols with stable IDs, "
            "Unicode notation, Hanyu Pinyin, broad IPA, categories and examples."
        ),
        "text/csv",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "Equivalent Bopomofo JSON Lines records",
        "One UTF-8 JSON object per Bopomofo symbol in canonical display order.",
        "application/x-ndjson",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        "MLCommons Croissant metadata",
        (
            "Croissant 1.1 metadata describing the canonical CSV and JSON Lines "
            "records, fields, source provenance and CC BY 4.0 reuse terms."
        ),
        "application/ld+json",
        "http://mlcommons.org/croissant/1.1",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "W3C CSVW metadata",
        (
            "CSV on the Web metadata describing the canonical table dialect, "
            "required columns, datatypes, primary key and URI templates."
        ),
        "application/csvm+json",
        "https://www.w3.org/TR/tabular-metadata/",
    ),
    PayloadSpec(
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "Bopomofo SKOS vocabulary",
        (
            "JSON-LD SKOS concept scheme for all 37 Bopomofo symbols with stable "
            "concept IRIs, bilingual labels and phonetic notation."
        ),
        "application/ld+json",
        "https://www.w3.org/TR/skos-reference/",
    ),
)


README_TEXT = """Bopomofo 37-Symbol RO-Crate 1.3
==================================

This attached RO-Crate packages the complete 37-symbol Bopomofo reference table
with JSON Lines, Croissant 1.1, W3C CSVW and SKOS JSON-LD metadata.

Open guide: {GUIDE}/data/packages/zhuyin-bopomofo-ro-crate/
Traditional Chinese guide: {GUIDE}/zh-Hant/data/packages/zhuyin-bopomofo-ro-crate/
Specification: https://w3id.org/ro/crate/1.3

Validation
----------
1. Verify checksums-sha256.txt.
2. Confirm ro-crate-metadata.json uses the RO-Crate 1.3 context and descriptor.
3. Parse the JSON-LD with the pinned official context.
4. Confirm all hasPart paths exist and match their byte lengths and SHA-256.

Scope
-----
This package contains reference data and standards metadata. It does not contain
audio, learner records, accounts, analytics or tracking. Publication does not
assign a DOI, register a repository deposit, certify the crate or prove ingest by
an external service.

繁體中文
--------
本 RO-Crate 1.3 套件收錄完整 37 個注音符號參考表、JSON Lines、Croissant
1.1、W3C CSVW 與 SKOS JSON-LD metadata。請先驗證 checksums-sha256.txt，
再檢查 ro-crate-metadata.json、所有 hasPart 路徑、byte 長度與 SHA-256。
本套件不含音訊、學習者紀錄、帳號、分析或追蹤；發布不代表取得 DOI、已登錄
典藏庫、獲得 RO-Crate 認證，或已被外部服務匯入。
""".replace("{GUIDE}", PUBLIC_SITE)

LICENSE_TEXT = """Creative Commons Attribution 4.0 International (CC BY 4.0)

The Bopomofo data and package-authored metadata are licensed under CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/

Attribution:
Bopomofo 37-Symbol Open Reference Data, iOS App Guide Open Resources.
{GUIDE}/data/packages/zhuyin-bopomofo-ro-crate/

The pinned RO-Crate JSON-LD context is distributed by the RO-Crate contributors
under CC0 1.0 and is used for offline validation; it is not included in the crate.
""".replace("{GUIDE}", PUBLIC_SITE)


COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo 37-Symbol RO-Crate 1.3 Research Object",
        "description": (
            "Download a deterministic RO-Crate 1.3 package for all 37 Bopomofo "
            "symbols, with CSV, JSON Lines, Croissant, CSVW, SKOS and SHA-256."
        ),
        "eyebrow": "RO-Crate 1.3 · 37 symbols · deterministic package",
        "lead": (
            "A self-contained research object for repositories, digital-humanities "
            "tools and reproducible reuse of the open Bopomofo reference data."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "downloads": "Research object downloads",
        "download_text": (
            "Use the attached ZIP for transfer, or inspect the same files directly "
            "on the web. Every packaged member except the checksum list has an exact "
            "SHA-256 entry."
        ),
        "bundle": "Complete RO-Crate ZIP",
        "metadata": "RO-Crate metadata",
        "preview": "Static crate preview",
        "checksums": "SHA-256 checksums",
        "payload": "Packaged data entities",
        "path": "Crate path",
        "format": "Format",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "validate": "Validate independently",
        "validate_text": (
            "The generator checks the pinned official 1.3 context, required "
            "descriptor and root fields, JSON-LD expansion, every local path, byte "
            "length, digest, ZIP member and checksum. The currently available "
            "third-party validator profiles stop at 1.2, so this page does not claim "
            "third-party 1.3 certification."
        ),
        "scope": "Scope and limits",
        "scope_items": (
            "The package contains complete 37-symbol reference data and standards metadata, not audio or learner records.",
            "The canonical URL is a web identifier; no DOI has been assigned.",
            "Publication does not register a repository deposit or prove external ingest.",
            "Checksums detect byte changes but are not signatures or independent authenticity proof.",
            "RO-Crate conformance does not imply endorsement or certification by the RO-Crate community.",
        ),
        "sources": "Standards and provenance",
        "sources_text": (
            "The metadata follows the RO-Crate 1.3.0 Recommendation and uses the "
            "official context pinned to an immutable public source commit. The data "
            "retains its source provenance and CC BY 4.0 attribution."
        ),
        "app_title": "Optional learning companion",
        "app_text": (
            "The research object is complete and reusable without an app. Lumi "
            "Bopomofo is an optional on-device practice layer."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": "Open research object · No account · No API key · No deposit claim",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "完整 37 注音符號 RO-Crate 1.3 研究物件",
        "description": (
            "下載完整 37 注音符號的 deterministic RO-Crate 1.3 套件，包含 CSV、"
            "JSON Lines、Croissant、CSVW、SKOS 與 SHA-256。"
        ),
        "eyebrow": "RO-Crate 1.3 · 37 個符號 · deterministic package",
        "lead": (
            "供典藏庫、數位人文工具與可重現資料重用使用的自含式注音開放資料"
            "研究物件。"
        ),
        "back": "開放資料",
        "language": "English",
        "downloads": "研究物件下載",
        "download_text": (
            "可下載 attached ZIP 進行移轉，也可直接在網頁檢查相同檔案。除了"
            "checksum 清單本身，每個 package member 都有精確 SHA-256。"
        ),
        "bundle": "完整 RO-Crate ZIP",
        "metadata": "RO-Crate metadata",
        "preview": "靜態 crate preview",
        "checksums": "SHA-256 checksums",
        "payload": "封裝的 data entities",
        "path": "Crate 路徑",
        "format": "格式",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "validate": "獨立驗證",
        "validate_text": (
            "Generator 會檢查固定版本的官方 1.3 context、必要 descriptor 與 root "
            "欄位、JSON-LD 展開、所有本地路徑、byte 長度、digest、ZIP member "
            "與 checksum。目前可用的第三方 validator profile 只到 1.2，因此"
            "本頁不宣稱取得第三方 1.3 認證。"
        ),
        "scope": "範圍與限制",
        "scope_items": (
            "套件包含完整 37 符號參考資料與標準 metadata，不含音訊或學習者紀錄。",
            "Canonical URL 是網頁識別碼，沒有取得 DOI。",
            "發布不代表已登錄典藏庫，也不證明已被外部系統匯入。",
            "Checksum 可偵測 bytes 變更，但不是數位簽章或獨立真偽證明。",
            "符合 RO-Crate 規格不代表獲得 RO-Crate 社群背書或認證。",
        ),
        "sources": "標準與來源",
        "sources_text": (
            "Metadata 遵循 RO-Crate 1.3.0 Recommendation，官方 context 固定至"
            "不可變的公開 source commit。資料保留來源脈絡與 CC BY 4.0 attribution。"
        ),
        "app_title": "選用學習夥伴",
        "app_text": (
            "研究物件不需 App 即可完整重用；Lumi 注音星球只是選用的裝置端練習層。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": "開放研究物件 · 不需帳號 · 不需 API key · 不宣稱已典藏",
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bytes_if_changed(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def _types(entity: dict) -> set[str]:
    value = entity.get("@type", [])
    return {value} if isinstance(value, str) else set(value)


def _load_context() -> dict:
    data = CONTEXT_PATH.read_bytes()
    if _sha256(data) != CONTEXT_SHA256:
        raise ValueError("Pinned RO-Crate 1.3 context SHA-256 mismatch")
    document = json.loads(data)
    if document.get("@id") != CONTEXT or document.get("version") != "1.3.0":
        raise ValueError("Pinned RO-Crate context identity or version mismatch")
    if not isinstance(document.get("@context"), dict):
        raise ValueError("Pinned RO-Crate context map is missing")
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    if (
        sources["specification"]["commit"] != SPEC_COMMIT
        or sources["specification"]["profile"] != PROFILE
        or sources["context"]["id"] != CONTEXT
        or sources["context"]["sha256"] != CONTEXT_SHA256
    ):
        raise ValueError("RO-Crate source provenance is inconsistent")
    return document


def _source_entries(pages: Path) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    for spec in PAYLOAD_SPECS:
        source = pages / spec.source_path
        if not source.is_file():
            raise FileNotFoundError(
                f"Generate the Bopomofo data resources before RO-Crate: {source}"
            )
        entries[spec.crate_path] = source.read_bytes()
    entries[README_FILENAME] = README_TEXT.encode("utf-8")
    entries[LICENSE_FILENAME] = LICENSE_TEXT.encode("utf-8")
    return entries


def _file_entity(spec: PayloadSpec, data: bytes) -> dict:
    entity = {
        "@id": spec.crate_path,
        "@type": "File",
        "name": spec.name,
        "description": spec.description,
        "encodingFormat": spec.encoding_format,
        "contentSize": str(len(data)),
        "sha256": _sha256(data),
        "license": {"@id": LICENSE},
    }
    if spec.conforms_to:
        entity["conformsTo"] = {"@id": spec.conforms_to}
    return entity


def _support_entity(path: str, name: str, description: str, media_type: str, data: bytes) -> dict:
    return {
        "@id": path,
        "@type": "File",
        "name": name,
        "description": description,
        "encodingFormat": media_type,
        "contentSize": str(len(data)),
        "sha256": _sha256(data),
        "license": {"@id": LICENSE},
    }


def crate_metadata(entries: dict[str, bytes], modified: str) -> dict:
    file_entities = [
        _file_entity(spec, entries[spec.crate_path]) for spec in PAYLOAD_SPECS
    ]
    file_entities.extend(
        (
            _support_entity(
                README_FILENAME,
                "Bilingual RO-Crate reuse guide",
                "Plain-text English and Traditional Chinese validation and reuse guide.",
                "text/plain",
                entries[README_FILENAME],
            ),
            _support_entity(
                LICENSE_FILENAME,
                "CC BY 4.0 attribution notice",
                "License URL and requested attribution for the packaged open data.",
                "text/plain",
                entries[LICENSE_FILENAME],
            ),
        )
    )
    part_refs = [{"@id": entity["@id"]} for entity in file_entities]
    return {
        "@context": CONTEXT,
        "@graph": [
            {
                "@id": METADATA_FILENAME,
                "@type": "CreativeWork",
                "about": {"@id": ROOT_ID},
                "conformsTo": {"@id": PROFILE},
            },
            {
                "@id": ROOT_ID,
                "@type": ["Dataset", "LearningResource"],
                "name": "Bopomofo 37-Symbol Open Reference RO-Crate",
                "alternateName": "完整 37 注音符號開放參考資料 RO-Crate",
                "description": (
                    "An attached RO-Crate 1.3 research object containing the complete "
                    "37-symbol Bopomofo table plus JSON Lines, Croissant 1.1, W3C CSVW "
                    "and SKOS JSON-LD metadata."
                ),
                "url": ROOT_ID,
                "identifier": {"@id": IDENTIFIER_ID},
                "cite-as": ROOT_ID,
                "version": VERSION,
                "datePublished": INITIAL_DATE,
                "dateModified": modified,
                "inLanguage": ["en", "zh-Hant"],
                "keywords": [
                    "Bopomofo",
                    "Zhuyin",
                    "Mandarin phonetics",
                    "RO-Crate",
                    "open data",
                    "research object",
                ],
                "isAccessibleForFree": True,
                "license": {"@id": LICENSE},
                "creator": {"@id": PUBLISHER_ID},
                "publisher": {"@id": PUBLISHER_ID},
                "hasPart": part_refs,
                "citation": [
                    {"@id": SPEC_URL},
                    {"@id": MOE_REFERENCE_ID},
                ],
                "creditText": (
                    "Bopomofo 37-Symbol Open Reference Data, iOS App Guide Open "
                    f"Resources, {ROOT_ID}"
                ),
            },
            {
                "@id": IDENTIFIER_ID,
                "@type": "PropertyValue",
                "name": "Canonical web identifier",
                "propertyID": "URL",
                "value": ROOT_ID,
                "url": ROOT_ID,
            },
            {
                "@id": PUBLISHER_ID,
                "@type": "Organization",
                "name": "iOS App Guide Open Resources",
                "url": SITE,
            },
            {
                "@id": LICENSE,
                "@type": "CreativeWork",
                "name": "Creative Commons Attribution 4.0 International",
                "description": (
                    "Permits sharing and adaptation for any purpose with attribution."
                ),
            },
            {
                "@id": PROFILE,
                "@type": "CreativeWork",
                "name": "RO-Crate Metadata Specification 1.3.0",
                "url": SPEC_URL,
            },
            {
                "@id": CONTEXT,
                "@type": "CreativeWork",
                "name": "RO-Crate 1.3 JSON-LD Context",
                "encodingFormat": "application/ld+json",
                "version": "1.3.0",
                "license": {
                    "@id": "https://creativecommons.org/publicdomain/zero/1.0/"
                },
            },
            {
                "@id": SPEC_URL,
                "@type": "CreativeWork",
                "name": "RO-Crate Metadata Specification 1.3.0",
                "isBasedOn": {"@id": f"{SPEC_REPOSITORY}/commit/{SPEC_COMMIT}"},
            },
            {
                "@id": MOE_REFERENCE_ID,
                "@type": "CreativeWork",
                "name": "Taiwan Ministry of Education Bopomofo reference",
                "publisher": {"@id": MOE_PUBLISHER_ID},
            },
            {
                "@id": MOE_PUBLISHER_ID,
                "@type": "Organization",
                "name": "Ministry of Education, Taiwan",
            },
            {
                "@id": PREVIEW_FILENAME,
                "@type": "CreativeWork",
                "about": {"@id": ROOT_ID},
                "name": "Static RO-Crate preview",
                "encodingFormat": "text/html",
            },
            *file_entities,
        ],
    }


def _metadata_bytes(metadata: dict) -> bytes:
    return (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def render_preview(metadata: dict) -> bytes:
    entities = {entity["@id"]: entity for entity in metadata["@graph"]}
    root = entities[ROOT_ID]
    rows = []
    for ref in root["hasPart"]:
        entity = entities[ref["@id"]]
        rows.append(
            "<tr>"
            f'<td><a href="{html.escape(entity["@id"], quote=True)}">'
            f'{html.escape(entity["@id"])}</a></td>'
            f'<td>{html.escape(entity["encodingFormat"])}</td>'
            f'<td>{html.escape(entity["contentSize"])}</td>'
            f'<td><code>{html.escape(entity["sha256"])}</code></td>'
            "</tr>"
        )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bopomofo 37-Symbol RO-Crate 1.3 Preview</title>
<style>
body{{font:16px/1.6 system-ui,sans-serif;margin:0;color:#172033;background:#f7f8fc}}
main{{width:min(1080px,calc(100% - 32px));margin:auto;padding:40px 0}}
h1{{line-height:1.1}}section{{background:#fff;border:1px solid #dfe3ee;border-radius:18px;padding:22px;margin:18px 0}}
table{{width:100%;border-collapse:collapse;display:block;overflow:auto}}th,td{{padding:10px;border-bottom:1px solid #e8eaf1;text-align:left;white-space:nowrap}}
code{{font-size:.78rem}}a{{color:#3046c7}}.tag{{display:inline-block;padding:5px 10px;border-radius:999px;background:#edf0ff;margin:3px;white-space:nowrap}}
</style>
</head>
<body>
<main>
<p><span class="tag">RO-Crate 1.3</span><span class="tag">CC BY 4.0</span><span class="tag">37 symbols</span></p>
<h1>{html.escape(root["name"])}</h1>
<p>{html.escape(root["description"])}</p>
<p lang="zh-Hant">本研究物件封裝完整 37 個注音符號資料與可重現的標準 metadata。</p>
<section>
<h2>Root Dataset</h2>
<p><strong>Identifier:</strong> <a href="{html.escape(ROOT_ID, quote=True)}">{html.escape(ROOT_ID)}</a></p>
<p><strong>Version:</strong> {html.escape(root["version"])} · <strong>Modified:</strong> {html.escape(root["dateModified"])}</p>
<p><strong>License:</strong> <a href="{html.escape(LICENSE, quote=True)}">CC BY 4.0</a></p>
</section>
<section>
<h2>Data entities</h2>
<table><thead><tr><th>Path</th><th>Format</th><th>Bytes</th><th>SHA-256</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</section>
<section>
<h2>Validation and limits</h2>
<p>Verify <a href="{CHECKSUM_FILENAME}">{CHECKSUM_FILENAME}</a>, parse
<a href="{METADATA_FILENAME}">{METADATA_FILENAME}</a> with the pinned official
1.3 context, and confirm every local hasPart path before reuse.</p>
<p>This crate has no DOI and makes no claim of repository registration, external
ingest, endorsement or certification. Checksums are fixity values, not signatures.</p>
<p lang="zh-Hant">本 crate 沒有 DOI，也不宣稱已登錄典藏庫、已被外部系統匯入、
獲得背書或認證。Checksum 是 fixity value，不是數位簽章。</p>
</section>
<section>
<h2>Sources</h2>
<p><a href="{SPEC_URL}">RO-Crate Metadata Specification 1.3.0</a> ·
<a href="{LICENSE}">CC BY 4.0</a></p>
</section>
</main>
</body>
</html>
"""
    return page.encode("utf-8")


def _checksum_bytes(entries: dict[str, bytes]) -> bytes:
    lines = [f"{_sha256(entries[path])}  {path}" for path in sorted(entries)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in entries:
            info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entries[path])
    return stream.getvalue()


def make_artifacts(pages: Path, modified: str) -> dict[str, bytes]:
    _load_context()
    source_entries = _source_entries(pages)
    metadata = crate_metadata(source_entries, modified)
    metadata_bytes = _metadata_bytes(metadata)
    preview_bytes = render_preview(metadata)
    ordered: dict[str, bytes] = {
        METADATA_FILENAME: metadata_bytes,
        PREVIEW_FILENAME: preview_bytes,
        README_FILENAME: source_entries[README_FILENAME],
        LICENSE_FILENAME: source_entries[LICENSE_FILENAME],
    }
    for spec in PAYLOAD_SPECS:
        ordered[spec.crate_path] = source_entries[spec.crate_path]
    checksum_bytes = _checksum_bytes(ordered)
    zip_entries = {**ordered, CHECKSUM_FILENAME: checksum_bytes}
    artifacts = {
        **zip_entries,
        BUNDLE_FILENAME: _zip_bytes(zip_entries),
    }
    validate_artifacts(artifacts, modified)
    return artifacts


def validate_artifacts(artifacts: dict[str, bytes], modified: str) -> None:
    context_document = _load_context()
    expected_members = [
        METADATA_FILENAME,
        PREVIEW_FILENAME,
        README_FILENAME,
        LICENSE_FILENAME,
        *(spec.crate_path for spec in PAYLOAD_SPECS),
        CHECKSUM_FILENAME,
    ]
    if list(artifacts) != [*expected_members, BUNDLE_FILENAME]:
        raise ValueError("RO-Crate artifact ordering or member set is invalid")
    metadata = json.loads(artifacts[METADATA_FILENAME])
    if metadata.get("@context") != CONTEXT:
        raise ValueError("RO-Crate must reference the official 1.3 context")
    graph = metadata.get("@graph")
    if not isinstance(graph, list):
        raise ValueError("RO-Crate @graph must be an array")
    entities = {entity.get("@id"): entity for entity in graph}
    if None in entities or len(entities) != len(graph):
        raise ValueError("Every RO-Crate entity must have a unique @id")
    descriptor = entities.get(METADATA_FILENAME)
    if descriptor != {
        "@id": METADATA_FILENAME,
        "@type": "CreativeWork",
        "about": {"@id": ROOT_ID},
        "conformsTo": {"@id": PROFILE},
    }:
        raise ValueError("RO-Crate metadata descriptor is not 1.3 conformant")
    root = entities.get(ROOT_ID)
    if not root or "Dataset" not in _types(root):
        raise ValueError("RO-Crate root data entity must be a Dataset")
    for field in (
        "name",
        "description",
        "datePublished",
        "license",
        "creator",
        "publisher",
        "hasPart",
    ):
        if not root.get(field):
            raise ValueError(f"RO-Crate root Dataset is missing {field}")
    if root.get("dateModified") != modified:
        raise ValueError("RO-Crate dateModified mismatch")
    reference = entities.get(MOE_REFERENCE_ID)
    if (
        not reference
        or reference.get("publisher") != {"@id": MOE_PUBLISHER_ID}
        or _types(entities.get(MOE_PUBLISHER_ID, {})) != {"Organization"}
    ):
        raise ValueError("RO-Crate source publisher must be an Organization entity")
    today = dt.datetime.now(dt.timezone.utc).date()
    for field in ("datePublished", "dateModified"):
        value = dt.date.fromisoformat(root[field])
        if value > today:
            raise ValueError(f"RO-Crate {field} must not be in the future")
    expected_parts = {
        README_FILENAME,
        LICENSE_FILENAME,
        *(spec.crate_path for spec in PAYLOAD_SPECS),
    }
    part_ids = {part.get("@id") for part in root["hasPart"]}
    if part_ids != expected_parts:
        raise ValueError("RO-Crate root hasPart set is incomplete")
    for path in expected_parts:
        entity = entities.get(path)
        if not entity or "File" not in _types(entity):
            raise ValueError(f"RO-Crate File entity missing: {path}")
        data = artifacts[path]
        if entity.get("contentSize") != str(len(data)):
            raise ValueError(f"RO-Crate contentSize mismatch: {path}")
        if entity.get("sha256") != _sha256(data):
            raise ValueError(f"RO-Crate SHA-256 mismatch: {path}")
        if not entity.get("name") or not entity.get("description"):
            raise ValueError(f"RO-Crate File description missing: {path}")
    csv_rows = list(
        csv.DictReader(
            io.StringIO(
                artifacts["data/zhuyin-bopomofo-ml-dataset.csv"].decode("utf-8")
            )
        )
    )
    if len(csv_rows) != 37:
        raise ValueError("RO-Crate CSV must contain exactly 37 data rows")
    jsonl_rows = [
        json.loads(line)
        for line in artifacts["data/zhuyin-bopomofo-ml-dataset.jsonl"]
        .decode("utf-8")
        .splitlines()
        if line
    ]
    if len(jsonl_rows) != 37:
        raise ValueError("RO-Crate JSON Lines must contain exactly 37 records")
    local_metadata = json.loads(artifacts[METADATA_FILENAME])
    local_metadata["@context"] = context_document["@context"]
    rdf = Graph()
    rdf.parse(
        data=json.dumps(local_metadata, ensure_ascii=False),
        format="json-ld",
        publicID=ROOT_ID,
    )
    if len(rdf) < 80:
        raise ValueError("RO-Crate JSON-LD graph is unexpectedly small")
    expected_checksums = _checksum_bytes(
        {path: artifacts[path] for path in expected_members if path != CHECKSUM_FILENAME}
    )
    if artifacts[CHECKSUM_FILENAME] != expected_checksums:
        raise ValueError("RO-Crate checksum list mismatch")
    with zipfile.ZipFile(io.BytesIO(artifacts[BUNDLE_FILENAME])) as archive:
        if archive.namelist() != expected_members:
            raise ValueError("RO-Crate ZIP member order or set mismatch")
        for info in archive.infolist():
            if info.date_time != ZIP_TIMESTAMP:
                raise ValueError(f"RO-Crate ZIP timestamp mismatch: {info.filename}")
            if (info.external_attr >> 16) != 0o100644:
                raise ValueError(f"RO-Crate ZIP mode mismatch: {info.filename}")
            if archive.read(info.filename) != artifacts[info.filename]:
                raise ValueError(f"RO-Crate ZIP byte mismatch: {info.filename}")
    preview = artifacts[PREVIEW_FILENAME].decode("utf-8")
    if "<script" in preview.lower():
        raise ValueError("RO-Crate preview must remain static and script-free")
    for path in (METADATA_FILENAME, CHECKSUM_FILENAME, *expected_parts):
        if path not in preview and path not in (README_FILENAME, LICENSE_FILENAME):
            raise ValueError(f"RO-Crate preview omits a required link: {path}")
    for path in expected_members:
        text = artifacts[path].decode("utf-8")
        for forbidden in FORBIDDEN:
            if forbidden.lower() in text.lower():
                raise ValueError(
                    f"RO-Crate machine artifact contains forbidden text: {forbidden}"
                )


def _prior_modified(metadata_path: Path) -> str:
    if not metadata_path.exists():
        return INITIAL_DATE
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        root = next(
            entity for entity in metadata["@graph"] if entity["@id"] == ROOT_ID
        )
        value = root["dateModified"]
        dt.date.fromisoformat(value)
    except (json.JSONDecodeError, KeyError, StopIteration, TypeError, ValueError) as error:
        raise ValueError(f"Existing RO-Crate metadata is invalid: {metadata_path}") from error
    return value


def _artifacts_changed(package_dir: Path, artifacts: dict[str, bytes]) -> bool:
    for path, data in artifacts.items():
        target = package_dir / path
        if not target.is_file() or target.read_bytes() != data:
            return True
    return False


def _is_app_public(pages: Path) -> bool:
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _artifact_rows(artifacts: dict[str, bytes], copy: dict) -> str:
    metadata = json.loads(artifacts[METADATA_FILENAME])
    entities = {entity["@id"]: entity for entity in metadata["@graph"]}
    root = entities[ROOT_ID]
    return "".join(
        "<tr>"
        f'<td><a href="{html.escape(PACKAGE_URL + ref["@id"], quote=True)}">'
        f'{html.escape(ref["@id"])}</a></td>'
        f'<td>{html.escape(entities[ref["@id"]]["encodingFormat"])}</td>'
        f'<td>{html.escape(entities[ref["@id"]]["contentSize"])}</td>'
        f'<td><code>{html.escape(entities[ref["@id"]]["sha256"][:16])}…</code></td>'
        "</tr>"
        for ref in root["hasPart"]
    )


def render_page(
    locale: str,
    artifacts: dict[str, bytes],
    modified: str,
    app_public: bool,
) -> str:
    copy = COPY[locale]
    canonical = PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL
    alternate = ZH_PACKAGE_URL if locale == "en" else PACKAGE_URL
    dataset_schema = {
        "@type": "Dataset",
        "name": copy["title"],
        "description": copy["description"],
        "url": canonical,
        "identifier": ROOT_ID,
        "version": VERSION,
        "dateModified": modified,
        "inLanguage": ["en", "zh-Hant"],
        "license": LICENSE,
        "isAccessibleForFree": True,
        "distribution": [
            {
                "@type": "DataDownload",
                "name": copy["bundle"],
                "contentUrl": BUNDLE_URL,
                "encodingFormat": "application/zip",
                "contentSize": len(artifacts[BUNDLE_FILENAME]),
                "sha256": _sha256(artifacts[BUNDLE_FILENAME]),
            },
            {
                "@type": "DataDownload",
                "name": copy["metadata"],
                "contentUrl": METADATA_URL,
                "encodingFormat": "application/json",
                "contentSize": len(artifacts[METADATA_FILENAME]),
                "sha256": _sha256(artifacts[METADATA_FILENAME]),
            },
        ],
    }
    schema_graph = [dataset_schema]
    if app_public:
        schema_graph.append(
            {
                "@type": "SoftwareApplication",
                "applicationCategory": "EducationApplication",
                "name": APP_NAME,
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_rocrate_{locale.lower()}"),
            }
        )
    schema = {"@context": "https://schema.org", "@graph": schema_graph}
    downloads = (
        f'<a class="download primary" href="{BUNDLE_URL}"><strong>{html.escape(copy["bundle"])}</strong>'
        f"<span>{len(artifacts[BUNDLE_FILENAME]):,} bytes · {_sha256(artifacts[BUNDLE_FILENAME])[:16]}…</span></a>"
        f'<a class="download" href="{METADATA_URL}"><strong>{html.escape(copy["metadata"])}</strong>'
        f"<span>{len(artifacts[METADATA_FILENAME]):,} bytes · JSON-LD</span></a>"
        f'<a class="download" href="{PREVIEW_URL}"><strong>{html.escape(copy["preview"])}</strong>'
        f"<span>{len(artifacts[PREVIEW_FILENAME]):,} bytes · static HTML</span></a>"
        f'<a class="download" href="{CHECKSUM_URL}"><strong>{html.escape(copy["checksums"])}</strong>'
        f"<span>{len(artifacts[CHECKSUM_FILENAME]):,} bytes · SHA-256</span></a>"
    )
    scope = "".join(f"<li>{html.escape(item)}</li>" for item in copy["scope_items"])
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel optional"><h2>'
            f'{html.escape(copy["app_title"])}</h2><p>{html.escape(copy["app_text"])}</p>'
            f'<a class="button" href="{appstore_url(APP_KEY, "iag_rocrate")}">'
            f'{html.escape(copy["app_cta"])}</a></section>'
        )
    return f"""<!doctype html>
<html lang="{copy['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{modified}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{PACKAGE_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_PACKAGE_URL}">
<link rel="alternate" hreflang="x-default" href="{PACKAGE_URL}">
<link rel="describedby" type="application/json" href="{METADATA_URL}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>
:root{{--ink:#172033;--muted:#5c6578;--line:#dfe3ee;--panel:#fff;--accent:#4659d9;--soft:#eef1ff}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.65 system-ui,sans-serif;color:var(--ink);background:linear-gradient(180deg,#f8f9ff,#fff)}}
a{{color:#3046c7}}.wrap{{width:min(1100px,calc(100% - 32px));margin:auto}}header{{padding:18px 0}}nav{{display:flex;justify-content:space-between;gap:12px}}nav a,.button{{white-space:nowrap}}
.hero{{padding:48px 0 22px}}.eyebrow{{font-weight:800;color:var(--accent);letter-spacing:.06em;text-transform:uppercase}}h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.04;margin:.18em 0}}.lead{{font-size:1.15rem;color:var(--muted);max-width:780px}}
.badges{{display:flex;gap:8px;flex-wrap:wrap}}.badge{{padding:6px 11px;border-radius:999px;background:var(--soft);font-weight:750;white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.panel{{background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 10px 36px rgba(29,42,92,.07);margin:18px 0}}
.download{{display:flex;justify-content:space-between;gap:14px;align-items:center;padding:14px 16px;border:1px solid var(--line);border-radius:14px;text-decoration:none;margin:10px 0}}.download span{{color:var(--muted);font-size:.88rem;white-space:nowrap}}.download.primary{{background:var(--accent);color:#fff;border-color:var(--accent)}}.download.primary span{{color:#eef1ff}}
table{{width:100%;border-collapse:collapse;display:block;overflow:auto}}th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}code{{font-size:.78rem}}.button{{display:inline-block;background:var(--accent);color:#fff;padding:11px 17px;border-radius:999px;text-decoration:none;font-weight:800}}
.optional{{border-style:dashed}}footer{{padding:32px 0;color:var(--muted)}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.download{{align-items:flex-start;flex-direction:column}}}}
</style>
</head>
<body>
<header class="wrap"><nav><a href="{SITE}/data/">{html.escape(copy['back'])}</a><a href="{alternate}">{html.escape(copy['language'])}</a></nav></header>
<main>
<section class="hero wrap"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges"><span class="badge">RO-Crate 1.3</span><span class="badge">CC BY 4.0</span><span class="badge">SHA-256</span><span class="badge">37 symbols</span></div></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p>{downloads}</article><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><a href="{SPEC_URL}">RO-Crate 1.3.0 Recommendation</a><br><a href="{SPEC_REPOSITORY}/commit/{SPEC_COMMIT}">Pinned source commit</a></article></section>
<section class="wrap panel"><h2>{html.escape(copy['payload'])}</h2><table><thead><tr><th>{html.escape(copy['path'])}</th><th>{html.escape(copy['format'])}</th><th>{html.escape(copy['bytes'])}</th><th>{html.escape(copy['sha'])}</th></tr></thead><tbody>{_artifact_rows(artifacts, copy)}</tbody></table></section>
<section class="wrap grid"><article class="panel"><h2>{html.escape(copy['scope'])}</h2><ul>{scope}</ul></article><article class="panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['sources_text'])}</p><a href="{SPEC_URL}">RO-Crate 1.3</a><br><a href="{LICENSE}">CC BY 4.0</a></article></section>
<div class="wrap">{app_section}</div>
</main>
<footer class="wrap">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def render_sitemap(modified: str) -> str:
    urls = (
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        METADATA_URL,
        PREVIEW_URL,
        f"{PACKAGE_URL}{README_FILENAME}",
        f"{PACKAGE_URL}{LICENSE_FILENAME}",
        *(f"{PACKAGE_URL}{spec.crate_path}" for spec in PAYLOAD_SPECS),
        CHECKSUM_URL,
        BUNDLE_URL,
    )
    rows = "\n".join(
        f"  <url><loc>{html.escape(url)}</loc><lastmod>{modified}</lastmod></url>"
        for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def validate_page(page: str, locale: str, app_public: bool) -> None:
    canonical = PACKAGE_URL if locale == "en" else ZH_PACKAGE_URL
    for required in (
        f'<html lang="{COPY[locale]["lang"]}">',
        f'<link rel="canonical" href="{canonical}">',
        f'href="{BUNDLE_URL}"',
        f'href="{METADATA_URL}"',
        f'href="{PREVIEW_URL}"',
        f'href="{CHECKSUM_URL}"',
        f'href="{SPEC_URL}"',
        *(
            f'href="{PACKAGE_URL}{path}"'
            for path in (
                README_FILENAME,
                LICENSE_FILENAME,
                *(spec.crate_path for spec in PAYLOAD_SPECS),
            )
        ),
    ):
        if required not in page:
            raise ValueError(f"RO-Crate landing is missing {required}")
    has_app = "apps.apple.com" in page
    if has_app != app_public:
        raise ValueError("RO-Crate optional app CTA does not match public availability")


def update_data_index(pages: Path, artifacts: dict[str, bytes]) -> bool:
    index = pages / "data" / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"Data index must exist before RO-Crate: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'{CARD_START}<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo RO-Crate 1.3 research object</h2>"
        "<p>Attached 37-symbol research object with CSV, JSON Lines, Croissant, "
        "CSVW, SKOS and deterministic SHA-256-verified ZIP.</p>"
        '<span class="tag">RO-Crate 1.3 · 37 symbols · EN + zh-Hant</span></a>'
        f"{CARD_END}"
    )
    updated = re.sub(
        re.escape(CARD_START) + r".*?" + re.escape(CARD_END),
        "",
        text,
        flags=re.DOTALL,
    )
    anchor_urls = (
        f"{SITE}/data/zhuyin-bopomofo-iiif-presentation-3.html",
        f"{SITE}/data/packages/zhuyin-bopomofo-ocfl/",
        f"{SITE}/data/zhuyin-bopomofo-ml-croissant.html",
    )
    anchor = None
    for anchor_url in anchor_urls:
        anchor = re.search(
            r'<a class="item" href="' + re.escape(anchor_url) + r'">.*?</a>',
            updated,
            re.DOTALL,
        )
        if anchor:
            break
    if anchor:
        updated = updated[: anchor.end()] + card + updated[anchor.end() :]
    else:
        footer = updated.find('<p class="foot">')
        if footer < 0:
            raise RuntimeError("data/index.html has no insertion anchor for RO-Crate")
        updated = updated[:footer] + card + updated[footer:]

    schema_pattern = re.compile(
        r'(<script type="application/ld\+json">)(.*?)(</script>)',
        re.DOTALL,
    )
    schema_match = schema_pattern.search(updated)
    if not schema_match:
        raise RuntimeError("data/index.html is missing DataCatalog JSON-LD")
    catalog = json.loads(schema_match.group(2))
    datasets = [
        item for item in catalog.get("dataset", []) if item.get("url") != PACKAGE_URL
    ]
    entry = {
        "@type": "Dataset",
        "name": COPY["en"]["title"],
        "description": COPY["en"]["description"],
        "url": PACKAGE_URL,
        "license": LICENSE,
        "conformsTo": PROFILE,
        "distribution": [
            {
                "@type": "DataDownload",
                "name": name,
                "contentUrl": url,
                "encodingFormat": media_type,
                "contentSize": len(artifacts[filename]),
                "sha256": _sha256(artifacts[filename]),
            }
            for name, filename, url, media_type in (
                (
                    "Complete RO-Crate ZIP",
                    BUNDLE_FILENAME,
                    BUNDLE_URL,
                    "application/zip",
                ),
                (
                    "RO-Crate metadata",
                    METADATA_FILENAME,
                    METADATA_URL,
                    "application/ld+json",
                ),
                (
                    "Static RO-Crate preview",
                    PREVIEW_FILENAME,
                    PREVIEW_URL,
                    "text/html",
                ),
                (
                    "SHA-256 checksums",
                    CHECKSUM_FILENAME,
                    CHECKSUM_URL,
                    "text/plain",
                ),
            )
        ],
    }
    anchor_dataset_urls = anchor_urls
    position = len(datasets)
    for offset, dataset in enumerate(datasets):
        if dataset.get("url") in anchor_dataset_urls:
            position = offset + 1
            break
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


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    package_dir = pages / PACKAGE_PATH
    package_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = package_dir / METADATA_FILENAME
    prior_modified = _prior_modified(metadata_path)
    artifacts = make_artifacts(pages, prior_modified)
    modified = prior_modified
    if _artifacts_changed(package_dir, artifacts):
        modified = TODAY
        artifacts = make_artifacts(pages, modified)
    for relative_path, data in artifacts.items():
        _write_bytes_if_changed(package_dir / relative_path, data)
    public = _is_app_public(pages) if app_public is None else app_public
    for locale, path in (
        ("en", package_dir / "index.html"),
        ("zh-Hant", pages / "zh-Hant" / PACKAGE_PATH / "index.html"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page = render_page(locale, artifacts, modified, public)
        validate_page(page, locale, public)
        write_text_if_changed(path, page)
    update_data_index(pages, artifacts)
    write_text_if_changed(pages / SITEMAP_PATH, render_sitemap(modified))
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        *[
            f"{PACKAGE_URL}{path}"
            for path in artifacts
            if path != BUNDLE_FILENAME
        ],
        BUNDLE_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Bopomofo RO-Crate -> {output}")


if __name__ == "__main__":
    main()
