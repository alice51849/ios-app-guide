#!/usr/bin/env python3
"""Offline, identity-only regeneration of existing external publishing assets.

Unlike a full content build, this pass retains reviewed paragraphs, currency
literals and historical price evidence. It never reads ASC or publishes posts.

Replay order: this pass; the social verified_content.py --identity-only;
semantic_arms.py --build; this pass again for versioned queue keys; then
persist_state.prepare_content_bundle(). A changed reviewed text digest still
requires an explicit content_release review before merging, never auto-approval.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
from pathlib import Path

from app_store_storefronts import (
    LOCALE_STOREFRONTS, load_storefront_details, localized_storefront_detail,
)
from external_app_identity import (
    INDIC_LOCALES,
    SOURCE_HEADLINES,
    TRIP_PLANET_ALIASES,
    TRIP_PLANET_NAME,
    registry_name,
    external_identity,
)

STORE_URL = re.compile(
    r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/"
    r"(?:[-A-Za-z0-9._~%]+/)?id(?P<id>\d{9,12})(?!\d)"
)
LOCALE_PATH = re.compile(
    r"(?:^|[/.:])(" + "|".join(re.escape(loc) for loc in INDIC_LOCALES)
    + r")(?=$|[/.:])"
)
FULL_HEADLINES = {
    "দৈনন্দিন রুটিন ও পুরস্কার চার্": SOURCE_HEADLINES["lumimission"]["bn-BD"]["subtitle"],
    "Lumi Mission Planet: ଦୈନିକ ଅଭ୍": SOURCE_HEADLINES["lumimission"]["or-IN"]["name"],
    "ଯାତ୍ରା ମୁଦ୍ରା ଓ ଖର୍ଚ୍ଚ ନିୟନ୍ତ୍": SOURCE_HEADLINES["gmoney"]["or-IN"]["subtitle"],
}
TEXT_SUFFIXES = frozenset({".html", ".json", ".xml", ".md", ".txt", ".webmanifest"})


def path_locale(value: str) -> str | None:
    match = LOCALE_PATH.search(value)
    return match.group(1) if match else None


def repair_text(source: str, locale: str | None, app_ids: set[str]) -> str:
    if locale not in INDIC_LOCALES:
        return source
    if locale == "bn-BD":
        source = STORE_URL.sub(
            lambda match: (
                f"https://apps.apple.com/{LOCALE_STOREFRONTS[locale]}/app/id{match['id']}"
                if match["id"] in app_ids else match.group()
            ),
            source,
        )
    for alias in TRIP_PLANET_ALIASES:
        source = source.replace(alias, TRIP_PLANET_NAME)
    for truncated, complete in FULL_HEADLINES.items():
        source = re.sub(
            re.escape(truncated) + r"(?![\w\u200c\u200d])", complete, source
        )
    return source


def repair_document(value, app_ids: set[str], locale: str | None = None):
    if isinstance(value, list):
        return [repair_document(item, app_ids, locale) for item in value]
    if isinstance(value, dict):
        declared = value.get("locale", value.get("lang", value.get("language")))
        if isinstance(declared, str):
            locale = declared
        elif locale is None:
            for field in ("record_id", "sk", "url", "id", "guide_url", "decision_page_url"):
                candidate = value.get(field)
                if isinstance(candidate, str) and path_locale(candidate):
                    locale = path_locale(candidate)
                    break
        repaired = {
            key: (
                child
                # Keep historical price/source proofs, not relabelled evidence.
                if key in {"storefront_facts", "content_contract"}
                else repair_document(
                    child, app_ids, key if key in INDIC_LOCALES else locale
                )
            )
            for key, child in value.items()
        }
        key = value.get("app_key", value.get("key"))
        if key == "tripplanet" and locale in INDIC_LOCALES:
            for field in ("name", "app_name"):
                if field in repaired:
                    repaired[field] = TRIP_PLANET_NAME
        rows = repaired.get("records")
        if isinstance(rows, list) and rows and all(
            isinstance(row, dict) and "decision_page_url" in row for row in rows
        ):
            order = {loc: index for index, loc in enumerate(dict.fromkeys(
                row["locale"] for row in rows
            ))}
            repaired["records"] = sorted(rows, key=lambda row: (
                order[row["locale"]],
                row["priority_rank"] if row["priority_rank"] is not None else 10000,
                row["app_name"].casefold(),
                row["app_key"],
            ))
        return repaired
    if isinstance(value, str):
        return repair_text(value, locale, app_ids)
    return value


def _json_text(value, source: str) -> str:
    indent_match = re.search(r"\n( +)\S", source)
    if indent_match:
        return json.dumps(
            value, ensure_ascii=False, indent=len(indent_match.group(1))
        ) + ("\n" if source.endswith("\n") else "")
    separators = (",", ":") if '": ' not in source else (", ", ": ")
    return json.dumps(value, ensure_ascii=False, separators=separators) + (
        "\n" if source.endswith("\n") else ""
    )


def regenerate(pages: Path, social: Path, *, write: bool = False) -> dict:
    apps = json.loads((social / "apps.json").read_text(encoding="utf-8"))
    app_ids = {str(app["url"]).rsplit("id", 1)[1] for app in apps.values()}
    if len(apps) != 47 or len(app_ids) != 47:
        raise ValueError("This audited migration requires the exact 47-live-App roster")
    changes: dict[Path, str] = {}
    digests: dict[str, str] = {}
    modified_dates: dict[str, str] = {}
    today = datetime.now(timezone.utc).date().isoformat()
    documents: dict[Path, tuple[dict, str]] = {}
    india_facts = load_storefront_details(pages).get("in", {})
    for path in sorted(pages.rglob("*")):
        relative = path.relative_to(pages)
        if (
            not path.is_file() or path.is_symlink()
            or path.suffix not in TEXT_SUFFIXES
            or any(part.startswith((".", "_")) for part in relative.parts)
        ):
            continue
        locale = path_locale(relative.as_posix())
        if locale is None and path.suffix != ".json":
            continue
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            original = json.loads(source)
            document = repair_document(original, app_ids, locale)
            if isinstance(document, dict):
                for row in document.get("records", []):
                    if not isinstance(row, dict) or row.get("locale") != "bn-BD":
                        continue
                    facts = row.get("storefront_facts")
                    if facts and "source_country" not in facts:
                        expected = localized_storefront_detail(
                            india_facts[str(row["app_store_id"])], "bn-BD"
                        )
                        if facts != expected:
                            raise ValueError("Historical Bangladesh-page price evidence changed")
                        row["storefront_facts"] = {**facts, "source_country": "in"}
            if document != original:
                changes[path] = _json_text(document, source)
            if isinstance(document, dict):
                documents[path] = (document, source)
        else:
            content = repair_text(source, locale, app_ids)
            if content != source:
                changes[path] = content

    # These datasets define their digest over the complete records, not the
    # subset of corrected locales. Refresh references as one coherent closure.
    for name in (
        "app-install-decision-routes",
        "lumi-studio-publisher-search-intent-catalog",
    ):
        path = pages / "data" / f"{name}.json"
        document, source = documents[path]
        original_digest = document["content_digest"]
        digest = hashlib.sha256(json.dumps(
            document["records"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if document["content_digest"] != digest:
            digests[document["content_digest"]] = digest
        document["content_digest"] = digest
        module = __import__(
            "app_install_decision_routes"
            if name == "app-install-decision-routes" else "publisher_intent_catalog"
        )
        generation = module._generation_digest(digest)
        if original_digest != digest or document["generation_digest"] != generation:
            document["dateModified"] = today
            modified_dates[original_digest] = today
            modified_dates[digest] = today
        if document["generation_digest"] != generation:
            digests[document["generation_digest"]] = generation
        document["generation_digest"] = generation
        content = _json_text(document, source)
        if content != source:
            changes[path] = content
        if name == "app-install-decision-routes":
            sitemap_path = pages / module.SITEMAP_NAME
            sitemap = module.render_sitemap(document["records"], document["dateModified"])
            if sitemap != sitemap_path.read_text():
                changes[sitemap_path] = sitemap
            schema_path = pages / module.SCHEMA_RELATIVE
            finder = json.loads(
                (pages / "data" / "verified-ios-app-finder-catalog.json").read_text()
            )
            schema = module._schema_payload({app["key"]: app for app in finder["apps"]})
            schema_source = schema_path.read_text()
            schema_content = _json_text(schema, schema_source)
            if schema_content != schema_source:
                changes[schema_path] = schema_content
        else:
            records = document["records"]
            jsonl_path = path.with_suffix(".jsonl")
            jsonl = "".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                for row in records
            )
            if jsonl != jsonl_path.read_text():
                changes[jsonl_path] = jsonl
            csv_path = path.with_suffix(".csv")
            csv = module._csv_text(records)
            if csv.encode("utf-8") != csv_path.read_bytes():
                changes[csv_path] = csv
            croissant_path = pages / "data" / module.CROISSANT_FILENAME
            croissant_source = croissant_path.read_text()
            croissant = json.loads(croissant_source)
            croissant["dateModified"] = document["dateModified"]
            for distribution in croissant["distribution"]:
                source_path = pages / "data" / distribution["contentUrl"].rsplit("/", 1)[-1]
                raw = changes[source_path].encode("utf-8") if source_path in changes else source_path.read_bytes()
                distribution["sha256"] = hashlib.sha256(raw).hexdigest()
                distribution["contentSize"] = f"{len(raw)} B"
            croissant_content = _json_text(croissant, croissant_source)
            if croissant_content != croissant_source:
                changes[croissant_path] = croissant_content

    api_root = pages / "api" / "v1" / "ios-app-catalog"
    api_locales = api_root / "locales"
    api_paths = [path for path in documents if path.parent == api_locales]
    if any(path in changes for path in api_paths):
        import portfolio_app_catalog_api

        localized = {path.stem: documents[path][0]["apps"] for path in api_paths}
        digest = portfolio_app_catalog_api._content_digest(localized)
        for path in api_paths:
            old_digest = documents[path][0].get("content_digest")
            if old_digest:
                digests[old_digest] = digest
                modified_dates[old_digest] = today

    for path, (document, source) in documents.items():
        modified = modified_dates.get(document.get("content_digest"))
        if modified is None:
            continue
        for field in ("dateModified", "date_modified"):
            if field in document:
                document[field] = modified
        content = _json_text(document, source)
        if content != source:
            changes[path] = content

    # Reuse the feed renderer/state contract: keep first-publication history,
    # but advance updated timestamps for the actual changed identity/CTA items.
    import app_install_decision_feeds as feeds
    import app_install_decision_routes as decisions

    owned = documents[pages / decisions.DATA_RELATIVE][0]
    records = owned["records"]
    grouped = feeds._group_records(records)
    previews = feeds._preview_images(pages, records)
    contexts = decisions._feed_contexts(records)
    changed_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for locale in feeds.OFFICIAL_LOCALES:
        context = feeds._context(contexts, locale)
        state = feeds._item_state(
            pages / feeds.feed_relative(locale, "json_feed"),
            grouped[locale], owned["dateModified"], changed_timestamp, previews,
        )
        for feed_format, renderer in (
            ("atom", feeds.render_atom), ("rss", feeds.render_rss),
            ("json_feed", feeds.render_json_feed),
        ):
            path = pages / feeds.feed_relative(locale, feed_format)
            content = renderer(
                locale, grouped[locale], owned["dateModified"], context, state, previews
            )
            if content != path.read_text(encoding="utf-8"):
                changes[path] = content

    if digests:
        for path in sorted(pages.rglob("*")):
            relative = path.relative_to(pages)
            if (
                not path.is_file() or path.is_symlink()
                or path.suffix not in TEXT_SUFFIXES
                or any(part.startswith((".", "_")) for part in relative.parts)
            ):
                continue
            source = path.read_text(encoding="utf-8")
            content = changes.get(path, source)
            if path.suffix == ".html" and any(digest in source for digest in modified_dates):
                content = re.sub(
                    r'("dateModified"\s*:\s*")\d{4}-\d{2}-\d{2}(")',
                    lambda match: match[1] + today + match[2], content,
                )
            for old, new in digests.items():
                content = content.replace(old, new)
            if content != source:
                changes[path] = content

    for name in ("i18n_posts.json", "text_queue.json", "queue.json", "publisher_intents.json"):
        path = social / name
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        original = json.loads(source)
        document = repair_document(original, app_ids)
        if name == "publisher_intents.json" and document.get("reviewed_extensions") is not None:
            document["source_content_digest"] = hashlib.sha256(json.dumps(
                {
                    "base_source_content_digest": document["base_source_content_digest"],
                    "reviewed_extensions": document["reviewed_extensions"],
                    "intents": document["intents"],
                },
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
        if isinstance(document, list):
            for row in document:
                if isinstance(row, dict) and isinstance(row.get("content_contract"), dict):
                    contract = row["content_contract"]
                    if contract.get("locale") in INDIC_LOCALES:
                        if str(social) not in sys.path:
                            sys.path.insert(0, str(social))
                        import verified_content

                        row["content_contract"] = {
                            **contract, "text_sha256": verified_content.sha256_json(row["text"])
                        }
                if not isinstance(row, dict) or not str(row.get("sk", "")).startswith("i18n:"):
                    continue
                _, key, locale = row["sk"].split(":")
                if locale not in INDIC_LOCALES:
                    continue
                identity, separator, rest = str(row.get("text", "")).partition("\n\n")
                lines = identity.splitlines()
                if not lines:
                    continue
                fields = external_identity(
                    key, locale, {"name": lines[0], "subtitle": "\n".join(lines[1:])}
                )
                row["text"] = "\n".join(
                    part for part in (fields["name"], fields["subtitle"]) if part
                ) + separator + rest
        if name == "text_queue.json":
            if str(social) not in sys.path:
                sys.path.insert(0, str(social))
            import semantic_arms

            arms = semantic_arms.arm_matrix(
                json.loads((social / "semantic_arms.json").read_text())
            )
            existing_keys = {row["sk"] for row in document}
            for row in document:
                parts = row["sk"].split(":")
                if (
                    len(parts) < 4 or parts[0] != "intent"
                    or parts[1] not in arms or parts[3] not in INDIC_LOCALES
                ):
                    continue
                revision = semantic_arms.campaign_revision(arms[parts[1]][parts[3]])
                current = ":".join((*parts[:4], revision))
                if current == row["sk"] or current not in existing_keys:
                    existing_keys.discard(row["sk"])
                    row["sk"] = current
                    existing_keys.add(current)
        if document != original:
            changes[path] = _json_text(document, source)
    for key, app in apps.items():
        app["name"] = registry_name(key, str(app["url"]).rsplit("id", 1)[1], app["name"])
        if key == "tripplanet" and "title" in app:
            app["title"] = app["name"]
    apps_path = social / "apps.json"
    apps_source = apps_path.read_text(encoding="utf-8")
    apps_content = _json_text(apps, apps_source)
    if apps_content != apps_source:
        changes[apps_path] = apps_content
    if write:
        for path, content in changes.items():
            path.write_text(content, encoding="utf-8")
    return {
        "mode": "offline-identity-only",
        "apps": len(apps),
        "locales": list(INDIC_LOCALES),
        "changed_files": len(changes),
        "paths": [
            ("guide/" + path.relative_to(pages).as_posix())
            if path.is_relative_to(pages)
            else "threads/" + path.relative_to(social).as_posix()
            for path in sorted(changes)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", required=True, type=Path)
    parser.add_argument("--social", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = regenerate(args.pages.resolve(), args.social.resolve(), write=args.write)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "paths"}))


if __name__ == "__main__":
    main()
