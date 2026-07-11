#!/usr/bin/env python3
"""Build static OPDS 2.0 and OPDS 1.2 catalogs for the travel passport OER."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from family_travel_dataset import (
    APP_ID,
    APP_NAME,
    SITE,
    load_dataset,
    write_text_if_changed,
)
from family_travel_observation_passport import (
    COPY,
    INITIAL_DATE,
    LICENSE,
    METADATA_URL,
    OPDS1_URL,
    OPDS2_URL,
    PAGES,
    SLUG,
    canonical,
    make_pdf_artifacts,
)


ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"
INTEGRITY_NS = f"{METADATA_URL}#"
XML_NS = "http://www.w3.org/XML/1998/namespace"
OPDS2_MEDIA_TYPE = "application/opds+json"
OPDS1_MEDIA_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"
OPEN_ACCESS_REL = "http://opds-spec.org/acquisition/open-access"
SITEMAP_URL = f"{SITE}/sitemap_opds.xml"
TODAY = dt.date.today().isoformat()
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FORBIDDEN = (
    "apps.apple.com",
    "SoftwareApplication",
    APP_NAME,
    APP_ID,
)

ET.register_namespace("", ATOM_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("integrity", INTEGRITY_NS)


def _atom(tag: str) -> str:
    return f"{{{ATOM_NS}}}{tag}"


def _dc(tag: str) -> str:
    return f"{{{DC_NS}}}{tag}"


def _integrity(tag: str) -> str:
    return f"{{{INTEGRITY_NS}}}{tag}"


def _timestamp(date: str) -> str:
    return f"{date}T00:00:00Z"


def _absolute_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _artifact_index(artifacts: dict[str, dict[str, dict]]) -> dict[str, dict]:
    return {
        artifact["url"]: artifact
        for locale_artifacts in artifacts.values()
        for artifact in locale_artifacts.values()
    }


def _checksum(artifact: dict) -> dict:
    return {
        "algorithm": "sha-256",
        "encoding": "hex",
        "value": artifact["sha256"],
    }


def _accessibility(locale: str) -> dict:
    summary = {
        "en": (
            "Each PDF has selectable text, and the linked HTML edition provides the "
            "same instructions and prompts. No PDF/UA conformance is claimed."
        ),
        "zh-Hant": (
            "每份 PDF 均有可選取文字，連結的 HTML 版本提供相同指示與提示。"
            "本資源不宣稱符合 PDF/UA。"
        ),
    }
    return {
        "accessMode": ["textual", "visual"],
        "accessModeSufficient": ["textual"],
        "hazard": [
            "noFlashingHazard",
            "noMotionSimulationHazard",
            "noSoundHazard",
        ],
        "summary": summary[locale],
    }


def _publication(
    dataset: dict,
    locale: str,
    modified: str,
    artifacts: dict[str, dict],
) -> dict:
    copy = COPY[locale]
    links = [
        {
            "rel": "alternate",
            "href": canonical(locale),
            "type": "text/html",
            "title": copy["title"],
        },
        {
            "rel": "describedby",
            "href": METADATA_URL,
            "type": "application/ld+json",
            "title": "Schema.org LearningResource metadata",
        },
    ]
    for size_name, artifact in artifacts.items():
        links.append(
            {
                "rel": OPEN_ACCESS_REL,
                "href": artifact["url"],
                "type": "application/pdf",
                "title": copy[size_name],
                "size": len(artifact["bytes"]),
                "language": locale,
                "properties": {"checksum": _checksum(artifact)},
            }
        )
    return {
        "metadata": {
            "@type": "https://schema.org/LearningResource",
            "identifier": f"{canonical(locale)}#resource",
            "title": copy["title"],
            "description": copy["description"],
            "language": locale,
            "published": INITIAL_DATE,
            "modified": modified,
            "author": {
                "name": "Lumi Apps - iOS App Guide",
                "identifier": SITE,
            },
            "publisher": {
                "name": "Lumi Apps - iOS App Guide",
                "identifier": SITE,
            },
            "license": LICENSE,
            "isAccessibleForFree": True,
            "educationalUse": copy["learning_use"],
            "numberOfPages": 14,
            "version": dataset["version"],
            "accessibility": _accessibility(locale),
        },
        "links": links,
    }


def opds2_catalog(
    dataset: dict,
    modified: str,
    artifacts: dict[str, dict[str, dict]],
) -> dict:
    return {
        "metadata": {
            "identifier": OPDS2_URL,
            "title": "Family Travel Observation Passport OER Catalog",
            "description": (
                "Open-access English and Traditional Chinese editions of a privacy-first "
                "family travel observation passport."
            ),
            "modified": modified,
            "numberOfItems": len(COPY),
        },
        "links": [
            {
                "rel": "self",
                "href": OPDS2_URL,
                "type": OPDS2_MEDIA_TYPE,
            },
            {
                "rel": "alternate",
                "href": OPDS1_URL,
                "type": OPDS1_MEDIA_TYPE,
                "title": "OPDS 1.2 catalog",
            },
            {
                "rel": "alternate",
                "href": canonical("en"),
                "type": "text/html",
                "title": COPY["en"]["title"],
            },
        ],
        "publications": [
            _publication(dataset, locale, modified, artifacts[locale])
            for locale in COPY
        ],
    }


def _add_text(parent: ET.Element, tag: str, text: str, **attributes: str) -> ET.Element:
    element = ET.SubElement(parent, tag, attributes)
    element.text = text
    return element


def _add_author(parent: ET.Element) -> None:
    author = ET.SubElement(parent, _atom("author"))
    _add_text(author, _atom("name"), "Lumi Apps - iOS App Guide")
    _add_text(author, _atom("uri"), SITE)


def opds1_catalog(
    dataset: dict,
    modified: str,
    artifacts: dict[str, dict[str, dict]],
) -> str:
    root = ET.Element(_atom("feed"))
    _add_text(root, _atom("id"), OPDS1_URL)
    _add_text(root, _atom("title"), "Family Travel Observation Passport OER Catalog")
    _add_text(root, _atom("updated"), modified)
    _add_author(root)
    for relation, href, media_type, title in (
        ("self", OPDS1_URL, OPDS1_MEDIA_TYPE, "OPDS 1.2 catalog"),
        ("start", OPDS1_URL, OPDS1_MEDIA_TYPE, "Catalog root"),
        ("alternate", OPDS2_URL, OPDS2_MEDIA_TYPE, "OPDS 2.0 catalog"),
        ("alternate", canonical("en"), "text/html", COPY["en"]["title"]),
        ("license", LICENSE, "text/html", "CC BY 4.0"),
    ):
        ET.SubElement(
            root,
            _atom("link"),
            {"rel": relation, "href": href, "type": media_type, "title": title},
        )

    for locale in COPY:
        copy = COPY[locale]
        entry = ET.SubElement(root, _atom("entry"))
        _add_text(entry, _atom("id"), f"{canonical(locale)}#resource")
        title = _add_text(entry, _atom("title"), copy["title"])
        title.set(f"{{{XML_NS}}}lang", locale)
        _add_text(entry, _atom("updated"), modified)
        _add_text(entry, _atom("published"), _timestamp(INITIAL_DATE))
        _add_author(entry)
        summary = _add_text(entry, _atom("summary"), copy["description"], type="text")
        summary.set(f"{{{XML_NS}}}lang", locale)
        _add_text(
            entry,
            _atom("rights"),
            "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        )
        _add_text(entry, _dc("identifier"), f"{canonical(locale)}#resource")
        _add_text(entry, _dc("language"), locale)
        _add_text(entry, _dc("issued"), INITIAL_DATE)
        _add_text(entry, _dc("rights"), LICENSE)
        _add_text(entry, _dc("hasVersion"), dataset["version"])
        ET.SubElement(
            entry,
            _atom("category"),
            {"term": "OER", "label": "Open educational resource"},
        )
        for relation, href, media_type, title_text in (
            ("alternate", canonical(locale), "text/html", copy["title"]),
            (
                "describedby",
                METADATA_URL,
                "application/ld+json",
                "Schema.org LearningResource metadata",
            ),
            ("license", LICENSE, "text/html", "CC BY 4.0"),
        ):
            ET.SubElement(
                entry,
                _atom("link"),
                {
                    "rel": relation,
                    "href": href,
                    "type": media_type,
                    "title": title_text,
                },
            )
        for size_name, artifact in artifacts[locale].items():
            link = ET.SubElement(
                entry,
                _atom("link"),
                {
                    "rel": OPEN_ACCESS_REL,
                    "href": artifact["url"],
                    "type": "application/pdf",
                    "title": copy[size_name],
                    "length": str(len(artifact["bytes"])),
                },
            )
            _add_text(
                link,
                _integrity("checksum"),
                artifact["sha256"],
                algorithm="sha-256",
                encoding="hex",
            )

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8") + "\n"


def _assert_no_blank(value, path: str = "$") -> None:
    if value is None or value == "" or value == [] or value == {}:
        raise ValueError(f"OPDS catalog contains a blank value at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_no_blank(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_blank(child, f"{path}[{index}]")


def _json_acquisitions(catalog: dict) -> dict[str, tuple[int, str]]:
    acquired = {}
    for publication in catalog["publications"]:
        for link in publication["links"]:
            if link.get("rel") != OPEN_ACCESS_REL:
                continue
            checksum = link.get("properties", {}).get("checksum", {})
            if checksum.get("algorithm") != "sha-256" or checksum.get("encoding") != "hex":
                raise ValueError("Every OPDS 2.0 acquisition must expose a SHA-256 hex checksum")
            acquired[link["href"]] = (link["size"], checksum.get("value", ""))
    return acquired


def validate_opds2(
    catalog: dict,
    artifacts: dict[str, dict[str, dict]],
) -> dict[str, tuple[int, str]]:
    encoded = json.dumps(catalog, ensure_ascii=False)
    for forbidden in FORBIDDEN:
        if forbidden in encoded:
            raise ValueError(f"OPDS catalogs must remain app-independent: {forbidden}")
    _assert_no_blank(catalog)
    metadata = catalog.get("metadata", {})
    if metadata.get("title") != "Family Travel Observation Passport OER Catalog":
        raise ValueError("OPDS 2.0 feed metadata must include the canonical title")
    if not TIMESTAMP_RE.fullmatch(metadata.get("modified", "")):
        raise ValueError("OPDS 2.0 modified must be an RFC 3339 UTC timestamp")
    if metadata.get("numberOfItems") != len(COPY):
        raise ValueError("OPDS 2.0 numberOfItems must match the publication count")
    self_links = [
        link
        for link in catalog.get("links", [])
        if link.get("rel") == "self"
        and link.get("href") == OPDS2_URL
        and link.get("type") == OPDS2_MEDIA_TYPE
    ]
    if len(self_links) != 1:
        raise ValueError("OPDS 2.0 feed must contain one typed self link")
    publications = catalog.get("publications", [])
    if len(publications) != len(COPY):
        raise ValueError("OPDS 2.0 feed must contain both language editions")
    languages = {publication["metadata"].get("language") for publication in publications}
    if languages != set(COPY):
        raise ValueError("OPDS 2.0 publication languages must be en and zh-Hant")
    identifiers = {publication["metadata"].get("identifier") for publication in publications}
    if len(identifiers) != len(COPY):
        raise ValueError("OPDS 2.0 publication identifiers must be unique")
    for publication in publications:
        publication_metadata = publication["metadata"]
        if publication_metadata.get("license") != LICENSE:
            raise ValueError("Every OPDS 2.0 publication must declare CC BY 4.0")
        if publication_metadata.get("numberOfPages") != 14:
            raise ValueError("Every OPDS 2.0 publication must declare 14 pages")
        accessibility = publication_metadata.get("accessibility", {})
        if accessibility.get("accessModeSufficient") != ["textual"]:
            raise ValueError("Text alone must be sufficient for every publication")
        acquisition_links = [
            link for link in publication["links"] if link.get("rel") == OPEN_ACCESS_REL
        ]
        if len(acquisition_links) != 2:
            raise ValueError("Each publication must expose A4 and US Letter acquisitions")
        for link in publication["links"]:
            if not _absolute_https(link["href"]):
                raise ValueError(f"OPDS links must use absolute HTTPS URLs: {link['href']}")
    acquired = _json_acquisitions(catalog)
    expected = {
        url: (len(artifact["bytes"]), artifact["sha256"])
        for url, artifact in _artifact_index(artifacts).items()
    }
    if acquired != expected:
        raise ValueError("OPDS 2.0 acquisition sizes or checksums do not match the PDFs")
    return acquired


def validate_opds1(
    xml_text: str,
    modified: str,
    artifacts: dict[str, dict[str, dict]],
) -> dict[str, tuple[int, str]]:
    for forbidden in FORBIDDEN:
        if forbidden in xml_text:
            raise ValueError(f"OPDS catalogs must remain app-independent: {forbidden}")
    root = ET.fromstring(xml_text)
    if root.tag != _atom("feed"):
        raise ValueError("OPDS 1.2 catalog root must be an Atom feed")
    if root.findtext(_atom("id")) != OPDS1_URL:
        raise ValueError("OPDS 1.2 feed must have a stable identifier")
    if root.findtext(_atom("updated")) != modified:
        raise ValueError("OPDS 1.2 feed timestamp must match OPDS 2.0")
    feed_links = root.findall(_atom("link"))
    if not any(
        link.get("rel") == "self"
        and link.get("href") == OPDS1_URL
        and link.get("type") == OPDS1_MEDIA_TYPE
        for link in feed_links
    ):
        raise ValueError("OPDS 1.2 feed must contain a typed self link")
    if not any(
        link.get("rel") == "start" and link.get("href") == OPDS1_URL
        for link in feed_links
    ):
        raise ValueError("OPDS 1.2 feed must identify its catalog root")
    entries = root.findall(_atom("entry"))
    if len(entries) != len(COPY):
        raise ValueError("OPDS 1.2 feed must contain both language editions")
    acquired = {}
    languages = set()
    for entry in entries:
        language = entry.findtext(_dc("language"))
        languages.add(language)
        if entry.findtext(_dc("rights")) != LICENSE:
            raise ValueError("Every OPDS 1.2 entry must declare CC BY 4.0")
        links = [
            link
            for link in entry.findall(_atom("link"))
            if link.get("rel") == OPEN_ACCESS_REL
        ]
        if len(links) != 2:
            raise ValueError("Each OPDS 1.2 entry must expose two PDF acquisitions")
        for link in links:
            checksum = link.find(_integrity("checksum"))
            if (
                link.get("type") != "application/pdf"
                or checksum is None
                or checksum.get("algorithm") != "sha-256"
                or checksum.get("encoding") != "hex"
            ):
                raise ValueError("OPDS 1.2 acquisitions require PDF type and SHA-256")
            acquired[link.get("href", "")] = (
                int(link.get("length", "0")),
                checksum.text or "",
            )
    if languages != set(COPY):
        raise ValueError("OPDS 1.2 entry languages must be en and zh-Hant")
    expected = {
        url: (len(artifact["bytes"]), artifact["sha256"])
        for url, artifact in _artifact_index(artifacts).items()
    }
    if acquired != expected:
        raise ValueError("OPDS 1.2 acquisition sizes or checksums do not match the PDFs")
    return acquired


def render_catalogs(
    dataset: dict,
    modified_date: str,
    artifacts: dict[str, dict[str, dict]],
) -> tuple[str, str]:
    modified = _timestamp(modified_date)
    catalog = opds2_catalog(dataset, modified, artifacts)
    json_text = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    xml_text = opds1_catalog(dataset, modified, artifacts)
    if json.loads(json_text) != catalog:
        raise ValueError("OPDS 2.0 serialization did not round-trip")
    if validate_opds2(catalog, artifacts) != validate_opds1(
        xml_text, modified, artifacts
    ):
        raise ValueError("OPDS 2.0 and OPDS 1.2 acquisitions are not symmetric")
    return json_text, xml_text


def _prior_modified(json_path: Path) -> str:
    if not json_path.exists():
        return INITIAL_DATE
    try:
        modified = json.loads(json_path.read_text(encoding="utf-8"))["metadata"][
            "modified"
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"Existing OPDS 2.0 catalog is invalid: {json_path}") from error
    if not TIMESTAMP_RE.fullmatch(modified):
        raise ValueError(f"Existing OPDS 2.0 timestamp is invalid: {modified}")
    return modified[:10]


def _verify_pdf_files(
    pages: Path,
    artifacts: dict[str, dict[str, dict]],
) -> None:
    for artifact in _artifact_index(artifacts).values():
        path = pages / "tools" / artifact["filename"]
        if not path.exists():
            raise FileNotFoundError(f"Generate the passport PDFs before OPDS catalogs: {path}")
        if path.read_bytes() != artifact["bytes"]:
            raise ValueError(f"Published PDF differs from the OPDS artifact: {path}")


def render_sitemap(modified_date: str) -> str:
    rows = "\n".join(
        f"  <url><loc>{url}</loc><lastmod>{modified_date}</lastmod></url>"
        for url in (OPDS2_URL, OPDS1_URL)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def build(
    pages: Path = PAGES,
    artifacts: dict[str, dict[str, dict]] | None = None,
) -> list[str]:
    dataset = load_dataset()
    artifacts = artifacts or make_pdf_artifacts(dataset)
    _verify_pdf_files(pages, artifacts)
    opds_dir = pages / "opds"
    opds_dir.mkdir(parents=True, exist_ok=True)
    json_path = opds_dir / f"{SLUG}.json"
    xml_path = opds_dir / f"{SLUG}.xml"
    prior_date = _prior_modified(json_path)
    candidate_json, candidate_xml = render_catalogs(dataset, prior_date, artifacts)
    existing_json = json_path.read_text(encoding="utf-8") if json_path.exists() else ""
    existing_xml = xml_path.read_text(encoding="utf-8") if xml_path.exists() else ""
    modified_date = prior_date
    if candidate_json != existing_json or candidate_xml != existing_xml:
        modified_date = TODAY
        candidate_json, candidate_xml = render_catalogs(dataset, modified_date, artifacts)
    write_text_if_changed(json_path, candidate_json)
    write_text_if_changed(xml_path, candidate_xml)
    write_text_if_changed(pages / "sitemap_opds.xml", render_sitemap(modified_date))
    return [OPDS2_URL, OPDS1_URL, SITEMAP_URL]


def main() -> None:
    for output in build():
        print(f"family travel OPDS catalog -> {output}")


if __name__ == "__main__":
    main()
