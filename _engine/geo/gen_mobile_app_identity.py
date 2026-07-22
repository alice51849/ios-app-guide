#!/usr/bin/env python3
"""Bind verified buyer-page JSON-LD to canonical App Store identities."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from typing import Any, Iterator
from urllib.parse import urlsplit

import gen_smart_app_banners
from appstore_live import live_app_keys
from videogen.registry import APPS, APPSTORE


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
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


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.languages: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {
            name.casefold(): value
            for name, value in attrs
            if value is not None
        }
        if tag.casefold() == "html" and values.get("lang"):
            self.languages.append(values["lang"].strip())
        if tag.casefold() != "link":
            return
        relations = {
            relation.casefold()
            for relation in values.get("rel", "").split()
        }
        if "canonical" in relations and values.get("href"):
            self.canonicals.append(values["href"].strip())

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)


def canonical_store_url(app_id: str) -> str:
    if not re.fullmatch(r"\d{9,12}", app_id):
        raise ValueError(f"Invalid App Store ID: {app_id}")
    return f"https://apps.apple.com/app/id{app_id}"


def _page_metadata(
    source: str,
    path: Path,
    site: str,
) -> tuple[str, str]:
    parser = _PageMetadataParser()
    parser.feed(source)
    canonicals = list(dict.fromkeys(parser.canonicals))
    if len(canonicals) != 1:
        raise ValueError(
            f"Mobile app identity page must have one canonical URL: "
            f"{path} ({len(canonicals)})"
        )
    canonical = canonicals[0]
    site = site.rstrip("/")
    parts = urlsplit(canonical)
    if (
        parts.scheme != "https"
        or parts.query
        or parts.fragment
        or not (
            canonical == site
            or canonical.startswith(f"{site}/")
        )
    ):
        raise ValueError(
            f"Mobile app identity page has invalid canonical URL: "
            f"{path} ({canonical})"
        )

    languages = list(dict.fromkeys(parser.languages))
    if (
        len(languages) != 1
        or not re.fullmatch(
            r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*",
            languages[0],
        )
    ):
        raise ValueError(
            f"Mobile app identity page must have one valid language: "
            f"{path} ({languages})"
        )
    return canonical, languages[0]


def _iter_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nodes(child)


def _root_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(value, dict):
        return
    graph = value.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            if isinstance(item, dict):
                yield item
        return
    yield value


def _schema_types(node: dict[str, Any]) -> list[str]:
    value = node.get("@type", [])
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def _reference_matches(value: Any, expected_id: str) -> bool:
    if isinstance(value, str):
        return value == expected_id
    return (
        isinstance(value, dict)
        and value.get("@id") == expected_id
    )


def _merge_reference(value: Any, expected_id: str) -> Any:
    reference = {"@id": expected_id}
    if value is None:
        return reference
    if _reference_matches(value, expected_id):
        return value
    if isinstance(value, list):
        if any(_reference_matches(item, expected_id) for item in value):
            return value
        return [*value, reference]
    if isinstance(value, (str, dict)):
        return [value, reference]
    raise ValueError("Schema relation must contain entity references")


def _remove_reference(value: Any, expected_id: str) -> Any:
    if value is None or _reference_matches(value, expected_id):
        return None
    if not isinstance(value, list):
        return value
    remaining = [
        item
        for item in value
        if not _reference_matches(item, expected_id)
    ]
    if not remaining:
        return None
    return remaining[0] if len(remaining) == 1 else remaining


def _page_relation(page_url: str) -> str:
    path = urlsplit(page_url).path
    if "/hubs/" in path:
        return "about"
    if "/answers/" in path or "/alternatives/" in path:
        return "mentions"
    return "mainEntity"


def _logical_page_path(value: str, site: str) -> tuple[str, ...] | None:
    parsed = urlsplit(value)
    site_parts = urlsplit(site.rstrip("/"))
    if (
        parsed.scheme != site_parts.scheme
        or parsed.netloc != site_parts.netloc
        or parsed.query
        or parsed.fragment not in {"", "webpage"}
    ):
        return None
    base_path = site_parts.path.rstrip("/")
    if parsed.path == base_path:
        relative = ""
    elif parsed.path.startswith(f"{base_path}/"):
        relative = parsed.path[len(base_path) + 1 :]
    else:
        return None
    segments = tuple(segment for segment in relative.split("/") if segment)
    if (
        segments
        and segments[0] not in gen_smart_app_banners.RESERVED_TOP_LEVEL_DIRS
        and gen_smart_app_banners.LOCALE_DIRECTORY_RE.fullmatch(segments[0])
    ):
        segments = segments[1:]
    return segments


def _same_logical_page(
    existing_url: Any,
    page_url: str,
    site: str,
) -> bool:
    if not isinstance(existing_url, str):
        return False
    existing_path = _logical_page_path(existing_url, site)
    return (
        existing_path is not None
        and existing_path == _logical_page_path(page_url, site)
    )


def _app_store_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return set(APP_STORE_RE.findall(value))
    if isinstance(value, list):
        ids: set[str] = set()
        for item in value:
            ids.update(_app_store_ids(item))
        return ids
    if isinstance(value, dict):
        ids: set[str] = set()
        for item in value.values():
            ids.update(_app_store_ids(item))
        return ids
    return set()


def _node_app_store_ids(node: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for field in (
        "@id",
        "url",
        "installUrl",
        "downloadUrl",
        "sameAs",
        "potentialAction",
    ):
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


def _canonical_install_target(value: Any, store_url: str) -> Any:
    if not isinstance(value, dict):
        return store_url
    target = dict(value)
    if "urlTemplate" in target:
        target["urlTemplate"] = store_url
    elif "url" in target:
        target["url"] = store_url
    else:
        target["urlTemplate"] = store_url
    return target


def _install_action(value: Any, app_id: str) -> dict[str, Any] | list[Any]:
    store_url = canonical_store_url(app_id)
    canonical = {"@type": "InstallAction", "target": store_url}
    if value is None:
        return canonical
    actions = value if isinstance(value, list) else [value]
    result: list[Any] = []
    found = False
    for action in actions:
        matching_install = (
            isinstance(action, dict)
            and "InstallAction" in _schema_types(action)
            and app_id in _app_store_ids(action.get("target"))
        )
        if not matching_install:
            result.append(action)
            continue
        if found:
            continue
        updated = dict(action)
        updated["target"] = _canonical_install_target(
            action.get("target"), store_url
        )
        result.append(updated)
        found = True
    if not found:
        result.append(canonical)
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
    page_url: str,
    relation: str,
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
    node["downloadUrl"] = store_url
    node["potentialAction"] = _install_action(
        node.get("potentialAction"), app_id
    )
    page_reference = {"@id": f"{page_url}#webpage"}
    if relation == "mainEntity":
        node["mainEntityOfPage"] = page_reference
    elif _reference_matches(
        node.get("mainEntityOfPage"),
        page_reference["@id"],
    ):
        node.pop("mainEntityOfPage", None)
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
    page_url: str | None = None,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
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
        "downloadUrl": canonical_store_url(app_id),
        "potentialAction": {
            "@type": "InstallAction",
            "target": canonical_store_url(app_id),
        },
    }
    if page_url is not None:
        schema["mainEntityOfPage"] = {
            "@id": f"{page_url}#webpage",
        }
    return schema


def _upgrade_webpage(
    node: dict[str, Any],
    page_url: str,
    language: str,
    app_id: str,
    relation: str,
    site: str,
) -> None:
    page_id = f"{page_url}#webpage"
    store_url = canonical_store_url(app_id)
    existing_id = node.get("@id")
    if (
        existing_id not in {None, page_url, page_id}
        and not _same_logical_page(existing_id, page_url, site)
    ):
        raise ValueError(
            f"Conflicting WebPage identity for {page_url}: {existing_id}"
        )
    existing_url = node.get("url")
    if (
        existing_url not in {None, page_url}
        and not _same_logical_page(existing_url, page_url, site)
    ):
        raise ValueError(
            f"Conflicting WebPage URL for {page_url}: {existing_url}"
        )
    node["@id"] = page_id
    node["url"] = page_url
    node["inLanguage"] = language
    if relation == "mainEntity":
        main_entity = node.get("mainEntity")
        if (
            main_entity is not None
            and not _reference_matches(main_entity, store_url)
        ):
            raise ValueError(
                f"Conflicting WebPage mainEntity for {page_url}"
            )
        node["mainEntity"] = {"@id": store_url}
        mentions = _remove_reference(node.get("mentions"), store_url)
        if mentions is None:
            node.pop("mentions", None)
        else:
            node["mentions"] = mentions
    else:
        main_entity = _remove_reference(
            node.get("mainEntity"),
            store_url,
        )
        if main_entity is None:
            node.pop("mainEntity", None)
        else:
            node["mainEntity"] = main_entity
        alternate_relation = "about" if relation == "mentions" else "mentions"
        alternate_value = _remove_reference(
            node.get(alternate_relation),
            store_url,
        )
        if alternate_value is None:
            node.pop(alternate_relation, None)
        else:
            node[alternate_relation] = alternate_value
        node[relation] = _merge_reference(
            node.get(relation),
            store_url,
        )


def webpage_schema(
    page_url: str,
    language: str,
    app_id: str,
    relation: str,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{page_url}#webpage",
        "url": page_url,
        "inLanguage": language,
    }
    schema[relation] = {
        "@id": canonical_store_url(app_id),
    }
    return schema


def ensure_mobile_identity(
    path: Path,
    app_id: str,
    app_name: str,
    category: str,
    site: str = gen_smart_app_banners.SITE,
) -> tuple[bool, int, bool]:
    source = path.read_text(encoding="utf-8")
    page_url, language = _page_metadata(source, path, site)
    relation = _page_relation(page_url)
    records: list[
        tuple[
            re.Match[str],
            Any,
            list[dict[str, Any]],
            list[dict[str, Any]],
        ]
    ] = []
    application_nodes: list[dict[str, Any]] = []
    webpage_nodes: list[dict[str, Any]] = []
    for match in JSON_LD_RE.finditer(source):
        try:
            document = json.loads(match.group("body"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON-LD in {path}: {error}") from error
        all_nodes = list(_iter_nodes(document))
        nodes = []
        for node in all_nodes:
            types = set(_schema_types(node))
            if types.intersection(
                {"SoftwareApplication", "MobileApplication"}
            ):
                nodes.append(node)
                application_nodes.append(node)
        webpage_nodes.extend(
            node
            for node in _root_nodes(document)
            if "WebPage" in _schema_types(node)
        )
        records.append((match, document, all_nodes, nodes))

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
    if len(webpage_nodes) > 1:
        page_id = f"{page_url}#webpage"
        for webpage in webpage_nodes:
            existing_id = webpage.get("@id")
            existing_url = webpage.get("url")
            identity_matches = (
                existing_id in {None, page_url, page_id}
                or (
                    isinstance(existing_id, str)
                    and _same_logical_page(existing_id, page_url, site)
                )
            )
            url_matches = (
                existing_url in {None, page_url}
                or (
                    isinstance(existing_url, str)
                    and _same_logical_page(existing_url, page_url, site)
                )
            )
            if not identity_matches or not url_matches:
                raise ValueError(
                    f"Conflicting WebPage identities in {path}"
                )

    inserted = not matching_nodes
    changed_nodes: set[int] = set()
    inserts: list[str] = []
    if inserted:
        if "</head>" not in source:
            raise ValueError(f"Mobile app identity page has no closing head: {path}")
        schema = mobile_app_schema(
            app_id,
            app_name,
            category,
            page_url if relation == "mainEntity" else None,
        )
        inserts.append(
            '<script type="application/ld+json" '
            'data-mobile-app-identity="1">\n'
            + json.dumps(schema, ensure_ascii=False, indent=2)
            + "\n</script>"
        )
    else:
        target = matching_nodes[0]
        before = json.dumps(target, ensure_ascii=False, sort_keys=True)
        _upgrade_node(
            target,
            app_id,
            app_name,
            category,
            page_url,
            relation,
        )
        after = json.dumps(target, ensure_ascii=False, sort_keys=True)
        if before != after:
            changed_nodes.add(id(target))

    if webpage_nodes:
        webpage = webpage_nodes[0]
        before = json.dumps(webpage, ensure_ascii=False, sort_keys=True)
        _upgrade_webpage(
            webpage,
            page_url,
            language,
            app_id,
            relation,
            site,
        )
        after = json.dumps(webpage, ensure_ascii=False, sort_keys=True)
        if before != after:
            changed_nodes.add(id(webpage))
    else:
        inserts.append(
            '<script type="application/ld+json" '
            'data-mobile-app-webpage="1">\n'
            + json.dumps(
                webpage_schema(
                    page_url,
                    language,
                    app_id,
                    relation,
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n</script>"
        )

    if not changed_nodes and not inserts:
        return False, 1, False

    parts: list[str] = []
    cursor = 0
    for match, document, all_nodes, _ in records:
        parts.append(source[cursor : match.start()])
        if any(id(node) in changed_nodes for node in all_nodes):
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
    if inserts:
        if "</head>" not in updated:
            raise ValueError(f"Mobile app identity page has no closing head: {path}")
        updated = updated.replace(
            "</head>",
            "\n".join([*inserts, "</head>"]),
            1,
        )
    path.write_text(updated, encoding="utf-8")
    return True, 1, inserted


def _without_managed_install_actions(
    value: Any, managed_ids: set[str]
) -> Any:
    if value is None:
        return None
    actions = value if isinstance(value, list) else [value]
    remaining = [
        action
        for action in actions
        if not (
            isinstance(action, dict)
            and "InstallAction" in _schema_types(action)
            and bool(_app_store_ids(action) & managed_ids)
        )
    ]
    if not remaining:
        return None
    return remaining[0] if len(remaining) == 1 else remaining


def _sanitize_unmanaged_identity(
    document: Any, managed_ids: set[str]
) -> bool:
    before = json.dumps(document, ensure_ascii=False, sort_keys=True)
    for node in _iter_nodes(document):
        if not set(_schema_types(node)).intersection(
            {"SoftwareApplication", "MobileApplication"}
        ):
            continue
        if not (_node_app_store_ids(node) & managed_ids):
            continue
        for field in ("installUrl", "downloadUrl"):
            if _app_store_ids(node.get(field)) & managed_ids:
                node.pop(field, None)
        actions = _without_managed_install_actions(
            node.get("potentialAction"), managed_ids
        )
        if actions is None:
            node.pop("potentialAction", None)
        else:
            node["potentialAction"] = actions

    store_urls = {
        canonical_store_url(app_id) for app_id in managed_ids
    }
    for node in _root_nodes(document):
        if "WebPage" not in _schema_types(node):
            continue
        for relation in ("mainEntity", "mentions"):
            value = node.get(relation)
            for store_url in store_urls:
                value = _remove_reference(value, store_url)
            if value is None:
                node.pop(relation, None)
            else:
                node[relation] = value

    after = json.dumps(document, ensure_ascii=False, sort_keys=True)
    return before != after


def remove_managed_identity(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    cleaned = gen_smart_app_banners.MOBILE_APP_IDENTITY_BLOCK_RE.sub(
        "\n", source
    )
    managed_ids = {str(app_id) for app_id in APPSTORE.values()}
    parts: list[str] = []
    cursor = 0
    for match in JSON_LD_RE.finditer(cleaned):
        parts.append(cleaned[cursor : match.start()])
        try:
            document = json.loads(match.group("body"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON-LD in {path}: {error}") from error
        if _sanitize_unmanaged_identity(document, managed_ids):
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
    parts.append(cleaned[cursor:])
    updated = "".join(parts)
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = gen_smart_app_banners.SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    targets, app_count = gen_smart_app_banners.build_install_targets(
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
            path,
            app_id,
            app_name,
            category,
            site,
        )
        changed += int(page_changed)
        entities += page_entities
        inserted += int(page_inserted)
    managed_pages = (
        gen_smart_app_banners._guide_pages(pages)
        | gen_smart_app_banners._buyer_intent_pages(pages)
    )
    for path in sorted(managed_pages - set(targets)):
        changed += int(remove_managed_identity(path))
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
