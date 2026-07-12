#!/usr/bin/env python3
"""Generate rich Open Graph, X Card, and oEmbed previews for public apps."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import html
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFilter, ImageOps


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

from appstore_live import live_app_keys  # noqa: E402
import gen_linkset  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
CARD_SIZE = (1200, 675)
POSTER_SIZE = (450, 600)
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ROBOTS_DIRECTIVE = (
    "index,follow,max-image-preview:large,"
    "max-snippet:-1,max-video-preview:-1"
)
BLOCK_START = "<!-- social-preview:start -->"
BLOCK_END = "<!-- social-preview:end -->"
BLOCK_RE = re.compile(
    rf"\s*{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\s*",
    flags=re.DOTALL,
)


class _GuideMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.descriptions: list[str] = []
        self.canonicals: list[str] = []
        self.robots: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        lowered = tag.lower()
        values = {key.lower(): value for key, value in attrs if value is not None}
        if lowered == "title":
            self.in_title = True
        if (
            lowered == "meta"
            and values.get("name", "").lower() == "description"
            and values.get("content")
        ):
            self.descriptions.append(values["content"])
        if (
            lowered == "meta"
            and values.get("name", "").lower() == "robots"
            and values.get("content")
        ):
            self.robots.append(values["content"])
        if lowered == "link":
            relations = values.get("rel", "").lower().split()
            if "canonical" in relations and values.get("href"):
                self.canonicals.append(values["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _guide_metadata(path: Path, expected_canonical: str) -> tuple[str, str]:
    parser = _GuideMetadataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    title = _normalize_text("".join(parser.title_parts))
    descriptions = list(dict.fromkeys(map(_normalize_text, parser.descriptions)))
    canonicals = list(dict.fromkeys(parser.canonicals))
    if not title:
        raise ValueError(f"Social preview guide has no title: {path}")
    if len(descriptions) != 1:
        raise ValueError(
            f"Social preview guide must have one description: {path}"
        )
    if canonicals != [expected_canonical]:
        raise ValueError(
            f"{path} must have canonical {expected_canonical}; found {canonicals}"
        )
    forbidden = {"noindex", "nofollow", "none", "nosnippet", "noimageindex"}
    for directive in parser.robots:
        tokens = {
            token.strip().lower()
            for token in re.split(r"[\s,]+", directive)
            if token.strip()
        }
        if tokens & forbidden:
            raise ValueError(
                f"Social preview guide has conflicting robots rules: "
                f"{path}: {sorted(tokens & forbidden)}"
            )
    return title, descriptions[0]


def render_card(poster_path: Path) -> bytes:
    with Image.open(poster_path) as source:
        poster = source.convert("RGB")
    background = ImageOps.fit(
        poster, CARD_SIZE, method=Image.Resampling.LANCZOS
    ).filter(ImageFilter.GaussianBlur(34))
    canvas = background.convert("RGBA")
    canvas = Image.alpha_composite(
        canvas, Image.new("RGBA", CARD_SIZE, (7, 10, 24, 112))
    )

    foreground = ImageOps.fit(
        poster, POSTER_SIZE, method=Image.Resampling.LANCZOS
    )
    x = (CARD_SIZE[0] - POSTER_SIZE[0]) // 2
    y = (CARD_SIZE[1] - POSTER_SIZE[1]) // 2
    mask = Image.new("L", POSTER_SIZE, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, POSTER_SIZE[0] - 1, POSTER_SIZE[1] - 1),
        radius=30,
        fill=255,
    )
    shadow = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x - 12, y + 10, x + POSTER_SIZE[0] + 12, y + POSTER_SIZE[1] + 30),
        radius=42,
        fill=(0, 0, 0, 170),
    )
    canvas = Image.alpha_composite(
        canvas, shadow.filter(ImageFilter.GaussianBlur(22))
    )
    canvas.paste(foreground, (x, y), mask)
    border = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        (x, y, x + POSTER_SIZE[0] - 1, y + POSTER_SIZE[1] - 1),
        radius=30,
        outline=(255, 255, 255, 105),
        width=3,
    )
    canvas = Image.alpha_composite(canvas, border)

    output = BytesIO()
    canvas.convert("RGB").save(
        output,
        format="JPEG",
        quality=88,
        optimize=True,
        progressive=True,
    )
    return output.getvalue()


def oembed_url(key: str, canonical: str, site: str = SITE) -> str:
    query = urllib.parse.urlencode({"url": canonical, "format": "json"})
    return f"{site}/oembed/{key}.json?{query}"


def oembed_document(title: str, image_url: str, site: str = SITE) -> dict[str, object]:
    return {
        "version": "1.0",
        "type": "link",
        "title": title,
        "provider_name": "iOS App Guide",
        "provider_url": f"{site}/index.html",
        "cache_age": 86400,
        "thumbnail_url": image_url,
        "thumbnail_width": CARD_SIZE[0],
        "thumbnail_height": CARD_SIZE[1],
    }


def metadata_block(
    key: str,
    title: str,
    description: str,
    canonical: str,
    app_name: str,
    site: str = SITE,
) -> str:
    image_url = f"{site}/social/img/{key}-share.jpg"
    embed_url = oembed_url(key, canonical, site)
    image_alt = f"{app_name} iOS app guide preview"
    esc = lambda value: html.escape(str(value), quote=True)
    lines = [
        BLOCK_START,
        f'<meta property="og:title" content="{esc(title)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{esc(canonical)}">',
        f'<meta property="og:image" content="{esc(image_url)}">',
        f'<meta property="og:image:secure_url" content="{esc(image_url)}">',
        '<meta property="og:image:type" content="image/jpeg">',
        f'<meta property="og:image:width" content="{CARD_SIZE[0]}">',
        f'<meta property="og:image:height" content="{CARD_SIZE[1]}">',
        f'<meta property="og:image:alt" content="{esc(image_alt)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        '<meta property="og:locale" content="en_US">',
        '<meta property="og:site_name" content="iOS App Guide">',
        f'<meta name="robots" content="{ROBOTS_DIRECTIVE}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<meta name="twitter:image" content="{esc(image_url)}">',
        f'<meta name="twitter:image:alt" content="{esc(image_alt)}">',
        (
            '<link rel="alternate" type="application/json+oembed" '
            f'href="{esc(embed_url)}" title="{esc(title)}">'
        ),
        BLOCK_END,
    ]
    return "\n".join(lines)


def ensure_metadata(path: Path, block: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source:
        raise ValueError(f"Social preview guide has no closing head: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    feed_match = gen_linkset.FEED_DISCOVERY_RE.search(cleaned)
    insert_index = feed_match.start() if feed_match else cleaned.index("</head>")
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + block
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_text_if_changed(path, updated)


def render_sitemap(keys: list[str], site: str = SITE) -> str:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for key in keys:
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = (
            f"{site}/oembed/{key}.json"
        )
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def _write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    _, records = gen_linkset.build_document(pages, set(live_keys), site)
    keys = [record["key"] for record in records]
    changed = 0

    image_dir = pages / "social" / "img"
    oembed_dir = pages / "oembed"
    for record in records:
        key = record["key"]
        guide_path = pages / "guides" / f"{key}.html"
        title, description = _guide_metadata(guide_path, record["guide"])
        poster_path = gen_linkset._owned_path(record["poster"], pages, site)
        card_path = image_dir / f"{key}-share.jpg"
        image_url = f"{site}/social/img/{key}-share.jpg"
        changed += int(_write_bytes_if_changed(card_path, render_card(poster_path)))
        changed += int(
            _write_text_if_changed(
                oembed_dir / f"{key}.json",
                json.dumps(
                    oembed_document(title, image_url, site),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
        )
        changed += int(
            ensure_metadata(
                guide_path,
                metadata_block(
                    key,
                    title,
                    description,
                    record["guide"],
                    record["name"],
                    site,
                ),
            )
        )

    live_key_set = set(keys)
    for stale in image_dir.glob("*-share.jpg") if image_dir.is_dir() else ():
        if stale.name.removesuffix("-share.jpg") not in live_key_set:
            stale.unlink()
            changed += 1
    for stale in oembed_dir.glob("*.json") if oembed_dir.is_dir() else ():
        if stale.stem not in live_key_set:
            stale.unlink()
            changed += 1

    changed += int(
        _write_text_if_changed(
            pages / "sitemap_oembed.xml", render_sitemap(keys, site)
        )
    )
    return {
        "apps": len(records),
        "cards": len(records),
        "oembed": len(records),
        "metadata_pages": len(records),
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
        "Social previews: "
        f"{result['apps']} apps, {result['cards']} cards, "
        f"{result['oembed']} oEmbed responses, "
        f"{result['metadata_pages']} metadata pages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
