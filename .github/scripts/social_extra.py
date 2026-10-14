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

Bluesky and Mastodon are posted by the threads-autopilot repo (media.yml),
where those accounts' secrets live: it reads the day's items from the
social-feed branch that `export` writes (feed.json). So this script skips
Bluesky unless FORCE_GUIDE_BLUESKY=1, and a Bluesky secret added here later
never double-posts. YouTube Shorts of the clips can also come from the Mac
(00_GrowthEngine hook-shorts-youtube.yml, off by default), reading the same feed.

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

import clip_posts  # noqa: E402
import clip_progress  # noqa: E402
import countdown_cards  # noqa: E402
import search_caption as SC  # noqa: E402

UA = "lumi-social-extra/1.0"
REPO = os.environ.get("GITHUB_REPOSITORY") or "alice51849/ios-app-guide"
PAUSE = 5  # seconds between polls (tests set 0)
STAGGER = 20  # seconds between two platforms that posted

CHANNELS = ("facebook", "bluesky", "youtube", "pinterest", "tumblr", "naver", "plurk", "dailymotion")
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
}
# Served by another repo from feed.json; this script never posts them unless forced.
SERVED_ELSEWHERE = {"bluesky": "threads-autopilot media.yml"}
EXPORT_CHANNELS = ("bluesky", "mastodon", "youtube")
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
}
# Campaign suffix per platform (App Store ct token / Play referrer).
CT = {"facebook": "fb", "bluesky": "bs", "youtube": "yt", "pinterest": "pin", "tumblr": "tb",
      "naver": "nv", "plurk": "pk", "dailymotion": "dm", "mastodon": "ma"}


def env(name):
    return os.environ.get(name, "").strip()


def served_elsewhere(channel):
    return channel in SERVED_ELSEWHERE and env("FORCE_GUIDE_BLUESKY") != "1"


def not_configured(channel):
    if served_elsewhere(channel):
        return f"{channel}: not configured here (served by {SERVED_ELSEWHERE[channel]}; FORCE_GUIDE_BLUESKY=1 overrides)"
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


def clip_item(key, clip, channel, day=None):
    """One clip for one platform: search-first caption, keyword title / alt text, the day's hook variant."""
    ct = CT[channel]
    t = clip_posts.text_for(clip["locale"])
    v = SC.choose(clip, channel, day or SC.today())
    return {"kind": "clip", "key": key, "locale": clip["locale"], "app": clip["app"], "video": clip["url"],
            "hook": v["lead"], "name": clip["name"], "title": SC.pin_title(clip, v), "tags": SC.tags(clip, 10),
            "caption": clip_posts.caption(clip, channel, v), "button": t["button"], "variant": v["id"],
            "alt": SC.alt_text(clip, v), "clip": clip, "v": v,
            "store": clip_posts.with_campaign(clip["store_url"], ct), "play": clip_posts.play_url(clip, ct)}


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
        if key in seen or key in done or not clip or not clip.get("url"):
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
                      "play": countdown_cards.play_store_url(countdown_cards.APP_ID, f"cd_{e['id']}_{ct}"[:40])})
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
    locales = PLAN[channel].get("locales")
    return [c for c in cards if not locales or c["locale"] in locales]


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


def link_lines(item):
    lines = [f"{item['button']}: {item['store']}"]
    if item.get("play"):
        lines.append(f"Google Play: {item['play']}")
    return lines


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


def post_facebook(item):
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
        "description": item["caption"]}))
    # Links in a Reel caption are not clickable: the store links go in the first
    # comment, or (if commenting is refused) in a link post with a preview.
    try:
        http("POST", f"{FB}/{vid}/comments", form({"message": "\n".join(link_lines(item)), "access_token": token}))
    except Exception as exc:
        print(f"facebook: comment refused ({exc.__class__.__name__}); posting a link post instead")
        http("POST", f"{FB}/{page}/feed", form({"message": f"{item['name']}\n{item['hook']}", "link": item["store"],
                                                 "access_token": token}))
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


def post_bluesky(item):
    s = bsky_session()
    links = [("App Store", item["store"])] + ([("Google Play", item["play"])] if item.get("play") else [])
    text, facets = bsky_rich(item["caption"], links)
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
        links = [f"App Store: {item['store']}"] + ([f"Google Play: {item['play']}"] if item.get("play") else [])
        return SC.youtube(item["clip"], item["v"], links)
    title, desc = yt_text(item["hook"], item["name"], item["store"], item.get("play"), item["tags"])
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
            locs[YT_LANG.get(clip["locale"], clip["locale"])] = {"title": t, "description": d}
    if locs:
        body["localizations"] = locs
    return body


def post_youtube(item, data=None):
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


def post_pinterest(item, tries=60):
    auth = {"Authorization": f"Bearer {pin_token()}"}
    board = pin_board(auth)
    pin = {"board_id": board, "link": item["store"], "title": item["title"][:100],
           "description": item["caption"][:500], "alt_text": (item.get("alt") or item["hook"])[:500]}
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


def post_tumblr(item):
    blog = tumblr_blog()
    if item["kind"] == "card":
        media = {"type": "image", "media": [{"type": "image/jpeg", "identifier": "media0", "width": 1080, "height": 1350}],
                 "alt_text": (item.get("alt") or item["hook"])[:4096]}
        upload = ("media0", fetch_bytes(item["image"]), "card.jpg", "image/jpeg")
    else:
        media = {"type": "video", "media": {"type": "video/mp4", "identifier": "media0", "width": 1080, "height": 1920}}
        upload = ("media0", fetch_bytes(item["video"]), "clip.mp4", "video/mp4")
    content = [{"type": "text", "text": item["caption"]}, media,
               {"type": "link", "url": item["store"], "title": item["name"], "description": item["hook"]}]
    if item["kind"] == "clip":  # keyword-rich heading: Tumblr search reads post text and the first tags
        content.insert(0, {"type": "text", "subtype": "heading2", "text": item["title"]})
    if item.get("play"):
        content.append(text_link_block("Google Play", item["play"]))
    payload = {"content": content, "state": "published",
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


def post_naver(item):
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
    text = "<br>".join(html.escape(line) for line in item["caption"].split("\n"))
    links = [f'<a href="{html.escape(item["store"])}">{html.escape(item["button"])}</a>']
    if item.get("play"):
        links.append(f'<a href="{html.escape(item["play"])}">Google Play에서 받기</a>')
    body = f"<p>{text}</p>{media}<p>{' · '.join(links)}</p>"
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


def post_plurk(item, limit=360):
    if item["kind"] == "card":
        media = plurk_call("/Timeline/uploadPicture", files=[("image", fetch_bytes(item["image"]), "card.jpg", "image/jpeg")])["full"]
    else:
        media = item["video"]
    tail = f"\n{media}\n{item['store']} ({item['button']})"
    if item.get("play") and len(tail) + len(item["play"]) + 16 < limit - 40:
        tail += f"\n{item['play']} (Google Play)"
    head = item["caption"]
    if len(head) + len(tail) > limit:
        head = head[:max(0, limit - len(tail) - 1)].rstrip() + "…"
    r = plurk_call("/Timeline/plurkAdd", {"content": head + tail, "qualifier": "shares", "lang": "tr_ch"})
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


def post_dailymotion(item):
    auth = {"Authorization": f"Bearer {dm_token()}"}
    desc = "\n".join([item["caption"], "", *link_lines(item)])
    r = http("POST", f"{DM}/me/videos", form({
        "url": item["video"], "title": f"{item['hook']} | {item['name']}"[:255], "description": desc[:3000],
        "tags": ",".join(t.lstrip("#") for t in item["tags"][:5]), "channel": "tech", "published": "true",
        "is_created_for_kids": "false"}), auth)
    return {"id": r["id"], "link": f"https://www.dailymotion.com/video/{r['id']}"}


def whoami_dailymotion():
    r = http("GET", f"{DM}/me?fields=id,username,screenname", headers={"Authorization": f"Bearer {dm_token()}"})
    print(f"dailymotion: {r.get('username')} ({r.get('screenname')})")


# ---------------------------------------------------------------- runner

POSTERS = {"facebook": post_facebook, "bluesky": post_bluesky, "youtube": post_youtube, "pinterest": post_pinterest,
           "tumblr": post_tumblr, "naver": post_naver, "plurk": post_plurk, "dailymotion": post_dailymotion}
WHOAMI = {"facebook": whoami_facebook, "bluesky": whoami_bluesky, "youtube": whoami_youtube,
          "pinterest": whoami_pinterest, "tumblr": whoami_tumblr, "naver": whoami_naver, "plurk": whoami_plurk,
          "dailymotion": whoami_dailymotion}


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
                print("  " + item["caption"].replace("\n", "\n  "))
                continue
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


def public(item, channel):
    """An item as plain feed data: search fields kept (variant, alt, keywords, keyline; for YouTube the
    search-first title / description / tags), the internal clip and variant objects dropped."""
    out = {k: v for k, v in item.items() if k not in ("clip", "v")}
    if item.get("clip"):
        out.update(keywords=item["clip"].get("keywords") or [], keyline=item["clip"].get("keyline", ""))
        if channel == "youtube":
            title, desc, words = yt_meta(item)
            out["youtube"] = {"title": title, "description": desc, "tags": words}
    return out


def export(day, check=True, data=None):
    """The day's clip and card items per EXPORT_CHANNELS, unfiltered by any post log.

    Consumers keep their own dedup and caps; clips come in clips.json order for
    slot 1 then slot 15 (Instagram entry first), cards only once published."""
    data = data if data is not None else clip_posts.load()
    items = {}
    for ch in EXPORT_CHANNELS:
        out = []
        for slot in (1, 15):
            out += [dict(public(i, ch), slot=slot) for i in todays_clips(data, [], ch, day, slot)
                    if i["key"] not in {o["key"] for o in out}]
        if PLAN[ch]["cards"]:
            out += [c for c in todays_cards(day, ch) if not check or exists(c["image"])]
        items[ch] = out
    return {"schema": FEED_SCHEMA, "date": day.isoformat(),
            "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "items": items}


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
