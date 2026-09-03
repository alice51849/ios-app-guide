#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keep only App-Store-reachable locales in the search index, and keep sitemaps honest.

The site ships ~1,000 locale directories, but Apple only sells in ~50 store
languages.  Pages written in a language the App Store does not support cannot
convert, are near-duplicates of the official-locale pages, and — at 20k+ URLs —
they dominate the crawl budget and dilute the domain's quality signal.  They stay
published and crawlable (``noindex,follow`` keeps their outbound link value) but
they leave the index and the sitemaps.

This runs as a pipeline step, *after* the page generators and *before* the sitemap
lastmod pass.  Editing the built files by hand does not work: the generators
overwrite them within the same publish.  It also fixes two sitemap defects found
in the same audit — URLs pointing at files that no longer exist, and indexable
pages that no sitemap ever listed.

    python geo/gen_locale_indexation.py            # apply
    python geo/gen_locale_indexation.py --check    # report only
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from official_locales import OFFICIAL_LOCALES  # noqa: E402
from canonical_urls import canonical_url_for_html  # noqa: E402
from site_tree_index import SiteTreeIndex  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")

# The locales we actually localize App Store metadata in, plus base English.
# Deliberately *not* base-language matching: fr-BF or en-ZW is readable French /
# English, but the page is a near-duplicate of fr-FR / en-US and can never be
# paired with localized store metadata, so it costs crawl budget and adds a
# duplicate-content signal without being able to convert.
INDEXABLE_LOCALES = set(OFFICIAL_LOCALES) | {"en"}

ROBOTS_META_RE = re.compile(
    r'<meta[^>]*\bname="robots"[^>]*>', re.I
)
HEAD_CLOSE_RE = re.compile(r"</head>", re.I)
MARK = "<!-- non-store-locale -->"
NOINDEX_META = f'{MARK}<meta name="robots" content="noindex,follow">'
ALTERNATE_RE = re.compile(
    r'\s*<link[^>]+rel="alternate"[^>]+hreflang="([^"]+)"[^>]*>', re.I
)
LOC_BLOCK_RE = re.compile(r"[ \t]*<url>.*?</url>\s*", re.DOTALL)
LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
SITEMAP_BLOCK_RE = re.compile(r"[ \t]*<sitemap>.*?</sitemap>\s*", re.DOTALL)
SITEMAP_ENTRY_RE = re.compile(
    r"<(?:[A-Za-z_][\w.-]*:)?(?:url|sitemap)(?:\s|>)",
    re.IGNORECASE,
)
ORPHAN_SITEMAP = "sitemap_orphans.xml"


@dataclass
class IndexationResult:
    tree: SiteTreeIndex
    dead_locales: set[str]
    indexable_relatives: set[str]
    canonical_by_relative: dict[str, str]
    page_stats: dict[str, int]
    sitemap_stats: dict[str, int]
    dropped_sitemaps: int
    orphan_urls: int


# ------------------------------------------------------------------ locale model
def first_html(
    directory: Path,
    tree: SiteTreeIndex | None = None,
) -> Path | None:
    if tree is not None:
        relatives = tree.html_relatives_under(directory.name)
        return tree.path(relatives[0]) if relatives else None
    for path in sorted(directory.rglob("*.html")):
        return path
    return None


def true_locale_dirs(
    pages: Path,
    tree: SiteTreeIndex | None = None,
) -> dict[str, bool]:
    """Map top-level directory -> is-a-locale-directory.

    A directory is a locale only when its pages declare that exact language.
    Matching on "not in OFFICIAL_LOCALES" instead would sweep in the English
    content directories (answers/, apps/, tools/ ...) and the real store-locale
    aliases (ja-JP, zh-CN, nb-NO ...).
    """
    tree = tree or SiteTreeIndex.scan(pages)
    result: dict[str, bool] = {}
    for child in sorted(pages.iterdir()):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        sample = first_html(child, tree)
        if sample is None:
            result[child.name] = False
            continue
        facts = tree.basic_facts(tree.relative(sample))
        result[child.name] = facts.lang == child.name
    return result


def non_store_locales(
    pages: Path,
    tree: SiteTreeIndex | None = None,
) -> set[str]:
    return {
        name
        for name, is_locale in true_locale_dirs(pages, tree).items()
        if is_locale and name not in INDEXABLE_LOCALES
    }


# ------------------------------------------------------------------ page rewrite
def apply_noindex(text: str) -> str:
    if MARK in text:
        return text
    if ROBOTS_META_RE.search(text):
        return ROBOTS_META_RE.sub(NOINDEX_META, text, count=1)
    match = HEAD_CLOSE_RE.search(text)
    if match:
        return text[: match.start()] + NOINDEX_META + text[match.start() :]
    return NOINDEX_META + text


def remove_noindex(text: str) -> str:
    """Undo our own stamp if a locale later becomes store-supported."""
    if MARK not in text:
        return text
    return text.replace(NOINDEX_META, "").replace(MARK, "")


def strip_dead_alternates(text: str, dead: set[str]) -> str:
    if not dead or 'rel="alternate"' not in text:
        return text

    def drop(match: re.Match[str]) -> str:
        return "" if match.group(1) in dead else match.group(0)

    return ALTERNATE_RE.sub(drop, text)


def rewrite_pages(
    pages: Path,
    dead: set[str],
    check: bool,
    tree: SiteTreeIndex | None = None,
) -> dict[str, int]:
    tree = tree or SiteTreeIndex.scan(pages)
    noindexed = 0
    alternates_cleaned = 0
    reindexed = 0
    for rel in tree.html_relatives():
        path = tree.path(rel)
        text = path.read_text(encoding="utf-8", errors="ignore")
        updated = text
        locale = rel.split("/")[0] if "/" in rel else ""
        if locale in dead:
            updated = apply_noindex(updated)
            if updated != text:
                noindexed += 1
        elif MARK in updated:
            updated = remove_noindex(updated)
            reindexed += 1
        before = updated
        updated = strip_dead_alternates(updated, dead)
        if updated != before:
            alternates_cleaned += 1
        if updated != text and not check:
            path.write_text(updated, encoding="utf-8")
            tree.update_source(rel, updated)
        else:
            tree.update_source(rel, text)
    return {
        "noindexed": noindexed,
        "reindexed": reindexed,
        "alternates_cleaned": alternates_cleaned,
    }


# ------------------------------------------------------------------ sitemap hygiene
def url_to_relative(url: str) -> str | None:
    prefix = SITE + "/"
    return url[len(prefix) :] if url.startswith(prefix) else None


def url_to_content_relative(url: str) -> str | None:
    rel = url_to_relative(url)
    if rel is None:
        return None
    if not rel or rel.endswith("/"):
        return f"{rel}index.html"
    return rel


def is_noindex_html(
    path: Path,
    tree: SiteTreeIndex | None = None,
) -> bool:
    if tree is not None:
        relative = tree.relative(path)
        if tree.contains(relative):
            return tree.facts(relative).noindex
    try:
        with path.open(encoding="utf-8", errors="ignore") as page:
            text = page.read(262144)
    except OSError:
        return False
    close = HEAD_CLOSE_RE.search(text)
    head = text[: close.start()] if close else text[:262144]
    robots = ROBOTS_META_RE.search(head)
    return bool(robots and "noindex" in robots.group(0).lower())


def sitemap_has_entries(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8", errors="ignore") as sitemap:
            tail = ""
            while chunk := sitemap.read(65536):
                source = tail + chunk
                if SITEMAP_ENTRY_RE.search(source):
                    return True
                tail = source[-128:]
    except OSError:
        return False
    return False


def sitemap_candidates(
    pages: Path,
    tree: SiteTreeIndex | None = None,
) -> list[Path]:
    excluded_names = {"sitemap_index.xml", ORPHAN_SITEMAP}
    candidates = (
        tuple(
            pages / path.relative_to(tree.root)
            for path in tree.sitemap_paths()
        )
        if tree is not None
        else tuple(pages.rglob("sitemap*.xml"))
    )
    return [
        candidate
        for candidate in sorted(candidates)
        if candidate.name not in excluded_names
    ]


def prune_sitemaps(
    pages: Path,
    dead: set[str],
    check: bool,
    tree: SiteTreeIndex | None = None,
) -> dict[str, int]:
    removed_dead = 0
    removed_ghost = 0
    removed_noindex = 0
    emptied: set[str] = set()
    kept_urls: set[str] = set()
    for path in sitemap_candidates(pages, tree):
        source = path.read_text(encoding="utf-8")
        stats = {"dead": 0, "ghost": 0, "noindex": 0, "kept": 0}

        def keep(match: re.Match[str]) -> str:
            body = match.group(0)
            loc = LOC_RE.search(body)
            if not loc:
                return body
            content_rel = url_to_content_relative(loc.group(1))
            if content_rel is None:
                stats["kept"] += 1
                kept_urls.add(loc.group(1))
                return body
            locale = (
                content_rel.split("/")[0]
                if "/" in content_rel
                else ""
            )
            if locale in dead:
                stats["dead"] += 1
                return ""
            target = pages / content_rel
            target_exists = (
                tree.contains(content_rel)
                if tree is not None and content_rel.endswith(".html")
                else target.is_file()
            )
            if content_rel.endswith(".html") and not target_exists:
                stats["ghost"] += 1
                return ""
            if content_rel.endswith(".html") and is_noindex_html(target, tree):
                stats["noindex"] += 1
                return ""
            stats["kept"] += 1
            kept_urls.add(loc.group(1))
            return body

        updated = LOC_BLOCK_RE.sub(keep, source)
        removed_dead += stats["dead"]
        removed_ghost += stats["ghost"]
        removed_noindex += stats["noindex"]
        if stats["kept"] == 0:
            emptied.add(path.relative_to(pages).as_posix())
        if updated != source and not check:
            path.write_text(updated, encoding="utf-8")
    return {
        "urls_dropped_non_store": removed_dead,
        "urls_dropped_missing_file": removed_ghost,
        "urls_dropped_noindex": removed_noindex,
        "sitemaps_emptied": len(emptied),
        "_emptied": emptied,
        "_kept": kept_urls,
    }


def indexable_pages(
    pages: Path,
    dead: set[str],
    tree: SiteTreeIndex | None = None,
) -> set[str]:
    tree = tree or SiteTreeIndex.scan(pages)
    out: set[str] = set()
    for rel in tree.html_relatives():
        locale = rel.split("/")[0] if "/" in rel else ""
        if locale in dead:
            continue
        if tree.facts(rel).noindex:
            continue
        out.add(rel)
    return out


def canonical_url_for_relative(
    pages: Path,
    relative: str,
    fallback: str,
    tree: SiteTreeIndex | None = None,
) -> str:
    if tree is None or not tree.contains(relative):
        return canonical_url_for_html(pages / relative, fallback, SITE)
    canonical = tree.canonical(relative)
    if canonical == SITE:
        return f"{SITE}/"
    if canonical and canonical.startswith(f"{SITE}/"):
        return canonical
    return fallback


def indexable_canonical_map(
    pages: Path,
    relatives: set[str],
    tree: SiteTreeIndex | None = None,
) -> dict[str, str]:
    return {
        relative: canonical_url_for_relative(
            pages,
            relative,
            f"{SITE}/{relative}",
            tree,
        )
        for relative in sorted(relatives)
    }


def write_orphan_sitemap(
    pages: Path,
    missing: list[str],
    check: bool,
    covered_urls: set[str] | None = None,
    tree: SiteTreeIndex | None = None,
) -> int:
    path = pages / ORPHAN_SITEMAP
    urls = {
        canonical_url_for_relative(
            pages,
            relative,
            f"{SITE}/{relative}",
            tree,
        )
        for relative in missing
    }
    urls.difference_update(covered_urls or set())
    if not urls:
        if path.is_file() and not check:
            path.unlink()
        return 0
    body = "".join(
        f"  <url><loc>{url}</loc></url>\n" for url in sorted(urls)
    )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}</urlset>\n"
    )
    if not check and (not path.is_file() or path.read_text(encoding="utf-8") != content):
        path.write_text(content, encoding="utf-8")
    return len(urls)


def update_sitemap_index(
    pages: Path,
    emptied: set[str],
    add_orphans: bool,
    check: bool,
    tree: SiteTreeIndex | None = None,
) -> int:
    path = pages / "sitemap_index.xml"
    if not path.is_file():
        return 0
    source = path.read_text(encoding="utf-8")
    previous: set[str] = set()
    for url in LOC_RE.findall(source):
        rel = url_to_relative(url)
        if rel is not None:
            previous.add(rel)

    candidates = previous | {
        candidate.relative_to(pages).as_posix()
        for candidate in sitemap_candidates(pages, tree)
    }
    if add_orphans:
        candidates.add(ORPHAN_SITEMAP)
    else:
        candidates.discard(ORPHAN_SITEMAP)
    valid = [
        rel
        for rel in sorted(candidates)
        if (
            rel not in emptied
            and (pages / rel).is_file()
            and sitemap_has_entries(pages / rel)
        )
    ]
    items = "\n".join(
        f"  <sitemap><loc>{SITE}/{rel}</loc></sitemap>"
        for rel in valid
    )
    updated = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}\n</sitemapindex>\n"
    )
    if updated != source and not check:
        path.write_text(updated, encoding="utf-8")
    return len(previous - set(valid))


def update_robots(pages: Path, add_orphans: bool, check: bool) -> bool:
    path = pages / "robots.txt"
    if not path.is_file():
        return False
    source = path.read_text(encoding="utf-8")
    line = f"Sitemap: {SITE}/{ORPHAN_SITEMAP}"
    if add_orphans and line not in source:
        updated = source.rstrip("\n") + "\n" + line + "\n"
    elif not add_orphans and line in source:
        updated = "\n".join(l for l in source.splitlines() if l.strip() != line) + "\n"
    else:
        return False
    if not check:
        path.write_text(updated, encoding="utf-8")
    return True


def run_indexation(
    pages: Path,
    *,
    check: bool = False,
    tree: SiteTreeIndex | None = None,
    rewrite_html: bool = True,
) -> IndexationResult:
    pages = pages.resolve()
    tree = tree or SiteTreeIndex.scan(pages)
    dead = non_store_locales(pages, tree)
    page_stats = (
        rewrite_pages(pages, dead, check, tree)
        if rewrite_html
        else {
            "noindexed": 0,
            "reindexed": 0,
            "alternates_cleaned": 0,
        }
    )
    sitemap_stats = prune_sitemaps(pages, dead, check, tree)
    kept_urls = sitemap_stats.pop("_kept")
    kept = {
        rel
        for rel in (
            url_to_content_relative(url)
            for url in kept_urls
        )
        if rel
    }
    covered_urls = {
        canonical_url_for_relative(
            pages,
            relative,
            url,
            tree,
        )
        if relative and relative.endswith(".html")
        else url
        for url in kept_urls
        for relative in [url_to_content_relative(url)]
    }
    emptied = sitemap_stats.pop("_emptied")
    indexable = indexable_pages(pages, dead, tree)
    missing = sorted(indexable - kept)
    orphans = write_orphan_sitemap(
        pages,
        missing,
        check,
        covered_urls,
        tree,
    )
    dropped_sitemaps = update_sitemap_index(
        pages,
        emptied,
        bool(orphans),
        check,
        tree,
    )
    update_robots(pages, bool(orphans), check)
    canonical_by_relative = indexable_canonical_map(
        pages,
        indexable,
        tree,
    )
    return IndexationResult(
        tree=tree,
        dead_locales=dead,
        indexable_relatives=indexable,
        canonical_by_relative=canonical_by_relative,
        page_stats=page_stats,
        sitemap_stats=sitemap_stats,
        dropped_sitemaps=dropped_sitemaps,
        orphan_urls=orphans,
    )


def print_result(result: IndexationResult) -> None:
    print(
        "locale-indexation: non_store_locales={dead} "
        "pages_noindexed={noindexed} pages_reindexed={reindexed} "
        "pages_alternates_cleaned={alternates_cleaned}".format(
            dead=len(result.dead_locales),
            **result.page_stats,
        )
    )
    print(
        "sitemap-hygiene: dropped_non_store={urls_dropped_non_store} "
        "dropped_missing_file={urls_dropped_missing_file} "
        "dropped_noindex={urls_dropped_noindex} "
        "sitemaps_unhooked={dropped} orphan_urls_added={orphans}".format(
            dropped=result.dropped_sitemaps,
            orphans=result.orphan_urls,
            **result.sitemap_stats,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print_result(
        run_indexation(
            args.pages_dir,
            check=args.check,
        )
    )


if __name__ == "__main__":
    main()
