#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, private, no-score Zhuyin observation guide."""
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

from gen_calculator import write_tools_sitemap  # noqa: E402
from videogen.registry import appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-readiness-check"
TOOL_DATE = "2026-07-15"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phoneticWrite.jsp?la=0"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

TASKS = {
    "en": (
        {
            "id": "recognition",
            "label": "Symbol recognition",
            "title": "Can your child name these six symbols?",
            "instruction": (
                "Point in a mixed order. Do not teach or correct during this sample; "
                "just note what your child recognizes today."
            ),
            "sample": ("ㄅ", "ㄌ", "ㄓ", "ㄙ", "ㄩ", "ㄤ"),
            "options": (
                ("0–2 recognized", "Use a smaller symbol set next"),
                ("3–4 recognized", "Keep this small set available"),
                ("5–6 recognized", "Try a different small set another day"),
            ),
        },
        {
            "id": "tones",
            "label": "Tone awareness",
            "title": "Can your child hear or imitate the five tones?",
            "instruction": (
                "Say each form naturally. Ask your child to identify or echo the tone; "
                "count responses that do not need a second model."
            ),
            "sample": ("ㄇㄚ", "ㄇㄚˊ", "ㄇㄚˇ", "ㄇㄚˋ", "˙ㄇㄚ"),
            "options": (
                ("0–1 without help", "Use two contrasting tones next"),
                ("2–3 without help", "Keep these contrasts available"),
                ("4–5 without help", "Try different familiar syllables another day"),
            ),
        },
        {
            "id": "blending",
            "label": "Sound blending",
            "title": "Can your child blend these parts into syllables?",
            "instruction": (
                "Point from left to right and ask for one smooth syllable. A first model "
                "is fine, but mark how many the child can then blend independently."
            ),
            "sample": ("ㄅ ＋ ㄚ", "ㄇ ＋ ㄧ", "ㄕ ＋ ㄨㄟˇ"),
            "options": (
                ("Not yet", "Keep the two sounds separate and slow"),
                ("1 blend alone", "Repeat one familiar pair another day"),
                ("2–3 blends alone", "Try different familiar syllables another day"),
            ),
        },
        {
            "id": "writing",
            "label": "Shape and writing",
            "title": "Can your child copy these three shapes?",
            "instruction": (
                "Use blank paper. Look for a recognizable shape and orientation, not "
                "perfect handwriting or speed."
            ),
            "sample": ("ㄅ", "ㄓ", "ㄩ"),
            "options": (
                ("Not yet", "Offer air-tracing or large shapes next"),
                ("1–2 with support", "Keep the same small set available"),
                ("2–3 independently", "Try different familiar shapes another day"),
            ),
        },
        {
            "id": "reading",
            "label": "Reading application",
            "title": "Can your child use Zhuyin to read this short phrase?",
            "instruction": (
                "Cover the Chinese characters first if your child already recognizes "
                "them. Ask for a slow read, then reveal the phrase."
            ),
            "sample": ("ㄅㄚˋ　˙ㄅㄚ　ㄏㄜ　ㄕㄨㄟˇ", "爸爸喝水"),
            "options": (
                ("Not yet", "Return to symbols or short familiar blends"),
                ("With one prompt", "Try another familiar phrase another day"),
                ("Independently", "Choose one short annotated phrase another day"),
            ),
        },
    ),
    "zh-Hant": (
        {
            "id": "recognition",
            "label": "符號認讀",
            "title": "孩子能念出這 6 個符號嗎？",
            "instruction": "請打亂順序指給孩子看；這一輪先不教、不糾正，只記錄孩子今天認得多少。",
            "sample": ("ㄅ", "ㄌ", "ㄓ", "ㄙ", "ㄩ", "ㄤ"),
            "options": (
                ("認得 0–2 個", "下次使用更小的符號組"),
                ("認得 3–4 個", "保留這一小組供日後使用"),
                ("認得 5–6 個", "改天再換一小組觀察"),
            ),
        },
        {
            "id": "tones",
            "label": "聲調聽辨",
            "title": "孩子能聽出或模仿五個聲調嗎？",
            "instruction": "自然念出每一種聲調，請孩子指出或跟念；不用示範第二次就答出的才計入。",
            "sample": ("ㄇㄚ", "ㄇㄚˊ", "ㄇㄚˇ", "ㄇㄚˋ", "˙ㄇㄚ"),
            "options": (
                ("獨立完成 0–1 個", "下次使用兩個差異大的聲調"),
                ("獨立完成 2–3 個", "保留這些聲調對比供日後使用"),
                ("獨立完成 4–5 個", "改天再換熟悉音節觀察"),
            ),
        },
        {
            "id": "blending",
            "label": "拼音結合",
            "title": "孩子能把兩部分拼成一個音節嗎？",
            "instruction": "從左向右指讀，請孩子把兩個音慢慢連起來；可先示範一次，再記錄能獨立拼出的題數。",
            "sample": ("ㄅ ＋ ㄚ", "ㄇ ＋ ㄧ", "ㄕ ＋ ㄨㄟˇ"),
            "options": (
                ("目前還不會", "先把兩個音拉長、分開念"),
                ("獨立拼出 1 題", "改天再用同一組熟悉聲音"),
                ("獨立拼出 2–3 題", "改天再換熟悉音節觀察"),
            ),
        },
        {
            "id": "writing",
            "label": "字形書寫",
            "title": "孩子能照著寫出這 3 個字形嗎？",
            "instruction": "請用空白紙；只觀察形狀與方向是否可辨識，不要求速度或像印刷字一樣完美。",
            "sample": ("ㄅ", "ㄓ", "ㄩ"),
            "options": (
                ("目前還不會", "下次可用空寫或大字描寫"),
                ("協助下完成 1–2 個", "保留這一小組供日後使用"),
                ("獨立完成 2–3 個", "改天再換熟悉字形觀察"),
            ),
        },
        {
            "id": "reading",
            "label": "閱讀應用",
            "title": "孩子能靠注音讀出這個短句嗎？",
            "instruction": "若孩子已認得國字，請先遮住下方國字，只看注音慢慢讀；讀完再揭曉短句。",
            "sample": ("ㄅㄚˋ　˙ㄅㄚ　ㄏㄜ　ㄕㄨㄟˇ", "爸爸喝水"),
            "options": (
                ("目前還不會", "回到單一符號或熟悉短音節"),
                ("提示一次後完成", "改天再換一個熟悉短句"),
                ("可以獨立讀出", "改天再選一個短注音句"),
            ),
        },
    ),
}

SAMPLE_SETS = {
    "recognition": (
        ("ㄅ", "ㄌ", "ㄓ", "ㄙ", "ㄩ", "ㄤ"),
        ("ㄆ", "ㄋ", "ㄐ", "ㄘ", "ㄨ", "ㄟ"),
        ("ㄇ", "ㄉ", "ㄑ", "ㄖ", "ㄧ", "ㄢ"),
        ("ㄈ", "ㄊ", "ㄒ", "ㄔ", "ㄚ", "ㄥ"),
    ),
    "tones": (
        ("ㄇㄚ", "ㄇㄚˊ", "ㄇㄚˇ", "ㄇㄚˋ", "˙ㄇㄚ"),
        ("ㄅㄚ", "ㄅㄚˊ", "ㄅㄚˇ", "ㄅㄚˋ", "˙ㄅㄚ"),
        ("ㄉㄚ", "ㄉㄚˊ", "ㄉㄚˇ", "ㄉㄚˋ", "˙ㄉㄚ"),
    ),
    "blending": (
        ("ㄅ ＋ ㄚ", "ㄇ ＋ ㄧ", "ㄕ ＋ ㄨㄟˇ"),
        ("ㄆ ＋ ㄛ", "ㄋ ＋ ㄧㄠˇ", "ㄍ ＋ ㄨㄤ"),
        ("ㄉ ＋ ㄚˋ", "ㄌ ＋ ㄧㄣˊ", "ㄔ ＋ ㄥˊ"),
    ),
    "writing": (
        ("ㄅ", "ㄓ", "ㄩ"),
        ("ㄋ", "ㄘ", "ㄥ"),
        ("ㄇ", "ㄑ", "ㄢ"),
        ("ㄈ", "ㄖ", "ㄨ"),
    ),
    "reading": (
        ("ㄅㄚˋ　˙ㄅㄚ　ㄏㄜ　ㄕㄨㄟˇ", "爸爸喝水"),
        ("ㄇㄚ　˙ㄇㄚ　ㄎㄢˋ　ㄕㄨ", "媽媽看書"),
        ("ㄉㄧˋ　˙ㄉㄧ　ㄔ　ㄈㄢˋ", "弟弟吃飯"),
    ),
}

COPY = {
    "en": {
        "lang": "en",
        "title": "3-Minute Zhuyin Observation Guide for Parents",
        "description": (
            "A free, private, parent-guided Bopomofo observation guide for symbol "
            "recognition, tones, blending, writing and reading—with no score or level."
        ),
        "eyebrow": "Free private tool · no login",
        "lead": (
            "Record five tiny observations, then choose any gentle next activity—without "
            "a total, score, stage or pass-or-fail result."
        ),
        "privacy": "Private · no upload · nothing saved",
        "disclaimer": "Guide only · not a test or diagnosis",
        "start": "Start the 3-minute observation",
        "language": "繁體中文",
        "before": "Before you begin",
        "before_items": (
            "Use only with a child who has already met at least some Zhuyin symbols.",
            "Sit beside the child, keep the tone neutral and avoid correcting during each sample.",
            "If a sample contains symbols not yet taught, choose “New sample” instead of counting them as errors.",
            "Stop if the child is tired or frustrated; today’s choices are only practice notes.",
        ),
        "method": "What this observation guide samples",
        "method_text": (
            "It samples five building blocks: recognizing symbols, hearing tones, blending "
            "sounds, copying shapes and using Zhuyin to decode a short phrase. It does not "
            "measure all 37 symbols, spoken Mandarin, comprehension or a formal reading level. "
            "It is not a school assessment or professional diagnosis."
        ),
        "step_template": "Step {current} of {total}",
        "choose": "Choose the closest observation before continuing.",
        "new_sample": "New sample",
        "back": "Back",
        "next": "Next",
        "result_button": "See observation notes",
        "result_title": "Today’s observation notes",
        "result_note": (
            "These five choices are not combined, ranked or converted into a score or level. "
            "Choose any one free activity below, or stop without assigning a next step."
        ),
        "dimension_title": "What you observed",
        "recommend_title": "Free activities you may choose",
        "restart": "Observe again",
        "print": "Print notes",
        "share": "Share tool",
        "shared": "Tool link copied.",
        "share_title": "Free 3-minute Zhuyin observation guide",
        "recommendations": {
            "recognition": {
                "title": "Build fast symbol recognition",
                "text": "Use a small rotating card set and stop before recall becomes tiring.",
                "label": "Open free Zhuyin flashcards",
                "url": f"{SITE}/tools/zhuyin-flashcards.html",
            },
            "tones": {
                "title": "Make tones visible and audible",
                "text": "Contrast two tones first, then add the others with hand motions and listening games.",
                "label": "Open the 37-symbol and tone chart",
                "url": f"{SITE}/tools/zhuyin-bopomofo-chart.html",
            },
            "blending": {
                "title": "Practice smooth blending",
                "text": "Slide an initial toward the rest of the syllable while stretching both sounds.",
                "label": "Open the free 14-day activity calendar",
                "url": f"{SITE}/tools/zhuyin-grade1-14-day-summer-calendar.html",
            },
            "writing": {
                "title": "Strengthen shape memory",
                "text": "Trace large symbols first, then copy only two or three without a model.",
                "label": "Create a free practice sheet",
                "url": f"{SITE}/tools/zhuyin-practice-sheet.html",
            },
            "reading": {
                "title": "Move into purposeful reading",
                "text": "Read one short Zhuyin-annotated phrase, then connect it to meaning and conversation.",
                "label": "Use the free five-day lesson plan",
                "url": f"{SITE}/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            },
        },
        "app_title": "Want an optional guided practice layer?",
        "app_text": (
            "Lumi Bopomofo adds listening, tracing, tone and blending games for all 37 "
            "symbols. It is free to download with an optional one-time unlock, "
            "has no ads and requires no recurring subscription."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "resources": "Free follow-up resources",
        "resource_items": (
            ("14-day Grade 1 Zhuyin summer warm-up", f"{SITE}/tools/zhuyin-grade1-14-day-summer-calendar.html"),
            ("Parent-teacher Zhuyin handoff kit", f"{SITE}/tools/zhuyin-parent-teacher-handoff-kit.html"),
            ("Family Zhuyin picture-book club kit", f"{SITE}/tools/zhuyin-family-picture-book-club-kit.html"),
            ("Grandparent Zhuyin video-call kit", f"{SITE}/tools/zhuyin-grandparent-video-call-kit.html"),
            ("Printable practice sheet", f"{SITE}/tools/zhuyin-practice-sheet.html"),
            ("Zhuyin flashcards", f"{SITE}/tools/zhuyin-flashcards.html"),
            ("Zhuyin bingo", f"{SITE}/tools/zhuyin-bingo.html"),
            ("37-symbol Bopomofo chart", f"{SITE}/tools/zhuyin-bopomofo-chart.html"),
            (
                "Five-day heritage-school lesson plan",
                f"{SITE}/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            ),
        ),
        "sources": "Method and official references",
        "sources_text": (
            "This publisher-authored tool was designed as a low-pressure practice "
            "observation guide. Symbol forms and notation were checked against Taiwan "
            "Ministry of Education references; those agencies did not create or endorse "
            "this tool."
        ),
        "source_labels": (
            "Ministry of Education Bopomofo Handbook",
            "Ministry of Education Zhuyin Practice Book",
        ),
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "Record five separate parent-guided Zhuyin observations and return the "
            "same notes and optional free activities as this page. Never combine, "
            "rank or convert the choices into a score, level, readiness judgment "
            "or diagnosis."
        ),
        "webmcp_privacy": (
            "The five choice codes are processed only in the current page execution. "
            "They are not uploaded, submitted, saved or analyzed."
        ),
        "faq_title": "Parent FAQ",
        "faq": (
            (
                "Is this a Zhuyin readiness test, score or diagnosis?",
                "No. It records five separate observations without a total, score or level. It cannot determine school readiness, a reading level, a speech issue or any developmental condition.",
            ),
            (
                "When should we repeat it?",
                "Only when another observation would be useful. Use different symbols, blends and phrases rather than drilling or memorizing this page.",
            ),
            (
                "What if my child rarely speaks Mandarin?",
                "Treat oral language as a separate learning need. Pair symbol work with conversation, stories and fluent speech; do not interpret any choice here as a learning difficulty.",
            ),
            (
                "Does this tool collect my child’s answers?",
                "No. It has no account, form submission or cloud storage. Choices remain only in the current browser tab and disappear when the page is closed or reset.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": "Independent no-score educational resource. Not an official assessment or professional diagnosis.",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "3 分鐘注音觀察指南｜給家長的低壓力練習筆記",
        "description": "免費、私密的家長引導式注音觀察指南，分別記下符號認讀、聲調、拼讀、書寫與閱讀互動，不產生總分或分級。",
        "eyebrow": "免費私密工具 · 免登入",
        "lead": "分別記下五個小觀察，再任選一個溫和活動；不加總、不評分、不分級，也沒有及格或不及格。",
        "privacy": "私密 · 不上傳 · 不儲存",
        "disclaimer": "僅供練習 · 不是測驗或診斷",
        "start": "開始 3 分鐘觀察",
        "language": "English",
        "before": "開始前請先知道",
        "before_items": (
            "適合已接觸過部分注音符號的孩子；完全初學者可先從注音符號表開始。",
            "請坐在孩子身旁，語氣保持輕鬆，每一題先不糾正或教答案。",
            "若出現孩子還沒學過的符號，請按「換一組」，不要把未教過算成答錯。",
            "孩子疲倦或挫折就先停止；今天的選擇只是一份練習筆記。",
        ),
        "method": "這份觀察指南取樣什麼？",
        "method_text": "五個面向包括符號認讀、聲調聽辨、拼音結合、字形書寫，以及用注音讀短句。它不代表 37 個符號的完整熟練度，也不評量口語中文、理解力或正式閱讀程度；更不是學校評量或專業診斷。",
        "step_template": "第 {current} 題，共 {total} 題",
        "choose": "請先選擇最接近今天表現的選項。",
        "new_sample": "換一組",
        "back": "上一題",
        "next": "下一題",
        "result_button": "查看觀察筆記",
        "result_title": "今天的五項觀察筆記",
        "result_note": "這五個選擇不會加總、排序，也不會換算成分數或階段。可從下方免費活動任選一項，也可以不安排下一步。",
        "dimension_title": "今天觀察到的情況",
        "recommend_title": "可自由選擇的免費活動",
        "restart": "重新觀察",
        "print": "列印筆記",
        "share": "分享工具",
        "shared": "已複製工具連結。",
        "share_title": "免費 3 分鐘注音觀察指南",
        "recommendations": {
            "recognition": {
                "title": "加快符號認讀",
                "text": "每次只用一小組輪替字卡，在孩子疲倦前就結束。",
                "label": "開啟免費注音字卡",
                "url": f"{SITE}/tools/zhuyin-flashcards.html",
            },
            "tones": {
                "title": "讓聲調聽得見、看得見",
                "text": "先對比兩個差異明顯的聲調，再搭配手勢與聽音遊戲逐步加入其他聲調。",
                "label": "開啟 37 符號與聲調表",
                "url": f"{SITE}/tools/zhuyin-bopomofo-chart.html",
            },
            "blending": {
                "title": "練習流暢拼音",
                "text": "把聲符慢慢滑向後半段，兩個聲音拉長後連成一個音節。",
                "label": "開啟免費 14 天活動日曆",
                "url": f"{SITE}/zh-Hant/tools/zhuyin-grade1-14-day-summer-calendar.html",
            },
            "writing": {
                "title": "建立字形動作記憶",
                "text": "先描大字，再只挑兩三個符號離開範本自己寫。",
                "label": "製作免費注音描寫表",
                "url": f"{SITE}/tools/zhuyin-practice-sheet.html",
            },
            "reading": {
                "title": "把注音用進閱讀",
                "text": "每天讀一個短句，再把聲音連回意思與生活對話。",
                "label": "使用免費五日注音教案",
                "url": f"{SITE}/zh-Hant/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            },
        },
        "app_title": "想加入選用的引導式練習嗎？",
        "app_text": "Lumi 注音星球用聽音、描寫、聲調與拼讀遊戲練習全部 37 個符號。可免費下載，另提供一次性一次購買解鎖；無廣告、無定期訂閱。",
        "app_cta": "試用 Lumi 注音星球",
        "resources": "免費延伸資源",
        "resource_items": (
            ("小一入學前 14 天注音暖身日曆", f"{SITE}/zh-Hant/tools/zhuyin-grade1-14-day-summer-calendar.html"),
            ("家庭—教師注音交接包", f"{SITE}/zh-Hant/tools/zhuyin-parent-teacher-handoff-kit.html"),
            ("家庭注音繪本四週共讀包", f"{SITE}/zh-Hant/tools/zhuyin-family-picture-book-club-kit.html"),
            ("祖孫視訊注音遊戲包", f"{SITE}/zh-Hant/tools/zhuyin-grandparent-video-call-kit.html"),
            ("可列印注音描寫表", f"{SITE}/tools/zhuyin-practice-sheet.html"),
            ("注音符號字卡", f"{SITE}/tools/zhuyin-flashcards.html"),
            ("注音賓果", f"{SITE}/tools/zhuyin-bingo.html"),
            ("37 個注音符號表", f"{SITE}/tools/zhuyin-bopomofo-chart.html"),
            (
                "海外中文學校五日教案",
                f"{SITE}/zh-Hant/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            ),
        ),
        "sources": "方法說明與官方參考",
        "sources_text": "這份獨立指南以低壓力的練習觀察為目的；符號字形與標示方式依台灣教育部資料核對，但本工具並非由教育部製作或背書。",
        "source_labels": ("教育部《國語注音符號手冊》", "教育部《注音練習簿》"),
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "分別記錄五項家長引導式注音觀察，回傳與本頁相同的筆記及可自由選擇的免費活動；"
            "不得加總、排序或換算成分數、階段、入學準備判斷或診斷。"
        ),
        "webmcp_privacy": "五個選項代碼只在目前頁面執行時處理，不會上傳、送出、儲存或分析。",
        "faq_title": "家長常見問題",
        "faq": (
            (
                "這是注音入學準備測驗、分數或診斷嗎？",
                "不是。它只分別記下五項觀察，不產生總分或分級；不能判定入學準備度、閱讀程度、語言問題或任何發展狀況。",
            ),
            (
                "什麼時候可以再觀察一次？",
                "只有再次觀察確實有幫助時才需要。請更換符號、拼音與短句，不要反覆練習或背熟本頁題目。",
            ),
            (
                "孩子平常很少說中文怎麼辦？",
                "口語經驗需要另外補充。請把符號練習搭配對話、故事與流利的中文語音；不要把本頁任何選擇解讀為學習困難。",
            ),
            (
                "工具會蒐集孩子的答案嗎？",
                "不會。沒有帳號、表單送出或雲端儲存；選擇只留在目前分頁，關閉或重設後就消失。",
            ),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "不評分的獨立教育資源；不是官方評量，也不是專業診斷。",
    },
}

STYLE = """
:root{--ink:#17253b;--muted:#607086;--paper:#fffdf8;--line:#e8dfcf;--jade:#087f6b;--jade2:#0da58a;--gold:#c58a2a;--plum:#6251ad;--soft:#eef8f5;--warn:#fff6db}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#f8fcfb 0,#fffaf0 52%,#f7f4ff 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}
a{color:#4f3ea1}.wrap{width:min(1040px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:5;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:800}.nav-links{display:flex;gap:16px;align-items:center}.hero{padding:58px 0 28px}.eyebrow{color:var(--jade);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:900px;margin:.18em 0;font-size:clamp(2rem,5.8vw,4.25rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:780px;font-size:clamp(1.08rem,2.4vw,1.28rem);color:var(--muted)}.trust{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.badge{display:inline-flex;align-items:center;gap:7px;padding:8px 12px;border:1px solid #cde7df;border-radius:999px;background:#f5fffb;color:#176554;font-size:.9rem;font-weight:800;white-space:nowrap}.badge.warn{border-color:#ead79d;background:var(--warn);color:#705417}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--jade),var(--jade2));color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #087f6b25}.button.secondary{background:#fff;color:#4f3ea1!important;border:1px solid #cfc7e8;box-shadow:none}.button:focus-visible,.option:focus-within{outline:3px solid #e1b95d;outline-offset:3px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{grid-column:span 12;background:var(--paper);border:1px solid var(--line);border-radius:24px;padding:24px;box-shadow:0 12px 34px #28354c12}.half{grid-column:span 6}.third{grid-column:span 4}h2{font-size:clamp(1.45rem,3vw,2.05rem);line-height:1.16;margin:1.55em 0 .6em}h3{line-height:1.25}.muted{color:var(--muted)}.check-shell{margin-top:26px;background:#fff;border:1px solid #d8e4e0;border-radius:28px;overflow:hidden;box-shadow:0 20px 60px #17463818}.check-head{padding:18px 24px;background:linear-gradient(135deg,#eefaf6,#f6f2ff);border-bottom:1px solid #dfe8e4}.progress-row{display:flex;align-items:center;justify-content:space-between;gap:16px;font-weight:850}.progress-track{height:8px;margin-top:11px;border-radius:999px;background:#dfe8e4;overflow:hidden}.progress-bar{height:100%;width:20%;background:linear-gradient(90deg,var(--jade),#79c792);transition:width .3s ease}.step-panel{display:none;padding:clamp(22px,4vw,38px)}.step-panel.active{display:block}.step-kicker{color:var(--jade);font-weight:850}.step-panel h2{margin:.25em 0 .35em}.sample{display:flex;align-items:center;justify-content:center;gap:clamp(8px,2vw,18px);flex-wrap:wrap;min-height:112px;margin:24px 0;padding:18px;border:1px solid #dfd7c5;border-radius:22px;background:linear-gradient(145deg,#fffaf0,#fff)}.symbol{display:inline-flex;align-items:center;justify-content:center;min-width:64px;min-height:68px;padding:7px 10px;border-radius:16px;background:#fff;box-shadow:0 6px 16px #33230d14;font-size:clamp(1.65rem,6vw,3rem);font-weight:850;white-space:nowrap}.options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.option{display:block;position:relative;min-width:0}.option input{position:absolute;opacity:0;pointer-events:none}.option-body{display:block;height:100%;padding:15px;border:2px solid #e2e5e7;border-radius:17px;background:#fff;cursor:pointer;transition:border-color .18s,transform .18s,background .18s}.option input:checked+.option-body{border-color:var(--jade);background:#effbf7;transform:translateY(-2px)}.option-title{display:block;font-weight:900}.option-detail{display:block;margin-top:3px;color:var(--muted);font-size:.9rem}.error{display:none;margin:14px 0 0;color:#a13f34;font-weight:800}.error.show{display:block}.check-nav{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 24px;border-top:1px solid #e5e8e6;background:#fbfdfc}.check-nav .button[hidden]{display:none}.result{display:none;padding:clamp(24px,5vw,44px)}.result.active{display:block}.stage{display:inline-flex;padding:8px 13px;border-radius:999px;background:#eaf8f3;color:#116451;font-weight:900;white-space:nowrap}.result-lead{font-size:1.12rem}.skill-row{display:grid;grid-template-columns:minmax(120px,1fr) 2fr auto;gap:12px;align-items:center;margin:12px 0}.skill-label{font-weight:800}.skill-track{height:10px;border-radius:99px;background:#e5e9e7;overflow:hidden}.skill-fill{height:100%;background:linear-gradient(90deg,#deb35a,var(--jade2));border-radius:99px}.skill-value{color:var(--muted);font-size:.88rem;white-space:nowrap}.recommendations{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.rec{padding:17px;border:1px solid #e4ddcf;border-radius:18px;background:#fff}.rec h3{margin:.1em 0}.rec p{color:var(--muted)}.rec a{font-weight:850}.notice{padding:16px 18px;border-left:5px solid var(--gold);border-radius:14px;background:var(--warn)}.source-list a{overflow-wrap:anywhere}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--jade);font-weight:800}
.sample-action{display:block;margin:-14px auto 22px;border:0;background:transparent;color:#4f3ea1;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap}
@media(max-width:760px){.half,.third{grid-column:span 12}.options,.recommendations{grid-template-columns:1fr}.nav-links a:first-child{display:none}.hero{padding-top:38px}.observation-row{grid-template-columns:1fr}.check-nav{padding:15px}.step-panel{padding:22px 16px}.symbol{min-width:52px;min-height:58px}.option-title,.button{white-space:nowrap}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.intro,.check-head,.step-panel,.check-nav,.result .actions,.app-card,.resources,.faq,.footer{display:none!important}body{background:#fff}.check-shell{border:0;box-shadow:none}.result.active{display:block!important;padding:0}.card,.rec{box-shadow:none;break-inside:avoid}.recommendations{grid-template-columns:1fr}.wrap{width:100%}}
"""

SCRIPT = """
(function(){
  "use strict";
  var cfg=JSON.parse(document.getElementById("tool-config").textContent);
  var form=document.getElementById("skills-form");
  var panels=Array.prototype.slice.call(document.querySelectorAll(".step-panel"));
  var current=0;
  var back=document.getElementById("back-button");
  var next=document.getElementById("next-button");
  var error=document.getElementById("step-error");
  var result=document.getElementById("result");
  function showStep(index,moveFocus){
    current=index;
    panels.forEach(function(panel,i){
      panel.classList.toggle("active",i===index);
      panel.setAttribute("aria-hidden",i===index?"false":"true");
    });
    document.getElementById("step-count").textContent=cfg.stepTemplate
      .replace("{current}",index+1).replace("{total}",panels.length);
    var progress=document.getElementById("progress");
    progress.style.width=(((index+1)/panels.length)*100)+"%";
    progress.parentElement.setAttribute("aria-valuenow",String(index+1));
    back.hidden=index===0;
    next.textContent=index===panels.length-1?cfg.resultButton:cfg.next;
    error.classList.remove("show");
    if(moveFocus){panels[index].querySelector("h2").focus();}
  }
  function selected(panel){
    return panel.querySelector("input[type=radio]:checked");
  }
  function rotateSample(panel){
    var id=panel.dataset.dimension;
    var sets=cfg.sampleSets[id];
    var sample=panel.querySelector(".sample");
    var currentSet=parseInt(sample.dataset.set,10)||0;
    var nextSet=(currentSet+1+Math.floor(Math.random()*(sets.length-1)))%sets.length;
    sample.dataset.set=String(nextSet);
    sample.replaceChildren();
    panel.querySelectorAll("input[type=radio]").forEach(function(input){
      input.checked=false;
    });
    sets[nextSet].forEach(function(value){
      var symbol=document.createElement("span");
      symbol.className="symbol";
      symbol.textContent=value;
      sample.appendChild(symbol);
    });
  }
  function recommendationCard(item){
    return '<article class="rec"><h3>'+item.title+'</h3><p>'+item.text+
      '</p><a href="'+item.url+'">'+item.label+' →</a></article>';
  }
  function toolChoice(input,id){
    if(!Object.prototype.hasOwnProperty.call(input,id)){
      throw new TypeError(id+" is required.");
    }
    var value=input[id];
    var allowed=cfg.webMcpInputSchema.properties[id].enum;
    if(allowed.indexOf(value)===-1){
      throw new RangeError(id+" is not a supported observation.");
    }
    return cfg.dimensions[id].options[value];
  }
  async function registerWebMcp(){
    if(!document.modelContext?.registerTool){return;}
    await document.modelContext.registerTool({
      name:"record_private_zhuyin_observations",
      description:cfg.webMcpDescription,
      inputSchema:cfg.webMcpInputSchema,
      annotations:{readOnlyHint:true,untrustedContentHint:false},
      execute:async function(input){
        if(input===null||typeof input!=="object"||Array.isArray(input)){
          throw new TypeError("WebMCP input must be an object.");
        }
        Object.keys(input).forEach(function(id){
          if(cfg.dimensionOrder.indexOf(id)===-1){
            throw new RangeError(id+" is not a supported input.");
          }
        });
        var observations=cfg.dimensionOrder.map(function(id){
          var choice=toolChoice(input,id);
          return {
            dimension:id,
            dimension_label:cfg.dimensions[id].label,
            observation:choice.title,
            next_observation_note:choice.detail
          };
        });
        return JSON.stringify({
          result_type:"private_zhuyin_observation_notes",
          observations_not_combined_or_ranked:true,
          boundary:cfg.resultNote,
          privacy_boundary:cfg.webMcpPrivacy,
          observations:observations,
          optional_free_activities:cfg.dimensionOrder.map(function(id){
            return cfg.dimensions[id].recommendation;
          }),
          official_and_protocol_sources:cfg.sourceUrls,
          optional_lumi_bopomofo:{
            description:cfg.appText,
            app_store_url:cfg.appStoreUrl
          }
        });
      }
    });
  }
  function renderResult(){
    var observations={};
    panels.forEach(function(panel){
      var option=selected(panel).closest(".option");
      observations[panel.dataset.dimension]={
        title:option.querySelector(".option-title").textContent,
        detail:option.querySelector(".option-detail").textContent
      };
    });
    document.getElementById("skill-results").innerHTML=cfg.dimensionOrder.map(function(id){
      var observation=observations[id];
      return '<article class="rec"><h3>'+cfg.dimensions[id].label+
        '</h3><p><strong>'+observation.title+'</strong><br>'+observation.detail+'</p></article>';
    }).join("");
    var recs=cfg.dimensionOrder.map(function(id){
      return cfg.dimensions[id].recommendation;
    });
    document.getElementById("recommendations").innerHTML=recs.map(recommendationCard).join("");
    document.getElementById("check-content").hidden=true;
    result.classList.add("active");
    document.body.classList.add("has-result");
    result.focus();
    result.scrollIntoView({behavior:"smooth",block:"start"});
  }
  next.addEventListener("click",function(){
    if(!selected(panels[current])){
      error.classList.add("show");
      panels[current].querySelector("input").focus();
      return;
    }
    if(current<panels.length-1){showStep(current+1,true);}else{renderResult();}
  });
  back.addEventListener("click",function(){if(current>0){showStep(current-1,true);}});
  form.addEventListener("change",function(){error.classList.remove("show");});
  form.addEventListener("click",function(event){
    if(event.target.classList.contains("sample-action")){
      rotateSample(event.target.closest(".step-panel"));
    }
  });
  document.getElementById("restart-button").addEventListener("click",function(){
    form.reset();
    panels.forEach(rotateSample);
    result.classList.remove("active");
    document.body.classList.remove("has-result");
    document.getElementById("check-content").hidden=false;
    showStep(0,true);
    document.getElementById("check").scrollIntoView({behavior:"smooth",block:"start"});
  });
  document.getElementById("print-button").addEventListener("click",function(){window.print();});
  document.getElementById("share-button").addEventListener("click",function(){
    var data={title:cfg.shareTitle,url:location.href.split("#")[0]};
    var status=document.getElementById("share-status");
    if(navigator.share){
      navigator.share(data).catch(function(shareError){
        if(shareError.name!=="AbortError"){status.textContent=data.url;}
      });
    }else if(navigator.clipboard){
      navigator.clipboard.writeText(data.url)
        .then(function(){status.textContent=cfg.shared;})
        .catch(function(){status.textContent=data.url;});
    }else{
      status.textContent=data.url;
    }
  });
  showStep(0,false);
  registerWebMcp().catch(function(registrationError){
    console.error("WebMCP tool registration failed.",registrationError);
  });
})();
"""


def canonical(locale: str) -> str:
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(data: dict) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False)
        + "</script>"
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    properties = {}
    for task in TASKS[locale]:
        choices = [
            {
                "type": "string",
                "const": f"choice-{index}",
                "title": title,
                "description": detail,
            }
            for index, (title, detail) in enumerate(task["options"], 1)
        ]
        properties[task["id"]] = {
            "type": "string",
            "enum": [choice["const"] for choice in choices],
            "oneOf": choices,
            "description": (
                f'{task["title"]} {task["instruction"]} '
                "Choose the closest observation only after using the current page sample."
            ),
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [task["id"] for task in TASKS[locale]],
        "properties": properties,
    }


def render_tasks(locale: str) -> str:
    t = COPY[locale]
    output = []
    for index, task in enumerate(TASKS[locale]):
        symbols = "".join(
            f'<span class="symbol">{html.escape(symbol)}</span>'
            for symbol in SAMPLE_SETS[task["id"]][0]
        )
        options = "".join(
            '<label class="option">'
            f'<input type="radio" name="{task["id"]}" value="choice-{option_index}">'
            '<span class="option-body">'
            f'<span class="option-title">{html.escape(title)}</span>'
            f'<span class="option-detail">{html.escape(detail)}</span>'
            "</span></label>"
            for option_index, (title, detail) in enumerate(task["options"], 1)
        )
        output.append(
            f'<section class="step-panel{" active" if index == 0 else ""}" '
            f'data-dimension="{task["id"]}" aria-hidden="{"false" if index == 0 else "true"}">'
            f'<div class="step-kicker">{html.escape(task["label"])}</div>'
            f'<h2 tabindex="-1">{html.escape(task["title"])}</h2>'
            f'<p class="muted">{html.escape(task["instruction"])}</p>'
            f'<div class="sample" data-set="0" aria-live="polite" '
            f'aria-label="{html.escape(task["title"])}">{symbols}</div>'
            f'<button class="sample-action" type="button">↻ {html.escape(t["new_sample"])}</button>'
            f'<div class="options">{options}</div></section>'
        )
    return "".join(output)


def render_page(locale: str) -> str:
    t = COPY[locale]
    url = canonical(locale)
    other_locale = "zh-Hant" if locale == "en" else "en"
    alternate = canonical(other_locale)
    home = f"{SITE}/{'zh-Hant/' if locale == 'zh-Hant' else ''}index.html"
    app_url = appstore_url("lumibopomofo", f"iag_readiness_{locale.lower()}")

    config = {
        "stepTemplate": t["step_template"],
        "next": t["next"],
        "resultButton": t["result_button"],
        "resultNote": t["result_note"],
        "shareTitle": t["share_title"],
        "shared": t["shared"],
        "webMcpDescription": t["webmcp_description"],
        "webMcpPrivacy": t["webmcp_privacy"],
        "webMcpInputSchema": webmcp_input_schema(locale),
        "sourceUrls": [MOE_HANDBOOK, MOE_PRACTICE, WEBMCP_SOURCE],
        "appStoreUrl": app_url,
        "appText": t["app_text"],
        "dimensionOrder": [task["id"] for task in TASKS[locale]],
        "sampleSets": SAMPLE_SETS,
        "dimensions": {
            task["id"]: {
                "label": task["label"],
                "options": {
                    f"choice-{index}": {
                        "title": title,
                        "detail": detail,
                    }
                    for index, (title, detail) in enumerate(
                        task["options"],
                        1,
                    )
                },
                "recommendation": t["recommendations"][task["id"]],
            }
            for task in TASKS[locale]
        },
    }
    before_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["before_items"]
    )
    resources = "".join(
        f'<li><a href="{html.escape(url)}">{html.escape(label)}</a></li>'
        for label, url in t["resource_items"]
    )
    faq_html = "".join(
        f"<h3>{html.escape(question)}</h3><p>{html.escape(answer)}</p>"
        for question, answer in t["faq"]
    )
    schemas = [
        {
            "@context": "https://schema.org",
            "@type": ["WebApplication", "LearningResource"],
            "name": t["title"],
            "description": t["description"],
            "url": url,
            "inLanguage": locale,
            "applicationCategory": "EducationalApplication",
            "operatingSystem": "Any",
            "browserRequirements": "JavaScript",
            "isAccessibleForFree": True,
            "dateModified": TOOL_DATE,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "learningResourceType": "Parent-guided no-score observation guide",
            "educationalUse": "Practice planning",
            "educationalLevel": "Beginner",
            "typicalAgeRange": "4-9",
            "timeRequired": "PT3M",
            "teaches": [
                "Zhuyin symbol recognition",
                "Mandarin tone awareness",
                "Bopomofo blending",
                "Zhuyin writing",
                "Zhuyin-supported reading",
            ],
            "citation": [MOE_HANDBOOK, MOE_PRACTICE],
            "featureList": [
                "Five separate parent-guided observations",
                "No total, score, level, readiness judgment or diagnosis",
                "No account, upload, storage or analytics",
                "Progressive read-only WebMCP notes for supporting browsers",
            ],
            "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
        },
        {
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
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": t["home"], "item": home},
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": t["title"],
                    "item": url,
                },
            ],
        },
    ]
    ld = "\n".join(json_script(schema) for schema in schemas)
    source_links = (
        f'<li><a href="{MOE_HANDBOOK}" rel="noopener">{html.escape(t["source_labels"][0])}</a></li>'
        f'<li><a href="{MOE_PRACTICE}" rel="noopener">{html.escape(t["source_labels"][1])}</a></li>'
        f'<li><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></li>'
    )

    config_json = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")

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
<meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<style>{STYLE}</style>
{ld}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="nav-links"><a href="{SITE}/tools/">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["language"])}</a></nav></div></header>
<main>
<section class="hero wrap">
<div class="eyebrow">{html.escape(t["eyebrow"])}</div>
<h1>{html.escape(t["title"])}</h1>
<p class="lead">{html.escape(t["lead"])}</p>
<div class="trust"><span class="badge">✓ {html.escape(t["privacy"])}</span><span class="badge warn">ⓘ {html.escape(t["disclaimer"])}</span></div>
<div class="actions"><a class="button" href="#check">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div>
</section>
<section class="wrap grid intro">
<article class="card half"><h2>{html.escape(t["before"])}</h2><ul>{before_items}</ul></article>
<article class="card half"><h2>{html.escape(t["method"])}</h2><p>{html.escape(t["method_text"])}</p></article>
</section>
<section class="wrap check-shell" id="check">
<div id="check-content">
<div class="check-head"><div class="progress-row"><span id="step-count"></span><span>≈ 3 min</span></div><div class="progress-track" role="progressbar" aria-valuemin="1" aria-valuemax="5" aria-valuenow="1"><div class="progress-bar" id="progress"></div></div></div>
<form id="skills-form" novalidate>{render_tasks(locale)}</form>
<div class="check-nav"><button class="button secondary" id="back-button" type="button">{html.escape(t["back"])}</button><p class="error" id="step-error" role="alert">{html.escape(t["choose"])}</p><button class="button" id="next-button" type="button">{html.escape(t["next"])}</button></div>
</div>
<section class="result" id="result" tabindex="-1">
<h2>{html.escape(t["result_title"])}</h2>
<p class="notice">{html.escape(t["result_note"])}</p>
<h2>{html.escape(t["dimension_title"])}</h2><div id="skill-results"></div>
<h2>{html.escape(t["recommend_title"])}</h2><div class="recommendations" id="recommendations"></div>
<div class="actions"><button class="button secondary" id="restart-button" type="button">{html.escape(t["restart"])}</button><button class="button secondary" id="print-button" type="button">{html.escape(t["print"])}</button><button class="button" id="share-button" type="button">{html.escape(t["share"])}</button></div>
<div class="share-status" id="share-status" aria-live="polite"></div>
</section>
</section>
<section class="wrap grid resources">
<article class="card half"><h2>{html.escape(t["resources"])}</h2><ul>{resources}</ul></article>
<article class="card half app-card"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_url)}" rel="nofollow noopener">{html.escape(t["app_cta"])}</a></article>
</section>
<section class="wrap grid">
<article class="card half"><h2>{html.escape(t["sources"])}</h2><p>{html.escape(t["sources_text"])}</p><ul class="source-list">{source_links}</ul></article>
<article class="card half faq"><h2>{html.escape(t["faq_title"])}</h2>{faq_html}</article>
</section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="tool-config">{config_json}</script>
<script>{SCRIPT}</script>
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
        f'<a href="{target}">3-Minute Zhuyin Observation Guide</a></h2>'
        "<p>Record five private observations with no score, level, login or upload.</p>"
        "</article>"
    )
    grid_marker = '<section class="wrap grid">'
    if grid_marker + card in text:
        return False
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(target)
        + r'">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    if grid_marker in updated:
        updated = updated.replace(grid_marker, grid_marker + card, 1)
        index.write_text(updated, encoding="utf-8")
        return updated != text
    marker = "</section></main>"
    if marker not in updated:
        raise RuntimeError("tools/index.html is missing its main grid marker")
    updated = updated.replace(marker, card + marker, 1)
    index.write_text(updated, encoding="utf-8")
    return updated != text


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def build(pages: Path = PAGES) -> list[str]:
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        target = pages / relative
        write_text_if_changed(target, render_page(locale))
        outputs.append(canonical(locale))
    update_tools_index(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"readiness tool -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
