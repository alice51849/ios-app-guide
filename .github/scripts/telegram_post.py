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
    canonical_app_store_url,
    channel_candidates,
    filter_reachable_pool,
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

FALLBACK_TEXT = {
    "en": "📱 {name} — See features, screenshots, and App Store details.",
    "zh-Hant": "📱 {name} — 查看功能、截圖與 App Store 詳情。",
    "zh-Hans": "📱 {name} — 查看功能、截图与 App Store 详情。",
    "ja": "📱 {name} — 機能、スクリーンショット、App Store の詳細を確認できます。",
    "ko": "📱 {name} — 기능, 스크린샷, App Store 상세 정보를 확인하세요.",
    "ms": "📱 {name} — Lihat ciri, tangkapan skrin dan butiran App Store.",
    "de": "📱 {name} — Funktionen, Screenshots und App-Store-Details ansehen.",
    "fr": "📱 {name} — Découvrez les fonctions, captures et détails sur l’App Store.",
    "es": "📱 {name} — Consulta funciones, capturas y detalles en el App Store.",
    "pt-BR": "📱 {name} — Veja recursos, capturas e detalhes na App Store.",
    "ru": "📱 {name} — Посмотрите функции, снимки экрана и сведения в App Store.",
    "ar": "📱 {name} — اطّلع على الميزات ولقطات الشاشة والتفاصيل في App Store.",
    "pl": "📱 {name} — Zobacz funkcje, zrzuty ekranu i szczegóły w App Store.",
}


def _zone(hour_utc):
    if 5 <= hour_utc < 13:
        return "eu_me"
    if 13 <= hour_utc < 21:
        return "americas"
    return "asia"  # 21–05 UTC(含 01:00 排程)


def load_pool():
    with open(os.path.join(HERE, "telegram_posts.json"), encoding="utf-8") as f:
        static_pool = json.load(f)
    import portfolio_daily

    live_apps = {
        app.app_id: app for app in portfolio_daily.load_public_apps()
    }
    pool = []
    represented = {}
    for item in static_pool:
        app_id = str(item.get("app") or "")
        if app_id not in live_apps:
            continue
        normalized = dict(item)
        normalized["app"] = app_id
        normalized["url"] = canonical_app_store_url(
            f"https://apps.apple.com/app/id{app_id}"
        )
        pool.append(normalized)
        represented.setdefault(app_id, set()).add(normalized.get("lang"))
    for app_id, app in live_apps.items():
        for lang, template in FALLBACK_TEXT.items():
            if lang in represented.get(app_id, set()):
                continue
            pool.append(
                {
                    "lang": lang,
                    "app": app_id,
                    "text": template.format(name=app.name),
                    "url": canonical_app_store_url(
                        f"https://apps.apple.com/app/id{app_id}"
                    ),
                }
            )
    return pool


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
    url = canonical_app_store_url(item.get("url"))
    return (
        f"{item['text']}\n\n👉 {url}\n\n"
        f"{footer_for(item.get('lang'))}"
    )


def pick_postable(pool, now=None):
    live_pool = filter_reachable_pool(
        pool, validator=validate_url, label="Telegram"
    )
    return candidates(live_pool, now)[0]


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
