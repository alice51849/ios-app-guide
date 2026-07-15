#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 目標查詢清單 — 人們真的會問 AI 的自然語言問句。
監測器會用這些去問各大 LLM,看你的 app 有沒有被推薦、排第幾。
策略:鎖定「競爭小、你就是明確答案」的利基查詢(不碰紅海大詞)。

來源:① CURATED 手工精選的高價值問句 ② 從 registry keywords 自動衍生。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "social"))
from videogen.registry import APPS  # noqa: E402

# 手工精選:最自然、最可能被問、競爭最小的利基問句
CURATED = {
    "snapport": [
        "How can I arrange passport photos on a 4x6 print sheet without uploading my photo?",
        "best app to take passport photos at home",
        "how to make a visa photo with my iphone",
        "passport photo app without subscription",
        "app to make id photos with correct size",
    ],
    "sononote": [
        "best voice to text notes app for iphone",
        "app to transcribe meetings on device privately",
        "voice memo to text app no subscription",
    ],
    "cvdesk": [
        "best resume builder app to pass ats",
        "app to check my resume ats score",
        "cv maker app with no watermark",
        "how to make an ats-friendly resume on iphone without a subscription",
    ],
    "picclear": [
        "best app to find duplicate photos on iphone",
        "app to free up iphone storage fast",
        "find large videos eating storage app",
    ],
    "scanto": [
        "best offline document scanner app for iphone",
        "scan to pdf app with no subscription",
        "pdf scanner app with ocr and face id lock",
        "how to scan a document to a searchable pdf on iphone offline",
    ],
    "gmoney": [
        "best simple budgeting app no subscription",
        "easy expense tracker app for iphone",
    ],
    "hourstag": [
        "best work hours tracker app for freelancers",
        "simple timesheet app to log work hours",
    ],
    "lockhour": [
        "best app to limit screen time and stay focused",
        "app to block distracting apps while working",
        "how to block distracting apps on iphone to focus without a subscription",
    ],
    "unblurry": [
        "best app to unblur photos",
        "app to fix blurry pictures on iphone",
        "sharpen a blurry photo app",
        "how to fix a blurry out of focus photo on iphone without uploading it",
    ],
    "photocream": [
        "best photo enhancer app for iphone",
        "app to make photos look professional",
    ],
    "cyca": [
        "best period and cycle tracker app private",
        "simple cycle tracking app no account",
        "private period tracker that keeps my data on my phone",
    ],
    "lumiletters": [
        "best app to teach kids the alphabet",
        "abc phonics app for toddlers",
        "learn letters app for preschoolers",
    ],
    "lumimath": [
        "best math app for kids",
        "fun math practice app for young children",
    ],
    "lumimission": [
        "best chore and routine app for kids",
        "kids reward chart app",
    ],
    "lumiweather": [
        "weather app for kids to learn",
    ],
    "lumibopomofo": [
        "best app to learn zhuyin bopomofo for kids",
        "chinese phonics app for children",
        "注音符號學習 app 推薦",
        "教小孩注音的 app",
        "Where can I make free printable Bopomofo flashcards for all 37 Zhuyin symbols?",
        "免費注音符號字卡產生器 37 個可列印",
        "Where can I make a free printable Bopomofo tracing and copy worksheet for all 37 symbols?",
        "免費注音符號描寫練習表產生器 37 個可列印",
    ],
    "zodira": [
        "best astrology app with no subscription",
        "tarot and horoscope app that works offline",
        "private birth chart app for iphone",
        "bazi and zi wei astrology app",
        "east west astrology app for iphone",
    ],
    "aim990": [
        "best app to study for the toeic test",
        "toeic listening and reading practice app for iphone",
        "app with a 30 day toeic study plan",
        "toeic prep app with a one time purchase option",
        "offline toeic practice app that works without internet",
        "app to track my toeic score progress toward 990",
        "app to fix my toeic weak points",
        "private toeic study app with no account needed",
        "toeic app alternative to studysapuri english",
        "abceed alternative toeic app for iphone",
        "santa toeic alternative app for iphone",
        "hackers toeic app alternative",
        "toeicer alternative toeic listening and reading app",
        "tflat toeic alternative app for iphone",
        "migii toeic alternative app",
        "best toeic app for working professionals to reach 900",
        "toeic app for self study without a tutor",
        "toeic app to practice listening and reading on the commute",
    ],
    "wordmate": [
        "How can I build a vocabulary study habit without uploading my learning data?",
        "How can I check whether a vocabulary app supports my language before buying?",
        "best pay once vocabulary app for iphone with no subscription",
        "language learning app with a Home Screen vocabulary widget",
        "vocabulary learning app for Apple Watch",
        "one app to learn vocabulary in 44 languages",
        "language app that keeps separate progress for multiple languages",
        "private vocabulary app with no account or tracking",
    ],
}
# pro 版沿用對應免費版的利基查詢
CURATED["lumiletterspro"] = CURATED["lumiletters"]
CURATED["lumimathpro"] = CURATED["lumimath"]
CURATED["lumimissionpro"] = CURATED["lumimission"]
CURATED["lumibopomofopro"] = CURATED["lumibopomofo"]

# Portfolio-wide owned-resource queries are consumed by generators that do not
# recommend a single app as the answer.
PORTFOLIO_CURATED = [
    "How can I find a privacy-first iPhone app with a one-time purchase?",
]


# 2026-07 擴充:補齊各 App 高意圖利基問句,均衡覆蓋 22 App(就地擴充,pro 版沿用同物件)
_MORE = {
    "snapport": [
        "passport photo app that auto removes the background",
        "how to check if my passport photo size is correct",
        "app to print passport photos at home from iphone",
        "baby passport photo app that gets the size right",
        "visa photo maker app without a subscription",
    ],
    "sononote": [
        "app to transcribe voice memos to text on iphone",
        "private meeting transcription app that stays on device",
        "voice to text notes app that works offline",
        "turn a lecture recording into notes app iphone",
        "dictation notes app with no monthly fee",
    ],
    "cvdesk": [
        "how to make an ats friendly resume on my iphone",
        "resume builder app with no watermark or subscription",
        "app to export my cv as a clean pdf",
        "resume template app for job hunting iphone",
        "one time payment resume maker app",
    ],
    "picclear": [
        "how to delete duplicate photos on iphone for free",
        "app to find similar and blurry photos to delete",
        "clean up iphone storage without deleting all photos",
        "app to find large videos taking up storage",
        "duplicate photo cleaner with no subscription",
    ],
    "scanto": [
        "how to scan documents to pdf on iphone offline",
        "document scanner app that locks scans with face id",
        "scan receipts and export to pdf app iphone",
        "offline ocr scanner app that extracts text",
        "app to scan and sign documents on iphone",
    ],
    "cyca": [
        "period tracker app that keeps data offline",
        "menstrual cycle app with no account or cloud",
        "ovulation tracker app that respects privacy",
        "period app that does not sell my data",
        "simple pms and symptom tracker app iphone",
    ],
    "gmoney": [
        "travel budget app for iphone that works offline",
        "trip expense tracker with built in currency converter",
        "app to track spending in multiple currencies abroad",
        "offline currency converter and travel money app",
        "vacation budget planner app with no subscription",
    ],
    "hourstag": [
        "app that shows purchases in hours of work",
        "how many hours of work does this cost app",
        "spending tracker to curb impulse buying iphone",
        "money mindset app to think before you spend",
        "simple private expense awareness app no subscription",
    ],
    "lockhour": [
        "app to block distracting apps while studying",
        "screen time limit app that actually works iphone",
        "how to lock myself out of social media apps",
        "focus timer that blocks apps during deep work",
        "digital detox app with no subscription",
    ],
    "unblurry": [
        "how to fix a blurry photo on iphone",
        "app to sharpen an out of focus picture",
        "make old blurry photos clearer app iphone",
        "unblur and enhance photo app without subscription",
    ],
    "photocream": [
        "film filter app to make photos look analog",
        "vintage retro camera filter app for iphone",
        "aesthetic film presets photo app no subscription",
        "app to give digital photos a 35mm film look",
    ],
    "lumiweather": [
        "kid friendly weather app for families",
        "weather app that tells kids what to wear today",
        "simple family weather app to plan outings with kids",
        "weather app for children with cute visuals",
    ],
    "lumimath": [
        "fun math practice app for young kids offline",
        "app to teach kids addition and subtraction",
        "kids math game app with no ads or subscription",
    ],
    "lumimission": [
        "morning routine app for kids with rewards",
        "chore chart app for children on iphone",
        "app to help kids build daily habits",
    ],
    "lumiletters": [
        "app to teach toddlers letter sounds phonics",
        "learn the alphabet app for preschoolers offline",
        "abc tracing app for kids with no ads",
    ],
}
for _k, _qs in _MORE.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-05 量身定做擴充:每款依「真實受眾 + 痛點 + 具名競品」寫專屬高意圖問句。
# 目標=讓每個 app 在 AI 問答/搜尋中,對「它自己那群買家真正會問的話」成為被推薦的答案。
# 新 app(zafe/mochi/tripplanet)在此首次進 CURATED;mochi 為「免費」app,不用 pay-once 框架。
_TAILORED = {
    # —— 證件照:場景/規格/競品 ——
    "snapport": [
        "passport photo app that meets government size requirements",
        "app to make a us visa photo 2x2 inches at home",
        "id photo app so i do not have to go to a photo booth",
        "white background passport photo app for iphone",
        "baby passport photo app that gets the head size right",
    ],
    # —— 語音轉筆記:競品/隱私/場景 ——
    "sononote": [
        "otter ai alternative that works offline on iphone",
        "app to turn voice memos into a clean summary",
        "transcribe an interview privately on device app",
        "app to record a lecture and get notes with action items",
    ],
    # —— 履歷/ATS:任務導向 ——
    "cvdesk": [
        "app to tailor my resume to a job description",
        "free ats resume checker app for iphone",
        "app that scores how well my cv matches a job posting",
    ],
    # —— 重複照片/清儲存:競品/急迫痛點 ——
    "picclear": [
        "gemini photos alternative to clean up iphone storage",
        "iphone storage full app to find what to delete first",
        "app to bulk delete screenshots and duplicate photos",
    ],
    # —— 掃描/OCR:競品/免訂閱/上鎖 ——
    "scanto": [
        "camscanner alternative with no subscription for iphone",
        "adobe scan alternative that locks documents with face id",
        "app to scan and search text inside pdfs offline",
    ],
    # —— 記帳+匯率:免帳號/旅行 ——
    "gmoney": [
        "app to log expenses in seconds without making an account",
        "offline expense tracker for travelers with no subscription",
    ],
    # —— 花費換算工時:心態/克制衝動 ——
    "hourstag": [
        "app to see if a purchase is worth my hours of work",
        "mindful spending app that turns a price into work time",
    ],
    # —— 專注/擋 app:競品 ——
    "lockhour": [
        "opal alternative app blocker with no subscription",
        "one sec alternative to reduce phone use on iphone",
        "app to block instagram and tiktok during study time",
    ],
    # —— 去模糊/超解析:競品/情感場景 ——
    "unblurry": [
        "remini alternative that works offline with no subscription",
        "app to sharpen and enhance old family photos on iphone",
    ],
    # —— 底片濾鏡:競品/質感 ——
    "photocream": [
        "dazz cam alternative film camera app for iphone",
        "app to add authentic 35mm film grain to iphone photos",
    ],
    # —— 生理週期:競品/隱私 ——
    "cyca": [
        "flo alternative period tracker that stays offline",
        "clue alternative cycle app that needs no account",
    ],
    # —— 幼兒字母/自然發音:年齡/競品 ——
    "lumiletters": [
        "app to teach my 4 year old to read with phonics",
        "abcmouse alternative free phonics app with no subscription",
        "letter tracing app for kindergarten readiness",
    ],
    "lumimath": [
        "app to teach preschoolers counting and early numbers",
        "prodigy math alternative for young kids no subscription",
    ],
    "lumimission": [
        "app to get kids through a morning routine without nagging",
        "chore chart app that motivates kids with rewards offline",
    ],
    "lumiweather": [
        "app to teach kids about weather and what to wear today",
    ],
    # —— 注音:海外華人子女場景 ——
    "lumibopomofo": [
        "app to teach bopomofo to overseas chinese kids",
        "zhuyin tracing app for taiwanese children",
        "Why should my child learn Zhuyin if they already speak Chinese?",
        "How can Zhuyin help my child read a Chinese dictionary?",
        "Where can I find a free five-day Zhuyin lesson plan for a heritage Chinese school?",
        "printable Bopomofo mini unit for weekend Chinese school teachers",
        "How can I check my child's Zhuyin skills at home in three minutes?",
        "海外小孩學注音符號的 app 推薦",
    ],
    # —— 占星:競品/東西合璧/離線 ——
    "zodira": [
        "co-star alternative astrology app that stays private",
        "the pattern alternative astrology app with no subscription",
        "app for chinese bazi and western astrology together",
        "offline tarot card reading app with no ads",
    ],
    # —— TOEIC:分數目標/市場 ——
    "aim990": [
        "toeic study app to go from 700 to 900",
        "toeic app for busy working professionals in japan",
    ],
    # —— 新 app:私密相簿保險箱(Face ID / 全裝置端 / 一次性付費) ——
    "zafe": [
        "app to hide private photos behind face id on iphone",
        "photo vault that keeps everything on device with no cloud upload",
        "how to hide photos on iphone from someone borrowing my phone",
        "private photo and video vault app with one time payment",
        "keepsafe alternative photo vault with no subscription",
        "app to lock a specific album on iphone with face id",
        "secret folder app for photos that stays completely offline",
        "app to hide sensitive screenshots on iphone privately",
    ],
    # —— 新 app:可愛清單(免費 / 無廣告,不用 pay-once 框架) ——
    "mochi": [
        "cute aesthetic to-do list app for iphone without a subscription",
        "cute free to do list app for iphone with no ads",
        "aesthetic checklist app that is satisfying to tick off",
        "minimalist daily task app that is free and needs no account",
        "cozy planner app for students that is free",
        "simple to do list app without a subscription or ads",
        "todoist alternative that is free and cute",
        "app to make a daily checklist you actually enjoy using",
    ],
    # —— 新 app:親子旅行遊戲(離線 / 一次性付費 / 兒童安全) ——
    "tripplanet": [
        "app to entertain kids on a long car trip offline",
        "travel games for kids that work without internet",
        "family vacation packing list app for kids",
        "road trip games app for children with no ads",
        "kid safe travel activity app with one time purchase",
        "app to make flying with toddlers easier",
        "offline travel games to keep children busy in the car",
    ],
}
for _k, _qs in _TAILORED.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-06 國家 × 規格/格式 × 場景 深度在地化擴充(_GEO_TAILORED)。
# 差異化策略:鎖定「翻譯做不到」的原生在地需求 —— 各國證件照精確尺寸、各國履歷格式、
# 具體任務場景。當某國使用者搜尋「自己國家的具體規格」時,我們就是那個精確答案。
# 規格數字皆經查證(官方標準);寫進問句本身作為 AI 內文的正確 anchor,避免生成錯規格。
_GEO_TAILORED = {
    # —— 證件照:各國護照/簽證精確尺寸(既有僅 US 2x2;以下為全新國別覆蓋)——
    "snapport": [
        "app to make a canada passport photo 50x70mm at home",
        "app to take a uk passport photo 35x45mm on iphone",
        "app to make a schengen visa photo 35x45mm at home",
        "app to make a germany visa photo 35x45mm on iphone",
        "app to make a france visa photo 35x45mm at home",
        "app to make a japan passport photo 35x45mm on iphone",
        "app to make a china visa photo 33x48mm at home",
        "app to make an india passport photo 51x51mm on iphone",
        "app to make an australia passport photo 35x45mm at home",
        "app to make a south korea passport photo 35x45mm on iphone",
        "app to make a us green card photo 2x2 inches at home",
        "app to make an oci card photo at home on iphone",
        "app to make a driver license photo at home on iphone",
        "app to make a japanese resume rirekisho photo at home",
        "app to check my passport photo head size is correct",
        "app to change a passport photo background to white on iphone",
    ],
    # —— 履歷:各國格式差異(既有僅通用 ATS;以下鎖定國別履歷慣例)——
    "cvdesk": [
        "app to make a german lebenslauf resume with a photo",
        "app to make a japanese rirekisho resume on iphone",
        "app to make a uk style cv with no photo on iphone",
        "app to make a europass cv on iphone",
        "app to make a french cv with a photo on iphone",
        "app to make a one page us resume that passes ats",
        "app to make a canadian style resume on iphone",
        "app to make an australian resume with selection criteria",
        "app to convert my resume into a german lebenslauf format",
    ],
    # —— 掃描/OCR:具體文件場景(既有為競品替代;以下為任務場景)——
    "scanto": [
        "app to scan receipts for taxes on iphone",
        "app to scan a contract to pdf and sign it",
        "app to scan book pages into a searchable pdf",
        "app to scan business cards to pdf on iphone",
        "app to scan handwritten notes into a pdf offline",
        "app to scan an id card to pdf and lock it with face id",
        "app to scan multiple pages into one pdf on iphone",
    ],
    # —— 清儲存:急迫場景(既有為 gemini/screenshots;以下為不同痛點)——
    "picclear": [
        "app to free up icloud storage by deleting duplicate photos",
        "app to find large videos eating up iphone storage",
        "app to clear whatsapp photos and videos from iphone storage",
        "app to delete similar burst photos and keep the best one",
    ],
    # —— 修復:場景/情感(既有為 remini/old family;以下為新場景)——
    "unblurry": [
        "app to fix motion blur in an iphone photo",
        "app to make blurry screenshot text readable again",
        "app to sharpen a blurry document photo before printing",
        "app to restore a blurry scan of an old paper photo",
    ],
    # —— 語音轉筆記:場景(既有為 otter/interview/lecture;以下為新場景)——
    "sononote": [
        "app to turn a voice memo into a to do list",
        "app to record and summarize a meeting into minutes",
        "app to transcribe a class lecture to text offline",
        "app to transcribe a doctor visit into notes privately",
    ],
    # —— 幼兒字母/發音:各國教學法(既有為年齡/競品;以下鎖定國別學制)——
    "lumiletters": [
        "app to teach a preschooler uk jolly phonics at home",
        "app to teach a child to write letters with correct stroke order",
        "app to teach kindergarten sight words to a 5 year old",
        "app to get a toddler ready to read before pre-k",
    ],
    # —— 注音:場景(既有為海外/描字;以下為家長教學情境)——
    "lumibopomofo": [
        "app to teach a 4 year old zhuyin bopomofo at home",
        "app for kids to practice taiwanese mandarin phonics",
        "app to help my child learn bopomofo before starting school",
    ],
    # —— 幼兒數學:各國早期數學(既有為 counting/競品;以下為方法/學制)——
    "lumimath": [
        "app to teach number bonds and counting before school",
        "app to make early math fun for a five year old at home",
        "app to teach a preschooler to count to twenty",
    ],
    # —— 親子行為:場景(既有為晨間/家務;以下為新情境)——
    "lumimission": [
        "app to build a visual bedtime routine chart for kids",
        "app to give kids a reward chart without ads or subscription",
    ],
    # —— 專注/擋 app:考試/番茄鐘場景(既有為競品/社群;以下為讀書情境)——
    "lockhour": [
        "app to block distracting apps while studying for an exam",
        "app to schedule focus time and lock apps during work",
    ],
    # —— 旅遊記帳:多幣別場景(既有為免帳號;以下為出國情境)——
    "gmoney": [
        "app to track travel expenses in multiple currencies offline",
        "app to split and log holiday spending without an account",
    ],
    # —— 私密相簿:場景(既有為 keepsafe/face id;以下為新情境)——
    "zafe": [
        "app to password protect photos before handing my phone to a child",
        "app to move private photos out of the camera roll on iphone",
    ],
    # —— 底片濾鏡:場景(既有為 dazz/35mm;以下為情境)——
    "photocream": [
        "app to give iphone photos an authentic 90s disposable camera look",
        "app to add film halation and light leaks to photos at full resolution",
    ],
    # —— 親子旅行:場景(既有為長途車程;以下為情境)——
    "tripplanet": [
        "app to keep a toddler busy on a long flight offline",
        "app with a kids packing checklist for a family holiday",
    ],
    # —— 旅遊規劃(tripbee 首次進 CURATED)——
    "tripbee": [
        "app to plan a trip itinerary that works offline",
        "pay once trip planner app with no subscription",
        "app to organize a multi city trip on iphone privately",
    ],
    # —— 週期追蹤:場景(既有為 flo/clue;以下為情境)——
    "cyca": [
        "app to track my cycle and fertile window without an account",
        "period tracker app that keeps all data on device with no ads",
    ],
    # —— 占星:場景(既有為 costar/bazi;以下為情境)——
    "zodira": [
        "app to read my full birth chart offline with no subscription",
        "app for a daily horoscope that does not sell my data",
    ],
    # —— TOEIC:市場/場景(既有已多;以下補通勤/自學角度)——
    "aim990": [
        "app to practice toeic listening and reading on my commute",
        "app to study for the toeic test offline without a tutor",
    ],
}
for _k, _qs in _GEO_TAILORED.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-06 加廣第二批:更多旅遊/移民大國護照規格(接上 answer_facts 的 topic-aware 內容)。
_GEO_TAILORED2 = {
    "snapport": [
        "app to make a spain passport photo 35x45mm at home",
        "app to make an italy passport photo 35x45mm on iphone",
        "app to make a netherlands passport photo 35x45mm at home",
        "app to make an ireland passport photo 35x45mm on iphone",
        "app to make a new zealand passport photo 35x45mm at home",
        "app to make an indonesia passport photo 40x60mm on iphone",
        "app to make a vietnam passport photo 4x6cm at home",
        "app to make a thailand passport photo 35x45mm on iphone",
        "app to make a philippines passport photo 35x45mm at home",
        "app to make a saudi arabia visa photo 40x60mm on iphone",
        "app to make a brazil passport photo 35x45mm at home",
        "app to make a singapore passport photo 35x45mm on iphone",
    ],
}
for _k, _qs in _GEO_TAILORED2.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-06 tick:各國履歷格式加廣(接上 answer_facts 的 RESUME_FORMATS)。
_GEO_TAILORED3 = {
    "cvdesk": [
        "app to make a spanish cv with a photo on iphone",
        "app to make an italian cv on iphone",
        "app to make a dutch cv with no photo on iphone",
        "app to make a chinese resume with a photo on iphone",
        "app to make a korean resume with a headshot on iphone",
        "app to make a brazilian resume on iphone",
        "app to make an indian resume on iphone",
        "app to make a singapore resume on iphone",
    ],
}
for _k, _qs in _GEO_TAILORED3.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-06 tick:純資訊型 AEO 問句(what size / does X need a photo / how long)。
# AI 搜尋引擎最愛引用「直接回答規格」的頁,回答中順帶帶出對應 App。
_GEO_TAILORED4 = {
    "snapport": [
        "what size is a us passport photo",
        "what size is a canada passport photo",
        "what size is a uk passport photo",
        "what size is a schengen visa photo",
        "what size is a japan passport photo",
        "what size is an india passport photo",
        "what size is a china visa photo",
        "what size is an australia passport photo",
        "what size is a south korea passport photo",
    ],
    "cvdesk": [
        "does a german lebenslauf need a photo",
        "does a japanese resume need a photo",
        "how long should a us resume be",
        "does a chinese resume need a photo",
        "should a uk cv have a photo",
        "does a french cv need a photo",
    ],
}
for _k, _qs in _GEO_TAILORED4.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:TripBee Pro 查詢覆蓋補齊(原僅 7 條,遠低於同類;皆誠實高意圖情境)。
_GEO_TAILORED5 = {
    "tripbee": [
        "app to plan a day by day travel itinerary on iphone",
        "app to organize flights hotels and activities in one place",
        "app to make a packing list for a trip on iphone",
        "trip planner app that keeps my plans private on device",
        "app to plan a family vacation itinerary with kids",
        "app to plan a road trip route with stops offline",
        "app to plan a multi city europe trip on iphone",
        "app to organize a group trip itinerary with friends",
        "app to plan a weekend getaway on iphone",
        "app to track a travel budget and expenses offline",
        "app to save trip ideas and build an itinerary later",
        "travel organizer app with no account required",
        "app to plan a business trip schedule on iphone",
        "app to keep all travel bookings in one place offline",
        "pay once travel planner app instead of a subscription",
        "app to make a shared travel itinerary for a family holiday",
        "app to plan a solo trip privately on iphone",
        "offline trip planner app that does not sell my data",
    ],
    "tripplanet": [
        "app to teach kids about a country before a family trip",
        "travel activity app to keep children busy on a road trip offline",
    ],
    "mochi": [
        "simple free to do list app for iphone with no account",
        "app to plan my day with a clean checklist offline",
    ],
}
for _k, _qs in _GEO_TAILORED5.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 新上架 App:Sereno(白噪音/助眠/專注音效機,一次性付費)完整查詢覆蓋。
_GEO_TAILORED_SERENO = {
    "sereno": [
        "pay once white noise app with no subscription",
        "sleep sounds app that works fully offline",
        "white noise app for baby that plays all night offline",
        "brown noise app for adhd focus",
        "app with non looping white noise for sleep",
        "rain sounds app with no ads offline",
        "focus sounds app pay once no subscription",
        "ocean sounds app for sleep on iphone",
        "app for tinnitus relief sounds offline",
        "meditation ambient sound app one time purchase",
        "white noise machine app that does not need an account",
        "sleep sound app that mixes rain and ocean",
        "app to block noise and help me focus at work",
        "high quality white noise app for iphone",
        "app to fall asleep with continuous soothing sound",
        "best white noise app",
        "white noise app for iphone",
        "white noise app for iphone free",
        "how to choose a white noise app",
        "best sleep sounds app",
        "sleep sounds app for iphone",
    ],
}
for _k, _qs in _GEO_TAILORED_SERENO.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:更多旅遊/移民大國護照規格(接上 answer_facts 的 PASSPORT_SPECS)。
_GEO_TAILORED6 = {
    "snapport": [
        "app to make a mexico passport photo 35x45mm at home",
        "app to make a malaysia passport photo 35x50mm on iphone",
        "app to make a turkey passport photo 50x60mm at home",
        "app to make a nigeria passport photo 35x45mm on iphone",
        "app to make a south africa passport photo 35x45mm at home",
        "app to make a pakistan passport photo 35x45mm on iphone",
        "app to make a bangladesh passport photo 45x35mm at home",
        "app to make an egypt visa photo 40x60mm on iphone",
        "app to make a uae visa photo 40x60mm at home",
        "what size is a malaysia passport photo",
        "what size is a turkey passport photo",
        "what size is a uae visa photo",
    ],
}
for _k, _qs in _GEO_TAILORED6.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:非護照證件照類型(US 簽證數位照/入籍/綠卡、加拿大入籍、居留證)。
_GEO_TAILORED7 = {
    "snapport": [
        "app to take a us visa digital photo for ds-160",
        "app to make a us citizenship naturalization photo at home",
        "app to make a us green card photo at home on iphone",
        "app to make a canadian citizenship photo at home",
        "app to make a schengen residence permit photo at home",
        "app to make a digital photo for an online visa application",
        "what are the photo requirements for a ds-160 us visa",
        "what size is a us citizenship photo",
    ],
}
for _k, _qs in _GEO_TAILORED7.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:精選真實知名競品的 "X alternative" 高意圖題(誠實框架:一次買斷/免費替代)。
# 只列真實同類 app;內容由 answer_facts._alternative_facts 產生誠實比較(不誹謗競品)。
_GEO_TAILORED8 = {
    "scanto": ["tiny scanner alternative app for iphone", "genius scan alternative app for iphone",
               "scanner pro alternative with no subscription"],
    "sononote": ["rev voice recorder alternative app for iphone", "notta alternative app for iphone"],
    "cvdesk": ["zety alternative resume app for iphone", "resume io alternative app for iphone",
               "canva resume alternative app for iphone"],
    "picclear": ["cleanup app alternative for iphone", "photo cleaner alternative app for iphone"],
    "unblurry": ["fotor alternative app for iphone", "picsart alternative to unblur photos"],
    "photocream": ["vsco alternative app for iphone", "huji cam alternative app for iphone",
                   "1998 cam alternative app for iphone"],
    "lockhour": ["forest alternative app blocker for iphone", "freedom app alternative for iphone",
                 "jomo alternative app blocker for iphone"],
    "cyca": ["stardust alternative period tracker for iphone", "natural cycles alternative app for iphone"],
    "zafe": ["photo vault alternative app for iphone", "calculator vault alternative for iphone"],
    "zodira": ["sanctuary astrology alternative app for iphone", "nebula astrology alternative for iphone",
               "chani alternative astrology app for iphone"],
    "gmoney": ["splitwise alternative app for iphone", "trail wallet alternative app for iphone"],
    "hourstag": ["ynab alternative app for iphone", "mint alternative spending tracker for iphone"],
    "mochi": ["tick tick alternative free checklist app", "microsoft to do alternative for iphone"],
    "lumiletters": ["khan academy kids alternative phonics app", "duolingo abc alternative app for iphone"],
    "lumimath": ["prodigy math alternative app for kids", "todo math alternative app for iphone"],
    "tripbee": ["wanderlog alternative trip planner for iphone", "tripit alternative app for iphone"],
}
for _k, _qs in _GEO_TAILORED8.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:場景加深 v2(新使用情境長尾,對應 answer_facts 的 scenario-widen v2)。
_GEO_TAILORED9 = {
    "scanto": ["app to scan tax documents to pdf on iphone",
               "app to scan an id card to pdf and lock it",
               "app to scan a passport page to pdf offline"],
    "picclear": ["app to clear live photos to save storage on iphone",
                 "app to find live photos taking up space"],
    "sononote": ["app to transcribe an interview to text on iphone",
                 "app to turn a podcast into notes and quotes"],
    "cvdesk": ["app to write a cover letter tailored to a job",
               "app to make an ats friendly cover letter on iphone"],
    "unblurry": ["app to sharpen a low res profile picture",
                 "app to enhance a linkedin profile photo on iphone"],
}
for _k, _qs in _GEO_TAILORED9.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:第三批護照國家(拉美/非洲/中東/南亞)。
_GEO_TAILORED10 = {
    "snapport": [
        "app to make an argentina passport photo 40x40mm at home",
        "app to make a chile passport photo 45x45mm on iphone",
        "app to make a colombia passport photo 40x50mm at home",
        "app to make a peru passport photo 35x43mm on iphone",
        "app to make a kenya passport photo 50x50mm at home",
        "app to make a ghana passport photo 45x35mm on iphone",
        "app to make a morocco passport photo 35x45mm at home",
        "app to make an israel passport photo 35x45mm on iphone",
        "app to make a sri lanka passport photo 35x45mm at home",
        "app to make a nepal passport photo 35x45mm on iphone",
        "what size is an argentina passport photo",
        "what size is a kenya passport photo",
    ],
}
for _k, _qs in _GEO_TAILORED10.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:第二批證件類型(UK 簽證/居留、澳洲入籍、印度 OCI/PAN)。
_GEO_TAILORED11 = {
    "snapport": [
        "app to make a uk visa photo 45x35mm at home",
        "app to make a uk settlement brp photo on iphone",
        "app to make an australian citizenship photo at home",
        "app to make an india oci photo 2x2 inches at home",
        "app to make an india pan card photo 35x25mm on iphone",
        "what size is a uk visa photo",
        "what size is an india pan card photo",
    ],
}
for _k, _qs in _GEO_TAILORED11.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:護照照片「規則/FAQ」型資訊題(高流量、AI 引擎最愛引用)。
_GEO_TAILORED12 = {
    "snapport": [
        "can you wear glasses in a passport photo",
        "can you smile in a passport photo",
        "what background color for a passport photo",
        "passport photo rules for a baby",
        "can i wear a hat in a passport photo",
        "how much does a passport photo cost",
        "common passport photo mistakes to avoid",
        "why do passport photos get rejected",
        "passport photo requirements at home",
        "can you wear a hijab in a passport photo",
    ],
}
for _k, _qs in _GEO_TAILORED12.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 平行 worker 整合:resume 國別(7)+ resume FAQ + 真實競品(付費/訂閱)。
_GEO_TAILORED13 = {
    "cvdesk": [
        # resume countries batch 2
        "app to make a mexican cv on iphone",
        "app to make a swedish cv on iphone",
        "app to make a polish cv on iphone",
        "app to make a turkish cv on iphone",
        "app to make a uae cv with a photo on iphone",
        "app to make a russian resume on iphone",
        "app to make an indonesian cv on iphone",
        # resume FAQ (high-volume informational)
        "how many pages should a resume be",
        "should a resume have a photo",
        "what is an ats and how to make a resume ats friendly",
        "how to explain an employment gap on a resume",
        "should you put references on a resume",
        "how many bullet points per job on a resume",
        "reverse chronological vs functional resume format",
        "should i send my resume as pdf or word",
        "should you tailor your resume to each job",
    ],
    # real, paid/subscription competitors -> honest pay-once alternative pages
    "gmoney": ["travelspend alternative app for iphone", "tripcoin alternative app for iphone"],
    "hourstag": ["copilot money alternative app for iphone", "pocketguard alternative app for iphone",
                 "spendee alternative app for iphone"],
    "zafe": ["keepsafe alternative app for iphone", "kyms alternative photo vault for iphone"],
    "photocream": ["nomo cam alternative app for iphone", "darkroom alternative app for iphone",
                   "afterlight alternative app for iphone"],
    "tripbee": ["sygic travel alternative app for iphone", "roadtrippers alternative app for iphone"],
    "cyca": ["clue alternative period tracker for iphone", "flo alternative period tracker for iphone"],
    "mochi": ["things 3 alternative free checklist app", "any.do alternative for iphone"],
    "lumimath": ["splashlearn alternative math app for kids"],
    "lumimission": ["s'moresup alternative chore app for kids", "homey alternative chore app for iphone"],
    "lumiweather": ["tinybop weather alternative app for kids", "marcopolo weather alternative for kids"],
    "tripplanet": ["stack the states alternative app for kids", "stack the countries alternative for kids"],
}
for _k, _qs in _GEO_TAILORED13.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 平行 worker 整合(app-scenarios):填補 hourstag/zafe/tripbee/lumimission 場景缺口。
_GEO_TAILORED14 = {
    "hourstag": ["app that converts a price to hours of work before buying",
                 "app to see how many hours of work a purchase costs"],
    "zafe": ["app to move private photos out of the iphone camera roll",
             "app to move sensitive photos into a locked vault"],
    "tripbee": ["offline day by day trip itinerary planner for iphone",
                "app to build a travel itinerary that works offline"],
    "lumimission": ["app to help a toddler build a morning routine",
                    "app to guide kids through a bedtime routine with rewards"],
    "gmoney": ["app to track foreign currency spending offline while traveling"],
    "photocream": ["photo editor with real film grain and halation"],
    "zodira": ["birth chart app for iphone with no account offline"],
    "lumiweather": ["weather app that tells me what clothes my child should wear"],
}
for _k, _qs in _GEO_TAILORED14.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 tick:passport 第四批(西歐/北歐/東亞)。
_GEO_TAILORED15 = {
    "snapport": [
        "app to make a switzerland passport photo 35x45mm at home",
        "app to make an austria passport photo 35x45mm on iphone",
        "app to make a belgium passport photo 35x45mm at home",
        "app to make a portugal passport photo 35x45mm on iphone",
        "app to make a greece passport photo 40x60mm at home",
        "app to make a norway passport photo 35x45mm on iphone",
        "app to make a denmark passport photo 35x45mm at home",
        "app to make a finland passport photo 36x47mm on iphone",
        "app to make a taiwan passport photo at home on iphone",
        "app to make a hong kong passport photo on iphone",
        "what size is a taiwan passport photo",
        "what size is a finland passport photo",
    ],
}
for _k, _qs in _GEO_TAILORED15.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 橫向鋪滿:新上架 app(Sereno)+ 0 覆蓋(Aim990)+ 3 組 FAQ(掃描/儲存/兒童)。
_GEO_TAILORED16 = {
    # —— 新上架:Sereno 白噪音/助眠 ——
    "sereno": [
        "best white noise app to sleep offline",
        "app to fall asleep faster with sounds",
        "brown noise app for focus and concentration",
        "rain sounds app that works offline",
        "sound machine app with a sleep timer no subscription",
        "pink noise app for sleep on iphone",
        "ocean sounds app to relax pay once",
        "white noise app with no ads or subscription",
    ],
    # —— 0 覆蓋:Aim990 TOEIC(誠實、含 ETS 免責)——
    "aim990": [
        "how to study for the toeic test",
        "how to improve my toeic listening and reading score",
        "how long does it take to prepare for toeic",
        "toeic study plan app for daily practice",
        "how to fix my toeic weak spots",
    ],
    # —— 掃描/PDF FAQ(ScanTo)——
    "scanto": [
        "how to scan a document with an iphone",
        "what is ocr for scanned pdfs",
        "how to combine multiple images into one pdf on iphone",
        "how to reduce pdf file size on iphone",
        "how to convert a jpg to pdf on iphone",
        "how to sign a pdf on iphone",
        "how to scan a document without shadows",
        "how to password protect a pdf on iphone",
        "how to scan multiple pages into one pdf",
        "is it safe to scan sensitive documents with an app",
    ],
    # —— 儲存/照片 FAQ(PicClear / Unblurry)——
    "picclear": [
        "why is my iphone storage always full",
        "how to free up iphone storage fast",
        "what is other system data on iphone storage",
        "does deleting photos free up space immediately",
    ],
    "unblurry": [
        "can you actually unblur a photo",
        "how to upscale a photo to higher resolution",
        "what is heic and should you convert to jpg",
    ],
    # —— 兒童學習 FAQ(Lumi 系列)——
    "lumiletters": [
        "what age do kids start reading",
        "what is phonics and why is it used to teach reading",
        "what age should a child start phonics",
        "how to teach a toddler the alphabet at home",
    ],
    "lumimath": [
        "when do children learn to count and recognize numbers",
        "how to teach early math to a preschooler at home",
    ],
    "lumibopomofo": [
        "what is zhuyin bopomofo and how do kids learn it",
        "how to teach mandarin tones and zhuyin blending to my child at home",
        "my child knows bopomofo symbols but cannot blend syllables",
        "孩子會認注音符號但不會拼讀怎麼練",
        "How can I help a child who can blend Zhuyin syllables but cannot read a whole sentence?",
        "How can I help a child move from Zhuyin sentences to a short story?",
        "How can I help a child understand and retell a Zhuyin story?",
    ],
    "lumiweather": [
        "how much screen time is appropriate for young children",
    ],
    "lumimission": [
        "how to get kids to follow a morning or bedtime routine",
        "what makes a kids learning app safe and good",
    ],
}
for _k, _qs in _GEO_TAILORED16.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 新方法:買家意圖「值不值得/多少錢」比價題(一次買斷 vs 服務費/月費)。
_GEO_TAILORED17 = {
    "cvdesk": ["how much does a resume writing service cost",
               "is a resume builder app worth it",
               "resume writing service vs resume app cost"],
    "sononote": ["how much does transcription cost per minute",
                 "is a transcription app worth it",
                 "transcription service vs app cost"],
    "picclear": ["is it worth paying for icloud storage",
                 "how much does icloud storage cost",
                 "clean up storage instead of paying for icloud"],
    "scanto": ["is a scanner app worth it vs a scanner",
               "how much does a document scanner cost",
               "scanner app vs hardware scanner cost"],
}
for _k, _qs in _GEO_TAILORED17.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-07 平行 worker 整合(cost-more + competitors2 + seasonal)。
_GEO_TAILORED18 = {
    # —— cost/worth 比價(擴充 7 app,接 _COST_FACTS)——
    "unblurry": ["how much does photo restoration cost", "is a pay once photo enhancer worth it vs remini"],
    "photocream": ["how much does adobe lightroom cost per year", "is a film filter app worth it vs a subscription"],
    "zafe": ["is it worth paying for a photo vault subscription", "how much does extra icloud storage cost"],
    "lockhour": ["how much does the freedom app cost", "is a pay once focus app worth it vs opal"],
    "cyca": ["how much does flo premium cost", "is a pay once period tracker worth it"],
    "gmoney": ["how much does ynab cost", "is a pay once travel budget app worth it vs ynab"],
    "zodira": ["how much do astrology apps cost", "is a pay once astrology app worth it"],
    # —— 真實競品 alternative(competitors2 驗證過;aim990 排除因有訂閱)——
    "sereno": ["dark noise alternative app for iphone", "endel alternative app for iphone",
               "noisli alternative app for iphone", "calm alternative for sleep sounds no subscription",
               "bettersleep alternative app for iphone",
               "best sleep app to fix sleep after daylight saving time", "white noise app for better sleep new year"],
    "tripbee": ["tripomatic alternative app for iphone", "roadtrippers alternative trip planner"],
    "lumiweather": ["marcopolo weather alternative app for kids"],
    "mochi": ["structured app alternative for iphone", "teuxdeux alternative cute to do list",
              "microsoft to do alternative for iphone"],
    "sononote": ["otter alternative that works offline on iphone", "notta alternative app for iphone",
                 "just press record alternative app for iphone", "fireflies alternative voice notes app"],
    # —— 季節性 demand(路由到既有 handler:scanto/snapport/kids/lockhour/picclear/sereno)——
    "scanto": ["best receipt scanner app for taxes on iphone", "how to scan w2 and tax documents with iphone"],
    "snapport": ["passport photo app for a summer trip abroad", "how to renew a passport photo at home before travel"],
    "picclear": ["how to free up iphone storage after christmas photos", "clear photo storage after the holidays"],
    "lumiletters": ["best kids phonics app for back to school"],
    "lumimath": ["best kids math app for back to school"],
}
for _k, _qs in _GEO_TAILORED18.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-08 整合 more-faq worker:LockHour/Sono Note/Zodira/Sereno 資訊型 FAQ。
_GEO_TAILORED19 = {
    "lockhour": ["how to reduce screen time on iphone",
                 "how to stay focused while studying",
                 "does app blocking actually work"],
    "sononote": ["what is the best way to take meeting notes",
                 "how to record a lecture and get notes"],
    "zodira": ["what is a birth chart",
               "what is a rising sign",
               "what is bazi chinese astrology"],
    "sereno": ["does white noise actually help you sleep",
               "what is the difference between white pink and brown noise"],
}
for _k, _qs in _GEO_TAILORED19.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 2026-07-08 persona-scoped recommendation pages ("best [app] for [persona]") and
# winner-app deep content — pulled from the answer_facts data modules (single
# source of truth, so adding entries there auto-creates the pages here).
try:
    from answer_personas import ALL_PERSONA_QUERIES as _PERSONA_Q
except Exception:
    _PERSONA_Q = {}
for _k, _qs in _PERSONA_Q.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)

try:
    from answer_deep import ALL_DEEP_QUERIES as _DEEP_Q
except Exception:
    _DEEP_Q = {}
for _k, _qs in _DEEP_Q.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)

# 2026-07-08 more-countries2 worker: 8 new passport countries + 7 new resume markets.
_GEO_TAILORED20 = {
    "snapport": [
        "poland passport photo size and background",
        "czech republic passport photo requirements",
        "hungary passport photo size",
        "romania passport photo requirements",
        "ukraine passport photo rules",
        "qatar passport photo size",
        "kuwait passport photo blue background",
        "iceland passport photo background requirements",
    ],
    "cvdesk": [
        "how to write a saudi arabia cv",
        "thailand cv format with photo",
        "vietnam cv format",
        "philippines resume format",
        "south africa cv no photo",
        "how to write a nigeria cv",
        "egypt cv format",
    ],
}
for _k, _qs in _GEO_TAILORED20.items():
    _base = CURATED.setdefault(_k, [])
    for _q in _qs:
        if _q not in _base:
            _base.append(_q)


# 從 AEO share-of-voice 報告自動載入每個 app 的真實競品 → 產生 "X alternative" 查詢
import json as _json  # noqa: E402
_SOV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "aeo_sov.json")
_COMPETITORS = {}
try:
    for _r in _json.load(open(_SOV_PATH, encoding="utf-8")).get("results", []):
        _COMPETITORS[_r["key"]] = [c for c, _ in _r.get("top_competitors", [])][:3]
except Exception:
    _COMPETITORS = {}


def queries_for(key):
    """合併手工精選 + 從 keywords 自動衍生的自然語言查詢,去重。"""
    a = APPS[key]
    out = list(CURATED.get(key, []))
    for kw in a.get("keywords", [])[:4]:
        out.append(f"best {kw} app")
        out.append(f"{kw} app for iphone")
        out.append(f"{kw} app for iphone free")
        out.append(f"how to choose a {kw} app")
    for comp in _COMPETITORS.get(key, []):
        out.append(f"{comp} alternative app for iphone")
    seen, res = set(), []
    for q in out:
        if q.lower() not in seen:
            seen.add(q.lower())
            res.append(q)
    return res


ALL = {k: queries_for(k) for k in APPS}


if __name__ == "__main__":
    total = 0
    for k, qs in ALL.items():
        print(f"\n== {APPS[k]['name']} ({k}) — {len(qs)} 條 ==")
        for q in qs:
            print("  •", q)
        total += len(qs)
    print(f"\n總計 {len(ALL)} 個 app,{total} 條利基查詢")
