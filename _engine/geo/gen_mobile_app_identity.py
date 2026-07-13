#!/usr/bin/env python3
"""Bind verified buyer-page JSON-LD to canonical App Store identities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterator

import gen_smart_app_banners
from appstore_live import live_app_keys
from videogen.registry import APPS, APPSTORE


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
JSON_LD_RE = re.compile(
    r"(?P<open><script\b[^>]*\btype\s*=\s*"
    r"(?:\"application/ld\+json\"|'application/ld\+json')[^>]*>)"
    r"(?P<body>.*?)"
    r"(?P<close></script\s*>)",
    flags=re.IGNORECASE | re.DOTALL,
)
APP_STORE_RE = re.compile(
    r"https://apps\.apple\.com/app/id(\d+)",
    flags=re.IGNORECASE,
)
SCHEMA_CATEGORY = {
    "photo-utility": "PhotographyApplication",
    "productivity": "BusinessApplication",
    "kids": "EducationalApplication",
    "education": "EducationalApplication",
    "finance": "FinanceApplication",
    "utility": "UtilitiesApplication",
    "health": "HealthApplication",
    "lifestyle": "LifestyleApplication",
    "sleep-sound": "LifestyleApplication",
    "travel": "TravelApplication",
}


def canonical_store_url(app_id: str) -> str:
    if not re.fullmatch(r"\d{9,12}", app_id):
        raise ValueError(f"Invalid App Store ID: {app_id}")
    return f"https://apps.apple.com/app/id{app_id}"


def _iter_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nodes(child)


def _schema_types(node: dict[str, Any]) -> list[str]:
    value = node.get("@type", [])
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def _app_store_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return set(APP_STORE_RE.findall(value))
    if isinstance(value, list):
        ids: set[str] = set()
        for item in value:
            ids.update(_app_store_ids(item))
        return ids
    return set()


def _node_app_store_ids(node: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for field in ("@id", "url", "installUrl", "downloadUrl", "sameAs"):
        ids.update(_app_store_ids(node.get(field)))
    return ids


def _normalized_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _mobile_types(value: Any) -> str | list[str]:
    if isinstance(value, str):
        return "MobileApplication"
    values = value if isinstance(value, list) else []
    result: list[str] = []
    for item in values:
        updated = "MobileApplication" if item == "SoftwareApplication" else item
        if isinstance(updated, str) and updated not in result:
            result.append(updated)
    if "MobileApplication" not in result:
        result.append("MobileApplication")
    return result


def _same_as(value: Any, app_id: str) -> str | list[str] | None:
    if value is None:
        return None
    values = value if isinstance(value, list) else [value]
    if any(not isinstance(item, str) for item in values):
        raise ValueError("MobileApplication sameAs must contain URLs")
    result: list[str] = []
    for item in values:
        if app_id in _app_store_ids(item):
            continue
        if item not in result:
            result.append(item)
    if not result:
        return None
    return result[0] if len(result) == 1 else result


def _is_store_identifier(value: Any, app_id: str) -> bool:
    if isinstance(value, str):
        return value in {app_id, f"id{app_id}", canonical_store_url(app_id)}
    if not isinstance(value, dict):
        return False
    property_id = str(value.get("propertyID", "")).casefold()
    identifier_value = str(value.get("value", ""))
    return "app store" in property_id or identifier_value in {
        app_id,
        f"id{app_id}",
    }


def _identifier(value: Any, app_id: str) -> dict[str, str] | list[Any]:
    identity = {
        "@type": "PropertyValue",
        "propertyID": "Apple App Store ID",
        "value": app_id,
    }
    if value is None:
        return identity
    values = value if isinstance(value, list) else [value]
    preserved = [
        item for item in values if not _is_store_identifier(item, app_id)
    ]
    if not preserved:
        return identity
    return [*preserved, identity]


def _upgrade_node(
    node: dict[str, Any],
    app_id: str,
    app_name: str,
    category: str,
) -> None:
    store_url = canonical_store_url(app_id)
    node["@type"] = _mobile_types(node.get("@type"))
    node["@id"] = store_url
    node["identifier"] = _identifier(node.get("identifier"), app_id)
    node["name"] = node.get("name") or app_name
    node["operatingSystem"] = node.get("operatingSystem") or "iOS"
    node["applicationCategory"] = (
        node.get("applicationCategory")
        or SCHEMA_CATEGORY.get(category, "UtilitiesApplication")
    )
    node["url"] = store_url
    node["installUrl"] = store_url
    node.pop("inLanguage", None)
    same_as = _same_as(node.get("sameAs"), app_id)
    if same_as is None:
        node.pop("sameAs", None)
    else:
        node["sameAs"] = same_as


def mobile_app_schema(
    app_id: str,
    app_name: str,
    category: str,
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "MobileApplication",
        "@id": canonical_store_url(app_id),
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "Apple App Store ID",
            "value": app_id,
        },
        "name": app_name,
        "operatingSystem": "iOS",
        "applicationCategory": SCHEMA_CATEGORY.get(
            category, "UtilitiesApplication"
        ),
        "url": canonical_store_url(app_id),
        "installUrl": canonical_store_url(app_id),
    }


def ensure_mobile_identity(
    path: Path,
    app_id: str,
    app_name: str,
    category: str,
) -> tuple[bool, int, bool]:
    source = path.read_text(encoding="utf-8")
    records: list[tuple[re.Match[str], Any, list[dict[str, Any]]]] = []
    application_nodes: list[dict[str, Any]] = []
    for match in JSON_LD_RE.finditer(source):
        try:
            document = json.loads(match.group("body"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON-LD in {path}: {error}") from error
        nodes = []
        for node in _iter_nodes(document):
            types = set(_schema_types(node))
            if types.intersection(
                {"SoftwareApplication", "MobileApplication"}
            ):
                nodes.append(node)
                application_nodes.append(node)
        records.append((match, document, nodes))

    conflicting_ids: set[str] = set()
    for node in application_nodes:
        conflicting_ids.update(_node_app_store_ids(node))
    conflicting_ids -= {app_id}
    if conflicting_ids:
        raise ValueError(
            f"Conflicting App Store IDs in {path}: {sorted(conflicting_ids)}"
        )

    matching_nodes = []
    for node in application_nodes:
        ids = _node_app_store_ids(node)
        name_matches = (
            _normalized_name(node.get("name")) == _normalized_name(app_name)
        )
        if app_id in ids or (not ids and name_matches):
            matching_nodes.append(node)
    if len(matching_nodes) > 1:
        raise ValueError(
            f"Duplicate MobileApplication identities in {path}: "
            f"{len(matching_nodes)}"
        )

    inserted = not matching_nodes
    if inserted:
        if "</head>" not in source:
            raise ValueError(f"Mobile app identity page has no closing head: {path}")
        schema = mobile_app_schema(
            app_id,
            app_name,
            category,
        )
        script = (
            '<script type="application/ld+json" '
            'data-mobile-app-identity="1">\n'
            + json.dumps(schema, ensure_ascii=False, indent=2)
            + "\n</script>"
        )
        updated = source.replace("</head>", f"{script}\n</head>", 1)
        path.write_text(updated, encoding="utf-8")
        return True, 1, True

    target = matching_nodes[0]
    before = json.dumps(target, ensure_ascii=False, sort_keys=True)
    _upgrade_node(target, app_id, app_name, category)
    after = json.dumps(target, ensure_ascii=False, sort_keys=True)
    if before == after:
        return False, 1, False

    parts: list[str] = []
    cursor = 0
    for match, document, nodes in records:
        parts.append(source[cursor : match.start()])
        if any(node is target for node in nodes):
            parts.extend(
                (
                    match.group("open"),
                    "\n",
                    json.dumps(document, ensure_ascii=False, indent=2),
                    "\n",
                    match.group("close"),
                )
            )
        else:
            parts.append(match.group(0))
        cursor = match.end()
    parts.append(source[cursor:])
    updated = "".join(parts)
    path.write_text(updated, encoding="utf-8")
    return True, 1, False


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = gen_smart_app_banners.SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    targets, app_count = gen_smart_app_banners.build_targets(
        pages, set(live_keys), site
    )
    app_by_id = {
        APPSTORE[key]: (
            APPS[key]["name"],
            APPS[key].get("category", "utility"),
        )
        for key in live_keys
    }
    changed = 0
    entities = 0
    inserted = 0
    for path, app_id in sorted(targets.items()):
        if app_id not in app_by_id:
            raise ValueError(f"No registry identity for App Store ID {app_id}")
        app_name, category = app_by_id[app_id]
        page_changed, page_entities, page_inserted = ensure_mobile_identity(
            path, app_id, app_name, category
        )
        changed += int(page_changed)
        entities += page_entities
        inserted += int(page_inserted)
    return {
        "apps": app_count,
        "pages": len(targets),
        "entities": entities,
        "inserted": inserted,
        "changed": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--site", default=gen_smart_app_banners.SITE)
    args = parser.parse_args()
    stats = generate(args.pages, site=args.site.rstrip("/"))
    print(
        "Mobile app identity: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
