#!/usr/bin/env python3
"""Standard.site App Store direct-link attribution contract."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping
from urllib.parse import parse_qsl, urlsplit, urlunsplit


PROVIDER_TOKEN = "118326163"
CAMPAIGN_TOKEN = "standard_site"
MEDIA_TYPE = "8"
MAX_CAMPAIGN_TOKEN_LENGTH = 30
PRIMARY_QUERY = (
    f"pt={PROVIDER_TOKEN}&ct={CAMPAIGN_TOKEN}&mt={MEDIA_TYPE}"
)
LEGACY_BARE_URL = "bare_url"
LEGACY_ABSENT_URL = "absent"

_BIDI_CONTROLS = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
_DIRECT_URL_RE = re.compile(
    rf"(?<![A-Za-z0-9%=&])"
    rf"https://apps\.apple\.com/"
    rf"[^\s<>'\"\[\]{{}}(){_BIDI_CONTROLS}]+"
)
_TRAILING_PROSE = ".,;:!?"
_APP_ID_RE = re.compile(r"id([0-9]+)")
_STOREFRONT_RE = re.compile(r"[a-z]{2}")
_MANAGED_DOCUMENT_FIELDS = (
    "canonical_url",
    "path",
    "title",
    "description",
    "text_content",
    "tags",
)


class AttributionError(ValueError):
    """A Standard.site primary App Store link violates the contract."""


@dataclass(frozen=True)
class AppStoreURL:
    value: str
    start: int
    end: int
    app_id: str
    storefront: str | None
    base_url: str
    query: str


def _parse_app_store_url(
    value: str,
    *,
    start: int = 0,
    end: int | None = None,
) -> AppStoreURL:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise AttributionError(f"Invalid App Store URL: {value!r}") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != "apps.apple.com"
        or parsed.netloc != "apps.apple.com"
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise AttributionError(f"Invalid App Store URL: {value!r}")

    segments = parsed.path.strip("/").split("/")
    storefront: str | None
    if segments and segments[0] == "app":
        storefront = None
        app_segments = segments[1:]
    elif (
        len(segments) >= 2
        and _STOREFRONT_RE.fullmatch(segments[0])
        and segments[1] == "app"
    ):
        storefront = segments[0]
        app_segments = segments[2:]
    else:
        raise AttributionError(f"Invalid App Store route: {value!r}")
    if not app_segments:
        raise AttributionError(f"App Store route has no App ID: {value!r}")
    match = _APP_ID_RE.fullmatch(app_segments[-1])
    if match is None:
        raise AttributionError(f"App Store route has no App ID: {value!r}")

    base_url = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, "", "")
    )
    return AppStoreURL(
        value=value,
        start=start,
        end=len(value) if end is None else end,
        app_id=match.group(1),
        storefront=storefront,
        base_url=base_url,
        query=parsed.query,
    )


def direct_app_store_urls(text: str) -> list[AppStoreURL]:
    """Return direct App Store URLs, excluding encoded/card-wrapper targets."""
    results: list[AppStoreURL] = []
    for match in _DIRECT_URL_RE.finditer(text):
        value = match.group(0).rstrip(_TRAILING_PROSE)
        end = match.start() + len(value)
        results.append(
            _parse_app_store_url(value, start=match.start(), end=end)
        )
    return results


def attributed_app_store_url(route: str) -> str:
    parsed = _parse_app_store_url(route)
    if parsed.query not in {"", PRIMARY_QUERY}:
        raise AttributionError(
            "Primary App Store route has unexpected query parameters"
        )
    return f"{parsed.base_url}?{PRIMARY_QUERY}"


def ensure_primary_app_store_url(
    text: str,
    *,
    app_id: str,
    fallback_route: str,
) -> tuple[str, str, str]:
    """Preserve an existing CTA/route while enforcing one attributed URL."""
    urls = direct_app_store_urls(text)
    if len(urls) > 1:
        raise AttributionError(
            "Standard.site text must contain one primary App Store direct URL"
        )
    if urls:
        current = urls[0]
        if current.app_id != str(app_id):
            raise AttributionError(
                "Primary App Store URL targets the wrong App ID"
            )
        if current.query not in {"", PRIMARY_QUERY}:
            raise AttributionError(
                "Primary App Store URL has unexpected query parameters"
            )
        primary = attributed_app_store_url(current.base_url)
        text = text[: current.start] + primary + text[current.end :]
        legacy_mode = LEGACY_BARE_URL
    else:
        fallback = _parse_app_store_url(fallback_route)
        if fallback.app_id != str(app_id):
            raise AttributionError(
                "Fallback App Store route targets the wrong App ID"
            )
        primary = attributed_app_store_url(fallback.base_url)
        text = f"{text.rstrip()}\n\nApp Store\n\n{primary}"
        legacy_mode = LEGACY_ABSENT_URL
    validate_primary_app_store_url(
        text,
        app_id=str(app_id),
        expected_url=primary,
    )
    return text, primary, legacy_mode


def validate_primary_app_store_url(
    text: str,
    *,
    app_id: str,
    expected_url: str | None = None,
) -> str:
    urls = direct_app_store_urls(text)
    if len(urls) != 1:
        raise AttributionError(
            "Standard.site text must contain exactly one App Store direct URL"
        )
    primary = urls[0]
    if primary.app_id != str(app_id):
        raise AttributionError(
            "Primary App Store URL targets the wrong App ID"
        )
    if primary.query != PRIMARY_QUERY:
        raise AttributionError(
            "Primary App Store URL must keep the exact pt/ct/mt contract"
        )
    if len(CAMPAIGN_TOKEN) > MAX_CAMPAIGN_TOKEN_LENGTH:
        raise AttributionError("Standard.site campaign token is too long")
    if expected_url is not None and primary.value != expected_url:
        raise AttributionError(
            "Primary App Store URL does not match the manifest contract"
        )
    return primary.value


def legacy_text_content(
    text: str,
    *,
    app_id: str,
    mode: str = LEGACY_BARE_URL,
) -> str:
    """Reconstruct the pre-attribution body for immutable published records."""
    urls = direct_app_store_urls(text)
    if len(urls) != 1:
        raise AttributionError(
            "Cannot derive legacy text without one primary App Store URL"
        )
    primary = urls[0]
    if primary.app_id != str(app_id) or primary.query != PRIMARY_QUERY:
        raise AttributionError(
            "Cannot derive legacy text from a non-primary App Store URL"
        )
    if mode == LEGACY_BARE_URL:
        return text[: primary.start] + primary.base_url + text[primary.end :]
    if mode == LEGACY_ABSENT_URL:
        suffix = f"\n\nApp Store\n\n{primary.value}"
        if not text.endswith(suffix):
            raise AttributionError(
                "Appended primary App Store URL is not the final CTA"
            )
        return text[: -len(suffix)]
    raise AttributionError(f"Unsupported legacy App Store mode: {mode}")


def document_content_hash(document: Mapping[str, object]) -> str:
    managed = {
        key: document[key]
        for key in _MANAGED_DOCUMENT_FIELDS
    }
    encoded = json.dumps(
        managed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def legacy_document_content_hash(document: Mapping[str, object]) -> str:
    legacy = dict(document)
    legacy["text_content"] = legacy_text_content(
        str(document["text_content"]),
        app_id=str(document["app_store_id"]),
        mode=str(document["legacy_app_store_link"]),
    )
    return document_content_hash(legacy)


def attribution_status(
    document: Mapping[str, object],
    published_hash: object,
) -> str:
    value = str(published_hash or "")
    if value == str(document["content_hash"]):
        return "attributed"
    if value == legacy_document_content_hash(document):
        return "legacy_unattributed"
    return "stale"


def text_content_for_status(
    document: Mapping[str, object],
    status: str,
) -> str:
    if status == "attributed":
        return str(document["text_content"])
    if status == "legacy_unattributed":
        return legacy_text_content(
            str(document["text_content"]),
            app_id=str(document["app_store_id"]),
            mode=str(document["legacy_app_store_link"]),
        )
    raise AttributionError(f"Unsupported attribution status: {status}")


def redirect_preserves_attribution(source_url: str, final_url: str) -> bool:
    """Allow Apple's canonical redirect to omit only the legacy ``mt`` key."""
    try:
        source = _parse_app_store_url(source_url)
        final = _parse_app_store_url(final_url)
    except AttributionError:
        return False
    if (
        source.query != PRIMARY_QUERY
        or source.app_id != final.app_id
        or (
            source.storefront is not None
            and source.storefront != final.storefront
        )
    ):
        return False
    pairs = parse_qsl(final.query, keep_blank_values=True)
    if len({key for key, _ in pairs}) != len(pairs):
        return False
    parameters = dict(pairs)
    return (
        parameters.get("pt") == PROVIDER_TOKEN
        and parameters.get("ct") == CAMPAIGN_TOKEN
        and parameters.get("mt") in {None, MEDIA_TYPE}
    )
