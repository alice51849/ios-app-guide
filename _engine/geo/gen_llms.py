#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 機器可讀層生成器 — llms.txt + llms-full.txt + robots + sitemap index。

讓 LLM 爬蟲(GPTBot/ClaudeBot/PerplexityBot/Google-Extended…)最容易「讀懂並引用」你:
  • llms.txt:AI 爬蟲索引 — 已公開 app 一句話價值 + App Store 連結。
  • llms-full.txt:從真實頁面與 registry 重建的完整 crawler map,不再手動過期。
  • robots.txt:明確歡迎各 AI bot,並列出全部 sitemap(含 alternatives/answers)。
  • sitemap_index.xml:把三張 sitemap 串成索引,讓爬蟲一次抓全。

不碰 app code。沿用 registry + aeo_sov.json。

    python geo/gen_llms.py            # 產檔(不部署)
    python geo/gen_llms.py --publish  # 並 git push + IndexNow
"""
import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
import app_install_decision_routes  # noqa: E402
import app_video_lessons  # noqa: E402
import build_pages_i18n  # noqa: E402
from app_store_storefronts import (  # noqa: E402
    campaign_app_store_url,
    load_storefront_availability,
    resolve_provider_token,
    verified_app_store_url,
)
from appstore_live import live_app_keys  # noqa: E402
from aeo_pages import disp, pricing_profile  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    OFFICIAL_LOCALE_SET,
    require_official_locale_coverage,
)
import portfolio_offer_catalog  # noqa: E402
import publisher_intent_catalog  # noqa: E402
from rsscloud_config import (  # noqa: E402
    RSSCLOUD_NOTIFY_URL,
    RSSCLOUD_WEBSUB_HUB,
)
from static_api_catalog import API_DESCRIPTORS  # noqa: E402
from websub_config import WEBSUB_HUBS  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
ALT = os.path.join(PAGES, "alternatives")
GUIDES = os.path.join(PAGES, "guides")
DATA_DIR = os.path.join(PAGES, "data")
API_DIR = os.path.join(PAGES, "api")
TOOLS = os.path.join(PAGES, "tools")
STORIES = os.path.join(PAGES, "stories")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SOV = os.path.join(HERE, "reports", "aeo_sov.json")
FAMILY_TRAVEL_OER = "family-travel-observation-passport"
FAMILY_TRAVEL_RO_CRATE = "family-travel-missions-ro-crate-metadata.json"
ZHUYIN_ANKI_DECK = "zhuyin-bopomofo-anki-deck"
ZHUYIN_SKOS_VOCABULARY = "zhuyin-bopomofo-vocabulary"
ZHUYIN_CROISSANT_DATASET = "zhuyin-bopomofo-ml-dataset"
ZHUYIN_DATA_PACKAGE = "zhuyin-bopomofo"
ZHUYIN_CSVW_PACKAGE = "zhuyin-bopomofo-csvw"
ZHUYIN_BAGIT_PACKAGE = "zhuyin-bopomofo-bagit"
ZHUYIN_OCFL_OBJECT = "zhuyin-bopomofo-ocfl"
ZHUYIN_IIIF_RESOURCE = "zhuyin-bopomofo-iiif-presentation-3"
ZHUYIN_RO_CRATE = "zhuyin-bopomofo-ro-crate"
ZHUYIN_RESOURCE_SYNC = "zhuyin-bopomofo-resourcesync"
ZHUYIN_LMS_BANK = "zhuyin-bopomofo-lms-question-bank"
ZHUYIN_EPUB = "zhuyin-bopomofo-epub-reference"
ZHUYIN_LIBRARY_CATALOG = "zhuyin-bopomofo-library-catalog-records"
ZHUYIN_OER_METADATA = "zhuyin-bopomofo-oer-repository-metadata"
ZHUYIN_DCAT_CATALOG = "zhuyin-bopomofo-dcat3-open-data-catalog"
ZHUYIN_METS_PREMIS = "zhuyin-bopomofo-mets2-premis3"
ZHUYIN_ORE = "zhuyin-bopomofo-oai-ore"
ZHUYIN_LDES = "zhuyin-bopomofo-ldes"
RESOURCE_SYNC_SOURCE = "https://alice51849.github.io/.well-known/resourcesync"
WORDMATE_LANGUAGE_DATASET = "wordmate-language-support"
WORDMATE_LANGUAGE_TOOL = "wordmate-44-language-support-checker"
PORTFOLIO_FINDER_DATASET = "verified-ios-app-finder-catalog"
PORTFOLIO_FINDER_TOOL = "private-pay-once-iphone-app-finder"
PORTFOLIO_COST_TOOL = "subscription-cost-calculator"
PUBLISHER_INTENT_VISUALS = "lumi-studio-publisher-intent-visuals"
PUBLISHER_INTENT_VISUALS_SITEMAP = "sitemap_intent_visuals.xml"
# Truthful titles for tool slugs whose filename would otherwise read as a
# capability the tool does not have (e.g. "ats resume keyword checker").
RESOURCE_TITLES = {
    ("tools", "ats-resume-keyword-checker"): (
        "Private resume evidence coverage planner"
    ),
    ("tools", "private-toeic-study-allocation-planner"): (
        "Private TOEIC study allocation planner"
    ),
    ("tools", "private-bopomofo-symbol-contrast-cards"): (
        "Private Bopomofo symbol contrast cards"
    ),
    ("tools", "private-bopomofo-matching-pair-cards"): (
        "Private Bopomofo matching-pair cards"
    ),
}
DATA_DISTRIBUTIONS = (
    ("JSON", ".json"),
    ("JSONL", ".jsonl"),
    ("CSV", ".csv"),
    ("JSON Schema", ".schema.json"),
    ("Croissant 1.1", ".croissant.jsonld"),
)

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User",
           "Claude-SearchBot", "anthropic-ai", "Claude-Web", "PerplexityBot",
           "Perplexity-User", "BraveSearchBot", "Google-Extended",
           "Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "CCBot",
           "Amazonbot", "Bytespider", "Meta-ExternalAgent", "DuckDuckBot",
           "cohere-ai", "YandexBot", "PetalBot"]

EXTERNAL_REPOS = [
    ("awesome-zhuyin-bopomofo-apps", "Zhuyin/Bopomofo learning apps for Taiwanese parents (Chinese)"),
    ("awesome-ios-language-learning", "Pay-once iOS language-learning apps"),
    ("awesome-toeic-pay-once-apps", "TOEIC study apps with one-time-purchase options (Japanese)"),
    ("awesome-ios-kids-learning", "Pay-once iOS kids-learning apps"),
    ("awesome-ios-photo-utilities", "Pay-once iOS photo utility apps"),
    ("awesome-ios-productivity", "Pay-once iOS productivity apps"),
    ("awesome-ios-money-budgeting", "Pay-once iOS money & budgeting apps"),
    ("awesome-ios-health-wellness", "Pay-once iOS health & wellness apps"),
    ("awesome-ios-for-students", "Pay-once iOS apps for students"),
    ("awesome-ios-everyday-utilities", "Pay-once iOS everyday utility apps"),
    ("awesome-ios-privacy-first", "Privacy-first iOS apps"),
    ("awesome-ios-pay-once", "Pay-once iOS apps"),
    ("awesome-pay-once-todo-apps", "Pay-once to-do & checklist apps"),
    ("open-reference-datasets", "Machine-readable CC BY 4.0 reference datasets"),
]


def load_competitors():
    out = {}
    if os.path.exists(SOV):
        data = json.load(open(SOV, encoding="utf-8"))
        for r in data.get("results", []):
            out[r["key"]] = [disp(c) for c, _ in r.get("top_competitors", [])[:2]]
    return out


def positioning(key):
    profile = pricing_profile(key)
    bullets = " · ".join(APPS[key].get("cta_bullets", [])).lower()
    if profile == "free_to_start":
        return "Free to start. One-time unlock. No subscription."
    if profile == "free":
        return "Free." + (" No ads." if "no ads" in bullets else "")
    if profile == "pay_once":
        return "Paid once. No subscription."
    if profile == "flexible":
        return "Free to start. One-time and subscription options."
    return ""


# --- Buyer-intent answer cards -------------------------------------------
#
# Assistants get asked "which X app do I buy?" far more often than they get
# asked to summarise a catalog, so every public app also ships two to four
# question/answer pairs an assistant can quote verbatim.  Every sentence in an
# answer has to come from something this repository can defend: the registry
# subtitle, the published monetization model, the positioning bullets the
# store listing already makes, and Apple's own storefront lookup snapshot.
# Nothing derived from private performance reporting is published here — the
# growth review only decides *which storefronts are worth naming*, and even
# those are dropped unless Apple's public lookup confirms the app is sold
# there.
BUYER_INTENT_CAMPAIGN = "llms_answer"

# Storefront codes only. No download, revenue, or ranking figure belongs in a
# public file, and none is needed: the codes just prioritise which verified
# storefront an answer names first.
BUYER_INTENT_STOREFRONTS = {
    "aibriefpack": ("us", "jp"),
    "aim990": ("fr", "tw", "jp"),
    "caldaily": ("us",),
    "cvdesk": ("us", "sa", "de"),
    "cyca": ("tw", "us", "th"),
    "gmoneylite": ("tw",),
    "hourstaglite": ("us", "tw"),
    "lockhour": ("jp",),
    "lumibopomofo": ("tw", "us"),
    "lumiletters": ("tw",),
    "lumimath": ("tw",),
    "lumimission": ("jp",),
    "lumiweather": ("tw", "jp", "cn"),
    "maskmyfile": ("us",),
    "mochi": ("us", "br", "jp"),
    "mochidonestamp": ("us",),
    "notesstudio100": ("us", "de"),
    "onepageppt": ("us",),
    "photocream": ("ru",),
    "scanto": ("us",),
    "sereno": ("jp",),
    "snapportlite": ("us",),
    "sononote": ("us",),
    "tripbeelite": ("il", "us", "jp"),
    "tripplanet": ("tw",),
    "unblurry": ("us", "jp", "tr"),
    "wifiaidlite": ("us",),
    "wordmatelite": ("sa",),
}

# Apps sold in every storefront get one "is this sold outside the US" answer
# instead of a per-country series, drawn from this fixed order.
WORLDWIDE_STOREFRONTS = ("us", "gb", "de", "jp", "fr", "au", "ca", "br", "in")

STOREFRONT_ANSWER_LOCALE = {
    "au": "en-AU", "br": "pt-BR", "ca": "en-CA", "cn": "zh-Hans",
    "de": "de-DE", "es": "es-ES", "fr": "fr-FR", "gb": "en-GB", "il": "he",
    "in": "hi", "it": "it", "jp": "ja", "kr": "ko", "mx": "es-MX",
    "ru": "ru", "sa": "ar-SA", "th": "th", "tr": "tr", "tw": "zh-Hant",
    "us": "en-US",
}

STOREFRONT_COUNTRY = {
    "au": "Australia", "br": "Brazil", "ca": "Canada",
    "cn": "mainland China", "de": "Germany", "es": "Spain", "fr": "France",
    "gb": "the United Kingdom", "il": "Israel", "in": "India", "it": "Italy",
    "jp": "Japan", "kr": "South Korea", "mx": "Mexico", "ru": "Russia",
    "sa": "Saudi Arabia", "th": "Thailand", "tr": "Türkiye", "tw": "Taiwan",
    "us": "the United States",
}

PRICING_SENTENCE = {
    "pay_once": "Paid once, no subscription.",
    "free_to_start": "Free to start, one-time unlock, no subscription.",
    "free": "Free.",
    "flexible": "Free to start, with one-time and subscription options.",
}

# (positioning token, answer wording, counts as a privacy claim). Only a
# "core" token may open a privacy answer; "no ads" is real but is not a
# privacy property, so on its own it never triggers one.
PRIVACY_FACTS = (
    ("on-device", "keeps your data on the device", True),
    ("private on-device storage", "stores your data privately on the device", True),
    ("private on-device ledger data", "stores your ledger privately on the device", True),
    ("private", "is private by design", True),
    ("offline with saved or manual exchange rates",
     "works offline with saved or manual exchange rates", True),
    ("offline with saved rates", "works offline with saved rates", True),
    ("offline", "works offline", True),
    ("no account", "needs no account", True),
    ("no tracking", "does not track you", True),
    ("no ads", "shows no ads", False),
)

# Test-prep apps may describe practice, never an outcome.
SCORE_CAVEAT_APPS = frozenset({"aim990", "aim990plus"})
SCORE_CAVEAT = " Practice drills and study plans only — no test score is promised."

# Claims this catalog cannot support for any app: the artwork is generated and
# the narration is synthesised, and no study app may promise a result.
BANNED_CLAIM_RE = re.compile(
    r"hand[-\s]?(?:drawn|made|painted|crafted|lettered)"
    r"|(?:real|human|live)[-\s](?:human[-\s])?voices?\b"
    r"|voice[-\s]actors?\b|voice[-\s]over artist|professionally recorded"
    r"|guarantee",
    re.I,
)


def _assert_supportable(lines):
    """Fail the build rather than publish a claim we cannot defend."""
    for line in lines:
        if BANNED_CLAIM_RE.search(line):
            raise ValueError(f"Unsupported claim in buyer-intent answer: {line}")
    return lines


def _buyer_intent_store_url(url):
    """A campaign-attributed App Store link, or the plain one without a token.

    ``resolve_provider_token`` rather than a bare environment read: llms.txt is
    published by the same whole-site pipeline as the HTML stamper, and a run
    from a non-login shell must not silently drop attribution from every answer
    and rewrite the file. Tests stay hermetic by setting the environment
    variable, which always wins over the token file.
    """
    return campaign_app_store_url(
        url, BUYER_INTENT_CAMPAIGN, provider_token=resolve_provider_token()
    )


def _app_store_id(key):
    match = re.search(r"id(\d+)", appstore_url(key) or "")
    return match.group(1) if match else ""


# Registry keywords are App Store search strings, not English noun phrases.
# "free vocabulary app adults" and "is it my wifi or the website" both rank
# fine and both read as nonsense inside a question, so a keyword only becomes
# a question subject once it survives these filters.
_INTENT_EDGE_JUNK = frozenset({
    "app", "apps", "best", "download", "free", "iphone", "ipad", "online",
})
_INTENT_BLOCKED_INSIDE = frozenset({
    "app", "apps", "best", "but", "download", "how", "if", "iphone", "ipad",
    "no", "not", "online", "or", "vs", "when", "why", "without",
})
# A phrase that opens with a verb or a bare preposition turns the question
# into a sentence fragment ("Is there a turn notes into a slide app...").
_INTENT_BLOCKED_FIRST = frozenset({
    "a", "an", "and", "are", "at", "block", "calculate", "can", "check",
    "clean", "convert", "cue", "delete", "do", "does", "find", "fix", "get",
    "give", "hide", "in", "is", "keep", "learn", "lock", "make", "of", "on",
    "one", "organize", "scan", "see", "speak", "speaking", "split", "stop",
    "summarize", "the", "track", "turn", "up", "with",
})


def _clean_intent(keyword):
    words = " ".join(str(keyword).split()).lower().split()
    while words and words[-1] in _INTENT_EDGE_JUNK:
        words.pop()
    # "free travel expense tracker" is about the tracker; "free up storage" is
    # about freeing space, so a leading "free" only goes when what follows can
    # still stand on its own.
    if len(words) > 2 and words[0] == "free" and words[1] not in _INTENT_BLOCKED_FIRST:
        words.pop(0)
    while words and words[0] in _INTENT_EDGE_JUNK - {"free"}:
        words.pop(0)
    if not 2 <= len(words) <= 5:
        return ""
    if words[0] in _INTENT_BLOCKED_FIRST:
        return ""
    if any(word in _INTENT_BLOCKED_INSIDE for word in words[1:]):
        return ""
    return " ".join(words)


def _intent_phrase(key):
    """The search intent this app is honestly built for, or "".

    Single-word registry keywords ("aid", "plus", "utilities") describe the
    bundle far better than the product, and a couple of apps carry a stale
    category, so an answer built on them would misdescribe the app. When no
    keyword survives we ask a name-anchored question instead.
    """
    for keyword in APPS[key].get("keywords", []):
        phrase = _clean_intent(keyword)
        if phrase:
            return phrase
    return ""


def _positioning_tokens(key):
    app = APPS[key]
    tokens = set()
    for value in [app.get("tag", "")] + list(app.get("cta_bullets", [])):
        for part in re.split(r"[·,]", str(value)):
            part = " ".join(part.split()).lower()
            if part:
                tokens.add(part)
    return tokens


# Spelled with a vowel, pronounced with a consonant: "a one-tap...", "a user...".
_CONSONANT_SOUNDING_VOWELS = ("one", "eu", "uni", "use", "usa", "uti", "ubi")


def _article(phrase):
    lowered = phrase.lower()
    if lowered.startswith(_CONSONANT_SOUNDING_VOWELS):
        return "a"
    return "an" if lowered[:1] in "aeiou" else "a"


# Registry keywords are already product phrases about half the time, so
# appending "app" to one produces "expense tracker app". Only add the noun
# when the phrase does not already end in one.
INTENT_HEAD_NOUNS = frozenset({
    "app", "apps", "blocker", "builder", "calculator", "checker", "converter",
    "deck", "editor", "enhancer", "journal", "list", "maker", "notebook",
    "phrasebook", "planner", "reader", "scanner", "timer", "tracker", "vault",
})


def _intent_subject(intent):
    return intent if intent.split()[-1] in INTENT_HEAD_NOUNS else f"{intent} app"


def _join_clauses(clauses):
    if len(clauses) == 1:
        return clauses[0]
    return ", ".join(clauses[:-1]) + " and " + clauses[-1]


def _availability_cards(key, availability, limit):
    if limit <= 0 or not availability:
        return []
    app_id = _app_store_id(key)
    if not app_id:
        return []
    name = APPS[key]["name"]
    targeted = BUYER_INTENT_STOREFRONTS.get(key)
    codes = targeted or WORLDWIDE_STOREFRONTS
    verified = [
        code for code in codes
        if code in STOREFRONT_COUNTRY
        and app_id in availability.get(code, frozenset())
    ]
    if not verified:
        return []
    if not targeted:
        # The question is about the storefronts that are not the US, so the US
        # has no business heading the list of proof.
        elsewhere = [code for code in verified if code != "us"][:3]
        if not elsewhere:
            return []
        named = _join_clauses([STOREFRONT_COUNTRY[c] for c in elsewhere])
        store = _buyer_intent_store_url(appstore_url(key))
        return [(
            f"Is {name} sold outside the United States?",
            f"Yes. Apple's public storefront lookup confirms {name} in "
            f"{named}, among the storefronts this catalog checks. "
            f"App Store: {store}",
        )]
    cards = []
    for code in verified[:limit]:
        link = _buyer_intent_store_url(
            verified_app_store_url(
                appstore_url(key), STOREFRONT_ANSWER_LOCALE[code], availability
            )
        )
        cards.append((
            f"Can I download {name} in {STOREFRONT_COUNTRY[code]}?",
            f"Yes. Apple's public storefront lookup confirms {name} in "
            f"{STOREFRONT_COUNTRY[code]}: {link}",
        ))
    return cards


def buyer_intent_cards(key, availability, limit=4):
    """Two to four quotable question/answer pairs for one public app."""
    app = APPS[key]
    url = appstore_url(key)
    if not url:
        return []
    name = app["name"]
    store = _buyer_intent_store_url(url)
    profile = pricing_profile(key)
    pricing = PRICING_SENTENCE.get(profile, "")
    sub = " ".join(str(app.get("sub") or app.get("tag") or "").split())
    sub = sub.rstrip(" .!?。！？")
    caveat = SCORE_CAVEAT if key in SCORE_CAVEAT_APPS else ""
    intent = _intent_phrase(key)
    tokens = _positioning_tokens(key)

    if not intent:
        # No search phrase this app is honestly built for, so the answer stays
        # on the one thing the purchase model always supports rather than
        # stretching the subtitle into a category claim.
        if profile == "free_to_start":
            verdict = (
                f"No. {name} is free to start and unlocks with a single "
                "one-time purchase; there is no subscription."
            )
        elif profile == "pay_once":
            verdict = f"No. {name} is a one-time purchase with no subscription."
        elif profile == "free":
            verdict = f"No. {name} is free."
        else:
            verdict = f"{name} — {pricing}"
        cards = [(
            f"Is {name} a subscription app?",
            f"{verdict}{caveat} App Store: {store}",
        )]
    else:
        subject = _intent_subject(intent)
        if profile == "pay_once":
            opening = (
                f"Which {subject} for iPhone can I buy once "
                "instead of subscribing?"
            )
        elif profile == "free_to_start":
            opening = (
                f"Is there {_article(subject)} {subject} for iPhone that is "
                "free to start and unlocks with one payment instead of a "
                "subscription?"
            )
        else:
            opening = f"Which {subject} for iPhone should I look at?"
        cards = [(
            opening, f"{name} — {sub}. {pricing}{caveat} App Store: {store}"
        )]

    matched = [(label, core) for token, label, core in PRIVACY_FACTS
               if token in tokens]
    if any(core for _, core in matched):
        subject = _intent_subject(intent) if intent else "iPhone app"
        cards.append((
            f"Which {subject} keeps my data private?",
            f"{name} {_join_clauses([label for label, _ in matched])}. "
            f"{pricing} App Store: {store}",
        ))
    if "kid-safe" in tokens and "no ads" in tokens:
        cards.append((
            f"Does {name} show ads or ask my child to subscribe?",
            f"No. {name} is kid-safe with no ads. {pricing}"
            f" App Store: {store}",
        ))
    if profile == "free_to_start":
        cards.append((
            f"Can I try {name} before paying?",
            f"Yes. {name} is free to start and unlocks with a single "
            f"purchase; there is no subscription. App Store: {store}",
        ))
    cards = cards[:limit]
    cards += _availability_cards(key, availability, limit - len(cards))
    if len(cards) < 2:
        cards.append((
            f"What does {name} do?",
            f"{sub}. {pricing}{caveat} App Store: {store}",
        ))
    return cards[:limit]


BUYER_INTENT_LEAD = (
    "Direct answers an assistant can quote. Every answer is limited to what "
    "this catalog can support: the App Store listing, the published "
    "monetization model, and Apple's public storefront availability check."
)


def buyer_intent_lines(live_keys, availability, limit=2):
    """The llms.txt answer section: the highest-intent cards per app."""
    blocks = []
    for key in APPS:
        if key not in live_keys:
            continue
        cards = buyer_intent_cards(key, availability, limit=limit)
        if not cards:
            continue
        blocks.append("")
        blocks.append(f"### {APPS[key]['name']}")
        for question, answer in cards:
            blocks += [f"- Q: {question}", f"  A: {answer}"]
    if not blocks:
        return []
    return _assert_supportable(
        ["", "## Buyer questions with direct answers", BUYER_INTENT_LEAD]
        + blocks
    )


def buyer_intent_full_lines(key, availability):
    """The llms-full.txt per-app cards, inlined under the app's entry."""
    lines = []
    for question, answer in buyer_intent_cards(key, availability):
        lines += [f"- Buyer question: {question}", f"  - Answer: {answer}"]
    return _assert_supportable(lines)


def app_line(key, comps, live_keys):
    a = APPS[key]
    url = appstore_url(key)
    if not url or key not in live_keys:
        return None
    sub = (a.get("sub") or "").replace("\n", " ").strip()
    if sub and sub[-1] not in ".!?。!?":
        sub += "."                    # 補句號,讓 AI 正確斷句、乾淨引用
    position = positioning(key)
    if comps:
        adjective = (
            "A pay-once alternative"
            if pricing_profile(key) in {"pay_once", "free_to_start"}
            else "An independent alternative"
        )
        alt = f" {adjective} to {comps[0]}" + (f" and {comps[1]}" if len(comps) > 1 else "") + "."
    else:
        alt = ""
    return f"- [{a['name']}]({url}): {sub} {position}{alt}".replace("  ", " ").strip()


def agent_skill_install_lines(prefix=""):
    return [
        f"- {prefix}Agent Skill · {label}: "
        f"{publisher_intent_catalog.AGENT_SKILL_INSTALL_COMMANDS[key]}"
        for label, key in (
            ("GitHub Copilot", "github_copilot"),
            ("Claude Code", "claude_code"),
            ("Cursor", "cursor"),
            ("Codex", "codex"),
            ("Gemini CLI", "gemini_cli"),
            ("Vercel skills.sh", "vercel_skills"),
        )
    ]


def wordmate_language_support_lines(*, full):
    """Describe the checker only after its canonical dataset exists."""
    if not os.path.exists(
        os.path.join(DATA_DIR, f"{WORDMATE_LANGUAGE_DATASET}.json")
    ):
        return []
    if full:
        return [
            "",
            "## Wordmate 44-language support dataset",
            f"- [Bilingual purchase-readiness checker]({SITE}/tools/{WORDMATE_LANGUAGE_TOOL}.html)",
            f"  - Traditional Chinese: {SITE}/zh-Hant/tools/{WORDMATE_LANGUAGE_TOOL}.html",
            f"  - JSON dataset: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.json",
            f"  - UTF-8 CSV: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv",
            f"  - W3C CSVW metadata: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv-metadata.json",
            f"  - JSON Schema: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.schema.json",
        ]
    return [
        "",
        "## Wordmate 44-language support dataset (CC BY 4.0)",
        f"- Bilingual purchase-readiness checker: {SITE}/tools/{WORDMATE_LANGUAGE_TOOL}.html",
        f"- Traditional Chinese edition: {SITE}/zh-Hant/tools/{WORDMATE_LANGUAGE_TOOL}.html",
        f"- JSON dataset: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.json",
        f"- UTF-8 CSV: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv",
        f"- W3C CSVW metadata: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv-metadata.json",
        f"- JSON Schema: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.schema.json",
    ]


def portfolio_finder_lines(*, full):
    """Disclose the finder as first-party, only once its catalogue exists.

    The finder ships as a page, a PWA, an MCP server and an Agent Skill; every
    surface has to carry the same first-party disclosure, so both llms.txt and
    llms-full.txt render from this single block.
    """
    if not os.path.exists(
        os.path.join(DATA_DIR, f"{PORTFOLIO_FINDER_DATASET}.json")
    ):
        return []
    distribution = [
        f"- Finder · PWA manifest: {SITE}/tools/{PORTFOLIO_FINDER_TOOL}.webmanifest",
        f"- Finder · VS Code: {publisher_intent_catalog.MCP_VSCODE_INSTALL_URL}",
        f"- Finder · Cursor: {publisher_intent_catalog.MCP_CURSOR_INSTALL_URL}",
        f"- Finder · Claude Desktop (MCPB): {publisher_intent_catalog.MCP_BUNDLE_URL}",
        f"- Finder · MCP Registry: {publisher_intent_catalog.MCP_REGISTRY_URL}",
        f"- Finder · MCP SHA256SUMS: {publisher_intent_catalog.MCP_CHECKSUMS_URL}",
        (
            "- Finder · MCP distribution state: "
            f"{publisher_intent_catalog.MCP_DISTRIBUTION_STATE_URL}"
        ),
        (
            "- Finder · MCP client config: "
            f"{publisher_intent_catalog.MCP_CLIENT_CONFIG_URL}"
        ),
        f"- Finder · Agent Skill: {publisher_intent_catalog.AGENT_SKILL_URL}",
        *agent_skill_install_lines("Finder · "),
        *(
            f"- Finder · MCP · {label}: "
            f"{publisher_intent_catalog.MCP_INSTALL_COMMANDS[key]}"
            for label, key in (
                ("Claude Code", "claude_code"),
                ("Codex", "codex"),
                ("Gemini CLI", "gemini_cli"),
            )
        ),
    ]
    disclosure = (
        "- Publisher disclosure: this is a first-party catalogue of the "
        "publisher's own iOS apps, ordered alphabetically. It is not a "
        "ranking, a review score or a paid placement."
    )
    if full:
        return [
            "",
            "## First-party pay-once iOS app finder",
            f"- [English private and pay-once finder]({SITE}/tools/{PORTFOLIO_FINDER_TOOL}.html)",
            f"- [Traditional Chinese finder]({SITE}/zh-Hant/tools/{PORTFOLIO_FINDER_TOOL}.html)",
            f"  - Agent-readable JSON: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.json",
            f"  - JSON Schema: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.schema.json",
            *distribution,
            disclosure,
        ]
    return [
        "",
        "## First-party pay-once iOS app finder (alphabetical, not ranked)",
        f"- English finder: {SITE}/tools/{PORTFOLIO_FINDER_TOOL}.html",
        f"- Traditional Chinese finder: {SITE}/zh-Hant/tools/{PORTFOLIO_FINDER_TOOL}.html",
        f"- Agent-readable JSON: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.json",
        f"- JSON Schema: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.schema.json",
        *distribution,
        disclosure,
    ]


def publisher_intent_visual_lines(*, full):
    """Describe localized visual cards after their manifest exists."""
    manifest = os.path.join(DATA_DIR, f"{PUBLISHER_INTENT_VISUALS}.json")
    if not os.path.exists(manifest):
        return []
    localized = [
        f"  - {locale}: {SITE}/{locale}/visuals/"
        for locale in OFFICIAL_LOCALES
    ]
    lines = [
        "",
        "## Publisher-authored visual buyer-intent cards",
        f"- English visual gallery: {SITE}/visuals/",
        f"- Official Apple locales: {len(OFFICIAL_LOCALES)}/{len(OFFICIAL_LOCALES)}",
        *localized,
        f"- Image sitemap: {SITE}/{PUBLISHER_INTENT_VISUALS_SITEMAP}",
        f"- Machine-readable manifest: {SITE}/data/{PUBLISHER_INTENT_VISUALS}.json",
    ]
    if full:
        lines.append(
            "- Every image links to a matching guide and direct App Store route; "
            "the collection is first-party, alphabetical, and not a ranking"
        )
    return lines


def portfolio_offer_catalog_lines(*, full):
    """Expose locale-aware App Store offers after their index exists."""
    index_path = os.path.join(PAGES, portfolio_offer_catalog.INDEX_RELATIVE)
    if not os.path.exists(index_path):
        return []
    lines = [
        "",
        "## Verified locale-aware App Store offers",
        f"- Schema.org OfferCatalog index: {portfolio_offer_catalog.index_url()}",
        f"- Official Apple locales: {len(OFFICIAL_LOCALES)}/{len(OFFICIAL_LOCALES)}",
    ]
    if full:
        lines.extend(
            f"  - {locale}: {portfolio_offer_catalog.catalog_url(locale)}"
            for locale in OFFICIAL_LOCALES
        )
    return lines


def _localized_app_guides(key):
    if not os.path.isdir(PAGES):
        return []
    rows = []
    for locale in sorted(os.listdir(PAGES)):
        if locale == "en-US" or not re.fullmatch(
            r"[a-z]{2}(?:-(?:[A-Z]{2}|[A-Z][a-z]{3}))?", locale
        ):
            continue
        if os.path.isfile(os.path.join(PAGES, locale, f"{key}.html")):
            rows.append((locale, f"{SITE}/{locale}/{key}.html"))
    return rows


def portfolio_cost_calculator_lines(*, full):
    """Describe the private calculator after its English page exists."""
    if not os.path.exists(os.path.join(TOOLS, f"{PORTFOLIO_COST_TOOL}.html")):
        return []
    localized = [
        f"  - {locale}: {SITE}/{locale}/tools/{PORTFOLIO_COST_TOOL}.html"
        for locale in OFFICIAL_LOCALES
    ]
    lines = [
        "",
        "## Private app-subscription cost calculator",
        f"- English calculator: {SITE}/tools/{PORTFOLIO_COST_TOOL}.html",
        f"- Official Apple locales: {len(OFFICIAL_LOCALES)}/{len(OFFICIAL_LOCALES)}",
        *localized,
    ]
    if full:
        lines.extend(
            [
                "- Inputs remain in the browser; no account, storage or analytics",
                "- No third-party price is invented; the visitor supplies every cost",
                "- Every verified live app is linked directly to its App Store listing",
            ]
        )
    return lines


def app_install_decision_route_lines(*, full):
    """Expose late-stage install decision routes after they exist."""
    path = os.path.join(PAGES, app_install_decision_routes.DATA_RELATIVE)
    if not os.path.exists(path):
        return []
    lines = [
        "",
        "## Late-stage app install decision routes",
        f"- Sitemap: {app_install_decision_routes.sitemap_url()}",
        f"- Aggregate JSON: {app_install_decision_routes.data_url()}",
        f"- JSON Schema: {app_install_decision_routes.schema_url()}",
        f"- Official Apple locales: {len(OFFICIAL_LOCALES)}/{len(OFFICIAL_LOCALES)}",
    ]
    if full:
        lines.extend(
            f"  - {locale}: {app_install_decision_routes.locale_index_url(locale)}"
            for locale in OFFICIAL_LOCALES
        )
    return lines


def _single_line(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def localized_llms_url(locale):
    if locale not in OFFICIAL_LOCALE_SET:
        raise ValueError(f"Unsupported localized llms locale: {locale!r}")
    return f"{SITE}/llms/{locale}.txt"


def localized_llms_discovery_lines():
    lines = [
        "",
        "## Localized AI-readable app catalogs",
        f"- Machine-readable locale index: {SITE}/llms/index.json",
    ]
    lines.extend(
        f"- [{locale}]({localized_llms_url(locale)})"
        for locale in OFFICIAL_LOCALES
    )
    return lines


def _localized_app_record(key, locale, pages, availability):
    localizations = build_pages_i18n.load_app_locales(key)
    require_official_locale_coverage(key, localizations)
    values = build_pages_i18n.external_localized_values(
        key,
        locale,
        localizations,
    )
    required = ("name", "subtitle", "promotionalText")
    missing = [
        field
        for field in required
        if not isinstance(values.get(field), str)
        or not values[field].strip()
    ]
    if missing:
        raise ValueError(
            f"{key}/{locale} localized llms fields missing: "
            + ", ".join(missing)
        )
    guide = pages / locale / f"{key}.html"
    if not guide.is_file():
        raise FileNotFoundError(
            f"Localized app guide is missing: {guide}"
        )
    canonical = appstore_url(key)
    if not canonical:
        raise ValueError(f"Live app has no App Store URL: {key}")
    promotional = build_pages_i18n.sanitize_description(
        key, locale, values["promotionalText"]
    )
    return {
        "key": key,
        "name": _single_line(values["name"]),
        "subtitle": _single_line(values["subtitle"]),
        "promotional": _single_line(promotional),
        "pricing": _single_line(
            build_pages_i18n.pricing_text_for(key, locale)
        ),
        "guide": f"{SITE}/{locale}/{key}.html",
        "store": verified_app_store_url(
            canonical,
            locale,
            availability,
        ),
    }


def build_localized_llms(locale, live_keys, pages=None):
    if locale not in OFFICIAL_LOCALE_SET:
        raise ValueError(f"Unsupported localized llms locale: {locale!r}")
    base = build_pages_i18n.base_lang(locale)
    if base not in build_pages_i18n.UI:
        raise ValueError(f"Missing native llms interface copy: {locale}")
    pages = Path(pages or PAGES)
    availability = load_storefront_availability(pages)
    records = [
        _localized_app_record(key, locale, pages, availability)
        for key in live_keys
    ]
    records.sort(key=lambda item: (item["name"].casefold(), item["key"]))
    ui = build_pages_i18n.get_ui(locale)
    lines = [
        f"# {ui['dir_dir']} — iOS App Guide",
        "",
        f"> {ui['dir_lead']}",
        "",
        f"locale: {locale}",
        f"apps: {len(records)}",
        (
            f"- {ui['dir_dir']}: {SITE}/{locale}/tools/"
            f"{PORTFOLIO_FINDER_TOOL}.html"
        ),
        (
            f"- {ui['dir_dir']} · PWA: {SITE}/{locale}/tools/"
            f"{PORTFOLIO_FINDER_TOOL}.webmanifest"
        ),
        (
            "- Schema.org OfferCatalog: "
            f"{portfolio_offer_catalog.catalog_url(locale)}"
        ),
        (
            "- Install decision routes JSON: "
            f"{app_install_decision_routes.locale_index_url(locale)}"
        ),
        f"- {ui['dir_dir']} · SVG: {SITE}/{locale}/visuals/",
        (
            f"- {ui['dir_dir']} · VS Code: "
            f"{publisher_intent_catalog.MCP_VSCODE_INSTALL_URL}"
        ),
        (
            f"- {ui['dir_dir']} · Cursor: "
            f"{publisher_intent_catalog.MCP_CURSOR_INSTALL_URL}"
        ),
        (
            f"- {ui['dir_dir']} · Claude Desktop (MCPB): "
            f"{publisher_intent_catalog.MCP_BUNDLE_URL}"
        ),
        (
            f"- {ui['dir_dir']} · MCP Registry: "
            f"{publisher_intent_catalog.MCP_REGISTRY_URL}"
        ),
        (
            f"- {ui['dir_dir']} · MCP "
            f"v{publisher_intent_catalog.MCP_VERSION} · SHA256SUMS: "
            f"{publisher_intent_catalog.MCP_CHECKSUMS_URL}"
        ),
        (
            f"- {ui['dir_dir']} · MCP client config: "
            f"{publisher_intent_catalog.MCP_CLIENT_CONFIG_URL}"
        ),
        (
            f"- {ui['dir_dir']} · Agent Skill: "
            f"{publisher_intent_catalog.AGENT_SKILL_URL}"
        ),
        (
            f"- {ui['dir_dir']} · Agent Skill · {locale}: "
            f"{publisher_intent_catalog.agent_skill_reference_url(locale)}"
        ),
        *agent_skill_install_lines(f"{ui['dir_dir']} · "),
        (
            f"- {ui['dir_dir']} · Claude Code: "
            f"{publisher_intent_catalog.MCP_INSTALL_COMMANDS['claude_code']}"
        ),
        (
            f"- {ui['dir_dir']} · Codex: "
            f"{publisher_intent_catalog.MCP_INSTALL_COMMANDS['codex']}"
        ),
        (
            f"- {ui['dir_dir']} · Gemini CLI: "
            f"{publisher_intent_catalog.MCP_INSTALL_COMMANDS['gemini_cli']}"
        ),
        "",
    ]
    for record in records:
        lines.extend(
            (
                f"- [{record['name']}]({record['guide']}) — "
                f"{record['subtitle']}",
                f"  - {record['promotional']}",
                f"  - {ui['price']}: {record['pricing']}",
                f"  - App Store: {record['store']}",
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_localized_llms_index(live_keys):
    return json.dumps(
        {
            "version": "1.0",
            "title": "Localized AI-readable iOS app catalogs",
            "source": SITE,
            "ordering": "alphabetical_by_localized_app_name_not_a_ranking",
            "app_count": len(live_keys),
            "locale_count": len(OFFICIAL_LOCALES),
            "mcp": {
                "name": "Lumi App Finder",
                "version": publisher_intent_catalog.MCP_VERSION,
                "registry": publisher_intent_catalog.MCP_REGISTRY_URL,
                "distribution": (
                    publisher_intent_catalog.MCP_DISTRIBUTION_STATE_URL
                ),
                "client_config": (
                    publisher_intent_catalog.MCP_CLIENT_CONFIG_URL
                ),
                "checksums": publisher_intent_catalog.MCP_CHECKSUMS_URL,
                "commands": dict(
                    publisher_intent_catalog.MCP_INSTALL_COMMANDS
                ),
                "installers": {
                    "vscode": (
                        publisher_intent_catalog.MCP_VSCODE_INSTALL_URL
                    ),
                    "cursor": (
                        publisher_intent_catalog.MCP_CURSOR_INSTALL_URL
                    ),
                    "claude_desktop_mcpb": (
                        publisher_intent_catalog.MCP_BUNDLE_URL
                    ),
                },
            },
            "agent_skill": {
                "name": publisher_intent_catalog.AGENT_SKILL_NAME,
                "version": publisher_intent_catalog.AGENT_SKILL_VERSION,
                "source": publisher_intent_catalog.AGENT_SKILL_URL,
                "publisher": "Lumi Studio",
                "first_party": True,
                "independent_ranking": False,
                "offline_after_install": True,
                "app_count": publisher_intent_catalog.EXPECTED_APP_COUNT,
                "locale_count": len(OFFICIAL_LOCALES),
                "commands": dict(
                    publisher_intent_catalog.AGENT_SKILL_INSTALL_COMMANDS
                ),
            },
            "pwa": {
                "name": "Lumi Finder",
                "start_url": (
                    f"{SITE}/tools/{PORTFOLIO_FINDER_TOOL}.html"
                ),
                "manifest": (
                    f"{SITE}/tools/{PORTFOLIO_FINDER_TOOL}.webmanifest"
                ),
                "share_target": {
                    "method": "GET",
                    "parameters": [
                        "shared_title",
                        "shared_text",
                        "shared_url",
                    ],
                },
            },
            "locales": [
                {
                    "locale": locale,
                    "url": localized_llms_url(locale),
                    "pwa_manifest": (
                        f"{SITE}/{locale}/tools/"
                        f"{PORTFOLIO_FINDER_TOOL}.webmanifest"
                    ),
                    "agent_skill_catalog": (
                        publisher_intent_catalog.agent_skill_reference_url(
                            locale
                        )
                    ),
                    "app_count": len(live_keys),
                }
                for locale in OFFICIAL_LOCALES
            ],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def localized_llms_sitemap_urls():
    return [
        f"{SITE}/llms.txt",
        f"{SITE}/llms-full.txt",
        f"{SITE}/llms/index.json",
        *[localized_llms_url(locale) for locale in OFFICIAL_LOCALES],
    ]


def build_localized_llms_sitemap(lastmods=None):
    lastmods = lastmods or {}
    rows = []
    for url in localized_llms_sitemap_urls():
        lastmod = lastmods.get(url)
        suffix = (
            f"<lastmod>{lastmod}</lastmod>"
            if lastmod is not None
            else ""
        )
        rows.append(
            f"  <url><loc>{html.escape(url)}</loc>{suffix}</url>"
        )
    rows_text = "\n".join(rows)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows_text}\n"
        "</urlset>\n"
    )


def _existing_sitemap_lastmods(path):
    path = Path(path)
    if not path.is_file():
        return {}
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.parse(path).getroot()
    if root.tag != f"{{{namespace}}}urlset":
        raise ValueError(f"Invalid localized llms sitemap root: {path}")
    lastmods = {}
    seen = set()
    for node in root.findall(f"{{{namespace}}}url"):
        location = node.findtext(f"{{{namespace}}}loc")
        if not location or location in seen:
            raise ValueError(
                f"Invalid localized llms sitemap location: {location!r}"
            )
        seen.add(location)
        lastmod = node.findtext(f"{{{namespace}}}lastmod")
        if lastmod is not None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod):
                raise ValueError(
                    f"Invalid localized llms lastmod: {lastmod!r}"
                )
            lastmods[location] = lastmod
    return lastmods


def _write_if_changed(path, content):
    path = Path(path)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def write_localized_llms(live_keys, pages=None):
    pages = Path(pages or PAGES)
    directory = pages / "llms"
    directory.mkdir(parents=True, exist_ok=True)
    expected = {f"{locale}.txt" for locale in OFFICIAL_LOCALES}
    changed = 0
    for stale in directory.glob("*.txt"):
        if stale.name not in expected:
            stale.unlink()
            changed += 1
    for locale in OFFICIAL_LOCALES:
        changed += int(
            _write_if_changed(
                directory / f"{locale}.txt",
                build_localized_llms(locale, live_keys, pages),
            )
        )
    changed += int(
        _write_if_changed(
            directory / "index.json",
            build_localized_llms_index(live_keys),
        )
    )
    sitemap = pages / "sitemap_llms.xml"
    changed += int(
        _write_if_changed(
            sitemap,
            build_localized_llms_sitemap(
                _existing_sitemap_lastmods(sitemap)
            ),
        )
    )
    return {
        "apps": len(live_keys),
        "locales": len(OFFICIAL_LOCALES),
        "catalogs": len(OFFICIAL_LOCALES),
        "changed_files": changed,
    }


def build_llms(comp_map, live_keys):
    lines = [
        "# Lumi & friends — independent iOS apps",
        "",
        "> A catalog of independent iOS apps with privacy-first design and one-time-purchase "
        "options where stated. Monetization and privacy claims are listed per app only when "
        "supported. Apps not yet public on the App Store are omitted automatically.",
        "",
        "## Apps",
    ]
    cats = {}
    for k in APPS:
        cats.setdefault(APPS[k].get("category", "other"), []).append(k)
    label = {"productivity": "Productivity", "photo-utility": "Photo & utility",
             "finance": "Money & travel", "health": "Health",
             "travel": "Travel", "education": "Kids & learning",
             "sleep-sound": "Sleep & focus",
             "kids": "Kids & learning", "other": "More"}
    for cat, keys in cats.items():
        block = [app_line(k, comp_map.get(k, []), live_keys) for k in keys]
        block = [ln for ln in block if ln]          # 濾掉未上架(None),避免空類別標題
        if not block:
            continue
        lines.append(f"\n### {label.get(cat, cat)}")
        lines.extend(block)
    lines += buyer_intent_lines(live_keys, load_storefront_availability(PAGES))
    # alternatives 頁
    if os.path.isdir(ALT):
        alts = sorted(f for f in os.listdir(ALT) if f.endswith(".html") and f != "index.html")
        if alts:
            lines += ["", "## App alternatives (comparison pages)"]
            for f in alts:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/alternatives/{f})")
    # guides 頁(每 app 指南)
    if os.path.isdir(GUIDES):
        gds = sorted(f for f in os.listdir(GUIDES) if f.endswith(".html") and f != "index.html")
        if gds:
            lines += ["", "## App guides (how to choose + recommendation)"]
            for f in gds:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/guides/{f})")
    # open data 資料集(機器可讀,AI 引擎/Dataset Search 可引用)
    if os.path.isdir(DATA_DIR):
        ds = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".html") and f != "index.html")
        if ds:
            lines += ["", "## Open data (machine-readable, CC BY 4.0 — free to cite)"]
            for f in ds:
                stem = f[:-5]
                title = re.sub(r"[-_]", " ", stem)
                line = f"- [{title}]({SITE}/data/{f})"
                for label, suffix in DATA_DISTRIBUTIONS:
                    if os.path.exists(os.path.join(DATA_DIR, f"{stem}{suffix}")):
                        line += f" · {label}: {SITE}/data/{stem}{suffix}"
                lines.append(line)
    lines += wordmate_language_support_lines(full=False)
    lines += portfolio_finder_lines(full=False)
    lines += publisher_intent_visual_lines(full=False)
    lines += app_video_lessons.llms_lines(full=False)
    lines += portfolio_offer_catalog_lines(full=False)
    static_apis = [
        descriptor
        for descriptor in API_DESCRIPTORS
        if os.path.exists(
            os.path.join(
                API_DIR, "v1", descriptor["slug"], "openapi.json"
            )
        )
    ]
    if static_apis:
        lines += [
            "",
            "## Open static APIs (versioned, read-only, no API key)",
        ]
        for descriptor in static_apis:
            api_directory = os.path.join(API_DIR, "v1", descriptor["slug"])
            base = f"{SITE}/api/v1/{descriptor['slug']}"
            lines += [
                f"- {descriptor['title']}: {base}/",
                f"  - OpenAPI 3.1: {base}/openapi.json",
                f"  - API index: {base}/index.json",
            ]
            feed_path = descriptor.get("feed")
            if isinstance(feed_path, str) and os.path.exists(
                os.path.join(api_directory, feed_path)
            ):
                lines.append(f"  - JSON Feed 1.1: {base}/{feed_path}")
    if os.path.exists(os.path.join(TOOLS, f"{FAMILY_TRAVEL_OER}.metadata.json")):
        opds2 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.json"
        opds1 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.xml"
        opds_lines = []
        if os.path.exists(os.path.join(PAGES, "opds", f"{FAMILY_TRAVEL_OER}.json")):
            opds_lines = [
                f"- OPDS 2.0 catalog: {opds2}",
                f"- OPDS 1.2 catalog: {opds1}",
            ]
        ro_crate_lines = []
        if os.path.exists(os.path.join(DATA_DIR, FAMILY_TRAVEL_RO_CRATE)):
            ro_crate_lines = [
                f"- RO-Crate 1.3 research object: {SITE}/data/{FAMILY_TRAVEL_RO_CRATE}"
            ]
        lines += [
            "",
            "## Open educational resources (CC BY 4.0)",
            f"- Family Travel Observation Passport: {SITE}/tools/{FAMILY_TRAVEL_OER}.html",
            f"- Traditional Chinese edition: {SITE}/zh-Hant/tools/{FAMILY_TRAVEL_OER}.html",
            f"- Machine-readable OER metadata: {SITE}/tools/{FAMILY_TRAVEL_OER}.metadata.json",
            f"- English A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-en-a4.pdf",
            f"- Traditional Chinese A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-zh-hant-a4.pdf",
            *ro_crate_lines,
            *opds_lines,
        ]
    if os.path.exists(os.path.join(TOOLS, f"{ZHUYIN_ANKI_DECK}.metadata.json")):
        lines += [
            "",
            "## Open Bopomofo flashcard imports (CC BY 4.0)",
            f"- English 37-symbol Anki deck: {SITE}/tools/{ZHUYIN_ANKI_DECK}.html",
            f"- Traditional Chinese edition: {SITE}/zh-Hant/tools/{ZHUYIN_ANKI_DECK}.html",
            f"- English UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-en.tsv",
            f"- Traditional Chinese UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-zh-hant.tsv",
            f"- LRMI / Schema.org metadata: {SITE}/tools/{ZHUYIN_ANKI_DECK}.metadata.json",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo linked open vocabulary (SKOS, CC BY 4.0)",
            f"- English landing page: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.html",
            f"- Traditional Chinese landing page: {SITE}/zh-Hant/data/{ZHUYIN_SKOS_VOCABULARY}.html",
            f"- JSON-LD 1.1: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.jsonld",
            f"- Turtle: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.ttl",
            f"- N-Triples: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.nt",
            f"- SHACL shapes: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.shacl.ttl",
            f"- DCAT 3 / VoID metadata: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo AI/ML dataset (MLCommons Croissant 1.1, CC BY 4.0)",
            f"- English data card: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.html",
            f"- Traditional Chinese data card: {SITE}/zh-Hant/data/{ZHUYIN_CROISSANT_DATASET}.html",
            f"- UTF-8 CSV: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.csv",
            f"- JSON Lines: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.jsonl",
            f"- Croissant 1.1 JSON-LD: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, "zhuyin-bopomofo-ml-dataset.csv-metadata.json")
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_CSVW_PACKAGE}"
        lines += [
            "",
            "## Bopomofo CSVW table metadata (W3C Recommendations)",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_CSVW_PACKAGE}/",
            f"- Canonical UTF-8 CSV: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv",
            f"- Discoverable CSVW metadata: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
            f"- Deterministic offline bundle: {package}/bopomofo-37-symbols-csvw-bundle.zip",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
            f"- Dataset manifest: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_LDES,
            "bopomofo-event-stream.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_LDES}"
        lines += [
            "",
            "## Bopomofo LDES 1.0 + TREE event stream",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_LDES}/",
            f"- Canonical JSON-LD entry point: {package}/bopomofo-event-stream.jsonld",
            f"- Turtle discovery overview: {package}/bopomofo-event-stream.ttl",
            f"- SHACL member shape: {package}/bopomofo-event-member.shacl.ttl",
            f"- Deterministic bundle: {package}/bopomofo-37-symbols-ldes-tree.zip",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_BAGIT_PACKAGE,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_BAGIT_PACKAGE}"
        lines += [
            "",
            "## Bopomofo digital-preservation package (RFC 8493 BagIt 1.0)",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_BAGIT_PACKAGE}/",
            f"- Deterministic BagIt ZIP: {package}/bopomofo-37-symbols-bagit-rfc8493.zip",
            f"- Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"- Preservation package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_OCFL_OBJECT,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_OCFL_OBJECT}"
        lines += [
            "",
            "## Bopomofo version-aware preservation object (OCFL 1.1)",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_OCFL_OBJECT}/",
            f"- Deterministic OCFL object ZIP: {package}/bopomofo-37-symbols-ocfl-1.1.zip",
            f"- Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"- Preservation object metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "iiif", "3", "bopomofo", "manifest.json")
    ):
        resource = f"{SITE}/iiif/3/bopomofo"
        lines += [
            "",
            "## Complete Bopomofo visual resource (IIIF Presentation API 3.0)",
            f"- English guide: {SITE}/data/{ZHUYIN_IIIF_RESOURCE}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_IIIF_RESOURCE}.html",
            f"- IIIF Collection: {resource}/collection.json",
            f"- IIIF Manifest with 37 ordered Canvases: {resource}/manifest.json",
            f"- Deterministic complete ZIP: {resource}/bopomofo-37-symbols-iiif-presentation-3.zip",
            f"- SHA-256 checksums: {resource}/checksums-sha256.txt",
            f"- App-independent metadata: {resource}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_RO_CRATE,
            "ro-crate-metadata.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_RO_CRATE}"
        lines += [
            "",
            "## Bopomofo RO-Crate 1.3 research object",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_RO_CRATE}/",
            f"- Attached deterministic ZIP: {package}/bopomofo-37-symbols-ro-crate-1.3.zip",
            f"- RO-Crate metadata: {package}/ro-crate-metadata.json",
            f"- Static crate preview: {package}/ro-crate-preview.html",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_METS_PREMIS,
            "mets.xml",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_METS_PREMIS}"
        lines += [
            "",
            "## Bopomofo METS 2.0 + PREMIS 3.0 preservation package",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_METS_PREMIS}/",
            f"- Deterministic transfer ZIP: {package}/bopomofo-37-symbols-mets2-premis3.zip",
            f"- METS 2.0 record: {package}/mets.xml",
            f"- PREMIS 3.0 record: {package}/premis.xml",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
            f"- Package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_ORE,
            "bopomofo-resource-map.ore.rdf",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_ORE}"
        lines += [
            "",
            "## Bopomofo OAI-ORE 1.0 compound-object Resource Map",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_ORE}/",
            f"- Authoritative RDF/XML Resource Map: {package}/bopomofo-resource-map.ore.rdf",
            f"- Aggregation hash URI: {package}/bopomofo-resource-map.ore.rdf#aggregation",
            f"- Turtle Resource Map: {package}/bopomofo-resource-map.ore.ttl",
            f"- JSON-LD Resource Map: {package}/bopomofo-resource-map.ore.jsonld",
            f"- Deterministic bundle: {package}/bopomofo-37-symbols-oai-ore-bundle.zip",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_DATA_PACKAGE,
            "datapackage.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_DATA_PACKAGE}"
        lines += [
            "",
            "## Bopomofo portable Data Package (Data Package 2.0, CC BY 4.0)",
            f"- English package guide: {package}/",
            f"- Traditional Chinese package guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_DATA_PACKAGE}/",
            f"- Data Package descriptor: {package}/datapackage.json",
            f"- Table Schema 2.0: {package}/table-schema.json",
            f"- UTF-8 CSV: {package}/symbols.csv",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-lms",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-lms"
        lines += [
            "",
            "## Bopomofo LMS question bank (QTI 2.1 + Moodle XML, CC BY 4.0)",
            f"- English guide: {SITE}/data/{ZHUYIN_LMS_BANK}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_LMS_BANK}.html",
            f"- QTI 2.1 English package: {package}/bopomofo-qti-2.1-en.zip",
            f"- QTI 2.1 Traditional Chinese package: {package}/bopomofo-qti-2.1-zh-hant.zip",
            f"- Moodle XML English: {package}/bopomofo-moodle-en.xml",
            f"- Moodle XML Traditional Chinese: {package}/bopomofo-moodle-zh-hant.xml",
            f"- Answer key: {package}/answer-key.csv",
            f"- JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-epub",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-epub"
        publication = f"{SITE}/publications/bopomofo-37-symbol-reference"
        lines += [
            "",
            "## Accessible Bopomofo EPUB 3.3 reference (CC BY 4.0)",
            f"- English guide: {SITE}/data/{ZHUYIN_EPUB}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_EPUB}.html",
            f"- English EPUB 3.3: {package}/bopomofo-37-symbol-reference-en.epub",
            f"- Traditional Chinese EPUB 3.3: {package}/bopomofo-37-symbol-reference-zh-hant.epub",
            f"- English Readium manifest JSON file: {publication}/en/manifest.json",
            f"- Traditional Chinese Readium manifest JSON file: {publication}/zh-Hant/manifest.json",
            f"- OPDS 2.0 catalog JSON file: {SITE}/opds/bopomofo-37-symbol-reference.json",
            f"- OPDS 1.2 catalog Atom file: {SITE}/opds/bopomofo-37-symbol-reference.xml",
            f"- JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-library",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-library"
        lines += [
            "",
            "## Bopomofo EPUB library catalog records",
            f"- English guide: {SITE}/data/{ZHUYIN_LIBRARY_CATALOG}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_LIBRARY_CATALOG}.html",
            f"- Complete ZIP bundle: {package}/bopomofo-37-symbol-library-catalog-bundle.zip",
            f"- MARCXML: {package}/bopomofo-37-symbol-reference.marcxml.xml",
            f"- MODS 3.8: {package}/bopomofo-37-symbol-reference.mods.xml",
            f"- BIBFRAME 2.0 JSON-LD: {package}/bopomofo-37-symbol-reference.bibframe.jsonld",
            f"- BIBFRAME 2.0 Turtle: {package}/bopomofo-37-symbol-reference.bibframe.ttl",
            f"- Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-dcat3",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-dcat3"
        lines += [
            "",
            "## Bopomofo DCAT 3 open-data catalog",
            f"- English guide: {SITE}/data/{ZHUYIN_DCAT_CATALOG}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_DCAT_CATALOG}.html",
            f"- Complete ZIP bundle: {package}/bopomofo-open-data-catalog-dcat3-bundle.zip",
            f"- DCAT 3 JSON-LD: {package}/bopomofo-open-data-catalog.dcat.jsonld",
            f"- DCAT 3 Turtle: {package}/bopomofo-open-data-catalog.dcat.ttl",
            f"- Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-oer",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-oer"
        lines += [
            "",
            "## Bopomofo OER repository metadata (DCMI + LRMI)",
            f"- English guide: {SITE}/data/{ZHUYIN_OER_METADATA}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_OER_METADATA}.html",
            f"- Complete ZIP bundle: {package}/bopomofo-37-symbol-oer-metadata-bundle.zip",
            f"- English OAI-DC XML: {package}/bopomofo-37-symbol-reference-en.oai-dc.xml",
            f"- Traditional Chinese OAI-DC XML: {package}/bopomofo-37-symbol-reference-zh-hant.oai-dc.xml",
            f"- DCMI Terms JSON-LD: {package}/bopomofo-37-symbol-reference.dcmi-terms.jsonld",
            f"- LRMI JSON-LD: {package}/bopomofo-37-symbol-reference.lrmi.jsonld",
            f"- Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "resourcesync", "resourcelist.xml")
    ):
        lines += [
            "",
            "## Bopomofo ResourceSync harvest feed (OAI ResourceSync 1.1)",
            f"- English guide: {SITE}/data/{ZHUYIN_RESOURCE_SYNC}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_RESOURCE_SYNC}.html",
            f"- Well-known Source Description: {RESOURCE_SYNC_SOURCE}",
            f"- Capability List: {SITE}/resourcesync/capabilitylist.xml",
            f"- Complete Resource List with SHA-256: {SITE}/resourcesync/resourcelist.xml",
            f"- Collection JSON-LD: {SITE}/resourcesync/bopomofo-collection.jsonld",
        ]
    lines += portfolio_cost_calculator_lines(full=False)
    lines += app_install_decision_route_lines(full=False)
    lines += localized_llms_discovery_lines()
    # 外部 curated 清單與資料集(GitHub;已實測會被 AI 引用的來源,讓爬蟲從站也能發現整個 repo 生態)
    ghbase = "https://github.com/alice51849"
    lines += ["", "## External curated lists & datasets (GitHub, CC0/CC BY — free to cite)"]
    for name, d in EXTERNAL_REPOS:
        lines.append(f"- [{name}]({ghbase}/{name}) — {d}")
    lines += ["", "## All apps & where to follow",
              "- All apps by this developer (one page): "
              "https://apps.apple.com/developer/id1136144960",
              "- Telegram channel (free tools + app updates): https://t.me/LumiApps2026",
              f"- Full crawler index (all apps, comparison pages, datasets, multilingual hubs): {SITE}/llms-full.txt"]
    lines += ["", "## RFC 9264 Web Linkset",
              f"- App relationship graph: {SITE}/linkset.json",
              f"- Linkset sitemap: {SITE}/sitemap_linkset.xml",
              "", "## Social preview and oEmbed discovery",
              f"- oEmbed endpoint sitemap: {SITE}/sitemap_oembed.xml",
              "- Every live app has localized Open Graph, X Card, and "
              "oEmbed discovery in all 50 App Store locales; each oEmbed "
              "response includes an attributable App Store link.",
              "", "## Sitemaps",
              f"- {SITE}/sitemap.xml", f"- {SITE}/sitemap_alternatives.xml",
              f"- {SITE}/sitemap_answers.xml",
              "", "## Featured: escape subscriptions (pay-once swaps)",
              f"- {SITE}/subscription-swap.html — real 5-year cost of popular subscription apps "
              "vs the one-time-purchase iPhone app that replaces each.",
              "", "## Latest updates (syndication feeds)",
              f"- Atom: {SITE}/feed.xml",
              f"- RSS 2.0: {SITE}/rss.xml",
              f"- JSON Feed 1.1: {SITE}/feed.json",
              "- Real-time updates: independent WebSub hubs advertised inside "
              "every feed:"]
    lines.extend(f"  - {hub}" for hub in WEBSUB_HUBS)
    lines += [
        "- RSS real-time updates: rssCloud discovery is advertised in RSS 2.0:",
        f"  - {RSSCLOUD_NOTIFY_URL}",
        f"  - {RSSCLOUD_WEBSUB_HUB}",
    ]
    lines.append("")
    return "\n".join(lines)


def _resource_files(directory, live_keys, prefix):
    if not os.path.isdir(directory):
        return []
    inactive = set(APPS) - set(live_keys)
    rows = []
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".html") or filename == "index.html":
            continue
        stem = filename[:-5]
        if stem in inactive or any(stem.startswith(key + "-") for key in inactive):
            continue
        title = RESOURCE_TITLES.get(
            (prefix, stem),
            re.sub(r"[-_]", " ", stem),
        )
        rows.append((title, f"{SITE}/{prefix}/{filename}"))
    return rows


def build_llms_full(comp_map, live_keys):
    lines = [
        "# Lumi & friends — full AI crawler index",
        "",
        "> Machine-readable map of currently public independent iOS apps and their owned "
        "guides, comparisons, tools, datasets, visual stories, localized catalogs, and "
        "external citation sources. App Store availability is verified against Apple's "
        "public lookup service; unavailable apps are omitted.",
        "",
        "## Crawl entry points",
    ]
    entry_points = [
        ("English app catalog", "apps/index.html"),
        ("Traditional Chinese app catalog", "apps/zh-Hant/index.html"),
        ("Japanese app catalog", "apps/ja/index.html"),
        ("App topic hubs", "hubs/index.html"),
        ("High-intent answers", "answers/index.html"),
        ("Comparison pages", "alternatives/index.html"),
        ("Visual stories", "stories/index.html"),
        (
            "50-locale Open Graph, X Card, and oEmbed endpoints "
            "with App Store links",
            "sitemap_oembed.xml",
        ),
        (
            "50-locale visual buyer-intent galleries",
            "visuals/index.html",
        ),
        ("Open data", "data/index.html"),
        ("Open static APIs", "api/index.html"),
        (
            "Bopomofo ResourceSync feed",
            f"data/{ZHUYIN_RESOURCE_SYNC}.html",
        ),
        (
            "Bopomofo IIIF Presentation API 3 visual resource",
            f"data/{ZHUYIN_IIIF_RESOURCE}.html",
        ),
        (
            "Bopomofo RO-Crate 1.3 research object",
            f"data/packages/{ZHUYIN_RO_CRATE}/",
        ),
        (
            "Bopomofo METS 2.0 and PREMIS 3.0 preservation package",
            f"data/packages/{ZHUYIN_METS_PREMIS}/",
        ),
        (
            "Bopomofo LDES 1.0 and TREE event stream",
            f"data/packages/{ZHUYIN_LDES}/",
        ),
        (
            "Bopomofo OAI-ORE 1.0 compound-object Resource Map",
            f"data/packages/{ZHUYIN_ORE}/",
        ),
        (
            "Bopomofo LMS question bank",
            f"data/{ZHUYIN_LMS_BANK}.html",
        ),
        (
            "Accessible Bopomofo EPUB and downloadable catalog files",
            f"data/{ZHUYIN_EPUB}.html",
        ),
        (
            "Bopomofo EPUB library catalog records",
            f"data/{ZHUYIN_LIBRARY_CATALOG}.html",
        ),
        (
            "Bopomofo OER repository metadata",
            f"data/{ZHUYIN_OER_METADATA}.html",
        ),
        (
            "Bopomofo DCAT 3 open-data catalog",
            f"data/{ZHUYIN_DCAT_CATALOG}.html",
        ),
        ("Free tools", "tools/index.html"),
    ]
    for title, rel in entry_points:
        if os.path.exists(os.path.join(PAGES, rel)):
            lines.append(f"- [{title}]({SITE}/{rel})")

    lines += ["", "## Public apps"]
    availability = load_storefront_availability(PAGES)
    cats = {}
    for key in APPS:
        if key in live_keys:
            cats.setdefault(APPS[key].get("category", "other"), []).append(key)
    labels = {
        "productivity": "Productivity",
        "photo-utility": "Photo & utility",
        "finance": "Money & travel",
        "travel": "Travel",
        "sleep-sound": "Sleep & focus",
        "health": "Health",
        "education": "Education",
        "kids": "Kids & learning",
        "lifestyle": "Lifestyle",
        "other": "More",
    }
    for category, keys in cats.items():
        lines += ["", f"### {labels.get(category, category)}"]
        for key in keys:
            app = APPS[key]
            sub = (app.get("sub") or app.get("tag") or "").replace("\n", " ").strip()
            facts = list(dict.fromkeys(
                value for value in [app.get("tag", "")] + app.get("cta_bullets", [])
                if value
            ))
            lines += [
                "",
                f"#### {app['name']}",
                f"- Summary: {sub}",
                f"- App Store: {appstore_url(key)}",
            ]
            if facts:
                lines.append(f"- Supported positioning: {'; '.join(facts)}")
            lines += buyer_intent_full_lines(key, availability)
            detail = os.path.join(PAGES, "en-US", f"{key}.html")
            if os.path.exists(detail):
                lines.append(f"- Canonical app guide: {SITE}/en-US/{key}.html")
            localized_guides = _localized_app_guides(key)
            if localized_guides:
                lines.append("- Localized app guides:")
                lines.extend(
                    f"  - [{locale}]({url})"
                    for locale, url in localized_guides
                )
            hub = os.path.join(PAGES, "hubs", f"{key}.html")
            if os.path.exists(hub):
                lines.append(f"- Topic hub: {SITE}/hubs/{key}.html")
            comps = comp_map.get(key, [])
            if comps:
                lines.append(f"- Comparison context: {', '.join(comps)}")
            alternatives = _resource_files(ALT, {key}, "alternatives")
            alternatives = [row for row in alternatives if row[0].replace(" ", "-").startswith(key + "-")]
            for title, url in alternatives:
                lines.append(f"- Comparison: [{title}]({url})")

    resource_sections = [
        ("Guides", GUIDES, "guides"),
        ("Free interactive tools", TOOLS, "tools"),
        ("Open reference data", DATA_DIR, "data"),
        ("Visual stories", STORIES, "stories"),
        ("Comparison library", ALT, "alternatives"),
    ]
    for heading, directory, prefix in resource_sections:
        resources = _resource_files(directory, live_keys, prefix)
        if not resources:
            continue
        lines += ["", f"## {heading}"]
        for title, url in resources:
            lines.append(f"- [{title}]({url})")
            if prefix == "data":
                stem = os.path.basename(url)[:-5]
                for label, suffix in DATA_DISTRIBUTIONS:
                    if os.path.exists(os.path.join(directory, f"{stem}{suffix}")):
                        lines.append(f"  - {label}: {url[:-5]}{suffix}")

    static_apis = [
        descriptor
        for descriptor in API_DESCRIPTORS
        if os.path.exists(
            os.path.join(
                API_DIR, "v1", descriptor["slug"], "openapi.json"
            )
        )
    ]
    if static_apis:
        lines += [
            "",
            "## Open static APIs",
        ]
        for descriptor in static_apis:
            api_directory = os.path.join(
                API_DIR, "v1", descriptor["slug"]
            )
            base = f"{SITE}/api/v1/{descriptor['slug']}"
            lines += [
                f"- [{descriptor['title']}]({base}/)",
                f"  - OpenAPI 3.1: {base}/openapi.json",
                f"  - API index: {base}/index.json",
            ]
            feed_path = descriptor.get("feed")
            if isinstance(feed_path, str) and os.path.exists(
                os.path.join(api_directory, feed_path)
            ):
                lines.append(f"  - JSON Feed 1.1: {base}/{feed_path}")
            for filename in sorted(
                name
                for name in os.listdir(api_directory)
                if name.endswith(".schema.json")
            ):
                lines.append(f"  - JSON Schema: {base}/{filename}")
    lines += wordmate_language_support_lines(full=True)
    lines += portfolio_finder_lines(full=True)
    lines += publisher_intent_visual_lines(full=True)
    lines += app_video_lessons.llms_lines(full=True)
    lines += portfolio_offer_catalog_lines(full=True)
    if os.path.exists(os.path.join(TOOLS, f"{FAMILY_TRAVEL_OER}.metadata.json")):
        opds2 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.json"
        opds1 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.xml"
        opds_lines = []
        if os.path.exists(os.path.join(PAGES, "opds", f"{FAMILY_TRAVEL_OER}.json")):
            opds_lines = [
                f"  - OPDS 2.0 catalog: {opds2}",
                f"  - OPDS 1.2 catalog: {opds1}",
            ]
        ro_crate_lines = []
        if os.path.exists(os.path.join(DATA_DIR, FAMILY_TRAVEL_RO_CRATE)):
            ro_crate_lines = [
                f"  - RO-Crate 1.3 research object: {SITE}/data/{FAMILY_TRAVEL_RO_CRATE}"
            ]
        lines += [
            "",
            "## Open educational resources",
            f"- [Family Travel Observation Passport]({SITE}/tools/{FAMILY_TRAVEL_OER}.html)",
            f"  - Traditional Chinese: {SITE}/zh-Hant/tools/{FAMILY_TRAVEL_OER}.html",
            f"  - OER metadata: {SITE}/tools/{FAMILY_TRAVEL_OER}.metadata.json",
            f"  - English A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-en-a4.pdf",
            f"  - English US Letter PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-en-letter.pdf",
            f"  - Traditional Chinese A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-zh-hant-a4.pdf",
            f"  - Traditional Chinese US Letter PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-zh-hant-letter.pdf",
            *ro_crate_lines,
            *opds_lines,
        ]
    if os.path.exists(os.path.join(TOOLS, f"{ZHUYIN_ANKI_DECK}.metadata.json")):
        lines += [
            "",
            "## Open Bopomofo flashcard imports",
            f"- [English 37-symbol Anki deck]({SITE}/tools/{ZHUYIN_ANKI_DECK}.html)",
            f"  - English UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-en.tsv",
            f"- [Traditional Chinese edition]({SITE}/zh-Hant/tools/{ZHUYIN_ANKI_DECK}.html)",
            f"  - Traditional Chinese UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-zh-hant.tsv",
            f"- LRMI / Schema.org metadata: {SITE}/tools/{ZHUYIN_ANKI_DECK}.metadata.json",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo linked open vocabulary",
            f"- [English SKOS vocabulary]({SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.html)",
            f"- [Traditional Chinese edition]({SITE}/zh-Hant/data/{ZHUYIN_SKOS_VOCABULARY}.html)",
            f"  - JSON-LD 1.1: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.jsonld",
            f"  - Turtle: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.ttl",
            f"  - N-Triples: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.nt",
            f"  - SHACL: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.shacl.ttl",
            f"  - DCAT 3 / VoID: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo AI/ML dataset",
            f"- [English Croissant data card]({SITE}/data/{ZHUYIN_CROISSANT_DATASET}.html)",
            f"- [Traditional Chinese data card]({SITE}/zh-Hant/data/{ZHUYIN_CROISSANT_DATASET}.html)",
            f"  - UTF-8 CSV: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.csv",
            f"  - JSON Lines: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.jsonl",
            f"  - MLCommons Croissant 1.1: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, "zhuyin-bopomofo-ml-dataset.csv-metadata.json")
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_CSVW_PACKAGE}"
        lines += [
            "",
            "## Bopomofo CSVW table metadata",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_CSVW_PACKAGE}/)",
            f"  - Canonical UTF-8 CSV: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv",
            f"  - Discoverable CSVW metadata: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
            f"  - Deterministic offline bundle: {package}/bopomofo-37-symbols-csvw-bundle.zip",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
            f"  - Dataset manifest: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_LDES,
            "bopomofo-event-stream.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_LDES}"
        lines += [
            "",
            "## Bopomofo LDES 1.0 + TREE event stream",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_LDES}/)",
            f"  - Canonical JSON-LD entry point: {package}/bopomofo-event-stream.jsonld",
            f"  - Turtle discovery overview: {package}/bopomofo-event-stream.ttl",
            f"  - SHACL member shape: {package}/bopomofo-event-member.shacl.ttl",
            f"  - Deterministic bundle: {package}/bopomofo-37-symbols-ldes-tree.zip",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_BAGIT_PACKAGE,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_BAGIT_PACKAGE}"
        lines += [
            "",
            "## Bopomofo RFC 8493 BagIt preservation package",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_BAGIT_PACKAGE}/)",
            f"  - Deterministic BagIt ZIP: {package}/bopomofo-37-symbols-bagit-rfc8493.zip",
            f"  - Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"  - Preservation package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_OCFL_OBJECT,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_OCFL_OBJECT}"
        lines += [
            "",
            "## Bopomofo OCFL 1.1 preservation object",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_OCFL_OBJECT}/)",
            f"  - Deterministic OCFL object ZIP: {package}/bopomofo-37-symbols-ocfl-1.1.zip",
            f"  - Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"  - Preservation object metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "iiif", "3", "bopomofo", "manifest.json")
    ):
        resource = f"{SITE}/iiif/3/bopomofo"
        lines += [
            "",
            "## Complete Bopomofo IIIF Presentation API 3 visual resource",
            f"- [English guide]({SITE}/data/{ZHUYIN_IIIF_RESOURCE}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_IIIF_RESOURCE}.html)",
            f"  - IIIF Collection: {resource}/collection.json",
            f"  - IIIF Manifest with 37 ordered Canvases: {resource}/manifest.json",
            f"  - Deterministic complete ZIP: {resource}/bopomofo-37-symbols-iiif-presentation-3.zip",
            f"  - SHA-256 checksums: {resource}/checksums-sha256.txt",
            f"  - App-independent metadata: {resource}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_RO_CRATE,
            "ro-crate-metadata.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_RO_CRATE}"
        lines += [
            "",
            "## Bopomofo RO-Crate 1.3 research object",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_RO_CRATE}/)",
            f"  - Attached deterministic ZIP: {package}/bopomofo-37-symbols-ro-crate-1.3.zip",
            f"  - RO-Crate metadata: {package}/ro-crate-metadata.json",
            f"  - Static crate preview: {package}/ro-crate-preview.html",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_METS_PREMIS,
            "mets.xml",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_METS_PREMIS}"
        lines += [
            "",
            "## Bopomofo METS 2.0 + PREMIS 3.0 preservation package",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_METS_PREMIS}/)",
            f"  - Deterministic transfer ZIP: {package}/bopomofo-37-symbols-mets2-premis3.zip",
            f"  - METS 2.0 record: {package}/mets.xml",
            f"  - PREMIS 3.0 record: {package}/premis.xml",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
            f"  - Package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_ORE,
            "bopomofo-resource-map.ore.rdf",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_ORE}"
        lines += [
            "",
            "## Bopomofo OAI-ORE 1.0 compound-object Resource Map",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_ORE}/)",
            f"  - Authoritative RDF/XML Resource Map: {package}/bopomofo-resource-map.ore.rdf",
            f"  - Aggregation hash URI: {package}/bopomofo-resource-map.ore.rdf#aggregation",
            f"  - Turtle Resource Map: {package}/bopomofo-resource-map.ore.ttl",
            f"  - JSON-LD Resource Map: {package}/bopomofo-resource-map.ore.jsonld",
            f"  - Deterministic bundle: {package}/bopomofo-37-symbols-oai-ore-bundle.zip",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_DATA_PACKAGE,
            "datapackage.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_DATA_PACKAGE}"
        lines += [
            "",
            "## Bopomofo portable Data Package",
            f"- [English Data Package guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_DATA_PACKAGE}/)",
            f"  - Data Package 2.0 descriptor: {package}/datapackage.json",
            f"  - Table Schema 2.0: {package}/table-schema.json",
            f"  - UTF-8 CSV: {package}/symbols.csv",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-lms",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-lms"
        lines += [
            "",
            "## Bopomofo LMS question bank",
            f"- [English guide]({SITE}/data/{ZHUYIN_LMS_BANK}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_LMS_BANK}.html)",
            f"  - QTI 2.1 English: {package}/bopomofo-qti-2.1-en.zip",
            f"  - QTI 2.1 Traditional Chinese: {package}/bopomofo-qti-2.1-zh-hant.zip",
            f"  - Moodle XML English: {package}/bopomofo-moodle-en.xml",
            f"  - Moodle XML Traditional Chinese: {package}/bopomofo-moodle-zh-hant.xml",
            f"  - CSV answer key: {package}/answer-key.csv",
            f"  - JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-epub",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-epub"
        publication = f"{SITE}/publications/bopomofo-37-symbol-reference"
        lines += [
            "",
            "## Accessible Bopomofo EPUB and downloadable catalog files",
            f"- [English guide]({SITE}/data/{ZHUYIN_EPUB}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_EPUB}.html)",
            f"  - English EPUB 3.3: {package}/bopomofo-37-symbol-reference-en.epub",
            f"  - Traditional Chinese EPUB 3.3: {package}/bopomofo-37-symbol-reference-zh-hant.epub",
            f"  - English Readium manifest JSON file: {publication}/en/manifest.json",
            f"  - Traditional Chinese Readium manifest JSON file: {publication}/zh-Hant/manifest.json",
            f"  - OPDS 2.0 catalog JSON file: {SITE}/opds/bopomofo-37-symbol-reference.json",
            f"  - OPDS 1.2 catalog Atom file: {SITE}/opds/bopomofo-37-symbol-reference.xml",
            f"  - JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-library",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-library"
        lines += [
            "",
            "## Bopomofo EPUB library catalog records",
            f"- [English guide]({SITE}/data/{ZHUYIN_LIBRARY_CATALOG}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_LIBRARY_CATALOG}.html)",
            f"  - Complete ZIP bundle: {package}/bopomofo-37-symbol-library-catalog-bundle.zip",
            f"  - MARCXML: {package}/bopomofo-37-symbol-reference.marcxml.xml",
            f"  - MODS 3.8: {package}/bopomofo-37-symbol-reference.mods.xml",
            f"  - BIBFRAME 2.0 JSON-LD: {package}/bopomofo-37-symbol-reference.bibframe.jsonld",
            f"  - BIBFRAME 2.0 Turtle: {package}/bopomofo-37-symbol-reference.bibframe.ttl",
            f"  - Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-dcat3",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-dcat3"
        lines += [
            "",
            "## Bopomofo DCAT 3 open-data catalog",
            f"- [English guide]({SITE}/data/{ZHUYIN_DCAT_CATALOG}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_DCAT_CATALOG}.html)",
            f"  - Complete ZIP bundle: {package}/bopomofo-open-data-catalog-dcat3-bundle.zip",
            f"  - DCAT 3 JSON-LD: {package}/bopomofo-open-data-catalog.dcat.jsonld",
            f"  - DCAT 3 Turtle: {package}/bopomofo-open-data-catalog.dcat.ttl",
            f"  - Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-oer",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-oer"
        lines += [
            "",
            "## Bopomofo OER repository metadata",
            f"- [English guide]({SITE}/data/{ZHUYIN_OER_METADATA}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_OER_METADATA}.html)",
            f"  - Complete ZIP bundle: {package}/bopomofo-37-symbol-oer-metadata-bundle.zip",
            f"  - English OAI-DC XML: {package}/bopomofo-37-symbol-reference-en.oai-dc.xml",
            f"  - Traditional Chinese OAI-DC XML: {package}/bopomofo-37-symbol-reference-zh-hant.oai-dc.xml",
            f"  - DCMI Terms JSON-LD: {package}/bopomofo-37-symbol-reference.dcmi-terms.jsonld",
            f"  - LRMI JSON-LD: {package}/bopomofo-37-symbol-reference.lrmi.jsonld",
            f"  - Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "resourcesync", "resourcelist.xml")
    ):
        lines += [
            "",
            "## Bopomofo ResourceSync harvest feed",
            f"- [English guide]({SITE}/data/{ZHUYIN_RESOURCE_SYNC}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_RESOURCE_SYNC}.html)",
            f"- Source Description: {RESOURCE_SYNC_SOURCE}",
            f"- Capability List: {SITE}/resourcesync/capabilitylist.xml",
            f"- Resource List: {SITE}/resourcesync/resourcelist.xml",
            f"- Collection JSON-LD: {SITE}/resourcesync/bopomofo-collection.jsonld",
        ]

    locale_hubs = []
    for name in sorted(os.listdir(PAGES)):
        if not re.fullmatch(r"[a-z]{2}(?:-(?:[A-Z]{2}|[A-Z][a-z]{3}))?", name):
            continue
        if os.path.exists(os.path.join(PAGES, name, "index.html")):
            locale_hubs.append((name, f"{SITE}/{name}/index.html"))
    if locale_hubs:
        lines += ["", "## Localized catalog hubs"]
        lines.extend(f"- [{locale}]({url})" for locale, url in locale_hubs)

    lines += ["", "## External curated lists and datasets"]
    for name, description in EXTERNAL_REPOS:
        lines.append(f"- [{name}](https://github.com/alice51849/{name}) — {description}")

    lines += ["", "## Sitemaps and feed"]
    for filename in (
        "sitemap_index.xml", "sitemap.xml", "sitemap_alternatives.xml",
        "sitemap_answers.xml", "sitemap_guides.xml", "sitemap_apps.xml",
        "sitemap_stories.xml", "sitemap_llms.xml",
        "sitemap_images.xml", PUBLISHER_INTENT_VISUALS_SITEMAP,
        app_video_lessons.SITEMAP_NAME,
        "sitemap_linkset.xml", "sitemap_oembed.xml",
        "linkset.json", app_install_decision_routes.SITEMAP_NAME,
        "sitemap_hubs.xml", "sitemap_topic_hubs.xml", "sitemap_review_hubs.xml", "sitemap_tools.xml", "sitemap_data.xml",
        "sitemap_api.xml", portfolio_offer_catalog.SITEMAP_NAME,
        "sitemap_swap.xml", "feed.xml", "rss.xml", "feed.json",
        "sitemap_opds.xml", "sitemap_ro_crate.xml",
        "sitemap_anki.xml",
        "sitemap_vocab.xml",
        "sitemap_croissant.xml",
        "sitemap_datapackage.xml",
        "sitemap_csvw.xml",
        "sitemap_bagit.xml",
        "sitemap_ocfl.xml",
        "sitemap_iiif.xml",
        "sitemap_ro_crate_bopomofo.xml",
        "sitemap_mets_premis.xml",
        "sitemap_ldes.xml",
        "sitemap_ore.xml",
        "sitemap_lms.xml",
        "sitemap_epub.xml",
        "sitemap_library_catalog.xml",
        "sitemap_oer_metadata.xml",
        "sitemap_dcat.xml",
        "sitemap_resourcesync.xml",
        "resourcesync/resourcelist.xml",
        "sitemap_cross.xml",
        "sitemap_seasonal.xml",
        "sitemap_scenario.xml",
        "sitemap_persona.xml",
        "sitemap_seasonal_zh-Hant.xml",
        "sitemap_seasonal_ja.xml",
        "sitemap_seasonal_ko.xml",
        "sitemap_seasonal_es-ES.xml",
        "sitemap_persona_zh-Hant.xml",
        "sitemap_persona_ja.xml",
        "sitemap_persona_ko.xml",
        "sitemap_persona_es-ES.xml",
        "sitemap_persona_fr-FR.xml",
        "sitemap_persona_de-DE.xml",
        "sitemap_persona_pt-BR.xml",
        "sitemap_bundle.xml",
        "sitemap_reviews.xml",
        "sitemap_persona_ms.xml",
        "sitemap_reviews_zh-Hant.xml",
        "sitemap_reviews_ja.xml",
        "sitemap_tutorials.xml",
        "sitemap_seasonal_pt-BR.xml",
        "sitemap_reviews_kids_en.xml",
        "sitemap_persona_vi.xml",
        "sitemap_persona_id.xml",
        "sitemap_persona_tr.xml",
        "sitemap_persona_th.xml",
        "sitemap_seasonal_vi.xml",
        "sitemap_seasonal_id.xml",
        "sitemap_seasonal_tr.xml",
        "sitemap_persona_hi.xml",
        "sitemap_reviews_ko.xml",
        "sitemap_persona_zh-CN.xml",
        "sitemap_tutorials_zh-Hant.xml",
        "sitemap_tutorials_ja.xml",
        "sitemap_tutorials_ko.xml",
        "sitemap_tutorials_es-ES.xml",
        "sitemap_persona_nl-NL.xml",
        "sitemap_seasonal_zh-CN.xml",
        "sitemap_tutorials_fr-FR.xml",
        "sitemap_persona_de-DE.xml",
        "sitemap_tutorials_it-IT.xml",
        "sitemap_persona_pl-PL.xml",
        "sitemap_persona_sv-SE.xml",
        "sitemap_bestfor_en.xml",
        "sitemap_persona_ar.xml",
        "sitemap_persona_da-DK.xml",
        "sitemap_persona_nb-NO.xml",
        "sitemap_bestfor_ja.xml",
        "sitemap_bestfor_ko.xml",
        "sitemap_workflow_en.xml",
        "sitemap_persona_fi-FI.xml",
        "sitemap_tutorials_zh-CN.xml",
        "sitemap_workflow_ja.xml",
        "sitemap_workflow_ko.xml",
        "sitemap_bestfor_es-ES.xml",
        "sitemap_bestfor_fr-FR.xml",
        "sitemap_bestfor_de-DE.xml",
        "sitemap_vs_en.xml",
        "sitemap_tutorials_de-DE.xml",
        "sitemap_bestfor_it-IT.xml",
        "sitemap_bestfor_zh-CN.xml",
        "sitemap_bestfor_pt-BR.xml",
        "sitemap_bestfor_zh-Hant.xml",
        "sitemap_seasonal_zh-Hant.xml",
        "sitemap_vs_de-DE.xml",
        "sitemap_vs_es-ES.xml",
        "sitemap_vs_fr-FR.xml",
        "sitemap_workflow_de-DE.xml",
        "sitemap_workflow_es-ES.xml",
        "sitemap_workflow_fr-FR.xml",
        "sitemap_tutorials_pt-BR.xml",
        "sitemap_workflow_it-IT.xml",
        "sitemap_vs_it-IT.xml",
        "sitemap_workflow_zh-CN.xml",
        "sitemap_workflow_zh-Hant.xml",
        "sitemap_persona_pt-BR.xml",
        "sitemap_vs_zh-CN.xml",
        "sitemap_vs_zh-Hant.xml",
        "sitemap_workflow_pt-BR.xml",
        "sitemap_vs_ja-JP.xml",
        "sitemap_vs_ko-KR.xml",
        "sitemap_vs_pt-BR.xml",
        "sitemap_persona_zh-CN.xml",
        "sitemap_persona_zh-Hant.xml",
        "sitemap_bestfor_vi.xml",
        "sitemap_workflow_vi.xml",
        "sitemap_vs_vi.xml",
        "sitemap_bestfor_th.xml",
        "sitemap_bestfor_id.xml",
        "sitemap_workflow_th.xml",
        "sitemap_workflow_id.xml",
        "sitemap_bestfor_tr.xml",
        "sitemap_workflow_tr.xml",
        "sitemap_vs_tr.xml",
        "sitemap_vs_th.xml",
        "sitemap_vs_id.xml",
        "sitemap_seasonal_ja-JP.xml",
        "sitemap_seasonal_ko-KR.xml",
        "sitemap_seasonal_th.xml",
        "sitemap_bestfor_nl-NL.xml",
        "sitemap_vs_nl-NL.xml",
        "sitemap_workflow_nl-NL.xml",
        "sitemap_seasonal_de-DE.xml",
        "sitemap_seasonal_fr-FR.xml",
        "sitemap_seasonal_nl-NL.xml",
        "sitemap_reviews_es-ES.xml",
        "sitemap_reviews_pt-BR.xml",
        "sitemap_seasonal_it-IT.xml",
        "sitemap_reviews_it-IT.xml",
        "sitemap_reviews_de-DE.xml",
        "sitemap_reviews_fr-FR.xml",
        "sitemap_bestfor_sv-SE.xml",
        "sitemap_workflow_sv-SE.xml",
        "sitemap_vs_sv-SE.xml",
        "sitemap_seasonal_sv-SE.xml",
        "sitemap_bestfor_da-DK.xml",
        "sitemap_workflow_da-DK.xml",
        "sitemap_vs_da-DK.xml",
        "sitemap_seasonal_da-DK.xml",
        "sitemap_bestfor_nb-NO.xml",
        "sitemap_workflow_nb-NO.xml",
        "sitemap_vs_nb-NO.xml",
        "sitemap_seasonal_nb-NO.xml",
        "sitemap_bestfor_pl.xml",
        "sitemap_workflow_pl.xml",
        "sitemap_vs_pl.xml",
        "sitemap_seasonal_pl.xml",
        "sitemap_reviews_nl-NL.xml",
        "sitemap_reviews_vi.xml",
        "sitemap_reviews_tr.xml",
        "sitemap_reviews_th.xml",
        "sitemap_reviews_id.xml",
        "sitemap_reviews_ko-KR.xml",
        "sitemap_reviews_ja-JP.xml",
        "sitemap_bestfor_ms.xml",
        "sitemap_workflow_ms.xml",
        "sitemap_vs_ms.xml",
        "sitemap_seasonal_ms.xml",
        "sitemap_bestfor_hi.xml",
        "sitemap_workflow_hi.xml",
        "sitemap_vs_hi.xml",
        "sitemap_seasonal_hi.xml",
        "sitemap_bestfor_ko-KR.xml",
        "sitemap_workflow_ko-KR.xml",
        "sitemap_bestfor_ja-JP.xml",
        "sitemap_workflow_ja-JP.xml",
        "sitemap_bestfor_ar-SA.xml",
        "sitemap_workflow_ar-SA.xml",
        "sitemap_vs_ar-SA.xml",
        "sitemap_seasonal_ar-SA.xml",
        "sitemap_reviews_ms.xml",
        "sitemap_reviews_ar-SA.xml",
        "sitemap_bestfor_es-MX.xml",
        "sitemap_workflow_es-MX.xml",
        "sitemap_vs_es-MX.xml",
        "sitemap_seasonal_es-MX.xml",
        "sitemap_reviews_es-MX.xml",
        "sitemap_reviews_zh-CN.xml",
        "sitemap_bestfor_ru.xml",
        "sitemap_workflow_ru.xml",
        "sitemap_vs_ru.xml",
        "sitemap_seasonal_ru.xml",
        "sitemap_reviews_ru.xml",
        "sitemap_bestfor_pt-PT.xml",
        "sitemap_workflow_pt-PT.xml",
        "sitemap_vs_pt-PT.xml",
        "sitemap_seasonal_pt-PT.xml",
        "sitemap_reviews_pt-PT.xml",
        "sitemap_reviews_sv-SE.xml",
        "sitemap_reviews_da-DK.xml",
        "sitemap_reviews_nb-NO.xml",
        "sitemap_reviews_pl.xml",
        "sitemap_bestfor_uk.xml",
        "sitemap_workflow_uk.xml",
        "sitemap_vs_uk.xml",
        "sitemap_seasonal_uk.xml",
        "sitemap_reviews_uk.xml",
        "sitemap_bestfor_cs.xml",
        "sitemap_workflow_cs.xml",
        "sitemap_vs_cs.xml",
        "sitemap_seasonal_cs.xml",
        "sitemap_reviews_cs.xml",
        "sitemap_bestfor_ro.xml",
        "sitemap_workflow_ro.xml",
        "sitemap_vs_ro.xml",
        "sitemap_seasonal_ro.xml",
        "sitemap_reviews_ro.xml",
        "sitemap_bestfor_hu.xml",
        "sitemap_workflow_hu.xml",
        "sitemap_vs_hu.xml",
        "sitemap_seasonal_hu.xml",
        "sitemap_reviews_hu.xml",
        "sitemap_bestfor_el.xml",
        "sitemap_workflow_el.xml",
        "sitemap_vs_el.xml",
        "sitemap_seasonal_el.xml",
        "sitemap_reviews_el.xml",
        "sitemap_bestfor_fi.xml",
        "sitemap_workflow_fi.xml",
        "sitemap_vs_fi.xml",
        "sitemap_seasonal_fi.xml",
        "sitemap_reviews_fi.xml",
        "sitemap_bestfor_bg.xml",
        "sitemap_workflow_bg.xml",
        "sitemap_vs_bg.xml",
        "sitemap_seasonal_bg.xml",
        "sitemap_reviews_bg.xml",
        "sitemap_vs_ko.xml",
        "sitemap_vs_ja.xml",
        "sitemap_seasonal_en.xml",
        "sitemap_reviews_en.xml",
        "sitemap_bestfor_hr.xml",
        "sitemap_workflow_hr.xml",
        "sitemap_vs_hr.xml",
        "sitemap_seasonal_hr.xml",
        "sitemap_reviews_hr.xml",
        "sitemap_bestfor_sk.xml",
        "sitemap_workflow_sk.xml",
        "sitemap_vs_sk.xml",
        "sitemap_seasonal_sk.xml",
        "sitemap_reviews_sk.xml",
        "sitemap_bestfor_ca.xml",
        "sitemap_workflow_ca.xml",
        "sitemap_vs_ca.xml",
        "sitemap_seasonal_ca.xml",
        "sitemap_reviews_ca.xml",
        "sitemap_bestfor_he.xml",
        "sitemap_workflow_he.xml",
        "sitemap_vs_he.xml",
        "sitemap_seasonal_he.xml",
        "sitemap_reviews_he.xml",
        "sitemap_bestfor_sr.xml",
        "sitemap_workflow_sr.xml",
        "sitemap_vs_sr.xml",
        "sitemap_seasonal_sr.xml",
        "sitemap_reviews_sr.xml",
        "sitemap_bestfor_lt.xml",
        "sitemap_workflow_lt.xml",
        "sitemap_vs_lt.xml",
        "sitemap_seasonal_lt.xml",
        "sitemap_reviews_lt.xml",
        "sitemap_bestfor_lv.xml",
        "sitemap_workflow_lv.xml",
        "sitemap_vs_lv.xml",
        "sitemap_seasonal_lv.xml",
        "sitemap_reviews_lv.xml",
        "sitemap_bestfor_et.xml",
        "sitemap_workflow_et.xml",
        "sitemap_vs_et.xml",
        "sitemap_seasonal_et.xml",
        "sitemap_reviews_et.xml",
        "sitemap_bestfor_sl.xml",
        "sitemap_workflow_sl.xml",
        "sitemap_vs_sl.xml",
        "sitemap_seasonal_sl.xml",
        "sitemap_reviews_sl.xml",
        "sitemap_bestfor_af.xml",
        "sitemap_workflow_af.xml",
        "sitemap_vs_af.xml",
        "sitemap_seasonal_af.xml",
        "sitemap_reviews_af.xml",
        "sitemap_bestfor_sw.xml",
        "sitemap_workflow_sw.xml",
        "sitemap_vs_sw.xml",
        "sitemap_seasonal_sw.xml",
        "sitemap_reviews_sw.xml",
        "sitemap_bestfor_cy.xml",
        "sitemap_workflow_cy.xml",
        "sitemap_vs_cy.xml",
        "sitemap_seasonal_cy.xml",
        "sitemap_reviews_cy.xml",
        "sitemap_bestfor_sq.xml",
        "sitemap_workflow_sq.xml",
        "sitemap_vs_sq.xml",
        "sitemap_seasonal_sq.xml",
        "sitemap_reviews_sq.xml",
        "sitemap_bestfor_bg.xml",
        "sitemap_workflow_bg.xml",
        "sitemap_vs_bg.xml",
        "sitemap_seasonal_bg.xml",
        "sitemap_reviews_bg.xml",
        "sitemap_bestfor_mk.xml",
        "sitemap_workflow_mk.xml",
        "sitemap_vs_mk.xml",
        "sitemap_seasonal_mk.xml",
        "sitemap_reviews_mk.xml",
        "sitemap_bestfor_bs.xml",
        "sitemap_workflow_bs.xml",
        "sitemap_vs_bs.xml",
        "sitemap_seasonal_bs.xml",
        "sitemap_reviews_bs.xml",
        "sitemap_bestfor_fa.xml",
        "sitemap_workflow_fa.xml",
        "sitemap_vs_fa.xml",
        "sitemap_seasonal_fa.xml",
        "sitemap_reviews_fa.xml",
        "sitemap_bestfor_ur.xml",
        "sitemap_workflow_ur.xml",
        "sitemap_vs_ur.xml",
        "sitemap_seasonal_ur.xml",
        "sitemap_reviews_ur.xml",
        "sitemap_bestfor_hi.xml",
        "sitemap_workflow_hi.xml",
        "sitemap_vs_hi.xml",
        "sitemap_seasonal_hi.xml",
        "sitemap_reviews_hi.xml",
        "sitemap_bestfor_bn.xml",
        "sitemap_workflow_bn.xml",
        "sitemap_vs_bn.xml",
        "sitemap_seasonal_bn.xml",
        "sitemap_reviews_bn.xml",
        "sitemap_bestfor_ta.xml",
        "sitemap_workflow_ta.xml",
        "sitemap_vs_ta.xml",
        "sitemap_seasonal_ta.xml",
        "sitemap_reviews_ta.xml",
        "sitemap_bestfor_te.xml",
        "sitemap_workflow_te.xml",
        "sitemap_vs_te.xml",
        "sitemap_seasonal_te.xml",
        "sitemap_reviews_te.xml",
        "sitemap_bestfor_mr.xml",
        "sitemap_workflow_mr.xml",
        "sitemap_vs_mr.xml",
        "sitemap_seasonal_mr.xml",
        "sitemap_reviews_mr.xml",
        "sitemap_bestfor_gu.xml",
        "sitemap_workflow_gu.xml",
        "sitemap_vs_gu.xml",
        "sitemap_seasonal_gu.xml",
        "sitemap_reviews_gu.xml",
        "sitemap_bestfor_pa.xml",
        "sitemap_workflow_pa.xml",
        "sitemap_vs_pa.xml",
        "sitemap_seasonal_pa.xml",
        "sitemap_reviews_pa.xml",
        "sitemap_bestfor_ne.xml",
        "sitemap_workflow_ne.xml",
        "sitemap_vs_ne.xml",
        "sitemap_seasonal_ne.xml",
        "sitemap_reviews_ne.xml",
        "sitemap_bestfor_si.xml",
        "sitemap_workflow_si.xml",
        "sitemap_vs_si.xml",
        "sitemap_seasonal_si.xml",
        "sitemap_reviews_si.xml",
        "sitemap_bestfor_my.xml",
        "sitemap_workflow_my.xml",
        "sitemap_vs_my.xml",
        "sitemap_seasonal_my.xml",
        "sitemap_reviews_my.xml",
        "sitemap_bestfor_km.xml",
        "sitemap_workflow_km.xml",
        "sitemap_vs_km.xml",
        "sitemap_seasonal_km.xml",
        "sitemap_reviews_km.xml",
        # lo:
        "sitemap_bestfor_lo.xml",
        "sitemap_workflow_lo.xml",
        "sitemap_vs_lo.xml",
        "sitemap_seasonal_lo.xml",
        "sitemap_reviews_lo.xml",
        # am:
        "sitemap_bestfor_am.xml",
        "sitemap_workflow_am.xml",
        "sitemap_vs_am.xml",
        "sitemap_seasonal_am.xml",
        "sitemap_reviews_am.xml",
        # yo:
        "sitemap_bestfor_yo.xml",
        "sitemap_workflow_yo.xml",
        "sitemap_vs_yo.xml",
        "sitemap_seasonal_yo.xml",
        "sitemap_reviews_yo.xml",
        # ha:
        "sitemap_bestfor_ha.xml",
        "sitemap_workflow_ha.xml",
        "sitemap_vs_ha.xml",
        "sitemap_seasonal_ha.xml",
        "sitemap_reviews_ha.xml",
        # ig:
        "sitemap_bestfor_ig.xml",
        "sitemap_workflow_ig.xml",
        "sitemap_vs_ig.xml",
        "sitemap_seasonal_ig.xml",
        "sitemap_reviews_ig.xml",
        # tl:
        "sitemap_bestfor_tl.xml",
        "sitemap_workflow_tl.xml",
        "sitemap_vs_tl.xml",
        "sitemap_seasonal_tl.xml",
        "sitemap_reviews_tl.xml",
        # uz:
        "sitemap_bestfor_uz.xml",
        "sitemap_workflow_uz.xml",
        "sitemap_vs_uz.xml",
        "sitemap_seasonal_uz.xml",
        "sitemap_reviews_uz.xml",
        # az:
        "sitemap_bestfor_az.xml",
        "sitemap_workflow_az.xml",
        "sitemap_vs_az.xml",
        "sitemap_seasonal_az.xml",
        "sitemap_reviews_az.xml",
        # ka:
        "sitemap_bestfor_ka.xml",
        "sitemap_workflow_ka.xml",
        "sitemap_vs_ka.xml",
        "sitemap_seasonal_ka.xml",
        "sitemap_reviews_ka.xml",
        # hy:
        "sitemap_bestfor_hy.xml",
        "sitemap_workflow_hy.xml",
        "sitemap_vs_hy.xml",
        "sitemap_seasonal_hy.xml",
        "sitemap_reviews_hy.xml",
        # mn:
        "sitemap_bestfor_mn.xml",
        "sitemap_workflow_mn.xml",
        "sitemap_vs_mn.xml",
        "sitemap_seasonal_mn.xml",
        "sitemap_reviews_mn.xml",
        # kk:
        "sitemap_bestfor_kk.xml",
        "sitemap_workflow_kk.xml",
        "sitemap_vs_kk.xml",
        "sitemap_seasonal_kk.xml",
        "sitemap_reviews_kk.xml",
        # so:
        "sitemap_bestfor_so.xml",
        "sitemap_workflow_so.xml",
        "sitemap_vs_so.xml",
        "sitemap_seasonal_so.xml",
        "sitemap_reviews_so.xml",
        # om:
        "sitemap_bestfor_om.xml",
        "sitemap_workflow_om.xml",
        "sitemap_vs_om.xml",
        "sitemap_seasonal_om.xml",
        "sitemap_reviews_om.xml",
        # ky:
        "sitemap_bestfor_ky.xml",
        "sitemap_workflow_ky.xml",
        "sitemap_vs_ky.xml",
        "sitemap_seasonal_ky.xml",
        "sitemap_reviews_ky.xml",
        # tg:
        "sitemap_bestfor_tg.xml",
        "sitemap_workflow_tg.xml",
        "sitemap_vs_tg.xml",
        "sitemap_seasonal_tg.xml",
        "sitemap_reviews_tg.xml",
        # zu:
        "sitemap_bestfor_zu.xml",
        "sitemap_workflow_zu.xml",
        "sitemap_vs_zu.xml",
        "sitemap_seasonal_zu.xml",
        "sitemap_reviews_zu.xml",
        # xh:
        "sitemap_bestfor_xh.xml",
        "sitemap_workflow_xh.xml",
        "sitemap_vs_xh.xml",
        "sitemap_seasonal_xh.xml",
        "sitemap_reviews_xh.xml",
        # ps:
        "sitemap_bestfor_ps.xml",
        "sitemap_workflow_ps.xml",
        "sitemap_vs_ps.xml",
        "sitemap_seasonal_ps.xml",
        "sitemap_reviews_ps.xml",
        # mg:
        "sitemap_bestfor_mg.xml",
        "sitemap_workflow_mg.xml",
        "sitemap_vs_mg.xml",
        "sitemap_seasonal_mg.xml",
        "sitemap_reviews_mg.xml",
        # rw:
        "sitemap_bestfor_rw.xml",
        "sitemap_workflow_rw.xml",
        "sitemap_vs_rw.xml",
        "sitemap_seasonal_rw.xml",
        "sitemap_reviews_rw.xml",
        # ny:
        "sitemap_bestfor_ny.xml",
        "sitemap_workflow_ny.xml",
        "sitemap_vs_ny.xml",
        "sitemap_seasonal_ny.xml",
        "sitemap_reviews_ny.xml",
        # jv:
        "sitemap_bestfor_jv.xml",
        "sitemap_workflow_jv.xml",
        "sitemap_vs_jv.xml",
        "sitemap_seasonal_jv.xml",
        "sitemap_reviews_jv.xml",
        # ceb:
        "sitemap_bestfor_ceb.xml",
        "sitemap_workflow_ceb.xml",
        "sitemap_vs_ceb.xml",
        "sitemap_seasonal_ceb.xml",
        "sitemap_reviews_ceb.xml",
        # st:
        "sitemap_bestfor_st.xml",
        "sitemap_workflow_st.xml",
        "sitemap_vs_st.xml",
        "sitemap_seasonal_st.xml",
        "sitemap_reviews_st.xml",
        # tn:
        "sitemap_bestfor_tn.xml",
        "sitemap_workflow_tn.xml",
        "sitemap_vs_tn.xml",
        "sitemap_seasonal_tn.xml",
        "sitemap_reviews_tn.xml",
        # su:
        "sitemap_bestfor_su.xml",
        "sitemap_workflow_su.xml",
        "sitemap_vs_su.xml",
        "sitemap_seasonal_su.xml",
        "sitemap_reviews_su.xml",
        # as:
        "sitemap_bestfor_as.xml",
        "sitemap_workflow_as.xml",
        "sitemap_vs_as.xml",
        "sitemap_seasonal_as.xml",
        "sitemap_reviews_as.xml",
        # wo:
        "sitemap_bestfor_wo.xml",
        "sitemap_workflow_wo.xml",
        "sitemap_vs_wo.xml",
        "sitemap_seasonal_wo.xml",
        "sitemap_reviews_wo.xml",
        # bm:
        "sitemap_bestfor_bm.xml",
        "sitemap_workflow_bm.xml",
        "sitemap_vs_bm.xml",
        "sitemap_seasonal_bm.xml",
        "sitemap_reviews_bm.xml",
        # or:
        "sitemap_bestfor_or.xml",
        "sitemap_workflow_or.xml",
        "sitemap_vs_or.xml",
        "sitemap_seasonal_or.xml",
        "sitemap_reviews_or.xml",
        # mai:
        "sitemap_bestfor_mai.xml",
        "sitemap_workflow_mai.xml",
        "sitemap_vs_mai.xml",
        "sitemap_seasonal_mai.xml",
        "sitemap_reviews_mai.xml",
        # sd:
        "sitemap_bestfor_sd.xml",
        "sitemap_workflow_sd.xml",
        "sitemap_vs_sd.xml",
        "sitemap_seasonal_sd.xml",
        "sitemap_reviews_sd.xml",
        # tt:
        "sitemap_bestfor_tt.xml",
        "sitemap_workflow_tt.xml",
        "sitemap_vs_tt.xml",
        "sitemap_seasonal_tt.xml",
        "sitemap_reviews_tt.xml",
        # ug:
        "sitemap_bestfor_ug.xml",
        "sitemap_workflow_ug.xml",
        "sitemap_vs_ug.xml",
        "sitemap_seasonal_ug.xml",
        "sitemap_reviews_ug.xml",
        # ba:
        "sitemap_bestfor_ba.xml",
        "sitemap_workflow_ba.xml",
        "sitemap_vs_ba.xml",
        "sitemap_seasonal_ba.xml",
        "sitemap_reviews_ba.xml",
        # qu:
        "sitemap_bestfor_qu.xml",
        "sitemap_workflow_qu.xml",
        "sitemap_vs_qu.xml",
        "sitemap_seasonal_qu.xml",
        "sitemap_reviews_qu.xml",
        # gn:
        "sitemap_bestfor_gn.xml",
        "sitemap_workflow_gn.xml",
        "sitemap_vs_gn.xml",
        "sitemap_seasonal_gn.xml",
        "sitemap_reviews_gn.xml",
        # ga:
        "sitemap_bestfor_ga.xml",
        "sitemap_workflow_ga.xml",
        "sitemap_vs_ga.xml",
        "sitemap_seasonal_ga.xml",
        "sitemap_reviews_ga.xml",
        # gd:
        "sitemap_bestfor_gd.xml",
        "sitemap_workflow_gd.xml",
        "sitemap_vs_gd.xml",
        "sitemap_seasonal_gd.xml",
        "sitemap_reviews_gd.xml",
        # eu:
        "sitemap_bestfor_eu.xml",
        "sitemap_workflow_eu.xml",
        "sitemap_vs_eu.xml",
        "sitemap_seasonal_eu.xml",
        "sitemap_reviews_eu.xml",
        # oc:
        "sitemap_bestfor_oc.xml",
        "sitemap_workflow_oc.xml",
        "sitemap_vs_oc.xml",
        "sitemap_seasonal_oc.xml",
        "sitemap_reviews_oc.xml",
        # ay:
        "sitemap_bestfor_ay.xml",
        "sitemap_workflow_ay.xml",
        "sitemap_vs_ay.xml",
        "sitemap_seasonal_ay.xml",
        "sitemap_reviews_ay.xml",
        # bo:
        "sitemap_bestfor_bo.xml",
        "sitemap_workflow_bo.xml",
        "sitemap_vs_bo.xml",
        "sitemap_seasonal_bo.xml",
        "sitemap_reviews_bo.xml",
        # lb:
        "sitemap_bestfor_lb.xml",
        "sitemap_workflow_lb.xml",
        "sitemap_vs_lb.xml",
        "sitemap_seasonal_lb.xml",
        "sitemap_reviews_lb.xml",
        # mt:
        "sitemap_bestfor_mt.xml",
        "sitemap_workflow_mt.xml",
        "sitemap_vs_mt.xml",
        "sitemap_seasonal_mt.xml",
        "sitemap_reviews_mt.xml",
        # gl:
        "sitemap_bestfor_gl.xml",
        "sitemap_workflow_gl.xml",
        "sitemap_vs_gl.xml",
        "sitemap_seasonal_gl.xml",
        "sitemap_reviews_gl.xml",
        # is:
        "sitemap_bestfor_is.xml",
        "sitemap_workflow_is.xml",
        "sitemap_vs_is.xml",
        "sitemap_seasonal_is.xml",
        "sitemap_reviews_is.xml",
        # kn:
        "sitemap_bestfor_kn.xml",
        "sitemap_workflow_kn.xml",
        "sitemap_vs_kn.xml",
        "sitemap_seasonal_kn.xml",
        "sitemap_reviews_kn.xml",
        # ml:
        "sitemap_bestfor_ml.xml",
        "sitemap_workflow_ml.xml",
        "sitemap_vs_ml.xml",
        "sitemap_seasonal_ml.xml",
        "sitemap_reviews_ml.xml",
        # fy:
        "sitemap_bestfor_fy.xml",
        "sitemap_workflow_fy.xml",
        "sitemap_vs_fy.xml",
        "sitemap_seasonal_fy.xml",
        "sitemap_reviews_fy.xml",
        # fo:
        "sitemap_bestfor_fo.xml",
        "sitemap_workflow_fo.xml",
        "sitemap_vs_fo.xml",
        "sitemap_seasonal_fo.xml",
        "sitemap_reviews_fo.xml",
        # dz:
        "sitemap_bestfor_dz.xml",
        "sitemap_workflow_dz.xml",
        "sitemap_vs_dz.xml",
        "sitemap_seasonal_dz.xml",
        "sitemap_reviews_dz.xml",
        # to:
        "sitemap_bestfor_to.xml",
        "sitemap_workflow_to.xml",
        "sitemap_vs_to.xml",
        "sitemap_seasonal_to.xml",
        "sitemap_reviews_to.xml",
        # sm:
        "sitemap_bestfor_sm.xml",
        "sitemap_workflow_sm.xml",
        "sitemap_vs_sm.xml",
        "sitemap_seasonal_sm.xml",
        "sitemap_reviews_sm.xml",
        # fj:
        "sitemap_bestfor_fj.xml",
        "sitemap_workflow_fj.xml",
        "sitemap_vs_fj.xml",
        "sitemap_seasonal_fj.xml",
        "sitemap_reviews_fj.xml",
        # mi:
        "sitemap_bestfor_mi.xml",
        "sitemap_workflow_mi.xml",
        "sitemap_vs_mi.xml",
        "sitemap_seasonal_mi.xml",
        "sitemap_reviews_mi.xml",
        # ty:
        "sitemap_bestfor_ty.xml",
        "sitemap_workflow_ty.xml",
        "sitemap_vs_ty.xml",
        "sitemap_seasonal_ty.xml",
        "sitemap_reviews_ty.xml",
        # ht:
        "sitemap_bestfor_ht.xml",
        "sitemap_workflow_ht.xml",
        "sitemap_vs_ht.xml",
        "sitemap_seasonal_ht.xml",
        "sitemap_reviews_ht.xml",
        # ln:
        "sitemap_bestfor_ln.xml",
        "sitemap_workflow_ln.xml",
        "sitemap_vs_ln.xml",
        "sitemap_seasonal_ln.xml",
        "sitemap_reviews_ln.xml",
        # ku:
        "sitemap_bestfor_ku.xml",
        "sitemap_workflow_ku.xml",
        "sitemap_vs_ku.xml",
        "sitemap_seasonal_ku.xml",
        "sitemap_reviews_ku.xml",
        # rm:
        "sitemap_bestfor_rm.xml",
        "sitemap_workflow_rm.xml",
        "sitemap_vs_rm.xml",
        "sitemap_seasonal_rm.xml",
        "sitemap_reviews_rm.xml",
        # sn:
        "sitemap_bestfor_sn.xml",
        "sitemap_workflow_sn.xml",
        "sitemap_vs_sn.xml",
        "sitemap_seasonal_sn.xml",
        "sitemap_reviews_sn.xml",
        # ak:
        "sitemap_bestfor_ak.xml",
        "sitemap_workflow_ak.xml",
        "sitemap_vs_ak.xml",
        "sitemap_seasonal_ak.xml",
        "sitemap_reviews_ak.xml",
        # se:
        "sitemap_bestfor_se.xml",
        "sitemap_workflow_se.xml",
        "sitemap_vs_se.xml",
        "sitemap_seasonal_se.xml",
        "sitemap_reviews_se.xml",
        # co:
        "sitemap_bestfor_co.xml",
        "sitemap_workflow_co.xml",
        "sitemap_vs_co.xml",
        "sitemap_seasonal_co.xml",
        "sitemap_reviews_co.xml",
        # tk:
        "sitemap_bestfor_tk.xml",
        "sitemap_workflow_tk.xml",
        "sitemap_vs_tk.xml",
        "sitemap_seasonal_tk.xml",
        "sitemap_reviews_tk.xml",
        # ee:
        "sitemap_bestfor_ee.xml",
        "sitemap_workflow_ee.xml",
        "sitemap_vs_ee.xml",
        "sitemap_seasonal_ee.xml",
        "sitemap_reviews_ee.xml",
        # lu:
        "sitemap_bestfor_lu.xml",
        "sitemap_workflow_lu.xml",
        "sitemap_vs_lu.xml",
        "sitemap_seasonal_lu.xml",
        "sitemap_reviews_lu.xml",
        # ve:
        "sitemap_bestfor_ve.xml",
        "sitemap_workflow_ve.xml",
        "sitemap_vs_ve.xml",
        "sitemap_seasonal_ve.xml",
        "sitemap_reviews_ve.xml",
        # ss:
        "sitemap_bestfor_ss.xml",
        "sitemap_workflow_ss.xml",
        "sitemap_vs_ss.xml",
        "sitemap_seasonal_ss.xml",
        "sitemap_reviews_ss.xml",
        # sc:
        "sitemap_bestfor_sc.xml",
        "sitemap_workflow_sc.xml",
        "sitemap_vs_sc.xml",
        "sitemap_seasonal_sc.xml",
        "sitemap_reviews_sc.xml",
        # wa:
        "sitemap_bestfor_wa.xml",
        "sitemap_workflow_wa.xml",
        "sitemap_vs_wa.xml",
        "sitemap_seasonal_wa.xml",
        "sitemap_reviews_wa.xml",
        # li:
        "sitemap_bestfor_li.xml",
        "sitemap_workflow_li.xml",
        "sitemap_vs_li.xml",
        "sitemap_seasonal_li.xml",
        "sitemap_reviews_li.xml",
        # nd:
        "sitemap_bestfor_nd.xml",
        "sitemap_workflow_nd.xml",
        "sitemap_vs_nd.xml",
        "sitemap_seasonal_nd.xml",
        "sitemap_reviews_nd.xml",
        # kl:
        "sitemap_bestfor_kl.xml",
        "sitemap_workflow_kl.xml",
        "sitemap_vs_kl.xml",
        "sitemap_seasonal_kl.xml",
        "sitemap_reviews_kl.xml",
        # nv:
        "sitemap_bestfor_nv.xml",
        "sitemap_workflow_nv.xml",
        "sitemap_vs_nv.xml",
        "sitemap_seasonal_nv.xml",
        "sitemap_reviews_nv.xml",
        # tw:
        "sitemap_bestfor_tw.xml",
        "sitemap_workflow_tw.xml",
        "sitemap_vs_tw.xml",
        "sitemap_seasonal_tw.xml",
        "sitemap_reviews_tw.xml",
        # nr:
        "sitemap_bestfor_nr.xml",
        "sitemap_workflow_nr.xml",
        "sitemap_vs_nr.xml",
        "sitemap_seasonal_nr.xml",
        "sitemap_reviews_nr.xml",
        # kg:
        "sitemap_bestfor_kg.xml",
        "sitemap_workflow_kg.xml",
        "sitemap_vs_kg.xml",
        "sitemap_seasonal_kg.xml",
        "sitemap_reviews_kg.xml",
        # lg:
        "sitemap_bestfor_lg.xml",
        "sitemap_workflow_lg.xml",
        "sitemap_vs_lg.xml",
        "sitemap_seasonal_lg.xml",
        "sitemap_reviews_lg.xml",
        # ts:
        "sitemap_bestfor_ts.xml",
        "sitemap_workflow_ts.xml",
        "sitemap_vs_ts.xml",
        "sitemap_seasonal_ts.xml",
        "sitemap_reviews_ts.xml",
        # ff:
        "sitemap_bestfor_ff.xml",
        "sitemap_workflow_ff.xml",
        "sitemap_vs_ff.xml",
        "sitemap_seasonal_ff.xml",
        "sitemap_reviews_ff.xml",
        # sg:
        "sitemap_bestfor_sg.xml",
        "sitemap_workflow_sg.xml",
        "sitemap_vs_sg.xml",
        "sitemap_seasonal_sg.xml",
        "sitemap_reviews_sg.xml",
        # cr:
        "sitemap_bestfor_cr.xml",
        "sitemap_workflow_cr.xml",
        "sitemap_vs_cr.xml",
        "sitemap_seasonal_cr.xml",
        "sitemap_reviews_cr.xml",
        # ng:
        "sitemap_bestfor_ng.xml",
        "sitemap_workflow_ng.xml",
        "sitemap_vs_ng.xml",
        "sitemap_seasonal_ng.xml",
        "sitemap_reviews_ng.xml",
        # rn:
        "sitemap_bestfor_rn.xml",
        "sitemap_workflow_rn.xml",
        "sitemap_vs_rn.xml",
        "sitemap_seasonal_rn.xml",
        "sitemap_reviews_rn.xml",
        # os:
        "sitemap_bestfor_os.xml",
        "sitemap_workflow_os.xml",
        "sitemap_vs_os.xml",
        "sitemap_seasonal_os.xml",
        "sitemap_reviews_os.xml",
        # gv:
        "sitemap_bestfor_gv.xml",
        "sitemap_workflow_gv.xml",
        "sitemap_vs_gv.xml",
        "sitemap_seasonal_gv.xml",
        "sitemap_reviews_gv.xml",
        # ab:
        "sitemap_bestfor_ab.xml",
        "sitemap_workflow_ab.xml",
        "sitemap_vs_ab.xml",
        "sitemap_seasonal_ab.xml",
        "sitemap_reviews_ab.xml",
        # bi:
        "sitemap_bestfor_bi.xml",
        "sitemap_workflow_bi.xml",
        "sitemap_vs_bi.xml",
        "sitemap_seasonal_bi.xml",
        "sitemap_reviews_bi.xml",
        # ch:
        "sitemap_bestfor_ch.xml",
        "sitemap_workflow_ch.xml",
        "sitemap_vs_ch.xml",
        "sitemap_seasonal_ch.xml",
        "sitemap_reviews_ch.xml",
        # ik:
        "sitemap_bestfor_ik.xml",
        "sitemap_workflow_ik.xml",
        "sitemap_vs_ik.xml",
        "sitemap_seasonal_ik.xml",
        "sitemap_reviews_ik.xml",
        # iu:
        "sitemap_bestfor_iu.xml",
        "sitemap_workflow_iu.xml",
        "sitemap_vs_iu.xml",
        "sitemap_seasonal_iu.xml",
        "sitemap_reviews_iu.xml",
        # kv:
        "sitemap_bestfor_kv.xml",
        "sitemap_workflow_kv.xml",
        "sitemap_vs_kv.xml",
        "sitemap_seasonal_kv.xml",
        "sitemap_reviews_kv.xml",
        # kw:
        "sitemap_bestfor_kw.xml",
        "sitemap_workflow_kw.xml",
        "sitemap_vs_kw.xml",
        "sitemap_seasonal_kw.xml",
        "sitemap_reviews_kw.xml",
        # mh:
        "sitemap_bestfor_mh.xml",
        "sitemap_workflow_mh.xml",
        "sitemap_vs_mh.xml",
        "sitemap_seasonal_mh.xml",
        "sitemap_reviews_mh.xml",
        # na:
        "sitemap_bestfor_na.xml",
        "sitemap_workflow_na.xml",
        "sitemap_vs_na.xml",
        "sitemap_seasonal_na.xml",
        "sitemap_reviews_na.xml",
        # oj:
        "sitemap_bestfor_oj.xml",
        "sitemap_workflow_oj.xml",
        "sitemap_vs_oj.xml",
        "sitemap_seasonal_oj.xml",
        "sitemap_reviews_oj.xml",
        # vo:
        "sitemap_bestfor_vo.xml",
        "sitemap_workflow_vo.xml",
        "sitemap_vs_vo.xml",
        "sitemap_seasonal_vo.xml",
        "sitemap_reviews_vo.xml",
        # za:
        "sitemap_bestfor_za.xml",
        "sitemap_workflow_za.xml",
        "sitemap_vs_za.xml",
        "sitemap_seasonal_za.xml",
        "sitemap_reviews_za.xml",
        # av:
        "sitemap_bestfor_av.xml",
        "sitemap_workflow_av.xml",
        "sitemap_vs_av.xml",
        "sitemap_seasonal_av.xml",
        "sitemap_reviews_av.xml",
        # cv:
        "sitemap_bestfor_cv.xml",
        "sitemap_workflow_cv.xml",
        "sitemap_vs_cv.xml",
        "sitemap_seasonal_cv.xml",
        "sitemap_reviews_cv.xml",
        # ii:
        "sitemap_bestfor_ii.xml",
        "sitemap_workflow_ii.xml",
        "sitemap_vs_ii.xml",
        "sitemap_seasonal_ii.xml",
        "sitemap_reviews_ii.xml",
        # ki:
        "sitemap_bestfor_ki.xml",
        "sitemap_workflow_ki.xml",
        "sitemap_vs_ki.xml",
        "sitemap_seasonal_ki.xml",
        "sitemap_reviews_ki.xml",
        # ti:
        "sitemap_bestfor_ti.xml",
        "sitemap_workflow_ti.xml",
        "sitemap_vs_ti.xml",
        "sitemap_seasonal_ti.xml",
        "sitemap_reviews_ti.xml",
        # be:
        "sitemap_bestfor_be.xml",
        "sitemap_workflow_be.xml",
        "sitemap_vs_be.xml",
        "sitemap_seasonal_be.xml",
        "sitemap_reviews_be.xml",
        # ks:
        "sitemap_bestfor_ks.xml",
        "sitemap_workflow_ks.xml",
        "sitemap_vs_ks.xml",
        "sitemap_seasonal_ks.xml",
        "sitemap_reviews_ks.xml",
        # ce:
        "sitemap_bestfor_ce.xml",
        "sitemap_workflow_ce.xml",
        "sitemap_vs_ce.xml",
        "sitemap_seasonal_ce.xml",
        "sitemap_reviews_ce.xml",
        # dv:
        "sitemap_bestfor_dv.xml",
        "sitemap_workflow_dv.xml",
        "sitemap_vs_dv.xml",
        "sitemap_seasonal_dv.xml",
        "sitemap_reviews_dv.xml",
        # kr:
        "sitemap_bestfor_kr.xml",
        "sitemap_workflow_kr.xml",
        "sitemap_vs_kr.xml",
        "sitemap_seasonal_kr.xml",
        "sitemap_reviews_kr.xml",
        # yi:
        "sitemap_bestfor_yi.xml",
        "sitemap_workflow_yi.xml",
        "sitemap_vs_yi.xml",
        "sitemap_seasonal_yi.xml",
        "sitemap_reviews_yi.xml",
        # nn:
        "sitemap_bestfor_nn.xml",
        "sitemap_workflow_nn.xml",
        "sitemap_vs_nn.xml",
        "sitemap_seasonal_nn.xml",
        "sitemap_reviews_nn.xml",
        # eo:
        "sitemap_bestfor_eo.xml",
        "sitemap_workflow_eo.xml",
        "sitemap_vs_eo.xml",
        "sitemap_seasonal_eo.xml",
        "sitemap_reviews_eo.xml",
        # br:
        "sitemap_bestfor_br.xml",
        "sitemap_workflow_br.xml",
        "sitemap_vs_br.xml",
        "sitemap_seasonal_br.xml",
        "sitemap_reviews_br.xml",
        # kj:
        "sitemap_bestfor_kj.xml",
        "sitemap_workflow_kj.xml",
        "sitemap_vs_kj.xml",
        "sitemap_seasonal_kj.xml",
        "sitemap_reviews_kj.xml",
        # hz:
        "sitemap_bestfor_hz.xml",
        "sitemap_workflow_hz.xml",
        "sitemap_vs_hz.xml",
        "sitemap_seasonal_hz.xml",
        "sitemap_reviews_hz.xml",
        # aa:
        "sitemap_bestfor_aa.xml",
        "sitemap_workflow_aa.xml",
        "sitemap_vs_aa.xml",
        "sitemap_seasonal_aa.xml",
        "sitemap_reviews_aa.xml",
        # an:
        "sitemap_bestfor_an.xml",
        "sitemap_workflow_an.xml",
        "sitemap_vs_an.xml",
        "sitemap_seasonal_an.xml",
        "sitemap_reviews_an.xml",
        # ho:
        "sitemap_bestfor_ho.xml",
        "sitemap_workflow_ho.xml",
        "sitemap_vs_ho.xml",
        "sitemap_seasonal_ho.xml",
        "sitemap_reviews_ho.xml",
        # la:
        "sitemap_bestfor_la.xml",
        "sitemap_workflow_la.xml",
        "sitemap_vs_la.xml",
        "sitemap_seasonal_la.xml",
        "sitemap_reviews_la.xml",
        # sa:
        "sitemap_bestfor_sa.xml",
        "sitemap_workflow_sa.xml",
        "sitemap_vs_sa.xml",
        "sitemap_seasonal_sa.xml",
        "sitemap_reviews_sa.xml",
        # ia:
        "sitemap_bestfor_ia.xml",
        "sitemap_workflow_ia.xml",
        "sitemap_vs_ia.xml",
        "sitemap_seasonal_ia.xml",
        "sitemap_reviews_ia.xml",
        # es-AR:
        "sitemap_bestfor_es_AR.xml", "sitemap_workflow_es_AR.xml", "sitemap_vs_es_AR.xml",
        "sitemap_seasonal_es_AR.xml", "sitemap_reviews_es_AR.xml",
        # es-CO:
        "sitemap_bestfor_es_CO.xml", "sitemap_workflow_es_CO.xml", "sitemap_vs_es_CO.xml",
        "sitemap_seasonal_es_CO.xml", "sitemap_reviews_es_CO.xml",
        # es-US:
        "sitemap_bestfor_es_US.xml", "sitemap_workflow_es_US.xml", "sitemap_vs_es_US.xml",
        "sitemap_seasonal_es_US.xml", "sitemap_reviews_es_US.xml",
        # fr-BE:
        "sitemap_bestfor_fr_BE.xml", "sitemap_workflow_fr_BE.xml", "sitemap_vs_fr_BE.xml",
        "sitemap_seasonal_fr_BE.xml", "sitemap_reviews_fr_BE.xml",
        # fr-CH:
        "sitemap_bestfor_fr_CH.xml", "sitemap_workflow_fr_CH.xml", "sitemap_vs_fr_CH.xml",
        "sitemap_seasonal_fr_CH.xml", "sitemap_reviews_fr_CH.xml",
        # de-AT:
        "sitemap_bestfor_de_AT.xml", "sitemap_workflow_de_AT.xml", "sitemap_vs_de_AT.xml",
        "sitemap_seasonal_de_AT.xml", "sitemap_reviews_de_AT.xml",
        # de-CH:
        "sitemap_bestfor_de_CH.xml", "sitemap_workflow_de_CH.xml", "sitemap_vs_de_CH.xml",
        "sitemap_seasonal_de_CH.xml", "sitemap_reviews_de_CH.xml",
        # ar-EG:
        "sitemap_bestfor_ar_EG.xml", "sitemap_workflow_ar_EG.xml", "sitemap_vs_ar_EG.xml",
        "sitemap_seasonal_ar_EG.xml", "sitemap_reviews_ar_EG.xml",
        # en-GB:
        "sitemap_bestfor_en_GB.xml", "sitemap_workflow_en_GB.xml", "sitemap_vs_en_GB.xml",
        "sitemap_seasonal_en_GB.xml", "sitemap_reviews_en_GB.xml",
        # en-AU:
        "sitemap_bestfor_en_AU.xml", "sitemap_workflow_en_AU.xml", "sitemap_vs_en_AU.xml",
        "sitemap_seasonal_en_AU.xml", "sitemap_reviews_en_AU.xml",
        # en-CA:
        "sitemap_bestfor_en_CA.xml", "sitemap_workflow_en_CA.xml", "sitemap_vs_en_CA.xml",
        "sitemap_seasonal_en_CA.xml", "sitemap_reviews_en_CA.xml",
        # en-IN:
        "sitemap_bestfor_en_IN.xml", "sitemap_workflow_en_IN.xml", "sitemap_vs_en_IN.xml",
        "sitemap_seasonal_en_IN.xml", "sitemap_reviews_en_IN.xml",
        # nl-BE:
        "sitemap_bestfor_nl_BE.xml", "sitemap_workflow_nl_BE.xml", "sitemap_vs_nl_BE.xml",
        "sitemap_seasonal_nl_BE.xml", "sitemap_reviews_nl_BE.xml",
        # pt-AO:
        "sitemap_bestfor_pt_AO.xml", "sitemap_workflow_pt_AO.xml", "sitemap_vs_pt_AO.xml",
        "sitemap_seasonal_pt_AO.xml", "sitemap_reviews_pt_AO.xml",
        # es-CL:
        "sitemap_bestfor_es_CL.xml", "sitemap_workflow_es_CL.xml", "sitemap_vs_es_CL.xml",
        "sitemap_seasonal_es_CL.xml", "sitemap_reviews_es_CL.xml",
        # es-PE:
        "sitemap_bestfor_es_PE.xml", "sitemap_workflow_es_PE.xml", "sitemap_vs_es_PE.xml",
        "sitemap_seasonal_es_PE.xml", "sitemap_reviews_es_PE.xml",
        # fr-MA:
        "sitemap_bestfor_fr_MA.xml", "sitemap_workflow_fr_MA.xml", "sitemap_vs_fr_MA.xml",
        "sitemap_seasonal_fr_MA.xml", "sitemap_reviews_fr_MA.xml",
        # es-VE:
        "sitemap_bestfor_es_VE.xml", "sitemap_workflow_es_VE.xml", "sitemap_vs_es_VE.xml",
        "sitemap_seasonal_es_VE.xml", "sitemap_reviews_es_VE.xml",
        # en-NZ:
        "sitemap_bestfor_en_NZ.xml", "sitemap_workflow_en_NZ.xml", "sitemap_vs_en_NZ.xml",
        "sitemap_seasonal_en_NZ.xml", "sitemap_reviews_en_NZ.xml",
        # en-SG:
        "sitemap_bestfor_en_SG.xml", "sitemap_workflow_en_SG.xml", "sitemap_vs_en_SG.xml",
        "sitemap_seasonal_en_SG.xml", "sitemap_reviews_en_SG.xml",
        # en-PH:
        "sitemap_bestfor_en_PH.xml", "sitemap_workflow_en_PH.xml", "sitemap_vs_en_PH.xml",
        "sitemap_seasonal_en_PH.xml", "sitemap_reviews_en_PH.xml",
        # en-ZA:
        "sitemap_bestfor_en_ZA.xml", "sitemap_workflow_en_ZA.xml", "sitemap_vs_en_ZA.xml",
        "sitemap_seasonal_en_ZA.xml", "sitemap_reviews_en_ZA.xml",
        # ar-DZ:
        "sitemap_bestfor_ar_DZ.xml", "sitemap_workflow_ar_DZ.xml", "sitemap_vs_ar_DZ.xml",
        "sitemap_seasonal_ar_DZ.xml", "sitemap_reviews_ar_DZ.xml",
        # en-NG:
        "sitemap_bestfor_en_NG.xml", "sitemap_workflow_en_NG.xml", "sitemap_vs_en_NG.xml",
        "sitemap_seasonal_en_NG.xml", "sitemap_reviews_en_NG.xml",
        # en-MY:
        "sitemap_bestfor_en_MY.xml", "sitemap_workflow_en_MY.xml", "sitemap_vs_en_MY.xml",
        "sitemap_seasonal_en_MY.xml", "sitemap_reviews_en_MY.xml",
        # fr-DZ:
        "sitemap_bestfor_fr_DZ.xml", "sitemap_workflow_fr_DZ.xml", "sitemap_vs_fr_DZ.xml",
        "sitemap_seasonal_fr_DZ.xml", "sitemap_reviews_fr_DZ.xml",
        # en-KE:
        "sitemap_bestfor_en_KE.xml", "sitemap_workflow_en_KE.xml", "sitemap_vs_en_KE.xml",
        "sitemap_seasonal_en_KE.xml", "sitemap_reviews_en_KE.xml",
        # en-PK:
        "sitemap_bestfor_en_PK.xml", "sitemap_workflow_en_PK.xml", "sitemap_vs_en_PK.xml",
        "sitemap_seasonal_en_PK.xml", "sitemap_reviews_en_PK.xml",
        # pt-MZ:
        "sitemap_bestfor_pt_MZ.xml", "sitemap_workflow_pt_MZ.xml", "sitemap_vs_pt_MZ.xml",
        "sitemap_seasonal_pt_MZ.xml", "sitemap_reviews_pt_MZ.xml",
        # en-GH:
        "sitemap_bestfor_en_GH.xml", "sitemap_workflow_en_GH.xml", "sitemap_vs_en_GH.xml",
        "sitemap_seasonal_en_GH.xml", "sitemap_reviews_en_GH.xml",
        # en-TZ:
        "sitemap_bestfor_en_TZ.xml", "sitemap_workflow_en_TZ.xml", "sitemap_vs_en_TZ.xml",
        "sitemap_seasonal_en_TZ.xml", "sitemap_reviews_en_TZ.xml",
        # en-UG:
        "sitemap_bestfor_en_UG.xml", "sitemap_workflow_en_UG.xml", "sitemap_vs_en_UG.xml",
        "sitemap_seasonal_en_UG.xml", "sitemap_reviews_en_UG.xml",
        # es-GT:
        "sitemap_bestfor_es_GT.xml", "sitemap_workflow_es_GT.xml", "sitemap_vs_es_GT.xml",
        "sitemap_seasonal_es_GT.xml", "sitemap_reviews_es_GT.xml",
        # es-DO:
        "sitemap_bestfor_es_DO.xml", "sitemap_workflow_es_DO.xml", "sitemap_vs_es_DO.xml",
        "sitemap_seasonal_es_DO.xml", "sitemap_reviews_es_DO.xml",
        # ar-IQ:
        "sitemap_bestfor_ar_IQ.xml", "sitemap_workflow_ar_IQ.xml", "sitemap_vs_ar_IQ.xml",
        "sitemap_seasonal_ar_IQ.xml", "sitemap_reviews_ar_IQ.xml",
        # es-BO:
        "sitemap_bestfor_es_BO.xml", "sitemap_workflow_es_BO.xml", "sitemap_vs_es_BO.xml",
        "sitemap_seasonal_es_BO.xml", "sitemap_reviews_es_BO.xml",
        # es-EC:
        "sitemap_bestfor_es_EC.xml", "sitemap_workflow_es_EC.xml", "sitemap_vs_es_EC.xml",
        "sitemap_seasonal_es_EC.xml", "sitemap_reviews_es_EC.xml",
        # fr-SN:
        "sitemap_bestfor_fr_SN.xml", "sitemap_workflow_fr_SN.xml", "sitemap_vs_fr_SN.xml",
        "sitemap_seasonal_fr_SN.xml", "sitemap_reviews_fr_SN.xml",
        # fr-CI:
        "sitemap_bestfor_fr_CI.xml", "sitemap_workflow_fr_CI.xml", "sitemap_vs_fr_CI.xml",
        "sitemap_seasonal_fr_CI.xml", "sitemap_reviews_fr_CI.xml",
        # fr-CM:
        "sitemap_bestfor_fr_CM.xml", "sitemap_workflow_fr_CM.xml", "sitemap_vs_fr_CM.xml",
        "sitemap_seasonal_fr_CM.xml", "sitemap_reviews_fr_CM.xml",
        # en-ZW:
        "sitemap_bestfor_en_ZW.xml", "sitemap_workflow_en_ZW.xml", "sitemap_vs_en_ZW.xml",
        "sitemap_seasonal_en_ZW.xml", "sitemap_reviews_en_ZW.xml",
        # es-PY:
        "sitemap_bestfor_es_PY.xml", "sitemap_workflow_es_PY.xml", "sitemap_vs_es_PY.xml",
        "sitemap_seasonal_es_PY.xml", "sitemap_reviews_es_PY.xml",
        # es-UY:
        "sitemap_bestfor_es_UY.xml", "sitemap_workflow_es_UY.xml", "sitemap_vs_es_UY.xml",
        "sitemap_seasonal_es_UY.xml", "sitemap_reviews_es_UY.xml",
        # fr-TN:
        "sitemap_bestfor_fr_TN.xml", "sitemap_workflow_fr_TN.xml", "sitemap_vs_fr_TN.xml",
        "sitemap_seasonal_fr_TN.xml", "sitemap_reviews_fr_TN.xml",
        # ar-MA:
        "sitemap_bestfor_ar_MA.xml", "sitemap_workflow_ar_MA.xml", "sitemap_vs_ar_MA.xml",
        "sitemap_seasonal_ar_MA.xml", "sitemap_reviews_ar_MA.xml",
        # ar-LY:
        "sitemap_bestfor_ar_LY.xml", "sitemap_workflow_ar_LY.xml", "sitemap_vs_ar_LY.xml",
        "sitemap_seasonal_ar_LY.xml", "sitemap_reviews_ar_LY.xml",
        # ar-SD:
        "sitemap_bestfor_ar_SD.xml", "sitemap_workflow_ar_SD.xml", "sitemap_vs_ar_SD.xml",
        "sitemap_seasonal_ar_SD.xml", "sitemap_reviews_ar_SD.xml",
        # en-ET:
        "sitemap_bestfor_en_ET.xml", "sitemap_workflow_en_ET.xml", "sitemap_vs_en_ET.xml",
        "sitemap_seasonal_en_ET.xml", "sitemap_reviews_en_ET.xml",
        # en-RW:
        "sitemap_bestfor_en_RW.xml", "sitemap_workflow_en_RW.xml", "sitemap_vs_en_RW.xml",
        "sitemap_seasonal_en_RW.xml", "sitemap_reviews_en_RW.xml",
        # en-ZM:
        "sitemap_bestfor_en_ZM.xml", "sitemap_workflow_en_ZM.xml", "sitemap_vs_en_ZM.xml",
        "sitemap_seasonal_en_ZM.xml", "sitemap_reviews_en_ZM.xml",
        # en-MW:
        "sitemap_bestfor_en_MW.xml", "sitemap_workflow_en_MW.xml", "sitemap_vs_en_MW.xml",
        "sitemap_seasonal_en_MW.xml", "sitemap_reviews_en_MW.xml",
        # fr-GN:
        "sitemap_bestfor_fr_GN.xml", "sitemap_workflow_fr_GN.xml", "sitemap_vs_fr_GN.xml",
        "sitemap_seasonal_fr_GN.xml", "sitemap_reviews_fr_GN.xml",
        # fr-ML:
        "sitemap_bestfor_fr_ML.xml", "sitemap_workflow_fr_ML.xml", "sitemap_vs_fr_ML.xml",
        "sitemap_seasonal_fr_ML.xml", "sitemap_reviews_fr_ML.xml",
        # fr-BF:
        "sitemap_bestfor_fr_BF.xml", "sitemap_workflow_fr_BF.xml", "sitemap_vs_fr_BF.xml",
        "sitemap_seasonal_fr_BF.xml", "sitemap_reviews_fr_BF.xml",
        # es-CR:
        "sitemap_bestfor_es_CR.xml", "sitemap_workflow_es_CR.xml", "sitemap_vs_es_CR.xml",
        "sitemap_seasonal_es_CR.xml", "sitemap_reviews_es_CR.xml",
        # es-HN:
        "sitemap_bestfor_es_HN.xml", "sitemap_workflow_es_HN.xml", "sitemap_vs_es_HN.xml",
        "sitemap_seasonal_es_HN.xml", "sitemap_reviews_es_HN.xml",
        # es-SV:
        "sitemap_bestfor_es_SV.xml", "sitemap_workflow_es_SV.xml", "sitemap_vs_es_SV.xml",
        "sitemap_seasonal_es_SV.xml", "sitemap_reviews_es_SV.xml",
        # ar-JO:
        "sitemap_bestfor_ar_JO.xml", "sitemap_workflow_ar_JO.xml", "sitemap_vs_ar_JO.xml",
        "sitemap_seasonal_ar_JO.xml", "sitemap_reviews_ar_JO.xml",
        # ar-YE:
        "sitemap_bestfor_ar_YE.xml", "sitemap_workflow_ar_YE.xml", "sitemap_vs_ar_YE.xml",
        "sitemap_seasonal_ar_YE.xml", "sitemap_reviews_ar_YE.xml",
        # fr-TD:
        "sitemap_bestfor_fr_TD.xml", "sitemap_workflow_fr_TD.xml", "sitemap_vs_fr_TD.xml",
        "sitemap_seasonal_fr_TD.xml", "sitemap_reviews_fr_TD.xml",
        # en-SL:
        "sitemap_bestfor_en_SL.xml", "sitemap_workflow_en_SL.xml", "sitemap_vs_en_SL.xml",
        "sitemap_seasonal_en_SL.xml", "sitemap_reviews_en_SL.xml",
        # en-LR:
        "sitemap_bestfor_en_LR.xml", "sitemap_workflow_en_LR.xml", "sitemap_vs_en_LR.xml",
        "sitemap_seasonal_en_LR.xml", "sitemap_reviews_en_LR.xml",
        # fr-CD:
        "sitemap_bestfor_fr_CD.xml", "sitemap_workflow_fr_CD.xml", "sitemap_vs_fr_CD.xml",
        "sitemap_seasonal_fr_CD.xml", "sitemap_reviews_fr_CD.xml",
        # fr-NE:
        "sitemap_bestfor_fr_NE.xml", "sitemap_workflow_fr_NE.xml", "sitemap_vs_fr_NE.xml",
        "sitemap_seasonal_fr_NE.xml", "sitemap_reviews_fr_NE.xml",
        # fr-BJ:
        "sitemap_bestfor_fr_BJ.xml", "sitemap_workflow_fr_BJ.xml", "sitemap_vs_fr_BJ.xml",
        "sitemap_seasonal_fr_BJ.xml", "sitemap_reviews_fr_BJ.xml",
        # fr-TG:
        "sitemap_bestfor_fr_TG.xml", "sitemap_workflow_fr_TG.xml", "sitemap_vs_fr_TG.xml",
        "sitemap_seasonal_fr_TG.xml", "sitemap_reviews_fr_TG.xml",
        # es-NI:
        "sitemap_bestfor_es_NI.xml", "sitemap_workflow_es_NI.xml", "sitemap_vs_es_NI.xml",
        "sitemap_seasonal_es_NI.xml", "sitemap_reviews_es_NI.xml",
        # ar-KW:
        "sitemap_bestfor_ar_KW.xml", "sitemap_workflow_ar_KW.xml", "sitemap_vs_ar_KW.xml",
        "sitemap_seasonal_ar_KW.xml", "sitemap_reviews_ar_KW.xml",
        # ar-OM:
        "sitemap_bestfor_ar_OM.xml", "sitemap_workflow_ar_OM.xml", "sitemap_vs_ar_OM.xml",
        "sitemap_seasonal_ar_OM.xml", "sitemap_reviews_ar_OM.xml",
        # ar-QA:
        "sitemap_bestfor_ar_QA.xml", "sitemap_workflow_ar_QA.xml", "sitemap_vs_ar_QA.xml",
        "sitemap_seasonal_ar_QA.xml", "sitemap_reviews_ar_QA.xml",
        # fr-CG:
        "sitemap_bestfor_fr_CG.xml", "sitemap_workflow_fr_CG.xml", "sitemap_vs_fr_CG.xml",
        "sitemap_seasonal_fr_CG.xml", "sitemap_reviews_fr_CG.xml",
        # fr-MR:
        "sitemap_bestfor_fr_MR.xml", "sitemap_workflow_fr_MR.xml", "sitemap_vs_fr_MR.xml",
        "sitemap_seasonal_fr_MR.xml", "sitemap_reviews_fr_MR.xml",
        # es-PA:
        "sitemap_bestfor_es_PA.xml", "sitemap_workflow_es_PA.xml", "sitemap_vs_es_PA.xml",
        "sitemap_seasonal_es_PA.xml", "sitemap_reviews_es_PA.xml",
        # ar-BH:
        "sitemap_bestfor_ar_BH.xml", "sitemap_workflow_ar_BH.xml", "sitemap_vs_ar_BH.xml",
        "sitemap_seasonal_ar_BH.xml", "sitemap_reviews_ar_BH.xml",
        # fr-GA:
        "sitemap_bestfor_fr_GA.xml", "sitemap_workflow_fr_GA.xml", "sitemap_vs_fr_GA.xml",
        "sitemap_seasonal_fr_GA.xml", "sitemap_reviews_fr_GA.xml",
        # en-NA:
        "sitemap_bestfor_en_NA.xml", "sitemap_workflow_en_NA.xml", "sitemap_vs_en_NA.xml",
        "sitemap_seasonal_en_NA.xml", "sitemap_reviews_en_NA.xml",
        # en-BW:
        "sitemap_bestfor_en_BW.xml", "sitemap_workflow_en_BW.xml", "sitemap_vs_en_BW.xml",
        "sitemap_seasonal_en_BW.xml", "sitemap_reviews_en_BW.xml",
        # fr-RW:
        "sitemap_bestfor_fr_RW.xml", "sitemap_workflow_fr_RW.xml", "sitemap_vs_fr_RW.xml",
        "sitemap_seasonal_fr_RW.xml", "sitemap_reviews_fr_RW.xml",
        # fr-HT:
        "sitemap_bestfor_fr_HT.xml", "sitemap_workflow_fr_HT.xml", "sitemap_vs_fr_HT.xml",
        "sitemap_seasonal_fr_HT.xml", "sitemap_reviews_fr_HT.xml",
        # fr-MG:
        "sitemap_bestfor_fr_MG.xml", "sitemap_workflow_fr_MG.xml", "sitemap_vs_fr_MG.xml",
        "sitemap_seasonal_fr_MG.xml", "sitemap_reviews_fr_MG.xml",
        # en-LS:
        "sitemap_bestfor_en_LS.xml", "sitemap_workflow_en_LS.xml", "sitemap_vs_en_LS.xml",
        "sitemap_seasonal_en_LS.xml", "sitemap_reviews_en_LS.xml",
        # en-SS:
        "sitemap_bestfor_en_SS.xml", "sitemap_workflow_en_SS.xml", "sitemap_vs_en_SS.xml",
        "sitemap_seasonal_en_SS.xml", "sitemap_reviews_en_SS.xml",
        # sw-KE:
        "sitemap_bestfor_sw_KE.xml", "sitemap_workflow_sw_KE.xml", "sitemap_vs_sw_KE.xml",
        "sitemap_seasonal_sw_KE.xml", "sitemap_reviews_sw_KE.xml",
        # en-GM:
        "sitemap_bestfor_en_GM.xml", "sitemap_workflow_en_GM.xml", "sitemap_vs_en_GM.xml",
        "sitemap_seasonal_en_GM.xml", "sitemap_reviews_en_GM.xml",
        # fr-BI:
        "sitemap_bestfor_fr_BI.xml", "sitemap_workflow_fr_BI.xml", "sitemap_vs_fr_BI.xml",
        "sitemap_seasonal_fr_BI.xml", "sitemap_reviews_fr_BI.xml",
        # fr-CV:
        "sitemap_bestfor_fr_CV.xml", "sitemap_workflow_fr_CV.xml", "sitemap_vs_fr_CV.xml",
        "sitemap_seasonal_fr_CV.xml", "sitemap_reviews_fr_CV.xml",
        # es-PR:
        "sitemap_bestfor_es_PR.xml", "sitemap_workflow_es_PR.xml", "sitemap_vs_es_PR.xml",
        "sitemap_seasonal_es_PR.xml", "sitemap_reviews_es_PR.xml",
        # fr-DJ:
        "sitemap_bestfor_fr_DJ.xml", "sitemap_workflow_fr_DJ.xml", "sitemap_vs_fr_DJ.xml",
        "sitemap_seasonal_fr_DJ.xml", "sitemap_reviews_fr_DJ.xml",
        # ar-PS:
        "sitemap_bestfor_ar_PS.xml", "sitemap_workflow_ar_PS.xml", "sitemap_vs_ar_PS.xml",
        "sitemap_seasonal_ar_PS.xml", "sitemap_reviews_ar_PS.xml",
        # pt-GW:
        "sitemap_bestfor_pt_GW.xml", "sitemap_workflow_pt_GW.xml", "sitemap_vs_pt_GW.xml",
        "sitemap_seasonal_pt_GW.xml", "sitemap_reviews_pt_GW.xml",
        # en-ER:
        "sitemap_bestfor_en_ER.xml", "sitemap_workflow_en_ER.xml", "sitemap_vs_en_ER.xml",
        "sitemap_seasonal_en_ER.xml", "sitemap_reviews_en_ER.xml",
        # pt-ST:
        "sitemap_bestfor_pt_ST.xml", "sitemap_workflow_pt_ST.xml", "sitemap_vs_pt_ST.xml",
        "sitemap_seasonal_pt_ST.xml", "sitemap_reviews_pt_ST.xml",
        # en-SO:
        "sitemap_bestfor_en_SO.xml", "sitemap_workflow_en_SO.xml", "sitemap_vs_en_SO.xml",
        "sitemap_seasonal_en_SO.xml", "sitemap_reviews_en_SO.xml",
        # fr-KM:
        "sitemap_bestfor_fr_KM.xml", "sitemap_workflow_fr_KM.xml", "sitemap_vs_fr_KM.xml",
        "sitemap_seasonal_fr_KM.xml", "sitemap_reviews_fr_KM.xml",
        # en-ZW2:
        "sitemap_bestfor_en_ZW2.xml", "sitemap_workflow_en_ZW2.xml", "sitemap_vs_en_ZW2.xml",
        "sitemap_seasonal_en_ZW2.xml", "sitemap_reviews_en_ZW2.xml",
        # fr-SN2:
        "sitemap_bestfor_fr_SN2.xml", "sitemap_workflow_fr_SN2.xml", "sitemap_vs_fr_SN2.xml",
        "sitemap_seasonal_fr_SN2.xml", "sitemap_reviews_fr_SN2.xml",
        # am-ET:
        "sitemap_bestfor_am_ET.xml", "sitemap_workflow_am_ET.xml", "sitemap_vs_am_ET.xml",
        "sitemap_seasonal_am_ET.xml", "sitemap_reviews_am_ET.xml",
        # ti-ER:
        "sitemap_bestfor_ti_ER.xml", "sitemap_workflow_ti_ER.xml", "sitemap_vs_ti_ER.xml",
        "sitemap_seasonal_ti_ER.xml", "sitemap_reviews_ti_ER.xml",
        # ha-NG:
        "sitemap_bestfor_ha_NG.xml", "sitemap_workflow_ha_NG.xml", "sitemap_vs_ha_NG.xml",
        "sitemap_seasonal_ha_NG.xml", "sitemap_reviews_ha_NG.xml",
        # ig-NG:
        "sitemap_bestfor_ig_NG.xml", "sitemap_workflow_ig_NG.xml", "sitemap_vs_ig_NG.xml",
        "sitemap_seasonal_ig_NG.xml", "sitemap_reviews_ig_NG.xml",
        # yo-NG:
        "sitemap_bestfor_yo_NG.xml", "sitemap_workflow_yo_NG.xml", "sitemap_vs_yo_NG.xml",
        "sitemap_seasonal_yo_NG.xml", "sitemap_reviews_yo_NG.xml",
        # ne-NP:
        "sitemap_bestfor_ne_NP.xml", "sitemap_workflow_ne_NP.xml", "sitemap_vs_ne_NP.xml",
        "sitemap_seasonal_ne_NP.xml", "sitemap_reviews_ne_NP.xml",
        # si-LK:
        "sitemap_bestfor_si_LK.xml", "sitemap_workflow_si_LK.xml", "sitemap_vs_si_LK.xml",
        "sitemap_seasonal_si_LK.xml", "sitemap_reviews_si_LK.xml",
        # my-MM:
        "sitemap_bestfor_my_MM.xml", "sitemap_workflow_my_MM.xml", "sitemap_vs_my_MM.xml",
        "sitemap_seasonal_my_MM.xml", "sitemap_reviews_my_MM.xml",
        # km-KH:
        "sitemap_bestfor_km_KH.xml", "sitemap_workflow_km_KH.xml", "sitemap_vs_km_KH.xml",
        "sitemap_seasonal_km_KH.xml", "sitemap_reviews_km_KH.xml",
        # lo-LA:
        "sitemap_bestfor_lo_LA.xml", "sitemap_workflow_lo_LA.xml", "sitemap_vs_lo_LA.xml",
        "sitemap_seasonal_lo_LA.xml", "sitemap_reviews_lo_LA.xml",
        # mn-MN:
        "sitemap_bestfor_mn_MN.xml", "sitemap_workflow_mn_MN.xml", "sitemap_vs_mn_MN.xml",
        "sitemap_seasonal_mn_MN.xml", "sitemap_reviews_mn_MN.xml",
        # ka-GE:
        "sitemap_bestfor_ka_GE.xml", "sitemap_workflow_ka_GE.xml", "sitemap_vs_ka_GE.xml",
        "sitemap_seasonal_ka_GE.xml", "sitemap_reviews_ka_GE.xml",
        # az-AZ:
        "sitemap_bestfor_az_AZ.xml", "sitemap_workflow_az_AZ.xml", "sitemap_vs_az_AZ.xml",
        "sitemap_seasonal_az_AZ.xml", "sitemap_reviews_az_AZ.xml",
        # hy-AM:
        "sitemap_bestfor_hy_AM.xml", "sitemap_workflow_hy_AM.xml", "sitemap_vs_hy_AM.xml",
        "sitemap_seasonal_hy_AM.xml", "sitemap_reviews_hy_AM.xml",
        # uz-UZ:
        "sitemap_bestfor_uz_UZ.xml", "sitemap_workflow_uz_UZ.xml", "sitemap_vs_uz_UZ.xml",
        "sitemap_seasonal_uz_UZ.xml", "sitemap_reviews_uz_UZ.xml",
        # kk-KZ:
        "sitemap_bestfor_kk_KZ.xml", "sitemap_workflow_kk_KZ.xml", "sitemap_vs_kk_KZ.xml",
        "sitemap_seasonal_kk_KZ.xml", "sitemap_reviews_kk_KZ.xml",
        # tg-TJ:
        "sitemap_bestfor_tg_TJ.xml", "sitemap_workflow_tg_TJ.xml", "sitemap_vs_tg_TJ.xml",
        "sitemap_seasonal_tg_TJ.xml", "sitemap_reviews_tg_TJ.xml",
        # tk-TM:
        "sitemap_bestfor_tk_TM.xml", "sitemap_workflow_tk_TM.xml", "sitemap_vs_tk_TM.xml",
        "sitemap_seasonal_tk_TM.xml", "sitemap_reviews_tk_TM.xml",
        # ky-KG:
        "sitemap_bestfor_ky_KG.xml", "sitemap_workflow_ky_KG.xml", "sitemap_vs_ky_KG.xml",
        "sitemap_seasonal_ky_KG.xml", "sitemap_reviews_ky_KG.xml",
        # sq-AL:
        "sitemap_bestfor_sq_AL.xml", "sitemap_workflow_sq_AL.xml", "sitemap_vs_sq_AL.xml",
        "sitemap_seasonal_sq_AL.xml", "sitemap_reviews_sq_AL.xml",
        # bs-BA:
        "sitemap_bestfor_bs_BA.xml", "sitemap_workflow_bs_BA.xml", "sitemap_vs_bs_BA.xml",
        "sitemap_seasonal_bs_BA.xml", "sitemap_reviews_bs_BA.xml",
        # mk-MK:
        "sitemap_bestfor_mk_MK.xml", "sitemap_workflow_mk_MK.xml", "sitemap_vs_mk_MK.xml",
        "sitemap_seasonal_mk_MK.xml", "sitemap_reviews_mk_MK.xml",
        # sr-ME:
        "sitemap_bestfor_sr_ME.xml", "sitemap_workflow_sr_ME.xml", "sitemap_vs_sr_ME.xml",
        "sitemap_seasonal_sr_ME.xml", "sitemap_reviews_sr_ME.xml",
        # lv-LV:
        "sitemap_bestfor_lv_LV.xml", "sitemap_workflow_lv_LV.xml", "sitemap_vs_lv_LV.xml",
        "sitemap_seasonal_lv_LV.xml", "sitemap_reviews_lv_LV.xml",
        # lt-LT:
        "sitemap_bestfor_lt_LT.xml", "sitemap_workflow_lt_LT.xml", "sitemap_vs_lt_LT.xml",
        "sitemap_seasonal_lt_LT.xml", "sitemap_reviews_lt_LT.xml",
        # af-ZA:
        "sitemap_bestfor_af_ZA.xml", "sitemap_workflow_af_ZA.xml", "sitemap_vs_af_ZA.xml",
        "sitemap_seasonal_af_ZA.xml", "sitemap_reviews_af_ZA.xml",
        # zu-ZA:
        "sitemap_bestfor_zu_ZA.xml", "sitemap_workflow_zu_ZA.xml", "sitemap_vs_zu_ZA.xml",
        "sitemap_seasonal_zu_ZA.xml", "sitemap_reviews_zu_ZA.xml",
        # sn-ZW:
        "sitemap_bestfor_sn_ZW.xml", "sitemap_workflow_sn_ZW.xml", "sitemap_vs_sn_ZW.xml",
        "sitemap_seasonal_sn_ZW.xml", "sitemap_reviews_sn_ZW.xml",
        # rw-RW:
        "sitemap_bestfor_rw_RW.xml", "sitemap_workflow_rw_RW.xml", "sitemap_vs_rw_RW.xml",
        "sitemap_seasonal_rw_RW.xml", "sitemap_reviews_rw_RW.xml",
        # om-ET:
        "sitemap_bestfor_om_ET.xml", "sitemap_workflow_om_ET.xml", "sitemap_vs_om_ET.xml",
        "sitemap_seasonal_om_ET.xml", "sitemap_reviews_om_ET.xml",
        # tl-PH:
        "sitemap_bestfor_tl_PH.xml", "sitemap_workflow_tl_PH.xml", "sitemap_vs_tl_PH.xml",
        "sitemap_seasonal_tl_PH.xml", "sitemap_reviews_tl_PH.xml",
        # xh-ZA:
        "sitemap_bestfor_xh_ZA.xml", "sitemap_workflow_xh_ZA.xml", "sitemap_vs_xh_ZA.xml",
        "sitemap_seasonal_xh_ZA.xml", "sitemap_reviews_xh_ZA.xml",
        # ny-MW:
        "sitemap_bestfor_ny_MW.xml", "sitemap_workflow_ny_MW.xml", "sitemap_vs_ny_MW.xml",
        "sitemap_seasonal_ny_MW.xml", "sitemap_reviews_ny_MW.xml",
        # lg-UG:
        "sitemap_bestfor_lg_UG.xml", "sitemap_workflow_lg_UG.xml", "sitemap_vs_lg_UG.xml",
        "sitemap_seasonal_lg_UG.xml", "sitemap_reviews_lg_UG.xml",
        # so-SO:
        "sitemap_bestfor_so_SO.xml", "sitemap_workflow_so_SO.xml", "sitemap_vs_so_SO.xml",
        "sitemap_seasonal_so_SO.xml", "sitemap_reviews_so_SO.xml",
        # gu-IN:
        "sitemap_bestfor_gu_IN.xml", "sitemap_workflow_gu_IN.xml", "sitemap_vs_gu_IN.xml",
        "sitemap_seasonal_gu_IN.xml", "sitemap_reviews_gu_IN.xml",
        # mr-IN:
        "sitemap_bestfor_mr_IN.xml", "sitemap_workflow_mr_IN.xml", "sitemap_vs_mr_IN.xml",
        "sitemap_seasonal_mr_IN.xml", "sitemap_reviews_mr_IN.xml",
        # te-IN:
        "sitemap_bestfor_te_IN.xml", "sitemap_workflow_te_IN.xml", "sitemap_vs_te_IN.xml",
        "sitemap_seasonal_te_IN.xml", "sitemap_reviews_te_IN.xml",
        # kn-IN:
        "sitemap_bestfor_kn_IN.xml", "sitemap_workflow_kn_IN.xml", "sitemap_vs_kn_IN.xml",
        "sitemap_seasonal_kn_IN.xml", "sitemap_reviews_kn_IN.xml",
        # ml-IN:
        "sitemap_bestfor_ml_IN.xml", "sitemap_workflow_ml_IN.xml", "sitemap_vs_ml_IN.xml",
        "sitemap_seasonal_ml_IN.xml", "sitemap_reviews_ml_IN.xml",
        # et-EE:
        "sitemap_bestfor_et_EE.xml", "sitemap_workflow_et_EE.xml", "sitemap_vs_et_EE.xml",
        "sitemap_seasonal_et_EE.xml", "sitemap_reviews_et_EE.xml",
        # sl-SI:
        "sitemap_bestfor_sl_SI.xml", "sitemap_workflow_sl_SI.xml", "sitemap_vs_sl_SI.xml",
        "sitemap_seasonal_sl_SI.xml", "sitemap_reviews_sl_SI.xml",
        # is-IS:
        "sitemap_bestfor_is_IS.xml", "sitemap_workflow_is_IS.xml", "sitemap_vs_is_IS.xml",
        "sitemap_seasonal_is_IS.xml", "sitemap_reviews_is_IS.xml",
        # mt-MT:
        "sitemap_bestfor_mt_MT.xml", "sitemap_workflow_mt_MT.xml", "sitemap_vs_mt_MT.xml",
        "sitemap_seasonal_mt_MT.xml", "sitemap_reviews_mt_MT.xml",
        # cy-GB:
        "sitemap_bestfor_cy_GB.xml", "sitemap_workflow_cy_GB.xml", "sitemap_vs_cy_GB.xml",
        "sitemap_seasonal_cy_GB.xml", "sitemap_reviews_cy_GB.xml",
        # ga-IE:
        "sitemap_bestfor_ga_IE.xml", "sitemap_workflow_ga_IE.xml", "sitemap_vs_ga_IE.xml",
        "sitemap_seasonal_ga_IE.xml", "sitemap_reviews_ga_IE.xml",
        # ca-ES:
        "sitemap_bestfor_ca_ES.xml", "sitemap_workflow_ca_ES.xml", "sitemap_vs_ca_ES.xml",
        "sitemap_seasonal_ca_ES.xml", "sitemap_reviews_ca_ES.xml",
        # eu-ES:
        "sitemap_bestfor_eu_ES.xml", "sitemap_workflow_eu_ES.xml", "sitemap_vs_eu_ES.xml",
        "sitemap_seasonal_eu_ES.xml", "sitemap_reviews_eu_ES.xml",
        # gl-ES:
        "sitemap_bestfor_gl_ES.xml", "sitemap_workflow_gl_ES.xml", "sitemap_vs_gl_ES.xml",
        "sitemap_seasonal_gl_ES.xml", "sitemap_reviews_gl_ES.xml",
        # or-IN:
        "sitemap_bestfor_or_IN.xml", "sitemap_workflow_or_IN.xml", "sitemap_vs_or_IN.xml",
        "sitemap_seasonal_or_IN.xml", "sitemap_reviews_or_IN.xml",
        # pa-IN:
        "sitemap_bestfor_pa_IN.xml", "sitemap_workflow_pa_IN.xml", "sitemap_vs_pa_IN.xml",
        "sitemap_seasonal_pa_IN.xml", "sitemap_reviews_pa_IN.xml",
        # as-IN:
        "sitemap_bestfor_as_IN.xml", "sitemap_workflow_as_IN.xml", "sitemap_vs_as_IN.xml",
        "sitemap_seasonal_as_IN.xml", "sitemap_reviews_as_IN.xml",
        # ps-AF:
        "sitemap_bestfor_ps_AF.xml", "sitemap_workflow_ps_AF.xml", "sitemap_vs_ps_AF.xml",
        "sitemap_seasonal_ps_AF.xml", "sitemap_reviews_ps_AF.xml",
        # sd-PK:
        "sitemap_bestfor_sd_PK.xml", "sitemap_workflow_sd_PK.xml", "sitemap_vs_sd_PK.xml",
        "sitemap_seasonal_sd_PK.xml", "sitemap_reviews_sd_PK.xml",
        # ceb-PH:
        "sitemap_bestfor_ceb_PH.xml", "sitemap_workflow_ceb_PH.xml", "sitemap_vs_ceb_PH.xml",
        "sitemap_seasonal_ceb_PH.xml", "sitemap_reviews_ceb_PH.xml",
        # wo-SN:
        "sitemap_bestfor_wo_SN.xml", "sitemap_workflow_wo_SN.xml", "sitemap_vs_wo_SN.xml",
        "sitemap_seasonal_wo_SN.xml", "sitemap_reviews_wo_SN.xml",
        # ff-SN:
        "sitemap_bestfor_ff_SN.xml", "sitemap_workflow_ff_SN.xml", "sitemap_vs_ff_SN.xml",
        "sitemap_seasonal_ff_SN.xml", "sitemap_reviews_ff_SN.xml",
        # tw-GH:
        "sitemap_bestfor_tw_GH.xml", "sitemap_workflow_tw_GH.xml", "sitemap_vs_tw_GH.xml",
        "sitemap_seasonal_tw_GH.xml", "sitemap_reviews_tw_GH.xml",
        # st-ZA:
        "sitemap_bestfor_st_ZA.xml", "sitemap_workflow_st_ZA.xml", "sitemap_vs_st_ZA.xml",
        "sitemap_seasonal_st_ZA.xml", "sitemap_reviews_st_ZA.xml",
        # lb-LU:
        "sitemap_bestfor_lb_LU.xml", "sitemap_workflow_lb_LU.xml", "sitemap_vs_lb_LU.xml",
        "sitemap_seasonal_lb_LU.xml", "sitemap_reviews_lb_LU.xml",
        # qu-PE:
        "sitemap_bestfor_qu_PE.xml", "sitemap_workflow_qu_PE.xml", "sitemap_vs_qu_PE.xml",
        "sitemap_seasonal_qu_PE.xml", "sitemap_reviews_qu_PE.xml",
        # ht-HT:
        "sitemap_bestfor_ht_HT.xml", "sitemap_workflow_ht_HT.xml", "sitemap_vs_ht_HT.xml",
        "sitemap_seasonal_ht_HT.xml", "sitemap_reviews_ht_HT.xml",
        # mg-MG:
        "sitemap_bestfor_mg_MG.xml", "sitemap_workflow_mg_MG.xml", "sitemap_vs_mg_MG.xml",
        "sitemap_seasonal_mg_MG.xml", "sitemap_reviews_mg_MG.xml",
        # gn-PY:
        "sitemap_bestfor_gn_PY.xml", "sitemap_workflow_gn_PY.xml", "sitemap_vs_gn_PY.xml",
        "sitemap_seasonal_gn_PY.xml", "sitemap_reviews_gn_PY.xml",
        # tt-RU:
        "sitemap_bestfor_tt_RU.xml", "sitemap_workflow_tt_RU.xml", "sitemap_vs_tt_RU.xml",
        "sitemap_seasonal_tt_RU.xml", "sitemap_reviews_tt_RU.xml",
        # ay-BO:
        "sitemap_bestfor_ay_BO.xml", "sitemap_workflow_ay_BO.xml", "sitemap_vs_ay_BO.xml",
        "sitemap_seasonal_ay_BO.xml", "sitemap_reviews_ay_BO.xml",
        # bo-CN:
        "sitemap_bestfor_bo_CN.xml", "sitemap_workflow_bo_CN.xml", "sitemap_vs_bo_CN.xml",
        "sitemap_seasonal_bo_CN.xml", "sitemap_reviews_bo_CN.xml",
        # dz-BT:
        "sitemap_bestfor_dz_BT.xml", "sitemap_workflow_dz_BT.xml", "sitemap_vs_dz_BT.xml",
        "sitemap_seasonal_dz_BT.xml", "sitemap_reviews_dz_BT.xml",
        # sm-WS:
        "sitemap_bestfor_sm_WS.xml", "sitemap_workflow_sm_WS.xml", "sitemap_vs_sm_WS.xml",
        "sitemap_seasonal_sm_WS.xml", "sitemap_reviews_sm_WS.xml",
        # to-TO:
        "sitemap_bestfor_to_TO.xml", "sitemap_workflow_to_TO.xml", "sitemap_vs_to_TO.xml",
        "sitemap_seasonal_to_TO.xml", "sitemap_reviews_to_TO.xml",
        # jv-ID:
        "sitemap_bestfor_jv_ID.xml", "sitemap_workflow_jv_ID.xml", "sitemap_vs_jv_ID.xml",
        "sitemap_seasonal_jv_ID.xml", "sitemap_reviews_jv_ID.xml",
        # su-ID:
        "sitemap_bestfor_su_ID.xml", "sitemap_workflow_su_ID.xml", "sitemap_vs_su_ID.xml",
        "sitemap_seasonal_su_ID.xml", "sitemap_reviews_su_ID.xml",
        # mi-NZ:
        "sitemap_bestfor_mi_NZ.xml", "sitemap_workflow_mi_NZ.xml", "sitemap_vs_mi_NZ.xml",
        "sitemap_seasonal_mi_NZ.xml", "sitemap_reviews_mi_NZ.xml",
        # fj-FJ:
        "sitemap_bestfor_fj_FJ.xml", "sitemap_workflow_fj_FJ.xml", "sitemap_vs_fj_FJ.xml",
        "sitemap_seasonal_fj_FJ.xml", "sitemap_reviews_fj_FJ.xml",
        # ba-RU:
        "sitemap_bestfor_ba_RU.xml", "sitemap_workflow_ba_RU.xml", "sitemap_vs_ba_RU.xml",
        "sitemap_seasonal_ba_RU.xml", "sitemap_reviews_ba_RU.xml",
        # ug-CN kab-DZ sc-IT br-FR cv-RU:
        "sitemap_bestfor_ug_CN.xml", "sitemap_workflow_ug_CN.xml", "sitemap_vs_ug_CN.xml",
        "sitemap_seasonal_ug_CN.xml", "sitemap_reviews_ug_CN.xml",
        "sitemap_bestfor_kab_DZ.xml", "sitemap_workflow_kab_DZ.xml", "sitemap_vs_kab_DZ.xml",
        "sitemap_seasonal_kab_DZ.xml", "sitemap_reviews_kab_DZ.xml",
        "sitemap_bestfor_sc_IT.xml", "sitemap_workflow_sc_IT.xml", "sitemap_vs_sc_IT.xml",
        "sitemap_seasonal_sc_IT.xml", "sitemap_reviews_sc_IT.xml",
        "sitemap_bestfor_br_FR.xml", "sitemap_workflow_br_FR.xml", "sitemap_vs_br_FR.xml",
        "sitemap_seasonal_br_FR.xml", "sitemap_reviews_br_FR.xml",
        "sitemap_bestfor_cv_RU.xml", "sitemap_workflow_cv_RU.xml", "sitemap_vs_cv_RU.xml",
        "sitemap_seasonal_cv_RU.xml", "sitemap_reviews_cv_RU.xml",
        # tn-ZA ve-ZA ss-SZ mad-ID min-ID:
        "sitemap_bestfor_tn_ZA.xml", "sitemap_workflow_tn_ZA.xml", "sitemap_vs_tn_ZA.xml",
        "sitemap_seasonal_tn_ZA.xml", "sitemap_reviews_tn_ZA.xml",
        "sitemap_bestfor_ve_ZA.xml", "sitemap_workflow_ve_ZA.xml", "sitemap_vs_ve_ZA.xml",
        "sitemap_seasonal_ve_ZA.xml", "sitemap_reviews_ve_ZA.xml",
        "sitemap_bestfor_ss_SZ.xml", "sitemap_workflow_ss_SZ.xml", "sitemap_vs_ss_SZ.xml",
        "sitemap_seasonal_ss_SZ.xml", "sitemap_reviews_ss_SZ.xml",
        "sitemap_bestfor_mad_ID.xml", "sitemap_workflow_mad_ID.xml", "sitemap_vs_mad_ID.xml",
        "sitemap_seasonal_mad_ID.xml", "sitemap_reviews_mad_ID.xml",
        "sitemap_bestfor_min_ID.xml", "sitemap_workflow_min_ID.xml", "sitemap_vs_min_ID.xml",
        "sitemap_seasonal_min_ID.xml", "sitemap_reviews_min_ID.xml",
        # bho mai-IN sat-IN gom-IN ks-IN:
        "sitemap_bestfor_bho.xml", "sitemap_workflow_bho.xml", "sitemap_vs_bho.xml",
        "sitemap_seasonal_bho.xml", "sitemap_reviews_bho.xml",
        "sitemap_bestfor_mai_IN.xml", "sitemap_workflow_mai_IN.xml", "sitemap_vs_mai_IN.xml",
        "sitemap_seasonal_mai_IN.xml", "sitemap_reviews_mai_IN.xml",
        "sitemap_bestfor_sat_IN.xml", "sitemap_workflow_sat_IN.xml", "sitemap_vs_sat_IN.xml",
        "sitemap_seasonal_sat_IN.xml", "sitemap_reviews_sat_IN.xml",
        "sitemap_bestfor_gom_IN.xml", "sitemap_workflow_gom_IN.xml", "sitemap_vs_gom_IN.xml",
        "sitemap_seasonal_gom_IN.xml", "sitemap_reviews_gom_IN.xml",
        "sitemap_bestfor_ks_IN.xml", "sitemap_workflow_ks_IN.xml", "sitemap_vs_ks_IN.xml",
        "sitemap_seasonal_ks_IN.xml", "sitemap_reviews_ks_IN.xml",
        # nap vec-IT lmo bug-ID sah-RU:
        "sitemap_bestfor_nap.xml", "sitemap_workflow_nap.xml", "sitemap_vs_nap.xml",
        "sitemap_seasonal_nap.xml", "sitemap_reviews_nap.xml",
        "sitemap_bestfor_vec_IT.xml", "sitemap_workflow_vec_IT.xml", "sitemap_vs_vec_IT.xml",
        "sitemap_seasonal_vec_IT.xml", "sitemap_reviews_vec_IT.xml",
        "sitemap_bestfor_lmo.xml", "sitemap_workflow_lmo.xml", "sitemap_vs_lmo.xml",
        "sitemap_seasonal_lmo.xml", "sitemap_reviews_lmo.xml",
        "sitemap_bestfor_bug_ID.xml", "sitemap_workflow_bug_ID.xml", "sitemap_vs_bug_ID.xml",
        "sitemap_seasonal_bug_ID.xml", "sitemap_reviews_bug_ID.xml",
        "sitemap_bestfor_sah_RU.xml", "sitemap_workflow_sah_RU.xml", "sitemap_vs_sah_RU.xml",
        "sitemap_seasonal_sah_RU.xml", "sitemap_reviews_sah_RU.xml",
        # awa bgc dgo-IN os-RU che-RU:
        "sitemap_bestfor_awa.xml", "sitemap_workflow_awa.xml", "sitemap_vs_awa.xml",
        "sitemap_seasonal_awa.xml", "sitemap_reviews_awa.xml",
        "sitemap_bestfor_bgc.xml", "sitemap_workflow_bgc.xml", "sitemap_vs_bgc.xml",
        "sitemap_seasonal_bgc.xml", "sitemap_reviews_bgc.xml",
        "sitemap_bestfor_dgo_IN.xml", "sitemap_workflow_dgo_IN.xml", "sitemap_vs_dgo_IN.xml",
        "sitemap_seasonal_dgo_IN.xml", "sitemap_reviews_dgo_IN.xml",
        "sitemap_bestfor_os_RU.xml", "sitemap_workflow_os_RU.xml", "sitemap_vs_os_RU.xml",
        "sitemap_seasonal_os_RU.xml", "sitemap_reviews_os_RU.xml",
        "sitemap_bestfor_che_RU.xml", "sitemap_workflow_che_RU.xml", "sitemap_vs_che_RU.xml",
        "sitemap_seasonal_che_RU.xml", "sitemap_reviews_che_RU.xml",
        # ban-ID ace-ID hne mag new-NP:
        "sitemap_bestfor_ban_ID.xml", "sitemap_workflow_ban_ID.xml", "sitemap_vs_ban_ID.xml",
        "sitemap_seasonal_ban_ID.xml", "sitemap_reviews_ban_ID.xml",
        "sitemap_bestfor_ace_ID.xml", "sitemap_workflow_ace_ID.xml", "sitemap_vs_ace_ID.xml",
        "sitemap_seasonal_ace_ID.xml", "sitemap_reviews_ace_ID.xml",
        "sitemap_bestfor_hne.xml", "sitemap_workflow_hne.xml", "sitemap_vs_hne.xml",
        "sitemap_seasonal_hne.xml", "sitemap_reviews_hne.xml",
        "sitemap_bestfor_mag.xml", "sitemap_workflow_mag.xml", "sitemap_vs_mag.xml",
        "sitemap_seasonal_mag.xml", "sitemap_reviews_mag.xml",
        "sitemap_bestfor_new_NP.xml", "sitemap_workflow_new_NP.xml", "sitemap_vs_new_NP.xml",
        "sitemap_seasonal_new_NP.xml", "sitemap_reviews_new_NP.xml",
        # mnw-MM shn-MM zgh-MA fur-IT oc-FR:
        "sitemap_bestfor_mnw_MM.xml", "sitemap_workflow_mnw_MM.xml", "sitemap_vs_mnw_MM.xml",
        "sitemap_seasonal_mnw_MM.xml", "sitemap_reviews_mnw_MM.xml",
        "sitemap_bestfor_shn_MM.xml", "sitemap_workflow_shn_MM.xml", "sitemap_vs_shn_MM.xml",
        "sitemap_seasonal_shn_MM.xml", "sitemap_reviews_shn_MM.xml",
        "sitemap_bestfor_zgh_MA.xml", "sitemap_workflow_zgh_MA.xml", "sitemap_vs_zgh_MA.xml",
        "sitemap_seasonal_zgh_MA.xml", "sitemap_reviews_zgh_MA.xml",
        "sitemap_bestfor_fur_IT.xml", "sitemap_workflow_fur_IT.xml", "sitemap_vs_fur_IT.xml",
        "sitemap_seasonal_fur_IT.xml", "sitemap_reviews_fur_IT.xml",
        "sitemap_bestfor_oc_FR.xml", "sitemap_workflow_oc_FR.xml", "sitemap_vs_oc_FR.xml",
        "sitemap_seasonal_oc_FR.xml", "sitemap_reviews_oc_FR.xml",
        # lij rm-CH co-FR scn-IT wa-BE:
        "sitemap_bestfor_lij.xml", "sitemap_workflow_lij.xml", "sitemap_vs_lij.xml",
        "sitemap_seasonal_lij.xml", "sitemap_reviews_lij.xml",
        "sitemap_bestfor_rm_CH.xml", "sitemap_workflow_rm_CH.xml", "sitemap_vs_rm_CH.xml",
        "sitemap_seasonal_rm_CH.xml", "sitemap_reviews_rm_CH.xml",
        "sitemap_bestfor_co_FR.xml", "sitemap_workflow_co_FR.xml", "sitemap_vs_co_FR.xml",
        "sitemap_seasonal_co_FR.xml", "sitemap_reviews_co_FR.xml",
        "sitemap_bestfor_scn_IT.xml", "sitemap_workflow_scn_IT.xml", "sitemap_vs_scn_IT.xml",
        "sitemap_seasonal_scn_IT.xml", "sitemap_reviews_scn_IT.xml",
        "sitemap_bestfor_wa_BE.xml", "sitemap_workflow_wa_BE.xml", "sitemap_vs_wa_BE.xml",
        "sitemap_seasonal_wa_BE.xml", "sitemap_reviews_wa_BE.xml",
        # pam-PH ilo-PH war-PH bcl-PH pag-PH:
        "sitemap_bestfor_pam_PH.xml", "sitemap_workflow_pam_PH.xml", "sitemap_vs_pam_PH.xml",
        "sitemap_seasonal_pam_PH.xml", "sitemap_reviews_pam_PH.xml",
        "sitemap_bestfor_ilo_PH.xml", "sitemap_workflow_ilo_PH.xml", "sitemap_vs_ilo_PH.xml",
        "sitemap_seasonal_ilo_PH.xml", "sitemap_reviews_ilo_PH.xml",
        "sitemap_bestfor_war_PH.xml", "sitemap_workflow_war_PH.xml", "sitemap_vs_war_PH.xml",
        "sitemap_seasonal_war_PH.xml", "sitemap_reviews_war_PH.xml",
        "sitemap_bestfor_bcl_PH.xml", "sitemap_workflow_bcl_PH.xml", "sitemap_vs_bcl_PH.xml",
        "sitemap_seasonal_bcl_PH.xml", "sitemap_reviews_bcl_PH.xml",
        "sitemap_bestfor_pag_PH.xml", "sitemap_workflow_pag_PH.xml", "sitemap_vs_pag_PH.xml",
        "sitemap_seasonal_pag_PH.xml", "sitemap_reviews_pag_PH.xml",
        # lua-CD mhr myv udm koi:
        "sitemap_bestfor_lua_CD.xml", "sitemap_workflow_lua_CD.xml", "sitemap_vs_lua_CD.xml",
        "sitemap_seasonal_lua_CD.xml", "sitemap_reviews_lua_CD.xml",
        "sitemap_bestfor_mhr.xml", "sitemap_workflow_mhr.xml", "sitemap_vs_mhr.xml",
        "sitemap_seasonal_mhr.xml", "sitemap_reviews_mhr.xml",
        "sitemap_bestfor_myv.xml", "sitemap_workflow_myv.xml", "sitemap_vs_myv.xml",
        "sitemap_seasonal_myv.xml", "sitemap_reviews_myv.xml",
        "sitemap_bestfor_udm.xml", "sitemap_workflow_udm.xml", "sitemap_vs_udm.xml",
        "sitemap_seasonal_udm.xml", "sitemap_reviews_udm.xml",
        "sitemap_bestfor_koi.xml", "sitemap_workflow_koi.xml", "sitemap_vs_koi.xml",
        "sitemap_seasonal_koi.xml", "sitemap_reviews_koi.xml",
        "sitemap_bestfor_bjn_ID.xml", "sitemap_workflow_bjn_ID.xml", "sitemap_vs_bjn_ID.xml",
        "sitemap_seasonal_bjn_ID.xml", "sitemap_reviews_bjn_ID.xml",
        "sitemap_bestfor_mak_ID.xml", "sitemap_workflow_mak_ID.xml", "sitemap_vs_mak_ID.xml",
        "sitemap_seasonal_mak_ID.xml", "sitemap_reviews_mak_ID.xml",
        "sitemap_bestfor_brx_IN.xml", "sitemap_workflow_brx_IN.xml", "sitemap_vs_brx_IN.xml",
        "sitemap_seasonal_brx_IN.xml", "sitemap_reviews_brx_IN.xml",
        "sitemap_bestfor_mni_IN.xml", "sitemap_workflow_mni_IN.xml", "sitemap_vs_mni_IN.xml",
        "sitemap_seasonal_mni_IN.xml", "sitemap_reviews_mni_IN.xml",
        "sitemap_bestfor_bm_ML.xml", "sitemap_workflow_bm_ML.xml", "sitemap_vs_bm_ML.xml",
        "sitemap_seasonal_bm_ML.xml", "sitemap_reviews_bm_ML.xml",
        "sitemap_bestfor_ewe_GH.xml", "sitemap_workflow_ewe_GH.xml", "sitemap_vs_ewe_GH.xml",
        "sitemap_seasonal_ewe_GH.xml", "sitemap_reviews_ewe_GH.xml",
        "sitemap_bestfor_twi_GH.xml", "sitemap_workflow_twi_GH.xml", "sitemap_vs_twi_GH.xml",
        "sitemap_seasonal_twi_GH.xml", "sitemap_reviews_twi_GH.xml",
        "sitemap_bestfor_dyu_CI.xml", "sitemap_workflow_dyu_CI.xml", "sitemap_vs_dyu_CI.xml",
        "sitemap_seasonal_dyu_CI.xml", "sitemap_reviews_dyu_CI.xml",
        "sitemap_bestfor_tcy.xml", "sitemap_workflow_tcy.xml", "sitemap_vs_tcy.xml",
        "sitemap_seasonal_tcy.xml", "sitemap_reviews_tcy.xml",
        "sitemap_bestfor_gag_MD.xml", "sitemap_workflow_gag_MD.xml", "sitemap_vs_gag_MD.xml",
        "sitemap_seasonal_gag_MD.xml", "sitemap_reviews_gag_MD.xml",
        "sitemap_bestfor_nso_ZA.xml", "sitemap_workflow_nso_ZA.xml", "sitemap_vs_nso_ZA.xml",
        "sitemap_seasonal_nso_ZA.xml", "sitemap_reviews_nso_ZA.xml",
        "sitemap_bestfor_ts_ZA.xml", "sitemap_workflow_ts_ZA.xml", "sitemap_vs_ts_ZA.xml",
        "sitemap_seasonal_ts_ZA.xml", "sitemap_reviews_ts_ZA.xml",
        "sitemap_bestfor_nr_ZA.xml", "sitemap_workflow_nr_ZA.xml", "sitemap_vs_nr_ZA.xml",
        "sitemap_seasonal_nr_ZA.xml", "sitemap_reviews_nr_ZA.xml",
        "sitemap_bestfor_pap.xml", "sitemap_workflow_pap.xml", "sitemap_vs_pap.xml",
        "sitemap_seasonal_pap.xml", "sitemap_reviews_pap.xml",
        "sitemap_bestfor_krl.xml", "sitemap_workflow_krl.xml", "sitemap_vs_krl.xml",
        "sitemap_seasonal_krl.xml", "sitemap_reviews_krl.xml",
        "sitemap_bestfor_srn.xml", "sitemap_workflow_srn.xml", "sitemap_vs_srn.xml",
        "sitemap_seasonal_srn.xml", "sitemap_reviews_srn.xml",
        "sitemap_bestfor_gcr.xml", "sitemap_workflow_gcr.xml", "sitemap_vs_gcr.xml",
        "sitemap_seasonal_gcr.xml", "sitemap_reviews_gcr.xml",
        "sitemap_bestfor_kea.xml", "sitemap_workflow_kea.xml", "sitemap_vs_kea.xml",
        "sitemap_seasonal_kea.xml", "sitemap_reviews_kea.xml",
        "sitemap_bestfor_mfe.xml", "sitemap_workflow_mfe.xml", "sitemap_vs_mfe.xml",
        "sitemap_seasonal_mfe.xml", "sitemap_reviews_mfe.xml",
        "sitemap_bestfor_hat.xml", "sitemap_workflow_hat.xml", "sitemap_vs_hat.xml",
        "sitemap_seasonal_hat.xml", "sitemap_reviews_hat.xml",
        "sitemap_bestfor_luo_KE.xml", "sitemap_workflow_luo_KE.xml", "sitemap_vs_luo_KE.xml",
        "sitemap_seasonal_luo_KE.xml", "sitemap_reviews_luo_KE.xml",
        "sitemap_bestfor_kam_KE.xml", "sitemap_workflow_kam_KE.xml", "sitemap_vs_kam_KE.xml",
        "sitemap_seasonal_kam_KE.xml", "sitemap_reviews_kam_KE.xml",
        "sitemap_bestfor_kln_KE.xml", "sitemap_workflow_kln_KE.xml", "sitemap_vs_kln_KE.xml",
        "sitemap_seasonal_kln_KE.xml", "sitemap_reviews_kln_KE.xml",
        "sitemap_bestfor_nyn_UG.xml", "sitemap_workflow_nyn_UG.xml", "sitemap_vs_nyn_UG.xml",
        "sitemap_seasonal_nyn_UG.xml", "sitemap_reviews_nyn_UG.xml",
        "sitemap_bestfor_swc_CD.xml", "sitemap_workflow_swc_CD.xml", "sitemap_vs_swc_CD.xml",
        "sitemap_seasonal_swc_CD.xml", "sitemap_reviews_swc_CD.xml",
        "sitemap_bestfor_wuu.xml", "sitemap_workflow_wuu.xml", "sitemap_vs_wuu.xml",
        "sitemap_seasonal_wuu.xml", "sitemap_reviews_wuu.xml",
        "sitemap_bestfor_gan.xml", "sitemap_workflow_gan.xml", "sitemap_vs_gan.xml",
        "sitemap_seasonal_gan.xml", "sitemap_reviews_gan.xml",
        "sitemap_bestfor_hsn.xml", "sitemap_workflow_hsn.xml", "sitemap_vs_hsn.xml",
        "sitemap_seasonal_hsn.xml", "sitemap_reviews_hsn.xml",
        "sitemap_bestfor_cdo.xml", "sitemap_workflow_cdo.xml", "sitemap_vs_cdo.xml",
        "sitemap_seasonal_cdo.xml", "sitemap_reviews_cdo.xml",
        "sitemap_bestfor_tet.xml", "sitemap_workflow_tet.xml", "sitemap_vs_tet.xml",
        "sitemap_seasonal_tet.xml", "sitemap_reviews_tet.xml",
        "sitemap_bestfor_bci.xml", "sitemap_workflow_bci.xml", "sitemap_vs_bci.xml",
        "sitemap_seasonal_bci.xml", "sitemap_reviews_bci.xml",
        "sitemap_bestfor_dag.xml", "sitemap_workflow_dag.xml", "sitemap_vs_dag.xml",
        "sitemap_seasonal_dag.xml", "sitemap_reviews_dag.xml",
        "sitemap_bestfor_gor_ID.xml", "sitemap_workflow_gor_ID.xml", "sitemap_vs_gor_ID.xml",
        "sitemap_seasonal_gor_ID.xml", "sitemap_reviews_gor_ID.xml",
        "sitemap_bestfor_maz.xml", "sitemap_workflow_maz.xml", "sitemap_vs_maz.xml",
        "sitemap_seasonal_maz.xml", "sitemap_reviews_maz.xml",
        "sitemap_bestfor_tzh.xml", "sitemap_workflow_tzh.xml", "sitemap_vs_tzh.xml",
        "sitemap_seasonal_tzh.xml", "sitemap_reviews_tzh.xml",
        "sitemap_bestfor_nym_TZ.xml", "sitemap_workflow_nym_TZ.xml", "sitemap_vs_nym_TZ.xml",
        "sitemap_seasonal_nym_TZ.xml", "sitemap_reviews_nym_TZ.xml",
        "sitemap_bestfor_suk.xml", "sitemap_workflow_suk.xml", "sitemap_vs_suk.xml",
        "sitemap_seasonal_suk.xml", "sitemap_reviews_suk.xml",
        "sitemap_bestfor_guz_KE.xml", "sitemap_workflow_guz_KE.xml", "sitemap_vs_guz_KE.xml",
        "sitemap_seasonal_guz_KE.xml", "sitemap_reviews_guz_KE.xml",
        "sitemap_bestfor_mer_KE.xml", "sitemap_workflow_mer_KE.xml", "sitemap_vs_mer_KE.xml",
        "sitemap_seasonal_mer_KE.xml", "sitemap_reviews_mer_KE.xml",
        "sitemap_bestfor_cgg_UG.xml", "sitemap_workflow_cgg_UG.xml", "sitemap_vs_cgg_UG.xml",
        "sitemap_seasonal_cgg_UG.xml", "sitemap_reviews_cgg_UG.xml",
        "sitemap_bestfor_xog_UG.xml", "sitemap_workflow_xog_UG.xml", "sitemap_vs_xog_UG.xml",
        "sitemap_seasonal_xog_UG.xml", "sitemap_reviews_xog_UG.xml",
        "sitemap_bestfor_ach_UG.xml", "sitemap_workflow_ach_UG.xml", "sitemap_vs_ach_UG.xml",
        "sitemap_seasonal_ach_UG.xml", "sitemap_reviews_ach_UG.xml",
        "sitemap_bestfor_teo_UG.xml", "sitemap_workflow_teo_UG.xml", "sitemap_vs_teo_UG.xml",
        "sitemap_seasonal_teo_UG.xml", "sitemap_reviews_teo_UG.xml",
        "sitemap_bestfor_mas_KE.xml", "sitemap_workflow_mas_KE.xml", "sitemap_vs_mas_KE.xml",
        "sitemap_seasonal_mas_KE.xml", "sitemap_reviews_mas_KE.xml",
        "sitemap_bestfor_nus_SS.xml", "sitemap_workflow_nus_SS.xml", "sitemap_vs_nus_SS.xml",
        "sitemap_seasonal_nus_SS.xml", "sitemap_reviews_nus_SS.xml",
        "sitemap_bestfor_bej.xml", "sitemap_workflow_bej.xml", "sitemap_vs_bej.xml",
        "sitemap_seasonal_bej.xml", "sitemap_reviews_bej.xml",
        "sitemap_bestfor_din.xml", "sitemap_workflow_din.xml", "sitemap_vs_din.xml",
        "sitemap_seasonal_din.xml", "sitemap_reviews_din.xml",
        "sitemap_bestfor_fij.xml", "sitemap_workflow_fij.xml", "sitemap_vs_fij.xml",
        "sitemap_seasonal_fij.xml", "sitemap_reviews_fij.xml",
        "sitemap_bestfor_sah.xml", "sitemap_workflow_sah.xml", "sitemap_vs_sah.xml",
        "sitemap_seasonal_sah.xml", "sitemap_reviews_sah.xml",
        "sitemap_bestfor_kaa.xml", "sitemap_workflow_kaa.xml", "sitemap_vs_kaa.xml",
        "sitemap_seasonal_kaa.xml", "sitemap_reviews_kaa.xml",
        "sitemap_bestfor_sm.xml", "sitemap_workflow_sm.xml", "sitemap_vs_sm.xml",
        "sitemap_seasonal_sm.xml", "sitemap_reviews_sm.xml",
        "sitemap_bestfor_to.xml", "sitemap_workflow_to.xml", "sitemap_vs_to.xml",
        "sitemap_seasonal_to.xml", "sitemap_reviews_to.xml",
        "sitemap_bestfor_ty.xml", "sitemap_workflow_ty.xml", "sitemap_vs_ty.xml",
        "sitemap_seasonal_ty.xml", "sitemap_reviews_ty.xml",
        "sitemap_bestfor_yua.xml", "sitemap_workflow_yua.xml", "sitemap_vs_yua.xml",
        "sitemap_seasonal_yua.xml", "sitemap_reviews_yua.xml",
        "sitemap_bestfor_che.xml", "sitemap_workflow_che.xml", "sitemap_vs_che.xml",
        "sitemap_seasonal_che.xml", "sitemap_reviews_che.xml",
        "sitemap_bestfor_bua.xml", "sitemap_workflow_bua.xml", "sitemap_vs_bua.xml",
        "sitemap_seasonal_bua.xml", "sitemap_reviews_bua.xml",
        "sitemap_bestfor_tyv.xml", "sitemap_workflow_tyv.xml", "sitemap_vs_tyv.xml",
        "sitemap_seasonal_tyv.xml", "sitemap_reviews_tyv.xml",
        "sitemap_bestfor_inh.xml", "sitemap_workflow_inh.xml", "sitemap_vs_inh.xml",
        "sitemap_seasonal_inh.xml", "sitemap_reviews_inh.xml",
        "sitemap_bestfor_av.xml", "sitemap_workflow_av.xml", "sitemap_vs_av.xml",
        "sitemap_seasonal_av.xml", "sitemap_reviews_av.xml",
        "sitemap_bestfor_nah.xml", "sitemap_workflow_nah.xml", "sitemap_vs_nah.xml",
        "sitemap_seasonal_nah.xml", "sitemap_reviews_nah.xml",
        "sitemap_bestfor_mh.xml", "sitemap_workflow_mh.xml", "sitemap_vs_mh.xml",
        "sitemap_seasonal_mh.xml", "sitemap_reviews_mh.xml",
        "sitemap_bestfor_pau.xml", "sitemap_workflow_pau.xml", "sitemap_vs_pau.xml",
        "sitemap_seasonal_pau.xml", "sitemap_reviews_pau.xml",
        "sitemap_bestfor_chk.xml", "sitemap_workflow_chk.xml", "sitemap_vs_chk.xml",
        "sitemap_seasonal_chk.xml", "sitemap_reviews_chk.xml",
        "sitemap_bestfor_pon.xml", "sitemap_workflow_pon.xml", "sitemap_vs_pon.xml",
        "sitemap_seasonal_pon.xml", "sitemap_reviews_pon.xml",
        "sitemap_bestfor_cos.xml", "sitemap_workflow_cos.xml", "sitemap_vs_cos.xml",
        "sitemap_seasonal_cos.xml", "sitemap_reviews_cos.xml",
        "sitemap_bestfor_sc.xml", "sitemap_workflow_sc.xml", "sitemap_vs_sc.xml",
        "sitemap_seasonal_sc.xml", "sitemap_reviews_sc.xml",
        "sitemap_bestfor_vec.xml", "sitemap_workflow_vec.xml", "sitemap_vs_vec.xml",
        "sitemap_seasonal_vec.xml", "sitemap_reviews_vec.xml",
        "sitemap_bestfor_scn.xml", "sitemap_workflow_scn.xml", "sitemap_vs_scn.xml",
        "sitemap_seasonal_scn.xml", "sitemap_reviews_scn.xml",
        "sitemap_bestfor_fur.xml", "sitemap_workflow_fur.xml", "sitemap_vs_fur.xml",
        "sitemap_seasonal_fur.xml", "sitemap_reviews_fur.xml",
        "sitemap_bestfor_lij.xml", "sitemap_workflow_lij.xml", "sitemap_vs_lij.xml",
        "sitemap_seasonal_lij.xml", "sitemap_reviews_lij.xml",
        "sitemap_bestfor_nap.xml", "sitemap_workflow_nap.xml", "sitemap_vs_nap.xml",
        "sitemap_seasonal_nap.xml", "sitemap_reviews_nap.xml",
        "sitemap_bestfor_pms.xml", "sitemap_workflow_pms.xml", "sitemap_vs_pms.xml",
        "sitemap_seasonal_pms.xml", "sitemap_reviews_pms.xml",
        "sitemap_bestfor_rup.xml", "sitemap_workflow_rup.xml", "sitemap_vs_rup.xml",
        "sitemap_seasonal_rup.xml", "sitemap_reviews_rup.xml",
        "sitemap_bestfor_nds.xml", "sitemap_workflow_nds.xml", "sitemap_vs_nds.xml",
        "sitemap_seasonal_nds.xml", "sitemap_reviews_nds.xml",
        "sitemap_bestfor_zza.xml", "sitemap_workflow_zza.xml", "sitemap_vs_zza.xml",
        "sitemap_seasonal_zza.xml", "sitemap_reviews_zza.xml",
        "sitemap_bestfor_gsw.xml", "sitemap_workflow_gsw.xml", "sitemap_vs_gsw.xml",
        "sitemap_seasonal_gsw.xml", "sitemap_reviews_gsw.xml",
        "sitemap_bestfor_lb.xml", "sitemap_workflow_lb.xml", "sitemap_vs_lb.xml",
        "sitemap_seasonal_lb.xml", "sitemap_reviews_lb.xml",
        "sitemap_bestfor_wln.xml", "sitemap_workflow_wln.xml", "sitemap_vs_wln.xml",
        "sitemap_seasonal_wln.xml", "sitemap_reviews_wln.xml",
        "sitemap_bestfor_rmy.xml", "sitemap_workflow_rmy.xml", "sitemap_vs_rmy.xml",
        "sitemap_seasonal_rmy.xml", "sitemap_reviews_rmy.xml",
        "sitemap_bestfor_oc.xml", "sitemap_workflow_oc.xml", "sitemap_vs_oc.xml",
        "sitemap_seasonal_oc.xml", "sitemap_reviews_oc.xml",
        "sitemap_bestfor_cre.xml", "sitemap_workflow_cre.xml", "sitemap_vs_cre.xml",
        "sitemap_seasonal_cre.xml", "sitemap_reviews_cre.xml",
        "sitemap_bestfor_oji.xml", "sitemap_workflow_oji.xml", "sitemap_vs_oji.xml",
        "sitemap_seasonal_oji.xml", "sitemap_reviews_oji.xml",
        "sitemap_bestfor_iku.xml", "sitemap_workflow_iku.xml", "sitemap_vs_iku.xml",
        "sitemap_seasonal_iku.xml", "sitemap_reviews_iku.xml",
        "sitemap_bestfor_ndc_ZW.xml", "sitemap_workflow_ndc_ZW.xml", "sitemap_vs_ndc_ZW.xml",
        "sitemap_seasonal_ndc_ZW.xml", "sitemap_reviews_ndc_ZW.xml",
        "sitemap_bestfor_sus.xml", "sitemap_workflow_sus.xml", "sitemap_vs_sus.xml",
        "sitemap_seasonal_sus.xml", "sitemap_reviews_sus.xml",
        "sitemap_bestfor_shn.xml", "sitemap_workflow_shn.xml", "sitemap_vs_shn.xml",
        "sitemap_seasonal_shn.xml", "sitemap_reviews_shn.xml",
        "sitemap_bestfor_kac.xml", "sitemap_workflow_kac.xml", "sitemap_vs_kac.xml",
        "sitemap_seasonal_kac.xml", "sitemap_reviews_kac.xml",
        "sitemap_bestfor_tem.xml", "sitemap_workflow_tem.xml", "sitemap_vs_tem.xml",
        "sitemap_seasonal_tem.xml", "sitemap_reviews_tem.xml",
        "sitemap_bestfor_tum.xml", "sitemap_workflow_tum.xml", "sitemap_vs_tum.xml",
        "sitemap_seasonal_tum.xml", "sitemap_reviews_tum.xml",
        "sitemap_bestfor_seh.xml", "sitemap_workflow_seh.xml", "sitemap_vs_seh.xml",
        "sitemap_seasonal_seh.xml", "sitemap_reviews_seh.xml",
        "sitemap_bestfor_new.xml", "sitemap_workflow_new.xml", "sitemap_vs_new.xml",
        "sitemap_seasonal_new.xml", "sitemap_reviews_new.xml",
        "sitemap_bestfor_lez.xml", "sitemap_workflow_lez.xml", "sitemap_vs_lez.xml",
        "sitemap_seasonal_lez.xml", "sitemap_reviews_lez.xml",
        "sitemap_bestfor_dar.xml", "sitemap_workflow_dar.xml", "sitemap_vs_dar.xml",
        "sitemap_seasonal_dar.xml", "sitemap_reviews_dar.xml",
        "sitemap_bestfor_kpe.xml", "sitemap_workflow_kpe.xml", "sitemap_vs_kpe.xml",
        "sitemap_seasonal_kpe.xml", "sitemap_reviews_kpe.xml",
        "sitemap_bestfor_tiv.xml", "sitemap_workflow_tiv.xml", "sitemap_vs_tiv.xml",
        "sitemap_seasonal_tiv.xml", "sitemap_reviews_tiv.xml",
        "sitemap_bestfor_edo.xml", "sitemap_workflow_edo.xml", "sitemap_vs_edo.xml",
        "sitemap_seasonal_edo.xml", "sitemap_reviews_edo.xml",
        "sitemap_bestfor_fon.xml", "sitemap_workflow_fon.xml", "sitemap_vs_fon.xml",
        "sitemap_seasonal_fon.xml", "sitemap_reviews_fon.xml",
        "sitemap_bestfor_luy.xml", "sitemap_workflow_luy.xml", "sitemap_vs_luy.xml",
        "sitemap_seasonal_luy.xml", "sitemap_reviews_luy.xml",
        "sitemap_bestfor_sat.xml", "sitemap_workflow_sat.xml", "sitemap_vs_sat.xml",
        "sitemap_seasonal_sat.xml", "sitemap_reviews_sat.xml",
        "sitemap_bestfor_kok.xml", "sitemap_workflow_kok.xml", "sitemap_vs_kok.xml",
        "sitemap_seasonal_kok.xml", "sitemap_reviews_kok.xml",
        "sitemap_bestfor_wol.xml", "sitemap_workflow_wol.xml", "sitemap_vs_wol.xml",
        "sitemap_seasonal_wol.xml", "sitemap_reviews_wol.xml",
        "sitemap_bestfor_ace.xml", "sitemap_workflow_ace.xml", "sitemap_vs_ace.xml",
        "sitemap_seasonal_ace.xml", "sitemap_reviews_ace.xml",
        "sitemap_bestfor_bug.xml", "sitemap_workflow_bug.xml", "sitemap_vs_bug.xml",
        "sitemap_seasonal_bug.xml", "sitemap_reviews_bug.xml",
        "sitemap_bestfor_quz.xml", "sitemap_workflow_quz.xml", "sitemap_vs_quz.xml",
        "sitemap_seasonal_quz.xml", "sitemap_reviews_quz.xml",
        "sitemap_bestfor_grn.xml", "sitemap_workflow_grn.xml", "sitemap_vs_grn.xml",
        "sitemap_seasonal_grn.xml", "sitemap_reviews_grn.xml",
        "sitemap_bestfor_ibb.xml", "sitemap_workflow_ibb.xml", "sitemap_vs_ibb.xml",
        "sitemap_seasonal_ibb.xml", "sitemap_reviews_ibb.xml",
        "sitemap_bestfor_tvl.xml", "sitemap_workflow_tvl.xml", "sitemap_vs_tvl.xml",
        "sitemap_seasonal_tvl.xml", "sitemap_reviews_tvl.xml",
        "sitemap_bestfor_chr.xml", "sitemap_workflow_chr.xml", "sitemap_vs_chr.xml",
        "sitemap_seasonal_chr.xml", "sitemap_reviews_chr.xml",
        "sitemap_bestfor_qom.xml", "sitemap_workflow_qom.xml", "sitemap_vs_qom.xml",
        "sitemap_seasonal_qom.xml", "sitemap_reviews_qom.xml",
        "sitemap_bestfor_mak.xml", "sitemap_workflow_mak.xml", "sitemap_vs_mak.xml",
        "sitemap_seasonal_mak.xml", "sitemap_reviews_mak.xml",
        "sitemap_bestfor_ewe.xml", "sitemap_workflow_ewe.xml", "sitemap_vs_ewe.xml",
        "sitemap_seasonal_ewe.xml", "sitemap_reviews_ewe.xml",
        "sitemap_bestfor_mos.xml", "sitemap_workflow_mos.xml", "sitemap_vs_mos.xml",
        "sitemap_seasonal_mos.xml", "sitemap_reviews_mos.xml",
        "sitemap_bestfor_dyu.xml", "sitemap_workflow_dyu.xml", "sitemap_vs_dyu.xml",
        "sitemap_seasonal_dyu.xml", "sitemap_reviews_dyu.xml",
        "sitemap_bestfor_aym.xml", "sitemap_workflow_aym.xml", "sitemap_vs_aym.xml",
        "sitemap_seasonal_aym.xml", "sitemap_reviews_aym.xml",
        "sitemap_bestfor_tzm.xml", "sitemap_workflow_tzm.xml", "sitemap_vs_tzm.xml",
        "sitemap_seasonal_tzm.xml", "sitemap_reviews_tzm.xml",
        "sitemap_bestfor_nso.xml", "sitemap_workflow_nso.xml", "sitemap_vs_nso.xml",
        "sitemap_seasonal_nso.xml", "sitemap_reviews_nso.xml",
        "sitemap_bestfor_pcm.xml", "sitemap_workflow_pcm.xml", "sitemap_vs_pcm.xml",
        "sitemap_seasonal_pcm.xml", "sitemap_reviews_pcm.xml",
        "sitemap_bestfor_hil.xml", "sitemap_workflow_hil.xml", "sitemap_vs_hil.xml",
        "sitemap_seasonal_hil.xml", "sitemap_reviews_hil.xml",
        "sitemap_bestfor_war.xml", "sitemap_workflow_war.xml", "sitemap_vs_war.xml",
        "sitemap_seasonal_war.xml", "sitemap_reviews_war.xml",
        "sitemap_bestfor_ilo.xml", "sitemap_workflow_ilo.xml", "sitemap_vs_ilo.xml",
        "sitemap_seasonal_ilo.xml", "sitemap_reviews_ilo.xml",
        "sitemap_bestfor_pag.xml", "sitemap_workflow_pag.xml", "sitemap_vs_pag.xml",
        "sitemap_seasonal_pag.xml", "sitemap_reviews_pag.xml",
        "sitemap_bestfor_bcl.xml", "sitemap_workflow_bcl.xml", "sitemap_vs_bcl.xml",
        "sitemap_seasonal_bcl.xml", "sitemap_reviews_bcl.xml",
        "sitemap_bestfor_krj.xml", "sitemap_workflow_krj.xml", "sitemap_vs_krj.xml",
        "sitemap_seasonal_krj.xml", "sitemap_reviews_krj.xml",
        "sitemap_bestfor_tsg.xml", "sitemap_workflow_tsg.xml", "sitemap_vs_tsg.xml",
        "sitemap_seasonal_tsg.xml", "sitemap_reviews_tsg.xml",
        "sitemap_bestfor_mdh.xml", "sitemap_workflow_mdh.xml", "sitemap_vs_mdh.xml",
        "sitemap_seasonal_mdh.xml", "sitemap_reviews_mdh.xml",
        "sitemap_bestfor_kri.xml", "sitemap_workflow_kri.xml", "sitemap_vs_kri.xml",
        "sitemap_seasonal_kri.xml", "sitemap_reviews_kri.xml",
        "sitemap_bestfor_ven.xml", "sitemap_workflow_ven.xml", "sitemap_vs_ven.xml",
        "sitemap_seasonal_ven.xml", "sitemap_reviews_ven.xml",
        "sitemap_bestfor_tso.xml", "sitemap_workflow_tso.xml", "sitemap_vs_tso.xml",
        "sitemap_seasonal_tso.xml", "sitemap_reviews_tso.xml",
        "sitemap_bestfor_jam.xml", "sitemap_workflow_jam.xml", "sitemap_vs_jam.xml",
        "sitemap_seasonal_jam.xml", "sitemap_reviews_jam.xml",
        "sitemap_bestfor_mwr.xml", "sitemap_workflow_mwr.xml", "sitemap_vs_mwr.xml",
        "sitemap_seasonal_mwr.xml", "sitemap_reviews_mwr.xml",
        "sitemap_bestfor_crs.xml", "sitemap_workflow_crs.xml", "sitemap_vs_crs.xml",
        "sitemap_seasonal_crs.xml", "sitemap_reviews_crs.xml",
        "sitemap_bestfor_pis.xml", "sitemap_workflow_pis.xml", "sitemap_vs_pis.xml",
        "sitemap_seasonal_pis.xml", "sitemap_reviews_pis.xml",
        "sitemap_bestfor_bis.xml", "sitemap_workflow_bis.xml", "sitemap_vs_bis.xml",
        "sitemap_seasonal_bis.xml", "sitemap_reviews_bis.xml",
        "sitemap_bestfor_gcf.xml", "sitemap_workflow_gcf.xml", "sitemap_vs_gcf.xml",
        "sitemap_seasonal_gcf.xml", "sitemap_reviews_gcf.xml",
        "sitemap_bestfor_swb.xml", "sitemap_workflow_swb.xml", "sitemap_vs_swb.xml",
        "sitemap_seasonal_swb.xml", "sitemap_reviews_swb.xml",
        "sitemap_bestfor_rap.xml", "sitemap_workflow_rap.xml", "sitemap_vs_rap.xml",
        "sitemap_seasonal_rap.xml", "sitemap_reviews_rap.xml",
        "sitemap_bestfor_niu.xml", "sitemap_workflow_niu.xml", "sitemap_vs_niu.xml",
        "sitemap_seasonal_niu.xml", "sitemap_reviews_niu.xml",
        "sitemap_bestfor_raj.xml", "sitemap_workflow_raj.xml", "sitemap_vs_raj.xml",
        "sitemap_seasonal_raj.xml", "sitemap_reviews_raj.xml",
        "sitemap_bestfor_gil.xml", "sitemap_workflow_gil.xml", "sitemap_vs_gil.xml",
        "sitemap_seasonal_gil.xml", "sitemap_reviews_gil.xml",
        "sitemap_bestfor_nhx.xml", "sitemap_workflow_nhx.xml", "sitemap_vs_nhx.xml",
        "sitemap_seasonal_nhx.xml", "sitemap_reviews_nhx.xml",
        "sitemap_bestfor_nan.xml", "sitemap_workflow_nan.xml", "sitemap_vs_nan.xml",
        "sitemap_seasonal_nan.xml", "sitemap_reviews_nan.xml",
        "sitemap_bestfor_yue.xml", "sitemap_workflow_yue.xml", "sitemap_vs_yue.xml",
        "sitemap_seasonal_yue.xml", "sitemap_reviews_yue.xml",
        "sitemap_bestfor_hak.xml", "sitemap_workflow_hak.xml", "sitemap_vs_hak.xml",
        "sitemap_seasonal_hak.xml", "sitemap_reviews_hak.xml",
        "sitemap_bestfor_min.xml", "sitemap_workflow_min.xml", "sitemap_vs_min.xml",
        "sitemap_seasonal_min.xml", "sitemap_reviews_min.xml",
        "sitemap_bestfor_akl.xml", "sitemap_workflow_akl.xml", "sitemap_vs_akl.xml",
        "sitemap_seasonal_akl.xml", "sitemap_reviews_akl.xml",
        "sitemap_bestfor_szl.xml", "sitemap_workflow_szl.xml", "sitemap_vs_szl.xml",
        "sitemap_seasonal_szl.xml", "sitemap_reviews_szl.xml",
        "sitemap_bestfor_kab.xml", "sitemap_workflow_kab.xml", "sitemap_vs_kab.xml",
        "sitemap_seasonal_kab.xml", "sitemap_reviews_kab.xml",
        "sitemap_bestfor_mfe.xml", "sitemap_workflow_mfe.xml", "sitemap_vs_mfe.xml",
        "sitemap_seasonal_mfe.xml", "sitemap_reviews_mfe.xml",
        "sitemap_bestfor_pap.xml", "sitemap_workflow_pap.xml", "sitemap_vs_pap.xml",
        "sitemap_seasonal_pap.xml", "sitemap_reviews_pap.xml",
        "sitemap_bestfor_shi.xml", "sitemap_workflow_shi.xml", "sitemap_vs_shi.xml",
        "sitemap_seasonal_shi.xml", "sitemap_reviews_shi.xml",
        "sitemap_bestfor_csb.xml", "sitemap_workflow_csb.xml", "sitemap_vs_csb.xml",
        "sitemap_seasonal_csb.xml", "sitemap_reviews_csb.xml",
        "sitemap_bestfor_rue.xml", "sitemap_workflow_rue.xml", "sitemap_vs_rue.xml",
        "sitemap_seasonal_rue.xml", "sitemap_reviews_rue.xml",
        "sitemap_bestfor_dsb.xml", "sitemap_workflow_dsb.xml", "sitemap_vs_dsb.xml",
        "sitemap_seasonal_dsb.xml", "sitemap_reviews_dsb.xml",
        "sitemap_bestfor_hsb.xml", "sitemap_workflow_hsb.xml", "sitemap_vs_hsb.xml",
        "sitemap_seasonal_hsb.xml", "sitemap_reviews_hsb.xml",
        "sitemap_bestfor_pcd.xml", "sitemap_workflow_pcd.xml", "sitemap_vs_pcd.xml",
        "sitemap_seasonal_pcd.xml", "sitemap_reviews_pcd.xml",
        "sitemap_bestfor_ext.xml", "sitemap_workflow_ext.xml", "sitemap_vs_ext.xml",
        "sitemap_seasonal_ext.xml", "sitemap_reviews_ext.xml",
        "sitemap_bestfor_mwl.xml", "sitemap_workflow_mwl.xml", "sitemap_vs_mwl.xml",
        "sitemap_seasonal_mwl.xml", "sitemap_reviews_mwl.xml",
        "sitemap_bestfor_lld.xml", "sitemap_workflow_lld.xml", "sitemap_vs_lld.xml",
        "sitemap_seasonal_lld.xml", "sitemap_reviews_lld.xml",
        "sitemap_bestfor_frp.xml", "sitemap_workflow_frp.xml", "sitemap_vs_frp.xml",
        "sitemap_seasonal_frp.xml", "sitemap_reviews_frp.xml",
        "sitemap_bestfor_sco.xml", "sitemap_workflow_sco.xml", "sitemap_vs_sco.xml",
        "sitemap_seasonal_sco.xml", "sitemap_reviews_sco.xml",
        "sitemap_bestfor_gag.xml", "sitemap_workflow_gag.xml", "sitemap_vs_gag.xml",
        "sitemap_seasonal_gag.xml", "sitemap_reviews_gag.xml",
        "sitemap_bestfor_xal.xml", "sitemap_workflow_xal.xml", "sitemap_vs_xal.xml",
        "sitemap_seasonal_xal.xml", "sitemap_reviews_xal.xml",
        "sitemap_bestfor_krc.xml", "sitemap_workflow_krc.xml", "sitemap_vs_krc.xml",
        "sitemap_seasonal_krc.xml", "sitemap_reviews_krc.xml",
        "sitemap_bestfor_ady.xml", "sitemap_workflow_ady.xml", "sitemap_vs_ady.xml",
        "sitemap_seasonal_ady.xml", "sitemap_reviews_ady.xml",
        "sitemap_bestfor_kbd.xml", "sitemap_workflow_kbd.xml", "sitemap_vs_kbd.xml",
        "sitemap_seasonal_kbd.xml", "sitemap_reviews_kbd.xml",
        "sitemap_bestfor_mdf.xml", "sitemap_workflow_mdf.xml", "sitemap_vs_mdf.xml",
        "sitemap_seasonal_mdf.xml", "sitemap_reviews_mdf.xml",
        "sitemap_bestfor_kpv.xml", "sitemap_workflow_kpv.xml", "sitemap_vs_kpv.xml",
        "sitemap_seasonal_kpv.xml", "sitemap_reviews_kpv.xml",
        "sitemap_bestfor_liv.xml", "sitemap_workflow_liv.xml", "sitemap_vs_liv.xml",
        "sitemap_seasonal_liv.xml", "sitemap_reviews_liv.xml",
        "sitemap_bestfor_sma.xml", "sitemap_workflow_sma.xml", "sitemap_vs_sma.xml",
        "sitemap_seasonal_sma.xml", "sitemap_reviews_sma.xml",
        "sitemap_bestfor_smj.xml", "sitemap_workflow_smj.xml", "sitemap_vs_smj.xml",
        "sitemap_seasonal_smj.xml", "sitemap_reviews_smj.xml",
        "sitemap_bestfor_sms.xml", "sitemap_workflow_sms.xml", "sitemap_vs_sms.xml",
        "sitemap_seasonal_sms.xml", "sitemap_reviews_sms.xml",
        "sitemap_bestfor_smn.xml", "sitemap_workflow_smn.xml", "sitemap_vs_smn.xml",
        "sitemap_seasonal_smn.xml", "sitemap_reviews_smn.xml",
        "sitemap_bestfor_olo.xml", "sitemap_workflow_olo.xml", "sitemap_vs_olo.xml",
        "sitemap_seasonal_olo.xml", "sitemap_reviews_olo.xml",
        "sitemap_bestfor_mer.xml", "sitemap_workflow_mer.xml", "sitemap_vs_mer.xml",
        "sitemap_seasonal_mer.xml", "sitemap_reviews_mer.xml",
        "sitemap_bestfor_guz.xml", "sitemap_workflow_guz.xml", "sitemap_vs_guz.xml",
        "sitemap_seasonal_guz.xml", "sitemap_reviews_guz.xml",
        "sitemap_bestfor_kam.xml", "sitemap_workflow_kam.xml", "sitemap_vs_kam.xml",
        "sitemap_seasonal_kam.xml", "sitemap_reviews_kam.xml",
        "sitemap_bestfor_luo.xml", "sitemap_workflow_luo.xml", "sitemap_vs_luo.xml",
        "sitemap_seasonal_luo.xml", "sitemap_reviews_luo.xml",
        "sitemap_bestfor_saq.xml", "sitemap_workflow_saq.xml", "sitemap_vs_saq.xml",
        "sitemap_seasonal_saq.xml", "sitemap_reviews_saq.xml",
        "sitemap_bestfor_mas.xml", "sitemap_workflow_mas.xml", "sitemap_vs_mas.xml",
        "sitemap_seasonal_mas.xml", "sitemap_reviews_mas.xml",
        "sitemap_bestfor_dav.xml", "sitemap_workflow_dav.xml", "sitemap_vs_dav.xml",
        "sitemap_seasonal_dav.xml", "sitemap_reviews_dav.xml",
        "sitemap_bestfor_teo.xml", "sitemap_workflow_teo.xml", "sitemap_vs_teo.xml",
        "sitemap_seasonal_teo.xml", "sitemap_reviews_teo.xml",
        "sitemap_bestfor_cgg.xml", "sitemap_workflow_cgg.xml", "sitemap_vs_cgg.xml",
        "sitemap_seasonal_cgg.xml", "sitemap_reviews_cgg.xml",
        "sitemap_bestfor_nyn.xml", "sitemap_workflow_nyn.xml", "sitemap_vs_nyn.xml",
        "sitemap_seasonal_nyn.xml", "sitemap_reviews_nyn.xml",
        "sitemap_bestfor_xog.xml", "sitemap_workflow_xog.xml", "sitemap_vs_xog.xml",
        "sitemap_seasonal_xog.xml", "sitemap_reviews_xog.xml",
        "sitemap_bestfor_ach.xml", "sitemap_workflow_ach.xml", "sitemap_vs_ach.xml",
        "sitemap_seasonal_ach.xml", "sitemap_reviews_ach.xml",
        "sitemap_bestfor_laj.xml", "sitemap_workflow_laj.xml", "sitemap_vs_laj.xml",
        "sitemap_seasonal_laj.xml", "sitemap_reviews_laj.xml",
        "sitemap_bestfor_niq.xml", "sitemap_workflow_niq.xml", "sitemap_vs_niq.xml",
        "sitemap_seasonal_niq.xml", "sitemap_reviews_niq.xml",
        "sitemap_bestfor_bas.xml", "sitemap_workflow_bas.xml", "sitemap_vs_bas.xml",
        "sitemap_seasonal_bas.xml", "sitemap_reviews_bas.xml",
        "sitemap_bestfor_bum.xml", "sitemap_workflow_bum.xml", "sitemap_vs_bum.xml",
        "sitemap_seasonal_bum.xml", "sitemap_reviews_bum.xml",
        "sitemap_bestfor_mgo.xml", "sitemap_workflow_mgo.xml", "sitemap_vs_mgo.xml",
        "sitemap_seasonal_mgo.xml", "sitemap_reviews_mgo.xml",
        "sitemap_bestfor_aeb.xml", "sitemap_workflow_aeb.xml", "sitemap_vs_aeb.xml",
        "sitemap_seasonal_aeb.xml", "sitemap_reviews_aeb.xml",
        "sitemap_bestfor_zgh.xml", "sitemap_workflow_zgh.xml", "sitemap_vs_zgh.xml",
        "sitemap_seasonal_zgh.xml", "sitemap_reviews_zgh.xml",
        "sitemap_bestfor_sid.xml", "sitemap_workflow_sid.xml", "sitemap_vs_sid.xml",
        "sitemap_seasonal_sid.xml", "sitemap_reviews_sid.xml",
        "sitemap_bestfor_wal.xml", "sitemap_workflow_wal.xml", "sitemap_vs_wal.xml",
        "sitemap_seasonal_wal.xml", "sitemap_reviews_wal.xml",
        "sitemap_bestfor_amo.xml", "sitemap_workflow_amo.xml", "sitemap_vs_amo.xml",
        "sitemap_seasonal_amo.xml", "sitemap_reviews_amo.xml",
        "sitemap_bestfor_rif.xml", "sitemap_workflow_rif.xml", "sitemap_vs_rif.xml",
        "sitemap_seasonal_rif.xml", "sitemap_reviews_rif.xml",
        "sitemap_bestfor_gez.xml", "sitemap_workflow_gez.xml", "sitemap_vs_gez.xml",
        "sitemap_seasonal_gez.xml", "sitemap_reviews_gez.xml",
        "sitemap_bestfor_snn.xml", "sitemap_workflow_snn.xml", "sitemap_vs_snn.xml",
        "sitemap_seasonal_snn.xml", "sitemap_reviews_snn.xml",
        "sitemap_bestfor_tig.xml", "sitemap_workflow_tig.xml", "sitemap_vs_tig.xml",
        "sitemap_seasonal_tig.xml", "sitemap_reviews_tig.xml",
        "sitemap_bestfor_fub.xml", "sitemap_workflow_fub.xml", "sitemap_vs_fub.xml",
        "sitemap_seasonal_fub.xml", "sitemap_reviews_fub.xml",
        "sitemap_bestfor_twi.xml", "sitemap_workflow_twi.xml", "sitemap_vs_twi.xml",
        "sitemap_seasonal_twi.xml", "sitemap_reviews_twi.xml",
        "sitemap_bestfor_fat.xml", "sitemap_workflow_fat.xml", "sitemap_vs_fat.xml",
        "sitemap_seasonal_fat.xml", "sitemap_reviews_fat.xml",
        "sitemap_bestfor_gaa.xml", "sitemap_workflow_gaa.xml", "sitemap_vs_gaa.xml",
        "sitemap_seasonal_gaa.xml", "sitemap_reviews_gaa.xml",
        "sitemap_bestfor_ada.xml", "sitemap_workflow_ada.xml", "sitemap_vs_ada.xml",
        "sitemap_seasonal_ada.xml", "sitemap_reviews_ada.xml",
        "sitemap_bestfor_nmg.xml", "sitemap_workflow_nmg.xml", "sitemap_vs_nmg.xml",
        "sitemap_seasonal_nmg.xml", "sitemap_reviews_nmg.xml",
        "sitemap_bestfor_nnh.xml", "sitemap_workflow_nnh.xml", "sitemap_vs_nnh.xml",
        "sitemap_seasonal_nnh.xml", "sitemap_reviews_nnh.xml",
        "sitemap_bestfor_agq.xml", "sitemap_workflow_agq.xml", "sitemap_vs_agq.xml",
        "sitemap_seasonal_agq.xml", "sitemap_reviews_agq.xml",
        "sitemap_bestfor_jgo.xml", "sitemap_workflow_jgo.xml", "sitemap_vs_jgo.xml",
        "sitemap_seasonal_jgo.xml", "sitemap_reviews_jgo.xml",
        "sitemap_bestfor_ksf.xml", "sitemap_workflow_ksf.xml", "sitemap_vs_ksf.xml",
        "sitemap_seasonal_ksf.xml", "sitemap_reviews_ksf.xml",
        "sitemap_bestfor_mua.xml", "sitemap_workflow_mua.xml", "sitemap_vs_mua.xml",
        "sitemap_seasonal_mua.xml", "sitemap_reviews_mua.xml",
        "sitemap_bestfor_dua.xml", "sitemap_workflow_dua.xml", "sitemap_vs_dua.xml",
        "sitemap_seasonal_dua.xml", "sitemap_reviews_dua.xml",
        "sitemap_bestfor_kkj.xml", "sitemap_workflow_kkj.xml", "sitemap_vs_kkj.xml",
        "sitemap_seasonal_kkj.xml", "sitemap_reviews_kkj.xml",
        "sitemap_bestfor_yav.xml", "sitemap_workflow_yav.xml", "sitemap_vs_yav.xml",
        "sitemap_seasonal_yav.xml", "sitemap_reviews_yav.xml",
        "sitemap_bestfor_byv.xml", "sitemap_workflow_byv.xml", "sitemap_vs_byv.xml",
        "sitemap_seasonal_byv.xml", "sitemap_reviews_byv.xml",
        "sitemap_bestfor_bkm.xml", "sitemap_workflow_bkm.xml", "sitemap_vs_bkm.xml",
        "sitemap_seasonal_bkm.xml", "sitemap_reviews_bkm.xml",
        "sitemap_bestfor_ebu.xml", "sitemap_workflow_ebu.xml", "sitemap_vs_ebu.xml",
        "sitemap_seasonal_ebu.xml", "sitemap_reviews_ebu.xml",
        "sitemap_bestfor_vun.xml", "sitemap_workflow_vun.xml", "sitemap_vs_vun.xml",
        "sitemap_seasonal_vun.xml", "sitemap_reviews_vun.xml",
        "sitemap_bestfor_asa.xml", "sitemap_workflow_asa.xml", "sitemap_vs_asa.xml",
        "sitemap_seasonal_asa.xml", "sitemap_reviews_asa.xml",
        "sitemap_bestfor_bez.xml", "sitemap_workflow_bez.xml", "sitemap_vs_bez.xml",
        "sitemap_seasonal_bez.xml", "sitemap_reviews_bez.xml",
        "sitemap_bestfor_kde.xml", "sitemap_workflow_kde.xml", "sitemap_vs_kde.xml",
        "sitemap_seasonal_kde.xml", "sitemap_reviews_kde.xml",
        "sitemap_bestfor_lag.xml", "sitemap_workflow_lag.xml", "sitemap_vs_lag.xml",
        "sitemap_seasonal_lag.xml", "sitemap_reviews_lag.xml",
        "sitemap_bestfor_rwk.xml", "sitemap_workflow_rwk.xml", "sitemap_vs_rwk.xml",
        "sitemap_seasonal_rwk.xml", "sitemap_reviews_rwk.xml",
        "sitemap_bestfor_sbp.xml", "sitemap_workflow_sbp.xml", "sitemap_vs_sbp.xml",
        "sitemap_seasonal_sbp.xml", "sitemap_reviews_sbp.xml",
        "sitemap_bestfor_jmc.xml", "sitemap_workflow_jmc.xml", "sitemap_vs_jmc.xml",
        "sitemap_seasonal_jmc.xml", "sitemap_reviews_jmc.xml",
        "sitemap_bestfor_rof.xml", "sitemap_workflow_rof.xml", "sitemap_vs_rof.xml",
        "sitemap_seasonal_rof.xml", "sitemap_reviews_rof.xml",
        "sitemap_bestfor_kln.xml", "sitemap_workflow_kln.xml", "sitemap_vs_kln.xml",
        "sitemap_seasonal_kln.xml", "sitemap_reviews_kln.xml",
        "sitemap_bestfor_dga.xml", "sitemap_workflow_dga.xml", "sitemap_vs_dga.xml",
        "sitemap_seasonal_dga.xml", "sitemap_reviews_dga.xml",
        "sitemap_bestfor_mgh.xml", "sitemap_workflow_mgh.xml", "sitemap_vs_mgh.xml",
        "sitemap_seasonal_mgh.xml", "sitemap_reviews_mgh.xml",
        "sitemap_bestfor_brx.xml", "sitemap_workflow_brx.xml", "sitemap_vs_brx.xml",
        "sitemap_seasonal_brx.xml", "sitemap_reviews_brx.xml",
        "sitemap_bestfor_mzn.xml", "sitemap_workflow_mzn.xml", "sitemap_vs_mzn.xml",
        "sitemap_seasonal_mzn.xml", "sitemap_reviews_mzn.xml",
        "sitemap_bestfor_glk.xml", "sitemap_workflow_glk.xml", "sitemap_vs_glk.xml",
        "sitemap_seasonal_glk.xml", "sitemap_reviews_glk.xml",
        "sitemap_bestfor_lrc.xml", "sitemap_workflow_lrc.xml", "sitemap_vs_lrc.xml",
        "sitemap_seasonal_lrc.xml", "sitemap_reviews_lrc.xml",
        "sitemap_bestfor_haz.xml", "sitemap_workflow_haz.xml", "sitemap_vs_haz.xml",
        "sitemap_seasonal_haz.xml", "sitemap_reviews_haz.xml",
        "sitemap_bestfor_dcc.xml", "sitemap_workflow_dcc.xml", "sitemap_vs_dcc.xml",
        "sitemap_seasonal_dcc.xml", "sitemap_reviews_dcc.xml",
        "sitemap_bestfor_wtm.xml", "sitemap_workflow_wtm.xml", "sitemap_vs_wtm.xml",
        "sitemap_seasonal_wtm.xml", "sitemap_reviews_wtm.xml",
        "sitemap_bestfor_skr.xml", "sitemap_workflow_skr.xml", "sitemap_vs_skr.xml",
        "sitemap_seasonal_skr.xml", "sitemap_reviews_skr.xml",
        "sitemap_bestfor_bgn.xml", "sitemap_workflow_bgn.xml", "sitemap_vs_bgn.xml",
        "sitemap_seasonal_bgn.xml", "sitemap_reviews_bgn.xml",
        "sitemap_bestfor_xmf.xml", "sitemap_workflow_xmf.xml", "sitemap_vs_xmf.xml",
        "sitemap_seasonal_xmf.xml", "sitemap_reviews_xmf.xml",
        "sitemap_bestfor_kum.xml", "sitemap_workflow_kum.xml", "sitemap_vs_kum.xml",
        "sitemap_seasonal_kum.xml", "sitemap_reviews_kum.xml",
        "sitemap_bestfor_kpy.xml", "sitemap_workflow_kpy.xml", "sitemap_vs_kpy.xml",
        "sitemap_seasonal_kpy.xml", "sitemap_reviews_kpy.xml",
        "sitemap_bestfor_tab.xml", "sitemap_workflow_tab.xml", "sitemap_vs_tab.xml",
        "sitemap_seasonal_tab.xml", "sitemap_reviews_tab.xml",
        "sitemap_bestfor_nog.xml", "sitemap_workflow_nog.xml", "sitemap_vs_nog.xml",
        "sitemap_seasonal_nog.xml", "sitemap_reviews_nog.xml",
        "sitemap_bestfor_lbe.xml", "sitemap_workflow_lbe.xml", "sitemap_vs_lbe.xml",
        "sitemap_seasonal_lbe.xml", "sitemap_reviews_lbe.xml",
        "sitemap_bestfor_tay.xml", "sitemap_workflow_tay.xml", "sitemap_vs_tay.xml",
        "sitemap_seasonal_tay.xml", "sitemap_reviews_tay.xml",
        "sitemap_bestfor_ami.xml", "sitemap_workflow_ami.xml", "sitemap_vs_ami.xml",
        "sitemap_seasonal_ami.xml", "sitemap_reviews_ami.xml",
        "sitemap_bestfor_dtp.xml", "sitemap_workflow_dtp.xml", "sitemap_vs_dtp.xml",
        "sitemap_seasonal_dtp.xml", "sitemap_reviews_dtp.xml",
        "sitemap_bestfor_hnj.xml", "sitemap_workflow_hnj.xml", "sitemap_vs_hnj.xml",
        "sitemap_seasonal_hnj.xml", "sitemap_reviews_hnj.xml",
        "sitemap_bestfor_blt.xml", "sitemap_workflow_blt.xml", "sitemap_vs_blt.xml",
        "sitemap_seasonal_blt.xml", "sitemap_reviews_blt.xml",
        "sitemap_bestfor_mfa.xml", "sitemap_workflow_mfa.xml", "sitemap_vs_mfa.xml",
        "sitemap_seasonal_mfa.xml", "sitemap_reviews_mfa.xml",
        "sitemap_bestfor_cjy.xml", "sitemap_workflow_cjy.xml", "sitemap_vs_cjy.xml",
        "sitemap_seasonal_cjy.xml", "sitemap_reviews_cjy.xml",
        "sitemap_bestfor_kek.xml", "sitemap_workflow_kek.xml", "sitemap_vs_kek.xml",
        "sitemap_seasonal_kek.xml", "sitemap_reviews_kek.xml",
        "sitemap_bestfor_quc.xml", "sitemap_workflow_quc.xml", "sitemap_vs_quc.xml",
        "sitemap_seasonal_quc.xml", "sitemap_reviews_quc.xml",
        "sitemap_bestfor_cak.xml", "sitemap_workflow_cak.xml", "sitemap_vs_cak.xml",
        "sitemap_seasonal_cak.xml", "sitemap_reviews_cak.xml",
        "sitemap_bestfor_tzo.xml", "sitemap_workflow_tzo.xml", "sitemap_vs_tzo.xml",
        "sitemap_seasonal_tzo.xml", "sitemap_reviews_tzo.xml",
        "sitemap_bestfor_mam.xml", "sitemap_workflow_mam.xml", "sitemap_vs_mam.xml",
        "sitemap_seasonal_mam.xml", "sitemap_reviews_mam.xml",
        "sitemap_bestfor_nav.xml", "sitemap_workflow_nav.xml", "sitemap_vs_nav.xml",
        "sitemap_seasonal_nav.xml", "sitemap_reviews_nav.xml",
        "sitemap_bestfor_arn.xml", "sitemap_workflow_arn.xml", "sitemap_vs_arn.xml",
        "sitemap_seasonal_arn.xml", "sitemap_reviews_arn.xml",
        "sitemap_bestfor_toj.xml", "sitemap_workflow_toj.xml", "sitemap_vs_toj.xml",
        "sitemap_seasonal_toj.xml", "sitemap_reviews_toj.xml",
        "sitemap_bestfor_ikt.xml", "sitemap_workflow_ikt.xml", "sitemap_vs_ikt.xml",
        "sitemap_seasonal_ikt.xml", "sitemap_reviews_ikt.xml",
        "sitemap_bestfor_tzj.xml", "sitemap_workflow_tzj.xml", "sitemap_vs_tzj.xml",
        "sitemap_seasonal_tzj.xml", "sitemap_reviews_tzj.xml",
        "sitemap_bestfor_guc.xml", "sitemap_workflow_guc.xml", "sitemap_vs_guc.xml",
        "sitemap_seasonal_guc.xml", "sitemap_reviews_guc.xml",
        "sitemap_bestfor_urh.xml", "sitemap_workflow_urh.xml", "sitemap_vs_urh.xml",
        "sitemap_seasonal_urh.xml", "sitemap_reviews_urh.xml",
        "sitemap_bestfor_idu.xml", "sitemap_workflow_idu.xml", "sitemap_vs_idu.xml",
        "sitemap_seasonal_idu.xml", "sitemap_reviews_idu.xml",
        "sitemap_bestfor_ixl.xml", "sitemap_workflow_ixl.xml", "sitemap_vs_ixl.xml",
        "sitemap_seasonal_ixl.xml", "sitemap_reviews_ixl.xml",
        "sitemap_bestfor_cni.xml", "sitemap_workflow_cni.xml", "sitemap_vs_cni.xml",
        "sitemap_seasonal_cni.xml", "sitemap_reviews_cni.xml",
        "sitemap_bestfor_pwo.xml", "sitemap_workflow_pwo.xml", "sitemap_vs_pwo.xml",
        "sitemap_seasonal_pwo.xml", "sitemap_reviews_pwo.xml",
        "sitemap_bestfor_mnw.xml", "sitemap_workflow_mnw.xml", "sitemap_vs_mnw.xml",
        "sitemap_seasonal_mnw.xml", "sitemap_reviews_mnw.xml",
        "sitemap_bestfor_blk.xml", "sitemap_workflow_blk.xml", "sitemap_vs_blk.xml",
        "sitemap_seasonal_blk.xml", "sitemap_reviews_blk.xml",
        "sitemap_bestfor_igl.xml", "sitemap_workflow_igl.xml", "sitemap_vs_igl.xml",
        "sitemap_seasonal_igl.xml", "sitemap_reviews_igl.xml",
        "sitemap_bestfor_bin.xml", "sitemap_workflow_bin.xml", "sitemap_vs_bin.xml",
        "sitemap_seasonal_bin.xml", "sitemap_reviews_bin.xml",
        "sitemap_bestfor_tpi.xml", "sitemap_workflow_tpi.xml", "sitemap_vs_tpi.xml",
        "sitemap_seasonal_tpi.xml", "sitemap_reviews_tpi.xml",
        "sitemap_bestfor_pam.xml", "sitemap_workflow_pam.xml", "sitemap_vs_pam.xml",
        "sitemap_seasonal_pam.xml", "sitemap_reviews_pam.xml",
        "sitemap_bestfor_dzo.xml", "sitemap_workflow_dzo.xml", "sitemap_vs_dzo.xml",
        "sitemap_seasonal_dzo.xml", "sitemap_reviews_dzo.xml",
        "sitemap_bestfor_kha.xml", "sitemap_workflow_kha.xml", "sitemap_vs_kha.xml",
        "sitemap_seasonal_kha.xml", "sitemap_reviews_kha.xml",
        "sitemap_bestfor_nia.xml", "sitemap_workflow_nia.xml", "sitemap_vs_nia.xml",
        "sitemap_seasonal_nia.xml", "sitemap_reviews_nia.xml",
        "sitemap_bestfor_ndc.xml", "sitemap_workflow_ndc.xml", "sitemap_vs_ndc.xml",
        "sitemap_seasonal_ndc.xml", "sitemap_reviews_ndc.xml",
        "sitemap_bestfor_mni.xml", "sitemap_workflow_mni.xml", "sitemap_vs_mni.xml",
        "sitemap_seasonal_mni.xml", "sitemap_reviews_mni.xml",
        "sitemap_bestfor_doi.xml", "sitemap_workflow_doi.xml", "sitemap_vs_doi.xml",
        "sitemap_seasonal_doi.xml", "sitemap_reviews_doi.xml",
        "sitemap_bestfor_lug.xml", "sitemap_workflow_lug.xml", "sitemap_vs_lug.xml",
        "sitemap_seasonal_lug.xml", "sitemap_reviews_lug.xml",
        "sitemap_bestfor_kin.xml", "sitemap_workflow_kin.xml", "sitemap_vs_kin.xml",
        "sitemap_seasonal_kin.xml", "sitemap_reviews_kin.xml",
        "sitemap_bestfor_run.xml", "sitemap_workflow_run.xml", "sitemap_vs_run.xml",
        "sitemap_seasonal_run.xml", "sitemap_reviews_run.xml",
        "sitemap_bestfor_lmn.xml", "sitemap_workflow_lmn.xml", "sitemap_vs_lmn.xml",
        "sitemap_seasonal_lmn.xml", "sitemap_reviews_lmn.xml",
        "sitemap_bestfor_gon.xml", "sitemap_workflow_gon.xml", "sitemap_vs_gon.xml",
        "sitemap_seasonal_gon.xml", "sitemap_reviews_gon.xml",
        "sitemap_bestfor_crh.xml", "sitemap_workflow_crh.xml", "sitemap_vs_crh.xml",
        "sitemap_seasonal_crh.xml", "sitemap_reviews_crh.xml",
        "sitemap_bestfor_ton.xml", "sitemap_workflow_ton.xml", "sitemap_vs_ton.xml",
        "sitemap_seasonal_ton.xml", "sitemap_reviews_ton.xml",
        "sitemap_bestfor_lad.xml", "sitemap_workflow_lad.xml", "sitemap_vs_lad.xml",
        "sitemap_seasonal_lad.xml", "sitemap_reviews_lad.xml",
        "sitemap_bestfor_bhi.xml", "sitemap_workflow_bhi.xml", "sitemap_vs_bhi.xml",
        "sitemap_seasonal_bhi.xml", "sitemap_reviews_bhi.xml",
        "sitemap_bestfor_tly.xml", "sitemap_workflow_tly.xml", "sitemap_vs_tly.xml",
        "sitemap_seasonal_tly.xml", "sitemap_reviews_tly.xml",
        "sitemap_bestfor_bew.xml", "sitemap_workflow_bew.xml", "sitemap_vs_bew.xml",
        "sitemap_seasonal_bew.xml", "sitemap_reviews_bew.xml",
        "sitemap_bestfor_bgp.xml", "sitemap_workflow_bgp.xml", "sitemap_vs_bgp.xml",
        "sitemap_seasonal_bgp.xml", "sitemap_reviews_bgp.xml",
        "sitemap_bestfor_sot.xml", "sitemap_workflow_sot.xml", "sitemap_vs_sot.xml",
        "sitemap_seasonal_sot.xml", "sitemap_reviews_sot.xml",
        "sitemap_bestfor_ssw.xml", "sitemap_workflow_ssw.xml", "sitemap_vs_ssw.xml",
        "sitemap_seasonal_ssw.xml", "sitemap_reviews_ssw.xml",
        "sitemap_bestfor_loz.xml", "sitemap_workflow_loz.xml", "sitemap_vs_loz.xml",
        "sitemap_seasonal_loz.xml", "sitemap_reviews_loz.xml",
        "sitemap_bestfor_mah.xml", "sitemap_workflow_mah.xml", "sitemap_vs_mah.xml",
        "sitemap_seasonal_mah.xml", "sitemap_reviews_mah.xml",
        "sitemap_bestfor_que.xml", "sitemap_workflow_que.xml", "sitemap_vs_que.xml",
        "sitemap_seasonal_que.xml", "sitemap_reviews_que.xml",
        "sitemap_bestfor_ckb.xml", "sitemap_workflow_ckb.xml", "sitemap_vs_ckb.xml",
        "sitemap_seasonal_ckb.xml", "sitemap_reviews_ckb.xml",
        "sitemap_bestfor_ksb.xml", "sitemap_workflow_ksb.xml", "sitemap_vs_ksb.xml",
        "sitemap_seasonal_ksb.xml", "sitemap_reviews_ksb.xml",
        "sitemap_bestfor_nus.xml", "sitemap_workflow_nus.xml", "sitemap_vs_nus.xml",
        "sitemap_seasonal_nus.xml", "sitemap_reviews_nus.xml",
        "sitemap_bestfor_bsq.xml", "sitemap_workflow_bsq.xml", "sitemap_vs_bsq.xml",
        "sitemap_seasonal_bsq.xml", "sitemap_reviews_bsq.xml",
        "sitemap_bestfor_men.xml", "sitemap_workflow_men.xml", "sitemap_vs_men.xml",
        "sitemap_seasonal_men.xml", "sitemap_reviews_men.xml",
        "sitemap_bestfor_naq.xml", "sitemap_workflow_naq.xml", "sitemap_vs_naq.xml",
        "sitemap_seasonal_naq.xml", "sitemap_reviews_naq.xml",
        "sitemap_bestfor_fuv.xml", "sitemap_workflow_fuv.xml", "sitemap_vs_fuv.xml",
        "sitemap_seasonal_fuv.xml", "sitemap_reviews_fuv.xml",
        "sitemap_bestfor_kmb.xml", "sitemap_workflow_kmb.xml", "sitemap_vs_kmb.xml",
        "sitemap_seasonal_kmb.xml", "sitemap_reviews_kmb.xml",
        "sitemap_bestfor_lua.xml", "sitemap_workflow_lua.xml", "sitemap_vs_lua.xml",
        "sitemap_seasonal_lua.xml", "sitemap_reviews_lua.xml",
        "sitemap_bestfor_mnk.xml", "sitemap_workflow_mnk.xml", "sitemap_vs_mnk.xml",
        "sitemap_seasonal_mnk.xml", "sitemap_reviews_mnk.xml",
        "sitemap_bestfor_lus.xml", "sitemap_workflow_lus.xml", "sitemap_vs_lus.xml",
        "sitemap_seasonal_lus.xml", "sitemap_reviews_lus.xml",
        "sitemap_bestfor_kby.xml", "sitemap_workflow_kby.xml", "sitemap_vs_kby.xml",
        "sitemap_seasonal_kby.xml", "sitemap_reviews_kby.xml",
        "sitemap_bestfor_ybb.xml", "sitemap_workflow_ybb.xml", "sitemap_vs_ybb.xml",
        "sitemap_seasonal_ybb.xml", "sitemap_reviews_ybb.xml",
        "sitemap_bestfor_dan.xml", "sitemap_workflow_dan.xml", "sitemap_vs_dan.xml",
        "sitemap_seasonal_dan.xml", "sitemap_reviews_dan.xml",
        "sitemap_bestfor_bsc.xml", "sitemap_workflow_bsc.xml", "sitemap_vs_bsc.xml",
        "sitemap_seasonal_bsc.xml", "sitemap_reviews_bsc.xml",
        "sitemap_bestfor_hif.xml", "sitemap_workflow_hif.xml", "sitemap_vs_hif.xml",
        "sitemap_seasonal_hif.xml", "sitemap_reviews_hif.xml",
        "sitemap_bestfor_meu.xml", "sitemap_workflow_meu.xml", "sitemap_vs_meu.xml",
        "sitemap_seasonal_meu.xml", "sitemap_reviews_meu.xml",
        "sitemap_bestfor_lkt.xml", "sitemap_workflow_lkt.xml", "sitemap_vs_lkt.xml",
        "sitemap_seasonal_lkt.xml", "sitemap_reviews_lkt.xml",
        "sitemap_bestfor_moh.xml", "sitemap_workflow_moh.xml", "sitemap_vs_moh.xml",
        "sitemap_seasonal_moh.xml", "sitemap_reviews_moh.xml",
        "sitemap_bestfor_cho.xml", "sitemap_workflow_cho.xml", "sitemap_vs_cho.xml",
        "sitemap_seasonal_cho.xml", "sitemap_reviews_cho.xml",
        "sitemap_bestfor_rop.xml", "sitemap_workflow_rop.xml", "sitemap_vs_rop.xml",
        "sitemap_seasonal_rop.xml", "sitemap_reviews_rop.xml",
        "sitemap_bestfor_ktu.xml", "sitemap_workflow_ktu.xml", "sitemap_vs_ktu.xml",
        "sitemap_seasonal_ktu.xml", "sitemap_reviews_ktu.xml",
        "sitemap_bestfor_guw.xml", "sitemap_workflow_guw.xml", "sitemap_vs_guw.xml",
        "sitemap_seasonal_guw.xml", "sitemap_reviews_guw.xml",
        "sitemap_bestfor_nde.xml", "sitemap_workflow_nde.xml", "sitemap_vs_nde.xml",
        "sitemap_seasonal_nde.xml", "sitemap_reviews_nde.xml",
        "sitemap_bestfor_bem.xml", "sitemap_workflow_bem.xml", "sitemap_vs_bem.xml",
        "sitemap_seasonal_bem.xml", "sitemap_reviews_bem.xml",
        "sitemap_bestfor_efi.xml", "sitemap_workflow_efi.xml", "sitemap_vs_efi.xml",
        "sitemap_seasonal_efi.xml", "sitemap_reviews_efi.xml",
        "sitemap_bestfor_vai.xml", "sitemap_workflow_vai.xml", "sitemap_vs_vai.xml",
        "sitemap_seasonal_vai.xml", "sitemap_reviews_vai.xml",
        "sitemap_bestfor_lun.xml", "sitemap_workflow_lun.xml", "sitemap_vs_lun.xml",
        "sitemap_seasonal_lun.xml", "sitemap_reviews_lun.xml",
        "sitemap_bestfor_kqn.xml", "sitemap_workflow_kqn.xml", "sitemap_vs_kqn.xml",
        "sitemap_seasonal_kqn.xml", "sitemap_reviews_kqn.xml",
        "sitemap_bestfor_kck.xml", "sitemap_workflow_kck.xml", "sitemap_vs_kck.xml",
        "sitemap_seasonal_kck.xml", "sitemap_reviews_kck.xml",
        "sitemap_bestfor_toi.xml", "sitemap_workflow_toi.xml", "sitemap_vs_toi.xml",
        "sitemap_seasonal_toi.xml", "sitemap_reviews_toi.xml",
        "sitemap_bestfor_lue.xml", "sitemap_workflow_lue.xml", "sitemap_vs_lue.xml",
        "sitemap_seasonal_lue.xml", "sitemap_reviews_lue.xml",
        "sitemap_bestfor_nya.xml", "sitemap_workflow_nya.xml", "sitemap_vs_nya.xml",
        "sitemap_seasonal_nya.xml", "sitemap_reviews_nya.xml",
        "sitemap_bestfor_bax.xml", "sitemap_workflow_bax.xml", "sitemap_vs_bax.xml",
        "sitemap_seasonal_bax.xml", "sitemap_reviews_bax.xml",
        "sitemap_bestfor_dyo.xml", "sitemap_workflow_dyo.xml", "sitemap_vs_dyo.xml",
        "sitemap_seasonal_dyo.xml", "sitemap_reviews_dyo.xml",
        "sitemap_bestfor_dip.xml", "sitemap_workflow_dip.xml", "sitemap_vs_dip.xml",
        "sitemap_seasonal_dip.xml", "sitemap_reviews_dip.xml",
        "sitemap_bestfor_cce.xml", "sitemap_workflow_cce.xml", "sitemap_vs_cce.xml",
        "sitemap_seasonal_cce.xml", "sitemap_reviews_cce.xml",
        "sitemap_bestfor_ndh.xml", "sitemap_workflow_ndh.xml", "sitemap_vs_ndh.xml",
        "sitemap_seasonal_ndh.xml", "sitemap_reviews_ndh.xml",
        "sitemap_bestfor_knf.xml", "sitemap_workflow_knf.xml", "sitemap_vs_knf.xml",
        "sitemap_seasonal_knf.xml", "sitemap_reviews_knf.xml",
        "sitemap_bestfor_lgg.xml", "sitemap_workflow_lgg.xml", "sitemap_vs_lgg.xml",
        "sitemap_seasonal_lgg.xml", "sitemap_reviews_lgg.xml",
        "sitemap_bestfor_alz.xml", "sitemap_workflow_alz.xml", "sitemap_vs_alz.xml",
        "sitemap_seasonal_alz.xml", "sitemap_reviews_alz.xml",
        "sitemap_bestfor_myx.xml", "sitemap_workflow_myx.xml", "sitemap_vs_myx.xml",
        "sitemap_seasonal_myx.xml", "sitemap_reviews_myx.xml",
        "sitemap_bestfor_nyo.xml", "sitemap_workflow_nyo.xml", "sitemap_vs_nyo.xml",
        "sitemap_seasonal_nyo.xml", "sitemap_reviews_nyo.xml",
        "sitemap_bestfor_bfa.xml", "sitemap_workflow_bfa.xml", "sitemap_vs_bfa.xml",
        "sitemap_seasonal_bfa.xml", "sitemap_reviews_bfa.xml",
        "sitemap_bestfor_kdj.xml", "sitemap_workflow_kdj.xml", "sitemap_vs_kdj.xml",
        "sitemap_seasonal_kdj.xml", "sitemap_reviews_kdj.xml",
        "sitemap_bestfor_lot.xml", "sitemap_workflow_lot.xml", "sitemap_vs_lot.xml",
        "sitemap_seasonal_lot.xml", "sitemap_reviews_lot.xml",
        "sitemap_bestfor_keo.xml", "sitemap_workflow_keo.xml", "sitemap_vs_keo.xml",
        "sitemap_seasonal_keo.xml", "sitemap_reviews_keo.xml",
        "sitemap_bestfor_kcg.xml", "sitemap_workflow_kcg.xml", "sitemap_vs_kcg.xml",
        "sitemap_seasonal_kcg.xml", "sitemap_reviews_kcg.xml",
        "sitemap_bestfor_avn.xml", "sitemap_workflow_avn.xml", "sitemap_vs_avn.xml",
        "sitemap_seasonal_avn.xml", "sitemap_reviews_avn.xml",
        "sitemap_bestfor_gog.xml", "sitemap_workflow_gog.xml", "sitemap_vs_gog.xml",
        "sitemap_seasonal_gog.xml", "sitemap_reviews_gog.xml",
        "sitemap_bestfor_hay.xml", "sitemap_workflow_hay.xml", "sitemap_vs_hay.xml",
        "sitemap_seasonal_hay.xml", "sitemap_reviews_hay.xml",
        "sitemap_bestfor_heh.xml", "sitemap_workflow_heh.xml", "sitemap_vs_heh.xml",
        "sitemap_seasonal_heh.xml", "sitemap_reviews_heh.xml",
        "sitemap_bestfor_rim.xml", "sitemap_workflow_rim.xml", "sitemap_vs_rim.xml",
        "sitemap_seasonal_rim.xml", "sitemap_reviews_rim.xml",
        "sitemap_bestfor_nyf.xml", "sitemap_workflow_nyf.xml", "sitemap_vs_nyf.xml",
        "sitemap_seasonal_nyf.xml", "sitemap_reviews_nyf.xml",
        "sitemap_bestfor_rag.xml", "sitemap_workflow_rag.xml", "sitemap_vs_rag.xml",
        "sitemap_seasonal_rag.xml", "sitemap_reviews_rag.xml",
        "sitemap_bestfor_thk.xml", "sitemap_workflow_thk.xml", "sitemap_vs_thk.xml",
        "sitemap_seasonal_thk.xml", "sitemap_reviews_thk.xml",
        "sitemap_bestfor_frr.xml", "sitemap_workflow_frr.xml", "sitemap_vs_frr.xml",
        "sitemap_seasonal_frr.xml", "sitemap_reviews_frr.xml",
        "sitemap_bestfor_vro.xml", "sitemap_workflow_vro.xml", "sitemap_vs_vro.xml",
        "sitemap_seasonal_vro.xml", "sitemap_reviews_vro.xml",
        "sitemap_bestfor_rmc.xml", "sitemap_workflow_rmc.xml", "sitemap_vs_rmc.xml",
        "sitemap_seasonal_rmc.xml", "sitemap_reviews_rmc.xml",
        "sitemap_bestfor_sas.xml", "sitemap_workflow_sas.xml", "sitemap_vs_sas.xml",
        "sitemap_seasonal_sas.xml", "sitemap_reviews_sas.xml",
        "sitemap_bestfor_bbc.xml", "sitemap_workflow_bbc.xml", "sitemap_vs_bbc.xml",
        "sitemap_seasonal_bbc.xml", "sitemap_reviews_bbc.xml",
        "sitemap_bestfor_nij.xml", "sitemap_workflow_nij.xml", "sitemap_vs_nij.xml",
        "sitemap_seasonal_nij.xml", "sitemap_reviews_nij.xml",
        "sitemap_bestfor_rej.xml", "sitemap_workflow_rej.xml", "sitemap_vs_rej.xml",
        "sitemap_seasonal_rej.xml", "sitemap_reviews_rej.xml",
        "sitemap_bestfor_abs.xml", "sitemap_workflow_abs.xml", "sitemap_vs_abs.xml",
        "sitemap_seasonal_abs.xml", "sitemap_reviews_abs.xml",
        "sitemap_bestfor_bbj.xml", "sitemap_workflow_bbj.xml", "sitemap_vs_bbj.xml",
        "sitemap_seasonal_bbj.xml", "sitemap_reviews_bbj.xml",
        "sitemap_bestfor_bfd.xml", "sitemap_workflow_bfd.xml", "sitemap_vs_bfd.xml",
        "sitemap_seasonal_bfd.xml", "sitemap_reviews_bfd.xml",
        "sitemap_bestfor_sef.xml", "sitemap_workflow_sef.xml", "sitemap_vs_sef.xml",
        "sitemap_seasonal_sef.xml", "sitemap_reviews_sef.xml",
        "sitemap_bestfor_gej.xml", "sitemap_workflow_gej.xml", "sitemap_vs_gej.xml",
        "sitemap_seasonal_gej.xml", "sitemap_reviews_gej.xml",
        "sitemap_bestfor_bqi.xml", "sitemap_workflow_bqi.xml", "sitemap_vs_bqi.xml",
        "sitemap_seasonal_bqi.xml", "sitemap_reviews_bqi.xml",
        "sitemap_bestfor_cjk.xml", "sitemap_workflow_cjk.xml", "sitemap_vs_cjk.xml",
        "sitemap_seasonal_cjk.xml", "sitemap_reviews_cjk.xml",
        "sitemap_bestfor_anu.xml", "sitemap_workflow_anu.xml", "sitemap_vs_anu.xml",
        "sitemap_seasonal_anu.xml", "sitemap_reviews_anu.xml",
        "sitemap_bestfor_shk.xml", "sitemap_workflow_shk.xml", "sitemap_vs_shk.xml",
        "sitemap_seasonal_shk.xml", "sitemap_reviews_shk.xml",
        "sitemap_bestfor_kdh.xml", "sitemap_workflow_kdh.xml", "sitemap_vs_kdh.xml",
        "sitemap_seasonal_kdh.xml", "sitemap_reviews_kdh.xml",
        "sitemap_bestfor_kus.xml", "sitemap_workflow_kus.xml", "sitemap_vs_kus.xml",
        "sitemap_seasonal_kus.xml", "sitemap_reviews_kus.xml",
        "sitemap_bestfor_ewo.xml", "sitemap_workflow_ewo.xml", "sitemap_vs_ewo.xml",
        "sitemap_seasonal_ewo.xml", "sitemap_reviews_ewo.xml",
        "sitemap_bestfor_rmn.xml", "sitemap_workflow_rmn.xml", "sitemap_vs_rmn.xml",
        "sitemap_seasonal_rmn.xml", "sitemap_reviews_rmn.xml",
        "sitemap_bestfor_ket.xml", "sitemap_workflow_ket.xml", "sitemap_vs_ket.xml",
        "sitemap_seasonal_ket.xml", "sitemap_reviews_ket.xml",
        "sitemap_bestfor_evn.xml", "sitemap_workflow_evn.xml", "sitemap_vs_evn.xml",
        "sitemap_seasonal_evn.xml", "sitemap_reviews_evn.xml",
        "sitemap_bestfor_niv.xml", "sitemap_workflow_niv.xml", "sitemap_vs_niv.xml",
        "sitemap_seasonal_niv.xml", "sitemap_reviews_niv.xml",
        "sitemap_bestfor_hmo.xml", "sitemap_workflow_hmo.xml", "sitemap_vs_hmo.xml",
        "sitemap_seasonal_hmo.xml", "sitemap_reviews_hmo.xml",
        "sitemap_bestfor_cnh.xml", "sitemap_workflow_cnh.xml", "sitemap_vs_cnh.xml",
        "sitemap_seasonal_cnh.xml", "sitemap_reviews_cnh.xml",
        "sitemap_bestfor_agr.xml", "sitemap_workflow_agr.xml", "sitemap_vs_agr.xml",
        "sitemap_seasonal_agr.xml", "sitemap_reviews_agr.xml",
        "sitemap_bestfor_shp.xml", "sitemap_workflow_shp.xml", "sitemap_vs_shp.xml",
        "sitemap_seasonal_shp.xml", "sitemap_reviews_shp.xml",
        "sitemap_bestfor_poh.xml", "sitemap_workflow_poh.xml", "sitemap_vs_poh.xml",
        "sitemap_seasonal_poh.xml", "sitemap_reviews_poh.xml",
        "sitemap_bestfor_kru.xml", "sitemap_workflow_kru.xml", "sitemap_vs_kru.xml",
        "sitemap_seasonal_kru.xml", "sitemap_reviews_kru.xml",
        "sitemap_bestfor_hoc.xml", "sitemap_workflow_hoc.xml", "sitemap_vs_hoc.xml",
        "sitemap_seasonal_hoc.xml", "sitemap_reviews_hoc.xml",
        "sitemap_bestfor_kfy.xml", "sitemap_workflow_kfy.xml", "sitemap_vs_kfy.xml",
        "sitemap_seasonal_kfy.xml", "sitemap_reviews_kfy.xml",
        "sitemap_bestfor_gbm.xml", "sitemap_workflow_gbm.xml", "sitemap_vs_gbm.xml",
        "sitemap_seasonal_gbm.xml", "sitemap_reviews_gbm.xml",
        "sitemap_bestfor_xnr.xml", "sitemap_workflow_xnr.xml", "sitemap_vs_xnr.xml",
        "sitemap_seasonal_xnr.xml", "sitemap_reviews_xnr.xml",
        "sitemap_bestfor_mrw.xml", "sitemap_workflow_mrw.xml", "sitemap_vs_mrw.xml",
        "sitemap_seasonal_mrw.xml", "sitemap_reviews_mrw.xml",
        "sitemap_bestfor_cbk.xml", "sitemap_workflow_cbk.xml", "sitemap_vs_cbk.xml",
        "sitemap_seasonal_cbk.xml", "sitemap_reviews_cbk.xml",
        "sitemap_bestfor_msb.xml", "sitemap_workflow_msb.xml", "sitemap_vs_msb.xml",
        "sitemap_seasonal_msb.xml", "sitemap_reviews_msb.xml",
        "sitemap_bestfor_tbw.xml", "sitemap_workflow_tbw.xml", "sitemap_vs_tbw.xml",
        "sitemap_seasonal_tbw.xml", "sitemap_reviews_tbw.xml",
        "sitemap_bestfor_hnn.xml", "sitemap_workflow_hnn.xml", "sitemap_vs_hnn.xml",
        "sitemap_seasonal_hnn.xml", "sitemap_reviews_hnn.xml",
        "sitemap_bestfor_any.xml", "sitemap_workflow_any.xml", "sitemap_vs_any.xml",
        "sitemap_seasonal_any.xml", "sitemap_reviews_any.xml",
        "sitemap_bestfor_abr.xml", "sitemap_workflow_abr.xml", "sitemap_vs_abr.xml",
        "sitemap_seasonal_abr.xml", "sitemap_reviews_abr.xml",
        "sitemap_bestfor_nzi.xml", "sitemap_workflow_nzi.xml", "sitemap_vs_nzi.xml",
        "sitemap_seasonal_nzi.xml", "sitemap_reviews_nzi.xml",
        "sitemap_bestfor_gjn.xml", "sitemap_workflow_gjn.xml", "sitemap_vs_gjn.xml",
        "sitemap_seasonal_gjn.xml", "sitemap_reviews_gjn.xml",
        "sitemap_bestfor_yom.xml", "sitemap_workflow_yom.xml", "sitemap_vs_yom.xml",
        "sitemap_seasonal_yom.xml", "sitemap_reviews_yom.xml",
        "sitemap_bestfor_mfq.xml", "sitemap_workflow_mfq.xml", "sitemap_vs_mfq.xml",
        "sitemap_seasonal_mfq.xml", "sitemap_reviews_mfq.xml",
        "sitemap_bestfor_luc.xml", "sitemap_workflow_luc.xml", "sitemap_vs_luc.xml",
        "sitemap_seasonal_luc.xml", "sitemap_reviews_luc.xml",
        "sitemap_bestfor_bud.xml", "sitemap_workflow_bud.xml", "sitemap_vs_bud.xml",
        "sitemap_seasonal_bud.xml", "sitemap_reviews_bud.xml",
        "sitemap_bestfor_yre.xml", "sitemap_workflow_yre.xml", "sitemap_vs_yre.xml",
        "sitemap_seasonal_yre.xml", "sitemap_reviews_yre.xml",
        "sitemap_bestfor_bss.xml", "sitemap_workflow_bss.xml", "sitemap_vs_bss.xml",
        "sitemap_seasonal_bss.xml", "sitemap_reviews_bss.xml",
        "sitemap_bestfor_bfo.xml", "sitemap_workflow_bfo.xml", "sitemap_vs_bfo.xml",
        "sitemap_seasonal_bfo.xml", "sitemap_reviews_bfo.xml",
        "sitemap_bestfor_dop.xml", "sitemap_workflow_dop.xml", "sitemap_vs_dop.xml",
        "sitemap_seasonal_dop.xml", "sitemap_reviews_dop.xml",
        "sitemap_bestfor_xon.xml", "sitemap_workflow_xon.xml", "sitemap_vs_xon.xml",
        "sitemap_seasonal_xon.xml", "sitemap_reviews_xon.xml",
        "sitemap_bestfor_ncu.xml", "sitemap_workflow_ncu.xml", "sitemap_vs_ncu.xml",
        "sitemap_seasonal_ncu.xml", "sitemap_reviews_ncu.xml",
        "sitemap_bestfor_gng.xml", "sitemap_workflow_gng.xml", "sitemap_vs_gng.xml",
        "sitemap_seasonal_gng.xml", "sitemap_reviews_gng.xml",
        "sitemap_bestfor_bqc.xml", "sitemap_workflow_bqc.xml", "sitemap_vs_bqc.xml",
        "sitemap_seasonal_bqc.xml", "sitemap_reviews_bqc.xml",
        "sitemap_bestfor_mcp.xml", "sitemap_workflow_mcp.xml", "sitemap_vs_mcp.xml",
        "sitemap_seasonal_mcp.xml", "sitemap_reviews_mcp.xml",
        "sitemap_bestfor_tik.xml", "sitemap_workflow_tik.xml", "sitemap_vs_tik.xml",
        "sitemap_seasonal_tik.xml", "sitemap_reviews_tik.xml",
        "sitemap_bestfor_koq.xml", "sitemap_workflow_koq.xml", "sitemap_vs_koq.xml",
        "sitemap_seasonal_koq.xml", "sitemap_reviews_koq.xml",
        "sitemap_bestfor_bex.xml", "sitemap_workflow_bex.xml", "sitemap_vs_bex.xml",
        "sitemap_seasonal_bex.xml", "sitemap_reviews_bex.xml",
        "sitemap_bestfor_avu.xml", "sitemap_workflow_avu.xml", "sitemap_vs_avu.xml",
        "sitemap_seasonal_avu.xml", "sitemap_reviews_avu.xml",
        "sitemap_bestfor_las.xml", "sitemap_workflow_las.xml", "sitemap_vs_las.xml",
        "sitemap_seasonal_las.xml", "sitemap_reviews_las.xml",
        "sitemap_bestfor_ntr.xml", "sitemap_workflow_ntr.xml", "sitemap_vs_ntr.xml",
        "sitemap_seasonal_ntr.xml", "sitemap_reviews_ntr.xml",
        "sitemap_bestfor_gud.xml", "sitemap_workflow_gud.xml", "sitemap_vs_gud.xml",
        "sitemap_seasonal_gud.xml", "sitemap_reviews_gud.xml",
        "sitemap_bestfor_bwu.xml", "sitemap_workflow_bwu.xml", "sitemap_vs_bwu.xml",
        "sitemap_seasonal_bwu.xml", "sitemap_reviews_bwu.xml",
        "sitemap_bestfor_nmz.xml", "sitemap_workflow_nmz.xml", "sitemap_vs_nmz.xml",
        "sitemap_seasonal_nmz.xml", "sitemap_reviews_nmz.xml",
        "sitemap_bestfor_dgo.xml", "sitemap_workflow_dgo.xml", "sitemap_vs_dgo.xml",
        "sitemap_seasonal_dgo.xml", "sitemap_reviews_dgo.xml",
        "sitemap_bestfor_kao.xml", "sitemap_workflow_kao.xml", "sitemap_vs_kao.xml",
        "sitemap_seasonal_kao.xml", "sitemap_reviews_kao.xml",
        "sitemap_bestfor_myk.xml", "sitemap_workflow_myk.xml", "sitemap_vs_myk.xml",
        "sitemap_seasonal_myk.xml", "sitemap_reviews_myk.xml",
        "sitemap_bestfor_bze.xml", "sitemap_workflow_bze.xml", "sitemap_vs_bze.xml",
        "sitemap_seasonal_bze.xml", "sitemap_reviews_bze.xml",
        "sitemap_bestfor_snk.xml", "sitemap_workflow_snk.xml", "sitemap_vs_snk.xml",
        "sitemap_seasonal_snk.xml", "sitemap_reviews_snk.xml",
        "sitemap_bestfor_kbn.xml", "sitemap_workflow_kbn.xml", "sitemap_vs_kbn.xml",
        "sitemap_seasonal_kbn.xml", "sitemap_reviews_kbn.xml",
        "sitemap_bestfor_sg2.xml", "sitemap_workflow_sg2.xml", "sitemap_vs_sg2.xml",
        "sitemap_seasonal_sg2.xml", "sitemap_reviews_sg2.xml",
        "sitemap_bestfor_nup.xml", "sitemap_workflow_nup.xml", "sitemap_vs_nup.xml",
        "sitemap_seasonal_nup.xml", "sitemap_reviews_nup.xml",
        "sitemap_bestfor_gbr.xml", "sitemap_workflow_gbr.xml", "sitemap_vs_gbr.xml",
        "sitemap_seasonal_gbr.xml", "sitemap_reviews_gbr.xml",
        "sitemap_bestfor_bqv.xml", "sitemap_workflow_bqv.xml", "sitemap_vs_bqv.xml",
        "sitemap_seasonal_bqv.xml", "sitemap_reviews_bqv.xml",
        "sitemap_bestfor_etu.xml", "sitemap_workflow_etu.xml", "sitemap_vs_etu.xml",
        "sitemap_seasonal_etu.xml", "sitemap_reviews_etu.xml",
        "sitemap_bestfor_mfi.xml", "sitemap_workflow_mfi.xml", "sitemap_vs_mfi.xml",
        "sitemap_seasonal_mfi.xml", "sitemap_reviews_mfi.xml",
        "sitemap_bestfor_mcn.xml", "sitemap_workflow_mcn.xml", "sitemap_vs_mcn.xml",
        "sitemap_seasonal_mcn.xml", "sitemap_reviews_mcn.xml",
        "sitemap_bestfor_gid.xml", "sitemap_workflow_gid.xml", "sitemap_vs_gid.xml",
        "sitemap_seasonal_gid.xml", "sitemap_reviews_gid.xml",
        "sitemap_bestfor_kbp2.xml", "sitemap_workflow_kbp2.xml", "sitemap_vs_kbp2.xml",
        "sitemap_seasonal_kbp2.xml", "sitemap_reviews_kbp2.xml",
        "sitemap_bestfor_bwq.xml", "sitemap_workflow_bwq.xml", "sitemap_vs_bwq.xml",
        "sitemap_seasonal_bwq.xml", "sitemap_reviews_bwq.xml",
        "sitemap_bestfor_dga2.xml", "sitemap_workflow_dga2.xml", "sitemap_vs_dga2.xml",
        "sitemap_seasonal_dga2.xml", "sitemap_reviews_dga2.xml",
        "sitemap_bestfor_mfz.xml", "sitemap_workflow_mfz.xml", "sitemap_vs_mfz.xml",
        "sitemap_seasonal_mfz.xml", "sitemap_reviews_mfz.xml",
        "sitemap_bestfor_bfa2.xml", "sitemap_workflow_bfa2.xml", "sitemap_vs_bfa2.xml",
        "sitemap_seasonal_bfa2.xml", "sitemap_reviews_bfa2.xml",
        "sitemap_bestfor_bjt.xml", "sitemap_workflow_bjt.xml", "sitemap_vs_bjt.xml",
        "sitemap_seasonal_bjt.xml", "sitemap_reviews_bjt.xml",
        "sitemap_bestfor_bsc2.xml", "sitemap_workflow_bsc2.xml", "sitemap_vs_bsc2.xml",
        "sitemap_seasonal_bsc2.xml", "sitemap_reviews_bsc2.xml",
        "sitemap_bestfor_csk.xml", "sitemap_workflow_csk.xml", "sitemap_vs_csk.xml",
        "sitemap_seasonal_csk.xml", "sitemap_reviews_csk.xml",
        "sitemap_bestfor_kdc2.xml", "sitemap_workflow_kdc2.xml", "sitemap_vs_kdc2.xml",
        "sitemap_seasonal_kdc2.xml", "sitemap_reviews_kdc2.xml",
        "sitemap_bestfor_vid.xml", "sitemap_workflow_vid.xml", "sitemap_vs_vid.xml",
        "sitemap_seasonal_vid.xml", "sitemap_reviews_vid.xml",
        "sitemap_bestfor_zga.xml", "sitemap_workflow_zga.xml", "sitemap_vs_zga.xml",
        "sitemap_seasonal_zga.xml", "sitemap_reviews_zga.xml",
        "sitemap_bestfor_nim.xml", "sitemap_workflow_nim.xml", "sitemap_vs_nim.xml",
        "sitemap_seasonal_nim.xml", "sitemap_reviews_nim.xml",
        "sitemap_bestfor_rag2.xml", "sitemap_workflow_rag2.xml", "sitemap_vs_rag2.xml",
        "sitemap_seasonal_rag2.xml", "sitemap_reviews_rag2.xml",
        "sitemap_bestfor_sba.xml", "sitemap_workflow_sba.xml", "sitemap_vs_sba.xml",
        "sitemap_seasonal_sba.xml", "sitemap_reviews_sba.xml",
        "sitemap_bestfor_tui.xml", "sitemap_workflow_tui.xml", "sitemap_vs_tui.xml",
        "sitemap_seasonal_tui.xml", "sitemap_reviews_tui.xml",
        "sitemap_bestfor_daa.xml", "sitemap_workflow_daa.xml", "sitemap_vs_daa.xml",
        "sitemap_seasonal_daa.xml", "sitemap_reviews_daa.xml",
        "sitemap_bestfor_ngb.xml", "sitemap_workflow_ngb.xml", "sitemap_vs_ngb.xml",
        "sitemap_seasonal_ngb.xml", "sitemap_reviews_ngb.xml",
        "sitemap_bestfor_ttj.xml", "sitemap_workflow_ttj.xml", "sitemap_vs_ttj.xml",
        "sitemap_seasonal_ttj.xml", "sitemap_reviews_ttj.xml",
        "sitemap_bestfor_gwr.xml", "sitemap_workflow_gwr.xml", "sitemap_vs_gwr.xml",
        "sitemap_seasonal_gwr.xml", "sitemap_reviews_gwr.xml",
        "sitemap_bestfor_pko.xml", "sitemap_workflow_pko.xml", "sitemap_vs_pko.xml",
        "sitemap_seasonal_pko.xml", "sitemap_reviews_pko.xml",
        "sitemap_bestfor_saf.xml", "sitemap_workflow_saf.xml", "sitemap_vs_saf.xml",
        "sitemap_seasonal_saf.xml", "sitemap_reviews_saf.xml",
        "sitemap_bestfor_mzw.xml", "sitemap_workflow_mzw.xml", "sitemap_vs_mzw.xml",
        "sitemap_seasonal_mzw.xml", "sitemap_reviews_mzw.xml",
        "sitemap_bestfor_hag.xml", "sitemap_workflow_hag.xml", "sitemap_vs_hag.xml",
        "sitemap_seasonal_hag.xml", "sitemap_reviews_hag.xml",
        "sitemap_bestfor_fuf.xml", "sitemap_workflow_fuf.xml", "sitemap_vs_fuf.xml",
        "sitemap_seasonal_fuf.xml", "sitemap_reviews_fuf.xml",
        "sitemap_bestfor_xpe.xml", "sitemap_workflow_xpe.xml", "sitemap_vs_xpe.xml",
        "sitemap_seasonal_xpe.xml", "sitemap_reviews_xpe.xml",
        "sitemap_bestfor_gkp.xml", "sitemap_workflow_gkp.xml", "sitemap_vs_gkp.xml",
        "sitemap_seasonal_gkp.xml", "sitemap_reviews_gkp.xml",
        "sitemap_bestfor_kqs.xml", "sitemap_workflow_kqs.xml", "sitemap_vs_kqs.xml",
        "sitemap_seasonal_kqs.xml", "sitemap_reviews_kqs.xml",
        "sitemap_bestfor_bza.xml", "sitemap_workflow_bza.xml", "sitemap_vs_bza.xml",
        "sitemap_seasonal_bza.xml", "sitemap_reviews_bza.xml",
        "sitemap_bestfor_snf.xml", "sitemap_workflow_snf.xml", "sitemap_vs_snf.xml",
        "sitemap_seasonal_snf.xml", "sitemap_reviews_snf.xml",
        "sitemap_bestfor_mcu.xml", "sitemap_workflow_mcu.xml", "sitemap_vs_mcu.xml",
        "sitemap_seasonal_mcu.xml", "sitemap_reviews_mcu.xml",
        "sitemap_bestfor_nnq.xml", "sitemap_workflow_nnq.xml", "sitemap_vs_nnq.xml",
        "sitemap_seasonal_nnq.xml", "sitemap_reviews_nnq.xml",
        "sitemap_bestfor_tnr.xml", "sitemap_workflow_tnr.xml", "sitemap_vs_tnr.xml",
        "sitemap_seasonal_tnr.xml", "sitemap_reviews_tnr.xml",
        "sitemap_bestfor_mfk.xml", "sitemap_workflow_mfk.xml", "sitemap_vs_mfk.xml",
        "sitemap_seasonal_mfk.xml", "sitemap_reviews_mfk.xml",
        "sitemap_bestfor_knc.xml", "sitemap_workflow_knc.xml", "sitemap_vs_knc.xml",
        "sitemap_seasonal_knc.xml", "sitemap_reviews_knc.xml",
        "sitemap_bestfor_dnj.xml", "sitemap_workflow_dnj.xml", "sitemap_vs_dnj.xml",
        "sitemap_seasonal_dnj.xml", "sitemap_reviews_dnj.xml",
        "sitemap_bestfor_lom.xml", "sitemap_workflow_lom.xml", "sitemap_vs_lom.xml",
        "sitemap_seasonal_lom.xml", "sitemap_reviews_lom.xml",
        "sitemap_bestfor_gbo.xml", "sitemap_workflow_gbo.xml", "sitemap_vs_gbo.xml",
        "sitemap_seasonal_gbo.xml", "sitemap_reviews_gbo.xml",
        "sitemap_bestfor_grj.xml", "sitemap_workflow_grj.xml", "sitemap_vs_grj.xml",
        "sitemap_seasonal_grj.xml", "sitemap_reviews_grj.xml",
        "sitemap_bestfor_dee.xml", "sitemap_workflow_dee.xml", "sitemap_vs_dee.xml",
        "sitemap_seasonal_dee.xml", "sitemap_reviews_dee.xml",
        "sitemap_bestfor_wob.xml", "sitemap_workflow_wob.xml", "sitemap_vs_wob.xml",
        "sitemap_seasonal_wob.xml", "sitemap_reviews_wob.xml",
        "sitemap_bestfor_bmq.xml", "sitemap_workflow_bmq.xml", "sitemap_vs_bmq.xml",
        "sitemap_seasonal_bmq.xml", "sitemap_reviews_bmq.xml",
        "sitemap_bestfor_box.xml", "sitemap_workflow_box.xml", "sitemap_vs_box.xml",
        "sitemap_seasonal_box.xml", "sitemap_reviews_box.xml",
        "sitemap_bestfor_kel.xml", "sitemap_workflow_kel.xml", "sitemap_vs_kel.xml",
        "sitemap_seasonal_kel.xml", "sitemap_reviews_kel.xml",
        "sitemap_bestfor_grt.xml", "sitemap_workflow_grt.xml", "sitemap_vs_grt.xml",
        "sitemap_seasonal_grt.xml", "sitemap_reviews_grt.xml",
        "sitemap_bestfor_nag.xml", "sitemap_workflow_nag.xml", "sitemap_vs_nag.xml",
        "sitemap_seasonal_nag.xml", "sitemap_reviews_nag.xml",
        "sitemap_bestfor_njo.xml", "sitemap_workflow_njo.xml", "sitemap_vs_njo.xml",
        "sitemap_seasonal_njo.xml", "sitemap_reviews_njo.xml",
        "sitemap_bestfor_wbm.xml", "sitemap_workflow_wbm.xml", "sitemap_vs_wbm.xml",
        "sitemap_seasonal_wbm.xml", "sitemap_reviews_wbm.xml",
        "sitemap_bestfor_tdg.xml", "sitemap_workflow_tdg.xml", "sitemap_vs_tdg.xml",
        "sitemap_seasonal_tdg.xml", "sitemap_reviews_tdg.xml",
        "sitemap_bestfor_tsj.xml", "sitemap_workflow_tsj.xml", "sitemap_vs_tsj.xml",
        "sitemap_seasonal_tsj.xml", "sitemap_reviews_tsj.xml",
        "sitemap_bestfor_lep.xml", "sitemap_workflow_lep.xml", "sitemap_vs_lep.xml",
        "sitemap_seasonal_lep.xml", "sitemap_reviews_lep.xml",
        "sitemap_bestfor_sip.xml", "sitemap_workflow_sip.xml", "sitemap_vs_sip.xml",
        "sitemap_seasonal_sip.xml", "sitemap_reviews_sip.xml",
        "sitemap_bestfor_jya.xml", "sitemap_workflow_jya.xml", "sitemap_vs_jya.xml",
        "sitemap_seasonal_jya.xml", "sitemap_reviews_jya.xml",
        "sitemap_bestfor_mtr.xml", "sitemap_workflow_mtr.xml", "sitemap_vs_mtr.xml",
        "sitemap_seasonal_mtr.xml", "sitemap_reviews_mtr.xml",
        "sitemap_bestfor_wbr.xml", "sitemap_workflow_wbr.xml", "sitemap_vs_wbr.xml",
        "sitemap_seasonal_wbr.xml", "sitemap_reviews_wbr.xml",
        "sitemap_bestfor_hoj.xml", "sitemap_workflow_hoj.xml", "sitemap_vs_hoj.xml",
        "sitemap_seasonal_hoj.xml", "sitemap_reviews_hoj.xml",
        "sitemap_bestfor_noe.xml", "sitemap_workflow_noe.xml", "sitemap_vs_noe.xml",
        "sitemap_seasonal_noe.xml", "sitemap_reviews_noe.xml",
        "sitemap_bestfor_dhd.xml", "sitemap_workflow_dhd.xml", "sitemap_vs_dhd.xml",
        "sitemap_seasonal_dhd.xml", "sitemap_reviews_dhd.xml",
        "sitemap_bestfor_bra.xml", "sitemap_workflow_bra.xml", "sitemap_vs_bra.xml",
        "sitemap_seasonal_bra.xml", "sitemap_reviews_bra.xml",
        "sitemap_bestfor_gju.xml", "sitemap_workflow_gju.xml", "sitemap_vs_gju.xml",
        "sitemap_seasonal_gju.xml", "sitemap_reviews_gju.xml",
        "sitemap_bestfor_anp.xml", "sitemap_workflow_anp.xml", "sitemap_vs_anp.xml",
        "sitemap_seasonal_anp.xml", "sitemap_reviews_anp.xml",
        "sitemap_bestfor_kjo.xml", "sitemap_workflow_kjo.xml", "sitemap_vs_kjo.xml",
        "sitemap_seasonal_kjo.xml", "sitemap_reviews_kjo.xml",
        "sitemap_bestfor_gdx.xml", "sitemap_workflow_gdx.xml", "sitemap_vs_gdx.xml",
        "sitemap_seasonal_gdx.xml", "sitemap_reviews_gdx.xml",
        "sitemap_bestfor_kvx.xml", "sitemap_workflow_kvx.xml", "sitemap_vs_kvx.xml",
        "sitemap_seasonal_kvx.xml", "sitemap_reviews_kvx.xml",
        "sitemap_bestfor_vah.xml", "sitemap_workflow_vah.xml", "sitemap_vs_vah.xml",
        "sitemap_seasonal_vah.xml", "sitemap_reviews_vah.xml",
        "sitemap_bestfor_bfy.xml", "sitemap_workflow_bfy.xml", "sitemap_vs_bfy.xml",
        "sitemap_seasonal_bfy.xml", "sitemap_reviews_bfy.xml",
        "sitemap_bestfor_unr.xml", "sitemap_workflow_unr.xml", "sitemap_vs_unr.xml",
        "sitemap_seasonal_unr.xml", "sitemap_reviews_unr.xml",
        "sitemap_bestfor_sgj.xml", "sitemap_workflow_sgj.xml", "sitemap_vs_sgj.xml",
        "sitemap_seasonal_sgj.xml", "sitemap_reviews_sgj.xml",
        "sitemap_bestfor_dhn.xml", "sitemap_workflow_dhn.xml", "sitemap_vs_dhn.xml",
        "sitemap_seasonal_dhn.xml", "sitemap_reviews_dhn.xml",
        "sitemap_bestfor_kfx.xml", "sitemap_workflow_kfx.xml", "sitemap_vs_kfx.xml",
        "sitemap_seasonal_kfx.xml", "sitemap_reviews_kfx.xml",
        "sitemap_bestfor_gwc.xml", "sitemap_workflow_gwc.xml", "sitemap_vs_gwc.xml",
        "sitemap_seasonal_gwc.xml", "sitemap_reviews_gwc.xml",
        "sitemap_bestfor_bsh.xml", "sitemap_workflow_bsh.xml", "sitemap_vs_bsh.xml",
        "sitemap_seasonal_bsh.xml", "sitemap_reviews_bsh.xml",
        "sitemap_bestfor_kfe.xml", "sitemap_workflow_kfe.xml", "sitemap_vs_kfe.xml",
        "sitemap_seasonal_kfe.xml", "sitemap_reviews_kfe.xml",
        "sitemap_bestfor_emx.xml", "sitemap_workflow_emx.xml", "sitemap_vs_emx.xml",
        "sitemap_seasonal_emx.xml", "sitemap_reviews_emx.xml",
        "sitemap_bestfor_aec.xml", "sitemap_workflow_aec.xml", "sitemap_vs_aec.xml",
        "sitemap_seasonal_aec.xml", "sitemap_reviews_aec.xml",
        "sitemap_bestfor_acm.xml", "sitemap_workflow_acm.xml", "sitemap_vs_acm.xml",
        "sitemap_seasonal_acm.xml", "sitemap_reviews_acm.xml",
        "sitemap_bestfor_afb.xml", "sitemap_workflow_afb.xml", "sitemap_vs_afb.xml",
        "sitemap_seasonal_afb.xml", "sitemap_reviews_afb.xml",
        "sitemap_bestfor_acw.xml", "sitemap_workflow_acw.xml", "sitemap_vs_acw.xml",
        "sitemap_seasonal_acw.xml", "sitemap_reviews_acw.xml",
        "sitemap_bestfor_acq.xml", "sitemap_workflow_acq.xml", "sitemap_vs_acq.xml",
        "sitemap_seasonal_acq.xml", "sitemap_reviews_acq.xml",
        "sitemap_bestfor_arz.xml", "sitemap_workflow_arz.xml", "sitemap_vs_arz.xml",
        "sitemap_seasonal_arz.xml", "sitemap_reviews_arz.xml",
        "sitemap_bestfor_ary.xml", "sitemap_workflow_ary.xml", "sitemap_vs_ary.xml",
        "sitemap_seasonal_ary.xml", "sitemap_reviews_ary.xml",
        "sitemap_bestfor_apd.xml", "sitemap_workflow_apd.xml", "sitemap_vs_apd.xml",
        "sitemap_seasonal_apd.xml", "sitemap_reviews_apd.xml",
        "sitemap_bestfor_apc.xml", "sitemap_workflow_apc.xml", "sitemap_vs_apc.xml",
        "sitemap_seasonal_apc.xml", "sitemap_reviews_apc.xml",
        "sitemap_bestfor_hno.xml", "sitemap_workflow_hno.xml", "sitemap_vs_hno.xml",
        "sitemap_seasonal_hno.xml", "sitemap_reviews_hno.xml",
        "sitemap_bestfor_hnd.xml", "sitemap_workflow_hnd.xml", "sitemap_vs_hnd.xml",
        "sitemap_seasonal_hnd.xml", "sitemap_reviews_hnd.xml",
        "sitemap_bestfor_pmu.xml", "sitemap_workflow_pmu.xml", "sitemap_vs_pmu.xml",
        "sitemap_seasonal_pmu.xml", "sitemap_reviews_pmu.xml",
        "sitemap_bestfor_bgq.xml", "sitemap_workflow_bgq.xml", "sitemap_vs_bgq.xml",
        "sitemap_seasonal_bgq.xml", "sitemap_reviews_bgq.xml",
        "sitemap_bestfor_ymm.xml", "sitemap_workflow_ymm.xml", "sitemap_vs_ymm.xml",
        "sitemap_seasonal_ymm.xml", "sitemap_reviews_ymm.xml",
        "sitemap_bestfor_gbk.xml", "sitemap_workflow_gbk.xml", "sitemap_vs_gbk.xml",
        "sitemap_seasonal_gbk.xml", "sitemap_reviews_gbk.xml",
        "sitemap_bestfor_xnj.xml", "sitemap_workflow_xnj.xml", "sitemap_vs_xnj.xml",
        "sitemap_seasonal_xnj.xml", "sitemap_reviews_xnj.xml",
        "sitemap_bestfor_odk.xml", "sitemap_workflow_odk.xml", "sitemap_vs_odk.xml",
        "sitemap_seasonal_odk.xml", "sitemap_reviews_odk.xml",
        "sitemap_bestfor_kxp.xml", "sitemap_workflow_kxp.xml", "sitemap_vs_kxp.xml",
        "sitemap_seasonal_kxp.xml", "sitemap_reviews_kxp.xml",
        "sitemap_bestfor_pce.xml", "sitemap_workflow_pce.xml", "sitemap_vs_pce.xml",
        "sitemap_seasonal_pce.xml", "sitemap_reviews_pce.xml",
        "sitemap_bestfor_rkt.xml", "sitemap_workflow_rkt.xml", "sitemap_vs_rkt.xml",
        "sitemap_seasonal_rkt.xml", "sitemap_reviews_rkt.xml",
        "sitemap_bestfor_ctg.xml", "sitemap_workflow_ctg.xml", "sitemap_vs_ctg.xml",
        "sitemap_seasonal_ctg.xml", "sitemap_reviews_ctg.xml",
        "sitemap_bestfor_syl.xml", "sitemap_workflow_syl.xml", "sitemap_vs_syl.xml",
        "sitemap_seasonal_syl.xml", "sitemap_reviews_syl.xml",
        "sitemap_bestfor_swv.xml", "sitemap_workflow_swv.xml", "sitemap_vs_swv.xml",
        "sitemap_seasonal_swv.xml", "sitemap_reviews_swv.xml",
        "sitemap_bestfor_kfq.xml", "sitemap_workflow_kfq.xml", "sitemap_vs_kfq.xml",
        "sitemap_seasonal_kfq.xml", "sitemap_reviews_kfq.xml",
        "sitemap_bestfor_bpy.xml", "sitemap_workflow_bpy.xml", "sitemap_vs_bpy.xml",
        "sitemap_seasonal_bpy.xml", "sitemap_reviews_bpy.xml",
        "sitemap_bestfor_tdb.xml", "sitemap_workflow_tdb.xml", "sitemap_vs_tdb.xml",
        "sitemap_seasonal_tdb.xml", "sitemap_reviews_tdb.xml",
        "sitemap_bestfor_xsr.xml", "sitemap_workflow_xsr.xml", "sitemap_vs_xsr.xml",
        "sitemap_seasonal_xsr.xml", "sitemap_reviews_xsr.xml",
        "sitemap_bestfor_kxv.xml", "sitemap_workflow_kxv.xml", "sitemap_vs_kxv.xml",
        "sitemap_seasonal_kxv.xml", "sitemap_reviews_kxv.xml",
        "sitemap_bestfor_gbj.xml", "sitemap_workflow_gbj.xml", "sitemap_vs_gbj.xml",
        "sitemap_seasonal_gbj.xml", "sitemap_reviews_gbj.xml",
        "sitemap_bestfor_sdr.xml", "sitemap_workflow_sdr.xml", "sitemap_vs_sdr.xml",
        "sitemap_seasonal_sdr.xml", "sitemap_reviews_sdr.xml",
        "sitemap_bestfor_mjl.xml", "sitemap_workflow_mjl.xml", "sitemap_vs_mjl.xml",
        "sitemap_seasonal_mjl.xml", "sitemap_reviews_mjl.xml",
        "sitemap_bestfor_kex.xml", "sitemap_workflow_kex.xml", "sitemap_vs_kex.xml",
        "sitemap_seasonal_kex.xml", "sitemap_reviews_kex.xml",
        "sitemap_bestfor_mjz.xml", "sitemap_workflow_mjz.xml", "sitemap_vs_mjz.xml",
        "sitemap_seasonal_mjz.xml", "sitemap_reviews_mjz.xml",
        "sitemap_bestfor_srx.xml", "sitemap_workflow_srx.xml", "sitemap_vs_srx.xml",
        "sitemap_seasonal_srx.xml", "sitemap_reviews_srx.xml",
        "sitemap_bestfor_mjt.xml", "sitemap_workflow_mjt.xml", "sitemap_vs_mjt.xml",
        "sitemap_seasonal_mjt.xml", "sitemap_reviews_mjt.xml",
        "sitemap_bestfor_xka.xml", "sitemap_workflow_xka.xml", "sitemap_vs_xka.xml",
        "sitemap_seasonal_xka.xml", "sitemap_reviews_xka.xml",
        "sitemap_bestfor_agi.xml", "sitemap_workflow_agi.xml", "sitemap_vs_agi.xml",
        "sitemap_seasonal_agi.xml", "sitemap_reviews_agi.xml",
        "sitemap_bestfor_cps.xml", "sitemap_workflow_cps.xml", "sitemap_vs_cps.xml",
        "sitemap_seasonal_cps.xml", "sitemap_reviews_cps.xml",
        "sitemap_bestfor_tbl.xml", "sitemap_workflow_tbl.xml", "sitemap_vs_tbl.xml",
        "sitemap_seasonal_tbl.xml", "sitemap_reviews_tbl.xml",
        "sitemap_bestfor_agn.xml", "sitemap_workflow_agn.xml", "sitemap_vs_agn.xml",
        "sitemap_seasonal_agn.xml", "sitemap_reviews_agn.xml",
        "sitemap_bestfor_mta.xml", "sitemap_workflow_mta.xml", "sitemap_vs_mta.xml",
        "sitemap_seasonal_mta.xml", "sitemap_reviews_mta.xml",
        "sitemap_bestfor_obo.xml", "sitemap_workflow_obo.xml", "sitemap_vs_obo.xml",
        "sitemap_seasonal_obo.xml", "sitemap_reviews_obo.xml",
        "sitemap_bestfor_msm.xml", "sitemap_workflow_msm.xml", "sitemap_vs_msm.xml",
        "sitemap_seasonal_msm.xml", "sitemap_reviews_msm.xml",
        "sitemap_bestfor_bnj.xml", "sitemap_workflow_bnj.xml", "sitemap_vs_bnj.xml",
        "sitemap_seasonal_bnj.xml", "sitemap_reviews_bnj.xml",
        "sitemap_bestfor_bkn.xml", "sitemap_workflow_bkn.xml", "sitemap_vs_bkn.xml",
        "sitemap_seasonal_bkn.xml", "sitemap_reviews_bkn.xml",
        "sitemap_bestfor_bar.xml", "sitemap_workflow_bar.xml", "sitemap_vs_bar.xml",
        "sitemap_seasonal_bar.xml", "sitemap_reviews_bar.xml",
        "sitemap_bestfor_vmf.xml", "sitemap_workflow_vmf.xml", "sitemap_vs_vmf.xml",
        "sitemap_seasonal_vmf.xml", "sitemap_reviews_vmf.xml",
        "sitemap_bestfor_swg.xml", "sitemap_workflow_swg.xml", "sitemap_vs_swg.xml",
        "sitemap_seasonal_swg.xml", "sitemap_reviews_swg.xml",
        "sitemap_bestfor_ksh.xml", "sitemap_workflow_ksh.xml", "sitemap_vs_ksh.xml",
        "sitemap_seasonal_ksh.xml", "sitemap_reviews_ksh.xml",
        "sitemap_bestfor_pfl.xml", "sitemap_workflow_pfl.xml", "sitemap_vs_pfl.xml",
        "sitemap_seasonal_pfl.xml", "sitemap_reviews_pfl.xml",
        "sitemap_bestfor_rgn.xml", "sitemap_workflow_rgn.xml", "sitemap_vs_rgn.xml",
        "sitemap_seasonal_rgn.xml", "sitemap_reviews_rgn.xml",
        "sitemap_bestfor_egl.xml", "sitemap_workflow_egl.xml", "sitemap_vs_egl.xml",
        "sitemap_seasonal_egl.xml", "sitemap_reviews_egl.xml",
        "sitemap_bestfor_nrf.xml", "sitemap_workflow_nrf.xml", "sitemap_vs_nrf.xml",
        "sitemap_seasonal_nrf.xml", "sitemap_reviews_nrf.xml",
        "sitemap_bestfor_sxu.xml", "sitemap_workflow_sxu.xml", "sitemap_vs_sxu.xml",
        "sitemap_seasonal_sxu.xml", "sitemap_reviews_sxu.xml",
        "sitemap_bestfor_vls.xml", "sitemap_workflow_vls.xml", "sitemap_vs_vls.xml",
        "sitemap_seasonal_vls.xml", "sitemap_reviews_vls.xml",
        "sitemap_bestfor_wae.xml", "sitemap_workflow_wae.xml", "sitemap_vs_wae.xml",
        "sitemap_seasonal_wae.xml", "sitemap_reviews_wae.xml",
        "sitemap_bestfor_zea.xml", "sitemap_workflow_zea.xml", "sitemap_vs_zea.xml",
        "sitemap_seasonal_zea.xml", "sitemap_reviews_zea.xml",
        "sitemap_bestfor_wep.xml", "sitemap_workflow_wep.xml", "sitemap_vs_wep.xml",
        "sitemap_seasonal_wep.xml", "sitemap_reviews_wep.xml",
        "sitemap_bestfor_prv.xml", "sitemap_workflow_prv.xml", "sitemap_vs_prv.xml",
        "sitemap_seasonal_prv.xml", "sitemap_reviews_prv.xml",
        "sitemap_bestfor_oci.xml", "sitemap_workflow_oci.xml", "sitemap_vs_oci.xml",
        "sitemap_seasonal_oci.xml", "sitemap_reviews_oci.xml",
        "sitemap_bestfor_srd.xml", "sitemap_workflow_srd.xml", "sitemap_vs_srd.xml",
        "sitemap_seasonal_srd.xml", "sitemap_reviews_srd.xml",
        "sitemap_bestfor_fit.xml", "sitemap_workflow_fit.xml", "sitemap_vs_fit.xml",
        "sitemap_seasonal_fit.xml", "sitemap_reviews_fit.xml",
        "sitemap_bestfor_fkv.xml", "sitemap_workflow_fkv.xml", "sitemap_vs_fkv.xml",
        "sitemap_seasonal_fkv.xml", "sitemap_reviews_fkv.xml",
        "sitemap_bestfor_twd.xml", "sitemap_workflow_twd.xml", "sitemap_vs_twd.xml",
        "sitemap_seasonal_twd.xml", "sitemap_reviews_twd.xml",
        "sitemap_bestfor_jut.xml", "sitemap_workflow_jut.xml", "sitemap_vs_jut.xml",
        "sitemap_seasonal_jut.xml", "sitemap_reviews_jut.xml",
        "sitemap_bestfor_ovd.xml", "sitemap_workflow_ovd.xml", "sitemap_vs_ovd.xml",
        "sitemap_seasonal_ovd.xml", "sitemap_reviews_ovd.xml",
        "sitemap_bestfor_sju.xml", "sitemap_workflow_sju.xml", "sitemap_vs_sju.xml",
        "sitemap_seasonal_sju.xml", "sitemap_reviews_sju.xml",
        "sitemap_bestfor_sje.xml", "sitemap_workflow_sje.xml", "sitemap_vs_sje.xml",
        "sitemap_seasonal_sje.xml", "sitemap_reviews_sje.xml",
        "sitemap_bestfor_gutn.xml", "sitemap_workflow_gutn.xml", "sitemap_vs_gutn.xml",
        "sitemap_seasonal_gutn.xml", "sitemap_reviews_gutn.xml",
        "sitemap_bestfor_kjh.xml", "sitemap_workflow_kjh.xml", "sitemap_vs_kjh.xml",
        "sitemap_seasonal_kjh.xml", "sitemap_reviews_kjh.xml",
        "sitemap_bestfor_alt.xml", "sitemap_workflow_alt.xml", "sitemap_vs_alt.xml",
        "sitemap_seasonal_alt.xml", "sitemap_reviews_alt.xml",
        "sitemap_bestfor_cjs.xml", "sitemap_workflow_cjs.xml", "sitemap_vs_cjs.xml",
        "sitemap_seasonal_cjs.xml", "sitemap_reviews_cjs.xml",
        "sitemap_bestfor_dlg.xml", "sitemap_workflow_dlg.xml", "sitemap_vs_dlg.xml",
        "sitemap_seasonal_dlg.xml", "sitemap_reviews_dlg.xml",
        "sitemap_bestfor_kim.xml", "sitemap_workflow_kim.xml", "sitemap_vs_kim.xml",
        "sitemap_seasonal_kim.xml", "sitemap_reviews_kim.xml",
        "sitemap_bestfor_kdr.xml", "sitemap_workflow_kdr.xml", "sitemap_vs_kdr.xml",
        "sitemap_seasonal_kdr.xml", "sitemap_reviews_kdr.xml",
        "sitemap_bestfor_mrj.xml", "sitemap_workflow_mrj.xml", "sitemap_vs_mrj.xml",
        "sitemap_seasonal_mrj.xml", "sitemap_reviews_mrj.xml",
        "sitemap_bestfor_gas.xml", "sitemap_workflow_gas.xml", "sitemap_vs_gas.xml",
        "sitemap_seasonal_gas.xml", "sitemap_reviews_gas.xml",
        "sitemap_bestfor_kdq.xml", "sitemap_workflow_kdq.xml", "sitemap_vs_kdq.xml",
        "sitemap_seasonal_kdq.xml", "sitemap_reviews_kdq.xml",
        "sitemap_bestfor_anr.xml", "sitemap_workflow_anr.xml", "sitemap_vs_anr.xml",
        "sitemap_seasonal_anr.xml", "sitemap_reviews_anr.xml",
        "sitemap_bestfor_dry.xml", "sitemap_workflow_dry.xml", "sitemap_vs_dry.xml",
        "sitemap_seasonal_dry.xml", "sitemap_reviews_dry.xml",
        "sitemap_bestfor_unx.xml", "sitemap_workflow_unx.xml", "sitemap_vs_unx.xml",
        "sitemap_seasonal_unx.xml", "sitemap_reviews_unx.xml",
        "sitemap_bestfor_bfw.xml", "sitemap_workflow_bfw.xml", "sitemap_vs_bfw.xml",
        "sitemap_seasonal_bfw.xml", "sitemap_reviews_bfw.xml",
        "sitemap_bestfor_bjj.xml", "sitemap_workflow_bjj.xml", "sitemap_vs_bjj.xml",
        "sitemap_seasonal_bjj.xml", "sitemap_reviews_bjj.xml",
        "sitemap_bestfor_bns.xml", "sitemap_workflow_bns.xml", "sitemap_vs_bns.xml",
        "sitemap_seasonal_bns.xml", "sitemap_reviews_bns.xml",
        "sitemap_bestfor_mup.xml", "sitemap_workflow_mup.xml", "sitemap_vs_mup.xml",
        "sitemap_seasonal_mup.xml", "sitemap_reviews_mup.xml",
        "sitemap_bestfor_bhb.xml", "sitemap_workflow_bhb.xml", "sitemap_vs_bhb.xml",
        "sitemap_seasonal_bhb.xml", "sitemap_reviews_bhb.xml",
        "sitemap_bestfor_gom.xml", "sitemap_workflow_gom.xml", "sitemap_vs_gom.xml",
        "sitemap_seasonal_gom.xml", "sitemap_reviews_gom.xml",
        "sitemap_bestfor_ahr.xml", "sitemap_workflow_ahr.xml", "sitemap_vs_ahr.xml",
        "sitemap_seasonal_ahr.xml", "sitemap_reviews_ahr.xml",
        "sitemap_bestfor_dty.xml", "sitemap_workflow_dty.xml", "sitemap_vs_dty.xml",
        "sitemap_seasonal_dty.xml", "sitemap_reviews_dty.xml",
        "sitemap_bestfor_thl.xml", "sitemap_workflow_thl.xml", "sitemap_vs_thl.xml",
        "sitemap_seasonal_thl.xml", "sitemap_reviews_thl.xml",
        "sitemap_bestfor_pnb.xml", "sitemap_workflow_pnb.xml", "sitemap_vs_pnb.xml",
        "sitemap_seasonal_pnb.xml", "sitemap_reviews_pnb.xml",
        "sitemap_bestfor_prs.xml", "sitemap_workflow_prs.xml", "sitemap_vs_prs.xml",
        "sitemap_seasonal_prs.xml", "sitemap_reviews_prs.xml",
        "sitemap_bestfor_bal.xml", "sitemap_workflow_bal.xml", "sitemap_vs_bal.xml",
        "sitemap_seasonal_bal.xml", "sitemap_reviews_bal.xml",
        "sitemap_bestfor_kas.xml", "sitemap_workflow_kas.xml", "sitemap_vs_kas.xml",
        "sitemap_seasonal_kas.xml", "sitemap_reviews_kas.xml",
        "sitemap_bestfor_sdh.xml", "sitemap_workflow_sdh.xml", "sitemap_vs_sdh.xml",
        "sitemap_seasonal_sdh.xml", "sitemap_reviews_sdh.xml",
        "sitemap_bestfor_khw.xml", "sitemap_workflow_khw.xml", "sitemap_vs_khw.xml",
        "sitemap_seasonal_khw.xml", "sitemap_reviews_khw.xml",
        "sitemap_bestfor_bcc.xml", "sitemap_workflow_bcc.xml", "sitemap_vs_bcc.xml",
        "sitemap_seasonal_bcc.xml", "sitemap_reviews_bcc.xml",
        "sitemap_bestfor_bft.xml", "sitemap_workflow_bft.xml", "sitemap_vs_bft.xml",
        "sitemap_seasonal_bft.xml", "sitemap_reviews_bft.xml",
        "sitemap_bestfor_thq.xml", "sitemap_workflow_thq.xml", "sitemap_vs_thq.xml",
        "sitemap_seasonal_thq.xml", "sitemap_reviews_thq.xml",
        "sitemap_bestfor_the.xml", "sitemap_workflow_the.xml", "sitemap_vs_the.xml",
        "sitemap_seasonal_the.xml", "sitemap_reviews_the.xml",
        "sitemap_bestfor_kfr.xml", "sitemap_workflow_kfr.xml", "sitemap_vs_kfr.xml",
        "sitemap_seasonal_kfr.xml", "sitemap_reviews_kfr.xml",
        "sitemap_bestfor_gvr.xml", "sitemap_workflow_gvr.xml", "sitemap_vs_gvr.xml",
        "sitemap_seasonal_gvr.xml", "sitemap_reviews_gvr.xml",
        "sitemap_bestfor_lif.xml", "sitemap_workflow_lif.xml", "sitemap_vs_lif.xml",
        "sitemap_seasonal_lif.xml", "sitemap_reviews_lif.xml",
        "sitemap_bestfor_sck.xml", "sitemap_workflow_sck.xml", "sitemap_vs_sck.xml",
        "sitemap_seasonal_sck.xml", "sitemap_reviews_sck.xml",
        "sitemap_bestfor_tts.xml", "sitemap_workflow_tts.xml", "sitemap_vs_tts.xml",
        "sitemap_seasonal_tts.xml", "sitemap_reviews_tts.xml",
        "sitemap_bestfor_nod.xml", "sitemap_workflow_nod.xml", "sitemap_vs_nod.xml",
        "sitemap_seasonal_nod.xml", "sitemap_reviews_nod.xml",
        "sitemap_bestfor_sou.xml", "sitemap_workflow_sou.xml", "sitemap_vs_sou.xml",
        "sitemap_seasonal_sou.xml", "sitemap_reviews_sou.xml",
        "sitemap_bestfor_khb.xml", "sitemap_workflow_khb.xml", "sitemap_vs_khb.xml",
        "sitemap_seasonal_khb.xml", "sitemap_reviews_khb.xml",
        "sitemap_bestfor_ksw.xml", "sitemap_workflow_ksw.xml", "sitemap_vs_ksw.xml",
        "sitemap_seasonal_ksw.xml", "sitemap_reviews_ksw.xml",
        "sitemap_bestfor_rki.xml", "sitemap_workflow_rki.xml", "sitemap_vs_rki.xml",
        "sitemap_seasonal_rki.xml", "sitemap_reviews_rki.xml",
        "sitemap_bestfor_luz.xml", "sitemap_workflow_luz.xml", "sitemap_vs_luz.xml",
        "sitemap_seasonal_luz.xml", "sitemap_reviews_luz.xml",
        "sitemap_bestfor_mad.xml", "sitemap_workflow_mad.xml", "sitemap_vs_mad.xml",
        "sitemap_seasonal_mad.xml", "sitemap_reviews_mad.xml",
        "sitemap_bestfor_ban.xml", "sitemap_workflow_ban.xml", "sitemap_vs_ban.xml",
        "sitemap_seasonal_ban.xml", "sitemap_reviews_ban.xml",
        "sitemap_bestfor_bjn.xml", "sitemap_workflow_bjn.xml", "sitemap_vs_bjn.xml",
        "sitemap_seasonal_bjn.xml", "sitemap_reviews_bjn.xml",
        # Locale-specific intent sitemaps kept in the growth-engine copy
        # of this generator; listed here so the two stay one file. Every
        # entry is filtered by os.path.exists below, so unbuilt locales
        # never reach the published index.
        "sitemap_problems_ven.xml",
        "sitemap_problems_tso.xml",
        "sitemap_problems_ssw.xml",
        "sitemap_problems_loz.xml",
        "sitemap_problems_bho.xml",
        "sitemap_problems_en.xml",
        "sitemap_problems_en-GB.xml",
        "sitemap_problems_en-AU.xml",
        "sitemap_problems_en-CA.xml",
        "sitemap_problems_de-DE.xml",
        "sitemap_problems_fr-FR.xml",
        "sitemap_problems_es-ES.xml",
        "sitemap_problems_es-MX.xml",
        "sitemap_problems_it-IT.xml",
        "sitemap_problems_pt-BR.xml",
        "sitemap_problems_ja-JP.xml",
        "sitemap_problems_ko-KR.xml",
        "sitemap_problems_zh-Hant.xml",
        "sitemap_problems_th.xml",
        "sitemap_problems_vi.xml",
        "sitemap_problems_id.xml",
        "sitemap_problems_ms.xml",
        "sitemap_problems_tr.xml",
        "sitemap_problems_ru.xml",
        "sitemap_problems_pl.xml",
        "sitemap_problems_hi.xml",
        "sitemap_problems_ar-SA.xml",
        "sitemap_problems_nb-NO.xml",
        "sitemap_problems_fi.xml",
        "sitemap_problems_cs.xml",
        "sitemap_payonce_en.xml",
        "sitemap_payonce_en-GB.xml",
        "sitemap_payonce_en-AU.xml",
        "sitemap_payonce_en-CA.xml",
        "sitemap_payonce_de-DE.xml",
        "sitemap_payonce_fr-FR.xml",
        "sitemap_payonce_es-ES.xml",
        "sitemap_payonce_es-MX.xml",
        "sitemap_payonce_it-IT.xml",
        "sitemap_payonce_pt-BR.xml",
        "sitemap_payonce_ja-JP.xml",
        "sitemap_payonce_ko-KR.xml",
        "sitemap_payonce_zh-Hant.xml",
        "sitemap_payonce_th.xml",
        "sitemap_payonce_vi.xml",
        "sitemap_payonce_id.xml",
        "sitemap_payonce_ms.xml",
        "sitemap_payonce_tr.xml",
        "sitemap_payonce_ru.xml",
        "sitemap_payonce_pl.xml",
        "sitemap_payonce_hi.xml",
        "sitemap_payonce_ar-SA.xml",
        "sitemap_payonce_nb-NO.xml",
        "sitemap_payonce_fi.xml",
        "sitemap_payonce_cs.xml",
        "sitemap_bestfor_zh-Hans.xml",
        "sitemap_workflow_zh-Hans.xml",
        "sitemap_vs_zh-Hans.xml",
        "sitemap_seasonal_zh-Hans.xml",
        "sitemap_reviews_zh-Hans.xml",
        "sitemap_bestfor_sv.xml",
        "sitemap_workflow_sv.xml",
        "sitemap_vs_sv.xml",
        "sitemap_seasonal_sv.xml",
        "sitemap_reviews_sv.xml",
        "sitemap_bestfor_da.xml",
        "sitemap_workflow_da.xml",
        "sitemap_vs_da.xml",
        "sitemap_seasonal_da.xml",
        "sitemap_reviews_da.xml",
        "sitemap_problems_zh-Hans.xml",
        "sitemap_problems_sv.xml",
        "sitemap_problems_da.xml",
        "sitemap_payonce_zh-Hans.xml",
        "sitemap_payonce_sv.xml",
        "sitemap_payonce_da.xml",
        "sitemap_noaccount_en.xml",
        "sitemap_noaccount_en-GB.xml",
        "sitemap_noaccount_en-AU.xml",
        "sitemap_noaccount_en-CA.xml",
        "sitemap_noaccount_de-DE.xml",
        "sitemap_noaccount_fr-FR.xml",
        "sitemap_noaccount_es-ES.xml",
        "sitemap_noaccount_es-MX.xml",
        "sitemap_noaccount_it-IT.xml",
        "sitemap_noaccount_pt-BR.xml",
        "sitemap_noaccount_ja-JP.xml",
        "sitemap_noaccount_ko-KR.xml",
        "sitemap_noaccount_zh-Hant.xml",
        "sitemap_noaccount_zh-Hans.xml",
        "sitemap_noaccount_th.xml",
        "sitemap_noaccount_vi.xml",
        "sitemap_noaccount_id.xml",
        "sitemap_noaccount_ms.xml",
        "sitemap_noaccount_tr.xml",
        "sitemap_noaccount_ru.xml",
        "sitemap_noaccount_pl.xml",
        "sitemap_noaccount_hi.xml",
        "sitemap_noaccount_ar-SA.xml",
        "sitemap_noaccount_sv.xml",
        "sitemap_noaccount_da.xml",
        "sitemap_noaccount_nb-NO.xml",
        "sitemap_noaccount_fi.xml",
        "sitemap_noaccount_cs.xml",
        "sitemap_family_en.xml",
        "sitemap_family_en-GB.xml",
        "sitemap_family_en-AU.xml",
        "sitemap_family_en-CA.xml",
        "sitemap_family_de-DE.xml",
        "sitemap_family_fr-FR.xml",
        "sitemap_family_es-ES.xml",
        "sitemap_family_es-MX.xml",
        "sitemap_family_it-IT.xml",
        "sitemap_family_pt-BR.xml",
        "sitemap_family_ja-JP.xml",
        "sitemap_family_ko-KR.xml",
        "sitemap_family_zh-Hant.xml",
        "sitemap_family_zh-Hans.xml",
        "sitemap_family_th.xml",
        "sitemap_family_vi.xml",
        "sitemap_family_id.xml",
        "sitemap_family_ms.xml",
        "sitemap_family_tr.xml",
        "sitemap_family_ru.xml",
        "sitemap_family_pl.xml",
        "sitemap_family_hi.xml",
        "sitemap_family_ar-SA.xml",
        "sitemap_family_sv.xml",
        "sitemap_family_da.xml",
        "sitemap_family_nb-NO.xml",
        "sitemap_family_fi.xml",
        "sitemap_family_cs.xml",
        "sitemap_gifting_en.xml",
        "sitemap_gifting_en-GB.xml",
        "sitemap_gifting_en-AU.xml",
        "sitemap_gifting_en-CA.xml",
        "sitemap_gifting_de-DE.xml",
        "sitemap_gifting_fr-FR.xml",
        "sitemap_gifting_es-ES.xml",
        "sitemap_gifting_es-MX.xml",
        "sitemap_gifting_it-IT.xml",
        "sitemap_gifting_pt-BR.xml",
        "sitemap_gifting_ja-JP.xml",
        "sitemap_gifting_ko-KR.xml",
        "sitemap_gifting_zh-Hant.xml",
        "sitemap_gifting_zh-Hans.xml",
        "sitemap_gifting_th.xml",
        "sitemap_gifting_vi.xml",
        "sitemap_gifting_id.xml",
        "sitemap_gifting_ms.xml",
        "sitemap_gifting_tr.xml",
        "sitemap_gifting_ru.xml",
        "sitemap_gifting_pl.xml",
        "sitemap_gifting_hi.xml",
        "sitemap_gifting_ar-SA.xml",
        "sitemap_gifting_sv.xml",
        "sitemap_gifting_da.xml",
        "sitemap_gifting_nb-NO.xml",
        "sitemap_gifting_fi.xml",
        "sitemap_gifting_cs.xml",
        "sitemap_switching_en.xml",
        "sitemap_switching_en-GB.xml",
        "sitemap_switching_en-AU.xml",
        "sitemap_switching_en-CA.xml",
        "sitemap_switching_de-DE.xml",
        "sitemap_switching_fr-FR.xml",
        "sitemap_switching_es-ES.xml",
        "sitemap_switching_es-MX.xml",
        "sitemap_switching_it-IT.xml",
        "sitemap_switching_pt-BR.xml",
        "sitemap_switching_ja-JP.xml",
        "sitemap_switching_ko-KR.xml",
        "sitemap_switching_zh-Hant.xml",
        "sitemap_switching_zh-Hans.xml",
        "sitemap_switching_th.xml",
        "sitemap_switching_vi.xml",
        "sitemap_switching_id.xml",
        "sitemap_switching_ms.xml",
        "sitemap_switching_tr.xml",
        "sitemap_switching_ru.xml",
        "sitemap_switching_pl.xml",
        "sitemap_switching_hi.xml",
        "sitemap_switching_ar-SA.xml",
        "sitemap_switching_sv.xml",
        "sitemap_switching_da.xml",
        "sitemap_switching_nb-NO.xml",
        "sitemap_switching_fi.xml",
        "sitemap_switching_cs.xml",
        "sitemap_choose_en.xml",
        "sitemap_choose_en-GB.xml",
        "sitemap_choose_en-AU.xml",
        "sitemap_choose_en-CA.xml",
        "sitemap_choose_de-DE.xml",
        "sitemap_choose_fr-FR.xml",
        "sitemap_choose_es-ES.xml",
        "sitemap_choose_es-MX.xml",
        "sitemap_choose_it-IT.xml",
        "sitemap_choose_pt-BR.xml",
        "sitemap_choose_ja-JP.xml",
        "sitemap_choose_ko-KR.xml",
        "sitemap_choose_zh-Hant.xml",
        "sitemap_choose_zh-Hans.xml",
        "sitemap_choose_th.xml",
        "sitemap_choose_vi.xml",
        "sitemap_choose_id.xml",
        "sitemap_choose_ms.xml",
        "sitemap_choose_tr.xml",
        "sitemap_choose_ru.xml",
        "sitemap_choose_pl.xml",
        "sitemap_choose_hi.xml",
        "sitemap_choose_ar-SA.xml",
        "sitemap_choose_sv.xml",
        "sitemap_choose_da.xml",
        "sitemap_choose_nb-NO.xml",
        "sitemap_choose_fi.xml",
        "sitemap_choose_cs.xml",
        "sitemap_problems_mag.xml",
        "sitemap_problems_new.xml",
        "sitemap_problems_mai.xml",
        "sitemap_problems_raj.xml",
        "sitemap_problems_mah.xml",
        "sitemap_problems_tvl.xml",
        "sitemap_problems_sm.xml",
        "sitemap_problems_nah.xml",
    ):
        if os.path.exists(os.path.join(PAGES, filename)):
            lines.append(f"- {SITE}/{filename}")
    lines.extend(
        f"- WebSub real-time hub: {hub} "
        "(topic URLs are advertised inside all three feeds)"
        for hub in WEBSUB_HUBS
    )
    lines += [
        f"- rssCloud subscriber registration: {RSSCLOUD_NOTIFY_URL}",
        f"- rssCloud WebSub hub: {RSSCLOUD_WEBSUB_HUB}",
    ]
    lines += portfolio_cost_calculator_lines(full=True)
    lines += app_install_decision_route_lines(full=True)
    lines += localized_llms_discovery_lines()
    lines.append("")
    return "\n".join(lines)


def build_robots():
    out = [
        "# AI assistants and search crawlers are welcome to index and cite this site.",
        f"# Localized AI app catalogs: {SITE}/llms/index.json",
        "",
    ]
    for bot in AI_BOTS:
        out.append(f"User-agent: {bot}")
        out.append("Allow: /")
        out.append("")
    out += ["User-agent: *", "Allow: /", "",
            f"Sitemap: {SITE}/sitemap.xml",
            f"Sitemap: {SITE}/sitemap_alternatives.xml",
            f"Sitemap: {SITE}/sitemap_answers.xml",
            f"Sitemap: {SITE}/sitemap_guides.xml",
            f"Sitemap: {SITE}/sitemap_apps.xml",
            f"Sitemap: {SITE}/sitemap_stories.xml",
            f"Sitemap: {SITE}/sitemap_images.xml",
            f"Sitemap: {SITE}/{PUBLISHER_INTENT_VISUALS_SITEMAP}",
            f"Sitemap: {SITE}/{app_video_lessons.SITEMAP_NAME}",
            f"Sitemap: {SITE}/sitemap_linkset.xml",
            f"Sitemap: {SITE}/sitemap_oembed.xml",
            f"Sitemap: {SITE}/sitemap_llms.xml",
            f"Sitemap: {SITE}/{app_install_decision_routes.SITEMAP_NAME}",
            f"Sitemap: {SITE}/sitemap_hubs.xml",
            f"Sitemap: {SITE}/sitemap_topic_hubs.xml",
            f"Sitemap: {SITE}/sitemap_review_hubs.xml",
            f"Sitemap: {SITE}/sitemap_tools.xml",
            f"Sitemap: {SITE}/sitemap_data.xml",
            f"Sitemap: {SITE}/sitemap_api.xml",
            f"Sitemap: {SITE}/{portfolio_offer_catalog.SITEMAP_NAME}",
            f"Sitemap: {SITE}/sitemap_swap.xml",
            f"Sitemap: {SITE}/sitemap_opds.xml",
            f"Sitemap: {SITE}/sitemap_ro_crate.xml",
            f"Sitemap: {SITE}/sitemap_anki.xml",
            f"Sitemap: {SITE}/sitemap_vocab.xml",
            f"Sitemap: {SITE}/sitemap_croissant.xml",
            f"Sitemap: {SITE}/sitemap_datapackage.xml",
            f"Sitemap: {SITE}/sitemap_csvw.xml",
            f"Sitemap: {SITE}/sitemap_bagit.xml",
            f"Sitemap: {SITE}/sitemap_ocfl.xml",
            f"Sitemap: {SITE}/sitemap_iiif.xml",
            f"Sitemap: {SITE}/sitemap_ro_crate_bopomofo.xml",
            f"Sitemap: {SITE}/sitemap_mets_premis.xml",
            f"Sitemap: {SITE}/sitemap_ldes.xml",
            f"Sitemap: {SITE}/sitemap_ore.xml",
            f"Sitemap: {SITE}/sitemap_lms.xml",
            f"Sitemap: {SITE}/sitemap_epub.xml",
            f"Sitemap: {SITE}/sitemap_library_catalog.xml",
            f"Sitemap: {SITE}/sitemap_oer_metadata.xml",
            f"Sitemap: {SITE}/sitemap_dcat.xml",
            f"Sitemap: {SITE}/sitemap_resourcesync.xml",
            f"Sitemap: {SITE}/resourcesync/resourcelist.xml",
            f"Sitemap: {SITE}/sitemap_index.xml", ""]
    return "\n".join(out)


SITEMAP_ENTRY_RE = re.compile(
    r"<(?:[A-Za-z_][\w.-]*:)?(?:url|sitemap)(?:\s|>)",
    re.IGNORECASE,
)


def sitemap_has_entries(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8", errors="ignore") as sitemap:
            tail = ""
            while chunk := sitemap.read(65536):
                source = tail + chunk
                if SITEMAP_ENTRY_RE.search(source):
                    return True
                tail = source[-128:]
    except OSError:
        return False
    return False


def build_sitemap_index():
    maps = ["sitemap.xml", "sitemap_alternatives.xml", "sitemap_answers.xml", "sitemap_guides.xml",
            "sitemap_apps.xml",
            "sitemap_stories.xml", "sitemap_images.xml", "sitemap_linkset.xml",
            PUBLISHER_INTENT_VISUALS_SITEMAP,
            app_video_lessons.SITEMAP_NAME,
            "sitemap_oembed.xml", "sitemap_llms.xml",
            app_install_decision_routes.SITEMAP_NAME,
            "sitemap_hubs.xml", "sitemap_topic_hubs.xml", "sitemap_review_hubs.xml", "sitemap_tools.xml",
            "sitemap_data.xml", "sitemap_api.xml",
            portfolio_offer_catalog.SITEMAP_NAME, "sitemap_swap.xml"]
    maps.extend([
        "sitemap_opds.xml",
        "sitemap_ro_crate.xml",
        "sitemap_anki.xml",
        "sitemap_vocab.xml",
        "sitemap_croissant.xml",
        "sitemap_datapackage.xml",
        "sitemap_csvw.xml",
        "sitemap_bagit.xml",
        "sitemap_ocfl.xml",
        "sitemap_iiif.xml",
        "sitemap_ro_crate_bopomofo.xml",
        "sitemap_mets_premis.xml",
        "sitemap_ldes.xml",
        "sitemap_ore.xml",
        "sitemap_lms.xml",
        "sitemap_epub.xml",
        "sitemap_library_catalog.xml",
        "sitemap_oer_metadata.xml",
        "sitemap_dcat.xml",
        "sitemap_resourcesync.xml",
        "resourcesync/resourcelist.xml",
        "sitemap_cross.xml",
        "sitemap_seasonal.xml",
        "sitemap_scenario.xml",
        "sitemap_persona.xml",
        "sitemap_seasonal_zh-Hant.xml",
        "sitemap_seasonal_ja.xml",
        "sitemap_seasonal_ko.xml",
        "sitemap_seasonal_es-ES.xml",
        "sitemap_persona_zh-Hant.xml",
        "sitemap_persona_ja.xml",
        "sitemap_persona_ko.xml",
        "sitemap_persona_es-ES.xml",
        "sitemap_persona_fr-FR.xml",
        "sitemap_persona_de-DE.xml",
        "sitemap_persona_pt-BR.xml",
        "sitemap_bundle.xml",
        "sitemap_reviews.xml",
        "sitemap_persona_ms.xml",
        "sitemap_reviews_zh-Hant.xml",
        "sitemap_reviews_ja.xml",
        "sitemap_tutorials.xml",
        "sitemap_seasonal_pt-BR.xml",
        "sitemap_reviews_kids_en.xml",
        "sitemap_persona_vi.xml",
        "sitemap_persona_id.xml",
        "sitemap_persona_tr.xml",
        "sitemap_persona_th.xml",
        "sitemap_seasonal_vi.xml",
        "sitemap_seasonal_id.xml",
        "sitemap_seasonal_tr.xml",
        "sitemap_persona_hi.xml",
        "sitemap_reviews_ko.xml",
        "sitemap_persona_zh-CN.xml",
        "sitemap_tutorials_zh-Hant.xml",
        "sitemap_tutorials_ja.xml",
        "sitemap_tutorials_ko.xml",
        "sitemap_tutorials_es-ES.xml",
        "sitemap_persona_nl-NL.xml",
        "sitemap_seasonal_zh-CN.xml",
        "sitemap_tutorials_fr-FR.xml",
        "sitemap_persona_de-DE.xml",
        "sitemap_tutorials_it-IT.xml",
        "sitemap_persona_pl-PL.xml",
        "sitemap_persona_sv-SE.xml",
        "sitemap_bestfor_en.xml",
        "sitemap_persona_ar.xml",
        "sitemap_persona_da-DK.xml",
        "sitemap_persona_nb-NO.xml",
        "sitemap_bestfor_ja.xml",
        "sitemap_bestfor_ko.xml",
        "sitemap_workflow_en.xml",
        "sitemap_persona_fi-FI.xml",
        "sitemap_tutorials_zh-CN.xml",
        "sitemap_workflow_ja.xml",
        "sitemap_workflow_ko.xml",
        "sitemap_bestfor_es-ES.xml",
        "sitemap_bestfor_fr-FR.xml",
        "sitemap_bestfor_de-DE.xml",
        "sitemap_vs_en.xml",
        "sitemap_tutorials_de-DE.xml",
        "sitemap_bestfor_it-IT.xml",
        "sitemap_bestfor_zh-CN.xml",
        "sitemap_bestfor_pt-BR.xml",
        "sitemap_bestfor_zh-Hant.xml",
        "sitemap_seasonal_zh-Hant.xml",
        "sitemap_vs_de-DE.xml",
        "sitemap_vs_es-ES.xml",
        "sitemap_vs_fr-FR.xml",
        "sitemap_workflow_de-DE.xml",
        "sitemap_workflow_es-ES.xml",
        "sitemap_workflow_fr-FR.xml",
        "sitemap_tutorials_pt-BR.xml",
        "sitemap_workflow_it-IT.xml",
        "sitemap_vs_it-IT.xml",
        "sitemap_workflow_zh-CN.xml",
        "sitemap_workflow_zh-Hant.xml",
        "sitemap_persona_pt-BR.xml",
        "sitemap_vs_zh-CN.xml",
        "sitemap_vs_zh-Hant.xml",
        "sitemap_workflow_pt-BR.xml",
        "sitemap_vs_ja-JP.xml",
        "sitemap_vs_ko-KR.xml",
        "sitemap_vs_pt-BR.xml",
        "sitemap_persona_zh-CN.xml",
        "sitemap_persona_zh-Hant.xml",
        "sitemap_bestfor_vi.xml",
        "sitemap_workflow_vi.xml",
        "sitemap_vs_vi.xml",
        "sitemap_bestfor_th.xml",
        "sitemap_bestfor_id.xml",
        "sitemap_workflow_th.xml",
        "sitemap_workflow_id.xml",
        "sitemap_bestfor_tr.xml",
        "sitemap_workflow_tr.xml",
        "sitemap_vs_tr.xml",
        "sitemap_vs_th.xml",
        "sitemap_vs_id.xml",
        "sitemap_seasonal_ja-JP.xml",
        "sitemap_seasonal_ko-KR.xml",
        "sitemap_seasonal_th.xml",
        "sitemap_bestfor_nl-NL.xml",
        "sitemap_vs_nl-NL.xml",
        "sitemap_workflow_nl-NL.xml",
        "sitemap_seasonal_de-DE.xml",
        "sitemap_seasonal_fr-FR.xml",
        "sitemap_seasonal_nl-NL.xml",
        "sitemap_reviews_es-ES.xml",
        "sitemap_reviews_pt-BR.xml",
        "sitemap_seasonal_it-IT.xml",
        "sitemap_reviews_it-IT.xml",
        "sitemap_reviews_de-DE.xml",
        "sitemap_reviews_fr-FR.xml",
        "sitemap_bestfor_sv-SE.xml",
        "sitemap_workflow_sv-SE.xml",
        "sitemap_vs_sv-SE.xml",
        "sitemap_seasonal_sv-SE.xml",
        "sitemap_bestfor_da-DK.xml",
        "sitemap_workflow_da-DK.xml",
        "sitemap_vs_da-DK.xml",
        "sitemap_seasonal_da-DK.xml",
        "sitemap_bestfor_nb-NO.xml",
        "sitemap_workflow_nb-NO.xml",
        "sitemap_vs_nb-NO.xml",
        "sitemap_seasonal_nb-NO.xml",
        "sitemap_bestfor_pl.xml",
        "sitemap_workflow_pl.xml",
        "sitemap_vs_pl.xml",
        "sitemap_seasonal_pl.xml",
        "sitemap_reviews_nl-NL.xml",
        "sitemap_reviews_vi.xml",
        "sitemap_reviews_tr.xml",
        "sitemap_reviews_th.xml",
        "sitemap_reviews_id.xml",
        "sitemap_reviews_ko-KR.xml",
        "sitemap_reviews_ja-JP.xml",
        "sitemap_bestfor_ms.xml",
        "sitemap_workflow_ms.xml",
        "sitemap_vs_ms.xml",
        "sitemap_seasonal_ms.xml",
        "sitemap_bestfor_hi.xml",
        "sitemap_workflow_hi.xml",
        "sitemap_vs_hi.xml",
        "sitemap_seasonal_hi.xml",
        "sitemap_bestfor_ko-KR.xml",
        "sitemap_workflow_ko-KR.xml",
        "sitemap_bestfor_ja-JP.xml",
        "sitemap_workflow_ja-JP.xml",
        "sitemap_bestfor_ar-SA.xml",
        "sitemap_workflow_ar-SA.xml",
        "sitemap_vs_ar-SA.xml",
        "sitemap_seasonal_ar-SA.xml",
        "sitemap_reviews_ms.xml",
        "sitemap_reviews_ar-SA.xml",
        "sitemap_bestfor_es-MX.xml",
        "sitemap_workflow_es-MX.xml",
        "sitemap_vs_es-MX.xml",
        "sitemap_seasonal_es-MX.xml",
        "sitemap_reviews_es-MX.xml",
        "sitemap_reviews_zh-CN.xml",
        "sitemap_bestfor_ru.xml",
        "sitemap_workflow_ru.xml",
        "sitemap_vs_ru.xml",
        "sitemap_seasonal_ru.xml",
        "sitemap_reviews_ru.xml",
        "sitemap_bestfor_pt-PT.xml",
        "sitemap_workflow_pt-PT.xml",
        "sitemap_vs_pt-PT.xml",
        "sitemap_seasonal_pt-PT.xml",
        "sitemap_reviews_pt-PT.xml",
        "sitemap_reviews_sv-SE.xml",
        "sitemap_reviews_da-DK.xml",
        "sitemap_reviews_nb-NO.xml",
        "sitemap_reviews_pl.xml",
        "sitemap_bestfor_uk.xml",
        "sitemap_workflow_uk.xml",
        "sitemap_vs_uk.xml",
        "sitemap_seasonal_uk.xml",
        "sitemap_reviews_uk.xml",
        "sitemap_bestfor_cs.xml",
        "sitemap_workflow_cs.xml",
        "sitemap_vs_cs.xml",
        "sitemap_seasonal_cs.xml",
        "sitemap_reviews_cs.xml",
        "sitemap_bestfor_ro.xml",
        "sitemap_workflow_ro.xml",
        "sitemap_vs_ro.xml",
        "sitemap_seasonal_ro.xml",
        "sitemap_reviews_ro.xml",
        "sitemap_bestfor_hu.xml",
        "sitemap_workflow_hu.xml",
        "sitemap_vs_hu.xml",
        "sitemap_seasonal_hu.xml",
        "sitemap_reviews_hu.xml",
        "sitemap_bestfor_el.xml",
        "sitemap_workflow_el.xml",
        "sitemap_vs_el.xml",
        "sitemap_seasonal_el.xml",
        "sitemap_reviews_el.xml",
        "sitemap_bestfor_fi.xml",
        "sitemap_workflow_fi.xml",
        "sitemap_vs_fi.xml",
        "sitemap_seasonal_fi.xml",
        "sitemap_reviews_fi.xml",
        "sitemap_bestfor_bg.xml",
        "sitemap_workflow_bg.xml",
        "sitemap_vs_bg.xml",
        "sitemap_seasonal_bg.xml",
        "sitemap_reviews_bg.xml",
        "sitemap_vs_ko.xml",
        "sitemap_vs_ja.xml",
        "sitemap_seasonal_en.xml",
        "sitemap_reviews_en.xml",
        "sitemap_bestfor_hr.xml",
        "sitemap_workflow_hr.xml",
        "sitemap_vs_hr.xml",
        "sitemap_seasonal_hr.xml",
        "sitemap_reviews_hr.xml",
        "sitemap_bestfor_sk.xml",
        "sitemap_workflow_sk.xml",
        "sitemap_vs_sk.xml",
        "sitemap_seasonal_sk.xml",
        "sitemap_reviews_sk.xml",
        "sitemap_bestfor_ca.xml",
        "sitemap_workflow_ca.xml",
        "sitemap_vs_ca.xml",
        "sitemap_seasonal_ca.xml",
        "sitemap_reviews_ca.xml",
        "sitemap_bestfor_he.xml",
        "sitemap_workflow_he.xml",
        "sitemap_vs_he.xml",
        "sitemap_seasonal_he.xml",
        "sitemap_reviews_he.xml",
        "sitemap_bestfor_sr.xml",
        "sitemap_workflow_sr.xml",
        "sitemap_vs_sr.xml",
        "sitemap_seasonal_sr.xml",
        "sitemap_reviews_sr.xml",
        "sitemap_bestfor_lt.xml",
        "sitemap_workflow_lt.xml",
        "sitemap_vs_lt.xml",
        "sitemap_seasonal_lt.xml",
        "sitemap_reviews_lt.xml",
        "sitemap_bestfor_lv.xml",
        "sitemap_workflow_lv.xml",
        "sitemap_vs_lv.xml",
        "sitemap_seasonal_lv.xml",
        "sitemap_reviews_lv.xml",
        "sitemap_bestfor_et.xml",
        "sitemap_workflow_et.xml",
        "sitemap_vs_et.xml",
        "sitemap_seasonal_et.xml",
        "sitemap_reviews_et.xml",
        "sitemap_bestfor_sl.xml",
        "sitemap_workflow_sl.xml",
        "sitemap_vs_sl.xml",
        "sitemap_seasonal_sl.xml",
        "sitemap_reviews_sl.xml",
        "sitemap_bestfor_af.xml",
        "sitemap_workflow_af.xml",
        "sitemap_vs_af.xml",
        "sitemap_seasonal_af.xml",
        "sitemap_reviews_af.xml",
        "sitemap_bestfor_sw.xml",
        "sitemap_workflow_sw.xml",
        "sitemap_vs_sw.xml",
        "sitemap_seasonal_sw.xml",
        "sitemap_reviews_sw.xml",
        "sitemap_bestfor_cy.xml",
        "sitemap_workflow_cy.xml",
        "sitemap_vs_cy.xml",
        "sitemap_seasonal_cy.xml",
        "sitemap_reviews_cy.xml",
        "sitemap_bestfor_sq.xml",
        "sitemap_workflow_sq.xml",
        "sitemap_vs_sq.xml",
        "sitemap_seasonal_sq.xml",
        "sitemap_reviews_sq.xml",
        "sitemap_bestfor_bg.xml",
        "sitemap_workflow_bg.xml",
        "sitemap_vs_bg.xml",
        "sitemap_seasonal_bg.xml",
        "sitemap_reviews_bg.xml",
        "sitemap_bestfor_mk.xml",
        "sitemap_workflow_mk.xml",
        "sitemap_vs_mk.xml",
        "sitemap_seasonal_mk.xml",
        "sitemap_reviews_mk.xml",
        "sitemap_bestfor_bs.xml",
        "sitemap_workflow_bs.xml",
        "sitemap_vs_bs.xml",
        "sitemap_seasonal_bs.xml",
        "sitemap_reviews_bs.xml",
        "sitemap_bestfor_fa.xml",
        "sitemap_workflow_fa.xml",
        "sitemap_vs_fa.xml",
        "sitemap_seasonal_fa.xml",
        "sitemap_reviews_fa.xml",
        "sitemap_bestfor_ur.xml",
        "sitemap_workflow_ur.xml",
        "sitemap_vs_ur.xml",
        "sitemap_seasonal_ur.xml",
        "sitemap_reviews_ur.xml",
        "sitemap_bestfor_hi.xml",
        "sitemap_workflow_hi.xml",
        "sitemap_vs_hi.xml",
        "sitemap_seasonal_hi.xml",
        "sitemap_reviews_hi.xml",
        "sitemap_bestfor_bn.xml",
        "sitemap_workflow_bn.xml",
        "sitemap_vs_bn.xml",
        "sitemap_seasonal_bn.xml",
        "sitemap_reviews_bn.xml",
        "sitemap_bestfor_ta.xml",
        "sitemap_workflow_ta.xml",
        "sitemap_vs_ta.xml",
        "sitemap_seasonal_ta.xml",
        "sitemap_reviews_ta.xml",
        "sitemap_bestfor_te.xml",
        "sitemap_workflow_te.xml",
        "sitemap_vs_te.xml",
        "sitemap_seasonal_te.xml",
        "sitemap_reviews_te.xml",
        "sitemap_bestfor_mr.xml",
        "sitemap_workflow_mr.xml",
        "sitemap_vs_mr.xml",
        "sitemap_seasonal_mr.xml",
        "sitemap_reviews_mr.xml",
        "sitemap_bestfor_gu.xml",
        "sitemap_workflow_gu.xml",
        "sitemap_vs_gu.xml",
        "sitemap_seasonal_gu.xml",
        "sitemap_reviews_gu.xml",
        "sitemap_bestfor_pa.xml",
        "sitemap_workflow_pa.xml",
        "sitemap_vs_pa.xml",
        "sitemap_seasonal_pa.xml",
        "sitemap_reviews_pa.xml",
        "sitemap_bestfor_ne.xml",
        "sitemap_workflow_ne.xml",
        "sitemap_vs_ne.xml",
        "sitemap_seasonal_ne.xml",
        "sitemap_reviews_ne.xml",
        "sitemap_bestfor_si.xml",
        "sitemap_workflow_si.xml",
        "sitemap_vs_si.xml",
        "sitemap_seasonal_si.xml",
        "sitemap_reviews_si.xml",
        "sitemap_bestfor_my.xml",
        "sitemap_workflow_my.xml",
        "sitemap_vs_my.xml",
        "sitemap_seasonal_my.xml",
        "sitemap_reviews_my.xml",
        "sitemap_bestfor_km.xml",
        "sitemap_workflow_km.xml",
        "sitemap_vs_km.xml",
        "sitemap_seasonal_km.xml",
        "sitemap_reviews_km.xml",
        # lo:
        "sitemap_bestfor_lo.xml",
        "sitemap_workflow_lo.xml",
        "sitemap_vs_lo.xml",
        "sitemap_seasonal_lo.xml",
        "sitemap_reviews_lo.xml",
        # am:
        "sitemap_bestfor_am.xml",
        "sitemap_workflow_am.xml",
        "sitemap_vs_am.xml",
        "sitemap_seasonal_am.xml",
        "sitemap_reviews_am.xml",
        # yo:
        "sitemap_bestfor_yo.xml",
        "sitemap_workflow_yo.xml",
        "sitemap_vs_yo.xml",
        "sitemap_seasonal_yo.xml",
        "sitemap_reviews_yo.xml",
        # ha:
        "sitemap_bestfor_ha.xml",
        "sitemap_workflow_ha.xml",
        "sitemap_vs_ha.xml",
        "sitemap_seasonal_ha.xml",
        "sitemap_reviews_ha.xml",
        # ig:
        "sitemap_bestfor_ig.xml",
        "sitemap_workflow_ig.xml",
        "sitemap_vs_ig.xml",
        "sitemap_seasonal_ig.xml",
        "sitemap_reviews_ig.xml",
        # tl:
        "sitemap_bestfor_tl.xml",
        "sitemap_workflow_tl.xml",
        "sitemap_vs_tl.xml",
        "sitemap_seasonal_tl.xml",
        "sitemap_reviews_tl.xml",
        # uz:
        "sitemap_bestfor_uz.xml",
        "sitemap_workflow_uz.xml",
        "sitemap_vs_uz.xml",
        "sitemap_seasonal_uz.xml",
        "sitemap_reviews_uz.xml",
        # az:
        "sitemap_bestfor_az.xml",
        "sitemap_workflow_az.xml",
        "sitemap_vs_az.xml",
        "sitemap_seasonal_az.xml",
        "sitemap_reviews_az.xml",
        # ka:
        "sitemap_bestfor_ka.xml",
        "sitemap_workflow_ka.xml",
        "sitemap_vs_ka.xml",
        "sitemap_seasonal_ka.xml",
        "sitemap_reviews_ka.xml",
        # hy:
        "sitemap_bestfor_hy.xml",
        "sitemap_workflow_hy.xml",
        "sitemap_vs_hy.xml",
        "sitemap_seasonal_hy.xml",
        "sitemap_reviews_hy.xml",
        # mn:
        "sitemap_bestfor_mn.xml",
        "sitemap_workflow_mn.xml",
        "sitemap_vs_mn.xml",
        "sitemap_seasonal_mn.xml",
        "sitemap_reviews_mn.xml",
        # kk:
        "sitemap_bestfor_kk.xml",
        "sitemap_workflow_kk.xml",
        "sitemap_vs_kk.xml",
        "sitemap_seasonal_kk.xml",
        "sitemap_reviews_kk.xml",
        # so:
        "sitemap_bestfor_so.xml",
        "sitemap_workflow_so.xml",
        "sitemap_vs_so.xml",
        "sitemap_seasonal_so.xml",
        "sitemap_reviews_so.xml",
        # om:
        "sitemap_bestfor_om.xml",
        "sitemap_workflow_om.xml",
        "sitemap_vs_om.xml",
        "sitemap_seasonal_om.xml",
        "sitemap_reviews_om.xml",
        # ky:
        "sitemap_bestfor_ky.xml",
        "sitemap_workflow_ky.xml",
        "sitemap_vs_ky.xml",
        "sitemap_seasonal_ky.xml",
        "sitemap_reviews_ky.xml",
        # tg:
        "sitemap_bestfor_tg.xml",
        "sitemap_workflow_tg.xml",
        "sitemap_vs_tg.xml",
        "sitemap_seasonal_tg.xml",
        "sitemap_reviews_tg.xml",
        # zu:
        "sitemap_bestfor_zu.xml",
        "sitemap_workflow_zu.xml",
        "sitemap_vs_zu.xml",
        "sitemap_seasonal_zu.xml",
        "sitemap_reviews_zu.xml",
        # xh:
        "sitemap_bestfor_xh.xml",
        "sitemap_workflow_xh.xml",
        "sitemap_vs_xh.xml",
        "sitemap_seasonal_xh.xml",
        "sitemap_reviews_xh.xml",
        # ps:
        "sitemap_bestfor_ps.xml",
        "sitemap_workflow_ps.xml",
        "sitemap_vs_ps.xml",
        "sitemap_seasonal_ps.xml",
        "sitemap_reviews_ps.xml",
        # mg:
        "sitemap_bestfor_mg.xml",
        "sitemap_workflow_mg.xml",
        "sitemap_vs_mg.xml",
        "sitemap_seasonal_mg.xml",
        "sitemap_reviews_mg.xml",
        # rw:
        "sitemap_bestfor_rw.xml",
        "sitemap_workflow_rw.xml",
        "sitemap_vs_rw.xml",
        "sitemap_seasonal_rw.xml",
        "sitemap_reviews_rw.xml",
        # ny:
        "sitemap_bestfor_ny.xml",
        "sitemap_workflow_ny.xml",
        "sitemap_vs_ny.xml",
        "sitemap_seasonal_ny.xml",
        "sitemap_reviews_ny.xml",
        # jv:
        "sitemap_bestfor_jv.xml",
        "sitemap_workflow_jv.xml",
        "sitemap_vs_jv.xml",
        "sitemap_seasonal_jv.xml",
        "sitemap_reviews_jv.xml",
        # ceb:
        "sitemap_bestfor_ceb.xml",
        "sitemap_workflow_ceb.xml",
        "sitemap_vs_ceb.xml",
        "sitemap_seasonal_ceb.xml",
        "sitemap_reviews_ceb.xml",
        # st:
        "sitemap_bestfor_st.xml",
        "sitemap_workflow_st.xml",
        "sitemap_vs_st.xml",
        "sitemap_seasonal_st.xml",
        "sitemap_reviews_st.xml",
        # tn:
        "sitemap_bestfor_tn.xml",
        "sitemap_workflow_tn.xml",
        "sitemap_vs_tn.xml",
        "sitemap_seasonal_tn.xml",
        "sitemap_reviews_tn.xml",
        # su:
        "sitemap_bestfor_su.xml",
        "sitemap_workflow_su.xml",
        "sitemap_vs_su.xml",
        "sitemap_seasonal_su.xml",
        "sitemap_reviews_su.xml",
        # as:
        "sitemap_bestfor_as.xml",
        "sitemap_workflow_as.xml",
        "sitemap_vs_as.xml",
        "sitemap_seasonal_as.xml",
        "sitemap_reviews_as.xml",
        # wo:
        "sitemap_bestfor_wo.xml",
        "sitemap_workflow_wo.xml",
        "sitemap_vs_wo.xml",
        "sitemap_seasonal_wo.xml",
        "sitemap_reviews_wo.xml",
        # bm:
        "sitemap_bestfor_bm.xml",
        "sitemap_workflow_bm.xml",
        "sitemap_vs_bm.xml",
        "sitemap_seasonal_bm.xml",
        "sitemap_reviews_bm.xml",
        # or:
        "sitemap_bestfor_or.xml",
        "sitemap_workflow_or.xml",
        "sitemap_vs_or.xml",
        "sitemap_seasonal_or.xml",
        "sitemap_reviews_or.xml",
        # mai:
        "sitemap_bestfor_mai.xml",
        "sitemap_workflow_mai.xml",
        "sitemap_vs_mai.xml",
        "sitemap_seasonal_mai.xml",
        "sitemap_reviews_mai.xml",
        # sd:
        "sitemap_bestfor_sd.xml",
        "sitemap_workflow_sd.xml",
        "sitemap_vs_sd.xml",
        "sitemap_seasonal_sd.xml",
        "sitemap_reviews_sd.xml",
        # tt:
        "sitemap_bestfor_tt.xml",
        "sitemap_workflow_tt.xml",
        "sitemap_vs_tt.xml",
        "sitemap_seasonal_tt.xml",
        "sitemap_reviews_tt.xml",
        # ug:
        "sitemap_bestfor_ug.xml",
        "sitemap_workflow_ug.xml",
        "sitemap_vs_ug.xml",
        "sitemap_seasonal_ug.xml",
        "sitemap_reviews_ug.xml",
        # ba:
        "sitemap_bestfor_ba.xml",
        "sitemap_workflow_ba.xml",
        "sitemap_vs_ba.xml",
        "sitemap_seasonal_ba.xml",
        "sitemap_reviews_ba.xml",
        # qu:
        "sitemap_bestfor_qu.xml",
        "sitemap_workflow_qu.xml",
        "sitemap_vs_qu.xml",
        "sitemap_seasonal_qu.xml",
        "sitemap_reviews_qu.xml",
        # gn:
        "sitemap_bestfor_gn.xml",
        "sitemap_workflow_gn.xml",
        "sitemap_vs_gn.xml",
        "sitemap_seasonal_gn.xml",
        "sitemap_reviews_gn.xml",
        # ga:
        "sitemap_bestfor_ga.xml",
        "sitemap_workflow_ga.xml",
        "sitemap_vs_ga.xml",
        "sitemap_seasonal_ga.xml",
        "sitemap_reviews_ga.xml",
        # gd:
        "sitemap_bestfor_gd.xml",
        "sitemap_workflow_gd.xml",
        "sitemap_vs_gd.xml",
        "sitemap_seasonal_gd.xml",
        "sitemap_reviews_gd.xml",
        # eu:
        "sitemap_bestfor_eu.xml",
        "sitemap_workflow_eu.xml",
        "sitemap_vs_eu.xml",
        "sitemap_seasonal_eu.xml",
        "sitemap_reviews_eu.xml",
        # oc:
        "sitemap_bestfor_oc.xml",
        "sitemap_workflow_oc.xml",
        "sitemap_vs_oc.xml",
        "sitemap_seasonal_oc.xml",
        "sitemap_reviews_oc.xml",
        # ay:
        "sitemap_bestfor_ay.xml",
        "sitemap_workflow_ay.xml",
        "sitemap_vs_ay.xml",
        "sitemap_seasonal_ay.xml",
        "sitemap_reviews_ay.xml",
        # bo:
        "sitemap_bestfor_bo.xml",
        "sitemap_workflow_bo.xml",
        "sitemap_vs_bo.xml",
        "sitemap_seasonal_bo.xml",
        "sitemap_reviews_bo.xml",
        # lb:
        "sitemap_bestfor_lb.xml",
        "sitemap_workflow_lb.xml",
        "sitemap_vs_lb.xml",
        "sitemap_seasonal_lb.xml",
        "sitemap_reviews_lb.xml",
        # mt:
        "sitemap_bestfor_mt.xml",
        "sitemap_workflow_mt.xml",
        "sitemap_vs_mt.xml",
        "sitemap_seasonal_mt.xml",
        "sitemap_reviews_mt.xml",
        # gl:
        "sitemap_bestfor_gl.xml",
        "sitemap_workflow_gl.xml",
        "sitemap_vs_gl.xml",
        "sitemap_seasonal_gl.xml",
        "sitemap_reviews_gl.xml",
        # is:
        "sitemap_bestfor_is.xml",
        "sitemap_workflow_is.xml",
        "sitemap_vs_is.xml",
        "sitemap_seasonal_is.xml",
        "sitemap_reviews_is.xml",
        # kn:
        "sitemap_bestfor_kn.xml",
        "sitemap_workflow_kn.xml",
        "sitemap_vs_kn.xml",
        "sitemap_seasonal_kn.xml",
        "sitemap_reviews_kn.xml",
        # ml:
        "sitemap_bestfor_ml.xml",
        "sitemap_workflow_ml.xml",
        "sitemap_vs_ml.xml",
        "sitemap_seasonal_ml.xml",
        "sitemap_reviews_ml.xml",
        # fy:
        "sitemap_bestfor_fy.xml",
        "sitemap_workflow_fy.xml",
        "sitemap_vs_fy.xml",
        "sitemap_seasonal_fy.xml",
        "sitemap_reviews_fy.xml",
        # fo:
        "sitemap_bestfor_fo.xml",
        "sitemap_workflow_fo.xml",
        "sitemap_vs_fo.xml",
        "sitemap_seasonal_fo.xml",
        "sitemap_reviews_fo.xml",
        # dz:
        "sitemap_bestfor_dz.xml",
        "sitemap_workflow_dz.xml",
        "sitemap_vs_dz.xml",
        "sitemap_seasonal_dz.xml",
        "sitemap_reviews_dz.xml",
        # to:
        "sitemap_bestfor_to.xml",
        "sitemap_workflow_to.xml",
        "sitemap_vs_to.xml",
        "sitemap_seasonal_to.xml",
        "sitemap_reviews_to.xml",
        # sm:
        "sitemap_bestfor_sm.xml",
        "sitemap_workflow_sm.xml",
        "sitemap_vs_sm.xml",
        "sitemap_seasonal_sm.xml",
        "sitemap_reviews_sm.xml",
        # fj:
        "sitemap_bestfor_fj.xml",
        "sitemap_workflow_fj.xml",
        "sitemap_vs_fj.xml",
        "sitemap_seasonal_fj.xml",
        "sitemap_reviews_fj.xml",
        # mi:
        "sitemap_bestfor_mi.xml",
        "sitemap_workflow_mi.xml",
        "sitemap_vs_mi.xml",
        "sitemap_seasonal_mi.xml",
        "sitemap_reviews_mi.xml",
        # ty:
        "sitemap_bestfor_ty.xml",
        "sitemap_workflow_ty.xml",
        "sitemap_vs_ty.xml",
        "sitemap_seasonal_ty.xml",
        "sitemap_reviews_ty.xml",
        # ht:
        "sitemap_bestfor_ht.xml",
        "sitemap_workflow_ht.xml",
        "sitemap_vs_ht.xml",
        "sitemap_seasonal_ht.xml",
        "sitemap_reviews_ht.xml",
        # ln:
        "sitemap_bestfor_ln.xml",
        "sitemap_workflow_ln.xml",
        "sitemap_vs_ln.xml",
        "sitemap_seasonal_ln.xml",
        "sitemap_reviews_ln.xml",
        # ku:
        "sitemap_bestfor_ku.xml",
        "sitemap_workflow_ku.xml",
        "sitemap_vs_ku.xml",
        "sitemap_seasonal_ku.xml",
        "sitemap_reviews_ku.xml",
        # rm:
        "sitemap_bestfor_rm.xml",
        "sitemap_workflow_rm.xml",
        "sitemap_vs_rm.xml",
        "sitemap_seasonal_rm.xml",
        "sitemap_reviews_rm.xml",
        # sn:
        "sitemap_bestfor_sn.xml",
        "sitemap_workflow_sn.xml",
        "sitemap_vs_sn.xml",
        "sitemap_seasonal_sn.xml",
        "sitemap_reviews_sn.xml",
        # ak:
        "sitemap_bestfor_ak.xml",
        "sitemap_workflow_ak.xml",
        "sitemap_vs_ak.xml",
        "sitemap_seasonal_ak.xml",
        "sitemap_reviews_ak.xml",
        # se:
        "sitemap_bestfor_se.xml",
        "sitemap_workflow_se.xml",
        "sitemap_vs_se.xml",
        "sitemap_seasonal_se.xml",
        "sitemap_reviews_se.xml",
        # co:
        "sitemap_bestfor_co.xml",
        "sitemap_workflow_co.xml",
        "sitemap_vs_co.xml",
        "sitemap_seasonal_co.xml",
        "sitemap_reviews_co.xml",
        # tk:
        "sitemap_bestfor_tk.xml",
        "sitemap_workflow_tk.xml",
        "sitemap_vs_tk.xml",
        "sitemap_seasonal_tk.xml",
        "sitemap_reviews_tk.xml",
        # ee:
        "sitemap_bestfor_ee.xml",
        "sitemap_workflow_ee.xml",
        "sitemap_vs_ee.xml",
        "sitemap_seasonal_ee.xml",
        "sitemap_reviews_ee.xml",
        # lu:
        "sitemap_bestfor_lu.xml",
        "sitemap_workflow_lu.xml",
        "sitemap_vs_lu.xml",
        "sitemap_seasonal_lu.xml",
        "sitemap_reviews_lu.xml",
        # ve:
        "sitemap_bestfor_ve.xml",
        "sitemap_workflow_ve.xml",
        "sitemap_vs_ve.xml",
        "sitemap_seasonal_ve.xml",
        "sitemap_reviews_ve.xml",
        # ss:
        "sitemap_bestfor_ss.xml",
        "sitemap_workflow_ss.xml",
        "sitemap_vs_ss.xml",
        "sitemap_seasonal_ss.xml",
        "sitemap_reviews_ss.xml",
        # sc:
        "sitemap_bestfor_sc.xml",
        "sitemap_workflow_sc.xml",
        "sitemap_vs_sc.xml",
        "sitemap_seasonal_sc.xml",
        "sitemap_reviews_sc.xml",
        # wa:
        "sitemap_bestfor_wa.xml",
        "sitemap_workflow_wa.xml",
        "sitemap_vs_wa.xml",
        "sitemap_seasonal_wa.xml",
        "sitemap_reviews_wa.xml",
        # li:
        "sitemap_bestfor_li.xml",
        "sitemap_workflow_li.xml",
        "sitemap_vs_li.xml",
        "sitemap_seasonal_li.xml",
        "sitemap_reviews_li.xml",
        # nd:
        "sitemap_bestfor_nd.xml",
        "sitemap_workflow_nd.xml",
        "sitemap_vs_nd.xml",
        "sitemap_seasonal_nd.xml",
        "sitemap_reviews_nd.xml",
        # kl:
        "sitemap_bestfor_kl.xml",
        "sitemap_workflow_kl.xml",
        "sitemap_vs_kl.xml",
        "sitemap_seasonal_kl.xml",
        "sitemap_reviews_kl.xml",
        # nv:
        "sitemap_bestfor_nv.xml",
        "sitemap_workflow_nv.xml",
        "sitemap_vs_nv.xml",
        "sitemap_seasonal_nv.xml",
        "sitemap_reviews_nv.xml",
        # tw:
        "sitemap_bestfor_tw.xml",
        "sitemap_workflow_tw.xml",
        "sitemap_vs_tw.xml",
        "sitemap_seasonal_tw.xml",
        "sitemap_reviews_tw.xml",
        # nr:
        "sitemap_bestfor_nr.xml",
        "sitemap_workflow_nr.xml",
        "sitemap_vs_nr.xml",
        "sitemap_seasonal_nr.xml",
        "sitemap_reviews_nr.xml",
        # kg:
        "sitemap_bestfor_kg.xml",
        "sitemap_workflow_kg.xml",
        "sitemap_vs_kg.xml",
        "sitemap_seasonal_kg.xml",
        "sitemap_reviews_kg.xml",
        # lg:
        "sitemap_bestfor_lg.xml",
        "sitemap_workflow_lg.xml",
        "sitemap_vs_lg.xml",
        "sitemap_seasonal_lg.xml",
        "sitemap_reviews_lg.xml",
        # ts:
        "sitemap_bestfor_ts.xml",
        "sitemap_workflow_ts.xml",
        "sitemap_vs_ts.xml",
        "sitemap_seasonal_ts.xml",
        "sitemap_reviews_ts.xml",
        # ff:
        "sitemap_bestfor_ff.xml",
        "sitemap_workflow_ff.xml",
        "sitemap_vs_ff.xml",
        "sitemap_seasonal_ff.xml",
        "sitemap_reviews_ff.xml",
        # sg:
        "sitemap_bestfor_sg.xml",
        "sitemap_workflow_sg.xml",
        "sitemap_vs_sg.xml",
        "sitemap_seasonal_sg.xml",
        "sitemap_reviews_sg.xml",
        # cr:
        "sitemap_bestfor_cr.xml",
        "sitemap_workflow_cr.xml",
        "sitemap_vs_cr.xml",
        "sitemap_seasonal_cr.xml",
        "sitemap_reviews_cr.xml",
        # ng:
        "sitemap_bestfor_ng.xml",
        "sitemap_workflow_ng.xml",
        "sitemap_vs_ng.xml",
        "sitemap_seasonal_ng.xml",
        "sitemap_reviews_ng.xml",
        # rn:
        "sitemap_bestfor_rn.xml",
        "sitemap_workflow_rn.xml",
        "sitemap_vs_rn.xml",
        "sitemap_seasonal_rn.xml",
        "sitemap_reviews_rn.xml",
        # os:
        "sitemap_bestfor_os.xml",
        "sitemap_workflow_os.xml",
        "sitemap_vs_os.xml",
        "sitemap_seasonal_os.xml",
        "sitemap_reviews_os.xml",
        # gv:
        "sitemap_bestfor_gv.xml",
        "sitemap_workflow_gv.xml",
        "sitemap_vs_gv.xml",
        "sitemap_seasonal_gv.xml",
        "sitemap_reviews_gv.xml",
        # ab:
        "sitemap_bestfor_ab.xml",
        "sitemap_workflow_ab.xml",
        "sitemap_vs_ab.xml",
        "sitemap_seasonal_ab.xml",
        "sitemap_reviews_ab.xml",
        # bi:
        "sitemap_bestfor_bi.xml",
        "sitemap_workflow_bi.xml",
        "sitemap_vs_bi.xml",
        "sitemap_seasonal_bi.xml",
        "sitemap_reviews_bi.xml",
        # ch:
        "sitemap_bestfor_ch.xml",
        "sitemap_workflow_ch.xml",
        "sitemap_vs_ch.xml",
        "sitemap_seasonal_ch.xml",
        "sitemap_reviews_ch.xml",
        # ik:
        "sitemap_bestfor_ik.xml",
        "sitemap_workflow_ik.xml",
        "sitemap_vs_ik.xml",
        "sitemap_seasonal_ik.xml",
        "sitemap_reviews_ik.xml",
        # iu:
        "sitemap_bestfor_iu.xml",
        "sitemap_workflow_iu.xml",
        "sitemap_vs_iu.xml",
        "sitemap_seasonal_iu.xml",
        "sitemap_reviews_iu.xml",
        # kv:
        "sitemap_bestfor_kv.xml",
        "sitemap_workflow_kv.xml",
        "sitemap_vs_kv.xml",
        "sitemap_seasonal_kv.xml",
        "sitemap_reviews_kv.xml",
        # kw:
        "sitemap_bestfor_kw.xml",
        "sitemap_workflow_kw.xml",
        "sitemap_vs_kw.xml",
        "sitemap_seasonal_kw.xml",
        "sitemap_reviews_kw.xml",
        # mh:
        "sitemap_bestfor_mh.xml",
        "sitemap_workflow_mh.xml",
        "sitemap_vs_mh.xml",
        "sitemap_seasonal_mh.xml",
        "sitemap_reviews_mh.xml",
        # na:
        "sitemap_bestfor_na.xml",
        "sitemap_workflow_na.xml",
        "sitemap_vs_na.xml",
        "sitemap_seasonal_na.xml",
        "sitemap_reviews_na.xml",
        # oj:
        "sitemap_bestfor_oj.xml",
        "sitemap_workflow_oj.xml",
        "sitemap_vs_oj.xml",
        "sitemap_seasonal_oj.xml",
        "sitemap_reviews_oj.xml",
        # vo:
        "sitemap_bestfor_vo.xml",
        "sitemap_workflow_vo.xml",
        "sitemap_vs_vo.xml",
        "sitemap_seasonal_vo.xml",
        "sitemap_reviews_vo.xml",
        # za:
        "sitemap_bestfor_za.xml",
        "sitemap_workflow_za.xml",
        "sitemap_vs_za.xml",
        "sitemap_seasonal_za.xml",
        "sitemap_reviews_za.xml",
        # av:
        "sitemap_bestfor_av.xml",
        "sitemap_workflow_av.xml",
        "sitemap_vs_av.xml",
        "sitemap_seasonal_av.xml",
        "sitemap_reviews_av.xml",
        # cv:
        "sitemap_bestfor_cv.xml",
        "sitemap_workflow_cv.xml",
        "sitemap_vs_cv.xml",
        "sitemap_seasonal_cv.xml",
        "sitemap_reviews_cv.xml",
        # ii:
        "sitemap_bestfor_ii.xml",
        "sitemap_workflow_ii.xml",
        "sitemap_vs_ii.xml",
        "sitemap_seasonal_ii.xml",
        "sitemap_reviews_ii.xml",
        # ki:
        "sitemap_bestfor_ki.xml",
        "sitemap_workflow_ki.xml",
        "sitemap_vs_ki.xml",
        "sitemap_seasonal_ki.xml",
        "sitemap_reviews_ki.xml",
        # ti:
        "sitemap_bestfor_ti.xml",
        "sitemap_workflow_ti.xml",
        "sitemap_vs_ti.xml",
        "sitemap_seasonal_ti.xml",
        "sitemap_reviews_ti.xml",
        # be:
        "sitemap_bestfor_be.xml",
        "sitemap_workflow_be.xml",
        "sitemap_vs_be.xml",
        "sitemap_seasonal_be.xml",
        "sitemap_reviews_be.xml",
        # ks:
        "sitemap_bestfor_ks.xml",
        "sitemap_workflow_ks.xml",
        "sitemap_vs_ks.xml",
        "sitemap_seasonal_ks.xml",
        "sitemap_reviews_ks.xml",
        # ce:
        "sitemap_bestfor_ce.xml",
        "sitemap_workflow_ce.xml",
        "sitemap_vs_ce.xml",
        "sitemap_seasonal_ce.xml",
        "sitemap_reviews_ce.xml",
        # dv:
        "sitemap_bestfor_dv.xml",
        "sitemap_workflow_dv.xml",
        "sitemap_vs_dv.xml",
        "sitemap_seasonal_dv.xml",
        "sitemap_reviews_dv.xml",
        # kr:
        "sitemap_bestfor_kr.xml",
        "sitemap_workflow_kr.xml",
        "sitemap_vs_kr.xml",
        "sitemap_seasonal_kr.xml",
        "sitemap_reviews_kr.xml",
        # yi:
        "sitemap_bestfor_yi.xml",
        "sitemap_workflow_yi.xml",
        "sitemap_vs_yi.xml",
        "sitemap_seasonal_yi.xml",
        "sitemap_reviews_yi.xml",
        # nn:
        "sitemap_bestfor_nn.xml",
        "sitemap_workflow_nn.xml",
        "sitemap_vs_nn.xml",
        "sitemap_seasonal_nn.xml",
        "sitemap_reviews_nn.xml",
        # eo:
        "sitemap_bestfor_eo.xml",
        "sitemap_workflow_eo.xml",
        "sitemap_vs_eo.xml",
        "sitemap_seasonal_eo.xml",
        "sitemap_reviews_eo.xml",
        # br:
        "sitemap_bestfor_br.xml",
        "sitemap_workflow_br.xml",
        "sitemap_vs_br.xml",
        "sitemap_seasonal_br.xml",
        "sitemap_reviews_br.xml",
        # kj:
        "sitemap_bestfor_kj.xml",
        "sitemap_workflow_kj.xml",
        "sitemap_vs_kj.xml",
        "sitemap_seasonal_kj.xml",
        "sitemap_reviews_kj.xml",
        # hz:
        "sitemap_bestfor_hz.xml",
        "sitemap_workflow_hz.xml",
        "sitemap_vs_hz.xml",
        "sitemap_seasonal_hz.xml",
        "sitemap_reviews_hz.xml",
        # aa:
        "sitemap_bestfor_aa.xml",
        "sitemap_workflow_aa.xml",
        "sitemap_vs_aa.xml",
        "sitemap_seasonal_aa.xml",
        "sitemap_reviews_aa.xml",
        # an:
        "sitemap_bestfor_an.xml",
        "sitemap_workflow_an.xml",
        "sitemap_vs_an.xml",
        "sitemap_seasonal_an.xml",
        "sitemap_reviews_an.xml",
        # ho:
        "sitemap_bestfor_ho.xml",
        "sitemap_workflow_ho.xml",
        "sitemap_vs_ho.xml",
        "sitemap_seasonal_ho.xml",
        "sitemap_reviews_ho.xml",
        # la:
        "sitemap_bestfor_la.xml",
        "sitemap_workflow_la.xml",
        "sitemap_vs_la.xml",
        "sitemap_seasonal_la.xml",
        "sitemap_reviews_la.xml",
        # sa:
        "sitemap_bestfor_sa.xml",
        "sitemap_workflow_sa.xml",
        "sitemap_vs_sa.xml",
        "sitemap_seasonal_sa.xml",
        "sitemap_reviews_sa.xml",
        # ia:
        "sitemap_bestfor_ia.xml",
        "sitemap_workflow_ia.xml",
        "sitemap_vs_ia.xml",
        "sitemap_seasonal_ia.xml",
        "sitemap_reviews_ia.xml",
        # es-AR:
        "sitemap_bestfor_es_AR.xml", "sitemap_workflow_es_AR.xml", "sitemap_vs_es_AR.xml",
        "sitemap_seasonal_es_AR.xml", "sitemap_reviews_es_AR.xml",
        # es-CO:
        "sitemap_bestfor_es_CO.xml", "sitemap_workflow_es_CO.xml", "sitemap_vs_es_CO.xml",
        "sitemap_seasonal_es_CO.xml", "sitemap_reviews_es_CO.xml",
        # es-US:
        "sitemap_bestfor_es_US.xml", "sitemap_workflow_es_US.xml", "sitemap_vs_es_US.xml",
        "sitemap_seasonal_es_US.xml", "sitemap_reviews_es_US.xml",
        # fr-BE:
        "sitemap_bestfor_fr_BE.xml", "sitemap_workflow_fr_BE.xml", "sitemap_vs_fr_BE.xml",
        "sitemap_seasonal_fr_BE.xml", "sitemap_reviews_fr_BE.xml",
        # fr-CH:
        "sitemap_bestfor_fr_CH.xml", "sitemap_workflow_fr_CH.xml", "sitemap_vs_fr_CH.xml",
        "sitemap_seasonal_fr_CH.xml", "sitemap_reviews_fr_CH.xml",
        # de-AT:
        "sitemap_bestfor_de_AT.xml", "sitemap_workflow_de_AT.xml", "sitemap_vs_de_AT.xml",
        "sitemap_seasonal_de_AT.xml", "sitemap_reviews_de_AT.xml",
        # de-CH:
        "sitemap_bestfor_de_CH.xml", "sitemap_workflow_de_CH.xml", "sitemap_vs_de_CH.xml",
        "sitemap_seasonal_de_CH.xml", "sitemap_reviews_de_CH.xml",
        # ar-EG:
        "sitemap_bestfor_ar_EG.xml", "sitemap_workflow_ar_EG.xml", "sitemap_vs_ar_EG.xml",
        "sitemap_seasonal_ar_EG.xml", "sitemap_reviews_ar_EG.xml",
        # en-GB:
        "sitemap_bestfor_en_GB.xml", "sitemap_workflow_en_GB.xml", "sitemap_vs_en_GB.xml",
        "sitemap_seasonal_en_GB.xml", "sitemap_reviews_en_GB.xml",
        # en-AU:
        "sitemap_bestfor_en_AU.xml", "sitemap_workflow_en_AU.xml", "sitemap_vs_en_AU.xml",
        "sitemap_seasonal_en_AU.xml", "sitemap_reviews_en_AU.xml",
        # en-CA:
        "sitemap_bestfor_en_CA.xml", "sitemap_workflow_en_CA.xml", "sitemap_vs_en_CA.xml",
        "sitemap_seasonal_en_CA.xml", "sitemap_reviews_en_CA.xml",
        # en-IN:
        "sitemap_bestfor_en_IN.xml", "sitemap_workflow_en_IN.xml", "sitemap_vs_en_IN.xml",
        "sitemap_seasonal_en_IN.xml", "sitemap_reviews_en_IN.xml",
        # nl-BE:
        "sitemap_bestfor_nl_BE.xml", "sitemap_workflow_nl_BE.xml", "sitemap_vs_nl_BE.xml",
        "sitemap_seasonal_nl_BE.xml", "sitemap_reviews_nl_BE.xml",
        # pt-AO:
        "sitemap_bestfor_pt_AO.xml", "sitemap_workflow_pt_AO.xml", "sitemap_vs_pt_AO.xml",
        "sitemap_seasonal_pt_AO.xml", "sitemap_reviews_pt_AO.xml",
        # es-CL:
        "sitemap_bestfor_es_CL.xml", "sitemap_workflow_es_CL.xml", "sitemap_vs_es_CL.xml",
        "sitemap_seasonal_es_CL.xml", "sitemap_reviews_es_CL.xml",
        # es-PE:
        "sitemap_bestfor_es_PE.xml", "sitemap_workflow_es_PE.xml", "sitemap_vs_es_PE.xml",
        "sitemap_seasonal_es_PE.xml", "sitemap_reviews_es_PE.xml",
        # fr-MA:
        "sitemap_bestfor_fr_MA.xml", "sitemap_workflow_fr_MA.xml", "sitemap_vs_fr_MA.xml",
        "sitemap_seasonal_fr_MA.xml", "sitemap_reviews_fr_MA.xml",
        # es-VE:
        "sitemap_bestfor_es_VE.xml", "sitemap_workflow_es_VE.xml", "sitemap_vs_es_VE.xml",
        "sitemap_seasonal_es_VE.xml", "sitemap_reviews_es_VE.xml",
        # en-NZ:
        "sitemap_bestfor_en_NZ.xml", "sitemap_workflow_en_NZ.xml", "sitemap_vs_en_NZ.xml",
        "sitemap_seasonal_en_NZ.xml", "sitemap_reviews_en_NZ.xml",
        # en-SG:
        "sitemap_bestfor_en_SG.xml", "sitemap_workflow_en_SG.xml", "sitemap_vs_en_SG.xml",
        "sitemap_seasonal_en_SG.xml", "sitemap_reviews_en_SG.xml",
        # en-PH:
        "sitemap_bestfor_en_PH.xml", "sitemap_workflow_en_PH.xml", "sitemap_vs_en_PH.xml",
        "sitemap_seasonal_en_PH.xml", "sitemap_reviews_en_PH.xml",
        # en-ZA:
        "sitemap_bestfor_en_ZA.xml", "sitemap_workflow_en_ZA.xml", "sitemap_vs_en_ZA.xml",
        "sitemap_seasonal_en_ZA.xml", "sitemap_reviews_en_ZA.xml",
        # ar-DZ:
        "sitemap_bestfor_ar_DZ.xml", "sitemap_workflow_ar_DZ.xml", "sitemap_vs_ar_DZ.xml",
        "sitemap_seasonal_ar_DZ.xml", "sitemap_reviews_ar_DZ.xml",
        # en-NG:
        "sitemap_bestfor_en_NG.xml", "sitemap_workflow_en_NG.xml", "sitemap_vs_en_NG.xml",
        "sitemap_seasonal_en_NG.xml", "sitemap_reviews_en_NG.xml",
        # en-MY:
        "sitemap_bestfor_en_MY.xml", "sitemap_workflow_en_MY.xml", "sitemap_vs_en_MY.xml",
        "sitemap_seasonal_en_MY.xml", "sitemap_reviews_en_MY.xml",
        # fr-DZ:
        "sitemap_bestfor_fr_DZ.xml", "sitemap_workflow_fr_DZ.xml", "sitemap_vs_fr_DZ.xml",
        "sitemap_seasonal_fr_DZ.xml", "sitemap_reviews_fr_DZ.xml",
        # en-KE:
        "sitemap_bestfor_en_KE.xml", "sitemap_workflow_en_KE.xml", "sitemap_vs_en_KE.xml",
        "sitemap_seasonal_en_KE.xml", "sitemap_reviews_en_KE.xml",
        # en-PK:
        "sitemap_bestfor_en_PK.xml", "sitemap_workflow_en_PK.xml", "sitemap_vs_en_PK.xml",
        "sitemap_seasonal_en_PK.xml", "sitemap_reviews_en_PK.xml",
        # pt-MZ:
        "sitemap_bestfor_pt_MZ.xml", "sitemap_workflow_pt_MZ.xml", "sitemap_vs_pt_MZ.xml",
        "sitemap_seasonal_pt_MZ.xml", "sitemap_reviews_pt_MZ.xml",
        # en-GH:
        "sitemap_bestfor_en_GH.xml", "sitemap_workflow_en_GH.xml", "sitemap_vs_en_GH.xml",
        "sitemap_seasonal_en_GH.xml", "sitemap_reviews_en_GH.xml",
        # en-TZ:
        "sitemap_bestfor_en_TZ.xml", "sitemap_workflow_en_TZ.xml", "sitemap_vs_en_TZ.xml",
        "sitemap_seasonal_en_TZ.xml", "sitemap_reviews_en_TZ.xml",
        # en-UG:
        "sitemap_bestfor_en_UG.xml", "sitemap_workflow_en_UG.xml", "sitemap_vs_en_UG.xml",
        "sitemap_seasonal_en_UG.xml", "sitemap_reviews_en_UG.xml",
        # es-GT:
        "sitemap_bestfor_es_GT.xml", "sitemap_workflow_es_GT.xml", "sitemap_vs_es_GT.xml",
        "sitemap_seasonal_es_GT.xml", "sitemap_reviews_es_GT.xml",
        # es-DO:
        "sitemap_bestfor_es_DO.xml", "sitemap_workflow_es_DO.xml", "sitemap_vs_es_DO.xml",
        "sitemap_seasonal_es_DO.xml", "sitemap_reviews_es_DO.xml",
        # ar-IQ:
        "sitemap_bestfor_ar_IQ.xml", "sitemap_workflow_ar_IQ.xml", "sitemap_vs_ar_IQ.xml",
        "sitemap_seasonal_ar_IQ.xml", "sitemap_reviews_ar_IQ.xml",
        # es-BO:
        "sitemap_bestfor_es_BO.xml", "sitemap_workflow_es_BO.xml", "sitemap_vs_es_BO.xml",
        "sitemap_seasonal_es_BO.xml", "sitemap_reviews_es_BO.xml",
        # es-EC:
        "sitemap_bestfor_es_EC.xml", "sitemap_workflow_es_EC.xml", "sitemap_vs_es_EC.xml",
        "sitemap_seasonal_es_EC.xml", "sitemap_reviews_es_EC.xml",
        # fr-SN:
        "sitemap_bestfor_fr_SN.xml", "sitemap_workflow_fr_SN.xml", "sitemap_vs_fr_SN.xml",
        "sitemap_seasonal_fr_SN.xml", "sitemap_reviews_fr_SN.xml",
        # fr-CI:
        "sitemap_bestfor_fr_CI.xml", "sitemap_workflow_fr_CI.xml", "sitemap_vs_fr_CI.xml",
        "sitemap_seasonal_fr_CI.xml", "sitemap_reviews_fr_CI.xml",
        # fr-CM:
        "sitemap_bestfor_fr_CM.xml", "sitemap_workflow_fr_CM.xml", "sitemap_vs_fr_CM.xml",
        "sitemap_seasonal_fr_CM.xml", "sitemap_reviews_fr_CM.xml",
        # en-ZW:
        "sitemap_bestfor_en_ZW.xml", "sitemap_workflow_en_ZW.xml", "sitemap_vs_en_ZW.xml",
        "sitemap_seasonal_en_ZW.xml", "sitemap_reviews_en_ZW.xml",
        # es-PY:
        "sitemap_bestfor_es_PY.xml", "sitemap_workflow_es_PY.xml", "sitemap_vs_es_PY.xml",
        "sitemap_seasonal_es_PY.xml", "sitemap_reviews_es_PY.xml",
        # es-UY:
        "sitemap_bestfor_es_UY.xml", "sitemap_workflow_es_UY.xml", "sitemap_vs_es_UY.xml",
        "sitemap_seasonal_es_UY.xml", "sitemap_reviews_es_UY.xml",
        # fr-TN:
        "sitemap_bestfor_fr_TN.xml", "sitemap_workflow_fr_TN.xml", "sitemap_vs_fr_TN.xml",
        "sitemap_seasonal_fr_TN.xml", "sitemap_reviews_fr_TN.xml",
        # ar-MA:
        "sitemap_bestfor_ar_MA.xml", "sitemap_workflow_ar_MA.xml", "sitemap_vs_ar_MA.xml",
        "sitemap_seasonal_ar_MA.xml", "sitemap_reviews_ar_MA.xml",
        # ar-LY:
        "sitemap_bestfor_ar_LY.xml", "sitemap_workflow_ar_LY.xml", "sitemap_vs_ar_LY.xml",
        "sitemap_seasonal_ar_LY.xml", "sitemap_reviews_ar_LY.xml",
        # ar-SD:
        "sitemap_bestfor_ar_SD.xml", "sitemap_workflow_ar_SD.xml", "sitemap_vs_ar_SD.xml",
        "sitemap_seasonal_ar_SD.xml", "sitemap_reviews_ar_SD.xml",
        # en-ET:
        "sitemap_bestfor_en_ET.xml", "sitemap_workflow_en_ET.xml", "sitemap_vs_en_ET.xml",
        "sitemap_seasonal_en_ET.xml", "sitemap_reviews_en_ET.xml",
        # en-RW:
        "sitemap_bestfor_en_RW.xml", "sitemap_workflow_en_RW.xml", "sitemap_vs_en_RW.xml",
        "sitemap_seasonal_en_RW.xml", "sitemap_reviews_en_RW.xml",
        # en-ZM:
        "sitemap_bestfor_en_ZM.xml", "sitemap_workflow_en_ZM.xml", "sitemap_vs_en_ZM.xml",
        "sitemap_seasonal_en_ZM.xml", "sitemap_reviews_en_ZM.xml",
        # en-MW:
        "sitemap_bestfor_en_MW.xml", "sitemap_workflow_en_MW.xml", "sitemap_vs_en_MW.xml",
        "sitemap_seasonal_en_MW.xml", "sitemap_reviews_en_MW.xml",
        # fr-GN:
        "sitemap_bestfor_fr_GN.xml", "sitemap_workflow_fr_GN.xml", "sitemap_vs_fr_GN.xml",
        "sitemap_seasonal_fr_GN.xml", "sitemap_reviews_fr_GN.xml",
        # fr-ML:
        "sitemap_bestfor_fr_ML.xml", "sitemap_workflow_fr_ML.xml", "sitemap_vs_fr_ML.xml",
        "sitemap_seasonal_fr_ML.xml", "sitemap_reviews_fr_ML.xml",
        # fr-BF:
        "sitemap_bestfor_fr_BF.xml", "sitemap_workflow_fr_BF.xml", "sitemap_vs_fr_BF.xml",
        "sitemap_seasonal_fr_BF.xml", "sitemap_reviews_fr_BF.xml",
        # es-CR:
        "sitemap_bestfor_es_CR.xml", "sitemap_workflow_es_CR.xml", "sitemap_vs_es_CR.xml",
        "sitemap_seasonal_es_CR.xml", "sitemap_reviews_es_CR.xml",
        # es-HN:
        "sitemap_bestfor_es_HN.xml", "sitemap_workflow_es_HN.xml", "sitemap_vs_es_HN.xml",
        "sitemap_seasonal_es_HN.xml", "sitemap_reviews_es_HN.xml",
        # es-SV:
        "sitemap_bestfor_es_SV.xml", "sitemap_workflow_es_SV.xml", "sitemap_vs_es_SV.xml",
        "sitemap_seasonal_es_SV.xml", "sitemap_reviews_es_SV.xml",
        # ar-JO:
        "sitemap_bestfor_ar_JO.xml", "sitemap_workflow_ar_JO.xml", "sitemap_vs_ar_JO.xml",
        "sitemap_seasonal_ar_JO.xml", "sitemap_reviews_ar_JO.xml",
        # ar-YE:
        "sitemap_bestfor_ar_YE.xml", "sitemap_workflow_ar_YE.xml", "sitemap_vs_ar_YE.xml",
        "sitemap_seasonal_ar_YE.xml", "sitemap_reviews_ar_YE.xml",
        # fr-TD:
        "sitemap_bestfor_fr_TD.xml", "sitemap_workflow_fr_TD.xml", "sitemap_vs_fr_TD.xml",
        "sitemap_seasonal_fr_TD.xml", "sitemap_reviews_fr_TD.xml",
        # en-SL:
        "sitemap_bestfor_en_SL.xml", "sitemap_workflow_en_SL.xml", "sitemap_vs_en_SL.xml",
        "sitemap_seasonal_en_SL.xml", "sitemap_reviews_en_SL.xml",
        # en-LR:
        "sitemap_bestfor_en_LR.xml", "sitemap_workflow_en_LR.xml", "sitemap_vs_en_LR.xml",
        "sitemap_seasonal_en_LR.xml", "sitemap_reviews_en_LR.xml",
        # fr-CD:
        "sitemap_bestfor_fr_CD.xml", "sitemap_workflow_fr_CD.xml", "sitemap_vs_fr_CD.xml",
        "sitemap_seasonal_fr_CD.xml", "sitemap_reviews_fr_CD.xml",
        # fr-NE:
        "sitemap_bestfor_fr_NE.xml", "sitemap_workflow_fr_NE.xml", "sitemap_vs_fr_NE.xml",
        "sitemap_seasonal_fr_NE.xml", "sitemap_reviews_fr_NE.xml",
        # fr-BJ:
        "sitemap_bestfor_fr_BJ.xml", "sitemap_workflow_fr_BJ.xml", "sitemap_vs_fr_BJ.xml",
        "sitemap_seasonal_fr_BJ.xml", "sitemap_reviews_fr_BJ.xml",
        # fr-TG:
        "sitemap_bestfor_fr_TG.xml", "sitemap_workflow_fr_TG.xml", "sitemap_vs_fr_TG.xml",
        "sitemap_seasonal_fr_TG.xml", "sitemap_reviews_fr_TG.xml",
        # es-NI:
        "sitemap_bestfor_es_NI.xml", "sitemap_workflow_es_NI.xml", "sitemap_vs_es_NI.xml",
        "sitemap_seasonal_es_NI.xml", "sitemap_reviews_es_NI.xml",
        # ar-KW:
        "sitemap_bestfor_ar_KW.xml", "sitemap_workflow_ar_KW.xml", "sitemap_vs_ar_KW.xml",
        "sitemap_seasonal_ar_KW.xml", "sitemap_reviews_ar_KW.xml",
        # ar-OM:
        "sitemap_bestfor_ar_OM.xml", "sitemap_workflow_ar_OM.xml", "sitemap_vs_ar_OM.xml",
        "sitemap_seasonal_ar_OM.xml", "sitemap_reviews_ar_OM.xml",
        # ar-QA:
        "sitemap_bestfor_ar_QA.xml", "sitemap_workflow_ar_QA.xml", "sitemap_vs_ar_QA.xml",
        "sitemap_seasonal_ar_QA.xml", "sitemap_reviews_ar_QA.xml",
        # fr-CG:
        "sitemap_bestfor_fr_CG.xml", "sitemap_workflow_fr_CG.xml", "sitemap_vs_fr_CG.xml",
        "sitemap_seasonal_fr_CG.xml", "sitemap_reviews_fr_CG.xml",
        # fr-MR:
        "sitemap_bestfor_fr_MR.xml", "sitemap_workflow_fr_MR.xml", "sitemap_vs_fr_MR.xml",
        "sitemap_seasonal_fr_MR.xml", "sitemap_reviews_fr_MR.xml",
        # es-PA:
        "sitemap_bestfor_es_PA.xml", "sitemap_workflow_es_PA.xml", "sitemap_vs_es_PA.xml",
        "sitemap_seasonal_es_PA.xml", "sitemap_reviews_es_PA.xml",
        # ar-BH:
        "sitemap_bestfor_ar_BH.xml", "sitemap_workflow_ar_BH.xml", "sitemap_vs_ar_BH.xml",
        "sitemap_seasonal_ar_BH.xml", "sitemap_reviews_ar_BH.xml",
        # fr-GA:
        "sitemap_bestfor_fr_GA.xml", "sitemap_workflow_fr_GA.xml", "sitemap_vs_fr_GA.xml",
        "sitemap_seasonal_fr_GA.xml", "sitemap_reviews_fr_GA.xml",
        # en-NA:
        "sitemap_bestfor_en_NA.xml", "sitemap_workflow_en_NA.xml", "sitemap_vs_en_NA.xml",
        "sitemap_seasonal_en_NA.xml", "sitemap_reviews_en_NA.xml",
        # en-BW:
        "sitemap_bestfor_en_BW.xml", "sitemap_workflow_en_BW.xml", "sitemap_vs_en_BW.xml",
        "sitemap_seasonal_en_BW.xml", "sitemap_reviews_en_BW.xml",
        # fr-RW:
        "sitemap_bestfor_fr_RW.xml", "sitemap_workflow_fr_RW.xml", "sitemap_vs_fr_RW.xml",
        "sitemap_seasonal_fr_RW.xml", "sitemap_reviews_fr_RW.xml",
        # fr-HT:
        "sitemap_bestfor_fr_HT.xml", "sitemap_workflow_fr_HT.xml", "sitemap_vs_fr_HT.xml",
        "sitemap_seasonal_fr_HT.xml", "sitemap_reviews_fr_HT.xml",
        # fr-MG:
        "sitemap_bestfor_fr_MG.xml", "sitemap_workflow_fr_MG.xml", "sitemap_vs_fr_MG.xml",
        "sitemap_seasonal_fr_MG.xml", "sitemap_reviews_fr_MG.xml",
        # en-LS:
        "sitemap_bestfor_en_LS.xml", "sitemap_workflow_en_LS.xml", "sitemap_vs_en_LS.xml",
        "sitemap_seasonal_en_LS.xml", "sitemap_reviews_en_LS.xml",
        # en-SS:
        "sitemap_bestfor_en_SS.xml", "sitemap_workflow_en_SS.xml", "sitemap_vs_en_SS.xml",
        "sitemap_seasonal_en_SS.xml", "sitemap_reviews_en_SS.xml",
        # sw-KE:
        "sitemap_bestfor_sw_KE.xml", "sitemap_workflow_sw_KE.xml", "sitemap_vs_sw_KE.xml",
        "sitemap_seasonal_sw_KE.xml", "sitemap_reviews_sw_KE.xml",
        # en-GM:
        "sitemap_bestfor_en_GM.xml", "sitemap_workflow_en_GM.xml", "sitemap_vs_en_GM.xml",
        "sitemap_seasonal_en_GM.xml", "sitemap_reviews_en_GM.xml",
        # fr-BI:
        "sitemap_bestfor_fr_BI.xml", "sitemap_workflow_fr_BI.xml", "sitemap_vs_fr_BI.xml",
        "sitemap_seasonal_fr_BI.xml", "sitemap_reviews_fr_BI.xml",
        # fr-CV:
        "sitemap_bestfor_fr_CV.xml", "sitemap_workflow_fr_CV.xml", "sitemap_vs_fr_CV.xml",
        "sitemap_seasonal_fr_CV.xml", "sitemap_reviews_fr_CV.xml",
        # es-PR:
        "sitemap_bestfor_es_PR.xml", "sitemap_workflow_es_PR.xml", "sitemap_vs_es_PR.xml",
        "sitemap_seasonal_es_PR.xml", "sitemap_reviews_es_PR.xml",
        # fr-DJ:
        "sitemap_bestfor_fr_DJ.xml", "sitemap_workflow_fr_DJ.xml", "sitemap_vs_fr_DJ.xml",
        "sitemap_seasonal_fr_DJ.xml", "sitemap_reviews_fr_DJ.xml",
        # ar-PS:
        "sitemap_bestfor_ar_PS.xml", "sitemap_workflow_ar_PS.xml", "sitemap_vs_ar_PS.xml",
        "sitemap_seasonal_ar_PS.xml", "sitemap_reviews_ar_PS.xml",
        # pt-GW:
        "sitemap_bestfor_pt_GW.xml", "sitemap_workflow_pt_GW.xml", "sitemap_vs_pt_GW.xml",
        "sitemap_seasonal_pt_GW.xml", "sitemap_reviews_pt_GW.xml",
        # en-ER:
        "sitemap_bestfor_en_ER.xml", "sitemap_workflow_en_ER.xml", "sitemap_vs_en_ER.xml",
        "sitemap_seasonal_en_ER.xml", "sitemap_reviews_en_ER.xml",
        # pt-ST:
        "sitemap_bestfor_pt_ST.xml", "sitemap_workflow_pt_ST.xml", "sitemap_vs_pt_ST.xml",
        "sitemap_seasonal_pt_ST.xml", "sitemap_reviews_pt_ST.xml",
        # en-SO:
        "sitemap_bestfor_en_SO.xml", "sitemap_workflow_en_SO.xml", "sitemap_vs_en_SO.xml",
        "sitemap_seasonal_en_SO.xml", "sitemap_reviews_en_SO.xml",
        # fr-KM:
        "sitemap_bestfor_fr_KM.xml", "sitemap_workflow_fr_KM.xml", "sitemap_vs_fr_KM.xml",
        "sitemap_seasonal_fr_KM.xml", "sitemap_reviews_fr_KM.xml",
        # en-ZW2:
        "sitemap_bestfor_en_ZW2.xml", "sitemap_workflow_en_ZW2.xml", "sitemap_vs_en_ZW2.xml",
        "sitemap_seasonal_en_ZW2.xml", "sitemap_reviews_en_ZW2.xml",
        # fr-SN2:
        "sitemap_bestfor_fr_SN2.xml", "sitemap_workflow_fr_SN2.xml", "sitemap_vs_fr_SN2.xml",
        "sitemap_seasonal_fr_SN2.xml", "sitemap_reviews_fr_SN2.xml",
        # am-ET:
        "sitemap_bestfor_am_ET.xml", "sitemap_workflow_am_ET.xml", "sitemap_vs_am_ET.xml",
        "sitemap_seasonal_am_ET.xml", "sitemap_reviews_am_ET.xml",
        # ti-ER:
        "sitemap_bestfor_ti_ER.xml", "sitemap_workflow_ti_ER.xml", "sitemap_vs_ti_ER.xml",
        "sitemap_seasonal_ti_ER.xml", "sitemap_reviews_ti_ER.xml",
        # ha-NG:
        "sitemap_bestfor_ha_NG.xml", "sitemap_workflow_ha_NG.xml", "sitemap_vs_ha_NG.xml",
        "sitemap_seasonal_ha_NG.xml", "sitemap_reviews_ha_NG.xml",
        # ig-NG:
        "sitemap_bestfor_ig_NG.xml", "sitemap_workflow_ig_NG.xml", "sitemap_vs_ig_NG.xml",
        "sitemap_seasonal_ig_NG.xml", "sitemap_reviews_ig_NG.xml",
        # yo-NG:
        "sitemap_bestfor_yo_NG.xml", "sitemap_workflow_yo_NG.xml", "sitemap_vs_yo_NG.xml",
        "sitemap_seasonal_yo_NG.xml", "sitemap_reviews_yo_NG.xml",
        # ne-NP:
        "sitemap_bestfor_ne_NP.xml", "sitemap_workflow_ne_NP.xml", "sitemap_vs_ne_NP.xml",
        "sitemap_seasonal_ne_NP.xml", "sitemap_reviews_ne_NP.xml",
        # si-LK:
        "sitemap_bestfor_si_LK.xml", "sitemap_workflow_si_LK.xml", "sitemap_vs_si_LK.xml",
        "sitemap_seasonal_si_LK.xml", "sitemap_reviews_si_LK.xml",
        # my-MM:
        "sitemap_bestfor_my_MM.xml", "sitemap_workflow_my_MM.xml", "sitemap_vs_my_MM.xml",
        "sitemap_seasonal_my_MM.xml", "sitemap_reviews_my_MM.xml",
        # km-KH:
        "sitemap_bestfor_km_KH.xml", "sitemap_workflow_km_KH.xml", "sitemap_vs_km_KH.xml",
        "sitemap_seasonal_km_KH.xml", "sitemap_reviews_km_KH.xml",
        # lo-LA:
        "sitemap_bestfor_lo_LA.xml", "sitemap_workflow_lo_LA.xml", "sitemap_vs_lo_LA.xml",
        "sitemap_seasonal_lo_LA.xml", "sitemap_reviews_lo_LA.xml",
        # mn-MN:
        "sitemap_bestfor_mn_MN.xml", "sitemap_workflow_mn_MN.xml", "sitemap_vs_mn_MN.xml",
        "sitemap_seasonal_mn_MN.xml", "sitemap_reviews_mn_MN.xml",
        # ka-GE:
        "sitemap_bestfor_ka_GE.xml", "sitemap_workflow_ka_GE.xml", "sitemap_vs_ka_GE.xml",
        "sitemap_seasonal_ka_GE.xml", "sitemap_reviews_ka_GE.xml",
        # az-AZ:
        "sitemap_bestfor_az_AZ.xml", "sitemap_workflow_az_AZ.xml", "sitemap_vs_az_AZ.xml",
        "sitemap_seasonal_az_AZ.xml", "sitemap_reviews_az_AZ.xml",
        # hy-AM:
        "sitemap_bestfor_hy_AM.xml", "sitemap_workflow_hy_AM.xml", "sitemap_vs_hy_AM.xml",
        "sitemap_seasonal_hy_AM.xml", "sitemap_reviews_hy_AM.xml",
        # uz-UZ:
        "sitemap_bestfor_uz_UZ.xml", "sitemap_workflow_uz_UZ.xml", "sitemap_vs_uz_UZ.xml",
        "sitemap_seasonal_uz_UZ.xml", "sitemap_reviews_uz_UZ.xml",
        # kk-KZ:
        "sitemap_bestfor_kk_KZ.xml", "sitemap_workflow_kk_KZ.xml", "sitemap_vs_kk_KZ.xml",
        "sitemap_seasonal_kk_KZ.xml", "sitemap_reviews_kk_KZ.xml",
        # tg-TJ:
        "sitemap_bestfor_tg_TJ.xml", "sitemap_workflow_tg_TJ.xml", "sitemap_vs_tg_TJ.xml",
        "sitemap_seasonal_tg_TJ.xml", "sitemap_reviews_tg_TJ.xml",
        # tk-TM:
        "sitemap_bestfor_tk_TM.xml", "sitemap_workflow_tk_TM.xml", "sitemap_vs_tk_TM.xml",
        "sitemap_seasonal_tk_TM.xml", "sitemap_reviews_tk_TM.xml",
        # ky-KG:
        "sitemap_bestfor_ky_KG.xml", "sitemap_workflow_ky_KG.xml", "sitemap_vs_ky_KG.xml",
        "sitemap_seasonal_ky_KG.xml", "sitemap_reviews_ky_KG.xml",
        # sq-AL:
        "sitemap_bestfor_sq_AL.xml", "sitemap_workflow_sq_AL.xml", "sitemap_vs_sq_AL.xml",
        "sitemap_seasonal_sq_AL.xml", "sitemap_reviews_sq_AL.xml",
        # bs-BA:
        "sitemap_bestfor_bs_BA.xml", "sitemap_workflow_bs_BA.xml", "sitemap_vs_bs_BA.xml",
        "sitemap_seasonal_bs_BA.xml", "sitemap_reviews_bs_BA.xml",
        # mk-MK:
        "sitemap_bestfor_mk_MK.xml", "sitemap_workflow_mk_MK.xml", "sitemap_vs_mk_MK.xml",
        "sitemap_seasonal_mk_MK.xml", "sitemap_reviews_mk_MK.xml",
        # sr-ME:
        "sitemap_bestfor_sr_ME.xml", "sitemap_workflow_sr_ME.xml", "sitemap_vs_sr_ME.xml",
        "sitemap_seasonal_sr_ME.xml", "sitemap_reviews_sr_ME.xml",
        # lv-LV:
        "sitemap_bestfor_lv_LV.xml", "sitemap_workflow_lv_LV.xml", "sitemap_vs_lv_LV.xml",
        "sitemap_seasonal_lv_LV.xml", "sitemap_reviews_lv_LV.xml",
        # lt-LT:
        "sitemap_bestfor_lt_LT.xml", "sitemap_workflow_lt_LT.xml", "sitemap_vs_lt_LT.xml",
        "sitemap_seasonal_lt_LT.xml", "sitemap_reviews_lt_LT.xml",
        # af-ZA:
        "sitemap_bestfor_af_ZA.xml", "sitemap_workflow_af_ZA.xml", "sitemap_vs_af_ZA.xml",
        "sitemap_seasonal_af_ZA.xml", "sitemap_reviews_af_ZA.xml",
        # zu-ZA:
        "sitemap_bestfor_zu_ZA.xml", "sitemap_workflow_zu_ZA.xml", "sitemap_vs_zu_ZA.xml",
        "sitemap_seasonal_zu_ZA.xml", "sitemap_reviews_zu_ZA.xml",
        # sn-ZW:
        "sitemap_bestfor_sn_ZW.xml", "sitemap_workflow_sn_ZW.xml", "sitemap_vs_sn_ZW.xml",
        "sitemap_seasonal_sn_ZW.xml", "sitemap_reviews_sn_ZW.xml",
        # rw-RW:
        "sitemap_bestfor_rw_RW.xml", "sitemap_workflow_rw_RW.xml", "sitemap_vs_rw_RW.xml",
        "sitemap_seasonal_rw_RW.xml", "sitemap_reviews_rw_RW.xml",
        # om-ET:
        "sitemap_bestfor_om_ET.xml", "sitemap_workflow_om_ET.xml", "sitemap_vs_om_ET.xml",
        "sitemap_seasonal_om_ET.xml", "sitemap_reviews_om_ET.xml",
        # tl-PH:
        "sitemap_bestfor_tl_PH.xml", "sitemap_workflow_tl_PH.xml", "sitemap_vs_tl_PH.xml",
        "sitemap_seasonal_tl_PH.xml", "sitemap_reviews_tl_PH.xml",
        # xh-ZA:
        "sitemap_bestfor_xh_ZA.xml", "sitemap_workflow_xh_ZA.xml", "sitemap_vs_xh_ZA.xml",
        "sitemap_seasonal_xh_ZA.xml", "sitemap_reviews_xh_ZA.xml",
        # ny-MW:
        "sitemap_bestfor_ny_MW.xml", "sitemap_workflow_ny_MW.xml", "sitemap_vs_ny_MW.xml",
        "sitemap_seasonal_ny_MW.xml", "sitemap_reviews_ny_MW.xml",
        # lg-UG:
        "sitemap_bestfor_lg_UG.xml", "sitemap_workflow_lg_UG.xml", "sitemap_vs_lg_UG.xml",
        "sitemap_seasonal_lg_UG.xml", "sitemap_reviews_lg_UG.xml",
        # so-SO:
        "sitemap_bestfor_so_SO.xml", "sitemap_workflow_so_SO.xml", "sitemap_vs_so_SO.xml",
        "sitemap_seasonal_so_SO.xml", "sitemap_reviews_so_SO.xml",
        # gu-IN:
        "sitemap_bestfor_gu_IN.xml", "sitemap_workflow_gu_IN.xml", "sitemap_vs_gu_IN.xml",
        "sitemap_seasonal_gu_IN.xml", "sitemap_reviews_gu_IN.xml",
        # mr-IN:
        "sitemap_bestfor_mr_IN.xml", "sitemap_workflow_mr_IN.xml", "sitemap_vs_mr_IN.xml",
        "sitemap_seasonal_mr_IN.xml", "sitemap_reviews_mr_IN.xml",
        # te-IN:
        "sitemap_bestfor_te_IN.xml", "sitemap_workflow_te_IN.xml", "sitemap_vs_te_IN.xml",
        "sitemap_seasonal_te_IN.xml", "sitemap_reviews_te_IN.xml",
        # kn-IN:
        "sitemap_bestfor_kn_IN.xml", "sitemap_workflow_kn_IN.xml", "sitemap_vs_kn_IN.xml",
        "sitemap_seasonal_kn_IN.xml", "sitemap_reviews_kn_IN.xml",
        # ml-IN:
        "sitemap_bestfor_ml_IN.xml", "sitemap_workflow_ml_IN.xml", "sitemap_vs_ml_IN.xml",
        "sitemap_seasonal_ml_IN.xml", "sitemap_reviews_ml_IN.xml",
        # et-EE:
        "sitemap_bestfor_et_EE.xml", "sitemap_workflow_et_EE.xml", "sitemap_vs_et_EE.xml",
        "sitemap_seasonal_et_EE.xml", "sitemap_reviews_et_EE.xml",
        # sl-SI:
        "sitemap_bestfor_sl_SI.xml", "sitemap_workflow_sl_SI.xml", "sitemap_vs_sl_SI.xml",
        "sitemap_seasonal_sl_SI.xml", "sitemap_reviews_sl_SI.xml",
        # is-IS:
        "sitemap_bestfor_is_IS.xml", "sitemap_workflow_is_IS.xml", "sitemap_vs_is_IS.xml",
        "sitemap_seasonal_is_IS.xml", "sitemap_reviews_is_IS.xml",
        # mt-MT:
        "sitemap_bestfor_mt_MT.xml", "sitemap_workflow_mt_MT.xml", "sitemap_vs_mt_MT.xml",
        "sitemap_seasonal_mt_MT.xml", "sitemap_reviews_mt_MT.xml",
        # cy-GB:
        "sitemap_bestfor_cy_GB.xml", "sitemap_workflow_cy_GB.xml", "sitemap_vs_cy_GB.xml",
        "sitemap_seasonal_cy_GB.xml", "sitemap_reviews_cy_GB.xml",
        # ga-IE:
        "sitemap_bestfor_ga_IE.xml", "sitemap_workflow_ga_IE.xml", "sitemap_vs_ga_IE.xml",
        "sitemap_seasonal_ga_IE.xml", "sitemap_reviews_ga_IE.xml",
        # ca-ES:
        "sitemap_bestfor_ca_ES.xml", "sitemap_workflow_ca_ES.xml", "sitemap_vs_ca_ES.xml",
        "sitemap_seasonal_ca_ES.xml", "sitemap_reviews_ca_ES.xml",
        # eu-ES:
        "sitemap_bestfor_eu_ES.xml", "sitemap_workflow_eu_ES.xml", "sitemap_vs_eu_ES.xml",
        "sitemap_seasonal_eu_ES.xml", "sitemap_reviews_eu_ES.xml",
        # gl-ES:
        "sitemap_bestfor_gl_ES.xml", "sitemap_workflow_gl_ES.xml", "sitemap_vs_gl_ES.xml",
        "sitemap_seasonal_gl_ES.xml", "sitemap_reviews_gl_ES.xml",
        # or-IN:
        "sitemap_bestfor_or_IN.xml", "sitemap_workflow_or_IN.xml", "sitemap_vs_or_IN.xml",
        "sitemap_seasonal_or_IN.xml", "sitemap_reviews_or_IN.xml",
        # pa-IN:
        "sitemap_bestfor_pa_IN.xml", "sitemap_workflow_pa_IN.xml", "sitemap_vs_pa_IN.xml",
        "sitemap_seasonal_pa_IN.xml", "sitemap_reviews_pa_IN.xml",
        # as-IN:
        "sitemap_bestfor_as_IN.xml", "sitemap_workflow_as_IN.xml", "sitemap_vs_as_IN.xml",
        "sitemap_seasonal_as_IN.xml", "sitemap_reviews_as_IN.xml",
        # ps-AF:
        "sitemap_bestfor_ps_AF.xml", "sitemap_workflow_ps_AF.xml", "sitemap_vs_ps_AF.xml",
        "sitemap_seasonal_ps_AF.xml", "sitemap_reviews_ps_AF.xml",
        # sd-PK:
        "sitemap_bestfor_sd_PK.xml", "sitemap_workflow_sd_PK.xml", "sitemap_vs_sd_PK.xml",
        "sitemap_seasonal_sd_PK.xml", "sitemap_reviews_sd_PK.xml",
        # ceb-PH:
        "sitemap_bestfor_ceb_PH.xml", "sitemap_workflow_ceb_PH.xml", "sitemap_vs_ceb_PH.xml",
        "sitemap_seasonal_ceb_PH.xml", "sitemap_reviews_ceb_PH.xml",
        # wo-SN:
        "sitemap_bestfor_wo_SN.xml", "sitemap_workflow_wo_SN.xml", "sitemap_vs_wo_SN.xml",
        "sitemap_seasonal_wo_SN.xml", "sitemap_reviews_wo_SN.xml",
        # ff-SN:
        "sitemap_bestfor_ff_SN.xml", "sitemap_workflow_ff_SN.xml", "sitemap_vs_ff_SN.xml",
        "sitemap_seasonal_ff_SN.xml", "sitemap_reviews_ff_SN.xml",
        # tw-GH:
        "sitemap_bestfor_tw_GH.xml", "sitemap_workflow_tw_GH.xml", "sitemap_vs_tw_GH.xml",
        "sitemap_seasonal_tw_GH.xml", "sitemap_reviews_tw_GH.xml",
        # st-ZA:
        "sitemap_bestfor_st_ZA.xml", "sitemap_workflow_st_ZA.xml", "sitemap_vs_st_ZA.xml",
        "sitemap_seasonal_st_ZA.xml", "sitemap_reviews_st_ZA.xml",
        # lb-LU:
        "sitemap_bestfor_lb_LU.xml", "sitemap_workflow_lb_LU.xml", "sitemap_vs_lb_LU.xml",
        "sitemap_seasonal_lb_LU.xml", "sitemap_reviews_lb_LU.xml",
        # qu-PE:
        "sitemap_bestfor_qu_PE.xml", "sitemap_workflow_qu_PE.xml", "sitemap_vs_qu_PE.xml",
        "sitemap_seasonal_qu_PE.xml", "sitemap_reviews_qu_PE.xml",
        # ht-HT:
        "sitemap_bestfor_ht_HT.xml", "sitemap_workflow_ht_HT.xml", "sitemap_vs_ht_HT.xml",
        "sitemap_seasonal_ht_HT.xml", "sitemap_reviews_ht_HT.xml",
        # mg-MG:
        "sitemap_bestfor_mg_MG.xml", "sitemap_workflow_mg_MG.xml", "sitemap_vs_mg_MG.xml",
        "sitemap_seasonal_mg_MG.xml", "sitemap_reviews_mg_MG.xml",
        # gn-PY:
        "sitemap_bestfor_gn_PY.xml", "sitemap_workflow_gn_PY.xml", "sitemap_vs_gn_PY.xml",
        "sitemap_seasonal_gn_PY.xml", "sitemap_reviews_gn_PY.xml",
        # tt-RU:
        "sitemap_bestfor_tt_RU.xml", "sitemap_workflow_tt_RU.xml", "sitemap_vs_tt_RU.xml",
        "sitemap_seasonal_tt_RU.xml", "sitemap_reviews_tt_RU.xml",
        # ay-BO:
        "sitemap_bestfor_ay_BO.xml", "sitemap_workflow_ay_BO.xml", "sitemap_vs_ay_BO.xml",
        "sitemap_seasonal_ay_BO.xml", "sitemap_reviews_ay_BO.xml",
        # bo-CN:
        "sitemap_bestfor_bo_CN.xml", "sitemap_workflow_bo_CN.xml", "sitemap_vs_bo_CN.xml",
        "sitemap_seasonal_bo_CN.xml", "sitemap_reviews_bo_CN.xml",
        # dz-BT:
        "sitemap_bestfor_dz_BT.xml", "sitemap_workflow_dz_BT.xml", "sitemap_vs_dz_BT.xml",
        "sitemap_seasonal_dz_BT.xml", "sitemap_reviews_dz_BT.xml",
        # sm-WS:
        "sitemap_bestfor_sm_WS.xml", "sitemap_workflow_sm_WS.xml", "sitemap_vs_sm_WS.xml",
        "sitemap_seasonal_sm_WS.xml", "sitemap_reviews_sm_WS.xml",
        # to-TO:
        "sitemap_bestfor_to_TO.xml", "sitemap_workflow_to_TO.xml", "sitemap_vs_to_TO.xml",
        "sitemap_seasonal_to_TO.xml", "sitemap_reviews_to_TO.xml",
        # jv-ID:
        "sitemap_bestfor_jv_ID.xml", "sitemap_workflow_jv_ID.xml", "sitemap_vs_jv_ID.xml",
        "sitemap_seasonal_jv_ID.xml", "sitemap_reviews_jv_ID.xml",
        # su-ID:
        "sitemap_bestfor_su_ID.xml", "sitemap_workflow_su_ID.xml", "sitemap_vs_su_ID.xml",
        "sitemap_seasonal_su_ID.xml", "sitemap_reviews_su_ID.xml",
        # mi-NZ:
        "sitemap_bestfor_mi_NZ.xml", "sitemap_workflow_mi_NZ.xml", "sitemap_vs_mi_NZ.xml",
        "sitemap_seasonal_mi_NZ.xml", "sitemap_reviews_mi_NZ.xml",
        # fj-FJ:
        "sitemap_bestfor_fj_FJ.xml", "sitemap_workflow_fj_FJ.xml", "sitemap_vs_fj_FJ.xml",
        "sitemap_seasonal_fj_FJ.xml", "sitemap_reviews_fj_FJ.xml",
        # ba-RU:
        "sitemap_bestfor_ba_RU.xml", "sitemap_workflow_ba_RU.xml", "sitemap_vs_ba_RU.xml",
        "sitemap_seasonal_ba_RU.xml", "sitemap_reviews_ba_RU.xml",
        # ug-CN kab-DZ sc-IT br-FR cv-RU:
        "sitemap_bestfor_ug_CN.xml", "sitemap_workflow_ug_CN.xml", "sitemap_vs_ug_CN.xml",
        "sitemap_seasonal_ug_CN.xml", "sitemap_reviews_ug_CN.xml",
        "sitemap_bestfor_kab_DZ.xml", "sitemap_workflow_kab_DZ.xml", "sitemap_vs_kab_DZ.xml",
        "sitemap_seasonal_kab_DZ.xml", "sitemap_reviews_kab_DZ.xml",
        "sitemap_bestfor_sc_IT.xml", "sitemap_workflow_sc_IT.xml", "sitemap_vs_sc_IT.xml",
        "sitemap_seasonal_sc_IT.xml", "sitemap_reviews_sc_IT.xml",
        "sitemap_bestfor_br_FR.xml", "sitemap_workflow_br_FR.xml", "sitemap_vs_br_FR.xml",
        "sitemap_seasonal_br_FR.xml", "sitemap_reviews_br_FR.xml",
        "sitemap_bestfor_cv_RU.xml", "sitemap_workflow_cv_RU.xml", "sitemap_vs_cv_RU.xml",
        "sitemap_seasonal_cv_RU.xml", "sitemap_reviews_cv_RU.xml",
        # tn-ZA ve-ZA ss-SZ mad-ID min-ID:
        "sitemap_bestfor_tn_ZA.xml", "sitemap_workflow_tn_ZA.xml", "sitemap_vs_tn_ZA.xml",
        "sitemap_seasonal_tn_ZA.xml", "sitemap_reviews_tn_ZA.xml",
        "sitemap_bestfor_ve_ZA.xml", "sitemap_workflow_ve_ZA.xml", "sitemap_vs_ve_ZA.xml",
        "sitemap_seasonal_ve_ZA.xml", "sitemap_reviews_ve_ZA.xml",
        "sitemap_bestfor_ss_SZ.xml", "sitemap_workflow_ss_SZ.xml", "sitemap_vs_ss_SZ.xml",
        "sitemap_seasonal_ss_SZ.xml", "sitemap_reviews_ss_SZ.xml",
        "sitemap_bestfor_mad_ID.xml", "sitemap_workflow_mad_ID.xml", "sitemap_vs_mad_ID.xml",
        "sitemap_seasonal_mad_ID.xml", "sitemap_reviews_mad_ID.xml",
        "sitemap_bestfor_min_ID.xml", "sitemap_workflow_min_ID.xml", "sitemap_vs_min_ID.xml",
        "sitemap_seasonal_min_ID.xml", "sitemap_reviews_min_ID.xml",
        # bho mai-IN sat-IN gom-IN ks-IN:
        "sitemap_bestfor_bho.xml", "sitemap_workflow_bho.xml", "sitemap_vs_bho.xml",
        "sitemap_seasonal_bho.xml", "sitemap_reviews_bho.xml",
        "sitemap_bestfor_mai_IN.xml", "sitemap_workflow_mai_IN.xml", "sitemap_vs_mai_IN.xml",
        "sitemap_seasonal_mai_IN.xml", "sitemap_reviews_mai_IN.xml",
        "sitemap_bestfor_sat_IN.xml", "sitemap_workflow_sat_IN.xml", "sitemap_vs_sat_IN.xml",
        "sitemap_seasonal_sat_IN.xml", "sitemap_reviews_sat_IN.xml",
        "sitemap_bestfor_gom_IN.xml", "sitemap_workflow_gom_IN.xml", "sitemap_vs_gom_IN.xml",
        "sitemap_seasonal_gom_IN.xml", "sitemap_reviews_gom_IN.xml",
        "sitemap_bestfor_ks_IN.xml", "sitemap_workflow_ks_IN.xml", "sitemap_vs_ks_IN.xml",
        "sitemap_seasonal_ks_IN.xml", "sitemap_reviews_ks_IN.xml",
        # nap vec-IT lmo bug-ID sah-RU:
        "sitemap_bestfor_nap.xml", "sitemap_workflow_nap.xml", "sitemap_vs_nap.xml",
        "sitemap_seasonal_nap.xml", "sitemap_reviews_nap.xml",
        "sitemap_bestfor_vec_IT.xml", "sitemap_workflow_vec_IT.xml", "sitemap_vs_vec_IT.xml",
        "sitemap_seasonal_vec_IT.xml", "sitemap_reviews_vec_IT.xml",
        "sitemap_bestfor_lmo.xml", "sitemap_workflow_lmo.xml", "sitemap_vs_lmo.xml",
        "sitemap_seasonal_lmo.xml", "sitemap_reviews_lmo.xml",
        "sitemap_bestfor_bug_ID.xml", "sitemap_workflow_bug_ID.xml", "sitemap_vs_bug_ID.xml",
        "sitemap_seasonal_bug_ID.xml", "sitemap_reviews_bug_ID.xml",
        "sitemap_bestfor_sah_RU.xml", "sitemap_workflow_sah_RU.xml", "sitemap_vs_sah_RU.xml",
        "sitemap_seasonal_sah_RU.xml", "sitemap_reviews_sah_RU.xml",
        # awa bgc dgo-IN os-RU che-RU:
        "sitemap_bestfor_awa.xml", "sitemap_workflow_awa.xml", "sitemap_vs_awa.xml",
        "sitemap_seasonal_awa.xml", "sitemap_reviews_awa.xml",
        "sitemap_bestfor_bgc.xml", "sitemap_workflow_bgc.xml", "sitemap_vs_bgc.xml",
        "sitemap_seasonal_bgc.xml", "sitemap_reviews_bgc.xml",
        "sitemap_bestfor_dgo_IN.xml", "sitemap_workflow_dgo_IN.xml", "sitemap_vs_dgo_IN.xml",
        "sitemap_seasonal_dgo_IN.xml", "sitemap_reviews_dgo_IN.xml",
        "sitemap_bestfor_os_RU.xml", "sitemap_workflow_os_RU.xml", "sitemap_vs_os_RU.xml",
        "sitemap_seasonal_os_RU.xml", "sitemap_reviews_os_RU.xml",
        "sitemap_bestfor_che_RU.xml", "sitemap_workflow_che_RU.xml", "sitemap_vs_che_RU.xml",
        "sitemap_seasonal_che_RU.xml", "sitemap_reviews_che_RU.xml",
        # ban-ID ace-ID hne mag new-NP:
        "sitemap_bestfor_ban_ID.xml", "sitemap_workflow_ban_ID.xml", "sitemap_vs_ban_ID.xml",
        "sitemap_seasonal_ban_ID.xml", "sitemap_reviews_ban_ID.xml",
        "sitemap_bestfor_ace_ID.xml", "sitemap_workflow_ace_ID.xml", "sitemap_vs_ace_ID.xml",
        "sitemap_seasonal_ace_ID.xml", "sitemap_reviews_ace_ID.xml",
        "sitemap_bestfor_hne.xml", "sitemap_workflow_hne.xml", "sitemap_vs_hne.xml",
        "sitemap_seasonal_hne.xml", "sitemap_reviews_hne.xml",
        "sitemap_bestfor_mag.xml", "sitemap_workflow_mag.xml", "sitemap_vs_mag.xml",
        "sitemap_seasonal_mag.xml", "sitemap_reviews_mag.xml",
        "sitemap_bestfor_new_NP.xml", "sitemap_workflow_new_NP.xml", "sitemap_vs_new_NP.xml",
        "sitemap_seasonal_new_NP.xml", "sitemap_reviews_new_NP.xml",
        # mnw-MM shn-MM zgh-MA fur-IT oc-FR:
        "sitemap_bestfor_mnw_MM.xml", "sitemap_workflow_mnw_MM.xml", "sitemap_vs_mnw_MM.xml",
        "sitemap_seasonal_mnw_MM.xml", "sitemap_reviews_mnw_MM.xml",
        "sitemap_bestfor_shn_MM.xml", "sitemap_workflow_shn_MM.xml", "sitemap_vs_shn_MM.xml",
        "sitemap_seasonal_shn_MM.xml", "sitemap_reviews_shn_MM.xml",
        "sitemap_bestfor_zgh_MA.xml", "sitemap_workflow_zgh_MA.xml", "sitemap_vs_zgh_MA.xml",
        "sitemap_seasonal_zgh_MA.xml", "sitemap_reviews_zgh_MA.xml",
        "sitemap_bestfor_fur_IT.xml", "sitemap_workflow_fur_IT.xml", "sitemap_vs_fur_IT.xml",
        "sitemap_seasonal_fur_IT.xml", "sitemap_reviews_fur_IT.xml",
        "sitemap_bestfor_oc_FR.xml", "sitemap_workflow_oc_FR.xml", "sitemap_vs_oc_FR.xml",
        "sitemap_seasonal_oc_FR.xml", "sitemap_reviews_oc_FR.xml",
        # lij rm-CH co-FR scn-IT wa-BE:
        "sitemap_bestfor_lij.xml", "sitemap_workflow_lij.xml", "sitemap_vs_lij.xml",
        "sitemap_seasonal_lij.xml", "sitemap_reviews_lij.xml",
        "sitemap_bestfor_rm_CH.xml", "sitemap_workflow_rm_CH.xml", "sitemap_vs_rm_CH.xml",
        "sitemap_seasonal_rm_CH.xml", "sitemap_reviews_rm_CH.xml",
        "sitemap_bestfor_co_FR.xml", "sitemap_workflow_co_FR.xml", "sitemap_vs_co_FR.xml",
        "sitemap_seasonal_co_FR.xml", "sitemap_reviews_co_FR.xml",
        "sitemap_bestfor_scn_IT.xml", "sitemap_workflow_scn_IT.xml", "sitemap_vs_scn_IT.xml",
        "sitemap_seasonal_scn_IT.xml", "sitemap_reviews_scn_IT.xml",
        "sitemap_bestfor_wa_BE.xml", "sitemap_workflow_wa_BE.xml", "sitemap_vs_wa_BE.xml",
        "sitemap_seasonal_wa_BE.xml", "sitemap_reviews_wa_BE.xml",
        # pam-PH ilo-PH war-PH bcl-PH pag-PH:
        "sitemap_bestfor_pam_PH.xml", "sitemap_workflow_pam_PH.xml", "sitemap_vs_pam_PH.xml",
        "sitemap_seasonal_pam_PH.xml", "sitemap_reviews_pam_PH.xml",
        "sitemap_bestfor_ilo_PH.xml", "sitemap_workflow_ilo_PH.xml", "sitemap_vs_ilo_PH.xml",
        "sitemap_seasonal_ilo_PH.xml", "sitemap_reviews_ilo_PH.xml",
        "sitemap_bestfor_war_PH.xml", "sitemap_workflow_war_PH.xml", "sitemap_vs_war_PH.xml",
        "sitemap_seasonal_war_PH.xml", "sitemap_reviews_war_PH.xml",
        "sitemap_bestfor_bcl_PH.xml", "sitemap_workflow_bcl_PH.xml", "sitemap_vs_bcl_PH.xml",
        "sitemap_seasonal_bcl_PH.xml", "sitemap_reviews_bcl_PH.xml",
        "sitemap_bestfor_pag_PH.xml", "sitemap_workflow_pag_PH.xml", "sitemap_vs_pag_PH.xml",
        "sitemap_seasonal_pag_PH.xml", "sitemap_reviews_pag_PH.xml",
        # lua-CD mhr myv udm koi:
        "sitemap_bestfor_lua_CD.xml", "sitemap_workflow_lua_CD.xml", "sitemap_vs_lua_CD.xml",
        "sitemap_seasonal_lua_CD.xml", "sitemap_reviews_lua_CD.xml",
        "sitemap_bestfor_mhr.xml", "sitemap_workflow_mhr.xml", "sitemap_vs_mhr.xml",
        "sitemap_seasonal_mhr.xml", "sitemap_reviews_mhr.xml",
        "sitemap_bestfor_myv.xml", "sitemap_workflow_myv.xml", "sitemap_vs_myv.xml",
        "sitemap_seasonal_myv.xml", "sitemap_reviews_myv.xml",
        "sitemap_bestfor_udm.xml", "sitemap_workflow_udm.xml", "sitemap_vs_udm.xml",
        "sitemap_seasonal_udm.xml", "sitemap_reviews_udm.xml",
        "sitemap_bestfor_koi.xml", "sitemap_workflow_koi.xml", "sitemap_vs_koi.xml",
        "sitemap_seasonal_koi.xml", "sitemap_reviews_koi.xml",
        "sitemap_bestfor_bjn_ID.xml", "sitemap_workflow_bjn_ID.xml", "sitemap_vs_bjn_ID.xml",
        "sitemap_seasonal_bjn_ID.xml", "sitemap_reviews_bjn_ID.xml",
        "sitemap_bestfor_mak_ID.xml", "sitemap_workflow_mak_ID.xml", "sitemap_vs_mak_ID.xml",
        "sitemap_seasonal_mak_ID.xml", "sitemap_reviews_mak_ID.xml",
        "sitemap_bestfor_brx_IN.xml", "sitemap_workflow_brx_IN.xml", "sitemap_vs_brx_IN.xml",
        "sitemap_seasonal_brx_IN.xml", "sitemap_reviews_brx_IN.xml",
        "sitemap_bestfor_mni_IN.xml", "sitemap_workflow_mni_IN.xml", "sitemap_vs_mni_IN.xml",
        "sitemap_seasonal_mni_IN.xml", "sitemap_reviews_mni_IN.xml",
        "sitemap_bestfor_bm_ML.xml", "sitemap_workflow_bm_ML.xml", "sitemap_vs_bm_ML.xml",
        "sitemap_seasonal_bm_ML.xml", "sitemap_reviews_bm_ML.xml",
        "sitemap_bestfor_ewe_GH.xml", "sitemap_workflow_ewe_GH.xml", "sitemap_vs_ewe_GH.xml",
        "sitemap_seasonal_ewe_GH.xml", "sitemap_reviews_ewe_GH.xml",
        "sitemap_bestfor_twi_GH.xml", "sitemap_workflow_twi_GH.xml", "sitemap_vs_twi_GH.xml",
        "sitemap_seasonal_twi_GH.xml", "sitemap_reviews_twi_GH.xml",
        "sitemap_bestfor_dyu_CI.xml", "sitemap_workflow_dyu_CI.xml", "sitemap_vs_dyu_CI.xml",
        "sitemap_seasonal_dyu_CI.xml", "sitemap_reviews_dyu_CI.xml",
        "sitemap_bestfor_tcy.xml", "sitemap_workflow_tcy.xml", "sitemap_vs_tcy.xml",
        "sitemap_seasonal_tcy.xml", "sitemap_reviews_tcy.xml",
        "sitemap_bestfor_gag_MD.xml", "sitemap_workflow_gag_MD.xml", "sitemap_vs_gag_MD.xml",
        "sitemap_seasonal_gag_MD.xml", "sitemap_reviews_gag_MD.xml",
        "sitemap_bestfor_nso_ZA.xml", "sitemap_workflow_nso_ZA.xml", "sitemap_vs_nso_ZA.xml",
        "sitemap_seasonal_nso_ZA.xml", "sitemap_reviews_nso_ZA.xml",
        "sitemap_bestfor_ts_ZA.xml", "sitemap_workflow_ts_ZA.xml", "sitemap_vs_ts_ZA.xml",
        "sitemap_seasonal_ts_ZA.xml", "sitemap_reviews_ts_ZA.xml",
        "sitemap_bestfor_nr_ZA.xml", "sitemap_workflow_nr_ZA.xml", "sitemap_vs_nr_ZA.xml",
        "sitemap_seasonal_nr_ZA.xml", "sitemap_reviews_nr_ZA.xml",
        "sitemap_bestfor_pap.xml", "sitemap_workflow_pap.xml", "sitemap_vs_pap.xml",
        "sitemap_seasonal_pap.xml", "sitemap_reviews_pap.xml",
        "sitemap_bestfor_krl.xml", "sitemap_workflow_krl.xml", "sitemap_vs_krl.xml",
        "sitemap_seasonal_krl.xml", "sitemap_reviews_krl.xml",
        "sitemap_bestfor_srn.xml", "sitemap_workflow_srn.xml", "sitemap_vs_srn.xml",
        "sitemap_seasonal_srn.xml", "sitemap_reviews_srn.xml",
        "sitemap_bestfor_gcr.xml", "sitemap_workflow_gcr.xml", "sitemap_vs_gcr.xml",
        "sitemap_seasonal_gcr.xml", "sitemap_reviews_gcr.xml",
        "sitemap_bestfor_kea.xml", "sitemap_workflow_kea.xml", "sitemap_vs_kea.xml",
        "sitemap_seasonal_kea.xml", "sitemap_reviews_kea.xml",
        "sitemap_bestfor_mfe.xml", "sitemap_workflow_mfe.xml", "sitemap_vs_mfe.xml",
        "sitemap_seasonal_mfe.xml", "sitemap_reviews_mfe.xml",
        "sitemap_bestfor_hat.xml", "sitemap_workflow_hat.xml", "sitemap_vs_hat.xml",
        "sitemap_seasonal_hat.xml", "sitemap_reviews_hat.xml",
        "sitemap_bestfor_luo_KE.xml", "sitemap_workflow_luo_KE.xml", "sitemap_vs_luo_KE.xml",
        "sitemap_seasonal_luo_KE.xml", "sitemap_reviews_luo_KE.xml",
        "sitemap_bestfor_kam_KE.xml", "sitemap_workflow_kam_KE.xml", "sitemap_vs_kam_KE.xml",
        "sitemap_seasonal_kam_KE.xml", "sitemap_reviews_kam_KE.xml",
        "sitemap_bestfor_kln_KE.xml", "sitemap_workflow_kln_KE.xml", "sitemap_vs_kln_KE.xml",
        "sitemap_seasonal_kln_KE.xml", "sitemap_reviews_kln_KE.xml",
        "sitemap_bestfor_nyn_UG.xml", "sitemap_workflow_nyn_UG.xml", "sitemap_vs_nyn_UG.xml",
        "sitemap_seasonal_nyn_UG.xml", "sitemap_reviews_nyn_UG.xml",
        "sitemap_bestfor_swc_CD.xml", "sitemap_workflow_swc_CD.xml", "sitemap_vs_swc_CD.xml",
        "sitemap_seasonal_swc_CD.xml", "sitemap_reviews_swc_CD.xml",
        "sitemap_bestfor_wuu.xml", "sitemap_workflow_wuu.xml", "sitemap_vs_wuu.xml",
        "sitemap_seasonal_wuu.xml", "sitemap_reviews_wuu.xml",
        "sitemap_bestfor_gan.xml", "sitemap_workflow_gan.xml", "sitemap_vs_gan.xml",
        "sitemap_seasonal_gan.xml", "sitemap_reviews_gan.xml",
        "sitemap_bestfor_hsn.xml", "sitemap_workflow_hsn.xml", "sitemap_vs_hsn.xml",
        "sitemap_seasonal_hsn.xml", "sitemap_reviews_hsn.xml",
        "sitemap_bestfor_cdo.xml", "sitemap_workflow_cdo.xml", "sitemap_vs_cdo.xml",
        "sitemap_seasonal_cdo.xml", "sitemap_reviews_cdo.xml",
        "sitemap_bestfor_tet.xml", "sitemap_workflow_tet.xml", "sitemap_vs_tet.xml",
        "sitemap_seasonal_tet.xml", "sitemap_reviews_tet.xml",
        "sitemap_bestfor_bci.xml", "sitemap_workflow_bci.xml", "sitemap_vs_bci.xml",
        "sitemap_seasonal_bci.xml", "sitemap_reviews_bci.xml",
        "sitemap_bestfor_dag.xml", "sitemap_workflow_dag.xml", "sitemap_vs_dag.xml",
        "sitemap_seasonal_dag.xml", "sitemap_reviews_dag.xml",
        "sitemap_bestfor_gor_ID.xml", "sitemap_workflow_gor_ID.xml", "sitemap_vs_gor_ID.xml",
        "sitemap_seasonal_gor_ID.xml", "sitemap_reviews_gor_ID.xml",
        "sitemap_bestfor_maz.xml", "sitemap_workflow_maz.xml", "sitemap_vs_maz.xml",
        "sitemap_seasonal_maz.xml", "sitemap_reviews_maz.xml",
        "sitemap_bestfor_tzh.xml", "sitemap_workflow_tzh.xml", "sitemap_vs_tzh.xml",
        "sitemap_seasonal_tzh.xml", "sitemap_reviews_tzh.xml",
        "sitemap_bestfor_nym_TZ.xml", "sitemap_workflow_nym_TZ.xml", "sitemap_vs_nym_TZ.xml",
        "sitemap_seasonal_nym_TZ.xml", "sitemap_reviews_nym_TZ.xml",
        "sitemap_bestfor_suk.xml", "sitemap_workflow_suk.xml", "sitemap_vs_suk.xml",
        "sitemap_seasonal_suk.xml", "sitemap_reviews_suk.xml",
        "sitemap_bestfor_guz_KE.xml", "sitemap_workflow_guz_KE.xml", "sitemap_vs_guz_KE.xml",
        "sitemap_seasonal_guz_KE.xml", "sitemap_reviews_guz_KE.xml",
        "sitemap_bestfor_mer_KE.xml", "sitemap_workflow_mer_KE.xml", "sitemap_vs_mer_KE.xml",
        "sitemap_seasonal_mer_KE.xml", "sitemap_reviews_mer_KE.xml",
        "sitemap_bestfor_cgg_UG.xml", "sitemap_workflow_cgg_UG.xml", "sitemap_vs_cgg_UG.xml",
        "sitemap_seasonal_cgg_UG.xml", "sitemap_reviews_cgg_UG.xml",
        "sitemap_bestfor_xog_UG.xml", "sitemap_workflow_xog_UG.xml", "sitemap_vs_xog_UG.xml",
        "sitemap_seasonal_xog_UG.xml", "sitemap_reviews_xog_UG.xml",
        "sitemap_bestfor_ach_UG.xml", "sitemap_workflow_ach_UG.xml", "sitemap_vs_ach_UG.xml",
        "sitemap_seasonal_ach_UG.xml", "sitemap_reviews_ach_UG.xml",
        "sitemap_bestfor_teo_UG.xml", "sitemap_workflow_teo_UG.xml", "sitemap_vs_teo_UG.xml",
        "sitemap_seasonal_teo_UG.xml", "sitemap_reviews_teo_UG.xml",
        "sitemap_bestfor_mas_KE.xml", "sitemap_workflow_mas_KE.xml", "sitemap_vs_mas_KE.xml",
        "sitemap_seasonal_mas_KE.xml", "sitemap_reviews_mas_KE.xml",
        "sitemap_bestfor_nus_SS.xml", "sitemap_workflow_nus_SS.xml", "sitemap_vs_nus_SS.xml",
        "sitemap_seasonal_nus_SS.xml", "sitemap_reviews_nus_SS.xml",
        "sitemap_bestfor_bej.xml", "sitemap_workflow_bej.xml", "sitemap_vs_bej.xml",
        "sitemap_seasonal_bej.xml", "sitemap_reviews_bej.xml",
        "sitemap_bestfor_din.xml", "sitemap_workflow_din.xml", "sitemap_vs_din.xml",
        "sitemap_seasonal_din.xml", "sitemap_reviews_din.xml",
        "sitemap_bestfor_fij.xml", "sitemap_workflow_fij.xml", "sitemap_vs_fij.xml",
        "sitemap_seasonal_fij.xml", "sitemap_reviews_fij.xml",
        "sitemap_bestfor_sah.xml", "sitemap_workflow_sah.xml", "sitemap_vs_sah.xml",
        "sitemap_seasonal_sah.xml", "sitemap_reviews_sah.xml",
        "sitemap_bestfor_kaa.xml", "sitemap_workflow_kaa.xml", "sitemap_vs_kaa.xml",
        "sitemap_seasonal_kaa.xml", "sitemap_reviews_kaa.xml",
        "sitemap_bestfor_sm.xml", "sitemap_workflow_sm.xml", "sitemap_vs_sm.xml",
        "sitemap_seasonal_sm.xml", "sitemap_reviews_sm.xml",
        "sitemap_bestfor_to.xml", "sitemap_workflow_to.xml", "sitemap_vs_to.xml",
        "sitemap_seasonal_to.xml", "sitemap_reviews_to.xml",
        "sitemap_bestfor_ty.xml", "sitemap_workflow_ty.xml", "sitemap_vs_ty.xml",
        "sitemap_seasonal_ty.xml", "sitemap_reviews_ty.xml",
        "sitemap_bestfor_yua.xml", "sitemap_workflow_yua.xml", "sitemap_vs_yua.xml",
        "sitemap_seasonal_yua.xml", "sitemap_reviews_yua.xml",
        "sitemap_bestfor_che.xml", "sitemap_workflow_che.xml", "sitemap_vs_che.xml",
        "sitemap_seasonal_che.xml", "sitemap_reviews_che.xml",
        "sitemap_bestfor_bua.xml", "sitemap_workflow_bua.xml", "sitemap_vs_bua.xml",
        "sitemap_seasonal_bua.xml", "sitemap_reviews_bua.xml",
        "sitemap_bestfor_tyv.xml", "sitemap_workflow_tyv.xml", "sitemap_vs_tyv.xml",
        "sitemap_seasonal_tyv.xml", "sitemap_reviews_tyv.xml",
        "sitemap_bestfor_inh.xml", "sitemap_workflow_inh.xml", "sitemap_vs_inh.xml",
        "sitemap_seasonal_inh.xml", "sitemap_reviews_inh.xml",
        "sitemap_bestfor_av.xml", "sitemap_workflow_av.xml", "sitemap_vs_av.xml",
        "sitemap_seasonal_av.xml", "sitemap_reviews_av.xml",
        "sitemap_bestfor_nah.xml", "sitemap_workflow_nah.xml", "sitemap_vs_nah.xml",
        "sitemap_seasonal_nah.xml", "sitemap_reviews_nah.xml",
        "sitemap_bestfor_mh.xml", "sitemap_workflow_mh.xml", "sitemap_vs_mh.xml",
        "sitemap_seasonal_mh.xml", "sitemap_reviews_mh.xml",
        "sitemap_bestfor_pau.xml", "sitemap_workflow_pau.xml", "sitemap_vs_pau.xml",
        "sitemap_seasonal_pau.xml", "sitemap_reviews_pau.xml",
        "sitemap_bestfor_chk.xml", "sitemap_workflow_chk.xml", "sitemap_vs_chk.xml",
        "sitemap_seasonal_chk.xml", "sitemap_reviews_chk.xml",
        "sitemap_bestfor_pon.xml", "sitemap_workflow_pon.xml", "sitemap_vs_pon.xml",
        "sitemap_seasonal_pon.xml", "sitemap_reviews_pon.xml",
        "sitemap_bestfor_cos.xml", "sitemap_workflow_cos.xml", "sitemap_vs_cos.xml",
        "sitemap_seasonal_cos.xml", "sitemap_reviews_cos.xml",
        "sitemap_bestfor_sc.xml", "sitemap_workflow_sc.xml", "sitemap_vs_sc.xml",
        "sitemap_seasonal_sc.xml", "sitemap_reviews_sc.xml",
        "sitemap_bestfor_vec.xml", "sitemap_workflow_vec.xml", "sitemap_vs_vec.xml",
        "sitemap_seasonal_vec.xml", "sitemap_reviews_vec.xml",
        "sitemap_bestfor_scn.xml", "sitemap_workflow_scn.xml", "sitemap_vs_scn.xml",
        "sitemap_seasonal_scn.xml", "sitemap_reviews_scn.xml",
        "sitemap_bestfor_fur.xml", "sitemap_workflow_fur.xml", "sitemap_vs_fur.xml",
        "sitemap_seasonal_fur.xml", "sitemap_reviews_fur.xml",
        "sitemap_bestfor_lij.xml", "sitemap_workflow_lij.xml", "sitemap_vs_lij.xml",
        "sitemap_seasonal_lij.xml", "sitemap_reviews_lij.xml",
        "sitemap_bestfor_nap.xml", "sitemap_workflow_nap.xml", "sitemap_vs_nap.xml",
        "sitemap_seasonal_nap.xml", "sitemap_reviews_nap.xml",
        "sitemap_bestfor_pms.xml", "sitemap_workflow_pms.xml", "sitemap_vs_pms.xml",
        "sitemap_seasonal_pms.xml", "sitemap_reviews_pms.xml",
        "sitemap_bestfor_rup.xml", "sitemap_workflow_rup.xml", "sitemap_vs_rup.xml",
        "sitemap_seasonal_rup.xml", "sitemap_reviews_rup.xml",
        "sitemap_bestfor_nds.xml", "sitemap_workflow_nds.xml", "sitemap_vs_nds.xml",
        "sitemap_seasonal_nds.xml", "sitemap_reviews_nds.xml",
        "sitemap_bestfor_zza.xml", "sitemap_workflow_zza.xml", "sitemap_vs_zza.xml",
        "sitemap_seasonal_zza.xml", "sitemap_reviews_zza.xml",
        "sitemap_bestfor_gsw.xml", "sitemap_workflow_gsw.xml", "sitemap_vs_gsw.xml",
        "sitemap_seasonal_gsw.xml", "sitemap_reviews_gsw.xml",
        "sitemap_bestfor_lb.xml", "sitemap_workflow_lb.xml", "sitemap_vs_lb.xml",
        "sitemap_seasonal_lb.xml", "sitemap_reviews_lb.xml",
        "sitemap_bestfor_wln.xml", "sitemap_workflow_wln.xml", "sitemap_vs_wln.xml",
        "sitemap_seasonal_wln.xml", "sitemap_reviews_wln.xml",
        "sitemap_bestfor_rmy.xml", "sitemap_workflow_rmy.xml", "sitemap_vs_rmy.xml",
        "sitemap_seasonal_rmy.xml", "sitemap_reviews_rmy.xml",
        "sitemap_bestfor_oc.xml", "sitemap_workflow_oc.xml", "sitemap_vs_oc.xml",
        "sitemap_seasonal_oc.xml", "sitemap_reviews_oc.xml",
        "sitemap_bestfor_cre.xml", "sitemap_workflow_cre.xml", "sitemap_vs_cre.xml",
        "sitemap_seasonal_cre.xml", "sitemap_reviews_cre.xml",
        "sitemap_bestfor_oji.xml", "sitemap_workflow_oji.xml", "sitemap_vs_oji.xml",
        "sitemap_seasonal_oji.xml", "sitemap_reviews_oji.xml",
        "sitemap_bestfor_iku.xml", "sitemap_workflow_iku.xml", "sitemap_vs_iku.xml",
        "sitemap_seasonal_iku.xml", "sitemap_reviews_iku.xml",
        "sitemap_bestfor_ndc_ZW.xml", "sitemap_workflow_ndc_ZW.xml", "sitemap_vs_ndc_ZW.xml",
        "sitemap_seasonal_ndc_ZW.xml", "sitemap_reviews_ndc_ZW.xml",
        "sitemap_bestfor_sus.xml", "sitemap_workflow_sus.xml", "sitemap_vs_sus.xml",
        "sitemap_seasonal_sus.xml", "sitemap_reviews_sus.xml",
        "sitemap_bestfor_shn.xml", "sitemap_workflow_shn.xml", "sitemap_vs_shn.xml",
        "sitemap_seasonal_shn.xml", "sitemap_reviews_shn.xml",
        "sitemap_bestfor_kac.xml", "sitemap_workflow_kac.xml", "sitemap_vs_kac.xml",
        "sitemap_seasonal_kac.xml", "sitemap_reviews_kac.xml",
        "sitemap_bestfor_tem.xml", "sitemap_workflow_tem.xml", "sitemap_vs_tem.xml",
        "sitemap_seasonal_tem.xml", "sitemap_reviews_tem.xml",
        "sitemap_bestfor_tum.xml", "sitemap_workflow_tum.xml", "sitemap_vs_tum.xml",
        "sitemap_seasonal_tum.xml", "sitemap_reviews_tum.xml",
        "sitemap_bestfor_seh.xml", "sitemap_workflow_seh.xml", "sitemap_vs_seh.xml",
        "sitemap_seasonal_seh.xml", "sitemap_reviews_seh.xml",
        "sitemap_bestfor_new.xml", "sitemap_workflow_new.xml", "sitemap_vs_new.xml",
        "sitemap_seasonal_new.xml", "sitemap_reviews_new.xml",
        "sitemap_bestfor_lez.xml", "sitemap_workflow_lez.xml", "sitemap_vs_lez.xml",
        "sitemap_seasonal_lez.xml", "sitemap_reviews_lez.xml",
        "sitemap_bestfor_dar.xml", "sitemap_workflow_dar.xml", "sitemap_vs_dar.xml",
        "sitemap_seasonal_dar.xml", "sitemap_reviews_dar.xml",
        "sitemap_bestfor_kpe.xml", "sitemap_workflow_kpe.xml", "sitemap_vs_kpe.xml",
        "sitemap_seasonal_kpe.xml", "sitemap_reviews_kpe.xml",
        "sitemap_bestfor_tiv.xml", "sitemap_workflow_tiv.xml", "sitemap_vs_tiv.xml",
        "sitemap_seasonal_tiv.xml", "sitemap_reviews_tiv.xml",
        "sitemap_bestfor_edo.xml", "sitemap_workflow_edo.xml", "sitemap_vs_edo.xml",
        "sitemap_seasonal_edo.xml", "sitemap_reviews_edo.xml",
        "sitemap_bestfor_fon.xml", "sitemap_workflow_fon.xml", "sitemap_vs_fon.xml",
        "sitemap_seasonal_fon.xml", "sitemap_reviews_fon.xml",
        "sitemap_bestfor_luy.xml", "sitemap_workflow_luy.xml", "sitemap_vs_luy.xml",
        "sitemap_seasonal_luy.xml", "sitemap_reviews_luy.xml",
        "sitemap_bestfor_sat.xml", "sitemap_workflow_sat.xml", "sitemap_vs_sat.xml",
        "sitemap_seasonal_sat.xml", "sitemap_reviews_sat.xml",
        "sitemap_bestfor_kok.xml", "sitemap_workflow_kok.xml", "sitemap_vs_kok.xml",
        "sitemap_seasonal_kok.xml", "sitemap_reviews_kok.xml",
        "sitemap_bestfor_wol.xml", "sitemap_workflow_wol.xml", "sitemap_vs_wol.xml",
        "sitemap_seasonal_wol.xml", "sitemap_reviews_wol.xml",
        "sitemap_bestfor_ace.xml", "sitemap_workflow_ace.xml", "sitemap_vs_ace.xml",
        "sitemap_seasonal_ace.xml", "sitemap_reviews_ace.xml",
        "sitemap_bestfor_bug.xml", "sitemap_workflow_bug.xml", "sitemap_vs_bug.xml",
        "sitemap_seasonal_bug.xml", "sitemap_reviews_bug.xml",
        "sitemap_bestfor_quz.xml", "sitemap_workflow_quz.xml", "sitemap_vs_quz.xml",
        "sitemap_seasonal_quz.xml", "sitemap_reviews_quz.xml",
        "sitemap_bestfor_grn.xml", "sitemap_workflow_grn.xml", "sitemap_vs_grn.xml",
        "sitemap_seasonal_grn.xml", "sitemap_reviews_grn.xml",
        "sitemap_bestfor_ibb.xml", "sitemap_workflow_ibb.xml", "sitemap_vs_ibb.xml",
        "sitemap_seasonal_ibb.xml", "sitemap_reviews_ibb.xml",
        "sitemap_bestfor_tvl.xml", "sitemap_workflow_tvl.xml", "sitemap_vs_tvl.xml",
        "sitemap_seasonal_tvl.xml", "sitemap_reviews_tvl.xml",
        "sitemap_bestfor_chr.xml", "sitemap_workflow_chr.xml", "sitemap_vs_chr.xml",
        "sitemap_seasonal_chr.xml", "sitemap_reviews_chr.xml",
        "sitemap_bestfor_qom.xml", "sitemap_workflow_qom.xml", "sitemap_vs_qom.xml",
        "sitemap_seasonal_qom.xml", "sitemap_reviews_qom.xml",
        "sitemap_bestfor_mak.xml", "sitemap_workflow_mak.xml", "sitemap_vs_mak.xml",
        "sitemap_seasonal_mak.xml", "sitemap_reviews_mak.xml",
        "sitemap_bestfor_ewe.xml", "sitemap_workflow_ewe.xml", "sitemap_vs_ewe.xml",
        "sitemap_seasonal_ewe.xml", "sitemap_reviews_ewe.xml",
        "sitemap_bestfor_mos.xml", "sitemap_workflow_mos.xml", "sitemap_vs_mos.xml",
        "sitemap_seasonal_mos.xml", "sitemap_reviews_mos.xml",
        "sitemap_bestfor_dyu.xml", "sitemap_workflow_dyu.xml", "sitemap_vs_dyu.xml",
        "sitemap_seasonal_dyu.xml", "sitemap_reviews_dyu.xml",
        "sitemap_bestfor_aym.xml", "sitemap_workflow_aym.xml", "sitemap_vs_aym.xml",
        "sitemap_seasonal_aym.xml", "sitemap_reviews_aym.xml",
        "sitemap_bestfor_tzm.xml", "sitemap_workflow_tzm.xml", "sitemap_vs_tzm.xml",
        "sitemap_seasonal_tzm.xml", "sitemap_reviews_tzm.xml",
        "sitemap_bestfor_nso.xml", "sitemap_workflow_nso.xml", "sitemap_vs_nso.xml",
        "sitemap_seasonal_nso.xml", "sitemap_reviews_nso.xml",
        "sitemap_bestfor_pcm.xml", "sitemap_workflow_pcm.xml", "sitemap_vs_pcm.xml",
        "sitemap_seasonal_pcm.xml", "sitemap_reviews_pcm.xml",
        "sitemap_bestfor_hil.xml", "sitemap_workflow_hil.xml", "sitemap_vs_hil.xml",
        "sitemap_seasonal_hil.xml", "sitemap_reviews_hil.xml",
        "sitemap_bestfor_war.xml", "sitemap_workflow_war.xml", "sitemap_vs_war.xml",
        "sitemap_seasonal_war.xml", "sitemap_reviews_war.xml",
        "sitemap_bestfor_ilo.xml", "sitemap_workflow_ilo.xml", "sitemap_vs_ilo.xml",
        "sitemap_seasonal_ilo.xml", "sitemap_reviews_ilo.xml",
        "sitemap_bestfor_pag.xml", "sitemap_workflow_pag.xml", "sitemap_vs_pag.xml",
        "sitemap_seasonal_pag.xml", "sitemap_reviews_pag.xml",
        "sitemap_bestfor_bcl.xml", "sitemap_workflow_bcl.xml", "sitemap_vs_bcl.xml",
        "sitemap_seasonal_bcl.xml", "sitemap_reviews_bcl.xml",
        "sitemap_bestfor_krj.xml", "sitemap_workflow_krj.xml", "sitemap_vs_krj.xml",
        "sitemap_seasonal_krj.xml", "sitemap_reviews_krj.xml",
        "sitemap_bestfor_tsg.xml", "sitemap_workflow_tsg.xml", "sitemap_vs_tsg.xml",
        "sitemap_seasonal_tsg.xml", "sitemap_reviews_tsg.xml",
        "sitemap_bestfor_mdh.xml", "sitemap_workflow_mdh.xml", "sitemap_vs_mdh.xml",
        "sitemap_seasonal_mdh.xml", "sitemap_reviews_mdh.xml",
        "sitemap_bestfor_kri.xml", "sitemap_workflow_kri.xml", "sitemap_vs_kri.xml",
        "sitemap_seasonal_kri.xml", "sitemap_reviews_kri.xml",
        "sitemap_bestfor_ven.xml", "sitemap_workflow_ven.xml", "sitemap_vs_ven.xml",
        "sitemap_seasonal_ven.xml", "sitemap_reviews_ven.xml",
        "sitemap_bestfor_tso.xml", "sitemap_workflow_tso.xml", "sitemap_vs_tso.xml",
        "sitemap_seasonal_tso.xml", "sitemap_reviews_tso.xml",
        "sitemap_bestfor_jam.xml", "sitemap_workflow_jam.xml", "sitemap_vs_jam.xml",
        "sitemap_seasonal_jam.xml", "sitemap_reviews_jam.xml",
        "sitemap_bestfor_mwr.xml", "sitemap_workflow_mwr.xml", "sitemap_vs_mwr.xml",
        "sitemap_seasonal_mwr.xml", "sitemap_reviews_mwr.xml",
        "sitemap_bestfor_crs.xml", "sitemap_workflow_crs.xml", "sitemap_vs_crs.xml",
        "sitemap_seasonal_crs.xml", "sitemap_reviews_crs.xml",
        "sitemap_bestfor_pis.xml", "sitemap_workflow_pis.xml", "sitemap_vs_pis.xml",
        "sitemap_seasonal_pis.xml", "sitemap_reviews_pis.xml",
        "sitemap_bestfor_bis.xml", "sitemap_workflow_bis.xml", "sitemap_vs_bis.xml",
        "sitemap_seasonal_bis.xml", "sitemap_reviews_bis.xml",
        "sitemap_bestfor_gcf.xml", "sitemap_workflow_gcf.xml", "sitemap_vs_gcf.xml",
        "sitemap_seasonal_gcf.xml", "sitemap_reviews_gcf.xml",
        "sitemap_bestfor_swb.xml", "sitemap_workflow_swb.xml", "sitemap_vs_swb.xml",
        "sitemap_seasonal_swb.xml", "sitemap_reviews_swb.xml",
        "sitemap_bestfor_rap.xml", "sitemap_workflow_rap.xml", "sitemap_vs_rap.xml",
        "sitemap_seasonal_rap.xml", "sitemap_reviews_rap.xml",
        "sitemap_bestfor_niu.xml", "sitemap_workflow_niu.xml", "sitemap_vs_niu.xml",
        "sitemap_seasonal_niu.xml", "sitemap_reviews_niu.xml",
        "sitemap_bestfor_raj.xml", "sitemap_workflow_raj.xml", "sitemap_vs_raj.xml",
        "sitemap_seasonal_raj.xml", "sitemap_reviews_raj.xml",
        "sitemap_bestfor_gil.xml", "sitemap_workflow_gil.xml", "sitemap_vs_gil.xml",
        "sitemap_seasonal_gil.xml", "sitemap_reviews_gil.xml",
        "sitemap_bestfor_nhx.xml", "sitemap_workflow_nhx.xml", "sitemap_vs_nhx.xml",
        "sitemap_seasonal_nhx.xml", "sitemap_reviews_nhx.xml",
        "sitemap_bestfor_nan.xml", "sitemap_workflow_nan.xml", "sitemap_vs_nan.xml",
        "sitemap_seasonal_nan.xml", "sitemap_reviews_nan.xml",
        "sitemap_bestfor_yue.xml", "sitemap_workflow_yue.xml", "sitemap_vs_yue.xml",
        "sitemap_seasonal_yue.xml", "sitemap_reviews_yue.xml",
        "sitemap_bestfor_hak.xml", "sitemap_workflow_hak.xml", "sitemap_vs_hak.xml",
        "sitemap_seasonal_hak.xml", "sitemap_reviews_hak.xml",
        "sitemap_bestfor_min.xml", "sitemap_workflow_min.xml", "sitemap_vs_min.xml",
        "sitemap_seasonal_min.xml", "sitemap_reviews_min.xml",
        "sitemap_bestfor_akl.xml", "sitemap_workflow_akl.xml", "sitemap_vs_akl.xml",
        "sitemap_seasonal_akl.xml", "sitemap_reviews_akl.xml",
        "sitemap_bestfor_szl.xml", "sitemap_workflow_szl.xml", "sitemap_vs_szl.xml",
        "sitemap_seasonal_szl.xml", "sitemap_reviews_szl.xml",
        "sitemap_bestfor_kab.xml", "sitemap_workflow_kab.xml", "sitemap_vs_kab.xml",
        "sitemap_seasonal_kab.xml", "sitemap_reviews_kab.xml",
        "sitemap_bestfor_mfe.xml", "sitemap_workflow_mfe.xml", "sitemap_vs_mfe.xml",
        "sitemap_seasonal_mfe.xml", "sitemap_reviews_mfe.xml",
        "sitemap_bestfor_pap.xml", "sitemap_workflow_pap.xml", "sitemap_vs_pap.xml",
        "sitemap_seasonal_pap.xml", "sitemap_reviews_pap.xml",
        "sitemap_bestfor_shi.xml", "sitemap_workflow_shi.xml", "sitemap_vs_shi.xml",
        "sitemap_seasonal_shi.xml", "sitemap_reviews_shi.xml",
        "sitemap_bestfor_csb.xml", "sitemap_workflow_csb.xml", "sitemap_vs_csb.xml",
        "sitemap_seasonal_csb.xml", "sitemap_reviews_csb.xml",
        "sitemap_bestfor_rue.xml", "sitemap_workflow_rue.xml", "sitemap_vs_rue.xml",
        "sitemap_seasonal_rue.xml", "sitemap_reviews_rue.xml",
        "sitemap_bestfor_dsb.xml", "sitemap_workflow_dsb.xml", "sitemap_vs_dsb.xml",
        "sitemap_seasonal_dsb.xml", "sitemap_reviews_dsb.xml",
        "sitemap_bestfor_hsb.xml", "sitemap_workflow_hsb.xml", "sitemap_vs_hsb.xml",
        "sitemap_seasonal_hsb.xml", "sitemap_reviews_hsb.xml",
        "sitemap_bestfor_pcd.xml", "sitemap_workflow_pcd.xml", "sitemap_vs_pcd.xml",
        "sitemap_seasonal_pcd.xml", "sitemap_reviews_pcd.xml",
        "sitemap_bestfor_ext.xml", "sitemap_workflow_ext.xml", "sitemap_vs_ext.xml",
        "sitemap_seasonal_ext.xml", "sitemap_reviews_ext.xml",
        "sitemap_bestfor_mwl.xml", "sitemap_workflow_mwl.xml", "sitemap_vs_mwl.xml",
        "sitemap_seasonal_mwl.xml", "sitemap_reviews_mwl.xml",
        "sitemap_bestfor_lld.xml", "sitemap_workflow_lld.xml", "sitemap_vs_lld.xml",
        "sitemap_seasonal_lld.xml", "sitemap_reviews_lld.xml",
        "sitemap_bestfor_frp.xml", "sitemap_workflow_frp.xml", "sitemap_vs_frp.xml",
        "sitemap_seasonal_frp.xml", "sitemap_reviews_frp.xml",
        "sitemap_bestfor_sco.xml", "sitemap_workflow_sco.xml", "sitemap_vs_sco.xml",
        "sitemap_seasonal_sco.xml", "sitemap_reviews_sco.xml",
        "sitemap_bestfor_gag.xml", "sitemap_workflow_gag.xml", "sitemap_vs_gag.xml",
        "sitemap_seasonal_gag.xml", "sitemap_reviews_gag.xml",
        "sitemap_bestfor_xal.xml", "sitemap_workflow_xal.xml", "sitemap_vs_xal.xml",
        "sitemap_seasonal_xal.xml", "sitemap_reviews_xal.xml",
        "sitemap_bestfor_krc.xml", "sitemap_workflow_krc.xml", "sitemap_vs_krc.xml",
        "sitemap_seasonal_krc.xml", "sitemap_reviews_krc.xml",
        "sitemap_bestfor_ady.xml", "sitemap_workflow_ady.xml", "sitemap_vs_ady.xml",
        "sitemap_seasonal_ady.xml", "sitemap_reviews_ady.xml",
        "sitemap_bestfor_kbd.xml", "sitemap_workflow_kbd.xml", "sitemap_vs_kbd.xml",
        "sitemap_seasonal_kbd.xml", "sitemap_reviews_kbd.xml",
        "sitemap_bestfor_mdf.xml", "sitemap_workflow_mdf.xml", "sitemap_vs_mdf.xml",
        "sitemap_seasonal_mdf.xml", "sitemap_reviews_mdf.xml",
        "sitemap_bestfor_kpv.xml", "sitemap_workflow_kpv.xml", "sitemap_vs_kpv.xml",
        "sitemap_seasonal_kpv.xml", "sitemap_reviews_kpv.xml",
        "sitemap_bestfor_liv.xml", "sitemap_workflow_liv.xml", "sitemap_vs_liv.xml",
        "sitemap_seasonal_liv.xml", "sitemap_reviews_liv.xml",
        "sitemap_bestfor_sma.xml", "sitemap_workflow_sma.xml", "sitemap_vs_sma.xml",
        "sitemap_seasonal_sma.xml", "sitemap_reviews_sma.xml",
        "sitemap_bestfor_smj.xml", "sitemap_workflow_smj.xml", "sitemap_vs_smj.xml",
        "sitemap_seasonal_smj.xml", "sitemap_reviews_smj.xml",
        "sitemap_bestfor_sms.xml", "sitemap_workflow_sms.xml", "sitemap_vs_sms.xml",
        "sitemap_seasonal_sms.xml", "sitemap_reviews_sms.xml",
        "sitemap_bestfor_smn.xml", "sitemap_workflow_smn.xml", "sitemap_vs_smn.xml",
        "sitemap_seasonal_smn.xml", "sitemap_reviews_smn.xml",
        "sitemap_bestfor_olo.xml", "sitemap_workflow_olo.xml", "sitemap_vs_olo.xml",
        "sitemap_seasonal_olo.xml", "sitemap_reviews_olo.xml",
        "sitemap_bestfor_mer.xml", "sitemap_workflow_mer.xml", "sitemap_vs_mer.xml",
        "sitemap_seasonal_mer.xml", "sitemap_reviews_mer.xml",
        "sitemap_bestfor_guz.xml", "sitemap_workflow_guz.xml", "sitemap_vs_guz.xml",
        "sitemap_seasonal_guz.xml", "sitemap_reviews_guz.xml",
        "sitemap_bestfor_kam.xml", "sitemap_workflow_kam.xml", "sitemap_vs_kam.xml",
        "sitemap_seasonal_kam.xml", "sitemap_reviews_kam.xml",
        "sitemap_bestfor_luo.xml", "sitemap_workflow_luo.xml", "sitemap_vs_luo.xml",
        "sitemap_seasonal_luo.xml", "sitemap_reviews_luo.xml",
        "sitemap_bestfor_saq.xml", "sitemap_workflow_saq.xml", "sitemap_vs_saq.xml",
        "sitemap_seasonal_saq.xml", "sitemap_reviews_saq.xml",
        "sitemap_bestfor_mas.xml", "sitemap_workflow_mas.xml", "sitemap_vs_mas.xml",
        "sitemap_seasonal_mas.xml", "sitemap_reviews_mas.xml",
        "sitemap_bestfor_dav.xml", "sitemap_workflow_dav.xml", "sitemap_vs_dav.xml",
        "sitemap_seasonal_dav.xml", "sitemap_reviews_dav.xml",
        "sitemap_bestfor_teo.xml", "sitemap_workflow_teo.xml", "sitemap_vs_teo.xml",
        "sitemap_seasonal_teo.xml", "sitemap_reviews_teo.xml",
        "sitemap_bestfor_cgg.xml", "sitemap_workflow_cgg.xml", "sitemap_vs_cgg.xml",
        "sitemap_seasonal_cgg.xml", "sitemap_reviews_cgg.xml",
        "sitemap_bestfor_nyn.xml", "sitemap_workflow_nyn.xml", "sitemap_vs_nyn.xml",
        "sitemap_seasonal_nyn.xml", "sitemap_reviews_nyn.xml",
        "sitemap_bestfor_xog.xml", "sitemap_workflow_xog.xml", "sitemap_vs_xog.xml",
        "sitemap_seasonal_xog.xml", "sitemap_reviews_xog.xml",
        "sitemap_bestfor_ach.xml", "sitemap_workflow_ach.xml", "sitemap_vs_ach.xml",
        "sitemap_seasonal_ach.xml", "sitemap_reviews_ach.xml",
        "sitemap_bestfor_laj.xml", "sitemap_workflow_laj.xml", "sitemap_vs_laj.xml",
        "sitemap_seasonal_laj.xml", "sitemap_reviews_laj.xml",
        "sitemap_bestfor_niq.xml", "sitemap_workflow_niq.xml", "sitemap_vs_niq.xml",
        "sitemap_seasonal_niq.xml", "sitemap_reviews_niq.xml",
        "sitemap_bestfor_bas.xml", "sitemap_workflow_bas.xml", "sitemap_vs_bas.xml",
        "sitemap_seasonal_bas.xml", "sitemap_reviews_bas.xml",
        "sitemap_bestfor_bum.xml", "sitemap_workflow_bum.xml", "sitemap_vs_bum.xml",
        "sitemap_seasonal_bum.xml", "sitemap_reviews_bum.xml",
        "sitemap_bestfor_mgo.xml", "sitemap_workflow_mgo.xml", "sitemap_vs_mgo.xml",
        "sitemap_seasonal_mgo.xml", "sitemap_reviews_mgo.xml",
        "sitemap_bestfor_aeb.xml", "sitemap_workflow_aeb.xml", "sitemap_vs_aeb.xml",
        "sitemap_seasonal_aeb.xml", "sitemap_reviews_aeb.xml",
        "sitemap_bestfor_zgh.xml", "sitemap_workflow_zgh.xml", "sitemap_vs_zgh.xml",
        "sitemap_seasonal_zgh.xml", "sitemap_reviews_zgh.xml",
        "sitemap_bestfor_sid.xml", "sitemap_workflow_sid.xml", "sitemap_vs_sid.xml",
        "sitemap_seasonal_sid.xml", "sitemap_reviews_sid.xml",
        "sitemap_bestfor_wal.xml", "sitemap_workflow_wal.xml", "sitemap_vs_wal.xml",
        "sitemap_seasonal_wal.xml", "sitemap_reviews_wal.xml",
        "sitemap_bestfor_amo.xml", "sitemap_workflow_amo.xml", "sitemap_vs_amo.xml",
        "sitemap_seasonal_amo.xml", "sitemap_reviews_amo.xml",
        "sitemap_bestfor_rif.xml", "sitemap_workflow_rif.xml", "sitemap_vs_rif.xml",
        "sitemap_seasonal_rif.xml", "sitemap_reviews_rif.xml",
        "sitemap_bestfor_gez.xml", "sitemap_workflow_gez.xml", "sitemap_vs_gez.xml",
        "sitemap_seasonal_gez.xml", "sitemap_reviews_gez.xml",
        "sitemap_bestfor_snn.xml", "sitemap_workflow_snn.xml", "sitemap_vs_snn.xml",
        "sitemap_seasonal_snn.xml", "sitemap_reviews_snn.xml",
        "sitemap_bestfor_tig.xml", "sitemap_workflow_tig.xml", "sitemap_vs_tig.xml",
        "sitemap_seasonal_tig.xml", "sitemap_reviews_tig.xml",
        "sitemap_bestfor_fub.xml", "sitemap_workflow_fub.xml", "sitemap_vs_fub.xml",
        "sitemap_seasonal_fub.xml", "sitemap_reviews_fub.xml",
        "sitemap_bestfor_twi.xml", "sitemap_workflow_twi.xml", "sitemap_vs_twi.xml",
        "sitemap_seasonal_twi.xml", "sitemap_reviews_twi.xml",
        "sitemap_bestfor_fat.xml", "sitemap_workflow_fat.xml", "sitemap_vs_fat.xml",
        "sitemap_seasonal_fat.xml", "sitemap_reviews_fat.xml",
        "sitemap_bestfor_gaa.xml", "sitemap_workflow_gaa.xml", "sitemap_vs_gaa.xml",
        "sitemap_seasonal_gaa.xml", "sitemap_reviews_gaa.xml",
        "sitemap_bestfor_ada.xml", "sitemap_workflow_ada.xml", "sitemap_vs_ada.xml",
        "sitemap_seasonal_ada.xml", "sitemap_reviews_ada.xml",
        "sitemap_bestfor_nmg.xml", "sitemap_workflow_nmg.xml", "sitemap_vs_nmg.xml",
        "sitemap_seasonal_nmg.xml", "sitemap_reviews_nmg.xml",
        "sitemap_bestfor_nnh.xml", "sitemap_workflow_nnh.xml", "sitemap_vs_nnh.xml",
        "sitemap_seasonal_nnh.xml", "sitemap_reviews_nnh.xml",
        "sitemap_bestfor_agq.xml", "sitemap_workflow_agq.xml", "sitemap_vs_agq.xml",
        "sitemap_seasonal_agq.xml", "sitemap_reviews_agq.xml",
        "sitemap_bestfor_jgo.xml", "sitemap_workflow_jgo.xml", "sitemap_vs_jgo.xml",
        "sitemap_seasonal_jgo.xml", "sitemap_reviews_jgo.xml",
        "sitemap_bestfor_ksf.xml", "sitemap_workflow_ksf.xml", "sitemap_vs_ksf.xml",
        "sitemap_seasonal_ksf.xml", "sitemap_reviews_ksf.xml",
        "sitemap_bestfor_mua.xml", "sitemap_workflow_mua.xml", "sitemap_vs_mua.xml",
        "sitemap_seasonal_mua.xml", "sitemap_reviews_mua.xml",
        "sitemap_bestfor_dua.xml", "sitemap_workflow_dua.xml", "sitemap_vs_dua.xml",
        "sitemap_seasonal_dua.xml", "sitemap_reviews_dua.xml",
        "sitemap_bestfor_kkj.xml", "sitemap_workflow_kkj.xml", "sitemap_vs_kkj.xml",
        "sitemap_seasonal_kkj.xml", "sitemap_reviews_kkj.xml",
        "sitemap_bestfor_yav.xml", "sitemap_workflow_yav.xml", "sitemap_vs_yav.xml",
        "sitemap_seasonal_yav.xml", "sitemap_reviews_yav.xml",
        "sitemap_bestfor_byv.xml", "sitemap_workflow_byv.xml", "sitemap_vs_byv.xml",
        "sitemap_seasonal_byv.xml", "sitemap_reviews_byv.xml",
        "sitemap_bestfor_bkm.xml", "sitemap_workflow_bkm.xml", "sitemap_vs_bkm.xml",
        "sitemap_seasonal_bkm.xml", "sitemap_reviews_bkm.xml",
        "sitemap_bestfor_ebu.xml", "sitemap_workflow_ebu.xml", "sitemap_vs_ebu.xml",
        "sitemap_seasonal_ebu.xml", "sitemap_reviews_ebu.xml",
        "sitemap_bestfor_vun.xml", "sitemap_workflow_vun.xml", "sitemap_vs_vun.xml",
        "sitemap_seasonal_vun.xml", "sitemap_reviews_vun.xml",
        "sitemap_bestfor_asa.xml", "sitemap_workflow_asa.xml", "sitemap_vs_asa.xml",
        "sitemap_seasonal_asa.xml", "sitemap_reviews_asa.xml",
        "sitemap_bestfor_bez.xml", "sitemap_workflow_bez.xml", "sitemap_vs_bez.xml",
        "sitemap_seasonal_bez.xml", "sitemap_reviews_bez.xml",
        "sitemap_bestfor_kde.xml", "sitemap_workflow_kde.xml", "sitemap_vs_kde.xml",
        "sitemap_seasonal_kde.xml", "sitemap_reviews_kde.xml",
        "sitemap_bestfor_lag.xml", "sitemap_workflow_lag.xml", "sitemap_vs_lag.xml",
        "sitemap_seasonal_lag.xml", "sitemap_reviews_lag.xml",
        "sitemap_bestfor_rwk.xml", "sitemap_workflow_rwk.xml", "sitemap_vs_rwk.xml",
        "sitemap_seasonal_rwk.xml", "sitemap_reviews_rwk.xml",
        "sitemap_bestfor_sbp.xml", "sitemap_workflow_sbp.xml", "sitemap_vs_sbp.xml",
        "sitemap_seasonal_sbp.xml", "sitemap_reviews_sbp.xml",
        "sitemap_bestfor_jmc.xml", "sitemap_workflow_jmc.xml", "sitemap_vs_jmc.xml",
        "sitemap_seasonal_jmc.xml", "sitemap_reviews_jmc.xml",
        "sitemap_bestfor_rof.xml", "sitemap_workflow_rof.xml", "sitemap_vs_rof.xml",
        "sitemap_seasonal_rof.xml", "sitemap_reviews_rof.xml",
        "sitemap_bestfor_kln.xml", "sitemap_workflow_kln.xml", "sitemap_vs_kln.xml",
        "sitemap_seasonal_kln.xml", "sitemap_reviews_kln.xml",
        "sitemap_bestfor_dga.xml", "sitemap_workflow_dga.xml", "sitemap_vs_dga.xml",
        "sitemap_seasonal_dga.xml", "sitemap_reviews_dga.xml",
        "sitemap_bestfor_mgh.xml", "sitemap_workflow_mgh.xml", "sitemap_vs_mgh.xml",
        "sitemap_seasonal_mgh.xml", "sitemap_reviews_mgh.xml",
        "sitemap_bestfor_brx.xml", "sitemap_workflow_brx.xml", "sitemap_vs_brx.xml",
        "sitemap_seasonal_brx.xml", "sitemap_reviews_brx.xml",
        "sitemap_bestfor_mzn.xml", "sitemap_workflow_mzn.xml", "sitemap_vs_mzn.xml",
        "sitemap_seasonal_mzn.xml", "sitemap_reviews_mzn.xml",
        "sitemap_bestfor_glk.xml", "sitemap_workflow_glk.xml", "sitemap_vs_glk.xml",
        "sitemap_seasonal_glk.xml", "sitemap_reviews_glk.xml",
        "sitemap_bestfor_lrc.xml", "sitemap_workflow_lrc.xml", "sitemap_vs_lrc.xml",
        "sitemap_seasonal_lrc.xml", "sitemap_reviews_lrc.xml",
        "sitemap_bestfor_haz.xml", "sitemap_workflow_haz.xml", "sitemap_vs_haz.xml",
        "sitemap_seasonal_haz.xml", "sitemap_reviews_haz.xml",
        "sitemap_bestfor_dcc.xml", "sitemap_workflow_dcc.xml", "sitemap_vs_dcc.xml",
        "sitemap_seasonal_dcc.xml", "sitemap_reviews_dcc.xml",
        "sitemap_bestfor_wtm.xml", "sitemap_workflow_wtm.xml", "sitemap_vs_wtm.xml",
        "sitemap_seasonal_wtm.xml", "sitemap_reviews_wtm.xml",
        "sitemap_bestfor_skr.xml", "sitemap_workflow_skr.xml", "sitemap_vs_skr.xml",
        "sitemap_seasonal_skr.xml", "sitemap_reviews_skr.xml",
        "sitemap_bestfor_bgn.xml", "sitemap_workflow_bgn.xml", "sitemap_vs_bgn.xml",
        "sitemap_seasonal_bgn.xml", "sitemap_reviews_bgn.xml",
        "sitemap_bestfor_xmf.xml", "sitemap_workflow_xmf.xml", "sitemap_vs_xmf.xml",
        "sitemap_seasonal_xmf.xml", "sitemap_reviews_xmf.xml",
        "sitemap_bestfor_kum.xml", "sitemap_workflow_kum.xml", "sitemap_vs_kum.xml",
        "sitemap_seasonal_kum.xml", "sitemap_reviews_kum.xml",
        "sitemap_bestfor_kpy.xml", "sitemap_workflow_kpy.xml", "sitemap_vs_kpy.xml",
        "sitemap_seasonal_kpy.xml", "sitemap_reviews_kpy.xml",
        "sitemap_bestfor_tab.xml", "sitemap_workflow_tab.xml", "sitemap_vs_tab.xml",
        "sitemap_seasonal_tab.xml", "sitemap_reviews_tab.xml",
        "sitemap_bestfor_nog.xml", "sitemap_workflow_nog.xml", "sitemap_vs_nog.xml",
        "sitemap_seasonal_nog.xml", "sitemap_reviews_nog.xml",
        "sitemap_bestfor_lbe.xml", "sitemap_workflow_lbe.xml", "sitemap_vs_lbe.xml",
        "sitemap_seasonal_lbe.xml", "sitemap_reviews_lbe.xml",
        "sitemap_bestfor_tay.xml", "sitemap_workflow_tay.xml", "sitemap_vs_tay.xml",
        "sitemap_seasonal_tay.xml", "sitemap_reviews_tay.xml",
        "sitemap_bestfor_ami.xml", "sitemap_workflow_ami.xml", "sitemap_vs_ami.xml",
        "sitemap_seasonal_ami.xml", "sitemap_reviews_ami.xml",
        "sitemap_bestfor_dtp.xml", "sitemap_workflow_dtp.xml", "sitemap_vs_dtp.xml",
        "sitemap_seasonal_dtp.xml", "sitemap_reviews_dtp.xml",
        "sitemap_bestfor_hnj.xml", "sitemap_workflow_hnj.xml", "sitemap_vs_hnj.xml",
        "sitemap_seasonal_hnj.xml", "sitemap_reviews_hnj.xml",
        "sitemap_bestfor_blt.xml", "sitemap_workflow_blt.xml", "sitemap_vs_blt.xml",
        "sitemap_seasonal_blt.xml", "sitemap_reviews_blt.xml",
        "sitemap_bestfor_mfa.xml", "sitemap_workflow_mfa.xml", "sitemap_vs_mfa.xml",
        "sitemap_seasonal_mfa.xml", "sitemap_reviews_mfa.xml",
        "sitemap_bestfor_cjy.xml", "sitemap_workflow_cjy.xml", "sitemap_vs_cjy.xml",
        "sitemap_seasonal_cjy.xml", "sitemap_reviews_cjy.xml",
        "sitemap_bestfor_kek.xml", "sitemap_workflow_kek.xml", "sitemap_vs_kek.xml",
        "sitemap_seasonal_kek.xml", "sitemap_reviews_kek.xml",
        "sitemap_bestfor_quc.xml", "sitemap_workflow_quc.xml", "sitemap_vs_quc.xml",
        "sitemap_seasonal_quc.xml", "sitemap_reviews_quc.xml",
        "sitemap_bestfor_cak.xml", "sitemap_workflow_cak.xml", "sitemap_vs_cak.xml",
        "sitemap_seasonal_cak.xml", "sitemap_reviews_cak.xml",
        "sitemap_bestfor_tzo.xml", "sitemap_workflow_tzo.xml", "sitemap_vs_tzo.xml",
        "sitemap_seasonal_tzo.xml", "sitemap_reviews_tzo.xml",
        "sitemap_bestfor_mam.xml", "sitemap_workflow_mam.xml", "sitemap_vs_mam.xml",
        "sitemap_seasonal_mam.xml", "sitemap_reviews_mam.xml",
        "sitemap_bestfor_nav.xml", "sitemap_workflow_nav.xml", "sitemap_vs_nav.xml",
        "sitemap_seasonal_nav.xml", "sitemap_reviews_nav.xml",
        "sitemap_bestfor_arn.xml", "sitemap_workflow_arn.xml", "sitemap_vs_arn.xml",
        "sitemap_seasonal_arn.xml", "sitemap_reviews_arn.xml",
        "sitemap_bestfor_toj.xml", "sitemap_workflow_toj.xml", "sitemap_vs_toj.xml",
        "sitemap_seasonal_toj.xml", "sitemap_reviews_toj.xml",
        "sitemap_bestfor_ikt.xml", "sitemap_workflow_ikt.xml", "sitemap_vs_ikt.xml",
        "sitemap_seasonal_ikt.xml", "sitemap_reviews_ikt.xml",
        "sitemap_bestfor_tzj.xml", "sitemap_workflow_tzj.xml", "sitemap_vs_tzj.xml",
        "sitemap_seasonal_tzj.xml", "sitemap_reviews_tzj.xml",
        "sitemap_bestfor_guc.xml", "sitemap_workflow_guc.xml", "sitemap_vs_guc.xml",
        "sitemap_seasonal_guc.xml", "sitemap_reviews_guc.xml",
        "sitemap_bestfor_urh.xml", "sitemap_workflow_urh.xml", "sitemap_vs_urh.xml",
        "sitemap_seasonal_urh.xml", "sitemap_reviews_urh.xml",
        "sitemap_bestfor_idu.xml", "sitemap_workflow_idu.xml", "sitemap_vs_idu.xml",
        "sitemap_seasonal_idu.xml", "sitemap_reviews_idu.xml",
        "sitemap_bestfor_ixl.xml", "sitemap_workflow_ixl.xml", "sitemap_vs_ixl.xml",
        "sitemap_seasonal_ixl.xml", "sitemap_reviews_ixl.xml",
        "sitemap_bestfor_cni.xml", "sitemap_workflow_cni.xml", "sitemap_vs_cni.xml",
        "sitemap_seasonal_cni.xml", "sitemap_reviews_cni.xml",
        "sitemap_bestfor_pwo.xml", "sitemap_workflow_pwo.xml", "sitemap_vs_pwo.xml",
        "sitemap_seasonal_pwo.xml", "sitemap_reviews_pwo.xml",
        "sitemap_bestfor_mnw.xml", "sitemap_workflow_mnw.xml", "sitemap_vs_mnw.xml",
        "sitemap_seasonal_mnw.xml", "sitemap_reviews_mnw.xml",
        "sitemap_bestfor_blk.xml", "sitemap_workflow_blk.xml", "sitemap_vs_blk.xml",
        "sitemap_seasonal_blk.xml", "sitemap_reviews_blk.xml",
        "sitemap_bestfor_igl.xml", "sitemap_workflow_igl.xml", "sitemap_vs_igl.xml",
        "sitemap_seasonal_igl.xml", "sitemap_reviews_igl.xml",
        "sitemap_bestfor_bin.xml", "sitemap_workflow_bin.xml", "sitemap_vs_bin.xml",
        "sitemap_seasonal_bin.xml", "sitemap_reviews_bin.xml",
        "sitemap_bestfor_tpi.xml", "sitemap_workflow_tpi.xml", "sitemap_vs_tpi.xml",
        "sitemap_seasonal_tpi.xml", "sitemap_reviews_tpi.xml",
        "sitemap_bestfor_pam.xml", "sitemap_workflow_pam.xml", "sitemap_vs_pam.xml",
        "sitemap_seasonal_pam.xml", "sitemap_reviews_pam.xml",
        "sitemap_bestfor_dzo.xml", "sitemap_workflow_dzo.xml", "sitemap_vs_dzo.xml",
        "sitemap_seasonal_dzo.xml", "sitemap_reviews_dzo.xml",
        "sitemap_bestfor_kha.xml", "sitemap_workflow_kha.xml", "sitemap_vs_kha.xml",
        "sitemap_seasonal_kha.xml", "sitemap_reviews_kha.xml",
        "sitemap_bestfor_nia.xml", "sitemap_workflow_nia.xml", "sitemap_vs_nia.xml",
        "sitemap_seasonal_nia.xml", "sitemap_reviews_nia.xml",
        "sitemap_bestfor_ndc.xml", "sitemap_workflow_ndc.xml", "sitemap_vs_ndc.xml",
        "sitemap_seasonal_ndc.xml", "sitemap_reviews_ndc.xml",
        "sitemap_bestfor_mni.xml", "sitemap_workflow_mni.xml", "sitemap_vs_mni.xml",
        "sitemap_seasonal_mni.xml", "sitemap_reviews_mni.xml",
        "sitemap_bestfor_doi.xml", "sitemap_workflow_doi.xml", "sitemap_vs_doi.xml",
        "sitemap_seasonal_doi.xml", "sitemap_reviews_doi.xml",
        "sitemap_bestfor_lug.xml", "sitemap_workflow_lug.xml", "sitemap_vs_lug.xml",
        "sitemap_seasonal_lug.xml", "sitemap_reviews_lug.xml",
        "sitemap_bestfor_kin.xml", "sitemap_workflow_kin.xml", "sitemap_vs_kin.xml",
        "sitemap_seasonal_kin.xml", "sitemap_reviews_kin.xml",
        "sitemap_bestfor_run.xml", "sitemap_workflow_run.xml", "sitemap_vs_run.xml",
        "sitemap_seasonal_run.xml", "sitemap_reviews_run.xml",
        "sitemap_bestfor_lmn.xml", "sitemap_workflow_lmn.xml", "sitemap_vs_lmn.xml",
        "sitemap_seasonal_lmn.xml", "sitemap_reviews_lmn.xml",
        "sitemap_bestfor_gon.xml", "sitemap_workflow_gon.xml", "sitemap_vs_gon.xml",
        "sitemap_seasonal_gon.xml", "sitemap_reviews_gon.xml",
        "sitemap_bestfor_crh.xml", "sitemap_workflow_crh.xml", "sitemap_vs_crh.xml",
        "sitemap_seasonal_crh.xml", "sitemap_reviews_crh.xml",
        "sitemap_bestfor_ton.xml", "sitemap_workflow_ton.xml", "sitemap_vs_ton.xml",
        "sitemap_seasonal_ton.xml", "sitemap_reviews_ton.xml",
        "sitemap_bestfor_lad.xml", "sitemap_workflow_lad.xml", "sitemap_vs_lad.xml",
        "sitemap_seasonal_lad.xml", "sitemap_reviews_lad.xml",
        "sitemap_bestfor_bhi.xml", "sitemap_workflow_bhi.xml", "sitemap_vs_bhi.xml",
        "sitemap_seasonal_bhi.xml", "sitemap_reviews_bhi.xml",
        "sitemap_bestfor_tly.xml", "sitemap_workflow_tly.xml", "sitemap_vs_tly.xml",
        "sitemap_seasonal_tly.xml", "sitemap_reviews_tly.xml",
        "sitemap_bestfor_bew.xml", "sitemap_workflow_bew.xml", "sitemap_vs_bew.xml",
        "sitemap_seasonal_bew.xml", "sitemap_reviews_bew.xml",
        "sitemap_bestfor_bgp.xml", "sitemap_workflow_bgp.xml", "sitemap_vs_bgp.xml",
        "sitemap_seasonal_bgp.xml", "sitemap_reviews_bgp.xml",
        "sitemap_bestfor_ksb.xml", "sitemap_workflow_ksb.xml", "sitemap_vs_ksb.xml",
        "sitemap_seasonal_ksb.xml", "sitemap_reviews_ksb.xml",
        "sitemap_bestfor_nus.xml", "sitemap_workflow_nus.xml", "sitemap_vs_nus.xml",
        "sitemap_seasonal_nus.xml", "sitemap_reviews_nus.xml",
        "sitemap_bestfor_bsq.xml", "sitemap_workflow_bsq.xml", "sitemap_vs_bsq.xml",
        "sitemap_seasonal_bsq.xml", "sitemap_reviews_bsq.xml",
        "sitemap_bestfor_men.xml", "sitemap_workflow_men.xml", "sitemap_vs_men.xml",
        "sitemap_seasonal_men.xml", "sitemap_reviews_men.xml",
        "sitemap_bestfor_naq.xml", "sitemap_workflow_naq.xml", "sitemap_vs_naq.xml",
        "sitemap_seasonal_naq.xml", "sitemap_reviews_naq.xml",
        "sitemap_bestfor_fuv.xml", "sitemap_workflow_fuv.xml", "sitemap_vs_fuv.xml",
        "sitemap_seasonal_fuv.xml", "sitemap_reviews_fuv.xml",
        "sitemap_bestfor_kmb.xml", "sitemap_workflow_kmb.xml", "sitemap_vs_kmb.xml",
        "sitemap_seasonal_kmb.xml", "sitemap_reviews_kmb.xml",
        "sitemap_bestfor_lua.xml", "sitemap_workflow_lua.xml", "sitemap_vs_lua.xml",
        "sitemap_seasonal_lua.xml", "sitemap_reviews_lua.xml",
        "sitemap_bestfor_mnk.xml", "sitemap_workflow_mnk.xml", "sitemap_vs_mnk.xml",
        "sitemap_seasonal_mnk.xml", "sitemap_reviews_mnk.xml",
        "sitemap_bestfor_lus.xml", "sitemap_workflow_lus.xml", "sitemap_vs_lus.xml",
        "sitemap_seasonal_lus.xml", "sitemap_reviews_lus.xml",
        "sitemap_bestfor_kby.xml", "sitemap_workflow_kby.xml", "sitemap_vs_kby.xml",
        "sitemap_seasonal_kby.xml", "sitemap_reviews_kby.xml",
        "sitemap_bestfor_ybb.xml", "sitemap_workflow_ybb.xml", "sitemap_vs_ybb.xml",
        "sitemap_seasonal_ybb.xml", "sitemap_reviews_ybb.xml",
        "sitemap_bestfor_dan.xml", "sitemap_workflow_dan.xml", "sitemap_vs_dan.xml",
        "sitemap_seasonal_dan.xml", "sitemap_reviews_dan.xml",
        "sitemap_bestfor_bsc.xml", "sitemap_workflow_bsc.xml", "sitemap_vs_bsc.xml",
        "sitemap_seasonal_bsc.xml", "sitemap_reviews_bsc.xml",
        "sitemap_bestfor_hif.xml", "sitemap_workflow_hif.xml", "sitemap_vs_hif.xml",
        "sitemap_seasonal_hif.xml", "sitemap_reviews_hif.xml",
        "sitemap_bestfor_meu.xml", "sitemap_workflow_meu.xml", "sitemap_vs_meu.xml",
        "sitemap_seasonal_meu.xml", "sitemap_reviews_meu.xml",
        "sitemap_bestfor_lkt.xml", "sitemap_workflow_lkt.xml", "sitemap_vs_lkt.xml",
        "sitemap_seasonal_lkt.xml", "sitemap_reviews_lkt.xml",
        "sitemap_bestfor_moh.xml", "sitemap_workflow_moh.xml", "sitemap_vs_moh.xml",
        "sitemap_seasonal_moh.xml", "sitemap_reviews_moh.xml",
        "sitemap_bestfor_cho.xml", "sitemap_workflow_cho.xml", "sitemap_vs_cho.xml",
        "sitemap_seasonal_cho.xml", "sitemap_reviews_cho.xml",
        "sitemap_bestfor_rop.xml", "sitemap_workflow_rop.xml", "sitemap_vs_rop.xml",
        "sitemap_seasonal_rop.xml", "sitemap_reviews_rop.xml",
        "sitemap_bestfor_ktu.xml", "sitemap_workflow_ktu.xml", "sitemap_vs_ktu.xml",
        "sitemap_seasonal_ktu.xml", "sitemap_reviews_ktu.xml",
        "sitemap_bestfor_guw.xml", "sitemap_workflow_guw.xml", "sitemap_vs_guw.xml",
        "sitemap_seasonal_guw.xml", "sitemap_reviews_guw.xml",
        "sitemap_bestfor_nde.xml", "sitemap_workflow_nde.xml", "sitemap_vs_nde.xml",
        "sitemap_seasonal_nde.xml", "sitemap_reviews_nde.xml",
        "sitemap_bestfor_bem.xml", "sitemap_workflow_bem.xml", "sitemap_vs_bem.xml",
        "sitemap_seasonal_bem.xml", "sitemap_reviews_bem.xml",
        "sitemap_bestfor_efi.xml", "sitemap_workflow_efi.xml", "sitemap_vs_efi.xml",
        "sitemap_seasonal_efi.xml", "sitemap_reviews_efi.xml",
        "sitemap_bestfor_vai.xml", "sitemap_workflow_vai.xml", "sitemap_vs_vai.xml",
        "sitemap_seasonal_vai.xml", "sitemap_reviews_vai.xml",
        "sitemap_bestfor_lun.xml", "sitemap_workflow_lun.xml", "sitemap_vs_lun.xml",
        "sitemap_seasonal_lun.xml", "sitemap_reviews_lun.xml",
        "sitemap_bestfor_kqn.xml", "sitemap_workflow_kqn.xml", "sitemap_vs_kqn.xml",
        "sitemap_seasonal_kqn.xml", "sitemap_reviews_kqn.xml",
        "sitemap_bestfor_kck.xml", "sitemap_workflow_kck.xml", "sitemap_vs_kck.xml",
        "sitemap_seasonal_kck.xml", "sitemap_reviews_kck.xml",
        "sitemap_bestfor_toi.xml", "sitemap_workflow_toi.xml", "sitemap_vs_toi.xml",
        "sitemap_seasonal_toi.xml", "sitemap_reviews_toi.xml",
        "sitemap_bestfor_lue.xml", "sitemap_workflow_lue.xml", "sitemap_vs_lue.xml",
        "sitemap_seasonal_lue.xml", "sitemap_reviews_lue.xml",
        "sitemap_bestfor_nya.xml", "sitemap_workflow_nya.xml", "sitemap_vs_nya.xml",
        "sitemap_seasonal_nya.xml", "sitemap_reviews_nya.xml",
        "sitemap_bestfor_bax.xml", "sitemap_workflow_bax.xml", "sitemap_vs_bax.xml",
        "sitemap_seasonal_bax.xml", "sitemap_reviews_bax.xml",
        "sitemap_bestfor_dyo.xml", "sitemap_workflow_dyo.xml", "sitemap_vs_dyo.xml",
        "sitemap_seasonal_dyo.xml", "sitemap_reviews_dyo.xml",
        "sitemap_bestfor_dip.xml", "sitemap_workflow_dip.xml", "sitemap_vs_dip.xml",
        "sitemap_seasonal_dip.xml", "sitemap_reviews_dip.xml",
        "sitemap_bestfor_cce.xml", "sitemap_workflow_cce.xml", "sitemap_vs_cce.xml",
        "sitemap_seasonal_cce.xml", "sitemap_reviews_cce.xml",
        "sitemap_bestfor_ndh.xml", "sitemap_workflow_ndh.xml", "sitemap_vs_ndh.xml",
        "sitemap_seasonal_ndh.xml", "sitemap_reviews_ndh.xml",
        "sitemap_bestfor_knf.xml", "sitemap_workflow_knf.xml", "sitemap_vs_knf.xml",
        "sitemap_seasonal_knf.xml", "sitemap_reviews_knf.xml",
        "sitemap_bestfor_lgg.xml", "sitemap_workflow_lgg.xml", "sitemap_vs_lgg.xml",
        "sitemap_seasonal_lgg.xml", "sitemap_reviews_lgg.xml",
        "sitemap_bestfor_alz.xml", "sitemap_workflow_alz.xml", "sitemap_vs_alz.xml",
        "sitemap_seasonal_alz.xml", "sitemap_reviews_alz.xml",
        "sitemap_bestfor_myx.xml", "sitemap_workflow_myx.xml", "sitemap_vs_myx.xml",
        "sitemap_seasonal_myx.xml", "sitemap_reviews_myx.xml",
        "sitemap_bestfor_nyo.xml", "sitemap_workflow_nyo.xml", "sitemap_vs_nyo.xml",
        "sitemap_seasonal_nyo.xml", "sitemap_reviews_nyo.xml",
        "sitemap_bestfor_bfa.xml", "sitemap_workflow_bfa.xml", "sitemap_vs_bfa.xml",
        "sitemap_seasonal_bfa.xml", "sitemap_reviews_bfa.xml",
        "sitemap_bestfor_kdj.xml", "sitemap_workflow_kdj.xml", "sitemap_vs_kdj.xml",
        "sitemap_seasonal_kdj.xml", "sitemap_reviews_kdj.xml",
        "sitemap_bestfor_lot.xml", "sitemap_workflow_lot.xml", "sitemap_vs_lot.xml",
        "sitemap_seasonal_lot.xml", "sitemap_reviews_lot.xml",
        "sitemap_bestfor_keo.xml", "sitemap_workflow_keo.xml", "sitemap_vs_keo.xml",
        "sitemap_seasonal_keo.xml", "sitemap_reviews_keo.xml",
        "sitemap_bestfor_kcg.xml", "sitemap_workflow_kcg.xml", "sitemap_vs_kcg.xml",
        "sitemap_seasonal_kcg.xml", "sitemap_reviews_kcg.xml",
        "sitemap_bestfor_avn.xml", "sitemap_workflow_avn.xml", "sitemap_vs_avn.xml",
        "sitemap_seasonal_avn.xml", "sitemap_reviews_avn.xml",
        "sitemap_bestfor_gog.xml", "sitemap_workflow_gog.xml", "sitemap_vs_gog.xml",
        "sitemap_seasonal_gog.xml", "sitemap_reviews_gog.xml",
        "sitemap_bestfor_hay.xml", "sitemap_workflow_hay.xml", "sitemap_vs_hay.xml",
        "sitemap_seasonal_hay.xml", "sitemap_reviews_hay.xml",
        "sitemap_bestfor_heh.xml", "sitemap_workflow_heh.xml", "sitemap_vs_heh.xml",
        "sitemap_seasonal_heh.xml", "sitemap_reviews_heh.xml",
        "sitemap_bestfor_rim.xml", "sitemap_workflow_rim.xml", "sitemap_vs_rim.xml",
        "sitemap_seasonal_rim.xml", "sitemap_reviews_rim.xml",
        "sitemap_bestfor_nyf.xml", "sitemap_workflow_nyf.xml", "sitemap_vs_nyf.xml",
        "sitemap_seasonal_nyf.xml", "sitemap_reviews_nyf.xml",
        "sitemap_bestfor_rag.xml", "sitemap_workflow_rag.xml", "sitemap_vs_rag.xml",
        "sitemap_seasonal_rag.xml", "sitemap_reviews_rag.xml",
        "sitemap_bestfor_thk.xml", "sitemap_workflow_thk.xml", "sitemap_vs_thk.xml",
        "sitemap_seasonal_thk.xml", "sitemap_reviews_thk.xml",
        "sitemap_bestfor_frr.xml", "sitemap_workflow_frr.xml", "sitemap_vs_frr.xml",
        "sitemap_seasonal_frr.xml", "sitemap_reviews_frr.xml",
        "sitemap_bestfor_vro.xml", "sitemap_workflow_vro.xml", "sitemap_vs_vro.xml",
        "sitemap_seasonal_vro.xml", "sitemap_reviews_vro.xml",
        "sitemap_bestfor_rmc.xml", "sitemap_workflow_rmc.xml", "sitemap_vs_rmc.xml",
        "sitemap_seasonal_rmc.xml", "sitemap_reviews_rmc.xml",
        "sitemap_bestfor_sas.xml", "sitemap_workflow_sas.xml", "sitemap_vs_sas.xml",
        "sitemap_seasonal_sas.xml", "sitemap_reviews_sas.xml",
        "sitemap_bestfor_bbc.xml", "sitemap_workflow_bbc.xml", "sitemap_vs_bbc.xml",
        "sitemap_seasonal_bbc.xml", "sitemap_reviews_bbc.xml",
        "sitemap_bestfor_nij.xml", "sitemap_workflow_nij.xml", "sitemap_vs_nij.xml",
        "sitemap_seasonal_nij.xml", "sitemap_reviews_nij.xml",
        "sitemap_bestfor_rej.xml", "sitemap_workflow_rej.xml", "sitemap_vs_rej.xml",
        "sitemap_seasonal_rej.xml", "sitemap_reviews_rej.xml",
        "sitemap_bestfor_abs.xml", "sitemap_workflow_abs.xml", "sitemap_vs_abs.xml",
        "sitemap_seasonal_abs.xml", "sitemap_reviews_abs.xml",
        "sitemap_bestfor_bbj.xml", "sitemap_workflow_bbj.xml", "sitemap_vs_bbj.xml",
        "sitemap_seasonal_bbj.xml", "sitemap_reviews_bbj.xml",
        "sitemap_bestfor_bfd.xml", "sitemap_workflow_bfd.xml", "sitemap_vs_bfd.xml",
        "sitemap_seasonal_bfd.xml", "sitemap_reviews_bfd.xml",
        "sitemap_bestfor_sef.xml", "sitemap_workflow_sef.xml", "sitemap_vs_sef.xml",
        "sitemap_seasonal_sef.xml", "sitemap_reviews_sef.xml",
        "sitemap_bestfor_gej.xml", "sitemap_workflow_gej.xml", "sitemap_vs_gej.xml",
        "sitemap_seasonal_gej.xml", "sitemap_reviews_gej.xml",
        "sitemap_bestfor_bqi.xml", "sitemap_workflow_bqi.xml", "sitemap_vs_bqi.xml",
        "sitemap_seasonal_bqi.xml", "sitemap_reviews_bqi.xml",
        "sitemap_bestfor_cjk.xml", "sitemap_workflow_cjk.xml", "sitemap_vs_cjk.xml",
        "sitemap_seasonal_cjk.xml", "sitemap_reviews_cjk.xml",
        "sitemap_bestfor_anu.xml", "sitemap_workflow_anu.xml", "sitemap_vs_anu.xml",
        "sitemap_seasonal_anu.xml", "sitemap_reviews_anu.xml",
        "sitemap_bestfor_shk.xml", "sitemap_workflow_shk.xml", "sitemap_vs_shk.xml",
        "sitemap_seasonal_shk.xml", "sitemap_reviews_shk.xml",
        "sitemap_bestfor_kdh.xml", "sitemap_workflow_kdh.xml", "sitemap_vs_kdh.xml",
        "sitemap_seasonal_kdh.xml", "sitemap_reviews_kdh.xml",
        "sitemap_bestfor_kus.xml", "sitemap_workflow_kus.xml", "sitemap_vs_kus.xml",
        "sitemap_seasonal_kus.xml", "sitemap_reviews_kus.xml",
        "sitemap_bestfor_ewo.xml", "sitemap_workflow_ewo.xml", "sitemap_vs_ewo.xml",
        "sitemap_seasonal_ewo.xml", "sitemap_reviews_ewo.xml",
        "sitemap_bestfor_rmn.xml", "sitemap_workflow_rmn.xml", "sitemap_vs_rmn.xml",
        "sitemap_seasonal_rmn.xml", "sitemap_reviews_rmn.xml",
        "sitemap_bestfor_ket.xml", "sitemap_workflow_ket.xml", "sitemap_vs_ket.xml",
        "sitemap_seasonal_ket.xml", "sitemap_reviews_ket.xml",
        "sitemap_bestfor_evn.xml", "sitemap_workflow_evn.xml", "sitemap_vs_evn.xml",
        "sitemap_seasonal_evn.xml", "sitemap_reviews_evn.xml",
        "sitemap_bestfor_niv.xml", "sitemap_workflow_niv.xml", "sitemap_vs_niv.xml",
        "sitemap_seasonal_niv.xml", "sitemap_reviews_niv.xml",
        "sitemap_bestfor_hmo.xml", "sitemap_workflow_hmo.xml", "sitemap_vs_hmo.xml",
        "sitemap_seasonal_hmo.xml", "sitemap_reviews_hmo.xml",
        "sitemap_bestfor_cnh.xml", "sitemap_workflow_cnh.xml", "sitemap_vs_cnh.xml",
        "sitemap_seasonal_cnh.xml", "sitemap_reviews_cnh.xml",
        "sitemap_bestfor_agr.xml", "sitemap_workflow_agr.xml", "sitemap_vs_agr.xml",
        "sitemap_seasonal_agr.xml", "sitemap_reviews_agr.xml",
        "sitemap_bestfor_shp.xml", "sitemap_workflow_shp.xml", "sitemap_vs_shp.xml",
        "sitemap_seasonal_shp.xml", "sitemap_reviews_shp.xml",
        "sitemap_bestfor_poh.xml", "sitemap_workflow_poh.xml", "sitemap_vs_poh.xml",
        "sitemap_seasonal_poh.xml", "sitemap_reviews_poh.xml",
        "sitemap_bestfor_kru.xml", "sitemap_workflow_kru.xml", "sitemap_vs_kru.xml",
        "sitemap_seasonal_kru.xml", "sitemap_reviews_kru.xml",
        "sitemap_bestfor_hoc.xml", "sitemap_workflow_hoc.xml", "sitemap_vs_hoc.xml",
        "sitemap_seasonal_hoc.xml", "sitemap_reviews_hoc.xml",
        "sitemap_bestfor_kfy.xml", "sitemap_workflow_kfy.xml", "sitemap_vs_kfy.xml",
        "sitemap_seasonal_kfy.xml", "sitemap_reviews_kfy.xml",
        "sitemap_bestfor_gbm.xml", "sitemap_workflow_gbm.xml", "sitemap_vs_gbm.xml",
        "sitemap_seasonal_gbm.xml", "sitemap_reviews_gbm.xml",
        "sitemap_bestfor_xnr.xml", "sitemap_workflow_xnr.xml", "sitemap_vs_xnr.xml",
        "sitemap_seasonal_xnr.xml", "sitemap_reviews_xnr.xml",
        "sitemap_bestfor_mrw.xml", "sitemap_workflow_mrw.xml", "sitemap_vs_mrw.xml",
        "sitemap_seasonal_mrw.xml", "sitemap_reviews_mrw.xml",
        "sitemap_bestfor_cbk.xml", "sitemap_workflow_cbk.xml", "sitemap_vs_cbk.xml",
        "sitemap_seasonal_cbk.xml", "sitemap_reviews_cbk.xml",
        "sitemap_bestfor_msb.xml", "sitemap_workflow_msb.xml", "sitemap_vs_msb.xml",
        "sitemap_seasonal_msb.xml", "sitemap_reviews_msb.xml",
        "sitemap_bestfor_tbw.xml", "sitemap_workflow_tbw.xml", "sitemap_vs_tbw.xml",
        "sitemap_seasonal_tbw.xml", "sitemap_reviews_tbw.xml",
        "sitemap_bestfor_hnn.xml", "sitemap_workflow_hnn.xml", "sitemap_vs_hnn.xml",
        "sitemap_seasonal_hnn.xml", "sitemap_reviews_hnn.xml",
        "sitemap_bestfor_any.xml", "sitemap_workflow_any.xml", "sitemap_vs_any.xml",
        "sitemap_seasonal_any.xml", "sitemap_reviews_any.xml",
        "sitemap_bestfor_abr.xml", "sitemap_workflow_abr.xml", "sitemap_vs_abr.xml",
        "sitemap_seasonal_abr.xml", "sitemap_reviews_abr.xml",
        "sitemap_bestfor_nzi.xml", "sitemap_workflow_nzi.xml", "sitemap_vs_nzi.xml",
        "sitemap_seasonal_nzi.xml", "sitemap_reviews_nzi.xml",
        "sitemap_bestfor_gjn.xml", "sitemap_workflow_gjn.xml", "sitemap_vs_gjn.xml",
        "sitemap_seasonal_gjn.xml", "sitemap_reviews_gjn.xml",
        "sitemap_bestfor_yom.xml", "sitemap_workflow_yom.xml", "sitemap_vs_yom.xml",
        "sitemap_seasonal_yom.xml", "sitemap_reviews_yom.xml",
        "sitemap_bestfor_mfq.xml", "sitemap_workflow_mfq.xml", "sitemap_vs_mfq.xml",
        "sitemap_seasonal_mfq.xml", "sitemap_reviews_mfq.xml",
        "sitemap_bestfor_luc.xml", "sitemap_workflow_luc.xml", "sitemap_vs_luc.xml",
        "sitemap_seasonal_luc.xml", "sitemap_reviews_luc.xml",
        "sitemap_bestfor_bud.xml", "sitemap_workflow_bud.xml", "sitemap_vs_bud.xml",
        "sitemap_seasonal_bud.xml", "sitemap_reviews_bud.xml",
        "sitemap_bestfor_yre.xml", "sitemap_workflow_yre.xml", "sitemap_vs_yre.xml",
        "sitemap_seasonal_yre.xml", "sitemap_reviews_yre.xml",
        "sitemap_bestfor_bss.xml", "sitemap_workflow_bss.xml", "sitemap_vs_bss.xml",
        "sitemap_seasonal_bss.xml", "sitemap_reviews_bss.xml",
        "sitemap_bestfor_bfo.xml", "sitemap_workflow_bfo.xml", "sitemap_vs_bfo.xml",
        "sitemap_seasonal_bfo.xml", "sitemap_reviews_bfo.xml",
        "sitemap_bestfor_dop.xml", "sitemap_workflow_dop.xml", "sitemap_vs_dop.xml",
        "sitemap_seasonal_dop.xml", "sitemap_reviews_dop.xml",
        "sitemap_bestfor_xon.xml", "sitemap_workflow_xon.xml", "sitemap_vs_xon.xml",
        "sitemap_seasonal_xon.xml", "sitemap_reviews_xon.xml",
        "sitemap_bestfor_ncu.xml", "sitemap_workflow_ncu.xml", "sitemap_vs_ncu.xml",
        "sitemap_seasonal_ncu.xml", "sitemap_reviews_ncu.xml",
        "sitemap_bestfor_gng.xml", "sitemap_workflow_gng.xml", "sitemap_vs_gng.xml",
        "sitemap_seasonal_gng.xml", "sitemap_reviews_gng.xml",
        "sitemap_bestfor_bqc.xml", "sitemap_workflow_bqc.xml", "sitemap_vs_bqc.xml",
        "sitemap_seasonal_bqc.xml", "sitemap_reviews_bqc.xml",
        "sitemap_bestfor_mcp.xml", "sitemap_workflow_mcp.xml", "sitemap_vs_mcp.xml",
        "sitemap_seasonal_mcp.xml", "sitemap_reviews_mcp.xml",
        "sitemap_bestfor_tik.xml", "sitemap_workflow_tik.xml", "sitemap_vs_tik.xml",
        "sitemap_seasonal_tik.xml", "sitemap_reviews_tik.xml",
        "sitemap_bestfor_koq.xml", "sitemap_workflow_koq.xml", "sitemap_vs_koq.xml",
        "sitemap_seasonal_koq.xml", "sitemap_reviews_koq.xml",
        "sitemap_bestfor_bex.xml", "sitemap_workflow_bex.xml", "sitemap_vs_bex.xml",
        "sitemap_seasonal_bex.xml", "sitemap_reviews_bex.xml",
        "sitemap_bestfor_avu.xml", "sitemap_workflow_avu.xml", "sitemap_vs_avu.xml",
        "sitemap_seasonal_avu.xml", "sitemap_reviews_avu.xml",
        "sitemap_bestfor_las.xml", "sitemap_workflow_las.xml", "sitemap_vs_las.xml",
        "sitemap_seasonal_las.xml", "sitemap_reviews_las.xml",
        "sitemap_bestfor_ntr.xml", "sitemap_workflow_ntr.xml", "sitemap_vs_ntr.xml",
        "sitemap_seasonal_ntr.xml", "sitemap_reviews_ntr.xml",
        "sitemap_bestfor_gud.xml", "sitemap_workflow_gud.xml", "sitemap_vs_gud.xml",
        "sitemap_seasonal_gud.xml", "sitemap_reviews_gud.xml",
        "sitemap_bestfor_bwu.xml", "sitemap_workflow_bwu.xml", "sitemap_vs_bwu.xml",
        "sitemap_seasonal_bwu.xml", "sitemap_reviews_bwu.xml",
        "sitemap_bestfor_nmz.xml", "sitemap_workflow_nmz.xml", "sitemap_vs_nmz.xml",
        "sitemap_seasonal_nmz.xml", "sitemap_reviews_nmz.xml",
        "sitemap_bestfor_dgo.xml", "sitemap_workflow_dgo.xml", "sitemap_vs_dgo.xml",
        "sitemap_seasonal_dgo.xml", "sitemap_reviews_dgo.xml",
        "sitemap_bestfor_kao.xml", "sitemap_workflow_kao.xml", "sitemap_vs_kao.xml",
        "sitemap_seasonal_kao.xml", "sitemap_reviews_kao.xml",
        "sitemap_bestfor_myk.xml", "sitemap_workflow_myk.xml", "sitemap_vs_myk.xml",
        "sitemap_seasonal_myk.xml", "sitemap_reviews_myk.xml",
        "sitemap_bestfor_bze.xml", "sitemap_workflow_bze.xml", "sitemap_vs_bze.xml",
        "sitemap_seasonal_bze.xml", "sitemap_reviews_bze.xml",
        "sitemap_bestfor_snk.xml", "sitemap_workflow_snk.xml", "sitemap_vs_snk.xml",
        "sitemap_seasonal_snk.xml", "sitemap_reviews_snk.xml",
        "sitemap_bestfor_kbn.xml", "sitemap_workflow_kbn.xml", "sitemap_vs_kbn.xml",
        "sitemap_seasonal_kbn.xml", "sitemap_reviews_kbn.xml",
        "sitemap_bestfor_sg2.xml", "sitemap_workflow_sg2.xml", "sitemap_vs_sg2.xml",
        "sitemap_seasonal_sg2.xml", "sitemap_reviews_sg2.xml",
        "sitemap_bestfor_nup.xml", "sitemap_workflow_nup.xml", "sitemap_vs_nup.xml",
        "sitemap_seasonal_nup.xml", "sitemap_reviews_nup.xml",
        "sitemap_bestfor_gbr.xml", "sitemap_workflow_gbr.xml", "sitemap_vs_gbr.xml",
        "sitemap_seasonal_gbr.xml", "sitemap_reviews_gbr.xml",
        "sitemap_bestfor_bqv.xml", "sitemap_workflow_bqv.xml", "sitemap_vs_bqv.xml",
        "sitemap_seasonal_bqv.xml", "sitemap_reviews_bqv.xml",
        "sitemap_bestfor_etu.xml", "sitemap_workflow_etu.xml", "sitemap_vs_etu.xml",
        "sitemap_seasonal_etu.xml", "sitemap_reviews_etu.xml",
        "sitemap_bestfor_mfi.xml", "sitemap_workflow_mfi.xml", "sitemap_vs_mfi.xml",
        "sitemap_seasonal_mfi.xml", "sitemap_reviews_mfi.xml",
        "sitemap_bestfor_mcn.xml", "sitemap_workflow_mcn.xml", "sitemap_vs_mcn.xml",
        "sitemap_seasonal_mcn.xml", "sitemap_reviews_mcn.xml",
        "sitemap_bestfor_gid.xml", "sitemap_workflow_gid.xml", "sitemap_vs_gid.xml",
        "sitemap_seasonal_gid.xml", "sitemap_reviews_gid.xml",
        "sitemap_bestfor_kbp2.xml", "sitemap_workflow_kbp2.xml", "sitemap_vs_kbp2.xml",
        "sitemap_seasonal_kbp2.xml", "sitemap_reviews_kbp2.xml",
        "sitemap_bestfor_bwq.xml", "sitemap_workflow_bwq.xml", "sitemap_vs_bwq.xml",
        "sitemap_seasonal_bwq.xml", "sitemap_reviews_bwq.xml",
        "sitemap_bestfor_dga2.xml", "sitemap_workflow_dga2.xml", "sitemap_vs_dga2.xml",
        "sitemap_seasonal_dga2.xml", "sitemap_reviews_dga2.xml",
        "sitemap_bestfor_mfz.xml", "sitemap_workflow_mfz.xml", "sitemap_vs_mfz.xml",
        "sitemap_seasonal_mfz.xml", "sitemap_reviews_mfz.xml",
        "sitemap_bestfor_bfa2.xml", "sitemap_workflow_bfa2.xml", "sitemap_vs_bfa2.xml",
        "sitemap_seasonal_bfa2.xml", "sitemap_reviews_bfa2.xml",
        "sitemap_bestfor_bjt.xml", "sitemap_workflow_bjt.xml", "sitemap_vs_bjt.xml",
        "sitemap_seasonal_bjt.xml", "sitemap_reviews_bjt.xml",
        "sitemap_bestfor_bsc2.xml", "sitemap_workflow_bsc2.xml", "sitemap_vs_bsc2.xml",
        "sitemap_seasonal_bsc2.xml", "sitemap_reviews_bsc2.xml",
        "sitemap_bestfor_csk.xml", "sitemap_workflow_csk.xml", "sitemap_vs_csk.xml",
        "sitemap_seasonal_csk.xml", "sitemap_reviews_csk.xml",
        "sitemap_bestfor_kdc2.xml", "sitemap_workflow_kdc2.xml", "sitemap_vs_kdc2.xml",
        "sitemap_seasonal_kdc2.xml", "sitemap_reviews_kdc2.xml",
        "sitemap_bestfor_vid.xml", "sitemap_workflow_vid.xml", "sitemap_vs_vid.xml",
        "sitemap_seasonal_vid.xml", "sitemap_reviews_vid.xml",
        "sitemap_bestfor_zga.xml", "sitemap_workflow_zga.xml", "sitemap_vs_zga.xml",
        "sitemap_seasonal_zga.xml", "sitemap_reviews_zga.xml",
        "sitemap_bestfor_nim.xml", "sitemap_workflow_nim.xml", "sitemap_vs_nim.xml",
        "sitemap_seasonal_nim.xml", "sitemap_reviews_nim.xml",
        "sitemap_bestfor_rag2.xml", "sitemap_workflow_rag2.xml", "sitemap_vs_rag2.xml",
        "sitemap_seasonal_rag2.xml", "sitemap_reviews_rag2.xml",
        "sitemap_bestfor_sba.xml", "sitemap_workflow_sba.xml", "sitemap_vs_sba.xml",
        "sitemap_seasonal_sba.xml", "sitemap_reviews_sba.xml",
        "sitemap_bestfor_tui.xml", "sitemap_workflow_tui.xml", "sitemap_vs_tui.xml",
        "sitemap_seasonal_tui.xml", "sitemap_reviews_tui.xml",
        "sitemap_bestfor_daa.xml", "sitemap_workflow_daa.xml", "sitemap_vs_daa.xml",
        "sitemap_seasonal_daa.xml", "sitemap_reviews_daa.xml",
        "sitemap_bestfor_ngb.xml", "sitemap_workflow_ngb.xml", "sitemap_vs_ngb.xml",
        "sitemap_seasonal_ngb.xml", "sitemap_reviews_ngb.xml",
        "sitemap_bestfor_ttj.xml", "sitemap_workflow_ttj.xml", "sitemap_vs_ttj.xml",
        "sitemap_seasonal_ttj.xml", "sitemap_reviews_ttj.xml",
        "sitemap_bestfor_gwr.xml", "sitemap_workflow_gwr.xml", "sitemap_vs_gwr.xml",
        "sitemap_seasonal_gwr.xml", "sitemap_reviews_gwr.xml",
        "sitemap_bestfor_pko.xml", "sitemap_workflow_pko.xml", "sitemap_vs_pko.xml",
        "sitemap_seasonal_pko.xml", "sitemap_reviews_pko.xml",
        "sitemap_bestfor_saf.xml", "sitemap_workflow_saf.xml", "sitemap_vs_saf.xml",
        "sitemap_seasonal_saf.xml", "sitemap_reviews_saf.xml",
        "sitemap_bestfor_mzw.xml", "sitemap_workflow_mzw.xml", "sitemap_vs_mzw.xml",
        "sitemap_seasonal_mzw.xml", "sitemap_reviews_mzw.xml",
        "sitemap_bestfor_hag.xml", "sitemap_workflow_hag.xml", "sitemap_vs_hag.xml",
        "sitemap_seasonal_hag.xml", "sitemap_reviews_hag.xml",
        "sitemap_bestfor_fuf.xml", "sitemap_workflow_fuf.xml", "sitemap_vs_fuf.xml",
        "sitemap_seasonal_fuf.xml", "sitemap_reviews_fuf.xml",
        "sitemap_bestfor_xpe.xml", "sitemap_workflow_xpe.xml", "sitemap_vs_xpe.xml",
        "sitemap_seasonal_xpe.xml", "sitemap_reviews_xpe.xml",
        "sitemap_bestfor_gkp.xml", "sitemap_workflow_gkp.xml", "sitemap_vs_gkp.xml",
        "sitemap_seasonal_gkp.xml", "sitemap_reviews_gkp.xml",
        "sitemap_bestfor_kqs.xml", "sitemap_workflow_kqs.xml", "sitemap_vs_kqs.xml",
        "sitemap_seasonal_kqs.xml", "sitemap_reviews_kqs.xml",
        "sitemap_bestfor_bza.xml", "sitemap_workflow_bza.xml", "sitemap_vs_bza.xml",
        "sitemap_seasonal_bza.xml", "sitemap_reviews_bza.xml",
        "sitemap_bestfor_snf.xml", "sitemap_workflow_snf.xml", "sitemap_vs_snf.xml",
        "sitemap_seasonal_snf.xml", "sitemap_reviews_snf.xml",
        "sitemap_bestfor_mcu.xml", "sitemap_workflow_mcu.xml", "sitemap_vs_mcu.xml",
        "sitemap_seasonal_mcu.xml", "sitemap_reviews_mcu.xml",
        "sitemap_bestfor_nnq.xml", "sitemap_workflow_nnq.xml", "sitemap_vs_nnq.xml",
        "sitemap_seasonal_nnq.xml", "sitemap_reviews_nnq.xml",
        "sitemap_bestfor_tnr.xml", "sitemap_workflow_tnr.xml", "sitemap_vs_tnr.xml",
        "sitemap_seasonal_tnr.xml", "sitemap_reviews_tnr.xml",
        "sitemap_bestfor_mfk.xml", "sitemap_workflow_mfk.xml", "sitemap_vs_mfk.xml",
        "sitemap_seasonal_mfk.xml", "sitemap_reviews_mfk.xml",
        "sitemap_bestfor_knc.xml", "sitemap_workflow_knc.xml", "sitemap_vs_knc.xml",
        "sitemap_seasonal_knc.xml", "sitemap_reviews_knc.xml",
        "sitemap_bestfor_dnj.xml", "sitemap_workflow_dnj.xml", "sitemap_vs_dnj.xml",
        "sitemap_seasonal_dnj.xml", "sitemap_reviews_dnj.xml",
        "sitemap_bestfor_lom.xml", "sitemap_workflow_lom.xml", "sitemap_vs_lom.xml",
        "sitemap_seasonal_lom.xml", "sitemap_reviews_lom.xml",
        "sitemap_bestfor_gbo.xml", "sitemap_workflow_gbo.xml", "sitemap_vs_gbo.xml",
        "sitemap_seasonal_gbo.xml", "sitemap_reviews_gbo.xml",
        "sitemap_bestfor_grj.xml", "sitemap_workflow_grj.xml", "sitemap_vs_grj.xml",
        "sitemap_seasonal_grj.xml", "sitemap_reviews_grj.xml",
        "sitemap_bestfor_dee.xml", "sitemap_workflow_dee.xml", "sitemap_vs_dee.xml",
        "sitemap_seasonal_dee.xml", "sitemap_reviews_dee.xml",
        "sitemap_bestfor_wob.xml", "sitemap_workflow_wob.xml", "sitemap_vs_wob.xml",
        "sitemap_seasonal_wob.xml", "sitemap_reviews_wob.xml",
        "sitemap_bestfor_bmq.xml", "sitemap_workflow_bmq.xml", "sitemap_vs_bmq.xml",
        "sitemap_seasonal_bmq.xml", "sitemap_reviews_bmq.xml",
        "sitemap_bestfor_box.xml", "sitemap_workflow_box.xml", "sitemap_vs_box.xml",
        "sitemap_seasonal_box.xml", "sitemap_reviews_box.xml",
        "sitemap_bestfor_kel.xml", "sitemap_workflow_kel.xml", "sitemap_vs_kel.xml",
        "sitemap_seasonal_kel.xml", "sitemap_reviews_kel.xml",
        "sitemap_bestfor_grt.xml", "sitemap_workflow_grt.xml", "sitemap_vs_grt.xml",
        "sitemap_seasonal_grt.xml", "sitemap_reviews_grt.xml",
        "sitemap_bestfor_nag.xml", "sitemap_workflow_nag.xml", "sitemap_vs_nag.xml",
        "sitemap_seasonal_nag.xml", "sitemap_reviews_nag.xml",
        "sitemap_bestfor_njo.xml", "sitemap_workflow_njo.xml", "sitemap_vs_njo.xml",
        "sitemap_seasonal_njo.xml", "sitemap_reviews_njo.xml",
        "sitemap_bestfor_wbm.xml", "sitemap_workflow_wbm.xml", "sitemap_vs_wbm.xml",
        "sitemap_seasonal_wbm.xml", "sitemap_reviews_wbm.xml",
        "sitemap_bestfor_tdg.xml", "sitemap_workflow_tdg.xml", "sitemap_vs_tdg.xml",
        "sitemap_seasonal_tdg.xml", "sitemap_reviews_tdg.xml",
        "sitemap_bestfor_tsj.xml", "sitemap_workflow_tsj.xml", "sitemap_vs_tsj.xml",
        "sitemap_seasonal_tsj.xml", "sitemap_reviews_tsj.xml",
        "sitemap_bestfor_lep.xml", "sitemap_workflow_lep.xml", "sitemap_vs_lep.xml",
        "sitemap_seasonal_lep.xml", "sitemap_reviews_lep.xml",
        "sitemap_bestfor_sip.xml", "sitemap_workflow_sip.xml", "sitemap_vs_sip.xml",
        "sitemap_seasonal_sip.xml", "sitemap_reviews_sip.xml",
        "sitemap_bestfor_jya.xml", "sitemap_workflow_jya.xml", "sitemap_vs_jya.xml",
        "sitemap_seasonal_jya.xml", "sitemap_reviews_jya.xml",
        "sitemap_bestfor_mtr.xml", "sitemap_workflow_mtr.xml", "sitemap_vs_mtr.xml",
        "sitemap_seasonal_mtr.xml", "sitemap_reviews_mtr.xml",
        "sitemap_bestfor_wbr.xml", "sitemap_workflow_wbr.xml", "sitemap_vs_wbr.xml",
        "sitemap_seasonal_wbr.xml", "sitemap_reviews_wbr.xml",
        "sitemap_bestfor_hoj.xml", "sitemap_workflow_hoj.xml", "sitemap_vs_hoj.xml",
        "sitemap_seasonal_hoj.xml", "sitemap_reviews_hoj.xml",
        "sitemap_bestfor_noe.xml", "sitemap_workflow_noe.xml", "sitemap_vs_noe.xml",
        "sitemap_seasonal_noe.xml", "sitemap_reviews_noe.xml",
        "sitemap_bestfor_dhd.xml", "sitemap_workflow_dhd.xml", "sitemap_vs_dhd.xml",
        "sitemap_seasonal_dhd.xml", "sitemap_reviews_dhd.xml",
        "sitemap_bestfor_bra.xml", "sitemap_workflow_bra.xml", "sitemap_vs_bra.xml",
        "sitemap_seasonal_bra.xml", "sitemap_reviews_bra.xml",
        "sitemap_bestfor_gju.xml", "sitemap_workflow_gju.xml", "sitemap_vs_gju.xml",
        "sitemap_seasonal_gju.xml", "sitemap_reviews_gju.xml",
        "sitemap_bestfor_anp.xml", "sitemap_workflow_anp.xml", "sitemap_vs_anp.xml",
        "sitemap_seasonal_anp.xml", "sitemap_reviews_anp.xml",
        "sitemap_bestfor_kjo.xml", "sitemap_workflow_kjo.xml", "sitemap_vs_kjo.xml",
        "sitemap_seasonal_kjo.xml", "sitemap_reviews_kjo.xml",
        "sitemap_bestfor_gdx.xml", "sitemap_workflow_gdx.xml", "sitemap_vs_gdx.xml",
        "sitemap_seasonal_gdx.xml", "sitemap_reviews_gdx.xml",
        "sitemap_bestfor_kvx.xml", "sitemap_workflow_kvx.xml", "sitemap_vs_kvx.xml",
        "sitemap_seasonal_kvx.xml", "sitemap_reviews_kvx.xml",
        "sitemap_bestfor_vah.xml", "sitemap_workflow_vah.xml", "sitemap_vs_vah.xml",
        "sitemap_seasonal_vah.xml", "sitemap_reviews_vah.xml",
        "sitemap_bestfor_bfy.xml", "sitemap_workflow_bfy.xml", "sitemap_vs_bfy.xml",
        "sitemap_seasonal_bfy.xml", "sitemap_reviews_bfy.xml",
        "sitemap_bestfor_unr.xml", "sitemap_workflow_unr.xml", "sitemap_vs_unr.xml",
        "sitemap_seasonal_unr.xml", "sitemap_reviews_unr.xml",
        "sitemap_bestfor_sgj.xml", "sitemap_workflow_sgj.xml", "sitemap_vs_sgj.xml",
        "sitemap_seasonal_sgj.xml", "sitemap_reviews_sgj.xml",
        "sitemap_bestfor_dhn.xml", "sitemap_workflow_dhn.xml", "sitemap_vs_dhn.xml",
        "sitemap_seasonal_dhn.xml", "sitemap_reviews_dhn.xml",
        "sitemap_bestfor_kfx.xml", "sitemap_workflow_kfx.xml", "sitemap_vs_kfx.xml",
        "sitemap_seasonal_kfx.xml", "sitemap_reviews_kfx.xml",
        "sitemap_bestfor_gwc.xml", "sitemap_workflow_gwc.xml", "sitemap_vs_gwc.xml",
        "sitemap_seasonal_gwc.xml", "sitemap_reviews_gwc.xml",
        "sitemap_bestfor_bsh.xml", "sitemap_workflow_bsh.xml", "sitemap_vs_bsh.xml",
        "sitemap_seasonal_bsh.xml", "sitemap_reviews_bsh.xml",
        "sitemap_bestfor_kfe.xml", "sitemap_workflow_kfe.xml", "sitemap_vs_kfe.xml",
        "sitemap_seasonal_kfe.xml", "sitemap_reviews_kfe.xml",
        "sitemap_bestfor_emx.xml", "sitemap_workflow_emx.xml", "sitemap_vs_emx.xml",
        "sitemap_seasonal_emx.xml", "sitemap_reviews_emx.xml",
        "sitemap_bestfor_aec.xml", "sitemap_workflow_aec.xml", "sitemap_vs_aec.xml",
        "sitemap_seasonal_aec.xml", "sitemap_reviews_aec.xml",
        "sitemap_bestfor_acm.xml", "sitemap_workflow_acm.xml", "sitemap_vs_acm.xml",
        "sitemap_seasonal_acm.xml", "sitemap_reviews_acm.xml",
        "sitemap_bestfor_afb.xml", "sitemap_workflow_afb.xml", "sitemap_vs_afb.xml",
        "sitemap_seasonal_afb.xml", "sitemap_reviews_afb.xml",
        "sitemap_bestfor_acw.xml", "sitemap_workflow_acw.xml", "sitemap_vs_acw.xml",
        "sitemap_seasonal_acw.xml", "sitemap_reviews_acw.xml",
        "sitemap_bestfor_acq.xml", "sitemap_workflow_acq.xml", "sitemap_vs_acq.xml",
        "sitemap_seasonal_acq.xml", "sitemap_reviews_acq.xml",
        "sitemap_bestfor_arz.xml", "sitemap_workflow_arz.xml", "sitemap_vs_arz.xml",
        "sitemap_seasonal_arz.xml", "sitemap_reviews_arz.xml",
        "sitemap_bestfor_ary.xml", "sitemap_workflow_ary.xml", "sitemap_vs_ary.xml",
        "sitemap_seasonal_ary.xml", "sitemap_reviews_ary.xml",
        "sitemap_bestfor_apd.xml", "sitemap_workflow_apd.xml", "sitemap_vs_apd.xml",
        "sitemap_seasonal_apd.xml", "sitemap_reviews_apd.xml",
        "sitemap_bestfor_apc.xml", "sitemap_workflow_apc.xml", "sitemap_vs_apc.xml",
        "sitemap_seasonal_apc.xml", "sitemap_reviews_apc.xml",
        "sitemap_bestfor_hno.xml", "sitemap_workflow_hno.xml", "sitemap_vs_hno.xml",
        "sitemap_seasonal_hno.xml", "sitemap_reviews_hno.xml",
        "sitemap_bestfor_hnd.xml", "sitemap_workflow_hnd.xml", "sitemap_vs_hnd.xml",
        "sitemap_seasonal_hnd.xml", "sitemap_reviews_hnd.xml",
        "sitemap_bestfor_pmu.xml", "sitemap_workflow_pmu.xml", "sitemap_vs_pmu.xml",
        "sitemap_seasonal_pmu.xml", "sitemap_reviews_pmu.xml",
        "sitemap_bestfor_bgq.xml", "sitemap_workflow_bgq.xml", "sitemap_vs_bgq.xml",
        "sitemap_seasonal_bgq.xml", "sitemap_reviews_bgq.xml",
        "sitemap_bestfor_ymm.xml", "sitemap_workflow_ymm.xml", "sitemap_vs_ymm.xml",
        "sitemap_seasonal_ymm.xml", "sitemap_reviews_ymm.xml",
        "sitemap_bestfor_gbk.xml", "sitemap_workflow_gbk.xml", "sitemap_vs_gbk.xml",
        "sitemap_seasonal_gbk.xml", "sitemap_reviews_gbk.xml",
        "sitemap_bestfor_xnj.xml", "sitemap_workflow_xnj.xml", "sitemap_vs_xnj.xml",
        "sitemap_seasonal_xnj.xml", "sitemap_reviews_xnj.xml",
        "sitemap_bestfor_odk.xml", "sitemap_workflow_odk.xml", "sitemap_vs_odk.xml",
        "sitemap_seasonal_odk.xml", "sitemap_reviews_odk.xml",
        "sitemap_bestfor_kxp.xml", "sitemap_workflow_kxp.xml", "sitemap_vs_kxp.xml",
        "sitemap_seasonal_kxp.xml", "sitemap_reviews_kxp.xml",
        "sitemap_bestfor_pce.xml", "sitemap_workflow_pce.xml", "sitemap_vs_pce.xml",
        "sitemap_seasonal_pce.xml", "sitemap_reviews_pce.xml",
        "sitemap_bestfor_rkt.xml", "sitemap_workflow_rkt.xml", "sitemap_vs_rkt.xml",
        "sitemap_seasonal_rkt.xml", "sitemap_reviews_rkt.xml",
        "sitemap_bestfor_ctg.xml", "sitemap_workflow_ctg.xml", "sitemap_vs_ctg.xml",
        "sitemap_seasonal_ctg.xml", "sitemap_reviews_ctg.xml",
        "sitemap_bestfor_syl.xml", "sitemap_workflow_syl.xml", "sitemap_vs_syl.xml",
        "sitemap_seasonal_syl.xml", "sitemap_reviews_syl.xml",
        "sitemap_bestfor_swv.xml", "sitemap_workflow_swv.xml", "sitemap_vs_swv.xml",
        "sitemap_seasonal_swv.xml", "sitemap_reviews_swv.xml",
        "sitemap_bestfor_kfq.xml", "sitemap_workflow_kfq.xml", "sitemap_vs_kfq.xml",
        "sitemap_seasonal_kfq.xml", "sitemap_reviews_kfq.xml",
        "sitemap_bestfor_bpy.xml", "sitemap_workflow_bpy.xml", "sitemap_vs_bpy.xml",
        "sitemap_seasonal_bpy.xml", "sitemap_reviews_bpy.xml",
        "sitemap_bestfor_tdb.xml", "sitemap_workflow_tdb.xml", "sitemap_vs_tdb.xml",
        "sitemap_seasonal_tdb.xml", "sitemap_reviews_tdb.xml",
        "sitemap_bestfor_xsr.xml", "sitemap_workflow_xsr.xml", "sitemap_vs_xsr.xml",
        "sitemap_seasonal_xsr.xml", "sitemap_reviews_xsr.xml",
        "sitemap_bestfor_kxv.xml", "sitemap_workflow_kxv.xml", "sitemap_vs_kxv.xml",
        "sitemap_seasonal_kxv.xml", "sitemap_reviews_kxv.xml",
        "sitemap_bestfor_gbj.xml", "sitemap_workflow_gbj.xml", "sitemap_vs_gbj.xml",
        "sitemap_seasonal_gbj.xml", "sitemap_reviews_gbj.xml",
        "sitemap_bestfor_sdr.xml", "sitemap_workflow_sdr.xml", "sitemap_vs_sdr.xml",
        "sitemap_seasonal_sdr.xml", "sitemap_reviews_sdr.xml",
        "sitemap_bestfor_mjl.xml", "sitemap_workflow_mjl.xml", "sitemap_vs_mjl.xml",
        "sitemap_seasonal_mjl.xml", "sitemap_reviews_mjl.xml",
        "sitemap_bestfor_kex.xml", "sitemap_workflow_kex.xml", "sitemap_vs_kex.xml",
        "sitemap_seasonal_kex.xml", "sitemap_reviews_kex.xml",
        "sitemap_bestfor_mjz.xml", "sitemap_workflow_mjz.xml", "sitemap_vs_mjz.xml",
        "sitemap_seasonal_mjz.xml", "sitemap_reviews_mjz.xml",
        "sitemap_bestfor_srx.xml", "sitemap_workflow_srx.xml", "sitemap_vs_srx.xml",
        "sitemap_seasonal_srx.xml", "sitemap_reviews_srx.xml",
        "sitemap_bestfor_mjt.xml", "sitemap_workflow_mjt.xml", "sitemap_vs_mjt.xml",
        "sitemap_seasonal_mjt.xml", "sitemap_reviews_mjt.xml",
        "sitemap_bestfor_xka.xml", "sitemap_workflow_xka.xml", "sitemap_vs_xka.xml",
        "sitemap_seasonal_xka.xml", "sitemap_reviews_xka.xml",
        "sitemap_bestfor_agi.xml", "sitemap_workflow_agi.xml", "sitemap_vs_agi.xml",
        "sitemap_seasonal_agi.xml", "sitemap_reviews_agi.xml",
        "sitemap_bestfor_cps.xml", "sitemap_workflow_cps.xml", "sitemap_vs_cps.xml",
        "sitemap_seasonal_cps.xml", "sitemap_reviews_cps.xml",
        "sitemap_bestfor_tbl.xml", "sitemap_workflow_tbl.xml", "sitemap_vs_tbl.xml",
        "sitemap_seasonal_tbl.xml", "sitemap_reviews_tbl.xml",
        "sitemap_bestfor_agn.xml", "sitemap_workflow_agn.xml", "sitemap_vs_agn.xml",
        "sitemap_seasonal_agn.xml", "sitemap_reviews_agn.xml",
        "sitemap_bestfor_mta.xml", "sitemap_workflow_mta.xml", "sitemap_vs_mta.xml",
        "sitemap_seasonal_mta.xml", "sitemap_reviews_mta.xml",
        "sitemap_bestfor_obo.xml", "sitemap_workflow_obo.xml", "sitemap_vs_obo.xml",
        "sitemap_seasonal_obo.xml", "sitemap_reviews_obo.xml",
        "sitemap_bestfor_msm.xml", "sitemap_workflow_msm.xml", "sitemap_vs_msm.xml",
        "sitemap_seasonal_msm.xml", "sitemap_reviews_msm.xml",
        "sitemap_bestfor_bnj.xml", "sitemap_workflow_bnj.xml", "sitemap_vs_bnj.xml",
        "sitemap_seasonal_bnj.xml", "sitemap_reviews_bnj.xml",
        "sitemap_bestfor_bkn.xml", "sitemap_workflow_bkn.xml", "sitemap_vs_bkn.xml",
        "sitemap_seasonal_bkn.xml", "sitemap_reviews_bkn.xml",
        "sitemap_bestfor_bar.xml", "sitemap_workflow_bar.xml", "sitemap_vs_bar.xml",
        "sitemap_seasonal_bar.xml", "sitemap_reviews_bar.xml",
        "sitemap_bestfor_vmf.xml", "sitemap_workflow_vmf.xml", "sitemap_vs_vmf.xml",
        "sitemap_seasonal_vmf.xml", "sitemap_reviews_vmf.xml",
        "sitemap_bestfor_swg.xml", "sitemap_workflow_swg.xml", "sitemap_vs_swg.xml",
        "sitemap_seasonal_swg.xml", "sitemap_reviews_swg.xml",
        "sitemap_bestfor_ksh.xml", "sitemap_workflow_ksh.xml", "sitemap_vs_ksh.xml",
        "sitemap_seasonal_ksh.xml", "sitemap_reviews_ksh.xml",
        "sitemap_bestfor_pfl.xml", "sitemap_workflow_pfl.xml", "sitemap_vs_pfl.xml",
        "sitemap_seasonal_pfl.xml", "sitemap_reviews_pfl.xml",
        "sitemap_bestfor_rgn.xml", "sitemap_workflow_rgn.xml", "sitemap_vs_rgn.xml",
        "sitemap_seasonal_rgn.xml", "sitemap_reviews_rgn.xml",
        "sitemap_bestfor_egl.xml", "sitemap_workflow_egl.xml", "sitemap_vs_egl.xml",
        "sitemap_seasonal_egl.xml", "sitemap_reviews_egl.xml",
        "sitemap_bestfor_nrf.xml", "sitemap_workflow_nrf.xml", "sitemap_vs_nrf.xml",
        "sitemap_seasonal_nrf.xml", "sitemap_reviews_nrf.xml",
        "sitemap_bestfor_sxu.xml", "sitemap_workflow_sxu.xml", "sitemap_vs_sxu.xml",
        "sitemap_seasonal_sxu.xml", "sitemap_reviews_sxu.xml",
        "sitemap_bestfor_vls.xml", "sitemap_workflow_vls.xml", "sitemap_vs_vls.xml",
        "sitemap_seasonal_vls.xml", "sitemap_reviews_vls.xml",
        "sitemap_bestfor_wae.xml", "sitemap_workflow_wae.xml", "sitemap_vs_wae.xml",
        "sitemap_seasonal_wae.xml", "sitemap_reviews_wae.xml",
        "sitemap_bestfor_zea.xml", "sitemap_workflow_zea.xml", "sitemap_vs_zea.xml",
        "sitemap_seasonal_zea.xml", "sitemap_reviews_zea.xml",
        "sitemap_bestfor_wep.xml", "sitemap_workflow_wep.xml", "sitemap_vs_wep.xml",
        "sitemap_seasonal_wep.xml", "sitemap_reviews_wep.xml",
        "sitemap_bestfor_prv.xml", "sitemap_workflow_prv.xml", "sitemap_vs_prv.xml",
        "sitemap_seasonal_prv.xml", "sitemap_reviews_prv.xml",
        "sitemap_bestfor_oci.xml", "sitemap_workflow_oci.xml", "sitemap_vs_oci.xml",
        "sitemap_seasonal_oci.xml", "sitemap_reviews_oci.xml",
        "sitemap_bestfor_srd.xml", "sitemap_workflow_srd.xml", "sitemap_vs_srd.xml",
        "sitemap_seasonal_srd.xml", "sitemap_reviews_srd.xml",
        "sitemap_bestfor_fit.xml", "sitemap_workflow_fit.xml", "sitemap_vs_fit.xml",
        "sitemap_seasonal_fit.xml", "sitemap_reviews_fit.xml",
        "sitemap_bestfor_fkv.xml", "sitemap_workflow_fkv.xml", "sitemap_vs_fkv.xml",
        "sitemap_seasonal_fkv.xml", "sitemap_reviews_fkv.xml",
        "sitemap_bestfor_twd.xml", "sitemap_workflow_twd.xml", "sitemap_vs_twd.xml",
        "sitemap_seasonal_twd.xml", "sitemap_reviews_twd.xml",
        "sitemap_bestfor_jut.xml", "sitemap_workflow_jut.xml", "sitemap_vs_jut.xml",
        "sitemap_seasonal_jut.xml", "sitemap_reviews_jut.xml",
        "sitemap_bestfor_ovd.xml", "sitemap_workflow_ovd.xml", "sitemap_vs_ovd.xml",
        "sitemap_seasonal_ovd.xml", "sitemap_reviews_ovd.xml",
        "sitemap_bestfor_sju.xml", "sitemap_workflow_sju.xml", "sitemap_vs_sju.xml",
        "sitemap_seasonal_sju.xml", "sitemap_reviews_sju.xml",
        "sitemap_bestfor_sje.xml", "sitemap_workflow_sje.xml", "sitemap_vs_sje.xml",
        "sitemap_seasonal_sje.xml", "sitemap_reviews_sje.xml",
        "sitemap_bestfor_gutn.xml", "sitemap_workflow_gutn.xml", "sitemap_vs_gutn.xml",
        "sitemap_seasonal_gutn.xml", "sitemap_reviews_gutn.xml",
        "sitemap_bestfor_kjh.xml", "sitemap_workflow_kjh.xml", "sitemap_vs_kjh.xml",
        "sitemap_seasonal_kjh.xml", "sitemap_reviews_kjh.xml",
        "sitemap_bestfor_alt.xml", "sitemap_workflow_alt.xml", "sitemap_vs_alt.xml",
        "sitemap_seasonal_alt.xml", "sitemap_reviews_alt.xml",
        "sitemap_bestfor_cjs.xml", "sitemap_workflow_cjs.xml", "sitemap_vs_cjs.xml",
        "sitemap_seasonal_cjs.xml", "sitemap_reviews_cjs.xml",
        "sitemap_bestfor_dlg.xml", "sitemap_workflow_dlg.xml", "sitemap_vs_dlg.xml",
        "sitemap_seasonal_dlg.xml", "sitemap_reviews_dlg.xml",
        "sitemap_bestfor_kim.xml", "sitemap_workflow_kim.xml", "sitemap_vs_kim.xml",
        "sitemap_seasonal_kim.xml", "sitemap_reviews_kim.xml",
        "sitemap_bestfor_kdr.xml", "sitemap_workflow_kdr.xml", "sitemap_vs_kdr.xml",
        "sitemap_seasonal_kdr.xml", "sitemap_reviews_kdr.xml",
        "sitemap_bestfor_mrj.xml", "sitemap_workflow_mrj.xml", "sitemap_vs_mrj.xml",
        "sitemap_seasonal_mrj.xml", "sitemap_reviews_mrj.xml",
        "sitemap_bestfor_gas.xml", "sitemap_workflow_gas.xml", "sitemap_vs_gas.xml",
        "sitemap_seasonal_gas.xml", "sitemap_reviews_gas.xml",
        "sitemap_bestfor_kdq.xml", "sitemap_workflow_kdq.xml", "sitemap_vs_kdq.xml",
        "sitemap_seasonal_kdq.xml", "sitemap_reviews_kdq.xml",
        "sitemap_bestfor_anr.xml", "sitemap_workflow_anr.xml", "sitemap_vs_anr.xml",
        "sitemap_seasonal_anr.xml", "sitemap_reviews_anr.xml",
        "sitemap_bestfor_dry.xml", "sitemap_workflow_dry.xml", "sitemap_vs_dry.xml",
        "sitemap_seasonal_dry.xml", "sitemap_reviews_dry.xml",
        "sitemap_bestfor_unx.xml", "sitemap_workflow_unx.xml", "sitemap_vs_unx.xml",
        "sitemap_seasonal_unx.xml", "sitemap_reviews_unx.xml",
        "sitemap_bestfor_bfw.xml", "sitemap_workflow_bfw.xml", "sitemap_vs_bfw.xml",
        "sitemap_seasonal_bfw.xml", "sitemap_reviews_bfw.xml",
        "sitemap_bestfor_bjj.xml", "sitemap_workflow_bjj.xml", "sitemap_vs_bjj.xml",
        "sitemap_seasonal_bjj.xml", "sitemap_reviews_bjj.xml",
        "sitemap_bestfor_bns.xml", "sitemap_workflow_bns.xml", "sitemap_vs_bns.xml",
        "sitemap_seasonal_bns.xml", "sitemap_reviews_bns.xml",
        "sitemap_bestfor_mup.xml", "sitemap_workflow_mup.xml", "sitemap_vs_mup.xml",
        "sitemap_seasonal_mup.xml", "sitemap_reviews_mup.xml",
        "sitemap_bestfor_bhb.xml", "sitemap_workflow_bhb.xml", "sitemap_vs_bhb.xml",
        "sitemap_seasonal_bhb.xml", "sitemap_reviews_bhb.xml",
        "sitemap_bestfor_gom.xml", "sitemap_workflow_gom.xml", "sitemap_vs_gom.xml",
        "sitemap_seasonal_gom.xml", "sitemap_reviews_gom.xml",
        "sitemap_bestfor_ahr.xml", "sitemap_workflow_ahr.xml", "sitemap_vs_ahr.xml",
        "sitemap_seasonal_ahr.xml", "sitemap_reviews_ahr.xml",
        "sitemap_bestfor_dty.xml", "sitemap_workflow_dty.xml", "sitemap_vs_dty.xml",
        "sitemap_seasonal_dty.xml", "sitemap_reviews_dty.xml",
        "sitemap_bestfor_thl.xml", "sitemap_workflow_thl.xml", "sitemap_vs_thl.xml",
        "sitemap_seasonal_thl.xml", "sitemap_reviews_thl.xml",
        "sitemap_bestfor_pnb.xml", "sitemap_workflow_pnb.xml", "sitemap_vs_pnb.xml",
        "sitemap_seasonal_pnb.xml", "sitemap_reviews_pnb.xml",
        "sitemap_bestfor_prs.xml", "sitemap_workflow_prs.xml", "sitemap_vs_prs.xml",
        "sitemap_seasonal_prs.xml", "sitemap_reviews_prs.xml",
        "sitemap_bestfor_bal.xml", "sitemap_workflow_bal.xml", "sitemap_vs_bal.xml",
        "sitemap_seasonal_bal.xml", "sitemap_reviews_bal.xml",
        "sitemap_bestfor_kas.xml", "sitemap_workflow_kas.xml", "sitemap_vs_kas.xml",
        "sitemap_seasonal_kas.xml", "sitemap_reviews_kas.xml",
        "sitemap_bestfor_sdh.xml", "sitemap_workflow_sdh.xml", "sitemap_vs_sdh.xml",
        "sitemap_seasonal_sdh.xml", "sitemap_reviews_sdh.xml",
        "sitemap_bestfor_khw.xml", "sitemap_workflow_khw.xml", "sitemap_vs_khw.xml",
        "sitemap_seasonal_khw.xml", "sitemap_reviews_khw.xml",
        "sitemap_bestfor_bcc.xml", "sitemap_workflow_bcc.xml", "sitemap_vs_bcc.xml",
        "sitemap_seasonal_bcc.xml", "sitemap_reviews_bcc.xml",
        "sitemap_bestfor_bft.xml", "sitemap_workflow_bft.xml", "sitemap_vs_bft.xml",
        "sitemap_seasonal_bft.xml", "sitemap_reviews_bft.xml",
        "sitemap_bestfor_thq.xml", "sitemap_workflow_thq.xml", "sitemap_vs_thq.xml",
        "sitemap_seasonal_thq.xml", "sitemap_reviews_thq.xml",
        "sitemap_bestfor_the.xml", "sitemap_workflow_the.xml", "sitemap_vs_the.xml",
        "sitemap_seasonal_the.xml", "sitemap_reviews_the.xml",
        "sitemap_bestfor_kfr.xml", "sitemap_workflow_kfr.xml", "sitemap_vs_kfr.xml",
        "sitemap_seasonal_kfr.xml", "sitemap_reviews_kfr.xml",
        "sitemap_bestfor_gvr.xml", "sitemap_workflow_gvr.xml", "sitemap_vs_gvr.xml",
        "sitemap_seasonal_gvr.xml", "sitemap_reviews_gvr.xml",
        "sitemap_bestfor_lif.xml", "sitemap_workflow_lif.xml", "sitemap_vs_lif.xml",
        "sitemap_seasonal_lif.xml", "sitemap_reviews_lif.xml",
        "sitemap_bestfor_sck.xml", "sitemap_workflow_sck.xml", "sitemap_vs_sck.xml",
        "sitemap_seasonal_sck.xml", "sitemap_reviews_sck.xml",
        "sitemap_bestfor_tts.xml", "sitemap_workflow_tts.xml", "sitemap_vs_tts.xml",
        "sitemap_seasonal_tts.xml", "sitemap_reviews_tts.xml",
        "sitemap_bestfor_nod.xml", "sitemap_workflow_nod.xml", "sitemap_vs_nod.xml",
        "sitemap_seasonal_nod.xml", "sitemap_reviews_nod.xml",
        "sitemap_bestfor_sou.xml", "sitemap_workflow_sou.xml", "sitemap_vs_sou.xml",
        "sitemap_seasonal_sou.xml", "sitemap_reviews_sou.xml",
        "sitemap_bestfor_khb.xml", "sitemap_workflow_khb.xml", "sitemap_vs_khb.xml",
        "sitemap_seasonal_khb.xml", "sitemap_reviews_khb.xml",
        "sitemap_bestfor_ksw.xml", "sitemap_workflow_ksw.xml", "sitemap_vs_ksw.xml",
        "sitemap_seasonal_ksw.xml", "sitemap_reviews_ksw.xml",
        "sitemap_bestfor_rki.xml", "sitemap_workflow_rki.xml", "sitemap_vs_rki.xml",
        "sitemap_seasonal_rki.xml", "sitemap_reviews_rki.xml",
        "sitemap_bestfor_luz.xml", "sitemap_workflow_luz.xml", "sitemap_vs_luz.xml",
        "sitemap_seasonal_luz.xml", "sitemap_reviews_luz.xml",
        "sitemap_bestfor_mad.xml", "sitemap_workflow_mad.xml", "sitemap_vs_mad.xml",
        "sitemap_seasonal_mad.xml", "sitemap_reviews_mad.xml",
        "sitemap_bestfor_ban.xml", "sitemap_workflow_ban.xml", "sitemap_vs_ban.xml",
        "sitemap_seasonal_ban.xml", "sitemap_reviews_ban.xml",
        "sitemap_bestfor_bjn.xml", "sitemap_workflow_bjn.xml", "sitemap_vs_bjn.xml",
        "sitemap_seasonal_bjn.xml", "sitemap_reviews_bjn.xml",
        # Locale-specific intent sitemaps kept in the growth-engine copy
        # of this generator; listed here so the two stay one file. Every
        # entry is filtered by os.path.exists below, so unbuilt locales
        # never reach the published index.
        "sitemap_problems_ven.xml",
        "sitemap_problems_tso.xml",
        "sitemap_problems_ssw.xml",
        "sitemap_problems_loz.xml",
        "sitemap_problems_bho.xml",
        "sitemap_problems_en.xml",
        "sitemap_problems_en-GB.xml",
        "sitemap_problems_en-AU.xml",
        "sitemap_problems_en-CA.xml",
        "sitemap_problems_de-DE.xml",
        "sitemap_problems_fr-FR.xml",
        "sitemap_problems_es-ES.xml",
        "sitemap_problems_es-MX.xml",
        "sitemap_problems_it-IT.xml",
        "sitemap_problems_pt-BR.xml",
        "sitemap_problems_ja-JP.xml",
        "sitemap_problems_ko-KR.xml",
        "sitemap_problems_zh-Hant.xml",
        "sitemap_problems_th.xml",
        "sitemap_problems_vi.xml",
        "sitemap_problems_id.xml",
        "sitemap_problems_ms.xml",
        "sitemap_problems_tr.xml",
        "sitemap_problems_ru.xml",
        "sitemap_problems_pl.xml",
        "sitemap_problems_hi.xml",
        "sitemap_problems_ar-SA.xml",
        "sitemap_problems_nb-NO.xml",
        "sitemap_problems_fi.xml",
        "sitemap_problems_cs.xml",
        "sitemap_payonce_en.xml",
        "sitemap_payonce_en-GB.xml",
        "sitemap_payonce_en-AU.xml",
        "sitemap_payonce_en-CA.xml",
        "sitemap_payonce_de-DE.xml",
        "sitemap_payonce_fr-FR.xml",
        "sitemap_payonce_es-ES.xml",
        "sitemap_payonce_es-MX.xml",
        "sitemap_payonce_it-IT.xml",
        "sitemap_payonce_pt-BR.xml",
        "sitemap_payonce_ja-JP.xml",
        "sitemap_payonce_ko-KR.xml",
        "sitemap_payonce_zh-Hant.xml",
        "sitemap_payonce_th.xml",
        "sitemap_payonce_vi.xml",
        "sitemap_payonce_id.xml",
        "sitemap_payonce_ms.xml",
        "sitemap_payonce_tr.xml",
        "sitemap_payonce_ru.xml",
        "sitemap_payonce_pl.xml",
        "sitemap_payonce_hi.xml",
        "sitemap_payonce_ar-SA.xml",
        "sitemap_payonce_nb-NO.xml",
        "sitemap_payonce_fi.xml",
        "sitemap_payonce_cs.xml",
        "sitemap_bestfor_zh-Hans.xml",
        "sitemap_workflow_zh-Hans.xml",
        "sitemap_vs_zh-Hans.xml",
        "sitemap_seasonal_zh-Hans.xml",
        "sitemap_reviews_zh-Hans.xml",
        "sitemap_bestfor_sv.xml",
        "sitemap_workflow_sv.xml",
        "sitemap_vs_sv.xml",
        "sitemap_seasonal_sv.xml",
        "sitemap_reviews_sv.xml",
        "sitemap_bestfor_da.xml",
        "sitemap_workflow_da.xml",
        "sitemap_vs_da.xml",
        "sitemap_seasonal_da.xml",
        "sitemap_reviews_da.xml",
        "sitemap_problems_zh-Hans.xml",
        "sitemap_problems_sv.xml",
        "sitemap_problems_da.xml",
        "sitemap_payonce_zh-Hans.xml",
        "sitemap_payonce_sv.xml",
        "sitemap_payonce_da.xml",
        "sitemap_noaccount_en.xml",
        "sitemap_noaccount_en-GB.xml",
        "sitemap_noaccount_en-AU.xml",
        "sitemap_noaccount_en-CA.xml",
        "sitemap_noaccount_de-DE.xml",
        "sitemap_noaccount_fr-FR.xml",
        "sitemap_noaccount_es-ES.xml",
        "sitemap_noaccount_es-MX.xml",
        "sitemap_noaccount_it-IT.xml",
        "sitemap_noaccount_pt-BR.xml",
        "sitemap_noaccount_ja-JP.xml",
        "sitemap_noaccount_ko-KR.xml",
        "sitemap_noaccount_zh-Hant.xml",
        "sitemap_noaccount_zh-Hans.xml",
        "sitemap_noaccount_th.xml",
        "sitemap_noaccount_vi.xml",
        "sitemap_noaccount_id.xml",
        "sitemap_noaccount_ms.xml",
        "sitemap_noaccount_tr.xml",
        "sitemap_noaccount_ru.xml",
        "sitemap_noaccount_pl.xml",
        "sitemap_noaccount_hi.xml",
        "sitemap_noaccount_ar-SA.xml",
        "sitemap_noaccount_sv.xml",
        "sitemap_noaccount_da.xml",
        "sitemap_noaccount_nb-NO.xml",
        "sitemap_noaccount_fi.xml",
        "sitemap_noaccount_cs.xml",
        "sitemap_family_en.xml",
        "sitemap_family_en-GB.xml",
        "sitemap_family_en-AU.xml",
        "sitemap_family_en-CA.xml",
        "sitemap_family_de-DE.xml",
        "sitemap_family_fr-FR.xml",
        "sitemap_family_es-ES.xml",
        "sitemap_family_es-MX.xml",
        "sitemap_family_it-IT.xml",
        "sitemap_family_pt-BR.xml",
        "sitemap_family_ja-JP.xml",
        "sitemap_family_ko-KR.xml",
        "sitemap_family_zh-Hant.xml",
        "sitemap_family_zh-Hans.xml",
        "sitemap_family_th.xml",
        "sitemap_family_vi.xml",
        "sitemap_family_id.xml",
        "sitemap_family_ms.xml",
        "sitemap_family_tr.xml",
        "sitemap_family_ru.xml",
        "sitemap_family_pl.xml",
        "sitemap_family_hi.xml",
        "sitemap_family_ar-SA.xml",
        "sitemap_family_sv.xml",
        "sitemap_family_da.xml",
        "sitemap_family_nb-NO.xml",
        "sitemap_family_fi.xml",
        "sitemap_family_cs.xml",
        "sitemap_gifting_en.xml",
        "sitemap_gifting_en-GB.xml",
        "sitemap_gifting_en-AU.xml",
        "sitemap_gifting_en-CA.xml",
        "sitemap_gifting_de-DE.xml",
        "sitemap_gifting_fr-FR.xml",
        "sitemap_gifting_es-ES.xml",
        "sitemap_gifting_es-MX.xml",
        "sitemap_gifting_it-IT.xml",
        "sitemap_gifting_pt-BR.xml",
        "sitemap_gifting_ja-JP.xml",
        "sitemap_gifting_ko-KR.xml",
        "sitemap_gifting_zh-Hant.xml",
        "sitemap_gifting_zh-Hans.xml",
        "sitemap_gifting_th.xml",
        "sitemap_gifting_vi.xml",
        "sitemap_gifting_id.xml",
        "sitemap_gifting_ms.xml",
        "sitemap_gifting_tr.xml",
        "sitemap_gifting_ru.xml",
        "sitemap_gifting_pl.xml",
        "sitemap_gifting_hi.xml",
        "sitemap_gifting_ar-SA.xml",
        "sitemap_gifting_sv.xml",
        "sitemap_gifting_da.xml",
        "sitemap_gifting_nb-NO.xml",
        "sitemap_gifting_fi.xml",
        "sitemap_gifting_cs.xml",
        "sitemap_switching_en.xml",
        "sitemap_switching_en-GB.xml",
        "sitemap_switching_en-AU.xml",
        "sitemap_switching_en-CA.xml",
        "sitemap_switching_de-DE.xml",
        "sitemap_switching_fr-FR.xml",
        "sitemap_switching_es-ES.xml",
        "sitemap_switching_es-MX.xml",
        "sitemap_switching_it-IT.xml",
        "sitemap_switching_pt-BR.xml",
        "sitemap_switching_ja-JP.xml",
        "sitemap_switching_ko-KR.xml",
        "sitemap_switching_zh-Hant.xml",
        "sitemap_switching_zh-Hans.xml",
        "sitemap_switching_th.xml",
        "sitemap_switching_vi.xml",
        "sitemap_switching_id.xml",
        "sitemap_switching_ms.xml",
        "sitemap_switching_tr.xml",
        "sitemap_switching_ru.xml",
        "sitemap_switching_pl.xml",
        "sitemap_switching_hi.xml",
        "sitemap_switching_ar-SA.xml",
        "sitemap_switching_sv.xml",
        "sitemap_switching_da.xml",
        "sitemap_switching_nb-NO.xml",
        "sitemap_switching_fi.xml",
        "sitemap_switching_cs.xml",
        "sitemap_choose_en.xml",
        "sitemap_choose_en-GB.xml",
        "sitemap_choose_en-AU.xml",
        "sitemap_choose_en-CA.xml",
        "sitemap_choose_de-DE.xml",
        "sitemap_choose_fr-FR.xml",
        "sitemap_choose_es-ES.xml",
        "sitemap_choose_es-MX.xml",
        "sitemap_choose_it-IT.xml",
        "sitemap_choose_pt-BR.xml",
        "sitemap_choose_ja-JP.xml",
        "sitemap_choose_ko-KR.xml",
        "sitemap_choose_zh-Hant.xml",
        "sitemap_choose_zh-Hans.xml",
        "sitemap_choose_th.xml",
        "sitemap_choose_vi.xml",
        "sitemap_choose_id.xml",
        "sitemap_choose_ms.xml",
        "sitemap_choose_tr.xml",
        "sitemap_choose_ru.xml",
        "sitemap_choose_pl.xml",
        "sitemap_choose_hi.xml",
        "sitemap_choose_ar-SA.xml",
        "sitemap_choose_sv.xml",
        "sitemap_choose_da.xml",
        "sitemap_choose_nb-NO.xml",
        "sitemap_choose_fi.xml",
        "sitemap_choose_cs.xml",
        "sitemap_problems_mag.xml",
        "sitemap_problems_new.xml",
        "sitemap_problems_mai.xml",
        "sitemap_problems_raj.xml",
        "sitemap_problems_mah.xml",
        "sitemap_problems_tvl.xml",
        "sitemap_problems_sm.xml",
        "sitemap_problems_nah.xml",
    ])
    maps = list(dict.fromkeys(maps))
    items = "\n".join(
        f"  <sitemap><loc>{SITE}/{m}</loc></sitemap>"
        for m in maps
        if sitemap_has_entries(Path(PAGES) / m)
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + items + "\n</sitemapindex>\n")


def publish(urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-500:]); return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add llms.txt + AI-crawler robots + sitemap index (top-tier AEO)"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            try:
                req = urllib.request.Request(ep, data=payload,
                                             headers={"Content-Type": "application/json; charset=utf-8"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the verified availability snapshot without refreshing it.",
    )
    args = ap.parse_args()
    publisher_intent_catalog.use_frozen_mcp_distribution(Path(PAGES))
    comp_map = load_competitors()
    live_keys = live_app_keys(
        APPSTORE, PAGES, refresh=not args.cached_live
    )
    localized_stats = write_localized_llms(live_keys)
    open(os.path.join(PAGES, "llms.txt"), "w", encoding="utf-8").write(build_llms(comp_map, live_keys))
    open(os.path.join(PAGES, "llms-full.txt"), "w", encoding="utf-8").write(
        build_llms_full(comp_map, live_keys))
    open(os.path.join(PAGES, "robots.txt"), "w", encoding="utf-8").write(build_robots())
    open(os.path.join(PAGES, "sitemap_index.xml"), "w", encoding="utf-8").write(build_sitemap_index())
    print(
        "✓ llms.txt / llms-full.txt / 50 localized catalogs / "
        f"robots.txt / sitemap_index.xml → {PAGES}"
    )
    print(f"  收錄 {len(live_keys)}/{len(APPS)} 個已公開 app；robots 歡迎 {len(AI_BOTS)} 個 AI/搜尋 bot")
    print(
        "  localized llms: "
        + ", ".join(
            f"{key}={value}" for key, value in localized_stats.items()
        )
    )
    if args.publish:
        publish([
            f"{SITE}/llms.txt", f"{SITE}/llms-full.txt",
            f"{SITE}/robots.txt", f"{SITE}/sitemap_index.xml",
            f"{SITE}/llms/index.json", f"{SITE}/sitemap_llms.xml",
            *[
                localized_llms_url(locale)
                for locale in OFFICIAL_LOCALES
            ],
        ])
    else:
        print("（加 --publish 部署)")


if __name__ == "__main__":
    main()
