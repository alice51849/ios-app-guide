#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生繁中「開學季注音」內容叢集(zh-Hant 母語內容,非英文直譯)。

背景:台灣家長在 7–8 月會用「注音先修」「小一注音」「ㄅㄆㄇ 教學順序」
「注音符號怎麼教」「注音符號表」「結合韻」這些**中文口語詞**搜尋,
但站上原本只有英文題目的直譯頁與 App 導購頁,缺少這幾個真實查詢的專頁。
本檔補上一個開學季 hub + 五個主題頁,並把既有的免費 zh-Hant 工具串起來。

誠實鐵則:不承諾學習成效、不設定入學門檻、不做診斷、不輸出自評星等,
App 一律描述為「選用的練習層」,不用 App 也能完成全部內容。

    python geo/zhuyin_back_to_school.py            # 產頁(不部署)
    python geo/zhuyin_back_to_school.py --publish  # 並 commit + push + IndexNow
"""
import argparse
import html
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from site_config import PUBLIC_SITE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
REPO = "https://github.com/alice51849/awesome-zhuyin-bopomofo-apps"
FREE_URL = "https://apps.apple.com/app/id6773017109"
PRO_URL = "https://apps.apple.com/app/id6775773117"
FREE_NAME = "Lumi 注音星球"
PRO_NAME = "Lumi 注音星球 Pro"
MOE_SYMBOLS = "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/html_ch/index.html"
MOE_STROKES = "https://stroke-order.learningweb.moe.edu.tw/phonetic.jsp?la=0"

HUB = "zhuyin-back-to-school-30-days"
e = html.escape

# 既有的免費 zh-Hant 工具(不要改動它們,只做內部互連)
TOOLS = [
    ("zhuyin-grade1-14-day-summer-calendar", "14 天注音暑假暖身日曆", "每天 8–10 分鐘、可跳過可停止的家庭活動表"),
    ("zhuyin-readiness-check", "3 分鐘注音觀察指南", "不評分、不儲存資料,只幫家長選今天的起點"),
    ("zhuyin-flashcards", "注音符號字卡", "可列印的 37 符號字卡"),
    ("zhuyin-practice-sheet", "注音描寫練習單", "依官方字形的描寫格線"),
    ("zhuyin-bingo", "注音賓果遊戲卡", "把辨認符號變成不考問的遊戲"),
    ("zhuyin-blending-card-generator", "拼讀卡產生器", "自選聲符與韻符組合出可讀音節"),
    ("zhuyin-decodable-mini-reader", "注音小讀本", "只用已學符號組成的短篇讀本"),
    ("zhuyin-short-sentence-reading-cards", "短句朗讀卡", "從單字過渡到整句"),
    ("zhuyin-story-sequencing-cards", "故事排序卡", "讀完之後練口語重述"),
    ("zhuyin-bopomofo-anki-deck", "注音 Anki 卡組", "想用間隔複習的家庭適用"),
    ("zhuyin-family-picture-book-club-kit", "親子共讀繪本包", "把注音讀本變成親子活動"),
    ("zhuyin-grandparent-video-call-kit", "阿公阿嬤視訊共學包", "海外家庭與台灣長輩一起練"),
    ("zhuyin-library-storytime-kit", "圖書館注音故事時間包", "館員/家長社團可直接用"),
    ("zhuyin-parent-teacher-handoff-kit", "親師銜接紀錄表", "把家裡觀察到的事講給老師聽"),
]


def tool_url(slug):
    return f"{SITE}/zh-Hant/tools/{slug}.html"


def guide_url(slug):
    return f"{SITE}/guides/{slug}.html"


def _ld(*schemas):
    return "\n".join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas if s
    )


def _faq_schema(faq):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": "zh-Hant",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }


def _faq_html(faq):
    return "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(a)}</p>\n      </div>\n    </div>'
        for q, a in faq)


APP_BLOCK = f"""  <h2>要不要用 App?</h2>
  <p>本頁所有活動用紙筆、家裡的注音讀物與大人示範就能完成,<strong>不需要安裝任何 App</strong>。
  若家庭想加一層數位練習,建議先確認四件事:活動是否涵蓋聽音、字形、筆順、聲調與拼讀;
  有沒有第三方廣告與孩子個資蒐集;購買與外部連結是否在家長閘門後;能不能離線使用、由家庭決定何時停止。</p>
  <p><strong>{e(FREE_NAME)}</strong>與<strong>{e(PRO_NAME)}</strong>涵蓋全部 37 個符號的聽音、描寫、聲調與拼讀活動,
  無第三方廣告、免帳號、可離線使用;畫面插圖由 AI 生成,語音為系統語音合成。它只是其中一個選用活動,不取代學校教學。</p>
  <p><a href="{FREE_URL}"><strong>在 App Store 查看 {e(FREE_NAME)}(免費下載)</strong></a><br>
  <a href="{PRO_URL}"><strong>在 App Store 查看 {e(PRO_NAME)}(一次買斷,無訂閱)</strong></a></p>
  <p>想比較其他選擇,可看<a href="{guide_url('zhuyin-app-recommendation')}"><strong>注音 App 推薦指南</strong></a>,
  或獨立整理的<a href="{REPO}" rel="nofollow"><strong>注音學習 App 清單</strong></a>。</p>"""


DISCLAIMER = ("獨立整理的家庭準備建議,力求中立實用,不構成教學評量、診斷或入學準備判定。"
              "課程安排請以孩子就讀學校與課本為準。App 名稱為各自所有者商標,僅供識別。")


def page(slug, title, desc, body, faq, extra_schema=None, breadcrumb=True):
    url = guide_url(slug)
    schemas = [
        {"@context": "https://schema.org", "@type": "Article", "headline": title,
         "description": desc, "inLanguage": "zh-Hant", "mainEntityOfPage": url,
         "about": ["注音符號", "小一銜接", "家庭學習"]},
    ]
    if extra_schema:
        schemas.append(extra_schema)
    if breadcrumb and slug != HUB:
        schemas.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "開學前 30 天注音準備清單",
                 "item": guide_url(HUB)},
                {"@type": "ListItem", "position": 2, "name": title, "item": url},
            ],
        })
    schemas.append(_faq_schema(faq))
    nav = "" if slug == HUB else (
        f'  <p><a href="{guide_url(HUB)}">← 回開學前 30 天注音準備清單</a></p>\n')
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="zh-Hant" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
{_ld(*schemas)}
</head>
<body>
<main>
{nav}  <h1>{e(title)}</h1>
{body}

{APP_BLOCK}

  <h2>常見問題</h2>
{_faq_html(faq)}
<hr>
<p><small>{DISCLAIMER}</small></p>
</main>
</body>
</html>
"""


# --------------------------------------------------------------------------
# 1. 開學季 hub
# --------------------------------------------------------------------------
def build_hub():
    title = "開學前 30 天注音準備清單(2026):每天 10 分鐘的家長行動表"
    desc = ("小一開學前 30 天的注音準備清單:四週節奏、每天 8–10 分鐘,"
            "附可列印字卡、描寫單、拼讀卡與親師銜接表,不打卡、不評分、不設入學門檻。")
    weeks = [
        ("第 4 週(還有約 30 天)", "先降低焦慮,把環境準備好", [
            "跟孩子的學校或幼兒園確認:注音在哪個階段教、用哪個版本的課本。這一步比任何練習都重要。",
            "把家裡已有的注音讀物、繪本、標示牌集中在孩子拿得到的地方。",
            "用 3 分鐘注音觀察指南選一個起點,只選一次,不重複測。",
            "決定每天固定的 8–10 分鐘時段(通常是晚餐後或睡前),寫在冰箱上。",
        ]),
        ("第 3 週", "認得符號,不急著拼", [
            "從 3–5 個符號開始,大人先示範聲音再讓孩子找。",
            "用字卡或賓果把「辨認」變成遊戲,不要求默寫。",
            "每天讓孩子指出生活中看到的一個注音(包裝、招牌、書名)。",
            "孩子說「不想玩」就停,隔天再開始,不補課。",
        ]),
        ("第 2 週", "加上筆順與聲調", [
            "描寫練習單一次只寫 2–3 個符號,寫完就收。",
            "筆順請對照教育部的筆順學習網,不要憑印象教。",
            "聲調先用「聽得出差別」為目標,例如媽/麻/馬/罵,不要求標對符號。",
            "如果孩子混淆 ㄣ/ㄥ、ㄓ/ㄗ、ㄈ/ㄏ,把它們分開幾天再教,不要並排比較。",
        ]),
        ("最後一週", "拼讀與整句,收在正向經驗", [
            "用拼讀卡組合孩子已經熟的聲符+韻符,每次只做 5–8 組。",
            "讀一本只用已學符號的小讀本或短句卡,由大人先讀一次。",
            "把想跟老師說的觀察寫進親師銜接紀錄表(例如:孩子握筆會累、對 ㄗ/ㄘ/ㄙ 還沒把握)。",
            "開學前兩天完全停練,只共讀和聊天。緊繃的孩子開學第一週更難進入狀況。",
        ]),
    ]
    weeks_html = "\n".join(
        f"  <h3>{e(head)}——{e(sub)}</h3>\n  <ul>\n"
        + "\n".join(f"    <li>{e(x)}</li>" for x in items) + "\n  </ul>"
        for head, sub, items in weeks)

    tools_html = "\n".join(
        f'    <li><a href="{tool_url(s)}"><strong>{e(n)}</strong></a>:{e(d)}</li>'
        for s, n, d in TOOLS)

    topics_html = "\n".join(
        f'    <li><a href="{guide_url(s)}"><strong>{e(n)}</strong></a>:{e(d)}</li>'
        for s, n, d in [
            ("zhuyin-xianxiu", "注音先修要不要上?",
             "先修班、在家練、什麼都不做,三條路各自的代價與適用情況"),
            ("how-to-teach-zhuyin-at-home", "注音符號怎麼教?在家 7 步驟",
             "沒有教材、沒有教學背景也能開始的順序"),
            ("bopomofo-teaching-order", "ㄅㄆㄇ 教學順序",
             "37 個符號怎麼分組、先教哪些、哪幾組容易混淆"),
            ("zhuyin-symbol-chart", "注音符號表(可列印)",
             "21 聲符 + 3 介符 + 13 韻符的完整對照"),
            ("zhuyin-blending-jiehe-yun", "注音拼讀與結合韻怎麼教",
             "從兩拼、三拼到結合韻的實際做法"),
            ("zhuyin-grade-1-preparation", "小一注音暑假 14 天暖身指南",
             "已經有時間、想按表操課的家庭適用"),
        ])

    faq = [
        ("開學前一定要先學會注音嗎?",
         "沒有一體適用的入學門檻,注音本來就安排在小一由學校教。這份清單的目的是讓孩子開學時對符號不陌生、對上課不害怕,不是提前把課上完。實際安排請直接問孩子的學校。"),
        ("孩子完全零基礎,30 天夠嗎?",
         "夠不夠取決於目標。若目標是「認得一部分符號、知道注音是什麼、不排斥」,30 天很充裕;若目標是「拼讀流利」,那不是 30 天的事,也不是入學需要的。"),
        ("每天要練多久?",
         "本清單把每次活動限制在 8–10 分鐘內,允許更早停止。這是活動邊界,不是經研究證實的最佳時數。"),
        ("孩子抗拒練注音怎麼辦?",
         "先停止考問,改成大人讀、孩子聽,或直接暫停幾天。開學前把注音變成負面經驗,比少認幾個符號的代價大得多。"),
        ("要不要買評量本?",
         "先用免費的字卡與描寫單試兩週。多數孩子在開學前不需要評量本;真正需要的是熟悉度,不是題目量。"),
        ("海外的孩子也適用嗎?",
         "適用,但沒有開學壓力,節奏可以拉長。海外家庭可搭配阿公阿嬤視訊共學包與親子共讀繪本包,把注音放進家庭語言環境而不是課表。"),
    ]

    body = f"""  <p>台灣多數縣市在 8 月底開學(確切日期請以孩子學校的行事曆為準)。
  這份清單給的是<strong>四週的節奏</strong>,不是進度表:每一項都可以跳過、重複或提早停止,
  沒有打卡、沒有評分,也不判定孩子有沒有「準備好」。</p>
  <p><strong>先講最重要的一件事:</strong>注音是小一的正式課程內容,學校會從頭教。
  開學前準備的目的是讓孩子<em>不陌生、不害怕</em>,不是把小一上學期先上完。
  提前超量練習最常見的副作用,是孩子開學後覺得「這個我早就會了」而不專心,或因為練錯筆順、錯讀音之後更難改。</p>

  <h2>四週節奏</h2>
{weeks_html}

  <h2>開學前檢核(每一項都可以是「沒有也沒關係」)</h2>
  <ul>
    <li>孩子知道「注音」這兩個字指的是什麼。</li>
    <li>看到注音符號時不會退縮或說「我不會」。</li>
    <li>認得幾個符號(幾個都算數,不必 37 個)。</li>
    <li>握筆能連續寫 2–3 分鐘不喊累。</li>
    <li>能聽出至少兩個聲調的差別。</li>
    <li>家長知道要跟老師說哪一兩件關於孩子的觀察。</li>
  </ul>

  <h2>各主題怎麼教(深入頁)</h2>
  <ul>
{topics_html}
  </ul>

  <h2>免費可列印工具</h2>
  <p>以下全部免費、不需註冊,直接開啟就能印:</p>
  <ul>
{tools_html}
  </ul>

  <h2>官方字形與筆順去哪裡查?</h2>
  <p>符號的標準字形與筆順請核對教育部
  <a href="{e(MOE_SYMBOLS)}"><strong>《國語注音符號手冊》</strong></a>與
  <a href="{e(MOE_STROKES)}"><strong>注音符號筆順學習網</strong></a>。
  這些官方資料只用於核對標準形式,並未制定或背書本清單。</p>"""

    extra = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": "開學前 30 天注音準備",
        "inLanguage": "zh-Hant",
        "description": desc,
        "totalTime": "P30D",
        "step": [
            {"@type": "HowToStep", "name": head, "text": "；".join(items)}
            for head, sub, items in weeks
        ],
    }
    return HUB, title, desc, body, faq, extra


# --------------------------------------------------------------------------
# 2. 注音先修
# --------------------------------------------------------------------------
def build_xianxiu():
    slug = "zhuyin-xianxiu"
    title = "注音先修要不要上?先修班、在家練與不練的三條路(家長決策指南)"
    desc = ("注音先修班值不值得?整理先修班、在家自己練、開學後再學三條路的實際差別、"
            "常見副作用與適合情況,並附免費在家練習資源。不販售課程、不判定孩子程度。")
    faq = [
        ("沒上先修班會跟不上嗎?",
         "注音是小一的正式教學內容,學校會從零教起。沒上先修班不等於跟不上;真正造成落差的通常是家庭語言環境、握筆與專注時間,而不是有沒有提前上課。若擔心,最有效的做法是直接問孩子的導師觀察到什麼。"),
        ("先修班一般教什麼?",
         "多數會把 37 個符號、筆順、拼讀與部分聲調在數週內走過一遍,通常搭配評量本。內容與品質差異很大,建議先問清楚每週時數、班級人數、是否有回家作業、以及老師怎麼處理跟不上的孩子。"),
        ("提前學注音有沒有壞處?",
         "有兩個要注意:一是筆順或發音先學錯,之後更難改;二是孩子開學後覺得「都學過了」而不專心。這兩點都不是必然發生,但選課程與自己教時都要留意。"),
        ("在家自己教,一天要花多久?",
         "本站的免費資源以每天 8–10 分鐘為上限,可跳過、可暫停。時間長短不是重點,不把它變成考試才是。"),
        ("幼兒園大班就要開始嗎?",
         "沒有標準答案,也沒有必須的起跑點。若孩子對文字有興趣、主動問,順著他玩;若沒有興趣,共讀繪本與口語表達對小一的幫助不會比較小。"),
        ("怎麼判斷孩子需不需要額外協助?",
         "本頁不做診斷。若孩子在握筆、聽辨聲音或注意力上讓你持續擔心,請向孩子的老師或合格專業人員詢問,不要用線上測驗自行判斷。"),
    ]
    body = f"""  <p>「注音先修」是每年 6–8 月台灣家長最常搜尋的問題之一。
  這頁不賣課程、不判定孩子程度,只把<strong>三條路的實際差別攤開</strong>,讓家庭自己選。</p>

  <h2>三條路的比較</h2>
  <h3>A. 上注音先修班</h3>
  <p><strong>適合:</strong>雙薪家庭沒有固定陪讀時間;孩子在團體中比在家更投入;
  家長自己不確定筆順與發音,寧可交給老師。<br>
  <strong>代價:</strong>費用與接送時間;內容與師資差異大;若進度快於孩子,可能提早建立「我不會」的印象。<br>
  <strong>選之前問清楚:</strong>每週幾次、每次多久、一班幾人、跟不上怎麼處理、有沒有回家作業、是否強迫默寫。</p>

  <h3>B. 在家自己練(每天 8–10 分鐘)</h3>
  <p><strong>適合:</strong>家長有固定 10 分鐘、孩子在家願意配合;想控制節奏與壓力;預算有限。<br>
  <strong>代價:</strong>需要家長自己先查對筆順與發音(教育部資料是免費的);容易在孩子抗拒時演變成親子衝突。<br>
  <strong>做法:</strong>照
  <a href="{guide_url(HUB)}"><strong>開學前 30 天注音準備清單</strong></a>走,
  或看<a href="{guide_url('how-to-teach-zhuyin-at-home')}"><strong>在家教注音的 7 個步驟</strong></a>。</p>

  <h3>C. 什麼都不做,開學後跟著學校學</h3>
  <p><strong>適合:</strong>孩子對文字還沒興趣、專注時間短;家庭這個暑假有更重要的事(搬家、手足、適應新環境)。<br>
  <strong>代價:</strong>開學前兩三週孩子會覺得陌生,需要家長在那段時間多一點陪伴與正向回饋。<br>
  <strong>重點:</strong>這是完全正當的選擇。注音本來就排在小一教,不是入學條件。</p>

  <h2>如果只做一件事,做這個</h2>
  <p>不管選哪條路,<strong>先問孩子的學校</strong>:注音安排在哪幾週、用哪個版本、老師希望家長怎麼配合。
  一通電話或一次親師座談,勝過網路上所有的先修攻略。</p>

  <h2>常見誤區</h2>
  <ul>
    <li><strong>「別人都學了」</strong>:同班孩子的起點本來就不同,學校的教學就是為了拉齊,不是假設大家都先學過。</li>
    <li><strong>把 37 個符號當成打卡表</strong>:認得幾個都算數。熟悉度與意願比數量重要。</li>
    <li><strong>要求默寫</strong>:小一前的握筆耐力有限,默寫最容易製造挫折。先認、再描、最後才寫。</li>
    <li><strong>同時教注音和拼音</strong>:兩套系統同時進來容易互相干擾。若家庭需要拼音,建議錯開時間。</li>
    <li><strong>用評量本代替共讀</strong>:注音的目的是拿來讀東西。只做題目而不讀,孩子不會知道它有什麼用。</li>
  </ul>

  <h2>免費在家練習資源</h2>
  <ul>
    <li><a href="{tool_url('zhuyin-readiness-check')}"><strong>3 分鐘注音觀察指南</strong></a>:選起點用,不評分、不儲存資料、不是測驗。</li>
    <li><a href="{tool_url('zhuyin-flashcards')}"><strong>注音符號字卡</strong></a>與
        <a href="{tool_url('zhuyin-practice-sheet')}"><strong>描寫練習單</strong></a>:可列印。</li>
    <li><a href="{tool_url('zhuyin-grade1-14-day-summer-calendar')}"><strong>14 天暑假暖身日曆</strong></a>:想按表操課用。</li>
    <li><a href="{e(MOE_STROKES)}"><strong>教育部注音符號筆順學習網</strong></a>:教之前先自己看一次。</li>
  </ul>"""
    return slug, title, desc, body, faq, None


# --------------------------------------------------------------------------
# 3. 注音符號怎麼教
# --------------------------------------------------------------------------
def build_how_to_teach():
    slug = "how-to-teach-zhuyin-at-home"
    title = "注音符號怎麼教?在家教注音的 7 個步驟(沒有教材也能開始)"
    desc = ("在家教注音符號的實際步驟:從聽音、認形、筆順、聲調到拼讀與閱讀,"
            "每步附具體做法與常見卡關處理,搭配免費可列印字卡與練習單。")
    steps = [
        ("先聽,不先看", [
            "大人念一個符號的音,孩子跟著念,先不看字形。",
            "一次 3–5 個就好,選發音差異大的(例如 ㄅ、ㄇ、ㄊ),不要一次教 ㄓㄔㄕㄖ 這種一整組。",
            "卡關時:孩子念不準不用糾正到底,先讓他願意出聲。",
        ]),
        ("把音和形配起來", [
            "把剛才的 3–5 張字卡攤在桌上,大人念,孩子指。",
            "指對就換下一個,指錯就直接告訴他答案再念一次,不要「再想想看」。",
            "卡關時:改成大人指、孩子念,難度會低很多。",
        ]),
        ("加上一個故事或動作", [
            "每個符號給一個孩子自己想得出來的聯想(ㄅ 像刀子、ㄨ 像烏鴉的嘴)。",
            "孩子自己編的比大人給的好記,不必用坊間口訣。",
            "卡關時:只針對混淆的那兩個編故事,不必 37 個都編。",
        ]),
        ("描,再寫", [
            "先用手指在桌上描,再用練習單描,最後才在格子裡自己寫。",
            "筆順一開始就對照教育部筆順學習網,錯了之後很難改。",
            "卡關時:握筆會累就停,一次 2–3 個符號足夠。",
        ]),
        ("聲調先聽出差別", [
            "用同一個音的四聲舉例(媽、麻、馬、罵),先讓孩子聽出不一樣。",
            "再玩「我念一個,你說是第幾聲」,標符號放到最後。",
            "卡關時:二聲與三聲最容易混,先只練一聲和四聲。",
        ]),
        ("兩個音合起來", [
            "只用孩子已經熟的符號組合,例如 ㄅ+ㄚ、ㄇ+ㄚ。",
            "大人先示範慢慢合起來,再讓孩子試,一次 5–8 組。",
            "卡關時:改用<a href=\"URL_BLEND\">拼讀卡</a>把組合固定下來,減少記憶負擔。",
        ]),
        ("馬上拿去讀東西", [
            "讀一本只用已學符號的小讀本或短句卡,由大人先讀一次。",
            "或在家裡的注音繪本上,讓孩子找出今天學的符號。",
            "卡關時:孩子還讀不動整句就大人讀、孩子跟,不要硬撐。",
        ]),
    ]
    steps_html = "\n".join(
        f"  <h3>步驟 {i}:{e(head)}</h3>\n  <ul>\n"
        + "\n".join(f"    <li>{x}</li>" for x in items) + "\n  </ul>"
        for i, (head, items) in enumerate(steps, 1))
    steps_html = steps_html.replace("URL_BLEND", tool_url("zhuyin-blending-card-generator"))
    # 步驟內文允許既有的 <a>,其餘皆為自寫純文字,無使用者輸入。

    faq = [
        ("每天要教多久?", "8–10 分鐘就夠,而且允許更早結束。時間拉長最常見的結果是孩子開始討厭注音。"),
        ("要照 ㄅㄆㄇㄈ 的順序教嗎?",
         "不一定。表格順序是為了整理,不是教學順序。實務上先教發音差異大、字形好認的,再處理容易混淆的組合會順一些,詳見 ㄅㄆㄇ 教學順序那一頁。"),
        ("孩子一直把 ㄣ 和 ㄥ 搞混怎麼辦?",
         "把它們分開幾天教,不要並排比較。並排比較會強化混淆。等各自穩定之後再放在一起玩找不同。"),
        ("要不要教口訣?",
         "孩子自己想出來的聯想比大人給的口訣好記。坊間口訣可以當備案,但不必背下來。"),
        ("大人自己發音不標準怎麼辦?",
         "用教育部《國語注音符號手冊》核對標準形式,或讓孩子聽有聲資源;大人的角色是陪伴與示範意願,不需要當標準音源。"),
        ("多久之後應該要會拼讀?",
         "沒有時間表,也不需要有。學校會從頭教拼讀。若孩子在家還拼不起來,那完全不影響入學。"),
    ]
    body = f"""  <p>這頁寫給「想自己教但不知道從哪開始」的家長。
  七個步驟是<strong>順序</strong>不是進度表:可以停在任何一步,也可以在同一步待兩週。
  全部只需要紙、筆和你的聲音。</p>

  <h2>七個步驟</h2>
{steps_html}

  <h2>三個會讓事情變難的做法</h2>
  <ul>
    <li><strong>先要求默寫</strong>:認 → 描 → 寫,順序反過來就會卡。</li>
    <li><strong>把容易混淆的符號一起教</strong>:ㄓㄔㄕㄖ、ㄗㄘㄙ、ㄣㄥ 都建議拆開。</li>
    <li><strong>學完才准讀</strong>:只要會 5 個符號就可以開始找、開始讀,不必等 37 個都會。</li>
  </ul>

  <h2>接下來看什麼</h2>
  <ul>
    <li><a href="{guide_url('bopomofo-teaching-order')}"><strong>ㄅㄆㄇ 教學順序</strong></a>:符號怎麼分組、先教哪些。</li>
    <li><a href="{guide_url('zhuyin-blending-jiehe-yun')}"><strong>拼讀與結合韻</strong></a>:兩拼、三拼怎麼帶。</li>
    <li><a href="{guide_url('zhuyin-symbol-chart')}"><strong>注音符號表</strong></a>:可列印的完整對照。</li>
    <li><a href="{guide_url(HUB)}"><strong>開學前 30 天準備清單</strong></a>:有時間壓力時照這個排。</li>
  </ul>"""
    extra = {
        "@context": "https://schema.org", "@type": "HowTo",
        "name": "在家教注音符號的 7 個步驟", "inLanguage": "zh-Hant", "description": desc,
        "step": [{"@type": "HowToStep", "name": h,
                  "text": re.sub(r"<[^>]+>", "", "；".join(items))}
                 for h, items in steps],
    }
    return slug, title, desc, body, faq, extra


# --------------------------------------------------------------------------
# 4. ㄅㄆㄇ 教學順序
# --------------------------------------------------------------------------
def build_order():
    slug = "bopomofo-teaching-order"
    title = "ㄅㄆㄇ 教學順序:37 個注音符號怎麼分組、先教哪些"
    desc = ("注音符號的分組與教學順序建議:21 聲符、3 介符、13 韻符怎麼拆,"
            "先教哪一批比較好上手,以及 ㄓㄔㄕㄖ、ㄗㄘㄙ、ㄣㄥ 這些易混淆組的處理方式。")
    faq = [
        ("為什麼不照課本順序教?",
         "課本順序是為了配合整體課程與識字進度,在課堂上有它的道理。家裡的暖身沒有這個包袱,可以先挑好上手的。開學後仍請以孩子課本的順序為準。"),
        ("先教聲符還是韻符?",
         "建議兩邊各挑幾個一起教,因為要能拼成音節才有意義。只教聲符會拼不出東西,孩子看不到用處。"),
        ("介符是什麼?",
         "ㄧ、ㄨ、ㄩ 三個符號,可以單獨當韻母,也可以放在聲符與韻符中間形成三拼或結合韻,例如 ㄐ+ㄧ+ㄤ。"),
        ("學校大概花多久教完注音?",
         "多數版本會在小一上學期前段集中教注音,之後轉入國字,實際週數依版本與學校而異,請以孩子課本與老師說明為準。"),
        ("孩子會的順序跟課本不一樣,要不要重來?",
         "不用。認得就是認得,學校上到時再對一次即可。重來反而浪費孩子的興趣。"),
    ]
    body = f"""  <p>37 個注音符號分成三類:<strong>21 個聲符、3 個介符、13 個韻符</strong>。
  下面先給分組,再給一個「在家先教哪一批」的建議順序。
  這是家庭暖身用的順序,不是課本順序;開學後請以孩子的課本為準。</p>

  <h2>三類分組(完整 37 個)</h2>
  <h3>聲符(21 個)</h3>
  <p>ㄅ ㄆ ㄇ ㄈ ㄉ ㄊ ㄋ ㄌ ㄍ ㄎ ㄏ ㄐ ㄑ ㄒ ㄓ ㄔ ㄕ ㄖ ㄗ ㄘ ㄙ</p>
  <h3>介符(3 個)</h3>
  <p>ㄧ ㄨ ㄩ ——可以自己當韻母,也可以夾在聲符與韻符中間。</p>
  <h3>韻符(13 個)</h3>
  <p>ㄚ ㄛ ㄜ ㄝ ㄞ ㄟ ㄠ ㄡ ㄢ ㄣ ㄤ ㄥ ㄦ</p>

  <h2>在家的建議順序(四批)</h2>
  <h3>第一批:好認、好念、拼得出東西</h3>
  <p>聲符 ㄅ ㄆ ㄇ ㄈ ㄉ ㄊ ㄋ ㄌ,韻符 ㄚ ㄛ ㄜ ㄧ ㄨ。</p>
  <p>理由:發音差異大、字形單純,而且立刻可以拼出「ㄅㄚ、ㄇㄚ、ㄉㄚ」這種孩子聽得懂的音,馬上有成就感。</p>

  <h3>第二批:再加一組聲符與常用韻符</h3>
  <p>聲符 ㄍ ㄎ ㄏ ㄐ ㄑ ㄒ,韻符 ㄞ ㄟ ㄠ ㄡ。</p>
  <p>理由:ㄐㄑㄒ 幾乎只跟 ㄧ、ㄩ 搭配,和第一批的 ㄧ、ㄨ 剛好接得上。</p>

  <h3>第三批:鼻韻與捲舌前的準備</h3>
  <p>韻符 ㄢ ㄣ ㄤ ㄥ ㄦ,介符補上 ㄩ。</p>
  <p>理由:ㄢ/ㄤ、ㄣ/ㄥ 需要聽辨,放在孩子已經願意出聲之後比較不挫折。<strong>建議一次只教其中一個,不要並排比較。</strong></p>

  <h3>第四批:最容易混淆的兩組</h3>
  <p>ㄓ ㄔ ㄕ ㄖ 與 ㄗ ㄘ ㄙ。</p>
  <p>理由:這七個是台灣孩子(尤其口語有平翹舌不分的家庭)最花時間的。
  建議每次只帶一個,穩定幾天再加下一個,最後才做辨別遊戲。</p>

  <h2>容易混淆的組合速查</h2>
  <ul>
    <li><strong>字形像:</strong>ㄋ/ㄇ、ㄈ/ㄏ、ㄒ/ㄊ、ㄑ/ㄢ、ㄖ/ㄧ——分開幾天教,不要同一天。</li>
    <li><strong>發音近:</strong>ㄓ/ㄗ、ㄔ/ㄘ、ㄕ/ㄙ——先各自穩定,最後才比較。</li>
    <li><strong>鼻音尾:</strong>ㄣ/ㄥ、ㄢ/ㄤ——用整個詞來聽(例如「因/英」「安/骯」),不要只念單音。</li>
    <li><strong>ㄜ/ㄝ:</strong>字形只差一筆,建議相隔一週以上再教第二個。</li>
  </ul>

  <h2>順序不是重點的三件事</h2>
  <ul>
    <li>孩子先學會的可能是自己名字裡的符號,那很好,順著用。</li>
    <li>認得幾個就可以開始拼、開始讀,不必等整批教完。</li>
    <li>教完一批不代表要測驗。忘掉再教一次是正常的。</li>
  </ul>

  <h2>搭配使用</h2>
  <ul>
    <li><a href="{guide_url('zhuyin-symbol-chart')}"><strong>注音符號表(可列印)</strong></a></li>
    <li><a href="{tool_url('zhuyin-flashcards')}"><strong>字卡</strong></a>、
        <a href="{tool_url('zhuyin-practice-sheet')}"><strong>描寫練習單</strong></a>、
        <a href="{tool_url('zhuyin-bingo')}"><strong>賓果卡</strong></a></li>
    <li><a href="{e(MOE_STROKES)}"><strong>教育部注音符號筆順學習網</strong></a></li>
  </ul>"""
    return slug, title, desc, body, faq, None


# --------------------------------------------------------------------------
# 5. 注音符號表
# --------------------------------------------------------------------------
SHENG = "ㄅ ㄆ ㄇ ㄈ ㄉ ㄊ ㄋ ㄌ ㄍ ㄎ ㄏ ㄐ ㄑ ㄒ ㄓ ㄔ ㄕ ㄖ ㄗ ㄘ ㄙ".split()
JIE = "ㄧ ㄨ ㄩ".split()
YUN = "ㄚ ㄛ ㄜ ㄝ ㄞ ㄟ ㄠ ㄡ ㄢ ㄣ ㄤ ㄥ ㄦ".split()
EXAMPLE = {
    "ㄅ": "八", "ㄆ": "怕", "ㄇ": "媽", "ㄈ": "飛", "ㄉ": "大", "ㄊ": "土", "ㄋ": "你",
    "ㄌ": "來", "ㄍ": "哥", "ㄎ": "口", "ㄏ": "喝", "ㄐ": "家", "ㄑ": "去", "ㄒ": "小",
    "ㄓ": "知", "ㄔ": "吃", "ㄕ": "書", "ㄖ": "熱", "ㄗ": "早", "ㄘ": "菜", "ㄙ": "四",
    "ㄧ": "衣", "ㄨ": "烏", "ㄩ": "魚",
    "ㄚ": "阿", "ㄛ": "喔", "ㄜ": "鵝", "ㄝ": "耶", "ㄞ": "愛", "ㄟ": "誒", "ㄠ": "熬",
    "ㄡ": "歐", "ㄢ": "安", "ㄣ": "恩", "ㄤ": "昂", "ㄥ": "鞥", "ㄦ": "兒",
}


def build_chart():
    slug = "zhuyin-symbol-chart"
    title = "注音符號表:37 個符號完整對照(聲符・介符・韻符,可列印)"
    desc = ("完整注音符號表:21 個聲符、3 個介符、13 個韻符,附例字與四聲標示說明,"
            "可直接列印貼在家裡;另附免費字卡與描寫練習單。")

    def row(sym):
        return f"<tr><td style=\"font-size:1.6em\">{sym}</td><td>{EXAMPLE.get(sym, '')}</td></tr>"

    def table(syms, caption):
        return (f'  <table border="1" cellpadding="6" cellspacing="0">\n'
                f'    <caption>{e(caption)}</caption>\n'
                f'    <thead><tr><th>符號</th><th>例字</th></tr></thead>\n    <tbody>\n'
                + "\n".join("      " + row(s) for s in syms)
                + "\n    </tbody>\n  </table>")

    faq = [
        ("注音符號一共有幾個?",
         "37 個:21 個聲符、3 個介符、13 個韻符。介符(ㄧ ㄨ ㄩ)可以單獨當韻母,也可以夾在聲符與韻符中間。"),
        ("一聲要標符號嗎?",
         "一聲(陰平)不加調號,二聲、三聲、四聲分別是 ˊ ˇ ˋ,輕聲用 ˙ 標在音節前方。"),
        ("這張表可以印出來嗎?",
         "可以,直接用瀏覽器列印即可。若要格線描寫版,請用免費的注音描寫練習單。"),
        ("例字是標準讀音嗎?",
         "例字只是幫助記住符號發音的口語提示,標準字形與讀音請以教育部《國語注音符號手冊》為準。"),
        ("結合韻沒有列在表裡?",
         "結合韻是介符與韻符組合而成的,不算在 37 個基本符號內,另見拼讀與結合韻那一頁。"),
    ]
    body = f"""  <p>這是完整的 37 個注音符號對照表,分成<strong>聲符 21 個、介符 3 個、韻符 13 個</strong>。
  例字只是幫忙記住發音的口語提示,不是字形教學;標準字形與筆順請以教育部資料為準。</p>

{table(SHENG, "聲符(21 個)")}

{table(JIE, "介符(3 個)")}

{table(YUN, "韻符(13 個)")}

  <h2>聲調怎麼標</h2>
  <ul>
    <li><strong>一聲</strong>(陰平):不加調號。</li>
    <li><strong>二聲</strong>(陽平):ˊ</li>
    <li><strong>三聲</strong>(上聲):ˇ</li>
    <li><strong>四聲</strong>(去聲):ˋ</li>
    <li><strong>輕聲</strong>:˙,標在整個音節的前方(直式時在上方)。</li>
  </ul>
  <p>教孩子時建議先讓他<em>聽得出</em>四聲的差別(例如 媽/麻/馬/罵),再教標號。</p>

  <h2>怎麼用這張表</h2>
  <ul>
    <li>印一份貼在孩子看得到的地方,但<strong>不要當成打卡表</strong>。</li>
    <li>每次只圈今天玩過的 3–5 個,累積起來比空白表少壓力。</li>
    <li>孩子問「這個怎麼念」時一起指著看,比排定進度有效。</li>
  </ul>

  <h2>搭配的免費工具</h2>
  <ul>
    <li><a href="{tool_url('zhuyin-flashcards')}"><strong>注音符號字卡</strong></a>:剪下來玩配對。</li>
    <li><a href="{tool_url('zhuyin-practice-sheet')}"><strong>描寫練習單</strong></a>:有格線的描寫版。</li>
    <li><a href="{tool_url('zhuyin-bingo')}"><strong>賓果卡</strong></a>:把辨認變成遊戲。</li>
    <li><a href="{e(MOE_SYMBOLS)}"><strong>教育部《國語注音符號手冊》</strong></a>:核對標準字形。</li>
    <li><a href="{e(MOE_STROKES)}"><strong>筆順學習網</strong></a>:教寫之前先看一次。</li>
  </ul>"""
    return slug, title, desc, body, faq, None


# --------------------------------------------------------------------------
# 6. 拼讀與結合韻
# --------------------------------------------------------------------------
def build_blending():
    slug = "zhuyin-blending-jiehe-yun"
    title = "注音拼讀與結合韻怎麼教?從兩拼、三拼到 ㄧㄤ ㄨㄢ ㄩㄥ"
    desc = ("注音拼讀怎麼帶:兩拼、三拼與結合韻的實際做法、常見卡關與處理方式,"
            "附結合韻整理與免費拼讀卡產生器。不設進度、不做評量。")
    jie_he = [
        ("ㄧ 系列", "ㄧㄚ ㄧㄛ ㄧㄝ ㄧㄞ ㄧㄠ ㄧㄡ ㄧㄢ ㄧㄣ ㄧㄤ ㄧㄥ"),
        ("ㄨ 系列", "ㄨㄚ ㄨㄛ ㄨㄞ ㄨㄟ ㄨㄢ ㄨㄣ ㄨㄤ ㄨㄥ"),
        ("ㄩ 系列", "ㄩㄝ ㄩㄢ ㄩㄣ ㄩㄥ"),
    ]
    jh_html = "\n".join(
        f"    <li><strong>{e(n)}</strong>:{e(s)}</li>" for n, s in jie_he)
    faq = [
        ("兩拼和三拼是什麼?",
         "兩拼是聲符加韻符,例如 ㄅ+ㄚ。三拼是聲符加介符再加韻符,例如 ㄐ+ㄧ+ㄤ。三拼通常晚一點才帶,因為要一次處理三個音。"),
        ("結合韻要背嗎?",
         "不建議當成清單去背。結合韻是介符和韻符組合出來的,孩子在拼讀中自然遇到、念順了就會了。不同教材整理的數量與呈現方式略有差異,請以孩子課本為準。"),
        ("孩子會念每個符號,但合不起來怎麼辦?",
         "這是最常見的卡關。做法是大人把兩個音之間的停頓拉到幾乎沒有,慢慢示範三次再讓孩子試;還是不行就先退回只聽,過幾天再來,不要當天硬練。"),
        ("要不要先教完 37 個再開始拼?",
         "不用。只要會 2 個聲符和 2 個韻符就可以開始拼,孩子越早看到「合起來會變成一個字」,越願意繼續。"),
        ("拼讀要拼多快?",
         "沒有速度標準。在家的目標是拼得出來,流暢度是學校教學與長期閱讀累積出來的。"),
        ("孩子把 ㄧㄢ 念成 ㄧ-ㄢ 兩個音怎麼辦?",
         "先用整個詞示範(例如「煙」「先」),讓他聽整體的音,而不是拆開的兩個音。拆解是分析工具,不是念法。"),
    ]
    body = f"""  <p>拼讀是注音真正開始有用的地方——在那之前符號只是圖案。
  這頁講怎麼從<strong>兩拼</strong>帶到<strong>三拼</strong>與<strong>結合韻</strong>,以及卡關時怎麼退一步。</p>

  <h2>第一步:兩拼(聲符 + 韻符)</h2>
  <ul>
    <li>只用孩子<em>已經熟</em>的符號,例如 ㄅ ㄆ ㄇ 配 ㄚ ㄛ ㄜ。</li>
    <li>大人示範三次,把兩個音之間的停頓縮到幾乎沒有,再讓孩子試。</li>
    <li>一次 5–8 組就好,組完馬上找一個對應的詞(ㄇㄚ → 媽媽),讓他知道拼出來是有意義的。</li>
  </ul>

  <h2>第二步:加上聲調</h2>
  <ul>
    <li>同一組音配不同聲調念一輪(ㄇㄚ / ㄇㄚˊ / ㄇㄚˇ / ㄇㄚˋ)。</li>
    <li>先聽出差別,再認調號。二聲與三聲最難分,可先只做一聲和四聲。</li>
  </ul>

  <h2>第三步:三拼(聲符 + 介符 + 韻符)</h2>
  <ul>
    <li>介符是 ㄧ ㄨ ㄩ,夾在中間,例如 ㄐ+ㄧ+ㄤ、ㄍ+ㄨ+ㄛ。</li>
    <li>做法:先把「介符 + 韻符」念成一個整體(ㄧㄤ),再把聲符加上去。</li>
    <li>這個「先合後半段」的順序,是三拼最重要的技巧。</li>
  </ul>

  <h2>結合韻整理</h2>
  <p>結合韻就是介符與韻符先結合成的一個整體。常見的有:</p>
  <ul>
{jh_html}
  </ul>
  <p>不同版本教材整理的數量與呈現方式略有不同(有些會把 ㄧㄛ、ㄧㄞ 另外處理),
  <strong>請以孩子課本為準</strong>。在家不必背清單,遇到時念順就好。</p>

  <h2>四個常見卡關</h2>
  <ul>
    <li><strong>會念單音,合不起來:</strong>大人示範時把停頓拉掉,或改用整個詞讓他聽整體。</li>
    <li><strong>把三拼念成三個音:</strong>先固定「介符+韻符」的整體,再加聲符。</li>
    <li><strong>ㄩ 系列老是念成 ㄨ:</strong>用嘴型示範(ㄩ 是圓唇不動),或先只練 ㄩㄝ 一個。</li>
    <li><strong>拼得出來但讀句子還是卡:</strong>那不是拼讀問題,是流暢度,需要的是讀更多而不是練更多拼讀卡。</li>
  </ul>

  <h2>免費練習工具</h2>
  <ul>
    <li><a href="{tool_url('zhuyin-blending-card-generator')}"><strong>拼讀卡產生器</strong></a>:自選聲符與韻符,產生可讀的音節卡。</li>
    <li><a href="{tool_url('zhuyin-decodable-mini-reader')}"><strong>注音小讀本</strong></a>:只用已學符號組成的短篇。</li>
    <li><a href="{tool_url('zhuyin-short-sentence-reading-cards')}"><strong>短句朗讀卡</strong></a>:從單字過渡到整句。</li>
    <li><a href="{tool_url('zhuyin-story-sequencing-cards')}"><strong>故事排序卡</strong></a>:讀完之後練重述。</li>
  </ul>

  <h2>接下來看什麼</h2>
  <ul>
    <li><a href="{guide_url('bopomofo-teaching-order')}"><strong>ㄅㄆㄇ 教學順序</strong></a></li>
    <li><a href="{guide_url('how-to-teach-zhuyin-at-home')}"><strong>在家教注音的 7 個步驟</strong></a></li>
    <li><a href="{guide_url(HUB)}"><strong>開學前 30 天注音準備清單</strong></a></li>
  </ul>"""
    return slug, title, desc, body, faq, None


BUILDERS = [build_hub, build_xianxiu, build_how_to_teach,
            build_order, build_chart, build_blending]


def build(pages=PAGES):
    pages = os.fspath(pages)
    guides = os.path.join(pages, "guides")
    os.makedirs(guides, exist_ok=True)
    urls = []
    for fn in BUILDERS:
        slug, title, desc, body, faq, extra = fn()
        with open(os.path.join(guides, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(slug, title, desc, body, faq, extra))
        urls.append(guide_url(slug))

    # 重建 guides sitemap(與 zhuyin_grade1_guide.py 同一份,保持一致)
    pages_path = Path(pages)
    files = sorted(
        [*pages_path.glob("guides/*.html"), *pages_path.glob("*/guides/*.html")],
        key=lambda p: p.relative_to(pages_path).as_posix())
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(f"  <url><loc>{SITE}/{p.relative_to(pages_path).as_posix()}</loc></url>"
                      for p in files)
          + "\n</urlset>\n")
    with open(os.path.join(pages, "sitemap_guides.xml"), "w", encoding="utf-8") as fh:
        fh.write(sm)
    return urls


def indexnow(urls):
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
    except Exception as ex:
        print(f"  IndexNow 略過(讀不到 key): {ex}")
        return
    host = re.sub(r"^https?://", "", SITE).split("/")[0]
    payload = json.dumps({
        "host": host, "key": key, "keyLocation": f"{SITE}/{key}.txt",
        "urlList": urls + [f"{SITE}/sitemap_guides.xml"],
    }).encode()
    for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
        try:
            rq = urllib.request.Request(
                ep, data=payload,
                headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(rq, timeout=30) as r:
                print(f"  IndexNow {ep} -> HTTP {r.status}")
        except Exception as ex:
            print(f"  IndexNow {ep} -> {ex}")


def publish(urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-500:])
        return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES,
                        capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更。")
    else:
        run(["git", "-c", "user.name=alice51849",
             "-c", "user.email=alice51849@users.noreply.github.com",
             "commit", "-m",
             "Add zh-Hant back-to-school zhuyin cluster (hub + 5 topic pages)\n\n"
             "Native zh-Hant pages for the queries Taiwanese parents actually "
             "type in July-August (zhuyin xianxiu, how to teach bopomofo, "
             "teaching order, printable symbol chart, blending/jiehe yun), "
             "interlinked with the existing free zh-Hant printables. "
             "No outcome claims, no readiness verdicts, no self-ratings."],
            cwd=PAGES)
        run(["git", "pull", "--rebase", "--autostash", "-X", "theirs", "origin", "main"], cwd=PAGES)
        run(["git", "-c", "credential.helper=!gh auth git-credential",
             "push", "-q", "origin", "main"], cwd=PAGES)
    indexnow(urls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    urls = build()
    for u in urls:
        print(f"✓ {u}")
    if args.publish:
        publish(urls)
    else:
        print("(加 --publish 部署)")


if __name__ == "__main__":
    main()
