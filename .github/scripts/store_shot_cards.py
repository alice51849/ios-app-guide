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
benefit, keyword line, App Store search line, then "📲 Download via the link in bio"
in the slot's language and the hashtags led by the app's brand hashtag, #Mochi;
owner 2026-10-17: no URL in an Instagram text, it cannot be tapped - the profile
link is the hub ig_bio_hub.py builds, ig_bio.py); the drawn cards carry no URL either.

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

import channel_rotation as CR  # noqa: E402
import clip_posts  # noqa: E402
import clip_progress  # noqa: E402
import countdown_cards as cd  # noqa: E402
import ig_bio as IGB  # noqa: E402
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


# ---------------------------------------------------------------- "5 apps" list carousels (methods50 #32)
#
# 2026-10-22 (50 methods dept, via the coordinator): the "must-have top 5" list format. A list that names only our
# own apps is not believed, so every list carries at least 3 apps of other developers and ours is one of the 5.
# Nothing is ranked by us: the list is Apple's own App Store search order for the app's head term, copied from the
# app's live comparison page (support_network/gen_market_snapshot.py, open.cait518.cc/<site>/compare*.html: rank,
# name, developer, rating, rating count, last update, fetch date). Our app is in the top 5 there, or it is shown
# as the fifth card with its real search position. No prices, no "best", no links to the other apps.
# The first carousel after the 10-22 restore uses this format, then one a week (TOP5_EVERY_DAYS).
TOP5_EVERY_DAYS = 7
TOP5_MIN_OTHERS = 3
COMPARE_ROOT = "https://open.cait518.cc"
COMPARE_SUFFIX = {"en": "", "zh-Hant": ".zh-Hant", "ja": ".ja", "ko": ".ko"}
SUPPORT_SITE = {"mochi": "mochitodo-support", "claudeusagemini": "usagenow-support", "sereno": "sereno-support",
                "lumibopomofo": "lumi-support"}
TOP5_TEXT = {
    "en": {"hook": "“{term}” on the App Store: 5 apps, in Apple's search order",
           "sub": "Apple's search order · {date} · We made one of these 5",
           "line": "{rank}. {app} ({dev}) ★{rating}", "ours": "← made by us",
           "badge": "Made by us", "rating": "★ {rating} · {count} ratings", "updated": "Updated {date}",
           "pos": "App Store search position {rank}",
           "honest": "The order is Apple's own search result ({date}); we did not score anything and have no ties with the other developers."},
    "zh-Hant": {"hook": "「{term}」在 App Store 搜得到的 5 款 App（照 Apple 實際順序）",
                "sub": "Apple 搜尋實際順序・{date}・其中一款是我們做的",
                "line": "{rank}. {app}（{dev}）★{rating}", "ours": "← 我們做的",
                "badge": "我們做的 App", "rating": "★ {rating}・{count} 則評分", "updated": "最近更新 {date}",
                "pos": "App Store 搜尋順序 {rank}",
                "honest": "排列照 App Store 搜尋實際順序（{date}），我們沒有另外打分，也和其他開發者沒有任何關係。"},
    "ja": {"hook": "「{term}」App Store 検索で出てくる5本（Apple の表示順）",
           "sub": "Apple の検索表示順・{date}・うち1本は私たちのアプリです",
           "line": "{rank}. {app}（{dev}）★{rating}", "ours": "← 私たちのアプリ",
           "badge": "私たちのアプリ", "rating": "★ {rating}・評価 {count} 件", "updated": "最終更新 {date}",
           "pos": "App Store 検索の表示順 {rank}",
           "honest": "並びは App Store 検索の実際の表示順（{date}）で、私たちは採点しておらず、他の開発者とは無関係です。"},
}
TOP5_PALETTE = ((54, 64, 120), (122, 82, 160))
TOP5_FIRST = ("mochi",)   # the flagship (owner 2026-10-20: Cute To-Do first) gets the list first when it fits


def compare_url(app, locale):
    site = SUPPORT_SITE.get(app) or f"{app}-support"
    return f"{COMPARE_ROOT}/{site}/compare{COMPARE_SUFFIX.get(locale, '.' + locale)}.html"


def parse_compare(page):
    """The comparison page as {"term", "date", "rows": [{rank, app, dev, rating, count, updated, ours}]}; None when
    the page is not one (no table, no own row)."""
    import html as _html
    rows = []
    for m in re.finditer(r"<tr( class=\"ours\")?>(.*?)</tr>", page or "", re.S):
        cells = [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(2), re.S)]
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        app = re.sub(r"<[^>]+>", "", re.sub(r'<span class="tag">.*?</span>', "", re.findall(r"<td[^>]*>(.*?)</td>", m.group(2), re.S)[1]))
        rows.append({"rank": int(cells[0]), "app": _html.unescape(app).strip(), "dev": cells[2], "rating": cells[3],
                     "count": cells[4], "updated": cells[6], "ours": bool(m.group(1))})
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page or "", re.S)
    term = re.search(r"[「“\"](.+?)[」”\"]", _html.unescape(h1.group(1))) if h1 else None
    date = re.search(r'"dateModified":\s*"(\d{4}-\d{2}-\d{2})', page or "") or re.search(r"(\d{4}-\d{2}-\d{2})", page or "")
    if not rows or not any(r["ours"] for r in rows) or not term:
        return None
    return {"term": term.group(1), "date": date.group(1) if date else "", "rows": rows}


def top5_rows(rows):
    """Apple's first 5 when ours is among them, else the first 4 others + ours (with its real position).
    None when fewer than TOP5_MIN_OTHERS other developers' apps would be on the list."""
    ours = next((r for r in rows if r["ours"]), None)
    others = [r for r in rows if not r["ours"]]
    if not ours:
        return None
    picks = rows[:5] if ours["rank"] <= 5 and ours in rows[:5] else others[:4] + [ours]
    if sum(1 for r in picks if not r["ours"]) < TOP5_MIN_OTHERS:
        return None
    return picks


def top5_due(posts, day):
    cutoff = (day - dt.timedelta(days=TOP5_EVERY_DAYS)).isoformat()
    return not any(p.get("channel") == CHANNEL and "/top5/" in str(p.get("clip", ""))
                   and str(p.get("posted_at", ""))[:10] >= cutoff for p in posts or [])


def top5_caption(clip, snap, picks):
    t = TOP5_TEXT.get(clip["locale"]) or TOP5_TEXT["en"]
    lines = [t["hook"].format(term=snap["term"]), ""]
    for r in picks:
        line = t["line"].format(rank=r["rank"], app=r["app"], dev=r["dev"], rating=r["rating"])
        if r["rating"] in ("", "—", "-"):
            line = line.rsplit(" ★", 1)[0]
        lines.append(f"{line} {t['ours']}" if r["ours"] else line)
    lines += ["", t["honest"].format(date=snap["date"]), IGB.bio_line(clip["locale"])]
    limit = SC.TAG_LIMIT.get("instagram", 5)
    tags = IGB.hashtags(lambda n: SC.tags(clip, n), clip["name"], clip.get("store_url"), limit)
    text = "\n".join(lines + (["", " ".join(tags)] if tags else []))
    return IGB.caption(text, clip["name"], clip["locale"], clip.get("store_url"), max_len=post_qa.LIMITS["instagram"],
                       tag_limit=limit, label=f"feed top5 {clip.get('app')}/{clip.get('locale')}")


def compose_text_card(lines, clip, out, badge=None, footer=False):
    """A 1080x1350 text card on the list palette: big first line, then the smaller lines; an optional badge.
    footer=True prints our app's name at the bottom (the cover and our own card only, never another app's card)."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H))
    cd.gradient(ImageDraw.Draw(img), W, H, *TOP5_PALETTE)
    draw = ImageDraw.Draw(img)
    idx = cd.FONT_INDEX.get(clip["locale"], 0)
    f = lambda size: ImageFont.truetype(cd.FONT, size, index=idx)
    y = 170
    for n, text in enumerate(lines):
        start = 120 if n == 0 else 56
        wrapped, size = cd.wrap(draw, text, f, start, W - 160)
        for line in wrapped[:4]:
            draw.text(((W - draw.textlength(line, font=f(size))) / 2, y), line, font=f(size), fill=cd.WHITE)
            y += int(size * 1.3)
        y += 40
    if badge:
        size = 48
        bw = draw.textlength(badge, font=f(size)) + 80
        x0, y0 = (W - bw) / 2, H - 260
        draw.rounded_rectangle([x0, y0, x0 + bw, y0 + 96], radius=48, fill=(255, 214, 102))
        draw.text((x0 + 40, y0 + 22), badge, font=f(size), fill=(40, 30, 60))
    if footer:
        name = clip.get("name", "")
        draw.text(((W - draw.textlength(name, font=f(36))) / 2, H - 110), name, font=f(36), fill=cd.WHITE)
    img.save(out, "JPEG", quality=90)
    return out


def make_top5(out_dir, day, slot, data, posts, page_fetcher=None):
    """The week's list carousel: the first app (planner order, not featured this week) whose comparison page in a
    slot locale has our row and at least 3 other developers in the 5. None when no app fits."""
    page_fetcher = page_fetcher or (lambda url: fetch(url, timeout=30).decode("utf-8"))
    week_apps, _ = recent(posts, day, APP_COOLDOWN_DAYS)
    clips = data.get("clips", {})
    order = app_order(data)
    order = [a for a in TOP5_FIRST if a in order] + [a for a in order if a not in TOP5_FIRST]
    for app in order:
        if app in week_apps or app.endswith("_b"):
            continue
        for locale in SLOT_LOCALES.get(slot) or SLOT_LOCALES[19]:
            clip = clips.get(f"{app}/{locale}")
            if not clip or not clip.get("store_url") or locale not in TOP5_TEXT:
                continue
            try:
                snap = parse_compare(page_fetcher(compare_url(app, locale)))
            except Exception:
                continue
            picks = top5_rows(snap["rows"]) if snap else None
            if not picks:
                continue
            t = TOP5_TEXT[locale]
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            cards = [compose_text_card([t["hook"].format(term=snap["term"]), t["sub"].format(date=snap["date"])],
                                       clip, out_dir / "01.jpg", footer=True).name]
            for i, r in enumerate(picks):
                body = [f"{r['rank']}", r["app"], r["dev"]]
                if r["rating"] not in ("", "—", "-"):
                    body.append(t["rating"].format(rating=r["rating"], count=r["count"]))
                body.append(t["updated"].format(date=r["updated"]))
                if r["ours"] and r["rank"] > 5:
                    body.insert(1, t["pos"].format(rank=r["rank"]))
                cards.append(compose_text_card(body, clip, out_dir / f"{i + 2:02d}.jpg",
                                               badge=t["badge"] if r["ours"] else None, footer=r["ours"]).name)
            listed = sorted({x for r in picks if not r["ours"] for x in (r["app"], r["dev"])})
            plan = {"key": f"{KEY_PREFIX}{app}/{locale}/top5/{day.isoformat()}", "app": app, "locale": locale,
                    "slot": slot, "date": day.isoformat(), "variant": "top5", "cards": cards,
                    "caption": top5_caption(clip, snap, picks), "store_url": clip["store_url"],
                    "name": clip.get("name", ""), "alt": t["hook"].format(term=snap["term"]), "listed": listed,
                    "source": compare_url(app, locale)}
            (out_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
            return plan
    return None


# ---------------------------------------------------------------- queued carousels (00_GrowthEngine social/carousel)
#
# 2026-10-22 (carousel line): 5-card carousels built in 00_GrowthEngine (social/carousel/build_carousels.py) from the
# apps' public App Store screenshots, published on this repo's public release "carousel-cards" and queued in
# .github/growth/carousels.json: "pain" (situation -> fix -> app) and "top5" (5 apps for X, ours marked, at least 3
# other developers' apps by name and objective fact only). They take the slot after the weekly list carousel and
# before the plain screenshot carousel, so the day's allowance (volume-ramp.json) and the weekly app cooldown still
# decide how many go out. Each carousel goes out once (key feed/<app>/<locale>/carousel/<id>).
QUEUE = HERE.parent / "growth" / "carousels.json"
QUEUE_SLOT_LOCALES = {7: ["zh-Hant", "ja", "ko", "de"], 19: ["en", "pt-BR"]}


def queued_caption(entry):
    """Instagram caption of a queued carousel: its text, the profile-link line and the brand hashtag first."""
    limit = SC.TAG_LIMIT.get("instagram", 5)
    tags = IGB.hashtags(lambda n: [t for t in entry.get("tags") or [] if isinstance(t, str)][:n], entry["name"],
                        entry["store_url"], limit)
    text = "\n".join([entry["text"], IGB.bio_line(entry["locale"])] + (["", " ".join(tags)] if tags else []))
    return IGB.caption(text, entry["name"], entry["locale"], entry["store_url"], max_len=post_qa.LIMITS["instagram"],
                       tag_limit=limit, label=f"feed carousel {entry['id']}")


def make_queued(out_dir, day, slot, posts, fetcher=fetch, path=None):
    """The first due queued carousel for the slot's locales whose app is not featured this week; its cards are
    downloaded into out_dir (the workflow republishes them on the feed-cards branch). None when nothing fits."""
    try:
        queue = json.loads(Path(path or QUEUE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    week_apps, _ = recent(posts, day, APP_COOLDOWN_DAYS)
    done = {p.get("clip") for p in posts or [] if p.get("channel") == CHANNEL}
    locales = QUEUE_SLOT_LOCALES.get(slot) or QUEUE_SLOT_LOCALES[19]
    for e in queue.get("items") or []:
        key = f"{KEY_PREFIX}{e.get('app')}/{e.get('locale')}/carousel/{e.get('id')}"
        if ("instagram" not in (e.get("channels") or []) or e.get("locale") not in locales or key in done
                or str(e.get("start") or "9999") > day.isoformat() or e.get("app") in week_apps):
            continue
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        cards = []
        try:
            for i, url in enumerate(e.get("images") or []):
                (out / f"{i + 1:02d}.jpg").write_bytes(fetcher(url))
                cards.append(f"{i + 1:02d}.jpg")
        except Exception as exc:  # a missing card skips this carousel, never half of it
            print(f"feed: queued carousel {e.get('id')} not downloadable ({exc.__class__.__name__}); next one")
            for c in cards:
                (out / c).unlink(missing_ok=True)
            continue
        if len(cards) < CARDS_MIN:
            continue
        store = (f"https://apps.apple.com/{str(e['country']).lower()}/app/id{e['app_id']}"
                 f"?pt=118326163&ct={feed_ct_token(e['app'], e['app_id'])}&mt=8")
        entry = dict(e, store_url=store)
        plan = {"key": key, "app": e["app"], "locale": e["locale"], "slot": slot, "date": day.isoformat(),
                "variant": f"carousel-{e.get('format')}", "cards": cards, "caption": queued_caption(entry),
                "store_url": store, "name": e["name"], "alt": (e.get("alt") or e["hook"])[:1000],
                "listed": list(e.get("listed") or []), "source": e.get("source")}
        problems = qa(plan, online=False)
        if problems:  # a queued carousel the gate would refuse never takes the slot: the next one does
            print(f"feed: queued carousel {e.get('id')} skipped ({problems[0]})")
            for c in cards:
                (out / c).unlink(missing_ok=True)
            continue
        (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        return plan
    return None


def feed_ct_token(app, app_id):  # the carousel family token h7_<app>_igc, sent at the app's level
    import download_links as DL
    return DL.app_campaign(f"h7_{app}_{FEED_CT}", str(app_id))


def make(out_dir, day, slot, data=None, posts=None, fetcher=fetch):
    """Render the slot's carousel into out_dir (NN.jpg + plan.json). Returns the plan, or None (nothing due,
    allowance used up, no screenshots)."""
    data = data or load_clips()
    posts = clip_posts.posted_log() if posts is None else posts
    allowed, done, left = volume_ramp.room(volume_ramp.load(), CHANNEL, day, posts)
    if left is not None and left <= 0:
        print(f"feed: {done} of today's {allowed} carousels already out (volume-ramp.json); nothing to make")
        return None
    if top5_due(posts, day):
        plan = make_top5(out_dir, day, slot, data, posts,
                         page_fetcher=lambda url: fetcher(url).decode("utf-8", "replace"))
        if plan:
            print(f"feed: list carousel {plan['key']} from {plan['source']}")
            return plan
        print("feed: no list carousel fits this slot; the screenshot carousel instead")
    plan = make_queued(out_dir, day, slot, posts, fetcher=fetcher)
    if plan:
        print(f"feed: queued carousel {plan['key']}")
        return plan
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
    """The caption as Instagram takes it (owner 2026-10-17): no URL, the profile-link line, the app's brand
    hashtag. The clip caption already is so; this is the last guard before the send (a caption that cannot be
    made so raises MissingDownloadLink and nothing is posted)."""
    return IGB.caption(plan["caption"], plan.get("name", ""), plan["locale"], plan["store_url"],
                       max_len=post_qa.LIMITS["instagram"], tag_limit=SC.TAG_LIMIT.get("instagram", 5),
                       label=f"feed {plan['key']}")


def post_instagram(plan, base_url, wait=PAUSE, tries=40):
    """Carousel container from the published card URLs, published; {"id", "link"} or None without a token."""
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        print("feed: IG_ACCESS_TOKEN not set, carousel skipped")
        return None
    caption = checked_caption(plan)   # before any upload: a caption that cannot go out stops the whole carousel
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
        "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption,
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
                                 name=plan["name"], online=online, require_bio=True, listed=tuple(plan.get("listed", ())))


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
    if CR.paused_notice("instagram"):  # channel rotation holdout week: no Instagram feed post, green
        return 0
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
