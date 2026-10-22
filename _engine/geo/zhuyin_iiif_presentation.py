#!/usr/bin/env python3
"""Publish all 37 Bopomofo symbols as a IIIF Presentation API 3 resource."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import math
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


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
    CSV_URL,
    LANDING_URL as CROISSANT_LANDING_URL,
    LICENSE,
    METADATA_URL as CROISSANT_METADATA_URL,
    SITE,
    records,
    validate_records,
)


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-12"
NAV_DATE = "2026-07-11T17:50:00Z"
TODAY = dt.date.today().isoformat()
VERSION = "3.0.0"
CARD_SIZE = 1200

LANDING_SLUG = "zhuyin-bopomofo-iiif-presentation-3"
LANDING_URL = f"{SITE}/data/{LANDING_SLUG}.html"
ZH_LANDING_URL = f"{SITE}/zh-Hant/data/{LANDING_SLUG}.html"
RESOURCE_PATH = Path("iiif") / "3" / "bopomofo"
RESOURCE_URL = f"{SITE}/{RESOURCE_PATH.as_posix()}"
COLLECTION_FILENAME = "collection.json"
MANIFEST_FILENAME = "manifest.json"
BUNDLE_FILENAME = "bopomofo-37-symbols-iiif-presentation-3.zip"
CHECKSUM_FILENAME = "checksums-sha256.txt"
METADATA_FILENAME = "metadata.jsonld"
COLLECTION_URL = f"{RESOURCE_URL}/{COLLECTION_FILENAME}"
MANIFEST_URL = f"{RESOURCE_URL}/{MANIFEST_FILENAME}"
BUNDLE_URL = f"{RESOURCE_URL}/{BUNDLE_FILENAME}"
CHECKSUM_URL = f"{RESOURCE_URL}/{CHECKSUM_FILENAME}"
METADATA_URL = f"{RESOURCE_URL}/{METADATA_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_iiif.xml"
DATA_CATALOG = f"{SITE}/data/"
ZIP_ROOT = "bopomofo-37-symbols-iiif-presentation-3"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

IIIF_CONTEXT = "http://iiif.io/api/presentation/3/context.json"
IIIF_SPEC_URL = "https://iiif.io/api/presentation/3.0/"
IIIF_API_COMMIT = "28a88829699ebbbe7722b4692cf3b7b67969bc6c"
IIIF_SPEC_SOURCE_URL = (
    "https://raw.githubusercontent.com/IIIF/api/"
    f"{IIIF_API_COMMIT}/source/presentation/3.0/index.md"
)
IIIF_SPEC_SHA256 = (
    "43d3e009418ea7601207c4a2945d3735629238c4427c3b01e81bb6e2a7b13f22"
)
IIIF_CONTEXT_SOURCE_URL = (
    "https://raw.githubusercontent.com/IIIF/api/"
    f"{IIIF_API_COMMIT}/source/presentation/3/context.json"
)
IIIF_CONTEXT_SHA256 = (
    "4bef9062347af702919b625655735a67a700f847f29f6501708c426159eda02d"
)
VALIDATOR_COMMIT = "fb5bd9039494701dc7472cdcaffe83fb5a212463"
VALIDATOR_URL = "https://github.com/IIIF/presentation-validator"
VALIDATOR_SCHEMA_URL = (
    "https://raw.githubusercontent.com/IIIF/presentation-validator/"
    f"{VALIDATOR_COMMIT}/schema/iiif_3_0.json"
)
VALIDATOR_SCHEMA_SHA256 = (
    "14dd7ee8aee25d959be4b12feddb4179c726909fc85b925f6707f4ab3bfe2ad6"
)
VALIDATOR_REQUIREMENT = (
    "iiif-presentation-validator @ "
    "git+https://github.com/IIIF/presentation-validator.git@"
    f"{VALIDATOR_COMMIT}"
)

FONT_COMMIT = "ec0464b978de222073645d6d3366f3fdf03376d8"
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/"
    f"{FONT_COMMIT}/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"
)
FONT_SHA256 = (
    "864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f"
)
FONT_BYTES = 11941968
OFL_URL = (
    "https://raw.githubusercontent.com/google/fonts/"
    f"{FONT_COMMIT}/ofl/notosanstc/OFL.txt"
)
OFL_SHA256 = (
    "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9"
)
OFL_BYTES = 4388
GLYPH_PATHS_SHA256 = (
    "ef9b2a76efe7eaa812502d3315a114255930914a5fa28c414f3584fda550b643"
)
GLYPH_PATHS_BYTES = 36202
REFERENCE_DIR = HERE / "reference_datasets" / "iiif-presentation-3"
GLYPH_PATHS_FILE = REFERENCE_DIR / "glyph-paths.json"
OFL_FILE = REFERENCE_DIR / "OFL.txt"
REFERENCE_SOURCES = REFERENCE_DIR / "sources.json"

SKOS_JSONLD_URL = f"{SITE}/data/zhuyin-bopomofo-vocabulary.jsonld"
SKOS_LANDING_URL = f"{SITE}/data/zhuyin-bopomofo-vocabulary.html"
ORG_URI = f"{SITE}/#organization"
IIIF_RIGHTS = "http://creativecommons.org/licenses/by/4.0/"

FORBIDDEN_MACHINE_MARKERS = (
    b"apps.apple.com",
    APP_ID.encode("ascii"),
    APP_NAME.encode("utf-8"),
    b"SoftwareApplication",
)

CATEGORY_NAMES = {
    "en": {
        "initial": "Initial",
        "medial": "Medial",
        "final": "Final",
    },
    "zh-Hant": {
        "initial": "聲母",
        "medial": "介音",
        "final": "韻母",
    },
}

PALETTES = {
    "initial": {
        "background": "#F7F1EC",
        "surface": "#FFFDFC",
        "accent": "#B85C4A",
        "ink": "#30283D",
        "muted": "#726878",
    },
    "medial": {
        "background": "#EDF4F5",
        "surface": "#FCFEFE",
        "accent": "#327C82",
        "ink": "#203D4B",
        "muted": "#58717A",
    },
    "final": {
        "background": "#F1F0F7",
        "surface": "#FEFDFF",
        "accent": "#6D5B9A",
        "ink": "#302D4E",
        "muted": "#6D6980",
    },
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Complete Bopomofo in IIIF Presentation API 3",
        "description": (
            "Explore and download a deterministic IIIF Presentation API 3.0 "
            "Manifest with 37 ordered Bopomofo symbol canvases and safe static SVG art."
        ),
        "eyebrow": "IIIF Presentation API 3.0 · 37 canvases · CC BY 4.0",
        "lead": (
            "A complete, app-independent visual reference for digital collections, "
            "language exhibits, classrooms and interoperable viewers."
        ),
        "back": "Open data",
        "language": "繁體中文",
        "badges": (
            "37 ordered Canvases",
            "Static SVG painting bodies",
            "Deterministic ZIP",
            "No Image API claim",
        ),
        "access": "Open the IIIF resource",
        "access_text": (
            "Start with the Collection or Manifest, inspect every source SVG, or "
            "download one reproducible archive with an external SHA-256 list."
        ),
        "collection": "IIIF Collection",
        "manifest": "IIIF Manifest",
        "bundle": "Complete deterministic ZIP",
        "checksums": "SHA-256 checksums",
        "metadata": "Independent JSON-LD metadata",
        "gallery": "All 37 Bopomofo canvases",
        "gallery_text": (
            "The canonical educational order is preserved: 21 initials, 3 medials "
            "and 13 finals. Every Canvas paints exactly one 1200 × 1200 SVG body."
        ),
        "model": "Presentation model",
        "model_items": (
            "One Collection references one Manifest without embedding a duplicate.",
            "The Manifest contains exactly 37 ordered Canvases.",
            "Each Canvas has one AnnotationPage and one painting Annotation.",
            "Every painting body is a directly addressable static SVG Image.",
        ),
        "limits": "Scope and limits",
        "limit_items": (
            "No Image API service is advertised; these SVGs are not deep-zoom tiles.",
            "The resource contains reference graphics and metadata, not audio or learner data.",
            "Checksums detect accidental byte changes but are not digital signatures.",
            "Conformance checks do not imply IIIF Consortium, Google or repository endorsement.",
        ),
        "validate": "Validate independently",
        "validate_text": (
            "Install the pinned official validator in an isolated virtual environment "
            "because its dependency constraints intentionally remain separate."
        ),
        "sources": "Pinned sources and licensing",
        "sources_text": (
            "The Presentation specification, context and validator schema are pinned "
            "by commit and SHA-256. Glyph outlines were derived once from Noto Sans TC "
            "weight 650 under the SIL Open Font License 1.1."
        ),
        "spec": "IIIF Presentation API 3.0",
        "validator": "Official validator source",
        "font": "Noto Sans TC source",
        "license": "CC BY 4.0 data license",
        "app_title": "Optional on-device practice",
        "app_text": (
            "The complete IIIF resource above is free and reusable without an app. "
            "Lumi Bopomofo is only an optional practice layer."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Open IIIF resource · No account · No API key · No deep-zoom claim"
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "完整注音符號 IIIF Presentation API 3 資源",
        "description": (
            "探索並下載 deterministic IIIF Presentation API 3.0 Manifest，"
            "內含 37 個依序排列的注音 Canvas 與安全靜態 SVG 圖卡。"
        ),
        "eyebrow": "IIIF Presentation API 3.0 · 37 個 Canvas · CC BY 4.0",
        "lead": (
            "供數位典藏、語言展示、教室與互通 viewer 使用，完整且不依賴 App 的"
            "注音視覺參考資源。"
        ),
        "back": "開放資料",
        "language": "English",
        "badges": (
            "37 個有序 Canvas",
            "靜態 SVG painting body",
            "Deterministic ZIP",
            "不宣稱 Image API",
        ),
        "access": "開啟 IIIF 資源",
        "access_text": (
            "可由 Collection 或 Manifest 開始，逐一檢視來源 SVG，或下載"
            "附有外部 SHA-256 清單的 reproducible archive。"
        ),
        "collection": "IIIF Collection",
        "manifest": "IIIF Manifest",
        "bundle": "完整 deterministic ZIP",
        "checksums": "SHA-256 checksums",
        "metadata": "獨立 JSON-LD metadata",
        "gallery": "全部 37 張注音 Canvas",
        "gallery_text": (
            "保留標準教學順序：21 個聲母、3 個介音與 13 個韻母。"
            "每個 Canvas 都只 painting 一個 1200 × 1200 SVG body。"
        ),
        "model": "Presentation 結構",
        "model_items": (
            "一個 Collection 引用一個 Manifest，不嵌入重複完整副本。",
            "Manifest 依序包含恰好 37 個 Canvas。",
            "每個 Canvas 有一個 AnnotationPage 與一個 painting Annotation。",
            "每個 painting body 都是可直接存取的靜態 SVG Image。",
        ),
        "limits": "範圍與限制",
        "limit_items": (
            "未提供 Image API service；這些 SVG 不是 deep-zoom tiles。",
            "資源只含參考圖像與 metadata，不含音訊或學習者資料。",
            "Checksum 可偵測非預期 bytes 變更，但不是數位簽章。",
            "通過格式檢查不代表 IIIF Consortium、Google 或典藏庫背書。",
        ),
        "validate": "獨立驗證",
        "validate_text": (
            "官方 validator 的 dependency constraints 與既有工具不同，"
            "因此請在隔離 virtual environment 安裝固定 commit。"
        ),
        "sources": "固定來源與授權",
        "sources_text": (
            "Presentation 規格、context 與 validator schema 均固定 commit "
            "及 SHA-256。字形 path 由 SIL Open Font License 1.1 授權的 "
            "Noto Sans TC weight 650 一次性擷取。"
        ),
        "spec": "IIIF Presentation API 3.0",
        "validator": "官方 validator 原始碼",
        "font": "Noto Sans TC 來源",
        "license": "CC BY 4.0 資料授權",
        "app_title": "選用的裝置端練習",
        "app_text": (
            "上方完整 IIIF 資源免費且不需要 App；Lumi 注音星球僅是選用的"
            "練習工具。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "開放 IIIF 資源 · 免帳號 · 免 API key · 不宣稱 deep zoom",
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _artifact(
    filename: str,
    relative_path: str,
    url: str,
    media_type: str,
    label: str,
    content: bytes,
) -> dict:
    return {
        "filename": filename,
        "path": relative_path,
        "url": url,
        "media_type": media_type,
        "label": label,
        "bytes": content,
        "sha256": _sha256(content),
    }


def image_url(symbol_id: str) -> str:
    return f"{RESOURCE_URL}/images/{symbol_id}.svg"


def canvas_id(symbol_id: str) -> str:
    return f"{RESOURCE_URL}/canvas/{symbol_id}"


def _language_map(en: str, zh_hant: str) -> dict[str, list[str]]:
    return {"en": [en], "zh-Hant": [zh_hant]}


def _metadata_item(label_en: str, label_zh: str, value_en: str, value_zh: str) -> dict:
    return {
        "label": _language_map(label_en, label_zh),
        "value": _language_map(value_en, value_zh),
    }


def _ascii_display(value: str) -> str:
    output = []
    for character in value:
        codepoint = ord(character)
        if 0x20 <= codepoint <= 0x7E:
            output.append(character)
        else:
            output.append(f" U+{codepoint:04X} ")
    return " ".join("".join(output).split())


def _format_number(value: float) -> str:
    rounded = round(value, 6)
    if rounded == 0:
        return "0"
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


def _glyph_transform(glyph: dict) -> str:
    x_min, y_min, x_max, y_max = glyph["bounds"]
    width = x_max - x_min
    height = y_max - y_min
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid glyph bounds for {glyph['symbol_id']}")
    scale = min(570 / width, 570 / height)
    target_x = 600
    target_y = 525
    translate_x = target_x - scale * ((x_min + x_max) / 2)
    translate_y = target_y + scale * ((y_min + y_max) / 2)
    return "matrix({} 0 0 -{} {} {})".format(
        _format_number(scale),
        _format_number(scale),
        _format_number(translate_x),
        _format_number(translate_y),
    )


def load_glyph_paths() -> tuple[dict, dict[str, dict]]:
    raw = GLYPH_PATHS_FILE.read_bytes()
    if len(raw) != GLYPH_PATHS_BYTES or _sha256(raw) != GLYPH_PATHS_SHA256:
        raise ValueError("Pinned Bopomofo glyph-path asset hash or size drifted")
    document = json.loads(raw)
    if document.get("format") != "bopomofo-glyph-paths-v1":
        raise ValueError("Unknown Bopomofo glyph-path format")
    if document.get("font") != {
        "family": "Noto Sans TC",
        "weight": 650,
        "unitsPerEm": 1000,
    }:
        raise ValueError("Pinned glyph font instance metadata drifted")
    rows = records()
    validate_records(rows)
    glyphs = document.get("glyphs")
    if not isinstance(glyphs, list) or len(glyphs) != 37:
        raise ValueError("Glyph-path reference must contain exactly 37 outlines")
    if [
        (glyph.get("symbol_id"), glyph.get("symbol")) for glyph in glyphs
    ] != [(row["symbol_id"], row["symbol"]) for row in rows]:
        raise ValueError("Glyph-path order or symbol coverage drifted")
    allowed_path = re.compile(r"[A-Za-z0-9., +\-]+")
    for glyph in glyphs:
        bounds = glyph.get("bounds")
        path = glyph.get("path")
        if (
            not isinstance(bounds, list)
            or len(bounds) != 4
            or not all(isinstance(value, (int, float)) for value in bounds)
            or not all(math.isfinite(value) for value in bounds)
            or not isinstance(path, str)
            or not path
            or not allowed_path.fullmatch(path)
            or "<" in path
            or ">" in path
        ):
            raise ValueError(f"Unsafe or incomplete glyph path: {glyph.get('symbol_id')}")
        _glyph_transform(glyph)
    return document, {glyph["symbol_id"]: glyph for glyph in glyphs}


def validate_reference_pins() -> None:
    source = json.loads(REFERENCE_SOURCES.read_text(encoding="utf-8"))
    iiif = source.get("iiifPresentationApi", {})
    if (
        iiif.get("commit") != IIIF_API_COMMIT
        or iiif.get("specification")
        != {
            "path": "source/presentation/3.0/index.md",
            "url": IIIF_SPEC_SOURCE_URL,
            "sha256": IIIF_SPEC_SHA256,
        }
        or iiif.get("context")
        != {
            "path": "source/presentation/3/context.json",
            "url": IIIF_CONTEXT_SOURCE_URL,
            "sha256": IIIF_CONTEXT_SHA256,
        }
    ):
        raise ValueError("IIIF Presentation source pins drifted")
    validator = source.get("officialValidator", {})
    if (
        validator.get("commit") != VALIDATOR_COMMIT
        or validator.get("schema")
        != {
            "path": "schema/iiif_3_0.json",
            "url": VALIDATOR_SCHEMA_URL,
            "sha256": VALIDATOR_SCHEMA_SHA256,
        }
        or validator.get("command")
        != "iiif-validator validate --version 3.0 <file>"
    ):
        raise ValueError("IIIF validator source pins drifted")
    glyph_source = source.get("glyphSource", {})
    if (
        glyph_source.get("commit") != FONT_COMMIT
        or glyph_source.get("font", {}).get("url") != FONT_URL
        or glyph_source.get("font", {}).get("bytes") != FONT_BYTES
        or glyph_source.get("font", {}).get("sha256") != FONT_SHA256
        or glyph_source.get("license", {}).get("url") != OFL_URL
        or glyph_source.get("license", {}).get("bytes") != OFL_BYTES
        or glyph_source.get("license", {}).get("sha256") != OFL_SHA256
        or glyph_source.get("derivedAsset", {}).get("bytes")
        != GLYPH_PATHS_BYTES
        or glyph_source.get("derivedAsset", {}).get("sha256")
        != GLYPH_PATHS_SHA256
    ):
        raise ValueError("Noto Sans TC glyph provenance pins drifted")
    ofl = OFL_FILE.read_bytes()
    if len(ofl) != OFL_BYTES or _sha256(ofl) != OFL_SHA256:
        raise ValueError("Pinned SIL OFL notice hash or size drifted")
    load_glyph_paths()


def render_svg(row: dict, glyph: dict) -> bytes:
    if glyph["symbol_id"] != row["symbol_id"] or glyph["symbol"] != row["symbol"]:
        raise ValueError("Glyph reference does not match the canonical record")
    palette = PALETTES[row["category"]]
    symbol_id = row["symbol_id"]
    title_id = f"title-{symbol_id}"
    description_id = f"description-{symbol_id}"
    title = (
        f"Bopomofo {row['symbol']} ({row['pinyin']}), "
        f"card {row['order']:02d} of 37"
    )
    description = (
        f"Static Bopomofo reference card. Unicode {row['unicode']}; "
        f"Pinyin {row['pinyin']}; IPA {row['ipa']}; category {row['category']}."
    )
    pinyin = _ascii_display(row["pinyin"])
    ipa = _ascii_display(row["ipa"])
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200" role="img" aria-labelledby="{title_id} {description_id}">
  <title id="{title_id}">{html.escape(title)}</title>
  <desc id="{description_id}">{html.escape(description)}</desc>
  <rect width="1200" height="1200" fill="{palette['background']}"/>
  <rect x="30" y="30" width="1140" height="1140" rx="72" fill="{palette['surface']}" stroke="{palette['accent']}" stroke-width="4"/>
  <rect x="96" y="78" width="1008" height="12" rx="6" fill="{palette['accent']}"/>
  <circle cx="600" cy="525" r="382" fill="{palette['background']}"/>
  <circle cx="600" cy="525" r="346" fill="none" stroke="{palette['accent']}" stroke-width="3" opacity="0.42"/>
  <path d="{glyph['path']}" transform="{_glyph_transform(glyph)}" fill="{palette['ink']}"/>
  <text x="600" y="142" text-anchor="middle" fill="{palette['accent']}" font-size="38" font-weight="700" letter-spacing="8">{row['category'].upper()}</text>
  <text x="600" y="948" text-anchor="middle" fill="{palette['ink']}" font-size="34" font-weight="700" letter-spacing="3">CARD {row['order']:02d} / 37 | {row['unicode']}</text>
  <text x="600" y="1012" text-anchor="middle" fill="{palette['muted']}" font-size="30" font-weight="600">PINYIN {html.escape(pinyin)} | IPA {html.escape(ipa)}</text>
  <text x="600" y="1094" text-anchor="middle" fill="{palette['accent']}" font-size="24" font-weight="700" letter-spacing="4">BOPOMOFO OPEN REFERENCE</text>
</svg>
"""
    raw = content.encode("utf-8")
    validate_svg(raw, row, glyph)
    return raw


def validate_svg(content: bytes, row: dict, glyph: dict) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("SVG is not UTF-8") from error
    lowered = text.lower()
    for forbidden in (
        "<script",
        "foreignobject",
        "<!doctype",
        "<!entity",
        "javascript:",
        "data:",
        "url(",
        "@font",
        "font-family",
        "href=",
        "xlink:",
        "apps.apple.com",
        APP_ID,
        APP_NAME.lower(),
    ):
        if forbidden in lowered:
            raise ValueError(f"Unsafe external or executable SVG content: {forbidden}")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError("SVG is not well-formed XML") from error
    namespace = "{http://www.w3.org/2000/svg}"
    if (
        root.tag != f"{namespace}svg"
        or root.get("width") != str(CARD_SIZE)
        or root.get("height") != str(CARD_SIZE)
        or root.get("viewBox") != "0 0 1200 1200"
        or root.get("role") != "img"
    ):
        raise ValueError("SVG root identity or dimensions drifted")
    allowed_tags = {
        f"{namespace}svg",
        f"{namespace}title",
        f"{namespace}desc",
        f"{namespace}rect",
        f"{namespace}circle",
        f"{namespace}path",
        f"{namespace}text",
    }
    allowed_attributes = {
        "aria-labelledby",
        "cx",
        "cy",
        "d",
        "fill",
        "font-size",
        "font-weight",
        "height",
        "id",
        "letter-spacing",
        "opacity",
        "r",
        "role",
        "rx",
        "stroke",
        "stroke-width",
        "text-anchor",
        "transform",
        "viewBox",
        "width",
        "x",
        "y",
    }
    for element in root.iter():
        if element.tag not in allowed_tags:
            raise ValueError(f"Unexpected SVG element: {element.tag}")
        for attribute in element.attrib:
            local = attribute.rsplit("}", 1)[-1]
            if (
                local not in allowed_attributes
                or local.lower().startswith("on")
                or local.lower() in {"href", "src"}
            ):
                raise ValueError(f"Unsafe SVG attribute: {attribute}")
    titles = root.findall(f"{namespace}title")
    paths = root.findall(f"{namespace}path")
    if len(titles) != 1 or row["symbol"] not in (titles[0].text or ""):
        raise ValueError("SVG accessible title is missing its Bopomofo symbol")
    if (
        len(paths) != 1
        or paths[0].get("d") != glyph["path"]
        or paths[0].get("transform") != _glyph_transform(glyph)
    ):
        raise ValueError("SVG glyph path or centered transform drifted")
    for element in root.findall(f"{namespace}text"):
        if not (element.text or "").isascii():
            raise ValueError("Rendered SVG metadata text must remain safe ASCII")


def _canvas(row: dict) -> dict:
    identifier = canvas_id(row["symbol_id"])
    page_id = f"{identifier}/page"
    annotation_id = f"{identifier}/annotation"
    category_en = CATEGORY_NAMES["en"][row["category"]]
    category_zh = CATEGORY_NAMES["zh-Hant"][row["category"]]
    example_en = (
        f"{row['example_character']} ({row['example_pinyin']}): "
        f"{row['example_meaning_en']}"
    )
    example_zh = f"{row['example_character']}（{row['example_pinyin']}）"
    return {
        "id": identifier,
        "type": "Canvas",
        "label": _language_map(
            f"{row['order']:02d}. Bopomofo {row['symbol']} ({row['pinyin']})",
            f"{row['order']:02d}. 注音符號 {row['symbol']}（{row['pinyin']}）",
        ),
        "metadata": [
            _metadata_item("Symbol", "符號", row["symbol"], row["symbol"]),
            _metadata_item("Unicode", "Unicode", row["unicode"], row["unicode"]),
            _metadata_item("Pinyin", "漢語拼音", row["pinyin"], row["pinyin"]),
            _metadata_item("IPA", "國際音標", row["ipa"], row["ipa"]),
            _metadata_item("Category", "分類", category_en, category_zh),
            _metadata_item("Example", "例字", example_en, example_zh),
        ],
        "height": CARD_SIZE,
        "width": CARD_SIZE,
        "items": [
            {
                "id": page_id,
                "type": "AnnotationPage",
                "items": [
                    {
                        "id": annotation_id,
                        "type": "Annotation",
                        "motivation": "painting",
                        "body": {
                            "id": image_url(row["symbol_id"]),
                            "type": "Image",
                            "format": "image/svg+xml",
                            "height": CARD_SIZE,
                            "width": CARD_SIZE,
                        },
                        "target": identifier,
                    }
                ],
            }
        ],
    }


def make_manifest(rows: list[dict]) -> dict:
    validate_records(rows)
    label = _language_map(
        "Complete Bopomofo: 37 Zhuyin symbol cards",
        "完整注音：37 張注音符號圖卡",
    )
    summary = _language_map(
        "An ordered, app-independent IIIF Presentation resource for every standard Bopomofo symbol.",
        "依標準教學順序收錄全部注音符號，且不依賴 App 的 IIIF Presentation 資源。",
    )
    return {
        "@context": IIIF_CONTEXT,
        "id": MANIFEST_URL,
        "type": "Manifest",
        "label": label,
        "summary": summary,
        "metadata": [
            _metadata_item(
                "Coverage",
                "涵蓋範圍",
                "37 standard Bopomofo symbols",
                "37 個標準注音符號",
            ),
            _metadata_item(
                "Canonical order",
                "標準順序",
                "21 initials, 3 medials, 13 finals",
                "21 個聲母、3 個介音、13 個韻母",
            ),
            _metadata_item(
                "Image model",
                "影像模式",
                "Static 1200 × 1200 SVG painting bodies; no Image API service",
                "靜態 1200 × 1200 SVG painting body；未提供 Image API service",
            ),
        ],
        "rights": IIIF_RIGHTS,
        "requiredStatement": {
            "label": _language_map("Attribution", "標示"),
            "value": _language_map(
                "Lumi Apps – iOS App Guide, Complete Bopomofo Open Reference",
                "Lumi Apps – iOS App Guide，完整注音開放參考資料",
            ),
        },
        "provider": [
            {
                "id": ORG_URI,
                "type": "Agent",
                "label": _language_map(
                    "Lumi Apps – iOS App Guide",
                    "Lumi Apps – iOS App Guide",
                ),
                "homepage": [
                    {
                        "id": SITE,
                        "type": "Text",
                        "label": _language_map(
                            "iOS App Guide open resources",
                            "iOS App Guide 開放資源",
                        ),
                        "format": "text/html",
                    }
                ],
            }
        ],
        "homepage": [
            {
                "id": LANDING_URL,
                "type": "Text",
                "label": _language_map(
                    "English resource guide",
                    "英文資源說明",
                ),
                "format": "text/html",
                "language": ["en"],
            },
            {
                "id": ZH_LANDING_URL,
                "type": "Text",
                "label": _language_map(
                    "Traditional Chinese resource guide",
                    "繁體中文資源說明",
                ),
                "format": "text/html",
                "language": ["zh-Hant"],
            },
        ],
        "seeAlso": [
            {
                "id": CSV_URL,
                "type": "Dataset",
                "label": _language_map(
                    "Canonical 37-row CSV",
                    "標準 37 列 CSV",
                ),
                "format": "text/csv",
            },
            {
                "id": CROISSANT_METADATA_URL,
                "type": "Dataset",
                "label": _language_map(
                    "MLCommons Croissant metadata",
                    "MLCommons Croissant metadata",
                ),
                "format": "application/ld+json",
            },
            {
                "id": SKOS_JSONLD_URL,
                "type": "Dataset",
                "label": _language_map(
                    "SKOS Bopomofo vocabulary",
                    "SKOS 注音詞彙表",
                ),
                "format": "application/ld+json",
            },
        ],
        "rendering": [
            {
                "id": BUNDLE_URL,
                "type": "Dataset",
                "label": _language_map(
                    "Download the complete deterministic ZIP",
                    "下載完整 deterministic ZIP",
                ),
                "format": "application/zip",
            }
        ],
        "thumbnail": [
            {
                "id": image_url(rows[0]["symbol_id"]),
                "type": "Image",
                "format": "image/svg+xml",
                "height": CARD_SIZE,
                "width": CARD_SIZE,
            }
        ],
        "navDate": NAV_DATE,
        "items": [_canvas(row) for row in rows],
    }


def make_collection(rows: list[dict]) -> dict:
    validate_records(rows)
    return {
        "@context": IIIF_CONTEXT,
        "id": COLLECTION_URL,
        "type": "Collection",
        "label": _language_map(
            "Complete Bopomofo IIIF Collection",
            "完整注音 IIIF Collection",
        ),
        "summary": _language_map(
            "A single-manifest collection of 37 ordered Bopomofo symbol cards.",
            "以單一 Manifest 收錄 37 張有序注音符號圖卡。",
        ),
        "requiredStatement": {
            "label": _language_map("Attribution", "標示"),
            "value": _language_map(
                "Lumi Apps – iOS App Guide, Complete Bopomofo Open Reference",
                "Lumi Apps – iOS App Guide，完整注音開放參考資料",
            ),
        },
        "rights": IIIF_RIGHTS,
        "items": [
            {
                "id": MANIFEST_URL,
                "type": "Manifest",
                "label": _language_map(
                    "Complete Bopomofo: 37 Zhuyin symbol cards",
                    "完整注音：37 張注音符號圖卡",
                ),
                "thumbnail": [
                    {
                        "id": image_url(rows[0]["symbol_id"]),
                        "type": "Image",
                        "format": "image/svg+xml",
                        "height": CARD_SIZE,
                        "width": CARD_SIZE,
                    }
                ],
            }
        ],
    }


def _zip_bytes(members: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative_path, content in members:
            info = zipfile.ZipInfo(f"{ZIP_ROOT}/{relative_path}", ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return buffer.getvalue()


def _checksum_bytes(artifacts: list[dict]) -> bytes:
    return "".join(
        f"{artifact['sha256']}  {artifact['path']}\n" for artifact in artifacts
    ).encode("ascii")


def _distribution(artifact: dict) -> dict:
    return {
        "@type": "DataDownload",
        "contentSize": f"{len(artifact['bytes'])} B",
        "contentUrl": artifact["url"],
        "encodingFormat": artifact["media_type"],
        "name": artifact["label"],
        "sha256": artifact["sha256"],
    }


def make_metadata(
    collection: dict,
    manifest: dict,
    images: dict[str, dict],
    bundle: dict,
    checksums: dict,
) -> dict:
    return {
        "@context": "https://schema.org",
        "@id": f"{METADATA_URL}#dataset",
        "@type": "Dataset",
        "name": "Complete Bopomofo IIIF Presentation API 3 resource",
        "alternateName": "完整注音 IIIF Presentation API 3 資源",
        "description": COPY["en"]["description"],
        "datePublished": INITIAL_DATE,
        "dateModified": NAV_DATE,
        "version": VERSION,
        "identifier": MANIFEST_URL,
        "url": LANDING_URL,
        "conformsTo": IIIF_SPEC_URL,
        "license": LICENSE,
        "isAccessibleForFree": True,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "numberOfItems": 37,
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps – iOS App Guide",
            "url": SITE,
        },
        "citation": [
            CSV_URL,
            CROISSANT_METADATA_URL,
            SKOS_JSONLD_URL,
        ],
        "measurementTechnique": (
            "IIIF Presentation API 3.0 with one static SVG painting body per Canvas; "
            "no IIIF Image API service"
        ),
        "distribution": [
            _distribution(collection),
            _distribution(manifest),
            _distribution(bundle),
            _distribution(checksums),
        ],
        "hasPart": [
            {
                "@type": "ImageObject",
                "contentSize": f"{len(artifact['bytes'])} B",
                "contentUrl": artifact["url"],
                "encodingFormat": artifact["media_type"],
                "identifier": symbol_id,
                "name": artifact["label"],
                "sha256": artifact["sha256"],
                "height": CARD_SIZE,
                "width": CARD_SIZE,
            }
            for symbol_id, artifact in images.items()
        ],
        "usageInfo": (
            "The checksum list covers collection.json, manifest.json, all 37 SVG "
            "files and the ZIP. It deliberately excludes itself and this metadata "
            "document to avoid recursive hashes."
        ),
    }


def make_artifacts(rows: list[dict] | None = None) -> dict[str, dict]:
    rows = records() if rows is None else rows
    validate_records(rows)
    validate_reference_pins()
    _glyph_document, glyphs = load_glyph_paths()
    images = {}
    for row in rows:
        relative_path = f"images/{row['symbol_id']}.svg"
        content = render_svg(row, glyphs[row["symbol_id"]])
        images[row["symbol_id"]] = _artifact(
            f"{row['symbol_id']}.svg",
            relative_path,
            image_url(row["symbol_id"]),
            "image/svg+xml",
            f"Bopomofo {row['symbol']} static SVG card",
            content,
        )

    manifest_document = make_manifest(rows)
    manifest = _artifact(
        MANIFEST_FILENAME,
        MANIFEST_FILENAME,
        MANIFEST_URL,
        "application/json",
        "IIIF Presentation API 3.0 Manifest",
        _json_bytes(manifest_document),
    )
    collection_document = make_collection(rows)
    collection = _artifact(
        COLLECTION_FILENAME,
        COLLECTION_FILENAME,
        COLLECTION_URL,
        "application/json",
        "IIIF Presentation API 3 Collection",
        _json_bytes(collection_document),
    )

    zip_members = [
        (COLLECTION_FILENAME, collection["bytes"]),
        (MANIFEST_FILENAME, manifest["bytes"]),
        *[
            (artifact["path"], artifact["bytes"])
            for artifact in images.values()
        ],
        ("reference/OFL.txt", OFL_FILE.read_bytes()),
        ("reference/sources.json", REFERENCE_SOURCES.read_bytes()),
    ]
    bundle = _artifact(
        BUNDLE_FILENAME,
        BUNDLE_FILENAME,
        BUNDLE_URL,
        "application/zip",
        "Deterministic complete IIIF resource ZIP",
        _zip_bytes(zip_members),
    )
    checksum_members = [
        collection,
        manifest,
        *images.values(),
        bundle,
    ]
    checksums = _artifact(
        CHECKSUM_FILENAME,
        CHECKSUM_FILENAME,
        CHECKSUM_URL,
        "text/plain",
        "SHA-256 checksums for non-recursive IIIF payload files",
        _checksum_bytes(checksum_members),
    )
    metadata_document = make_metadata(
        collection,
        manifest,
        images,
        bundle,
        checksums,
    )
    metadata = _artifact(
        METADATA_FILENAME,
        METADATA_FILENAME,
        METADATA_URL,
        "application/ld+json",
        "App-independent Schema.org resource metadata",
        _json_bytes(metadata_document),
    )
    artifacts = {
        "collection": collection,
        "manifest": manifest,
        "images": images,
        "bundle": bundle,
        "checksums": checksums,
        "metadata": metadata,
        "_rows": rows,
        "_zip_members": zip_members,
        "_checksum_members": checksum_members,
    }
    validate_artifacts(artifacts)
    return artifacts


def _validate_language_map(value: object, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"en", "zh-Hant"}:
        raise ValueError(f"{label} must be an English and Traditional Chinese language map")
    for language, entries in value.items():
        if (
            not isinstance(entries, list)
            or not entries
            or any(not isinstance(entry, str) or not entry for entry in entries)
        ):
            raise ValueError(f"{label} has an invalid {language} language list")


def _validate_https(identifier: object, label: str) -> None:
    if not isinstance(identifier, str):
        raise ValueError(f"{label} must be a string")
    parsed = urlparse(identifier)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute HTTPS identifier")


def _walk(value: object):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _validate_common_iiif(document: dict, expected_type: str, expected_id: str) -> None:
    if (
        document.get("@context") != IIIF_CONTEXT
        or not isinstance(document.get("@context"), str)
        or document.get("type") != expected_type
        or document.get("id") != expected_id
    ):
        raise ValueError(f"IIIF {expected_type} context, type or id drifted")
    _validate_https(document["id"], f"{expected_type} id")
    _validate_language_map(document.get("label"), f"{expected_type} label")
    _validate_language_map(document.get("summary"), f"{expected_type} summary")
    required = document.get("requiredStatement")
    if not isinstance(required, dict):
        raise ValueError(f"IIIF {expected_type} requiredStatement is missing")
    _validate_language_map(required.get("label"), "requiredStatement label")
    _validate_language_map(required.get("value"), "requiredStatement value")
    if document.get("rights") != IIIF_RIGHTS:
        raise ValueError(f"IIIF {expected_type} rights URI drifted")
    for node in _walk(document):
        if isinstance(node, dict):
            if "service" in node:
                raise ValueError("IIIF resource must not advertise an Image API service")
            if "id" in node:
                _validate_https(node["id"], f"{expected_type} nested id")
    raw = _json_bytes(document)
    _validate_machine_bytes(raw, f"IIIF {expected_type}")


def validate_manifest(document: dict, rows: list[dict] | None = None) -> None:
    rows = records() if rows is None else rows
    validate_records(rows)
    _validate_common_iiif(document, "Manifest", MANIFEST_URL)
    if document.get("navDate") != NAV_DATE:
        raise ValueError("IIIF Manifest navDate drifted")
    try:
        parsed_nav_date = dt.datetime.fromisoformat(
            document["navDate"].replace("Z", "+00:00")
        )
    except (TypeError, ValueError) as error:
        raise ValueError("IIIF Manifest navDate is not RFC 3339") from error
    if parsed_nav_date.tzinfo is None:
        raise ValueError("IIIF Manifest navDate must include a timezone")

    metadata = document.get("metadata")
    if not isinstance(metadata, list) or not metadata:
        raise ValueError("IIIF Manifest metadata is missing")
    for index, entry in enumerate(metadata):
        if not isinstance(entry, dict):
            raise ValueError("IIIF Manifest metadata entry is not an object")
        _validate_language_map(entry.get("label"), f"Manifest metadata {index} label")
        _validate_language_map(entry.get("value"), f"Manifest metadata {index} value")

    providers = document.get("provider")
    if (
        not isinstance(providers, list)
        or len(providers) != 1
        or providers[0].get("type") != "Agent"
        or providers[0].get("id") != ORG_URI
    ):
        raise ValueError("IIIF Manifest provider drifted")
    _validate_language_map(providers[0].get("label"), "provider label")
    if not providers[0].get("homepage"):
        raise ValueError("IIIF Manifest provider homepage is missing")

    homepage = document.get("homepage")
    if (
        not isinstance(homepage, list)
        or [entry.get("id") for entry in homepage]
        != [LANDING_URL, ZH_LANDING_URL]
    ):
        raise ValueError("IIIF Manifest bilingual homepages drifted")
    for entry in homepage:
        _validate_language_map(entry.get("label"), "homepage label")

    expected_see_also = [
        (CSV_URL, "text/csv"),
        (CROISSANT_METADATA_URL, "application/ld+json"),
        (SKOS_JSONLD_URL, "application/ld+json"),
    ]
    see_also = document.get("seeAlso")
    if (
        not isinstance(see_also, list)
        or [(entry.get("id"), entry.get("format")) for entry in see_also]
        != expected_see_also
    ):
        raise ValueError("IIIF Manifest seeAlso resources drifted")
    for entry in see_also:
        _validate_language_map(entry.get("label"), "seeAlso label")

    rendering = document.get("rendering")
    if (
        not isinstance(rendering, list)
        or len(rendering) != 1
        or rendering[0].get("id") != BUNDLE_URL
        or rendering[0].get("format") != "application/zip"
    ):
        raise ValueError("IIIF Manifest deterministic ZIP rendering drifted")
    _validate_language_map(rendering[0].get("label"), "rendering label")

    thumbnails = document.get("thumbnail")
    if (
        not isinstance(thumbnails, list)
        or len(thumbnails) != 1
        or thumbnails[0].get("id") != image_url(rows[0]["symbol_id"])
        or thumbnails[0].get("type") != "Image"
        or thumbnails[0].get("format") != "image/svg+xml"
        or thumbnails[0].get("height") != CARD_SIZE
        or thumbnails[0].get("width") != CARD_SIZE
    ):
        raise ValueError("IIIF Manifest thumbnail drifted")

    canvases = document.get("items")
    if not isinstance(canvases, list) or len(canvases) != 37:
        raise ValueError("IIIF Manifest must contain exactly 37 Canvases")
    for row, canvas in zip(rows, canvases, strict=True):
        expected_canvas_id = canvas_id(row["symbol_id"])
        if (
            canvas.get("id") != expected_canvas_id
            or canvas.get("type") != "Canvas"
            or canvas.get("height") != CARD_SIZE
            or canvas.get("width") != CARD_SIZE
        ):
            raise ValueError(f"IIIF Canvas identity drifted: {row['symbol_id']}")
        _validate_language_map(canvas.get("label"), "Canvas label")
        canvas_metadata = canvas.get("metadata")
        if not isinstance(canvas_metadata, list) or len(canvas_metadata) != 6:
            raise ValueError(f"IIIF Canvas metadata drifted: {row['symbol_id']}")
        for entry in canvas_metadata:
            _validate_language_map(entry.get("label"), "Canvas metadata label")
            _validate_language_map(entry.get("value"), "Canvas metadata value")
        pages = canvas.get("items")
        if (
            not isinstance(pages, list)
            or len(pages) != 1
            or pages[0].get("id") != f"{expected_canvas_id}/page"
            or pages[0].get("type") != "AnnotationPage"
        ):
            raise ValueError(f"IIIF AnnotationPage drifted: {row['symbol_id']}")
        annotations = pages[0].get("items")
        if not isinstance(annotations, list) or len(annotations) != 1:
            raise ValueError(f"IIIF painting Annotation drifted: {row['symbol_id']}")
        annotation = annotations[0]
        body = annotation.get("body")
        if (
            annotation.get("id") != f"{expected_canvas_id}/annotation"
            or annotation.get("type") != "Annotation"
            or annotation.get("motivation") != "painting"
            or annotation.get("target") != expected_canvas_id
            or not isinstance(body, dict)
            or body.get("id") != image_url(row["symbol_id"])
            or body.get("type") != "Image"
            or body.get("format") != "image/svg+xml"
            or body.get("height") != CARD_SIZE
            or body.get("width") != CARD_SIZE
            or "service" in body
        ):
            raise ValueError(f"IIIF painting graph drifted: {row['symbol_id']}")


def validate_collection(document: dict, rows: list[dict] | None = None) -> None:
    rows = records() if rows is None else rows
    validate_records(rows)
    _validate_common_iiif(document, "Collection", COLLECTION_URL)
    items = document.get("items")
    if (
        not isinstance(items, list)
        or len(items) != 1
        or items[0].get("id") != MANIFEST_URL
        or items[0].get("type") != "Manifest"
    ):
        raise ValueError("IIIF Collection must reference the single Manifest")
    if "items" in items[0]:
        raise ValueError("IIIF Collection must not embed a second Manifest copy")
    _validate_language_map(items[0].get("label"), "Collection Manifest label")
    thumbnail = items[0].get("thumbnail")
    if (
        not isinstance(thumbnail, list)
        or len(thumbnail) != 1
        or thumbnail[0].get("id") != image_url(rows[0]["symbol_id"])
    ):
        raise ValueError("IIIF Collection Manifest thumbnail drifted")


def _validate_machine_bytes(content: bytes, label: str) -> None:
    lowered = content.lower()
    for marker in FORBIDDEN_MACHINE_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"App promotion leaked into {label}")


def _expected_zip_members(artifacts: dict[str, dict]) -> list[tuple[str, bytes]]:
    return [
        (COLLECTION_FILENAME, artifacts["collection"]["bytes"]),
        (MANIFEST_FILENAME, artifacts["manifest"]["bytes"]),
        *[
            (artifact["path"], artifact["bytes"])
            for artifact in artifacts["images"].values()
        ],
        ("reference/OFL.txt", OFL_FILE.read_bytes()),
        ("reference/sources.json", REFERENCE_SOURCES.read_bytes()),
    ]


def validate_artifacts(artifacts: dict[str, dict]) -> None:
    validate_reference_pins()
    rows = artifacts["_rows"]
    validate_records(rows)
    if list(artifacts["images"]) != [row["symbol_id"] for row in rows]:
        raise ValueError("IIIF image artifact order drifted from canonical records")
    manifest_document = json.loads(artifacts["manifest"]["bytes"])
    collection_document = json.loads(artifacts["collection"]["bytes"])
    validate_manifest(manifest_document, rows)
    validate_collection(collection_document, rows)
    _glyph_document, glyphs = load_glyph_paths()
    for row in rows:
        artifact = artifacts["images"][row["symbol_id"]]
        if (
            artifact["path"] != f"images/{row['symbol_id']}.svg"
            or artifact["url"] != image_url(row["symbol_id"])
            or artifact["sha256"] != _sha256(artifact["bytes"])
        ):
            raise ValueError(f"IIIF SVG artifact metadata drifted: {row['symbol_id']}")
        validate_svg(artifact["bytes"], row, glyphs[row["symbol_id"]])

    expected_zip_members = _expected_zip_members(artifacts)
    expected_zip_names = [
        f"{ZIP_ROOT}/{relative_path}" for relative_path, _content in expected_zip_members
    ]
    with zipfile.ZipFile(io.BytesIO(artifacts["bundle"]["bytes"])) as archive:
        if archive.namelist() != expected_zip_names:
            raise ValueError("IIIF ZIP membership or canonical order drifted")
        for relative_path, expected_content in expected_zip_members:
            name = f"{ZIP_ROOT}/{relative_path}"
            if archive.read(name) != expected_content:
                raise ValueError(f"IIIF ZIP member bytes drifted: {relative_path}")
            info = archive.getinfo(name)
            if (
                info.date_time != ZIP_TIMESTAMP
                or info.compress_type != zipfile.ZIP_STORED
                or info.create_system != 3
                or ((info.external_attr >> 16) & 0o777) != 0o644
            ):
                raise ValueError(f"IIIF ZIP metadata is not deterministic: {relative_path}")
    if artifacts["bundle"]["sha256"] != _sha256(artifacts["bundle"]["bytes"]):
        raise ValueError("IIIF ZIP SHA-256 drifted")

    expected_checksum_members = [
        artifacts["collection"],
        artifacts["manifest"],
        *artifacts["images"].values(),
        artifacts["bundle"],
    ]
    expected_checksums = _checksum_bytes(expected_checksum_members)
    if artifacts["checksums"]["bytes"] != expected_checksums:
        raise ValueError("IIIF checksum list drifted from exact payload bytes")
    checksum_paths = [
        line.split("  ", 1)[1]
        for line in expected_checksums.decode("ascii").splitlines()
    ]
    if (
        len(checksum_paths) != 40
        or len(checksum_paths) != len(set(checksum_paths))
        or CHECKSUM_FILENAME in checksum_paths
        or METADATA_FILENAME in checksum_paths
    ):
        raise ValueError("IIIF checksum list must be exact and non-recursive")

    metadata = json.loads(artifacts["metadata"]["bytes"])
    if (
        metadata.get("@type") != "Dataset"
        or metadata.get("identifier") != MANIFEST_URL
        or metadata.get("conformsTo") != IIIF_SPEC_URL
        or metadata.get("numberOfItems") != 37
        or metadata.get("datePublished") != INITIAL_DATE
        or metadata.get("dateModified") != NAV_DATE
    ):
        raise ValueError("IIIF app-independent metadata identity drifted")
    distributions = {
        item["contentUrl"]: item for item in metadata.get("distribution", [])
    }
    for artifact in (
        artifacts["collection"],
        artifacts["manifest"],
        artifacts["bundle"],
        artifacts["checksums"],
    ):
        item = distributions.get(artifact["url"])
        if (
            item is None
            or item.get("sha256") != artifact["sha256"]
            or item.get("contentSize") != f"{len(artifact['bytes'])} B"
            or item.get("encodingFormat") != artifact["media_type"]
        ):
            raise ValueError(f"IIIF metadata distribution drifted: {artifact['path']}")
    image_parts = {
        item["identifier"]: item for item in metadata.get("hasPart", [])
    }
    if set(image_parts) != set(artifacts["images"]):
        raise ValueError("IIIF metadata must describe all 37 SVG images")
    for symbol_id, artifact in artifacts["images"].items():
        item = image_parts[symbol_id]
        if (
            item.get("contentUrl") != artifact["url"]
            or item.get("sha256") != artifact["sha256"]
            or item.get("contentSize") != f"{len(artifact['bytes'])} B"
            or item.get("height") != CARD_SIZE
            or item.get("width") != CARD_SIZE
        ):
            raise ValueError(f"IIIF image metadata drifted: {symbol_id}")

    machine_artifacts = [
        artifacts["collection"],
        artifacts["manifest"],
        *artifacts["images"].values(),
        artifacts["bundle"],
        artifacts["checksums"],
        artifacts["metadata"],
    ]
    for artifact in machine_artifacts:
        _validate_machine_bytes(artifact["bytes"], artifact["path"])


def _write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def _output_paths(pages: Path, artifacts: dict[str, dict]) -> list[tuple[Path, dict]]:
    resource = pages / RESOURCE_PATH
    return [
        (resource / COLLECTION_FILENAME, artifacts["collection"]),
        (resource / MANIFEST_FILENAME, artifacts["manifest"]),
        *[
            (resource / artifact["path"], artifact)
            for artifact in artifacts["images"].values()
        ],
        (resource / BUNDLE_FILENAME, artifacts["bundle"]),
        (resource / CHECKSUM_FILENAME, artifacts["checksums"]),
        (resource / METADATA_FILENAME, artifacts["metadata"]),
    ]


def write_artifacts(pages: Path) -> dict[str, dict]:
    artifacts = make_artifacts()
    for path, artifact in _output_paths(pages, artifacts):
        _write_bytes_if_changed(path, artifact["bytes"])
    return artifacts


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def page_url(locale: str) -> str:
    return LANDING_URL if locale == "en" else ZH_LANDING_URL


def _page_schema(
    locale: str,
    artifacts: dict[str, dict],
    app_public: bool,
    modified: str,
) -> dict:
    dataset = {
        "@type": "Dataset",
        "@id": f"{METADATA_URL}#dataset",
        "name": COPY[locale]["title"],
        "description": COPY[locale]["description"],
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "conformsTo": IIIF_SPEC_URL,
        "license": LICENSE,
        "isAccessibleForFree": True,
        "numberOfItems": 37,
        "url": page_url(locale),
        "distribution": [
            _distribution(artifacts[key])
            for key in ("collection", "manifest", "bundle", "checksums", "metadata")
        ],
    }
    graph = [dataset]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "applicationCategory": "EducationApplication",
                "name": APP_NAME,
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_iiif_{locale.lower()}"),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(locale: str, artifacts: dict[str, dict]) -> str:
    labels = {
        "collection": COPY[locale]["collection"],
        "manifest": COPY[locale]["manifest"],
        "bundle": COPY[locale]["bundle"],
        "checksums": COPY[locale]["checksums"],
        "metadata": COPY[locale]["metadata"],
    }
    return "".join(
        '<a class="download" href="{url}"><strong>{label}</strong>'
        "<span>{filename}</span></a>".format(
            url=html.escape(artifacts[key]["url"], quote=True),
            label=html.escape(labels[key]),
            filename=html.escape(artifacts[key]["filename"]),
        )
        for key in ("collection", "manifest", "bundle", "checksums", "metadata")
    )


def _gallery(locale: str, rows: list[dict]) -> str:
    return "".join(
        '<a class="symbol" href="{url}"><img src="{url}" width="1200" height="1200" '
        'loading="lazy" alt="{alt}"><span>{order:02d} · {symbol} · {pinyin}</span></a>'.format(
            url=html.escape(image_url(row["symbol_id"]), quote=True),
            alt=html.escape(
                (
                    f"Bopomofo {row['symbol']} ({row['pinyin']})"
                    if locale == "en"
                    else f"注音符號 {row['symbol']}（{row['pinyin']}）"
                ),
                quote=True,
            ),
            order=row["order"],
            symbol=html.escape(row["symbol"]),
            pinyin=html.escape(row["pinyin"]),
        )
        for row in rows
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
    model_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["model_items"]
    )
    limit_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["limit_items"]
    )
    app_section = ""
    if app_public:
        app_section = (
            '<section id="optional-app" class="wrap panel app">'
            "<h2>{title}</h2><p>{text}</p>"
            '<a class="button" href="{url}" rel="nofollow noopener">{cta}</a>'
            "</section>"
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(APP_KEY, f"iag_iiif_{locale.lower()}"),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _page_schema(locale, artifacts, app_public, modified),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    command = (
        "python3 -m venv .venv-iiif\n"
        f'.venv-iiif/bin/pip install "{VALIDATOR_REQUIREMENT}"\n'
        f".venv-iiif/bin/iiif-validator validate --version 3.0 {MANIFEST_FILENAME}\n"
        f".venv-iiif/bin/iiif-validator validate --version 3.0 {COLLECTION_FILENAME}"
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
<link rel="alternate" hreflang="en" href="{LANDING_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_LANDING_URL}">
<link rel="alternate" hreflang="x-default" href="{LANDING_URL}">
<link rel="alternate" type="application/json" href="{MANIFEST_URL}">
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#28263c;--sub:#656476;--line:#dedce8;--paper:#fff;--wash:#f4f1f7;--brand:#6d5b9a;--soft:#f0edf7;--code:#171522}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1120px;margin:auto;padding-left:20px;padding-right:20px}}.top{{background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}}.nav{{min-height:60px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:800;text-decoration:none;white-space:nowrap}}.hero{{padding-top:68px;padding-bottom:38px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;overflow-x:auto}}h1{{font-size:clamp(32px,6vw,60px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:1020px}}h2{{font-size:clamp(23px,4vw,32px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub)}}.lead{{font-size:clamp(17px,3vw,21px);max-width:880px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:7px 13px;font-size:13px;font-weight:760;white-space:nowrap}}main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:24px;padding:clamp(20px,4vw,32px);box-shadow:0 16px 40px rgba(45,38,72,.07)}}.downloads{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:4px;border:1px solid var(--line);border-radius:16px;padding:17px;text-decoration:none;background:var(--soft);min-width:0}}.download strong{{font-size:15px}}.download span{{color:var(--sub);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.gallery{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin-top:22px}}.symbol{{background:var(--soft);border:1px solid var(--line);border-radius:18px;padding:8px;text-decoration:none;min-width:0}}.symbol img{{display:block;width:100%;height:auto;border-radius:12px;background:#fff}}.symbol span{{display:block;padding:8px 4px 3px;text-align:center;color:var(--ink);font-size:13px;font-weight:780;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}ul{{padding-left:24px}}li{{margin:8px 0;color:var(--sub)}}pre{{background:var(--code);color:#eeeaf8;border-radius:16px;padding:18px;overflow:auto;font:12px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:720;white-space:nowrap}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:820;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#f0edf7)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:900px){{.downloads{{grid-template-columns:repeat(2,minmax(0,1fr))}}.gallery{{grid-template-columns:repeat(4,minmax(0,1fr))}}}}
@media(max-width:680px){{.two{{grid-template-columns:1fr}}.gallery{{grid-template-columns:repeat(3,minmax(0,1fr))}}.hero{{padding-top:44px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{DATA_CATALOG}">{html.escape(copy['back'])}</a><a href="{html.escape(page_url(other), quote=True)}">{html.escape(copy['language'])}</a></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['access'])}</h2><p>{html.escape(copy['access_text'])}</p><div class="downloads">{_download_cards(locale, artifacts)}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['gallery'])}</h2><p>{html.escape(copy['gallery_text'])}</p><div class="gallery">{_gallery(locale, artifacts['_rows'])}</div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['model'])}</h2><ul>{model_items}</ul></article><article class="panel"><h2>{html.escape(copy['limits'])}</h2><ul>{limit_items}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['validate'])}</h2><p>{html.escape(copy['validate_text'])}</p><pre>{html.escape(command)}</pre></section>
<section class="wrap panel"><h2>{html.escape(copy['sources'])}</h2><p>{html.escape(copy['sources_text'])}</p><div class="sources"><a href="{IIIF_SPEC_URL}" rel="noopener">{html.escape(copy['spec'])}</a><a href="{VALIDATOR_URL}" rel="noopener">{html.escape(copy['validator'])}</a><a href="{FONT_URL}" rel="noopener">{html.escape(copy['font'])}</a><a href="{LICENSE}" rel="license noopener">{html.escape(copy['license'])}</a></div></section>
{app_section}
</main>
<footer class="footer">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def update_data_index(pages: Path, artifacts: dict[str, dict]) -> bool:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index must exist before IIIF: {index}")
    text = index.read_text(encoding="utf-8")
    card = (
        f'<a class="item" href="{LANDING_URL}">'
        "<h2>Bopomofo IIIF Presentation API 3</h2>"
        "<p>Complete 37-Canvas visual reference with static SVG painting bodies, "
        "deterministic ZIP and exact SHA-256 checksums.</p>"
        '<span class="tag">IIIF 3.0 · 37 Canvases · SVG · EN + zh-Hant</span></a>'
    )
    existing = re.compile(
        r'<a class="item" href="' + re.escape(LANDING_URL) + r'">.*?</a>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    anchor_urls = (
        f"{SITE}/data/packages/zhuyin-bopomofo-ocfl/",
        CROISSANT_LANDING_URL,
        f"{SITE}/data/zhuyin-bopomofo.html",
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
            raise RuntimeError("data/index.html has no insertion anchor for IIIF")
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
        item
        for item in catalog.get("dataset", [])
        if item.get("url") != LANDING_URL
    ]
    entry = {
        "@type": "Dataset",
        "name": COPY["en"]["title"],
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "conformsTo": IIIF_SPEC_URL,
        "license": LICENSE,
        "distribution": [
            {
                "@type": "DataDownload",
                "contentUrl": artifacts[key]["url"],
                "encodingFormat": artifacts[key]["media_type"],
                "name": artifacts[key]["label"],
            }
            for key in ("collection", "manifest", "bundle", "checksums", "metadata")
        ],
    }
    anchor_dataset_urls = (
        f"{SITE}/data/packages/zhuyin-bopomofo-ocfl/",
        CROISSANT_LANDING_URL,
    )
    position = len(datasets)
    found_anchor = False
    for anchor_url in anchor_dataset_urls:
        for offset, dataset in enumerate(datasets):
            if dataset.get("url") == anchor_url:
                position = offset + 1
                found_anchor = True
                break
        if found_anchor:
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


def render_sitemap(
    page_modified: dict[str, str],
    artifacts: dict[str, dict],
) -> str:
    entries = [
        (LANDING_URL, page_modified["en"]),
        (ZH_LANDING_URL, page_modified["zh-Hant"]),
        (COLLECTION_URL, INITIAL_DATE),
        (MANIFEST_URL, INITIAL_DATE),
        *[
            (artifact["url"], INITIAL_DATE)
            for artifact in artifacts["images"].values()
        ],
        (BUNDLE_URL, INITIAL_DATE),
        (CHECKSUM_URL, INITIAL_DATE),
        (METADATA_URL, INITIAL_DATE),
    ]
    rows = "\n".join(
        f"  <url><loc>{html.escape(url)}</loc><lastmod>{modified}</lastmod></url>"
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
    artifacts = write_artifacts(pages)
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", pages / "data" / f"{LANDING_SLUG}.html"),
        (
            "zh-Hant",
            pages / "zh-Hant" / "data" / f"{LANDING_SLUG}.html",
        ),
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
        pages / "sitemap_iiif.xml",
        render_sitemap(page_modified, artifacts),
    )
    return [
        LANDING_URL,
        ZH_LANDING_URL,
        COLLECTION_URL,
        MANIFEST_URL,
        *[artifact["url"] for artifact in artifacts["images"].values()],
        BUNDLE_URL,
        CHECKSUM_URL,
        METADATA_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin IIIF resource -> {output}")


if __name__ == "__main__":
    main()
