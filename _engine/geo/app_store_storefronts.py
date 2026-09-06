#!/usr/bin/env python3
"""Shared App Store storefront, identity and campaign-link contracts."""

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
# Two spellings exist in the wild (provider_token.py writes the first,
# older shell tooling wrote the second); read both, write only the first.
PROVIDER_TOKEN_FILES = (
    Path.home() / ".growth-private" / "app-store-provider-token",
    Path.home() / ".growth-private" / "app_store_provider_token",
)
PROMOTIONAL_RATING_MIN_VALUE = 4.0
PROMOTIONAL_RATING_MIN_COUNT = 2
LOCALE_STOREFRONTS = {
    "ar-SA": "sa",
    # Bengali readers are served by the India storefront. Apple has no "bd"
    # storefront at all -- apps.apple.com/bd/... 301s to /us, and an iTunes
    # lookup with country=bd returns 0 results for *every* app, including
    # Facebook and WhatsApp. Pointing bn-BD at "bd" silently redirected all
    # Bengali store links to the US store, where the apps are not purchasable.
    # See NON_STOREFRONTS below for the guard that keeps this from recurring.
    "bn-BD": "in",
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
APP_STORE_DEVELOPER_PATH_RE = re.compile(
    r"/(?:(?P<country>[a-z]{2})/)?developer/"
    r"(?:[-A-Za-z0-9._~%]+/)?id[0-9]{1,20}"
)

# Two-letter codes that look like plausible storefronts but are not ones Apple
# operates. A locale mapped here produces links that 301 to /us, sending readers
# to a storefront where the app is usually not for sale -- a silent failure, so
# it is rejected at import time instead. Verified with a control app that ships
# in every real storefront (Facebook, id284882215): a storefront is real if the
# control app resolves there. Re-check with ``verify_storefronts_live()``.
NON_STOREFRONTS = frozenset({"bd"})

if set(LOCALE_STOREFRONTS) != OFFICIAL_LOCALE_SET:
    raise RuntimeError("App Store storefront mapping must cover 50 official locales")
_dead = {
    locale: country
    for locale, country in LOCALE_STOREFRONTS.items()
    if country in NON_STOREFRONTS
}
if _dead:
    raise RuntimeError(
        "App Store storefront mapping points at storefronts Apple does not "
        f"operate: {_dead}. Links to these 301 to /us. Map the locale to the "
        "storefront that actually serves those readers."
    )
del _dead
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


def is_clean_app_store_developer_url(value: str) -> bool:
    """A developer profile is a publisher identity, never an app download CTA."""
    if not isinstance(value, str):
        return False
    parsed = urllib.parse.urlsplit(value)
    match = APP_STORE_DEVELOPER_PATH_RE.fullmatch(parsed.path)
    return bool(
        parsed.scheme == "https" and parsed.netloc == "apps.apple.com"
        and not parsed.query and not parsed.fragment and match
        and (
            match.group("country") is None
            or match.group("country") in LOCALE_STOREFRONTS.values()
        )
    )


def storefront_locale_for_url(value: str, locale: str | None) -> str | None:
    """Supplemental web languages may use global links, never guessed countries."""
    if locale is None or locale in LOCALE_STOREFRONTS:
        return locale
    parsed = urllib.parse.urlsplit(value)
    match = APP_STORE_PATH_RE.fullmatch(parsed.path)
    if match is None:
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    if match["country"] is not None:
        raise ValueError(f"Unsupported App Store locale: {locale!r}")
    return None


def validated_app_store_url(
    value: str,
    expected_app_id: str | None = None,
    *,
    expected_locale: str | None = None,
    require_campaign: bool = False,
    provider_token: str | None = None,
    availability: dict[str, frozenset[str]] | None = None,
) -> str:
    """Validate a clean Apple URL or a complete Apple campaign URL."""
    if not isinstance(value, str):
        raise ValueError("App Store URL must be a string")
    if re.search(r"[\x00-\x20\x7f]", value.strip()):
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    if expected_locale is not None and expected_locale not in LOCALE_STOREFRONTS:
        raise ValueError(f"Unsupported App Store locale: {expected_locale!r}")
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
    if country is not None:
        if expected_locale is not None and country != LOCALE_STOREFRONTS[expected_locale]:
            raise ValueError(
                f"App Store storefront mismatch for {expected_locale}: {value!r}"
            )
        if availability is not None and path.group("app_id") not in availability.get(
            country, frozenset()
        ):
            raise ValueError(f"Unverified App Store storefront: {value!r}")
    try:
        parameters = urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as error:
        raise ValueError(f"Invalid direct App Store URL: {value!r}") from error
    if not parameters:
        if require_campaign:
            raise ValueError(f"Missing App Store campaign attribution: {value!r}")
        return urllib.parse.urlunsplit(parsed._replace(query=""))
    if (
        [key for key, _ in parameters] != ["pt", "ct", "mt"]
        or PROVIDER_TOKEN_RE.fullmatch(parameters[0][1]) is None
        or CAMPAIGN_TOKEN_RE.fullmatch(parameters[1][1]) is None
        or parameters[2][1] != MEDIA_TYPE
    ):
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    if provider_token is not None and parameters[0][1] != _provider_token(provider_token):
        raise ValueError(f"App Store provider token mismatch: {value!r}")
    return urllib.parse.urlunsplit(
        parsed._replace(query=urllib.parse.urlencode(parameters))
    )


def resolve_provider_token() -> str:
    """Apple's account-wide campaign-link provider token (``pt``), opt-in.

    The environment always wins, *including when it is deliberately set to an
    empty string* — that is how tests and one-off runs turn attribution off.
    Only when the variable is entirely absent do we fall back to the private
    token file, so a hand-run pipeline in a non-login shell still produces
    attributable links.

    Deliberately NOT used by ``_provider_token`` below: the shared helpers stay
    strictly environment-driven so that generator unit tests remain hermetic on
    a machine that has the real token on disk. Publication entry points opt in
    and export the resolved value before running any generators.
    """
    env = os.environ.get(PROVIDER_TOKEN_ENV)
    if env is not None:
        return env.strip()
    for name in PROVIDER_TOKEN_FILES:
        try:
            value = name.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return ""


def _provider_token(value: str | None) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError("App Store provider token must be a string")
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
    """Use a complete Apple campaign URL only when a provider token exists."""
    parsed = urllib.parse.urlsplit(value.strip())
    direct = urllib.parse.urlunsplit(parsed._replace(query="", fragment=""))
    validated_app_store_url(direct)
    existing_parameters = urllib.parse.parse_qs(parsed.query)
    providers = existing_parameters.get("pt", [])
    if len(providers) > 1:
        raise ValueError(f"Duplicate App Store provider token: {value!r}")
    token = _provider_token(
        provider_token if provider_token is not None else providers[0] if providers else None
    )
    if token is None:
        return direct
    if CAMPAIGN_TOKEN_RE.fullmatch(campaign_token) is None:
        raise ValueError(f"Invalid App Store campaign token: {campaign_token!r}")
    return urllib.parse.urlunsplit(
        parsed._replace(
            query=urllib.parse.urlencode(
                (("pt", token), ("ct", campaign_token), ("mt", MEDIA_TYPE))
            ),
            fragment="",
        )
    )


def required_campaign_app_store_url(
    value: str,
    campaign_token: str,
    *,
    provider_token: str | None = None,
    expected_locale: str | None = None,
    expected_app_id: str | None = None,
    availability: dict[str, frozenset[str]] | None = None,
) -> str:
    """Build a publishable CTA; missing attribution and wrong storefronts block."""
    if not isinstance(value, str) or urllib.parse.urlsplit(value).fragment:
        raise ValueError(f"Invalid direct App Store URL: {value!r}")
    # Validate the input before retargeting it: silently dropping unknown or
    # duplicate query parameters hides broken generator contracts.
    normalized = normalize_app_store_campaign_url(value, provider_token=provider_token)
    validated_app_store_url(
        normalized,
        expected_app_id,
        expected_locale=expected_locale,
        availability=availability,
    )
    result = campaign_app_store_url(
        normalized, campaign_token, provider_token=provider_token
    )
    return validated_app_store_url(
        result,
        expected_app_id,
        expected_locale=expected_locale,
        require_campaign=True,
        provider_token=provider_token,
        availability=availability,
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


# Facebook. Ships in every storefront Apple operates, so it separates "this
# storefront does not exist" from "our app is not sold there" -- a distinction
# that is invisible when you only probe your own catalogue.
STOREFRONT_CONTROL_APP_ID = "284882215"


def verify_storefronts_live(control_app_id: str = STOREFRONT_CONTROL_APP_ID):
    """Return the storefront codes in LOCALE_STOREFRONTS Apple does not operate.

    Network call, so this is a maintenance helper rather than an import-time
    check; NON_STOREFRONTS carries the result. Run it when adding a locale.
    """
    import json
    import time
    import urllib.request

    dead = []
    for country in sorted(set(LOCALE_STOREFRONTS.values())):
        url = (
            "https://itunes.apple.com/lookup"
            f"?id={control_app_id}&country={country}"
        )
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = json.load(response)
        except Exception:  # network flake -- inconclusive, not a failure
            continue
        if not payload.get("resultCount"):
            dead.append(country)
        time.sleep(0.25)
    return dead
