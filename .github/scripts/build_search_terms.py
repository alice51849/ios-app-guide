#!/usr/bin/env python3
"""Data-driven App Store search terms for the "Search “X” on the App Store" caption line.

About 95% of our downloads come from App Store search, so the search line in a caption should send people to a
term where the app is about to reach the top 3, not only to its brand name. This builds
.github/growth/search-terms.json from the Growth Engine keyword rank history (00_GrowthEngine
data/rank_watch/history.csv: date, storefront, app, term, rank, results; read by the Mac rank probe) and the
funnel snapshot (reports/funnel-latest.json, which storefronts paid in the last 7 days).

Per app and storefront it keeps one term:
- the term's latest reading is at most FRESH_DAYS older than the newest reading in the file;
- the latest rank is in WINDOW (2-10: past #10 people rarely scroll down to the app, so the caption keeps the
  brand name), the smallest rank wins (closest to the top 3); a term already at #1 is
  only the fallback when no 2-10 term exists; ties go to the term with more results (more competition = more
  searches), then the term text;
- the term is in the storefront's language (script check; a Latin-script non-English storefront skips terms
  the same app also tracks in an English storefront) and passes the post QA claim check (no superlatives,
  no competitor names or claims the app's own store text does not carry);
- the term is not on the exclusion list (.github/growth/search-terms-exclude.json: misspellings people do type
  but a caption should not print); the next qualifying term is used instead.

search_caption.search_term() reads the file; with no entry (or a stale one) the caption keeps the clip's
own search phrase. Only terms the rank probe really tracks and the app really ranks for are written.

    python3 .github/scripts/build_search_terms.py \
        --history ../00_GrowthEngine/data/rank_watch/history.csv \
        --funnel ../00_GrowthEngine/reports/funnel-latest.json
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import post_qa as QA  # noqa: E402

GROWTH = HERE.parent / "growth"
OUT = GROWTH / "search-terms.json"
EXCLUDE = GROWTH / "search-terms-exclude.json"
CLIPS = GROWTH / "clips.json"
ENGINE = HERE.parents[2] / "00_GrowthEngine"
SCHEMA = "lumi.search-terms/v1"

# Storefront -> the caption locale used there (same table as 00_GrowthEngine shorts/scripts/striking_distance.py).
LOCALE = {"US": "en", "GB": "en", "CA": "en", "JP": "ja", "TW": "zh-Hant", "KR": "ko", "DE": "de", "FR": "fr",
          "BR": "pt-BR", "CN": "zh-Hans", "TH": "th", "VN": "vi", "RU": "ru"}
# Relative App Store spend per storefront (only the order matters): picks the storefront when one locale
# serves several (en: US, GB, CA) and the clip's own store link does not name one.
MARKET_WEIGHT = {"US": 1.0, "JP": 0.6, "GB": 0.45, "CN": 0.45, "DE": 0.4, "KR": 0.3, "FR": 0.3, "TW": 0.3,
                 "CA": 0.25, "BR": 0.2, "RU": 0.1, "TH": 0.1, "VN": 0.08}
ENGLISH_STOREFRONTS = {"US", "GB", "CA"}
WINDOW = (2, 10)
FRESH_DAYS = 7


def read_history(path):
    """{(app, storefront, term): (date, rank or None, results or None)} - the latest reading of each term."""
    out = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            day = (row.get("date") or "")[:10]
            key = (row.get("app") or "", (row.get("storefront") or "").upper(), (row.get("term") or "").strip())
            if not day or not all(key):
                continue
            if key in out and out[key][0] >= day:
                continue
            rank, results = (row.get("rank") or "").strip(), (row.get("results") or "").strip()
            out[key] = (day, int(rank) if rank.isdigit() else None, int(results) if results.isdigit() else None)
    return out


def paid_storefronts(funnel):
    """{app: {storefronts with paid units in the last 7 days}}."""
    out = {}
    for row in (funnel or {}).get("apps") or []:
        if isinstance(row, dict) and isinstance(row.get("app_key"), str):
            out[row["app_key"]] = {str(m.get("country", "")).upper() for m in row.get("top_paid_markets_7d") or []
                                   if isinstance(m, dict) and (m.get("paid_units_7d") or 0) > 0}
    return out


def store_facts(clips):
    """{app: the app's own store text (names, keylines, keywords, search phrases)} for the claim check."""
    out = {}
    for clip in (clips or {}).get("clips", {}).values():
        app = str(clip.get("app", ""))
        app = app[:-2] if app.endswith("_b") else app
        parts = [clip.get("name", ""), clip.get("keyline", ""), clip.get("search", ""), *(clip.get("keywords") or [])]
        out.setdefault(app, []).extend(p for p in parts if isinstance(p, str) and p)
    return {app: "\n".join(parts) for app, parts in out.items()}


def in_language(term, storefront, english_terms=()):
    """True when the term is written in the storefront's language (by script)."""
    locale = LOCALE.get(storefront)
    if not locale:
        return False
    han, kana, hangul = QA.HAN.search(term), QA.KANA.search(term), QA.HANGUL.search(term)
    if locale == "ja":
        return bool(kana or han) and not hangul
    if locale == "ko":
        return bool(hangul) and not kana
    if locale == "zh-Hant":
        return bool(han) and not kana and not hangul and not any(ch in QA.SIMPLIFIED for ch in term)
    if locale == "zh-Hans":
        return bool(han) and not kana and not hangul
    lang = locale.split("-")[0]
    if lang in QA.SCRIPT:
        return bool(QA.SCRIPT[lang].search(term))
    if han or kana or hangul or any(rx.search(term) for rx in QA.SCRIPT.values()):
        return False
    if not any(ch.isalpha() for ch in term):
        return False
    return lang == "en" or term.casefold() not in english_terms


def competitor(term, facts=""):
    """A competitor name in any letter case (people type "chatgpt") that the app's own store text does not name."""
    low, facts_low = term.casefold(), (facts or "").casefold()
    return any(QA.re.search(r"(?<!\w)" + QA.re.escape(c.casefold()) + r"(?!\w)", low) and c.casefold() not in facts_low
               for c in QA.COMPETITORS)


def excluded_terms(data):
    """{(app, storefront, term casefolded)} from the exclusion file; app / storefront "*" = any."""
    out = set()
    for row in (data or {}).get("terms") or []:
        if isinstance(row, dict) and str(row.get("term") or "").strip():
            out.add((str(row.get("app") or "*"), str(row.get("storefront") or "*").upper(),
                     str(row["term"]).strip().casefold()))
    return out


def is_excluded(app, storefront, term, exclude):
    t = term.casefold()
    return any((a, sf, t) in exclude for a in (app, "*") for sf in (storefront, "*"))


def build(history, funnel=None, clips=None, exclude=None):
    readings = history
    if not readings:
        return {"schema": SCHEMA, "as_of": None, "window": list(WINDOW), "apps": {}}
    newest = max(day for day, _, _ in readings.values())
    cutoff = (dt.date.fromisoformat(newest) - dt.timedelta(days=FRESH_DAYS)).isoformat()
    paid, facts = paid_storefronts(funnel), store_facts(clips)
    english = {}
    for (app, storefront, term) in readings:
        if storefront in ENGLISH_STOREFRONTS:
            english.setdefault(app, set()).add(term.casefold())
    best = {}
    for (app, storefront, term), (day, rank, results) in readings.items():
        if day < cutoff or rank is None or rank > WINDOW[1] or rank < 1 or storefront not in LOCALE:
            continue
        if is_excluded(app, storefront, term, exclude or set()):
            continue
        if not in_language(term, storefront, english.get(app, set())):
            continue
        if QA.claim_problems(term, facts=facts.get(app, "")) or competitor(term, facts.get(app, "")):
            continue
        # rank 2-10 first (smallest wins), a #1 term only when nothing in the window is left
        sort_key = (rank < WINDOW[0], rank, -(results or 0), term)
        current = best.get((app, storefront))
        if current is None or sort_key < current[0]:
            best[(app, storefront)] = (sort_key, {"term": term, "rank": rank, "results": results, "date": day})
    apps = {}
    for (app, storefront), (_, entry) in sorted(best.items()):
        apps.setdefault(app, {})[storefront] = dict(entry, locale=LOCALE[storefront],
                                                    paid=storefront in paid.get(app, set()),
                                                    weight=MARKET_WEIGHT.get(storefront, 0.05))
    return {"schema": SCHEMA, "as_of": newest, "window": list(WINDOW), "fresh_days": FRESH_DAYS,
            "source": "00_GrowthEngine data/rank_watch/history.csv + reports/funnel-latest.json", "apps": apps}


def _load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--history", default=str(ENGINE / "data" / "rank_watch" / "history.csv"))
    ap.add_argument("--funnel", default=str(ENGINE / "reports" / "funnel-latest.json"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    if not Path(args.history).is_file():
        print(f"::error::rank history not found: {args.history}")
        return 1
    data = build(read_history(args.history), _load(args.funnel), _load(CLIPS), excluded_terms(_load(EXCLUDE)))
    if not data["apps"]:
        print("::error::no ranked term in the history: search-terms.json left as it is")
        return 1
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    pairs = sum(len(v) for v in data["apps"].values())
    print(f"search terms: {len(data['apps'])} apps, {pairs} app/storefront pairs, as of {data['as_of']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
