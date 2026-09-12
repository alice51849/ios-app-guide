"""Create 470 unpublished Indic candidates from cached production evidence.

No App metadata, existing Guide output, social queue, receipt, or price is
written. The normal page generator and shared storefront/attribution helpers
produce the same app/locale records on both sides of the paired source.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re

import app_store_storefronts as stores
import build_pages_i18n as pages
import gen_store_attribution as attribution
import market_availability as market
from indic_native_copy import DISCLOSURES, FIELDS, LOCALES, TARGET_CELLS, TARGET_FIELDS
import indic_text_gate

STORE_URL = re.compile(r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/id(?P<id>[0-9]+)(?:\?[^\"<>\s]*)?")


def load_apps(source_pages):
    document = json.loads((source_pages / "data/verified-ios-app-finder-catalog.json").read_text())
    apps = {row["key"]: row for row in document["apps"]}
    live_ids = json.loads((source_pages / ".appstore_live_state.json").read_text())["live_ids"]
    if len(apps) != 47 or len(document["apps"]) != 47 or len(live_ids) != 47:
        raise ValueError("Indic candidates require exactly 47 verified App identities")
    if {str(row["app_store_id"]) for row in apps.values()} != set(map(str, live_ids)):
        raise ValueError("Indic cached-live and catalog App identities differ")
    for key, app in apps.items():
        if str(app["app_store_id"]) != str(pages.APPSTORE.get(key)) or app["purchase_model"] != pages.APPS[key]["purchase_model"]:
            raise ValueError(f"Indic App identity/purchase model differs: {key}")
    return apps


def destination(app_id, locale, availability, relative):
    if market.is_unavailable(locale):
        return None
    if locale not in LOCALES or stores.LOCALE_STOREFRONTS[locale] != "in":
        raise ValueError(f"Unexpected Indic storefront: {locale}")
    route = stores.verified_app_store_url(
        f"https://apps.apple.com/app/id{app_id}", locale, availability
    )
    if route != f"https://apps.apple.com/in/app/id{app_id}":
        raise ValueError(f"Indian storefront is not verified: {app_id}/{locale}")
    return attribution.final_store_url(
        route, attribution.campaign_token(relative), stores.resolve_provider_token(),
        locale=locale, availability=availability, app_id=app_id,
    )


def finalize_page(source, key, locale, availability):
    """A deterministic candidate stage, not a hand-edited artifact."""
    app_id = str(pages.APPSTORE[key])
    link = destination(app_id, locale, availability, f"{locale}/{key}.html")
    if link is None:
        if "apps.apple.com" in source:
            raise ValueError(f"Unavailable candidate still contains an App Store URL: {key}/{locale}")
    else:
        count = 0
        def replace(match):
            nonlocal count
            if match["id"] != app_id:
                raise ValueError(f"Candidate points to another App: {key}/{locale}")
            count += 1
            escaped = "&amp;" in match[0]
            return html.escape(link, quote=True) if escaped else link
        source = STORE_URL.sub(replace, source)
        if count < 2:
            raise ValueError(f"Candidate is missing its App Store schema or CTA: {key}/{locale}")
    disclosure = html.escape(DISCLOSURES[locale])
    if disclosure not in source:
        footer = f'<p data-indic-publisher-disclosure="true">{disclosure}</p>'
        if "</main>" not in source:
            raise ValueError("Candidate has no main content")
        source = source.replace("</main>", footer + "</main>", 1)
    return source, link


def inventory(apps, availability):
    records = []
    for key, app in sorted(apps.items()):
        for locale in LOCALES:
            values = pages.external_localized_values(key, locale)
            for field in FIELDS:
                indic_text_gate.validate(
                    values[field], locale, purchase_model=app["purchase_model"],
                    minimum_ratio=0.95 if field in TARGET_FIELDS.get((key, locale), ()) else None,
                )
            link = destination(str(app["app_store_id"]), locale, availability, f"{locale}/{key}.html")
            records.append({
                "app_key": key, "app_id": str(app["app_store_id"]), "locale": locale,
                "purchase_model": app["purchase_model"],
                "one_time_option": app["one_time_option"],
                "content": {field: values[field] for field in FIELDS},
                "app_store_url": link,
                "market_state": market.market_state(locale),
                "publisher_disclosure": DISCLOSURES[locale],
                "source_corrected": (key, locale) in TARGET_CELLS,
                "publication_state": "unpublished_candidate",
                "social_receipt": None,
                **market.record_fields(locale),
            })
    if len(records) != 470:
        raise ValueError("Indic candidate coverage must remain exact47×10")
    return records


def generate(source_pages, output):
    source_pages, output = Path(source_pages).resolve(), Path(output).resolve()
    if output.exists() or output == source_pages or source_pages in output.parents:
        raise ValueError("Choose a new candidate directory outside existing Guide output")
    metadata = Path(pages.DATA).resolve()
    if output == metadata or metadata in output.parents:
        raise ValueError("Candidates cannot overwrite App metadata")
    apps = load_apps(source_pages)
    availability = stores.load_storefront_availability(source_pages)
    rows = inventory(apps, availability)
    original = pages.PAGES
    try:
        pages.PAGES = str(output)
        for row in rows:
            path = Path(pages.build_one(row["app_key"], row["locale"], pages.all_locales_for(row["app_key"])))
            source, link = finalize_page(path.read_text(), row["app_key"], row["locale"], availability)
            if link != row["app_store_url"]:
                raise ValueError("Candidate link differs from inventory")
            path.write_text(source, encoding="utf-8")
    finally:
        pages.PAGES = original
    (output / "content-inventory.json").write_text(
        json.dumps({"locales": LOCALES, "apps": 47, "cells": rows}, ensure_ascii=False, indent=2) + "\n"
    )
    return {"apps": 47, "locales": 10, "cells": 470, "html_candidates": 470,
            "blocked_bn_bd": 47, "verified_india_ctas": 423, "published": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.source_pages, args.output)))


if __name__ == "__main__":
    main()
