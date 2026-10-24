#!/usr/bin/env python3
"""Every promo text carries the app's direct download link (fail closed, zero token).

Owner rule (2026-10-17): every promo post, update and text must carry the app's direct download link -
the App Store link, plus the Google Play link when the app is live on Android. Posts that went out
without one (Instagram Reels captions had "Link in bio" and the store name only) are the reason this
module exists. The posters share these three helpers:

- has_download_link(text, app_store_url, play_url): is the link of that exact app in the text?
- link_problems(text, ...): QA-gate style list of what is missing (post_qa.py calls it before posting).
- ensure_download_link(text, ...): the last-line defence at the send call. A text without the link gets
  the template link lines appended (the body is trimmed to the platform limit, hashtags first); when the
  app has no known link, or no room is left, it raises MissingDownloadLink so nothing is sent silently.

Platform rules: Instagram cannot turn a URL in a caption, comment or reply into a link, so an Instagram text
carries NO URL at all (owner 2026-10-17, replacing the same day's "write the full URL into it"): it closes with
the localized "download via the link in bio" line and a caption names the app in one brand hashtag (#BattAI) -
instagram_problems() / ensure_instagram_caption() below. Threads keeps its link in the first reply (account
limit history), so its main text is not checked here - threads_reply_problems() checks the reply.

Campaign tokens (ct) leave at channel level: coarse_campaign() turns any posting line's token into one of
COARSE_CAMPAIGNS (threads, bluesky, telegram, instagram, youtube, web, social, outreach), because Apple hides a
campaign's downloads below its privacy threshold. ensure_download_link() applies it to the text it returns, and the
URL builders (social_post_common.campaign_app_store_url, clip_posts.with_campaign, the card store_url()s) mint it.

    python3 download_links.py check "text" --app-store https://apps.apple.com/app/id1   # exit 1 when missing
"""
import json
import os
import re
import sys
import unicodedata
import urllib.parse

APP_STORE_URL = re.compile(r"https?://(?:apps|itunes)\.apple\.com/[^\s\"'<>)]+", re.I)
APP_STORE_BARE = re.compile(r"https?://(?:apps|itunes)\.apple\.com/[^\s\"'<>)]*?/id(\d+)(?![A-Za-z0-9_])", re.I)
PLAY_LINK = re.compile(r"https?://play\.google\.com/store/apps/details\?(?:[^\s\"'<>)]*&)?id=([A-Za-z0-9_.]+)", re.I)
HASHTAG_LINE = re.compile(r"^\s*(?:#\S+\s*)+$")


class MissingDownloadLink(ValueError):
    """The text has no download link and none could be added: the post must not go out."""


def app_store_id(url):
    """The numeric App Store id of an apps.apple.com / itunes.apple.com link, or ''."""
    m = APP_STORE_BARE.search(url or "")
    return m.group(1) if m else ""


def play_package(url):
    """The package name of a Google Play details link, or ''."""
    m = PLAY_LINK.search(url or "")
    return m.group(1) if m else ""


def _plain(text):
    """The text with percent-encoded URLs read as plain ones (a platform may hand a link back wrapped)."""
    text = text or ""
    return urllib.parse.unquote(text) if "%2F" in text.upper() or "%3A" in text.upper() else text


def store_ids_in(text):
    """App ids the text links as a DOWNLOAD page. A write-review link (?action=write-review) is the same
    app page but not a download link, so it does not count."""
    ids = set()
    for m in APP_STORE_URL.finditer(_plain(text)):
        url = m.group(0)
        if "action=write-review" in url.lower():
            continue
        found = APP_STORE_BARE.search(url)
        if found:
            ids.add(found.group(1))
    return ids


def play_packages_in(text):
    return {m.group(1) for m in PLAY_LINK.finditer(_plain(text))}


def links_covered(text, wanted_text):
    """True when `text` holds every App Store page and Google Play package that `wanted_text` links to
    (compared by app id / package, so a changed campaign token or a rewritten URL does not matter)."""
    ids, packages = store_ids_in(wanted_text), play_packages_in(wanted_text)
    return bool(ids or packages) and ids <= store_ids_in(text) and packages <= play_packages_in(text)


def has_app_store_link(text, app_store_url):
    """True when the text links this app's App Store page (any storefront, any campaign token)."""
    wanted = app_store_id(app_store_url)
    return bool(wanted) and wanted in store_ids_in(text)


def has_play_link(text, play_url):
    wanted = play_package(play_url)
    return bool(wanted) and wanted in play_packages_in(text)


def has_download_link(text, app_store_url, play_url=None):
    """The App Store link of this app (and its Google Play link when the app has one) is in the text."""
    if not has_app_store_link(text, app_store_url):
        return False
    return not play_url or has_play_link(text, play_url)


def link_problems(text, app_store_url, play_url=None, label="text"):
    """What is missing, as QA-gate problem strings (empty list = the text carries the link)."""
    out = []
    if not app_store_id(app_store_url):
        out.append(f"{label}: no App Store link known for this app (cannot attach the download link)")
    elif not has_app_store_link(text, app_store_url):
        out.append(f"{label}: no direct App Store download link (id{app_store_id(app_store_url)}) in the text")
    if play_url and not has_play_link(text, play_url):
        out.append(f"{label}: app is on Google Play but the text has no Google Play link")
    return out


# ---------------------------------------------------------------- companion edition (a paid app's free Lite)
#
# A paid app whose free edition (same content, matching store copy) downloads far better gets that edition's
# direct links as one extra line UNDER its own links (2026-10-24: DailyMate 1 download in 30 days, DailyMate Lite 17).
# The paid app's own links stay the ones every check counts; the Lite line is only added when it still fits the
# platform limit, never in place of the app's own link. Its ct is the app's own ct plus "_lite", so Apple reports the
# two apart. App Store id -> companion; keep both cores in the same change (agent/ct_codes reads "<campaign>_lite").
COMPANION_APPS = {
    "6790418321": {"key": "dailymatelite", "app_store": "https://apps.apple.com/app/id6794725568",
                   "play": "https://play.google.com/store/apps/details?id=com.alice51849.DailyMateLite"},
}
COMPANION_LABEL = "Lite"
COMPANION_CT_SUFFIX = "_lite"
_CT_MAX = 40  # agent/ct_codes.TOKEN_RE: 1-40 characters


def companion_of(app_store_url):
    """The companion entry (COMPANION_APPS) of the app an App Store link points to, or None."""
    return COMPANION_APPS.get(app_store_id(app_store_url))


def companion_ids(app_id):
    """App Store ids of the companion edition of `app_id` (a set; empty for an app without one)."""
    comp = COMPANION_APPS.get(str(app_id or ""))
    return {app_store_id(comp["app_store"])} if comp else set()


def companion_packages(app_id):
    """Google Play packages of the companion edition of `app_id` (a set; empty for an app without one)."""
    comp = COMPANION_APPS.get(str(app_id or ""))
    return {play_package(comp["play"])} - {""} if comp else set()


def primary_ids(ids):
    """`ids` minus the companion editions of the other ids in it: the apps a text is about."""
    ids = set(ids)
    extra = set()
    for app_id in ids:
        extra |= companion_ids(app_id)
    return ids - extra


def companion_campaign(token):
    """The ct of a companion line: the app's own ct plus "_lite", cut to stay a valid token."""
    token = str(token or "")
    if not token:
        return ""
    return token[:_CT_MAX - len(COMPANION_CT_SUFFIX)] + COMPANION_CT_SUFFIX


def _companion_base(token):
    t = str(token or "").strip().lower()
    if t.endswith(COMPANION_CT_SUFFIX) and t[:-len(COMPANION_CT_SUFFIX)] in COARSE_CAMPAIGNS:
        return t[:-len(COMPANION_CT_SUFFIX)]
    return None


def _companion_play_url(comp, play_url):
    """The companion's Play link; when the app's own Play link carries an install referrer, the same one with
    utm_source + "_lite" and the companion's own key."""
    import urllib.parse
    found = re.search(r"[?&]referrer=([^&\s]+)", play_url or "")
    if not found:
        return comp["play"]
    src = (urllib.parse.parse_qs(urllib.parse.unquote(found.group(1))).get("utm_source") or [""])[0]
    if not src:
        return comp["play"]
    ref = f"utm_source={companion_campaign(src)}&utm_campaign={comp['key']}"
    return comp["play"] + "&referrer=" + urllib.parse.quote(ref, safe="")


def _with_companion(out, app_store_url, play_url, play_label, max_len, measure):
    """`out` plus the companion line(s) when the app has a companion, it is not linked yet and it fits max_len."""
    comp = companion_of(app_store_url)
    if not comp or app_store_id(comp["app_store"]) in store_ids_in(out):
        return out
    lite = comp["app_store"]
    ct = _CT_PARAM.search(app_store_url)
    if ct:
        lite += ("&" if "?" in lite else "?") + "ct=" + companion_campaign(ct.group(1))
    lines = [f"{COMPANION_LABEL}: {lite}"]
    if play_url and comp.get("play") and not has_play_link(out, comp["play"]):
        lines.append(f"{COMPANION_LABEL} {play_label}: {_companion_play_url(comp, play_url)}")
    for n in range(len(lines), 0, -1):  # both lines, else the App Store one alone, else none
        candidate = f"{out.rstrip()}\n" + "\n".join(lines[:n])
        if max_len is None or measure(candidate) <= max_len:
            return candidate
    return out


def _link_block(text, app_store_url, play_url, app_store_label, play_label):
    lines = []
    if not has_app_store_link(text, app_store_url):
        lines.append(f"{app_store_label}: {app_store_url}")
    if play_url and not has_play_link(text, play_url):
        lines.append(f"{play_label}: {play_url}")
    return "\n".join(lines)


def _cut(text, room):
    """`text` cut to `room` characters at a line or word boundary, ending in an ellipsis."""
    if len(text) <= room:
        return text
    cut = text[:max(room - 1, 0)]
    for sep in ("\n", " "):
        pos = cut.rfind(sep)
        if pos >= len(cut) // 2:
            cut = cut[:pos]
            break
    cut = re.sub(r"https?://\S*$", "", cut)  # never leave half a URL behind
    return cut.rstrip() + "…"


def _without_own_links(text, app_store_url, play_url):
    """`text` minus the lines that carry this app's own store links (the full link block is rebuilt after a trim)."""
    wanted_id, wanted_pkg = app_store_id(app_store_url), play_package(play_url)
    ids, pkgs = {wanted_id} | companion_ids(wanted_id), {wanted_pkg} | companion_packages(wanted_id)
    ids.discard("")
    pkgs.discard("")
    keep = []
    for line in (text or "").split("\n"):  # the companion line goes too: it is added back after the trim
        own = bool(ids & store_ids_in(line)) or bool(pkgs & play_packages_in(line))
        if not own:
            keep.append(line)
    return "\n".join(keep)


def ensure_download_link(text, app_store_url, play_url=None, *, max_len=None, app_store_label="App Store",
                         play_label="Google Play", measure=len, label="post"):
    """`text` with the app's direct download link(s), appended when missing.

    Raises MissingDownloadLink when the App Store link is not a valid apps.apple.com app link, or when
    the links do not fit `max_len` even after the body is trimmed (hashtag lines go first). `measure`
    counts length the platform's way (graphemes, URL weights); default is len(). Every App Store link of the
    result carries the app's own ct level (app_campaign). An app with a companion edition (COMPANION_APPS) gets
    its "Lite" line under its own links when that still fits max_len.
    """
    out = _ensure_own_links(text, app_store_url, play_url, max_len=max_len, app_store_label=app_store_label,
                            play_label=play_label, measure=measure, label=label)
    return _with_companion(out, coarse_campaign_url(app_store_url), play_url, play_label, max_len, measure)


def _ensure_own_links(text, app_store_url, play_url, *, max_len, app_store_label, play_label, measure, label):
    text = coarsen_campaign_links(text)  # first, so the platform limit is measured on what is sent
    app_store_url = coarse_campaign_url(app_store_url)
    if not app_store_id(app_store_url):
        raise MissingDownloadLink(f"{label}: no App Store link known for this app: {app_store_url!r}")
    block = _link_block(text, app_store_url, play_url, app_store_label, play_label)
    if not block:
        return text
    sep = "\n\n"
    out = f"{text.rstrip()}{sep}{block}" if text.strip() else block
    if max_len is None or measure(out) <= max_len:
        return out
    # Over the limit: rebuild with the FULL link block (App Store + Play) and a trimmed body, so a trim can
    # never cut away a link the text already had; the result is verified before it is returned.
    block = "\n".join(filter(None, [f"{app_store_label}: {app_store_url}",
                                    f"{play_label}: {play_url}" if play_url else ""]))
    lines = _without_own_links(text, app_store_url, play_url).rstrip().split("\n")
    candidates = []

    def with_block():
        body = "\n".join(lines).rstrip()
        candidates.append(f"{body}{sep}{block}" if body else block)

    with_block()  # the whole body first
    while lines and (not lines[-1].strip() or HASHTAG_LINE.match(lines[-1])):  # then without the hashtag tail
        lines.pop()
        with_block()
    body = "\n".join(lines).rstrip()
    for out in candidates:
        if measure(out) <= max_len:
            return _verified(out, app_store_url, play_url, label)
    room = max_len - measure(sep + block) - 1
    while room > 0:
        trimmed = _cut(body, room)
        out = f"{trimmed}{sep}{block}"
        if measure(out) <= max_len:
            return _verified(out, app_store_url, play_url, label)
        room -= max(1, measure(out) - max_len)
    if measure(block) <= max_len:  # only the link itself fits: still a post with a download link
        return _verified(block, app_store_url, play_url, label)
    raise MissingDownloadLink(f"{label}: the download link ({measure(block)} chars) does not fit {max_len}")


def _verified(out, app_store_url, play_url, label):
    problems = link_problems(out, app_store_url, play_url, label)
    if problems:
        raise MissingDownloadLink("; ".join(problems))
    return out


def threads_reply_problems(reply_text, app_store_url, play_url=None):
    """Threads posts keep links out of the main text; the first reply must carry them."""
    return link_problems(reply_text, app_store_url, play_url, label="Threads link reply")


# ---------------------------------------------------------------- channel-level App Store campaign (ct)
#
# Apple's App Analytics shows a campaign's downloads per app only past its privacy threshold. Tokens cut per post,
# page, locale, card type, clip variant or source family (h7_<app>_tg, ut_<app>_tg, soc_tg_<app>, cd_tg, bf_tg ...
# on one Telegram channel) split the same few downloads into rows Apple never reveals: the 2026-10-17 audit found
# 0 of 4,021 downloads in 30 days attributable. So every outbound App Store link leaves with ONE channel-level
# token per app (the app is already Apple's row); which post, page, locale or variant it was stays in our own
# posting logs (00_GrowthEngine agent/channel_proxy.py reads them). 00_GrowthEngine agent/ct_codes.py reads these
# tokens and every older one; its test keeps the tables below in step with its channel table.
COARSE_CAMPAIGNS = ("threads", "bluesky", "telegram", "instagram", "youtube", "web", "social", "outreach")
# Platform codes the posting lines append as the last segment (h7_<app>[_b]_<pf>, ut_<app>_<pf>, cd_<pf>).
_CLIP_CAMPAIGN = {
    "th": "threads", "threads": "threads", "tg": "telegram", "telegram": "telegram", "ig": "instagram",
    "igc": "instagram", "bs": "bluesky", "bsky": "bluesky", "yt": "youtube", "fb": "social", "pin": "social",
    "tb": "social", "nv": "social", "pk": "social", "dm": "social", "ma": "social", "tt": "social",
    "ln": "outreach",
    # 2026-10-22 platform 50 (social_extra.py): Misskey, Pixelfed, Telegraph, Write.as, Hatena Blog,
    # WordPress.com, Blogger, WhiteWind.
    "mk": "social", "pxf": "social", "tph": "social", "wrt": "social", "htn": "social", "wp": "social",
    "blg": "social", "ww": "social",
}
# Hand-posted hero kits h_<app>_<market>_<channel>.
_HERO_CAMPAIGN = dict(_CLIP_CAMPAIGN, **{
    "x": "social", "rd": "social", "dc": "social", "pt": "social", "yc": "social", "nt": "social", "cm": "social",
    "pi": "social", "li": "social", "kol": "outreach", "ln": "outreach", "at": "outreach", "kk": "outreach",
    "ph": "outreach", "wa": "outreach",
    "l8": "social", "xhs": "social", "qr": "social", "md": "social", "dsc": "social", "sc": "social",
    "lv": "social",
})
# BM series bm_<app>_<market>_<channel>; a BM token without a known channel is its SEO intent page (web).
_BM_CAMPAIGN = dict(_HERO_CAMPAIGN, seo="web", dir="outreach", zenn="social", gn="social", naver="social",
                    note="social", qa="social", edu="outreach", gh="social")
# Demand radar replies radar_<code>: the platform the reply was posted on.
_RADAR_CAMPAIGN = {"th": "threads", "bs": "bluesky", "yt": "youtube", "rd": "social", "se": "social",
                   "qr": "social", "pn": "social", "nv": "social", "fb": "social"}
_CAMPAIGN_FAMILIES = (("h7_", _CLIP_CAMPAIGN, None), ("cd_", _CLIP_CAMPAIGN, None), ("ut_", _CLIP_CAMPAIGN, None),
                      ("h_", _HERO_CAMPAIGN, None), ("bm_", _BM_CAMPAIGN, "web"))
_CAMPAIGN_EXACT = {
    "soc_th_guide": "threads", "rp_th": "threads", "bf_th": "threads",
    "soc_tg_guide": "telegram", "soc_tg_digest": "telegram", "bf_tg": "telegram",
    "rp_ig": "instagram", "bf_ig": "instagram", "yt_shorts": "youtube", "standard_site": "web",
    "mastodon": "social", "nostr": "social", "devto": "social",
}
_CAMPAIGN_PREFIXES = (
    ("soc_tg_", "telegram"), ("social_", "telegram"), ("tg_", "telegram"),
    ("ig_bio_", "instagram"), ("geo_", "web"), ("iag_", "web"), ("img_", "web"), ("home_", "web"), ("sup_", "web"),
    ("nostr_", "social"), ("devto_", "social"), ("qiita_", "social"), ("ml_", "social"),
    ("appdir_", "outreach"), ("outreach", "outreach"),
)
# Sent as they are: experiment cells whose own contract reads the token back (gx_reach_*; th_mochi_<lang>_<nn>, the
# 2026-10-20..11-01 Threads Mochi trial posts, threads_post.py), the one long-form YouTube token, the Cute To-Do
# audience-segment links ln_mochi_<seg>_<cc>_<ch>_<MMDD> (segment_ct.py; 00_GrowthEngine ops/company/audience/mochi.md), and
# any token not listed above (00_GrowthEngine's inventory test names those).
_CAMPAIGN_KEEP = ("gx_reach_", "yt_longform", "th_mochi_", "ln_mochi_")
_CT_PARAM = re.compile(r"(?<=[?&;])ct=([A-Za-z0-9_-]+)")
# Per app, the channel rows are merged further until they can pass Apple's threshold (owner 2026-10-18: every app
# earns on its own, so each app gets its own split; merging only ever happens inside one app). Tier from
# 00_GrowthEngine reports/per_app/build_growth_board.ct_tier (est. external first-time downloads a month):
# A keeps every channel row; B sends the text socials (Threads, Bluesky, Telegram, Instagram) as one social row;
# C sends YouTube there too. web and outreach always stay their own rows. An app not listed is C. Change a tier
# on purpose only (a new token restarts Apple's count), in both cores in the same change.
APP_CT_TIER = {"6785004775": "A", "6802423998": "B", "6782251621": "B"}  # App Store id -> tier
_TEXT_SOCIAL = ("threads", "bluesky", "telegram", "instagram")
_TIER_MERGE = {"A": {}, "B": dict.fromkeys(_TEXT_SOCIAL, "social"),
               "C": dict.fromkeys(_TEXT_SOCIAL + ("youtube",), "social")}


def coarse_campaign(token):
    """The channel-level campaign (one of COARSE_CAMPAIGNS) a ct token is sent as; a token kept on purpose
    (_CAMPAIGN_KEEP) or not known here comes back unchanged."""
    raw = str(token or "")
    t = raw.strip().lower()
    if not t or t in COARSE_CAMPAIGNS:
        return t or raw
    if _companion_base(t):  # a companion line's <campaign>_lite (COMPANION_APPS) is sent as it is
        return raw
    if t.startswith(_CAMPAIGN_KEEP):
        return raw
    if t in _CAMPAIGN_EXACT:
        return _CAMPAIGN_EXACT[t]
    if t.startswith("radar_"):
        return _RADAR_CAMPAIGN.get(t[len("radar_"):], raw)
    for prefix, platforms, own in _CAMPAIGN_FAMILIES:
        if t.startswith(prefix):
            return platforms.get(t.rsplit("_", 1)[-1]) or own or raw
    for prefix, campaign in _CAMPAIGN_PREFIXES:
        if t.startswith(prefix):
            return campaign
    if "_flyer" in t:
        return "outreach"
    return raw


def app_ct_tier(app_id):
    """The app's tracking-code tier (APP_CT_TIER; an app not listed is C)."""
    return APP_CT_TIER.get(str(app_id or ""), "C")


def app_campaign(token, app_id):
    """The ct a token is sent as on this app's links: coarse_campaign, then the app's own tier merge."""
    t = coarse_campaign(token)
    base = _companion_base(t)
    if base:  # <campaign>_lite: the campaign part takes this app's tier merge, the suffix stays
        return _TIER_MERGE[app_ct_tier(app_id)].get(base, base) + COMPANION_CT_SUFFIX
    return _TIER_MERGE[app_ct_tier(app_id)].get(t, t)


def coarse_campaign_url(url):
    """An App Store link with its ct token sent at this app's level (app_campaign); anything else unchanged."""
    if not url or not APP_STORE_URL.match(url):
        return url
    app_id = app_store_id(url)
    return _CT_PARAM.sub(lambda m: "ct=" + app_campaign(m.group(1), app_id), url)


def coarsen_campaign_links(text):
    """`text` with every App Store link's ct sent at channel level (idempotent; nothing else is touched)."""
    return APP_STORE_URL.sub(lambda m: coarse_campaign_url(m.group(0)), text or "")


def fine_campaigns(text):
    """The ct tokens of App Store links in `text` that app_campaign would still merge ([] = all at app level)."""
    return [m.group(1) for u in APP_STORE_URL.finditer(text or "") for m in _CT_PARAM.finditer(u.group(0))
            if app_campaign(m.group(1), app_store_id(u.group(0))) != m.group(1)]


# ---------------------------------------------------------------- Instagram: no URL, the profile (bio) link instead
#
# Owner 2026-10-17 (replacing the same day's "write the full URL into the Instagram text"): 「ig 貼文沒辦法顯示連結的話
# 你用很長的文字沒有比較好耶 改成原版的好了 請大家去個人檔案下載」「但是你的 tag 可以直接放一個我 app 的名稱」. Instagram never
# turns a URL in a caption, comment or reply into a link, so an Instagram text carries NO URL: it closes with the
# localized "download via the link in bio" line, and a caption names the app in ONE brand hashtag - the main store
# name without spaces and symbols (#BattAI, #LumiWeather; a brand written in another script takes its Latin store
# name: Lumi注音星球 -> #LumiBopomofo). The profile link is the download link. Every other platform keeps its links.

INSTAGRAM_CHANNELS = ("instagram", "instagram_feed")
INSTAGRAM_CTA = {
    "en": "Download via the link in bio",
    "zh-Hant": "請到個人檔案（bio）的連結下載",
    "zh-Hans": "请到个人主页（bio）的链接下载",
    "ja": "ダウンロードはプロフィール（bio）のリンクから",
    "ko": "다운로드는 프로필(bio) 링크에서",
    "de": "Download über den Link in der Bio",
    "fr": "Téléchargez-la via le lien dans la bio",
    "es": "Descárgala desde el enlace de la bio",
    "it": "Scaricala dal link nella bio",
    "pt-BR": "Baixe pelo link na bio",
    "id": "Unduh lewat link di bio",
    "vi": "Tải về qua link ở bio",
    "th": "ดาวน์โหลดได้ที่ลิงก์ในโปรไฟล์ (bio)",
    "cs": "Stáhněte si ji přes odkaz v profilu (bio)",
    "pl": "Pobierz przez link w bio",
    "nl": "Download via de link in bio",
    "da": "Download via linket i bio",
    "nb": "Last ned via lenken i bio",
    "el": "Λήψη από τον σύνδεσμο στο προφίλ (bio)",
    "ar": "حمّله من الرابط في الملف الشخصي (bio)",
    "ru": "Скачать можно по ссылке в профиле (bio)",
    "sk": "Stiahnite si ju cez odkaz v profile (bio)",
}
_CTA_ALIAS = {"zh": "zh-Hant", "zh-TW": "zh-Hant", "zh-HK": "zh-Hant", "zh-CN": "zh-Hans", "pt": "pt-BR", "no": "nb"}
INSTAGRAM_CTA_MARK = "📲"
# A web address in any form a reader could copy: a scheme, "www.", a domain with a path, a store host, a bare domain.
IG_URL = re.compile(r"https?://\S+|\bwww\.\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,24}/\S*|"
                    r"\b(?:apps\.apple|itunes\.apple|play\.google)\.com\b\S*|"
                    r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|cc|co|me|dev|page|link|ly|gl|to|site|xyz|info)\b",
                    re.I)
_BRAND_SPLIT = re.compile(r"\s*[:：｜|]\s*|\s+[-–—]\s+")
_IG_TAG = re.compile(r"(?<!\w)#\w+")


def is_instagram(channel):
    """True for the Instagram surfaces (Reels / image posts, and the feed carousels' own ledger channel)."""
    return (channel or "") in INSTAGRAM_CHANNELS


def instagram_cta(locale=None):
    """The localized "download via the link in bio" phrase (English for a locale without its own)."""
    locale = _CTA_ALIAS.get(locale or "en", locale or "en")
    return INSTAGRAM_CTA.get(locale) or INSTAGRAM_CTA.get(locale.split("-")[0]) or INSTAGRAM_CTA["en"]


def instagram_cta_line(locale=None):
    """The line that closes an Instagram text: "📲 Download via the link in bio", in the text's language."""
    return f"{INSTAGRAM_CTA_MARK} {instagram_cta(locale)}"


def has_instagram_cta(text, locale=None):
    """True when the text says to download via the profile (bio) link (in `locale` when one is given)."""
    text = text or ""
    if locale:
        return instagram_cta(locale) in text
    return any(phrase in text for phrase in INSTAGRAM_CTA.values())


def brand_name(name):
    """The app's main store name: the part before the first ':' / '：' / '｜' / ' - ' ("Mochi: Cute" -> "Mochi")."""
    name = " ".join((name or "").split())
    head = _BRAND_SPLIT.split(name, maxsplit=1)[0].strip()
    return head if len(head) >= 2 else name


def _latin_only(text):
    return all(ch.isascii() or unicodedata.name(ch, "").startswith("LATIN") for ch in text if ch.isalpha())


def brand_hashtag(name, latin_name=None):
    """'#BattAI' for 'BattAI: Battery Health & Life': the main store name without spaces and symbols. A brand that
    is not written in Latin letters ('Lumi注音星球') takes `latin_name`, the app's Latin store name ('Lumi Bopomofo'
    -> '#LumiBopomofo'); '' when neither gives one."""
    for candidate in (name, latin_name):
        head = brand_name(candidate)
        if not head or not _latin_only(head):
            continue
        tag = "".join(ch for ch in head if ch.isalnum())
        if tag and not tag.isdigit():
            return f"#{tag}"
    return ""


def has_brand_hashtag(text, tag):
    """True when `tag` is one of the text's hashtags (the whole tag, any letter case)."""
    return bool(tag) and tag.casefold() in {t.casefold() for t in _IG_TAG.findall(text or "")}


def instagram_url_problems(text, label="instagram text"):
    """An Instagram text must not carry a URL: Instagram cannot tap it, the profile (bio) link is the download link."""
    found = IG_URL.search(text or "")
    if not found:
        return []
    return [f"{label}: an Instagram text must not carry a URL ({found.group(0)[:60]!r}); Instagram cannot tap it, "
            "the download link is the profile (bio) link"]


def instagram_problems(text, name=None, *, locale=None, latin_name=None, brand=True, urls=True,
                       label="instagram text"):
    """QA problems of an Instagram text ([] = fine): a URL in it (urls=True), no "download via the link in bio" line
    (in `locale` when given), and for a caption (brand=True) no brand hashtag of the app."""
    out = instagram_url_problems(text, label) if urls else []
    if not has_instagram_cta(text, locale):
        out.append(f"{label}: no profile-link line ({instagram_cta_line(locale)!r}); an Instagram text says to "
                   "download via the link in the profile (bio)")
    if brand:
        tag = brand_hashtag(name, latin_name)
        if not tag:
            out.append(f"{label}: no brand hashtag can be made from the app name {name!r} (no Latin store name known)")
        elif not has_brand_hashtag(text, tag):
            out.append(f"{label}: no brand hashtag {tag} (the app's name as one hashtag)")
    return out


def ensure_instagram_caption(text, name, locale=None, *, latin_name=None, max_len=None, tag_limit=None,
                             measure=len, label="instagram"):
    """`text` as an Instagram caption: the profile-link line and the brand hashtag (first in the closing hashtag
    line) are added when missing; with tag_limit the other hashtags make room for the brand one. Over max_len the
    other hashtags go first, then the body is trimmed - never the profile-link line or the brand hashtag.

    Raises MissingDownloadLink (nothing is sent) when the text carries a URL, when no brand hashtag can be made
    from the app name, or when the caption still does not fit."""
    text = text or ""
    tag = brand_hashtag(name, latin_name)
    problems = instagram_url_problems(text, label)
    if not tag:
        problems.append(f"{label}: no brand hashtag can be made from the app name {name!r} (no Latin store name known)")
    if problems:
        raise MissingDownloadLink("; ".join(problems))
    lines = text.rstrip().split("\n")
    tags = []
    while lines and (not lines[-1].strip() or HASHTAG_LINE.match(lines[-1])):
        tags = lines.pop().split() + tags
    body = "\n".join(lines).rstrip()
    cta = instagram_cta_line(locale)
    if not has_instagram_cta(body, locale):
        body = f"{body}\n{cta}" if body else cta
    if not has_brand_hashtag(body, tag):
        tags = [tag] + [t for t in tags if t.casefold() != tag.casefold()]
    if tag_limit:
        tags = tags[:tag_limit]

    def build(head, shown):
        return f"{head}\n\n{' '.join(shown)}" if shown else head

    out = build(body, tags)
    if max_len is None or measure(out) <= max_len:
        return _instagram_verified(out, name, locale, latin_name, label)
    kept = tags[:1] if tags and tags[0].casefold() == tag.casefold() else []
    others = tags[len(kept):]
    while others:  # the other hashtags go first, from the end
        others.pop()
        out = build(body, kept + others)
        if measure(out) <= max_len:
            return _instagram_verified(out, name, locale, latin_name, label)
    head = "\n".join(line for line in body.split("\n") if instagram_cta(locale) not in line).rstrip()
    tail = build(cta, kept)
    room = max_len - measure("\n" + tail)
    while head and room > 0:  # then the body is trimmed above the profile-link line
        out = f"{_cut(head, room)}\n{tail}"
        if measure(out) <= max_len:
            return _instagram_verified(out, name, locale, latin_name, label)
        room -= max(1, measure(out) - max_len)
    if measure(tail) <= max_len:
        return _instagram_verified(tail, name, locale, latin_name, label)
    raise MissingDownloadLink(f"{label}: the profile-link line and the brand hashtag do not fit {max_len}")


def _instagram_verified(out, name, locale, latin_name, label):
    problems = instagram_problems(out, name, locale=locale, latin_name=latin_name, label=label)
    if problems:
        raise MissingDownloadLink("; ".join(problems))
    return out


def refuse(label, problems, log_path=None):
    """Print the QA refusal as workflow errors and append one JSON line to the link-guard log
    (LINK_GUARD_LOG, or the given path) so the pipeline's alert/action log shows what was held back."""
    for p in problems:
        print(f"::error::{label}: download link guard refused: {p}")
    path = log_path or os.environ.get("LINK_GUARD_LOG")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"label": label, "problems": list(problems)}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return False


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Check that a text carries the app's download link")
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("text")
    ap.add_argument("--app-store", required=True)
    ap.add_argument("--play")
    args = ap.parse_args(argv)
    problems = link_problems(args.text, args.app_store, args.play)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
