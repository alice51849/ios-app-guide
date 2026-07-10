#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a bilingual, print-ready Zhuyin video-call kit for grandparents."""
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
SLUG = "zhuyin-grandparent-video-call-kit"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
VIDEO_STUDY = "https://pmc.ncbi.nlm.nih.gov/articles/PMC9539353/"
MOE_HANDBOOK = (
    "https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/index.html"
)
MOE_PRACTICE = "https://stroke-order.learningweb.moe.edu.tw/phoneticWrite.jsp?la=0"
NHLRC = "https://nhlrc.ucla.edu/nhlrc"

WORDS = (
    {
        "symbol": "ㄅ",
        "word": "爸爸",
        "zhuyin": "ㄅㄚˋ　˙ㄅㄚ",
        "en": "Point to Dad or a photo. Say ㄅ once, then say 爸爸 naturally.",
        "zh-Hant": "指向爸爸或照片；先念一次 ㄅ，再自然地說「爸爸」。",
    },
    {
        "symbol": "ㄇ",
        "word": "媽媽",
        "zhuyin": "ㄇㄚ　˙ㄇㄚ",
        "en": "Point to Mom or a photo. Say ㄇ once, then say 媽媽 naturally.",
        "zh-Hant": "指向媽媽或照片；先念一次 ㄇ，再自然地說「媽媽」。",
    },
    {
        "symbol": "ㄈ",
        "word": "飯",
        "zhuyin": "ㄈㄢˋ",
        "en": "Show today's meal or pretend to eat, then stretch the first sound gently.",
        "zh-Hant": "拿今天的飯菜入鏡，或做吃飯動作，再輕輕拉長第一個音。",
    },
    {
        "symbol": "ㄉ",
        "word": "弟弟",
        "zhuyin": "ㄉㄧˋ　˙ㄉㄧ",
        "en": "Use a family photo or toy figure; let the child say the whole word after ㄉ.",
        "zh-Hant": "拿家人照片或玩偶入鏡；念完 ㄉ，讓孩子接著說完整詞語。",
    },
    {
        "symbol": "ㄋ",
        "word": "奶奶",
        "zhuyin": "ㄋㄞˇ　˙ㄋㄞ",
        "en": "Wave at Grandma, say ㄋ, and let the child finish the familiar word.",
        "zh-Hant": "向奶奶揮手，先念 ㄋ，再讓孩子接完熟悉的詞語。",
    },
    {
        "symbol": "ㄌ",
        "word": "來",
        "zhuyin": "ㄌㄞˊ",
        "en": "Beckon with one hand while saying 來; ask the child to copy the action.",
        "zh-Hant": "邊說「來」邊招手，請孩子模仿動作，不要求立刻答對。",
    },
    {
        "symbol": "ㄍ",
        "word": "狗",
        "zhuyin": "ㄍㄡˇ",
        "en": "Show a toy, pet or picture of a dog and invite one playful bark.",
        "zh-Hant": "拿玩具狗、寵物或照片入鏡，再一起學一聲狗叫。",
    },
    {
        "symbol": "ㄎ",
        "word": "看",
        "zhuyin": "ㄎㄢˋ",
        "en": "Make binoculars with your hands, say 看, then find one object on camera.",
        "zh-Hant": "雙手做望遠鏡，說「看」，再一起找鏡頭裡的一樣東西。",
    },
    {
        "symbol": "ㄏ",
        "word": "花",
        "zhuyin": "ㄏㄨㄚ",
        "en": "Show a flower, plant or drawing and notice the breathy first sound.",
        "zh-Hant": "拿花、植物或畫作入鏡，一起感受第一個送氣的聲音。",
    },
    {
        "symbol": "ㄐ",
        "word": "家",
        "zhuyin": "ㄐㄧㄚ",
        "en": "Point around the room and say 家; let the child show their home too.",
        "zh-Hant": "指一指房間並說「家」，再讓孩子帶阿公阿嬤看看自己的家。",
    },
    {
        "symbol": "ㄑ",
        "word": "去",
        "zhuyin": "ㄑㄩˋ",
        "en": "Point away from the screen and use 去 in a tiny family sentence.",
        "zh-Hant": "指向遠處，用「去」說一個很短的家庭句子。",
    },
    {
        "symbol": "ㄒ",
        "word": "小",
        "zhuyin": "ㄒㄧㄠˇ",
        "en": "Hold up the smallest nearby object and let the child find another one.",
        "zh-Hant": "拿起身邊最小的物品，再請孩子找一個小東西。",
    },
    {
        "symbol": "ㄔ",
        "word": "吃",
        "zhuyin": "ㄔ",
        "en": "Pretend to take one bite; repeat the child's attempt correctly without grading it.",
        "zh-Hant": "做吃一口的動作；孩子念完後自然重述正確讀音，不打分數。",
    },
    {
        "symbol": "ㄕ",
        "word": "水",
        "zhuyin": "ㄕㄨㄟˇ",
        "en": "Hold up a cup of water and let the child show theirs on camera.",
        "zh-Hant": "拿一杯水入鏡，也請孩子把自己的水拿給阿公阿嬤看。",
    },
    {
        "symbol": "ㄗ",
        "word": "早",
        "zhuyin": "ㄗㄠˇ",
        "en": "Wave and say 早安; use it as the opening card on a morning call.",
        "zh-Hant": "揮手說「早安」；早上視訊時可把這張當開場卡。",
    },
    {
        "symbol": "ㄚ",
        "word": "阿嬤",
        "zhuyin": "ㄚ　ㄇㄚˋ",
        "en": "Grandma points to herself, says ㄚ, and pauses for the child to finish.",
        "zh-Hant": "阿嬤指自己，先說 ㄚ，停一下讓孩子接完「阿嬤」。",
    },
)

COPY = {
    "en": {
        "lang": "en",
        "title": "Free 10-Minute Zhuyin Video-Call Kit for Grandparents",
        "description": (
            "A free bilingual, print-ready Bopomofo video-call routine for grandparents "
            "and children: three family words, camera games, tone gestures and gentle prompts."
        ),
        "eyebrow": "Free family kit · no login",
        "lead": (
            "Turn one ordinary family call into ten minutes of warm, responsive Zhuyin "
            "practice—without making grandparents teach a formal lesson."
        ),
        "badges": ("10-minute routine", "Print or use on screen", "No child data uploaded or saved"),
        "start": "Build today’s call plan",
        "language": "繁體中文",
        "setup": "Two-device setup",
        "setup_items": (
            ("1. Parent", "Open this page beside the child and keep three ordinary household objects nearby."),
            ("2. Grandparent", "Open the same page—or print the call script—and follow the five short turns."),
            ("3. Everyone", "Use familiar words and real conversation. Stop while the child still wants more."),
        ),
        "kit_title": "Today’s three-word call plan",
        "kit_intro": (
            "Use these as conversation starters, not flashcard scores. If a word is unfamiliar, "
            "tap “New plan” before the call."
        ),
        "new_plan": "New 3-word plan",
        "print": "Print this kit",
        "share": "Share tool",
        "shared": "Tool link copied.",
        "share_title": "Free Zhuyin grandparent video-call kit",
        "timeline": "The 10-minute routine",
        "timeline_items": (
            ("0–1 min", "Warm hello", "Say the child’s name, smile and show one familiar object. No quiz yet."),
            ("1–3 min", "Child chooses", "Let the child point to one of today’s three symbols or family words."),
            ("3–5 min", "Sound mirror", "Grandparent models once; child may echo, point or make the matching action."),
            ("5–8 min", "Camera treasure hunt", "Find a real object, person or gesture connected to the word."),
            ("8–9 min", "Tone elevator", "Move one hand with the pitch while saying one familiar syllable."),
            ("9–10 min", "Family sentence", "Use the word in one real sentence, then let the child pick next call’s card."),
        ),
        "grandparent": "Grandparent’s gentle script",
        "grandparent_items": (
            "“今天想玩哪一張？”— offer a choice instead of testing.",
            "“我先念一次，你可以跟我念、用手指，或做動作。”",
            "If the sound is different, repeat the word naturally: “對，是水，ㄕㄨㄟˇ。”",
            "End with one specific success: “你今天找到水，也記得 ㄕ。”",
        ),
        "parent": "Nearby parent’s job",
        "parent_items": (
            "Keep the device steady and help both sides look at the same object.",
            "Wait a few seconds before answering for the child.",
            "Translate only when needed; protect the back-and-forth rhythm.",
            "Stop or switch to normal conversation if the child looks tired or frustrated.",
        ),
        "tones": "Tone elevator",
        "tone_note": (
            "Use one hand to trace the pitch while saying a familiar syllable. The gestures "
            "are an independent teaching aid; official tone-mark placement comes from Taiwan’s MOE reference."
        ),
        "tone_items": (
            ("ㄇㄚ", "First tone", "→ level"),
            ("ㄇㄚˊ", "Second tone", "↗ rising"),
            ("ㄇㄚˇ", "Third tone", "∨ dip then rise"),
            ("ㄇㄚˋ", "Fourth tone", "↘ falling"),
            ("˙ㄇㄚ", "Neutral tone", "· short and light"),
        ),
        "shy": "If the child is shy",
        "shy_text": (
            "Pointing, finding an object, waving or making a hand motion all count as a turn. "
            "Do not demand repetition. Grandparent sensitivity and real-time response matter "
            "more than completing every card."
        ),
        "evidence": "What the research supports—and what it does not",
        "evidence_text": (
            "A longitudinal study of 48 families found that grandparent sensitivity predicted "
            "infants’ positive affect during both video and in-person interactions. The paper "
            "also summarizes evidence that live social contingency and a nearby adult’s "
            "scaffolding support young children’s engagement. The sample was mostly highly "
            "educated White/Caucasian families during COVID-19, and the study did not test "
            "Zhuyin learning or this kit. We use it only to inform short turns, responsive "
            "prompts and parent support—not to claim faster learning."
        ),
        "sources": "Research and official references",
        "source_items": (
            ("Presence at a distance: intergenerational video-chat study", VIDEO_STUDY),
            ("Taiwan Ministry of Education Bopomofo Handbook", MOE_HANDBOOK),
            ("Taiwan Ministry of Education Zhuyin Practice Book", MOE_PRACTICE),
            ("UCLA National Heritage Language Resource Center", NHLRC),
        ),
        "reuse": "Print, adapt and share",
        "reuse_text": (
            "This original family routine is CC BY 4.0. Families, libraries and heritage "
            "schools may print or adapt it with credit to iOS App Guide and a link to this page."
        ),
        "app_title": "Optional practice between family calls",
        "app_text": (
            "Lumi Bopomofo adds listening, tracing, tone and blending games for all 37 "
            "symbols. It is free to download with an optional one-time lifetime unlock, "
            "has no ads and requires no recurring subscription."
        ),
        "app_cta": "Try Lumi Bopomofo",
        "related": "Related free resources",
        "related_items": (
            ("3-minute Zhuyin skills check", f"{SITE}/tools/zhuyin-readiness-check.html"),
            ("Parent-teacher Zhuyin handoff kit", f"{SITE}/tools/zhuyin-parent-teacher-handoff-kit.html"),
            ("Family Zhuyin picture-book club kit", f"{SITE}/tools/zhuyin-family-picture-book-club-kit.html"),
            ("Printable Zhuyin flashcards", f"{SITE}/tools/zhuyin-flashcards.html"),
            ("Five-day heritage-school lesson plan", f"{SITE}/guides/zhuyin-5-day-lesson-plan-heritage-school.html"),
        ),
        "faq": "Family FAQ",
        "faq_items": (
            (
                "Does the grandparent need to know how to teach Zhuyin?",
                "No. The script asks for familiar words, gestures and real conversation. It is not a formal lesson plan.",
            ),
            (
                "Does the call have to last exactly ten minutes?",
                "No. Ten minutes is a simple structure, not a target to force. End earlier when attention drops.",
            ),
            (
                "Does this page record our call or the child’s answers?",
                "No. It has no camera, microphone, account, form submission or saved result. It only displays and prints prompts.",
            ),
            (
                "Can this replace a teacher or speech professional?",
                "No. It is a family conversation aid, not a school assessment, curriculum, speech evaluation or professional diagnosis.",
            ),
        ),
        "home": "Home",
        "tools": "Free tools",
        "footer": "Independent family learning resource; not an official curriculum or assessment.",
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "title": "祖孫視訊學注音｜免費 10 分鐘遊戲包",
        "description": "英繁雙語、可列印的祖孫注音視訊流程：三個家庭詞語、鏡頭尋寶、聲調手勢與低壓力提示，免登入、不儲存孩子資料。",
        "eyebrow": "免費家庭工具 · 免登入",
        "lead": "把一次普通家庭視訊，變成 10 分鐘溫暖、有來有往的注音練習；不用把阿公阿嬤變成正式老師。",
        "badges": ("10 分鐘流程", "可直接看或列印", "不上傳、不儲存孩子資料"),
        "start": "產生今天的視訊計畫",
        "language": "English",
        "setup": "兩地怎麼準備？",
        "setup_items": (
            ("1. 孩子身邊的大人", "把本頁開在孩子旁邊，順手準備三樣普通家中物品。"),
            ("2. 阿公阿嬤", "開啟同一頁，或列印一頁腳本，跟著五個短回合進行。"),
            ("3. 全家", "用熟悉詞語與真實對話；孩子還想玩時就收尾，為下次保留期待。"),
        ),
        "kit_title": "今天的三詞視訊計畫",
        "kit_intro": "把詞語當成聊天起點，不是閃卡考試。若孩子沒學過，視訊前按「換一組」。",
        "new_plan": "換一組三詞計畫",
        "print": "列印遊戲包",
        "share": "分享工具",
        "shared": "已複製工具連結。",
        "share_title": "免費祖孫視訊注音遊戲包",
        "timeline": "10 分鐘視訊流程",
        "timeline_items": (
            ("0–1 分", "溫暖打招呼", "叫孩子名字、微笑、拿出熟悉物品；這一分鐘先不問答。"),
            ("1–3 分", "讓孩子選", "請孩子從今天三個符號或家庭詞語中指一張。"),
            ("3–5 分", "聲音照鏡子", "阿公阿嬤示範一次；孩子可跟念、指圖或做動作。"),
            ("5–8 分", "鏡頭尋寶", "在兩邊家裡找和詞語有關的物品、家人或動作。"),
            ("8–9 分", "聲調電梯", "念一個熟悉音節，手跟著音高移動。"),
            ("9–10 分", "家庭短句", "把詞語放進真實句子，再讓孩子選下次想玩的卡。"),
        ),
        "grandparent": "阿公阿嬤的低壓力腳本",
        "grandparent_items": (
            "「今天想玩哪一張？」——給選擇，不用一開始就考。",
            "「我先念一次，你可以跟我念、用手指，或做動作。」",
            "讀音不同時自然重述：「對，是水，ㄕㄨㄟˇ。」不要說答錯。",
            "用具體成功收尾：「你今天找到水，也記得 ㄕ。」",
        ),
        "parent": "孩子身邊大人的工作",
        "parent_items": (
            "固定好裝置，幫兩邊一起看同一樣物品。",
            "先等幾秒，不要立刻代替孩子回答。",
            "只在需要時翻譯，保留祖孫一來一往的節奏。",
            "孩子累了或挫折，就停止練習、回到普通聊天。",
        ),
        "tones": "聲調電梯",
        "tone_note": "念熟悉音節時，用一隻手畫出音高。手勢是本工具自製的教學輔助；正式聲調標示位置以台灣教育部資料為準。",
        "tone_items": (
            ("ㄇㄚ", "第一聲", "→ 平"),
            ("ㄇㄚˊ", "第二聲", "↗ 上揚"),
            ("ㄇㄚˇ", "第三聲", "∨ 先降後升"),
            ("ㄇㄚˋ", "第四聲", "↘ 下降"),
            ("˙ㄇㄚ", "輕聲", "· 短而輕"),
        ),
        "shy": "孩子害羞怎麼辦？",
        "shy_text": "指一指、找物品、揮手或做手勢，都算完成一個互動回合；不要強迫跟念。阿公阿嬤是否敏感回應，比做完每一張卡更重要。",
        "evidence": "研究支持什麼？不能證明什麼？",
        "evidence_text": "一項 48 個家庭的縱向研究發現，不論視訊或面對面，祖父母的敏感回應能預測嬰兒較正向的情緒；論文也整理了即時社會回應與身旁大人協助對幼兒投入視訊的重要性。研究樣本多為高教育程度的白人家庭，且發生於 COVID-19 期間；它沒有測試注音學習，也沒有測試本工具。我們只把研究用於設計短回合、敏感提示與家長協助，絕不宣稱能加速學習。",
        "sources": "研究與官方參考",
        "source_items": (
            ("遠距同在：祖孫視訊互動研究", VIDEO_STUDY),
            ("台灣教育部《國語注音符號手冊》", MOE_HANDBOOK),
            ("台灣教育部《注音練習簿》", MOE_PRACTICE),
            ("UCLA 美國國家傳承語言資源中心", NHLRC),
        ),
        "reuse": "可列印、改編與分享",
        "reuse_text": "本原創家庭流程採 CC BY 4.0；家庭、圖書館與海外中文學校可列印或改編，請標註 iOS App Guide 並連回本頁。",
        "app_title": "兩次祖孫視訊之間的選用練習",
        "app_text": "Lumi 注音星球以聽音、描寫、聲調與拼讀遊戲練習全部 37 個符號。可免費下載，另提供一次性永久解鎖；無廣告、無定期訂閱。",
        "app_cta": "試用 Lumi 注音星球",
        "related": "相關免費資源",
        "related_items": (
            ("3 分鐘注音學習檢核", f"{SITE}/zh-Hant/tools/zhuyin-readiness-check.html"),
            ("家庭—教師注音交接包", f"{SITE}/zh-Hant/tools/zhuyin-parent-teacher-handoff-kit.html"),
            ("家庭注音繪本四週共讀包", f"{SITE}/zh-Hant/tools/zhuyin-family-picture-book-club-kit.html"),
            ("可列印注音符號字卡", f"{SITE}/tools/zhuyin-flashcards.html"),
            ("海外中文學校五日教案", f"{SITE}/zh-Hant/guides/zhuyin-5-day-lesson-plan-heritage-school.html"),
        ),
        "faq": "家庭常見問題",
        "faq_items": (
            ("阿公阿嬤要會教注音嗎？", "不用。腳本只需要熟悉詞語、手勢與真實聊天，不是正式教案。"),
            ("一定要剛好視訊 10 分鐘嗎？", "不用。10 分鐘只是好記的結構，不是要強迫完成的目標；注意力下降就提早收尾。"),
            ("網頁會錄下視訊或孩子答案嗎？", "不會。沒有相機、麥克風、帳號、表單送出或儲存結果，只負責顯示與列印提示。"),
            ("可以取代老師或語言專業人員嗎？", "不行。這是家庭對話輔助，不是學校評量、正式課程、語言治療評估或專業診斷。"),
        ),
        "home": "首頁",
        "tools": "免費工具",
        "footer": "獨立家庭學習資源；不是官方課程或評量。",
    },
}

STYLE = """
:root{--ink:#1e2940;--muted:#667187;--paper:#fffdf8;--line:#e7dfd2;--coral:#c45e52;--coral2:#e48b63;--teal:#14786f;--gold:#bd862e;--soft:#fff3ea}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:linear-gradient(180deg,#fff9f3 0,#f7fbfa 48%,#f8f5ff 100%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.65}a{color:#5941a5}.wrap{width:min(1050px,calc(100% - 32px));margin:auto}.top{position:sticky;top:0;z-index:4;background:#fffffff0;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850}.links{display:flex;gap:15px}.hero{padding:56px 0 28px}.eyebrow{color:var(--coral);font-size:.78rem;font-weight:900;letter-spacing:.09em;text-transform:uppercase}.hero h1{max-width:920px;margin:.18em 0;font-size:clamp(2rem,5.8vw,4.1rem);line-height:1.04;letter-spacing:-.035em}.lead{max-width:800px;color:var(--muted);font-size:clamp(1.08rem,2.5vw,1.28rem)}.badges,.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.badge{padding:8px 12px;border:1px solid #ead8c9;border-radius:999px;background:#fff;color:#755145;font-weight:800;white-space:nowrap}.button{appearance:none;border:0;border-radius:999px;padding:12px 19px;background:linear-gradient(135deg,var(--coral),var(--coral2));color:#fff!important;text-decoration:none;font:inherit;font-weight:850;cursor:pointer;white-space:nowrap;box-shadow:0 8px 20px #a8544225}.button.secondary{background:#fff;color:#5941a5!important;border:1px solid #cec4e6;box-shadow:none}.button:focus-visible{outline:3px solid #e2b858;outline-offset:3px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:18px}.card{grid-column:span 12;padding:23px;background:var(--paper);border:1px solid var(--line);border-radius:23px;box-shadow:0 10px 32px #34281a12}.half{grid-column:span 6}.third{grid-column:span 4}h2{margin:1.55em 0 .58em;font-size:clamp(1.45rem,3vw,2rem);line-height:1.18}h3{line-height:1.25}.muted{color:var(--muted)}.setup .card h3{margin:.1em 0}.kit{margin-top:26px;padding:clamp(22px,4vw,34px);background:#fff;border:1px solid #e0d7ca;border-radius:28px;box-shadow:0 20px 55px #5a382016}.plan-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;flex-wrap:wrap}.plan-head h2{margin:.1em 0}.word-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:22px 0}.word-card{min-height:220px;padding:18px;border:1px solid #ead9cc;border-radius:21px;background:linear-gradient(150deg,#fff8f2,#fff);text-align:center}.symbol{display:inline-flex;align-items:center;justify-content:center;width:72px;height:72px;border-radius:50%;background:#fff;color:var(--coral);font-size:2.6rem;font-weight:900;box-shadow:0 8px 20px #55352014}.word{font-size:1.65rem;font-weight:900;margin-top:9px}.zhuyin{font-size:1.28rem;color:var(--teal);font-weight:850;white-space:nowrap}.prompt{color:var(--muted);font-size:.93rem;text-align:left}.timeline{counter-reset:steps}.turn{display:grid;grid-template-columns:88px 1fr;gap:15px;align-items:start;padding:16px 0;border-bottom:1px solid var(--line)}.turn:last-child{border:0}.time{color:var(--coral);font-weight:900;white-space:nowrap}.turn h3{margin:0}.turn p{margin:.2em 0;color:var(--muted)}.tone-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.tone{padding:15px 9px;border:1px solid var(--line);border-radius:17px;background:#fff;text-align:center}.tone b{display:block;font-size:1.55rem;color:var(--teal);white-space:nowrap}.tone span{display:block;color:var(--muted);font-size:.87rem}.notice{padding:16px 18px;border-left:5px solid var(--gold);border-radius:14px;background:#fff7dc}.source-list a{overflow-wrap:anywhere}.footer{margin-top:44px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}.share-status{min-height:1.5em;color:var(--teal);font-weight:800}
@media(max-width:760px){.half,.third{grid-column:span 12}.word-grid{grid-template-columns:1fr}.word-card{min-height:0}.tone-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.links a:first-child{display:none}.hero{padding-top:38px}.turn{grid-template-columns:72px 1fr}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important}}
@media print{.top,.hero,.setup,.actions,.app-card,.related,.faq,.evidence-section,.footer{display:none!important}body{background:#fff;font-size:10.5pt}.wrap{width:100%}.kit,.card{border:0;box-shadow:none;padding:0}.word-grid{grid-template-columns:repeat(3,1fr)}.word-card{min-height:0;break-inside:avoid}.timeline-grid{display:grid;grid-template-columns:1fr 1fr;gap:10mm}.turn{padding:7px 0}.tone{break-inside:avoid}@page{size:A4;margin:11mm}}
"""

SCRIPT = """
(function(){
  "use strict";
  var cfg=JSON.parse(document.getElementById("kit-config").textContent);
  var board=document.getElementById("word-board");
  var offset=0;
  function card(item){
    var article=document.createElement("article");
    article.className="word-card";
    [["div","symbol",item.symbol],["div","word",item.word],["div","zhuyin",item.zhuyin],["p","prompt",item.prompt]]
      .forEach(function(part){
        var node=document.createElement(part[0]);
        node.className=part[1];
        node.textContent=part[2];
        article.appendChild(node);
      });
    return article;
  }
  function renderPlan(){
    board.replaceChildren();
    var count=cfg.words.length;
    [0,5,10].forEach(function(step){
      board.appendChild(card(cfg.words[(offset+step)%count]));
    });
  }
  document.getElementById("new-plan").addEventListener("click",function(){
    offset=(offset+1+Math.floor(Math.random()*(cfg.words.length-1)))%cfg.words.length;
    renderPlan();
  });
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
  renderPlan();
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
    app_url = appstore_url("lumibopomofo", f"iag_grandparent_{locale.lower()}")

    setup = "".join(
        f'<article class="card third"><h3>{html.escape(title)}</h3>'
        f"<p>{html.escape(text)}</p></article>"
        for title, text in t["setup_items"]
    )
    first_words = WORDS[:3]
    word_cards = "".join(
        '<article class="word-card">'
        f'<div class="symbol">{html.escape(item["symbol"])}</div>'
        f'<div class="word">{html.escape(item["word"])}</div>'
        f'<div class="zhuyin">{html.escape(item["zhuyin"])}</div>'
        f'<p class="prompt">{html.escape(item[locale])}</p></article>'
        for item in first_words
    )
    timeline = "".join(
        f'<div class="turn"><div class="time">{html.escape(minutes)}</div><div>'
        f"<h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div></div>"
        for minutes, title, text in t["timeline_items"]
    )
    tone_cards = "".join(
        f'<div class="tone"><b>{html.escape(mark)}</b><strong>{html.escape(name)}</strong>'
        f"<span>{html.escape(gesture)}</span></div>"
        for mark, name, gesture in t["tone_items"]
    )
    grandparent_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["grandparent_items"]
    )
    parent_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["parent_items"]
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
    config = {
        "shareTitle": t["share_title"],
        "shared": t["shared"],
        "words": [
            {
                "symbol": item["symbol"],
                "word": item["word"],
                "zhuyin": item["zhuyin"],
                "prompt": item[locale],
            }
            for item in WORDS
        ],
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
            "applicationCategory": "EducationalApplication",
            "operatingSystem": "Any",
            "browserRequirements": "JavaScript",
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "learningResourceType": "Family video-call activity kit",
            "educationalUse": "Heritage language practice",
            "educationalLevel": "Beginner",
            "typicalAgeRange": "4-9",
            "timeRequired": "PT10M",
            "license": LICENSE,
            "teaches": [
                "Zhuyin sound-symbol recognition",
                "Mandarin tone awareness",
                "Heritage-language family conversation",
            ],
            "citation": [VIDEO_STUDY, MOE_HANDBOOK, MOE_PRACTICE, NHLRC],
            "author": {"@type": "Organization", "name": "iOS App Guide", "url": SITE},
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
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["title"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div><div class="actions"><a class="button" href="#kit">{html.escape(t["start"])}</a><a class="button secondary" href="{alternate}">{html.escape(t["language"])}</a></div></section>
<section class="wrap setup"><h2>{html.escape(t["setup"])}</h2><div class="grid">{setup}</div></section>
<section class="wrap kit" id="kit">
<div class="plan-head"><div><h2>{html.escape(t["kit_title"])}</h2><p class="muted">{html.escape(t["kit_intro"])}</p></div><div class="actions"><button class="button secondary" id="new-plan" type="button">{html.escape(t["new_plan"])}</button><button class="button secondary" id="print-kit" type="button">{html.escape(t["print"])}</button><button class="button" id="share-kit" type="button">{html.escape(t["share"])}</button></div></div>
<div class="word-grid" id="word-board" aria-live="polite">{word_cards}</div><div class="share-status" id="share-status" aria-live="polite"></div>
<h2>{html.escape(t["timeline"])}</h2><div class="timeline-grid">{timeline}</div>
<div class="grid"><article class="card half"><h2>{html.escape(t["grandparent"])}</h2><ul>{grandparent_items}</ul></article><article class="card half"><h2>{html.escape(t["parent"])}</h2><ul>{parent_items}</ul></article></div>
<h2>{html.escape(t["tones"])}</h2><p class="muted">{html.escape(t["tone_note"])}</p><div class="tone-grid">{tone_cards}</div>
<h2>{html.escape(t["shy"])}</h2><p class="notice">{html.escape(t["shy_text"])}</p>
</section>
<section class="wrap grid evidence-section">
<article class="card half"><h2>{html.escape(t["evidence"])}</h2><p>{html.escape(t["evidence_text"])}</p><h3>{html.escape(t["sources"])}</h3><ul class="source-list">{sources}</ul></article>
<article class="card half"><h2>{html.escape(t["reuse"])}</h2><p>{html.escape(t["reuse_text"])}</p><a href="{LICENSE}" rel="license noopener">Creative Commons Attribution 4.0</a></article>
</section>
<section class="wrap grid related">
<article class="card half app-card"><h2>{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p><a class="button" href="{html.escape(app_url)}" rel="nofollow noopener">{html.escape(t["app_cta"])}</a></article>
<article class="card half"><h2>{html.escape(t["related"])}</h2><ul>{related}</ul></article>
</section>
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
        f'<a href="{target}">Grandparent Zhuyin Video-Call Kit</a></h2>'
        "<p>A bilingual, print-ready 10-minute family call routine.</p>"
        "</article>"
    )
    existing = re.compile(
        r'<article class="card third"><h2><a href="'
        + re.escape(target)
        + r'">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    readiness = re.search(
        r'<article class="card third"><h2><a href="zhuyin-readiness-check\.html">'
        r".*?</article>",
        updated,
        re.S,
    )
    if readiness:
        position = readiness.end()
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
        print(f"grandparent call kit -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
