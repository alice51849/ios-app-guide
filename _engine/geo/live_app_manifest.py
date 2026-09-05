#!/usr/bin/env python3
"""Versioned, read-only App Store inventory shared by growth consumers."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid


SCHEMA = "lumi.live-app-manifest/v2"
VERSION = 2
ROSTER_SCHEMA = "lumi.live-app-roster/v1"
MAX_TTL_SECONDS = 24 * 60 * 60
MIN_APP_COUNT = 46
DEFAULT_MANIFEST = Path(__file__).with_suffix(".json")
DEFAULT_ROSTER = DEFAULT_MANIFEST
LOOKUP_COUNTRIES = ("us", "tw", "jp", "gb")
RETIRE_AFTER_MISSES = 3
SOURCE = "Apple iTunes Lookup API (US, TW, JP, GB)"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FIELDS = {
    "schema", "version", "generated_at", "ttl_seconds", "source",
    "roster_digest", "live_state_sha256", "apps", "observations",
}
_ROSTER_FIELDS = {"schema", "version", "revision", "roster_digest", "apps"}
_OBSERVATION_FIELDS = {"status", "checked_at", "reason"}
_OBSERVATION_OPTIONAL = {
    "last_verified_at", "consecutive_misses", "confirmed_sources",
}


class ManifestError(ValueError):
    """The inventory cannot be used as current, complete evidence."""


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ManifestError("Manifest timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ManifestError(f"Invalid manifest timestamp: {value!r}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ManifestError("Manifest timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _now(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ManifestError("Validation time must include a timezone")
    return value.astimezone(timezone.utc)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _apps(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict) or len(value) < MIN_APP_COUNT:
        raise ManifestError(
            f"Live manifest must retain at least {MIN_APP_COUNT} apps; "
            "legacy 45-app baselines are not accepted"
        )
    normalized = {}
    ids = set()
    for key, app in value.items():
        if (
            not isinstance(key, str)
            or re.fullmatch(r"[a-z0-9]+", key) is None
            or not isinstance(app, dict)
            or set(app) != {"app_id", "name"}
            or not isinstance(app["app_id"], str)
            or re.fullmatch(r"[0-9]+", app["app_id"]) is None
            or not isinstance(app["name"], str)
            or not app["name"].strip()
        ):
            raise ManifestError(f"Invalid live manifest app: {key!r}")
        if app["app_id"] in ids:
            raise ManifestError(f"Duplicate App Store ID: {app['app_id']}")
        ids.add(app["app_id"])
        normalized[key] = dict(app)
    return dict(sorted(normalized.items()))


def roster_digest(apps: object) -> str:
    return _digest(_apps(apps))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"Duplicate manifest JSON field: {key}")
        result[key] = value
    return result


def _read(path: Path | str) -> dict:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise ManifestError(f"Live manifest is unavailable: {path}") from error


def _validate_envelope(document: object) -> dict:
    if (
        not isinstance(document, dict)
        or not _FIELDS <= set(document) <= _FIELDS | {"pending_adoptions"}
        or document.get("schema") != SCHEMA
        or type(document.get("version")) is not int
        or document["version"] != VERSION
    ):
        raise ManifestError(f"Live manifest schema must be {SCHEMA}")
    if (
        type(document["ttl_seconds"]) is not int
        or not 0 < document["ttl_seconds"] <= MAX_TTL_SECONDS
        or document["source"] != SOURCE
        or not isinstance(document["live_state_sha256"], str)
        or _SHA256.fullmatch(document["live_state_sha256"]) is None
    ):
        raise ManifestError("Live manifest TTL, source or state digest is invalid")
    generated = timestamp(document["generated_at"])
    apps = _apps(document["apps"])
    if document["roster_digest"] != roster_digest(apps):
        raise ManifestError("Live manifest roster digest does not match its apps")
    observations = document["observations"]
    if not isinstance(observations, dict) or set(observations) != set(apps):
        raise ManifestError("Live manifest observations must cover the exact roster")
    for key, observation in observations.items():
        if (
            not isinstance(observation, dict)
            or not _OBSERVATION_FIELDS <= set(observation) <= _OBSERVATION_FIELDS | _OBSERVATION_OPTIONAL
            or observation["status"] not in ("live", "unknown", "unavailable")
            or not isinstance(observation["reason"], str)
            or (
                observation["status"] != "live"
                and not observation["reason"].strip()
            )
        ):
            raise ManifestError(f"Invalid live manifest observation: {key}")
        checked = observation["checked_at"]
        if checked is None:
            if observation["status"] != "unknown":
                raise ManifestError(f"Live observation has no timestamp: {key}")
        elif timestamp(checked) > generated:
            raise ManifestError(f"Observation is newer than the manifest: {key}")
        verified = observation.get("last_verified_at")
        if verified is not None and timestamp(verified) > generated:
            raise ManifestError(f"Last-good observation is newer than the manifest: {key}")
        misses = observation.get("consecutive_misses", 0)
        if type(misses) is not int or not 0 <= misses <= RETIRE_AFTER_MISSES:
            raise ManifestError(f"Invalid consecutive misses: {key}")
        if observation["status"] == "unavailable" and misses != RETIRE_AFTER_MISSES:
            raise ManifestError(f"Unavailable App requires three clean misses: {key}")
        sources = observation.get("confirmed_sources", [])
        if (
            not isinstance(sources, list)
            or any(not isinstance(value, str) or value not in (*LOOKUP_COUNTRIES, "aggregate") for value in sources)
            or len(sources) != len(set(sources))
        ):
            raise ManifestError(f"Invalid verification sources: {key}")
    pending = document.get("pending_adoptions", [])
    if not isinstance(pending, list):
        raise ManifestError("Pending adoptions must be an array")
    pending_ids = set()
    for entry in pending:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"key", "app_id", "name", "sources"}
            or not isinstance(entry["key"], str)
            or not isinstance(entry["app_id"], str)
            or not entry["app_id"].isdigit()
            or not isinstance(entry["name"], str) or not entry["name"].strip()
            or entry["key"] in apps
            or entry["app_id"] in pending_ids
            or not isinstance(entry["sources"], list)
            or any(value not in (*LOOKUP_COUNTRIES, "aggregate") for value in entry["sources"])
        ):
            raise ManifestError("Invalid pending App adoption")
        pending_ids.add(entry["app_id"])
    return {**document, "apps": apps}


def _validate_roster(document: object) -> dict:
    if (
        not isinstance(document, dict) or set(document) != _ROSTER_FIELDS
        or document.get("schema") != ROSTER_SCHEMA
        or type(document.get("version")) is not int or document["version"] != 1
        or type(document.get("revision")) is not int or document["revision"] < 1
    ):
        raise ManifestError(f"Versioned roster schema must be {ROSTER_SCHEMA}")
    apps = _apps(document["apps"])
    if document["roster_digest"] != roster_digest(apps):
        raise ManifestError("Versioned roster digest does not match its apps")
    return {**document, "apps": apps}


def canonical_manifest() -> dict:
    """Load timeless identity, never availability or a current verification claim."""
    return _validate_roster(_read(DEFAULT_ROSTER))


def runtime_manifest_path() -> Path:
    return Path(os.environ.get(
        "GROWTH_LIVE_MANIFEST",
        Path(__file__).resolve().parents[1] / ".growth-runtime" / "live-app-manifest.json",
    )).expanduser()


def _statuses(document: dict, now: datetime) -> dict[str, dict]:
    generated = timestamp(document["generated_at"])
    if generated > now:
        raise ManifestError("Live manifest generated_at is in the future")
    ttl = document["ttl_seconds"]
    expired = (now - generated).total_seconds() >= ttl
    rows = {}
    for key, observation in document["observations"].items():
        checked = observation["checked_at"]
        age = (now - timestamp(checked)).total_seconds() if checked else None
        stale = checked is not None and (expired or (age is not None and age >= ttl))
        reason = observation["reason"]
        if stale:
            reason = "; ".join(filter(None, ("Live inventory TTL expired", reason)))
        rows[key] = {
            "inventory_status": "stale" if stale else observation["status"],
            "inventory_reason": reason,
            "inventory_observed_at": checked,
            "inventory_last_verified_at": observation.get(
                "last_verified_at", checked if observation["status"] == "live" else None,
            ),
            "public_eligible": observation["status"] != "unavailable",
            "consecutive_misses": observation.get("consecutive_misses", 0),
        }
    return rows


def validate_manifest(
    document: object, *, now: datetime | None = None, require_fresh: bool = True,
) -> dict:
    normalized = _validate_envelope(document)
    baseline = canonical_manifest()
    if normalized["roster_digest"] != baseline["roster_digest"]:
        missing = sorted(set(baseline["apps"]) - set(normalized["apps"]))
        extra = sorted(set(normalized["apps"]) - set(baseline["apps"]))
        raise ManifestError(
            f"Live manifest roster drift from versioned baseline; "
            f"missing={missing}, extra={extra}"
        )
    if normalized.get("pending_adoptions"):
        appstore, registry = _registry()
        if any(
            str(appstore.get(entry["key"], "")) != entry["app_id"]
            or registry.get(entry["key"], {}).get("name") != entry["name"]
            for entry in normalized["pending_adoptions"]
        ):
            raise ManifestError("Unregistered pending adoption identity")
    states = _statuses(normalized, _now(now))
    stale = [key for key, state in states.items() if state["inventory_status"] == "stale"]
    if require_fresh and stale:
        raise ManifestError("Live manifest TTL expired (stale): " + ", ".join(sorted(stale)))
    return normalized


def load_manifest(
    path: Path | str | None = None, *, now: datetime | None = None,
    require_fresh: bool = True,
) -> dict:
    path = Path(path) if path is not None else runtime_manifest_path()
    if not path.exists():
        now = _now(now)
        return create_manifest(
            canonical_manifest()["apps"], now=now,
            observations={
                key: {
                    "status": "unknown", "checked_at": None,
                    "reason": "Availability snapshot is missing; versioned roster retained",
                }
                for key in canonical_manifest()["apps"]
            },
        )
    return validate_manifest(
        _read(path),
        now=now, require_fresh=require_fresh,
    )


def app_statuses(document: dict, *, now: datetime | None = None) -> dict[str, dict]:
    now = _now(now)
    return _statuses(validate_manifest(document, now=now, require_fresh=False), now)


def manifest_fingerprint(document: dict, *, now: datetime | None = None) -> dict:
    document = validate_manifest(document, now=now, require_fresh=False)
    # Verification times expire evidence, but must not force an expensive full
    # acquisition refresh when the verified identities and availability are unchanged.
    return {
        key: document[key]
        for key in ("schema", "version", "roster_digest", "live_state_sha256", "apps")
    } | {
        "availability": {
            key: value["status"]
            for key, value in sorted(document["observations"].items())
        }
    }


def validate_outreach_coverage(
    document: object, *, now: datetime | None = None, require_fresh: bool = True,
) -> dict[str, dict]:
    now = _now(now)
    if not isinstance(document, dict) or document.get("schema") != "lumi.outreach-scorecard/v2":
        raise ManifestError("Owned-outreach coverage requires the versioned v2 schema")
    inventory = validate_manifest(
        document.get("live_inventory"), now=now, require_fresh=False,
    )
    generated = timestamp(document.get("generated_at"))
    if generated > now or generated < timestamp(inventory["generated_at"]):
        raise ManifestError("Owned-outreach coverage timestamp does not match its inventory")
    expired = (now - generated).total_seconds() >= inventory["ttl_seconds"]
    if require_fresh and expired:
        raise ManifestError("Owned-outreach coverage TTL expired")
    raw_rows = document.get("rows")
    if (
        not isinstance(raw_rows, list)
        or type(document.get("live_app_count")) is not int
        or type(document.get("public_apps")) is not int
        or document["live_app_count"] != len(inventory["apps"])
    ):
        raise ManifestError("Owned-outreach coverage has incomplete roster metadata")
    states = _statuses(inventory, now)
    rows = {}
    public_count = 0
    for row in raw_rows:
        if not isinstance(row, dict) or type(row.get("public")) is not bool:
            raise ManifestError("Owned-outreach coverage has an invalid row")
        key = row.get("key")
        if not isinstance(key, str):
            raise ManifestError("Owned-outreach coverage has an invalid App key")
        if key not in inventory["apps"]:
            if row.get("in_live_roster") is not False or row["public"]:
                raise ManifestError("Owned-outreach coverage contains roster drift")
            continue
        if (
            key in rows
            or row.get("in_live_roster") is not True
            or row.get("app_id") != inventory["apps"][key]["app_id"]
        ):
            raise ManifestError(f"Owned-outreach coverage App identity drift: {key}")
        score = row.get("coverage_score")
        if (
            isinstance(score, bool) or not isinstance(score, (int, float))
            or not 0 <= score <= 1 or not math.isfinite(score)
        ):
            raise ManifestError(f"Invalid owned-outreach coverage score: {key}")
        public_count += row["public"]
        state = dict(states[key])
        if expired:
            state.update(inventory_status="stale", inventory_reason="Owned-outreach coverage TTL expired")
        elif state["inventory_status"] == "live" and row.get("inventory_status") in ("unknown", "stale"):
            state["inventory_status"] = row["inventory_status"]
            state["inventory_reason"] = row.get("inventory_reason", "")
        rows[key] = {
            **row, **state,
            "public": row["public"] and state["public_eligible"],
        }
    if set(rows) != set(inventory["apps"]) or document.get("public_apps") != public_count:
        raise ManifestError("Owned-outreach coverage does not contain the exact live roster")
    return rows


def create_manifest(
    apps: dict, *, now: datetime | None = None, observations: dict | None = None,
    live_state_sha256: str | None = None,
) -> dict:
    now = _now(now)
    apps = _apps(apps)
    if observations is None:
        observations = {
            key: {"status": "live", "checked_at": now.isoformat(), "reason": ""}
            for key in apps
        }
    state = {
        key: observation["status"]
        for key, observation in sorted(observations.items())
    }
    return _validate_envelope({
        "schema": SCHEMA,
        "version": VERSION,
        "source": SOURCE,
        "generated_at": now.isoformat(),
        "ttl_seconds": MAX_TTL_SECONDS,
        "roster_digest": roster_digest(apps),
        "live_state_sha256": live_state_sha256 or _digest(state),
        "apps": apps,
        "observations": observations,
    })


def _registry(appstore=None, registry=None):
    if appstore is None or registry is None:
        source = Path(__file__).resolve().parents[1] / "social" / "videogen" / "registry.py"
        spec = importlib.util.spec_from_file_location("_live_manifest_registry", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        appstore = module.APPSTORE if appstore is None else appstore
        registry = module.APPS if registry is None else registry
    ids = [str(value) for value in appstore.values() if value]
    if len(ids) != len(set(ids)) or any(not value.isascii() or not value.isdigit() for value in ids):
        raise ManifestError("Registered App Store identities must be unique numeric IDs")
    return appstore, registry


def _lookup_results(appstore, *, lookup=None, lookup_country=None):
    if lookup_country is None and lookup is None:
        if __package__:
            from .appstore_live import _lookup_country
        else:
            from appstore_live import _lookup_country
        lookup_country = _lookup_country
    results = {}
    for country in (("aggregate",) if lookup is not None else LOOKUP_COUNTRIES):
        try:
            values = lookup(appstore.values()) if lookup is not None else lookup_country(appstore.values(), country)
        except (OSError, RuntimeError, TimeoutError):
            results[country] = None
            continue
        if (
            not isinstance(values, (set, frozenset, list, tuple))
            or any(not str(value).isascii() or not str(value).isdigit() for value in values)
        ):
            raise ManifestError(f"Malformed public lookup result: {country}")
        results[country] = {str(value) for value in values}
    observed = set().union(*(values for values in results.values() if values is not None))
    unknown = observed - {str(value) for value in appstore.values() if value}
    if unknown:
        raise ManifestError(
            "Unregistered App IDs in lookup; adoption refused: " + ", ".join(sorted(unknown))
        )
    return results


def _atomic_json(path, document, *, mode):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if mode == 0o600 else 0o755)
    staged = path.with_name(f".{path.name}.{uuid.uuid4().hex}.part")
    try:
        descriptor = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        staged.chmod(mode)
        os.replace(staged, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        staged.unlink(missing_ok=True)


@contextmanager
def _roster_lock(path):
    directory = runtime_manifest_path().parent
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:16]
    descriptor = os.open(directory / f"roster-{name}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def adopt_registered_live_apps(results, *, appstore=None, registry=None):
    """Add only registry-owned IDs freshly confirmed by two Apple storefronts."""
    appstore, registry = _registry(appstore, registry)
    if not isinstance(results, dict) or any(source not in (*LOOKUP_COUNTRIES, "aggregate") for source in results):
        raise ManifestError("Adoption requires identified Apple storefront sources")
    observed = set()
    for source, values in results.items():
        if values is None:
            continue
        if not isinstance(values, (set, frozenset)) or any(not isinstance(value, str) or not value.isdigit() for value in values):
            raise ManifestError(f"Invalid adoption evidence: {source}")
        observed.update(values)
    known_ids = {str(value) for value in appstore.values()}
    if observed - known_ids:
        raise ManifestError("Unregistered App IDs cannot be adopted")
    for key, app_id in appstore.items():
        if str(app_id) in observed and (
            key not in registry or not isinstance(registry[key].get("name"), str)
            or not registry[key]["name"].strip()
        ):
            raise ManifestError(f"App must be registered in both APPSTORE and APPS: {key}")
    with _roster_lock(DEFAULT_ROSTER):
        roster = canonical_manifest()
        apps = dict(roster["apps"])
        if any(
            str(appstore.get(key, "")) != app["app_id"]
            or registry.get(key, {}).get("name") != app["name"]
            for key, app in apps.items()
        ):
            raise ManifestError("Registry roster drift blocks automatic adoption")
        added = []
        for key, app_id in appstore.items():
            sources = [source for source in LOOKUP_COUNTRIES if str(app_id) in (results.get(source) or set())]
            if key not in apps and len(sources) >= 2:
                apps[key] = {"app_id": str(app_id), "name": registry[key]["name"]}
                added.append(key)
        if added:
            candidate = _validate_roster({
                **roster, "revision": roster["revision"] + 1,
                "apps": apps, "roster_digest": roster_digest(apps),
            })
            _atomic_json(DEFAULT_ROSTER, candidate, mode=0o644)
        return sorted(added)


def _previous_snapshot(path, apps, now, *, registered_ids):
    if path is None or not Path(path).exists():
        return None
    previous = _validate_envelope(_read(path))
    _statuses(previous, now)
    snapshot_ids = {app["app_id"] for app in previous["apps"].values()}
    snapshot_ids.update(entry["app_id"] for entry in previous.get("pending_adoptions", []))
    unregistered = snapshot_ids - registered_ids
    if unregistered:
        raise ManifestError(
            "Unregistered App IDs in last-good availability snapshot: "
            + ", ".join(sorted(unregistered))
        )
    if any(apps.get(key) != app for key, app in previous["apps"].items()):
        print(
            "Availability advisory: discarding stale last-good snapshot with outdated "
            "roster identity; rebuilding without cached availability history",
            file=sys.stderr,
        )
        return None
    return previous


def refresh_manifest(
    appstore: dict | None = None, registry: dict | None = None, *,
    now: datetime | None = None, lookup=None, lookup_country=None,
    previous_path: Path | str | None = None, adopt: bool = False,
) -> dict:
    """Refresh availability independently; outages never delete roster identities."""
    appstore, registry = _registry(appstore, registry)
    baseline = canonical_manifest()
    for key, app in baseline["apps"].items():
        if (
            str(appstore.get(key, "")) != app["app_id"]
            or key not in registry or registry[key].get("name") != app["name"]
        ):
            raise ManifestError(f"Registry roster drift: {key}")
    now = _now(now)
    previous = _previous_snapshot(
        previous_path, baseline["apps"], now,
        registered_ids={str(app_id) for app_id in appstore.values() if app_id},
    )
    results = _lookup_results(appstore, lookup=lookup, lookup_country=lookup_country)
    if adopt:
        adopt_registered_live_apps(results, appstore=appstore, registry=registry)
        baseline = canonical_manifest()
    apps = baseline["apps"]
    observed = set().union(*(values for values in results.values() if values is not None))
    clean = (
        all(results.get(source) is not None for source in LOOKUP_COUNTRIES)
        and len(observed & {app["app_id"] for app in apps.values()}) >= max(1, len(apps) // 2)
    )
    pending = []
    for key, app_id in appstore.items():
        if str(app_id) in observed and key not in apps:
            if key not in registry:
                raise ManifestError(f"Observed App is not registered in APPS: {key}")
            pending.append({
                "key": key, "app_id": str(app_id), "name": registry[key]["name"],
                "sources": sorted(source for source, values in results.items() if values and str(app_id) in values),
            })
    observations = {}
    for key, app in apps.items():
        old = (previous or {}).get("observations", {}).get(key, {})
        verified = old.get("last_verified_at") or (
            old.get("checked_at") if old.get("status") == "live" else None
        )
        live = app["app_id"] in observed
        misses = 0 if live else min(
            RETIRE_AFTER_MISSES, old.get("consecutive_misses", 0) + int(clean),
        )
        status = "live" if live else (
            "unavailable" if misses >= RETIRE_AFTER_MISSES else "unknown"
        )
        observations[key] = {
            "status": status,
            "checked_at": now.isoformat() if any(value is not None for value in results.values()) else None,
            "last_verified_at": now.isoformat() if live else verified,
            "consecutive_misses": misses,
            "confirmed_sources": sorted(source for source, values in results.items() if values and app["app_id"] in values),
            "reason": "" if live else (
                f"Not observed in {misses}/3 consecutive clean checks; identity retained"
                if clean else "Lookup incomplete; last-good availability and miss count retained"
            ),
        }
        if status == "unavailable" and observations[key]["checked_at"] is None:
            observations[key]["checked_at"] = old["checked_at"]
    document = create_manifest(apps, now=now, observations=observations)
    document["pending_adoptions"] = sorted(pending, key=lambda entry: entry["key"])
    return validate_manifest(document, now=now, require_fresh=False)


def write_manifest(path: Path | str, document: dict, *, private: bool = False) -> None:
    document = validate_manifest(document, require_fresh=False)
    path = Path(path)
    if path.resolve() == DEFAULT_ROSTER.resolve():
        raise ManifestError("Availability snapshots cannot overwrite the versioned roster")
    _atomic_json(path, document, mode=0o600 if private else 0o644)


def write_legacy_live_state(path, document):
    """Compatibility membership only; no runtime timestamps enter the Pages tree."""
    if __package__:
        from .appstore_live import _write_state
    else:
        from appstore_live import _write_state
    states = app_statuses(document)
    ids = {document["apps"][key]["app_id"] for key, row in states.items() if row["public_eligible"]}
    misses = {
        document["apps"][key]["app_id"]: row["consecutive_misses"]
        for key, row in states.items()
        if row["public_eligible"] and row["consecutive_misses"]
    }
    _write_state(str(path), ids, misses)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--adopt", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--live-state-output", type=Path)
    args = parser.parse_args(argv)
    if args.refresh and args.output is None:
        parser.error("--refresh requires an explicit --output")
    if args.adopt and not args.refresh:
        parser.error("--adopt requires --refresh")
    try:
        document = refresh_manifest(previous_path=args.output, adopt=args.adopt) if args.refresh else load_manifest(args.manifest, require_fresh=False)
        if args.output:
            write_manifest(args.output, document, private=True)
        if args.live_state_output:
            write_legacy_live_state(args.live_state_output, document)
        states = app_statuses(document)
        gaps = sorted(key for key, row in states.items() if row["inventory_status"] != "live")
        print(
            f"Live manifest: {len(states)} apps; {len(gaps)} unknown/stale; "
            f"roster={document['roster_digest']}"
        )
        if gaps:
            print("Availability advisory: " + ", ".join(gaps), file=sys.stderr)
        if document.get("pending_adoptions"):
            print("Pending registered App adoption: " + ", ".join(row["key"] for row in document["pending_adoptions"]), file=sys.stderr)
        return 0
    except ManifestError as error:
        print(f"Live manifest invalid: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
