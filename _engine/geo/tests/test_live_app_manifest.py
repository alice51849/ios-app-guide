from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "geo"))
sys.path.insert(0, str(ROOT / "social"))
import live_app_manifest as manifest
from videogen.registry import APPS, APPSTORE


NOW = datetime(2026, 9, 5, 6, tzinfo=timezone.utc)


class LiveManifestTests(unittest.TestCase):
    def setUp(self):
        self.apps = manifest.canonical_manifest()["apps"]
        self.document = manifest.create_manifest(self.apps, now=NOW)

    def test_versioned_roster_has_all_46_apps_including_battai(self):
        result = manifest.validate_manifest(self.document, now=NOW)
        self.assertEqual(46, len(result["apps"]))
        self.assertEqual("6802423998", result["apps"]["battai"]["app_id"])
        self.assertEqual(manifest.SCHEMA, result["schema"])
        self.assertEqual(
            set(APPSTORE) - {"zafe", "zodira"}, set(result["apps"]),
        )
        self.assertEqual(manifest.roster_digest(self.apps), result["roster_digest"])

    def test_legacy_45_array_and_v1_inventory_are_rejected(self):
        old_apps = {key: app for key, app in self.apps.items() if key != "battai"}
        for old in (
            [{"appStoreUrl": f"https://apps.apple.com/app/id{app['app_id']}"} for app in old_apps.values()],
            {"version": 1, "live_state_sha256": "a" * 64, "apps": old_apps},
        ):
            with self.subTest(kind=type(old).__name__):
                with self.assertRaisesRegex(manifest.ManifestError, "schema"):
                    manifest.validate_manifest(old, now=NOW)
        forged = deepcopy(self.document)
        forged["apps"] = old_apps
        forged["observations"].pop("battai")
        with self.assertRaisesRegex(manifest.ManifestError, "46.*45"):
            manifest.validate_manifest(forged, now=NOW)

    def test_digest_drift_and_resealed_identity_drift_are_rejected(self):
        altered = deepcopy(self.document)
        altered["apps"]["battai"]["app_id"] = "9999999999"
        with self.assertRaisesRegex(manifest.ManifestError, "digest"):
            manifest.validate_manifest(altered, now=NOW)
        altered["roster_digest"] = manifest.roster_digest(altered["apps"])
        with self.assertRaisesRegex(manifest.ManifestError, "roster drift"):
            manifest.validate_manifest(altered, now=NOW)

    def test_same_count_replacement_cannot_hide_battai(self):
        changed = deepcopy(self.document)
        changed["apps"]["replacement"] = changed["apps"].pop("battai")
        changed["observations"]["replacement"] = changed["observations"].pop("battai")
        changed["roster_digest"] = manifest.roster_digest(changed["apps"])
        with self.assertRaisesRegex(manifest.ManifestError, "battai"):
            manifest.validate_manifest(changed, now=NOW)

    def test_schema_ttl_and_timestamps_fail_closed(self):
        for key, value in (
            ("version", True), ("version", 1), ("schema", "other"),
            ("ttl_seconds", True), ("ttl_seconds", 0),
            ("ttl_seconds", manifest.MAX_TTL_SECONDS + 1),
            ("generated_at", "2026-09-05T06:00:00"),
            ("generated_at", (NOW + timedelta(seconds=1)).isoformat()),
        ):
            with self.subTest(key=key, value=value):
                changed = deepcopy(self.document)
                changed[key] = value
                with self.assertRaises(manifest.ManifestError):
                    manifest.validate_manifest(changed, now=NOW)

    def test_ttl_boundary_and_stale_rows_are_explicit(self):
        manifest.validate_manifest(
            self.document, now=NOW + timedelta(seconds=manifest.MAX_TTL_SECONDS - 1),
        )
        expired = NOW + timedelta(seconds=manifest.MAX_TTL_SECONDS)
        with self.assertRaisesRegex(manifest.ManifestError, "TTL expired"):
            manifest.validate_manifest(self.document, now=expired)
        states = manifest.app_statuses(self.document, now=expired)
        self.assertEqual(46, len(states))
        self.assertEqual({"stale"}, {row["inventory_status"] for row in states.values()})

    def test_per_app_unknown_and_stale_do_not_shrink_roster(self):
        self.document["observations"]["battai"] = {
            "status": "unknown", "checked_at": None, "reason": "Lookup unavailable",
        }
        self.document["observations"]["savetag"]["checked_at"] = (
            NOW - timedelta(seconds=manifest.MAX_TTL_SECONDS)
        ).isoformat()
        states = manifest.app_statuses(self.document, now=NOW)
        self.assertEqual(46, len(states))
        self.assertEqual("unknown", states["battai"]["inventory_status"])
        self.assertEqual("stale", states["savetag"]["inventory_status"])
        with self.assertRaisesRegex(manifest.ManifestError, "savetag"):
            manifest.validate_manifest(self.document, now=NOW)

    def test_duplicate_ids_observations_and_json_fields_are_rejected(self):
        changed = deepcopy(self.document)
        changed["apps"]["battai"]["app_id"] = changed["apps"]["savetag"]["app_id"]
        with self.assertRaisesRegex(manifest.ManifestError, "Duplicate"):
            manifest.validate_manifest(changed, now=NOW)
        changed = deepcopy(self.document)
        changed["observations"].pop("battai")
        with self.assertRaisesRegex(manifest.ManifestError, "exact roster"):
            manifest.validate_manifest(changed, now=NOW)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            text = json.dumps(self.document)
            path.write_text(text.replace('"version": 2', '"version": 2, "version": 2'), encoding="utf-8")
            with self.assertRaisesRegex(manifest.ManifestError, "Duplicate"):
                manifest.load_manifest(path, now=NOW)

    def test_refresh_preserves_missing_battai_as_unknown(self):
        observed = {app["app_id"] for key, app in self.apps.items() if key != "battai"}
        result = manifest.refresh_manifest(
            APPSTORE, APPS, now=NOW, lookup=lambda ids: observed,
        )
        self.assertEqual(46, len(result["apps"]))
        self.assertEqual("unknown", result["observations"]["battai"]["status"])
        self.assertEqual(self.document["roster_digest"], result["roster_digest"])

    def test_failed_lookup_retains_46_unknown_apps(self):
        def unavailable(ids):
            raise TimeoutError("Network down")

        result = manifest.refresh_manifest(APPSTORE, APPS, now=NOW, lookup=unavailable)
        self.assertEqual(46, len(result["apps"]))
        states = manifest.app_statuses(result, now=NOW)
        self.assertEqual({"unknown"}, {row["inventory_status"] for row in states.values()})

    def test_registered_new_apps_wait_for_explicit_multisource_adoption(self):
        observed = set(APPSTORE.values())
        result = manifest.refresh_manifest(APPSTORE, APPS, now=NOW, lookup=lambda ids: observed)
        self.assertEqual({"zafe", "zodira"}, {row["key"] for row in result["pending_adoptions"]})
        self.assertEqual(46, len(result["apps"]))
        changed = dict(APPSTORE, battai="12345")
        with self.assertRaisesRegex(manifest.ManifestError, "Registry roster drift: battai"):
            manifest.refresh_manifest(changed, APPS, now=NOW, lookup=lambda ids: observed)

    def test_fingerprint_ignores_check_time_but_binds_availability(self):
        later = NOW + timedelta(seconds=30)
        second = manifest.create_manifest(self.apps, now=later)
        self.assertEqual(
            manifest.manifest_fingerprint(self.document, now=later),
            manifest.manifest_fingerprint(second, now=later),
        )
        second["observations"]["battai"]["status"] = "unknown"
        second["observations"]["battai"]["reason"] = "Lookup gap"
        self.assertNotEqual(
            manifest.manifest_fingerprint(self.document, now=later),
            manifest.manifest_fingerprint(second, now=later),
        )

    def test_publisher_refreshes_manifest_before_any_rebuild_or_publication(self):
        import publish

        with (
            mock.patch.object(sys, "argv", ["publish.py", "--no-push"]),
            mock.patch.object(publish, "require", side_effect=RuntimeError("stop preflight")) as require,
        ):
            with self.assertRaisesRegex(RuntimeError, "stop preflight"):
                publish.main()
        require.assert_called_once()
        command = require.call_args.args[0]
        self.assertTrue(command[1].endswith("live_app_manifest.py"))
        self.assertEqual(["--refresh", "--output"], command[2:4])
        self.assertEqual(command[4], require.call_args.kwargs["env"]["GROWTH_LIVE_MANIFEST"])


if __name__ == "__main__":
    unittest.main()
