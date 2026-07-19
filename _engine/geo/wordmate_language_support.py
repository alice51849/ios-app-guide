#!/usr/bin/env python3
"""Generate a bilingual Wordmate language checker and open support dataset."""

from __future__ import annotations

import csv
import html
import io
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from vocabulary_habit_planner import LANGUAGES  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "wordmate-44-language-support-checker"
DATA_SLUG = "wordmate-language-support"
CONTENT_DATE = "2026-07-14"
TOOL_DATE = "2026-07-15"
OFFICIAL_LISTING = "https://apps.apple.com/app/id6789917808"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
APP_URL = appstore_url("wordmate", "iag_wordmate_language_matrix")
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

COPY = {
    "en": {
        "html_lang": "en",
        "title": "Wordmate 44-Language Support Checker & Open Dataset",
        "description": (
            "Search Wordmate's 44-language catalogue and compare its iPhone, iPad, "
            "Home Screen widget and Apple Watch practice surfaces before buying."
        ),
        "home": f"{SITE}/index.html",
        "tools": f"{SITE}/tools/",
        "switch": "繁體中文",
        "eyebrow": "Purchase-readiness checker · verified source",
        "heading": "Does Wordmate support your language?",
        "lead": (
            "Search the complete 44-language catalogue, then check exactly what the "
            "current App Store listing says is available on each Apple device surface."
        ),
        "verified": "Source checked 14 July 2026",
        "included": "All 44 included in one paid download",
        "private": "No account or tracking",
        "search_label": "Search by language name or code",
        "search_placeholder": "Try Japanese, zh-Hant, Kannada or 泰文",
        "clear": "Clear",
        "count": "{shown} of {total} languages shown",
        "language": "Language",
        "code": "Code",
        "phone": "iPhone / iPad",
        "widget": "Home Screen widget",
        "watch": "Apple Watch",
        "phone_value": "Vocabulary + system TTS",
        "widget_value": "View · Next · Save",
        "watch_value": "Learn · Voice · Save · Progress",
        "downloads_title": "Download the support matrix",
        "downloads_text": (
            "The same 44 records are published as JSON and UTF-8 CSV, with a JSON "
            "Schema and W3C CSVW metadata for validation and reuse."
        ),
        "download_json": "JSON dataset",
        "download_csv": "UTF-8 CSV",
        "download_csvw": "W3C CSVW metadata",
        "download_schema": "JSON Schema",
        "copy_link": "Copy checker link",
        "share": "Share checker",
        "copied": "Checker link copied.",
        "copy_failed": "Copy is unavailable. Copy the page URL from the address bar.",
        "share_cancelled": "Sharing was cancelled.",
        "confirmed_title": "What the published source confirms",
        "confirmed": [
            "Wordmate is a paid download and one purchase includes all 44 languages, every level and every feature.",
            "iPhone and iPad provide vocabulary lessons, natural examples and pronunciation through system text-to-speech.",
            "The interactive Home Screen widget can show a word, move to the next word and save it.",
            "Apple Watch can support learning, system-voice playback, favourites and progress.",
            "The listing says there are no subscriptions, in-app purchases, paid upgrades, required account, third-party ads, tracking or analytics.",
        ],
        "limits_title": "What to verify on your own device",
        "limits": [
            "System-voice availability can vary by OS version, installed voices, language and device.",
            "The widget is for viewing, advancing and saving; the listing assigns pronunciation to iPhone, iPad and Apple Watch.",
            "Price, storefront availability and compatibility can change. Check the current App Store listing before buying.",
            "The CC BY 4.0 license covers this original support-matrix compilation, not Apple or Wordmate trademarks.",
        ],
        "source_title": "Primary source",
        "source_text": (
            "Each record is based on the developer's current Wordmate catalogue and "
            "the live Apple listing. No search-volume, retention or learning-result "
            "claim is inferred from the language list."
        ),
        "source_link": "Read Wordmate's current App Store listing",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "Check whether Wordmate's verified 44-language catalogue contains a "
            "specific language name or code. Return device-surface facts and the "
            "source boundary without ranking languages or promising an installed voice."
        ),
        "webmcp_query_description": (
            "Language name or code, such as Japanese, zh-Hant, Kannada or 泰文."
        ),
        "app_title": "Ready to keep vocabulary close at hand?",
        "app_text": (
            "Wordmate's paid download includes all 44 languages, 14 topics, 84 units, "
            "the interactive widget and Apple Watch. There is no subscription or later "
            "language-pack purchase."
        ),
        "app_cta": "View current price on the App Store",
        "faq_title": "Questions",
        "faqs": [
            (
                "Are all 44 languages included in one purchase?",
                "Yes. The current App Store description says one paid download includes all 44 languages, every level and every feature.",
            ),
            (
                "Does every listed language always have an installed system voice?",
                "Not necessarily. Wordmate uses system text-to-speech, while voice availability can vary with the OS, device and installed voices.",
            ),
            (
                "Is this an independent benchmark of language-learning quality?",
                "No. It is a transparent product-support matrix derived from the current listing and developer catalogue, not a ranking or outcome study.",
            ),
        ],
        "index_title": "Wordmate 44-Language Support Checker",
        "index_description": (
            "Check all 44 languages, device capabilities and downloadable support data "
            "before buying."
        ),
        "footer": (
            "Free checker and CC BY 4.0 data compilation. No account, form submission, "
            "storage, analytics or advertising code."
        ),
    },
    "zh-Hant": {
        "html_lang": "zh-Hant",
        "title": "Wordmate 44 語言支援檢查器與開放資料集",
        "description": (
            "購買前搜尋 Wordmate 的 44 種語言，並比較 iPhone、iPad、主畫面小工具與 Apple Watch 的練習功能。"
        ),
        "home": f"{SITE}/zh-Hant/index.html",
        "tools": f"{SITE}/zh-Hant/tools/",
        "switch": "English",
        "eyebrow": "購買前檢查 · 已核對公開來源",
        "heading": "Wordmate 支援你要學的語言嗎？",
        "lead": "搜尋完整 44 語言目錄，再查看目前 App Store 頁面對各 Apple 裝置功能的明確說明。",
        "verified": "來源核對日期：2026 年 7 月 14 日",
        "included": "一次付費下載包含全部 44 種語言",
        "private": "免帳號、無追蹤",
        "search_label": "依語言名稱或代碼搜尋",
        "search_placeholder": "輸入日文、zh-Hant、Kannada 或泰文",
        "clear": "清除",
        "count": "顯示 {shown}／{total} 種語言",
        "language": "語言",
        "code": "代碼",
        "phone": "iPhone／iPad",
        "widget": "主畫面小工具",
        "watch": "Apple Watch",
        "phone_value": "單字內容＋系統語音",
        "widget_value": "查看 · 下一個 · 收藏",
        "watch_value": "學習 · 語音 · 收藏 · 進度",
        "downloads_title": "下載支援矩陣",
        "downloads_text": "相同 44 筆資料提供 JSON 與 UTF-8 CSV，並附 JSON Schema 與 W3C CSVW metadata，方便驗證與重用。",
        "download_json": "JSON 資料集",
        "download_csv": "UTF-8 CSV",
        "download_csvw": "W3C CSVW metadata",
        "download_schema": "JSON Schema",
        "copy_link": "複製檢查器連結",
        "share": "分享檢查器",
        "copied": "已複製檢查器連結。",
        "copy_failed": "無法自動複製，請從網址列複製本頁連結。",
        "share_cancelled": "已取消分享。",
        "confirmed_title": "公開來源已確認的內容",
        "confirmed": [
            "Wordmate 是付費下載；一次購買包含全部 44 種語言、所有級別與全部功能。",
            "iPhone 與 iPad 提供單字課程、自然例句，以及透過系統文字轉語音播放發音。",
            "主畫面互動小工具可顯示單字、切換下一個單字並收藏。",
            "Apple Watch 可用於學習、播放系統語音、收藏與查看進度。",
            "上架頁面表示無訂閱、無 App 內購、無付費升級、免帳號，也沒有第三方廣告、追蹤或分析。",
        ],
        "limits_title": "仍應在自己的裝置確認",
        "limits": [
            "系統語音是否可用，可能因 OS 版本、已安裝語音、語言與裝置而不同。",
            "小工具用於查看、切換與收藏；上架頁面將發音功能列於 iPhone、iPad 與 Apple Watch。",
            "價格、商店地區供應與相容性可能變動，購買前請查看目前 App Store 頁面。",
            "CC BY 4.0 授權僅涵蓋這份原創支援矩陣彙編，不涵蓋 Apple 或 Wordmate 商標。",
        ],
        "source_title": "主要來源",
        "source_text": (
            "每筆資料依開發者目前的 Wordmate 目錄與 Apple 即時上架頁面整理；不會從語言清單推論搜尋量、留存或學習成果。"
        ),
        "source_link": "查看 Wordmate 目前的 App Store 頁面",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "依語言名稱或代碼查詢 Wordmate 已驗證的 44 語言目錄；回傳各裝置功能與"
            "來源限制，不替語言排名，也不保證裝置已安裝系統語音。"
        ),
        "webmcp_query_description": (
            "語言名稱或代碼，例如日文、zh-Hant、Kannada 或泰文。"
        ),
        "app_title": "準備把單字練習放進日常空檔？",
        "app_text": (
            "Wordmate 一次付費下載包含 44 種語言、14 個主題、84 個單元、主畫面互動小工具與 Apple Watch；沒有訂閱，也不需另外購買語言包。"
        ),
        "app_cta": "前往 App Store 查看目前價格",
        "faq_title": "常見問題",
        "faqs": [
            (
                "一次購買真的包含全部 44 種語言嗎？",
                "是。目前 App Store 說明表示，一次付費下載包含全部 44 種語言、所有級別與全部功能。",
            ),
            (
                "每種語言都一定已安裝可用的系統語音嗎？",
                "不一定。Wordmate 使用系統文字轉語音，而語音是否可用可能受 OS、裝置與已安裝語音影響。",
            ),
            (
                "這是獨立的語言學習品質評比嗎？",
                "不是。這是依目前上架頁面與開發者目錄製作的透明產品支援矩陣，不是排名或成效研究。",
            ),
        ],
        "index_title": "Wordmate 44 語言支援檢查器",
        "index_description": "購買前確認全部 44 種語言、各裝置功能，並下載機器可讀支援資料。",
        "footer": "免費檢查器與 CC BY 4.0 資料彙編。免帳號、不送出表單、不儲存、無分析追蹤或廣告程式。",
    },
}


def canonical(locale: str) -> str:
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def data_url(suffix: str) -> str:
    return f"{SITE}/data/{DATA_SLUG}{suffix}"


def records() -> list[dict[str, object]]:
    return [
        {
            "language_code": code,
            "english_name": english_name,
            "traditional_chinese_name": chinese_name,
            "included_in_paid_download": True,
            "iphone_ipad": "Vocabulary lessons, examples and system TTS",
            "home_screen_widget": "View word, next word and save",
            "apple_watch": "Learn, system voice, save favourites and view progress",
            "voice_availability_note": (
                "System voice availability can vary by OS, device and installed voices."
            ),
            "source_url": OFFICIAL_LISTING,
            "verified_date": CONTENT_DATE,
        }
        for code, english_name, chinese_name in LANGUAGES
    ]


def webmcp_input_schema(locale: str) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "minLength": 1,
                "maxLength": 80,
                "description": COPY[locale]["webmcp_query_description"],
            }
        },
    }


def webmcp_records() -> list[dict[str, object]]:
    return [
        {
            "search": f"{code} {english_name} {chinese_name}".casefold(),
            "record": {
                key: value
                for key, value in record.items()
                if key
                not in {
                    "source_url",
                    "verified_date",
                    "voice_availability_note",
                }
            },
        }
        for (code, english_name, chinese_name), record in zip(
            LANGUAGES,
            records(),
            strict=True,
        )
    ]


def dataset_json() -> str:
    data = {
        "name": "Wordmate 44-Language Support Matrix",
        "description": (
            "Developer-maintained catalogue and device-surface support matrix for "
            "Wordmate, verified against its current App Store listing."
        ),
        "version": CONTENT_DATE,
        "license": LICENSE_URL,
        "source_url": OFFICIAL_LISTING,
        "record_count": len(LANGUAGES),
        "records": records(),
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def dataset_csv() -> bytes:
    fields = list(records()[0])
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in records():
        writer.writerow(
            {
                key: str(value).lower() if isinstance(value, bool) else value
                for key, value in row.items()
            }
        )
    return buffer.getvalue().encode("utf-8")


def dataset_schema() -> str:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": data_url(".schema.json"),
        "title": "Wordmate 44-Language Support Matrix",
        "type": "object",
        "required": [
            "name",
            "description",
            "version",
            "license",
            "source_url",
            "record_count",
            "records",
        ],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "version": {"type": "string", "format": "date"},
            "license": {"type": "string", "format": "uri"},
            "source_url": {"type": "string", "format": "uri"},
            "record_count": {"const": len(LANGUAGES)},
            "records": {
                "type": "array",
                "minItems": len(LANGUAGES),
                "maxItems": len(LANGUAGES),
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(records()[0]),
                    "properties": {
                        "language_code": {
                            "type": "string",
                            "enum": [code for code, _, _ in LANGUAGES],
                        },
                        "english_name": {"type": "string", "minLength": 1},
                        "traditional_chinese_name": {
                            "type": "string",
                            "minLength": 1,
                        },
                        "included_in_paid_download": {"const": True},
                        "iphone_ipad": {"type": "string"},
                        "home_screen_widget": {"type": "string"},
                        "apple_watch": {"type": "string"},
                        "voice_availability_note": {"type": "string"},
                        "source_url": {"const": OFFICIAL_LISTING},
                        "verified_date": {
                            "type": "string",
                            "format": "date",
                        },
                    },
                },
            },
        },
        "additionalProperties": False,
    }
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def csvw_metadata() -> str:
    columns = [
        ("language_code", "string"),
        ("english_name", "string"),
        ("traditional_chinese_name", "string"),
        ("included_in_paid_download", "boolean"),
        ("iphone_ipad", "string"),
        ("home_screen_widget", "string"),
        ("apple_watch", "string"),
        ("voice_availability_note", "string"),
        ("source_url", "anyURI"),
        ("verified_date", "date"),
    ]
    metadata = {
        "@context": [
            "http://www.w3.org/ns/csvw",
            {
                "@language": "en",
                "dc": "http://purl.org/dc/terms/",
            },
        ],
        "url": data_url(".csv"),
        "dc:title": "Wordmate 44-Language Support Matrix",
        "dc:description": (
            "The 44 learning languages and stated device-surface capabilities "
            "published for Wordmate."
        ),
        "dc:license": LICENSE_URL,
        "dc:source": OFFICIAL_LISTING,
        "dialect": {"encoding": "utf-8", "header": True},
        "tableSchema": {
            "primaryKey": "language_code",
            "columns": [
                {
                    "name": name,
                    "titles": name.replace("_", " ").title(),
                    "datatype": datatype,
                    "required": True,
                }
                for name, datatype in columns
            ],
        },
    }
    return json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"


def structured_data(locale: str, copy: dict[str, object]) -> str:
    distributions = [
        ("JSON", ".json"),
        ("text/csv", ".csv"),
        ("application/csvm+json", ".csv-metadata.json"),
        ("application/schema+json", ".schema.json"),
    ]
    faq = [
        {
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        for question, answer in copy["faqs"]
    ]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Dataset",
                "name": "Wordmate 44-Language Support Matrix",
                "description": copy["description"],
                "url": canonical(locale),
                "sameAs": canonical("en"),
                "creator": {
                    "@type": "Organization",
                    "name": "iOS App Guide",
                    "url": SITE,
                },
                "license": LICENSE_URL,
                "isAccessibleForFree": True,
                "inLanguage": ["en", "zh-Hant"],
                "datePublished": CONTENT_DATE,
                "dateModified": CONTENT_DATE,
                "version": CONTENT_DATE,
                "citation": OFFICIAL_LISTING,
                "keywords": [
                    "Wordmate",
                    "vocabulary app",
                    "language support",
                    "Apple Watch language learning",
                    "Home Screen vocabulary widget",
                ],
                "variableMeasured": [
                    "learning language",
                    "iPhone and iPad support",
                    "Home Screen widget support",
                    "Apple Watch support",
                    "purchase inclusion",
                ],
                "distribution": [
                    {
                        "@type": "DataDownload",
                        "encodingFormat": encoding,
                        "contentUrl": data_url(suffix),
                    }
                    for encoding, suffix in distributions
                ],
            },
            {
                "@type": "WebApplication",
                "name": copy["heading"],
                "url": canonical(locale),
                "applicationCategory": "EducationalApplication",
                "operatingSystem": "Any modern browser",
                "browserRequirements": "JavaScript",
                "isAccessibleForFree": True,
                "inLanguage": copy["html_lang"],
                "dateModified": TOOL_DATE,
                "featureList": [
                    "Local filtering of 44 language records",
                    "No account, submission, storage or analytics",
                    "JSON, CSV, JSON Schema and CSVW downloads",
                    "Progressive read-only WebMCP lookup for supporting browsers",
                ],
            },
            {
                "@type": "FAQPage",
                "inLanguage": copy["html_lang"],
                "mainEntity": faq,
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def table_rows(locale: str) -> str:
    copy = COPY[locale]
    rows = []
    for code, english_name, chinese_name in LANGUAGES:
        label = (
            f"{chinese_name} · {english_name}"
            if locale == "zh-Hant"
            else f"{english_name} · {chinese_name}"
        )
        search = f"{code} {english_name} {chinese_name}".lower()
        rows.append(
            f'<tr data-language data-search="{html.escape(search)}">'
            f"<th scope=\"row\">{html.escape(label)}</th>"
            f"<td><code>{html.escape(code)}</code></td>"
            f"<td>{html.escape(copy['phone_value'])}</td>"
            f"<td>{html.escape(copy['widget_value'])}</td>"
            f"<td>{html.escape(copy['watch_value'])}</td></tr>"
        )
    return "\n".join(rows)


def render_page(locale: str, *, show_app_cta: bool) -> str:
    copy = COPY[locale]
    esc = html.escape
    other_locale = "zh-Hant" if locale == "en" else "en"
    confirmed = "".join(f"<li>{esc(item)}</li>" for item in copy["confirmed"])
    limits = "".join(f"<li>{esc(item)}</li>" for item in copy["limits"])
    faq = "".join(
        f"<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>"
        for question, answer in copy["faqs"]
    )
    app_card = ""
    if show_app_cta:
        app_card = f"""
<section class="wrap card app-card">
  <div><p class="eyebrow">{esc(copy["app_title"])}</p><p>{esc(copy["app_text"])}</p></div>
  <a class="primary one-line" href="{esc(APP_URL)}">{esc(copy["app_cta"])}</a>
</section>"""
    count_copy = json.dumps(copy["count"], ensure_ascii=False)
    page = r"""<!doctype html>
<html lang="__HTML_LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESCRIPTION__">
<link rel="canonical" href="__CANONICAL__">
<link rel="alternate" hreflang="en" href="__EN_URL__">
<link rel="alternate" hreflang="zh-Hant" href="__ZH_URL__">
<link rel="alternate" hreflang="x-default" href="__EN_URL__">
__FEEDS__
<meta property="og:type" content="website">
<meta property="og:title" content="__HEADING__">
<meta property="og:description" content="__DESCRIPTION__">
<meta property="og:url" content="__CANONICAL__">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">__SCHEMA__</script>
<style>
:root{--ink:#16201d;--muted:#5d6864;--line:#dce7e2;--paper:#fff;--mint:#e9f8f1;--teal:#126b57;--violet:#6750c9;--shadow:0 22px 70px rgba(27,68,57,.11);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 8% 2%,#e3fff3 0,transparent 31%),radial-gradient(circle at 92% 12%,#eee9ff 0,transparent 34%),#f8fbf9;color:var(--ink);line-height:1.58}a{color:var(--teal)}.wrap{width:min(1180px,calc(100% - 30px));margin:auto}
.top{position:sticky;top:0;z-index:4;border-bottom:1px solid rgba(220,231,226,.84);background:rgba(248,251,249,.92);backdrop-filter:blur(18px)}.nav{min-height:64px;display:flex;align-items:center;justify-content:space-between;gap:12px}.nav a{font-weight:850;text-decoration:none;white-space:nowrap}
.hero{padding:64px 0 28px}.eyebrow{margin:0 0 9px;color:var(--teal);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}h1{margin:0;font-size:clamp(1.15rem,5vw,3.7rem);line-height:1.05;letter-spacing:-.045em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lead{max-width:850px;margin:18px 0 0;color:var(--muted);font-size:clamp(1rem,2vw,1.2rem)}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.badge{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:rgba(255,255,255,.84);font-size:.82rem;font-weight:850;white-space:nowrap}
.card{border:1px solid var(--line);border-radius:28px;background:rgba(255,255,255,.94);box-shadow:var(--shadow);padding:clamp(20px,4vw,32px);margin-bottom:22px}.checker{overflow:hidden}.search-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:end}.search-row label{display:block;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.search-row input{width:100%;min-height:50px;margin-top:6px;border:1px solid #c8d7d0;border-radius:15px;padding:11px 14px;background:#fff;color:var(--ink);font:inherit}
button,.primary,.download{min-height:48px;border-radius:999px;padding:12px 18px;font:inherit;font-weight:900;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}.primary{display:inline-flex;align-items:center;justify-content:center;border:0;background:linear-gradient(135deg,var(--teal),#178c70);color:#fff!important;box-shadow:0 10px 28px rgba(18,107,87,.22)}button,.download{border:1px solid #c8d7d0;background:#fff;color:var(--teal);box-shadow:none}.status{min-height:1.4em;margin:14px 0 0;color:var(--teal);font-weight:850}
.table-wrap{overflow:auto;margin:16px -10px 0;padding:0 10px}table{width:100%;border-collapse:collapse;min-width:980px}th,td{padding:12px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:middle;white-space:nowrap}thead th{font-size:.76rem;text-transform:uppercase;letter-spacing:.055em;color:var(--muted)}tbody th{font-weight:850}code{border-radius:8px;background:#edf4f1;padding:3px 7px}[hidden]{display:none!important}
.two{display:grid;gap:20px}@media(min-width:820px){.two{grid-template-columns:1fr 1fr}}h2{margin:0 0 10px;font-size:clamp(1.35rem,3vw,2rem);letter-spacing:-.025em}.list{padding-left:1.25rem}.list li{margin:.58rem 0}.downloads{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.download{display:inline-flex;align-items:center}.source a{font-weight:850}.app-card{display:grid;gap:18px;align-items:center;background:linear-gradient(135deg,#f2edff,#e7fbf2)}@media(min-width:760px){.app-card{grid-template-columns:1fr auto}}.app-card p{margin:4px 0}details{border-top:1px solid var(--line);padding:14px 0}summary{font-weight:850;cursor:pointer}footer{padding:28px 0 52px;color:var(--muted);font-size:.9rem}
button:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid rgba(103,80,201,.42);outline-offset:3px}@media(max-width:520px){.search-row{grid-template-columns:1fr}.search-row button{width:100%}.card{border-radius:22px}.nav{font-size:.88rem}}
</style>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="__HOME__">iOS App Guide</a><nav><a href="__TOOLS__">__TOOLS_LABEL__</a> · <a href="__SWITCH_URL__">__SWITCH__</a></nav></div></header>
<main>
<section class="hero wrap">
  <p class="eyebrow">__EYEBROW__</p>
  <h1>__HEADING__</h1>
  <p class="lead">__LEAD__</p>
  <div class="badges"><span class="badge">__VERIFIED__</span><span class="badge">__INCLUDED__</span><span class="badge">__PRIVATE__</span></div>
</section>
<section class="wrap card checker">
  <div class="search-row">
    <label for="language-search">__SEARCH_LABEL__<input id="language-search" type="search" autocomplete="off" placeholder="__SEARCH_PLACEHOLDER__"></label>
    <button id="clear-search" type="button">__CLEAR__</button>
  </div>
  <p class="status" id="result-count" role="status"></p>
  <div class="table-wrap"><table>
    <thead><tr><th scope="col">__LANGUAGE__</th><th scope="col">__CODE__</th><th scope="col">__PHONE__</th><th scope="col">__WIDGET__</th><th scope="col">__WATCH__</th></tr></thead>
    <tbody>__ROWS__</tbody>
  </table></div>
</section>
<section class="wrap two">
  <article class="card"><h2>__CONFIRMED_TITLE__</h2><ul class="list">__CONFIRMED__</ul></article>
  <article class="card"><h2>__LIMITS_TITLE__</h2><ul class="list">__LIMITS__</ul></article>
</section>
<section class="wrap card">
  <h2>__DOWNLOADS_TITLE__</h2><p>__DOWNLOADS_TEXT__</p>
  <div class="downloads">
    <a class="download" href="__JSON_URL__" download>__DOWNLOAD_JSON__</a>
    <a class="download" href="__CSV_URL__" download>__DOWNLOAD_CSV__</a>
    <a class="download" href="__CSVW_URL__">__DOWNLOAD_CSVW__</a>
    <a class="download" href="__SCHEMA_URL__">__DOWNLOAD_SCHEMA__</a>
    <button id="copy-link" type="button">__COPY_LINK__</button>
    <button id="share-link" type="button">__SHARE__</button>
  </div>
  <p class="status" id="share-status" role="status"></p>
</section>
<section class="wrap card source"><h2>__SOURCE_TITLE__</h2><p>__SOURCE_TEXT__</p><p><a href="__OFFICIAL_LISTING__">__SOURCE_LINK__</a> · <a href="__WEBMCP_SOURCE_URL__">__WEBMCP_SOURCE__</a> · <a href="__LICENSE_URL__">CC BY 4.0</a></p></section>
__APP_CARD__
<section class="wrap card"><h2>__FAQ_TITLE__</h2>__FAQ__</section>
</main>
<footer><div class="wrap">__FOOTER__</div></footer>
<script>
const input=document.getElementById("language-search");
const rows=[...document.querySelectorAll("[data-language]")];
const count=document.getElementById("result-count");
const status=document.getElementById("share-status");
const countPattern=__COUNT_COPY__;
const WEBMCP_INPUT_SCHEMA=__WEBMCP_INPUT_SCHEMA__;
const WEBMCP_RECORDS=__WEBMCP_RECORDS__;
const WEBMCP_TOOL_DESCRIPTION=__WEBMCP_DESCRIPTION__;
const WORDMATE_APP_STORE_URL=__APP_STORE_URL__;
function update(){
  const query=input.value.trim().toLocaleLowerCase();
  let shown=0;
  for(const row of rows){const visible=!query||row.dataset.search.includes(query);row.hidden=!visible;if(visible)shown++;}
  count.textContent=countPattern.replace("{shown}",String(shown)).replace("{total}",String(rows.length));
}
function syncUrlFilters(){
  const url=new URL(location.href);
  const query=input.value.trim();
  if(query)url.searchParams.set("q",query);else url.searchParams.delete("q");
  history.replaceState(null,"",`${url.pathname}${url.search}${url.hash}`);
}
function applyUrlFilters(){
  const query=new URLSearchParams(location.search).get("q");
  if(query!==null)input.value=query.slice(0,80);
  update();
}
function currentUrl(){return location.href;}
async function registerWebMcp(){
  if(!document.modelContext?.registerTool)return;
  await document.modelContext.registerTool({
    name:"check_wordmate_language_support",
    description:WEBMCP_TOOL_DESCRIPTION,
    inputSchema:WEBMCP_INPUT_SCHEMA,
    annotations:{readOnlyHint:true,untrustedContentHint:false},
    execute:async(value)=>{
      if(value===null||typeof value!=="object"||Array.isArray(value))throw new TypeError("WebMCP input must be an object.");
      if(typeof value.query!=="string")throw new TypeError("query must be a string.");
      const query=value.query.trim();
      if(!query)throw new RangeError("query must not be empty.");
      if(query.length>80)throw new RangeError("query exceeds 80 characters.");
      const matches=WEBMCP_RECORDS.filter(item=>item.search.includes(query.toLocaleLowerCase())).map(item=>item.record);
      return JSON.stringify({
        result_type:"wordmate_language_support_matches",
        verified_date:"__CONTENT_DATE__",
        match_count:matches.length,
        matches,
        source_url:"__OFFICIAL_LISTING__",
        voice_boundary:"System voice availability can vary by OS, device and installed voices.",
        wordmate_app_store_url:WORDMATE_APP_STORE_URL||null
      });
    }
  });
}
async function copyLink(){
  try{await navigator.clipboard.writeText(currentUrl());status.textContent="__COPIED__";}
  catch(error){status.textContent="__COPY_FAILED__";}
}
async function shareLink(){
  if(navigator.share){try{await navigator.share({title:document.title,url:currentUrl()});return;}catch(error){if(error&&error.name==="AbortError"){status.textContent="__SHARE_CANCELLED__";return;}}}
  await copyLink();
}
input.addEventListener("input",()=>{update();syncUrlFilters();});
document.getElementById("clear-search").addEventListener("click",()=>{input.value="";update();syncUrlFilters();input.focus();});
document.getElementById("copy-link").addEventListener("click",copyLink);
document.getElementById("share-link").addEventListener("click",shareLink);
applyUrlFilters();
registerWebMcp().catch(error=>console.error("WebMCP tool registration failed.",error));
</script>
</body>
</html>
"""
    replacements = {
        "__HTML_LANG__": esc(copy["html_lang"]),
        "__TITLE__": esc(copy["title"]),
        "__DESCRIPTION__": esc(copy["description"]),
        "__CANONICAL__": canonical(locale),
        "__EN_URL__": canonical("en"),
        "__ZH_URL__": canonical("zh-Hant"),
        "__FEEDS__": feed_discovery_links(),
        "__SCHEMA__": structured_data(locale, copy),
        "__HOME__": esc(copy["home"]),
        "__TOOLS__": esc(copy["tools"]),
        "__TOOLS_LABEL__": esc("免費工具" if locale == "zh-Hant" else "Free tools"),
        "__SWITCH_URL__": canonical(other_locale),
        "__SWITCH__": esc(copy["switch"]),
        "__EYEBROW__": esc(copy["eyebrow"]),
        "__HEADING__": esc(copy["heading"]),
        "__LEAD__": esc(copy["lead"]),
        "__VERIFIED__": esc(copy["verified"]),
        "__INCLUDED__": esc(copy["included"]),
        "__PRIVATE__": esc(copy["private"]),
        "__SEARCH_LABEL__": esc(copy["search_label"]),
        "__SEARCH_PLACEHOLDER__": esc(copy["search_placeholder"]),
        "__CLEAR__": esc(copy["clear"]),
        "__LANGUAGE__": esc(copy["language"]),
        "__CODE__": esc(copy["code"]),
        "__PHONE__": esc(copy["phone"]),
        "__WIDGET__": esc(copy["widget"]),
        "__WATCH__": esc(copy["watch"]),
        "__ROWS__": table_rows(locale),
        "__CONFIRMED_TITLE__": esc(copy["confirmed_title"]),
        "__CONFIRMED__": confirmed,
        "__LIMITS_TITLE__": esc(copy["limits_title"]),
        "__LIMITS__": limits,
        "__DOWNLOADS_TITLE__": esc(copy["downloads_title"]),
        "__DOWNLOADS_TEXT__": esc(copy["downloads_text"]),
        "__JSON_URL__": data_url(".json"),
        "__CSV_URL__": data_url(".csv"),
        "__CSVW_URL__": data_url(".csv-metadata.json"),
        "__SCHEMA_URL__": data_url(".schema.json"),
        "__DOWNLOAD_JSON__": esc(copy["download_json"]),
        "__DOWNLOAD_CSV__": esc(copy["download_csv"]),
        "__DOWNLOAD_CSVW__": esc(copy["download_csvw"]),
        "__DOWNLOAD_SCHEMA__": esc(copy["download_schema"]),
        "__COPY_LINK__": esc(copy["copy_link"]),
        "__SHARE__": esc(copy["share"]),
        "__SOURCE_TITLE__": esc(copy["source_title"]),
        "__SOURCE_TEXT__": esc(copy["source_text"]),
        "__OFFICIAL_LISTING__": OFFICIAL_LISTING,
        "__SOURCE_LINK__": esc(copy["source_link"]),
        "__WEBMCP_SOURCE_URL__": WEBMCP_SOURCE,
        "__WEBMCP_SOURCE__": esc(copy["webmcp_source"]),
        "__LICENSE_URL__": LICENSE_URL,
        "__APP_CARD__": app_card,
        "__FAQ_TITLE__": esc(copy["faq_title"]),
        "__FAQ__": faq,
        "__FOOTER__": esc(copy["footer"]),
        "__COUNT_COPY__": count_copy,
        "__COPIED__": esc(copy["copied"]),
        "__COPY_FAILED__": esc(copy["copy_failed"]),
        "__SHARE_CANCELLED__": esc(copy["share_cancelled"]),
        "__WEBMCP_INPUT_SCHEMA__": json.dumps(
            webmcp_input_schema(locale),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_RECORDS__": json.dumps(
            webmcp_records(),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_DESCRIPTION__": json.dumps(
            copy["webmcp_description"],
            ensure_ascii=False,
        ),
        "__APP_STORE_URL__": json.dumps(
            APP_URL if show_app_cta else "",
        ),
        "__CONTENT_DATE__": CONTENT_DATE,
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    unresolved = sorted(set(re.findall(r"__[A-Z][A-Z_]+__", page)))
    if unresolved:
        raise ValueError(f"Unresolved template markers: {unresolved}")
    return page


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def _update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    copy = COPY[locale]
    card = (
        f'<article class="card third" data-tool="{SLUG}">'
        f'<h2><a href="{SLUG}.html">{html.escape(copy["index_title"])}</a></h2>'
        f'<p>{html.escape(copy["index_description"])}</p></article>'
    )
    pattern = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>',
        re.S,
    )
    if pattern.search(text):
        updated = pattern.sub(card, text, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in text:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = text.replace(marker, marker + card, 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def build(pages: Path = PAGES, *, show_app_cta: bool) -> list[str]:
    data_dir = pages / "data"
    write_text_if_changed(data_dir / f"{DATA_SLUG}.json", dataset_json())
    write_bytes_if_changed(data_dir / f"{DATA_SLUG}.csv", dataset_csv())
    write_text_if_changed(
        data_dir / f"{DATA_SLUG}.schema.json",
        dataset_schema(),
    )
    write_text_if_changed(
        data_dir / f"{DATA_SLUG}.csv-metadata.json",
        csvw_metadata(),
    )
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, show_app_cta=show_app_cta),
        )
        outputs.append(canonical(locale))
    _update_one_index(pages / "tools" / "index.html", "en")
    _update_one_index(
        pages / "zh-Hant" / "tools" / "index.html",
        "zh-Hant",
    )
    return outputs


def main() -> None:
    show_app_cta = "wordmate" in live_app_keys(
        APPSTORE,
        str(PAGES),
        refresh=False,
    )
    for output in build(show_app_cta=show_app_cta):
        print(f"wordmate language support -> {output}")
    print(f"dataset JSON -> {data_url('.json')}")
    print(f"dataset CSV -> {data_url('.csv')}")
    print(f"dataset CSVW -> {data_url('.csv-metadata.json')}")
    print(f"dataset schema -> {data_url('.schema.json')}")
    print(f"tools sitemap -> {write_tools_sitemap()} urls")


if __name__ == "__main__":
    main()
