#!/usr/bin/env python3
"""Tests for the data-driven App Store search line (build_search_terms.py + search_caption.search_term)."""
import csv
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import build_search_terms as B  # noqa: E402
import clip_posts  # noqa: E402
import search_caption as SC  # noqa: E402

HEADER = ["date", "storefront", "app", "term", "rank", "results"]


def history(rows):
    """Write rows to a temp CSV and read it back the way the builder does."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    try:
        return B.read_history(f.name)
    finally:
        os.unlink(f.name)


class BuildTest(unittest.TestCase):
    def test_smallest_rank_above_one_wins_and_one_is_only_the_fallback(self):
        h = history([
            ["2026-10-17", "US", "mochi", "mochi", "1", "50"],
            ["2026-10-17", "US", "mochi", "cute todo", "4", "80"],
            ["2026-10-17", "US", "mochi", "todo list", "12", "190"],
            ["2026-10-17", "US", "mochi", "planner", "", "190"],          # not in the top 200
            ["2026-10-17", "US", "mochi", "checklist", "45", "190"],      # past the window
            ["2026-10-17", "JP", "mochi", "かわいいtodo", "1", "20"],       # only a #1 term: kept as fallback
        ])
        apps = B.build(h)["apps"]
        self.assertEqual(apps["mochi"]["US"]["term"], "cute todo")
        self.assertEqual(apps["mochi"]["US"]["rank"], 4)
        self.assertEqual(apps["mochi"]["US"]["locale"], "en")
        self.assertEqual(apps["mochi"]["JP"]["term"], "かわいいtodo")

    def test_latest_reading_counts_and_stale_terms_drop(self):
        h = history([
            ["2026-10-01", "US", "mochi", "cute todo", "2", "80"],
            ["2026-10-17", "US", "mochi", "cute todo", "40", "80"],     # fell out of the window since
            ["2026-10-02", "US", "mochi", "todo app", "3", "190"],      # last read 15 days before the newest row
            ["2026-10-16", "US", "mochi", "checklist", "9", "190"],
        ])
        self.assertEqual(B.build(h)["apps"]["mochi"]["US"]["term"], "checklist")

    def test_tie_goes_to_the_term_with_more_results(self):
        h = history([
            ["2026-10-17", "DE", "x", "copilot nutzung", "3", "4"],
            ["2026-10-17", "DE", "x", "ki nutzung tracker", "3", "11"],
        ])
        self.assertEqual(B.build(h)["apps"]["x"]["DE"]["term"], "ki nutzung tracker")

    def test_term_must_be_in_the_storefront_language(self):
        h = history([
            ["2026-10-17", "JP", "a", "usage tracker", "2", "9"],      # English in Japan
            ["2026-10-17", "JP", "a", "使用量", "5", "9"],
            ["2026-10-17", "KR", "a", "使用量", "2", "9"],             # no Hangul in Korea
            ["2026-10-17", "KR", "a", "사용량", "6", "9"],
            ["2026-10-17", "TW", "a", "这个用量", "2", "9"],           # Simplified in Taiwan
            ["2026-10-17", "TW", "a", "用量追蹤", "7", "9"],
            ["2026-10-17", "US", "a", "token usage", "30", "9"],
            ["2026-10-17", "FR", "a", "token usage", "2", "9"],        # the English term tracked in the US
            ["2026-10-17", "FR", "a", "consommation tokens", "8", "9"],
            ["2026-10-17", "RU", "a", "token usage", "2", "9"],        # no Cyrillic in Russia
            ["2026-10-17", "RU", "a", "расход токенов", "9", "9"],
            ["2026-10-17", "XX", "a", "anything", "2", "9"],           # storefront without a caption locale
        ])
        apps = B.build(h)["apps"]["a"]
        self.assertEqual({sf: e["term"] for sf, e in apps.items()},
                         {"JP": "使用量", "KR": "사용량", "TW": "用量追蹤", "US": "token usage",
                          "FR": "consommation tokens", "RU": "расход токенов"})

    def test_terms_failing_the_post_claim_check_are_skipped(self):
        h = history([
            ["2026-10-17", "US", "a", "best todo app", "2", "190"],    # superlative
            ["2026-10-17", "US", "a", "chatgpt usage", "3", "190"],    # competitor the store text does not name
            ["2026-10-17", "US", "a", "todo widget", "6", "190"],
        ])
        self.assertEqual(B.build(h)["apps"]["a"]["US"]["term"], "todo widget")

    def test_paid_flag_from_the_funnel(self):
        h = history([["2026-10-17", "TW", "a", "用量追蹤", "2", "9"], ["2026-10-17", "US", "a", "usage", "5", "9"]])
        funnel = {"apps": [{"app_key": "a", "top_paid_markets_7d": [{"country": "TW", "paid_units_7d": 1.0}]}]}
        apps = B.build(h, funnel)["apps"]["a"]
        self.assertTrue(apps["TW"]["paid"])
        self.assertFalse(apps["US"]["paid"])

    def test_empty_history_writes_nothing(self):
        self.assertEqual(B.build({})["apps"], {})


DAY = dt.date(2026, 10, 17)
DATA = {"apps": {"mochi": {
    "US": {"term": "cute todo", "rank": 4, "date": "2026-10-17", "locale": "en", "paid": False, "weight": 1.0},
    "GB": {"term": "todo list", "rank": 3, "date": "2026-10-17", "locale": "en", "paid": True, "weight": 0.45},
    "TW": {"term": "待辦清單", "rank": 2, "date": "2026-09-01", "locale": "zh-Hant", "paid": True, "weight": 0.3},
}}}


class SearchTermTest(unittest.TestCase):
    def test_store_link_storefront_first(self):
        self.assertEqual(SC.search_term("mochi", "en", "https://apps.apple.com/us/app/id1", "Mochi", DATA, DAY),
                         "cute todo")

    def test_locale_storefronts_paid_first_without_a_store_link(self):
        self.assertEqual(SC.search_term("mochi", "en", "", "Mochi", DATA, DAY), "todo list")

    def test_store_link_in_another_language_falls_to_the_locale(self):
        self.assertEqual(SC.search_term("mochi", "en", "https://apps.apple.com/tw/app/id1", "Mochi", DATA, DAY),
                         "todo list")

    def test_stale_or_missing_entries_keep_the_fallback(self):
        self.assertEqual(SC.search_term("mochi", "zh-Hant", "", "Mochi 可愛待辦清單", DATA, DAY), "Mochi 可愛待辦清單")
        self.assertEqual(SC.search_term("mochi", "ja", "", "Mochi かわいいToDo", DATA, DAY), "Mochi かわいいToDo")
        self.assertEqual(SC.search_term("zipbox", "en", "", "ZipBox", DATA, DAY), "ZipBox")
        self.assertEqual(SC.search_term("mochi", "en", "", "Mochi", {}, DAY), "Mochi")

    def test_hook_variant_listing_uses_its_base_app(self):
        clip = {"app": "mochi_b", "locale": "en", "store_url": "https://apps.apple.com/us/app/id1", "search": "Mochi"}
        self.assertEqual(SC.clip_search(clip, DATA, DAY), "cute todo")

    def test_caption_carries_the_term_and_still_the_download_link(self):
        clip = {"app": "mochi", "locale": "en", "name": "Mochi: Cute Checklist", "search": "Mochi Cute Checklist",
                "hook": "Your to-do list, but make it cute", "url": "https://files.catbox.moe/x.mp4",
                "store_url": "https://apps.apple.com/us/app/id6785004775?pt=118326163&ct=h7_mochi&mt=8"}
        with mock.patch.object(SC, "_terms", return_value=DATA), mock.patch.object(SC, "today", return_value=DAY):
            text = clip_posts.caption(clip, "telegram")
        self.assertIn("Search “cute todo” on the App Store", text)
        self.assertIn("Mochi: Cute Checklist", text)
        self.assertIn("apps.apple.com/us/app/id6785004775", text)
        with mock.patch.object(SC, "_terms", return_value={}):
            self.assertIn("Search “Mochi Cute Checklist” on the App Store", clip_posts.caption(clip, "telegram"))


class CommittedFileTest(unittest.TestCase):
    """The committed search-terms.json: only tracked, ranked, in-language terms."""

    def test_committed_terms_are_well_formed(self):
        data = json.loads(SC.SEARCH_TERMS.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], B.SCHEMA)
        self.assertTrue(data["apps"])
        for app, per in data["apps"].items():
            for sf, e in per.items():
                with self.subTest(app=app, storefront=sf):
                    self.assertEqual(e["locale"], B.LOCALE[sf])
                    self.assertTrue(1 <= e["rank"] <= B.WINDOW[1])
                    self.assertTrue(B.in_language(e["term"], sf))
                    self.assertLessEqual(e["date"], data["as_of"])

    def test_committed_terms_match_the_rank_history_when_it_is_checked_out(self):
        path = B.ENGINE / "data" / "rank_watch" / "history.csv"
        if not path.is_file():  # the guide CI has no Growth Engine checkout; the builder's own tests cover the logic
            return
        h = B.read_history(path)
        data = json.loads(SC.SEARCH_TERMS.read_text(encoding="utf-8"))
        for app, per in data["apps"].items():
            for sf, e in per.items():
                with self.subTest(app=app, storefront=sf):
                    reading = h.get((app, sf, e["term"]))
                    self.assertIsNotNone(reading, "term not tracked by the rank probe")
                    self.assertGreaterEqual(reading[0], e["date"])


if __name__ == "__main__":
    unittest.main()
