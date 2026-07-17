#!/usr/bin/env python3
"""Refresh country-level App Store availability for direct download links."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from app_store_storefronts import (  # noqa: E402
    LOCALE_STOREFRONTS,
    STATE_FILE,
    load_storefront_availability,
)
from appstore_live import _lookup_country, live_app_keys  # noqa: E402
from family_travel_dataset import write_text_if_changed  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PAGES = HERE / "pages"
MAX_AGE = dt.timedelta(hours=20)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _read_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_fresh(payload: dict[str, object], now: dt.datetime) -> bool:
    value = payload.get("checked_at")
    if not isinstance(value, str):
        return False
    try:
        checked = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return dt.timedelta(0) <= now - checked < MAX_AGE


def refresh(pages=PAGES, *, force=False) -> dict[str, frozenset[str]]:
    pages = Path(pages)
    path = pages / STATE_FILE
    previous_payload = _read_payload(path)
    now = _utc_now()
    if not force and _is_fresh(previous_payload, now):
        return load_storefront_availability(pages)

    live_keys = live_app_keys(APPSTORE, pages, refresh=False)
    app_ids = {APPSTORE[key] for key in live_keys}
    previous = load_storefront_availability(pages)
    countries: dict[str, list[str]] = {}
    refreshed = 0
    for country in sorted(set(LOCALE_STOREFRONTS.values())):
        try:
            observed = _lookup_country(app_ids, country)
        except Exception as error:
            if country not in previous:
                print(f"{country}: unavailable ({error})")
                continue
            observed = set(previous[country])
            print(f"{country}: retained cached snapshot ({error})")
        else:
            if not observed and previous.get(country):
                observed = set(previous[country])
                print(f"{country}: retained non-empty snapshot after zero result")
            else:
                refreshed += 1
        countries[country] = sorted(observed & app_ids)

    if not countries:
        raise RuntimeError("No App Store storefront snapshots are available")
    payload = {
        "version": 1,
        "source": "Apple iTunes Lookup API",
        "checked_at": now.isoformat().replace("+00:00", "Z"),
        "app_count": len(app_ids),
        "countries": countries,
    }
    write_text_if_changed(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    print(
        f"storefront availability: apps={len(app_ids)}, "
        f"countries={len(countries)}, refreshed={refreshed}"
    )
    return {
        country: frozenset(ids)
        for country, ids in countries.items()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    refresh(force=args.force)


if __name__ == "__main__":
    main()
