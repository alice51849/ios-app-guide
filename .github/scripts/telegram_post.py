#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram 頻道自動發文 — 在地化每日輪播與可靠重試。"""
import datetime as _dt
import json
import os
import sys
import urllib.parse
import urllib.request

from social_post_common import (
    HTTPStatusError,
    RequestError,
    channel_candidates,
    footer_for,
    request_json,
    validate_url,
)

HERE = os.path.dirname(os.path.abspath(__file__))

# 依 3 個排程時段(01/09/15 UTC)發對應時區的在地語言,讓各國看到自己語言的貼文。
TZ_LANGS = {
    "asia": ["zh-Hant", "ja", "ko", "zh-Hans", "ms"],          # 09:00 台灣 / 亞洲(21–05 UTC)
    "eu_me": ["de", "fr", "es", "pt-BR", "ru", "ar", "pl"],     # 歐洲早 / 中東(05–13 UTC)
    "americas": ["en", "es", "pt-BR"],                          # 美洲(13–21 UTC)
}


def _zone(hour_utc):
    if 5 <= hour_utc < 13:
        return "eu_me"
    if 13 <= hour_utc < 21:
        return "americas"
    return "asia"  # 21–05 UTC(含 01:00 排程)


def load_pool():
    with open(os.path.join(HERE, "telegram_posts.json"), encoding="utf-8") as f:
        return json.load(f)


def candidates(pool, now=None):
    now = (
        _dt.datetime.now(_dt.timezone.utc)
        if now is None
        else now
    )
    zone = _zone(
        now.hour if now.tzinfo is None else now.astimezone(_dt.timezone.utc).hour
    )
    return channel_candidates(pool, f"telegram:{zone}", now)


def pick(pool, now=None):
    return candidates(pool, now)[0]


def compose_text(item):
    return (
        f"{item['text']}\n\n👉 {item['url']}\n\n"
        f"{footer_for(item.get('lang'))}"
    )


def pick_postable(pool, now=None):
    for item in candidates(pool, now):
        url = item.get("url")
        if validate_url(url):
            return item
        print(f"Telegram: skipping dead URL ({url})", file=sys.stderr)
    raise RequestError("Telegram: no live URL remains in this channel's content pool")


def _send_message(token, chat, text):
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "disable_web_page_preview": "false",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Lumi Apps poster)"},
    )
    return request_json(
        req,
        label="Telegram sendMessage",
        timeout=25,
        attempts=3,
    )


def main():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not chat:
        print("missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1
    try:
        item = pick_postable(load_pool())
        res = _send_message(tok, chat, compose_text(item))
        if not res.get("ok") or not res.get("result", {}).get("message_id"):
            raise RequestError("Telegram sendMessage returned no message_id")
        print("posted ok, message_id:", res.get("result", {}).get("message_id"),
              "| lang:", item.get("lang"), "| app:", item.get("app"))
        return 0
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Telegram post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
