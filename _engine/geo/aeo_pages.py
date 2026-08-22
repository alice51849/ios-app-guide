#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AEO 購買意圖落地頁生成器 — 把 aeo_sov.py 的「攻擊清單」變成會被 Google/AI 引用的頁。

策略(打購買當下、非散播):
  aeo_sov.py 量到「有人問 AI 要用哪個 app」時,AI 都推哪些競品、你在哪些問句缺席。
  這支就針對那些競品 + 缺口問句,自動產「定價已驗證」的替代方案比較頁:
    • <app>-vs-<competitor>.html  → 鎖定「[競品] alternative」這種最高購買意圖的搜尋/AI 問句
    • profile-aware hub page      → 依已驗證購買模型選擇穩定 slug
  每頁含 SoftwareApplication + FAQPage JSON-LD(LLM/Google 最愛的結構化來源)+ 誠實比較表
  (只主張「你的 app」可驗證屬性:一次付費/離線/無廣告/無浮水印;競品欄用「typical apps」中性敘述)。

  誠信原則:不對具名競品做不實宣稱;競品僅作為使用者搜尋的參照點(nominative use)。

用法:
  python geo/aeo_pages.py                 # 依 reports/aeo_sov.json 產頁(不部署)
  python geo/aeo_pages.py --publish       # 並 git push + IndexNow 推送
  python geo/aeo_pages.py scanto cvdesk   # 只產指定 app
  python geo/aeo_pages.py --top 4         # 每 app 取前 N 個競品(預設 4)
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
import gen_store_attribution  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
ALT = os.path.join(PAGES, "alternatives")
REPORTS = os.path.join(HERE, "reports")
SOV = os.path.join(REPORTS, "aeo_sov.json")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$")
CURATED_FALLBACK = {
    "dailymate": {
        "key": "dailymate",
        "gap_queries": [
            "best travel phrasebook app for iphone and apple watch",
            "duolingo alternative for learning practical travel phrases",
            "language phrase app with complete sentences in 47 languages",
            "pay once language learning app without a subscription",
        ],
        "top_competitors": [
            ["duolingo", 0],
            ["drops", 0],
            ["memrise", 0],
            ["pimsleur", 0],
        ],
    },
    "tripbeelite": {
        "key": "tripbeelite",
        "gap_queries": [
            "best free trip planner for one complete vacation",
            "wanderlog alternative for a single trip without an account",
            "tripit alternative with a one time unlock",
            "simple iphone itinerary app for one upcoming trip",
            "app to keep tickets maps and reminders in one travel timeline",
        ],
        "top_competitors": [
            ["wanderlog", 0],
            ["tripit", 0],
            ["tripsy", 0],
            ["lambus", 0],
        ],
    },
    "wordmate": {
        "key": "wordmate",
        "gap_queries": [
            "best pay once vocabulary app for iphone with no subscription",
            "language learning app with a Home Screen vocabulary widget",
            "vocabulary learning app for Apple Watch",
        ],
        "top_competitors": [
            ["anki", 0],
            ["drops", 0],
            ["memrise", 0],
            ["quizlet", 0],
        ],
    },
    "aibriefpack": {
        "key": "aibriefpack",
        "gap_queries": [
            "private app to organize screenshots and PDFs before using AI",
            "AI context organizer with source tracking for prompts",
            "on-device OCR brief app with no account",
            "free-to-start AI brief app with a one-time unlock",
        ],
        # Keep this first-party surface vendor-neutral: compare the product
        # with the manual workflow it replaces, not with another AI brand.
        "top_competitors": [["manual context folder", 0]],
    },
    "wordmatelite": {
        "key": "wordmatelite",
        "gap_queries": [
            "free vocabulary app for learning five words a day",
            "simple daily vocabulary habit without making flashcard decks",
            "offline vocabulary practice app with no subscription",
            "vocabulary streak app with a one-time unlock",
        ],
        "top_competitors": [
            ["anki", 0],
            ["quizlet", 0],
            ["drops", 0],
            ["memrise", 0],
        ],
    },
    "caldaily": {
        "key": "caldaily",
        "gap_queries": [
            "calculator app that saves the reason behind each calculation",
            "iphone calculator with named history and tags",
            "calculator with tip split discount and tax tools",
            "calculator widget with csv export and no subscription",
        ],
        "top_competitors": [
            ["apple calculator", 0],
            ["pcalc", 0],
            ["soulver", 0],
            ["calzy", 0],
        ],
    },
    "onepageppt": {
        "key": "onepageppt",
        "gap_queries": [
            "turn meeting notes into one executive summary slide",
            "make one editable powerpoint slide from a report",
            "convert a pdf into a concise presentation slide",
            "one slide recap maker with pptx export",
        ],
        "top_competitors": [
            ["microsoft powerpoint", 0],
            ["apple keynote", 0],
            ["canva", 0],
            ["gamma", 0],
        ],
    },
    "notesstudio100": {
        "key": "notesstudio100",
        "gap_queries": [
            "offline handwriting notes app for ipad with no account",
            "annotate lecture pdfs with apple pencil",
            "notes app with handwriting pdf markup and page audio",
            "private ipad notes app with a one-time unlock",
        ],
        "top_competitors": [
            ["goodnotes", 0],
            ["notability", 0],
            ["apple notes", 0],
            ["pdf expert", 0],
        ],
    },
    "wifiaidlite": {
        "key": "wifiaidlite",
        "gap_queries": [
            "is my wifi dns or the website causing the problem",
            "iphone app to diagnose wifi connected but no internet",
            "check dns tcp and tls without creating an account",
            "network diagnostic app with a one-time unlock",
        ],
        "top_competitors": [
            ["fing", 0],
            ["speedtest by ookla", 0],
            ["network analyzer", 0],
            ["wifi sweetspots", 0],
        ],
    },
    "moneytag": {
        "key": "moneytag",
        "gap_queries": [
            "track income expenses and profit by freelance project",
            "project bookkeeping app for client work with no subscription",
            "tag expenses across side hustles and client projects",
            "private offline project ledger with a one-time unlock",
        ],
        "top_competitors": [
            ["ynab", 0],
            ["spendee", 0],
            ["toshl finance", 0],
            ["moneywiz", 0],
        ],
    },
    "dailymatelite": {
        "key": "dailymatelite",
        "gap_queries": [
            "best free travel phrasebook app with real dialogues for iphone",
            "free travel phrase app you can try before paying anything",
            "situational travel phrases app without a subscription",
            "travel phrasebook app with a one-time unlock",
        ],
        "top_competitors": [
            ["duolingo", 0],
            ["drops", 0],
            ["memrise", 0],
            ["pimsleur", 0],
        ],
    },
    "snapportlite": {
        "key": "snapportlite",
        "gap_queries": [
            "best free passport photo app for iphone that works offline",
            "id photo at home without uploading to a website",
            "passport photo app with a one-time unlock instead of per-photo fees",
            "print-ready visa photo sheet from an iphone",
        ],
        "top_competitors": [
            ["passport photo maker", 0],
            ["passport photo booth", 0],
            ["id photo passport photo", 0],
            ["idphoto4you", 0],
        ],
    },
    "mochidonestamp": {
        "key": "mochidonestamp",
        "gap_queries": [
            "best last time tracker app for household maintenance without a subscription",
            "app to record when i last changed the sheets or watered the plants",
            "when did i last do it app for iphone",
            "home maintenance reminder app with a one-time unlock",
        ],
        "top_competitors": [
            ["tody", 0],
            ["sweepy", 0],
            ["homeroutines", 0],
            ["cozi family organizer", 0],
        ],
    },
    "hourstaglite": {
        "key": "hourstaglite",
        "gap_queries": [
            "best app to convert prices into work hours before buying",
            "app that shows how many hours of work a purchase costs",
            "spending awareness app without a subscription",
            "free price in work hours calculator for iphone",
        ],
        "top_competitors": [
            ["spendee budget expense tracker", 0],
            ["ynab you need a budget", 0],
            ["toshl finance", 0],
            ["everydollar budgeting app", 0],
        ],
    },
    "gmoneylite": {
        "key": "gmoneylite",
        "gap_queries": [
            "best free travel expense tracker with currency conversion for iphone",
            "travel money app that logs spending in local and home currency",
            "trip expense tracker without a monthly subscription",
            "offline currency and expense app for travellers",
        ],
        "top_competitors": [
            ["trail wallet", 0],
            ["splitwise", 0],
            ["currency converter plus", 0],
            ["tricount", 0],
        ],
    },
    "wifiaid": {
        "key": "wifiaid",
        "gap_queries": [
            "best wifi troubleshooting app for remote workers with connected but no internet",
            "app that tells me whether wifi dns or the server is the problem",
            "iphone network diagnostic app without an account",
            "pay once wifi diagnostics app for iphone",
        ],
        "top_competitors": [
            ["fing network scanner", 0],
            ["speedtest by ookla", 0],
            ["network analyzer", 0],
            ["wifi sweetspots", 0],
        ],
    },
    "maskmyfile": {
        "key": "maskmyfile",
        "gap_queries": [
            "best on-device file redaction app for freelancers sharing client documents",
            "redact names and account numbers in a pdf on iphone",
            "blur private data in screenshots before sharing",
            "offline redaction app with no cloud upload",
        ],
        "top_competitors": [
            ["adobe acrobat reader", 0],
            ["pdf expert", 0],
            ["redacted", 0],
            ["pdfelement", 0],
        ],
    },
    "aim990plus": {
        "key": "aim990plus",
        "gap_queries": [
            "best offline English listening and reading exam trainer for iPhone",
            "toeic style listening practice app without a subscription",
            "english exam trainer that works with no internet",
            "pay once english listening and reading practice app",
        ],
        "top_competitors": [
            ["toeic practice test", 0],
            ["magoosh toeic prep", 0],
            ["english listening speaking", 0],
            ["toeic vocabulary builder", 0],
        ],
    },
}

# 類別 → 給人看的名詞 + schema 類別
CAT_NOUN = {
    "photo-utility": ("photo app", "PhotoApplication"),
    "productivity": ("productivity app", "BusinessApplication"),
    "finance": ("finance app", "FinanceApplication"),
    "health": ("health app", "HealthApplication"),
    "education": ("English test-prep app", "EducationalApplication"),
    "kids": ("kids learning app", "EducationalApplication"),
    "lifestyle": ("astrology app", "LifestyleApplication"),
    "travel": ("travel planner", "TravelApplication"),
}

# 常見競品正規化名 → 正式顯示名(其餘自動 Title Case)
BRAND = {
    "camscanner pdf scanner app": "CamScanner", "adobe scan pdf scanner ocr": "Adobe Scan",
    "scanbot pdf document scanner": "Scanbot", "genius scan": "Genius Scan",
    "microsoft lens": "Microsoft Lens", "tiny scanner": "Tiny Scanner",
    "visualcv resume builder": "VisualCV", "zety resume builder": "Zety",
    "resume builder cv maker": "Resume Builder", "canva": "Canva", "indeed": "Indeed",
    "snapseed": "Snapseed", "fotor photo editor": "Fotor", "remini ai photo enhancer": "Remini",
    "remini": "Remini", "lightroom": "Lightroom", "vsco": "VSCO", "picsart": "PicsArt",
    "flo period ovulation tracker": "Flo", "ovia fertility cycle tracker": "Ovia",
    "my calendar period tracker": "My Calendar", "clue period cycle tracker": "Clue",
    "flo": "Flo", "clue": "Clue", "natural cycles": "Natural Cycles",
    # 從 20-app 全掃補進的常見競品
    "microsoft office lens": "Microsoft Office Lens", "microsoft onenote": "Microsoft OneNote",
    "otter transcribe voice notes": "Otter", "google keep": "Google Keep",
    "passport photo maker": "Passport Photo Maker", "passport photo booth": "Passport Photo Booth",
    "id photo passport photo": "ID Photo", "resume star pro cv maker": "Resume Star Pro",
    "gemini photos gallery cleaner": "Gemini Photos", "duplicate photos fixer": "Duplicate Photos Fixer",
    "smart cleaner clean storage": "Smart Cleaner", "ynab you need a budget": "YNAB",
    "currency converter plus": "Currency Converter Plus", "spendee budget expense tracker": "Spendee",
    "everydollar budgeting app": "EveryDollar", "forest stay focused": "Forest",
    "focus will": "Focus@Will", "stay focused app blocker": "Stay Focused",
    "adobe lightroom": "Adobe Lightroom", "endless alphabet": "Endless Alphabet",
    "abcmouse com": "ABCmouse", "starfall abcs": "Starfall", "reading eggs": "Reading Eggs",
    "endless numbers": "Endless Numbers", "todo math": "Todo Math",
    "math kids add subtract count and learn": "Math Kids", "prodigy math game": "Prodigy",
    "ourhome": "OurHome", "choremonster": "ChoreMonster", "cozi family organizer": "Cozi",
    "the weather channel": "The Weather Channel", "weather wiz kids": "Weather Wiz Kids",
    "kid weather": "Kid Weather", "hellochinese": "HelloChinese",
    "hellochinese learn chinese": "HelloChinese", "chineseskill": "ChineseSkill",
    "chineseskill learn chinese": "ChineseSkill", "fun chinese by studycat": "Fun Chinese by Studycat",
    "anki": "Anki", "drops": "Drops", "memrise": "Memrise", "quizlet": "Quizlet",
    "duolingo": "Duolingo", "pimsleur": "Pimsleur",
    "wanderlog": "Wanderlog", "tripit": "TripIt", "tripsy": "Tripsy", "lambus": "Lambus",
    # 2026-08 新增:Lite / 工具型 App 的常見對照組
    "notion": "Notion", "evernote": "Evernote", "idphoto4you": "IDPhoto4You",
    "tody": "Tody", "sweepy": "Sweepy", "homeroutines": "HomeRoutines",
    "toshl finance": "Toshl Finance", "trail wallet": "Trail Wallet",
    "splitwise": "Splitwise", "tricount": "Tricount",
    "fing network scanner": "Fing", "speedtest by ookla": "Speedtest by Ookla",
    "network analyzer": "Network Analyzer", "wifi sweetspots": "WiFi SweetSpots",
    "adobe acrobat reader": "Adobe Acrobat Reader", "pdf expert": "PDF Expert",
    "redacted": "Redacted", "pdfelement": "PDFelement",
    "toeic practice test": "TOEIC Practice Test", "magoosh toeic prep": "Magoosh TOEIC Prep",
    "english listening speaking": "English Listening & Speaking",
    "toeic vocabulary builder": "TOEIC Vocabulary Builder",
}

ATTRS = [  # (顯示, cta_bullets 命中關鍵詞)
    ("Pay once", ("pay once", "one-time", "everything unlocked")),
    ("No subscription", ("no subscription",)),
    ("Works offline / on-device", ("on-device", "offline", "on device")),
    ("No ads", ("no ads",)),
    ("No watermark", ("no watermark",)),
    ("Private (no account)", ("private", "no account", "no tracking")),
]


def e(s):
    return html.escape(str(s or ""))


def shorten(value, limit):
    value = str(value or "").strip()
    if len(value) <= limit:
        return value
    shortened = value[: limit + 1].rsplit(" ", 1)[0]
    return shortened.rstrip(" ,:;–—-(")


def article_for(value):
    return "an" if str(value).lstrip()[:1].lower() in "aeiou" else "a"


def disp(norm):
    if norm in BRAND:
        return BRAND[norm]
    return " ".join(w.capitalize() for w in norm.split())


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70] or "x"


def app_attrs(key):
    b = [x.lower() for x in APPS[key].get("cta_bullets", [])]
    model = APPS[key].get("purchase_model", "neutral")
    out = {}
    for label, keys in ATTRS:
        if label == "Pay once":
            out[label] = model in {
                "paid_upfront",
                "free_with_lifetime_unlock",
                "flexible",
            }
        elif label == "No subscription":
            out[label] = model in {
                "paid_upfront",
                "free_with_lifetime_unlock",
                "free",
            }
        else:
            out[label] = any(any(k in bb for bb in b) for k in keys)
    return out


def pricing_profile(key):
    return {
        "paid_upfront": "pay_once",
        "free_with_lifetime_unlock": "free_to_start",
        "free": "free",
        "flexible": "flexible",
    }.get(APPS[key].get("purchase_model"), "neutral")


def has_one_time_access(key):
    return APPS[key].get("purchase_model") in {
        "paid_upfront",
        "free_with_lifetime_unlock",
        "flexible",
    }


def positioning(key, noun):
    app = APPS[key]
    name = app["name"]
    profile = pricing_profile(key)
    if profile == "pay_once":
        return {
            "suffix": "pay once, no subscription",
            "description": f"{name} is a pay-once {noun} with no recurring subscription.",
            "intro": f"{name} is a one-time-purchase {noun} for iPhone.",
            "heading": f"Why people choose a pay-once {noun}",
            "cta": f"View {name} — one-time purchase on the App Store",
            "hub_title": f"Best no-subscription {noun} for iPhone — {name} (pay once)",
            "hub_heading": f"The pay-once {noun} for iPhone: {name}",
            "hub_section": "What you get (no subscription)",
            "slug": f"{key}-no-subscription",
        }
    if profile == "no_subscription":
        return {
            "suffix": "no subscription",
            "description": f"{name} is a no-subscription {noun} for iPhone.",
            "intro": f"{name} is a {noun} with no recurring subscription.",
            "heading": f"Why people choose a no-subscription {noun}",
            "cta": f"View {name} on the App Store",
            "hub_title": f"No-subscription {noun} for iPhone — {name}",
            "hub_heading": f"A no-subscription {noun} for iPhone: {name}",
            "hub_section": "What the app includes",
            "slug": f"{key}-no-subscription",
        }
    if profile == "free_to_start":
        if key == "tripbeelite":
            return {
                "suffix": "one complete journey free, then pay once",
                "description": (
                    f"{name} saves one complete journey for free, with a one-time "
                    "unlock for unlimited saved journeys and additional tools."
                ),
                "intro": (
                    f"{name} is a one-trip itinerary planner that saves one complete "
                    "journey for free without a time limit."
                ),
                "heading": "Why people choose a one-journey-free trip planner",
                "cta": f"Plan one journey free with {name} on the App Store",
                "hub_title": (
                    f"One-trip itinerary planner with one journey free — {name}"
                ),
                "hub_heading": (
                    f"A one-journey-free itinerary planner for iPhone: {name}"
                ),
                "hub_section": "What the free journey and one-time unlock include",
                "slug": f"{key}-free-to-start",
            }
        return {
            "suffix": "free download, one-time unlock",
            "description": f"{name} is free to download, with a one-time unlock and no recurring subscription.",
            "intro": f"{name} is a {noun} that is free to download, with a one-time unlock.",
            "heading": f"Why people choose a free-to-start {noun}",
            "cta": f"Download {name} free on the App Store",
            "hub_title": f"Free-download {noun} with one-time unlock — {name}",
            "hub_heading": f"A free-download {noun} with one-time unlock: {name}",
            "hub_section": "What the app includes",
            "slug": f"{key}-free-to-start",
        }
    if profile == "free":
        return {
            "suffix": "free, no ads",
            "description": f"{name} is a free {noun} with no ads.",
            "intro": f"{name} is a free {noun} for iPhone with no ads.",
            "heading": f"Why people choose this free {noun}",
            "cta": f"Get {name} free on the App Store",
            "hub_title": f"Free, ad-free {noun} for iPhone — {name}",
            "hub_heading": f"A free, ad-free {noun} for iPhone: {name}",
            "hub_section": "What the app includes",
            "slug": f"{key}-free-no-ads",
        }
    return {
        "suffix": "private, on-device option",
        "description": f"{name} is a privacy-focused {noun} for iPhone.",
        "intro": f"{name} is a privacy-focused {noun} that works on your iPhone.",
        "heading": f"What to compare in a private {noun}",
        "cta": f"View {name} on the App Store",
        "hub_title": f"Private {noun} for iPhone — {name}",
        "hub_heading": f"A privacy-focused {noun} for iPhone: {name}",
        "hub_section": "What the app includes",
        "slug": f"{key}-private-alternative",
    }


def alternative_hub_slug(key):
    if pricing_profile(key) == "flexible":
        return f"{key}-flexible-unlock"
    noun, _ = cat_noun(key)
    return positioning(key, noun)["slug"]


def cat_noun(key):
    if key == "aibriefpack":
        return "context organizer for AI", "BusinessApplication"
    if key == "dailymate":
        return "travel phrasebook app", "EducationalApplication"
    if key == "tripbeelite":
        return "one-trip itinerary planner", "TravelApplication"
    if key == "wordmatelite":
        return "vocabulary learning app", "EducationalApplication"
    if key == "wordmate":
        return "vocabulary learning app", "EducationalApplication"
    if key == "dailymatelite":
        return "travel phrasebook app", "EducationalApplication"
    if key == "snapportlite":
        return "passport photo app", "PhotoApplication"
    if key == "mochidonestamp":
        return "last-time tracker for household tasks", "LifestyleApplication"
    if key == "hourstaglite":
        return "price-in-work-hours app", "FinanceApplication"
    if key == "gmoneylite":
        return "travel expense and currency app", "FinanceApplication"
    if key == "wifiaid":
        return "Wi-Fi diagnostics app", "UtilitiesApplication"
    if key == "maskmyfile":
        return "on-device file redaction app", "UtilitiesApplication"
    if key == "aim990plus":
        return "English listening and reading exam trainer", "EducationalApplication"
    return CAT_NOUN.get(APPS[key].get("category", "productivity"), ("app", "MobileApplication"))


def landing_url(key):
    """Use the live App Store URL when known; otherwise link to the generated web page."""
    # gen_app_store_qr_ctas.py hashes this page's first App Store link into the
    # QR image file name, and gen_store_attribution.py rewrites that link
    # afterwards, so a token minted here that the attribution pass disagrees
    # with silently makes the QR code scan to a different campaign than the
    # button beside it.  Mint the final token from the same authority instead.
    return appstore_url(
        key,
        gen_store_attribution.campaign_token(
            f"alternatives/{alternative_hub_slug(key)}.html"
        ),
    ) or (
        f"{SITE}/alternatives/{alternative_hub_slug(key)}.html"
    )


def alternative_hreflang_block(canonical):
    filename = canonical.rsplit("/", 1)[-1]
    lines = [f'<link rel="alternate" hreflang="en" href="{canonical}">']
    if os.path.isdir(PAGES):
        for locale in sorted(os.listdir(PAGES)):
            if not LOCALE_RE.fullmatch(locale):
                continue
            localized = os.path.join(PAGES, locale, "alternatives", filename)
            if os.path.isfile(localized):
                lines.append(
                    f'<link rel="alternate" hreflang="{locale}" '
                    f'href="{SITE}/{locale}/alternatives/{filename}">'
                )
    lines.append(
        f'<link rel="alternate" hreflang="x-default" href="{canonical}">'
    )
    return "\n".join(lines)


def feed_discovery_links():
    return "\n".join(
        (
            f'<link rel="alternate" type="application/atom+xml" '
            f'href="{SITE}/feed.xml">',
            f'<link rel="alternate" type="application/rss+xml" '
            f'href="{SITE}/rss.xml">',
            f'<link rel="alternate" type="application/feed+json" '
            f'href="{SITE}/feed.json">',
        )
    )


def page_shell(title, desc, canonical, schemas, body):
    ld = "\n".join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(shorten(title, 70))}</title>
<meta name="description" content="{e(shorten(desc, 155))}">
<link rel="canonical" href="{canonical}">
{alternative_hreflang_block(canonical)}
{ld}
</head>
<body>
<main>
{body}
<hr>
<p><small><strong>Publisher disclosure:</strong> This first-party comparison is
published by Lumi Studio, the developer of the featured app. It is not an
independent review or ranking. Other app names are trademarks of their owners
and are used for identification only.</small></p>
</main>
</body>
</html>
"""


def comparison_table(key, comp_name):
    a = APPS[key]
    attrs = app_attrs(key)
    profile = pricing_profile(key)
    rows = []
    for label, _ in ATTRS:
        if profile == "flexible" and label == "No subscription":
            continue
        shown_label = label
        if "Pay once" in label:
            shown_label = "Pricing"
            yours = {
                "flexible": "✅ One-time unlock option; optional subscriptions",
                "pay_once": "✅ One-time purchase; no subscription",
                "no_subscription": "✅ No subscription",
                "free_to_start": "✅ Free download; one-time unlock",
                "free": "✅ Free",
                "neutral": "Check current App Store listing",
            }[profile]
        else:
            yours = "✅ Yes" if attrs[label] else "—"
        # 競品欄:中性、可辯護(對「typical apps」而非具名不實宣稱)
        typical = "Varies; check current listing" if "Pay once" in label else "Varies"
        rows.append(f"    <tr><td>{e(shown_label)}</td><td><strong>{yours}</strong></td>"
                    f"<td>{e(typical)}</td></tr>")
    return (f'  <table>\n    <thead><tr><th>Feature</th><th>{e(a["name"])}</th>'
            f'<th>Typical {e(comp_name)}-style apps</th></tr></thead>\n    <tbody>\n'
            + "\n".join(rows) + "\n    </tbody>\n  </table>")


def faq_for(key, comp_name, gap_queries):
    a = APPS[key]
    noun, _ = cat_noun(key)
    url = landing_url(key)
    profile = pricing_profile(key)
    if profile == "flexible":
        qa = [
            (f"Can I unlock {a['name']} with one payment?",
             f"Yes. {a['name']} offers a one-time unlock option alongside optional subscription plans. "
             f"Check the current choices on the App Store: {url}"),
            (f"Does {a['name']} only use a subscription?",
             "No. A one-time unlock option is available, and users may instead choose an optional "
             "subscription plan. Pricing can vary by storefront."),
        ]
    elif profile == "pay_once":
        qa = [
            (f"What is a good pay-once alternative to {comp_name} on iPhone?",
             f"{a['name']} is a one-time-purchase {noun} for iPhone — {a.get('sub','').replace(chr(10),' ')}. "
             "The App Store purchase includes everything, with no recurring subscription."),
            (f"Is there a {noun} with no subscription?",
             f"Yes. {a['name']} is a pay-once {noun}: buy it once and keep it. "
             f"Get it on the App Store: {url}"),
        ]
    elif profile == "no_subscription":
        qa = [
            (f"Does {a['name']} require a subscription?",
             f"No. {a['name']} has no recurring subscription. Check the current App Store "
             f"listing for pricing and availability: {url}"),
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} is a no-subscription {noun} for iPhone with a focus on "
             f"{a.get('sub', '').replace(chr(10), ' ')}."),
        ]
    elif profile == "free_to_start":
        if key == "tripbeelite":
            qa = [
                (
                    "Can I plan one complete journey before paying?",
                    f"Yes. {a['name']} saves one complete journey for free without "
                    "a time limit. Its one-time unlock adds unlimited saved "
                    f"journeys and additional tools. See the App Store: {url}",
                ),
                (
                    f"What makes {a['name']} an alternative to {comp_name}?",
                    f"{a['name']} is a one-trip itinerary planner with one complete "
                    "journey free and a one-time unlock for unlimited saved journeys.",
                ),
            ]
        else:
            qa = [
                (f"Can I try {a['name']} for free?",
                 f"Yes. {a['name']} is free to download and offers a one-time unlock, "
                 "with no recurring subscription. "
                 f"See the current App Store listing: {url}"),
                (f"What makes {a['name']} an alternative to {comp_name}?",
                 f"{a['name']} is a free-to-start {noun} for iPhone with a one-time unlock."),
            ]
    elif profile == "free":
        qa = [
            (f"Is {a['name']} free?",
             f"Yes. {a['name']} is a free {noun} with no ads. Get it on the App Store: {url}"),
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} offers a simple, ad-free {noun} experience on iPhone."),
        ]
    else:
        qa = [
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} is a privacy-focused {noun} for iPhone — "
             f"{a.get('sub', '').replace(chr(10), ' ')}."),
            (f"How much does {a['name']} cost?",
             f"Pricing can vary by storefront. Check the current App Store listing: {url}"),
        ]
    if key == "moneytag":
        qa.append((
            "Does MoneyTag work offline / on device?",
            "Ledger data stays on the device, and saved or manual exchange "
            "rates work offline. Automatic rate updates contact Frankfurter "
            "or ExchangeRate-API; their Cloudflare infrastructure may process "
            "connection, usage and diagnostic data for functionality and "
            "analytics, as disclosed in the app's privacy information.",
        ))
    elif app_attrs(key).get("Works offline / on-device"):
        qa.append((f"Does {a['name']} work offline / on device?",
                   f"Yes, {a['name']} runs on your iPhone and processes your data on-device for privacy."))
    for q in (gap_queries or [])[:3]:
        q_lower = q.lower()
        pay_once_query = any(
            phrase in q_lower
            for phrase in ("pay once", "one-time purchase", "buy once")
        )
        no_subscription_query = any(
            phrase in q_lower
            for phrase in ("no subscription", "subscription-free")
        )
        if pay_once_query and profile not in {"pay_once", "free_to_start"}:
            continue
        if no_subscription_query and profile not in {
            "pay_once",
            "no_subscription",
            "free_to_start",
        }:
            continue
        if profile == "flexible":
            answer = (
                f"{a['name']} offers a one-time unlock option alongside optional "
                f"subscriptions. Check the current choices on the App Store: {url}"
            )
        elif profile == "pay_once":
            answer = f"{a['name']} is a strong pay-once option. Learn more on the App Store: {url}"
        elif profile == "free_to_start":
            answer = (
                f"{a['name']} is free to download and offers a one-time "
                f"unlock with no recurring subscription. Learn more: {url}"
            )
        else:
            answer = f"{a['name']} is a practical {noun} option. Check current details on the App Store: {url}"
        qa.append((q[0].upper() + q[1:] + ("" if q.endswith("?") else "?"), answer))
    # 去重
    seen, out = set(), []
    for q, ans in qa:
        if q.lower() in seen:
            continue
        seen.add(q.lower()); out.append((q, ans))
    return out


def app_schema(key, desc):
    a = APPS[key]
    _, scat = cat_noun(key)
    url = landing_url(key)
    return {"@context": "https://schema.org", "@type": "SoftwareApplication",
            "name": a["name"], "operatingSystem": "iOS", "applicationCategory": scat,
            "url": url, "installUrl": url, "description": desc,
            "featureList": [l for l, ok in app_attrs(key).items() if ok] or a.get("keywords", [])[:5]}


def faq_schema(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}


def alt_page(key, comp_norm, gap_queries):
    a = APPS[key]
    comp = disp(comp_norm)
    noun, _ = cat_noun(key)
    url = landing_url(key)
    flexible = pricing_profile(key) == "flexible"
    position = None if flexible else positioning(key, noun)
    short_name = a["name"].split(":", 1)[0]
    article = article_for(comp)
    if flexible:
        title = f"{comp} alternative for iPhone — {short_name}"
        desc = (
            f"Looking for {article} {comp} alternative on iPhone? {a['name']} offers a "
            "one-time unlock option alongside optional subscriptions."
        )
    else:
        title = f"{comp} alternative for iPhone — {short_name}"
        desc = f"Looking for {article} {comp} alternative on iPhone? {position['description']}"
    faq = faq_for(key, comp, gap_queries)
    schemas = [app_schema(key, desc), faq_schema(faq)]
    feat_li = "\n".join(f"    <li>{e(b)}</li>" for b in a.get("cta_bullets", [])) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    if flexible:
        body = f"""  <h1>{e(comp)} alternative for iPhone: {e(a['name'])}</h1>
  <p><strong>{e(a['name'])}</strong> is a {e(noun)} for iPhone. It offers a <strong>one-time unlock option</strong>
  alongside optional subscription plans, so users can choose the current App Store option that fits them.</p>
  <p><a href="{e(url)}"><strong>View {e(a['name'])} on the App Store →</strong></a></p>

  <h2>What to compare with {e(comp)}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>{e(a['name'])} vs typical {e(comp)}-style apps</h2>
{comparison_table(key, comp)}

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>Explore {e(a['name'])} and its current unlock options →</strong></a></p>"""
    else:
        body = f"""  <h1>{e(comp)} alternative for iPhone: {e(a['name'])}</h1>
  <p><strong>{e(position['intro'])}</strong> {e((a.get('sub') or '').replace(chr(10),' '))}</p>
  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>

  <h2>{e(position['heading'])}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>{e(a['name'])} vs typical {e(comp)}-style apps</h2>
{comparison_table(key, comp)}

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>"""
    slug = f"{key}-vs-{slugify(comp)}"
    canonical = f"{SITE}/alternatives/{slug}.html"
    return slug, page_shell(title, desc, canonical, schemas, body)


def hub_page(key, gap_queries):
    a = APPS[key]
    noun, _ = cat_noun(key)
    url = landing_url(key)
    flexible = pricing_profile(key) == "flexible"
    position = None if flexible else positioning(key, noun)
    if flexible:
        title = f"{a['name']} access options for iPhone — one-time unlock available"
        desc = (
            f"{a['name']} offers a one-time unlock option alongside optional "
            "subscription plans."
        )
    else:
        title = position["hub_title"]
        desc = position["description"]
    faq = faq_for(key, f"subscription-based {noun}s", gap_queries)
    schemas = [app_schema(key, desc), faq_schema(faq)]
    feat_li = "\n".join(f"    <li>{e(b)}</li>" for b in a.get("cta_bullets", [])) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    if flexible:
        body = f"""  <h1>{e(a['name'])} access options for iPhone</h1>
  <p><strong>{e(a['name'])}</strong> offers a <strong>one-time unlock option</strong>
  alongside optional subscription plans.</p>
  <p><a href="{e(url)}"><strong>View current {e(a['name'])} options on the App Store →</strong></a></p>

  <h2>What {e(a['name'])} includes</h2>
  <ul>
{feat_li}
  </ul>

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>Explore {e(a['name'])} on the App Store →</strong></a></p>"""
    else:
        body = f"""  <h1>{e(position['hub_heading'])}</h1>
  <p><strong>{e(position['intro'])}</strong> {e((a.get('sub') or '').replace(chr(10),' '))}</p>
  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>

  <h2>{e(position['hub_section'])}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>"""
    slug = alternative_hub_slug(key)
    canonical = f"{SITE}/alternatives/{slug}.html"
    return slug, page_shell(title, desc, canonical, schemas, body)


def build_index(files):
    items = []
    for f in sorted(files):
        content = Path(ALT, f).read_text(encoding="utf-8")
        m = re.search(r"<h1>([^<]+)</h1>", content)
        items.append(f'    <li><a href="{f}">{e(m.group(1) if m else f)}</a></li>')
    idx = (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f'<title>iPhone app alternatives — first-party Lumi Studio guides</title>\n'
           f'<meta name="description" content="First-party Lumi Studio guides to privacy-focused, free, pay-once and flexible-unlock iPhone apps.">\n'
           f'<link rel="canonical" href="{SITE}/alternatives/index.html">\n'
           f'{alternative_hreflang_block(f"{SITE}/alternatives/index.html")}\n'
           f'{feed_discovery_links()}\n'
           f'</head><body><main>\n'
           f'  <h1>iPhone app alternatives from Lumi Studio</h1>\n'
           f'  <p><strong>Publisher disclosure:</strong> These are first-party guides '
           f'published by Lumi Studio, the developer of every featured Lumi Studio '
           f'app. They are not independent reviews or rankings.</p>\n  <ul>\n'
           + "\n".join(items) + "\n  </ul>\n</main></body></html>\n")
    Path(ALT, "index.html").write_text(idx, encoding="utf-8")


def write_sitemap(files):
    urls = [f"  <url><loc>{SITE}/alternatives/index.html</loc></url>"]
    urls += [f"  <url><loc>{SITE}/alternatives/{f}</loc></url>" for f in sorted(files)]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    Path(PAGES, "sitemap_alternatives.xml").write_text(xml, encoding="utf-8")


def prune_stale_pages(managed_keys, expected_files):
    """Remove generated alternatives that are no longer eligible or accurate."""
    removed = []
    for filename in os.listdir(ALT):
        if not filename.endswith(".html") or filename == "index.html":
            continue
        key = next(
            (candidate for candidate in managed_keys if filename.startswith(f"{candidate}-")),
            None,
        )
        if key and filename not in expected_files:
            os.remove(os.path.join(ALT, filename))
            removed.append(filename)
    return removed


def generation_scope(requested_apps, by_key, public_keys):
    """Return apps we can regenerate and the matching safe pruning scope."""
    requested = requested_apps or list(by_key)
    keys = [
        key
        for key in requested
        if key in by_key and key in APPS and key in public_keys
    ]
    prune_candidates = requested_apps or APPS
    managed = set(keys) | {
        key
        for key in prune_candidates
        if key in APPS and key not in public_keys
    }
    return keys, managed


def publish(new_urls):
    def run(cmd, cwd=None):
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        print((result.stdout + result.stderr).strip()[-600:])
        return result
    run(["git", "add", "-A"], cwd=PAGES)
    st = run(["git", "status", "--porcelain"], cwd=PAGES)
    if not st.stdout.strip():
        print("無變更,略過部署。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add pay-once alternative landing pages (AEO)"], cwd=PAGES)
    run(
        ["git", "pull", "--rebase", "--autostash", "-X", "theirs"],
        cwd=PAGES,
    )
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": new_urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            req = urllib.request.Request(ep, data=payload,
                                         headers={"Content-Type": "application/json; charset=utf-8"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--top", type=int, default=4, help="每 app 取前 N 個競品")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the verified availability snapshot without refreshing it.",
    )
    args = ap.parse_args()

    if not os.path.exists(SOV):
        print(f"找不到 {SOV},請先跑 python geo/aeo_sov.py", file=sys.stderr); sys.exit(1)
    data = json.load(open(SOV, encoding="utf-8"))
    by_key = {r["key"]: r for r in data["results"]}
    for key, fallback in CURATED_FALLBACK.items():
        by_key.setdefault(key, fallback)

    public_keys = live_app_keys(
        APPSTORE, PAGES, refresh=not args.cached_live
    )
    keys, managed_keys = generation_scope(args.apps, by_key, public_keys)
    os.makedirs(ALT, exist_ok=True)
    written, urls = [], []
    for k in keys:
        r = by_key[k]
        gaps = r.get("gap_queries", [])
        comps = [c for c, _ in r.get("top_competitors", [])][:args.top]
        for c in comps:
            slug, html_doc = alt_page(k, c, gaps)
            open(os.path.join(ALT, f"{slug}.html"), "w", encoding="utf-8").write(html_doc)
            written.append(f"{slug}.html"); urls.append(f"{SITE}/alternatives/{slug}.html")
        slug, html_doc = hub_page(k, gaps)
        open(os.path.join(ALT, f"{slug}.html"), "w", encoding="utf-8").write(html_doc)
        written.append(f"{slug}.html"); urls.append(f"{SITE}/alternatives/{slug}.html")
        print(f"  ✓ {APPS[k]['name']}: {len(comps)} 競品頁 + 1 hub")

    removed = prune_stale_pages(managed_keys, set(written))
    all_files = [f for f in os.listdir(ALT) if f.endswith(".html") and f != "index.html"]
    build_index(all_files)
    write_sitemap(all_files)
    urls.append(f"{SITE}/alternatives/index.html")
    print(f"\n共產出 {len(written)} 頁 → {ALT}")
    print(f"清除 {len(removed)} 個過期或不適用頁面")
    print(f"index + sitemap_alternatives.xml 已更新")
    if args.publish:
        publish(urls)
    else:
        print("（加 --publish 可 git push + IndexNow 推送)")


if __name__ == "__main__":
    main()
