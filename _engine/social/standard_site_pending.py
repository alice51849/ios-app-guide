#!/usr/bin/env python3
"""Versioned, bounded pending-state contract for Standard.site publishing."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import re
from typing import Mapping, MutableMapping, Sequence


ATTRIBUTION_REPAIR_REASON = "remote_attribution_removed"
ATTRIBUTION_REPAIR_FIELDS = (
    "repair_reason",
    "repair_detected_at",
    "repair_after_day",
)
ATTRIBUTION_REPAIR_BACKLOG_FIELD = "repair_backlog_days"
ORDINARY_REPUBLISH_REASON = "ordinary_pending_republish"
ORDINARY_REPUBLISH_FIELDS = (
    "republish_reason",
    "republish_detected_at",
    "republish_after_day",
    "republish_backlog_days",
)
PENDING_POLICY_FIELD = "pending_policy"
PENDING_POLICY_VERSION = 1
PENDING_POLICY_FIELDS = frozenset(
    {"version", "effective_daily_limit", "revision_at"}
)
PENDING_WINDOW_FIELD = "pending_window"
PENDING_WINDOW_VERSION = 1
PENDING_WINDOW_FIELDS = frozenset(
    {
        "version",
        "cohort_day",
        "effective_daily_limit",
        "pending_documents",
        "pending_apps",
        "max_per_app",
        "prior_cohort_days",
        "cohort_days",
        "computed_days",
        "updated_at",
    }
)
CONFIRMATION_FIELDS = (
    "at_uri",
    "cid",
    "record_hash",
    "last_verified_at",
    "updated_at",
)
MAX_DAILY_LIMIT = 4
MAX_TRACKED_DOCUMENTS = 5_000
MAX_WINDOW_DAYS = MAX_TRACKED_DOCUMENTS * MAX_TRACKED_DOCUMENTS
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PendingStateError(ValueError):
    """A pending Standard.site state is corrupt or has exceeded its bound."""


def _timestamp(value: object, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise PendingStateError(
            f"Invalid {label} timestamp: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        raise PendingStateError(f"{label} timestamp needs a timezone")
    return parsed.astimezone(timezone.utc)


def _timestamp_text(value: object, label: str) -> tuple[datetime, str]:
    parsed = _timestamp(value, label)
    return (
        parsed,
        parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    )


def _day(value: object, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise PendingStateError(f"Invalid {label} day: {value!r}") from error


def _daily_limit(value: object) -> int:
    if (
        type(value) is not int
        or not 1 <= value <= MAX_DAILY_LIMIT
    ):
        raise PendingStateError("Effective daily document limit is invalid")
    return value


def _bounded_int(
    value: object,
    *,
    minimum: int,
    maximum: int,
    label: str,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise PendingStateError(f"Invalid pending-window {label}")
    return value


def _prefixed_fields(
    entry: Mapping[str, object], prefix: str
) -> set[str]:
    return {str(field) for field in entry if str(field).startswith(prefix)}


def pending_kind(entry: Mapping[str, object]) -> str | None:
    repair_fields = _prefixed_fields(entry, "repair_")
    republish_fields = _prefixed_fields(entry, "republish_")
    if repair_fields and republish_fields:
        raise PendingStateError(
            "Document mixes attribution-repair and ordinary-republish state"
        )
    if repair_fields:
        return "attribution_repair"
    if republish_fields:
        return "ordinary_republish"
    return None


def pending_detected_at(entry: Mapping[str, object]) -> object | None:
    kind = pending_kind(entry)
    if kind == "attribution_repair":
        return entry.get("repair_detected_at")
    if kind == "ordinary_republish":
        return entry.get("republish_detected_at")
    return None


def pending_cohort_day(entry: Mapping[str, object]) -> str | None:
    kind = pending_kind(entry)
    if kind is None:
        return None
    window = entry.get(PENDING_WINDOW_FIELD)
    if isinstance(window, Mapping):
        return str(window.get("cohort_day") or "")
    detected = _timestamp(
        pending_detected_at(entry), "pending detection"
    )
    return detected.date().isoformat()


def pending_event_at(entry: Mapping[str, object]) -> object | None:
    detected_value = pending_detected_at(entry)
    if detected_value is None:
        return None
    detected = _timestamp(detected_value, "pending detection")
    window = entry.get(PENDING_WINDOW_FIELD)
    if isinstance(window, Mapping) and window.get("updated_at"):
        return max(
            detected,
            _timestamp(window["updated_at"], "pending-window update"),
        )
    return detected


def validate_pending_policy(
    state: Mapping[str, object],
) -> Mapping[str, object] | None:
    policy = state.get(PENDING_POLICY_FIELD)
    if policy is None:
        return None
    if (
        not isinstance(policy, Mapping)
        or set(policy) != PENDING_POLICY_FIELDS
        or type(policy.get("version")) is not int
        or policy.get("version") != PENDING_POLICY_VERSION
    ):
        raise PendingStateError("Invalid Standard.site pending policy")
    _daily_limit(policy.get("effective_daily_limit"))
    _timestamp(policy.get("revision_at"), "pending-policy revision")
    return policy


def effective_daily_limit(
    state: Mapping[str, object],
    *,
    required: bool,
) -> int | None:
    policy = validate_pending_policy(state)
    if policy is None:
        if required:
            raise PendingStateError(
                "Pending documents have no persisted effective daily limit"
            )
        return None
    return _daily_limit(policy["effective_daily_limit"])


def backlog_basis(
    entries: Sequence[Mapping[str, object]],
    daily_limit: int,
) -> dict[str, int]:
    limit = _daily_limit(daily_limit)
    if not entries:
        return {
            "pending_documents": 0,
            "pending_apps": 0,
            "max_per_app": 0,
            "cohort_days": 0,
        }
    if len(entries) > MAX_TRACKED_DOCUMENTS:
        raise PendingStateError("Pending document backlog is too large")
    counts = Counter(str(entry.get("app_key") or "") for entry in entries)
    if "" in counts:
        raise PendingStateError("Pending document has no app key")
    pending_documents = len(entries)
    pending_apps = len(counts)
    max_per_app = max(counts.values())
    total_days = (pending_documents + limit - 1) // limit
    app_cycles = (pending_apps + limit - 1) // limit
    round_robin_days = max_per_app * app_cycles
    cohort_days = max(total_days, round_robin_days)
    if cohort_days > MAX_WINDOW_DAYS:
        raise PendingStateError("Pending backlog window is too large")
    return {
        "pending_documents": pending_documents,
        "pending_apps": pending_apps,
        "max_per_app": max_per_app,
        "cohort_days": cohort_days,
    }


def backlog_drain_days(
    entries: Sequence[Mapping[str, object]],
    daily_limit: int,
) -> int:
    return backlog_basis(entries, daily_limit)["cohort_days"]


def _backlog_field(kind: str) -> str:
    return (
        ATTRIBUTION_REPAIR_BACKLOG_FIELD
        if kind == "attribution_repair"
        else "republish_backlog_days"
    )


def _validate_window(
    entry: Mapping[str, object],
    *,
    kind: str,
    detected: datetime,
    label: str,
) -> Mapping[str, object] | None:
    window = entry.get(PENDING_WINDOW_FIELD)
    if window is None:
        return None
    if (
        not isinstance(window, Mapping)
        or set(window) != PENDING_WINDOW_FIELDS
        or type(window.get("version")) is not int
        or window.get("version") != PENDING_WINDOW_VERSION
    ):
        raise PendingStateError(f"Invalid pending-window basis: {label}")
    cohort_day = _day(window.get("cohort_day"), "pending cohort")
    if cohort_day != detected.date():
        raise PendingStateError(f"Pending cohort day disagrees: {label}")
    limit = _daily_limit(window.get("effective_daily_limit"))
    documents = _bounded_int(
        window.get("pending_documents"),
        minimum=1,
        maximum=MAX_TRACKED_DOCUMENTS,
        label="document count",
    )
    apps = _bounded_int(
        window.get("pending_apps"),
        minimum=1,
        maximum=documents,
        label="app count",
    )
    max_per_app = _bounded_int(
        window.get("max_per_app"),
        minimum=1,
        maximum=documents - apps + 1,
        label="per-app count",
    )
    prior_days = _bounded_int(
        window.get("prior_cohort_days"),
        minimum=0,
        maximum=MAX_WINDOW_DAYS,
        label="prior cohort days",
    )
    cohort_days = _bounded_int(
        window.get("cohort_days"),
        minimum=1,
        maximum=MAX_WINDOW_DAYS,
        label="cohort days",
    )
    computed_days = _bounded_int(
        window.get("computed_days"),
        minimum=1,
        maximum=MAX_WINDOW_DAYS,
        label="computed days",
    )
    total_days = (documents + limit - 1) // limit
    app_cycles = (apps + limit - 1) // limit
    expected_cohort_days = max(
        total_days,
        max_per_app * app_cycles,
    )
    if (
        cohort_days != expected_cohort_days
        or computed_days != prior_days + cohort_days
        or entry.get(_backlog_field(kind)) != computed_days
    ):
        raise PendingStateError(
            f"Pending-window calculation basis is inconsistent: {label}"
        )
    updated = _timestamp(
        window.get("updated_at"), "pending-window update"
    )
    if updated < detected:
        raise PendingStateError(
            f"Pending-window predates detection: {label}"
        )
    return window


def validate_pending_entry(
    entry: Mapping[str, object],
    *,
    label: str,
    allow_unfinalized: bool = False,
) -> None:
    repair_fields = _prefixed_fields(entry, "repair_")
    republish_fields = _prefixed_fields(entry, "republish_")
    known_repair = set(ATTRIBUTION_REPAIR_FIELDS) | {
        ATTRIBUTION_REPAIR_BACKLOG_FIELD
    }
    unknown_repair = repair_fields - known_repair
    unknown_republish = republish_fields - set(ORDINARY_REPUBLISH_FIELDS)
    if unknown_repair or unknown_republish:
        unknown = sorted(unknown_repair | unknown_republish)
        raise PendingStateError(
            f"Unknown pending fields for {label}: {', '.join(unknown)}"
        )
    kind = pending_kind(entry)
    if kind is None:
        if PENDING_WINDOW_FIELD in entry:
            raise PendingStateError(
                f"Document retains an orphan pending window: {label}"
            )
        return
    if entry.get("published") is True:
        raise PendingStateError(
            f"Published document retains pending state: {label}"
        )
    if any(field in entry for field in CONFIRMATION_FIELDS):
        raise PendingStateError(
            f"Pending document retains remote confirmation: {label}"
        )
    if kind == "attribution_repair":
        if (
            not set(ATTRIBUTION_REPAIR_FIELDS) <= repair_fields
            or entry.get("repair_reason") != ATTRIBUTION_REPAIR_REASON
            or not SHA256_RE.fullmatch(
                str(entry.get("published_hash") or "")
            )
        ):
            raise PendingStateError(
                f"Invalid pending attribution repair: {label}"
            )
        detected = _timestamp(
            entry["repair_detected_at"], "attribution repair detection"
        )
        after_day = _day(
            entry["repair_after_day"], "attribution repair"
        )
        if detected.date() != after_day:
            raise PendingStateError(
                f"Attribution repair dates disagree: {label}"
            )
        backlog_days = entry.get(ATTRIBUTION_REPAIR_BACKLOG_FIELD)
        if backlog_days is not None:
            _bounded_int(
                backlog_days,
                minimum=1,
                maximum=MAX_WINDOW_DAYS,
                label="attribution-repair days",
            )
    else:
        required_republish = set(ORDINARY_REPUBLISH_FIELDS[:-1])
        allowed_republish = (
            required_republish
            if allow_unfinalized
            and "republish_backlog_days" not in republish_fields
            else set(ORDINARY_REPUBLISH_FIELDS)
        )
        if (
            allowed_republish != republish_fields
            or entry.get("republish_reason") != ORDINARY_REPUBLISH_REASON
            or not entry.get("published_at")
            or entry.get("published_hash") is not None
        ):
            raise PendingStateError(
                f"Invalid ordinary pending republish: {label}"
            )
        detected = _timestamp(
            entry["republish_detected_at"],
            "ordinary republish detection",
        )
        after_day = _day(
            entry["republish_after_day"], "ordinary republish"
        )
        if detected.date() != after_day:
            raise PendingStateError(
                f"Ordinary republish dates disagree: {label}"
            )
        if "republish_backlog_days" in entry:
            _bounded_int(
                entry["republish_backlog_days"],
                minimum=1,
                maximum=MAX_WINDOW_DAYS,
                label="ordinary-republish days",
            )
    _validate_window(
        entry,
        kind=kind,
        detected=detected,
        label=label,
    )


def validate_pending_state(
    state: Mapping[str, object],
    *,
    require_finalized: bool,
) -> None:
    policy = validate_pending_policy(state)
    policy_revision = (
        _timestamp(policy["revision_at"], "pending-policy revision")
        if policy is not None
        else None
    )
    documents = state.get("documents")
    if not isinstance(documents, Mapping):
        return
    for canonical, entry in documents.items():
        if not isinstance(entry, Mapping):
            continue
        label = str(canonical)
        validate_pending_entry(entry, label=label)
        kind = pending_kind(entry)
        if kind is None:
            continue
        window = entry.get(PENDING_WINDOW_FIELD)
        if require_finalized and (
            policy is None or not isinstance(window, Mapping)
        ):
            raise PendingStateError(
                f"Pending document has no finalized policy/window: {label}"
            )
        if isinstance(window, Mapping):
            if policy_revision is None:
                raise PendingStateError(
                    f"Pending window has no persisted policy: {label}"
                )
            if _timestamp(
                window["updated_at"], "pending-window update"
            ) > policy_revision:
                raise PendingStateError(
                    f"Pending window is newer than its policy: {label}"
                )


def finalize_pending_windows(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
    *,
    daily_limit: int,
    updated_at: object,
) -> bool:
    """Widen UTC-day cohorts, never shrink them, and persist their basis.

    Same-day arrivals may widen their cohort. Later UTC days form newer
    cohorts, which the publisher drains only after every older cohort.
    """
    limit = _daily_limit(daily_limit)
    current, current_text = _timestamp_text(
        updated_at, "pending-window finalization"
    )
    policy = validate_pending_policy(state)
    if policy is not None:
        revision = _timestamp(
            policy["revision_at"], "pending-policy revision"
        )
        if current < revision:
            raise PendingStateError(
                "Pending-window clock moved backwards"
            )
        if (
            policy.get("effective_daily_limit") != limit
            and current == revision
        ):
            raise PendingStateError(
                "Effective daily limit change needs a newer revision"
            )
    else:
        revision = datetime.min.replace(tzinfo=timezone.utc)

    manifest_documents = {
        str(document["canonical_url"]): document
        for document in manifest["documents"]
    }
    cohorts: dict[str, list[tuple[str, MutableMapping[str, object]]]] = {}
    for canonical in manifest_documents:
        entry = state["documents"].get(canonical)
        if not isinstance(entry, MutableMapping):
            continue
        validate_pending_entry(
            entry,
            label=canonical,
            allow_unfinalized=True,
        )
        kind = pending_kind(entry)
        if entry.get("published") is True or kind is None:
            continue
        detected = _timestamp(
            pending_detected_at(entry), "pending detection"
        )
        if detected > current:
            raise PendingStateError(
                f"Pending detection is in the future: {canonical}"
            )
        if (
            policy is not None
            and entry.get(PENDING_WINDOW_FIELD) is None
            and detected < revision
        ):
            raise PendingStateError(
                f"Backdated pending cohort cannot join the queue: {canonical}"
            )
        cohorts.setdefault(detected.date().isoformat(), []).append(
            (canonical, entry)
        )

    changed = policy is None or (
        policy.get("effective_daily_limit") != limit
    )
    prior_cohort_days = 0
    for cohort_day in sorted(cohorts):
        members = cohorts[cohort_day]
        basis = backlog_basis(
            [entry for _, entry in members],
            limit,
        )
        target_days = prior_cohort_days + basis["cohort_days"]
        for canonical, entry in members:
            kind = str(pending_kind(entry))
            backlog_field = _backlog_field(kind)
            existing_days = int(entry.get(backlog_field) or 0)
            existing_window = entry.get(PENDING_WINDOW_FIELD)
            widened_days = max(existing_days, target_days)
            cohort_grew = (
                not isinstance(existing_window, Mapping)
                or basis["pending_documents"]
                > int(existing_window["pending_documents"])
                or basis["pending_apps"]
                > int(existing_window["pending_apps"])
                or basis["max_per_app"]
                > int(existing_window["max_per_app"])
            )
            if (
                existing_window is None
                or widened_days > existing_days
                or cohort_grew
            ):
                basis_prior_days = (
                    prior_cohort_days
                    if widened_days == target_days
                    else widened_days - basis["cohort_days"]
                )
                entry[backlog_field] = widened_days
                entry[PENDING_WINDOW_FIELD] = {
                    "version": PENDING_WINDOW_VERSION,
                    "cohort_day": cohort_day,
                    "effective_daily_limit": limit,
                    "pending_documents": basis["pending_documents"],
                    "pending_apps": basis["pending_apps"],
                    "max_per_app": basis["max_per_app"],
                    "prior_cohort_days": basis_prior_days,
                    "cohort_days": basis["cohort_days"],
                    "computed_days": widened_days,
                    "updated_at": current_text,
                }
                validate_pending_entry(entry, label=canonical)
                changed = True
        prior_cohort_days += basis["cohort_days"]

    if changed:
        state[PENDING_POLICY_FIELD] = {
            "version": PENDING_POLICY_VERSION,
            "effective_daily_limit": limit,
            "revision_at": current_text,
        }
    return changed


def audit_pending_documents(
    state: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    now: datetime,
) -> dict[str, object]:
    if now.tzinfo is None:
        raise PendingStateError("Pending audit time needs a timezone")
    current = now.astimezone(timezone.utc)
    today = current.date()
    policy = validate_pending_policy(state)
    if policy is not None and _timestamp(
        policy["revision_at"], "pending-policy revision"
    ) > current:
        raise PendingStateError(
            "Pending-policy revision is in the future"
        )
    manifest_documents = {
        str(document["canonical_url"]): document
        for document in manifest["documents"]
    }
    candidates: list[tuple[str, Mapping[str, object], Mapping[str, object]]] = []
    for canonical, expected in manifest_documents.items():
        entry = state["documents"].get(canonical)
        if not isinstance(entry, Mapping):
            continue
        validate_pending_entry(entry, label=canonical)
        if entry.get("published") is True:
            continue
        kind = pending_kind(entry)
        if kind is not None or entry.get("published_at"):
            candidates.append((canonical, entry, expected))

    daily_limit = effective_daily_limit(
        state,
        required=bool(candidates),
    )
    policy_revision = (
        _timestamp(policy["revision_at"], "pending-policy revision")
        if policy is not None
        else None
    )
    for canonical, entry, _expected in candidates:
        kind = pending_kind(entry)
        window = entry.get(PENDING_WINDOW_FIELD)
        if (
            kind is not None
            and isinstance(window, Mapping)
            and policy_revision is not None
            and _timestamp(
                window["updated_at"], "pending-window update"
            )
            > policy_revision
        ):
            raise PendingStateError(
                f"Pending window is newer than its policy: {canonical}"
            )
    fallback_basis = backlog_basis(
        [entry for _, entry, _ in candidates],
        int(daily_limit or 1),
    )
    details: list[dict[str, object]] = []
    counts = {
        "attribution_repair_deferred": 0,
        "attribution_repair_pending": 0,
        "ordinary_republish": 0,
    }
    for canonical, entry, expected in candidates:
        kind = pending_kind(entry)
        if kind == "attribution_repair":
            if entry.get("published_hash") != expected.get("content_hash"):
                raise PendingStateError(
                    "Attribution repair does not preserve the current "
                    f"manifest generation: {canonical}"
                )
            detected = _timestamp(
                entry["repair_detected_at"],
                "attribution repair detection",
            )
            after_day = _day(
                entry["repair_after_day"], "attribution repair"
            )
            backlog_days = entry.get(
                ATTRIBUTION_REPAIR_BACKLOG_FIELD
            )
            window = entry.get(PENDING_WINDOW_FIELD)
            if backlog_days is None or window is None:
                raise PendingStateError(
                    f"Attribution repair has no finalized window: {canonical}"
                )
            deadline = after_day + timedelta(days=int(backlog_days))
            phase = (
                "attribution_repair_deferred"
                if today <= after_day
                else "attribution_repair_pending"
            )
        else:
            if kind == "ordinary_republish":
                detected = _timestamp(
                    entry["republish_detected_at"],
                    "ordinary republish detection",
                )
                after_day = _day(
                    entry["republish_after_day"], "ordinary republish"
                )
                backlog_days = int(entry["republish_backlog_days"])
                window = entry.get(PENDING_WINDOW_FIELD)
                if window is None:
                    raise PendingStateError(
                        f"Ordinary republish has no finalized window: {canonical}"
                    )
            else:
                if entry.get("published_hash") is not None or any(
                    field in entry for field in CONFIRMATION_FIELDS
                ):
                    raise PendingStateError(
                        "Untracked pending document retains attributed "
                        f"confirmation: {canonical}"
                    )
                detected = _timestamp(
                    entry["published_at"], "ordinary republish"
                )
                after_day = detected.date()
                backlog_days = fallback_basis["cohort_days"]
            deadline = after_day + timedelta(days=backlog_days - 1)
            phase = "ordinary_republish"
        if detected > current or after_day > today:
            raise PendingStateError(
                f"Pending document starts in the future: {canonical}"
            )
        if today > deadline:
            raise PendingStateError(
                f"{phase.replace('_', ' ').title()} exceeded its bounded "
                f"backlog window: {canonical} "
                f"(deadline {deadline.isoformat()})"
            )
        counts[phase] += 1
        details.append(
            {
                "canonical_url": canonical,
                "kind": kind or "ordinary_republish",
                "phase": phase,
                "deadline_day": deadline.isoformat(),
                "window": (
                    dict(entry[PENDING_WINDOW_FIELD])
                    if kind is not None
                    else None
                ),
            }
        )

    details.sort(key=lambda item: str(item["canonical_url"]))
    repair_total = (
        counts["attribution_repair_deferred"]
        + counts["attribution_repair_pending"]
    )
    warnings: list[str] = []
    if repair_total:
        warnings.append(
            f"{repair_total} tracked attribution repair(s) remain inside "
            "their bounded publishing window"
        )
    if counts["ordinary_republish"]:
        warnings.append(
            f"{counts['ordinary_republish']} ordinary document republish(es) "
            "remain inside their bounded publishing window"
        )
    return {
        "documents": details,
        "counts": {
            **counts,
            "attribution_repair": repair_total,
            "total": len(details),
        },
        "warnings": warnings,
        "backlog_upper_days": fallback_basis["cohort_days"],
        "daily_limit": daily_limit,
        "policy_version": (
            policy["version"] if policy is not None else None
        ),
    }
