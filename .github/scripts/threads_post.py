#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Threads 自動發文 — 零成本,重用 telegram_posts.json 內容池。
兩步流程:建容器 → 等就緒 → 發布;transient 500 會重試。token 來自 env(GitHub Secret)。
"""
import datetime as _dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Lumi Apps poster)"
FOOTER = "\n\n— Lumi Apps · 買斷制 · 無訂閱"


def _post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=30))


# Threads 兩個排程時段(03/14 UTC):台灣/亞洲早、歐美。各發對應時區在地語言。
TZ_LANGS = {
    "asia": ["zh-Hant", "ja", "ko", "zh-Hans", "ms"],                    # 03 UTC 台灣 11:00 / 亞洲
    "west": ["en", "es", "de", "fr", "pt-BR", "ru", "ar", "pl"],         # 14 UTC 歐美
}


def _zone(hour_utc):
    return "west" if 9 <= hour_utc < 21 else "asia"  # 09–21 UTC 歐美;其餘(含 03:00)亞洲


def pick(pool):
    base = _dt.datetime(2026, 1, 1)
    now = _dt.datetime.utcnow()
    hours = int((now - base).total_seconds() // 3600)
    langs = TZ_LANGS[_zone(now.hour)]
    subset = [p for p in pool if p.get("lang") in langs]
    if not subset:
        subset = pool
    return subset[hours % len(subset)]


def main():
    tok = os.environ.get("THREADS_TOKEN", "").strip()
    uid = os.environ.get("THREADS_USER_ID", "").strip()
    if not tok or not uid:
        print("missing THREADS_TOKEN / THREADS_USER_ID", file=sys.stderr); sys.exit(1)
    pool = json.load(open(os.path.join(HERE, "telegram_posts.json"), encoding="utf-8"))
    item = pick(pool)
    text = f"{item['text']}\n\n{item['url']}{FOOTER}"
    try:
        c = _post(f"https://graph.threads.net/v1.0/{uid}/threads",
                  {"media_type": "TEXT", "text": text, "access_token": tok})
        cid = c.get("id")
        if not cid:
            print("no container id:", c, file=sys.stderr); sys.exit(1)
        # 等容器就緒再發布,transient 錯誤重試
        for attempt in range(4):
            time.sleep(35 if attempt == 0 else 25)
            try:
                p = _post(f"https://graph.threads.net/v1.0/{uid}/threads_publish",
                          {"creation_id": cid, "access_token": tok})
                print("threads posted ok, id:", p.get("id"), "| app:", item.get("app"))
                return
            except urllib.error.HTTPError as e:
                b = e.read().decode()[:150]
                if "transient" in b or e.code == 500:
                    print(f"transient, retry {attempt+1}...", file=sys.stderr); continue
                print("threads publish error:", e.code, b, file=sys.stderr); sys.exit(1)
        print("threads publish failed after retries (transient)", file=sys.stderr)
    except urllib.error.HTTPError as e:
        print("threads container error:", e.code, e.read().decode()[:200], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
