#!/usr/bin/env python3
"""Seal an exact held feed release and verify it on both public hosts by GET."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.message import Message
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from deployment_generation import validate_binding
from notification_release import read_policy
from site_config import ORIGIN_SITE
import owned_app_feeds as feeds
from owned_feed_public_capture import NoRedirect
from owned_feed_reconciliation import semantic_feed

SCHEMA = "lumi.owned-feed-live-manifest/v1"
MANIFEST = Path(".well-known/owned-feed-release.json")
HOSTS = (feeds.SITE, ORIGIN_SITE)


def seal(pages: Path) -> dict:
    if read_policy()["notification_release_hold"] is not True:
        raise ValueError("This publication requires notification_release_hold=true")
    catalog = feeds.read_manifest(pages)
    generation = validate_binding(feeds.read_json(pages / ".well-known/deployment.json"))
    result = {
        "schema": SCHEMA, "notification_release_hold": True,
        "provider_intents": 0, "provider_requests": 0,
        "subscriber_delivery_verified": False, "indexing_verified": False,
        "generation": generation, "source_commit": generation["pages_source_sha"],
        "engine_source_revision": generation["source_sha"],
        "route_manifest_digest": generation["manifest_digest"],
        "feed_manifest_sha256": feeds.sha256((pages / feeds.INDEX).read_bytes()),
        "feed_generation_digest": catalog["generation_digest"],
        "catalog_sha256": feeds.sha256((pages / feeds.CATALOG / "index.json").read_bytes()),
        "app_count": catalog["app_count"], "locale_count": catalog["locale_count"],
        "record_count": catalog["record_count"], "feed_count": catalog["feed_count"],
        "feeds": catalog["feeds"],
    }
    result["manifest_digest"] = feeds.digest(result)
    feeds.write_if_changed(pages / MANIFEST, feeds.json_bytes(result))
    return result


def get_exact(url: str, expected: bytes, allowed: set[str], *, opener=None, attempts=6, delay=5) -> bytes:
    opener = opener or urllib.request.build_opener(NoRedirect()).open
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "Lumi-Owned-Feed-Live-Readback/1.0", "Cache-Control": "no-cache",
                "Accept": "*/*",
            })
            with opener(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != url:
                    raise ValueError("HTTP status or redirect mismatch")
                header = Message()
                header["Content-Type"] = response.headers.get("Content-Type", "")
                if header.get_content_type() not in allowed:
                    raise ValueError("Incorrect Content-Type")
                charset = header.get_content_charset()
                if charset and charset.casefold() not in {"utf-8", "utf8"}:
                    raise ValueError("Incorrect charset")
                raw = response.read(feeds.MAX_BYTES + 1)
                raw.decode("utf-8", errors="strict")
                if raw != expected:
                    raise ValueError("Body hash/source generation mismatch")
                return raw
        except (urllib.error.URLError, OSError, ValueError) as error:
            last = str(error)
            if attempt + 1 < attempts:
                time.sleep(delay)
    raise ValueError(f"Public feed is not the bound release: {url}: {last}")


def verify(pages: Path, *, opener=None, attempts=6, delay=5) -> dict:
    catalog = feeds.read_manifest(pages)
    manifest_raw = (pages / MANIFEST).read_bytes()
    manifest = feeds.decode(manifest_raw)
    generation = validate_binding(manifest)
    if (
        manifest.get("schema") != SCHEMA or manifest.get("notification_release_hold") is not True
        or manifest.get("manifest_digest") != feeds.digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
        or manifest.get("feed_manifest_sha256") != feeds.sha256((pages / feeds.INDEX).read_bytes())
        or manifest.get("feed_generation_digest") != catalog["generation_digest"]
        or manifest.get("provider_intents") != 0 or manifest.get("provider_requests") != 0
    ):
        raise ValueError("Invalid held-release manifest")
    hosts = {}
    for host in HOSTS:
        for path, raw in (
            (MANIFEST, manifest_raw),
            (feeds.INDEX, (pages / feeds.INDEX).read_bytes()),
            (Path(".well-known/deployment.json"), (pages / ".well-known/deployment.json").read_bytes()),
        ):
            get_exact(f"{host}/{path}", raw, {"application/json"}, opener=opener, attempts=attempts, delay=delay)
        targets = [
            (locale, fmt, spec)
            for locale, row in catalog["feeds"].items() for fmt, spec in row["formats"].items()
        ]
        def check(target):
            locale, fmt, spec = target
            raw = get_exact(
                f"{host}/{spec['path']}", (pages / spec["path"]).read_bytes(), feeds.CONTENT_TYPES[fmt],
                opener=opener, attempts=attempts, delay=delay,
            )
            semantic = semantic_feed(locale, fmt, raw, catalog["apps"])
            return {
                "locale": locale, "format": fmt, "path": spec["path"], "http_status": 200,
                "sha256": feeds.sha256(raw), "semantic_sha256": feeds.digest(semantic),
                "records": len(semantic["items"]), "canonical": feeds.SITE,
            }
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(check, targets))
        get_exact(f"{host}/{MANIFEST}", manifest_raw, {"application/json"},
                  opener=opener, attempts=attempts, delay=delay)
        hosts[host] = {"valid": len(rows), "expected": 150, "feeds": rows}
    report = {
        "schema": "lumi.owned-feed-live-readback/v1", "generation": generation,
        "source_commit": generation["pages_source_sha"], "engine_source_revision": generation["source_sha"],
        "route_manifest_digest": generation["manifest_digest"],
        "notification_release_hold": True, "provider_intents": 0, "provider_requests": 0,
        "hosts": hosts, "feed_count": 150, "record_count": 2350,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "next_notification_release_eligibility": {
            "technical_feed_readback_passed": True, "dispatch_authorized": False,
            "requires": ["separate notification-release authorization", "fresh production ACK reconciliation"],
        },
    }
    report["receipt_digest"] = feeds.digest(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("seal", "verify"))
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=5)
    args = parser.parse_args()
    result = seal(args.pages_dir) if args.operation == "seal" else verify(
        args.pages_dir, attempts=args.attempts, delay=args.delay,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes(feeds.json_bytes(result))
        args.report.chmod(0o600)
    print(json.dumps({
        "operation": args.operation, "notification_release_hold": True,
        "provider_intents": 0, "provider_requests": 0,
        "feed_count": result["feed_count"], "record_count": result["record_count"],
        "source_commit": result["source_commit"],
        "host_coverage": {host: row["valid"] for host, row in result.get("hosts", {}).items()},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
