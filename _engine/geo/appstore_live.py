#!/usr/bin/env python3
"""Track which registry apps are publicly available on the App Store."""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

if __package__:
    from . import live_app_manifest as manifest
    from .current_source import validate_consumer
else:
    import live_app_manifest as manifest
    from current_source import validate_consumer

LOOKUP_URL = "https://itunes.apple.com/lookup"
LOOKUP_COUNTRIES = ("us", "tw", "jp", "gb")
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
RETIRE_AFTER_MISSES = 3
STATE_FILE = ".appstore_live_state.json"
STATE_SCHEMA = "lumi.live-state/v2"
STATE_SOURCE = "Apple iTunes Lookup API (US, TW, JP, GB)"
UA = "Mozilla/5.0 (Lumi Apps availability checker)"
_IPV4_RESOLUTION_LOCK = threading.Lock()


def _urlopen_ipv4(request, *, timeout):
    original_getaddrinfo = socket.getaddrinfo

    def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        records = original_getaddrinfo(host, port, family, type, proto, flags)
        ipv4 = [record for record in records if record[0] == socket.AF_INET]
        return ipv4 or records

    with _IPV4_RESOLUTION_LOCK:
        socket.getaddrinfo = ipv4_getaddrinfo
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        finally:
            socket.getaddrinfo = original_getaddrinfo


def _lookup_country_records(ids, country, attempts=3):
    query = urllib.parse.urlencode({
        "id": ",".join(sorted(ids)),
        "country": country,
        "entity": "software",
        "limit": 200,
    })
    req = urllib.request.Request(f"{LOOKUP_URL}?{query}", headers={"User-Agent": UA})
    last_error = None
    for attempt in range(attempts):
        try:
            with _urlopen_ipv4(req, timeout=30) as response:
                payload = json.load(response)
            return {
                str(item["trackId"]): item
                for item in payload.get("results", [])
                if isinstance(item, dict) and item.get("trackId")
            }
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP:
                raise
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"App Store lookup failed for {country}: {last_error}")


def _lookup_country(ids, country, attempts=3):
    return set(_lookup_country_records(ids, country, attempts))


def fetch_live_ids(ids):
    wanted = {str(value) for value in ids if value}
    live = set()
    for country in LOOKUP_COUNTRIES:
        live.update(_lookup_country(wanted, country))
    return live & wanted


def _read_state(path, *, strict=False, now=None):
    try:
        raw = manifest._read(path)
        source = manifest.current_source()
        expected_ids = {app["app_id"] for app in source["apps"].values()}
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != STATE_SCHEMA
            or raw.get("source_sha256") != source["source_sha256"]
            or raw.get("roster_digest") != source["roster_digest"]
            or raw.get("locale_roster_sha256") != source["locale_roster_sha256"]
            or type(raw.get("ttl_seconds")) is not int
            or not 0 < raw["ttl_seconds"] <= manifest.MAX_TTL_SECONDS
            or not isinstance(raw.get("live_ids"), list)
            or len(raw["live_ids"]) != len(expected_ids)
            or set(raw["live_ids"]) != expected_ids
            or raw.get("miss_counts") != {}
            or raw.get("source") != STATE_SOURCE
            or raw.get("retire_after_consecutive_misses")
            != RETIRE_AFTER_MISSES
        ):
            raise ValueError("legacy snapshot or current-source identity drift")
        age = (
            manifest._now(now) - manifest.timestamp(raw.get("observed_at"))
        ).total_seconds()
        if not 0 <= age < raw["ttl_seconds"]:
            raise ValueError("snapshot observed_at is stale or in the future")
        return {"live_ids": expected_ids, "miss_counts": {}, **{
            field: raw[field] for field in ("source_sha256", "observed_at")
        }}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Invalid current-source App Store live state: {path}: {error}; "
            "no registry or legacy-state fallback is permitted"
        ) from error


def _write_state(path, live_ids, miss_counts, *, observed_at, source_sha256):
    path = manifest.snapshot_destination(path)
    source = manifest.current_source()
    if (
        set(live_ids) != {app["app_id"] for app in source["apps"].values()}
        or miss_counts != {} or source_sha256 != source["source_sha256"]
    ):
        raise RuntimeError("Cannot write a partial or mismatched current-source live state")
    age = (manifest._now(None) - manifest.timestamp(observed_at)).total_seconds()
    if not 0 <= age < manifest.MAX_TTL_SECONDS:
        raise RuntimeError("Cannot write a stale or future current-source observation")
    payload = {
        "schema": STATE_SCHEMA,
        "source": STATE_SOURCE,
        "source_sha256": source_sha256,
        "roster_digest": source["roster_digest"],
        "locale_roster_sha256": source["locale_roster_sha256"],
        "observed_at": observed_at,
        "ttl_seconds": manifest.MAX_TTL_SECONDS,
        "retire_after_consecutive_misses": RETIRE_AFTER_MISSES,
        "live_ids": sorted(live_ids),
        "miss_counts": dict(sorted(miss_counts.items())),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    previous = ""
    try:
        with open(path, encoding="utf-8") as handle:
            previous = handle.read()
    except OSError:
        pass
    if text != previous:
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, mode=0o700, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.",
            suffix=".tmp",
            dir=directory,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
            directory_descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)


def live_app_keys(
    appstore,
    pages_dir,
    refresh=True,
    *,
    seed_state_path=None,
    strict_state=False,
):
    """Use one complete source-bound observation; never infer a new denominator."""
    validate_consumer(appstore)
    state_path = os.path.join(pages_dir, STATE_FILE)
    if os.environ.get("GROWTH_LIVE_MANIFEST"):
        document = manifest.require_public_inventory(manifest.load_manifest())
    elif refresh:
        document = manifest.require_public_inventory(manifest.refresh_manifest())
        manifest.write_legacy_live_state(state_path, document)
    else:
        selected = state_path
        if not os.path.exists(selected) and seed_state_path:
            selected = seed_state_path
        _read_state(selected, strict=True)
        return set(appstore)
    return set(document["apps"])
