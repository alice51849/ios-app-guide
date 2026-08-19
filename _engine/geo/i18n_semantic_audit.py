#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic audit for the localized GEO site: find translations that are *wrong*,
not merely missing.

Coverage passes (``i18n_page_patch.py``, ``i18n_batch_apply.py``) answer "is this
span still English?".  They cannot see the more damaging failure mode: a span that
*is* translated but says the opposite of, or something unrelated to, the English
source.  A page that renders "best app to blur photos" in Spanish for the query
"best app to unblur photos" is worse than one that renders the English -- it lies
to the reader about what the app does.

Checks
------
reversal   curated per-locale term table.  Each rule is a regex that must never
           appear in that locale (optionally: only when the English source page
           carries a trigger term), plus the correct replacement.  This is where
           verified antonyms, mistransliterations and off-topic renderings live.
negation   the English source says "no X" / "X-free"; the localized title, meta
           description or H1 must then carry a negation marker for that language.
           A dropped negation flips a pricing or capability claim.
mixed      a localized title/H1 that still carries English function words is a
           half-substituted string ("abc menekap app for kids with no ads"), the
           signature of a glossary word-replacement that ran over untranslated
           English.
collision  one target string serving three or more distinct long English strings
           in the same dictionary: the translator emitted canned boilerplate
           instead of translating, so several different answers now read alike.
numeric    digits present in the English source but absent from the translation
           (prices, counts, "37 symbols"): a factual drift check.

Usage
-----
    python3 i18n_semantic_audit.py --check all                # audit everything
    python3 i18n_semantic_audit.py --check reversal --fix     # apply the fixes
    python3 i18n_semantic_audit.py --locales "es-ES pt-BR" --json report.json

``--fix`` rewrites the curated ``reversal`` rules in both the shared dictionaries
and the published HTML.  HTML is only ever written when every guard holds:
the tag sequence is byte-identical, href/hreflang counts are unchanged,
``</head>``/``</body>`` survive, and every JSON-LD block still parses -- the same
contract ``i18n_page_patch.py`` enforces.  Unlike that tool this one *does* touch
spans that already carry a translation, which is precisely the point: those are
the spans that are wrong.
"""
from __future__ import annotations

import argparse
import html as _html
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

TAG_RX = re.compile(r"<[^>]+>")
ATTR_VAL_RX = re.compile(r'="[^"]*"')
HREF_RX = re.compile(r'(?:href|hreflang|src)="([^"]*)"')
SCRIPT_RX = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)
TITLE_RX = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RX = re.compile(r'<meta name="description" content="(.*?)"', re.S)
H1_RX = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def _load_i18n():
    spec = importlib.util.spec_from_file_location("_aeo_i18n", ROOT / "aeo_answers_i18n.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# reversal rules
# ---------------------------------------------------------------------------
# (pattern, replacement | None, category, note)
#   pattern      regex matched against localized text
#   replacement  what --fix writes; None means "report only, needs a human"
#   category     reversal | offtopic | spelling | inconsistent | factual
# Rules are applied in order, so put the longest / most specific first.
REVERSAL_RULES: dict[str, list[tuple[str, str | None, str, str]]] = {
    # --- unblur rendered as its antonym "blur" -----------------------------
    "es-ES": [
        (r"para desenfocar fotos", "para quitar el desenfoque de las fotos", "reversal",
         "'desenfocar' means *to blur*; the page is about un-blurring"),
        (r"en desenfocar fotos", "en quitar el desenfoque de las fotos", "reversal",
         "'desenfocar' means *to blur*"),
        (r"desenfocar y mejorar", "quitar el desenfoque y mejorar", "reversal",
         "claims the app blurs your images"),
        (r"mejorar y desenfocar fotos", "mejorar y dar nitidez a fotos", "reversal",
         "meta description claims the app blurs your photos"),
        (r"\bdesenfocar\b", None, "reversal", "verb 'to blur' -- check the surrounding claim"),
    ],
    "es-MX": [
        (r"para desenfocar fotos", "para quitar el desenfoque de las fotos", "reversal",
         "'desenfocar' means *to blur*"),
    ],
    "pt-BR": [
        (r"aprimorar e desfocar fotos", "aprimorar e dar nitidez a fotos", "reversal",
         "meta description claims the app blurs your photos"),
        (r"duplicatas, desfocar e", "duplicatas, fotos borradas e", "reversal",
         "noun list: 'blurry' became the verb 'to blur'"),
        (r"para desfocar fotos", "para tirar o desfoque das fotos", "reversal",
         "'desfocar' means *to blur*; the page is about un-blurring"),
        (r"em desfocar fotos", "em tirar o desfoque das fotos", "reversal",
         "'desfocar' means *to blur*"),
        (r"\bdesfocar\b", None, "reversal", "verb 'to blur' -- check the surrounding claim"),
    ],
    "pt-PT": [
        (r"para desfocar foto", "para tirar a desfocagem da foto", "reversal",
         "'desfocar' means *to blur*; the page is about un-blurring"),
        (r"desfocar foto melhorar foto", "remover desfoque foto melhorar foto", "reversal",
         "feature list advertises blurring instead of un-blurring"),
    ],
    "de-DE": [
        (r"zum Entschärfen von Fotos", "zum Schärfen unscharfer Fotos", "reversal",
         "'entschärfen' means *to defuse*, and reads as the opposite of sharpening"),
        (r"Verbesserung und Entblurrung von Fotos", "Verbesserung und Schärfung von Fotos",
         "inconsistent", "'Entblurrung' is not German"),
        (r"Entblurren von Fotos", "Schärfen unscharfer Fotos", "inconsistent",
         "'Entblurren' is not German and clashes with the other pages' wording"),
    ],
    "uk": [
        (r"для покращення та розмиття фотографій",
         "для покращення та усунення розмиття фотографій", "reversal",
         "'розмиття' = blurring; the app removes blur"),
        (r"додаток для розмиття фотографій", "додаток для усунення розмиття фотографій",
         "reversal", "'розмиття' = blurring; the app removes blur"),
    ],
    "nl-NL": [
        (r"het verhelderen van foto", "het verscherpen van foto", "inconsistent",
         "'verhelderen' = to brighten, not to remove blur"),
        (r"en verhelderen van foto", "en verscherpen van foto", "inconsistent",
         "'verhelderen' = to brighten, not to remove blur"),
        (r"te verhelderen", "scherper te maken", "inconsistent",
         "'verhelderen' = to brighten, not to remove blur"),
    ],
    # --- "no subscription" rendered as something else ----------------------
    "te-IN": [
        (r"ఉపసంహరణ లేకుండా", "సబ్‌స్క్రిప్షన్ లేకుండా", "reversal",
         "'ఉపసంహరణ' means *withdrawal*, not *subscription*"),
    ],
    "ko": [
        (r"일일 지출 한도가 있는 오프라인 유럽 배낭여행 예산 추적기는 구독이 없으면 평생 소장·한 번 구매합니다\.",
         "일일 지출 한도가 있는 오프라인 유럽 배낭여행 예산 추적기, 구독 없이 한 번만 결제", "reversal",
         "reads 'if there is no subscription you buy it once', a conditional the English never makes"),
        (r"가입하지 않은 여행자를 위한 오프라인 비용 추적기",
         "구독 없는 여행자용 오프라인 지출 관리 앱", "reversal",
         "'가입하지 않은 여행자' = travellers who have not signed up; English says 'with no subscription'"),
        (r"초점 소리 앱은 구독하지 않고 한 번 구매합니다\.",
         "집중 사운드 앱, 구독 없이 한 번만 결제", "reversal",
         "'초점 소리' = focal-point sound; the product is focus sounds"),
    ],
    # --- off-topic / mistransliterated ------------------------------------
    "or-IN": [
        (r"ଓଟରମାର୍କ", "ୱାଟରମାର୍କ", "spelling", "'watermark' transliterated wrongly"),
    ],
    "pa-IN": [
        (r"ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨਾਂ ਨੂੰ ਨਵੇਂ ਖੇਤਰ ਦੀ ਭਾਸ਼ਾ ਵਿੱਚ ਦੁਬਾਰਾ ਲਿਖੋ",
         "ਬੁਲੇਟ ਪੁਆਇੰਟਾਂ ਨੂੰ ਨਵੇਂ ਖੇਤਰ ਦੀ ਭਾਸ਼ਾ ਵਿੱਚ ਦੁਬਾਰਾ ਲਿਖੋ", "offtopic",
         "'ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨ' = wooden marks; English says 'bullets'"),
        (r"ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨਾਂ ਨੂੰ ਨਕਲ ਕਰਨਾ ਲੋੜੀਂਦਾ ਹੈ",
         "ਟਾਰਗੇਟ ਨੌਕਰੀ ਦੇ ਕੀਵਰਡ ਦੁਹਰਾਉਣੇ ਲੋੜੀਂਦੇ ਹਨ", "offtopic",
         "'ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨ' = wooden marks; English says 'the target job's keywords'"),
        (r"ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨਾਂ ਨੂੰ ਨਕਲ ਕਰੋ",
         "ਟਾਰਗੇਟ ਨੌਕਰੀ ਦੇ ਕੀਵਰਡ ਦੁਹਰਾਓ", "offtopic",
         "'ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨ' = wooden marks; English says 'the target job's keywords'"),
        (r"ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨਾਂ ਨੂੰ ਪੇਸਟ ਕਰੋ",
         "ਟਾਰਗੇਟ ਨੌਕਰੀ ਦਾ ਵੇਰਵਾ ਪੇਸਟ ਕਰੋ", "offtopic",
         "'ਲਕੜੀ ਦੇ ਨਿਸ਼ਾਨ' = wooden marks; English says 'the target job description'"),
        (r"ਭਾਸ਼ਾ ਲਕੜੀਆਂ", "ਭਾਸ਼ਾ ਡੈੱਕ", "offtopic",
         "'ਲਕੜੀਆਂ' = pieces of wood; English says 'language decks'"),
    ],
}

# Verified literal corrections that are too numerous (and too data-shaped) to
# keep inline: {locale: [[wrong, right, category, note], ...]}.  They are merged
# into REVERSAL_RULES as escaped literals at import time, so `--fix` and the
# audit both see them.
FIXES_FILE = ROOT / "i18n_semantic_fixes.json"
# patterns that are escaped literals rather than hand-written regexes; only
# those may be re-derived into HTML-escaped variants.
LITERAL_PATTERNS: set[str] = set()


def _load_sidecar() -> None:
    if not FIXES_FILE.exists():
        return
    data = json.loads(FIXES_FILE.read_text(encoding="utf-8"))
    for locale, rows in data.items():
        bucket = REVERSAL_RULES.setdefault(locale, [])
        for wrong, right, category, note in rows:
            pattern = re.escape(wrong)
            LITERAL_PATTERNS.add(pattern)
            bucket.append((pattern, right, category, note))


_load_sidecar()


# ---------------------------------------------------------------------------
# negation markers -- a locale-level closed list; a "no X" claim in English must
# leave at least one of these in the localized title/description/H1.
# ---------------------------------------------------------------------------
NEGATION = {
    "ar-SA": r"بلا|بدون|دون|لا |غير|مجان|خال|خالٍ|خالية",
    "bn-BD": r"ছাড়া|নেই|বিনা|না\b|মুক্ত|বিহীন|হীন|লাগে না",
    "ca": r"\bsense\b|\bcap\b|\bno\b|gratu",
    "cs": r"\bbez|žádn|nulov|zdarma",
    "da": r"\buden\b|\bingen\b|\bikke\b|fri|gratis|aldrig|\bnej\b",
    "de-DE": r"\bohne\b|\bkein|frei|gratis|kostenlos|\bnein\b|\bnicht\b|\bnie\b",
    "el": r"χωρίς|καμία|κανένα|δεν |μη |δωρεάν",
    "es-ES": r"\bsin\b|ningun|\bno\b|gratis|gratu|libre de|ausencia|jamás|nunca",
    "es-MX": r"\bsin\b|ningun|\bno\b|gratis|gratu|libre de|ausencia|jamás|nunca",
    "fi": r"\bilman\b|\bei\b|ton\b|tön\b|ttom|maksuton|ilmai",
    "fr-FR": r"\bsans\b|aucun|\bpas d|gratuit|zéro|absence|\bnon\b|\bni\b|jamais",
    "gu-IN": r"વગર|વિના|નથી|નહીં|ના\b|મુક્ત|રહિત| વિનાનું",
    "he": r"ללא|בלי|אין|חינם|לא\b|נטול",
    "hi": r"बिना|नहीं|बगैर|रहित|मुफ़्त|मुफ्त|फ्री|मुक्त",
    "hr": r"\bbez\b|nema|besplat",
    "hu": r"nélkül|nincs|mentes|ingyen",
    "id": r"\btanpa\b|\btidak\b|\bbebas\b|gratis|nol|bukan",
    "it": r"\bsenza\b|nessun|\bno\b|gratis|gratuit|niente|priv[ao] di|una tantum|mai\b",
    "ja": r"なし|ない|ません|不要|ゼロ|無料|無し|レス|買い切り|一括購入|いいえ|フリー",
    "kn-IN": r"ಇಲ್ಲದೆ|ಇಲ್ಲ|ಿಲ್ಲ|ರಹಿತ|ಉಚಿತ|ಬೇಡ",
    "ko": r"없|무료|미포함|제로|않|불필요|무광고|아니|안 ",
    "ml-IN": r"ഇല്ലാതെ|ഇല്ല|ില്ലാ|രഹിത|സൗജന്യ|വേണ്ട",
    "mr-IN": r"शिवाय|विना|नाही|नको|रहित|मोफत|नसले|नसता",
    "ms": r"\btanpa\b|\btiada\b|\bbebas\b|percuma|bukan",
    "nl-NL": r"\bzonder\b|\bgeen\b|vrij|gratis|nooit|nimmer|\bniet\b",
    "no": r"\buten\b|\bingen\b|\bikke\b|fri|gratis|aldri|\bnei\b",
    "or-IN": r"ବିନା|ନାହିଁ|ନାହିଣ|ରହିତ|ମାଗଣା|ନା\b",
    "pa-IN": r"ਬਿਨਾਂ|ਬਿਨਾ|ਨਹੀਂ|ਰਹਿਤ|ਮੁਫ਼ਤ|ਮੁਫਤ",
    "pl": r"\bbez\b|żadn|\bbrak\b|\bnie\b|darmow|zero",
    "pt-BR": r"\bsem\b|nenhum|\bnão\b|gr[áa]tis|gratuit|zero|livre de|ausência|nunca|jamais",
    "pt-PT": r"\bsem\b|nenhum|\bnão\b|gr[áa]tis|gratuit|zero|livre de|ausência|nunca|jamais",
    "ro": r"\bfără\b|\bfara\b|niciun|\bnu\b|gratuit",
    "ru": r"\bбез|\bнет\b|\bне\b|беспла|нулев|никак|ноль",
    "sk": r"\bbez\b|žiadn|zadarmo",
    "sl-SI": r"\bbrez\b|\bni\b|brezplač",
    "sv": r"\butan\b|\bing(?:en|a|et)\b|fri|gratis|aldrig|\binte\b|\bnej\b",
    "ta-IN": r"இல்லா|இல்லை|ில்லா|அற்ற|இன்றி|இலவச|தேவையில்",
    "te-IN": r"లేకుండా|లేదు|రహిత|లేని|ఉచిత|లేకపోవ",
    "th": r"ไม่|ปราศจาก|ฟรี|ปลอด",
    "tr": r"s[ıi]z|suz|süz|olma|\byok\b|ücretsiz|bedava|gerektirmeyen|mez\b|maz\b|hayır",
    "uk": r"\bбез|нема|\bне\b|безкошт|жодн|нуль",
    "ur-PK": r"بغیر|بنا|نہیں|مفت",
    "vi": r"không|miễn|chẳng|chưa",
    "zh-Hans": r"无|不|免|没|零|非",
    "zh-Hant": r"無|不|免|沒|零|非",
}

NEG_TRIGGER = re.compile(
    r"no subscription|without subscription|no ads|ad-free|no watermark|watermark-free"
    r"|no account|without an account|no login|no cloud|no wifi|without internet"
    r"|no monthly|no ongoing|no in-app purchase|no data collection",
    re.I,
)

# English function words that must not survive into a localized headline.  The
# per-locale exclusions are real words in that language ("for" is Norwegian,
# "in"/"a" are Italian, "de"/"a" are Romance) and would fire constantly.
MIXED_FN = r"\b(for|with|and|the|that|of|to|my|your|without|from|best|how|what|can|does|when|while|before|after)\b"
MIXED_SKIP = {"no", "da", "sv", "nl-NL", "de-DE", "it", "fr-FR", "fr-CA", "ca", "ro", "en"}

NUM_RX = re.compile(r"\d+(?:[.,]\d+)?")
DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹০১২৩৪৫৬৭৮৯०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯",
                          "0123456789" * 5)


def site_locales() -> list[str]:
    locs = sorted({p.parent.name for p in PAGES.glob("*/answers")})
    return [l for l in locs if not l.startswith("en")]


def nfc(text: str) -> str:
    """Indic and Hebrew pages mix precomposed and nukta-decomposed forms of the
    same grapheme (ਸ਼ = U+0A36 vs U+0A38 U+0A3C).  Every comparison in this file
    runs on NFC so a rule written one way still matches text written the other."""
    return unicodedata.normalize("NFC", text)


def visible_text(source: str) -> str:
    return nfc(_html.unescape(TAG_RX.sub(" ", SCRIPT_RX.sub(" ", source))))


def _first(rx: re.Pattern, source: str) -> str | None:
    m = rx.search(source)
    if not m:
        return None
    return _html.unescape(TAG_RX.sub("", m.group(1))).strip()


def untranslated(en: str, target: str) -> bool:
    """True when the target merely *wraps* the untouched English string.

    Thin locales publish titles such as "abc tracing app for kids with no ads –
    دليل صادق لاختيار تطبيقات iPhone": the query was never translated, only the
    boilerplate suffix was.  That is a coverage gap for the translation waves to
    close, not a meaning error, and it would otherwise drown out the real
    findings in the mixed and negation checks.
    """
    e = re.sub(r"\s+", " ", en.strip().lower())
    t = re.sub(r"\s+", " ", target.strip().lower())
    if e == t or e in t:
        return True
    # the query part before the boilerplate separator
    head = re.split(r"\s[:\u2013\u2014-]\s|: ", e)[0]
    return len(head) >= 12 and head in t


def head_strings(source: str) -> tuple[str | None, str | None, str | None]:
    return _first(TITLE_RX, source), _first(DESC_RX, source), _first(H1_RX, source)


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def check_reversal(locales: list[str], findings: list[dict]) -> None:
    for locale in locales:
        rules = REVERSAL_RULES.get(locale)
        if not rules:
            continue
        compiled = [(re.compile(nfc(p)), rep, cat, note) for p, rep, cat, note in rules]
        # dictionary
        dpath = TRANS / f"{locale}.json"
        if dpath.exists():
            for en, target in json.loads(dpath.read_text(encoding="utf-8")).items():
                for rx, rep, cat, note in compiled:
                    if rx.search(nfc(target)):
                        findings.append({
                            "check": "reversal", "category": cat, "locale": locale,
                            "where": f"dict:{dpath.name}", "en": en[:160],
                            "found": rx.pattern, "target": target[:160],
                            "fix": rep, "note": note,
                        })
                        break
        # pages
        base = PAGES / locale
        if not base.is_dir():
            continue
        for page in sorted(base.rglob("*.html")):
            text = visible_text(page.read_text(encoding="utf-8", errors="ignore"))
            for rx, rep, cat, note in compiled:
                m = rx.search(text)
                if m:
                    findings.append({
                        "check": "reversal", "category": cat, "locale": locale,
                        "where": str(page.relative_to(PAGES)),
                        "found": rx.pattern,
                        "target": re.sub(r"\s+", " ", text[max(0, m.start() - 40):m.end() + 40]).strip(),
                        "fix": rep, "note": note,
                    })
                    break


def check_negation(locales: list[str], en_head: dict, findings: list[dict]) -> None:
    for locale in locales:
        pattern = NEGATION.get(locale)
        if not pattern:
            continue
        rx = re.compile(pattern, re.I)
        d = PAGES / locale / "answers"
        if not d.is_dir():
            continue
        for page in sorted(d.glob("*.html")):
            en = en_head.get(page.name)
            if not en:
                continue
            src = page.read_text(encoding="utf-8", errors="ignore")
            loc = head_strings(src)
            # Only title and H1 are translations *of the English string in the
            # same slot*.  The localized meta description comes from a separate
            # template that quotes the raw English query, so comparing it against
            # the English description would report every page.
            for idx, field in ((0, "title"), (2, "h1")):
                e, l = en[idx], loc[idx]
                if not e or not l or not NEG_TRIGGER.search(e):
                    continue
                if untranslated(e, l):
                    continue  # still English: a coverage problem, not a meaning one
                if not rx.search(l):
                    findings.append({
                        "check": "negation", "category": "reversal", "locale": locale,
                        "where": f"{locale}/answers/{page.name}#{field}",
                        "en": e, "target": l, "fix": None,
                        "note": "English states a 'no X' claim; translation carries no negation marker",
                    })


def check_mixed(locales: list[str], en_head: dict, findings: list[dict]) -> None:
    fn = re.compile(MIXED_FN, re.I)
    for locale in locales:
        if locale in MIXED_SKIP:
            continue
        d = PAGES / locale / "answers"
        if not d.is_dir():
            continue
        for page in sorted(d.glob("*.html")):
            en = en_head.get(page.name)
            if not en:
                continue
            loc = head_strings(page.read_text(encoding="utf-8", errors="ignore"))
            for idx, field in ((0, "title"), (2, "h1")):
                e, l = en[idx], loc[idx]
                if not e or not l or untranslated(e, l):
                    continue
                if len(fn.findall(e)) >= 2 and len(fn.findall(l)) >= 2:
                    findings.append({
                        "check": "mixed", "category": "inconsistent", "locale": locale,
                        "where": f"{locale}/answers/{page.name}#{field}",
                        "en": e, "target": l, "fix": None,
                        "note": "half-substituted string: English sentence with glossary words spliced in",
                    })


def check_collision(locales: list[str], findings: list[dict], min_len: int = 60,
                    min_group: int = 3) -> None:
    for locale in locales:
        dpath = TRANS / f"{locale}.json"
        if not dpath.exists():
            continue
        inverse: dict[str, list[str]] = defaultdict(list)
        for en, target in json.loads(dpath.read_text(encoding="utf-8")).items():
            if len(en) >= min_len:
                inverse[target].append(en)
        for target, sources in inverse.items():
            if len(sources) < min_group:
                continue
            # near-identical English legitimately shares one translation
            heads = {s[:40].lower() for s in sources}
            if len(heads) < min_group:
                continue
            findings.append({
                "check": "collision", "category": "factual", "locale": locale,
                "where": f"dict:{dpath.name}", "en": " | ".join(s[:70] for s in sources[:4]),
                "target": target[:160], "fix": None,
                "note": f"{len(sources)} distinct English strings collapsed onto one translation",
            })


def _numbers(text: str) -> Counter:
    """Integer values in a string, separator-agnostic.

    Locales write the same quantity as 8,400 / 8.400 / 8 400 / 8\u202f400 / 8400
    and Arabic/Indic scripts use their own digits, so comparing raw substrings
    reports a false error on almost every large number.  Only values >= 10 are
    collected: single digits are routinely spelled out ("4 tone marks" ->
    "quatre") and would drown the real findings.
    """
    normalized = re.sub(r"(?<=\d)[\s\u00a0\u202f\u2009.,'\u2019](?=\d)", "",
                        text.translate(DIGIT_MAP))
    out = Counter()
    for token in re.findall(r"\d+", normalized):
        if int(token) >= 10:
            out[str(int(token))] += 1
    return out


def check_numeric(locales: list[str], findings: list[dict]) -> None:
    for locale in locales:
        dpath = TRANS / f"{locale}.json"
        if not dpath.exists():
            continue
        for en, target in json.loads(dpath.read_text(encoding="utf-8")).items():
            missing = _numbers(en) - _numbers(target)
            if missing:
                findings.append({
                    "check": "numeric", "category": "factual", "locale": locale,
                    "where": f"dict:{dpath.name}", "en": en[:200], "target": target[:200],
                    "fix": None,
                    "note": f"numbers missing from translation: {sorted(missing)}",
                })


# ---------------------------------------------------------------------------
# fixer
# ---------------------------------------------------------------------------
_ENTITY = re.compile(r"&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")


def _unsafe(replacement: str) -> bool:
    """A replacement may not introduce markup or a broken escape.

    ``&`` is allowed only as a complete character reference, because the same
    correction is applied to raw text and to HTML-escaped text (see
    ``_rule_variants``) and the escaped variant legitimately contains
    ``&amp;`` / ``&#x27;``.
    """
    return bool(re.search(r'[<>"\\]', replacement)) or bool(
        re.search(r"&", _ENTITY.sub("", replacement)))


def _rule_variants(pattern: str, replacement: str) -> list[tuple[str, str]]:
    """Yield the raw rule plus its HTML-escaped forms.

    A headline lives in the page three ways: as a text node (``&amp;`` for
    ampersands, apostrophes raw), inside ``content="..."`` (apostrophes become
    ``&#x27;``) and inside JSON-LD (raw).  Matching only the raw form would
    silently skip the escaped copies, which is how earlier passes left the
    ``<title>`` and og: tags stale.
    """
    out: list[tuple[str, str]] = [(pattern, replacement)]
    if pattern not in LITERAL_PATTERNS:
        return out  # hand-written regex: expanding it would corrupt \b, [], ...
    literal = re.sub(r"\\(.)", r"\1", pattern)
    seen = {pattern}
    for quote in (False, True):
        pat = re.escape(_html.escape(literal, quote=quote))
        if pat in seen:
            continue
        seen.add(pat)
        out.append((pat, _html.escape(replacement, quote=quote)))
    return out


def fix_locale(locale: str, i18n, dry_run: bool) -> tuple[int, int, int]:
    """Apply the curated reversal rules to the dictionary and the published HTML.

    Substitution runs on the raw file text rather than on extracted spans: the
    same wrong phrase shows up in text nodes, in ``content=``/``title=``/
    ``data-search=`` attributes, inside JSON-LD and inside the inline JSON that
    powers the finder widgets, and a span-only pass silently leaves most of them
    behind.  That is only safe because every replacement string is plain text --
    ``SAFE_REPL`` refuses any rule carrying ``< > " & \\`` -- so a substitution
    can neither open a tag, close an attribute, nor break a JSON escape.  The
    guards below then re-verify structure, link targets and JSON-LD parseability
    before anything is written.
    """
    dict_rules = []   # JSON dictionaries store unescaped text
    html_rules = []   # pages store the same string raw and HTML-escaped
    for pattern, replacement, _cat, _note in REVERSAL_RULES.get(locale, ()):
        if replacement is None:
            continue
        variants = _rule_variants(pattern, replacement)
        dict_rules.append((re.compile(nfc(pattern)), nfc(replacement)))
        safe = [(p_, r_) for p_, r_ in variants if not _unsafe(r_)]
        if not safe:
            raise ValueError(f"unsafe replacement for {locale}: {replacement!r}")
        html_rules.extend((re.compile(nfc(p_)), nfc(r_)) for p_, r_ in safe)
    if not html_rules:
        return 0, 0, 0

    def _apply(text: str, rules) -> str:
        out = nfc(text)
        for rx, rep in rules:
            out = rx.sub(rep, out)
        return out

    def rewrite(text: str) -> str:
        return _apply(text, dict_rules)

    dict_edits = 0
    dpath = TRANS / f"{locale}.json"
    if dpath.exists():
        data = json.loads(dpath.read_text(encoding="utf-8"))
        changed = False
        for en, target in list(data.items()):
            new = rewrite(target)
            if new != nfc(target):
                data[en] = new
                dict_edits += 1
                changed = True
        if changed and not dry_run:
            dpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = failures = 0
    base = PAGES / locale
    if not base.is_dir():
        return dict_edits, 0, 0
    for page in sorted(list(base.rglob("*.html")) + list(base.rglob("*.md"))):
        src = page.read_text(encoding="utf-8", errors="ignore")
        out = _apply(src, html_rules)
        if out == nfc(src):
            continue
        try:
            # structure: tag names, attribute names and nesting must be identical.
            # Attribute *values* are compared separately because this pass exists
            # precisely to rewrite <title>, meta content and title= tooltips.
            if ([ATTR_VAL_RX.sub('=""', t) for t in TAG_RX.findall(out)]
                    != [ATTR_VAL_RX.sub('=""', t) for t in TAG_RX.findall(nfc(src))]):
                raise ValueError("tag sequence changed")
            if sorted(HREF_RX.findall(out)) != sorted(HREF_RX.findall(src)):
                raise ValueError("link targets changed")
            for token in ("href=", "hreflang=", "</head>", "</body>"):
                if out.count(token) != src.count(token):
                    raise ValueError(f"{token!r} count changed")
            for _s, _e, raw in i18n.extract_strings(out)[2]:
                json.loads(raw)  # every JSON-LD block still parses
            left = [rx.pattern for rx, _rep in html_rules if rx.search(out)]
            if left:
                raise ValueError(f"pattern still present after fix: {left}")
        except Exception as exc:  # noqa: BLE001 - report and keep the old page
            failures += 1
            print(f"  FAIL {page.relative_to(PAGES)}: {exc}", file=sys.stderr)
            continue
        pages += 1
        if not dry_run:
            page.write_text(out, encoding="utf-8")
    return dict_edits, pages, failures


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", default="all",
                    help="all | reversal | negation | mixed | collision | numeric (comma separated)")
    ap.add_argument("--locales", help="space/comma separated locales (default: every site locale)")
    ap.add_argument("--json", help="write the full finding list here")
    ap.add_argument("--fix", action="store_true", help="apply the curated reversal fixes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=8, help="examples printed per bucket")
    args = ap.parse_args()

    locales = ([x for x in re.split(r"[\s,]+", args.locales) if x]
               if args.locales else site_locales())
    checks = ({"reversal", "negation", "mixed", "collision", "numeric"}
              if args.check == "all" else set(re.split(r"[\s,]+", args.check)))

    if args.fix:
        i18n = _load_i18n()
        total_d = total_p = total_f = 0
        for locale in locales:
            d, p, f = fix_locale(locale, i18n, args.dry_run)
            if d or p or f:
                print(f"[{locale}] dictionary entries fixed: {d}, pages rewritten: {p}, failed: {f}")
            total_d += d
            total_p += p
            total_f += f
        print(f"TOTAL dictionary {total_d}, pages {total_p}, failed {total_f}"
              + (" (dry run)" if args.dry_run else ""))
        return 1 if total_f else 0

    findings: list[dict] = []
    en_head = {}
    if {"negation", "mixed"} & checks:
        for page in (PAGES / "answers").glob("*.html"):
            if page.name != "index.html":
                en_head[page.name] = head_strings(page.read_text(encoding="utf-8", errors="ignore"))

    if "reversal" in checks:
        check_reversal(locales, findings)
    if "negation" in checks:
        check_negation(locales, en_head, findings)
    if "mixed" in checks:
        check_mixed(locales, en_head, findings)
    if "collision" in checks:
        check_collision(locales, findings)
    if "numeric" in checks:
        check_numeric(locales, findings)

    by_check = Counter(f["check"] for f in findings)
    by_cat = Counter(f["category"] for f in findings)
    print(f"findings: {len(findings)}")
    print("  by check:    " + ", ".join(f"{k}={v}" for k, v in by_check.most_common()))
    print("  by category: " + ", ".join(f"{k}={v}" for k, v in by_cat.most_common()))
    for check in sorted(by_check):
        rows = [f for f in findings if f["check"] == check]
        locs = Counter(f["locale"] for f in rows)
        print(f"\n### {check} ({len(rows)}) — " + ", ".join(f"{k}:{v}" for k, v in locs.most_common(12)))
        for row in rows[:args.limit]:
            print(f"  [{row['locale']}] {row['where']}")
            if row.get("en"):
                print(f"     EN  {row['en'][:120]}")
            print(f"     XX  {row['target'][:120]}")
            print(f"     ->  {row['note']}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(findings, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
