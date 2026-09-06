#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish the portfolio as a product feed an AI shopping agent already parses.

Assistants that answer "which app should I buy for X?" increasingly read the
same shape of file that shopping ingesters read: a flat JSONL feed where every
line is one purchasable thing with an id, a title, a description, a link, an
image, a price and a currency.  Our catalog, offer catalogs and install routes
each hold part of that record, but none of them is that shape, so an agent has
to join three documents before it can compare us with anything else it found.

This generator emits the join.  Field names follow the product-feed convention
those ingesters use — ``id``, ``item_group_id``, ``title``, ``description``,
``link``, ``image_link``, ``price``, ``availability``, ``brand``, ``condition``
— so a reader that already understands a shopping feed understands this file
without a bespoke schema.  Two flags say what we are and are not: every row is
``enable_search: true`` because the whole point is to be found, and every row is
``enable_checkout: false`` because an iOS app is bought from Apple and we run no
checkout of our own.  Claiming otherwise would be the one lie an agent could
act on.

Honesty constraints this file inherits from the rest of the site:
  • a row exists only for a storefront where Apple's own public lookup confirms
    the app is sold, and its price is the price that lookup returned;
  • the title, description and link are the localized ones the site already
    publishes, so the feed cannot drift from the pages;
  • no rating, review count, download figure or rank appears, because none of
    those is a public fact we are entitled to publish.

    python geo/agent_product_feed.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import io
import json
import os
from pathlib import Path
import html
import re
from typing import Any
import email.utils
import xml.sax.saxutils as saxutils

import app_decision_matrix
from app_store_storefronts import (
    LOCALE_STOREFRONTS,
    load_storefront_details,
    localized_storefront_detail,
    validated_app_store_url,
)
from family_travel_dataset import write_text_if_changed
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog
from site_config import PUBLIC_SITE  # noqa: E402


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE",
    PUBLIC_SITE,
).rstrip("/")
SLUG = "ios-app-agent-feed"
FEED_DIR = Path("api") / "v1" / SLUG
INDEX_RELATIVE = FEED_DIR / "index.json"
FEED_RELATIVE = FEED_DIR / "feed.jsonl"
CSV_RELATIVE = FEED_DIR / "feed.csv"
SCHEMA_RELATIVE = FEED_DIR / "feed.schema.json"
XML_RELATIVE = FEED_DIR / "feed.xml"
JSONLD_RELATIVE = FEED_DIR / "catalog.jsonld"
PAGE_RELATIVE = FEED_DIR / "index.html"
SITEMAP_RELATIVE = Path("sitemap_agent_feed.xml")
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
BRAND = "Lumi Studio"
BASE_LOCALE = "en-US"
TITLE_LIMIT = 150
DESCRIPTION_LIMIT = 5000

# Field names are the shopping-feed convention; the values are ours.
FEED_FIELDS: tuple[str, ...] = (
    "id",
    "item_group_id",
    "title",
    "description",
    "link",
    "image_link",
    "price",
    "price_value",
    "price_currency",
    "availability",
    "condition",
    "brand",
    "product_category",
    "product_type",
    "content_language",
    "shipping_country",
    "enable_search",
    "enable_checkout",
    "seller_name",
    "seller_url",
    "app_store_id",
    "app_store_url",
    "operating_system",
    "purchase_model",
    "one_time_purchase",
    "subscription",
)

OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def index_url() -> str:
    return f"{SITE}/{INDEX_RELATIVE.as_posix()}"


def feed_url() -> str:
    return f"{SITE}/{FEED_RELATIVE.as_posix()}"


def csv_url() -> str:
    return f"{SITE}/{CSV_RELATIVE.as_posix()}"


def schema_url() -> str:
    return f"{SITE}/{SCHEMA_RELATIVE.as_posix()}"


def xml_url() -> str:
    return f"{SITE}/{XML_RELATIVE.as_posix()}"


def jsonld_url() -> str:
    return f"{SITE}/{JSONLD_RELATIVE.as_posix()}"


def page_url() -> str:
    return f"{SITE}/{FEED_DIR.as_posix()}/"


def _snapshot_date(pages: Path) -> str:
    payload = json.loads(
        (pages / ".appstore_storefront_state.json").read_text(encoding="utf-8")
    )
    checked_at = payload.get("checked_at")
    value = checked_at[:10] if isinstance(checked_at, str) else ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("App Store snapshot must have a valid checked_at date")
    return value


def app_image_links(pages: Path, app_keys: set[str]) -> dict[str, str]:
    """The share image each app's own English guide page already declares."""
    images: dict[str, str] = {}
    for app_key in sorted(app_keys):
        page = pages / BASE_LOCALE / f"{app_key}.html"
        try:
            markup = page.read_text(encoding="utf-8")
        except OSError:
            continue
        match = OG_IMAGE_RE.search(markup)
        if match and match.group(1).startswith("https://"):
            images[app_key] = match.group(1)
    return images


def _clip(value: str, limit: int) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _description(app_name: str, decision_context: str) -> str:
    """The site's own localized sentence, made self-describing on its own line.

    A feed row is read without the page around it, so a context sentence that
    never names the product reads as being about something else. Naming the app
    is the only thing added; the sentence itself is still the one the offer
    catalog publishes, so the feed cannot drift from the site.
    """
    context = " ".join(str(decision_context).split())
    name = " ".join(str(app_name).split())
    if name and name.casefold() not in context.casefold():
        context = f"{name} — {context}"
    return _clip(context, DESCRIPTION_LIMIT)


def build_rows(pages: Path = PAGES) -> tuple[list[dict[str, Any]], str]:
    """One feed row per app and storefront Apple's lookup actually confirms."""
    records, apps = publisher_intent_catalog.build_records(pages)
    details = load_storefront_details(pages)
    modified = _snapshot_date(pages)
    images = app_image_links(
        pages, {str(record["app_key"]) for record in records}
    )
    category_labels = app_decision_matrix.CATEGORY_LABELS
    rows: list[dict[str, Any]] = []
    for record in sorted(
        records,
        key=lambda item: (str(item["app_key"]), str(item["locale"])),
    ):
        locale = str(record["locale"])
        app_key = str(record["app_key"])
        app_id = str(record["app_store_id"])
        country = LOCALE_STOREFRONTS[locale]
        detail = details.get(country, {}).get(app_id)
        if detail is None:
            # Apple's public lookup does not confirm the app is sold there, so
            # there is no price we are entitled to quote and no row to publish.
            continue
        localized = localized_storefront_detail(detail, locale)
        price_value = str(localized["price"])
        currency = str(localized["currency"])
        purchase_model = str(record["purchase_model"])
        row = {
            "id": f"{app_key}-{locale}",
            "item_group_id": app_key,
            "title": _clip(str(record["app_name"]), TITLE_LIMIT),
            "description": _description(
                str(record["app_name"]), str(record["decision_context"])
            ),
            "link": str(record["canonical_guide_url"]),
            "image_link": images.get(app_key, ""),
            "price": f"{price_value} {currency}",
            "price_value": price_value,
            "price_currency": currency,
            "availability": "in_stock",
            "condition": "new",
            "brand": BRAND,
            "product_category": category_labels.get(
                str(apps[app_key]["category"]), str(apps[app_key]["category"])
            ),
            "product_type": "mobile application",
            "content_language": locale,
            "shipping_country": country.upper(),
            "enable_search": True,
            "enable_checkout": False,
            "seller_name": BRAND,
            "seller_url": f"{SITE}/about.html",
            "app_store_id": app_id,
            "app_store_url": validated_app_store_url(
                str(record["app_store_url"]),
                expected_app_id=app_id,
                expected_locale=locale,
                require_campaign=True,
            ),
            "operating_system": "iOS",
            "purchase_model": purchase_model,
            "one_time_purchase": bool(record["one_time_option"]),
            "subscription": False,
        }
        if not row["image_link"]:
            del row["image_link"]
        rows.append(row)
    return rows, modified


def feed_text(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )


def csv_text(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(FEED_FIELDS),
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        flat = {}
        for field in FEED_FIELDS:
            value = row.get(field, "")
            if isinstance(value, bool):
                value = "true" if value else "false"
            flat[field] = value
        writer.writerow(flat)
    return buffer.getvalue()


def index_payload(rows: list[dict[str, Any]], modified: str) -> dict[str, Any]:
    locales = sorted({str(row["content_language"]) for row in rows})
    apps = sorted({str(row["item_group_id"]) for row in rows})
    return {
        "schema_version": 1,
        "name": "Lumi Studio verified iOS app agent product feed",
        "description": (
            "A flat product feed of every verified live Lumi Studio iOS app, "
            "one row per app and Apple storefront, using the field names AI "
            "shopping agents already parse. Search-only: apps are purchased "
            "on the Apple App Store, so no row offers checkout here."
        ),
        "field_convention": (
            "Product-feed field naming as used by AI shopping ingesters "
            "(id, item_group_id, title, description, link, image_link, price, "
            "availability, brand, condition). This feed is published for "
            "reading; it is not submitted to any merchant checkout programme."
        ),
        "url": index_url(),
        "feed_url": feed_url(),
        "csv_url": csv_url(),
        "schema_url": schema_url(),
        "license": LICENSE_URL,
        "dateModified": modified,
        "publisher": {"name": BRAND, "url": f"{SITE}/about.html"},
        "publisher_disclosure": (
            "First-party feed published by Lumi Studio, the developer of every "
            "listed app; not an independent ranking or a marketplace."
        ),
        "enable_search": True,
        "enable_checkout": False,
        "checkout_note": (
            "Purchase happens on the Apple App Store via app_store_url; this "
            "publisher operates no checkout endpoint."
        ),
        "price_source": "Apple App Store public lookup snapshot",
        "row_count": len(rows),
        "app_count": len(apps),
        "locale_count": len(locales),
        "official_locale_count": len(OFFICIAL_LOCALES),
        "locales": locales,
        "app_keys": apps,
        "fields": list(FEED_FIELDS),
        "content_digest": "sha256:"
        + hashlib.sha256(feed_text(rows).encode("utf-8")).hexdigest(),
    }


def schema_payload() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_url(),
        "title": "Lumi Studio agent product feed row",
        "description": "One JSON object per line of feed.jsonl.",
        "type": "object",
        "required": [
            "id",
            "item_group_id",
            "title",
            "description",
            "link",
            "price",
            "price_value",
            "price_currency",
            "availability",
            "content_language",
            "enable_search",
            "enable_checkout",
            "app_store_url",
        ],
        "properties": {
            "id": {"type": "string"},
            "item_group_id": {"type": "string"},
            "title": {"type": "string", "maxLength": TITLE_LIMIT},
            "description": {"type": "string", "maxLength": DESCRIPTION_LIMIT},
            "link": {"type": "string", "format": "uri"},
            "image_link": {"type": "string", "format": "uri"},
            "price": {"type": "string"},
            "price_value": {"type": "string", "pattern": r"^\d+(\.\d+)?$"},
            "price_currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
            "availability": {"const": "in_stock"},
            "condition": {"const": "new"},
            "brand": {"type": "string"},
            "product_category": {"type": "string"},
            "product_type": {"const": "mobile application"},
            "content_language": {"enum": list(OFFICIAL_LOCALES)},
            "shipping_country": {"type": "string", "pattern": "^[A-Z]{2}$"},
            "enable_search": {"const": True},
            "enable_checkout": {"const": False},
            "app_store_id": {"type": "string", "pattern": r"^\d+$"},
            "app_store_url": {"type": "string", "format": "uri"},
            "operating_system": {"const": "iOS"},
            "one_time_purchase": {"type": "boolean"},
            "subscription": {"const": False},
        },
        "additionalProperties": True,
    }


# --- Surfaces a shopping ingester cannot read -----------------------------
#
# The JSONL feed answers "give me the rows". It does not answer the two
# questions everything else asks first: search engines and answer engines look
# for schema.org markup, and several directory and merchant ingesters only
# accept an RSS/XML feed. A directory of raw .json/.jsonl files also has
# nothing a crawler will follow or a person will link to, which is most of why
# the feed has no inbound links today.
#
# Same rows, same snapshot, three more shapes. Nothing new is asserted here:
# every value below already appears in feed.jsonl.

# schema.org publishes a closed vocabulary of ApplicationCategory values. The
# feed's product_type is the constant "mobile application", which is not one of
# them, so every entry was declaring a category no consumer can interpret.
# Mapped from the registry's own category, which is what the store listing says.
SCHEMA_APP_CATEGORY = {
    "photo-utility": "MultimediaApplication",
    "productivity": "BusinessApplication",
    "health": "HealthApplication",
    "finance": "FinanceApplication",
    "kids": "EducationApplication",
    "education": "EducationApplication",
    "lifestyle": "LifestyleApplication",
    "travel": "TravelApplication",
    "sleep-sound": "HealthApplication",
    "utility": "UtilitiesApplication",
}


def _schema_category(key):
    from videogen.registry import APPS as _APPS
    return SCHEMA_APP_CATEGORY.get(str(_APPS.get(key, {}).get("category") or ""), "")


def _apps_in_base_locale(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per app, preferring the base locale, in stable order."""
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["item_group_id"])
        current = best.get(key)
        if current is None or (
            row["content_language"] == BASE_LOCALE
            and current["content_language"] != BASE_LOCALE
        ):
            best[key] = row
    return [best[key] for key in sorted(best)]


def jsonld_payload(rows: list[dict[str, Any]], modified: str) -> dict[str, Any]:
    """schema.org ItemList of MobileApplication, one entry per app."""
    languages: dict[str, list[str]] = {}
    for row in rows:
        languages.setdefault(str(row["item_group_id"]), []).append(
            str(row["content_language"])
        )

    def application(row: dict[str, Any]) -> dict[str, Any]:
        key = str(row["item_group_id"])
        node = {
            "@type": "MobileApplication",
            "name": row["title"],
            "description": row["description"],
            "applicationCategory": _schema_category(key),
            "operatingSystem": "iOS",
            "url": row["app_store_url"],
            "image": row.get("image_link", ""),
            "inLanguage": sorted(set(languages.get(key, []))),
            "author": {"@type": "Organization", "name": BRAND},
            "offers": {
                "@type": "Offer",
                "price": str(row["price_value"]),
                "priceCurrency": row["price_currency"],
                "availability": "https://schema.org/InStock",
                "url": row["app_store_url"],
            },
        }
        # No aggregateRating anywhere in this file. The feed carries no rating,
        # so publishing one here would be inventing it.
        return {k: v for k, v in node.items() if v not in ("", [], None)}

    # Bound before the literal: this used to be a walrus inside it, which was
    # only correct because numberOfItems happened to be written above
    # itemListElement. Reordering the keys would have silently turned the list
    # into one entry per app *and locale*.
    base_rows = _apps_in_base_locale(rows)
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{BRAND} iOS app catalog",
        "description": (
            f"Every verified live {BRAND} iOS app, with the price and store "
            "link Apple publishes for it. Structured form of the agent product "
            "feed published alongside it."
        ),
        "url": page_url(),
        "numberOfItems": len(base_rows),
        "dateModified": modified,
        "license": LICENSE_URL,
        "provider": {"@type": "Organization", "name": BRAND, "url": f"{SITE}/about.html"},
        "itemListElement": [
            {"@type": "ListItem", "position": i, "item": application(row)}
            for i, row in enumerate(base_rows, 1)
        ],
    }


def _rfc822(day: str) -> str:
    """RSS 2.0 dates are RFC-822; a bare ISO day is not a valid value."""
    try:
        stamp = _dt.datetime.strptime(day, "%Y-%m-%d").replace(
            tzinfo=_dt.timezone.utc
        )
    except ValueError:
        stamp = _dt.datetime.now(_dt.timezone.utc)
    return email.utils.format_datetime(stamp)


def xml_text(rows: list[dict[str, Any]], modified: str) -> str:
    """RSS 2.0 with the Google Merchant namespace, for XML-only ingesters."""
    def tag(name: str, value: Any) -> str:
        return f"      <{name}>{saxutils.escape(str(value))}</{name}>\n"

    items = []
    for row in rows:
        entry = "    <item>\n"
        # RSS 2.0 requires an item to carry at least a title or a description,
        # and readers outside the merchant world do not know the g: namespace
        # at all. Without these, a generic reader sees empty items -- which
        # defeats the reason this file exists.
        entry += tag("title", row["title"])
        entry += tag("link", row["app_store_url"])
        entry += tag("description", " ".join(str(row["description"]).split())[:5000])
        entry += (
            f'      <guid isPermaLink="false">'
            f'{saxutils.escape(str(row["id"]))}</guid>\n'
        )
        entry += tag("g:id", row["id"])
        entry += tag("g:item_group_id", row["item_group_id"])
        entry += tag("g:title", row["title"])
        entry += tag("g:description", row["description"])
        entry += tag("g:link", row["link"])
        if row.get("image_link"):
            entry += tag("g:image_link", row["image_link"])
        entry += tag("g:price", row["price"])
        entry += tag("g:availability", "in stock")
        entry += tag("g:condition", row["condition"])
        entry += tag("g:brand", row["brand"])
        entry += tag("g:product_type", row.get("product_type", ""))
        entry += tag("g:content_language", row["content_language"])
        entry += tag("g:identifier_exists", "no")
        entry += "    </item>\n"
        items.append(entry)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
        "  <channel>\n"
        f"    <title>{saxutils.escape(BRAND)} iOS app product feed</title>\n"
        f"    <link>{page_url()}</link>\n"
        "    <description>Every verified live iOS app, one entry per app and "
        "Apple storefront. Search-only: apps are purchased on the App Store."
        "</description>\n"
        f"    <lastBuildDate>{_rfc822(modified)}</lastBuildDate>\n"
        + "".join(items)
        + "  </channel>\n</rss>\n"
    )


def page_text(rows: list[dict[str, Any]], modified: str) -> str:
    """A page a crawler can follow and a person can link to."""
    jsonld = jsonld_payload(rows, modified)
    apps = _apps_in_base_locale(rows)
    locales = sorted({str(row["content_language"]) for row in rows})

    def line(row: dict[str, Any]) -> str:
        name = html.escape(str(row["title"]))
        url = html.escape(str(row["app_store_url"]))
        category = html.escape(str(row.get("product_type") or ""))
        price = html.escape(str(row["price"]))
        model = "one-time purchase" if row["one_time_purchase"] else "free"
        return (
            f"<tr><td><a href=\"{url}\">{name}</a></td><td>{category}</td>"
            f"<td>{price}</td><td>{model}</td></tr>"
        )

    rows_html = "\n".join(line(row) for row in apps)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iOS app product feed — {html.escape(BRAND)}</title>
<meta name="description" content="Machine-readable catalog of every verified live {html.escape(BRAND)} iOS app: JSONL, CSV, RSS and schema.org JSON-LD, covering {len(apps)} apps across {len(locales)} Apple storefronts.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{page_url()}">
<link rel="alternate" type="application/json" href="{jsonld_url()}">
<link rel="alternate" type="text/csv" href="{csv_url()}">
<link rel="alternate" type="application/rss+xml" href="{xml_url()}">
<style>
body{{font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:60rem;margin:0 auto;padding:2rem 1rem;color:#1c1c1e}}
table{{border-collapse:collapse;width:100%;margin:1.5rem 0}}
th,td{{text-align:left;padding:.5rem .6rem;border-bottom:1px solid #e5e5ea;font-size:.94rem}}
th{{font-weight:600;background:#f7f7fa}}
.formats a{{display:inline-block;margin:0 1rem .4rem 0}}
</style>
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False, indent=1)}
</script>
</head>
<body>
<h1>iOS app product feed</h1>
<p>{len(apps)} verified live iOS apps from {html.escape(BRAND)}, published across
{len(locales)} Apple storefronts, in the shapes directories and answer engines read.
Snapshot taken {html.escape(modified)}.</p>

<p class="formats"><strong>Formats:</strong>
<a href="feed.jsonl">JSONL feed</a>
<a href="feed.csv">CSV</a>
<a href="feed.xml">RSS 2.0 / Merchant XML</a>
<a href="catalog.jsonld">schema.org JSON-LD</a>
<a href="feed.schema.json">JSON Schema</a>
<a href="index.json">Feed index</a></p>

<h2>What this feed does and does not claim</h2>
<ul>
<li>Prices and storefronts come from Apple&rsquo;s own lookup; the App Store listing is authoritative.</li>
<li><strong>No ratings, awards or rankings appear anywhere in this feed.</strong> Nothing here is a score we assigned ourselves.</li>
<li>Every row is search-only. Apps are purchased on the App Store; we run no checkout.</li>
<li>Illustrations in the Lumi children&rsquo;s apps are digitally generated and narration is text-to-speech.</li>
<li>Published under <a href="{LICENSE_URL}">CC BY 4.0</a>. Reuse is welcome.</li>
</ul>

<h2>Catalog</h2>
<table>
<thead><tr><th>App</th><th>Category</th><th>Price</th><th>Monetization</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>

<p><a href="{SITE}/">&larr; iOS app guide</a> &middot; <a href="{SITE}/about.html">About</a></p>
</body>
</html>
"""


def sitemap_text(modified: str) -> str:
    urls = [page_url(), jsonld_url(), xml_url(), csv_url(), feed_url(), index_url()]
    body = "\n".join(
        f"  <url><loc>{url}</loc><lastmod>{modified}</lastmod></url>" for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


def build(pages: Path = PAGES) -> dict[str, int]:
    rows, modified = build_rows(pages)
    if not rows:
        raise ValueError("Refusing to publish an empty agent product feed")
    (pages / FEED_DIR).mkdir(parents=True, exist_ok=True)
    written = 0
    written += write_text_if_changed(pages / FEED_RELATIVE, feed_text(rows))
    written += write_text_if_changed(pages / CSV_RELATIVE, csv_text(rows))
    written += write_text_if_changed(
        pages / SCHEMA_RELATIVE,
        json.dumps(schema_payload(), ensure_ascii=False, indent=2) + "\n",
    )
    written += write_text_if_changed(
        pages / INDEX_RELATIVE,
        json.dumps(index_payload(rows, modified), ensure_ascii=False, indent=2)
        + "\n",
    )
    written += write_text_if_changed(
        pages / JSONLD_RELATIVE,
        json.dumps(jsonld_payload(rows, modified), ensure_ascii=False, indent=2)
        + "\n",
    )
    written += write_text_if_changed(pages / XML_RELATIVE, xml_text(rows, modified))
    written += write_text_if_changed(pages / PAGE_RELATIVE, page_text(rows, modified))
    written += write_text_if_changed(pages / SITEMAP_RELATIVE, sitemap_text(modified))
    return {
        "rows": len(rows),
        "apps": len({str(row["item_group_id"]) for row in rows}),
        "locales": len({str(row["content_language"]) for row in rows}),
        "written": written,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", default=str(PAGES))
    args = parser.parse_args()
    stats = build(Path(args.pages))
    print(
        f"✓ agent product feed: {stats['rows']} rows "
        f"({stats['apps']} apps × {stats['locales']} locales, "
        f"{stats['written']} files written)"
    )


if __name__ == "__main__":
    main()
