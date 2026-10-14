#!/usr/bin/env python3
"""Post the day's 7-second hook clip to Telegram and Instagram Reels.

The clips are rendered and uploaded by the private Growth Engine
(shorts/scripts/publish_clips.py); .github/growth/clips.json lists their
public video URLs, the App Store link with a per-clip campaign token, the
hook line and the App Store search term shown on the end card.

Which clip goes out is a pure function of the date and the slot, so there
is no state to keep: the slot gate already stops a slot from running twice.
Priority apps rotate first; held apps (paid editions promoted only through
their Lite version, apps waiting for a pricing change) are skipped.

    python3 clip_posts.py telegram --slot 1     # sendVideo + App Store button
    python3 clip_posts.py instagram --slot 15   # Reels via the official API
    python3 clip_posts.py preview --slot 1      # print what would be posted
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIPS = HERE.parent / "growth" / "clips.json"
EPOCH = dt.date(2026, 10, 15)
GRAPH = "https://graph.instagram.com/v21.0"

# Slot (UTC hour) -> locales in order of preference for that audience.
SLOT_LOCALES = {
    1: ["zh-Hant", "ja", "ko", "en"],   # Taiwan / Japan / Korea morning
    9: ["en", "de", "fr", "es"],        # Europe
    15: ["en", "es-MX", "pt-BR"],       # Americas
}

TEXT = {
    "en": {"search": "Search “{s}” on the App Store", "bio": "Link in bio", "button": "Get it on the App Store",
           "tags": "#iphoneapps #appstore #iosapps"},
    "zh-Hant": {"search": "在 App Store 搜尋「{s}」", "bio": "下載連結在個人檔案", "button": "在 App Store 下載",
                "tags": "#iPhone #App推薦 #iOS"},
    "ja": {"search": "App Storeで「{s}」を検索", "bio": "リンクはプロフィールから", "button": "App Storeで入手",
           "tags": "#iPhoneアプリ #アプリ紹介 #iOS"},
    "ko": {"search": "App Store에서 '{s}' 검색", "bio": "링크는 프로필에", "button": "App Store에서 받기",
           "tags": "#아이폰어플 #앱추천 #iOS"},
    "de": {"search": "Im App Store nach „{s}“ suchen", "bio": "Link in der Bio", "button": "Im App Store laden",
           "tags": "#iphoneapps #appstore #ios"},
    "fr": {"search": "Recherchez « {s} » sur l'App Store", "bio": "Lien dans la bio", "button": "Télécharger sur l'App Store",
           "tags": "#iphoneapps #appstore #ios"},
    "es": {"search": "Busca «{s}» en el App Store", "bio": "Enlace en la bio", "button": "Descargar en el App Store",
           "tags": "#iphoneapps #appstore #ios"},
    "pt-BR": {"search": "Pesquise “{s}” na App Store", "bio": "Link na bio", "button": "Baixar na App Store",
              "tags": "#iphoneapps #appstore #ios"},
}


def text_for(locale):
    return TEXT.get(locale) or TEXT.get(locale.split("-")[0]) or TEXT["en"]


def load(path=CLIPS):
    data = json.loads(path.read_text(encoding="utf-8"))
    held = set(data.get("hold", []))
    clips = [c for c in data.get("clips", []) if c.get("app") not in held and c.get("url")]
    priority = {app: i for i, app in enumerate(data.get("priority", []))}
    return clips, priority


def pick(clips, priority, day, slot):
    """The clip for this date and slot, or None when nothing fits."""
    wanted = SLOT_LOCALES.get(slot, ["en"])
    best = {}
    for clip in clips:
        if clip["locale"] not in wanted:
            continue
        rank = wanted.index(clip["locale"])
        if clip["app"] not in best or rank < best[clip["app"]][0]:
            best[clip["app"]] = (rank, clip)
    if not best:
        return None
    apps = sorted(best, key=lambda a: (priority.get(a, len(priority)), a))
    # Each slot walks the list one app per day (so every app comes up);
    # slots start a third of the list apart so one day shows different apps.
    slot_index = sorted(SLOT_LOCALES).index(slot) if slot in SLOT_LOCALES else 0
    index = ((day - EPOCH).days + slot_index * (len(apps) // len(SLOT_LOCALES) + 1)) % len(apps)
    return best[apps[index]][1]


def with_campaign(url, channel):
    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query))
    query["ct"] = f"{query.get('ct', 'h7')}_{channel}"[:40]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def caption(clip, channel):
    t = text_for(clip["locale"])
    lines = [clip["hook"], "", clip["name"], t["search"].format(s=clip["search"])]
    if channel == "instagram":
        lines += [t["bio"], "", t["tags"]]
    return "\n".join(line for line in lines if line is not None)


def _post(url, fields, timeout=60):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "lumi-clip-poster/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "lumi-clip-poster/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def post_telegram(clip):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("clip: Telegram secrets missing, skipped")
        return None
    button = {"inline_keyboard": [[{"text": text_for(clip["locale"])["button"],
                                     "url": with_campaign(clip["store_url"], "tg")}]]}
    result = _post(f"https://api.telegram.org/bot{token}/sendVideo", {
        "chat_id": chat,
        "video": clip["url"],
        "caption": caption(clip, "telegram"),
        "supports_streaming": "true",
        "reply_markup": json.dumps(button),
    })
    if not result.get("ok"):
        raise RuntimeError(f"Telegram sendVideo failed: {result}")
    return result["result"]["message_id"]


def post_instagram(clip, wait=5, tries=60):
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        print("clip: IG_ACCESS_TOKEN not set yet, Reels skipped")
        return None
    # Long-lived tokens last 60 days; refreshing on every run keeps them alive.
    try:
        _get(f"https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token={token}")
    except Exception as exc:  # a refresh failure must not block today's post
        print(f"clip: token refresh skipped ({exc.__class__.__name__})")
    me = _get(f"{GRAPH}/me?fields=user_id,username&access_token={token}")
    user = me.get("user_id") or me.get("id")
    container = _post(f"{GRAPH}/{user}/media", {
        "media_type": "REELS",
        "video_url": clip["url"],
        "caption": caption(clip, "instagram"),
        "share_to_feed": "true",
        "access_token": token,
    })["id"]
    for _ in range(tries):
        status = _get(f"{GRAPH}/{container}?fields=status_code&access_token={token}").get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Instagram could not process the video")
        time.sleep(wait)
    else:
        raise RuntimeError("Instagram processing timed out")
    return _post(f"{GRAPH}/{user}/media_publish", {"creation_id": container, "access_token": token})["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel", choices=["telegram", "instagram", "preview"])
    ap.add_argument("--slot", type=int, required=True)
    ap.add_argument("--date", help="YYYY-MM-DD, default today (UTC)")
    args = ap.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    if not CLIPS.exists():
        print("clip: no clips.json yet, nothing to post")
        return 0
    clips, priority = load()
    clip = pick(clips, priority, day, args.slot)
    if not clip:
        print("clip: no clip for this slot")
        return 0
    print(f"clip: {clip['app']} {clip['locale']} {clip['url']}")
    if args.channel == "preview":
        print(caption(clip, "instagram"))
        return 0
    posted = post_telegram(clip) if args.channel == "telegram" else post_instagram(clip)
    print(f"clip: posted {posted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
