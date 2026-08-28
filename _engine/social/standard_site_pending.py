#!/usr/bin/env python3
"""Bounded pending-state contract for Standard.site document publishing."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import re
from typing import Mapping, Sequence


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
CONFIRMATION_FIELDS = (
    "at_uri",
    "cid",
    "record_hash",
    "last_verified_at",
    "updated_at",
)
MAX_DAILY_LIMIT = 4
MAX_BACKLOG_DAYS = 5_000
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


def _day(value: object, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise PendingStateError(f"Invalid {label} day: {value!r}") from error


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


def validate_pending_entry(
    entry: Mapping[str, object],
    *,
    label: str,
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
        if backlog_days is not None and (
            type(backlog_days) is not int
            or not 1 <= backlog_days <= MAX_BACKLOG_DAYS
        ):
            raise PendingStateError(
                f"Invalid attribution repair backlog: {label}"
            )
        return
    if (
        set(ORDINARY_REPUBLISH_FIELDS) != republish_fields
        or entry.get("republish_reason") != ORDINARY_REPUBLISH_REASON
        or not entry.get("published_at")
        or entry.get("published_hash") is not None
    ):
        raise PendingStateError(
            f"Invalid ordinary pending republish: {label}"
        )
    detected = _timestamp(
        entry["republish_detected_at"], "ordinary republish detection"
    )
    after_day = _day(entry["republish_after_day"], "ordinary republish")
    if detected.date() != after_day:
        raise PendingStateError(
            f"Ordinary republish dates disagree: {label}"
        )
    backlog_days = entry["republish_backlog_days"]
    if (
        type(backlog_days) is not int
        or not 1 <= backlog_days <= MAX_BACKLOG_DAYS
    ):
        raise PendingStateError(
            f"Invalid ordinary republish backlog: {label}"
        )


def backlog_drain_days(
    entries: Sequence[Mapping[str, object]],
    daily_limit: int,
) -> int:
    if (
        type(daily_limit) is not int
        or not 1 <= daily_limit <= MAX_DAILY_LIMIT
    ):
        raise PendingStateError("Daily document limit is invalid")
    if not entries:
        return 0
    counts = Counter(str(entry.get("app_key") or "") for entry in entries)
    if "" in counts:
        raise PendingStateError("Pending document has no app key")
    limit_bound = (len(entries) + daily_limit - 1) // daily_limit
    return max(limit_bound, max(counts.values()))


def audit_pending_documents(
    state: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    now: datetime,
    daily_limit: int,
) -> dict[str, object]:
    if now.tzinfo is None:
        raise PendingStateError("Pending audit time needs a timezone")
    current = now.astimezone(timezone.utc)
    today = current.date()
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
        if pending_kind(entry) is not None or entry.get("published_at"):
            candidates.append((canonical, entry, expected))

    fallback_days = backlog_drain_days(
        [entry for _, entry, _ in candidates],
        daily_limit,
    )
    manifest_upper_days = backlog_drain_days(
        list(manifest_documents.values()),
        daily_limit,
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
            if detected > current:
                raise PendingStateError(
                    f"Attribution repair detection is in the future: {canonical}"
                )
            after_day = _day(
                entry["repair_after_day"], "attribution repair"
            )
            backlog_days = entry.get(
                ATTRIBUTION_REPAIR_BACKLOG_FIELD
            )
            if backlog_days is None:
                backlog_days = fallback_days
            if int(backlog_days) > manifest_upper_days:
                raise PendingStateError(
                    "Attribution repair backlog exceeds the manifest/limit "
                    f"upper bound: {canonical}"
                )
            deadline = after_day + timedelta(days=int(backlog_days))
            phase = (
                "attribution_repair_deferred"
                if today <= after_day
                else "attribution_repair_pending"
            )
            if today > deadline:
                raise PendingStateError(
                    "Attribution repair exceeded its bounded backlog window: "
                    f"{canonical} (deadline {deadline.isoformat()})"
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
                backlog_days = fallback_days
            if backlog_days > manifest_upper_days:
                raise PendingStateError(
                    "Ordinary republish backlog exceeds the manifest/limit "
                    f"upper bound: {canonical}"
                )
            if detected > current or after_day > today:
                raise PendingStateError(
                    f"Ordinary republish starts in the future: {canonical}"
                )
            deadline = after_day + timedelta(days=backlog_days - 1)
            phase = "ordinary_republish"
            if today > deadline:
                raise PendingStateError(
                    "Ordinary republish exceeded its bounded backlog window: "
                    f"{canonical} (deadline {deadline.isoformat()})"
                )
        counts[phase] += 1
        details.append(
            {
                "canonical_url": canonical,
                "kind": kind or "ordinary_republish",
                "phase": phase,
                "deadline_day": deadline.isoformat(),
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
        "backlog_upper_days": fallback_days,
        "manifest_upper_days": manifest_upper_days,
        "daily_limit": daily_limit,
    }
