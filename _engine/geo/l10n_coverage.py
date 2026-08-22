#!/usr/bin/env python3
"""Measure body-copy localization coverage of the GEO answer pages.

Method
------
For every locale directory under ``pages/<locale>/answers`` we compare each
localized page against its English source ``pages/answers/<slug>.html``.

Both files are run through the *same* string extractor the localizer uses
(``aeo_answers_i18n.extract_strings``), so we are comparing exactly the units
that the translation pipeline is responsible for.

For a localized page:

  untranslated_chars = sum(len(s) for s in localized_strings if s in english_strings)
  coverage           = 1 - untranslated_chars / total_chars

i.e. a visible string that is byte-identical to a string on the English page is
counted as *not* localized.  This works for Latin-script locales (de/fr/es/...)
where a character-class heuristic cannot, and it ignores proper nouns only when
they are the whole string (app names such as "PhotoCream" are legitimately
identical -- they are short, so their weight is small).

A secondary ``native_ratio`` is reported for locales with a distinctive script
(CJK/Korean/Cyrillic/Greek/Arabic/Hebrew/Thai/Devanagari): the share of letters
in the body text that belong to that script.

Usage
-----
    python3 l10n_coverage.py                       # all locales, 120-slug sample
    python3 l10n_coverage.py --langs "ja ko de-DE" --all-slugs
    python3 l10n_coverage.py --json reports/l10n_coverage.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# CI symlinks _engine/geo/pages at the site root; GEO_PAGES overrides it.
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

_spec = importlib.util.spec_from_file_location(
    "_aeo_i18n", ROOT / "aeo_answers_i18n.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
extract_strings = _mod.extract_strings

SCRIPT_RANGES = {
    "han": [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF)],
    "kana": [(0x3040, 0x30FF), (0x31F0, 0x31FF)],
    "hangul": [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)],
    "cyrillic": [(0x0400, 0x04FF)],
    "greek": [(0x0370, 0x03FF)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F)],
    "hebrew": [(0x0590, 0x05FF)],
    "thai": [(0x0E00, 0x0E7F)],
    "devanagari": [(0x0900, 0x097F)],
}

NATIVE_SCRIPTS = {
    "ja": ["han", "kana"],
    "ko": ["hangul"],
    "zh-Hans": ["han"],
    "zh-Hant": ["han"],
    "ru": ["cyrillic"],
    "uk": ["cyrillic"],
    "bg": ["cyrillic"],
    "el": ["greek"],
    "ar-SA": ["arabic"],
    "he": ["hebrew"],
    "th": ["thai"],
    "hi": ["devanagari"],
    "mr": ["devanagari"],
}


def _in_script(ch: str, names: list[str]) -> bool:
    cp = ord(ch)
    for name in names:
        for lo, hi in SCRIPT_RANGES[name]:
            if lo <= cp <= hi:
                return True
    return False


def native_ratio(text: str, lang: str) -> float | None:
    names = NATIVE_SCRIPTS.get(lang)
    if not names:
        return None
    letters = [c for c in text if unicodedata.category(c).startswith("L")]
    if not letters:
        return None
    return sum(1 for c in letters if _in_script(c, names)) / len(letters)


def locale_dirs() -> list[str]:
    out = []
    for p in sorted(PAGES.iterdir()):
        if p.is_dir() and (p / "answers").is_dir() and p.name not in {"answers", "_engine"}:
            out.append(p.name)
    return out


def page_coverage(en_src: str, loc_src: str, lang: str) -> tuple[int, int, float | None]:
    en_strings, _, _ = extract_strings(en_src)
    return page_coverage_from_english_strings(en_strings, loc_src, lang)


def page_coverage_from_english_strings(
    en_strings: list[str],
    loc_src: str,
    lang: str,
) -> tuple[int, int, float | None]:
    loc_strings, _, _ = extract_strings(loc_src)
    en_set = set(en_strings)
    total = 0
    untranslated = 0
    for s in loc_strings:
        n = len(s)
        total += n
        if s in en_set:
            untranslated += n
    return total, untranslated, native_ratio(" ".join(loc_strings), lang)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", help="space/comma separated locales (default: all)")
    ap.add_argument("--sample", type=int, default=120, help="slugs per locale (0 = all)")
    ap.add_argument("--all-slugs", action="store_true", help="shorthand for --sample 0")
    ap.add_argument("--json", help="write the full result table to this path")
    ap.add_argument("--markdown", help="write a markdown table to this path")
    args = ap.parse_args()

    langs = locale_dirs()
    if args.langs:
        want = [x for x in re.split(r"[\s,]+", args.langs) if x]
        langs = [l for l in langs if l in want]

    sample = 0 if args.all_slugs else args.sample

    en_dir = PAGES / "answers"
    en_slugs = sorted(p.stem for p in en_dir.glob("*.html"))
    english_cache: dict[str, list[str]] = {}

    rows = []
    for lang in langs:
        d = PAGES / lang / "answers"
        slugs = sorted(p.stem for p in d.glob("*.html"))
        slugs = [s for s in slugs if (en_dir / f"{s}.html").exists()]
        n_total = len(slugs)
        if sample and n_total > sample:
            step = n_total / sample
            slugs = [slugs[int(i * step)] for i in range(sample)]
        tot = unt = 0
        natives = []
        fully_en = 0
        for s in slugs:
            try:
                if s not in english_cache:
                    en_src = (en_dir / f"{s}.html").read_text(
                        encoding="utf-8"
                    )
                    english_cache[s] = extract_strings(en_src)[0]
                loc_src = (d / f"{s}.html").read_text(encoding="utf-8")
            except OSError:
                continue
            t, u, nr = page_coverage_from_english_strings(
                english_cache[s],
                loc_src,
                lang,
            )
            tot += t
            unt += u
            if nr is not None:
                natives.append(nr)
            if t and u / t > 0.9:
                fully_en += 1
        cov = (1 - unt / tot) if tot else 0.0
        rows.append(
            {
                "locale": lang,
                "pages": n_total,
                "measured": len(slugs),
                "coverage": round(cov * 100, 1),
                "native_ratio": round(sum(natives) / len(natives) * 100, 1) if natives else None,
                "untranslated_pages": fully_en,
            }
        )

    rows.sort(key=lambda r: r["coverage"])
    hdr = f"{'locale':<10} {'pages':>6} {'meas':>5} {'body l10n %':>12} {'native %':>9}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        nat = f"{r['native_ratio']:.1f}" if r["native_ratio"] is not None else "-"
        print(f"{r['locale']:<10} {r['pages']:>6} {r['measured']:>5} {r['coverage']:>12.1f} {nat:>9}")
    if rows:
        avg = sum(r["coverage"] for r in rows) / len(rows)
        print("-" * len(hdr))
        print(f"{'AVG':<10} {'':>6} {'':>5} {avg:>12.1f}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown:
        lines = ["| locale | pages | body l10n % | native script % |", "|---|---:|---:|---:|"]
        for r in rows:
            nat = f"{r['native_ratio']:.1f}" if r["native_ratio"] is not None else "-"
            lines.append(f"| {r['locale']} | {r['pages']} | {r['coverage']:.1f} | {nat} |")
        Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
