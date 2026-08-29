#!/usr/bin/env python3
"""Read-only social discovery metadata gate for install-decision pages."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import struct
import time
from typing import Any
import urllib.error
import urllib.request

from official_locales import OFFICIAL_LOCALES, open_graph_locale


SITE = "https://alice51849.github.io/ios-app-guide"
IMAGE_SIZE = (1200, 675)
RTL_LOCALES = frozenset({"ar-SA", "he", "ur-PK"})
ENGLISH_LOCALES = frozenset({"en-AU", "en-CA", "en-GB", "en-US"})
SCRIPT_RANGES = {
    "ar-SA": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "bn-BD": ((0x0980, 0x09FF),),
    "el": ((0x0370, 0x03FF),),
    "gu-IN": ((0x0A80, 0x0AFF),),
    "he": ((0x0590, 0x05FF),),
    "hi": ((0x0900, 0x097F),),
    "ja": ((0x3040, 0x30FF),),
    "kn-IN": ((0x0C80, 0x0CFF),),
    "ko": ((0xAC00, 0xD7AF),),
    "ml-IN": ((0x0D00, 0x0D7F),),
    "mr-IN": ((0x0900, 0x097F),),
    "or-IN": ((0x0B00, 0x0B7F),),
    "pa-IN": ((0x0A00, 0x0A7F),),
    "ru": ((0x0400, 0x04FF),),
    "ta-IN": ((0x0B80, 0x0BFF),),
    "te-IN": ((0x0C00, 0x0C7F),),
    "th": ((0x0E00, 0x0E7F),),
    "uk": ((0x0400, 0x04FF),),
    "ur-PK": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "zh-Hans": ((0x3400, 0x9FFF),),
    "zh-Hant": ((0x3400, 0x9FFF),),
}
PLACEHOLDER_RE = re.compile(
    r"\{\{|\}\}|\$\{|\[\[[^\]]+\]\]|__[A-Za-z0-9_.-]+__|"
    r"\b(?:translation|locale|copy|text)_[a-z0-9_]+\b",
    re.IGNORECASE,
)
ONE_TIME_CLAIM_RE = re.compile(
    r"\b(?:buy|pay)\s+once\b|\bone[- ]time\b|\blifetime unlock\b|"
    r"\bno subscription\b|\bsubscription[- ]free\b",
    re.IGNORECASE,
)
GUARANTEE_RE = re.compile(
    r"\b(?:guarantee(?:d)?\s+(?:a\s+)?(?:score|result)|"
    r"(?:score|result)\s+guarantee(?:d)?)\b",
    re.IGNORECASE,
)
APP_ID_RE = re.compile(r"(?<!\d)\d{9,12}(?!\d)")


class MetadataParser(HTMLParser):
    """Collect only metadata needed by the gate."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_attrs: dict[str, str] = {}
        self.meta: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.links: list[dict[str, str]] = []
        self.title_parts: list[str] = []
        self.json_ld: list[str] = []
        self.decision_records: list[str] = []
        self._title = False
        self._script_kind = ""
        self._script_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {
            key.casefold(): value
            for key, value in attrs
            if value is not None
        }
        tag = tag.casefold()
        if tag == "html":
            self.html_attrs = values
        elif tag == "meta":
            for kind in ("property", "name"):
                key = values.get(kind)
                if key is not None:
                    self.meta[(kind, key.casefold())].append(
                        values.get("content", "")
                    )
        elif tag == "link":
            self.links.append(values)
        elif tag == "title":
            self._title = True
        elif tag == "script":
            media_type = values.get("type", "").casefold()
            script_id = values.get("id", "")
            if media_type == "application/ld+json":
                self._script_kind = "jsonld"
            elif media_type == "application/json" and script_id == "decision-record":
                self._script_kind = "record"
            else:
                self._script_kind = ""
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "title":
            self._title = False
        elif tag == "script" and self._script_kind:
            text = "".join(self._script_parts)
            if self._script_kind == "jsonld":
                self.json_ld.append(text)
            else:
                self.decision_records.append(text)
            self._script_kind = ""
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._title:
            self.title_parts.append(data)
        if self._script_kind:
            self._script_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


@dataclass
class CheckCount:
    required: int = 0
    passed: int = 0
    missing: int = 0
    unknown: int = 0
    not_applicable: int = 0


class Audit:
    def __init__(self) -> None:
        self.checks: dict[str, CheckCount] = defaultdict(CheckCount)
        self.issue_counts: Counter[str] = Counter()
        self.samples: dict[str, list[dict[str, str]]] = defaultdict(list)

    def require(
        self,
        check: str,
        ok: bool,
        *,
        code: str,
        app_key: str = "",
        locale: str = "",
        detail: str = "",
    ) -> None:
        count = self.checks[check]
        count.required += 1
        if ok:
            count.passed += 1
            return
        count.missing += 1
        self.issue_counts[code] += 1
        if len(self.samples[code]) < 8:
            self.samples[code].append(
                {
                    key: value
                    for key, value in {
                        "app_key": app_key,
                        "locale": locale,
                        "detail": detail,
                    }.items()
                    if value
                }
            )

    def unknown(self, check: str, amount: int = 1) -> None:
        self.checks[check].unknown += amount

    def not_applicable(self, check: str, amount: int = 1) -> None:
        self.checks[check].not_applicable += amount

    def result(self) -> str:
        return (
            "fail"
            if any(count.missing for count in self.checks.values())
            else "pass"
        )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _single(values: list[str]) -> str | None:
    return values[0] if len(values) == 1 else None


def _meta(parser: MetadataParser, kind: str, key: str) -> list[str]:
    return parser.meta.get((kind, key.casefold()), [])


def _schema_nodes(documents: list[str]) -> tuple[list[dict[str, Any]], bool]:
    nodes: list[dict[str, Any]] = []
    valid = True
    for source in documents:
        try:
            root = json.loads(source)
        except (TypeError, ValueError, json.JSONDecodeError):
            valid = False
            continue
        roots = root if isinstance(root, list) else [root]
        for item in roots:
            if not isinstance(item, dict):
                valid = False
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                nodes.extend(node for node in graph if isinstance(node, dict))
            else:
                nodes.append(item)
    return nodes, valid


def _types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def _node(nodes: list[dict[str, Any]], schema_type: str) -> dict[str, Any] | None:
    return next((item for item in nodes if schema_type in _types(item)), None)


def _has_script(text: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(
        start <= ord(character) <= end
        for character in text
        for start, end in ranges
    )


def _jpeg_size(path: Path) -> tuple[str, int, int]:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            return "unknown", 0, 0
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                return "image/jpeg", 0, 0
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if not marker or marker in {b"\xd8", b"\xd9"}:
                continue
            length_bytes = handle.read(2)
            if len(length_bytes) != 2:
                return "image/jpeg", 0, 0
            length = struct.unpack(">H", length_bytes)[0]
            if marker[0] in {
                0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
            }:
                data = handle.read(5)
                if len(data) != 5:
                    return "image/jpeg", 0, 0
                height, width = struct.unpack(">HH", data[1:])
                return "image/jpeg", width, height
            handle.seek(max(0, length - 2), os.SEEK_CUR)


def _probe_image(url: str, timeout: float, attempts: int) -> dict[str, Any]:
    error = ""
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "Lumi-social-metadata-audit/1.0"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return {
                    "status": int(response.status),
                    "mime": response.headers.get_content_type(),
                    "length": response.headers.get("Content-Length"),
                }
        except urllib.error.HTTPError as exc:
            error = f"http_{exc.code}"
            if exc.code not in {403, 405, 429, 500, 502, 503, 504}:
                break
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            error = type(exc).__name__
        if attempt + 1 < attempts:
            time.sleep(min(2 ** attempt, 2))
    return {"status": None, "mime": None, "length": None, "error": error}


def _load_cache(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.new")
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _check_single_meta(
    audit: Audit,
    parser: MetadataParser,
    kind: str,
    key: str,
    expected: str,
    *,
    app_key: str,
    locale: str,
) -> None:
    values = _meta(parser, kind, key)
    audit.require(
        f"{kind}:{key}",
        values == [expected],
        code=f"invalid_{kind}_{key.replace(':', '_')}",
        app_key=app_key,
        locale=locale,
        detail=f"expected one exact value; found {values[:3]!r}",
    )


def audit_site(
    root: Path,
    *,
    expected_app_count: int = 46,
    expected_locales: tuple[str, ...] = OFFICIAL_LOCALES,
    online_images: bool = False,
    network_cache: Path | None = None,
    network_timeout: float = 10.0,
    network_attempts: int = 3,
    network_workers: int = 2,
) -> dict[str, Any]:
    root = root.resolve()
    audit = Audit()
    catalogue = _load_object(root / "data/verified-ios-app-finder-catalog.json")
    dataset = _load_object(root / "data/app-install-decision-routes.json")
    app_rows = catalogue.get("apps")
    records = dataset.get("records")
    if not isinstance(app_rows, list) or not isinstance(records, list):
        raise ValueError("Verified catalogue or decision dataset is malformed")
    apps = {
        str(item["key"]): item
        for item in app_rows
        if isinstance(item, dict) and item.get("key")
    }
    by_pair = {
        (str(item["app_key"]), str(item["locale"])): item
        for item in records
        if isinstance(item, dict)
        and item.get("app_key")
        and item.get("locale")
    }
    expected_pairs = {
        (app_key, locale)
        for app_key in apps
        for locale in expected_locales
    }
    audit.require(
        "manifest_app_count",
        catalogue.get("record_count") == len(apps) == expected_app_count,
        code="invalid_manifest_app_count",
        detail=f"catalogue={catalogue.get('record_count')}, parsed={len(apps)}",
    )
    audit.require(
        "manifest_locale_count",
        dataset.get("locales") == list(expected_locales)
        and dataset.get("locale_count") == len(expected_locales),
        code="invalid_manifest_locale_count",
    )
    audit.require(
        "manifest_pair_count",
        set(by_pair) == expected_pairs
        and dataset.get("record_count") == len(expected_pairs),
        code="invalid_manifest_pair_count",
        detail=(
            f"expected={len(expected_pairs)}, actual={len(by_pair)}, "
            f"missing={len(expected_pairs - set(by_pair))}, "
            f"extra={len(set(by_pair) - expected_pairs)}"
        ),
    )

    english = {
        app_key: by_pair.get((app_key, "en-US"), {})
        for app_key in apps
    }
    title_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    description_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    template_shapes: set[tuple[Any, ...]] = set()
    image_urls: dict[str, str] = {}
    parsed_pages = 0

    for app_key, locale in sorted(expected_pairs):
        record = by_pair.get((app_key, locale))
        audit.require(
            "record_presence",
            isinstance(record, dict),
            code="missing_record",
            app_key=app_key,
            locale=locale,
        )
        if not isinstance(record, dict):
            continue
        path = root / "apps" / app_key / "decision" / "l" / locale / "index.html"
        audit.require(
            "page_presence",
            path.is_file(),
            code="missing_page",
            app_key=app_key,
            locale=locale,
        )
        if not path.is_file():
            continue
        parser = MetadataParser()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            audit.require(
                "page_parse",
                False,
                code="unreadable_page",
                app_key=app_key,
                locale=locale,
                detail=type(exc).__name__,
            )
            continue
        parsed_pages += 1
        audit.require(
            "page_parse",
            True,
            code="unreadable_page",
            app_key=app_key,
            locale=locale,
        )
        expected_url = str(record["decision_page_url"])
        expected_id = str(record["app_store_id"])
        expected_name = str(record["app_name"])
        query = str(record["publisher_query"])
        context = str(record["decision_context"])
        image_url = f"{SITE}/social/img/{app_key}-share.jpg"
        image_urls[app_key] = image_url
        title_groups[(locale, " ".join(query.split()).casefold())].append(app_key)
        description_groups[
            (locale, " ".join(context.split()).casefold())
        ].append(app_key)

        audit.require(
            "html_lang",
            parser.html_attrs.get("lang") == locale,
            code="invalid_html_lang",
            app_key=app_key,
            locale=locale,
        )
        expected_dir = "rtl" if locale in RTL_LOCALES else "ltr"
        audit.require(
            "html_dir",
            parser.html_attrs.get("dir") == expected_dir,
            code="invalid_html_dir",
            app_key=app_key,
            locale=locale,
        )
        audit.require(
            "html_title",
            parser.title == f"{query} | {expected_name}",
            code="invalid_html_title",
            app_key=app_key,
            locale=locale,
        )
        canonical = [
            link.get("href", "")
            for link in parser.links
            if "canonical" in link.get("rel", "").casefold().split()
        ]
        audit.require(
            "canonical",
            canonical == [expected_url],
            code="invalid_canonical",
            app_key=app_key,
            locale=locale,
            detail=repr(canonical[:3]),
        )
        hreflang = {
            link["hreflang"]: link.get("href", "")
            for link in parser.links
            if link.get("rel", "").casefold() == "alternate"
            and "hreflang" in link
        }
        expected_hreflang = {
            other: f"{SITE}/apps/{app_key}/decision/l/{other}/index.html"
            for other in expected_locales
        }
        expected_hreflang["x-default"] = expected_hreflang["en-US"]
        audit.require(
            "hreflang_alternates",
            hreflang == expected_hreflang,
            code="invalid_hreflang_alternates",
            app_key=app_key,
            locale=locale,
        )

        for kind, key, expected in (
            ("name", "description", context),
            ("name", "apple-itunes-app", f"app-id={expected_id}"),
            ("property", "og:title", query),
            ("property", "og:url", expected_url),
            ("property", "og:image", image_url),
            ("property", "og:image:secure_url", image_url),
            ("property", "og:image:type", "image/jpeg"),
            ("property", "og:image:width", str(IMAGE_SIZE[0])),
            ("property", "og:image:height", str(IMAGE_SIZE[1])),
            ("property", "og:image:alt", query),
            ("property", "og:locale", open_graph_locale(locale)),
            ("property", "og:site_name", "iOS App Guide"),
            ("name", "twitter:card", "app"),
            ("name", "twitter:title", query),
            ("name", "twitter:image", image_url),
            ("name", "twitter:image:alt", query),
            ("name", "twitter:app:name:iphone", expected_name),
            ("name", "twitter:app:id:iphone", expected_id),
            ("name", "twitter:app:name:ipad", expected_name),
            ("name", "twitter:app:id:ipad", expected_id),
        ):
            _check_single_meta(
                audit,
                parser,
                kind,
                key,
                expected,
                app_key=app_key,
                locale=locale,
            )
        for kind, key in (
            ("property", "og:description"),
            ("name", "twitter:description"),
        ):
            values = _meta(parser, kind, key)
            audit.require(
                f"{kind}:{key}",
                len(values) == 1 and context in values[0],
                code=f"invalid_{kind}_{key.replace(':', '_')}",
                app_key=app_key,
                locale=locale,
            )

        expected_og_alternates = sorted(
            open_graph_locale(other)
            for other in expected_locales
            if other != locale
        )
        actual_og_alternates = sorted(
            _meta(parser, "property", "og:locale:alternate")
        )
        audit.require(
            "og_locale_alternates",
            actual_og_alternates == expected_og_alternates,
            code="invalid_og_locale_alternates",
            app_key=app_key,
            locale=locale,
            detail=(
                f"expected={len(expected_og_alternates)}, "
                f"actual={len(actual_og_alternates)}"
            ),
        )

        storefront = record.get("storefront_facts")
        expected_og_type = "product" if isinstance(storefront, dict) else "website"
        _check_single_meta(
            audit,
            parser,
            "property",
            "og:type",
            expected_og_type,
            app_key=app_key,
            locale=locale,
        )
        if isinstance(storefront, dict):
            for key, expected in (
                ("product:price:amount", str(storefront["price"])),
                ("product:price:currency", str(storefront["currency"])),
                ("product:availability", "instock"),
            ):
                _check_single_meta(
                    audit,
                    parser,
                    "property",
                    key,
                    expected,
                    app_key=app_key,
                    locale=locale,
                )
            _check_single_meta(
                audit,
                parser,
                "name",
                "twitter:data1",
                str(storefront["formatted_price"]),
                app_key=app_key,
                locale=locale,
            )
        else:
            audit.not_applicable("property:product:price:amount")
            audit.not_applicable("property:product:price:currency")
            audit.not_applicable("property:product:availability")
            audit.not_applicable("name:twitter:data1")

        nodes, valid_schema = _schema_nodes(parser.json_ld)
        audit.require(
            "json_ld_parse",
            valid_schema and bool(nodes),
            code="invalid_json_ld",
            app_key=app_key,
            locale=locale,
        )
        app_node = next(
            (
                node
                for node in nodes
                if str(node.get("@id", "")).endswith(f"/id{expected_id}")
            ),
            None,
        )
        audit.require(
            "json_ld_app_identity",
            app_node is not None
            and app_node.get("name") == expected_name
            and str(
                (app_node.get("identifier") or {}).get("value", "")
            ) == expected_id,
            code="invalid_json_ld_app_identity",
            app_key=app_key,
            locale=locale,
        )
        app_types = _types(app_node or {})
        audit.require(
            "json_ld_software_application",
            "SoftwareApplication" in app_types,
            code="missing_json_ld_software_application",
            app_key=app_key,
            locale=locale,
        )
        audit.require(
            "json_ld_product",
            "Product" in app_types,
            code="missing_json_ld_product",
            app_key=app_key,
            locale=locale,
        )
        webpage = _node(nodes, "WebPage")
        faq = _node(nodes, "FAQPage")
        breadcrumb = _node(nodes, "BreadcrumbList")
        audit.require(
            "json_ld_webpage",
            webpage is not None
            and webpage.get("url") == expected_url
            and webpage.get("name") == query
            and webpage.get("description") == context,
            code="invalid_json_ld_webpage",
            app_key=app_key,
            locale=locale,
        )
        main_entities = (faq or {}).get("mainEntity")
        if isinstance(main_entities, dict):
            main_entities = [main_entities]
        question = (
            main_entities[0]
            if isinstance(main_entities, list) and len(main_entities) == 1
            else {}
        )
        audit.require(
            "json_ld_faq",
            faq is not None
            and question.get("@type") == "Question"
            and question.get("name") == query
            and (question.get("acceptedAnswer") or {}).get("@type") == "Answer"
            and (question.get("acceptedAnswer") or {}).get("text") == context,
            code="invalid_json_ld_faq",
            app_key=app_key,
            locale=locale,
        )
        crumbs = (breadcrumb or {}).get("itemListElement")
        expected_crumbs = [
            (1, "iOS App Guide", f"{SITE}/"),
            (2, expected_name, str(record["canonical_guide_url"])),
            (3, query, expected_url),
        ]
        actual_crumbs = [
            (
                item.get("position"),
                item.get("name"),
                item.get("item"),
            )
            for item in crumbs
        ] if isinstance(crumbs, list) else []
        audit.require(
            "json_ld_breadcrumb",
            actual_crumbs == expected_crumbs,
            code="invalid_json_ld_breadcrumb",
            app_key=app_key,
            locale=locale,
        )
        schema_image = (webpage or {}).get("primaryImageOfPage") or {}
        audit.require(
            "json_ld_image",
            schema_image.get("contentUrl") == image_url
            and schema_image.get("url") == image_url
            and schema_image.get("width") == IMAGE_SIZE[0]
            and schema_image.get("height") == IMAGE_SIZE[1]
            and schema_image.get("encodingFormat") == "image/jpeg",
            code="invalid_json_ld_image",
            app_key=app_key,
            locale=locale,
        )
        if isinstance(storefront, dict):
            offer = (app_node or {}).get("offers") or {}
            audit.require(
                "json_ld_offer",
                offer.get("@type") == "Offer"
                and str(offer.get("price")) == str(storefront["price"])
                and offer.get("priceCurrency") == storefront["currency"]
                and offer.get("url") == record["app_store_url"],
                code="invalid_json_ld_offer",
                app_key=app_key,
                locale=locale,
            )
        else:
            audit.not_applicable("json_ld_offer")

        identity_text = "\n".join(
            [
                parser.title,
                *[value for values in parser.meta.values() for value in values],
                *parser.json_ld,
            ]
        )
        known_ids = {
            match.group(0)
            for match in APP_ID_RE.finditer(identity_text)
            if match.group(0)
            in {str(item["app_store_id"]) for item in apps.values()}
        }
        audit.require(
            "cross_app_identity",
            known_ids == {expected_id},
            code="cross_app_identity_leak",
            app_key=app_key,
            locale=locale,
            detail=repr(sorted(known_ids)),
        )
        copy_values = [
            query,
            context,
            str(record["app_store_cta_label"]),
            str(record["guide_cta_label"]),
            str(record["publisher_disclosure"]),
            *[str(value) for value in record.get("badge_labels", [])],
        ]
        audit.require(
            "raw_localization_keys",
            not any(PLACEHOLDER_RE.search(value) for value in copy_values),
            code="raw_localization_key",
            app_key=app_key,
            locale=locale,
        )
        if locale in ENGLISH_LOCALES:
            audit.not_applicable("english_fallback_title")
            audit.not_applicable("english_fallback_description")
        else:
            en_record = english[app_key]
            audit.require(
                "english_fallback_title",
                query.casefold()
                != str(en_record.get("publisher_query", "")).casefold(),
                code="english_fallback_title",
                app_key=app_key,
                locale=locale,
            )
            audit.require(
                "english_fallback_description",
                context.casefold()
                != str(en_record.get("decision_context", "")).casefold(),
                code="english_fallback_description",
                app_key=app_key,
                locale=locale,
            )
        ranges = SCRIPT_RANGES.get(locale)
        if ranges is None:
            audit.unknown("native_script_title")
            audit.unknown("native_script_description")
        else:
            audit.require(
                "native_script_title",
                _has_script(query, ranges),
                code="native_script_title_mismatch",
                app_key=app_key,
                locale=locale,
            )
            audit.require(
                "native_script_description",
                _has_script(context, ranges),
                code="native_script_description_mismatch",
                app_key=app_key,
                locale=locale,
            )
        claims = " ".join(copy_values)
        audit.require(
            "unsupported_one_time_claim",
            bool(apps[app_key].get("one_time_option"))
            or ONE_TIME_CLAIM_RE.search(claims) is None,
            code="unsupported_one_time_claim",
            app_key=app_key,
            locale=locale,
        )
        audit.require(
            "guaranteed_result_claim",
            GUARANTEE_RE.search(claims) is None,
            code="guaranteed_result_claim",
            app_key=app_key,
            locale=locale,
        )
        template_shapes.add(
            (
                tuple(sorted((kind, key, len(values)) for (kind, key), values in parser.meta.items())),
                tuple(
                    sorted(
                        tuple(sorted(_types(node)))
                        for node in nodes
                        if _types(node)
                    )
                ),
            )
        )

    for groups, check, code in (
        (title_groups, "cross_app_title_uniqueness", "duplicate_cross_app_title"),
        (
            description_groups,
            "cross_app_description_uniqueness",
            "duplicate_cross_app_description",
        ),
    ):
        duplicates = {
            key: values for key, values in groups.items() if len(set(values)) > 1
        }
        duplicate_apps = {
            (locale, app_key)
            for (locale, _), app_keys in duplicates.items()
            for app_key in app_keys
        }
        for app_key, locale in expected_pairs:
            audit.require(
                check,
                (locale, app_key) not in duplicate_apps,
                code=code,
                app_key=app_key,
                locale=locale,
            )

    image_hashes: dict[str, list[str]] = defaultdict(list)
    for app_key, image_url in sorted(image_urls.items()):
        path = root / "social" / "img" / f"{app_key}-share.jpg"
        audit.require(
            "local_image_presence",
            path.is_file() and path.stat().st_size > 0,
            code="missing_local_image",
            app_key=app_key,
        )
        if not path.is_file() or path.stat().st_size == 0:
            continue
        mime, width, height = _jpeg_size(path)
        audit.require(
            "local_image_mime",
            mime == "image/jpeg",
            code="invalid_local_image_mime",
            app_key=app_key,
            detail=mime,
        )
        audit.require(
            "local_image_dimensions",
            (width, height) == IMAGE_SIZE,
            code="invalid_local_image_dimensions",
            app_key=app_key,
            detail=f"{width}x{height}",
        )
        image_hashes[hashlib.sha256(path.read_bytes()).hexdigest()].append(app_key)
    duplicate_images = {
        key: values for key, values in image_hashes.items() if len(values) > 1
    }
    duplicate_image_apps = {
        app_key for values in duplicate_images.values() for app_key in values
    }
    for app_key in sorted(image_urls):
        audit.require(
            "cross_app_image_uniqueness",
            app_key not in duplicate_image_apps,
            code="duplicate_cross_app_image",
            app_key=app_key,
        )

    cache = _load_cache(network_cache)
    probes: dict[str, dict[str, Any]] = {}
    if online_images:
        urls = sorted(set(image_urls.values()))
        with ThreadPoolExecutor(max_workers=max(1, min(network_workers, 4))) as pool:
            results = pool.map(
                lambda url: _probe_image(url, network_timeout, network_attempts),
                urls,
            )
            probes = dict(zip(urls, results))
        cache.update(probes)
        if network_cache is not None:
            _write_private_json(network_cache, cache)
    for app_key, url in sorted(image_urls.items()):
        probe = probes.get(url) or cache.get(url)
        if not isinstance(probe, dict):
            audit.unknown("remote_image_http")
            audit.unknown("remote_image_mime")
            continue
        status = probe.get("status")
        audit.require(
            "remote_image_http",
            status == 200,
            code="remote_image_non_200",
            app_key=app_key,
            detail=str(status or probe.get("error", "unknown")),
        )
        audit.require(
            "remote_image_mime",
            probe.get("mime") == "image/jpeg",
            code="remote_image_mime_mismatch",
            app_key=app_key,
            detail=str(probe.get("mime")),
        )

    checks = {
        key: {
            "required": value.required,
            "passed": value.passed,
            "missing": value.missing,
            "unknown": value.unknown,
            "not_applicable": value.not_applicable,
        }
        for key, value in sorted(audit.checks.items())
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "apps": len(apps),
            "locales": len(expected_locales),
            "expected_pages": len(expected_pairs),
            "parsed_pages": parsed_pages,
            "unique_images": len(image_urls),
        },
        "content_evidence": {
            "template_instances": parsed_pages,
            "unique_metadata_schema_shapes": len(template_shapes),
            "unique_titles": len(title_groups),
            "unique_descriptions": len(description_groups),
            "note": (
                "Structural instances are counted exhaustively; one repeated "
                "template is not treated as independent native-copy evidence."
            ),
        },
        "checks": checks,
        "issue_counts": dict(sorted(audit.issue_counts.items())),
        "samples": dict(sorted(audit.samples.items())),
        "result": audit.result(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--online-images", action="store_true")
    parser.add_argument("--network-cache", type=Path)
    parser.add_argument("--network-timeout", type=float, default=10.0)
    parser.add_argument("--network-attempts", type=int, default=3)
    parser.add_argument("--network-workers", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.network_attempts <= 4:
        parser.error("--network-attempts must be between 1 and 4")
    if not 1 <= args.network_workers <= 4:
        parser.error("--network-workers must be between 1 and 4")
    if not 1 <= args.network_timeout <= 30:
        parser.error("--network-timeout must be between 1 and 30 seconds")
    report = audit_site(
        args.site_root,
        online_images=args.online_images,
        network_cache=args.network_cache,
        network_timeout=args.network_timeout,
        network_attempts=args.network_attempts,
        network_workers=args.network_workers,
    )
    if args.report is not None:
        _write_private_json(args.report, report)
    print(
        f"social metadata: {report['result']} "
        f"({report['scope']['parsed_pages']}/"
        f"{report['scope']['expected_pages']} pages, "
        f"{sum(report['issue_counts'].values())} issues)"
    )
    return int(report["result"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
