#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Threads 自動發文 — 在地化每日輪播與可靠兩階段發布。"""
import datetime as _dt
import json
import os
import sys
import time
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
UA = "Mozilla/5.0 (Lumi Apps poster)"
MAX_POST_CHARS = 500


def _threads_transient(_status, body):
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    marked_transient = (
        bool(error.get("is_transient")) if isinstance(error, dict) else False
    )
    return marked_transient or "transient" in body.lower()


def _post(url, data, *, label, retry_delays=(2, 4)):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"User-Agent": UA},
    )
    return request_json(
        req,
        label=label,
        timeout=30,
        attempts=3,
        retry_delays=retry_delays,
        extra_transient=_threads_transient,
    )


# Threads 兩個排程時段(03/14 UTC):台灣/亞洲早、歐美。各發對應時區在地語言。
TZ_LANGS = {
    "asia": ["zh-Hant", "ja", "ko", "zh-Hans", "ms"],                    # 03 UTC 台灣 11:00 / 亞洲
    "west": ["en", "es", "de", "fr", "pt-BR", "ru", "ar", "pl"],         # 14 UTC 歐美
}


def _zone(hour_utc):
    return "west" if 9 <= hour_utc < 21 else "asia"  # 09–21 UTC 歐美;其餘(含 03:00)亞洲


def candidates(pool, now=None):
    now = (
        _dt.datetime.now(_dt.timezone.utc)
        if now is None
        else now
    )
    zone = _zone(
        now.hour if now.tzinfo is None else now.astimezone(_dt.timezone.utc).hour
    )
    return channel_candidates(pool, f"threads:{zone}", now)


def pick(pool, now=None):
    return candidates(pool, now)[0]


def compose_text(item):
    return f"{item['text']}\n\n{item['url']}\n\n{footer_for(item.get('lang'))}"


def pick_postable(pool, now=None):
    for item in candidates(pool, now):
        text = compose_text(item)
        if len(text) > MAX_POST_CHARS:
            print(
                f"Threads: skipping overlong item ({len(text)} chars, "
                f"lang={item.get('lang')}, app={item.get('app')})",
                file=sys.stderr,
            )
            continue
        url = item.get("url")
        if validate_url(url):
            return item, text
        print(f"Threads: skipping dead URL ({url})", file=sys.stderr)
    raise RequestError(
        "Threads: no live item of 500 characters or fewer remains in this channel"
    )


def publish_text(token, user_id, text, sleeper=time.sleep):
    if len(text) > MAX_POST_CHARS:
        raise ValueError(
            f"Threads post exceeds {MAX_POST_CHARS} characters: {len(text)}"
        )
    container = _post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        {"media_type": "TEXT", "text": text, "access_token": token},
        label="Threads container",
    )
    container_id = container.get("id")
    if not container_id:
        raise RequestError("Threads container returned no id")
    sleeper(35)
    published = _post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        {"creation_id": container_id, "access_token": token},
        label="Threads publish",
        retry_delays=(25, 25),
    )
    post_id = published.get("id")
    if not post_id:
        raise RequestError("Threads publish returned no id")
    return post_id


def main():
    tok = os.environ.get("THREADS_TOKEN", "").strip()
    uid = os.environ.get("THREADS_USER_ID", "").strip()
    if not tok or not uid:
        print("missing THREADS_TOKEN / THREADS_USER_ID", file=sys.stderr)
        return 1
    try:
        with open(
            os.path.join(HERE, "telegram_posts.json"), encoding="utf-8"
        ) as pool_file:
            pool = json.load(pool_file)
        item, text = pick_postable(pool)
        post_id = publish_text(tok, uid, text)
        print("threads posted ok, id:", post_id, "| app:", item.get("app"))
        return 0
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Threads post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
