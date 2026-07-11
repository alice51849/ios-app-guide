#!/usr/bin/env python3
"""Publish an OCFL 1.1 preservation object for the open Bopomofo dataset."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import zipfile
from collections import defaultdict
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
from zhuyin_bagit_package import SOURCE_PAYLOADS  # noqa: E402
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
# Preserve the actual first-build instant so clean v1 rebuilds remain reproducible.
INITIAL_DATE = "2026-07-11"
INITIAL_TIMESTAMP = "2026-07-11T16:16:16Z"
TODAY = dt.date.today().isoformat()
PACKAGE_VERSION = "1.0.0"
OCFL_VERSION = "1.1"

PACKAGE_SLUG = "zhuyin-bopomofo-ocfl"
PACKAGE_PATH = Path("data") / "packages" / PACKAGE_SLUG
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}/"
ZH_PACKAGE_URL = f"{SITE}/zh-Hant/{PACKAGE_PATH.as_posix()}/"
OBJECT_ROOT = "bopomofo-37-symbols-ocfl"
OBJECT_ID = f"{PACKAGE_URL}#ocfl-object"
BUNDLE_FILENAME = "bopomofo-37-symbols-ocfl-1.1.zip"
CHECKSUM_FILENAME = "checksums-sha256.txt"
METADATA_FILENAME = "metadata.jsonld"
BUNDLE_URL = f"{PACKAGE_URL}{BUNDLE_FILENAME}"
CHECKSUM_URL = f"{PACKAGE_URL}{CHECKSUM_FILENAME}"
METADATA_URL = f"{PACKAGE_URL}{METADATA_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_ocfl.xml"
DATA_CATALOG = f"{SITE}/data/"

SPEC_URL = "https://ocfl.io/1.1/spec/"
SCHEMA_URL = "https://ocfl.io/1.1/spec/inventory_schema.json"
SPEC_SOURCE_URL = (
    "https://raw.githubusercontent.com/OCFL/spec/"
    "c3f88b31ab8c82c37a190a4f0e5b9bc3c9f01010/1.1/spec/index.md"
)
SPEC_SOURCE_SHA256 = (
    "3d02c6c68e542f471d9252cf1f02cd97e94615e3063930507fb2c33aa31d8f6e"
)
SCHEMA_SHA256 = (
    "3f87a36951c25464824a25273e1480fd68448668f05ee7fa5af0115716b0b82c"
)
VALIDATOR_URL = "https://github.com/zimeon/ocfl-py"
VALIDATOR_VERSION = "2.1.0"
ZIP_MEDIA_TYPE = "application/zip"
REFERENCE_SOURCES = HERE / "reference_datasets" / "ocfl" / "sources.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

DECLARATION_FILENAME = "0=ocfl_object_1.1"
DECLARATION_BYTES = b"ocfl_object_1.1\n"
INVENTORY_FILENAME = "inventory.json"
SIDECAR_FILENAME = "inventory.json.sha512"
INVENTORY_TYPE = "https://ocfl.io/1.1/spec/#inventory"
ALLOWED_INVENTORY_KEYS = {
    "id",
    "type",
    "digestAlgorithm",
    "head",
    "manifest",
    "versions",
    "fixity",
}

COPY = {
    "en": {
        "lang": "en",
        "title": "OCFL 1.1 Preservation Object for Bopomofo",
        "description": (
            "Download a deterministic, independently validated OCFL 1.1 object "
            "for the complete 37-symbol Bopomofo dataset, with SHA-512 "
            "content addressing and SHA-256 fixity."
        ),
        "eyebrow": "OCFL 1.1 · 10 logical files · SHA-512 inventory",
        "lead": (
            "A transparent, version-aware preservation object for digital "
            "repositories and durable custody of the open Bopomofo reference data."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "badges": (
            "Exact Namaste declaration",
            "Root + version inventory",
            "SHA-512 + SHA-256",
            "CC BY 4.0 content",
        ),
        "downloads": "Preservation object",
        "download_text": (
            "Verify the outer ZIP checksum, extract the single object root, then "
            "validate that directory. The ZIP is only a deterministic transfer "
            "wrapper around the OCFL object-at-rest layout."
        ),
        "bundle": "Complete OCFL object ZIP",
        "checksum": "Outer SHA-256",
        "metadata": "Package metadata",
        "validate": "Validate independently",
        "validate_text": (
            "The pinned ocfl-py validator checks the Namaste declaration, every "
            "inventory rule, sidecar, logical state, content path and digest."
        ),
        "tree": "Object layout",
        "contents": "Head-version logical state",
        "path": "Logical path",
        "format": "Format",
        "bytes": "Bytes",
        "sha": "SHA-512",
        "integrity": "Preservation design",
        "integrity_items": (
            "The object root and head-version directory contain byte-identical inventories and sidecars.",
            "The manifest maps SHA-512 digests to physical content paths.",
            "Each version state maps content digests to portable logical paths.",
            "A complete SHA-256 fixity block independently covers every stored content file.",
            "Future logical-state changes create a new forward-delta version instead of rewriting history.",
        ),
        "scope": "Scope and limits",
        "scope_items": (
            "This is one OCFL Object, not a complete OCFL Storage Root or repository.",
            "It contains reference data and standards metadata, not audio or learner records.",
            "OCFL defines an object-at-rest layout, not a ZIP transfer serialization or media type.",
            "The generic application/zip wrapper is not part of OCFL conformance.",
            "Validation does not imply OCFL community endorsement or repository ingest.",
        ),
        "standards": "Sources and interoperability",
        "standards_text": (
            "The object follows the published OCFL 1.1 specification with its "
            "1.1.1 editorial corrections. The generator hash-pins the official "
            "specification source and inventory schema."
        ),
        "spec": "OCFL 1.1 specification",
        "schema": "Official inventory schema",
        "validator": "ocfl-py validator",
        "license": "CC BY 4.0",
        "app_title": "Optional learning companion",
        "app_text": (
            "The OCFL object is complete and reusable without an app. Lumi "
            "Bopomofo is only an optional on-device practice layer."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Open preservation object · No account · No API key · "
            "No claim of institutional ingest"
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音資料 OCFL 1.1 數位保存物件",
        "description": (
            "下載完整 37 注音符號資料的 deterministic OCFL 1.1 保存物件，"
            "提供 SHA-512 content addressing 與 SHA-256 fixity。"
        ),
        "eyebrow": "OCFL 1.1 · 10 個 logical files · SHA-512 inventory",
        "lead": (
            "供數位典藏庫與長期 custody 使用，具透明目錄結構與版本能力的"
            "開放注音參考資料保存物件。"
        ),
        "back": "開放資料",
        "language": "English",
        "badges": (
            "精確 Namaste declaration",
            "Root＋version inventory",
            "SHA-512＋SHA-256",
            "CC BY 4.0 content",
        ),
        "downloads": "數位保存物件",
        "download_text": (
            "先核對 ZIP 外層 checksum，再解壓縮單一 object root 並驗證該目錄。"
            "ZIP 只是包裝 OCFL object-at-rest 目錄的 deterministic transfer wrapper。"
        ),
        "bundle": "完整 OCFL object ZIP",
        "checksum": "外層 SHA-256",
        "metadata": "套件 metadata",
        "validate": "獨立驗證",
        "validate_text": (
            "固定版本的 ocfl-py validator 會檢查 Namaste declaration、inventory "
            "規則、sidecar、logical state、content path 與全部 digest。"
        ),
        "tree": "物件目錄",
        "contents": "Head version logical state",
        "path": "Logical path",
        "format": "格式",
        "bytes": "Bytes",
        "sha": "SHA-512",
        "integrity": "保存設計",
        "integrity_items": (
            "Object root 與 head-version 目錄保存 byte-identical inventories 與 sidecars。",
            "Manifest 將 SHA-512 digests 對應到實體 content paths。",
            "每個 version state 都將 content digests 對應到可攜 logical paths。",
            "完整 SHA-256 fixity block 另行涵蓋每個已儲存 content file。",
            "未來 logical state 若改變，會新增 forward-delta version，而不會覆寫歷史。",
        ),
        "scope": "範圍與限制",
        "scope_items": (
            "這是一個 OCFL Object，不是完整 OCFL Storage Root 或 repository。",
            "內容為參考資料與標準 metadata，不含音訊或學習者紀錄。",
            "OCFL 定義 object-at-rest 目錄，不定義 ZIP transfer serialization 或 media type。",
            "通用 application/zip wrapper 不屬於 OCFL conformance。",
            "通過驗證不代表 OCFL community 背書或典藏庫已匯入。",
        ),
        "standards": "規格來源與互通性",
        "standards_text": (
            "物件依已發布的 OCFL 1.1 規格與 1.1.1 editorial corrections 建立；"
            "generator 固定官方規格原始檔與 inventory schema 的 hash。"
        ),
        "spec": "OCFL 1.1 規格",
        "schema": "官方 inventory schema",
        "validator": "ocfl-py validator",
        "license": "CC BY 4.0",
        "app_title": "選用學習工具",
        "app_text": (
            "OCFL 保存物件不需要 App 即可完整使用；Lumi 注音星球僅是選用的"
            "裝置端練習層。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "開放保存物件 · 免帳號 · 免 API key · 不宣稱機構已收錄",
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha512(content: bytes) -> str:
    return hashlib.sha512(content).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


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


def _safe_path(path: str) -> bool:
    parts = path.split("/")
    return (
        bool(path)
        and not path.startswith("/")
        and not path.endswith("/")
        and "\\" not in path
        and all(part not in {"", ".", ".."} for part in parts)
    )


def _utc_timestamp() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def render_readme() -> bytes:
    return f"""# Complete Bopomofo reference data OCFL object

This OCFL 1.1 object preserves the complete 37-symbol Bopomofo (Zhuyin)
table, its CSVW and MLCommons Croissant metadata, and the companion SKOS
vocabulary. It is one OCFL Object, not an OCFL Storage Root.

The CSV and its `<CSV filename>-metadata.json` document remain adjacent in
the logical state, so the relative CSVW `url` resolves after reconstruction.

## Validate the extracted object

```sh
python3 -m pip install ocfl-py=={VALIDATOR_VERSION}
ocfl-validate.py {OBJECT_ROOT}
```

OCFL validation checks structure, inventory semantics and stored-byte
integrity. Downstream users should also validate CSVW, Croissant, RDF and
SHACL semantics as needed.

Specification: {SPEC_URL}
Package guide: {PACKAGE_URL}
""".encode("utf-8")


def render_license() -> bytes:
    return (
        "Complete Bopomofo reference data OCFL preservation object\n"
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
            raise FileNotFoundError(f"Build the OCFL content source first: {path}")
        content = path.read_bytes()
        if not content:
            raise ValueError(f"OCFL content source is empty: {path}")
        payload[destination] = content
        descriptions[destination] = {
            "media_type": media_type,
            "label": label,
            "source": f"{SITE}/{source}",
        }
    payload["data/README.md"] = render_readme()
    payload["data/LICENSE.txt"] = render_license()
    descriptions["data/README.md"] = {
        "media_type": "text/markdown",
        "label": "Preservation and validation guide",
        "source": PACKAGE_URL,
    }
    descriptions["data/LICENSE.txt"] = {
        "media_type": "text/plain",
        "label": "CC BY 4.0 license notice",
        "source": LICENSE,
    }

    rows = records()
    validate_records(rows)
    csv_path = "data/zhuyin-bopomofo-ml-dataset.csv"
    if payload[csv_path] != render_csv(rows).encode("utf-8"):
        raise ValueError("OCFL CSV drifted from the canonical 37-row table")
    return payload, descriptions


def _state_for_payload(payload: dict[str, bytes]) -> dict[str, list[str]]:
    state: defaultdict[str, list[str]] = defaultdict(list)
    for logical_path, content in sorted(payload.items()):
        if not _safe_path(logical_path):
            raise ValueError(f"Unsafe OCFL logical path: {logical_path}")
        state[_sha512(content)].append(logical_path)
    return {digest: paths for digest, paths in sorted(state.items())}


def _sidecar(inventory_bytes: bytes) -> bytes:
    return f"{_sha512(inventory_bytes)}  {INVENTORY_FILENAME}\n".encode("ascii")


def _fixity_for_manifest(
    object_files: dict[str, bytes],
    manifest: dict[str, list[str]],
) -> dict[str, dict[str, list[str]]]:
    fixity: defaultdict[str, list[str]] = defaultdict(list)
    for paths in manifest.values():
        for content_path in paths:
            fixity[_sha256(object_files[content_path])].append(content_path)
    return {
        "sha256": {
            digest: sorted(paths)
            for digest, paths in sorted(fixity.items())
        }
    }


def _version_record(
    state: dict[str, list[str]],
    created: str,
    version: str,
) -> dict:
    return {
        "created": created,
        "message": (
            "Initial preservation version of the complete Bopomofo reference data."
            if version == "v1"
            else "Preservation update after a logical-state change."
        ),
        "state": state,
        "user": {
            "address": SITE,
            "name": "Lumi Apps - iOS App Guide",
        },
    }


def _inventory(
    head: str,
    manifest: dict[str, list[str]],
    versions: dict[str, dict],
    fixity: dict[str, dict[str, list[str]]],
) -> dict:
    return {
        "digestAlgorithm": "sha512",
        "fixity": fixity,
        "head": head,
        "id": OBJECT_ID,
        "manifest": {
            digest: sorted(paths)
            for digest, paths in sorted(manifest.items())
        },
        "type": INVENTORY_TYPE,
        "versions": versions,
    }


def make_object_files(
    payload: dict[str, bytes],
    created: str = INITIAL_TIMESTAMP,
    previous_files: dict[str, bytes] | None = None,
) -> dict[str, bytes]:
    state = _state_for_payload(payload)
    if previous_files is None:
        object_files = {DECLARATION_FILENAME: DECLARATION_BYTES}
        manifest = {}
        for digest, logical_paths in state.items():
            logical_path = logical_paths[0]
            content_path = f"v1/content/{logical_path}"
            object_files[content_path] = payload[logical_path]
            manifest[digest] = [content_path]
        versions = {"v1": _version_record(state, created, "v1")}
        inventory = _inventory(
            "v1",
            manifest,
            versions,
            _fixity_for_manifest(object_files, manifest),
        )
        inventory_bytes = _json_bytes(inventory)
        sidecar = _sidecar(inventory_bytes)
        object_files[INVENTORY_FILENAME] = inventory_bytes
        object_files[SIDECAR_FILENAME] = sidecar
        object_files["v1/inventory.json"] = inventory_bytes
        object_files["v1/inventory.json.sha512"] = sidecar
        return object_files

    validate_object_files(previous_files)
    previous_inventory = json.loads(previous_files[INVENTORY_FILENAME])
    previous_head = previous_inventory["head"]
    if previous_inventory["versions"][previous_head]["state"] == state:
        return dict(previous_files)

    next_number = int(previous_head[1:]) + 1
    head = f"v{next_number}"
    object_files = {
        path: content
        for path, content in previous_files.items()
        if path not in {INVENTORY_FILENAME, SIDECAR_FILENAME}
    }
    manifest = {
        digest: list(paths)
        for digest, paths in previous_inventory["manifest"].items()
    }
    for digest, logical_paths in state.items():
        if digest in manifest:
            continue
        logical_path = logical_paths[0]
        content_path = f"{head}/content/{logical_path}"
        object_files[content_path] = payload[logical_path]
        manifest[digest] = [content_path]
    versions = {
        version: value
        for version, value in previous_inventory["versions"].items()
    }
    versions[head] = _version_record(state, created, head)
    inventory = _inventory(
        head,
        manifest,
        versions,
        _fixity_for_manifest(object_files, manifest),
    )
    inventory_bytes = _json_bytes(inventory)
    sidecar = _sidecar(inventory_bytes)
    object_files[INVENTORY_FILENAME] = inventory_bytes
    object_files[SIDECAR_FILENAME] = sidecar
    object_files[f"{head}/inventory.json"] = inventory_bytes
    object_files[f"{head}/inventory.json.sha512"] = sidecar
    return object_files


def _zip_bytes(object_files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, content in sorted(object_files.items()):
            info = zipfile.ZipInfo(f"{OBJECT_ROOT}/{relative}", ZIP_TIMESTAMP)
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
    object_files: dict[str, bytes],
) -> bytes:
    inventory = json.loads(object_files[INVENTORY_FILENAME])
    document = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": f"{PACKAGE_URL}#dataset",
        "alternateName": "完整注音參考資料 OCFL 1.1 數位保存物件",
        "conformsTo": SPEC_URL,
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps - iOS App Guide",
            "url": SITE,
        },
        "dateModified": modified,
        "datePublished": INITIAL_DATE,
        "description": COPY["en"]["description"],
        "distribution": [
            {
                "@type": "DataDownload",
                "contentSize": f"{len(artifact['bytes'])} B",
                "contentUrl": artifact["url"],
                "encodingFormat": artifact["media_type"],
                "name": artifact["label"],
                "sha256": artifact["sha256"],
            }
            for artifact in (bundle, checksums)
        ],
        "hasPart": [
            {
                "@type": "DigitalDocument",
                "contentSize": f"{len(content)} B",
                "description": descriptions[path]["label"],
                "encodingFormat": descriptions[path]["media_type"],
                "isBasedOn": descriptions[path]["source"],
                "name": path,
                "sha256": _sha256(content),
                "sha512": _sha512(content),
            }
            for path, content in sorted(payload.items())
        ],
        "identifier": OBJECT_ID,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "isAccessibleForFree": True,
        "license": LICENSE,
        "measurementTechnique": (
            "OCFL 1.1 object with SHA-512 content addressing and complete "
            "SHA-256 fixity"
        ),
        "name": "OCFL 1.1 object for complete Bopomofo reference data",
        "numberOfItems": len(payload),
        "url": PACKAGE_URL,
        "version": inventory["head"],
    }
    return _json_bytes(document)


def make_artifacts(
    payload: dict[str, bytes],
    descriptions: dict[str, dict],
    modified: str,
    previous_files: dict[str, bytes] | None = None,
    created: str = INITIAL_TIMESTAMP,
) -> dict[str, dict]:
    object_files = make_object_files(payload, created, previous_files)
    bundle = _artifact(
        BUNDLE_FILENAME,
        BUNDLE_URL,
        ZIP_MEDIA_TYPE,
        "Deterministic OCFL 1.1 object ZIP",
        _zip_bytes(object_files),
    )
    checksums = _artifact(
        CHECKSUM_FILENAME,
        CHECKSUM_URL,
        "text/plain",
        "Outer SHA-256 checksum",
        f"{bundle['sha256']}  {BUNDLE_FILENAME}\n".encode("ascii"),
    )
    metadata = _artifact(
        METADATA_FILENAME,
        METADATA_URL,
        "application/ld+json",
        "Schema.org OCFL package metadata",
        package_metadata(
            modified,
            payload,
            descriptions,
            bundle,
            checksums,
            object_files,
        ),
    )
    return {
        "bundle": bundle,
        "checksums": checksums,
        "metadata": metadata,
        "_object_files": object_files,
        "_payload": payload,
        "_descriptions": descriptions,
    }


def _validate_sidecar(
    inventory_bytes: bytes,
    sidecar_bytes: bytes,
    location: str,
) -> None:
    expected = _sidecar(inventory_bytes)
    if sidecar_bytes != expected:
        raise ValueError(f"OCFL inventory sidecar mismatch: {location}")


def _validate_paths(paths: list[str], label: str) -> None:
    if not paths or paths != sorted(set(paths)):
        raise ValueError(f"OCFL {label} paths must be non-empty, unique and sorted")
    if any(not _safe_path(path) for path in paths):
        raise ValueError(f"OCFL {label} contains an unsafe path")
    for path in paths:
        if any(
            other != path and other.startswith(path + "/")
            for other in paths
        ):
            raise ValueError(f"OCFL {label} paths conflict: {path}")


def validate_object_files(
    object_files: dict[str, bytes],
    current_payload: dict[str, bytes] | None = None,
) -> None:
    if object_files.get(DECLARATION_FILENAME) != DECLARATION_BYTES:
        raise ValueError("OCFL object declaration is missing or not exact")
    if any(not _safe_path(path) for path in object_files):
        raise ValueError("OCFL object contains an unsafe relative path")
    inventory_bytes = object_files.get(INVENTORY_FILENAME)
    sidecar_bytes = object_files.get(SIDECAR_FILENAME)
    if inventory_bytes is None or sidecar_bytes is None:
        raise ValueError("OCFL root inventory or sidecar is missing")
    _validate_sidecar(inventory_bytes, sidecar_bytes, "object root")
    try:
        inventory = json.loads(inventory_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("OCFL root inventory is not UTF-8 JSON") from error
    if set(inventory) != ALLOWED_INVENTORY_KEYS:
        raise ValueError("OCFL inventory keys do not match the 1.1 specification")
    if (
        inventory["id"] != OBJECT_ID
        or inventory["type"] != INVENTORY_TYPE
        or inventory["digestAlgorithm"] != "sha512"
    ):
        raise ValueError("OCFL inventory identity, type or digest algorithm drifted")

    versions = inventory["versions"]
    version_names = sorted(versions, key=lambda value: int(value[1:]))
    if version_names != [f"v{number}" for number in range(1, len(versions) + 1)]:
        raise ValueError("OCFL versions must be a continuous non-padded sequence")
    if inventory["head"] != version_names[-1]:
        raise ValueError("OCFL inventory head is not the highest version")
    allowed_roots = {
        DECLARATION_FILENAME,
        INVENTORY_FILENAME,
        SIDECAR_FILENAME,
        *version_names,
    }
    if any(path.split("/", 1)[0] not in allowed_roots for path in object_files):
        raise ValueError("OCFL object root contains an unrecognized entry")

    for version in version_names:
        version_inventory_path = f"{version}/inventory.json"
        version_sidecar_path = f"{version}/inventory.json.sha512"
        if version_inventory_path not in object_files:
            raise ValueError(f"OCFL {version} inventory is missing")
        if version_sidecar_path not in object_files:
            raise ValueError(f"OCFL {version} inventory sidecar is missing")
        version_inventory_bytes = object_files[version_inventory_path]
        _validate_sidecar(
            version_inventory_bytes,
            object_files[version_sidecar_path],
            version,
        )
        version_inventory = json.loads(version_inventory_bytes)
        if version_inventory.get("head") != version:
            raise ValueError(f"OCFL {version} inventory head is incorrect")
        if version == inventory["head"] and version_inventory_bytes != inventory_bytes:
            raise ValueError("OCFL head and object-root inventories must match")

    manifest = inventory["manifest"]
    physical_paths = []
    for digest, paths in manifest.items():
        if not re.fullmatch(r"[0-9a-f]{128}", digest):
            raise ValueError("OCFL manifest contains a non-SHA-512 digest")
        _validate_paths(paths, "manifest")
        for path in paths:
            if not re.fullmatch(r"v[1-9][0-9]*/content/.+", path):
                raise ValueError(f"OCFL manifest path is outside version content: {path}")
            content = object_files.get(path)
            if content is None or _sha512(content) != digest:
                raise ValueError(f"OCFL manifest content mismatch: {path}")
            physical_paths.append(path)
    if len(physical_paths) != len(set(physical_paths)):
        raise ValueError("OCFL physical content path appears under multiple digests")
    actual_content_paths = sorted(
        path for path in object_files if re.fullmatch(r"v[1-9][0-9]*/content/.+", path)
    )
    if sorted(physical_paths) != actual_content_paths:
        raise ValueError("OCFL manifest does not cover every stored content file")

    used_digests = set()
    for version in version_names:
        record = versions[version]
        if set(record) - {"created", "message", "state", "user"}:
            raise ValueError(f"OCFL {version} record contains unknown keys")
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            record.get("created", ""),
        ):
            raise ValueError(f"OCFL {version} created value is not RFC 3339 UTC")
        logical_paths = []
        for digest, paths in record["state"].items():
            if digest not in manifest:
                raise ValueError(f"OCFL {version} state digest is absent from manifest")
            _validate_paths(paths, f"{version} logical state")
            logical_paths.extend(paths)
            used_digests.add(digest)
        _validate_paths(sorted(logical_paths), f"{version} combined logical state")
    if used_digests != set(manifest):
        raise ValueError("OCFL manifest contains content unused by every version")

    fixity = inventory["fixity"]
    if set(fixity) != {"sha256"}:
        raise ValueError("OCFL fixity must contain the complete SHA-256 block")
    fixed_paths = []
    for digest, paths in fixity["sha256"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("OCFL fixity contains a non-SHA-256 digest")
        _validate_paths(paths, "fixity")
        for path in paths:
            content = object_files.get(path)
            if content is None or _sha256(content) != digest:
                raise ValueError(f"OCFL SHA-256 fixity mismatch: {path}")
            fixed_paths.append(path)
    if sorted(fixed_paths) != actual_content_paths:
        raise ValueError("OCFL SHA-256 fixity does not cover every content file")

    if current_payload is not None:
        if len(current_payload) != 10:
            raise ValueError("OCFL head state must contain exactly ten logical files")
        if inventory["versions"][inventory["head"]]["state"] != _state_for_payload(
            current_payload
        ):
            raise ValueError("OCFL head state drifted from the current payload")

    raw = b"\n".join(object_files.values())
    for forbidden in (
        b"apps.apple.com",
        APP_ID.encode("ascii"),
        APP_NAME.encode("utf-8"),
        b"SoftwareApplication",
    ):
        if forbidden in raw:
            raise ValueError("App promotion leaked into OCFL preservation bytes")


def validate_reference_pin() -> None:
    source = json.loads(REFERENCE_SOURCES.read_text(encoding="utf-8"))
    if (
        source.get("version") != "OCFL 1.1.1"
        or source.get("objectDeclaration") != "ocfl_object_1.1"
    ):
        raise ValueError("OCFL source pin version or declaration drifted")
    if source.get("sources") != [
        {"url": SPEC_SOURCE_URL, "sha256": SPEC_SOURCE_SHA256},
        {"url": SCHEMA_URL, "sha256": SCHEMA_SHA256},
    ]:
        raise ValueError("OCFL official source URLs or SHA-256 pins drifted")


def validate_artifacts(artifacts: dict[str, dict]) -> None:
    validate_reference_pin()
    payload = artifacts["_payload"]
    object_files = artifacts["_object_files"]
    validate_object_files(object_files, payload)
    expected_names = [
        f"{OBJECT_ROOT}/{path}" for path in sorted(object_files)
    ]
    with zipfile.ZipFile(io.BytesIO(artifacts["bundle"]["bytes"])) as archive:
        if archive.namelist() != expected_names:
            raise ValueError("OCFL ZIP membership or order is not deterministic")
        for path, content in object_files.items():
            name = f"{OBJECT_ROOT}/{path}"
            if archive.read(name) != content:
                raise ValueError(f"OCFL ZIP content mismatch: {path}")
            info = archive.getinfo(name)
            if (
                info.date_time != ZIP_TIMESTAMP
                or info.compress_type != zipfile.ZIP_STORED
                or (info.external_attr >> 16) & 0o777 != 0o644
            ):
                raise ValueError(f"OCFL ZIP metadata is not deterministic: {path}")
    expected_checksum = (
        f"{_sha256(artifacts['bundle']['bytes'])}  {BUNDLE_FILENAME}\n"
    ).encode("ascii")
    if artifacts["checksums"]["bytes"] != expected_checksum:
        raise ValueError("OCFL outer checksum does not match the ZIP")
    metadata = json.loads(artifacts["metadata"]["bytes"])
    inventory = json.loads(object_files[INVENTORY_FILENAME])
    if (
        metadata.get("conformsTo") != SPEC_URL
        or metadata.get("identifier") != OBJECT_ID
        or metadata.get("version") != inventory["head"]
        or metadata.get("numberOfItems") != 10
    ):
        raise ValueError("OCFL package metadata identity or counts drifted")
    parts = {item["name"]: item for item in metadata.get("hasPart", [])}
    if set(parts) != set(payload):
        raise ValueError("OCFL metadata must list every head-state logical file")
    for path, content in payload.items():
        if (
            parts[path]["sha256"] != _sha256(content)
            or parts[path]["sha512"] != _sha512(content)
            or parts[path]["contentSize"] != f"{len(content)} B"
        ):
            raise ValueError(f"OCFL metadata drifted from logical content: {path}")


def _read_existing_object(pages: Path) -> dict[str, bytes] | None:
    bundle_path = pages / PACKAGE_PATH / BUNDLE_FILENAME
    if not bundle_path.exists():
        return None
    with zipfile.ZipFile(bundle_path) as archive:
        prefix = f"{OBJECT_ROOT}/"
        names = archive.namelist()
        if not names or any(not name.startswith(prefix) for name in names):
            raise ValueError("Existing OCFL ZIP does not contain one expected object root")
        object_files = {
            name[len(prefix) :]: archive.read(name)
            for name in names
            if name != prefix
        }
    validate_object_files(object_files)
    return object_files


def _prior_modified(pages: Path) -> str:
    path = pages / PACKAGE_PATH / METADATA_FILENAME
    if not path.exists():
        return INITIAL_TIMESTAMP
    try:
        return json.loads(path.read_text(encoding="utf-8"))["dateModified"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return INITIAL_TIMESTAMP


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
    previous_files = _read_existing_object(pages)
    prior = _prior_modified(pages)
    created = INITIAL_TIMESTAMP if previous_files is None else _utc_timestamp()
    artifacts = make_artifacts(
        payload,
        descriptions,
        prior,
        previous_files,
        created,
    )
    validate_artifacts(artifacts)
    if _outputs_match(pages, artifacts):
        return artifacts, prior
    artifacts = make_artifacts(
        payload,
        descriptions,
        created,
        previous_files,
        created,
    )
    validate_artifacts(artifacts)
    for key, path in _output_paths(pages).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != artifacts[key]["bytes"]:
            path.write_bytes(artifacts[key]["bytes"])
    return artifacts, created


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
    inventory = json.loads(artifacts["_object_files"][INVENTORY_FILENAME])
    dataset = {
        "@type": "Dataset",
        "@id": f"{PACKAGE_URL}#dataset",
        "conformsTo": SPEC_URL,
        "dateModified": modified,
        "datePublished": INITIAL_DATE,
        "description": COPY[locale]["description"],
        "distribution": [
            {
                "@type": "DataDownload",
                "contentSize": f"{len(artifacts[key]['bytes'])} B",
                "contentUrl": artifacts[key]["url"],
                "encodingFormat": artifacts[key]["media_type"],
                "name": artifacts[key]["label"],
                "sha256": artifacts[key]["sha256"],
            }
            for key in ("bundle", "checksums", "metadata")
        ],
        "identifier": OBJECT_ID,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "isAccessibleForFree": True,
        "license": LICENSE,
        "name": COPY[locale]["title"],
        "numberOfItems": len(artifacts["_payload"]),
        "url": page_url(locale),
        "version": inventory["head"],
    }
    graph = [dataset]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "applicationCategory": "EducationApplication",
                "name": APP_NAME,
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_ocfl_{locale.lower()}"),
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


def _payload_rows(artifacts: dict[str, dict]) -> str:
    descriptions = artifacts["_descriptions"]
    return "".join(
        "<tr><td><code>{path}</code></td><td>{media}</td><td>{size}</td>"
        "<td><code>{sha}</code></td></tr>".format(
            path=html.escape(path),
            media=html.escape(descriptions[path]["media_type"]),
            size=len(content),
            sha=_sha512(content)[:16] + "...",
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
                appstore_url(APP_KEY, f"iag_ocfl_{locale.lower()}"),
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
        f"python3 -m pip install ocfl-py=={VALIDATOR_VERSION}\n"
        f"ocfl-validate.py {OBJECT_ROOT}"
    )
    object_files = artifacts["_object_files"]
    inventory = json.loads(object_files[INVENTORY_FILENAME])
    versions = sorted(
        inventory["versions"],
        key=lambda value: int(value[1:]),
    )
    tree_lines = [
        f"{OBJECT_ROOT}/",
        f"├── {DECLARATION_FILENAME}",
        "├── inventory.json",
        "├── inventory.json.sha512",
    ]
    for index, version in enumerate(versions):
        connector = "└──" if index == len(versions) - 1 else "├──"
        has_content = any(
            path.startswith(f"{version}/content/") for path in object_files
        )
        contents = "inventory + sidecar + content/" if has_content else "inventory + sidecar"
        tree_lines.append(f"{connector} {version}/ ({contents})")
    tree = "\n".join(tree_lines)
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
:root{{--ink:#172033;--sub:#5d6678;--line:#dce2eb;--paper:#fff;--wash:#f3f5f8;--brand:#455c49;--soft:#edf4ee;--code:#15191f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.66 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1080px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.95);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:980px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:850px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:760;white-space:nowrap}}main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,45,64,.06)}}.downloads{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}ul{{padding-left:24px}}li{{margin:8px 0;color:var(--sub)}}pre{{background:var(--code);color:#e7f3e9;border-radius:16px;padding:18px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:720;white-space:nowrap}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:820;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#edf4ee)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:760px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{DATA_CATALOG}">{html.escape(copy['back'])}</a><a href="{html.escape(page_url(other), quote=True)}">{html.escape(copy['language'])}</a></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, artifacts)}</div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><pre>{html.escape(command)}</pre></article><article class="panel"><h2>{html.escape(copy['tree'])}</h2><pre>{html.escape(tree)}</pre></article></section>
<section class="wrap panel"><h2>{html.escape(copy['contents'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['path'])}</th><th>{html.escape(copy['format'])}</th><th>{html.escape(copy['bytes'])}</th><th>{html.escape(copy['sha'])}</th></tr></thead><tbody>{_payload_rows(artifacts)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['integrity'])}</h2><ul>{integrity}</ul></article><article class="panel"><h2>{html.escape(copy['scope'])}</h2><ul>{scope}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['standards'])}</h2><p>{html.escape(copy['standards_text'])}</p><div class="sources"><a href="{SPEC_URL}" rel="noopener">{html.escape(copy['spec'])}</a><a href="{SCHEMA_URL}" rel="noopener">{html.escape(copy['schema'])}</a><a href="{VALIDATOR_URL}" rel="noopener">{html.escape(copy['validator'])}</a><a href="{LICENSE}" rel="license noopener">{html.escape(copy['license'])}</a></div></section>
<div class="wrap">{app_section}</div>
</main>
<footer class="footer">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def update_data_index(pages: Path, artifacts: dict[str, dict]) -> bool:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index must exist before OCFL: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'<a class="item" href="{PACKAGE_URL}">'
        "<h2>Bopomofo OCFL 1.1 preservation object</h2>"
        "<p>Version-aware 37-symbol preservation object with SHA-512 "
        "content addressing, complete SHA-256 fixity and deterministic ZIP.</p>"
        '<span class="tag">OCFL 1.1 · SHA-512 + SHA-256 · EN + zh-Hant</span></a>'
    )
    existing = re.compile(
        r'<a class="item" href="' + re.escape(PACKAGE_URL) + r'">.*?</a>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    bagit_url = f"{SITE}/data/packages/zhuyin-bopomofo-bagit/"
    anchor = re.search(
        r'<a class="item" href="' + re.escape(bagit_url) + r'">.*?</a>',
        updated,
        re.DOTALL,
    )
    if not anchor:
        raise RuntimeError("data/index.html is missing the BagIt card")
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
        "conformsTo": SPEC_URL,
        "description": COPY["en"]["description"],
        "distribution": [
            {
                "@type": "DataDownload",
                "contentUrl": artifacts[key]["url"],
                "encodingFormat": artifacts[key]["media_type"],
                "name": artifacts[key]["label"],
            }
            for key in ("bundle", "checksums", "metadata")
        ],
        "license": LICENSE,
        "name": COPY["en"]["title"],
        "url": PACKAGE_URL,
    }
    position = next(
        (
            offset + 1
            for offset, dataset in enumerate(datasets)
            if dataset.get("url") == bagit_url
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
        pages / "sitemap_ocfl.xml",
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
        print(f"Zhuyin OCFL resource -> {output}")


if __name__ == "__main__":
    main()
