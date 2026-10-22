#!/usr/bin/env python3
"""Translate the *page queries* -- the `<h1>`/`<title>`/meta text of every
answer page -- by composing them from search-shaped frames.

Why a separate expander
-----------------------
The query is the single most visible string on an answer page: it is the
headline, the browser tab, the meta description and the snippet a search engine
shows.  It is also the string the rest of the page is built from -- once a query
is in the dictionary, ``i18n_pattern_expand.py`` composes three more sentences
from it ("How to choose: {q}", "{q}: honest iPhone app buying guide", the meta
description), so one translated query removes roughly 340 characters of English
from a page rather than the ~90 the headline itself contributes.

There are ~1,750 distinct queries, which is far too many to hand-translate into
22 locales.  But a quarter of them are formulaic search phrases:

    "<brand> alternative app for iphone"   (108 queries, brand kept verbatim)
    "<topic> app for iphone"               (184 queries)
    "<topic> app for iphone free"          (172 queries)

The brand family needs no vocabulary at all -- the brand is a proper noun that
stays in English in every locale -- so one frame per locale localizes all 108.
The topic families need one short noun phrase per topic per locale, held in
``i18n_query_topics.json``; a topic without a translation is simply skipped.

Queries are what a user actually types, so the frames are written as *search
phrases*, not as polished prose: lowercase where the locale's searchers type
lowercase, and ordered the way that market words the query.

    python3 i18n_query_expand.py [--langs "ja ko"] [--dry-run]
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"
TOPICS_PATH = ROOT / "i18n_query_topics.json"
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

_vspec = importlib.util.spec_from_file_location("_i18n_validate", ROOT / "i18n_batch_apply.py")
_validate_mod = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(_validate_mod)
validate = _validate_mod.validate

# frame name -> {"en": english pattern, locale: localized pattern}
# Slot {x} is a brand for BRAND_FRAMES and a topic phrase everywhere else.
QUERY_FRAMES: dict[str, dict[str, str]] = {
    "alt_app_iphone": {
        "en": "{x} alternative app for iphone",
        "ja": "{x} の代替アプリ(iPhone)",
        "ko": "{x} 대체 앱 (iPhone)",
        "zh-Hant": "{x} 替代 App(iPhone)",
        "zh-Hans": "{x} 替代 App(iPhone)",
        "de-DE": "{x} Alternative App für iPhone",
        "fr-FR": "alternative à {x} pour iPhone",
        "es-ES": "alternativa a {x} para iPhone",
        "pt-BR": "alternativa ao {x} para iPhone",
        "pt-PT": "alternativa ao {x} para iPhone",
        "th": "แอปทางเลือกแทน {x} สำหรับ iPhone",
        "vi": "ứng dụng thay thế {x} cho iPhone",
        "tr": "iPhone için {x} alternatifi uygulama",
        "id": "aplikasi alternatif {x} untuk iPhone",
        "ar-SA": "تطبيق بديل لـ {x} على iPhone",
        "ms": "apl alternatif {x} untuk iPhone",
        "nl-NL": "{x} alternatief voor iPhone",
        "it": "alternativa a {x} per iPhone",
        "ru": "аналог {x} для iPhone",
        "pl": "alternatywa dla {x} na iPhone",
        "uk": "аналог {x} для iPhone",
        "hi": "iPhone के लिए {x} का विकल्प ऐप",
        "sv": "{x} alternativ för iPhone",
    },
    "app_for_iphone": {
        "en": "{x} app for iphone",
        "ja": "{x} アプリ(iPhone)",
        "ko": "{x} 앱 (iPhone)",
        "zh-Hant": "{x} App(iPhone)",
        "zh-Hans": "{x} App(iPhone)",
        "de-DE": "{x} App für iPhone",
        "fr-FR": "app {x} pour iPhone",
        "es-ES": "app de {x} para iPhone",
        "pt-BR": "app de {x} para iPhone",
        "pt-PT": "app de {x} para iPhone",
        "th": "แอป{x}สำหรับ iPhone",
        "vi": "ứng dụng {x} cho iPhone",
        "tr": "iPhone için {x} uygulaması",
        "id": "aplikasi {x} untuk iPhone",
        "ar-SA": "تطبيق {x} لـ iPhone",
        "ms": "apl {x} untuk iPhone",
        "nl-NL": "{x} app voor iPhone",
        "it": "app {x} per iPhone",
        "ru": "приложение {x} для iPhone",
        "pl": "aplikacja {x} na iPhone",
        "uk": "застосунок {x} для iPhone",
        "hi": "iPhone के लिए {x} ऐप",
        "sv": "{x} app för iPhone",
    },
    "app_for_iphone_free": {
        "en": "{x} app for iphone free",
        "ja": "{x} アプリ(iPhone、無料)",
        "ko": "{x} 앱 (iPhone, 무료)",
        "zh-Hant": "{x} App(iPhone,免費)",
        "zh-Hans": "{x} App(iPhone,免费)",
        "de-DE": "{x} App für iPhone kostenlos",
        "fr-FR": "app {x} gratuite pour iPhone",
        "es-ES": "app de {x} gratis para iPhone",
        "pt-BR": "app de {x} grátis para iPhone",
        "pt-PT": "app de {x} grátis para iPhone",
        "th": "แอป{x}สำหรับ iPhone ฟรี",
        "vi": "ứng dụng {x} miễn phí cho iPhone",
        "tr": "iPhone için ücretsiz {x} uygulaması",
        "id": "aplikasi {x} gratis untuk iPhone",
        "ar-SA": "تطبيق {x} مجاني لـ iPhone",
        "ms": "apl {x} percuma untuk iPhone",
        "nl-NL": "{x} app voor iPhone gratis",
        "it": "app {x} gratis per iPhone",
        "ru": "бесплатное приложение {x} для iPhone",
        "pl": "darmowa aplikacja {x} na iPhone",
        "uk": "безкоштовний застосунок {x} для iPhone",
        "hi": "iPhone के लिए मुफ़्त {x} ऐप",
        "sv": "{x} app för iPhone gratis",
    },
}

# Frames whose {x} is a product name: copied through untranslated, because a
# brand is written the same way in every market.
BRAND_FRAMES = {"alt_app_iphone"}


def load_topics() -> dict[str, dict[str, str]]:
    if TOPICS_PATH.exists():
        return json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    return {}


def page_queries() -> set[str]:
    """Every `<h1>` on the English answer pages -- one per page."""
    out: set[str] = set()
    for path in (PAGES / "answers").glob("*.html"):
        if path.name == "index.html":
            continue
        m = re.search(r"<h1\b[^>]*>(.*?)</h1>", path.read_text(encoding="utf-8"), re.S | re.I)
        if m:
            text = html.unescape(re.sub(r"<.*?>", "", m.group(1))).strip()
            if text:
                out.add(text)
    return out


def compile_frames() -> list[tuple[str, re.Pattern[str]]]:
    compiled = []
    for name, per_locale in QUERY_FRAMES.items():
        pattern = re.escape(per_locale["en"]).replace(re.escape("{x}"), "(?P<x>.+?)")
        compiled.append((name, re.compile("^" + pattern + "$")))
    # longest english pattern first, so "... app for iphone free" is matched
    # before the "... app for iphone" prefix swallows it
    compiled.sort(key=lambda item: -len(QUERY_FRAMES[item[0]]["en"]))
    return compiled


def expand(lang: str, queries: set[str], compiled, topics) -> dict[str, str]:
    path = TRANS / f"{lang}.json"
    dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out: dict[str, str] = {}
    for query in queries:
        if query in dictionary:
            continue
        for name, rx in compiled:
            frame = QUERY_FRAMES[name].get(lang)
            if not frame:
                continue
            match = rx.match(query)
            if not match:
                continue
            raw = match.group("x")
            if name in BRAND_FRAMES:
                value = raw
            else:
                value = (topics.get(raw) or {}).get(lang)
                if not value:
                    break
            candidate = frame.format(x=value)
            if validate(query, lang, candidate) is None:
                out[query] = candidate
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", help="space/comma separated locales")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    langs = sorted({l for frame in QUERY_FRAMES.values() for l in frame} - {"en"})
    if args.langs:
        want = {x for x in re.split(r"[\s,]+", args.langs) if x}
        langs = [l for l in langs if l in want]

    queries = page_queries()
    compiled = compile_frames()
    topics = load_topics()
    total = 0
    for lang in langs:
        added = expand(lang, queries, compiled, topics)
        path = TRANS / f"{lang}.json"
        dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        dictionary.update(added)
        total += len(added)
        print(f"[{lang}] composed {len(added)} queries -> dict {len(dictionary)}")
        if not args.dry_run and added:
            path.write_text(json.dumps(dictionary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"queries_composed": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
