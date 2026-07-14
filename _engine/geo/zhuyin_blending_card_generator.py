#!/usr/bin/env python3
"""Generate bilingual, private Zhuyin blending practice cards."""

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
SLUG = "zhuyin-blending-card-generator"
CONTENT_DATE = "2026-07-14"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/"
    "juyin/html_ch/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=0"
APP_URL = appstore_url("lumibopomofo")

BLENDS = {
    "two": [
        {"parts": ["ㄅ", "ㄚ"], "blend": "ㄅㄚ", "word": "爸", "reading": "ㄅㄚˋ"},
        {"parts": ["ㄆ", "ㄛ"], "blend": "ㄆㄛ", "word": "坡", "reading": "ㄆㄛ"},
        {"parts": ["ㄇ", "ㄧ"], "blend": "ㄇㄧ", "word": "米", "reading": "ㄇㄧˇ"},
        {"parts": ["ㄈ", "ㄟ"], "blend": "ㄈㄟ", "word": "飛", "reading": "ㄈㄟ"},
        {"parts": ["ㄉ", "ㄚ"], "blend": "ㄉㄚ", "word": "大", "reading": "ㄉㄚˋ"},
        {"parts": ["ㄊ", "ㄨ"], "blend": "ㄊㄨ", "word": "兔", "reading": "ㄊㄨˋ"},
        {"parts": ["ㄋ", "ㄧ"], "blend": "ㄋㄧ", "word": "你", "reading": "ㄋㄧˇ"},
        {"parts": ["ㄌ", "ㄧ"], "blend": "ㄌㄧ", "word": "梨", "reading": "ㄌㄧˊ"},
        {"parts": ["ㄍ", "ㄡ"], "blend": "ㄍㄡ", "word": "狗", "reading": "ㄍㄡˇ"},
        {"parts": ["ㄎ", "ㄢ"], "blend": "ㄎㄢ", "word": "看", "reading": "ㄎㄢˋ"},
        {"parts": ["ㄏ", "ㄠ"], "blend": "ㄏㄠ", "word": "好", "reading": "ㄏㄠˇ"},
        {"parts": ["ㄓ", "ㄨ"], "blend": "ㄓㄨ", "word": "豬", "reading": "ㄓㄨ"},
        {"parts": ["ㄔ", "ㄜ"], "blend": "ㄔㄜ", "word": "車", "reading": "ㄔㄜ"},
        {"parts": ["ㄕ", "ㄨ"], "blend": "ㄕㄨ", "word": "書", "reading": "ㄕㄨ"},
        {"parts": ["ㄖ", "ㄣ"], "blend": "ㄖㄣ", "word": "人", "reading": "ㄖㄣˊ"},
        {"parts": ["ㄙ", "ㄢ"], "blend": "ㄙㄢ", "word": "三", "reading": "ㄙㄢ"},
    ],
    "three": [
        {
            "parts": ["ㄐ", "ㄧ", "ㄚ"],
            "blend": "ㄐㄧㄚ",
            "word": "家",
            "reading": "ㄐㄧㄚ",
        },
        {
            "parts": ["ㄑ", "ㄧ", "ㄡ"],
            "blend": "ㄑㄧㄡ",
            "word": "球",
            "reading": "ㄑㄧㄡˊ",
        },
        {
            "parts": ["ㄒ", "ㄧ", "ㄠ"],
            "blend": "ㄒㄧㄠ",
            "word": "小",
            "reading": "ㄒㄧㄠˇ",
        },
        {
            "parts": ["ㄉ", "ㄧ", "ㄢ"],
            "blend": "ㄉㄧㄢ",
            "word": "電",
            "reading": "ㄉㄧㄢˋ",
        },
        {
            "parts": ["ㄊ", "ㄧ", "ㄢ"],
            "blend": "ㄊㄧㄢ",
            "word": "天",
            "reading": "ㄊㄧㄢ",
        },
        {
            "parts": ["ㄋ", "ㄧ", "ㄠ"],
            "blend": "ㄋㄧㄠ",
            "word": "鳥",
            "reading": "ㄋㄧㄠˇ",
        },
        {
            "parts": ["ㄌ", "ㄧ", "ㄥ"],
            "blend": "ㄌㄧㄥ",
            "word": "零",
            "reading": "ㄌㄧㄥˊ",
        },
        {
            "parts": ["ㄍ", "ㄨ", "ㄚ"],
            "blend": "ㄍㄨㄚ",
            "word": "瓜",
            "reading": "ㄍㄨㄚ",
        },
        {
            "parts": ["ㄎ", "ㄨ", "ㄞ"],
            "blend": "ㄎㄨㄞ",
            "word": "快",
            "reading": "ㄎㄨㄞˋ",
        },
        {
            "parts": ["ㄏ", "ㄨ", "ㄚ"],
            "blend": "ㄏㄨㄚ",
            "word": "花",
            "reading": "ㄏㄨㄚ",
        },
        {
            "parts": ["ㄓ", "ㄨ", "ㄥ"],
            "blend": "ㄓㄨㄥ",
            "word": "中",
            "reading": "ㄓㄨㄥ",
        },
        {
            "parts": ["ㄔ", "ㄨ", "ㄤ"],
            "blend": "ㄔㄨㄤ",
            "word": "床",
            "reading": "ㄔㄨㄤˊ",
        },
        {
            "parts": ["ㄕ", "ㄨ", "ㄟ"],
            "blend": "ㄕㄨㄟ",
            "word": "水",
            "reading": "ㄕㄨㄟˇ",
        },
        {
            "parts": ["ㄖ", "ㄨ", "ㄢ"],
            "blend": "ㄖㄨㄢ",
            "word": "軟",
            "reading": "ㄖㄨㄢˇ",
        },
        {
            "parts": ["ㄗ", "ㄨ", "ㄟ"],
            "blend": "ㄗㄨㄟ",
            "word": "嘴",
            "reading": "ㄗㄨㄟˇ",
        },
        {
            "parts": ["ㄙ", "ㄨ", "ㄢ"],
            "blend": "ㄙㄨㄢ",
            "word": "酸",
            "reading": "ㄙㄨㄢ",
        },
    ],
    "tones": [
        {
            "base": "ㄇㄚ",
            "items": [
                {"word": "媽", "reading": "ㄇㄚ"},
                {"word": "麻", "reading": "ㄇㄚˊ"},
                {"word": "馬", "reading": "ㄇㄚˇ"},
                {"word": "罵", "reading": "ㄇㄚˋ"},
            ],
        },
        {
            "base": "ㄅㄚ",
            "items": [
                {"word": "八", "reading": "ㄅㄚ"},
                {"word": "拔", "reading": "ㄅㄚˊ"},
                {"word": "把", "reading": "ㄅㄚˇ"},
                {"word": "爸", "reading": "ㄅㄚˋ"},
            ],
        },
        {
            "base": "ㄉㄚ",
            "items": [
                {"word": "搭", "reading": "ㄉㄚ"},
                {"word": "達", "reading": "ㄉㄚˊ"},
                {"word": "打", "reading": "ㄉㄚˇ"},
                {"word": "大", "reading": "ㄉㄚˋ"},
            ],
        },
        {
            "base": "ㄊㄤ",
            "items": [
                {"word": "湯", "reading": "ㄊㄤ"},
                {"word": "糖", "reading": "ㄊㄤˊ"},
                {"word": "躺", "reading": "ㄊㄤˇ"},
                {"word": "燙", "reading": "ㄊㄤˋ"},
            ],
        },
    ],
}

COPY = {
    "en": {
        "title": "Free Zhuyin Blending Practice Card Generator",
        "description": (
            "Make private, printable Zhuyin practice cards for two-symbol joins, "
            "three-symbol joins and Mandarin tones. No score, login, upload or profile."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · private · no score",
        "heading": "Zhuyin blending practice cards",
        "lead": (
            "For a child who can recognise ㄅㄆㄇ but pauses when symbols need to "
            "be joined. Build a short set, say each part slowly, slide the sounds "
            "together, then reveal a familiar word."
        ),
        "privacy": "No name, account, score, upload or saved profile",
        "scope": "Original practice activity; not a test or diagnosis",
        "builder": "Build a short practice set",
        "mode_label": "Choose one step",
        "mode_two": "Two-symbol joins",
        "mode_three": "Three-symbol joins",
        "mode_tones": "Tone ladder",
        "count": "Cards",
        "new_set": "New set",
        "reveal_all": "Reveal all",
        "hide_all": "Hide all",
        "print": "Print cards",
        "share": "Share tool",
        "tap": "Tap to reveal",
        "hide": "Tap to hide",
        "prompt": "Say each part, then join",
        "tone_prompt": "Blend the base, then try four tones",
        "ready": "Tap any card to reveal its joined syllable and familiar word.",
        "shared": "Share sheet opened.",
        "cancelled": "Sharing was cancelled.",
        "copied": "Tool link copied.",
        "copy_failed": "Copy was unavailable. Use this link:",
        "two_help": (
            "Point to the first symbol, pause, say the second, then slide your "
            "finger toward the joined syllable."
        ),
        "three_help": (
            "Keep the middle ㄧ, ㄨ or ㄩ connected like a bridge. Join all three "
            "without turning the activity into a speed test."
        ),
        "tones_help": (
            "Blend the unmarked base first. Reveal the familiar words only when "
            "the base is comfortable."
        ),
        "why_title": "Recognition and blending are different steps",
        "why_text": (
            "A symbol flashcard asks “what is this?” These cards ask the next "
            "question: “how do these sounds become one syllable?” The generator "
            "uses a small curated set of familiar Mandarin examples, not every "
            "possible syllable."
        ),
        "routine_title": "A calm four-step routine",
        "routine": [
            "Point to each visible symbol without asking for speed.",
            "Say the parts with a short pause between them.",
            "Move a finger across the card while shortening the pause.",
            "Reveal the joined syllable and connect it to the familiar word.",
        ],
        "gentle_title": "Keep it low-pressure",
        "gentle_text": (
            "Use only a few cards at a time. Repeat, switch sets or stop whenever "
            "the child wants. This tool records no answers and cannot measure "
            "mastery, readiness or a learning difficulty."
        ),
        "print_note": (
            "Printing reveals every answer and removes the controls. Cut the cards "
            "apart or keep them on one sheet for finger-sliding practice."
        ),
        "app_title": "Want guided audio after the paper activity?",
        "app_text": (
            "Lumi Bopomofo is an optional next step with guided listening, tracing, "
            "tones and syllable-blending games. It uses a one-time lifetime unlock "
            "with no ads, subscription or account."
        ),
        "app_cta": "See Lumi Bopomofo on the App Store",
        "sources": "Sources and scope",
        "source_labels": [
            "Taiwan Ministry of Education: Mandarin Phonetic Symbols handbook",
            "Taiwan Ministry of Education: standard character and Zhuyin forms",
        ],
        "source_note": (
            "The official references support standard symbols, notation and forms. "
            "They do not prescribe, evaluate or endorse this original card activity. "
            "No Ministry images, audio, animations or worksheets are reproduced."
        ),
        "faq": [
            (
                "Does this tool score my child?",
                "No. It has no correct/wrong buttons, timer, score, level or saved progress.",
            ),
            (
                "Is this a complete Mandarin syllable table?",
                "No. It is a short practice generator using familiar examples for joining sounds and comparing four tones.",
            ),
            (
                "Does the tool diagnose a learning difficulty or school readiness?",
                "No. It is a parent-guided practice activity, not an assessment, diagnosis or readiness measure.",
            ),
            (
                "Does any practice data leave the browser?",
                "No practice answers are collected. Selections stay in page memory and reset when the page closes.",
            ),
        ],
        "index_title": "Zhuyin Blending Practice Cards",
        "index_description": (
            "Printable two-symbol, three-symbol and tone practice with no scores or profiles."
        ),
    },
    "zh-Hant": {
        "title": "免費注音拼讀練習卡產生器｜二拼、三拼與聲調",
        "description": (
            "免費產生可列印的注音拼讀練習卡：練二符拼讀、三符拼讀與四聲。"
            "不計分、免登入、不上傳、不建立兒童檔案。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費・私密・不計分",
        "heading": "注音拼讀練習卡產生器",
        "lead": (
            "孩子會認 ㄅㄆㄇ，合起來卻常停住時，可先做短短一組拼讀卡："
            "慢慢念每個符號、用手指把聲音滑近，再翻卡看熟悉的例字。"
        ),
        "privacy": "不填姓名、免帳號、不計分、不上傳、不儲存個人檔案",
        "scope": "原創練習活動；不是測驗、診斷或入學準備度判定",
        "builder": "建立一組短練習",
        "mode_label": "選一個練習步驟",
        "mode_two": "二符拼讀",
        "mode_three": "三符拼讀",
        "mode_tones": "四聲階梯",
        "count": "卡片張數",
        "new_set": "換一組",
        "reveal_all": "全部翻開",
        "hide_all": "全部蓋回",
        "print": "列印練習卡",
        "share": "分享工具",
        "tap": "點卡看答案",
        "hide": "點卡蓋回",
        "prompt": "分開念，再合起來",
        "tone_prompt": "先拼底音，再試四聲",
        "ready": "點任何卡片，即可翻開拼讀結果與熟悉例字。",
        "shared": "已開啟分享選單。",
        "cancelled": "已取消分享。",
        "copied": "已複製工具連結。",
        "copy_failed": "無法自動複製，請使用這個連結：",
        "two_help": (
            "先指第一個符號，停一下再念第二個；接著用手指往右滑，"
            "把停頓慢慢縮短。"
        ),
        "three_help": (
            "把中間的 ㄧ、ㄨ 或 ㄩ 當成橋，三個聲音連在一起即可；"
            "不需要計時，也不用比速度。"
        ),
        "tones_help": (
            "先把沒有聲調記號的底音拼順，再翻卡連結四個熟悉例字。"
        ),
        "why_title": "認得符號，和把聲音拼起來是不同步驟",
        "why_text": (
            "一般符號字卡問的是「這是什麼？」；這組卡接著練「這些聲音怎麼合成"
            "一個音節？」工具只使用一小組熟悉的華語例字，不是完整音節表。"
        ),
        "routine_title": "低壓力四步驟",
        "routine": [
            "先指每個看得到的符號，不催速度。",
            "把每個聲音分開念，中間留一點停頓。",
            "手指沿著卡片往右滑，同時慢慢縮短停頓。",
            "翻開完整拼音，再連到下方的熟悉例字。",
        ],
        "gentle_title": "一次幾張就好",
        "gentle_text": (
            "可以重複、換組，或在孩子不想繼續時停下來。工具不記錄答案，"
            "也不能衡量熟練度、入學準備度或判定任何學習困難。"
        ),
        "print_note": (
            "列印時會自動顯示全部答案並隱藏操作按鈕。可剪成小卡，"
            "也可保留整張做手指滑讀。"
        ),
        "app_title": "紙卡之後想要有引導音檔？",
        "app_text": (
            "Lumi 注音星球是選配的下一步，提供聽音、描寫、聲調與拼讀遊戲。"
            "一次付費永久解鎖，無廣告、無訂閱、免帳號。"
        ),
        "app_cta": "前往 App Store 查看 Lumi 注音星球",
        "sources": "資料來源與適用範圍",
        "source_labels": [
            "教育部《國語注音符號手冊》",
            "教育部常用國字標準字體筆順學習網",
        ],
        "source_note": (
            "官方資料只用來核對標準符號、標音與字形；教育部沒有設計、測試或"
            "推薦本練習卡。本站未重製教育部圖片、音檔、動畫或練習單。"
        ),
        "faq": [
            (
                "這個工具會替孩子打分數嗎？",
                "不會。沒有答對答錯按鈕、計時、分數、等級或儲存進度。",
            ),
            (
                "這是完整的國語音節表嗎？",
                "不是。這是用熟悉例字練習合音與四聲的小型產生器。",
            ),
            (
                "它能判斷學習困難或入學準備度嗎？",
                "不能。這是家長陪伴的練習活動，不是評量、診斷或準備度測驗。",
            ),
            (
                "練習資料會離開瀏覽器嗎？",
                "不會收集練習答案；選項只留在目前頁面的記憶體，關閉後即重設。",
            ),
        ],
        "index_title": "注音拼讀練習卡產生器",
        "index_description": "免費建立二符、三符與四聲練習卡；不計分、不建立兒童檔案。",
    },
}

STYLE = r"""
:root{--bg:#f5f2ec;--paper:#fffdf9;--ink:#20201f;--muted:#68645d;--line:#ded8ce;--plum:#65507b;--plum2:#8b6ba8;--sage:#6f8874;--gold:#c08a3f;--soft:#f2ebf7;--shadow:0 18px 50px rgba(63,48,38,.10)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:radial-gradient(circle at 10% 0,#fff 0,var(--bg) 45%,#eee8df 100%);color:var(--ink);line-height:1.65}
a{color:#51406b}.wrap{width:min(1120px,100% - 30px);margin:auto}
.top{position:sticky;top:0;z-index:8;background:rgba(255,253,249,.88);border-bottom:1px solid rgba(222,216,206,.9);backdrop-filter:blur(14px)}
.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:18px}.nav a{text-decoration:none;font-weight:800}.nav-links{display:flex;gap:16px;align-items:center}.nav-links a{color:var(--muted);font-size:14px;white-space:nowrap}
.hero{padding:58px 0 26px}.eyebrow{display:inline-flex;border:1px solid var(--line);background:rgba(255,255,255,.7);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:850;color:var(--plum);letter-spacing:.03em}
h1{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(38px,7vw,70px);line-height:1.02;letter-spacing:-.035em;margin:.28em 0 .24em;max-width:880px}
.lead{max-width:820px;color:var(--muted);font-size:clamp(17px,2.3vw,21px);margin:0}
.trust{display:flex;flex-wrap:wrap;gap:9px;margin:22px 0 0}.badge{border:1px solid #d9d2c7;background:#fff;border-radius:999px;padding:8px 12px;font-size:13px;font-weight:750;color:#4f5e52}.badge.scope{color:#675774}
.workspace{background:rgba(255,253,249,.96);border:1px solid var(--line);border-radius:30px;padding:clamp(18px,4vw,34px);box-shadow:var(--shadow);margin:20px auto 34px}
.workspace-head{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.workspace h2,.content-card h2,.cta-card h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(24px,4vw,34px);line-height:1.15;margin:0}
.controls{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;margin:24px 0 14px;padding:18px;border-radius:22px;background:#f8f4ee;border:1px solid #e7e0d6}
.control-label{display:block;font-size:13px;font-weight:850;color:var(--muted);margin-bottom:8px}.seg{display:flex;flex-wrap:wrap;gap:7px}.seg button,.button,select{font:inherit;font-weight:800;border-radius:999px;white-space:nowrap}
.seg button{border:1px solid var(--line);background:#fff;color:var(--muted);padding:9px 13px;cursor:pointer}.seg button.on{background:linear-gradient(135deg,var(--plum),var(--plum2));border-color:transparent;color:#fff;box-shadow:0 8px 18px rgba(101,80,123,.18)}
select{border:1px solid var(--line);background:#fff;color:var(--ink);padding:9px 36px 9px 13px;min-width:92px}.mode-help{color:var(--muted);margin:0 0 18px;font-size:14px}
.actions{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0 20px}.button{border:0;background:linear-gradient(135deg,var(--plum),var(--plum2));color:#fff;padding:11px 16px;cursor:pointer;box-shadow:0 8px 20px rgba(101,80,123,.16)}.button.secondary{background:#fff;color:var(--plum);border:1px solid var(--line);box-shadow:none}
.status{min-height:1.5em;color:var(--muted);font-size:14px;margin:0 0 14px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.practice-card{appearance:none;width:100%;min-width:0;text-align:left;background:linear-gradient(160deg,#fff,#fcfaf6);border:1px solid #dcd4c8;border-radius:24px;padding:18px;color:var(--ink);font:inherit;cursor:pointer;box-shadow:0 8px 24px rgba(52,45,38,.06);break-inside:avoid}.practice-card:focus-visible{outline:3px solid #b9a2cf;outline-offset:3px}.practice-card.revealed{border-color:#aa98bc;background:linear-gradient(160deg,#fff,#f7f1fb)}
.card-kicker{display:block;color:var(--muted);font-size:12px;font-weight:800;margin-bottom:12px}.equation{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.symbol{display:inline-flex;align-items:center;justify-content:center;min-width:54px;height:58px;border:1px solid #d9d0c4;border-radius:16px;background:#fff;font-size:35px;font-weight:850;line-height:1}.join{font-size:25px;color:var(--gold);font-weight:900}.joined{font-size:37px;font-weight:900;color:var(--plum);white-space:nowrap}.mask{display:inline-flex;align-items:center;justify-content:center;min-width:64px;height:58px;border:1px dashed #baaebf;border-radius:16px;color:#988ca0;font-size:28px}.practice-card:not(.revealed) .joined,.practice-card:not(.revealed) .answer{display:none}.practice-card.revealed .mask{display:none}
.answer{border-top:1px solid var(--line);margin-top:14px;padding-top:12px;display:flex;align-items:baseline;gap:10px}.word{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:32px;font-weight:850}.reading{font-size:23px;font-weight:850;color:var(--sage);white-space:nowrap}.tap{display:block;color:var(--plum);font-size:12px;font-weight:800;text-align:right;margin-top:10px}
.tone-base{font-size:40px;font-weight:900;color:var(--plum);margin-bottom:12px}.tone-row{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.tone-item{border:1px solid var(--line);border-radius:14px;padding:9px 5px;text-align:center;background:#fff}.tone-num{display:block;color:var(--muted);font-size:11px;font-weight:800}.tone-word{font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:25px;font-weight:850}.tone-reading{display:block;color:var(--sage);font-size:15px;font-weight:850;white-space:nowrap}.practice-card:not(.revealed) .tone-word,.practice-card:not(.revealed) .tone-reading{visibility:hidden}
.content-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin:30px auto}.content-card{grid-column:span 6;background:rgba(255,253,249,.9);border:1px solid var(--line);border-radius:26px;padding:25px}.content-card.full{grid-column:span 12}.content-card p{color:var(--muted);margin:.8em 0 0}.content-card ol,.content-card ul{margin:14px 0 0;padding-left:22px;color:var(--muted)}.content-card li{margin:.55em 0}
.cta-card{background:linear-gradient(135deg,#443651,#6c517f);color:#fff;border-radius:30px;padding:clamp(24px,5vw,40px);margin:32px auto}.cta-card p{color:#eee5f3;max-width:800px}.cta-card .button{background:#fff;color:#4c3b5a;box-shadow:none;text-decoration:none;display:inline-flex;margin-top:8px}
.sources{margin:30px auto 54px;color:var(--muted);font-size:14px}.sources h2{color:var(--ink)}.sources p{max-width:900px}.faq-list{display:grid;gap:10px}.faq-list details{border:1px solid var(--line);border-radius:18px;background:#fff;padding:13px 16px}.faq-list summary{font-weight:850;cursor:pointer}.faq-list p{margin:.6em 0 0;color:var(--muted)}
@media(max-width:760px){.hero{padding-top:38px}.workspace-head{display:block}.controls{grid-template-columns:1fr}.cards{grid-template-columns:1fr}.content-card{grid-column:span 12}.tone-row{gap:4px}.tone-item{padding:8px 2px}.tone-reading{font-size:13px}.nav{align-items:flex-start;padding:13px 0}}
@media print{.top,.hero,.controls,.actions,.status,.mode-help,.tap,.content-grid,.cta-card,.sources,.workspace-head{display:none!important}body{background:#fff}.wrap{width:100%}.workspace{border:0;box-shadow:none;padding:0;margin:0}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:8mm}.practice-card{border:1pt solid #777;border-radius:4mm;box-shadow:none;padding:6mm;page-break-inside:avoid}.practice-card .joined,.practice-card .answer{display:flex!important}.practice-card .mask{display:none!important}.practice-card .tone-word,.practice-card .tone-reading{visibility:visible!important}.practice-card:not(.revealed) .answer{display:flex!important}@page{size:A4;margin:11mm}}
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def render_page(locale: str) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    url = canonical(locale)
    alternate = canonical(other_locale)
    home = f"{SITE}/index.html" if locale == "en" else f"{SITE}/zh-Hant/index.html"
    tools = f"{SITE}/tools/" if locale == "en" else f"{SITE}/zh-Hant/tools/"
    app_campaign = f"{APP_URL}?ct=iag_zhuyin_blending_{locale.lower()}"
    mode_help = {
        "two": t["two_help"],
        "three": t["three_help"],
        "tones": t["tones_help"],
    }
    client_copy = {
        "tap": t["tap"],
        "hide": t["hide"],
        "prompt": t["prompt"],
        "tonePrompt": t["tone_prompt"],
        "ready": t["ready"],
        "shared": t["shared"],
        "cancelled": t["cancelled"],
        "copied": t["copied"],
        "copyFailed": t["copy_failed"],
        "revealAll": t["reveal_all"],
        "hideAll": t["hide_all"],
        "modeHelp": mode_help,
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
        "learningResourceType": "Parent-guided printable practice cards",
        "educationalUse": "Practice",
        "educationalLevel": "Beginner",
        "teaches": [
            "Zhuyin syllable blending",
            "Two-symbol Zhuyin combinations",
            "Three-symbol Zhuyin combinations",
            "Mandarin tone comparison",
        ],
        "citation": [MOE_HANDBOOK, MOE_PRACTICE],
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
            (MOE_HANDBOOK, MOE_PRACTICE), t["source_labels"], strict=True
        )
    )
    data_json = json.dumps(BLENDS, ensure_ascii=False).replace("</", "<\\/")
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
<div class="workspace-head"><div><h2>{html.escape(t["builder"])}</h2></div></div>
<div class="controls">
<div><span class="control-label">{html.escape(t["mode_label"])}</span><div class="seg" id="mode-buttons" role="group" aria-label="{html.escape(t["mode_label"])}"><button type="button" class="on" data-mode="two">{html.escape(t["mode_two"])}</button><button type="button" data-mode="three">{html.escape(t["mode_three"])}</button><button type="button" data-mode="tones">{html.escape(t["mode_tones"])}</button></div></div>
<label><span class="control-label">{html.escape(t["count"])}</span><select id="card-count"><option value="4">4</option><option value="8" selected>8</option><option value="12">12</option></select></label>
</div>
<p class="mode-help" id="mode-help">{html.escape(t["two_help"])}</p>
<div class="actions"><button class="button" id="new-set" type="button">{html.escape(t["new_set"])}</button><button class="button secondary" id="reveal-all" type="button">{html.escape(t["reveal_all"])}</button><button class="button secondary" id="print-cards" type="button">{html.escape(t["print"])}</button><button class="button secondary" id="share-tool" type="button">{html.escape(t["share"])}</button></div>
<p class="status" id="status" aria-live="polite">{html.escape(t["ready"])}</p>
<div class="cards" id="cards"></div>
<p class="mode-help">{html.escape(t["print_note"])}</p>
</section>
<section class="content-grid wrap">
<article class="content-card"><h2>{html.escape(t["why_title"])}</h2><p>{html.escape(t["why_text"])}</p></article>
<article class="content-card"><h2>{html.escape(t["routine_title"])}</h2><ol>{routine}</ol></article>
<article class="content-card full"><h2>{html.escape(t["gentle_title"])}</h2><p>{html.escape(t["gentle_text"])}</p></article>
</section>
<section class="cta-card wrap"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_campaign, quote=True)}">{html.escape(t["app_cta"])}</a></section>
<section class="sources wrap"><h2>{html.escape(t["sources"])}</h2><ul>{sources}</ul><p>{html.escape(t["source_note"])}</p><div class="faq-list">{faq}</div></section>
</main>
<script>
const DATA={data_json};
const COPY={copy_json};
let mode="two";
let count=8;
let batch=[];
let revealed=new Set();
const cards=document.getElementById("cards");
const countSelect=document.getElementById("card-count");
const revealButton=document.getElementById("reveal-all");
const status=document.getElementById("status");
const modeHelp=document.getElementById("mode-help");

function shuffle(items){{
  const result=[...items];
  for(let i=result.length-1;i>0;i--){{
    const j=Math.floor(Math.random()*(i+1));
    [result[i],result[j]]=[result[j],result[i]];
  }}
  return result;
}}

function makeBatch(){{
  const requested=mode==="tones"?DATA.tones.length:count;
  batch=shuffle(DATA[mode]).slice(0,Math.min(requested,DATA[mode].length));
  revealed=new Set();
  render();
}}

function blendCard(item,index){{
  const isOpen=revealed.has(index);
  const symbols=item.parts.map(part=>`<span class="symbol">${{part}}</span>`).join('<span class="join">+</span>');
  return `<button class="practice-card ${{isOpen?"revealed":""}}" type="button" data-index="${{index}}" aria-expanded="${{isOpen}}"><span class="card-kicker">${{COPY.prompt}}</span><div class="equation">${{symbols}}<span class="join">→</span><span class="mask">?</span><span class="joined">${{item.blend}}</span></div><span class="answer"><span class="word">${{item.word}}</span><span class="reading">${{item.reading}}</span></span><span class="tap">${{isOpen?COPY.hide:COPY.tap}}</span></button>`;
}}

function toneCard(item,index){{
  const isOpen=revealed.has(index);
  const tones=item.items.map((tone,toneIndex)=>`<span class="tone-item"><span class="tone-num">${{toneIndex+1}}</span><span class="tone-word">${{tone.word}}</span><span class="tone-reading">${{tone.reading}}</span></span>`).join("");
  return `<button class="practice-card ${{isOpen?"revealed":""}}" type="button" data-index="${{index}}" aria-expanded="${{isOpen}}"><span class="card-kicker">${{COPY.tonePrompt}}</span><div class="tone-base">${{item.base}}</div><span class="tone-row">${{tones}}</span><span class="tap">${{isOpen?COPY.hide:COPY.tap}}</span></button>`;
}}

function render(){{
  cards.innerHTML=batch.map((item,index)=>mode==="tones"?toneCard(item,index):blendCard(item,index)).join("");
  const allOpen=batch.length>0&&revealed.size===batch.length;
  revealButton.textContent=allOpen?COPY.hideAll:COPY.revealAll;
  modeHelp.textContent=COPY.modeHelp[mode];
  countSelect.disabled=mode==="tones";
}}

document.getElementById("mode-buttons").addEventListener("click",event=>{{
  const button=event.target.closest("button[data-mode]");
  if(!button)return;
  mode=button.dataset.mode;
  document.querySelectorAll("#mode-buttons button").forEach(item=>item.classList.toggle("on",item===button));
  makeBatch();
}});
countSelect.addEventListener("change",()=>{{count=Number(countSelect.value);makeBatch();}});
document.getElementById("new-set").addEventListener("click",makeBatch);
cards.addEventListener("click",event=>{{
  const card=event.target.closest(".practice-card");
  if(!card)return;
  const index=Number(card.dataset.index);
  revealed.has(index)?revealed.delete(index):revealed.add(index);
  render();
}});
revealButton.addEventListener("click",()=>{{
  if(revealed.size===batch.length)revealed.clear();
  else revealed=new Set(batch.map((_,index)=>index));
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
    grid_marker = '<section class="wrap grid">'
    if grid_marker in updated:
        updated = updated.replace(grid_marker, grid_marker + card, 1)
    else:
        marker = "</section></main>"
        if marker not in updated:
            raise RuntimeError(f"{index} is missing its main tools section")
        updated = updated.replace(marker, card + marker, 1)
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
        print(f"zhuyin blending cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
