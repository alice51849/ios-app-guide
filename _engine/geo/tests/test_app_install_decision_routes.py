#!/usr/bin/env python3
"""Regression tests for localized install-decision routes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_install_decision_routes
import app_store_storefronts
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog


class AppInstallDecisionRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        possible_pages = []
        configured = os.environ.get("GEO_PAGES")
        if configured:
            possible_pages.append(Path(configured))
        possible_pages.extend((GEO / "pages", GEO.parents[1]))
        cls.pages = next(
            (
                path
                for path in possible_pages
                if (path / app_install_decision_routes.DATA_RELATIVE).exists()
            ),
            None,
        )
        if cls.pages is None:
            raise unittest.SkipTest("Generated install-decision routes are absent")
        cls.payload = json.loads(
            (cls.pages / app_install_decision_routes.DATA_RELATIVE).read_text(
                encoding="utf-8"
            )
        )
        cls.records = cls.payload["records"]
        cls.apps = publisher_intent_catalog.build_records(cls.pages)[1]
        cls.by_locale = {
            locale: [
                record for record in cls.records if record["locale"] == locale
            ]
            for locale in OFFICIAL_LOCALES
        }

    def test_dataset_covers_every_live_app_locale_with_bounded_priority(self) -> None:
        expected_app_count = len(self.apps)
        self.assertEqual(50, self.payload["locale_count"])
        self.assertEqual(expected_app_count, self.payload["app_count"])
        self.assertEqual(
            expected_app_count * len(OFFICIAL_LOCALES),
            self.payload["record_count"],
        )
        self.assertEqual(
            list(app_install_decision_routes.PRIORITY_APPS),
            self.payload["priority_app_keys"],
        )
        self.assertEqual(list(OFFICIAL_LOCALES), self.payload["locales"])

        for locale in OFFICIAL_LOCALES:
            locale_records = self.by_locale[locale]
            self.assertEqual(expected_app_count, len(locale_records))
            self.assertEqual(
                list(app_install_decision_routes.PRIORITY_APPS),
                [
                    record["app_key"]
                    for record in locale_records[
                        : len(app_install_decision_routes.PRIORITY_APPS)
                    ]
                ],
            )
            remaining = locale_records[
                len(app_install_decision_routes.PRIORITY_APPS) :
            ]
            self.assertEqual(
                sorted(
                    (record["app_name"] for record in remaining),
                    key=str.casefold,
                ),
                [record["app_name"] for record in remaining],
            )

    def test_records_keep_direct_links_dedup_and_provenance(self) -> None:
        seen_ids: set[str] = set()
        seen_pages: set[str] = set()
        for record in self.records:
            self.assertNotIn(record["record_id"], seen_ids)
            seen_ids.add(record["record_id"])
            self.assertNotIn(record["decision_page_url"], seen_pages)
            seen_pages.add(record["decision_page_url"])
            self.assertFalse(record["is_ranking"])
            self.assertFalse(record["measured_search_volume"])
            self.assertTrue(record["verified_live"])
            self.assertGreaterEqual(len(record["publisher_disclosure"]), 20)
            self.assertIn(
                record["source_surface"],
                {"answer_page", "app_guide_page"},
            )
            self.assertEqual(
                app_install_decision_routes.locale_index_url(
                    record["locale"]
                ),
                record["locale_index_url"],
            )
            app_store_storefronts.validated_app_store_url(
                record["app_store_url"],
                expected_app_id=record["app_store_id"],
            )
            self.assertTrue(record["badge_labels"])
            self.assertEqual(
                len(record["badge_labels"]),
                len(set(record["badge_labels"])),
            )

    def test_locale_indexes_and_pages_match_dataset(self) -> None:
        for locale in OFFICIAL_LOCALES:
            payload = json.loads(
                (
                    self.pages
                    / app_install_decision_routes.locale_index_relative(locale)
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(locale, payload["locale"])
            self.assertEqual(len(self.apps), payload["record_count"])
            self.assertEqual(
                list(app_install_decision_routes.PRIORITY_APPS),
                payload["priority_app_keys"],
            )
            self.assertEqual(
                [record["record_id"] for record in self.by_locale[locale]],
                [record["record_id"] for record in payload["records"]],
            )

        samples = [
            self.by_locale["en-US"][0],
            self.by_locale["zh-Hant"][1],
            self.by_locale["ja"][2],
            self.records[-1],
        ]
        for record in samples:
            path = self.pages / app_install_decision_routes.decision_page_relative(
                record["app_key"],
                record["locale"],
            )
            self.assertTrue(path.is_file(), path)
            source = path.read_text(encoding="utf-8")
            self.assertIn(
                f'<link rel="canonical" href="{record["decision_page_url"]}">',
                source,
            )
            self.assertIn(record["app_store_url"], source)
            self.assertIn(record["canonical_guide_url"], source)
            self.assertIn('id="decision-record"', source)
            self.assertIn(record["app_store_cta_label"], source)

    def test_llms_discloses_decision_indexes(self) -> None:
        root = (self.pages / "llms.txt").read_text(encoding="utf-8")
        self.assertIn(app_install_decision_routes.data_url(), root)
        self.assertIn(app_install_decision_routes.sitemap_url(), root)
        localized = (self.pages / "llms" / "ja.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn(app_install_decision_routes.locale_index_url("ja"), localized)

    def test_dedicated_sitemap_covers_routes_and_indexes_exactly_once(self) -> None:
        sitemap = ET.parse(
            self.pages / app_install_decision_routes.SITEMAP_NAME
        ).getroot()
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        locations = [
            node.find(f"{namespace}loc").text
            for node in sitemap.findall(f"{namespace}url")
        ]
        expected = app_install_decision_routes.sitemap_entries(self.records)
        self.assertEqual(expected, locations)
        self.assertEqual(1600, sum("/decision/l/" in url for url in locations))
        self.assertEqual(len(expected), len(set(locations)))

    def test_sitemap_index_and_robots_register_decision_sitemap(self) -> None:
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        sitemap_index = ET.parse(self.pages / "sitemap_index.xml").getroot()
        self.assertIn(
            app_install_decision_routes.sitemap_url(),
            {
                node.find(f"{namespace}loc").text
                for node in sitemap_index.findall(f"{namespace}sitemap")
            },
        )
        robots = (self.pages / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(app_install_decision_routes.SITEMAP_NAME, robots)


if __name__ == "__main__":
    unittest.main()
