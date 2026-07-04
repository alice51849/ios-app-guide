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
    ],
    "unblurry": [
        "best app to unblur photos",
        "app to fix blurry pictures on iphone",
        "sharpen a blurry photo app",
    ],
    "photocream": [
        "best photo enhancer app for iphone",
        "app to make photos look professional",
    ],
    "cyca": [
        "best period and cycle tracker app private",
        "simple cycle tracking app no account",
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
}
# pro 版沿用對應免費版的利基查詢
CURATED["lumiletterspro"] = CURATED["lumiletters"]
CURATED["lumimathpro"] = CURATED["lumimath"]
CURATED["lumimissionpro"] = CURATED["lumimission"]
CURATED["lumibopomofopro"] = CURATED["lumibopomofo"]


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
