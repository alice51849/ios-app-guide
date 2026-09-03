#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish one machine-readable comparison matrix across every verified app.

An assistant asked "which app should I install for X?" cannot answer from a
catalog: a catalog says what each app *is*, and the question is about how the
candidates *differ*.  Everything this site already publishes is per app — a
guide page, an offer, an install route — so an assistant that wants to compare
two of our apps has to open two documents and infer the comparison itself.
That inference is exactly where a model invents a difference we never claimed.

So this generator emits the comparison as data: one row per verified live app,
the same columns for every row, grouped by the App Store category the registry
already records.  Every column is copied from something the repository can
defend — the registry purchase model, the persona query the app was actually
built for, the decision context the offer catalog already publishes, and
Apple's own public storefront price snapshot.  Nothing is scored, ranked or
weighted, because we publish every app in the table and a first-party ranking
of your own products is not evidence.

The two judgement columns are deliberately mechanical.  ``choose_when`` restates
the buyer intent the app was built for; ``consider_instead_when`` states the one
honest reason a buyer should not pick it, derived from the purchase model alone
(a pay-once app cannot be tried for free; a free-to-start app needs an in-app
purchase to be complete).  Neither sentence may introduce a capability claim,
which is why neither is assembled from marketing copy.

    python geo/app_decision_matrix.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
from typing import Any

from app_store_storefronts import (
    LOCALE_STOREFRONTS,
    load_storefront_details,
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
SLUG = "ios-app-decision-matrix"
DATA_DIR = Path("data")
JSON_RELATIVE = DATA_DIR / f"{SLUG}.json"
JSONL_RELATIVE = DATA_DIR / f"{SLUG}.jsonl"
CSV_RELATIVE = DATA_DIR / f"{SLUG}.csv"
SCHEMA_RELATIVE = DATA_DIR / f"{SLUG}.schema.json"
JSONLD_RELATIVE = DATA_DIR / f"{SLUG}.jsonld"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
BASE_LOCALE = "en-US"
BASE_COUNTRY = LOCALE_STOREFRONTS[BASE_LOCALE]

# Registry categories are App Store shelves, not buyer questions. The label is
# what an assistant will read back to a person, so it names the shelf in the
# words a buyer would use without promising anything about a specific app.
CATEGORY_LABELS = {
    "education": "Study and exam practice",
    "finance": "Money, billing and time tracking",
    "health": "Personal health tracking",
    "kids": "Kids learning and family routines",
    "lifestyle": "Everyday habits",
    "photo-utility": "Photo, document and file utilities",
    "productivity": "Notes, documents and focus",
    "sleep-sound": "Sleep and ambient sound",
    "travel": "Travel planning",
    "utility": "iPhone utilities",
}

# Suffixes the registry uses for a sibling edition of the same app. Naming a
# sibling is useful ("there is a free way in"), inventing one is not, so the
# stem only counts when the stripped key is itself a published app.
EDITION_SUFFIXES = ("lite", "pro", "plus")

PURCHASE_MODEL_LABELS = {
    "paid_upfront": "pay once, no subscription",
    "free_with_lifetime_unlock": "free to start, one-time unlock, no subscription",
}

# The single honest reason not to pick an app, given only its purchase model.
CONSIDER_INSTEAD = {
    "paid_upfront": (
        "you want to try the app before paying — this edition is a paid "
        "download with no free tier"
    ),
    "free_with_lifetime_unlock": (
        "you want every feature without an in-app purchase — the free "
        "download needs a one-time unlock to be complete"
    ),
}

OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
    re.IGNORECASE,
)

COLUMNS: tuple[dict[str, str], ...] = (
    {
        "name": "app_key",
        "type": "string",
        "description": "Stable internal key for the app; never changes.",
        "source": "publisher registry",
    },
    {
        "name": "app_name",
        "type": "string",
        "description": "App Store name of the app.",
        "source": "Apple App Store listing",
    },
    {
        "name": "app_store_id",
        "type": "string",
        "description": "Numeric Apple App Store identifier.",
        "source": "Apple App Store listing",
    },
    {
        "name": "category",
        "type": "string",
        "description": "Registry category key used to group comparable apps.",
        "source": "publisher registry",
    },
    {
        "name": "category_label",
        "type": "string",
        "description": "Human-readable name of the comparison group.",
        "source": "publisher-authored",
    },
    {
        "name": "buyer_intent",
        "type": "string",
        "description": "The buyer question this app was built to answer.",
        "source": "publisher-authored persona query",
    },
    {
        "name": "decision_context",
        "type": "string",
        "description": "One-sentence description of what the app does.",
        "source": "publisher-authored, shared with the offer catalog",
    },
    {
        "name": "purchase_model",
        "type": "string",
        "description": "paid_upfront or free_with_lifetime_unlock.",
        "source": "publisher registry",
    },
    {
        "name": "purchase_model_label",
        "type": "string",
        "description": "Plain-language reading of the purchase model.",
        "source": "derived from purchase_model",
    },
    {
        "name": "one_time_option",
        "type": "boolean",
        "description": "True when the app can be owned with a single payment.",
        "source": "publisher registry",
    },
    {
        "name": "free_to_download",
        "type": "boolean",
        "description": (
            "True when Apple's public storefront snapshot prices the download "
            "at zero in the United States storefront."
        ),
        "source": "Apple storefront lookup snapshot",
    },
    {
        "name": "subscription",
        "type": "boolean",
        "description": "Always false; no app in this table sells a subscription.",
        "source": "publisher registry",
    },
    {
        "name": "us_price",
        "type": "string",
        "description": (
            "United States storefront price at snapshot time, or null when "
            "Apple's lookup did not return one."
        ),
        "source": "Apple storefront lookup snapshot",
    },
    {
        "name": "us_price_currency",
        "type": "string",
        "description": "ISO 4217 currency of us_price, or null.",
        "source": "Apple storefront lookup snapshot",
    },
    {
        "name": "verified_storefront_count",
        "type": "integer",
        "description": (
            "Number of Apple storefronts whose public lookup confirms the app "
            "is sold there."
        ),
        "source": "Apple storefront lookup snapshot",
    },
    {
        "name": "sibling_app_keys",
        "type": "array",
        "description": (
            "Other published editions of the same app, so an assistant can "
            "offer the free way in instead of guessing one."
        ),
        "source": "publisher registry",
    },
    {
        "name": "choose_when",
        "type": "string",
        "description": "The buyer situation this app is the answer to.",
        "source": "derived from buyer_intent",
    },
    {
        "name": "consider_instead_when",
        "type": "string",
        "description": (
            "The one honest reason to skip this app, derived from its "
            "purchase model."
        ),
        "source": "derived from purchase_model",
    },
    {
        "name": "guide_url",
        "type": "string",
        "description": "Canonical English guide page for the app.",
        "source": "this site",
    },
    {
        "name": "app_store_url",
        "type": "string",
        "description": "Direct App Store link for the United States storefront.",
        "source": "Apple App Store listing",
    },
)

CSV_COLUMNS = tuple(
    column["name"] for column in COLUMNS if column["name"] != "sibling_app_keys"
) + ("sibling_app_keys",)


def json_url() -> str:
    return f"{SITE}/{JSON_RELATIVE.as_posix()}"


def jsonl_url() -> str:
    return f"{SITE}/{JSONL_RELATIVE.as_posix()}"


def csv_url() -> str:
    return f"{SITE}/{CSV_RELATIVE.as_posix()}"


def schema_url() -> str:
    return f"{SITE}/{SCHEMA_RELATIVE.as_posix()}"


def jsonld_url() -> str:
    return f"{SITE}/{JSONLD_RELATIVE.as_posix()}"


def _snapshot_date(pages: Path) -> str:
    payload = json.loads(
        (pages / ".appstore_storefront_state.json").read_text(encoding="utf-8")
    )
    checked_at = payload.get("checked_at")
    value = checked_at[:10] if isinstance(checked_at, str) else ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("App Store snapshot must have a valid checked_at date")
    return value


def _sibling_keys(app_key: str, published: set[str]) -> list[str]:
    """Every other published edition that shares this app's stem."""
    stems = {app_key}
    for suffix in EDITION_SUFFIXES:
        if app_key.endswith(suffix) and app_key[: -len(suffix)] in published:
            stems.add(app_key[: -len(suffix)])
    siblings = set()
    for stem in stems:
        for suffix in EDITION_SUFFIXES:
            candidate = f"{stem}{suffix}"
            if candidate in published:
                siblings.add(candidate)
        if stem in published:
            siblings.add(stem)
    siblings.discard(app_key)
    return sorted(siblings)


def _choose_when(record: dict[str, Any]) -> str:
    intent = " ".join(str(record.get("source_persona_query") or "").split())
    name = str(record["app_name"])
    label = PURCHASE_MODEL_LABELS[str(record["purchase_model"])]
    if intent:
        return f"You are looking for {intent}, and you want {label}."
    return f"You want what {name} does, and you want {label}."


def _consider_instead(record: dict[str, Any], siblings: list[str]) -> str:
    reason = CONSIDER_INSTEAD[str(record["purchase_model"])]
    if siblings:
        return (
            f"Consider another edition when {reason}; "
            f"also published: {', '.join(siblings)}."
        )
    return f"Consider a different app when {reason}."


def build_rows(pages: Path = PAGES) -> tuple[list[dict[str, Any]], str]:
    """One comparable row per verified live app, alphabetical, never ranked."""
    records, apps = publisher_intent_catalog.build_records(pages)
    details = load_storefront_details(pages)
    modified = _snapshot_date(pages)
    base = {
        str(record["app_key"]): record
        for record in records
        if str(record["locale"]) == BASE_LOCALE
    }
    published = set(base)
    rows: list[dict[str, Any]] = []
    for app_key in sorted(published):
        record = base[app_key]
        app = apps[app_key]
        app_id = str(record["app_store_id"])
        category = str(app["category"])
        purchase_model = str(record["purchase_model"])
        if purchase_model not in PURCHASE_MODEL_LABELS:
            raise ValueError(
                f"{app_key}: unmapped purchase model {purchase_model!r}"
            )
        us_detail = details.get(BASE_COUNTRY, {}).get(app_id)
        verified_storefronts = sum(
            app_id in country_details for country_details in details.values()
        )
        siblings = _sibling_keys(app_key, published)
        rows.append(
            {
                "app_key": app_key,
                "app_name": str(record["app_name"]),
                "app_store_id": app_id,
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, category),
                "buyer_intent": " ".join(
                    str(record.get("source_persona_query") or "").split()
                ),
                "decision_context": str(record["decision_context"]),
                "purchase_model": purchase_model,
                "purchase_model_label": PURCHASE_MODEL_LABELS[purchase_model],
                "one_time_option": bool(record["one_time_option"]),
                "free_to_download": (
                    None
                    if us_detail is None
                    else str(us_detail.get("price")) == "0"
                ),
                "subscription": False,
                "us_price": (
                    None if us_detail is None else str(us_detail.get("price"))
                ),
                "us_price_currency": (
                    None if us_detail is None else str(us_detail.get("currency"))
                ),
                "verified_storefront_count": verified_storefronts,
                "sibling_app_keys": siblings,
                "choose_when": _choose_when(record),
                "consider_instead_when": _consider_instead(record, siblings),
                "guide_url": str(record["canonical_guide_url"]),
                "app_store_url": validated_app_store_url(
                    str(record["app_store_url"]),
                    expected_app_id=app_id,
                ),
            }
        )
    return rows, modified


def _groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_category: dict[str, list[str]] = {}
    for row in rows:
        by_category.setdefault(str(row["category"]), []).append(
            str(row["app_key"])
        )
    return [
        {
            "category": category,
            "label": CATEGORY_LABELS.get(category, category),
            "app_count": len(keys),
            "app_keys": sorted(keys),
        }
        for category, keys in sorted(by_category.items())
    ]


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def matrix_payload(rows: list[dict[str, Any]], modified: str) -> dict[str, Any]:
    return {
        "$schema": schema_url(),
        "schema_version": 1,
        "name": "Lumi Studio verified iOS app decision matrix",
        "description": (
            "One comparable row per verified live Lumi Studio iOS app, with "
            "identical columns for every row, so an assistant can compare "
            "candidates without inferring a difference we never claimed. "
            "Prices come from Apple's public storefront lookup snapshot."
        ),
        "identifier": json_url(),
        "url": json_url(),
        "license": LICENSE_URL,
        "dateModified": modified,
        "publisher": {
            "name": "Lumi Studio",
            "url": f"{SITE}/about.html",
        },
        "publisher_disclosure": (
            "First-party decision-support material published by Lumi Studio, "
            "the developer of every listed app; not an independent ranking or "
            "a measured search-volume product."
        ),
        "ordering": "alphabetical_by_app_key",
        "is_ranking": False,
        "measured_search_volume": False,
        "price_source": "Apple App Store public lookup snapshot",
        "price_storefront": BASE_COUNTRY.upper(),
        "official_locale_count": len(OFFICIAL_LOCALES),
        "app_count": len(rows),
        "columns": [dict(column) for column in COLUMNS],
        "groups": _groups(rows),
        "rows": rows,
        "content_digest": f"sha256:{_digest(rows)}",
    }


def schema_payload() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_url(),
        "title": "Lumi Studio verified iOS app decision matrix",
        "type": "object",
        "required": ["schema_version", "columns", "groups", "rows"],
        "properties": {
            "schema_version": {"const": 1},
            "is_ranking": {"const": False},
            "measured_search_volume": {"const": False},
            "app_count": {"type": "integer", "minimum": 1},
            "columns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "type", "description", "source"],
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "description": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
            },
            "groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["category", "label", "app_keys"],
                    "properties": {
                        "category": {"type": "string"},
                        "label": {"type": "string"},
                        "app_count": {"type": "integer", "minimum": 1},
                        "app_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [column["name"] for column in COLUMNS],
                    "properties": {
                        "app_key": {"type": "string"},
                        "app_store_id": {"type": "string", "pattern": r"^\d+$"},
                        "purchase_model": {
                            "enum": sorted(PURCHASE_MODEL_LABELS)
                        },
                        "one_time_option": {"type": "boolean"},
                        "subscription": {"const": False},
                        "free_to_download": {"type": ["boolean", "null"]},
                        "us_price": {"type": ["string", "null"]},
                        "us_price_currency": {"type": ["string", "null"]},
                        "verified_storefront_count": {
                            "type": "integer",
                            "minimum": 0,
                        },
                        "sibling_app_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


def jsonld_payload(rows: list[dict[str, Any]], modified: str) -> dict[str, Any]:
    """The same table as Schema.org, so a crawler can read it without our schema."""
    items = []
    for position, row in enumerate(rows, start=1):
        properties = [
            {
                "@type": "PropertyValue",
                "name": "purchase_model",
                "value": row["purchase_model"],
            },
            {
                "@type": "PropertyValue",
                "name": "one_time_option",
                "value": row["one_time_option"],
            },
            {
                "@type": "PropertyValue",
                "name": "subscription",
                "value": False,
            },
            {
                "@type": "PropertyValue",
                "name": "choose_when",
                "value": row["choose_when"],
            },
            {
                "@type": "PropertyValue",
                "name": "consider_instead_when",
                "value": row["consider_instead_when"],
            },
            {
                "@type": "PropertyValue",
                "name": "verified_storefront_count",
                "value": row["verified_storefront_count"],
            },
        ]
        application: dict[str, Any] = {
            "@type": "SoftwareApplication",
            "@id": f"{json_url()}#{row['app_key']}",
            "name": row["app_name"],
            "url": row["guide_url"],
            "sameAs": row["app_store_url"],
            "installUrl": row["app_store_url"],
            "applicationCategory": row["category_label"],
            "operatingSystem": "iOS",
            "description": row["decision_context"],
            "additionalProperty": properties,
        }
        if row["us_price"] is not None:
            application["offers"] = {
                "@type": "Offer",
                "price": row["us_price"],
                "priceCurrency": row["us_price_currency"],
                "availability": "https://schema.org/InStock",
                "url": row["app_store_url"],
                "eligibleRegion": {
                    "@type": "Country",
                    "identifier": BASE_COUNTRY.upper(),
                },
            }
            application["isAccessibleForFree"] = bool(row["free_to_download"])
        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "url": row["guide_url"],
                "item": application,
            }
        )
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": f"{jsonld_url()}#matrix",
        "url": jsonld_url(),
        "name": "Lumi Studio verified iOS app decision matrix",
        "description": (
            "Every verified live Lumi Studio iOS app with identical comparison "
            "fields. Alphabetical by app key; this is not a ranking."
        ),
        "license": LICENSE_URL,
        "dateModified": modified,
        "numberOfItems": len(items),
        "itemListOrder": "https://schema.org/ItemListUnordered",
        "itemListElement": items,
    }


def csv_text(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(CSV_COLUMNS), lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        flat = {key: row[key] for key in CSV_COLUMNS}
        flat["sibling_app_keys"] = " ".join(row["sibling_app_keys"])
        for key, value in list(flat.items()):
            if value is None:
                flat[key] = ""
            elif isinstance(value, bool):
                flat[key] = "true" if value else "false"
        writer.writerow(flat)
    return buffer.getvalue()


def build(pages: Path = PAGES) -> dict[str, int]:
    rows, modified = build_rows(pages)
    payload = matrix_payload(rows, modified)
    written = 0
    written += write_text_if_changed(
        pages / JSON_RELATIVE,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    written += write_text_if_changed(
        pages / JSONL_RELATIVE,
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
    )
    written += write_text_if_changed(pages / CSV_RELATIVE, csv_text(rows))
    written += write_text_if_changed(
        pages / SCHEMA_RELATIVE,
        json.dumps(schema_payload(), ensure_ascii=False, indent=2) + "\n",
    )
    written += write_text_if_changed(
        pages / JSONLD_RELATIVE,
        json.dumps(jsonld_payload(rows, modified), ensure_ascii=False, indent=2)
        + "\n",
    )
    return {"apps": len(rows), "groups": len(payload["groups"]), "written": written}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", default=str(PAGES))
    args = parser.parse_args()
    stats = build(Path(args.pages))
    print(
        f"✓ decision matrix: {stats['apps']} apps in {stats['groups']} groups "
        f"({stats['written']} files written)"
    )


if __name__ == "__main__":
    main()
