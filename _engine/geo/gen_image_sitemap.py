#!/usr/bin/env python3
"""Generate a Google Image Sitemap for canonical Web Story posters."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import os
from pathlib import Path
import urllib.parse
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"


class _StoryMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.posters: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "link" and "canonical" in values.get("rel", "").split():
            if values.get("href"):
                self.canonicals.append(values["href"])
        if tag.lower() == "amp-story" and values.get("poster-portrait-src"):
            self.posters.append(values["poster-portrait-src"])


def _absolute_url(value: str, base_url: str) -> str:
    return urllib.parse.urljoin(f"{base_url.rsplit('/', 1)[0]}/", value)


def _owned_file(url: str, pages: Path, site: str) -> Path:
    parsed = urllib.parse.urlsplit(url)
    site_parts = urllib.parse.urlsplit(site)
    if (
        parsed.scheme != site_parts.scheme
        or parsed.netloc != site_parts.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Image URL is not a stable owned URL: {url}")

    base_path = site_parts.path.rstrip("/")
    prefix = f"{base_path}/" if base_path else "/"
    if not parsed.path.startswith(prefix):
        raise ValueError(f"Image URL is outside the published site path: {url}")

    relative = urllib.parse.unquote(parsed.path[len(prefix) :])
    target = (pages / relative).resolve()
    try:
        target.relative_to(pages.resolve())
    except ValueError as error:
        raise ValueError(f"Image URL escapes the Pages directory: {url}") from error
    if not target.is_file() or target.stat().st_size == 0:
        raise FileNotFoundError(f"Image sitemap asset is missing or empty: {target}")
    return target


def collect(pages: Path = PAGES, site: str = SITE) -> list[tuple[str, str]]:
    stories = pages / "stories"
    if not stories.is_dir():
        raise FileNotFoundError(f"Web Stories directory does not exist: {stories}")

    entries: list[tuple[str, str]] = []
    seen_pages: set[str] = set()
    for story in sorted(stories.glob("*.html"), key=lambda path: path.name.casefold()):
        if story.name == "index.html":
            continue
        parser = _StoryMetadataParser()
        parser.feed(story.read_text(encoding="utf-8"))

        canonicals = list(dict.fromkeys(parser.canonicals))
        posters = list(dict.fromkeys(parser.posters))
        if len(canonicals) != 1:
            raise ValueError(
                f"{story} must declare exactly one canonical URL; found {len(canonicals)}"
            )
        if len(posters) != 1:
            raise ValueError(
                f"{story} must declare exactly one portrait poster; found {len(posters)}"
            )

        expected_page = f"{site}/stories/{story.name}"
        page_url = _absolute_url(canonicals[0], expected_page)
        if page_url != expected_page:
            raise ValueError(
                f"{story} canonical URL does not match its published path: {page_url}"
            )
        if page_url in seen_pages:
            raise ValueError(f"Duplicate Image Sitemap page URL: {page_url}")

        image_url = _absolute_url(posters[0], page_url)
        _owned_file(image_url, pages, site)
        seen_pages.add(page_url)
        entries.append((page_url, image_url))

    if not entries:
        raise ValueError("No canonical Web Story posters were found")
    return entries


def render(entries: list[tuple[str, str]]) -> str:
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("image", IMAGE_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for page_url, image_url in entries:
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = page_url
        image = ET.SubElement(url, f"{{{IMAGE_NS}}}image")
        ET.SubElement(image, f"{{{IMAGE_NS}}}loc").text = image_url
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def generate(pages: Path = PAGES, site: str = SITE) -> tuple[int, bool]:
    entries = collect(pages, site)
    changed = _write_if_changed(pages / "sitemap_images.xml", render(entries))
    return len(entries), changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=Path, default=PAGES, help="Alternate Pages checkout."
    )
    args = parser.parse_args()
    count, changed = generate(args.pages)
    state = "updated" if changed else "unchanged"
    print(f"Image Sitemap {state}: {count} canonical Web Story posters")


if __name__ == "__main__":
    main()
