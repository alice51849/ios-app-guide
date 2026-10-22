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
        self.app_count = len(self.document["apps"])
        self.stack.enter_context(mock.patch.object(scorecard, "APPS", self.document["apps"]))
        self.stack.enter_context(mock.patch.object(scorecard, "_social_posts", return_value=[]))
        self.stack.enter_context(mock.patch.object(scorecard, "_exists", return_value=False))
        self.stack.enter_context(mock.patch.object(scorecard, "PAGES", str(self.directory / "pages")))
        self.stack.enter_context(mock.patch.object(scorecard, "REPORTS", str(self.directory)))
        self.stack.enter_context(mock.patch.object(scorecard, "JSON_OUT", str(self.directory / "report.json")))
        self.stack.enter_context(mock.patch.object(scorecard, "MD_OUT", str(self.directory / "report.md")))

    def test_zero_coverage_keeps_the_complete_live_roster(self):
        rows = scorecard.build_rows(manifest=self.document, now=NOW)
        self.assertCountEqual(self.document["apps"], [row["key"] for row in rows])
        self.assertIn("zipbox", {row["key"] for row in rows})
        self.assertTrue(all(row["coverage_score"] == 0 for row in rows))
        report = scorecard.write_reports(rows, self.document)
        self.assertEqual(self.app_count, report["live_app_count"])
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
        self.assertEqual(self.app_count, report["live_app_count"])
        self.assertEqual(self.app_count, report["public_apps"])
        self.assertEqual(self.app_count - 2, report["verified_public_apps"])
        self.assertCountEqual(self.document["apps"], [row["key"] for row in rows])
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
        self.assertCountEqual(self.document["apps"], [row["key"] for row in rows])

    def test_expired_availability_never_expires_the_complete_public_roster(self):
        rows = scorecard.build_rows(manifest=self.document, now=NOW + timedelta(days=1))
        report = scorecard.write_reports(rows, self.document)
        self.assertEqual(self.app_count, report["live_app_count"])
        self.assertEqual(self.app_count, report["public_apps"])
        self.assertEqual(0, report["verified_public_apps"])
        self.assertCountEqual(self.document["apps"], report["inventory_gaps"])
        self.assertCountEqual(self.document["apps"], [row["key"] for row in rows])
        self.assertTrue(all(row["inventory_status"] == "stale" for row in rows))

    def test_legacy_array_or_incomplete_manifest_is_rejected(self):
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
        self.assertEqual(self.app_count, report["live_app_count"])
        self.assertCountEqual(self.document["apps"], [row["key"] for row in report["rows"]])
        self.assertEqual(["battai"], report["inventory_gaps"])

    def test_portfolio_posts_accept_attributed_app_store_urls(self):
        pages = Path(scorecard.PAGES)
        (pages / ".github" / "scripts").mkdir(parents=True)
        (pages / ".github" / "workflows").mkdir(parents=True)
        (pages / ".github" / "scripts" / "portfolio_daily.py").write_text("")
        (pages / ".github" / "workflows" / "portfolio-daily.yml").write_text("")
        attributed_id = str(scorecard.APPSTORE["zipbox"])
        bare_id = str(scorecard.APPSTORE["battai"])
        (pages / "apps.json").write_text(
            json.dumps(
                [
                    {
                        "appStoreUrl": (
                            f"https://apps.apple.com/app/id{attributed_id}"
                            "?pt=118326163&ct=geo_pick&mt=8"
                        )
                    },
                    {
                        "appStoreUrl": (
                            f"https://apps.apple.com/app/id{bare_id}"
                        )
                    },
                    {
                        "appStoreUrl": (
                            "https://apps.apple.com.evil.invalid/app/"
                            f"id{scorecard.APPSTORE['savetag']}"
                        )
                    },
                    {
                        "appStoreUrl": (
                            "https://apps.apple.com/app/"
                            f"id{scorecard.APPSTORE['moneytag']}?redirect=1"
                        )
                    },
                ]
            ),
            encoding="utf-8",
        )

        self.assertEqual(
            [
                {
                    "app": bare_id,
                    "lang": "zh-Hant",
                    "source": "portfolio-daily",
                },
                {
                    "app": attributed_id,
                    "lang": "zh-Hant",
                    "source": "portfolio-daily",
                },
            ],
            scorecard._portfolio_social_posts(
                {"zipbox", "battai", "savetag", "moneytag"}
            ),
        )


class NewAppOutreachInputsTests(unittest.TestCase):
    """A newly published App must have the two inputs that cannot self-heal.

    ``--require-complete`` fails the daily line when any public App scores
    below 100%.  Two components of that score come from reviewed inputs that
    no generator can invent: competitor rows (which mint the alternatives
    pages) and the multi-language social post pool.  ledmovingtext shipped on
    2026-09-18 without either and stalled Daily GEO eight hours later, so this
    test fails in seconds instead.
    """

    def test_every_roster_app_has_reviewed_competitor_rows(self):
        import aeo_pages

        evidence = json.loads(Path(aeo_pages.SOV).read_text(encoding="utf-8"))
        covered = {
            str(row["key"]) for row in evidence["results"]
        } | set(aeo_pages.CURATED_FALLBACK)
        roster = set(manifest.canonical_manifest()["apps"])
        self.assertEqual(set(), roster - covered)
        for key in roster:
            row = aeo_pages.CURATED_FALLBACK.get(key)
            if row is None:
                continue
            with self.subTest(key=key):
                # min(alt_count / 2, 1.0) is the scored component, so one
                # competitor page plus the hub is the floor that still scores.
                self.assertGreaterEqual(len(row["top_competitors"]), 1)
                self.assertTrue(row["gap_queries"])

    def test_every_roster_app_has_social_posts_in_three_languages(self):
        from videogen.registry import APPSTORE

        pool = Path(scorecard.PAGES) / ".github" / "scripts" / "telegram_posts.json"
        if not pool.is_file():
            self.skipTest("Telegram post pool is only present in the Guide tree")
        posts = json.loads(pool.read_text(encoding="utf-8"))
        languages = {}
        for post in posts:
            languages.setdefault(str(post.get("app")), set()).add(post.get("lang"))
        for key in sorted(manifest.canonical_manifest()["apps"]):
            app_id = str(APPSTORE.get(key) or "")
            with self.subTest(key=key):
                # portfolio-daily contributes zh-Hant on its own, so the pool
                # has to carry at least two more to reach the scored three.
                self.assertGreaterEqual(len(languages.get(app_id, set())), 2)


if __name__ == "__main__":
    unittest.main()
