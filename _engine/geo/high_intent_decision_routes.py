#!/usr/bin/env python3
"""Build source-bound, native-only high-intent app decision routes.

The source repository owns this generator and its reviewed route data. The
production Guide runs a mirrored copy from ``_engine/geo``; syncing that copy
and deploying the Guide are separate reviewed operations. This module only
emits a deterministic, explicitly non-deployment manifest.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlsplit

import app_store_storefronts
import gen_store_attribution
from official_locales import OFFICIAL_LOCALES
import sync_standard_site
from site_config import PUBLIC_SITE
from websub_config import WEBSUB_HUBS


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
SOURCE_PATH = HERE / "data" / "high_intent_decision_routes_v2.json"
SYNC_CONTRACT_PATH = (
    HERE / "data" / "high_intent_guide_sync_contract.json"
)
SYNC_CONTRACT_SCHEMA_VERSION = 1
SYNC_ENGINE_FILES = (
    Path("high_intent_decision_routes.py"),
    Path("data") / "high_intent_decision_routes_v2.json",
    Path("gen_store_attribution.py"),
    Path("official_locales.py"),
    Path("publish.py"),
    Path("sync_standard_site.py"),
    Path("site_config.py"),
    Path("websub_config.py"),
)
INVENTORY_FILENAME = "verified-ios-app-finder-catalog.json"
MANAGED_OWNER = "high_intent_decision_routes"
MANIFEST_SCHEMA_VERSION = 2
DEPLOYMENT_SCHEMA_VERSION = 4
DEPLOYMENT_ID_PREFIX = "github-pages:high-intent:v1"
MANIFEST_RELATIVE = (
    Path("data")
    / "high-intent-decision-routes"
    / "expected-output-manifest.json"
)
DEPLOYMENT_RELATIVE = Path(".well-known") / "deployment.json"
COVERAGE_RELATIVE = (
    Path("data") / "high-intent-decision-routes" / "coverage.json"
)
FEED_RELATIVE = Path("data") / "high-intent-decision-routes" / "feed.json"
SITEMAP_RELATIVE = Path("sitemap-high-intent-decision-routes.xml")
SITEMAP_INDEX_RELATIVE = Path("sitemap_index.xml")
FIXED_MANAGED_OUTPUTS = {
    COVERAGE_RELATIVE.as_posix(): "coverage_report",
    FEED_RELATIVE.as_posix(): "json_feed",
    SITEMAP_RELATIVE.as_posix(): "sitemap",
}
MANAGED_OUTPUT_KINDS = frozenset(
    {"route_html", *FIXED_MANAGED_OUTPUTS.values()}
)
PERCENT_CONFUSABLES = frozenset({"\u0025", "\u066a", "\ufe6a", "\uff05"})
RELEASE_STATE_EXACT = "exact"
RELEASE_STATE_INVENTORY_GAP = "degraded_missing_route_copy"
INTENT_TYPES = frozenset(
    {"problem_aware", "alternative", "workflow", "privacy_pay_once"}
)
MANIFEST_ROUTE_FIELDS = frozenset(
    {
        "route_id",
        "app_key",
        "app_store_id",
        "app_store_url",
        "locale",
        "intent_type",
        "campaign_token",
        "creative_id",
        "creative_digest",
        "content_type",
        "route_slug",
        "relative_path",
        "url",
        "record_digest",
        "output_sha256",
    }
)
MIN_CONTENT_UNITS = 180
MAX_EDITORIAL_JACCARD = 0.72
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
REF_RE = re.compile(
    r"(?:summary\.(?:en|zh-Hant)|feature\.[0-9]+|"
    r"fact\.(?:purchase_model|one_time_option)|capability\.[a-z_]+)"
)
EDITORIAL_FIELDS = (
    "culture_route",
    "buyer_problem",
    "decision_rule",
    "alternative_lens",
)
LOCALE_LANGUAGE = {
    "en-US": "en",
    "zh-Hant": "zh-Hant",
}
CULTURE_MARKERS = {
    "en-US": ("US", "United States"),
    "zh-Hant": ("台灣", "臺灣"),
}
COPY_FIELDS = frozenset(
    {
        "language",
        "market",
        "culture_route",
        "query",
        "buyer_problem",
        "decision_rule",
        "workflow_checks",
        "alternative_lens",
        "verify_before_install",
        "evidence_refs",
    }
)
INVENTORY_DIGEST_FIELDS = (
    "key",
    "app_store_id",
    "name",
    "category",
    "purchase_model",
    "one_time_option",
    "summaries",
    "features",
    "keywords",
    "capabilities",
    "canonical_app_store_url",
    "verified_live",
)
INVENTORY_CONTRACT_FIELDS = frozenset(
    {
        "relative_path",
        "expected_app_count",
        "app_keys_sha256",
        "copy_sha256",
        "official_locales_sha256",
    }
)
UI = {
    "en-US": {
        "eyebrow": "First-party decision route",
        "intent_types": {
            "problem_aware": "Problem-aware",
            "alternative": "Alternative",
            "workflow": "Workflow",
            "privacy_pay_once": "Privacy / pay once",
        },
        "situation": "Your situation",
        "rule": "Decision rule",
        "checks": "Workflow checks",
        "alternative": "When another route is better",
        "evidence": "First-party product evidence",
        "vocabulary": "Published task vocabulary",
        "verify": "Verify before installing",
        "store": "View on the App Store",
        "source": "Source",
        "purchase_model": {
            "paid_upfront": "Paid download",
            "free_with_lifetime_unlock": (
                "Free to start with a one-time unlock"
            ),
            "free": "Free",
            "flexible": "Check the current purchase model",
            "neutral": "Check the current purchase model",
        },
        "one_time_option": "The first-party inventory records a one-time option.",
        "feature_labels": {
            "Free to start": "Free to start",
            "One-time unlock": "One-time unlock",
            "No subscription": "No subscription",
        },
        "capabilities": {
            "offline": "The first-party inventory marks offline use.",
            "no_account": "The first-party inventory marks no account required.",
            "no_ads": "The first-party inventory marks no ads.",
            "no_tracking": "The first-party inventory marks no tracking.",
            "private_or_on_device": (
                "The first-party inventory marks private or on-device handling."
            ),
            "widget": "The first-party inventory marks a Home Screen widget.",
            "apple_watch": "The first-party inventory marks Apple Watch support.",
        },
    },
    "zh-Hant": {
        "eyebrow": "第一方決策路徑",
        "intent_types": {
            "problem_aware": "問題導向",
            "alternative": "替代方案",
            "workflow": "工作流程",
            "privacy_pay_once": "隱私／一次付費",
        },
        "situation": "你的情境",
        "rule": "判斷原則",
        "checks": "流程檢查",
        "alternative": "何時應改選其他方案",
        "evidence": "第一方產品依據",
        "vocabulary": "已發布的任務用語",
        "verify": "安裝前確認",
        "store": "前往 App Store 查看",
        "source": "來源",
        "purchase_model": {
            "paid_upfront": "付費下載",
            "free_with_lifetime_unlock": "免費開始，可一次付費解鎖",
            "free": "免費",
            "flexible": "請確認目前購買方式",
            "neutral": "請確認目前購買方式",
        },
        "one_time_option": "第一方 inventory 記錄此 App 提供一次性付費選項。",
        "feature_labels": {
            "Free to start": "可免費開始使用",
            "One-time unlock": "提供一次性付費解鎖",
            "No subscription": "不採訂閱制",
        },
        "capabilities": {
            "offline": "第一方 inventory 標示可離線使用。",
            "no_account": "第一方 inventory 標示不需帳號。",
            "no_ads": "第一方 inventory 標示無廣告。",
            "no_tracking": "第一方 inventory 標示無追蹤。",
            "private_or_on_device": "第一方 inventory 標示隱私優先或裝置端處理。",
            "widget": "第一方 inventory 標示支援主畫面小工具。",
            "apple_watch": "第一方 inventory 標示支援 Apple Watch。",
        },
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _single_line(value: object, field: str, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    cleaned = " ".join(value.split())
    if (
        len(cleaned) < minimum
        or "\n" in value
        or "\r" in value
        or "{" in cleaned
        or "}" in cleaned
    ):
        raise ValueError(f"{field} must be substantive single-line copy")
    return cleaned


def _inventory_projection(apps: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {field: app.get(field) for field in INVENTORY_DIGEST_FIELDS}
        for app in sorted(apps, key=lambda item: str(item["key"]))
    ]


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def deployment_identity(route_manifest_digest: str) -> str:
    """Identify deployed route bytes independently of unrelated Guide commits."""
    if re.fullmatch(r"[0-9a-f]{64}", route_manifest_digest) is None:
        raise ValueError("route_manifest_digest must be a SHA-256 digest")
    return f"{DEPLOYMENT_ID_PREFIX}:{route_manifest_digest}"


def _inventory_digests(
    apps: Iterable[dict[str, Any]],
) -> tuple[str, str]:
    projection = _inventory_projection(apps)
    keys = "\n".join(str(app["key"]) for app in projection)
    return hashlib.sha256(keys.encode("utf-8")).hexdigest(), _sha256_json(
        projection
    )


def release_expectations(source: dict[str, Any]) -> dict[str, Any]:
    """Derive exact release cardinality from the reviewed source contract."""
    contract = source.get("inventory_contract")
    if not isinstance(contract, dict) or set(contract) != INVENTORY_CONTRACT_FIELDS:
        raise ValueError("High-intent inventory contract fields differ")
    app_count = contract.get("expected_app_count")
    if type(app_count) is not int or app_count < 1:
        raise ValueError("High-intent inventory app count must be positive")
    if (
        contract.get("relative_path")
        != f"data/{INVENTORY_FILENAME}"
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(contract.get(field))) is None
            for field in (
                "app_keys_sha256",
                "copy_sha256",
                "official_locales_sha256",
            )
        )
    ):
        raise ValueError("High-intent inventory contract digest is invalid")
    locales = tuple(OFFICIAL_LOCALES)
    if not locales or len(locales) != len(set(locales)):
        raise ValueError("OFFICIAL_LOCALES must be a non-empty unique list")
    locale_digest = _sha256_json(list(locales))
    if contract.get("official_locales_sha256") != locale_digest:
        raise ValueError(
            "OFFICIAL_LOCALES drifted from the versioned route source"
        )

    raw_routes = source.get("routes")
    if not isinstance(raw_routes, list):
        raise ValueError("High-intent route data must contain routes")
    app_keys: list[str] = []
    route_ids: list[str] = []
    for position, raw in enumerate(raw_routes):
        if not isinstance(raw, dict):
            raise ValueError(f"Route entry {position} must be an object")
        key = raw.get("app_key")
        slug = raw.get("route_slug")
        copies = raw.get("locales")
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(slug, str)
            or not slug
            or not isinstance(copies, dict)
            or not copies
        ):
            raise ValueError(f"Route entry {position} identity is incomplete")
        app_keys.append(key)
        for locale in copies:
            if locale not in locales:
                raise ValueError(f"{key}: unsupported locale {locale}")
            route_ids.append(f"{locale}:{key}:{slug}")
    if len(app_keys) != app_count or len(set(app_keys)) != app_count:
        raise ValueError(
            "Route source App keys do not match inventory_contract count"
        )
    key_digest = hashlib.sha256(
        "\n".join(sorted(app_keys)).encode("utf-8")
    ).hexdigest()
    if contract.get("app_keys_sha256") != key_digest:
        raise ValueError(
            "Route source App keys drifted from inventory_contract digest"
        )
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("Route source contains duplicate localized route IDs")
    candidate_pairs = app_count * len(locales)
    if len(route_ids) > candidate_pairs:
        raise ValueError("Route source exceeds the App-locale candidate set")
    derived = {
        "app_count": app_count,
        "app_keys": tuple(sorted(app_keys)),
        "app_keys_sha256": key_digest,
        "copy_sha256": contract.get("copy_sha256"),
        "official_locales": locales,
        "official_locales_sha256": locale_digest,
        "route_ids": tuple(sorted(route_ids)),
        "route_count": len(route_ids),
        "creative_count": app_count,
        "candidate_app_locale_pairs": candidate_pairs,
        "abstained_pairs": candidate_pairs - len(route_ids),
        "managed_output_count": len(route_ids) + len(FIXED_MANAGED_OUTPUTS),
    }
    derived["release_contract_digest"] = _sha256_json(
        {
            "inventory_contract": contract,
            "official_locales": list(locales),
            "route_ids": list(derived["route_ids"]),
            "fixed_managed_outputs": FIXED_MANAGED_OUTPUTS,
        }
    )
    return derived


def load_inventory(path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    raw_apps = payload.get("apps")
    if not isinstance(raw_apps, list) or not raw_apps:
        raise ValueError(f"Public inventory apps are missing: {path}")
    if (
        "record_count" in payload
        and payload.get("record_count") != len(raw_apps)
    ):
        raise ValueError(f"Public inventory record_count is inconsistent: {path}")
    apps: dict[str, dict[str, Any]] = {}
    for raw in raw_apps:
        if not isinstance(raw, dict):
            raise ValueError(f"Inventory app must be an object: {path}")
        key = _single_line(raw.get("key"), "inventory key")
        if key in apps:
            raise ValueError(f"Duplicate inventory app key: {key}")
        if raw.get("verified_live") is not True:
            raise ValueError(f"Inventory app is not verified live: {key}")
        app_id = _single_line(raw.get("app_store_id"), f"{key}.app_store_id")
        app_store_storefronts.validated_app_store_url(
            _single_line(
                raw.get("canonical_app_store_url"),
                f"{key}.canonical_app_store_url",
            ),
            expected_app_id=app_id,
        )
        for field in ("summaries", "capabilities"):
            if not isinstance(raw.get(field), dict):
                raise ValueError(f"{key}.{field} must be an object")
        for field in ("features", "keywords"):
            values = raw.get(field)
            if not isinstance(values, list) or len(values) < 3:
                raise ValueError(f"{key}.{field} needs at least three values")
        apps[key] = raw
    return apps


def load_route_source(path: Path = SOURCE_PATH) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != 3:
        raise ValueError("High-intent route data must use schema_version 3")
    if not isinstance(payload.get("routes"), list):
        raise ValueError("High-intent route data must contain routes")
    publisher = payload.get("publisher")
    if (
        not isinstance(publisher, dict)
        or publisher.get("name") != "Lumi Studio"
        or publisher.get("relationship") != "developer_of_every_listed_app"
        or not isinstance(publisher.get("disclosures"), dict)
    ):
        raise ValueError("Publisher relationship must identify the app developer")
    return payload


def validate_inventory_binding(
    source: dict[str, Any],
    apps: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    return _validate_inventory_binding(source, apps, allow_new_live_apps=False)


def _validate_inventory_binding(
    source: dict[str, Any],
    apps: dict[str, dict[str, Any]],
    *,
    allow_new_live_apps: bool,
) -> tuple[dict[str, Any], list[str]]:
    expectations = release_expectations(source)
    expected_keys = set(expectations["app_keys"])
    current_keys = set(apps)
    missing = sorted(expected_keys - current_keys)
    if missing:
        raise ValueError(
            "Reviewed high-intent Apps disappeared from current inventory: "
            f"{missing}"
        )
    contracted_apps = [apps[key] for key in expectations["app_keys"]]
    keys_digest, copy_digest = _inventory_digests(contracted_apps)
    if (
        expectations["app_count"] != len(contracted_apps)
        or expectations["app_keys_sha256"] != keys_digest
        or expectations["copy_sha256"] != copy_digest
    ):
        raise ValueError(
            "Public inventory/copy drifted; review every source reference "
            "before regenerating decision routes"
        )
    extra = sorted(current_keys - expected_keys)
    if extra and not allow_new_live_apps:
        raise ValueError(
            "Every current public app needs reviewed native route copy: "
            f"missing={extra}"
        )
    return expectations, extra


def _native_copy(locale: str, copy: dict[str, Any]) -> None:
    expected_language = LOCALE_LANGUAGE.get(locale)
    if expected_language is None:
        raise ValueError(f"No native-copy validator for {locale}")
    if copy.get("language") != expected_language:
        raise ValueError(f"{locale}: native language marker is missing")
    joined = " ".join(
        [
            str(copy.get(field, ""))
            for field in EDITORIAL_FIELDS
        ]
        + [str(copy.get("query", ""))]
        + [str(item) for item in copy.get("workflow_checks", [])]
        + [str(item) for item in copy.get("verify_before_install", [])]
    )
    if locale == "zh-Hant" and len(re.findall(r"[\u3400-\u9fff]", joined)) < 80:
        raise ValueError(f"{locale}: copy is not substantively native")
    if locale == "en-US" and len(re.findall(r"[A-Za-z]+", joined)) < 90:
        raise ValueError(f"{locale}: copy is not substantively native")
    if not any(
        marker in str(copy["culture_route"])
        for marker in CULTURE_MARKERS[locale]
    ):
        raise ValueError(f"{locale}: culture route lacks a market marker")


def _validate_locale_copy(
    app_key: str,
    app_name: str,
    locale: str,
    copy: object,
) -> dict[str, Any]:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"{app_key}: unsupported locale {locale}")
    if not isinstance(copy, dict) or set(copy) != COPY_FIELDS:
        raise ValueError(f"{app_key}/{locale}: copy fields differ from contract")
    for field in EDITORIAL_FIELDS:
        _single_line(copy[field], f"{app_key}/{locale}.{field}", 45)
    _single_line(copy["market"], f"{app_key}/{locale}.market", 2)
    _single_line(copy["query"], f"{app_key}/{locale}.query", 15)
    for field, minimum_count in (
        ("workflow_checks", 3),
        ("verify_before_install", 2),
        ("evidence_refs", 3),
    ):
        values = copy[field]
        if (
            not isinstance(values, list)
            or len(values) < minimum_count
            or len(values) != len(set(str(value) for value in values))
        ):
            raise ValueError(
                f"{app_key}/{locale}.{field} needs "
                f"{minimum_count} distinct values"
            )
        for index, value in enumerate(values):
            text = _single_line(
                value,
                f"{app_key}/{locale}.{field}[{index}]",
                8 if field != "evidence_refs" else 5,
            )
            if field == "workflow_checks" and not text.endswith(("?", "？")):
                raise ValueError(
                    f"{app_key}/{locale}: workflow checks must be questions"
                )
            if field == "evidence_refs" and REF_RE.fullmatch(text) is None:
                raise ValueError(
                    f"{app_key}/{locale}: unsupported evidence ref {text}"
                )
    app_name_folded = app_name.casefold()
    for field in EDITORIAL_FIELDS:
        value = str(copy[field]).casefold()
        if app_name_folded in value or "this app " in value:
            raise ValueError(
                f"{app_key}/{locale}.{field} contains an unsourced product claim"
            )
    _native_copy(locale, copy)
    return copy


def _validate_source(
    source: dict[str, Any],
    apps: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    routes, _, _ = _validate_source_binding(
        source,
        apps,
        allow_new_live_apps=False,
    )
    return routes


def _validate_source_binding(
    source: dict[str, Any],
    apps: dict[str, dict[str, Any]],
    *,
    allow_new_live_apps: bool,
) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    expectations, inventory_gaps = _validate_inventory_binding(
        source,
        apps,
        allow_new_live_apps=allow_new_live_apps,
    )
    expected_keys = set(expectations["app_keys"])
    routes: dict[str, dict[str, Any]] = {}
    slugs: set[str] = set()
    queries: set[tuple[str, str]] = set()
    for raw in source["routes"]:
        if not isinstance(raw, dict):
            raise ValueError("Route entries must be objects")
        expected_fields = {
            "app_key",
            "route_slug",
            "intent_type",
            "primary",
            "keyword_refs",
            "locales",
        }
        if set(raw) != expected_fields:
            raise ValueError("Route fields differ from contract")
        key = _single_line(raw["app_key"], "route app_key")
        if key not in apps or key not in expected_keys or key in routes:
            raise ValueError(f"Unknown or duplicate route app: {key}")
        slug = _single_line(raw["route_slug"], f"{key}.route_slug")
        if SLUG_RE.fullmatch(slug) is None or slug in slugs:
            raise ValueError(f"Invalid or duplicate route slug: {slug}")
        slugs.add(slug)
        if raw["intent_type"] not in INTENT_TYPES or raw["primary"] is not True:
            raise ValueError(f"{key}: missing valid primary decision intent")
        keyword_refs = raw["keyword_refs"]
        keywords = apps[key]["keywords"]
        if (
            not isinstance(keyword_refs, list)
            or len(keyword_refs) < 3
            or len(keyword_refs) != len(set(keyword_refs))
            or any(
                not isinstance(index, int)
                or isinstance(index, bool)
                or index < 0
                or index >= len(keywords)
                for index in keyword_refs
            )
        ):
            raise ValueError(f"{key}: invalid keyword references")
        locale_copies = raw["locales"]
        if not isinstance(locale_copies, dict) or not locale_copies:
            raise ValueError(f"{key}: at least one native locale is required")
        validated_copies = {}
        for locale, copy in locale_copies.items():
            validated = _validate_locale_copy(
                key,
                str(apps[key]["name"]),
                locale,
                copy,
            )
            query_key = (locale, str(validated["query"]).casefold())
            if query_key in queries:
                raise ValueError(f"Duplicate localized decision query: {query_key}")
            queries.add(query_key)
            validated_copies[locale] = validated
        routes[key] = {**raw, "locales": validated_copies}
    if set(routes) != expected_keys:
        raise ValueError(
            "Versioned inventory contract needs exactly one primary route: "
            f"missing={sorted(expected_keys - set(routes))}, "
            f"extra={sorted(set(routes) - expected_keys)}"
        )
    counts = Counter(str(route["intent_type"]) for route in routes.values())
    if set(counts) != INTENT_TYPES or max(counts.values()) > len(routes) * 0.6:
        raise ValueError(f"Decision-intent mix is not diverse: {dict(counts)}")
    return routes, inventory_gaps, expectations


def _evidence(
    app: dict[str, Any],
    locale: str,
    reference: str,
) -> dict[str, Any]:
    key = str(app["key"])
    if reference.startswith("summary."):
        summary_key = reference.split(".", 1)[1]
        summaries = app["summaries"]
        if summary_key not in summaries:
            raise ValueError(f"{key}/{locale}: missing {reference}")
        value = _single_line(
            summaries[summary_key],
            f"{key}.{reference}",
            12,
        )
        pointer = f"/apps/{key}/summaries/{summary_key}"
        source_value: object = value
    elif reference.startswith("feature."):
        index = int(reference.rsplit(".", 1)[1])
        try:
            source_value = _single_line(
                app["features"][index],
                f"{key}.{reference}",
                2,
            )
        except IndexError as error:
            raise ValueError(f"{key}/{locale}: missing {reference}") from error
        if locale == "en-US":
            value = source_value
        else:
            labels = UI[locale].get("feature_labels")
            if not isinstance(labels, dict) or source_value not in labels:
                raise ValueError(
                    f"{key}/{locale}: missing localized feature evidence: "
                    f"{source_value}"
                )
            value = _single_line(
                labels[source_value],
                f"{key}/{locale}.{reference}.localized",
                2,
            )
            if value.casefold() == source_value.casefold():
                raise ValueError(
                    f"{key}/{locale}: feature evidence fell back to source locale"
                )
        pointer = f"/apps/{key}/features/{index}"
    elif reference == "fact.purchase_model":
        model = str(app["purchase_model"])
        labels = UI[locale]["purchase_model"]
        if model not in labels:
            raise ValueError(f"{key}/{locale}: unknown purchase model {model}")
        value = str(labels[model])
        pointer = f"/apps/{key}/purchase_model"
        source_value = model
    elif reference == "fact.one_time_option":
        if app.get("one_time_option") is not True:
            raise ValueError(f"{key}/{locale}: one-time option is not verified")
        value = str(UI[locale]["one_time_option"])
        pointer = f"/apps/{key}/one_time_option"
        source_value = True
    elif reference.startswith("capability."):
        capability = reference.split(".", 1)[1]
        if app["capabilities"].get(capability) is not True:
            raise ValueError(
                f"{key}/{locale}: capability is not verified: {capability}"
            )
        labels = UI[locale]["capabilities"]
        if capability not in labels:
            raise ValueError(f"{key}/{locale}: capability label is missing")
        value = str(labels[capability])
        pointer = f"/apps/{key}/capabilities/{capability}"
        source_value = True
    else:
        raise ValueError(f"{key}/{locale}: unsupported evidence ref {reference}")
    return {
        "reference": reference,
        "inventory_pointer": pointer,
        "source_value": source_value,
        "text": value,
    }


def campaign_token(intent_type: str) -> str:
    token = gen_store_attribution.campaign_token_for_intent(intent_type)
    if (
        len(token) > gen_store_attribution.MAX_TOKEN
        or app_store_storefronts.CAMPAIGN_TOKEN_RE.fullmatch(token) is None
    ):
        raise ValueError(f"Invalid shared campaign token: {token}")
    return token


def _campaign_url(
    app: dict[str, Any],
    locale: str,
    intent_type: str,
    provider_token: str,
) -> str:
    if not provider_token:
        raise ValueError(
            "A real Apple provider token is required; a partial campaign URL "
            "must never be emitted"
        )
    direct = app_store_storefronts.localized_app_store_url(
        str(app["canonical_app_store_url"]),
        locale,
    )
    value = app_store_storefronts.campaign_app_store_url(
        direct,
        campaign_token(intent_type),
        provider_token=provider_token,
    )
    app_store_storefronts.validated_app_store_url(
        value,
        expected_app_id=str(app["app_store_id"]),
    )
    if [key for key, _ in parse_qsl(urlsplit(value).query)] != ["pt", "ct", "mt"]:
        raise ValueError(f"Incomplete App Store campaign URL: {value}")
    if dict(parse_qsl(urlsplit(value).query)).get("mt") != "8":
        raise ValueError(f"Wrong App Store media type: {value}")
    return value


def _creative_identity(
    app_key: str,
    route_slug: str,
    intent_type: str,
    campaign: str,
) -> tuple[str, str]:
    creative_id = f"{app_key}:{route_slug}:{intent_type}"
    creative_digest = _sha256_json(
        {
            "app_key": app_key,
            "route_slug": route_slug,
            "intent_type": intent_type,
            "campaign_token": campaign,
        }
    )
    return creative_id, creative_digest


def route_relative(record: dict[str, Any]) -> Path:
    return (
        Path(str(record["locale"]))
        / "decide"
        / str(record["app_key"])
        / f"{record['route_slug']}.html"
    )


def route_url(app_key: str, route_slug: str, locale: str) -> str:
    return (
        f"{SITE}/{locale}/decide/{app_key}/{route_slug}.html"
    )


def _content_units(record: dict[str, Any]) -> int:
    visible = " ".join(
        [
            str(record[field])
            for field in (
                "query",
                "culture_route",
                "buyer_problem",
                "decision_rule",
                "alternative_lens",
                "publisher_disclosure",
            )
        ]
        + [str(item) for item in record["workflow_checks"]]
        + [str(item) for item in record["verify_before_install"]]
        + [str(item["text"]) for item in record["evidence"]]
        + [str(item) for item in record["source_vocabulary"]]
    )
    latin_words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:['’_-][A-Za-z0-9]+)*", visible)
    han = re.findall(r"[\u3400-\u9fff]", visible)
    return len(latin_words) + len(han)


def _editorial_tokens(record: dict[str, Any]) -> set[str]:
    text = " ".join(
        [
            str(record["query"]),
            str(record["culture_route"]),
            str(record["buyer_problem"]),
            str(record["decision_rule"]),
            str(record["alternative_lens"]),
        ]
        + [str(value) for value in record["workflow_checks"]]
    ).casefold()
    tokens = set(re.findall(r"[a-zà-öø-ÿ\u3400-\u9fff]{3,}", text))
    stop = {
        "the",
        "and",
        "that",
        "when",
        "with",
        "from",
        "this",
        "what",
        "which",
        "can",
        "without",
        "better",
        "choose",
        "decision",
        "需要",
        "是否",
        "可以",
        "如何",
        "目前",
    }
    return tokens - stop


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _max_similarity(records: list[dict[str, Any]]) -> tuple[float, list[str]]:
    maximum = 0.0
    pair: list[str] = []
    by_locale: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_locale.setdefault(str(record["locale"]), []).append(record)
    for localized in by_locale.values():
        for index, left in enumerate(localized):
            left_tokens = _editorial_tokens(left)
            for right in localized[index + 1 :]:
                score = _jaccard(left_tokens, _editorial_tokens(right))
                if score > maximum:
                    maximum = score
                    pair = [str(left["route_id"]), str(right["route_id"])]
    return maximum, pair


def _build_record(
    app: dict[str, Any],
    route: dict[str, Any],
    locale: str,
    provider_token: str,
    disclosure: str,
) -> dict[str, Any]:
    copy = route["locales"][locale]
    intent_type = str(route["intent_type"])
    campaign = campaign_token(intent_type)
    creative_id, creative_digest = _creative_identity(
        str(app["key"]),
        str(route["route_slug"]),
        intent_type,
        campaign,
    )
    evidence = [
        _evidence(app, locale, str(reference))
        for reference in copy["evidence_refs"]
    ]
    keywords = (
        [
            _single_line(
                app["keywords"][index],
                f"{app['key']}.keywords[{index}]",
                2,
            )
            for index in route["keyword_refs"]
        ]
        if locale == "en-US"
        else []
    )
    record = {
        "route_id": f"{locale}:{app['key']}:{route['route_slug']}",
        "app_key": str(app["key"]),
        "app_name": str(app["name"]),
        "app_store_id": str(app["app_store_id"]),
        "category": str(app["category"]),
        "purchase_model": str(app["purchase_model"]),
        "one_time_option": bool(app["one_time_option"]),
        "locale": locale,
        "language": str(copy["language"]),
        "market": str(copy["market"]),
        "intent_type": intent_type,
        "campaign_token": campaign,
        "creative_id": creative_id,
        "creative_digest": creative_digest,
        "primary": True,
        "route_slug": str(route["route_slug"]),
        "query": str(copy["query"]),
        "culture_route": str(copy["culture_route"]),
        "buyer_problem": str(copy["buyer_problem"]),
        "decision_rule": str(copy["decision_rule"]),
        "workflow_checks": list(copy["workflow_checks"]),
        "alternative_lens": str(copy["alternative_lens"]),
        "verify_before_install": list(copy["verify_before_install"]),
        "evidence": evidence,
        "source_vocabulary": keywords,
        "inventory_source": (
            f"{SITE}/data/{INVENTORY_FILENAME}"
        ),
        "canonical_url": route_url(
            str(app["key"]),
            str(route["route_slug"]),
            locale,
        ),
        "app_store_url": _campaign_url(
            app,
            locale,
            str(route["intent_type"]),
            provider_token,
        ),
        "publisher": "Lumi Studio",
        "publisher_relationship": "app_developer",
        "publisher_disclosure": disclosure,
        "is_independent_review": False,
        "is_ranking": False,
    }
    record["content_units"] = _content_units(record)
    if record["content_units"] < MIN_CONTENT_UNITS:
        raise ValueError(
            f"Thin decision route {record['route_id']}: "
            f"{record['content_units']} < {MIN_CONTENT_UNITS}"
        )
    return record


def _gate(
    passed: bool,
    detail: str,
) -> dict[str, Any]:
    return {"passed": passed, "detail": detail}


def build(
    *,
    inventory_path: Path | None = None,
    source_path: Path = SOURCE_PATH,
    provider_token: str,
    allow_new_live_app_gaps: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventory_path = inventory_path or PAGES / "data" / INVENTORY_FILENAME
    apps = load_inventory(inventory_path)
    source = load_route_source(source_path)
    routes, inventory_gaps, expectations = _validate_source_binding(
        source,
        apps,
        allow_new_live_apps=allow_new_live_app_gaps,
    )
    covered_apps = {
        key: apps[key]
        for key in expectations["app_keys"]
    }
    current_keys_digest, current_copy_digest = _inventory_digests(
        apps.values()
    )
    release_state = (
        RELEASE_STATE_INVENTORY_GAP
        if inventory_gaps
        else RELEASE_STATE_EXACT
    )
    disclosures = source["publisher"]["disclosures"]
    records: list[dict[str, Any]] = []
    abstention_counts: Counter[str] = Counter()
    locale_rows: dict[str, dict[str, int]] = {}
    app_rows: dict[str, dict[str, Any]] = {}
    for locale in OFFICIAL_LOCALES:
        emitted = 0
        abstained = 0
        for app_key in sorted(covered_apps):
            route = routes[app_key]
            if locale not in route["locales"]:
                abstention_counts["missing_curated_native_copy"] += 1
                abstained += 1
                continue
            disclosure = disclosures.get(locale)
            if not isinstance(disclosure, str) or not disclosure.strip():
                raise ValueError(f"Missing native publisher disclosure: {locale}")
            records.append(
                _build_record(
                    covered_apps[app_key],
                    route,
                    locale,
                    provider_token,
                    _single_line(
                        disclosure,
                        f"{locale}.publisher_disclosure",
                        40,
                    ),
                )
            )
            emitted += 1
        locale_rows[locale] = {
            "emitted": emitted,
            "abstained": abstained,
        }
    for key in sorted(covered_apps):
        app_records = [record for record in records if record["app_key"] == key]
        app_rows[key] = {
            "intent_type": routes[key]["intent_type"],
            "route_slug": routes[key]["route_slug"],
            "native_locales": [record["locale"] for record in app_records],
            "record_count": len(app_records),
        }
    similarity, similarity_pair = _max_similarity(records)
    route_signatures = {
        _sha256_json(
            {
                "query": record["query"],
                "culture_route": record["culture_route"],
                "buyer_problem": record["buyer_problem"],
                "decision_rule": record["decision_rule"],
                "workflow_checks": record["workflow_checks"],
                "alternative_lens": record["alternative_lens"],
            }
        )
        for record in records
    }
    intent_counts = Counter(
        str(route["intent_type"]) for route in routes.values()
    )
    cta_ok = all(
        [key for key, _ in parse_qsl(urlsplit(record["app_store_url"]).query)]
        == ["pt", "ct", "mt"]
        and dict(parse_qsl(urlsplit(record["app_store_url"]).query)).get("mt")
        == "8"
        and dict(parse_qsl(urlsplit(record["app_store_url"]).query)).get("ct")
        == record["campaign_token"]
        and record["campaign_token"] in {
            "geo_ask",
            "geo_pick",
            "geo_learn",
        }
        and len(str(record["campaign_token"])) <= 30
        for record in records
    )
    gates = {
        "exact_release_cardinality": _gate(
            len(records) == expectations["route_count"]
            and len(covered_apps) * len(OFFICIAL_LOCALES)
            == expectations["candidate_app_locale_pairs"]
            and sum(abstention_counts.values())
            == expectations["abstained_pairs"]
            and len(OFFICIAL_LOCALES)
            == len(expectations["official_locales"]),
            f"{len(records)} routes; {len(covered_apps)} apps; "
            f"{len(covered_apps) * len(OFFICIAL_LOCALES)} pairs; "
            f"{sum(abstention_counts.values())} abstentions",
        ),
        "versioned_app_coverage": _gate(
            len(routes) == len(covered_apps) == expectations["app_count"],
            f"{len(routes)}/{expectations['app_count']} contracted apps mapped",
        ),
        "current_inventory_coverage": _gate(
            not inventory_gaps and len(routes) == len(apps),
            (
                f"{len(routes)}/{len(apps)} current public apps mapped; "
                f"missing route copy={inventory_gaps}"
            ),
        ),
        "primary_intent_coverage": _gate(
            all(route["primary"] is True for route in routes.values()),
            f"{len(routes)}/{len(apps)} apps have one primary route",
        ),
        "intent_diversity": _gate(
            set(intent_counts) == INTENT_TYPES,
            json.dumps(dict(sorted(intent_counts.items())), sort_keys=True),
        ),
        "inventory_bound_claims": _gate(
            all(len(record["evidence"]) >= 3 for record in records),
            f"{sum(len(record['evidence']) for record in records)} "
            "evidence references resolved from inventory",
        ),
        "native_copy_or_abstain": _gate(
            sum(row["emitted"] + row["abstained"] for row in locale_rows.values())
            == len(covered_apps) * len(OFFICIAL_LOCALES),
            f"{len(records)} emitted; "
            f"{sum(abstention_counts.values())} explicit abstentions; "
            "0 fallbacks",
        ),
        "cultural_route": _gate(
            all(record["culture_route"] for record in records),
            f"{len(records)}/{len(records)} emitted records",
        ),
        "complete_app_store_cta": _gate(
            cta_ok,
            f"{len(records)}/{len(records)} URLs use ordered pt/ct/mt=8",
        ),
        "truthful_publisher_disclosure": _gate(
            all(
                record["publisher"] == "Lumi Studio"
                and record["publisher_relationship"] == "app_developer"
                and record["is_independent_review"] is False
                for record in records
            ),
            f"{len(records)}/{len(records)} records disclose developer authorship",
        ),
        "non_thin": _gate(
            all(
                record["content_units"] >= MIN_CONTENT_UNITS
                for record in records
            ),
            f"minimum={min(record['content_units'] for record in records)} "
            f"units; threshold={MIN_CONTENT_UNITS}",
        ),
        "non_template": _gate(
            len(route_signatures) == len(records)
            and similarity <= MAX_EDITORIAL_JACCARD,
            f"{len(route_signatures)}/{len(records)} unique signatures; "
            f"max Jaccard={similarity:.3f}",
        ),
    }
    report = {
        "schema_version": 1,
        "dataset": str(source["dataset_name"]),
        "release_state": release_state,
        "release_contract_digest": expectations["release_contract_digest"],
        "inventory": {
            "relative_path": source["inventory_contract"]["relative_path"],
            "public_apps": expectations["app_count"],
            "app_keys_sha256": source["inventory_contract"][
                "app_keys_sha256"
            ],
            "copy_sha256": source["inventory_contract"]["copy_sha256"],
            "official_locales_sha256": source["inventory_contract"][
                "official_locales_sha256"
            ],
        },
        "current_inventory": {
            "public_apps": len(apps),
            "app_keys_sha256": current_keys_digest,
            "copy_sha256": current_copy_digest,
            "missing_route_app_keys": inventory_gaps,
            "missing_route_app_keys_sha256": _sha256_json(inventory_gaps),
        },
        "coverage": {
            "mapped_apps": len(routes),
            "current_public_apps": len(apps),
            "missing_route_apps": len(inventory_gaps),
            "missing_route_app_keys": inventory_gaps,
            "app_coverage_percent": round(
                len(routes) / len(apps) * 100,
                2,
            ),
            "primary_routes": len(routes),
            "intent_type_counts": dict(sorted(intent_counts.items())),
            "official_locales_considered": len(OFFICIAL_LOCALES),
            "native_locale_records": len(records),
            "native_locales_with_records": sum(
                row["emitted"] > 0 for row in locale_rows.values()
            ),
            "candidate_app_locale_pairs": (
                len(covered_apps) * len(OFFICIAL_LOCALES)
            ),
            "native_locale_pair_coverage_percent": round(
                len(records)
                / (len(covered_apps) * len(OFFICIAL_LOCALES))
                * 100,
                2,
            ),
            "abstained_pairs": sum(abstention_counts.values()),
            "fallback_records": 0,
            "abstention_reasons": dict(sorted(abstention_counts.items())),
        },
        "quality": {
            "all_gates_passed": all(
                bool(gate["passed"]) for gate in gates.values()
            ),
            "materialization_safe": all(
                bool(gate["passed"])
                for name, gate in gates.items()
                if name != "current_inventory_coverage"
            ),
            "gates": gates,
            "minimum_content_units": min(
                record["content_units"] for record in records
            ),
            "maximum_editorial_jaccard": round(similarity, 6),
            "maximum_similarity_pair": similarity_pair,
        },
        "locales": locale_rows,
        "apps": app_rows,
    }
    if not report["quality"]["all_gates_passed"]:
        failed = [
            name for name, gate in gates.items() if not gate["passed"]
        ]
        allowed = (
            {"current_inventory_coverage"}
            if allow_new_live_app_gaps and inventory_gaps
            else set()
        )
        if set(failed) != allowed:
            raise ValueError(f"High-intent quality gates failed: {failed}")
    return records, report


def _list(items: Iterable[str]) -> str:
    return "".join(f"<li>{html.escape(str(item))}</li>" for item in items)


def render_html(record: dict[str, Any]) -> str:
    locale = str(record["locale"])
    ui = UI[locale]
    title = f"{record['query']} | {record['app_name']}"
    evidence = "".join(
        (
            "<blockquote>"
            f"<p>{html.escape(str(item['text']))}</p>"
            f"<cite>{html.escape(str(ui['source']))}: "
            f"{html.escape(str(item['inventory_pointer']))}</cite>"
            "</blockquote>"
        )
        for item in record["evidence"]
    )
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": f"{record['canonical_url']}#article",
                "url": record["canonical_url"],
                "headline": record["query"],
                "description": record["buyer_problem"],
                "inLanguage": record["language"],
                "author": {
                    "@type": "Organization",
                    "name": "Lumi Studio",
                    "url": f"{SITE}/about.html",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "Lumi Studio",
                    "url": f"{SITE}/about.html",
                },
            },
            {
                "@type": "MobileApplication",
                "name": record["app_name"],
                "operatingSystem": "iOS",
                "applicationCategory": record["category"],
                "downloadUrl": record["app_store_url"],
            },
        ],
    }
    language = html.escape(str(record["language"]))
    description = html.escape(str(record["buyer_problem"]), quote=True)
    canonical = html.escape(str(record["canonical_url"]), quote=True)
    schema_json = json.dumps(
        schema,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    intent_label = html.escape(
        str(ui["intent_types"][record["intent_type"]])
    )
    vocabulary_section = ""
    if record["source_vocabulary"]:
        vocabulary_section = (
            f"<h2>{html.escape(str(ui['vocabulary']))}</h2>\n"
            f"<ul>{_list(record['source_vocabulary'])}</ul>"
        )
    store_url = html.escape(str(record["app_store_url"]), quote=True)
    store_label = html.escape(str(ui["store"]))
    app_name = html.escape(str(record["app_name"]))
    disclosure = html.escape(str(record["publisher_disclosure"]))
    return f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{description}">
<meta name="growth-attribution-intent" content="{html.escape(str(record['intent_type']), quote=True)}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/feed+json" title="High-intent decision routes" href="{SITE}/{FEED_RELATIVE.as_posix()}">
<script type="application/ld+json">{schema_json}</script>
<style>
body{{font:17px/1.65 system-ui,sans-serif;color:#17202a;
background:#f6f8fb;margin:0}}
main{{width:min(860px,92vw);margin:auto;padding:48px 0}}
article,footer{{background:#fff;border:1px solid #dce3ea;border-radius:22px;
padding:clamp(22px,5vw,46px);box-shadow:0 14px 40px #18324a12}}
h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.08}}
h2{{margin-top:2rem}}.eyebrow,cite{{color:#52606d}}
blockquote{{margin:1rem 0;padding:1rem 1.2rem;border-left:4px solid #4169a1;
background:#f7faff}}
.cta{{display:inline-block;margin-top:1.5rem;padding:.9rem 1.2rem;
border-radius:999px;background:#163f72;color:#fff;text-decoration:none;
font-weight:700}}
footer{{margin-top:1rem;font-size:.92rem}}
</style>
</head>
<body data-managed-route="{html.escape(str(record['route_id']), quote=True)}"
 data-record-digest="{_record_digest(record)}">
<main>
<article>
<p class="eyebrow">{html.escape(str(ui['eyebrow']))} · {intent_label} ·
{html.escape(str(record['market']))}</p>
<h1>{html.escape(str(record['query']))}</h1>
<p>{html.escape(str(record['culture_route']))}</p>
<h2>{html.escape(str(ui['situation']))}</h2>
<p>{html.escape(str(record['buyer_problem']))}</p>
<h2>{html.escape(str(ui['rule']))}</h2>
<p>{html.escape(str(record['decision_rule']))}</p>
<h2>{html.escape(str(ui['checks']))}</h2>
<ul>{_list(record['workflow_checks'])}</ul>
<h2>{html.escape(str(ui['alternative']))}</h2>
<p>{html.escape(str(record['alternative_lens']))}</p>
<h2>{html.escape(str(ui['evidence']))}</h2>
{evidence}
{vocabulary_section}
<h2>{html.escape(str(ui['verify']))}</h2>
<ul>{_list(record['verify_before_install'])}</ul>
<a class="cta" rel="noopener" href="{store_url}">{store_label}: {app_name}</a>
</article>
<footer data-publisher-disclosure="true">{disclosure}</footer>
</main>
</body>
</html>
"""


def _json_text(value: object) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def build_sync_contract(engine_root: Path = HERE) -> dict[str, Any]:
    """Describe the exact reviewed files required by the production Guide."""
    files = []
    for relative in SYNC_ENGINE_FILES:
        path = engine_root / relative
        if not path.is_file():
            raise ValueError(f"Sync source is missing: {relative}")
        files.append(
            {
                "engine_relative_path": relative.as_posix(),
                "source_path": (Path("geo") / relative).as_posix(),
                "target_path": (
                    Path("_engine") / "geo" / relative
                ).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    document: dict[str, Any] = {
        "schema_version": SYNC_CONTRACT_SCHEMA_VERSION,
        "owner": MANAGED_OWNER,
        "copy_mode": "byte_for_byte",
        "source_repository": "alice51849/00_GrowthEngine",
        "target_repository": "alice51849/ios-app-guide",
        "files": files,
    }
    document["contract_digest"] = _sha256_json(document)
    return document


def validate_sync_contract(
    contract_path: Path = SYNC_CONTRACT_PATH,
    *,
    engine_root: Path = HERE,
    current_source_root: Path | None = None,
    require_external_source: bool = False,
) -> dict[str, Any]:
    """Fail closed unless local and optional current source match the contract."""
    document = _read_json(contract_path)
    if set(document) != {
        "schema_version",
        "owner",
        "copy_mode",
        "source_repository",
        "target_repository",
        "files",
        "contract_digest",
    }:
        raise ValueError("High-intent sync contract fields differ")
    if (
        document.get("schema_version") != SYNC_CONTRACT_SCHEMA_VERSION
        or document.get("owner") != MANAGED_OWNER
        or document.get("copy_mode") != "byte_for_byte"
        or document.get("source_repository") != "alice51849/00_GrowthEngine"
        or document.get("target_repository") != "alice51849/ios-app-guide"
        or document.get("contract_digest")
        != _sha256_json(
            {
                key: value
                for key, value in document.items()
                if key != "contract_digest"
            }
        )
    ):
        raise ValueError("High-intent sync contract is invalid")
    expected_paths = [path.as_posix() for path in SYNC_ENGINE_FILES]
    entries = document.get("files")
    if not isinstance(entries, list) or [
        entry.get("engine_relative_path")
        for entry in entries
        if isinstance(entry, dict)
    ] != expected_paths:
        raise ValueError("High-intent sync contract file set differs")
    for relative, entry in zip(SYNC_ENGINE_FILES, entries, strict=True):
        if not isinstance(entry, dict) or set(entry) != {
            "engine_relative_path",
            "source_path",
            "target_path",
            "sha256",
        }:
            raise ValueError(f"Invalid sync entry: {relative}")
        expected_source = (Path("geo") / relative).as_posix()
        expected_target = (
            Path("_engine") / "geo" / relative
        ).as_posix()
        path = engine_root / relative
        digest = (
            hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else None
        )
        if (
            entry["source_path"] != expected_source
            or entry["target_path"] != expected_target
            or not isinstance(entry["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
            or digest != entry["sha256"]
        ):
            raise ValueError(f"High-intent sync drift: {relative}")
    if require_external_source and current_source_root is None:
        raise ValueError(
            "Pages preparation requires a separately checked-out current "
            "GrowthEngine source"
        )
    if current_source_root is not None:
        source_root = current_source_root.resolve()
        if source_root == engine_root.resolve():
            raise ValueError(
                "Current GrowthEngine source must be a separate checkout, "
                "not the Guide mirror itself"
            )
        source_contract_path = (
            source_root / "data" / SYNC_CONTRACT_PATH.name
        )
        if (
            not source_contract_path.is_file()
            or source_contract_path.is_symlink()
            or source_contract_path.read_bytes() != contract_path.read_bytes()
        ):
            raise ValueError(
                "Current GrowthEngine sync contract differs from the Guide "
                "copy"
            )
        for relative, entry in zip(SYNC_ENGINE_FILES, entries, strict=True):
            source_file = source_root / relative
            digest = (
                hashlib.sha256(source_file.read_bytes()).hexdigest()
                if source_file.is_file() and not source_file.is_symlink()
                else None
            )
            if digest != entry["sha256"]:
                raise ValueError(
                    f"Current GrowthEngine source digest drift: {relative}"
                )
    return document


def write_sync_contract(
    path: Path = SYNC_CONTRACT_PATH,
    *,
    engine_root: Path = HERE,
) -> dict[str, Any]:
    document = build_sync_contract(engine_root)
    _atomic_write_text(path, _json_text(document))
    return document


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record_digest(record: dict[str, Any]) -> str:
    return _sha256_json(
        {
            key: record[key]
            for key in (
                "route_id",
                "app_key",
                "app_store_id",
                "locale",
                "intent_type",
                "campaign_token",
                "creative_id",
                "creative_digest",
                "route_slug",
                "canonical_url",
                "app_store_url",
                "query",
                "culture_route",
                "buyer_problem",
                "decision_rule",
                "workflow_checks",
                "alternative_lens",
                "verify_before_install",
                "evidence",
            )
        }
    )


def render_feed(records: Iterable[dict[str, Any]]) -> str:
    ordered = sorted(records, key=lambda item: str(item["route_id"]))
    document = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Lumi Studio high-intent app decision routes",
        "home_page_url": SITE,
        "feed_url": f"{SITE}/{FEED_RELATIVE.as_posix()}",
        "description": (
            "First-party, source-bound app decision routes published by "
            "Lumi Studio."
        ),
        "hubs": [
            {"type": "WebSub", "url": hub}
            for hub in WEBSUB_HUBS
        ],
        "items": [
            {
                "id": record["route_id"],
                "url": record["canonical_url"],
                "title": record["query"],
                "summary": record["buyer_problem"],
                "language": record["language"],
                "_lumi_route": {
                    "app_key": record["app_key"],
                    "locale": record["locale"],
                    "intent_type": record["intent_type"],
                    "campaign_token": record["campaign_token"],
                    "record_digest": _record_digest(record),
                },
            }
            for record in ordered
        ],
    }
    return _json_text(document)


def render_sitemap(records: Iterable[dict[str, Any]]) -> str:
    urls = sorted(str(record["canonical_url"]) for record in records)
    body = "\n".join(
        f"  <url><loc>{html.escape(url, quote=False)}</loc></url>" for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def _validated_relative_path(value: object) -> PurePosixPath:
    if type(value) is not str or not value:
        raise ValueError("Managed output relative_path must be nonempty text")
    if (
        "\\" in value
        or any(character in PERCENT_CONFUSABLES for character in value)
        or any(
            ord(character) < 0x20
            or 0x7F <= ord(character) <= 0x9F
            for character in value
        )
    ):
        raise ValueError(
            f"Managed output relative_path is unsafe: {value!r}"
        )
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise ValueError(
            f"Managed output relative_path is unsafe: {value!r}"
        )
    relative = PurePosixPath(value)
    if relative.is_absolute() or relative.as_posix() != value:
        raise ValueError(
            f"Managed output relative_path is unsafe: {value!r}"
        )
    return relative


def _validate_output_containment(
    output_dir: Path,
    relative: PurePosixPath,
) -> None:
    try:
        root = output_dir.resolve(strict=False)
        target = root.joinpath(*relative.parts).resolve(strict=False)
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError(
            f"Managed output escapes output directory: {relative}"
        ) from error


def _is_managed_route(relative: PurePosixPath | Path) -> bool:
    return (
        not relative.is_absolute()
        and len(relative.parts) == 4
        and relative.parts[0] in OFFICIAL_LOCALES
        and relative.parts[1] == "decide"
        and all(part not in {"", ".", ".."} for part in relative.parts)
        and relative.suffix == ".html"
    )


def _validated_managed_outputs(
    entries: object,
    *,
    output_dir: Path | None = None,
) -> dict[PurePosixPath, dict[str, Any]]:
    if not isinstance(entries, list):
        raise ValueError("Managed high-intent outputs must be a list")
    outputs: dict[PurePosixPath, dict[str, Any]] = {}
    fixed_outputs: dict[str, str] = {}
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Managed output entry {position} must be an object"
            )
        kind = entry.get("kind")
        if (
            type(kind) is not str
            or not kind
            or kind not in MANAGED_OUTPUT_KINDS
        ):
            raise ValueError(
                f"Managed output entry {position} has an invalid kind"
            )
        relative = _validated_relative_path(entry.get("relative_path"))
        if output_dir is not None:
            _validate_output_containment(output_dir, relative)
        if kind == "route_html":
            safe = _is_managed_route(relative)
        else:
            safe = (
                FIXED_MANAGED_OUTPUTS.get(relative.as_posix()) == kind
            )
            if safe:
                fixed_outputs[relative.as_posix()] = kind
        digest = entry.get("generated_sha256")
        if (
            not safe
            or type(digest) is not str
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise ValueError(f"Unsafe managed output entry: {entry}")
        if relative in outputs:
            raise ValueError(
                f"Duplicate managed output entry: {relative}"
            )
        outputs[relative] = entry
    if fixed_outputs != FIXED_MANAGED_OUTPUTS:
        raise ValueError(
            "Managed fixed outputs do not exactly match the contract"
        )
    return outputs


def _managed_route_target(output_dir: Path, relative: Path) -> Path:
    if not _is_managed_route(relative):
        raise ValueError(f"Unsafe managed route output: {relative}")
    root = output_dir.resolve()
    target = root / relative
    try:
        target.parent.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"Managed route parent escapes output directory: {relative}"
        ) from error
    if target.is_symlink():
        raise ValueError(f"Managed route target may not be a symlink: {relative}")
    return target


def _manifest_without_digest(document: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in document.items() if key != "manifest_digest"
    }


def _validate_manifest(
    document: dict[str, Any],
    *,
    output_dir: Path | None = None,
) -> None:
    if (
        document.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or document.get("owner") != MANAGED_OWNER
        or document.get("deployment_state") != "generated_not_deployed"
        or document.get("release_state")
        not in {RELEASE_STATE_EXACT, RELEASE_STATE_INVENTORY_GAP}
        or not isinstance(document.get("release_contract_digest"), str)
        or re.fullmatch(
            r"[0-9a-f]{64}",
            document["release_contract_digest"],
        )
        is None
        or not isinstance(document.get("source_contract_digest"), str)
        or re.fullmatch(
            r"[0-9a-f]{64}",
            document["source_contract_digest"],
        )
        is None
        or not isinstance(document.get("expected_outputs"), list)
        or not isinstance(document.get("routes"), list)
    ):
        raise ValueError("Managed high-intent manifest contract is invalid")
    expected = _sha256_json(_manifest_without_digest(document))
    if document.get("manifest_digest") != expected:
        raise ValueError("Managed high-intent manifest digest is invalid")
    current_inventory = document.get("current_inventory")
    if not isinstance(current_inventory, dict) or set(current_inventory) != {
        "public_apps",
        "app_keys_sha256",
        "copy_sha256",
        "missing_route_app_keys",
        "missing_route_app_keys_sha256",
    }:
        raise ValueError("Managed current inventory contract is invalid")
    gaps = current_inventory.get("missing_route_app_keys")
    if (
        type(current_inventory.get("public_apps")) is not int
        or current_inventory["public_apps"] < 1
        or not isinstance(gaps, list)
        or any(
            not isinstance(key, str)
            or re.fullmatch(r"[a-z0-9][a-z0-9_-]*", key) is None
            for key in gaps
        )
        or gaps != sorted(set(gaps))
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(current_inventory.get(field)))
            is None
            for field in (
                "app_keys_sha256",
                "copy_sha256",
                "missing_route_app_keys_sha256",
            )
        )
        or current_inventory["missing_route_app_keys_sha256"]
        != _sha256_json(gaps)
        or (
            document["release_state"] == RELEASE_STATE_EXACT
            and gaps
        )
        or (
            document["release_state"] == RELEASE_STATE_INVENTORY_GAP
            and not gaps
        )
    ):
        raise ValueError("Managed current inventory digest is invalid")
    outputs = _validated_managed_outputs(
        document["expected_outputs"],
        output_dir=output_dir,
    )
    route_paths: list[PurePosixPath] = []
    for position, route in enumerate(document["routes"]):
        if not isinstance(route, dict):
            raise ValueError(
                f"Managed route entry {position} must be an object"
            )
        relative = _validated_relative_path(route.get("relative_path"))
        if not _is_managed_route(relative):
            raise ValueError(
                f"Managed route entry {position} has an unsafe path"
            )
        if output_dir is not None:
            _validate_output_containment(output_dir, relative)
        output = outputs.get(relative)
        if output is None or output.get("kind") != "route_html":
            raise ValueError(
                f"Managed route entry {position} lacks its route output"
            )
        route_paths.append(relative)
    route_outputs = {
        relative
        for relative, entry in outputs.items()
        if entry["kind"] == "route_html"
    }
    if (
        len(route_paths) != len(set(route_paths))
        or set(route_paths) != route_outputs
    ):
        raise ValueError(
            "Managed route outputs do not exactly match manifest routes"
        )


def _previous_managed_routes(output_dir: Path) -> set[Path]:
    path = output_dir / MANIFEST_RELATIVE
    if not path.exists():
        return set()
    document = _read_json(path)
    _validate_manifest(document, output_dir=output_dir)
    managed: set[Path] = set()
    for entry in document["expected_outputs"]:
        if entry.get("kind") != "route_html":
            continue
        relative = _validated_relative_path(entry.get("relative_path"))
        managed.add(Path(*relative.parts))
    return managed


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.unlink(missing_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(pending, flags, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        pending.unlink(missing_ok=True)


def _expected_manifest(
    records: list[dict[str, Any]],
    report: dict[str, Any],
    rendered: dict[Path, tuple[str, str]],
) -> dict[str, Any]:
    source_contract = validate_sync_contract()
    routes = [
        {
            "route_id": record["route_id"],
            "app_key": record["app_key"],
            "app_store_id": record["app_store_id"],
            "app_store_url": record["app_store_url"],
            "locale": record["locale"],
            "intent_type": record["intent_type"],
            "campaign_token": record["campaign_token"],
            "creative_id": record["creative_id"],
            "creative_digest": record["creative_digest"],
            "content_type": record["intent_type"],
            "route_slug": record["route_slug"],
            "relative_path": route_relative(record).as_posix(),
            "url": record["canonical_url"],
            "record_digest": _record_digest(record),
            "output_sha256": _sha256_text(
                rendered[route_relative(record)][1]
            ),
        }
        for record in sorted(records, key=lambda item: str(item["route_id"]))
    ]
    outputs = [
        {
            "kind": kind,
            "relative_path": relative.as_posix(),
            "generated_sha256": _sha256_text(text),
        }
        for relative, (kind, text) in sorted(
            rendered.items(),
            key=lambda item: item[0].as_posix(),
        )
    ]
    document = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "owner": MANAGED_OWNER,
        "deployment_state": "generated_not_deployed",
        "release_state": report["release_state"],
        "release_contract_digest": report["release_contract_digest"],
        "source_contract_digest": source_contract["contract_digest"],
        "site": SITE,
        "dataset": report["dataset"],
        "inventory": report["inventory"],
        "current_inventory": report["current_inventory"],
        "route_count": len(routes),
        "app_count": report["coverage"]["mapped_apps"],
        "creative_count": len(
            {str(route["creative_id"]) for route in routes}
        ),
        "candidate_app_locale_pairs": report["coverage"][
            "candidate_app_locale_pairs"
        ],
        "fallback_records": report["coverage"]["fallback_records"],
        "abstained_pairs": report["coverage"]["abstained_pairs"],
        "expected_outputs": outputs,
        "routes": routes,
    }
    document["manifest_digest"] = _sha256_json(document)
    return document


def _rendered_outputs(
    records: list[dict[str, Any]],
    report: dict[str, Any],
    output_dir: Path,
) -> tuple[dict[Path, tuple[str, str]], dict[str, Any]]:
    rendered: dict[Path, tuple[str, str]] = {}
    for record in records:
        relative = route_relative(record)
        target = _managed_route_target(output_dir, relative)
        text = render_html(record)
        try:
            previous = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            previous = ""
        if previous:
            text = sync_standard_site.preserve_managed_links(
                previous,
                text,
                label=relative.as_posix(),
            )
        rendered[relative] = ("route_html", text)
    publication_report = {
        **report,
        "publication": {
            "state": report["release_state"],
            "deployment_eligible": (
                report["release_state"] == RELEASE_STATE_EXACT
            ),
            "managed_owner": MANAGED_OWNER,
            "expected_route_pages": len(records),
            "feed_items": len(records),
            "sitemap_urls": len(records),
            "fallback_records": report["coverage"]["fallback_records"],
            "abstained_pairs": report["coverage"]["abstained_pairs"],
        },
    }
    rendered[COVERAGE_RELATIVE] = (
        "coverage_report",
        _json_text(publication_report),
    )
    rendered[FEED_RELATIVE] = ("json_feed", render_feed(records))
    rendered[SITEMAP_RELATIVE] = ("sitemap", render_sitemap(records))
    return rendered, _expected_manifest(records, report, rendered)


def write_outputs(
    records: Iterable[dict[str, Any]],
    report: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Atomically emit one complete managed generation, then prune known stale pages."""
    output_dir = output_dir.resolve()
    ordered = sorted(records, key=lambda item: str(item["route_id"]))
    previous = _previous_managed_routes(output_dir)
    rendered, manifest = _rendered_outputs(ordered, report, output_dir)

    for relative, (_, text) in sorted(
        rendered.items(),
        key=lambda item: item[0].as_posix(),
    ):
        _atomic_write_text(output_dir / relative, text)

    current = {route_relative(record) for record in ordered}
    stale = sorted(previous - current, key=lambda path: path.as_posix())
    for relative in stale:
        target = _managed_route_target(output_dir, relative)
        target.unlink(missing_ok=True)
        if target.parent.is_dir() and not any(target.parent.iterdir()):
            target.parent.rmdir()

    _atomic_write_text(output_dir / MANIFEST_RELATIVE, _json_text(manifest))
    return {
        "written_pages": len(ordered),
        "stale_routes_removed": len(stale),
        "manifest_digest": manifest["manifest_digest"],
    }


def _validate_release_cardinality(
    manifest: dict[str, Any],
    *,
    source_path: Path = SOURCE_PATH,
) -> None:
    _validate_manifest(manifest)
    routes = manifest.get("routes")
    outputs = manifest.get("expected_outputs")
    if not isinstance(routes, list) or not isinstance(outputs, list):
        raise ValueError("High-intent release routes or outputs are missing")
    output_by_path = _validated_managed_outputs(outputs)
    validated_route_paths: list[PurePosixPath] = []
    for position, route in enumerate(routes):
        if not isinstance(route, dict) or set(route) != MANIFEST_ROUTE_FIELDS:
            raise ValueError(
                f"High-intent route {position} fields differ from contract"
            )
        relative = _validated_relative_path(route.get("relative_path"))
        if not _is_managed_route(relative):
            raise ValueError(
                f"High-intent route {position} has an unsafe path"
            )
        validated_route_paths.append(relative)
    expectations = release_expectations(load_route_source(source_path))
    route_ids = [str(route.get("route_id")) for route in routes]
    route_urls = [str(route.get("url")) for route in routes]
    route_paths = [path.as_posix() for path in validated_route_paths]
    app_keys = {str(route.get("app_key")) for route in routes}
    creative_ids = {str(route.get("creative_id")) for route in routes}
    if (
        manifest.get("release_state") != RELEASE_STATE_EXACT
        or manifest.get("release_contract_digest")
        != expectations["release_contract_digest"]
        or manifest.get("route_count") != expectations["route_count"]
        or len(routes) != expectations["route_count"]
        or len(route_ids) != len(set(route_ids))
        or set(route_ids) != set(expectations["route_ids"])
        or len(route_urls) != len(set(route_urls))
        or len(route_paths) != len(set(route_paths))
        or manifest.get("app_count") != expectations["app_count"]
        or app_keys != set(expectations["app_keys"])
        or manifest.get("creative_count") != expectations["creative_count"]
        or len(creative_ids) != expectations["creative_count"]
        or manifest.get("candidate_app_locale_pairs")
        != expectations["candidate_app_locale_pairs"]
        or manifest.get("abstained_pairs")
        != expectations["abstained_pairs"]
        or manifest.get("fallback_records") != 0
        or len(outputs) != expectations["managed_output_count"]
    ):
        raise ValueError(
            "High-intent release cardinality differs from the versioned "
            f"route source: routes={expectations['route_count']}, "
            f"apps={expectations['app_count']}, "
            f"pairs={expectations['candidate_app_locale_pairs']}, "
            f"abstentions={expectations['abstained_pairs']}, "
            f"outputs={expectations['managed_output_count']}"
        )
    source_contract = validate_sync_contract()
    if (
        manifest.get("source_contract_digest")
        != source_contract["contract_digest"]
    ):
        raise ValueError(
            "High-intent release does not match the current source contract"
        )
    inventory = manifest.get("inventory")
    if (
        not isinstance(inventory, dict)
        or inventory.get("public_apps") != expectations["app_count"]
        or inventory.get("app_keys_sha256")
        != expectations["app_keys_sha256"]
        or inventory.get("copy_sha256") != expectations["copy_sha256"]
        or inventory.get("official_locales_sha256")
        != expectations["official_locales_sha256"]
    ):
        raise ValueError(
            "High-intent release inventory digest differs from route source"
        )
    current_inventory = manifest.get("current_inventory")
    if (
        not isinstance(current_inventory, dict)
        or current_inventory.get("public_apps") != expectations["app_count"]
        or current_inventory.get("app_keys_sha256")
        != expectations["app_keys_sha256"]
        or current_inventory.get("copy_sha256")
        != expectations["copy_sha256"]
        or current_inventory.get("missing_route_app_keys") != []
        or current_inventory.get("missing_route_app_keys_sha256")
        != _sha256_json([])
    ):
        raise ValueError(
            "High-intent release is not exact for the current inventory"
        )

    route_output_count = 0
    for relative, entry in output_by_path.items():
        kind = entry.get("kind")
        if kind == "route_html":
            route_output_count += 1
        elif FIXED_MANAGED_OUTPUTS.get(relative.as_posix()) != kind:
            raise ValueError(
                f"Unexpected high-intent managed output: {relative}"
            )
    if (
        route_output_count != expectations["route_count"]
        or {
            path
            for path, entry in output_by_path.items()
            if entry.get("kind") != "route_html"
        }
        != {PurePosixPath(path) for path in FIXED_MANAGED_OUTPUTS}
    ):
        raise ValueError(
            "High-intent release output set does not exactly cover every "
            "versioned route plus the fixed managed outputs"
        )

    app_ids: dict[str, str] = {}
    app_creatives: dict[str, str] = {}
    for position, (route, relative) in enumerate(
        zip(routes, validated_route_paths, strict=True)
    ):
        app = str(route["app_key"])
        app_id = str(route["app_store_id"])
        locale = str(route["locale"])
        slug = str(route["route_slug"])
        campaign = str(route["campaign_token"])
        creative_id = str(route["creative_id"])
        output = output_by_path.get(relative)
        parsed_store = urlsplit(str(route["app_store_url"]))
        store_parameters = parse_qsl(
            parsed_store.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
        if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", app) is None:
            raise ValueError(f"Invalid high-intent App key: {app}")
        if (
            not app_id.isdigit()
            or relative.is_absolute()
            or not _is_managed_route(relative)
            or relative.parts[:3] != (locale, "decide", app)
            or relative.stem != slug
            or route["route_id"] != f"{locale}:{app}:{slug}"
            or route["url"] != f"{SITE}/{relative.as_posix()}"
            or route["content_type"] != route["intent_type"]
            or campaign != campaign_token(str(route["intent_type"]))
            or not creative_id.startswith(f"{app}:")
            or re.fullmatch(r"[0-9a-f]{64}", str(route["creative_digest"]))
            is None
            or re.fullmatch(r"[0-9a-f]{64}", str(route["record_digest"]))
            is None
            or re.fullmatch(r"[0-9a-f]{64}", str(route["output_sha256"]))
            is None
            or output is None
            or output.get("kind") != "route_html"
            or output.get("generated_sha256") != route["output_sha256"]
            or [key for key, _ in store_parameters] != ["pt", "ct", "mt"]
            or not store_parameters[0][1]
            or store_parameters[1][1] != campaign
            or store_parameters[2][1] != "8"
        ):
            raise ValueError(
                f"High-intent route {position} identity or attribution drifted"
            )
        app_store_storefronts.validated_app_store_url(
            str(route["app_store_url"]),
            expected_app_id=app_id,
        )
        if app in app_ids and app_ids[app] != app_id:
            raise ValueError(f"High-intent App ID drifted across routes: {app}")
        if app in app_creatives and app_creatives[app] != creative_id:
            raise ValueError(
                f"High-intent creative drifted across locales: {app}"
            )
        app_ids[app] = app_id
        app_creatives[app] = creative_id
    if set(app_ids) != set(expectations["app_keys"]):
        raise ValueError(
            "High-intent release App IDs do not exactly cover route source"
        )


def verify_production_closure(
    output_dir: Path,
    *,
    strict_release: bool = True,
    expected_manifest: dict[str, Any] | None = None,
    inventory_path: Path | None = None,
    source_path: Path = SOURCE_PATH,
    provider_token: str | None = None,
) -> dict[str, int]:
    """Verify the built routes reached feed, sitemap and final attribution gates."""
    output_dir = output_dir.resolve()
    manifest = _read_json(output_dir / MANIFEST_RELATIVE)
    _validate_manifest(manifest, output_dir=output_dir)
    if strict_release:
        _validate_release_cardinality(manifest, source_path=source_path)
        if expected_manifest is None:
            validate_sync_contract()
            provider_token = (
                provider_token
                or app_store_storefronts.resolve_provider_token()
            )
            if not provider_token:
                raise ValueError(
                    "A provider token is required to recompute the immutable "
                    "pre-upload release"
                )
            records, report = build(
                inventory_path=(
                    inventory_path
                    or output_dir / "data" / INVENTORY_FILENAME
                ),
                source_path=source_path,
                provider_token=provider_token,
            )
            _, expected_manifest = _rendered_outputs(
                sorted(records, key=lambda item: str(item["route_id"])),
                report,
                output_dir,
            )
    if expected_manifest is not None and manifest != expected_manifest:
        raise ValueError(
            "Generated high-intent manifest drifted from the current "
            "immutable source, inventory, or sync contract"
        )
    routes = manifest["routes"]
    if manifest.get("route_count") != len(routes):
        raise ValueError("High-intent manifest route count is inconsistent")

    expected_outputs = {
        Path(*relative.parts): entry
        for relative, entry in _validated_managed_outputs(
            manifest["expected_outputs"],
            output_dir=output_dir,
        ).items()
    }
    expected_paths = set(expected_outputs)
    missing = sorted(
        relative.as_posix()
        for relative in expected_paths
        if not (output_dir / relative).is_file()
        or (output_dir / relative).stat().st_size == 0
    )
    if missing:
        raise ValueError(f"High-intent expected outputs are missing: {missing}")
    drifted = sorted(
        relative.as_posix()
        for relative, entry in expected_outputs.items()
        if hashlib.sha256((output_dir / relative).read_bytes()).hexdigest()
        != entry["generated_sha256"]
    )
    if drifted:
        raise ValueError(
            f"High-intent generated output digest drift: {drifted}"
        )

    feed = _read_json(output_dir / FEED_RELATIVE)
    feed_ids = {
        str(item.get("id"))
        for item in feed.get("items", [])
        if isinstance(item, dict)
    }
    route_ids = {str(route["route_id"]) for route in routes}
    if feed_ids != route_ids:
        raise ValueError("High-intent feed does not exactly cover managed routes")

    sitemap_text = (output_dir / SITEMAP_RELATIVE).read_text(encoding="utf-8")
    sitemap_urls = set(
        html.unescape(value)
        for value in re.findall(r"<loc>([^<]+)</loc>", sitemap_text)
    )
    route_urls = {str(route["url"]) for route in routes}
    if sitemap_urls != route_urls:
        raise ValueError("High-intent sitemap does not exactly cover managed routes")

    sitemap_index = (output_dir / SITEMAP_INDEX_RELATIVE).read_text(
        encoding="utf-8"
    )
    expected_sitemap_url = f"{SITE}/{SITEMAP_RELATIVE.as_posix()}"
    if expected_sitemap_url not in sitemap_index:
        raise ValueError("High-intent sitemap is absent from the sitemap index")

    for route in routes:
        relative = Path(str(route["relative_path"]))
        page = _managed_route_target(output_dir, relative).read_text(
            encoding="utf-8"
        )
        marker = (
            f'data-managed-route="{html.escape(str(route["route_id"]), quote=True)}"'
        )
        if marker not in page:
            raise ValueError(f"Managed route marker is missing: {relative}")
        digest_marker = (
            f'data-record-digest="{route["record_digest"]}"'
        )
        if digest_marker not in page:
            raise ValueError(f"Route record digest marker is missing: {relative}")
        ctas = [
            html.unescape(url)
            for url in re.findall(
                r'<a class="cta"[^>]+href="(https://apps\.apple\.com/[^"]+)"',
                page,
            )
        ]
        if len(ctas) != 1:
            raise ValueError(f"Route must have exactly one direct CTA: {relative}")
        cta = ctas[0]
        if cta != route["app_store_url"]:
            raise ValueError(
                f"Route CTA differs from the immutable manifest: {relative}"
            )
        app_store_storefronts.validated_app_store_url(
            cta,
            expected_app_id=str(route["app_store_id"]),
        )
        parameters = parse_qsl(
            urlsplit(cta).query,
            keep_blank_values=True,
            strict_parsing=True,
        )
        if (
            [key for key, _ in parameters] != ["pt", "ct", "mt"]
            or not parameters[0][1]
            or parameters[1][1] != route["campaign_token"]
            or parameters[2][1] != "8"
        ):
            raise ValueError(
                f"Final attribution differs from route intent: {relative}"
            )
        expected = gen_store_attribution.campaign_token(
            relative.as_posix(),
            page,
        )
        if expected != route["campaign_token"]:
            raise ValueError(
                f"Site-wide attribution contract differs for {relative}"
            )
    return {
        "routes": len(routes),
        "feed_items": len(feed_ids),
        "sitemap_urls": len(sitemap_urls),
        "attribution_routes": len(routes),
    }


def verify_materialization_closure(
    output_dir: Path,
    *,
    inventory_path: Path,
    source_path: Path,
    provider_token: str,
) -> dict[str, Any]:
    """Verify an exact or explicitly degraded daily materialization."""
    records, report = build(
        inventory_path=inventory_path,
        source_path=source_path,
        provider_token=provider_token,
        allow_new_live_app_gaps=True,
    )
    _, expected_manifest = _rendered_outputs(
        sorted(records, key=lambda item: str(item["route_id"])),
        report,
        output_dir.resolve(),
    )
    closure = verify_production_closure(
        output_dir,
        strict_release=False,
        expected_manifest=expected_manifest,
    )
    return {
        **closure,
        "release_state": report["release_state"],
        "missing_route_apps": report["coverage"]["missing_route_apps"],
        "missing_route_app_keys": report["coverage"][
            "missing_route_app_keys"
        ],
        "deployment_eligible": (
            report["release_state"] == RELEASE_STATE_EXACT
        ),
    }


def prepare_pages_deployment(
    output_dir: Path,
    *,
    inventory_path: Path,
    source_path: Path,
    provider_token: str,
    source_commit: str,
    current_source_root: Path,
    engine_source_revision: str,
) -> dict[str, Any]:
    """Regenerate and verify the exact immutable release before Pages upload."""
    if re.fullmatch(r"[0-9a-f]{40,64}", source_commit) is None:
        raise ValueError("source_commit must be a full lowercase Git object ID")
    if re.fullmatch(r"[0-9a-f]{40,64}", engine_source_revision) is None:
        raise ValueError(
            "engine_source_revision must be a full lowercase Git object ID"
        )
    source_contract = validate_sync_contract(
        current_source_root=current_source_root,
        require_external_source=True,
    )
    records, report = build(
        inventory_path=inventory_path,
        source_path=source_path,
        provider_token=provider_token,
    )
    ordered = sorted(records, key=lambda item: str(item["route_id"]))
    _, expected_manifest = _rendered_outputs(ordered, report, output_dir.resolve())
    generation_was_current = False
    manifest_path = output_dir.resolve() / MANIFEST_RELATIVE
    if manifest_path.is_file():
        try:
            previous = _read_json(manifest_path)
            generation_was_current = previous == expected_manifest and all(
                (
                    output_dir.resolve() / str(entry["relative_path"])
                ).is_file()
                and hashlib.sha256(
                    (
                        output_dir.resolve() / str(entry["relative_path"])
                    ).read_bytes()
                ).hexdigest()
                == entry["generated_sha256"]
                for entry in previous.get("expected_outputs", [])
                if isinstance(entry, dict)
            )
        except (OSError, ValueError):
            generation_was_current = False
    write_stats = write_outputs(ordered, report, output_dir)

    from close_sitemap_graph import close_graph  # noqa: PLC0415

    close_graph(output_dir.resolve())
    closure = verify_production_closure(
        output_dir,
        strict_release=True,
        expected_manifest=expected_manifest,
        source_path=source_path,
    )
    deployment = {
        "version": DEPLOYMENT_SCHEMA_VERSION,
        "generated_at": (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "deployment_id": deployment_identity(
            expected_manifest["manifest_digest"]
        ),
        "source_commit": source_commit,
        "engine_source_revision": engine_source_revision,
        "source_contract_digest": source_contract["contract_digest"],
        "route_manifest_digest": expected_manifest["manifest_digest"],
        "route_count": expected_manifest["route_count"],
        "app_count": expected_manifest["app_count"],
        "candidate_app_locale_pairs": expected_manifest[
            "candidate_app_locale_pairs"
        ],
        "abstained_pairs": expected_manifest["abstained_pairs"],
        "fallback_records": 0,
    }
    _atomic_write_text(
        output_dir.resolve() / DEPLOYMENT_RELATIVE,
        _json_text(deployment),
    )
    return {
        **write_stats,
        **closure,
        "regenerated_for_source_drift": not generation_was_current,
        "deployment_id": deployment["deployment_id"],
    }


def _select(
    records: list[dict[str, Any]],
    app_keys: list[str],
    locales: list[str],
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = [
        record
        for record in records
        if (not app_keys or record["app_key"] in app_keys)
        and (not locales or record["locale"] in locales)
    ]
    if app_keys:
        unknown = set(app_keys) - {str(record["app_key"]) for record in records}
        if unknown:
            raise ValueError(f"No emitted native route for apps: {sorted(unknown)}")
    if locales:
        unknown = set(locales) - set(OFFICIAL_LOCALES)
        if unknown:
            raise ValueError(f"Unsupported locales: {sorted(unknown)}")
    return selected[:limit] if limit is not None else selected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=PAGES / "data" / INVENTORY_FILENAME,
    )
    parser.add_argument("--routes", type=Path, default=SOURCE_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check-production-closure", action="store_true")
    parser.add_argument(
        "--materialize-current-inventory",
        action="store_true",
    )
    parser.add_argument(
        "--check-materialization-closure",
        action="store_true",
    )
    parser.add_argument("--prepare-pages-deployment", action="store_true")
    parser.add_argument("--source-commit")
    parser.add_argument("--current-source-root", type=Path)
    parser.add_argument("--engine-source-revision")
    parser.add_argument("--write-sync-contract", action="store_true")
    parser.add_argument("--coverage-report", type=Path)
    parser.add_argument("--app-key", action="append", default=[])
    parser.add_argument("--locale", action="append", default=[])
    parser.add_argument("--limit", type=int)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if args.write_sync_contract:
        if (
            args.dry_run
            or args.output_dir is not None
            or args.check_production_closure
            or args.materialize_current_inventory
            or args.check_materialization_closure
            or args.prepare_pages_deployment
            or args.source_commit is not None
            or args.current_source_root is not None
            or args.engine_source_revision is not None
            or args.coverage_report is not None
            or args.app_key
            or args.locale
            or args.limit is not None
        ):
            parser.error("sync contract writing cannot be combined with generation")
        contract = write_sync_contract()
        print(json.dumps(contract, ensure_ascii=False, sort_keys=True))
        return 0
    validate_sync_contract()
    if args.prepare_pages_deployment:
        if (
            args.dry_run
            or args.check_production_closure
            or args.materialize_current_inventory
            or args.check_materialization_closure
            or args.coverage_report is not None
            or args.app_key
            or args.locale
            or args.limit is not None
            or args.output_dir is None
            or args.source_commit is None
            or args.current_source_root is None
            or args.engine_source_revision is None
        ):
            parser.error(
                "Pages preparation requires --output-dir, --source-commit, "
                "--current-source-root, and --engine-source-revision"
            )
        provider_token = app_store_storefronts.resolve_provider_token()
        if not provider_token:
            parser.error(
                "APP_STORE_PROVIDER_TOKEN or the private provider-token file "
                "is required for the Pages pre-upload gate"
            )
        stats = prepare_pages_deployment(
            args.output_dir,
            inventory_path=args.inventory,
            source_path=args.routes,
            provider_token=provider_token,
            source_commit=args.source_commit,
            current_source_root=args.current_source_root,
            engine_source_revision=args.engine_source_revision,
        )
        print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
        return 0
    if (
        args.source_commit is not None
        or args.current_source_root is not None
        or args.engine_source_revision is not None
    ):
        parser.error(
            "source binding arguments require --prepare-pages-deployment"
        )
    if args.check_production_closure:
        if (
            args.dry_run
            or args.materialize_current_inventory
            or args.check_materialization_closure
            or args.app_key
            or args.locale
            or args.limit
        ):
            parser.error("closure checks cannot be combined with selection/dry-run")
        stats = verify_production_closure(args.output_dir or PAGES)
        print(json.dumps(stats, sort_keys=True))
        return 0
    if args.check_materialization_closure:
        if (
            args.dry_run
            or args.materialize_current_inventory
            or args.app_key
            or args.locale
            or args.limit
        ):
            parser.error(
                "materialization closure cannot be combined with generation "
                "or selection"
            )
        provider_token = app_store_storefronts.resolve_provider_token()
        if not provider_token:
            parser.error(
                "APP_STORE_PROVIDER_TOKEN or the private provider-token file "
                "is required for materialization closure"
            )
        stats = verify_materialization_closure(
            args.output_dir or PAGES,
            inventory_path=args.inventory,
            source_path=args.routes,
            provider_token=provider_token,
        )
        print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
        return 0
    if args.dry_run == (args.output_dir is not None):
        parser.error("choose exactly one of --dry-run or --output-dir")
    if args.materialize_current_inventory and args.output_dir is None:
        parser.error(
            "--materialize-current-inventory requires --output-dir"
        )
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.output_dir is not None and (
        args.app_key or args.locale or args.limit is not None
    ):
        parser.error("managed emission must include the complete generation")
    provider_token = app_store_storefronts.resolve_provider_token()
    if not provider_token:
        parser.error(
            "APP_STORE_PROVIDER_TOKEN or the private provider-token file is "
            "required for complete pt/ct/mt=8 links"
        )
    records, report = build(
        inventory_path=args.inventory,
        source_path=args.routes,
        provider_token=provider_token,
        allow_new_live_app_gaps=args.materialize_current_inventory,
    )
    selected = _select(records, args.app_key, args.locale, args.limit)
    for record in selected:
        render_html(record)
    write_stats = {
        "written_pages": 0,
        "stale_routes_removed": 0,
        "manifest_digest": None,
    }
    if args.output_dir is not None:
        write_stats = write_outputs(selected, report, args.output_dir)
    managed_coverage = (
        (args.output_dir.resolve() / COVERAGE_RELATIVE)
        if args.output_dir is not None
        else None
    )
    if (
        args.coverage_report is not None
        and (
            managed_coverage is None
            or args.coverage_report.resolve() != managed_coverage
        )
    ):
        _atomic_write_text(
            args.coverage_report,
            _json_text(
                {
                    **report,
                    "publication": {
                        "state": report["release_state"],
                        "deployment_eligible": (
                            report["release_state"] == RELEASE_STATE_EXACT
                        ),
                        "managed_owner": MANAGED_OWNER,
                    },
                }
            ),
        )
    print(
        json.dumps(
            {
                "mode": "dry-run" if args.dry_run else "emit",
                "release_state": report["release_state"],
                "deployment_eligible": (
                    report["release_state"] == RELEASE_STATE_EXACT
                ),
                "missing_route_apps": report["coverage"][
                    "missing_route_apps"
                ],
                "selected_records": len(selected),
                **write_stats,
                "mapped_apps": report["coverage"]["mapped_apps"],
                "app_coverage_percent": report["coverage"][
                    "app_coverage_percent"
                ],
                "native_locale_records": report["coverage"][
                    "native_locale_records"
                ],
                "candidate_app_locale_pairs": report["coverage"][
                    "candidate_app_locale_pairs"
                ],
                "abstained_pairs": report["coverage"]["abstained_pairs"],
                "quality_gates_passed": report["quality"][
                    "all_gates_passed"
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
