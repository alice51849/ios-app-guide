#!/usr/bin/env python3
"""Publish locale-aware Schema.org offers for every verified live app."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
from xml.sax.saxutils import escape

from app_store_storefronts import (
    LOCALE_STOREFRONTS,
    load_storefront_details,
    localized_storefront_detail,
    validated_app_store_url,
)
import gen_mobile_app_identity
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE",
    "https://alice51849.github.io/ios-app-guide",
).rstrip("/")
API_RELATIVE = Path("api") / "v1" / "ios-app-offers"
INDEX_RELATIVE = API_RELATIVE / "index.json"
SITEMAP_NAME = "sitemap_app_offers.xml"
SCHEMA_URL = "https://schema.org/OfferCatalog"
INITIAL_DATE = "2026-07-20"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def catalog_relative(locale: str) -> Path:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported offer catalog locale: {locale!r}")
    return API_RELATIVE / f"{locale}.jsonld"


def catalog_url(locale: str) -> str:
    return f"{SITE}/{catalog_relative(locale).as_posix()}"


def index_url() -> str:
    return f"{SITE}/{INDEX_RELATIVE.as_posix()}"


def _snapshot_date(pages: Path) -> str:
    payload = json.loads(
        (pages / ".appstore_storefront_state.json").read_text(encoding="utf-8")
    )
    checked_at = payload.get("checked_at")
    value = checked_at[:10] if isinstance(checked_at, str) else ""
    if DATE_RE.fullmatch(value) is None:
        raise ValueError("App Store snapshot must have a valid checked_at date")
    return max(INITIAL_DATE, value)


def offer_item(
    record: dict[str, Any],
    app: dict[str, Any],
    detail: dict[str, object] | None,
    position: int,
) -> dict[str, Any]:
    app_id = str(record["app_store_id"])
    locale = str(record["locale"])
    store_url = validated_app_store_url(
        str(record["app_store_url"]),
        expected_app_id=app_id,
    )
    offer_id = f"{catalog_url(locale)}#offer-{record['app_key']}"
    application = gen_mobile_app_identity.mobile_app_schema(
        app_id,
        str(record["app_name"]),
        str(app["category"]),
        str(record["canonical_guide_url"]),
    )
    application.pop("@context")
    application.update(
        {
            "url": store_url,
            "installUrl": store_url,
            "downloadUrl": store_url,
            "sameAs": str(record["canonical_app_store_url"]),
            "inLanguage": locale,
            "description": str(record["decision_context"]),
            "offers": {"@id": offer_id},
            "potentialAction": {
                "@type": "InstallAction",
                "target": store_url,
            },
            "additionalProperty": [
                {
                    "@type": "PropertyValue",
                    "name": "purchase_model",
                    "value": str(record["purchase_model"]),
                },
                {
                    "@type": "PropertyValue",
                    "name": "one_time_option",
                    "value": bool(record["one_time_option"]),
                },
            ],
        }
    )
    offer: dict[str, Any] = {
        "@type": "Offer",
        "@id": offer_id,
        "url": store_url,
        "name": str(record["app_name"]),
        "description": str(record["decision_context"]),
        "seller": {
            "@type": "Organization",
            "@id": f"{SITE}/about.html#organization",
            "name": "Lumi Studio",
            "url": f"{SITE}/about.html",
        },
        "itemOffered": application,
    }
    if detail is not None:
        localized = localized_storefront_detail(detail, locale)
        offer.update(
            {
                "price": str(localized["price"]),
                "priceCurrency": str(localized["currency"]),
                "availability": "https://schema.org/InStock",
                "eligibleRegion": {
                    "@type": "Country",
                    "identifier": LOCALE_STOREFRONTS[locale].upper(),
                },
            }
        )
        application["isAccessibleForFree"] = localized["price"] == "0"
    return {
        "@type": "ListItem",
        "position": position,
        "url": store_url,
        "item": offer,
    }


def catalog_payload(
    locale: str,
    records: list[dict[str, Any]],
    apps: dict[str, dict[str, Any]],
    details: dict[str, dict[str, dict[str, object]]],
    localized_ui: dict[str, str],
    modified: str,
) -> tuple[dict[str, Any], int]:
    ordered = sorted(
        records,
        key=lambda record: (
            str(record["app_name"]).casefold(),
            str(record["app_store_id"]),
        ),
    )
    country = LOCALE_STOREFRONTS[locale]
    items = []
    price_verified = 0
    for position, record in enumerate(ordered, start=1):
        app_id = str(record["app_store_id"])
        detail = details.get(country, {}).get(app_id)
        price_verified += int(detail is not None)
        items.append(
            offer_item(
                record,
                apps[str(record["app_key"])],
                detail,
                position,
            )
        )
    payload = {
        "@context": "https://schema.org",
        "@type": "OfferCatalog",
        "@id": f"{catalog_url(locale)}#catalog",
        "url": catalog_url(locale),
        "name": localized_ui[publisher_intent_catalog.NAME],
        "description": localized_ui[publisher_intent_catalog.DESCRIPTION],
        "inLanguage": locale,
        "dateModified": modified,
        "numberOfItems": len(items),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": items,
    }
    return payload, price_verified


def build_payloads(
    pages: Path = PAGES,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    records, apps = publisher_intent_catalog.build_records(pages)
    details = load_storefront_details(pages)
    i18n = publisher_intent_catalog.load_ui_i18n()
    modified = _snapshot_date(pages)
    by_locale = {locale: [] for locale in OFFICIAL_LOCALES}
    for record in records:
        by_locale[str(record["locale"])].append(record)

    catalogs: dict[str, dict[str, Any]] = {}
    locale_entries = []
    total_verified_prices = 0
    for locale in OFFICIAL_LOCALES:
        localized_ui = publisher_intent_catalog.dynamic_ui(i18n[locale])
        catalog, verified_prices = catalog_payload(
            locale,
            by_locale[locale],
            apps,
            details,
            localized_ui,
            modified,
        )
        catalogs[locale] = catalog
        total_verified_prices += verified_prices
        locale_entries.append(
            {
                "locale": locale,
                "url": catalog_url(locale),
                "offer_count": len(catalog["itemListElement"]),
                "price_verified_offer_count": verified_prices,
            }
        )

    digest = hashlib.sha256(
        json.dumps(
            catalogs,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    index = {
        "schema_version": 1,
        "conforms_to": SCHEMA_URL,
        "name": "Lumi Studio verified iOS App Store offer catalogs",
        "description": (
            "Locale-aware direct App Store offers for every verified live "
            "Lumi Studio iOS app. Prices appear only when Apple storefront "
            "snapshot data is available."
        ),
        "publisher": {
            "name": "Lumi Studio",
            "url": f"{SITE}/about.html",
        },
        "date_modified": modified,
        "content_digest": f"sha256:{digest}",
        "locale_count": len(catalogs),
        "app_count": len(apps),
        "offer_count": sum(
            len(catalog["itemListElement"]) for catalog in catalogs.values()
        ),
        "price_verified_offer_count": total_verified_prices,
        "locales": locale_entries,
    }
    return index, catalogs


def sitemap_text(modified: str) -> str:
    urls = [index_url(), *(catalog_url(locale) for locale in OFFICIAL_LOCALES)]
    body = "\n".join(
        "  <url>"
        f"<loc>{escape(url)}</loc>"
        f"<lastmod>{modified}</lastmod>"
        "</url>"
        for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def build(pages: Path = PAGES) -> dict[str, int]:
    index, catalogs = build_payloads(pages)
    changed = int(
        publisher_intent_catalog.write_text_if_changed(
            pages / INDEX_RELATIVE,
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        )
    )
    for locale, payload in catalogs.items():
        changed += int(
            publisher_intent_catalog.write_text_if_changed(
                pages / catalog_relative(locale),
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            )
        )
    changed += int(
        publisher_intent_catalog.write_text_if_changed(
            pages / SITEMAP_NAME,
            sitemap_text(str(index["date_modified"])),
        )
    )
    return {
        "apps": int(index["app_count"]),
        "locales": int(index["locale_count"]),
        "offers": int(index["offer_count"]),
        "price_verified": int(index["price_verified_offer_count"]),
        "changed_files": changed,
    }


def main() -> None:
    stats = build()
    print(
        "APP_OFFER_CATALOG "
        + " ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
