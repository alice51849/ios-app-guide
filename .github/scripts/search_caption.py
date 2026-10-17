#!/usr/bin/env python3
"""Search-first captions, alt text and hook-variant choice (deterministic, no model calls).

Our accounts have few followers, so every post has to be found through search
and the platforms' topic / hashtag distribution. The Growth Engine planner
(shorts/scripts/schedule_posts.py + search_intent.py) puts the search fields
into .github/growth/clips.json, from the storyboards and the App Store
keyword data only:

- clip["hooks"]     2-3 variants {"id", "lead", "benefit"} from the storyboard
- clip["keyline"]   the localized subtitle / searchable name part
- clip["keywords"]  ASO keywords in the locale, priority order
- clip["tags"]      3-6 locale-native hashtags derived from those keywords
- clip["hook_best"] the variant post_performance.py ranks first (once data exists)
- data["seo"]       the same fields per app / locale for the daily cards

Every caption starts with the problem line, keeps a keyword phrase inside the
first 125 characters (what Instagram / Threads show and index before "more"),
and ends with at most a handful of tags. Old clips.json entries without these
fields still get a caption (hook + brand tag).
"""
import datetime as dt
import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROWTH = HERE.parent / "growth"
CLIPS = GROWTH / "clips.json"
SEARCH_TERMS = GROWTH / "search-terms.json"  # build_search_terms.py, from the keyword rank history
PERFORMANCE = GROWTH / "performance.json"

FIRST = 125  # characters Instagram / Threads show before "more"
TAG_LIMIT = {"instagram": 5, "threads": 1, "telegram": 3, "bluesky": 3, "facebook": 3, "plurk": 3}
# Generic store / platform tags say nothing a searcher types for a problem.
GENERIC_TAGS = {"#app", "#apps", "#iphoneapps", "#appstore", "#iosapps", "#ios", "#iphone", "#app推薦", "#アプリ紹介",
                "#앱추천", "#아이폰어플", "#iphoneアプリ", "#aplikasiiphone", "#ungdungiphone", "#แอพไอโฟน",
                "#productivity", "#android", "#free",
                # Edition words say nothing a searcher types: they only repeat a part of the brand tag.
                "#探索版", "#完整版", "#免費版", "#lite", "#pro", "#エクスプローラー版", "#탐험판"}


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


FULLWIDTH_PUNCT = "、。，．！？：；」』）】〉》…"


def tidy(line):
    """One caption line as a native writer types it: single spaces, none after full-width punctuation
    ("照片拍糊了？ 秒變清晰" -> "照片拍糊了？秒變清晰", "証明写真、 おうちで" -> "証明写真、おうちで")."""
    line = re.sub(r"\s+", " ", (line or "").replace("*", "")).strip()
    return re.sub(f"([{FULLWIDTH_PUNCT}]) ", r"\1", line)


def dedupe(lines):
    """Drop a line another line already contains (case-insensitive), keeping the longer one in place;
    blank lines are kept as separators."""
    out = []
    for i, line in enumerate(lines):
        low = line.strip().casefold()
        if low and any(low != o.strip().casefold() and low in o.casefold() for o in lines if o.strip()):
            continue
        if low and low in {o.strip().casefold() for o in out}:
            continue
        out.append(line)
    return out


def variants(clip):
    """The clip's hook variants (lines tidied); a clip without them has one: its hook."""
    hooks = [dict(h, lead=tidy(h["lead"]), benefit=tidy(h.get("benefit", ""))) for h in clip.get("hooks") or []
             if h.get("lead")]
    return hooks or [{"id": "a", "lead": tidy(clip.get("hook", "")), "benefit": ""}]


def winners(path=PERFORMANCE):
    return _load(path, {}).get("hook_winners") or {}


def winner(wins, key, locale):
    wins = wins if isinstance(wins, dict) else {}
    return (wins.get("apps") or {}).get(key) or (wins.get("locales") or {}).get(locale) or wins.get("global")


def choose(clip, channel, day, wins=None):
    """Variant to post: rotates across platforms and days; once the performance loop has a winner for this
    clip (or its locale, or overall) the winner goes out two days in three, the rotation keeps testing."""
    hooks = variants(clip)
    if len(hooks) == 1:
        return hooks[0]
    wins = winners() if wins is None else wins
    best = clip.get("hook_best") or winner(wins, f"{clip.get('app')}/{clip.get('locale')}", clip.get("locale"))
    by_id = {h["id"]: h for h in hooks}
    if best in by_id and day.toordinal() % 3:
        return by_id[best]
    spread = sum(map(ord, f"{channel}/{clip.get('app')}/{clip.get('locale')}"))  # not one variant for a whole day
    return hooks[(day.toordinal() + spread) % len(hooks)]


def tags(clip, limit=5):
    """Keyword-derived tags without generic store tags; the brand tag when nothing else is known."""
    out = []
    for t in clip.get("tags") or []:
        t = t if t.startswith("#") else f"#{t}"
        if t.casefold() not in GENERIC_TAGS and t.casefold() not in {x.casefold() for x in out}:
            out.append(t)
    brand = "#" + "".join(ch for ch in clip.get("search", "") if ch.isalnum()) if clip.get("search") else ""
    if not out and brand:
        out = [brand]
    if len(out) > limit > 1 and brand.casefold() in {t.casefold() for t in out}:  # keep the brand tag
        out = [t for t in out if t.casefold() != brand.casefold()][:limit - 1] + [brand]
    return out[:limit]


def body(clip, variant, limit=FIRST):
    """Problem line, benefit, keyword line; the keyword line moves up if it would fall past `limit`."""
    lead, benefit, keyline = tidy(variant.get("lead", "")), tidy(variant.get("benefit", "")), clip.get("keyline", "")
    rest = [x for x in (benefit, keyline) if x and x != lead]
    if keyline and benefit and len("\n".join([lead, benefit, keyline])) > limit:
        rest = [keyline, benefit]
    return [lead, *rest]


def alt_text(clip, variant, limit=500):
    """Accessible description that also carries the search phrase."""
    parts = [clip.get("name", ""), variant.get("lead", ""), variant.get("benefit", ""), clip.get("keyline", "")]
    text = " — ".join(p for i, p in enumerate(parts) if p and not any(p in q for q in parts[:i]))
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def youtube(clip, variant, links, limit=100):
    """(title, description, tags) for a Short: problem phrase + app name + #Shorts in the title."""
    suffix = f" | {clip.get('search') or clip.get('name', '')} #Shorts"
    lead = variant.get("lead", "")
    room = limit - len(suffix)
    title = (lead if len(lead) <= room else lead[:room - 1].rstrip() + "…") + suffix
    hashtags = ["#Shorts", *tags(clip, 2)]
    lines = [*body(clip, variant, 10_000), "", clip.get("name", ""), *links]
    if clip.get("keywords"):
        lines += ["", " · ".join(clip["keywords"])]
    lines += ["", " ".join(hashtags)]
    words, total = [], 0
    for w in [*clip.get("keywords", []), *(t.lstrip("#") for t in tags(clip, 6)), clip.get("search", "")]:
        if w and w.casefold() not in {x.casefold() for x in words} and total + len(w) + 1 <= 450:
            words.append(w)
            total += len(w) + 1
    return title, "\n".join(lines), words


def pin_title(clip, variant, limit=100):
    """Pinterest / Tumblr title: the problem line, then the searchable keyline, then the app."""
    parts = [variant.get("lead", ""), clip.get("keyline", ""), clip.get("search") or clip.get("name", "")]
    title = " | ".join(p for i, p in enumerate(parts) if p and p not in parts[:i])
    return title if len(title) <= limit else title[:limit - 1].rstrip() + "…"


@lru_cache(maxsize=1)
def _feed():
    return _load(CLIPS, {})


def seo_for(app, locale, data=None):
    """{"tags", "keywords", "keyline"} for a card's app and locale ({} when the planner has none)."""
    data = _feed() if data is None else data
    clip = (data.get("clips") or {}).get(f"{app}/{locale}")
    if clip and (clip.get("tags") or clip.get("keyline")):
        return {"tags": clip.get("tags") or [], "keywords": clip.get("keywords") or [],
                "keyline": clip.get("keyline", "")}
    return ((data.get("seo") or {}).get(app) or {}).get(locale) or {}


def card_tags(app, locale, limit=5, data=None):
    return tags({"tags": seo_for(app, locale, data).get("tags") or []}, limit)


def card_alt(name, caption, app, locale, data=None, limit=500):
    """Alt text for a card image: what the card says, the app, and its search phrase."""
    lines = [line for line in caption.split("\n") if line.strip()][:3]
    keyline = seo_for(app, locale, data).get("keyline", "")
    text = " — ".join(p for p in [name, *lines, keyline] if p)
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


@lru_cache(maxsize=1)
def _terms():
    return _load(SEARCH_TERMS, {})


STOREFRONT = re.compile(r"apps\.apple\.com/([a-z]{2})/", re.I)
TERM_MAX_AGE = 21  # days: an older rank reading no longer says where the app stands
MAX_RANK = 10  # past #10 people rarely scroll down to the app: the caption keeps the brand name


def search_term(app, locale, store_url="", fallback="", data=None, day=None):
    """The App Store search term for the caption's search line: the term the app is closest to the top 3 on
    in the post's storefront (the clip's store link first, then the locale's other storefronts: paid there
    in the last 7 days first, then the bigger market), from search-terms.json. `fallback` (the clip's own
    search phrase / store name) when there is no fresh entry in that language."""
    data = _terms() if data is None else data
    app = str(app or "")
    per = ((data.get("apps") or {}).get(app[:-2] if app.endswith("_b") else app) or {})
    if not isinstance(per, dict) or not locale:
        return fallback
    m = STOREFRONT.search(store_url or "")
    others = sorted((sf for sf, e in per.items() if isinstance(e, dict) and e.get("locale") == locale),
                    key=lambda sf: (not per[sf].get("paid"), -float(per[sf].get("weight") or 0), sf))
    day = day or today()
    for sf in ([m.group(1).upper()] if m else []) + others:
        entry = per.get(sf)
        if not isinstance(entry, dict) or entry.get("locale") != locale:
            continue
        term = str(entry.get("term") or "").strip()
        try:
            age = (day - dt.date.fromisoformat(str(entry.get("date")))).days
        except ValueError:
            continue
        try:
            rank = int(entry.get("rank") or 0)
        except (TypeError, ValueError):
            continue
        if term and 1 <= rank <= MAX_RANK and -1 <= age <= TERM_MAX_AGE:
            return term
    return fallback


def clip_search(clip, data=None, day=None):
    """search_term() for a hook clip; its planner search phrase when the rank data has nothing."""
    return search_term(clip.get("app", ""), clip.get("locale", ""), clip.get("store_url", ""),
                       clip.get("search", ""), data=data, day=day)


def today():
    return dt.datetime.now(dt.timezone.utc).date()
