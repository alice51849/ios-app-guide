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
from app_store_storefronts import (  # noqa: E402
    LOCALE_STOREFRONTS,
    PROMOTIONAL_RATING_MIN_COUNT,
    PROMOTIONAL_RATING_MIN_VALUE,
    campaign_app_store_url,
    has_trusted_promotional_rating,
    load_storefront_availability,
    load_storefront_details,
    localized_storefront_detail,
    verified_app_store_url,
)
import gen_linkset  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    OPEN_GRAPH_LOCALES,
    open_graph_locale as _open_graph_locale,
)
from videogen.registry import APPSTORE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
CARD_SIZE = (1200, 675)
POSTER_SIZE = (450, 600)
BUYER_INTENT_SIZE = (1200, 630)
OEMBED_SIZE = (
    BUYER_INTENT_SIZE[0] // 2,
    BUYER_INTENT_SIZE[1] // 2,
)
# One vote is too noisy to promote as social proof.
SOCIAL_RATING_MIN_VALUE = PROMOTIONAL_RATING_MIN_VALUE
SOCIAL_RATING_MIN_COUNT = PROMOTIONAL_RATING_MIN_COUNT
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ROBOTS_DIRECTIVE = (
    "index,follow,max-image-preview:large,"
    "max-snippet:-1,max-video-preview:-1"
)
BLOCK_START = "<!-- social-preview:start -->"
BLOCK_END = "<!-- social-preview:end -->"
QR_STYLE_ANCHOR = "<!-- app-store-qr-style:start -->"
DECISION_STYLE_ANCHOR = "<!-- app-decision-card-style:start -->"
BLOCK_RE = re.compile(
    rf"\s*{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\s*",
    flags=re.DOTALL,
)
HERO_START = "<!-- app-preview-hero:start -->"
HERO_END = "<!-- app-preview-hero:end -->"
HERO_RE = re.compile(
    rf"\s*{re.escape(HERO_START)}.*?{re.escape(HERO_END)}\s*",
    flags=re.DOTALL,
)
H1_RE = re.compile(r"<h1\b[^>]*>.*?</h1>", flags=re.IGNORECASE | re.DOTALL)
HERO_STYLE = """<style>
.iag-app-preview{margin:clamp(1rem,3vw,1.5rem) 0 clamp(1.5rem,4vw,2.25rem)}
.iag-app-preview__link{display:block;position:relative;width:100%;max-width:1200px;margin:0 auto;overflow:hidden;border-radius:clamp(14px,2.2vw,24px);background:#0b1020;box-shadow:0 18px 50px rgba(15,23,42,.22);line-height:0}
.iag-app-preview__link::after{content:"";position:absolute;inset:0;border:1px solid rgba(255,255,255,.28);border-radius:inherit;pointer-events:none}
.iag-app-preview__link:focus-visible{outline:3px solid #2563eb;outline-offset:4px}
.iag-app-preview__image{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}
@media(hover:hover){.iag-app-preview__link:hover{box-shadow:0 22px 60px rgba(15,23,42,.3)}}
</style>"""


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


def _campaign_store_url(store_url: str, campaign: str) -> str:
    return campaign_app_store_url(store_url, campaign)


def _oembed_campaign(locale: str) -> str:
    return f"iag_oembed_{locale.replace('-', '_').lower()}"


def _storefront_detail(
    app_id: str,
    locale: str,
    availability: dict[str, frozenset[str]],
    details: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object] | None:
    country = LOCALE_STOREFRONTS[locale]
    if app_id not in availability.get(country, frozenset()):
        return None
    detail = details.get(country, {}).get(app_id)
    if detail is None:
        return None
    return localized_storefront_detail(detail, locale)


def _storefront_proof(storefront: dict[str, object] | None) -> str:
    if storefront is None:
        return ""
    parts = ["App Store", _normalize_text(str(storefront["formatted_price"]))]
    if _has_social_rating(storefront):
        parts.extend(
            (
                f"★ {float(storefront['rating_value']):.1f}/5",
                str(int(storefront["rating_count"])),
            )
        )
    return " · ".join(parts)


def _has_social_rating(storefront: dict[str, object]) -> bool:
    return has_trusted_promotional_rating(storefront)


def _social_description(
    description: str,
    storefront: dict[str, object] | None,
) -> str:
    proof = _storefront_proof(storefront)
    return f"{proof}. {description}" if proof else description


def oembed_relative_path(key: str, locale: str | None = None) -> str:
    if locale is None:
        return f"oembed/{key}.json"
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported localized oEmbed locale: {locale}")
    return f"oembed/{locale}/{key}.json"


def oembed_url(
    key: str,
    canonical: str,
    site: str = SITE,
    locale: str | None = None,
) -> str:
    query = urllib.parse.urlencode({"url": canonical, "format": "json"})
    return f"{site}/{oembed_relative_path(key, locale)}?{query}"


def buyer_intent_image_url(
    key: str,
    locale: str,
    site: str = SITE,
) -> str:
    if re.fullmatch(r"[a-z0-9]+", key) is None:
        raise ValueError(f"Invalid buyer-intent app key: {key}")
    asset_locale = "en-US" if locale == "en" else locale
    if asset_locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported buyer-intent locale: {locale}")
    return f"{site}/visuals/{asset_locale}/{key}.svg"


def _available_buyer_intent_image(
    pages: Path,
    key: str,
    locale: str,
    site: str = SITE,
) -> str | None:
    url = buyer_intent_image_url(key, locale, site)
    asset_locale = "en-US" if locale == "en" else locale
    target = pages / "visuals" / asset_locale / f"{key}.svg"
    if not target.is_file() or target.stat().st_size == 0:
        return None
    return url


def rich_oembed_html(
    title: str,
    buyer_intent_url: str,
    app_store_url: str,
) -> str:
    visual = urllib.parse.urlsplit(buyer_intent_url)
    store = urllib.parse.urlsplit(app_store_url)
    if visual.scheme != "https" or not visual.hostname or visual.username:
        raise ValueError("Rich oEmbed visual URL must be public HTTPS")
    if (
        store.scheme != "https"
        or store.hostname != "apps.apple.com"
        or store.username
    ):
        raise ValueError("Rich oEmbed App Store URL is invalid")
    esc = lambda value: html.escape(str(value), quote=True)
    return (
        f'<a href="{esc(app_store_url)}" rel="nofollow noopener">'
        f'<img src="{esc(buyer_intent_url)}" alt="{esc(title)}" '
        f'width="{OEMBED_SIZE[0]}" height="{OEMBED_SIZE[1]}" '
        f'style="display:block;width:100%;height:auto;'
        f'max-width:{OEMBED_SIZE[0]}px;'
        'margin:0;padding:0;border:0" /></a>'
    )


def _enrich_oembed_document(
    document: dict[str, object],
    buyer_intent_url: str,
) -> dict[str, object]:
    title = document.get("title")
    app_store_url = document.get("_lumi_app_store_url")
    if not isinstance(title, str) or not title:
        raise ValueError("Rich oEmbed response has no title")
    if not isinstance(app_store_url, str) or not app_store_url:
        raise ValueError("Rich oEmbed response has no App Store URL")
    document.update(
        {
            "type": "rich",
            "html": rich_oembed_html(
                title,
                buyer_intent_url,
                app_store_url,
            ),
            "width": OEMBED_SIZE[0],
            "height": OEMBED_SIZE[1],
            "_lumi_buyer_intent_image_url": buyer_intent_url,
        }
    )
    return document


def oembed_document(
    title: str,
    image_url: str,
    canonical: str,
    store_url: str,
    locale: str,
    site: str = SITE,
    *,
    storefront: dict[str, object] | None = None,
    buyer_intent_url: str | None = None,
) -> dict[str, object]:
    campaign_store_url = _campaign_store_url(
        store_url,
        _oembed_campaign(locale),
    )
    document: dict[str, object] = {
        "version": "1.0",
        "type": "link",
        "title": title,
        "author_name": "Lumi Studio",
        "author_url": f"{site}/about.html",
        "provider_name": "iOS App Guide",
        "provider_url": f"{site}/index.html",
        "cache_age": 86400,
        "thumbnail_url": image_url,
        "thumbnail_width": CARD_SIZE[0],
        "thumbnail_height": CARD_SIZE[1],
        "_lumi_locale": locale,
        "_lumi_guide_url": canonical,
        "_lumi_app_store_url": campaign_store_url,
    }
    if storefront is not None:
        document.update(
            {
                "_lumi_app_store_price": storefront["price"],
                "_lumi_app_store_currency": storefront["currency"],
                "_lumi_app_store_formatted_price": storefront[
                    "formatted_price"
                ],
            }
        )
        if _has_social_rating(storefront):
            document["_lumi_app_store_rating"] = storefront["rating_value"]
            document["_lumi_app_store_rating_count"] = storefront[
                "rating_count"
            ]
    if buyer_intent_url is not None:
        _enrich_oembed_document(document, buyer_intent_url)
    return document


def primary_image_schema(
    title: str,
    description: str,
    canonical: str,
    image_url: str,
    image_alt: str,
    locale: str,
) -> dict[str, object]:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{canonical}#webpage",
        "url": canonical,
        "name": title,
        "description": description,
        "inLanguage": locale,
        "primaryImageOfPage": {
            "@type": "ImageObject",
            "@id": f"{image_url}#primaryimage",
            "contentUrl": image_url,
            "url": image_url,
            "width": CARD_SIZE[0],
            "height": CARD_SIZE[1],
            "encodingFormat": "image/jpeg",
            "caption": image_alt,
            "representativeOfPage": True,
        },
    }


def _json_ld(document: dict[str, object]) -> str:
    return json.dumps(
        document, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")


def _hero_store_url(store_url: str) -> str:
    return _campaign_store_url(store_url, "iag_hero")


def hero_block(
    key: str,
    app_name: str,
    store_url: str,
    site: str = SITE,
) -> str:
    image_url = f"{site}/social/img/{key}-share.jpg"
    image_alt = f"{app_name} iOS app guide preview"
    esc = lambda value: html.escape(str(value), quote=True)
    return "\n".join(
        (
            HERO_START,
            '<figure class="iag-app-preview">',
            (
                f'  <a class="iag-app-preview__link" '
                f'href="{esc(_hero_store_url(store_url))}" '
                f'aria-label="{esc(f"View {app_name} on the App Store")}">'
            ),
            (
                f'    <img class="iag-app-preview__image" '
                f'src="{esc(image_url)}" alt="{esc(image_alt)}" '
                f'width="{CARD_SIZE[0]}" height="{CARD_SIZE[1]}" '
                'loading="eager" decoding="async" fetchpriority="high">'
            ),
            "  </a>",
            "</figure>",
            HERO_END,
        )
    )


def metadata_block(
    key: str,
    title: str,
    description: str,
    canonical: str,
    app_name: str,
    site: str = SITE,
    *,
    locale: str = "en-US",
    endpoint_locale: str | None = None,
    image_alt: str | None = None,
    storefront: dict[str, object] | None = None,
) -> str:
    image_url = f"{site}/social/img/{key}-share.jpg"
    embed_url = oembed_url(key, canonical, site, endpoint_locale)
    image_alt = image_alt or f"{app_name} iOS app guide preview"
    schema = primary_image_schema(
        title,
        description,
        canonical,
        image_url,
        image_alt,
        locale,
    )
    social_description = _social_description(description, storefront)
    og_type = "product" if storefront is not None else "website"
    esc = lambda value: html.escape(str(value), quote=True)
    lines = [
        BLOCK_START,
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:url" content="{esc(canonical)}">',
        f'<meta property="og:image" content="{esc(image_url)}">',
        f'<meta property="og:image:secure_url" content="{esc(image_url)}">',
        '<meta property="og:image:type" content="image/jpeg">',
        f'<meta property="og:image:width" content="{CARD_SIZE[0]}">',
        f'<meta property="og:image:height" content="{CARD_SIZE[1]}">',
        f'<meta property="og:image:alt" content="{esc(image_alt)}">',
        f'<meta property="og:description" content="{esc(social_description)}">',
        f'<meta property="og:locale" content="{esc(_open_graph_locale(locale))}">',
        '<meta property="og:site_name" content="iOS App Guide">',
    ]
    if storefront is not None:
        lines.extend(
            (
                f'<meta property="product:price:amount" '
                f'content="{esc(storefront["price"])}">',
                f'<meta property="product:price:currency" '
                f'content="{esc(storefront["currency"])}">',
                '<meta property="product:availability" content="instock">',
            )
        )
    lines.extend(
        (
            f'<meta name="robots" content="{ROBOTS_DIRECTIVE}">',
            '<script type="application/ld+json" data-iag="primary-image">',
            _json_ld(schema),
            "</script>",
            HERO_STYLE,
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{esc(title)}">',
            (
                f'<meta name="twitter:description" '
                f'content="{esc(social_description)}">'
            ),
            f'<meta name="twitter:image" content="{esc(image_url)}">',
            f'<meta name="twitter:image:alt" content="{esc(image_alt)}">',
        )
    )
    if storefront is not None:
        lines.extend(
            (
                '<meta name="twitter:label1" content="App Store">',
                f'<meta name="twitter:data1" '
                f'content="{esc(storefront["formatted_price"])}">',
            )
        )
        if _has_social_rating(storefront):
            rating = (
                f"★ {float(storefront['rating_value']):.1f}/5"
                f" · {int(storefront['rating_count'])}"
            )
            lines.extend(
                (
                    '<meta name="twitter:label2" content="★">',
                    f'<meta name="twitter:data2" content="{esc(rating)}">',
                )
            )
    lines.extend(
        (
            (
                '<link rel="alternate" type="application/json+oembed" '
                f'href="{esc(embed_url)}" title="{esc(title)}">'
            ),
            BLOCK_END,
        )
    )
    return "\n".join(lines)


def _metadata_insert_index(source: str) -> int:
    head_index = source.index("</head>")
    feed_match = gen_linkset.FEED_DISCOVERY_RE.search(source)
    if feed_match:
        head_index = min(head_index, feed_match.start())
    for anchor in (QR_STYLE_ANCHOR, DECISION_STYLE_ANCHOR):
        anchor_index = source.find(anchor)
        if 0 <= anchor_index < head_index:
            head_index = anchor_index
    return head_index


def ensure_guide(path: Path, metadata: str, hero: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source:
        raise ValueError(f"Social preview guide has no closing head: {path}")
    cleaned = HERO_RE.sub("\n", BLOCK_RE.sub("\n", source))
    if "primaryImageOfPage" in cleaned:
        raise ValueError(
            f"Guide already declares primaryImageOfPage outside generated block: {path}"
        )
    insert_index = _metadata_insert_index(cleaned)
    with_metadata = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + metadata
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    heading = H1_RE.search(with_metadata)
    body_index = with_metadata.lower().find("<body")
    if heading is None or body_index < 0 or heading.start() < body_index:
        raise ValueError(f"Social preview guide has no body h1: {path}")
    updated = (
        with_metadata[: heading.end()].rstrip()
        + "\n"
        + hero
        + "\n"
        + with_metadata[heading.end() :].lstrip()
    )
    return _write_text_if_changed(path, updated)


def ensure_metadata_page(path: Path, metadata: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source:
        raise ValueError(f"Social preview page has no closing head: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    if "primaryImageOfPage" in cleaned:
        raise ValueError(
            f"Page already declares primaryImageOfPage outside generated block: {path}"
        )
    insert_index = _metadata_insert_index(cleaned)
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + metadata
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_text_if_changed(path, updated)


def remove_generated_guide_content(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    cleaned = HERO_RE.sub("\n", BLOCK_RE.sub("\n", source))
    return source != cleaned and _write_text_if_changed(path, cleaned)


def remove_generated_metadata(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    cleaned = BLOCK_RE.sub("\n", source)
    return source != cleaned and _write_text_if_changed(path, cleaned)


def render_sitemap(paths: list[str], site: str = SITE) -> str:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for path in paths:
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = f"{site}/{path}"
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


def enrich_oembed_responses(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    changed = 0
    endpoint_count = 0
    for key in sorted(live_keys):
        for locale in ("en", *OFFICIAL_LOCALES):
            path = pages / oembed_relative_path(
                key,
                None if locale == "en" else locale,
            )
            if not path.is_file():
                raise ValueError(f"Rich oEmbed endpoint is missing: {path}")
            visual_url = _available_buyer_intent_image(
                pages,
                key,
                locale,
                site,
            )
            if visual_url is None:
                raise ValueError(
                    f"Rich oEmbed buyer-intent visual is missing: "
                    f"{locale}/{key}"
                )
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("_lumi_locale") != locale:
                raise ValueError(
                    f"Rich oEmbed locale mismatch: {path}: "
                    f"{document.get('_lumi_locale')!r}"
                )
            _enrich_oembed_document(document, visual_url)
            changed += int(
                _write_text_if_changed(
                    path,
                    json.dumps(
                        document,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
            )
            endpoint_count += 1
    return {
        "apps": len(live_keys),
        "oembed": endpoint_count,
        "changed_files": changed,
    }


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
    availability = load_storefront_availability(pages)
    details = load_storefront_details(pages)

    image_dir = pages / "social" / "img"
    oembed_dir = pages / "oembed"
    oembed_paths = [
        oembed_relative_path(record["key"]) for record in records
    ]
    expected_oembed_files = {
        pages / path for path in oembed_paths
    }
    expected_localized_pages: set[Path] = set()
    localized_metadata_pages = 0
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
                    oembed_document(
                        title,
                        image_url,
                        record["guide"],
                        record["store"],
                        "en",
                        site,
                        buyer_intent_url=_available_buyer_intent_image(
                            pages,
                            key,
                            "en",
                            site,
                        ),
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
        )
        changed += int(
            ensure_guide(
                guide_path,
                metadata_block(
                    key,
                    title,
                    description,
                    record["guide"],
                    record["name"],
                    site,
                ),
                hero_block(key, record["name"], record["store"], site),
            )
        )
        for locale in OFFICIAL_LOCALES:
            app_id = str(APPSTORE[key])
            canonical = f"{site}/{locale}/{key}.html"
            localized_path = pages / locale / f"{key}.html"
            storefront = _storefront_detail(
                app_id,
                locale,
                availability,
                details,
            )
            localized_store_url = verified_app_store_url(
                f"https://apps.apple.com/app/id{app_id}",
                locale,
                availability,
            )
            expected_localized_pages.add(localized_path)
            localized_title, localized_description = _guide_metadata(
                localized_path,
                canonical,
            )
            relative_oembed = oembed_relative_path(key, locale)
            oembed_paths.append(relative_oembed)
            expected_oembed_files.add(pages / relative_oembed)
            changed += int(
                _write_text_if_changed(
                    pages / relative_oembed,
                    json.dumps(
                        oembed_document(
                            localized_title,
                            image_url,
                            canonical,
                            localized_store_url,
                            locale,
                            site,
                            storefront=storefront,
                            buyer_intent_url=_available_buyer_intent_image(
                                pages,
                                key,
                                locale,
                                site,
                            ),
                        ),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                )
            )
            changed += int(
                ensure_metadata_page(
                    localized_path,
                    metadata_block(
                        key,
                        localized_title,
                        localized_description,
                        canonical,
                        record["name"],
                        site,
                        locale=locale,
                        endpoint_locale=locale,
                        image_alt=localized_title,
                        storefront=storefront,
                    ),
                )
            )
            localized_metadata_pages += 1

    live_key_set = set(keys)
    guides_dir = pages / "guides"
    for stale in guides_dir.glob("*.html") if guides_dir.is_dir() else ():
        if stale.stem not in live_key_set:
            changed += int(remove_generated_guide_content(stale))
    for locale in OFFICIAL_LOCALES:
        localized_dir = pages / locale
        for stale in (
            localized_dir.glob("*.html")
            if localized_dir.is_dir()
            else ()
        ):
            if stale not in expected_localized_pages:
                changed += int(remove_generated_metadata(stale))
    for stale in image_dir.glob("*-share.jpg") if image_dir.is_dir() else ():
        if stale.name.removesuffix("-share.jpg") not in live_key_set:
            stale.unlink()
            changed += 1
    for stale in oembed_dir.rglob("*.json") if oembed_dir.is_dir() else ():
        if stale not in expected_oembed_files:
            stale.unlink()
            changed += 1
    for directory in sorted(
        (path for path in oembed_dir.glob("*") if path.is_dir()),
        reverse=True,
    ):
        if not any(directory.iterdir()):
            directory.rmdir()

    changed += int(
        _write_text_if_changed(
            pages / "sitemap_oembed.xml", render_sitemap(oembed_paths, site)
        )
    )
    return {
        "apps": len(records),
        "cards": len(records),
        "oembed": len(oembed_paths),
        "metadata_pages": len(records),
        "localized_metadata_pages": localized_metadata_pages,
        "hero_pages": len(records),
        "changed_files": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=Path, default=PAGES, help="Alternate Pages checkout."
    )
    parser.add_argument(
        "--oembed-only",
        action="store_true",
        help="Enrich existing oEmbed responses after buyer-intent visuals.",
    )
    args = parser.parse_args()
    if args.oembed_only:
        result = enrich_oembed_responses(args.pages)
        print(
            "Rich oEmbed: "
            f"{result['apps']} apps, {result['oembed']} responses, "
            f"{result['changed_files']} files updated"
        )
        return
    result = generate(args.pages)
    print(
        "Social previews: "
        f"{result['apps']} apps, {result['cards']} cards, "
        f"{result['oembed']} oEmbed responses, "
        f"{result['metadata_pages']} metadata pages, "
        f"{result['localized_metadata_pages']} localized metadata pages, "
        f"{result['hero_pages']} visible hero pages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
