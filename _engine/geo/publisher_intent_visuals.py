#!/usr/bin/env python3
"""Generate localized visual buyer-intent cards for every verified live app."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

from app_store_storefronts import (
    campaign_app_store_url,
    normalize_app_store_campaign_url,
    validated_app_store_url,
)
from gen_feed import feed_discovery_links, render_feed_discovery
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog as catalog
import sync_standard_site
from site_config import PUBLIC_SITE  # noqa: E402


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE",
    PUBLIC_SITE,
).rstrip("/")
SLUG = "lumi-studio-publisher-intent-visuals"
MANIFEST_NAME = f"{SLUG}.json"
SITEMAP_NAME = "sitemap_intent_visuals.xml"
LICENSE_URL = catalog.LICENSE_URL
CARD_WIDTH = 1200
CARD_HEIGHT = 630
EXPECTED_IMAGE_COUNT = (
    catalog.EXPECTED_APP_COUNT * catalog.EXPECTED_LOCALE_COUNT
)
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"
KEY_RE = re.compile(r"[a-z0-9]+")
TODAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
PALETTES = (
    ("#111827", "#312e81", "#8b5cf6"),
    ("#102a43", "#035388", "#38bdf8"),
    ("#132a13", "#31572c", "#80b918"),
    ("#3f0d12", "#7f1d1d", "#fb7185"),
    ("#2e1065", "#701a75", "#e879f9"),
    ("#172554", "#1e3a8a", "#60a5fa"),
    ("#134e4a", "#115e59", "#2dd4bf"),
)


def write_text_if_changed(path: Path, content: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _final_gallery_content(path: Path, content: str) -> str:
    try:
        previous = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        previous = ""
    if previous:
        content = sync_standard_site.preserve_managed_links(
            previous,
            content,
            label=str(path),
        )
    return render_feed_discovery(content)


def write_gallery_if_changed(path: Path, content: str) -> bool:
    return write_text_if_changed(
        path,
        _final_gallery_content(path, content),
    )


def visual_campaign_token(locale: str) -> str:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported visual locale: {locale}")
    token = f"iag_visual_{locale.replace('-', '_').lower()}"
    if len(token) > 30 or not re.fullmatch(r"[a-z0-9_]+", token):
        raise ValueError(f"Invalid visual campaign token: {token}")
    return token


def visual_store_url(record: dict[str, Any]) -> str:
    locale = str(record["locale"])
    app_id = str(record["app_store_id"])
    source = normalize_app_store_campaign_url(
        str(record["app_store_url"])
    )
    validated_app_store_url(source, expected_app_id=app_id)
    return campaign_app_store_url(source, visual_campaign_token(locale))


def visual_relative_path(locale: str, key: str) -> str:
    if locale not in OFFICIAL_LOCALES or KEY_RE.fullmatch(key) is None:
        raise ValueError(f"Invalid visual path: {locale}/{key}")
    return f"visuals/{locale}/{key}.svg"


def visual_url(locale: str, key: str, site: str = SITE) -> str:
    return f"{site}/{visual_relative_path(locale, key)}"


def gallery_relative_path(locale: str) -> str:
    if locale == "en":
        return "visuals/index.html"
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported gallery locale: {locale}")
    return f"{locale}/visuals/index.html"


def gallery_url(locale: str, site: str = SITE) -> str:
    relative = gallery_relative_path(locale)
    return f"{site}/{relative.removesuffix('index.html')}"


def _single_line(value: object) -> str:
    result = catalog.single_line(str(value))
    if not result or "\n" in result or "\r" in result:
        raise ValueError("Visual text must be a non-empty single line")
    return result


def _palette(key: str) -> tuple[str, str, str]:
    digest = hashlib.sha256(key.encode("ascii")).digest()
    return PALETTES[digest[0] % len(PALETTES)]


def _display_weight(value: str) -> float:
    weight = 0.0
    for character in value:
        category = unicodedata.category(character)
        if category.startswith("M"):
            continue
        if character.isspace():
            weight += 0.45
        elif unicodedata.east_asian_width(character) in {"F", "W"}:
            weight += 1.75
        else:
            weight += 1.2
    return max(weight, 1.0)


def _fitted_size(
    value: str,
    *,
    maximum: int,
    minimum: int,
    width: int,
) -> int:
    estimated = width / (_display_weight(value) * 0.58)
    return max(minimum, min(maximum, int(estimated)))


def _render_width(value: str, size: int) -> float:
    advance = 0.0
    for character in value:
        codepoint = ord(character)
        category = unicodedata.category(character)
        if category.startswith("M"):
            continue
        if character.isspace():
            advance += 0.4
        elif unicodedata.east_asian_width(character) in {"F", "W"}:
            advance += 1.0
        elif (
            0x0900 <= codepoint <= 0x0D7F
            or 0x0E00 <= codepoint <= 0x0E7F
        ):
            advance += 0.95
        elif (
            0x0600 <= codepoint <= 0x06FF
            or 0x0750 <= codepoint <= 0x077F
            or 0x08A0 <= codepoint <= 0x08FF
            or 0xFB50 <= codepoint <= 0xFDFF
            or 0xFE70 <= codepoint <= 0xFEFF
        ):
            advance += 0.75
        elif 0x0590 <= codepoint <= 0x05FF:
            advance += 0.72
        else:
            advance += 0.68
    return max(advance * size, 1.0)


def _text_node(
    value: str,
    *,
    x: int,
    y: int,
    size: int,
    width: int,
    anchor: str,
    css_class: str,
    direction: str | None = None,
) -> str:
    rendered_width = _render_width(value, size)
    fit = ""
    if rendered_width > width:
        scale = width / rendered_width
        fit = (
            f' transform="translate({x} 0) scale({scale:.4f} 1) '
            f'translate({-x} 0)"'
        )
    direction_attribute = f' direction="{direction}"' if direction else ""
    return (
        f'<text class="{css_class}" x="{x}" y="{y}" '
        f'font-size="{size}" text-anchor="{anchor}"'
        f"{direction_attribute}{fit}>"
        f"{html.escape(value)}</text>"
    )


def render_svg(
    record: dict[str, Any],
    purchase_label: str,
    site: str = SITE,
) -> str:
    locale = _single_line(record["locale"])
    key = _single_line(record["app_key"])
    if locale not in OFFICIAL_LOCALES or KEY_RE.fullmatch(key) is None:
        raise ValueError(f"Invalid visual record: {locale}/{key}")
    app_name = _single_line(record["app_name"])
    query = _single_line(record["publisher_query"])
    context = _single_line(record["decision_context"])
    purchase = _single_line(purchase_label)
    app_id = _single_line(record["app_store_id"])
    rtl = locale in catalog.RTL_LOCALES
    app_anchor = "end" if rtl else "start"
    body_anchor = "start"
    text_x = 1100 if rtl else 400
    body_x = 1100 if rtl else 100
    start, end, accent = _palette(key)
    query_size = _fitted_size(
        query,
        maximum=54,
        minimum=24,
        width=1000,
    )
    context_size = _fitted_size(
        context,
        maximum=31,
        minimum=16,
        width=1000,
    )
    app_size = _fitted_size(
        app_name,
        maximum=48,
        minimum=26,
        width=700,
    )
    purchase_size = _fitted_size(
        purchase,
        maximum=25,
        minimum=16,
        width=700,
    )
    icon_url = f"{site}/stories/img/{key}-icon.jpg"
    metadata = html.escape(
        json.dumps(
            {
                "creator": "Lumi Studio",
                "license": LICENSE_URL,
                "locale": locale,
                "app_store_id": app_id,
                "publisher_authored": True,
                "measured_search_volume": False,
                "is_ranking": False,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return "\n".join(
        (
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
                f'viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" '
                f'role="img" aria-labelledby="title description" '
                f'xml:lang="{html.escape(locale, quote=True)}" '
                f'direction="{"rtl" if rtl else "ltr"}">'
            ),
            f"<title id=\"title\">{html.escape(query)}</title>",
            (
                f'<desc id="description">{html.escape(context)} '
                f'{html.escape(purchase)}</desc>'
            ),
            "<defs>",
            (
                '<linearGradient id="background" x1="0" y1="0" '
                'x2="1" y2="1">'
            ),
            f'<stop offset="0" stop-color="{start}"/>',
            f'<stop offset="0.62" stop-color="{end}"/>',
            f'<stop offset="1" stop-color="{accent}"/>',
            "</linearGradient>",
            (
                '<radialGradient id="glow" cx="0.84" cy="0.12" r="0.72">'
                '<stop offset="0" stop-color="#ffffff" stop-opacity="0.28"/>'
                '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
                "</radialGradient>"
            ),
            (
                '<filter id="shadow" x="-30%" y="-30%" width="160%" '
                'height="180%"><feDropShadow dx="0" dy="18" stdDeviation="20" '
                'flood-color="#020617" flood-opacity="0.42"/></filter>'
            ),
            (
                '<clipPath id="iconClip"><rect x="92" y="78" width="244" '
                'height="244" rx="56"/></clipPath>'
            ),
            "</defs>",
            (
                f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="42" '
                'fill="url(#background)"/>'
            ),
            (
                f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="42" '
                'fill="url(#glow)"/>'
            ),
            (
                '<circle cx="1080" cy="560" r="280" fill="none" '
                'stroke="#ffffff" stroke-opacity="0.11" stroke-width="90"/>'
            ),
            (
                '<rect x="68" y="54" width="1092" height="522" rx="36" '
                'fill="#020617" fill-opacity="0.2" stroke="#ffffff" '
                'stroke-opacity="0.22"/>'
            ),
            (
                '<rect x="92" y="78" width="244" height="244" rx="56" '
                'fill="#ffffff" fill-opacity="0.16" filter="url(#shadow)"/>'
            ),
            (
                f'<image href="{html.escape(icon_url, quote=True)}" '
                f'xlink:href="{html.escape(icon_url, quote=True)}" '
                'x="92" y="78" width="244" height="244" '
                'preserveAspectRatio="xMidYMid slice" '
                'clip-path="url(#iconClip)"/>'
            ),
            (
                '<rect x="948" y="82" width="154" height="48" rx="24" '
                'fill="#ffffff" fill-opacity="0.16" stroke="#ffffff" '
                'stroke-opacity="0.2"/>'
            ),
            (
                f'<text x="1025" y="114" text-anchor="middle" '
                f'font-size="21" font-weight="700" fill="#ffffff" '
                f'direction="ltr">'
                f"{html.escape(locale)}</text>"
            ),
            _text_node(
                app_name,
                x=text_x,
                y=188,
                size=app_size,
                width=700,
                anchor=app_anchor,
                css_class="app-name",
                direction="ltr" if rtl else None,
            ),
            (
                f'<text x="{text_x}" y="238" text-anchor="{app_anchor}" '
                'font-size="23" font-weight="650" fill="#e2e8f0" '
                'direction="ltr">'
                f"App Store ID {html.escape(app_id)}</text>"
            ),
            _text_node(
                query,
                x=body_x,
                y=392,
                size=query_size,
                width=1000,
                anchor=body_anchor,
                css_class="query",
            ),
            _text_node(
                context,
                x=body_x,
                y=457,
                size=context_size,
                width=1000,
                anchor=body_anchor,
                css_class="context",
            ),
            (
                '<line x1="100" y1="498" x2="1100" y2="498" '
                'stroke="#ffffff" stroke-opacity="0.22"/>'
            ),
            _text_node(
                purchase,
                x=body_x,
                y=548,
                size=purchase_size,
                width=700,
                anchor=body_anchor,
                css_class="purchase-model",
            ),
            (
                '<text x="1100" y="548" text-anchor="end" font-size="25" '
                'font-weight="800" fill="#ffffff">App Store</text>'
                if not rtl
                else (
                    '<text x="100" y="548" text-anchor="start" font-size="25" '
                    'font-weight="800" fill="#ffffff" direction="ltr">'
                    'App Store</text>'
                )
            ),
            (
                '<text x="100" y="604" font-size="18" font-weight="650" '
                'fill="#cbd5e1" direction="ltr">Lumi Studio</text>'
            ),
            f"<metadata>{metadata}</metadata>",
            "<style>",
            (
                "text{font-family:-apple-system,BlinkMacSystemFont,"
                "'Segoe UI','Noto Sans','Noto Sans CJK TC',sans-serif;"
                "unicode-bidi:plaintext}"
            ),
            (
                ".app-name{font-weight:850;fill:#fff}"
                ".query{font-weight:820;fill:#fff}"
                ".context{font-weight:560;fill:#e2e8f0}"
                ".purchase-model{font-weight:700;fill:#fff}"
            ),
            "</style>",
            "</svg>",
            "",
        )
    )


def _alternates(site: str = SITE) -> str:
    links = [
        f'<link rel="alternate" hreflang="en" href="{site}/visuals/">'
    ]
    links.extend(
        f'<link rel="alternate" hreflang="{locale}" '
        f'href="{site}/{locale}/visuals/">'
        for locale in OFFICIAL_LOCALES
    )
    links.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{site}/visuals/">'
    )
    return "\n".join(links)


def _gallery_schema(
    locale: str,
    canonical: str,
    records: list[dict[str, Any]],
    purchase_labels: dict[str, str],
    purchase_name: str,
    modified: str,
    site: str = SITE,
) -> dict[str, Any]:
    asset_locale = str(records[0]["locale"])
    return {
        "@context": "https://schema.org",
        "@type": "ImageGallery",
        "@id": f"{canonical}#gallery",
        "url": canonical,
        "name": records[0]["catalog_name"],
        "description": records[0]["catalog_description"],
        "inLanguage": locale,
        "isAccessibleForFree": True,
        "license": LICENSE_URL,
        "dateModified": modified,
        "creator": {
            "@type": "Organization",
            "@id": f"{site}/#organization",
            "name": "Lumi Studio",
            "url": site,
        },
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(records),
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "item": {
                        "@type": "ImageObject",
                        "contentUrl": visual_url(
                            asset_locale,
                            str(record["app_key"]),
                            site,
                        ),
                        "encodingFormat": "image/svg+xml",
                        "width": CARD_WIDTH,
                        "height": CARD_HEIGHT,
                        "caption": record["publisher_query"],
                        "description": record["decision_context"],
                        "license": LICENSE_URL,
                        "about": {
                            "@type": "MobileApplication",
                            "name": record["app_name"],
                            "operatingSystem": "iOS",
                            "identifier": {
                                "@type": "PropertyValue",
                                "propertyID": "App Store ID",
                                "value": record["app_store_id"],
                            },
                            "url": record["canonical_guide_url"],
                            "downloadUrl": visual_store_url(record),
                            "additionalProperty": {
                                "@type": "PropertyValue",
                                "name": purchase_name,
                                "value": purchase_labels[
                                    str(record["purchase_model"])
                                ],
                            },
                        },
                    },
                }
                for position, record in enumerate(records, start=1)
            ],
        },
    }


def render_gallery(
    locale: str,
    records: list[dict[str, Any]],
    ui: dict[str, str],
    modified: str,
    site: str = SITE,
) -> str:
    if not records:
        raise ValueError(f"No visual records for {locale}")
    asset_locale = str(records[0]["locale"])
    if any(str(record["locale"]) != asset_locale for record in records):
        raise ValueError(f"Mixed visual record locales for {locale}")
    ui = catalog.dynamic_ui(ui)
    purchase_labels = {
        model: _single_line(ui[source])
        for model, source in catalog.PURCHASE_LABELS.items()
    }
    canonical = gallery_url(locale, site)
    records_with_catalog = [
        {
            **record,
            "catalog_name": ui[catalog.NAME],
            "catalog_description": ui[catalog.DESCRIPTION],
        }
        for record in records
    ]
    schema = json.dumps(
        _gallery_schema(
            locale,
            canonical,
            records_with_catalog,
            purchase_labels,
            _single_line(ui["Purchase model"]),
            modified,
            site,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    cards = []
    for record in records:
        key = str(record["app_key"])
        query = _single_line(record["publisher_query"])
        context = _single_line(record["decision_context"])
        app_name = _single_line(record["app_name"])
        image = visual_url(asset_locale, key, site)
        store = visual_store_url(record)
        guide = _single_line(record["canonical_guide_url"])
        purchase = purchase_labels[str(record["purchase_model"])]
        cards.append(
            "".join(
                (
                    '<article class="visual-card">',
                    (
                        f'<a class="visual-link" rel="nofollow noopener" '
                        f'href="{html.escape(store, quote=True)}" '
                        f'aria-label="{html.escape(str(record["app_store_cta_label"]), quote=True)}">'
                    ),
                    (
                        f'<img src="{html.escape(image, quote=True)}" '
                        f'alt="{html.escape(query, quote=True)}" '
                        f'title="{html.escape(context, quote=True)}" '
                        f'width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
                        'loading="lazy" decoding="async">'
                    ),
                    "</a>",
                    f"<h2>{html.escape(app_name)}</h2>",
                    (
                        f'<p class="query" title="{html.escape(query, quote=True)}">'
                        f"{html.escape(query)}</p>"
                    ),
                    (
                        f'<p class="context" title="{html.escape(context, quote=True)}">'
                        f"{html.escape(context)}</p>"
                    ),
                    '<div class="actions">',
                    f'<span class="purchase">{html.escape(purchase)}</span>',
                    (
                        f'<a href="{html.escape(guide, quote=True)}">'
                        f'{html.escape(ui["Guide"])}</a>'
                    ),
                    (
                        f'<a rel="nofollow noopener" '
                        f'href="{html.escape(store, quote=True)}">'
                        f'{html.escape(str(record["app_store_cta_label"]))}</a>'
                    ),
                    "</div>",
                    "</article>",
                )
            )
        )
    direction = ' dir="rtl"' if asset_locale in catalog.RTL_LOCALES else ""
    root_prefix = "" if locale == "en" else f"/{locale}"
    return f"""<!doctype html>
<html lang="{html.escape(locale)}"{direction}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="content-modified" content="{html.escape(modified)}">
<title>{html.escape(ui[catalog.NAME])}</title>
<meta name="description" content="{html.escape(ui[catalog.DESCRIPTION], quote=True)}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
{_alternates(site)}
<link rel="alternate" type="application/json" href="{site}/data/{MANIFEST_NAME}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(ui[catalog.NAME], quote=True)}">
<meta property="og:description" content="{html.escape(ui[catalog.DESCRIPTION], quote=True)}">
<meta property="og:url" content="{html.escape(canonical, quote=True)}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#171b28;--sub:#5c6476;--line:#e2e6ee;--brand:#5546c8;--bg:#f7f8fc;--card:#fff}}
*{{box-sizing:border-box}}
html,body{{margin:0;min-width:100%;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",sans-serif}}
a{{color:var(--brand);text-decoration-thickness:1px;text-underline-offset:3px}}
.wrap{{width:100%;padding:28px clamp(18px,4vw,54px) 64px}}
h1,h2,p,a,span,strong{{white-space:nowrap}}
h1{{margin:16px 0 8px;overflow:hidden;text-overflow:ellipsis;font-size:clamp(28px,4vw,46px);line-height:1.15}}
.lead,.disclosure{{margin:0 0 16px;overflow-x:auto;color:var(--sub)}}
.crumb{{overflow-x:auto;color:var(--sub);font-size:13px;white-space:nowrap}}
.badges,.actions{{display:flex;min-width:0;gap:8px;align-items:center;overflow-x:auto}}
.badge,.purchase,.actions a{{display:inline-flex;flex:0 0 auto;border:1px solid var(--line);border-radius:999px;background:var(--card);padding:7px 12px;font-size:13px;font-weight:700;text-decoration:none}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,31rem),1fr));gap:18px;margin-top:22px}}
.visual-card{{min-width:0;overflow:hidden;border:1px solid var(--line);border-radius:22px;background:var(--card);box-shadow:0 12px 34px rgba(34,37,59,.07)}}
.visual-link{{display:block;overflow:hidden;background:#111827;line-height:0}}
.visual-link img{{display:block;width:100%;height:auto;aspect-ratio:1200/630;object-fit:cover}}
.visual-card h2,.visual-card p,.actions{{margin-inline:18px}}
.visual-card h2{{margin-block:16px 4px;overflow:hidden;text-overflow:ellipsis;font-size:20px}}
.visual-card p{{margin-block:4px;overflow:hidden;text-overflow:ellipsis}}
.query{{font-weight:760}}
.context{{color:var(--sub)}}
.actions{{margin-block:14px 18px}}
.actions a:last-child{{color:#fff;background:linear-gradient(135deg,#6557de,#4f41bb)}}
.footer{{margin-top:24px;overflow-x:auto;color:var(--sub);font-size:13px}}
@media(max-width:34rem){{.wrap{{padding-inline:14px}}.grid{{gap:14px}}}}
</style>
{feed_discovery_links()}
</head>
<body>
<main class="wrap">
<div class="crumb"><a href="{site}{root_prefix}/index.html">{html.escape(ui["Home"])}</a> · <a href="{site}{root_prefix}/data/{catalog.SLUG}.html">{html.escape(ui["Open data"])}</a></div>
<h1>{html.escape(ui[catalog.NAME])}</h1>
<p class="lead">{html.escape(ui[catalog.LEAD])}</p>
<div class="badges"><span class="badge">{html.escape(ui["1,300 records: 26 apps × 50 locales."])}</span><span class="badge">{html.escape(ui["First-party publisher catalog"])}</span><span class="badge">{html.escape(ui["Not measured search volume"])}</span></div>
<p class="disclosure">{html.escape(ui[catalog.DISCLOSURE])} {html.escape(ui[catalog.NON_MEASURED])}</p>
<section class="grid">{"".join(cards)}</section>
<p class="footer">{html.escape(ui["Alphabetical by app name — never a ranking."])} · {html.escape(ui["License"])}: <a href="{LICENSE_URL}">CC BY 4.0</a> · {html.escape(ui["Updated"])} {html.escape(modified)}</p>
</main>
</body>
</html>
"""


def _manifest_record(
    record: dict[str, Any],
    svg: str,
    site: str = SITE,
) -> dict[str, Any]:
    locale = str(record["locale"])
    key = str(record["app_key"])
    return {
        "locale": locale,
        "app_key": key,
        "app_store_id": str(record["app_store_id"]),
        "image_url": visual_url(locale, key, site),
        "gallery_url": gallery_url(locale, site),
        "canonical_guide_url": str(record["canonical_guide_url"]),
        "app_store_url": visual_store_url(record),
        "sha256": hashlib.sha256(svg.encode("utf-8")).hexdigest(),
    }


def _gallery_manifest_record(
    locale: str,
    source: str,
    site: str = SITE,
) -> dict[str, str]:
    return {
        "locale": locale,
        "gallery_url": gallery_url(locale, site),
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }


def _content_digest(records: list[dict[str, Any]]) -> str:
    fields = (
        "locale",
        "app_key",
        "app_name",
        "app_store_id",
        "publisher_query",
        "decision_context",
        "purchase_model",
        "canonical_guide_url",
        "app_store_url",
    )
    compact = [
        {field: record[field] for field in fields}
        for record in records
    ]
    return hashlib.sha256(
        json.dumps(
            compact,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _generation_digest(content_digest: str) -> str:
    digest = hashlib.sha256()
    digest.update(content_digest.encode("ascii"))
    digest.update(catalog.I18N_PATH.read_bytes())
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()


def _stable_modified(
    path: Path,
    generation_digest: str,
    today: str,
) -> str:
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return today
    value = previous.get("dateModified")
    if (
        previous.get("generation_digest") == generation_digest
        and isinstance(value, str)
        and TODAY_RE.fullmatch(value)
        and value <= today
    ):
        return value
    return today


def render_sitemap(
    records_by_locale: dict[str, list[dict[str, Any]]],
    modified: str,
    site: str = SITE,
) -> str:
    if TODAY_RE.fullmatch(modified) is None:
        raise ValueError(f"Invalid visual sitemap date: {modified}")
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("image", IMAGE_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    gallery_locales = ("en", *OFFICIAL_LOCALES)
    for gallery_locale in gallery_locales:
        asset_locale = "en-US" if gallery_locale == "en" else gallery_locale
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = gallery_url(
            gallery_locale,
            site,
        )
        ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = modified
        for record in records_by_locale[asset_locale]:
            image = ET.SubElement(url, f"{{{IMAGE_NS}}}image")
            ET.SubElement(image, f"{{{IMAGE_NS}}}loc").text = visual_url(
                asset_locale,
                str(record["app_key"]),
                site,
            )
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def validate_icons(pages: Path, app_keys: Iterable[str]) -> None:
    invalid = []
    for key in sorted(str(value) for value in app_keys):
        if KEY_RE.fullmatch(key) is None:
            raise ValueError(f"Invalid visual app key: {key}")
        icon = pages / "stories" / "img" / f"{key}-icon.jpg"
        try:
            valid = icon.is_file() and icon.stat().st_size > 0
        except OSError:
            valid = False
        if not valid:
            invalid.append(icon)
    if invalid:
        joined = ", ".join(str(path) for path in invalid)
        raise ValueError(f"Publisher visual icons are missing or empty: {joined}")


def build(
    pages: Path = PAGES,
    today: str | None = None,
    site: str = SITE,
) -> dict[str, int]:
    today = today or datetime.now(timezone.utc).date().isoformat()
    if TODAY_RE.fullmatch(today) is None:
        raise ValueError(f"Invalid build date: {today}")
    records, apps = catalog.build_records(pages)
    if len(records) != EXPECTED_IMAGE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_IMAGE_COUNT} visual records, got {len(records)}"
        )
    validate_icons(pages, apps)
    ui_i18n = catalog.load_ui_i18n()
    records_by_locale = {
        locale: [
            record for record in records if record["locale"] == locale
        ]
        for locale in OFFICIAL_LOCALES
    }
    for locale, localized in records_by_locale.items():
        if len(localized) != catalog.EXPECTED_APP_COUNT:
            raise ValueError(
                f"Incomplete visual app coverage: {locale}={len(localized)}"
            )

    content_digest = _content_digest(records)
    generation_digest = _generation_digest(content_digest)
    manifest_path = pages / "data" / MANIFEST_NAME
    source_dataset_path = pages / "data" / f"{catalog.SLUG}.json"
    source_digest = hashlib.sha256(source_dataset_path.read_bytes()).hexdigest()
    modified = _stable_modified(manifest_path, generation_digest, today)
    manifest_records: list[dict[str, Any]] = []
    changed = 0
    expected_images: set[Path] = set()
    for locale in OFFICIAL_LOCALES:
        ui = catalog.dynamic_ui(ui_i18n[locale])
        purchase_labels = {
            model: _single_line(ui[source])
            for model, source in catalog.PURCHASE_LABELS.items()
        }
        for record in records_by_locale[locale]:
            svg = render_svg(
                record,
                purchase_labels[str(record["purchase_model"])],
                site,
            )
            target = pages / visual_relative_path(
                locale,
                str(record["app_key"]),
            )
            expected_images.add(target)
            changed += int(write_text_if_changed(target, svg))
            manifest_records.append(_manifest_record(record, svg, site))

    visuals_root = pages / "visuals"
    for stale in visuals_root.glob("*/*.svg") if visuals_root.is_dir() else ():
        if stale not in expected_images:
            stale.unlink()
            changed += 1

    manifest_galleries: list[dict[str, str]] = []
    root_records = records_by_locale["en-US"]
    root_gallery_path = pages / gallery_relative_path("en")
    root_gallery_source = _final_gallery_content(
        root_gallery_path,
        render_gallery(
            "en",
            root_records,
            ui_i18n["en-US"],
            modified,
            site,
        ),
    )
    changed += int(
        write_text_if_changed(root_gallery_path, root_gallery_source)
    )
    manifest_galleries.append(
        _gallery_manifest_record("en", root_gallery_source, site)
    )
    for locale in OFFICIAL_LOCALES:
        gallery_path = pages / gallery_relative_path(locale)
        gallery_source = _final_gallery_content(
            gallery_path,
            render_gallery(
                locale,
                records_by_locale[locale],
                ui_i18n[locale],
                modified,
                site,
            ),
        )
        changed += int(
            write_text_if_changed(gallery_path, gallery_source)
        )
        manifest_galleries.append(
            _gallery_manifest_record(locale, gallery_source, site)
        )

    manifest = {
        "name": "Lumi Studio Publisher Intent Visuals",
        "description": (
            "Localized first-party visual buyer-intent cards for every "
            "verified live iOS app."
        ),
        "url": f"{site}/visuals/",
        "dateModified": modified,
        "license": LICENSE_URL,
        "creator": {
            "@type": "Organization",
            "name": "Lumi Studio",
            "url": site,
        },
        "source_dataset": f"{site}/data/{catalog.SLUG}.json",
        "source_sha256": source_digest,
        "content_digest": content_digest,
        "generation_digest": generation_digest,
        "ordering": "official_locale_order_then_alphabetical_app_name",
        "app_count": len(apps),
        "locale_count": len(OFFICIAL_LOCALES),
        "image_count": len(manifest_records),
        "gallery_count": len(OFFICIAL_LOCALES) + 1,
        "galleries": manifest_galleries,
        "publisher_authored": True,
        "measured_search_volume": False,
        "is_ranking": False,
        "app_store_link_policy": {
            "default": "clean_direct",
            "campaign_scope": "per_locale_visual",
            "campaign_requires": ["pt", "ct", "mt=8"],
        },
        "records": manifest_records,
    }
    changed += int(
        write_text_if_changed(
            manifest_path,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    )
    changed += int(
        write_text_if_changed(
            pages / SITEMAP_NAME,
            render_sitemap(records_by_locale, modified, site),
        )
    )
    result = {
        "apps": len(apps),
        "locales": len(records_by_locale),
        "images": len(manifest_records),
        "galleries": len(OFFICIAL_LOCALES) + 1,
        "changed_files": changed,
    }
    print(
        "PUBLISHER_INTENT_VISUALS "
        f"apps={result['apps']} locales={result['locales']} "
        f"images={result['images']} galleries={result['galleries']} "
        f"changed={result['changed_files']}",
        flush=True,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        type=Path,
        default=PAGES,
        help="Pages repository root.",
    )
    parser.add_argument("--today", help="Stable test/build date.")
    args = parser.parse_args()
    build(args.pages.resolve(), args.today)


if __name__ == "__main__":
    main()
