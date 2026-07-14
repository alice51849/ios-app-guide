#!/usr/bin/env python3
"""Generate bilingual Zhuyin story-sequencing and comprehension cards."""

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
from zhuyin_mini_reader import STORIES, sentence_markup  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "zhuyin-story-sequencing-cards"
CONTENT_DATE = "2026-07-14"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/"
    "juyin/html_ch/index.html"
)
MOE_CURRICULUM = "https://cirn.k12ea.gov.tw/TWELVE/List.aspx?fid=11010"
APP_URL = appstore_url("lumibopomofo")
STATIC_ORDER = (2, 0, 4, 1, 5, 3)

PROMPTS = {
    "bird-water": {
        "en": (
            "Why did the bird fly to the river?",
            "What happened after the frog jumped onto the rock?",
        ),
        "zh-Hant": (
            "小鳥為什麼飛到小河邊？",
            "青蛙跳上石頭以後，發生了什麼事？",
        ),
    },
    "rainbow": {
        "en": (
            "Where did the cat stay while the rain was heavy?",
            "What changed before the cat saw the rainbow?",
        ),
        "zh-Hant": (
            "大雨下得很大時，小貓躲在哪裡？",
            "小貓看見彩虹以前，天氣發生了什麼變化？",
        ),
    },
    "paper-boat": {
        "en": (
            "What made the paper boat move forward?",
            "Which events happened before the boat turned?",
        ),
        "zh-Hant": (
            "是什麼讓紙船向前走？",
            "紙船轉彎以前，先發生了哪些事？",
        ),
    },
}


def validate_content() -> None:
    if len(STORIES) != 3:
        raise ValueError("sequencing cards require exactly three mini-reader stories")
    if set(PROMPTS) != {story["id"] for story in STORIES}:
        raise ValueError("every story must have comprehension prompts")
    if sorted(STATIC_ORDER) != list(range(6)):
        raise ValueError("static card order must contain every event exactly once")
    for story in STORIES:
        if len(story["pages"]) != 6:
            raise ValueError(f"{story['id']} must contain exactly six events")
        if set(PROMPTS[story["id"]]) != {"en", "zh-Hant"}:
            raise ValueError(f"{story['id']} prompts are incomplete")
        if any(len(PROMPTS[story["id"]][locale]) != 2 for locale in PROMPTS[story["id"]]):
            raise ValueError(f"{story['id']} must have two prompts per locale")


validate_content()

COPY = {
    "en": {
        "title": "Free Zhuyin Story Sequencing Cards | Read, Order and Retell",
        "description": (
            "Shuffle and reorder six fully annotated events from three original Zhuyin "
            "stories. Reveal the story order, discuss two prompts and print privately. "
            "No login, score or child data."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · original · story structure",
        "heading": "Zhuyin story sequencing cards",
        "lead": (
            "After reading a short story, mix its six event cards and rebuild what "
            "happened first, next and last without turning comprehension into a test."
        ),
        "privacy": "No name, response form, score, upload or saved child profile",
        "scope": "Reading and retelling practice; not an assessment or diagnosis",
        "builder": "Choose a story and rebuild its order",
        "story_label": "Story",
        "shuffle": "Shuffle the six cards",
        "reveal": "Show the original order",
        "print": "Print current cards",
        "share": "Share tool",
        "card": "Current position",
        "earlier": "Move earlier",
        "later": "Move later",
        "discussion": "Talk about the story",
        "shuffled_status": "The six events are mixed. Move one card at a time.",
        "moved_status": "Card moved. Keep discussing what happened before and after.",
        "revealed_status": (
            "The original order is visible for discussion; this is not a score or result."
        ),
        "shared": "Share sheet opened.",
        "cancelled": "Sharing was cancelled.",
        "copied": "Tool link copied.",
        "copy_failed": "Copy was unavailable. Use this link:",
        "why_title": "Move from decoding to meaning",
        "why_text": (
            "Reordering familiar events shifts attention from sounding out one line to "
            "remembering characters, actions and cause-and-effect across the whole story."
        ),
        "routine_title": "A calm four-step routine",
        "routine": [
            "Read the selected story once with all Zhuyin visible.",
            "Shuffle the six cards and ask what might happen first.",
            "Move cards together while talking about before, after and because.",
            "Reveal the original order, retell it and stop without timing or scoring.",
        ],
        "reuse_title": "Same original stories, a different reading task",
        "reuse_text": (
            "The cards reuse the three original mini-readers so the words stay familiar. "
            "This tool adds sequencing and retelling; it does not replace the reader or "
            "claim to measure comprehension."
        ),
        "print_note": (
            "Printing keeps the current six-card order and discussion prompts. Controls "
            "and promotional content are removed."
        ),
        "app_title": "Need symbol, tone or blending practice before story work?",
        "app_text": (
            "Lumi Bopomofo is an optional practice layer for listening, tracing, tones "
            "and syllable blending. It has a one-time lifetime unlock with no ads, "
            "subscription or account. These free sequencing cards remain complete without it."
        ),
        "app_cta": "Parents: see Lumi Bopomofo on the App Store",
        "sources": "Sources and scope",
        "source_labels": [
            "Taiwan Ministry of Education: Mandarin Phonetic Symbols handbook",
            "CIRN: Mandarin learning outcomes for the first learning stage",
        ],
        "source_note": (
            "The official first-stage outcomes include reading stage-appropriate texts "
            "(5-I-3), understanding important information and viewpoints (5-I-4), and "
            "using images or story structure to support understanding and retelling "
            "(5-I-6). They support the scope only; the Ministry did not create, test or "
            "endorse this independent tool."
        ),
        "faq": [
            (
                "Are the stories copied from a book or worksheet?",
                "No. The three story sequences were written for the free mini-reader and are reused here as original sequencing cards.",
            ),
            (
                "Does the revealed order grade the learner?",
                "No. It is a discussion reference only, with no score, timer, level, pass or diagnostic result.",
            ),
            (
                "Why keep all Zhuyin visible?",
                "The task is to follow meaning and event order, so decoding support stays stable.",
            ),
            (
                "Is any card order or response saved?",
                "No. Nothing is entered or collected, and the card order resets when the page closes.",
            ),
        ],
        "index_title": "Zhuyin Story Sequencing Cards",
        "index_description": (
            "Reorder six events from three original annotated stories, reveal the "
            "sequence, discuss and print with no score or login."
        ),
    },
    "zh-Hant": {
        "title": "免費注音故事排序卡｜閱讀、排序與重述練習",
        "description": (
            "把三篇原創注音故事各六張事件卡打散、重新排序，再顯示原始順序一起討論，"
            "也可私密列印。免登入、不計分、不蒐集兒童資料。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費・原創・故事結構",
        "heading": "注音故事排序與理解卡",
        "lead": (
            "讀完短篇故事後，把六張事件卡打散，再一起排出先發生、接著發生與最後發生的事，"
            "不把閱讀理解變成考試。"
        ),
        "privacy": "不填姓名、無作答表單、不計分、不上傳、不儲存兒童檔案",
        "scope": "閱讀與重述練習；不是評量、分級或診斷",
        "builder": "選一篇故事，重新排出事件順序",
        "story_label": "故事",
        "shuffle": "打散六張卡",
        "reveal": "顯示原始順序",
        "print": "列印目前卡片",
        "share": "分享工具",
        "card": "目前位置",
        "earlier": "往前移",
        "later": "往後移",
        "discussion": "一起聊故事",
        "shuffled_status": "六個事件已打散；一次移動一張卡。",
        "moved_status": "卡片已移動；繼續聊聊前後發生了什麼。",
        "revealed_status": "已顯示原始順序供討論；這不是分數或測驗結果。",
        "shared": "已開啟分享選單。",
        "cancelled": "已取消分享。",
        "copied": "已複製工具連結。",
        "copy_failed": "無法自動複製，請使用這個連結：",
        "why_title": "從讀出聲音走到理解意思",
        "why_text": (
            "重新排列熟悉事件，能把注意力從讀出單一行文字，轉到記住整篇故事的角色、"
            "動作與前因後果。"
        ),
        "routine_title": "四步低壓力練習",
        "routine": [
            "先保留全部注音，讀一次選擇的故事。",
            "打散六張卡，先聊哪一件事可能最早發生。",
            "一起移動卡片，聊聊之前、之後與為什麼。",
            "顯示原始順序後重述故事，不計時也不打分。",
        ],
        "reuse_title": "相同原創故事，不同閱讀任務",
        "reuse_text": (
            "卡片沿用三篇原創迷你讀本，讓文字保持熟悉；這裡增加的是排序與重述，"
            "不取代讀本，也不宣稱能測量閱讀理解。"
        ),
        "print_note": "列印時保留目前六張卡的順序與討論題；操作按鈕與宣傳內容會隱藏。",
        "app_title": "進入故事練習前，還想加強符號、聲調或拼讀？",
        "app_text": (
            "Lumi 注音星球是選配的練習層，提供聽音、描寫、聲調與拼讀遊戲。"
            "一次付費永久解鎖，無廣告、無訂閱、免帳號；不使用 App 也能完整使用"
            "上方免費排序卡。"
        ),
        "app_cta": "家長前往 App Store 查看 Lumi 注音星球",
        "sources": "資料來源與適用範圍",
        "source_labels": [
            "教育部《國語注音符號手冊》",
            "CIRN 國語文第一學習階段學習重點",
        ],
        "source_note": (
            "官方第一學習階段目標包含「讀懂與學習階段相符的文本」（5-I-3）、"
            "「了解文本中的重要訊息與觀點」（5-I-4），以及利用圖像、故事結構等策略"
            "協助理解與重述（5-I-6）。官方資料只支持工具範圍；教育部沒有設計、測試"
            "或推薦這個獨立工具。"
        ),
        "faq": [
            (
                "故事是從童書或練習單複製的嗎？",
                "不是。三篇故事原本就是本站為免費迷你讀本創作，這裡只把原創事件做成排序卡。",
            ),
            (
                "顯示原始順序會替孩子評分嗎？",
                "不會。它只供一起討論，沒有分數、計時、等級、通過或診斷結果。",
            ),
            (
                "為什麼卡片一直保留完整注音？",
                "這次任務聚焦理解意思與事件順序，因此讓拼讀提示保持穩定。",
            ),
            (
                "卡片順序或回答會被儲存嗎？",
                "不會輸入或收集任何回答，關閉頁面後卡片順序就會重設。",
            ),
        ],
        "index_title": "注音故事排序與理解卡",
        "index_description": "打散三篇原創注音故事的六個事件，重新排序、討論、顯示原始順序並列印。",
    },
}

STYLE = r"""
:root{--bg:#f5efe8;--paper:#fffdfa;--ink:#25231f;--muted:#6b665f;--line:#ddd3c6;--berry:#7b3f58;--berry2:#a45f77;--soft:#f7eaf0;--shadow:0 18px 48px rgba(62,44,49,.10)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 50%,#e9ded4 100%);color:var(--ink);line-height:1.65}
a{color:#71364f}.wrap{width:min(1120px,100% - 30px);margin:auto}.top{position:sticky;top:0;z-index:8;background:rgba(255,253,250,.93);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}
.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:18px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.nav-links{display:flex;gap:16px}.nav-links a{color:var(--muted);font-size:14px}
.hero{padding:58px 0 26px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--berry);white-space:nowrap}
h1,h2,.board-title{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6.5vw,64px);line-height:1.04;letter-spacing:-.035em;margin:.28em 0 .24em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.3vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.trust{display:flex;gap:9px;flex-wrap:wrap;margin-top:22px}.badge.scope{color:#725f4e}
.workspace{background:rgba(255,253,250,.98);border:1px solid var(--line);border-radius:30px;padding:clamp(18px,4vw,34px);box-shadow:var(--shadow);margin:20px auto 34px}.workspace h2,.content-card h2,.cta-card h2{font-size:clamp(24px,4vw,34px);line-height:1.15;margin:0;white-space:nowrap;overflow-x:auto}
.controls{display:grid;gap:14px;margin:24px 0 16px;padding:18px;border:1px solid #e7ddd2;border-radius:22px;background:#faf5ef}.control-label{display:block;color:var(--muted);font-size:13px;font-weight:850;margin-bottom:8px;white-space:nowrap}.seg,.actions{display:flex;flex-wrap:wrap;gap:8px}.seg button,.button,.move button{font:inherit;font-weight:820;border-radius:999px;white-space:nowrap;cursor:pointer}.seg button{border:1px solid var(--line);background:#fff;color:var(--muted);padding:9px 13px}.seg button.on{background:linear-gradient(135deg,var(--berry),var(--berry2));border-color:transparent;color:#fff;box-shadow:0 8px 18px rgba(123,63,88,.18)}
.actions{margin:14px 0}.button{border:0;background:linear-gradient(135deg,var(--berry),var(--berry2));color:#fff;padding:11px 16px;box-shadow:0 8px 20px rgba(123,63,88,.16)}.button.secondary{background:#fff;color:var(--berry);border:1px solid var(--line);box-shadow:none}.status{color:var(--muted);font-size:14px;min-height:1.5em;white-space:nowrap;overflow-x:auto}
.board-title{font-size:clamp(26px,4vw,38px);margin:20px 0 14px;text-align:center;white-space:nowrap;overflow-x:auto}.board{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.event-card{background:linear-gradient(155deg,#fff,#fcf8f4);border:1px solid #ddd1c4;border-radius:24px;padding:16px 18px;box-shadow:0 8px 24px rgba(59,44,47,.06);break-inside:avoid;overflow:hidden}.slot{display:block;color:var(--berry);font-size:12px;font-weight:900;white-space:nowrap}.sentence{display:flex;align-items:flex-end;gap:clamp(8px,1.4vw,17px);font-family:ui-serif,Georgia,"Noto Serif TC",serif;font-size:clamp(24px,3.7vw,37px);font-weight:850;line-height:1.2;margin:23px 0 12px;padding:17px 0 5px;white-space:nowrap;overflow-x:auto}.phrase{display:inline-flex;align-items:flex-end;white-space:nowrap}.sentence ruby{ruby-position:over;ruby-align:center;margin:0 .035em}.sentence rt{font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC",sans-serif;font-size:.36em;font-weight:800;color:var(--berry)}
.move{display:flex;gap:7px}.move button{border:1px solid var(--line);background:#fff;color:var(--berry);padding:7px 11px}.move button:disabled{opacity:.35;cursor:not-allowed}.prompts{margin:18px 0 0;padding:18px 21px;border:1px solid var(--line);border-radius:20px;background:var(--soft)}.prompts h3,.prompts li{white-space:nowrap;overflow-x:auto}.prompts h3{margin:0}.prompts li{margin:.45em 0;color:var(--muted)}
.content-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px;margin:30px auto}.content-card{grid-column:span 6;background:rgba(255,253,250,.94);border:1px solid var(--line);border-radius:26px;padding:25px}.content-card.full{grid-column:span 12}.content-card p,.content-card li{color:var(--muted)}.content-card p{white-space:nowrap;overflow-x:auto}.content-card li{margin:.5em 0}.cta-card{background:linear-gradient(135deg,#613045,#8d5068);color:#fff;border-radius:30px;padding:clamp(24px,5vw,40px);margin:32px auto}.cta-card p{color:#f6eaf0;white-space:nowrap;overflow-x:auto}.cta-card .button{display:inline-flex;background:#fff;color:#69334b;text-decoration:none;box-shadow:none}.sources{margin:30px auto 54px;color:var(--muted);font-size:14px}.sources h2,.sources p,.sources li{white-space:nowrap;overflow-x:auto}.faq-list{display:grid;gap:10px}.faq-list details{border:1px solid var(--line);border-radius:18px;background:#fff;padding:13px 16px}.faq-list summary{font-weight:850;cursor:pointer;white-space:nowrap;overflow-x:auto}.faq-list p{margin:.6em 0 0}
@media(max-width:760px){.hero{padding-top:38px}.board{grid-template-columns:1fr}.content-card{grid-column:span 12}.nav{align-items:flex-start;padding:13px 0}}
@media print{.top,.hero,.controls,.actions,.status,.content-grid,.cta-card,.sources,.workspace>h2,.move{display:none!important}body{background:#fff}.wrap{width:100%}.workspace{border:0;box-shadow:none;padding:0;margin:0}.board-title{font-size:22pt;margin:0 0 6mm}.board{grid-template-columns:1fr;gap:5mm}.event-card{border:1pt solid #777;border-radius:4mm;box-shadow:none;padding:6mm;page-break-inside:avoid}.sentence{font-size:21pt;overflow:visible;margin:4mm 0}.prompts{break-inside:avoid}@page{size:A4 portrait;margin:11mm}}
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def card_markup(
    page: dict[str, object],
    position: int,
    copy: dict[str, object],
) -> str:
    return (
        '<article class="event-card">'
        f'<span class="slot">{html.escape(copy["card"])} {position + 1}</span>'
        f"{sentence_markup(page)}"
        '<div class="move">'
        f'<button type="button" data-move="-1">{html.escape(copy["earlier"])}</button>'
        f'<button type="button" data-move="1">{html.escape(copy["later"])}</button>'
        "</div></article>"
    )


def prompts_markup(story: dict[str, object], locale: str, copy: dict[str, object]) -> str:
    items = "".join(
        f"<li>{html.escape(prompt)}</li>" for prompt in PROMPTS[story["id"]][locale]
    )
    return (
        f'<aside class="prompts"><h3>{html.escape(copy["discussion"])}</h3>'
        f"<ol>{items}</ol></aside>"
    )


def static_board(locale: str, copy: dict[str, object]) -> str:
    story = STORIES[0]
    cards = "".join(
        card_markup(story["pages"][original_index], position, copy)
        for position, original_index in enumerate(STATIC_ORDER)
    )
    return (
        f'<h3 class="board-title">{html.escape(story["titles"][locale])}</h3>'
        f'<div class="board" id="board">{cards}</div>'
        f'<div id="prompt-shell">{prompts_markup(story, locale, copy)}</div>'
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
    app_campaign = f"{APP_URL}?ct=iag_zhuyin_story_sequence_{locale.lower()}"
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
        "browserRequirements": (
            "JavaScript for shuffling and reordering; story cards remain readable "
            "without JavaScript"
        ),
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "learningResourceType": "Interactive story sequencing cards",
        "educationalUse": "Reading comprehension and retelling practice",
        "educationalLevel": "Beginner",
        "teaches": [
            "Ordering events from a short Traditional Chinese story",
            "Understanding important information across a connected text",
            "Using story structure to support oral retelling",
        ],
        "citation": [MOE_HANDBOOK, MOE_CURRICULUM],
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
            (MOE_HANDBOOK, MOE_CURRICULUM),
            t["source_labels"],
            strict=True,
        )
    )
    client_copy = {
        "card": t["card"],
        "earlier": t["earlier"],
        "later": t["later"],
        "discussion": t["discussion"],
        "shuffled": t["shuffled_status"],
        "moved": t["moved_status"],
        "revealed": t["revealed_status"],
        "shareTitle": t["heading"],
        "shareText": t["lead"],
        "shared": t["shared"],
        "cancelled": t["cancelled"],
        "copied": t["copied"],
        "copyFailed": t["copy_failed"],
    }
    data_json = json.dumps(STORIES, ensure_ascii=False).replace("</", "<\\/")
    prompts_json = json.dumps(PROMPTS, ensure_ascii=False).replace("</", "<\\/")
    copy_json = json.dumps(client_copy, ensure_ascii=False).replace("</", "<\\/")
    order_json = json.dumps(STATIC_ORDER)

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
<div class="controls"><div><span class="control-label">{html.escape(t["story_label"])}</span><div class="seg" id="story-buttons" role="group" aria-label="{html.escape(t["story_label"])}">{story_buttons}</div></div></div>
<div class="actions"><button class="button" id="shuffle-cards" type="button">{html.escape(t["shuffle"])}</button><button class="button secondary" id="reveal-order" type="button">{html.escape(t["reveal"])}</button><button class="button secondary" id="print-cards" type="button">{html.escape(t["print"])}</button><button class="button secondary" id="share-tool" type="button">{html.escape(t["share"])}</button></div>
<p class="status" id="status" aria-live="polite">{html.escape(t["shuffled_status"])}</p>
<div id="board-shell">{static_board(locale, t)}</div>
<p class="status">{html.escape(t["print_note"])}</p>
</section>
<section class="content-grid wrap"><article class="content-card"><h2>{html.escape(t["why_title"])}</h2><p>{html.escape(t["why_text"])}</p></article><article class="content-card"><h2>{html.escape(t["routine_title"])}</h2><ol>{routine}</ol></article><article class="content-card full"><h2>{html.escape(t["reuse_title"])}</h2><p>{html.escape(t["reuse_text"])}</p></article></section>
<section class="cta-card wrap"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_campaign, quote=True)}">{html.escape(t["app_cta"])}</a></section>
<section class="sources wrap"><h2>{html.escape(t["sources"])}</h2><ul>{sources}</ul><p>{html.escape(t["source_note"])}</p><div class="faq-list">{faq}</div></section>
</main>
<script>
const STORIES={data_json};
const PROMPTS={prompts_json};
const COPY={copy_json};
const LOCALE={json.dumps(locale)};
const STATIC_ORDER={order_json};
let storyIndex=0;
let order=[...STATIC_ORDER];
let revealed=false;
const shell=document.getElementById("board-shell");
const status=document.getElementById("status");

function shuffledOrder(){{
  const values=[0,1,2,3,4,5];
  for(let index=values.length-1;index>0;index--){{
    const swap=Math.floor(Math.random()*(index+1));
    [values[index],values[swap]]=[values[swap],values[index]];
  }}
  if(values.every((value,index)=>value===index)){{
    [values[0],values[1]]=[values[1],values[0]];
  }}
  return values;
}}

function sentenceHTML(page){{
  return page.phrases.map(phrase=>{{
    const tokens=phrase.tokens.map(token=>`<ruby>${{token.char}}<rt>${{token.reading}}</rt></ruby>`).join("");
    return `<span class="phrase">${{tokens}}${{phrase.after||""}}</span>`;
  }}).join("");
}}

function render(){{
  const story=STORIES[storyIndex];
  const cards=order.map((originalIndex,position)=>`<article class="event-card"><span class="slot">${{COPY.card}} ${{position+1}}</span><p class="sentence">${{sentenceHTML(story.pages[originalIndex])}}</p><div class="move"><button type="button" data-position="${{position}}" data-move="-1" ${{position===0?"disabled":""}}>${{COPY.earlier}}</button><button type="button" data-position="${{position}}" data-move="1" ${{position===order.length-1?"disabled":""}}>${{COPY.later}}</button></div></article>`).join("");
  const prompts=PROMPTS[story.id][LOCALE].map(prompt=>`<li>${{prompt}}</li>`).join("");
  shell.innerHTML=`<h3 class="board-title">${{story.titles[LOCALE]}}</h3><div class="board" id="board">${{cards}}</div><aside class="prompts"><h3>${{COPY.discussion}}</h3><ol>${{prompts}}</ol></aside>`;
  document.querySelectorAll("#story-buttons button").forEach((button,index)=>button.classList.toggle("on",index===storyIndex));
}}

function resetCards(){{
  order=shuffledOrder();
  revealed=false;
  status.textContent=COPY.shuffled;
  render();
}}

document.getElementById("story-buttons").addEventListener("click",event=>{{
  const button=event.target.closest("button[data-story]");
  if(!button)return;
  storyIndex=Number(button.dataset.story);
  resetCards();
}});
document.getElementById("board-shell").addEventListener("click",event=>{{
  const button=event.target.closest("button[data-move]");
  if(!button)return;
  const position=Number(button.dataset.position);
  const destination=position+Number(button.dataset.move);
  if(destination<0||destination>=order.length)return;
  [order[position],order[destination]]=[order[destination],order[position]];
  revealed=false;
  status.textContent=COPY.moved;
  render();
}});
document.getElementById("shuffle-cards").addEventListener("click",resetCards);
document.getElementById("reveal-order").addEventListener("click",()=>{{
  order=[0,1,2,3,4,5];
  revealed=true;
  status.textContent=COPY.revealed;
  render();
}});
document.getElementById("print-cards").addEventListener("click",()=>window.print());
document.getElementById("share-tool").addEventListener("click",async()=>{{
  const payload={{title:COPY.shareTitle,text:COPY.shareText,url:window.location.href}};
  if(navigator.share){{
    try{{await navigator.share(payload);status.textContent=COPY.shared;return;}}
    catch(error){{if(error&&error.name==="AbortError"){{status.textContent=COPY.cancelled;return;}}}}
  }}
  try{{await navigator.clipboard.writeText(window.location.href);status.textContent=COPY.copied;}}
  catch(error){{status.textContent=`${{COPY.copyFailed}} ${{window.location.href}}`;}}
}});
resetCards();
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
        r'zhuyin-decodable-mini-reader\.html">.*?</article>)',
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
        print(f"zhuyin story sequencing cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
