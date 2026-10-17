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

Every post carries the app's direct download link (owner rule 2026-10-17, download_links.py): the
Instagram and Telegram captions hold the full App Store URL (plus Google Play when the app is on
Android; an Instagram caption link is not tappable, so the caption also says "Link in bio → tap “<app>”",
ig_bio.py, and the profile link is the hub ig_bio_hub.py builds), the Threads video keeps
its links in the first reply (account-limit history) and that reply is retried and checked. The QA
gate (post_qa.py) refuses a caption without the link and ensure_download_link() is the last guard at
the send call, so a post never goes out without it silently.

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
import download_links as DL
import ig_bio as IGB
import post_qa
import review_links
import search_caption as SC
import threads_series
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


def already_posted(channel, posts=None):
    """Clip keys already posted on this channel (clip-posts.json), so a backup
    run (clip-backup.yml) that fills a slot GitHub dropped never re-posts.

    A post marked "taken_down" (video_takedown.py: a non-compliant cut taken down) does not count: its entry stays
    as history, and a new compliant real-recording cut of the same clip key can go out on this channel again."""
    posts = posted_log() if posts is None else posts
    return {p["clip"] for p in posts if p.get("channel") == channel and not p.get("taken_down")}


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


CHANNEL_CT = {"instagram": "ig", "telegram": "tg", "threads": "th"}   # ct suffix per channel (agent/ct_codes.py)
# An Instagram surface with its own row (store_shot_cards.py carousels: h7_<app>_igc), so Reels and carousels are
# told apart in App Store Connect; pass it as caption(..., tag=...).
LINK_IN_CAPTION = ("instagram", "telegram")   # Threads keeps its links in the first reply


def play_label(clip):
    return PLAY_LINE.get(clip["locale"]) or PLAY_LINE.get(clip["locale"].split("-")[0]) or PLAY_LINE["en"]


def download_urls(clip, channel, tag=None):
    """(App Store URL, Google Play URL or None) with the channel's own ct token (tag: another surface's suffix)."""
    tag = tag or CHANNEL_CT.get(channel, channel)
    return with_campaign(clip["store_url"], tag), play_url(clip, tag)


def link_lines(clip, channel, tag=None):
    """The "label: URL" lines that carry the direct download link(s) in a caption."""
    store, play = download_urls(clip, channel, tag)
    lines = [f"{text_for(clip['locale'])['button']}: {store}"]
    if play:
        lines.append(f"{play_label(clip)}: {play}")
    return lines


def caption(clip, channel, variant=None, tag=None):
    """Search-first caption (search_caption.py): problem line, benefit and keyword line inside the first
    125 characters, app name + App Store search line, then a few keyword hashtags. tag: the ct suffix of a
    surface with its own row (default: the channel's, CHANNEL_CT)."""
    t = text_for(clip["locale"])
    lines = SC.body(clip, variant or SC.variants(clip)[0])
    lines += [clip["name"], t["search"].format(s=SC.clip_search(clip))]
    lines = SC.dedupe(lines)  # a keyline the app name already says ("可愛待辦清單" / "Mochi: 可愛待辦清單") goes
    if channel == "instagram":
        # The caption URL below cannot be tapped: say where to tap, the app on the profile-link hub (ig_bio.py).
        lines.append(IGB.bio_line(clip["locale"], clip["name"], t["bio"]))
    if channel in LINK_IN_CAPTION:
        lines += link_lines(clip, channel, tag)  # the direct download link(s), in the text itself
    elif play_store_url(ios_id(clip), "h7"):
        lines.append(play_label(clip))  # Threads: the links are in the first reply
    if channel == "telegram":
        # Clickable existing-user review link, only for the review_links.json pairs in their locale
        # (Threads posts carry none).
        lines += review_links.lines(review_links.for_clip(clip))
    tags = SC.tags(clip, SC.TAG_LIMIT.get(channel, 5))
    if tags:
        lines += ["", " ".join(tags)]
    text = "\n".join(lines)
    if channel in LINK_IN_CAPTION:
        # Keeps the links when a long caption would pass the platform limit (hashtags go first).
        store, play = download_urls(clip, channel, tag)
        text = DL.ensure_download_link(text, store, play, max_len=post_qa.LIMITS.get(channel),
                                       app_store_label=t["button"], play_label=play_label(clip),
                                       label=f"{clip.get('app')}/{clip.get('locale')} {channel}")
    return text


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
    store, play_link = download_urls(clip, "telegram")
    text = DL.ensure_download_link(caption(clip, "telegram", variant), store, play_link,
                                   max_len=post_qa.LIMITS["telegram"], app_store_label=text_for(clip["locale"])["button"],
                                   play_label=play_label(clip), label=f"{clip.get('app')}/{clip.get('locale')} telegram")
    result = _post(f"https://api.telegram.org/bot{token}/sendVideo", {
        "chat_id": chat,
        "video": clip["url"],
        "caption": text,
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
    store, play = download_urls(clip, "instagram")
    text = DL.ensure_download_link(caption(clip, "instagram", variant), store, play, max_len=post_qa.LIMITS["instagram"],
                                   app_store_label=text_for(clip["locale"])["button"], play_label=play_label(clip),
                                   label=f"{clip.get('app')}/{clip.get('locale')} instagram")  # never without the link
    container = _post(f"{GRAPH}/{user}/media", {
        "media_type": "REELS",
        "video_url": clip["url"],
        "caption": text,  # Reels take no alt_text (image posts only)
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


# A new Threads container is not ready to publish at once (publishing answers "(#24) The requested resource does
# not exist"); threads_post.publish_post waits 35 s and publishes again 25 s apart, the reply here does the same.
REPLY_WAIT = 35
REPLY_RETRY_WAIT = 25


def own_link_reply_exists(token, media, store, play):
    """True when our own reply under `media` already carries the download link (a retry must not double it),
    False when it does not, None when the look itself failed (then nothing more is posted: a second reply
    could double the first, link_backfill.py looks again later)."""
    try:
        rows = _get(f"{THREADS}/{media}/replies?fields=text,is_reply_owned_by_me&access_token={token}").get("data", [])
    except Exception:
        return None
    return DL.has_download_link(" ".join(r.get("text", "") for r in rows if r.get("is_reply_owned_by_me")), store, play)


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
    store, play = download_urls(clip, "threads")
    links = [f"{t['button']}: {store}"]
    if play:
        links.append(f"Google Play: {play}")
    reply_text = "\n".join(links)
    reply_ok = False
    problems = DL.threads_reply_problems(reply_text, store, play)
    if problems:
        DL.refuse(f"{clip.get('app')}/{clip.get('locale')} threads", problems)
    else:
        reply = None
        for attempt in range(3):  # the video is up: the download link reply is retried, never silently dropped
            if attempt:
                exists = own_link_reply_exists(token, media, store, play)
                if exists:  # an earlier try published after all
                    reply_ok = True
                    break
                if exists is None:  # cannot tell whether it is there: no second reply
                    print("clip: could not check for an earlier link reply; not posting another")
                    break
            try:
                if reply is None:  # a retry publishes the same container again, it never opens a second one
                    reply = _post(f"{THREADS}/{user}/threads", {
                        "media_type": "TEXT", "text": reply_text, "reply_to_id": media, "access_token": token,
                    })["id"]
                    time.sleep(REPLY_WAIT)  # a new container is not ready to publish at once
                _post(f"{THREADS}/{user}/threads_publish", {"creation_id": reply, "access_token": token})
                reply_ok = True
                break
            except Exception as exc:
                print(f"clip: Threads link reply attempt {attempt + 1} failed ({exc.__class__.__name__})")
                time.sleep(REPLY_RETRY_WAIT * (attempt + 1))
    if not reply_ok:
        DL.refuse(f"{clip.get('app')}/{clip.get('locale')} threads",
                  ["the Threads video is up but its download link reply was not posted (link_backfill.py adds it)"])
    try:
        link = _get(f"{THREADS}/{media}?fields=permalink&access_token={token}").get("permalink")
    except Exception as exc:
        print(f"clip: permalink lookup skipped ({exc.__class__.__name__})")
        link = None
    return {"id": media, "link": link, "link_reply": reply_ok}


# Threads clip slots that give way to the evening conversion post (threads-post.yml slot 1, Asia 01:40 UTC).
EVENING_YIELD_SLOTS = (1,)


def yields_to_evening(channel, slot, day, queue=None):
    """The evening conversion post that the Threads hook clip of `slot` gives way to, or None.
    The account takes 3 Threads posts a day (threads-autopilot at Taiwan midnight, slot 1, slot 3),
    so on a date growth/threads-evening-queue.json has a valid post for, the morning hook clip
    (reduce in channel_funnel) leaves the third place to the 13:00 UTC bm_*_th conversion post
    for the top paying markets. Telegram and Instagram post as usual. Slot 1 fires at 09:40 in
    Taiwan, so its UTC date is the Taiwan date the queue is keyed on."""
    if channel != "threads" or slot not in EVENING_YIELD_SLOTS:
        return None
    queue = threads_series.load_evening_queue(threads_series.EVENING_QUEUE) if queue is None else queue
    queued = threads_series.evening_queued(day, queue)
    if queued and not threads_series.evening_queue_problems([queued]):
        return queued
    return None


def qa_variant(clip, channel, preferred, online=True):
    """(variant, problems): the preferred hook variant when its caption passes the pre-post QA gate
    (post_qa.py), else the first variant that does; (None, problems) when none may go out."""
    hooks = SC.variants(clip)
    order = [preferred] + [h for h in hooks if h is not preferred and h.get("id") != preferred.get("id")]
    first = None
    for v in order:
        try:
            text = caption(clip, channel, v)
        except (KeyError, ValueError) as exc:  # DL.MissingDownloadLink is a ValueError: no link, no post
            return None, [f"caption cannot be built: {exc}"]
        problems = post_qa.clip_problems(clip, channel, text, online=online)
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
    queued = yields_to_evening(channel, args.slot, day)
    if queued and args.channel != "preview":
        print(f"clip: Threads slot {args.slot} gives way to tonight's conversion post "
              f"({queued['app']} {queued['ct']}); Telegram and Instagram are unaffected")
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
        if posted.get("link_reply") is False:
            # The post is up and recorded. A red step would only make the watchdog re-dispatch the slot and post
            # it twice, so the step stays green: the ::error:: above is the alert and link_backfill.py (the
            # sweeper, link-backfill.yml) adds the missing reply under the post.
            print(f"::error::{clip['app']}/{clip['locale']} {channel}: posted without its download link reply; "
                  "link-backfill adds it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
