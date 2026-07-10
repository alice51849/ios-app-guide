#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared deterministic rotation, localization, and HTTP retry helpers."""

import datetime as _dt
import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_DATE = _dt.date(2026, 1, 1)
DEFAULT_UA = "Mozilla/5.0 (Lumi Apps poster)"
DEAD_LINK_STATUSES = frozenset((404, 410))
TRANSIENT_STATUSES = frozenset((408, 429))

FOOTERS = {
    "en": "— Lumi Apps · Independent iOS developer",
    "zh-Hant": "— Lumi Apps · 獨立 iOS 開發者",
    "zh-Hans": "— Lumi Apps · 独立 iOS 开发者",
    "ja": "— Lumi Apps · 個人開発の iOS アプリ",
    "ko": "— Lumi Apps · 인디 iOS 개발자",
    "ms": "— Lumi Apps · Pembangun iOS indie",
    "de": "— Lumi Apps · Unabhängig entwickelte iOS-Apps",
    "fr": "— Lumi Apps · Développement iOS indépendant",
    "es": "— Lumi Apps · Desarrollo iOS independiente",
    "pt-BR": "— Lumi Apps · Desenvolvimento iOS independente",
    "ru": "— Lumi Apps · Независимый разработчик iOS",
    "ar": "— Lumi Apps · تطوير مستقل لتطبيقات iOS",
    "pl": "— Lumi Apps · Niezależne aplikacje iOS",
}

# Explicit offsets are stable across runners (unlike Python's randomized hash()).
CHANNEL_SPECS = {
    "telegram:asia": {
        "langs": ("zh-Hant", "ja", "ko", "zh-Hans", "ms"),
        "offset": 0,
    },
    "threads:asia": {
        "langs": ("zh-Hant", "ja", "ko", "zh-Hans", "ms"),
        "offset": 29,
    },
    "telegram:eu_me": {
        "langs": ("de", "fr", "es", "pt-BR", "ru", "ar", "pl"),
        "offset": 11,
    },
    "threads:west": {
        "langs": ("en", "es", "de", "fr", "pt-BR", "ru", "ar", "pl"),
        "offset": 47,
    },
    "telegram:americas": {
        "langs": ("en", "es", "pt-BR"),
        "offset": 23,
    },
}

# This mirrors the five UTC cron times, so every later channel avoids earlier picks.
CHANNEL_ORDER = (
    "telegram:asia",
    "threads:asia",
    "telegram:eu_me",
    "threads:west",
    "telegram:americas",
)
_SCHEDULE_CACHE = {}


class RequestError(RuntimeError):
    """A request failed or returned an unusable response."""


class HTTPStatusError(RequestError):
    """A request returned an HTTP error status."""

    def __init__(self, label, status, body="", attempts=1):
        self.label = label
        self.status = status
        self.body = body
        self.attempts = attempts
        suffix = f" after {attempts} attempts" if attempts > 1 else ""
        detail = f": {body[:200]}" if body else ""
        super().__init__(f"{label} failed{suffix}: HTTP {status}{detail}")


class ScheduleCapacityError(ValueError):
    """A reduced content pool cannot supply unique posts to every channel."""


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc)


def as_utc(now=None):
    now = utc_now() if now is None else now
    if now.tzinfo is None:
        return now.replace(tzinfo=_dt.timezone.utc)
    return now.astimezone(_dt.timezone.utc)


def day_sequence(now=None):
    return (as_utc(now).date() - BASE_DATE).days


def footer_for(lang):
    """Return a localized footer, safely defaulting unknown languages to English."""
    return FOOTERS.get(lang, FOOTERS["en"])


def item_key(item):
    return (
        item.get("lang", ""),
        item.get("app", ""),
        item.get("text", ""),
        item.get("url", ""),
    )


def is_transient_status(status):
    return status in TRANSIENT_STATUSES or 500 <= status <= 599


def rotated_channel_candidates(pool, channel, now=None):
    """Return a channel's language subset, rotated one position per UTC day."""
    if channel not in CHANNEL_SPECS:
        raise ValueError(f"unknown social channel: {channel}")
    items = list(pool)
    spec = CHANNEL_SPECS[channel]
    subset = [item for item in items if item.get("lang") in spec["langs"]]
    if not subset:
        subset = items
    if not subset:
        raise ValueError("social post pool is empty")
    start = (day_sequence(now) + spec["offset"]) % len(subset)
    return subset[start:] + subset[:start]


def _new_schedule(pool):
    items = list(pool)
    subsets = {}
    for channel in CHANNEL_ORDER:
        spec = CHANNEL_SPECS[channel]
        subset = [item for item in items if item.get("lang") in spec["langs"]]
        subset = subset or items
        if not subset:
            raise ValueError("social post pool is empty")
        keys = [item_key(item) for item in subset]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate social post in {channel} pool")
        subsets[channel] = subset
    return {
        "subsets": subsets,
        "schedules": {channel: {} for channel in CHANNEL_ORDER},
        "planned_cycles": {channel: set() for channel in CHANNEL_ORDER},
    }


def _cycle_items(state, channel, cycle):
    subset = state["subsets"][channel]
    step = CHANNEL_ORDER.index(channel) + 1
    offset = (CHANNEL_SPECS[channel]["offset"] + cycle * step) % len(subset)
    return subset[offset:] + subset[:offset]


def _ensure_schedule_through(state, channel_index, end_day):
    channel = CHANNEL_ORDER[channel_index]
    subset = state["subsets"][channel]
    final_cycle = end_day // len(subset)
    for cycle in range(final_cycle + 1):
        if cycle in state["planned_cycles"][channel]:
            continue
        start = cycle * len(subset)
        days = list(range(start, start + len(subset)))
        for earlier_index in range(channel_index):
            _ensure_schedule_through(state, earlier_index, days[-1])

        items = _cycle_items(state, channel, cycle)
        forbidden = {
            day: {
                item_key(state["schedules"][earlier][day])
                for earlier in CHANNEL_ORDER[:channel_index]
            }
            for day in days
        }
        item_to_day = {}
        day_to_item = {}

        def assign(day, seen_items):
            day_offset = day - start
            for offset in range(len(items)):
                item_index = (day_offset + offset) % len(items)
                if item_index in seen_items:
                    continue
                item = items[item_index]
                if item_key(item) in forbidden[day]:
                    continue
                seen_items.add(item_index)
                previous_day = item_to_day.get(item_index)
                if previous_day is None or assign(previous_day, seen_items):
                    item_to_day[item_index] = day
                    day_to_item[day] = item_index
                    return True
            return False

        ordered_days = sorted(
            days,
            key=lambda day: (
                len(items) - sum(
                    item_key(item) in forbidden[day] for item in items
                ),
                day,
            ),
        )
        for day in ordered_days:
            if not assign(day, set()):
                raise ScheduleCapacityError(
                    f"cannot build a fair cycle for {channel}; "
                    "add more localized content"
                )
        if len(day_to_item) != len(days):
            raise ScheduleCapacityError(
                f"incomplete fair cycle for {channel}; add more localized content"
            )
        for day, item_index in day_to_item.items():
            state["schedules"][channel][day] = items[item_index]
        state["planned_cycles"][channel].add(cycle)


def _scheduled_picks(pool, through_channel, now=None):
    target_day = day_sequence(now)
    if target_day < 0:
        raise ValueError(f"social schedule predates {BASE_DATE.isoformat()}")
    items = list(pool)
    signature = tuple(item_key(item) for item in items)
    state = _SCHEDULE_CACHE.get(signature)
    if state is None:
        state = _new_schedule(items)
        _SCHEDULE_CACHE[signature] = state

    target_index = CHANNEL_ORDER.index(through_channel)
    for channel_index in range(target_index + 1):
        _ensure_schedule_through(state, channel_index, target_day)
    return {
        channel: state["schedules"][channel][target_day]
        for channel in CHANNEL_ORDER[: target_index + 1]
    }


def channel_candidates(pool, channel, now=None):
    """Return fair-cycle candidates without same-day cross-channel duplication."""
    if channel not in CHANNEL_ORDER:
        raise ValueError(f"unknown social channel: {channel}")
    items = list(pool)
    try:
        picks = _scheduled_picks(items, CHANNEL_ORDER[-1], now)
    except ScheduleCapacityError:
        # Small test or recovery pools may not be large enough for all channels.
        picks = _scheduled_picks(items, channel, now)
    selected = picks[channel]
    selected_key = item_key(selected)
    blocked = {
        item_key(item)
        for current, item in picks.items()
        if current != channel
    }
    rotated = rotated_channel_candidates(items, channel, now)
    safe = [
        item
        for item in rotated
        if item_key(item) != selected_key and item_key(item) not in blocked
    ]
    fallback = [
        item
        for item in rotated
        if item_key(item) != selected_key and item_key(item) in blocked
    ]
    return [selected, *safe, *fallback]


def _error_body(error):
    try:
        raw = error.read(2048)
    except Exception:  # The status remains useful even if its body cannot be read.
        return ""
    finally:
        error.close()
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace").strip()
    return str(raw).strip()


def _sleep_for_retry(label, attempt, sleeper, retry_delays, reason):
    delay = (
        retry_delays[attempt]
        if attempt < len(retry_delays)
        else retry_delays[-1] * (2 ** (attempt - len(retry_delays) + 1))
    )
    print(
        f"{label}: transient {reason}; retrying attempt {attempt + 2} "
        f"of {len(retry_delays) + 1} in {delay:g}s",
        file=sys.stderr,
    )
    sleeper(delay)


def validate_url(
    url,
    *,
    timeout=15,
    attempts=3,
    opener=None,
    sleeper=None,
    retry_delays=(1, 2),
):
    """Return False only for a confirmed 404/410; transient failures raise."""
    parsed = urllib.parse.urlsplit(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"invalid post URL: {url!r}")
    if attempts < 1:
        raise ValueError("attempts must be positive")
    opener = urllib.request.urlopen if opener is None else opener
    sleeper = time.sleep if sleeper is None else sleeper
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA}, method="HEAD")

    for attempt in range(attempts):
        try:
            with opener(req, timeout=timeout):
                return True
        except urllib.error.HTTPError as error:
            if error.code in DEAD_LINK_STATUSES:
                error.close()
                return False
            if not is_transient_status(error.code):
                # Only 404/410 prove the destination is dead; e.g. 403/405 still
                # confirms that an HTTP endpoint exists.
                error.close()
                return True
            if attempt == attempts - 1:
                raise HTTPStatusError(
                    "URL validation", error.code, _error_body(error), attempts
                ) from error
            error.close()
            _sleep_for_retry(
                "URL validation",
                attempt,
                sleeper,
                retry_delays,
                f"HTTP {error.code}",
            )
        except (
            urllib.error.URLError,
            OSError,
            http.client.HTTPException,
        ) as error:
            if attempt == attempts - 1:
                raise RequestError(
                    f"URL validation failed after {attempts} attempts: {error}"
                ) from error
            _sleep_for_retry(
                "URL validation", attempt, sleeper, retry_delays, type(error).__name__
            )
    raise RequestError("URL validation failed unexpectedly")


def request_json(
    request,
    *,
    label,
    timeout,
    attempts=3,
    opener=None,
    sleeper=None,
    retry_delays=(1, 2),
    extra_transient=None,
):
    """Open an API request with bounded retries and decode its JSON response."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    opener = urllib.request.urlopen if opener is None else opener
    sleeper = time.sleep if sleeper is None else sleeper

    for attempt in range(attempts):
        try:
            with opener(request, timeout=timeout) as response:
                raw = response.read()
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return json.loads(raw)
            except (TypeError, UnicodeError, json.JSONDecodeError) as error:
                if attempt == attempts - 1:
                    raise RequestError(
                        f"{label} returned invalid JSON after {attempts} attempts"
                    ) from error
                _sleep_for_retry(
                    label, attempt, sleeper, retry_delays, "invalid JSON"
                )
        except urllib.error.HTTPError as error:
            body = _error_body(error)
            transient = is_transient_status(error.code)
            if extra_transient is not None:
                transient = transient or bool(extra_transient(error.code, body))
            if not transient:
                raise HTTPStatusError(label, error.code, body) from error
            if attempt == attempts - 1:
                raise HTTPStatusError(
                    label, error.code, body, attempts
                ) from error
            _sleep_for_retry(
                label, attempt, sleeper, retry_delays, f"HTTP {error.code}"
            )
        except (
            urllib.error.URLError,
            OSError,
            http.client.HTTPException,
        ) as error:
            if attempt == attempts - 1:
                raise RequestError(
                    f"{label} failed after {attempts} attempts: {error}"
                ) from error
            _sleep_for_retry(
                label, attempt, sleeper, retry_delays, type(error).__name__
            )
    raise RequestError(f"{label} failed unexpectedly")
