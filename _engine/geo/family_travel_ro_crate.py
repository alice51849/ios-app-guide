#!/usr/bin/env python3
"""Build detached RO-Crate 1.3 metadata for the family-travel open resources."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from family_travel_dataset import (
    APP_ID,
    APP_NAME,
    APP_SHORT_NAME,
    SITE,
    load_dataset,
    write_text_if_changed,
)


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
FILENAME = "family-travel-missions-ro-crate-metadata.json"
METADATA_URL = f"{SITE}/data/{FILENAME}"
ROOT_ID = f"{SITE}/data/family-travel-missions.html"
IDENTIFIER_ID = f"{ROOT_ID}#identifier"
CONTEXT = "https://w3id.org/ro/crate/1.3/context"
PROFILE = "https://w3id.org/ro/crate/1.3"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
PUBLISHER_ID = f"{SITE}/#organization"
CONTACT_ID = "https://github.com/alice51849"
SITEMAP_URL = f"{SITE}/sitemap_ro_crate.xml"
TODAY = dt.date.today().isoformat()
FORBIDDEN = (
    "apps.apple.com",
    "SoftwareApplication",
    APP_NAME,
    APP_SHORT_NAME,
    APP_ID,
)


@dataclass(frozen=True)
class FileSpec:
    relative_path: str
    name: str
    encoding_format: str
    in_language: str | tuple[str, ...] | None = None
    learning_resource: bool = False

    @property
    def url(self) -> str:
        return f"{SITE}/{self.relative_path}"


FILE_SPECS = (
    FileSpec(
        "data/family-travel-missions.json",
        "Canonical bilingual family travel mission taxonomy",
        "application/json",
        ("en", "zh-Hant"),
    ),
    FileSpec(
        "data/family-travel-missions.csv",
        "Flat bilingual family travel mission records",
        "text/csv",
        ("en", "zh-Hant"),
    ),
    FileSpec(
        "data/family-travel-missions.schema.json",
        "Family travel mission JSON Schema",
        "application/schema+json",
        "en",
    ),
    FileSpec(
        "data/family-travel-missions.csv-metadata.json",
        "Family travel mission CSVW metadata",
        "application/csvm+json",
        "en",
    ),
    FileSpec(
        "data/family-travel-missions.dcat.jsonld",
        "Family travel mission DCAT 3 metadata",
        "application/ld+json",
        ("en", "zh-Hant"),
    ),
    FileSpec(
        "api/v1/family-travel-missions/index.json",
        "Family travel missions static API index",
        "application/json",
        "en",
    ),
    FileSpec(
        "api/v1/family-travel-missions/openapi.json",
        "Family travel missions OpenAPI 3.1 document",
        "application/vnd.oai.openapi+json;version=3.1",
        "en",
    ),
    FileSpec(
        "api/v1/family-travel-missions/index.html",
        "Family travel missions static API documentation",
        "text/html",
        "en",
    ),
    FileSpec(
        "zh-Hant/api/v1/family-travel-missions/index.html",
        "親子旅行任務靜態 API 說明",
        "text/html",
        "zh-Hant",
    ),
    FileSpec(
        "tools/family-travel-observation-passport.metadata.json",
        "Family travel observation passport OER metadata",
        "application/ld+json",
        ("en", "zh-Hant"),
        True,
    ),
    FileSpec(
        "tools/family-travel-observation-passport.html",
        "Family travel observation passport",
        "text/html",
        "en",
        True,
    ),
    FileSpec(
        "zh-Hant/tools/family-travel-observation-passport.html",
        "親子旅行觀察護照",
        "text/html",
        "zh-Hant",
        True,
    ),
    FileSpec(
        "tools/family-travel-observation-passport-en-a4.pdf",
        "Family travel observation passport - English A4 PDF",
        "application/pdf",
        "en",
        True,
    ),
    FileSpec(
        "tools/family-travel-observation-passport-en-letter.pdf",
        "Family travel observation passport - English US Letter PDF",
        "application/pdf",
        "en",
        True,
    ),
    FileSpec(
        "tools/family-travel-observation-passport-zh-hant-a4.pdf",
        "親子旅行觀察護照 - 繁體中文 A4 PDF",
        "application/pdf",
        "zh-Hant",
        True,
    ),
    FileSpec(
        "tools/family-travel-observation-passport-zh-hant-letter.pdf",
        "親子旅行觀察護照 - 繁體中文 US Letter PDF",
        "application/pdf",
        "zh-Hant",
        True,
    ),
    FileSpec(
        "opds/family-travel-observation-passport.json",
        "Family travel observation passport OPDS 2.0 catalog",
        "application/opds+json",
        ("en", "zh-Hant"),
        True,
    ),
    FileSpec(
        "opds/family-travel-observation-passport.xml",
        "Family travel observation passport OPDS 1.2 catalog",
        "application/atom+xml;profile=opds-catalog;kind=acquisition",
        ("en", "zh-Hant"),
        True,
    ),
)


def _absolute_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _types(entity: dict) -> set[str]:
    value = entity.get("@type", [])
    return {value} if isinstance(value, str) else set(value)


def _file_entity(spec: FileSpec, pages: Path, modified: str) -> dict:
    path = pages / spec.relative_path
    if not path.is_file():
        raise FileNotFoundError(
            f"Generate all family-travel resources before the RO-Crate: {path}"
        )
    entity = {
        "@id": spec.url,
        "@type": ["File", "LearningResource"]
        if spec.learning_resource
        else "File",
        "name": spec.name,
        "description": (
            f"{spec.name}, published as part of the bilingual family-travel "
            "research object."
        ),
        "encodingFormat": spec.encoding_format,
        "contentSize": str(path.stat().st_size),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sdDatePublished": f"{modified}T00:00:00Z",
        "isPartOf": {"@id": ROOT_ID},
    }
    if spec.in_language:
        entity["inLanguage"] = spec.in_language
    return entity


def crate_graph(dataset: dict, pages: Path, modified: str) -> dict:
    file_entities = [_file_entity(spec, pages, modified) for spec in FILE_SPECS]
    file_refs = [{"@id": entity["@id"]} for entity in file_entities]
    references = [
        {
            "@id": reference["url"],
            "@type": "CreativeWork",
            "name": reference["title"],
            "publisher": reference["publisher"],
        }
        for reference in dataset["officialReferences"]
    ]
    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": ROOT_ID},
            "conformsTo": {"@id": PROFILE},
        },
        {
            "@id": ROOT_ID,
            "@type": ["Dataset", "LearningResource"],
            "name": "Family Travel Mission Taxonomy and Observation Passport",
            "description": (
                "A bilingual, privacy-first research object combining an open family-travel "
                "mission taxonomy, printable observation passport, static API and OPDS catalogs."
            ),
            "url": ROOT_ID,
            "identifier": {"@id": IDENTIFIER_ID},
            "cite-as": {"@id": ROOT_ID},
            "version": dataset["version"],
            "datePublished": dataset["dateCreated"],
            "dateModified": modified,
            "inLanguage": dataset["languages"],
            "keywords": [
                *dataset["keywords"],
                "open educational resource",
                "RO-Crate",
                "static API",
            ],
            "isAccessibleForFree": True,
            "license": {"@id": LICENSE},
            "creator": {"@id": PUBLISHER_ID},
            "publisher": {"@id": PUBLISHER_ID},
            "learningResourceType": ["Dataset", "Printable", "API"],
            "educationalUse": (
                "Family-guided observation, bilingual travel vocabulary practice and reuse "
                "in research or educational tools"
            ),
            "hasPart": file_refs,
            "subjectOf": [
                {
                    "@id": (
                        f"{SITE}/data/family-travel-missions.dcat.jsonld"
                    )
                },
                {
                    "@id": (
                        f"{SITE}/api/v1/family-travel-missions/openapi.json"
                    )
                },
                {
                    "@id": (
                        f"{SITE}/tools/"
                        "family-travel-observation-passport.metadata.json"
                    )
                },
                {
                    "@id": (
                        f"{SITE}/opds/family-travel-observation-passport.json"
                    )
                },
            ],
            "citation": [{"@id": item["url"]} for item in dataset["officialReferences"]],
        },
        {
            "@id": IDENTIFIER_ID,
            "@type": "PropertyValue",
            "name": "Family travel research object canonical identifier",
            "description": "Canonical web identifier for this research object.",
            "propertyID": "URL",
            "value": ROOT_ID,
            "url": ROOT_ID,
        },
        {
            "@id": PUBLISHER_ID,
            "@type": "Organization",
            "name": "Lumi Apps - iOS App Guide",
            "url": SITE,
            "contactPoint": {"@id": CONTACT_ID},
        },
        {
            "@id": CONTACT_ID,
            "@type": "ContactPoint",
            "name": "iOS App Guide maintainer profile",
            "url": CONTACT_ID,
        },
        {
            "@id": LICENSE,
            "@type": "CreativeWork",
            "name": "Creative Commons Attribution 4.0 International",
            "description": (
                "Permits sharing and adaptation for any purpose with attribution."
            ),
        },
        {
            "@id": PROFILE,
            "@type": "CreativeWork",
            "name": "RO-Crate Metadata Specification 1.3",
        },
        *file_entities,
        *references,
    ]
    return {"@context": CONTEXT, "@graph": graph}


def validate_crate(crate: dict, pages: Path) -> None:
    encoded = json.dumps(crate, ensure_ascii=False)
    for forbidden in FORBIDDEN:
        if forbidden in encoded:
            raise ValueError(f"RO-Crate must remain app-independent: {forbidden}")
    if crate.get("@context") != CONTEXT:
        raise ValueError("RO-Crate must use the stable 1.3 JSON-LD context")
    graph = crate.get("@graph")
    if not isinstance(graph, list):
        raise ValueError("RO-Crate @graph must be an array")
    entities = {entity.get("@id"): entity for entity in graph}
    if None in entities or len(entities) != len(graph):
        raise ValueError("Every RO-Crate entity must have a unique @id")
    descriptor = entities.get("ro-crate-metadata.json")
    if descriptor != {
        "@id": "ro-crate-metadata.json",
        "@type": "CreativeWork",
        "about": {"@id": ROOT_ID},
        "conformsTo": {"@id": PROFILE},
    }:
        raise ValueError("Detached RO-Crate descriptor does not conform to RO-Crate 1.3")
    root = entities.get(ROOT_ID)
    if not root or "Dataset" not in _types(root):
        raise ValueError("RO-Crate root data entity must be a Dataset")
    for field in (
        "name",
        "description",
        "datePublished",
        "dateModified",
        "license",
        "publisher",
        "hasPart",
    ):
        if not root.get(field):
            raise ValueError(f"RO-Crate root Dataset is missing {field}")
    if root["license"] != {"@id": LICENSE}:
        raise ValueError("RO-Crate root Dataset must declare CC BY 4.0")
    if (
        root.get("identifier") != {"@id": IDENTIFIER_ID}
        or root.get("cite-as") != {"@id": ROOT_ID}
    ):
        raise ValueError("RO-Crate root Dataset must cite its canonical URL")
    expected_urls = {spec.url for spec in FILE_SPECS}
    part_urls = {part.get("@id") for part in root["hasPart"]}
    if part_urls != expected_urls:
        raise ValueError("RO-Crate hasPart does not match the published resource set")
    file_entities = {
        identifier: entity
        for identifier, entity in entities.items()
        if "File" in _types(entity)
    }
    if set(file_entities) != expected_urls:
        raise ValueError("Every published resource must have one RO-Crate File entity")
    specs = {spec.url: spec for spec in FILE_SPECS}
    for url, entity in file_entities.items():
        if not _absolute_https(url):
            raise ValueError(f"RO-Crate Web File @id must be an absolute HTTPS URL: {url}")
        spec = specs[url]
        path = pages / spec.relative_path
        if entity.get("encodingFormat") != spec.encoding_format:
            raise ValueError(f"RO-Crate encodingFormat mismatch: {url}")
        if entity.get("contentSize") != str(path.stat().st_size):
            raise ValueError(f"RO-Crate contentSize mismatch: {url}")
        if not entity.get("description"):
            raise ValueError(f"RO-Crate File description is missing: {url}")
        if entity.get("sdDatePublished") != f"{root['dateModified']}T00:00:00Z":
            raise ValueError(f"RO-Crate File sdDatePublished mismatch: {url}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if entity.get("sha256") != digest:
            raise ValueError(f"RO-Crate SHA-256 mismatch: {url}")
        if entity.get("isPartOf") != {"@id": ROOT_ID}:
            raise ValueError(f"RO-Crate File isPartOf mismatch: {url}")
    if METADATA_URL in expected_urls:
        raise ValueError("Detached RO-Crate metadata must not include itself as a data entity")


def _json(crate: dict) -> str:
    return json.dumps(crate, ensure_ascii=False, indent=2) + "\n"


def _prior_modified(path: Path, dataset: dict) -> str:
    if not path.exists():
        return dataset["dateCreated"]
    try:
        crate = json.loads(path.read_text(encoding="utf-8"))
        root = next(entity for entity in crate["@graph"] if entity["@id"] == ROOT_ID)
        modified = root["dateModified"]
    except (json.JSONDecodeError, KeyError, StopIteration, TypeError) as error:
        raise ValueError(f"Existing RO-Crate metadata is invalid: {path}") from error
    if not isinstance(modified, str) or len(modified) != 10:
        raise ValueError(f"Existing RO-Crate dateModified is invalid: {modified}")
    return modified


def render_sitemap(modified: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{METADATA_URL}</loc><lastmod>{modified}</lastmod></url>\n"
        "</urlset>\n"
    )


def build(pages: Path = PAGES) -> list[str]:
    dataset = load_dataset()
    data_dir = pages / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = data_dir / FILENAME
    prior_date = _prior_modified(metadata_path, dataset)
    crate = crate_graph(dataset, pages, prior_date)
    validate_crate(crate, pages)
    candidate = _json(crate)
    existing = (
        metadata_path.read_text(encoding="utf-8") if metadata_path.exists() else ""
    )
    modified = prior_date
    if candidate != existing:
        modified = TODAY
        crate = crate_graph(dataset, pages, modified)
        validate_crate(crate, pages)
        candidate = _json(crate)
    write_text_if_changed(metadata_path, candidate)
    write_text_if_changed(
        pages / "sitemap_ro_crate.xml", render_sitemap(modified)
    )
    return [METADATA_URL, SITEMAP_URL]


def main() -> None:
    for output in build():
        print(f"family travel RO-Crate -> {output}")


if __name__ == "__main__":
    main()
