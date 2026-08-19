#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Push corrected dictionary entries onto pages that already carry the *old,
wrong* translation.

``i18n_page_patch.py`` deliberately only touches spans that are still English,
so it cannot repair a span whose translation is present but wrong.  A full
``--refresh`` re-render would repair it, but it also throws away every span the
shared dictionary cannot reproduce, which is why it is unsafe on these pages.

This tool takes the narrow middle path: given a list of English strings whose
translation has just been corrected, it finds *exactly those spans* on the
localized page and rewrites them.

Finding them needs alignment, because the wrong translation is usually a
duplicate -- the same canned paragraph was emitted for several different English
answers, so a plain search-and-replace cannot tell the occurrences apart.  The
alignment is dictionary-driven: each English string is mapped through the
*previous* dictionary to the localized string the renderer would have produced,
and ``difflib`` matches that projected sequence against the page's real span
sequence.  Only positions inside a confirmed matching block are rewritten, and
only when the span still holds the exact stale text.

    python3 i18n_align_retranslate.py --locales "es-ES de-DE" \
        --keys corrected_keys.json --old old_values.json [--dry-run]

``--keys``  JSON list of English strings that were corrected.
``--old``   JSON {locale: {english: previous_translation}} so the projection can
            reproduce the page as it was rendered.
"""
from __future__ import annotations

import argparse
import difflib
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

TAG_RX = re.compile(r"<[^>]+>")
ATTR_VAL_RX = re.compile(r'="[^"]*"')
HREF_RX = re.compile(r'(?:href|hreflang|src)="([^"]*)"')

_spec = importlib.util.spec_from_file_location("_aeo_i18n", ROOT / "aeo_answers_i18n.py")
_i18n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_i18n)


def ordered_spans(source: str) -> list[tuple[int, int, str, str]]:
    """Document-ordered, *non-deduplicated* translatable spans.

    ``aeo_answers_i18n.extract_strings`` returns its string list de-duplicated,
    which destroys the positional correspondence this tool depends on -- and the
    duplicates are exactly the problem being fixed here (one canned paragraph
    emitted for several different answers).  So the alignment runs on the raw
    span list instead.
    """
    return sorted(_i18n.extract_strings(source)[1], key=lambda s: s[0])


def json_blocks(source: str) -> list[tuple[int, int, object]]:
    out = []
    for start, end, raw in _i18n.extract_strings(source)[2]:
        try:
            out.append((start, end, json.loads(raw)))
        except json.JSONDecodeError:
            continue
    return out


def retranslate_json(en_obj, loc_obj, old: dict[str, str], new: dict[str, str],
                     targets: set[str], key: str | None = None):
    """Walk the English and localized JSON-LD trees in parallel.

    Structure is identical between the two renders, so the English node tells us
    which source sentence a localized string came from -- something a value-based
    mapping cannot know when the same wrong translation was reused.
    """
    if isinstance(en_obj, dict) and isinstance(loc_obj, dict):
        return {k: (retranslate_json(en_obj.get(k), v, old, new, targets, k)
                    if k in en_obj else v)
                for k, v in loc_obj.items()}
    if isinstance(en_obj, list) and isinstance(loc_obj, list) and len(en_obj) == len(loc_obj):
        return [retranslate_json(a, b, old, new, targets, key)
                for a, b in zip(en_obj, loc_obj)]
    if isinstance(en_obj, str) and isinstance(loc_obj, str):
        if en_obj in targets and en_obj in new and loc_obj == old.get(en_obj):
            return new[en_obj]
    return loc_obj


def align(en_projected: list[str], loc_strings: list[str]) -> dict[int, int]:
    """Map english index -> localized span index for confirmed matches only."""
    matcher = difflib.SequenceMatcher(a=en_projected, b=loc_strings, autojunk=False)
    pairs: dict[int, int] = {}
    for a0, b0, size in matcher.get_matching_blocks():
        for k in range(size):
            pairs[a0 + k] = b0 + k
    return pairs


def patch(en_src: str, loc_src: str, old: dict[str, str], new: dict[str, str],
          targets: set[str]) -> tuple[str, int] | None:
    en_spans = ordered_spans(en_src)
    loc_spans = ordered_spans(loc_src)
    en_seq = [s[2] for s in en_spans]
    loc_seq = [s[2] for s in loc_spans]

    projected = [old.get(s, s) for s in en_seq]
    pairs = align(projected, loc_seq)

    replacements: list[tuple[int, int, str]] = []
    replaced = 0
    for i, en in enumerate(en_seq):
        if en not in targets or en not in new:
            continue
        j = pairs.get(i)
        if j is None:
            continue
        stale = old.get(en)
        if stale is None or loc_seq[j] != stale:
            continue
        start, end, original, kind = loc_spans[j]
        escaped = html.escape(new[en], quote=(kind == "content"))
        if kind == "text":
            raw = loc_src[start:end]
            escaped = (re.match(r"\s*", raw).group(0) + escaped
                       + re.search(r"\s*$", raw).group(0))
        replacements.append((start, end, escaped))
        replaced += 1

    en_json = json_blocks(en_src)
    loc_json = json_blocks(loc_src)
    if len(en_json) == len(loc_json):
        for (_es, _ee, en_obj), (start, end, loc_obj) in zip(en_json, loc_json):
            patched = retranslate_json(en_obj, loc_obj, old, new, targets)
            if patched != loc_obj:
                replacements.append(
                    (start, end, "\n" + json.dumps(patched, ensure_ascii=False, indent=2) + "\n"))
    if not replacements:
        return None

    out = _i18n.replace_spans(loc_src, replacements)
    if ([ATTR_VAL_RX.sub('=""', t) for t in TAG_RX.findall(out)]
            != [ATTR_VAL_RX.sub('=""', t) for t in TAG_RX.findall(loc_src)]):
        raise ValueError("tag sequence changed")
    if sorted(HREF_RX.findall(out)) != sorted(HREF_RX.findall(loc_src)):
        raise ValueError("link targets changed")
    for token in ("href=", "hreflang=", "</head>", "</body>"):
        if out.count(token) != loc_src.count(token):
            raise ValueError(f"{token!r} count changed")
    for _s, _e, raw in _i18n.extract_strings(out)[2]:
        json.loads(raw)
    return out, replaced


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--locales", required=True)
    ap.add_argument("--keys", required=True, help="JSON list of corrected English strings")
    ap.add_argument("--old", required=True, help="JSON {locale: {english: old translation}}")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = set(json.loads(Path(args.keys).read_text(encoding="utf-8")))
    old_all = json.loads(Path(args.old).read_text(encoding="utf-8"))

    total_pages = total_spans = failures = 0
    for locale in [x for x in re.split(r"[\s,]+", args.locales) if x]:
        new = json.loads((TRANS / f"{locale}.json").read_text(encoding="utf-8"))
        old = dict(new)
        old.update({k: v for k, v in old_all.get(locale, {}).items() if v})
        loc_dir = PAGES / locale / "answers"
        if not loc_dir.is_dir():
            continue
        pages = spans = 0
        for loc_path in sorted(loc_dir.glob("*.html")):
            en_path = PAGES / "answers" / loc_path.name
            if not en_path.exists():
                continue
            try:
                result = patch(en_path.read_text(encoding="utf-8"),
                               loc_path.read_text(encoding="utf-8"),
                               old, new, targets)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"  FAIL {locale}/{loc_path.name}: {exc}", file=sys.stderr)
                continue
            if not result:
                continue
            out, replaced = result
            pages += 1
            spans += replaced
            if not args.dry_run:
                loc_path.write_text(out, encoding="utf-8")
        print(f"[{locale}] {pages} pages, {spans} spans rewritten")
        total_pages += pages
        total_spans += spans
    print(f"TOTAL {total_pages} pages, {total_spans} spans, {failures} failed"
          + (" (dry run)" if args.dry_run else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
