#!/usr/bin/env python3
"""Mine already-published localized answer pages for translations the shared
dictionaries in ``geo/i18n_trans`` are still missing.

Why this exists
---------------
Localized pages were generated over many months by several different back-ends.
Whatever those runs translated is baked into the HTML and then forgotten -- the
shared dictionary never learned it, so the *next* page starts from scratch and
falls back to English.  That is a large part of why body-copy localization has
been stuck around 25-40%.

How it works
------------
``extract_strings`` returns spans in document order, and a localized page is a
span-for-span rewrite of its English source.  So when the two pages yield the
same number of spans, span *i* of the localized page is by construction the
translation of span *i* of the English page.  Pages whose span counts disagree
(the English page was regenerated with a new section since) are skipped
entirely rather than guessed at.

Candidates are then majority-voted across every page that contains the string,
validated (script, zh-Hans orthography, English-fallback) and only *added* --
an existing dictionary entry is never overwritten.

    python3 i18n_harvest_existing.py --langs "ja ko de-DE" [--dry-run]
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# CI symlinks _engine/geo/pages at the site root; GEO_PAGES overrides it.
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()
TRANS = ROOT / "i18n_trans"

_spec = importlib.util.spec_from_file_location("_aeo_i18n", ROOT / "aeo_answers_i18n.py")
_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_i18n)

_vspec = importlib.util.spec_from_file_location("_i18n_validate", ROOT / "i18n_batch_apply.py")
_validate_mod = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(_validate_mod)
validate = _validate_mod.validate

MIN_LEN = 8          # ignore punctuation and single glyphs
MIN_VOTES_RATIO = 0.6  # winning translation must be the clear majority
LEN_RATIO = (0.25, 3.0)  # plausible translated/source length band


def page_link_labels() -> set[str]:
    """Every answer page's <h1>/title text.

    These strings also appear as *link labels* inside the "related answers"
    blocks, and those blocks are curated per locale -- the localized page can
    link to a different set of pages than the English one, so a positional pair
    there is not a translation, it is a different question. Excluding them is
    what keeps harvesting honest.
    """
    labels: set[str] = set()
    for path in (PAGES / "answers").glob("*.html"):
        if path.name == "index.html":
            continue
        html = path.read_text(encoding="utf-8")
        for match in re.finditer(r"<h1[^>]*>(.*?)</h1>|<title>(.*?)</title>", html, flags=re.S | re.I):
            text = re.sub(r"<[^>]+>", "", match.group(1) or match.group(2) or "").strip()
            if text:
                labels.add(text)
    return labels


NON_LATIN = {
    "ja", "ko", "zh-Hans", "zh-Hant", "ru", "uk", "bg", "el", "ar-SA", "he",
    "th", "hi", "mr-IN", "bn-BD", "ta-IN", "te-IN", "kn-IN", "ml-IN", "gu-IN",
    "pa-IN", "or-IN", "ur-PK",
}


def _looks_like_untranslated_english(source: str, target: str, lang: str) -> bool:
    """Catch a pair that is really two *different* English strings."""
    if lang not in NON_LATIN:
        return False
    return not re.search(r"[^\x00-\x7F]", target)


def locale_dirs() -> list[str]:
    return sorted(
        p.name
        for p in PAGES.iterdir()
        if p.is_dir() and (p / "answers").is_dir() and p.name not in {"answers", "_engine"}
    )


def harvest(lang: str, verbose: bool = False, link_labels: set[str] | None = None) -> dict[str, str]:
    link_labels = page_link_labels() if link_labels is None else link_labels
    en_dir = PAGES / "answers"
    loc_dir = PAGES / lang / "answers"
    votes: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    aligned = skipped = 0
    for loc_path in sorted(loc_dir.glob("*.html")):
        if loc_path.name == "index.html":
            continue
        en_path = en_dir / loc_path.name
        if not en_path.exists():
            continue
        try:
            _, en_spans, _ = _i18n.extract_strings(en_path.read_text(encoding="utf-8"))
            _, loc_spans, _ = _i18n.extract_strings(loc_path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if len(en_spans) != len(loc_spans):
            skipped += 1
            continue
        aligned += 1
        for en_span, loc_span in zip(en_spans, loc_spans):
            # meta/og attributes are rewritten by ensure_locale_meta with a
            # per-locale frame, so they are never a translation of the English
            # attribute -- only body text spans can be paired.
            if en_span[3] != "text" or loc_span[3] != "text":
                continue
            source = en_span[2].strip()
            target = loc_span[2].strip()
            if len(source) < MIN_LEN or not target or target == source:
                continue
            if source in link_labels or target in link_labels:
                continue
            ratio = len(target) / len(source)
            if not (LEN_RATIO[0] <= ratio <= LEN_RATIO[1]):
                continue
            votes[source][target] += 1
    if verbose:
        print(f"[{lang}] aligned {aligned} pages, skipped {skipped} (span mismatch)")

    harvested: dict[str, str] = {}
    for source, counter in votes.items():
        target, n = counter.most_common(1)[0]
        if n / sum(counter.values()) < MIN_VOTES_RATIO:
            continue
        if _looks_like_untranslated_english(source, target, lang):
            continue
        if validate(source, lang, target) is None:
            harvested[source] = target
    return harvested


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", help="space/comma separated locales (default: all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    langs = locale_dirs()
    if args.langs:
        want = {x for x in re.split(r"[\s,]+", args.langs) if x}
        langs = [l for l in langs if l in want]

    labels = page_link_labels()
    grand = 0
    for lang in langs:
        if lang in _i18n.ENGLISH_LOCALES:
            continue
        found = harvest(lang, verbose=True, link_labels=labels)
        path = TRANS / f"{lang}.json"
        current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        added = {k: v for k, v in found.items() if k not in current}
        current.update(added)
        grand += len(added)
        print(f"[{lang}] harvested {len(found)} usable, +{len(added)} new -> dict {len(current)}")
        if not args.dry_run and added:
            path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"new_entries": grand}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
