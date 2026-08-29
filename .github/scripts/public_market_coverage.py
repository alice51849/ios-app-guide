#!/usr/bin/env python3
"""Verify every localized public catalog feed from the deployed site."""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_SITE = "https://alice51849.github.io/ios-app-guide"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APPS_MANIFEST = REPO_ROOT / "apps.json"
GEO_ENGINE = REPO_ROOT / "_engine" / "geo"
if str(GEO_ENGINE) not in sys.path:
    sys.path.insert(0, str(GEO_ENGINE))

from official_locales import OFFICIAL_LOCALE_SET  # noqa: E402

EXPECTED_APPS = 46
EXPECTED_LOCALES = 50
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
HEX_40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
APP_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
APP_ID_RE = re.compile(r"^[0-9]{7,12}$")
APP_STORE_PATH_RE = re.compile(
    r"^/(?:[a-z]{2}/)?app/(?:[^/?#]+/)?id([0-9]{7,12})$"
)
ENGLISH_LOCALES = frozenset({"en-AU", "en-CA", "en-GB", "en-US"})
SCRIPT_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "ar-SA": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "bn-BD": ((0x0980, 0x09FF),),
    "el": ((0x0370, 0x03FF),),
    "gu-IN": ((0x0A80, 0x0AFF),),
    "he": ((0x0590, 0x05FF),),
    "hi": ((0x0900, 0x097F),),
    "ja": ((0x3040, 0x30FF), (0x3400, 0x9FFF)),
    "kn-IN": ((0x0C80, 0x0CFF),),
    "ko": ((0x1100, 0x11FF), (0xAC00, 0xD7AF)),
    "ml-IN": ((0x0D00, 0x0D7F),),
    "mr-IN": ((0x0900, 0x097F),),
    "or-IN": ((0x0B00, 0x0B7F),),
    "pa-IN": ((0x0A00, 0x0A7F),),
    "ru": ((0x0400, 0x052F),),
    "ta-IN": ((0x0B80, 0x0BFF),),
    "te-IN": ((0x0C00, 0x0C7F),),
    "th": ((0x0E00, 0x0E7F),),
    "uk": ((0x0400, 0x052F),),
    "ur-PK": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "zh-Hans": ((0x3400, 0x9FFF),),
    "zh-Hant": ((0x3400, 0x9FFF),),
}


class CoverageError(RuntimeError):
    """The deployed public market surface is incomplete or inconsistent."""


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CoverageError(f"{field} must be an object")
    return value


def _array(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise CoverageError(f"{field} must be an array")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoverageError(f"{field} must be non-empty text")
    return value.strip()


def _site_identity(site: str) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(site.rstrip("/"))
    if (
        parsed.scheme != "https"
        or parsed.hostname != "alice51849.github.io"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path != "/ios-app-guide"
    ):
        raise CoverageError("site must be the canonical HTTPS Guide origin")
    return parsed.hostname, parsed.path


def _trusted_public_url(url: str, *, site: str) -> str:
    hostname, prefix = _site_identity(site)
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != hostname
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith(prefix + "/")
    ):
        raise CoverageError(f"untrusted public URL: {url}")
    return url


def fetch_json(
    url: str,
    *,
    site: str = DEFAULT_SITE,
    attempts: int = 3,
    timeout: float = 15,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    _trusted_public_url(url, site=site)
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ios-app-guide-public-market-sla/1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                final_url = response.geturl()
                _trusted_public_url(final_url, site=site)
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise CoverageError(f"public JSON exceeds size limit: {url}")
                value = json.loads(payload)
                return _object(value, url)
        except (
            CoverageError,
            json.JSONDecodeError,
            OSError,
            UnicodeError,
            urllib.error.URLError,
        ) as error:
            last_error = error
            if attempt + 1 < attempts:
                sleep(float(2**attempt))
    raise CoverageError(f"cannot fetch public JSON {url}: {last_error}")


def _app_store_identity(url: object, *, field: str) -> tuple[str, str]:
    text = _text(url, field)
    parsed = urllib.parse.urlsplit(text)
    match = APP_STORE_PATH_RE.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "apps.apple.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or match is None
    ):
        raise CoverageError(f"{field} is not a trusted App Store URL")
    query = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
    if query.get("mt") != ["8"] or query.get("pt") != ["118326163"]:
        raise CoverageError(f"{field} lacks the reviewed campaign identity")
    if len(query.get("ct", [])) != 1:
        raise CoverageError(f"{field} lacks one campaign code")
    country = parsed.path.strip("/").split("/", 1)[0]
    return match.group(1), country


def load_reviewed_app_ids(path: Path = DEFAULT_APPS_MANIFEST) -> frozenset[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CoverageError(f"cannot load reviewed App manifest: {error}") from error
    rows = _array(document, "reviewed App manifest")
    app_ids: set[str] = set()
    for raw in rows:
        row = _object(raw, "reviewed App manifest row")
        url = _text(row.get("appStoreUrl"), "reviewed App Store URL")
        parsed = urllib.parse.urlsplit(url)
        match = APP_STORE_PATH_RE.fullmatch(parsed.path)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "apps.apple.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or match is None
        ):
            raise CoverageError("reviewed App manifest has an invalid App Store URL")
        app_id = match.group(1)
        if app_id in app_ids:
            raise CoverageError(f"reviewed App manifest repeats App ID {app_id}")
        app_ids.add(app_id)
    if not app_ids:
        raise CoverageError("reviewed App manifest is empty")
    return frozenset(app_ids)


def _has_expected_script(locale: str, text: str) -> bool:
    ranges = SCRIPT_RANGES.get(locale)
    if ranges is None:
        return True
    return any(
        start <= ord(character) <= end
        for character in text
        for start, end in ranges
    )


def _validate_index(
    document: dict[str, Any],
    *,
    site: str,
    expected_apps: int,
    expected_locales: int,
    official_locales: frozenset[str],
) -> tuple[int, str, list[dict[str, str]]]:
    observed_apps = document.get("record_count")
    if not isinstance(observed_apps, int) or observed_apps < expected_apps:
        raise CoverageError("catalog index App denominator fell below SLA floor")
    if document.get("locale_count") != expected_locales:
        raise CoverageError("catalog index locale denominator changed")
    if len(official_locales) != expected_locales:
        raise CoverageError("official locale authority contradicts SLA denominator")
    digest = _text(document.get("content_digest"), "index content_digest")
    if HEX_64_RE.fullmatch(digest) is None:
        raise CoverageError("index content_digest is not SHA-256")
    rows = _array(document.get("locales"), "index locales")
    if len(rows) != expected_locales:
        raise CoverageError("catalog index locale rows are incomplete")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in rows:
        row = _object(raw, "index locale row")
        locale = _text(row.get("locale"), "index locale")
        if locale in seen:
            raise CoverageError(f"duplicate locale in catalog index: {locale}")
        catalog_url = _trusted_public_url(
            _text(row.get("url"), f"{locale} catalog URL"),
            site=site,
        )
        feed_url = _trusted_public_url(
            _text(row.get("feed"), f"{locale} feed URL"),
            site=site,
        )
        if catalog_url != (
            f"{site}/api/v1/ios-app-catalog/locales/{locale}.json"
        ):
            raise CoverageError(f"{locale} catalog URL is not canonical")
        if feed_url != f"{site}/api/v1/ios-app-catalog/feeds/{locale}.json":
            raise CoverageError(f"{locale} feed URL is not canonical")
        seen.add(locale)
        result.append(
            {"locale": locale, "catalog_url": catalog_url, "feed_url": feed_url}
        )
    if "en-US" not in seen:
        raise CoverageError("catalog index lacks en-US baseline")
    if seen != official_locales:
        missing = sorted(official_locales - seen)
        unexpected = sorted(seen - official_locales)
        raise CoverageError(
            "catalog index does not match official Apple locales: "
            f"missing={missing}, unexpected={unexpected}"
        )
    return observed_apps, digest, result


def _validate_catalog(
    document: dict[str, Any],
    *,
    locale: str,
    digest: str,
    site: str,
    expected_apps: int,
) -> dict[str, dict[str, str]]:
    if document.get("locale") != locale:
        raise CoverageError(f"{locale} catalog language identity changed")
    if document.get("record_count") != expected_apps:
        raise CoverageError(f"{locale} catalog App denominator changed")
    if document.get("content_digest") != digest:
        raise CoverageError(f"{locale} catalog digest drifted from index")
    apps = _array(document.get("apps"), f"{locale} catalog apps")
    if len(apps) != expected_apps:
        raise CoverageError(f"{locale} catalog App rows are incomplete")
    records: dict[str, dict[str, str]] = {}
    app_ids: set[str] = set()
    for raw in apps:
        app = _object(raw, f"{locale} catalog App")
        key = _text(app.get("key"), f"{locale} App key")
        app_id = _text(app.get("app_store_id"), f"{locale}/{key} App ID")
        if APP_KEY_RE.fullmatch(key) is None or APP_ID_RE.fullmatch(app_id) is None:
            raise CoverageError(f"{locale}/{key} has an invalid identity")
        if key in records or app_id in app_ids:
            raise CoverageError(f"{locale} catalog repeats an App identity")
        if app.get("verified_live") is not True:
            raise CoverageError(f"{locale}/{key} is not verified live")
        name = _text(app.get("name"), f"{locale}/{key} name")
        summary = _text(app.get("summary"), f"{locale}/{key} summary")
        guide_url = _trusted_public_url(
            _text(app.get("guide_url"), f"{locale}/{key} guide URL"),
            site=site,
        )
        if guide_url != f"{site}/{locale}/{key}.html":
            raise CoverageError(f"{locale}/{key} guide URL is not canonical")
        observed_id, country = _app_store_identity(
            app.get("app_store_url"),
            field=f"{locale}/{key} App Store URL",
        )
        if observed_id != app_id:
            raise CoverageError(f"{locale}/{key} App Store identity mismatch")
        if not _has_expected_script(locale, f"{name} {summary}"):
            raise CoverageError(f"{locale}/{key} lacks native-script copy")
        records[key] = {
            "app_id": app_id,
            "name": name,
            "summary": summary,
            "guide_url": guide_url,
            "country": country,
        }
        app_ids.add(app_id)
    return records


def _validate_feed(
    document: dict[str, Any],
    *,
    locale: str,
    digest: str,
    catalog: dict[str, dict[str, str]],
    expected_apps: int,
) -> dict[str, str]:
    if document.get("language") != locale:
        raise CoverageError(f"{locale} feed language identity changed")
    metadata = _object(document.get("_lumi_catalog"), f"{locale} feed metadata")
    if metadata.get("recordCount") != expected_apps:
        raise CoverageError(f"{locale} feed App denominator changed")
    if metadata.get("contentDigest") != digest:
        raise CoverageError(f"{locale} feed digest drifted from index")
    items = _array(document.get("items"), f"{locale} feed items")
    if len(items) != expected_apps:
        raise CoverageError(f"{locale} feed items are incomplete")
    by_id = {record["app_id"]: key for key, record in catalog.items()}
    result: dict[str, str] = {}
    for raw in items:
        item = _object(raw, f"{locale} feed item")
        if item.get("language") != locale:
            raise CoverageError(f"{locale} feed item has wrong language")
        app_id, country = _app_store_identity(
            item.get("external_url"),
            field=f"{locale} feed App Store URL",
        )
        key = by_id.get(app_id)
        if key is None or key in result:
            raise CoverageError(f"{locale} feed App identity is missing or repeated")
        record = catalog[key]
        if country != record["country"]:
            raise CoverageError(f"{locale}/{key} storefront country mismatch")
        if item.get("url") != record["guide_url"]:
            raise CoverageError(f"{locale}/{key} feed guide URL mismatch")
        content = _text(item.get("content_text"), f"{locale}/{key} feed copy")
        if content != record["summary"]:
            raise CoverageError(f"{locale}/{key} feed and catalog copy differ")
        if not _has_expected_script(locale, content):
            raise CoverageError(f"{locale}/{key} feed copy lacks native script")
        result[key] = content
    if set(result) != set(catalog):
        raise CoverageError(f"{locale} feed and catalog App sets differ")
    return result


def audit_public_market_coverage(
    *,
    site: str = DEFAULT_SITE,
    expected_apps: int = EXPECTED_APPS,
    expected_locales: int = EXPECTED_LOCALES,
    reviewed_app_ids: frozenset[str] | None = None,
    official_locales: frozenset[str] = OFFICIAL_LOCALE_SET,
    fetcher: Callable[[str], dict[str, Any]] | None = None,
    workers: int = 10,
) -> dict[str, Any]:
    site = site.rstrip("/")
    _site_identity(site)
    fetch = fetcher or (lambda url: fetch_json(url, site=site))
    deployment = fetch(f"{site}/.well-known/deployment.json")
    reviewed_ids = reviewed_app_ids or load_reviewed_app_ids()
    if len(reviewed_ids) < expected_apps:
        raise CoverageError("reviewed App manifest fell below SLA floor")
    source_commit = _text(
        deployment.get("source_commit"),
        "deployment source_commit",
    )
    if deployment.get("version") != 1 or HEX_40_RE.fullmatch(source_commit) is None:
        raise CoverageError("deployment manifest is invalid")
    index = fetch(f"{site}/api/v1/ios-app-catalog/index.json")
    observed_apps, digest, locale_rows = _validate_index(
        index,
        site=site,
        expected_apps=expected_apps,
        expected_locales=expected_locales,
        official_locales=official_locales,
    )
    if observed_apps != len(reviewed_ids):
        raise CoverageError(
            "deployed App denominator differs from reviewed App manifest"
        )

    def load_pair(row: dict[str, str]) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return (
            row["locale"],
            fetch(row["catalog_url"]),
            fetch(row["feed_url"]),
        )

    loaded: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, min(workers, expected_locales))
    ) as executor:
        for locale, catalog, feed in executor.map(load_pair, locale_rows):
            loaded[locale] = (catalog, feed)

    baseline_keys: set[str] | None = None
    baseline_ids: dict[str, str] | None = None
    english_copy: dict[str, str] | None = None
    native_cells = 0
    for row in locale_rows:
        locale = row["locale"]
        catalog_document, feed_document = loaded[locale]
        catalog = _validate_catalog(
            catalog_document,
            locale=locale,
            digest=digest,
            site=site,
            expected_apps=observed_apps,
        )
        feed = _validate_feed(
            feed_document,
            locale=locale,
            digest=digest,
            catalog=catalog,
            expected_apps=observed_apps,
        )
        keys = set(catalog)
        ids = {key: value["app_id"] for key, value in catalog.items()}
        if baseline_keys is None:
            baseline_keys = keys
            baseline_ids = ids
        elif keys != baseline_keys or ids != baseline_ids:
            raise CoverageError(f"{locale} changed the reviewed App denominator")
        if locale == "en-US":
            english_copy = feed
        native_cells += len(feed)

    if english_copy is None:
        raise CoverageError("en-US native-copy baseline is missing")
    if baseline_ids is None or set(baseline_ids.values()) != reviewed_ids:
        raise CoverageError(
            "deployed App identities differ from reviewed App manifest"
        )
    for locale, (_catalog_document, feed_document) in loaded.items():
        if locale in ENGLISH_LOCALES:
            continue
        catalog = _validate_catalog(
            loaded[locale][0],
            locale=locale,
            digest=digest,
            site=site,
            expected_apps=observed_apps,
        )
        localized = _validate_feed(
            feed_document,
            locale=locale,
            digest=digest,
            catalog=catalog,
            expected_apps=observed_apps,
        )
        for key, content in localized.items():
            if content.casefold() == english_copy[key].casefold():
                raise CoverageError(f"{locale}/{key} reuses the en-US feed copy")

    expected_cells = observed_apps * expected_locales
    if native_cells != expected_cells:
        raise CoverageError(
            f"public market coverage is {native_cells}, expected {expected_cells}"
        )
    return {
        "schema_version": 1,
        "status": "READY",
        "observed_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "site": site,
        "deployment_source_commit": source_commit,
        "content_digest": digest,
        "apps": observed_apps,
        "minimum_apps": expected_apps,
        "locales": expected_locales,
        "native_public_cells": native_cells,
        "verified_public_endpoints": 2 + expected_locales * 2,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_summary(path: Path, report: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            "## Public market coverage\n\n"
            f"- Status: **{report['status']}**\n"
            f"- Apps: **{report['apps']}**\n"
            f"- Apple locales: **{report['locales']}**\n"
            f"- Native public cells: **{report['native_public_cells']}**\n"
            f"- Deployment: `{report['deployment_source_commit']}`\n"
            f"- Observed: `{report['observed_at']}`\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=DEFAULT_SITE)
    parser.add_argument("--expected-apps", type=int, default=EXPECTED_APPS)
    parser.add_argument("--expected-locales", type=int, default=EXPECTED_LOCALES)
    parser.add_argument("--apps-manifest", type=Path, default=DEFAULT_APPS_MANIFEST)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    report = audit_public_market_coverage(
        site=args.site,
        expected_apps=args.expected_apps,
        expected_locales=args.expected_locales,
        reviewed_app_ids=load_reviewed_app_ids(args.apps_manifest),
        workers=args.workers,
    )
    if args.report is not None:
        write_report(args.report, report)
    if args.summary is not None:
        append_summary(args.summary, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
