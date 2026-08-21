#!/usr/bin/env python3
"""Track which registry apps are publicly available on the App Store."""
from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

LOOKUP_URL = "https://itunes.apple.com/lookup"
LOOKUP_COUNTRIES = ("us", "tw", "jp", "gb")
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
RETIRE_AFTER_MISSES = 3
STATE_FILE = ".appstore_live_state.json"
STATE_SOURCE = "Apple iTunes Lookup API (US, TW, JP, GB)"
UA = "Mozilla/5.0 (Lumi Apps availability checker)"


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
            with urllib.request.urlopen(req, timeout=30) as response:
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


def _read_state(path, *, strict=False):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("state must be a JSON object")
        live_values = raw.get("live_ids")
        miss_values = raw.get("miss_counts")
        if not isinstance(live_values, list) or not isinstance(
            miss_values, dict
        ):
            raise ValueError("state must include live_ids and miss_counts")
        live_ids = {str(value) for value in live_values}
        miss_counts = {
            str(key): int(value)
            for key, value in miss_values.items()
        }
        if (
            raw.get("source") != STATE_SOURCE
            or raw.get("retire_after_consecutive_misses")
            != RETIRE_AFTER_MISSES
            or any(not value.isdigit() for value in live_ids)
            or any(
                key not in live_ids
                or value < 0
                or value >= RETIRE_AFTER_MISSES
                for key, value in miss_counts.items()
            )
        ):
            raise ValueError("state metadata or values are invalid")
        return {"live_ids": live_ids, "miss_counts": miss_counts}
    except FileNotFoundError:
        return {"live_ids": set(), "miss_counts": {}}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        if strict:
            raise RuntimeError(f"Invalid App Store live state: {path}") from error
        return {"live_ids": set(), "miss_counts": {}}


def _write_state(path, live_ids, miss_counts):
    payload = {
        "source": STATE_SOURCE,
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
    """Return public app keys, retaining a formerly-live app until 3 clean misses."""
    state_path = os.path.join(pages_dir, STATE_FILE)
    known_ids = {str(value) for value in appstore.values() if value}
    state_exists = os.path.exists(state_path)
    state = _read_state(state_path, strict=strict_state)
    if not state_exists and seed_state_path:
        if not os.path.exists(seed_state_path):
            raise RuntimeError(
                "Verified App Store live-state baseline is missing: "
                f"{seed_state_path}"
            )
        seed = _read_state(seed_state_path, strict=True)
        seed_live = seed["live_ids"] & known_ids
        if not seed_live:
            raise RuntimeError(
                "Verified App Store live-state baseline has no current apps"
            )
        seed_misses = {
            app_id: count
            for app_id, count in seed["miss_counts"].items()
            if app_id in seed_live
        }
        _write_state(state_path, seed_live, seed_misses)
        state = {"live_ids": seed_live, "miss_counts": seed_misses}

    if refresh:
        try:
            observed = fetch_live_ids(known_ids)
            if known_ids and not observed:
                raise RuntimeError("App Store lookup unexpectedly returned zero apps")
            if (
                state["live_ids"]
                and len(observed) < max(1, len(state["live_ids"]) // 2)
            ):
                raise RuntimeError(
                    "App Store lookup returned an implausibly small portfolio"
                )
        except Exception as exc:  # Keep the last verified snapshot on transient failure.
            if not state["live_ids"]:
                raise
            print(f"App Store lookup unavailable; using verified cache: {exc}")
        else:
            previous_live = state["live_ids"] & known_ids
            live_ids = set(observed)
            misses = {}
            for app_id in previous_live - observed:
                count = state["miss_counts"].get(app_id, 0) + 1
                if count < RETIRE_AFTER_MISSES:
                    live_ids.add(app_id)
                    misses[app_id] = count
            state = {"live_ids": live_ids, "miss_counts": misses}
            _write_state(state_path, live_ids, misses)

    if not state["live_ids"]:
        observed = fetch_live_ids(known_ids)
        state = {"live_ids": observed, "miss_counts": {}}
        _write_state(state_path, observed, {})

    return {
        key
        for key, app_id in appstore.items()
        if str(app_id) in state["live_ids"]
    }
