#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜尋實況意圖頁（第 3 組 13 款）→ <Guide>/<lang>/seasonal/<slug>.html。

背景：業主 2026-10-22 23:20「站在使用者的國家、受眾的角度…到底打開 APP STORE 大家會怎麼搜尋…
然後把我們適配進去」。aso/search_reality/<key>.md 依 App Store 搜尋建議與搜尋結果前 10 名，
替每款挑出最該搶的「國家 × 詞」；這支替每款的第一組寫一頁手寫內容（不是一詞一頁的模板頁），
標題與網址用使用者真的會打的字，內文回答他們搜這個詞時真正想解決的事。

規則（CLAUDE.md、ops/company/duo_claim_rules.md）：
- 功能句只取 data/<key>_full.json 該語系商店文案；不寫價格、免費、Free、Pro。
- 每頁一張主卡（＋必要時一張同系列卡），附該國商店 App Store 直連（pt＋ct＋mt）；
  ct＝gw 階梯碼 ln_<key>_<詞群>_<國>_gw（gw_campaign.py：款 × 國家 × 詞群，量不夠的格子併成 all／ww）；
  頁首放詞群標記 growth-attribution-group=sr，每日改寫照標記逐連結重算、不再蓋成 geo_*。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 每頁專屬內容：中日文 ≥450 字、英文 ≥450 個詞。
- 只寫這些頁與各語系 sitemap_seasonal_<lang>.xml 的這幾列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_g3.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_g3.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (HERE, ROOT / "social"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import android_play  # noqa: E402
import gw_campaign  # noqa: E402
import store_copy_drift  # noqa: E402
import first_party_disclosure  # noqa: E402
from app_store_storefronts import validated_app_store_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
SECTION = "seasonal"
UPDATED = "2026-10-23"
CAMPAIGN_DATE = "1023"
SEG = "sr"
PROVIDER_TOKEN = "118326163"  # 公開值：站上每個 App Store 連結的 pt= 都是它
GW_GROUP = "sr"            # gw_campaign 詞群：品類主詞
GW_META = gw_campaign.meta_tag(GW_GROUP)
MAX_CT = 30                   # app_store_storefronts.CAMPAIGN_TOKEN_RE 的上限
MIN_CJK = 450
MIN_WORDS = 450
BANNED = re.compile(r"免費|免费|無料|\bfree\b|\bpro\b|NT\$|US\$|\$\s?\d|¥\s?\d|￥|\d\s?円|\d\s?元", re.IGNORECASE)
CJK = re.compile(r"[぀-ヿ㐀-鿿]")
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")

# 頁面語系 → 商店語系（data/<key>_full.json）、App 介紹頁目錄、商店國碼、介面字。
LANGS = {
    "en": {"store": "en-US", "dir": "en-US", "cc": "us", "og": "en_US", "html": "en",
           "home": "iOS App Guide", "answers": "Answers", "about": "About", "crumb": "Guides",
           "updated": "Updated", "cta": "Download on the App Store →", "more": "Full app overview",
           "faq": "FAQ", "related": "Related pages", "toc": "On this page", "home_label": "Home"},
    "zh-Hant": {"store": "zh-Hant", "dir": "zh-Hant", "cc": "tw", "og": "zh_TW", "html": "zh-Hant",
                "home": "iOS App 指南", "answers": "答案", "about": "關於", "crumb": "推薦",
                "updated": "更新日期", "cta": "在 App Store 下載 →", "more": "看完整介紹",
                "faq": "常見問題", "related": "相關頁面", "toc": "本頁目錄", "home_label": "首頁"},
    "zh-Hans": {"store": "zh-Hans", "dir": "zh-Hans", "cc": "cn", "og": "zh_CN", "html": "zh-Hans",
                "home": "iOS App 指南", "answers": "答案", "about": "关于", "crumb": "推荐",
                "updated": "更新日期", "cta": "在 App Store 下载 →", "more": "查看完整介绍",
                "faq": "常见问题", "related": "相关页面", "toc": "本页目录", "home_label": "首页"},
    "ja": {"store": "ja", "dir": "ja", "cc": "jp", "og": "ja_JP", "html": "ja",
           "home": "iOS アプリガイド", "answers": "回答", "about": "概要", "crumb": "おすすめ",
           "updated": "更新日", "cta": "App Store でダウンロード →", "more": "アプリの詳しい紹介",
           "faq": "よくある質問", "related": "関連ページ", "toc": "目次", "home_label": "ホーム"},
}

APP_IDS = {
    "gmoney": "6755782939", "gmoneylite": "6793436548", "moneytag": "6801956402", "tripbee": "6787754435",
    "tripbeelite": "6791299610", "tripplanet": "6787193643", "cyca": "6782251621", "sononote": "6782139553",
    "savetag": "6802505528", "cvdesk": "6781337213", "onepageppt": "6798814385", "aibriefpack": "6791658210",
    "claudeusagemini": "6818607603",
}

CSS = """
:root{--bg:#f7f7fb;--card:#fff;--ink:#161622;--muted:#5d6370;--line:#e6e7ef;--brand:#5b5ff2;--ok:#0f8f5f}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Hiragino Sans","Noto Sans TC","Noto Sans JP","Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.75}
a{color:var(--brand)}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header.top{background:#fff;border-bottom:1px solid var(--line)}
.nav{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;padding:12px 16px}
.nav a{text-decoration:none;font-weight:600}
.breadcrumb{font-size:.85rem;color:var(--muted);margin:18px 0 4px}
h1{font-size:1.6rem;line-height:1.35;margin:.3rem 0 .6rem}
h2{font-size:1.2rem;margin:2rem 0 .8rem}
h3{font-size:1.02rem;margin:0 0 .35rem}
.lead{font-size:1.05rem;color:#30323d}
.updated{font-size:.82rem;color:var(--muted)}
.toc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;font-size:.92rem;margin:1rem 0}
.points{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 18px 12px 34px}
.points li{margin:.4rem 0}
.steps{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px 14px 36px}
.steps li{margin:.35rem 0}
.cards{display:grid;gap:12px}
.app{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.app p{margin:.3rem 0}
.cta{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:.5rem}
.dl{display:inline-block;background:var(--brand);color:#fff;padding:.45rem 1rem;border-radius:10px;text-decoration:none;font-weight:600;font-size:.92rem}
.android-play{font-size:.85rem;margin:.2rem 0 0}
.more{font-size:.88rem}
details.faq{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.7rem 1rem;margin:.6rem 0}
details.faq summary{cursor:pointer;font-weight:600}
.related ul{padding-left:1.2rem}
.legal{font-size:.78rem;color:var(--muted);margin:2rem 0 2.5rem}
@media (prefers-color-scheme:dark){:root{--bg:#121218;--card:#1c1c24;--ink:#ececf3;--muted:#a3a7b3;--line:#2c2d38;--brand:#8f93ff;--ok:#5fd3a0}
header.top{background:#16161d}.lead{color:#d6d8e0}}
""".strip()


class GenerationError(RuntimeError):
    """The pages cannot be published as written; nothing is written."""


# --------------------------------------------------------------------------------------------
# 頁面內容（每頁手寫；功能句對照 data/<key>_full.json 該語系商店文案）
# sections：(h2, 段落清單, 條列清單)；cards：(key, 卡片文字)；第一張是主卡。
# --------------------------------------------------------------------------------------------
PAGE_SPECS: list[dict] = [
    # 1 G+Money：台灣「旅遊記帳」「出國記帳」
    {
        "key": "gmoney", "lang": "zh-Hant",
        "slug": "lvyou-jizhang-app-chuguo-jizhang-duobibie-zhhant",
        "terms": ["旅遊記帳", "出國記帳", "旅行記帳"],
        "title": "旅遊記帳 App 怎麼選？出國記帳不亂的 5 個重點（多幣別・離線・不用帳號）",
        "desc": "出國付完錢就記、回國不用對帳：旅遊記帳 App 要看多幣別換算、離線匯率、每日上限、依旅程分組與匯出。附 G+Money 的實際用法與台灣 App Store 直連。",
        "h1": "旅遊記帳 App 怎麼選：出國記帳不亂的 5 個重點",
        "lead": "在 App Store 搜「旅遊記帳」「出國記帳」的人，多半是機票剛訂好，或人已經在國外，想找一個付完錢十秒內就能記好、回國不用再對帳的工具。",
        "intro": [
            "我們在 2026 年 10 月實際查了台灣 App Store「旅遊記帳」的搜尋結果：前 10 名裡有一半是評分不到 100 則的新 App，排第一的也只有一千多則評分。這代表大家還在找，還沒有一個公認的答案，所以挑之前更值得先想清楚自己要什麼。",
            "我們也讀了這幾款的使用者評論。最常出現的三句話是「付完錢馬上記才不會亂」「匯率顯示不出來」「可以選的幣別太少」；另一個常被忽略的問題是資料：有人換手機後舊旅程不見，有人一打開就被要求註冊帳號。出國記帳的資料只有你自己需要，存在自己的手機或自己的 iCloud 就夠了。",
        ],
        "sections": [
            ("搜「旅遊記帳」的人真正需要的 5 件事", [], [
                "用當地貨幣記、當下就看到台幣：在日本刷了一筆日圓，記下去那一刻就知道約等於多少台幣，不用回國再一筆一筆換算。",
                "沒有網路也能記、也能換算：飛機上、地鐵裡、山區，或還沒開網卡的第一天，匯率要能用上次存好的，或自己手動設定。",
                "每天能花多少一眼看到：出發前設好每日上限，才不會到最後兩天只剩便利商店的預算。",
                "一趟旅程一本帳：日本行、韓國行分開算，回國後每趟都有自己的小計；日常的咖啡和房租不要混進旅費裡。",
                "能匯出：回國後要跟旅伴對帳、或自己留存，要能匯出純文字或 CSV，不要被鎖在某個 App 裡。",
            ]),
            ("三種常見的出國情境，各自怎麼記", [
                "冬季日本自由行（12 月到 2 月）：先建立一個「東京 5 天」的旅程，母國貨幣設台幣、外幣選日圓。每天晚上回飯店看一眼當天花費和每日上限，超出了就把隔天的購物行程縮短一點，比回國才發現刷爆好得多。",
                "過年或長假出國：機票和住宿通常出發前就付清了，旅程裡要管的是「現場花的錢」。把交通、餐飲、購物、伴手禮分類記，回國時就能看出錢主要花在哪，下一趟也比較好抓預算。",
                "長住、打工度假、一路換好幾個國家：每換一個幣別就新增一個旅程，各自有圖示和顏色，總覽仍然用台幣算總額。資料存在自己的裝置上，不會因為某個服務停掉就整段消失。",
            ], []),
        ],
        "steps_title": "出發前 5 分鐘設定好",
        "steps": [
            "建立旅程：取名（例如「東京 5 天」），選一個圖示和顏色。",
            "確認母國貨幣與當地貨幣；出發前在有網路的地方打開一次，讓匯率自動更新，也可以改成自己設定的匯率。",
            "設定每日上限，之後每天都能看到「今天還能花多少」。",
            "到當地付完錢就記：輸入金額、選分類（餐飲、交通、住宿、購物、生活雜貨等），並指定到這趟旅程。",
            "回國後依旅程篩選，匯出純文字或 CSV，跟旅伴對帳或自己留存。",
        ],
        "cards": [
            ("gmoney", "G+Money 把貨幣換算和記帳放在同一個 App：50 種世界貨幣，匯率可自動更新或手動設定，完全離線也能用。記帳依分類與旅程分組，可設定每日上限、即時顯示母國貨幣總額，並匯出純文字或 CSV。無帳號、免註冊、不追蹤、無廣告；一次買斷，沒有訂閱。"),
            ("gmoneylite", "只想記一趟短程旅行、先看看順不順手？同系列的 G+Money Lite 專為旅行花費設計：用當地貨幣記每一筆，馬上看到母國貨幣金額，離線也能用。"),
        ],
        "faqs": [
            ("出國沒有網路，旅遊記帳 App 還能換算嗎？", "G+Money 的換算完全離線可用：有網路時自動更新匯率，沒有網路時用上次存好的匯率，也可以改成自己設定的匯率。"),
            ("一定要註冊帳號嗎？資料存在哪裡？", "不用註冊。資料存在你的裝置上；開啟 iCloud 同步後也會存到你自己的 iCloud，開發者不蒐集任何資訊。"),
            ("日常花費和旅行花費會混在一起嗎？", "不會。每筆消費可以指定到某個旅程，也可以不指定、當作日常消費；總覽與匯出都依旅程分組並顯示各旅程小計。"),
            ("是訂閱制嗎？", "不是。G+Money 是一次買斷，沒有訂閱。"),
        ],
        "related": [("zh-Hant/gmoney.html", "G+Money 完整介紹"), ("zh-Hant/gmoneylite.html", "G+Money Lite：旅行記帳·匯率換算"),
                    ("zh-Hant/seasonal/lianjia-chuyou-xingcheng-jizhang-fenzhang-app-zhhant.html", "連假出遊：行程、記帳、分帳 App")],
    },
    # 2 G+Money Lite：美國「vacation budget」「travel budget」「daily budget」
    {
        "key": "gmoneylite", "lang": "en",
        "slug": "vacation-budget-app-daily-spending-limit-abroad",
        "terms": ["vacation budget", "travel budget", "daily budget"],
        "title": "Vacation budget app: set a daily spending limit abroad and see it in your home currency",
        "desc": "Searching \"vacation budget\" or \"travel budget\"? What to check before you pick an app: local-currency logging, home-currency totals, offline rates and a daily limit, with a simple method that works.",
        "h1": "Vacation budget app: how to set a daily limit abroad and actually stick to it",
        "lead": "People who type \"vacation budget\" into the App Store are usually a few days away from a trip, or already on one, and want to answer one question: how much can I spend today without wrecking the rest of the trip?",
        "intro": [
            "We looked at the US App Store results for \"vacation budget\", \"travel budget\" and \"daily budget\" in October 2026. Several of the top ten apps have fewer than a dozen ratings, which tells you the space is still wide open and nobody has nailed the simple version yet. The reviews of the popular travel budget apps keep pointing to the same needs: log in the local currency, see the total in dollars, and keep working when there is no signal, whether that is a cruise ship, a plane or a mountain road.",
            "The other recurring complaint is accuracy. Card and cash rates differ from the mid-market rate you see online, so an app that hides where its rate comes from will quietly drift. A good budget tool tells you which rate it uses and lets you set your own when you know better, for example after you changed cash at the airport.",
        ],
        "sections": [
            ("What a vacation budget app needs to do", [], [
                "Log each purchase in the currency you actually paid in, so you are not doing mental math at the register.",
                "Show that amount in your home currency right away, so a dinner bill in yen or euros means something.",
                "Keep working offline with saved rates, or with a rate you set yourself.",
                "Offer an optional daily limit, so you notice overspending on day two instead of on the last day.",
                "Keep each trip separate, with categories and filters, so a weekend away does not blur into everyday spending.",
                "Let you back up and restore, so a new phone does not erase the trip you are on.",
            ]),
            ("A simple daily-limit method that works", [
                "Start with your spending money for the trip, after flights and the hotel are paid. Keep back a small buffer for one surprise day, such as a taxi in the rain or a ticket you did not plan, then divide the rest by the number of days. That number is your daily limit.",
                "Each evening, glance at today against the limit. Spent less? Good, tomorrow has a little room. Spent more? Make tomorrow a lighter day, with a picnic lunch and a long walk instead of a paid attraction. The goal is not to record every cent for the rest of your life; it is to notice early enough that the last two days of the trip are still fun.",
                "This works just as well for a long weekend as for a three-week tour. Short trips are where people skip budgeting entirely, and they are also where a single expensive dinner can eat half of the plan.",
            ], []),
        ],
        "steps_title": "Set it up before you leave",
        "steps": [
            "Create the trip and choose your home currency.",
            "Open the app once on Wi-Fi so it fetches the latest rates (it refreshes about every six hours when you open it); you can also set a rate manually.",
            "Turn on the optional daily limit and enter the number you worked out above.",
            "During the trip, log each purchase right after you pay, in the local currency, and pick a category.",
            "At night, check the day against the limit; back home, keep a backup of the trip.",
        ],
        "cards": [
            ("gmoneylite", "G+Money Lite logs each purchase in the local currency and shows it instantly in your home currency, online or off. Rates are fetched automatically or set by you, using the mid-market reference rate (cards and cash may differ). You get an optional daily limit, categories, trips, filters, records, a widget and an Apple Watch app, plus backup and restore. Everything stays on your device: no account, no tracking. One payment unlocks unlimited expenses and trips, with no subscription."),
            ("gmoney", "Want one app for everyday spending and travel? G+Money combines a currency converter for 50 currencies with a category budget, trips and a daily limit, fully offline, with no account."),
        ],
        "faqs": [
            ("Does a travel budget app work without internet?", "G+Money Lite does. It fetches the latest rates when it can and always works offline with your saved rates, or with a rate you set manually."),
            ("Which exchange rate does it use?", "The mid-market reference rate from a public exchange-rate service. Your card or cash rate may differ, so you can switch to a manual rate whenever you like."),
            ("Do I need an account?", "No. Everything stays on your device, with no account and no tracking."),
            ("Is it a subscription?", "No. One payment unlocks unlimited expenses and trips, with no subscription."),
        ],
        "related": [("en-US/gmoneylite.html", "G+Money Lite: full overview"), ("en-US/gmoney.html", "G+Money: spending and budget"),
                    ("en/seasonal/best-iphone-apps-summer-travel-2026.html", "Travel apps for iPhone")],
    },
    # 3 MoneyTag：日本「副業 収支」
    {
        "key": "moneytag", "lang": "ja",
        "slug": "fukugyou-shuushi-kanri-app-anken-goto",
        "terms": ["副業 収支", "フリーランス 収支", "収支"],
        "title": "副業の収支管理アプリの選び方｜案件ごとに「本当の利益」を見る方法",
        "desc": "「副業 収支」で探している人へ。案件・プロジェクトごとに帳簿を分け、収入−支出の純額を見る方法と、アプリで確認したい5つのポイント。MoneyTagの使い方つき。",
        "h1": "副業の収支管理：案件ごとに「本当の利益」を見る方法",
        "lead": "App Storeで「副業 収支」と検索する人の多くは、本業のほかにフリマでの販売、ハンドメイド、ライター、配達などを掛け持ちしていて、「結局どれがいくら残っているのか」が分からなくなっている人です。",
        "intro": [
            "2026年10月に日本のApp Storeで「副業 収支」の検索結果を確認すると、上位には副業専用の収支メモアプリと、大手の家計簿アプリが並んでいました。家計簿アプリは生活費の管理には便利ですが、副業の案件ごとに収入と経費を分けて「この案件はいくらの黒字なのか」を見るのはあまり得意ではありません。",
            "副業の収支でつまずくポイントは、だいたい次の三つです。複数の案件の売上と経費が一つのリストに混ざること、材料費や交通費などの経費を後から思い出せないこと、そして年末にまとめて計算しようとして、どの案件が利益を出しているのか分からなくなることです。",
        ],
        "sections": [
            ("副業の収支を「案件ごと」に分けるべき理由", [
                "売上が多い案件と、利益が残る案件は同じとは限りません。たとえば販売の副業は売上が大きく見えても、仕入れや送料、梱包材を引くと手元に残る金額は意外と小さいことがあります。逆に、ライティングのように経費が少ない仕事は、売上が小さくても利益率が高いことがあります。",
                "案件ごとに帳簿を分けて「収入−支出＝純額」を見ると、時間をかける価値がある案件と、そうでない案件がはっきりします。来年どの副業を続けるかを決めるときの、いちばん確かな材料になります。",
            ], []),
            ("アプリで確認したい5つのポイント", [], [
                "案件ごとに独立した帳簿を作れるか（取引・通貨・収支が混ざらないか）。",
                "収入から支出を引いた純額が、案件ごとにすぐ見えるか。",
                "タグで案件をまたいだ集計ができるか（交通費や材料費が全体でいくらかかったか）。",
                "海外のクライアントや外貨の案件にも対応しているか（案件ごとの通貨、自動または手動の為替レート）。",
                "CSVやPDFへの書き出しとバックアップができ、端末を替えても帳簿を移せるか。",
            ]),
            ("年末のふり返りにも", [
                "年末にまとめて見直すときも、案件ごとの純額が出ていれば、どこに経費がかかったのか、どの案件が伸びたのかを短時間で確認できます。税金の扱いについては、税務署の案内や専門家に確認してください。アプリは数字を整理する道具であり、税務の判断はしません。",
            ], []),
        ],
        "steps_title": "今日から始める手順",
        "steps": [
            "副業の案件ごとにプロジェクトを作る（例：「ハンドメイド販売」「Webライター」）。",
            "収入と支出は発生したその場で入力し、「材料費」「交通費」などのタグを付ける。",
            "週に一度、各プロジェクトの純額（収入−支出）を確認する。",
            "タグ画面で、同じタグの収入・支出・純額を案件横断で見る（買い切り版の機能）。",
            "月末にCSVやPDFで書き出し、バックアップを取っておく（買い切り版の機能）。",
        ],
        "cards": [
            ("moneytag", "MoneyTagはプロジェクトごとに帳簿が独立し、収入から支出を引いた純額をすぐ表示します。タグは収入にも支出にも付けられ、タグ画面では同じタグの収入・支出・純額を全プロジェクト横断で集計できます（買い切り版）。1プロジェクトに1通貨、自動または手動の為替レート、iPhoneとiPadで同じ帳簿、Apple Watchアプリ、ホーム画面・ロック画面ウィジェットに対応。データは端末内に保存され、買い切りでずっと使えます。"),
        ],
        "faqs": [
            ("家計簿アプリとの違いは？", "家計簿は生活全体のお金を見るためのものです。MoneyTagは案件・プロジェクトごとに帳簿を分け、その案件だけの純額を表示することに特化しています。"),
            ("外貨で支払われる案件にも使えますか？", "はい。各プロジェクトに基準通貨があり、入力通貨を選べます。為替レートは約6時間ごとに自動更新され、手動レートに切り替えることもできます。"),
            ("データはどこに保存されますか？", "プロジェクト、取引、金額、メモ、タグなどは端末内に保存されます。iCloud同期をオンにすると、あなた自身のiCloudにもコピーが保存されます。"),
            ("サブスクリプションですか？", "いいえ。無制限のプロジェクト・タグ・レポートや書き出しは、買い切りでずっと使えます。"),
        ],
        "related": [("ja/moneytag.html", "MoneyTag の詳しい紹介")],
    },
    # 4 TripBee：台灣「旅遊行程」「行程規劃」「旅遊規劃」
    {
        "key": "tripbee", "lang": "zh-Hant",
        "slug": "lvyou-xingcheng-guihua-app-jiutuan-gongbian-zhhant",
        "terms": ["旅遊行程", "行程規劃", "旅遊規劃"],
        "title": "旅遊行程規劃 App：揪團出國，大家一起編同一份行程（打包清單・雨天備案・離線）",
        "desc": "搜「旅遊行程」「行程規劃」的主揪看這裡：揪團出國最常卡在版本混亂、時區轉機、天氣變化與打包遺漏。挑行程 App 要看的 6 件事，附 TripBee 的用法與台灣 App Store 直連。",
        "h1": "揪團出國的旅遊行程規劃：一份行程，大家一起編",
        "lead": "在 App Store 搜「旅遊行程」「行程規劃」的人，很多是揪團的主揪：群組裡每個人都傳一版行程，改到最後沒人知道哪一份才是最新的。",
        "intro": [
            "2026 年 10 月我們查了台灣 App Store「旅遊行程」與「旅遊規劃」的搜尋結果：前 10 名裡有好幾個評分不到 100 則的新 App，也有主打 AI 自動排行程的工具。但對揪團的人來說，最常卡住的通常不是「排不出行程」，而是「大家看的不是同一份」。",
            "國外大型行程 App 的使用者評論也反映同樣的事：最常被稱讚的是把訂位資料整理在一起，最常被抱怨的是分享只能靠 email、而且常常失敗；另一個抱怨是付了訂閱費，功能卻沒跟上。換句話說，大家要的是一份能一起改、出國沒網路也看得到、而且不用每個月付費的行程表。",
        ],
        "sections": [
            ("揪團行程最常出問題的 4 個地方", [], [
                "版本混亂：群組裡傳截圖、傳試算表、傳文字，每個人手上的版本都不一樣，集合時間一改就有人沒跟上。",
                "時區與轉機：多城市、跨國轉機時，航班時間到底是哪個時區，常常要再查一次。",
                "天氣變化：遇到下雨或颱風，整天的行程要重排，臨時才想備案最手忙腳亂。",
                "打包遺漏：每個旅伴、每個孩子要帶的東西不一樣，證件、藥品、充電器最容易漏。",
            ]),
            ("挑旅遊行程規劃 App 要看的 6 件事", [], [
                "能不能邀請旅伴一起查看、一起編輯同一份旅程。",
                "逐日時間軸是否能放航班、飯店、餐廳與活動，並記錄時間、時區、地址、備註與提醒。",
                "出國沒有網路時，行程還能不能看、能不能改。",
                "能不能一鍵開地圖導航，到景點、飯店、機場或集合地點。",
                "能不能把既有的表格或備忘錄匯入，換手機時能不能完整備份還原。",
                "資料放在哪裡：有沒有私密同步、開發者能不能看到你的旅行資料。",
            ]),
            ("春節、寒假多城市行程的排法", [
                "多城市行程建議以「每一天」為單位排：早上從哪裡出發、中午在哪一站、晚上住哪裡。轉機那天把航班時區寫清楚，抵達後的第一個行程安排得鬆一點。每一天都先想好一個室內的雨天備案，真的下雨時，只要把當天換成備案，群組裡大家看到的就是同一份新行程。",
                "出發前一週再做一次打包清單：依天數、季節和每位旅伴（包含孩子年齡）分開列，證件、藥品、充電器放最前面。出發前把整趟行程做成一張海報分享到群組，讓還沒裝 App 的家人也知道大概的安排。",
            ], []),
        ],
        "steps_title": "主揪 10 分鐘把揪團行程建好",
        "steps": [
            "建立旅程，逐日放進航班、飯店、餐廳與活動，填好時間、時區與地址。",
            "啟用 iCloud 後邀請旅伴，受邀者可以查看並編輯同一份共享旅程。",
            "每天先看天氣，替戶外行程準備一個室內備案。",
            "產生打包清單，依天數、季節、每位旅伴與孩子年齡分開確認。",
            "出發前做一張旅程海報分享給同行者；當地沒網路時，核心行程照樣可以離線查看。",
        ],
        "cards": [
            ("tripbee", "TripBee 以逐日時間軸整理航班、飯店、餐廳與活動，記錄時間、時區、地址、備註與提醒；啟用 iCloud 後可邀請他人查看及編輯共享旅程。智慧打包清單依天數、季節、每位家庭成員與孩子年齡自動產生；可先看天氣安排雨天備案、一鍵開 Apple 地圖導航、做旅程海報、CSV 匯入與本機備份還原。核心旅程規劃可離線使用；一次購買，無廣告、無追蹤。"),
            ("tripbeelite", "只有一趟旅程、想要更簡單？TripBee Lite 專注在下一趟旅程，把航班、住宿與行程排成每日時間軸，免帳號、無廣告。"),
        ],
        "faqs": [
            ("旅伴可以一起改行程嗎？", "可以。啟用 iCloud 後邀請他人，受邀者可以查看及編輯共享旅程；儲存、同步與通知由 Apple 處理。"),
            ("出國沒有網路還看得到行程嗎？", "可以。TripBee 的核心旅程規劃可離線使用。"),
            ("開發者看得到我們的旅行資料嗎？", "看不到。資料存在你的私人 iCloud，開發者沒有旅行資料伺服器，也無法存取這些內容。"),
            ("帶小孩出門，有適合孩子的 App 嗎？", "可以看同系列的 Trip Planet 親子旅行遊戲：把搭機、搭車、住飯店變成孩子能完成的小任務。"),
        ],
        "related": [("zh-Hant/tripbee.html", "TripBee 完整介紹"), ("zh-Hant/tripbeelite.html", "TripBee Lite：旅程規劃"),
                    ("zh-Hant/tripplanet.html", "Trip Planet 親子旅行遊戲"),
                    ("zh-Hant/seasonal/lianjia-chuyou-xingcheng-jizhang-fenzhang-app-zhhant.html", "連假出遊：行程、記帳、分帳 App")],
    },
    # 5 TripBee Lite：日本「旅のしおり」「旅程」
    {
        "key": "tripbeelite", "lang": "ja",
        "slug": "tabi-no-shiori-app-ryoteihyou-tsukurikata",
        "terms": ["旅のしおり", "旅程", "旅行 計画"],
        "title": "旅のしおりアプリの作り方｜予約メール・スクショを1日ごとの旅程表にまとめる",
        "desc": "「旅のしおり」で探している人へ。航空券・ホテル・チケットの情報が散らばっていても、1日ごとの旅程表にまとめるコツと、しおりに入れておきたい項目。TripBee Liteの使い方つき。",
        "h1": "旅のしおりをアプリで作る：予約情報を1日ごとの旅程表に",
        "lead": "App Storeで「旅のしおり」と検索する人の多くは、航空券は予約メール、ホテルは予約サイト、チケットはスクショ…と情報が散らばっていて、それを一つの旅程表にまとめたい人です。",
        "intro": [
            "2026年10月に日本のApp Storeで「旅のしおり」を検索すると、上位には共有型のしおり作成アプリや、観光スポット検索と一体になったアプリが並んでいました。グループで作り込むなら便利ですが、「次の帰省や旅行の予定を、自分のために1画面で見たい」だけなら、機能が多すぎると感じる人も少なくありません。",
            "海外の大手旅行計画アプリのレビューでも、いちばんほめられていたのは「予約情報が一か所にまとまること」と「シンプルさ」でした。しおりに本当に必要なのは、日ごとの時間の流れと、その場で必要な情報（便名、予約番号、住所、メモ）がすぐに出てくることです。",
        ],
        "sections": [
            ("旅のしおりに入れておきたい項目", [], [
                "日ごとの時間の流れ：何時にどこを出て、どこへ向かうか。",
                "フライトや新幹線：便名、出発時刻、座席、乗り換え。",
                "宿泊：ホテル名、住所、チェックイン時刻、予約番号。",
                "予定とチケット：入場時間、予約番号、受け取り方法。",
                "メモとリマインダー：持ち物、集合場所、出発前にやること。",
            ]),
            ("年末年始の帰省・温泉旅行での使い方", [
                "年末年始の帰省は、新幹線の時刻、実家への到着時間、親戚との予定、温泉宿のチェックインなど、細かい時刻がいくつも重なります。予約メールを毎回探す代わりに、出発の数日前に日ごとのタイムラインへ並べておくと、当日は画面を一つ見るだけで済みます。",
                "連休の温泉旅行なら、1日目は移動とチェックイン、2日目は観光、3日目はチェックアウトと帰りの便、というように一日ずつ組み立てます。チケットの情報や予約番号は、その予定の中にメモしておくと、窓口や受付でスクショを探さずに済みます。",
                "旅が終わったら、その旅程は次の旅に入れ替えて使えます。毎回ゼロから作るより、前回の流れを参考にできるので準備が早くなります。",
            ], []),
        ],
        "steps_title": "しおりを作る手順",
        "steps": [
            "次の旅を一つ作り、日付を入れる。",
            "日ごとのタイムラインに、フライト、宿泊、予定を時間順に並べる。",
            "予約番号やチケット情報、住所はそれぞれの予定のメモにまとめる。",
            "出発前日や集合時刻にリマインダーを設定する。",
            "旅が終わったら、次の旅に入れ替えて使う。",
        ],
        "cards": [
            ("tripbeelite", "TripBee Liteは、いま準備する一つの旅をすっきり整える旅行プランナーです。日ごとのタイムラインにフライト、宿泊、予定を並べ、メモ、リマインダー、チケット情報も必要な場所にまとめられます。アカウント登録は不要で、広告、解析、トラッキングはありません。旅の保存件数無制限、共有、完全なバックアップと復元、スマート持ち物リストは一度の購入で使え、サブスクリプションではありません。"),
            ("tripbee", "家族や友達と同じ旅程を共同編集したいなら、TripBeeは共有旅程の共同編集、雨の日の代案づくり、持ち物リストに対応しています。"),
        ],
        "faqs": [
            ("アカウント登録は必要ですか？", "不要です。広告、解析、トラッキングもなく、旅の計画は自分で管理できます。"),
            ("複数の旅を同時に保存できますか？", "一度に1件の旅を保存して、次の旅へ入れ替えながら使えます。保存件数無制限は一度の購入で使えます。"),
            ("家族と一緒に編集したいときは？", "共同編集が必要なら、同じシリーズのTripBeeが共有旅程の共同編集に対応しています。"),
            ("サブスクリプションですか？", "いいえ。一度の購入で、アプリの提供期間中ずっと利用できます。"),
        ],
        "related": [("ja/tripbeelite.html", "TripBee Lite の詳しい紹介"), ("ja/tripbee.html", "TripBee の詳しい紹介")],
    },
    # 6 Trip Planet：美國「road trip games」「kids travel games」
    {
        "key": "tripplanet", "lang": "en",
        "slug": "road-trip-games-for-kids-car-ride-missions",
        "terms": ["road trip games", "kids travel games", "airplane games for kids"],
        "title": "Road trip games for kids: car-ride missions that beat \"Are we there yet?\"",
        "desc": "Looking for road trip games for kids this Thanksgiving? Why small real-world missions work better than another screen game for ages 3 to 10, an hour-by-hour drive plan, and how Trip Planet sets the missions.",
        "h1": "Road trip games for kids that are not just another screen",
        "lead": "Parents who search \"road trip games\" in November are usually counting the hours of a Thanksgiving drive and wondering how a five-year-old is going to survive them, and how they will survive the five-year-old.",
        "intro": [
            "We checked the US App Store results for \"road trip games\" and \"kids travel games\" in October 2026. Most of the top results for \"road trip games\" are party games for adults and teens, such as would-you-rather questions and timed trivia. The options built for younger kids are mostly cartoon driving games. They are fine for a few minutes, but they keep a child looking down at a screen for the whole drive, and the questions start again the moment the battery runs out.",
            "What works better for ages three to ten is a goal they can finish in the real world: spot three red cars, try a new snack at the rest stop, say thank you to the person at the counter. Small, finishable missions give a child something to look forward to, and a reward at the end turns the long drive into a story they helped write.",
        ],
        "sections": [
            ("What actually works on long drives with kids aged 3 to 10", [], [
                "Short missions with a clear end, so a child feels the win every twenty or thirty minutes.",
                "Look-outside missions: colours, animals, signs and landmarks keep eyes out of the window instead of on a screen.",
                "Bravery and kindness missions for the stops: ordering their own snack, greeting a relative, trying a new food.",
                "A reward they can collect, so finishing a mission feels like progress rather than a chore.",
                "A keepsake at the end of the trip, so the drive becomes a memory instead of something to forget.",
            ]),
            ("A Thanksgiving drive, hour by hour", [
                "Before you leave: pick two or three missions per hour of driving, and keep a couple in reserve for traffic. Tell your child the plan the night before, because a drive with a map of challenges feels shorter than a drive with no end in sight.",
                "First hour: easy look-outside missions while everyone is still fresh. At the first stop: a bravery or kindness mission, such as paying for a snack or saying thank you. Middle of the drive: a quiet mission, such as drawing something they saw, while a younger sibling naps. Last hour: the big reward is close, so save the most exciting mission for the final stretch.",
                "On arrival, let your child see what they completed. A passport stamp or a short story card of the trip is something grandparents love to see, and it gives the drive home a head start.",
            ], []),
        ],
        "steps_title": "Set up the missions in five minutes",
        "steps": [
            "Create the trip the night before and choose the Mission Packs that fit: car rides, food, kindness, bravery and memories.",
            "Add a second parent so both of you can follow the trip from your own phones.",
            "In the car, open one mission at a time and let your child tell you when it is done.",
            "Celebrate each finished mission with the reward unlock, then put the phone away until the next one.",
            "When you arrive, look at the trip together and share the Trip Story Card with family.",
        ],
        "cards": [
            ("tripplanet", "Trip Planet turns family trips into small real-world missions for kids ages 3 to 10: Mission Packs for flight days, hotels, food, museums, kindness, bravery and memories, with collectible rewards on a constellation adventure map, Travel Passport stamps for completed trips and auto-generated Trip Story Cards to share as keepsakes. Mom, dad and grandparents can share one trip through iCloud, each from their own device. No ads and no third-party tracking; purchases and sharing sit behind a parent gate. It is a one-time purchase, not a subscription."),
        ],
        "faqs": [
            ("Is this another screen-time game?", "No. The missions happen in the real world, outside the window, at the rest stop or at the table. The app sets the mission and celebrates it when your child finishes."),
            ("What ages is Trip Planet for?", "It is designed for kids aged 3 to 10, with missions that a parent can read aloud for younger children."),
            ("Can grandparents follow the trip?", "Yes. iCloud co-parent sharing works for mom, dad and grandparents, each from their own device."),
            ("Are there ads or in-app tricks?", "There are no ads and no third-party tracking. Purchases and sharing sit behind a parent gate, and it is a one-time purchase, not a subscription."),
        ],
        "related": [("en-US/tripplanet.html", "Trip Planet: full overview"), ("en-US/tripbee.html", "TripBee: group trip planner"),
                    ("en/seasonal/best-iphone-apps-summer-travel-2026.html", "Travel apps for iPhone")],
    },
    # 7 Cyca：美國「period tracker」（private／no account）
    {
        "key": "cyca", "lang": "en",
        "slug": "private-period-tracker-no-account-offline",
        "terms": ["period tracker", "private period tracker", "ovulation tracker"],
        "title": "Private period tracker: no account, no cloud, works offline (what to check first)",
        "desc": "Searching for a period tracker that keeps your data private? Five questions to ask any period app about accounts, storage, offline use and predictions, and how Cyca keeps everything on your iPhone.",
        "h1": "A private period tracker: what \"private\" should actually mean",
        "lead": "Searches such as \"period tracker\" and \"ovulation tracker\" come from people who want predictions they can plan their weeks around, without handing their cycle to somebody else's servers.",
        "intro": [
            "We looked at the US App Store results for \"period tracker\" and \"ovulation tracker\" in October 2026. The top results are large, well-known apps with hundreds of thousands of ratings. Their recent reviews keep returning to the same complaints: features moving behind a subscription, being asked to create an account, and losing history after switching phones. In one recent sample of fifty reviews for a leading app, seven were about subscriptions.",
            "\"Private\" can mean very different things in an app listing. Some apps encrypt data but still store it on their own servers. Some let you skip an account at first but push you to create one later. Before you log anything as personal as your cycle, it is worth asking a few plain questions and reading the answers in the app description, not just the screenshots.",
        ],
        "sections": [
            ("Five questions to ask any period app", [], [
                "Do I need an account? If the answer is yes, your history lives with the company, not with you.",
                "Where is my data stored? On the phone only, in your own cloud, or on the developer's servers?",
                "Does it work offline? An app that works in airplane mode is usually not sending your logs anywhere.",
                "How are predictions made, and are they labelled as estimates rather than medical advice?",
                "What does it cost over time? A single lifetime purchase and a monthly subscription feel very different after two years.",
            ]),
            ("Planning your weeks around your cycle", [
                "The most practical use of a cycle calendar is planning. Before the holidays, a trip or a long week at work, a look at the calendar shows your next expected period, your estimated fertile window and the days when you are likely to want an easier schedule. A heads-up a day or two before your period or PMS helps you pack, plan and be a little kinder to yourself.",
                "Logging only works if it is quick. Recording flow, symptoms, mood and a note should take a tap or two, so that it becomes a habit rather than homework. Over a few cycles, your own patterns start to appear, and predictions get more personal as the app learns your rhythm.",
                "One important limit: cycle predictions are wellness estimates. They are not a medical device and not a form of contraception. If something feels wrong, talk to a doctor.",
            ], []),
        ],
        "steps_title": "Getting started in two minutes",
        "steps": [
            "Log the first day of your current or last period.",
            "Each day, record flow, symptoms, mood or a note in a tap.",
            "Check the calendar for your next period, fertile window and ovulation estimate.",
            "Read the Daily Body Forecast in the morning for a gentle idea of how today may feel.",
            "Use the Smart Planner to spot your best and gentlest days before you plan the week.",
        ],
        "cards": [
            ("cyca", "Cyca turns your period and cycle into calm clarity: log your day in a tap, read a gentle Daily Body Forecast, and look ahead to your next period, fertile window and ovulation on a soothing calendar. Smart, personal predictions adapt every time you log, and the Smart Planner highlights your best and gentlest days. Cyca has no servers and no account; your data never leaves your device and the app works fully offline. Future predictions, Personal Rhythm, the Smart Planner and full calendar history come with a single lifetime purchase, never a subscription. Cyca provides wellness and planning estimates and is not a medical device or a form of contraception."),
        ],
        "faqs": [
            ("Does Cyca need an account?", "No. There is no account and there are no Cyca servers. Your data never leaves your device."),
            ("Does it work offline?", "Yes. Cyca works fully offline, including logging, the calendar and predictions."),
            ("Can I use the predictions as contraception?", "No. Cyca provides wellness and planning estimates and is not a medical device or a form of contraception."),
            ("Is Cyca a subscription?", "No. Predictions, Personal Rhythm, the Smart Planner and full history come with a single lifetime purchase, never a subscription."),
        ],
        "related": [("en-US/cyca.html", "Cyca: full overview"),
                    ("en/seasonal/best-iphone-privacy-apps-end-of-year-2026.html", "Privacy apps for iPhone")],
    },
    # 8 Sono Note：台灣「錄音轉文字」「語音轉文字」「逐字稿」
    {
        "key": "sononote", "lang": "zh-Hant",
        "slug": "luyin-zhuan-wenzi-app-huiyi-ketang-zhaiyao-zhhant",
        "terms": ["錄音轉文字", "語音轉文字", "逐字稿"],
        "title": "錄音轉文字 App 怎麼選？開會、上課錄音變逐字稿＋重點摘要＋待辦",
        "desc": "搜「錄音轉文字」「語音轉文字」「逐字稿」的人，要的通常不是一大段原始文字，而是能直接用的筆記。挑選時要看的 5 件事、三種場合的錄法，附 Sono Note 的用法與台灣 App Store 直連。",
        "h1": "錄音轉文字：開會、上課後，直接拿到摘要、重點與待辦",
        "lead": "在 App Store 搜「錄音轉文字」「語音轉文字」「逐字稿」的人，通常剛開完會、剛下課，或手上有一段採訪錄音，想要的不是一大段原始文字，而是能直接拿去用的筆記。",
        "intro": [
            "2026 年 10 月台灣 App Store「錄音轉文字」前幾名，多是專做逐字稿的 App。逐字稿很完整，但一小時的會議轉出來是上萬字，最後還是得自己從頭讀一遍、自己整理重點。國外同類 App 的使用者評論裡，最常出現的使用情境是會議、上課與工作，最常見的抱怨則是錄音長度與次數的限制，以及轉寫失敗。",
            "所以挑錄音轉文字 App 前，先想清楚你要的是哪一種結果：要一字不漏的逐字稿（例如訪談、字幕），還是要一份整理好的筆記（例如會議結論、上課重點、要做的事）。後者需要的不只是轉寫，還有摘要、重點與待辦的整理。",
        ],
        "sections": [
            ("選錄音轉文字 App 要看的 5 件事", [], [
                "準確度：單一說話者、聲音清楚的錄音最準；多人同時講話時，任何工具的準確度都會下降。",
                "隱私：錄音會不會上傳到開發者的伺服器？能不能選擇只在手機上處理？",
                "整理能力：除了逐字稿，能不能直接產生摘要、重點、待辦清單，甚至追蹤信的草稿。",
                "匯出：能不能匯出成文字、Markdown 或 PDF，貼到報告、筆記或寄給同事。",
                "錄音長度：一堂課或一場會議常常超過一小時，要確認長錄音能不能完整處理。",
            ]),
            ("會議、課堂、採訪：三種場合怎麼錄", [
                "會議：手機放在桌子中間、靠近主要發言的人；會後先看摘要與待辦清單，確認負責人與期限，再用追蹤信草稿寄給大家，十分鐘就能把會議結論發出去。",
                "上課：坐前排、靠近老師；下課後先看重點，再用原始錄音重聽沒聽懂的段落。考前把每堂課的重點匯出整理成一份複習講義。",
                "採訪與訪談：先徵得對方同意再錄音；採訪結束後用逐字稿核對引述，再用摘要快速整理出報導或研究筆記的架構。",
            ], []),
        ],
        "steps_title": "第一次使用的步驟",
        "steps": [
            "選一個範本：工作更新、客戶電話、課堂、面試、就醫、創意等。",
            "按下錄音，自然地說話，或錄下會議、上課的內容。",
            "結束後看摘要、重點與行動項目，需要時重播原始錄音核對。",
            "選擇語氣，產生追蹤信草稿，確認內容後寄出。",
            "以文字、Markdown 或 PDF 匯出，分享給同事或存進筆記。",
        ],
        "cards": [
            ("sononote", "Sono Note 把錄音轉錄並整理成一份完成的筆記：清晰的摘要、重點、行動項目，以及依你選擇的語氣草擬的後續郵件；隨時可以在筆記中重播原始錄音，並以文字、Markdown 或 PDF 匯出。現成範本適用於工作更新、客戶電話、課堂、面試、就醫、創意與專案回顧，支援數十種語言。筆記都存在你的 iPhone 上，無需帳號、無廣告、無追蹤；切換到「僅限本機」模式，所有處理都留在裝置上，飛航模式下也能使用。"),
        ],
        "faqs": [
            ("錄音會上傳到開發者的伺服器嗎？", "不會。Sono Note 沒有自己的伺服器。語音轉文字使用 Apple 語音辨識，部分語言可能會把音訊傳送給 Apple；切換到「僅限本機」模式，所有處理都留在你的裝置上。"),
            ("支援中文嗎？", "支援。Sono Note 支援數十種語言，隨時可以切換。"),
            ("轉出來的文字準不準？", "最清晰的結果來自清晰、單一說話者的錄音。生成的文字需要經過你的確認後再使用。"),
            ("可以匯出嗎？", "可以以文字、Markdown 或 PDF 格式匯出，也能把所有資料備份成單一檔案並一鍵還原。"),
        ],
        "related": [("zh-Hant/sononote.html", "Sono Note 完整介紹")],
    },
    # 9 SaveTag：美國「read later」「bookmark manager」「link saver」
    {
        "key": "savetag", "lang": "en",
        "slug": "read-later-app-save-links-from-any-app",
        "terms": ["read later", "bookmark manager", "link saver"],
        "title": "Read-later app that works from any app: save links, auto-tag them, actually read them",
        "desc": "\"Read later\" is the first thing the App Store suggests when you type it. What to look for in a read-later app in 2026: share sheet from any app, automatic tags, search by idea, a habit that brings you back, and export.",
        "h1": "The read-later app for people who save more than they read",
        "lead": "\"Read later\" is the first suggestion the US App Store shows as you type it, and the people searching for it usually share one problem: links saved everywhere, read nowhere.",
        "intro": [
            "We looked at the US App Store results for \"read later\", \"bookmark manager\" and \"link saver\" in October 2026. Among the top ten for \"read later\", one long-running app has a few thousand ratings and most of the others have almost none, which means a lot of people are still looking for a home for their links. Reading the reviews of the established apps, a clear pattern appears: people searching for a replacement after a read-later service they relied on shut down, frustration with yearly fees, share sheets that crash, and slow syncing.",
            "And one thing keeps people loyal when it works: being able to come back. As one reviewer put it, they save articles because they do not have time to read right now, so they can go back later. The whole point of a read-later app is the later part.",
        ],
        "sections": [
            ("Why saved links turn into a black hole", [
                "You send yourself a recipe from a friend, a jacket you liked, a video you promised to watch and a thread you wanted to reread. They land in chats, notes, screenshots and browser tabs. A month later you remember the idea but not where it went, and searching your messages for \"that link\" rarely works.",
                "Most bookmark tools solve the saving part and stop there. A list that only grows is not a reading list; it is a pile. What changes the habit is sorting that happens without effort, and a small daily nudge that brings a few saves back in front of you.",
            ], []),
            ("What to look for in a read-later app", [], [
                "Save from any app through the share sheet, plus a quick save from the clipboard.",
                "Automatic tags the moment a link lands, so shopping, recipes, travel and work do not mix.",
                "Search that finds the idea, not just the exact words you typed.",
                "A reason to come back: a few unread saves each day, with a goal and a streak.",
                "Export to an open format, so your saves are never locked in.",
                "Privacy you can check: no account, no cloud copy you did not ask for, no ads.",
            ]),
            ("Moving on from an old read-later app", [
                "You do not have to migrate years of saves to start fresh. Begin with what you are saving this week: share every new link to one place and let the tags sort it. Keep your old export as an archive file. Within a couple of weeks, the new list is the one you actually use.",
            ], []),
        ],
        "steps_title": "Build the habit in a week",
        "steps": [
            "Add SaveTag to the top of your share sheet so saving is one tap from any app.",
            "Save everything you mean to come back to: articles, videos, posts, recipes, products.",
            "Let the automatic tags sort each save, and add a custom tag only when you need your own system.",
            "Open Rediscover once a day and clear the small handful of saves it shows you.",
            "Use search with whatever you remember, such as \"that pasta from last week\".",
        ],
        "cards": [
            ("savetag", "SaveTag gives every link one home and does the filing for you. Share any link into SaveTag from any app, or quick-save from the clipboard; the title, site and preview are pulled in. Every save is tagged on your device the moment it lands, search runs across titles, notes, tags and sources, and Rediscover surfaces a small handful of unread saves each day with a goal ring and a streak. No account, no cloud, no ads, no tracking: your saves never leave your device. Unlimited saves, custom tags, Markdown export and backup come with a one-time in-app purchase. No subscription, ever."),
        ],
        "faqs": [
            ("Do I need an account?", "No. SaveTag has no account and no cloud, and your saves never leave your device."),
            ("Is SaveTag an AI chatbot?", "No. Tagging runs on Apple's on-device text intelligence to file your saves. It is not a chatbot and it never writes content for you."),
            ("Can I get my saves out later?", "Yes. Markdown export and backup are part of the one-time purchase, so your saves are never locked in."),
            ("Is there a subscription?", "No subscription, ever. SaveTag uses a one-time in-app purchase."),
        ],
        "related": [("en-US/savetag.html", "SaveTag: full overview")],
    },
    # 10 CV Desk：美國「ats resume」「resume builder」
    {
        "key": "cvdesk", "lang": "en",
        "slug": "ats-resume-checker-iphone-score-and-fix",
        "terms": ["ats resume", "resume builder", "ats resume checker"],
        "title": "ATS resume checker on iPhone: score your resume and fix what gets it auto-rejected",
        "desc": "Applied everywhere and heard nothing back? Why applicant tracking systems fail to read many resume templates, a 10-minute ATS check you can do on your phone, and how CV Desk scores and exports an ATS-safe resume.",
        "h1": "Is your resume getting past the ATS? How to check it on your phone",
        "lead": "If you have applied to dozens of jobs and heard nothing back, the problem may not be your experience. Many applicant tracking systems, the software that reads resumes before a person does, cannot read the layout many templates use.",
        "intro": [
            "We looked at the US App Store results for \"ats resume\" and \"resume builder\" in October 2026. The top results are a mix of brand-new ATS apps with no ratings yet and large resume builders with tens of thousands. Reviews of the big builders praise speed and templates, and complain about the same two surprises: being asked for a weekly subscription just to save the file, and a watermark on the export.",
            "An applicant tracking system turns your resume into plain text and fields: name, contact details, job titles, dates, skills. If it cannot find those fields, your resume can be filtered out before anyone reads it. The good news is that the fixes are simple, and most of them are about structure rather than writing.",
        ],
        "sections": [
            ("Why resumes fail ATS parsing", [], [
                "Two-column or table layouts that make the text come out in the wrong order.",
                "Text inside images, icons or graphics, which the system cannot read at all.",
                "Creative section headings instead of standard ones such as Experience, Education and Skills.",
                "Contact details placed in the page header or footer, which some systems skip.",
                "Missing keywords: the skills and titles from the job post do not appear in your resume.",
            ]),
            ("A 10-minute ATS check", [
                "First, copy all the text from your resume PDF and paste it into a plain note. If the order is jumbled or parts are missing, an ATS will have the same trouble. Second, compare the job post with your resume and list the skills and tools it mentions; make sure the ones you really have appear in your resume, written the same way. Third, check that your headings are standard and that every job has a title, an employer and dates.",
                "Then tailor one version per job. It sounds like extra work, but changing a summary line and reordering a few bullet points takes minutes once the structure is right, and it is the difference between a resume that matches the post and one that only matches your last job.",
            ], []),
        ],
        "steps_title": "Fix it on your phone",
        "steps": [
            "Build or paste your resume into a single-column, recruiter-ready template.",
            "Check the instant 0 to 100 ATS score and tap each suggested fix.",
            "Make a copy for the job you are applying to and adjust the summary and keywords.",
            "Export a single-column PDF with real, selectable text and standard headings.",
            "Need to edit wording elsewhere? Export an editable .docx and open it in Word, Pages or Google Docs.",
        ],
        "cards": [
            ("cvdesk", "CV Desk builds an ATS-safe resume entirely on your iPhone. You see an instant 0 to 100 ATS score with clear, tappable fixes, then export a single-column PDF with real, selectable text and standard headings, or an editable .docx with the same fonts, colours and layout. Multiple resumes let you tailor one per job, and the optional header photo is off by default. Build and preview without a purchase; unlock once to export with no watermark. No subscription, no ads, no account, and your resume never leaves your iPhone. The ATS score is an on-device estimate; results vary by employer system."),
        ],
        "faqs": [
            ("Is the ATS score the same as the employer's system?", "No. It is an on-device estimate that helps with parse safety and keyword coverage. Every employer system is different, so treat it as a checklist, not a guarantee."),
            ("Is my resume uploaded anywhere?", "No. Your resume never leaves your iPhone, and the app works in airplane mode."),
            ("Can I edit the resume in Word?", "Yes. Export an editable .docx and open it in Word, Pages or Google Docs with the same fonts, colours and layout."),
            ("Do I need a subscription to export?", "No. Unlock once to export with no watermark. There is no subscription, ever."),
        ],
        "related": [("en-US/cvdesk.html", "CV Desk: full overview")],
    },
    # 11 OnePage PPT：中國「年终总结 PPT」「PPT制作」
    {
        "key": "onepageppt", "lang": "zh-Hans",
        "slug": "nianzhong-zongjie-ppt-yiye-zenme-zuo-zhhans",
        "terms": ["年终总结", "ppt制作", "ai ppt"],
        "title": "年终总结PPT怎么做成一页？把一年的笔记、数据变成一页汇报",
        "desc": "12 月到 1 月要交年终总结、述职汇报？一页总结的四个区块、数字怎么放才可信、常见场景，以及用 OnePage PPT 把会议纪要、PDF、截图和 CSV 变成一页 16:9 幻灯片的做法。",
        "h1": "年终总结 PPT：一页讲清楚的做法",
        "lead": "12 月到 1 月，在 App Store 搜「年终总结」「PPT制作」的人，大多手上有一堆周报、会议纪要和表格，却要在几天内交出一份领导愿意看完的总结。",
        "intro": [
            "2026 年 10 月我们看了中国区 App Store「PPT制作」「AI PPT」的搜索结果：前几名多是模板库，或者用 AI 一次生成整套幻灯片的工具。但年终总结真正的难点往往不是“做二十页”，而是“把一年压成一页结论”。同类 AI 幻灯片 App 的差评，也集中在“一直转圈不出结果”“不按要求做”“乱编数字”。",
            "一页总结有一个好处：它逼着你先想清楚结论。听的人不用翻页就能看完，你也不用维护二十张幻灯片的排版。领导真正关心的通常只有三件事：今年做成了什么、数字说明了什么、明年打算怎么做。",
        ],
        "sections": [
            ("一页年终总结的四个区块", [], [
                "结论标题：一句话说清楚今年最重要的成果，不要写“2026 年度工作总结”这种空标题。",
                "三个关键成果：每个成果配一个真实数字，用柱状图、折线图或 KPI 数据行呈现。",
                "时间轴：按季度列出几个里程碑，让听的人看到一年的节奏。",
                "明年计划：两到三个重点方向，以及需要的支持或资源。",
            ]),
            ("数字怎么放才可信", [
                "总结里的每个数字都要能追溯到原始材料：周报、表格或系统导出的数据。宁可少放一个图表，也不要为了好看而估一个数字。只有数据真的撑得起来时才画图，没有数据的部分就用要点卡片说清楚。",
                "如果材料是一大堆截图和会议纪要，先把它们放在一起，让工具提炼出要点，再由你决定保留哪三条。最后一步一定是自己核对：每个标题、每个数字都要是你敢在会上解释的。",
            ], []),
            ("常见场景", [
                "述职汇报：一页讲清楚岗位职责、关键成果与明年目标。项目复盘：把一小时的复盘会纪要收成一页结论。部门年会：把季度数据变成一眼看懂的走势。学生的学期总结：把课程重点整理成一页讲义。",
            ], []),
        ],
        "steps_title": "三步做出一页总结",
        "steps": [
            "把全年的周报、会议纪要、PDF、截图或 CSV 表格放进去，中英文混排也可以。",
            "点「生成幻灯片」，要点变成标题，数字变成真正的图表，日期排成时间轴。",
            "用改版按钮试几个方向（更简洁、更图形化、更专业等），喜欢的元素可以锁定。",
            "点任意元素改文字、换图片、调顺序；改坏了可以用版本历史回到之前的稿子。",
            "导出可编辑的 .pptx、PDF 或高分辨率 PNG，直接发给领导或投到会议室。",
        ],
        "cards": [
            ("onepageppt", "OnePage PPT 能读懂你给它的文字、截图、照片、PDF 和 CSV 表格，提炼出关键信息，排成一页可以直接开讲的 16:9 幻灯片：数字变成柱状图、条形图、折线图、环形图或漏斗图，步骤变成流程图，日期变成时间轴，只有数据真的撑得起来时才会画图，绝不编造任何数字。六种一键改版、点任意元素即可修改、完整版本历史；可导出可编辑的 .pptx、PDF 与高分辨率 PNG。所有处理都在设备上完成，无需账号、没有追踪；Lifetime 解锁是一次性购买，不是订阅。"),
        ],
        "faqs": [
            ("导出的 PPT 还能改吗？", "可以。导出的 .pptx 保留可编辑的文本框与图表，不是一张图片，能用 PowerPoint、Keynote、Google 幻灯片打开继续改。"),
            ("材料会上传到服务器吗？", "不会。所有处理都在你的设备上完成，项目和图片都留在 iPhone 或 iPad 上，导出的文件只有你自己分享时才会离开设备。"),
            ("会不会自己编数字？", "不会。OnePage PPT 只有数据真的撑得起来时才会画图，绝不编造任何数字。"),
            ("是订阅制吗？", "不是。Lifetime 解锁是一次性购买，没有月费，也没有任何续费。"),
        ],
        "related": [("zh-Hans/onepageppt.html", "OnePage PPT 完整介绍")],
    },
    # 12 AI Brief：美國「ai prompt」「pdf summary」
    {
        "key": "aibriefpack", "lang": "en",
        "slug": "ai-prompt-from-pdf-and-screenshots-context-brief",
        "terms": ["ai prompt", "prompt generator", "pdf summary"],
        "title": "AI prompt from your files: turn PDFs, screenshots and notes into one brief the AI can't misread",
        "desc": "Typing \"ai prompt\" because the answers keep missing the point? The fix is usually context, not wording. How to build a context brief from PDFs, screenshots, notes and links, check the facts and remove personal details first.",
        "h1": "Better AI prompts start with better context, not better wording",
        "lead": "\"AI prompt\" is the very first suggestion the US App Store shows when you type \"ai p\". Many of the people typing it are not after clever wording; they are tired of answers that miss the point because the AI only saw half the story.",
        "intro": [
            "We looked at the US App Store results for \"ai prompt\" and \"prompt generator\" in October 2026. Most of the top results are prompt generators for images: you pick a style and get a line of text for an art model. If you are trying to get a useful answer about your own work, your class or your trip, that kind of prompt does not help. The model needs the facts: what the document says, what the screenshot shows, what you already decided.",
            "Reviews of AI study and PDF tools say the same thing in different words. Students praise PDF summaries that save them time before finals; people working on a phone complain that the mobile versions cannot handle their files the way the desktop does. The common need is simple: get the right material in front of the AI, in a clean form, without leaking personal details along the way.",
        ],
        "sections": [
            ("Why answers miss the point", [], [
                "The AI only sees what you paste, and pasting from five apps on a phone is slow, so people paste less.",
                "Screenshots and PDFs hold the details that matter, but they are not text until something reads them.",
                "Facts conflict across sources, and the AI quietly picks one without telling you.",
                "Personal details such as phone numbers and names come along for the ride.",
                "Every new chat starts from zero, so you rebuild the same background again and again.",
            ]),
            ("How to build a context brief", [
                "Start with the sources, not the question. Add the lecture PDFs, the screenshots of the booking, the notes from the meeting and the links you read. Let them be read on your phone, then look at the facts that come out: each one should show where it came from and how confident the reading is. Fix anything that needs context, and decide what stays in.",
                "Next, deal with privacy before anything leaves your device. Names, numbers and addresses should be kept, replaced or removed one by one, on purpose. Finally, put your actual question at the end of a brief with clear headings. The AI now answers your situation instead of guessing at it, and you can reuse the same brief tomorrow.",
            ], []),
        ],
        "steps_title": "From scattered files to one brief",
        "steps": [
            "Add screenshots, PDFs, files, copied text, notes or links; mix as many sources as you need.",
            "Let OCR and PDF reading run on your device, then review the facts, conflicts and open questions.",
            "Keep, replace or remove each detected personal detail before export.",
            "Pick a purpose-built template and check every fact, source and confidence.",
            "Copy the finished brief in one tap and paste it into any AI chat; reuse it next time.",
        ],
        "cards": [
            ("aibriefpack", "AI Brief turns screenshots, files, notes and documents into one clear AI-ready brief. OCR, PDF reading, duplicate checks, fact extraction and privacy detection use Apple frameworks on your device. Every fact keeps its source and confidence, and you can find facts, conflicts and open questions before AI sees them. Detected details are never removed automatically: keep, replace or remove each one before export. Structured headings, purpose-built templates and version history help you build context once and reuse it; copy the finished brief in one tap into any AI chat. No third-party ads, tracking, analytics or content telemetry."),
        ],
        "faqs": [
            ("Is AI Brief an image prompt generator?", "No. It builds a context brief from your own files, screenshots, notes and links, so a chat assistant can answer about your real situation."),
            ("Are my files sent to a server?", "OCR, PDF reading, fact extraction and privacy detection use Apple frameworks locally. You review the brief before sending it to any AI service."),
            ("Does it remove personal details automatically?", "No. Detected details are never removed automatically; you keep, replace or remove each one, and the changes are applied at export. AI Brief never promises anonymity."),
            ("Which AI assistants does it work with?", "Any of them. You copy the finished brief and paste it into the AI chat you already use."),
        ],
        "related": [("en-US/aibriefpack.html", "AI Brief: full overview")],
    },
    # 13 UsageNow：美國「claude usage」「ai usage tracker」「codex usage」
    {
        "key": "claudeusagemini", "lang": "en",
        "slug": "claude-usage-limit-check-reset-time-iphone",
        "terms": ["claude usage", "ai usage tracker", "codex usage"],
        "title": "Claude usage limit on iPhone: check what's left and when it resets (Codex and Copilot too)",
        "desc": "Hit your Claude limit halfway through a task? How to see your remaining session and weekly usage, the exact reset time and alerts before you run out, on your Home Screen, Lock Screen and Apple Watch.",
        "h1": "How to check your Claude usage limit and reset time on iPhone",
        "lead": "Most people who search \"claude usage\" have just been stopped in the middle of a coding session or a long document and want to know two things: how much is left, and when does it come back?",
        "intro": [
            "UsageNow shows Claude's five-hour session limit and weekly limits, including per-model weekly limits, alongside ChatGPT Codex, GitHub Copilot and Gemini. The usage itself lives on each service's own settings page, which is fine when you are at your desk and annoying when you are halfway through a task and do not want to break your flow to check.",
            "We looked at the US App Store results for \"claude usage\" and \"ai usage tracker\" in October 2026. The top results are a handful of small apps with very few ratings, and the reviews that exist ask for the same things: support for several accounts, and a widget that shows everything at a glance. People also said they paid quickly, because being stuck at the limit costs more time than the app does.",
        ],
        "sections": [
            ("What helps before you hit the limit", [], [
                "Keep the remaining percentage where you already look: the Home Screen, the Lock Screen or your watch.",
                "Know the exact reset time in your own time zone, not just a countdown.",
                "Set alerts at the percentages that matter to you, such as 90 and 98, once per limit and cycle.",
                "Turn on a reset alert so you know the moment the limit is back.",
                "If you have work and personal plans, sort the accounts so the one with room is on top.",
            ]),
            ("Planning long sessions around the reset", [
                "Long agentic coding sessions use up a session limit faster than chat. Before you start a big refactor or a long document, glance at the remaining session and weekly usage. If the five-hour window is nearly spent, do the planning and review steps now and start the heavy work right after the reset.",
                "If you use more than one assistant, the same view helps you switch on purpose instead of by accident: when one limit is close, move the next task to the assistant that still has room, and come back when the reset alert arrives.",
            ], []),
        ],
        "steps_title": "Set it up in two minutes",
        "steps": [
            "Sign in to each service on its official login page inside UsageNow.",
            "Add a Home Screen or Lock Screen widget, or the Apple Watch complication.",
            "Create alerts for the five-hour limit, the weekly limit or all limits at the percentages you choose.",
            "Turn on the reset alert.",
            "Sort your accounts by the soonest reset or by usage, or drag them into your own order.",
        ],
        "cards": [
            ("claudeusagemini", "UsageNow shows how much of each AI plan is left and the exact time it resets, on your Home Screen, and alerts you before you run out. It covers Claude's five-hour session and weekly limits (including per-model weekly limits), ChatGPT Codex five-hour and weekly windows, GitHub Copilot premium requests, chat and completions, and Gemini daily requests per model. Widgets come in every size for the Home Screen and Lock Screen, plus an Apple Watch complication, and you can flip through every account. Sign-in happens on each service's official login page and is stored in your device keychain; UsageNow has no servers, no account and no tracking."),
        ],
        "faqs": [
            ("Is UsageNow made by Anthropic?", "No. UsageNow is an independent app and is not affiliated with Anthropic, OpenAI, GitHub, Microsoft or Google."),
            ("Where are my sign-in details stored?", "You sign in on each service's official login page, the session is stored in your device keychain, and UsageNow talks only to those services. There is no UsageNow server."),
            ("Can I track more than one account?", "Yes. Show work and personal accounts side by side and sort them by reset time, usage, name or service, or drag them into your own order."),
            ("Does it work on Apple Watch?", "Yes. UsageNow runs on iPhone, iPad and Apple Watch, with Lock Screen widgets and watch complications."),
        ],
        "related": [("en-US/claudeusagemini.html", "UsageNow: full overview")],
        "legal": "Claude, ChatGPT, Codex, GitHub Copilot and Gemini are trademarks of their respective owners. UsageNow is an independent app and is not affiliated with them.",
    },
]


# --------------------------------------------------------------------------------------------
def esc(value: str) -> str:
    return html.escape(value, quote=True)


def url_for(relative: str) -> str:
    return f"{SITE}/{relative}"


def page_relative(spec: dict) -> str:
    return f"{spec['lang']}/{SECTION}/{spec['slug']}.html"


def sitemap_name(lang: str) -> str:
    return f"sitemap_{SECTION}_{lang}.xml"


def campaign(key: str, cc: str) -> str:
    """款 × 國家 × 詞群（sr）的 gw 階梯碼（gw_campaign.py）；開格看 geo/data/gw_campaign_plan.json。"""
    try:
        token = gw_campaign.campaign(key, GW_GROUP, cc)
    except gw_campaign.GwCampaignError as error:
        raise GenerationError(str(error)) from error
    if len(token) > MAX_CT:
        raise GenerationError(f"campaign token does not fit: {token!r}")
    return token


def store_url(key: str, lang: str) -> str:
    info = LANGS[lang]
    app_id = APP_IDS[key]
    url = (f"https://apps.apple.com/{info['cc']}/app/id{app_id}"
           f"?pt={PROVIDER_TOKEN}&ct={campaign(key, info['cc'])}&mt=8")
    return validated_app_store_url(url, app_id, expected_locale=info["store"], require_campaign=True,
                                   provider_token=PROVIDER_TOKEN)


def store_names(data_dir: Path = ROOT / "data") -> dict[tuple[str, str], str]:
    """(key, page lang) → 該國商店名（data/<key>_full.json）。"""
    out = {}
    for spec in PAGE_SPECS:
        store = LANGS[spec["lang"]]["store"]
        for key, _ in spec["cards"]:
            path = data_dir / f"{key}_full.json"
            if not path.exists():
                raise GenerationError(f"{key}: missing {path.name}")
            name = (json.loads(path.read_text(encoding="utf-8")).get(store) or {}).get("name")
            if not name:
                raise GenerationError(f"{key}: no {store} store name")
            out[(key, spec["lang"])] = name
    return out


def _card(key: str, text: str, lang: str, names: dict) -> str:
    info = LANGS[lang]
    name = names[(key, lang)]
    cta = f'<a class="dl" href="{esc(store_url(key, lang))}" rel="noopener">{esc(info["cta"])}</a>'
    cta += f' <a class="more" href="{esc(url_for(f"{info["dir"]}/{key}.html"))}">{esc(info["more"])}</a>'
    return "\n".join([f'<article class="app" id="app-{esc(key)}">', f"<h3>{esc(name)}</h3>",
                      f"<p>{esc(text)}</p>", f'<p class="cta">{cta}</p>', "</article>"])


def render(spec: dict, names: dict) -> str:
    lang = spec["lang"]
    info = LANGS[lang]
    relative = page_relative(spec)
    canonical = url_for(relative)
    home = url_for(f"{info['dir']}/index.html")
    blocks, toc = [], []
    for number, (title, paras, points) in enumerate(spec["sections"], 1):
        anchor = f"s{number}"
        toc.append(f'<a href="#{anchor}">{esc(title)}</a>')
        body = "".join(f"<p>{esc(p)}</p>" for p in paras)
        if points:
            body += '<ul class="points">' + "".join(f"<li>{esc(p)}</li>" for p in points) + "</ul>"
        blocks.append(f'<section id="{anchor}"><h2>{esc(title)}</h2>{body}</section>')
    steps = "".join(f"<li>{esc(step)}</li>" for step in spec["steps"])
    blocks.append(f'<section id="steps"><h2>{esc(spec["steps_title"])}</h2><ol class="steps">{steps}</ol></section>')
    toc.append(f'<a href="#steps">{esc(spec["steps_title"])}</a>')
    cards = "\n".join(_card(key, text, lang, names) for key, text in spec["cards"])
    blocks.append(f'<section id="apps"><div class="cards">\n{cards}\n</div></section>')
    faqs = "".join(f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
                   for q, a in spec["faqs"])
    related = "".join(f'<li><a href="{esc(url_for(rel))}">{esc(label)}</a></li>' for rel, label in spec["related"])
    main_key = spec["cards"][0][0]
    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": info["home"], "item": home},
            {"@type": "ListItem", "position": 2, "name": spec["h1"], "item": canonical},
        ]},
        {"@context": "https://schema.org", "@type": "Article", "headline": spec["h1"], "inLanguage": info["html"],
         "dateModified": UPDATED, "mainEntityOfPage": canonical, "keywords": ", ".join(spec["terms"]),
         "about": {"@type": "SoftwareApplication", "name": names[(main_key, lang)], "operatingSystem": "iOS",
                   "applicationCategory": "MobileApplication", "url": url_for(f"{info['dir']}/{main_key}.html")}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in spec["faqs"]
        ]},
    ]
    ld_json = json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/")
    legal = f'<p class="legal">{esc(spec["legal"])}</p>' if spec.get("legal") else ""
    return f"""<!DOCTYPE html>
<html lang="{info['html']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec['title'])}</title>
<meta name="description" content="{esc(spec['desc'])}">
<meta name="robots" content="index,follow,max-image-preview:large">
{GW_META}
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:locale" content="{info['og']}">
<meta property="og:title" content="{esc(spec['title'])}">
<meta property="og:description" content="{esc(spec['desc'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="article:modified_time" content="{UPDATED}">
<meta name="apple-itunes-app" content="app-id={APP_IDS[main_key]}">
<style>
{CSS}
</style>
<script type="application/ld+json">
{ld_json}
</script>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{esc(home)}">{esc(info['home'])}</a><nav><a href="{esc(url_for(f"{info['dir']}/answers/index.html"))}">{esc(info['answers'])}</a> · <a href="{esc(url_for('about.html'))}">{esc(info['about'])}</a></nav></div></header>
<main class="wrap">
<div class="breadcrumb"><a href="{esc(home)}">{esc(info['home_label'])}</a> / {esc(info['crumb'])}</div>
<h1>{esc(spec['h1'])}</h1>
<p class="lead">{esc(spec['lead'])}</p>
<p class="updated">{esc(info['updated'])}: {UPDATED}</p>
{''.join(f'<p>{esc(p)}</p>' for p in spec['intro'])}
<nav class="toc" aria-label="{esc(info['toc'])}">{' · '.join(toc)}</nav>
{chr(10).join(blocks)}
<section><h2>{esc(info['faq'])}</h2>{faqs}</section>
<section class="related"><h2>{esc(info['related'])}</h2><ul>{related}</ul></section>
{legal}
</main>
</body>
</html>
"""


def visible_text(source: str) -> str:
    main = re.search(r"<main\b.*?</main>", source, re.S)
    text = re.sub(r"<[^>]+>", " ", main.group(0) if main else "")
    return html.unescape(text)


def dedicated_size(lang: str, text: str) -> int:
    return len(CJK.findall(text)) if lang in ("zh-Hant", "zh-Hans", "ja") else len(WORD.findall(text))


def page_problems(spec: dict, source: str, pages: Path | None = None) -> list[str]:
    relative = page_relative(spec)
    problems = []
    text = visible_text(source)
    size = dedicated_size(spec["lang"], text)
    floor = MIN_CJK if spec["lang"] in ("zh-Hant", "zh-Hans", "ja") else MIN_WORDS
    if size < floor:
        problems.append(f"{relative}: dedicated text {size} under {floor}")
    head = source.split("</head>", 1)[0]
    head_text = re.sub(r"<script\b.*?</script>", "", head, flags=re.S)
    for found in BANNED.finditer(html.unescape(text + head_text)):
        problems.append(f"{relative}: banned price/free/pro wording {found.group(0)!r}")
    info = LANGS[spec["lang"]]
    for href in re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', source):
        url = html.unescape(href)
        try:
            validated_app_store_url(url, expected_locale=info["store"], require_campaign=True)
        except ValueError as error:
            problems.append(f"{relative}: {error}")
    cards = re.findall(r'<article class="app"[^>]*>.*?</article>', source, re.S)
    if not cards:
        problems.append(f"{relative}: no app cards")
    for card in cards:
        if f"https://apps.apple.com/{info['cc']}/app/id" not in card:
            problems.append(f"{relative}: card without a direct App Store link")
    if pages is not None:
        for href in set(re.findall(r'href="(' + re.escape(SITE) + r'/[^"#]+)"', source)):
            target = href[len(SITE) + 1:]
            if target == relative:
                continue
            path = pages / target
            if not path.is_file():
                problems.append(f"{relative}: internal link target missing {target}")
            elif re.search(r'<meta[^>]+name="robots"[^>]+noindex', path.read_text(encoding="utf-8", errors="ignore")):
                problems.append(f"{relative}: internal link target is noindex {target}")
    # 倉儲文案與線上商店不一致的款（store_copy_drift 紅燈）：同一句有品牌名＋商店已不列的功能 → 擋
    problems += store_copy_drift.html_page_problems(source, label=f"{relative}: ")
    return problems


def finalize(source: str, relative: str, android_apps: dict) -> str:
    source = android_play.inject_html(source, android_apps)
    return first_party_disclosure.finalize_page(source, relative)


def build(android_apps: dict, *, pages: Path | None = None, names: dict | None = None) -> dict[str, str]:
    names = names if names is not None else store_names()
    out, problems, slugs = {}, [], set()
    for spec in PAGE_SPECS:
        relative = page_relative(spec)
        if relative in slugs:
            problems.append(f"duplicate page {relative}")
        slugs.add(relative)
        out[relative] = finalize(render(spec, names), relative, android_apps)
        problems += page_problems(spec, out[relative], pages)
    if problems:
        raise GenerationError("\n".join(problems))
    return out


def merge_sitemap(source: str, urls: list[str], lastmod: str = UPDATED) -> str:
    """Add the missing <url> rows before </urlset>; rows already present are left as they are."""
    rows = [f"<url><loc>{esc(url)}</loc><lastmod>{lastmod}</lastmod></url>"
            for url in urls if f"<loc>{esc(url)}</loc>" not in source]
    if not rows:
        return source
    if "</urlset>" not in source:
        raise GenerationError("sitemap has no </urlset>")
    head, tail = source.rsplit("</urlset>", 1)
    return head + "\n".join(rows) + "\n</urlset>" + tail


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只檢查，不寫檔")
    parser.add_argument("--pages", type=Path, default=PAGES)
    args = parser.parse_args(argv)
    pages = args.pages.resolve()
    try:
        android_apps = android_play.load_snapshot()
    except (OSError, ValueError) as error:  # an untrusted snapshot publishes no Play link
        print(f"android snapshot ignored: {error}", file=sys.stderr)
        android_apps = {}
    out = build(android_apps, pages=pages)
    writes = dict(out)
    for lang in sorted({spec["lang"] for spec in PAGE_SPECS}):
        name = sitemap_name(lang)
        urls = [url_for(page_relative(s)) for s in PAGE_SPECS if s["lang"] == lang]
        writes[name] = merge_sitemap((pages / name).read_text(encoding="utf-8"), urls)
    changed = []
    for relative, source in writes.items():
        path = pages / relative
        if not path.exists() or path.read_text(encoding="utf-8") != source:
            changed.append(relative)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
    print(json.dumps({"pages": sorted(out), "changed": changed, "android_apps": len(android_apps),
                      "sizes": {page_relative(s): dedicated_size(s["lang"], visible_text(out[page_relative(s)]))
                                for s in PAGE_SPECS}}, ensure_ascii=False, indent=1))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
