"""Reviewed identity authority for every external-promotion consumer.

The JSON roster is changed by a reviewed source commit, never by a lookup.
Deployment copies of this module, the roster and official_locales.py must be
byte-identical to the GrowthEngine sources.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

if __package__:
    from .official_locales import OFFICIAL_LOCALES
else:
    from official_locales import OFFICIAL_LOCALES


SCHEMA = "lumi.current-source/v1"
ROSTER_SCHEMA = "lumi.live-app-roster/v1"
MANIFEST_PATH = Path(__file__).with_name("live_app_manifest.json")
APP_COUNT = 47
LOCALE_COUNT = 50
PAIR_COUNT = APP_COUNT * LOCALE_COUNT


class SourceError(ValueError):
    """A consumer is not using the complete reviewed current source."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceError(f"Duplicate current-source field: {key}")
        result[key] = value
    return result


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def load_source(path: Path | str | None = None) -> dict:
    path = Path(path) if path is not None else MANIFEST_PATH
    try:
        raw = path.read_bytes()
        document = json.loads(raw, object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SourceError(f"Current-source manifest is unavailable: {path}") from error
    if (
        not isinstance(document, dict)
        or set(document) != {"schema", "version", "revision", "roster_digest", "apps"}
        or document["schema"] != ROSTER_SCHEMA
        or type(document["version"]) is not int or document["version"] != 1
        or type(document["revision"]) is not int or document["revision"] < 1
        or not isinstance(document["apps"], dict)
        or len(document["apps"]) != APP_COUNT
    ):
        raise SourceError(f"Current source requires exactly {APP_COUNT} reviewed App identities")
    apps = document["apps"]
    ids = set()
    for key, app in apps.items():
        if (
            not isinstance(key, str) or re.fullmatch(r"[a-z0-9]+", key) is None
            or not isinstance(app, dict) or set(app) != {"app_id", "name"}
            or not isinstance(app["app_id"], str)
            or re.fullmatch(r"[0-9]+", app["app_id"]) is None
            or not isinstance(app["name"], str) or not app["name"].strip()
            or app["app_id"] in ids
        ):
            raise SourceError(f"Invalid current-source App identity: {key}")
        ids.add(app["app_id"])
    if document["roster_digest"] != _digest(apps):
        raise SourceError("Current-source roster digest mismatch")
    locales = tuple(OFFICIAL_LOCALES)
    if len(locales) != LOCALE_COUNT or len(set(locales)) != LOCALE_COUNT:
        raise SourceError(f"Current source requires exactly {LOCALE_COUNT} official locales")
    return {
        "schema": SCHEMA,
        "revision": document["revision"],
        "source_path": "geo/live_app_manifest.json",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "roster_digest": document["roster_digest"],
        "apps": dict(sorted(apps.items())),
        "locales": locales,
        "locale_roster_sha256": _digest(locales),
        "app_count": APP_COUNT,
        "locale_count": LOCALE_COUNT,
        "pair_count": PAIR_COUNT,
    }


def appstore_ids(source: dict | None = None) -> dict[str, str]:
    source = load_source() if source is None else source
    return {key: app["app_id"] for key, app in source["apps"].items()}


def campaign_pairs(source: dict | None = None) -> tuple[tuple[str, str], ...]:
    source = load_source() if source is None else source
    return tuple(
        (key, locale) for key in source["apps"] for locale in source["locales"]
    )


def validate_consumer(appstore: dict, registry: dict | None = None, *, source=None) -> dict:
    source = load_source() if source is None else source
    expected = appstore_ids(source)
    if appstore != expected:
        missing = sorted(set(expected) - set(appstore))
        extra = sorted(set(appstore) - set(expected))
        raise SourceError(
            "Consumer current-source identity drift; "
            f"missing={missing}, extra={extra}, expected={source['source_sha256']}"
        )
    if registry is not None:
        if set(registry) != set(expected):
            raise SourceError("Consumer creative registry must cover the exact current source")
        for key, identity in source["apps"].items():
            if not isinstance(registry[key], dict) or registry[key].get("name") != identity["name"]:
                raise SourceError(f"Consumer current-source name drift: {key}")
    return source
