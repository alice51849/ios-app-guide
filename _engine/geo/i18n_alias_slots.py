#!/usr/bin/env python3
"""Reuse an existing translation for a *truncated or duplicated* copy of it.

The rendered answer pages contain a handful of slot values that are damaged
variants of a string we already translate properly: an app tagline that was cut
off mid-word by an upstream length limit, or one whose tail got repeated
("...signal checks.ignal checks."). Translating those by hand again is pure
waste and invites drift.

The rule here is deliberately narrow, so it can never map two *different*
products onto each other: a variant is only aliased to a canonical entry when,
after whitespace normalisation, the canonical text is contained in the variant
or the variant is a prefix of the canonical text. Anything looser (fuzzy ratios)
would happily confuse "Aim990" with "Aim990 Plus", or TripBee Lite with Pro.

    python3 i18n_alias_slots.py --langs "th vi tr id pt-PT ar-SA ja ko" [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"
PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "pages")).resolve()

_spec = importlib.util.spec_from_file_location("_pattern_expand", ROOT / "i18n_pattern_expand.py")
_pe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pe)

MIN_LEN = 40  # short labels are far too easy to confuse


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def slot_values() -> set[str]:
    """Every {sub} value the frames can see on the English pages."""
    out: set[str] = set()
    compiled = _pe.compile_frames()
    for source in _pe.english_strings():
        for _name, rx in compiled:
            match = rx.match(source)
            if not match:
                continue
            value = match.groupdict().get("sub")
            if value:
                out.add(value)
            break
    return out


def alias(lang: str, values: set[str]) -> dict[str, str]:
    path = TRANS / f"{lang}.json"
    dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    canonical = {_norm(k): k for k in dictionary if len(k) >= MIN_LEN}
    out: dict[str, str] = {}
    for value in values:
        if value in dictionary or len(value) < MIN_LEN:
            continue
        norm = _norm(value)
        best = None
        for cnorm, key in canonical.items():
            if cnorm in norm or norm.startswith(cnorm) or cnorm.startswith(norm):
                if best is None or len(cnorm) > len(_norm(best)):
                    best = key
        if best:
            out[value] = dictionary[best]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", required=True, help="space/comma separated locales")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    langs = [x for x in re.split(r"[\s,]+", args.langs) if x]
    values = slot_values()
    total = 0
    for lang in langs:
        added = alias(lang, values)
        path = TRANS / f"{lang}.json"
        dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        dictionary.update(added)
        total += len(added)
        print(f"[{lang}] aliased {len(added)} damaged slot values -> dict {len(dictionary)}")
        if added and not args.dry_run:
            path.write_text(json.dumps(dictionary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aliased": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
