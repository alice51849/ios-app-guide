#!/usr/bin/env python3
"""Format check for the App Store storefront snapshot (.appstore_storefront_state.json).

geo-daily commits a freshly re-fetched snapshot on its own (see
commit_storefront_snapshot.py) before the slow route/derived-file suites run,
so a red route suite no longer throws away readback-confirmed ``zero_since``
history (11-25 ruling 2307 item 1).  This checker is the snapshot's own gate:
it validates only the file itself, never the pages generated from it.

Checks: version/shape, ``checked_at`` freshness, storefront list, ids,
per-record price/currency/readback/rating fields, ``zero_since`` only on a
readback-confirmed zero and never after ``checked_at``; against the previous
committed snapshot (``--previous``): ``paid_seen`` only grows, ``checked_at``
never goes back, and a still-confirmed zero keeps its earlier ``zero_since``
(in the storefronts the loader prints from).

Exit 0 = OK, 1 = problems (printed one per line).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from app_store_storefronts import (  # noqa: E402
    AVAILABILITY_STOREFRONTS,
    CURRENCY_RE,
    LOCALE_STOREFRONTS,
    PRICE_RE,
    STATE_FILE,
    snapshot_paid_seen,
    snapshot_prices_fresh,
)

DETAIL_FIELDS = frozenset({
    "price",
    "currency",
    "formatted_price",
    "rating_value",
    "rating_count",
    "price_readback",
    "currency_readback",
    "zero_since",
})


def _utc(value: object) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _digit_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item.isdigit() for item in value)
        and value == sorted(set(value))
    )


def _is_zero(value: object) -> bool:
    return (
        isinstance(value, str)
        and PRICE_RE.fullmatch(value) is not None
        and float(value) == 0
    )


def _check_detail(
    where: str,
    detail: object,
    checked_at: dt.datetime | None,
) -> list[str]:
    if not isinstance(detail, dict):
        return [f"{where}: 不是物件"]
    problems: list[str] = []
    extra = sorted(set(detail) - DETAIL_FIELDS)
    if extra:
        problems.append(f"{where}: 多出欄位 {extra}")
    price = detail.get("price")
    if not isinstance(price, str) or PRICE_RE.fullmatch(price) is None:
        problems.append(f"{where}: price 格式錯 {price!r}")
    currency = detail.get("currency")
    if not isinstance(currency, str) or CURRENCY_RE.fullmatch(currency) is None:
        problems.append(f"{where}: currency 格式錯 {currency!r}")
    formatted = detail.get("formatted_price")
    if (
        not isinstance(formatted, str)
        or not formatted.strip()
        or len(formatted) > 64
    ):
        problems.append(f"{where}: formatted_price 格式錯")
    has_rating = ("rating_value" in detail, "rating_count" in detail)
    if any(has_rating):
        value = detail.get("rating_value")
        count = detail.get("rating_count")
        if (
            not all(has_rating)
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0 <= float(value) <= 5
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            problems.append(f"{where}: 評分欄位不成對或超出範圍")
    has_readback = ("price_readback" in detail, "currency_readback" in detail)
    if any(has_readback):
        readback = detail.get("price_readback")
        readback_currency = detail.get("currency_readback")
        if (
            not all(has_readback)
            or not isinstance(readback, str)
            or PRICE_RE.fullmatch(readback) is None
            or not isinstance(readback_currency, str)
            or CURRENCY_RE.fullmatch(readback_currency) is None
        ):
            problems.append(f"{where}: 讀回欄位不成對或格式錯")
    if "zero_since" in detail:
        since = _utc(detail.get("zero_since"))
        if since is None:
            problems.append(f"{where}: zero_since 不是帶時區的時間")
        elif checked_at is not None and since > checked_at:
            problems.append(f"{where}: zero_since 晚於 checked_at")
        if not (
            _is_zero(price)
            and detail.get("price_readback") == price
            and detail.get("currency_readback") == currency
        ):
            problems.append(f"{where}: zero_since 只能出現在讀回確認的 0 價")
    return problems


def check_snapshot(
    payload: object,
    *,
    previous: object = None,
    now: dt.datetime | None = None,
) -> list[str]:
    """Return a list of problems; empty means the snapshot may be committed."""
    if not isinstance(payload, dict):
        return ["快照不是 JSON 物件"]
    problems: list[str] = []
    if payload.get("version") != 2:
        problems.append(f"version 應為 2，實為 {payload.get('version')!r}")
    if not isinstance(payload.get("source"), str) or not payload["source"]:
        problems.append("source 缺")
    checked_at = _utc(payload.get("checked_at"))
    if checked_at is None:
        problems.append("checked_at 缺或沒有時區")
    elif not snapshot_prices_fresh(payload, now):
        problems.append("checked_at 過期或在未來")
    storefronts = sorted(AVAILABILITY_STOREFRONTS)
    if payload.get("storefronts") != storefronts:
        problems.append("storefronts 與 AVAILABILITY_STOREFRONTS 不同")
    app_ids = payload.get("app_ids")
    if not _digit_list(app_ids) or not app_ids:
        problems.append("app_ids 須為排序、不重複的數字字串清單")
        app_ids = []
    if payload.get("app_count") != len(app_ids):
        problems.append("app_count 與 app_ids 數量不同")
    known_ids = set(app_ids)
    countries = payload.get("countries")
    if not isinstance(countries, dict) or not countries:
        problems.append("countries 缺或為空")
        countries = {}
    for country, ids in countries.items():
        if country not in AVAILABILITY_STOREFRONTS:
            problems.append(f"countries.{country}: 不是已知店面")
        if not _digit_list(ids):
            problems.append(f"countries.{country}: 須為排序、不重複的數字字串清單")
        elif not set(ids) <= known_ids:
            problems.append(f"countries.{country}: 含 app_ids 以外的 ID")
    details = payload.get("details")
    if not isinstance(details, dict):
        problems.append("details 缺")
        details = {}
    for country, app_details in details.items():
        if country not in countries:
            problems.append(f"details.{country}: countries 沒有這區")
            continue
        if not isinstance(app_details, dict):
            problems.append(f"details.{country}: 不是物件")
            continue
        listed = set(countries[country]) if isinstance(countries[country], list) else set()
        for app_id, detail in app_details.items():
            where = f"details.{country}.{app_id}"
            if app_id not in listed:
                problems.append(f"{where}: 不在 countries.{country}")
            problems.extend(_check_detail(where, detail, checked_at))
    paid_seen = payload.get("paid_seen")
    if not isinstance(paid_seen, dict):
        problems.append("paid_seen 缺")
        paid_seen = {}
    for country, ids in paid_seen.items():
        if country not in AVAILABILITY_STOREFRONTS:
            problems.append(f"paid_seen.{country}: 不是已知店面")
        if not _digit_list(ids) or not ids:
            problems.append(f"paid_seen.{country}: 須為非空、排序、不重複的數字字串清單")
    if isinstance(previous, dict):
        problems.extend(_check_against_previous(payload, previous, checked_at))
    return problems


def _check_against_previous(
    payload: dict,
    previous: dict,
    checked_at: dt.datetime | None,
) -> list[str]:
    problems: list[str] = []
    before = _utc(previous.get("checked_at"))
    if before is not None and checked_at is not None and checked_at < before:
        problems.append("checked_at 比上一份快照早")
    now_seen = snapshot_paid_seen(payload)
    for country, ids in sorted(snapshot_paid_seen(previous).items()):
        lost = sorted(ids - now_seen.get(country, set()))
        if lost:
            problems.append(f"paid_seen.{country}: 少了 {lost}（只能增加）")
    old_details = previous.get("details")
    new_details = payload.get("details")
    if not isinstance(old_details, dict) or not isinstance(new_details, dict):
        return problems
    # Only storefronts the loader prints from carry zero_since history: the
    # refresher reads its previous records through load_storefront_details,
    # which skips the extra (hk/mo) storefronts, so theirs restarts each run
    # and is never printed.
    printed = set(LOCALE_STOREFRONTS.values())
    for country, app_details in new_details.items():
        if country not in printed or not isinstance(app_details, dict):
            continue
        for app_id, detail in app_details.items():
            if not isinstance(detail, dict) or "zero_since" not in detail:
                continue
            old = old_details.get(country, {})
            old = old.get(app_id, {}) if isinstance(old, dict) else {}
            if not isinstance(old, dict):
                continue
            old_confirmed = (
                old.get("price") == detail.get("price")
                and old.get("price_readback") == detail.get("price")
                and isinstance(old.get("zero_since"), str)
            )
            if old_confirmed and detail["zero_since"] != old["zero_since"]:
                problems.append(
                    f"details.{country}.{app_id}: zero_since 被重設"
                    f"（上一份 {old['zero_since']}）"
                )
    return problems


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--pages",
        default=os.environ.get("GEO_PAGES", str(HERE / "pages")),
        help="指南站根目錄（快照所在處）",
    )
    parser.add_argument("--previous", help="上一份已提交的快照（可省略）")
    parser.add_argument("--now", help="判讀時間（ISO，測試用；預設現在）")
    args = parser.parse_args(argv)
    path = Path(args.pages) / STATE_FILE
    try:
        payload = _read_json(path)
    except (OSError, ValueError) as error:
        print(f"快照讀不到：{path}（{error}）")
        return 1
    previous = None
    if args.previous:
        try:
            previous = _read_json(Path(args.previous))
        except (OSError, ValueError):
            previous = None
    now = _utc(args.now) if args.now else None
    problems = check_snapshot(payload, previous=previous, now=now)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"快照格式 OK：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
