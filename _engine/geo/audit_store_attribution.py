#!/usr/bin/env python3
"""Fail closed on incomplete App Store attribution in the final public tree.

Run after every generator, including feeds and downloadable artifacts:
    python geo/audit_store_attribution.py --pages-dir geo/pages --report report.json

This gate is read-only and uses the cached Apple live/storefront snapshots.
It checks HTML, structured APIs, feed enclosures, browser payloads, QR pixels,
PDF annotations and archive members. IDs, canonical/hreflang and developer
profiles stay clean and never count as download CTAs. Supplemental languages
may use verified-app global URLs, but never an unverified country guess.
The official catalog still requires every verified app in all 50 locales.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import dataclass
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

from app_store_storefronts import (
    APP_STORE_PATH_RE,
    LOCALE_STOREFRONTS,
    PROVIDER_TOKEN_RE,
    STATE_FILE,
    is_clean_app_store_developer_url,
    load_storefront_availability,
    resolve_provider_token,
    storefront_locale_for_url,
    validated_app_store_url,
)
from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
EXCLUDED_PARTS = {".git", "_engine", "node_modules", "__pycache__"}
TEXT_SUFFIXES = {
    ".html", ".htm", ".xhtml", ".json", ".jsonld", ".jsonl", ".csv", ".webmanifest",
    ".xml", ".svg", ".rss", ".atom", ".opf", ".js", ".mjs", ".md", ".txt", ".ics", ".vcf",
}
JSON_ENDPOINTS = {".well-known/api-catalog"}
ACTION_FIELDS = {
    "app_store_url", "appstore_url", "appstoreurl", "store_url",
    "installurl", "downloadurl", "external_url",
}
IDENTITY_FIELDS = {
    "@id", "id", "guid", "sameas", "canonical", "canonical_url", "identifier", "anchor",
    "canonical_app_store_url", "storefront_url", "citation", "source", "sources",
    # Provenance: these say where a dataset or article came from. They are
    # identity, never a call to action, so they must stay a clean canonical URL.
    "source_url", "dc:source", "dcterms:source", "isbasedon", "mainentityofpage",
}
# JSON Schema / OpenAPI value keywords describe the *shape* of a document, not a
# link a visitor can follow: ``pattern`` is a regular expression that may spell
# out ``pt=``, ``enum``/``examples``/``default``/``const`` are sample values.
# Inside a schema node they are opaque — never a Reference, never stamped.
SCHEMA_VALUE_FIELDS = {"const", "enum", "default", "examples", "example", "pattern"}
SCHEMA_NODE_FIELDS = {
    "$schema", "type", "properties", "items", "$ref", "$defs", "definitions",
    "oneof", "anyof", "allof", "openapi", "components",
}
# Only ASCII characters RFC 3986 allows in a URL, and never the quote, bracket
# and backslash characters that delimit URLs in HTML/JS/JSON. Text right after
# a link — CJK, Thai, full-width punctuation — is not part of the link, and a
# trailing sentence mark (``.,;:!?``) belongs to the prose, not the URL.
STORE_TEXT_RE = re.compile(
    r"(?:https?://|itms-apps://|//)apps\.apple\.com"
    r"(?:[A-Za-z0-9\-._~:/?#@!$&*+;=%]*[A-Za-z0-9\-_~/#@$&*+=%])?",
    re.IGNORECASE,
)
JS_STRING_RE = re.compile(r"""(?P<quote>["'`])(?P<body>(?:\\.|[^\\])*?)(?P=quote)""")
FIELD_RE = re.compile(r"""(?:["'](?P<quoted>[\w@-]+)["']|(?P<bare>[\w@-]+))\s*:\s*$""")
SCRIPT_RE = re.compile(
    r"(?P<open><script\b[^>]*>)(?P<body>.*?)(?P<close></script\s*>)",
    re.IGNORECASE | re.DOTALL,
)
QR_NAME_RE = re.compile(r"id(?P<app>\d{9,12})-(?P<digest>[0-9a-f]{20})\.svg")
REQUIRED_SURFACES = frozenset({"html", "api", "feed", "qr", "download", "tool"})


class AttributionError(ValueError):
    """A generated surface is not safe to publish."""

    def __init__(self, message: str, *, failures=(), summary=None):
        super().__init__(message)
        self.failures = list(failures)
        self.summary = summary or {}


@dataclass(frozen=True)
class Reference:
    url: str
    field: str
    locale: str | None = None
    app_id: str | None = None
    identity: bool = False
    surface: str = ""


def locale_of(path: str) -> str | None:
    for part in reversed(Path(path).parts):
        candidate = part.split(".", 1)[0]
        if candidate in LOCALE_STOREFRONTS:
            return candidate
    return None


def _locale(value: object, fallback: str | None) -> str | None:
    if value is None:
        return fallback
    if fallback and value == fallback.split("-")[0]:
        return fallback
    if value == "en":
        return "en-US"
    if not isinstance(value, str):
        raise AttributionError(f"Unsupported attribution locale: {value!r}")
    # Non-App metadata may use human-readable languages. A CTA carrying one
    # still fails in validated_app_store_url; unrelated metadata is not a link.
    return value


def is_store_url(value: str) -> bool:
    return "apps.apple.com" in value.casefold()


def identity_field(field: str, parent: dict | None = None) -> bool:
    field = field.casefold()
    return field in IDENTITY_FIELDS or field.startswith("canonical")


def schema_node(value: object, inherited: bool = False) -> bool:
    """True when ``value`` is (or sits inside) a JSON Schema / OpenAPI node."""
    if inherited:
        return True
    return isinstance(value, dict) and any(
        isinstance(key, str) and key.casefold() in SCHEMA_NODE_FIELDS for key in value
    )


def schema_value_field(field: str, parent: object, inherited: bool = False) -> bool:
    """Schema sample/regex keywords are opaque: not a link, never stamped."""
    return field.casefold() in SCHEMA_VALUE_FIELDS and schema_node(parent, inherited)


def _text_references(value: str, field: str, locale: str | None,
                     app_id: str | None, identity: bool = False):
    for match in STORE_TEXT_RE.finditer(value):
        yield Reference(match.group().rstrip(".,;"), field, locale, app_id, identity)


def json_references(value: object, *, locale: str | None = None,
                    app_id: str | None = None, field: str = "",
                    identity: bool = False, linked_app_id: str | None = None,
                    schema: bool = False):
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise AttributionError("Malformed object or CSV column count")
        schema = schema_node(value, schema)
        local = next(
            (value[name] for name in ("locale", "page_language", "content_language",
                                     "language", "inLanguage")
             if isinstance(value.get(name), str)),
            None,
        )
        locale = _locale(local, locale)
        own_id = value.get("app_store_id", value.get("appStoreId"))
        if own_id is None and any(key in value for key in ("external_url", "content_html", "content_text")):
            metadata_ids = {
                str(child["app_store_id"])
                for key, child in value.items()
                if key.startswith("_") and isinstance(child, dict) and child.get("app_store_id")
            }
            if len(metadata_ids) > 1:
                raise AttributionError("Conflicting JSON Feed App Store IDs")
            own_id = next(iter(metadata_ids), None)
        if value.get("platform") == "itunes":
            own_id = value.get("id")
            if not isinstance(value.get("url"), str) or not value["url"]:
                raise AttributionError("Missing PWA App Store URL")
        if isinstance(own_id, (str, int)):
            app_id = str(own_id)
            if not re.fullmatch(r"\d{9,12}", app_id):
                raise AttributionError(f"Invalid App Store record ID: {app_id!r}")
            has_link = any(
                key.casefold() in ACTION_FIELDS
                for key in value
            )
            site_descriptor = {
                "schemaVersion", "appStoreId", "urlPattern", "pagesPerLocale"
            }.issubset(value)
            if not has_link and linked_app_id not in {None, app_id}:
                raise AttributionError("Conflicting nested App Store record ID")
            if value.get("platform") != "itunes" and not has_link and linked_app_id != app_id and not site_descriptor:
                raise AttributionError(f"Missing App Store link in record {app_id}")
            if has_link:
                linked_app_id = app_id
        if (
            isinstance(value.get("id"), str) and is_store_url(value["id"])
            and not is_clean_app_store_developer_url(value["id"])
        ):
            has_destination = any(key.casefold() in ACTION_FIELDS for key in value) or (
                isinstance(value.get("url"), str) and is_store_url(value["url"])
            )
            if not identity and not has_destination:
                raise AttributionError("App Store feed item is missing a destination link")
            canonical = validated_app_store_url(value["id"])
            app_id = APP_STORE_PATH_RE.fullmatch(urllib.parse.urlsplit(canonical).path)["app_id"]
        for key, child in value.items():
            if schema and key.casefold() in SCHEMA_VALUE_FIELDS:
                continue
            child_identity = identity or identity_field(key, value)
            if key.casefold() in ACTION_FIELDS and not isinstance(child, (dict, list)):
                if not isinstance(child, str) or not child.strip():
                    raise AttributionError(f"Missing App Store link: {key}")
                if key.casefold() in {"app_store_url", "appstore_url", "appstoreurl", "store_url"} or (
                    app_id is not None and key.casefold() in {"external_url", "installurl"}
                ):
                    yield Reference(child, key, locale, app_id)
                    continue
            yield from json_references(
                child, locale=locale, app_id=app_id, field=key, identity=child_identity,
                linked_app_id=linked_app_id, schema=schema,
            )
    elif isinstance(value, list):
        for child in value:
            yield from json_references(
                child, locale=locale, app_id=app_id, field=field, identity=identity,
                linked_app_id=linked_app_id, schema=schema,
            )
    elif isinstance(value, str):
        if identity:
            _clean_identity(value, field)
        if value.startswith(("https://apps.", "http://apps.", "//apps.")):
            yield Reference(value, field, locale, app_id, identity)
        elif "<a" in value.casefold():
            yield from html_references(value, locale=locale)
        else:
            yield from _text_references(value, field, locale, app_id, identity)


def js_strings(source: str):
    """Decode URL literals, including JSON's escaped slashes and ampersands."""
    for match in JS_STRING_RE.finditer(source):
        body = match["body"]
        if match["quote"] == "'":
            body = body.replace(r"\'", "'").replace('"', r'\"')
        elif match["quote"] == "`":
            if "${" in body and is_store_url(body):
                raise AttributionError("App Store template URL cannot contain dynamic interpolation")
            body = body.replace(r"\`", "`").replace('"', r'\"').replace("\n", r"\n").replace("\r", r"\r")
        body = re.sub(r"\\x([0-9a-fA-F]{2})", r"\\u00\1", body)
        try:
            decoded = json.loads(f'"{body}"')
        except ValueError:
            if "apps.apple.com" in body:
                raise AttributionError("Unparseable App Store JavaScript literal")
            continue
        preceding = FIELD_RE.search(source[max(0, match.start() - 100):match.start()])
        field = (preceding["quoted"] or preceding["bare"]) if preceding else ""
        if field.casefold() not in ACTION_FIELDS and (
            re.search(r"\[(?:href|data-[\w-]*url)\s*[~|^$*]?=", decoded)
            or re.search(
                r"(?:\.(?:startsWith|endsWith|indexOf|includes)\(|===|!==|==|!=)\s*$",
                source[max(0, match.start() - 60):match.start()],
            )
        ):
            continue
        yield match, decoded, field


def js_references(source: str, locale: str | None):
    for _, value, field in js_strings(source):
        if field.casefold() in ACTION_FIELDS and not value:
            raise AttributionError(f"Missing tool App Store link: {field}")
        if field.casefold() in {"app_store_url", "appstore_url", "appstoreurl", "store_url"}:
            yield Reference(value, field, locale)
            continue
        if is_store_url(value):
            yield from _text_references(
                value, field or "JavaScript URL", locale, None, identity_field(field)
            )


def _clean_identity(value: str, field: str) -> None:
    parsed = urllib.parse.urlsplit(value)
    parameters = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if any(key.casefold() in {"pt", "ct", "mt"} or key.casefold().startswith("utm_")
           for key, _ in parameters):
        raise AttributionError(f"Tracking parameters on {field}: {value}")


class _HTMLReferences(HTMLParser):
    def __init__(self, locale: str | None):
        super().__init__(convert_charrefs=True)
        self.locale = locale
        self.references: list[Reference] = []
        self.script_type: str | None = None
        self.script_parts: list[str] = []
        self.qr_cards: list[tuple[str, str]] = []
        self.qr_containers = 0
        self.qr_href: str | None = None
        self.qr_image = False

    def handle_starttag(self, tag, attrs):
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            raise AttributionError(f"Duplicate HTML attributes on <{tag}>")
        values = dict(attrs)
        if tag == "html" and values.get("lang"):
            declared = _locale(values["lang"], self.locale)
            self.locale = self.locale or declared
        if tag == "script":
            self.script_type = values.get("type", "").casefold()
            self.script_parts = []
        if tag == "link" and (
            "canonical" in (values.get("rel") or "").casefold().split()
            or "hreflang" in values
        ):
            href = values.get("href")
            if not href:
                raise AttributionError("Missing canonical/hreflang href")
            _clean_identity(href, "canonical/hreflang")
            if is_store_url(href):
                self.references.append(Reference(href, "canonical/hreflang", identity=True))
            return
        classes = (values.get("class") or "").split()
        self.qr_containers += int("app-store-qr-card" in classes)
        if tag in {"a", "area"} and any("store" in name for name in classes):
            if not values.get("href"):
                raise AttributionError("App Store CTA has no href")
        if "app-store-qr-card__link" in classes:
            self.qr_href = values.get("href")
            self.qr_image = False
            if not self.qr_href:
                raise AttributionError("QR card has no App Store link")
        if "app-store-qr-card__image" in classes:
            if not self.qr_href or not values.get("src"):
                raise AttributionError("QR card has no matching link/image")
            self.qr_cards.append((self.qr_href, values["src"]))
            self.qr_image = True
        if tag == "meta" and (values.get("name") or "").casefold() == "apple-itunes-app":
            parameters = dict(
                part.strip().split("=", 1)
                for part in (values.get("content") or "").split(",") if "=" in part
            )
            app_id = parameters.get("app-id", "")
            affiliate = parameters.get("affiliate-data", "")
            self.references.append(Reference(
                f"https://apps.apple.com/app/id{app_id}?{affiliate}",
                "Smart App Banner", self.locale or "en-US", app_id,
            ))
        for name, value in attrs:
            if name == "data-app-store-url" and not value:
                raise AttributionError("Missing App Store share URL")
            if not value:
                continue
            if is_store_url(value) or name == "data-app-store-url":
                if name not in {"href", "action", "content"} and not name.startswith("data-"):
                    continue
                if tag == "meta" and name == "content":
                    continue
                identity = (
                    name == "data-store-url" and tag == "span"
                    and "app-store-qr-card__url" in classes
                    and values.get("aria-hidden") == "true"
                )
                local = _locale(values.get("data-locale") or values.get("lang"), self.locale or "en-US")
                self.references.append(Reference(value, name, local, identity=identity))

    handle_startendtag = handle_starttag

    def close(self):
        super().close()
        if self.qr_containers and self.qr_containers != len(self.qr_cards):
            raise AttributionError("QR card is missing its link or image")

    def handle_data(self, data):
        if self.script_type is not None:
            self.script_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.qr_href is not None:
            if not self.qr_image:
                raise AttributionError("QR card has no image")
            self.qr_href = None
        if tag == "script" and self.script_type is not None:
            source = "".join(self.script_parts)
            if self.script_type in {"application/json", "application/ld+json"}:
                refs = json_references(json.loads(source), locale=self.locale or "en-US")
            else:
                refs = js_references(source, self.locale or "en-US")
            surface = "tool" if self.script_type != "application/ld+json" else "html"
            self.references.extend(
                Reference(ref.url, ref.field, ref.locale, ref.app_id, ref.identity, surface)
                for ref in refs
            )
            self.script_type = None


def html_references(source: str, *, locale: str | None = None):
    parser = _HTMLReferences(locale)
    parser.feed(source)
    parser.close()
    if parser.script_type is not None or parser.qr_href is not None:
        raise AttributionError("Unclosed script or QR card")
    yield from parser.references


def normalized_reference(ref: Reference) -> Reference:
    if not is_clean_app_store_developer_url(ref.url):
        return ref
    if ref.field.casefold() in ACTION_FIELDS | {
        "canonical_app_store_url", "storefront_url", "data-app-store-url",
    }:
        raise AttributionError(f"An App Store CTA cannot point to a developer profile: {ref.field}")
    return Reference(ref.url, ref.field, ref.locale, None, True, ref.surface)


def validate_reference(ref: Reference, *, provider: str,
                       availability: dict[str, frozenset[str]] | None = None) -> str | None:
    ref = normalized_reference(ref)
    if ref.identity:
        _clean_identity(ref.url, ref.field)
        if not is_clean_app_store_developer_url(ref.url):
            validated_app_store_url(ref.url, ref.app_id)
        return None
    expected_locale = storefront_locale_for_url(ref.url, ref.locale)
    normalized = validated_app_store_url(
        ref.url, ref.app_id, expected_locale=expected_locale,
        require_campaign=True, provider_token=provider, availability=availability,
    )
    campaign = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(normalized).query))["ct"]
    from gen_store_attribution import BUCKETS, PROTECTED_CAMPAIGNS, TOKEN_PREFIX

    allowed = {TOKEN_PREFIX + bucket for bucket in BUCKETS} | PROTECTED_CAMPAIGNS
    # These are existing publisher-owned atomic collections, not new buckets.
    if ref.locale in LOCALE_STOREFRONTS:
        allowed.add("iag_visual_" + ref.locale.replace("-", "_").lower())
    if campaign not in allowed:
        raise AttributionError(f"Campaign outside the existing taxonomy: {campaign}")
    return campaign


def _qr_card(href: str, image: str, root: Path | None, cache: set | None = None) -> None:
    parsed = urllib.parse.urlsplit(image)
    name = QR_NAME_RE.fullmatch(Path(parsed.path).name)
    if name is None or parsed.query or parsed.fragment:
        raise AttributionError(f"Invalid QR asset path: {image}")
    url = validated_app_store_url(href, name["app"], require_campaign=True)
    expected = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    if name["digest"] != expected:
        raise AttributionError(f"QR image/link digest mismatch: {image}")
    if root is not None:
        marker = "assets/app-store-qr/"
        if marker not in parsed.path:
            raise AttributionError(f"QR asset is outside its managed directory: {image}")
        relative = marker + parsed.path.split(marker, 1)[1]
        asset = root / relative
        if not asset.resolve().is_relative_to(root.resolve()) or not asset.is_file():
            raise AttributionError(f"Missing QR asset: {image}")
        source = asset.read_text(encoding="utf-8")
        fingerprint = (asset.resolve(), url, hashlib.sha256(source.encode()).digest())
        if cache is not None and fingerprint in cache:
            return
        from gen_app_store_qr_ctas import qr_svg

        if source != qr_svg(name["app"], url):
            raise AttributionError(f"QR pixels do not encode the linked URL: {image}")
        if cache is not None:
            cache.add(fingerprint)


def _xml_references(source: str, locale: str | None):
    root = ET.fromstring(source)

    def walk(element, inherited_locale, app_id=None):
        field = element.tag.rsplit("}", 1)[-1].casefold()
        local = _locale(
            element.get("{http://www.w3.org/XML/1998/namespace}lang"), inherited_locale
        )
        languages = {
            child.text.strip()
            for child in element
            if child.tag.rsplit("}", 1)[-1].casefold() in {
                "language", "inlanguage", "content_language"
            } and child.text and child.text.strip()
        }
        if len(languages) == 1:
            local = _locale(next(iter(languages)), local)
        if field in {"entry", "item"}:
            for child in element:
                if child.tag.rsplit("}", 1)[-1].casefold() in {"id", "guid"}:
                    if child.text and is_store_url(child.text):
                        canonical = validated_app_store_url(child.text)
                        app_id = APP_STORE_PATH_RE.fullmatch(
                            urllib.parse.urlsplit(canonical).path
                        )["app_id"]
        identity = identity_field(field) or field == "loc"
        if element.text and is_store_url(element.text):
            if "<a" in element.text.casefold():
                for ref in html_references(element.text, locale=local):
                    yield Reference(ref.url, ref.field, ref.locale, app_id, ref.identity, ref.surface)
            else:
                yield from _text_references(element.text, field, local, app_id, identity)
        for key, value in element.attrib.items():
            if is_store_url(value):
                yield Reference(value, key, local, app_id, identity)
        for child in element:
            yield from walk(child, local, app_id)

    yield from walk(root, locale)


def audit_source(source: str, relative: str, *, provider: str,
                 availability: dict[str, frozenset[str]] | None = None,
                 root: Path | None = None, qr_cache: set | None = None) -> list[Reference]:
    suffix = Path(relative).suffix.lower()
    locale = locale_of(relative)
    surface = "download"
    if suffix in {".html", ".htm", ".xhtml"}:
        parser = _HTMLReferences(locale)
        parser.feed(source)
        parser.close()
        if parser.script_type is not None or parser.qr_href is not None:
            raise AttributionError("Unclosed script or QR card")
        refs = parser.references
        if refs and all(ref.identity for ref in refs):
            raise AttributionError("App page has no actionable App Store CTA")
        for href, image in parser.qr_cards:
            _qr_card(href, image, root, qr_cache)
        surface = "html"
    elif suffix in {".json", ".jsonld", ".webmanifest"} or relative in JSON_ENDPOINTS:
        payload = json.loads(source)
        if relative.startswith("api/v1/ios-app-catalog/") and locale and isinstance(payload, dict):
            declared = payload.get("locale", payload.get("language"))
            if isinstance(declared, str) and _locale(declared, locale) != locale:
                raise AttributionError("App Store API locale does not match its output path")
        refs = list(json_references(payload, locale=locale))
        if isinstance(payload, dict) and str(payload.get("version", "")).startswith("https://jsonfeed.org/"):
            surface = "feed"
        elif "api" in Path(relative).parts or relative in JSON_ENDPOINTS:
            surface = "api"
    elif suffix == ".jsonl":
        refs = [ref for line in source.splitlines() if line.strip()
                for ref in json_references(json.loads(line), locale=locale)]
        surface = "feed"
    elif suffix == ".csv":
        refs = [ref for row in csv.DictReader(io.StringIO(source))
                for ref in json_references(row, locale=locale)]
        surface = "feed" if "feed" in relative else "download"
    elif suffix in {".xml", ".svg", ".rss", ".atom", ".opf"}:
        refs = list(_xml_references(source, locale))
        if suffix == ".svg" and QR_NAME_RE.fullmatch(Path(relative).name):
            surface = "qr"
            if len(refs) != 1:
                raise AttributionError("QR SVG must declare exactly one destination")
            _qr_card(refs[0].url, relative, root, qr_cache)
        elif ET.fromstring(source).tag.rsplit("}", 1)[-1] in {"feed", "rss"}:
            surface = "feed"
    elif suffix in {".js", ".mjs"}:
        refs = list(js_references(source, locale))
        surface = "tool"
    else:
        if suffix in {".ics", ".vcf"}:
            source = re.sub(r"\r?\n[ \t]", "", source)
        refs = list(_text_references(html.unescape(source), relative, locale, None))
    result = []
    for ref in refs:
        ref = normalized_reference(ref)
        validate_reference(ref, provider=provider, availability=availability)
        result.append(Reference(
            ref.url, ref.field, ref.locale, ref.app_id, ref.identity, ref.surface or surface
        ))
    return result


def _download_references(path: Path, relative: str, provider: str, availability, root):
    if path.suffix.lower() in {".epub", ".zip"}:
        with zipfile.ZipFile(path) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 256_000_000:
                raise AttributionError(f"Oversized download archive: {relative}")
            for entry in archive.infolist():
                if entry.file_size > 20_000_000:
                    raise AttributionError(f"Oversized archive member: {entry.filename}")
                if Path(entry.filename).suffix.lower() in TEXT_SUFFIXES:
                    yield from audit_source(
                        archive.read(entry).decode("utf-8"), f"{relative}/{entry.filename}",
                        provider=provider, availability=availability,
                    )
                elif Path(entry.filename).suffix.lower() == ".pdf":
                    yield from _pdf_references(
                        io.BytesIO(archive.read(entry)), f"{relative}/{entry.filename}",
                        provider, availability,
                    )
        return
    yield from _pdf_references(path, relative, provider, availability)


def _pdf_references(source, relative: str, provider: str, availability):
    from pypdf import PdfReader

    reader = PdfReader(source, strict=True)
    if reader.is_encrypted:
        raise AttributionError(f"Cannot verify encrypted download: {relative}")
    for page in reader.pages:
        for annotation in page.get("/Annots", []):
            action = annotation.get_object().get("/A", {})
            if hasattr(action, "get_object"):
                action = action.get_object()
            url = action.get("/URI")
            if isinstance(url, str) and is_store_url(url):
                ref = normalized_reference(Reference(
                    url, "PDF URI", locale_of(relative), surface="download"
                ))
                validate_reference(ref, provider=provider, availability=availability)
                yield ref


def _audit_file(path: Path, pages: Path, provider: str, availability,
                expected_app_ids: set[str], qr_cache: set):
    relative = path.relative_to(pages).as_posix()
    counts, campaigns, coverage, app_ids = Counter(), Counter(), set(), set()
    error = None
    try:
        if not path.resolve().is_relative_to(pages.resolve()):
            raise AttributionError("Public file escapes the isolated output tree")
        if path.suffix.lower() in {".pdf", ".epub", ".zip"}:
            refs = _download_references(path, relative, provider, availability, pages)
        else:
            refs = audit_source(
                path.read_text(encoding="utf-8"), relative, provider=provider,
                availability=availability, root=pages, qr_cache=qr_cache,
            )
        for ref in refs:
            if ref.identity:
                continue
            parsed = urllib.parse.urlsplit(ref.url)
            app_id = APP_STORE_PATH_RE.fullmatch(parsed.path)["app_id"]
            if app_id not in expected_app_ids:
                raise AttributionError(f"App Store CTA is outside the verified live inventory: {app_id}")
            counts[ref.surface or "download"] += 1
            app_ids.add(app_id)
            if ref.locale in LOCALE_STOREFRONTS:
                coverage.add((app_id, ref.locale))
            campaigns[dict(urllib.parse.parse_qsl(parsed.query))["ct"]] += 1
    except (ValueError, OSError, ET.ParseError, zipfile.BadZipFile, ImportError) as exception:
        error = f"{relative}: {exception}"
    return relative, counts, campaigns, coverage, app_ids, error


def _init_worker(pages, provider, availability, expected_app_ids):
    global _WORKER_CONTEXT
    _WORKER_CONTEXT = (pages, provider, availability, expected_app_ids, set())


def _audit_worker(path):
    return _audit_file(path, *_WORKER_CONTEXT)


def _audit_results(paths, pages, provider, availability, expected_app_ids, workers):
    if workers == 1:
        cache = set()
        for path in paths:
            yield _audit_file(path, pages, provider, availability, expected_app_ids, cache)
    else:
        with ProcessPoolExecutor(
            max_workers=workers, initializer=_init_worker,
            initargs=(pages, provider, availability, expected_app_ids),
        ) as pool:
            yield from pool.map(_audit_worker, paths, chunksize=64)


def audit_tree(pages: Path, *, provider: str | None = None,
               expected_app_ids: set[str] | None = None,
               required_surfaces: frozenset[str] = REQUIRED_SURFACES,
               progress: Callable[[int, int], None] | None = None,
               workers: int = 1) -> dict:
    if not isinstance(workers, int) or workers < 1:
        raise AttributionError("Attribution worker count must be positive")
    provider = resolve_provider_token() if provider is None else provider
    if not isinstance(provider, str) or PROVIDER_TOKEN_RE.fullmatch(provider) is None:
        raise AttributionError("A valid APP_STORE_PROVIDER_TOKEN is required")
    if not pages.is_dir():
        raise AttributionError(f"Missing generated public tree: {pages}")
    availability = load_storefront_availability(pages)
    if not (pages / STATE_FILE).is_file() or not availability:
        raise AttributionError("Missing verified App Store storefront snapshot")
    if expected_app_ids is None:
        from appstore_live import _read_state, STATE_FILE as LIVE_STATE_FILE

        expected_app_ids = _read_state(str(pages / LIVE_STATE_FILE), strict=True)["live_ids"]
    if not expected_app_ids:
        raise AttributionError("Missing verified live App Store inventory")
    counts: Counter = Counter()
    campaigns: Counter = Counter()
    coverage = set()
    catalog_coverage = {}
    errors = []
    files = 0
    paths = []
    for path in sorted(pages.rglob("*")):
        relative = path.relative_to(pages).as_posix()
        if any(
            part in EXCLUDED_PARTS or part.startswith(".") and part != ".well-known"
            for part in Path(relative).parts
        ):
            continue
        if not path.is_file() or (
            path.suffix.lower() not in TEXT_SUFFIXES | {".pdf", ".epub", ".zip"}
            and relative not in JSON_ENDPOINTS
        ):
            continue
        paths.append(path)
    for relative, file_counts, file_campaigns, file_coverage, app_ids, error in _audit_results(
        paths, pages, provider, availability, expected_app_ids, workers
    ):
        files += 1
        if progress is not None and files % 5000 == 0:
            progress(files, len(errors))
        counts.update(file_counts)
        campaigns.update(file_campaigns)
        coverage.update(file_coverage)
        if error is not None:
            errors.append(error)
        elif relative.startswith("api/v1/ios-app-catalog/locales/") and relative.endswith(".json"):
            catalog_coverage[Path(relative).stem] = app_ids
    missing = {(app_id, locale) for app_id in expected_app_ids for locale in OFFICIAL_LOCALES} - coverage
    if missing:
        errors.append(f"Missing App/locale CTA coverage: {len(missing)} cells; {sorted(missing)[:5]}")
    if missing_surfaces := required_surfaces - counts.keys():
        errors.append(f"Missing attribution surfaces: {sorted(missing_surfaces)}")
    if "api" in required_surfaces:
        for locale in OFFICIAL_LOCALES:
            if catalog_coverage.get(locale) != expected_app_ids:
                errors.append(f"App Store API catalog CTA coverage mismatch: {locale}")
    summary = {
        "files": files, "apps": len(expected_app_ids), "locales": len(OFFICIAL_LOCALES),
        "app_locale_cells": len(coverage), "links_by_surface": dict(counts),
        "links_by_campaign": dict(campaigns), "verified_qr_assets": counts["qr"],
    }
    if errors:
        raise AttributionError(
            f"App Store attribution failed ({len(errors)} errors):\n" + "\n".join(errors[:20]),
            failures=errors, summary=summary,
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=Path(os.environ.get("GEO_PAGES", HERE / "pages")))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    try:
        result = audit_tree(
            args.pages_dir,
            workers=args.workers,
            progress=lambda count, failures: print(
                f"store-attribution: scanned={count} failures={failures}",
                file=sys.stderr, flush=True,
            ),
        )
    except Exception as error:
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps({
                "status": "FAIL", **getattr(error, "summary", {}),
                "errors": getattr(error, "failures", None) or [str(error)],
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"store-attribution: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps({"status": "PASS", **result}, indent=2) + "\n", encoding="utf-8"
        )
    print("store-attribution: PASS " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
