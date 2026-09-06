"""Integrity and freshness contracts for the read-only ASO -> offsite boundary.

Digests bind evidence, not publisher identity: inputs still have to come from
the configured first-party source. Downloading a catalog or changing its mtime
never refreshes evidence; the producer records actual Apple Lookup observation
times. Legacy documents deliberately fail closed.

Producer protocol
-----------------
``seal`` adds schema_version, generated_at, expires_at, source_digests and
document_digest. All digests use canonical UTF-8 JSON (sorted keys, compact
separators, no NaN); document_digest excludes only itself. Timestamp offsets
are mandatory and expiry is exclusive. ``source_digests.live_roster`` hashes
the exact {app_key: track_id} mapping from the versioned 46-app live registry.

Finder: the producer always emits the 46-row roster. Verified observations
have verified_live=true and their actual verified_at; unobserved availability
and missing localized metadata stay explicit unknown/null, never fabricated.
``catalog`` hashes the complete apps array. The eight-day TTL starts at Apple
verification, not a catalog rebuild/download.

Strategy: all live apps keyed by app key, each with string track_id,
data_status, evidence, core_markets and amplify_markets. ``feedback`` hashes
the independently loaded feedback object; source_generated_at must exactly
match its generated_at. Strategy TTL is 36 hours, feedback TTL is 30 hours.
Missing or mismatched feedback identities produce canonical track_id rows
with unknown measurements, never measured zeros.

Proposals bind finder, strategy, feedback, normalized readings and terms.
They expire no later than their sources and can authorize only an allowlisted
offsite projection. The public topic contract carries that proposal digest,
not private feedback, candidate ASC fields or local source paths. Every
consumer rechecks TTL; unsupported inputs remain explicit unknown app rows.
Reading provenance is checked at proposal generation time; the topic consumer
then rechecks current freshness per app, rather than letting an unused stale
reading veto fresh evidence for the rest of the roster.
After an envelope passes schema/digest/source checks, individual missing or
mismatched apps are assessed independently. Derived proposals/topics retain
all 46 rows. Publication requires verified source/rank evidence for every app
that actually emits a topic, not for inactive rows. Unknown apps remain in
the roster and generate explicit WARN health details, never new topics.
A staging candidate is
checked against both engine and Guide last-good files before replacement or
git mutation; zero topics are never publishable and cannot erase last-good.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

FINDER_SCHEMA = "growth-finder-evidence/1"
STRATEGY_SCHEMA = "growth-market-strategy/1"
PROPOSAL_SCHEMA = "growth-aso-proposals/2"
TOPICS_SCHEMA = "growth-offsite-topics/1"
MAX_AGE = {
    FINDER_SCHEMA: timedelta(days=8),
    STRATEGY_SCHEMA: timedelta(hours=36),
    PROPOSAL_SCHEMA: timedelta(hours=36),
    TOPICS_SCHEMA: timedelta(hours=36),
}
SOURCE_KEYS = {
    FINDER_SCHEMA: {"live_roster", "catalog"},
    STRATEGY_SCHEMA: {"live_roster", "feedback"},
    PROPOSAL_SCHEMA: {"live_roster", "finder", "strategy", "feedback", "readings", "terms"},
    TOPICS_SCHEMA: {"live_roster", "proposal"},
}
FEEDBACK_MAX_AGE = timedelta(hours=30)
LIVE_APP_COUNT = 46
READING_FRESH_DAYS = 4
OFFSITE_ONLY = "offsite_topics_only"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024


class ContractError(ValueError):
    pass


def reason_code(error: Any) -> str:
    code = str(error).split(":", 1)[0]
    return code if re.fullmatch(r"[a-z][a-z0-9_]*", code) else "source_unavailable"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ContractError("timestamp_missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("timestamp_invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError("timestamp_not_timezone_aware")
    return parsed.astimezone(timezone.utc)


def canonical_digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ContractError("non_canonical_json") from error
    return hashlib.sha256(encoded).hexdigest()


def document_digest(document: Mapping[str, Any]) -> str:
    return canonical_digest({k: v for k, v in document.items() if k != "document_digest"})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def decode_document(raw: bytes | str) -> dict:
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ContractError("document_exceeds_size_cap")
    try:
        document = json.loads(raw, object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as error:
        raise ContractError(f"invalid_json:{error}") from error
    if not isinstance(document, dict):
        raise ContractError("document_not_object")
    canonical_digest(document)
    return document


def read_document(path: Path) -> dict:
    with path.open("rb") as handle:
        return decode_document(handle.read(MAX_DOCUMENT_BYTES + 1))


def live_roster() -> dict[str, dict[str, str]]:
    """Use the same versioned live set as season_engine, never an input subset."""
    geo = Path(__file__).resolve().parent
    for path in (geo, geo.parent / "social"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from answer_personas import PERSONAS
    from videogen.registry import APPS, APPSTORE

    if len(PERSONAS) != LIVE_APP_COUNT:
        raise ContractError(f"live_roster_count:{len(PERSONAS)}!={LIVE_APP_COUNT}")
    roster = {}
    for key in sorted(PERSONAS):
        app_id = str(APPSTORE.get(key) or "")
        if key not in APPS or not app_id.isdigit():
            raise ContractError(f"live_roster_identity_missing:{key}")
        roster[key] = {"name": APPS[key]["name"], "track_id": app_id}
    if len({row["track_id"] for row in roster.values()}) != len(roster):
        raise ContractError("live_roster_duplicate_id")
    return roster


def roster_digest(roster: Mapping[str, Mapping[str, str]]) -> str:
    return canonical_digest({key: row["track_id"] for key, row in roster.items()})


def seal(
    document: dict, schema: str, *, roster: Mapping[str, Mapping[str, str]],
    generated_at: datetime, sources: Mapping[str, str | None],
    expires_at: datetime | None = None,
) -> dict:
    """Producer helper; sealing is not a substitute for validating source evidence."""
    result = {
        **document, "schema_version": schema,
        "generated_at": generated_at.isoformat(),
        "expires_at": (expires_at or (generated_at + MAX_AGE[schema])).isoformat(),
        "source_digests": {"live_roster": roster_digest(roster), **sources},
    }
    result["document_digest"] = document_digest(result)
    return result


def validate(
    document: Any, schema: str, *, roster: Mapping[str, Mapping[str, str]],
    now: datetime | None = None, sources: Mapping[str, str | None] | None = None,
    allow_app_gaps: bool = False,
) -> dict:
    now = now or utc_now()
    if not isinstance(document, dict) or document.get("schema_version") != schema:
        raise ContractError("unsupported_schema")
    generated = timestamp(document.get("generated_at"))
    expires = timestamp(document.get("expires_at"))
    if generated > now:
        raise ContractError("future_evidence")
    if expires <= generated or expires - generated > MAX_AGE[schema]:
        raise ContractError("invalid_ttl")
    if now >= expires or now - generated > MAX_AGE[schema]:
        raise ContractError("stale_evidence")
    digest = document.get("document_digest")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ContractError("document_digest_missing")
    if not hmac.compare_digest(digest, document_digest(document)):
        raise ContractError("document_digest_mismatch")
    actual_sources = document.get("source_digests")
    if not isinstance(actual_sources, dict) or set(actual_sources) != SOURCE_KEYS[schema] or any(
        not isinstance(key, str) or (
            value is not None and (
                not isinstance(value, str) or not SHA256.fullmatch(value)
            )
        ) for key, value in actual_sources.items()
    ):
        raise ContractError("source_digests_invalid")
    expected = {"live_roster": roster_digest(roster), **(sources or {})}
    if any(actual_sources.get(key) != value for key, value in expected.items()):
        raise ContractError("source_digest_mismatch")
    apps = document.get("apps")
    if isinstance(apps, list):
        indexed = {}
        for row in apps:
            if not isinstance(row, dict) or not isinstance(row.get("key"), str):
                raise ContractError("app_record_invalid")
            if row["key"] in indexed:
                raise ContractError("duplicate_app")
            indexed[row["key"]] = row
        if type(document.get("record_count")) is not int or document["record_count"] != len(indexed):
            raise ContractError("record_count_mismatch")
    elif isinstance(apps, dict):
        indexed = apps
    else:
        raise ContractError("apps_missing")
    if set(indexed) - set(roster) or not allow_app_gaps and set(indexed) != set(roster):
        missing = ",".join(sorted(set(roster) - set(indexed)))
        extra = ",".join(sorted(set(indexed) - set(roster)))
        raise ContractError(f"roster_mismatch:missing={missing};extra={extra}")
    for key, row in indexed.items():
        if not isinstance(row, dict):
            raise ContractError(f"app_record_invalid:{key}")
        app_id = row.get("app_store_id", row.get("track_id"))
        if not allow_app_gaps and (not isinstance(app_id, str) or app_id != roster[key]["track_id"]):
            raise ContractError(f"app_identity_mismatch:{key}")
    return document


def validate_finder(document: Any, *, roster, now: datetime | None = None) -> dict:
    now = now or utc_now()
    validate(document, FINDER_SCHEMA, roster=roster, now=now, allow_app_gaps=True)
    if not isinstance(document["apps"], list):
        raise ContractError("finder_apps_not_array")
    validate(document, FINDER_SCHEMA, roster=roster, now=now, allow_app_gaps=True, sources={
        "catalog": canonical_digest(document["apps"]),
    })
    verification = document.get("availability_verification")
    if not isinstance(verification, dict) or verification.get("source") != "Apple iTunes Lookup API":
        raise ContractError("finder_verification_missing")
    if verification.get("verified_at") is not None:
        verified = timestamp(verification["verified_at"])
        if verified > timestamp(document["generated_at"]):
            raise ContractError("finder_verification_in_future")
        if now - verified >= MAX_AGE[FINDER_SCHEMA] or timestamp(document["expires_at"]) > verified + MAX_AGE[FINDER_SCHEMA]:
            raise ContractError("finder_verification_stale")
    return document


def finder_app_states(document: dict, *, roster, now=None) -> dict:
    now = now or utc_now()
    validate_finder(document, roster=roster, now=now)
    indexed = {row["key"]: row for row in document["apps"]}
    states = {}
    for key, expected in roster.items():
        row = indexed.get(key)
        issues = []
        if row is None:
            issues.append("app_missing")
        elif row.get("app_store_id") != expected["track_id"]:
            issues.append("app_identity_mismatch")
        elif row.get("verified_live") is not True:
            issues.append("availability_unknown")
        elif row.get("metadata_status", "verified") != "verified":
            issues.append("metadata_unknown")
        else:
            try:
                observed = timestamp(row.get("verified_at", document["availability_verification"].get("verified_at")))
                if observed > timestamp(document["generated_at"]) or now - observed >= MAX_AGE[FINDER_SCHEMA]:
                    raise ContractError("availability_timestamp_invalid")
            except ContractError:
                issues.append("availability_timestamp_invalid")
        states[key] = {"status": "unknown" if issues else "verified", "issues": issues}
    return states


def feedback_app_states(feedback: dict, *, roster) -> tuple[dict, dict]:
    rows = feedback.get("apps") if isinstance(feedback, dict) else None
    if not isinstance(rows, list):
        raise ContractError("feedback_apps_missing")
    indexed = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("key"), str):
            raise ContractError("feedback_app_invalid")
        key = row["key"]
        if key in indexed or key not in roster:
            raise ContractError("feedback_roster_invalid")
        indexed[key] = row
    states = {}
    for key, expected in roster.items():
        row = indexed.get(key)
        issues = []
        if row is None:
            issues.append("feedback_app_missing")
        elif row.get("app_id") != expected["track_id"]:
            issues.append("feedback_app_identity_mismatch")
        elif row.get("data_status") not in ("ready", "pending", "error", "unknown"):
            issues.append("feedback_status_unknown")
        states[key] = {"status": "unknown" if issues else "verified", "issues": issues}
    return indexed, states


def validate_strategy(document: Any, *, roster, feedback: dict, now: datetime | None = None) -> dict:
    now = now or utc_now()
    if not isinstance(feedback, dict):
        raise ContractError("feedback_source_unavailable")
    validate(document, STRATEGY_SCHEMA, roster=roster, now=now, allow_app_gaps=True, sources={
        "feedback": canonical_digest(feedback),
    })
    if type(document.get("version")) is not int or document["version"] != 1:
        raise ContractError("strategy_version_invalid")
    source_time = timestamp(feedback.get("generated_at"))
    if document.get("source_generated_at") != feedback.get("generated_at"):
        raise ContractError("source_timestamp_mismatch")
    if source_time > timestamp(document["generated_at"]) or source_time > now:
        raise ContractError("future_source_evidence")
    if now - source_time >= FEEDBACK_MAX_AGE:
        raise ContractError("stale_source_evidence")
    feedback_app_states(feedback, roster=roster)
    if not isinstance(document["apps"], dict):
        raise ContractError("strategy_apps_not_object")
    return document


def strategy_app_states(document: dict, *, roster, feedback, now=None) -> dict:
    validate_strategy(document, roster=roster, feedback=feedback, now=now)
    feedback_rows, states = feedback_app_states(feedback, roster=roster)
    for key, expected in roster.items():
        row = document["apps"].get(key)
        issues = list(states[key]["issues"])
        if row is None:
            issues.append("app_missing")
            states[key] = {"status": "unknown", "issues": issues}
            continue
        if row.get("track_id") != expected["track_id"]:
            issues.append("app_identity_mismatch")
        if row.get("data_status") not in ("ready", "pending", "error", "unknown") or row.get("evidence") not in ("measured", "sibling_inherited", "unknown"):
            issues.append("evidence_status_invalid")
        if key in feedback_rows and row.get("data_status") != feedback_rows[key].get("data_status"):
            issues.append("source_status_mismatch")
        if row.get("data_status") != "ready" and row.get("evidence") == "measured":
            issues.append("unknown_claimed_measured")
        for field in ("core_markets", "amplify_markets"):
            values = row.get(field)
            if values is not None and (
                not isinstance(values, list) or any(
                    not isinstance(value, dict)
                    or not isinstance(value.get("territory"), str)
                    for value in values
                )
            ):
                issues.append("markets_invalid")
        states[key] = {"status": "unknown" if issues else "verified", "issues": issues}
    return states


def source_app_states(*, finder, strategy, feedback, terms, roster, now=None) -> dict:
    unavailable = {key: {"status": "unknown", "issues": ["source_unavailable"]} for key in roster}
    finder_states = finder_app_states(finder, roster=roster, now=now) if finder is not None else unavailable
    strategy_states = strategy_app_states(strategy, roster=roster, feedback=feedback, now=now) if strategy is not None else unavailable
    term_apps = terms.get("apps") if isinstance(terms, dict) else None
    markets = terms.get("markets") if isinstance(terms, dict) else None
    terms_valid = (
        isinstance(terms, dict) and type(terms.get("version")) is int and terms["version"] == 1
        and isinstance(term_apps, dict) and isinstance(markets, dict) and bool(markets)
        and all(
            isinstance(key, str) and re.fullmatch(r"[A-Z]{2}", key)
            and isinstance(row, dict) and isinstance(row.get("lang"), str) and bool(row["lang"])
            for key, row in markets.items()
        )
    )
    states = {}
    for key, expected in roster.items():
        issues = [f"finder:{reason}" for reason in finder_states[key]["issues"]]
        issues.extend(f"strategy:{reason}" for reason in strategy_states[key]["issues"])
        row = term_apps.get(key) if isinstance(term_apps, dict) else None
        if not isinstance(row, dict) or str(row.get("track_id")) != expected["track_id"]:
            issues.append("terms:app_missing_or_identity_mismatch")
        if not terms_valid:
            issues.append("terms:invalid_schema")
        states[key] = {"status": "unknown" if issues else "verified", "issues": issues}
    return states


def newest_validated(paths, validator) -> tuple[dict | None, dict]:
    """Content timestamps determine precedence; invalid candidates stay visible."""
    valid = []
    rejected = []
    try:
        paths = sorted(paths)
    except OSError:
        return None, {"status": "unknown", "reason": "source_directory_unavailable", "rejected": []}
    for path in paths:
        try:
            document = validator(read_document(path))
            valid.append((timestamp(document["generated_at"]), document["document_digest"], str(path), document))
        except (OSError, ContractError) as error:
            rejected.append({"path": str(path), "status": "unknown", "reason": str(error)})
    if not valid:
        return None, {"status": "unknown", "reason": "no_valid_evidence", "rejected": rejected}
    valid.sort(key=lambda row: (row[0], row[1], row[2]))
    latest = [row for row in valid if row[0] == valid[-1][0]]
    if len({row[1] for row in latest}) != 1:
        return None, {"status": "unknown", "reason": "ambiguous_evidence_timestamp", "rejected": rejected}
    _, digest, path, document = latest[-1]
    return document, {
        "status": "verified", "path": path, "document_digest": digest,
        "generated_at": document["generated_at"], "expires_at": document["expires_at"],
        "rejected": rejected,
    }


def validate_proposals(document: Any, *, roster, feedback: dict | None, now=None) -> dict:
    now = now or utc_now()
    validate(document, PROPOSAL_SCHEMA, roster=roster, now=now)
    observed_at = timestamp(document["generated_at"])
    if (
        type(document.get("version")) is not int or document["version"] != 2
        or document.get("mode") != OFFSITE_ONLY
        or document.get("allowed_consumers") != ["geo.rank_opportunity_pages"]
        or document.get("forbidden_actions") != ["asc.metadata", "asc.keywords", "asc.screenshots"]
    ):
        raise ContractError("offsite_boundary_invalid")
    evidence = document.get("evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("readings"), list) or not isinstance(evidence.get("terms"), dict):
        raise ContractError("proposal_evidence_missing")
    markets = document.get("markets")
    if not isinstance(markets, dict):
        raise ContractError("proposal_markets_invalid")
    finder, strategy = evidence.get("finder"), evidence.get("strategy")
    sources = {
        "readings": canonical_digest(evidence["readings"]),
        "terms": canonical_digest(evidence["terms"]),
        "finder": document_digest(finder) if isinstance(finder, dict) else None,
        "strategy": document_digest(strategy) if isinstance(strategy, dict) else None,
    }
    if feedback is not None:
        sources["feedback"] = canonical_digest(feedback)
    validate(document, PROPOSAL_SCHEMA, roster=roster, now=now, sources=sources)
    apps = document["apps"]
    if not isinstance(apps, dict):
        raise ContractError("proposal_apps_not_object")
    has_verified = any(row.get("evidence_status") == "verified" for row in apps.values())
    if has_verified:
        if (
            not isinstance(evidence["terms"].get("apps"), dict)
            or markets != evidence["terms"].get("markets")
            or any(
                not isinstance(market, str) or not re.fullmatch(r"[A-Z]{2}", market) or not isinstance(row, dict)
                or not isinstance(row.get("lang"), str) or not row["lang"]
                for market, row in markets.items()
            )
        ):
            raise ContractError("proposal_terms_schema_invalid")
        if feedback is None:
            raise ContractError("feedback_source_unavailable")
        validate_finder(finder, roster=roster, now=now)
        validate_strategy(strategy, roster=roster, feedback=feedback, now=now)
        deadline = min(
            timestamp(finder["expires_at"]), timestamp(strategy["expires_at"]),
            timestamp(feedback["generated_at"]) + FEEDBACK_MAX_AGE,
        )
        if timestamp(document["expires_at"]) > deadline:
            raise ContractError("proposal_outlives_source")
    source_states = source_app_states(
        finder=finder, strategy=strategy, feedback=feedback, terms=evidence["terms"], roster=roster, now=now,
    )
    indexed = {}
    for row in evidence["readings"]:
        if not isinstance(row, dict):
            raise ContractError("reading_invalid")
        app, market, term = row.get("app"), row.get("market"), row.get("term")
        if not isinstance(app, str) or app not in roster or not isinstance(market, str) or not isinstance(term, str) or not term.strip():
            raise ContractError("reading_identity_invalid")
        key = (app, market, term)
        if key in indexed:
            raise ContractError("duplicate_reading")
        validate_reading(row, now=observed_at)
        indexed[key] = row
    for app, entry in apps.items():
        status = entry.get("evidence_status")
        sections, backlog = entry.get("storefronts"), entry.get("backlog")
        issues = entry.get("issues")
        if entry.get("source_status") != source_states[app]["status"]:
            raise ContractError("proposal_source_status_mismatch")
        if (
            status not in ("verified", "unknown") or not isinstance(sections, dict) or not isinstance(backlog, list)
            or not isinstance(issues, list) or any(not isinstance(reason, str) for reason in issues)
        ):
            raise ContractError("proposal_app_status_invalid")
        if status == "unknown":
            if sections or backlog or not entry.get("issues"):
                raise ContractError("unknown_app_has_actions")
            continue
        if source_states[app]["status"] != "verified":
            raise ContractError("unverified_app_source")
        if issues or not any(key[0] == app for key in indexed):
            raise ContractError("verified_app_without_evidence")
        term_app = evidence["terms"].get("apps", {}).get(app)
        if not isinstance(term_app, dict) or str(term_app.get("track_id")) != roster[app]["track_id"]:
            raise ContractError("proposal_terms_identity_mismatch")
        proposed = []
        for market, section in sections.items():
            if (
                market not in markets or not isinstance(section, dict) or section.get("market") != market
                or section.get("lang") != markets[market]["lang"] or not isinstance(section.get("proposals"), list)
            ):
                raise ContractError("proposal_storefront_invalid")
            proposed.extend((market, row) for row in section["proposals"])
        if any(not isinstance(row, dict) for row in backlog):
            raise ContractError("proposal_backlog_invalid")
        proposed.extend((row.get("market"), row) for row in backlog)
        seen = set()
        for market, row in proposed:
            if (
                not isinstance(market, str) or market not in markets
                or not isinstance(row, dict) or not isinstance(row.get("term"), str)
                or not isinstance(row.get("concept", ""), str)
            ):
                raise ContractError("proposal_row_invalid")
            key = (app, market, row["term"])
            reading = indexed.get(key)
            if key in seen or not reading:
                raise ContractError("proposal_reading_missing_or_duplicate")
            seen.add(key)
            if reading.get("status") != "ranked" or any(
                row.get(field) != reading.get(source_field)
                for field, source_field in (
                    ("proxy_rank", "rank"), ("result_count", "result_count"), ("reading_date", "date"),
                )
            ):
                raise ContractError("proposal_reading_mismatch")
            if "concept" in row and row["concept"] != reading.get("concept"):
                raise ContractError("proposal_concept_mismatch")
            validate_rank(row.get("proxy_rank"), row.get("result_count"), row.get("reading_date"), now=observed_at, minimum=4)
    return document


def validate_rank(rank: Any, count: Any, reading_date: Any, *, now, minimum=1) -> None:
    if type(rank) is not int or type(count) is not int or not minimum <= rank <= min(30, count):
        raise ContractError("rank_invalid")
    try:
        observed = date.fromisoformat(reading_date)
    except (TypeError, ValueError) as error:
        raise ContractError("reading_date_invalid") from error
    if observed > now.date() or (now.date() - observed).days > READING_FRESH_DAYS:
        raise ContractError("reading_stale_or_future")


def validate_reading(row: dict, *, now) -> None:
    rank, count, status = row.get("rank"), row.get("result_count"), row.get("status")
    if type(count) is not int or count < 0 or not (
        status == "ranked" and type(rank) is int and 1 <= rank <= count
        or status == "unranked" and rank is None
    ):
        raise ContractError("reading_rank_invalid")
    try:
        observed = date.fromisoformat(row.get("date"))
    except (TypeError, ValueError) as error:
        raise ContractError("reading_date_invalid") from error
    if observed > now.date() or (now.date() - observed).days > READING_FRESH_DAYS:
        raise ContractError("reading_stale_or_future")
    if "observed_at" in row:
        measured = timestamp(row["observed_at"])
        if measured > now or measured.date() != observed:
            raise ContractError("reading_observation_timestamp_invalid")
    if any(not isinstance(row.get(field), str) for field in ("concept", "source", "rendering")):
        raise ContractError("reading_text_invalid")


TOPIC_FIELDS = {
    "app", "locale", "storefront", "market", "term", "concept",
    "rank", "result_count", "reading_date", "role", "source",
}


def topic_coverage_health(apps: dict, topics: list) -> dict:
    unknown = [
        {
            "app": key, "source_status": row["source_status"],
            "evidence_status": row["evidence_status"], "reasons": sorted(set(row["issues"])),
        }
        for key, row in sorted(apps.items())
        if row["source_status"] != "verified" or row["evidence_status"] != "verified"
    ]
    return {
        "status": "FAIL" if not topics else "WARN" if unknown else "OK",
        "app_count": len(apps), "topic_app_count": len({row["app"] for row in topics}),
        "topic_count": len(topics), "unknown_apps": unknown,
    }


def topic_warning_messages(health: dict) -> list[str]:
    return [
        f"WARN {row['app']}: {', '.join(row['reasons'])}"
        for row in health["unknown_apps"]
    ]


def validate_topics(document: Any, *, roster=None, now=None) -> dict:
    now = now or utc_now()
    roster = live_roster() if roster is None else roster
    validate(document, TOPICS_SCHEMA, roster=roster, now=now)
    allowed_fields = {
        "schema_version", "generated_at", "expires_at", "source_digests", "document_digest",
        "version", "mode", "source", "apps", "topics", "as_of", "reading_dates", "skipped", "selection", "counts", "health",
    }
    if (
        set(document) - allowed_fields or type(document.get("version")) is not int or document["version"] != 2
        or document.get("mode") != OFFSITE_ONLY or document.get("source") != "itunes_search_proxy"
    ):
        raise ContractError("offsite_boundary_invalid")
    proposal_digest = document["source_digests"].get("proposal")
    topics = document.get("topics")
    if not isinstance(topics, list) or not isinstance(document["apps"], dict):
        raise ContractError("topics_invalid")
    if topics and (not isinstance(proposal_digest, str) or not SHA256.fullmatch(proposal_digest)):
        raise ContractError("proposal_source_digest_missing")
    from app_store_storefronts import LOCALE_STOREFRONTS
    seen = set()
    for app in document["apps"].values():
        if (
            set(app) != {"track_id", "source_status", "evidence_status", "issues"}
            or app.get("source_status") not in ("verified", "unknown")
            or app.get("evidence_status") not in ("verified", "unknown")
            or not isinstance(app.get("issues"), list)
            or any(not isinstance(reason, str) for reason in app["issues"])
            or app["evidence_status"] == "unknown" and not app["issues"]
        ):
            raise ContractError("topic_app_status_invalid")
        if app["source_status"] != "verified" and app["evidence_status"] == "verified":
            raise ContractError("topic_source_unverified")
    for row in topics:
        if not isinstance(row, dict) or set(row) != TOPIC_FIELDS:
            raise ContractError("topic_fields_invalid")
        if not all(isinstance(row[field], str) for field in TOPIC_FIELDS - {"rank", "result_count"}):
            raise ContractError("topic_types_invalid")
        if (
            row["app"] not in roster
            or document["apps"][row["app"]]["source_status"] != "verified"
            or document["apps"][row["app"]]["evidence_status"] != "verified"
        ):
            raise ContractError("topic_app_unverified")
        if row["source"] != "itunes_search_proxy" or not row["term"].strip():
            raise ContractError("topic_source_invalid")
        validate_rank(row["rank"], row["result_count"], row["reading_date"], now=now)
        role = "defend" if row["rank"] <= 3 else "opportunity"
        if row["role"] != role or row["storefront"] != row["market"].lower() or LOCALE_STOREFRONTS.get(row["locale"]) != row["storefront"]:
            raise ContractError("topic_market_or_role_mismatch")
        key = (row["app"], row["locale"], row["term"])
        if key in seen:
            raise ContractError("duplicate_topic")
        seen.add(key)
    if "health" in document and document["health"] != topic_coverage_health(document["apps"], topics):
        raise ContractError("topic_health_mismatch")
    return document


def assert_publishable_topics(document: dict, *, previous: bytes | None = None, roster=None, now=None) -> dict:
    """Last-good preservation is checked before either write or git mutation."""
    validate_topics(document, roster=roster, now=now)
    if not document["topics"]:
        raise ContractError("empty_topics_not_publishable")
    return document
