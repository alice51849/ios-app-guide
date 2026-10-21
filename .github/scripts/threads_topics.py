#!/usr/bin/env python3
"""Threads topic tag (the `topic_tag` field of a post container) and the existing-user review line of the
first (link) reply.

Threads API, Posts (developers.facebook.com/docs/threads/posts, "Topic tags" > "Using the topic_tag
parameter"): "You can include a topic in a post either by using the `topic_tag` parameter or by including a
tag within the text of a post." "Topic tags must be at least 1 character and no more than 50 characters long."
Periods (.) and ampersands (&) are not allowed; one topic per post; the tag is sent without the hash sign.

- clean(tag): the tag to send, or None (missing, or not valid: a ::warning:: says why and the post goes out
  without a topic - a topic never stops a post).
- for_post(app_id, text, lang, explicit): the post's own "topic_tag" when it has one, else the default topic
  of the app's category (apps.json) in the post's language; None for an app or category we have no topic for.
- review_tail(links, app_id, lang, limit): the link reply plus, after the download links, the neutral
  existing-user review line of review_links.py (no reward, no star prompt, no ct) - only when it fits whole.
"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import review_links

HERE = Path(__file__).resolve().parent
APPS = HERE.parent.parent / "apps.json"
MAX_LEN = 50
FORBIDDEN = re.compile(r"[.&\r\n]")
KANA = re.compile(r"[぀-ゟ゠-ヺヽ-ヿ]")
HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힯]")
HAN = re.compile(r"[一-鿿]")

# apps.json category -> topic per language (en / zh = Traditional Chinese / ja / ko).
CATEGORY_TOPICS = {
    "Productivity": {"en": "Productivity", "zh": "效率", "ja": "仕事効率化", "ko": "생산성"},
    "Education": {"en": "Studying", "zh": "讀書", "ja": "勉強", "ko": "공부"},
    "Kids & learning": {"en": "Parenting", "zh": "育兒", "ja": "子育て", "ko": "육아"},
    "Photo & utility": {"en": "iPhone Tips", "zh": "iPhone 技巧", "ja": "iPhone活用", "ko": "아이폰 꿀팁"},
    "Money & travel": {"en": "Personal Finance", "zh": "理財", "ja": "節約", "ko": "재테크"},
    "Travel": {"en": "Travel", "zh": "旅行", "ja": "旅行", "ko": "여행"},
    "Health": {"en": "Health", "zh": "健康", "ja": "健康", "ko": "건강"},
    "Lifestyle": {"en": "Lifestyle", "zh": "生活", "ja": "暮らし", "ko": "일상"},
    "Sleep & focus": {"en": "Sleep", "zh": "睡眠", "ja": "睡眠", "ko": "수면"},
    "More": {"en": "iPhone Apps", "zh": "iPhone App", "ja": "iPhoneアプリ", "ko": "아이폰 앱"},
}


def _warn(message):
    print(f"::warning::Threads topic tag: {message}; posted without a topic", file=sys.stderr)


def clean(tag):
    """The topic to send (stripped, without a leading '#'), or None when there is none or it is not valid."""
    if tag is None:
        return None
    if not isinstance(tag, str):
        _warn(f"not text ({type(tag).__name__})")
        return None
    tag = tag.strip().lstrip("#").strip()
    if not tag:
        _warn("empty")
        return None
    if len(tag) > MAX_LEN:
        _warn(f"{len(tag)} characters (at most {MAX_LEN})")
        return None
    if FORBIDDEN.search(tag):
        _warn(f"{tag!r} holds a period, an ampersand or a line break")
        return None
    return tag


def lang_of(text, lang=None):
    """The post's base language ('en', 'zh', 'pt' ...) from its locale, else 'en' / 'zh' / 'ja' / 'ko' from its script."""
    base = (lang or "").split("-")[0].lower()
    if base:
        return base  # a language without a CATEGORY_TOPICS entry gets no default topic
    text = text or ""
    if HANGUL.search(text):
        return "ko"
    if KANA.search(text):
        return "ja"
    if HAN.search(text):
        return "zh"
    return "en"


def locale_of(text, lang=None):
    """The review_links.py locale of a post (its own when it has one)."""
    if lang:
        return lang
    return {"en": "en-US", "zh": "zh-Hant", "ja": "ja", "ko": "ko"}[lang_of(text)]


@lru_cache(maxsize=1)
def _categories():
    try:
        rows = json.loads(APPS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for row in rows if isinstance(rows, list) else []:
        app_id = review_links.store_app_id(str((row or {}).get("appStoreUrl") or ""))
        if app_id and row.get("category"):
            out[app_id] = row["category"]
    return out


def default_topic(app_id, text, lang=None):
    topics = CATEGORY_TOPICS.get(_categories().get(str(app_id or "")))
    return topics.get(lang_of(text, lang)) if topics else None


def for_post(app_id, text, lang=None, explicit=None):
    """The topic a post is sent with: its own "topic_tag", else its app category's default; None for none."""
    return clean(explicit if explicit is not None else default_topic(app_id, text, lang))


def review_tail(links, app_id, lang=None, text="", limit=500):
    """`links` (the reply's download links) plus the neutral existing-user review line when it fits whole."""
    rate = review_links.for_official(str(app_id or ""), locale_of(text, lang), any_app=True)
    if not rate:
        return links
    tail = links + "\n📝 " + "\n".join(review_links.lines(rate))
    return tail if len(tail) <= limit else links
