#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, privacy-first family travel mission-card generator."""
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

from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "family-travel-mission-card-generator"
APP_KEY = "tripplanet"
APP_ID = "6787193643"
APP_NAME = "Lumi Trip Planet: World Travel"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
TSA_PHOTOS = (
    "https://www.tsa.gov/travel/frequently-asked-questions/"
    "can-i-film-and-take-photos-security-checkpoint"
)
FAA_CHILD_SAFETY = (
    "https://www.faa.gov/travelers/fly_children/child_safety_seat_tips"
)
NHTSA_CHILD_PASSENGER = (
    "https://www.nhtsa.gov/vehicle-safety/car-seats-and-booster-seats"
)
DOT_FAMILY_TRAVEL = (
    "https://www.transportation.gov/resources/individuals/"
    "aviation-consumer-protection/tips-families-and-links-airline-webpages"
)


SCENARIOS = {
    "en": (
        {
            "id": "pre-trip",
            "icon": "🧳",
            "name": "Before leaving",
            "boundary": (
                "Use these cards at home. Adults keep control of travel documents, "
                "medicine, keys and final packing decisions."
            ),
            "targets": (
                "one item that helps everyone stay comfortable",
                "one item in the adult's travel-document check",
                "one object that can be used again instead of thrown away",
                "one quiet activity for a wait",
                "one colour shared by two packed items",
                "one item the adult may need to reach quickly",
                "one way the group can help each other",
            ),
        },
        {
            "id": "airport",
            "icon": "🛫",
            "name": "Airport",
            "boundary": (
                "Stay beside the supervising adult, keep paths and checkpoints clear, "
                "and follow airport and security staff. These cards never ask for photos."
            ),
            "targets": (
                "two different signs visible from your current waiting spot",
                "a vehicle seen through a window",
                "one repeating shape in the building",
                "one colour worn by staff",
                "an object with wheels",
                "one quiet sound and one louder sound",
                "one symbol that helps people find a place",
            ),
        },
        {
            "id": "flight",
            "icon": "✈️",
            "name": "Flight",
            "boundary": (
                "Use only while seated and when the crew permits it. Stop for safety "
                "briefings, instructions, turbulence or whenever the adult says to pause."
            ),
            "targets": (
                "one shape outside the window, if your seat has a view",
                "two different materials near your seat",
                "one quiet sound",
                "one object that folds",
                "one item the crew uses to share information",
                "one cloud shape, if visible",
                "one polite way to help your row",
            ),
        },
        {
            "id": "road-trip",
            "icon": "🚗",
            "name": "Road trip",
            "boundary": (
                "Observe only from a correctly restrained passenger seat. The driver "
                "never reads, answers or operates these cards while driving."
            ),
            "targets": (
                "one colour repeated on two road signs",
                "a bridge, tunnel or overpass",
                "one changing landscape feature",
                "a vehicle carrying something unusual",
                "one safe rest-stop detail",
                "one cloud or weather clue",
                "one landmark the adult points out",
            ),
        },
        {
            "id": "train-ferry",
            "icon": "🚆",
            "name": "Train or ferry",
            "boundary": (
                "Follow the operator and supervising adult. Stay behind marked lines, "
                "use seats or handholds as directed, and never approach an edge for a card."
            ),
            "targets": (
                "one arrival or departure sign",
                "one repeated seat or railing pattern",
                "one sound that signals movement",
                "one object used by staff",
                "one view that changes as you travel",
                "one safe handhold pointed out by the adult",
                "one way passengers make space for each other",
            ),
        },
        {
            "id": "city-walk",
            "icon": "🏙️",
            "name": "City walk",
            "boundary": (
                "Use a card only after the adult chooses a safe place to stop. The adult "
                "handles navigation, crossings, traffic and decisions about where to walk."
            ),
            "targets": (
                "one old building detail",
                "one new building detail",
                "one symbol used for crossing or directions",
                "three colours on one block",
                "one tree, planter or public garden",
                "one detail above eye level",
                "one place where people pause",
            ),
        },
        {
            "id": "museum",
            "icon": "🏛️",
            "name": "Museum",
            "boundary": (
                "Follow the venue's current rules. Do not touch or photograph anything "
                "unless it is clearly permitted, and choose watching or stopping at any time."
            ),
            "targets": (
                "one object with an unexpected texture",
                "one object from another time or place",
                "one tiny detail in a large display",
                "one shape repeated in two works",
                "one question the label may help answer",
                "one object you would protect carefully",
                "one display you can describe without touching",
            ),
        },
        {
            "id": "theme-park",
            "icon": "🎡",
            "name": "Theme park",
            "boundary": (
                "Use only while safely stationary and when the adult permits it. Queue, "
                "ride, height, restraint and staff instructions always take priority."
            ),
            "targets": (
                "one design detail in the waiting area",
                "one map symbol",
                "one object that helps staff communicate",
                "one colour used to guide visitors",
                "one shaded or quiet rest area",
                "one sound that belongs to the theme",
                "one way the group can stay together",
            ),
        },
        {
            "id": "nature-beach",
            "icon": "🌿",
            "name": "Nature or beach",
            "boundary": (
                "Stay where the adult and local rules allow. Observe wildlife from a safe "
                "distance; do not touch, collect or feed anything for a card."
            ),
            "targets": (
                "one pattern made by wind or water",
                "one natural object to observe without taking",
                "one sign of an animal from a safe distance",
                "two shades of one colour",
                "one weather change",
                "one sound you can hear without moving closer",
                "one way to leave the place as you found it",
            ),
        },
        {
            "id": "hotel",
            "icon": "🏨",
            "name": "Hotel",
            "boundary": (
                "Keep room numbers, names and travel details off the cards. Respect other "
                "guests; the adult handles keys, exits and emergency information."
            ),
            "targets": (
                "one sign that helps find a room or exit",
                "one repeating pattern in a shared area",
                "one object that saves water or energy",
                "one quiet way to move through a hallway",
                "one item the group needs before leaving the room",
                "one view from an allowed shared space",
                "one way to leave the room tidy",
            ),
        },
        {
            "id": "restaurant",
            "icon": "🍽️",
            "name": "Restaurant",
            "boundary": (
                "Adults and restaurant staff handle allergies, food safety and movement. "
                "Do not photograph or approach other guests for a card."
            ),
            "targets": (
                "one ingredient named on the menu",
                "one shape repeated in the table setting",
                "one polite phrase the group can use",
                "one colour shared by two foods",
                "one item staff uses to organise service",
                "one sound that signals food preparation",
                "one way to help clear your own space",
            ),
        },
        {
            "id": "quiet-waiting",
            "icon": "🪑",
            "name": "Quiet waiting",
            "boundary": (
                "Observe from the seat or area chosen by the adult. Never approach a "
                "stranger for a card, and skip anything that could disturb the space."
            ),
            "targets": (
                "one object with straight lines",
                "one object with curved lines",
                "three things in the same colour family",
                "one nearby sound and one distant sound",
                "one object that starts with a chosen sound",
                "one detail you did not notice at first",
                "one tiny story about an ordinary object",
            ),
        },
    ),
    "zh-Hant": (
        {
            "id": "pre-trip",
            "icon": "🧳",
            "name": "出發前",
            "boundary": (
                "請在家使用這組卡片。旅行文件、藥物、鑰匙與最後打包決定，"
                "全都由大人保管與確認。"
            ),
            "targets": (
                "一件讓大家旅途中更舒適的物品",
                "一件大人會檢查的旅行文件用品",
                "一件可重複使用而非用完即丟的物品",
                "一種等待時可安靜進行的活動",
                "兩件擁有相同顏色的行李物品",
                "一件大人可能需要快速拿到的物品",
                "一種同行成員可互相幫忙的方法",
            ),
        },
        {
            "id": "airport",
            "icon": "🛫",
            "name": "機場",
            "boundary": (
                "留在陪同大人身旁，不阻擋走道或安檢區，並遵守機場與安檢人員指示。"
                "這組卡片完全沒有拍照任務。"
            ),
            "targets": (
                "從目前等待位置看得到的兩種標誌",
                "一台從窗戶看得到的車輛",
                "建築裡一種重複出現的形狀",
                "工作人員身上的一種顏色",
                "一件有輪子的物品",
                "一個安靜聲音與一個較大的聲音",
                "一個協助旅客找到地點的符號",
            ),
        },
        {
            "id": "flight",
            "icon": "✈️",
            "name": "飛行途中",
            "boundary": (
                "只有在坐好且機組人員允許時才使用。安全說明、任何指示、亂流，"
                "或大人要求暫停時，立即停止活動。"
            ),
            "targets": (
                "座位看得到窗外時，窗外的一種形狀",
                "座位附近兩種不同材質",
                "一個安靜的聲音",
                "一件可以折疊的物品",
                "一件機組人員用來傳達資訊的物品",
                "看得到天空時，一朵雲的形狀",
                "一種可協助同排乘客的禮貌做法",
            ),
        },
        {
            "id": "road-trip",
            "icon": "🚗",
            "name": "公路旅行",
            "boundary": (
                "只能從正確使用安全座椅或安全帶的乘客座位觀察。行車期間，"
                "駕駛絕不閱讀、回答或操作卡片。"
            ),
            "targets": (
                "兩個道路標誌上重複出現的一種顏色",
                "一座橋、隧道或高架道路",
                "一項逐漸改變的地景",
                "一台載著特別物品的車輛",
                "一個安全休息站裡的細節",
                "一個雲朵或天氣線索",
                "一個由大人指出的地標",
            ),
        },
        {
            "id": "train-ferry",
            "icon": "🚆",
            "name": "火車或渡輪",
            "boundary": (
                "遵守運輸業者與陪同大人的指示，留在標線內，依指示使用座位或扶手；"
                "絕不為了卡片靠近月台或船邊。"
            ),
            "targets": (
                "一個抵達或出發標誌",
                "一種重複出現的座椅或欄杆圖案",
                "一個表示移動開始的聲音",
                "一件工作人員使用的物品",
                "一個旅途中逐漸改變的景色",
                "一個由大人指出的安全扶手",
                "一種乘客彼此留出空間的方法",
            ),
        },
        {
            "id": "city-walk",
            "icon": "🏙️",
            "name": "城市散步",
            "boundary": (
                "只有在大人選定安全停留處後才使用卡片。導航、過馬路、車流與行走路線，"
                "全部由大人判斷。"
            ),
            "targets": (
                "一個老建築的細節",
                "一個新建築的細節",
                "一個用於過馬路或指路的符號",
                "同一街區裡的三種顏色",
                "一棵樹、一個花台或一座公共花園",
                "一個高於視線的細節",
                "一個人們會停下來的地方",
            ),
        },
        {
            "id": "museum",
            "icon": "🏛️",
            "name": "博物館",
            "boundary": (
                "遵守場館當下規則。除非明確允許，否則不觸摸、不拍照；"
                "任何時候都可選擇只看或停止。"
            ),
            "targets": (
                "一件材質觸感看起來很特別的物品",
                "一件來自不同年代或地方的物品",
                "一個大型展示裡的微小細節",
                "兩件作品裡重複出現的一種形狀",
                "一個展示說明可能回答的問題",
                "一件你會小心保護的物品",
                "一個不用觸摸就能描述的展示",
            ),
        },
        {
            "id": "theme-park",
            "icon": "🎡",
            "name": "主題樂園",
            "boundary": (
                "只有在安全停留且大人允許時才使用。排隊、設施、身高、安全裝置與"
                "工作人員指示永遠優先。"
            ),
            "targets": (
                "等候區裡的一個設計細節",
                "地圖上的一個符號",
                "一件協助工作人員溝通的物品",
                "一種用來引導遊客的顏色",
                "一個有遮蔭或較安靜的休息區",
                "一個符合主題的聲音",
                "一種讓同行成員保持在一起的方法",
            ),
        },
        {
            "id": "nature-beach",
            "icon": "🌿",
            "name": "自然景點或海邊",
            "boundary": (
                "只停留在大人與當地規則允許的地方，和野生動物保持安全距離；"
                "不為了卡片觸摸、撿走或餵食任何東西。"
            ),
            "targets": (
                "一種由風或水形成的圖案",
                "一件只觀察、不帶走的自然物",
                "一個從安全距離看得到的動物線索",
                "同一種顏色的兩種深淺",
                "一項天氣變化",
                "一個不用靠近也聽得到的聲音",
                "一種讓環境保持原樣的方法",
            ),
        },
        {
            "id": "hotel",
            "icon": "🏨",
            "name": "飯店",
            "boundary": (
                "卡片上不寫房號、姓名或行程資料，並尊重其他旅客。房卡、出口與"
                "緊急資訊都由大人管理。"
            ),
            "targets": (
                "一個協助找到房間或出口的標誌",
                "公共空間裡一種重複出現的圖案",
                "一件節省水或能源的物品",
                "一種安靜通過走廊的方法",
                "一件離開房間前同行成員需要的物品",
                "一個從允許使用的公共空間看得到的景色",
                "一種讓房間保持整齊的方法",
            ),
        },
        {
            "id": "restaurant",
            "icon": "🍽️",
            "name": "餐廳",
            "boundary": (
                "過敏、食品安全與走動方式由大人和餐廳人員處理；"
                "不為了卡片拍攝或靠近其他客人。"
            ),
            "targets": (
                "菜單上寫到的一種食材",
                "餐具擺設裡重複出現的一種形狀",
                "一句同行成員可以使用的禮貌用語",
                "兩種食物共有的一種顏色",
                "一件工作人員用來安排服務的物品",
                "一個和準備餐點有關的聲音",
                "一種協助整理自己座位空間的方法",
            ),
        },
        {
            "id": "quiet-waiting",
            "icon": "🪑",
            "name": "安靜等待",
            "boundary": (
                "只從大人選定的座位或區域觀察，不為了卡片靠近陌生人；"
                "任何可能打擾現場的內容都直接跳過。"
            ),
            "targets": (
                "一件有直線的物品",
                "一件有曲線的物品",
                "三件屬於相近色系的東西",
                "一個近處聲音與一個遠處聲音",
                "一件名稱以指定聲音開頭的物品",
                "一個剛才沒有注意到的細節",
                "一個以普通物品為主角的迷你故事",
            ),
        },
    ),
}


COPY = {
    "en": {
        "title": "Free Printable Family Travel Mission Card Generator",
        "description": (
            "Make private, printable family travel mission cards for 12 settings. "
            "No login, names, photos, location, upload, tracking or saved activity."
        ),
        "eyebrow": "Free bilingual family travel tool",
        "lead": (
            "Choose a travel setting and one of three flexible ways to participate. "
            "The page makes five optional observation prompts plus one blank card."
        ),
        "badges": (
            "12 travel settings",
            "No photos or personal details",
            "No scores or completion tracking",
            "Print from the browser",
        ),
        "start": "Make a card set",
        "language": "繁體中文",
        "tools": "Free tools",
        "home": "Home",
        "boundary_title": "Adult-led safety boundary",
        "boundary_text": (
            "These are stationary observation prompts, not instructions to move, search "
            "or separate from the group. A supervising adult chooses when and where a "
            "card is safe. Local law and current carrier, venue and staff instructions "
            "always override every card."
        ),
        "not_test_title": "Prompts, not a test",
        "not_test_text": (
            "The three participation styles are choices, not ages, levels or ability "
            "rankings. A child may watch, point, describe, imagine, switch styles or skip "
            "every card. The tool makes no promise about behaviour, mood, learning or "
            "travel quality."
        ),
        "generator": "Build today's travel cards",
        "generator_intro": (
            "Nothing is submitted. Your selection and generated set exist only in this "
            "open page and disappear when it closes."
        ),
        "choose_scene": "1. Choose a setting",
        "choose_style": "2. Choose a participation style",
        "styles": (
            {
                "id": "watch",
                "name": "Watch or point",
                "detail": "Notice from the safe place chosen by the adult.",
                "template": (
                    "From your current spot, notice {target}. Point only when the setting "
                    "permits and your supervising adult has said it is safe; never ask a "
                    "driver to look."
                ),
            },
            {
                "id": "describe",
                "name": "Notice or describe",
                "detail": "Notice one colour, shape, sound or detail.",
                "template": (
                    "Notice {target}. Think of one colour, shape, sound or detail. Share "
                    "only with a non-driving companion when the setting permits."
                ),
            },
            {
                "id": "create",
                "name": "Plan or create",
                "detail": "Turn an observation into a question or tiny story.",
                "template": (
                    "Use {target} as a prompt. Invent one kind question, route idea or "
                    "tiny story alone or with a non-driving companion when permitted."
                ),
            },
        ),
        "make": "Make 6 cards",
        "new_set": "Try another set",
        "print": "Print current cards",
        "print_heading": "Current printable set",
        "print_boundary": (
            "Safety first: use only from the place approved by the supervising adult. "
            "Current local, carrier, crew, driver, security, venue and staff instructions "
            "always override a card."
        ),
        "mission": "Optional card",
        "skip": "Skip any card",
        "blank": "Make your own",
        "blank_text": "Adult-approved prompt:",
        "privacy": "What this page never collects",
        "privacy_text": (
            "There is no name, age, room number, route, destination, location, photo, "
            "video, audio, itinerary, completion record, form, account or upload. The "
            "page uses no persistent browser storage, saved child profile or analytics request."
        ),
        "photo_title": "Why there are no photo missions",
        "photo_text": (
            "Rules differ by country and place. U.S. TSA guidance, for example, says "
            "checkpoint photography must not interfere with screening and may not capture "
            "certain sensitive information. This independent tool takes a simpler, more "
            "portable boundary: none of its cards asks anyone to take a photo."
        ),
        "sources": "Official safety references",
        "sources_intro": (
            "These links help define conservative boundaries; they do not endorse this "
            "tool. Check the current rule for the exact country, carrier, vehicle and venue."
        ),
        "source_items": (
            ("TSA: filming and photos at a security checkpoint", TSA_PHOTOS),
            ("FAA: flying with children and child safety seats", FAA_CHILD_SAFETY),
            ("NHTSA: car seats and booster seats", NHTSA_CHILD_PASSENGER),
            ("U.S. DOT: tips for families travelling by air", DOT_FAMILY_TRAVEL),
        ),
        "license_title": "Reuse the original cards",
        "license_text": (
            "The original wording and blank card layout are available under CC BY 4.0. "
            "The license does not cover external sources, logos, venue content or third-"
            "party rules."
        ),
        "app_title": "Optional reusable digital layer",
        "app_text": (
            "Lumi Trip Planet lets a parent create reusable travel missions, choose a "
            "target count and set an optional family reward. Check the current App Store "
            "listing for availability and exact features; the free cards above work "
            "without the app."
        ),
        "app_cta": "View Lumi Trip Planet on the App Store",
        "faq": "Questions families ask",
        "faq_items": (
            (
                "Do I need the app to use these cards?",
                "No. Choose a setting and style, print the six cards and use them independently.",
            ),
            (
                "Does the generator save a child's activity?",
                "No. It has no account, form, upload, completion log or browser storage.",
            ),
            (
                "Are the three styles age or ability levels?",
                "No. They are flexible participation choices, and anyone may switch or skip.",
            ),
            (
                "Can a card override an airline, venue or adult instruction?",
                "No. Current local rules and adult, crew, driver, security and venue instructions always come first.",
            ),
            (
                "Why are there no photo challenges?",
                "Photography and privacy rules vary. Observation-only prompts are easier to use conservatively across places.",
            ),
            (
                "Do children need a score or reward?",
                "No. The cards are optional conversation prompts, not a test or completion system.",
            ),
        ),
        "howto": (
            ("Choose a setting", "Pick the current travel setting without entering a destination or location."),
            ("Choose a style", "Select watch or point, notice or describe, or plan or create."),
            ("Make the set", "Generate five observation prompts and one blank adult-approved card."),
            ("Apply the safety boundary", "The supervising adult checks every card against the current place and instructions."),
            ("Print or use on screen", "Use the current set without an account, upload or saved completion record."),
        ),
        "footer": "A free privacy-first resource from iOS App Guide.",
        "status": "A new card set is ready.",
    },
    "zh-Hant": {
        "title": "免費親子旅行任務卡產生器",
        "description": (
            "為 12 種旅行情境製作英繁雙語親子任務卡。免登入，不收姓名、照片、"
            "位置、上傳資料或完成紀錄，可直接列印。"
        ),
        "eyebrow": "免費英繁雙語親子旅行工具",
        "lead": (
            "先選旅行情境，再選三種彈性參與方式之一；網頁會產生五張選用觀察提示，"
            "再附一張空白卡。"
        ),
        "badges": (
            "12 種旅行情境",
            "不拍照、不填個資",
            "不評分、不追蹤完成度",
            "直接從瀏覽器列印",
        ),
        "start": "開始製作任務卡",
        "language": "English",
        "tools": "免費工具",
        "home": "首頁",
        "boundary_title": "由大人主導的安全界線",
        "boundary_text": (
            "這些是原地觀察提示，不是要求孩子移動、搜尋或離開同行成員的指示。"
            "陪同大人決定何時、何地適合使用；當地法規與當下的運輸業者、場館、"
            "工作人員指示永遠優先。"
        ),
        "not_test_title": "只是提示，不是測驗",
        "not_test_text": (
            "三種參與方式不是年齡、程度或能力排名。孩子可以看、指、描述、想像、"
            "隨時換方式，或跳過所有卡片；工具不承諾改善行為、情緒、學習或旅行品質。"
        ),
        "generator": "製作今天的旅行任務卡",
        "generator_intro": (
            "所有內容都不會送出。選擇與產生的卡片只存在目前開啟的頁面，"
            "關閉後就消失。"
        ),
        "choose_scene": "1. 選擇情境",
        "choose_style": "2. 選擇參與方式",
        "styles": (
            {
                "id": "watch",
                "name": "看一看／指出來",
                "detail": "只從大人選定的安全位置觀察。",
                "template": "從目前位置觀察「{target}」。只有在情境允許且陪同大人已確認安全時，才從原地指出來；絕不要求駕駛查看。",
            },
            {
                "id": "describe",
                "name": "觀察／描述",
                "detail": "留意一個顏色、形狀、聲音或細節。",
                "template": "觀察「{target}」，想一個顏色、形狀、聲音或細節；只有在情境允許且有非駕駛同行者時才分享。",
            },
            {
                "id": "create",
                "name": "規劃／創作",
                "detail": "把觀察變成問題或迷你故事。",
                "template": "以「{target}」為提示，自己想一個友善問題、小路線或迷你故事；情境允許時也可和非駕駛同行者一起想。",
            },
        ),
        "make": "產生 6 張卡片",
        "new_set": "換一組卡片",
        "print": "列印目前卡片",
        "print_heading": "目前可列印任務卡",
        "print_boundary": (
            "安全優先：只在陪同大人事先核准的位置使用。當下的當地規則與運輸業者、"
            "機組、駕駛、安檢、場館及工作人員指示永遠凌駕卡片。"
        ),
        "mission": "選用任務卡",
        "skip": "任何一張都可跳過",
        "blank": "自己設計",
        "blank_text": "由大人核准的提示：",
        "privacy": "這個網頁絕不收集什麼",
        "privacy_text": (
            "沒有姓名、年齡、房號、路線、目的地、位置、照片、影片、聲音、行程、"
            "完成紀錄、表單、帳號或上傳；也不使用持續性瀏覽器儲存、儲存孩子檔案，"
            "或發送分析請求。"
        ),
        "photo_title": "為什麼完全沒有拍照任務",
        "photo_text": (
            "各國與各場所規則不同。以美國 TSA 為例，官方說明指出，安檢區拍攝"
            "不得干擾安檢，也不可拍到特定敏感資訊。這個獨立工具採用更簡單、"
            "跨地點更保守的界線：所有卡片都不要求任何人拍照。"
        ),
        "sources": "官方安全參考",
        "sources_intro": (
            "這些連結只用來建立保守界線，不代表官方為本工具背書。請依實際國家、"
            "運輸業者、車輛與場館確認當下規則。"
        ),
        "source_items": (
            ("TSA：在安檢區錄影與拍照", TSA_PHOTOS),
            ("FAA：兒童搭機與兒童安全座椅", FAA_CHILD_SAFETY),
            ("NHTSA：汽車安全座椅與增高座椅", NHTSA_CHILD_PASSENGER),
            ("美國交通部：家庭航空旅行提示", DOT_FAMILY_TRAVEL),
        ),
        "license_title": "重複利用原創卡片",
        "license_text": (
            "原創文字與空白卡版型採 CC BY 4.0 授權；授權不包含外部來源、商標、"
            "場館內容或第三方規則。"
        ),
        "app_title": "選用的可重複數位層",
        "app_text": (
            "Lumi Trip Planet 讓家長建立可重複使用的旅行任務、選擇目標數量，"
            "並設定選用家庭獎勵。請以目前 App Store 頁面確認供應地區與確切功能；"
            "上方免費卡片不需要 App 也能完整使用。"
        ),
        "app_cta": "在 App Store 查看 Lumi Trip Planet",
        "faq": "家庭常見問題",
        "faq_items": (
            (
                "一定要安裝 App 才能使用卡片嗎？",
                "不用。選好情境與方式，直接列印六張卡片，就能獨立使用。",
            ),
            (
                "產生器會儲存孩子的活動嗎？",
                "不會。沒有帳號、表單、上傳、完成紀錄或瀏覽器儲存。",
            ),
            (
                "三種方式是年齡或能力分級嗎？",
                "不是。它們只是彈性參與選擇，任何人都能更換或跳過。",
            ),
            (
                "卡片可以凌駕航空公司、場館或大人的指示嗎？",
                "不可以。當地規則與大人、機組、駕駛、安檢及場館人員指示永遠優先。",
            ),
            (
                "為什麼沒有拍照挑戰？",
                "拍攝與隱私規則因地而異；只觀察的提示更適合跨地點保守使用。",
            ),
            (
                "孩子需要分數或獎勵嗎？",
                "不需要。卡片是選用對話提示，不是測驗或完成系統。",
            ),
        ),
        "howto": (
            ("選擇情境", "選目前旅行情境，不輸入目的地或位置。"),
            ("選擇參與方式", "選看一看／指出來、觀察／描述，或規劃／創作。"),
            ("產生卡片", "產生五張觀察提示與一張由大人核准的空白卡。"),
            ("套用安全界線", "陪同大人依目前場所與指示檢查每一張卡。"),
            ("列印或直接使用", "免帳號、免上傳、無完成紀錄，直接使用目前卡片。"),
        ),
        "footer": "iOS App Guide 提供的免費隱私優先資源。",
        "status": "新的卡片組已準備完成。",
    },
}


STYLE = r"""
:root{--ink:#18213b;--muted:#5f677b;--paper:#fffdf8;--panel:#ffffff;
--line:#e5e7ee;--navy:#17213b;--violet:#6858d9;--coral:#f47c67;
--mint:#dff4e9;--gold:#ffe2a7;--shadow:0 24px 70px rgba(31,35,65,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:linear-gradient(180deg,#f4f0ff 0,#fff9ed 35rem,#fffdf8 100%);
color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.65}
a{color:#5144b8}.wrap{width:min(1120px,calc(100% - 32px));margin:auto}
.top{background:rgba(23,33,59,.97);color:white;position:sticky;top:0;z-index:20;
box-shadow:0 8px 24px rgba(18,23,45,.14)}.nav{min-height:64px;display:flex;align-items:center;
justify-content:space-between;gap:20px}.nav a{color:white;text-decoration:none;font-weight:760;white-space:nowrap}
.links{display:flex;gap:18px;overflow-x:auto}.hero{padding:76px 0 42px;text-align:center}
.eyebrow{display:inline-flex;padding:8px 14px;border:1px solid rgba(104,88,217,.23);
border-radius:999px;background:rgba(255,255,255,.68);font-weight:800;color:#5144b8;
letter-spacing:.03em;white-space:nowrap}.hero h1{font-family:Georgia,serif;font-size:clamp(2.35rem,7vw,5rem);
line-height:1.02;letter-spacing:-.045em;margin:24px auto 20px;max-width:960px}
.lead{font-size:clamp(1.04rem,2.3vw,1.28rem);color:var(--muted);max-width:780px;margin:0 auto}
.badges,.actions{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-top:24px}
.badge{background:white;border:1px solid var(--line);box-shadow:0 8px 24px rgba(31,35,65,.06);
padding:8px 13px;border-radius:999px;font-size:.92rem;font-weight:720;white-space:nowrap}
.button{appearance:none;border:0;border-radius:14px;background:var(--violet);color:white!important;
font:inherit;font-weight:820;padding:13px 19px;text-decoration:none;cursor:pointer;
box-shadow:0 10px 25px rgba(104,88,217,.22);white-space:nowrap}
.button:hover{transform:translateY(-1px)}.button.secondary{background:white;color:var(--ink)!important;
border:1px solid var(--line);box-shadow:none}.card{background:var(--panel);border:1px solid var(--line);
border-radius:24px;padding:clamp(22px,4vw,38px);box-shadow:var(--shadow)}
.boundaries{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:12px 0 42px}
.boundaries .card:first-child{border-top:6px solid var(--coral)}
.boundaries .card:last-child{border-top:6px solid var(--violet)}
h2{font-family:Georgia,serif;font-size:clamp(1.55rem,3vw,2.35rem);line-height:1.16;margin:0 0 12px}
h3{line-height:1.25}.generator{padding:0 0 48px}.generator-shell{overflow:hidden;padding:0}
.generator-head{padding:clamp(24px,5vw,44px);background:linear-gradient(135deg,var(--navy),#303b67);
color:white}.generator-head p{color:#e8e9f5;max-width:760px;margin-bottom:0}
.controls{padding:clamp(22px,4vw,38px)}.control-block+.control-block{margin-top:30px}
.control-label{font-weight:880;font-size:1.05rem;margin-bottom:12px}.choices{display:flex;flex-wrap:wrap;gap:9px}
.choice{appearance:none;border:1px solid var(--line);border-radius:13px;background:#fbfbfd;
color:var(--ink);font:inherit;font-weight:760;padding:11px 14px;cursor:pointer;white-space:nowrap}
.choice:hover,.choice:focus-visible{border-color:var(--violet)}
.choice[aria-pressed="true"]{background:var(--violet);border-color:var(--violet);color:white;
box-shadow:0 8px 22px rgba(104,88,217,.2)}
.styles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.style-choice{text-align:left;
white-space:normal}.style-choice strong{display:block;white-space:nowrap}.style-choice small{display:block;
margin-top:5px;line-height:1.35;color:var(--muted)}.style-choice[aria-pressed="true"] small{color:#efefff}
.control-actions{justify-content:flex-start}.safety-note{margin:28px 0 0;padding:16px 18px;
border-left:5px solid var(--coral);background:#fff6f3;border-radius:0 14px 14px 0}
.preview{padding:clamp(24px,5vw,44px);background:#f8f7fc;border-top:1px solid var(--line)}
.preview-head{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:18px}
.preview-head p{margin:5px 0 0;color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.print-boundary{margin:0 0 18px;padding:14px 16px;border:1px solid #f0c9bf;
border-radius:14px;background:#fff6f3;font-size:.92rem;font-weight:720}
.mission-card{min-height:210px;background:var(--paper);border:1px solid #ddd7ca;border-radius:18px;
padding:20px;display:flex;flex-direction:column;position:relative;overflow:hidden}
.mission-card:before{content:"";position:absolute;inset:0 0 auto 0;height:7px;background:linear-gradient(90deg,var(--violet),var(--coral))}
.card-kicker{font-size:.77rem;text-transform:uppercase;letter-spacing:.08em;font-weight:900;
color:#6a607d;margin-top:5px}.mission-card h3{font-size:1.12rem;margin:15px 0 8px}
.mission-card p{margin:0}.skip{margin-top:auto;padding-top:18px;color:var(--muted);font-size:.84rem;font-weight:720}
.blank-lines{display:block;border-bottom:1px solid #bbb3a5;height:34px;margin-top:8px}
.status{min-height:1.6em;color:#4f4874;font-weight:720;margin-top:12px}.details{display:grid;
grid-template-columns:1fr 1fr;gap:18px;padding-bottom:42px}.details .wide{grid-column:1/-1}
.source-list{padding-left:20px}.source-list li+li{margin-top:8px}.app-card{background:linear-gradient(135deg,#201f42,#38376c);
color:white;border-color:#38376c}.app-card p{color:#e5e4f2}.app-card .button{background:var(--gold);color:#28223c!important}
.faq{padding-bottom:56px}.faq-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}
.faq-item{background:white;border:1px solid var(--line);border-radius:18px;padding:20px}
.faq-item h3{font-size:1rem;margin:0 0 7px}.faq-item p{color:var(--muted);margin:0}
.footer{background:var(--navy);color:#dfe3f2;text-align:center;padding:28px 0}
button:focus-visible,a:focus-visible{outline:3px solid #ffb685;outline-offset:3px}
@media(max-width:820px){.boundaries,.details,.faq-grid{grid-template-columns:1fr}
.details .wide{grid-column:auto}.styles{grid-template-columns:1fr}.cards{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.wrap{width:min(100% - 22px,1120px)}.hero{padding-top:52px}
.nav{min-height:58px}.links{gap:12px}.cards{grid-template-columns:1fr}.preview-head{align-items:flex-start;
flex-direction:column}.badges{justify-content:flex-start}.hero .badges,.hero .actions{justify-content:center}
.choices{flex-wrap:nowrap;overflow-x:auto;padding-bottom:7px}.choice{flex:0 0 auto}
.control-actions{flex-wrap:wrap;overflow:visible}.control-actions .button{flex:1 1 auto}}
@media print{body{background:white}.top,.hero,.boundaries,.generator-head,.controls,.details,.faq,.footer{display:none!important}
.wrap{width:100%}.generator{padding:0}.generator-shell,.preview{border:0;box-shadow:none;padding:0;background:white}
.preview-head .actions,.status{display:none}.preview-head{margin-bottom:12px}.cards{grid-template-columns:1fr 1fr;gap:10px}
.mission-card{break-inside:avoid;min-height:210px;box-shadow:none}@page{margin:12mm}}
"""


SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("mission-config").textContent);
  const sceneButtons = [...document.querySelectorAll("[data-scene]")];
  const styleButtons = [...document.querySelectorAll("[data-style]")];
  const cards = document.getElementById("mission-cards");
  const boundary = document.getElementById("scene-boundary");
  const printBoundary = document.getElementById("print-boundary");
  const status = document.getElementById("mission-status");
  let sceneId = config.scenarios[0].id;
  let styleId = config.styles[0].id;
  let offset = 0;

  function selected(items, id) {
    return items.find((item) => item.id === id);
  }

  function cardMarkup(label, title, text, number, blank = false) {
    const line = blank ? '<span class="blank-lines"></span><span class="blank-lines"></span>' : "";
    return `<article class="mission-card"><div class="card-kicker">${label} ${number}</div>` +
      `<h3>${title}</h3><p>${text}</p>${line}<div class="skip">${config.skip}</div></article>`;
  }

  function render() {
    const scene = selected(config.scenarios, sceneId);
    const style = selected(config.styles, styleId);
    const prompts = Array.from({length: 5}, (_, index) =>
      scene.targets[(offset + index) % scene.targets.length]);
    cards.innerHTML = prompts.map((target, index) =>
      cardMarkup(config.mission, `${scene.icon} ${scene.name}`,
        style.template.replace("{target}", target), index + 1)).join("") +
      cardMarkup(config.mission, config.blank, config.blankText, 6, true);
    boundary.textContent = scene.boundary;
    printBoundary.textContent = `${config.printBoundary} ${scene.boundary}`;
  }

  sceneButtons.forEach((button) => button.addEventListener("click", () => {
    sceneId = button.dataset.scene;
    offset = 0;
    sceneButtons.forEach((item) =>
      item.setAttribute("aria-pressed", String(item === button)));
    render();
  }));

  styleButtons.forEach((button) => button.addEventListener("click", () => {
    styleId = button.dataset.style;
    styleButtons.forEach((item) =>
      item.setAttribute("aria-pressed", String(item === button)));
    render();
  }));

  document.getElementById("make-cards").addEventListener("click", () => {
    offset = 0;
    render();
    document.getElementById("printable-set").scrollIntoView({behavior: "smooth"});
  });
  document.getElementById("new-cards").addEventListener("click", () => {
    const scene = selected(config.scenarios, sceneId);
    offset = (offset + 2) % scene.targets.length;
    render();
    status.textContent = config.status;
  });
  document.getElementById("print-cards").addEventListener("click", () => window.print());
  render();
})();
"""


def canonical(locale: str) -> str:
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def render_page(locale: str, app_public: bool = False) -> str:
    t = COPY[locale]
    other_locale = "zh-Hant" if locale == "en" else "en"
    url = canonical(locale)
    alternate = canonical(other_locale)
    home = f"{SITE}/{'zh-Hant/' if locale == 'zh-Hant' else ''}index.html"
    badges = "".join(
        f'<span class="badge">✓ {html.escape(item)}</span>' for item in t["badges"]
    )
    scene_buttons = "".join(
        f'<button type="button" class="choice" data-scene="{scene["id"]}" '
        f'aria-pressed="{"true" if index == 0 else "false"}">'
        f'{scene["icon"]} {html.escape(scene["name"])}</button>'
        for index, scene in enumerate(SCENARIOS[locale])
    )
    style_buttons = "".join(
        f'<button type="button" class="choice style-choice" data-style="{style["id"]}" '
        f'aria-pressed="{"true" if index == 0 else "false"}"><strong>'
        f'{html.escape(style["name"])}</strong><small>{html.escape(style["detail"])}</small>'
        "</button>"
        for index, style in enumerate(t["styles"])
    )
    sources = "".join(
        f'<li><a href="{html.escape(source_url)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source_url in t["source_items"]
    )
    faq = "".join(
        f'<article class="faq-item"><h3>{html.escape(question)}</h3>'
        f"<p>{html.escape(answer)}</p></article>"
        for question, answer in t["faq_items"]
    )
    config = {
        "scenarios": SCENARIOS[locale],
        "styles": t["styles"],
        "mission": t["mission"],
        "skip": t["skip"],
        "blank": t["blank"],
        "blankText": t["blank_text"],
        "printBoundary": t["print_boundary"],
        "status": t["status"],
    }
    config_json = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")

    schemas = [
        {
            "@context": "https://schema.org",
            "@type": ["WebApplication", "LearningResource"],
            "name": t["title"],
            "description": t["description"],
            "url": url,
            "inLanguage": locale,
            "applicationCategory": "TravelApplication",
            "operatingSystem": "Any",
            "isAccessibleForFree": True,
            "learningResourceType": "Printable family travel prompt cards",
            "license": LICENSE,
            "citation": [
                TSA_PHOTOS,
                FAA_CHILD_SAFETY,
                NHTSA_CHILD_PASSENGER,
                DOT_FAMILY_TRAVEL,
            ],
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
                    "name": name,
                    "text": text,
                }
                for index, (name, text) in enumerate(t["howto"], 1)
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
    app_section = ""
    if app_public:
        tracked_app_url = appstore_url(APP_KEY, f"iag_travel_cards_{locale.lower()}")
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "url": tracked_app_url,
                "operatingSystem": "iOS",
                "applicationCategory": "TravelApplication",
                "description": t["app_text"],
            }
        )
        app_section = (
            '<article class="card app-card"><h2>'
            f'{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></article>'
        )
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
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#generator">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div></section>
<section class="wrap boundaries"><article class="card"><h2>{html.escape(t["boundary_title"])}</h2><p>{html.escape(t["boundary_text"])}</p></article><article class="card"><h2>{html.escape(t["not_test_title"])}</h2><p>{html.escape(t["not_test_text"])}</p></article></section>
<section class="wrap generator" id="generator"><article class="card generator-shell"><div class="generator-head"><h2>{html.escape(t["generator"])}</h2><p>{html.escape(t["generator_intro"])}</p></div><div class="controls"><div class="control-block"><div class="control-label">{html.escape(t["choose_scene"])}</div><div class="choices" role="group" aria-label="{html.escape(t["choose_scene"])}">{scene_buttons}</div></div><div class="control-block"><div class="control-label">{html.escape(t["choose_style"])}</div><div class="styles" role="group" aria-label="{html.escape(t["choose_style"])}">{style_buttons}</div></div><p class="safety-note" id="scene-boundary">{html.escape(SCENARIOS[locale][0]["boundary"])}</p><div class="actions control-actions"><button class="button" id="make-cards" type="button">{html.escape(t["make"])}</button><button class="button secondary" id="new-cards" type="button">{html.escape(t["new_set"])}</button></div></div><div class="preview" id="printable-set"><div class="preview-head"><div><h2>{html.escape(t["print_heading"])}</h2></div><div class="actions"><button class="button secondary" id="print-cards" type="button">{html.escape(t["print"])}</button></div></div><p class="print-boundary" id="print-boundary">{html.escape(t["print_boundary"])} {html.escape(SCENARIOS[locale][0]["boundary"])}</p><div class="cards" id="mission-cards"></div><div class="status" id="mission-status" aria-live="polite"></div></div></article></section>
<section class="wrap details"><article class="card"><h2>{html.escape(t["privacy"])}</h2><p>{html.escape(t["privacy_text"])}</p></article><article class="card"><h2>{html.escape(t["photo_title"])}</h2><p>{html.escape(t["photo_text"])}</p></article><article class="card wide"><h2>{html.escape(t["sources"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{sources}</ul></article><article class="card"><h2>{html.escape(t["license_title"])}</h2><p>{html.escape(t["license_text"])}</p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></article>{app_section}</section>
<section class="wrap faq"><h2>{html.escape(t["faq"])}</h2><div class="faq-grid">{faq}</div></section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="mission-config">{config_json}</script>
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
        f'<a href="{target}">Family Travel Mission Card Generator</a></h2>'
        "<p>Private printable prompts for 12 travel settings.</p>"
        "</article>"
    )
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(target)
        + r'">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
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


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    if app_public is None:
        app_public = APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale == "zh-Hant":
            relative = Path(locale) / relative
        target = pages / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(locale, app_public), encoding="utf-8")
        outputs.append(canonical(locale))
    update_tools_index(pages)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"family travel mission cards -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
