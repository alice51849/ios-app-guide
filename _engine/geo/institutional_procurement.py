#!/usr/bin/env python3
"""Generate a fail-closed institutional iOS procurement release candidate."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable
import unicodedata
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

from aeo_answers_i18n import NATIVE_SCRIPT_RANGES
from official_locales import (
    OFFICIAL_LOCALES,
    open_graph_locale,
    require_official_locale_coverage,
)
import publisher_intent_catalog


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE.parents[1]))
SITE = os.environ.get(
    "GEO_SITE",
    "https://alice51849.github.io/ios-app-guide",
).rstrip("/")
MANIFEST_PATH = HERE / "institutional_procurement_manifest.json"
I18N_PATH = HERE / "institutional_procurement_i18n.json"
ROOT_DIR = Path("institutional")
APP_DIR = ROOT_DIR / "apps"
PAGE_NAME = "ios-procurement.html"
DATA_NAME = "apple-managed-apps.json"
SCHEMA_NAME = "apple-managed-apps.schema.json"
SCORECARD_SCHEMA_NAME = "institutional-scorecard.schema.json"
SCORECARD_NAMES = {7: "scorecard-7d.json", 28: "scorecard-28d.json"}
STATE_NAME = "generation-state.json"
SITEMAP_NAME = "sitemap_institutional_procurement.xml"
STATE_PATH = ROOT_DIR / STATE_NAME
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XHTML_NS = "http://www.w3.org/1999/xhtml"
DEEP_WORKFLOW_LOCALES = {
    "en-AU",
    "en-CA",
    "en-GB",
    "en-US",
    "ja",
    "zh-Hant",
}
RTL_LOCALES = {"ar-SA", "he", "ur-PK"}
SOURCE_FIELDS = {
    "title",
    "intro",
    "paid",
    "direct",
    "iap",
    "fit",
    "disclosure",
    "measurement",
    "steps",
    "labels",
}
LABEL_FIELDS = {
    "roster",
    "platform",
    "purpose",
    "limits",
    "support",
    "privacy",
    "source",
    "last_checked",
    "copy",
    "copied",
    "school",
    "business",
    "not_shortlisted",
}
SOURCE_TOKEN_RE = re.compile(
    r"(?i)\b(?:Apple|Microsoft|Intune|App|Store|School|Business|Manager|"
    r"iOS|MDM|GET|PENDING|IAP|ID|URL|Lumi|Studio)\b"
)
EMAIL_RE = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
OLD_EMAIL = "alice51849@hotmail.com"
ALLOWED_EMAIL = "hourstag.app@gmail.com"
ID_RE = re.compile(r"\d{9,12}")
BUNDLE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]+")
CAMPAIGN_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{1,30}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
APPLE_LOOKUP_SELLER_NAME = "Guan Feng Lai"
REQUIRED_PROHIBITED_CLAIM_FRAGMENTS = {
    "apple certified",
    "apple-approved",
    "education certified",
    "mdm certified",
    "available in apple school manager",
    "available in apple business manager",
    "school approved",
    "institution approved",
    "volume discount",
    "institutional discount",
}
REQUIRED_INDEPENDENT_SOURCE_KEYS = {
    "apple_lookup_receipt",
    "owner_support_registry",
    "portfolio_receipt",
}
REQUIRED_OFFICIAL_REFERENCE_PINS = {
    "apple-content-distribution": {
        "publisher": "Apple",
        "url": (
            "https://support.apple.com/guide/deployment/"
            "intro-to-content-distribution-depe1553f932/web"
        ),
        "supports": (
            "Apple School Manager or Apple Business Manager can acquire "
            "eligible paid and free App Store apps through Apps and Books.",
            "Apps can be assigned to devices or users through device management.",
            "In-app purchases and subscriptions are not compatible with volume "
            "purchasing, managed apps, or Managed Apple Accounts.",
        ),
    },
    "apple-managed-apps": {
        "publisher": "Apple",
        "url": (
            "https://support.apple.com/guide/deployment/"
            "distribute-managed-apps-dep575bfed86/web"
        ),
        "supports": (
            "A device management service must assign a device-based or "
            "user-based licence before installing an Apps and Books app.",
            "Managed apps can be required or optional, and supervised devices "
            "can install them silently.",
        ),
    },
    "microsoft-intune-direct-store": {
        "publisher": "Microsoft",
        "url": (
            "https://learn.microsoft.com/en-us/intune/app-management/"
            "deployment/add-store-ios"
        ),
        "supports": (
            "The direct iOS Store app method can assign only apps that are "
            "free of charge in the App Store.",
            "Paid apps should use Apple's volume-purchase path.",
        ),
    },
    "microsoft-intune-volume-purchase": {
        "publisher": "Microsoft",
        "url": (
            "https://learn.microsoft.com/en-us/intune/app-management/"
            "deployment/manage-vpp-apple"
        ),
        "supports": (
            "Intune synchronises Apps and Books location tokens from Apple "
            "Business Manager or Apple School Manager.",
            "Apple Business Manager can acquire both free and paid App Store "
            "apps for managed distribution.",
            "Device-licensed apps are installed and updated through the MDM "
            "channel.",
        ),
    },
}
ENGLISH_FALLBACK_WORD_RE = re.compile(
    r"(?i)\b(?:best|useful|should|before|without|with|for|and|the|is|"
    r"built|free|start|one-time|unlock|subscription|track|where|money|"
    r"saving|hours|work|client|document|household|maintenance|reading|"
    r"listening|trainer|purchase|complete|workflow)\b"
)


class BlockedNotDeployable(RuntimeError):
    """Raised when a release candidate fails a blocking publication gate."""


def _today() -> date:
    return date.today()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BlockedNotDeployable(f"Unreadable JSON source: {path}") from error
    if not isinstance(payload, dict):
        raise BlockedNotDeployable(f"JSON source must be an object: {path}")
    return payload


def _load_manifest(pages: Path) -> dict[str, Any]:
    manifest = _read_json(MANIFEST_PATH)
    if manifest.get("schema_version") != 1:
        raise BlockedNotDeployable("Unsupported procurement manifest version")
    if manifest.get("release_status") != "CANDIDATE_NOT_DEPLOYED":
        raise BlockedNotDeployable("Candidate must remain explicitly not deployed")
    if manifest.get("apple_lookup_seller_name") != APPLE_LOOKUP_SELLER_NAME:
        raise BlockedNotDeployable("Apple Lookup seller identity pin differs")
    source_files = manifest.get("source_files")
    if not isinstance(source_files, dict) or not source_files:
        raise BlockedNotDeployable("Manifest has no pinned source files")
    if not REQUIRED_INDEPENDENT_SOURCE_KEYS <= set(source_files):
        raise BlockedNotDeployable("Manifest lacks independent evidence pins")
    today = _today()
    for key, record in source_files.items():
        if not isinstance(record, dict):
            raise BlockedNotDeployable(f"Invalid source pin: {key}")
        relative = Path(str(record.get("path", "")))
        expected = str(record.get("sha256", ""))
        path = pages / relative
        try:
            actual = _sha256_bytes(path.read_bytes())
        except OSError as error:
            raise BlockedNotDeployable(f"Missing pinned source: {relative}") from error
        if actual != expected:
            raise BlockedNotDeployable(
                f"Source SHA drift for {relative}: expected={expected} actual={actual}"
            )
        if key in REQUIRED_INDEPENDENT_SOURCE_KEYS:
            try:
                checked_on = date.fromisoformat(str(record["checked_on"]))
                expires_on = date.fromisoformat(str(record["expires_on"]))
            except (KeyError, ValueError) as error:
                raise BlockedNotDeployable(
                    f"Invalid independent source dates: {key}"
                ) from error
            max_age_days = int(record.get("max_age_days", 0))
            if (
                max_age_days < 1
                or max_age_days > 30
                or expires_on != checked_on + timedelta(days=max_age_days)
            ):
                raise BlockedNotDeployable(
                    f"Independent source expiry differs: {key}"
                )
            if today < checked_on or today > expires_on:
                raise BlockedNotDeployable(
                    f"Independent source expired or future-dated: {key}"
                )
    _validate_prohibited_claims(manifest)
    _validate_official_source_expiry(manifest)
    return manifest


def _validate_prohibited_claims(manifest: dict[str, Any]) -> None:
    prohibited = manifest.get("prohibited_claim_fragments")
    if (
        not isinstance(prohibited, list)
        or len(prohibited) != len(set(prohibited))
        or set(prohibited) != REQUIRED_PROHIBITED_CLAIM_FRAGMENTS
    ):
        raise BlockedNotDeployable(
            "Prohibited institutional claim set differs from required pins"
        )


def _validate_official_source_expiry(manifest: dict[str, Any]) -> None:
    policy = manifest.get("official_source_policy")
    references = manifest.get("official_references")
    if not isinstance(policy, dict) or not isinstance(references, list):
        raise BlockedNotDeployable("Official-source expiry policy is missing")
    max_age_days = int(policy.get("max_age_days", 0))
    if max_age_days < 1 or max_age_days > 30:
        raise BlockedNotDeployable("Official-source max age must be 1-30 days")
    if not references:
        raise BlockedNotDeployable("Official references cannot be empty")
    reference_ids = {
        str(reference.get("id", ""))
        for reference in references
        if isinstance(reference, dict)
    }
    if reference_ids != set(REQUIRED_OFFICIAL_REFERENCE_PINS):
        raise BlockedNotDeployable("Official reference ID set differs")
    seen: set[str] = set()
    today = _today()
    for reference in references:
        if not isinstance(reference, dict):
            raise BlockedNotDeployable("Invalid official reference")
        source_id = str(reference.get("id", ""))
        publisher = str(reference.get("publisher", ""))
        if not source_id or source_id in seen:
            raise BlockedNotDeployable("Invalid official reference identity")
        seen.add(source_id)
        expected = REQUIRED_OFFICIAL_REFERENCE_PINS[source_id]
        if (
            publisher != expected["publisher"]
            or str(reference.get("url", "")) != expected["url"]
            or tuple(reference.get("supports", [])) != expected["supports"]
        ):
            raise BlockedNotDeployable(
                f"Official reference pin differs: {source_id}"
            )
        try:
            checked_on = date.fromisoformat(str(reference["checked_on"]))
            expires_on = date.fromisoformat(str(reference["expires_on"]))
        except (KeyError, ValueError) as error:
            raise BlockedNotDeployable(
                f"Invalid official-source dates: {source_id}"
            ) from error
        if expires_on != checked_on + timedelta(days=max_age_days):
            raise BlockedNotDeployable(
                f"Official-source expiry differs: {source_id}"
            )
        if today < checked_on or today > expires_on:
            raise BlockedNotDeployable(
                f"Official source expired or future-dated: {source_id}"
            )
        parts = urlsplit(str(reference.get("url", "")))
        expected_host = urlsplit(str(expected["url"])).netloc
        if parts.scheme != "https" or parts.netloc != expected_host:
            raise BlockedNotDeployable(
                f"Official source must stay on first-party host: {source_id}"
            )
        supports = reference.get("supports")
        if (
            not isinstance(supports, list)
            or not supports
            or any(not str(statement).strip() for statement in supports)
        ):
            raise BlockedNotDeployable(
                f"Official source has no pinned policy facts: {source_id}"
            )
    if {
        str(reference["publisher"])
        for reference in references
    } != {"Apple", "Microsoft"}:
        raise BlockedNotDeployable(
            "Official references must include Apple and Microsoft"
        )


def _native_script_ratio(locale: str, values: Iterable[str]) -> float:
    ranges = NATIVE_SCRIPT_RANGES.get(locale)
    if not ranges:
        return 1.0
    text = SOURCE_TOKEN_RE.sub("", " ".join(values))
    text = re.sub(r"[A-Za-z0-9._/+:-]+", "", text)
    letters = [character for character in text if character.isalpha()]
    native = sum(
        any(start <= ord(character) <= end for start, end in ranges)
        for character in letters
    )
    return native / max(1, len(letters))


def _load_i18n() -> dict[str, dict[str, Any]]:
    payload = _read_json(I18N_PATH)
    localizations = payload.get("localizations")
    if not isinstance(localizations, dict):
        raise BlockedNotDeployable("Procurement i18n localizations are missing")
    require_official_locale_coverage(
        "institutional procurement",
        localizations,
    )
    source = localizations.get("en-US")
    if not isinstance(source, dict):
        raise BlockedNotDeployable("Procurement i18n lacks en-US")
    for locale, mapping in localizations.items():
        if not isinstance(mapping, dict) or set(mapping) != SOURCE_FIELDS:
            raise BlockedNotDeployable(f"Wrong i18n fields for {locale}")
        labels = mapping.get("labels")
        steps = mapping.get("steps")
        if not isinstance(labels, dict) or set(labels) != LABEL_FIELDS:
            raise BlockedNotDeployable(f"Wrong i18n labels for {locale}")
        expected_steps = 5 if locale in DEEP_WORKFLOW_LOCALES else 3
        if not isinstance(steps, list) or len(steps) < expected_steps:
            raise BlockedNotDeployable(
                f"Workflow depth is too low for {locale}: {len(steps or [])}"
            )
        strings = [
            str(mapping[key])
            for key in SOURCE_FIELDS - {"labels", "steps"}
        ]
        strings.extend(str(value) for value in labels.values())
        strings.extend(str(value) for value in steps)
        if any(value != value.strip() or "\n" in value for value in strings):
            raise BlockedNotDeployable(f"Invalid whitespace in i18n {locale}")
        if locale not in {"en-US", "en-AU", "en-CA", "en-GB"}:
            for key in (
                "intro",
                "paid",
                "direct",
                "iap",
                "fit",
                "disclosure",
                "measurement",
            ):
                if mapping[key] == source[key]:
                    raise BlockedNotDeployable(
                        f"English fallback in {locale}: {key}"
                    )
        ratio = _native_script_ratio(
            locale,
            [
                str(mapping[key])
                for key in (
                    "title",
                    "intro",
                    "paid",
                    "direct",
                    "iap",
                    "fit",
                    "disclosure",
                    "measurement",
                )
            ]
            + [str(value) for value in steps],
        )
        if ratio < 0.70:
            raise BlockedNotDeployable(
                f"Native-script ratio too low for {locale}: {ratio:.3f}"
            )
    return localizations


def _source_paths(
    pages: Path,
    manifest: dict[str, Any],
) -> dict[str, Path]:
    source_files = manifest["source_files"]
    return {
        key: pages / Path(str(record["path"]))
        for key, record in source_files.items()
    }


def _intent_records(
    payload: dict[str, Any],
    expected_keys: set[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    records = payload.get("records")
    if (
        not isinstance(records, list)
        or payload.get("app_count") != len(expected_keys)
        or payload.get("locale_count") != len(OFFICIAL_LOCALES)
    ):
        raise BlockedNotDeployable("Publisher intent catalog metadata differs")
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise BlockedNotDeployable("Invalid publisher intent record")
        pair = (str(record.get("locale")), str(record.get("app_key")))
        if pair in by_pair:
            raise BlockedNotDeployable(f"Duplicate publisher intent pair: {pair}")
        by_pair[pair] = record
    expected_pairs = {
        (locale, key)
        for locale in OFFICIAL_LOCALES
        for key in expected_keys
    }
    if set(by_pair) != expected_pairs:
        raise BlockedNotDeployable(
            "Publisher intent coverage differs: "
            f"missing={len(expected_pairs - set(by_pair))}, "
            f"extra={len(set(by_pair) - expected_pairs)}"
        )
    return by_pair


def _apply_intent_overrides(
    by_pair: dict[tuple[str, str], dict[str, Any]],
    payload: dict[str, Any],
    expected_keys: set[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    if payload.get("schema_version") != 1:
        raise BlockedNotDeployable("Unsupported intent override version")
    localizations = payload.get("localizations")
    if not isinstance(localizations, dict):
        raise BlockedNotDeployable("Intent overrides lack localizations")
    output = {pair: dict(record) for pair, record in by_pair.items()}
    for locale, apps in localizations.items():
        if locale not in OFFICIAL_LOCALES or not isinstance(apps, dict):
            raise BlockedNotDeployable(f"Invalid intent override locale: {locale}")
        for key, fields in apps.items():
            if key not in expected_keys or not isinstance(fields, dict):
                raise BlockedNotDeployable(
                    f"Invalid intent override app: {locale}/{key}"
                )
            if not fields or not set(fields) <= {
                "publisher_query",
                "decision_context",
            }:
                raise BlockedNotDeployable(
                    f"Invalid intent override fields: {locale}/{key}"
                )
            for field, value in fields.items():
                if (
                    not isinstance(value, str)
                    or value != value.strip()
                    or "\n" in value
                    or len(value) < 12
                ):
                    raise BlockedNotDeployable(
                        f"Invalid intent override value: {locale}/{key}/{field}"
                    )
                output[(locale, key)][field] = value
    return output


def _validate_no_intent_fallback(
    records: dict[tuple[str, str], dict[str, Any]],
    expected_keys: set[str],
) -> None:
    base = {
        key: records[("en-US", key)]
        for key in expected_keys
    }
    for locale in OFFICIAL_LOCALES:
        if locale.startswith("en-"):
            continue
        for key in expected_keys:
            record = records[(locale, key)]
            for field in ("publisher_query", "decision_context"):
                value = str(record[field])
                source = str(base[key][field])
                if (
                    value == source
                    and len(source) >= 24
                    and len(re.findall(r"[A-Za-z]+", source)) >= 4
                ):
                    raise BlockedNotDeployable(
                        f"English intent fallback: {locale}/{key}/{field}"
                    )
            text = (
                f"{record['publisher_query']} {record['decision_context']}"
            )
            ranges = NATIVE_SCRIPT_RANGES.get(locale)
            if ranges:
                native = sum(
                    any(start <= ord(char) <= end for start, end in ranges)
                    for char in text
                    if char.isalpha()
                )
                if native < 12:
                    raise BlockedNotDeployable(
                        f"Localized intent lacks native script: {locale}/{key}"
                    )
            elif len(ENGLISH_FALLBACK_WORD_RE.findall(text)) >= 8:
                raise BlockedNotDeployable(
                    f"Probable English intent fallback: {locale}/{key}"
                )


def _checked_date(value: Any, label: str) -> date:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise BlockedNotDeployable(f"Invalid evidence timestamp: {label}") from error
    if parsed.tzinfo is None:
        raise BlockedNotDeployable(f"Evidence timestamp lacks timezone: {label}")
    return parsed.date()


def _validate_evidence_freshness(
    manifest: dict[str, Any],
    lookup: dict[str, Any],
    storefront: dict[str, Any],
    apple_receipt: dict[str, Any],
    owner_registry: dict[str, Any],
) -> None:
    policy = manifest["official_source_policy"]
    today = _today()
    evidence = (
        (
            "public lookup",
            lookup.get("checked_at"),
            int(policy.get("public_lookup_max_age_days", 0)),
        ),
        (
            "storefront snapshot",
            storefront.get("checked_at"),
            int(policy.get("storefront_max_age_days", 0)),
        ),
        (
            "Apple Lookup receipt",
            apple_receipt.get("fetched_at"),
            int(policy.get("apple_lookup_receipt_max_age_days", 0)),
        ),
        (
            "owner support registry",
            owner_registry.get("checked_at"),
            int(policy.get("owner_support_registry_max_age_days", 0)),
        ),
    )
    for label, checked_at, max_age_days in evidence:
        if max_age_days < 1 or max_age_days > 30:
            raise BlockedNotDeployable(f"Invalid freshness policy: {label}")
        checked_on = _checked_date(checked_at, label)
        age = (today - checked_on).days
        if age < 0 or age > max_age_days:
            raise BlockedNotDeployable(
                f"Expired or future-dated evidence: {label} age={age}"
            )
    for label, payload, start_key in (
        ("Apple Lookup receipt", apple_receipt, "fetched_at"),
        ("owner support registry", owner_registry, "checked_at"),
    ):
        try:
            start = datetime.fromisoformat(
                str(payload[start_key]).replace("Z", "+00:00")
            )
            expires = datetime.fromisoformat(
                str(payload["expires_at"]).replace("Z", "+00:00")
            )
        except (KeyError, ValueError) as error:
            raise BlockedNotDeployable(
                f"Invalid internal evidence expiry: {label}"
            ) from error
        max_age = int(
            policy[
                "apple_lookup_receipt_max_age_days"
                if label == "Apple Lookup receipt"
                else "owner_support_registry_max_age_days"
            ]
        )
        if expires != start + timedelta(days=max_age):
            raise BlockedNotDeployable(
                f"Internal evidence expiry differs: {label}"
            )
    if not (
        lookup.get("checked_at")
        == apple_receipt.get("fetched_at")
        == owner_registry.get("checked_at")
    ):
        raise BlockedNotDeployable(
            "Public lookup and independent receipts were not captured together"
        )


def _campaign_attribution(record: dict[str, Any], app_id: str) -> dict[str, str]:
    url = str(record.get("app_store_url", ""))
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    provider = query.get("pt", [])
    campaign = query.get("ct", [])
    media_type = query.get("mt", [])
    if (
        parts.scheme != "https"
        or parts.netloc != "apps.apple.com"
        or f"id{app_id}" not in parts.path
        or len(provider) != 1
        or not provider[0].isdigit()
        or len(campaign) != 1
        or CAMPAIGN_TOKEN_RE.fullmatch(campaign[0]) is None
        or media_type != ["8"]
    ):
        raise BlockedNotDeployable(
            f"Invalid first-party campaign URL: {record.get('locale')}/{app_id}"
        )
    return {
        "url": url,
        "provider_token": provider[0],
        "campaign_token": campaign[0],
        "media_type": media_type[0],
        "source": "verified_publisher_intent_catalog",
    }


def _normalize_brand(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.findall(r"[a-z0-9+]+", normalized))


def _brand_matches(track_name: str, candidates: Iterable[str]) -> bool:
    track = _normalize_brand(track_name)
    return any(
        track == brand or track.startswith(f"{brand} ")
        for brand in (_normalize_brand(value) for value in candidates)
        if brand
    )


def _portfolio_receipt_records(
    receipt: dict[str, Any],
    expected_count: int,
) -> dict[str, dict[str, Any]]:
    normalized = deepcopy(receipt)
    digest = str(normalized.pop("content_digest", ""))
    records = receipt.get("records")
    try:
        captured_on = date.fromisoformat(str(receipt["captured_on"]))
        expires_on = date.fromisoformat(str(receipt["expires_on"]))
    except (KeyError, ValueError) as error:
        raise BlockedNotDeployable(
            "Invalid canonical portfolio receipt dates"
        ) from error
    if (
        receipt.get("schema_version") != 1
        or receipt.get("source_kind") != "canonical_app_portfolio_receipt"
        or receipt.get("source_path") != "00_Standards/app-portfolio.md"
        or SHA256_RE.fullmatch(str(receipt.get("source_sha256", ""))) is None
        or expires_on != captured_on + timedelta(days=7)
        or digest != f"sha256:{_canonical_digest(normalized)}"
        or receipt.get("record_count") != expected_count
        or not isinstance(records, list)
        or len(records) != expected_count
    ):
        raise BlockedNotDeployable("Invalid canonical portfolio receipt")
    by_key: dict[str, dict[str, Any]] = {}
    bundles: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise BlockedNotDeployable("Invalid canonical portfolio record")
        key = str(record.get("app_key", ""))
        bundle = str(record.get("bundle_id", ""))
        portfolio_id = record.get("portfolio_app_store_id")
        if (
            not key
            or key in by_key
            or BUNDLE_ID_RE.fullmatch(bundle) is None
            or bundle in bundles
            or (
                portfolio_id is not None
                and ID_RE.fullmatch(str(portfolio_id)) is None
            )
            or SHA256_RE.fullmatch(
                str(record.get("source_line_sha256", ""))
            )
            is None
            or int(record.get("source_line_number", 0)) <= 0
            or not str(record.get("portfolio_name", "")).strip()
            or not str(record.get("canonical_name", "")).strip()
        ):
            raise BlockedNotDeployable(
                f"Invalid canonical portfolio identity: {key}"
            )
        by_key[key] = record
        bundles.add(bundle)
    return by_key


def _receipt_records(
    receipt: dict[str, Any],
    expected_count: int,
) -> dict[str, dict[str, Any]]:
    if (
        receipt.get("schema_version") != 1
        or receipt.get("publisher") != "Apple"
        or receipt.get("source_kind") != "itunes_lookup_raw_response"
    ):
        raise BlockedNotDeployable("Invalid Apple Lookup receipt metadata")
    request = urlsplit(str(receipt.get("request_url", "")))
    if request.scheme != "https" or request.netloc != "itunes.apple.com":
        raise BlockedNotDeployable("Apple Lookup receipt host differs")
    response = receipt.get("response")
    if not isinstance(response, dict):
        raise BlockedNotDeployable("Apple Lookup receipt response is missing")
    canonical = str(receipt.get("response_canonical_sha256", ""))
    if canonical != _canonical_digest(response):
        raise BlockedNotDeployable("Apple Lookup receipt canonical digest differs")
    results = response.get("results")
    if (
        not isinstance(results, list)
        or response.get("resultCount") != expected_count
        or len(results) != expected_count
    ):
        raise BlockedNotDeployable("Apple Lookup receipt must contain exact roster")
    records = {
        str(item.get("trackId")): item
        for item in results
        if isinstance(item, dict)
    }
    if len(records) != expected_count:
        raise BlockedNotDeployable("Apple Lookup receipt has duplicate identities")
    return records


def _owner_registry_records(
    registry: dict[str, Any],
    expected_count: int,
) -> dict[str, dict[str, Any]]:
    allowed_hosts = {"alice51849.github.io", "open.cait518.cc"}
    records = registry.get("records")
    if (
        registry.get("schema_version") != 1
        or registry.get("source_kind")
        != "first_party_owner_page_http_receipts"
        or set(registry.get("allowed_owner_hosts", [])) != allowed_hosts
        or registry.get("record_count") != expected_count
        or not isinstance(records, list)
        or len(records) != expected_count
    ):
        raise BlockedNotDeployable("Invalid owner support registry metadata")
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise BlockedNotDeployable("Invalid owner support record")
        app_id = str(record.get("app_store_id", ""))
        if ID_RE.fullmatch(app_id) is None or app_id in by_id:
            raise BlockedNotDeployable("Duplicate owner support identity")
        for kind in ("support", "privacy"):
            url = str(record.get(f"{kind}_url", ""))
            receipt = record.get(f"{kind}_receipt")
            if not isinstance(receipt, dict):
                raise BlockedNotDeployable(
                    f"Missing {kind} owner receipt: {app_id}"
                )
            parts = urlsplit(url)
            fetched = urlsplit(str(receipt.get("fetched_url", "")))
            if (
                parts.scheme != "https"
                or parts.netloc not in allowed_hosts
                or receipt.get("requested_url") != url
                or receipt.get("http_status") != 200
                or receipt.get("owner_host") not in allowed_hosts
                or fetched.scheme != "https"
                or fetched.netloc not in allowed_hosts
                or SHA256_RE.fullmatch(
                    str(receipt.get("content_sha256", ""))
                )
                is None
                or int(receipt.get("content_length", 0)) <= 0
                or not receipt.get("canonical_brand_tokens")
                or not receipt.get("matched_brand_tokens")
                or set(receipt["matched_brand_tokens"])
                != set(receipt["canonical_brand_tokens"])
            ):
                raise BlockedNotDeployable(
                    f"Invalid {kind} owner receipt: {app_id}"
                )
        by_id[app_id] = record
    return by_id


def _validate_identity_evidence(
    manifest: dict[str, Any],
    finder: dict[str, Any],
    lookup: dict[str, Any],
    storefront: dict[str, Any],
    apple_receipt: dict[str, Any],
    owner_registry: dict[str, Any],
    portfolio_receipt: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    expected_count = int(manifest["expected_app_count"])
    apps = finder.get("apps")
    lookup_records = lookup.get("records")
    if (
        not isinstance(apps, list)
        or len(apps) != expected_count
        or finder.get("record_count") != expected_count
    ):
        raise BlockedNotDeployable("Verified catalog must contain exactly 46 apps")
    if (
        not isinstance(lookup_records, list)
        or len(lookup_records) != expected_count
        or lookup.get("record_count") != expected_count
    ):
        raise BlockedNotDeployable("Public lookup must contain exactly 46 apps")
    if storefront.get("app_count") != expected_count:
        raise BlockedNotDeployable("Storefront snapshot must contain 46 apps")

    apps_by_key: dict[str, dict[str, Any]] = {}
    app_ids: set[str] = set()
    for app in apps:
        if not isinstance(app, dict):
            raise BlockedNotDeployable("Invalid verified app record")
        key = str(app.get("key", ""))
        app_id = str(app.get("app_store_id", ""))
        if (
            not key
            or key in apps_by_key
            or ID_RE.fullmatch(app_id) is None
            or app_id in app_ids
            or app.get("verified_live") is not True
        ):
            raise BlockedNotDeployable(f"Invalid verified app identity: {key}")
        apps_by_key[key] = app
        app_ids.add(app_id)

    storefront_ids = {
        str(app_id) for app_id in storefront.get("app_ids", [])
    }
    receipt_by_id = _receipt_records(apple_receipt, expected_count)
    owner_by_id = _owner_registry_records(owner_registry, expected_count)
    lookup_by_id = {
        str(record.get("app_store_id")): record
        for record in lookup_records
        if isinstance(record, dict)
    }
    if (
        storefront_ids != app_ids
        or set(receipt_by_id) != app_ids
        or set(owner_by_id) != app_ids
        or set(lookup_by_id) != app_ids
    ):
        raise BlockedNotDeployable("Independent evidence roster differs")

    portfolio_by_key = _portfolio_receipt_records(
        portfolio_receipt,
        expected_count,
    )
    if set(portfolio_by_key) != set(apps_by_key):
        raise BlockedNotDeployable(
            "Canonical portfolio receipt roster differs"
        )
    aliases = manifest.get("canonical_brand_aliases", {})
    if not isinstance(aliases, dict) or set(aliases) - set(apps_by_key):
        raise BlockedNotDeployable("Invalid canonical brand aliases")
    for key, app in apps_by_key.items():
        app_id = str(app["app_store_id"])
        evidence = lookup_by_id[app_id]
        raw = receipt_by_id[app_id]
        owner = owner_by_id[app_id]
        portfolio = portfolio_by_key[key]
        raw_bundle = str(raw.get("bundleId", ""))
        raw_name = str(raw.get("trackName", "")).strip()
        track_url = urlsplit(str(raw.get("trackViewUrl", "")))
        supported_devices = [
            str(value) for value in raw.get("supportedDevices", [])
        ]
        iphone_supported = any(
            value.startswith("iPhone") for value in supported_devices
        )
        ipad_supported = any(
            value.startswith("iPad") for value in supported_devices
        )
        expected_platforms = (
            ["iPhone", "iPad"] if ipad_supported else ["iPhone"]
        )
        brand_candidates = [
            str(app["name"]),
            str(portfolio["portfolio_name"]),
            *[str(value) for value in aliases.get(key, [])],
        ]
        if (
            str(raw.get("trackId")) != app_id
            or BUNDLE_ID_RE.fullmatch(raw_bundle) is None
            or raw_bundle != portfolio["bundle_id"]
            or portfolio.get("verified_app_store_id") != app_id
            or (
                portfolio.get("portfolio_app_store_id") is not None
                and str(portfolio["portfolio_app_store_id"]) != app_id
            )
            or portfolio.get("canonical_name") != app.get("name")
            or not raw_name
            or not _brand_matches(raw_name, brand_candidates)
            or raw.get("sellerName") != manifest.get("apple_lookup_seller_name")
            or raw.get("artistName") != manifest.get("apple_lookup_seller_name")
            or track_url.scheme != "https"
            or track_url.netloc != "apps.apple.com"
            or f"id{app_id}" not in track_url.path
            or not iphone_supported
            or not supported_devices
        ):
            raise BlockedNotDeployable(
                f"Apple receipt and portfolio identity differ: {key}"
            )
        expected_url = f"https://apps.apple.com/app/id{app_id}"
        expected_lookup = (
            f"https://itunes.apple.com/lookup?id={app_id}"
            "&country=us&entity=software"
        )
        expected_page = f"https://apps.apple.com/us/app/id{app_id}"
        if (
            evidence.get("canonical_app_store_url") != expected_url
            or evidence.get("lookup_url") != expected_lookup
            or evidence.get("app_store_page_url") != expected_page
            or evidence.get("bundle_id") != raw_bundle
            or evidence.get("public_name") != raw_name
            or evidence.get("platforms") != expected_platforms
            or evidence.get("ipad_supported")
            != ("iPad" in evidence.get("platforms", []))
            or evidence.get("ipad_supported") is not ipad_supported
            or owner.get("app_key") != key
            or owner.get("canonical_brand") != str(app["name"])
            or evidence.get("support_url") != owner.get("support_url")
            or evidence.get("privacy_url") != owner.get("privacy_url")
        ):
            raise BlockedNotDeployable(
                f"Public lookup cross-source identity differs: {key}"
            )
        expected_download = (
            "paid_download"
            if app.get("purchase_model") == "paid_upfront"
            else "free_download"
        )
        if evidence.get("download_class") != expected_download:
            raise BlockedNotDeployable(
                f"Purchase classification differs from public lookup: {key}"
            )
        for field in (
            "support_url",
            "privacy_url",
            "lookup_url",
            "app_store_page_url",
        ):
            parts = urlsplit(str(evidence.get(field, "")))
            if parts.scheme != "https" or not parts.netloc:
                raise BlockedNotDeployable(f"Invalid {field} for {key}")

    return (
        sorted(
            apps_by_key.values(),
            key=lambda app: (
                str(
                    lookup_by_id[str(app["app_store_id"])]["public_name"]
                ).casefold(),
                str(app["app_store_id"]),
            ),
        ),
        lookup_by_id,
    )


def _load_sources(
    pages: Path,
    manifest: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    dict[str, Any],
]:
    paths = _source_paths(pages, manifest)
    finder = _read_json(paths["verified_catalog"])
    lookup = _read_json(paths["public_lookup"])
    intents = _read_json(paths["publisher_intent"])
    intent_overrides = _read_json(paths["intent_overrides"])
    storefront = _read_json(paths["storefront_state"])
    apple_receipt = _read_json(paths["apple_lookup_receipt"])
    owner_registry = _read_json(paths["owner_support_registry"])
    portfolio_receipt = _read_json(paths["portfolio_receipt"])
    _validate_evidence_freshness(
        manifest,
        lookup,
        storefront,
        apple_receipt,
        owner_registry,
    )
    apps, lookup_by_id = _validate_identity_evidence(
        manifest,
        finder,
        lookup,
        storefront,
        apple_receipt,
        owner_registry,
        portfolio_receipt,
    )
    apps_by_key = {str(app["key"]): app for app in apps}

    by_pair = _intent_records(intents, set(apps_by_key))
    by_pair = _apply_intent_overrides(
        by_pair,
        intent_overrides,
        set(apps_by_key),
    )
    _validate_no_intent_fallback(by_pair, set(apps_by_key))
    for (locale, key), record in by_pair.items():
        app = apps_by_key[key]
        if (
            str(record.get("app_store_id")) != str(app["app_store_id"])
            or record.get("purchase_model") != app.get("purchase_model")
            or record.get("verified_live") is not True
            or record.get("is_ranking") is not False
            or record.get("measured_search_volume") is not False
            or not str(record.get("publisher_query", "")).strip()
            or not str(record.get("decision_context", "")).strip()
        ):
            raise BlockedNotDeployable(
                f"Unsafe publisher intent record: {locale}/{key}"
            )
        _campaign_attribution(record, str(app["app_store_id"]))
    return (
        apps,
        lookup_by_id,
        by_pair,
        {
            "lookup": lookup,
            "storefront": storefront,
            "finder": finder,
            "apple_receipt": apple_receipt,
            "owner_registry": owner_registry,
            "portfolio_receipt": manifest["source_files"][
                "portfolio_receipt"
            ],
        },
    )


def _validate_related_fit(
    manifest: dict[str, Any],
    apps: list[dict[str, Any]],
    intents: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, list[str]]:
    keys = {str(app["key"]) for app in apps}
    related = manifest.get("related_fit")
    if not isinstance(related, dict) or set(related) != {"school", "business"}:
        raise BlockedNotDeployable("Related-fit manifest must define two workflows")
    by_key = {key: [] for key in keys}
    for workflow, records in related.items():
        if not isinstance(records, dict):
            raise BlockedNotDeployable(f"Invalid related-fit workflow: {workflow}")
        unknown = set(records) - keys
        if unknown:
            raise BlockedNotDeployable(
                f"Unknown related-fit apps for {workflow}: {sorted(unknown)}"
            )
        for key, needles in records.items():
            if not isinstance(needles, list) or len(needles) < 2:
                raise BlockedNotDeployable(f"Weak related-fit evidence: {workflow}/{key}")
            source = intents[("en-US", key)]
            haystack = (
                f"{source['publisher_query']} {source['decision_context']}"
            ).casefold()
            missing = [
                str(needle)
                for needle in needles
                if str(needle).casefold() not in haystack
            ]
            if missing:
                raise BlockedNotDeployable(
                    f"Related-fit evidence drift: {workflow}/{key} missing={missing}"
                )
            by_key[key].append(workflow)
    return by_key


def _validate_canary(
    manifest: dict[str, Any],
    apps: list[dict[str, Any]],
    related_fit: dict[str, list[str]],
) -> tuple[str, ...]:
    canary = manifest.get("canary")
    if not isinstance(canary, dict):
        raise BlockedNotDeployable("Canary policy is missing")
    keys = canary.get("app_keys")
    if (
        canary.get("status") != "BLOCKED_PENDING_ADMIN_VERIFICATION"
        or not isinstance(keys, list)
        or len(keys) not in {2, 3}
        or len(keys) != len(set(keys))
    ):
        raise BlockedNotDeployable("Canary must stay BLOCKED with 2-3 apps")
    apps_by_key = {str(app["key"]): app for app in apps}
    if any(str(key) not in apps_by_key for key in keys):
        raise BlockedNotDeployable("Canary contains an unknown app")
    selected = [apps_by_key[str(key)] for key in keys]
    models = {str(app["purchase_model"]) for app in selected}
    if models != {"paid_upfront", "free_with_lifetime_unlock"}:
        raise BlockedNotDeployable(
            "Canary must prove both paid-download and IAP boundaries"
        )
    if any(not related_fit[str(app["key"])] for app in selected):
        raise BlockedNotDeployable("Canary app lacks first-party fit evidence")
    return tuple(str(key) for key in keys)


def _publisher_ui() -> dict[str, dict[str, str]]:
    raw = publisher_intent_catalog.load_ui_i18n()
    return {
        locale: publisher_intent_catalog.dynamic_ui(mapping)
        for locale, mapping in raw.items()
    }


def page_relative(locale: str | None) -> Path:
    return (
        ROOT_DIR / PAGE_NAME
        if locale is None
        else Path(locale) / ROOT_DIR / PAGE_NAME
    )


def data_relative(locale: str | None) -> Path:
    return (
        ROOT_DIR / DATA_NAME
        if locale is None
        else Path(locale) / ROOT_DIR / DATA_NAME
    )


def app_page_relative(locale: str | None, app_key: str) -> Path:
    relative = APP_DIR / f"{app_key}.html"
    return relative if locale is None else Path(locale) / relative


def page_url(locale: str | None) -> str:
    return f"{SITE}/{page_relative(locale).as_posix()}"


def app_page_url(locale: str | None, app_key: str) -> str:
    return f"{SITE}/{app_page_relative(locale, app_key).as_posix()}"


def data_url(locale: str | None) -> str:
    return f"{SITE}/{data_relative(locale).as_posix()}"


def schema_url() -> str:
    return f"{SITE}/{(ROOT_DIR / SCHEMA_NAME).as_posix()}"


def scorecard_url(days: int) -> str:
    return f"{SITE}/{(ROOT_DIR / SCORECARD_NAMES[days]).as_posix()}"


def scorecard_schema_url() -> str:
    return f"{SITE}/{(ROOT_DIR / SCORECARD_SCHEMA_NAME).as_posix()}"


def sitemap_url() -> str:
    return f"{SITE}/{SITEMAP_NAME}"


def _source_digest(manifest: dict[str, Any]) -> str:
    normalized = {
        "source_files": {
            key: dict(record)
            for key, record in sorted(manifest["source_files"].items())
        },
        "official_source_policy": manifest["official_source_policy"],
        "official_references": manifest["official_references"],
        "apple_lookup_seller_name": manifest["apple_lookup_seller_name"],
        "canonical_brand_aliases": manifest["canonical_brand_aliases"],
        "canary": manifest["canary"],
        "measurement": manifest["measurement"],
    }
    return f"sha256:{_canonical_digest(normalized)}"


def _roster_digest(
    apps: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
) -> str:
    records = []
    for app in apps:
        app_id = str(app["app_store_id"])
        evidence = lookup[app_id]
        records.append(
            {
                "app_store_id": app_id,
                "bundle_id": evidence["bundle_id"],
                "public_name": evidence["public_name"],
                "canonical_app_store_url": evidence["canonical_app_store_url"],
                "purchase_model": app["purchase_model"],
                "support_url": evidence["support_url"],
                "privacy_url": evidence["privacy_url"],
                "platforms": evidence["platforms"],
                "checked_at": evidence.get("checked_at"),
            }
        )
    return f"sha256:{_canonical_digest(records)}"


def _with_content_digest(payload: dict[str, Any]) -> dict[str, Any]:
    output = deepcopy(payload)
    output.pop("content_digest", None)
    output["content_digest"] = f"sha256:{_canonical_digest(output)}"
    return output


def _localized_apps(
    locale: str,
    apps: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    intents: dict[tuple[str, str], dict[str, Any]],
    related_fit: dict[str, list[str]],
    copy: dict[str, Any],
    publisher_ui: dict[str, str],
    checked_at: str,
    canary_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    records = []
    for app in apps:
        key = str(app["key"])
        app_id = str(app["app_store_id"])
        evidence = lookup[app_id]
        intent = intents[(locale, key)]
        purchase_model = str(app["purchase_model"])
        is_canary = key in canary_keys
        campaign = _campaign_attribution(intent, app_id)
        download_model = (
            "paid_download"
            if purchase_model == "paid_upfront"
            else "free_download"
        )
        unlock_model = (
            "included_in_paid_download"
            if purchase_model == "paid_upfront"
            else "optional_one_time_iap_individual_purchase"
        )
        deployment_class = (
            "asm_apps_and_books_paid_candidate"
            if purchase_model == "paid_upfront"
            else "intune_direct_store_free_tier_evaluation"
        )
        limitation = (
            str(copy["paid"])
            if purchase_model == "paid_upfront"
            else str(copy["iap"])
        )
        if purchase_model == "paid_upfront":
            policy = {
                "classification": "eligible_paid_download_general_apple_rule",
                "portal_visibility": "BLOCKED_UNVERIFIED_IN_ASM_ABM",
                "device_assignment_language_allowed": True,
                "volume_procurement_language_allowed": True,
                "full_unlock_distribution": "INCLUDED_IN_PAID_DOWNLOAD",
            }
            canary_status = "BLOCKED_PORTAL_VISIBILITY_UNVERIFIED"
        else:
            policy = {
                "classification": "free_download_with_lifetime_iap",
                "portal_visibility": "NOT_APPLICABLE_TO_IAP_UNLOCK",
                "device_assignment_language_allowed": False,
                "volume_procurement_language_allowed": False,
                "full_unlock_distribution": (
                    "NOT_APPLICABLE_REQUIRES_INDIVIDUAL_PERSONAL_APPLE_ACCOUNT"
                ),
            }
            canary_status = "BLOCKED_FREE_TIER_ONLY_IAP_NOT_DISTRIBUTABLE"
        records.append(
            {
                "app_key": key,
                "app_store_id": app_id,
                "bundle_id": str(evidence["bundle_id"]),
                "public_name": str(evidence["public_name"]),
                "canonical_app_store_url": str(
                    evidence["canonical_app_store_url"]
                ),
                "campaign_app_store_url": campaign["url"],
                "campaign_attribution": {
                    key: value
                    for key, value in campaign.items()
                    if key != "url"
                },
                "platforms": list(evidence["platforms"]),
                "ipad_supported": bool(evidence["ipad_supported"]),
                "purchase_model": purchase_model,
                "purchase_model_wording": publisher_ui[
                    publisher_intent_catalog.PURCHASE_LABELS[purchase_model]
                ],
                "download_model": download_model,
                "unlock_model": unlock_model,
                "deployment_class": deployment_class,
                "publisher_query": str(intent["publisher_query"]),
                "decision_context": str(intent["decision_context"]),
                "related_fit": sorted(related_fit[key]),
                "canary": is_canary,
                "canary_status": (
                    canary_status if is_canary else "NOT_SELECTED_FOR_CANARY"
                ),
                "institutional_policy": policy,
                "limitation": limitation,
                "support_url": str(evidence["support_url"]),
                "privacy_url": str(evidence["privacy_url"]),
                "last_checked": checked_at,
                "lookup_provenance": {
                    "identity_platform_download": str(evidence["lookup_url"]),
                    "support_privacy": str(evidence["app_store_page_url"]),
                    "method": "cross_validated_public_get",
                    "public_name_rule": (
                        "exact_apple_us_trackName_and_canonical_brand_prefix"
                    ),
                    "owner_url_rule": (
                        "exact_first_party_registry_url_and_brand_receipt"
                    ),
                    "independent_pins": [
                        "apple_lookup_receipt",
                        "owner_support_registry",
                        "portfolio_receipt",
                    ],
                },
                "verified_live": True,
                "institutional_exposure_verified": False,
                "institutional_approval_verified": False,
                "discount_verified": False,
            }
        )
    return records


def _data_payload(
    locale: str,
    route_locale: str | None,
    apps: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    intents: dict[tuple[str, str], dict[str, Any]],
    related_fit: dict[str, list[str]],
    manifest: dict[str, Any],
    source_context: dict[str, Any],
    copy: dict[str, Any],
    publisher_ui: dict[str, str],
    source_digest: str,
    roster_digest: str,
    canary_keys: tuple[str, ...],
) -> dict[str, Any]:
    lookup_payload = source_context["lookup"]
    storefront = source_context["storefront"]
    apple_receipt = source_context["apple_receipt"]
    owner_registry = source_context["owner_registry"]
    portfolio_receipt = source_context["portfolio_receipt"]
    localized_apps = _localized_apps(
        locale,
        apps,
        lookup,
        intents,
        related_fit,
        copy,
        publisher_ui,
        str(lookup_payload["checked_at"]),
        canary_keys,
    )
    counts = {
        "apps": len(localized_apps),
        "paid_upfront": sum(
            app["purchase_model"] == "paid_upfront"
            for app in localized_apps
        ),
        "free_to_start_with_iap": sum(
            app["purchase_model"] == "free_with_lifetime_unlock"
            for app in localized_apps
        ),
        "fully_free": sum(
            app["purchase_model"] == "free" for app in localized_apps
        ),
        "ipad_supported": sum(
            bool(app["ipad_supported"]) for app in localized_apps
        ),
        "school_related": sum(
            "school" in app["related_fit"] for app in localized_apps
        ),
        "business_related": sum(
            "business" in app["related_fit"] for app in localized_apps
        ),
        "canary": sum(bool(app["canary"]) for app in localized_apps),
    }
    payload = {
        "$schema": schema_url(),
        "schema_version": 1,
        "release_status": manifest["release_status"],
        "deployment_status": "not_deployed",
        "locale": locale,
        "route_kind": "x-default" if route_locale is None else "localized",
        "url": data_url(route_locale),
        "generated_on": manifest["candidate_date"],
        "source_digest": source_digest,
        "roster_digest": roster_digest,
        "content_digest": "",
        "publisher": {
            "name": "Lumi Studio",
            "relationship": "first_party_developer",
            "is_independent_ranking": False,
            "support_email": ALLOWED_EMAIL,
        },
        "disclosures": {
            "first_party_non_ranking_non_endorsement": copy["disclosure"],
            "live_policy_note": copy["intro"],
            "public_lookup_scope": copy["disclosure"],
        },
        "official_references": [
            {
                "id": reference["id"],
                "publisher": reference["publisher"],
                "source_title": reference["title"],
                "url": reference["url"],
                "checked_on": reference["checked_on"],
                "expires_on": reference["expires_on"],
            }
            for reference in manifest["official_references"]
        ],
        "source_state": {
            "public_lookup_checked_at": lookup_payload["checked_at"],
            "storefront_snapshot_checked_at": storefront["checked_at"],
            "apple_lookup_receipt_fetched_at": apple_receipt["fetched_at"],
            "apple_lookup_receipt_expires_at": apple_receipt["expires_at"],
            "owner_support_registry_checked_at": owner_registry["checked_at"],
            "owner_support_registry_expires_at": owner_registry["expires_at"],
            "portfolio_receipt_sha256": portfolio_receipt["sha256"],
            "portfolio_receipt_expires_on": portfolio_receipt["expires_on"],
            "official_source_max_age_days": manifest[
                "official_source_policy"
            ]["max_age_days"],
            "lookup_method": "public_get_plus_pinned_cross_source_receipts",
            "institutional_portal_login": False,
            "deployment_or_submission": False,
        },
        "workflow": {
            "paid_apps_and_books": copy["paid"],
            "intune_direct_store_free_tier": copy["direct"],
            "managed_app_iap_warning": copy["iap"],
            "related_fit_method": copy["fit"],
            "administrator_steps": copy["steps"],
        },
        "canary": {
            "status": manifest["canary"]["status"],
            "reason": manifest["canary"]["reason"],
            "count": len(canary_keys),
            "app_keys": list(canary_keys),
            "paid_download_app_keys": [
                app["app_key"]
                for app in localized_apps
                if app["canary"] and app["purchase_model"] == "paid_upfront"
            ],
            "free_iap_app_keys": [
                app["app_key"]
                for app in localized_apps
                if app["canary"]
                and app["purchase_model"] == "free_with_lifetime_unlock"
            ],
        },
        "counts": counts,
        "apps": localized_apps,
        "measurement": {
            "explanation": copy["measurement"],
            "scorecards": {
                str(days): scorecard_url(days)
                for days in manifest["measurement"]["scorecard_windows_days"]
            },
            "generated_rc_is_not_exposure": True,
            "ordinary_downloads_are_institutional": False,
        },
    }
    return _with_content_digest(payload)


def _primary_schema() -> dict[str, Any]:
    uri = {"type": "string", "format": "uri", "pattern": "^https://"}
    metric_false = {"type": "boolean", "const": False}
    return {
        "$schema": "https://json-schema.org/draft/2019-09/schema",
        "$id": schema_url(),
        "x-schema-version": 1,
        "title": "Lumi Studio institutional managed-app candidate roster",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "schema_version",
            "release_status",
            "deployment_status",
            "locale",
            "route_kind",
            "url",
            "generated_on",
            "source_digest",
            "roster_digest",
            "content_digest",
            "publisher",
            "disclosures",
            "official_references",
            "source_state",
            "workflow",
            "canary",
            "counts",
            "apps",
            "measurement",
        ],
        "properties": {
            "$schema": {"const": schema_url()},
            "schema_version": {"const": 1},
            "release_status": {"const": "CANDIDATE_NOT_DEPLOYED"},
            "deployment_status": {"const": "not_deployed"},
            "locale": {"enum": list(OFFICIAL_LOCALES)},
            "route_kind": {"enum": ["x-default", "localized"]},
            "url": uri,
            "generated_on": {"type": "string", "format": "date"},
            "source_digest": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
            "roster_digest": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
            "content_digest": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
            "publisher": {"type": "object"},
            "disclosures": {"type": "object"},
            "official_references": {
                "type": "array",
                "minItems": 4,
                "items": {"type": "object"},
            },
            "source_state": {"type": "object"},
            "workflow": {"type": "object"},
            "canary": {
                "type": "object",
                "required": ["status", "reason", "count", "app_keys"],
                "properties": {
                    "status": {
                        "const": "BLOCKED_PENDING_ADMIN_VERIFICATION"
                    },
                    "reason": {"type": "string", "minLength": 1},
                    "count": {"type": "integer", "minimum": 2, "maximum": 3},
                    "app_keys": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 3,
                        "uniqueItems": True,
                    },
                },
            },
            "counts": {
                "type": "object",
                "required": [
                    "apps",
                    "paid_upfront",
                    "free_to_start_with_iap",
                    "fully_free",
                    "ipad_supported",
                    "school_related",
                    "business_related",
                    "canary",
                ],
                "properties": {
                    "apps": {"const": 46},
                    "paid_upfront": {"type": "integer", "minimum": 0},
                    "free_to_start_with_iap": {
                        "type": "integer",
                        "minimum": 0,
                    },
                    "fully_free": {"type": "integer", "minimum": 0},
                    "ipad_supported": {"type": "integer", "minimum": 0},
                    "school_related": {"type": "integer", "minimum": 0},
                    "business_related": {"type": "integer", "minimum": 0},
                    "canary": {"type": "integer", "minimum": 2, "maximum": 3},
                },
                "additionalProperties": False,
            },
            "apps": {
                "type": "array",
                "minItems": 46,
                "maxItems": 46,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "app_key",
                        "app_store_id",
                        "bundle_id",
                        "public_name",
                        "canonical_app_store_url",
                        "campaign_app_store_url",
                        "campaign_attribution",
                        "platforms",
                        "ipad_supported",
                        "purchase_model",
                        "purchase_model_wording",
                        "download_model",
                        "unlock_model",
                        "deployment_class",
                        "publisher_query",
                        "decision_context",
                        "related_fit",
                        "canary",
                        "canary_status",
                        "institutional_policy",
                        "limitation",
                        "support_url",
                        "privacy_url",
                        "last_checked",
                        "lookup_provenance",
                        "verified_live",
                        "institutional_exposure_verified",
                        "institutional_approval_verified",
                        "discount_verified",
                    ],
                    "properties": {
                        "app_key": {"type": "string", "minLength": 1},
                        "app_store_id": {
                            "type": "string",
                            "pattern": "^\\d{9,12}$",
                        },
                        "bundle_id": {
                            "type": "string",
                            "pattern": "^[A-Za-z0-9][A-Za-z0-9.-]+$",
                        },
                        "public_name": {"type": "string", "minLength": 1},
                        "canonical_app_store_url": uri,
                        "campaign_app_store_url": uri,
                        "campaign_attribution": {"type": "object"},
                        "platforms": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"enum": ["iPhone", "iPad"]},
                        },
                        "ipad_supported": {"type": "boolean"},
                        "purchase_model": {
                            "enum": [
                                "paid_upfront",
                                "free_with_lifetime_unlock",
                            ]
                        },
                        "purchase_model_wording": {
                            "type": "string",
                            "minLength": 1,
                        },
                        "download_model": {
                            "enum": ["paid_download", "free_download"]
                        },
                        "unlock_model": {
                            "enum": [
                                "included_in_paid_download",
                                "optional_one_time_iap_individual_purchase",
                            ]
                        },
                        "deployment_class": {
                            "enum": [
                                "asm_apps_and_books_paid_candidate",
                                "intune_direct_store_free_tier_evaluation",
                            ]
                        },
                        "publisher_query": {"type": "string", "minLength": 1},
                        "decision_context": {"type": "string", "minLength": 1},
                        "related_fit": {
                            "type": "array",
                            "uniqueItems": True,
                            "items": {"enum": ["school", "business"]},
                        },
                        "canary": {"type": "boolean"},
                        "canary_status": {"type": "string", "minLength": 1},
                        "institutional_policy": {"type": "object"},
                        "limitation": {"type": "string", "minLength": 1},
                        "support_url": uri,
                        "privacy_url": uri,
                        "last_checked": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "lookup_provenance": {"type": "object"},
                        "verified_live": {"const": True},
                        "institutional_exposure_verified": metric_false,
                        "institutional_approval_verified": metric_false,
                        "discount_verified": metric_false,
                    },
                },
            },
            "measurement": {"type": "object"},
        },
    }


def _scorecard_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2019-09/schema",
        "$id": scorecard_schema_url(),
        "x-schema-version": 1,
        "title": "Institutional procurement read-only scorecard",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "schema_version",
            "release_status",
            "window_days",
            "window_start",
            "window_end",
            "content_digest",
            "privacy_rule",
            "stage_contract",
            "metrics",
        ],
        "properties": {
            "$schema": {"const": scorecard_schema_url()},
            "schema_version": {"const": 1},
            "release_status": {"const": "CANDIDATE_NOT_DEPLOYED"},
            "window_days": {"enum": [7, 28]},
            "window_start": {"type": "string", "format": "date"},
            "window_end": {"type": "string", "format": "date"},
            "content_digest": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
            "privacy_rule": {"type": "object"},
            "stage_contract": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {"type": "object"},
            },
            "metrics": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": [
                        "stage",
                        "value",
                        "status",
                        "source",
                        "is_institutional_outcome",
                    ],
                    "properties": {
                        "stage": {"type": "string"},
                        "value": {"type": "integer", "minimum": 0},
                        "status": {"enum": ["VERIFIED", "PENDING"]},
                        "source": {"type": "string"},
                        "is_institutional_outcome": {"type": "boolean"},
                    },
                },
            },
        },
    }


def _scorecard_payload(
    days: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    end = date.fromisoformat(str(manifest["candidate_date"]))
    start = end - timedelta(days=days - 1)
    stages = list(manifest["measurement"]["stages"])
    sources = {
        "inventory": "verified_live_catalog_plus_apple_public_get",
        "deployed": "candidate_not_deployed",
        "http_get": "deployment_http_logs_not_available",
        "qualified_click": (
            "no_client_tracking; first_party_aggregate_logs_not_available"
        ),
        "institutional_download": (
            "organization_specific_evidence_not_available; "
            "ordinary_asc_downloads_excluded"
        ),
    }
    payload = {
        "$schema": scorecard_schema_url(),
        "schema_version": 1,
        "release_status": manifest["release_status"],
        "window_days": days,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "content_digest": "",
        "privacy_rule": {
            "threshold": int(manifest["measurement"]["privacy_threshold"]),
            "values_1_to_4": "report_as_range_1_to_4_or_PENDING",
            "no_evidence": "0/PENDING",
            "search_console_and_asc": (
                "read_only_observed_lower_bounds_only; never infer exposure "
                "or institutional attribution"
            ),
        },
        "stage_contract": [
            {
                "stage": stage,
                "distinct_from_next_stage": index < len(stages) - 1,
            }
            for index, stage in enumerate(stages)
        ],
        "metrics": [
            {
                "stage": stage,
                "value": (
                    int(manifest["expected_app_count"])
                    if stage == "inventory"
                    else 0
                ),
                "status": "VERIFIED" if stage == "inventory" else "PENDING",
                "source": sources[stage],
                "is_institutional_outcome": (
                    stage == "institutional_download"
                ),
            }
            for stage in stages
        ],
    }
    return _with_content_digest(payload)


def _hreflang_links(app_key: str | None = None) -> str:
    url_for = (
        (lambda locale: app_page_url(locale, app_key))
        if app_key is not None
        else page_url
    )
    links = [
        (
            f'<link rel="alternate" hreflang="{html.escape(locale)}" '
            f'href="{html.escape(url_for(locale), quote=True)}">'
        )
        for locale in OFFICIAL_LOCALES
    ]
    links.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{html.escape(url_for(None), quote=True)}">'
    )
    return "\n".join(links)


def _copy_field(
    label: str,
    value: str,
    copy_label: str,
) -> str:
    escaped_value = html.escape(value)
    return (
        '<div class="field">'
        f"<dt>{html.escape(label)}</dt>"
        f'<dd><code>{escaped_value}</code>'
        f'<button type="button" class="copy" data-copy="{html.escape(value, quote=True)}">'
        f"{html.escape(copy_label)}</button></dd></div>"
    )


def _app_card(
    app: dict[str, Any],
    labels: dict[str, str],
    route_locale: str | None,
    link_detail: bool = True,
) -> str:
    fit = app["related_fit"]
    badges = [
        f'<span class="tag">{html.escape(value)}</span>'
        for value in app["platforms"]
    ]
    if fit:
        badges.extend(
            f'<span class="tag fit">{html.escape(labels[value])}</span>'
            for value in fit
        )
    else:
        badges.append(
            f'<span class="tag quiet">{html.escape(labels["not_shortlisted"])}</span>'
        )
    fields = [
        _copy_field(
            "App ID",
            str(app["app_store_id"]),
            labels["copy"],
        ),
        _copy_field(
            "Bundle ID",
            str(app["bundle_id"]),
            labels["copy"],
        ),
        _copy_field(
            "App Store URL",
            str(app["canonical_app_store_url"]),
            labels["copy"],
        ),
        _copy_field(
            labels["support"],
            str(app["support_url"]),
            labels["copy"],
        ),
        _copy_field(
            labels["privacy"],
            str(app["privacy_url"]),
            labels["copy"],
        ),
    ]
    links = (
        f'<a rel="nofollow noopener noreferrer" '
        f'href="{html.escape(str(app["campaign_app_store_url"]), quote=True)}">'
        "App Store</a> · "
        f'<a rel="noopener noreferrer" '
        f'href="{html.escape(str(app["support_url"]), quote=True)}">'
        f'{html.escape(labels["support"])}</a> · '
        f'<a rel="noopener noreferrer" '
        f'href="{html.escape(str(app["privacy_url"]), quote=True)}">'
        f'{html.escape(labels["privacy"])}</a>'
    )
    detail = (
        f'<p><a href="{html.escape(app_page_url(route_locale, str(app["app_key"])), quote=True)}">'
        f'{html.escape(str(app["public_name"]))}</a></p>'
        if link_detail
        else ""
    )
    return (
        f'<article class="app" id="app-{html.escape(str(app["app_store_id"]))}">'
        f'<div class="app-head"><div><h3>{html.escape(str(app["public_name"]))}</h3>'
        f'<p class="model">{html.escape(str(app["purchase_model_wording"]))}</p></div>'
        f'<div class="tags">{"".join(badges)}</div></div>'
        f'<h4>{html.escape(labels["purpose"])}</h4>'
        f'<p>{html.escape(str(app["publisher_query"]))}</p>'
        f'<p>{html.escape(str(app["decision_context"]))}</p>'
        f'<p><code>download={html.escape(str(app["download_model"]))}</code> · '
        f'<code>unlock={html.escape(str(app["unlock_model"]))}</code></p>'
        f'<p class="status">{html.escape(str(app["canary_status"]))}</p>'
        f'<div class="warning"><strong>{html.escape(labels["limits"])}:</strong> '
        f'{html.escape(str(app["limitation"]))}</div>'
        f'<dl>{"".join(fields)}</dl>'
        f'<p class="links">{links}</p>'
        f"{detail}"
        f'<p class="checked">{html.escape(labels["last_checked"])}: '
        f'{html.escape(str(app["last_checked"]))}</p>'
        "</article>"
    )


def _render_page(
    locale: str,
    route_locale: str | None,
    payload: dict[str, Any],
    copy: dict[str, Any],
    publisher_ui: dict[str, str],
    manifest: dict[str, Any],
) -> str:
    canonical = page_url(route_locale)
    canary_apps = [app for app in payload["apps"] if app["canary"]]
    paid_apps = [
        app
        for app in canary_apps
        if app["purchase_model"] == "paid_upfront"
    ]
    free_apps = [
        app
        for app in canary_apps
        if app["purchase_model"] == "free_with_lifetime_unlock"
    ]
    labels = copy["labels"]
    references = "\n".join(
        (
            f'<li><a rel="noopener noreferrer" '
            f'href="{html.escape(reference["url"], quote=True)}">'
            f'{html.escape(reference["publisher"])} — '
            f'{html.escape(reference["source_title"])}</a> '
            f'<code>{html.escape(reference["checked_on"])}</code> → '
            f'<code>{html.escape(reference["expires_on"])}</code></li>'
        )
        for reference in payload["official_references"]
    )
    steps = "\n".join(
        f"<li>{html.escape(str(step))}</li>" for step in copy["steps"]
    )
    paid_cards = "\n".join(
        _app_card(app, labels, route_locale) for app in paid_apps
    )
    free_cards = "\n".join(
        _app_card(app, labels, route_locale) for app in free_apps
    )
    direction = "rtl" if locale in RTL_LOCALES else "ltr"
    page_title = str(copy["title"])
    description = str(copy["intro"])
    paid_heading = publisher_ui[
        publisher_intent_catalog.PURCHASE_LABELS["paid_upfront"]
    ]
    free_heading = publisher_ui[
        publisher_intent_catalog.PURCHASE_LABELS[
            "free_with_lifetime_unlock"
        ]
    ]
    source_label = str(labels["source"])
    score_links = " · ".join(
        f'<a href="{html.escape(scorecard_url(days), quote=True)}">'
        f"{days}d JSON</a>"
        for days in (7, 28)
    )
    return f"""<!doctype html>
<html lang="{html.escape(locale)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(page_title)} | Lumi Studio</title>
<meta name="description" content="{html.escape(description, quote=True)}">
<meta name="robots" content="index,follow,max-snippet:-1">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
{_hreflang_links()}
<link rel="alternate" type="application/json" href="{html.escape(data_url(route_locale), quote=True)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{html.escape(open_graph_locale(locale))}">
<meta property="og:title" content="{html.escape(page_title, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:url" content="{html.escape(canonical, quote=True)}">
<style>
:root{{--bg:#f4f5f7;--card:#fff;--ink:#172033;--muted:#5f6877;--line:#d9dee8;--accent:#3056d3;--warn:#fff5d9;--fit:#e9f8ef}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
a{{color:#244cbe}}main{{width:min(1180px,94vw);margin:auto;padding:32px 0 72px}}.hero,.panel,.app{{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:0 12px 38px rgba(20,31,56,.06)}}
.hero{{padding:clamp(24px,5vw,56px);background:linear-gradient(145deg,#fff,#eef2ff)}}.status{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#e8ecf7;color:#39445e;font-size:.82rem;font-weight:700}}
h1{{font-size:clamp(2rem,5vw,4.4rem);line-height:1.02;letter-spacing:-.04em;margin:.55em 0 .35em}}.lead{{font-size:clamp(1.05rem,2vw,1.32rem);max-width:72ch}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}}.count,.tag{{border:1px solid var(--line);border-radius:999px;padding:6px 10px;background:#fff;font-size:.82rem}}
.panel{{padding:24px;margin-top:22px}}.warning{{background:var(--warn);border:1px solid #efd690;border-radius:14px;padding:14px;margin:14px 0}}
.workflow{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}.workflow section{{border:1px solid var(--line);border-radius:16px;padding:18px}}
.roster{{margin-top:34px}}.apps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:18px}}.app{{padding:20px;overflow:hidden}}
.app-head{{display:flex;gap:14px;align-items:flex-start;justify-content:space-between}}h3{{margin:0;font-size:1.28rem}}h4{{margin:18px 0 4px}}.model,.checked{{color:var(--muted);font-size:.9rem}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}}.tag.fit{{background:var(--fit)}}.tag.quiet{{background:#f2f3f6;color:var(--muted)}}dl{{margin:14px 0}}
.field{{border-top:1px solid var(--line);padding:10px 0}}dt{{font-weight:700;font-size:.84rem;color:var(--muted)}}dd{{margin:5px 0 0;display:flex;align-items:center;gap:8px}}code{{overflow-wrap:anywhere;font-size:.78rem}}
.copy{{margin-inline-start:auto;border:1px solid var(--line);border-radius:10px;background:#fff;padding:7px 10px;cursor:pointer}}.copy:focus-visible{{outline:3px solid #9bb2ff}}.links{{overflow-wrap:anywhere}}
footer{{margin-top:30px;color:var(--muted)}}@media (prefers-color-scheme:dark){{:root{{--bg:#10131b;--card:#181d29;--ink:#f3f5fb;--muted:#aab3c4;--line:#30394b;--warn:#3c321c;--fit:#173a29}}.hero{{background:linear-gradient(145deg,#1a2030,#171a26)}}.count,.tag,.copy{{background:#202737}}}}
</style>
</head>
<body><main>
<header class="hero">
<span class="status">BLOCKED · CANDIDATE_NOT_DEPLOYED</span>
<h1>{html.escape(page_title)}</h1>
<p class="lead">{html.escape(description)}</p>
<div class="warning">{html.escape(str(copy["disclosure"]))}</div>
<div class="counts">
<span class="count">46 · {html.escape(str(labels["roster"]))}</span>
<span class="count">{len(canary_apps)} / 46 · BLOCKED</span>
<span class="count">{len(paid_apps)} {html.escape(paid_heading)}</span>
<span class="count">{len(free_apps)} {html.escape(free_heading)}</span>
<span class="count">50 locales</span>
</div>
</header>
<section class="panel">
<h2>{html.escape(str(copy["title"]))}</h2>
<div class="workflow">
<section><h3>{html.escape(paid_heading)}</h3><p>{html.escape(str(copy["paid"]))}</p></section>
<section><h3>{html.escape(free_heading)}</h3><p>{html.escape(str(copy["direct"]))}</p></section>
</div>
<div class="warning"><strong>IAP:</strong> {html.escape(str(copy["iap"]))}</div>
<ol>{steps}</ol>
</section>
<section class="panel">
<h2>{html.escape(str(labels["school"]))} / {html.escape(str(labels["business"]))}</h2>
<p>{html.escape(str(copy["fit"]))}</p>
</section>
<section class="panel">
<h2>7d / 28d</h2>
<p>{html.escape(str(copy["measurement"]))}</p>
<p>{score_links}</p>
</section>
<section class="panel">
<h2>{html.escape(source_label)}</h2>
<ul>{references}</ul>
<p>{html.escape(str(payload["disclosures"]["public_lookup_scope"]))}</p>
</section>
<section class="roster">
<h2>{html.escape(str(labels["roster"]))} · 46</h2>
<p><a href="{html.escape(data_url(route_locale), quote=True)}">JSON inventory</a></p>
<h2>{len(canary_apps)} / 46 · BLOCKED</h2>
<h2>{html.escape(paid_heading)} · {len(paid_apps)}</h2>
<div class="apps">{paid_cards}</div>
<h2>{html.escape(free_heading)} · {len(free_apps)}</h2>
<div class="warning">{html.escape(str(copy["iap"]))}</div>
<div class="apps">{free_cards}</div>
</section>
<footer>
<p>{html.escape(str(copy["disclosure"]))}</p>
<p>{html.escape(str(labels["support"]))}: <a href="mailto:{ALLOWED_EMAIL}">{ALLOWED_EMAIL}</a></p>
<p>Roster digest: <code>{html.escape(str(payload["roster_digest"]))}</code></p>
</footer>
</main>
<script>
document.addEventListener("click",async event=>{{
  const button=event.target.closest("button[data-copy]");
  if(!button)return;
  const original=button.textContent;
  try{{
    await navigator.clipboard.writeText(button.dataset.copy);
    button.textContent={json.dumps(labels["copied"], ensure_ascii=False)};
    window.setTimeout(()=>{{button.textContent=original}},1200);
  }}catch(_error){{button.textContent=original}}
}});
</script>
</body></html>
"""


def _render_app_page(
    locale: str,
    route_locale: str | None,
    app: dict[str, Any],
    payload: dict[str, Any],
    copy: dict[str, Any],
) -> str:
    app_key = str(app["app_key"])
    canonical = app_page_url(route_locale, app_key)
    labels = copy["labels"]
    references = "\n".join(
        (
            f'<li><a rel="noopener noreferrer" '
            f'href="{html.escape(reference["url"], quote=True)}">'
            f'{html.escape(reference["publisher"])} — '
            f'{html.escape(reference["source_title"])}</a> '
            f'<code>{html.escape(reference["checked_on"])}</code> → '
            f'<code>{html.escape(reference["expires_on"])}</code></li>'
        )
        for reference in payload["official_references"]
    )
    if app["purchase_model"] == "paid_upfront":
        policy_heading = (
            f'Apps and Books · {app["purchase_model_wording"]}'
        )
        policy_body = str(copy["paid"])
    else:
        policy_heading = "NOT_APPLICABLE · IAP volume unlock"
        policy_body = f'{copy["direct"]} {copy["iap"]}'
    direction = "rtl" if locale in RTL_LOCALES else "ltr"
    title = f'{app["public_name"]} · {copy["title"]}'
    return f"""<!doctype html>
<html lang="{html.escape(locale)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} | Lumi Studio</title>
<meta name="description" content="{html.escape(str(copy["intro"]), quote=True)}">
<meta name="robots" content="index,follow,max-snippet:-1">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
{_hreflang_links(app_key)}
<link rel="alternate" type="application/json" href="{html.escape(data_url(route_locale), quote=True)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="{html.escape(open_graph_locale(locale))}">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(str(copy["intro"]), quote=True)}">
<meta property="og:url" content="{html.escape(canonical, quote=True)}">
<style>
:root{{--bg:#f4f5f7;--card:#fff;--ink:#172033;--muted:#5f6877;--line:#d9dee8;--warn:#fff5d9;--accent:#3056d3;--fit:#e9f8ef}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
a{{color:#244cbe}}main{{width:min(920px,94vw);margin:auto;padding:32px 0 72px}}.hero,.panel,.app{{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:0 12px 38px rgba(20,31,56,.06)}}
.hero{{padding:clamp(24px,5vw,48px);background:linear-gradient(145deg,#fff,#eef2ff)}}.panel,.app{{padding:22px;margin-top:22px}}.status{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#e8ecf7;color:#39445e;font-size:.82rem;font-weight:700}}
h1{{font-size:clamp(2rem,5vw,3.6rem);line-height:1.05;letter-spacing:-.035em;margin:.55em 0 .35em}}.warning{{background:var(--warn);border:1px solid #efd690;border-radius:14px;padding:14px;margin:14px 0}}
.app-head{{display:flex;gap:14px;align-items:flex-start;justify-content:space-between}}h3{{margin:0;font-size:1.28rem}}h4{{margin:18px 0 4px}}.model,.checked{{color:var(--muted);font-size:.9rem}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}}.tag{{border:1px solid var(--line);border-radius:999px;padding:6px 10px;background:#fff;font-size:.82rem}}.tag.fit{{background:var(--fit)}}.tag.quiet{{background:#f2f3f6;color:var(--muted)}}dl{{margin:14px 0}}
.field{{border-top:1px solid var(--line);padding:10px 0}}dt{{font-weight:700;font-size:.84rem;color:var(--muted)}}dd{{margin:5px 0 0;display:flex;align-items:center;gap:8px}}code{{overflow-wrap:anywhere;font-size:.78rem}}
.copy{{margin-inline-start:auto;border:1px solid var(--line);border-radius:10px;background:#fff;padding:7px 10px;cursor:pointer}}footer{{margin-top:28px;color:var(--muted)}}@media (prefers-color-scheme:dark){{:root{{--bg:#10131b;--card:#181d29;--ink:#f3f5fb;--muted:#aab3c4;--line:#30394b;--warn:#3c321c;--fit:#173a29}}.hero{{background:linear-gradient(145deg,#1a2030,#171a26)}}.tag,.copy{{background:#202737}}}}
</style>
</head>
<body><main>
<header class="hero">
<span class="status">{html.escape(str(app["canary_status"]))}</span>
<h1>{html.escape(str(app["public_name"]))}</h1>
<p>{html.escape(str(copy["intro"]))}</p>
<div class="warning">{html.escape(str(copy["disclosure"]))}</div>
</header>
{_app_card(app, labels, route_locale, link_detail=False)}
<section class="panel">
<h2>{html.escape(policy_heading)}</h2>
<p>{html.escape(policy_body)}</p>
<p>{html.escape(str(copy["disclosure"]))}</p>
</section>
<section class="panel">
<h2>App Store · pt / ct / mt</h2>
<p><code>pt={html.escape(str(app["campaign_attribution"]["provider_token"]))}</code> · <code>ct={html.escape(str(app["campaign_attribution"]["campaign_token"]))}</code> · <code>mt=8</code></p>
</section>
<section class="panel"><h2>{html.escape(str(labels["source"]))}</h2><ul>{references}</ul></section>
<footer>
<p><a href="{html.escape(page_url(route_locale), quote=True)}">{html.escape(str(copy["title"]))}</a></p>
<p>{html.escape(str(labels["support"]))}: <a href="mailto:{ALLOWED_EMAIL}">{ALLOWED_EMAIL}</a></p>
<p>{html.escape(str(copy["disclosure"]))}</p>
</footer>
</main>
<script>
document.addEventListener("click",async event=>{{
  const button=event.target.closest("button[data-copy]");
  if(!button)return;
  const original=button.textContent;
  try{{
    await navigator.clipboard.writeText(button.dataset.copy);
    button.textContent={json.dumps(labels["copied"], ensure_ascii=False)};
    window.setTimeout(()=>{{button.textContent=original}},1200);
  }}catch(_error){{button.textContent=original}}
}});
</script>
</body></html>
"""


def _render_sitemap(modified: str, canary_keys: tuple[str, ...]) -> str:
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("xhtml", XHTML_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    routes: list[str | None] = [None, *OFFICIAL_LOCALES]
    for route_locale in routes:
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = page_url(route_locale)
        ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = modified
        alternates = [
            (locale, page_url(locale)) for locale in OFFICIAL_LOCALES
        ] + [("x-default", page_url(None))]
        for hreflang, href in alternates:
            node = ET.SubElement(url, f"{{{XHTML_NS}}}link")
            node.set("rel", "alternate")
            node.set("hreflang", hreflang)
            node.set("href", href)
    for app_key in canary_keys:
        alternates = [
            (locale, app_page_url(locale, app_key))
            for locale in OFFICIAL_LOCALES
        ] + [("x-default", app_page_url(None, app_key))]
        for route_locale in routes:
            url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
            ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = app_page_url(
                route_locale,
                app_key,
            )
            ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = modified
            for hreflang, href in alternates:
                node = ET.SubElement(url, f"{{{XHTML_NS}}}link")
                node.set("rel", "alternate")
                node.set("hreflang", hreflang)
                node.set("href", href)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root,
        encoding="unicode",
    ) + "\n"


def _block_markers(name: str) -> tuple[str, str]:
    if name == "robots":
        return (
            "# institutional-procurement:start",
            "# institutional-procurement:end",
        )
    return (
        "<!-- institutional-procurement:start -->",
        "<!-- institutional-procurement:end -->",
    )


def _managed_block(name: str, body: str) -> str:
    start, end = _block_markers(name)
    return f"{start}\n{body.rstrip()}\n{end}"


def _extract_block(source: str, name: str) -> str | None:
    start, end = _block_markers(name)
    count = source.count(start) + source.count(end)
    if count == 0:
        return None
    if source.count(start) != 1 or source.count(end) != 1:
        raise BlockedNotDeployable(f"Duplicate shared marker: {name}")
    begin = source.index(start)
    finish = source.index(end, begin) + len(end)
    return source[begin:finish]


def _upsert_block(
    source: str,
    name: str,
    block: str,
    anchor: str | None,
) -> str:
    existing = _extract_block(source, name)
    if existing is not None:
        return source.replace(existing, block, 1)
    if anchor is None:
        separator = "" if source.endswith("\n") else "\n"
        return f"{source}{separator}{block}\n"
    if source.count(anchor) != 1:
        raise BlockedNotDeployable(
            f"Shared insertion anchor differs for {name}: {anchor}"
        )
    return source.replace(anchor, f"{block}\n{anchor}", 1)


def _shared_updates(
    pages: Path,
    modified: str,
) -> tuple[dict[Path, str], dict[str, str]]:
    app_link = _managed_block(
        "apps-index",
        (
            '<section class="section" id="institutional-procurement">'
            "<h2>Institutional iOS procurement preflight</h2>"
            "<p>Administrator reference for Apple School Manager, Apple "
            "Business Manager and Microsoft Intune. First-party, non-ranking, "
            "and not proof of institutional catalogue visibility.</p>"
            '<p><a href="../institutional/ios-procurement.html">'
            "Open the institutional procurement reference</a></p></section>"
        ),
    )
    robots = _managed_block(
        "robots",
        f"Sitemap: {sitemap_url()}",
    )
    sitemap_index = _managed_block(
        "sitemap-index",
        (
            f"  <sitemap><loc>{html.escape(sitemap_url())}</loc>"
            f"<lastmod>{modified}</lastmod></sitemap>"
        ),
    )
    specs = {
        Path("apps/index.html"): ("apps-index", app_link, "</main>"),
        Path("robots.txt"): ("robots", robots, None),
        Path("sitemap_index.xml"): (
            "sitemap-index",
            sitemap_index,
            "</sitemapindex>",
        ),
    }
    updates: dict[Path, str] = {}
    block_hashes: dict[str, str] = {}
    for relative, (name, block, anchor) in specs.items():
        source = (pages / relative).read_text(encoding="utf-8")
        updated = _upsert_block(source, name, block, anchor)
        updates[relative] = updated
        block_hashes[name] = _sha256_text(block)
    return updates, block_hashes


def _state_payload(
    manifest: dict[str, Any],
    source_digest: str,
    roster_digest: str,
    outputs: dict[Path, str],
    shared_block_hashes: dict[str, str],
) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "release_status": manifest["release_status"],
        "generated_on": manifest["candidate_date"],
        "source_digest": source_digest,
        "roster_digest": roster_digest,
        "content_digest": "",
        "managed_outputs": {
            path.as_posix(): f"sha256:{_sha256_text(content)}"
            for path, content in sorted(
                outputs.items(),
                key=lambda item: item[0].as_posix(),
            )
        },
        "shared_blocks": {
            key: f"sha256:{value}"
            for key, value in sorted(shared_block_hashes.items())
        },
    }
    return _with_content_digest(payload)


def _verify_existing_state(pages: Path) -> None:
    path = pages / STATE_PATH
    if not path.exists():
        return
    state = _read_json(path)
    expected_digest = str(state.get("content_digest", ""))
    normalized = deepcopy(state)
    normalized.pop("content_digest", None)
    if expected_digest != f"sha256:{_canonical_digest(normalized)}":
        raise BlockedNotDeployable("Generation state self-digest differs")
    outputs = state.get("managed_outputs")
    if not isinstance(outputs, dict):
        raise BlockedNotDeployable("Generation state has no managed outputs")
    for relative, expected in outputs.items():
        output = pages / relative
        if not output.is_file():
            raise BlockedNotDeployable(f"Managed output disappeared: {relative}")
        actual = f"sha256:{_sha256_bytes(output.read_bytes())}"
        if actual != expected:
            raise BlockedNotDeployable(
                f"CAS mismatch for managed output: {relative}"
            )
    shared = state.get("shared_blocks")
    shared_files = {
        "apps-index": Path("apps/index.html"),
        "robots": Path("robots.txt"),
        "sitemap-index": Path("sitemap_index.xml"),
    }
    if not isinstance(shared, dict):
        raise BlockedNotDeployable("Generation state has no shared block hashes")
    for name, relative in shared_files.items():
        source = (pages / relative).read_text(encoding="utf-8")
        block = _extract_block(source, name)
        if block is None:
            raise BlockedNotDeployable(f"Shared managed block disappeared: {name}")
        if f"sha256:{_sha256_text(block)}" != shared.get(name):
            raise BlockedNotDeployable(f"CAS mismatch for shared block: {name}")


def _scan_output_safety(
    outputs: dict[Path, str],
    manifest: dict[str, Any],
) -> None:
    combined = "\n".join(outputs.values())
    if OLD_EMAIL.casefold() in combined.casefold():
        raise BlockedNotDeployable("Legacy Hotmail address reached outputs")
    emails = {match.casefold() for match in EMAIL_RE.findall(combined)}
    if emails - {ALLOWED_EMAIL}:
        raise BlockedNotDeployable(
            f"Unexpected public email in outputs: {sorted(emails)}"
        )
    folded = combined.casefold()
    for fragment in manifest["prohibited_claim_fragments"]:
        if str(fragment).casefold() in folded:
            raise BlockedNotDeployable(
                f"Invented institutional claim reached outputs: {fragment}"
            )
    if re.search(
        r'(?i)"(?:price|rating|review_count|discount|institutional_price)"\s*:',
        combined,
    ):
        raise BlockedNotDeployable("Price, rating or discount field reached outputs")
    if re.search(
        r"(?i)<script[^>]+src=|<iframe|fetch\s*\(|XMLHttpRequest|sendBeacon|"
        r"localStorage|sessionStorage|document\.cookie",
        combined,
    ):
        raise BlockedNotDeployable("Tracking or third-party script reached outputs")


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _build_outputs(
    pages: Path,
) -> tuple[
    dict[Path, str],
    dict[Path, str],
    dict[str, Any],
]:
    manifest = _load_manifest(pages)
    i18n = _load_i18n()
    apps, lookup, intents, source_context = _load_sources(pages, manifest)
    related_fit = _validate_related_fit(manifest, apps, intents)
    canary_keys = _validate_canary(manifest, apps, related_fit)
    publisher_ui = _publisher_ui()
    source_digest = _source_digest(manifest)
    roster_digest = _roster_digest(apps, lookup)
    outputs: dict[Path, str] = {}
    routes: list[tuple[str, str | None]] = [
        ("en-US", None),
        *((locale, locale) for locale in OFFICIAL_LOCALES),
    ]
    for locale, route_locale in routes:
        payload = _data_payload(
            locale,
            route_locale,
            apps,
            lookup,
            intents,
            related_fit,
            manifest,
            source_context,
            i18n[locale],
            publisher_ui[locale],
            source_digest,
            roster_digest,
            canary_keys,
        )
        outputs[data_relative(route_locale)] = (
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        outputs[page_relative(route_locale)] = _render_page(
            locale,
            route_locale,
            payload,
            i18n[locale],
            publisher_ui[locale],
            manifest,
        )
        apps_by_key = {
            str(app["app_key"]): app for app in payload["apps"]
        }
        for app_key in canary_keys:
            outputs[app_page_relative(route_locale, app_key)] = _render_app_page(
                locale,
                route_locale,
                apps_by_key[app_key],
                payload,
                i18n[locale],
            )
    outputs[ROOT_DIR / SCHEMA_NAME] = (
        json.dumps(_primary_schema(), ensure_ascii=False, indent=2) + "\n"
    )
    outputs[ROOT_DIR / SCORECARD_SCHEMA_NAME] = (
        json.dumps(_scorecard_schema(), ensure_ascii=False, indent=2) + "\n"
    )
    for days, name in SCORECARD_NAMES.items():
        outputs[ROOT_DIR / name] = (
            json.dumps(
                _scorecard_payload(days, manifest),
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    outputs[Path(SITEMAP_NAME)] = _render_sitemap(
        str(manifest["candidate_date"]),
        canary_keys,
    )
    shared, block_hashes = _shared_updates(
        pages,
        str(manifest["candidate_date"]),
    )
    _scan_output_safety({**outputs, **shared}, manifest)
    state = _state_payload(
        manifest,
        source_digest,
        roster_digest,
        outputs,
        block_hashes,
    )
    outputs[STATE_PATH] = json.dumps(
        state,
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    summary = {
        "manifest": manifest,
        "apps": len(apps),
        "locales": len(OFFICIAL_LOCALES),
        "html_pages": (1 + len(OFFICIAL_LOCALES)) * (1 + len(canary_keys)),
        "localized_roster_json": 1 + len(OFFICIAL_LOCALES),
        "json_files": (
            1
            + len(OFFICIAL_LOCALES)
            + 2
            + 2
            + 1
        ),
        "paid_upfront": sum(
            app["purchase_model"] == "paid_upfront" for app in apps
        ),
        "free_to_start_with_iap": sum(
            app["purchase_model"] == "free_with_lifetime_unlock"
            for app in apps
        ),
        "school_related": len(manifest["related_fit"]["school"]),
        "business_related": len(manifest["related_fit"]["business"]),
        "canary": len(canary_keys),
        "roster_digest": roster_digest,
    }
    return outputs, shared, summary


def build(pages: Path = PAGES, check: bool = False) -> dict[str, Any]:
    _verify_existing_state(pages)
    outputs, shared, summary = _build_outputs(pages)
    state_content = outputs[STATE_PATH]
    if check:
        mismatches = []
        for relative, expected in outputs.items():
            path = pages / relative
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                mismatches.append(relative.as_posix())
        for relative, expected in shared.items():
            path = pages / relative
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                mismatches.append(relative.as_posix())
        if mismatches:
            raise BlockedNotDeployable(
                "Generated outputs differ: " + ", ".join(mismatches[:12])
            )
        return summary

    changed = 0
    for relative, content in outputs.items():
        if relative == STATE_PATH:
            continue
        changed += _write_if_changed(pages / relative, content)
    for relative, content in shared.items():
        changed += _write_if_changed(pages / relative, content)
    changed += _write_if_changed(pages / STATE_PATH, state_content)
    summary["changed_files"] = changed
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        summary = build(args.pages.resolve(), check=args.check)
    except (BlockedNotDeployable, ValueError, KeyError, TypeError) as error:
        print(f"BLOCKED_NOT_DEPLOYABLE {error}", file=sys.stderr)
        return 2
    print(
        "INSTITUTIONAL_PROCUREMENT "
        f"status={summary['manifest']['release_status']} "
        f"apps={summary['apps']} locales={summary['locales']} "
        f"html={summary['html_pages']} json={summary['json_files']} "
        f"paid={summary['paid_upfront']} "
        f"free_iap={summary['free_to_start_with_iap']} "
        f"school={summary['school_related']} "
        f"business={summary['business_related']} "
        f"canary={summary['canary']} "
        f"roster={summary['roster_digest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
