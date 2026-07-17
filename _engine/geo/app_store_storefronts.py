#!/usr/bin/env python3
"""Map the official App Store locales to direct country storefront URLs."""

from __future__ import annotations

import re

from official_locales import OFFICIAL_LOCALE_SET


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
