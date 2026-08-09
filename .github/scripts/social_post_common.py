#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared deterministic rotation, localization, and HTTP retry helpers."""

import base64
import concurrent.futures
import datetime as _dt
import http.client
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_DATE = _dt.date(2026, 1, 1)
FULL_LOCALE_SOCIAL_LAUNCH_DATE = _dt.date(2026, 7, 19)
FULL_LOCALE_SOCIAL_LAUNCH_DAYS = 13
DEFAULT_UA = "Mozilla/5.0 (Lumi Apps poster)"
DEAD_LINK_STATUSES = frozenset((404, 410))
TRANSIENT_STATUSES = frozenset((408, 429))
APP_STORE_PATH_RE = re.compile(r"^/app/id(\d+)$")
SOCIAL_IMAGE_PATH_RE = re.compile(
    r"^/ios-app-guide/social/img/([a-z0-9]+)-share\.jpg$"
)

ASIA_LOCALES = (
    "bn-BD",
    "en-AU",
    "gu-IN",
    "hi",
    "id",
    "ja",
    "kn-IN",
    "ko",
    "ml-IN",
    "mr-IN",
    "ms",
    "or-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
    "th",
    "ur-PK",
    "vi",
    "zh-Hans",
    "zh-Hant",
)
EUROPE_MIDDLE_EAST_LOCALES = (
    "ar-SA",
    "ca",
    "cs",
    "da",
    "de-DE",
    "el",
    "en-GB",
    "es-ES",
    "fi",
    "fr-FR",
    "he",
    "hr",
    "hu",
    "it",
    "nl-NL",
    "no",
    "pl",
    "pt-PT",
    "ro",
    "ru",
    "sk",
    "sl-SI",
    "sv",
    "tr",
    "uk",
)
AMERICAS_LOCALES = (
    "en-CA",
    "en-US",
    "es-MX",
    "fr-CA",
    "pt-BR",
)
OFFICIAL_SOCIAL_LOCALES = (
    *ASIA_LOCALES,
    *EUROPE_MIDDLE_EAST_LOCALES,
    *AMERICAS_LOCALES,
)
ASC_SIGNAL_ACTIONS = {
    "ACTIVATE",
    "DOWNLOAD_CONVERT",
    "INTENT_REFINE",
    "PENDING",
    "RETRY",
    "SCALE",
}

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
        "langs": ASIA_LOCALES,
        "offset": 0,
        "region": "asia",
    },
    "threads:asia": {
        "langs": ASIA_LOCALES,
        "offset": 29,
        "region": "asia",
    },
    "threads:eu_me2": {
        "langs": EUROPE_MIDDLE_EAST_LOCALES,
        "offset": 37,
        "region": "eu_me",
    },
    "telegram:eu_me": {
        "langs": EUROPE_MIDDLE_EAST_LOCALES,
        "offset": 11,
        "region": "eu_me",
    },
    "threads:west": {
        "langs": EUROPE_MIDDLE_EAST_LOCALES,
        "offset": 47,
        "region": "eu_me",
    },
    "telegram:americas": {
        "langs": AMERICAS_LOCALES,
        "offset": 23,
        "region": "americas",
    },
    "threads:americas": {
        "langs": AMERICAS_LOCALES,
        "offset": 53,
        "region": "americas",
    },
}

# This mirrors the seven UTC cron times, so every channel gets a distinct App.
CHANNEL_ORDER = (
    "telegram:asia",
    "threads:asia",
    "threads:eu_me2",
    "telegram:eu_me",
    "threads:west",
    "telegram:americas",
    "threads:americas",
)
REGION_LOCALES = {
    "asia": ASIA_LOCALES,
    "eu_me": EUROPE_MIDDLE_EAST_LOCALES,
    "americas": AMERICAS_LOCALES,
}
REGION_CHANNELS = {
    region: tuple(
        channel
        for channel in CHANNEL_ORDER
        if CHANNEL_SPECS[channel]["region"] == region
    )
    for region in REGION_LOCALES
}


def _load_asc_growth_signals(raw=None, today=None):
    if raw is None:
        encoded = os.environ.get("ASC_GROWTH_SIGNALS_B64", "").strip()
        if not encoded:
            return {}, {}
        try:
            raw = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise ValueError(
                "ASC_GROWTH_SIGNALS_B64 must contain valid base64 JSON"
            ) from error
    if not isinstance(raw, str) or not raw.strip():
        return {}, {}
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("ASC growth signals must be valid JSON") from error
    apps = document.get("apps") if isinstance(document, dict) else None
    if (
        not isinstance(document, dict)
        or document.get("version") != 1
        or not isinstance(apps, dict)
        or document.get("app_count") != len(apps)
    ):
        raise ValueError("ASC growth signals have invalid coverage metadata")
    try:
        valid_until = _dt.date.fromisoformat(str(document["valid_until"]))
        _dt.datetime.fromisoformat(
            str(document["generated_at"]).replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("ASC growth signals have invalid timestamps") from error
    current_day = today or _dt.datetime.now(_dt.timezone.utc).date()
    if valid_until < current_day:
        print(
            "WARNING: ASC growth signals expired; using deterministic routing",
            file=sys.stderr,
        )
        return {}, {}

    locales_by_app = {}
    actions_by_app = {}
    for app, signal in apps.items():
        locales = signal.get("locales") if isinstance(signal, dict) else None
        action = signal.get("action") if isinstance(signal, dict) else None
        if (
            not isinstance(app, str)
            or re.fullmatch(r"[a-z0-9]+", app) is None
            or not isinstance(locales, list)
            or len(locales) > 6
            or len(locales) != len(set(locales))
            or any(locale not in OFFICIAL_SOCIAL_LOCALES for locale in locales)
            or action not in ASC_SIGNAL_ACTIONS
        ):
            raise ValueError(f"ASC growth signals have invalid App signal: {app!r}")
        locales_by_app[app] = tuple(locales)
        actions_by_app[app] = action
    return locales_by_app, actions_by_app


ASC_MARKET_LOCALES, ASC_GROWTH_ACTIONS = _load_asc_growth_signals()

# ASC 證實有曝光的市場,在語言輪替中佔幾個位子(長尾語言各佔 1 個)。
# 3 = 主力市場約每 4 次挑選輪到一次,長尾仍會出現、不被排除。
PREFERRED_LOCALE_WEIGHT = 3


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


def item_footer(item):
    value = item.get("footer")
    if value is None:
        return footer_for(item.get("lang"))
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError("social post footer must be a non-empty single line")
    return value.strip()


def canonical_app_store_url(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("App Store URL is missing")
    parsed = urllib.parse.urlsplit(value.strip())
    match = APP_STORE_PATH_RE.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "apps.apple.com"
        or not match
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid canonical App Store URL: {value}")
    return f"https://apps.apple.com/app/id{match.group(1)}"


def canonical_social_image_url(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Social image URL is missing")
    parsed = urllib.parse.urlsplit(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.netloc != "alice51849.github.io"
        or SOCIAL_IMAGE_PATH_RE.fullmatch(parsed.path) is None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid social image URL: {value}")
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, "", "")
    )


def item_image_url(item):
    value = item.get("image_url")
    return None if value is None else canonical_social_image_url(value)


def item_key(item):
    return (
        item.get("lang", ""),
        item.get("app", ""),
        item.get("text", ""),
        item.get("url", ""),
    )


def app_key(item):
    value = str(item.get("app") or "").strip()
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"invalid App Store ID in social post: {value!r}")
    url = canonical_app_store_url(item.get("url"))
    match = APP_STORE_PATH_RE.fullmatch(urllib.parse.urlsplit(url).path)
    if not match or match.group(1) != value:
        raise ValueError(
            f"social post App Store ID does not match its URL: {value} != {url}"
        )
    return value


def is_transient_status(status):
    return status in TRANSIENT_STATUSES or 500 <= status <= 599


def _app_groups(pool):
    groups = {}
    for item in pool:
        groups.setdefault(app_key(item), []).append(item)
    if not groups:
        raise ValueError("social post pool is empty")
    return groups


def _prioritized_locales(items, locales):
    keys = {
        item.get("app_key")
        for item in items
        if isinstance(item.get("app_key"), str)
        and re.fullmatch(r"[a-z0-9]+", item["app_key"])
    }
    if len(keys) > 1:
        raise ValueError("social App group contains multiple publisher keys")
    app = next(iter(keys), None)
    preferred = tuple(
        dict.fromkeys(
            locale
            for locale in ASC_MARKET_LOCALES.get(app, ())
            if locale in locales
        )
    )
    tail = tuple(locale for locale in locales if locale not in preferred)
    if not preferred:
        return tuple(dict.fromkeys(locales))
    # 平均輪替在這個規模下等於沒有宣傳:41 支 App、每區每天 1 個時段,
    # 一支 App 一年只在該區被挑到約 9 次,平均分給 25 個語言就是「每個
    # 語言每 2.8 年一次」。所以把 ASC 證實有曝光的市場加權,長尾語言
    # 仍留在輪替中(永不排除),只是頻率低。
    cycle = []
    tail_iter = iter(tail)
    exhausted = False
    while not exhausted:
        for locale in preferred:
            cycle.extend([locale] * PREFERRED_LOCALE_WEIGHT)
        for _ in range(len(preferred)):
            nxt = next(tail_iter, None)
            if nxt is None:
                exhausted = True
                break
            cycle.append(nxt)
    return tuple(cycle)


def filter_reachable_pool(pool, validator=None, label="Social", max_workers=8):
    """Drop only confirmed-dead apps so every channel schedules the same live set."""
    validator = validate_url if validator is None else validator
    items = list(pool)
    groups = _app_groups(items)
    live_ids = set()
    urls = {
        app_id: canonical_app_store_url(app_items[0].get("url"))
        for app_id, app_items in groups.items()
    }
    worker_count = max(1, min(max_workers, len(urls)))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:
        futures = {
            app_id: executor.submit(validator, url)
            for app_id, url in urls.items()
        }
        for app_id, url in urls.items():
            if futures[app_id].result():
                live_ids.add(app_id)
            else:
                print(
                    f"{label}: excluding confirmed dead URL ({url})",
                    file=sys.stderr,
                )
    if not live_ids:
        raise RequestError(f"{label}: no live App Store URL remains")
    return [item for item in items if app_key(item) in live_ids]


def _copy_candidates(items, channel, day, app_index, app_count):
    languages = CHANNEL_SPECS[channel]["langs"]
    localized = [item for item in items if item.get("lang") in languages]
    candidates = localized or list(items)
    channel_index = CHANNEL_ORDER.index(channel)
    channel_count = len(CHANNEL_ORDER)
    current_round = (
        day * channel_count + channel_index
    ) // app_count
    current_region = CHANNEL_SPECS[channel]["region"]
    region_channels = REGION_CHANNELS[current_region]
    region_index = region_channels.index(channel)
    region_locales = REGION_LOCALES[current_region]
    regional_rank = 0
    for round_index in range(current_round):
        shift = (
            round_index
            if math.gcd(app_count, channel_count) != 1
            else 0
        )
        position = (app_index - shift) % app_count
        prior_channel = (
            round_index * app_count + position
        ) % channel_count
        prior_region = CHANNEL_SPECS[
            CHANNEL_ORDER[prior_channel]
        ]["region"]
        if prior_region == current_region:
            regional_rank += 1
    launch_phase = day - (
        FULL_LOCALE_SOCIAL_LAUNCH_DATE - BASE_DATE
    ).days
    if 0 <= launch_phase < FULL_LOCALE_SOCIAL_LAUNCH_DAYS:
        target_locale = region_locales[
            (
                len(region_channels) * launch_phase
                + region_index
            )
            % len(region_locales)
        ]
    else:
        locales = _prioritized_locales(items, region_locales)
        target_locale = locales[regional_rank % len(locales)]
    targeted = [item for item in candidates if item.get("lang") == target_locale]
    remaining = [item for item in candidates if item.get("lang") != target_locale]
    cycle = day // app_count
    offset = (
        cycle + app_index + CHANNEL_SPECS[channel]["offset"]
    ) % max(len(remaining), 1)
    return targeted + remaining[offset:] + remaining[:offset]


def rotated_channel_candidates(pool, channel, now=None):
    """Rotate apps fairly, then rotate suitable copy for each selected app."""
    if channel not in CHANNEL_SPECS:
        raise ValueError(f"unknown social channel: {channel}")
    day = day_sequence(now)
    if day < 0:
        raise ValueError(f"social schedule predates {BASE_DATE.isoformat()}")
    groups = _app_groups(pool)
    app_ids = list(groups)
    app_count = len(app_ids)
    start = (day + CHANNEL_ORDER.index(channel)) % app_count
    ordered_ids = app_ids[start:] + app_ids[:start]
    candidates = []
    for app_id in ordered_ids:
        candidates.extend(
            _copy_candidates(
                groups[app_id],
                channel,
                day,
                app_ids.index(app_id),
                app_count,
            )
        )
    return candidates


def channel_candidates(pool, channel, now=None):
    """Select apps fairly before copy, without same-day app duplication."""
    if channel not in CHANNEL_ORDER:
        raise ValueError(f"unknown social channel: {channel}")
    day = day_sequence(now)
    if day < 0:
        raise ValueError(f"social schedule predates {BASE_DATE.isoformat()}")
    groups = _app_groups(pool)
    app_ids = list(groups)
    if len(app_ids) < len(CHANNEL_ORDER):
        raise ScheduleCapacityError(
            f"at least {len(CHANNEL_ORDER)} live apps are required for "
            "unique daily channel picks"
        )
    app_count = len(app_ids)
    channel_count = len(CHANNEL_ORDER)
    selected_by_channel = {
        current: app_ids[
            (
                position
                + (
                    round_index
                    if math.gcd(app_count, channel_count) != 1
                    else 0
                )
            )
            % app_count
        ]
        for index, current in enumerate(CHANNEL_ORDER)
        for round_index, position in (
            divmod(day * channel_count + index, app_count),
        )
    }
    selected_id = selected_by_channel[channel]
    blocked = {
        app_id
        for current, app_id in selected_by_channel.items()
        if current != channel
    }
    selected_index = app_ids.index(selected_id)
    rotated_ids = app_ids[selected_index:] + app_ids[:selected_index]
    safe_ids = [
        app_id
        for app_id in rotated_ids
        if app_id != selected_id and app_id not in blocked
    ]
    fallback_ids = [
        app_id
        for app_id in rotated_ids
        if app_id != selected_id and app_id in blocked
    ]
    candidates = []
    for app_id in [selected_id, *safe_ids, *fallback_ids]:
        candidates.extend(
            _copy_candidates(
                groups[app_id],
                channel,
                day,
                app_ids.index(app_id),
                app_count,
            )
        )
    return candidates


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
