#!/usr/bin/env python3
"""Pure rules for constructing and validating the daily cloud-health bundle."""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any


PASS = "PASS"
BLOCKED = "BLOCKED"
EXPECTED_COUNT = 46
EXPECTED_DIGEST = (
    "3e2a4e8e85e7a30af7335028d8ed2d6bd05576847c168ddc26c5552941bf7b6e"
)
V3_DIGEST = "339f48d201b11698c366836899f75d9bca125246abd80f1798be3dd458b7b03d"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://alice51849.github.io/ios-app-guide/cloud-health/schema.json",
    "title": "Lumi Studio daily cloud-health evidence",
    "type": "object",
    "required": [
        "schema_version",
        "generator_version",
        "generation_id",
        "generated_at",
        "overall_status",
        "window",
        "constraints_observed",
        "canonical_roster",
        "line_verdicts",
        "layers",
        "source_evidence",
    ],
    "properties": {
        "schema_version": {"const": 4},
        "generator_version": {"type": "string"},
        "generation_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "generated_at": {"type": "string", "format": "date-time"},
        "overall_status": {"enum": [PASS, BLOCKED]},
        "window": {
            "type": "object",
            "required": ["since", "until", "days"],
            "properties": {
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "days": {"const": 7},
            },
            "additionalProperties": False,
        },
        "constraints_observed": {"type": "object"},
        "canonical_roster": {"type": "object"},
        "line_verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["line", "status", "evidence", "reason"],
                "properties": {
                    "line": {"type": "string"},
                    "status": {"enum": [PASS, BLOCKED]},
                    "evidence": {},
                    "reason": {"type": "string"},
                },
            },
        },
        "layers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["layer", "status", "reason"],
                "properties": {
                    "layer": {
                        "enum": [
                            "capacity",
                            "run",
                            "deployed",
                            "GET",
                            "crawler",
                            "click",
                            "download",
                        ]
                    },
                    "status": {"enum": [PASS, BLOCKED]},
                    "reason": {"type": "string"},
                },
            },
        },
        "source_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "source",
                    "status",
                    "observed_at",
                    "run_id",
                    "sha256",
                ],
                "properties": {
                    "source": {"type": "string"},
                    "status": {"enum": [PASS, BLOCKED]},
                    "observed_at": {"type": "string", "format": "date-time"},
                    "run_id": {"type": ["integer", "string", "null"]},
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
            },
        },
    },
}


class ContractError(ValueError):
    """Raised when evidence is mislabeled, incomplete, or semantically unsafe."""


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def roster_digest(keys: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(keys), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _status(condition: bool) -> str:
    return PASS if condition else BLOCKED


def _line(name: str, condition: bool, evidence: Any, reason: str) -> dict[str, Any]:
    return {
        "line": name,
        "status": _status(condition),
        "evidence": evidence,
        "reason": reason,
    }


def _source_ok(snapshot: dict[str, Any], *names: str) -> bool:
    indexed = {row.get("source"): row for row in snapshot.get("source_evidence", [])}
    snapshot_at = parse_time(snapshot["observed_at"])
    for name in names:
        row = indexed.get(name, {})
        if row.get("status") != PASS:
            return False
        try:
            observed_at = parse_time(row["observed_at"])
        except (KeyError, TypeError, ValueError):
            return False
        if abs((snapshot_at - observed_at).total_seconds()) > 6 * 60 * 60:
            return False
    return True


def _window_metric(
    start: date,
    end: date,
    metric: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    unknown_rows = sorted(values.get("unknown_no_row") or [])
    known = int(values.get("known", EXPECTED_COUNT - len(unknown_rows)))
    unknown = int(values.get("unknown", len(unknown_rows)))
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "metric": metric,
        "apps_ge_1": int(values.get("apps_ge_1", 0)),
        "known": known,
        "unknown": unknown,
        "denominator": EXPECTED_COUNT,
        "unknown_no_row": unknown_rows,
        "source": "App Store Connect Sales and Trends",
        "aggregate_semantics": "exact",
        "analytics_privacy_suppression_applied": False,
        "counts_as_public_exposure": False,
    }


def normalize_asc_windows(asc: dict[str, Any]) -> dict[str, Any]:
    as_of = date.fromisoformat(asc["as_of"])
    rolling_start = as_of - timedelta(days=6)
    month_start = as_of.replace(day=1)
    raw = asc.get("window_counts", {})
    return {
        "latest_daily": {
            "downloads": _window_metric(
                as_of,
                as_of,
                "first_downloads_ge_1",
                raw.get("latest_daily_downloads", {}),
            ),
            "iap": _window_metric(
                as_of,
                as_of,
                "iap_units_ge_1",
                raw.get("latest_daily_iap", {}),
            ),
        },
        "rolling_7d": {
            "downloads": _window_metric(
                rolling_start,
                as_of,
                "first_downloads_ge_1",
                raw.get("rolling_7d_downloads", {}),
            ),
            "iap": _window_metric(
                rolling_start,
                as_of,
                "iap_units_ge_1",
                raw.get("rolling_7d_iap", {}),
            ),
        },
        "month_to_date": {
            "downloads": _window_metric(
                month_start,
                as_of,
                "first_downloads_ge_1",
                raw.get("month_to_date_downloads", {}),
            ),
            "iap": _window_metric(
                month_start,
                as_of,
                "iap_units_ge_1",
                raw.get("month_to_date_iap", {}),
            ),
        },
    }


def _schedule_aggregate(value: dict[str, Any]) -> dict[str, Any]:
    expected = int(value.get("nominal_cron_roots", 0))
    actual = int(value.get("actual_natural_schedule_roots", 0))
    conclusions = dict(value.get("natural_root_conclusions", {}))
    return {
        "workflow_count": int(value.get("workflow_count", 0)),
        "nominal_cron_roots": expected,
        "actual_natural_schedule_roots": actual,
        "nominal_cron_delivery_ratio": round(actual / expected, 4) if expected else None,
        "nominal_cron_delivery_ratio_is_sla": False,
        "nominal_cron_delivery_ratio_counts_as_capacity": False,
        "nominal_cron_denominator_note": (
            "Current cron expressions expanded over the seven-day window form a "
            "nominal comparison only; they are not a GitHub SLA or capacity measure."
        ),
        "natural_root_conclusions": conclusions,
        "natural_root_success_ratio": (
            round(int(conclusions.get("success", 0)) / actual, 4) if actual else None
        ),
        "workflow_dispatch_runs_excluded_from_natural_roots": int(
            value.get("workflow_dispatch_runs", 0)
        ),
        "collection_errors": list(value.get("collection_errors", [])),
    }


def build_artifact(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build a new result only from this run's snapshot; no old artifact is read."""
    generated_at = snapshot["observed_at"]
    generated_dt = parse_time(generated_at)
    window_since = generated_dt - timedelta(days=7)
    canonical = snapshot.get("canonical", {})
    keys = sorted(canonical.get("keys") or [])
    digests = {
        "expected_digest": EXPECTED_DIGEST,
        "cloud_threads_digest": canonical.get("threads_digest"),
        "cloud_guide_source_digest": canonical.get("guide_digest"),
        "public_apps_json_digest": canonical.get("public_digest"),
        "asc_live_roster_digest": canonical.get("asc_digest"),
    }
    exact46 = (
        len(keys) == EXPECTED_COUNT
        and roster_digest(keys) == EXPECTED_DIGEST
        and all(value == EXPECTED_DIGEST for value in digests.values())
        and not canonical.get("missing_live_apps")
        and not canonical.get("unknown_live_apps")
        and _source_ok(snapshot, "canonical", "asc")
    )

    schedule = snapshot.get("schedule", {})
    all_outreach = _schedule_aggregate(schedule.get("all_outreach", {}))
    social = _schedule_aggregate(schedule.get("social", {}))
    high_frequency = _schedule_aggregate(schedule.get("high_frequency_social", {}))
    schedule_delivery_ok = (
        _source_ok(snapshot, "github_actions")
        and not all_outreach["collection_errors"]
        and all_outreach["nominal_cron_roots"] > 0
        and all_outreach["actual_natural_schedule_roots"]
        == all_outreach["nominal_cron_roots"]
    )
    run_ok = (
        _source_ok(snapshot, "github_actions")
        and all_outreach["actual_natural_schedule_roots"] > 0
        and all_outreach["natural_root_conclusions"]
        == {"success": all_outreach["actual_natural_schedule_roots"]}
    )
    digest_gate = snapshot.get("digest_gate", {})
    digest_ok = (
        _source_ok(snapshot, "digest_gate")
        and digest_gate.get("fresh") is True
        and not digest_gate.get("failures")
    )

    pages = snapshot.get("pages", {})
    deploy_ok = (
        _source_ok(snapshot, "pages_deployments")
        and pages.get("recent_deployments", 0)
        == pages.get("recent_deployment_successes", -1)
        and pages.get("recent_deployments", 0) > 0
    )
    get_ok = (
        _source_ok(snapshot, "public_get")
        and pages.get("pages_get_ok") == pages.get("pages_get_total")
        and pages.get("guide_get_ok") == EXPECTED_COUNT
        and pages.get("guide_get_total") == EXPECTED_COUNT
        and pages.get("app_store_get_ok") == EXPECTED_COUNT
        and pages.get("app_store_get_total") == EXPECTED_COUNT
    )
    pages_ok = deploy_ok and get_ok

    owned = snapshot.get("owned_surfaces", {})
    owned_ok = (
        _source_ok(snapshot, "publisher", "public_get")
        and owned.get("guide_count") == EXPECTED_COUNT
        and owned.get("publisher_count") == EXPECTED_COUNT
        and owned.get("profile_count") == EXPECTED_COUNT
        and not owned.get("publisher_missing")
        and not owned.get("profile_missing")
    )

    social_channels = copy.deepcopy(snapshot.get("social_channels", []))
    social_ok = (
        _source_ok(snapshot, "social_receipts", "standard")
        and bool(social_channels)
        and all(item.get("status") == PASS for item in social_channels)
    )
    crawler = copy.deepcopy(snapshot.get("crawler", {}))
    crawler_ok = (
        _source_ok(snapshot, "crawler")
        and crawler.get("sitemap_get_ok") is True
        and crawler.get("robots_get_ok") is True
        and crawler.get("guide_apps_in_sitemap") == EXPECTED_COUNT
        and crawler.get("standard_reader_verified") is True
        and crawler.get("search_index_presence") is True
    )
    click = copy.deepcopy(snapshot.get("click", {}))
    click_ok = (
        _source_ok(snapshot, "click")
        and click.get("known") is True
        and len(click.get("apps_with_click") or []) == EXPECTED_COUNT
    )

    asc = copy.deepcopy(snapshot.get("asc", {}))
    windows = normalize_asc_windows(asc) if asc.get("as_of") else {}
    asc_fresh = (
        _source_ok(snapshot, "asc")
        and asc.get("fresh") is True
        and asc.get("aggregate_semantics") == "exact"
        and asc.get("analytics_privacy_suppression_applied") is False
        and asc.get("live_roster_count") == EXPECTED_COUNT
        and asc.get("windows_complete") is True
    )
    daily = (windows.get("latest_daily") or {}).get("downloads", {})
    asc_floor_ok = asc_fresh and daily.get("apps_ge_1") == EXPECTED_COUNT

    lines = [
        _line(
            "canonical_exact46",
            exact46,
            {
                **digests,
                "count": len(keys),
                "missing_live_apps": canonical.get("missing_live_apps", []),
                "unknown_live_apps": canonical.get("unknown_live_apps", []),
            },
            "Every canonical source must freshly match the approved exact46 digest.",
        ),
        _line(
            "github_schedule_delivery",
            schedule_delivery_ok,
            {"all_outreach": all_outreach, "social_engine": social},
            "Nominal cron delivery is kept separate from capacity and run success.",
        ),
        _line(
            "content_digest_gate",
            digest_ok,
            {
                "fresh": digest_gate.get("fresh", False),
                "failures": digest_gate.get("failures", []),
                "counts_as_github_schedule_delivery_failure": False,
                "counts_as_public_exposure": False,
            },
            "Publisher digest integrity is an application gate, not schedule delivery.",
        ),
        _line(
            "natural_schedule_run_success",
            run_ok and digest_ok,
            {
                "all_outreach": all_outreach,
                "high_frequency_social": high_frequency,
                "attempt_semantics": "event=schedule, attempt=1 only",
            },
            "Only natural event=schedule attempt-1 roots count as run success.",
        ),
        _line(
            "pages_deployment_and_http_delivery",
            pages_ok,
            pages,
            "A successful deployment and an independent public GET are separate gates.",
        ),
        _line(
            "owned_surface_exact46_coverage",
            owned_ok,
            owned,
            "Guide, publisher root, and profile must each cover exact46.",
        ),
        _line(
            "social_public_exposure",
            social_ok,
            social_channels,
            "Receipts are deduplicated by public identity; Nostr ACK is not exposure.",
        ),
        _line(
            "crawler_and_index",
            crawler_ok,
            crawler,
            "HTTP delivery, crawler notification, and confirmed index presence differ.",
        ),
        _line(
            "click",
            click_ok,
            click,
            "A public receipt is not a click; missing channel click evidence is unknown.",
        ),
        _line(
            "asc_download_evidence",
            asc_fresh,
            {
                "snapshot": asc.get("snapshot"),
                "canonical_live_roster": f"{asc.get('live_roster_count', 0)}/46",
                "daily_first_downloads": asc.get("daily_first_downloads"),
                "month_to_date_first_downloads": asc.get(
                    "month_to_date_first_downloads"
                ),
                "source_run_id": asc.get("source_run_id"),
                "source_system": "App Store Connect Sales and Trends",
                "aggregate_semantics": "exact",
                "analytics_privacy_suppression_applied": False,
            },
            "Fresh exact Sales and Trends evidence must cover the exact46 live roster.",
        ),
        _line(
            "asc_per_app_download_floor",
            asc_floor_ok,
            {
                "windows": windows,
                "eligible_days": asc.get("eligible_days", {}),
                "unknown_no_row": asc.get("unknown_no_row", []),
                "all_zero_rows": asc.get("all_zero_rows", []),
                "excluded_population_reports": asc.get(
                    "excluded_population_reports", []
                ),
                "raw_reconstruction_counts_are_floor_truth": asc.get(
                    "raw_reconstruction_counts_are_floor_truth", False
                ),
            },
            "Daily, rolling-7d, and MTD remain distinct exact windows; unknown is not zero.",
        ),
    ]
    line_status = {item["line"]: item["status"] for item in lines}
    layers = [
        {
            "layer": "capacity",
            "status": BLOCKED,
            "reason": (
                "No billing/quota capacity evidence is collected; nominal cron "
                "delivery is explicitly not a capacity measurement."
            ),
        },
        {
            "layer": "run",
            "status": _status(run_ok and digest_ok),
            "reason": "Natural attempt-1 schedule roots plus the separate digest gate.",
        },
        {
            "layer": "deployed",
            "status": _status(deploy_ok),
            "reason": "Latest recent Pages deployments completed successfully.",
        },
        {
            "layer": "GET",
            "status": _status(get_ok and owned_ok and social_ok),
            "reason": "Independent anonymous public GET and receipt resolution.",
        },
        {
            "layer": "crawler",
            "status": line_status["crawler_and_index"],
            "reason": "Crawler discovery, notification, and index proof.",
        },
        {
            "layer": "click",
            "status": line_status["click"],
            "reason": "Measured click evidence only.",
        },
        {
            "layer": "download",
            "status": _status(asc_fresh and asc_floor_ok),
            "reason": "Exact ASC Sales and Trends download windows.",
        },
    ]
    source_evidence = copy.deepcopy(snapshot.get("source_evidence", []))
    result: dict[str, Any] = {
        "schema_version": 4,
        "generator_version": "cloud-health-daily/1",
        "generation_id": "",
        "generated_at": generated_at,
        "overall_status": (
            PASS if lines and all(item["status"] == PASS for item in lines) else BLOCKED
        ),
        "window": {
            "since": iso_z(window_since),
            "until": iso_z(generated_dt),
            "days": 7,
        },
        "constraints_observed": {
            "network_methods": ["GET"],
            "repo_modified_by_generator": False,
            "workflow_dispatched": False,
            "workflow_rerun": False,
            "http_post_by_generator": False,
            "secrets_emitted": False,
            "model_used": False,
            "old_green_carried_forward": False,
            "natural_schedule_attempt": 1,
            "standard_cross_unit_subtraction": False,
            "nostr_relay_ack_counts_as_public_exposure": False,
        },
        "definitions": {
            "nominal_cron_delivery_ratio": (
                "Observed natural schedule roots divided by current cron expressions "
                "expanded over the window; not an SLA or capacity measurement."
            ),
            "run_success": "Conclusion of attempt 1 for event=schedule only.",
            "public_get": "Independent anonymous HTTP GET resolving a public surface.",
            "crawler_index": (
                "Crawler/index receipts are separate from HTTP delivery; IndexNow "
                "acceptance is not index presence."
            ),
            "click": "Measured click evidence; visibility is not a click.",
            "sales_trends_unknown": (
                "A missing report row is unknown, not zero; Sales and Trends is exact "
                "and does not use Analytics privacy suppression."
            ),
        },
        "canonical_roster": {
            "expected_count": EXPECTED_COUNT,
            "expected_digest": EXPECTED_DIGEST,
            "keys": keys,
            "missing_live_apps": canonical.get("missing_live_apps", []),
            "unknown_live_apps": canonical.get("unknown_live_apps", []),
        },
        "line_verdicts": lines,
        "layers": layers,
        "source_evidence": source_evidence,
    }
    identity = copy.deepcopy(result)
    identity["generation_id"] = None
    result["generation_id"] = digest_value(identity)
    validate_artifact(result)
    return result


def _find_line(artifact: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [row for row in artifact.get("line_verdicts", []) if row.get("line") == name]
    if len(matches) != 1:
        raise ContractError(f"expected one {name} line")
    return matches[0]


def _assert_metric(
    metric: dict[str, Any], start: date, end: date, metric_name: str
) -> None:
    if metric.get("start") != start.isoformat() or metric.get("end") != end.isoformat():
        raise ContractError(f"{metric_name} window bounds changed")
    if metric.get("metric") != metric_name:
        raise ContractError(f"{metric_name} label changed")
    if metric.get("denominator") != EXPECTED_COUNT:
        raise ContractError(f"{metric_name} denominator must be exact46")
    known, unknown = metric.get("known"), metric.get("unknown")
    if not isinstance(known, int) or not isinstance(unknown, int):
        raise ContractError(f"{metric_name} known/unknown must be integers")
    if known + unknown != EXPECTED_COUNT:
        raise ContractError(f"{metric_name} known+unknown must equal exact46")
    missing = metric.get("unknown_no_row")
    if not isinstance(missing, list) or len(missing) != unknown:
        raise ContractError(f"{metric_name} unknown rows do not reconcile")
    if metric.get("aggregate_semantics") != "exact":
        raise ContractError(f"{metric_name} must remain exact")
    if metric.get("analytics_privacy_suppression_applied") is not False:
        raise ContractError(f"{metric_name} cannot use Analytics suppression")
    if metric.get("counts_as_public_exposure") is not False:
        raise ContractError(f"{metric_name} cannot count as public exposure")


def validate_v3_golden(artifact: dict[str, Any]) -> None:
    if artifact.get("artifact_revision") != "v3":
        raise ContractError("golden fixture is not v3")
    canonical = artifact.get("canonical_roster", {})
    keys = canonical.get("keys") or []
    if canonical.get("expected_count") != EXPECTED_COUNT:
        raise ContractError("v3 expected count changed")
    if canonical.get("expected_digest") != EXPECTED_DIGEST:
        raise ContractError("v3 expected digest changed")
    if len(keys) != EXPECTED_COUNT or roster_digest(keys) != EXPECTED_DIGEST:
        raise ContractError("v3 exact46 roster changed")
    floor = _find_line(artifact, "asc_per_app_download_floor")["evidence"]
    windows = floor["windows"]
    as_of = date.fromisoformat(windows["latest_daily"]["downloads"]["end"])
    expected = {
        "latest_daily": (as_of, as_of),
        "rolling_7d": (as_of - timedelta(days=6), as_of),
        "month_to_date": (as_of.replace(day=1), as_of),
    }
    for window_name, (start, end) in expected.items():
        _assert_metric(
            windows[window_name]["downloads"], start, end, "first_downloads_ge_1"
        )
        _assert_metric(windows[window_name]["iap"], start, end, "iap_units_ge_1")
    golden_counts = {
        ("latest_daily", "downloads"): 22,
        ("latest_daily", "iap"): 4,
        ("rolling_7d", "downloads"): 34,
        ("rolling_7d", "iap"): 11,
        ("month_to_date", "downloads"): 41,
        ("month_to_date", "iap"): 23,
    }
    for (window_name, metric_name), expected_count in golden_counts.items():
        if windows[window_name][metric_name]["apps_ge_1"] != expected_count:
            raise ContractError(
                f"v3 {window_name} {metric_name} golden changed"
            )
    if windows["month_to_date"]["downloads"]["unknown_no_row"] != ["aim990plus"]:
        raise ContractError("v3 MTD unknown semantics changed")
    social = _find_line(artifact, "social_public_exposure")["evidence"]
    nostr = next(row for row in social if row.get("channel") == "Nostr")
    if nostr.get("counts_as_public_exposure") is not False:
        raise ContractError("Nostr relay ACK was relabeled as public exposure")
    if not isinstance(nostr.get("public_get_sample"), dict):
        raise ContractError("Nostr public GET is not separate")
    crawler = _find_line(artifact, "crawler_and_index")["evidence"]
    standard = crawler.get("standard_site", {})
    if standard.get("app_count_and_document_count_are_same_unit") is not False:
        raise ContractError("Standard cross-unit semantics changed")
    forbidden = "public_index_document_count_minus_state_derived_app_count"
    if forbidden in json.dumps(artifact, ensure_ascii=False):
        raise ContractError("Standard cross-unit subtraction returned")
    schedule = _find_line(artifact, "github_schedule_delivery")["evidence"]
    for aggregate in schedule.values():
        if not isinstance(aggregate, dict):
            continue
        if aggregate.get("nominal_cron_delivery_ratio_is_sla") is not False:
            raise ContractError("nominal cron ratio became an SLA")
        if aggregate.get("nominal_cron_delivery_ratio_counts_as_capacity") is not False:
            raise ContractError("nominal cron ratio became capacity")


def validate_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("schema_version") != 4:
        raise ContractError("schema_version must be 4")
    if artifact.get("overall_status") not in {PASS, BLOCKED}:
        raise ContractError("invalid overall status")
    if not HEX64.fullmatch(str(artifact.get("generation_id", ""))):
        raise ContractError("invalid generation id")
    parse_time(artifact["generated_at"])
    constraints = artifact.get("constraints_observed", {})
    required_false = [
        "repo_modified_by_generator",
        "workflow_dispatched",
        "workflow_rerun",
        "http_post_by_generator",
        "secrets_emitted",
        "model_used",
        "old_green_carried_forward",
        "standard_cross_unit_subtraction",
        "nostr_relay_ack_counts_as_public_exposure",
    ]
    if any(constraints.get(key) is not False for key in required_false):
        raise ContractError("a read-only/fail-closed constraint was violated")
    if constraints.get("network_methods") != ["GET"]:
        raise ContractError("generator network method must be GET only")
    roster = artifact.get("canonical_roster", {})
    if roster.get("expected_count") != EXPECTED_COUNT:
        raise ContractError("exact46 count changed")
    if roster.get("expected_digest") != EXPECTED_DIGEST:
        raise ContractError("exact46 digest changed")
    keys = roster.get("keys") or []
    if len(keys) != EXPECTED_COUNT or roster_digest(keys) != EXPECTED_DIGEST:
        raise ContractError("canonical roster is not exact46")
    names = [row.get("line") for row in artifact.get("line_verdicts", [])]
    if len(names) != len(set(names)) or len(names) != 11:
        raise ContractError("line verdict set is incomplete or duplicated")
    floor = _find_line(artifact, "asc_per_app_download_floor")["evidence"]
    windows = floor.get("windows")
    if windows:
        as_of = date.fromisoformat(windows["latest_daily"]["downloads"]["end"])
        ranges = {
            "latest_daily": (as_of, as_of),
            "rolling_7d": (as_of - timedelta(days=6), as_of),
            "month_to_date": (as_of.replace(day=1), as_of),
        }
        for name, (start, end) in ranges.items():
            _assert_metric(
                windows[name]["downloads"], start, end, "first_downloads_ge_1"
            )
            _assert_metric(windows[name]["iap"], start, end, "iap_units_ge_1")
    if "public_index_document_count_minus_state_derived_app_count" in json.dumps(
        artifact, ensure_ascii=False
    ):
        raise ContractError("Standard cross-unit subtraction is forbidden")
    for row in artifact.get("source_evidence", []):
        if row.get("status") not in {PASS, BLOCKED}:
            raise ContractError("invalid source evidence status")
        parse_time(row["observed_at"])
        if "run_id" not in row or not HEX64.fullmatch(str(row.get("sha256", ""))):
            raise ContractError("source evidence lacks timestamp/run/digest")
    if any(row.get("status") == BLOCKED for row in artifact["line_verdicts"]):
        if artifact.get("overall_status") != BLOCKED:
            raise ContractError("blocked line cannot produce a green artifact")


def build_snapshot_from_v3(v3: dict[str, Any]) -> dict[str, Any]:
    """Project the approved v3 fixture into the new rule engine for regression tests."""
    validate_v3_golden(v3)
    lines = {row["line"]: row for row in v3["line_verdicts"]}
    roster = v3["canonical_roster"]
    schedule = lines["github_schedule_delivery"]["evidence"]
    floor = lines["asc_per_app_download_floor"]["evidence"]
    windows = floor["windows"]
    asc_download = lines["asc_download_evidence"]["evidence"]
    social = copy.deepcopy(lines["social_public_exposure"]["evidence"])
    for row in social:
        row["status"] = row.get("status", BLOCKED)
    observed_at = v3["public_snapshot_at"]
    sources = []
    for name in [
        "canonical",
        "github_actions",
        "digest_gate",
        "pages_deployments",
        "public_get",
        "publisher",
        "social_receipts",
        "standard",
        "crawler",
        "click",
        "asc",
    ]:
        payload = {"source": name, "fixture": V3_DIGEST}
        sources.append(
            {
                "source": name,
                "status": PASS,
                "observed_at": observed_at,
                "run_id": asc_download.get("source_run_id") if name == "asc" else None,
                "sha256": digest_value(payload),
                "fixture": True,
            }
        )
    def raw_metric(window: str, metric: str) -> dict[str, Any]:
        value = windows[window][metric]
        return {
            "apps_ge_1": value["apps_ge_1"],
            "known": value["known"],
            "unknown": value["unknown"],
            "unknown_no_row": value["unknown_no_row"],
        }
    return {
        "observed_at": observed_at,
        "source_evidence": sources,
        "canonical": {
            "keys": roster["keys"],
            "threads_digest": EXPECTED_DIGEST,
            "guide_digest": EXPECTED_DIGEST,
            "public_digest": EXPECTED_DIGEST,
            "asc_digest": EXPECTED_DIGEST,
            "missing_live_apps": [],
            "unknown_live_apps": [],
        },
        "schedule": {
            "all_outreach": schedule["all_outreach"],
            "social": schedule["social_engine"],
            "high_frequency_social": lines["natural_schedule_run_success"][
                "evidence"
            ]["high_frequency_social"],
        },
        "digest_gate": {
            "fresh": True,
            "failures": lines["content_digest_gate"]["evidence"]["latest_affected_natural_roots"],
        },
        "pages": lines["pages_deployment_and_http_delivery"]["evidence"]
        | {
            "pages_get_total": lines["pages_deployment_and_http_delivery"]["evidence"][
                "pages_repos"
            ],
            "pages_get_ok": int(
                lines["pages_deployment_and_http_delivery"]["evidence"][
                    "pages_public_get"
                ].split("/")[0]
            ),
            "guide_get_total": EXPECTED_COUNT,
            "guide_get_ok": EXPECTED_COUNT,
            "app_store_get_total": EXPECTED_COUNT,
            "app_store_get_ok": EXPECTED_COUNT,
            "recent_deployments": lines["pages_deployment_and_http_delivery"][
                "evidence"
            ]["repos_with_deployment_7d"],
            "recent_deployment_successes": int(
                lines["pages_deployment_and_http_delivery"]["evidence"][
                    "latest_recent_deployment_success"
                ].split("/")[0]
            ),
        },
        "owned_surfaces": {
            "guide_count": EXPECTED_COUNT,
            "publisher_count": int(
                lines["owned_surface_exact46_coverage"]["evidence"][
                    "publisher_root"
                ].split("/")[0]
            ),
            "profile_count": int(
                lines["owned_surface_exact46_coverage"]["evidence"][
                    "github_profile"
                ].split("/")[0]
            ),
            "publisher_missing": lines["owned_surface_exact46_coverage"]["evidence"][
                "publisher_root_missing"
            ],
            "profile_missing": lines["owned_surface_exact46_coverage"]["evidence"][
                "github_profile_missing"
            ],
        },
        "social_channels": social,
        "crawler": {
            "sitemap_get_ok": True,
            "robots_get_ok": True,
            "guide_apps_in_sitemap": EXPECTED_COUNT,
            "standard_reader_verified": False,
            "search_index_presence": False,
            "standard_site": lines["crawler_and_index"]["evidence"].get(
                "standard_site", {}
            ),
        },
        "click": {
            **lines["click"]["evidence"],
            "known": True,
        },
        "asc": {
            "as_of": windows["latest_daily"]["downloads"]["end"],
            "fresh": True,
            "aggregate_semantics": "exact",
            "analytics_privacy_suppression_applied": False,
            "live_roster_count": EXPECTED_COUNT,
            "windows_complete": True,
            "source_run_id": asc_download["source_run_id"],
            "snapshot": asc_download["snapshot"],
            "daily_first_downloads": asc_download["daily_first_downloads"],
            "month_to_date_first_downloads": asc_download[
                "month_to_date_first_downloads"
            ],
            "window_counts": {
                "latest_daily_downloads": raw_metric("latest_daily", "downloads"),
                "latest_daily_iap": raw_metric("latest_daily", "iap"),
                "rolling_7d_downloads": raw_metric("rolling_7d", "downloads"),
                "rolling_7d_iap": raw_metric("rolling_7d", "iap"),
                "month_to_date_downloads": raw_metric("month_to_date", "downloads"),
                "month_to_date_iap": raw_metric("month_to_date", "iap"),
            },
            "eligible_days": floor["eligible_days"],
            "unknown_no_row": floor["unknown_no_row"],
            "all_zero_rows": floor["all_zero_rows"],
            "excluded_population_reports": floor["excluded_population_reports"],
            "raw_reconstruction_counts_are_floor_truth": True,
        },
    }


def render_report(artifact: dict[str, Any], digest: str) -> str:
    lines = [
        "# 46-App 免費外宣每日雲端健康",
        "",
        f"- generation：`{artifact['generation_id']}`",
        f"- JSON digest：`sha256:{digest}`",
        f"- generated：`{artifact['generated_at']}`",
        f"- overall：**{artifact['overall_status']}**",
        "- network：GET-only；zero-model；不 dispatch／rerun／POST。",
        "",
        "## 線別",
        "",
        "| Line | Status |",
        "|---|---|",
    ]
    lines.extend(
        f"| `{row['line']}` | **{row['status']}** |"
        for row in artifact["line_verdicts"]
    )
    lines.extend(
        [
            "",
            "## 分層",
            "",
            "| Layer | Status | Meaning |",
            "|---|---|---|",
        ]
    )
    lines.extend(
        f"| `{row['layer']}` | **{row['status']}** | {row['reason']} |"
        for row in artifact["layers"]
    )
    lines.extend(
        [
            "",
            "## 固定語意",
            "",
            "- `nominal_cron_delivery_ratio` 不是 SLA，也不是 capacity。",
            "- run 僅計 `event=schedule` 的 attempt 1 natural roots。",
            "- Nostr relay ACK 與 public GET 分開，ACK 不算公開曝光。",
            "- Standard App coverage 與 document count 不跨單位相減。",
            "- ASC daily／rolling 7d／MTD 各自帶 start/end/metric/known/unknown。",
            "- 任一來源缺失、限流、網路失敗或過期即寫 **BLOCKED**，不沿用舊綠。",
            "",
        ]
    )
    return "\n".join(lines)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def write_bundle(output_dir: Path, artifact: dict[str, Any]) -> dict[str, str]:
    validate_artifact(artifact)
    output_dir.mkdir(parents=True, exist_ok=True)
    stage = output_dir / f".cloud-health-stage-{os.getpid()}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    try:
        json_bytes = (
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        json_digest = hashlib.sha256(json_bytes).hexdigest()
        report_bytes = render_report(artifact, json_digest).encode("utf-8")
        schema_bytes = (
            json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        files = {
            "cloud-health.json": json_bytes,
            "cloud-health.report.md": report_bytes,
            "cloud-health.schema.json": schema_bytes,
        }
        manifest = {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in files.items()
        }
        digest_bytes = "".join(
            f"{value}  {name}\n" for name, value in sorted(manifest.items())
        ).encode("utf-8")
        files["cloud-health.sha256"] = digest_bytes
        for name, payload in files.items():
            path = stage / name
            path.write_bytes(payload)
            _fsync_file(path)
        for name in files:
            os.replace(stage / name, output_dir / name)
        return {
            "json_sha256": json_digest,
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "schema_sha256": hashlib.sha256(schema_bytes).hexdigest(),
        }
    finally:
        shutil.rmtree(stage, ignore_errors=True)
