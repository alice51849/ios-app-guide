#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, print-ready 14-day Grade 1 Zhuyin warm-up calendar."""
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
SLUG = "zhuyin-grade1-14-day-summer-calendar"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/"
    "html_ch/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=0"

DAYS = {
    "en": (
        {
            "day": "Day 1",
            "focus": "Choose a gentle starting lane",
            "base": "If Zhuyin is completely new, open the official chart and choose only two or three symbols. The adult models once; listening counts.",
            "stretch": "If the child has seen Zhuyin before, use the free 3-minute observation guide once to choose a lane—not to produce a score.",
        },
        {
            "day": "Day 2",
            "focus": "Hear, then point",
            "base": "Say or play three selected symbol sounds one at a time. The child may point, look, copy a gesture or simply listen.",
            "stretch": "Mix four to six familiar symbols and let the child choose which one the adult models next.",
        },
        {
            "day": "Day 3",
            "focus": "Match shapes without speed",
            "base": "Write two copies of each selected symbol on scrap paper. Turn them face up and pair matching shapes together.",
            "stretch": "Add one similar-looking pair and talk about one visible difference without calling either answer wrong.",
        },
        {
            "day": "Day 4",
            "focus": "Trace one official form",
            "base": "Check the Ministry of Education stroke reference. Model one or two symbols in the air; the child may air-trace, finger-trace or watch.",
            "stretch": "Trace the same familiar symbols once on paper, stopping before neatness becomes the goal.",
        },
        {
            "day": "Day 5",
            "focus": "Connect one sound to family life",
            "base": "Choose one familiar spoken Mandarin word and use an authorized reference to notice one Zhuyin symbol in it.",
            "stretch": "Find a second family word with the same selected sound; conversation matters more than recall.",
        },
        {
            "day": "Day 6",
            "focus": "Move with one tone contrast",
            "base": "Use one familiar spoken syllable. The adult models two tones with a hand path; the child may move, listen or imitate.",
            "stretch": "Try the same base syllable with up to four tones only if the child remains comfortable.",
        },
        {
            "day": "Day 7",
            "focus": "Repeat by child choice",
            "base": "Offer the activities from Days 2–6 and let the child choose one. Add no new symbol today.",
            "stretch": "Let the child become the caller, card chooser or movement leader without correcting publicly.",
        },
        {
            "day": "Day 8",
            "focus": "Meet a second small set",
            "base": "Choose two or three different symbols from the official chart. Model, point and move exactly as on Day 2.",
            "stretch": "Mix the new set with two familiar symbols and sort them into ‘seen before’ and ‘new today.’",
        },
        {
            "day": "Day 9",
            "focus": "Notice a look-alike pair",
            "base": "Place one similar-looking pair side by side. Name or trace the feature that makes their shapes different.",
            "stretch": "Add each symbol to a tiny matching or pointing game; avoid timed rounds.",
        },
        {
            "day": "Day 10",
            "focus": "Return to stroke order",
            "base": "Use the official stroke reference for one selected symbol. Model slowly, then invite one air or paper trace.",
            "stretch": "Compare the child’s own two attempts only to notice movement—not to grade neatness.",
        },
        {
            "day": "Day 11",
            "focus": "Listen to a two-part blend",
            "base": "With two familiar symbols from an authorized model, say the parts slowly and then join them. The child may only listen.",
            "stretch": "If ready, let the child slide two paper cards together while joining the sounds without a timer.",
        },
        {
            "day": "Day 12",
            "focus": "Add a tone only when ready",
            "base": "Reuse yesterday’s familiar base syllable and model one tone with a hand path. Keep symbol blending and tone listening separate.",
            "stretch": "Compare two tones on the same syllable; stop if the two tasks begin to overload attention.",
        },
        {
            "day": "Day 13",
            "focus": "Notice Zhuyin in real reading",
            "base": "Use one legally owned, borrowed or authorized annotated book. Let the child choose one page and notice one familiar symbol.",
            "stretch": "Read for meaning, then point to one short annotation only if the child wants to revisit it.",
        },
        {
            "day": "Day 14",
            "focus": "Let the child lead the ending",
            "base": "The child chooses a favorite activity from the calendar. Repeat it and end while the interaction is still comfortable.",
            "stretch": "Choose one neutral next step—repeat, pause, ask the school or explore another small set—without assigning a level.",
        },
    ),
    "zh-Hant": (
        {
            "day": "第 1 天",
            "focus": "選一條溫和起點",
            "base": "完全沒接觸過注音時，打開教育部官方符號表，只選兩至三個符號。大人示範一次，孩子只聽也算參與。",
            "stretch": "孩子以前看過注音時，可使用一次免費 3 分鐘觀察指南，只用來選起點，不產生分數。",
        },
        {
            "day": "第 2 天",
            "focus": "先聽，再指",
            "base": "一次說出或播放一個選定符號的聲音，共三個。孩子可以指、看、模仿手勢或只聽。",
            "stretch": "混合四至六個熟悉符號，讓孩子選下一個由大人示範的符號。",
        },
        {
            "day": "第 3 天",
            "focus": "不計時配對形狀",
            "base": "在廢紙上把每個選定符號各寫兩張，全部翻開，將相同形狀配在一起。",
            "stretch": "加入一組外形相近的符號，只談一個看得見的差異，不說哪個答案錯了。",
        },
        {
            "day": "第 4 天",
            "focus": "描一個官方字形",
            "base": "查看教育部官方筆順，示範一至兩個符號的空中筆畫；孩子可空寫、手指描或觀看。",
            "stretch": "把同一個熟悉符號在紙上描一次；整齊還沒變成目標前就停止。",
        },
        {
            "day": "第 5 天",
            "focus": "把一個聲音連到家庭生活",
            "base": "選一個熟悉的華語口語詞，搭配合法授權的參考資料，注意其中一個注音。",
            "stretch": "再找一個含相同聲音的家庭詞語；對話比記住答案重要。",
        },
        {
            "day": "第 6 天",
            "focus": "用動作感受一組聲調",
            "base": "使用一個熟悉的口語音節，大人用手勢路徑示範兩個聲調；孩子可動作、聆聽或模仿。",
            "stretch": "只有孩子仍感到自在時，才把同一個音節試到最多四個聲調。",
        },
        {
            "day": "第 7 天",
            "focus": "由孩子選擇重複",
            "base": "把第 2 至 6 天的活動列出來，讓孩子選一個；今天不增加新符號。",
            "stretch": "讓孩子擔任出題、選卡或動作帶領者，不公開糾正。",
        },
        {
            "day": "第 8 天",
            "focus": "認識第二小組符號",
            "base": "從官方符號表另選兩至三個符號，像第 2 天一樣示範、指認與動作。",
            "stretch": "把新符號與兩個熟悉符號混合，分成「以前看過」與「今天新看見」。",
        },
        {
            "day": "第 9 天",
            "focus": "注意一組相近字形",
            "base": "把一組外形相近的符號並排，說出或描出讓兩個形狀不同的特徵。",
            "stretch": "把兩個符號放進小型配對或指認遊戲，不做計時回合。",
        },
        {
            "day": "第 10 天",
            "focus": "再次查看筆順",
            "base": "使用官方筆順參考一個選定符號；慢慢示範，再邀請孩子空寫或紙上描一次。",
            "stretch": "只比較孩子自己的兩次動作來觀察路徑，不評分整齊度。",
        },
        {
            "day": "第 11 天",
            "focus": "聽一組二拼",
            "base": "依合法授權的示範，使用兩個熟悉符號，先慢慢分開說，再連起來；孩子只聽也可以。",
            "stretch": "準備好時，讓孩子把兩張紙卡滑近並連音，不使用計時器。",
        },
        {
            "day": "第 12 天",
            "focus": "準備好才加聲調",
            "base": "沿用昨天熟悉的基本音節，以手勢路徑示範一個聲調；先把拼讀與聽聲調分開。",
            "stretch": "在同一音節比較兩個聲調；兩項任務開始讓注意力過載就停止。",
        },
        {
            "day": "第 13 天",
            "focus": "在真實閱讀中看見注音",
            "base": "使用家中合法購買、借閱或授權取得的注音讀物，讓孩子選一頁，只注意一個熟悉符號。",
            "stretch": "以理解內容為主；孩子想再看時，才指一個短短的注音標示。",
        },
        {
            "day": "第 14 天",
            "focus": "讓孩子帶領收尾",
            "base": "孩子從日曆選一個最喜歡的活動，重複一次，在互動仍自在時結束。",
            "stretch": "選一個中性的下一步：重複、休息、詢問學校或再探索一小組，不替孩子分級。",
        },
    ),
}

COPY = {
    "en": {
        "title": "Free 14-Day Grade 1 Zhuyin Summer Warm-Up",
        "description": (
            "A bilingual, print-ready 14-day Zhuyin summer warm-up with 8–10 "
            "minute family activities, no scores, no login and no readiness claim."
        ),
        "eyebrow": "Free summer family calendar · no login",
        "lead": (
            "Build familiarity before school without turning summer into a test. "
            "Choose a starting lane, keep each day under ten minutes and stop early when needed."
        ),
        "badges": (
            "14 days · 8–10 minutes",
            "English + Traditional Chinese",
            "No score, diagnosis or saved child data",
        ),
        "start": "Open the 14-day calendar",
        "language": "繁體中文",
        "boundary": "Warm-up, not an entrance requirement",
        "boundary_text": (
            "This optional calendar does not set a Grade 1 prerequisite. It does not "
            "teach or assess all 37 symbols, assign a level or predict school performance. "
            "Schools differ; ask the child’s school about its actual first-term plan."
        ),
        "lanes": "Choose one starting lane",
        "lane_intro": (
            "Use the lightest lane that fits today. Move between lanes freely; no child "
            "needs to complete a lane or catch up to the calendar."
        ),
        "lane_items": (
            (
                "Completely new",
                "Use two or three symbols. The adult models; listening, watching or stopping all count.",
            ),
            (
                "Recognises some",
                "Use four to six symbols the child has already seen for pointing, matching and movement.",
            ),
            (
                "Ready to combine",
                "Use two familiar two-part blends without speed, ranking or handwriting pressure.",
            ),
        ),
        "routine": "The same 8–10 minute rhythm",
        "routine_items": (
            "1 minute · child chooses the lane or material",
            "2 minutes · adult models once; do not quiz first",
            "3 minutes · point, match, move or listen",
            "2 minutes · connect to paper, a family word or an authorized book",
            "1–2 minutes · name one effort and stop",
        ),
        "calendar": "Fourteen-day printable calendar",
        "base_label": "Gentle route",
        "stretch_label": "Only if already comfortable",
        "print": "Print the calendar",
        "share": "Share tool",
        "shared": "Tool link copied.",
        "share_title": "Free 14-day Grade 1 Zhuyin summer warm-up",
        "privacy": "No completion tracking",
        "privacy_text": (
            "There is no child-name field, date field, checkbox tracker, account, "
            "form submission, camera, microphone, upload, analytics input, local "
            "storage or saved profile. The page receives no answers or activity history."
        ),
        "evidence": "What the official sources do—and do not—show",
        "evidence_text": (
            "Taiwan Ministry of Education references establish standard Zhuyin forms, "
            "notation and stroke order. They do not prescribe or endorse this calendar. "
            "This original 14-day sequence has not been evaluated in a study and cannot "
            "show that a child is ready for school, will learn faster or will earn a "
            "particular result. Fourteen days is a bounded family routine, not a mastery timeline."
        ),
        "sources": "Official references",
        "source_items": (
            ("Taiwan Ministry of Education Bopomofo Handbook", MOE_HANDBOOK),
            ("Taiwan Ministry of Education Zhuyin Stroke Order", MOE_PRACTICE),
        ),
        "reuse": "Reuse the original calendar",
        "reuse_text": (
            "Families, libraries and heritage schools may print or adapt this original "
            "calendar under CC BY 4.0 with credit to iOS App Guide and a link to this page. "
            "The license does not cover Ministry materials, books or other external sources."
        ),
        "app_title": "Optional practice inside a chosen day",
        "app_text": (
            "The complete calendar works with paper, official references and an authorized "
            "book. If a family wants guided listening, tracing, tone or blending practice, "
            "Lumi Bopomofo covers all 37 symbols. It is free to download with an optional "
            "one-time lifetime unlock, has no ads and requires no account."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "related": "Related free resources",
        "related_items": (
            ("3-minute Zhuyin observation guide", f"{SITE}/tools/zhuyin-readiness-check.html"),
            ("37-symbol Bopomofo chart", f"{SITE}/tools/zhuyin-bopomofo-chart.html"),
            ("Printable Zhuyin practice sheet", f"{SITE}/tools/zhuyin-practice-sheet.html"),
            (
                "Family Zhuyin picture-book club kit",
                f"{SITE}/tools/zhuyin-family-picture-book-club-kit.html",
            ),
            (
                "Parent-teacher Zhuyin handoff kit",
                f"{SITE}/tools/zhuyin-parent-teacher-handoff-kit.html",
            ),
        ),
        "faq": "Parent FAQ",
        "faq_items": (
            (
                "Must a child know Zhuyin before Grade 1?",
                "This calendar sets no entrance requirement. Ask the child’s school about its teaching plan and use this only as an optional familiarity routine.",
            ),
            (
                "Will fourteen days teach all 37 symbols?",
                "No. It samples listening, shape, stroke, tone, blending and reading interactions. Repeat, pause or continue later without assigning a level.",
            ),
            (
                "What if the child uses little spoken Mandarin?",
                "Treat oral language as a separate need. Pair Zhuyin with conversation and fluent speech; do not interpret slow symbol work as a diagnosis.",
            ),
            (
                "Is an app required?",
                "No. Paper, official references, adult modeling and a legally available annotated book are enough for the complete calendar.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": (
            "Independent family resource; not an official curriculum, entrance "
            "requirement, assessment, diagnosis or promise of school results."
        ),
    },
    "zh-Hant": {
        "title": "小一入學前 14 天注音暖身日曆｜免費可列印",
        "description": "英繁雙語、可列印的 14 天注音暑假暖身日曆：每天 8–10 分鐘、免登入、不評分、不診斷，也不把注音設為入學門檻。",
        "eyebrow": "免費暑假家庭日曆 · 免登入",
        "lead": "入學前先降低陌生感，不把暑假變成測驗。選一條適合今天的起點，每天不超過 10 分鐘，需要時提早停止。",
        "badges": ("14 天 · 每天 8–10 分鐘", "英文＋繁體中文", "不評分、不診斷、不儲存孩子資料"),
        "start": "開啟 14 天日曆",
        "language": "English",
        "boundary": "只是暖身，不是入學門檻",
        "boundary_text": "這份選用日曆不替小一設定先備條件；它不教完或評量全部 37 個符號、不替孩子分級，也不預測學校表現。各校安排不同，請向孩子的學校確認實際開學教學計畫。",
        "lanes": "選一條起點",
        "lane_intro": "今天適合多輕就從多輕開始，可自由更換路線；孩子不需要完成某條路線，也不需要追趕日曆。",
        "lane_items": (
            ("完全沒接觸過", "只用兩至三個符號。大人示範；聆聽、觀看或停止都算參與。"),
            ("已認得一些", "使用孩子看過的四至六個符號，進行指認、配對與動作。"),
            ("準備開始組合", "使用兩組熟悉的二拼，不計速度、不排名，也不要求書寫整齊。"),
        ),
        "routine": "每天相同的 8–10 分鐘節奏",
        "routine_items": (
            "1 分鐘 · 孩子選路線或材料",
            "2 分鐘 · 大人示範一次，不先考問",
            "3 分鐘 · 指認、配對、動作或聆聽",
            "2 分鐘 · 連到紙張、家庭詞語或合法取得的書",
            "1–2 分鐘 · 說出一項努力並停止",
        ),
        "calendar": "14 天可列印日曆",
        "base_label": "溫和路線",
        "stretch_label": "已經自在才延伸",
        "print": "列印日曆",
        "share": "分享工具",
        "shared": "已複製工具連結。",
        "share_title": "免費小一入學前 14 天注音暖身日曆",
        "privacy": "沒有完成度追蹤",
        "privacy_text": "沒有孩子姓名欄、日期欄、打卡追蹤、帳號、表單送出、相機、麥克風、上傳、分析輸入、local storage 或儲存檔案。本頁不接收答案或活動紀錄。",
        "evidence": "官方來源能說明什麼，不能說明什麼",
        "evidence_text": "台灣教育部資料提供標準注音字形、標示方式與筆順；並未制定或背書本日曆。這份原創 14 天流程尚未經研究評估，不能判定孩子是否準備好上學、能否學得更快或取得特定成果。14 天只是有邊界的家庭流程，不是精熟時程。",
        "sources": "官方參考",
        "source_items": (
            ("台灣教育部《國語注音符號手冊》", MOE_HANDBOOK),
            ("台灣教育部注音符號筆順", MOE_PRACTICE),
        ),
        "reuse": "自由使用原創日曆",
        "reuse_text": "家庭、圖書館與海外中文學校可依 CC BY 4.0 列印或改編本原創日曆；請標註 iOS App Guide 並連回本頁。此授權不涵蓋教育部資料、書籍或其他外部來源。",
        "app_title": "選定活動中的選用練習",
        "app_text": "只用紙張、官方參考與合法取得的書，就能完整使用日曆。家庭若想在某一天加入有引導的聽音、描寫、聲調或拼讀練習，Lumi 注音星球涵蓋全部 37 個符號；可免費下載，另可選擇一次性永久解鎖，無廣告、免帳號。",
        "app_cta": "試用 Lumi 注音星球",
        "related": "相關免費資源",
        "related_items": (
            ("3 分鐘注音觀察指南", f"{SITE}/zh-Hant/tools/zhuyin-readiness-check.html"),
            ("37 個注音符號表", f"{SITE}/tools/zhuyin-bopomofo-chart.html"),
            ("注音描寫練習表", f"{SITE}/tools/zhuyin-practice-sheet.html"),
            (
                "家庭注音繪本四週共讀包",
                f"{SITE}/zh-Hant/tools/zhuyin-family-picture-book-club-kit.html",
            ),
            (
                "家庭—教師注音交接包",
                f"{SITE}/zh-Hant/tools/zhuyin-parent-teacher-handoff-kit.html",
            ),
        ),
        "faq": "家長常見問題",
        "faq_items": (
            ("孩子上小一前一定要會注音嗎？", "本日曆不設定入學門檻。請向孩子的學校確認教學安排，並只把這份日曆當成選用的熟悉流程。"),
            ("14 天能學完全部 37 個符號嗎？", "不能。它只取樣聽音、字形、筆順、聲調、拼讀與閱讀互動；可重複、暫停或日後延續，不替孩子分級。"),
            ("孩子平常很少說華語怎麼辦？", "把口語視為另一項需要；注音要搭配對話與流暢口語，不把符號學得慢解讀成診斷。"),
            ("一定要使用 App 嗎？", "不用。紙張、官方參考、大人示範與合法取得的注音讀物，就能完成整份日曆。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立家庭資源；不是官方課程、入學門檻、評量、診斷或學校成果保證。",
    },
}

STYLE = """
:root{--ink:#283246;--muted:#687287;--paper:#fffef9;--line:#dddcd4;--blue:#486a93;--green:#42806d;--sun:#d99a35;--soft:#eef7f2}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#f4f9ff 0,#f5fbf7 52%,#fff9ea 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}a{color:#315f87}.wrap{width:min(1080px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:4;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850}.links{display:flex;gap:15px}.hero{padding:58px 0 32px}.eyebrow{color:var(--green);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:940px;margin:.18em 0;font-size:clamp(2rem,5.7vw,4rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:830px;color:var(--muted);font-size:clamp(1.08rem,2.5vw,1.27rem)}.badges,.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.badge{padding:8px 12px;border:1px solid #cde0d9;border-radius:999px;background:#fff;color:#3e665d;font-weight:800;white-space:nowrap}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--green),#579781);color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #34796f28}.button.secondary{background:#fff;color:#315f87!important;border:1px solid #c9d6e2;box-shadow:none}.button:focus-visible{outline:3px solid #e2b858;outline-offset:3px}.card{padding:23px;background:var(--paper);border:1px solid var(--line);border-radius:23px;box-shadow:0 10px 32px #34281a12}.boundary{margin-bottom:24px}.notice{padding:17px 19px;border-left:5px solid var(--sun);border-radius:14px;background:#fff7dc}.section-title{margin:1.6em 0 .55em;font-size:clamp(1.45rem,3vw,2rem);line-height:1.18}.lanes,.info-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.lane{padding:19px;border:1px solid #cadbd5;border-radius:18px;background:#fff}.lane h3{margin:.1em 0}.routine{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:16px}.beat{padding:14px;border-radius:16px;background:var(--soft);font-weight:750}.calendar{margin-top:25px;padding:clamp(20px,4vw,32px);background:#fff;border:1px solid #d8d9d5;border-radius:28px;box-shadow:0 20px 55px #23354b15}.calendar-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}.calendar-head h2{margin:.1em 0}.days{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;margin-top:20px}.day{padding:19px;border:1px solid #d7dcd7;border-radius:19px;background:linear-gradient(160deg,#fff,#fbfdfb);break-inside:avoid}.day-no{color:var(--green);font-size:.82rem;font-weight:900;letter-spacing:.05em}.day h3{margin:.18em 0 .6em;line-height:1.25}.route{margin:.55em 0;padding:11px 13px;border-radius:13px;background:#f0f6fb}.route.stretch{background:#fff8e8}.route strong{display:block;color:#526276;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}.extras{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:24px}.source-list a{overflow-wrap:anywhere}.related ul{padding-left:1.2em}.faq{margin-top:24px}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--green);font-weight:800}
@media(max-width:820px){.lanes,.info-grid,.extras{grid-template-columns:1fr}.routine{grid-template-columns:1fr 1fr}.days{grid-template-columns:1fr}.links a:first-child{display:none}.hero{padding-top:38px}}
@media(max-width:480px){.routine{grid-template-columns:1fr}.badge{font-size:.88rem}.calendar{padding:16px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.extras,.app-card,.related,.faq,.evidence,.footer,.actions,.share-status{display:none!important}body{background:#fff;font-size:9.2pt}.wrap{width:100%}.boundary,.calendar,.card{border:0;box-shadow:none;padding:0}.boundary{margin-bottom:4mm}.lanes{grid-template-columns:repeat(3,1fr);gap:3mm}.lane{padding:3mm}.routine{grid-template-columns:repeat(5,1fr);gap:2mm}.beat{padding:2mm}.calendar-head{margin-top:4mm}.days{grid-template-columns:repeat(2,1fr);gap:3mm}.day{padding:3mm}.route{padding:2mm;margin:1.5mm 0}@page{size:A4;margin:8mm}}
"""

SCRIPT = """
(function(){
  "use strict";
  var cfg=JSON.parse(document.getElementById("calendar-config").textContent);
  document.getElementById("print-calendar").addEventListener("click",function(){window.print();});
  document.getElementById("share-calendar").addEventListener("click",function(){
    var status=document.getElementById("share-status");
    var data={title:cfg.shareTitle,url:location.href.split("#")[0]};
    if(navigator.share){
      navigator.share(data).catch(function(error){if(error.name!=="AbortError"){status.textContent=data.url;}});
    }else if(navigator.clipboard){
      navigator.clipboard.writeText(data.url).then(function(){status.textContent=cfg.shared;})
        .catch(function(){status.textContent=data.url;});
    }else{status.textContent=data.url;}
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
    app_url = appstore_url("lumibopomofo", f"iag_grade1_14day_{locale.lower()}")
    badges = "".join(
        f'<span class="badge">✓ {html.escape(item)}</span>' for item in t["badges"]
    )
    lanes = "".join(
        f'<article class="lane"><h3>{html.escape(title)}</h3>'
        f"<p>{html.escape(text)}</p></article>"
        for title, text in t["lane_items"]
    )
    routine = "".join(
        f'<div class="beat">{html.escape(item)}</div>' for item in t["routine_items"]
    )
    day_cards = "".join(
        '<article class="day">'
        f'<div class="day-no">{html.escape(day["day"])}</div>'
        f'<h3>{html.escape(day["focus"])}</h3>'
        f'<div class="route"><strong>{html.escape(t["base_label"])}</strong>'
        f'{html.escape(day["base"])}</div>'
        f'<div class="route stretch"><strong>{html.escape(t["stretch_label"])}</strong>'
        f'{html.escape(day["stretch"])}</div>'
        "</article>"
        for day in DAYS[locale]
    )
    sources = "".join(
        f'<li><a href="{html.escape(source_url)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
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
            "learningResourceType": "Fourteen-day family warm-up calendar",
            "educationalUse": "Optional pre-school familiarity practice",
            "educationalLevel": "Beginner",
            "typicalAgeRange": "5-7",
            "license": LICENSE,
            "citation": [MOE_HANDBOOK, MOE_PRACTICE],
            "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
        },
        {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": t["title"],
            "description": t["description"],
            "step": [
                {
                    "@type": "HowToStep",
                    "position": index,
                    "name": f'{day["day"]}: {day["focus"]}',
                    "text": day["base"],
                }
                for index, day in enumerate(DAYS[locale], 1)
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
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#calendar">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div></section>
<section class="wrap boundary"><article class="card"><h2 class="section-title">{html.escape(t["boundary"])}</h2><p class="notice">{html.escape(t["boundary_text"])}</p><h2 class="section-title">{html.escape(t["lanes"])}</h2><p>{html.escape(t["lane_intro"])}</p><div class="lanes">{lanes}</div><h2 class="section-title">{html.escape(t["routine"])}</h2><div class="routine">{routine}</div></article></section>
<section class="wrap calendar" id="calendar"><div class="calendar-head"><h2>{html.escape(t["calendar"])}</h2><div class="actions"><button class="button secondary" id="print-calendar" type="button">{html.escape(t["print"])}</button><button class="button" id="share-calendar" type="button">{html.escape(t["share"])}</button></div></div><div class="days">{day_cards}</div><div class="share-status" id="share-status" aria-live="polite"></div></section>
<section class="wrap extras"><article class="card"><h2>{html.escape(t["privacy"])}</h2><p>{html.escape(t["privacy_text"])}</p></article><article class="card"><h2>{html.escape(t["reuse"])}</h2><p>{html.escape(t["reuse_text"])}</p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></article></section>
<section class="wrap card evidence"><h2>{html.escape(t["evidence"])}</h2><p>{html.escape(t["evidence_text"])}</p><h3>{html.escape(t["sources"])}</h3><ul class="source-list">{sources}</ul></section>
<section class="wrap extras related"><article class="card"><h2>{html.escape(t["related"])}</h2><ul>{related}</ul></article><article class="card app-card"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_url)}" rel="nofollow noopener">{html.escape(t["app_cta"])}</a></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq"])}</h2>{faq_html}</section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="calendar-config">{config_json}</script>
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
        f'<a href="{target}">14-Day Grade 1 Zhuyin Summer Warm-Up</a></h2>'
        "<p>A bilingual, non-scored 8–10 minute family calendar.</p>"
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
        r'zhuyin-readiness-check\.html">.*?</article>',
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
        print(f"grade-1 summer calendar -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
