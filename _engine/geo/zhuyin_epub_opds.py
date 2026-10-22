#!/usr/bin/env python3
"""Publish bilingual Bopomofo EPUB 3.3 editions and OPDS catalogs."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape, quoteattr


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
    validate_records,
)


PAGES = HERE / "pages"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
INITIAL_TIMESTAMP = f"{INITIAL_DATE}T00:00:00Z"
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)
VERSION = "1.0.0"
SLUG = "zhuyin-bopomofo-epub-reference"
BOOK_SLUG = "bopomofo-37-symbol-reference"
PACKAGE_PATH = Path("data") / "packages" / "zhuyin-bopomofo-epub"
PACKAGE_URL = f"{SITE}/{PACKAGE_PATH.as_posix()}"
PUBLICATION_PATH = Path("publications") / BOOK_SLUG
PUBLICATION_URL = f"{SITE}/{PUBLICATION_PATH.as_posix()}"
LANDING_PATH = Path("data") / f"{SLUG}.html"
ZH_LANDING_PATH = Path("zh-Hant") / LANDING_PATH
LANDING_URL = f"{SITE}/{LANDING_PATH.as_posix()}"
ZH_LANDING_URL = f"{SITE}/{ZH_LANDING_PATH.as_posix()}"
METADATA_FILENAME = "metadata.jsonld"
METADATA_URL = f"{PACKAGE_URL}/{METADATA_FILENAME}"
OPDS2_PATH = Path("opds") / f"{BOOK_SLUG}.json"
OPDS1_PATH = Path("opds") / f"{BOOK_SLUG}.xml"
OPDS2_URL = f"{SITE}/{OPDS2_PATH.as_posix()}"
OPDS1_URL = f"{SITE}/{OPDS1_PATH.as_posix()}"
SITEMAP_PATH = Path("sitemap_epub.xml")
SITEMAP_URL = f"{SITE}/{SITEMAP_PATH.as_posix()}"
RESOURCE_SYNC = f"{SITE}/resourcesync/capabilitylist.xml"
SOURCE_DATASET = f"{SITE}/data/zhuyin-bopomofo-ml-dataset.html"
EPUB_SPEC = "https://www.w3.org/TR/epub-33/"
EPUB_A11Y_SPEC = "https://www.w3.org/TR/epub-a11y-11/"
WEBPUB_SPEC = "https://readium.org/webpub-manifest/"
OPDS2_SPEC = "https://specs.opds.io/opds-2.0"
OPDS1_SPEC = "https://specs.opds.io/opds-1.2"
EPUB_MEDIA_TYPE = "application/epub+zip"
WEBPUB_MEDIA_TYPE = "application/webpub+json"
OPDS2_MEDIA_TYPE = "application/opds+json"
OPDS1_MEDIA_TYPE = (
    "application/atom+xml;profile=opds-catalog;kind=acquisition"
)
OPEN_ACCESS_REL = "http://opds-spec.org/acquisition/open-access"
CARD_START = "<!-- epub-opds-card:start -->"
CARD_END = "<!-- epub-opds-card:end -->"

XHTML_NS = "http://www.w3.org/1999/xhtml"
OPF_NS = "http://www.idpf.org/2007/opf"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"
XML_NS = "http://www.w3.org/XML/1998/namespace"
INTEGRITY_NS = f"{METADATA_URL}#"

CONTENT_ORDER = (
    "title",
    "intro",
    "initials",
    "medials",
    "finals",
    "practice",
    "about",
)
CATEGORY_FILES = {
    "initial": "initials",
    "medial": "medials",
    "final": "finals",
}
FORBIDDEN = (
    "apps.apple.com",
    "SoftwareApplication",
    APP_NAME,
    APP_ID,
)

ET.register_namespace("", ATOM_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("integrity", INTEGRITY_NS)


MEANING_ZH = {
    "father": "爸爸",
    "afraid": "害怕",
    "mother": "媽媽",
    "to fly": "飛翔",
    "big": "大",
    "sky": "天空",
    "you": "你",
    "to come": "來",
    "dog": "狗",
    "to look": "看",
    "good": "好",
    "home": "家",
    "to go": "去",
    "small": "小",
    "middle": "中間",
    "to eat": "吃",
    "to be": "是",
    "person": "人",
    "early": "早",
    "vegetable": "蔬菜",
    "three": "三",
    "one": "一",
    "five": "五",
    "fish": "魚",
    "wave": "波浪",
    "to drink": "喝",
    "hey (interjection)": "誒（感嘆詞）",
    "love": "愛",
    "to give": "給",
    "to have": "有",
    "peace": "平安",
    "grace": "恩惠",
    "busy": "忙",
    "cold": "冷",
    "two": "二",
}


COPY = {
    "en": {
        "lang": "en",
        "web_segment": "en",
        "title": "Bopomofo: A 37-Symbol Reference",
        "landing_title": (
            "Free Bopomofo EPUB 3.3 - All 37 Zhuyin Symbols"
        ),
        "description": (
            "A free, text-first EPUB 3.3 reference for all 37 Bopomofo "
            "symbols, with Pinyin, broad IPA, examples and open OPDS catalogs."
        ),
        "eyebrow": (
            "EPUB 3.3 · English + Traditional Chinese · OPDS · CC BY 4.0"
        ),
        "lead": (
            "Download a compact offline reference, read the matching web "
            "edition, or download the open catalog files for testing with "
            "compatible tools."
        ),
        "other_language": "繁體中文",
        "back": "Open data",
        "category": {
            "initial": "Initials",
            "medial": "Medials",
            "final": "Finals",
        },
        "category_intro": {
            "initial": (
                "Twenty-one symbols used at the beginning of Mandarin "
                "syllables."
            ),
            "medial": (
                "Three glide symbols that can appear between an initial and "
                "a final."
            ),
            "final": (
                "Thirteen symbols used as simple or compound syllable finals."
            ),
        },
        "labels": {
            "pinyin": "Hanyu Pinyin",
            "ipa": "Broad IPA",
            "unicode": "Unicode",
            "example": "Example",
            "meaning": "Meaning",
        },
        "intro_title": "How to use this reference",
        "intro_paragraphs": (
            (
                "Bopomofo, also called Zhuyin, is a phonetic notation system "
                "used most visibly in Taiwan. This book keeps all 37 base "
                "symbols in one predictable reading order."
            ),
            (
                "Each entry gives a practical Hanyu Pinyin correspondence, a "
                "broad IPA value and one Traditional Chinese example. Exact "
                "pronunciation still depends on syllable context and a fluent "
                "spoken model."
            ),
            (
                "Use this as a lookup and review aid. It is not an audio "
                "course, speech test, diagnostic tool or school-readiness "
                "measure."
            ),
        ),
        "practice_title": "A low-pressure five-minute routine",
        "practice_steps": (
            "Choose five symbols from one chapter.",
            "Read the symbol, then compare the Pinyin and broad IPA.",
            "Say the example after a fluent model rather than guessing from text.",
            "Cover the reference and recall the symbol or Pinyin once.",
            "Stop after five minutes and choose a different set next time.",
        ),
        "about_title": "Sources, license and accessibility",
        "about_text": (
            "The 37 entries come from the companion canonical dataset. This "
            "edition is text-first, has a linear reading order and structural "
            "navigation, and needs no images, audio, scripts or remote media. "
            "No accessibility certification is claimed; rendering and "
            "Bopomofo font support still vary by reading system."
        ),
        "downloads": "Download or read",
        "download_text": (
            "Both editions contain the same 37-symbol reference. Choose the "
            "reading language, or use the online edition when an EPUB reader "
            "does not render Bopomofo reliably."
        ),
        "english_epub": "Download English EPUB",
        "chinese_epub": "Download Traditional Chinese EPUB",
        "online": "Read online",
        "manifest": "Download Readium manifest JSON",
        "catalogs": "Downloadable catalog files",
        "catalog_text": (
            "The OPDS 2.0 JSON and OPDS 1.2 Atom files list both open-access "
            "EPUB editions with byte lengths and SHA-256 checksums."
        ),
        "coverage": "What is inside",
        "coverage_items": (
            "21 initials, 3 medials and 13 finals",
            "Hanyu Pinyin and broad IPA correspondences",
            "Traditional Chinese example characters and meanings",
            "Text-first EPUB navigation, web editions and manifest JSON files",
        ),
        "compatibility": "Compatibility boundary",
        "compatibility_text": (
            "EPUB 3 and Bopomofo font support differ across reading systems. "
            "Check navigation and glyph rendering in the target reader. The "
            "online edition remains available as a fallback. This static host "
            "may return generic JSON or XML HTTP Content-Types, so catalog "
            "clients that require exact OPDS or WebPub media types may need "
            "direct file import."
        ),
        "accessibility": "Accessibility boundary",
        "accessibility_text": (
            "The publication declares textual access modes, structural "
            "navigation and no flashing, motion-simulation or sound hazards. "
            "It does not claim WCAG or EPUB Accessibility certification."
        ),
        "standards": "Standards and source data",
        "license": "License and independence",
        "license_text": (
            "The EPUB files, web editions, manifest JSON and catalog files are "
            "CC BY 4.0. They contain no App Store link, app identifier, "
            "account code, analytics or tracking."
        ),
        "app_title": "Optional activity layer",
        "app_text": (
            "Lumi Bopomofo adds short on-device activities. The open book "
            "remains free, readable and reusable without the app."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "An open, portable reference for families, teachers, weekend "
            "schools and heritage-language programs."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "web_segment": "zh-Hant",
        "title": "注音符號：37 符號完整參考手冊",
        "landing_title": "免費注音 EPUB 3.3：完整 37 個注音符號",
        "description": (
            "免費下載完整 37 個注音符號的純文字 EPUB 3.3 參考手冊，"
            "含漢語拼音、寬式 IPA、例字與開放 OPDS 目錄。"
        ),
        "eyebrow": (
            "EPUB 3.3 · 英文＋繁體中文 · OPDS · CC BY 4.0"
        ),
        "lead": (
            "可下載離線參考手冊、直接閱讀對應網頁版，或下載開放目錄檔案"
            "並以相容工具測試。"
        ),
        "other_language": "English",
        "back": "開放資料",
        "category": {
            "initial": "聲母",
            "medial": "介音",
            "final": "韻母",
        },
        "category_intro": {
            "initial": "21 個用於國語音節開頭的符號。",
            "medial": "3 個可位於聲母與韻母之間的介音符號。",
            "final": "13 個可作為單韻母或複合韻母部分的符號。",
        },
        "labels": {
            "pinyin": "漢語拼音",
            "ipa": "寬式 IPA",
            "unicode": "Unicode",
            "example": "例字",
            "meaning": "例字意思",
        },
        "intro_title": "本手冊的使用方式",
        "intro_paragraphs": (
            (
                "注音符號又稱 Zhuyin 或 Bopomofo，是台灣最常見的漢語"
                "標音系統。本手冊依固定順序收錄全部 37 個基本符號。"
            ),
            (
                "每筆資料提供實用的漢語拼音對照、寬式 IPA 與一個繁體中文"
                "例字；實際發音仍會受音節環境影響，應搭配流利的口語示範。"
            ),
            (
                "本手冊適合查找與複習，不是語音課程、發音測驗、診斷工具"
                "或入學準備評量。"
            ),
        ),
        "practice_title": "低壓力五分鐘複習法",
        "practice_steps": (
            "從同一章挑選五個符號。",
            "先看符號，再核對拼音與寬式 IPA。",
            "跟著流利示範念例字，不要只靠文字猜音。",
            "遮住參考資料，回想一次符號或拼音。",
            "五分鐘就停止，下次改選另一組。",
        ),
        "about_title": "來源、授權與無障礙說明",
        "about_text": (
            "37 筆內容來自同一份標準資料集。本版以文字為主，具線性閱讀"
            "順序與結構化導覽，不需要圖片、音訊、script 或遠端媒體。"
            "本資源不宣稱取得無障礙認證；實際顯示與注音字型支援仍依"
            "閱讀系統而異。"
        ),
        "downloads": "下載或線上閱讀",
        "download_text": (
            "兩種語言版本都涵蓋相同的 37 個符號。請依閱讀語言選擇；"
            "若 EPUB 閱讀器無法正確顯示注音，可改用線上文字版。"
        ),
        "english_epub": "下載英文 EPUB",
        "chinese_epub": "下載繁體中文 EPUB",
        "online": "線上閱讀",
        "manifest": "下載 Readium manifest JSON",
        "catalogs": "可下載的電子書目錄檔案",
        "catalog_text": (
            "OPDS 2.0 JSON 與 OPDS 1.2 Atom 檔案列出兩個開放 EPUB "
            "版本，並附位元組長度與 SHA-256 校驗值。"
        ),
        "coverage": "手冊內容",
        "coverage_items": (
            "21 個聲母、3 個介音與 13 個韻母",
            "漢語拼音與寬式 IPA 對照",
            "繁體中文例字與意思",
            "純文字 EPUB 導覽、網頁版與 manifest JSON 檔案",
        ),
        "compatibility": "相容性界線",
        "compatibility_text": (
            "各閱讀系統的 EPUB 3 與注音字型支援不同，請在目標閱讀器"
            "檢查導覽與字形；若顯示不完整，可直接使用線上版本。此靜態"
            "主機可能回傳一般 JSON 或 XML HTTP Content-Type，因此嚴格"
            "要求 OPDS 或 WebPub 專用 media type 的目錄工具可能需要直接"
            "匯入檔案。"
        ),
        "accessibility": "無障礙界線",
        "accessibility_text": (
            "出版品宣告文字存取模式、結構化導覽，以及無閃爍、動態模擬"
            "與聲音危害；但不宣稱通過 WCAG 或 EPUB Accessibility 認證。"
        ),
        "standards": "標準與資料來源",
        "license": "授權與獨立性",
        "license_text": (
            "EPUB、網頁版、manifest JSON 與目錄檔案皆採 CC BY 4.0，"
            "不含 App Store 連結、App ID、帳號程式碼、analytics 或追蹤。"
        ),
        "app_title": "選用活動層",
        "app_text": (
            "Lumi 注音星球提供裝置端短活動；開放手冊不需 App，仍可免費"
            "閱讀與重用。"
        ),
        "app_cta": "在 App Store 查看 Lumi 注音星球",
        "footer": (
            "提供家庭、教師、週末中文學校與海外傳承語課程使用的開放"
            "可攜式參考資源。"
        ),
    },
}


def _epub_filename(locale: str) -> str:
    suffix = "en" if locale == "en" else "zh-hant"
    return f"{BOOK_SLUG}-{suffix}.epub"


def epub_url(locale: str) -> str:
    return f"{PACKAGE_URL}/{_epub_filename(locale)}"


def web_path(locale: str) -> Path:
    return PUBLICATION_PATH / COPY[locale]["web_segment"]


def web_url(locale: str, filename: str = "title.xhtml") -> str:
    return f"{SITE}/{web_path(locale).as_posix()}/{filename}"


def manifest_url(locale: str) -> str:
    return web_url(locale, "manifest.json")


def page_url(locale: str) -> str:
    return LANDING_URL if locale == "en" else ZH_LANDING_URL


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_bytes_if_changed(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return
    path.write_bytes(content)


def _absolute_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _assert_app_independent(texts: list[str], label: str) -> None:
    combined = "\n".join(texts)
    for forbidden in FORBIDDEN:
        if forbidden in combined:
            raise ValueError(
                f"{label} must remain app-independent: {forbidden}"
            )


def _symbol_cards(rows: list[dict], locale: str, category: str) -> str:
    copy = COPY[locale]
    cards = []
    for row in rows:
        if row["category"] != category:
            continue
        meaning = (
            row["example_meaning_en"]
            if locale == "en"
            else MEANING_ZH[row["example_meaning_en"]]
        )
        cards.append(
            '<section class="symbol-card" data-symbol-id="{symbol_id}" '
            'aria-labelledby="heading-{symbol_id}">'
            '<h2 id="heading-{symbol_id}"><span lang="zh-Bopo">{symbol}</span>'
            '<span class="pinyin"> — {pinyin}</span></h2>'
            "<dl>"
            "<div><dt>{pinyin_label}</dt><dd>{pinyin}</dd></div>"
            "<div><dt>{ipa_label}</dt><dd>/{ipa}/</dd></div>"
            "<div><dt>{unicode_label}</dt><dd>{unicode}</dd></div>"
            "</dl>"
            '<p class="example"><strong>{example_label}:</strong> '
            '<span lang="zh-Hant">{example}</span> '
            "<span>({example_pinyin})</span> — "
            '<span lang="{meaning_lang}">{meaning}</span></p>'
            "</section>".format(
                symbol_id=html.escape(row["symbol_id"], quote=True),
                symbol=html.escape(row["symbol"]),
                pinyin=html.escape(row["pinyin"]),
                ipa=html.escape(row["ipa"]),
                unicode=html.escape(row["unicode"]),
                example=html.escape(row["example_character"]),
                example_pinyin=html.escape(row["example_pinyin"]),
                meaning=html.escape(meaning),
                meaning_lang="en" if locale == "en" else "zh-Hant",
                pinyin_label=html.escape(copy["labels"]["pinyin"]),
                ipa_label=html.escape(copy["labels"]["ipa"]),
                unicode_label=html.escape(copy["labels"]["unicode"]),
                example_label=html.escape(copy["labels"]["example"]),
            )
        )
    expected = {"initial": 21, "medial": 3, "final": 13}[category]
    if len(cards) != expected:
        raise ValueError(
            f"Expected {expected} {category} cards, found {len(cards)}"
        )
    return "\n".join(cards)


def _xhtml_document(
    locale: str,
    filename: str,
    title: str,
    body: str,
    epub_type: str = "bodymatter",
    modified: str = INITIAL_TIMESTAMP,
) -> str:
    canonical = web_url(locale, filename)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="{COPY[locale]['lang']}" xml:lang="{COPY[locale]['lang']}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="content-modified" content="{modified}" />
  <title>{html.escape(title)}</title>
  <link rel="canonical" href="{html.escape(canonical, quote=True)}" />
  <link rel="stylesheet" type="text/css" href="styles.css" />
</head>
<body epub:type="{html.escape(epub_type, quote=True)}">
{body}
</body>
</html>
"""


def _publication_css() -> str:
    return """@charset "UTF-8";
:root {
  color-scheme: light;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC",
    "Microsoft JhengHei", "Noto Sans CJK TC", sans-serif;
  line-height: 1.65;
}
body { max-width: 46rem; margin: 0 auto; padding: 1.5rem; color: #17223a; }
main { display: block; }
h1 { font-size: 2rem; line-height: 1.2; }
h2 { line-height: 1.3; }
a { color: #315fc4; }
.eyebrow { color: #315fc4; font-weight: 700; letter-spacing: .04em; }
.lead { font-size: 1.1rem; color: #4d5a72; }
.symbol-card {
  border-top: .08rem solid #d8dfeb;
  padding: 1rem 0;
  break-inside: avoid;
}
.symbol-card h2 { margin: 0 0 .6rem; }
.symbol-card h2 [lang="zh-Bopo"] { font-size: 2.3rem; }
.pinyin { font-size: 1.1rem; color: #4d5a72; }
dl { margin: 0; }
dl div { display: flex; gap: .7rem; }
dt { min-width: 7rem; font-weight: 700; }
dd { margin: 0; }
.example { margin-bottom: 0; }
nav ol, ol { padding-left: 1.4rem; }
li { margin: .45rem 0; }
.note { border-left: .25rem solid #315fc4; padding-left: 1rem; }
.license { margin-top: 2rem; font-size: .9rem; color: #4d5a72; }
"""


def _nav_document(locale: str) -> str:
    copy = COPY[locale]
    labels = {
        "title": copy["title"],
        "intro": copy["intro_title"],
        "initials": copy["category"]["initial"],
        "medials": copy["category"]["medial"],
        "finals": copy["category"]["final"],
        "practice": copy["practice_title"],
        "about": copy["about_title"],
    }
    rows = "\n".join(
        f'      <li><a href="{name}.xhtml">{html.escape(labels[name])}</a></li>'
        for name in CONTENT_ORDER
    )
    toc = "Table of contents" if locale == "en" else "目錄"
    landmarks = "Landmarks" if locale == "en" else "導覽標記"
    start = "Start" if locale == "en" else "開始閱讀"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="{copy['lang']}" xml:lang="{copy['lang']}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(toc)}</title>
  <link rel="stylesheet" type="text/css" href="styles.css" />
</head>
<body>
  <nav epub:type="toc" id="toc" role="doc-toc">
    <h1>{html.escape(toc)}</h1>
    <ol>
{rows}
    </ol>
  </nav>
  <nav epub:type="landmarks" aria-label="{html.escape(landmarks, quote=True)}">
    <ol>
      <li><a epub:type="bodymatter" href="intro.xhtml">{html.escape(start)}</a></li>
    </ol>
  </nav>
</body>
</html>
"""


def _package_document(
    locale: str,
    modified: str = INITIAL_TIMESTAMP,
) -> str:
    copy = COPY[locale]
    identifier = web_url(locale)
    manifest_items = [
        (
            "nav",
            "nav.xhtml",
            "application/xhtml+xml",
            ' properties="nav"',
        ),
        ("css", "styles.css", "text/css", ""),
        *[
            (
                name,
                f"{name}.xhtml",
                "application/xhtml+xml",
                "",
            )
            for name in CONTENT_ORDER
        ],
    ]
    manifest = "\n".join(
        f'    <item id="{item_id}" href="{href}" media-type="{media_type}"{extra}/>'
        for item_id, href, media_type, extra in manifest_items
    )
    spine = "\n".join(
        f'    <itemref idref="{name}"/>' for name in CONTENT_ORDER
    )
    summary = (
        "Text-only publication with structural navigation; no images, audio, "
        "scripts, flashing, motion simulation or sound hazards."
        if locale == "en"
        else "純文字出版品，具結構化導覽；無圖片、音訊、script、閃爍、動態模擬或聲音危害。"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="{OPF_NS}" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0" unique-identifier="pub-id">
  <metadata>
    <dc:identifier id="pub-id">{escape(identifier)}</dc:identifier>
    <dc:title>{escape(copy['title'])}</dc:title>
    <dc:language>{escape(copy['lang'])}</dc:language>
    <dc:creator>Lumi Apps - iOS App Guide</dc:creator>
    <dc:publisher>Lumi Apps - iOS App Guide</dc:publisher>
    <dc:date>{INITIAL_DATE}</dc:date>
    <dc:rights>Creative Commons Attribution 4.0 International</dc:rights>
    <dc:source>{escape(SOURCE_DATASET)}</dc:source>
    <dc:subject>Bopomofo</dc:subject>
    <dc:subject>Zhuyin</dc:subject>
    <meta property="dcterms:modified">{modified}</meta>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessModeSufficient">textual</meta>
    <meta property="schema:accessibilityFeature">tableOfContents</meta>
    <meta property="schema:accessibilityFeature">readingOrder</meta>
    <meta property="schema:accessibilityFeature">structuralNavigation</meta>
    <meta property="schema:accessibilityHazard">noFlashingHazard</meta>
    <meta property="schema:accessibilityHazard">noMotionSimulationHazard</meta>
    <meta property="schema:accessibilityHazard">noSoundHazard</meta>
    <meta property="schema:accessibilitySummary">{escape(summary)}</meta>
  </metadata>
  <manifest>
{manifest}
  </manifest>
  <spine>
{spine}
  </spine>
</package>
"""


def publication_files(
    rows: list[dict],
    locale: str,
    modified: str = INITIAL_TIMESTAMP,
) -> dict[str, bytes]:
    copy = COPY[locale]
    title_body = (
        '<main epub:type="frontmatter titlepage">'
        f'<p class="eyebrow">EPUB 3.3 · CC BY 4.0 · {VERSION}</p>'
        f"<h1>{html.escape(copy['title'])}</h1>"
        f"<p class=\"lead\">{html.escape(copy['description'])}</p>"
        "<p>21 + 3 + 13 = 37</p>"
        "</main>"
    )
    intro_body = (
        "<main>"
        f"<h1>{html.escape(copy['intro_title'])}</h1>"
        + "".join(
            f"<p>{html.escape(paragraph)}</p>"
            for paragraph in copy["intro_paragraphs"]
        )
        + '<p class="note">21 initials · 3 medials · 13 finals</p>'
        + "</main>"
    )
    practice_body = (
        "<main>"
        f"<h1>{html.escape(copy['practice_title'])}</h1><ol>"
        + "".join(
            f"<li>{html.escape(step)}</li>"
            for step in copy["practice_steps"]
        )
        + "</ol></main>"
    )
    about_body = f"""<main>
<h1>{html.escape(copy['about_title'])}</h1>
<p>{html.escape(copy['about_text'])}</p>
<ul>
  <li><a href="{EPUB_SPEC}">W3C EPUB 3.3</a></li>
  <li><a href="{EPUB_A11Y_SPEC}">W3C EPUB Accessibility 1.1</a></li>
  <li><a href="{SOURCE_DATASET}">{html.escape(copy['standards'])}</a></li>
</ul>
<p class="license"><a rel="license" href="{LICENSE}">CC BY 4.0</a> · Lumi Apps - iOS App Guide</p>
</main>"""
    content = {
        "title": _xhtml_document(
            locale,
            "title.xhtml",
            copy["title"],
            title_body,
            "frontmatter titlepage",
            modified,
        ),
        "intro": _xhtml_document(
            locale,
            "intro.xhtml",
            copy["intro_title"],
            intro_body,
            modified=modified,
        ),
        "practice": _xhtml_document(
            locale,
            "practice.xhtml",
            copy["practice_title"],
            practice_body,
            modified=modified,
        ),
        "about": _xhtml_document(
            locale,
            "about.xhtml",
            copy["about_title"],
            about_body,
            "backmatter",
            modified,
        ),
    }
    for category, filename in CATEGORY_FILES.items():
        body = (
            "<main>"
            f"<h1>{html.escape(copy['category'][category])}</h1>"
            f"<p>{html.escape(copy['category_intro'][category])}</p>"
            f"{_symbol_cards(rows, locale, category)}"
            "</main>"
        )
        content[filename] = _xhtml_document(
            locale,
            f"{filename}.xhtml",
            copy["category"][category],
            body,
            modified=modified,
        )

    container = f"""<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="{CONTAINER_NS}" version="1.0">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    files = {
        "META-INF/container.xml": container.encode("utf-8"),
        "EPUB/package.opf": _package_document(
            locale,
            modified,
        ).encode("utf-8"),
        "EPUB/nav.xhtml": _nav_document(locale).encode("utf-8"),
        "EPUB/styles.css": _publication_css().encode("utf-8"),
    }
    files.update(
        {
            f"EPUB/{name}.xhtml": content[name].encode("utf-8")
            for name in CONTENT_ORDER
        }
    )
    return files


def _zip_info(name: str, compress_type: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = compress_type
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def render_epub(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.writestr(
            _zip_info("mimetype", zipfile.ZIP_STORED),
            EPUB_MEDIA_TYPE.encode("ascii"),
        )
        for name in sorted(files):
            archive.writestr(
                _zip_info(name, zipfile.ZIP_DEFLATED),
                files[name],
            )
    return buffer.getvalue()


def validate_epub(
    rows: list[dict],
    locale: str,
    content: bytes,
) -> None:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if not names or names[0] != "mimetype":
            raise ValueError("EPUB mimetype must be the first ZIP entry")
        if infos[0].compress_type != zipfile.ZIP_STORED:
            raise ValueError("EPUB mimetype must be stored without compression")
        if archive.read("mimetype") != EPUB_MEDIA_TYPE.encode("ascii"):
            raise ValueError("EPUB mimetype content is invalid")
        if len(names) != len(set(names)):
            raise ValueError("EPUB ZIP contains duplicate paths")
        if any(
            name.startswith("/") or ".." in Path(name).parts for name in names
        ):
            raise ValueError("EPUB ZIP contains an unsafe path")
        if archive.testzip() is not None:
            raise ValueError("EPUB ZIP CRC validation failed")

        expected = {
            "mimetype",
            "META-INF/container.xml",
            "EPUB/package.opf",
            "EPUB/nav.xhtml",
            "EPUB/styles.css",
            *[f"EPUB/{name}.xhtml" for name in CONTENT_ORDER],
        }
        if set(names) != expected:
            raise ValueError("EPUB ZIP inventory is incomplete")

        raw_texts = [
            archive.read(name).decode("utf-8")
            for name in names
            if name != "mimetype"
        ]
        _assert_app_independent(raw_texts, "EPUB")

        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(
            f".//{{{CONTAINER_NS}}}rootfile"
        )
        if (
            rootfile is None
            or rootfile.get("full-path") != "EPUB/package.opf"
        ):
            raise ValueError("EPUB container does not identify package.opf")

        package = ET.fromstring(archive.read("EPUB/package.opf"))
        if (
            package.tag != f"{{{OPF_NS}}}package"
            or package.get("version") != "3.0"
        ):
            raise ValueError("EPUB package document must use OPF 3.0")
        language = package.findtext(
            f".//{{http://purl.org/dc/elements/1.1/}}language"
        )
        if language != COPY[locale]["lang"]:
            raise ValueError("EPUB package language is incorrect")
        manifest = {
            item.get("id"): item
            for item in package.findall(f".//{{{OPF_NS}}}item")
        }
        if manifest.get("nav") is None or (
            "nav" not in (manifest["nav"].get("properties") or "").split()
        ):
            raise ValueError("EPUB package requires one nav manifest item")
        for item in manifest.values():
            href = item.get("href", "")
            if f"EPUB/{href}" not in expected:
                raise ValueError(f"EPUB manifest target is missing: {href}")
        spine = [
            item.get("idref")
            for item in package.findall(f".//{{{OPF_NS}}}itemref")
        ]
        if spine != list(CONTENT_ORDER):
            raise ValueError("EPUB spine does not match the reading order")

        found_ids = []
        forbidden_elements = {
            f"{{{XHTML_NS}}}script",
            f"{{{XHTML_NS}}}img",
            f"{{{XHTML_NS}}}audio",
            f"{{{XHTML_NS}}}video",
            f"{{{XHTML_NS}}}iframe",
        }
        for filename in ("nav", *CONTENT_ORDER):
            root = ET.fromstring(archive.read(f"EPUB/{filename}.xhtml"))
            if root.tag != f"{{{XHTML_NS}}}html":
                raise ValueError(f"Invalid XHTML root: {filename}")
            if any(element.tag in forbidden_elements for element in root.iter()):
                raise ValueError(
                    f"EPUB contains forbidden active/media content: {filename}"
                )
            found_ids.extend(
                element.get("data-symbol-id")
                for element in root.iter()
                if element.get("data-symbol-id")
            )
        expected_ids = [row["symbol_id"] for row in rows]
        if sorted(found_ids) != sorted(expected_ids):
            raise ValueError("EPUB must contain each canonical symbol exactly once")


def make_epub_artifacts(
    rows: list[dict],
    modified: str = INITIAL_TIMESTAMP,
) -> dict[str, dict]:
    artifacts = {}
    for locale in COPY:
        files = publication_files(rows, locale, modified)
        content = render_epub(files)
        validate_epub(rows, locale, content)
        artifacts[locale] = {
            "filename": _epub_filename(locale),
            "url": epub_url(locale),
            "media_type": EPUB_MEDIA_TYPE,
            "locale": locale,
            "bytes": content,
            "sha256": _sha256(content),
            "files": files,
        }
    return artifacts


def _accessibility(locale: str) -> dict:
    summary = (
        "Text-only publication with structural navigation and no images, "
        "audio, scripts, flashing, motion simulation or sound hazards. No "
        "accessibility certification is claimed."
        if locale == "en"
        else "純文字出版品，具結構化導覽，無圖片、音訊、script、閃爍、動態模擬或聲音危害；不宣稱取得無障礙認證。"
    )
    return {
        "accessMode": ["textual"],
        "accessModeSufficient": ["textual"],
        "feature": [
            "tableOfContents",
            "readingOrder",
            "structuralNavigation",
        ],
        "hazard": [
            "noFlashingHazard",
            "noMotionSimulationHazard",
            "noSoundHazard",
        ],
        "summary": summary,
    }


def web_manifest(
    locale: str,
    epub: dict,
    modified: str = INITIAL_TIMESTAMP,
) -> dict:
    copy = COPY[locale]
    labels = {
        "title": copy["title"],
        "intro": copy["intro_title"],
        "initials": copy["category"]["initial"],
        "medials": copy["category"]["medial"],
        "finals": copy["category"]["final"],
        "practice": copy["practice_title"],
        "about": copy["about_title"],
    }
    return {
        "@context": "https://readium.org/webpub-manifest/context.jsonld",
        "metadata": {
            "@type": "https://schema.org/LearningResource",
            "identifier": web_url(locale),
            "title": copy["title"],
            "description": copy["description"],
            "language": locale,
            "published": INITIAL_DATE,
            "modified": modified,
            "author": [
                {
                    "name": "Lumi Apps - iOS App Guide",
                    "identifier": SITE,
                }
            ],
            "publisher": [
                {
                    "name": "Lumi Apps - iOS App Guide",
                    "identifier": SITE,
                }
            ],
            "license": LICENSE,
            "numberOfPages": len(CONTENT_ORDER),
            "accessibility": _accessibility(locale),
        },
        "links": [
            {
                "rel": "self",
                "href": manifest_url(locale),
                "type": WEBPUB_MEDIA_TYPE,
            },
            {
                "rel": "alternate",
                "href": epub["url"],
                "type": EPUB_MEDIA_TYPE,
                "size": len(epub["bytes"]),
                "properties": {
                    "checksum": {
                        "algorithm": "sha-256",
                        "encoding": "hex",
                        "value": epub["sha256"],
                    }
                },
            },
            {
                "rel": "license",
                "href": LICENSE,
                "type": "text/html",
            },
        ],
        "readingOrder": [
            {
                "href": web_url(locale, f"{name}.xhtml"),
                "type": "application/xhtml+xml",
                "title": labels[name],
            }
            for name in CONTENT_ORDER
        ],
        "resources": [
            {
                "href": web_url(locale, "nav.xhtml"),
                "type": "application/xhtml+xml",
                "rel": "contents",
            },
            {
                "href": web_url(locale, "styles.css"),
                "type": "text/css",
            },
        ],
        "toc": [
            {
                "href": web_url(locale, f"{name}.xhtml"),
                "title": labels[name],
            }
            for name in CONTENT_ORDER
        ],
    }


def validate_web_manifest(
    locale: str,
    manifest: dict,
    epub: dict,
    web_files: dict[str, bytes],
) -> None:
    encoded = json.dumps(manifest, ensure_ascii=False)
    _assert_app_independent([encoded], "Web Publication manifest")
    if manifest.get("@context") != (
        "https://readium.org/webpub-manifest/context.jsonld"
    ):
        raise ValueError("Web Publication manifest context is invalid")
    if manifest.get("metadata", {}).get("language") != locale:
        raise ValueError("Web Publication manifest language is invalid")
    if len(manifest.get("readingOrder", [])) != len(CONTENT_ORDER):
        raise ValueError("Web Publication reading order is incomplete")
    prefix = f"{PUBLICATION_URL}/{COPY[locale]['web_segment']}/"
    expected_reading = {
        f"{prefix}{name}.xhtml" for name in CONTENT_ORDER
    }
    actual_reading = {
        item.get("href") for item in manifest["readingOrder"]
    }
    if actual_reading != expected_reading:
        raise ValueError("Web Publication reading order targets are invalid")
    for url in actual_reading:
        if not _absolute_https(url):
            raise ValueError(f"Web Publication URL must be HTTPS: {url}")
        if url.removeprefix(prefix) not in web_files:
            raise ValueError(f"Web Publication target is missing: {url}")
    epub_links = [
        link
        for link in manifest.get("links", [])
        if link.get("type") == EPUB_MEDIA_TYPE
    ]
    if len(epub_links) != 1:
        raise ValueError("Web Publication must link one EPUB edition")
    link = epub_links[0]
    checksum = link.get("properties", {}).get("checksum", {})
    if (
        link.get("href") != epub["url"]
        or link.get("size") != len(epub["bytes"])
        or checksum.get("value") != epub["sha256"]
    ):
        raise ValueError("Web Publication EPUB integrity metadata is invalid")


def _metadata(
    epubs: dict[str, dict],
    manifests: dict[str, dict],
    modified: str,
) -> dict:
    encodings = []
    for locale in COPY:
        epub = epubs[locale]
        manifest = manifests[locale]
        encodings.extend(
            [
                {
                    "@type": "MediaObject",
                    "name": f"{COPY[locale]['title']} - EPUB 3.3",
                    "encodingFormat": EPUB_MEDIA_TYPE,
                    "contentUrl": epub["url"],
                    "contentSize": f"{len(epub['bytes'])} bytes",
                    "sha256": epub["sha256"],
                    "inLanguage": locale,
                },
                {
                    "@type": "MediaObject",
                    "name": (
                        f"{COPY[locale]['title']} - "
                        "Readium manifest JSON file"
                    ),
                    "encodingFormat": WEBPUB_MEDIA_TYPE,
                    "contentUrl": manifest_url(locale),
                    "contentSize": f"{len(manifest['bytes'])} bytes",
                    "sha256": manifest["sha256"],
                    "inLanguage": locale,
                },
            ]
        )
    return {
        "@context": "https://schema.org",
        "@type": ["Book", "LearningResource", "Dataset"],
        "@id": f"{LANDING_URL}#book",
        "name": COPY["en"]["title"],
        "alternateName": COPY["zh-Hant"]["title"],
        "description": COPY["en"]["description"],
        "url": LANDING_URL,
        "inLanguage": ["en", "zh-Hant", "zh-Bopo"],
        "version": VERSION,
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "license": LICENSE,
        "isAccessibleForFree": True,
        "learningResourceType": "Reference",
        "educationalUse": ["reference", "practice"],
        "accessMode": ["textual"],
        "accessModeSufficient": ["textual"],
        "accessibilityFeature": [
            "tableOfContents",
            "readingOrder",
            "structuralNavigation",
        ],
        "accessibilityHazard": [
            "noFlashingHazard",
            "noMotionSimulationHazard",
            "noSoundHazard",
        ],
        "isBasedOn": SOURCE_DATASET,
        "conformsTo": EPUB_SPEC,
        "citation": [
            WEBPUB_SPEC,
            OPDS2_SPEC,
            OPDS1_SPEC,
        ],
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps - iOS App Guide",
            "url": SITE,
        },
        "encoding": encodings,
        "subjectOf": [
            {
                "@type": "DataDownload",
                "name": "OPDS 2.0 catalog JSON file",
                "encodingFormat": OPDS2_MEDIA_TYPE,
                "contentUrl": OPDS2_URL,
            },
            {
                "@type": "DataDownload",
                "name": "OPDS 1.2 catalog Atom file",
                "encodingFormat": OPDS1_MEDIA_TYPE,
                "contentUrl": OPDS1_URL,
            },
        ],
    }


def _publication(locale: str, modified: str, epub: dict) -> dict:
    copy = COPY[locale]
    return {
        "metadata": {
            "@type": "https://schema.org/Book",
            "identifier": web_url(locale),
            "title": copy["title"],
            "description": copy["description"],
            "language": locale,
            "published": INITIAL_DATE,
            "modified": modified,
            "author": {
                "name": "Lumi Apps - iOS App Guide",
                "identifier": SITE,
            },
            "publisher": {
                "name": "Lumi Apps - iOS App Guide",
                "identifier": SITE,
            },
            "license": LICENSE,
            "isAccessibleForFree": True,
            "numberOfPages": len(CONTENT_ORDER),
            "accessibility": _accessibility(locale),
        },
        "links": [
            {
                "rel": OPEN_ACCESS_REL,
                "href": epub["url"],
                "type": EPUB_MEDIA_TYPE,
                "title": f"{copy['title']} - EPUB 3.3",
                "size": len(epub["bytes"]),
                "language": locale,
                "properties": {
                    "checksum": {
                        "algorithm": "sha-256",
                        "encoding": "hex",
                        "value": epub["sha256"],
                    }
                },
            },
            {
                "rel": "alternate",
                "href": manifest_url(locale),
                "type": WEBPUB_MEDIA_TYPE,
                "title": "Web Publication manifest",
            },
            {
                "rel": "alternate",
                "href": web_url(locale),
                "type": "application/xhtml+xml",
                "title": copy["title"],
            },
            {
                "rel": "describedby",
                "href": METADATA_URL,
                "type": "application/ld+json",
            },
            {
                "rel": "license",
                "href": LICENSE,
                "type": "text/html",
            },
        ],
    }


def opds2_catalog(modified: str, epubs: dict[str, dict]) -> dict:
    return {
        "metadata": {
            "identifier": OPDS2_URL,
            "title": "Bopomofo 37-Symbol Open Publication Catalog",
            "description": (
                "Open-access English and Traditional Chinese EPUB 3.3 "
                "references for all 37 Bopomofo symbols."
            ),
            "modified": modified,
            "numberOfItems": len(COPY),
        },
        "links": [
            {
                "rel": "self",
                "href": OPDS2_URL,
                "type": OPDS2_MEDIA_TYPE,
            },
            {
                "rel": "alternate",
                "href": OPDS1_URL,
                "type": OPDS1_MEDIA_TYPE,
                "title": "OPDS 1.2 catalog",
            },
            {
                "rel": "alternate",
                "href": LANDING_URL,
                "type": "text/html",
                "title": COPY["en"]["landing_title"],
            },
        ],
        "publications": [
            _publication(locale, modified, epubs[locale])
            for locale in COPY
        ],
    }


def _atom(tag: str) -> str:
    return f"{{{ATOM_NS}}}{tag}"


def _dc(tag: str) -> str:
    return f"{{{DC_NS}}}{tag}"


def _integrity(tag: str) -> str:
    return f"{{{INTEGRITY_NS}}}{tag}"


def _add_text(
    parent: ET.Element,
    tag: str,
    text: str,
    **attributes: str,
) -> ET.Element:
    element = ET.SubElement(parent, tag, attributes)
    element.text = text
    return element


def _add_author(parent: ET.Element) -> None:
    author = ET.SubElement(parent, _atom("author"))
    _add_text(author, _atom("name"), "Lumi Apps - iOS App Guide")
    _add_text(author, _atom("uri"), SITE)


def opds1_catalog(modified: str, epubs: dict[str, dict]) -> str:
    root = ET.Element(_atom("feed"))
    _add_text(root, _atom("id"), OPDS1_URL)
    _add_text(
        root,
        _atom("title"),
        "Bopomofo 37-Symbol Open Publication Catalog",
    )
    _add_text(root, _atom("updated"), modified)
    _add_author(root)
    for relation, href, media_type, title in (
        ("self", OPDS1_URL, OPDS1_MEDIA_TYPE, "OPDS 1.2 catalog"),
        ("start", OPDS1_URL, OPDS1_MEDIA_TYPE, "Catalog root"),
        ("alternate", OPDS2_URL, OPDS2_MEDIA_TYPE, "OPDS 2.0 catalog"),
        ("alternate", LANDING_URL, "text/html", COPY["en"]["landing_title"]),
        ("license", LICENSE, "text/html", "CC BY 4.0"),
    ):
        ET.SubElement(
            root,
            _atom("link"),
            {
                "rel": relation,
                "href": href,
                "type": media_type,
                "title": title,
            },
        )

    for locale in COPY:
        copy = COPY[locale]
        epub = epubs[locale]
        entry = ET.SubElement(root, _atom("entry"))
        _add_text(entry, _atom("id"), web_url(locale))
        title = _add_text(entry, _atom("title"), copy["title"])
        title.set(f"{{{XML_NS}}}lang", locale)
        _add_text(entry, _atom("updated"), modified)
        _add_text(
            entry,
            _atom("published"),
            f"{INITIAL_DATE}T00:00:00Z",
        )
        _add_author(entry)
        summary = _add_text(
            entry,
            _atom("summary"),
            copy["description"],
            type="text",
        )
        summary.set(f"{{{XML_NS}}}lang", locale)
        _add_text(
            entry,
            _atom("rights"),
            "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        )
        _add_text(entry, _dc("identifier"), web_url(locale))
        _add_text(entry, _dc("language"), locale)
        _add_text(entry, _dc("issued"), INITIAL_DATE)
        _add_text(entry, _dc("rights"), LICENSE)
        _add_text(entry, _dc("hasVersion"), VERSION)
        ET.SubElement(
            entry,
            _atom("category"),
            {"term": "OER", "label": "Open educational resource"},
        )
        for relation, href, media_type, title_text in (
            (
                "alternate",
                web_url(locale),
                "application/xhtml+xml",
                copy["title"],
            ),
            (
                "alternate",
                manifest_url(locale),
                WEBPUB_MEDIA_TYPE,
                "Web Publication manifest",
            ),
            (
                "describedby",
                METADATA_URL,
                "application/ld+json",
                "Schema.org metadata",
            ),
            ("license", LICENSE, "text/html", "CC BY 4.0"),
        ):
            ET.SubElement(
                entry,
                _atom("link"),
                {
                    "rel": relation,
                    "href": href,
                    "type": media_type,
                    "title": title_text,
                },
            )
        link = ET.SubElement(
            entry,
            _atom("link"),
            {
                "rel": OPEN_ACCESS_REL,
                "href": epub["url"],
                "type": EPUB_MEDIA_TYPE,
                "title": f"{copy['title']} - EPUB 3.3",
                "length": str(len(epub["bytes"])),
            },
        )
        _add_text(
            link,
            _integrity("checksum"),
            epub["sha256"],
            algorithm="sha-256",
            encoding="hex",
        )

    ET.indent(root, space="  ")
    return (
        ET.tostring(root, encoding="utf-8", xml_declaration=True)
        .decode("utf-8")
        + "\n"
    )


def validate_catalogs(
    opds2: dict,
    opds1: str,
    epubs: dict[str, dict],
) -> None:
    encoded = json.dumps(opds2, ensure_ascii=False)
    _assert_app_independent([encoded, opds1], "OPDS catalogs")
    metadata = opds2.get("metadata", {})
    if (
        metadata.get("identifier") != OPDS2_URL
        or metadata.get("numberOfItems") != len(COPY)
    ):
        raise ValueError("OPDS 2.0 metadata is invalid")
    if len(opds2.get("publications", [])) != len(COPY):
        raise ValueError("OPDS 2.0 must contain both language editions")
    json_acquisitions = {}
    languages = set()
    for publication in opds2["publications"]:
        languages.add(publication["metadata"].get("language"))
        links = [
            link
            for link in publication.get("links", [])
            if link.get("rel") == OPEN_ACCESS_REL
        ]
        if len(links) != 1:
            raise ValueError("Each OPDS 2.0 publication needs one EPUB")
        link = links[0]
        checksum = link.get("properties", {}).get("checksum", {})
        json_acquisitions[link.get("href")] = (
            link.get("size"),
            checksum.get("value"),
        )
        if (
            link.get("type") != EPUB_MEDIA_TYPE
            or checksum.get("algorithm") != "sha-256"
            or checksum.get("encoding") != "hex"
        ):
            raise ValueError("OPDS 2.0 EPUB integrity metadata is invalid")
    if languages != set(COPY):
        raise ValueError("OPDS 2.0 languages must be en and zh-Hant")

    root = ET.fromstring(opds1)
    if root.tag != _atom("feed"):
        raise ValueError("OPDS 1.2 root must be an Atom feed")
    entries = root.findall(_atom("entry"))
    if len(entries) != len(COPY):
        raise ValueError("OPDS 1.2 must contain both language editions")
    xml_acquisitions = {}
    for entry in entries:
        links = [
            link
            for link in entry.findall(_atom("link"))
            if link.get("rel") == OPEN_ACCESS_REL
        ]
        if len(links) != 1:
            raise ValueError("Each OPDS 1.2 entry needs one EPUB")
        link = links[0]
        checksum = link.find(_integrity("checksum"))
        if (
            checksum is None
            or checksum.get("algorithm") != "sha-256"
            or checksum.get("encoding") != "hex"
        ):
            raise ValueError("OPDS 1.2 EPUB integrity metadata is invalid")
        xml_acquisitions[link.get("href")] = (
            int(link.get("length", "0")),
            checksum.text or "",
        )
    expected = {
        artifact["url"]: (
            len(artifact["bytes"]),
            artifact["sha256"],
        )
        for artifact in epubs.values()
    }
    if json_acquisitions != expected or xml_acquisitions != expected:
        raise ValueError("OPDS acquisitions do not match EPUB artifacts")


def _schema_graph(
    locale: str,
    epubs: dict[str, dict],
    manifests: dict[str, dict],
    artifact_modified: str,
    page_modified: str,
    app_public: bool,
) -> dict:
    metadata = _metadata(epubs, manifests, artifact_modified)
    metadata.pop("@context")
    graph = [
        {
            "@type": "WebPage",
            "@id": page_url(locale),
            "url": page_url(locale),
            "name": COPY[locale]["landing_title"],
            "description": COPY[locale]["description"],
            "inLanguage": locale,
            "datePublished": INITIAL_DATE,
            "dateModified": page_modified,
            "mainEntity": {"@id": metadata["@id"]},
        },
        metadata,
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Open data",
                    "item": f"{SITE}/data/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": COPY[locale]["landing_title"],
                    "item": page_url(locale),
                },
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
                "url": appstore_url(
                    APP_KEY,
                    f"iag_bopomofo_epub_{locale.lower()}",
                ),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(locale: str, epubs: dict[str, dict]) -> str:
    copy = COPY[locale]
    cards = []
    for item_locale, label in (
        ("en", copy["english_epub"]),
        ("zh-Hant", copy["chinese_epub"]),
    ):
        artifact = epubs[item_locale]
        cards.append(
            '<a class="download" href="{url}" download><strong>{label}</strong>'
            "<span>{size:,} bytes</span><small>SHA-256 {hash}</small></a>".format(
                url=html.escape(artifact["url"], quote=True),
                label=html.escape(label),
                size=len(artifact["bytes"]),
                hash=artifact["sha256"][:16] + "…",
            )
        )
    return "".join(cards)


def render_page(
    locale: str,
    epubs: dict[str, dict],
    manifests: dict[str, dict],
    artifact_modified: str,
    app_public: bool,
    page_modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other = "zh-Hant" if locale == "en" else "en"
    schema = json.dumps(
        _schema_graph(
            locale,
            epubs,
            manifests,
            artifact_modified,
            page_modified,
            app_public,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    coverage = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["coverage_items"]
    )
    app_section = ""
    if app_public:
        app_section = (
            '<section class="panel app"><p class="kicker">{title}</p>'
            '<p>{text}</p><a class="button" href="{url}" '
            'rel="nofollow noopener">{cta} &rarr;</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(
                    APP_KEY,
                    f"iag_bopomofo_epub_{locale.lower()}",
                ),
                quote=True,
            ),
            cta=html.escape(copy["app_cta"]),
        )
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['landing_title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(page_modified, quote=True)}">
<link rel="canonical" href="{html.escape(page_url(locale), quote=True)}">
<link rel="alternate" hreflang="en" href="{LANDING_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{ZH_LANDING_URL}">
<link rel="alternate" hreflang="x-default" href="{LANDING_URL}">
<link rel="alternate" type="{EPUB_MEDIA_TYPE}" hreflang="en" href="{epub_url('en')}" title="{html.escape(COPY['en']['title'], quote=True)}">
<link rel="alternate" type="{EPUB_MEDIA_TYPE}" hreflang="zh-Hant" href="{epub_url('zh-Hant')}" title="{html.escape(COPY['zh-Hant']['title'], quote=True)}">
<link rel="alternate" type="{WEBPUB_MEDIA_TYPE}" href="{manifest_url(locale)}" title="Web Publication manifest">
<link rel="alternate" type="{OPDS2_MEDIA_TYPE}" href="{OPDS2_URL}" title="OPDS 2.0 catalog">
<link rel="alternate" type="{OPDS1_MEDIA_TYPE}" href="{OPDS1_URL}" title="OPDS 1.2 catalog">
<link rel="describedby" type="application/ld+json" href="{METADATA_URL}">
<link rel="resourcesync" href="{RESOURCE_SYNC}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#14203a;--sub:#5b687e;--line:#d9e2ee;--brand:#315fc4;--bg:#f3f7fc;--paper:#fff;--soft:#edf3ff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.68 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}a{{color:var(--brand)}}.wrap{{max-width:1080px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.95);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:780;text-decoration:none;white-space:nowrap}}.hero{{padding:62px 20px 34px}}.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.07em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:980px}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}p{{color:var(--sub);margin:8px 0}}.lead{{font-size:clamp(17px,3vw,21px);max-width:850px}}main>.wrap{{margin-bottom:24px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 34px rgba(34,53,91,.05)}}.downloads,.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:4px;border:1px solid var(--line);border-radius:16px;padding:17px;background:var(--soft);text-decoration:none;min-width:0}}.download strong{{font-size:16px}}.download span,.download small{{color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.download small{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}.links{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:17px}}.links a{{border:1px solid var(--line);border-radius:13px;padding:11px 13px;text-decoration:none;font-weight:760;background:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}li{{margin:8px 0;color:var(--sub)}}.button{{display:inline-flex;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:820;white-space:nowrap}}.app{{background:linear-gradient(135deg,#fff,#edf3ff)}}footer{{padding:18px 20px 44px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:760px){{.downloads,.two,.links{{grid-template-columns:1fr}}.hero{{padding-top:42px}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{SITE}/data/">&larr; {html.escape(copy['back'])}</a><a href="{html.escape(page_url(other), quote=True)}">{html.escape(copy['other_language'])}</a></div></header>
<main>
<section class="wrap hero"><p class="eyebrow">{html.escape(copy['eyebrow'])}</p><h1>{html.escape(copy['landing_title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p></section>
<section class="wrap panel"><h2>{html.escape(copy['downloads'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads">{_download_cards(locale, epubs)}</div><div class="links"><a href="{web_url(locale)}">{html.escape(copy['online'])} &rarr;</a><a href="{manifest_url(locale)}" download>{html.escape(copy['manifest'])} &rarr;</a></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['coverage'])}</h2><ul>{coverage}</ul></article><article class="panel"><h2>{html.escape(copy['catalogs'])}</h2><p>{html.escape(copy['catalog_text'])}</p><div class="links"><a href="{OPDS2_URL}" download>OPDS 2.0 JSON</a><a href="{OPDS1_URL}" download>OPDS 1.2 Atom</a></div></article></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['compatibility'])}</h2><p>{html.escape(copy['compatibility_text'])}</p></article><article class="panel"><h2>{html.escape(copy['accessibility'])}</h2><p>{html.escape(copy['accessibility_text'])}</p></article></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['standards'])}</h2><div class="links"><a href="{EPUB_SPEC}" rel="noopener">EPUB 3.3</a><a href="{EPUB_A11Y_SPEC}" rel="noopener">EPUB Accessibility 1.1</a><a href="{WEBPUB_SPEC}" rel="noopener">Readium manifest reference</a><a href="{SOURCE_DATASET}">37-symbol dataset</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a><p><a href="{METADATA_URL}">SHA-256 metadata</a> · {artifact_modified[:10]}</p></article></section>
<div class="wrap">{app_section}</div>
</main>
<footer>{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def _update_data_index(
    pages: Path,
    epubs: dict[str, dict],
    manifests: dict[str, dict],
    modified: str,
) -> None:
    index = pages / "data" / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Data index is missing: {index}")
    content = index.read_text(encoding="utf-8")
    block = (
        f'{CARD_START}<a class="item" href="{LANDING_URL}"><div>'
        '<span class="tag">EPUB 3.3 · OPDS</span>'
        "<h2>Bopomofo 37-symbol open publication</h2>"
        "<p>Accessible English and Traditional Chinese EPUB editions with "
        "web reading and open catalog feeds.</p></div>"
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
                    "@type": ["Dataset", "Book", "LearningResource"],
                    "name": COPY["en"]["title"],
                    "description": COPY["en"]["description"],
                    "url": LANDING_URL,
                    "dateModified": modified,
                    "license": LICENSE,
                    "learningResourceType": "Reference",
                    "distribution": [
                        *[
                            {
                                "@type": "DataDownload",
                                "name": f"{COPY[locale]['title']} - EPUB 3.3",
                                "encodingFormat": EPUB_MEDIA_TYPE,
                                "contentUrl": epubs[locale]["url"],
                            }
                            for locale in COPY
                        ],
                        *[
                            {
                                "@type": "DataDownload",
                                "name": (
                                    f"{COPY[locale]['title']} - "
                                    "Web Publication manifest"
                                ),
                                "encodingFormat": WEBPUB_MEDIA_TYPE,
                                "contentUrl": manifest_url(locale),
                            }
                            for locale in COPY
                        ],
                    ],
                }
            )
            catalog["dataset"] = datasets
            updated = (
                updated[: match.start()]
                + match.group(1)
                + json.dumps(catalog, ensure_ascii=False)
                + match.group(3)
                + updated[match.end() :]
            )
    write_text_if_changed(index, updated)


def render_sitemap(
    page_modified: dict[str, str],
    artifact_modified: str,
) -> str:
    entries = [
        (LANDING_URL, page_modified["en"]),
        (ZH_LANDING_URL, page_modified["zh-Hant"]),
        (METADATA_URL, artifact_modified),
        (OPDS2_URL, artifact_modified),
        (OPDS1_URL, artifact_modified),
    ]
    for locale in COPY:
        entries.extend(
            [
                (epub_url(locale), artifact_modified),
                (manifest_url(locale), artifact_modified),
                *[
                    (
                        web_url(locale, f"{name}.xhtml"),
                        artifact_modified,
                    )
                    for name in CONTENT_ORDER
                ],
            ]
        )
    rows = "\n".join(
        f"  <url><loc>{escape(url)}</loc><lastmod>{modified}</lastmod></url>"
        for url, modified in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n</urlset>\n"
    )


def is_app_public(pages: Path = PAGES) -> bool:
    if APPSTORE.get(APP_KEY) != APP_ID:
        raise ValueError("Lumi Bopomofo App Store ID does not match the registry")
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _prior_modified(opds_path: Path) -> str:
    if not opds_path.exists():
        return INITIAL_TIMESTAMP
    try:
        modified = json.loads(opds_path.read_text(encoding="utf-8"))[
            "metadata"
        ]["modified"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"Existing OPDS catalog is invalid: {opds_path}") from error
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        modified,
    ):
        raise ValueError(f"Existing OPDS modified value is invalid: {modified}")
    return modified


def _render_core_artifacts(
    rows: list[dict],
    modified: str,
) -> tuple[dict[str, dict], dict[str, dict], dict[Path, bytes]]:
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        modified,
    ):
        raise ValueError(f"Publication modified timestamp is invalid: {modified}")

    epubs = make_epub_artifacts(rows, modified)
    manifests = {}
    files: dict[Path, bytes] = {}
    for locale, epub in epubs.items():
        files[PACKAGE_PATH / epub["filename"]] = epub["bytes"]
        web_files = {
            f"{name}.xhtml": epub["files"][f"EPUB/{name}.xhtml"]
            for name in CONTENT_ORDER
        }
        web_files["nav.xhtml"] = epub["files"]["EPUB/nav.xhtml"]
        web_files["styles.css"] = epub["files"]["EPUB/styles.css"]
        manifest = web_manifest(locale, epub, modified)
        validate_web_manifest(locale, manifest, epub, web_files)
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        manifests[locale] = {
            "bytes": manifest_bytes,
            "sha256": _sha256(manifest_bytes),
            "url": manifest_url(locale),
        }
        for filename, content in web_files.items():
            files[web_path(locale) / filename] = content
        files[web_path(locale) / "manifest.json"] = manifest_bytes

    opds2 = opds2_catalog(modified, epubs)
    opds1 = opds1_catalog(modified, epubs)
    validate_catalogs(opds2, opds1, epubs)
    files[OPDS2_PATH] = (
        json.dumps(opds2, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    files[OPDS1_PATH] = opds1.encode("utf-8")

    metadata_text = json.dumps(
        _metadata(epubs, manifests, modified),
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    _assert_app_independent([metadata_text], "Publication metadata")
    files[PACKAGE_PATH / METADATA_FILENAME] = metadata_text.encode("utf-8")
    return epubs, manifests, files


def _next_modified(prior: str) -> str:
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        NOW,
    ):
        raise ValueError(f"Current publication timestamp is invalid: {NOW}")
    if NOW > prior:
        return NOW
    parsed = dt.datetime.strptime(prior, "%Y-%m-%dT%H:%M:%SZ")
    return (parsed + dt.timedelta(seconds=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def build(
    pages: Path = PAGES,
    app_public: bool | None = None,
) -> list[str]:
    rows = records()
    validate_records(rows)
    opds_path = pages / OPDS2_PATH
    catalog_exists = opds_path.exists()
    prior_modified = _prior_modified(opds_path)
    artifact_modified = prior_modified
    epubs, manifests, core_files = _render_core_artifacts(
        rows,
        artifact_modified,
    )
    changed = any(
        not (pages / path).exists()
        or (pages / path).read_bytes() != content
        for path, content in core_files.items()
    )
    if changed and catalog_exists:
        artifact_modified = _next_modified(prior_modified)
        if artifact_modified != prior_modified:
            epubs, manifests, core_files = _render_core_artifacts(
                rows,
                artifact_modified,
            )
    for path, content in core_files.items():
        _write_bytes_if_changed(pages / path, content)

    artifact_modified_date = artifact_modified[:10]
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, path in (
        ("en", pages / LANDING_PATH),
        ("zh-Hant", pages / ZH_LANDING_PATH),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        page_modified[locale] = render_versioned_page(
            path,
            lambda page_date, locale=locale: render_page(
                locale,
                epubs,
                manifests,
                artifact_modified,
                public,
                page_date,
            ),
            INITIAL_DATE,
            TODAY,
        )

    _update_data_index(
        pages,
        epubs,
        manifests,
        artifact_modified_date,
    )
    write_text_if_changed(
        pages / SITEMAP_PATH,
        render_sitemap(page_modified, artifact_modified_date),
    )

    return [
        LANDING_URL,
        ZH_LANDING_URL,
        *[artifact["url"] for artifact in epubs.values()],
        *[manifest["url"] for manifest in manifests.values()],
        OPDS2_URL,
        OPDS1_URL,
        METADATA_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    for output in build():
        print(f"Zhuyin EPUB/OPDS publication -> {output}")


if __name__ == "__main__":
    main()
