#!/usr/bin/env python3
"""Refresh country-level App Store availability for direct download links."""

from __future__ import annotations

import argparse
import datetime as dt
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from app_store_storefronts import (  # noqa: E402
    AVAILABILITY_STOREFRONTS,
    STATE_FILE,
    load_storefront_availability,
    load_storefront_details,
    snapshot_paid_seen,
)
from appstore_live import _lookup_country_records, live_app_keys  # noqa: E402
from family_travel_dataset import write_text_if_changed  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
MAX_AGE = dt.timedelta(hours=20)


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _read_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_fresh(
    payload: dict[str, object],
    now: dt.datetime,
    expected_app_ids: set[str],
) -> bool:
    cached_app_ids = payload.get("app_ids")
    if (
        payload.get("version") != 2
        or not isinstance(payload.get("countries"), dict)
        or not isinstance(payload.get("details"), dict)
        or payload.get("app_count") != len(expected_app_ids)
        or not isinstance(cached_app_ids, list)
        or any(
            not isinstance(app_id, str) or not app_id.isdigit()
            for app_id in cached_app_ids
        )
        or set(cached_app_ids) != expected_app_ids
        # A snapshot taken over a different storefront list (e.g. before the
        # hk/mo extra storefronts were queried) is stale, not "fresh".
        or payload.get("storefronts") != sorted(AVAILABILITY_STOREFRONTS)
    ):
        return False
    value = payload.get("checked_at")
    if not isinstance(value, str):
        return False
    try:
        checked = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return dt.timedelta(0) <= now - checked < MAX_AGE


def _public_detail(item: dict[str, object]) -> dict[str, object] | None:
    price_value = item.get("price")
    if isinstance(price_value, bool):
        return None
    try:
        price = Decimal(str(price_value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    currency = item.get("currency")
    formatted_price = item.get("formattedPrice")
    if (
        not price.is_finite()
        or price < 0
        or not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isalpha()
        or not isinstance(formatted_price, str)
        or not formatted_price.strip()
        or len(formatted_price) > 64
    ):
        return None
    price_text = format(price.normalize(), "f")
    detail: dict[str, object] = {
        "price": price_text,
        "currency": currency.upper(),
        "formatted_price": formatted_price.strip(),
    }
    rating_value = item.get("averageUserRating")
    rating_count = item.get("userRatingCount")
    if (
        isinstance(rating_value, (int, float))
        and not isinstance(rating_value, bool)
        and 0 <= float(rating_value) <= 5
        and isinstance(rating_count, int)
        and not isinstance(rating_count, bool)
        and rating_count > 0
    ):
        detail["rating_value"] = round(float(rating_value), 1)
        detail["rating_count"] = rating_count
    return detail


def _retained_details(
    previous_details: dict[str, dict[str, dict[str, object]]],
    country: str,
) -> dict[str, dict[str, object]]:
    """Carry cached facts over without any live readback: not printable."""
    retained: dict[str, dict[str, object]] = {}
    for app_id, detail in previous_details.get(country, {}).items():
        record = dict(detail)
        record.pop("price_readback", None)
        record.pop("currency_readback", None)
        record.pop("zero_since", None)
        retained[app_id] = record
    return retained


def refresh(pages=PAGES, *, force=False) -> dict[str, frozenset[str]]:
    pages = Path(pages)
    path = pages / STATE_FILE
    previous_payload = _read_payload(path)
    now = _utc_now()
    live_keys = live_app_keys(APPSTORE, pages, refresh=False)
    app_ids = {str(APPSTORE[key]) for key in live_keys}
    if not force and _is_fresh(previous_payload, now, app_ids):
        return load_storefront_availability(pages)

    previous = load_storefront_availability(pages)
    paid_seen = snapshot_paid_seen(previous_payload)
    # Raw records: the refresher needs last run's prices even when they are
    # no longer printable, to carry them over and to confirm zero prices.
    previous_details = load_storefront_details(pages, verified=False)
    countries: dict[str, list[str]] = {}
    details: dict[str, dict[str, dict[str, object]]] = {}
    fresh_countries: list[str] = []
    refreshed = 0
    for country in sorted(AVAILABILITY_STOREFRONTS):
        try:
            records = _lookup_country_records(app_ids, country)
        except Exception as error:
            if country not in previous:
                print(f"{country}: unavailable ({error})")
                continue
            observed = set(previous[country])
            country_details = _retained_details(previous_details, country)
            print(f"{country}: retained cached snapshot ({error})")
        else:
            observed = set(records)
            if not observed and previous.get(country):
                observed = set(previous[country])
                country_details = _retained_details(previous_details, country)
                print(f"{country}: retained non-empty snapshot after zero result")
            else:
                country_details = {}
                for app_id, item in records.items():
                    detail = _public_detail(item)
                    if detail is not None:
                        country_details[app_id] = detail
                fresh_countries.append(country)
                refreshed += 1
        countries[country] = sorted(observed & app_ids)
        details[country] = {
            app_id: country_details[app_id]
            for app_id in countries[country]
            if app_id in country_details
        }

    if not countries:
        raise RuntimeError("No App Store storefront snapshots are available")
    checked_at = now.isoformat().replace("+00:00", "Z")
    # Live readback: a second lookup pass, after the whole first sweep, must
    # report the same price before generators may print it.  Countries whose
    # readback fails keep no readback, so their prices are not printed.
    for country in fresh_countries:
        try:
            readback_records = _lookup_country_records(app_ids, country)
        except Exception as error:
            print(f"{country}: price readback unavailable ({error})")
            continue
        for app_id, detail in details[country].items():
            item = readback_records.get(app_id)
            readback = None if item is None else _public_detail(item)
            if readback is not None:
                detail["price_readback"] = readback["price"]
                detail["currency_readback"] = readback["currency"]
            if (
                readback is not None
                and readback["price"] == detail["price"]
                and readback["currency"] == detail["currency"]
                and float(detail["price"]) == 0
            ):
                # Keep the earliest readback-confirmed zero; any break in the
                # chain (paid, missing, unconfirmed) restarts the clock.
                previous_detail = previous_details.get(country, {}).get(
                    app_id, {}
                )
                previous_confirmed_zero = (
                    previous_detail.get("price") == detail["price"]
                    and previous_detail.get("price_readback") == detail["price"]
                    and isinstance(previous_detail.get("zero_since"), str)
                )
                detail["zero_since"] = (
                    previous_detail["zero_since"]
                    if previous_confirmed_zero
                    else checked_at
                )
    # Sticky paid history: carried over even when a storefront or an app is
    # missing from this refresh, so it can only grow.
    for country, app_details in details.items():
        for app_id, detail in app_details.items():
            for field in ("price", "price_readback"):
                value = detail.get(field)
                if isinstance(value, str) and float(value) > 0:
                    paid_seen.setdefault(country, set()).add(app_id)
    payload = {
        "version": 2,
        "source": "Apple iTunes Lookup API",
        "checked_at": checked_at,
        "app_count": len(app_ids),
        "app_ids": sorted(app_ids),
        "storefronts": sorted(AVAILABILITY_STOREFRONTS),
        "countries": countries,
        "details": details,
        "paid_seen": {
            country: sorted(seen_ids)
            for country, seen_ids in sorted(paid_seen.items())
            if seen_ids
        },
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
