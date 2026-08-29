#!/usr/bin/env python3
"""Generate a fresh, fail-closed cloud-health bundle using GET-only evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloud_health.collectors import LiveCollector, load_config  # noqa: E402
from cloud_health.core import (  # noqa: E402
    BLOCKED,
    EXPECTED_COUNT,
    EXPECTED_DIGEST,
    build_artifact,
    build_snapshot_from_v3,
    digest_value,
    iso_z,
    write_bundle,
)


def blocked_snapshot(config: dict, error: Exception) -> dict:
    observed = iso_z(datetime.now(timezone.utc))
    keys = sorted(config["live_dates"])
    message = str(error)[:500]
    source_names = [
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
    ]
    sources = [
        {
            "source": name,
            "status": BLOCKED,
            "observed_at": observed,
            "run_id": None,
            "sha256": digest_value({"source": name, "error": message, "at": observed}),
            "error": message,
        }
        for name in source_names
    ]
    return {
        "observed_at": observed,
        "source_evidence": sources,
        "canonical": {
            "keys": keys,
            "threads_digest": None,
            "guide_digest": None,
            "public_digest": None,
            "asc_digest": None,
            "missing_live_apps": keys,
            "unknown_live_apps": [],
        },
        "schedule": {
            "all_outreach": {"collection_errors": [message]},
            "social": {"collection_errors": [message]},
            "high_frequency_social": {"collection_errors": [message]},
        },
        "digest_gate": {"fresh": False, "failures": [{"error": message}]},
        "pages": {
            "pages_get_total": 0,
            "pages_get_ok": 0,
            "guide_get_total": EXPECTED_COUNT,
            "guide_get_ok": 0,
            "app_store_get_total": EXPECTED_COUNT,
            "app_store_get_ok": 0,
            "recent_deployments": 0,
            "recent_deployment_successes": 0,
        },
        "owned_surfaces": {
            "guide_count": 0,
            "publisher_count": 0,
            "profile_count": 0,
            "publisher_missing": keys,
            "profile_missing": keys,
        },
        "social_channels": [],
        "crawler": {
            "sitemap_get_ok": False,
            "robots_get_ok": False,
            "guide_apps_in_sitemap": 0,
            "standard_reader_verified": False,
            "search_index_presence": False,
        },
        "click": {"known": False, "apps_with_click": [], "error": message},
        "asc": {
            "fresh": False,
            "aggregate_semantics": "exact",
            "analytics_privacy_suppression_applied": False,
            "live_roster_count": 0,
            "windows_complete": False,
            "error": message,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("config.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--golden-v3",
        type=Path,
        help="Offline deterministic projection of the approved v3 fixture.",
    )
    args = parser.parse_args(argv)
    config = load_config(args.config)
    try:
        if args.golden_v3:
            raw = args.golden_v3.read_bytes()
            if __import__("hashlib").sha256(raw).hexdigest() != config[
                "approved_v3_sha256"
            ]:
                raise ValueError("v3 fixture digest does not match approval token")
            snapshot = build_snapshot_from_v3(json.loads(raw))
        else:
            snapshot = LiveCollector(config).collect()
        artifact = build_artifact(snapshot)
    except Exception as error:
        artifact = build_artifact(blocked_snapshot(config, error))
    digests = write_bundle(args.output_dir, artifact)
    print(
        json.dumps(
            {
                "status": artifact["overall_status"],
                "generation_id": artifact["generation_id"],
                "json_sha256": digests["json_sha256"],
                "output_dir": str(args.output_dir),
                "network_methods": ["GET"],
                "model_used": False,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
