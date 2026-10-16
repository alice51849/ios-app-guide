#!/usr/bin/env python3
"""Post the day's 7-second hook clip to Telegram and Instagram Reels.

The clips are rendered and uploaded by the private Growth Engine
(shorts/scripts/publish_clips.py); .github/growth/clips.json lists their
public video URLs, the App Store link with a per-clip campaign token, the
hook line and the App Store search term shown on the end card.

clips.json carries a pre-planned schedule: every entry names the date, the
slot and the channel of exactly one clip. A clip is scheduled at most once per
channel, so nothing is ever re-posted, and the pacing is decided when the
schedule is written, not here. A slot without an entry posts nothing. The
daily volume climbs by .github/growth/volume-ramp.json (volume_ramp.py): the
planner adds slots stage by stage, and this script checks the day's allowance
right before posting, so a plan written before an automatic throttle never
posts more than the ramp allows today. A rate-limit, spam or action-block
answer from a platform drops that channel one stage (volume_ramp.handle_error)
and opens a volume-throttle GitHub issue.

Captions are search-first (search_caption.py): the problem line, benefit and
keyword line from clips.json, then a few keyword hashtags; the hook variant
rotates across platforms and days and is recorded in clip-posts.json so
post_performance.py can rank variants.

    python3 clip_posts.py telegram --slot 1     # sendVideo + App Store button
    python3 clip_posts.py instagram --slot 15   # Reels via the official API
    python3 clip_posts.py preview --slot 1      # print what would be posted
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import clip_progress
import post_qa
import review_links
import search_caption as SC
import volume_ramp
from social_post_common import play_store_url

HERE = Path(__file__).resolve().parent
CLIPS = HERE.parent / "growth" / "clips.json"
GRAPH = "https://graph.instagram.com/v21.0"

TEXT = {
    "en": {"search": "Search “{s}” on the App Store", "bio": "Link in bio", "button": "Get it on the App Store"},
    "zh-Hant": {"search": "在 App Store 搜尋「{s}」", "bio": "下載連結在個人檔案", "button": "在 App Store 下載"},
    "ja": {"search": "App Storeで「{s}」を検索", "bio": "リンクはプロフィールから", "button": "App Storeで入手"},
    "ko": {"search": "App Store에서 '{s}' 검색", "bio": "링크는 프로필에", "button": "App Store에서 받기"},
    "de": {"search": "Im App Store nach „{s}“ suchen", "bio": "Link in der Bio", "button": "Im App Store laden"},
    "fr": {"search": "Recherchez « {s} » sur l'App Store", "bio": "Lien dans la bio", "button": "Télécharger sur l'App Store"},
    "es": {"search": "Busca «{s}» en el App Store", "bio": "Enlace en la bio", "button": "Descargar en el App Store"},
    "id": {"search": "Cari “{s}” di App Store", "bio": "Link di bio", "button": "Unduh di App Store"},
    "vi": {"search": "Tìm “{s}” trên App Store", "bio": "Link ở bio", "button": "Tải trên App Store"},
    "th": {"search": "ค้นหา “{s}” ใน App Store", "bio": "ลิงก์อยู่ในโปรไฟล์", "button": "ดาวน์โหลดใน App Store"},
    "pt-BR": {"search": "Pesquise “{s}” na App Store", "bio": "Link na bio", "button": "Baixar na App Store"},
    "zh-Hans": {"search": "在 App Store 搜索“{s}”", "bio": "下载链接在主页简介", "button": "在 App Store 下载"},
    "cs": {"search": "Vyhledejte „{s}“ v App Storu", "bio": "Odkaz najdete v profilu", "button": "Stáhnout z App Storu"},
    "pl": {"search": "Wyszukaj „{s}” w App Store", "bio": "Link w bio", "button": "Pobierz z App Store"},
    "nl": {"search": "Zoek op ‘{s}’ in de App Store", "bio": "Link in bio", "button": "Download in de App Store"},
    "da": {"search": "Søg efter “{s}” i App Store", "bio": "Link i bio", "button": "Hent i App Store"},
    "nb": {"search": "Søk etter «{s}» i App Store", "bio": "Lenke i bio", "button": "Last ned i App Store"},
    "el": {"search": "Αναζητήστε «{s}» στο App Store", "bio": "Σύνδεσμος στο προφίλ", "button": "Λήψη από το App Store"},
    "ar": {"search": "ابحث عن «{s}» في App Store", "bio": "الرابط في الملف الشخصي", "button": "حمّله من App Store"},
}


def text_for(locale):
    return TEXT.get(locale) or TEXT.get(locale.split("-")[0]) or TEXT["en"]


def load(path=CLIPS):
    return json.loads(path.read_text(encoding="utf-8"))


def posted_log():
    """Every logged post (clip-posts.json)."""
    path = CLIPS.parent / "clip-posts.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("posts", [])


def already_posted(channel):
    """Clip keys already posted on this channel (clip-posts.json), so a backup
    run (clip-backup.yml) that fills a slot GitHub dropped never re-posts."""
    return {p["clip"] for p in posted_log() if p.get("channel") == channel}


def scheduled(data, day, slot, channel):
    """The clip planned for this date, slot and channel, or None (also None
    once it has been posted)."""
    done = already_posted(channel)
    for entry in data.get("schedule", []):
        if entry["clip"] in done:
            continue
        if entry["date"] == day.isoformat() and entry["slot"] == slot and entry["channel"] == channel:
            clip = data["clips"].get(entry["clip"])
            if clip and clip.get("url"):
                return clip
    return None


# A locale segment of an older clip token (h7_<app>_<locale>): en, ja, zh-Hant, pt-BR ...
CLIP_LOCALE_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


def clip_campaign(token):
    """The clip's App Store campaign without its locale: h7_<app>[_b]_<locale> -> h7_<app>[_b].
    Apple reveals a campaign (per app) only past 5 first-time downloads; per-locale tokens never got
    there, so the token stays at clip x platform and the locale lives in the post log
    (00_GrowthEngine agent/ct_codes.py reads the result)."""
    parts = (token or "h7").split("_")
    if len(parts) >= 3 and parts[0] == "h7" and CLIP_LOCALE_RE.fullmatch(parts[-1]):
        return "_".join(parts[:-1])
    return token or "h7"


def with_campaign(url, channel):
    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query))
    query["ct"] = f"{clip_campaign(query.get('ct', 'h7'))}_{channel}"[:40]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


PLAY_LINE = {"en": "Also on Google Play", "zh-Hant": "Android 版在 Google Play", "ja": "AndroidはGoogle Playで",
             "ko": "Android는 Google Play에서", "de": "Auch bei Google Play", "fr": "Aussi sur Google Play",
             "es": "También en Google Play", "pt-BR": "Também no Google Play",
             "id": "Juga ada di Google Play", "vi": "Có cả trên Google Play", "th": "มีบน Google Play ด้วย",
             "zh-Hans": "安卓版在 Google Play", "cs": "Také na Google Play", "pl": "Także w Google Play",
             "nl": "Ook op Google Play", "da": "Også på Google Play", "nb": "Også på Google Play",
             "el": "Και στο Google Play", "ar": "متوفر أيضًا على Google Play"}


def ios_id(clip):
    m = re.search(r"/id(\d+)", clip.get("store_url", ""))
    return m.group(1) if m else ""


def play_url(clip, channel):
    """Google Play link for the clip's app (same ct token), or None if not on Android."""
    ct = urllib.parse.parse_qs(urllib.parse.urlsplit(clip.get("store_url", "")).query).get("ct", ["h7"])[0]
    return play_store_url(ios_id(clip), f"{clip_campaign(ct)}_{channel}"[:40])


def caption(clip, channel, variant=None):
    """Search-first caption (search_caption.py): problem line, benefit and keyword line inside the first
    125 characters, app name + App Store search line, then a few keyword hashtags."""
    t = text_for(clip["locale"])
    lines = SC.body(clip, variant or SC.variants(clip)[0])
    lines += [clip["name"], t["search"].format(s=clip["search"])]
    lines = SC.dedupe(lines)  # a keyline the app name already says ("可愛待辦清單" / "Mochi: 可愛待辦清單") goes
    if play_store_url(ios_id(clip), "h7"):
        lines.append(PLAY_LINE.get(clip["locale"]) or PLAY_LINE.get(clip["locale"].split("-")[0]) or PLAY_LINE["en"])
    if channel == "instagram":
        lines.append(t["bio"])
    if channel == "telegram":
        # Clickable existing-user review link, only for the review_links.json pairs in their locale
        # (Instagram captions cannot carry a link; Threads posts carry none).
        lines += review_links.lines(review_links.for_clip(clip))
    tags = SC.tags(clip, SC.TAG_LIMIT.get(channel, 5))
    if tags:
        lines += ["", " ".join(tags)]
    return "\n".join(lines)


def _open(req, timeout):
    """The JSON answer; an HTTP error carries the API's reason (never the token) so a rate limit or
    block is recognisable (volume_ramp.is_throttle_error)."""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from None


def _post(url, fields, timeout=60):
    data = urllib.parse.urlencode(fields).encode()
    return _open(urllib.request.Request(url, data=data, headers={"User-Agent": "lumi-clip-poster/1.0"}), timeout)


def _get(url, timeout=60):
    return _open(urllib.request.Request(url, headers={"User-Agent": "lumi-clip-poster/1.0"}), timeout)


def post_telegram(clip, variant=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("clip: Telegram secrets missing, skipped")
        return None
    row = [{"text": text_for(clip["locale"])["button"], "url": with_campaign(clip["store_url"], "tg")}]
    play = play_url(clip, "tg")
    if play:
        row.append({"text": "Google Play", "url": play})
    button = {"inline_keyboard": [row]}
    result = _post(f"https://api.telegram.org/bot{token}/sendVideo", {
        "chat_id": chat,
        "video": clip["url"],
        "caption": caption(clip, "telegram", variant),
        "supports_streaming": "true",
        "reply_markup": json.dumps(button),
    })
    if not result.get("ok"):
        raise RuntimeError(f"Telegram sendVideo failed: {result}")
    message = result["result"]
    username = (message.get("chat") or {}).get("username")
    link = f"https://t.me/{username}/{message['message_id']}" if username else None
    return {"id": message["message_id"], "link": link}


def post_instagram(clip, variant=None, wait=5, tries=60):
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
        "caption": caption(clip, "instagram", variant),  # Reels take no alt_text (image posts only)
        "share_to_feed": "true",
        # Cover = the hook frame once its slam has settled (frame 9), before the first cut: the pain point,
        # full size, inside the 3:4 profile-grid crop.
        "thumb_offset": str(COVER_MS),
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
    media = _post(f"{GRAPH}/{user}/media_publish", {"creation_id": container, "access_token": token})["id"]
    try:
        link = _get(f"{GRAPH}/{media}?fields=permalink&access_token={token}").get("permalink")
    except Exception as exc:  # the Reel is up; a missing link must not fail the run
        print(f"clip: permalink lookup skipped ({exc.__class__.__name__})")
        link = None
    return {"id": media, "link": link}


THREADS = "https://graph.threads.net/v1.0"
COVER_MS = 300  # Reels cover frame (ms): hook settled (its slam ends at frame 7), phone already in view


def post_threads(clip, variant=None, wait=5, tries=60):
    """Video post with the hook caption; store links go in the first reply."""
    token = os.environ.get("THREADS_TOKEN", "").strip()
    user = os.environ.get("THREADS_USER_ID", "").strip()
    if not token or not user:
        print("clip: Threads secrets missing, skipped")
        return None
    # The token's own account id (the THREADS_USER_ID secret can point at an old account).
    user = _get(f"{THREADS}/me?fields=id&access_token={token}").get("id") or user
    t = text_for(clip["locale"])
    text = caption(clip, "threads", variant)
    container = _post(f"{THREADS}/{user}/threads", {
        "media_type": "VIDEO", "video_url": clip["url"], "text": text, "access_token": token,
    })["id"]
    for _ in range(tries):
        status = _get(f"{THREADS}/{container}?fields=status,error_message&access_token={token}")
        if status.get("status") == "FINISHED":
            break
        if status.get("status") == "ERROR":
            raise RuntimeError(f"Threads could not process the video: {status.get('error_message')}")
        time.sleep(wait)
    else:
        raise RuntimeError("Threads processing timed out")
    media = _post(f"{THREADS}/{user}/threads_publish", {"creation_id": container, "access_token": token})["id"]
    links = [f"{t['button']}: {with_campaign(clip['store_url'], 'th')}"]
    play = play_url(clip, "th")
    if play:
        links.append(f"Google Play: {play}")
    try:
        reply = _post(f"{THREADS}/{user}/threads", {
            "media_type": "TEXT", "text": "\n".join(links), "reply_to_id": media, "access_token": token,
        })["id"]
        time.sleep(wait)
        _post(f"{THREADS}/{user}/threads_publish", {"creation_id": reply, "access_token": token})
    except Exception as exc:  # the video is up; a failed reply must not fail the run
        print(f"clip: Threads link reply skipped ({exc.__class__.__name__})")
    try:
        link = _get(f"{THREADS}/{media}?fields=permalink&access_token={token}").get("permalink")
    except Exception as exc:
        print(f"clip: permalink lookup skipped ({exc.__class__.__name__})")
        link = None
    return {"id": media, "link": link}


def qa_variant(clip, channel, preferred, online=True):
    """(variant, problems): the preferred hook variant when its caption passes the pre-post QA gate
    (post_qa.py), else the first variant that does; (None, problems) when none may go out."""
    hooks = SC.variants(clip)
    order = [preferred] + [h for h in hooks if h is not preferred and h.get("id") != preferred.get("id")]
    first = None
    for v in order:
        problems = post_qa.clip_problems(clip, channel, caption(clip, channel, v), online=online)
        if not problems:
            if v is not preferred:
                print(f"clip: hook {preferred.get('id')} refused by QA, posting hook {v.get('id')} instead")
            return v, []
        first = first or problems
        if any("dead store link" in p or "media URL" in p or p.startswith("clip has no") for p in problems):
            break  # the asset itself is broken: no caption can fix it
    return None, first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel", choices=["telegram", "instagram", "threads", "preview"])
    ap.add_argument("--slot", type=int, required=True)
    ap.add_argument("--date", help="YYYY-MM-DD, default today (UTC)")
    args = ap.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    if not CLIPS.exists():
        print("clip: no clips.json yet, nothing to post")
        return 0
    channel = "instagram" if args.channel == "preview" else args.channel
    clip = scheduled(load(), day, args.slot, channel)
    if not clip:
        print(f"clip: nothing scheduled for {channel} on {day} slot {args.slot}")
        return 0
    allowed, done, left = volume_ramp.room(volume_ramp.load(), channel, day, posted_log())
    if left is not None and left <= 0 and args.channel != "preview":
        print(f"clip: {channel} already made {done} of today's {allowed} clip posts (volume-ramp.json); slot skipped")
        return 0
    variant, problems = qa_variant(clip, channel, SC.choose(clip, channel, day), online=args.channel != "preview")
    if variant is None:
        post_qa.gate(problems, f"clip {clip['app']}/{clip['locale']} {channel}")
        return 1
    print(f"clip: {clip['app']} {clip['locale']} hook {variant['id']} {clip['url']}")
    if args.channel == "preview":
        print(caption(clip, "instagram", variant))
        return 0
    try:
        posted = {"telegram": post_telegram, "instagram": post_instagram, "threads": post_threads}[args.channel](clip, variant)
    except Exception as exc:
        # A "slow down" answer drops the channel one ramp stage (committed by the workflow) and opens an issue;
        # any failure still fails the step so it shows red.
        volume_ramp.handle_error(channel, exc, day=day)
        raise
    print(f"clip: posted {posted}")
    if posted:
        # The promotion page (office.cait518.cc) lists every post's link; the variant id feeds the
        # hook A/B ranking in post_performance.py.
        clip_progress.record_post(channel, f"{clip['app']}/{clip['locale']}", posted.get("link"),
                                  media_id=posted.get("id"), variant=variant["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
