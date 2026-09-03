#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, print-ready Zhuyin parent-teacher handoff kit."""
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
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
SLUG = "zhuyin-parent-teacher-handoff-kit"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phoneticWrite.jsp?la=0"
MOE_SITE_INFO = "https://stroke-order.learningweb.moe.edu.tw/page.jsp?ID=28&la=1"
OCAC_STARTER = "https://taiwancenter.taiwan-world.net/material/basic/content/54"

WEEKS = {
    "en": (
        {
            "number": "Week 1",
            "title": "Match one shape and sound",
            "teacher": "Choose one to three symbols already modeled in class. Write only those items on the handoff card.",
            "home": "Let the child choose one item, hear it once, then point, trace in the air or find its card.",
            "return": "Circle what the child chose to do. Do not mark correct/incorrect or add a score.",
        },
        {
            "number": "Week 2",
            "title": "Notice one tone contrast",
            "teacher": "Choose one familiar syllable and two contrasting tones from the current lesson.",
            "home": "Model both naturally with a hand motion. Listening, copying the motion or echoing all count.",
            "return": "Note only which form felt comfortable and which one the teacher may model again.",
        },
        {
            "number": "Week 3",
            "title": "Join a short blend",
            "teacher": "Choose one blend the class has already heard; avoid sending a new rule home.",
            "home": "Slide the two symbol cards together slowly, then say one familiar word containing the blend.",
            "return": "Circle listened, pointed, blended or asked to stop. Every option is useful information.",
        },
        {
            "number": "Week 4",
            "title": "Use Zhuyin in real reading",
            "teacher": "Choose one short annotated word or phrase from an authorized class or family resource.",
            "home": "Read it together for meaning. The child may point, act, draw or say part of the phrase.",
            "return": "Write one neutral next step, such as “model once more” or “ready for another example.”",
        },
    ),
    "zh-Hant": (
        {
            "number": "第 1 週",
            "title": "連結一個形與音",
            "teacher": "從課堂已示範的內容選一至三個符號，只把這些項目寫在交接卡上。",
            "home": "讓孩子選一個，先聽一次，再指一指、空中描寫或找出對應卡片。",
            "return": "只圈出孩子願意做的互動，不標對錯，也不給分。",
        },
        {
            "number": "第 2 週",
            "title": "注意一組聲調對比",
            "teacher": "從本週課程選一個熟悉音節與兩個對比聲調。",
            "home": "搭配手勢自然示範；孩子聆聽、模仿手勢或跟念，都算參與。",
            "return": "只記哪個形式較自在，以及哪一個可請老師下次再示範。",
        },
        {
            "number": "第 3 週",
            "title": "完成一組短拼讀",
            "teacher": "選一組課堂已經聽過的拼讀，不把新規則當作回家作業。",
            "home": "慢慢把兩張符號卡滑在一起，再說一個含有這組音的熟悉詞語。",
            "return": "圈出聆聽、指認、拼讀或想停止；每種反應都是有用資訊。",
        },
        {
            "number": "第 4 週",
            "title": "把注音用進真實閱讀",
            "teacher": "從合法授權的課堂或家庭資源選一個短詞或短句。",
            "home": "一起讀懂意思；孩子可以指圖、做動作、畫圖或只說部分詞語。",
            "return": "寫一個中性的下一步，例如「再示範一次」或「可換另一個例子」。",
        },
    ),
}

COPY = {
    "en": {
        "lang": "en",
        "title": "Free Zhuyin Parent-Teacher Handoff Kit",
        "description": (
            "A bilingual, print-ready school-to-home Zhuyin handoff kit with a "
            "teacher cue card, ten-minute family routine and non-scored return slip."
        ),
        "eyebrow": "Free weekend-school resource · no login",
        "lead": (
            "Keep the teacher and family on the same tiny weekly focus without an "
            "account, child name, online log or score."
        ),
        "badges": (
            "English + Traditional Chinese",
            "Print-ready and CC BY 4.0",
            "No child data submitted or saved",
        ),
        "start": "Open the printable handoff",
        "language": "繁體中文",
        "boundary_title": "A handoff, not homework grading",
        "boundary_text": (
            "The teacher chooses one to three items already taught. The family uses "
            "one gentle ten-minute routine and returns observations, not a score. "
            "No child name, diagnosis, behavior label or contact detail is needed."
        ),
        "rhythm": "Four-week handoff rhythm",
        "rhythm_intro": (
            "Use the weeks in order or repeat the one that matches the current class. "
            "The teacher remains responsible for selecting the actual symbols, words and pace."
        ),
        "teacher": "Teacher sends",
        "family": "Family tries",
        "return": "Family returns",
        "print": "Print the handoff kit",
        "share": "Share tool",
        "shared": "Tool link copied.",
        "share_title": "Free Zhuyin parent-teacher handoff kit",
        "kit": "Printable teacher-to-family handoff",
        "kit_intro": (
            "Print one copy for the teacher and one for the family. All blank lines "
            "stay on paper; this page has no form and receives nothing."
        ),
        "teacher_card": "Teacher cue card",
        "teacher_fields": (
            (
                "This week's focus",
                "○ symbol-sound  ○ tone  ○ blending  ○ writing  ○ annotated reading",
            ),
            ("Practice only these 1–3 items", "________________________________________"),
            (
                "Model once",
                "Hear → point / trace / act → use in one familiar word",
            ),
            (
                "Gentle stop",
                "Stop at ten minutes or sooner whenever the child wants to stop.",
            ),
        ),
        "family_card": "Ten-minute family card",
        "family_steps": (
            "1 min · Let the child choose one teacher-selected item.",
            "2 min · Adult models once; no “What is this?” quiz.",
            "3 min · Point, match, air-trace or use a hand motion.",
            "3 min · Put the sound or word into a real family phrase.",
            "1 min · Name one effort you noticed and stop while the mood is positive.",
        ),
        "return_slip": "Non-scored return slip",
        "return_intro": (
            "This slip records participation, not correctness. Circle only what "
            "happened; blank items are not failures, and this is not a mastery check."
        ),
        "return_items": (
            "○ chose an item",
            "○ listened",
            "○ pointed or matched",
            "○ traced or moved",
            "○ joined a sound or word",
            "○ asked to stop",
        ),
        "next": "One neutral next step: ________________________________________",
        "question": "Optional family question for the teacher: __________________________",
        "privacy": "Private by design",
        "privacy_text": (
            "There is no account, child-name field, class field, form submission, "
            "camera, microphone, upload, analytics input, local storage or saved "
            "profile. The printable slip works without a name. Schools and families "
            "keep any handwriting under their own privacy policy."
        ),
        "evidence": "What this kit can and cannot establish",
        "evidence_text": (
            "This original organizational template has not been evaluated in a "
            "trial. The linked Ministry of Education and OCAC materials establish "
            "standard notation, stroke order and longer-form teaching resources; "
            "they do not evaluate or endorse this kit. This page cannot diagnose a "
            "child, prove Zhuyin gains, validate the four-week sequence or promise "
            "that a ten-minute routine will improve learning."
        ),
        "sources": "Official references",
        "source_items": (
            ("Taiwan Ministry of Education Bopomofo Handbook", MOE_HANDBOOK),
            ("Taiwan Ministry of Education Bopomofo Practice Book", MOE_PRACTICE),
            ("MOE Stroke Order Learning Program information", MOE_SITE_INFO),
            ("OCAC Let's Learn Mandarin Starter (Bopomofo)", OCAC_STARTER),
        ),
        "reuse": "Print, adapt and share",
        "reuse_text": (
            "Weekend schools, teachers and families may print or adapt this original "
            "kit under CC BY 4.0 with credit to iOS App Guide and a link to this page. "
            "The license does not cover linked government materials."
        ),
        "app_title": "Optional practice after the handoff",
        "app_text": (
            "The kit works without an app. If the teacher selects symbols, tones or "
            "blends for extra practice, Lumi Bopomofo covers all 37 symbols with "
            "listening, tracing, tone and blending activities. It is free to download "
            "with an optional one-time unlock, has no ads and requires no account."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "related": "Related free resources",
        "related_items": (
            (
                "Library Zhuyin family storytime kit",
                f"{SITE}/tools/zhuyin-library-storytime-kit.html",
            ),
            (
                "Five-day heritage-school lesson plan",
                f"{SITE}/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            ),
            ("3-minute Zhuyin skills check", f"{SITE}/tools/zhuyin-readiness-check.html"),
            (
                "Family Zhuyin picture-book club kit",
                f"{SITE}/tools/zhuyin-family-picture-book-club-kit.html",
            ),
            (
                "Grandparent Zhuyin video-call kit",
                f"{SITE}/tools/zhuyin-grandparent-video-call-kit.html",
            ),
        ),
        "faq": "Teacher and family FAQ",
        "faq_items": (
            (
                "Does a teacher or family need an account?",
                "No. Open or print the page directly. Nothing is submitted to the site.",
            ),
            (
                "Does the return slip assess Zhuyin mastery?",
                "No. It records participation only and cannot measure mastery, readiness or a learning difficulty.",
            ),
            (
                "Must a family use Lumi Bopomofo?",
                "No. Paper, teacher modeling and an authorized class resource are enough to use the complete kit.",
            ),
            (
                "Should a family write the child's name?",
                "No name is needed. Follow the school's own privacy policy for any optional handwriting kept offline.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": (
            "Independent school-to-home resource; not an official curriculum, "
            "assessment, clinical tool or promise of learning results."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "注音家庭—教師交接包｜免費英繁雙語列印工具",
        "description": "給週末中文學校與家庭的英繁雙語注音交接包，含教師提示卡、10 分鐘家庭流程與不計分回條；免登入、不儲存孩子資料。",
        "eyebrow": "免費週末中文學校資源 · 免登入",
        "lead": "讓老師與家庭每週只對準一個小焦點；不需要帳號、孩子姓名、線上紀錄或分數。",
        "badges": ("英文＋繁體中文", "可列印 · CC BY 4.0", "不送出或儲存孩子資料"),
        "start": "開啟可列印交接包",
        "language": "English",
        "boundary_title": "這是交接，不是回家評分",
        "boundary_text": "老師從課堂已教內容選一至三項；家庭用一套溫和的 10 分鐘流程，再回傳觀察而非分數。不需要孩子姓名、診斷、行為標籤或聯絡資料。",
        "rhythm": "四週交接節奏",
        "rhythm_intro": "可以依序使用，也可重複最符合本週課程的一週；實際符號、詞語與速度仍由老師決定。",
        "teacher": "老師交接",
        "family": "家庭練習",
        "return": "家庭回傳",
        "print": "列印交接包",
        "share": "分享工具",
        "shared": "已複製工具連結。",
        "share_title": "免費注音家庭—教師交接包",
        "kit": "可列印的教師—家庭交接單",
        "kit_intro": "老師與家庭各列印一份；所有空白欄位只留在紙上，本頁沒有表單，也不接收任何內容。",
        "teacher_card": "教師提示卡",
        "teacher_fields": (
            ("本週焦點", "○ 形音連結　○ 聲調　○ 拼讀　○ 書寫　○ 注音閱讀"),
            ("只練這 1–3 項", "________________________________________"),
            ("示範一次", "先聽 → 指／描／做動作 → 放進一個熟悉詞語"),
            ("溫和停止", "最多 10 分鐘；孩子想停止時就提早結束。"),
        ),
        "family_card": "10 分鐘家庭練習卡",
        "family_steps": (
            "1 分鐘｜讓孩子從老師選的內容中挑一項。",
            "2 分鐘｜大人只示範一次，不用「這是什麼？」考孩子。",
            "3 分鐘｜指認、配對、空中描寫或搭配手勢。",
            "3 分鐘｜把聲音或詞語放進真實家庭句子。",
            "1 分鐘｜說出一個你注意到的努力，在氣氛還好時收尾。",
        ),
        "return_slip": "不計分家庭回條",
        "return_intro": "只圈出實際發生的互動；空白不是失敗，這張回條也不是精熟度檢核。",
        "return_items": (
            "○ 自己選一項",
            "○ 聆聽",
            "○ 指認或配對",
            "○ 描寫或做動作",
            "○ 加入一個音或詞",
            "○ 表示想停止",
        ),
        "next": "一個中性的下一步：________________________________________",
        "question": "家庭想問老師的一個問題（選填）：__________________________",
        "privacy": "從設計上保護隱私",
        "privacy_text": "沒有帳號、孩子姓名欄、班級欄、表單送出、相機、麥克風、上傳、分析輸入、local storage 或孩子檔案。紙本回條不寫姓名也能使用；任何手寫內容由學校與家庭依自己的隱私規範保管。",
        "evidence": "這套工具能證明什麼？不能證明什麼？",
        "evidence_text": "這是原創的組織模板，尚未經試驗評估。連結的教育部與僑委會資料提供標準符號、筆順與長期教材，但沒有評估或背書本工具。本頁不能診斷孩子、證明注音進步、驗證四週順序，也不承諾 10 分鐘流程能改善學習。",
        "sources": "官方參考",
        "source_items": (
            ("台灣教育部《國語注音符號手冊》", MOE_HANDBOOK),
            ("台灣教育部《注音練習簿》", MOE_PRACTICE),
            ("教育部常用國字標準字體筆順學習網說明", MOE_SITE_INFO),
            ("僑委會《學華語向前走》入門冊（注音符號版）", OCAC_STARTER),
        ),
        "reuse": "可列印、改編與分享",
        "reuse_text": "週末中文學校、老師與家庭可依 CC BY 4.0 列印或改編本原創工具；請標註 iOS App Guide 並連回本頁。此授權不涵蓋外部政府教材。",
        "app_title": "完成交接後的選用練習",
        "app_text": "不使用 App 也能完整使用交接包。如果老師指定符號、聲調或拼讀作為延伸練習，Lumi 注音星球提供全部 37 個符號的聽音、描寫、聲調與拼讀活動。可免費下載，另可選擇一次性一次購買解鎖；無廣告、免帳號。",
        "app_cta": "試用 Lumi 注音星球",
        "related": "相關免費資源",
        "related_items": (
            (
                "圖書館注音親子故事時間包",
                f"{SITE}/zh-Hant/tools/zhuyin-library-storytime-kit.html",
            ),
            (
                "海外中文學校五日教案",
                f"{SITE}/zh-Hant/guides/zhuyin-5-day-lesson-plan-heritage-school.html",
            ),
            (
                "3 分鐘注音學習檢核",
                f"{SITE}/zh-Hant/tools/zhuyin-readiness-check.html",
            ),
            (
                "家庭注音繪本四週共讀包",
                f"{SITE}/zh-Hant/tools/zhuyin-family-picture-book-club-kit.html",
            ),
            (
                "祖孫視訊注音遊戲包",
                f"{SITE}/zh-Hant/tools/zhuyin-grandparent-video-call-kit.html",
            ),
        ),
        "faq": "老師與家庭常見問題",
        "faq_items": (
            ("老師或家庭需要帳號嗎？", "不用。直接開啟或列印頁面；不會把任何內容送到網站。"),
            ("家庭回條能評量注音精熟度嗎？", "不能。它只記錄參與方式，無法測量精熟度、入學準備或學習困難。"),
            ("家庭一定要使用 Lumi 注音星球嗎？", "不用。紙筆、老師示範與合法授權的課堂資源，就能完整使用交接包。"),
            ("家庭要寫孩子姓名嗎？", "不需要姓名；任何離線手寫內容請依學校自己的隱私規範處理。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立製作的家庭—學校資源；不是官方課程、評量、臨床工具或學習成效保證。",
    },
}

STYLE = """
:root{--ink:#24324a;--muted:#69758a;--paper:#fffef9;--line:#dedbd0;--blue:#315c91;--blue2:#557db0;--sage:#397a68;--gold:#b9852f;--soft:#eef5fb}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#f7fbff 0,#f8fbf5 48%,#fffaf1 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}a{color:#315c91}.wrap{width:min(1060px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:4;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850}.links{display:flex;gap:15px}.hero{padding:58px 0 30px}.eyebrow{color:var(--blue);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:940px;margin:.18em 0;font-size:clamp(2rem,5.8vw,4rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:820px;color:var(--muted);font-size:clamp(1.08rem,2.5vw,1.27rem)}.badges,.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.badge{padding:8px 12px;border:1px solid #cfdae8;border-radius:999px;background:#fff;color:#405b7c;font-weight:800;white-space:nowrap}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #315c9128}.button.secondary{background:#fff;color:#315c91!important;border:1px solid #c7d4e5;box-shadow:none}.button:focus-visible{outline:3px solid #e2b858;outline-offset:3px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{grid-column:span 12;padding:23px;background:var(--paper);border:1px solid var(--line);border-radius:23px;box-shadow:0 10px 32px #34281a12}.half{grid-column:span 6}.third{grid-column:span 4}h2{margin:1.5em 0 .58em;font-size:clamp(1.45rem,3vw,2rem);line-height:1.18}h3{line-height:1.25}.muted{color:var(--muted)}.notice{padding:17px 19px;border-left:5px solid var(--gold);border-radius:14px;background:#fff7dc}.rhythm{margin-bottom:28px}.week-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.week{padding:21px;border:1px solid #d7e0e9;border-radius:22px;background:linear-gradient(150deg,#f7fbff,#fff)}.week-no{color:var(--blue);font-weight:900;white-space:nowrap}.week h3{margin:.15em 0;font-size:1.3rem}.phase{padding:10px 0;border-top:1px solid var(--line)}.phase b{display:block;color:var(--sage);white-space:nowrap}.phase p{margin:.2em 0}.kit{padding:clamp(22px,4vw,34px);background:#fff;border:1px solid #d7d9d4;border-radius:28px;box-shadow:0 20px 55px #23354b15}.kit-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap}.kit-head h2{margin:.1em 0}.print-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:22px}.sheet{padding:20px;border:1px solid #ccd8e4;border-radius:19px;background:#fff}.sheet.full{grid-column:1/-1}.field{padding:11px 0;border-bottom:1px dashed #b8bec8}.field:last-child{border-bottom:0}.field b{display:block;color:var(--blue);white-space:nowrap}.family-step{padding:8px 0;border-bottom:1px solid var(--line)}.return-options{display:flex;flex-wrap:wrap;gap:8px 18px}.return-options span{white-space:nowrap}.line{margin-top:18px;padding:9px 0;border-bottom:1px solid #7f8791}.source-list a{overflow-wrap:anywhere}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--sage);font-weight:800}
@media(max-width:760px){.half,.third{grid-column:span 12}.week-grid,.print-grid{grid-template-columns:1fr}.links a:first-child{display:none}.hero{padding-top:38px}.return-options{display:grid;grid-template-columns:1fr 1fr}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.boundary,.rhythm,.extras,.app-card,.related,.faq,.evidence-section,.footer,.actions{display:none!important}body{background:#fff;font-size:10pt}.wrap{width:100%}.kit,.sheet,.card{border:0;box-shadow:none;padding:0}.kit-head{margin-bottom:5mm}.print-grid{grid-template-columns:1fr 1fr;gap:8mm}.sheet{break-inside:avoid}.sheet.full{grid-column:1/-1;border-top:1px solid #999;padding-top:4mm}.field{padding:2.5mm 0}.family-step{padding:2mm 0}@page{size:A4;margin:11mm}}
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
    app_url = appstore_url("lumibopomofo", f"iag_handoff_{locale.lower()}")
    weeks = "".join(
        '<article class="week">'
        f'<div class="week-no">{html.escape(week["number"])}</div>'
        f'<h3>{html.escape(week["title"])}</h3>'
        f'<div class="phase"><b>{html.escape(t["teacher"])}</b><p>{html.escape(week["teacher"])}</p></div>'
        f'<div class="phase"><b>{html.escape(t["family"])}</b><p>{html.escape(week["home"])}</p></div>'
        f'<div class="phase"><b>{html.escape(t["return"])}</b><p>{html.escape(week["return"])}</p></div>'
        "</article>"
        for week in WEEKS[locale]
    )
    teacher_fields = "".join(
        f'<div class="field"><b>{html.escape(label)}</b><span>{html.escape(value)}</span></div>'
        for label, value in t["teacher_fields"]
    )
    family_steps = "".join(
        f'<div class="family-step">{html.escape(step)}</div>'
        for step in t["family_steps"]
    )
    return_items = "".join(
        f"<span>{html.escape(item)}</span>" for item in t["return_items"]
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
            "learningResourceType": "Parent-teacher handoff kit",
            "educationalUse": "School-to-home communication",
            "educationalLevel": "Beginner",
            "typicalAgeRange": "4-8",
            "timeRequired": "P4W",
            "license": LICENSE,
            "teaches": [
                "Coordinating Zhuyin practice between school and home",
                "Using non-scored family observations",
                "Selecting a small weekly Bopomofo focus",
            ],
            "citation": [MOE_HANDBOOK, MOE_PRACTICE, MOE_SITE_INFO, OCAC_STARTER],
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
                    "text": f'{week["teacher"]} {week["home"]} {week["return"]}',
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
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#handoff">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div></section>
<section class="wrap boundary"><article class="card"><h2>{html.escape(t["boundary_title"])}</h2><p class="notice">{html.escape(t["boundary_text"])}</p></article></section>
<section class="wrap rhythm"><h2>{html.escape(t["rhythm"])}</h2><p class="muted">{html.escape(t["rhythm_intro"])}</p><div class="week-grid">{weeks}</div></section>
<section class="wrap kit" id="handoff"><div class="kit-head"><div><h2>{html.escape(t["kit"])}</h2><p class="muted">{html.escape(t["kit_intro"])}</p></div><div class="actions"><button class="button secondary" id="print-kit" type="button">{html.escape(t["print"])}</button><button class="button" id="share-kit" type="button">{html.escape(t["share"])}</button></div></div><div class="print-grid"><article class="sheet"><h3>{html.escape(t["teacher_card"])}</h3>{teacher_fields}</article><article class="sheet"><h3>{html.escape(t["family_card"])}</h3>{family_steps}</article><article class="sheet full"><h3>{html.escape(t["return_slip"])}</h3><p>{html.escape(t["return_intro"])}</p><div class="return-options">{return_items}</div><div class="line">{html.escape(t["next"])}</div><div class="line">{html.escape(t["question"])}</div></article></div><div class="share-status" id="share-status" aria-live="polite"></div></section>
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
        f'<a href="{target}">Zhuyin Parent-Teacher Handoff Kit</a></h2>'
        "<p>A bilingual school-to-home practice card with no scores or logins.</p>"
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
        r'zhuyin-family-picture-book-club-kit\.html">.*?</article>',
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
        print(f"parent-teacher handoff kit -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
