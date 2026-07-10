#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, print-ready Zhuyin library storytime kit."""
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
SLUG = "zhuyin-library-storytime-kit"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
META_REVIEW = "https://centaur.reading.ac.uk/80756/"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phoneticWrite.jsp?la=0"
OCAC_STARTER = "https://taiwancenter.taiwan-world.net/material/basic/content/54"

SESSION_STEPS = {
    "en": (
        {
            "time": "0–3 min",
            "title": "Welcome with choices",
            "text": "Show the three participation choices: listen, point or join. A child may also watch quietly or stop.",
        },
        {
            "time": "3–6 min",
            "title": "Warm up three symbols",
            "text": "The facilitator models three symbols found in the selected authorized book. Families echo, gesture or simply listen.",
        },
        {
            "time": "6–18 min",
            "title": "Read for meaning",
            "text": "Read the approved book naturally. Pause at pictures and conversation, not at every annotation, and never turn the group into a quiz.",
        },
        {
            "time": "18–23 min",
            "title": "Try a symbol hunt",
            "text": "Use the original blank hunt card below. Families notice one of today's symbols in the authorized copy beside them.",
        },
        {
            "time": "23–27 min",
            "title": "Retell in any mode",
            "text": "Invite a word, gesture, drawing or acted moment. Recast naturally without public correction or ranking.",
        },
        {
            "time": "27–30 min",
            "title": "Send one gentle idea home",
            "text": "Give the original take-home card, remind families to use a legally available book and close before attention is exhausted.",
        },
    ),
    "zh-Hant": (
        {
            "time": "0–3 分鐘",
            "title": "用選擇迎接家庭",
            "text": "先說明三種參與方式：聽、指、一起說；孩子也可以安靜觀看或停止。",
        },
        {
            "time": "3–6 分鐘",
            "title": "暖身三個符號",
            "text": "帶領者示範授權書籍中出現的三個符號；家庭可跟念、做手勢，也可只聽。",
        },
        {
            "time": "6–18 分鐘",
            "title": "以理解故事為主",
            "text": "自然朗讀館方核可的書；在圖片與對話處停頓，不逐字考注音，也不把團體變成測驗。",
        },
        {
            "time": "18–23 分鐘",
            "title": "進行符號尋寶",
            "text": "使用下方原創空白尋寶卡，讓家庭從身旁合法使用的書中找今天的一個符號。",
        },
        {
            "time": "23–27 分鐘",
            "title": "用任何方式重述",
            "text": "詞語、手勢、畫圖或演一個片段都可以；自然重述，不公開糾正或排名。",
        },
        {
            "time": "27–30 分鐘",
            "title": "帶一個溫和點子回家",
            "text": "發下原創家庭提示卡，提醒使用合法取得的書，並在注意力耗盡前收尾。",
        },
    ),
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Free Zhuyin Library Storytime Kit",
        "description": (
            "A bilingual, print-ready 30-minute Zhuyin storytime plan for libraries "
            "and heritage centers, with rights checks, symbol-hunt cards and no child data."
        ),
        "eyebrow": "Free library program kit · no login",
        "lead": (
            "Run a low-pressure Traditional Chinese storytime without copying a book, "
            "collecting child profiles or turning Zhuyin into a public test."
        ),
        "badges": (
            "30-minute reusable program",
            "English + Traditional Chinese",
            "No story text or child data saved",
        ),
        "start": "Open the program plan",
        "language": "繁體中文",
        "rights": "Confirm rights before choosing the book",
        "rights_text": (
            "Copyright rules, licenses and library policies differ by place. This kit "
            "contains no story and grants no right to perform, display, record, stream, "
            "photograph, scan or distribute a book. Staff must approve the selected title "
            "and planned use under current local law, licenses, publisher terms and library policy."
        ),
        "rights_items": (
            "Use only a library-owned, borrowed or otherwise authorized copy approved for the planned in-person program.",
            "Do not record, livestream or publish page images unless the rights holder, license and local policy explicitly permit it.",
            "Do not paste book text, titles, scans, photographs or recordings into this page; it has no upload field.",
            "If rights are unclear, choose another approved title or ask the library's designated copyright contact.",
        ),
        "plan": "Thirty-minute family storytime",
        "plan_intro": (
            "Choose any approved Traditional Chinese picture book with readable Zhuyin. "
            "The book supplies the story; this original kit supplies only the interaction structure."
        ),
        "print": "Print the storytime kit",
        "share": "Share tool",
        "shared": "Tool link copied.",
        "share_title": "Free Zhuyin library storytime kit",
        "hunt": "Blank three-symbol hunt card",
        "hunt_intro": (
            "The facilitator writes three symbols already visible in the approved book. "
            "Families may notice them without reading every annotation aloud."
        ),
        "hunt_rows": (
            ("Symbol 1", "________", "○ heard  ○ saw  ○ pointed  ○ air-traced"),
            ("Symbol 2", "________", "○ heard  ○ saw  ○ pointed  ○ air-traced"),
            ("Symbol 3", "________", "○ heard  ○ saw  ○ pointed  ○ air-traced"),
        ),
        "hunt_headers": ("Card", "Today's symbol", "Any participation counts"),
        "take_home": "Family take-home card",
        "take_home_steps": (
            "Use a book your family may legally borrow, own or access.",
            "Let the child choose one page or picture.",
            "Notice one annotation without asking for a score.",
            "Talk, point, act or draw for up to ten gentle minutes.",
            "Stop when the child wants to stop; return borrowed material on time.",
        ),
        "note": "Anonymous facilitator note",
        "note_intro": (
            "No attendance names. Record only an optional aggregate program note on paper; "
            "blank lines are fine and nothing is submitted here."
        ),
        "note_lines": (
            "Families present (optional total only): __________",
            "Participation noticed: ○ chose  ○ listened  ○ pointed  ○ acted  ○ spoke  ○ stopped",
            "One program adjustment for next time: ____________________________________",
        ),
        "privacy": "No child data collection",
        "privacy_text": (
            "There is no registration, name field, attendance form, account, camera, "
            "microphone, upload, analytics input, local storage or saved child profile. "
            "This page does not receive the title used, session notes, images, audio or video."
        ),
        "evidence": "Evidence boundary",
        "evidence_text": (
            "A 2020 systematic review and meta-analysis covered 19 randomized trials "
            "with 2,594 children. Parent/caregiver book-sharing interventions showed "
            "small average effects on expressive language (d = 0.41) and receptive "
            "language (d = 0.26), plus a larger effect on caregiver book-sharing "
            "competence (d = 1.01). Those studies did not test group library storytime, "
            "Zhuyin, this 30-minute structure, symbol-hunt cards or this kit. The results "
            "cannot justify a promise about attendance, language gains or reading scores."
        ),
        "sources": "Research and official references",
        "source_items": (
            ("Shared picture-book reading systematic review and meta-analysis", META_REVIEW),
            ("Taiwan Ministry of Education Bopomofo Handbook", MOE_HANDBOOK),
            ("Taiwan Ministry of Education Bopomofo Practice Book", MOE_PRACTICE),
            ("OCAC Let's Learn Mandarin Starter (Bopomofo)", OCAC_STARTER),
        ),
        "reuse": "Reuse the original program cards",
        "reuse_text": (
            "Libraries and heritage centers may print or adapt this original routine, "
            "blank hunt card and take-home prompt under CC BY 4.0 with credit to iOS "
            "App Guide and a link to this page. The license covers no book or external source."
        ),
        "app_title": "Optional practice after the program",
        "app_text": (
            "The complete storytime works without an app. Families who want structured "
            "practice after the event can use Lumi Bopomofo for listening, tracing, tones "
            "and blending across all 37 symbols. It is free to download with an optional "
            "one-time lifetime unlock, has no ads and requires no account."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "related": "Related free resources",
        "related_items": (
            (
                "Family Zhuyin picture-book club kit",
                f"{SITE}/tools/zhuyin-family-picture-book-club-kit.html",
            ),
            (
                "Five-day heritage-school lesson plan",
                f"{SITE}/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            ),
            (
                "Parent-teacher Zhuyin handoff kit",
                f"{SITE}/tools/zhuyin-parent-teacher-handoff-kit.html",
            ),
            ("3-minute Zhuyin skills check", f"{SITE}/tools/zhuyin-readiness-check.html"),
        ),
        "faq": "Library FAQ",
        "faq_items": (
            (
                "Does this kit include or license a picture book?",
                "No. It includes original program prompts only. The library must separately approve the title and every planned use.",
            ),
            (
                "Can the library record or livestream the reading?",
                "This kit grants no such right. Check the rights holder, current license, local law and library policy before any recording or transmission.",
            ),
            (
                "Does the anonymous note assess children?",
                "No. It is an optional aggregate program note, not attendance tracking, a child profile or a learning assessment.",
            ),
            (
                "Must families use Lumi Bopomofo?",
                "No. The full program uses an approved book, facilitator interaction and the original printable cards.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": (
            "Independent library program resource; not legal advice, an official "
            "curriculum, a child assessment or a promise of learning results."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "圖書館注音親子故事時間包｜免費英繁雙語",
        "description": "給圖書館與台灣華語中心的英繁雙語 30 分鐘注音故事時間包，含權利檢核、符號尋寶卡與無姓名紀錄；可列印、免登入。",
        "eyebrow": "免費圖書館活動包 · 免登入",
        "lead": "不複製繪本、不蒐集孩子檔案，也不把注音變成公開測驗，就能帶一場低壓力繁體中文故事時間。",
        "badges": ("30 分鐘可重複流程", "英文＋繁體中文", "不儲存故事文字或孩子資料"),
        "start": "開啟活動流程",
        "language": "English",
        "rights": "選書前先確認使用權利",
        "rights_text": "各地著作權規定、授權與館方政策不同。本工具不含任何故事，也不授予朗讀、展示、錄影、直播、拍照、掃描或散布書籍的權利。館員必須依當地現行法規、授權、出版社條款與館方政策，核准選書與預定使用方式。",
        "rights_items": (
            "只使用館藏、借閱或以其他方式合法取得，且經館方核准可用於預定現場活動的版本。",
            "除非權利人、授權與館方政策明確允許，否則不錄影、不直播，也不發布書頁圖片。",
            "不要把書中文字、書名、掃描、照片或錄音錄影貼進本頁；本頁沒有上傳欄位。",
            "權利不明時，改選另一個核准書目，或詢問館方指定的著作權聯絡人。",
        ),
        "plan": "30 分鐘親子故事時間",
        "plan_intro": "選一本館方核准、附有清楚注音的繁體中文繪本。書籍提供故事；本原創工具只提供互動結構。",
        "print": "列印故事時間包",
        "share": "分享工具",
        "shared": "已複製工具連結。",
        "share_title": "免費圖書館注音親子故事時間包",
        "hunt": "三格空白符號尋寶卡",
        "hunt_intro": "帶領者寫下館方核可書籍中已出現的三個符號；家庭可以注意它們，不必逐一朗讀所有注音。",
        "hunt_rows": (
            ("符號 1", "________", "○ 聽到　○ 看到　○ 指出　○ 空中描寫"),
            ("符號 2", "________", "○ 聽到　○ 看到　○ 指出　○ 空中描寫"),
            ("符號 3", "________", "○ 聽到　○ 看到　○ 指出　○ 空中描寫"),
        ),
        "hunt_headers": ("卡片", "今日符號", "任何參與方式都算"),
        "take_home": "家庭帶回提示卡",
        "take_home_steps": (
            "使用家庭可合法借閱、購買或存取的書。",
            "讓孩子自己選一頁或一張圖。",
            "注意一個注音，不要求分數。",
            "溫和對話、指圖、演一演或畫圖，最多 10 分鐘。",
            "孩子想停止就停止；借閱資料請準時歸還。",
        ),
        "note": "無姓名活動紀錄",
        "note_intro": "不記出席者姓名；只在紙上留下選填的整體活動觀察。空白也沒關係，本頁不接收任何內容。",
        "note_lines": (
            "參與家庭（只填選用總數）：__________",
            "觀察到的參與：○ 選擇　○ 聆聽　○ 指認　○ 動作　○ 說話　○ 停止",
            "下次活動可調整一件事：____________________________________",
        ),
        "privacy": "不蒐集孩子資料",
        "privacy_text": "沒有報名、姓名欄、出席表單、帳號、相機、麥克風、上傳、分析輸入、local storage 或孩子檔案。本頁不接收使用書名、活動紀錄、圖片、聲音或影片。",
        "evidence": "研究證據的界線",
        "evidence_text": "2020 年一篇系統性回顧與統合分析納入 19 項隨機試驗、共 2,594 名孩子。由家長／照顧者帶領的共讀介入，對表達語言（d = 0.41）與理解語言（d = 0.26）呈現小幅平均效果，對照顧者共讀能力的效果較大（d = 1.01）。這些研究沒有測試圖書館團體故事時間、注音、本 30 分鐘流程、符號尋寶卡或本工具，因此不能據此承諾出席率、語言進步或閱讀分數。",
        "sources": "研究與官方參考",
        "source_items": (
            ("親子繪本共讀系統性回顧與統合分析", META_REVIEW),
            ("台灣教育部《國語注音符號手冊》", MOE_HANDBOOK),
            ("台灣教育部《注音練習簿》", MOE_PRACTICE),
            ("僑委會《學華語向前走》入門冊（注音符號版）", OCAC_STARTER),
        ),
        "reuse": "自由使用原創活動卡",
        "reuse_text": "圖書館與台灣華語中心可依 CC BY 4.0 列印或改編本原創流程、空白尋寶卡與家庭提示；請標註 iOS App Guide 並連回本頁。此授權不涵蓋任何書籍或外部來源。",
        "app_title": "活動後的選用練習",
        "app_text": "不使用 App 也能完整進行故事時間。活動後若家庭想做有結構的練習，可使用 Lumi 注音星球練習全部 37 個符號的聽音、描寫、聲調與拼讀。可免費下載，另可選擇一次性永久解鎖；無廣告、免帳號。",
        "app_cta": "試用 Lumi 注音星球",
        "related": "相關免費資源",
        "related_items": (
            (
                "家庭注音繪本四週共讀包",
                f"{SITE}/zh-Hant/tools/zhuyin-family-picture-book-club-kit.html",
            ),
            (
                "海外中文學校五日教案",
                f"{SITE}/zh-Hant/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            ),
            (
                "家庭—教師注音交接包",
                f"{SITE}/zh-Hant/tools/zhuyin-parent-teacher-handoff-kit.html",
            ),
            (
                "3 分鐘注音學習檢核",
                f"{SITE}/zh-Hant/tools/zhuyin-readiness-check.html",
            ),
        ),
        "faq": "圖書館常見問題",
        "faq_items": (
            ("本工具有附繪本或授權繪本嗎？", "沒有。它只提供原創活動提示；館方必須另外核准書目與每一種預定使用方式。"),
            ("圖書館可以錄影或直播朗讀嗎？", "本工具不授予這類權利。錄製或傳送前，請查核權利人、現行授權、當地法規與館方政策。"),
            ("無姓名紀錄能評量孩子嗎？", "不能。它只是選填的整體活動觀察，不是出席追蹤、孩子檔案或學習評量。"),
            ("家庭一定要使用 Lumi 注音星球嗎？", "不用。館方核准的書、帶領者互動與原創列印卡，就能完成整場活動。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立圖書館活動資源；不是法律意見、官方課程、孩子評量或學習成效保證。",
    },
}

STYLE = """
:root{--ink:#243044;--muted:#667287;--paper:#fffef9;--line:#dedcd3;--navy:#34547a;--teal:#34796f;--gold:#b7822e;--soft:#edf7f4}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#f6fbff 0,#f3faf7 48%,#fff9ed 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}a{color:#315f87}.wrap{width:min(1060px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:4;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850}.links{display:flex;gap:15px}.hero{padding:58px 0 30px}.eyebrow{color:var(--teal);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:940px;margin:.18em 0;font-size:clamp(2rem,5.8vw,4rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:820px;color:var(--muted);font-size:clamp(1.08rem,2.5vw,1.27rem)}.badges,.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.badge{padding:8px 12px;border:1px solid #cde0d9;border-radius:999px;background:#fff;color:#3e665d;font-weight:800;white-space:nowrap}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--teal),#4e9487);color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #34796f28}.button.secondary{background:#fff;color:#315f87!important;border:1px solid #c9d6e2;box-shadow:none}.button:focus-visible{outline:3px solid #e2b858;outline-offset:3px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{grid-column:span 12;padding:23px;background:var(--paper);border:1px solid var(--line);border-radius:23px;box-shadow:0 10px 32px #34281a12}.half{grid-column:span 6}h2{margin:1.5em 0 .58em;font-size:clamp(1.45rem,3vw,2rem);line-height:1.18}h3{line-height:1.25}.muted{color:var(--muted)}.notice{padding:17px 19px;border-left:5px solid var(--gold);border-radius:14px;background:#fff7dc}.rights{margin-bottom:28px}.plan{padding:clamp(22px,4vw,34px);background:#fff;border:1px solid #d7d9d4;border-radius:28px;box-shadow:0 20px 55px #23354b15}.plan-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap}.plan-head h2{margin:.1em 0}.timeline{margin-top:20px}.step{display:grid;grid-template-columns:92px 1fr;gap:16px;padding:16px 0;border-bottom:1px solid var(--line)}.step:last-child{border-bottom:0}.time{color:var(--teal);font-weight:900;white-space:nowrap}.step h3{margin:0}.step p{margin:.2em 0;color:var(--muted)}.print-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:28px}.sheet{padding:20px;border:1px solid #ccd8e4;border-radius:19px;background:#fff}.sheet.full{grid-column:1/-1}.hunt{width:100%;border-collapse:collapse}.hunt th,.hunt td{padding:11px;border:1px solid var(--line);text-align:left}.hunt th{background:#edf7f4;white-space:nowrap}.hunt td:first-child,.hunt td:nth-child(2){white-space:nowrap}.line{padding:10px 0;border-bottom:1px solid #838b94}.source-list a{overflow-wrap:anywhere}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--teal);font-weight:800}
@media(max-width:760px){.half{grid-column:span 12}.print-grid{grid-template-columns:1fr}.links a:first-child{display:none}.hero{padding-top:38px}.step{grid-template-columns:74px 1fr}.hunt{display:block;overflow-x:auto}.hunt th,.hunt td{min-width:130px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.extras,.app-card,.related,.faq,.evidence-section,.footer,.actions{display:none!important}body{background:#fff;font-size:10pt}.wrap{width:100%}.rights,.plan,.sheet,.card{border:0;box-shadow:none;padding:0}.rights{margin-bottom:5mm}.plan-head{margin-bottom:3mm}.step{padding:2.5mm 0}.print-grid{grid-template-columns:1fr 1fr;gap:7mm}.sheet{break-inside:avoid}.sheet.full{grid-column:1/-1;border-top:1px solid #999;padding-top:4mm}.hunt th,.hunt td{padding:2mm}@page{size:A4;margin:10mm}}
"""

SCRIPT = """
(function(){
  "use strict";
  var cfg=JSON.parse(document.getElementById("kit-config").textContent);
  document.getElementById("print-kit").addEventListener("click",function(){window.print();});
  document.getElementById("share-kit").addEventListener("click",function(){
    var status=document.getElementById("share-status");
    var data={title:cfg.shareTitle,url:location.href.split("#")[0]};
    if(navigator.share){
      navigator.share(data).catch(function(error){
        if(error.name!=="AbortError"){status.textContent=data.url;}
      });
    }else if(navigator.clipboard){
      navigator.clipboard.writeText(data.url)
        .then(function(){status.textContent=cfg.shared;})
        .catch(function(){status.textContent=data.url;});
    }else{
      status.textContent=data.url;
    }
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


def render_page(locale: str) -> str:
    t = COPY[locale]
    url = canonical(locale)
    other_locale = "zh-Hant" if locale == "en" else "en"
    alternate = canonical(other_locale)
    home = f"{SITE}/{'zh-Hant/' if locale == 'zh-Hant' else ''}index.html"
    app_url = appstore_url("lumibopomofo", f"iag_storytime_{locale.lower()}")
    rights_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["rights_items"]
    )
    steps = "".join(
        '<article class="step">'
        f'<div class="time">{html.escape(step["time"])}</div><div>'
        f'<h3>{html.escape(step["title"])}</h3><p>{html.escape(step["text"])}</p>'
        "</div></article>"
        for step in SESSION_STEPS[locale]
    )
    hunt_headers = "".join(
        f"<th>{html.escape(header)}</th>" for header in t["hunt_headers"]
    )
    hunt_rows = "".join(
        f"<tr><td>{html.escape(card)}</td><td>{html.escape(symbol)}</td>"
        f"<td>{html.escape(actions)}</td></tr>"
        for card, symbol, actions in t["hunt_rows"]
    )
    take_home = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["take_home_steps"]
    )
    note_lines = "".join(
        f'<div class="line">{html.escape(line)}</div>' for line in t["note_lines"]
    )
    sources = "".join(
        f'<li><a href="{html.escape(source_url)}" rel="noopener">{html.escape(label)}</a></li>'
        for label, source_url in t["source_items"]
    )
    related = "".join(
        f'<li><a href="{html.escape(resource_url)}">{html.escape(label)}</a></li>'
        for label, resource_url in t["related_items"]
    )
    faq_html = "".join(
        f"<h3>{html.escape(question)}</h3><p>{html.escape(answer)}</p>"
        for question, answer in t["faq_items"]
    )
    config_json = json.dumps(
        {"shareTitle": t["share_title"], "shared": t["shared"]},
        ensure_ascii=False,
    ).replace("</", "<\\/")
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
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "learningResourceType": "Library storytime program kit",
            "educationalUse": "Heritage-language family programming",
            "educationalLevel": "Beginner",
            "typicalAgeRange": "4-8",
            "timeRequired": "PT30M",
            "license": LICENSE,
            "teaches": [
                "Low-pressure shared reading with Zhuyin annotations",
                "Family participation during library storytime",
                "Noticing selected Bopomofo symbols in an authorized book",
            ],
            "citation": [META_REVIEW, MOE_HANDBOOK, MOE_PRACTICE, OCAC_STARTER],
            "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
        },
        {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": t["title"],
            "description": t["description"],
            "totalTime": "PT30M",
            "step": [
                {
                    "@type": "HowToStep",
                    "position": index,
                    "name": f'{step["time"]}: {step["title"]}',
                    "text": step["text"],
                }
                for index, step in enumerate(SESSION_STEPS[locale], 1)
            ],
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
                for question, answer in t["faq_items"]
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": t["home"], "item": home},
                {"@type": "ListItem", "position": 2, "name": t["title"], "item": url},
            ],
        },
    ]
    ld = "\n".join(json_script(schema) for schema in schemas)
    badges = "".join(
        f'<span class="badge">✓ {html.escape(badge)}</span>' for badge in t["badges"]
    )
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
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{SITE}/tools/">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["language"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#plan">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div></section>
<section class="wrap rights"><article class="card"><h2>{html.escape(t["rights"])}</h2><p class="notice">{html.escape(t["rights_text"])}</p><ul>{rights_items}</ul></article></section>
<section class="wrap plan" id="plan"><div class="plan-head"><div><h2>{html.escape(t["plan"])}</h2><p class="muted">{html.escape(t["plan_intro"])}</p></div><div class="actions"><button class="button secondary" id="print-kit" type="button">{html.escape(t["print"])}</button><button class="button" id="share-kit" type="button">{html.escape(t["share"])}</button></div></div><div class="timeline">{steps}</div><div class="print-grid"><article class="sheet"><h3>{html.escape(t["hunt"])}</h3><p>{html.escape(t["hunt_intro"])}</p><table class="hunt"><thead><tr>{hunt_headers}</tr></thead><tbody>{hunt_rows}</tbody></table></article><article class="sheet"><h3>{html.escape(t["take_home"])}</h3><ol>{take_home}</ol></article><article class="sheet full"><h3>{html.escape(t["note"])}</h3><p>{html.escape(t["note_intro"])}</p>{note_lines}</article></div><div class="share-status" id="share-status" aria-live="polite"></div></section>
<section class="wrap grid extras"><article class="card half"><h2>{html.escape(t["privacy"])}</h2><p>{html.escape(t["privacy_text"])}</p></article><article class="card half"><h2>{html.escape(t["reuse"])}</h2><p>{html.escape(t["reuse_text"])}</p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></article></section>
<section class="wrap grid evidence-section"><article class="card"><h2>{html.escape(t["evidence"])}</h2><p>{html.escape(t["evidence_text"])}</p><h3>{html.escape(t["sources"])}</h3><ul class="source-list">{sources}</ul></article></section>
<section class="wrap grid related"><article class="card half app-card"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_url)}" rel="nofollow noopener">{html.escape(t["app_cta"])}</a></article><article class="card half"><h2>{html.escape(t["related"])}</h2><ul>{related}</ul></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq"])}</h2>{faq_html}</section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="kit-config">{config_json}</script>
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
        f'<a href="{target}">Zhuyin Library Storytime Kit</a></h2>'
        "<p>A bilingual, rights-aware 30-minute family program.</p>"
        "</article>"
    )
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(target)
        + r'">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    anchor = re.search(
        r'<article class="card third"><h2><a href="'
        r'zhuyin-parent-teacher-handoff-kit\.html">.*?</article>',
        updated,
        re.S,
    )
    if anchor:
        position = anchor.end()
        updated = updated[:position] + card + updated[position:]
    else:
        marker = '<section class="wrap grid">'
        if marker in updated:
            updated = updated.replace(marker, marker + card, 1)
        elif "</section></main>" in updated:
            updated = updated.replace("</section></main>", card + "</section></main>", 1)
        else:
            raise RuntimeError("tools/index.html is missing its main grid marker")
    if updated == text:
        return False
    index.write_text(updated, encoding="utf-8")
    return True


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
    update_tools_index(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"library storytime kit -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
