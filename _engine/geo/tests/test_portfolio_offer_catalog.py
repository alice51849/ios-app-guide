#!/usr/bin/env python3
"""Regression tests for locale-aware App Store offer catalogs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_store_storefronts
from official_locales import OFFICIAL_LOCALES
import portfolio_app_finder
import portfolio_offer_catalog
import publisher_intent_catalog


class PortfolioOfferCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
        cls.index, cls.catalogs = portfolio_offer_catalog.build_payloads(
            cls.pages
        )
        cls.details = app_store_storefronts.load_storefront_details(cls.pages)
        cls.records, cls.apps = publisher_intent_catalog.build_records(
            cls.pages
        )
        cls.records_by_locale = {
            locale: {
                str(record["app_store_id"]): record
                for record in cls.records
                if record["locale"] == locale
            }
            for locale in OFFICIAL_LOCALES
        }

    def test_payloads_cover_every_app_and_official_locale(self):
        self.assertEqual(50, self.index["locale_count"])
        self.assertEqual(28, self.index["app_count"])
        self.assertEqual(1400, self.index["offer_count"])
        self.assertEqual(set(OFFICIAL_LOCALES), set(self.catalogs))
        self.assertGreater(self.index["price_verified_offer_count"], 0)
        self.assertLessEqual(
            self.index["price_verified_offer_count"],
            self.index["offer_count"],
        )

        verified_prices = 0
        for locale, catalog in self.catalogs.items():
            self.assertEqual("https://schema.org", catalog["@context"])
            self.assertEqual("OfferCatalog", catalog["@type"])
            self.assertEqual(locale, catalog["inLanguage"])
            self.assertEqual(28, catalog["numberOfItems"])
            items = catalog["itemListElement"]
            self.assertEqual(list(range(1, 29)), [
                item["position"] for item in items
            ])
            self.assertEqual(
                sorted(
                    (item["item"]["name"] for item in items),
                    key=str.casefold,
                ),
                [item["item"]["name"] for item in items],
            )
            expected_records = self.records_by_locale[locale]
            observed_ids = set()
            country = app_store_storefronts.LOCALE_STOREFRONTS[locale]
            for item in items:
                offer = item["item"]
                application = offer["itemOffered"]
                app_id = application["identifier"]["value"]
                observed_ids.add(app_id)
                record = expected_records[app_id]
                expected_url = record["app_store_url"]
                self.assertEqual(expected_url, item["url"])
                self.assertEqual(expected_url, offer["url"])
                self.assertEqual(expected_url, application["downloadUrl"])
                self.assertEqual(expected_url, application["installUrl"])
                self.assertEqual(
                    expected_url,
                    application["potentialAction"]["target"],
                )
                app_store_storefronts.validated_app_store_url(
                    expected_url,
                    expected_app_id=app_id,
                )
                detail = self.details.get(country, {}).get(app_id)
                if detail is None:
                    self.assertNotIn("price", offer)
                    self.assertNotIn("priceCurrency", offer)
                    self.assertNotIn("availability", offer)
                    self.assertNotIn(
                        "isAccessibleForFree",
                        application,
                    )
                else:
                    verified_prices += 1
                    self.assertEqual(detail["price"], offer["price"])
                    self.assertEqual(
                        detail["currency"],
                        offer["priceCurrency"],
                    )
                    self.assertEqual(
                        "https://schema.org/InStock",
                        offer["availability"],
                    )
                    self.assertEqual(
                        detail["price"] == "0",
                        application["isAccessibleForFree"],
                    )
            self.assertEqual(set(expected_records), observed_ids)
        self.assertEqual(
            self.index["price_verified_offer_count"],
            verified_prices,
        )

    def test_published_catalogs_sitemap_and_finder_discovery_match(self):
        published_index = json.loads(
            (self.pages / portfolio_offer_catalog.INDEX_RELATIVE).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(self.index, published_index)
        expected_urls = {portfolio_offer_catalog.index_url()}
        for locale, expected in self.catalogs.items():
            published = json.loads(
                (
                    self.pages
                    / portfolio_offer_catalog.catalog_relative(locale)
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(expected, published)
            expected_url = portfolio_offer_catalog.catalog_url(locale)
            expected_urls.add(expected_url)
            finder = (
                self.pages
                / locale
                / "tools"
                / f"{portfolio_app_finder.SLUG}.html"
            ).read_text(encoding="utf-8")
            self.assertEqual(
                1,
                finder.count(
                    '<link rel="alternate" type="application/ld+json" '
                    f'href="{expected_url}">'
                ),
            )
            localized_llms = (
                self.pages / "llms" / f"{locale}.txt"
            ).read_text(encoding="utf-8")
            self.assertIn(
                f"Schema.org OfferCatalog: {expected_url}",
                localized_llms,
            )

        sitemap = ET.parse(
            self.pages / portfolio_offer_catalog.SITEMAP_NAME
        ).getroot()
        namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        observed_urls = {
            node.find(f"{namespace}loc").text
            for node in sitemap.findall(f"{namespace}url")
        }
        self.assertEqual(expected_urls, observed_urls)
        self.assertEqual(
            {self.index["date_modified"]},
            {
                node.find(f"{namespace}lastmod").text
                for node in sitemap.findall(f"{namespace}url")
            },
        )
        sitemap_index = ET.parse(self.pages / "sitemap_index.xml").getroot()
        self.assertIn(
            f"{portfolio_offer_catalog.SITE}/"
            f"{portfolio_offer_catalog.SITEMAP_NAME}",
            {
                node.find(f"{namespace}loc").text
                for node in sitemap_index.findall(f"{namespace}sitemap")
            },
        )
        for path in ("llms.txt", "llms-full.txt", "robots.txt"):
            self.assertIn(
                portfolio_offer_catalog.index_url()
                if path != "robots.txt"
                else portfolio_offer_catalog.SITEMAP_NAME,
                (self.pages / path).read_text(encoding="utf-8"),
            )

    def test_unverified_price_is_omitted_instead_of_invented(self):
        record = self.records[0]
        app = self.apps[str(record["app_key"])]
        item = portfolio_offer_catalog.offer_item(record, app, None, 1)
        offer = item["item"]
        self.assertNotIn("price", offer)
        self.assertNotIn("priceCurrency", offer)
        self.assertNotIn("availability", offer)


if __name__ == "__main__":
    unittest.main()
