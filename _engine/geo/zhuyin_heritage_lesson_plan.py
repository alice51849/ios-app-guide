#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, print-ready Zhuyin starter lesson plan."""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from videogen.registry import appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-5-day-lesson-plan-heritage-school"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
SOURCES = (
    (
        "Taiwan Ministry of Education Bopomofo Handbook",
        "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html",
    ),
    (
        "Taiwan Ministry of Education Zhuyin Practice Book",
        "https://stroke-order.learningweb.moe.edu.tw/phoneticWrite.jsp?la=0",
    ),
    (
        "Overseas Community Affairs Council e-book catalog",
        "https://www.ocac.gov.tw/OCAC/Pages/List.aspx?nodeid=1438",
    ),
    (
        "Global Chinese Language and Culture Center teaching materials",
        "https://www.huayuworld.org/Ebook/TeachingMaterials",
    ),
)
RELATED_URLS = (
    f"{SITE}/tools/zhuyin-readiness-check.html",
    f"{SITE}/tools/zhuyin-library-storytime-kit.html",
    f"{SITE}/tools/zhuyin-parent-teacher-handoff-kit.html",
    f"{SITE}/tools/zhuyin-grandparent-video-call-kit.html",
    f"{SITE}/tools/zhuyin-family-picture-book-club-kit.html",
    f"{SITE}/tools/zhuyin-practice-sheet.html",
    f"{SITE}/tools/zhuyin-flashcards.html",
    f"{SITE}/tools/zhuyin-bingo.html",
    f"{SITE}/tools/zhuyin-bopomofo-chart.html",
    f"{SITE}/answers/app-to-reinforce-weekend-chinese-school-bopomofo-lessons-at-home.html",
)

DAYS = {
    "en": (
        {
            "title": "Day 1 — Hear and see ㄅ ㄆ ㄇ ㄈ + ㄚ",
            "goal": "Connect five new shapes to their sounds without asking for memorization.",
            "activities": (
                "5 min: teacher models each sound; children watch the mouth and echo once.",
                "8 min: trace large symbols in the air, then on a printed grid.",
                "10 min: sound hunt — hold up the matching card when a sound is heard.",
                "5 min: optional Lumi Bopomofo listen-and-tap practice.",
                "2 min exit check: identify any two symbols without pressure.",
            ),
        },
        {
            "title": "Day 2 — Add ㄉ ㄊ ㄋ ㄌ and review ㄚ",
            "goal": "Notice how tongue placement changes these four initial sounds.",
            "activities": (
                "5 min: quick card review of Day 1.",
                "8 min: teacher models ㄉ ㄊ ㄋ ㄌ slowly; children echo and compare.",
                "10 min: sort mixed cards into yesterday/today groups, saying each sound.",
                "5 min: trace only the two symbols each child finds hardest.",
                "2 min exit check: hear one sound and point to its symbol.",
            ),
        },
        {
            "title": "Day 3 — Add ㄧ ㄨ ㄩ and start blending",
            "goal": "Move from isolated symbols to slow, audible blends such as ㄅㄧ and ㄋㄧ.",
            "activities": (
                "5 min: review ㄅ ㄆ ㄇ ㄈ ㄉ ㄊ ㄋ ㄌ with shuffled cards.",
                "8 min: introduce ㄧ ㄨ ㄩ with clear mouth-shape contrasts.",
                "10 min: slide an initial card toward a medial card while blending aloud.",
                "5 min: optional syllable-train practice in Lumi Bopomofo.",
                "2 min exit check: blend one teacher-selected pair.",
            ),
        },
        {
            "title": "Day 4 — Hear tones with ㄇㄚ",
            "goal": "Hear that pitch changes meaning while the base symbols stay the same.",
            "activities": (
                "5 min: say ㄇㄚ with first, second, third and fourth-tone hand motions.",
                "8 min: match four spoken tones to arrow cards; add the neutral tone last.",
                "10 min: tone detective — children identify a tone before seeing its mark.",
                "5 min: optional Lumi Bopomofo tone-game practice.",
                "2 min exit check: distinguish two contrasting tones.",
            ),
        },
        {
            "title": "Day 5 — Decode, review and celebrate",
            "goal": "Use the starter set to decode a few real words and learn the repeatable routine.",
            "activities": (
                "5 min: child-led review with the full starter card set.",
                "8 min: decode 爸 ㄅㄚˋ, 媽 ㄇㄚ, 馬 ㄇㄚˇ, 弟 ㄉㄧˋ, 你 ㄋㄧˇ and 他 ㄊㄚ.",
                "10 min: bingo or memory match using sounds rather than letter names.",
                "5 min: choose the next four symbols for the following week.",
                "2 min exit check: name one sound learned and one sound to revisit.",
            ),
        },
    ),
    "zh-Hant": (
        {
            "title": "第 1 天｜聽音、認形：ㄅ ㄆ ㄇ ㄈ ＋ ㄚ",
            "goal": "把五個新符號的形與音連起來，不要求第一天就背熟。",
            "activities": (
                "5 分鐘：老師示範發音，孩子看嘴形後跟讀一次。",
                "8 分鐘：先在空中寫大字，再到列印方格描寫。",
                "10 分鐘：聽音找卡——聽到聲音就舉起對應符號。",
                "5 分鐘：可選用 Lumi Bopomofo 做聽音點選練習。",
                "2 分鐘離堂檢核：輕鬆認出任兩個符號即可。",
            ),
        },
        {
            "title": "第 2 天｜加入 ㄉ ㄊ ㄋ ㄌ，複習 ㄚ",
            "goal": "觀察舌頭位置如何改變四個聲音。",
            "activities": (
                "5 分鐘：用卡片快速複習第 1 天。",
                "8 分鐘：老師放慢示範 ㄉ ㄊ ㄋ ㄌ，孩子比較後跟讀。",
                "10 分鐘：把混合卡片分成昨天／今天兩組，邊分邊念。",
                "5 分鐘：只描寫每個孩子最容易混淆的兩個符號。",
                "2 分鐘離堂檢核：聽一個音，指出對應符號。",
            ),
        },
        {
            "title": "第 3 天｜加入 ㄧ ㄨ ㄩ，開始拼讀",
            "goal": "從單一符號進到緩慢、聽得清楚的拼讀，例如 ㄅㄧ、ㄋㄧ。",
            "activities": (
                "5 分鐘：打亂卡片複習 ㄅ ㄆ ㄇ ㄈ ㄉ ㄊ ㄋ ㄌ。",
                "8 分鐘：用清楚的嘴形對比介紹 ㄧ ㄨ ㄩ。",
                "10 分鐘：把聲符卡滑向介音卡，同時拉長聲音完成拼讀。",
                "5 分鐘：可選用 Lumi Bopomofo 的拼讀小火車練習。",
                "2 分鐘離堂檢核：拼出老師指定的一組符號。",
            ),
        },
        {
            "title": "第 4 天｜用 ㄇㄚ 聽辨聲調",
            "goal": "聽出音高會改變意思，而基本符號維持不變。",
            "activities": (
                "5 分鐘：搭配手勢念 ㄇㄚ 的一、二、三、四聲。",
                "8 分鐘：把四個讀音配到音高箭頭卡，最後再加入輕聲。",
                "10 分鐘：聲調偵探——先聽辨，再揭曉聲調符號。",
                "5 分鐘：可選用 Lumi Bopomofo 的聲調遊戲練習。",
                "2 分鐘離堂檢核：分辨兩個對比明顯的聲調。",
            ),
        },
        {
            "title": "第 5 天｜拼讀、複習與完成感",
            "goal": "用入門符號拼出幾個真實詞語，並學會可重複使用的練習流程。",
            "activities": (
                "5 分鐘：由孩子帶領，用完整入門卡組複習。",
                "8 分鐘：拼讀爸 ㄅㄚˋ、媽 ㄇㄚ、馬 ㄇㄚˇ、弟 ㄉㄧˋ、你 ㄋㄧˇ、他 ㄊㄚ。",
                "10 分鐘：用聲音而非符號名稱玩賓果或記憶配對。",
                "5 分鐘：一起選出下週要接著學的四個符號。",
                "2 分鐘離堂檢核：說出一個學會的音和一個想再練的音。",
            ),
        },
    ),
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Free 5-Day Zhuyin Lesson Plan for Heritage Chinese Schools",
        "description": (
            "A print-ready five-day Bopomofo starter mini-unit for ages 4–8, "
            "available in English and Traditional Chinese with official sources."
        ),
        "eyebrow": "Free teacher resource · CC BY 4.0",
        "lead": (
            "A five-day starter mini-unit with 30 minutes of instruction per day "
            "for weekend Chinese "
            "schools, heritage-language families and homeschool groups."
        ),
        "important": (
            "This plan introduces a reusable learning routine and a 12-symbol "
            "starter set. It does not claim to teach all 37 Zhuyin symbols in five days."
        ),
        "print": "Print lesson plan",
        "overview": "At a glance",
        "overview_items": (
            ("Age", "4–8, beginner"),
            ("Time", "5 days × 30 minutes"),
            ("Group", "One child, small group or weekend class"),
            ("Materials", "Symbol cards, pencil, printed grid and a device only if desired"),
        ),
        "outcomes": "Learning outcomes",
        "outcome_items": (
            "Recognize and pronounce the 12-symbol starter set.",
            "Blend selected initials with ㄚ, ㄧ, ㄨ or ㄩ slowly.",
            "Hear basic contrasts among Mandarin tones.",
            "Use the same listen → see → move → play → check routine for the remaining symbols.",
        ),
        "plan": "Five-day plan",
        "goal": "Objective",
        "goal_separator": ":",
        "field_separator": ":",
        "teaches": (
            "Zhuyin symbol-sound recognition",
            "Bopomofo syllable blending",
            "Mandarin tone awareness",
        ),
        "adapt": "Adapt it to your learners",
        "adapt_items": (
            (
                "Speaks Mandarin, cannot yet read",
                "Use familiar words first; let oral vocabulary support decoding.",
            ),
            (
                "Does not hear Mandarin daily",
                "Spend more time listening and echoing; teach fewer symbols per session.",
            ),
            (
                "Mixed-level class",
                "Beginners match sounds to cards; experienced learners blend and find example words.",
            ),
        ),
        "assessment": "End-of-week check",
        "assessment_text": (
            "Shuffle the starter cards. Ask each child to identify sounds, blend two "
            "teacher-selected combinations and distinguish two tones. Record only "
            "what to revisit; do not turn the check into a speed test."
        ),
        "app": "Optional practice layer",
        "app_text": (
            "The lesson works without an app. Lumi Bopomofo can provide short "
            "listen-and-tap, tracing, tone and blending practice between classes. "
            "It has no ads or account requirement. The free download offers an "
            "optional one-time unlock; Lumi Bopomofo Pro is a one-time paid download."
        ),
        "free_cta": "Try Lumi Bopomofo",
        "pro_cta": "Get the complete Pro edition",
        "official": "Official references and further materials",
        "official_note": (
            "This independent mini-unit is not an official government curriculum. "
            "Use the sources below for standard notation and longer-form materials."
        ),
        "source_titles": tuple(title for title, _ in SOURCES),
        "reuse": "Reuse this lesson",
        "reuse_text": (
            "You may print, adapt and share this original lesson under CC BY 4.0. "
            "Credit “iOS App Guide” and link to this page."
        ),
        "related": "Related free resources",
        "related_labels": (
            "3-minute Zhuyin skills check",
            "Library Zhuyin family storytime kit",
            "Parent-teacher Zhuyin handoff kit",
            "Grandparent Zhuyin video-call kit",
            "Family Zhuyin picture-book club kit",
            "Zhuyin practice sheet",
            "Zhuyin flashcards",
            "Zhuyin bingo",
            "37-symbol Bopomofo chart",
            "Weekend Chinese-school home practice guide",
        ),
        "faq_title": "Teacher FAQ",
        "faq": (
            (
                "Will children learn all 37 symbols in five days?",
                "No. This is an honest starter mini-unit. Repeat its routine with new symbol groups over following weeks.",
            ),
            (
                "Is this an official Ministry of Education lesson plan?",
                "No. It is an independent, reusable plan that links to official Taiwan references for notation and practice.",
            ),
            (
                "Do I need the app to teach the lesson?",
                "No. Cards, paper, teacher modeling and games are sufficient. The app is an optional practice layer.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": "Independent educational resource. Source-checked July 2026.",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "海外華語學校免費五日注音入門教案｜可列印英繁雙語資源",
        "description": (
            "給海外華裔家庭、週末中文學校與自學小組的五日注音入門教案；"
            "每天 30 分鐘、可直接列印，附官方來源與分層教學方法。"
        ),
        "eyebrow": "免費教師資源 · CC BY 4.0",
        "lead": "為海外週末中文學校、華裔家庭與自學小組設計：五天、每天 30 分鐘的注音入門小單元。",
        "important": "這份教案建立可重複的學習流程，先教 12 個入門符號；不宣稱五天就能學完全部 37 個注音。",
        "print": "列印教案",
        "overview": "教案速覽",
        "overview_items": (
            ("年齡", "4–8 歲，初學"),
            ("時間", "5 天 × 每天 30 分鐘"),
            ("人數", "一對一、小組或週末班"),
            ("材料", "符號卡、鉛筆、列印方格；裝置為選用"),
        ),
        "outcomes": "學習目標",
        "outcome_items": (
            "認讀並正確發出 12 個入門符號的音。",
            "緩慢拼讀部分聲符與 ㄚ、ㄧ、ㄨ、ㄩ 的組合。",
            "聽出華語基本聲調的差異。",
            "把「聽音 → 認形 → 動手 → 遊戲 → 檢核」流程套用到其餘符號。",
        ),
        "plan": "五日教學流程",
        "goal": "本日目標",
        "goal_separator": "：",
        "field_separator": "：",
        "teaches": (
            "注音符號的形音連結",
            "注音拼讀",
            "華語聲調覺察",
        ),
        "adapt": "依孩子程度調整",
        "adapt_items": (
            ("會說華語、還不識字", "先用熟悉口語詞，讓已有詞彙支持文字拼讀。"),
            ("平常很少聽華語", "增加聽音與跟讀時間，每次少教幾個符號。"),
            ("混齡／混程度班級", "初學者做聲音配卡；熟練者做拼讀並找例字。"),
        ),
        "assessment": "週末學習檢核",
        "assessment_text": (
            "打亂入門符號卡，請孩子認音、拼出老師指定的兩組符號，再分辨兩個聲調。"
            "只記錄下週要複習的項目，不比速度、不排名。"
        ),
        "app": "選用的練習層",
        "app_text": (
            "不用 App 也能完成教案。課間若要加強聽音點選、描寫、聲調與拼讀，"
            "可選用無廣告、免帳號的 Lumi Bopomofo。免費版可下載試用並選擇一次性永久解鎖；"
            "Lumi Bopomofo Pro 則是一次付費下載的完整版本。"
        ),
        "free_cta": "試用 Lumi Bopomofo",
        "pro_cta": "取得完整 Pro 版",
        "official": "官方參考與延伸教材",
        "official_note": "本教案為獨立製作，並非政府官方課程；正式符號寫法與長期教材請參考下列官方來源。",
        "source_titles": (
            "台灣教育部《國語注音符號手冊》",
            "台灣教育部《注音練習簿》",
            "僑務委員會電子書目錄",
            "全球華文網教材專區",
        ),
        "reuse": "自由使用這份教案",
        "reuse_text": "本原創教案採 CC BY 4.0，可列印、改編與分享；請標註「iOS App Guide」並連回本頁。",
        "related": "相關免費資源",
        "related_labels": (
            "3 分鐘注音學習檢核",
            "圖書館注音親子故事時間包",
            "家庭—教師注音交接包",
            "祖孫視訊注音遊戲包",
            "家庭注音繪本四週共讀包",
            "注音描寫練習表",
            "注音符號字卡",
            "注音賓果",
            "37 個注音符號表",
            "週末中文學校的家庭複習指南",
        ),
        "faq_title": "教師常見問題",
        "faq": (
            ("孩子五天能學完 37 個注音嗎？", "不能。這是誠實的入門小單元；後續數週請沿用相同流程，分組加入新符號。"),
            ("這是教育部官方教案嗎？", "不是。本頁是可自由改編的獨立教案，並連結台灣官方資料供查核符號與筆順。"),
            ("一定要使用 App 嗎？", "不用。符號卡、紙筆、老師示範與遊戲已足夠；App 只是選用的課間練習層。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立教育資源；資料於 2026 年 7 月查核。",
    },
}

STYLE = """
:root{--ink:#17202a;--muted:#596474;--paper:#fffdf7;--line:#e8dcc4;--gold:#b7791f;--plum:#6b46c1;--soft:#f7f2ff}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#fff 0,#faf7ef 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.65}
a{color:#5138a5}.wrap{width:min(1040px,calc(100% - 32px));margin:auto}.top{padding:16px 0;border-bottom:1px solid var(--line);background:#ffffffeb;position:sticky;top:0;z-index:2}.nav{display:flex;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:750}.hero{padding:52px 0 28px}.eyebrow{color:var(--gold);font-weight:850;letter-spacing:.08em;text-transform:uppercase}.hero h1{font-size:clamp(2rem,5.6vw,4rem);line-height:1.06;margin:.2em 0}.lead{font-size:1.2rem;color:var(--muted);max-width:800px}.notice{padding:16px 18px;border-left:5px solid var(--gold);background:#fff8df;border-radius:12px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.button{border:0;border-radius:999px;padding:12px 18px;background:linear-gradient(135deg,var(--plum),#805ad5);color:#fff;text-decoration:none;font-weight:800;cursor:pointer}.button.secondary{background:#fff;color:#5138a5;border:1px solid #cfc2eb}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{grid-column:span 12;background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:0 8px 26px #523d1912}.half{grid-column:span 6}.third{grid-column:span 4}h2{font-size:clamp(1.4rem,3vw,2rem);margin:1.4em 0 .55em}.day{break-inside:avoid}.day h3{margin:.1em 0;color:#5138a5}.goal{color:var(--muted)}li{margin:.45em 0}.fact{font-size:1.08rem;font-weight:750}.source-list a{overflow-wrap:anywhere}.footer{margin-top:40px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}
@media(max-width:720px){.half,.third{grid-column:span 12}.nav{align-items:flex-start;flex-direction:column}.hero{padding-top:34px}}
@media print{.top,.actions{display:none}body{background:#fff;font-size:11pt}.wrap{width:100%}.hero{padding:0 0 12px}.card{box-shadow:none;break-inside:avoid;padding:14px}.day{page-break-inside:avoid}a{color:#000;text-decoration:none}.footer{margin-top:14px}}
"""


def _canonical(locale: str) -> str:
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    return f"{SITE}/{prefix}guides/{SLUG}.html"


def _json_script(data: dict) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False)
        + "</script>"
    )


def render_page(locale: str) -> str:
    t = COPY[locale]
    canonical = _canonical(locale)
    other_locale = "zh-Hant" if locale == "en" else "en"
    alternate = _canonical(other_locale)
    free_url = appstore_url("lumibopomofo", f"iag_oer_{locale.lower()}")
    pro_url = appstore_url("lumibopomofopro", f"iag_oer_{locale.lower()}_pro")
    home = f"{SITE}/{'zh-Hant/' if locale == 'zh-Hant' else ''}index.html"

    day_html = "".join(
        '<section class="card day">'
        f'<h3>{html.escape(day["title"])}</h3>'
        f'<p class="goal"><strong>{html.escape(t["goal"] + t["goal_separator"])}</strong> '
        f'{html.escape(day["goal"])}</p><ol>'
        + "".join(f"<li>{html.escape(step)}</li>" for step in day["activities"])
        + "</ol></section>"
        for day in DAYS[locale]
    )
    overview_html = "".join(
        f'<div class="card third"><div class="fact">{html.escape(label)}</div>'
        f'<div>{html.escape(value)}</div></div>'
        for label, value in t["overview_items"]
    )
    adaptations = "".join(
        f"<li><strong>{html.escape(label + t['field_separator'])}</strong> "
        f"{html.escape(value)}</li>"
        for label, value in t["adapt_items"]
    )
    faq_html = "".join(
        '<div itemscope itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name">{html.escape(question)}</h3>'
        '<div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">'
        f'<p itemprop="text">{html.escape(answer)}</p></div></div>'
        for question, answer in t["faq"]
    )
    source_html = "".join(
        f'<li><a href="{html.escape(url)}" rel="noopener">{html.escape(title)}</a></li>'
        for title, (_, url) in zip(t["source_titles"], SOURCES)
    )
    resource_schema = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "name": t["title"],
        "description": t["description"],
        "url": canonical,
        "inLanguage": locale,
        "isAccessibleForFree": True,
        "learningResourceType": "Lesson plan",
        "educationalUse": "Instruction",
        "educationalLevel": "Beginner",
        "typicalAgeRange": "4-8",
        "timeRequired": "PT2H30M",
        "license": LICENSE,
        "teaches": list(t["teaches"]),
        "citation": [url for _, url in SOURCES],
        "author": {
            "@type": "Organization",
            "name": "iOS App Guide",
            "url": SITE,
        },
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": locale,
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in t["faq"]
        ],
    }
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t["home"], "item": home},
            {
                "@type": "ListItem",
                "position": 2,
                "name": t["title"],
                "item": canonical,
            },
        ],
    }
    related_urls = list(RELATED_URLS)
    if locale == "zh-Hant":
        related_urls[0] = f"{SITE}/zh-Hant/tools/zhuyin-readiness-check.html"
        related_urls[1] = f"{SITE}/zh-Hant/tools/zhuyin-library-storytime-kit.html"
        related_urls[2] = f"{SITE}/zh-Hant/tools/zhuyin-parent-teacher-handoff-kit.html"
        related_urls[3] = f"{SITE}/zh-Hant/tools/zhuyin-grandparent-video-call-kit.html"
        related_urls[4] = f"{SITE}/zh-Hant/tools/zhuyin-family-picture-book-club-kit.html"
    related = "".join(
        f'<li><a href="{html.escape(url)}">{html.escape(label)}</a></li>'
        for label, url in zip(t["related_labels"], related_urls)
    )

    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="{locale}" href="{canonical}">
<link rel="alternate" hreflang="{other_locale}" href="{alternate}">
<link rel="alternate" hreflang="x-default" href="{_canonical("en")}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{canonical}">
<style>{STYLE}</style>
{_json_script(resource_schema)}
{_json_script(faq_schema)}
{_json_script(breadcrumb_schema)}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav><a href="{home}">{html.escape(t["home"])}</a> · <a href="{SITE}/tools/">{html.escape(t["tools"])}</a></nav></div></header>
<main>
<section class="hero wrap">
<div class="eyebrow">{html.escape(t["eyebrow"])}</div>
<h1>{html.escape(t["title"])}</h1>
<p class="lead">{html.escape(t["lead"])}</p>
<p class="notice">{html.escape(t["important"])}</p>
<div class="actions"><button class="button" onclick="window.print()">{html.escape(t["print"])}</button><a class="button secondary" href="{alternate}">English / 繁體中文</a></div>
</section>
<section class="wrap"><h2>{html.escape(t["overview"])}</h2><div class="grid">{overview_html}</div></section>
<section class="wrap"><h2>{html.escape(t["outcomes"])}</h2><div class="card"><ul>{''.join(f'<li>{html.escape(item)}</li>' for item in t["outcome_items"])}</ul></div></section>
<section class="wrap"><h2>{html.escape(t["plan"])}</h2><div class="grid">{day_html}</div></section>
<section class="wrap grid">
<article class="card half"><h2>{html.escape(t["adapt"])}</h2><ul>{adaptations}</ul></article>
<article class="card half"><h2>{html.escape(t["assessment"])}</h2><p>{html.escape(t["assessment_text"])}</p></article>
</section>
<section class="wrap grid">
<article class="card half"><h2>{html.escape(t["app"])}</h2><p>{html.escape(t["app_text"])}</p><div class="actions"><a class="button" href="{free_url}" rel="nofollow noopener">{html.escape(t["free_cta"])}</a><a class="button secondary" href="{pro_url}" rel="nofollow noopener">{html.escape(t["pro_cta"])}</a></div></article>
<article class="card half"><h2>{html.escape(t["reuse"])}</h2><p>{html.escape(t["reuse_text"])}</p><p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></p></article>
</section>
<section class="wrap grid">
<article class="card half"><h2>{html.escape(t["official"])}</h2><p>{html.escape(t["official_note"])}</p><ul class="source-list">{source_html}</ul></article>
<article class="card half"><h2>{html.escape(t["related"])}</h2><ul>{related}</ul></article>
</section>
<section class="wrap card"><h2>{html.escape(t["faq_title"])}</h2>{faq_html}</section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
</body>
</html>
"""


def _write_sitemap(pages: Path) -> None:
    files = sorted((pages / "guides").glob("*.html"))
    files += sorted(pages.glob("*/guides/*.html"))
    urls = [
        f"{SITE}/{path.relative_to(pages).as_posix()}"
        for path in files
        if path.name != "index.html"
    ]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
        + "\n</urlset>\n"
    )
    (pages / "sitemap_guides.xml").write_text(xml, encoding="utf-8")


def build(pages: Path = PAGES) -> list[str]:
    outputs = []
    for locale in COPY:
        relative = Path("guides") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        target = pages / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(locale), encoding="utf-8")
        outputs.append(f"{SITE}/{relative.as_posix()}")
    _write_sitemap(pages)
    return outputs


if __name__ == "__main__":
    for url in build():
        print(f"created {url}")
