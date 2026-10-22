#!/usr/bin/env python3
"""Zero-token daily posts to nine more platforms, reusing the hook-clip pipeline.

What goes out (no new schedule: the clip generator stays untouched):

- clips  today's clip is mirrored from the clips.json schedule of the same day
         and slot (Instagram entry first, then Threads, then Telegram); the
         Korean-only (Naver) and Traditional-Chinese-only (Plurk) channels may
         also take an earlier-scheduled clip of their locale. Each clip carries
         its own locale caption (clip_posts.caption).
- cards  the day's countdown card (countdown_cards.py, countdown-cards branch)
         and utility card (utility_cards.py, utility-cards branch) when they
         are published; slot 15 only, so the morning workflows drew them.

A clip or card never goes to the same platform twice: every post is appended to
.github/growth/clip-posts.json through clip_progress.record_post, which also
puts the link on the promotion page (office.cait518.cc). Daily caps per
platform live in PLAN. Every platform is secret-gated: without its secrets it
logs "not configured" and moves on; one platform failing never fails the run.

Every post carries the app's direct download link (owner rule 2026-10-17, download_links.py): the App
Store link, plus Google Play when the app is on Android. render() builds, per platform, every piece that
platform receives (text, link field / block / facet / first comment) and `final_text()` is the whole of it
as one string: the QA gate (qa_problems, run, export) checks that string, and each post_<platform> sends
the very same pieces after a last link check (outgoing()), so a post without its link is refused with a
::error:: and never sent silently.

Bluesky and Mastodon are posted by the threads-autopilot repo (media.yml),
where those accounts' secrets live: it reads the day's items from the
social-feed branch that `export` writes (feed.json). So this script skips
Bluesky unless FORCE_GUIDE_BLUESKY=1, and a Bluesky secret added here later
never double-posts. YouTube Shorts of the clips come from the Mac
(00_GrowthEngine hook-shorts-youtube.yml, back on since the owner's 2026-10-14
decision), reading the same feed, so this script skips YouTube too unless
FORCE_GUIDE_YOUTUBE=1. Besides the day's items, `export` lists a `pool` of every
uploaded clip for Bluesky and YouTube (performance boost apps first) and the
performance summary, so those posters can pick the best clip not yet posted.

    python3 social_extra.py post --slot 1 [--channel bluesky] [--dry-run]
    python3 social_extra.py whoami [--channel facebook]
    python3 social_extra.py export --out feed.json [--date YYYY-MM-DD]
"""
import argparse
import base64
import datetime as dt
import hashlib
import hmac
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xmlrpc.client
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import channel_rotation as CR  # noqa: E402
import clip_posts  # noqa: E402
import download_links as DL  # noqa: E402
import clip_progress  # noqa: E402
import review_links  # noqa: E402
import countdown_cards  # noqa: E402
import post_qa  # noqa: E402
import search_caption as SC  # noqa: E402
from social_post_common import play_store_url  # noqa: E402

UA = "lumi-social-extra/1.0"
REPO = os.environ.get("GITHUB_REPOSITORY") or "alice51849/ios-app-guide"
PAUSE = 5  # seconds between polls (tests set 0)
STAGGER = 20  # seconds between two platforms that posted

CHANNELS = ("facebook", "bluesky", "youtube", "pinterest", "tumblr", "naver", "plurk", "dailymotion",
            "misskey", "pixelfed", "telegraph", "writeas", "hatena", "wordpress", "blogger", "whitewind")
# X is pay-per-post: the owner never uses paid channels, so it is not a channel here.
# cap = posts a day; clips/cards = what the platform takes; locales = allowed caption locales.
PLAN = {
    "facebook": {"cap": 2, "clips": True, "cards": False},
    "bluesky": {"cap": 3, "clips": True, "cards": True},
    "youtube": {"cap": 2, "clips": True, "cards": False},
    "pinterest": {"cap": 3, "clips": True, "cards": True},
    "tumblr": {"cap": 3, "clips": True, "cards": True},
    "naver": {"cap": 1, "clips": True, "cards": True, "locales": ("ko",)},
    "plurk": {"cap": 2, "clips": True, "cards": True, "locales": ("zh-Hant",)},
    "dailymotion": {"cap": 1, "clips": True, "cards": False},
    # Export only (not in CHANNELS): posted by threads-autopilot from feed.json.
    "mastodon": {"cap": 2, "clips": True, "cards": True},
    # Export only: posted from feed.json by the Mac (00_GrowthEngine social/feed_poster.py), whose TikTok token
    # rotates on every refresh and stays on the Mac. A clip goes out only once 04's real-recording gate passed it.
    "tiktok": {"cap": 2, "clips": True, "cards": False},
    # 2026-10-22 (owner: 50 platforms a day): one or two a day each, the safe pace of a new account.
    "misskey": {"cap": 2, "clips": True, "cards": True, "locales": ("ja",)},
    "pixelfed": {"cap": 2, "clips": True, "cards": True},
    "telegraph": {"cap": 2, "clips": True, "cards": True},
    "writeas": {"cap": 1, "clips": True, "cards": True},
    "hatena": {"cap": 1, "clips": True, "cards": True, "locales": ("ja",)},
    "wordpress": {"cap": 1, "clips": True, "cards": True},
    "blogger": {"cap": 1, "clips": True, "cards": True},
    "whitewind": {"cap": 1, "clips": True, "cards": True},
}
# Served by another repo from feed.json; this script never posts them unless forced
# (FORCE_GUIDE_BLUESKY=1 / FORCE_GUIDE_YOUTUBE=1), so nothing is ever double-posted.
# Pinterest's refresh token rotates (60-day continuous refresh): only the Mac can write the new one back, so the
# Mac posts the feed's Pinterest items (00_GrowthEngine social/feed_poster.py) and this runner leaves them alone.
SERVED_ELSEWHERE = {"bluesky": "threads-autopilot media.yml", "youtube": "00_GrowthEngine hook-shorts-youtube.yml",
                    "pinterest": "00_GrowthEngine social/feed_poster.py (Mac)"}
EXPORT_CHANNELS = ("bluesky", "mastodon", "youtube", "pinterest", "tiktok")
# Channels whose poster picks from the whole clip library (feed["pool"]), not only the day's schedule.
POOL_CHANNELS = ("bluesky", "youtube", "pinterest", "tiktok")
FEED_SCHEMA = "lumi.social-feed/v1"
SECRETS = {
    "facebook": ("FB_PAGE_ID", "FB_PAGE_TOKEN"),
    "bluesky": ("BSKY_HANDLE", "BSKY_APP_PASSWORD"),
    "youtube": ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"),
    "pinterest": ("PINTEREST_TOKEN",),
    "tumblr": ("TUMBLR_CONSUMER_KEY", "TUMBLR_CONSUMER_SECRET", "TUMBLR_TOKEN", "TUMBLR_TOKEN_SECRET", "TUMBLR_BLOG"),
    "naver": ("NAVER_ID", "NAVER_BLOG_API_PASSWORD"),
    "plurk": ("PLURK_APP_KEY", "PLURK_APP_SECRET", "PLURK_TOKEN", "PLURK_TOKEN_SECRET"),
    "dailymotion": ("DM_API_KEY", "DM_API_SECRET", "DM_USERNAME", "DM_PASSWORD"),
    "misskey": ("MISSKEY_TOKEN",),
    "pixelfed": ("PIXELFED_TOKEN",),
    "telegraph": ("TELEGRAPH_TOKEN",),
    "writeas": ("WRITEAS_TOKEN",),
    "hatena": ("HATENA_ID", "HATENA_BLOG_ID", "HATENA_API_KEY"),
    "wordpress": ("WPCOM_SITE", "WPCOM_TOKEN"),
    "blogger": ("BLOGGER_BLOG_ID", "BLOGGER_REFRESH_TOKEN"),
    "whitewind": ("BSKY_HANDLE", "BSKY_APP_PASSWORD"),
}
# Campaign suffix per platform (App Store ct token / Play referrer).
CT = {"facebook": "fb", "bluesky": "bs", "youtube": "yt", "pinterest": "pin", "tumblr": "tb",
      "naver": "nv", "plurk": "pk", "dailymotion": "dm", "mastodon": "ma", "tiktok": "tt",
      "misskey": "mk", "pixelfed": "pxf", "telegraph": "tph", "writeas": "wrt", "hatena": "htn", "wordpress": "wp",
      "blogger": "blg", "whitewind": "ww"}


def env(name):
    return os.environ.get(name, "").strip()


def served_elsewhere(channel):
    return channel in SERVED_ELSEWHERE and env(f"FORCE_GUIDE_{channel.upper()}") != "1"


def not_configured(channel):
    if served_elsewhere(channel):
        return (f"{channel}: not configured here (served by {SERVED_ELSEWHERE[channel]}; "
                f"FORCE_GUIDE_{channel.upper()}=1 overrides)")
    return f"{channel}: not configured ({', '.join(SECRETS[channel])})"


def configured(channel):
    if served_elsewhere(channel):
        return False
    if channel == "facebook" and env("IG_ACCESS_TOKEN"):
        return True  # the probe may find a Page token behind the Instagram token
    if channel == "pinterest" and all(env(k) for k in ("PINTEREST_REFRESH_TOKEN", "PINTEREST_APP_ID", "PINTEREST_APP_SECRET")):
        return True
    return all(env(k) for k in SECRETS[channel])


# ---------------------------------------------------------------- HTTP helpers

def http(method, url, data=None, headers=None, timeout=180, raw=False):
    """JSON (or raw status, headers, body) from one request; errors never echo the URL query (tokens)."""
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if raw:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, body
            try:
                return json.loads(body) if body.strip() else {}
            except ValueError:  # e.g. an S3 upload answering in XML
                return {"raw": body.decode(errors="replace")[:300]}
    except urllib.error.HTTPError as exc:
        parts = urllib.parse.urlsplit(url)
        reason = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"HTTP {exc.code} {parts.netloc}{parts.path}: {reason}") from None


def fetch_bytes(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def exists(url):
    try:
        return http("HEAD", url, raw=True, timeout=30)[0] == 200
    except Exception:
        return False


def form(fields):
    return urllib.parse.urlencode(fields).encode()


def jbody(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def multipart(parts):
    """parts: [(name, value)] or [(name, bytes, filename, content_type)] -> (body, content type)."""
    boundary = "lumi" + uuid.uuid4().hex
    out = []
    for part in parts:
        name, value = part[0], part[1]
        if len(part) > 2:
            filename, ctype = part[2], part[3]
            disp = f'form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "")
            out.append(f"--{boundary}\r\nContent-Disposition: {disp}\r\nContent-Type: {ctype}\r\n\r\n".encode() + value + b"\r\n")
        else:
            out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def _enc(value):
    return urllib.parse.quote(str(value), safe="~-._")


def oauth1_header(method, url, consumer_key, consumer_secret, token, token_secret, params=None,
                  nonce=None, timestamp=None):
    """OAuth 1.0a HMAC-SHA1 Authorization header (form params signed, JSON/multipart bodies not)."""
    oauth = {"oauth_consumer_key": consumer_key, "oauth_nonce": nonce or uuid.uuid4().hex,
             "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(timestamp or int(time.time())),
             "oauth_token": token, "oauth_version": "1.0"}
    parts = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True) + list((params or {}).items()) + list(oauth.items())
    norm = "&".join(f"{k}={v}" for k, v in sorted((_enc(k), _enc(v)) for k, v in pairs))
    base = "&".join([method.upper(), _enc(f"{parts.scheme}://{parts.netloc}{parts.path}"), _enc(norm)])
    key = f"{_enc(consumer_secret)}&{_enc(token_secret)}".encode()
    oauth["oauth_signature"] = base64.b64encode(hmac.new(key, base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth.items()))


def to_jpeg(data, limit=950_000):
    """PNG/JPEG bytes -> JPEG under `limit` bytes (Bluesky blobs must stay under 1 MB)."""
    try:
        from PIL import Image
    except ImportError:
        if len(data) <= limit and data[:3] == b"\xff\xd8\xff":
            return data
        raise RuntimeError("pillow is needed to convert the card")
    img = Image.open(io.BytesIO(data)).convert("RGB")
    while True:
        for quality in (90, 82, 74, 66, 58, 50):
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality, optimize=True)
            if buf.tell() <= limit:
                return buf.getvalue()
        img = img.resize((int(img.width * 0.8), int(img.height * 0.8)))


# ---------------------------------------------------------------- what to post

def load_posts():
    return clip_progress.load_json(clip_progress.POSTS, {}).get("posts", [])


def variant_for(clip, channel, day):
    """The day's hook variant. A YouTube Short is found through search, where hook slogans got no views
    (00_GrowthEngine social/reports/youtube_performance.md), so it leads with the problem line (variant a)
    unless the performance loop already knows a winner; the other platforms rotate (search_caption.choose)."""
    if channel != "youtube":
        return SC.choose(clip, channel, day)
    hooks = SC.variants(clip)
    by_id = {h["id"]: h for h in hooks}
    best = clip.get("hook_best") or SC.winner(SC.winners(), f"{clip.get('app')}/{clip.get('locale')}", clip.get("locale"))
    return by_id.get(best) or by_id.get("a") or hooks[0]


def clip_item(key, clip, channel, day=None):
    """One clip for one platform: search-first caption, keyword title / alt text, the day's hook variant."""
    ct = CT[channel]
    t = clip_posts.text_for(clip["locale"])
    v = variant_for(clip, channel, day or SC.today())
    item = {"kind": "clip", "key": key, "locale": clip["locale"], "app": clip["app"], "video": clip["url"],
            "hook": v["lead"], "name": clip["name"], "title": SC.pin_title(clip, v), "tags": SC.tags(clip, 10),
            "caption": clip_posts.caption(clip, channel, v), "button": t["button"], "variant": v["id"],
            "alt": SC.alt_text(clip, v), "clip": clip, "v": v,
            "store": clip_posts.with_campaign(clip["store_url"], ct, day), "play": clip_posts.play_url(clip, ct, day)}
    # Existing-user review link, every App (12 top-3 formula, 2026-10-20: ratings are the gap on every App; the
    # review_links.json pairs keep their own line, the others get the neutral any_app line): {"label", "url"}, no ct.
    # It reaches the feed as is (the YouTube Shorts description, threads-autopilot's Bluesky posts). Every channel
    # that reads it attaches it only when it fits whole: never by trimming the caption or a download link.
    review = review_links.for_clip(clip, any_app=True)
    if review:
        item["review"] = review
    return item


def todays_clips(data, posts, channel, day, slot):
    """Unposted clips for this platform: today's slot entries (Instagram first), plus
    earlier-scheduled clips of the locale for locale-only platforms."""
    locales = PLAN[channel].get("locales")
    done = {p["clip"] for p in posts if p["channel"] == channel}
    order = {"instagram": 0, "threads": 1, "telegram": 2}
    schedule = data.get("schedule", [])
    keys = [e["clip"] for e in sorted((e for e in schedule if e["date"] == day.isoformat() and e["slot"] == slot),
                                      key=lambda e: order.get(e["channel"], 9))]
    if locales:
        keys += [e["clip"] for e in schedule if e["date"] < day.isoformat()]
    out, seen = [], set()
    for key in keys:
        clip = data.get("clips", {}).get(key)
        if key in seen or key in done or not clip or not clip.get("url") or post_qa.video_compliance_problems(clip):
            continue
        seen.add(key)
        if locales and clip["locale"] not in locales:
            continue
        out.append(clip_item(key, clip, channel, day))
    return out


def with_tags(caption, tags, channel):
    """A card caption plus its keyword hashtags (as many as the platform takes well)."""
    tags = tags[:SC.TAG_LIMIT.get(channel, 5)]
    return caption + "\n\n" + " ".join(tags) if tags else caption


def raw_url(branch, day):
    return f"https://raw.githubusercontent.com/{REPO}/{branch}/card-{day.strftime('%Y%m%d')}.jpg"


def todays_cards(day, channel):
    """The day's countdown and utility cards (their own captions and store links)."""
    ct = CT[channel]
    cards = []
    hit = countdown_cards.due(day)
    if hit:
        e, n = hit
        cap = countdown_cards.caption(e, n, day)
        tags = SC.card_tags("countdaysnow", e["locale"]) or ["#countdown", "#CountDaysNow"]
        cards.append({"kind": "card", "key": f"card/{e['id']}/{day.isoformat()}", "locale": e["locale"],
                      "image": raw_url("countdown-cards", day), "caption": with_tags(cap, tags, channel),
                      "title": cap.split("\n")[0], "alt": SC.card_alt("CountDaysNow", cap, "countdaysnow", e["locale"]),
                      "name": "CountDaysNow", "hook": cap.split("\n")[0], "tags": tags,
                      "button": countdown_cards.TEXT[e["locale"]]["button"],
                      "store": countdown_cards.store_url(e, ct),
                      "play": countdown_cards.play_store_url(countdown_cards.APP_ID, countdown_cards.campaign(ct))})
    try:
        import utility_cards as uc
    except ImportError:
        uc = None
    if uc:
        try:
            card = uc.pick(day)
            cap = uc.caption(card, day)
            app = uc.APPS[card["app"]]
            tags = SC.card_tags(card["app"], card["locale"]) or [f"#{app['name'].replace(' ', '')}"]
            cards.append({"kind": "card", "key": card["key"], "locale": card["locale"],
                          "image": raw_url("utility-cards", day), "caption": with_tags(cap, tags, channel),
                          "title": cap.split("\n")[0], "alt": SC.card_alt(app["name"], cap, card["app"], card["locale"]),
                          "name": app["name"], "hook": cap.split("\n")[0], "tags": tags,
                          "button": clip_posts.text_for(card["locale"])["button"], "store": uc.store_url(card, ct),
                          "play": countdown_cards.play_store_url(app["id"], uc.campaign(card, ct))})
        except Exception as exc:  # a utility-card data change must not stop the clips
            print(f"social-extra: utility card skipped ({exc.__class__.__name__})")
    cards += carousel_cards(day, channel)
    locales = PLAN[channel].get("locales")
    return [c for c in cards if not locales or c["locale"] in locales]


# ---------------------------------------------------------------- image carousels (00_GrowthEngine social/carousel)
#
# 2026-10-22 (carousel line): 5-card 1080x1350 carousels made from the apps' public App Store screenshots plus
# localized text cards (00_GrowthEngine social/carousel/build_carousels.py; pain -> fix -> app, and "5 apps for X"
# lists with at least 3 other developers' apps, names and objective facts only). The images live on the public
# release "carousel-cards"; the queue is .github/growth/carousels.json. Each entry opens on its `start` day and stays
# offered for CAROUSEL_WINDOW_DAYS; the posters keep their own caps and never post a key twice. A card item carries
# `images` (all cards, in order) besides `image` (the cover): Bluesky takes up to 4, single-image posters the cover.
CAROUSELS = HERE.parent / "growth" / "carousels.json"
CAROUSEL_WINDOW_DAYS = 21


def carousel_store_url(entry, channel):
    """App Store link of a carousel post: the h7 family's platform token, sent at the app's level (app_campaign)."""
    app_id = str(entry["app_id"])
    token = DL.app_campaign(f"h7_{entry['app']}_{CT.get(channel, channel)}", app_id)
    query = urllib.parse.urlencode({"pt": "118326163", "ct": token, "mt": "8"})
    return f"https://apps.apple.com/{entry['country'].lower()}/app/id{app_id}?{query}"


def carousel_cards(day, channel, path=None):
    """The queued carousels due on `day` for `channel` (queue order: the flagship and priority apps first)."""
    try:
        data = json.loads(Path(path or CAROUSELS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    today, oldest = day.isoformat(), (day - dt.timedelta(days=CAROUSEL_WINDOW_DAYS)).isoformat()
    out = []
    for e in data.get("items") or []:
        start = str(e.get("start") or "")
        images = [u for u in e.get("images") or [] if isinstance(u, str) and u.startswith("https://")]
        if not start or not oldest <= start <= today or channel not in (e.get("channels") or []) or not images:
            continue
        body = e.get("short") if channel == "bluesky" else e.get("text")
        tags = [t for t in e.get("tags") or [] if isinstance(t, str)]
        tags = tags[:SC.TAG_LIMIT.get(channel, 5)]
        if channel == "bluesky":  # 4 images at most: the entry's own 4-card cut (the app reveal kept)
            images = [u for u in e.get("images4") or [] if isinstance(u, str) and u.startswith("https://")] or images[:4]
        out.append({"kind": "card", "key": f"carousel/{e['id']}", "locale": e["locale"], "app": e["app"],
                    "image": images[0], "images": images, "caption": with_tags(body or e["hook"], tags, channel),
                    "title": e["hook"], "alt": e.get("alt") or e["hook"], "name": e["name"], "hook": e["hook"],
                    "tags": tags, "button": clip_posts.text_for(e["locale"])["button"],
                    "store": carousel_store_url(e, channel), "format": e.get("format")})
    return out


def plan(channel, data, posts, day, slot, check=True):
    """Items to post now, in order, within the platform's daily cap."""
    rule = PLAN[channel]
    today = sum(1 for p in posts if p["channel"] == channel and p.get("posted_at", "").startswith(day.isoformat()))
    room = rule["cap"] - today
    if room <= 0:
        return []
    done = {p["clip"] for p in posts if p["channel"] == channel}
    items = todays_clips(data, posts, channel, day, slot)[:1] if rule["clips"] else []
    if rule["cards"] and slot == 15:
        items += [c for c in todays_cards(day, channel) if c["key"] not in done and (not check or exists(c["image"]))]
    return items[:room]


GOOGLE_PLAY = "Google Play"
URL_IN_TEXT = re.compile(r"https?://\S+")
# Apple's rating link carries the app's id too, but it is not a download link: it never counts as one.
REVIEW_LINK = re.compile(r"https?://[^\s\"'<>]*action=write-review[^\s\"'<>]*")


def fedi_len(text):
    """Mastodon length: every link counts 23 characters, whatever its length."""
    return len(URL_IN_TEXT.sub("x" * 23, text))


def button_of(item):
    """The App Store button label of the item's locale (the feed always carries one)."""
    return item.get("button") or clip_posts.text_for(item.get("locale") or "en")["button"]


def play_of(item):
    """The item's Google Play link, or None when the app is not on Android. An item without one gets it from
    the Android snapshot, with the campaign token of its own App Store link. Raises MissingDownloadLink when
    the snapshot cannot be read or the app is on Android but its link cannot be built: never "iPhone only"
    on a guess (the QA gate turns it into a refusal of that item, the feed leaves it out)."""
    if item.get("play"):
        return item["play"]
    app_id = DL.app_store_id(item.get("store"))
    if not app_id:
        return None
    ct = urllib.parse.parse_qs(urllib.parse.urlsplit(item["store"]).query).get("ct", ["social"])[0]
    try:
        return play_store_url(app_id, ct)
    except ValueError as exc:   # SnapshotMissing is one: the text of these errors never carries a token or URL
        raise DL.MissingDownloadLink(f"the Google Play link cannot be decided: {exc}") from None


def link_lines(item, review=True):
    lines = [f"{button_of(item)}: {item['store']}"]
    play = play_of(item)
    if play:
        lines.append(f"{GOOGLE_PLAY}: {play}")
    return lines + (review_links.lines(item.get("review")) if review else [])


def link_problems(text, item, label):
    """What `text` lacks of the app's download link: its App Store link, and its Google Play link when the app
    is on Android (the rating link does not count)."""
    return DL.link_problems(REVIEW_LINK.sub(" ", text or ""), item.get("store"), play_of(item), label=label)


def with_links(body, item, limit, *, measure=len, review=True, label="post"):
    """`body` followed by the item's download link lines. The body (hashtags first) is trimmed to fit `limit`,
    a link never is; MissingDownloadLink when they cannot fit. The rating lines follow only if they still fit."""
    text = DL.ensure_download_link(body, item.get("store"), play_of(item), max_len=limit, app_store_label=button_of(item),
                                   play_label=GOOGLE_PLAY, measure=measure, label=label)
    extra = review_links.lines(item.get("review")) if review else []
    if extra and measure(text + "\n" + "\n".join(extra)) <= limit:
        text += "\n" + "\n".join(extra)
    return text


def qa_problems(item, channel, online=True):
    """Pre-post QA (post_qa.py) for one feed item on one platform: it checks final_text(), the caption together
    with the download links this platform really receives, not the bare caption."""
    try:
        out = render(item, channel)
    except DL.MissingDownloadLink as exc:
        return [f"{channel} text: {exc}"]
    counted = "counted" in out  # posters that fit the text to the platform limit themselves: measured below
    if item["kind"] == "clip":
        problems = post_qa.clip_problems(item["clip"], channel, out["final"], online=online, length=not counted)
    else:
        problems = post_qa.card_problems(out["final"], item["locale"], channel, store_url=item["store"],
                                         name=item.get("name", ""), online=online, length=not counted)
    limit = post_qa.LIMITS.get(channel)
    if counted and limit and out.get("measure", len)(out["counted"]) > limit:
        problems.append(f"{channel} text is {out.get('measure', len)(out['counted'])} characters; {channel} takes {limit}")
    for name, text in out["checks"]:  # the strict check: the rating link is no download link
        problems += [p for p in link_problems(text, item, f"{channel} {name}") if p not in problems]
    return problems


def final_text(item, channel):
    """Everything the platform's reader gets of this post - caption, link block / first comment / link field /
    link facets - as one string (MissingDownloadLink when the links cannot be attached). The QA gate
    checks this text and the poster sends the same pieces."""
    return render(item, channel)["final"]


def outgoing(item, channel):
    """The pieces to send for this platform (render), after the last link check right before the send call.
    None - after a ::error:: - when the download link is missing or cannot be attached: nothing is sent then."""
    label = f"{channel} {item.get('key', '')}".strip()
    try:
        out = render(item, channel)
    except DL.MissingDownloadLink as exc:
        DL.refuse(label, [str(exc)])
        return None
    problems = []
    for name, text in out["checks"]:
        problems += link_problems(text, item, f"{channel} {name}")
    if problems:
        DL.refuse(label, problems)
        return None
    return out


# ---------------------------------------------------------------- Facebook Page

FB_VER = "v21.0"
FB = f"https://graph.facebook.com/{FB_VER}"


def fb_probe(token, prefer=""):
    """A Page (id, name, access_token) with CREATE_CONTENT behind this user token, or None."""
    try:
        r = http("GET", f"{FB}/me/accounts?fields=id,name,access_token,tasks&access_token={_enc(token)}")
    except RuntimeError as exc:
        print(f"facebook: /me/accounts with IG_ACCESS_TOKEN failed ({exc}); an Instagram-login token "
              "cannot manage Pages, set FB_PAGE_ID and FB_PAGE_TOKEN")
        return None
    pages = [p for p in r.get("data", []) if "CREATE_CONTENT" in (p.get("tasks") or []) and p.get("access_token")]
    pages.sort(key=lambda p: p.get("id") != prefer)
    return pages[0] if pages else None


def fb_creds():
    page, token = env("FB_PAGE_ID"), env("FB_PAGE_TOKEN")
    if page and token:
        return {"page": page, "token": token}
    ig = env("IG_ACCESS_TOKEN")
    found = fb_probe(ig, page) if ig else None
    if not found:
        print("facebook: not configured (no FB_PAGE_ID/FB_PAGE_TOKEN, and IG_ACCESS_TOKEN gives no Page with CREATE_CONTENT)")
        return None
    print(f"facebook: using Page '{found.get('name')}' ({found['id']}) from IG_ACCESS_TOKEN")
    return {"page": found["id"], "token": found["access_token"]}


def render_facebook(item):
    """Reel description = the caption plus every download link written out (Reel captions are not clickable, like
    Instagram's, so the full URLs are text a person can copy); the same links are the first comment (clickable),
    or - if commenting is refused - a link post. All three carry every download link."""
    # The rating lines go only when the Reel description still fits the limit with them: the whole line or none.
    review = len(f"{item['caption']}\n\n" + "\n".join(link_lines(item))) <= post_qa.LIMITS["facebook"]
    comment = "\n".join(link_lines(item, review))
    fallback = "\n".join([item.get("name", ""), item.get("hook", ""), "", *link_lines(item, review)])
    final = f"{item['caption']}\n\n{comment}"
    return {"final": final, "description": final, "comment": comment,
            "fallback": fallback, "link": item["store"],
            "checks": [("reel description", final), ("first comment", comment), ("link post", fallback)]}


def post_facebook(item):
    out = outgoing(item, "facebook")
    if not out:
        return None
    creds = fb_creds()
    if not creds:
        return None
    page, token = creds["page"], creds["token"]
    start = http("POST", f"{FB}/{page}/video_reels", form({"upload_phase": "start", "access_token": token}))
    vid = start["video_id"]
    up = http("POST", start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{FB_VER}/{vid}", b"",
              {"Authorization": f"OAuth {token}", "file_url": item["video"]})
    if not up.get("success"):
        raise RuntimeError(f"Facebook upload failed: {up}")
    http("POST", f"{FB}/{page}/video_reels", form({
        "access_token": token, "video_id": vid, "upload_phase": "finish", "video_state": "PUBLISHED",
        "description": out["description"]}))
    # Links in a Reel caption are not clickable: the store links go in the first
    # comment, or (if commenting is refused) in a link post with a preview.
    try:
        http("POST", f"{FB}/{vid}/comments", form({"message": out["comment"], "access_token": token}))
    except Exception as exc:
        print(f"facebook: comment refused ({exc.__class__.__name__}); posting a link post instead")
        try:
            http("POST", f"{FB}/{page}/feed", form({"message": out["fallback"], "link": out["link"],
                                                     "access_token": token}))
        except Exception as exc2:  # the Reel is up: no repost, but the missing link is loud and left to the sweeper
            DL.refuse("facebook reel", [f"the Reel {vid} is up but neither its link comment nor the link post went out "
                                        f"({exc2.__class__.__name__})"])
    return {"id": vid, "link": f"https://www.facebook.com/reel/{vid}"}


def whoami_facebook():
    page, token = env("FB_PAGE_ID"), env("FB_PAGE_TOKEN")
    if page and token:
        me = http("GET", f"{FB}/{page}?fields=id,name&access_token={_enc(token)}")
        print(f"facebook: FB_PAGE_TOKEN -> Page '{me.get('name')}' ({me.get('id')})")
    ig = env("IG_ACCESS_TOKEN")
    if ig:
        found = fb_probe(ig, page)
        print(f"facebook: IG_ACCESS_TOKEN probe -> {'Page ' + repr(found.get('name')) + ' (' + found['id'] + ') usable' if found else 'no usable Page'}")
    if not (page and token) and not ig:
        print("facebook: not configured")


# ---------------------------------------------------------------- Bluesky

BSKY = "https://bsky.social"
BSKY_VIDEO = "https://video.bsky.app/xrpc"


def bsky_session():
    s = http("POST", f"{BSKY}/xrpc/com.atproto.server.createSession",
             jbody({"identifier": env("BSKY_HANDLE"), "password": env("BSKY_APP_PASSWORD")}),
             {"Content-Type": "application/json"})
    pds = BSKY
    for svc in (s.get("didDoc") or {}).get("service", []):
        if svc.get("id", "").endswith("#atproto_pds"):
            pds = svc.get("serviceEndpoint", BSKY).rstrip("/")
    return {"jwt": s["accessJwt"], "did": s["did"], "handle": s.get("handle") or env("BSKY_HANDLE"), "pds": pds}


def bsky_rich(body, links, limit=300):
    """Text with link facets (UTF-8 byte offsets) on the labels and tag facets on #hashtags (Bluesky only
    indexes a hashtag for search and feeds when it carries a tag facet); body trimmed to fit."""
    tail = "\n\n" + " · ".join(label for label, _ in links)
    if len(body) + len(tail) > limit:
        lines = body.split("\n")
        if lines and lines[-1].startswith("#"):  # drop tags before cutting the problem / benefit lines
            while len(body) + len(tail) > limit and " " in lines[-1]:
                lines[-1] = lines[-1].rsplit(" ", 1)[0]
                body = "\n".join(lines)
    if len(body) + len(tail) > limit:
        body = body[:limit - len(tail) - 1].rstrip() + "…"
    text = body + "\n\n"
    facets = []
    for m in re.finditer(r"(?:^|\s)(#[^\s#…]+)", body):
        start = len(body[:m.start(1)].encode("utf-8"))
        facets.append({"index": {"byteStart": start, "byteEnd": start + len(m.group(1).encode("utf-8"))},
                       "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)[1:]}]})
    for i, (label, uri) in enumerate(links):
        if i:
            text += " · "
        start = len(text.encode("utf-8"))
        text += label
        facets.append({"index": {"byteStart": start, "byteEnd": start + len(label.encode("utf-8"))},
                       "features": [{"$type": "app.bsky.richtext.facet#link", "uri": uri}]})
    return text, facets


def bsky_video(s, data, tries=60):
    host = urllib.parse.urlsplit(s["pds"]).netloc
    auth = http("GET", f"{s['pds']}/xrpc/com.atproto.server.getServiceAuth?aud={_enc('did:web:' + host)}"
                       f"&lxm=com.atproto.repo.uploadBlob&exp={int(time.time()) + 1800}",
                headers={"Authorization": f"Bearer {s['jwt']}"})["token"]
    job = http("POST", f"{BSKY_VIDEO}/app.bsky.video.uploadVideo?did={_enc(s['did'])}&name=clip.mp4", data,
               {"Authorization": f"Bearer {auth}", "Content-Type": "video/mp4"})
    job = job.get("jobStatus", job)
    for _ in range(tries):
        if job.get("blob"):
            return job["blob"]
        if job.get("state") == "JOB_STATE_FAILED":
            raise RuntimeError(f"Bluesky video failed: {job.get('error')}")
        time.sleep(PAUSE)
        job = http("GET", f"{BSKY_VIDEO}/app.bsky.video.getJobStatus?jobId={_enc(job['jobId'])}").get("jobStatus", {})
    raise RuntimeError("Bluesky video processing timed out")


def bsky_links(item, limit=None):
    links = [("App Store", item["store"])]
    if play_of(item):
        links.append((GOOGLE_PLAY, play_of(item)))
    review = item.get("review")
    if review:  # the review sentence is its own link facet, only when the caption still fits whole with it
        tail = "\n\n" + " · ".join(label for label, _ in [*links, (review["label"], review["url"])])
        if len(item.get("caption") or "") + len(tail) <= (limit or post_qa.LIMITS["bluesky"]):
            links.append((review["label"], review["url"]))
    return links


def render_bluesky(item):
    """The links are facets on their labels, so only the labels count towards the 300 characters; the facets'
    URIs are the link field of this post (part of `final`)."""
    limit = post_qa.LIMITS["bluesky"]
    text, facets = bsky_rich(item["caption"], bsky_links(item, limit), limit)
    if len(text) > limit:
        raise DL.MissingDownloadLink(f"bluesky {item.get('key')}: the link labels do not fit {limit} characters")
    uris = [f["features"][0]["uri"] for f in facets if f["features"][0]["$type"].endswith("#link")]
    return {"final": "\n".join([text, *uris]), "counted": text, "text": text, "facets": facets,
            "checks": [("text", "\n".join(uris))]}


def post_bluesky(item):
    out = outgoing(item, "bluesky")
    if not out:
        return None
    s = bsky_session()
    text, facets = out["text"], out["facets"]
    auth = {"Authorization": f"Bearer {s['jwt']}"}
    if item["kind"] == "card":
        blob = http("POST", f"{s['pds']}/xrpc/com.atproto.repo.uploadBlob", to_jpeg(fetch_bytes(item["image"])),
                    {**auth, "Content-Type": "image/jpeg"})["blob"]
        embed = {"$type": "app.bsky.embed.images", "images": [
            {"alt": (item.get("alt") or item["caption"])[:2000], "image": blob,
             "aspectRatio": {"width": 1080, "height": 1350}}]}
    else:
        try:
            embed = {"$type": "app.bsky.embed.video", "video": bsky_video(s, fetch_bytes(item["video"])),
                     "alt": (item.get("alt") or item["hook"])[:2000], "aspectRatio": {"width": 1080, "height": 1920}}
        except Exception as exc:  # no video quota or a processing error: post a link card instead
            print(f"bluesky: video upload failed ({exc}); posting a link card")
            embed = {"$type": "app.bsky.embed.external", "external": {
                "uri": item["store"], "title": item["name"], "description": item["hook"]}}
    record = {"$type": "app.bsky.feed.post", "text": text, "facets": facets, "langs": [item["locale"]],
              "createdAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "embed": embed}
    r = http("POST", f"{s['pds']}/xrpc/com.atproto.repo.createRecord",
             jbody({"repo": s["did"], "collection": "app.bsky.feed.post", "record": record}),
             {**auth, "Content-Type": "application/json"})
    return {"id": r["uri"], "link": f"https://bsky.app/profile/{s['handle']}/post/{r['uri'].rsplit('/', 1)[-1]}"}


def whoami_bluesky():
    s = bsky_session()
    print(f"bluesky: {s['handle']} ({s['did']}) on {s['pds']}")


# ---------------------------------------------------------------- YouTube Shorts

YT_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_LANG = {"zh-Hant": "zh-TW", "pt-BR": "pt-BR"}


def yt_token():
    return http("POST", "https://oauth2.googleapis.com/token", form({
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}))["access_token"]


def yt_text(hook, name, store, play, tags):
    suffix = " #Shorts"
    title = (hook if len(hook) + len(suffix) <= 100 else hook[:100 - len(suffix) - 1] + "…") + suffix
    lines = [hook, "", name, f"App Store: {store}"]
    if play:
        lines.append(f"Google Play: {play}")
    lines += ["", " ".join(["#Shorts", *tags[:3]])]
    return title, "\n".join(lines)


def yt_meta(item):
    """(title, description, tags): search-first for clips (search_caption.youtube), the plain shape otherwise."""
    if item.get("clip"):
        links = [f"App Store: {item['store']}"] + ([f"{GOOGLE_PLAY}: {play_of(item)}"] if play_of(item) else [])
        meta = SC.youtube(item["clip"], item["v"], links + review_links.lines(item.get("review")))
        # The rating lines go only when the description still fits YouTube's limit with them.
        return meta if len(meta[1]) <= post_qa.LIMITS["youtube"] else SC.youtube(item["clip"], item["v"], links)
    title, desc = yt_text(item["hook"], item["name"], item["store"], play_of(item), item["tags"])
    return title, desc, [t.lstrip("#") for t in item["tags"]][:10]


def yt_body(item, data=None):
    title, desc, words = yt_meta(item)
    body = {"snippet": {"title": title, "description": desc, "categoryId": "28", "tags": words,
                        "defaultLanguage": YT_LANG.get(item["locale"], item["locale"])},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    # The same app's other locales become YouTube localizations of this Short.
    locs = {}
    for clip in (data or {}).get("clips", {}).values():
        if clip["app"] == item["app"] and clip["locale"] != item["locale"]:
            other = clip_item(f"{clip['app']}/{clip['locale']}", clip, "youtube")
            t, d, _ = yt_meta(other)
            problems = link_problems(d, other, f"youtube localization {clip['locale']}")
            if problems:  # a translation without the download link is left out; the post itself is checked apart
                DL.refuse(f"youtube {item.get('key')}", problems)
                continue
            locs[YT_LANG.get(clip["locale"], clip["locale"])] = {"title": t, "description": d}
    if locs:
        body["localizations"] = locs
    return body


def render_youtube(item):
    title, desc, words = yt_meta(item)
    return {"final": desc, "title": title, "description": desc, "tags": words, "checks": [("description", desc)]}


def post_youtube(item, data=None):
    if not outgoing(item, "youtube"):
        return None
    token = yt_token()
    video = fetch_bytes(item["video"])
    body = yt_body(item, data)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
               "X-Upload-Content-Length": str(len(video)), "X-Upload-Content-Type": "video/mp4"}

    def start(b):
        parts = "snippet,status" + (",localizations" if "localizations" in b else "")
        return http("POST", f"{YT_UPLOAD}?uploadType=resumable&part={parts}", jbody(b), headers, raw=True)[1]["location"]

    try:
        location = start(body)
    except RuntimeError as exc:
        if "localizations" not in body:
            raise
        print(f"youtube: localizations refused ({exc}); uploading without them")
        body.pop("localizations")
        location = start(body)
    r = http("PUT", location, video, {"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"}, timeout=600)
    privacy = (r.get("status") or {}).get("privacyStatus", "?")
    print(f"youtube: uploaded {r['id']} ({privacy}); uploads from an unaudited API project stay private "
          "until the project passes YouTube's API audit")
    return {"id": r["id"], "link": f"https://youtube.com/shorts/{r['id']}"}


def whoami_youtube():
    token = yt_token()
    r = http("GET", "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
             headers={"Authorization": f"Bearer {token}"})
    names = [c["snippet"]["title"] for c in r.get("items", [])]
    print(f"youtube: channel {', '.join(names) or '(none)'}")


# ---------------------------------------------------------------- Pinterest

PIN = "https://api.pinterest.com/v5"
PIN_BOARD = "Lumi Apps"


def pin_token():
    token = env("PINTEREST_TOKEN")
    refresh, app, secret = env("PINTEREST_REFRESH_TOKEN"), env("PINTEREST_APP_ID"), env("PINTEREST_APP_SECRET")
    if refresh and app and secret:
        basic = base64.b64encode(f"{app}:{secret}".encode()).decode()
        try:
            token = http("POST", f"{PIN}/oauth/token", form({"grant_type": "refresh_token", "refresh_token": refresh}),
                         {"Authorization": f"Basic {basic}"}).get("access_token") or token
        except RuntimeError as exc:
            print(f"pinterest: token refresh skipped ({exc})")
    return token


def pin_board(auth):
    if env("PINTEREST_BOARD_ID"):
        return env("PINTEREST_BOARD_ID")
    for board in http("GET", f"{PIN}/boards?page_size=100", headers=auth).get("items", []):
        if board.get("name", "").lower() == PIN_BOARD.lower():
            return board["id"]
    return http("POST", f"{PIN}/boards", jbody({"name": PIN_BOARD, "privacy": "PUBLIC",
                                                "description": "Small, useful iPhone and Android apps"}),
                {**auth, "Content-Type": "application/json"})["id"]


def render_pinterest(item):
    """A pin has one link field (the App Store page); Google Play, which cannot go there, is written into the
    description with the App Store link too, so the text alone carries every download link (800 characters)."""
    desc = with_links(item["caption"], item, post_qa.LIMITS["pinterest"], review=False, label=f"pinterest {item.get('key')}")
    return {"final": f"{desc}\n{item['store']}", "counted": desc, "description": desc, "link": item["store"],
            "checks": [("description", desc)]}


def post_pinterest(item, tries=60):
    out = outgoing(item, "pinterest")
    if not out:
        return None
    auth = {"Authorization": f"Bearer {pin_token()}"}
    board = pin_board(auth)
    pin = {"board_id": board, "link": out["link"], "title": item["title"][:100],
           "description": out["description"], "alt_text": (item.get("alt") or item["hook"])[:500]}
    if item["kind"] == "card":
        pin["media_source"] = {"source_type": "image_url", "url": item["image"]}
    else:
        media = http("POST", f"{PIN}/media", jbody({"media_type": "video"}), {**auth, "Content-Type": "application/json"})
        params = list((media.get("upload_parameters") or {}).items())
        body, ctype = multipart(params + [("file", fetch_bytes(item["video"]), "clip.mp4", "video/mp4")])
        http("POST", media["upload_url"], body, {"Content-Type": ctype})
        for _ in range(tries):
            status = http("GET", f"{PIN}/media/{media['media_id']}", headers=auth).get("status")
            if status == "succeeded":
                break
            if status == "failed":
                raise RuntimeError("Pinterest could not process the video")
            time.sleep(PAUSE)
        else:
            raise RuntimeError("Pinterest video processing timed out")
        pin["media_source"] = {"source_type": "video_id", "media_id": media["media_id"], "cover_image_key_frame_time": 1}
    r = http("POST", f"{PIN}/pins", jbody(pin), {**auth, "Content-Type": "application/json"})
    return {"id": r["id"], "link": f"https://www.pinterest.com/pin/{r['id']}/"}


def whoami_pinterest():
    r = http("GET", f"{PIN}/user_account", headers={"Authorization": f"Bearer {pin_token()}"})
    print(f"pinterest: {r.get('username')} ({r.get('account_type')})")


# ---------------------------------------------------------------- Tumblr

TUMBLR = "https://api.tumblr.com/v2"


def tumblr_blog():
    blog = re.sub(r"^https?://", "", env("TUMBLR_BLOG")).strip("/")
    return blog if "." in blog else f"{blog}.tumblr.com"


def tumblr_auth(method, url, params=None):
    return oauth1_header(method, url, env("TUMBLR_CONSUMER_KEY"), env("TUMBLR_CONSUMER_SECRET"),
                         env("TUMBLR_TOKEN"), env("TUMBLR_TOKEN_SECRET"), params)


def text_link_block(label, url):
    return {"type": "text", "text": label, "formatting": [{"start": 0, "end": len(label), "type": "link", "url": url}]}


def tumblr_content(item):
    """The post's NPF blocks: caption, the media, the App Store link block and the Google Play link text."""
    if item["kind"] == "card":
        media = {"type": "image", "media": [{"type": "image/jpeg", "identifier": "media0", "width": 1080, "height": 1350}],
                 "alt_text": (item.get("alt") or item["hook"])[:4096]}
    else:
        media = {"type": "video", "media": {"type": "video/mp4", "identifier": "media0", "width": 1080, "height": 1920}}
    content = [{"type": "text", "text": item["caption"]}, media,
               {"type": "link", "url": item["store"], "title": item["name"], "description": item["hook"]}]
    if item["kind"] == "clip":  # keyword-rich heading: Tumblr search reads post text and the first tags
        content.insert(0, {"type": "text", "subtype": "heading2", "text": item["title"]})
    if play_of(item):
        content.append(text_link_block(GOOGLE_PLAY, play_of(item)))
    return content


def npf_text(content):
    """The text of NPF blocks as one string: the text blocks (the heading aside) and the URL of every link
    block or linked text."""
    out = []
    for block in content:
        if block.get("type") == "text" and block.get("subtype") != "heading2":
            out.append(block["text"])
            out += [f["url"] for f in block.get("formatting", []) if f.get("type") == "link"]
        elif block.get("type") == "link":
            out.append(block["url"])
    return "\n".join(out)


def render_tumblr(item):
    content = tumblr_content(item)
    text = npf_text(content)
    return {"final": text, "content": content, "checks": [("text", text)]}


def post_tumblr(item):
    out = outgoing(item, "tumblr")
    if not out:
        return None
    blog = tumblr_blog()
    if item["kind"] == "card":
        upload = ("media0", fetch_bytes(item["image"]), "card.jpg", "image/jpeg")
    else:
        upload = ("media0", fetch_bytes(item["video"]), "clip.mp4", "video/mp4")
    payload = {"content": out["content"], "state": "published",
               "tags": ",".join(t.lstrip("#") for t in item["tags"][:5])}
    body, ctype = multipart([("json", jbody(payload), None, "application/json"), upload])
    url = f"{TUMBLR}/blog/{blog}/posts"
    r = http("POST", url, body, {"Authorization": tumblr_auth("POST", url), "Content-Type": ctype}, timeout=600)
    pid = str(r["response"].get("id_string") or r["response"]["id"])
    name = blog[:-len(".tumblr.com")] if blog.endswith(".tumblr.com") else None
    return {"id": pid, "link": f"https://www.tumblr.com/{name}/{pid}" if name else f"https://{blog}/post/{pid}"}


def whoami_tumblr():
    url = f"{TUMBLR}/user/info"
    user = http("GET", url, headers={"Authorization": tumblr_auth("GET", url)})["response"]["user"]
    print(f"tumblr: {user.get('name')} blogs {', '.join(b.get('name', '') for b in user.get('blogs', []))}; posting to {tumblr_blog()}")


# ---------------------------------------------------------------- Naver Blog (ko)

NAVER = "https://api.blog.naver.com/xmlrpc"


def naver_call(method, *params):
    body = xmlrpc.client.dumps(params, method, allow_none=False).encode("utf-8")
    raw = http("POST", NAVER, body, {"Content-Type": "text/xml; charset=utf-8"}, raw=True)[2]
    try:
        return xmlrpc.client.loads(raw)[0][0]
    except xmlrpc.client.Fault as fault:
        raise RuntimeError(f"Naver fault {fault.faultCode}: {fault.faultString}") from None


def naver_links(item):
    links = [(button_of(item), item["store"])]
    if play_of(item):
        links.append(("Google Play에서 받기", play_of(item)))
    return links


def naver_review(item, base):
    """The item's rating link when `base` (the post without it) still fits Naver's limit with it, else None."""
    review = item.get("review")
    if review and len(base) + len("\n".join(["", *review_links.lines(review)])) <= post_qa.LIMITS["naver"]:
        return review
    return None


def naver_body(item, media):
    text = "<br>".join(html.escape(line) for line in item["caption"].split("\n"))
    links = " · ".join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in naver_links(item))
    body = f"<p>{text}</p>{media}<p>{links}</p>"
    review = item.get("review")
    if review:  # the whole paragraph, only when the HTML still fits Naver's limit with it
        para = (f'<p><a href="{html.escape(review["url"])}" rel="nofollow">'
                f'{html.escape(review["label"])}</a></p>')
        if len(body) + len(para) <= post_qa.LIMITS["naver"]:
            body += para
    return body


def render_naver(item):
    text = "\n".join([item["caption"], *(f"{label}: {url}" for label, url in naver_links(item))])
    review = naver_review(item, text)
    if review:
        text = "\n".join([text, *review_links.lines(review)])
    return {"final": text, "checks": [("text", text)]}


def post_naver(item):
    if not outgoing(item, "naver"):
        return None
    nid, pw = env("NAVER_ID"), env("NAVER_BLOG_API_PASSWORD")
    if item["kind"] == "card":
        up = naver_call("metaWeblog.newMediaObject", nid, nid, pw, {
            "name": f"{item['key'].replace('/', '_')}.jpg", "type": "image/jpeg",
            "bits": xmlrpc.client.Binary(fetch_bytes(item["image"]))})
        media = f'<p><img src="{html.escape(up["url"])}" alt="{html.escape(item["hook"])}"></p>'
    else:
        src = html.escape(item["video"])
        media = (f'<p><video src="{src}" controls playsinline width="360"></video></p>'
                 f'<p><a href="{src}">▶ 영상 보기</a></p>')
    body = naver_body(item, media)
    problems = link_problems(body, item, "naver html")  # the HTML that is sent
    if problems:
        return DL.refuse(f"naver {item.get('key')}", problems) or None
    postid = naver_call("metaWeblog.newPost", nid, nid, pw, {"title": f"{item['name']} — {item['title']}", "description": body}, True)
    return {"id": str(postid), "link": f"https://blog.naver.com/{nid}/{postid}"}


def whoami_naver():
    blogs = naver_call("blogger.getUsersBlogs", "", env("NAVER_ID"), env("NAVER_BLOG_API_PASSWORD"))
    print(f"naver: {', '.join(b.get('url', b.get('blogName', '')) for b in blogs) if isinstance(blogs, list) else blogs}")


# ---------------------------------------------------------------- Plurk (zh-Hant)

PLURK = "https://www.plurk.com/APP"


def plurk_call(path, params=None, files=None):
    url = PLURK + path
    sign = lambda p: oauth1_header("POST", url, env("PLURK_APP_KEY"), env("PLURK_APP_SECRET"),
                                   env("PLURK_TOKEN"), env("PLURK_TOKEN_SECRET"), p)
    if files:
        body, ctype = multipart(files)
        return http("POST", url, body, {"Authorization": sign({}), "Content-Type": ctype})
    params = params or {}
    return http("POST", url, form(params), {"Authorization": sign(params),
                                            "Content-Type": "application/x-www-form-urlencoded"})


def base36(n):
    digits, out = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    n = int(n)
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if not n:
            return out


def plurk_content(item, media, limit=360):
    """The plurk: the caption, then the media link and every download link. The links come first and are never
    cut: the caption is trimmed to what is left of the limit (MissingDownloadLink when not even they fit).
    The rating link (every App) follows Google Play only if the caption still fits whole with it."""
    tail = f"\n{media}\n{item['store']} ({button_of(item)})"
    if play_of(item):
        tail += f"\n{play_of(item)} ({GOOGLE_PLAY})"
    if len(tail) > limit:
        raise DL.MissingDownloadLink(f"plurk {item.get('key')}: the download links ({len(tail)} chars) do not fit {limit}")
    review = "\n".join(["", *review_links.lines(item.get("review"))]) if item.get("review") else ""
    # Only when the caption still fits whole with it: the rating link never costs a character of the caption.
    if review and len(tail) + len(review) < limit - 40 and len(item["caption"]) + len(tail) + len(review) <= limit:
        tail += review
    return fit_head(item["caption"], limit - len(tail)) + tail


def fit_head(head, room):
    """`head` cut to `room` characters: the trailing hashtag lines go first (a hashtag cut in half is no tag),
    then the text itself, ending in an ellipsis."""
    if len(head) <= room:
        return head
    lines = head.rstrip().split("\n")
    while lines and (not lines[-1].strip() or DL.HASHTAG_LINE.match(lines[-1])):
        lines.pop()
        trimmed = "\n".join(lines).rstrip()
        if len(trimmed) <= room:
            return trimmed
    body = "\n".join(lines).rstrip()
    return body[:room - 1].rstrip() + "…" if room >= 2 else ""


def render_plurk(item):
    """The media link is the card's uploaded picture (known after the upload): the clip / card URL stands in."""
    content = plurk_content(item, item.get("video") or item.get("image") or "", post_qa.LIMITS["plurk"])
    return {"final": content, "counted": content, "checks": [("text", content)]}


def post_plurk(item, limit=360):
    if not outgoing(item, "plurk"):
        return None
    if item["kind"] == "card":
        media = plurk_call("/Timeline/uploadPicture", files=[("image", fetch_bytes(item["image"]), "card.jpg", "image/jpeg")])["full"]
    else:
        media = item["video"]
    try:
        content = plurk_content(item, media, limit)
    except DL.MissingDownloadLink as exc:
        return DL.refuse(f"plurk {item.get('key')}", [str(exc)]) or None
    problems = link_problems(content, item, "plurk text")
    if problems:
        return DL.refuse(f"plurk {item.get('key')}", problems) or None
    r = plurk_call("/Timeline/plurkAdd", {"content": content, "qualifier": "shares", "lang": "tr_ch"})
    return {"id": str(r["plurk_id"]), "link": f"https://www.plurk.com/p/{base36(r['plurk_id'])}"}


def whoami_plurk():
    r = plurk_call("/Users/me")
    print(f"plurk: {r.get('nick_name')} ({r.get('display_name')})")


# ---------------------------------------------------------------- Dailymotion

DM = "https://api.dailymotion.com"


def dm_token():
    return http("POST", f"{DM}/oauth/token", form({
        "grant_type": "password", "client_id": env("DM_API_KEY"), "client_secret": env("DM_API_SECRET"),
        "username": env("DM_USERNAME"), "password": env("DM_PASSWORD"), "scope": "manage_videos"}))["access_token"]


def render_dailymotion(item):
    desc = with_links(item["caption"], item, post_qa.LIMITS["dailymotion"], label=f"dailymotion {item.get('key')}")
    return {"final": desc, "description": desc, "checks": [("description", desc)]}


def post_dailymotion(item):
    out = outgoing(item, "dailymotion")
    if not out:
        return None
    auth = {"Authorization": f"Bearer {dm_token()}"}
    r = http("POST", f"{DM}/me/videos", form({
        "url": item["video"], "title": f"{item['hook']} | {item['name']}"[:255], "description": out["description"],
        "tags": ",".join(t.lstrip("#") for t in item["tags"][:5]), "channel": "tech", "published": "true",
        "is_created_for_kids": "false"}), auth)
    return {"id": r["id"], "link": f"https://www.dailymotion.com/video/{r['id']}"}


def whoami_dailymotion():
    r = http("GET", f"{DM}/me?fields=id,username,screenname", headers={"Authorization": f"Bearer {dm_token()}"})
    print(f"dailymotion: {r.get('username')} ({r.get('screenname')})")


# ---------------------------------------------------------------- more platforms (owner 2026-10-22: 50 platforms)
#
# Owner 2026-10-22: "所有社群跟影片我要求你每天至少發五十個通路" -> 50 different platforms posting every day.
# Each one below is secret-gated like the rest (not configured -> logged, nothing sent) and goes through the same
# render() / outgoing() / QA gate: the App Store link (+ Google Play when the app is on Android) in the text that
# is really sent. The Mac opens the accounts with its signed-in browser and sets the secrets
# (00_GrowthEngine ops/handoff/LOCAL_QUEUE_2026-10-22_platform50.md); then `social-extra.yml` channel=<name>
# mode=whoami / post reads them back.

def media_url(item):
    return item.get("video") or item.get("image") or ""


def blog_title(item):
    return f"{item['name']} — {item['title']}"[:200]


def link_pairs(item, review=True):
    """(label, url) of every link a blog post carries: App Store, Google Play when on Android, then the rating
    link (never a download link)."""
    pairs = [(button_of(item), item["store"])]
    play = play_of(item)
    if play:
        pairs.append((GOOGLE_PLAY, play))
    if review and item.get("review"):
        pairs.append((item["review"]["label"], item["review"]["url"]))
    return pairs


def blog_markdown(item):
    if item["kind"] == "card":
        media = f"![{(item.get('alt') or item['hook']).replace(']', ')')}]({item['image']})"
    else:
        media = f"[▶ {item['hook']}]({item['video']})"
    links = "\n".join(f"- [{label}]({url})" for label, url in link_pairs(item))
    return "\n\n".join([item["caption"], media, links])


def blog_html(item):
    text = "<br>".join(html.escape(line) for line in item["caption"].split("\n"))
    if item["kind"] == "card":
        media = f'<p><img src="{html.escape(item["image"])}" alt="{html.escape(item.get("alt") or item["hook"])}"></p>'
    else:
        src = html.escape(item["video"])
        media = (f'<p><video src="{src}" controls playsinline width="360"></video></p>'
                 f'<p><a href="{src}">▶ {html.escape(item["hook"])}</a></p>')
    links = "<br>".join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in link_pairs(item))
    return f"<p>{text}</p>{media}<p>{links}</p>"


def html_text(body):
    """What a reader gets of an HTML body, link targets included (for the link check of the HTML sent)."""
    hrefs = re.findall(r'href="([^"]+)"', body)
    return "\n".join([re.sub(r"<[^>]+>", " ", body), *(html.unescape(h) for h in hrefs)])


def render_blog(item, fmt):
    body = blog_markdown(item) if fmt == "markdown" else blog_html(item)
    final = "\n".join([item["caption"], media_url(item), *(f"{label}: {url}" for label, url in link_pairs(item))])
    shown = body if fmt == "markdown" else html_text(body)
    return {"final": final, "title": blog_title(item), "body": body, "checks": [("body", shown)]}


def render_microblog(item, channel, media_line=True):
    """Caption + download links within the platform's limit (hashtags give way first, a link never), then the
    clip's video link when it still fits (media_line=False: the platform gets the video itself)."""
    limit = post_qa.LIMITS[channel]
    text = with_links(item["caption"], item, limit, label=f"{channel} {item.get('key')}")
    if media_line and item["kind"] == "clip" and len(text) + len(item["video"]) + 3 <= limit:
        text += f"\n▶ {item['video']}"
    return {"final": text, "counted": text, "text": text, "checks": [("text", text)]}


# Misskey (misskey.io, Japan's largest fediverse server): notes API with an access token (Settings -> API).
def misskey_host():
    return "https://" + re.sub(r"^https?://", "", env("MISSKEY_HOST") or "misskey.io").strip("/")


def misskey_call(path, payload):
    return http("POST", f"{misskey_host()}/api/{path}", jbody({"i": env("MISSKEY_TOKEN"), **payload}),
                {"Content-Type": "application/json"})


def render_misskey(item):
    return render_microblog(item, "misskey")


def post_misskey(item):
    out = outgoing(item, "misskey")
    if not out:
        return None
    files = []
    if item["kind"] == "card":
        body, ctype = multipart([("i", env("MISSKEY_TOKEN")),
                                 ("file", to_jpeg(fetch_bytes(item["image"])), "card.jpg", "image/jpeg")])
        files = [http("POST", f"{misskey_host()}/api/drive/files/create", body, {"Content-Type": ctype})["id"]]
    note = misskey_call("notes/create", {"text": out["text"], "visibility": "public", **({"fileIds": files} if files else {})})
    nid = note["createdNote"]["id"]
    return {"id": nid, "link": f"{misskey_host()}/notes/{nid}"}


def whoami_misskey():
    me = misskey_call("i", {})
    print(f"misskey: @{me.get('username')} on {misskey_host()}")


# Pixelfed (pixelfed.social, photo fediverse): Mastodon-compatible API with a personal access token.
def pixelfed_host():
    return "https://" + re.sub(r"^https?://", "", env("PIXELFED_HOST") or "pixelfed.social").strip("/")


def render_pixelfed(item):
    return render_microblog(item, "pixelfed", media_line=False)


def post_pixelfed(item):
    out = outgoing(item, "pixelfed")
    if not out:
        return None
    auth = {"Authorization": f"Bearer {env('PIXELFED_TOKEN')}"}
    if item["kind"] == "card":
        upload = ("file", to_jpeg(fetch_bytes(item["image"])), "card.jpg", "image/jpeg")
    else:
        upload = ("file", fetch_bytes(item["video"]), "clip.mp4", "video/mp4")
    body, ctype = multipart([upload, ("description", (item.get("alt") or item["hook"])[:1000])])
    media = http("POST", f"{pixelfed_host()}/api/v1/media", body, {**auth, "Content-Type": ctype}, timeout=600)
    r = http("POST", f"{pixelfed_host()}/api/v1/statuses",
             jbody({"status": out["text"], "media_ids": [media["id"]], "visibility": "public"}),
             {**auth, "Content-Type": "application/json"})
    return {"id": str(r["id"]), "link": r.get("url") or f"{pixelfed_host()}/p/{r['id']}"}


def whoami_pixelfed():
    me = http("GET", f"{pixelfed_host()}/api/v1/accounts/verify_credentials",
              headers={"Authorization": f"Bearer {env('PIXELFED_TOKEN')}"})
    print(f"pixelfed: @{me.get('username')} on {pixelfed_host()}")


# Telegraph (telegra.ph, Telegram's instant-view pages; no sign-up: createAccount gives the token).
TELEGRAPH = "https://api.telegra.ph"


def telegraph_nodes(item):
    nodes = [{"tag": "p", "children": [line]} for line in item["caption"].split("\n") if line.strip()]
    if item["kind"] == "card":
        nodes.append({"tag": "figure", "children": [{"tag": "img", "attrs": {"src": item["image"]}}]})
    else:
        nodes.append({"tag": "p", "children": [{"tag": "a", "attrs": {"href": item["video"]}, "children": [f"▶ {item['hook']}"]}]})
    for label, url in link_pairs(item):
        nodes.append({"tag": "p", "children": [{"tag": "a", "attrs": {"href": url}, "children": [label]}]})
    return nodes


def nodes_text(nodes):
    out = []
    for node in nodes:
        for child in node.get("children", []):
            if isinstance(child, str):
                out.append(child)
            else:
                out += [child.get("attrs", {}).get("href", ""), *[c for c in child.get("children", []) if isinstance(c, str)]]
    return "\n".join(x for x in out if x)


def render_telegraph(item):
    nodes = telegraph_nodes(item)
    out = render_blog(item, "markdown")
    return dict(out, nodes=nodes, checks=[("page", nodes_text(nodes))])


def post_telegraph(item):
    out = outgoing(item, "telegraph")
    if not out:
        return None
    r = http("POST", f"{TELEGRAPH}/createPage", form({
        "access_token": env("TELEGRAPH_TOKEN"), "title": out["title"][:256], "author_name": "Lumi Apps",
        "author_url": "https://open.cait518.cc/ig/", "content": json.dumps(out["nodes"], ensure_ascii=False)}))
    if not r.get("ok"):
        raise RuntimeError(f"telegraph: {r.get('error')}")
    return {"id": r["result"]["path"], "link": r["result"]["url"]}


def whoami_telegraph():
    r = http("GET", f"{TELEGRAPH}/getAccountInfo?" + urllib.parse.urlencode({"access_token": env("TELEGRAPH_TOKEN")}))
    print(f"telegraph: {r.get('result', {}).get('short_name')}")


# Write.as (write.as / WriteFreely, federated long-form): API token from POST /api/auth/login.
WRITEAS = "https://write.as/api"


def render_writeas(item):
    return render_blog(item, "markdown")


def post_writeas(item):
    out = outgoing(item, "writeas")
    if not out:
        return None
    blog = env("WRITEAS_BLOG")
    url = f"{WRITEAS}/collections/{blog}/posts" if blog else f"{WRITEAS}/posts"
    r = http("POST", url, jbody({"title": out["title"], "body": out["body"], "lang": (item["locale"] or "en").split("-")[0]}),
             {"Authorization": f"Token {env('WRITEAS_TOKEN')}", "Content-Type": "application/json"})["data"]
    link = f"https://write.as/{blog}/{r['slug']}" if blog and r.get("slug") else f"https://write.as/{r['id']}"
    return {"id": r["id"], "link": link}


def whoami_writeas():
    me = http("GET", f"{WRITEAS}/me", headers={"Authorization": f"Token {env('WRITEAS_TOKEN')}"})
    print(f"writeas: {me.get('data', {}).get('username')} blog {env('WRITEAS_BLOG') or '(anonymous posts)'}")


# Hatena Blog (Japan): AtomPub with the blog's API key (Settings -> 詳細設定 -> AtomPub).
def hatena_root():
    return f"https://blog.hatena.ne.jp/{env('HATENA_ID')}/{env('HATENA_BLOG_ID')}/atom"


def hatena_auth():
    token = base64.b64encode(f"{env('HATENA_ID')}:{env('HATENA_API_KEY')}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def render_hatena(item):
    return render_blog(item, "html")


def post_hatena(item):
    out = outgoing(item, "hatena")
    if not out:
        return None
    cats = "".join(f'<category term="{html.escape(t.lstrip("#"))}" />' for t in item["tags"][:5])
    entry = ('<?xml version="1.0" encoding="utf-8"?>'
             '<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">'
             f'<title>{html.escape(out["title"])}</title><author><name>{html.escape(env("HATENA_ID"))}</name></author>'
             f'<content type="text/html">{html.escape(out["body"])}</content>{cats}'
             '<app:control><app:draft>no</app:draft></app:control></entry>')
    raw = http("POST", f"{hatena_root()}/entry", entry.encode("utf-8"),
               {**hatena_auth(), "Content-Type": "application/xml; charset=utf-8"}, raw=True)[2].decode("utf-8", "replace")
    link = re.search(r'<link rel="alternate" type="text/html" href="([^"]+)"', raw)
    eid = re.search(r"<id>([^<]+)</id>", raw)
    if not link:
        raise RuntimeError("hatena: no entry link in the answer")
    return {"id": eid.group(1) if eid else link.group(1), "link": html.unescape(link.group(1))}


def whoami_hatena():
    raw = http("GET", hatena_root(), headers=hatena_auth(), raw=True)[2].decode("utf-8", "replace")
    title = re.search(r"<atom:title>([^<]+)</atom:title>|<title>([^<]+)</title>", raw)
    print(f"hatena: {env('HATENA_ID')} / {env('HATENA_BLOG_ID')} {(title.group(1) or title.group(2)) if title else ''}")


# WordPress.com (free blog; REST v1.1 with an OAuth2 token of the site's own app).
WPCOM = "https://public-api.wordpress.com/rest/v1.1"


def render_wordpress(item):
    return render_blog(item, "html")


def post_wordpress(item):
    out = outgoing(item, "wordpress")
    if not out:
        return None
    r = http("POST", f"{WPCOM}/sites/{urllib.parse.quote(env('WPCOM_SITE'), safe='')}/posts/new", form({
        "title": out["title"], "content": out["body"], "status": "publish",
        "tags": ",".join(t.lstrip("#") for t in item["tags"][:5])}), {"Authorization": f"Bearer {env('WPCOM_TOKEN')}"})
    return {"id": str(r["ID"]), "link": r["URL"]}


def whoami_wordpress():
    me = http("GET", f"{WPCOM}/me", headers={"Authorization": f"Bearer {env('WPCOM_TOKEN')}"})
    print(f"wordpress: {me.get('username')} site {env('WPCOM_SITE')}")


# Blogger (Google): the Mac's Google OAuth client with the blogger scope (refresh token BLOGGER_REFRESH_TOKEN).
BLOGGER = "https://www.googleapis.com/blogger/v3"


def blogger_token():
    return http("POST", "https://oauth2.googleapis.com/token", form({
        "client_id": env("BLOGGER_CLIENT_ID") or env("YT_CLIENT_ID"),
        "client_secret": env("BLOGGER_CLIENT_SECRET") or env("YT_CLIENT_SECRET"),
        "refresh_token": env("BLOGGER_REFRESH_TOKEN"), "grant_type": "refresh_token"}))["access_token"]


def render_blogger(item):
    return render_blog(item, "html")


def post_blogger(item):
    out = outgoing(item, "blogger")
    if not out:
        return None
    r = http("POST", f"{BLOGGER}/blogs/{env('BLOGGER_BLOG_ID')}/posts/",
             jbody({"kind": "blogger#post", "title": out["title"], "content": out["body"],
                    "labels": [t.lstrip("#") for t in item["tags"][:5]]}),
             {"Authorization": f"Bearer {blogger_token()}", "Content-Type": "application/json"})
    return {"id": str(r["id"]), "link": r["url"]}


def whoami_blogger():
    r = http("GET", f"{BLOGGER}/blogs/{env('BLOGGER_BLOG_ID')}", headers={"Authorization": f"Bearer {blogger_token()}"})
    print(f"blogger: {r.get('name')} {r.get('url')}")


# WhiteWind (whtwnd.com, Markdown blog on the AT Protocol): the Bluesky account's app password.
def render_whitewind(item):
    return render_blog(item, "markdown")


def post_whitewind(item):
    out = outgoing(item, "whitewind")
    if not out:
        return None
    s = bsky_session()
    record = {"$type": "com.whtwnd.blog.entry", "title": out["title"], "content": out["body"],
              "createdAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "visibility": "public"}
    r = http("POST", f"{s['pds']}/xrpc/com.atproto.repo.createRecord",
             jbody({"repo": s["did"], "collection": "com.whtwnd.blog.entry", "record": record}),
             {"Authorization": f"Bearer {s['jwt']}", "Content-Type": "application/json"})
    rkey = r["uri"].rsplit("/", 1)[-1]
    return {"id": r["uri"], "link": f"https://whtwnd.com/{s['handle']}/{rkey}"}


def whoami_whitewind():
    s = bsky_session()
    print(f"whitewind: {s['handle']} ({s['did']})")


# ---------------------------------------------------------------- what really goes out

def render_mastodon(item):
    """Posted by threads-autopilot from the feed: the caption plus the download links, counted the Mastodon way
    (every link 23 characters, 500 in all)."""
    text = with_links(item["caption"], item, post_qa.LIMITS["mastodon"], measure=fedi_len, review=False,
                      label=f"mastodon {item.get('key')}")
    return {"final": text, "counted": text, "measure": fedi_len, "text": text, "checks": [("text", text)]}


def render_tiktok(item):
    """Posted by the Mac from the feed: TikTok caption links cannot be tapped, so every download link is written
    out in full after the caption (hashtags give way first; 2200 characters in all)."""
    text = with_links(item["caption"], item, post_qa.LIMITS["tiktok"], review=False, label=f"tiktok {item.get('key')}")
    return {"final": text, "counted": text, "caption": text, "checks": [("caption", text)]}


RENDER = {"facebook": render_facebook, "bluesky": render_bluesky, "youtube": render_youtube,
          "pinterest": render_pinterest, "tumblr": render_tumblr, "naver": render_naver, "plurk": render_plurk,
          "dailymotion": render_dailymotion, "mastodon": render_mastodon, "tiktok": render_tiktok,
          "misskey": render_misskey, "pixelfed": render_pixelfed, "telegraph": render_telegraph,
          "writeas": render_writeas, "hatena": render_hatena, "wordpress": render_wordpress,
          "blogger": render_blogger, "whitewind": render_whitewind}


def render(item, channel):
    """Every piece `channel` receives for this item (see final_text); MissingDownloadLink when the app has no
    valid App Store link or the links cannot be attached within the platform's limit."""
    if not DL.app_store_id(item.get("store")):
        raise DL.MissingDownloadLink(f"no App Store link known for this app: {item.get('store')!r}")
    return RENDER[channel](item)


# ---------------------------------------------------------------- runner

POSTERS = {"facebook": post_facebook, "bluesky": post_bluesky, "youtube": post_youtube, "pinterest": post_pinterest,
           "tumblr": post_tumblr, "naver": post_naver, "plurk": post_plurk, "dailymotion": post_dailymotion,
           "misskey": post_misskey, "pixelfed": post_pixelfed, "telegraph": post_telegraph, "writeas": post_writeas,
           "hatena": post_hatena, "wordpress": post_wordpress, "blogger": post_blogger, "whitewind": post_whitewind}
WHOAMI = {"facebook": whoami_facebook, "bluesky": whoami_bluesky, "youtube": whoami_youtube,
          "pinterest": whoami_pinterest, "tumblr": whoami_tumblr, "naver": whoami_naver, "plurk": whoami_plurk,
          "dailymotion": whoami_dailymotion, "misskey": whoami_misskey, "pixelfed": whoami_pixelfed,
          "telegraph": whoami_telegraph, "writeas": whoami_writeas, "hatena": whoami_hatena,
          "wordpress": whoami_wordpress, "blogger": whoami_blogger, "whitewind": whoami_whitewind}


def whoami(channels):
    for ch in channels:
        if not configured(ch):
            print(not_configured(ch))
            continue
        try:
            WHOAMI[ch]()
        except Exception as exc:
            print(f"::warning::{ch}: whoami failed ({exc})")
    return 0


def run(channels, day, slot, dry_run=False, data=None):
    data = data if data is not None else clip_posts.load()
    posts = load_posts()
    posted_any = False
    for ch in channels:
        if not dry_run and CR.paused_notice(ch):  # channel rotation holdout week: only this channel sits out
            continue
        ok = configured(ch)
        if not ok and not dry_run:
            print(not_configured(ch))
            continue
        try:
            items = plan(ch, data, posts, day, slot, check=not dry_run)
        except Exception as exc:
            print(f"::warning::{ch}: planning failed ({exc})")
            continue
        if not items:
            print(f"{ch}: nothing to post (cap reached or nothing new)")
        for item in items:
            if dry_run:
                state = "" if ok else " [not configured]"
                print(f"{ch}{state}: would post {item['kind']} {item['key']} ({item['locale']}) -> {item['store']}")
                if play_of(item):
                    print(f"  Google Play -> {play_of(item)}")
                try:
                    shown = final_text(item, ch)
                except DL.MissingDownloadLink as exc:
                    shown = f"[no download link: {exc}]\n{item['caption']}"
                print("  " + shown.replace("\n", "\n  "))
                continue
            if not post_qa.gate(qa_problems(item, ch), f"{ch} {item['key']}"):
                continue  # broken asset or caption: refused, the next item may still go
            if posted_any and STAGGER:
                time.sleep(STAGGER)
            try:
                res = POSTERS[ch](item, data) if ch == "youtube" else POSTERS[ch](item)
            except Exception as exc:  # one platform failing never blocks the others
                print(f"::warning::{ch}: {item['key']} failed ({exc})")
                break
            if not res:
                break
            posted_any = True
            print(f"{ch}: posted {item['key']} {res.get('link')}")
            clip_progress.record_post(ch, item["key"], res.get("link"), media_id=res.get("id"),
                                      variant=item.get("variant"))
            posts.append({"channel": ch, "clip": item["key"], "posted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    return 0


# The rendered pieces the Mac poster sends per channel (feed item[channel]).
MAC_PIECES = {"tiktok": ("caption",), "pinterest": ("description", "link")}


def public(item, channel):
    """An item as plain feed data: search fields kept (variant, alt, keywords, keyline; for YouTube the
    search-first title / description / tags), the internal clip and variant objects dropped."""
    out = {k: v for k, v in item.items() if k not in ("clip", "v")}
    # The consumers (threads-autopilot, the Mac) build their post from these three: always present, and
    # `play` is the Google Play link whenever the app is on Android (None otherwise).
    out.update(store=item.get("store"), play=play_of(item), button=button_of(item))
    if item.get("clip"):
        out.update(keywords=item["clip"].get("keywords") or [], keyline=item["clip"].get("keyline", ""),
                   compliance=item["clip"].get("compliance"))  # threads-autopilot / the YouTube runner check it
        if channel == "youtube":
            title, desc, words = yt_meta(item)
            out["youtube"] = {"title": title, "description": desc, "tags": words}
    if channel in MAC_PIECES:
        # The Mac sends exactly these pieces (the QA gate checked the same render); it re-checks the links itself.
        pieces = render(item, channel)
        out[channel] = {k: pieces[k] for k in MAC_PIECES[channel]}
    return out


def performance_summary(path=SC.PERFORMANCE):
    """What the performance loop knows (performance.json), as plain feed data; {} before any insights."""
    perf = SC._load(path, {})
    return {k: perf[k] for k in ("boost", "demote", "hook_winners", "best_hours", "updated_at") if perf.get(k)}


def pool(data, channel, day, perf=None):
    """Every uploaded clip as a ready item for `channel` (search-first caption, the day's hook variant),
    performance boost apps first, then clips.json order; unfiltered by any post log."""
    boost = [a for a in (perf or {}).get("boost") or [] if isinstance(a, str)]
    rank = {app: i for i, app in enumerate(boost)}
    clips = [(k, c) for k, c in (data.get("clips") or {}).items() if c.get("url") and c.get("store_url")]
    order = sorted(range(len(clips)), key=lambda i: (rank.get(clips[i][1].get("app"), len(rank)), i))
    out = []
    for i in order:
        key, clip = clips[i]
        if post_qa.video_compliance_problems(clip):  # no real-recording record: never offered (owner rule)
            continue
        raw = clip_item(key, clip, channel, day)
        if not outgoing(raw, channel):  # a clip whose download link cannot be attached is not offered
            continue
        item = public(raw, channel)
        if clip.get("app") in rank:
            item["boost_rank"] = rank[clip["app"]] + 1
        out.append(item)
    return out


def export(day, check=True, data=None, perf=None):
    """The day's clip and card items per EXPORT_CHANNELS, unfiltered by any post log, plus the
    clip pool for POOL_CHANNELS and the performance summary.

    Consumers keep their own dedup and caps; clips come in clips.json order for
    slot 1 then slot 15 (Instagram entry first), cards only once published."""
    data = data if data is not None else clip_posts.load()
    perf = performance_summary() if perf is None else perf
    items = {}
    for ch in EXPORT_CHANNELS:
        out = []
        # Only items that pass the pre-post QA gate reach the feed's posters (post_qa.py).
        ok = lambda i: post_qa.gate(qa_problems(i, ch, online=check), f"feed {ch} {i['key']}")  # noqa: E731
        for slot in (1, 15):
            out += [dict(public(i, ch), slot=slot) for i in todays_clips(data, [], ch, day, slot)
                    if i["key"] not in {o["key"] for o in out} and ok(i)]
        if PLAN[ch]["cards"]:
            out += [public(c, ch) for c in todays_cards(day, ch) if (not check or exists(c["image"])) and ok(c)]
        items[ch] = out
    return {"schema": FEED_SCHEMA, "date": day.isoformat(),
            "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "items": items,
            "pool": {ch: pool(data, ch, day, perf) for ch in POOL_CHANNELS}, "performance": perf}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["post", "whoami", "export"])
    ap.add_argument("--out", help="export: file to write (default stdout)")
    ap.add_argument("--channel", default="all", help="one platform, a comma list, or all")
    ap.add_argument("--slot", default="auto", help="1 or 15 (clips.json slot); auto = by UTC hour")
    ap.add_argument("--date", help="YYYY-MM-DD (UTC), default today")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    channels = CHANNELS if args.channel in ("", "all") else tuple(c.strip() for c in args.channel.split(",") if c.strip())
    unknown = [c for c in channels if c not in CHANNELS]
    if unknown:
        print(f"social-extra: unknown channel {', '.join(unknown)}")
        return 0
    if args.mode == "whoami":
        return whoami(channels)
    now = dt.datetime.now(dt.timezone.utc)
    day = dt.date.fromisoformat(args.date) if args.date else now.date()
    if args.mode == "export":
        text = json.dumps(export(day), ensure_ascii=False, indent=1) + "\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    slot = int(args.slot) if args.slot.isdigit() else (1 if now.hour < 12 else 15)
    return run(channels, day, slot, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
