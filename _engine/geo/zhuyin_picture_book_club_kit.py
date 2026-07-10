#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, print-ready family Zhuyin picture-book club kit."""
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
SLUG = "zhuyin-family-picture-book-club-kit"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
META_REVIEW = "https://centaur.reading.ac.uk/80756/"
MOE_DICTIONARY = "https://dict.mini.moe.edu.tw/"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
OCAC_STARTER = "https://taiwancenter.taiwan-world.net/material/basic/content/54"

WEEKS = {
    "en": (
        {
            "number": "Week 1",
            "title": "Choose and notice",
            "focus": "Keep the relationship first: let the child choose the book, page or picture.",
            "before": "Look at the cover and pictures. Ask, “Which page should we visit first?”",
            "during": "Point out one Zhuyin annotation without testing: “I notice ㄇ beside this character.”",
            "after": "Let the child choose one favorite picture and connect it to family life.",
            "finish": "Close while interest is still positive; rereading the same page is welcome.",
        },
        {
            "number": "Week 2",
            "title": "Hear and join",
            "focus": "Model one familiar annotated word and leave several seconds for any response.",
            "before": "Choose up to three words from your legal copy. Do not enter or upload the book text here.",
            "during": "Read naturally. The child may echo, point, make an action or simply listen.",
            "after": "Use one chosen word in a real family sentence instead of asking for a definition.",
            "finish": "Write only the next word to revisit on your private paper copy—never a score.",
        },
        {
            "number": "Week 3",
            "title": "Let the child lead",
            "focus": "The child controls the page turn, pace and one question for the adult.",
            "before": "Offer two choices: reread a familiar page or explore one new page.",
            "during": "Pause after a picture or sentence. If a character is unfamiliar, check one entry together in the MOE Mini Dictionary.",
            "after": "Ask, “What should we show someone else from this page?” Accept words, gestures or drawings.",
            "finish": "Stop before the exchange becomes a quiz or speed-reading task.",
        },
        {
            "number": "Week 4",
            "title": "Retell and celebrate",
            "focus": "Use pictures, props and family memories to retell—not to test exact recall.",
            "before": "Invite the child to choose three pictures or moments from the book.",
            "during": "Take turns telling what happened. Recast a word naturally without saying “wrong.”",
            "after": "Draw, act out or photograph a family object connected to the story; do not upload it here.",
            "finish": "Celebrate one specific interaction and let the child choose the next legal book.",
        },
    ),
    "zh-Hant": (
        {
            "number": "第 1 週",
            "title": "自己選、一起看",
            "focus": "把關係放第一：讓孩子自己選書、選頁或選圖。",
            "before": "先看封面和圖片，問：「今天想先去哪一頁？」",
            "during": "只自然指出一個注音，不考孩子：「我看到這個字旁邊有 ㄇ。」",
            "after": "讓孩子挑一張最喜歡的圖，再連到家裡的真實生活。",
            "finish": "孩子還有興趣時就收尾；重讀同一頁也很好。",
        },
        {
            "number": "第 2 週",
            "title": "聽一聽、一起加入",
            "focus": "大人示範一個熟悉的注音詞語，再留幾秒等待任何形式的回應。",
            "before": "從合法取得的繪本中選最多三個詞；不要把書中文字輸入或上傳到本頁。",
            "during": "自然朗讀；孩子可以跟念、指圖、做動作，也可以只聽。",
            "after": "把一個詞放進真實家庭句子，不要求孩子解釋詞義。",
            "finish": "只在自己的紙本記下下次想再看的詞，不記分數。",
        },
        {
            "number": "第 3 週",
            "title": "讓孩子帶著讀",
            "focus": "由孩子控制翻頁、節奏，並挑一個問題問大人。",
            "before": "給兩個選擇：重讀熟悉的一頁，或探索一頁新內容。",
            "during": "看到圖片或念完一句就停一下；遇到陌生國字，只一起查一筆教育部《國語小字典》。",
            "after": "問：「這一頁最想分享什麼？」詞語、手勢或畫圖都算回應。",
            "finish": "在互動變成考試或速度競賽前停止。",
        },
        {
            "number": "第 4 週",
            "title": "重述故事、慶祝互動",
            "focus": "用圖片、道具與家庭回憶重述，不考孩子是否精準背出內容。",
            "before": "請孩子從書中挑三張圖或三個片段。",
            "during": "輪流說發生什麼；讀音不同時自然重述，不說「答錯」。",
            "after": "畫圖、演一演，或拍下和故事有關的家中物品；不要上傳到本頁。",
            "finish": "肯定一個具體互動，再讓孩子挑下一本合法取得的書。",
        },
    ),
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Free 4-Week Family Zhuyin Picture-Book Club Kit",
        "description": (
            "A free bilingual, print-ready four-week family reading plan for legally "
            "owned or borrowed Traditional Chinese picture books with Zhuyin annotations."
        ),
        "eyebrow": "Free family reading kit · no login",
        "lead": (
            "Use one book you legally own or borrow, ten gentle minutes at a time. "
            "The prompts support shared conversation without copying book text or grading a child."
        ),
        "badges": (
            "4 reusable weekly routines",
            "Print or use on screen",
            "No book text or child data saved",
        ),
        "start": "Open the four-week plan",
        "language": "繁體中文",
        "choose": "Choose a suitable legal copy",
        "choose_items": (
            "Use a book your family owns, borrows from a library or accesses through an authorized service.",
            "Look for Traditional Chinese text with readable Zhuyin annotations and pictures the child wants to discuss.",
            "Choose a length that can stop after ten minutes without rushing to finish.",
            "Keep the physical or authorized digital book beside you; this page never asks for its text or images.",
        ),
        "copyright_title": "Copyright-safe by design",
        "copyright_text": (
            "This kit supplies only original prompts and a blank reading log. It does not "
            "host, reproduce or link to unauthorized copies of picture books. The CC BY 4.0 "
            "license covers this original kit—not any book, dictionary or linked source."
        ),
        "club": "Your four-week family club",
        "club_intro": (
            "Repeat a favorite book or choose a different legal copy each week. Ten minutes "
            "is a gentle structure, not a target to force."
        ),
        "before": "Before reading",
        "during": "During reading",
        "after": "After reading",
        "finish": "Gentle finish",
        "print": "Print the club kit",
        "share": "Share tool",
        "shared": "Tool link copied.",
        "share_title": "Free family Zhuyin picture-book club kit",
        "log": "Non-scored family reading log",
        "log_intro": (
            "Circle anything that happened; blank spaces are not failures. Keep the printed "
            "sheet at home. Nothing is submitted or saved by this page."
        ),
        "log_headers": ("Week", "Circle any moments you noticed", "One idea for next time"),
        "log_rows": (
            ("1", "○ child chose　○ noticed a picture　○ asked or answered", "________________"),
            ("2", "○ listened　○ joined a word　○ pointed or acted", "________________"),
            ("3", "○ led a page　○ waited and talked　○ checked one word", "________________"),
            ("4", "○ retold　○ connected to family　○ chose another book", "________________"),
        ),
        "privacy": "Private by default",
        "privacy_text": (
            "There is no account, title field, form submission, camera, microphone, upload, "
            "analytics input, local storage or saved child profile. Print handwriting stays with your family."
        ),
        "evidence": "What the evidence supports—and what it cannot prove",
        "evidence_text": (
            "A 2020 systematic review and meta-analysis covered 19 randomized trials with "
            "2,594 children; mean child ages across studies ranged from 1 to 6 years. "
            "Book-sharing interventions showed small average effects on expressive language "
            "(d = 0.41) and receptive language (d = 0.26), and a larger effect on caregiver "
            "book-sharing competence (d = 1.01). The review did not test Zhuyin, this exact "
            "four-week or ten-minute routine, independent reading, or this tool. We use it "
            "only to inform shared adult-child interaction—not to promise a learning result."
        ),
        "sources": "Research and official references",
        "source_items": (
            ("Shared picture-book reading systematic review and meta-analysis", META_REVIEW),
            ("Taiwan Ministry of Education Mini Dictionary", MOE_DICTIONARY),
            ("Taiwan Ministry of Education Bopomofo Handbook", MOE_HANDBOOK),
            ("OCAC Let's Learn Mandarin Starter (Bopomofo)", OCAC_STARTER),
        ),
        "reuse": "Print, adapt and share",
        "reuse_text": (
            "Families, libraries and heritage schools may print or adapt this original kit "
            "under CC BY 4.0 with credit to iOS App Guide and a link to this page."
        ),
        "app_title": "Optional practice between reading days",
        "app_text": (
            "Lumi Bopomofo adds listening, tracing, tone and blending games for all 37 "
            "symbols. It is free to download with an optional one-time lifetime unlock, "
            "has no ads and requires no recurring subscription. The club kit works without it."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "related": "Related free resources",
        "related_items": (
            ("3-minute Zhuyin skills check", f"{SITE}/tools/zhuyin-readiness-check.html"),
            ("Parent-teacher Zhuyin handoff kit", f"{SITE}/tools/zhuyin-parent-teacher-handoff-kit.html"),
            ("Grandparent Zhuyin video-call kit", f"{SITE}/tools/zhuyin-grandparent-video-call-kit.html"),
            ("Five-day heritage-school lesson plan", f"{SITE}/guides/zhuyin-5-day-lesson-plan-heritage-school.html"),
            ("Zhuyin flashcards", f"{SITE}/tools/zhuyin-flashcards.html"),
        ),
        "faq": "Family FAQ",
        "faq_items": (
            (
                "Does this page provide free copies of picture books?",
                "No. Use a book you legally own, borrow or access through an authorized service. This page provides original prompts only.",
            ),
            (
                "Must the child read every Zhuyin annotation aloud?",
                "No. Listening, pointing, choosing a picture, acting or joining one familiar word are all valid participation.",
            ),
            (
                "Does four weeks guarantee better Zhuyin or reading scores?",
                "No. Research supports the promise of shared book-reading interventions for language outcomes, but did not test Zhuyin, this schedule or this tool.",
            ),
            (
                "Does the page save our book title or reading log?",
                "No. There is no title field, account, form submission, upload or saved result. A printed handwritten log remains with your family.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": "Independent family reading resource; not an official curriculum, reading assessment or source of book copies.",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "家庭注音繪本共讀包｜免費四週計畫",
        "description": "英繁雙語、可列印的四週家庭共讀計畫：搭配合法購買或借閱的繁體中文注音繪本，不複製書中文字，也不儲存孩子資料。",
        "eyebrow": "免費家庭共讀工具 · 免登入",
        "lead": "每次用合法購買或借閱的一本書，溫和共讀 10 分鐘。提示只幫助親子對話，不複製繪本內容，也不替孩子打分。",
        "badges": ("四週可重複流程", "可直接看或列印", "不儲存書中文字或孩子資料"),
        "start": "開啟四週計畫",
        "language": "English",
        "choose": "選一本合法取得、適合共讀的書",
        "choose_items": (
            "使用家中購買、圖書館借閱，或透過合法授權服務取得的繪本。",
            "優先選繁體中文、注音清楚、圖片是孩子想聊的內容。",
            "選可以在 10 分鐘自然停下的長度，不急著一次讀完。",
            "把實體書或合法電子書放在身旁；本頁不會要求輸入書中文字或上傳圖片。",
        ),
        "copyright_title": "從設計上保護著作權",
        "copyright_text": "本工具只提供原創提示與空白共讀紀錄，不託管、不重製，也不連結未授權的繪本副本。CC BY 4.0 僅涵蓋本原創工具，不包含任何繪本、字典或外部來源。",
        "club": "四週家庭共讀計畫",
        "club_intro": "可以重讀同一本喜歡的書，也可每週選一本不同的合法書籍。10 分鐘是溫和結構，不是強迫完成的目標。",
        "before": "共讀前",
        "during": "共讀中",
        "after": "共讀後",
        "finish": "溫和收尾",
        "print": "列印共讀包",
        "share": "分享工具",
        "shared": "已複製工具連結。",
        "share_title": "免費家庭注音繪本共讀包",
        "log": "不計分的家庭共讀紀錄",
        "log_intro": "發生什麼就圈什麼；空白不是失敗。列印後留在家中，本頁不會送出或儲存任何紀錄。",
        "log_headers": ("週次", "圈出今天出現的互動", "下次想延續的一件事"),
        "log_rows": (
            ("1", "○ 自己選　○ 注意圖片　○ 提問或回應", "________________"),
            ("2", "○ 聆聽　○ 加入一個詞　○ 指圖或動作", "________________"),
            ("3", "○ 帶著翻頁　○ 等待對話　○ 查一個字", "________________"),
            ("4", "○ 重述　○ 連到家庭生活　○ 選下一本書", "________________"),
        ),
        "privacy": "預設保護隱私",
        "privacy_text": "沒有帳號、書名欄位、表單送出、相機、麥克風、上傳、分析輸入、local storage 或孩子檔案；紙本手寫內容只留在家中。",
        "evidence": "研究支持什麼？不能證明什麼？",
        "evidence_text": "2020 年一篇系統性回顧與統合分析納入 19 項隨機試驗、共 2,594 名孩子，各研究的平均年齡介於 1 至 6 歲。共讀介入對表達語言（d = 0.41）與理解語言（d = 0.26）呈現小幅平均效果，對照顧者共讀能力的效果較大（d = 1.01）。該回顧沒有測試注音、這套四週或 10 分鐘流程、自主閱讀，也沒有測試本工具。我們只用它支持親子共讀互動的設計，不承諾任何學習成果。",
        "sources": "研究與官方參考",
        "source_items": (
            ("親子繪本共讀系統性回顧與統合分析", META_REVIEW),
            ("台灣教育部《國語小字典》", MOE_DICTIONARY),
            ("台灣教育部《國語注音符號手冊》", MOE_HANDBOOK),
            ("僑委會《學華語向前走》入門冊（注音符號版）", OCAC_STARTER),
        ),
        "reuse": "可列印、改編與分享",
        "reuse_text": "家庭、圖書館與海外中文學校可依 CC BY 4.0 列印或改編本原創工具；請標註 iOS App Guide 並連回本頁。",
        "app_title": "兩次共讀之間的選用練習",
        "app_text": "Lumi 注音星球以聽音、描寫、聲調與拼讀遊戲練習全部 37 個符號。可免費下載，另提供一次性永久解鎖；無廣告、無定期訂閱。不使用 App 也能完整使用共讀包。",
        "app_cta": "試用 Lumi 注音星球",
        "related": "相關免費資源",
        "related_items": (
            ("3 分鐘注音學習檢核", f"{SITE}/zh-Hant/tools/zhuyin-readiness-check.html"),
            ("家庭—教師注音交接包", f"{SITE}/zh-Hant/tools/zhuyin-parent-teacher-handoff-kit.html"),
            ("祖孫視訊注音遊戲包", f"{SITE}/zh-Hant/tools/zhuyin-grandparent-video-call-kit.html"),
            ("海外中文學校五日教案", f"{SITE}/zh-Hant/guides/zhuyin-5-day-lesson-plan-heritage-school.html"),
            ("注音符號字卡", f"{SITE}/tools/zhuyin-flashcards.html"),
        ),
        "faq": "家庭常見問題",
        "faq_items": (
            ("本頁會提供免費繪本副本嗎？", "不會。請使用合法購買、借閱或透過授權服務取得的書；本頁只提供原創共讀提示。"),
            ("孩子一定要把每個注音都念出來嗎？", "不用。聆聽、指圖、選一張圖、做動作或加入一個熟悉詞語，都算有效參與。"),
            ("四週能保證提升注音或閱讀成績嗎？", "不能。研究顯示共讀介入對語言發展有潛力，但沒有測試注音、本流程或本工具。"),
            ("頁面會儲存書名或共讀紀錄嗎？", "不會。沒有書名欄位、帳號、表單送出、上傳或儲存結果；列印後的手寫紀錄只留在家中。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立家庭共讀資源；不是官方課程、閱讀評量或繪本副本來源。",
    },
}

STYLE = """
:root{--ink:#243047;--muted:#687287;--paper:#fffef9;--line:#e4dfd3;--plum:#70496f;--plum2:#a46582;--teal:#18776e;--gold:#bc852d;--soft:#faf1f5}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#fff8fb 0,#f5fbf9 48%,#fffaf0 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}a{color:#5f3d89}.wrap{width:min(1060px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:4;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850}.links{display:flex;gap:15px}.hero{padding:58px 0 30px}.eyebrow{color:var(--plum);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:940px;margin:.18em 0;font-size:clamp(2rem,5.8vw,4rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:820px;color:var(--muted);font-size:clamp(1.08rem,2.5vw,1.27rem)}.badges,.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.badge{padding:8px 12px;border:1px solid #e6d4dd;border-radius:999px;background:#fff;color:#74536b;font-weight:800;white-space:nowrap}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--plum),var(--plum2));color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #70496f28}.button.secondary{background:#fff;color:#5f3d89!important;border:1px solid #d6c8db;box-shadow:none}.button:focus-visible{outline:3px solid #e2b858;outline-offset:3px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{grid-column:span 12;padding:23px;background:var(--paper);border:1px solid var(--line);border-radius:23px;box-shadow:0 10px 32px #34281a12}.half{grid-column:span 6}.third{grid-column:span 4}h2{margin:1.5em 0 .58em;font-size:clamp(1.45rem,3vw,2rem);line-height:1.18}h3{line-height:1.25}.muted{color:var(--muted)}.selection{margin-bottom:28px}.notice{padding:17px 19px;border-left:5px solid var(--gold);border-radius:14px;background:#fff7dc}.kit{padding:clamp(22px,4vw,34px);background:#fff;border:1px solid #ded6ca;border-radius:28px;box-shadow:0 20px 55px #513a2815}.kit-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap}.kit-head h2{margin:.1em 0}.week-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:22px}.week{padding:21px;border:1px solid #e5d8df;border-radius:22px;background:linear-gradient(150deg,#fff7fb,#fff)}.week-no{color:var(--plum);font-weight:900;white-space:nowrap}.week h3{margin:.15em 0;font-size:1.35rem}.focus{color:var(--teal);font-weight:800}.phase{padding:11px 0;border-top:1px solid var(--line)}.phase b{display:block;color:var(--plum);white-space:nowrap}.phase p{margin:.2em 0}.log{width:100%;border-collapse:collapse;margin-top:12px}.log th,.log td{padding:12px;border:1px solid var(--line);text-align:left;vertical-align:top}.log th{background:#f8f1f6;white-space:nowrap}.log td:first-child{font-weight:900;color:var(--plum);white-space:nowrap}.privacy{margin-top:18px}.source-list a{overflow-wrap:anywhere}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--teal);font-weight:800}
@media(max-width:760px){.half,.third{grid-column:span 12}.week-grid{grid-template-columns:1fr}.links a:first-child{display:none}.hero{padding-top:38px}.log{display:block;overflow-x:auto}.log th,.log td{min-width:150px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.selection,.extras,.app-card,.related,.faq,.evidence-section,.footer,.actions{display:none!important}body{background:#fff;font-size:10pt}.wrap{width:100%}.kit,.card{border:0;box-shadow:none;padding:0}.week-grid{grid-template-columns:1fr 1fr;gap:6mm}.week{break-inside:avoid;padding:4mm}.phase{padding:2mm 0}.log{font-size:9pt}.log th,.log td{padding:2.5mm}@page{size:A4;margin:10mm}}
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
    app_url = appstore_url("lumibopomofo", f"iag_bookclub_{locale.lower()}")
    choose_items = "".join(f"<li>{html.escape(item)}</li>" for item in t["choose_items"])
    weeks = "".join(
        '<article class="week">'
        f'<div class="week-no">{html.escape(week["number"])}</div>'
        f'<h3>{html.escape(week["title"])}</h3>'
        f'<p class="focus">{html.escape(week["focus"])}</p>'
        f'<div class="phase"><b>{html.escape(t["before"])}</b><p>{html.escape(week["before"])}</p></div>'
        f'<div class="phase"><b>{html.escape(t["during"])}</b><p>{html.escape(week["during"])}</p></div>'
        f'<div class="phase"><b>{html.escape(t["after"])}</b><p>{html.escape(week["after"])}</p></div>'
        f'<div class="phase"><b>{html.escape(t["finish"])}</b><p>{html.escape(week["finish"])}</p></div>'
        "</article>"
        for week in WEEKS[locale]
    )
    log_rows = "".join(
        f"<tr><td>{html.escape(week)}</td><td>{html.escape(moments)}</td>"
        f"<td>{html.escape(next_time)}</td></tr>"
        for week, moments, next_time in t["log_rows"]
    )
    log_headers = "".join(f"<th>{html.escape(header)}</th>" for header in t["log_headers"])
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
            "browserRequirements": "JavaScript",
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "learningResourceType": "Family picture-book club kit",
            "educationalUse": "Heritage-language shared reading",
            "educationalLevel": "Beginner",
            "typicalAgeRange": "4-8",
            "timeRequired": "P4W",
            "license": LICENSE,
            "teaches": [
                "Interactive family shared reading",
                "Using Zhuyin annotations during Traditional Chinese reading",
                "Low-pressure heritage-language conversation",
            ],
            "citation": [META_REVIEW, MOE_DICTIONARY, MOE_HANDBOOK, OCAC_STARTER],
            "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
        },
        {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": t["title"],
            "description": t["description"],
            "totalTime": "P4W",
            "step": [
                {
                    "@type": "HowToStep",
                    "position": index,
                    "name": f'{week["number"]}: {week["title"]}',
                    "text": f'{week["focus"]} {week["before"]} {week["during"]} {week["after"]}',
                }
                for index, week in enumerate(WEEKS[locale], 1)
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
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#club">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div></section>
<section class="wrap grid selection"><article class="card half"><h2>{html.escape(t["choose"])}</h2><ul>{choose_items}</ul></article><article class="card half"><h2>{html.escape(t["copyright_title"])}</h2><p class="notice">{html.escape(t["copyright_text"])}</p></article></section>
<section class="wrap kit" id="club"><div class="kit-head"><div><h2>{html.escape(t["club"])}</h2><p class="muted">{html.escape(t["club_intro"])}</p></div><div class="actions"><button class="button secondary" id="print-kit" type="button">{html.escape(t["print"])}</button><button class="button" id="share-kit" type="button">{html.escape(t["share"])}</button></div></div><div class="week-grid">{weeks}</div><h2>{html.escape(t["log"])}</h2><p class="muted">{html.escape(t["log_intro"])}</p><table class="log"><thead><tr>{log_headers}</tr></thead><tbody>{log_rows}</tbody></table><div class="share-status" id="share-status" aria-live="polite"></div></section>
<section class="wrap grid extras"><article class="card half privacy"><h2>{html.escape(t["privacy"])}</h2><p>{html.escape(t["privacy_text"])}</p></article><article class="card half"><h2>{html.escape(t["reuse"])}</h2><p>{html.escape(t["reuse_text"])}</p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></article></section>
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
        f'<a href="{target}">Family Zhuyin Picture-Book Club Kit</a></h2>'
        "<p>A bilingual, print-ready four-week shared-reading plan.</p>"
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
        r'zhuyin-grandparent-video-call-kit\.html">.*?</article>',
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
        print(f"picture-book club kit -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
