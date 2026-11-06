#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜尋實況意圖頁：TripBee Cute：可愛旅行手帳（tripbeecute）新上架 → <Guide>/zh-Hant/seasonal/<slug>.html。

背景：2026-11-05 上架；aso/search_reality/tripbeecute.md 量到台灣主詞「可愛 旅行手帳」首量 #5（42 款），
前 3 名都是一般手帳 App、沒有旅行專用，是最有機會衝第 1 的母語詞。集中國澳門、香港、台灣
（reports/tripbeecute/rank_focus.json），這頁用繁中寫給「想把行程排成一本可愛手冊」的人。

沿用第 3 組產生器（gen_search_reality_g3.py）的版面、檢查、Google Play 補連結與 sitemap 合併，只換頁面內容
（同 gen_search_reality_metrotimehelper.py 的做法）。規則：
- 功能句只取 data/tripbeecute_full.json 繁中商店文案；不寫價格、免費、Free、Pro，也不寫解鎖方式與內購名稱。
- 每頁一張主卡，附台灣 App Store 直連（pt＋ct＋mt）；ct＝gw 階梯碼（gw_campaign.py，款 × 國家 × 詞群 sr）。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 主卡的「完整介紹」連到 zh-Hant/tripbeecute.html：指南站逐語系頁產生前，g3 的內部連結檢查會擋，
  所以本檔與產出頁只在指南站收錄本款後才併入主線（判準見 reports/tripbeecute/action_cards.md）。
- 專屬內容：中文 ≥450 字。只寫這頁與 sitemap_seasonal_zh-Hant.xml 的這一列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_tripbeecute.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_tripbeecute.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gen_search_reality_g3 as g3  # noqa: E402

LANGS = dict(g3.LANGS)
APP_IDS = {"tripbeecute": "6826987407"}
BANNED = g3.BANNED

PAGE_SPECS: list[dict] = [
    # 台灣：「可愛 旅行手帳」（主詞，首量 #5）、「旅行手帳」「出國 行程表」「出國倒數」
    {
        "key": "tripbeecute", "lang": "zh-Hant",
        "slug": "keai-lvxing-shouzhang-chuguo-xingchengbiao-daoshu-zhhant",
        "terms": ["可愛 旅行手帳", "旅行手帳", "出國 行程表", "出國倒數"],
        "title": "可愛旅行手帳怎麼做？把整趟行程排成一本插畫手冊的 5 個重點",
        "desc": "想把出國行程做成可愛的旅行手帳，又不想在截圖、訂位信和備忘錄之間翻來翻去？整理挑選旅行手帳 App 的重點、和朋友一起排行程的做法，附 TripBee Cute 的設定步驟與台灣 App Store 直連。",
        "h1": "可愛旅行手帳：出國倒數、航班、每日行程和行李清單收進同一本",
        "lead": "在 App Store 搜「可愛 旅行手帳」的人，多半正在為下一趟旅行興奮：機票訂好了，行程卻還散落在截圖、訂位信和好幾則備忘錄裡。",
        "intro": [
            "實體旅行手帳很可愛，可是貼貼紙、抄航班、改行程都很花時間，出發前一晚臨時改計畫更是整頁重寫。手機上的行程工具很方便，卻常常長得像試算表，打開來一點都不期待。很多人真正想要的，是兩者的中間：排起來像手機一樣快，翻起來像手帳一樣可愛。",
            "我們在 2026 年 11 月實際查了台灣 App Store：打「可愛 旅行手帳」跳出四十多款，排在最前面的大多是一般的日記與手帳 App，真正為旅行設計、把航班、倒數和每日行程放在同一本的並不多。下面整理挑選時要看的重點，以及實際的做法。",
        ],
        "sections": [
            ("挑旅行手帳 App，先看這 5 件事", [], [
                "整趟旅行一頁看完：封面、出發倒數、航班、每天的行程、行李清單和筆記都在同一本，不必在好幾個 App 之間切來切去。",
                "每一天分得清楚：每天有自己的顏色，可以只看某一天，也可以看全部。",
                "資料就放在行程旁邊：照片、票券和備註貼在對應的行程旁，到了現場不用再翻相簿找截圖。",
                "能和旅伴一起排：用 iCloud 邀請朋友共同編輯同一本手冊，變更會同步到彼此的裝置（對方也需要安裝 App）。",
                "分享出去對方打得開：分享成網頁手冊，任何瀏覽器或聊天 App 都能打開，離線也能看。",
            ]),
            ("三種最常見的旅行，各自怎麼排", [
                "第一次出國自由行：先幫旅行取個名字、挑一張插畫封面，加上登機證風格的航班卡（時間、航廈、訂位代號），再把每一天填滿。出發倒數會一天天往下跳，主畫面與鎖定畫面小工具也看得到下一趟旅行。",
                "閨蜜旅行、畢業旅行：大家各自查好的景點，直接加進同一本手冊；每個行程都能貼上貼紙、完成就打勾、隨時調整順序。遇到下雨，切換成從主計畫複製的雨天備案就好。",
                "全家出遊、環島、蜜月：行李清單可以依同行者、季節與天數產生，旅行筆記與貼心提醒放在最後一頁；習慣用試算表排行程的人，可以匯出 CSV 範本填好再匯入，自動變成一本手冊。",
            ], []),
            ("出國前一晚最常忘的事", [
                "航班時間與航廈、訂位代號、目的地天氣與當地時間，最好都放在打開就看得到的地方。TripBee Cute 的手冊裡有出發倒數、目的地天氣與當地時間，Apple Watch 上也看得到倒數和下一個行程。",
                "不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有在你開啟同步時，才會存到你自己的私人 iCloud。",
            ], []),
        ],
        "steps_title": "5 分鐘做出第一本旅行手冊",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行並取個名字。",
            "從插畫封面裡挑一張：城市、地標、季節、旅行心情都有。",
            "加上航班卡，出發倒數就會開始跑。",
            "把每一天的行程填進去，替每天命名、貼上貼紙，照片和票券放在行程旁。",
            "想和朋友一起排，用 iCloud 邀請對方共同編輯；或分享成網頁手冊傳到聊天群組。",
        ],
        "cards": [
            ("tripbeecute", "把整趟旅行收進一本可愛的插畫手冊：出國倒數、航班、每日行程和行李清單都在同一頁。每一天都有自己的顏色，照片、票券和備註就放在對應的行程旁邊；用 iCloud 邀請朋友一起編輯同一本手冊，也能分享成任何瀏覽器都能打開、離線也能看的網頁手冊。支援主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式與 50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("可以和朋友一起排同一份行程嗎？", "可以。透過 iCloud 邀請朋友共同編輯同一本手冊，變更會同步到彼此的裝置；對方也需要安裝 TripBee Cute。"),
            ("朋友沒有裝 App，看得到行程嗎？", "可以分享成網頁手冊：一個網頁檔，任何瀏覽器或聊天 App 都能打開，離線也能看，倒數也會持續跑。"),
            ("原本用試算表排好的行程可以搬進來嗎？", "可以。匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就會自動變成一本手冊。"),
            ("需要註冊帳號嗎？", "不用。不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟同步時才會存到你自己的私人 iCloud。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁介紹的 App 為獨立開發；天氣資料來自 Open-Meteo，只會用到目的地。",
    },
]


def _install() -> None:
    """把本批的 App、頁面與檢查換進第 3 組產生器（其餘版面與檢查原樣沿用）。"""
    g3.LANGS = LANGS
    g3.APP_IDS = APP_IDS
    g3.PAGE_SPECS = PAGE_SPECS
    g3.BANNED = BANNED


def main(argv=None) -> int:
    _install()
    return g3.main(argv)


if __name__ == "__main__":
    sys.exit(main())
