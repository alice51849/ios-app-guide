#!/usr/bin/env python3
"""Generate the first-party Lumi Studio publisher search-intent dataset."""

from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
from typing import Any, Iterator
import unicodedata

from answer_personas import PERSONAS
from app_store_storefronts import (
    campaign_app_store_url,
    load_storefront_availability,
    verified_app_store_url,
)
from gen_feed import feed_discovery_links
from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE",
    "https://alice51849.github.io/ios-app-guide",
).rstrip("/")
SLUG = "lumi-studio-publisher-search-intent-catalog"
I18N_PATH = HERE / "publisher_intent_catalog_i18n.json"
FINDER_DATASET = "verified-ios-app-finder-catalog.json"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
MCP_REPOSITORY_URL = "https://github.com/alice51849/lumi-mcp"
MCP_REGISTRY_URL = (
    "https://registry.modelcontextprotocol.io/v0.1/servers"
    "?search=io.github.alice51849%2Flumi-app-finder&limit=10"
)
MCP_BUNDLE_URL = (
    "https://github.com/alice51849/lumi-mcp/releases/latest/download/"
    "lumi-app-finder.mcpb"
)
CROISSANT_SPEC = "http://mlcommons.org/croissant/1.1"
CROISSANT_SUFFIX = "croissant.jsonld"
CROISSANT_FILENAME = f"{SLUG}.{CROISSANT_SUFFIX}"
CROISSANT_URL = f"{SITE}/data/{CROISSANT_FILENAME}"
CROISSANT_MEDIA_TYPE = (
    'application/ld+json; profile="http://mlcommons.org/croissant/1.1"'
)
CROISSANT_CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "sc": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "dct": "http://purl.org/dc/terms/",
    "annotation": "cr:annotation",
    "arrayShape": "cr:arrayShape",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "containedIn": "cr:containedIn",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "description": {"@container": "@language"},
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "excludes": "cr:excludes",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isArray": "cr:isArray",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "name": {"@container": "@language"},
    "parentField": "cr:parentField",
    "path": "cr:path",
    "readLines": "cr:readLines",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sdVersion": "cr:sdVersion",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "unArchive": "cr:unArchive",
    "value": "cr:value",
}
DATASET_VERSION = "1.0.0"
INITIAL_DATE = "2026-07-19"
TODAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
RTL_LOCALES = frozenset({"ar-SA", "he", "ur-PK"})
BASE_APP_COUNT = 26
BASE_RECORD_COUNT = 1300
EXPECTED_APP_COUNT = len(PERSONAS)
EXPECTED_LOCALE_COUNT = len(OFFICIAL_LOCALES)
EXPECTED_RECORD_COUNT = EXPECTED_APP_COUNT * EXPECTED_LOCALE_COUNT

NAME = "Lumi Studio Publisher Search Intent Catalog"
DESCRIPTION = (
    "A first-party catalog of who each app is designed for, the task they are "
    "trying to complete, and the direct App Store path."
)
LEAD = (
    "Publisher-authored search intents across 26 verified live iOS apps and "
    "50 Apple locales."
)
DISCLOSURE = (
    "This is first-party material published by Lumi Studio, the developer of "
    "every listed app."
)
NON_MEASURED = (
    "The queries are editorial descriptions of intended use cases, not measured "
    "search-volume data, rankings, independent reviews, or user endorsements."
)
METHODOLOGY = (
    "One primary buyer persona was selected for each verified live app. Each "
    "query and decision context was editorially localized for the target locale "
    "and linked to the matching full guide."
)

PURCHASE_LABELS = {
    "paid_upfront": "Paid download",
    "free_with_lifetime_unlock": "Free to start · lifetime unlock",
    "free": "Free",
    "flexible": "Flexible · check listing",
    "neutral": "Check current listing",
}

CSV_FIELDS = (
    "record_id",
    "locale",
    "app_key",
    "app_name",
    "app_store_id",
    "publisher_query",
    "decision_context",
    "purchase_model",
    "one_time_option",
    "source_persona_query",
    "canonical_guide_url",
    "canonical_app_store_url",
    "app_store_url",
    "publisher_disclosure",
    "query_origin",
    "measured_search_volume",
    "is_ranking",
    "verified_live",
)

CROISSANT_FIELD_SPECS = {
    "record_id": (
        "sc:Text",
        "Stable identifier combining locale, app key and publisher query.",
        "https://schema.org/identifier",
    ),
    "locale": (
        "sc:Text",
        "Apple App Store locale used for the localized decision context.",
        "https://schema.org/inLanguage",
    ),
    "app_key": (
        "sc:Text",
        "Stable publisher key for the verified live iOS app.",
        None,
    ),
    "app_name": (
        "sc:Text",
        "Localized app name shown on the matching guide.",
        "https://schema.org/name",
    ),
    "app_store_id": (
        "sc:Text",
        "Numeric Apple App Store identifier.",
        "https://schema.org/identifier",
    ),
    "publisher_query": (
        "sc:Text",
        "Editorially localized high-intent query for the app and persona.",
        None,
    ),
    "decision_context": (
        "sc:Text",
        "Localized problem context explaining when the app may fit.",
        "https://schema.org/description",
    ),
    "purchase_model": (
        "sc:Text",
        "Truthful purchase-model classification from the publisher catalog.",
        None,
    ),
    "one_time_option": (
        "sc:Boolean",
        "Whether the catalog records a one-time purchase option.",
        None,
    ),
    "source_persona_query": (
        "sc:Text",
        "Canonical English persona query used as the localization source.",
        None,
    ),
    "canonical_guide_url": (
        "sc:URL",
        "Canonical localized guide that supports the decision context.",
        "https://schema.org/url",
    ),
    "canonical_app_store_url": (
        "sc:URL",
        "Storefront-neutral canonical Apple App Store listing URL.",
        "https://schema.org/sameAs",
    ),
    "app_store_url": (
        "sc:URL",
        "Verified locale-aware direct App Store URL.",
        "https://schema.org/downloadUrl",
    ),
    "publisher_disclosure": (
        "sc:Text",
        "First-party disclosure shown on the localized guide.",
        None,
    ),
    "query_origin": (
        "sc:Text",
        "Provenance classification for the editorial query.",
        None,
    ),
    "measured_search_volume": (
        "sc:Boolean",
        "Always false because these are not measured search-volume records.",
        None,
    ),
    "is_ranking": (
        "sc:Boolean",
        "Always false because the catalog is not a ranking.",
        None,
    ),
    "verified_live": (
        "sc:Boolean",
        "True only when the app passed the public App Store availability gate.",
        None,
    ),
}


def write_text_if_changed(path: Path, content: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def slugify(value: str) -> str:
    return re.sub(
        r"-+",
        "-",
        re.sub(r"[^a-z0-9]+", "-", value.lower()),
    ).strip("-")


def single_line(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    return " ".join(value.split())


def _replace_localized_number(
    value: str,
    old: int,
    new: int,
) -> str:
    if old == new:
        return value
    separators = frozenset({",", ".", "'", " ", "\u00a0", "\u202f", "\u066c"})
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for index, char in enumerate(value):
        if unicodedata.category(char) == "Nd":
            if start is None:
                start = index
            continue
        if start is not None and char in separators:
            continue
        if start is not None:
            spans.append((start, index))
            start = None
    if start is not None:
        spans.append((start, len(value)))

    result = value
    for start, end in reversed(spans):
        span = result[start:end].rstrip("".join(separators))
        end = start + len(span)
        digits = [
            char
            for char in span
            if unicodedata.category(char) == "Nd"
        ]
        normalized = "".join(
            str(unicodedata.digit(char)) for char in digits
        )
        if normalized != str(old):
            continue
        replacement_digits = str(new)
        if len(replacement_digits) != len(digits):
            raise ValueError(
                f"Count width changed from {old} to {new}; "
                "update publisher intent localization templates"
            )
        digit_index = 0
        replacement = []
        for char in span:
            if unicodedata.category(char) != "Nd":
                replacement.append(char)
                continue
            zero = ord(char) - unicodedata.digit(char)
            replacement.append(
                chr(zero + int(replacement_digits[digit_index]))
            )
            digit_index += 1
        result = result[:start] + "".join(replacement) + result[end:]
    return result


def dynamic_ui(mapping: dict[str, str]) -> dict[str, str]:
    return {
        source: _replace_localized_number(
            _replace_localized_number(
                target,
                BASE_RECORD_COUNT,
                EXPECTED_RECORD_COUNT,
            ),
            BASE_APP_COUNT,
            EXPECTED_APP_COUNT,
        )
        for source, target in mapping.items()
    }


def _extract(source: str, pattern: str, field: str) -> str:
    match = re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError(f"Missing {field}")
    value = single_line(match.group(1))
    if not value:
        raise ValueError(f"Empty {field}")
    return value


def _json_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _json_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _json_nodes(child)


def _localized_app_name(source: str, app_id: str) -> str:
    for raw in re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _json_nodes(payload):
            node_type = node.get("@type")
            types = (
                {node_type}
                if isinstance(node_type, str)
                else set(node_type)
                if isinstance(node_type, list)
                else set()
            )
            if not types & {"MobileApplication", "SoftwareApplication"}:
                continue
            if f"id{app_id}" not in json.dumps(node, ensure_ascii=False):
                continue
            name = node.get("name")
            if isinstance(name, str) and single_line(name):
                return single_line(name)
    raise ValueError(f"Missing localized app name for App Store ID {app_id}")


def load_ui_i18n(path: Path = I18N_PATH) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    strings = payload.get("strings")
    localizations = payload.get("localizations")
    if (
        payload.get("schema_version") != 1
        or payload.get("source_locale") != "en-US"
        or not isinstance(strings, list)
        or not isinstance(localizations, dict)
    ):
        raise ValueError("Invalid publisher intent localization document")
    expected_locales = set(OFFICIAL_LOCALES)
    if set(localizations) != expected_locales:
        raise ValueError(
            "Publisher intent locale coverage differs: "
            f"missing={sorted(expected_locales - set(localizations))}, "
            f"extra={sorted(set(localizations) - expected_locales)}"
        )
    expected_strings = set(strings)
    for locale, mapping in localizations.items():
        if not isinstance(mapping, dict) or set(mapping) != expected_strings:
            raise ValueError(f"Incomplete publisher intent UI mapping: {locale}")
        for source, target in mapping.items():
            if (
                not isinstance(source, str)
                or not isinstance(target, str)
                or not target.strip()
                or "\n" in target
                or "\r" in target
            ):
                raise ValueError(
                    f"Invalid publisher intent UI translation: {locale}/{source}"
                )
    return localizations


def campaign_token(locale: str) -> str:
    token = f"iag_data_{locale.replace('-', '_').lower()}"
    if len(token) > 30 or not re.fullmatch(r"[a-z0-9_]+", token):
        raise ValueError(f"Invalid publisher intent campaign token: {token}")
    return token


def _app_store_url(
    app_id: str,
    locale: str,
    availability: dict[str, frozenset[str]],
) -> str:
    canonical = f"https://apps.apple.com/app/id{app_id}"
    return campaign_app_store_url(
        verified_app_store_url(canonical, locale, availability),
        campaign_token(locale),
    )


def _finder_records(pages: Path) -> dict[str, dict[str, Any]]:
    path = pages / "data" / FINDER_DATASET
    payload = json.loads(path.read_text(encoding="utf-8"))
    apps = payload.get("apps")
    if not isinstance(apps, list):
        raise ValueError(f"Invalid finder catalog: {path}")
    records = {
        str(app["key"]): app
        for app in apps
        if isinstance(app, dict) and app.get("key")
    }
    expected = set(PERSONAS)
    if set(records) != expected:
        raise ValueError(
            "Finder/persona app coverage differs: "
            f"missing={sorted(expected - set(records))}, "
            f"extra={sorted(set(records) - expected)}"
        )
    if len(records) != EXPECTED_APP_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_APP_COUNT} verified apps, got {len(records)}"
        )
    return records


def _page_record(
    pages: Path,
    locale: str,
    key: str,
    app: dict[str, Any],
    availability: dict[str, frozenset[str]],
) -> dict[str, Any]:
    source_query = str(PERSONAS[key][0]["query"])
    page_slug = slugify(source_query)
    path = pages / locale / "answers" / f"{page_slug}.html"
    source = path.read_text(encoding="utf-8")
    app_id = str(app["app_store_id"])
    if f"apps.apple.com/app/id{app_id}" not in source:
        raise ValueError(f"Wrong App Store owner in {path}")
    canonical = _extract(
        source,
        r'<link rel="canonical" href="([^"]+)"',
        "canonical URL",
    )
    expected_canonical = (
        f"{SITE}/{locale}/answers/{page_slug}.html"
    )
    if canonical != expected_canonical:
        raise ValueError(
            f"Unexpected canonical in {path}: {canonical}"
        )
    cta_label = _extract(
        source,
        r'<a class="cta" href="https://apps\.apple\.com/[^"]+"[^>]*>'
        r"(.*?)</a>",
        "App Store CTA",
    )
    return {
        "record_id": f"{locale}:{key}:{page_slug}",
        "locale": locale,
        "app_key": key,
        "app_name": _localized_app_name(source, app_id),
        "app_store_id": app_id,
        "publisher_query": _extract(
            source,
            r"<h1>(.*?)</h1>",
            "localized publisher query",
        ),
        "decision_context": _extract(
            source,
            r'<p class="lead">(.*?)</p>',
            "localized decision context",
        ),
        "purchase_model": str(app["purchase_model"]),
        "one_time_option": bool(app["one_time_option"]),
        "source_persona_query": source_query,
        "canonical_guide_url": canonical,
        "canonical_app_store_url": (
            f"https://apps.apple.com/app/id{app_id}"
        ),
        "app_store_url": _app_store_url(app_id, locale, availability),
        "app_store_cta_label": cta_label,
        "publisher_disclosure": _extract(
            source,
            r'<footer class="footer"><div class="wrap">(.*?)</div></footer>',
            "publisher disclosure",
        ),
        "query_origin": "publisher_authored_editorially_localized",
        "measured_search_volume": False,
        "is_ranking": False,
        "verified_live": True,
    }


def build_records(
    pages: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    apps = _finder_records(pages)
    availability = load_storefront_availability(pages)
    ordered_keys = sorted(
        apps,
        key=lambda key: (str(apps[key]["name"]).casefold(), key),
    )
    records = [
        _page_record(pages, locale, key, apps[key], availability)
        for locale in OFFICIAL_LOCALES
        for key in ordered_keys
    ]
    if len(records) != EXPECTED_RECORD_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_RECORD_COUNT} records, got {len(records)}"
        )
    if len({record["record_id"] for record in records}) != len(records):
        raise ValueError("Duplicate publisher intent record IDs")
    return records, apps


def _content_digest(records: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _generation_digest(record_digest: str) -> str:
    digest = hashlib.sha256()
    digest.update(record_digest.encode("ascii"))
    digest.update(I18N_PATH.read_bytes())
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


def dataset_payload(
    records: list[dict[str, Any]],
    modified: str,
    content_digest: str,
    generation_digest: str,
) -> dict[str, Any]:
    return {
        "$schema": f"{SITE}/data/{SLUG}.schema.json",
        "name": NAME,
        "description": DESCRIPTION,
        "identifier": f"{SITE}/data/{SLUG}.json",
        "url": f"{SITE}/data/{SLUG}.html",
        "dateModified": modified,
        "content_digest": content_digest,
        "generation_digest": generation_digest,
        "license": LICENSE_URL,
        "creator": {
            "@type": "Organization",
            "name": "Lumi Studio",
            "url": SITE,
        },
        "publisher_disclosure": DISCLOSURE,
        "methodology": METHODOLOGY,
        "query_origin": "publisher_authored_editorially_localized",
        "measured_search_volume": False,
        "is_ranking": False,
        "ordering": "official_locale_order_then_alphabetical_app_name",
        "app_count": EXPECTED_APP_COUNT,
        "locale_count": EXPECTED_LOCALE_COUNT,
        "record_count": len(records),
        "locales": list(OFFICIAL_LOCALES),
        "records": records,
    }


def schema_payload(
    apps: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{SITE}/data/{SLUG}.schema.json",
        "title": NAME,
        "type": "object",
        "required": [
            "name",
            "description",
            "identifier",
            "dateModified",
            "content_digest",
            "generation_digest",
            "publisher_disclosure",
            "measured_search_volume",
            "is_ranking",
            "app_count",
            "locale_count",
            "record_count",
            "records",
        ],
        "properties": {
            "name": {"const": NAME},
            "description": {"type": "string", "minLength": 20},
            "identifier": {"type": "string", "format": "uri"},
            "url": {"type": "string", "format": "uri"},
            "dateModified": {"type": "string", "format": "date"},
            "content_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "generation_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "license": {"type": "string", "format": "uri"},
            "creator": {"type": "object"},
            "publisher_disclosure": {
                "type": "string",
                "minLength": 20,
            },
            "methodology": {"type": "string", "minLength": 20},
            "query_origin": {
                "const": "publisher_authored_editorially_localized"
            },
            "measured_search_volume": {"const": False},
            "is_ranking": {"const": False},
            "ordering": {
                "const": "official_locale_order_then_alphabetical_app_name"
            },
            "app_count": {"const": EXPECTED_APP_COUNT},
            "locale_count": {"const": EXPECTED_LOCALE_COUNT},
            "record_count": {"const": EXPECTED_RECORD_COUNT},
            "locales": {
                "type": "array",
                "items": {"enum": list(OFFICIAL_LOCALES)},
                "minItems": EXPECTED_LOCALE_COUNT,
                "maxItems": EXPECTED_LOCALE_COUNT,
                "uniqueItems": True,
            },
            "records": {
                "type": "array",
                "minItems": EXPECTED_RECORD_COUNT,
                "maxItems": EXPECTED_RECORD_COUNT,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(CSV_FIELDS)
                    + ["app_store_cta_label"],
                    "properties": {
                        "record_id": {"type": "string", "minLength": 10},
                        "locale": {"enum": list(OFFICIAL_LOCALES)},
                        "app_key": {"enum": sorted(apps)},
                        "app_name": {"type": "string", "minLength": 1},
                        "app_store_id": {
                            "type": "string",
                            "pattern": "^[0-9]{9,12}$",
                        },
                        "publisher_query": {
                            "type": "string",
                            "minLength": 10,
                        },
                        "decision_context": {
                            "type": "string",
                            "minLength": 20,
                        },
                        "purchase_model": {
                            "enum": sorted(
                                {
                                    str(app["purchase_model"])
                                    for app in apps.values()
                                }
                            )
                        },
                        "one_time_option": {"type": "boolean"},
                        "source_persona_query": {
                            "type": "string",
                            "minLength": 10,
                        },
                        "canonical_guide_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "canonical_app_store_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "app_store_url": {
                            "type": "string",
                            "format": "uri",
                        },
                        "app_store_cta_label": {
                            "type": "string",
                            "minLength": 3,
                        },
                        "publisher_disclosure": {
                            "type": "string",
                            "minLength": 20,
                        },
                        "query_origin": {
                            "const": (
                                "publisher_authored_editorially_localized"
                            )
                        },
                        "measured_search_volume": {"const": False},
                        "is_ranking": {"const": False},
                        "verified_live": {"const": True},
                    },
                },
            },
        },
    }


def _csv_text(records: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                field: (
                    str(record[field]).lower()
                    if isinstance(record[field], bool)
                    else record[field]
                )
                for field in CSV_FIELDS
            }
        )
    return output.getvalue()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _croissant_file_object(
    data_dir: Path,
    suffix: str,
    media_type: str,
    description: str,
) -> dict[str, Any]:
    filename = f"{SLUG}.{suffix}"
    path = data_dir / filename
    return {
        "@type": "cr:FileObject",
        "@id": filename,
        "name": filename,
        "description": description,
        "contentUrl": f"{SITE}/data/{filename}",
        "contentSize": f"{path.stat().st_size} B",
        "encodingFormat": media_type,
        "sha256": _file_sha256(path),
    }


def _croissant_field(name: str) -> dict[str, Any]:
    data_type, description, equivalent_property = CROISSANT_FIELD_SPECS[name]
    field = {
        "@type": "cr:Field",
        "@id": f"publisher_intents/{name}",
        "name": name,
        "description": description,
        "dataType": data_type,
        "source": {
            "fileObject": {"@id": f"{SLUG}.csv"},
            "extract": {"column": name},
        },
    }
    if equivalent_property:
        field["equivalentProperty"] = equivalent_property
    return field


def _croissant_examples(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            f"publisher_intents/{field}": record[field]
            for field in CSV_FIELDS
        }
        for record in records[:2]
    ]


def croissant_metadata(
    records: list[dict[str, Any]],
    ui_i18n: dict[str, dict[str, str]],
    modified: str,
    data_dir: Path,
) -> dict[str, Any]:
    dataset_url = f"{SITE}/data/{SLUG}.html"
    localized_ui = {
        locale: dynamic_ui(mapping)
        for locale, mapping in ui_i18n.items()
    }
    distributions = [
        _croissant_file_object(
            data_dir,
            "csv",
            "text/csv",
            "Canonical UTF-8 table loaded by the publisher_intents RecordSet.",
        ),
        _croissant_file_object(
            data_dir,
            "jsonl",
            "application/x-ndjson",
            "The same 1,400 records serialized as newline-delimited JSON.",
        ),
        _croissant_file_object(
            data_dir,
            "json",
            "application/json",
            "Dataset envelope with provenance, coverage and all 1,400 records.",
        ),
    ]
    return {
        "@context": CROISSANT_CONTEXT,
        "@id": dataset_url,
        "@type": "sc:Dataset",
        "conformsTo": CROISSANT_SPEC,
        "name": {
            locale: localized_ui[locale][NAME]
            for locale in OFFICIAL_LOCALES
        },
        "description": {
            locale: localized_ui[locale][DESCRIPTION]
            for locale in OFFICIAL_LOCALES
        },
        "license": LICENSE_URL,
        "url": dataset_url,
        "creator": {
            "@id": f"{SITE}/#organization",
            "@type": "sc:Organization",
            "name": "Lumi Studio",
            "url": SITE,
        },
        "publisher": {"@id": f"{SITE}/#organization"},
        "datePublished": INITIAL_DATE,
        "dateModified": modified,
        "version": DATASET_VERSION,
        "sdVersion": DATASET_VERSION,
        "isLiveDataset": False,
        "isAccessibleForFree": True,
        "inLanguage": list(OFFICIAL_LOCALES),
        "keywords": [
            "iOS apps",
            "App Store",
            "publisher search intent",
            "localized app discovery",
            "mobile application recommendations",
            "MLCommons Croissant",
        ],
        "identifier": f"{SITE}/data/{SLUG}.json",
        "includedInDataCatalog": f"{SITE}/data/",
        "isBasedOn": [
            f"{SITE}/data/{SLUG}.json",
            f"{SITE}/data/{SLUG}.schema.json",
        ],
        "conditionsOfAccess": "Open access; no account or API key required.",
        "measurementTechnique": METHODOLOGY,
        "citeAs": (
            "@misc{lumi_publisher_intent_catalog_2026, "
            "title={Lumi Studio Publisher Search Intent Catalog}, "
            "author={Lumi Studio}, year={2026}, "
            f"url={{{dataset_url}}}}}"
        ),
        "distribution": distributions,
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "publisher_intents",
                "name": "publisher_intents",
                "description": (
                    "One publisher-authored localized buyer-intent record for "
                    "each verified app and Apple locale."
                ),
                "dataType": "sc:Thing",
                "key": {"@id": "publisher_intents/record_id"},
                "examples": _croissant_examples(records),
                "field": [
                    _croissant_field(name)
                    for name in CSV_FIELDS
                ],
            }
        ],
    }


def validate_croissant_metadata(
    metadata: dict[str, Any],
    records: list[dict[str, Any]],
    data_dir: Path,
) -> None:
    if metadata.get("@context") != CROISSANT_CONTEXT:
        raise ValueError("Croissant metadata must use the local 1.1 context")
    if metadata.get("@type") != "sc:Dataset":
        raise ValueError("Croissant top-level type must be sc:Dataset")
    if metadata.get("conformsTo") != CROISSANT_SPEC:
        raise ValueError("Croissant metadata must conform to version 1.1")
    if set(metadata.get("name", {})) != set(OFFICIAL_LOCALES):
        raise ValueError("Croissant names must cover all official locales")
    if set(metadata.get("description", {})) != set(OFFICIAL_LOCALES):
        raise ValueError("Croissant descriptions must cover all official locales")
    localized_values = [
        *metadata["name"].values(),
        *metadata["description"].values(),
    ]
    if any(not value.strip() or "\n" in value for value in localized_values):
        raise ValueError("Croissant localized metadata must stay single-line")

    distributions = {
        distribution["@id"]: distribution
        for distribution in metadata.get("distribution", [])
    }
    expected_files = {
        f"{SLUG}.csv",
        f"{SLUG}.jsonl",
        f"{SLUG}.json",
    }
    if set(distributions) != expected_files:
        raise ValueError("Croissant distributions are incomplete")
    for filename, distribution in distributions.items():
        path = data_dir / filename
        if distribution["sha256"] != _file_sha256(path):
            raise ValueError(f"Invalid Croissant checksum for {filename}")
        if distribution["contentSize"] != f"{path.stat().st_size} B":
            raise ValueError(f"Invalid Croissant size for {filename}")

    record_sets = metadata.get("recordSet", [])
    if len(record_sets) != 1 or record_sets[0].get("@id") != "publisher_intents":
        raise ValueError("Croissant metadata must define publisher_intents")
    record_set = record_sets[0]
    if record_set.get("key") != {"@id": "publisher_intents/record_id"}:
        raise ValueError("record_id must be the Croissant RecordSet key")
    fields = record_set.get("field", [])
    if [field.get("name") for field in fields] != list(CSV_FIELDS):
        raise ValueError("Croissant fields do not match the CSV contract")
    for field in fields:
        name = field["name"]
        if field["source"]["fileObject"] != {"@id": f"{SLUG}.csv"}:
            raise ValueError(f"{name} must source the canonical CSV")
        if field["source"]["extract"] != {"column": name}:
            raise ValueError(f"{name} uses the wrong CSV column")
    if record_set.get("examples") != _croissant_examples(records):
        raise ValueError("Croissant examples must match RecordSet fields")


def _alternates() -> str:
    links = [
        f'<link rel="alternate" hreflang="en" '
        f'href="{SITE}/data/{SLUG}.html">'
    ]
    links.extend(
        f'<link rel="alternate" hreflang="{locale}" '
        f'href="{SITE}/{locale}/data/{SLUG}.html">'
        for locale in OFFICIAL_LOCALES
    )
    links.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{SITE}/data/{SLUG}.html">'
    )
    return "\n".join(links)


def _schema_org(
    locale: str,
    canonical: str,
    ui: dict[str, str],
    modified: str,
    apps: dict[str, dict[str, Any]],
    data_dir: Path,
) -> dict[str, Any]:
    formats = (
        ("application/json", "json"),
        ("application/x-ndjson", "jsonl"),
        ("text/csv", "csv"),
        (CROISSANT_MEDIA_TYPE, CROISSANT_SUFFIX),
    )
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": f"{SITE}/data/{SLUG}.html#dataset",
        "name": ui[NAME],
        "description": ui[DESCRIPTION],
        "url": canonical,
        "sameAs": f"{SITE}/data/{SLUG}.html",
        "identifier": f"{SITE}/data/{SLUG}.json",
        "inLanguage": locale,
        "isAccessibleForFree": True,
        "license": LICENSE_URL,
        "dateModified": modified,
        "conformsTo": CROISSANT_SPEC,
        "creator": {
            "@type": "Organization",
            "@id": f"{SITE}/#organization",
            "name": "Lumi Studio",
            "url": SITE,
        },
        "publisher": {"@id": f"{SITE}/#organization"},
        "includedInDataCatalog": {
            "@type": "DataCatalog",
            "name": "Lumi Studio Open Data",
            "url": f"{SITE}/data/",
        },
        "measurementTechnique": ui[METHODOLOGY],
        "subjectOf": {
            "@type": "SoftwareApplication",
            "@id": f"{MCP_REPOSITORY_URL}#mcp-server",
            "name": "Lumi App Finder",
            "description": ui[DESCRIPTION],
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Node.js 20 or later",
            "url": MCP_REPOSITORY_URL,
            "sameAs": MCP_REGISTRY_URL,
            "downloadUrl": MCP_BUNDLE_URL,
            "softwareVersion": "1.0.0",
            "isAccessibleForFree": True,
            "author": {"@id": f"{SITE}/#organization"},
        },
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": mime,
                "contentUrl": f"{SITE}/data/{SLUG}.{suffix}",
                "contentSize": (
                    f"{(data_dir / f'{SLUG}.{suffix}').stat().st_size} bytes"
                ),
            }
            for mime, suffix in formats
        ],
        "about": [
            {
                "@type": "MobileApplication",
                "name": str(app["name"]),
                "operatingSystem": "iOS",
                "identifier": {
                    "@type": "PropertyValue",
                    "propertyID": "App Store ID",
                    "value": str(app["app_store_id"]),
                },
                "url": (
                    "https://apps.apple.com/app/"
                    f"id{app['app_store_id']}"
                ),
            }
            for app in sorted(
                apps.values(),
                key=lambda app: str(app["name"]).casefold(),
            )
        ],
    }


def _page(
    locale: str,
    canonical: str,
    ui: dict[str, str],
    records: list[dict[str, Any]],
    modified: str,
    apps: dict[str, dict[str, Any]],
    data_dir: Path,
) -> str:
    ui = dynamic_ui(ui)
    escape = html.escape
    purchase_labels = {
        model: ui[source]
        for model, source in PURCHASE_LABELS.items()
    }
    rows = "".join(
        "<tr>"
        f'<td><strong>{escape(str(record["app_name"]))}</strong></td>'
        f'<td><a href="{escape(str(record["canonical_guide_url"]), quote=True)}">'
        f'{escape(str(record["publisher_query"]))}</a></td>'
        f'<td>{escape(str(record["decision_context"]))}</td>'
        f'<td>{escape(purchase_labels[str(record["purchase_model"])])}</td>'
        f'<td><a href="{escape(str(record["canonical_guide_url"]), quote=True)}">'
        f'{escape(ui["Guide"])}</a></td>'
        f'<td><a rel="nofollow noopener" href="'
        f'{escape(str(record["app_store_url"]), quote=True)}">'
        f'{escape(str(record["app_store_cta_label"]))}</a></td>'
        "</tr>"
        for record in records
    )
    schema = json.dumps(
        _schema_org(locale, canonical, ui, modified, apps, data_dir),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    root_prefix = "" if locale == "en" else f"/{locale}"
    visuals_href = f"{SITE}{root_prefix}/visuals/"
    direction = ' dir="rtl"' if locale in RTL_LOCALES else ""
    return f"""<!doctype html>
<html lang="{escape(locale)}"{direction}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="content-modified" content="{escape(modified)}">
<title>{escape(ui[NAME])}</title>
<meta name="description" content="{escape(ui[DESCRIPTION], quote=True)}">
<link rel="canonical" href="{escape(canonical, quote=True)}">
{_alternates()}
<link rel="describedby" type="application/ld+json" href="{CROISSANT_URL}" title="MLCommons Croissant 1.1">
<meta property="og:type" content="website">
<meta property="og:title" content="{escape(ui[NAME], quote=True)}">
<meta property="og:description" content="{escape(ui[DESCRIPTION], quote=True)}">
<meta property="og:url" content="{escape(canonical, quote=True)}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#171b28;--sub:#596174;--line:#e2e6ee;--brand:#5546c8;--bg:#f7f8fc;--card:#fff}}
*{{box-sizing:border-box}}
html,body{{margin:0;min-width:100%;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;overflow-x:auto}}
a{{color:var(--brand);text-decoration-thickness:1px;text-underline-offset:3px}}
.wrap{{width:max-content;min-width:100%;padding:28px clamp(18px,4vw,54px) 64px}}
h1,h2,p,a,span,strong,th,td{{white-space:nowrap}}
h1{{font-size:clamp(28px,4vw,46px);line-height:1.15;margin:16px 0 8px}}
h2{{font-size:20px;margin:0 0 10px}}
.lead{{font-size:18px;color:var(--sub);margin:0 0 18px}}
.crumb{{font-size:13px;color:var(--sub)}}
.badges,.downloads{{display:flex;gap:9px;align-items:center;margin:14px 0 20px}}
.badge,.download{{display:inline-flex;border:1px solid var(--line);border-radius:999px;background:var(--card);padding:8px 13px;font-size:13px;font-weight:650;text-decoration:none}}
.download{{border-radius:12px;color:#fff;background:linear-gradient(135deg,#6557de,#4f41bb)}}
.cards{{display:flex;gap:14px;margin:16px 0 22px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:17px 19px;box-shadow:0 8px 28px rgba(34,37,59,.05)}}
.card p{{margin:4px 0;color:var(--sub)}}
.table-wrap{{max-width:calc(100vw - 36px);overflow-x:auto;border:1px solid var(--line);border-radius:18px;background:var(--card)}}
table{{width:max-content;min-width:100%;border-collapse:collapse;font-size:14px}}
th,td{{text-align:start;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{position:sticky;top:0;background:#eeeff8;color:#4e5568;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
tr:last-child td{{border-bottom:0}}
.footer{{color:var(--sub);font-size:13px;margin-top:22px}}
</style>
{feed_discovery_links()}
</head>
<body>
<main class="wrap">
<div class="crumb"><a href="{SITE}{root_prefix}/index.html">{escape(ui["Home"])}</a> · <a href="{SITE}/data/">{escape(ui["Open data"])}</a></div>
<h1>{escape(ui[NAME])}</h1>
<p class="lead">{escape(ui[LEAD])}</p>
<div class="badges"><span class="badge">{escape(ui["1,300 records: 26 apps × 50 locales."])}</span><span class="badge">{escape(ui["First-party publisher catalog"])}</span><span class="badge">{escape(ui["Not measured search volume"])}</span><span class="badge">{escape(ui["Free to download"])}</span><a class="badge" href="{escape(visuals_href, quote=True)}">{escape(ui["Publisher query"])} · SVG</a></div>
<div class="downloads"><strong>{escape(ui["Download the complete dataset"])}</strong><a class="download" href="{SITE}/data/{SLUG}.json">JSON</a><a class="download" href="{SITE}/data/{SLUG}.jsonl">JSONL</a><a class="download" href="{SITE}/data/{SLUG}.csv">CSV</a><a class="download" href="{CROISSANT_URL}">Croissant 1.1</a></div>
<div class="cards"><section class="card"><h2>{escape(ui["Methodology"])}</h2><p>{escape(ui[METHODOLOGY])}</p><p>{escape(ui["Alphabetical by app name — never a ranking."])}</p></section><section class="card"><h2>{escape(ui["What this dataset contains"])}</h2><p>{escape(ui["JSON, JSONL and CSV contain the same 1,300 records."])}</p><p>{escape(ui["Scroll horizontally to inspect every field."])}</p></section></div>
<section class="card"><h2>{escape(ui["First-party publisher catalog"])}</h2><p>{escape(ui[DISCLOSURE])}</p><p>{escape(ui[NON_MEASURED])}</p></section>
<section class="card"><h2>{escape(ui[NAME])} · MCP</h2><p>{escape(ui[DESCRIPTION])}</p><p><a href="{escape(MCP_REGISTRY_URL, quote=True)}">MCP Registry</a> · <a href="{escape(MCP_REPOSITORY_URL, quote=True)}">GitHub</a> · <a href="{escape(MCP_BUNDLE_URL, quote=True)}">MCPB</a></p></section>
<div class="table-wrap"><table><thead><tr><th>{escape(ui["App"])}</th><th>{escape(ui["Publisher query"])}</th><th>{escape(ui["Decision context"])}</th><th>{escape(ui["Purchase model"])}</th><th>{escape(ui["Guide"])}</th><th>App Store</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="footer">{escape(ui["License"])}: <a href="{LICENSE_URL}">CC BY 4.0</a> · {escape(ui["CC BY 4.0 applies to the original catalog compilation; app names and App Store marks belong to their owners."])} · {escape(ui["Updated"])} {escape(modified)}</p>
</main>
</body>
</html>
"""


def build(pages: Path = PAGES, today: str | None = None) -> str:
    today = today or date.today().isoformat()
    if not TODAY_RE.fullmatch(today):
        raise ValueError(f"Invalid build date: {today}")
    ui_i18n = load_ui_i18n()
    records, apps = build_records(pages)
    content_digest = _content_digest(records)
    generation_digest = _generation_digest(content_digest)
    data_dir = pages / "data"
    json_path = data_dir / f"{SLUG}.json"
    modified = _stable_modified(json_path, generation_digest, today)
    payload = dataset_payload(
        records,
        modified,
        content_digest,
        generation_digest,
    )
    write_text_if_changed(
        json_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    write_text_if_changed(
        data_dir / f"{SLUG}.jsonl",
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            + "\n"
            for record in records
        ),
    )
    write_text_if_changed(data_dir / f"{SLUG}.csv", _csv_text(records))
    write_text_if_changed(
        data_dir / f"{SLUG}.schema.json",
        json.dumps(
            schema_payload(apps),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    croissant = croissant_metadata(
        records,
        ui_i18n,
        modified,
        data_dir,
    )
    validate_croissant_metadata(croissant, records, data_dir)
    write_text_if_changed(
        data_dir / CROISSANT_FILENAME,
        json.dumps(croissant, ensure_ascii=False, indent=2) + "\n",
    )

    by_locale = {
        locale: [
            record for record in records if record["locale"] == locale
        ]
        for locale in OFFICIAL_LOCALES
    }
    root_ui = ui_i18n["en-US"]
    write_text_if_changed(
        data_dir / f"{SLUG}.html",
        _page(
            "en",
            f"{SITE}/data/{SLUG}.html",
            root_ui,
            by_locale["en-US"],
            modified,
            apps,
            data_dir,
        ),
    )
    for locale in OFFICIAL_LOCALES:
        write_text_if_changed(
            pages / locale / "data" / f"{SLUG}.html",
            _page(
                locale,
                f"{SITE}/{locale}/data/{SLUG}.html",
                ui_i18n[locale],
                by_locale[locale],
                modified,
                apps,
                data_dir,
            ),
        )
    print(
        "PUBLISHER_INTENT_CATALOG "
        f"apps={len(apps)} locales={len(by_locale)} "
        f"records={len(records)} pages={len(by_locale) + 1}",
        flush=True,
    )
    return SLUG


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
