#!/usr/bin/env python3
"""Refresh the public Apple evidence used by institutional procurement pages."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
PAGES = HERE.parents[1]
CATALOG = Path("data") / "verified-ios-app-finder-catalog.json"
OUTPUT = Path("_engine") / "geo" / "institutional_public_lookup.json"
LOOKUP_ENDPOINT = "https://itunes.apple.com/lookup"
APP_STORE_PAGE = "https://apps.apple.com/us/app/id{app_id}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 InstitutionalProcurementEvidence/1.0"
)


class PrivacyLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._anchor: dict[str, Any] | None = None
        self.links: list[tuple[str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "a":
            self._anchor = {
                "href": dict(attrs).get("href") or "",
                "text": [],
            }

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._anchor is None:
            return
        text = " ".join("".join(self._anchor["text"]).split())
        href = str(self._anchor["href"])
        self.links.append((text, href))
        self._anchor = None


def _get(url: str, attempts: int = 3) -> bytes:
    error: Exception | None = None
    for attempt in range(attempts):
        request = Request(
            url,
            headers={
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "User-Agent": USER_AGENT,
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=45) as response:
                return response.read()
        except Exception as caught:  # pragma: no cover - exercised live
            error = caught
            if attempt + 1 < attempts:
                time.sleep(1.0 + attempt)
    raise RuntimeError(f"GET failed after {attempts} attempts: {url}") from error


def _https_url(value: str, label: str, app_id: str) -> str:
    value = unescape(value).replace("\\/", "/").strip()
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError(f"Invalid {label} URL for {app_id}: {value!r}")
    return value


def _support_url(source: str, app_id: str) -> str:
    match = re.search(
        r'"text":"Support".{0,1600}?"url":"([^"]+)"',
        source,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError(f"Public App Store page lacks Support URL: {app_id}")
    encoded = match.group(1)
    try:
        decoded = json.loads(f'"{encoded}"')
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid Support URL encoding: {app_id}") from error
    return _https_url(decoded, "Support", app_id)


def _privacy_url(source: str, app_id: str) -> str:
    parser = PrivacyLinkParser()
    parser.feed(source)
    candidates = []
    for text, href in parser.links:
        normalized = text.casefold().replace("’", "'")
        if "privacy policy" not in normalized:
            continue
        parts = urlsplit(href)
        if parts.netloc.casefold() in {
            "apple.com",
            "www.apple.com",
            "apps.apple.com",
        }:
            continue
        candidates.append(_https_url(href, "Privacy", app_id))
    if not candidates:
        raise ValueError(f"Public App Store page lacks Privacy URL: {app_id}")
    return candidates[0]


def _catalog_apps(pages: Path) -> list[dict[str, Any]]:
    payload = json.loads((pages / CATALOG).read_text(encoding="utf-8"))
    apps = payload.get("apps")
    if not isinstance(apps, list) or len(apps) != 46:
        raise ValueError("Verified public catalog must contain exactly 46 apps")
    app_ids = [str(app.get("app_store_id", "")) for app in apps]
    if len(app_ids) != len(set(app_ids)) or any(
        re.fullmatch(r"\d{9,12}", app_id) is None for app_id in app_ids
    ):
        raise ValueError("Verified public catalog has invalid or duplicate IDs")
    return apps


def _lookup_records(app_ids: list[str]) -> dict[str, dict[str, Any]]:
    query = urlencode(
        {
            "id": ",".join(app_ids),
            "country": "us",
            "entity": "software",
            "limit": "200",
        },
        safe=",",
    )
    payload = json.loads(_get(f"{LOOKUP_ENDPOINT}?{query}"))
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Apple lookup response has no results array")
    records = {
        str(item["trackId"]): item
        for item in results
        if isinstance(item, dict) and item.get("trackId")
    }
    if set(records) != set(app_ids):
        raise ValueError(
            "Apple lookup coverage differs from verified roster: "
            f"missing={sorted(set(app_ids) - set(records))}, "
            f"extra={sorted(set(records) - set(app_ids))}"
        )
    return records


def refresh(pages: Path, checked_at: str) -> dict[str, Any]:
    try:
        normalized_checked_at = datetime.fromisoformat(
            checked_at.replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ValueError(f"Invalid --checked-at value: {checked_at}") from error
    if (
        not checked_at.endswith("Z")
        or normalized_checked_at.tzinfo is None
        or normalized_checked_at.utcoffset() != timedelta(0)
    ):
        raise ValueError("--checked-at must be a UTC ISO-8601 timestamp ending Z")

    catalog_apps = _catalog_apps(pages)
    app_ids = [str(app["app_store_id"]) for app in catalog_apps]
    lookup = _lookup_records(app_ids)
    records = []
    for app in catalog_apps:
        app_id = str(app["app_store_id"])
        item = lookup[app_id]
        page_url = APP_STORE_PAGE.format(app_id=app_id)
        page_source = _get(page_url).decode("utf-8")
        supported_devices = [
            str(value) for value in item.get("supportedDevices", [])
        ]
        features = [str(value) for value in item.get("features", [])]
        ipad_supported = (
            "iosUniversal" in features
            or any(value.startswith("iPad") for value in supported_devices)
        )
        iphone_supported = any(
            value.startswith("iPhone") for value in supported_devices
        )
        if not iphone_supported:
            raise ValueError(f"Verified iOS app lacks iPhone evidence: {app_id}")
        bundle_id = str(item.get("bundleId", "")).strip()
        if (
            not bundle_id
            or "." not in bundle_id
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]+", bundle_id) is None
        ):
            raise ValueError(f"Apple lookup lacks a valid bundle ID: {app_id}")
        download_class = (
            "free_download"
            if float(item.get("price", -1)) == 0
            else "paid_download"
        )
        records.append(
            {
                "app_store_id": app_id,
                "bundle_id": bundle_id,
                "public_name": str(item["trackName"]).strip(),
                "canonical_app_store_url": f"https://apps.apple.com/app/id{app_id}",
                "lookup_url": (
                    f"{LOOKUP_ENDPOINT}?id={app_id}&country=us&entity=software"
                ),
                "app_store_page_url": page_url,
                "support_url": _support_url(page_source, app_id),
                "privacy_url": _privacy_url(page_source, app_id),
                "platforms": (
                    ["iPhone", "iPad"] if ipad_supported else ["iPhone"]
                ),
                "ipad_supported": ipad_supported,
                "download_class": download_class,
            }
        )
        time.sleep(0.1)

    payload = {
        "schema_version": 1,
        "checked_at": checked_at,
        "sources": {
            "identity_platform_download": (
                "Apple iTunes Lookup API, US storefront, public GET"
            ),
            "support_privacy": (
                "Public US App Store product pages, public GET"
            ),
            "scope_note": (
                "Public lookup verifies listing identity and observed storefront "
                "facts only; it does not verify Apple School Manager, Apple "
                "Business Manager, Intune, institutional approval, certification, "
                "discounts, or managed-app availability."
            ),
        },
        "record_count": len(records),
        "records": records,
    }
    output = pages / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--checked-at", required=True)
    args = parser.parse_args()
    payload = refresh(args.pages.resolve(), args.checked_at)
    print(
        "INSTITUTIONAL_PUBLIC_LOOKUP "
        f"apps={payload['record_count']} checked_at={payload['checked_at']}"
    )


if __name__ == "__main__":
    main()
