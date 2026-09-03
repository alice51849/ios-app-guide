#!/usr/bin/env python3
"""Generate a Google Image Sitemap for owned story and app-preview images."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from PIL import Image

from answer_app_store_links import (
    direct_app_store_ids,
    unmanaged_app_store_source,
)
from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from videogen.registry import APPSTORE  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"
ANSWER_IMAGE_SIZE = (1200, 675)
ANSWER_BLOCK_START = "<!-- answer-social-preview:start -->"
ANSWER_BLOCK_END = "<!-- answer-social-preview:end -->"
ANSWER_BLOCK_RE = re.compile(
    rf"{re.escape(ANSWER_BLOCK_START)}(?P<body>.*?)"
    rf"{re.escape(ANSWER_BLOCK_END)}",
    flags=re.DOTALL,
)
APP_ID_TO_KEY = {str(app_id): key for key, app_id in APPSTORE.items()}
if len(APP_ID_TO_KEY) != len(APPSTORE):
    raise RuntimeError("Image Sitemap App Store IDs must be unique")
ANSWER_OG_FIELDS = frozenset(
    {
        "og:image",
        "og:image:secure_url",
        "og:image:type",
        "og:image:width",
        "og:image:height",
        "og:image:alt",
    }
)
ANSWER_NAMED_FIELDS = frozenset(
    {
        "robots",
        "twitter:card",
        "twitter:image",
        "twitter:image:alt",
    }
)
ANSWER_ROBOTS_DIRECTIVES = frozenset(
    {
        "index",
        "follow",
        "max-image-preview:large",
        "max-snippet:-1",
        "max-video-preview:-1",
    }
)


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


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.images: list[str] = []
        self.properties: dict[str, list[str]] = {}
        self.named: dict[str, list[str]] = {}
        self.has_refresh = False
        self.attribute_errors: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        relevant_attributes = {
            "link": {"href", "rel"},
            "meta": {"content", "http-equiv", "name", "property"},
        }.get(tag, set())
        values: dict[str, str | None] = {}
        duplicates: set[str] = set()
        for key, value in attrs:
            key = key.lower()
            if key in values and key in relevant_attributes:
                duplicates.add(key)
                continue
            values.setdefault(key, value)
        if duplicates:
            self.attribute_errors.append(
                f"<{tag}> repeats {', '.join(sorted(duplicates))}"
            )

        rel = values.get("rel") or ""
        if tag == "link" and "canonical" in rel.split():
            if values.get("href"):
                self.canonicals.append(values["href"])
        if tag == "meta":
            property_name = (values.get("property") or "").strip().lower()
            name = (values.get("name") or "").strip().lower()
            content = values.get("content") or ""
            if property_name:
                self.properties.setdefault(property_name, []).append(content)
            if name:
                self.named.setdefault(name, []).append(content)
            if property_name == "og:image":
                self.images.append(content)
        if (
            tag == "meta"
            and (values.get("http-equiv") or "").lower() == "refresh"
        ):
            self.has_refresh = True


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


def _reject_duplicate_attributes(
    parser: _PageMetadataParser,
    path: Path,
) -> None:
    if parser.attribute_errors:
        raise ValueError(
            f"{path} has duplicate metadata attributes: "
            + "; ".join(parser.attribute_errors)
        )


def _verified_answer_image(
    image_url: str,
    app_id: str,
    pages: Path,
    site: str,
    answer: Path,
) -> Path:
    key = APP_ID_TO_KEY.get(app_id)
    if key is None:
        raise ValueError(f"{answer} references unknown App Store ID: {app_id}")
    expected = f"{site}/social/img/{key}-share.jpg"
    if image_url != expected:
        raise ValueError(
            f"{answer} Answer image does not match App Store ID {app_id}: "
            f"{image_url}"
        )
    target = _owned_file(image_url, pages, site)
    try:
        with Image.open(target) as image:
            image_format = image.format
            image_size = image.size
            image.verify()
    except (OSError, SyntaxError) as error:
        raise ValueError(
            f"{answer} Answer image is not a valid JPEG: {target}"
        ) from error
    if image_format != "JPEG" or image_size != ANSWER_IMAGE_SIZE:
        raise ValueError(
            f"{answer} Answer image must be a "
            f"{ANSWER_IMAGE_SIZE[0]}x{ANSWER_IMAGE_SIZE[1]} JPEG: {target}"
        )
    return target


def _single_metadata_value(
    values: dict[str, list[str]],
    key: str,
    path: Path,
) -> str:
    matches = values.get(key, [])
    if len(matches) != 1:
        raise ValueError(
            f"{path} Answer social preview must declare exactly one {key}; "
            f"found {len(matches)}"
        )
    return matches[0]


def _answer_entry(
    answer: Path,
    pages: Path,
    site: str,
) -> tuple[str, str] | None:
    source = answer.read_text(encoding="utf-8")
    parser = _PageMetadataParser()
    parser.feed(source)
    _reject_duplicate_attributes(parser, answer)
    app_store_ids = direct_app_store_ids(
        unmanaged_app_store_source(source),
        answer,
    )

    free_resource = any(
        value.strip().casefold() == "true"
        for value in parser.named.get("iag-free-resource-first", [])
    )
    if free_resource or parser.has_refresh or len(app_store_ids) != 1:
        return None
    app_id = next(iter(app_store_ids))

    start_count = source.count(ANSWER_BLOCK_START)
    end_count = source.count(ANSWER_BLOCK_END)
    if start_count == 0 and end_count == 0:
        image_properties = {
            key
            for key in parser.properties
            if key == "og:image" or key.startswith("og:image:")
        }
        image_names = {
            key
            for key in parser.named
            if key == "twitter:image" or key.startswith("twitter:image:")
        }
        if image_properties or image_names:
            raise ValueError(
                f"{answer} has unmanaged image metadata: "
                f"{sorted(image_properties | image_names)}"
            )
        return None
    if start_count != 1 or end_count != 1:
        raise ValueError(
            f"{answer} must contain one complete Answer social preview block"
        )

    block_match = ANSWER_BLOCK_RE.search(source)
    head_end = source.lower().find("</head>")
    if (
        block_match is None
        or head_end < 0
        or block_match.start() > head_end
        or block_match.end() > head_end
    ):
        raise ValueError(
            f"{answer} must contain one complete Answer social preview block "
            "inside <head>"
        )

    block_parser = _PageMetadataParser()
    block_parser.feed(block_match.group("body"))
    _reject_duplicate_attributes(block_parser, answer)
    block_image_properties = {
        key
        for key in block_parser.properties
        if key == "og:image" or key.startswith("og:image:")
    }
    block_named_fields = {
        key
        for key in block_parser.named
        if key in ANSWER_NAMED_FIELDS
        or key == "twitter:image"
        or key.startswith("twitter:image:")
    }
    full_image_properties = {
        key
        for key in parser.properties
        if key == "og:image" or key.startswith("og:image:")
    }
    full_named_fields = {
        key
        for key in parser.named
        if key in ANSWER_NAMED_FIELDS
        or key == "twitter:image"
        or key.startswith("twitter:image:")
    }
    if (
        block_image_properties != ANSWER_OG_FIELDS
        or block_named_fields != ANSWER_NAMED_FIELDS
    ):
        raise ValueError(
            f"{answer} has an incomplete Answer social preview block"
        )
    if (
        full_image_properties != ANSWER_OG_FIELDS
        or full_named_fields != ANSWER_NAMED_FIELDS
    ):
        raise ValueError(
            f"{answer} has unmanaged Answer social preview metadata"
        )

    for key in ANSWER_OG_FIELDS:
        if parser.properties.get(key, []) != block_parser.properties.get(key, []):
            raise ValueError(
                f"{answer} has unmanaged Answer social preview metadata: {key}"
            )
    for key in ANSWER_NAMED_FIELDS:
        if parser.named.get(key, []) != block_parser.named.get(key, []):
            raise ValueError(
                f"{answer} has unmanaged Answer social preview metadata: {key}"
            )

    canonicals = list(dict.fromkeys(parser.canonicals))
    if len(canonicals) != 1:
        raise ValueError(
            f"{answer} must declare exactly one canonical URL; "
            f"found {len(canonicals)}"
        )
    expected_page = f"{site}/answers/{answer.name}"
    page_url = _absolute_url(canonicals[0], expected_page)
    if page_url != expected_page:
        raise ValueError(
            f"{answer} canonical URL does not match its published path: "
            f"{page_url}"
        )

    image_url = _single_metadata_value(
        block_parser.properties,
        "og:image",
        answer,
    )
    secure_url = _single_metadata_value(
        block_parser.properties,
        "og:image:secure_url",
        answer,
    )
    image_type = _single_metadata_value(
        block_parser.properties,
        "og:image:type",
        answer,
    )
    image_width = _single_metadata_value(
        block_parser.properties,
        "og:image:width",
        answer,
    )
    image_height = _single_metadata_value(
        block_parser.properties,
        "og:image:height",
        answer,
    )
    image_alt = _single_metadata_value(
        block_parser.properties,
        "og:image:alt",
        answer,
    )
    robots = _single_metadata_value(block_parser.named, "robots", answer)
    twitter_card = _single_metadata_value(
        block_parser.named,
        "twitter:card",
        answer,
    )
    twitter_image = _single_metadata_value(
        block_parser.named,
        "twitter:image",
        answer,
    )
    twitter_alt = _single_metadata_value(
        block_parser.named,
        "twitter:image:alt",
        answer,
    )
    robots_directives = frozenset(
        directive.strip().casefold()
        for directive in robots.split(",")
        if directive.strip()
    )
    if (
        secure_url != image_url
        or image_type.casefold() != "image/jpeg"
        or image_width != "1200"
        or image_height != "675"
        or not image_alt.strip()
        or robots_directives != ANSWER_ROBOTS_DIRECTIVES
        or twitter_card.casefold() != "summary_large_image"
        or twitter_image != image_url
        or twitter_alt != image_alt
    ):
        raise ValueError(
            f"{answer} has invalid Answer social preview metadata"
        )

    _verified_answer_image(image_url, app_id, pages, site, answer)
    return page_url, image_url


def collect(
    pages: Path = PAGES,
    site: str = SITE,
    *,
    include_hubs: bool = False,
    include_answers: bool = False,
) -> list[tuple[str, str]]:
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

    if include_hubs:
        hub_paths = list((pages / "hubs").glob("*.html"))
        for locale in OFFICIAL_LOCALES:
            hub_paths.extend((pages / locale / "hubs").glob("*.html"))
        for hub in sorted(hub_paths, key=lambda path: path.as_posix().casefold()):
            if hub.name == "index.html":
                continue
            parser = _PageMetadataParser()
            parser.feed(hub.read_text(encoding="utf-8"))
            canonicals = list(dict.fromkeys(parser.canonicals))
            images = list(dict.fromkeys(parser.images))
            if len(canonicals) != 1:
                raise ValueError(
                    f"{hub} must declare exactly one canonical URL; found "
                    f"{len(canonicals)}"
                )
            if len(images) != 1:
                raise ValueError(
                    f"{hub} must declare exactly one Open Graph image; found "
                    f"{len(images)}"
                )
            relative = hub.relative_to(pages).as_posix()
            expected_page = f"{site}/{relative}"
            page_url = _absolute_url(canonicals[0], expected_page)
            if page_url != expected_page:
                raise ValueError(
                    f"{hub} canonical URL does not match its published path: "
                    f"{page_url}"
                )
            if page_url in seen_pages:
                raise ValueError(f"Duplicate Image Sitemap page URL: {page_url}")
            image_url = _absolute_url(images[0], page_url)
            _owned_file(image_url, pages, site)
            seen_pages.add(page_url)
            entries.append((page_url, image_url))

    if include_answers:
        answers = pages / "answers"
        answer_paths = answers.glob("*.html") if answers.is_dir() else ()
        for answer in sorted(
            answer_paths,
            key=lambda path: path.name.casefold(),
        ):
            if answer.name == "index.html":
                continue
            entry = _answer_entry(answer, pages, site)
            if entry is None:
                continue
            page_url, image_url = entry
            if page_url in seen_pages:
                raise ValueError(f"Duplicate Image Sitemap page URL: {page_url}")
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
    entries = collect(
        pages,
        site,
        include_hubs=True,
        include_answers=True,
    )
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
    print(f"Image Sitemap {state}: {count} owned preview images")


if __name__ == "__main__":
    main()
