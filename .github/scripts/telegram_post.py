#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram 頻道自動發文 — 在地化每日輪播與可靠重試。"""
import datetime as _dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

from social_post_common import (
    AMERICAS_LOCALES,
    ASIA_LOCALES,
    EUROPE_MIDDLE_EAST_LOCALES,
    HTTPStatusError,
    OFFICIAL_SOCIAL_LOCALES,
    RequestError,
    canonical_app_store_url,
    canonical_social_image_url,
    channel_candidates,
    item_footer,
    item_image_url,
    request_json,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = Path(HERE).parents[1]
INTENT_CATALOG_PATH = (
    REPO_ROOT
    / "data"
    / "lumi-studio-publisher-search-intent-catalog.json"
)
INTENT_I18N_PATH = (
    REPO_ROOT / "_engine" / "geo" / "publisher_intent_catalog_i18n.json"
)
SOCIAL_IMAGE_DIR = REPO_ROOT / "social" / "img"
SITE_URL = "https://alice51849.github.io/ios-app-guide"
PUBLISHER_LABEL = "First-party publisher catalog"

# 依 3 個排程時段(01/09/15 UTC)發對應時區的在地語言,讓各國看到自己語言的貼文。
TZ_LANGS = {
    "asia": list(ASIA_LOCALES),                    # 09:00 台灣 / 亞洲(21–05 UTC)
    "eu_me": list(EUROPE_MIDDLE_EAST_LOCALES),    # 歐洲早 / 中東(05–13 UTC)
    "americas": list(AMERICAS_LOCALES),           # 美洲(13–21 UTC)
}


def _zone(hour_utc):
    if 5 <= hour_utc < 13:
        return "eu_me"
    if 13 <= hour_utc < 21:
        return "americas"
    return "asia"  # 21–05 UTC(含 01:00 排程)


def _one_line(value, label):
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError(f"{label} must be a non-empty single line")
    return value.strip()


def _load_intent_pool(live_apps):
    with open(INTENT_CATALOG_PATH, encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    with open(INTENT_I18N_PATH, encoding="utf-8") as i18n_file:
        i18n = json.load(i18n_file)

    locales = catalog.get("locales")
    records = catalog.get("records")
    localizations = i18n.get("localizations")
    if (
        not isinstance(locales, list)
        or len(locales) != 50
        or set(locales) != set(OFFICIAL_SOCIAL_LOCALES)
        or not isinstance(records, list)
        or not isinstance(localizations, dict)
    ):
        raise ValueError("publisher intent catalog does not cover 50 locales")

    expected = {
        (app_id, locale)
        for app_id in live_apps
        for locale in OFFICIAL_SOCIAL_LOCALES
    }
    observed = set()
    pool = []
    for record in records:
        if not isinstance(record, dict) or record.get("verified_live") is not True:
            raise ValueError("publisher intent record is not verified live")
        app_id = str(record.get("app_store_id") or "")
        locale = str(record.get("locale") or "")
        key = str(record.get("app_key") or "")
        pair = (app_id, locale)
        if (
            app_id not in live_apps
            or locale not in OFFICIAL_SOCIAL_LOCALES
            or pair in observed
            or re.fullmatch(r"[a-z0-9]+", key) is None
        ):
            raise ValueError(f"invalid publisher intent social record: {pair}")
        canonical = canonical_app_store_url(
            record.get("canonical_app_store_url")
        )
        if canonical != live_apps[app_id].appstore_url():
            raise ValueError(f"publisher intent App Store mismatch: {pair}")
        image_path = SOCIAL_IMAGE_DIR / f"{key}-share.jpg"
        if not image_path.is_file() or image_path.stat().st_size <= 0:
            raise ValueError(f"missing social image for {key}")
        image_url = canonical_social_image_url(
            f"{SITE_URL}/social/img/{key}-share.jpg"
        )
        translations = localizations.get(locale)
        if not isinstance(translations, dict):
            raise ValueError(f"missing publisher label localization: {locale}")
        publisher_label = _one_line(
            translations.get(PUBLISHER_LABEL),
            f"publisher label {locale}",
        )
        query = _one_line(record.get("publisher_query"), f"query {pair}")
        cta = _one_line(
            record.get("app_store_cta_label"),
            f"App Store CTA {pair}",
        )
        pool.append(
            {
                "lang": locale,
                "app": app_id,
                "app_key": key,
                "text": f"{query}\n{cta}",
                "url": canonical,
                "image_url": image_url,
                "footer": f"— Lumi Studio · {publisher_label}",
                "source": "publisher_intent_catalog",
            }
        )
        observed.add(pair)
    if observed != expected:
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        raise ValueError(
            "publisher intent social coverage mismatch: "
            f"missing={missing[:5]}, unexpected={unexpected[:5]}"
        )
    return pool


def load_pool():
    with open(os.path.join(HERE, "telegram_posts.json"), encoding="utf-8") as f:
        static_pool = json.load(f)
    import portfolio_daily

    live_apps = {
        app.app_id: app for app in portfolio_daily.load_public_apps()
    }
    pool = _load_intent_pool(live_apps)
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
        f"{item_footer(item)}"
    )


def pick_postable(pool, now=None):
    # load_pool() only contains apps from the verified live linkset. Avoid
    # probing the full portfolio again and tripping Apple's HTTP 429 limit.
    return candidates(pool, now)[0]


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


def _send_photo(token, chat, text, image_url):
    image_url = canonical_social_image_url(image_url)
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "photo": image_url,
        "caption": text,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Lumi Apps poster)"},
    )
    return request_json(
        req,
        label="Telegram sendPhoto",
        timeout=30,
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
        text = compose_text(item)
        image_url = item_image_url(item)
        res = (
            _send_photo(tok, chat, text, image_url)
            if image_url
            else _send_message(tok, chat, text)
        )
        if not res.get("ok") or not res.get("result", {}).get("message_id"):
            raise RequestError("Telegram publication returned no message_id")
        print("posted ok, message_id:", res.get("result", {}).get("message_id"),
              "| lang:", item.get("lang"), "| app:", item.get("app"))
        return 0
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Telegram post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
