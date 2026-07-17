#!/usr/bin/env python3
"""App Store Connect locales required by the portfolio localization standard."""

OFFICIAL_LOCALES = (
    "ar-SA",
    "bn-BD",
    "ca",
    "cs",
    "da",
    "de-DE",
    "el",
    "en-AU",
    "en-CA",
    "en-GB",
    "en-US",
    "es-ES",
    "es-MX",
    "fi",
    "fr-CA",
    "fr-FR",
    "gu-IN",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "it",
    "ja",
    "kn-IN",
    "ko",
    "ml-IN",
    "mr-IN",
    "ms",
    "nl-NL",
    "no",
    "or-IN",
    "pa-IN",
    "pl",
    "pt-BR",
    "pt-PT",
    "ro",
    "ru",
    "sk",
    "sl-SI",
    "sv",
    "ta-IN",
    "te-IN",
    "th",
    "tr",
    "uk",
    "ur-PK",
    "vi",
    "zh-Hans",
    "zh-Hant",
)
OFFICIAL_LOCALE_SET = frozenset(OFFICIAL_LOCALES)


def require_official_locale_coverage(key, locales):
    """Reject partial or noncanonical locale sets before public generation."""
    actual = set(locales)
    missing = sorted(OFFICIAL_LOCALE_SET - actual)
    unexpected = sorted(actual - OFFICIAL_LOCALE_SET)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unexpected:
            details.append(f"unexpected={','.join(unexpected)}")
        raise ValueError(f"{key} must have exactly 50 official locales: {'; '.join(details)}")

