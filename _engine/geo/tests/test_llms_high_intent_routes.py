#!/usr/bin/env python3
"""High-intent routes must be discoverable without inventing route inventory."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_llms  # noqa: E402


def _item(app_key, locale, slug, intent_type="problem_aware"):
    return {
        "_lumi_route": {
            "app_key": app_key,
            "campaign_token": "geo_ask",
            "intent_type": intent_type,
            "locale": locale,
            "record_digest": "a" * 64,
        },
        "id": f"{locale}:{app_key}:{slug}",
        "language": locale.split("-")[0],
        "summary": f"A source-bound summary for {app_key}.",
        "title": f"Should I use {app_key} for this decision?",
        "url": (
            f"{gen_llms.SITE}/{locale}/decide/{app_key}/{slug}.html"
        ),
    }


class HighIntentLlmsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_pages = gen_llms.PAGES
        gen_llms.PAGES = self.temp.name
        self.items = [
            _item("aim990", "en-US", "daily-exam-practice"),
            _item(
                "wordmate",
                "zh-Hant",
                "private-vocabulary-review",
                "privacy_pay_once",
            ),
        ]
        self._write_feed(self.items)

    def tearDown(self):
        gen_llms.PAGES = self.old_pages
        self.temp.cleanup()

    def _write_feed(self, items):
        path = Path(self.temp.name) / gen_llms.HIGH_INTENT_FEED
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "description": "Source-bound test feed.",
                    "feed_url": (
                        f"{gen_llms.SITE}/{gen_llms.HIGH_INTENT_FEED}"
                    ),
                    "home_page_url": gen_llms.SITE,
                    "hubs": [
                        {"type": "WebSub", "url": hub}
                        for hub in gen_llms.WEBSUB_HUBS
                    ],
                    "items": items,
                }
            ),
            encoding="utf-8",
        )

    def test_compact_catalog_exposes_feed_sitemap_and_exact_counts(self):
        text = "\n".join(
            gen_llms.high_intent_decision_route_lines(full=False)
        )
        self.assertIn(
            f"{gen_llms.SITE}/{gen_llms.HIGH_INTENT_FEED}", text
        )
        self.assertIn(
            (
                f"{gen_llms.SITE}/"
                f"{gen_llms.high_intent_decision_routes.SITEMAP_RELATIVE}"
            ),
            text,
        )
        self.assertIn(
            "2 source-bound routes across 2 verified live apps", text
        )
        self.assertNotIn("/decide/", text)
        self.assertIn("not an independent ranking", text)

    def test_full_catalog_lists_exact_feed_urls_once(self):
        lines = gen_llms.high_intent_decision_route_lines(full=True)
        text = "\n".join(lines)
        expected = {item["url"] for item in self.items}
        actual = {
            line.split("](", 1)[1].split(")", 1)[0]
            for line in lines
            if "](" in line and "/decide/" in line
        }
        self.assertEqual(expected, actual)
        for url in expected:
            self.assertEqual(1, text.count(url))

    def test_duplicate_route_is_rejected(self):
        self._write_feed([self.items[0], self.items[0]])
        with self.assertRaisesRegex(ValueError, "duplicate routes"):
            gen_llms.high_intent_decision_route_lines(full=True)

    def test_unbound_or_unpublished_route_is_rejected(self):
        invalid = _item("not_in_registry", "en-US", "unknown-app")
        self._write_feed([invalid])
        with self.assertRaisesRegex(ValueError, "Invalid high-intent"):
            gen_llms.high_intent_decision_route_lines(full=True)


class PublishedHighIntentLlmsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = Path(gen_llms.PAGES)
        paths = (
            cls.pages / gen_llms.HIGH_INTENT_FEED,
            cls.pages / "llms.txt",
            cls.pages / "llms-full.txt",
        )
        if not all(path.is_file() for path in paths):
            raise unittest.SkipTest("generated high-intent llms surfaces are absent")
        cls.feed = json.loads(paths[0].read_text(encoding="utf-8"))
        cls.compact = paths[1].read_text(encoding="utf-8")
        cls.full = paths[2].read_text(encoding="utf-8")

    def test_compact_has_discovery_but_no_individual_routes(self):
        self.assertEqual(
            1,
            self.compact.count(
                "## Source-bound high-intent app decision guides"
            ),
        )
        self.assertNotIn("/decide/", self.compact)
        self.assertIn(
            f"{gen_llms.SITE}/{gen_llms.HIGH_INTENT_FEED}",
            self.compact,
        )

    def test_full_route_urls_are_the_exact_feed_set(self):
        expected = {item["url"] for item in self.feed["items"]}
        actual = {
            line.split("](", 1)[1].split(")", 1)[0]
            for line in self.full.splitlines()
            if "](" in line and "/decide/" in line
        }
        self.assertEqual(expected, actual)
        for url in expected:
            self.assertEqual(1, self.full.count(url))


if __name__ == "__main__":
    unittest.main()
