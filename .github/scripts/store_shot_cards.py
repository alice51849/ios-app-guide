#!/usr/bin/env python3
"""Instagram feed carousels from the live App Store screenshots (zero token, zero paid service).

The Reels reach people who scroll; the feed grid is what a visitor sees after a
Reel or a search, and today it holds only the daily utility card. This script
posts one carousel per slot: 3-4 cards (1080x1350) made from the app's own
App Store screenshots in the storefront of the slot's market, each card with a
pain-point line in that market's language. Texts come from .github/growth/
clips.json (the storyboard hooks, benefit, keyline and search phrase that the
pre-post QA already vets: no price, no "free", no superlatives), the images
from itunes.apple.com lookup (the public screenshotUrls), so nothing here is
invented and nothing in App Store Connect is touched.

Slots (ig-feed-daily.yml, .github/growth/volume-ramp.json "instagram_feed"):
07 UTC = Taipei 15:20 / Tokyo-Seoul 16:20 -> the app's Asia locale (zh-Hant
first: the top revenue per download), 19 UTC = New York 15:20 / LA 12:20 ->
English. Apps rotate in the planner's revenue order (the order of clips.json's
schedule), one app at most once a week here, one (app, locale) carousel at
most once in 60 days. The caption is clip_posts.caption (problem line,
benefit, keyword line, App Store search line, the profile-link step naming the app
(ig_bio.py), the direct App Store link with ct=h7_<app>_igc - the carousels' own row,
apart from the Reels' h7_<app>_ig - plus Google Play when the app is on Android,
keyword tags); the drawn cards carry no URL (not tappable on an image).

    python3 store_shot_cards.py make --slot 7 --out-dir cards/      # cards + plan.json
    python3 store_shot_cards.py post --dir cards/ --base-url https://raw.githubusercontent.com/<repo>/feed-cards
    python3 store_shot_cards.py preview --slot 19                     # what would go out, no network
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clip_posts  # noqa: E402
import clip_progress  # noqa: E402
import countdown_cards as cd  # noqa: E402
import download_links as DL  # noqa: E402
import post_qa  # noqa: E402
import search_caption as SC  # noqa: E402
import volume_ramp  # noqa: E402

CHANNEL = "instagram_feed"
KEY_PREFIX = "feed/"
GRAPH = "https://graph.instagram.com/v21.0"
W, H = 1080, 1350
CARDS_MAX = 4
CARDS_MIN = 2
APP_COOLDOWN_DAYS = 7     # the same app at most once a week in the feed
PAIR_COOLDOWN_DAYS = 60   # the same (app, locale) carousel at most once in two months
SLOT_LOCALES = {7: ["zh-Hant", "ja", "ko"], 19: ["en"]}
STOREFRONT = {"zh-Hant": "tw", "ja": "jp", "ko": "kr", "en": "us", "pt-BR": "br", "de": "de", "fr": "fr", "es": "es",
              "id": "id", "vi": "vn", "th": "th", "cs": "cz", "nl": "nl", "da": "dk", "nb": "no", "pl": "pl", "el": "gr",
              "ar": "sa", "zh-Hans": "cn"}
SHOT_SIZE = "1242x2688bb.jpg"  # the mzstatic size segment we ask for (the lookup returns 320x480 thumbnails)
UA = "lumi-feed-cards/1.0"
PAUSE = 5  # seconds between processing polls (tests set 0)


def load_clips(path=clip_posts.CLIPS):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def app_order(data):
    """Listing keys in the planner's order: first appearance in the schedule (revenue-led), then the rest."""
    out = []
    for e in data.get("schedule", []):
        app = (data.get("clips", {}).get(e["clip"]) or {}).get("app")
        if app and app not in out:
            out.append(app)
    for c in data.get("clips", {}).values():
        if c.get("app") and c["app"] not in out:
            out.append(c["app"])
    return out


def recent(posts, day, days, prefix=KEY_PREFIX):
    """(apps, keys) posted in the feed within `days` before `day`."""
    cutoff = (day - dt.timedelta(days=days)).isoformat()
    apps, keys = set(), set()
    for p in posts or []:
        if p.get("channel") != CHANNEL or not str(p.get("clip", "")).startswith(prefix):
            continue
        if str(p.get("posted_at", ""))[:10] >= cutoff:
            keys.add(p["clip"])
            apps.add(p["clip"][len(prefix):].split("/")[0])
    return apps, keys


def pick(data, posts, day, slot):
    """(key, clip) for this slot: the first app in planner order with a clip in one of the slot's locales,
    not featured in the feed this week, this pair not within 60 days. None when nothing fits."""
    locales = SLOT_LOCALES.get(slot) or SLOT_LOCALES[19]
    week_apps, _ = recent(posts, day, APP_COOLDOWN_DAYS)
    _, old_keys = recent(posts, day, PAIR_COOLDOWN_DAYS)
    clips = data.get("clips", {})
    for app in app_order(data):
        base = clips.get(f"{app}/{locales[0]}", {}).get("base") or app
        if base in week_apps or app in week_apps or app.endswith("_b"):  # variants share the listing's week
            continue
        for locale in locales:
            clip = clips.get(f"{app}/{locale}")
            key = f"{KEY_PREFIX}{app}/{locale}"
            if clip and clip.get("store_url") and key not in old_keys:
                return key, clip
    return None, None


# ---------------------------------------------------------------- images

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def shot_urls(clip, locale):
    """The app's iPhone screenshots in the slot market's storefront (large size), [] offline or when absent."""
    app_id = clip_posts.ios_id(clip)
    rec = post_qa.store_lookup(app_id, STOREFRONT.get(locale, "us")) if app_id else None
    if not rec:
        return []
    urls = [u for u in rec.get("screenshotUrls") or [] if isinstance(u, str)]
    return [re.sub(r"/\d+x\d+bb\.(?:jpg|png)$", f"/{SHOT_SIZE}", u) for u in urls[:CARDS_MAX]]


def palette(img):
    """(top, bottom) card colours from the screenshot's own edge colour, kept legible for white text."""
    small = img.convert("RGB").resize((20, 40))
    px = [small.getpixel((x, y)) for x in range(20) for y in (0, 1, 38, 39)]
    r, g, b = (sum(p[i] for p in px) // len(px) for i in range(3))
    base = cd.legible((r, g, b), cd.WHITE, 5.5)
    top = tuple(int(c * 0.75) for c in base)
    bottom = tuple(min(255, int(c * 1.15) + 12) for c in base)
    return top, cd.legible(bottom, cd.WHITE, 4.6)


def card_lines(clip, variant, index):
    """Headline per card: the problem line, then the benefit, then the keyline, then the search line."""
    t = clip_posts.text_for(clip["locale"])
    pool = [SC.tidy(variant.get("lead", "")), SC.tidy(variant.get("benefit", "")), clip.get("keyline", ""),
            t["search"].format(s=SC.clip_search(clip))]
    pool = [x for i, x in enumerate(pool) if x and x not in pool[:i]]
    return pool[index % len(pool)]


def compose(shot_bytes, headline, clip, out):
    """One 1080x1350 card: gradient from the screenshot's colours, the headline, the phone screenshot, a footer
    with the app name. Returns the saved path."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    shot = Image.open(io.BytesIO(shot_bytes)).convert("RGBA")
    top, bottom = palette(shot)
    img = Image.new("RGB", (W, H))
    cd.gradient(ImageDraw.Draw(img), W, H, top, bottom)
    draw = ImageDraw.Draw(img)
    idx = cd.FONT_INDEX.get(clip["locale"], 0)
    f = lambda size: ImageFont.truetype(cd.FONT, size, index=idx)
    lines, size = cd.wrap(draw, headline, f, 68, W - 140)
    y = 90
    for line in lines[:3]:
        draw.text(((W - draw.textlength(line, font=f(size))) / 2, y), line, font=f(size), fill=cd.WHITE)
        y += int(size * 1.28)
    # The phone screenshot below the headline, rounded, with a soft shadow.
    ph = min(H - y - 60 - 110, 900)
    pw = int(shot.width * ph / shot.height)
    if pw > W - 160:
        pw = W - 160
        ph = int(shot.height * pw / shot.width)
    phone = shot.resize((pw, ph), Image.LANCZOS)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=int(pw * 0.09), fill=255)
    shadow = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 50, pw + 40, ph + 40], radius=int(pw * 0.09), fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    x, top_y = (W - pw) // 2, y + 40
    img.paste(shadow, (x - 40, top_y - 40), shadow)
    img.paste(phone, (x, top_y), mask)
    cd.footer_band(img, bottom, h=220)
    draw = ImageDraw.Draw(img)
    name = clip.get("name", "")
    size = 40
    while draw.textlength(name, font=f(size)) > W - 160 and size > cd.MIN_TEXT:
        size -= 2
    draw.text(((W - draw.textlength(name, font=f(size))) / 2, H - 60 - size), name, font=f(size), fill=cd.WHITE)
    img.save(out, "JPEG", quality=90)
    return out


FEED_CT = "igc"   # ct suffix of the carousels (h7_<app>_igc; 00_GrowthEngine agent/ct_codes.py: instagram_feed)


def caption(clip, variant):
    return clip_posts.caption(clip, "instagram", variant, tag=FEED_CT)


def make(out_dir, day, slot, data=None, posts=None, fetcher=fetch):
    """Render the slot's carousel into out_dir (NN.jpg + plan.json). Returns the plan, or None (nothing due,
    allowance used up, no screenshots)."""
    data = data or load_clips()
    posts = clip_posts.posted_log() if posts is None else posts
    allowed, done, left = volume_ramp.room(volume_ramp.load(), CHANNEL, day, posts)
    if left is not None and left <= 0:
        print(f"feed: {done} of today's {allowed} carousels already out (volume-ramp.json); nothing to make")
        return None
    key, clip = pick(data, posts, day, slot)
    if not clip:
        print("feed: no app fits this slot (all featured recently)")
        return None
    variant = SC.choose(clip, CHANNEL, day)
    urls = shot_urls(clip, clip["locale"])
    if len(urls) < CARDS_MIN:
        print(f"feed: {key} has {len(urls)} store screenshots in {STOREFRONT.get(clip['locale'], 'us')}; need {CARDS_MIN}")
        return None
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for i, url in enumerate(urls[:CARDS_MAX]):
        try:
            data_bytes = fetcher(url)
        except Exception as exc:  # the thumbnail size we asked for is missing: fall back to the listed one
            print(f"feed: {url} failed ({exc.__class__.__name__}); trying the listed size")
            try:
                data_bytes = fetcher(re.sub(rf"/{re.escape(SHOT_SIZE)}$", "/320x480bb.jpg", url))
            except Exception:
                continue
        cards.append(compose(data_bytes, card_lines(clip, variant, i), clip, out_dir / f"{i + 1:02d}.jpg").name)
    if len(cards) < CARDS_MIN:
        print(f"feed: only {len(cards)} cards could be drawn; skipped")
        return None
    plan = {"key": key, "app": clip["app"], "locale": clip["locale"], "slot": slot, "date": day.isoformat(),
            "variant": variant["id"], "cards": cards, "caption": caption(clip, variant), "store_url": clip["store_url"],
            "name": clip.get("name", ""), "alt": SC.alt_text(clip, variant)}
    (out_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return plan


# ---------------------------------------------------------------- Instagram

def checked_caption(plan):
    """The caption with the app's direct download link(s): the clip caption already holds them; this is the
    last guard before the send (a caption without the link raises MissingDownloadLink and nothing is posted)."""
    stub = {"store_url": plan["store_url"], "locale": plan["locale"]}
    store, play = clip_posts.download_urls(stub, "instagram", FEED_CT)
    return DL.ensure_download_link(plan["caption"], store, play, max_len=post_qa.LIMITS["instagram"],
                                   app_store_label=clip_posts.text_for(plan["locale"])["button"],
                                   play_label=clip_posts.play_label(stub), label=f"feed {plan['key']}")


def post_instagram(plan, base_url, wait=PAUSE, tries=40):
    """Carousel container from the published card URLs, published; {"id", "link"} or None without a token."""
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        print("feed: IG_ACCESS_TOKEN not set, carousel skipped")
        return None
    me = clip_posts._get(f"{GRAPH}/me?fields=user_id,username&access_token={token}")
    user = me.get("user_id") or me.get("id")
    children = []
    for i, name in enumerate(plan["cards"]):
        fields = {"image_url": f"{base_url.rstrip('/')}/{name}", "is_carousel_item": "true", "access_token": token}
        if i == 0 and plan.get("alt"):
            fields["alt_text"] = plan["alt"][:1000]
        children.append(clip_posts._post(f"{GRAPH}/{user}/media", fields)["id"])
        time.sleep(min(wait, 2))
    container = clip_posts._post(f"{GRAPH}/{user}/media", {
        "media_type": "CAROUSEL", "children": ",".join(children), "caption": checked_caption(plan),
        "access_token": token})["id"]
    for _ in range(tries):
        status = clip_posts._get(f"{GRAPH}/{container}?fields=status_code&access_token={token}").get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Instagram could not build the carousel")
        time.sleep(wait)
    else:
        raise RuntimeError("Instagram carousel processing timed out")
    media = clip_posts._post(f"{GRAPH}/{user}/media_publish", {"creation_id": container, "access_token": token})["id"]
    try:
        link = clip_posts._get(f"{GRAPH}/{media}?fields=permalink&access_token={token}").get("permalink")
    except Exception as exc:  # the post is up; a missing link must not fail the run
        print(f"feed: permalink lookup skipped ({exc.__class__.__name__})")
        link = None
    return {"id": media, "link": link}


def qa(plan, online=True):
    """The pre-post QA gate on the exact caption (store name as the allowed brand word)."""
    return post_qa.card_problems(plan["caption"], plan["locale"], "instagram", store_url=plan["store_url"],
                                 name=plan["name"], online=online, require_bio=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make", "post", "preview"])
    ap.add_argument("--slot", type=int, help="UTC slot hour (7 = Asia locale, 19 = English)")
    ap.add_argument("--date", help="YYYY-MM-DD, default today (UTC)")
    ap.add_argument("--out-dir", default="feed-cards")
    ap.add_argument("--dir", default="feed-cards", help="post: directory holding plan.json and the cards")
    ap.add_argument("--base-url", help="post: public URL the cards were published under")
    args = ap.parse_args(argv)
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    if args.cmd in ("make", "preview"):
        slot = args.slot if args.slot is not None else (7 if dt.datetime.now(dt.timezone.utc).hour < 13 else 19)
        if args.cmd == "preview":
            key, clip = pick(load_clips(), clip_posts.posted_log(), day, slot)
            if not clip:
                print("feed: nothing fits")
                return 0
            variant = SC.choose(clip, CHANNEL, day)
            print(key, "\n" + caption(clip, variant))
            for i in range(CARDS_MAX):
                print(f"card {i + 1}: {card_lines(clip, variant, i)}")
            return 0
        plan = make(args.out_dir, day, slot)
        print(json.dumps({k: plan[k] for k in ("key", "cards")}, ensure_ascii=False) if plan else "feed: nothing made")
        return 0
    plan_path = Path(args.dir) / "plan.json"
    if not plan_path.exists():
        print("feed: no plan.json; nothing to post")
        return 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not args.base_url:
        print("::error::feed: --base-url is required to post")
        return 1
    if not post_qa.gate(qa(plan), f"feed {plan['key']}"):
        return 1
    try:
        posted = post_instagram(plan, args.base_url)
    except Exception as exc:
        volume_ramp.handle_error(CHANNEL, exc, day=day)
        raise
    print(f"feed: posted {posted}")
    if posted:
        clip_progress.record_post(CHANNEL, plan["key"], posted.get("link"), media_id=posted.get("id"),
                                  variant=plan.get("variant"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
