#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Close the off-page GEO/AEO gap: give every content page a real App Store path.

Large parts of the site (vs/ comparison pages, workflow/ how-to pages, topic hubs
and section indexes) were generated without a single ``apps.apple.com`` link and
without app-entity structured data.  Generative engines could read the page but had
no canonical entity to cite, and human readers had no way to reach the product page.

This is an *idempotent post-processor*: it runs after the page generators, never
edits a generator, and rewrites only its own marked block.  It never invents a link
— an app is only linked when it is confirmed live on the App Store, and the CTA
label is harvested from copy the site already ships in that exact locale, so no
machine translation is introduced.

    python geo/gen_store_reach.py               # inject / refresh
    python geo/gen_store_reach.py --check       # report only, non-zero if work pending
    python geo/gen_store_reach.py --refresh-labels
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import os
from pathlib import Path
import re
import sys
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402
from app_pairs import (  # noqa: E402
    free_to_paid, paid_name_re, paid_slug_re, paid_to_free,
    strip_paid_nav_anchors,
)

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
LABELS_CACHE = HERE / "reports" / "store_reach_labels.json"

BLOCK_START = "<!-- store-reach:start -->"
BLOCK_END = "<!-- store-reach:end -->"
BLOCK_RE = re.compile(
    rf"\s*{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\s*", flags=re.DOTALL
)
APPLE_RE = re.compile(r"apps\.apple\.com")
NOINDEX_RE = re.compile(r'<meta[^>]+name="robots"[^>]*content="[^"]*noindex', re.I)
FREE_FIRST = '<meta name="iag-free-resource-first" content="true">'
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
LOCAL_HREF_RE = re.compile(r'href="([^"#?]+\.html)"')
DL_LABEL_RE = re.compile(
    r'<a[^>]+href="https://apps\.apple\.com/[^"]*"[^>]*class="dl"[^>]*>([^<]{1,80})</a>'
)
ANY_LABEL_RE = re.compile(
    r'<a[^>]+href="https://apps\.apple\.com/[^"]*"[^>]*>([^<]{1,80})</a>'
)
LABEL_SOURCE_SECTIONS = ("best-for", "reviews", "seasonal", "tutorials", "persona")
FALLBACK_LABEL = "Download on the App Store →"

STYLE_START = "<!-- store-reach-style:start -->"
STYLE_END = "<!-- store-reach-style:end -->"
STYLE_RE = re.compile(
    rf"\s*{re.escape(STYLE_START)}.*?{re.escape(STYLE_END)}\s*", flags=re.DOTALL
)
STYLE = (
    "<style>.store-reach{margin:2rem 0 0;padding-top:1rem;border-top:1px solid #e5e7eb}"
    ".store-reach h2{font-size:1rem;margin:0 0 .6rem}"
    ".store-reach a.dl{display:inline-block;background:#007aff;color:#fff;padding:.55rem 1.1rem;"
    "border-radius:8px;text-decoration:none;font-weight:600;font-size:.9rem;margin:.3rem .4rem .3rem 0}"
    ".store-reach ul{margin:.6rem 0 0;padding-left:1.2rem}"
    ".store-reach li{font-size:.9rem;margin:.25rem 0}</style>"
)

MAX_APPS_CONTENT = 6
MAX_APPS_HUB = 8
MAX_RELATED = 5


def _sorted_names(keys):
    """Registry display names, longest first so 'Snapport Lite' beats 'Snapport'."""
    pairs = [(APPS[k]["name"], k) for k in keys if APPS.get(k, {}).get("name")]
    return sorted(pairs, key=lambda pair: (-len(pair[0]), pair[0]))


def store_url(key: str) -> str:
    return f"https://apps.apple.com/app/id{APPSTORE[key]}"


def page_url(rel: str) -> str:
    return f"{SITE}/{rel}"


def locale_of(rel: str) -> str:
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else ""


# --------------------------------------------------------------------------- labels
def harvest_labels(pages: Path) -> dict[str, str]:
    """Per-locale 'Download on the App Store' wording, taken from shipped pages."""
    per: dict[str, Counter] = {}
    for child in sorted(pages.iterdir()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        counter: Counter = Counter()
        for section in LABEL_SOURCE_SECTIONS:
            directory = child / section
            if not directory.is_dir():
                continue
            for path in directory.glob("*.html"):
                text = path.read_text(encoding="utf-8", errors="ignore")
                for match in DL_LABEL_RE.finditer(text):
                    counter[match.group(1).strip()] += 1
                if not counter:
                    for match in ANY_LABEL_RE.finditer(text):
                        label = match.group(1).strip()
                        if 3 <= len(label) <= 60:
                            counter[label] += 1
            if counter:
                break
        if counter:
            per[child.name] = counter
    return {loc: c.most_common(1)[0][0] for loc, c in per.items()}


def load_labels(pages: Path, refresh: bool) -> dict[str, str]:
    if not refresh and LABELS_CACHE.is_file():
        return json.loads(LABELS_CACHE.read_text(encoding="utf-8"))
    labels = harvest_labels(pages)
    if not labels:
        raise RuntimeError("store-reach could not harvest any localized CTA label")
    LABELS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LABELS_CACHE.write_text(
        json.dumps(labels, ensure_ascii=False, sort_keys=True, indent=0),
        encoding="utf-8",
    )
    return labels


# --------------------------------------------------------------------------- block
def build_block(
    rel: str,
    app_keys: list[str],
    label: str,
    related: list[tuple[str, str]],
    heading: str,
) -> str:
    ctas = "".join(
        '<a class="dl" href="{url}" rel="noopener">{name} · {label}</a>'.format(
            url=store_url(key),
            name=htmllib.escape(APPS[key]["name"]),
            label=htmllib.escape(label),
        )
        for key in app_keys
    )
    links = ""
    if related:
        links = (
            "<ul>"
            + "".join(
                '<li><a href="{href}">{title}</a></li>'.format(
                    href=htmllib.escape(href), title=htmllib.escape(title)
                )
                for href, title in related
            )
            + "</ul>"
        )
    nodes = [
        {
            "@type": "MobileApplication",
            "name": APPS[key]["name"],
            "operatingSystem": "iOS",
            "applicationCategory": "MobileApplication",
            "url": store_url(key),
            "installUrl": store_url(key),
            "sameAs": store_url(key),
        }
        for key in app_keys
    ]
    if len(nodes) == 1:
        data = {"@context": "https://schema.org", **nodes[0]}
    else:
        data = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "item": node}
                for i, node in enumerate(nodes)
            ],
        }
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        f"{BLOCK_START}"
        f'<section class="store-reach">'
        f"<h2>{htmllib.escape(heading)}</h2>{ctas}{links}</section>"
        f'<script type="application/ld+json">{data_json}</script>'
        f"{BLOCK_END}"
    )


# ``str.lower()`` is *not* length preserving.  Turkish ``İ`` (U+0130) lowercases to
# two code points (``i`` + combining dot above), so every ``İ`` before a tag pushes
# that tag one position further in a lowercased copy of the page.  Using such an
# offset to slice the *original* string cuts closing tags in half — which is exactly
# how ``tr/`` and ``crh/`` pages ended up with ``<<!-- store-reach-style:start -->``
# … ``/head>`` and ``</`` … ``body>`` (2026-08-18).  Match case-insensitively with a
# regex instead: match offsets always live in the original string's index space.
HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)

#: Closing tags this post-processor writes next to, and therefore can damage.
STRUCTURAL_CLOSE_TAGS = ("</head>", "</body>", "</html>")
_SPLIT_CLOSE_TAG_RES = tuple(
    (re.compile(re.escape(tag[:cut]) + r"\s+" + re.escape(tag[cut:]), re.IGNORECASE), tag)
    for tag in STRUCTURAL_CLOSE_TAGS
    for cut in range(1, len(tag))
)
_STRAY_LT_RE = re.compile(r"<(?=</(?:head|body|html)>)", re.IGNORECASE)
_INJECTED_SRC = (
    rf"(?:{re.escape(STYLE_START)}.*?{re.escape(STYLE_END)}"
    rf"|{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)})"
)
_SPLIT_TAG_AROUND_BLOCK_RES = tuple(
    (
        re.compile(
            re.escape(tag[:cut]) + r"\s*(" + _INJECTED_SRC + r")\s*" + re.escape(tag[cut:]),
            re.IGNORECASE | re.DOTALL,
        ),
        tag,
    )
    for tag in STRUCTURAL_CLOSE_TAGS
    for cut in range(1, len(tag))
)


def _last_index(pattern: re.Pattern[str], text: str) -> int:
    """``rfind`` for a case-insensitive literal, in ``text``'s own index space."""
    start = -1
    for match in pattern.finditer(text):
        start = match.start()
    return start


def repair_injected_markup(text: str) -> str:
    """Heal closing tags a previous (buggy) run of this script sliced apart.

    Two residue shapes exist in the tree: a closing tag split by whitespace
    (``</`` + newline + ``body>``, left behind once the injected block between the
    halves was stripped) and a stray ``<`` immediately before an otherwise intact
    closing tag.  A third shape appears before the block is stripped: the injected
    block still sits *inside* the halves of the tag, and is lifted back out in front
    of it.  None of these shapes is valid HTML under any circumstance, so repairing
    them can only improve a page; pages that were never damaged are untouched.
    """
    for pattern, tag in _SPLIT_TAG_AROUND_BLOCK_RES:
        if pattern.search(text):
            text = pattern.sub(lambda m, tag=tag: m.group(1) + tag, text)
    for pattern, tag in _SPLIT_CLOSE_TAG_RES:
        if pattern.search(text):
            text = pattern.sub(tag, text)
    return _STRAY_LT_RE.sub("", text)


def strip_block(text: str) -> str:
    if STYLE_START in text:
        text = STYLE_RE.sub("", text)
    if BLOCK_START in text:
        text = BLOCK_RE.sub("\n", text)
    return repair_injected_markup(text)


def insert_block(text: str, block: str) -> str:
    base = strip_block(text)
    head = _last_index(HEAD_CLOSE_RE, base)
    if head != -1:
        base = base[:head] + STYLE_START + STYLE + STYLE_END + base[head:]
    else:
        block = STYLE_START + STYLE + STYLE_END + block
    index = _last_index(BODY_CLOSE_RE, base)
    if index == -1:
        return base.rstrip() + "\n" + block + "\n"
    return base[:index] + block + base[index:]


# --------------------------------------------------------------------------- targets
def app_keys_from_text(text: str, names) -> list[str]:
    """Registry apps named in the page, longest name first to avoid Lite/Pro bleed."""
    haystack = text
    found: list[str] = []
    for name, key in names:
        if name in haystack:
            found.append(key)
            haystack = haystack.replace(name, " " * len(name))
    return found


def align_keys_with_copy(keys: list[str], rel: str, text: str, live: set[str]) -> list[str]:
    """CTA 開哪一版,由這一頁的文案決定 —— 不是由上游挑到哪個 key 決定。

    這個區塊是後製注入的,若它自作主張換成免費/Lite 版,就會出現「整頁在講
    買斷版、唯一按鈕開免費版」(2026-08-10 稽核抓到的誠實性問題)。規則:
      • 頁面文案/slug 點名付費版 → 用付費版(名稱與目的地一致)。
      • 文案沒點名付費版(例如 key 是從外連頁面的 App id 統計來的)→
        依 free-first 導流規則用免費版,對得上站上其他頁的門。
    """
    p2f, f2p = paid_to_free(), free_to_paid()
    stem = Path(rel).stem
    out: list[str] = []
    for key in keys:
        paid_key = key if key in p2f else f2p.get(key, "")
        if paid_key:
            names_paid = bool(
                paid_slug_re(paid_key).search(stem)
                or paid_name_re(paid_key).search(
                    strip_paid_nav_anchors(text, paid_key)
                )
            )
            free_key = p2f.get(paid_key, "")
            if names_paid:
                key = paid_key
            elif free_key in live:
                key = free_key
        if key in live and key not in out:
            out.append(key)
    return out


def vs_key(path: Path, live: set[str]) -> str | None:
    stem = path.stem
    for key in sorted(live, key=len, reverse=True):
        if stem.startswith(key + "-"):
            return key
    return None


def related_links(pages: Path, rel: str, limit: int = MAX_RELATED) -> list[tuple[str, str]]:
    """Sibling pages in the same locale, so orphan sections join the link graph."""
    locale = locale_of(rel)
    if not locale:
        return []
    self_path = pages / rel
    out: list[tuple[str, str]] = []
    root = pages / locale
    index = root / "index.html"
    if index.is_file():
        title = page_title(index) or "App guide"
        out.append((page_url(f"{locale}/"), title))
    for section in ("best-for", "reviews", "vs", "workflow", "seasonal", "answers"):
        directory = root / section
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.html")):
            if path.resolve() == self_path.resolve() or path.name == "index.html":
                continue
            title = page_title(path)
            if not title:
                continue
            out.append((page_url(f"{locale}/{section}/{path.name}"), title))
            break
        if len(out) >= limit:
            break
    return out[:limit]


_TITLE_CACHE: dict[Path, str] = {}


def page_title(path: Path) -> str:
    cached = _TITLE_CACHE.get(path)
    if cached is not None:
        return cached
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    except OSError:
        return ""
    match = TITLE_RE.search(head)
    title = htmllib.unescape(re.sub(r"\s+", " ", match.group(1)).strip()) if match else ""
    title = title.split(" | ")[0].strip()[:110]
    _TITLE_CACHE[path] = title
    return title


def hub_app_keys(
    pages: Path,
    rel: str,
    text: str,
    live: set[str],
    snapshot: dict[Path, set[str]],
) -> list[str]:
    """Apps recommended by the pages this hub links to (data-driven, never invented)."""
    base = (pages / rel).parent
    ids_to_key = {APPSTORE[k]: k for k in live}
    counts: Counter = Counter()
    seen = 0
    for href in LOCAL_HREF_RE.findall(text):
        if href.startswith(("http://", "https://")):
            if not href.startswith(SITE + "/"):
                continue
            target = pages / href[len(SITE) + 1 :]
        elif href.startswith("/"):
            continue
        else:
            target = base / href
        try:
            target = target.resolve()
            target.relative_to(pages.resolve())
        except (OSError, ValueError):
            continue
        if not target.is_file() or target == (pages / rel).resolve():
            continue
        if target.name == "index.html":
            continue  # navigation pages link to everything and would blur the topic
        seen += 1
        if seen > 400:
            break
        # read from the pre-run snapshot so a hub never feeds on its own output
        for app_id in snapshot.get(target, ()):
            key = ids_to_key.get(app_id)
            if key:
                counts[key] += 1
    if not counts:
        return []
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top = ranked[0][1]
    floor = max(2, top // 4)  # drop apps that only leak in via a stray cross-link
    return [key for key, n in ranked[:MAX_APPS_HUB] if n >= floor]


HUB_BASENAMES = {"index.html"}
HUB_ROOT_PAGES = {
    "about.html",
    "find-app.html",
    "focus-productivity.html",
    "kids-learning.html",
    "money-travel.html",
    "passport-photos.html",
    "photo-tools.html",
    "resume-formats.html",
    "sleep-wellbeing.html",
}


def classify(rel: str) -> str | None:
    parts = rel.split("/")
    name = parts[-1]
    if "/vs/" in rel and name != "index.html":
        return "vs"
    if "/workflow/" in rel and name != "index.html":
        return "workflow"
    if name in HUB_BASENAMES or (len(parts) == 1 and name in HUB_ROOT_PAGES):
        return "hub"
    if len(parts) >= 2 and parts[-2] in {"topic-hubs", "hubs"}:
        return "hub"
    return None


def iter_pages(pages: Path):
    for path in pages.rglob("*.html"):
        try:
            rel = path.relative_to(pages).as_posix()
        except ValueError:
            continue
        if rel.startswith(("_engine/", ".git/")):
            continue
        yield rel, path


APP_ID_RE = re.compile(r"apps\.apple\.com/app/id(\d+)")


def app_id_snapshot(pages: Path) -> dict[Path, tuple[str, ...]]:
    """App Store IDs each page carries *before* this run touches anything.

    Sorted tuples, not sets: set iteration order varies with the interpreter's
    hash seed, which would make hub ranking differ between otherwise identical
    runs and leave the tree permanently dirty.
    """
    snapshot: dict[Path, tuple[str, ...]] = {}
    for _rel, path in iter_pages(pages):
        body = strip_block(path.read_text(encoding="utf-8", errors="ignore"))
        ids = sorted(set(APP_ID_RE.findall(body)))
        if ids:
            snapshot[path.resolve()] = tuple(ids)
    return snapshot


HEADINGS = {
    "vs": "App Store",
    "workflow": "App Store",
    "hub": "App Store",
}


def generate(pages: Path, labels: dict[str, str], check: bool) -> tuple[int, int]:
    live = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    live = {k for k in live if k in APPSTORE and k in APPS}
    names = _sorted_names(live)
    snapshot = app_id_snapshot(pages)
    changed = 0
    considered = 0

    def render(rel: str, path: Path, kind: str, text: str) -> tuple[str, int]:
        """New text for one page, plus whether it counted towards ``considered``."""
        if NOINDEX_RE.search(text) or FREE_FIRST in text:
            return text, 0
        stripped = strip_block(text)
        if APPLE_RE.search(stripped):
            return text, 0  # already reaches the store on its own
        if kind == "vs":
            key = vs_key(path, live)
            keys = [key] if key else app_keys_from_text(stripped, names)[:1]
        elif kind == "workflow":
            keys = app_keys_from_text(stripped, names)[:MAX_APPS_CONTENT]
        else:
            keys = hub_app_keys(pages, rel, stripped, live, snapshot)
            if not keys:
                keys = app_keys_from_text(stripped, names)[:MAX_APPS_HUB]
        keys = align_keys_with_copy([k for k in keys if k in live], rel, stripped, live)
        if not keys:
            return text, 1
        label = labels.get(locale_of(rel)) or labels.get("en") or FALLBACK_LABEL
        related = related_links(pages, rel) if kind in {"vs", "workflow"} else []
        block = build_block(rel, keys, label, related, HEADINGS[kind])
        return insert_block(text, block), 1

    for rel, path in iter_pages(pages):
        kind = classify(rel)
        if kind is None:
            continue
        original = path.read_text(encoding="utf-8", errors="ignore")
        # Heal damage from earlier runs *before* deciding anything: a page whose
        # closing tag this script once sliced apart may well be skipped below
        # (noindex / already links to the store / no live app), and would then stay
        # broken for ever.  Repairing up front makes the fix self-applying.
        text = repair_injected_markup(original)
        updated, counted = render(rel, path, kind, text)
        considered += counted
        if updated != original:
            changed += 1
            if not check:
                path.write_text(updated, encoding="utf-8")
    return changed, considered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-labels", action="store_true")
    args = parser.parse_args()

    labels = load_labels(args.pages_dir, args.refresh_labels)
    changed, considered = generate(args.pages_dir, labels, args.check)
    print(
        f"store-reach: locales_with_label={len(labels)} "
        f"pages_without_store_path={considered} pages_written={changed}"
    )
    if args.check and changed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
