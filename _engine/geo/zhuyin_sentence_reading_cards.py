#!/usr/bin/env python3
"""Generate bilingual, private Zhuyin short-sentence reading cards."""

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
SLUG = "zhuyin-short-sentence-reading-cards"
CONTENT_DATE = "2026-07-14"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/"
    "juyin/html_ch/index.html"
)
MOE_FORMS = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=0"
MOE_CURRICULUM = "https://cirn.k12ea.gov.tw/TWELVE/List.aspx?fid=11010"
APP_URL = appstore_url("lumibopomofo")


def phrase(
    text: str,
    readings: tuple[str, ...],
    after: str = "",
) -> dict[str, object]:
    if len(text) != len(readings):
        raise ValueError(f"reading count does not match {text!r}")
    return {
        "tokens": [
            {"char": char, "reading": reading}
            for char, reading in zip(text, readings, strict=True)
        ],
        "after": after,
    }


SENTENCES = {
    "short": [
        {
            "phrases": [
                phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ")),
                phrase("飛", ("ㄈㄟ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("小狗", ("ㄒㄧㄠˇ", "ㄍㄡˇ")),
                phrase("跑", ("ㄆㄠˇ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("青蛙", ("ㄑㄧㄥ", "ㄨㄚ")),
                phrase("跳", ("ㄊㄧㄠˋ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("我", ("ㄨㄛˇ",)),
                phrase("喝水", ("ㄏㄜ", "ㄕㄨㄟˇ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("花朵", ("ㄏㄨㄚ", "ㄉㄨㄛˇ")),
                phrase("開", ("ㄎㄞ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("大雨", ("ㄉㄚˋ", "ㄩˇ")),
                phrase("停", ("ㄊㄧㄥˊ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("太陽", ("ㄊㄞˋ", "ㄧㄤˊ")),
                phrase("升", ("ㄕㄥ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("白雲", ("ㄅㄞˊ", "ㄩㄣˊ")),
                phrase("飄", ("ㄆㄧㄠ",), "。"),
            ]
        },
    ],
    "everyday": [
        {
            "phrases": [
                phrase("雨滴", ("ㄩˇ", "ㄉㄧ")),
                phrase("落在", ("ㄌㄨㄛˋ", "ㄗㄞˋ")),
                phrase("屋頂上", ("ㄨ", "ㄉㄧㄥˇ", "ㄕㄤˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("紅花", ("ㄏㄨㄥˊ", "ㄏㄨㄚ")),
                phrase("開在", ("ㄎㄞ", "ㄗㄞˋ")),
                phrase("草地上", ("ㄘㄠˇ", "ㄉㄧˋ", "ㄕㄤˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ")),
                phrase("飛到", ("ㄈㄟ", "ㄉㄠˋ")),
                phrase("屋頂上", ("ㄨ", "ㄉㄧㄥˇ", "ㄕㄤˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("我用", ("ㄨㄛˇ", "ㄩㄥˋ")),
                phrase("積木", ("ㄐㄧ", "ㄇㄨˋ")),
                phrase("蓋高塔", ("ㄍㄞˋ", "ㄍㄠ", "ㄊㄚˇ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("黑貓", ("ㄏㄟ", "ㄇㄠ")),
                phrase("跳過", ("ㄊㄧㄠˋ", "ㄍㄨㄛˋ")),
                phrase("小木箱", ("ㄒㄧㄠˇ", "ㄇㄨˋ", "ㄒㄧㄤ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("我在", ("ㄨㄛˇ", "ㄗㄞˋ")),
                phrase("紙上", ("ㄓˇ", "ㄕㄤˋ")),
                phrase("畫月亮", ("ㄏㄨㄚˋ", "ㄩㄝˋ", "ㄌㄧㄤˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("火車", ("ㄏㄨㄛˇ", "ㄔㄜ")),
                phrase("穿過", ("ㄔㄨㄢ", "ㄍㄨㄛˋ")),
                phrase("山洞", ("ㄕㄢ", "ㄉㄨㄥˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("雨後", ("ㄩˇ", "ㄏㄡˋ")),
                phrase("天空", ("ㄊㄧㄢ", "ㄎㄨㄥ")),
                phrase("有彩虹", ("ㄧㄡˇ", "ㄘㄞˇ", "ㄏㄨㄥˊ"), "。"),
            ]
        },
    ],
    "clauses": [
        {
            "phrases": [
                phrase("清晨", ("ㄑㄧㄥ", "ㄔㄣˊ"), "，"),
                phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ")),
                phrase("在樹上", ("ㄗㄞˋ", "ㄕㄨˋ", "ㄕㄤˋ")),
                phrase("唱歌", ("ㄔㄤˋ", "ㄍㄜ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("太陽", ("ㄊㄞˋ", "ㄧㄤˊ")),
                phrase("落山", ("ㄌㄨㄛˋ", "ㄕㄢ"), "，"),
                phrase("天空", ("ㄊㄧㄢ", "ㄎㄨㄥ")),
                phrase("變成", ("ㄅㄧㄢˋ", "ㄔㄥˊ")),
                phrase("橘紅色", ("ㄐㄩˊ", "ㄏㄨㄥˊ", "ㄙㄜˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("雨停", ("ㄩˇ", "ㄊㄧㄥˊ")),
                phrase("以後", ("ㄧˇ", "ㄏㄡˋ"), "，"),
                phrase("青蛙", ("ㄑㄧㄥ", "ㄨㄚ")),
                phrase("跳出", ("ㄊㄧㄠˋ", "ㄔㄨ")),
                phrase("水池", ("ㄕㄨㄟˇ", "ㄔˊ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("春風", ("ㄔㄨㄣ", "ㄈㄥ")),
                phrase("吹來", ("ㄔㄨㄟ", "ㄌㄞˊ"), "，"),
                phrase("花園", ("ㄏㄨㄚ", "ㄩㄢˊ")),
                phrase("開滿", ("ㄎㄞ", "ㄇㄢˇ")),
                phrase("紅花", ("ㄏㄨㄥˊ", "ㄏㄨㄚ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("黑貓", ("ㄏㄟ", "ㄇㄠ")),
                phrase("躍過", ("ㄩㄝˋ", "ㄍㄨㄛˋ")),
                phrase("木箱", ("ㄇㄨˋ", "ㄒㄧㄤ"), "，"),
                phrase("穩穩", ("ㄨㄣˇ", "ㄨㄣˇ")),
                phrase("落地", ("ㄌㄨㄛˋ", "ㄉㄧˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("遠方", ("ㄩㄢˇ", "ㄈㄤ")),
                phrase("火車", ("ㄏㄨㄛˇ", "ㄔㄜ")),
                phrase("穿過", ("ㄔㄨㄢ", "ㄍㄨㄛˋ")),
                phrase("綠色", ("ㄌㄩˋ", "ㄙㄜˋ")),
                phrase("山洞", ("ㄕㄢ", "ㄉㄨㄥˋ"), "。"),
            ]
        },
        {
            "phrases": [
                phrase("彩虹", ("ㄘㄞˇ", "ㄏㄨㄥˊ")),
                phrase("出現", ("ㄔㄨ", "ㄒㄧㄢˋ"), "，"),
                phrase("大家", ("ㄉㄚˋ", "ㄐㄧㄚ")),
                phrase("抬頭", ("ㄊㄞˊ", "ㄊㄡˊ")),
                phrase("看", ("ㄎㄢˋ",), "。"),
            ]
        },
        {
            "phrases": [
                phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ")),
                phrase("飛過", ("ㄈㄟ", "ㄍㄨㄛˋ")),
                phrase("田野", ("ㄊㄧㄢˊ", "ㄧㄝˇ"), "，"),
                phrase("停在", ("ㄊㄧㄥˊ", "ㄗㄞˋ")),
                phrase("高樹上", ("ㄍㄠ", "ㄕㄨˋ", "ㄕㄤˋ"), "。"),
            ]
        },
    ],
}


def validate_sentences() -> None:
    reading_pattern = re.compile(r"^[\u3105-\u3129\u02ca\u02c7\u02cb\u02d9]+$")
    allowed_after = {"", "，", "。"}
    for level, sentences in SENTENCES.items():
        if len(sentences) != 8:
            raise ValueError(f"{level} must contain exactly 8 sentences")
        for sentence in sentences:
            phrases = sentence.get("phrases")
            if not isinstance(phrases, list) or not phrases:
                raise ValueError(f"{level} contains an empty sentence")
            for item in phrases:
                if item["after"] not in allowed_after:
                    raise ValueError(f"unsupported punctuation: {item['after']!r}")
                tokens = item["tokens"]
                if not tokens:
                    raise ValueError(f"{level} contains an empty phrase")
                for token in tokens:
                    if len(token["char"]) != 1:
                        raise ValueError(f"invalid character token: {token!r}")
                    reading = token["reading"]
                    if not reading_pattern.fullmatch(reading):
                        raise ValueError(f"invalid Zhuyin reading: {reading!r}")
                    if "ˉ" in reading:
                        raise ValueError("first-tone marks must be omitted")


validate_sentences()


COPY = {
    "en": {
        "title": "Free Zhuyin Short Sentence Reading Cards | Printable",
        "description": (
            "Make private, printable Zhuyin short-sentence reading cards. "
            "Progress from short lines to two-clause sentences, then hide the "
            "annotations and reread. No login, score, upload or saved child profile."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · original · private",
        "heading": "Zhuyin short sentence reading cards",
        "lead": (
            "For the step after syllable blending: read one short, fully annotated "
            "sentence, tap to hide its Zhuyin, then reread the same words without "
            "a timer or score."
        ),
        "privacy": "No name, account, score, upload or saved child profile",
        "scope": "Original text practice; not a reading test, level or diagnosis",
        "builder": "Build a calm reading set",
        "level_label": "Choose sentence length",
        "level_short": "3-character lines",
        "level_everyday": "6–7-character sentences",
        "level_clauses": "Two-clause sentences",
        "count": "Cards",
        "new_set": "New sentence set",
        "hide_all": "Hide all Zhuyin",
        "show_all": "Show all Zhuyin",
        "print": "Print cards",
        "share": "Share tool",
        "hide": "Hide Zhuyin",
        "show": "Show Zhuyin",
        "kicker": "Decode with Zhuyin, then hide it and reread",
        "ready": "Zhuyin is visible. Read first, then hide it for a second pass.",
        "shared": "Share sheet opened.",
        "cancelled": "Sharing was cancelled.",
        "copied": "Tool link copied.",
        "copy_failed": "Copy was unavailable. Use this link:",
        "short_help": (
            "Start with one familiar subject and action. The phrase spacing stays "
            "visible while every character has a standard Zhuyin annotation."
        ),
        "everyday_help": (
            "Move to familiar places and actions in six- or seven-character "
            "sentences. Pause at the small phrase gaps instead of rushing."
        ),
        "clauses_help": (
            "Try two connected parts only when shorter sentences feel comfortable. "
            "The comma provides a natural pause."
        ),
        "why_title": "Move from one syllable to one complete thought",
        "why_text": (
            "Recognising symbols, blending a syllable and reading a sentence are "
            "separate steps. These text-only cards add one step at a time: short "
            "phrases, a complete sentence, then the same sentence without visible "
            "Zhuyin."
        ),
        "routine_title": "A four-step rereading routine",
        "routine": [
            "An adult reads the sentence once while pointing to each annotated character.",
            "The learner reads it slowly with the Zhuyin still visible.",
            "Hide the annotations and reread exactly the same sentence.",
            "Stop after a few cards; there is no timer, target speed or score.",
        ],
        "text_title": "Text-only by design",
        "text_note": (
            "The cards do not ask a learner to guess a word from a picture. Use "
            "picture books separately for story enjoyment and conversation; use "
            "these cards for a short, focused decoding pass."
        ),
        "print_note": (
            "Printing always shows the Zhuyin and removes the controls. Each sentence "
            "stays on one line; longer cards can be printed in landscape if preferred."
        ),
        "app_title": "Need sound and blending practice before sentences?",
        "app_text": (
            "Lumi Bopomofo is an optional practice layer for listening, tracing, "
            "tones and syllable blending. It has a one-time lifetime unlock with no "
            "ads, subscription or account. The free reading cards remain complete "
            "without the app."
        ),
        "app_cta": "Parents: see Lumi Bopomofo on the App Store",
        "sources": "Sources and scope",
        "source_labels": [
            "Taiwan Ministry of Education: Mandarin Phonetic Symbols handbook",
            "Taiwan Ministry of Education: standard character and Zhuyin forms",
            "CIRN: Mandarin learning outcomes for the first learning stage",
        ],
        "source_note": (
            "The official references support standard symbols, forms and first-stage "
            "goals such as reading Zhuyin material and reading text accurately. They "
            "do not prescribe, test or endorse this original card activity. Every "
            "sentence is original; no Ministry worksheet, image, audio or assessment "
            "is reproduced."
        ),
        "faq": [
            (
                "Does this tool calculate a reading level or score?",
                "No. It has no timer, correct/wrong button, total, level or saved progress.",
            ),
            (
                "Does hiding Zhuyin prove that a child has mastered reading?",
                "No. It creates a second pass through the same sentence; it is not proof of mastery, fluency or school readiness.",
            ),
            (
                "Why are there no pictures on the cards?",
                "The short card activity keeps attention on characters and their Zhuyin. Families can use picture books separately for stories, vocabulary and conversation.",
            ),
            (
                "Does any reading data leave the browser?",
                "No reading responses are collected. Card choices remain only in page memory and reset when the page closes.",
            ),
        ],
        "index_title": "Zhuyin Short Sentence Reading Cards",
        "index_description": (
            "Printable, progressive sentences with tap-to-hide Zhuyin and no scores or profiles."
        ),
    },
    "zh-Hant": {
        "title": "免費注音短句閱讀卡產生器｜分級、可列印",
        "description": (
            "免費產生可列印的注音短句閱讀卡，從三字短句進到兩段句；"
            "先看逐字注音，再遮住重讀。免登入、不計分、不上傳、不建立兒童檔案。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費・原創・私密",
        "heading": "注音短句閱讀卡產生器",
        "lead": (
            "孩子會拼單音，看到整句卻停住時，先讀一張完整標注注音的短句卡，"
            "再點一下遮住注音，重讀同一句；不計時，也不打分數。"
        ),
        "privacy": "不填姓名、免帳號、不計分、不上傳、不儲存兒童檔案",
        "scope": "原創文字練習；不是閱讀測驗、程度分級或診斷",
        "builder": "建立一組低壓力短句",
        "level_label": "選擇句子長度",
        "level_short": "三字短句",
        "level_everyday": "六至七字生活句",
        "level_clauses": "兩段式短句",
        "count": "句卡張數",
        "new_set": "換一組短句",
        "hide_all": "全部遮住注音",
        "show_all": "全部顯示注音",
        "print": "列印句卡",
        "share": "分享工具",
        "hide": "遮住注音",
        "show": "顯示注音",
        "kicker": "先看注音解碼，再遮住重讀",
        "ready": "目前顯示注音；先讀一次，再遮住做第二次。",
        "shared": "已開啟分享選單。",
        "cancelled": "已取消分享。",
        "copied": "已複製工具連結。",
        "copy_failed": "無法自動複製，請使用這個連結：",
        "short_help": (
            "先讀熟悉的主詞與動作。每個國字都有標準注音，詞組之間保留小間距。"
        ),
        "everyday_help": (
            "接著讀六至七字的生活句；看到詞組間距就稍停一下，不需要趕速度。"
        ),
        "clauses_help": (
            "短句讀得舒服後，再試兩段式句子；逗號就是自然停頓的位置。"
        ),
        "why_title": "從拼出一個音節，走到讀完一句話",
        "why_text": (
            "認符號、拼音節和讀完整句子是不同步驟。這組純文字句卡一次只加一層："
            "先讀短詞組，再讀完整句，最後遮住注音重讀同一句。"
        ),
        "routine_title": "四步驟重讀法",
        "routine": [
            "大人先示範一次，手指依序指向每個有注音的國字。",
            "孩子看著注音，按照自己的速度慢慢讀。",
            "遮住注音，再重讀完全相同的句子。",
            "一次幾張就好；沒有計時、目標速度或分數。",
        ],
        "text_title": "刻意不放猜字圖片",
        "text_note": (
            "短句卡把注意力留在國字與注音上，不要求孩子看圖猜字。繪本可另外用來"
            "享受故事、聊內容與累積詞彙；這裡只做短而專注的解碼練習。"
        ),
        "print_note": (
            "列印時會顯示全部注音並隱藏操作按鈕。每一句保持單行；較長句卡可改用"
            "橫向列印。"
        ),
        "app_title": "讀句子前，還想加強聽音與拼讀？",
        "app_text": (
            "Lumi 注音星球是選配的練習層，提供聽音、描寫、聲調與拼讀遊戲。"
            "一次付費永久解鎖，無廣告、無訂閱、免帳號；不使用 App 也能完整使用"
            "上方免費句卡。"
        ),
        "app_cta": "家長前往 App Store 查看 Lumi 注音星球",
        "sources": "資料來源與適用範圍",
        "source_labels": [
            "教育部《國語注音符號手冊》",
            "教育部常用國字標準字體筆順學習網",
            "CIRN 國語文第一學習階段學習重點",
        ],
        "source_note": (
            "官方資料只用來核對標準符號、字形，以及「利用注音讀物學習閱讀」與"
            "「正確朗讀文本」等第一學習階段目標；教育部沒有設計、測試或推薦本句卡。"
            "所有短句皆為本站原創，未重製教育部練習單、圖片、音檔或評量。"
        ),
        "faq": [
            (
                "這個工具會計算閱讀程度或分數嗎？",
                "不會。沒有計時、答對答錯按鈕、總分、等級或儲存進度。",
            ),
            (
                "遮住注音後讀出來，就代表已經熟練嗎？",
                "不能這樣判定。它只是讓孩子重讀同一句，不能證明熟練度、流暢度或入學準備度。",
            ),
            (
                "句卡為什麼不放圖片？",
                "短句活動把注意力留在國字與注音；繪本可另外用來享受故事、累積詞彙與親子對話。",
            ),
            (
                "閱讀資料會離開瀏覽器嗎？",
                "不會收集閱讀反應；選擇只留在目前頁面記憶體，關閉後即重設。",
            ),
        ],
        "index_title": "注音短句閱讀卡產生器",
        "index_description": "免費建立分級短句；可遮住注音重讀、列印，不計分也不建立兒童檔案。",
    },
}

STYLE = r"""
:root{--bg:#f3f1eb;--paper:#fffefb;--ink:#20211f;--muted:#66665f;--line:#ddd8cd;--forest:#315f50;--forest2:#4c806d;--sun:#c78a2c;--soft:#edf4f0;--shadow:0 18px 50px rgba(50,48,39,.10)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:radial-gradient(circle at 10% 0,#fff 0,var(--bg) 46%,#e9e5db 100%);color:var(--ink);line-height:1.65}
a{color:#285747}.wrap{width:min(1120px,100% - 30px);margin:auto}
.top{position:sticky;top:0;z-index:8;background:rgba(255,254,251,.9);border-bottom:1px solid rgba(221,216,205,.92);backdrop-filter:blur(14px)}
.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:18px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.nav-links{display:flex;gap:16px;align-items:center}.nav-links a{color:var(--muted);font-size:14px}
.hero{padding:58px 0 26px}.eyebrow{display:inline-flex;border:1px solid var(--line);background:rgba(255,255,255,.72);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:850;color:var(--forest);letter-spacing:.03em;white-space:nowrap}
h1{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(34px,6.5vw,66px);line-height:1.04;letter-spacing:-.035em;margin:.28em 0 .24em;max-width:100%;white-space:nowrap;overflow-x:auto;padding-bottom:.08em}
.lead{max-width:850px;color:var(--muted);font-size:clamp(17px,2.3vw,21px);margin:0}
.trust{display:flex;flex-wrap:wrap;gap:9px;margin:22px 0 0}.badge{border:1px solid #d8d3c8;background:#fff;border-radius:999px;padding:8px 12px;font-size:13px;font-weight:750;color:#3f5e52}.badge.scope{color:#695d49}
.workspace{background:rgba(255,254,251,.97);border:1px solid var(--line);border-radius:30px;padding:clamp(18px,4vw,34px);box-shadow:var(--shadow);margin:20px auto 34px}
.workspace h2,.content-card h2,.cta-card h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(24px,4vw,34px);line-height:1.15;margin:0}
.controls{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;margin:24px 0 14px;padding:18px;border-radius:22px;background:#f7f4ed;border:1px solid #e6e0d4}
.control-label{display:block;font-size:13px;font-weight:850;color:var(--muted);margin-bottom:8px;white-space:nowrap}.seg{display:flex;flex-wrap:wrap;gap:7px}.seg button,.button,select{font:inherit;font-weight:800;border-radius:999px;white-space:nowrap}
.seg button{border:1px solid var(--line);background:#fff;color:var(--muted);padding:9px 13px;cursor:pointer}.seg button.on{background:linear-gradient(135deg,var(--forest),var(--forest2));border-color:transparent;color:#fff;box-shadow:0 8px 18px rgba(49,95,80,.18)}
select{border:1px solid var(--line);background:#fff;color:var(--ink);padding:9px 36px 9px 13px;min-width:92px}.level-help{color:var(--muted);margin:0 0 18px;font-size:14px}
.actions{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0 20px}.button{border:0;background:linear-gradient(135deg,var(--forest),var(--forest2));color:#fff;padding:11px 16px;cursor:pointer;box-shadow:0 8px 20px rgba(49,95,80,.16)}.button.secondary{background:#fff;color:var(--forest);border:1px solid var(--line);box-shadow:none}
.status{min-height:1.5em;color:var(--muted);font-size:14px;margin:0 0 14px}
.cards{display:grid;grid-template-columns:1fr;gap:14px}.reading-card{background:linear-gradient(160deg,#fff,#fbfaf6);border:1px solid #dcd6ca;border-radius:24px;padding:18px 20px;box-shadow:0 8px 24px rgba(52,48,38,.06);break-inside:avoid;overflow:hidden}.card-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.card-kicker{color:var(--muted);font-size:12px;font-weight:800;white-space:nowrap;overflow-x:auto}.toggle{border:1px solid var(--line);background:#fff;color:var(--forest);border-radius:999px;padding:7px 11px;font:inherit;font-size:12px;font-weight:850;white-space:nowrap;cursor:pointer}.toggle:focus-visible{outline:3px solid #a7c8bb;outline-offset:3px}
.sentence{display:flex;align-items:flex-end;gap:clamp(12px,2.4vw,25px);font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(34px,7vw,58px);font-weight:850;line-height:1.15;margin:24px 0 5px;padding:24px 0 6px;white-space:nowrap;overflow-x:auto}.phrase{display:inline-flex;align-items:flex-end;white-space:nowrap}.sentence ruby{ruby-position:over;ruby-align:center;margin:0 .035em}.sentence rt{font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC",sans-serif;font-size:.34em;font-weight:800;color:var(--forest);letter-spacing:.01em}.sentence.reading-hidden rt{visibility:hidden}
.content-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin:30px auto}.content-card{grid-column:span 6;background:rgba(255,254,251,.92);border:1px solid var(--line);border-radius:26px;padding:25px}.content-card.full{grid-column:span 12}.content-card p{color:var(--muted);margin:.8em 0 0}.content-card ol{margin:14px 0 0;padding-left:22px;color:var(--muted)}.content-card li{margin:.55em 0}
.cta-card{background:linear-gradient(135deg,#254d41,#477562);color:#fff;border-radius:30px;padding:clamp(24px,5vw,40px);margin:32px auto}.cta-card p{color:#e8f0ec;max-width:820px}.cta-card .button{background:#fff;color:#244c40;box-shadow:none;text-decoration:none;display:inline-flex;margin-top:8px;white-space:nowrap}
.sources{margin:30px auto 54px;color:var(--muted);font-size:14px}.sources h2{color:var(--ink)}.sources p{max-width:920px}.faq-list{display:grid;gap:10px}.faq-list details{border:1px solid var(--line);border-radius:18px;background:#fff;padding:13px 16px}.faq-list summary{font-weight:850;cursor:pointer}.faq-list p{margin:.6em 0 0;color:var(--muted)}
@media(max-width:760px){.hero{padding-top:38px}.controls{grid-template-columns:1fr}.content-card{grid-column:span 12}.card-head{align-items:flex-start}.nav{align-items:flex-start;padding:13px 0}.sentence{gap:14px}}
@media print{.top,.hero,.controls,.actions,.status,.level-help,.content-grid,.cta-card,.sources,.workspace>h2,.card-head{display:none!important}body{background:#fff}.wrap{width:100%}.workspace{border:0;box-shadow:none;padding:0;margin:0}.cards{gap:8mm}.reading-card{border:1pt solid #777;border-radius:4mm;box-shadow:none;padding:7mm;page-break-inside:avoid}.sentence{font-size:26pt;overflow:visible;margin:5mm 0}.sentence rt{visibility:visible!important}@page{size:A4 landscape;margin:11mm}}
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def static_sentence_card(
    sentence: dict[str, object],
    index: int,
    copy: dict[str, object],
) -> str:
    phrases = []
    for item in sentence["phrases"]:
        tokens = "".join(
            (
                f"<ruby>{html.escape(token['char'])}"
                f"<rt>{html.escape(token['reading'])}</rt></ruby>"
            )
            for token in item["tokens"]
        )
        phrases.append(
            f'<span class="phrase">{tokens}{html.escape(item["after"])}</span>'
        )
    return (
        '<article class="reading-card"><div class="card-head">'
        f'<span class="card-kicker">{html.escape(copy["kicker"])}</span>'
        f'<button class="toggle" type="button" data-index="{index}" '
        f'aria-pressed="false">{html.escape(copy["hide"])}</button></div>'
        f'<p class="sentence">{"".join(phrases)}</p></article>'
    )


def render_page(locale: str) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    url = canonical(locale)
    alternate = canonical(other_locale)
    home = f"{SITE}/index.html" if locale == "en" else f"{SITE}/zh-Hant/index.html"
    tools = f"{SITE}/tools/" if locale == "en" else f"{SITE}/zh-Hant/tools/"
    app_campaign = f"{APP_URL}?ct=iag_zhuyin_sentence_reading_{locale.lower()}"
    level_help = {
        "short": t["short_help"],
        "everyday": t["everyday_help"],
        "clauses": t["clauses_help"],
    }
    client_copy = {
        "hide": t["hide"],
        "show": t["show"],
        "hideAll": t["hide_all"],
        "showAll": t["show_all"],
        "kicker": t["kicker"],
        "ready": t["ready"],
        "shared": t["shared"],
        "cancelled": t["cancelled"],
        "copied": t["copied"],
        "copyFailed": t["copy_failed"],
        "levelHelp": level_help,
        "shareTitle": t["heading"],
        "shareText": t["lead"],
    }
    schema = {
        "@context": "https://schema.org",
        "@type": ["WebApplication", "LearningResource"],
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any",
        "browserRequirements": "JavaScript",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "learningResourceType": "Parent-guided printable reading cards",
        "educationalUse": "Practice",
        "educationalLevel": "Beginner",
        "teaches": [
            "Reading short Traditional Chinese sentences with Zhuyin",
            "Phrase-by-phrase sentence decoding",
            "Rereading the same sentence without visible Zhuyin",
        ],
        "citation": [MOE_HANDBOOK, MOE_FORMS, MOE_CURRICULUM],
        "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
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
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": home},
            {"@type": "ListItem", "position": 2, "name": t["tools"], "item": tools},
            {"@type": "ListItem", "position": 3, "name": t["heading"], "item": url},
        ],
    }
    routine = "".join(f"<li>{html.escape(item)}</li>" for item in t["routine"])
    faq = "".join(
        (
            f"<details><summary>{html.escape(question)}</summary>"
            f"<p>{html.escape(answer)}</p></details>"
        )
        for question, answer in t["faq"]
    )
    sources = "".join(
        (
            f'<li><a href="{source}" rel="noopener noreferrer">'
            f"{html.escape(label)}</a></li>"
        )
        for source, label in zip(
            (MOE_HANDBOOK, MOE_FORMS, MOE_CURRICULUM),
            t["source_labels"],
            strict=True,
        )
    )
    initial_cards = "".join(
        static_sentence_card(sentence, index, t)
        for index, sentence in enumerate(SENTENCES["short"][:3])
    )
    data_json = json.dumps(SENTENCES, ensure_ascii=False).replace("</", "<\\/")
    copy_json = json.dumps(client_copy, ensure_ascii=False).replace("</", "<\\/")

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
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="nav-links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap">
<div class="eyebrow">{html.escape(t["eyebrow"])}</div>
<h1>{html.escape(t["heading"])}</h1>
<p class="lead">{html.escape(t["lead"])}</p>
<div class="trust"><span class="badge">{html.escape(t["privacy"])}</span><span class="badge scope">{html.escape(t["scope"])}</span></div>
</section>
<section class="workspace wrap" id="generator">
<h2>{html.escape(t["builder"])}</h2>
<div class="controls">
<div><span class="control-label">{html.escape(t["level_label"])}</span><div class="seg" id="level-buttons" role="group" aria-label="{html.escape(t["level_label"])}"><button type="button" class="on" data-level="short">{html.escape(t["level_short"])}</button><button type="button" data-level="everyday">{html.escape(t["level_everyday"])}</button><button type="button" data-level="clauses">{html.escape(t["level_clauses"])}</button></div></div>
<label><span class="control-label">{html.escape(t["count"])}</span><select id="card-count"><option value="3">3</option><option value="6" selected>6</option><option value="8">8</option></select></label>
</div>
<p class="level-help" id="level-help">{html.escape(t["short_help"])}</p>
<div class="actions"><button class="button" id="new-set" type="button">{html.escape(t["new_set"])}</button><button class="button secondary" id="toggle-all" type="button">{html.escape(t["hide_all"])}</button><button class="button secondary" id="print-cards" type="button">{html.escape(t["print"])}</button><button class="button secondary" id="share-tool" type="button">{html.escape(t["share"])}</button></div>
<p class="status" id="status" aria-live="polite">{html.escape(t["ready"])}</p>
<div class="cards" id="cards">{initial_cards}</div>
<p class="level-help">{html.escape(t["print_note"])}</p>
</section>
<section class="content-grid wrap">
<article class="content-card"><h2>{html.escape(t["why_title"])}</h2><p>{html.escape(t["why_text"])}</p></article>
<article class="content-card"><h2>{html.escape(t["routine_title"])}</h2><ol>{routine}</ol></article>
<article class="content-card full"><h2>{html.escape(t["text_title"])}</h2><p>{html.escape(t["text_note"])}</p></article>
</section>
<section class="cta-card wrap"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_campaign, quote=True)}">{html.escape(t["app_cta"])}</a></section>
<section class="sources wrap"><h2>{html.escape(t["sources"])}</h2><ul>{sources}</ul><p>{html.escape(t["source_note"])}</p><div class="faq-list">{faq}</div></section>
</main>
<script>
const DATA={data_json};
const COPY={copy_json};
let level="short";
let count=6;
let batch=[];
let hidden=new Set();
const cards=document.getElementById("cards");
const countSelect=document.getElementById("card-count");
const toggleAll=document.getElementById("toggle-all");
const status=document.getElementById("status");
const levelHelp=document.getElementById("level-help");

function shuffle(items){{
  const result=[...items];
  for(let i=result.length-1;i>0;i--){{
    const j=Math.floor(Math.random()*(i+1));
    [result[i],result[j]]=[result[j],result[i]];
  }}
  return result;
}}

function makeBatch(){{
  batch=shuffle(DATA[level]).slice(0,Math.min(count,DATA[level].length));
  hidden=new Set();
  status.textContent=COPY.ready;
  render();
}}

function sentenceHTML(item,index){{
  const isHidden=hidden.has(index);
  const phrases=item.phrases.map(phrase=>{{
    const tokens=phrase.tokens.map(token=>`<ruby>${{token.char}}<rt>${{token.reading}}</rt></ruby>`).join("");
    return `<span class="phrase">${{tokens}}${{phrase.after||""}}</span>`;
  }}).join("");
  return `<article class="reading-card"><div class="card-head"><span class="card-kicker">${{COPY.kicker}}</span><button class="toggle" type="button" data-index="${{index}}" aria-pressed="${{isHidden}}">${{isHidden?COPY.show:COPY.hide}}</button></div><p class="sentence ${{isHidden?"reading-hidden":""}}">${{phrases}}</p></article>`;
}}

function render(){{
  cards.innerHTML=batch.map(sentenceHTML).join("");
  const allHidden=batch.length>0&&hidden.size===batch.length;
  toggleAll.textContent=allHidden?COPY.showAll:COPY.hideAll;
  levelHelp.textContent=COPY.levelHelp[level];
}}

document.getElementById("level-buttons").addEventListener("click",event=>{{
  const button=event.target.closest("button[data-level]");
  if(!button)return;
  level=button.dataset.level;
  document.querySelectorAll("#level-buttons button").forEach(item=>item.classList.toggle("on",item===button));
  makeBatch();
}});
countSelect.addEventListener("change",()=>{{count=Number(countSelect.value);makeBatch();}});
document.getElementById("new-set").addEventListener("click",makeBatch);
cards.addEventListener("click",event=>{{
  const button=event.target.closest("button[data-index]");
  if(!button)return;
  const index=Number(button.dataset.index);
  hidden.has(index)?hidden.delete(index):hidden.add(index);
  render();
}});
toggleAll.addEventListener("click",()=>{{
  if(hidden.size===batch.length)hidden.clear();
  else hidden=new Set(batch.map((_,index)=>index));
  render();
}});
document.getElementById("print-cards").addEventListener("click",()=>window.print());
document.getElementById("share-tool").addEventListener("click",async()=>{{
  const payload={{title:COPY.shareTitle,text:COPY.shareText,url:window.location.href}};
  if(navigator.share){{
    try{{
      await navigator.share(payload);
      status.textContent=COPY.shared;
      return;
    }}catch(error){{
      if(error&&error.name==="AbortError"){{
        status.textContent=COPY.cancelled;
        return;
      }}
    }}
  }}
  try{{
    await navigator.clipboard.writeText(window.location.href);
    status.textContent=COPY.copied;
  }}catch(error){{
    status.textContent=`${{COPY.copyFailed}} ${{window.location.href}}`;
  }}
}});
makeBatch();
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
        r'zhuyin-blending-card-generator\.html">.*?</article>)',
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
    changed = 0
    changed += _update_one_index(pages / "tools" / "index.html", "en")
    changed += _update_one_index(
        pages / "zh-Hant" / "tools" / "index.html", "zh-Hant"
    )
    return changed


def build(pages: Path = PAGES) -> list[str]:
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        target = pages / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(locale), encoding="utf-8")
        outputs.append(canonical(locale))
    update_tools_indexes(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"zhuyin sentence reading cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
