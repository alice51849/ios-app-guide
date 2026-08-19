#!/usr/bin/env python3
"""Generate bilingual, private Zhuyin mini-readers for connected-text practice."""

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
from zhuyin_sentence_reading_cards import phrase  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-decodable-mini-reader"
CONTENT_DATE = "2026-07-14"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/"
    "juyin/html_ch/index.html"
)
MOE_FORMS = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=0"
MOE_CURRICULUM = "https://cirn.k12ea.gov.tw/TWELVE/List.aspx?fid=11010"

STORIES = [
    {
        "id": "bird-water",
        "titles": {"en": "The Bird Finds Water", "zh-Hant": "小鳥找水"},
        "pages": [
            {
                "phrases": [
                    phrase("清晨", ("ㄑㄧㄥ", "ㄔㄣˊ"), "，"),
                    phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ")),
                    phrase("飛出", ("ㄈㄟ", "ㄔㄨ")),
                    phrase("樹林", ("ㄕㄨˋ", "ㄌㄧㄣˊ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("太陽", ("ㄊㄞˋ", "ㄧㄤˊ")),
                    phrase("升高", ("ㄕㄥ", "ㄍㄠ"), "，"),
                    phrase("天氣", ("ㄊㄧㄢ", "ㄑㄧˋ")),
                    phrase("變熱", ("ㄅㄧㄢˋ", "ㄖㄜˋ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ")),
                    phrase("飛到", ("ㄈㄟ", "ㄉㄠˋ")),
                    phrase("小河邊", ("ㄒㄧㄠˇ", "ㄏㄜˊ", "ㄅㄧㄢ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("牠", ("ㄊㄚ",)),
                    phrase("低頭", ("ㄉㄧ", "ㄊㄡˊ")),
                    phrase("喝", ("ㄏㄜ",)),
                    phrase("幾口水", ("ㄐㄧˇ", "ㄎㄡˇ", "ㄕㄨㄟˇ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("青蛙", ("ㄑㄧㄥ", "ㄨㄚ")),
                    phrase("跳上", ("ㄊㄧㄠˋ", "ㄕㄤˋ")),
                    phrase("大石頭", ("ㄉㄚˋ", "ㄕˊ", "˙ㄊㄡ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("小鳥", ("ㄒㄧㄠˇ", "ㄋㄧㄠˇ"), "、"),
                    phrase("青蛙", ("ㄑㄧㄥ", "ㄨㄚ")),
                    phrase("一起", ("ㄧ", "ㄑㄧˇ")),
                    phrase("唱歌", ("ㄔㄤˋ", "ㄍㄜ"), "。"),
                ]
            },
        ],
    },
    {
        "id": "rainbow",
        "titles": {"en": "Rainbow After Rain", "zh-Hant": "雨後彩虹"},
        "pages": [
            {
                "phrases": [
                    phrase("午後", ("ㄨˇ", "ㄏㄡˋ"), "，"),
                    phrase("天空", ("ㄊㄧㄢ", "ㄎㄨㄥ")),
                    phrase("飄來", ("ㄆㄧㄠ", "ㄌㄞˊ")),
                    phrase("烏雲", ("ㄨ", "ㄩㄣˊ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("大雨", ("ㄉㄚˋ", "ㄩˇ")),
                    phrase("落在", ("ㄌㄨㄛˋ", "ㄗㄞˋ")),
                    phrase("紅屋頂上", ("ㄏㄨㄥˊ", "ㄨ", "ㄉㄧㄥˇ", "ㄕㄤˋ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("小貓", ("ㄒㄧㄠˇ", "ㄇㄠ")),
                    phrase("躲進", ("ㄉㄨㄛˇ", "ㄐㄧㄣˋ")),
                    phrase("溫暖小屋", ("ㄨㄣ", "ㄋㄨㄢˇ", "ㄒㄧㄠˇ", "ㄨ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("窗外", ("ㄔㄨㄤ", "ㄨㄞˋ")),
                    phrase("雨聲", ("ㄩˇ", "ㄕㄥ")),
                    phrase("越來越小", ("ㄩㄝˋ", "ㄌㄞˊ", "ㄩㄝˋ", "ㄒㄧㄠˇ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("雨停", ("ㄩˇ", "ㄊㄧㄥˊ")),
                    phrase("以後", ("ㄧˇ", "ㄏㄡˋ"), "，"),
                    phrase("太陽", ("ㄊㄞˋ", "ㄧㄤˊ")),
                    phrase("照亮", ("ㄓㄠˋ", "ㄌㄧㄤˋ")),
                    phrase("草地", ("ㄘㄠˇ", "ㄉㄧˋ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("小貓", ("ㄒㄧㄠˇ", "ㄇㄠ")),
                    phrase("抬頭", ("ㄊㄞˊ", "ㄊㄡˊ"), "，"),
                    phrase("看見", ("ㄎㄢˋ", "ㄐㄧㄢˋ")),
                    phrase("彩虹", ("ㄘㄞˇ", "ㄏㄨㄥˊ"), "。"),
                ]
            },
        ],
    },
    {
        "id": "paper-boat",
        "titles": {"en": "The Paper Boat Travels", "zh-Hant": "紙船旅行"},
        "pages": [
            {
                "phrases": [
                    phrase("我把", ("ㄨㄛˇ", "ㄅㄚˇ")),
                    phrase("白紙", ("ㄅㄞˊ", "ㄓˇ")),
                    phrase("折成", ("ㄓㄜˊ", "ㄔㄥˊ")),
                    phrase("小船", ("ㄒㄧㄠˇ", "ㄔㄨㄢˊ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("小船", ("ㄒㄧㄠˇ", "ㄔㄨㄢˊ")),
                    phrase("輕輕", ("ㄑㄧㄥ", "ㄑㄧㄥ")),
                    phrase("放進", ("ㄈㄤˋ", "ㄐㄧㄣˋ")),
                    phrase("水溝", ("ㄕㄨㄟˇ", "ㄍㄡ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("微風", ("ㄨㄟ", "ㄈㄥ")),
                    phrase("吹來", ("ㄔㄨㄟ", "ㄌㄞˊ"), "，"),
                    phrase("小船", ("ㄒㄧㄠˇ", "ㄔㄨㄢˊ")),
                    phrase("向前走", ("ㄒㄧㄤˋ", "ㄑㄧㄢˊ", "ㄗㄡˇ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("小船", ("ㄒㄧㄠˇ", "ㄔㄨㄢˊ")),
                    phrase("經過", ("ㄐㄧㄥ", "ㄍㄨㄛˋ")),
                    phrase("綠色小橋", ("ㄌㄩˋ", "ㄙㄜˋ", "ㄒㄧㄠˇ", "ㄑㄧㄠˊ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("樹葉", ("ㄕㄨˋ", "ㄧㄝˋ")),
                    phrase("落下", ("ㄌㄨㄛˋ", "ㄒㄧㄚˋ"), "，"),
                    phrase("陪", ("ㄆㄟˊ",)),
                    phrase("小船", ("ㄒㄧㄠˇ", "ㄔㄨㄢˊ")),
                    phrase("轉彎", ("ㄓㄨㄢˇ", "ㄨㄢ"), "。"),
                ]
            },
            {
                "phrases": [
                    phrase("我在", ("ㄨㄛˇ", "ㄗㄞˋ")),
                    phrase("橋邊", ("ㄑㄧㄠˊ", "ㄅㄧㄢ"), "，"),
                    phrase("向", ("ㄒㄧㄤˋ",)),
                    phrase("小船", ("ㄒㄧㄠˇ", "ㄔㄨㄢˊ")),
                    phrase("揮手", ("ㄏㄨㄟ", "ㄕㄡˇ"), "。"),
                ]
            },
        ],
    },
]


def validate_stories() -> None:
    reading_pattern = re.compile(r"^[\u3105-\u3129\u02ca\u02c7\u02cb\u02d9]+$")
    if len(STORIES) != 3:
        raise ValueError("mini-reader must contain exactly three stories")
    ids = set()
    for story in STORIES:
        if story["id"] in ids:
            raise ValueError(f"duplicate story id: {story['id']}")
        ids.add(story["id"])
        if set(story["titles"]) != {"en", "zh-Hant"}:
            raise ValueError(f"story titles are incomplete: {story['id']}")
        if len(story["pages"]) != 6:
            raise ValueError(f"{story['id']} must contain exactly six pages")
        for page in story["pages"]:
            if not page["phrases"]:
                raise ValueError(f"{story['id']} contains an empty page")
            for item in page["phrases"]:
                if item["after"] not in {"", "，", "。", "、"}:
                    raise ValueError(f"unsupported punctuation: {item['after']!r}")
                for token in item["tokens"]:
                    if len(token["char"]) != 1:
                        raise ValueError(f"invalid character token: {token!r}")
                    if not reading_pattern.fullmatch(token["reading"]):
                        raise ValueError(f"invalid Zhuyin reading: {token['reading']!r}")
                    if "ˉ" in token["reading"]:
                        raise ValueError("first-tone marks must be omitted")


validate_stories()

COPY = {
    "en": {
        "title": "Free Printable Zhuyin Mini-Readers | 3 Original Stories",
        "description": (
            "Read three original six-page Zhuyin mini-readers in the browser or print "
            "them. Show all annotations, hide alternate pages, then reread without "
            "Zhuyin. No login, score, upload or saved child profile."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · original · connected text",
        "heading": "Zhuyin mini-reader generator",
        "lead": (
            "For the step after short sentences: choose one six-page story, read the "
            "connected text with full Zhuyin, then remove one layer of support at a time."
        ),
        "privacy": "No name, account, score, upload or saved child profile",
        "scope": "Original reading practice; not a test, level or diagnosis",
        "builder": "Choose a mini-reader",
        "story_label": "Story",
        "mode_label": "Reading pass",
        "mode_full": "1 · Show all Zhuyin",
        "mode_mixed": "2 · Hide alternate pages",
        "mode_none": "3 · Hide all Zhuyin",
        "next": "Next mini-reader",
        "print": "Print this reader",
        "share": "Share tool",
        "page": "Page",
        "full_status": "All Zhuyin is visible for the first reading.",
        "mixed_status": "Zhuyin is hidden on pages 2, 4 and 6 for a supported reread.",
        "none_status": "All Zhuyin is hidden for a final reread of the same story.",
        "shared": "Share sheet opened.",
        "cancelled": "Sharing was cancelled.",
        "copied": "Tool link copied.",
        "copy_failed": "Copy was unavailable. Use this link:",
        "why_title": "Keep the meaning connected",
        "why_text": (
            "A mini-reader asks the learner to carry characters, actions and meaning "
            "across six short pages. The story stays the same while only the visible "
            "Zhuyin support changes."
        ),
        "routine_title": "Three calm passes",
        "routine": [
            "Read all six pages with every Zhuyin annotation visible.",
            "Hide annotations on alternate pages and reread the same story.",
            "Hide all annotations only if the earlier pass feels comfortable.",
            "Talk about what happened; do not time, score or label the learner.",
        ],
        "original_title": "Original text, no copied worksheet",
        "original_text": (
            "All 18 sentences and three story sequences were written for this tool. "
            "There are no copied books, illustrations, audio clips or Ministry worksheets."
        ),
        "tone_title": "Dictionary tones, natural speech",
        "tone_text": (
            "Annotations use Taiwan Ministry of Education dictionary base tones. "
            "Natural connected speech can change adjacent third tones and the spoken "
            "tone of 一; those pronunciation changes are not rewritten as dictionary forms."
        ),
        "print_note": (
            "Printing shows all Zhuyin and only the selected six-page reader. Controls "
            "and promotional content are removed."
        ),
        "app_title": "Need symbol, tone or blending practice first?",
        "app_text": (
            "Lumi Bopomofo is an optional practice layer for listening, tracing, tones "
            "and syllable blending. It has a one-time unlock with no ads, "
            "subscription or account. The free mini-readers remain complete without it."
        ),
        "app_cta": "Parents: see Lumi Bopomofo on the App Store",
        "sources": "Sources and scope",
        "source_labels": [
            "Taiwan Ministry of Education: Mandarin Phonetic Symbols handbook",
            "Taiwan Ministry of Education: standard character and Zhuyin forms",
            "CIRN: Mandarin learning outcomes for the first learning stage",
        ],
        "source_note": (
            "The official references support standard symbols and first-stage outcomes "
            "including using Zhuyin material to learn reading (3-I-4) and reading text "
            "accurately at an appropriate rate (5-I-1). They did not design, test or "
            "endorse these independent stories."
        ),
        "faq": [
            (
                "Are these adapted from a published children's book?",
                "No. All three stories and every sentence are original to this free tool.",
            ),
            (
                "Does finishing a reader prove fluency or school readiness?",
                "No. A reread is practice only; there is no score, timing, level or diagnostic result.",
            ),
            (
                "Why does the middle pass hide only alternate pages?",
                "It removes support gradually while keeping half of the story fully annotated.",
            ),
            (
                "Does any reading data leave the browser?",
                "No response is entered or collected. Story and display choices reset when the page closes.",
            ),
        ],
        "index_title": "Zhuyin Mini-Reader Generator",
        "index_description": (
            "Three original six-page stories with staged Zhuyin hiding, browser reading "
            "and private printing."
        ),
    },
    "zh-Hant": {
        "title": "免費注音迷你讀本產生器｜三篇原創故事可列印",
        "description": (
            "免費閱讀或列印三篇原創六頁注音迷你讀本；先顯示全部注音，再隔頁遮住，"
            "最後重讀無注音版本。免登入、不計分、不上傳、不建立兒童檔案。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費・原創・連貫短文",
        "heading": "注音迷你讀本產生器",
        "lead": (
            "短句讀得比較順後，選一篇六頁小故事，先看完整注音讀完連貫內容，"
            "再一次減少一層提示。"
        ),
        "privacy": "不填姓名、免帳號、不計分、不上傳、不儲存兒童檔案",
        "scope": "原創閱讀練習；不是測驗、程度分級或診斷",
        "builder": "選擇一篇迷你讀本",
        "story_label": "故事",
        "mode_label": "閱讀輪次",
        "mode_full": "第一輪・顯示全部注音",
        "mode_mixed": "第二輪・隔頁遮住注音",
        "mode_none": "第三輪・遮住全部注音",
        "next": "換下一篇讀本",
        "print": "列印這篇讀本",
        "share": "分享工具",
        "page": "第",
        "full_status": "第一輪顯示全部注音。",
        "mixed_status": "第二、四、六頁已遮住注音，重讀相同故事。",
        "none_status": "全部注音已遮住，可重讀相同故事；不代表通過測驗。",
        "shared": "已開啟分享選單。",
        "cancelled": "已取消分享。",
        "copied": "已複製工具連結。",
        "copy_failed": "無法自動複製，請使用這個連結：",
        "why_title": "讓意思跨頁連起來",
        "why_text": (
            "迷你讀本讓孩子在六個短頁面之間記住角色、動作與前後意思。故事內容不變，"
            "每一輪只改變看得見的注音提示。"
        ),
        "routine_title": "三輪低壓力讀法",
        "routine": [
            "第一輪顯示每個國字的注音，依序讀完六頁。",
            "第二輪只遮住偶數頁注音，重讀完全相同的故事。",
            "前一輪讀得舒服時，才在第三輪遮住全部注音。",
            "最後聊聊故事發生什麼；不計時、不打分，也不替孩子貼標籤。",
        ],
        "original_title": "原創文字，不複製練習單",
        "original_text": (
            "三篇故事與 18 句文字全部為本站原創；沒有複製童書、插圖、音檔或教育部練習單。"
        ),
        "tone_title": "頁面標本調，朗讀用自然語音",
        "tone_text": (
            "注音依教育部辭典標示本調；自然連讀時，相鄰三聲與「一」的實際聲調可能改變，"
            "頁面不會把口語變調改寫成辭典字音。"
        ),
        "print_note": (
            "列印時只保留目前選擇的六頁讀本，並顯示全部注音；操作按鈕與宣傳內容會隱藏。"
        ),
        "app_title": "讀小故事前，還想加強符號、聲調或拼讀？",
        "app_text": (
            "Lumi 注音星球是選配的練習層，提供聽音、描寫、聲調與拼讀遊戲。"
            "一次付費一次購買解鎖，無廣告、無訂閱、免帳號；不使用 App 也能完整使用"
            "上方免費讀本。"
        ),
        "app_cta": "家長前往 App Store 查看 Lumi 注音星球",
        "sources": "資料來源與適用範圍",
        "source_labels": [
            "教育部《國語注音符號手冊》",
            "教育部常用國字標準字體筆順學習網",
            "CIRN 國語文第一學習階段學習重點",
        ],
        "source_note": (
            "官方資料只用來核對標準符號、字形，以及第一學習階段「利用注音讀物，"
            "學習閱讀」（3-I-4）與「以適切速率正確朗讀文本」（5-I-1）等目標；"
            "教育部沒有設計、測試或推薦這三篇獨立原創故事。"
        ),
        "faq": [
            (
                "這些故事改寫自已出版的童書嗎？",
                "不是。三篇故事與每一句文字都是本站為這個免費工具原創。",
            ),
            (
                "讀完就代表流暢或準備好上小學嗎？",
                "不能這樣判定。重讀只是練習，沒有分數、計時、等級或診斷結果。",
            ),
            (
                "第二輪為什麼只遮住偶數頁？",
                "它逐步減少提示，同時保留一半頁面的完整注音。",
            ),
            (
                "閱讀資料會離開瀏覽器嗎？",
                "不會輸入或收集閱讀反應；故事與顯示選擇在關閉頁面後即重設。",
            ),
        ],
        "index_title": "注音迷你讀本產生器",
        "index_description": "三篇原創六頁小故事，可分三輪遮住注音、直接閱讀與私密列印。",
    },
}

STYLE = r"""
:root{--bg:#f2eee6;--paper:#fffdf8;--ink:#20221f;--muted:#66675f;--line:#ddd5c8;--leaf:#315f50;--leaf2:#4e7f6b;--soft:#edf4f0;--shadow:0 18px 50px rgba(50,48,39,.10)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:radial-gradient(circle at 10% 0,#fff 0,var(--bg) 48%,#e7e0d5 100%);color:var(--ink);line-height:1.65}
a{color:#285747}.wrap{width:min(1120px,100% - 30px);margin:auto}.top{position:sticky;top:0;z-index:8;background:rgba(255,253,248,.92);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}
.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:18px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.nav-links{display:flex;gap:16px}.nav-links a{color:var(--muted);font-size:14px}
.hero{padding:58px 0 26px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--leaf);white-space:nowrap}
h1,h2,.reader-title{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6.5vw,66px);line-height:1.04;letter-spacing:-.035em;margin:.28em 0 .24em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.3vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.trust{display:flex;gap:9px;flex-wrap:wrap;margin-top:22px}.badge.scope{color:#695d49}
.workspace{background:rgba(255,253,248,.98);border:1px solid var(--line);border-radius:30px;padding:clamp(18px,4vw,34px);box-shadow:var(--shadow);margin:20px auto 34px}.workspace h2,.content-card h2,.cta-card h2{font-size:clamp(24px,4vw,34px);line-height:1.15;margin:0;white-space:nowrap;overflow-x:auto}
.controls{display:grid;gap:16px;margin:24px 0 16px;padding:18px;border:1px solid #e6ded1;border-radius:22px;background:#f8f4ec}.control-label{display:block;color:var(--muted);font-size:13px;font-weight:850;margin-bottom:8px;white-space:nowrap}.seg{display:flex;flex-wrap:wrap;gap:7px}.seg button,.button{font:inherit;font-weight:800;border-radius:999px;white-space:nowrap;cursor:pointer}.seg button{border:1px solid var(--line);background:#fff;color:var(--muted);padding:9px 13px}.seg button.on{background:linear-gradient(135deg,var(--leaf),var(--leaf2));border-color:transparent;color:#fff;box-shadow:0 8px 18px rgba(49,95,80,.18)}
.actions{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0}.button{border:0;background:linear-gradient(135deg,var(--leaf),var(--leaf2));color:#fff;padding:11px 16px;box-shadow:0 8px 20px rgba(49,95,80,.16)}.button.secondary{background:#fff;color:var(--leaf);border:1px solid var(--line);box-shadow:none}.status{color:var(--muted);font-size:14px;min-height:1.5em;white-space:nowrap;overflow-x:auto}
.reader-title{font-size:clamp(26px,4vw,38px);margin:20px 0 14px;text-align:center;white-space:nowrap;overflow-x:auto}.reader{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.reader-page{background:linear-gradient(155deg,#fff,#fbf8f1);border:1px solid #dcd3c5;border-radius:24px;padding:17px 18px;box-shadow:0 8px 24px rgba(52,48,38,.06);break-inside:avoid;overflow:hidden}.page-label{display:block;color:var(--muted);font-size:12px;font-weight:850;white-space:nowrap}.sentence{display:flex;align-items:flex-end;gap:clamp(8px,1.4vw,17px);font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(25px,4vw,40px);font-weight:850;line-height:1.2;margin:24px 0 5px;padding:18px 0 5px;white-space:nowrap;overflow-x:auto}.phrase{display:inline-flex;align-items:flex-end;white-space:nowrap}.sentence ruby{ruby-position:over;ruby-align:center;margin:0 .035em}.sentence rt{font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC",sans-serif;font-size:.36em;font-weight:800;color:var(--leaf)}.sentence.reading-hidden rt{visibility:hidden}
.content-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin:30px auto}.content-card{grid-column:span 6;background:rgba(255,253,248,.94);border:1px solid var(--line);border-radius:26px;padding:25px}.content-card.full{grid-column:span 12}.content-card p,.content-card li{color:var(--muted)}.content-card p{white-space:nowrap;overflow-x:auto}.content-card li{margin:.5em 0}.cta-card{background:linear-gradient(135deg,#254d41,#477562);color:#fff;border-radius:30px;padding:clamp(24px,5vw,40px);margin:32px auto}.cta-card p{color:#e8f0ec;white-space:nowrap;overflow-x:auto}.cta-card .button{display:inline-flex;background:#fff;color:#244c40;text-decoration:none;box-shadow:none}.sources{margin:30px auto 54px;color:var(--muted);font-size:14px}.sources h2,.sources p,.sources li{white-space:nowrap;overflow-x:auto}.faq-list{display:grid;gap:10px}.faq-list details{border:1px solid var(--line);border-radius:18px;background:#fff;padding:13px 16px}.faq-list summary{font-weight:850;cursor:pointer;white-space:nowrap;overflow-x:auto}.faq-list p{margin:.6em 0 0}
@media(max-width:760px){.hero{padding-top:38px}.reader{grid-template-columns:1fr}.content-card{grid-column:span 12}.nav{align-items:flex-start;padding:13px 0}}
@media print{.top,.hero,.controls,.actions,.status,.content-grid,.cta-card,.sources,.workspace>h2{display:none!important}body{background:#fff}.wrap{width:100%}.workspace{border:0;box-shadow:none;padding:0;margin:0}.reader-title{font-size:22pt;margin:0 0 6mm}.reader{grid-template-columns:1fr;gap:5mm}.reader-page{border:1pt solid #777;border-radius:4mm;box-shadow:none;padding:7mm;page-break-inside:avoid}.sentence{font-size:23pt;overflow:visible;margin:4mm 0}.sentence rt{visibility:visible!important}@page{size:A4 portrait;margin:11mm}}
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def sentence_markup(page: dict[str, object], *, hidden: bool = False) -> str:
    phrases = []
    for item in page["phrases"]:
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
    hidden_class = " reading-hidden" if hidden else ""
    return f'<p class="sentence{hidden_class}">{"".join(phrases)}</p>'


def static_reader(locale: str, copy: dict[str, object]) -> str:
    story = STORIES[0]
    pages = "".join(
        (
            '<article class="reader-page">'
            f'<span class="page-label">{html.escape(copy["page"])} '
            f'{index + 1}</span>{sentence_markup(page)}</article>'
        )
        for index, page in enumerate(story["pages"])
    )
    return (
        f'<h3 class="reader-title">{html.escape(story["titles"][locale])}</h3>'
        f'<div class="reader" id="reader">{pages}</div>'
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
    app_campaign = appstore_url(
        "lumibopomofo",
        f"iag_zhuyin_mini_reader_{locale.lower()}",
    )
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
        "learningResourceType": "Parent-guided printable mini-reader",
        "educationalUse": "Reading practice",
        "educationalLevel": "Beginner",
        "teaches": [
            "Reading connected Traditional Chinese text with Zhuyin",
            "Carrying meaning across six short pages",
            "Rereading the same story with gradually reduced Zhuyin support",
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
    story_buttons = "".join(
        (
            f'<button type="button" class="{"on" if index == 0 else ""}" '
            f'data-story="{index}">{html.escape(story["titles"][locale])}</button>'
        )
        for index, story in enumerate(STORIES)
    )
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
    client_copy = {
        "page": t["page"],
        "status": {
            "full": t["full_status"],
            "mixed": t["mixed_status"],
            "none": t["none_status"],
        },
        "shareTitle": t["heading"],
        "shareText": t["lead"],
        "shared": t["shared"],
        "cancelled": t["cancelled"],
        "copied": t["copied"],
        "copyFailed": t["copy_failed"],
    }
    data_json = json.dumps(STORIES, ensure_ascii=False).replace("</", "<\\/")
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
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="trust"><span class="badge">{html.escape(t["privacy"])}</span><span class="badge scope">{html.escape(t["scope"])}</span></div></section>
<section class="workspace wrap" id="generator">
<h2>{html.escape(t["builder"])}</h2>
<div class="controls">
<div><span class="control-label">{html.escape(t["story_label"])}</span><div class="seg" id="story-buttons" role="group" aria-label="{html.escape(t["story_label"])}">{story_buttons}</div></div>
<div><span class="control-label">{html.escape(t["mode_label"])}</span><div class="seg" id="mode-buttons" role="group" aria-label="{html.escape(t["mode_label"])}"><button type="button" class="on" data-mode="full">{html.escape(t["mode_full"])}</button><button type="button" data-mode="mixed">{html.escape(t["mode_mixed"])}</button><button type="button" data-mode="none">{html.escape(t["mode_none"])}</button></div></div>
</div>
<div class="actions"><button class="button" id="next-reader" type="button">{html.escape(t["next"])}</button><button class="button secondary" id="print-reader" type="button">{html.escape(t["print"])}</button><button class="button secondary" id="share-tool" type="button">{html.escape(t["share"])}</button></div>
<p class="status" id="status" aria-live="polite">{html.escape(t["full_status"])}</p>
<div id="reader-shell">{static_reader(locale, t)}</div>
<p class="status">{html.escape(t["print_note"])}</p>
</section>
<section class="content-grid wrap"><article class="content-card"><h2>{html.escape(t["why_title"])}</h2><p>{html.escape(t["why_text"])}</p></article><article class="content-card"><h2>{html.escape(t["routine_title"])}</h2><ol>{routine}</ol></article><article class="content-card full"><h2>{html.escape(t["original_title"])}</h2><p>{html.escape(t["original_text"])}</p></article><article class="content-card full"><h2>{html.escape(t["tone_title"])}</h2><p>{html.escape(t["tone_text"])}</p></article></section>
<section class="cta-card wrap"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_campaign, quote=True)}">{html.escape(t["app_cta"])}</a></section>
<section class="sources wrap"><h2>{html.escape(t["sources"])}</h2><ul>{sources}</ul><p>{html.escape(t["source_note"])}</p><div class="faq-list">{faq}</div></section>
</main>
<script>
const STORIES={data_json};
const COPY={copy_json};
const LOCALE={json.dumps(locale)};
let storyIndex=0;
let mode="full";
const shell=document.getElementById("reader-shell");
const status=document.getElementById("status");

function sentenceHTML(page,index){{
  const hidden=mode==="none"||(mode==="mixed"&&index%2===1);
  const phrases=page.phrases.map(phrase=>{{
    const tokens=phrase.tokens.map(token=>`<ruby>${{token.char}}<rt>${{token.reading}}</rt></ruby>`).join("");
    return `<span class="phrase">${{tokens}}${{phrase.after||""}}</span>`;
  }}).join("");
  return `<article class="reader-page"><span class="page-label">${{COPY.page}} ${{index+1}}</span><p class="sentence ${{hidden?"reading-hidden":""}}">${{phrases}}</p></article>`;
}}

function render(){{
  const story=STORIES[storyIndex];
  shell.innerHTML=`<h3 class="reader-title">${{story.titles[LOCALE]}}</h3><div class="reader" id="reader">${{story.pages.map(sentenceHTML).join("")}}</div>`;
  status.textContent=COPY.status[mode];
  document.querySelectorAll("#story-buttons button").forEach((button,index)=>button.classList.toggle("on",index===storyIndex));
  document.querySelectorAll("#mode-buttons button").forEach(button=>button.classList.toggle("on",button.dataset.mode===mode));
}}

document.getElementById("story-buttons").addEventListener("click",event=>{{
  const button=event.target.closest("button[data-story]");
  if(!button)return;
  storyIndex=Number(button.dataset.story);
  mode="full";
  render();
}});
document.getElementById("mode-buttons").addEventListener("click",event=>{{
  const button=event.target.closest("button[data-mode]");
  if(!button)return;
  mode=button.dataset.mode;
  render();
}});
document.getElementById("next-reader").addEventListener("click",()=>{{
  storyIndex=(storyIndex+1)%STORIES.length;
  mode="full";
  render();
}});
document.getElementById("print-reader").addEventListener("click",()=>window.print());
document.getElementById("share-tool").addEventListener("click",async()=>{{
  const payload={{title:COPY.shareTitle,text:COPY.shareText,url:window.location.href}};
  if(navigator.share){{
    try{{await navigator.share(payload);status.textContent=COPY.shared;return;}}
    catch(error){{if(error&&error.name==="AbortError"){{status.textContent=COPY.cancelled;return;}}}}
  }}
  try{{await navigator.clipboard.writeText(window.location.href);status.textContent=COPY.copied;}}
  catch(error){{status.textContent=`${{COPY.copyFailed}} ${{window.location.href}}`;}}
}});
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
        r'zhuyin-short-sentence-reading-cards\.html">.*?</article>)',
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
        print(f"zhuyin mini-reader -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
