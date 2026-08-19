#!/usr/bin/env python3
"""Make the site chrome read the same on every page of a locale.

The header of an answer page carries five fixed links -- the site name, Answers,
Free tools, Alternatives and About.  Because the localized pages were produced by
several generations of the translation pipeline, one locale can end up with three
different renderings of its own site name ("Sprievodca aplikáciami pre iOS",
"Sprievodca aplikáciami iOS", "Sprievodca iOS aplikáciami" all appear in sk), which
reads as sloppy and weakens the brand.

Unlike ``i18n_page_patch.py`` this pass *does* overwrite existing translations --
but only inside these five anchors, only when the shared dictionary has a
translation for the link's English label, and only in locales the caller names.
The link is identified by its href, so a label can never be moved onto the wrong
destination.

    python3 i18n_chrome_normalize.py --langs "cs sk" [--dry-run]
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
HEADER_RX = re.compile(r"<header\b[^>]*>.*?</header>", re.S | re.I)
LINK_RX = re.compile(r'(<a\b[^>]*href="([^"]+)"[^>]*>)(.*?)(</a>)', re.S | re.I)
JSONLD_RX = re.compile(
    r'(<script\b[^>]*application/ld\+json[^>]*>)(.*?)(</script>)', re.S | re.I
)

# href suffix -> English label. Longest suffix first: "/answers/index.html" has to
# win over the bare "/index.html" that identifies the locale home page.
CHROME = [
    ("/answers/index.html", "Answers"),
    ("/alternatives/", "Alternatives"),
    ("/about.html", "About"),
    ("/tools/", "Free tools"),
    ("/index.html", "iOS App Guide"),
]


def english_label(href: str) -> str | None:
    for suffix, label in CHROME:
        if href.endswith(suffix):
            return label
    return None


def _rename_site(obj, site_name: str) -> int:
    """Rewrite the site name where JSON-LD states it: the WebSite node and the
    first crumb of the breadcrumb trail.  Both are the site itself, so they must
    match the header link rather than whichever wording a past run produced."""
    changed = 0
    if isinstance(obj, list):
        return sum(_rename_site(x, site_name) for x in obj)
    if not isinstance(obj, dict):
        return 0
    types = obj.get("@type")
    types = types if isinstance(types, list) else [types]
    if "WebSite" in types and obj.get("name") not in (None, site_name):
        obj["name"] = site_name
        changed += 1
    if "BreadcrumbList" in types:
        for item in obj.get("itemListElement") or []:
            if isinstance(item, dict) and item.get("position") == 1:
                if item.get("name") not in (None, site_name):
                    item["name"] = site_name
                    changed += 1
    for value in obj.values():
        changed += _rename_site(value, site_name)
    return changed


def normalize(source: str, dictionary: dict[str, str]) -> tuple[str, int] | None:
    m = HEADER_RX.search(source)
    if not m:
        return None
    header = m.group(0)
    changed = 0

    def repl(link: re.Match[str]) -> str:
        nonlocal changed
        open_tag, href, inner, close = link.groups()
        if TAG_RX.search(inner):  # never touch a link that wraps markup
            return link.group(0)
        label = english_label(href)
        if not label:
            return link.group(0)
        target = dictionary.get(label)
        if not target:
            return link.group(0)
        escaped = html.escape(target)
        if escaped == inner:
            return link.group(0)
        changed += 1
        return f"{open_tag}{escaped}{close}"

    new_header = LINK_RX.sub(repl, header)
    out = source[: m.start()] + new_header + source[m.end() :]

    site_name = dictionary.get("iOS App Guide")
    if site_name:

        def ld_repl(block: re.Match[str]) -> str:
            nonlocal changed
            open_tag, raw, close = block.groups()
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                return block.group(0)
            hits = _rename_site(obj, site_name)
            if not hits:
                return block.group(0)
            changed += hits
            return open_tag + "\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n" + close

        out = JSONLD_RX.sub(ld_repl, out)

    if not changed:
        return None
    if TAG_RX.findall(out) != TAG_RX.findall(source):
        raise ValueError("tag sequence changed")
    for token in ("href=", "hreflang=", "</head>", "</body>"):
        if out.count(token) != source.count(token):
            raise ValueError(f"{token!r} count changed")
    for _open, raw, _close in JSONLD_RX.findall(out):
        json.loads(raw)  # raises on malformed JSON-LD
    return out, changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", required=True, help="space/comma separated locales")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total = 0
    for lang in [x for x in re.split(r"[\s,]+", args.langs) if x]:
        path = TRANS / f"{lang}.json"
        dictionary = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        loc_dir = PAGES / lang / "answers"
        if not loc_dir.is_dir():
            print(f"[{lang}] no answers directory", file=sys.stderr)
            continue
        pages = links = 0
        for p in sorted(loc_dir.glob("*.html")):
            source = p.read_text(encoding="utf-8")
            try:
                result = normalize(source, dictionary)
            except Exception as exc:  # noqa: BLE001
                print(f"  FAIL {lang}/{p.name}: {exc}", file=sys.stderr)
                continue
            if result is None:
                continue
            out, changed = result
            pages += 1
            links += changed
            if not args.dry_run:
                p.write_text(out, encoding="utf-8")
        total += links
        print(f"[{lang}] normalized {links} chrome links on {pages} pages")
    print(json.dumps({"links_normalized": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
