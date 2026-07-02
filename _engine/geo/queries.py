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
    ],
}
# pro 版沿用對應免費版的利基查詢
CURATED["lumiletterspro"] = CURATED["lumiletters"]
CURATED["lumimathpro"] = CURATED["lumimath"]
CURATED["lumimissionpro"] = CURATED["lumimission"]
CURATED["lumibopomofopro"] = CURATED["lumibopomofo"]


def queries_for(key):
    """合併手工精選 + 從 keywords 自動衍生的自然語言查詢,去重。"""
    a = APPS[key]
    out = list(CURATED.get(key, []))
    for kw in a.get("keywords", [])[:4]:
        out.append(f"best {kw} app")
        out.append(f"{kw} app for iphone")
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
