#!/usr/bin/env python3
"""Publish an RFC 8493 BagIt 1.0 preservation package for Bopomofo data."""

from __future__ import annotations

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
    LICENSE,
    SITE,
    records,
    render_csv,
    validate_records,
)


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
VERSION = "1.0.0"

PACKAGE_SLUG = "zhuyin-bopomofo-bagit"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
BAG_ROOT = "bopomofo-37-symbols-bagit"
BUNDLE_FILENAME = "bopomofo-37-symbols-bagit-rfc8493.zip"
CHECKSUM_FILENAME = "checksums-sha256.txt"
METADATA_FILENAME = "metadata.jsonld"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_bagit.xml"
DATA_CATALOG = f"{SITE}/data/"

RFC_URL = "https://www.rfc-editor.org/rfc/rfc8493"
RFC_TEXT_URL = "https://www.rfc-editor.org/rfc/rfc8493.txt"
RFC_TEXT_SHA256 = (
    "4964147d2e6e16442d4a6dbfbe68178a8f33c3e791c06d68a8b33f51ad821537"
)
BAGIT_PYTHON_URL = "https://github.com/LibraryOfCongress/bagit-python"
REFERENCE_SOURCES = HERE / "reference_datasets" / "bagit" / "sources.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

SOURCE_PAYLOADS = (
    (
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "data/zhuyin-bopomofo-ml-dataset.csv",
        "text/csv",
        "Canonical 37-row UTF-8 table",
    ),
    (
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "data/zhuyin-bopomofo-ml-dataset.jsonl",
        "application/x-ndjson",
        "Equivalent JSON Lines records",
    ),
    (
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld",
        'application/ld+json; profile="http://mlcommons.org/croissant/1.1"',
        "MLCommons Croissant 1.1 metadata",
    ),
    (
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
        "application/csvm+json",
        "W3C CSVW metadata",
    ),
    (
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "data/zhuyin-bopomofo-vocabulary.jsonld",
        "application/ld+json",
        "SKOS vocabulary in JSON-LD",
    ),
    (
        "data/zhuyin-bopomofo-vocabulary.ttl",
        "data/zhuyin-bopomofo-vocabulary.ttl",
        "text/turtle",
        "SKOS vocabulary in Turtle",
    ),
    (
        "data/zhuyin-bopomofo-vocabulary.nt",
        "data/zhuyin-bopomofo-vocabulary.nt",
        "application/n-triples",
        "SKOS vocabulary in N-Triples",
    ),
    (
        "data/zhuyin-bopomofo-vocabulary.shacl.ttl",
        "data/zhuyin-bopomofo-vocabulary.shacl.ttl",
        "text/turtle",
        "SHACL validation shapes",
    ),
)

COPY = {
    "en": {
        "lang": "en",
        "title": "RFC 8493 BagIt Preservation Package for Bopomofo",
        "description": (
            "Download a deterministic BagIt 1.0 preservation package for the "
            "complete 37-symbol Bopomofo dataset, with SHA-256 and SHA-512 "
            "payload and tag manifests."
        ),
        "eyebrow": "RFC 8493 BagIt 1.0 · 10 payload files · dual fixity",
        "lead": (
            "A self-checking deposit package for digital repositories, library "
            "preservation workflows and durable transfer of the open Bopomofo data."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "badges": (
            "Exact Payload-Oxum",
            "SHA-256 + SHA-512",
            "Deterministic ZIP",
            "CC BY 4.0 payload",
        ),
        "downloads": "Preservation package",
        "download_text": (
            "Download the ZIP, verify its outer SHA-256, then extract the single "
            "BagIt base directory. The JSON-LD manifest lists exact bytes and "
            "checksums for every preserved payload file."
        ),
        "bundle": "Complete BagIt ZIP",
        "checksum": "Outer SHA-256",
        "metadata": "Package metadata",
        "validate": "Validate independently",
        "validate_text": (
            "The pinned Library of Congress validator checks completeness, "
            "Payload-Oxum and every payload and tag checksum."
        ),
        "contents": "Preserved payload",
        "path": "Bag path",
        "format": "Format",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "integrity": "Integrity design",
        "integrity_items": (
            "Every payload file appears exactly once in both payload manifests.",
            "Both tag manifests cover bagit.txt, bag-info.txt and both payload manifests.",
            "Payload-Oxum records the exact octet total and payload stream count.",
            "The ZIP uses fixed timestamps, stable ordering and stored bytes.",
        ),
        "scope": "Scope and limits",
        "scope_items": (
            "The package contains reference data and standards metadata, not audio or learner records.",
            "RFC 8493 defines the BagIt directory layout; it does not define or register a ZIP serialization.",
            "Checksums detect corruption but are not a digital signature or proof against an active attacker.",
            "Conformance does not imply RFC Editor, IETF or Library of Congress endorsement or repository ingest.",
        ),
        "standards": "Sources and interoperability",
        "standards_text": (
            "The layout follows RFC 8493 BagIt 1.0. The official RFC text is "
            "hash-pinned in the generator, and validation is tested with "
            "LibraryOfCongress bagit-python 1.9.0."
        ),
        "rfc": "RFC 8493",
        "validator": "Library of Congress validator",
        "license": "CC BY 4.0",
        "app_title": "Optional learning companion",
        "app_text": (
            "The preservation package is complete and reusable without an app. "
            "Lumi Bopomofo is an optional on-device practice layer."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Open preservation package · No account · No API key · "
            "No claim of institutional ingest"
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音資料 RFC 8493 BagIt 數位保存套件",
        "description": (
            "下載完整 37 注音符號資料的 deterministic BagIt 1.0 數位保存套件，"
            "包含 SHA-256、SHA-512 payload 與 tag manifests。"
        ),
        "eyebrow": "RFC 8493 BagIt 1.0 · 10 個 payload 檔 · 雙重 fixity",
        "lead": (
            "供數位典藏庫、圖書館保存流程與開放注音資料長期移轉使用的"
            "自我驗證 deposit package。"
        ),
        "back": "開放資料",
        "language": "English",
        "badges": (
            "精確 Payload-Oxum",
            "SHA-256＋SHA-512",
            "Deterministic ZIP",
            "CC BY 4.0 payload",
        ),
        "downloads": "數位保存套件",
        "download_text": (
            "先下載 ZIP 並核對外層 SHA-256，再解壓縮單一 BagIt base directory。"
            "JSON-LD manifest 列出每個保存檔案的精確 bytes 與 checksum。"
        ),
        "bundle": "完整 BagIt ZIP",
        "checksum": "外層 SHA-256",
        "metadata": "套件 metadata",
        "validate": "獨立驗證",
        "validate_text": (
            "固定版本的美國國會圖書館 validator 會檢查完整性、Payload-Oxum，"
            "以及全部 payload 與 tag checksums。"
        ),
        "contents": "保存的 payload",
        "path": "Bag 路徑",
        "format": "格式",
        "bytes": "Bytes",
        "sha": "SHA-256",
        "integrity": "完整性設計",
        "integrity_items": (
            "每個 payload 檔案在兩份 payload manifest 中都恰好出現一次。",
            "兩份 tag manifest 都涵蓋 bagit.txt、bag-info.txt 與兩份 payload manifest。",
            "Payload-Oxum 記錄精確 octet 總數與 payload stream 數量。",
            "ZIP 採固定時間戳、穩定排序與不壓縮 bytes。",
        ),
        "scope": "範圍與限制",
        "scope_items": (
            "套件只含參考資料與標準 metadata，不含音訊或學習者紀錄。",
            "RFC 8493 定義 BagIt 目錄結構，並未定義或登錄 ZIP serialization。",
            "Checksum 可偵測損毀，但不是數位簽章，也無法防止主動攻擊。",
            "符合格式不代表 RFC Editor、IETF、美國國會圖書館背書或典藏庫已收錄。",
        ),
        "standards": "規格來源與互通性",
        "standards_text": (
            "目錄結構依 RFC 8493 BagIt 1.0 建立；generator 固定官方 RFC 文字的 "
            "hash，並使用 LibraryOfCongress bagit-python 1.9.0 驗證。"
        ),
        "rfc": "RFC 8493",
        "validator": "美國國會圖書館 validator",
        "license": "CC BY 4.0",
        "app_title": "選用學習工具",
        "app_text": (
            "數位保存套件不需要 App 即可完整使用；Lumi 注音星球僅是選用的"
            "裝置端練習層。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "開放保存套件 · 免帳號 · 免 API key · 不宣稱機構已收錄",
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha512(content: bytes) -> str:
    return hashlib.sha512(content).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


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


def render_readme() -> bytes:
    return f"""# Complete Bopomofo reference data preservation payload

This BagIt payload preserves the complete 37-symbol Bopomofo (Zhuyin) table,
its CSVW and MLCommons Croissant metadata, and the companion SKOS vocabulary.

The CSV and its `<CSV filename>-metadata.json` document remain adjacent, so
the relative CSVW `url` continues to resolve after extraction.

## Validate the bag

From the directory containing the BagIt base directory:

```sh
python3 -m pip install bagit==1.9.0
python3 -m bagit --validate {BAG_ROOT}
```

BagIt validates transfer integrity, not the semantics of each payload format.
Downstream users should also validate CSVW, Croissant, RDF and SHACL as needed.

Specification: {RFC_URL}
Package guide: {PACKAGE_URL}
""".encode("utf-8")


def render_license() -> bytes:
    return (
        "Complete Bopomofo reference data preservation payload\n"
        "Copyright 2026 Lumi Apps - iOS App Guide\n\n"
        "Licensed under Creative Commons Attribution 4.0 International "
        "(CC BY 4.0):\n"
        f"{LICENSE}\n\n"
        "Suggested attribution: Lumi Apps - iOS App Guide, Complete "
        f"37-symbol Bopomofo reference data, {PACKAGE_URL}\n"
    ).encode("utf-8")


def load_payload(pages: Path) -> tuple[dict[str, bytes], dict[str, dict]]:
    payload = {}
    descriptions = {}
    for source, destination, media_type, label in SOURCE_PAYLOADS:
        path = pages / source
        if not path.exists():
            raise FileNotFoundError(f"Build the BagIt payload source first: {path}")
        content = path.read_bytes()
        if not content:
            raise ValueError(f"BagIt payload source is empty: {path}")
        payload[destination] = content
        descriptions[destination] = {
            "media_type": media_type,
            "label": label,
            "source": f"{SITE}/{source}",
        }
    readme_path = "data/README.md"
    license_path = "data/LICENSE.txt"
    payload[readme_path] = render_readme()
    payload[license_path] = render_license()
    descriptions[readme_path] = {
        "media_type": "text/markdown",
        "label": "Preservation and validation guide",
        "source": PACKAGE_URL,
    }
    descriptions[license_path] = {
        "media_type": "text/plain",
        "label": "CC BY 4.0 license notice",
        "source": LICENSE,
    }

    rows = records()
    validate_records(rows)
    expected_csv = render_csv(rows).encode("utf-8")
    csv_path = "data/zhuyin-bopomofo-ml-dataset.csv"
    if payload[csv_path] != expected_csv:
        raise ValueError("BagIt CSV drifted from the canonical 37-row table")
    return payload, descriptions


def payload_oxum(payload: dict[str, bytes]) -> str:
    return f"{sum(len(content) for content in payload.values())}.{len(payload)}"


def render_manifest(payload: dict[str, bytes], algorithm: str) -> bytes:
    digest = _sha256 if algorithm == "sha256" else _sha512
    return "".join(
        f"{digest(content)}  {path}\n"
        for path, content in sorted(payload.items())
    ).encode("utf-8")


def render_bag_info(payload: dict[str, bytes], modified: str) -> bytes:
    return (
        "Source-Organization: Lumi Apps - iOS App Guide\n"
        "External-Description: Deterministic preservation copy of the complete\n"
        " 37-symbol Bopomofo reference table and standards metadata.\n"
        f"Bagging-Date: {modified}\n"
        f"External-Identifier: {PACKAGE_URL}\n"
        f"Payload-Oxum: {payload_oxum(payload)}\n"
        f"Internal-Sender-Identifier: {PACKAGE_SLUG}-{VERSION}\n"
    ).encode("utf-8")


def render_tag_manifest(tag_files: dict[str, bytes], algorithm: str) -> bytes:
    digest = _sha256 if algorithm == "sha256" else _sha512
    return "".join(
        f"{digest(content)}  {path}\n"
        for path, content in sorted(tag_files.items())
    ).encode("utf-8")


def make_bag_files(payload: dict[str, bytes], modified: str) -> dict[str, bytes]:
    tags = {
        "bagit.txt": (
            b"BagIt-Version: 1.0\n"
            b"Tag-File-Character-Encoding: UTF-8\n"
        ),
        "bag-info.txt": render_bag_info(payload, modified),
        "manifest-sha256.txt": render_manifest(payload, "sha256"),
        "manifest-sha512.txt": render_manifest(payload, "sha512"),
    }
    return {
        **payload,
        **tags,
        "tagmanifest-sha256.txt": render_tag_manifest(tags, "sha256"),
        "tagmanifest-sha512.txt": render_tag_manifest(tags, "sha512"),
    }


def _zip_bytes(bag_files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, content in sorted(bag_files.items()):
            info = zipfile.ZipInfo(f"{BAG_ROOT}/{relative}", ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return buffer.getvalue()


def package_metadata(
    modified: str,
    payload: dict[str, bytes],
    descriptions: dict[str, dict],
    bundle: dict,
    checksums: dict,
) -> bytes:
    document = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": f"{PACKAGE_URL}#dataset",
        "name": "RFC 8493 BagIt package for complete Bopomofo reference data",
        "alternateName": "完整注音參考資料 BagIt 數位保存套件",
        "description": COPY["en"]["description"],
        "url": PACKAGE_URL,
        "identifier": PACKAGE_URL,
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "license": LICENSE,
        "isAccessibleForFree": True,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "conformsTo": RFC_URL,
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps - iOS App Guide",
            "url": SITE,
        },
        "measurementTechnique": (
            "RFC 8493 BagIt 1.0 with SHA-256 and SHA-512 payload and tag manifests"
        ),
        "size": payload_oxum(payload),
        "distribution": [
            {
                "@type": "DataDownload",
                "name": bundle["label"],
                "contentUrl": bundle["url"],
                "encodingFormat": bundle["media_type"],
                "contentSize": f"{len(bundle['bytes'])} B",
                "sha256": bundle["sha256"],
            },
            {
                "@type": "DataDownload",
                "name": checksums["label"],
                "contentUrl": checksums["url"],
                "encodingFormat": checksums["media_type"],
                "contentSize": f"{len(checksums['bytes'])} B",
                "sha256": checksums["sha256"],
            },
        ],
        "hasPart": [
            {
                "@type": "DigitalDocument",
                "name": path,
                "description": descriptions[path]["label"],
                "encodingFormat": descriptions[path]["media_type"],
                "contentSize": f"{len(content)} B",
                "sha256": _sha256(content),
                "isBasedOn": descriptions[path]["source"],
            }
            for path, content in sorted(payload.items())
        ],
    }
    return _json_bytes(document)


def make_artifacts(
    payload: dict[str, bytes],
    descriptions: dict[str, dict],
    modified: str,
) -> dict[str, dict]:
    bag_files = make_bag_files(payload, modified)
    bundle_bytes = _zip_bytes(bag_files)
    bundle = _artifact(
        BUNDLE_FILENAME,
        BUNDLE_URL,
        "application/zip",
        "Deterministic RFC 8493 BagIt ZIP",
        bundle_bytes,
    )
    checksum_bytes = (
        f"{bundle['sha256']}  {BUNDLE_FILENAME}\n"
    ).encode("ascii")
    checksums = _artifact(
        CHECKSUM_FILENAME,
        CHECKSUM_URL,
        "text/plain",
        "Outer SHA-256 checksum",
        checksum_bytes,
    )
    metadata_bytes = package_metadata(
        modified,
        payload,
        descriptions,
        bundle,
        checksums,
    )
    metadata = _artifact(
        METADATA_FILENAME,
        METADATA_URL,
        "application/ld+json",
        "Schema.org preservation package metadata",
        metadata_bytes,
    )
    return {
        "bundle": bundle,
        "checksums": checksums,
        "metadata": metadata,
        "_bag_files": bag_files,
        "_payload": payload,
        "_descriptions": descriptions,
    }


def _manifest_entries(content: bytes) -> dict[str, str]:
    entries = {}
    for line in content.decode("utf-8").splitlines():
        checksum, path = re.split(r"[ \t]+", line, maxsplit=1)
        if path in entries:
            raise ValueError(f"Duplicate BagIt manifest path: {path}")
        entries[path] = checksum
    return entries


def validate_reference_pin() -> None:
    source = json.loads(REFERENCE_SOURCES.read_text(encoding="utf-8"))
    if source.get("version") != "RFC 8493":
        raise ValueError("BagIt source pin must identify RFC 8493")
    pinned = source.get("sources", [])
    if pinned != [{"url": RFC_TEXT_URL, "sha256": RFC_TEXT_SHA256}]:
        raise ValueError("BagIt RFC source URL or SHA-256 pin drifted")


def validate_artifacts(artifacts: dict[str, dict]) -> None:
    validate_reference_pin()
    payload = artifacts["_payload"]
    bag_files = artifacts["_bag_files"]
    if len(payload) != 10:
        raise ValueError(f"BagIt payload must contain 10 files, found {len(payload)}")
    if not all(path.startswith("data/") for path in payload):
        raise ValueError("Every BagIt payload path must be under data/")
    if any(
        path.startswith("/") or ".." in Path(path).parts or "\\" in path
        for path in bag_files
    ):
        raise ValueError("BagIt paths must be safe relative POSIX paths")
    if bag_files["bagit.txt"] != (
        b"BagIt-Version: 1.0\n"
        b"Tag-File-Character-Encoding: UTF-8\n"
    ):
        raise ValueError("bagit.txt must contain the exact RFC 8493 declaration")
    for name, content in bag_files.items():
        if name.endswith(".txt") and (
            content.startswith(b"\xef\xbb\xbf") or not content.endswith(b"\n")
        ):
            raise ValueError(f"BagIt text tag must be UTF-8 without BOM and end LF: {name}")
    expected_oxum = payload_oxum(payload)
    if f"Payload-Oxum: {expected_oxum}\n".encode("ascii") not in bag_files["bag-info.txt"]:
        raise ValueError("BagIt Payload-Oxum does not match payload bytes and streams")

    for algorithm, digest in (("sha256", _sha256), ("sha512", _sha512)):
        manifest = _manifest_entries(bag_files[f"manifest-{algorithm}.txt"])
        if set(manifest) != set(payload):
            raise ValueError(f"BagIt {algorithm} payload manifest is incomplete")
        for path, content in payload.items():
            if manifest[path] != digest(content):
                raise ValueError(f"BagIt {algorithm} payload checksum mismatch: {path}")
        tag_files = {
            name: content
            for name, content in bag_files.items()
            if not name.startswith("data/") and not name.startswith("tagmanifest-")
        }
        tag_manifest = _manifest_entries(
            bag_files[f"tagmanifest-{algorithm}.txt"]
        )
        if set(tag_manifest) != set(tag_files):
            raise ValueError(f"BagIt {algorithm} tag manifest coverage is invalid")
        for path, content in tag_files.items():
            if tag_manifest[path] != digest(content):
                raise ValueError(f"BagIt {algorithm} tag checksum mismatch: {path}")

    expected_names = [f"{BAG_ROOT}/{path}" for path in sorted(bag_files)]
    with zipfile.ZipFile(io.BytesIO(artifacts["bundle"]["bytes"])) as archive:
        if archive.namelist() != expected_names:
            raise ValueError("BagIt ZIP membership or order is not deterministic")
        for path, content in bag_files.items():
            name = f"{BAG_ROOT}/{path}"
            if archive.read(name) != content:
                raise ValueError(f"BagIt ZIP content mismatch: {path}")
            info = archive.getinfo(name)
            if info.date_time != ZIP_TIMESTAMP:
                raise ValueError(f"BagIt ZIP timestamp is not fixed: {path}")
            if info.compress_type != zipfile.ZIP_STORED:
                raise ValueError(f"BagIt ZIP entry must use stored bytes: {path}")
            if (info.external_attr >> 16) & 0o777 != 0o644:
                raise ValueError(f"BagIt ZIP mode must be 0644: {path}")

    expected_outer = (
        f"{_sha256(artifacts['bundle']['bytes'])}  {BUNDLE_FILENAME}\n"
    ).encode("ascii")
    if artifacts["checksums"]["bytes"] != expected_outer:
        raise ValueError("BagIt outer checksum does not match the ZIP")
    metadata = json.loads(artifacts["metadata"]["bytes"])
    if metadata.get("conformsTo") != RFC_URL:
        raise ValueError("BagIt package metadata must identify RFC 8493")
    if metadata.get("size") != expected_oxum:
        raise ValueError("BagIt package metadata Payload-Oxum drifted")
    parts = {item["name"]: item for item in metadata.get("hasPart", [])}
    if set(parts) != set(payload):
        raise ValueError("BagIt package metadata must list every payload file")
    for path, content in payload.items():
        if (
            parts[path]["sha256"] != _sha256(content)
            or parts[path]["contentSize"] != f"{len(content)} B"
        ):
            raise ValueError(f"BagIt package metadata drifted from payload: {path}")

    raw = b"\n".join(
        [
            artifacts["bundle"]["bytes"],
            artifacts["checksums"]["bytes"],
            artifacts["metadata"]["bytes"],
            *bag_files.values(),
        ]
    )
    for forbidden in (
        b"apps.apple.com",
        APP_ID.encode("ascii"),
        APP_NAME.encode("utf-8"),
        b"SoftwareApplication",
    ):
        if forbidden in raw:
            raise ValueError("App promotion leaked into BagIt preservation artifacts")


def _prior_modified(pages: Path) -> str:
    path = pages / PACKAGE_PATH / METADATA_FILENAME
    if not path.exists():
        return INITIAL_DATE
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value["dateModified"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return INITIAL_DATE


def _output_paths(pages: Path) -> dict[str, Path]:
    package = pages / PACKAGE_PATH
    return {
        "bundle": package / BUNDLE_FILENAME,
        "checksums": package / CHECKSUM_FILENAME,
        "metadata": package / METADATA_FILENAME,
    }


def _outputs_match(pages: Path, artifacts: dict[str, dict]) -> bool:
    return all(
        path.exists() and path.read_bytes() == artifacts[key]["bytes"]
        for key, path in _output_paths(pages).items()
    )


def write_artifacts(pages: Path) -> tuple[dict[str, dict], str]:
    payload, descriptions = load_payload(pages)
    prior = _prior_modified(pages)
    artifacts = make_artifacts(payload, descriptions, prior)
    validate_artifacts(artifacts)
    if _outputs_match(pages, artifacts):
        return artifacts, prior
    artifacts = make_artifacts(payload, descriptions, TODAY)
    validate_artifacts(artifacts)
    for key, path in _output_paths(pages).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != artifacts[key]["bytes"]:
            path.write_bytes(artifacts[key]["bytes"])
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
    dataset = {
        "@type": "Dataset",
        "@id": f"{PACKAGE_URL}#dataset",
        "name": COPY[locale]["title"],
        "description": COPY[locale]["description"],
        "url": page_url(locale),
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "license": LICENSE,
        "isAccessibleForFree": True,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "conformsTo": RFC_URL,
        "size": payload_oxum(artifacts["_payload"]),
        "distribution": [
            {
                "@type": "DataDownload",
                "name": artifacts[key]["label"],
                "encodingFormat": artifacts[key]["media_type"],
                "contentUrl": artifacts[key]["url"],
                "contentSize": f"{len(artifacts[key]['bytes'])} B",
                "sha256": artifacts[key]["sha256"],
            }
            for key in ("bundle", "checksums", "metadata")
        ],
    }
    graph = [dataset]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "applicationCategory": "EducationApplication",
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_bagit_{locale.lower()}"),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(locale: str, artifacts: dict[str, dict]) -> str:
    labels = {
        "bundle": COPY[locale]["bundle"],
        "checksums": COPY[locale]["checksum"],
        "metadata": COPY[locale]["metadata"],
    }
    return "".join(
        '<a class="download" href="{url}"><strong>{label}</strong>'
        "<span>{filename}</span></a>".format(
            url=html.escape(artifacts[key]["url"], quote=True),
            label=html.escape(labels[key]),
            filename=html.escape(artifacts[key]["filename"]),
        )
        for key in ("bundle", "checksums", "metadata")
    )


def _payload_rows(locale: str, artifacts: dict[str, dict]) -> str:
    descriptions = artifacts["_descriptions"]
    return "".join(
        "<tr><td><code>{path}</code></td><td>{media}</td><td>{size}</td>"
        "<td><code>{sha}</code></td></tr>".format(
            path=html.escape(path),
            media=html.escape(descriptions[path]["media_type"]),
            size=len(content),
            sha=_sha256(content)[:16] + "...",
        )
        for path, content in sorted(artifacts["_payload"].items())
    )


def render_page(
    locale: str,
    artifacts: dict[str, dict],
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other = "zh-Hant" if locale == "en" else "en"
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    integrity = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["integrity_items"]
    )
    scope = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["scope_items"]
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
                appstore_url(APP_KEY, f"iag_bagit_{locale.lower()}"),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _page_schema(locale, modified, artifacts, app_public),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    command = (
        f"shasum -a 256 -c {CHECKSUM_FILENAME}\n"
        f"unzip {BUNDLE_FILENAME}\n"
        "python3 -m pip install bagit==1.9.0\n"
        f"python3 -m bagit --validate {BAG_ROOT}"
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
<link rel="alternate" type="application/zip" href="{BUNDLE_URL}">
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#172033;--sub:#5d6678;--line:#dce2eb;--paper:#fff;--wash:#f3f5f8;--brand:#745329;--soft:#f8f1e7;--code:#15191f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.66 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1080px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.95);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:980px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:850px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:760;white-space:nowrap}}main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,45,64,.06)}}.downloads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}ol,ul{{padding-left:24px}}li{{margin:8px 0;color:var(--sub)}}pre{{background:var(--code);color:#f4eadb;border-radius:16px;padding:18px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:720;white-space:nowrap}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:820;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#f8f1e7)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:760px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{DATA_CATALOG}">{html.escape(copy['back'])}</a><a href="{html.escape(page_url(other), quote=True)}">{html.escape(copy['language'])}</a></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, artifacts)}</div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><pre>{html.escape(command)}</pre></article><article class="panel"><h2>Payload-Oxum</h2><pre>{html.escape(payload_oxum(artifacts['_payload']))}</pre><p>octets.streams</p></article></section>
<section class="wrap panel"><h2>{html.escape(copy['contents'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['path'])}</th><th>{html.escape(copy['format'])}</th><th>{html.escape(copy['bytes'])}</th><th>{html.escape(copy['sha'])}</th></tr></thead><tbody>{_payload_rows(locale, artifacts)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['integrity'])}</h2><ul>{integrity}</ul></article><article class="panel"><h2>{html.escape(copy['scope'])}</h2><ul>{scope}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['standards'])}</h2><p>{html.escape(copy['standards_text'])}</p><div class="sources"><a href="{RFC_URL}" rel="noopener">{html.escape(copy['rfc'])}</a><a href="{BAGIT_PYTHON_URL}" rel="noopener">{html.escape(copy['validator'])}</a><a href="{LICENSE}" rel="license noopener">{html.escape(copy['license'])}</a></div></section>
<div class="wrap">{app_section}</div>
</main>
<footer class="footer">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def update_data_index(pages: Path, artifacts: dict[str, dict]) -> bool:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index must exist before BagIt: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo RFC 8493 BagIt preservation package</h2>"
        "<p>Deposit-ready 37-symbol data with exact Payload-Oxum, dual "
        "payload and tag manifests, and deterministic ZIP serialization.</p>"
        '<span class="tag">BagIt 1.0 · SHA-256 + SHA-512 · EN + zh-Hant</span></a>'
    )
    existing = re.compile(
        r'<a class="item" href="' + re.escape(PACKAGE_URL) + r'">.*?</a>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    csvw_url = f"{SITE}/data/packages/zhuyin-bopomofo-csvw/"
    anchor = re.search(
        r'<a class="item" href="' + re.escape(csvw_url) + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if not anchor:
        raise RuntimeError("data/index.html is missing the CSVW card")
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
        "conformsTo": RFC_URL,
        "distribution": [
            {
                "@type": "DataDownload",
                "name": artifacts[key]["label"],
                "encodingFormat": artifacts[key]["media_type"],
                "contentUrl": artifacts[key]["url"],
            }
            for key in ("bundle", "checksums", "metadata")
        ],
    }
    position = next(
        (
            offset + 1
            for offset, dataset in enumerate(datasets)
            if dataset.get("url") == csvw_url
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
            for key in ("bundle", "checksums", "metadata")
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
        pages / "sitemap_bagit.xml",
        render_sitemap(page_modified, artifact_modified, artifacts),
    )
    return [
        PACKAGE_URL,
        ZH_PACKAGE_URL,
        BUNDLE_URL,
        CHECKSUM_URL,
        METADATA_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin BagIt resource -> {output}")


if __name__ == "__main__":
    main()
