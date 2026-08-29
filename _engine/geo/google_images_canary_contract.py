"""Immutable design contracts shared by the canary builder and measurement."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


DIGEST_SCHEMA = "lumi.google-images-canary-design-digest/v4"
CONTENT_SCHEMA = "lumi.google-images-canary-content-attestation/v2"
ASSIGNMENT_METHOD = (
    "sha256-ranked-stratified-complete-randomization/v1"
)
SHA256_RE = re.compile(r"[a-f0-9]{64}")


def canonical_value(value: object) -> object:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def digest_json(value: object) -> str:
    payload = json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _rank(
    experiment_spec: dict[str, Any],
    purpose: str,
    *parts: object,
) -> str:
    material = "\0".join(
        (
            str(experiment_spec.get("experiment_id", "")),
            str(experiment_spec.get("assignment_salt", "")),
            purpose,
            *(str(part) for part in parts),
        )
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def stratified_assignment(
    experiment_spec: dict[str, Any],
) -> dict[str, dict[str, object]]:
    """Recompute the preregistered 19/19 assignment from frozen units."""
    randomization = experiment_spec.get("randomization")
    units = experiment_spec.get("units")
    if (
        not isinstance(randomization, dict)
        or randomization.get("method") != ASSIGNMENT_METHOD
        or randomization.get("stratum_field") != "app"
        or randomization.get("analysis") != "stratified_randomization_inference"
        or randomization.get("pairing_claim") != "none"
        or not isinstance(units, list)
        or not units
    ):
        raise ValueError("Canary randomization contract is invalid")
    try:
        treatment_target = int(randomization["target_treatment"])
        holdout_target = int(randomization["target_holdout"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Canary randomization targets are invalid") from error
    if (
        treatment_target <= 0
        or holdout_target <= 0
        or treatment_target + holdout_target != len(units)
    ):
        raise ValueError("Canary randomization targets do not cover all units")

    by_stratum: dict[str, list[dict[str, Any]]] = {}
    unit_ids: set[str] = set()
    asset_ids: set[str] = set()
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("Canary randomization unit is not an object")
        unit_id = str(unit.get("id", ""))
        stratum = str(unit.get("app", ""))
        asset_id = str(unit.get("asset", ""))
        if (
            not unit_id
            or unit_id in unit_ids
            or not stratum
            or not asset_id
            or asset_id in asset_ids
        ):
            raise ValueError("Canary randomization units are not one-to-one")
        unit_ids.add(unit_id)
        asset_ids.add(asset_id)
        by_stratum.setdefault(stratum, []).append(unit)

    base_treatment = sum(len(rows) // 2 for rows in by_stratum.values())
    odd_strata = [
        stratum
        for stratum, rows in by_stratum.items()
        if len(rows) % 2
    ]
    extra_count = treatment_target - base_treatment
    if extra_count < 0 or extra_count > len(odd_strata):
        raise ValueError("Canary odd-stratum balance is impossible")
    extra_treatment = set(
        sorted(
            odd_strata,
            key=lambda stratum: (
                _rank(experiment_spec, "odd-stratum", stratum),
                stratum,
            ),
        )[:extra_count]
    )

    plan: dict[str, dict[str, object]] = {}
    for stratum, rows in sorted(by_stratum.items()):
        ordered = sorted(
            rows,
            key=lambda unit: (
                _rank(
                    experiment_spec,
                    "unit",
                    stratum,
                    unit["id"],
                    unit["asset"],
                ),
                str(unit["id"]),
            ),
        )
        treatment_slots = len(ordered) // 2 + int(
            stratum in extra_treatment
        )
        for index, unit in enumerate(ordered):
            unit_id = str(unit["id"])
            plan[unit_id] = {
                "arm": (
                    "treatment"
                    if index < treatment_slots
                    else "holdout"
                ),
                "assignment_rank": _rank(
                    experiment_spec,
                    "unit",
                    stratum,
                    unit_id,
                    unit["asset"],
                ),
                "stratum": stratum,
                "stratum_size": len(ordered),
                "stratum_treatment_slots": treatment_slots,
            }
    if (
        sum(row["arm"] == "treatment" for row in plan.values())
        != treatment_target
        or sum(row["arm"] == "holdout" for row in plan.values())
        != holdout_target
    ):
        raise ValueError("Canary stratified assignment is not balanced")
    return plan


def content_attestation(
    records: list[dict[str, Any]],
) -> dict[str, object]:
    pages: list[dict[str, str]] = []
    assets: list[dict[str, str]] = []
    ownership: list[dict[str, str]] = []
    creative_ids: set[str] = set()
    page_urls: set[str] = set()
    asset_ids: set[str] = set()
    image_urls: set[str] = set()
    source_paths: set[str] = set()
    source_digests: set[str] = set()
    pixel_digests: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Canary design record is not an object")
        creative_id = str(record.get("creative_id", ""))
        page_url = str(record.get("page_url", ""))
        page_sha256 = str(record.get("page_sha256", ""))
        asset_id = str(record.get("asset_id", ""))
        image_url = str(record.get("image_url", ""))
        source_path = str(record.get("source_path", ""))
        source_sha256 = str(record.get("source_sha256", ""))
        pixel_sha256 = str(record.get("pixel_sha256", ""))
        arm = str(record.get("arm", ""))
        if (
            not creative_id
            or creative_id in creative_ids
            or not page_url
            or page_url in page_urls
            or SHA256_RE.fullmatch(page_sha256) is None
        ):
            raise ValueError("Canary page attestation is invalid")
        creative_ids.add(creative_id)
        page_urls.add(page_url)
        pages.append(
            {
                "creative_id": creative_id,
                "url": page_url,
                "sha256": page_sha256,
            }
        )
        if (
            not asset_id
            or asset_id in asset_ids
            or not image_url
            or image_url in image_urls
            or not source_path
            or source_path in source_paths
            or SHA256_RE.fullmatch(source_sha256) is None
            or source_sha256 in source_digests
            or SHA256_RE.fullmatch(pixel_sha256) is None
            or pixel_sha256 in pixel_digests
            or arm not in {"treatment", "holdout"}
        ):
            raise ValueError(
                "Canary asset ownership is shared, duplicated, or invalid"
            )
        asset_ids.add(asset_id)
        image_urls.add(image_url)
        source_paths.add(source_path)
        source_digests.add(source_sha256)
        pixel_digests.add(pixel_sha256)
        assets.append(
            {
                "asset_id": asset_id,
                "url": image_url,
                "sha256": source_sha256,
                "pixel_sha256": pixel_sha256,
            }
        )
        ownership.append(
            {
                "creative_id": creative_id,
                "page_url": page_url,
                "arm": arm,
                "asset_id": asset_id,
                "image_url": image_url,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "pixel_sha256": pixel_sha256,
            }
        )

    page_rows = sorted(pages, key=lambda row: row["creative_id"])
    asset_rows = sorted(assets, key=lambda row: row["url"])
    ownership_rows = sorted(
        ownership,
        key=lambda row: row["creative_id"],
    )
    if len(page_rows) != len(asset_rows):
        raise ValueError("Canary pages and assets are not one-to-one")
    return {
        "schema": CONTENT_SCHEMA,
        "page_count": len(page_rows),
        "page_manifest_digest": digest_json(page_rows),
        "asset_count": len(asset_rows),
        "asset_manifest_digest": digest_json(asset_rows),
        "ownership_manifest_digest": digest_json(ownership_rows),
    }


def design_material(
    experiment_spec: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, object]:
    assignments = sorted(
        canonical_value(records),
        key=lambda row: str(row["creative_id"]),
    )
    return {
        "schema": DIGEST_SCHEMA,
        "experiment_spec": canonical_value(experiment_spec),
        "assignments": assignments,
        "content_attestation": content_attestation(assignments),
    }


def design_digest(
    experiment_spec: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    return digest_json(design_material(experiment_spec, records))
