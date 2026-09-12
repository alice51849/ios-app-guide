#!/usr/bin/env python3
"""Compose reviewed locale fields with the normal web renderers, without publishing.

The production checkout remains read-only. The candidate keeps the production
homepage/canary, owned answers, sitemap inventory and blocked-market files.
Changed locale fields route decision copy to the newly rendered, reviewed app
page rather than silently inheriting an older persona answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import app_install_decision_routes as decisions
import app_store_storefronts as storefronts
import build_pages_i18n as pages
import gen_app_decision_cards as cards
import gen_app_store_facts as facts
import gen_app_store_qr_ctas as qr
import gen_app_store_share_ctas as share
import gen_guide_design as design
import gen_hubs as hubs
import gen_mobile_store_ctas as mobile
import gen_mobile_app_identity as mobile_identity
import gen_outreach_layout as layout
import gen_smart_app_banners as smart
import gen_social_previews as previews
import gen_store_attribution as attribution
import market_availability as market
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog as publisher


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_directory(source, destination):
    if not source.is_dir():
        return
    if os.uname().sysname == "Darwin":
        subprocess.run(["cp", "-cR", str(source), str(destination)], check=True)
    else:
        shutil.copytree(source, destination)


def clone_public_source(source, output):
    output.mkdir(parents=True)
    for item in source.iterdir():
        if item.is_dir() and (not item.name.startswith((".", "_")) or item.name == ".well-known"):
            _copy_directory(item, output / item.name)
        elif item.is_file() and item.name not in {".git"}:
            shutil.copyfile(item, output / item.name)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stamp(path, root, locale, availability):
    source = path.read_text(encoding="utf-8")
    token = attribution.page_token(path.relative_to(root).as_posix(), source)
    if token is None:
        raise ValueError(f"Available candidate page has no campaign token: {path}")
    rendered, _ = attribution.rewrite(
        source, token, storefronts.resolve_provider_token(),
        locale=locale, availability=availability,
    )
    path.write_text(rendered, encoding="utf-8")


def generate(source, output, field_truth):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output == source or source in output.parents:
        raise ValueError("Use a new, isolated candidate directory")
    truth = _json(Path(field_truth))
    if len(truth) != 968:
        raise ValueError("Reviewed field truth must contain exactly 968 fields")
    corrected = {(row["app_key"], row["locale"]) for row in truth}
    if len(corrected) != 289:
        raise ValueError("Reviewed field truth must retain exactly 289 cells")
    for row in truth:
        if pages.external_localized_values(row["app_key"], row["locale"])[row["field"]] != row["merged"]:
            raise ValueError(f"Reviewed field changed: {row['app_key']}/{row['locale']}/{row['field']}")
    apps = {row["key"]: row for row in _json(source / "data/verified-ios-app-finder-catalog.json")["apps"]}
    live_ids = set(map(str, _json(source / ".appstore_live_state.json")["live_ids"]))
    if len(apps) != 47 or {str(row["app_store_id"]) for row in apps.values()} != live_ids:
        raise ValueError("Candidate must use the exact47 production roster")
    intents = {(row["app_key"], row["locale"]): row for row in _json(source / "data/lumi-studio-publisher-search-intent-catalog.json")["records"]}
    records = {(row["app_key"], row["locale"]): row for row in _json(source / "data/app-install-decision-routes.json")["records"]}
    clone_public_source(source, output)
    protected = {
        str(path.relative_to(source)): _sha(path)
        for path in source.rglob("*")
        if path.is_file() and not path.is_symlink()
        and "_engine" not in path.parts and market.locale_from_path(str(path.relative_to(source))) == "bn-BD"
    }
    for relative in protected:
        destination = output / relative
        if not destination.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
    availability = storefronts.load_storefront_availability(source)
    details = storefronts.load_storefront_details(source)
    original_pages, original_hubs = pages.PAGES, hubs.PAGES
    pages.PAGES, hubs.PAGES = str(output), str(source)
    qr_targets = set()
    rendered = []
    try:
        for locale in OFFICIAL_LOCALES:
            if market.is_unavailable(locale):
                continue
            for key, app in sorted(apps.items()):
                app_id = str(app["app_store_id"])
                path = Path(pages.build_one(key, locale, list(OFFICIAL_LOCALES)))
                values = pages.external_localized_values(key, locale)
                mobile_identity.ensure_mobile_identity(
                    path, app_id, values["name"],
                    pages.SCHEMA_CAT.get(app["category"], "UtilitiesApplication"), pages.SITE,
                )
                store_url = storefronts.verified_app_store_url(
                    f"https://apps.apple.com/app/id{app_id}", locale, availability)
                raw_detail = details.get(storefronts.LOCALE_STOREFRONTS[locale], {}).get(app_id)
                detail = storefronts.localized_storefront_detail(raw_detail, locale) if raw_detail else None
                facts.ensure_page_facts(path, app_id, locale, detail, store_url, site=pages.SITE)
                title, description = previews._guide_metadata(path, f"{pages.SITE}/{locale}/{key}.html")
                previews.ensure_metadata_page(
                    path, previews.metadata_block(
                        key, title, description, f"{pages.SITE}/{locale}/{key}.html",
                        values["name"], pages.SITE, locale=locale, endpoint_locale=locale,
                        image_alt=title, storefront=detail,
                    )
                )
                design.ensure_design(path, design.stylesheet_href(pages.SITE))
                cards.ensure_card(path, key, app_id, output, pages.SITE, availability=availability)
                _stamp(path, output, locale, availability)
                source_html = path.read_text()
                path.write_text(smart.render_banner(path, source_html, app_id), encoding="utf-8")
                mobile.ensure_mobile_cta(path, app_id, mobile.asset_href(pages.SITE))
                cta = mobile.app_store_cta(path.read_text(), app_id)
                if cta is None:
                    raise ValueError(f"Missing final CTA: {key}/{locale}")
                href, label = cta
                qr_targets.add((app_id, href))
                qr.ensure_qr_card(
                    path, app_id, href, label,
                    qr._site_asset_href(pages.SITE, qr.STYLESHEET_RELATIVE),
                    qr._site_asset_href(pages.SITE, qr.qr_asset_relative(app_id, href)), locale,
                )
                share.ensure_share(path, app_id, share.asset_href(pages.SITE), store_url=href)
                primary = path.relative_to(output)
                rendered.append(primary)
                if (key, locale) in corrected:
                    intent = publisher._page_record(
                        output, locale, key, app, availability,
                        intents[(key, locale)]["publisher_disclosure"],
                        prefer_app_page=True,
                    )
                    record = decisions._record(output, intent, app, details)
                    records[(key, locale)] = record
                else:
                    record = records[(key, locale)]
                decision_path = decisions.decision_page_relative(key, locale)
                destination = output / decision_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(decisions.render_page(record, "2026-09-12", str(record["app_name"])), encoding="utf-8")
                _stamp(destination, output, locale, availability)
                rendered.append(decision_path)
                hub_path = Path(locale) / "hubs" / f"{key}.html"
                destination = output / hub_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(hubs.build_localized_hub(
                    key, locale, availability, page_copy=(values["name"], values["description"])), encoding="utf-8")
                _stamp(destination, output, locale, availability)
                rendered.append(hub_path)
        qr.sync_assets(output, qr_targets)
        share._write_if_changed(output / share.ASSET_RELATIVE, share.SCRIPT)
        layout.generate(output, rendered)
    finally:
        pages.PAGES, hubs.PAGES = original_pages, original_hubs
    for relative, digest in protected.items():
        if not (output / relative).is_file() or _sha(output / relative) != digest:
            raise ValueError(f"Blocked-market source changed: {relative}")
    for name in ("index.html", "sitemap.xml", "sitemap_index.xml"):
        if (source / name).is_file() and _sha(source / name) != _sha(output / name):
            raise ValueError(f"Production index/canary changed: {name}")
    result = {
        "status": "UNPUBLISHED_CANDIDATE", "publish_allowed": False,
        "apps": 47, "locales": 50, "reviewed_cells": 289, "reviewed_fields": 968,
        "rendered_pages": len(rendered), "bn_protected_files": len(protected),
        "gitlink_changed": False, "index_canary_preserved": True,
        "records": [{"app_key": key, "locale": locale, "app_id": str(apps[key]["app_store_id"]),
                     "path": f"{locale}/{key}.html",
                     "content": pages.external_localized_values(key, locale),
                     "decision": records[(key, locale)]}
                    for key in sorted(apps) for locale in OFFICIAL_LOCALES],
    }
    (output / "release-candidate.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return {key: value for key, value in result.items() if key != "records"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--field-truth", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.output, args.field_truth)))


if __name__ == "__main__":
    main()
