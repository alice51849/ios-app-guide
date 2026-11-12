#!/usr/bin/env python3
"""Finder purchase models: neutral is listed honestly; unknown skips one app only."""

from __future__ import annotations

from datetime import datetime, timezone
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

from app_store_storefronts import PROVIDER_TOKEN_ENV
import portfolio_app_finder as finder


PAID, UNLOCK = "lumimathpro", "aibriefpack"


class FinderPurchaseModelTests(unittest.TestCase):
    def setUp(self):
        finder.SKIPPED_APPS.clear()
        self.addCleanup(finder.SKIPPED_APPS.clear)
        self.pages = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.pages))

    def records(self, keys):
        return {
            r["key"]: r
            for r in finder.catalog_records(
                set(keys), self.pages, allow_unknown_summaries=True
            )
        }

    def test_existing_models_keep_their_labels_and_one_time_option(self):
        records = self.records({PAID, UNLOCK})
        for key in (PAID, UNLOCK):
            model = finder.APPS[key]["purchase_model"]
            with self.subTest(key=key):
                self.assertIn(model, {"paid_upfront", "free_with_lifetime_unlock"})
                self.assertIs(True, records[key]["one_time_option"])
                self.assertEqual(
                    finder.UI["en"]["purchase_labels"][model],
                    records[key]["purchase_labels"]["en"],
                )
        self.assertEqual({}, finder.SKIPPED_APPS)

    def test_neutral_subscription_app_uses_check_listing_copy(self):
        with mock.patch.dict(finder.APPS[PAID], {"purchase_model": "neutral"}):
            record = self.records({PAID})[PAID]
        self.assertEqual("neutral", record["purchase_model"])
        self.assertIs(False, record["one_time_option"])
        self.assertEqual("Check current listing", record["purchase_labels"]["en"])
        self.assertEqual("查看目前上架頁", record["purchase_labels"]["zh-Hant"])
        for locale in ("ja", "de-DE", "ar-SA"):
            label = finder.UI[locale]["purchase_labels"]["neutral"]
            self.assertTrue(label.strip())
            self.assertNotEqual(
                finder.UI[locale]["purchase_labels"]["free_with_lifetime_unlock"], label
            )
        self.assertEqual({}, finder.SKIPPED_APPS)

    def test_unknown_model_skips_only_that_app_and_reports_an_error(self):
        with mock.patch.dict(finder.APPS[PAID], {"purchase_model": "mystery"}), \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            records = self.records({PAID, UNLOCK})
        self.assertEqual({UNLOCK}, set(records))
        self.assertIn(f"::error::Portfolio finder skipped {PAID}", err.getvalue())
        self.assertIn("mystery", finder.SKIPPED_APPS[PAID])

    def test_unknown_only_app_is_still_an_explicit_failure(self):
        with mock.patch.dict(finder.APPS[PAID], {"purchase_model": "mystery"}), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaisesRegex(ValueError, "no app with a known purchase model"):
                self.records({PAID})

    def test_dataset_payload_omits_the_skipped_app_without_failing(self):
        roster = {
            key: {"name": finder.APPS[key]["name"], "track_id": str(finder.APPSTORE[key])}
            for key in (PAID, UNLOCK)
        }
        now = datetime(2026, 11, 12, tzinfo=timezone.utc)
        with mock.patch.dict(finder.APPS[PAID], {"purchase_model": "mystery"}), \
                mock.patch("sys.stderr", new_callable=io.StringIO), \
                mock.patch.dict("os.environ", {PROVIDER_TOKEN_ENV: "118326163"}):
            document = finder.dataset_payload(
                list(self.records(roster).values()), roster=roster, now=now,
                pages=self.pages,
            )
        self.assertEqual([UNLOCK], [app["key"] for app in document["apps"]])
        self.assertEqual(1, document["record_count"])
        schema = __import__("json").loads(finder.dataset_schema())
        self.assertEqual(
            len(finder.contract.live_roster()) - 1,
            schema["properties"]["record_count"]["const"],
        )


if __name__ == "__main__":
    unittest.main()
