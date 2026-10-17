#!/usr/bin/env python3
"""Instagram's only tappable link is the profile (bio) link: where it points and how a post points to it.

Instagram never turns a URL in a caption or a comment into a link (owner 2026-10-17: 「你IG貼文的留言 都沒有成功
變成連結耶 沒辦法直接點」). Only the profile's links can be tapped (Story link stickers too, but the API cannot add
them). So an Instagram text keeps the full App Store URL (owner rule 2026-10-17, download_links.py; it is the
fail-closed proof the post carries the link) and also says exactly where to tap:

    📲 Link in bio → tap “Mochi”            📲 下載連結在個人檔案 → 點「Lumi注音星球」

The profile link is the hub page HUB_URL, built by ig_bio_hub.py after every recorded Instagram post (the root
site alice51849.github.io mirrors it): the apps of the newest posts first, then every app by category, each one
tap from the App Store or Google Play. The line names the app instead of "the first link", because the order of
the hub changes with every new post while the app's name stays on the page.

No network, no imports of the posters: clip_posts.py, utility_cards.py, countdown_cards.py, link_backfill.py,
comment_replies.py and post_qa.py all use this one table.
"""
import re

HUB_URL = "https://open.cait518.cc/ig/"
CT_PREFIX = "ig_bio_"   # App Store campaign of a hub button: ig_bio_<app> (00_GrowthEngine agent/ct_codes.py)

# The localized "link in bio" phrase (the same words as clip_posts.TEXT[...]["bio"]; a test keeps them equal).
BIO = {
    "en": "Link in bio", "zh-Hant": "下載連結在個人檔案", "ja": "リンクはプロフィールから", "ko": "링크는 프로필에",
    "de": "Link in der Bio", "fr": "Lien dans la bio", "es": "Enlace en la bio", "id": "Link di bio", "vi": "Link ở bio",
    "th": "ลิงก์อยู่ในโปรไฟล์", "pt-BR": "Link na bio", "zh-Hans": "下载链接在主页简介", "cs": "Odkaz najdete v profilu",
    "pl": "Link w bio", "nl": "Link in bio", "da": "Link i bio", "nb": "Lenke i bio", "el": "Σύνδεσμος στο προφίλ",
    "ar": "الرابط في الملف الشخصي",
}
# The step after the profile link, per caption locale; {app} is the app's short store name.
TAP = {
    "en": "tap “{app}”",
    "zh-Hant": "點「{app}」",
    "zh-Hans": "点“{app}”",
    "ja": "「{app}」をタップ",
    "ko": "‘{app}’ 누르면 다운로드",
    "de": "„{app}“ antippen",
    "fr": "touchez « {app} »",
    "es": "toca «{app}»",
    "id": "ketuk “{app}”",
    "vi": "chạm vào “{app}”",
    "th": "แตะ “{app}”",
    "pt-BR": "toque em “{app}”",
    "cs": "klepněte na „{app}“",
    "pl": "stuknij „{app}”",
    "nl": "tik op ‘{app}’",
    "da": "tryk på “{app}”",
    "nb": "trykk på «{app}»",
    "el": "πατήστε «{app}»",
    "ar": "اضغط على «{app}»",
}
ARROW = {"ar": "←"}   # right-to-left text: the arrow points the way the line is read
EMOJI = "📲"
# The main name ends at the first delimiter: "Mochi: Cute Checklist" -> "Mochi", "UsageNow：AI 用量與額度追蹤" -> "UsageNow".
SPLIT = re.compile(r"\s*[:：｜|]\s*|\s+[-–—]\s+")


def _pick(table, locale):
    locale = locale or "en"
    return table.get(locale) or table.get(locale.split("-")[0]) or table["en"]


def short_name(name):
    """The app's main store name, the part people find on the hub: before the first ':' / '：' / ' - '."""
    name = " ".join((name or "").split())
    head = SPLIT.split(name, maxsplit=1)[0].strip()
    return head if len(head) >= 2 else name


def tap_text(locale, name):
    """The localized "tap “<app>”" step (the part QA looks for)."""
    return _pick(TAP, locale).format(app=short_name(name))


def bio_line(locale, name, base=None):
    """The Instagram line that replaces the generic "Link in bio": the localized "link in bio" phrase (the
    poster's own, e.g. clip_posts.TEXT[...]["bio"], else BIO), then the arrow and the tap step naming the app."""
    if not short_name(name):
        raise ValueError("the Instagram bio line needs the app's name")
    base = base or _pick(BIO, locale)
    return f"{EMOJI} {base} {ARROW.get((locale or 'en').split('-')[0], '→')} {tap_text(locale, name)}"


def has_bio_line(text, locale, name):
    """True when the text tells people to tap this app on the profile link (in the text's locale)."""
    return bool(short_name(name)) and tap_text(locale, name) in (text or "")


def bio_problems(text, locale, name, label="instagram text"):
    """QA (post_qa.py): an Instagram text must point to the profile link and name the app to tap there."""
    if has_bio_line(text, locale, name):
        return []
    return [f"{label}: no profile-link step naming the app ({tap_text(locale, name)!r}); an Instagram URL cannot "
            f"be tapped, so the post must say where to tap (ig_bio.py, hub {HUB_URL})"]
