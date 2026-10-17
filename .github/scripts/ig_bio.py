#!/usr/bin/env python3
"""Instagram's only tappable link is the profile (bio) link: where it points and how a post points to it.

Instagram never turns a URL in a caption, a comment or a reply into a link (owner 2026-10-17: 「你IG貼文的留言 都沒有
成功變成連結耶 沒辦法直接點」), and a long URL only makes the text longer (owner, the same day: 「ig 貼文沒辦法顯示連結的話
你用很長的文字沒有比較好耶 改成原版的好了 請大家去個人檔案下載」「但是你的 tag 可以直接放一個我 app 的名稱」). So an Instagram
text carries no URL: it closes with the localized profile-link line, and a caption names the app in ONE brand
hashtag (download_links.py holds the rule and its fail-closed check; this module adds the app data it needs):

    Your to-do list, but make it cute                寫到一半 AI 額度又爆了？
    ...                                               ...
    📲 Download via the link in bio                   📲 請到個人檔案（bio）的連結下載

    #Mochi #ToDoList #Checklist                       #UsageNow #AI額度 ...

The brand hashtag is the main store name without spaces and symbols; a brand written in another script
(Lumi注音星球) takes the app's Latin store name (latin_name: the English clip name in clips.json, else the
utility cards' Latin name, else the catalog name in apps.json) -> #LumiBopomofo.

The profile link is the hub page HUB_URL, built by ig_bio_hub.py after every recorded Instagram post (the root
site alice51849.github.io mirrors it): the apps of the newest posts first, then every app by category, each one
tap from the App Store or Google Play.

No network, and no poster is imported at load time (utility_cards' name table only when a Latin name is looked
up): clip_posts.py, store_shot_cards.py, utility_cards.py, countdown_cards.py, comment_replies.py,
link_backfill.py and post_qa.py all use these helpers.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

import download_links as DL

HERE = Path(__file__).resolve().parent
CLIPS = HERE.parent / "growth" / "clips.json"
CATALOG = HERE.parents[1] / "apps.json"
HUB_URL = "https://open.cait518.cc/ig/"
CT_PREFIX = "ig_bio_"   # App Store campaign of a hub button: ig_bio_<app> (00_GrowthEngine agent/ct_codes.py)

BIO = DL.INSTAGRAM_CTA      # the localized "download via the link in bio" phrase, one table for every poster
EMOJI = DL.INSTAGRAM_CTA_MARK
APP_ID = re.compile(r"/id(\d+)")


def short_name(name):
    """The app's main store name, the part people find on the hub: before the first ':' / '：' / ' - '."""
    return DL.brand_name(name)


def bio_line(locale):
    """The line that closes every Instagram text: "📲 Download via the link in bio", in the text's locale."""
    return DL.instagram_cta_line(locale)


@lru_cache(maxsize=1)
def _latin_names():
    """{App Store id: Latin store name}: the English clip names (clips.json, the live store names), then the
    utility cards' own store names when they are Latin, then the catalog names (apps.json)."""
    names = {}
    try:
        clips = json.loads(CLIPS.read_text(encoding="utf-8")).get("clips", {})
    except (OSError, ValueError, AttributeError):
        clips = {}
    for clip in clips.values():
        m = APP_ID.search(str(clip.get("store_url", "")))
        if m and clip.get("locale") == "en" and clip.get("name"):
            names.setdefault(m.group(1), clip["name"])
    try:
        import utility_cards   # its table names some apps the way their store page does ("Lumi Letters Lite")
        for app in utility_cards.APPS.values():
            if app.get("id") and app.get("name") and DL.brand_hashtag(app["name"]):
                names.setdefault(str(app["id"]), app["name"])
    except Exception:  # noqa: BLE001 - one source less, never a crash: the catalog below still answers
        pass
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        catalog = []
    for app in catalog if isinstance(catalog, list) else []:
        m = APP_ID.search(str(app.get("appStoreUrl", "")))
        if m and app.get("name"):
            names.setdefault(m.group(1), app["name"])
    return names


def latin_name(ref):
    """The Latin-letter store name of the app behind `ref` (an App Store link or id); '' when unknown."""
    ref = str(ref or "")
    m = APP_ID.search(ref)
    app_id = m.group(1) if m else (ref if ref.isdigit() else "")
    return _latin_names().get(app_id, "")


def brand_tag(name, ref=None):
    """The app's brand hashtag (#BattAI): its store name, else its Latin store name (ref = App Store link or id)."""
    return DL.brand_hashtag(name, latin_name(ref))


def hashtags(make, name, ref=None, limit=5):
    """An Instagram caption's hashtags: the brand hashtag first, then the keyword tags make(n) gives - n = limit, or
    limit - 1 when the brand is not among them, so their own selection rules decide what stays - `limit` in all."""
    brand = brand_tag(name, ref)
    tags = list(make(limit))
    if brand and not DL.has_brand_hashtag(" ".join(tags), brand):
        tags = list(make(max(limit - 1, 0)))
    rest = [t for t in tags if not brand or t.casefold() != brand.casefold()]
    return ([brand] if brand else []) + rest[:max(limit - (1 if brand else 0), 0)]


def caption(text, name, locale, ref=None, *, max_len=2200, tag_limit=None, label="instagram"):
    """The last guard of an Instagram caption (download_links.ensure_instagram_caption): no URL, the profile-link
    line, the brand hashtag; raises MissingDownloadLink (nothing is sent) when it cannot be made so."""
    return DL.ensure_instagram_caption(text, name, locale, latin_name=latin_name(ref), max_len=max_len,
                                       tag_limit=tag_limit, label=label)


def caption_problems(text, locale, name, ref=None, label="instagram text", urls=True):
    """QA (post_qa.py): an Instagram caption has no URL, says to download via the link in bio (in its locale) and
    names the app in its brand hashtag."""
    return DL.instagram_problems(text, name, locale=locale, latin_name=latin_name(ref), urls=urls, label=label)


def reply_problems(text, locale, label="instagram reply"):
    """An Instagram reply or comment: no URL, and the profile-link line in its language (no hashtag asked)."""
    return DL.instagram_problems(text, locale=locale, brand=False, label=label)
