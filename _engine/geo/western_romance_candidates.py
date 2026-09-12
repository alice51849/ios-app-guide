#!/usr/bin/env python3
"""Build an exact-47 × 10 offline Western/Romance content candidate.

Uses the normal app-page, hub, decision, persona, alternatives and feed
renderers. Workflow alternatives are explicitly not competitor test results.
No ASC, metadata, publishing, existing generated files or social state is
written. English product copy does not imply independent market research.

    python3 geo/western_romance_candidates.py \
        --source-pages geo/pages --output .local/western-candidate

The output must be a new, project-owned candidate directory. All candidate
outputs are reproducible; no unreviewed source or missing app is silently skipped.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import alternatives_i18n
import app_install_decision_feeds as feeds
import app_install_decision_routes as decisions
import build_pages_i18n as pages
import gen_feed
import gen_hubs
import gen_persona_hubs as personas
from western_romance_copy import LOCALES, PT_PT_COPY, purchase_note
import western_romance_surface_copy as framing

FIELDS = ("name", "subtitle", "description", "promotionalText", "keywords")
CATALOG = Path("data/verified-ios-app-finder-catalog.json")
DECISIONS = Path("data/app-install-decision-routes.json")
SURFACES = ("app", "hub", "decision", "persona", "alternative", "rss", "json_feed")


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_sources(source_pages):
    catalogue = _json(source_pages / CATALOG)
    apps = {app["key"]: app for app in catalogue["apps"]}
    live_rows = _json(source_pages / ".appstore_live_state.json")["live_ids"]
    live_ids = {str(value) for value in live_rows}
    if (
        len(catalogue["apps"]) != 47 or len(apps) != 47 or len(live_rows) != 47
        or set(apps) != set(PT_PT_COPY)
        or {str(app["app_store_id"]) for app in apps.values()} != live_ids
    ):
        raise ValueError("Western candidates require the same exact 47 live apps")
    records = _json(source_pages / DECISIONS)["records"]
    indexed = {(record["app_key"], record["locale"]): record for record in records}
    if len(indexed) != len(records):
        raise ValueError("Duplicate source decision cells")
    missing = {(key, locale) for key in apps for locale in LOCALES} - set(indexed)
    if missing:
        raise ValueError(f"Missing source decision cells: {sorted(missing)}")
    return apps, indexed


def native_record(key, locale, app, source):
    if locale not in LOCALES:
        raise ValueError(f"Unsupported Western locale: {locale}")
    if str(app["app_store_id"]) != str(pages.APPSTORE[key]):
        raise ValueError(f"App identity mismatch: {key}")
    if app["purchase_model"] != pages.APPS[key]["purchase_model"]:
        raise ValueError(f"Purchase model mismatch: {key}")
    if (
        source.get("app_key"), source.get("locale"), str(source.get("app_store_id"))
    ) != (key, locale, str(app["app_store_id"])):
        raise ValueError(f"Source decision identity mismatch: {key}/{locale}")
    values = pages.external_localized_values(key, locale)
    ui = framing.for_locale(locale)
    note = purchase_note(locale, app["purchase_model"])
    context = values["description"]
    if note not in context:
        context += "\n\n" + note
    record = copy.deepcopy(source)
    record.update(
        record_id=f"{locale}:{key}",
        app_key=key, app_name=values["name"], locale=locale,
        app_store_id=str(app["app_store_id"]),
        publisher_query=f'{values["name"]} — {values["subtitle"]}',
        decision_context=" ".join(context.split()),
        purchase_model=app["purchase_model"],
        purchase_label=note,
        one_time_option=True,
        canonical_guide_url=f"{pages.SITE}/{locale}/{key}.html",
        decision_page_url=decisions.decision_page_url(key, locale),
        locale_index_url=decisions.locale_index_url(locale),
        oembed_url=decisions.decision_oembed_url(key, locale),
        canonical_app_store_url=f'https://apps.apple.com/app/id{app["app_store_id"]}',
        app_store_url=pages.appstore_url(key, f"geo_wr_{locale.lower()}"),
        app_store_cta_label=ui["store"].format(name=values["name"]),
        guide_cta_label=ui["guide"],
        publisher_disclosure=ui["disclosure"],
        source_persona_query=ui["persona_title"].format(name=values["name"]),
        source_surface="app_page",
        query_origin="publisher_authored_editorially_localized",
        measured_search_volume=False,
        is_ranking=False,
        storefront_facts=None,
    )
    if locale == "pt-PT":
        for field in ("privacy_labels", "device_labels", "badge_labels"):
            record[field] = [
                label.replace("rastreamento", "rastreio")
                .replace("Tela de Início", "ecrã principal")
                .replace("assinatura", "subscrição")
                for label in record[field]
            ]
    for field in (
        "app_name", "publisher_query", "decision_context", "purchase_label",
        "app_store_url", "app_store_cta_label", "publisher_disclosure",
    ):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"Empty source field: {key}/{locale}/{field}")
    return values, record


def build_inventory(apps, sources):
    inventory = []
    for key, app in sorted(apps.items()):
        for locale in LOCALES:
            values, record = native_record(key, locale, app, sources[(key, locale)])
            inventory.append({
                "app_key": key,
                "app_id": str(app["app_store_id"]),
                "locale": locale,
                "content": {field: values[field] for field in FIELDS},
                "record": record,
                "editorial_scope": framing.editorial_scope(locale),
                "storefront_verification": "global_live_roster_not_local_availability",
                "comparison_kind": "workflow_not_competitor_test",
                "alternative_method": framing.alternative_method(key, locale),
                "publication_state": "unpublished_candidate",
                "social_receipt": None,
                "devto": "English-only eligible; no publication" if locale == "en-US" else "N/A (non-en-US)",
                "surfaces": list(SURFACES),
            })
    if len(inventory) != 470:
        raise ValueError("Western inventory must retain all 470 cells")
    return inventory


def _write(root, relative, content):
    path = root / relative
    if path.is_absolute() and root.resolve() not in path.resolve().parents:
        raise ValueError(f"Candidate path escaped its owner: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_alternative(cell, app):
    record = copy.deepcopy(cell["record"])
    ui = framing.for_locale(cell["locale"])
    record["decision_context"] = (
        ui["comparison"].format(method=cell["alternative_method"])
        + " " + record["decision_context"]
    )
    route = {
        "slug": f'{cell["app_key"]}-vs-existing-workflow',
        "route_id": f'western-workflow:{cell["app_key"]}',
        "app_key": cell["app_key"],
        "app_store_id": cell["app_id"],
        "competitor_name": cell["alternative_method"],
        "comparison_kind": "workflow",
        "query_family": "publisher_workflow_comparison",
        "locales": LOCALES,
    }
    labels = {
        "Purchase model": ui["purchase"],
        "Guide": ui["guide"],
        alternatives_i18n.PURCHASE_LABEL_SOURCES[record["purchase_model"]]: record["purchase_label"],
    }
    return alternatives_i18n.render_page(
        route, cell["locale"], record, app, labels, ui["alternatives"], pages.SITE
    )


def render_persona(cell):
    record, locale = cell["record"], cell["locale"]
    ui = framing.for_locale(locale)
    return personas.render(
        {
            "apps": [cell["app_key"]],
            "slug": f'{cell["app_key"]}-for-your-workflow',
            "title": ui["persona_title"].format(name=record["app_name"]),
            "desc": cell["content"]["subtitle"],
            "intro": ui["persona_intro"] + " " + cell["content"]["description"].split("\n\n")[0],
            "faqs": [(ui["purchase"], record["purchase_label"])],
        },
        locale=locale,
        localized={cell["app_key"]: record},
    )


def generate(source_pages, output, modified=None):
    source_pages, output = source_pages.resolve(), output.resolve()
    if (
        output == source_pages or source_pages in output.parents
        or output == Path(pages.DATA).resolve() or Path(pages.DATA).resolve() in output.parents
        or output.exists()
    ):
        raise ValueError("Use a new candidate directory outside metadata and existing Guide output")
    apps, sources = load_sources(source_pages)
    inventory = build_inventory(apps, sources)
    previews = {key: gen_feed.app_preview_image(key, source_pages, pages.SITE) for key in apps}
    modified = modified or datetime.now(timezone.utc).date().isoformat()
    originals = pages.PAGES, gen_hubs.PAGES
    pages.PAGES, gen_hubs.PAGES = str(output), str(output)
    try:
        for cell in inventory:
            key, locale, record = cell["app_key"], cell["locale"], cell["record"]
            pages.build_one(key, locale, pages.all_locales_for(key))
            _write(output, Path(locale) / "hubs" / f"{key}.html", gen_hubs.build_localized_hub(
                key, locale, availability={},
                page_copy=(record["app_name"], cell["content"]["description"]),
            ))
            _write(output, decisions.decision_page_relative(key, locale), decisions.render_page(
                record, modified, framing.for_locale(locale)["feed_title"],
            ))
            _write(output, Path(locale) / "persona" / f"{key}-for-your-workflow.html", render_persona(cell))
            _write(output, Path(locale) / "alternatives" / f"{key}-vs-existing-workflow.html", render_alternative(cell, apps[key]))
        for locale in LOCALES:
            records = [cell["record"] for cell in inventory if cell["locale"] == locale]
            ui = framing.for_locale(locale)
            context = {"title": ui["feed_title"], "description": ui["feed_description"], "publisher_disclosure": ui["disclosure"]}
            state = {
                row["record_id"]: {
                    "date_published": feeds._timestamp(modified),
                    "date_modified": feeds._timestamp(modified),
                    "content_digest": hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                }
                for row in records
            }
            images = {row["record_id"]: previews[row["app_key"]] for row in records}
            for kind, renderer, alias in (
                ("atom", feeds.render_atom, "feed.xml"),
                ("rss", feeds.render_rss, "rss.xml"),
                ("json_feed", feeds.render_json_feed, "feed.json"),
            ):
                content = renderer(locale, records, modified, context, state, images)
                _write(output, feeds.feed_relative(locale, kind), content)
                _write(output, Path(locale) / alias, content)
        _write(output, Path("content-inventory.json"), json.dumps(
            {"locales": LOCALES, "apps": 47, "cells": inventory}, ensure_ascii=False, indent=2
        ) + "\n")
    finally:
        pages.PAGES, gen_hubs.PAGES = originals
    return {"apps": 47, "locales": 10, "cells": 470, "html_candidates": 2350, "canonical_feeds": 30, "published": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.source_pages, args.output)))


if __name__ == "__main__":
    main()
