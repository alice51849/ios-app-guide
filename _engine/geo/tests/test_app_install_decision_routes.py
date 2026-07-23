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

import app_install_decision_feeds
import app_install_decision_routes
import app_store_storefronts
import gen_social_previews
from official_locales import OFFICIAL_LOCALES, open_graph_locale
import portfolio_app_finder
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
        cls.storefront_details = (
            app_store_storefronts.load_storefront_details(cls.pages)
        )
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
        self.assertEqual(
            app_install_decision_feeds.syndication_payload(),
            self.payload["syndication"],
        )

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

    def test_schema_declares_every_dataset_field(self) -> None:
        schema = json.loads(
            (
                self.pages / app_install_decision_routes.SCHEMA_RELATIVE
            ).read_text(encoding="utf-8")
        )
        properties = set(schema["properties"])
        required = set(schema["required"])
        self.assertEqual(set(self.payload), properties)
        self.assertEqual(properties, required)

    def test_records_keep_direct_links_dedup_and_provenance(self) -> None:
        seen_ids: set[str] = set()
        seen_pages: set[str] = set()
        verified_storefront_records = 0
        verified_rating_records = 0
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
            country = app_store_storefronts.LOCALE_STOREFRONTS[
                record["locale"]
            ]
            expected_facts = self.storefront_details.get(country, {}).get(
                record["app_store_id"]
            )
            if expected_facts is None:
                self.assertIsNone(record["storefront_facts"])
                continue
            expected_facts = (
                app_store_storefronts.localized_storefront_detail(
                    expected_facts,
                    record["locale"],
                )
            )
            self.assertEqual(expected_facts, record["storefront_facts"])
            self.assertTrue(
                any(
                    str(expected_facts["formatted_price"]) in label
                    for label in record["badge_labels"]
                )
            )
            structured = app_install_decision_routes._structured_data(record)
            app_entity = structured["@graph"][0]
            self.assertEqual(
                str(expected_facts["price"]),
                app_entity["offers"]["price"],
            )
            self.assertEqual(
                str(expected_facts["currency"]),
                app_entity["offers"]["priceCurrency"],
            )
            self.assertEqual(
                record["app_store_url"],
                app_entity["offers"]["url"],
            )
            verified_storefront_records += 1
            if "rating_value" in expected_facts:
                self.assertEqual(
                    float(expected_facts["rating_value"]),
                    app_entity["aggregateRating"]["ratingValue"],
                )
                self.assertEqual(
                    int(expected_facts["rating_count"]),
                    app_entity["aggregateRating"]["ratingCount"],
                )
                verified_rating_records += 1
        self.assertGreater(
            verified_storefront_records,
            len(self.records) * 0.95,
        )
        self.assertGreater(verified_rating_records, 0)

    def test_kids_writing_copy_uses_native_practice_terms(self) -> None:
        expected = {
            "da:lumibopomofo": "skriveøvelser",
            "da:lumiletterspro": "skriveøvelser",
            "no:lumibopomofo": "skriveøvelser",
            "no:lumiletterspro": "skriveøvelser",
            "sv:lumiletterspro": "skrivövningar",
            "nl-NL:lumibopomofo": "overtrekken",
            "nl-NL:lumiletterspro": "overtrekken",
        }
        records = {record["record_id"]: record for record in self.records}
        forbidden = ("sporing", "spårning", "traceren")
        for record_id, native_term in expected.items():
            with self.subTest(record_id=record_id):
                context = records[record_id]["decision_context"].casefold()
                self.assertIn(native_term.casefold(), context)
                self.assertFalse(
                    any(term in context for term in forbidden),
                    context,
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
                app_install_decision_feeds.feed_urls(locale),
                payload["syndication"],
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
            if record["storefront_facts"] is not None:
                self.assertIn(
                    str(record["storefront_facts"]["formatted_price"]),
                    source,
                )
            self.assertIn(
                f'<meta name="twitter:app:id:iphone" '
                f'content="{record["app_store_id"]}">',
                source,
            )
            for feed_url in app_install_decision_feeds.feed_urls(
                record["locale"]
            ).values():
                self.assertIn(feed_url, source)

    def test_every_route_has_localized_install_share_metadata(self) -> None:
        verified_storefronts = 0
        fallback_storefronts = 0
        for record in self.records:
            page = (
                self.pages
                / app_install_decision_routes.decision_page_relative(
                    record["app_key"],
                    record["locale"],
                )
            )
            source = page.read_text(encoding="utf-8")
            share_url = (
                f"{app_install_decision_routes.SITE}/social/img/"
                f"{record['app_key']}-share.jpg"
            )
            self.assertEqual(
                1,
                source.count('type="application/json+oembed"'),
                record["record_id"],
            )
            self.assertIn(
                f'href="{record["oembed_url"].replace("&", "&amp;")}"',
                source,
                record["record_id"],
            )
            self.assertIn(
                f'property="og:locale" content="'
                f'{open_graph_locale(record["locale"])}"',
                source,
                record["record_id"],
            )
            self.assertIn(
                'property="og:site_name" content="iOS App Guide"',
                source,
                record["record_id"],
            )
            self.assertIn(
                f'property="og:image" content="{share_url}"',
                source,
                record["record_id"],
            )
            self.assertIn(
                f'property="og:image:width" content="'
                f'{gen_social_previews.CARD_SIZE[0]}"',
                source,
                record["record_id"],
            )
            self.assertIn(
                f'property="og:image:height" content="'
                f'{gen_social_previews.CARD_SIZE[1]}"',
                source,
                record["record_id"],
            )
            self.assertIn(
                f'name="twitter:image" content="{share_url}"',
                source,
                record["record_id"],
            )
            self.assertIn(
                f'name="twitter:app:id:iphone" '
                f'content="{record["app_store_id"]}"',
                source,
                record["record_id"],
            )
            endpoint = (
                self.pages
                / app_install_decision_routes.decision_oembed_relative(
                    record["app_key"],
                    record["locale"],
                )
            )
            self.assertTrue(endpoint.is_file(), endpoint)
            embed = json.loads(endpoint.read_text(encoding="utf-8"))
            self.assertEqual("rich", embed["type"])
            self.assertEqual(record["publisher_query"], embed["title"])
            self.assertEqual(
                record["decision_page_url"],
                embed["_lumi_decision_url"],
            )
            self.assertNotIn("_lumi_guide_url", embed)
            self.assertIn(
                f"id{record['app_store_id']}",
                embed["_lumi_app_store_url"],
            )

            structured = app_install_decision_routes._structured_data(record)
            webpage = structured["@graph"][1]
            self.assertEqual(
                share_url,
                webpage["primaryImageOfPage"]["contentUrl"],
            )
            storefront = record["storefront_facts"]
            if storefront is None:
                fallback_storefronts += 1
                self.assertIn(
                    'property="og:type" content="website"',
                    source,
                )
                self.assertNotIn("product:price:amount", source)
                self.assertNotIn('name="twitter:data1"', source)
                continue
            verified_storefronts += 1
            self.assertIn(
                'property="og:type" content="product"',
                source,
            )
            self.assertIn(
                f'property="product:price:amount" '
                f'content="{storefront["price"]}"',
                source,
            )
            self.assertIn(
                f'property="product:price:currency" '
                f'content="{storefront["currency"]}"',
                source,
            )
            self.assertIn(
                f'name="twitter:data1" '
                f'content="{storefront["formatted_price"]}"',
                source,
            )
        self.assertGreater(verified_storefronts, len(self.records) * 0.95)
        self.assertGreater(fallback_storefronts, 0)
        self.assertEqual(
            len(self.records),
            len(
                list(
                    (
                        self.pages
                        / app_install_decision_routes.OEMBED_DIR
                    ).glob("*/*.json")
                )
            ),
        )

    def test_every_route_has_a_localized_finder_inbound_link(self) -> None:
        for locale in OFFICIAL_LOCALES:
            finder = (
                self.pages
                / locale
                / "tools"
                / f"{portfolio_app_finder.SLUG}.html"
            ).read_text(encoding="utf-8")
            for record in self.by_locale[locale]:
                self.assertIn(
                    f'href="{record["decision_page_url"]}"',
                    finder,
                    record["record_id"],
                )

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
        self.assertEqual(
            1600,
            sum("/oembed/decision/" in url for url in locations),
        )
        self.assertEqual(
            len(OFFICIAL_LOCALES) * len(app_install_decision_feeds.FORMATS),
            sum(
                "/data/app-install-decision-routes/feeds/" in url
                for url in locations
            ),
        )
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
