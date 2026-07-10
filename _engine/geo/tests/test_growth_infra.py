#!/usr/bin/env python3
"""Regression tests for App Store availability and AI outreach generation."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
if GEO not in sys.path:
    sys.path.insert(0, GEO)

import aeo_answers
import aeo_pages
import answer_deep
import appstore_live
import gen_app_catalog
import gen_hubs
import gen_llms
import outreach_scorecard


class AppStoreAvailabilityTests(unittest.TestCase):
    def test_new_unlisted_apps_are_omitted_and_live_apps_are_cached(self):
        with tempfile.TemporaryDirectory() as pages:
            with mock.patch.object(
                appstore_live, "fetch_live_ids", return_value={"1"}
            ):
                keys = appstore_live.live_app_keys(
                    {"live": "1", "pending": "2"}, pages
                )
            self.assertEqual({"live"}, keys)
            with open(
                os.path.join(pages, appstore_live.STATE_FILE), encoding="utf-8"
            ) as handle:
                state = json.load(handle)
            self.assertEqual(["1"], state["live_ids"])

    def test_formerly_live_app_requires_three_consecutive_misses(self):
        with tempfile.TemporaryDirectory() as pages:
            apps = {"first": "1", "second": "2"}
            with mock.patch.object(
                appstore_live, "fetch_live_ids", return_value={"1", "2"}
            ):
                self.assertEqual(
                    {"first", "second"},
                    appstore_live.live_app_keys(apps, pages),
                )
            for miss in (1, 2):
                with mock.patch.object(
                    appstore_live, "fetch_live_ids", return_value={"2"}
                ):
                    keys = appstore_live.live_app_keys(apps, pages)
                self.assertIn("first", keys)
                with open(
                    os.path.join(pages, appstore_live.STATE_FILE), encoding="utf-8"
                ) as handle:
                    state = json.load(handle)
                self.assertEqual(miss, state["miss_counts"]["1"])
            with mock.patch.object(
                appstore_live, "fetch_live_ids", return_value={"2"}
            ):
                keys = appstore_live.live_app_keys(apps, pages)
            self.assertEqual({"second"}, keys)

    def test_transient_lookup_failure_keeps_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as pages:
            apps = {"live": "1"}
            with mock.patch.object(
                appstore_live, "fetch_live_ids", return_value={"1"}
            ):
                appstore_live.live_app_keys(apps, pages)
            with mock.patch.object(
                appstore_live, "fetch_live_ids", side_effect=TimeoutError("offline")
            ):
                self.assertEqual(
                    {"live"}, appstore_live.live_app_keys(apps, pages)
                )
            with mock.patch.object(
                appstore_live, "fetch_live_ids", return_value=set()
            ):
                self.assertEqual(
                    {"live"}, appstore_live.live_app_keys(apps, pages)
                )


class GeneratorTests(unittest.TestCase):
    def test_llms_omits_unavailable_apps_and_avoids_false_aim990_claim(self):
        text = gen_llms.build_llms({}, {"aim990", "lumibopomofo"})
        self.assertNotIn("Zafe", text)
        aim_line = gen_llms.app_line("aim990", ["Competitor"], {"aim990"})
        self.assertIn("An independent alternative", aim_line)
        self.assertNotIn("pay-once alternative", aim_line.lower())
        sereno = gen_llms.build_llms({}, {"sereno"})
        self.assertIn("### Sleep & focus", sereno)
        self.assertNotIn("### sleep-sound", sereno)

    def test_topic_hub_has_no_fake_zero_price_and_links_script_locales(self):
        hub = gen_hubs.build_hub("lumibopomofo")
        self.assertNotIn('"price":"0"', hub)
        self.assertIn('hreflang="zh-Hant"', hub)

    def test_alternatives_use_accurate_schema_and_aim990_pricing(self):
        self.assertNotIn("offers", aeo_pages.app_schema("aim990", "Accurate copy"))
        slug, page = aeo_pages.hub_page("aim990", [])
        self.assertEqual("aim990-flexible-unlock", slug)
        self.assertEqual(slug, aeo_pages.alternative_hub_slug("aim990"))
        self.assertIn("one-time unlock option", page)
        self.assertIn("optional subscription plans", page)
        self.assertNotIn("No subscription, no recurring fees", page)
        _slug, comparison = aeo_pages.alt_page("aim990", "magoosh", [])
        self.assertNotIn("no subscription", comparison.lower())
        expected_profiles = {
            "mochi": ("free", "mochi-free-no-ads"),
            "lumibopomofo": ("free_to_start", "lumibopomofo-free-to-start"),
            "snapport": ("neutral", "snapport-private-alternative"),
        }
        for key, (profile, expected_slug) in expected_profiles.items():
            with self.subTest(key=key):
                self.assertEqual(profile, aeo_pages.pricing_profile(key))
                actual_slug, actual_page = aeo_pages.hub_page(
                    key,
                    ["simple task app pay once no subscription"],
                )
                self.assertEqual(expected_slug, actual_slug)
                self.assertEqual(
                    expected_slug,
                    aeo_pages.alternative_hub_slug(key),
                )
                self.assertNotIn("pay once", actual_page.lower())

    def test_alternatives_prune_stale_or_unlisted_app_pages(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            aeo_pages, "ALT", directory
        ):
            keep = {
                "aim990-flexible-unlock.html",
                "snapport-no-subscription.html",
            }
            stale = {
                "aim990-no-subscription.html",
                "zafe-no-subscription.html",
            }
            for filename in keep | stale:
                open(os.path.join(directory, filename), "w", encoding="utf-8").close()
            removed = set(
                aeo_pages.prune_stale_pages(
                    {"aim990", "snapport", "zafe"},
                    keep,
                )
            )
            self.assertEqual(stale, removed)
            self.assertEqual(keep, set(os.listdir(directory)))

    def test_deep_meta_keeps_the_final_word_when_no_truncation_is_needed(self):
        lead = (
            "TripBee Pro keeps a day-by-day itinerary available without an "
            "internet connection."
        )
        self.assertEqual(lead, answer_deep.concise_meta(lead))
        self.assertLessEqual(len(answer_deep.concise_meta("word " * 100)), 151)

    def test_catalog_contains_only_verified_public_apps(self):
        page = gen_app_catalog.render_catalog("en", {"lumibopomofo"})
        self.assertIn("Lumi Bopomofo", page)
        self.assertNotIn("Zafe", page)
        self.assertIn('"numberOfItems": 1', page)

    def test_question_plan_prioritizes_focus_tiers_and_skips_unlisted(self):
        public = {"lumibopomofo", "snapport", "sononote"}
        with (
            mock.patch.object(
                aeo_answers, "live_app_keys", return_value=public
            ) as live_keys,
            mock.patch.object(aeo_answers, "_coverage_rates", return_value={}),
        ):
            plan = aeo_answers.question_plan(None)
            first_seen = []
            for key, _question in plan:
                if key not in first_seen:
                    first_seen.append(key)
            self.assertEqual(
                ["lumibopomofo", "snapport", "sononote"],
                first_seen,
            )
            with self.assertRaisesRegex(SystemExit, "not public"):
                aeo_answers.question_plan(["zafe"])
            self.assertEqual(2, live_keys.call_count)
            self.assertTrue(
                all(call.kwargs.get("refresh") is True for call in live_keys.call_args_list)
            )

    def test_scorecard_marks_unavailable_apps_without_promoting_them(self):
        rows = outreach_scorecard.build_rows({"lumibopomofo"})
        by_key = {row["key"]: row for row in rows}
        self.assertTrue(by_key["lumibopomofo"]["public"])
        self.assertGreater(by_key["lumibopomofo"]["coverage_score"], 0)
        self.assertFalse(by_key["zafe"]["public"])
        self.assertEqual("", by_key["zafe"]["appstore"])


if __name__ == "__main__":
    unittest.main()
