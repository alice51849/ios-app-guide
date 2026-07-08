#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram 頻道自動發文 — 零成本、零 OpenAI、合法(發自己的頻道、揭露開發者身份)。
內容池來自 telegram_posts.json(可持續擴充各國語言)。依「日+時」輪播,一天多則不重複。
token/chat_id 來自環境變數(GitHub Secrets),不寫死在 repo。
"""
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FOOTER = "\n\n— Lumi Apps(獨立開發者 · 買斷制 · 無訂閱)"


def load_pool():
    with open(os.path.join(HERE, "telegram_posts.json"), encoding="utf-8") as f:
        return json.load(f)


def pick(pool):
    # 依「距基準日的小時數」輪播:不同排程時段=不同貼文,循環涵蓋全部
    base = _dt.datetime(2026, 1, 1)
    now = _dt.datetime.utcnow()
    hours = int((now - base).total_seconds() // 3600)
    return pool[hours % len(pool)]


def main():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not chat:
        print("missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(1)
    pool = load_pool()
    item = pick(pool)
    text = f"{item['text']}\n\n👉 {item['url']}{FOOTER}"
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "disable_web_page_preview": "false",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data)
    try:
        r = urllib.request.urlopen(req, timeout=25)
        res = json.load(r)
        print("posted ok, message_id:", res.get("result", {}).get("message_id"),
              "| lang:", item.get("lang"), "| app:", item.get("app"))
    except urllib.error.HTTPError as e:
        print("telegram HTTPError:", e.code, e.read().decode()[:300], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
