#!/usr/bin/env python3
"""Publish bilingual, directly importable Anki text decks for all 37 Zhuyin symbols."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from family_travel_dataset import (  # noqa: E402
    render_versioned_page,
    write_text_if_changed,
)
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_data_hub import ZHUYIN, ZHUYIN_IPA  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-bopomofo-anki-deck"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
DATASET_URL = f"{SITE}/data/zhuyin-bopomofo.html"
DATASET_JSON = f"{SITE}/data/zhuyin-bopomofo.json"
CHART_URL = f"{SITE}/tools/zhuyin-bopomofo-chart.html"
ANKI_MANUAL = "https://docs.ankiweb.net/importing/text-files.html"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/"
    "index.html"
)
METADATA_FILENAME = f"{SLUG}.metadata.json"
METADATA_URL = f"{SITE}/tools/{METADATA_FILENAME}"
SITEMAP_URL = f"{SITE}/sitemap_anki.xml"
APP_KEY = "lumibopomofo"
APP_ID = "6773017109"
APP_NAME = "Lumi Bopomofo"
CONTENT_MODIFIED_RE = re.compile(
    r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"'
)

DECKS = {
    "en": {
        "filename": f"{SLUG}-en.tsv",
        "deck": "Open Bopomofo - 37 Symbols (English)",
        "tags": "bopomofo zhuyin taiwan-mandarin open-oer english",
    },
    "zh-Hant": {
        "filename": f"{SLUG}-zh-hant.tsv",
        "deck": "開放注音牌組 - 37 個符號（繁體中文）",
        "tags": "bopomofo zhuyin taiwan-mandarin open-oer zh-hant",
    },
}

CATEGORY_LABELS = {
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

COPY = {
    "en": {
        "lang": "en",
        "title": "Free Bopomofo Anki Deck - All 37 Zhuyin Symbols",
        "description": (
            "Download a free UTF-8 Anki import deck covering all 37 Bopomofo "
            "symbols with Pinyin, IPA, categories and Traditional Chinese examples."
        ),
        "eyebrow": "Open flashcard deck · CC BY 4.0",
        "lead": (
            "A compact, inspectable two-field deck for learning the complete Zhuyin "
            "alphabet used for Mandarin pronunciation in Taiwan."
        ),
        "badges": (
            "37 symbols",
            "Pinyin + IPA",
            "UTF-8 TSV",
            "No account required",
        ),
        "language": "繁體中文",
        "tools": "Free tools",
        "download": "Download the Anki import deck",
        "download_text": (
            "Choose one language edition. Each note uses the symbol on the front and "
            "Pinyin, IPA, category and an example word on the back."
        ),
        "primary": "English deck",
        "alternate": "Traditional Chinese deck",
        "file_note": "37 notes · tab-separated UTF-8 text · no media files",
        "how": "Import in three steps",
        "steps": (
            "Download the English or Traditional Chinese TSV file.",
            "In Anki, choose File > Import and select the downloaded file.",
            "Keep Front mapped to Front and Back mapped to Back, then import.",
        ),
        "repeat": (
            "The symbol is the first field, so importing an updated edition can match "
            "the same notes without relying on custom GUIDs."
        ),
        "included": "What every card includes",
        "included_items": (
            "One of the complete 37 Zhuyin symbols",
            "Hanyu Pinyin correspondence",
            "Broad IPA transcription",
            "Initial, medial or final classification",
            "A Traditional Chinese example with marked Pinyin and English meaning",
        ),
        "preview": "Preview all 37 notes",
        "symbol": "Symbol",
        "details": "Card back",
        "source": "Open data and provenance",
        "source_text": (
            "The deck is generated from the site's CC BY 4.0 Bopomofo dataset. "
            "Pronunciation mappings are reference aids, not a replacement for listening "
            "to a qualified speaker or teacher."
        ),
        "dataset": "View the machine-readable dataset",
        "chart": "Open the printable 37-symbol chart",
        "manual": "Read Anki's official text import guide",
        "license": "License and reuse",
        "license_text": (
            "Reuse, adapt and redistribute the deck under CC BY 4.0 with attribution "
            "to Lumi Apps - iOS App Guide."
        ),
        "privacy": "Private by design",
        "privacy_text": (
            "The download has no scripts, account, analytics, learner records, audio, "
            "images or remote requests. It is plain text you can inspect before import."
        ),
        "faq": "Questions",
        "faqs": (
            (
                "Does this work with Anki?",
                "Yes. It follows Anki's official UTF-8 text import headers and uses a "
                "tab separator with two named fields.",
            ),
            (
                "Does the deck include all Bopomofo symbols?",
                "Yes. It contains 21 initials, 3 medials and 13 finals: 37 notes total.",
            ),
            (
                "Does it include audio?",
                "No. This edition is deliberately text-only so it remains small, "
                "inspectable, remixable and free of third-party media rights.",
            ),
            (
                "Is this an official Anki deck?",
                "No. It is an independent open educational resource and is not "
                "affiliated with or endorsed by Anki.",
            ),
        ),
        "app_title": "Optional game-based iPhone practice",
        "app_text": (
            "Lumi Bopomofo offers a separate on-device way to practise Zhuyin through "
            "short activities. The open deck remains free and independent."
        ),
        "app_cta": "View Lumi Bopomofo on the App Store",
        "footer": (
            "Independent open educational resource. Anki is referenced only for "
            "format compatibility."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "免費注音 Anki 牌組｜完整 37 個注音符號",
        "description": (
            "免費下載 UTF-8 Anki 匯入牌組，完整收錄 37 個注音符號、漢語拼音、"
            "IPA、分類與繁體中文例字。"
        ),
        "eyebrow": "開放閃卡牌組 · CC BY 4.0",
        "lead": (
            "可檢視、可編輯、可直接匯入的雙欄牌組，完整涵蓋台灣華語使用的"
            " 37 個注音符號。"
        ),
        "badges": (
            "37 個符號",
            "拼音＋IPA",
            "UTF-8 TSV",
            "免帳號下載",
        ),
        "language": "English",
        "tools": "免費工具",
        "download": "下載 Anki 匯入牌組",
        "download_text": (
            "選擇一種語言版本；每張卡正面是注音符號，背面包含漢語拼音、"
            "IPA、分類與例字。"
        ),
        "primary": "繁體中文版",
        "alternate": "英文版",
        "file_note": "37 張卡 · UTF-8 Tab 分隔純文字 · 不含媒體檔",
        "how": "三步驟匯入",
        "steps": (
            "下載繁體中文或英文 TSV 檔。",
            "在 Anki 選擇「檔案 > 匯入」，再選取下載的檔案。",
            "確認 Front 對應正面、Back 對應背面，再執行匯入。",
        ),
        "repeat": (
            "第一欄使用唯一注音符號，因此日後匯入更新版時，不需自訂 GUID "
            "也能比對同一筆筆記。"
        ),
        "included": "每張卡包含",
        "included_items": (
            "完整 37 個注音符號之一",
            "漢語拼音對照",
            "寬式 IPA 音標",
            "聲母、介音或韻母分類",
            "繁體中文例字、標調拼音與英文意思",
        ),
        "preview": "預覽全部 37 張卡",
        "symbol": "符號",
        "details": "卡片背面",
        "source": "開放資料與來源",
        "source_text": (
            "牌組由本站 CC BY 4.0 注音資料集自動產生。發音對照僅供參考，"
            "不能取代合格華語教師或母語者的實際示範。"
        ),
        "dataset": "查看機器可讀資料集",
        "chart": "開啟可列印 37 符號表",
        "manual": "閱讀 Anki 官方文字匯入說明",
        "license": "授權與再利用",
        "license_text": (
            "依 CC BY 4.0 授權；標示 Lumi Apps - iOS App Guide 後即可再利用、"
            "修改與重新散布。"
        ),
        "privacy": "從設計保護隱私",
        "privacy_text": (
            "下載檔不含程式碼、帳號、分析、學習紀錄、聲音、圖片或遠端請求；"
            "它是匯入前即可自行檢查的純文字。"
        ),
        "faq": "常見問題",
        "faqs": (
            (
                "這個檔案可以匯入 Anki 嗎？",
                "可以。檔案採用 Anki 官方支援的 UTF-8 文字匯入標頭、Tab "
                "分隔與兩個具名欄位。",
            ),
            (
                "牌組有完整收錄所有注音嗎？",
                "有，共 21 個聲母、3 個介音與 13 個韻母，合計 37 張卡。",
            ),
            (
                "牌組有聲音嗎？",
                "沒有。本版刻意維持純文字，讓檔案小、可檢查、可自由修改，"
                "也不涉及第三方媒體權利。",
            ),
            (
                "這是 Anki 官方牌組嗎？",
                "不是。這是獨立開放教育資源，與 Anki 沒有隸屬或背書關係。",
            ),
        ),
        "app_title": "選用的 iPhone 遊戲化練習",
        "app_text": (
            "Lumi 注音星球提供另一種在裝置上以短活動練習注音的方式；"
            "開放牌組仍維持免費且獨立。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "footer": "獨立開放教育資源；Anki 僅作為檔案相容格式名稱使用。",
    },
}


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def deck_url(locale: str) -> str:
    return f"{SITE}/tools/{DECKS[locale]['filename']}"


def is_app_public(pages: Path = PAGES) -> bool:
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def _details(locale: str, record: tuple[str, str, str, str, str, str]) -> str:
    symbol, pinyin, category, character, example_pinyin, meaning = record
    ipa = ZHUYIN_IPA[symbol]
    category_label = CATEGORY_LABELS[locale][category]
    if locale == "en":
        return (
            f"Pinyin: {pinyin} | IPA: [{ipa}] | Category: {category_label} | "
            f"Example: {character} ({example_pinyin}) - {meaning}"
        )
    return (
        f"漢語拼音：{pinyin}｜IPA：[{ipa}]｜分類：{category_label}｜"
        f"例字：{character}（{example_pinyin}）｜英文：{meaning}"
    )


def render_tsv(locale: str) -> str:
    deck = DECKS[locale]
    headers = [
        "#separator:Tab",
        "#html:false",
        f"#tags:{deck['tags']}",
        f"#deck:{deck['deck']}",
        "#columns:Front\tBack",
    ]
    rows = [f"{record[0]}\t{_details(locale, record)}" for record in ZHUYIN]
    return "\n".join([*headers, *rows]) + "\n"


def validate_tsv(locale: str, content: str) -> None:
    if content.startswith("\ufeff"):
        raise ValueError("Anki TSV must be UTF-8 without a BOM")
    deck = DECKS[locale]
    expected_headers = [
        "#separator:Tab",
        "#html:false",
        f"#tags:{deck['tags']}",
        f"#deck:{deck['deck']}",
        "#columns:Front\tBack",
    ]
    lines = content.splitlines()
    if lines[: len(expected_headers)] != expected_headers:
        raise ValueError(f"Invalid Anki import headers for {locale}")
    rows = lines[len(expected_headers) :]
    if len(rows) != len(ZHUYIN):
        raise ValueError(f"Anki deck must contain all {len(ZHUYIN)} symbols")
    expected_symbols = [record[0] for record in ZHUYIN]
    actual_symbols = []
    for line, record in zip(rows, ZHUYIN):
        fields = line.split("\t")
        if len(fields) != 2:
            raise ValueError("Every Anki note must contain exactly two fields")
        symbol, details = fields
        actual_symbols.append(symbol)
        for expected in (
            record[1],
            ZHUYIN_IPA[symbol],
            record[3],
            record[4],
        ):
            if expected not in details:
                raise ValueError(f"Anki note is missing {expected}: {symbol}")
        if "<" in details or ">" in details:
            raise ValueError("HTML is not allowed when #html:false is declared")
    if actual_symbols != expected_symbols or len(set(actual_symbols)) != len(ZHUYIN):
        raise ValueError("Anki notes must preserve the unique canonical symbol order")
    if "apps.apple.com" in content or APP_ID in content:
        raise ValueError("Anki import files must remain app-independent")


def make_artifacts() -> dict[str, dict]:
    artifacts = {}
    for locale in DECKS:
        content = render_tsv(locale)
        validate_tsv(locale, content)
        data = content.encode("utf-8")
        artifacts[locale] = {
            "filename": DECKS[locale]["filename"],
            "url": deck_url(locale),
            "content": content,
            "bytes": data,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return artifacts


def metadata_graph(artifacts: dict[str, dict], modified: str) -> dict:
    resources = []
    for locale, artifact in artifacts.items():
        copy = COPY[locale]
        resources.append(
            {
                "@id": f"{canonical(locale)}#deck",
                "@type": "LearningResource",
                "name": copy["title"],
                "description": copy["description"],
                "url": canonical(locale),
                "datePublished": INITIAL_DATE,
                "dateModified": modified,
                "version": "1.0.0",
                "inLanguage": locale,
                "isAccessibleForFree": True,
                "license": LICENSE,
                "learningResourceType": ["Flashcard", "Anki text import"],
                "educationalUse": ["Practice", "Reference"],
                "interactivityType": "active",
                "accessMode": ["textual", "visual"],
                "accessModeSufficient": {
                    "@type": "ItemList",
                    "itemListElement": ["textual"],
                },
                "numberOfItems": len(ZHUYIN),
                "teaches": [
                    "Zhuyin symbol recognition",
                    "Bopomofo to Hanyu Pinyin correspondence",
                    "Broad IPA reference",
                    "Traditional Chinese example words",
                ],
                "audience": [
                    {
                        "@type": "EducationalAudience",
                        "educationalRole": "student",
                    },
                    {
                        "@type": "EducationalAudience",
                        "educationalRole": "teacher",
                    },
                    {
                        "@type": "EducationalAudience",
                        "educationalRole": "parent",
                    },
                ],
                "isBasedOn": DATASET_JSON,
                "citation": [MOE_HANDBOOK, ANKI_MANUAL],
                "creator": {
                    "@type": "Organization",
                    "name": "Lumi Apps - iOS App Guide",
                    "url": SITE,
                },
                "encoding": {
                    "@type": "DataDownload",
                    "name": artifact["filename"],
                    "contentUrl": artifact["url"],
                    "encodingFormat": "text/tab-separated-values",
                    "contentSize": f"{len(artifact['bytes'])} bytes",
                    "sha256": artifact["sha256"],
                },
            }
        )
    return {"@context": "https://schema.org", "@graph": resources}


def validate_metadata(metadata: dict, artifacts: dict[str, dict]) -> None:
    encoded = json.dumps(metadata, ensure_ascii=False)
    for forbidden in ("apps.apple.com", "SoftwareApplication", APP_ID, APP_NAME):
        if forbidden in encoded:
            raise ValueError(f"Anki metadata must remain app-independent: {forbidden}")
    resources = metadata.get("@graph", [])
    if len(resources) != len(DECKS):
        raise ValueError("Anki metadata must describe both language editions")
    by_language = {resource.get("inLanguage"): resource for resource in resources}
    if set(by_language) != set(DECKS):
        raise ValueError("Anki metadata languages must be en and zh-Hant")
    for locale, artifact in artifacts.items():
        resource = by_language[locale]
        if resource.get("@type") != "LearningResource":
            raise ValueError("Anki metadata entries must be LearningResource objects")
        if resource.get("numberOfItems") != len(ZHUYIN):
            raise ValueError("Anki metadata must declare exactly 37 notes")
        if resource.get("license") != LICENSE:
            raise ValueError("Anki metadata must declare CC BY 4.0")
        encoding = resource.get("encoding", {})
        if (
            encoding.get("contentUrl") != artifact["url"]
            or encoding.get("contentSize") != f"{len(artifact['bytes'])} bytes"
            or encoding.get("sha256") != artifact["sha256"]
        ):
            raise ValueError(f"Anki metadata artifact mismatch for {locale}")


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_versioned_metadata(
    path: Path, artifacts: dict[str, dict]
) -> str:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    match = CONTENT_MODIFIED_RE.search(existing)
    prior_date = match.group(1) if match else INITIAL_DATE
    candidate_data = metadata_graph(artifacts, prior_date)
    validate_metadata(candidate_data, artifacts)
    candidate = _json(candidate_data)
    if candidate == existing:
        return prior_date
    updated_data = metadata_graph(artifacts, TODAY)
    validate_metadata(updated_data, artifacts)
    write_text_if_changed(path, _json(updated_data))
    return TODAY


def _schema(
    locale: str,
    artifact: dict,
    page_modified: str,
    app_public: bool,
) -> dict:
    copy = COPY[locale]
    graph = [
        {
            "@type": "WebPage",
            "@id": canonical(locale),
            "name": copy["title"],
            "description": copy["description"],
            "url": canonical(locale),
            "inLanguage": copy["lang"],
            "dateModified": page_modified,
            "mainEntity": {"@id": f"{canonical(locale)}#deck"},
        },
        {
            "@type": "LearningResource",
            "@id": f"{canonical(locale)}#deck",
            "name": copy["title"],
            "description": copy["description"],
            "url": canonical(locale),
            "datePublished": INITIAL_DATE,
            "dateModified": page_modified,
            "inLanguage": locale,
            "isAccessibleForFree": True,
            "license": LICENSE,
            "learningResourceType": ["Flashcard", "Anki text import"],
            "educationalUse": ["Practice", "Reference"],
            "numberOfItems": len(ZHUYIN),
            "isBasedOn": DATASET_JSON,
            "encoding": {
                "@type": "DataDownload",
                "contentUrl": artifact["url"],
                "encodingFormat": "text/tab-separated-values",
                "contentSize": f"{len(artifact['bytes'])} bytes",
                "sha256": artifact["sha256"],
            },
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
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": copy["tools"],
                    "item": f"{SITE}/tools/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": copy["title"],
                    "item": canonical(locale),
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
                "url": appstore_url(APP_KEY, f"iag_anki_{locale.lower()}"),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _preview_rows(locale: str) -> str:
    return "".join(
        "<tr><td class=\"symbol\">{symbol}</td><td>{details}</td></tr>".format(
            symbol=html.escape(record[0]),
            details=html.escape(_details(locale, record)),
        )
        for record in ZHUYIN
    )


def render_page(
    locale: str,
    artifacts: dict[str, dict],
    app_public: bool,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    primary = artifacts[locale]
    alternate = artifacts[other_locale]
    home = f"{SITE}/index.html" if locale == "en" else f"{SITE}/zh-Hant/index.html"
    badges = "".join(
        f"<span>{html.escape(item)}</span>" for item in copy["badges"]
    )
    steps = "".join(f"<li>{html.escape(item)}</li>" for item in copy["steps"])
    included = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["included_items"]
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
                appstore_url(APP_KEY, f"iag_anki_{locale.lower()}"), quote=True
            ),
            cta=html.escape(copy["app_cta"]),
        )
    schema = json.dumps(
        _schema(locale, primary, modified, app_public),
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
<link rel="canonical" href="{html.escape(canonical(locale), quote=True)}">
<link rel="alternate" hreflang="en" href="{html.escape(canonical('en'), quote=True)}">
<link rel="alternate" hreflang="zh-Hant" href="{html.escape(canonical('zh-Hant'), quote=True)}">
<link rel="alternate" hreflang="x-default" href="{html.escape(canonical('en'), quote=True)}">
<link rel="describedby" type="application/ld+json" href="{html.escape(METADATA_URL, quote=True)}">
<link rel="alternate" type="text/tab-separated-values" href="{html.escape(primary['url'], quote=True)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
<meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
<meta property="og:url" content="{html.escape(canonical(locale), quote=True)}">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#172039;--sub:#59657a;--line:#dfe5ef;--paper:#fff;--wash:#f4f7fc;--brand:#3159c9;--soft:#edf3ff;--mint:#e8f8f2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}
a{{color:var(--brand)}}.wrap{{max-width:980px;margin:auto;padding:0 20px}}.top{{background:rgba(255,255,255,.9);border-bottom:1px solid var(--line)}}.nav{{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.nav a{{font-weight:750;text-decoration:none;white-space:nowrap}}.links{{display:flex;gap:18px}}
.hero{{padding-top:64px;padding-bottom:34px}}.eyebrow{{color:var(--brand);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}}h1{{font-size:clamp(32px,7vw,58px);line-height:1.06;letter-spacing:-.04em;margin:10px 0 18px;max-width:900px}}.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:780px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}}
main>.wrap{{margin-bottom:28px}}.panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:clamp(20px,4vw,30px);box-shadow:0 14px 36px rgba(37,55,98,.06)}}h2{{font-size:clamp(23px,4vw,31px);line-height:1.2;margin:0 0 10px}}h3{{margin:0 0 6px}}p{{color:var(--sub);margin:8px 0}}.downloads,.two{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:20px}}.download{{display:flex;flex-direction:column;gap:3px;border:1px solid var(--line);border-radius:16px;padding:18px;text-decoration:none;background:var(--soft)}}.download strong{{font-size:17px}}.download span{{color:var(--sub);font-size:13px}}.button{{display:inline-flex;align-items:center;justify-content:center;background:var(--brand);color:#fff;border-radius:12px;padding:11px 16px;text-decoration:none;font-weight:800;white-space:nowrap}}
.notice{{background:var(--mint);border-radius:14px;padding:14px 16px;color:#315c50}}ol,ul{{padding-left:24px}}li{{margin:8px 0}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:18px;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:var(--paper)}}th,td{{padding:12px 15px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:var(--soft);font-size:13px}}tr:last-child td{{border-bottom:0}}.symbol{{font-size:26px;font-weight:850}}.sources{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}}.sources a{{border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-weight:700;white-space:nowrap}}details{{border-top:1px solid var(--line);padding:12px 0}}summary{{cursor:pointer;font-weight:800}}.app{{background:linear-gradient(135deg,#fff,#edf3ff)}}.footer{{padding:18px 20px 42px;text-align:center;color:var(--sub);font-size:13px}}
@media(max-width:680px){{.downloads,.two{{grid-template-columns:1fr}}.hero{{padding-top:42px}}.sources{{display:grid}}.sources a{{overflow:hidden;text-overflow:ellipsis}}}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{SITE}/tools/">{html.escape(copy['tools'])}</a><a href="{html.escape(canonical(other_locale), quote=True)}">{html.escape(copy['language'])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div></section>
<section class="wrap panel"><h2>{html.escape(copy['download'])}</h2><p>{html.escape(copy['download_text'])}</p><div class="downloads"><a class="download" href="{html.escape(primary['url'], quote=True)}" download><strong>{html.escape(copy['primary'])}</strong><span>{html.escape(copy['file_note'])}</span></a><a class="download" href="{html.escape(alternate['url'], quote=True)}" download><strong>{html.escape(copy['alternate'])}</strong><span>{html.escape(copy['file_note'])}</span></a></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['how'])}</h2><ol>{steps}</ol><p class="notice">{html.escape(copy['repeat'])}</p></article><article class="panel"><h2>{html.escape(copy['included'])}</h2><ul>{included}</ul></article></section>
<section class="wrap panel"><h2>{html.escape(copy['preview'])}</h2><div class="table-wrap"><table><thead><tr><th>{html.escape(copy['symbol'])}</th><th>{html.escape(copy['details'])}</th></tr></thead><tbody>{_preview_rows(locale)}</tbody></table></div></section>
<section class="wrap two"><article class="panel"><h2>{html.escape(copy['source'])}</h2><p>{html.escape(copy['source_text'])}</p><div class="sources"><a href="{DATASET_URL}">{html.escape(copy['dataset'])}</a><a href="{CHART_URL}">{html.escape(copy['chart'])}</a><a href="{ANKI_MANUAL}" rel="noopener">{html.escape(copy['manual'])}</a></div></article><article class="panel"><h2>{html.escape(copy['license'])}</h2><p>{html.escape(copy['license_text'])}</p><a href="{LICENSE}" rel="license noopener">CC BY 4.0</a><h2>{html.escape(copy['privacy'])}</h2><p>{html.escape(copy['privacy_text'])}</p></article></section>
<section class="wrap panel"><h2>{html.escape(copy['faq'])}</h2>{faqs}</section>
<div class="wrap">{app_section}</div>
</main>
<footer class="footer">{html.escape(copy['footer'])}</footer>
</body>
</html>
"""


def update_tools_index(pages: Path = PAGES) -> bool:
    index = pages / "tools" / "index.html"
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    target = f"{SLUG}.html"
    card = (
        '<article class="card third"><h2>'
        f'<a href="{target}">Free Bopomofo Anki Import Deck</a></h2>'
        "<p>All 37 Zhuyin symbols with Pinyin, IPA and examples.</p>"
        "</article>"
    )
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(target)
        + r'">.*?</article>',
        re.DOTALL,
    )
    updated = existing.sub("", text)
    passport = re.search(
        r'<article class="card third"><h2><a href="'
        r'family-travel-observation-passport\.html">.*?</article>',
        updated,
        re.DOTALL,
    )
    if passport:
        position = passport.end()
        updated = updated[:position] + card + updated[position:]
    else:
        marker = '<section class="wrap grid">'
        if marker not in updated:
            raise RuntimeError("tools/index.html is missing its main grid marker")
        updated = updated.replace(marker, marker + card, 1)
    return write_text_if_changed(index, updated)


def render_sitemap(
    page_modified: dict[str, str],
    artifact_modified: str,
) -> str:
    entries = [
        (canonical("en"), page_modified["en"]),
        (canonical("zh-Hant"), page_modified["zh-Hant"]),
        (deck_url("en"), artifact_modified),
        (deck_url("zh-Hant"), artifact_modified),
        (METADATA_URL, artifact_modified),
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
    artifacts = make_artifacts()
    tools = pages / "tools"
    zh_tools = pages / "zh-Hant" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    zh_tools.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts.values():
        write_text_if_changed(
            tools / artifact["filename"],
            artifact["content"],
        )
    metadata_modified = write_versioned_metadata(
        tools / METADATA_FILENAME,
        artifacts,
    )
    public = is_app_public(pages) if app_public is None else app_public
    page_modified = {}
    for locale, directory in (("en", tools), ("zh-Hant", zh_tools)):
        page_modified[locale] = render_versioned_page(
            directory / f"{SLUG}.html",
            lambda modified, locale=locale: render_page(
                locale,
                artifacts,
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    update_tools_index(pages)
    write_text_if_changed(
        pages / "sitemap_anki.xml",
        render_sitemap(page_modified, metadata_modified),
    )
    return [
        canonical("en"),
        canonical("zh-Hant"),
        deck_url("en"),
        deck_url("zh-Hant"),
        METADATA_URL,
        SITEMAP_URL,
    ]


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"Zhuyin Anki resource -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
