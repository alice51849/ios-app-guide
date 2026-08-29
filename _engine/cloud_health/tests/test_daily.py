from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import unittest
from urllib.error import URLError

from cloud_health.collectors import EvidenceError, GetClient, RawResponse, load_config
from cloud_health.core import (
    BLOCKED,
    EXPECTED_DIGEST,
    PASS,
    ContractError,
    build_artifact,
    build_snapshot_from_v3,
    validate_artifact,
    validate_v3_golden,
    write_bundle,
)
from cloud_health.run import blocked_snapshot, main


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "cloud_health"
FIXTURE = PACKAGE / "tests" / "fixtures" / "cloud-health-audit.v3.json"
CONFIG = PACKAGE / "config.json"
V3_SHA = "339f48d201b11698c366836899f75d9bca125246abd80f1798be3dd458b7b03d"


class CloudHealthDailyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v3_bytes = FIXTURE.read_bytes()
        self.v3 = json.loads(self.v3_bytes)
        self.scratch = PACKAGE / "tests" / f".scratch-{os.getpid()}"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_approved_v3_is_exact_golden(self) -> None:
        self.assertEqual(hashlib.sha256(self.v3_bytes).hexdigest(), V3_SHA)
        validate_v3_golden(self.v3)

    def test_v3_projection_preserves_line_statuses_and_windows(self) -> None:
        artifact = build_artifact(build_snapshot_from_v3(self.v3))
        validate_artifact(artifact)
        expected = {
            row["line"]: row["status"] for row in self.v3["line_verdicts"]
        }
        actual = {
            row["line"]: row["status"] for row in artifact["line_verdicts"]
        }
        self.assertEqual(actual, expected)
        floor = next(
            row for row in artifact["line_verdicts"]
            if row["line"] == "asc_per_app_download_floor"
        )["evidence"]["windows"]
        self.assertEqual(floor["latest_daily"]["downloads"]["apps_ge_1"], 22)
        self.assertEqual(floor["latest_daily"]["iap"]["apps_ge_1"], 4)
        self.assertEqual(floor["rolling_7d"]["downloads"]["apps_ge_1"], 34)
        self.assertEqual(floor["rolling_7d"]["iap"]["apps_ge_1"], 11)
        self.assertEqual(floor["month_to_date"]["downloads"]["apps_ge_1"], 41)
        self.assertEqual(floor["month_to_date"]["iap"]["apps_ge_1"], 23)
        self.assertEqual(
            floor["month_to_date"]["downloads"]["unknown_no_row"],
            ["aim990plus"],
        )

    def test_v3_mutations_fail_closed(self) -> None:
        def floor(value):
            return next(
                row for row in value["line_verdicts"]
                if row["line"] == "asc_per_app_download_floor"
            )["evidence"]["windows"]

        def social(value):
            return next(
                row for row in value["line_verdicts"]
                if row["line"] == "social_public_exposure"
            )["evidence"]

        def crawler(value):
            return next(
                row for row in value["line_verdicts"]
                if row["line"] == "crawler_and_index"
            )["evidence"]

        def schedule(value):
            return next(
                row for row in value["line_verdicts"]
                if row["line"] == "github_schedule_delivery"
            )["evidence"]

        mutations = []
        value = copy.deepcopy(self.v3)
        floor(value)["latest_daily"]["downloads"]["apps_ge_1"] = 34
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["latest_daily"]["iap"]["apps_ge_1"] = 11
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["rolling_7d"]["downloads"]["start"] = "2026-08-28"
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["rolling_7d"]["iap"]["apps_ge_1"] = 4
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["month_to_date"]["downloads"]["apps_ge_1"] = 23
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["month_to_date"]["iap"]["apps_ge_1"] = 4
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["month_to_date"]["downloads"]["unknown_no_row"] = []
        floor(value)["month_to_date"]["downloads"]["unknown"] = 0
        floor(value)["month_to_date"]["downloads"]["known"] = 46
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        floor(value)["rolling_7d"]["downloads"]["metric"] = "daily_downloads"
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        next(row for row in social(value) if row["channel"] == "Nostr")[
            "counts_as_public_exposure"
        ] = True
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        next(row for row in social(value) if row["channel"] == "Nostr").pop(
            "public_get_sample"
        )
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        crawler(value)["standard_site"][
            "app_count_and_document_count_are_same_unit"
        ] = True
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        crawler(value)["standard_site"][
            "public_index_document_count_minus_state_derived_app_count"
        ] = 13
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        schedule(value)["all_outreach"][
            "nominal_cron_delivery_ratio_counts_as_capacity"
        ] = True
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        value["canonical_roster"]["expected_digest"] = "0" * 64
        mutations.append(value)
        value = copy.deepcopy(self.v3)
        value["canonical_roster"]["keys"][0] = "not-canonical"
        mutations.append(value)

        self.assertEqual(len(mutations), 15)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ContractError):
                validate_v3_golden(mutation)

    def test_rate_limit_retries_then_succeeds(self) -> None:
        responses = [
            RawResponse(429, b"rate", {"retry-after": "0"}, "https://example.com/x"),
            RawResponse(200, b'{"ok":true}', {}, "https://example.com/x"),
        ]
        calls = []

        def transport(url, headers, timeout):
            calls.append((url, headers, timeout))
            return responses.pop(0)

        client = GetClient(transport=transport, sleep=lambda _: None, attempts=3)
        payload, receipt = client.json("https://example.com/x")
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(receipt["method"], "GET")
        self.assertEqual(len(calls), 2)

    def test_rate_limit_exhaustion_is_blocking(self) -> None:
        def transport(url, headers, timeout):
            return RawResponse(
                429, b"rate", {"retry-after": "0"}, "https://example.com/x"
            )

        client = GetClient(transport=transport, sleep=lambda _: None, attempts=2)
        with self.assertRaises(EvidenceError):
            client.json("https://example.com/x")

    def test_signed_redirect_values_are_never_emitted(self) -> None:
        safe = GetClient._safe_url(
            "https://blob.example/file.zip?sig=secret&token=secret&public=ok"
        )
        self.assertNotIn("secret", safe)
        self.assertIn("sig=[REDACTED]", safe)
        self.assertIn("token=[REDACTED]", safe)
        self.assertIn("public=ok", safe)

    def test_network_failure_becomes_fresh_blocked_bundle(self) -> None:
        config = load_config(CONFIG)
        snapshot = blocked_snapshot(config, URLError("offline"))
        artifact = build_artifact(snapshot)
        self.assertEqual(artifact["overall_status"], BLOCKED)
        self.assertTrue(
            all(row["status"] == BLOCKED for row in artifact["source_evidence"])
        )
        self.assertFalse(
            artifact["constraints_observed"]["old_green_carried_forward"]
        )
        write_bundle(self.scratch, artifact)
        stored = json.loads((self.scratch / "cloud-health.json").read_text())
        self.assertEqual(stored["overall_status"], BLOCKED)
        self.assertIn("offline", json.dumps(stored))

    def test_partial_evidence_blocks_only_fresh_dependencies(self) -> None:
        snapshot = build_snapshot_from_v3(self.v3)
        source = next(
            row for row in snapshot["source_evidence"]
            if row["source"] == "public_get"
        )
        source["status"] = BLOCKED
        source["error"] = "partial evidence"
        artifact = build_artifact(snapshot)
        lines = {row["line"]: row["status"] for row in artifact["line_verdicts"]}
        self.assertEqual(lines["canonical_exact46"], PASS)
        self.assertEqual(lines["pages_deployment_and_http_delivery"], BLOCKED)
        self.assertEqual(artifact["overall_status"], BLOCKED)

    def test_source_evidence_always_has_timestamp_run_and_digest(self) -> None:
        artifact = build_artifact(build_snapshot_from_v3(self.v3))
        for row in artifact["source_evidence"]:
            self.assertIn("observed_at", row)
            self.assertIn("run_id", row)
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")

    def test_atomic_bundle_digest_matches_and_replaces_old_files(self) -> None:
        for name in [
            "cloud-health.json",
            "cloud-health.report.md",
            "cloud-health.schema.json",
            "cloud-health.sha256",
        ]:
            (self.scratch / name).write_text("STALE-GREEN")
        artifact = build_artifact(build_snapshot_from_v3(self.v3))
        write_bundle(self.scratch, artifact)
        manifest = {}
        for line in (self.scratch / "cloud-health.sha256").read_text().splitlines():
            digest, name = line.split("  ", 1)
            manifest[name] = digest
        self.assertEqual(
            set(manifest),
            {
                "cloud-health.json",
                "cloud-health.report.md",
                "cloud-health.schema.json",
            },
        )
        for name, digest in manifest.items():
            body = (self.scratch / name).read_bytes()
            self.assertNotIn(b"STALE-GREEN", body)
            self.assertEqual(hashlib.sha256(body).hexdigest(), digest)

    def test_offline_cli_writes_complete_bundle(self) -> None:
        result = main(
            [
                "--config",
                str(CONFIG),
                "--golden-v3",
                str(FIXTURE),
                "--output-dir",
                str(self.scratch),
            ]
        )
        self.assertEqual(result, 0)
        for name in [
            "cloud-health.json",
            "cloud-health.report.md",
            "cloud-health.schema.json",
            "cloud-health.sha256",
        ]:
            self.assertTrue((self.scratch / name).is_file())

    def test_config_recomputes_exact46_digest(self) -> None:
        config = load_config(CONFIG)
        keys = sorted(config["live_dates"])
        digest = hashlib.sha256(
            json.dumps(keys, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(len(keys), 46)
        self.assertEqual(digest, EXPECTED_DIGEST)

    def test_no_runtime_network_mutation_verbs(self) -> None:
        source = (PACKAGE / "collectors.py").read_text()
        self.assertIn('Request(url, method="GET"', source)
        for forbidden in [
            'method="POST"',
            'method="PATCH"',
            'method="DELETE"',
            "workflow_dispatch(",
            "rerun(",
        ]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
