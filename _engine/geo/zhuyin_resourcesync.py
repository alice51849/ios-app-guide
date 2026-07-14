#!/usr/bin/env python3
"""Publish an OAI ResourceSync 1.1 feed for the Bopomofo open-resource set."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import mimetypes
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import (  # noqa: E402
    render_versioned_page,
    write_text_if_changed,
)
from gen_feed import ensure_site_feed_discovery, feed_discovery_links  # noqa: E402
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
TODAY = dt.date.today().isoformat()
SPEC = "https://www.openarchives.org/rs/1.1/resourcesync"
RS_NAMESPACE = "http://www.openarchives.org/rs/terms/"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"

SOURCE_DESCRIPTION_COPY_PATH = Path("resourcesync") / "source-description.xml"
CAPABILITY_LIST_PATH = Path("resourcesync") / "capabilitylist.xml"
RESOURCE_LIST_PATH = Path("resourcesync") / "resourcelist.xml"
COLLECTION_PATH = Path("resourcesync") / "bopomofo-collection.jsonld"
STATE_PATH = Path("resourcesync") / "snapshot.json"
STATE_VERSION = 2
LANDING_PATH = Path("data") / "zhuyin-bopomofo-resourcesync.html"
ZH_LANDING_PATH = Path("zh-Hant") / LANDING_PATH
SITEMAP_PATH = Path("sitemap_resourcesync.xml")
IIIF_PATH = Path("iiif") / "3" / "bopomofo"
IIIF_IMAGE_PATHS = tuple(
    IIIF_PATH / "images" / f"u{codepoint:04X}.svg"
    for codepoint in range(0x3105, 0x312A)
)
RO_CRATE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-ro-crate"
RO_CRATE_REQUIRED_PATHS = (
    RO_CRATE_PATH / "index.html",
    RO_CRATE_PATH / "ro-crate-metadata.json",
    RO_CRATE_PATH / "ro-crate-preview.html",
    RO_CRATE_PATH / "README.txt",
    RO_CRATE_PATH / "LICENSE.txt",
    RO_CRATE_PATH / "checksums-sha256.txt",
    RO_CRATE_PATH / "bopomofo-37-symbols-ro-crate-1.3.zip",
    RO_CRATE_PATH / "data" / "zhuyin-bopomofo-ml-dataset.csv",
    RO_CRATE_PATH / "data" / "zhuyin-bopomofo-ml-dataset.jsonl",
    RO_CRATE_PATH / "data" / "zhuyin-bopomofo-ml-dataset.croissant.jsonld",
    RO_CRATE_PATH / "data" / "zhuyin-bopomofo-ml-dataset.csv-metadata.json",
    RO_CRATE_PATH / "data" / "zhuyin-bopomofo-vocabulary.jsonld",
    Path("zh-Hant") / RO_CRATE_PATH / "index.html",
)
METS_PREMIS_PATH = Path("data") / "packages" / "zhuyin-bopomofo-mets2-premis3"
METS_PREMIS_REQUIRED_PATHS = (
    METS_PREMIS_PATH / "index.html",
    METS_PREMIS_PATH / "mets.xml",
    METS_PREMIS_PATH / "premis.xml",
    METS_PREMIS_PATH / "README.txt",
    METS_PREMIS_PATH / "LICENSE.txt",
    METS_PREMIS_PATH / "checksums-sha256.txt",
    METS_PREMIS_PATH / "metadata.jsonld",
    METS_PREMIS_PATH / "bopomofo-37-symbols-mets2-premis3.zip",
    METS_PREMIS_PATH / "data" / "zhuyin-bopomofo-ml-dataset.csv",
    METS_PREMIS_PATH / "data" / "zhuyin-bopomofo-ml-dataset.jsonl",
    METS_PREMIS_PATH / "data" / "zhuyin-bopomofo-ml-dataset.croissant.jsonld",
    METS_PREMIS_PATH / "data" / "zhuyin-bopomofo-ml-dataset.csv-metadata.json",
    METS_PREMIS_PATH / "data" / "zhuyin-bopomofo-vocabulary.jsonld",
    Path("zh-Hant") / METS_PREMIS_PATH / "index.html",
)
ORE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-oai-ore"
ORE_REQUIRED_PATHS = (
    ORE_PATH / "index.html",
    ORE_PATH / "bopomofo-resource-map.ore.rdf",
    ORE_PATH / "bopomofo-resource-map.ore.ttl",
    ORE_PATH / "bopomofo-resource-map.ore.jsonld",
    ORE_PATH / "README.txt",
    ORE_PATH / "LICENSE.txt",
    ORE_PATH / "checksums-sha256.txt",
    ORE_PATH / "metadata.jsonld",
    ORE_PATH / "bopomofo-37-symbols-oai-ore-bundle.zip",
    Path("zh-Hant") / ORE_PATH / "index.html",
)
LDES_PATH = Path("data") / "packages" / "zhuyin-bopomofo-ldes"
LDES_REQUIRED_PATHS = (
    LDES_PATH / "index.html",
    LDES_PATH / "bopomofo-event-stream.jsonld",
    LDES_PATH / "bopomofo-event-stream.ttl",
    LDES_PATH / "nodes" / "page-001.jsonld",
    LDES_PATH / "nodes" / "page-002.jsonld",
    LDES_PATH / "nodes" / "page-003.jsonld",
    LDES_PATH / "bopomofo-event-member.shacl.ttl",
    LDES_PATH / "README.txt",
    LDES_PATH / "LICENSE.txt",
    LDES_PATH / "checksums-sha256.txt",
    LDES_PATH / "metadata.jsonld",
    LDES_PATH / "bopomofo-37-symbols-ldes-tree.zip",
    Path("zh-Hant") / LDES_PATH / "index.html",
)

SOURCE_DESCRIPTION_URL = "https://alice51849.github.io/.well-known/resourcesync"
SOURCE_DESCRIPTION_COPY_URL = f"{SITE}/{SOURCE_DESCRIPTION_COPY_PATH.as_posix()}"
CAPABILITY_LIST_URL = f"{SITE}/{CAPABILITY_LIST_PATH.as_posix()}"
RESOURCE_LIST_URL = f"{SITE}/{RESOURCE_LIST_PATH.as_posix()}"
COLLECTION_URL = f"{SITE}/{COLLECTION_PATH.as_posix()}"
LANDING_URL = f"{SITE}/{LANDING_PATH.as_posix()}"
ZH_LANDING_URL = f"{SITE}/{ZH_LANDING_PATH.as_posix()}"
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"

CONTENT_PATTERNS = (
    "data/zhuyin-bopomofo*",
    "data/packages/zhuyin-bopomofo/**/*",
    "data/packages/zhuyin-bopomofo-lms/**/*",
    "data/packages/zhuyin-bopomofo-epub/**/*",
    "data/packages/zhuyin-bopomofo-library/**/*",
    "data/packages/zhuyin-bopomofo-oer/**/*",
    "data/packages/zhuyin-bopomofo-dcat3/**/*",
    "data/packages/zhuyin-bopomofo-csvw/**/*",
    "data/packages/zhuyin-bopomofo-bagit/**/*",
    "data/packages/zhuyin-bopomofo-ocfl/**/*",
    "data/packages/zhuyin-bopomofo-ro-crate/**/*",
    "data/packages/zhuyin-bopomofo-mets2-premis3/**/*",
    "data/packages/zhuyin-bopomofo-oai-ore/**/*",
    "data/packages/zhuyin-bopomofo-ldes/**/*",
    "iiif/3/bopomofo/**/*",
    "publications/bopomofo-37-symbol-reference/**/*",
    "opds/bopomofo-37-symbol-reference.*",
    "api/v1/bopomofo-symbols/**/*",
    "tools/zhuyin-*",
    "zh-Hant/data/zhuyin-bopomofo*",
    "zh-Hant/data/packages/zhuyin-bopomofo/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-csvw/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-bagit/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-ocfl/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-ro-crate/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-mets2-premis3/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-oai-ore/**/*",
    "zh-Hant/data/packages/zhuyin-bopomofo-ldes/**/*",
    "zh-Hant/api/v1/bopomofo-symbols/**/*",
    "zh-Hant/tools/zhuyin-*",
)
REQUIRED_PATHS = (
    Path("data") / "zhuyin-bopomofo.json",
    Path("data") / "zhuyin-bopomofo-vocabulary.jsonld",
    Path("data") / "zhuyin-bopomofo-ml-dataset.croissant.jsonld",
    Path("data") / "zhuyin-bopomofo-ml-dataset.csv-metadata.json",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-csvw"
    / "bopomofo-37-symbols-csvw-bundle.zip",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-csvw"
    / "checksums-sha256.txt",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-csvw"
    / "metadata.jsonld",
    Path("data") / "packages" / "zhuyin-bopomofo" / "datapackage.json",
    Path("api") / "v1" / "bopomofo-symbols" / "index.json",
    Path("data") / "packages" / "zhuyin-bopomofo-lms" / "metadata.jsonld",
    Path("data") / "packages" / "zhuyin-bopomofo-lms" / "bopomofo-qti-2.1-en.zip",
    Path("data") / "packages" / "zhuyin-bopomofo-lms" / "bopomofo-qti-2.1-zh-hant.zip",
    Path("data") / "packages" / "zhuyin-bopomofo-lms" / "bopomofo-moodle-en.xml",
    Path("data") / "packages" / "zhuyin-bopomofo-lms" / "bopomofo-moodle-zh-hant.xml",
    Path("data") / "packages" / "zhuyin-bopomofo-lms" / "answer-key.csv",
    Path("data") / "packages" / "zhuyin-bopomofo-epub" / "metadata.jsonld",
    Path("data") / "packages" / "zhuyin-bopomofo-epub" / "bopomofo-37-symbol-reference-en.epub",
    Path("data") / "packages" / "zhuyin-bopomofo-epub" / "bopomofo-37-symbol-reference-zh-hant.epub",
    Path("publications") / "bopomofo-37-symbol-reference" / "en" / "manifest.json",
    Path("publications") / "bopomofo-37-symbol-reference" / "zh-Hant" / "manifest.json",
    Path("opds") / "bopomofo-37-symbol-reference.json",
    Path("opds") / "bopomofo-37-symbol-reference.xml",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-library"
    / "bopomofo-37-symbol-reference.marcxml.xml",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-library"
    / "bopomofo-37-symbol-reference.mods.xml",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-library"
    / "bopomofo-37-symbol-reference.bibframe.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-library"
    / "bopomofo-37-symbol-reference.bibframe.ttl",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-library"
    / "bopomofo-37-symbol-library-catalog-bundle.zip",
    Path("data") / "packages" / "zhuyin-bopomofo-library" / "metadata.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-oer"
    / "bopomofo-37-symbol-reference-en.oai-dc.xml",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-oer"
    / "bopomofo-37-symbol-reference-zh-hant.oai-dc.xml",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-oer"
    / "bopomofo-37-symbol-reference.dcmi-terms.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-oer"
    / "bopomofo-37-symbol-reference.lrmi.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-oer"
    / "bopomofo-37-symbol-oer-metadata-bundle.zip",
    Path("data") / "packages" / "zhuyin-bopomofo-oer" / "metadata.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-dcat3"
    / "bopomofo-open-data-catalog.dcat.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-dcat3"
    / "bopomofo-open-data-catalog.dcat.ttl",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-dcat3"
    / "bopomofo-open-data-catalog-dcat3-bundle.zip",
    Path("data") / "packages" / "zhuyin-bopomofo-dcat3" / "metadata.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-bagit"
    / "bopomofo-37-symbols-bagit-rfc8493.zip",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-bagit"
    / "checksums-sha256.txt",
    Path("data") / "packages" / "zhuyin-bopomofo-bagit" / "metadata.jsonld",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-ocfl"
    / "bopomofo-37-symbols-ocfl-1.1.zip",
    Path("data")
    / "packages"
    / "zhuyin-bopomofo-ocfl"
    / "checksums-sha256.txt",
    Path("data") / "packages" / "zhuyin-bopomofo-ocfl" / "metadata.jsonld",
    IIIF_PATH / "collection.json",
    IIIF_PATH / "manifest.json",
    IIIF_PATH / "bopomofo-37-symbols-iiif-presentation-3.zip",
    IIIF_PATH / "checksums-sha256.txt",
    IIIF_PATH / "metadata.jsonld",
    *IIIF_IMAGE_PATHS,
    *RO_CRATE_REQUIRED_PATHS,
    *METS_PREMIS_REQUIRED_PATHS,
    *ORE_REQUIRED_PATHS,
    *LDES_REQUIRED_PATHS,
)
CARD_START = "<!-- resourcesync-card:start -->"
CARD_END = "<!-- resourcesync-card:end -->"

COPY = {
    "en": {
        "lang": "en",
        "title": "Bopomofo ResourceSync Feed",
        "description": (
            "A standards-based synchronization feed for the complete Bopomofo "
            "open-data, linked-data, API and teaching-resource collection."
        ),
        "eyebrow": "OAI ResourceSync 1.1 · SHA-256 fixity · CC BY 4.0",
        "lead": (
            "Libraries, data catalogs and research tools can discover every "
            "published resource, verify exact bytes and refresh only what changed."
        ),
        "language": "繁體中文",
        "back": "Open data",
        "badges": (
            "Well-known discovery",
            "Complete 37-symbol API",
            "SHA-256 checksums",
            "No account or API key",
        ),
        "start": "Machine entry points",
        "start_text": (
            "Start at the well-known Source Description. It leads to one "
            "Capability List and a complete Resource List based on Sitemaps."
        ),
        "source": "Source Description",
        "capability": "Capability List",
        "resources": "Resource List",
        "metadata": "Collection metadata",
        "coverage": "What the feed covers",
        "coverage_text": (
            "The synchronized set is intentionally narrow: reusable Bopomofo "
            "reference data, standards metadata, static API responses and free "
            "teaching tools. Marketing pages and unrelated app content are excluded."
        ),
        "groups": (
            ("Data and linked data", "JSON, CSV, JSON-LD, Turtle and N-Triples"),
            (
                "Portable packages",
                "Croissant, Data Package, LMS imports, accessible EPUB editions, "
                "OER metadata, RFC 8493 BagIt, OCFL 1.1, RO-Crate 1.3, "
                "METS 2.0 with PREMIS 3.0 and the DCAT 3 catalog",
            ),
            (
                "Visual interoperability",
                "IIIF Presentation API 3 Collection, Manifest and 37 static SVG cards",
            ),
            ("Static API", "OpenAPI plus all 37 versioned symbol responses"),
            ("Open teaching tools", "Bilingual guides, decks and printable activities"),
        ),
        "sync": "How synchronization works",
        "sync_items": (
            "Discover the feed at /.well-known/resourcesync.",
            "Read the Capability List to locate the current Resource List.",
            "Compare SHA-256 and byte length before downloading a resource.",
            "Use the Resource List snapshot time to detect a new inventory.",
        ),
        "limits": "Scope and limitations",
        "limit_text": (
            "This is a synchronization inventory, not a pronunciation model, "
            "speech corpus, text converter, learner assessment or curriculum. "
            "ResourceSync does not guarantee that any third-party catalog will ingest it."
        ),
        "standard": "Official ResourceSync 1.1 specification",
        "license": "CC BY 4.0 license",
        "app_title": "Optional practice layer",
        "app_text": (
            "Lumi Bopomofo adds short, on-device activities. The synchronized "
            "open-resource collection remains free and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "A deterministic, machine-verifiable inventory for responsible reuse."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音開放資源 ResourceSync 同步目錄",
        "description": (
            "依標準發布的注音開放資料、Linked Data、API 與教學資源同步目錄。"
        ),
        "eyebrow": "OAI ResourceSync 1.1 · SHA-256 完整性 · CC BY 4.0",
        "lead": (
            "圖書館、資料目錄與研究工具可一次找到全部資源、核對實際檔案，"
            "並只更新有變動的內容。"
        ),
        "language": "English",
        "back": "開放資料",
        "badges": (
            "標準 well-known 發現",
            "完整 37 符號 API",
            "SHA-256 校驗",
            "免帳號與 API 金鑰",
        ),
        "start": "機器入口",
        "start_text": (
            "先讀取標準 well-known Source Description，再依序找到 Capability "
            "List 與以 Sitemap 為基礎的完整 Resource List。"
        ),
        "source": "Source Description",
        "capability": "Capability List",
        "resources": "Resource List",
        "metadata": "資源集合 metadata",
        "coverage": "同步範圍",
        "coverage_text": (
            "本集合刻意維持聚焦：只同步可重用的注音參考資料、標準 metadata、"
            "靜態 API 回應與免費教學工具，不納入行銷頁或無關 App 內容。"
        ),
        "groups": (
            ("資料與 Linked Data", "JSON、CSV、JSON-LD、Turtle 與 N-Triples"),
            (
                "可攜套件",
                "Croissant、Data Package、LMS 匯入檔、無障礙 EPUB 版本、"
                "OER metadata、RFC 8493 BagIt、OCFL 1.1、RO-Crate 1.3、"
                "METS 2.0 與 PREMIS 3.0，以及 DCAT 3 目錄",
            ),
            (
                "視覺互通資源",
                "IIIF Presentation API 3 Collection、Manifest 與 37 張靜態 SVG 圖卡",
            ),
            ("靜態 API", "OpenAPI 與完整 37 個版本化符號回應"),
            ("開放教學工具", "雙語指南、牌組與可列印活動"),
        ),
        "sync": "同步方式",
        "sync_items": (
            "從 /.well-known/resourcesync 發現同步入口。",
            "讀取 Capability List，取得目前 Resource List。",
            "下載前先比對 SHA-256 與檔案位元組長度。",
            "以 Resource List 快照時間判斷是否出現新清單。",
        ),
        "limits": "範圍與限制",
        "limit_text": (
            "這是同步清單，不是發音模型、語音語料、文字轉換器、學習評量或"
            "完整課程；ResourceSync 也不保證任何第三方目錄一定會收錄。"
        ),
        "standard": "ResourceSync 1.1 官方規格",
        "license": "CC BY 4.0 授權",
        "app_title": "選用練習層",
        "app_text": (
            "Lumi 注音星球提供裝置端短活動；同步的開放資源集合仍維持免費且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": "供負責任重用的固定生成、可機器驗證資源清單。",
    },
}


@dataclass(frozen=True)
class Resource:
    relative_path: Path
    url: str
    media_type: str
    byte_length: int
    sha256: str
    modified: str | None


def _media_type(path: Path) -> str:
    if (
        path.parent.name == "opds"
        and path.name == "bopomofo-37-symbol-reference.xml"
    ):
        return "application/atom+xml"
    suffix = path.suffix.lower()
    overrides = {
        ".csv": "text/csv",
        ".epub": "application/epub+zip",
        ".json": "application/json",
        ".jsonld": "application/ld+json",
        ".jsonl": "text/plain",
        ".nt": "application/n-triples",
        ".rdf": "application/rdf+xml",
        ".svg": "image/svg+xml",
        ".tsv": "text/tab-separated-values",
        ".ttl": "text/turtle",
        ".xhtml": "application/xhtml+xml",
    }
    if suffix in overrides:
        return overrides[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _content_modified(path: Path, content: bytes) -> str | None:
    if path.suffix.lower() != ".html":
        return None
    match = re.search(
        rb'<meta name="content-modified" content="(\d{4}-\d{2}-\d{2})">',
        content,
    )
    return match.group(1).decode("ascii") if match else None


def discover_resources(pages: Path) -> list[Resource]:
    paths = set()
    for pattern in CONTENT_PATTERNS:
        paths.update(path for path in pages.glob(pattern) if path.is_file())
    resources = []
    for path in sorted(paths):
        content = path.read_bytes()
        relative = path.relative_to(pages)
        resources.append(
            Resource(
                relative_path=relative,
                url=f"{SITE}/{relative.as_posix()}",
                media_type=_media_type(path),
                byte_length=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                modified=_content_modified(path, content),
            )
        )
    return resources


def validate_resources(resources: list[Resource]) -> None:
    paths = [resource.relative_path for resource in resources]
    if len(paths) != len(set(paths)):
        raise ValueError("ResourceSync paths must be unique")
    missing = [path for path in REQUIRED_PATHS if path not in set(paths)]
    if missing:
        raise ValueError(
            "ResourceSync prerequisites are missing: "
            + ", ".join(path.as_posix() for path in missing)
        )
    symbol_prefix = Path("api") / "v1" / "bopomofo-symbols" / "symbols"
    symbol_count = sum(
        resource.relative_path.parent == symbol_prefix
        and resource.relative_path.suffix == ".json"
        for resource in resources
    )
    if symbol_count != 37:
        raise ValueError(
            f"ResourceSync requires all 37 symbol responses, found {symbol_count}"
        )
    for resource in resources:
        if resource.byte_length <= 0:
            raise ValueError(f"ResourceSync resource is empty: {resource.url}")
        if not re.fullmatch(r"[0-9a-f]{64}", resource.sha256):
            raise ValueError(f"Invalid SHA-256 for {resource.url}")


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _next_revision_at(previous_at: str | None) -> str:
    candidate = _utc_now()
    if candidate.tzinfo is None:
        raise ValueError("ResourceSync revision time must include a timezone")
    candidate = candidate.astimezone(dt.timezone.utc).replace(microsecond=0)
    if previous_at:
        try:
            previous = dt.datetime.fromisoformat(
                previous_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid prior ResourceSync revision time: {previous_at}"
            ) from exc
        if previous.tzinfo is None:
            raise ValueError(
                f"Prior ResourceSync revision time lacks timezone: {previous_at}"
            )
        previous = previous.astimezone(dt.timezone.utc)
        candidate = max(candidate, previous + dt.timedelta(seconds=1))
    return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")


def _snapshot(pages: Path, resources: list[Resource]) -> dict:
    fingerprint_source = "\n".join(
        ":".join(
            (
                resource.relative_path.as_posix(),
                resource.sha256,
                str(resource.byte_length),
                resource.media_type,
                resource.modified or "",
            )
        )
        for resource in resources
    ).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_source).hexdigest()
    state_path = pages / STATE_PATH
    previous = {}
    if state_path.exists():
        previous = json.loads(state_path.read_text(encoding="utf-8"))
    unchanged = (
        previous.get("stateVersion") == STATE_VERSION
        and previous.get("fingerprint") == fingerprint
    )
    at = (
        previous["at"]
        if unchanged
        else _next_revision_at(previous.get("at"))
    )
    state = {
        "stateVersion": STATE_VERSION,
        "specification": SPEC,
        "at": at,
        "fingerprint": fingerprint,
        "resourceCount": len(resources),
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(
        state_path,
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
    )
    return state


def render_source_description() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NAMESPACE}" xmlns:rs="{RS_NAMESPACE}">
  <rs:ln rel="describedby" href={quoteattr(COLLECTION_URL)} type="application/ld+json"/>
  <rs:md capability="description"/>
  <url>
    <loc>{escape(CAPABILITY_LIST_URL)}</loc>
    <rs:md capability="capabilitylist"/>
    <rs:ln rel="describedby" href={quoteattr(COLLECTION_URL)} type="application/ld+json"/>
  </url>
</urlset>
"""


def render_capability_list() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NAMESPACE}" xmlns:rs="{RS_NAMESPACE}">
  <rs:ln rel="describedby" href={quoteattr(COLLECTION_URL)} type="application/ld+json"/>
  <rs:ln rel="up" href={quoteattr(SOURCE_DESCRIPTION_URL)} type="application/xml"/>
  <rs:md capability="capabilitylist"/>
  <url>
    <loc>{escape(RESOURCE_LIST_URL)}</loc>
    <rs:md capability="resourcelist"/>
  </url>
</urlset>
"""


def render_resource_list(resources: list[Resource], at: str) -> str:
    rows = []
    for resource in resources:
        lastmod = (
            f"\n    <lastmod>{resource.modified}</lastmod>"
            if resource.modified
            else ""
        )
        rows.append(
            "  <url>\n"
            f"    <loc>{escape(resource.url)}</loc>{lastmod}\n"
            f"    <rs:md hash={quoteattr('sha-256:' + resource.sha256)} "
            f"length={quoteattr(str(resource.byte_length))} "
            f"type={quoteattr(resource.media_type)}/>\n"
            "  </url>"
        )
    body = "\n".join(rows)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="{SITEMAP_NAMESPACE}" xmlns:rs="{RS_NAMESPACE}">
  <rs:ln rel="describedby" href={quoteattr(COLLECTION_URL)} type="application/ld+json"/>
  <rs:ln rel="up" href={quoteattr(CAPABILITY_LIST_URL)} type="application/xml"/>
  <rs:md capability="resourcelist" at={quoteattr(at)}/>
{body}
</urlset>
"""


def collection_metadata(resource_count: int, modified: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": f"{LANDING_URL}#collection",
        "name": "Bopomofo open-resource synchronization collection",
        "alternateName": "注音開放資源同步集合",
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "license": LICENSE,
        "isAccessibleForFree": True,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "version": "1.0",
        "conformsTo": SPEC,
        "size": f"{resource_count} resources",
        "distribution": [
            {
                "@type": "DataDownload",
                "name": "ResourceSync Source Description",
                "encodingFormat": "application/xml",
                "contentUrl": SOURCE_DESCRIPTION_URL,
            },
            {
                "@type": "DataDownload",
                "name": "ResourceSync Capability List",
                "encodingFormat": "application/xml",
                "contentUrl": CAPABILITY_LIST_URL,
            },
            {
                "@type": "DataDownload",
                "name": "ResourceSync Resource List",
                "encodingFormat": "application/xml",
                "contentUrl": RESOURCE_LIST_URL,
            },
        ],
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps",
            "url": SITE,
        },
    }


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match the registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def render_page(
    locale: str,
    resource_count: int,
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    canonical = LANDING_URL if locale == "en" else ZH_LANDING_URL
    other = ZH_LANDING_URL if locale == "en" else LANDING_URL
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    groups = "".join(
        f"<article><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></article>"
        for title, text in copy["groups"]
    )
    sync_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["sync_items"]
    )
    collection = collection_metadata(resource_count, modified)
    collection.pop("@context")
    schema_graph = [collection]
    app_block = ""
    if app_public:
        app_url = appstore_url(
            APP_KEY, f"iag_bopomofo_resourcesync_{locale.lower()}"
        )
        schema_graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "applicationCategory": "EducationApplication",
                "operatingSystem": "iOS",
                "url": app_url,
            }
        )
        app_block = (
            '<section class="app"><p class="kicker">{title}</p><p>{text}</p>'
            '<a href="{url}" rel="nofollow noopener">{cta} &rarr;</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(app_url, quote=True),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        {"@context": "https://schema.org", "@graph": schema_graph},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<link rel="alternate" hreflang="en" href="{LANDING_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_LANDING_URL}">
<link rel="alternate" hreflang="x-default" href="{LANDING_URL}">
<link rel="resourcesync" href="{CAPABILITY_LIST_URL}">
<link rel="describedby" type="application/ld+json" href="{COLLECTION_URL}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#15213a;--sub:#5c687d;--line:#dbe4f0;--brand:#315fc4;--bg:#f4f7fc;--paper:#fff;--soft:#edf3ff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.68 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}.wrap{{max-width:1020px;margin:auto;padding:24px 20px 72px}}a{{color:var(--brand)}}.top{{display:flex;justify-content:space-between;gap:16px;font-size:14px}}.top a{{font-weight:760;text-decoration:none;white-space:nowrap}}.hero{{padding:52px 0 28px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,56px);line-height:1.08;letter-spacing:-.035em;margin:10px 0 16px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}h3{{margin:0 0 6px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:820px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}.badges span{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:720;white-space:nowrap}}section{{margin-top:34px}}.panel,.app{{background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:23px;box-shadow:0 12px 30px rgba(27,44,79,.05)}}.links,.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:11px;margin-top:17px}}.links a,.grid article{{border:1px solid var(--line);border-radius:14px;padding:15px;background:#fbfcff}}.links a{{text-decoration:none;font-weight:780}}.grid p{{margin:0}}.count{{font-size:42px;font-weight:850;line-height:1;color:var(--brand)}}li{{margin:8px 0;color:var(--sub)}}.app a{{font-weight:820;text-decoration:none}}footer{{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}}
</style>
{feed_discovery_links()}
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{SITE}/data/">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(other, quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></header>
<section class="panel"><p class="count">{resource_count}</p><h2>{html.escape(copy['start'])}</h2><p>{html.escape(copy['start_text'])}</p><div class="links"><a href="{SOURCE_DESCRIPTION_URL}">{html.escape(copy['source'])} &rarr;</a><a href="{CAPABILITY_LIST_URL}">{html.escape(copy['capability'])} &rarr;</a><a href="{RESOURCE_LIST_URL}">{html.escape(copy['resources'])} &rarr;</a><a href="{COLLECTION_URL}">{html.escape(copy['metadata'])} &rarr;</a></div></section>
<section><h2>{html.escape(copy['coverage'])}</h2><p>{html.escape(copy['coverage_text'])}</p><div class="grid">{groups}</div></section>
<section class="panel"><h2>{html.escape(copy['sync'])}</h2><ol>{sync_items}</ol></section>
<section class="panel"><h2>{html.escape(copy['limits'])}</h2><p>{html.escape(copy['limit_text'])}</p><div class="links"><a href="{SPEC}" rel="noopener">{html.escape(copy['standard'])} &rarr;</a><a href="{LICENSE}" rel="license noopener">{html.escape(copy['license'])} &rarr;</a></div></section>
{app_block}
<footer>{html.escape(copy['footer'])}</footer>
</main>
</body>
</html>
"""


def _update_data_index(pages: Path) -> None:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index must exist before ResourceSync: {index}")
    content = index.read_text(encoding="utf-8")
    block = (
        f'{CARD_START}<a class="item" href="{LANDING_URL}"><div>'
        '<span class="tag">ResourceSync 1.1</span>'
        "<h2>Bopomofo synchronization feed</h2>"
        "<p>Well-known discovery, SHA-256 fixity and a complete harvestable "
        "inventory of the open Bopomofo collection.</p></div>"
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
    write_text_if_changed(index, updated)


def render_sitemap(modified: str, page_modified: dict[str, str]) -> str:
    entries = (
        (LANDING_URL, page_modified["en"]),
        (ZH_LANDING_URL, page_modified["zh-Hant"]),
        (SOURCE_DESCRIPTION_URL, modified),
        (SOURCE_DESCRIPTION_COPY_URL, modified),
        (CAPABILITY_LIST_URL, modified),
        (RESOURCE_LIST_URL, modified),
        (COLLECTION_URL, modified),
    )
    rows = "\n".join(
        f"  <url><loc>{escape(url)}</loc><lastmod>{date}</lastmod></url>"
        for url, date in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{SITEMAP_NAMESPACE}">\n{rows}\n</urlset>\n'
    )


def validate_control_documents(documents: list[str]) -> None:
    combined = "\n".join(documents)
    for forbidden in ("apps.apple.com", APP_ID, APP_NAME, "SoftwareApplication"):
        if forbidden in combined:
            raise ValueError(
                f"ResourceSync control documents must remain app-independent: "
                f"{forbidden}"
            )


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    ensure_site_feed_discovery(pages)
    public = is_app_public(pages) if app_public is None else app_public
    provisional = discover_resources(pages)
    expected_count = len(provisional) + sum(
        path not in {resource.relative_path for resource in provisional}
        for path in (LANDING_PATH, ZH_LANDING_PATH)
    )
    page_modified = {}
    for locale, path in (
        ("en", pages / LANDING_PATH),
        ("zh-Hant", pages / ZH_LANDING_PATH),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda modified, locale=locale: render_page(
                locale, expected_count, public, modified
            ),
            INITIAL_DATE,
            TODAY,
        )

    resources = discover_resources(pages)
    validate_resources(resources)
    snapshot = _snapshot(pages, resources)
    modified = snapshot["at"][:10]
    metadata = json.dumps(
        collection_metadata(len(resources), modified),
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    source_description = render_source_description()
    capability_list = render_capability_list()
    resource_list = render_resource_list(resources, snapshot["at"])
    validate_control_documents(
        [metadata, source_description, capability_list, resource_list]
    )

    outputs = {
        SOURCE_DESCRIPTION_COPY_PATH: source_description,
        CAPABILITY_LIST_PATH: capability_list,
        RESOURCE_LIST_PATH: resource_list,
        COLLECTION_PATH: metadata,
        SITEMAP_PATH: render_sitemap(modified, page_modified),
    }
    for relative, content in outputs.items():
        path = pages / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_if_changed(path, content)
    _update_data_index(pages)
    return [
        LANDING_URL,
        ZH_LANDING_URL,
        SOURCE_DESCRIPTION_URL,
        CAPABILITY_LIST_URL,
        RESOURCE_LIST_URL,
        COLLECTION_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin ResourceSync -> {output}")


if __name__ == "__main__":
    main()
