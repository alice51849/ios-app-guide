#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜尋實況意圖頁：TripBee Cute：可愛旅行手帳（tripbeecute）新上架 → <Guide>/<lang>/seasonal/<slug>.html（台灣繁中兩頁＋韓文＋香港繁中）。

背景：2026-11-05 上架；aso/search_reality/tripbeecute.md 量到台灣主詞「可愛 旅行手帳」首量 #5（42 款），
前 3 名都是一般手帳 App、沒有旅行專用，是最有機會衝第 1 的母語詞。集中國澳門、香港、台灣
（reports/tripbeecute/rank_focus.json），這頁用繁中寫給「想把行程排成一本可愛手冊」的人。
2026-11-07 加韓文頁：韓國主詞「다꾸 여행」#45（54 款），前 10 幾乎全 0 則評分、離前 10 最近；寫給用貼紙、
插畫封面做可愛旅行手帳（여행 다이어리）的「다꾸」族群（韓文語系表、禁用字與韓文字數照 gen_search_reality_easyam.py）。

沿用第 3 組產生器（gen_search_reality_g3.py）的版面、檢查、Google Play 補連結與 sitemap 合併，只換頁面內容
（同 gen_search_reality_metrotimehelper.py 的做法）。規則：
- 功能句只取 data/tripbeecute_full.json 繁中／韓文商店文案；不寫價格、免費、Free、Pro，也不寫解鎖方式與內購名稱。
- 每頁一張主卡，附該國 App Store 直連（台灣、韓國；香港頁 spec "cc"＝hk 連香港店；pt＋ct＋mt）；ct＝gw 階梯碼（gw_campaign.py，款 × 國家 × 詞群 sr）。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 主卡的「完整介紹」連到 zh-Hant/tripbeecute.html：指南站逐語系頁產生前，g3 的內部連結檢查會擋，
  所以本檔與產出頁只在指南站收錄本款後才併入主線（判準見 reports/tripbeecute/action_cards.md）。
- 2026-11-08 加香港繁中頁：香港主詞「旅行手帳」「旅行 手帳」#72；語言目錄沿用 zh-Hant，spec "cc": "hk" 改連香港店。
- 2026-11-08 加台灣第二頁：「旅遊手帳」#21、「旅行 清單」#85；寫出發前打包清單與每日行程並排（預設台灣店，不需 cc）。
- 2026-11-10 加日文頁（「旅行 手帳」#17）與澳洲英文頁（「cute travel journal」#4，en-AU 目錄連澳洲店，sitemap 用既有 sitemap_seasonal_en_AU.xml）。
- 專屬內容：中文 ≥450 字、韓文 ≥450 個韓文字。只寫這兩頁與各語系 sitemap_seasonal_<lang>.xml 的這幾列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_tripbeecute.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_tripbeecute.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gen_search_reality_easyam as easyam  # noqa: E402
import gen_search_reality_g3 as g3  # noqa: E402

LANGS = dict(g3.LANGS)
LANGS["ko"] = easyam.LANGS["ko"]
# 澳洲英文：沿用英文介面字串，目錄 en-AU、連澳洲店（en-AU 是官方語系，商店國家 au 由 locale_storefronts.json 對應）。
LANGS["en-AU"] = dict(g3.LANGS["en"], store="en-AU", dir="en-AU", cc="au", og="en_AU", html="en-AU")
APP_IDS = {"tripbeecute": "6826987407"}
BANNED = easyam.BANNED
dedicated_size = easyam.dedicated_size

PAGE_SPECS: list[dict] = [
    # 台灣：「可愛 旅行手帳」（主詞，首量 #5）、「旅行手帳」「出國 行程表」「出國倒數」
    {
        "key": "tripbeecute", "lang": "zh-Hant",
        "slug": "keai-lvxing-shouzhang-chuguo-xingchengbiao-daoshu-zhhant",
        "terms": ["可愛 旅行手帳", "旅行手帳", "出國 行程表", "出國倒數", "可愛 行程"],
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
            ("想要一份可愛的行程表？", [
                "搜「可愛 行程」的人，常常是想把行程表排得好看一點，打開就有出發的心情。TripBee Cute 的每一天都有自己的顏色，逐日分色一眼就分得清楚，也能依日期篩選只看某一天；每趟旅行都有一張插畫封面，城市、地標、季節、旅行心情都有，像書架上的一本小手冊。",
                "已經在試算表裡排好行程也沒關係：匯出 CSV 範本，填好後再匯入，就會自動變成一本可愛的行程手冊，不必一格一格重新輸入。",
            ], []),
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
    # 韓國：「다꾸 여행」（主詞，#45、前 10 幾乎全 0 則評分）、「여행 다이어리」「여행 일정」「여행 디데이」
    {
        "key": "tripbeecute", "lang": "ko",
        "slug": "dakku-yeohaeng-diary-sticker-illust-pyoji",
        "terms": ["다꾸 여행", "여행 다이어리", "여행 일정", "여행 디데이"],
        "title": "다꾸 여행 다이어리 만드는 법: 스티커와 일러스트 표지로 여행 책자 한 권 완성하는 5가지 포인트",
        "desc": "여행 다이어리를 귀엽게 꾸미고 싶은데 캡처, 메일, 메모에 흩어진 일정 정리부터 막막한가요? 다꾸 감성 여행 앱 고르는 법과 친구와 함께 일정을 짜는 방법, TripBee Cute 사용 순서와 한국 App Store 바로가기를 정리했어요.",
        "h1": "다꾸 여행: 출발 디데이, 항공편, 하루 일정, 준비물까지 귀여운 책자 한 권에",
        "lead": "App Store에서 「다꾸 여행」을 검색하는 사람은 대부분 다음 여행을 앞두고 설레는 중이에요. 비행기 표는 끊었는데, 일정은 아직 캡처와 예약 메일, 메모 여러 개에 흩어져 있죠.",
        "intro": [
            "종이 다이어리에 스티커를 붙이고 마스킹 테이프를 두르는 다꾸는 정말 귀엽지만, 항공편을 옮겨 적고 일정을 고칠 때마다 한 페이지를 다시 꾸미는 건 시간이 꽤 걸려요. 출발 전날 갑자기 계획이 바뀌면 더 그렇고요. 반대로 휴대폰 일정 앱은 편하지만 표처럼 생겨서 열어 볼 때 설렘이 없어요. 많은 사람이 원하는 건 그 중간이에요. 휴대폰처럼 빠르게 짜고, 다이어리처럼 귀엽게 넘겨 보는 여행 책자.",
            "저희는 2026년 11월에 한국 App Store에서 「다꾸 여행」을 실제로 검색해 봤어요. 결과는 많지 않았고, 상위에는 일반 다이어리와 꾸미기 앱이 주로 보였어요. 항공편, 디데이, 날마다의 일정을 여행 한 권에 함께 담는 여행 전용 앱은 드물었어요. 아래에 고를 때 볼 포인트와 실제로 만드는 방법을 정리했어요.",
        ],
        "sections": [
            ("다꾸 여행 앱, 이 5가지부터 보세요", [], [
                "여행 전체를 한 페이지에서: 일러스트 표지를 펼치고 아래로 내리기만 하면 출발 디데이, 항공편, 날마다의 일정, 준비물 리스트와 메모까지 이어져요. 여러 앱을 오갈 필요가 없어요.",
                "꾸미는 재미: 도시, 랜드마크, 계절, 여행 기분을 담은 일러스트 표지를 고르고, 하루 일정마다 이름을 붙이고 스티커를 달 수 있어요.",
                "날짜마다 다른 색: 날짜마다 색이 달라 한눈에 구분되고, 날짜 필터로 그날 일정만 볼 수 있어요.",
                "기록은 일정 바로 옆에: 사진, 티켓, 메모를 해당 일정 옆에 보관해서 현지에서 앨범을 뒤질 필요가 없어요.",
                "친구와 함께, 친구에게 보여 주기: iCloud로 친구를 초대해 같은 책자를 함께 편집하고(친구도 TripBee Cute 필요), 웹 책자로 공유하면 어떤 브라우저나 메신저에서도 열리고 오프라인에서도 볼 수 있어요.",
            ]),
            ("자주 있는 세 가지 여행, 이렇게 꾸며요", [
                "첫 해외여행, 일본이나 제주 주말 여행: 여행 이름을 정하고 표지를 고른 뒤, 시간, 터미널, 예약 번호가 담긴 탑승권 스타일 항공편 카드를 넣어요. 출발 디데이가 하루씩 줄어들고, 홈 화면과 잠금 화면 위젯에서도 다음 여행 표지를 볼 수 있어요.",
                "우정 여행, 커플 여행: 각자 찾아 둔 장소를 같은 책자에 바로 추가해요. 일정마다 스티커를 붙이고, 다녀온 곳은 완료 체크하고, 순서도 언제든 바꿀 수 있어요. 비가 오면 메인 일정에서 복사해 둔 우천 플랜으로 바꾸면 돼요.",
                "가족 여행, 신혼여행: 동행, 계절, 여행 기간에 맞춘 준비물 리스트로 짐을 챙기고, 여행 메모와 다정한 알림은 마지막 페이지에 모아 둬요. 스프레드시트로 계획하는 편이라면 CSV 템플릿을 내보내 채운 뒤 가져오기만 하면 책자가 완성돼요.",
            ], []),
            ("출발 전날 자주 잊는 것", [
                "항공편 시간과 터미널, 예약 번호, 여행지 날씨와 현지 시간은 열자마자 보이는 곳에 두는 게 좋아요. TripBee Cute 책자에는 출발 디데이와 여행지 날씨, 현지 시간이 함께 있고, Apple Watch에서도 디데이와 다음 일정을 확인할 수 있어요.",
                "계정 가입, 광고, 추적이 없어요. 책자는 기기에 저장되고, 동기화를 켰을 때만 내 개인 iCloud에 저장돼요. 다크 모드와 iPad, 50개 언어도 지원해요.",
            ], []),
        ],
        "steps_title": "5분 만에 첫 여행 책자 만들기",
        "steps": [
            "TripBee Cute를 열고 새 여행을 추가한 뒤 이름을 정해요.",
            "도시, 랜드마크, 계절, 여행 기분 일러스트 표지 중에서 하나를 골라요.",
            "항공편 카드를 넣으면 출발 디데이가 시작돼요.",
            "날마다 일정을 채우고, 하루마다 이름을 붙이고 스티커를 달고, 사진과 티켓은 일정 옆에 붙여요.",
            "친구와 함께 짜려면 iCloud로 초대하고, 보여 주기만 할 거라면 웹 책자로 메신저에 공유해요.",
        ],
        "cards": [
            ("tripbeecute", "캡처, 메일, 메모에 흩어진 여행 정보를 귀여운 일러스트 여행 책자 한 권으로 모아 줘요. 출발 디데이, 항공편, 날짜별로 색이 다른 하루 일정, 준비물 리스트까지 한 페이지에서 끝나요. 사진, 티켓, 메모는 해당 일정 바로 옆에 보관하고, iCloud로 친구를 초대해 같은 책자를 함께 편집할 수 있어요. 웹 책자로 공유하면 어떤 브라우저에서도 열리고 오프라인에서도 볼 수 있어요. 홈 화면·잠금 화면 위젯, Apple Watch, iPad, 다크 모드, 50개 언어를 지원하고, 계정 가입, 광고, 추적이 없어요."),
        ],
        "faqs": [
            ("친구와 같은 일정을 함께 짤 수 있나요?", "네. iCloud로 친구를 초대해 같은 책자를 함께 편집하고, 변경 사항은 서로의 기기에 동기화돼요. 친구도 TripBee Cute가 필요해요."),
            ("친구가 앱이 없어도 일정을 볼 수 있나요?", "웹 책자로 공유하면 돼요. 웹 파일 하나로 어떤 브라우저나 메신저에서도 열리고, 오프라인에서도 볼 수 있고 디데이도 계속 줄어들어요."),
            ("스프레드시트로 짠 일정을 옮길 수 있나요?", "네. CSV 템플릿을 내보내 직접 채우거나 평소 쓰는 AI 어시스턴트에게 채워 달라고 한 뒤, 가져오기만 하면 책자가 완성돼요."),
            ("계정 가입이 필요한가요?", "아니요. 계정 가입, 광고, 추적이 없어요. 책자는 기기에 저장되고, 동기화를 켰을 때만 내 개인 iCloud에 저장돼요."),
        ],
        "related": [("ko/tripbeecute.html", "TripBee Cute 자세히 보기")],
        "legal": "이 페이지에서 소개하는 앱은 독립 개발 앱이에요. 날씨는 Open-Meteo에서 여행지 정보만 사용해 가져와요. App Store 검색 결과는 2026년 11월 실제 검색 기준이며 순위는 바뀔 수 있어요.",
    },
    # 香港：「旅行手帳」「旅行 手帳」（#72）；香港 App Store 前十多是一般手帳、記帳分帳與旅遊攻略類，
    # 用香港店直連（spec "cc"＝hk，gen_search_reality_g3.EXTRA_STOREFRONTS），寫給「去旅行前想把行程整理成一本」的香港讀者。
    {
        "key": "tripbeecute", "lang": "zh-Hant", "cc": "hk",
        "slug": "lvxing-shouzhang-qu-lvxing-xingcheng-guihua-hk",
        "terms": ["旅行手帳", "旅行 手帳", "旅遊 行程", "去旅行"],
        "title": "旅行手帳 App 點揀？去旅行前把行程、航班和行李清單整理成一本插畫手冊",
        "desc": "去旅行前，行程散落在截圖、訂位電郵和 WhatsApp 群組？整理香港人揀旅行手帳 App 的重點：短途周末遊、長途自由行、和朋友夾行程各自怎樣做，附 TripBee Cute 的使用步驟與香港 App Store 直連。",
        "h1": "旅行手帳：去旅行前，把航班、每日行程和行李清單收進同一本可愛手冊",
        "lead": "在香港 App Store 搜「旅行手帳」的人，通常機票已經買好，正準備去旅行；可是行程還散落在截圖、訂位電郵和群組對話裡，一到機場就要逐個翻。",
        "intro": [
            "我們在 2026 年 11 月實際查了香港 App Store：打「旅行手帳」或「旅行 手帳」，排在前十的多是一般的電子手帳、日記和記帳分帳 App，旅遊類的則多主打攻略或收據記帳。真正把航班、出發倒數、每日行程和行李清單放進同一本手冊的旅行專用 App 不多，所以很多人最後仍是用備忘錄加截圖拼湊。",
            "香港人去旅行有個特點：假期短、說走就走，日本、韓國、台灣這類短途行程經常只有三四天，一個周末加一兩天假就出發。時間愈緊，愈需要一本打開就看到「下一步去哪裡」的行程手冊，而不是一份要放大縮小才看得清的試算表。",
        ],
        "sections": [
            ("揀旅行手帳 App 之前，先問自己三個問題", [], [
                "行程會不會經常改？如果要調整順序、臨時插入空檔時間，選每個行程都能拖動排序、完成可打勾的手冊，比重新抄一頁快得多。",
                "會不會和朋友一起夾行程？TripBee Cute 可以用 iCloud 邀請朋友共同編輯同一本手冊，變更會同步到彼此的裝置（對方也需要安裝 App）；只想給家人看，就分享成網頁手冊，用任何瀏覽器或聊天 App 都打得開，離線也能看。",
                "到埗之後要不要導航？每個行程都能附上照片、票券和備註，還可以直接用地圖 App 導航，不用另外抄地址。",
            ]),
            ("短途周末遊、長途自由行、一家大細出發：各自怎樣排", [
                "三日兩夜的短途遊：先替旅行起個名字，從城市、地標、季節和旅行心情的插畫封面揀一張，再加上登機證風格的航班卡（時間、客運大樓、訂位代號）。出發倒數會一日一日往下數，主畫面和鎖定畫面小工具會用封面插畫顯示下一趟旅行，Apple Watch 上也看得到倒數和下一個行程。",
                "長途自由行：每一天各有顏色，可以按日期篩選，只看今日或看全程；兩個景點之間留空檔時間，天氣不好就切換成由主計畫複製出來的雨天備案。習慣先在試算表排好的人，可以匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就自動變成一本手冊。",
                "一家大細出遊：行李清單可以按同行者、季節和天數產生，出發前逐項打勾；旅行筆記和貼心提醒放在最後，例如轉插頭、八達通以外的當地交通卡、藥物，翻到手冊尾就看到。",
            ], []),
            ("用了一段時間之後，最常被問的事", [
                "舊行程怎樣保存？手冊可以備份匯出和匯入，可整本取代，也可以選擇合併，只加入新內容、不刪除任何東西；自己多部裝置之間也能用 iCloud 同步。",
                "不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟同步時才會存到你自己的私人 iCloud。支援深色模式、iPad 和 50 種語言，可跟隨系統語言，也能在 App 內切換。",
            ], []),
        ],
        "steps_title": "出發前一晚，十分鐘整理好一本手冊",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行，替它起個名字。",
            "揀一張插畫封面，再加上航班卡，倒數隨即開始。",
            "逐日填入行程，替每一天命名，把照片、票券和備註放在對應行程旁邊。",
            "用行李清單逐項執好行李，雨天備案和空檔時間也一併排好。",
            "邀請朋友用 iCloud 一起編輯，或分享成網頁手冊傳到群組。",
        ],
        "cards": [
            ("tripbeecute", "每趟旅行都是書架上的一本小手冊，有自己的插畫封面：翻開後一路往下滑，就是出發倒數、航班、逐日分色的行程，最後是行李清單和筆記。每個行程可以附照片、票券和備註，也能用地圖 App 導航；遇上落雨就切換雨天備案。和朋友用 iCloud 一起編輯同一本，或分享成任何瀏覽器都打得開、離線也能看的網頁手冊。主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式、50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("行程臨時要改，會不會很麻煩？", "不會。每日行程可以調整順序、完成打勾，也可以加入空檔時間；下雨時切換成由主計畫複製的雨天備案即可。"),
            ("朋友在群組問行程，可以直接傳給他們嗎？", "可以分享成網頁手冊：一個網頁檔，任何瀏覽器或聊天 App 都能打開，離線也能看，倒數也會持續跑。"),
            ("之前用 TripBee 或 TripBee Lite 排的行程可以打開嗎？", "可以。TripBee Cute 能打開 TripBee 和 TripBee Lite 的行程檔，也能分享含照片與票券的行程檔。"),
            ("手錶上看得到嗎？", "可以。Apple Watch App 會顯示出發倒數和下一個行程。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁介紹的 App 為獨立開發；天氣資料來自 Open-Meteo，只會用到目的地。App Store 搜尋結果為 2026 年 11 月香港 App Store 實際查詢，名次會變動。",
    },
    # 台灣：「旅遊手帳」（#21）＋「旅行 清單」（#85）。2026-11-08 查台灣 App Store 前十：「旅遊手帳」多是旅遊記帳、
    # 分帳與一般手帳（晴之旅、旅收、Tabii、旅帳…），「旅行 清單」多是行李打包清單（派客、PackPoint、Luggy、出門簽…）。
    # 寫給「出發前要打包、想把清單和每日行程放在同一本」的人；情境與既有台灣頁（出國倒數）、香港頁（短途周末遊）不同。
    {
        "key": "tripbeecute", "lang": "zh-Hant",
        "slug": "lvyou-shouzhang-lvxing-qingdan-dabao-xingli-zhhant",
        "terms": ["旅遊手帳", "旅行 清單", "行李清單", "打包清單"],
        "title": "旅遊手帳＋旅行清單：出發前的打包清單、每日行程和行李清單排在同一本",
        "desc": "旅行清單在一個 App、行程在另一個、截圖又在相簿？整理出發前一週怎麼用一本旅遊手帳同時管打包清單和每日行程：一個人、和旅伴一起、帶家人各自怎麼排，附 TripBee Cute 步驟與台灣 App Store 直連。",
        "h1": "旅遊手帳裡的旅行清單：行李清單和每日行程並排，出發前一週一本搞定",
        "lead": "在 App Store 搜「旅遊手帳」或「旅行 清單」的人，多半已經在倒數出發：行李要打包、行程要確認，可是清單在一個 App、行程在另一個，訂位資料又躺在相簿裡。",
        "intro": [
            "我們在 2026 年 11 月實際查了台灣 App Store：打「旅遊手帳」，前十名多是旅遊記帳、分帳和一般電子手帳；打「旅行 清單」，前十名則多是專門的行李打包清單。換句話說，想要一本「打開就看到每天去哪裡、也看得到還有什麼沒帶」的旅行手帳，常常得同時開兩三個 App。先說清楚：TripBee Cute 不是記帳或分帳工具，它做的是把行程和清單收進同一本手冊。",
            "打包清單和行程其實是連在一起的：第三天要去溫泉，就要記得帶換洗衣物；最後一天要搭早班機，前一晚就得先把行李收好。把兩者放在同一本手冊裡，從上往下滑一次，就能同時確認「去哪裡」和「帶什麼」。",
        ],
        "sections": [
            ("出發前一週，旅行清單這樣排", [], [
                "第 7 天前：建立這趟旅行、挑一張插畫封面，加上登機證風格的航班卡（時間、航廈、訂位代號），出發倒數開始跑。",
                "第 5 天前：把每天的行程填進去，替每天命名、各有顏色；看著行程列行李清單，哪天要爬山、哪天要正式晚餐，一目了然。",
                "第 3 天前：智慧行李清單可依同行者、季節與天數產生一份基本清單，再自己增減。",
                "前一晚：照清單逐項打勾，訂位與票券照片放在對應行程旁，旅行筆記與貼心提醒放在手冊最後。",
                "出發當天：主畫面與鎖定畫面小工具、Apple Watch 上看得到倒數和下一個行程，不用一直打開 App。",
            ]),
            ("一個人、和旅伴、帶家人：清單各自怎麼用", [
                "一個人出國：清單和行程在同一頁往下滑就看完，依日期篩選只看今天；兩個景點之間可以留空檔時間，臨時想休息也不會打亂整天。",
                "和旅伴一起：用 iCloud 邀請朋友共同編輯同一本手冊，誰查到新景點、誰想到要帶什麼，都直接加進去，變更會同步到彼此的裝置（對方也需要安裝 TripBee Cute）；只想讓大家看，就分享成網頁手冊傳到聊天群組，任何瀏覽器都能打開、離線也能看。",
                "帶家人出遊：行李清單依同行者與天數產生，長輩和小孩要帶的東西不容易漏；遇到下雨，切換成從主計畫複製出來的雨天備案。原本用試算表列好清單與行程的人，可以匯出 CSV 範本填好再匯入，自動變成一本手冊。",
            ], []),
            ("跟單純的打包清單 App 差在哪", [
                "打包清單 App 很適合只管行李；如果你還想要每日行程、航班、出發倒數、目的地天氣與當地時間，又希望翻起來像一本可愛的手帳，把它們放在同一本會更省事。每個行程都能附上照片、票券和備註，也能直接用地圖 App 導航。",
                "不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟同步時才會存到你自己的私人 iCloud。支援深色模式、iPad 與 50 種語言。",
            ], []),
        ],
        "steps_title": "把旅行清單和行程放進同一本的 5 個步驟",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行並挑一張插畫封面。",
            "加上航班卡，出發倒數開始跑。",
            "逐日填行程，替每天命名、貼上貼紙，照片和票券放在行程旁。",
            "在手冊最後建立行李清單，出發前逐項打勾。",
            "邀旅伴用 iCloud 一起編輯，或分享成網頁手冊傳到群組。",
        ],
        "cards": [
            ("tripbeecute", "一本可愛的插畫旅遊手帳，從封面一路往下滑：出發倒數、航班、每天分色的行程，最後是行李清單和旅行筆記。行李清單可以逐項打勾，也能依同行者、季節與天數產生；每個行程附照片、票券和備註，遇雨切換雨天備案。用 iCloud 邀旅伴一起編輯同一本，或分享成離線也能看的網頁手冊。主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式、50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("行李清單和行程可以放在同一個地方嗎？", "可以。每本手冊從封面往下依序是出發倒數、航班、每日行程，最後是行李清單和筆記，滑一次就能看完。"),
            ("可以和旅伴一起編輯清單嗎？", "可以。透過 iCloud 邀請朋友共同編輯同一本手冊，變更會同步到彼此的裝置；對方也需要安裝 TripBee Cute。"),
            ("可以拿來記帳或分帳嗎？", "TripBee Cute 是行程與清單手冊，不是記帳或分帳工具；花費可以寫在行程備註或旅行筆記裡。"),
            ("原本在試算表列好的行程能搬進來嗎？", "可以。匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就會自動變成一本手冊。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁介紹的 App 為獨立開發；天氣資料來自 Open-Meteo，只會用到目的地。App Store 搜尋結果為 2026 年 11 月台灣 App Store 實際查詢，名次會變動。",
    },
    # 澳門：2026-11-09 查澳門 App Store（iTunes 搜尋 country=mo）：「旅行 手帳」本款 #13、「旅行手帳」#15，
    # 「旅行 手賬」「旅行手賬」「行程 規劃」「旅遊 行程」前 25 名沒有本款。前十標題多寫「手帳」（微手帳、手帳罐頭、
    # Cute手帳軟件、喵咪手帳），也有「手賬」與簡體「手帐」；以「手帳」為主詞。前十多是一般手帳、記帳與攻略類。
    # 用澳門店直連（spec "cc"＝mo，EXTRA_STOREFRONTS），情境寫澳門出發：澳門機場或經港珠澳大橋轉香港機場、
    # 日韓台短途、和家人同行、長假出行；與香港頁（短途周末遊）、台灣兩頁（出國倒數、打包清單）不同。
    {
        "key": "tripbeecute", "lang": "zh-Hant", "cc": "mo",
        "slug": "lvxing-shouzhang-aomen-chufa-jiaren-tongxing-mo",
        "terms": ["旅行手帳", "旅行 手帳", "旅行 手賬", "家庭旅行"],
        "title": "旅行手帳 App：從澳門出發，和家人去日本、韓國、台灣的行程排成一本插畫手冊",
        "desc": "從澳門機場直飛，或經港珠澳大橋到香港機場轉機？整理澳門人出發前怎樣用一本旅行手帳管好航班、每日行程、家人的行李清單，長假出行也不亂，附 TripBee Cute 使用步驟與澳門 App Store 直連。",
        "h1": "旅行手帳：從澳門出發，一家人的航班、每日行程和行李清單收進同一本",
        "lead": "在澳門 App Store 搜「旅行手帳」或「旅行 手賬」的人，很多是準備帶家人出發：有人訂機票、有人查景點、有人負責執行李，資料分散在幾個人的手機裡，出發前總要在群組裡反覆問。",
        "intro": [
            "我們在 2026 年 11 月實際查了澳門 App Store：打「旅行手帳」或「旅行 手帳」，排在前十的多是一般電子手帳、日記和記帳 App，也有旅遊攻略類；標題多寫「手帳」，也有人寫「手賬」。把航班、出發倒數、每日行程和行李清單放進同一本手冊的旅行專用 App 不多，所以不少家庭仍是靠備忘錄、截圖和群組訊息拼湊行程。",
            "澳門人去旅行，出發路線本身就要先安排：可以由澳門國際機場直飛，也可以經港珠澳大橋去香港機場轉機。日本、韓國、台灣這類短途目的地最受歡迎，常常是一家人、甚至三代同行，趁長假一起出發。人一多，誰坐哪班機、哪天去哪裡、要帶甚麼，最好都寫在同一本，大家打開就看到同一份。",
        ],
        "sections": [
            ("從澳門出發，先把「去機場」這一段排好", [
                "航班卡用登機證風格顯示時間、客運大樓和訂位代號；若經港珠澳大橋去香港機場，可以把過關時間、集合地點寫成第一天最早的一個行程，再留一段空檔時間作緩衝，大家都知道幾點要出門。",
                "出發倒數會一日一日往下數，主畫面和鎖定畫面小工具會用封面插畫顯示下一趟旅行；目的地天氣與當地時間也一起顯示，去日本、韓國要調時差的時候一眼就看到。",
            ], []),
            ("一家人同行：誰負責甚麼，都在同一本", [], [
                "負責排行程的人：每一天各有顏色、可以替每天命名，按日期篩選只看今日；行程能調整順序、完成打勾，遇上落雨就切換成由主計畫複製出來的雨天備案，長輩和小朋友都不用在雨中乾等。",
                "負責執行李的人：行李清單可以按同行者、季節和天數產生，逐項打勾；長輩的藥物、小朋友的換洗衣物、轉插頭和當地交通卡，寫進旅行筆記和貼心提醒，翻到手冊尾就看到。",
                "想一起改行程的家人：用 iCloud 邀請對方共同編輯同一本手冊，變更會同步到彼此的裝置（對方也需要安裝 TripBee Cute）；只想讓長輩看，就分享成網頁手冊傳到家庭群組，任何瀏覽器或聊天 App 都打得開，離線也能看。",
            ]),
            ("長假出行之後，手冊可以留着下次再用", [
                "每趟旅行都是書架上的一本小手冊，有自己的插畫封面；每個行程都能附上照片、票券和備註，也能直接用地圖 App 導航。手冊可以備份匯出和匯入，可整本取代，或選擇合併，只加入新內容、不刪除任何東西，下次同一個目的地可以拿來參考。",
                "習慣先在試算表排好行程的人，可以匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就自動變成一本手冊。不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟同步時才會存到你自己的私人 iCloud。支援深色模式、iPad 和 50 種語言。",
            ], []),
        ],
        "steps_title": "出發前一個星期，一家人分工整理好一本手冊",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行，替它起個名字，揀一張插畫封面。",
            "加上航班卡，把去機場或過大橋的集合時間寫成第一個行程，倒數隨即開始。",
            "逐日填入行程，替每一天命名，把照片、票券和備註放在對應行程旁邊。",
            "按同行者建立行李清單，長輩和小朋友要帶的東西逐項打勾。",
            "用 iCloud 邀請家人一起編輯，或分享成網頁手冊傳到家庭群組。",
        ],
        "cards": [
            ("tripbeecute", "每趟旅行都是一本有插畫封面的小手冊：翻開後一路往下滑，就是出發倒數、登機證風格的航班卡、逐日分色的行程，最後是行李清單和旅行筆記。目的地天氣與當地時間一起顯示；每個行程可以附照片、票券和備註，也能用地圖 App 導航，落雨就切換雨天備案。和家人用 iCloud 一起編輯同一本，或分享成離線也能看的網頁手冊。主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式、50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("經港珠澳大橋去香港機場，這段可以寫進去嗎？", "可以。把集合地點和過關時間寫成第一天的行程，前後留空檔時間作緩衝；航班卡另外記下時間、客運大樓和訂位代號。"),
            ("屋企長輩不太會用新 App，可以給他們看行程嗎？", "可以分享成網頁手冊：一個網頁檔，任何瀏覽器或聊天 App 都能打開，離線也能看，倒數也會持續跑。"),
            ("去日本、韓國要調時差，看得到當地時間嗎？", "可以。手冊會顯示目的地天氣與當地時間；天氣資料來自 Open-Meteo，只會用到目的地。"),
            ("手錶上看得到下一個行程嗎？", "可以。Apple Watch App 會顯示出發倒數和下一個行程。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁介紹的 App 為獨立開發；天氣資料來自 Open-Meteo，只會用到目的地。App Store 搜尋結果為 2026 年 11 月澳門 App Store 實際查詢，名次會變動。",
    },
    # 日本：2026-11-10 查日本 App Store（iTunes 搜尋 country=jp）：「旅行 手帳」本款 #17（170 款）、「旅行手帳」#35，
    # 第 1 名評分僅 2 則；日本沒有本款意圖頁（姊妹款 TripBee Lite 的日文頁打「旅のしおり」，本頁改打「手帳」族群，不搶同詞）。
    # 功能句只取日文商店文案中購買前就能用的部分（不寫共同編集、スマート持ち物リスト、iCloud 同期、表紙總數）。
    {
        "key": "tripbeecute", "lang": "ja",
        "slug": "ryoko-techo-app-kawaii-ensei-joshitabi",
        "terms": ["旅行 手帳", "旅行手帳", "かわいい 旅行 手帳", "旅行 カウントダウン"],
        "title": "旅行手帳アプリの選び方｜女子旅・ライブ遠征の予定をかわいいイラストの1冊にまとめる5つのポイント",
        "desc": "紙の旅行手帳は好きだけど、予約メールやスクショを書き写すのが大変…という人へ。旅行手帳アプリを選ぶときのポイントと、出発までのカウントダウン、フライト、毎日の予定、持ち物を1ページにまとめる手順、日本のApp Storeへの直リンクをまとめました。",
        "h1": "旅行手帳をアプリで：カウントダウン、フライト、毎日の予定、持ち物をかわいい1冊に",
        "lead": "App Storeで「旅行 手帳」と検索する人の多くは、もう次の旅の予定が決まっています。航空券は予約メール、ホテルは予約サイト、行きたいお店はスクショ。情報がばらばらで、手帳に書き写す前に疲れてしまうことも。",
        "intro": [
            "マスキングテープやシールで飾る紙の旅行手帳はかわいいけれど、フライトの時間を書き写したり、予定が変わるたびに書き直したりするのは意外と手間がかかります。かといってカレンダーアプリだと表のようで、開いてもわくわくしません。ほしいのはその間、スマホのようにさっと作れて、手帳のようにめくって楽しい1冊です。",
            "2026年11月に日本のApp Storeで「旅行 手帳」を実際に検索してみると、上位には一般的な手帳アプリや日記アプリ、旅の記録アプリが並び、フライト、カウントダウン、毎日の予定、持ち物を旅ごとに1冊にまとめる旅行専用のアプリは多くありませんでした。選ぶときに見ておきたいポイントと、実際の作り方をまとめます。",
        ],
        "sections": [
            ("旅行手帳アプリは、この5つをチェック", [], [
                "旅の全体が1ページで見渡せるか：イラストの表紙を開いて下へスクロールするだけで、出発までのカウントダウン、フライト、毎日の予定、持ち物リストとメモまで続きます。アプリを行ったり来たりしなくていいのが一番の違いです。",
                "手帳らしく飾れるか：街や名所、季節のイラスト表紙を選び、日ごとの予定に名前をつけてステッカーを付けられます。",
                "日ごとに見分けられるか：日ごとに色が分かれて一目でわかり、日付で絞り込めばその日の予定だけを表示できます。",
                "記録を予定のそばに置けるか：写真やチケット、メモをその予定のすぐそばに保存でき、マップアプリで道順も確認できます。",
                "スマホを開かなくても見られるか：ホーム画面・ロック画面ウィジェットに表紙と次の予定、Apple Watchにカウントダウンと次の予定が表示されます。",
            ]),
            ("女子旅、ライブ遠征、はじめての海外旅行に", [
                "女子旅や韓国・台湾への週末旅行なら、旅に名前をつけて表紙を選び、時刻・ターミナル・予約番号が入った搭乗券風のフライトカードを入れるだけで、出発までのカウントダウンが始まります。行き先の天気と現地時刻も一緒に表示されるので、時差のある旅でも迷いません。",
                "ライブ遠征なら、会場入りの時間や物販、移動の予定を日ごとに並べ、終わったものから完了チェック。すき間時間も予定として入れておけます。雨が降ったら、メインの予定からコピーして作っておいた雨の日プランに切り替えられます。",
                "同行する友だちや家族に予定を見せたいときは、Webしおりで共有できます。1つのWebファイルなのでどのブラウザやチャットアプリでも開けて、オフラインでも見られ、カウントダウンも進み続けます。",
            ], []),
            ("紙の手帳派にもうれしいところ", [
                "表計算で予定を立てる派なら、CSVテンプレートを書き出して自分で記入するか、ふだん使っているAIアシスタントに記入してもらい、読み込めばしおりが1冊できあがります。書き写す手間がいらないので、飾ることに時間を使えます。",
                "アカウント登録なし、広告なし、トラッキングなし。しおりは端末に保存されます。天気はOpen-Meteoから行き先の情報だけを使って取得します。ダークモード、iPad、50言語にも対応しています。",
            ], []),
        ],
        "steps_title": "5分でつくる、はじめての旅行手帳",
        "steps": [
            "TripBee Cuteを開いて新しい旅を追加し、名前をつけます。",
            "街や名所、季節のイラストから表紙を1枚選びます。",
            "フライトカードを入れると、出発までのカウントダウンが始まります。",
            "毎日の予定を入れて日ごとに名前とステッカーを付け、写真やチケットは予定のそばに添付します。",
            "持ち物リストを作って、出発前にひとつずつチェックします。",
        ],
        "cards": [
            ("tripbeecute", "スクショやメール、メモに散らばった旅の予定を、かわいいイラストのしおり1冊にまとめます。出発までのカウントダウン、行き先の天気と現地時刻、搭乗券風のフライトカード、日ごとに色分けされた毎日の予定、持ち物リストまで1ページで見渡せます。写真やチケット、メモは予定のすぐそばに保存でき、雨の日プランへの切り替えも。Webしおりで共有すれば、どのブラウザでもオフラインでも開けます。ホーム画面・ロック画面ウィジェット、Apple Watch、iPad、ダークモード、50言語に対応。アカウント登録なし、広告なし、トラッキングなし。"),
        ],
        "faqs": [
            ("アプリを持っていない友だちにも予定を見せられますか？", "Webしおりで共有できます。1つのWebファイルでどのブラウザやチャットアプリでも開けて、オフラインでも見られ、カウントダウンも進み続けます。"),
            ("海外旅行で現地の時間や天気はわかりますか？", "行き先の天気と現地時刻がしおりに表示されます。天気はOpen-Meteoから行き先の情報だけを使って取得します。"),
            ("表計算で作った予定を移せますか？", "CSVテンプレートを書き出して記入し、読み込めばしおりができあがります。AIアシスタントに記入してもらうこともできます。"),
            ("アカウント登録は必要ですか？", "いいえ。アカウント登録なし、広告なし、トラッキングなしで、しおりは端末に保存されます。"),
        ],
        "related": [("ja/tripbeecute.html", "TripBee Cute の詳しい紹介")],
        "legal": "このページで紹介しているアプリは個人開発です。天気はOpen-Meteoから行き先の情報だけを使って取得します。App Storeの検索結果は2026年11月の日本のApp Storeでの実際の検索に基づくもので、順位は変わることがあります。",
    },
    # 澳洲：2026-11-10 查澳洲 App Store：「cute travel journal」本款 #4（162 款），鄰國紐西蘭 #3、愛爾蘭 #3、加拿大 #6、
    # 英國 #14；第 1 名 Journi 1,772 則評分。美國不在前 40，所以不用 en（美國店）頁，改用 en-AU 語系目錄連澳洲店。
    # 用澳洲英文（holiday、colour、mates）；功能句只取 en-AU 商店文案中購買前就能用的部分。
    {
        "key": "tripbeecute", "lang": "en-AU",
        "slug": "cute-travel-journal-app-holiday-countdown-en-au",
        "terms": ["cute travel journal", "travel journal", "holiday countdown", "cute trip planner"],
        "title": "Cute Travel Journal App: 5 Things to Check Before Your Next Holiday (Countdown, Flights, Day Plans, Packing)",
        "desc": "Looking for a cute travel journal on your iPhone? What to check before you pick one, how to turn booking emails and screenshots into one illustrated booklet with a holiday countdown, flights, day plans and a packing list, plus a direct Australian App Store link.",
        "h1": "Cute travel journal: your holiday countdown, flights, day plans and packing list in one illustrated booklet",
        "lead": "Most people who search the App Store for a cute travel journal already have a trip booked. The flights are in one email, the accommodation is in another, the cafe you want to try is a screenshot, and the group chat has the rest.",
        "intro": [
            "A paper travel journal with washi tape and stickers looks lovely, but copying flight times into it and rewriting a page every time the plan changes takes a lot of evenings. A calendar app is quicker, yet it looks like a spreadsheet and does nothing for the excitement of the trip. What most people want sits in the middle: something as quick as a phone and as nice to flip through as a journal.",
            "We searched the Australian App Store for cute travel journal in November 2026. The top results were mostly general journals, diaries and trip trackers that log where you have been. Very few put the flights, the countdown, each day's plans and the packing list for one trip together in one place. Below is what to look for, and how to build your first booklet in a few minutes.",
        ],
        "sections": [
            ("Five things to check in a cute travel journal app", [], [
                "The whole trip on one page: open the illustrated cover and scroll down through the countdown to departure, your flights, each day's plans, then the packing list and notes. No jumping between apps.",
                "Room to decorate: pick an illustrated cover of a city, landmark or season, give each day a name and add stickers to your plans.",
                "Days you can tell apart: each day has its own colour, and a date filter shows a single day when you only need today.",
                "Keepsakes next to the plan: keep photos, tickets and notes right beside each plan, and get directions in your maps app.",
                "A glance without opening it: Home Screen and Lock Screen widgets show your cover art and next plan, and the Apple Watch app shows the countdown and your next plan.",
            ]),
            ("Three common holidays, three ways to use it", [
                "A long weekend away or a road trip up the coast: name the trip, choose a cover and add your plans for each day, with gaps for downtime. If the weather turns, switch to the rainy-day plan you made as a copy of the main plan.",
                "A week in Bali or a first big trip overseas: add a flight card styled like a boarding pass, with times, terminals and booking references, and the countdown starts. The weather and local time at your destination sit right there too, which helps when the time zone changes.",
                "A family holiday or a trip with your mates: share a web booklet. It is a single web file that opens in any browser or chat app, works offline, and its countdown keeps running, so everyone can see the plan without installing anything.",
            ], []),
            ("Handy for planners who like a spreadsheet", [
                "Already have the plan in a spreadsheet? Export the CSV template, fill it in yourself or ask any AI assistant you like to do it, then import the file and the booklet appears. Less copying means more time for the fun part.",
                "No account, no ads and no tracking. Your booklet stays on your device, and the weather comes from Open-Meteo using only your destination. Dark Mode, iPad and 50 languages are supported.",
            ], []),
        ],
        "steps_title": "Make your first travel booklet in five minutes",
        "steps": [
            "Open TripBee Cute, add a new trip and give it a name.",
            "Choose an illustrated cover of a city, landmark or season.",
            "Add a flight card and the countdown to departure begins.",
            "Fill in each day, name the days, add stickers, and attach photos and tickets next to the plans.",
            "Build your packing list and tick things off before you leave.",
        ],
        "cards": [
            ("tripbeecute", "Turns booking emails, screenshots and group chats into one cute illustrated booklet: the countdown to departure, the weather and local time at your destination, flight cards styled like boarding passes, colour-coded day plans and your packing list, all on one page. Keep photos, tickets and notes beside each plan, switch to a rainy-day plan when the weather turns, and share a web booklet that opens in any browser, even offline. Home Screen and Lock Screen widgets, Apple Watch, iPad, Dark Mode and 50 languages. No account, no ads and no tracking."),
        ],
        "faqs": [
            ("Can friends see the plan without the app?", "Yes. Share a web booklet: a single web file that opens in any browser or chat app, works offline, and keeps the countdown running."),
            ("Does it show the time and weather where I am going?", "Yes. The booklet shows the weather and local time at your destination. Weather comes from Open-Meteo using only your destination."),
            ("Can I bring in a plan from a spreadsheet?", "Yes. Export the CSV template, fill it in or ask an AI assistant to, then import it and the booklet is made for you."),
            ("Do I need to sign up?", "No. There is no account, no ads and no tracking, and your booklet stays on your device."),
        ],
        "related": [("en-AU/tripbeecute.html", "TripBee Cute: full app overview")],
        "legal": "The app on this page is made by an independent developer. Weather comes from Open-Meteo using only your destination. App Store search results are from a real search of the Australian App Store in November 2026, and rankings change.",
    },
]


_G3_SITEMAP_NAME = g3.sitemap_name


def sitemap_name(lang: str) -> str:
    """指南站澳洲英文的 seasonal sitemap 檔名用底線（sitemap_seasonal_en_AU.xml，已列在 sitemap_index.xml）。"""
    return f"sitemap_{g3.SECTION}_en_AU.xml" if lang == "en-AU" else _G3_SITEMAP_NAME(lang)


def _install() -> None:
    """把本批的語系表、App、頁面與檢查換進第 3 組產生器（其餘版面與檢查原樣沿用）。"""
    g3.LANGS = LANGS
    g3.APP_IDS = APP_IDS
    g3.PAGE_SPECS = PAGE_SPECS
    g3.BANNED = BANNED
    g3.dedicated_size = dedicated_size
    g3.sitemap_name = sitemap_name


def main(argv=None) -> int:
    _install()
    return g3.main(argv)


if __name__ == "__main__":
    sys.exit(main())
