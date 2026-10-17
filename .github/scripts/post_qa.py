#!/usr/bin/env python3
"""Pre-post QA gate: refuse to post a broken or non-compliant promo asset (zero token, free APIs only).

Every automated poster (clip_posts.py, utility_cards.py, countdown_cards.py,
social_extra.py) calls this right before it posts. A post is refused when:

- text is missing: empty caption, empty hook line, no app name / search term,
  no video or store URL, or template leftovers ("{s}", "*accent*", "None");
- the caption is too long for the platform, or carries more hashtags than the
  platform takes;
- the direct download link is missing (download_links.py): the caption must hold the app's App Store
  URL (and its Google Play URL when the app is on Android) - Threads is exempt, its links go in the
  first reply, which clip_posts.py / threads_series.py check themselves;
- an Instagram caption does not say where to tap (its URL cannot be tapped): the profile-link step
  naming the app, "Link in bio → tap “Mochi”" (ig_bio.py);
- the text is in the wrong language: a ja caption without kana, a zh-Hant
  caption with Simplified-only characters or kana / Hangul, an English template
  line ("Search ... on the App Store", "Link in bio") in another locale;
- a claim is banned or unsupported: superlatives / rankings ("best", "#1",
  最好, 世界一, 최고...), a competitor app's name, or "free" / "no ads" /
  "no subscription" / "one-time purchase" and feature counts that the product
  page (store name, subtitle, live description, price) does not state;
- a link is dead (only when online): the App Store lookup has no such app in
  that storefront, or the video URL answers 404 / 410. Network trouble never
  blocks a post; only a definite "not there" does.

    python3 post_qa.py audit            # every clip x channel in clips.json, offline
    python3 post_qa.py audit --online   # plus store / video link checks and product-page facts
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

import download_links as DL

HERE = Path(__file__).resolve().parent
CLIPS = HERE.parent / "growth" / "clips.json"
UA = "lumi-post-qa/1.0"

# Platform caption limits (characters; Bluesky counts graphemes, len() is close for our text).
LIMITS = {"telegram": 1024, "instagram": 2200, "threads": 500, "bluesky": 300, "mastodon": 500, "plurk": 360,
          "facebook": 5000, "pinterest": 800, "tumblr": 4096, "naver": 10000, "youtube": 5000, "dailymotion": 3000}
MAX_TAGS = {"instagram": 5, "threads": 1, "telegram": 3, "bluesky": 3, "facebook": 3, "plurk": 3, "mastodon": 5,
            "pinterest": 10, "tumblr": 10, "naver": 10, "youtube": 15, "dailymotion": 10}
FIRST_LINE_MAX = 90  # the hook line has to fit the platforms' one-line preview

HAN = re.compile(r"[㐀-䶿一-鿿]")
KANA = re.compile(r"[぀-ゟ゠-ヺヽ-ヿ]")  # kana, without the shared middle dot / long mark
HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힯]")
SCRIPT = {"el": re.compile(r"[Ͱ-Ͽ]"), "ar": re.compile(r"[؀-ۿ]"), "fa": re.compile(r"[؀-ۿ]"),
          "ur": re.compile(r"[؀-ۿ]"), "he": re.compile(r"[֐-׿]"), "th": re.compile(r"[฀-๿]"),
          "ru": re.compile(r"[Ѐ-ӿ]"), "uk": re.compile(r"[Ѐ-ӿ]"), "hi": re.compile(r"[ऀ-ॿ]"),
          "mr": re.compile(r"[ऀ-ॿ]")}
# Simplified-only forms (their Traditional form differs and they do not occur in Traditional text).
SIMPLIFIED = set("这们说时么为发会过还进个东书来对开关门问间题种动视频应该习让认识设计页码软载画网络电脑号线车买卖"
                 "价钱银红绿蓝颜亲爱气头险护证务单记录简报币汇历实轻击图库语终机写边")
# English template lines that must never show up in another locale's caption.
ENGLISH_TEMPLATE = re.compile(r"on the App Store|Get it on the App Store|Also on Google Play|Search [“\"]|"
                              r"on App Store or Google Play|\bLink in bio\b", re.I)
LINK_IN_BIO_NATIVE = {"en", "nl", "da"}  # "Link in bio" is the native phrase there

SUPERLATIVE = re.compile(
    r"\bbest\b|#\s?1\b|\bno\.?\s?1\b|\bnumber one\b|\btop[- ]rated\b|\bbest[- ]selling\b|\bworld'?s first\b|"
    r"\bthe only app\b|最好|最佳|最棒|最強|最强|第一名|唯一一款|世界一|日本一|世界初|ナンバーワン|No\.1|1위|최고(?!\s*기록)|"
    r"\bdie beste\b|\bterbaik\b|\btốt nhất\b|\bnejlepší\b|\bnajlepsz", re.I)
# Other companies' apps: only named when the product page itself names them (e.g. what an app tracks).
COMPETITORS = ["CamScanner", "Adobe Scan", "Genius Scan", "Microsoft Lens", "Evernote", "Notion", "Todoist", "TickTick",
               "Any.do", "Things 3", "Duolingo", "Memrise", "Quizlet", "Remini", "Picsart", "VSCO", "Snapseed",
               "Lightroom", "Facetune", "Meitu", "BeautyPlus", "Opal app", "Flo Period", "Clue Period", "Headspace",
               "BetterSleep", "WinZip", "iZip", "TripIt", "Wanderlog", "Splitwise", "Moneyforward", "マネーフォワード",
               "Zaim", "Gemini Photos", "Otter.ai", "Notta", "Canva", "Grammarly", "Zety", "Instapaper", "Raindrop.io",
               "Widgetsmith", "TimeTree", "Fantastical", "Google Keep", "GoodNotes", "Notability", "ChatGPT",
               "Brainly", "Photomath", "Babbel", "Moneybook", "CleanMyPhone", "Calm app"]
# (Plain words that are also app names - Forest, Calm, Pocket, Speak, Cake - are left out: they occur in ordinary copy.)
COMPETITOR_RE = re.compile(r"(?<![\w])(" + "|".join(re.escape(c) for c in COMPETITORS) + r")(?![\w])")
# Claims that need the product page behind them: category -> (claim pattern, backing pattern).
CLAIMS = {
    "free": (re.compile(r"\bfree\b(?!\s+up)(?<!hands-free)|免費|免费|無料|무료|\bgratis\b|kostenlos|miễn phí|gratuit|"
                        r"zdarma|darmow", re.I),
             re.compile(r"\bfree\b|免費|免费|無料|무료|gratis|kostenlos|miễn phí|gratuit|zdarma|darmow", re.I)),
    "no ads": (re.compile(r"no ads|ad-free|ad free|zero ads|無廣告|零廣告|沒有廣告|不含廣告|无广告|広告なし|広告ゼロ|"
                          r"광고\s?없|tanpa iklan|không quảng cáo|keine werbung|bez reklam", re.I),
               re.compile(r"no ads|ad-free|ad free|zero ads|without ads|無廣告|零廣告|沒有廣告|不含廣告|无广告|広告なし|"
                          r"広告ゼロ|広告は表示されません|광고\s?없|tanpa iklan|không quảng cáo|keine werbung|bez reklam", re.I)),
    "no subscription": (re.compile(r"no subscription|without (a )?subscription|免訂閱|不用訂閱|無訂閱|无订阅|サブスクなし|"
                                   r"サブスク不要|구독\s?없|tanpa langganan|bez předplatného", re.I),
                        re.compile(r"no subscription|without (a )?subscription|免訂閱|不用訂閱|無訂閱|无订阅|サブスクなし|"
                                   r"サブスク不要|구독\s?없|tanpa langganan|bez předplatného", re.I)),
    "one-time purchase": (re.compile(r"one-time purchase|pay once|買斷|买断|買い切り|평생 이용|일회성 구매", re.I),
                          re.compile(r"one-time|one time|pay once|買斷|买断|買い切り|평생|일회성", re.I)),
}
# A count with a unit ("35 種", "101 cute themes", "13 formats") is a feature claim.
COUNT = re.compile(r"(?<![\w.])(\d{2,}\+?)\s?(?=[^\d\s%:/.,]|$)")
URL = re.compile(r"https?://\S+")
TAG = re.compile(r"(?<!\w)#\S+")
LEFTOVER = re.compile(r"\{[a-z_]*\}|\*[^*\n]+\*|\bNone\b|\bnull\b|\bundefined\b|\bTODO\b|\\n")


def _strip(text, allowed=()):
    text = URL.sub(" ", text)
    text = TAG.sub(" ", text)
    for a in sorted((a for a in allowed if a and len(a.strip()) >= 3), key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(a.strip()) + r"(?!\w)", " ", text)  # whole names only
    return text


def locale_problems(text, locale, allowed=()):
    """Wrong-language text in a caption (app names, search terms, URLs and hashtags excluded)."""
    body = _strip(text, allowed)
    lang = locale.split("-")[0]
    out = []
    if locale in ("zh-Hant", "zh-TW", "zh-HK"):
        if not HAN.search(body):
            out.append("zh-Hant caption has no Chinese text")
        bad = sorted({ch for ch in body if ch in SIMPLIFIED})
        if bad:
            out.append(f"zh-Hant caption uses Simplified characters: {''.join(bad)}")
        if KANA.search(body) or HANGUL.search(body):
            out.append("zh-Hant caption contains Japanese kana or Korean Hangul")
    elif lang == "zh":
        if not HAN.search(body):
            out.append(f"{locale} caption has no Chinese text")
        if KANA.search(body) or HANGUL.search(body):
            out.append(f"{locale} caption contains Japanese kana or Korean Hangul")
    elif lang == "ja":
        if not KANA.search(body):
            out.append("ja caption has no kana: not Japanese")
        if HANGUL.search(body):
            out.append("ja caption contains Korean Hangul")
    elif lang == "ko":
        if not HANGUL.search(body):
            out.append("ko caption has no Hangul: not Korean")
        if KANA.search(body):
            out.append("ko caption contains Japanese kana")
    elif lang in SCRIPT:
        if not SCRIPT[lang].search(body):
            out.append(f"{locale} caption has no text in its own script")
    else:  # Latin-script locales
        if HAN.search(body) or KANA.search(body) or HANGUL.search(body):
            out.append(f"{locale} caption contains CJK text")
    if lang != "en":
        for m in ENGLISH_TEMPLATE.finditer(body):
            if m.group(0).lower() == "link in bio" and lang in LINK_IN_BIO_NATIVE:
                continue
            out.append(f"{locale} caption contains the English template line {m.group(0)!r}")
            break
    return out


def lead_problems(lead, locale, allowed=()):
    """The hook line itself must be in the locale's script (the template lines around it can be right while
    the hook is not): zh -> Chinese characters, ja -> kana or kanji, ko -> Hangul, Latin locales -> no CJK."""
    body = _strip(lead or "", allowed)
    lang = locale.split("-")[0]
    cjk = HAN.search(body) or KANA.search(body) or HANGUL.search(body)
    ok = {"zh": bool(HAN.search(body)), "ja": bool(HAN.search(body) or KANA.search(body)) and not HANGUL.search(body),
          "ko": bool(HANGUL.search(body))}.get(lang)
    if ok is None:
        ok = bool(SCRIPT[lang].search(body)) if lang in SCRIPT else not cjk
    return [] if ok else [f"hook line {lead!r} is not in {locale}"]


def claim_problems(text, allowed=(), facts="", price=None):
    """Banned claims, competitor names and product-page-unsupported claims.

    allowed = the app's own name / search term (may contain anything); facts = product-page text
    (store name, subtitle, live description); price = live store price when known."""
    body = _strip(text, allowed)
    facts_low = (facts or "").casefold()
    out = []
    m = SUPERLATIVE.search(body)
    if m:
        out.append(f"superlative or ranking claim {m.group(0)!r}")
    for m in COMPETITOR_RE.finditer(body):
        if m.group(1).casefold() not in facts_low:
            out.append(f"competitor name {m.group(1)!r} that the product page does not name")
    for name, (claim, backing) in CLAIMS.items():
        m = claim.search(body)
        if not m:
            continue
        if name == "free" and price == 0:
            continue
        if not backing.search(facts or ""):
            out.append(f"{name!r} claim ({m.group(0)!r}) is not on the product page")
    return out


EN_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                        "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
EN_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
ZH_DIGIT = {ch: i for i, ch in enumerate("零一二三四五六七八九")} | {"兩": 2, "两": 2}


def spelled_numbers(text):
    """Numbers written out in words: "One hundred themes" -> 100, "四十六種" -> 46, "thirty-five" -> 35."""
    out = set()
    low = (text or "").casefold()
    for m in re.finditer(r"\b(?:(a|one|two|three|four|five|six|seven|eight|nine)\s+hundred(?:\s+and)?\s*)?"
                         r"(?:(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[- ]?)?"
                         r"(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                         r"fifteen|sixteen|seventeen|eighteen|nineteen)?\b", low):
        hundreds, tens, units = m.groups()
        if not (hundreds or tens or units):
            continue
        out.add((100 * (1 if hundreds == "a" else EN_UNITS.get(hundreds, 0)) if hundreds else 0)
                + EN_TENS.get(tens, 0) + EN_UNITS.get(units, 0))
    for m in re.finditer(r"[零一二兩两三四五六七八九十百]+", text or ""):
        s, total, cur = m.group(0), 0, 0
        for ch in s:
            if ch in ZH_DIGIT:
                cur = ZH_DIGIT[ch]
            elif ch == "十":
                total += (cur or 1) * 10
                cur = 0
            elif ch == "百":
                total += (cur or 1) * 100
                cur = 0
        out.add(total + cur)
    return {str(n) for n in out if n >= 10}


def count_problems(lines, facts):
    """Counts in the hook lines ("35 種", "101 themes") that the product page text never states."""
    digits = set(re.findall(r"\d+", facts or "")) | spelled_numbers(facts)
    out = []
    for line in lines:
        for m in COUNT.finditer(line or ""):
            n = m.group(1).rstrip("+")
            if n not in digits:
                out.append(f"count {m.group(1)!r} in {line!r} is not on the product page")
    return out


def text_problems(text, locale, channel, *, allowed=(), facts="", price=None, first_line=True, length=True):
    """Everything about the words of one post (length=False for posters that trim to the platform limit)."""
    out = []
    if not (text or "").strip():
        return ["caption is empty"]
    limit = LIMITS.get(channel)
    if length and limit and len(text) > limit:
        out.append(f"caption is {len(text)} characters; {channel} takes {limit}")
    tags = TAG.findall(text)
    if channel in MAX_TAGS and len(tags) > MAX_TAGS[channel]:
        out.append(f"{len(tags)} hashtags; {channel} takes {MAX_TAGS[channel]}")
    lead = text.strip().split("\n")[0]
    if first_line and len(lead) > FIRST_LINE_MAX:
        out.append(f"hook line is {len(lead)} characters; it must fit the one-line preview ({FIRST_LINE_MAX})")
    m = LEFTOVER.search(_strip(text, allowed))
    if m:
        out.append(f"template leftover {m.group(0)!r}")
    out += locale_problems(text, locale, allowed)
    if first_line:
        out += lead_problems(lead, locale, allowed)
    out += claim_problems(text, allowed, facts, price)
    return out


# ------------------------------------------------------------------ live links and product-page facts

def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def offline():
    """POST_QA_OFFLINE=1 (tests, previews): no network lookups; link checks pass, facts come from the feed."""
    return os.environ.get("POST_QA_OFFLINE") == "1"


@lru_cache(maxsize=None)
def store_lookup(app_id, country):
    """The App Store record for an app in a storefront: dict, {} when the app is not there, None on network trouble."""
    if offline():
        return None
    try:
        data = _get_json(f"https://itunes.apple.com/lookup?id={app_id}&country={country}")
    except (OSError, ValueError, urllib.error.URLError):
        return None
    results = data.get("results") or []
    return results[0] if results else {}


@lru_cache(maxsize=None)
def url_status(url):
    """HTTP status of a HEAD request (None on network trouble)."""
    if offline():
        return None
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (OSError, ValueError):
        return None


def store_ref(store_url):
    """(app id, storefront country) from an apps.apple.com link."""
    parts = urllib.parse.urlsplit(store_url or "")
    m = re.search(r"/id(\d+)", parts.path)
    country = (parts.path.strip("/").split("/") or ["us"])[0]
    return (m.group(1) if m else ""), (country if len(country) == 2 else "us")


def link_problems(store_url, media_url=None):
    """Dead App Store link (app missing from that storefront) or dead media URL. Network trouble passes."""
    out = []
    app_id, country = store_ref(store_url)
    if not app_id:
        out.append(f"store link has no app id: {store_url!r}")
    else:
        rec = store_lookup(app_id, country)
        if rec == {}:
            out.append(f"App Store has no app id{app_id} in the {country.upper()} storefront (dead store link)")
    if media_url:
        status = url_status(media_url)
        if status in (404, 410):
            out.append(f"media URL answers {status}: {media_url}")
    return out


def product_facts(store_url, extra=()):
    """(facts text, price) from the live product page plus the given store-backed strings; price None offline."""
    app_id, country = store_ref(store_url)
    rec = store_lookup(app_id, country) if app_id else None
    parts = [*extra]
    price = None
    if rec:
        parts += [rec.get("trackName", ""), rec.get("description", "")]
        price = rec.get("price")
        if country != "us":  # counts and claims are the same app facts in the US description
            us = store_lookup(app_id, "us")
            if us:
                parts.append(us.get("description", ""))
    return "\n".join(p for p in parts if p), price


# ------------------------------------------------------------------ the gates

# Channels whose main text is not required to hold the link: Threads keeps links in the first reply
# (the old account was limited for linked posts); the poster checks that reply itself.
LINK_EXEMPT = {"threads"}


def download_link_problems(text, store_url, channel, play_url=None):
    """The post must carry the app's direct download link (App Store, and Google Play when it is on Android)."""
    if channel in LINK_EXEMPT:
        return []
    if play_url is None:
        from social_post_common import android_apps, play_store_url
        if not android_apps():  # an unreadable snapshot would silently drop every Google Play link
            return [f"{channel} text: the Android snapshot (_engine/geo/data/android_live_snapshot.json) is missing or "
                    "empty, so the Google Play links cannot be checked"]
        app_id = DL.app_store_id(store_url)
        play_url = play_store_url(app_id, "qa") if app_id else None
    return DL.link_problems(text, store_url, play_url, label=f"{channel} text")


def bio_problems(text, locale, name, channel):
    """Instagram only: a caption URL cannot be tapped, so the text must say where to tap - the profile link,
    then the app by name ("Link in bio → tap “Mochi”", ig_bio.py). Other channels have tappable links."""
    if channel != "instagram":
        return []
    import ig_bio
    return ig_bio.bio_problems(text, locale, name, label=f"{channel} text")


def clip_problems(clip, channel, text, online=True, length=True):
    """Everything that should stop one hook clip post on one channel."""
    out = []
    for field in ("url", "store_url", "name", "search", "locale"):
        if not (clip.get(field) or "").strip():
            out.append(f"clip has no {field}")
    hooks = clip.get("hooks") or [{"lead": clip.get("hook", "")}]
    if not any((h.get("lead") or "").strip() for h in hooks):
        out.append("clip has no hook line")
    store_text = [clip.get("name", ""), clip.get("keyline", "")]
    facts, price = product_facts(clip.get("store_url", ""), store_text) if online else ("\n".join(store_text), None)
    allowed = (clip.get("name", ""), clip.get("search", ""))
    out += text_problems(text, clip.get("locale", ""), channel, allowed=allowed, facts=facts, price=price, length=length)
    out += download_link_problems(text, clip.get("store_url", ""), channel)
    if clip.get("name"):
        out += bio_problems(text, clip.get("locale", ""), clip["name"], channel)
    if online:
        live = facts != "\n".join(p for p in store_text if p)
        if live:  # counts are only checked against a live description
            lines = [x for h in hooks for x in (h.get("lead"), h.get("benefit")) if x]
            out += count_problems([x for x in lines if x in text], facts)
        out += link_problems(clip.get("store_url", ""), clip.get("url"))
    return out


def card_problems(text, locale, channel, *, store_url, name, image=None, extra_facts=(), online=True, length=True,
                  require_link=True, require_bio=False):
    """Everything that should stop one image card post. require_bio: an Instagram text must also say where to
    tap (bio_problems); the card posters whose captions carry that line pass it."""
    out = []
    if image is not None:
        p = Path(image)
        if not p.is_file() or p.stat().st_size < 10_000:
            out.append(f"card image missing or empty: {image}")
    facts, price = product_facts(store_url, (name, *extra_facts)) if online else ("\n".join((name, *extra_facts)), None)
    out += text_problems(text, locale, channel, allowed=(name,), facts=facts, price=price, length=length)
    if require_link:
        out += download_link_problems(text, store_url, channel)
    if require_bio:
        out += bio_problems(text, locale, name, channel)
    if online:
        out += link_problems(store_url)
    return out


def gate(problems, label):
    """True when the post may go out; otherwise prints why it was refused."""
    if not problems:
        return True
    for p in problems:
        print(f"::error::{label}: QA refused: {p}")
    return False


def audit(online=False, path=CLIPS):
    import clip_posts
    import search_caption as SC
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = 0
    for key, clip in sorted(data.get("clips", {}).items()):
        for channel in ("telegram", "instagram", "threads"):
            for v in SC.variants(clip):
                try:
                    text = clip_posts.caption(clip, channel, v)
                except (KeyError, ValueError) as exc:
                    gate([f"caption cannot be built: {exc}"], f"{key} {channel} hook {v.get('id')}")
                    bad += 1
                    continue
                problems = clip_problems(clip, channel, text, online=online)
                if problems:
                    bad += 1
                    gate(problems, f"{key} {channel} hook {v.get('id')}")
    print(f"post_qa: {len(data.get('clips', {}))} clips audited, {bad} refused captions")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit"])
    ap.add_argument("--online", action="store_true")
    args = ap.parse_args()
    return audit(online=args.online)


if __name__ == "__main__":
    sys.exit(main())
