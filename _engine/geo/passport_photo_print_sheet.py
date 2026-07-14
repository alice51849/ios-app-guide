#!/usr/bin/env python3
"""Generate a bilingual, local-only passport photo print-sheet maker."""

from __future__ import annotations

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
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "private-passport-photo-print-sheet-maker"
CONTENT_DATE = "2026-07-14"
US_SOURCE = "https://travel.state.gov/en/passports/apply/help/photos.html"
UK_SOURCE = "https://www.gov.uk/photos-for-passports/photo-requirements"
CANADA_SOURCE = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
    "canadian-passports/photos.html"
)
APP_URL = appstore_url("snapport")

PRESETS = {
    "us": {
        "width_mm": 50.8,
        "height_mm": 50.8,
        "source": US_SOURCE,
    },
    "uk": {
        "width_mm": 35.0,
        "height_mm": 45.0,
        "source": UK_SOURCE,
    },
    "canada": {
        "width_mm": 50.0,
        "height_mm": 70.0,
        "source": CANADA_SOURCE,
    },
}
PAPERS = {
    "4x6": {"width_mm": 101.6, "height_mm": 152.4},
    "a4": {"width_mm": 210.0, "height_mm": 297.0},
    "letter": {"width_mm": 215.9, "height_mm": 279.4},
}

COPY = {
    "en": {
        "title": "Private Passport Photo Print Sheet Maker | 4×6, A4 & Letter",
        "description": (
            "Arrange a local photo into an exact-size 300 DPI 4×6, A4 or Letter "
            "print sheet with non-overprinting cut marks where white space allows. "
            "Nothing is uploaded, saved or analyzed."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · local-only · 300 DPI",
        "heading": "Private passport photo print sheet maker",
        "lead": (
            "Choose a verified final-size preset or custom dimensions, keep the "
            "photo inside this browser tab and export a multi-copy PNG with cut marks "
            "that stay outside every photo."
        ),
        "privacy": "Your photo stays in this tab; no upload, account or saved file",
        "scope": "Print layout only; not a biometric or acceptance check",
        "builder": "Build the print sheet",
        "photo_label": "Choose a local photo",
        "photo_help": (
            "The browser decodes the selected image in memory. Closing or reloading "
            "the page clears it."
        ),
        "preset_label": "Final photo size",
        "preset_options": {
            "us": "U.S. passport · 2×2 in",
            "uk": "UK printed passport · 35×45 mm",
            "canada": "Canada printed passport · 50×70 mm",
            "custom": "Custom dimensions",
        },
        "custom_width": "Custom width (mm)",
        "custom_height": "Custom height (mm)",
        "paper_label": "Paper",
        "paper_options": {
            "4x6": "4×6 in photo paper",
            "a4": "A4",
            "letter": "US Letter",
        },
        "orientation_label": "Orientation",
        "orientation_options": {
            "auto": "Auto · fit the most copies",
            "portrait": "Portrait",
            "landscape": "Landscape",
        },
        "margin_label": "Outer margin (mm)",
        "gap_label": "Gap between copies (mm)",
        "zoom_label": "Photo zoom",
        "horizontal_label": "Horizontal position",
        "vertical_label": "Vertical position",
        "reset": "Reset photo position",
        "download": "Download 300 DPI PNG",
        "print": "Open exact-size print view",
        "share": "Share tool",
        "summary_initial": (
            "U.S. 2×2 in on 4×6 in paper: 6 copies, 600×600 px each, "
            "1200×1800 px sheet."
        ),
        "placeholder": "LOCAL PHOTO",
        "choose_status": "Choose a photo, or use the placeholder to inspect the layout.",
        "loading_status": "Loading the new photo locally…",
        "loaded_status": "Photo loaded locally. Nothing was uploaded.",
        "invalid_status": "Choose an image file that this browser can decode.",
        "large_status": "Choose an image smaller than 25 MB.",
        "layout_error": "The selected photo does not fit with these margins and gaps.",
        "export_error_status": (
            "The PNG could not be created. Try a smaller photo or reload this page."
        ),
        "downloaded_status": "The 300 DPI PNG is ready in your downloads.",
        "popup_status": "Allow pop-ups to open the exact-size print view.",
        "print_status": (
            "Print at 100% or Actual Size. Disable Fit to Page and verify one photo "
            "with a ruler before using the sheet."
        ),
        "shared_status": "Share sheet opened.",
        "cancelled_status": "Sharing was cancelled.",
        "copied_status": "Tool link copied.",
        "copy_failed_status": "Copy was unavailable. Use this link:",
        "copies_word": "copies",
        "portrait_word": "portrait",
        "landscape_word": "landscape",
        "sheet_word": "sheet",
        "each_word": "each",
        "cut_marks_ready": "cut marks outside photos",
        "cut_marks_unavailable": "full-bleed layout · no cut-mark gutter",
        "warning_title": "Before printing",
        "warnings": [
            "Use 100% or Actual Size; printer auto-fit changes the physical dimensions.",
            "Measure one printed copy with a ruler before cutting the full sheet.",
            "Cut marks are drawn only in white margins or gaps, never over a photo. A full-bleed six-copy 2×2 layout has no waste area for marks.",
            "This tool does not check pose, head size, eye line, background, lighting, recency or digital alteration rules.",
            "UK printed photos must meet a professional standard, have no border and not be cut down from a larger picture.",
            "Canada requires passport photos to be taken in person by a commercial photographer or studio; use its preset as a dimension reference only.",
        ],
        "related_title": "Related free resources",
        "related_links": [
            ("Check passport photo dimensions by country", "passport-photo-size-guide.html"),
            ("Turn an iPhone image into a PDF", "image-to-pdf-iphone.html"),
        ],
        "app_title": "Need cropping, face guides or export formats on iPhone?",
        "app_text": (
            "Snapport is an optional paid-download iPhone tool for passport, visa and "
            "ID templates, face-alignment guides, custom sizes and print layouts. "
            "It works on device with no account or subscription. This free sheet maker "
            "remains complete without it, and neither tool can guarantee acceptance."
        ),
        "app_cta": "See Snapport on the App Store",
        "sources": "Official dimensions and important limits",
        "source_labels": [
            "U.S. Department of State: passport photo requirements",
            "GOV.UK: printed passport photo requirements",
            "Government of Canada: passport photo requirements",
        ],
        "source_note": (
            "Presets encode final physical dimensions only. Always read the current "
            "official page for the exact application route before taking, editing, "
            "printing or submitting a photo."
        ),
        "faq": [
            (
                "Does my photo upload to this website?",
                "No. The selected file is decoded in this browser tab and drawn to a local canvas. There is no network request, account, storage or analytics.",
            ),
            (
                "Does the PNG guarantee the printed size?",
                "No. The PNG has the correct 300 DPI pixel dimensions, but printer software can rescale it. Print at 100% or Actual Size and measure a copy.",
            ),
            (
                "Does this check whether a passport photo will be accepted?",
                "No. It only arranges copies. Official rules can also cover pose, face size, background, expression, lighting, recency, paper and whether editing or home printing is allowed.",
            ),
            (
                "Why are UK and Canada marked with warnings?",
                "Their official paper-photo instructions include professional-standard print or photographer requirements that a home sheet cannot certify. The presets are dimension references, not submission approval.",
            ),
        ],
        "index_title": "Private Passport Photo Print Sheet Maker",
        "index_description": (
            "Keep a photo local and arrange exact-size copies on 4×6, A4 or Letter "
            "at 300 DPI with non-overprinting cut marks where space allows."
        ),
    },
    "zh-Hant": {
        "title": "私密護照照片排版工具｜4×6、A4 與 Letter",
        "description": (
            "照片只留在瀏覽器分頁內，依精確尺寸排成 300 DPI 的 4×6、A4 或 "
            "Letter 多張版；裁切標記只畫在可用留白，不碰照片；不上傳、不儲存、不分析。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 僅在本機 · 300 DPI",
        "heading": "私密護照照片排版工具",
        "lead": (
            "選擇已核實的成品尺寸或自訂毫米數，照片只在目前分頁處理，"
            "再匯出多張 PNG；裁切標記全都留在照片外。"
        ),
        "privacy": "照片只留在目前分頁；不上傳、不登入、不儲存",
        "scope": "只做列印排版；不檢查生物特徵或保證受理",
        "builder": "建立列印排版",
        "photo_label": "選擇本機照片",
        "photo_help": "瀏覽器只在記憶體解碼照片；關閉或重新載入頁面就會清除。",
        "preset_label": "成品照片尺寸",
        "preset_options": {
            "us": "美國護照 · 2×2 吋",
            "uk": "英國紙本護照 · 35×45 mm",
            "canada": "加拿大紙本護照 · 50×70 mm",
            "custom": "自訂尺寸",
        },
        "custom_width": "自訂寬度（mm）",
        "custom_height": "自訂高度（mm）",
        "paper_label": "紙張",
        "paper_options": {
            "4x6": "4×6 吋相紙",
            "a4": "A4",
            "letter": "美規 Letter",
        },
        "orientation_label": "方向",
        "orientation_options": {
            "auto": "自動 · 排入最多張",
            "portrait": "直向",
            "landscape": "橫向",
        },
        "margin_label": "外側留白（mm）",
        "gap_label": "照片間距（mm）",
        "zoom_label": "照片縮放",
        "horizontal_label": "水平位置",
        "vertical_label": "垂直位置",
        "reset": "重設照片位置",
        "download": "下載 300 DPI PNG",
        "print": "開啟精確尺寸列印頁",
        "share": "分享工具",
        "summary_initial": (
            "美國 2×2 吋照片排在 4×6 吋相紙：6 張；每張 600×600 px，"
            "整版 1200×1800 px。"
        ),
        "placeholder": "本機照片",
        "choose_status": "可先查看預留版面，或選擇照片完成排版。",
        "loading_status": "正在本機載入新照片…",
        "loaded_status": "照片已在本機載入，沒有上傳。",
        "invalid_status": "請選擇目前瀏覽器能解碼的圖片檔。",
        "large_status": "請選擇小於 25 MB 的圖片。",
        "layout_error": "目前的照片尺寸、留白與間距無法排進所選紙張。",
        "export_error_status": "無法建立 PNG，請改用較小的照片，或重新載入此頁面。",
        "downloaded_status": "300 DPI PNG 已送到下載項目。",
        "popup_status": "請允許彈出式視窗，以開啟精確尺寸列印頁。",
        "print_status": (
            "請用 100% 或「實際大小」列印，關閉「符合頁面」，並先用尺量一張。"
        ),
        "shared_status": "已開啟分享表單。",
        "cancelled_status": "已取消分享。",
        "copied_status": "已複製工具連結。",
        "copy_failed_status": "無法複製，請使用此連結：",
        "copies_word": "張",
        "portrait_word": "直向",
        "landscape_word": "橫向",
        "sheet_word": "整版",
        "each_word": "每張",
        "cut_marks_ready": "裁切標記不碰照片",
        "cut_marks_unavailable": "滿版排版 · 沒有裁切標記留白",
        "warning_title": "列印前務必確認",
        "warnings": [
            "請用 100% 或「實際大小」列印；印表機自動縮放會改變成品尺寸。",
            "裁切整版前，先用尺量其中一張。",
            "裁切標記只畫在白色留白或照片間距，絕不蓋到照片。六張 2×2 吋滿版排版沒有可畫標記的廢邊。",
            "本工具不檢查姿勢、頭部比例、眼線、背景、光線、拍攝日期或數位修改規定。",
            "英國紙本護照照片的列印品質須達專業標準、無邊框，且不可由較大照片裁切而成。",
            "加拿大要求護照照片由商業攝影師或攝影工作室當面拍攝；此處預設只能當尺寸參考。",
        ],
        "related_title": "相關免費資源",
        "related_links": [
            ("查詢各國護照照片尺寸", "passport-photo-size-guide.html"),
            ("將 iPhone 圖片轉成 PDF", "image-to-pdf-iphone.html"),
        ],
        "app_title": "需要 iPhone 裁切、臉部定位線或更多匯出格式？",
        "app_text": (
            "Snapport 是選用的付費下載 iPhone 工具，提供護照、簽證與證件模板、"
            "臉部定位線、自訂尺寸及列印排版；裝置端處理、免帳號、無訂閱。"
            "本頁免費排版工具不需 App 也能完整使用，兩者都不保證受理。"
        ),
        "app_cta": "在 App Store 查看 Snapport",
        "sources": "官方尺寸與重要限制",
        "source_labels": [
            "美國國務院：護照照片規定",
            "英國 GOV.UK：紙本護照照片規定",
            "加拿大政府：護照照片規定",
        ],
        "source_note": (
            "預設只代表最終實體尺寸。拍攝、編修、列印或送件前，"
            "務必依申請方式閱讀最新官方頁面。"
        ),
        "faq": [
            (
                "照片會上傳到這個網站嗎？",
                "不會。所選檔案只在目前瀏覽器分頁解碼並畫到本機 canvas；沒有網路請求、帳號、儲存或分析。",
            ),
            (
                "下載的 PNG 能保證列印尺寸嗎？",
                "不能。PNG 具正確的 300 DPI 像素尺寸，但列印軟體仍可能縮放；請選 100% 或「實際大小」並用尺確認。",
            ),
            (
                "這能檢查護照照片是否會受理嗎？",
                "不能。本工具只排列多張照片；官方還可能規定姿勢、臉部比例、背景、表情、光線、拍攝日期、紙張及是否允許編修或自行列印。",
            ),
            (
                "為什麼英國與加拿大預設有特別警告？",
                "兩地官方紙本規定包含專業品質列印或攝影師要求，本機排版無法證明符合；預設只提供尺寸參考，不代表送件核准。",
            ),
        ],
        "index_title": "私密護照照片排版工具",
        "index_description": (
            "照片不上傳，依精確尺寸排成 300 DPI 的 4×6、A4 或 Letter "
            "多張版；有留白時提供不壓到照片的裁切標記。"
        ),
    },
}

STYLE = r"""
:root{--ink:#171b24;--muted:#616978;--line:#dce1eb;--paper:#fff;--bg:#eef3f8;--navy:#18365f;--blue:#2d6da3;--mint:#dff4ec;--warn:#fff4d8;--shadow:0 20px 55px rgba(29,49,78,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#dce7f2 100%);color:var(--ink);line-height:1.6}
a{color:#18558b}.wrap{width:min(1180px,100% - 30px);margin:auto}.top{position:sticky;top:0;z-index:8;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}
.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:18px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.nav-links{display:flex;gap:16px}.nav-links a{color:var(--muted);font-size:14px}
.hero{padding:58px 0 25px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--navy);white-space:nowrap}
h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6.2vw,64px);line-height:1.04;letter-spacing:-.035em;margin:.28em 0 .24em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.3vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.trust{display:flex;gap:9px;flex-wrap:wrap;margin-top:22px}.badge.scope{color:#684c1d;background:#fff9ea}
.workspace{background:rgba(255,255,255,.98);border:1px solid var(--line);border-radius:30px;padding:clamp(18px,4vw,34px);box-shadow:var(--shadow);margin:20px auto 34px}.workspace h2,.content-card h2,.cta-card h2{font-size:clamp(24px,4vw,34px);line-height:1.15;margin:0;white-space:nowrap;overflow-x:auto}
.builder-grid{display:grid;grid-template-columns:minmax(260px,390px) minmax(0,1fr);gap:24px;margin-top:24px}.controls{display:grid;gap:13px;align-content:start}.field{border:1px solid var(--line);background:#f8fafc;border-radius:18px;padding:13px}.field label,.field-title{display:block;color:var(--navy);font-size:13px;font-weight:850;margin-bottom:7px;white-space:nowrap;overflow-x:auto}
input,select,button{font:inherit}input[type=file],input[type=number],select{width:100%;min-height:46px;border:1px solid #cbd3df;border-radius:13px;background:#fff;color:var(--ink);padding:10px 12px}input[type=range]{width:100%;accent-color:var(--blue)}input:disabled{opacity:.48;background:#eef1f5}
.help,.status,.summary{color:var(--muted);font-size:13px;margin:7px 0 0;white-space:nowrap;overflow-x:auto}.summary{background:var(--mint);border:1px solid #bfe2d6;border-radius:16px;padding:12px;color:#215a4a;font-weight:760}.status{min-height:1.5em}.actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:4px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--navy),var(--blue));color:#fff;text-decoration:none;font-weight:850;padding:11px 16px;box-shadow:0 8px 20px rgba(24,54,95,.18);cursor:pointer;white-space:nowrap}.button.secondary{background:#fff;color:var(--navy);border:1px solid var(--line);box-shadow:none}.button:disabled{opacity:.45;cursor:not-allowed;box-shadow:none}
.preview{min-width:0;display:grid;align-content:start;gap:12px}.canvas-shell{display:flex;justify-content:center;align-items:flex-start;min-height:420px;padding:16px;border:1px solid var(--line);border-radius:22px;background:repeating-linear-gradient(45deg,#e7ebf0,#e7ebf0 12px,#f3f5f8 12px,#f3f5f8 24px);overflow:auto}canvas{display:block;max-width:100%;height:auto;max-height:720px;background:#fff;box-shadow:0 10px 28px rgba(20,34,52,.18)}
.content-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-bottom:30px}.content-card,.cta-card,.sources{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:24px;padding:clamp(18px,3vw,28px)}.content-card.warn{background:var(--warn);border-color:#ead49d}.content-card.full{grid-column:1/-1}.content-card p,.content-card li,.cta-card p,.sources p,.sources li,.faq-list p,.faq-list summary{white-space:nowrap;overflow-x:auto}.content-card ul,.sources ul{padding-left:22px}.content-card li{margin:8px 0}.cta-card{margin:0 auto 30px;background:linear-gradient(135deg,#f9fbff,#e8f1f8)}.cta-card .button{display:inline-flex;margin-top:6px}.sources{margin:0 auto 45px}.sources h2{margin-top:0}.sources li{margin:8px 0}.faq-list{display:grid;gap:9px;margin-top:20px}.faq-list details{border:1px solid var(--line);border-radius:15px;padding:11px 14px;background:#fff}.faq-list summary{font-weight:820;cursor:pointer}.faq-list p{color:var(--muted)}
@media(max-width:820px){.builder-grid{grid-template-columns:1fr}.canvas-shell{min-height:320px}.content-grid{grid-template-columns:1fr}.content-card.full{grid-column:auto}.nav-links{gap:10px}.nav-links a{font-size:12px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.actions,.summary,.status,.content-grid,.cta-card,.sources{display:none!important}body,.workspace,.canvas-shell{background:#fff!important;margin:0!important;padding:0!important;border:0!important;box-shadow:none!important}.wrap,.workspace,.builder-grid,.preview{width:100%!important;max-width:none!important;display:block!important}.canvas-shell{min-height:0!important;overflow:visible!important}canvas{max-width:100%!important;max-height:none!important;box-shadow:none!important}}
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def _options(values: dict[str, str]) -> str:
    return "".join(
        f'<option value="{html.escape(key, quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def render_page(locale: str, show_app_cta: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    url = canonical(locale)
    other_locale = "zh-Hant" if locale == "en" else "en"
    alternate = canonical(other_locale)
    home_prefix = "" if locale == "en" else f"{locale}/"
    home = f"{SITE}/{home_prefix}index.html"
    tools = f"{SITE}/{home_prefix}tools/index.html"
    app_campaign = f"{APP_URL}?ct=iag_passport_print_sheet_{locale.lower()}"
    app_cta = ""
    if show_app_cta:
        app_cta = (
            f'<section class="cta-card wrap"><h2>{html.escape(t["app_title"])}</h2>'
            f'<p>{html.escape(t["app_text"])}</p><a class="button" '
            f'href="{html.escape(app_campaign, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></section>'
        )
    schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Any",
        "browserRequirements": (
            "JavaScript and local image decoding; no server upload is used"
        ),
        "isAccessibleForFree": True,
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
        },
        "featureList": [
            "Local-only photo processing",
            "300 DPI 4x6, A4 and US Letter layouts",
            "U.S., UK and Canada final-size references",
            "Custom millimetre dimensions",
            "Accessible zoom and position controls",
            "PNG export with non-overprinting cut marks where white space allows",
            "Exact-size print view",
        ],
        "citation": [US_SOURCE, UK_SOURCE, CANADA_SOURCE],
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in t["faq"]
        ],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": home},
            {"@type": "ListItem", "position": 2, "name": t["tools"], "item": tools},
            {"@type": "ListItem", "position": 3, "name": t["heading"], "item": url},
        ],
    }
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in t["warnings"])
    sources = "".join(
        (
            f'<li><a href="{source}" rel="noopener noreferrer">'
            f"{html.escape(label)}</a></li>"
        )
        for source, label in zip(
            (US_SOURCE, UK_SOURCE, CANADA_SOURCE),
            t["source_labels"],
            strict=True,
        )
    )
    faq = "".join(
        (
            f"<details><summary>{html.escape(question)}</summary>"
            f"<p>{html.escape(answer)}</p></details>"
        )
        for question, answer in t["faq"]
    )
    related = "".join(
        f'<li><a href="{html.escape(href, quote=True)}">{html.escape(label)}</a></li>'
        for label, href in t["related_links"]
    )
    client_copy = {
        key: t[key]
        for key in (
            "placeholder",
            "choose_status",
            "loading_status",
            "loaded_status",
            "invalid_status",
            "large_status",
            "layout_error",
            "export_error_status",
            "downloaded_status",
            "popup_status",
            "print_status",
            "shared_status",
            "cancelled_status",
            "copied_status",
            "copy_failed_status",
            "copies_word",
            "portrait_word",
            "landscape_word",
            "sheet_word",
            "each_word",
            "cut_marks_ready",
            "cut_marks_unavailable",
            "heading",
            "lead",
        )
    }
    copy_json = json.dumps(client_copy, ensure_ascii=False).replace("</", "<\\/")
    preset_json = json.dumps(PRESETS, ensure_ascii=False)
    paper_json = json.dumps(PAPERS, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="{locale}" href="{url}">
<link rel="alternate" hreflang="{other_locale}" href="{alternate}">
<link rel="alternate" hreflang="x-default" href="{canonical("en")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["heading"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<style>{STYLE}</style>
{json_script(schema)}
{json_script(faq_schema)}
{json_script(breadcrumb)}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="nav-links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="trust"><span class="badge">{html.escape(t["privacy"])}</span><span class="badge scope">{html.escape(t["scope"])}</span></div></section>
<section class="workspace wrap" id="generator"><h2>{html.escape(t["builder"])}</h2><div class="builder-grid"><div class="controls">
<div class="field"><label for="photo-file">{html.escape(t["photo_label"])}</label><input id="photo-file" type="file" accept="image/*"><p class="help">{html.escape(t["photo_help"])}</p></div>
<div class="field"><label for="preset">{html.escape(t["preset_label"])}</label><select id="preset">{_options(t["preset_options"])}</select></div>
<div class="field"><label for="custom-width">{html.escape(t["custom_width"])}</label><input id="custom-width" type="number" min="20" max="100" step="0.1" value="35" disabled><label for="custom-height">{html.escape(t["custom_height"])}</label><input id="custom-height" type="number" min="20" max="100" step="0.1" value="45" disabled></div>
<div class="field"><label for="paper">{html.escape(t["paper_label"])}</label><select id="paper">{_options(t["paper_options"])}</select><label for="orientation">{html.escape(t["orientation_label"])}</label><select id="orientation">{_options(t["orientation_options"])}</select></div>
<div class="field"><label for="margin">{html.escape(t["margin_label"])}</label><input id="margin" type="number" min="0" max="20" step="0.5" value="0"><label for="gap">{html.escape(t["gap_label"])}</label><input id="gap" type="number" min="0" max="10" step="0.5" value="0"></div>
<div class="field"><label for="zoom">{html.escape(t["zoom_label"])}</label><input id="zoom" type="range" min="100" max="220" value="100"><label for="horizontal">{html.escape(t["horizontal_label"])}</label><input id="horizontal" type="range" min="-100" max="100" value="0"><label for="vertical">{html.escape(t["vertical_label"])}</label><input id="vertical" type="range" min="-100" max="100" value="0"></div>
<div class="actions"><button class="button secondary" id="reset-position" type="button">{html.escape(t["reset"])}</button><button class="button" id="download-sheet" type="button" disabled>{html.escape(t["download"])}</button><button class="button secondary" id="print-sheet" type="button" disabled>{html.escape(t["print"])}</button><button class="button secondary" id="share-tool" type="button">{html.escape(t["share"])}</button></div>
<p class="summary" id="summary">{html.escape(t["summary_initial"])}</p><p class="status" id="status" aria-live="polite">{html.escape(t["choose_status"])}</p>
</div><div class="preview"><div class="canvas-shell"><canvas id="sheet" width="1200" height="1800" aria-label="{html.escape(t["heading"])}"></canvas></div></div></div></section>
<section class="content-grid wrap"><article class="content-card warn full"><h2>{html.escape(t["warning_title"])}</h2><ul>{warnings}</ul></article><article class="content-card full"><h2>{html.escape(t["related_title"])}</h2><ul>{related}</ul></article></section>
{app_cta}
<section class="sources wrap"><h2>{html.escape(t["sources"])}</h2><ul>{sources}</ul><p>{html.escape(t["source_note"])}</p><div class="faq-list">{faq}</div></section>
</main>
<script>
const COPY={copy_json};
const PRESETS={preset_json};
const PAPERS={paper_json};
const DPI=300;
const MM_PER_INCH=25.4;
const MAX_FILE_BYTES=25*1024*1024;
const canvas=document.getElementById("sheet");
const context=canvas.getContext("2d",{{alpha:false}});
const photoInput=document.getElementById("photo-file");
const presetInput=document.getElementById("preset");
const customWidth=document.getElementById("custom-width");
const customHeight=document.getElementById("custom-height");
const paperInput=document.getElementById("paper");
const orientationInput=document.getElementById("orientation");
const marginInput=document.getElementById("margin");
const gapInput=document.getElementById("gap");
const zoomInput=document.getElementById("zoom");
const horizontalInput=document.getElementById("horizontal");
const verticalInput=document.getElementById("vertical");
const downloadButton=document.getElementById("download-sheet");
const printButton=document.getElementById("print-sheet");
const summary=document.getElementById("summary");
const status=document.getElementById("status");
let localImage=null;
let localImageURL="";
let photoLoadToken=0;
let currentLayout=null;

function clamp(value,min,max){{return Math.min(max,Math.max(min,value));}}
function mmToPx(value){{return Math.round(value/MM_PER_INCH*DPI);}}
function numberValue(input,min,max,fallback){{
  const parsed=Number(input.value);
  return Number.isFinite(parsed)?clamp(parsed,min,max):fallback;
}}
function photoSize(){{
  if(presetInput.value!=="custom")return PRESETS[presetInput.value];
  return {{
    width_mm:numberValue(customWidth,20,100,35),
    height_mm:numberValue(customHeight,20,100,45)
  }};
}}
function candidate(paperWidth,paperHeight,photoWidth,photoHeight,margin,gap,name){{
  const usableWidth=paperWidth-margin*2;
  const usableHeight=paperHeight-margin*2;
  const columns=Math.floor((usableWidth+gap)/(photoWidth+gap));
  const rows=Math.floor((usableHeight+gap)/(photoHeight+gap));
  return {{paperWidth,paperHeight,photoWidth,photoHeight,margin,gap,columns,rows,count:Math.max(0,columns)*Math.max(0,rows),name}};
}}
function chooseLayout(){{
  const photo=photoSize();
  const paper=PAPERS[paperInput.value];
  const margin=numberValue(marginInput,0,20,0);
  const gap=numberValue(gapInput,0,10,0);
  const portrait=candidate(paper.width_mm,paper.height_mm,photo.width_mm,photo.height_mm,margin,gap,"portrait");
  const landscape=candidate(paper.height_mm,paper.width_mm,photo.width_mm,photo.height_mm,margin,gap,"landscape");
  if(orientationInput.value==="portrait")return portrait;
  if(orientationInput.value==="landscape")return landscape;
  return landscape.count>portrait.count?landscape:portrait;
}}
function pixelSafeLayout(layout){{
  const paperWidthPx=mmToPx(layout.paperWidth);
  const paperHeightPx=mmToPx(layout.paperHeight);
  const photoWidthPx=mmToPx(layout.photoWidth);
  const photoHeightPx=mmToPx(layout.photoHeight);
  const marginPx=mmToPx(layout.margin);
  const gapPx=mmToPx(layout.gap);
  const usableWidthPx=Math.max(0,paperWidthPx-marginPx*2);
  const usableHeightPx=Math.max(0,paperHeightPx-marginPx*2);
  const pixelColumns=Math.floor(
    (usableWidthPx+gapPx)/(photoWidthPx+gapPx)
  );
  const pixelRows=Math.floor(
    (usableHeightPx+gapPx)/(photoHeightPx+gapPx)
  );
  const columns=Math.max(0,Math.min(layout.columns,pixelColumns));
  const rows=Math.max(0,Math.min(layout.rows,pixelRows));
  return {{
    ...layout,
    paperWidthPx,
    paperHeightPx,
    photoWidthPx,
    photoHeightPx,
    marginPx,
    gapPx,
    columns,
    rows,
    count:columns*rows
  }};
}}
function drawPlaceholder(x,y,width,height){{
  const gradient=context.createLinearGradient(x,y,x+width,y+height);
  gradient.addColorStop(0,"#dfeaf4");
  gradient.addColorStop(1,"#f7fafc");
  context.fillStyle=gradient;
  context.fillRect(x,y,width,height);
  context.fillStyle="#41617f";
  context.font=`700 ${{Math.max(16,Math.round(Math.min(width,height)*.09))}}px -apple-system,BlinkMacSystemFont,sans-serif`;
  context.textAlign="center";
  context.textBaseline="middle";
  context.fillText(COPY.placeholder,x+width/2,y+height/2);
}}
function drawPhoto(x,y,width,height){{
  if(!localImage){{drawPlaceholder(x,y,width,height);return;}}
  const zoom=numberValue(zoomInput,100,220,100)/100;
  const base=Math.max(width/localImage.naturalWidth,height/localImage.naturalHeight);
  const scale=base*zoom;
  const drawWidth=localImage.naturalWidth*scale;
  const drawHeight=localImage.naturalHeight*scale;
  const overflowX=Math.max(0,drawWidth-width);
  const overflowY=Math.max(0,drawHeight-height);
  const shiftX=numberValue(horizontalInput,-100,100,0)/100*overflowX/2;
  const shiftY=numberValue(verticalInput,-100,100,0)/100*overflowY/2;
  const drawX=x+(width-drawWidth)/2+shiftX;
  const drawY=y+(height-drawHeight)/2+shiftY;
  context.save();
  context.beginPath();
  context.rect(x,y,width,height);
  context.clip();
  context.drawImage(localImage,drawX,drawY,drawWidth,drawHeight);
  context.restore();
}}
function drawCutMarks(layout,startX,startY,photoWidth,photoHeight,gap){{
  const lineWidth=Math.max(1,Math.round(DPI/300));
  const offset=Math.ceil(lineWidth/2)+1;
  const maxLength=mmToPx(4);
  let segmentCount=0;
  function mark(x,y,available,dx,dy){{
    const length=Math.floor(Math.min(maxLength,available-offset));
    if(length<2)return;
    const nearX=x+dx*offset;
    const nearY=y+dy*offset;
    context.moveTo(nearX,nearY);
    context.lineTo(nearX+dx*length,nearY+dy*length);
    segmentCount++;
  }}
  context.save();
  context.strokeStyle="#333";
  context.lineWidth=lineWidth;
  context.lineCap="butt";
  context.beginPath();
  for(let row=0;row<layout.rows;row++){{
    for(let column=0;column<layout.columns;column++){{
      const x=startX+column*(photoWidth+gap);
      const y=startY+row*(photoHeight+gap);
      const topSpace=row===0?y:gap/2;
      const bottomSpace=row===layout.rows-1?canvas.height-(y+photoHeight):gap/2;
      const leftSpace=column===0?x:gap/2;
      const rightSpace=column===layout.columns-1?canvas.width-(x+photoWidth):gap/2;
      mark(x,y,topSpace,0,-1);
      mark(x+photoWidth,y,topSpace,0,-1);
      mark(x,y+photoHeight,bottomSpace,0,1);
      mark(x+photoWidth,y+photoHeight,bottomSpace,0,1);
      mark(x,y,leftSpace,-1,0);
      mark(x,y+photoHeight,leftSpace,-1,0);
      mark(x+photoWidth,y,rightSpace,1,0);
      mark(x+photoWidth,y+photoHeight,rightSpace,1,0);
    }}
  }}
  if(segmentCount)context.stroke();
  context.restore();
  return segmentCount;
}}
function render(){{
  const layout=pixelSafeLayout(chooseLayout());
  currentLayout=layout;
  if(layout.count<1){{
    summary.textContent=COPY.layout_error;
    status.textContent=COPY.layout_error;
    canvas.width=800;canvas.height=500;
    context.fillStyle="#fff";context.fillRect(0,0,canvas.width,canvas.height);
    context.fillStyle="#7a4f00";context.font="700 24px sans-serif";
    context.textAlign="center";context.fillText(COPY.layout_error,canvas.width/2,canvas.height/2);
    return;
  }}
  canvas.width=layout.paperWidthPx;
  canvas.height=layout.paperHeightPx;
  context.fillStyle="#fff";context.fillRect(0,0,canvas.width,canvas.height);
  const photoWidth=layout.photoWidthPx;
  const photoHeight=layout.photoHeightPx;
  const gap=layout.gapPx;
  const blockWidth=layout.columns*photoWidth+(layout.columns-1)*gap;
  const blockHeight=layout.rows*photoHeight+(layout.rows-1)*gap;
  const startX=Math.round((canvas.width-blockWidth)/2);
  const startY=Math.round((canvas.height-blockHeight)/2);
  for(let row=0;row<layout.rows;row++){{
    for(let column=0;column<layout.columns;column++){{
      const x=startX+column*(photoWidth+gap);
      const y=startY+row*(photoHeight+gap);
      drawPhoto(x,y,photoWidth,photoHeight);
    }}
  }}
  const cutMarkCount=drawCutMarks(
    layout,startX,startY,photoWidth,photoHeight,gap
  );
  const orientation=layout.name==="portrait"?COPY.portrait_word:COPY.landscape_word;
  const cutMarkStatus=cutMarkCount?COPY.cut_marks_ready:COPY.cut_marks_unavailable;
  summary.textContent=`${{layout.count}} ${{COPY.copies_word}} · ${{orientation}} · ${{COPY.each_word}} ${{layout.photoWidth.toFixed(1)}}×${{layout.photoHeight.toFixed(1)}} mm (${{photoWidth}}×${{photoHeight}} px) · ${{COPY.sheet_word}} ${{layout.paperWidth.toFixed(1)}}×${{layout.paperHeight.toFixed(1)}} mm (${{canvas.width}}×${{canvas.height}} px) · ${{cutMarkStatus}}`;
}}
function resetPosition(){{
  zoomInput.value="100";
  horizontalInput.value="0";
  verticalInput.value="0";
  render();
}}
function safeName(){{
  return `passport-photo-sheet-${{presetInput.value}}-${{paperInput.value}}-300dpi.png`;
}}

function crc32(bytes){{
  let crc=0xffffffff;
  for(const byte of bytes){{
    crc^=byte;
    for(let bit=0;bit<8;bit++){{
      crc=(crc>>>1)^((crc&1)?0xedb88320:0);
    }}
  }}
  return (crc^0xffffffff)>>>0;
}}
function pngDensityChunk(dpi){{
  const chunk=new Uint8Array(21);
  const view=new DataView(chunk.buffer);
  const pixelsPerMetre=Math.round(dpi/0.0254);
  view.setUint32(0,9,false);
  chunk.set([112,72,89,115],4);
  view.setUint32(8,pixelsPerMetre,false);
  view.setUint32(12,pixelsPerMetre,false);
  chunk[16]=1;
  view.setUint32(17,crc32(chunk.slice(4,17)),false);
  return chunk;
}}
async function pngWithDensity(blob,dpi){{
  const bytes=new Uint8Array(await blob.arrayBuffer());
  const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  const signature=[137,80,78,71,13,10,26,10];
  const validSignature=signature.every((byte,index)=>bytes[index]===byte);
  const validHeader=bytes.length>=33&&String.fromCharCode(...bytes.slice(12,16))==="IHDR";
  if(!validSignature||!validHeader)throw new Error("Canvas did not return a valid PNG");
  const insertAt=8+12+view.getUint32(8,false);
  return new Blob(
    [bytes.slice(0,insertAt),pngDensityChunk(dpi),bytes.slice(insertAt)],
    {{type:"image/png"}}
  );
}}
function setExportEnabled(enabled){{
  downloadButton.disabled=!enabled;
  printButton.disabled=!enabled;
}}
function clearLocalImage(){{
  if(localImageURL)URL.revokeObjectURL(localImageURL);
  localImageURL="";
  localImage=null;
}}

photoInput.addEventListener("change",()=>{{
  const loadToken=++photoLoadToken;
  setExportEnabled(false);
  const file=photoInput.files&&photoInput.files[0];
  clearLocalImage();
  render();
  if(!file){{status.textContent=COPY.choose_status;return;}}
  if(!file.type.startsWith("image/")){{status.textContent=COPY.invalid_status;return;}}
  if(file.size>MAX_FILE_BYTES){{status.textContent=COPY.large_status;return;}}
  status.textContent=COPY.loading_status;
  const nextURL=URL.createObjectURL(file);
  const nextImage=new Image();
  nextImage.onload=()=>{{
    if(loadToken!==photoLoadToken){{URL.revokeObjectURL(nextURL);return;}}
    localImageURL=nextURL;
    localImage=nextImage;
    status.textContent=COPY.loaded_status;
    render();
    setExportEnabled(true);
  }};
  nextImage.onerror=()=>{{
    URL.revokeObjectURL(nextURL);
    if(loadToken!==photoLoadToken)return;
    status.textContent=COPY.invalid_status;
  }};
  nextImage.src=nextURL;
}});
presetInput.addEventListener("change",()=>{{
  const custom=presetInput.value==="custom";
  customWidth.disabled=!custom;
  customHeight.disabled=!custom;
  render();
}});
for(const input of [customWidth,customHeight,paperInput,orientationInput,marginInput,gapInput,zoomInput,horizontalInput,verticalInput]){{
  input.addEventListener("input",render);
  input.addEventListener("change",render);
}}
document.getElementById("reset-position").addEventListener("click",resetPosition);
downloadButton.addEventListener("click",()=>{{
  if(downloadButton.disabled||!localImage||!currentLayout||currentLayout.count<1)return;
  canvas.toBlob(async blob=>{{
    if(!blob)return;
    try{{
      const png=await pngWithDensity(blob,DPI);
      const url=URL.createObjectURL(png);
      const anchor=document.createElement("a");
      anchor.href=url;anchor.download=safeName();
      document.body.appendChild(anchor);anchor.click();anchor.remove();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
      status.textContent=COPY.downloaded_status;
    }}catch(error){{
      status.textContent=COPY.export_error_status;
    }}
  }},"image/png");
}});
printButton.addEventListener("click",()=>{{
  if(printButton.disabled||!localImage||!currentLayout||currentLayout.count<1)return;
  const popup=window.open("","_blank");
  if(!popup){{status.textContent=COPY.popup_status;return;}}
  const data=canvas.toDataURL("image/png");
  popup.document.write(`<!DOCTYPE html><html><head><title>${{COPY.heading}}</title><style>@page{{size:${{currentLayout.paperWidth}}mm ${{currentLayout.paperHeight}}mm;margin:0}}html,body{{margin:0;padding:0;width:${{currentLayout.paperWidth}}mm;height:${{currentLayout.paperHeight}}mm}}img{{display:block;width:${{currentLayout.paperWidth}}mm;height:${{currentLayout.paperHeight}}mm}}</style></head><body><img src="${{data}}" alt=""></body></html>`);
  popup.document.close();
  popup.focus();
  setTimeout(()=>popup.print(),350);
  status.textContent=COPY.print_status;
}});
document.getElementById("share-tool").addEventListener("click",async()=>{{
  const payload={{title:COPY.heading,text:COPY.lead,url:window.location.href}};
  if(navigator.share){{
    try{{await navigator.share(payload);status.textContent=COPY.shared_status;return;}}
    catch(error){{if(error&&error.name==="AbortError"){{status.textContent=COPY.cancelled_status;return;}}}}
  }}
  try{{await navigator.clipboard.writeText(window.location.href);status.textContent=COPY.copied_status;}}
  catch(error){{status.textContent=`${{COPY.copy_failed_status}} ${{window.location.href}}`;}}
}});
window.addEventListener("beforeunload",()=>{{if(localImageURL)URL.revokeObjectURL(localImageURL);}});
render();
</script>
</body>
</html>
"""


def _index_card(locale: str) -> str:
    t = COPY[locale]
    return (
        '<article class="card third"><h2><a href="'
        f'{SLUG}.html">{html.escape(t["index_title"])}</a></h2>'
        f'<p>{html.escape(t["index_description"])}</p></article>'
    )


def _update_one_index(index: Path, locale: str) -> bool:
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    card = _index_card(locale)
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(f"{SLUG}.html")
        + r'">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    anchor = re.compile(
        r'(<article class="card third"><h2><a href="'
        r'passport-photo-size-guide\.html">.*?</article>)',
        re.S,
    )
    if anchor.search(updated):
        updated = anchor.sub(r"\1" + card, updated, count=1)
    else:
        grid_marker = '<section class="wrap grid">'
        if grid_marker not in updated:
            raise RuntimeError(f"{index} is missing its tools grid")
        updated = updated.replace(grid_marker, grid_marker + card, 1)
    if updated == text:
        return False
    index.write_text(updated, encoding="utf-8")
    return True


def update_tools_indexes(pages: Path = PAGES) -> int:
    changed = _update_one_index(pages / "tools" / "index.html", "en")
    changed += _update_one_index(
        pages / "zh-Hant" / "tools" / "index.html",
        "zh-Hant",
    )
    return changed


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def build(pages: Path = PAGES, *, show_app_cta: bool) -> list[str]:
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        target = pages / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text_if_changed(target, render_page(locale, show_app_cta))
        outputs.append(canonical(locale))
    update_tools_indexes(pages)
    return outputs


def main() -> None:
    show_app_cta = "snapport" in live_app_keys(
        APPSTORE,
        str(PAGES),
        refresh=False,
    )
    outputs = build(show_app_cta=show_app_cta)
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"passport photo print sheet -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
