#!/usr/bin/env python3
"""Replace the *leftover English* strings of an already-published localized
answer page, in place, without touching anything that is already translated.

Why this exists
---------------
``aeo_answers_i18n.py --refresh`` re-renders a localized page from the current
English source plus the current dictionary.  That is the right tool when the
shared dictionary is richer than the page.  It is the wrong tool for the thin
locales: their pages were localized months ago by a back-end whose output was
never written back to ``geo/i18n_trans`` (``i18n_harvest_existing.py`` cannot
recover it either -- the English source has gained sections since, so the span
counts no longer line up).  Re-rendering such a page would *throw away* the
translation baked into the HTML and replace it with English wherever the shared
dictionary is still empty, which is why ``--refresh`` correctly refuses to run
on them.

This pass works the other way round: it keeps the published page exactly as it
is and only rewrites the spans that are *still English*, i.e. spans whose text
appears verbatim on the English source page.  A span that already carries a
translation is never considered, so the page can only ever gain localization.

Guards (a page is written only if all of them hold)
--------------------------------------------------
  * the tag sequence is byte-identical before and after -- only text nodes,
    meta ``content`` attributes and JSON-LD string values may change
  * the number of ``href=``/``hreflang=`` occurrences is unchanged
  * ``</head>`` and ``</body>`` are still present
  * every JSON-LD block still parses
  * the share of visible characters that is still English strictly decreases

    python3 i18n_page_patch.py --langs "he no da" [--dry-run] [--json report.json]
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

_spec = importlib.util.spec_from_file_location("_aeo_i18n", ROOT / "aeo_answers_i18n.py")
_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_i18n)

TAG_RX = re.compile(r"<[^>]+>")


def _english_mass(strings: list[str], english: set[str]) -> tuple[int, int]:
    total = sum(len(s) for s in strings)
    same = sum(len(s) for s in strings if s in english)
    return total, same


def patch_page(en_src: str, loc_src: str, dictionary: dict[str, str], lang: str) -> tuple[str, int, float, float] | None:
    """Return (new_html, replaced_spans, before_english_share, after_english_share)."""
    english = set(_i18n.extract_strings(en_src)[0])
    strings, spans, json_spans = _i18n.extract_strings(loc_src)

    # Only strings that are still English *and* have a translation are eligible.
    candidates = {s: dictionary[s] for s in strings if s in english and s in dictionary}
    candidates = _i18n.apply_locale_text_overrides(candidates, lang)
    mapping = {k: v for k, v in candidates.items() if v and v.strip() and v.strip() != k.strip()}
    if not mapping:
        return None

    replacements: list[tuple[int, int, str]] = []
    replaced = 0
    for start, end, original, kind in spans:
        if original not in mapping:
            continue
        escaped = html.escape(mapping[original], quote=(kind == "content"))
        if kind == "text":
            raw = loc_src[start:end]
            leading = re.match(r"\s*", raw).group(0)
            trailing = re.search(r"\s*$", raw).group(0)
            escaped = f"{leading}{escaped}{trailing}"
        replacements.append((start, end, escaped))
        replaced += 1

    for start, end, raw in json_spans:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        patched = _i18n.apply_json_mapping(obj, mapping)
        if patched == obj:
            continue
        replacements.append((start, end, "\n" + json.dumps(patched, ensure_ascii=False, indent=2) + "\n"))

    if not replacements:
        return None

    out = _i18n.replace_spans(loc_src, replacements)

    # --- guards -----------------------------------------------------------
    if TAG_RX.findall(out) != TAG_RX.findall(loc_src):
        raise ValueError("tag sequence changed")
    for token in ("href=", "hreflang=", "</head>", "</body>"):
        if out.count(token) != loc_src.count(token):
            raise ValueError(f"{token!r} count changed")
    new_strings, _, new_json = _i18n.extract_strings(out)
    for _s, _e, raw in new_json:
        json.loads(raw)  # raises on malformed JSON-LD

    tot_b, same_b = _english_mass(strings, english)
    tot_a, same_a = _english_mass(new_strings, english)
    before = same_b / tot_b if tot_b else 0.0
    after = same_a / tot_a if tot_a else 0.0
    if after >= before:
        raise ValueError(f"no gain ({before:.3f} -> {after:.3f})")
    return out, replaced, before, after


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", required=True, help="space/comma separated locales")
    ap.add_argument("--slugs", help="optional space/comma separated slugs")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", help="write a per-locale summary here")
    args = ap.parse_args()

    langs = [x for x in re.split(r"[\s,]+", args.langs) if x]
    only = {Path(x).stem for x in re.split(r"[\s,]+", args.slugs) if x} if args.slugs else None

    en_dir = PAGES / "answers"
    report = []
    for lang in langs:
        path = TRANS / f"{lang}.json"
        dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        loc_dir = PAGES / lang / "answers"
        if not loc_dir.is_dir():
            print(f"[{lang}] no answers directory", file=sys.stderr)
            continue
        patched = skipped = failed = 0
        before_sum = after_sum = 0.0
        pages = 0
        for loc_path in sorted(loc_dir.glob("*.html")):
            if loc_path.name == "index.html":
                continue
            if only and loc_path.stem not in only:
                continue
            en_path = en_dir / loc_path.name
            if not en_path.exists():
                continue
            pages += 1
            try:
                result = patch_page(
                    en_path.read_text(encoding="utf-8"),
                    loc_path.read_text(encoding="utf-8"),
                    dictionary,
                    lang,
                )
            except Exception as exc:  # noqa: BLE001 - report and keep the old page
                failed += 1
                print(f"  FAIL {lang}/{loc_path.name}: {exc}", file=sys.stderr)
                continue
            if result is None:
                skipped += 1
                continue
            out, replaced, before, after = result
            before_sum += before
            after_sum += after
            patched += 1
            if not args.dry_run:
                loc_path.write_text(out, encoding="utf-8")
        row = {
            "locale": lang,
            "pages": pages,
            "patched": patched,
            "skipped": skipped,
            "failed": failed,
            "english_share_before": round(before_sum / patched * 100, 1) if patched else None,
            "english_share_after": round(after_sum / patched * 100, 1) if patched else None,
        }
        report.append(row)
        print(
            f"[{lang}] patched {patched}/{pages} pages, skipped {skipped}, failed {failed}"
            + (
                f", English body {row['english_share_before']}% -> {row['english_share_after']}%"
                if patched
                else ""
            )
        )
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
