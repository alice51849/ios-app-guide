#!/usr/bin/env python3
"""Build a bilingual, print-ready family travel observation passport OER."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import json
import os
import re
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from family_travel_dataset import (
    APP_ID,
    APP_KEY,
    APP_NAME,
    SITE,
    RO_CRATE_URL,
    is_app_public,
    load_dataset,
    render_versioned_page,
    write_text_if_changed,
)
from gen_calculator import write_tools_sitemap
from videogen.registry import appstore_url


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
SLUG = "family-travel-observation-passport"
INITIAL_DATE = "2026-07-11"
TODAY = dt.date.today().isoformat()
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
DATASET_PAGE = f"{SITE}/data/family-travel-missions.html"
API_DOCS = f"{SITE}/api/v1/family-travel-missions/"
METADATA_URL = f"{SITE}/tools/{SLUG}.metadata.json"
OPDS2_URL = f"{SITE}/opds/{SLUG}.json"
OPDS1_URL = f"{SITE}/opds/{SLUG}.xml"
PDF_SIZES = {"a4": A4, "letter": LETTER}
CONTENT_MODIFIED_RE = re.compile(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"')

rl_config.invariant = 1
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


COPY = {
    "en": {
        "lang": "en",
        "title": "Free Family Travel Observation Passport",
        "description": (
            "Download a privacy-first, print-ready 14-page family travel observation "
            "passport for 12 settings, with A4 and US Letter PDFs."
        ),
        "eyebrow": "Open educational resource · CC BY 4.0",
        "lead": (
            "Turn waiting, transport and place-based noticing into calm family conversation "
            "without names, destinations, photos, scores or tracking."
        ),
        "badges": (
            "12 travel settings",
            "A4 + US Letter",
            "No personal details",
            "English + 繁體中文",
        ),
        "language": "繁體中文",
        "tools": "Free tools",
        "start": "Open the printable passport",
        "download": "Download the ready-to-print PDF",
        "download_intro": (
            "Choose the paper size your printer uses. Both files contain the same "
            "14-page resource with selectable text."
        ),
        "a4": "A4 PDF",
        "letter": "US Letter PDF",
        "html_print": "Print this web version",
        "metadata": "Machine-readable OER metadata",
        "ro_crate": "RO-Crate research object",
        "opds2": "OPDS 2.0 catalog",
        "opds1": "OPDS 1.2 catalog",
        "inside": "What is inside",
        "inside_text": (
            "One adult guide, one page for each of 12 common travel settings and one "
            "reuse-and-attribution page. Every setting offers three participation choices."
        ),
        "safety": "Adult-led safety boundary",
        "safety_text": (
            "Use a page only while safely stationary or seated and only when the supervising "
            "adult permits it. Current local, carrier, crew, driver, security, venue, ranger "
            "and staff instructions always come first. The driver never reads, answers or "
            "operates the passport while driving."
        ),
        "privacy": "Private by design",
        "privacy_text": (
            "The passport asks for no name, age, date, destination, precise location, room "
            "number, route, photo, audio, itinerary or completion record. Keep optional notes "
            "private and do not add or post identifying details."
        ),
        "respect": "Observe places, not private people",
        "respect_text": (
            "Use public signs, objects, shapes, sounds and approved displays as prompts. "
            "Do not record, describe or photograph private people, restricted information or "
            "anything a local rule says to leave alone."
        ),
        "choices": "Three choices, never levels",
        "choices_text": (
            "Watch or point, notice or describe, or plan or create. Anyone may switch, "
            "combine or skip them; they are not age bands, tests or ability rankings."
        ),
        "how": "How to use the passport",
        "how_items": (
            "Print the A4 or US Letter file, or print this web page.",
            "The supervising adult chooses a safe, stationary moment.",
            "Pick any one of the three prompts on the current setting page.",
            "Talk, point, imagine or make a private note; skip freely and stop immediately when asked.",
        ),
        "page": "Passport page",
        "optional": "Optional prompt",
        "note": "Optional note or drawing — do not add names, dates or precise locations",
        "skip": "Skip this page freely. Safety, comfort and current instructions always come first.",
        "cover_title": "Family Travel Observation Passport",
        "cover_subtitle": "A private, adult-guided noticing booklet for 12 travel settings",
        "cover_notice": (
            "No names · No destinations · No photos · No scores · No completion tracking"
        ),
        "closing": "Reuse, adapt and share",
        "closing_text": (
            "This original passport may be printed, adapted and shared under CC BY 4.0. "
            "Credit “Family Travel Observation Passport — Lumi Apps / iOS App Guide,” link "
            "to the resource page and state whether changes were made."
        ),
        "attribution": (
            "Family Travel Observation Passport | Lumi Apps - iOS App Guide | CC BY 4.0"
        ),
        "changes": "Adaptations must identify changes.",
        "source": "Open source data and safety references",
        "source_text": (
            "The prompts are generated from the citable Family Travel Mission Taxonomy. "
            "Official links support conservative safety boundaries but do not endorse this resource."
        ),
        "source_titles": (
            "TSA: filming and photos at a security checkpoint",
            "FAA: child safety seat tips",
            "NHTSA: car seats and booster seats",
            "U.S. DOT: air-travel tips for families",
            "U.S. National Park Service: Junior Ranger",
            "U.S. FTC: children's privacy",
        ),
        "dataset": "Family Travel Mission Taxonomy",
        "api": "Versioned static API",
        "license": "Creative Commons Attribution 4.0",
        "faq": "Family and educator questions",
        "faq_items": (
            (
                "Does a child have to finish every page?",
                "No. Every page and prompt is optional, and there is no score or completion target.",
            ),
            (
                "Does the passport collect or upload anything?",
                "No. The HTML and PDFs contain no form, account, upload, saved profile or tracking request.",
            ),
            (
                "Can a prompt override a travel rule?",
                "No. The supervising adult and current local, operator, venue and staff instructions always take priority.",
            ),
            (
                "May I adapt it for a class or family group?",
                "Yes. CC BY 4.0 permits adaptation and sharing with attribution and a note describing changes.",
            ),
        ),
        "app_title": "Optional digital travel layer",
        "app_text": (
            "Lumi Trip Planet offers an optional on-device activity layer. The complete "
            "passport, PDFs, metadata and open data remain free and independent."
        ),
        "app_cta": "View Lumi Trip Planet on the App Store",
        "footer": "Independent, openly licensed family travel resource from iOS App Guide.",
        "learning_use": "Family-guided observation and bilingual travel vocabulary practice",
        "keywords": (
            "family travel observation passport, printable travel activity, privacy-first "
            "travel worksheet, open educational resource"
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "免費親子旅行觀察護照",
        "description": (
            "下載隱私優先、可直接列印的 14 頁親子旅行觀察護照，涵蓋 12 種情境，"
            "提供 A4 與 US Letter PDF。"
        ),
        "eyebrow": "開放教育資源 · CC BY 4.0",
        "lead": (
            "把等待、交通與在地觀察變成平靜的親子對話；不填姓名、目的地，"
            "不拍照、不評分、不追蹤。"
        ),
        "badges": (
            "12 種旅行情境",
            "A4 ＋ US Letter",
            "不填任何個資",
            "English ＋ 繁體中文",
        ),
        "language": "English",
        "tools": "免費工具",
        "start": "開啟可列印護照",
        "download": "下載可直接列印的 PDF",
        "download_intro": (
            "依印表機紙張選擇版本；兩份檔案都包含相同的 14 頁內容，文字可選取。"
        ),
        "a4": "A4 PDF",
        "letter": "US Letter PDF",
        "html_print": "列印目前網頁版本",
        "metadata": "機器可讀 OER 中繼資料",
        "ro_crate": "RO-Crate 研究物件",
        "opds2": "OPDS 2.0 資源目錄",
        "opds1": "OPDS 1.2 資源目錄",
        "inside": "護照包含什麼",
        "inside_text": (
            "一頁大人指南、12 種常見旅行情境各一頁，以及一頁再利用與來源標示；"
            "每種情境都有三種參與選擇。"
        ),
        "safety": "由大人主導的安全界線",
        "safety_text": (
            "只有在安全原地或坐好、且陪同大人允許時才使用。當下的當地法規、"
            "運輸業者、機組、駕駛、安檢、場館、巡護員與工作人員指示永遠優先；"
            "車輛行駛時，駕駛絕不閱讀、回答或操作這本護照。"
        ),
        "privacy": "從設計保護隱私",
        "privacy_text": (
            "護照不要求姓名、年齡、日期、目的地、精確位置、房號、路線、照片、"
            "聲音、行程或完成紀錄。選用筆記請留在家中，不要加入或公開可識別資訊。"
        ),
        "respect": "觀察地方，不觀察私人個體",
        "respect_text": (
            "只用公共標誌、物件、形狀、聲音與場館允許的展示作為提示；不要記錄、"
            "描述或拍攝私人個體、受限制資訊，或任何當地規則要求不要碰觸的內容。"
        ),
        "choices": "三種選擇，絕不是分級",
        "choices_text": (
            "可選擇看一看／指出來、觀察／描述、規劃／創作；任何人都能切換、"
            "混用或跳過。這些不是年齡層、測驗或能力排名。"
        ),
        "how": "如何使用這本護照",
        "how_items": (
            "列印 A4、US Letter PDF，或直接列印目前網頁。",
            "由陪同大人選擇安全且已原地停下的時刻。",
            "在目前情境頁的三個提示中任選一個。",
            "可以聊天、指出、想像或留下私密筆記；隨時跳過，收到指示就立刻停止。",
        ),
        "page": "護照頁",
        "optional": "選用提示",
        "note": "選用筆記或圖畫——不要加入姓名、日期或精確位置",
        "skip": "可自由跳過本頁；安全、舒適與當下指示永遠優先。",
        "cover_title": "親子旅行觀察護照",
        "cover_subtitle": "給 12 種旅行情境使用的私密、大人陪同觀察手冊",
        "cover_notice": "不填姓名 · 不填目的地 · 不拍照 · 不評分 · 不追蹤完成度",
        "closing": "再利用、改編與分享",
        "closing_text": (
            "本原創護照採 CC BY 4.0，可列印、改編與分享。請標示「親子旅行觀察護照"
            "——Lumi Apps／iOS App Guide」、連回資源頁，並說明是否做過修改。"
        ),
        "attribution": "親子旅行觀察護照 | Lumi Apps - iOS App Guide | CC BY 4.0",
        "changes": "改編版本必須註明修改內容。",
        "source": "開放來源資料與安全參考",
        "source_text": (
            "所有提示都由可引用的《親子旅行任務分類資料集》生成；官方連結只支援"
            "保守安全界線，不代表官方為本資源背書。"
        ),
        "source_titles": (
            "美國運輸安全管理局：安檢區攝影規則",
            "美國聯邦航空總署：兒童安全座椅提示",
            "美國國家公路交通安全管理局：汽車座椅與增高座椅",
            "美國運輸部：家庭航空旅行提示",
            "美國國家公園管理局：少年巡護員",
            "美國聯邦貿易委員會：兒童隱私",
        ),
        "dataset": "親子旅行任務分類資料集",
        "api": "版本化靜態 API",
        "license": "Creative Commons 姓名標示 4.0",
        "faq": "家庭與教育工作者常見問題",
        "faq_items": (
            ("孩子一定要完成每一頁嗎？", "不用。每頁與每個提示都可自由跳過，沒有分數或完成目標。"),
            ("護照會收集或上傳資料嗎？", "不會。HTML 與 PDF 沒有表單、帳號、上傳、儲存個人檔案或追蹤請求。"),
            ("提示可以凌駕旅行規則嗎？", "不可以。陪同大人與當下的當地、運輸業者、場館及工作人員指示永遠優先。"),
            ("可以改成班級或家庭團體版本嗎？", "可以。CC BY 4.0 允許在保留來源標示並說明修改內容後改編與分享。"),
        ),
        "app_title": "選用數位旅行層",
        "app_text": (
            "Lumi Trip Planet 提供選用的裝置端活動層；完整護照、PDF、中繼資料與"
            "開放資料仍維持免費且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi Trip Planet",
        "footer": "由 iOS App Guide 提供的獨立開放授權親子旅行資源。",
        "learning_use": "家庭陪同觀察與英繁雙語旅行詞彙練習",
        "keywords": "親子旅行觀察護照, 可列印旅行活動, 隱私優先旅行學習單, 開放教育資源",
    },
}


STYLE = """
:root{--ink:#18202f;--sub:#586477;--paper:#fffdf8;--line:#ded6c7;--wash:#f5f1e8;--blue:#245b78;--gold:#b47a27;--mint:#e8f5ef}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#f9f6ef,#edf4f6);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}
a{color:var(--blue)}.wrap{width:min(1040px,calc(100% - 32px));margin:auto}.top{padding:15px 0;border-bottom:1px solid var(--line);background:#ffffffed;position:sticky;top:0;z-index:3}.nav{display:flex;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:780}
.hero{padding:56px 0 30px}.eyebrow{color:var(--gold);font-size:13px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.hero h1{font-size:clamp(2.25rem,6vw,4.35rem);line-height:1.03;letter-spacing:-.04em;margin:.18em 0}.lead{max-width:800px;color:var(--sub);font-size:clamp(1.05rem,2.5vw,1.28rem)}
.badges,.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:22px}.badge{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 12px;font-size:13px;font-weight:750;white-space:nowrap}.button{display:inline-block;border:0;border-radius:999px;padding:12px 18px;background:linear-gradient(135deg,var(--blue),#347d91);color:#fff;text-decoration:none;font-weight:820;cursor:pointer;white-space:nowrap}.button.secondary{background:#fff;color:var(--blue);border:1px solid #b8cbd2}
.screen-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin:18px auto 38px}.panel{grid-column:span 6;background:#fff;border:1px solid var(--line);border-radius:22px;padding:23px;box-shadow:0 10px 28px #2632480d}.panel.wide{grid-column:span 12}.panel.privacy{background:var(--mint)}h2{font-size:clamp(1.45rem,3vw,2.05rem);line-height:1.2;margin:0 0 10px}h3{line-height:1.25}.panel p{color:var(--sub)}
.downloads{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:16px}.download{padding:16px;border:1px solid var(--line);border-radius:14px;background:var(--paper);text-decoration:none;font-weight:800}.download span{display:block;color:var(--sub);font-size:12px;font-weight:500}.passport{margin:32px auto}.passport-sheet{width:min(820px,100%);min-height:900px;margin:20px auto;padding:42px;background:var(--paper);border:1px solid var(--line);border-radius:24px;box-shadow:0 15px 40px #27344812;display:flex;flex-direction:column}.sheet-no{color:var(--gold);font-size:12px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.passport-sheet h2{font-size:clamp(1.8rem,4vw,2.75rem);margin:8px 0 13px}.boundary{padding:14px 16px;border-left:5px solid var(--gold);background:#fff5dc;border-radius:12px;color:#3d4654}.prompt-grid{display:grid;gap:13px;margin-top:20px}.prompt-card{border:1px solid #cad8dc;border-radius:16px;padding:17px;background:#fff}.prompt-card h3{color:var(--blue);margin:0 0 6px}.prompt-card p{margin:0;color:#465366}.note{margin-top:22px;font-weight:750}.note-box{min-height:135px;border:1px dashed #9fa9b5;border-radius:14px;background:#fff}.skip{margin-top:auto;padding-top:20px;color:var(--sub);font-size:13px}.cover-sheet{justify-content:center;text-align:center}.cover-sheet .boundary{text-align:left;margin-top:28px}.closing-sheet{justify-content:center}.closing-sheet a{overflow-wrap:anywhere}.sources li{margin:8px 0}.faq-item{border-top:1px solid var(--line);padding:15px 0}.faq-item:first-child{border-top:0}.app-card{border-color:#b9cfd6;background:#f6fcfd}.footer{margin-top:42px;padding:28px 0;border-top:1px solid var(--line);color:var(--sub);font-size:13px}
@media(max-width:720px){.panel{grid-column:span 12}.passport-sheet{min-height:0;padding:24px}.nav{align-items:flex-start;flex-direction:column}.hero{padding-top:36px}}
@media print{@page{margin:13mm}.screen-only,.top,.footer{display:none!important}body{background:#fff;font-size:10.5pt}.wrap{width:100%}.passport{margin:0}.passport-sheet{width:100%;min-height:0;height:auto;margin:0;padding:7mm;border:0;border-radius:0;box-shadow:none;page-break-after:always}.passport-sheet:last-child{page-break-after:auto}.passport-sheet h2{font-size:23pt}.prompt-card{break-inside:avoid}.note-box{min-height:34mm}.skip{margin-top:8mm}a{color:#000;text-decoration:none}}
"""


def canonical(locale: str) -> str:
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def pdf_filename(locale: str, size_name: str) -> str:
    language = "zh-hant" if locale == "zh-Hant" else "en"
    return f"{SLUG}-{language}-{size_name}.pdf"


def _prompt_rows(dataset: dict, locale: str, scenario: dict) -> list[dict]:
    target_indexes = (0, 2, 4)
    rows = []
    for mode, target_index in zip(dataset["participationModes"], target_indexes):
        target = scenario["targets"][target_index]["text"][locale]
        rows.append(
            {
                "mode": mode["name"][locale],
                "prompt": mode["promptTemplate"][locale].replace("{target}", target),
            }
        )
    return rows


def _pdf_styles(locale: str) -> dict[str, ParagraphStyle]:
    normal_font = "STSong-Light" if locale == "zh-Hant" else "Helvetica"
    strong_font = "STSong-Light" if locale == "zh-Hant" else "Helvetica-Bold"
    word_wrap = "CJK" if locale == "zh-Hant" else None
    base = {
        "fontName": normal_font,
        "textColor": colors.HexColor("#18202f"),
        "wordWrap": word_wrap,
    }
    return {
        "title": ParagraphStyle(
            "PassportTitle",
            **{**base, "fontName": strong_font},
            fontSize=27,
            leading=32,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "PassportSubtitle",
            **{**base, "textColor": colors.HexColor("#586477")},
            fontSize=14,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "heading": ParagraphStyle(
            "PassportHeading",
            **{**base, "fontName": strong_font},
            fontSize=23,
            leading=28,
            spaceAfter=10,
        ),
        "eyebrow": ParagraphStyle(
            "PassportEyebrow",
            **{
                **base,
                "fontName": strong_font,
                "textColor": colors.HexColor("#a06518"),
            },
            fontSize=9,
            leading=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "PassportBody", **base, fontSize=10.5, leading=15, spaceAfter=8
        ),
        "small": ParagraphStyle(
            "PassportSmall",
            **{**base, "textColor": colors.HexColor("#586477")},
            fontSize=8.5,
            leading=12,
        ),
        "card_title": ParagraphStyle(
            "PassportCardTitle",
            **{
                **base,
                "fontName": strong_font,
                "textColor": colors.HexColor("#245b78"),
            },
            fontSize=11.5,
            leading=15,
            spaceAfter=4,
        ),
    }


def render_pdf(dataset: dict, locale: str, page_size: tuple[float, float]) -> bytes:
    copy = COPY[locale]
    styles = _pdf_styles(locale)
    normal_font = "STSong-Light" if locale == "zh-Hant" else "Helvetica"
    width, _ = page_size
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=23 * mm,
        title=copy["title"],
        author="Lumi Apps - iOS App Guide",
        subject=copy["description"],
        keywords=copy["keywords"],
    )
    usable_width = width - document.leftMargin - document.rightMargin
    story = [
        Spacer(1, 32 * mm),
        Paragraph(html.escape(copy["cover_title"]), styles["title"]),
        Paragraph(html.escape(copy["cover_subtitle"]), styles["subtitle"]),
        Table(
            [[Paragraph(html.escape(copy["cover_notice"]), styles["body"])]],
            colWidths=[usable_width],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f5ef")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#b8d9ca")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            ),
        ),
        Spacer(1, 12 * mm),
        Paragraph(html.escape(copy["safety"]), styles["card_title"]),
        Paragraph(html.escape(copy["safety_text"]), styles["body"]),
        Paragraph(html.escape(copy["privacy"]), styles["card_title"]),
        Paragraph(html.escape(copy["privacy_text"]), styles["body"]),
        Paragraph(html.escape(copy["choices"]), styles["card_title"]),
        Paragraph(html.escape(copy["choices_text"]), styles["body"]),
        PageBreak(),
    ]
    for index, scenario in enumerate(dataset["scenarios"], 1):
        rows = _prompt_rows(dataset, locale, scenario)
        story.extend(
            [
                Paragraph(
                    html.escape(f"{copy['page']} {index:02d} / 12"),
                    styles["eyebrow"],
                ),
                Paragraph(html.escape(scenario["name"][locale]), styles["heading"]),
                Table(
                    [
                        [
                            Paragraph(
                                html.escape(scenario["safetyBoundary"][locale]),
                                styles["body"],
                            )
                        ]
                    ],
                    colWidths=[usable_width],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff4d8")),
                            ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor("#b47a27")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 12),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                            ("TOPPADDING", (0, 0), (-1, -1), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ]
                    ),
                ),
                Spacer(1, 7 * mm),
            ]
        )
        for prompt_index, row in enumerate(rows, 1):
            card = Table(
                [
                    [Paragraph(html.escape(row["mode"]), styles["card_title"])],
                    [
                        Paragraph(
                            f"{prompt_index}. {html.escape(row['prompt'])}",
                            styles["body"],
                        )
                    ],
                ],
                colWidths=[usable_width],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#c8d6da")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 11),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            )
            story.extend([KeepTogether([card]), Spacer(1, 3.2 * mm)])
        story.extend(
            [
                Spacer(1, 2 * mm),
                Paragraph(html.escape(copy["note"]), styles["card_title"]),
                Table(
                    [[""]],
                    colWidths=[usable_width],
                    rowHeights=[26 * mm],
                    style=TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#9fa9b5")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ]
                    ),
                ),
                Spacer(1, 4 * mm),
                Paragraph(html.escape(copy["skip"]), styles["small"]),
                PageBreak(),
            ]
        )
    source_links = [
        f'<link href="{DATASET_PAGE}">{html.escape(copy["dataset"])}</link>',
        f'<link href="{API_DOCS}">{html.escape(copy["api"])}</link>',
        f'<link href="{LICENSE}">{html.escape(copy["license"])}</link>',
    ]
    story.extend(
        [
            Spacer(1, 28 * mm),
            Paragraph(html.escape(copy["closing"]), styles["heading"]),
            Paragraph(html.escape(copy["closing_text"]), styles["body"]),
            Spacer(1, 7 * mm),
            Paragraph(html.escape(copy["privacy"]), styles["card_title"]),
            Paragraph(html.escape(copy["privacy_text"]), styles["body"]),
            Paragraph(html.escape(copy["respect"]), styles["card_title"]),
            Paragraph(html.escape(copy["respect_text"]), styles["body"]),
            Spacer(1, 7 * mm),
            Paragraph(html.escape(copy["source"]), styles["card_title"]),
            Paragraph(html.escape(copy["source_text"]), styles["body"]),
            *[Paragraph(f"• {link}", styles["body"]) for link in source_links],
        ]
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setTitle(copy["title"])
        canvas.setAuthor("Lumi Apps - iOS App Guide")
        canvas.setSubject(copy["description"])
        canvas.setKeywords(copy["keywords"])
        canvas.setFont(normal_font, 7)
        canvas.setFillColor(colors.HexColor("#586477"))
        canvas.drawString(16 * mm, 13 * mm, copy["attribution"])
        canvas.drawString(
            16 * mm,
            9.5 * mm,
            f"{LICENSE} | {copy['changes']}",
        )
        canvas.drawRightString(width - 16 * mm, 13 * mm, str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def make_pdf_artifacts(dataset: dict) -> dict[str, dict[str, dict]]:
    artifacts: dict[str, dict[str, dict]] = {}
    for locale in COPY:
        artifacts[locale] = {}
        for size_name, page_size in PDF_SIZES.items():
            filename = pdf_filename(locale, size_name)
            content = render_pdf(dataset, locale, page_size)
            artifacts[locale][size_name] = {
                "filename": filename,
                "url": f"{SITE}/tools/{filename}",
                "bytes": content,
                "sha256": hashlib.sha256(content).hexdigest(),
                "contentSize": f"{len(content)} bytes",
            }
    return artifacts


def _encoding(artifact: dict, locale: str, size_name: str) -> dict:
    return {
        "@type": "MediaObject",
        "name": f"{COPY[locale][size_name]} — {COPY[locale]['title']}",
        "contentUrl": artifact["url"],
        "encodingFormat": "application/pdf",
        "contentSize": artifact["contentSize"],
        "inLanguage": locale,
        "additionalProperty": {
            "@type": "PropertyValue",
            "name": "SHA-256",
            "value": artifact["sha256"],
        },
    }


def learning_resource(
    dataset: dict,
    locale: str,
    modified: str,
    artifacts: dict[str, dict],
) -> dict:
    copy = COPY[locale]
    return {
        "@type": "LearningResource",
        "@id": f"{canonical(locale)}#resource",
        "name": copy["title"],
        "description": copy["description"],
        "url": canonical(locale),
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "version": dataset["version"],
        "inLanguage": locale,
        "isAccessibleForFree": True,
        "license": LICENSE,
        "learningResourceType": ["Activity", "Printable"],
        "educationalUse": copy["learning_use"],
        "interactivityType": "active",
        "accessMode": ["textual", "visual"],
        "accessModeSufficient": {
            "@type": "ItemList",
            "itemListElement": ["textual"],
        },
        "audience": [
            {"@type": "EducationalAudience", "educationalRole": "student"},
            {"@type": "EducationalAudience", "educationalRole": "parent"},
            {"@type": "EducationalAudience", "educationalRole": "teacher"},
        ],
        "keywords": copy["keywords"],
        "isBasedOn": DATASET_PAGE,
        "citation": [
            DATASET_PAGE,
            *[reference["url"] for reference in dataset["officialReferences"]],
        ],
        "creator": {
            "@type": "Organization",
            "name": "Lumi Apps - iOS App Guide",
            "url": SITE,
        },
        "encoding": [
            _encoding(artifacts[size_name], locale, size_name)
            for size_name in PDF_SIZES
        ],
    }


def metadata_graph(
    dataset: dict,
    modified: str,
    artifacts: dict[str, dict[str, dict]],
) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            learning_resource(dataset, locale, modified, artifacts[locale])
            for locale in COPY
        ],
    }


def validate_metadata(metadata: dict) -> None:
    encoded = json.dumps(metadata, ensure_ascii=False)
    for forbidden in (
        "apps.apple.com",
        "SoftwareApplication",
        APP_NAME,
        APP_ID,
    ):
        if forbidden in encoded:
            raise ValueError(f"OER metadata must remain app-independent: {forbidden}")
    resources = metadata.get("@graph", [])
    if len(resources) != 2:
        raise ValueError("OER metadata must describe both language editions")
    for resource in resources:
        if resource.get("@type") != "LearningResource":
            raise ValueError("OER graph entries must be LearningResource objects")
        if resource.get("license") != LICENSE:
            raise ValueError("OER metadata must include the CC BY 4.0 license")
        if len(resource.get("encoding", [])) != len(PDF_SIZES):
            raise ValueError("Each OER language must expose A4 and US Letter PDFs")
        if resource.get("accessModeSufficient", {}).get("itemListElement") != [
            "textual"
        ]:
            raise ValueError("Text alone must be sufficient to use the OER")


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_versioned_metadata(path: Path, renderer) -> str:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    match = CONTENT_MODIFIED_RE.search(existing)
    prior_date = match.group(1) if match else INITIAL_DATE
    candidate_data = renderer(prior_date)
    validate_metadata(candidate_data)
    candidate = _json(candidate_data)
    if candidate == existing:
        return prior_date
    modified = TODAY
    updated_data = renderer(modified)
    validate_metadata(updated_data)
    write_text_if_changed(path, _json(updated_data))
    return modified


def _json_script(data: dict) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace(
            "</", "<\\/"
        )
        + "</script>"
    )


def render_page(
    dataset: dict,
    locale: str,
    artifacts: dict[str, dict],
    app_public: bool = False,
    modified: str = INITIAL_DATE,
) -> str:
    copy = COPY[locale]
    url = canonical(locale)
    other_locale = "zh-Hant" if locale == "en" else "en"
    alternate = canonical(other_locale)
    home = f"{SITE}/{'zh-Hant/' if locale == 'zh-Hant' else ''}index.html"
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in copy["badges"]
    )
    downloads = "".join(
        '<a class="download" href="{url}" download>{label}<span>PDF · {size}</span></a>'.format(
            url=html.escape(artifacts[size_name]["url"], quote=True),
            label=html.escape(copy[size_name]),
            size=html.escape(
                "210 × 297 mm" if size_name == "a4" else "8.5 × 11 in"
            ),
        )
        for size_name in PDF_SIZES
    )
    how_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in copy["how_items"]
    )
    scenario_pages = []
    for index, scenario in enumerate(dataset["scenarios"], 1):
        prompts = "".join(
            '<article class="prompt-card"><h3>{mode}</h3><p><strong>{number}. '
            "</strong>{prompt}</p></article>".format(
                mode=html.escape(row["mode"]),
                number=prompt_index,
                prompt=html.escape(row["prompt"]),
            )
            for prompt_index, row in enumerate(
                _prompt_rows(dataset, locale, scenario), 1
            )
        )
        scenario_pages.append(
            '<article class="passport-sheet"><div class="sheet-no">{page} {index:02d} / '
            "12</div><h2>{name}</h2><p class=\"boundary\">{boundary}</p>"
            '<div class="prompt-grid">{prompts}</div><p class="note">{note}</p>'
            '<div class="note-box" aria-hidden="true"></div><p class="skip">{skip}</p>'
            "</article>".format(
                page=html.escape(copy["page"]),
                index=index,
                name=html.escape(scenario["name"][locale]),
                boundary=html.escape(scenario["safetyBoundary"][locale]),
                prompts=prompts,
                note=html.escape(copy["note"]),
                skip=html.escape(copy["skip"]),
            )
        )
    source_items = [
        (copy["dataset"], DATASET_PAGE),
        (copy["api"], API_DOCS),
        (copy["license"], LICENSE),
        *[
            (title, reference["url"])
            for title, reference in zip(
                copy["source_titles"], dataset["officialReferences"]
            )
        ],
    ]
    sources = "".join(
        f'<li><a href="{html.escape(source_url, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source_url in source_items
    )
    faq = "".join(
        f'<article class="faq-item"><h3>{html.escape(question)}</h3>'
        f"<p>{html.escape(answer)}</p></article>"
        for question, answer in copy["faq_items"]
    )
    resource = learning_resource(dataset, locale, modified, artifacts)
    graph = [
        resource,
        {
            "@type": "WebPage",
            "@id": f"{url}#page",
            "url": url,
            "name": copy["title"],
            "description": copy["description"],
            "inLanguage": locale,
            "dateModified": modified,
            "mainEntity": {"@id": resource["@id"]},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": copy["tools"], "item": f"{SITE}/tools/"},
                {"@type": "ListItem", "position": 2, "name": copy["title"], "item": url},
            ],
        },
    ]
    app_section = ""
    if app_public:
        tracked_url = appstore_url(APP_KEY, f"iag_travel_passport_{locale.lower()}")
        graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "url": tracked_url,
                "operatingSystem": "iOS",
                "applicationCategory": "TravelApplication",
                "description": copy["app_text"],
            }
        )
        app_section = (
            '<article class="panel wide app-card screen-only"><h2>{title}</h2>'
            '<p>{text}</p><a class="button" href="{url}" rel="nofollow noopener">'
            "{cta}</a></article>"
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(tracked_url, quote=True),
            cta=html.escape(copy["app_cta"]),
        )
    schema = _json_script({"@context": "https://schema.org", "@graph": graph})
    cover = (
        '<article class="passport-sheet cover-sheet"><div class="sheet-no">'
        f'{html.escape(copy["eyebrow"])}</div><h2>{html.escape(copy["cover_title"])}</h2>'
        f'<p class="lead">{html.escape(copy["cover_subtitle"])}</p>'
        f'<p class="boundary">{html.escape(copy["safety_text"])}</p>'
        f'<p><strong>{html.escape(copy["cover_notice"])}</strong></p></article>'
    )
    closing = (
        '<article class="passport-sheet closing-sheet"><div class="sheet-no">'
        f'CC BY 4.0</div><h2>{html.escape(copy["closing"])}</h2>'
        f'<p>{html.escape(copy["closing_text"])}</p><h3>{html.escape(copy["privacy"])}</h3>'
        f'<p>{html.escape(copy["privacy_text"])}</p><h3>{html.escape(copy["respect"])}</h3>'
        f'<p>{html.escape(copy["respect_text"])}</p><h3>{html.escape(copy["source"])}</h3>'
        f'<ul class="sources">{sources}</ul></article>'
    )
    pdf_alternates = "\n".join(
        f'<link rel="alternate" type="application/pdf" '
        f'href="{html.escape(artifacts[size_name]["url"], quote=True)}" '
        f'title="{html.escape(copy[size_name], quote=True)}">'
        for size_name in PDF_SIZES
    )
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
<link rel="canonical" href="{html.escape(url, quote=True)}">
<link rel="alternate" hreflang="en" href="{canonical('en')}">
<link rel="alternate" hreflang="zh-Hant" href="{canonical('zh-Hant')}">
<link rel="alternate" hreflang="x-default" href="{canonical('en')}">
<link rel="alternate" type="application/ld+json" href="{METADATA_URL}" title="OER metadata">
<link rel="describedby" type="application/ld+json" href="{RO_CRATE_URL}" title="RO-Crate 1.3 metadata">
<link rel="alternate" type="application/opds+json" href="{OPDS2_URL}" title="OPDS 2.0 catalog">
<link rel="alternate" type="application/atom+xml;profile=opds-catalog;kind=acquisition" href="{OPDS1_URL}" title="OPDS 1.2 catalog">
{pdf_alternates}
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
<meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
<meta property="og:url" content="{html.escape(url, quote=True)}">
<meta name="twitter:card" content="summary">
<style>{STYLE}</style>
{schema}
</head>
<body>
<header class="top screen-only"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav><a href="{SITE}/tools/">{html.escape(copy['tools'])}</a> · <a href="{alternate}">{html.escape(copy['language'])}</a></nav></div></header>
<main>
<section class="hero wrap screen-only"><div class="eyebrow">{html.escape(copy['eyebrow'])}</div><h1>{html.escape(copy['title'])}</h1><p class="lead">{html.escape(copy['lead'])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#passport">{html.escape(copy['start'])}</a><a class="button secondary" href="{alternate}">{html.escape(copy['language'])}</a></div></section>
<section class="screen-grid wrap screen-only"><article class="panel wide"><h2>{html.escape(copy['download'])}</h2><p>{html.escape(copy['download_intro'])}</p><div class="downloads">{downloads}</div><div class="actions"><button class="button secondary" type="button" onclick="window.print()">{html.escape(copy['html_print'])}</button><a class="button secondary" href="{METADATA_URL}">{html.escape(copy['metadata'])}</a><a class="button secondary" href="{RO_CRATE_URL}">{html.escape(copy['ro_crate'])}</a><a class="button secondary" href="{OPDS2_URL}">{html.escape(copy['opds2'])}</a><a class="button secondary" href="{OPDS1_URL}">{html.escape(copy['opds1'])}</a></div></article><article class="panel"><h2>{html.escape(copy['inside'])}</h2><p>{html.escape(copy['inside_text'])}</p><h3>{html.escape(copy['how'])}</h3><ol>{how_items}</ol></article><article class="panel"><h2>{html.escape(copy['choices'])}</h2><p>{html.escape(copy['choices_text'])}</p><h3>{html.escape(copy['respect'])}</h3><p>{html.escape(copy['respect_text'])}</p></article><article class="panel privacy"><h2>{html.escape(copy['privacy'])}</h2><p>{html.escape(copy['privacy_text'])}</p></article><article class="panel"><h2>{html.escape(copy['safety'])}</h2><p>{html.escape(copy['safety_text'])}</p></article></section>
<section class="passport wrap" id="passport">{cover}{''.join(scenario_pages)}{closing}</section>
<section class="screen-grid wrap screen-only"><article class="panel wide"><h2>{html.escape(copy['source'])}</h2><p>{html.escape(copy['source_text'])}</p><ul class="sources">{sources}</ul></article><article class="panel wide"><h2>{html.escape(copy['faq'])}</h2>{faq}</article>{app_section}</section>
</main>
<footer class="footer screen-only"><div class="wrap">{html.escape(copy['footer'])} <a href="{LICENSE}" rel="license noopener">CC BY 4.0</a></div></footer>
</body>
</html>
"""


def write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.write_bytes(content)
    return True


def update_tools_index(pages: Path = PAGES) -> bool:
    index = pages / "tools" / "index.html"
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    target = f"{SLUG}.html"
    card = (
        '<article class="card third"><h2>'
        f'<a href="{target}">Family Travel Observation Passport</a></h2>'
        "<p>Openly licensed 14-page printable for 12 travel settings.</p>"
        "</article>"
    )
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(target)
        + r'">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    marker = '<section class="wrap grid">'
    if marker in updated:
        updated = updated.replace(marker, marker + card, 1)
    elif "</section></main>" in updated:
        updated = updated.replace("</section></main>", card + "</section></main>", 1)
    else:
        raise RuntimeError("tools/index.html is missing its main grid marker")
    return write_text_if_changed(index, updated)


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    dataset = load_dataset()
    artifacts = make_pdf_artifacts(dataset)
    tools = pages / "tools"
    zh_tools = pages / "zh-Hant" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    zh_tools.mkdir(parents=True, exist_ok=True)
    for locale_artifacts in artifacts.values():
        for artifact in locale_artifacts.values():
            write_bytes_if_changed(tools / artifact["filename"], artifact["bytes"])
    metadata_path = tools / f"{SLUG}.metadata.json"
    write_versioned_metadata(
        metadata_path,
        lambda modified: metadata_graph(dataset, modified, artifacts),
    )
    public = is_app_public(pages) if app_public is None else app_public
    modified_dates = {}
    for locale, directory in (("en", tools), ("zh-Hant", zh_tools)):
        modified_dates[locale] = render_versioned_page(
            directory / f"{SLUG}.html",
            lambda modified, locale=locale: render_page(
                dataset,
                locale,
                artifacts[locale],
                public,
                modified,
            ),
            INITIAL_DATE,
            TODAY,
        )
    update_tools_index(pages)
    return [
        canonical("en"),
        canonical("zh-Hant"),
        METADATA_URL,
        *[
            artifact["url"]
            for locale_artifacts in artifacts.values()
            for artifact in locale_artifacts.values()
        ],
    ]


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"family travel observation passport -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
