#!/usr/bin/env python3
"""Existing-user App Store review link for the few App x country pairs where it can flip the category.

review_links.json lists the pairs whose category leader has 20 ratings or fewer
(00_GrowthEngine reports/top1_gap_2026-10-16.md): there one to three ratings
can move us to the top. Only those pairs, in their own locale, get one neutral
line plus Apple's direct review action on the posts that carry clickable links:

- telegram_post.py   the daily text post (official locale, e.g. ko / de-DE / en-US);
- clip_posts.py      the Telegram hook clip caption (clip locale, e.g. ko / de / en);
- social_extra.py    the feed items ("review" field: the YouTube Shorts description,
                     threads-autopilot's Bluesky posts) and the link lines of the
                     extra platforms.

Rules kept here: the sentence is the existing-user line of 00_GrowthEngine
geo/gen_app_store_review_ctas.py, word for word (no reward, no star prompt, no
price, no superlative); the link is exactly
https://apps.apple.com/app/id<N>?action=write-review (no pt / ct / mt: it is not
a download CTA); a pair is matched by App Store ID, never by app key, so a
renamed clip key (UsageNow ships as claudeusagemini) still matches.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "review_links.json"
SCHEMA = "lumi.review-links/v1"
APP_ID_RE = re.compile(r"\d{9,12}")
REVIEW_URL_RE = re.compile(r"https://apps\.apple\.com/app/id(\d{9,12})\?action=write-review")
STORE_ID_RE = re.compile(r"^https://apps\.apple\.com/(?:[a-z]{2}/)?app/(?:[^/?#]+/)?id(\d{9,12})(?:[?#]|$)")
# Same guard as geo/gen_app_store_review_ctas.py INCENTIVE_RE: the line may ask for a rating,
# never promise anything for it or suggest which rating to give.
INCENTIVE_RE = re.compile(
    r"\b(?:5|five)[- ]?stars?\b|★|⭐|\breward|\bgift|\bfree\b|\bunlock|\bdiscount|\bcoupon|"
    r"\bprize|\bgiveaway|\bpro\b|五星|星5|별점\s?5|5점|免費|無料|무료|kostenlos|\$|NT\$|¥|€|₩",
    re.IGNORECASE,
)
SUPERLATIVE_RE = re.compile(r"\bbest\b|#\s?1\b|最好|最佳|第一|最高|최고|1위|beste", re.IGNORECASE)


def review_url(app_id):
    app_id = str(app_id)
    if not APP_ID_RE.fullmatch(app_id):
        raise ValueError(f"invalid App Store ID for a review link: {app_id!r}")
    return f"https://apps.apple.com/app/id{app_id}?action=write-review"


def store_app_id(url):
    """The App Store ID of an apps.apple.com product link ('' when it is not one)."""
    match = STORE_ID_RE.match(url or "")
    return match.group(1) if match else ""


def validate(config):
    if not isinstance(config, dict) or config.get("schema") != SCHEMA:
        raise ValueError("review_links.json: wrong schema")
    labels = config.get("labels")
    pairs = config.get("pairs")
    if not isinstance(labels, dict) or not isinstance(pairs, list) or not pairs:
        raise ValueError("review_links.json: labels and pairs are required")
    for locale, label in labels.items():
        if (not isinstance(label, str) or not label.strip() or "\n" in label or "http" in label
                or len(label) > 120 or INCENTIVE_RE.search(label) or SUPERLATIVE_RE.search(label)):
            raise ValueError(f"review_links.json: label {locale!r} must be one neutral line")
    seen = set()
    for pair in pairs:
        key = (pair.get("app_id"), pair.get("country"))
        if (not APP_ID_RE.fullmatch(str(pair.get("app_id") or "")) or key in seen
                or pair.get("official_locale") not in labels or not pair.get("clip_locale")
                or not re.fullmatch(r"[a-z]{2}", str(pair.get("country") or ""))):
            raise ValueError(f"review_links.json: invalid pair {pair!r}")
        seen.add(key)
    return config


@lru_cache(maxsize=1)
def config():
    return validate(json.loads(CONFIG.read_text(encoding="utf-8")))


def _review(pair, cfg):
    return {"label": cfg["labels"][pair["official_locale"]], "url": review_url(pair["app_id"])}


def for_official(app_id, locale, cfg=None):
    """{"label", "url"} for a post in an official locale (telegram_post.py), or None."""
    cfg = cfg or config()
    for pair in cfg["pairs"]:
        if pair["app_id"] == str(app_id) and pair["official_locale"] == locale:
            return _review(pair, cfg)
    return None


def for_clip(clip, cfg=None):
    """{"label", "url"} for a hook clip (clips.json entry: App ID from its store_url), or None."""
    cfg = cfg or config()
    app_id = store_app_id((clip or {}).get("store_url", ""))
    locale = (clip or {}).get("locale")
    for pair in cfg["pairs"]:
        if app_id and pair["app_id"] == app_id and pair["clip_locale"] == locale:
            return _review(pair, cfg)
    return None


def lines(review):
    """The two lines a post carries: the sentence, then the bare link (clickable on every platform)."""
    return [review["label"], review["url"]] if review else []
