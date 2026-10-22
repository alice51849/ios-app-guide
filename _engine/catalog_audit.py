#!/usr/bin/env python3
"""Fail-closed audit for automatic app registry and localization sources.

CI may audit GrowthEngine alone with ``python3 catalog_audit.py`` or include
the Guide input mirror with ``--guide-root /path/to/guide/geo/pages``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Iterable, Mapping
import urllib.parse


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "geo"))
sys.path.insert(0, str(ROOT / "social"))

from answer_personas import PENDING_PERSONAS, PERSONAS  # noqa: E402

# A persona staged ahead of publication counts here. This audit is the gate
# that decides whether a newly public app may enter the registry at all, and
# the reviewed persona is written before that happens by design.
REVIEWED_PERSONAS = {**PERSONAS, **PENDING_PERSONAS}
from app_store_storefronts import LOCALE_STOREFRONTS  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402


AUTO_REGISTRY = ROOT / "social" / "videogen" / "registry_auto.json"
DATA_ROOT = ROOT / "data"
EXPECTED_LOCALE_COUNT = 50
KEY_RE = re.compile(r"[a-z0-9]+")
APP_ID_RE = re.compile(r"\d{8,}")
STORE_URL_RE = re.compile(r"https://apps\.apple\.com/app/id(\d{8,})")
CAMPAIGN_KEY_RE = re.compile(r"i18n:([a-z0-9]+):(.+)")
CAMPAIGN_STORE_PATH_RE = re.compile(
    r"/(?:(?P<country>[a-z]{2})/)?app/id(?P<app_id>\d{8,})"
)
STOP_WORDS = {
    "the",
    "app",
    "pro",
    "lite",
    "free",
    "kids",
    "my",
    "ios",
    "iphone",
}
REQUIRED_LOCALIZATION_FIELDS = (
    "name",
    "subtitle",
    "description",
    "keywords",
    "promotionalText",
)


class CatalogAuditError(RuntimeError):
    """The candidate catalog is incomplete or internally inconsistent."""


def _single_line(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def _campaign_store_identity(value: object) -> tuple[str | None, str]:
    if not isinstance(value, str) or not value.strip():
        raise CatalogAuditError("Threads campaign text must be non-empty")
    urls = [
        match.group(0).rstrip(".,!?;:，。！？；：)]}")
        for match in re.finditer(r"https?://\S+", value)
    ]
    store_urls = [
        url
        for url in urls
        if urllib.parse.urlsplit(url).hostname == "apps.apple.com"
    ]
    if len(store_urls) != 1:
        raise CatalogAuditError(
            "Threads campaign must contain exactly one direct App Store URL"
        )
    parsed = urllib.parse.urlsplit(store_urls[0])
    path = CAMPAIGN_STORE_PATH_RE.fullmatch(parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "apps.apple.com"
        or path is None
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port is not None
    ):
        raise CatalogAuditError("Threads campaign App Store URL is invalid")
    return path.group("country"), path.group("app_id")


def persona_keywords(
    key: str,
    name: str,
    *,
    personas: Mapping[str, list[dict[str, object]]] = REVIEWED_PERSONAS,
    limit: int = 6,
) -> list[str]:
    """Return deterministic demand phrases from an explicitly reviewed persona."""
    phrases: list[str] = []
    brand_words = {
        word
        for word in re.findall(r"[a-z0-9]+", (name or "").lower())
        if word not in STOP_WORDS
    }
    for persona in personas.get(key, []):
        candidates = list(persona.get("triggers") or [])
        if persona.get("query"):
            candidates.append(persona["query"])
        for candidate in candidates:
            normalized = _single_line(candidate)
            words = set(re.findall(r"[a-z0-9]+", normalized)) - STOP_WORDS
            if (
                not normalized
                or len(normalized) > 80
                or not words
                or words <= brand_words
                or normalized in phrases
            ):
                continue
            phrases.append(normalized)
            if len(phrases) == limit:
                return phrases
    return phrases


def _json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogAuditError(f"Missing {label}: {path}") from error
    except json.JSONDecodeError as error:
        raise CatalogAuditError(f"Invalid JSON in {label}: {path}") from error
    if not isinstance(value, dict):
        raise CatalogAuditError(f"{label} must be a JSON object: {path}")
    return value


def _json_array(path: Path, label: str) -> list[object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogAuditError(f"Missing {label}: {path}") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CatalogAuditError(f"Invalid JSON in {label}: {path}") from error
    if not isinstance(value, list):
        raise CatalogAuditError(f"{label} must be a JSON array: {path}")
    return value


def _target_keys(
    registry: Mapping[str, object],
    keys: Iterable[str] | None,
) -> list[str]:
    selected = sorted(set(keys) if keys is not None else set(registry))
    missing = sorted(set(selected) - set(registry))
    if missing:
        raise CatalogAuditError(
            "Catalog keys are missing from registry: " + ", ".join(missing)
        )
    return selected


def validate_registry(
    registry: Mapping[str, object],
    *,
    keys: Iterable[str] | None = None,
    expected_identities: Mapping[str, str] | None = None,
    personas: Mapping[str, list[dict[str, object]]] = REVIEWED_PERSONAS,
    strict_review_keys: Iterable[str] = (),
) -> list[str]:
    """Validate identity and reviewed-persona contracts without writing files."""
    selected = _target_keys(registry, keys)
    strict = set(strict_review_keys)
    unexpected_strict = sorted(strict - set(selected))
    if unexpected_strict:
        raise CatalogAuditError(
            "Strict review keys are outside the audit selection: "
            + ", ".join(unexpected_strict)
        )

    identities: dict[str, str] = {}
    for key, raw_entry in registry.items():
        if KEY_RE.fullmatch(key) is None or not isinstance(raw_entry, dict):
            raise CatalogAuditError(f"Invalid automatic registry entry: {key!r}")
        app_id = str(raw_entry.get("appstore_id") or "")
        if APP_ID_RE.fullmatch(app_id) is None:
            raise CatalogAuditError(f"Invalid App Store identity for {key}: {app_id!r}")
        previous = identities.get(app_id)
        if previous is not None:
            raise CatalogAuditError(
                f"Duplicate App Store identity {app_id}: {previous}, {key}"
            )
        identities[app_id] = key

    expected_identities = expected_identities or {}
    for key in selected:
        entry = registry[key]
        assert isinstance(entry, dict)
        app_id = str(entry["appstore_id"])
        expected_id = expected_identities.get(key)
        if expected_id is not None and app_id != str(expected_id):
            raise CatalogAuditError(
                f"Live identity mismatch for {key}: expected {expected_id}, got {app_id}"
            )
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise CatalogAuditError(f"Registry name is missing for {key}")
        expected_keywords = persona_keywords(key, name, personas=personas)
        if len(expected_keywords) < 3:
            raise CatalogAuditError(
                f"Reviewed buyer persona is missing or incomplete for {key}"
            )

        source = entry.get("keyword_source")
        if source == "pending_persona_review":
            raise CatalogAuditError(f"Buyer persona review is still pending for {key}")
        if source not in {None, "reviewed_persona"}:
            raise CatalogAuditError(f"Invalid keyword source for {key}: {source!r}")
        if key in strict and source != "reviewed_persona":
            raise CatalogAuditError(
                f"Explicit reviewed_persona marker is required for {key}"
            )

        keywords = entry.get("keywords")
        if not isinstance(keywords, list):
            raise CatalogAuditError(f"Reviewed keywords must be a list for {key}")
        normalized = [_single_line(value) for value in keywords]
        if (
            len(normalized) < 3
            or any(not value for value in normalized)
            or len(set(normalized)) != len(normalized)
        ):
            raise CatalogAuditError(
                f"At least three unique reviewed keywords are required for {key}"
            )
        if source == "reviewed_persona" and normalized != expected_keywords:
            raise CatalogAuditError(
                f"Reviewed keywords do not match the buyer persona for {key}"
            )
    return selected


def validate_localizations(
    key: str,
    document: Mapping[str, object],
    *,
    official_locales: Iterable[str] = OFFICIAL_LOCALES,
) -> None:
    """Require the exact official locale set and complete metadata fields."""
    official_locales = tuple(official_locales)
    expected = set(official_locales)
    if (
        len(official_locales) != EXPECTED_LOCALE_COUNT
        or len(expected) != EXPECTED_LOCALE_COUNT
    ):
        raise CatalogAuditError(
            "Official locale contract must contain exactly "
            f"{EXPECTED_LOCALE_COUNT} unique locales"
        )
    actual = set(document)
    if actual != expected:
        raise CatalogAuditError(
            f"{key} must have exactly {len(expected)} official locales; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    for locale in official_locales:
        entry = document.get(locale)
        if not isinstance(entry, dict):
            raise CatalogAuditError(f"Invalid localization object: {key}/{locale}")
        missing_fields = [
            field
            for field in REQUIRED_LOCALIZATION_FIELDS
            if not isinstance(entry.get(field), str) or not entry[field].strip()
        ]
        if missing_fields:
            raise CatalogAuditError(
                f"Incomplete localization {key}/{locale}: "
                + ", ".join(missing_fields)
            )


def _localization_projection(
    key: str,
    document: Mapping[str, object],
    *,
    official_locales: Iterable[str] = OFFICIAL_LOCALES,
) -> dict[str, dict[str, str]]:
    """Return the canonical ASC fields while allowing Guide-only enrichment."""
    official_locales = tuple(official_locales)
    validate_localizations(
        key,
        document,
        official_locales=official_locales,
    )
    return {
        locale: {
            field: str(document[locale][field])
            for field in REQUIRED_LOCALIZATION_FIELDS
        }
        for locale in official_locales
    }


def audit_catalog_documents(
    registry: Mapping[str, object],
    source_paths: Mapping[str, Path],
    *,
    keys: Iterable[str] | None = None,
    expected_identities: Mapping[str, str] | None = None,
    personas: Mapping[str, list[dict[str, object]]] = REVIEWED_PERSONAS,
    strict_review_keys: Iterable[str] = (),
    official_locales: Iterable[str] = OFFICIAL_LOCALES,
) -> dict[str, int]:
    """Audit in-memory registry plus candidate source files."""
    official_locales = tuple(official_locales)
    selected = validate_registry(
        registry,
        keys=keys,
        expected_identities=expected_identities,
        personas=personas,
        strict_review_keys=strict_review_keys,
    )
    for key in selected:
        path = source_paths.get(key)
        if path is None:
            raise CatalogAuditError(f"Localization source path is missing for {key}")
        validate_localizations(
            key,
            _json_object(Path(path), f"localization source for {key}"),
            official_locales=official_locales,
        )
    return {"apps": len(selected), "locales": len(official_locales)}


def audit_catalog_paths(
    registry_path: Path = AUTO_REGISTRY,
    data_root: Path = DATA_ROOT,
    *,
    guide_root: Path | None = None,
    keys: Iterable[str] | None = None,
    expected_identities: Mapping[str, str] | None = None,
    personas: Mapping[str, list[dict[str, object]]] = REVIEWED_PERSONAS,
    strict_review_keys: Iterable[str] = (),
    official_locales: Iterable[str] = OFFICIAL_LOCALES,
) -> dict[str, int]:
    """Audit checked-in sources and, optionally, their Guide mirror."""
    registry_path = Path(registry_path)
    data_root = Path(data_root)
    registry = _json_object(registry_path, "automatic registry")
    selected = _target_keys(registry, keys)
    source_paths = {
        key: data_root / f"{key}_full.json"
        for key in selected
    }
    result = audit_catalog_documents(
        registry,
        source_paths,
        keys=selected,
        expected_identities=expected_identities,
        personas=personas,
        strict_review_keys=strict_review_keys,
        official_locales=official_locales,
    )

    if guide_root is not None:
        guide_root = Path(guide_root)
        mirror_registry = (
            guide_root
            / "_engine"
            / "social"
            / "videogen"
            / "registry_auto.json"
        )
        if (
            not mirror_registry.is_file()
            or mirror_registry.read_bytes() != registry_path.read_bytes()
        ):
            raise CatalogAuditError(
                "Guide registry mirror differs from the canonical registry: "
                f"{mirror_registry}"
            )
        for key, source in source_paths.items():
            mirror = guide_root / "_engine" / "data" / source.name
            source_document = _json_object(
                source, f"localization source for {key}"
            )
            source_projection = _localization_projection(
                key,
                source_document,
                official_locales=official_locales,
            )
            try:
                mirror_document = _json_object(
                    mirror, f"Guide localization mirror for {key}"
                )
                mirror_projection = _localization_projection(
                    key,
                    mirror_document,
                    official_locales=official_locales,
                )
            except CatalogAuditError as error:
                raise CatalogAuditError(
                    f"Guide localization mirror differs for {key}: {mirror}"
                ) from error
            if mirror_projection != source_projection:
                raise CatalogAuditError(
                    f"Guide localization mirror differs for {key}: {mirror}"
                )
        result["mirrors"] = len(selected) + 1
    else:
        result["mirrors"] = 0
    return result


def _verified_live_keys(
    live_state: Mapping[str, object],
    *,
    apps: Mapping[str, Mapping[str, object]],
    appstore: Mapping[str, object],
) -> list[str]:
    live_ids = live_state.get("live_ids")
    if (
        not isinstance(live_ids, list)
        or not live_ids
        or any(APP_ID_RE.fullmatch(str(value)) is None for value in live_ids)
        or len({str(value) for value in live_ids}) != len(live_ids)
    ):
        raise CatalogAuditError("Verified live state has invalid live_ids")
    identities: dict[str, str] = {}
    for key in apps:
        app_id = str(appstore.get(key) or "")
        if APP_ID_RE.fullmatch(app_id) is None:
            raise CatalogAuditError(f"Portfolio identity is invalid for {key}")
        previous = identities.get(app_id)
        if previous:
            raise CatalogAuditError(
                f"Duplicate portfolio identity {app_id}: {previous}, {key}"
            )
        identities[app_id] = key
    unknown_ids = sorted(set(map(str, live_ids)) - set(identities))
    if unknown_ids:
        raise CatalogAuditError(
            "Verified live apps are absent from the portfolio registry: "
            + ", ".join(unknown_ids)
        )
    return sorted(identities[app_id] for app_id in map(str, live_ids))


def _audit_threads_portfolio(
    threads_root: Path,
    *,
    live_keys: Iterable[str],
    appstore: Mapping[str, object],
    official_locales: Iterable[str],
) -> dict[str, int]:
    threads_root = Path(threads_root)
    live_keys = tuple(sorted(live_keys))
    expected_keys = set(live_keys)
    official_locales = tuple(official_locales)
    expected_locales = set(official_locales)
    expected_pairs = {
        (key, locale)
        for key in live_keys
        for locale in official_locales
    }

    apps_document = _json_object(threads_root / "apps.json", "Threads app registry")
    if set(apps_document) != expected_keys:
        raise CatalogAuditError(
            "Threads app registry differs from the verified live portfolio"
        )
    for key in live_keys:
        entry = apps_document[key]
        if not isinstance(entry, Mapping):
            raise CatalogAuditError(f"Invalid Threads app entry for {key}")
        match = STORE_URL_RE.fullmatch(str(entry.get("url") or ""))
        if not match or match.group(1) != str(appstore[key]):
            raise CatalogAuditError(f"Threads App Store identity differs for {key}")

    routes_document = _json_object(
        threads_root / "storefront_routes.json", "Threads storefront routes"
    )
    if routes_document.get("version") != 1:
        raise CatalogAuditError("Threads storefront route schema version is invalid")
    routes = routes_document.get("routes")
    expected_ids = {str(appstore[key]) for key in live_keys}
    if (
        not isinstance(routes, Mapping)
        or set(routes) != expected_ids
        or routes_document.get("app_count") != len(live_keys)
        or routes_document.get("locale_count") != len(official_locales)
        or routes_document.get("route_count") != len(expected_pairs)
    ):
        raise CatalogAuditError("Threads storefront route matrix is incomplete")
    fallback_count = 0
    for app_id, locale_routes in routes.items():
        if (
            not isinstance(locale_routes, Mapping)
            or set(locale_routes) != expected_locales
        ):
            raise CatalogAuditError(
                f"Threads storefront routes are incomplete for {app_id}"
            )
        for locale, country in locale_routes.items():
            expected_country = LOCALE_STOREFRONTS.get(locale)
            if country is None:
                fallback_count += 1
            elif country != expected_country:
                raise CatalogAuditError(
                    f"Threads storefront route is invalid for "
                    f"{app_id}/{locale}: {country!r}"
                )
    if routes_document.get("fallback_count") != fallback_count:
        raise CatalogAuditError("Threads storefront fallback count is inconsistent")

    campaigns = _json_array(
        threads_root / "i18n_posts.json", "Threads localized campaigns"
    )
    campaign_pairs: set[tuple[str, str]] = set()
    for value in campaigns:
        if not isinstance(value, Mapping):
            raise CatalogAuditError("Threads campaign entry must be an object")
        match = CAMPAIGN_KEY_RE.fullmatch(str(value.get("sk") or ""))
        locale = str(value.get("lang") or "")
        if (
            not match
            or match.group(1) not in expected_keys
            or match.group(2) != locale
            or locale not in expected_locales
        ):
            raise CatalogAuditError(
                f"Invalid Threads localized campaign identity: {value.get('sk')!r}"
            )
        if value.get("kind") != "text":
            raise CatalogAuditError(
                f"Invalid Threads localized campaign kind: {value.get('sk')!r}"
            )
        if "video_url" in value:
            raise CatalogAuditError(
                f"Threads text campaign contains video_url: {value.get('sk')!r}"
            )
        pair = (match.group(1), locale)
        if pair in campaign_pairs:
            raise CatalogAuditError(
                f"Duplicate Threads localized campaign: {pair[0]}/{pair[1]}"
            )
        country, app_id = _campaign_store_identity(value.get("text"))
        expected_app_id = str(appstore[pair[0]])
        expected_country = routes[expected_app_id][locale]
        if app_id != expected_app_id or country != expected_country:
            raise CatalogAuditError(
                f"Threads campaign App Store route differs for "
                f"{pair[0]}/{locale}"
            )
        campaign_pairs.add(pair)
    if campaign_pairs != expected_pairs:
        missing = sorted(expected_pairs - campaign_pairs)
        extra = sorted(campaign_pairs - expected_pairs)
        raise CatalogAuditError(
            "Threads localized campaigns differ from the live 50-locale matrix; "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )

    markets = _json_object(
        threads_root / "market_locales.json", "Threads market locale registry"
    )
    market_keys = {key for key in markets if not key.startswith("_")}
    if market_keys != expected_keys:
        raise CatalogAuditError(
            "Threads market locale registry differs from the verified portfolio"
        )
    for key in market_keys:
        locales = markets[key]
        if (
            not isinstance(locales, list)
            or not locales
            or len(locales) != len(set(map(str, locales)))
            or not set(map(str, locales)).issubset(expected_locales)
        ):
            raise CatalogAuditError(f"Invalid Threads market locales for {key}")

    intents_document = _json_object(
        threads_root / "publisher_intents.json", "Threads publisher intents"
    )
    intents = intents_document.get("intents")
    if (
        not isinstance(intents, Mapping)
        or set(intents) != expected_keys
        or intents_document.get("app_count") != len(live_keys)
        or intents_document.get("locale_count") != len(official_locales)
        or intents_document.get("record_count") != len(expected_pairs)
    ):
        raise CatalogAuditError("Threads publisher intent matrix is incomplete")
    for key, localized in intents.items():
        if not isinstance(localized, Mapping) or set(localized) != expected_locales:
            raise CatalogAuditError(
                f"Threads publisher intents are incomplete for {key}"
            )
        for locale, entry in localized.items():
            if (
                not isinstance(entry, Mapping)
                or not isinstance(entry.get("query"), str)
                or not entry["query"].strip()
                or not isinstance(entry.get("context"), str)
                or not entry["context"].strip()
            ):
                raise CatalogAuditError(
                    f"Invalid Threads publisher intent for {key}/{locale}"
                )

    return {
        "campaigns": len(campaign_pairs),
        "routes": sum(len(value) for value in routes.values()),
        "intents": sum(len(value) for value in intents.values()),
    }


def audit_live_portfolio_paths(
    *,
    data_root: Path = DATA_ROOT,
    guide_root: Path,
    threads_root: Path,
    apps: Mapping[str, Mapping[str, object]] = APPS,
    appstore: Mapping[str, object] = APPSTORE,
    official_locales: Iterable[str] = OFFICIAL_LOCALES,
) -> dict[str, int]:
    """Audit the complete verified live portfolio across all promotion repos."""
    guide_root = Path(guide_root)
    official_locales = tuple(official_locales)
    if (
        len(official_locales) != EXPECTED_LOCALE_COUNT
        or len(set(official_locales)) != EXPECTED_LOCALE_COUNT
    ):
        raise CatalogAuditError(
            "Official locale contract must contain exactly "
            f"{EXPECTED_LOCALE_COUNT} unique locales"
        )
    live_state = _json_object(
        guide_root / ".appstore_live_state.json",
        "verified live App Store state",
    )
    live_keys = _verified_live_keys(
        live_state,
        apps=apps,
        appstore=appstore,
    )
    for key in live_keys:
        source = _json_object(
            Path(data_root) / f"{key}_full.json",
            f"localization source for {key}",
        )
        mirror = _json_object(
            guide_root / "_engine" / "data" / f"{key}_full.json",
            f"Guide localization mirror for {key}",
        )
        if _localization_projection(
            key,
            source,
            official_locales=official_locales,
        ) != _localization_projection(
            key,
            mirror,
            official_locales=official_locales,
        ):
            raise CatalogAuditError(
                f"Guide localization mirror differs for live app {key}"
            )
        for locale in official_locales:
            page = guide_root / locale / f"{key}.html"
            if not page.is_file():
                raise CatalogAuditError(
                    f"Guide localized app page is missing: {key}/{locale}"
                )

    threads_result = _audit_threads_portfolio(
        Path(threads_root),
        live_keys=live_keys,
        appstore=appstore,
        official_locales=official_locales,
    )
    return {
        "apps": len(live_keys),
        "locales": len(official_locales),
        "pages": len(live_keys) * len(official_locales),
        **threads_result,
    }


def _identity(value: str) -> tuple[str, str]:
    key, separator, app_id = value.partition("=")
    if (
        not separator
        or KEY_RE.fullmatch(key) is None
        or APP_ID_RE.fullmatch(app_id) is None
    ):
        raise argparse.ArgumentTypeError("identity must be KEY=APP_STORE_ID")
    return key, app_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=AUTO_REGISTRY)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--guide-root", type=Path)
    parser.add_argument(
        "--threads-root",
        type=Path,
        help=(
            "Audit the complete verified live portfolio against a Threads "
            "candidate; requires --guide-root."
        ),
    )
    parser.add_argument("--key", action="append", dest="keys")
    parser.add_argument("--identity", action="append", type=_identity, default=[])
    parser.add_argument(
        "--strict-review",
        action="store_true",
        help="Require explicit reviewed_persona markers for every selected key.",
    )
    args = parser.parse_args()
    identities = dict(args.identity)
    try:
        if args.threads_root is not None:
            if args.guide_root is None:
                parser.error("--threads-root requires --guide-root")
            result = audit_live_portfolio_paths(
                data_root=args.data_root,
                guide_root=args.guide_root,
                threads_root=args.threads_root,
            )
            print(
                "PORTFOLIO_AUDIT_OK "
                f"apps={result['apps']} locales={result['locales']} "
                f"pages={result['pages']} campaigns={result['campaigns']} "
                f"routes={result['routes']} intents={result['intents']}"
            )
            return 0
        strict = []
        if args.strict_review:
            strict = args.keys or list(
                _json_object(args.registry, "automatic registry")
            )
        result = audit_catalog_paths(
            args.registry,
            args.data_root,
            guide_root=args.guide_root,
            keys=args.keys,
            expected_identities=identities,
            strict_review_keys=strict,
        )
    except CatalogAuditError as error:
        print(f"CATALOG_AUDIT_FAILED: {error}", file=sys.stderr)
        return 1
    print(
        "CATALOG_AUDIT_OK "
        f"apps={result['apps']} locales={result['locales']} "
        f"mirrors={result['mirrors']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
