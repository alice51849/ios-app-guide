#!/usr/bin/env python3
"""Map the official App Store locales to direct country storefront URLs."""

from __future__ import annotations

import re
import json
from pathlib import Path

from official_locales import OFFICIAL_LOCALE_SET


STATE_FILE = ".appstore_storefront_state.json"
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
APP_STORE_URL_RE = re.compile(
    r"https://apps\.apple\.com/app/id(?P<app_id>\d{9,12})"
)

if set(LOCALE_STOREFRONTS) != OFFICIAL_LOCALE_SET:
    raise RuntimeError("App Store storefront mapping must cover 50 official locales")


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
