"""Immutable digest contract shared by the canary builder and measurement."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


DIGEST_SCHEMA = "lumi.google-images-canary-design-digest/v3"
CONTENT_SCHEMA = "lumi.google-images-canary-content-attestation/v1"
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


def content_attestation(
    records: list[dict[str, Any]],
) -> dict[str, object]:
    pages: list[dict[str, str]] = []
    assets: dict[str, dict[str, str]] = {}
    creative_ids: set[str] = set()
    page_urls: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Canary design record is not an object")
        creative_id = str(record.get("creative_id", ""))
        page_url = str(record.get("page_url", ""))
        page_sha256 = str(record.get("page_sha256", ""))
        asset_id = str(record.get("asset_id", ""))
        image_url = str(record.get("image_url", ""))
        source_sha256 = str(record.get("source_sha256", ""))
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
            or not image_url
            or SHA256_RE.fullmatch(source_sha256) is None
        ):
            raise ValueError("Canary asset attestation is invalid")
        asset = {
            "asset_id": asset_id,
            "url": image_url,
            "sha256": source_sha256,
        }
        previous = assets.get(image_url)
        if previous is not None and previous != asset:
            raise ValueError("Canary asset attestation conflicts")
        assets[image_url] = asset

    page_rows = sorted(pages, key=lambda row: row["creative_id"])
    asset_rows = sorted(assets.values(), key=lambda row: row["url"])
    return {
        "schema": CONTENT_SCHEMA,
        "page_count": len(page_rows),
        "page_manifest_digest": digest_json(page_rows),
        "asset_count": len(asset_rows),
        "asset_manifest_digest": digest_json(asset_rows),
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
