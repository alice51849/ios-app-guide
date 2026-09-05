from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "geo"))
import live_app_manifest as manifest
import outreach_scorecard as scorecard


NOW = datetime(2026, 9, 5, 6, tzinfo=timezone.utc)


class OutreachScorecardTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.document = manifest.create_manifest(manifest.canonical_manifest()["apps"], now=NOW)
        self.stack.enter_context(mock.patch.object(scorecard, "APPS", self.document["apps"]))
        self.stack.enter_context(mock.patch.object(scorecard, "_social_posts", return_value=[]))
        self.stack.enter_context(mock.patch.object(scorecard, "_exists", return_value=False))
        self.stack.enter_context(mock.patch.object(scorecard, "PAGES", str(self.directory / "pages")))
        self.stack.enter_context(mock.patch.object(scorecard, "REPORTS", str(self.directory)))
        self.stack.enter_context(mock.patch.object(scorecard, "JSON_OUT", str(self.directory / "report.json")))
        self.stack.enter_context(mock.patch.object(scorecard, "MD_OUT", str(self.directory / "report.md")))

    def test_zero_coverage_keeps_all_46_apps_and_battai(self):
        rows = scorecard.build_rows(manifest=self.document, now=NOW)
        self.assertEqual(46, len(rows))
        self.assertEqual(set(self.document["apps"]), {row["key"] for row in rows})
        self.assertTrue(all(row["coverage_score"] == 0 for row in rows))
        report = scorecard.write_reports(rows, self.document)
        self.assertEqual(46, report["live_app_count"])
        self.assertTrue(report["inventory_complete"])
        text = (self.directory / "report.md").read_text(encoding="utf-8")
        for app in self.document["apps"].values():
            self.assertIn(f"| {app['name']} | live |", text)

    def test_unknown_and_stale_apps_are_individual_rows_not_excluded(self):
        self.document["observations"]["battai"] = {
            "status": "unknown", "checked_at": None, "reason": "Lookup failed",
        }
        self.document["observations"]["savetag"]["checked_at"] = (NOW - timedelta(days=1)).isoformat()
        rows = scorecard.build_rows(manifest=self.document, now=NOW)
        report = scorecard.write_reports(rows, self.document)
        self.assertEqual(46, report["live_app_count"])
        self.assertEqual(46, report["public_apps"])
        self.assertEqual(44, report["verified_public_apps"])
        self.assertEqual({"battai", "savetag"}, set(report["inventory_gaps"]))
        self.assertTrue(report["inventory_complete"])
        self.assertFalse(report["availability_complete"])
        text = (self.directory / "report.md").read_text(encoding="utf-8")
        self.assertIn("| BattAI | unknown |", text)
        self.assertIn("| SaveTag | stale |", text)
        self.assertNotIn("Excluded until", text)

    def test_missing_public_key_still_has_a_roster_row(self):
        keys = set(self.document["apps"]) - {"battai"}
        rows = scorecard.build_rows(keys, manifest=self.document, now=NOW)
        battai = next(row for row in rows if row["key"] == "battai")
        self.assertEqual("unknown", battai["inventory_status"])
        self.assertFalse(battai["public"])
        self.assertEqual("", battai["appstore"])
        self.assertEqual(46, len(rows))

    def test_expired_availability_never_expires_the_46_app_public_roster(self):
        rows = scorecard.build_rows(manifest=self.document, now=NOW + timedelta(days=1))
        report = scorecard.write_reports(rows, self.document)
        self.assertEqual(46, report["live_app_count"])
        self.assertEqual(46, report["public_apps"])
        self.assertEqual(0, report["verified_public_apps"])
        self.assertEqual(46, len(report["inventory_gaps"]))
        self.assertTrue(all(row["inventory_status"] == "stale" for row in rows))

    def test_old_45_array_or_forged_45_manifest_is_rejected(self):
        path = self.directory / "baseline.json"
        forged = deepcopy(self.document)
        forged["apps"].pop("battai")
        forged["observations"].pop("battai")
        for document in ([{}] * 45, forged):
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.subTest(kind=type(document).__name__):
                with self.assertRaises(RuntimeError):
                    scorecard.validate_public_inventory(None, path, now=NOW)

    def test_same_count_digest_drift_and_missing_public_key_fail_gate(self):
        path = self.directory / "manifest.json"
        path.write_text(json.dumps(self.document), encoding="utf-8")
        scorecard.validate_public_inventory(set(self.document["apps"]), path, now=NOW)
        with self.assertRaisesRegex(RuntimeError, "unexpectedly shrank"):
            scorecard.validate_public_inventory(set(self.document["apps"]) - {"battai"}, path, now=NOW)
        changed = deepcopy(self.document)
        changed["apps"]["battai"]["name"] = "Wrong App"
        changed["roster_digest"] = manifest.roster_digest(changed["apps"])
        path.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "roster drift"):
            scorecard.validate_public_inventory(None, path, now=NOW)

    def test_cli_always_validates_and_never_looks_up_apps_implicitly(self):
        path = self.directory / "manifest.json"
        path.write_text(json.dumps([{}] * 45), encoding="utf-8")
        with (
            mock.patch("urllib.request.urlopen", side_effect=AssertionError("No implicit network")),
            redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(1, scorecard.main(["--manifest", str(path)]))
            fresh = manifest.create_manifest(self.document["apps"])
            path.write_text(json.dumps(fresh), encoding="utf-8")
            self.assertEqual(0, scorecard.main(["--manifest", str(path)]))
            fresh["observations"]["battai"] = {
                "status": "unknown", "checked_at": None, "reason": "Lookup failed",
            }
            path.write_text(json.dumps(fresh), encoding="utf-8")
            self.assertEqual(0, scorecard.main(["--manifest", str(path)]))
        report = json.loads((self.directory / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(46, report["live_app_count"])
        self.assertEqual(["battai"], report["inventory_gaps"])


if __name__ == "__main__":
    unittest.main()
