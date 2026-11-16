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
  （例外：pass_wording 頁照 reports/blitz/tripbeecute_materials.md「付費口徑」標 Cute Pass，台韓頁 FAQ 列不購買可用清單含分帳。）
- 每頁一張主卡，附該國 App Store 直連（台灣、韓國；香港頁 spec "cc"＝hk 連香港店；pt＋ct＋mt）；ct＝gw 階梯碼（gw_campaign.py，款 × 國家 × 詞群 sr）。
  Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 主卡的「完整介紹」連到 zh-Hant/tripbeecute.html：指南站逐語系頁產生前，g3 的內部連結檢查會擋，
  所以本檔與產出頁只在指南站收錄本款後才併入主線（判準見 reports/tripbeecute/action_cards.md）。
- 2026-11-08 加香港繁中頁：香港主詞「旅行手帳」「旅行 手帳」#72；語言目錄沿用 zh-Hant，spec "cc": "hk" 改連香港店。
- 2026-11-08 加台灣第二頁：「旅遊手帳」#21、「旅行 清單」#85；寫出發前打包清單與每日行程並排（預設台灣店，不需 cc）。
- 2026-11-10 加日文頁（「旅行 手帳」#17）與澳洲英文頁（「cute travel journal」#4，en-AU 目錄連澳洲店，sitemap 用既有 sitemap_seasonal_en_AU.xml）。
- 2026-11-15 加給 AI 助理讀的問答頁（英、繁中、日、韓四頁：是什麼、適合誰、怎麼收費、和同類差在哪），主卡放第一屏（cards_first）。
- 專屬內容：中文 ≥450 字、韓文 ≥450 個韓文字。只寫這兩頁與各語系 sitemap_seasonal_<lang>.xml 的這幾列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_tripbeecute.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_search_reality_tripbeecute.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import re
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
# 2026-11-11 商店文案修正（aso/write_packs/2026-11-11_tripbeecute_copy_fix/SPEC.md C 段）後，台灣主頁與韓文頁照實寫出
# 不購買能做什麼與 Cute Pass 清單；韓文 FAQ 題目需要「무료」，所以這兩頁只放行這個字，價格、Free、Pro 照擋。
PASS_BANNED = re.compile(BANNED.pattern.replace("무료|", ""), BANNED.flags)
dedicated_size = easyam.dedicated_size

PAGE_SPECS: list[dict] = [
    # 台灣：「可愛 旅行手帳」（主詞，首量 #5）、「旅行手帳」「出國 行程表」「出國倒數」
    {
        "key": "tripbeecute", "lang": "zh-Hant",
        "slug": "keai-lvxing-shouzhang-chuguo-xingchengbiao-daoshu-zhhant",
        "banned": PASS_BANNED, "pass_wording": True,
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
                "能和旅伴一起排：用 iCloud 邀請朋友共同編輯同一本手冊（Cute Pass），變更會同步到彼此的裝置（對方也需要安裝 App）。",
                "分享出去對方打得開：分享成網頁手冊，任何瀏覽器或聊天 App 都能打開，離線也能看。",
            ]),
            ("想要一份可愛的行程表？", [
                "搜「可愛 行程」的人，常常是想把行程表排得好看一點，打開就有出發的心情。TripBee Cute 的每一天都有自己的顏色，逐日分色一眼就分得清楚，也能依日期篩選只看某一天；每趟旅行都有一張插畫封面，城市、地標、季節、旅行心情都有（內含 6 款，Cute Pass 再加 51 款，還能用自己的照片當封面），像書架上的一本小手冊。",
                "已經在試算表裡排好行程也沒關係：匯出 CSV 範本，填好後再匯入，就會自動變成一本可愛的行程手冊，不必一格一格重新輸入。",
            ], []),
            ("三種最常見的旅行，各自怎麼排", [
                "第一次出國自由行：先幫旅行取個名字、挑一張插畫封面，加上登機證風格的航班卡（時間、航廈、訂位代號），再把每一天填滿。出發倒數會一天天往下跳，主畫面與鎖定畫面小工具也看得到下一趟旅行。",
                "閨蜜旅行、畢業旅行：大家各自查好的景點，直接加進同一本手冊；每個行程都能貼上貼紙、完成就打勾、隨時調整順序。遇到下雨，切換成從主計畫複製的雨天備案就好。",
                "全家出遊、環島、蜜月：行李清單可以逐項打勾，用 Cute Pass 的智慧行李清單還能依同行者、季節與天數產生，旅行筆記與貼心提醒放在最後一頁；習慣用試算表排行程的人，可以匯出 CSV 範本填好再匯入，自動變成一本手冊。",
            ], []),
            ("跨年、寒假、春節出國怎麼排", [
                "跨年、寒假和春節是一年裡最多人出國的時候，機票往往兩三個月前就訂好了。先建一本手冊、加上航班卡，出發倒數就會開始一天天往下跳，主畫面與鎖定畫面小工具也看得到，等待的那幾週也充滿期待；航班卡放好時間、航廈和訂位代號，連假機場人多，打開就找得到。",
                "長假天數多，每一天都有自己的顏色，跨年夜、除夕、初一各自分得清楚，也能依日期篩選只看某一天。出發前用行李清單逐項打勾，厚外套、轉插頭和紅包袋都不容易漏；排好之後分享成網頁手冊傳到家族群組，爸媽用任何瀏覽器都能打開，離線也能看，倒數也會一直跑。",
            ], []),
            ("出國前一晚最常忘的事", [
                "航班時間與航廈、訂位代號、目的地天氣與當地時間，最好都放在打開就看得到的地方。TripBee Cute 的手冊裡有出發倒數、目的地天氣與當地時間，Apple Watch 上也看得到倒數和下一個行程。",
                "不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有在你開啟 iCloud 同步（Cute Pass）時，才會存到你自己的私人 iCloud。",
            ], []),
        ],
        "steps_title": "5 分鐘做出第一本旅行手冊",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行並取個名字。",
            "從插畫封面裡挑一張：城市、地標、季節、旅行心情都有。",
            "加上航班卡，出發倒數就會開始跑。",
            "把每一天的行程填進去，替每天命名、貼上貼紙，照片和票券放在行程旁。",
            "想和朋友一起排，用 iCloud 邀請對方共同編輯（Cute Pass）；或分享成網頁手冊傳到聊天群組。",
        ],
        "cards": [
            ("tripbeecute", "把整趟旅行收進一本可愛的插畫手冊：出國倒數、航班、每日行程和行李清單都在同一頁。每一天都有自己的顏色，照片、票券和備註就放在對應的行程旁邊；用 iCloud 邀請朋友一起編輯同一本手冊（Cute Pass），也能分享成任何瀏覽器都能打開、離線也能看的網頁手冊。支援主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式與 50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("下載前想知道：不購買能做什麼？", "不購買也能一次保存 1 本手冊，並使用 6 款封面、CSV 匯入、網頁手冊、航班、每日行程、分帳（和旅伴記花費、算清誰該付給誰）、行李清單、小工具和 Apple Watch App。其餘由一次性 App 內購買 Cute Pass 解鎖，不是訂閱：不限手冊數量、再多 51 款封面並可用自己的照片當封面、智慧行李清單、iCloud 同步與備份、分享含照片與票券的行程檔，以及和朋友一起規劃（iCloud 共同編輯）。"),
            ("可以和朋友一起排同一份行程嗎？", "可以，這是 Cute Pass 功能。透過 iCloud 邀請朋友共同編輯同一本手冊，變更會同步到彼此的裝置；對方也需要安裝 TripBee Cute。"),
            ("朋友沒有裝 App，看得到行程嗎？", "可以分享成網頁手冊：一個網頁檔，任何瀏覽器或聊天 App 都能打開，離線也能看，倒數也會持續跑。"),
            ("原本用試算表排好的行程可以搬進來嗎？", "可以。匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就會自動變成一本手冊。"),
            ("需要註冊帳號嗎？", "不用。不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟 iCloud 同步（Cute Pass）時才會存到你自己的私人 iCloud。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁介紹的 App 為獨立開發；天氣資料來自 Open-Meteo，只會用到目的地。",
    },
    # 韓國：「다꾸 여행」（主詞，#45、前 10 幾乎全 0 則評分）、「여행 다이어리」「여행 일정」「여행 디데이」
    {
        "key": "tripbeecute", "lang": "ko",
        "slug": "dakku-yeohaeng-diary-sticker-illust-pyoji",
        "banned": PASS_BANNED, "pass_wording": True,
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
                "꾸미는 재미: 도시, 랜드마크, 계절, 여행 기분을 담은 일러스트 표지를 고르고(기본 6종, Cute Pass로 51종 추가, 내 사진도 표지로 쓸 수 있어요), 하루 일정마다 이름을 붙이고 스티커를 달 수 있어요.",
                "날짜마다 다른 색: 날짜마다 색이 달라 한눈에 구분되고, 날짜 필터로 그날 일정만 볼 수 있어요.",
                "기록은 일정 바로 옆에: 사진, 티켓, 메모를 해당 일정 옆에 보관해서 현지에서 앨범을 뒤질 필요가 없어요.",
                "친구와 함께, 친구에게 보여 주기: iCloud로 친구를 초대해 같은 책자를 함께 편집하고(Cute Pass, 친구도 TripBee Cute 필요), 웹 책자로 공유하면 어떤 브라우저나 메신저에서도 열리고 오프라인에서도 볼 수 있어요.",
            ]),
            ("자주 있는 세 가지 여행, 이렇게 꾸며요", [
                "첫 해외여행, 일본이나 제주 주말 여행: 여행 이름을 정하고 표지를 고른 뒤, 시간, 터미널, 예약 번호가 담긴 탑승권 스타일 항공편 카드를 넣어요. 출발 디데이가 하루씩 줄어들고, 홈 화면과 잠금 화면 위젯에서도 다음 여행 표지를 볼 수 있어요.",
                "우정 여행, 커플 여행: 각자 찾아 둔 장소를 같은 책자에 바로 추가해요. 일정마다 스티커를 붙이고, 다녀온 곳은 완료 체크하고, 순서도 언제든 바꿀 수 있어요. 비가 오면 메인 일정에서 복사해 둔 우천 플랜으로 바꾸면 돼요.",
                "가족 여행, 신혼여행: 준비물 리스트에 하나씩 체크하며 짐을 챙기고(Cute Pass의 스마트 준비물 리스트는 동행, 계절, 여행 기간에 맞춰 만들어 줘요), 여행 메모와 다정한 알림은 마지막 페이지에 모아 둬요. 스프레드시트로 계획하는 편이라면 CSV 템플릿을 내보내 채운 뒤 가져오기만 하면 책자가 완성돼요.",
            ], []),
            ("출발 전날 자주 잊는 것", [
                "항공편 시간과 터미널, 예약 번호, 여행지 날씨와 현지 시간은 열자마자 보이는 곳에 두는 게 좋아요. TripBee Cute 책자에는 출발 디데이와 여행지 날씨, 현지 시간이 함께 있고, Apple Watch에서도 디데이와 다음 일정을 확인할 수 있어요.",
                "계정 가입, 광고, 추적이 없어요. 책자는 기기에 저장되고, iCloud 동기화(Cute Pass)를 켰을 때만 내 개인 iCloud에 저장돼요. 다크 모드와 iPad, 50개 언어도 지원해요.",
            ], []),
        ],
        "steps_title": "5분 만에 첫 여행 책자 만들기",
        "steps": [
            "TripBee Cute를 열고 새 여행을 추가한 뒤 이름을 정해요.",
            "도시, 랜드마크, 계절, 여행 기분 일러스트 표지 중에서 하나를 골라요.",
            "항공편 카드를 넣으면 출발 디데이가 시작돼요.",
            "날마다 일정을 채우고, 하루마다 이름을 붙이고 스티커를 달고, 사진과 티켓은 일정 옆에 붙여요.",
            "친구와 함께 짜려면 iCloud로 초대하고(Cute Pass), 보여 주기만 할 거라면 웹 책자로 메신저에 공유해요.",
        ],
        "cards": [
            ("tripbeecute", "캡처, 메일, 메모에 흩어진 여행 정보를 귀여운 일러스트 여행 책자 한 권으로 모아 줘요. 출발 디데이, 항공편, 날짜별로 색이 다른 하루 일정, 준비물 리스트까지 한 페이지에서 끝나요. 사진, 티켓, 메모는 해당 일정 바로 옆에 보관하고, iCloud로 친구를 초대해 같은 책자를 함께 편집할 수 있어요(Cute Pass). 웹 책자로 공유하면 어떤 브라우저에서도 열리고 오프라인에서도 볼 수 있어요. 홈 화면·잠금 화면 위젯, Apple Watch, iPad, 다크 모드, 50개 언어를 지원하고, 계정 가입, 광고, 추적이 없어요."),
        ],
        "faqs": [
            ("구매 전에: 무료로 무엇을 할 수 있나요?", "구매하지 않아도 책자 1권을 저장하고, 표지 6종, CSV 가져오기, 웹 책자, 항공편, 하루 일정, 여행 경비 정산(동행과 쓴 돈을 기록하고 누가 누구에게 얼마를 보낼지 계산), 준비물 리스트, 위젯, Apple Watch 앱을 쓸 수 있어요. 나머지는 한 번만 구매하는 앱 내 구입 Cute Pass로 열리고, 구독이 아니에요. 책자 수 제한 없음, 표지 51종 추가와 내 사진 표지, 스마트 준비물 리스트, iCloud 동기화와 백업, 사진과 티켓이 담긴 여행 파일 공유, 친구와 함께 계획하기(iCloud 공동 편집)가 들어 있어요."),
            ("여행 경비 정산이나 더치페이도 되나요?", "네, 구매하지 않아도 쓸 수 있어요. 일정마다 누가 냈는지 기록하고 똑같이 나누거나 금액을 직접 정할 수 있고, 정산 화면에서 누가 누구에게 얼마를 보내야 하는지 바로 보여요. 다른 통화는 실시간 환율로 바꿔서 계산해요."),
            ("친구와 같은 일정을 함께 짤 수 있나요?", "네. Cute Pass 기능이에요. iCloud로 친구를 초대해 같은 책자를 함께 편집하고, 변경 사항은 서로의 기기에 동기화돼요. 친구도 TripBee Cute가 필요해요."),
            ("친구가 앱이 없어도 일정을 볼 수 있나요?", "웹 책자로 공유하면 돼요. 웹 파일 하나로 어떤 브라우저나 메신저에서도 열리고, 오프라인에서도 볼 수 있고 디데이도 계속 줄어들어요."),
            ("스프레드시트로 짠 일정을 옮길 수 있나요?", "네. CSV 템플릿을 내보내 직접 채우거나 평소 쓰는 AI 어시스턴트에게 채워 달라고 한 뒤, 가져오기만 하면 책자가 완성돼요."),
            ("계정 가입이 필요한가요?", "아니요. 계정 가입, 광고, 추적이 없어요. 책자는 기기에 저장되고, iCloud 동기화(Cute Pass)를 켰을 때만 내 개인 iCloud에 저장돼요."),
        ],
        "related": [("ko/tripbeecute.html", "TripBee Cute 자세히 보기")],
        "legal": "이 페이지에서 소개하는 앱은 독립 개발 앱이에요. 날씨는 Open-Meteo에서 여행지 정보만 사용해 가져와요. App Store 검색 결과는 2026년 11월 실제 검색 기준이며 순위는 바뀔 수 있어요.",
    },
    # 香港：「旅行手帳」「旅行 手帳」（#72）；香港 App Store 前十多是一般手帳、記帳分帳與旅遊攻略類，
    # 用香港店直連（spec "cc"＝hk，gen_search_reality_g3.EXTRA_STOREFRONTS），寫給「去旅行前想把行程整理成一本」的香港讀者。
    {
        "key": "tripbeecute", "lang": "zh-Hant", "cc": "hk", "pass_wording": True,
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
                "會不會和朋友一起夾行程？TripBee Cute 可以用 iCloud 邀請朋友共同編輯同一本手冊（Cute Pass），變更會同步到彼此的裝置（對方也需要安裝 App）；只想給家人看，就分享成網頁手冊，用任何瀏覽器或聊天 App 都打得開，離線也能看。",
                "到埗之後要不要導航？每個行程都能附上照片、票券和備註，還可以直接用地圖 App 導航，不用另外抄地址。",
            ]),
            ("短途周末遊、長途自由行、一家大細出發：各自怎樣排", [
                "三日兩夜的短途遊：先替旅行起個名字，從城市、地標、季節和旅行心情的插畫封面揀一張（內含 6 款，Cute Pass 再加 51 款，還可以用自己的相片做封面），再加上登機證風格的航班卡（時間、客運大樓、訂位代號）。出發倒數會一日一日往下數，主畫面和鎖定畫面小工具會用封面插畫顯示下一趟旅行，Apple Watch 上也看得到倒數和下一個行程。",
                "長途自由行：每一天各有顏色，可以按日期篩選，只看今日或看全程；兩個景點之間留空檔時間，天氣不好就切換成由主計畫複製出來的雨天備案。習慣先在試算表排好的人，可以匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就自動變成一本手冊。",
                "一家大細出遊：行李清單可以逐項打勾，用 Cute Pass 的智慧行李清單還能按同行者、季節和天數產生；旅行筆記和貼心提醒放在最後，例如轉插頭、八達通以外的當地交通卡、藥物，翻到手冊尾就看到。",
            ], []),
            ("用了一段時間之後，最常被問的事", [
                "舊行程怎樣保存？手冊可以備份匯出和匯入，可整本取代，也可以選擇合併，只加入新內容、不刪除任何東西；自己多部裝置之間也能用 iCloud 同步（Cute Pass）。",
                "不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟 iCloud 同步（Cute Pass）時才會存到你自己的私人 iCloud。支援深色模式、iPad 和 50 種語言，可跟隨系統語言，也能在 App 內切換。",
            ], []),
        ],
        "steps_title": "出發前一晚，十分鐘整理好一本手冊",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行，替它起個名字。",
            "揀一張插畫封面，再加上航班卡，倒數隨即開始。",
            "逐日填入行程，替每一天命名，把照片、票券和備註放在對應行程旁邊。",
            "用行李清單逐項執好行李，雨天備案和空檔時間也一併排好。",
            "邀請朋友用 iCloud 一起編輯（Cute Pass），或分享成網頁手冊傳到群組。",
        ],
        "cards": [
            ("tripbeecute", "每趟旅行都是書架上的一本小手冊，有自己的插畫封面：翻開後一路往下滑，就是出發倒數、航班、逐日分色的行程，最後是行李清單和筆記。每個行程可以附照片、票券和備註，也能用地圖 App 導航；遇上落雨就切換雨天備案。和朋友用 iCloud 一起編輯同一本（Cute Pass），或分享成任何瀏覽器都打得開、離線也能看的網頁手冊。主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式、50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("行程臨時要改，會不會很麻煩？", "不會。每日行程可以調整順序、完成打勾，也可以加入空檔時間；下雨時切換成由主計畫複製的雨天備案即可。"),
            ("朋友在群組問行程，可以直接傳給他們嗎？", "可以分享成網頁手冊：一個網頁檔，任何瀏覽器或聊天 App 都能打開，離線也能看，倒數也會持續跑。"),
            ("之前用 TripBee 或 TripBee Lite 排的行程可以打開嗎？", "可以。TripBee Cute 能打開 TripBee 和 TripBee Lite 的行程檔，分享含照片與票券的行程檔則是 Cute Pass 功能。"),
            ("手錶上看得到嗎？", "可以。Apple Watch App 會顯示出發倒數和下一個行程。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁介紹的 App 為獨立開發；天氣資料來自 Open-Meteo，只會用到目的地。App Store 搜尋結果為 2026 年 11 月香港 App Store 實際查詢，名次會變動。",
    },
    # 台灣：「旅遊手帳」（#21）＋「旅行 清單」（#85）。2026-11-08 查台灣 App Store 前十：「旅遊手帳」多是旅遊記帳、
    # 分帳與一般手帳（晴之旅、旅收、Tabii、旅帳…），「旅行 清單」多是行李打包清單（派客、PackPoint、Luggy、出門簽…）。
    # 寫給「出發前要打包、想把清單和每日行程放在同一本」的人；情境與既有台灣頁（出國倒數）、香港頁（短途周末遊）不同。
    {
        "key": "tripbeecute", "lang": "zh-Hant", "pass_wording": True,
        "slug": "lvyou-shouzhang-lvxing-qingdan-dabao-xingli-zhhant",
        "terms": ["旅遊手帳", "旅行 清單", "行李清單", "打包清單"],
        "title": "旅遊手帳＋旅行清單：出發前的打包清單、每日行程和行李清單排在同一本",
        "desc": "旅行清單在一個 App、行程在另一個、截圖又在相簿？整理出發前一週怎麼用一本旅遊手帳同時管打包清單和每日行程：一個人、和旅伴一起、帶家人各自怎麼排，附 TripBee Cute 步驟與台灣 App Store 直連。",
        "h1": "旅遊手帳裡的旅行清單：行李清單和每日行程並排，出發前一週一本搞定",
        "lead": "在 App Store 搜「旅遊手帳」或「旅行 清單」的人，多半已經在倒數出發：行李要打包、行程要確認，可是清單在一個 App、行程在另一個，訂位資料又躺在相簿裡。",
        "intro": [
            "我們在 2026 年 11 月實際查了台灣 App Store：打「旅遊手帳」，前十名多是旅遊記帳、分帳和一般電子手帳；打「旅行 清單」，前十名則多是專門的行李打包清單。換句話說，想要一本「打開就看到每天去哪裡、也看得到還有什麼沒帶」的旅行手帳，常常得同時開兩三個 App。先說清楚：TripBee Cute 不是記帳 App，但和旅伴的花費可以直接在行程上分帳、算清誰該付給誰（分帳不購買就能用）；它主要做的是把行程和清單收進同一本手冊。",
            "打包清單和行程其實是連在一起的：第三天要去溫泉，就要記得帶換洗衣物；最後一天要搭早班機，前一晚就得先把行李收好。把兩者放在同一本手冊裡，從上往下滑一次，就能同時確認「去哪裡」和「帶什麼」。",
        ],
        "sections": [
            ("出發前一週，旅行清單這樣排", [], [
                "第 7 天前：建立這趟旅行、挑一張插畫封面（內含 6 款，Cute Pass 再加 51 款，還能用自己的照片當封面），加上登機證風格的航班卡（時間、航廈、訂位代號），出發倒數開始跑。",
                "第 5 天前：把每天的行程填進去，替每天命名、各有顏色；看著行程列行李清單，哪天要爬山、哪天要正式晚餐，一目了然。",
                "第 3 天前：Cute Pass 的智慧行李清單可依同行者、季節與天數產生一份基本清單，再自己增減。",
                "前一晚：照清單逐項打勾，訂位與票券照片放在對應行程旁，旅行筆記與貼心提醒放在手冊最後。",
                "出發當天：主畫面與鎖定畫面小工具、Apple Watch 上看得到倒數和下一個行程，不用一直打開 App。",
            ]),
            ("一個人、和旅伴、帶家人：清單各自怎麼用", [
                "一個人出國：清單和行程在同一頁往下滑就看完，依日期篩選只看今天；兩個景點之間可以留空檔時間，臨時想休息也不會打亂整天。",
                "和旅伴一起：用 iCloud 邀請朋友共同編輯同一本手冊（Cute Pass），誰查到新景點、誰想到要帶什麼，都直接加進去，變更會同步到彼此的裝置（對方也需要安裝 TripBee Cute）；只想讓大家看，就分享成網頁手冊傳到聊天群組，任何瀏覽器都能打開、離線也能看。",
                "帶家人出遊：行李清單逐項打勾，用 Cute Pass 的智慧行李清單還能依同行者與天數產生，長輩和小孩要帶的東西不容易漏；遇到下雨，切換成從主計畫複製出來的雨天備案。原本用試算表列好清單與行程的人，可以匯出 CSV 範本填好再匯入，自動變成一本手冊。",
            ], []),
            ("跟單純的打包清單 App 差在哪", [
                "打包清單 App 很適合只管行李；如果你還想要每日行程、航班、出發倒數、目的地天氣與當地時間，又希望翻起來像一本可愛的手帳，把它們放在同一本會更省事。每個行程都能附上照片、票券和備註，也能直接用地圖 App 導航。",
                "不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟 iCloud 同步（Cute Pass）時才會存到你自己的私人 iCloud。支援深色模式、iPad 與 50 種語言。",
            ], []),
        ],
        "steps_title": "把旅行清單和行程放進同一本的 5 個步驟",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行並挑一張插畫封面。",
            "加上航班卡，出發倒數開始跑。",
            "逐日填行程，替每天命名、貼上貼紙，照片和票券放在行程旁。",
            "在手冊最後建立行李清單，出發前逐項打勾。",
            "邀旅伴用 iCloud 一起編輯（Cute Pass），或分享成網頁手冊傳到群組。",
        ],
        "cards": [
            ("tripbeecute", "一本可愛的插畫旅遊手帳，從封面一路往下滑：出發倒數、航班、每天分色的行程，最後是行李清單和旅行筆記。行李清單可以逐項打勾，用 Cute Pass 的智慧行李清單還能依同行者、季節與天數產生；每個行程附照片、票券和備註，遇雨切換雨天備案。用 iCloud 邀旅伴一起編輯同一本（Cute Pass），或分享成離線也能看的網頁手冊。主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式、50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("行李清單和行程可以放在同一個地方嗎？", "可以。每本手冊從封面往下依序是出發倒數、航班、每日行程，最後是行李清單和筆記，滑一次就能看完。"),
            ("可以和旅伴一起編輯清單嗎？", "可以。這是 Cute Pass 功能。透過 iCloud 邀請朋友共同編輯同一本手冊，變更會同步到彼此的裝置；對方也需要安裝 TripBee Cute。"),
            ("可以拿來記帳或分帳嗎？", "TripBee Cute 不是記帳 App，但和旅伴的花費可以直接在行程上分帳、算清誰該付給誰，分帳不購買就能用。"),
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
        "key": "tripbeecute", "lang": "zh-Hant", "cc": "mo", "pass_wording": True,
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
                "負責執行李的人：行李清單可以逐項打勾，用 Cute Pass 的智慧行李清單還能按同行者、季節和天數產生；長輩的藥物、小朋友的換洗衣物、轉插頭和當地交通卡，寫進旅行筆記和貼心提醒，翻到手冊尾就看到。",
                "想一起改行程的家人：用 iCloud 邀請對方共同編輯同一本手冊（Cute Pass），變更會同步到彼此的裝置（對方也需要安裝 TripBee Cute）；只想讓長輩看，就分享成網頁手冊傳到家庭群組，任何瀏覽器或聊天 App 都打得開，離線也能看。",
            ]),
            ("長假出行之後，手冊可以留着下次再用", [
                "每趟旅行都是書架上的一本小手冊，有自己的插畫封面（內含 6 款，Cute Pass 再加 51 款，還可以用自己的相片做封面）；每個行程都能附上照片、票券和備註，也能直接用地圖 App 導航。手冊可以備份匯出和匯入，可整本取代，或選擇合併，只加入新內容、不刪除任何東西，下次同一個目的地可以拿來參考。",
                "習慣先在試算表排好行程的人，可以匯出 CSV 範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就自動變成一本手冊。不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，只有開啟 iCloud 同步（Cute Pass）時才會存到你自己的私人 iCloud。支援深色模式、iPad 和 50 種語言。",
            ], []),
        ],
        "steps_title": "出發前一個星期，一家人分工整理好一本手冊",
        "steps": [
            "打開 TripBee Cute，新增一趟旅行，替它起個名字，揀一張插畫封面。",
            "加上航班卡，把去機場或過大橋的集合時間寫成第一個行程，倒數隨即開始。",
            "逐日填入行程，替每一天命名，把照片、票券和備註放在對應行程旁邊。",
            "建立行李清單，長輩和小朋友要帶的東西逐項打勾。",
            "用 iCloud 邀請家人一起編輯（Cute Pass），或分享成網頁手冊傳到家庭群組。",
        ],
        "cards": [
            ("tripbeecute", "每趟旅行都是一本有插畫封面的小手冊：翻開後一路往下滑，就是出發倒數、登機證風格的航班卡、逐日分色的行程，最後是行李清單和旅行筆記。目的地天氣與當地時間一起顯示；每個行程可以附照片、票券和備註，也能用地圖 App 導航，落雨就切換雨天備案。和家人用 iCloud 一起編輯同一本（Cute Pass），或分享成離線也能看的網頁手冊。主畫面與鎖定畫面小工具、Apple Watch、iPad、深色模式、50 種語言；不用註冊帳號、沒有廣告、不追蹤。"),
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
    # 2026-11-12 正確性更正：表紙數照付費口徑（6 種類入り＋Cute Pass 51 種類＋自分の写真）標 Cute Pass；港澳日澳四頁同步標註。
    {
        "key": "tripbeecute", "lang": "ja", "pass_wording": True,
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
                "手帳らしく飾れるか：街や名所、季節のイラスト表紙を選び（6種類入り、Cute Passで51種類を追加でき、自分の写真も表紙にできます）、日ごとの予定に名前をつけてステッカーを付けられます。",
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
        "key": "tripbeecute", "lang": "en-AU", "pass_wording": True,
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
                "Room to decorate: pick an illustrated cover of a city, landmark or season (6 come with the app; Cute Pass adds 51 more and lets you use your own photo as a cover), give each day a name and add stickers to your plans.",
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
    # 2026-11-15 給 AI 助理讀的問答頁（衝刺令 B 項，reports/blitz/sprint_all_2026-11-15.md）：英、繁中、日、韓四頁，
    # 每頁回答四件事：這款是什麼、適合誰、怎麼收費（iOS 與 Google Play 分開寫）、和一般旅遊規劃 App、記帳分帳 App、紙本手帳差在哪。
    # 事實只取 2026-11-15 iTunes 公開查詢讀回的 us／tw／jp／kr 商店描述、Google Play en-US 完整說明，以及
    # reports/blitz/tripbeecute_materials.md「付費口徑」；不寫價格數字、試用、評分或下載數；比較段只寫類別、不點名競品。
    # terms 只放品牌與「是什麼」類問句，不放既有頁的主詞；主卡放第一屏（cards_first）。
    {
        "key": "tripbeecute", "lang": "en", "pass_wording": True, "cards_first": True, "updated": "2026-11-15",
        "slug": "tripbeecute-what-it-is-who-for-pricing-vs-others-en",
        "terms": ["TripBee Cute", "what is TripBee Cute", "TripBee Cute Cute Pass", "TripBee Cute vs trip planner apps"],
        "title": "What Is TripBee Cute? Who It Is For, How Cute Pass Works, and How It Compares",
        "desc": "A plain answer page about TripBee Cute: what the app does, who it suits, what you can use without buying anything on iPhone and on Android, what the one-time Cute Pass adds, and how it differs from trip planners, cost-splitting apps and paper journals.",
        "h1": "TripBee Cute: what it is, who it is for, how you pay, and how it differs from other travel tools",
        "lead": "This page answers four questions people and AI assistants ask about TripBee Cute. Every fact comes from the app's own App Store and Google Play descriptions, read on November 15, 2026.",
        "intro": [
            "In one sentence: TripBee Cute is a travel journal and trip planner that turns one whole trip into one cute illustrated booklet, with the countdown to departure, flights, day plans and the packing list on a single page. It is made by an independent developer and is on the App Store for iPhone and iPad and on Google Play for Android.",
            "The sections below keep the iPhone and Android versions apart where they differ, because the two stores list different things inside Cute Pass. Nothing here is a ranking or a review; it only describes what the store listings say the app does.",
        ],
        "sections": [
            ("What TripBee Cute is", [
                "Each trip sits on a bookshelf as a little booklet with its own illustrated cover. Open it and scroll from the cover art to the countdown, your flights, every day's plan, and finally the packing list and notes. The idea is to stop digging through booking emails, screenshots and notes while you travel.",
            ], [
                "Countdown to departure, plus the weather and local time at your destination.",
                "Flight cards styled like boarding passes, with times, terminals and booking codes.",
                "Day plans you can name, decorate with stickers, check off and reorder; each day has its own color and a date filter shows one day or the whole trip.",
                "Downtime slots and a rainy-day plan you can copy from the main plan.",
                "Photos, tickets and notes kept on each plan, with directions in your maps app.",
                "Expense splitting: log who paid, split evenly or enter each person's amount, then settle up to see who owes whom, with live exchange rates across currencies.",
                "A packing list, trip notes and gentle reminders.",
                "CSV import: export the template, fill it in yourself or ask the AI assistant you already use, then import it and the booklet is ready.",
                "A web booklet: a single web file anyone can open in a browser or chat app, even offline, with a countdown that keeps running.",
                "Home Screen widgets that show your next trip on its cover art; on iPhone also Lock Screen widgets and an Apple Watch app with the countdown and your next plan.",
                "Dark Mode, iPad or tablets, and 50 languages. No account, no ads and no tracking; booklets stay on your device.",
            ]),
            ("Who it is for", [
                "The store listings name a weekend getaway, a family vacation, a road trip, a cruise and a honeymoon. In practice it suits people who already have a trip booked and want everything for that one trip in one place that is nice to open.",
            ], [
                "Travelers whose plans are scattered across emails, screenshots, notes and group chats.",
                "Friends or families travelling together who want to log shared costs on the trip and see who owes whom at the end.",
                "Planners who like spreadsheets or AI assistants, since a filled-in CSV template becomes a booklet.",
                "People who want to share the plan with someone who does not have the app, using the web booklet.",
                "People who care about privacy: there is no account to create, no ads and no tracking.",
                "It is less of a fit if you need a tool that books flights or hotels, or a long-running budget for a household; TripBee Cute is organized around one trip at a time.",
            ]),
            ("How it is charged: iPhone and Android are listed differently", [
                "The app is a download with no up-front charge on both stores. Extra features come with Cute Pass, a one-time purchase made inside the app. It is not a recurring plan, so there is no monthly or yearly charge. This page does not quote prices because they differ by country; the store page shows the amount in your currency.",
                "iPhone and iPad (App Store): without a purchase you can keep one booklet at a time and use 6 covers, CSV import, the web booklet, flights, day plans, expense splitting, the packing list, widgets and the Apple Watch app. Cute Pass adds unlimited booklets, 51 more covers plus your own photos as covers, smart packing lists based on who is coming, the season and trip length, iCloud sync and backup, sharing trip files with photos and tickets, and planning with friends by inviting them through iCloud to edit the same booklet (friends need TripBee Cute too).",
                "Android (Google Play): without buying anything you can make one booklet of your own, open every trip, link and backup file you receive, and use 6 covers, CSV import, the web booklet, flights, day plans, splitting costs, the packing list, reminders and widgets. Cute Pass on Android adds unlimited booklets of your own, 50 more covers plus your own photos as covers, smart packing lists, backup export, and sending trip files with photos and tickets. The Google Play listing does not include iCloud sync, planning together through iCloud or an Apple Watch app; those are part of the iPhone version.",
            ], []),
            ("How it differs from trip planners, cost-splitting apps and paper journals", [
                "General trip planners and itinerary apps are often organized as lists, calendars or maps, and some are built around bookings. TripBee Cute does not book anything: you add or import your own flights and plans, and it lays one trip out as one illustrated booklet you scroll from cover to packing list, with a color for every day.",
                "Dedicated expense-splitting apps are made for shared bills of any kind, including ongoing ones between housemates. In TripBee Cute, splitting lives inside the trip next to the plans: who paid, an even or custom split, settling up and currency conversion. If you only need to share household bills, a dedicated splitting app is the more natural choice; if the costs belong to one trip, keeping them in the same booklet saves switching apps.",
                "A paper travel journal is tactile and lovely to decorate, but copying flight times and rewriting pages when plans change takes time, and it cannot show a countdown on your wrist. TripBee Cute keeps the decorating part (illustrated covers, stickers, a color for each day) while plans stay editable and shareable. If writing by hand is the point for you, paper still does that best.",
            ], []),
        ],
        "steps_title": "Getting started in five minutes",
        "steps": [
            "Install TripBee Cute from the App Store or Google Play and add a new trip.",
            "Give the trip a name and pick an illustrated cover of a city, landmark or season.",
            "Add a flight card and the countdown to departure begins.",
            "Fill in each day, or import a CSV template you filled in yourself or with an AI assistant.",
            "Share a web booklet with your travel mates, and log shared costs as you go.",
        ],
        "cards": [
            ("tripbeecute", "One trip, one cute illustrated booklet: the countdown to departure, destination weather and local time, boarding-pass style flight cards, color-coded day plans, expense splitting with live exchange rates, and the packing list on a single page. Share a web booklet that opens in any browser, even offline. Cute Pass is a one-time purchase inside the app, not a recurring plan. No account, no ads and no tracking."),
        ],
        "faqs": [
            ("Do I pay every month for Cute Pass?", "No. Cute Pass is a one-time purchase made inside the app, on both the App Store and Google Play. It is not a recurring plan."),
            ("What can I use without buying anything?", "On iPhone: one booklet at a time, 6 covers, CSV import, the web booklet, flights, day plans, expense splitting, the packing list, widgets and the Apple Watch app. On Android: one booklet of your own, every trip, link and backup file you receive, 6 covers, CSV import, the web booklet, flights, day plans, splitting costs, the packing list, reminders and widgets."),
            ("Is TripBee Cute on Android?", "Yes, on Google Play. The Android Cute Pass list differs from the iPhone one: it includes backup export and sending trip files, and it does not include iCloud sync or planning together through iCloud."),
            ("Do I need an account?", "No. There is no account, no ads and no tracking. Booklets stay on your device; on iPhone they go to your own private iCloud only when you turn on sync, which is part of Cute Pass."),
        ],
        "related": [("en-US/tripbeecute.html", "TripBee Cute: full app overview")],
        "legal": "Facts on this page come from the TripBee Cute descriptions on the US App Store and on Google Play, read on November 15, 2026; store listings can change. Weather comes from Open-Meteo using only your destination. The app is made by an independent developer.",
    },
    {
        "key": "tripbeecute", "lang": "zh-Hant", "pass_wording": True, "cards_first": True, "updated": "2026-11-15",
        "slug": "tripbeecute-what-it-is-who-for-pricing-vs-others-zhhant",
        "terms": ["TripBee Cute", "TripBee Cute 是什麼", "TripBee Cute 怎麼收費", "TripBee Cute 和其他旅遊 App 差在哪"],
        "title": "TripBee Cute 是什麼？適合誰、Cute Pass 怎麼收費、和其他旅遊工具差在哪",
        "desc": "一頁看懂 TripBee Cute：這款 App 做什麼、適合哪些人、iPhone 與 Android 不購買能用什麼、一次性購買的 Cute Pass 多了什麼，以及和一般旅遊規劃 App、記帳分帳 App、紙本手帳的差別。",
        "h1": "TripBee Cute 問答：是什麼、適合誰、怎麼收費、和同類差在哪",
        "lead": "這一頁替想認識 TripBee Cute 的人與 AI 助理，照實回答四個最常被問的問題。內容全部取自這款 App 在 App Store 與 Google Play 的商店說明，於 2026 年 11 月 15 日讀取。",
        "intro": [
            "一句話說明：TripBee Cute 是一款旅行手帳兼行程規劃 App，把一整趟旅行收進一本可愛的插畫手冊，出發倒數、航班、每日行程和行李清單都在同一頁。由獨立開發者製作，iPhone、iPad 在 App Store，Android 在 Google Play。",
            "兩個商店列出的 Cute Pass 內容不完全一樣，所以下面講到收費時，iPhone 版和 Android 版分開寫。本頁不是排行或評測，只描述商店說明裡寫的功能。",
        ],
        "sections": [
            ("TripBee Cute 是什麼", [
                "每趟旅行都是書架上的一本小手冊，有自己的插畫封面。翻開後一路往下滑：封面插畫、出發倒數、航班、每天的行程，最後是行李清單和筆記。目的是讓你不用再翻截圖、訂位信和備忘錄找資料。",
            ], [
                "出發倒數，加上目的地天氣與當地時間。",
                "登機證風格的航班卡：時間、航廈、訂位代號。",
                "每日行程：替每天命名、貼上貼紙、完成打勾、調整順序；每天各有顏色，可依日期篩選只看某一天或看全部。",
                "空檔時間，以及可從主計畫複製的雨天備案。",
                "每個行程都能附上照片、票券和備註，還能用地圖 App 導航。",
                "分帳：和旅伴記下誰付了錢、平均分或各自輸入金額，結算時算清誰該付給誰，不同幣別用即時匯率換算。",
                "行李清單、旅行筆記與貼心提醒。",
                "CSV 匯入：匯出範本，自己填好或交給慣用的 AI 助理幫忙填，再匯入就會變成一本手冊。",
                "網頁手冊：一個網頁檔，任何瀏覽器或聊天 App 都能打開，離線也能看，倒數也會持續跑。",
                "主畫面小工具用封面插畫顯示下一趟旅行；iPhone 版另有鎖定畫面小工具，以及顯示倒數和下一個行程的 Apple Watch App。",
                "深色模式、iPad 或平板、50 種語言。不用註冊帳號、沒有廣告、不追蹤，手冊存在你的裝置上。",
            ]),
            ("適合誰", [
                "商店說明列出的情境有週末小旅行、全家出遊、環島、畢業旅行、蜜月，以及第一次出國自由行。實際上最適合已經訂好行程、想把這一趟的所有資料放在同一個打開就開心的地方的人。",
            ], [
                "行程資料散在訂位信、截圖、備忘錄和聊天群組裡的人。",
                "和朋友或家人一起出遊，想在行程上直接記共同花費、最後算清誰該付給誰的人。",
                "習慣用試算表或 AI 助理排行程的人：填好的 CSV 範本可以直接變成手冊。",
                "想把行程傳給沒有裝 App 的家人朋友看的人：網頁手冊用瀏覽器就能打開。",
                "在意隱私的人：不用註冊帳號、沒有廣告、不追蹤。",
                "比較不適合：需要直接訂機票、訂飯店的人，或要長期管理家庭收支的人；TripBee Cute 是以「一趟旅行」為單位設計的。",
            ]),
            ("怎麼收費：iPhone 版和 Android 版分開看", [
                "兩個商店都可以直接下載，不必先付費。進階功能屬於 Cute Pass，是一次性 App 內購買，不是訂閱，沒有按月或按年收費。各國金額不同，本頁不寫金額，請以商店頁顯示的當地幣別為準。",
                "iPhone、iPad（App Store）：不購買也能一次保存 1 本手冊，並使用 6 款封面、CSV 匯入、網頁手冊、航班、每日行程、分帳、行李清單、小工具和 Apple Watch App。Cute Pass 解鎖：不限手冊數量、再多 51 款封面並可用自己的照片當封面、依同行者季節與天數產生的智慧行李清單、iCloud 同步與備份、分享含照片與票券的行程檔，以及透過 iCloud 邀請朋友共同編輯同一本手冊（對方也需要安裝 TripBee Cute）。",
                "Android（Google Play）：不購買也能建立 1 本自己的手冊、打開收到的所有行程、連結和備份檔，並使用 6 款封面、CSV 匯入、網頁手冊、航班、每日行程、分帳、行李清單、提醒和小工具。Android 版的 Cute Pass 解鎖：不限自己的手冊數量、再多 50 款封面並可用自己的照片當封面、智慧行李清單、匯出備份，以及傳送含照片與票券的行程檔。Google Play 的說明沒有列 iCloud 同步、透過 iCloud 一起規劃和 Apple Watch App，這幾項屬於 iPhone 版。",
            ], []),
            ("和一般旅遊規劃 App、記帳分帳 App、紙本手帳差在哪", [
                "一般旅遊規劃或行程 App，多半用清單、行事曆或地圖來排，有些以訂票訂房為主。TripBee Cute 不幫你訂任何東西：航班和行程由你自己加入或用 CSV 匯入，然後把一趟旅行排成一本從封面滑到行李清單的插畫手冊，每一天都有自己的顏色。",
                "專門的記帳分帳 App，適合各種共同開銷，包括室友之間長期的帳。TripBee Cute 的分帳放在旅行裡、就在行程旁邊：誰付的、平均分或自訂金額、結算與換匯。如果只是要記家裡或室友的日常帳，專門的分帳 App 比較合適；如果這些花費屬於同一趟旅行，放在同一本手冊裡就不用另開一個 App。",
                "紙本旅行手帳摸得到、很好裝飾，但抄航班、行程一改就要重寫，也沒辦法在手錶上看倒數。TripBee Cute 保留了裝飾的樂趣（插畫封面、貼紙、每天一種顏色），行程又能隨時修改、分享給旅伴。如果你就是喜歡手寫的感覺，紙本在這一點上還是最好的。",
            ], []),
        ],
        "steps_title": "5 分鐘開始用",
        "steps": [
            "從 App Store 或 Google Play 安裝 TripBee Cute，新增一趟旅行。",
            "幫旅行取個名字，挑一張城市、地標或季節的插畫封面。",
            "加上航班卡，出發倒數就會開始跑。",
            "把每一天的行程填進去，或匯入自己填好、或請 AI 助理幫忙填的 CSV 範本。",
            "分享網頁手冊給旅伴，出遊時把共同花費記在行程上。",
        ],
        "cards": [
            ("tripbeecute", "一趟旅行一本可愛的插畫手冊：出發倒數、目的地天氣與當地時間、登機證風格的航班卡、每天分色的行程、用即時匯率換算的分帳，以及行李清單，全在同一頁。分享成網頁手冊，任何瀏覽器都能打開，離線也能看。Cute Pass 是一次性 App 內購買，不是訂閱。不用註冊帳號、沒有廣告、不追蹤。"),
        ],
        "faqs": [
            ("Cute Pass 是訂閱嗎？", "不是。Cute Pass 在 App Store 和 Google Play 都是一次性 App 內購買，不會按月或按年收費。"),
            ("不購買能用哪些功能？", "iPhone 版：一次保存 1 本手冊、6 款封面、CSV 匯入、網頁手冊、航班、每日行程、分帳、行李清單、小工具和 Apple Watch App。Android 版：1 本自己的手冊、打開收到的所有行程連結和備份檔、6 款封面、CSV 匯入、網頁手冊、航班、每日行程、分帳、行李清單、提醒和小工具。"),
            ("Android 也有嗎？", "有，在 Google Play。Android 版的 Cute Pass 內容和 iPhone 版不同：包含匯出備份與傳送行程檔，不包含 iCloud 同步和透過 iCloud 一起規劃。"),
            ("需要註冊帳號嗎？", "不用。不用註冊帳號、沒有廣告、不追蹤；手冊存在你的裝置上，iPhone 版只有在開啟 iCloud 同步（Cute Pass）時才會存到你自己的私人 iCloud。"),
        ],
        "related": [("zh-Hant/tripbeecute.html", "TripBee Cute 完整介紹")],
        "legal": "本頁內容取自 TripBee Cute 在 App Store 與 Google Play 的商店說明，2026 年 11 月 15 日讀取；商店內容可能更新。天氣資料來自 Open-Meteo，只會用到目的地。本頁介紹的 App 為獨立開發。",
    },
    {
        "key": "tripbeecute", "lang": "ja", "pass_wording": True, "cards_first": True, "updated": "2026-11-15",
        "slug": "tripbeecute-what-it-is-who-for-pricing-vs-others-ja",
        "terms": ["TripBee Cute", "TripBee Cute とは", "TripBee Cute 料金", "TripBee Cute 違い"],
        "title": "TripBee Cute とは？どんな人向けか、Cute Pass の支払い方、ほかの旅行ツールとの違い",
        "desc": "TripBee Cute がどんなアプリか、どんな人に向いているか、iPhone と Android で購入せずに使える機能、1回限りの購入の Cute Pass で増える機能、一般的な旅行計画アプリ・割り勘アプリ・紙の手帳との違いを、ストアの説明だけをもとにまとめました。",
        "h1": "TripBee Cute のQ&A：どんなアプリか、誰向けか、支払い方、ほかとの違い",
        "lead": "このページは、TripBee Cute について人や AI アシスタントがよく尋ねる4つの質問に、事実だけで答えます。内容はすべて App Store と Google Play の説明文から取り、2026年11月15日に確認しました。",
        "intro": [
            "ひとことで言うと、TripBee Cute は旅の予定をかわいいイラストのしおり1冊にまとめる旅行手帳・旅行計画アプリです。出発までのカウントダウン、フライト、毎日の予定、持ち物リストが1ページで見渡せます。個人開発で、iPhone と iPad は App Store、Android は Google Play で配信されています。",
            "2つのストアで Cute Pass に含まれる内容が少し違うため、支払いの節では iPhone 版と Android 版を分けて書いています。ランキングやレビューではなく、ストアの説明に書かれている機能だけを紹介します。",
        ],
        "sections": [
            ("TripBee Cute はどんなアプリか", [
                "旅はそれぞれ、本棚に並ぶ1冊のしおりになります。イラストの表紙を開いたら、そのまま下へスクロールするだけで、出発までのカウントダウン、フライト、毎日の予定、持ち物リストとメモまで続きます。スクショやメール、メモに散らばった予定を探し回らなくてすむように作られています。",
            ], [
                "出発までのカウントダウン、行き先の天気と現地時刻。",
                "搭乗券風のフライトカード：時刻、ターミナル、予約番号。",
                "毎日の予定：日ごとの名前、ステッカー、完了チェック、並べ替え。日ごとに色が分かれ、日付で絞り込めばその日の予定だけを表示できます。",
                "すき間時間と、メインの予定からコピーできる雨の日プラン。",
                "予定ごとに写真・チケット・メモを添付、マップアプリで道順も確認。",
                "割り勘：誰が払ったかを記録し、均等に分けるか金額を個別に入力。精算で誰が誰に払うかを計算し、異なる通貨はリアルタイムの為替レートで換算します。",
                "持ち物リスト、旅のメモ、やさしいリマインダー。",
                "CSV の読み込み：テンプレートを書き出して自分で記入するか、ふだん使っている AI アシスタントに記入してもらい、読み込めばしおりが完成します。",
                "Web しおり：1つの Web ファイルで、どのブラウザやチャットアプリでも開け、オフラインでも見られ、カウントダウンも進み続けます。",
                "表紙イラストで次の旅を表示するホーム画面ウィジェット。iPhone 版にはロック画面ウィジェットと、カウントダウンと次の予定がわかる Apple Watch アプリもあります。",
                "ダークモード、iPad やタブレット、50言語に対応。アカウント登録なし、広告なし、トラッキングなしで、しおりは端末に保存されます。",
            ]),
            ("どんな人に向いているか", [
                "ストアの説明に挙がっているのは、週末の街歩き、家族旅行、女子旅、卒業旅行、新婚旅行、ライブ遠征、はじめての海外旅行です。予約はもう済んでいて、その旅の情報を開くのが楽しみになる1か所にまとめたい人に向いています。",
            ], [
                "予定が予約メール、スクショ、メモ、グループチャットに散らばっている人。",
                "友だちや家族と旅行して、立て替えた出費を予定につけ、最後に誰が誰に払うかをはっきりさせたい人。",
                "表計算や AI アシスタントで予定を立てる人。記入した CSV テンプレートがそのまましおりになります。",
                "アプリを入れていない家族や友だちに予定を見せたい人。Web しおりならブラウザで開けます。",
                "プライバシーを気にする人。アカウント登録も広告もトラッキングもありません。",
                "あまり向かないのは、航空券やホテルをアプリ内で予約したい人や、家計を長く管理したい人です。TripBee Cute は旅1回ごとに使う設計です。",
            ]),
            ("支払い方：iPhone 版と Android 版は内容が違います", [
                "どちらのストアでも、先にお金を払わずにダウンロードできます。追加の機能は Cute Pass に含まれ、これは1回限りの App 内購入です。毎月や毎年の支払いはありません。金額は国によって違うため、このページには書いていません。ストアのページに表示される現地の金額をご確認ください。",
                "iPhone・iPad（App Store）：購入しなくても、しおりを一度に1冊保存でき、表紙6種類、CSV の読み込み、Web しおり、フライト、毎日の予定、割り勘、持ち物リスト、ウィジェット、Apple Watch アプリが使えます。Cute Pass で増えるのは、しおりの冊数無制限、表紙51種類の追加と自分の写真を表紙にする機能、同行者・季節・日数から作るスマート持ち物リスト、iCloud 同期とバックアップ、写真やチケット入りの旅行ファイルの共有、iCloud で友だちを招待して同じしおりを共同編集する機能（相手にも TripBee Cute が必要）です。",
                "Android（Google Play）：購入しなくても、自分のしおりを1冊作れ、受け取った旅行・リンク・バックアップファイルはすべて開けます。表紙6種類、CSV の読み込み、Web しおり、フライト、毎日の予定、割り勘、持ち物リスト、リマインダー、ウィジェットも使えます。Android 版の Cute Pass で増えるのは、自分のしおりの冊数無制限、表紙50種類の追加と自分の写真を表紙にする機能、スマート持ち物リスト、バックアップの書き出し、写真やチケット入りの旅行ファイルの送信です。Google Play の説明には iCloud 同期、iCloud での共同編集、Apple Watch アプリは載っておらず、これらは iPhone 版の機能です。",
            ], []),
            ("一般的な旅行計画アプリ・割り勘アプリ・紙の手帳との違い", [
                "一般的な旅行計画アプリや行程アプリは、リストやカレンダー、地図で整理するものが多く、予約が中心のものもあります。TripBee Cute は何かを予約するアプリではありません。フライトや予定は自分で入れるか CSV で読み込み、1回の旅を表紙から持ち物リストまでスクロールするイラストのしおり1冊にまとめます。日ごとに色が分かれます。",
                "割り勘専用のアプリは、ルームメイトとの継続的な精算も含め、あらゆる共同の出費に使えるように作られています。TripBee Cute の割り勘は旅の中、予定のすぐそばにあり、誰が払ったか、均等か個別の金額か、精算と通貨の換算までを扱います。日々の家計やルームメイトとの精算だけなら専用アプリのほうが自然です。出費が1回の旅のものなら、同じしおりにまとめればアプリを行き来せずにすみます。",
                "紙の旅行手帳は手ざわりがあって飾るのも楽しい反面、フライトを書き写したり、予定が変わるたびに書き直したりするのは手間で、カウントダウンを手首で見ることもできません。TripBee Cute は飾る楽しさ（イラストの表紙、ステッカー、日ごとの色）を残しつつ、予定はいつでも直せて旅の仲間と共有できます。手書きそのものが好きなら、その点ではやはり紙がいちばんです。",
            ], []),
        ],
        "steps_title": "5分ではじめる",
        "steps": [
            "App Store か Google Play から TripBee Cute を入れて、新しい旅を追加します。",
            "旅に名前をつけ、街・名所・季節のイラスト表紙を選びます。",
            "フライトカードを入れると、出発までのカウントダウンが始まります。",
            "毎日の予定を入れるか、自分や AI アシスタントが記入した CSV テンプレートを読み込みます。",
            "Web しおりを旅の仲間に共有し、旅先では立て替えた出費を予定につけていきます。",
        ],
        "cards": [
            ("tripbeecute", "旅1回をかわいいイラストのしおり1冊に。出発までのカウントダウン、行き先の天気と現地時刻、搭乗券風のフライトカード、日ごとに色分けした予定、リアルタイムの為替レートで換算する割り勘、持ち物リストが1ページに。Web しおりで共有すれば、どのブラウザでもオフラインでも見られます。Cute Pass は1回限りの App 内購入で、毎月の支払いはありません。アカウント登録なし、広告なし、トラッキングなし。"),
        ],
        "faqs": [
            ("Cute Pass は毎月お金がかかりますか？", "いいえ。Cute Pass は App Store でも Google Play でも1回限りの App 内購入で、毎月や毎年の支払いはありません。"),
            ("購入しなくても使える機能は？", "iPhone 版：しおり1冊（一度に1冊保存）、表紙6種類、CSV の読み込み、Web しおり、フライト、毎日の予定、割り勘、持ち物リスト、ウィジェット、Apple Watch アプリ。Android 版：自分のしおり1冊、受け取った旅行・リンク・バックアップファイルの閲覧、表紙6種類、CSV の読み込み、Web しおり、フライト、毎日の予定、割り勘、持ち物リスト、リマインダー、ウィジェット。"),
            ("Android 版はありますか？", "はい、Google Play にあります。Android 版の Cute Pass は iPhone 版と内容が違い、バックアップの書き出しと旅行ファイルの送信を含み、iCloud 同期と iCloud での共同編集は含みません。"),
            ("アカウント登録は必要ですか？", "いいえ。アカウント登録なし、広告なし、トラッキングなしです。しおりは端末に保存され、iPhone 版では同期（Cute Pass）をオンにしたときだけ、あなた自身のプライベートな iCloud に保存されます。"),
        ],
        "related": [("ja/tripbeecute.html", "TripBee Cute の詳しい紹介")],
        "legal": "このページの内容は、TripBee Cute の App Store と Google Play の説明文を2026年11月15日に確認したものです。ストアの内容は変わることがあります。天気は Open-Meteo から行き先の情報だけを使って取得します。紹介しているアプリは個人開発です。",
    },
    {
        "key": "tripbeecute", "lang": "ko", "pass_wording": True, "cards_first": True, "updated": "2026-11-15",
        "slug": "tripbeecute-what-it-is-who-for-pricing-vs-others-ko",
        "terms": ["TripBee Cute", "TripBee Cute 뭐예요", "TripBee Cute 요금", "TripBee Cute 차이"],
        "title": "TripBee Cute는 어떤 앱? 누구에게 맞는지, Cute Pass 결제 방식, 다른 여행 도구와의 차이",
        "desc": "TripBee Cute가 어떤 앱인지, 누구에게 잘 맞는지, iPhone과 Android에서 구입하지 않고 쓸 수 있는 기능, 1회성 구입인 Cute Pass로 늘어나는 기능, 일반 여행 계획 앱·정산 앱·종이 다이어리와의 차이를 스토어 설명만으로 정리했어요.",
        "h1": "TripBee Cute 문답: 어떤 앱인지, 누구에게 맞는지, 어떻게 결제하는지, 무엇이 다른지",
        "lead": "이 페이지는 사람과 AI 어시스턴트가 TripBee Cute에 대해 자주 묻는 네 가지 질문에 사실만으로 답해요. 내용은 모두 App Store와 Google Play의 앱 설명에서 가져왔고, 2026년 11월 15일에 확인했어요.",
        "intro": [
            "한마디로 TripBee Cute는 여행 한 번을 귀여운 일러스트 여행 책자 한 권으로 모아 주는 여행 다이어리 겸 여행 계획 앱이에요. 출발 디데이, 항공편, 하루 일정, 준비물 리스트를 한 페이지에서 볼 수 있어요. 독립 개발자가 만들었고, iPhone과 iPad는 App Store, Android는 Google Play에 있어요.",
            "두 스토어에서 Cute Pass에 들어 있는 내용이 조금 달라서, 결제 부분은 iPhone 버전과 Android 버전을 나눠서 적었어요. 순위나 리뷰가 아니라 스토어 설명에 적힌 기능만 소개해요.",
        ],
        "sections": [
            ("TripBee Cute는 어떤 앱인가요", [
                "여행마다 책장에 꽂히는 작은 책자 한 권이 생겨요. 일러스트 표지를 펼치고 아래로 내리기만 하면 출발 디데이, 항공편, 날마다의 일정, 준비물 리스트와 메모까지 이어져요. 캡처, 메일, 메모에 흩어진 여행 정보를 찾아 헤매지 않도록 만든 앱이에요.",
            ], [
                "출발 디데이, 여행지 날씨와 현지 시간.",
                "탑승권 스타일 항공편 카드: 시간, 터미널, 예약 번호.",
                "하루 일정: 날마다 이름 붙이기, 스티커, 완료 체크, 순서 바꾸기. 날짜마다 색이 달라 한눈에 구분되고, 날짜 필터로 그날 일정만 볼 수 있어요.",
                "빈 시간, 그리고 메인 일정에서 복사할 수 있는 우천 플랜.",
                "일정마다 사진, 티켓, 메모 첨부, 지도 앱으로 길찾기.",
                "더치페이: 누가 냈는지 기록하고 똑같이 나누거나 금액을 각자 입력, 정산하면 누가 누구에게 보낼지 계산하고 다른 통화는 실시간 환율로 환산해요.",
                "준비물 리스트, 여행 메모와 다정한 알림.",
                "CSV 가져오기: 템플릿을 내보내 직접 채우거나 평소 쓰는 AI 어시스턴트에게 채워 달라고 한 뒤 가져오면 책자가 완성돼요.",
                "웹 책자: 웹 파일 하나로 어떤 브라우저나 메신저에서도 열리고, 오프라인에서도 볼 수 있으며 디데이도 계속 줄어들어요.",
                "표지 일러스트로 다음 여행을 보여 주는 홈 화면 위젯. iPhone 버전에는 잠금 화면 위젯과 디데이와 다음 일정을 보여 주는 Apple Watch 앱도 있어요.",
                "다크 모드, iPad나 태블릿, 50개 언어. 계정 가입, 광고, 추적이 없고 책자는 기기에 저장돼요.",
            ]),
            ("누구에게 잘 맞나요", [
                "스토어 설명에 나오는 여행은 주말 도시 여행, 가족 여행, 우정 여행, 커플 여행, 신혼여행, 첫 해외여행이에요. 예약은 이미 끝났고, 그 여행의 정보를 열어 볼 때마다 기분 좋은 한곳에 모으고 싶은 사람에게 잘 맞아요.",
            ], [
                "일정이 예약 메일, 캡처, 메모, 단체 채팅방에 흩어져 있는 사람.",
                "친구나 가족과 함께 여행하면서 같이 쓴 경비를 일정에 적고, 마지막에 누가 누구에게 보내면 되는지 깔끔하게 정리하고 싶은 사람.",
                "스프레드시트나 AI 어시스턴트로 계획하는 사람. 채운 CSV 템플릿이 바로 책자가 돼요.",
                "앱이 없는 가족이나 친구에게 일정을 보여 주고 싶은 사람. 웹 책자는 브라우저에서 열려요.",
                "개인정보가 신경 쓰이는 사람. 계정 가입도, 광고도, 추적도 없어요.",
                "덜 맞는 경우: 앱 안에서 항공권이나 숙소를 예약하고 싶은 사람, 집안 살림 가계부를 오래 관리하고 싶은 사람. TripBee Cute는 여행 한 번 단위로 쓰도록 만들어졌어요.",
            ]),
            ("결제 방식: iPhone 버전과 Android 버전은 내용이 달라요", [
                "두 스토어 모두 먼저 돈을 내지 않고 내려받을 수 있어요. 추가 기능은 Cute Pass에 들어 있고, Cute Pass는 1회성 앱 내 구입이에요. 구독이 아니어서 매달이나 매년 결제되지 않아요. 금액은 나라마다 달라서 이 페이지에는 적지 않았어요. 스토어 페이지에 표시되는 현지 통화 금액을 확인해 주세요.",
                "iPhone·iPad(App Store): 구입하지 않아도 책자를 한 번에 1권 보관하고 표지 6종, CSV 가져오기, 웹 책자, 항공편, 하루 일정, 더치페이, 준비물 리스트, 위젯, Apple Watch 앱을 쓸 수 있어요. Cute Pass로 늘어나는 것은 책자 개수 제한 없음, 표지 51종 추가와 내 사진을 표지로 쓰기, 동행·계절·여행 기간에 맞춘 스마트 준비물 리스트, iCloud 동기화와 백업, 사진·티켓이 담긴 여행 파일 공유, iCloud로 친구를 초대해 같은 책자를 공동 편집하기(친구도 TripBee Cute 필요)예요.",
                "Android(Google Play): 구입하지 않아도 내 책자 1권을 만들고, 받은 여행·링크·백업 파일은 모두 열 수 있어요. 표지 6종, CSV 가져오기, 웹 책자, 항공편, 하루 일정, 더치페이, 준비물 리스트, 알림, 위젯도 쓸 수 있어요. Android 버전의 Cute Pass로 늘어나는 것은 내 책자 개수 제한 없음, 표지 50종 추가와 내 사진을 표지로 쓰기, 스마트 준비물 리스트, 백업 내보내기, 사진·티켓이 담긴 여행 파일 보내기예요. Google Play 설명에는 iCloud 동기화, iCloud 공동 편집, Apple Watch 앱이 없고, 이 기능들은 iPhone 버전에 있어요.",
            ], []),
            ("일반 여행 계획 앱, 정산 앱, 종이 다이어리와 무엇이 다른가요", [
                "일반 여행 계획 앱이나 일정 앱은 목록, 캘린더, 지도로 정리하는 경우가 많고, 예약이 중심인 앱도 있어요. TripBee Cute는 무언가를 예약해 주는 앱이 아니에요. 항공편과 일정은 직접 넣거나 CSV로 가져오고, 여행 한 번을 표지부터 준비물 리스트까지 스크롤하는 일러스트 책자 한 권으로 정리해요. 날짜마다 색이 달라요.",
                "정산 전용 앱은 룸메이트와 계속 나누는 생활비까지 포함해 모든 공동 지출에 쓸 수 있게 만들어져 있어요. TripBee Cute의 더치페이는 여행 안, 일정 바로 옆에 있어서 누가 냈는지, 똑같이 나눌지 금액을 따로 넣을지, 정산과 환율 환산까지 다뤄요. 집안이나 룸메이트 정산만 필요하다면 전용 앱이 더 자연스럽고, 경비가 한 번의 여행에 속한다면 같은 책자에 모아 두는 편이 앱을 오가지 않아도 돼서 편해요.",
                "종이 여행 다이어리는 손에 잡히는 느낌이 좋고 꾸미는 재미가 있지만, 항공편을 옮겨 적고 일정이 바뀔 때마다 다시 쓰는 데 시간이 들고, 손목에서 디데이를 볼 수도 없어요. TripBee Cute는 꾸미는 재미(일러스트 표지, 스티커, 날짜별 색)는 살리면서 일정은 언제든 고치고 동행과 공유할 수 있어요. 손글씨 자체를 좋아한다면 그 점에서는 여전히 종이가 가장 좋아요.",
            ], []),
        ],
        "steps_title": "5분 만에 시작하기",
        "steps": [
            "App Store나 Google Play에서 TripBee Cute를 설치하고 새 여행을 추가해요.",
            "여행 이름을 정하고 도시, 랜드마크, 계절 일러스트 표지를 골라요.",
            "항공편 카드를 넣으면 출발 디데이가 시작돼요.",
            "날마다 일정을 채우거나, 직접 또는 AI 어시스턴트가 채운 CSV 템플릿을 가져와요.",
            "웹 책자를 동행에게 공유하고, 여행 중에는 같이 쓴 경비를 일정에 적어요.",
        ],
        "cards": [
            ("tripbeecute", "여행 한 번을 귀여운 일러스트 책자 한 권으로. 출발 디데이, 여행지 날씨와 현지 시간, 탑승권 스타일 항공편 카드, 날짜별 색으로 나뉜 일정, 실시간 환율로 환산하는 더치페이, 준비물 리스트가 한 페이지에 있어요. 웹 책자로 공유하면 어떤 브라우저에서도, 오프라인에서도 열려요. Cute Pass는 1회성 앱 내 구입이고 구독이 아니에요. 계정 가입, 광고, 추적이 없어요."),
        ],
        "faqs": [
            ("Cute Pass는 구독인가요?", "아니요. Cute Pass는 App Store와 Google Play 모두 1회성 앱 내 구입이라 매달이나 매년 결제되지 않아요."),
            ("구입하지 않고 쓸 수 있는 기능은요?", "iPhone 버전: 책자 1권(한 번에 1권 보관), 표지 6종, CSV 가져오기, 웹 책자, 항공편, 하루 일정, 더치페이, 준비물 리스트, 위젯, Apple Watch 앱. Android 버전: 내 책자 1권, 받은 여행·링크·백업 파일 열기, 표지 6종, CSV 가져오기, 웹 책자, 항공편, 하루 일정, 더치페이, 준비물 리스트, 알림, 위젯."),
            ("Android 버전도 있나요?", "네, Google Play에 있어요. Android 버전의 Cute Pass는 iPhone 버전과 내용이 달라서 백업 내보내기와 여행 파일 보내기가 들어 있고, iCloud 동기화와 iCloud 공동 편집은 들어 있지 않아요."),
            ("계정 가입이 필요한가요?", "아니요. 계정 가입, 광고, 추적이 없어요. 책자는 기기에 저장되고, iPhone 버전에서는 동기화(Cute Pass)를 켰을 때만 내 개인 iCloud에 저장돼요."),
        ],
        "related": [("ko/tripbeecute.html", "TripBee Cute 자세히 보기")],
        "legal": "이 페이지의 내용은 2026년 11월 15일에 확인한 TripBee Cute의 App Store와 Google Play 앱 설명을 바탕으로 해요. 스토어 내용은 바뀔 수 있어요. 날씨는 Open-Meteo에서 여행지 정보만 사용해 가져와요. 소개한 앱은 독립 개발 앱이에요.",
    },
    # 2026-11-16 美國英文意圖頁（CLAUDE 1.7 美國搜尋曝光主力；小組 F）：iTunes 公開搜尋 country=us 實測本款
    # 「cute trip planner」#34（185 款）、「trip planner cute」#38（181 款），落在 31～40 名缺口；「cute itinerary」已 #1
    # （美國店名是 TripBee Cute: Itinerary Maker）不放進 terms，留作對照詞；「travel journal app」「packing list cute」
    # 前 200 名外也不放。美國不另開 en-US 目錄，沿用 en（美國店）。功能句只取 2026-11-16 讀回的美國店 1.0.3 描述；
    # Cute Pass 標示照 reports/blitz/tripbeecute_materials.md「付費口徑」，不寫價格、試用。判讀 11-23（+7）。
    {
        "key": "tripbeecute", "lang": "en", "pass_wording": True, "updated": "2026-11-16",
        "slug": "cute-trip-planner-app-itinerary-booklet-us",
        "terms": ["cute trip planner", "trip planner cute", "cute vacation itinerary", "aesthetic trip planner"],
        "title": "Cute Trip Planner App: Turn Your Itinerary Into One Illustrated Booklet (Flights, Day Plans, Packing, Countdown)",
        "desc": "Want a trip planner that is actually cute? What to look for, how to turn booking emails and screenshots into one illustrated booklet with a countdown, flight cards, color-coded day plans and a packing list, and how to plan with friends. Direct US App Store and Google Play links.",
        "h1": "Cute trip planner: your countdown, flights, color-coded days and packing list in one illustrated booklet",
        "lead": "People who search the App Store for a cute trip planner usually have the trip half booked already. The flights are in one email, the hotel is in another, the brunch spot is a screenshot, and the group chat has everything else.",
        "intro": [
            "Most planning apps look like a spreadsheet or a calendar. They are useful, but opening them does nothing for the excitement of the trip, and a list of rows is hard to scan when you are standing in an airport. A paper planner with stickers looks great, but rewriting a page every time a reservation moves takes a lot of evenings. What most people want is something in between: as quick to edit as a phone, and as nice to flip through as a journal.",
            "We searched the US App Store for cute trip planner in November 2026. The results were a mix of general itinerary apps, journals and booking tools. Few of them lay out one whole trip, from the countdown to the packing list, as one illustrated page you scroll. Below is what to check before you pick one, and how to build your first booklet in about five minutes.",
        ],
        "sections": [
            ("Five things to check in a cute trip planner", [], [
                "The whole trip on one page: open the illustrated cover and scroll through the countdown, your flights, every day's plan, then the packing list and notes, instead of jumping between apps.",
                "Covers you actually like: illustrated covers with cities, landmarks, seasons and travel moods (6 come with the app; Cute Pass adds 51 more and lets you use your own photos as covers).",
                "Days you can tell apart: each day has its own color, you can name the days and decorate plans with stickers, and a date filter shows one day or the whole trip.",
                "Keepsakes beside the plan: photos, tickets and notes sit right next to the plan they belong to, with directions in your maps app.",
                "A glance without opening it: Home Screen and Lock Screen widgets show your next trip on its cover art, and the Apple Watch app shows the countdown and your next plan.",
            ]),
            ("Three trips, three ways to plan them", [
                "A girls' weekend or a holiday-season getaway: name the trip, pick a cover and fill in each day, leaving downtime slots so the plan does not feel rushed. If it rains, switch to the rainy-day plan you copied from the main plan.",
                "Winter break or spring break with flights: add a flight card styled like a boarding pass, with times, terminals and booking codes, and the countdown to departure begins. The weather and local time at your destination sit right there too.",
                "A family vacation, a road trip or a cruise with friends: share a web booklet, a single web file anyone can open in a browser or chat app, even offline, with a countdown that keeps running. Shared costs can be split right on the trip: log who paid, split evenly or enter each person's amount, then settle up to see who owes whom, with live exchange rates across currencies.",
            ], []),
            ("Planning together and planning from a spreadsheet", [
                "Want everyone editing the same plan? Invite friends through iCloud to edit one booklet together, and changes sync to each device (Cute Pass; friends need TripBee Cute too). A smart packing list based on who is coming, the season and trip length is also part of Cute Pass, while the regular packing list is in the app from the start.",
                "Already have the itinerary in a spreadsheet? Export the CSV template, fill it in yourself or ask the AI assistant you already use to fill it in, then import it and your booklet is ready. Without buying anything you can keep one booklet at a time and use 6 covers, CSV import, the web booklet, flights, day plans, expense splitting, the packing list, widgets and the Apple Watch app. Cute Pass is a one-time purchase inside the app, not a recurring plan.",
                "No account, no ads and no tracking. Your booklets stay on your device. Weather comes from Open-Meteo and uses only your destination. Dark Mode, iPad and 50 languages are supported.",
            ], []),
        ],
        "steps_title": "Make your first cute trip booklet in five minutes",
        "steps": [
            "Open TripBee Cute, add a new trip and give it a name.",
            "Pick an illustrated cover of a city, landmark, season or travel mood.",
            "Add a flight card and the countdown to departure begins.",
            "Fill in each day: name it, add plans and stickers, and keep photos and tickets next to each plan.",
            "Build your packing list, share a web booklet with your travel buddies, and check off your plans day by day.",
        ],
        "cards": [
            ("tripbeecute", "Stop digging through emails, screenshots and notes: TripBee Cute turns your whole trip into one cute illustrated booklet, with the countdown, destination weather and local time, boarding-pass style flight cards, color-coded day plans and the packing list on a single page. Keep photos, tickets and notes beside each plan, split shared costs with your travel buddies, and share a web booklet that opens in any browser, even offline. Widgets, Apple Watch, iPad, Dark Mode and 50 languages. No account, no ads and no tracking."),
        ],
        "faqs": [
            ("Can my friends see the itinerary without the app?", "Yes. Share a web booklet: a single web file that opens in any browser or chat app, even offline, and keeps the countdown running."),
            ("Can we plan the trip together?", "Yes, with Cute Pass: invite friends through iCloud to edit the same booklet, and changes sync to each device. Friends need TripBee Cute too."),
            ("Is Cute Pass a monthly charge?", "No. Cute Pass is a one-time purchase inside the app, not a recurring plan. Without it you can keep one booklet at a time and use 6 covers, flights, day plans, expense splitting, the packing list, widgets and the Apple Watch app."),
            ("Do I need to sign up?", "No. There is no account, no ads and no tracking, and your booklets stay on your device."),
        ],
        "related": [("en-US/tripbeecute.html", "TripBee Cute: full app overview"),
                    ("en/seasonal/tripbeecute-what-it-is-who-for-pricing-vs-others-en.html", "What is TripBee Cute? Who it is for and how Cute Pass works")],
        "legal": "Facts on this page come from the TripBee Cute description on the US App Store, read on November 16, 2026; store listings can change. App Store search results are from a real search of the US App Store in November 2026, and rankings change. Weather comes from Open-Meteo using only your destination. The app is made by an independent developer.",
    },
]


_G3_SITEMAP_NAME = g3.sitemap_name
_G3_RENDER = g3.render
_APPS_BLOCK = re.compile(r'<section id="apps">.*?</section>\n', re.S)
_UPDATED_LINE = re.compile(r'<p class="updated">[^\n]*</p>\n')


def render(spec: dict, names: dict) -> str:
    """spec["cards_first"]：主卡（App Store 直連，Google Play 由 inject_html 補在第一個直連後）移到第一屏的更新日期下方。"""
    source = _G3_RENDER(spec, names)
    if spec.get("updated"):
        # 本頁自己的讀取日期（第 3 組共用 UPDATED 是 2026-10-23，與內文讀取日不符）
        source = source.replace(g3.UPDATED, spec["updated"])
    if not spec.get("cards_first"):
        return source
    block = _APPS_BLOCK.search(source)
    updated = _UPDATED_LINE.search(source)
    if not block or not updated or updated.start() > block.start():
        raise g3.GenerationError(f"{spec['slug']}: cannot move app card to the first screen")
    source = source[:block.start()] + source[block.end():]
    return source[:updated.end()] + block.group(0) + source[updated.end():]


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
    g3.render = render


def main(argv=None) -> int:
    _install()
    return g3.main(argv)


if __name__ == "__main__":
    sys.exit(main())
