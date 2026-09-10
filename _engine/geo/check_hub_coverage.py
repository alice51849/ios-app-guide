#!/usr/bin/env python3
"""Fail-closed verification for canonical live-App topic hubs."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
from xml.etree import ElementTree

import gen_hubs


class HubContractError(ValueError):
    """The public topic-hub collection is incomplete or internally inconsistent."""


class _HubParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_attrs = {}
        self.metas = defaultdict(list)
        self.canonicals = []
        self.alternates = []
        self.anchors = []
        self.json_documents = []
        self._json = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "html":
            self.html_attrs = values
        elif tag == "meta" and values.get("name"):
            self.metas[values["name"]].append(values.get("content", ""))
        elif tag == "link":
            rel = set((values.get("rel") or "").casefold().split())
            if "canonical" in rel:
                self.canonicals.append(values.get("href", ""))
            if "alternate" in rel and values.get("hreflang"):
                self.alternates.append(
                    (values["hreflang"], values.get("href", ""))
                )
        elif tag == "a":
            self.anchors.append(values.get("href", ""))
        elif (
            tag == "script"
            and values.get("type", "").casefold() == "application/ld+json"
        ):
            self._json = []

    def handle_data(self, data):
        if self._json is not None:
            self._json.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json is not None:
            raw = "".join(self._json)
            self._json = None
            try:
                self.json_documents.append(json.loads(raw))
            except json.JSONDecodeError as error:
                raise HubContractError("Topic hub contains invalid JSON-LD") from error


def _one(values, label, relative):
    if len(values) != 1 or not values[0]:
        raise HubContractError(
            f"{relative}: expected exactly one non-empty {label}"
        )
    return values[0]


def _expected_alternates(key, locales):
    expected = {
        locale: gen_hubs.hub_url(key, locale)
        for locale in locales
    }
    expected["x-default"] = gen_hubs.hub_url(key)
    return expected


def _attributed_store_links(parser, app_id, relative):
    links = [
        href
        for href in parser.anchors
        if urllib.parse.urlsplit(href).netloc.casefold() == "apps.apple.com"
    ]
    if len(links) < 2:
        raise HubContractError(
            f"{relative}: expected at least two visible App Store links"
        )
    providers = set()
    expected_campaign = gen_hubs.gen_store_attribution.campaign_token(relative)
    for href in links:
        parsed = urllib.parse.urlsplit(html.unescape(href))
        match = re.fullmatch(r"/(?:[a-z]{2}/)?app/id([0-9]{9,12})", parsed.path)
        if match is None or match.group(1) != app_id:
            raise HubContractError(
                f"{relative}: App Store link does not belong to App {app_id}"
            )
        parameters = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        names = [key for key, _ in parameters]
        if len(names) != len(set(names)):
            raise HubContractError(
                f"{relative}: duplicate App Store attribution parameters"
            )
        values = dict(parameters)
        if (
            re.fullmatch(r"[0-9]{1,20}", values.get("pt", "")) is None
            or values.get("ct") != expected_campaign
            or values.get("mt") != "8"
            or set(values) - {"pt", "ct", "mt", "ppid"}
        ):
            raise HubContractError(
                f"{relative}: incomplete App Store attribution"
            )
        providers.add(values["pt"])
    return providers


def _collection_schema(parser, relative):
    collections = [
        document
        for document in parser.json_documents
        if isinstance(document, dict)
        and document.get("@type") == "CollectionPage"
    ]
    if len(collections) != 1:
        raise HubContractError(
            f"{relative}: expected exactly one CollectionPage JSON-LD object"
        )
    return collections[0]


def _parse_hub(path, relative):
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise HubContractError(f"Missing or unreadable topic hub: {relative}") from error
    parser = _HubParser()
    parser.feed(source)
    parser.close()
    digest = _one(
        parser.metas[gen_hubs.SOURCE_DIGEST_META],
        "hub source digest",
        relative,
    )
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise HubContractError(f"{relative}: invalid hub source digest")
    return source, parser


def _validate_hub(
    pages,
    key,
    app,
    locales,
    *,
    locale=None,
    provider_token=None,
):
    if locale is None:
        relative = f"hubs/{key}.html"
        canonical = gen_hubs.hub_url(key)
        language = "en"
        owner_locale = "x-default"
        source_owner = None
    else:
        relative = f"{locale}/hubs/{key}.html"
        canonical = gen_hubs.hub_url(key, locale)
        language = locale
        owner_locale = locale
        source_owner = f"{locale}/{key}.html"
    source, parser = _parse_hub(pages / relative, relative)
    if parser.html_attrs.get("lang") != language:
        raise HubContractError(f"{relative}: wrong html lang ownership")
    expected_dir = "rtl" if locale in gen_hubs.RTL_LOCALES else None
    if parser.html_attrs.get("dir") != expected_dir:
        raise HubContractError(f"{relative}: wrong text-direction ownership")
    if _one(parser.canonicals, "canonical URL", relative) != canonical:
        raise HubContractError(f"{relative}: wrong canonical URL")
    alternates = defaultdict(list)
    for hreflang, href in parser.alternates:
        alternates[hreflang].append(href)
    expected_alternates = _expected_alternates(key, locales)
    if (
        set(alternates) != set(expected_alternates)
        or any(
            values != [expected_alternates[hreflang]]
            for hreflang, values in alternates.items()
        )
    ):
        raise HubContractError(f"{relative}: incomplete or incorrect hreflang set")
    if _one(parser.metas["iag-hub-app"], "hub App owner", relative) != key:
        raise HubContractError(f"{relative}: wrong App ownership")
    if (
        _one(parser.metas["iag-hub-locale"], "hub locale owner", relative)
        != owner_locale
    ):
        raise HubContractError(f"{relative}: wrong locale ownership")
    source_markers = parser.metas["iag-hub-source"]
    if source_owner is None:
        if source_markers:
            raise HubContractError(f"{relative}: root hub claims a locale source")
    elif _one(source_markers, "locale source owner", relative) != source_owner:
        raise HubContractError(f"{relative}: wrong locale source ownership")
    schema = _collection_schema(parser, relative)
    if (
        schema.get("url") != canonical
        or schema.get("inLanguage") != language
        or not isinstance(schema.get("about"), dict)
    ):
        raise HubContractError(f"{relative}: wrong JSON-LD locale ownership")
    about = schema["about"]
    expected_store = gen_hubs.gen_mobile_app_identity.canonical_store_url(
        app["app_id"]
    )
    if (
        about.get("@type") != "MobileApplication"
        or about.get("@id") != expected_store
        or about.get("url") != expected_store
        or about.get("installUrl") != expected_store
        or about.get("downloadUrl") != expected_store
    ):
        raise HubContractError(f"{relative}: wrong App Store JSON-LD ownership")
    providers = _attributed_store_links(parser, app["app_id"], relative)
    if provider_token is not None and providers != {provider_token}:
        raise HubContractError(
            f"{relative}: App Store provider token mismatch"
        )
    description = _one(parser.metas["description"], "description", relative)
    return source, description, providers


def _sitemap_rows(path):
    try:
        root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ElementTree.ParseError) as error:
        raise HubContractError(f"Invalid topic-hub sitemap: {path}") from error
    rows = []
    for node in root:
        loc = node.findtext("{*}loc")
        lastmod = node.findtext("{*}lastmod")
        try:
            parsed = date.fromisoformat(lastmod or "")
        except ValueError as error:
            raise HubContractError(f"Invalid topic-hub lastmod for {loc}") from error
        rows.append((loc, parsed.isoformat()))
    return rows


def audit(pages):
    pages = Path(pages)
    apps = gen_hubs.authority_apps()
    locales = gen_hubs.official_locales()
    expected_app_files = {f"{key}.html" for key in apps}
    root = pages / "hubs"
    actual_root = {path.name for path in root.glob("*.html")}
    expected_root = expected_app_files | {"index.html"}
    if actual_root != expected_root:
        raise HubContractError(
            "Root topic hubs do not match canonical live_app_manifest: "
            f"missing={sorted(expected_root - actual_root)}, "
            f"unexpected={sorted(actual_root - expected_root)}"
        )
    extra_locale_dirs = sorted(
        path.parent.name
        for path in pages.glob("*/hubs")
        if path.parent.name not in locales and any(path.glob("*.html"))
    )
    if extra_locale_dirs:
        raise HubContractError(
            f"Unexpected localized topic-hub directories: {extra_locale_dirs}"
        )
    for locale in locales:
        actual = {
            path.name for path in (pages / locale / "hubs").glob("*.html")
        }
        if actual != expected_app_files:
            raise HubContractError(
                f"{locale} topic hubs are incomplete: "
                f"missing={sorted(expected_app_files - actual)}, "
                f"unexpected={sorted(actual - expected_app_files)}"
            )

    providers = set()
    expected_provider = gen_hubs.resolve_provider_token()
    if gen_hubs.PROVIDER_TOKEN_RE.fullmatch(expected_provider) is None:
        raise HubContractError(
            f"{gen_hubs.PROVIDER_TOKEN_ENV} must be configured for verification"
        )
    english_descriptions = {}
    for key, app in apps.items():
        _, _, found = _validate_hub(
            pages,
            key,
            app,
            locales,
            provider_token=expected_provider,
        )
        providers.update(found)
        _, description, found = _validate_hub(
            pages,
            key,
            app,
            locales,
            locale="en-US",
            provider_token=expected_provider,
        )
        english_descriptions[key] = description
        providers.update(found)
    for locale in locales:
        if locale == "en-US":
            continue
        for key, app in apps.items():
            _, description, found = _validate_hub(
                pages,
                key,
                app,
                locales,
                locale=locale,
                provider_token=expected_provider,
            )
            providers.update(found)
            if (
                locale not in gen_hubs.ENGLISH_LOCALES
                and gen_hubs._looks_like_english_fallback(
                    description, english_descriptions[key]
                )
            ):
                raise HubContractError(
                    f"{locale}/hubs/{key}.html: English fallback"
                )
    if len(providers) != 1:
        raise HubContractError(
            f"Topic hubs must use one App Store provider token: {sorted(providers)}"
        )

    _, index = _parse_hub(root / "index.html", "hubs/index.html")
    if index.html_attrs.get("lang") != "en":
        raise HubContractError("hubs/index.html: wrong html lang")
    if _one(index.canonicals, "canonical URL", "hubs/index.html") != (
        f"{gen_hubs.SITE}/hubs/"
    ):
        raise HubContractError("hubs/index.html: wrong canonical URL")
    if (
        _one(
            index.metas["iag-hub-index"],
            "canonical roster owner",
            "hubs/index.html",
        )
        != "canonical-live-app-manifest"
    ):
        raise HubContractError("hubs/index.html: wrong roster ownership")
    expected_index_links = {
        gen_hubs.hub_url(key)
        for key in apps
    }
    if set(index.anchors) != expected_index_links or len(index.anchors) != len(apps):
        raise HubContractError("hubs/index.html: incomplete canonical App links")

    expected_urls = [
        *(gen_hubs.hub_url(key) for key in apps),
        *(
            gen_hubs.hub_url(key, locale)
            for locale in locales
            for key in apps
        ),
        f"{gen_hubs.SITE}/hubs/",
    ]
    sitemap_rows = _sitemap_rows(pages / "sitemap_hubs.xml")
    sitemap_urls = [url for url, _ in sitemap_rows]
    if (
        len(sitemap_urls) != len(set(sitemap_urls))
        or sitemap_urls != expected_urls
    ):
        raise HubContractError(
            "sitemap_hubs.xml is not the exact canonical hub URL sequence"
        )
    expected_count = len(apps) * (len(locales) + 1) + 1
    if len(sitemap_urls) != expected_count:
        raise HubContractError(
            f"Topic-hub URL count mismatch: {len(sitemap_urls)} != {expected_count}"
        )
    return {
        "apps": len(apps),
        "locales": len(locales),
        "root_hubs": len(apps),
        "localized_hubs": len(apps) * len(locales),
        "index_pages": 1,
        "sitemap_urls": expected_count,
        "provider_token": next(iter(providers)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages-dir",
        type=Path,
        default=Path(gen_hubs.PAGES),
    )
    args = parser.parse_args()
    result = audit(args.pages_dir)
    print(
        "PASS topic hubs: "
        f"apps={result['apps']} locales={result['locales']} "
        f"root={result['root_hubs']} localized={result['localized_hubs']} "
        f"index={result['index_pages']} sitemap={result['sitemap_urls']}"
    )


if __name__ == "__main__":
    main()
