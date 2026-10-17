#!/usr/bin/env python3
"""Export public ASC localizations for GEO use without mutating App Store data."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "social"))

import asc  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    require_official_locale_coverage,
)
from videogen.registry import APPSTORE  # noqa: E402


# Every roster App exports to data/<key>_full.json, the copy bank the Guide,
# support sites and threads-autopilot contracts read.
OUTPUT_FILES = {key: f"{key}_full.json" for key in APPSTORE}
REQUIRED_FIELDS = ("name", "subtitle", "description", "keywords", "promotionalText")
PUBLIC_STATES = {"READY_FOR_SALE", "READY_FOR_DISTRIBUTION"}


def _version_key(item):
    version = item.get("attributes", {}).get("versionString", "")
    parts = tuple(int(value) for value in re.findall(r"\d+", version))
    return parts, version


def _select_public_resource(items, label):
    public = [
        item
        for item in items
        if item.get("attributes", {}).get("appStoreState") in PUBLIC_STATES
    ]
    if not public:
        raise RuntimeError(f"No public {label} found")
    return max(public, key=_version_key) if label == "version" else public[0]


def _localizations(resource_type, resource_id, fields):
    endpoint = (
        f"/v1/{resource_type}s/{resource_id}/{resource_type}Localizations"
    )
    localization_type = f"{resource_type}Localizations"
    return asc.get_all(
        endpoint,
        {f"fields[{localization_type}]": ",".join(("locale", *fields))},
    )


def fetch_public_localizations(key):
    app_id = APPSTORE[key]
    versions = asc.get_all(
        f"/v1/apps/{app_id}/appStoreVersions",
        {
            "filter[platform]": "IOS",
            "fields[appStoreVersions]": "versionString,appStoreState,platform",
        },
    )
    app_infos = asc.get_all(
        f"/v1/apps/{app_id}/appInfos",
        {"fields[appInfos]": "appStoreState"},
    )
    version = _select_public_resource(versions, "version")
    app_info = _select_public_resource(app_infos, "app info")

    info_by_locale = {
        item["attributes"]["locale"]: item["attributes"]
        for item in _localizations(
            "appInfo", app_info["id"], ("name", "subtitle")
        )
    }
    version_by_locale = {
        item["attributes"]["locale"]: item["attributes"]
        for item in _localizations(
            "appStoreVersion",
            version["id"],
            ("description", "keywords", "promotionalText"),
        )
    }
    require_official_locale_coverage(key, info_by_locale)
    require_official_locale_coverage(key, version_by_locale)

    exported = {}
    for locale in OFFICIAL_LOCALES:
        merged = {
            **info_by_locale[locale],
            **version_by_locale[locale],
        }
        merged.pop("locale", None)
        empty = [
            field
            for field in REQUIRED_FIELDS
            if not str(merged.get(field) or "").strip()
        ]
        if empty:
            raise ValueError(f"{key}/{locale} has empty fields: {','.join(empty)}")
        exported[locale] = {field: merged[field].strip() for field in REQUIRED_FIELDS}
    return exported


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--app",
        action="append",
        choices=tuple(OUTPUT_FILES),
        dest="apps",
        help="App key to export; repeat for multiple apps (default: all configured apps).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data",
        help="Destination directory for deterministic public metadata snapshots.",
    )
    return parser.parse_args()


def merge_existing(path, payload):
    """Keep fields this export does not own (e.g. subtitle_orig) on each locale."""
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return payload
    if not isinstance(existing, dict):
        return payload
    merged = {}
    for locale, fields in payload.items():
        old = existing.get(locale)
        extra = {
            name: value
            for name, value in (old.items() if isinstance(old, dict) else ())
            if name not in REQUIRED_FIELDS
        }
        merged[locale] = {**fields, **extra}
    return merged


def main():
    args = parse_args()
    keys = args.apps or list(OUTPUT_FILES)
    failed = []
    for key in keys:
        try:
            payload = fetch_public_localizations(key)
        except Exception as exc:  # one App's gap must not hide the rest
            failed.append(key)
            print(f"✗ {key}: {exc}", file=sys.stderr)
            continue
        destination = args.output_dir / OUTPUT_FILES[key]
        write_json(destination, merge_existing(destination, payload))
        print(f"✓ {key}: {len(payload)} public locales → {destination}")
    if failed:
        print(f"failed: {','.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
