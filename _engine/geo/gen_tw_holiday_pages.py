#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台灣連假意圖頁＋ iPhone Duo 必裝 App 滿版清單 → <Guide>/zh-Hant/seasonal/。

背景：業主 2026-10-22「明天全台灣放假 請用力宣傳」。10/23（五）起台灣連假，同一天 iPhone Duo
開賣；台灣使用者會搜「iPhone Duo 必裝 App」「連假 行程規劃 App」「連假 讀書計畫」「大掃除 清單」。
這支產生 4 頁手寫內容（不是一詞一頁的模板頁），每頁的情境、步驟、常見問題都不同。

規則（ops/company/duo_claim_rules.md、CLAUDE.md）：
- iPhone Duo 宣稱只給 aso/duo/duo_list.py 判定可宣稱、而且 iTunes Lookup 讀到的線上版本等於
  live_version 的款；句子只用 aso/duo/claim_lines.json 的 zh-Hant promo_line（已另一模型複審）。
  不在清單的款（例如 BattAI）iPhone Duo 頁一個字都不寫，情境頁也不掛宣稱句。
- 每張卡片附台灣商店 App Store 直連（pt＋ct＋mt）；ct＝gw 階梯碼 ln_<key>_<詞群>_<國>_gw（gw_campaign.py：
  款 × 國家 × 詞群，量不夠的格子併成 all／ww；頁首詞群標記 ss，每日改寫照標記逐連結重算、不蓋成 geo_*）。
  Google Play 連結由 android_play.inject_html 依已發布快照補上（同一個 ct 進安裝來源）。
- 功能句只取 data/<key>_full.json 的 zh-Hant 商店文案；不寫價格、免費、Free。
- 只寫這 4 頁與 sitemap_seasonal_zh-Hant.xml 的這 4 列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_tw_holiday_pages.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_tw_holiday_pages.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (HERE, ROOT / "social", ROOT / "aso" / "duo"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import android_play  # noqa: E402
import gw_campaign  # noqa: E402
import store_copy_drift  # noqa: E402
import duo_list  # noqa: E402
import first_party_disclosure  # noqa: E402
from app_store_storefronts import validated_app_store_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
LANG = "zh-Hant"
SECTION = "seasonal"
SITEMAP = "sitemap_seasonal_zh-Hant.xml"
UPDATED = "2026-10-22"
CAMPAIGN_DATE = "1023"
PROVIDER_TOKEN = "118326163"  # 公開值：站上每個 App Store 連結的 pt= 都是它
GW_GROUP = "ss"            # gw_campaign 詞群：檔期
GW_META = gw_campaign.meta_tag(GW_GROUP)
MAX_CT = 30                   # app_store_storefronts.CAMPAIGN_TOKEN_RE 的上限
CLAIM_LINES = ROOT / "aso" / "duo" / "claim_lines.json"
LOOKUP_URL = "https://itunes.apple.com/lookup?id={ids}&country={cc}"
BANNED = re.compile(r"免費|free|NT\$|US\$|\$\d", re.IGNORECASE)
CJK = re.compile(r"[㐀-鿿]")
LEGAL = "iPhone 是 Apple Inc. 在美國及其他國家註冊的商標。"

# 台灣商店名（= data/<key>_full.json zh-Hant name；產生時逐款比對，不一致就停）。
NAMES = {
    "aibriefpack": "AI Brief：檔案轉 AI 提示詞",
    "aim990": "Aim990：英文弱點教練",
    "caldaily": "CalDaily 計算機與主題",
    "claudeusagemini": "UsageNow：AI 用量與額度追蹤",
    "countdaysnow": "CountDaysNow: Event Counter",
    "cvdesk": "CV Desk ATS 履歷製作",
    "cyca": "Cyca 經期週期追蹤・排卵",
    "dailymate": "DailyMate：用句子學語言",
    "dailymatelite": "DailyMate Lite：開口練習",
    "dbhalo": "dB Halo：分貝計",
    "easyam": "EasyAM: 國定假日、連假不響的智慧鬧鐘",
    "gmoney": "G+Money：日常記帳·預算·匯率",
    "gmoneylite": "G+Money Lite：旅行記帳·匯率換算",
    "hourstag": "HoursTag：價格換工時",
    "hourstaglite": "HoursTag Lite：買前先算工時",
    "ledmovingtext": "LED Moving Text",
    "lockhour": "LockHour Pro：封鎖 App·專注計時",
    "lumibopomofo": "Lumi注音星球",
    "lumibopomofopro": "Lumi注音星球 Pro",
    "lumiletters": "Lumi 字母星球 Lite：兒童英文ABC遊戲",
    "lumiletterspro": "Lumi 字母星球 Pro：ABC啟蒙",
    "lumimath": "Lumi數學星球：探索版",
    "lumimathpro": "Lumi 數學星球：兒童數學",
    "lumimission": "Lumi 任務星球：生活習慣養成",
    "lumimissionpro": "Lumi 任務星球 Pro：好習慣養成遊戲",
    "lumiweather": "Lumi天氣星球：天氣預報與穿搭建議",
    "maskmyfile": "Mask My File：分享前移除個資",
    "mochi": "Mochi: 可愛待辦清單",
    "mochidonestamp": "Mochi DoneStamp：上次何時",
    "moneytag": "MoneyTag: 收入與支出",
    "notesstudio100": "100 Notes Studio: Pen & Paper",
    "onepageppt": "OnePage PPT: AI 一頁簡報",
    "photocream": "PhotoCream Pro：底片濾鏡·復古修圖",
    "picclear": "PicClear Pro：照片清理·釋放空間",
    "qrcodehalo": "QR Code Halo：安全掃描與建立",
    "savetag": "SaveTag:AI 連結收藏",
    "scanto": "ScanTo Pro: 離線PDF掃描",
    "sereno": "Sereno: 極致睡眠音效",
    "shotinbox": "ShotInbox AI：截圖整理",
    "snapport": "Snapport: 護照證件照",
    "snapportlite": "Snapport Lite：在家拍證件照",
    "sononote": "Sono Note：錄音轉文字",
    "stayclock": "Stay Clock:翻頁桌鐘",
    "studydown": "Studydown：翻面專注計時",
    "tripbee": "TripBee: 旅遊行程規劃",
    "tripbeelite": "TripBee Lite：旅程規劃",
    "tripplanet": "Trip Planet 親子旅行遊戲",
    "unblurry": "Unblurry Pro：照片變清晰",
    "wifiaid": "WiFi Aid：找出網路問題·診斷",
    "wifiaidlite": "WiFi Aid Lite",
    "wordmate": "Wordmate：44 種語言背單字",
    "wordmatelite": "Wordmate Lite 每天五個單字",
    "zipbox": "Zipbox 解壓縮：RAR ZIP 7z",
}

# iPhone Duo 頁：每款一句真實好處（對照各款 zh-Hant 商店描述）。
DUO_LINES = {
    "mochi": "寫下今天要做的事，輕點小圓圈打勾；主畫面小工具和 Apple Watch 上隨時看得到清單。",
    "mochidonestamp": "上次換床單、澆花、換濾芯是哪天？做完點一下就記下時間，下次提醒從實際完成那一刻重新算。",
    "lockhour": "開始一段專注時段，選定的 App 立刻鎖住、時間到自動解鎖，讀書和工作時不會一直點開社群。",
    "studydown": "選好項目、把手機螢幕朝下放在桌上就開始計時，把每次專心累積成看得見的紀錄。",
    "countdaysnow": "考試、旅行、紀念日一起倒數，剩 7 天、3 天、1 天都會提醒，日期旁還能顯示農曆或民國年。",
    "easyam": "國定假日自動不響、補班日照響，接下來七天哪幾天會響、幾點響一眼看清楚。",
    "stayclock": "把 iPhone 變成隔著房間也看得清楚的翻頁桌鐘，同一款錶面同步到待機模式、小工具與 Apple Watch。",
    "sononote": "對著手機說話或錄下一堂課，幾秒就整理成摘要、重點和待辦，也能切換成只在本機處理。",
    "notesstudio100": "手寫、打字、PDF 標註和頁面錄音放在同一本筆記裡，核心編輯不用連網也能用。",
    "onepageppt": "把打好的字、截圖或 PDF 丟進去，自動排成一頁可以直接上台講的 16:9 投影片。",
    "scanto": "收據、合約、證件掃成清楚的 PDF，在手機上辨識文字，之後搜尋內文就找得到，全程離線。",
    "aibriefpack": "把截圖、PDF 和筆記整理成一份附來源的摘要，貼給 AI 之前先檢查事實與個資。",
    "savetag": "從任何 App 一鍵把連結分享進來，自動分好購物、美食、旅遊等標籤，只記得大概也搜得到。",
    "cvdesk": "在 iPhone 上做出 ATS 系統讀得懂的履歷，即時給 0 到 100 分與修正建議，可匯出 PDF 與 Word。",
    "maskmyfile": "傳檔案之前先找出並永久遮蔽個資，圖片、PDF 和多種文字檔都能處理，全程在手機上完成。",
    "zipbox": "直接打開 ZIP、RAR、7z 等 13 種格式，先預覽裡面的檔案，只取出需要的那一個。",
    "claudeusagemini": "Claude、Codex、Copilot、Gemini 的剩餘額度和重置倒數一次看清楚，額度見底前先提醒你。",
    "gmoney": "記帳、每日預算和 50 種貨幣換算合在一個 App，依旅程分組小計，沒有網路也能用。",
    "gmoneylite": "出國用當地幣別記下每一筆，立刻換算成你的本國貨幣，每天的花費和上限一眼對照。",
    "moneytag": "每個專案各自一本帳，收入減支出就是淨額，同一個標籤還能跨專案合計。",
    "hourstag": "輸入價格就換算成要工作幾小時，再把花費標成必要、想要或衝動，看清楚錢花去哪裡。",
    "hourstaglite": "衝動購物前先換算成工時，看見一個目標背後要工作多久，並追蹤進度。",
    "caldaily": "除了一般計算，還有折扣與稅、小費與分帳、行程油費、貸款月付等工具，每筆結果都能命名再搜尋。",
    "tripbee": "逐日行程時間軸、依旅伴與孩子年齡自動產生的打包清單，還能邀家人朋友一起編同一份行程。",
    "tripbeelite": "用清楚的每日時間軸整理航班、住宿與活動，備註、提醒和票券資訊都放在找得到的地方。",
    "tripplanet": "把長途車程和搭飛機變成 3 到 10 歲孩子的小任務，完成就收集獎勵，走完一趟旅程還會在旅行護照蓋章。",
    "lumiweather": "把溫度、降雨、紫外線和風綜合成外出指數，並標出今天最適合出門的時段。",
    "photocream": "超過 100 種底片風格，按快門前就能預覽成品，拍完還能細修光線、色彩與膚質。",
    "unblurry": "手震、失焦、太暗的照片在手機上就能變清晰，照片不會上傳到雲端。",
    "picclear": "找出重複照片、舊截圖、模糊照片和大型影片，刪除前逐張檢視，把儲存空間拿回來。",
    "shotinbox": "截圖自動分成購物、票券、地圖、收據等類別，用文字就搜得到，辨識都在手機上完成。",
    "snapport": "在家拍護照、簽證與證件照，有臉部對齊指引、背景替換和可列印的排版。",
    "snapportlite": "把人像照精準裁成指定尺寸，內建 35 種範本，可匯出 JPEG、PNG 或 PDF。",
    "aim990": "8 分鐘診斷找出多益聽讀最弱的 3 項技能，每天只練一項，第 30 天複測看進步。",
    "wordmate": "44 種語言、14 個生活主題的單字，學英文時每個字都有例句和發音，小工具上也能背。",
    "wordmatelite": "一次只練 5 個字，結束時列出今天學會的字，通勤幾分鐘就能維持習慣。",
    "dailymate": "用完整句子學語言：47 種語言、8,400 句生活短句，每一句都附上道地的回應。",
    "dailymatelite": "旅行、點餐、問路等生活情境的一來一往，用 50 種語言練習開口。",
    "lumiletters": "3 到 7 歲的孩子聽字母名稱與發音，跟著筆順輔助線描大寫和小寫，沒有廣告、離線也能玩。",
    "lumiletterspro": "14 顆星球、12 種題型練自然發音，家長專區看得到四項能力的進步，還能列印學習單。",
    "lumimath": "數數、加減法、九九乘法、時鐘與錢幣變成太空冒險，題目看圖就懂，也能朗讀題目。",
    "lumimathpro": "46 種玩法涵蓋規律、邏輯推理與應用題，弱項練習會把常錯的題型集中起來反覆練。",
    "lumibopomofo": "37 個注音符號變成可愛的小夥伴，邊玩邊熟悉符號、發音、聲調與拼讀。",
    "lumibopomofopro": "給 3 到 7 歲孩子的注音完整版：拼讀、聲調和筆順描寫，不用登入、不用網路。",
    "lumimission": "吃飯、刷牙、收玩具變成溫柔的小任務，孩子每完成一步，兔兔夥伴就跳起來歡呼。",
    "lumimissionpro": "五個每日任務加上自訂任務，家長後台看得到今日總覽與七天紀錄。",
    "sereno": "雨聲、海浪、風聲等實地錄音混出上千種音景，睡眠計時器會慢慢淡出，完全離線。",
    "cyca": "記錄經期與症狀，預測下次經期、易孕期與排卵日，資料只留在你的 iPhone。",
    "wifiaid": "網路卡住時一鍵檢查 Wi-Fi、DNS 與網際網路連線，告訴你最可能是哪裡出了問題。",
    "wifiaidlite": "無法上網時從多條路徑同時檢測，幾秒內看到結果與診斷結論，紀錄只存在你的裝置上。",
    "qrcodehalo": "掃到就直接開啟網址、Wi-Fi 等內容；想先檢查可以關掉自動執行，再到歷史紀錄做安全檢查。",
    "dbhalo": "即時分貝、頻譜與噪音劑量估算，還能整理睡覺時的打鼾、說話等聲音事件。",
    "ledmovingtext": "打一句話，手機就變成會跑的大字看板，接機、演唱會應援隔著人群也看得清楚。",
}

DUO_GROUPS = (
    ("待辦與時間管理", ("mochi", "mochidonestamp", "lockhour", "studydown", "countdaysnow", "easyam",
                       "stayclock")),
    ("筆記、文件與工作", ("sononote", "notesstudio100", "onepageppt", "scanto", "aibriefpack", "savetag",
                         "cvdesk", "maskmyfile", "zipbox", "claudeusagemini")),
    ("記帳與理財", ("gmoney", "gmoneylite", "moneytag", "hourstag", "hourstaglite", "caldaily")),
    ("旅行與天氣", ("tripbee", "tripbeelite", "tripplanet", "lumiweather")),
    ("拍照與相簿整理", ("photocream", "unblurry", "picclear", "shotinbox", "snapport", "snapportlite")),
    ("語言學習", ("aim990", "wordmate", "wordmatelite", "dailymate", "dailymatelite")),
    ("孩子學習與好習慣", ("lumiletters", "lumiletterspro", "lumimath", "lumimathpro", "lumibopomofo",
                         "lumibopomofopro", "lumimission", "lumimissionpro")),
    ("健康與睡眠", ("sereno", "cyca")),
    ("網路與實用工具", ("wifiaid", "wifiaidlite", "qrcodehalo", "dbhalo", "ledmovingtext")),
)


def _answers(slug: str) -> str:
    return f"{LANG}/answers/{slug}.html"


DUO_SLUG = "iphone-duo-bizhuang-app-manban-zhichi-qingdan-zhhant"
TRIP_SLUG = "lianjia-chuyou-xingcheng-jizhang-fenzhang-app-zhhant"
STUDY_SLUG = "lianjia-dushu-jihua-buji-jindu-app-zhhant"
CLEAN_SLUG = "lianjia-dasaochu-zhengli-daiban-qingdan-app-zhhant"

PAGE_SPECS = (
    {
        "slug": DUO_SLUG,
        "seg": "duo",
        "title": "iPhone Duo 必裝 App：已針對 iPhone Duo 最佳化的滿版清單（2026）",
        "h1": "iPhone Duo 必裝 App：已滿版支援清單",
        "desc": ("iPhone Duo 10/23 開賣，很多 App 還沒適配內螢幕。這份清單只列實測通過、已針對 iPhone Duo "
                 "最佳化、真正填滿內螢幕的 App，依用途分類，每款附一句重點與 App Store 下載連結。"),
        "lead": "新機到手，最想知道的是常用 App 有沒有適配內螢幕。這份清單只列已經實測通過、打開就填滿整個內螢幕的 App。",
        "intro": (
            "iPhone Duo 打開是 7.6 吋的內螢幕，摺起來是 5.4 吋的外螢幕，出廠就是 iOS 27.1。蘋果的開發者說明提到，"
            "用 iOS 27.1 開發套件建置的 App 才會延伸到螢幕邊緣；還沒更新的 App 在內螢幕不會填滿，看起來就像把手機版放大。"
            "所以 10/23 開賣後，大家最常問的不是哪款最好用，而是「我常用的 App 到底有沒有適配」。",
            "下面這份清單只列我們自己開發、而且已經用 iPhone Duo 實測通過的 App，目前上架的版本就是通過驗證的版本，"
            "依用途分成幾類。每一款都填滿整個內螢幕，摺起或打開都會自動調整版面；之後有新的 App 通過驗證，會再補進來。",
        ),
        "steps_title": "怎麼自己判斷一款 App 有沒有為 iPhone Duo 最佳化",
        "steps": (
            "先把 App 更新到 App Store 上的最新版本，舊版本不會因為換了新機就自動滿版。",
            "打開內螢幕看一次：左右或上下留了一圈空白、畫面像放大的手機版，通常就是還沒適配。",
            "摺起來、再打開各試一次，看版面會不會跟著螢幕大小重新排好。",
            "看 App Store 商店頁：開發者上傳 iPhone Duo 截圖後，商店頁會顯示「已針對 iPhone Duo 最佳化」標章。"
            "標章取決於截圖有沒有上傳，所以最準的方法還是實際打開看。",
        ),
        "faqs": (
            ("這份清單裡的 App 都已經滿版了嗎？",
             "是。清單只列實測通過、而且 App Store 上目前的版本就是通過驗證版本的 App；更新到最新版後打開內螢幕就是滿版。"),
            ("為什麼有些 App 在 iPhone Duo 上沒有滿版？",
             "蘋果的說明是：用 iOS 27.1 開發套件建置的 App 才會延伸到螢幕邊緣。還沒用新開發套件更新的 App，在內螢幕上不會填滿，要等開發者更新。"),
            ("App Store 上怎麼看哪些 App 已經適配？",
             "開發者在商店後台上傳 iPhone Duo 截圖後，商店頁會出現「已針對 iPhone Duo 最佳化」標章。標章要看截圖有沒有上傳，"
             "所以沒有標章不一定代表沒適配；最準的方法是更新到最新版後實際打開看。"),
            ("連假要出門或讀書，該從哪幾款開始？",
             "要排行程和記帳，先看 TripBee 和 G+Money；要補讀書進度，先看 LockHour Pro 和 Studydown；要整理家裡和手機，"
             "先看 Mochi 可愛待辦清單和 PicClear Pro。下面的「相關頁面」有三份連假情境清單。"),
        ),
        "related": (
            (f"{LANG}/{SECTION}/{TRIP_SLUG}.html", "連假出遊 App：排行程、分帳記帳、看天氣"),
            (f"{LANG}/{SECTION}/{STUDY_SLUG}.html", "連假讀書計畫：補進度、不滑手機"),
            (f"{LANG}/{SECTION}/{CLEAN_SLUG}.html", "連假大掃除與整理待辦清單"),
        ),
        "legal": True,
    },
    {
        "slug": TRIP_SLUG,
        "seg": "trip",
        "title": "連假出遊 App 推薦：排行程、分帳記帳、看天氣一次搞定（2026）",
        "h1": "連假出遊 App：排行程、分帳記帳、看天氣",
        "desc": ("10/23 起連假要出門？從揪團排行程、雨天備案、記帳分帳到收假鬧鐘，挑出出遊真的用得上的 iPhone App，"
                 "照出門前、路上、回家後排好，每款附 App Store 下載連結。"),
        "lead": "連假出遊真正麻煩的，通常不是去哪裡，而是行程一直改、雨天沒備案、回來算不清楚誰付了多少。",
        "intro": (
            "這次 10/23（五）起連假，不少人臨時決定出門走走。群組裡的行程版本傳了好幾份、出發前一天才發現要下雨、"
            "回家後對著一疊發票算分攤，是最常見的三個卡關點。",
            "下面照「出門前、路上、帶孩子與拍照、收假前一晚」四個時間點，挑出我們自己做、而且真的對得上這些麻煩的 App。"
            "每一段都先講要解決什麼，再講用哪一款、怎麼用。",
        ),
        # 2026-10-23 付費榜衝榜實驗（reports/yi30/paid_chart_targets.md）：TripBee 在台灣付費旅遊榜前 10，
        # 連假三天放在頁首最顯眼的位置。points 每一句都是 data/tripbee_full.json zh-Hant 描述的原文片段（測試逐句核對）。
        "updated": "2026-10-23",
        "spotlight": {
            "key": "tripbee",
            "seg": "pick",
            "title": "這次連假先裝這一款：TripBee: 旅遊行程規劃",
            "lead": "揪團出遊最常卡在三件事：行程版本傳來傳去、下雨沒有備案、出門才發現少帶東西。TripBee 把這三件事放進同一份行程：",
            "points": (
                "逐日行程時間軸：支援航班、飯店、餐廳與活動",
                "邀請他人共同編輯共享旅程",
                "智慧打包清單：依旅遊天數、季節、每位家庭成員與孩子年齡自動產生",
                "結合天氣規劃：先看天氣再安排戶外與室內活動，遇到雨天、颱風或臨時改期時，也能快速準備備案",
                "一鍵 Apple 地圖導航：從任一出發點前往景點、飯店、餐廳、機場或集合地點",
                "一次購買，無廣告、無追蹤",
            ),
            "cta": "在 App Store 下載 TripBee →",
        },
        "groups": (
            ("出門前：排行程、看天氣、收好票券", (
                ("tripbee", "揪團出遊最怕行程傳來傳去。TripBee 可以邀家人朋友一起編同一份逐日行程，航班、飯店、餐廳和活動都排在時間軸上；"
                            "打包清單會依天數、季節、每位旅伴與孩子年齡自動產生，還能先看天氣準備雨天備案。"),
                ("tripbeelite", "只規劃這一趟、想要簡單一點的話，TripBee Lite 用每日時間軸整理航班、住宿與活動，"
                                "備註、提醒和票券資訊都放在需要時找得到的地方。"),
                ("lumiweather", "連假天氣說變就變。Lumi天氣星球把溫度、降雨機率、紫外線和風綜合成 0 到 100 的外出指數，"
                                "標出今天最適合出門的時段，也會提醒該不該帶傘、擦防曬。"),
                ("shotinbox", "訂房確認、車票、餐廳地址常常只是一張截圖。ShotInbox AI 會把截圖自動分到票券、旅遊、地圖與地點等類別，"
                              "到了現場用文字就搜得到，還能一鍵在地圖中開啟。"),
            )),
            ("路上：記帳、分帳、算油錢", (
                ("gmoney", "每一筆花費依分類記下，設好每日上限就知道今天還能花多少；把這趟建成一個旅程，總覽和匯出都會依旅程分組小計，"
                           "匯出純文字或 CSV 就能傳給同行的朋友對帳。"),
                ("caldaily", "結帳要拆帳時，CalDaily 計算機與主題內建小費與分帳工具，自駕還能用行程油費工具先算油錢；"
                             "每筆結果都能命名，回頭搜尋「那次分帳的晚餐」就找得到。"),
                ("moneytag", "多人一起出遊、有收公費的話，可以在 MoneyTag 把這次連假開成一個專案，收進來的公費記收入、花掉的記支出，"
                             "收入減支出就是還剩多少。"),
                ("gmoneylite", "連假出國的話，G+Money Lite 讓你用當地幣別記帳、立刻換算成本國貨幣，沒有網路時改用已儲存的匯率。"),
            )),
            ("帶孩子、睡不好、照片拍糊了", (
                ("tripplanet", "帶 3 到 10 歲的孩子塞在車陣裡？Trip Planet 把長途車程、飯店住宿和嘗試新食物變成小任務，"
                               "完成就收集獎勵，兩位家長可以用各自的裝置共享同一趟旅程。"),
                ("sereno", "換了床睡不著，Sereno 有為旅行準備的場景，雨聲、海浪等實地錄音可以自己疊加混音，"
                           "睡眠計時器會慢慢淡出；完全離線，山上收訊不好也能播。"),
                ("photocream", "想讓出遊照片有底片感，PhotoCream Pro 有超過 100 種底片風格，按快門前就能預覽，還能加上日期戳記。"),
                ("unblurry", "在車上拍糊了、夜景太暗，Unblurry Pro 的銳化與低光源模式可以在手機上把照片救回來，照片不會上傳。"),
            )),
            ("收假前一晚：鬧鐘和相簿", (
                ("easyam", "連假前不必一個個關鬧鐘：EasyAM 國定假日自動不響、補班日照響。遇到臨時宣布的放假或自己多請的假，"
                           "設成休假或一鍵只跳過下一次就好，收假那天照常叫你起床。"),
                ("picclear", "回家一看相簿多了幾百張連拍。PicClear Pro 會把相似照片分組並建議保留最好的一張，刪除前可以先完整檢視。"),
            )),
        ),
        "steps_title": "出發前一晚的 5 分鐘清單",
        "steps": (
            "在共用行程裡寫清楚每天的集合時間與地點，群組裡只傳這一份。",
            "看一次外出指數和降雨，每個戶外行程旁邊先放一個室內備案。",
            "記帳先建好這趟旅程、講好怎麼分攤，每次付錢當下就記一筆，不要等回家才對發票。",
            "把訂房確認、票券截圖先找一次，確定到現場搜得到。",
            "收假前一晚確認鬧鐘：要上班上課的那天，鬧鐘要照常響。",
        ),
        "faqs": (
            ("一起編的行程資料放在哪裡？",
             "TripBee 的核心旅程規劃可以離線使用；啟用 iCloud 後，旅程、備註、打包清單等資料存在你自己的私人 iCloud 並同步，"
             "受邀的人可以查看及編輯共享旅程。開發者沒有旅行資料伺服器，也看不到這些內容。"),
            ("記帳 App 可以直接算出每個人要付多少嗎？",
             "G+Money 負責把每一筆記下來、依旅程小計，可以匯出純文字或 CSV 給大家對帳；要把一筆帳拆給幾個人，"
             "用 CalDaily 的小費與分帳工具計算。兩個搭配用最清楚。"),
            ("臨時宣布的放假，EasyAM 會自動知道嗎？",
             "EasyAM 內建 67 個國家與地區的假日資料，國定假日和地方假日會自動跳過；臨時宣布的放假（例如颱風假），"
             "用「只跳過下一次」處理明天早上那一次就好，原本的規則不變。"),
            ("山上沒有網路也能用嗎？",
             "TripBee 的核心旅程規劃、G+Money 的記帳與換算（使用已儲存的匯率）和 Sereno 的音效都能離線使用。"),
        ),
        "related": (
            (_answers("best-trip-itinerary-planner-app-for-iphone"), "行程規劃 App 怎麼選"),
            (_answers("best-travel-money-app"), "旅遊記帳 App 怎麼選"),
            (_answers("tip-split-discount-tax-tools-app-for-iphone"), "小費、分帳、折扣與稅金計算 App"),
            (_answers("traveling-with-young-kids-what-to-prepare-the-week-before"), "帶小孩旅行，出發前一週的清單"),
            (f"{LANG}/{SECTION}/{DUO_SLUG}.html", "iPhone Duo 必裝 App：已滿版支援清單"),
            (f"{LANG}/{SECTION}/{CLEAN_SLUG}.html", "連假大掃除與整理待辦清單"),
        ),
    },
    {
        "slug": STUDY_SLUG,
        "seg": "study",
        "title": "連假讀書計畫怎麼排？補進度、不滑手機的 iPhone App（2026）",
        "h1": "連假讀書計畫：補進度、不滑手機",
        "desc": ("連假想補讀書進度卻一直滑手機？用番茄鐘鎖住會分心的 App、翻面計時、考試倒數和多益弱點診斷，"
                 "把連假排成做得完的讀書計畫，附每日時段範本與 App Store 下載連結。"),
        "lead": "連假讀書計畫最常見的版本是「連假讀完五章」，結果第一天睡到中午、最後一晚才開始焦慮。",
        "intro": (
            "比較做得到的排法是：每天只固定兩到三個專心時段，每段只做一件事，而且在那段時間裡手機真的拿不起來。"
            "其餘時間照常休息、出門，收假前留半天複習，不排新進度。",
            "下面的 App 分成四類：先把要做的事和考試日放到眼前、讀書時段不滑手機、補進度時知道自己哪裡弱，"
            "以及家裡有小學生時怎麼一起補。每一款都附一句實際用法。",
        ),
        "groups": (
            ("先把要做的事和考試日放到眼前", (
                ("mochi", "把連假要讀的東西寫成清單，一張清單只放 4 件，例如「數學第 3 章習題」「英文單字 2 個單元」，"
                          "做完輕點小圓圈打勾；清單放在主畫面小工具，解鎖手機第一眼就看到。"),
                ("countdaysnow", "段考、學測、多益還剩幾天？CountDaysNow 把考試日設成倒數，剩 7 天、3 天、1 天都會提醒，"
                                 "鎖定畫面和動態島也能一直顯示倒數。"),
            )),
            ("讀書時段：不滑手機、看得到時間", (
                ("lockhour", "LockHour Pro 的學習模式是番茄鐘循環加休息，開始後選定的 App 立刻被封鎖、時間到自動解鎖；"
                             "開啟強制模式的話，想提前結束要先倒數並打字確認，讓你有機會改變主意。"),
                ("studydown", "Studydown 用最簡單的方法防分心：選好科目、按開始，把手機螢幕朝下放在桌上；"
                              "拿起手機會依你設定的寬限時間暫停，離開 App 的時間也不會算進去。"),
                ("sereno", "家裡太吵就開 Sereno，裡面有為深度專注與學習準備的場景，白噪音、粉紅噪音、雨聲可以疊在一起各自調音量。"),
            )),
            ("補進度：知道自己哪裡弱", (
                ("aim990", "準備多益的人，Aim990 先用 8 分鐘診斷找出聽讀最弱的 3 項技能，連假每天只練其中一項；"
                           "考前 1、3、7、14 天還有緊急模式。"),
                ("wordmate", "零碎時間背單字：Wordmate 有 44 種語言、14 個生活主題，學英文時每個字都附例句和發音，"
                             "主畫面互動小工具上就能直接背。"),
                ("wordmatelite", "怕又在第三天放棄的話，Wordmate Lite 一次只練 5 個字，每日目標可以設 5、10、15 或 20 個字。"),
                ("sononote", "讀完一章，用 Sono Note 錄下自己把重點講一遍，幾秒內整理成摘要、重點和待辦，可以匯出成文字、Markdown 或 PDF。"),
                ("scanto", "講義、考卷掃成 PDF，ScanTo Pro 會在手機上辨識文字，之後搜尋關鍵字就知道是哪一張，全程離線。"),
                ("notesstudio100", "用 100 Notes Studio 手寫整理筆記、直接在 PDF 講義上標註，頁面錄音和學習複習工具也在同一個地方。"),
                ("onepageppt", "連假還有報告要交，OnePage PPT 可以把筆記、截圖或 PDF 整理成一頁 16:9 投影片，先看第一版再換方向挑。"),
            )),
            ("家裡有小學生", (
                ("lumimath", "Lumi數學星球：探索版讓家長看到學習進度、針對弱項加強練習，還能列印附解答的學習單。"),
                ("lumibopomofopro", "要幼小銜接的孩子，Lumi注音星球 Pro 練拼讀、聲調和筆順描寫，還能列印學習單在紙上再練一次。"),
            )),
        ),
        "steps_title": "連假每天的讀書時段範本",
        "steps": (
            "上午兩個 50 分鐘時段，留給最需要專心的科目，例如習題和閱讀測驗；中間休息 10 分鐘。",
            "下午只排一個時段，用來補筆記或背單字，其餘時間照常出門或休息。",
            "晚上花 10 分鐘把今天的清單打勾，沒做完的移到明天，不要硬撐熬夜。",
            "每個時段只放一件事，做完才看手機。",
            "收假前留半天複習，不排新進度。",
        ),
        "faqs": (
            ("連假讀書一天讀多久比較實際？",
             "與其排滿一整天，不如每天固定 2 到 3 個專心時段，每段 50 分鐘左右。做得到的計畫，比排得很滿卻做不完的計畫更能補進度。"),
            ("LockHour Pro 和 Studydown 差在哪？",
             "LockHour Pro 是在設定的時間內把會分心的 App 鎖住，時間到自動解鎖；Studydown 用手機螢幕朝下計時，拿起手機就暫停，"
             "並把每個項目投入的時間記下來。想要強制力選前者，想看每科花了多少時間選後者。"),
            ("這些 App 要註冊帳號嗎？",
             "Aim990、Studydown 和 ScanTo Pro 都不用註冊帳號，學習或掃描的紀錄留在你的裝置上。"),
        ),
        "related": (
            (_answers("best-app-to-block-social-media-while-studying-iphone"), "讀書時封鎖社群媒體的 App"),
            (_answers("best-study-time-tracker-no-subscription-app"), "讀書時間追蹤 App 怎麼選"),
            (f"{LANG}/{SECTION}/{DUO_SLUG}.html", "iPhone Duo 必裝 App：已滿版支援清單"),
            (f"{LANG}/{SECTION}/{CLEAN_SLUG}.html", "連假大掃除與整理待辦清單"),
        ),
    },
    {
        "slug": CLEAN_SLUG,
        "seg": "clean",
        "title": "連假大掃除與整理待辦：清單怎麼排、手機也一起清（2026）",
        "h1": "連假大掃除與整理待辦清單",
        "desc": ("連假想把家裡和手機一起整理乾淨？用可愛待辦清單拆大掃除、記下上次換濾網的日期、清相簿與截圖、"
                 "把紙本收據掃成 PDF，附排法範本與 App Store 下載連結。"),
        "lead": "「整理全家」這種待辦太大，寫下去只會一直留在清單上。拆成一區一張清單，才會真的打勾。",
        "intro": (
            "連假在家，很多人想順便大掃除，但常常第一天就被「從哪裡開始」卡住。比較做得完的方法是：一個區域一張清單，"
            "每張只放幾件 30 分鐘內做得完的小事，做完就打勾；像冷氣濾網、床單這種「多久清一次」的事，清完順手記下日期。",
            "手機裡的照片、截圖、連結和紙本文件，也可以用同樣的方法整理。下面照「拆清單、清手機、收紙本、整理完再買」"
            "四步，挑出對應得到的 App。",
        ),
        "groups": (
            ("拆成做得完的清單", (
                ("mochi", "用 Mochi 可愛待辦清單替每個區域開一張清單，例如「廚房」放「清排油煙機濾網」「丟過期調味料」；做完輕點小圓圈打勾，"
                          "清單放在主畫面小工具和 Apple Watch 上，邊打掃邊看。缺的清潔用品順手寫進購物清單。"),
                ("mochidonestamp", "冷氣濾網、除濕機水箱、床單這類固定週期的家事，清完在 Mochi DoneStamp 點一下就記下時間；"
                                   "設好大約或精準的週期，下次提醒會從這次實際完成的時間重新算。"),
                ("lumimission", "家裡有 3 到 7 歲的孩子，Lumi 任務星球把收玩具變成每日小任務，孩子完成一步就點一下，兔兔夥伴會跳起來歡呼，比一直催有用。"),
            )),
            ("手機也大掃除", (
                ("picclear", "PicClear Pro 在手機上掃描相簿，找出重複照片、相似的連拍、舊截圖、模糊照片和最吃空間的大型影片；"
                             "刪除前可以先完整檢視，刪掉的照片會先進「最近刪除」，一段時間內還能復原。"),
                ("shotinbox", "幾千張截圖不一定要刪：ShotInbox AI 會辨識截圖裡的文字並自動分成購物、收據、票券、食譜等類別，"
                              "用文字就搜得到；它不會自動刪除任何截圖。"),
                ("savetag", "散落在聊天室和備忘錄的連結，用分享選單一鍵存進 SaveTag，會自動分好美食、食譜、居家、購物等標籤，"
                            "「重新發現」每天挑幾則帶你回頭看。"),
            )),
            ("收好紙本與文件", (
                ("scanto", "抽屜裡的保固卡、收據、合約掃成清楚的 PDF，ScanTo Pro 會自動分類成收據、證件、合約等並辨識文字，"
                           "之後搜尋內文就找得到；全程離線，掃描檔不會碰到伺服器。"),
                ("maskmyfile", "整理出要轉賣的家電，要傳保固卡或發票照片給買家前，先用 Mask My File 永久遮蔽上面的私密資訊，處理全在手機上完成。"),
            )),
            ("整理完再買、順手檢查網路", (
                ("hourstag", "大掃除完很容易想一次買齊收納用品。下單前用 HoursTag 把價格換算成要工作幾小時，"
                             "再標成必要、想要或衝動，買得比較清楚。"),
                ("wifiaid", "打掃時把分享器換了位置，網路變慢？WiFi Aid 一鍵檢查 Wi-Fi、DNS 與網際網路連線，告訴你最可能的故障原因。"),
            )),
        ),
        "steps_title": "連假大掃除的排法",
        "steps": (
            "第一天上午先列清單：一個區域一張，每張不超過 4 件，從最在意的區域開始。",
            "每清完一區就打勾，順手記下濾網、床單這類週期性家事的日期。",
            "下午留 30 分鐘清手機：先刪重複照片與大型影片，再整理截圖和連結。",
            "最後一天把紙本收據、保固卡掃成 PDF，紙本分類收好。",
            "缺的清潔和收納用品寫進購物清單，出門一次買齊。",
        ),
        "faqs": (
            ("待辦清單一直做不完怎麼辦？",
             "把大事拆成 30 分鐘內做得完的小事，一張清單只放幾件，做完才加新的。清單看得完，才會每天打開。"),
            ("清相簿會不會刪錯照片？",
             "PicClear Pro 在你確認前不會刪除任何東西，智慧選取會在每組保留建議的最佳照片，也不會自動選取你的「最愛」；"
             "刪除的項目會先進入「照片」的「最近刪除」，一段時間內可以復原。"),
            ("Mochi 和 Mochi DoneStamp 差在哪？",
             "Mochi 是待辦清單，列「這次要做的事」；Mochi DoneStamp 是生活事件記憶器，記「上次做這件事是什麼時候」，"
             "適合濾網、床單這類固定週期的家事。"),
        ),
        "related": (
            (_answers("todo-list-never-finished-five-a-day-timebox-weekend-reset"), "待辦清單一直沒做完？每天 5 件、週末清理"),
            (_answers("todo-list-app-first-day-setup-home-screen-widget-apple-watch-two-lists"), "待辦清單 App 第一天怎麼設定"),
            (_answers("best-link-organizer-app"), "存下的連結怎麼整理"),
            (f"{LANG}/{SECTION}/{DUO_SLUG}.html", "iPhone Duo 必裝 App：已滿版支援清單"),
            (f"{LANG}/{SECTION}/{STUDY_SLUG}.html", "連假讀書計畫：補進度、不滑手機"),
        ),
    },
)

CSS = """
:root{--bg:#f7f7fb;--card:#fff;--ink:#161622;--muted:#5d6370;--line:#e6e7ef;--brand:#5b5ff2;--ok:#0f8f5f}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC","Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.7}
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
.steps{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px 14px 36px}
.steps li{margin:.35rem 0}
.cards{display:grid;gap:12px}
.app{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.app p{margin:.3rem 0}
.duo-badge{display:inline-block;font-size:.78rem;color:var(--ok);background:#e9f7f0;border-radius:999px;padding:.1rem .6rem}
.cta{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:.5rem}
.dl{display:inline-block;background:var(--brand);color:#fff;padding:.45rem 1rem;border-radius:10px;text-decoration:none;font-weight:600;font-size:.92rem}
.android-play{font-size:.85rem;margin:.2rem 0 0}
.more{font-size:.88rem}
details.faq{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.7rem 1rem;margin:.6rem 0}
details.faq summary{cursor:pointer;font-weight:600}
.related ul{padding-left:1.2rem}
.legal{font-size:.78rem;color:var(--muted);margin:2rem 0 2.5rem}
@media (prefers-color-scheme:dark){:root{--bg:#121218;--card:#1c1c24;--ink:#ececf3;--muted:#a3a7b3;--line:#2c2d38;--brand:#8f93ff;--ok:#5fd3a0}
header.top{background:#16161d}.lead{color:#d6d8e0}.duo-badge{background:#123327}}
""".strip()


# 頁首主推卡的樣式：只加在有 spotlight 的頁（其他頁位元組不變）。
SPOT_CSS = """
.spot{background:var(--card);border:2px solid var(--brand);border-radius:16px;padding:16px 18px;margin:1.2rem 0}
.spot h2{margin:0 0 .5rem}
.spot ul{margin:.4rem 0 .6rem;padding-left:1.2rem}
.spot li{margin:.2rem 0}
""".strip()


class GenerationError(RuntimeError):
    """The pages cannot be published as written; nothing is written."""


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def url_for(relative: str) -> str:
    return f"{SITE}/{relative}"


def page_relative(slug: str) -> str:
    return f"{LANG}/{SECTION}/{slug}.html"


def campaign(key: str, seg: str) -> str:
    """款 × 台灣 × 詞群（ss 檔期）的 gw 階梯碼（gw_campaign.py）；哪一頁（族群）由點擊計數的 p 分。"""
    if not re.fullmatch(r"[a-z]+", seg or ""):
        raise GenerationError(f"bad segment: {seg!r}")
    try:
        token = gw_campaign.campaign(key, GW_GROUP, "tw")
    except gw_campaign.GwCampaignError as error:
        raise GenerationError(str(error)) from error
    if len(token) > MAX_CT:
        raise GenerationError(f"campaign token does not fit: {token!r}")
    return token


def store_url(app_id: str, key: str, seg: str) -> str:
    url = (f"https://apps.apple.com/tw/app/id{app_id}"
           f"?pt={PROVIDER_TOKEN}&ct={campaign(key, seg)}&mt=8")
    return validated_app_store_url(url, app_id, expected_locale=LANG, require_campaign=True,
                                   provider_token=PROVIDER_TOKEN)


def promo_line(path: Path = CLAIM_LINES) -> str:
    lines = json.loads(path.read_text(encoding="utf-8"))["promo_line"]
    line = lines.get(LANG) if isinstance(lines, dict) else None
    if not line:
        raise GenerationError("claim_lines.json has no zh-Hant promo_line")
    return line


def lookup_versions(app_ids, opener=urllib.request.urlopen) -> dict[str, str]:
    """{app_id: live version}: Taiwan storefront first, then US; a failed request stops (no claim)."""
    out: dict[str, str] = {}
    for cc in ("tw", "us"):
        todo = sorted(i for i in set(app_ids) if i not in out)
        if not todo:
            break
        try:
            with opener(LOOKUP_URL.format(ids=",".join(todo), cc=cc), timeout=30) as response:
                rows = json.loads(response.read().decode("utf-8")).get("results") or []
        except Exception:  # noqa: BLE001 - lookup failure means no claim
            break
        for row in rows:
            if str(row.get("trackId")) in todo and row.get("version"):
                out[str(row["trackId"])] = str(row["version"])
    return out


def claimable_apps(load=duo_list.load, versions=None) -> tuple[dict[str, str], list[dict]]:
    """{key: app_id} that may carry the iPhone Duo claim right now, and the refusals."""
    apps, rejected, error = load()
    if error:
        raise GenerationError(f"duo_verified.json: {error}")
    live = lookup_versions(a["app_id"] for a in apps) if versions is None else versions
    out, refused = {}, list(rejected)
    for app in apps:
        if live.get(app["app_id"]) != app["live_version"]:
            refused.append({"source_key": app["source_key"], "app_id": app["app_id"],
                            "reason": f"live_version_mismatch:{live.get(app['app_id'])!r}"})
            continue
        out[app["slug"]] = app["app_id"]
    return out, refused


def manifest_ids(path: Path = HERE / "live_app_manifest.json") -> dict[str, str]:
    apps = json.loads(path.read_text(encoding="utf-8")).get("apps", {})
    return {key: str(value["app_id"]) for key, value in apps.items() if value.get("app_id")}


def check_store_names(data_dir: Path = ROOT / "data") -> list[str]:
    problems = []
    for key, name in NAMES.items():
        path = data_dir / f"{key}_full.json"
        if not path.exists():
            problems.append(f"{key}: missing {path.name}")
            continue
        store = (json.loads(path.read_text(encoding="utf-8")).get(LANG) or {}).get("name")
        if store != name:
            problems.append(f"{key}: store name {store!r} != {name!r}")
    return problems


def _card(key: str, text: str, *, app_id: str, seg: str, badge: str | None, link_guide: bool) -> str:
    parts = [f'<article class="app" id="app-{esc(key)}">', f"<h3>{esc(NAMES[key])}</h3>"]
    if badge:
        parts.append(f'<p class="duo-badge">{esc(badge)}</p>')
    parts.append(f"<p>{esc(text)}</p>")
    cta = f'<a class="dl" href="{esc(store_url(app_id, key, seg))}" rel="noopener">在 App Store 下載 →</a>'
    if link_guide:
        cta += f' <a class="more" href="{esc(url_for(f"{LANG}/{key}.html"))}">看完整介紹</a>'
    parts.append(f'<p class="cta">{cta}</p>')
    parts.append("</article>")
    return "\n".join(parts)


def spotlight_block(spot: dict, app_id: str | None, relative: str) -> str:
    """頁首主推卡：一款、幾句商店原文、一個台灣商店直連（ct＝ln_<key>_<seg>_tw_gw_1023）。"""
    if not app_id:
        raise GenerationError(f"{relative}: spotlight {spot['key']} is not in the live app manifest")
    points = "".join(f"<li>{esc(point)}</li>" for point in spot["points"])
    href = esc(store_url(app_id, spot["key"], spot["seg"]))
    return (f'<section class="spot" id="pick-{esc(spot["key"])}"><h2>{esc(spot["title"])}</h2>'
            f'<p>{esc(spot["lead"])}</p><ul>{points}</ul>'
            f'<p class="cta"><a class="dl" href="{href}" rel="noopener">{esc(spot["cta"])}</a></p></section>')


def page_groups(spec: dict, claimable: dict[str, str]) -> list[tuple[str, list[tuple[str, str]]]]:
    if spec["seg"] == "duo":
        groups = [(title, [(key, DUO_LINES[key]) for key in keys if key in claimable])
                  for title, keys in DUO_GROUPS]
    else:
        groups = [(title, list(items)) for title, items in spec["groups"]]
    return [(title, items) for title, items in groups if items]


def render(spec: dict, claimable: dict[str, str], ids: dict[str, str], badge: str) -> str:
    relative = page_relative(spec["slug"])
    canonical = url_for(relative)
    updated = spec.get("updated", UPDATED)
    groups = page_groups(spec, claimable)
    is_duo = spec["seg"] == "duo"
    count = sum(len(items) for _, items in groups)
    body = []
    toc = []
    for number, (title, items) in enumerate(groups, 1):
        anchor = f"{spec['seg']}-{number}"
        toc.append(f'<a href="#{anchor}">{esc(title)}</a>')
        cards = []
        for key, text in items:
            app_id = claimable.get(key) or ids.get(key)
            if not app_id:
                raise GenerationError(f"{relative}: {key} is not in the live app manifest")
            cards.append(_card(key, text, app_id=app_id, seg=spec["seg"],
                               badge=badge if key in claimable and not is_duo else None, link_guide=is_duo))
        body.append(f'<section id="{anchor}"><h2>{esc(title)}</h2>\n<div class="cards">\n'
                    + "\n".join(cards) + "\n</div></section>")
    intro = list(spec["intro"])
    if is_duo:
        intro[1] = intro[1].replace("依用途分成幾類", f"共 {count} 款，依用途分成 {len(groups)} 類")
    steps = "".join(f"<li>{esc(step)}</li>" for step in spec["steps"])
    faqs = "".join(
        f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in spec["faqs"]
    )
    related = "".join(f'<li><a href="{esc(url_for(rel))}">{esc(label)}</a></li>' for rel, label in spec["related"])
    steps_block = f'<section><h2>{esc(spec["steps_title"])}</h2><ol class="steps">{steps}</ol></section>'
    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App 指南", "item": url_for(f"{LANG}/index.html")},
            {"@type": "ListItem", "position": 2, "name": spec["h1"], "item": canonical},
        ]},
        {"@context": "https://schema.org", "@type": "ItemList", "name": spec["h1"], "numberOfItems": count,
         "itemListElement": [
             {"@type": "ListItem", "position": i, "name": NAMES[key], "url": url_for(f"{LANG}/{key}.html")}
             for i, key in enumerate((key for _, items in groups for key, _ in items), 1)
         ]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in spec["faqs"]
        ]},
    ]
    ld_json = json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/")
    sections = [f'<nav class="toc" aria-label="分類">{" · ".join(toc)}</nav>'] + body + [steps_block]
    if spec.get("spotlight"):
        sections.insert(0, spotlight_block(spec["spotlight"], claimable.get(spec["spotlight"]["key"])
                                           or ids.get(spec["spotlight"]["key"]), relative))
    if is_duo:  # the page itself is the claim: one reviewed line above the list, not one per card
        sections.insert(0, f'<p class="duo-badge">{esc(badge)}</p>')
    legal = f'<p class="legal">{esc(LEGAL)}</p>' if spec.get("legal") else ""
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec['title'])}</title>
<meta name="description" content="{esc(spec['desc'])}">
<meta name="robots" content="index,follow,max-image-preview:large">
{GW_META}
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:locale" content="zh_TW">
<meta property="og:title" content="{esc(spec['title'])}">
<meta property="og:description" content="{esc(spec['desc'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="article:modified_time" content="{updated}">
<style>
{CSS + (chr(10) + SPOT_CSS if spec.get("spotlight") else "")}
</style>
<script type="application/ld+json">
{ld_json}
</script>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{esc(url_for(f'{LANG}/index.html'))}">iOS App 指南</a><nav><a href="{esc(url_for(f'{LANG}/answers/index.html'))}">答案</a> · <a href="{esc(url_for(f'{LANG}/alternatives/'))}">替代方案</a> · <a href="{esc(url_for('about.html'))}">關於</a></nav></div></header>
<main class="wrap">
<div class="breadcrumb"><a href="{esc(url_for(f'{LANG}/index.html'))}">首頁</a> / 季節推薦</div>
<h1>{esc(spec['h1'])}</h1>
<p class="lead">{esc(spec['lead'])}</p>
<p class="updated">更新日期：{updated}</p>
{''.join(f'<p>{esc(p)}</p>' for p in intro)}
{chr(10).join(sections)}
<section><h2>常見問題</h2>{faqs}</section>
<section class="related"><h2>相關頁面</h2><ul>{related}</ul></section>
{legal}
</main>
</body>
</html>
"""


def visible_text(source: str) -> str:
    main = re.search(r"<main\b.*?</main>", source, re.S)
    text = re.sub(r"<[^>]+>", " ", main.group(0) if main else "")
    return html.unescape(text)


def page_problems(relative: str, source: str, pages: Path | None = None) -> list[str]:
    problems = []
    text = visible_text(source)
    if len(CJK.findall(text)) < 450:
        problems.append(f"{relative}: dedicated text under 450 characters")
    head = source.split("</head>", 1)[0]
    for found in BANNED.finditer(html.unescape(re.sub(r"<script\b.*?</script>", "", text + head, flags=re.S))):
        problems.append(f"{relative}: banned price/free wording {found.group(0)!r}")
    for href in re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', source):
        url = html.unescape(href)
        try:
            validated_app_store_url(url, expected_locale=LANG, require_campaign=True)
        except ValueError as error:
            problems.append(f"{relative}: {error}")
    cards = re.findall(r'<article class="app"[^>]*>.*?</article>', source, re.S)
    if not cards:
        problems.append(f"{relative}: no app cards")
    for card in cards:
        if "https://apps.apple.com/tw/app/id" not in card:
            problems.append(f"{relative}: card without a direct App Store link")
    if pages is not None:
        for href in set(re.findall(r'href="(' + re.escape(SITE) + r'/[^"#]+)"', source)):
            target = href[len(SITE) + 1:]
            if target.endswith("/"):
                target += "index.html"
            path = pages / target
            if target == relative or target.startswith(f"{LANG}/{SECTION}/"):
                continue
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


def build(claimable: dict[str, str], ids: dict[str, str], android_apps: dict, *, badge: str,
          pages: Path | None = None) -> dict[str, str]:
    out = {}
    for spec in PAGE_SPECS:
        relative = page_relative(spec["slug"])
        out[relative] = finalize(render(spec, claimable, ids, badge), relative, android_apps)
    problems = [p for relative, source in out.items() for p in page_problems(relative, source, pages)]
    for relative in out:
        for rel, _ in next(s for s in PAGE_SPECS if page_relative(s["slug"]) == relative)["related"]:
            if rel.startswith(f"{LANG}/{SECTION}/") and rel not in out:
                problems.append(f"{relative}: related page {rel} is not generated")
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
    names = check_store_names()
    if names:
        raise GenerationError("store names drifted:\n" + "\n".join(names))
    claimable, refused = claimable_apps()
    ids = manifest_ids()
    unknown = sorted(set(NAMES) - set(ids))
    if unknown:
        raise GenerationError(f"not in live_app_manifest.json: {unknown}")
    try:
        android_apps = android_play.load_snapshot()
    except (OSError, ValueError) as error:  # an untrusted snapshot publishes no Play link
        print(f"android snapshot ignored: {error}", file=sys.stderr)
        android_apps = {}
    out = build(claimable, ids, android_apps, badge=promo_line(), pages=pages)
    sitemap_path = pages / SITEMAP
    sitemap = merge_sitemap(sitemap_path.read_text(encoding="utf-8"), [url_for(r) for r in out])
    changed = []
    for relative, source in {**out, SITEMAP: sitemap}.items():
        path = pages / relative
        if not path.exists() or path.read_text(encoding="utf-8") != source:
            changed.append(relative)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
    missing = sorted(set(claimable) - set(DUO_LINES))
    print(json.dumps({"pages": sorted(out), "changed": changed, "duo_claimable": len(claimable),
                      "duo_listed": sum(1 for k in DUO_LINES if k in claimable),
                      "duo_claimable_without_line": missing, "refused": refused,
                      "android_apps": len(android_apps)}, ensure_ascii=False, indent=1))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
