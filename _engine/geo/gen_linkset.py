#!/usr/bin/env python3
"""Generate an RFC 9264 JSON Linkset for every public app."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

from appstore_live import live_app_keys  # noqa: E402
import gen_image_sitemap  # noqa: E402
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
LINKSET_TYPE = "application/linkset+json"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
PRIORITY_KEYS = ("lumibopomofopro", "lumibopomofo")
DISCOVERY_RE = re.compile(
    r"\s*<link\b(?=[^>]*\brel=[\"'][^\"']*\blinkset\b[^\"']*[\"'])[^>]*>\s*",
    flags=re.IGNORECASE,
)
FEED_DISCOVERY_RE = re.compile(
    r"<link\b"
    r"(?=[^>]*\brel=[\"'][^\"']*\balternate\b[^\"']*[\"'])"
    r"(?=[^>]*\btype=[\"']application/"
    r"(?:atom\+xml|rss\+xml|feed\+json)[\"'])[^>]*>",
    flags=re.IGNORECASE,
)


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.alternates: list[tuple[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "link":
            return
        values = {key.lower(): value for key, value in attrs if value is not None}
        relations = values.get("rel", "").lower().split()
        href = values.get("href")
        if "canonical" in relations and href:
            self.canonicals.append(href)
        if "alternate" in relations and href and values.get("hreflang"):
            self.alternates.append((href, values["hreflang"]))


def _absolute_url(value: str, context_url: str) -> str:
    return urllib.parse.urljoin(context_url, value)


def _owned_path(url: str, pages: Path, site: str) -> Path:
    parsed = urllib.parse.urlsplit(url)
    site_parts = urllib.parse.urlsplit(site)
    if (
        parsed.scheme != site_parts.scheme
        or parsed.netloc != site_parts.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Linkset URL is not a stable owned URL: {url}")
    base_path = site_parts.path.rstrip("/")
    prefix = f"{base_path}/" if base_path else "/"
    if not parsed.path.startswith(prefix):
        raise ValueError(f"Linkset URL is outside the published site path: {url}")
    relative = urllib.parse.unquote(parsed.path[len(prefix) :])
    target = (pages / relative).resolve()
    try:
        target.relative_to(pages.resolve())
    except ValueError as error:
        raise ValueError(f"Linkset URL escapes the Pages directory: {url}") from error
    if not target.is_file() or target.stat().st_size == 0:
        raise FileNotFoundError(f"Linkset resource is missing or empty: {target}")
    return target


def _page_metadata(path: Path) -> _PageMetadataParser:
    parser = _PageMetadataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _ordered_keys(keys: set[str]) -> list[str]:
    priority = [key for key in PRIORITY_KEYS if key in keys]
    return priority + sorted(keys - set(priority))


def _english_title(value: str) -> list[dict[str, str]]:
    return [{"value": value, "language": "en"}]


def _guide_context(
    key: str,
    pages: Path,
    site: str,
    story_map: dict[str, tuple[str, str]],
) -> tuple[dict[str, object], dict[str, str]]:
    guide_path = pages / "guides" / f"{key}.html"
    if not guide_path.is_file():
        raise FileNotFoundError(f"Public app guide is missing: {guide_path}")
    metadata = _page_metadata(guide_path)
    canonicals = list(dict.fromkeys(metadata.canonicals))
    expected_guide = f"{site}/guides/{key}.html"
    if canonicals != [expected_guide]:
        raise ValueError(
            f"{guide_path} must have canonical {expected_guide}; found {canonicals}"
        )

    alternates: dict[str, set[str]] = {}
    for href, language in metadata.alternates:
        absolute = _absolute_url(href, expected_guide)
        _owned_path(absolute, pages, site)
        alternates.setdefault(absolute, set()).add(language)
    if not alternates:
        raise ValueError(f"Public app guide has no language alternates: {guide_path}")

    if key not in story_map:
        raise ValueError(f"Public app has no canonical Web Story poster: {key}")
    story_url, poster_url = story_map[key]
    hub_url = f"{site}/hubs/{key}.html"
    _owned_path(hub_url, pages, site)

    store_url = appstore_url(key, "iag_linkset")
    parsed_store = urllib.parse.urlsplit(store_url)
    if (
        parsed_store.scheme != "https"
        or parsed_store.netloc != "apps.apple.com"
        or not re.fullmatch(r"/app/id\d+", parsed_store.path)
        or urllib.parse.parse_qs(parsed_store.query) != {"ct": ["iag_linkset"]}
    ):
        raise ValueError(f"Invalid App Store Linkset target for {key}: {store_url}")

    name = APPS[key]["name"]
    context: dict[str, object] = {
        "anchor": expected_guide,
        "alternate": [
            {
                "href": href,
                "hreflang": sorted(languages),
                "type": "text/html",
            }
            for href, languages in sorted(alternates.items())
        ],
        "related": [
            {
                "href": store_url,
                "type": "text/html",
                "title*": _english_title(f"{name} on the App Store"),
            },
            {
                "href": story_url,
                "type": "text/html",
                "title*": _english_title(f"{name} visual story"),
            },
        ],
        "collection": [
            {
                "href": hub_url,
                "type": "text/html",
                "title*": _english_title(f"{name} resource hub"),
            }
        ],
        "preview": [
            {
                "href": poster_url,
                "type": "image/jpeg",
                "title*": _english_title(f"{name} story poster"),
            }
        ],
    }
    return context, {
        "guide": expected_guide,
        "name": name,
        "store": store_url,
        "story": story_url,
        "poster": poster_url,
        "hub": hub_url,
    }


def build_document(
    pages: Path, live_keys: set[str], site: str = SITE
) -> tuple[dict[str, object], list[dict[str, str]]]:
    unknown = live_keys - set(APPS)
    if unknown:
        raise ValueError(f"Public app keys are missing from the registry: {unknown}")

    story_map = {
        Path(urllib.parse.urlsplit(story).path).stem: (story, poster)
        for story, poster in gen_image_sitemap.collect(pages, site)
    }
    if set(story_map) != live_keys:
        missing = sorted(live_keys - set(story_map))
        stale = sorted(set(story_map) - live_keys)
        raise ValueError(
            f"Web Story/public app mismatch; missing={missing}, stale={stale}"
        )

    records: list[dict[str, str]] = []
    contexts: list[dict[str, object]] = []
    for key in _ordered_keys(live_keys):
        context, record = _guide_context(key, pages, site, story_map)
        contexts.append(context)
        records.append({"key": key, **record})

    root_path = pages / "index.html"
    if not root_path.is_file():
        raise FileNotFoundError(f"Site index is missing: {root_path}")
    root_url = f"{site}/index.html"
    root_canonicals = list(dict.fromkeys(_page_metadata(root_path).canonicals))
    if root_canonicals != [root_url]:
        raise ValueError(
            f"{root_path} must have canonical {root_url}; found {root_canonicals}"
        )

    root_resources = [
        ("alternate", "feed.xml", "application/atom+xml"),
        ("alternate", "rss.xml", "application/rss+xml"),
        ("alternate", "feed.json", "application/feed+json"),
        ("describedby", "llms-full.txt", "text/plain"),
        ("describedby", "apps/index.html", "text/html"),
    ]
    root_context: dict[str, object] = {
        "anchor": root_url,
        "item": [
            {
                "href": record["guide"],
                "type": "text/html",
                "title*": _english_title(record["name"]),
            }
            for record in records
        ],
    }
    for relation, relative, media_type in root_resources:
        url = f"{site}/{relative}"
        _owned_path(url, pages, site)
        root_context.setdefault(relation, []).append(
            {"href": url, "type": media_type}
        )
    return {"linkset": [root_context, *contexts]}, records


def render_sitemap(site: str = SITE) -> str:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
    ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = f"{site}/linkset.json"
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def discovery_link(site: str = SITE) -> str:
    return (
        f'<link rel="linkset" type="{LINKSET_TYPE}" '
        f'href="{site}/linkset.json">'
    )


def ensure_discovery(path: Path, site: str = SITE) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source:
        raise ValueError(f"Linkset discovery target has no closing head: {path}")
    cleaned = DISCOVERY_RE.sub("\n", source)
    social_index = cleaned.find("<!-- social-preview:start -->")
    feed_match = FEED_DISCOVERY_RE.search(cleaned)
    insert_index = (
        social_index
        if social_index >= 0
        else feed_match.start()
        if feed_match
        else cleaned.index("</head>")
    )
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + discovery_link(site)
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_if_changed(path, updated)


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    document, records = build_document(pages, set(live_keys), site)
    changed = int(
        _write_if_changed(
            pages / "linkset.json",
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        )
    )
    changed += int(
        _write_if_changed(pages / "sitemap_linkset.xml", render_sitemap(site))
    )
    discovery_paths = [pages / "index.html"] + [
        pages / "guides" / f"{record['key']}.html" for record in records
    ]
    for path in discovery_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Linkset discovery target is missing: {path}")
        changed += int(ensure_discovery(path, site))
    return {
        "apps": len(records),
        "contexts": len(document["linkset"]),
        "discovery_pages": len(discovery_paths),
        "changed_files": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=Path, default=PAGES, help="Alternate Pages checkout."
    )
    args = parser.parse_args()
    result = generate(args.pages)
    print(
        "RFC 9264 Linkset: "
        f"{result['apps']} public apps, {result['contexts']} contexts, "
        f"{result['discovery_pages']} discovery pages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
