#!/usr/bin/env python3
"""Map the official App Store locales to direct country storefront URLs."""

from __future__ import annotations

import re
import json
import os
from pathlib import Path
import urllib.parse

from official_locales import OFFICIAL_LOCALE_SET


STATE_FILE = ".appstore_storefront_state.json"
PRICE_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
CURRENCY_RE = re.compile(r"[A-Z]{3}")
CAMPAIGN_TOKEN_RE = re.compile(r"[A-Za-z0-9_/]{1,30}")
PROVIDER_TOKEN_RE = re.compile(r"[0-9]{1,20}")
MEDIA_TYPE = "8"
PROVIDER_TOKEN_ENV = "APP_STORE_PROVIDER_TOKEN"
PROMOTIONAL_RATING_MIN_VALUE = 4.0
PROMOTIONAL_RATING_MIN_COUNT = 2
LOCALE_STOREFRONTS = {
    "ar-SA": "sa",
    "bn-BD": "bd",
    "ca": "es",
    "cs": "cz",
    "da": "dk",
    "de-DE": "de",
    "el": "gr",
    "en-AU": "au",
    "en-CA": "ca",
    "en-GB": "gb",
    "en-US": "us",
    "es-ES": "es",
    "es-MX": "mx",
    "fi": "fi",
    "fr-CA": "ca",
    "fr-FR": "fr",
    "gu-IN": "in",
    "he": "il",
    "hi": "in",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "it": "it",
    "ja": "jp",
    "kn-IN": "in",
    "ko": "kr",
    "ml-IN": "in",
    "mr-IN": "in",
    "ms": "my",
    "nl-NL": "nl",
    "no": "no",
    "or-IN": "in",
    "pa-IN": "in",
    "pl": "pl",
    "pt-BR": "br",
    "pt-PT": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl-SI": "si",
    "sv": "se",
    "ta-IN": "in",
    "te-IN": "in",
    "th": "th",
    "tr": "tr",
    "uk": "ua",
    "ur-PK": "pk",
    "vi": "vn",
    "zh-Hans": "cn",
    "zh-Hant": "tw",
}
FREE_LABELS = {
    "ar-SA": "مجاني",
    "bn-BD": "বিনামূল্যে",
    "ca": "Gratis",
    "cs": "Zdarma",
    "da": "Gratis",
    "de-DE": "Kostenlos",
    "el": "Δωρεάν",
    "en-AU": "Free",
    "en-CA": "Free",
    "en-GB": "Free",
    "en-US": "Free",
    "es-ES": "Gratis",
    "es-MX": "Gratis",
    "fi": "Ilmainen",
    "fr-CA": "Gratuit",
    "fr-FR": "Gratuit",
    "gu-IN": "મફત",
    "he": "בחינם",
    "hi": "मुफ़्त",
    "hr": "Besplatno",
    "hu": "Ingyenes",
    "id": "Gratis",
    "it": "Gratis",
    "ja": "無料",
    "kn-IN": "ಉಚಿತ",
    "ko": "무료",
    "ml-IN": "സൗജന്യം",
    "mr-IN": "मोफत",
    "ms": "Percuma",
    "nl-NL": "Gratis",
    "no": "Gratis",
    "or-IN": "ମାଗଣା",
    "pa-IN": "ਮੁਫ਼ਤ",
    "pl": "Bezpłatnie",
    "pt-BR": "Grátis",
    "pt-PT": "Grátis",
    "ro": "Gratuit",
    "ru": "Бесплатно",
    "sk": "Zadarmo",
    "sl-SI": "Brezplačno",
    "sv": "Gratis",
    "ta-IN": "இலவசம்",
    "te-IN": "ఉచితం",
    "th": "ฟรี",
    "tr": "Ücretsiz",
    "uk": "Безкоштовно",
    "ur-PK": "مفت",
    "vi": "Miễn phí",
    "zh-Hans": "免费",
    "zh-Hant": "免費",
}
APP_STORE_URL_RE = re.compile(
    r"https://apps\.apple\.com/app/id(?P<app_id>\d{9,12})"
)
APP_STORE_PATH_RE = re.compile(
    r"/(?:(?P<country>[a-z]{2})/)?app/id(?P<app_id>\d{9,12})"
)

if set(LOCALE_STOREFRONTS) != OFFICIAL_LOCALE_SET:
    raise RuntimeError("App Store storefront mapping must cover 50 official locales")
if set(FREE_LABELS) != OFFICIAL_LOCALE_SET:
    raise RuntimeError("Free labels must cover 50 official locales")


def localized_app_store_url(value: str, locale: str) -> str:
    """Return a direct App Store URL without wrappers or tracking parameters."""
    if locale not in LOCALE_STOREFRONTS:
        raise ValueError(f"Unsupported App Store locale: {locale!r}")
    if not isinstance(value, str):
        raise ValueError("App Store URL must be a string")
    match = APP_STORE_URL_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid canonical App Store URL: {value!r}")
    country = LOCALE_STOREFRONTS[locale]
    return (
        f"https://apps.apple.com/{country}/app/"
        f"id{match.group('app_id')}"
    )


def validated_app_store_url(
    value: str,
    expected_app_id: str | None = None,
) -> str:
    """Validate a clean Apple URL or a complete Apple campaign URL."""
    if not isinstance(value, str):
        raise ValueError("App Store URL must be a string")
    parsed = urllib.parse.urlsplit(value.strip())
    path = APP_STORE_PATH_RE.fullmatch(parsed.path)
    country = path.group("country") if path else None
    if (
        parsed.scheme != "https"
        or parsed.netloc != "apps.apple.com"
        or path is None
        or parsed.fragment
        or (
            country is not None
            and country not in set(LOCALE_STOREFRONTS.values())
        )
        or (
            expected_app_id is not None
            and path.group("app_id") != expected_app_id
        )
    ):
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    try:
        parameters = urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as error:
        raise ValueError(f"Invalid direct App Store URL: {value!r}") from error
    if not parameters:
        return urllib.parse.urlunsplit(parsed._replace(query=""))
    if (
        [key for key, _ in parameters] != ["pt", "ct", "mt"]
        or PROVIDER_TOKEN_RE.fullmatch(parameters[0][1]) is None
        or CAMPAIGN_TOKEN_RE.fullmatch(parameters[1][1]) is None
        or parameters[2][1] != MEDIA_TYPE
    ):
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    return urllib.parse.urlunsplit(
        parsed._replace(query=urllib.parse.urlencode(parameters))
    )


def _provider_token(value: str | None) -> str | None:
    token = (
        os.environ.get(PROVIDER_TOKEN_ENV, "").strip()
        if value is None
        else value.strip()
    )
    if not token:
        return None
    if PROVIDER_TOKEN_RE.fullmatch(token) is None:
        raise ValueError(f"Invalid App Store provider token: {token!r}")
    return token


def normalize_app_store_campaign_url(
    value: str,
    *,
    provider_token: str | None = None,
) -> str:
    """Remove partial campaign parameters or complete them with a real token."""
    if not isinstance(value, str):
        raise ValueError("App Store URL must be a string")
    parsed = urllib.parse.urlsplit(value.strip())
    direct = urllib.parse.urlunsplit(parsed._replace(query="", fragment=""))
    validated_app_store_url(direct)
    try:
        parameters = urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as error:
        raise ValueError(f"Invalid direct App Store URL: {value!r}") from error
    if not parameters:
        return direct
    if any(key not in {"pt", "ct", "mt"} for key, _ in parameters):
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    values: dict[str, str] = {}
    for key, parameter_value in parameters:
        if key in values:
            raise ValueError(f"Invalid direct App Store URL: {value!r}")
        values[key] = parameter_value
    campaign = values.get("ct", "")
    if values.get("mt") not in {None, MEDIA_TYPE}:
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    selected_provider = (
        provider_token if provider_token is not None else values.get("pt")
    )
    token = _provider_token(selected_provider)
    if not token or not campaign:
        return direct
    if CAMPAIGN_TOKEN_RE.fullmatch(campaign) is None:
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    return urllib.parse.urlunsplit(
        parsed._replace(
            query=urllib.parse.urlencode(
                (("pt", token), ("ct", campaign), ("mt", MEDIA_TYPE))
            ),
            fragment="",
        )
    )


def campaign_app_store_url(
    value: str,
    campaign_token: str,
    *,
    provider_token: str | None = None,
) -> str:
    """Add ct= campaign token to a direct App Store URL; pt= added when available."""
    parsed = urllib.parse.urlsplit(value.strip())
    direct = urllib.parse.urlunsplit(parsed._replace(query="", fragment=""))
    validated_app_store_url(direct)
    if CAMPAIGN_TOKEN_RE.fullmatch(campaign_token) is None:
        raise ValueError(f"Invalid App Store campaign token: {campaign_token!r}")
    existing_parameters = urllib.parse.parse_qs(parsed.query)
    providers = existing_parameters.get("pt", [])
    if len(providers) > 1:
        raise ValueError(f"Duplicate App Store provider token: {value!r}")
    token = _provider_token(
        provider_token if provider_token is not None else providers[0] if providers else None
    )
    params: list[tuple[str, str]] = []
    if token is not None:
        params.append(("pt", token))
    params.append(("ct", campaign_token))
    return urllib.parse.urlunsplit(
        parsed._replace(
            query=urllib.parse.urlencode(params),
            fragment="",
        )
    )


def has_trusted_promotional_rating(detail: dict[str, object]) -> bool:
    """Return whether a rating is strong enough to feature as social proof."""
    rating_value = detail.get("rating_value")
    rating_count = detail.get("rating_count")
    return (
        isinstance(rating_value, (int, float))
        and not isinstance(rating_value, bool)
        and float(rating_value) >= PROMOTIONAL_RATING_MIN_VALUE
        and isinstance(rating_count, int)
        and not isinstance(rating_count, bool)
        and rating_count >= PROMOTIONAL_RATING_MIN_COUNT
    )


def load_storefront_availability(pages_dir) -> dict[str, frozenset[str]]:
    """Read the last public Apple lookup snapshot."""
    path = Path(pages_dir) / STATE_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}
    countries = payload.get("countries")
    if not isinstance(countries, dict):
        return {}
    return {
        country: frozenset(
            str(app_id)
            for app_id in app_ids
            if str(app_id).isdigit()
        )
        for country, app_ids in countries.items()
        if country in set(LOCALE_STOREFRONTS.values())
        and isinstance(app_ids, list)
    }


def load_storefront_details(
    pages_dir,
) -> dict[str, dict[str, dict[str, object]]]:
    """Read validated public price and rating facts from the Apple snapshot."""
    path = Path(pages_dir) / STATE_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}
    details = payload.get("details")
    if not isinstance(details, dict):
        return {}
    result: dict[str, dict[str, dict[str, object]]] = {}
    for country, app_details in details.items():
        if (
            country not in set(LOCALE_STOREFRONTS.values())
            or not isinstance(app_details, dict)
        ):
            continue
        valid: dict[str, dict[str, object]] = {}
        for app_id, detail in app_details.items():
            if not str(app_id).isdigit() or not isinstance(detail, dict):
                continue
            price = detail.get("price")
            currency = detail.get("currency")
            formatted_price = detail.get("formatted_price")
            if (
                not isinstance(price, str)
                or PRICE_RE.fullmatch(price) is None
                or not isinstance(currency, str)
                or CURRENCY_RE.fullmatch(currency) is None
                or not isinstance(formatted_price, str)
                or not formatted_price.strip()
                or len(formatted_price) > 64
            ):
                continue
            record: dict[str, object] = {
                "price": price,
                "currency": currency,
                "formatted_price": formatted_price.strip(),
            }
            rating_value = detail.get("rating_value")
            rating_count = detail.get("rating_count")
            if (
                isinstance(rating_value, (int, float))
                and not isinstance(rating_value, bool)
                and 0 <= float(rating_value) <= 5
                and isinstance(rating_count, int)
                and not isinstance(rating_count, bool)
                and rating_count > 0
            ):
                record["rating_value"] = float(rating_value)
                record["rating_count"] = rating_count
            valid[str(app_id)] = record
        result[country] = valid
    return result


def localized_storefront_detail(
    detail: dict[str, object],
    locale: str,
) -> dict[str, object]:
    """Use native copy for zero-price listings without altering Apple amounts."""
    if locale not in OFFICIAL_LOCALE_SET:
        raise ValueError(f"Unsupported App Store locale: {locale!r}")
    localized = dict(detail)
    if localized.get("price") == "0":
        localized["formatted_price"] = FREE_LABELS[locale]
    return localized


def verified_app_store_url(
    value: str,
    locale: str,
    availability: dict[str, frozenset[str]],
) -> str:
    """Use a country URL only when Apple verified that exact storefront."""
    localized = localized_app_store_url(value, locale)
    app_id = APP_STORE_URL_RE.fullmatch(value.strip()).group("app_id")
    country = LOCALE_STOREFRONTS[locale]
    if app_id in availability.get(country, frozenset()):
        return localized
    return value.strip()

