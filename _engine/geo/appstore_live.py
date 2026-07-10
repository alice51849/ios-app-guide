#!/usr/bin/env python3
"""Track which registry apps are publicly available on the App Store."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

LOOKUP_URL = "https://itunes.apple.com/lookup"
LOOKUP_COUNTRIES = ("us", "tw", "jp", "gb")
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
RETIRE_AFTER_MISSES = 3
STATE_FILE = ".appstore_live_state.json"
UA = "Mozilla/5.0 (Lumi Apps availability checker)"


def _lookup_country(ids, country, attempts=3):
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
                str(item["trackId"])
                for item in payload.get("results", [])
                if item.get("trackId")
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


def fetch_live_ids(ids):
    wanted = {str(value) for value in ids if value}
    live = set()
    for country in LOOKUP_COUNTRIES:
        live.update(_lookup_country(wanted, country))
    return live & wanted


def _read_state(path):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
        return {
            "live_ids": {str(value) for value in raw.get("live_ids", [])},
            "miss_counts": {
                str(key): int(value)
                for key, value in raw.get("miss_counts", {}).items()
            },
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"live_ids": set(), "miss_counts": {}}


def _write_state(path, live_ids, miss_counts):
    payload = {
        "source": "Apple iTunes Lookup API (US, TW, JP, GB)",
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
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def live_app_keys(appstore, pages_dir, refresh=True):
    """Return public app keys, retaining a formerly-live app until 3 clean misses."""
    state_path = os.path.join(pages_dir, STATE_FILE)
    state = _read_state(state_path)
    known_ids = {str(value) for value in appstore.values() if value}

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
