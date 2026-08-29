#!/usr/bin/env python3
"""Regression tests for the two cross-app surfaces an AI assistant reads.

The decision matrix and the agent product feed both exist so an assistant can
answer "which of these should I install?" without inferring anything. That makes
them the two files where an invented difference would do the most damage, so the
tests here check the same three things from both sides: every column is filled
from something the repository can defend, no row states a fact Apple's public
lookup has not confirmed, and nothing private ever reaches a public file.
"""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import agent_product_feed  # noqa: E402
import app_decision_matrix  # noqa: E402
import app_store_storefronts  # noqa: E402
import gen_llms  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", GEO / "pages"))

# Numbers that are allowed to appear inside a sentence a buyer will read back:
# they are part of a product name, not a measurement of our business.
ALLOWED_SENTENCE_NUMBERS = {"100", "44", "990", "3", "8"}
# A buyer's own search phrase can carry the year they are shopping in
# ("best resume builder app ... 2026"). A calendar year says nothing about how
# the app is selling, so it is allowed; every other number still is not.
CALENDAR_YEAR_RE = re.compile(r"^20\d\d$")

# Words that would turn a first-party table into a performance claim.
FORBIDDEN_WORDS = (
    "download count",
    "downloads",
    "installs",
    "revenue",
    "proceeds",
    "units sold",
    "best-selling",
    "bestseller",
    "top-ranked",
    "number one",
    "#1",
    "conversion rate",
    "impressions",
)


def _snapshot_available() -> bool:
    return (PAGES / ".appstore_storefront_state.json").exists()


class DecisionMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _snapshot_available():
            raise unittest.SkipTest("no App Store snapshot in this checkout")
        cls.rows, cls.modified = app_decision_matrix.build_rows(PAGES)
        cls.payload = app_decision_matrix.matrix_payload(cls.rows, cls.modified)
        cls.details = app_store_storefronts.load_storefront_details(PAGES)

    def test_every_row_carries_every_column(self):
        expected = {column["name"] for column in app_decision_matrix.COLUMNS}
        self.assertTrue(self.rows)
        for row in self.rows:
            with self.subTest(app=row["app_key"]):
                self.assertEqual(set(row), expected)

    def test_columns_all_declare_where_the_value_came_from(self):
        for column in app_decision_matrix.COLUMNS:
            with self.subTest(column=column["name"]):
                self.assertTrue(column["description"].strip())
                self.assertTrue(column["source"].strip())

    def test_the_table_never_presents_itself_as_a_ranking(self):
        self.assertFalse(self.payload["is_ranking"])
        self.assertFalse(self.payload["measured_search_volume"])
        self.assertEqual(self.payload["ordering"], "alphabetical_by_app_key")
        self.assertEqual(
            [row["app_key"] for row in self.rows],
            sorted(row["app_key"] for row in self.rows),
        )

    def test_no_row_claims_a_subscription_or_an_unmapped_model(self):
        for row in self.rows:
            with self.subTest(app=row["app_key"]):
                self.assertIs(row["subscription"], False)
                self.assertIn(
                    row["purchase_model"],
                    app_decision_matrix.PURCHASE_MODEL_LABELS,
                )
                self.assertIn(
                    "no subscription", row["purchase_model_label"]
                )

    def test_prices_match_apples_own_snapshot_for_the_us_storefront(self):
        us = self.details.get(app_decision_matrix.BASE_COUNTRY, {})
        for row in self.rows:
            detail = us.get(row["app_store_id"])
            with self.subTest(app=row["app_key"]):
                if detail is None:
                    self.assertIsNone(row["us_price"])
                    self.assertIsNone(row["free_to_download"])
                    continue
                self.assertEqual(row["us_price"], str(detail["price"]))
                self.assertEqual(
                    row["us_price_currency"], str(detail["currency"])
                )
                self.assertIs(
                    row["free_to_download"], str(detail["price"]) == "0"
                )

    def test_verified_storefront_counts_are_counted_not_asserted(self):
        for row in self.rows:
            expected = sum(
                row["app_store_id"] in country
                for country in self.details.values()
            )
            with self.subTest(app=row["app_key"]):
                self.assertEqual(row["verified_storefront_count"], expected)
                self.assertLessEqual(
                    row["verified_storefront_count"], len(self.details)
                )

    def test_store_links_point_at_the_app_they_name(self):
        for row in self.rows:
            with self.subTest(app=row["app_key"]):
                self.assertRegex(row["app_store_id"], r"^\d+$")
                self.assertIn(
                    f"id{row['app_store_id']}", row["app_store_url"]
                )
                self.assertTrue(
                    row["guide_url"].startswith("https://"), row["guide_url"]
                )

    def test_sibling_editions_are_published_apps_and_symmetric(self):
        keys = {row["app_key"] for row in self.rows}
        by_key = {row["app_key"]: row for row in self.rows}
        for row in self.rows:
            for sibling in row["sibling_app_keys"]:
                with self.subTest(app=row["app_key"], sibling=sibling):
                    self.assertIn(sibling, keys)
                    self.assertNotEqual(sibling, row["app_key"])
                    self.assertIn(
                        row["app_key"], by_key[sibling]["sibling_app_keys"]
                    )

    def test_judgement_columns_stay_inside_the_purchase_model(self):
        for row in self.rows:
            with self.subTest(app=row["app_key"]):
                self.assertTrue(row["choose_when"].endswith("."))
                self.assertIn(
                    row["purchase_model_label"], row["choose_when"]
                )
                self.assertIn(
                    app_decision_matrix.CONSIDER_INSTEAD[row["purchase_model"]],
                    row["consider_instead_when"],
                )

    def test_no_sentence_makes_an_unsupportable_claim(self):
        for row in self.rows:
            for field in (
                "choose_when",
                "consider_instead_when",
                "decision_context",
                "buyer_intent",
                "category_label",
            ):
                with self.subTest(app=row["app_key"], field=field):
                    self.assertIsNone(
                        gen_llms.BANNED_CLAIM_RE.search(str(row[field]))
                    )

    def test_no_sentence_leaks_a_private_business_number(self):
        for row in self.rows:
            for field in ("choose_when", "consider_instead_when", "buyer_intent"):
                text = str(row[field])
                lowered = text.casefold()
                for word in FORBIDDEN_WORDS:
                    with self.subTest(app=row["app_key"], word=word):
                        self.assertNotIn(word, lowered)
                for number in re.findall(r"\b[0-9][0-9,.]*\b", text):
                    if CALENDAR_YEAR_RE.fullmatch(number):
                        continue
                    with self.subTest(app=row["app_key"], number=number):
                        self.assertIn(number, ALLOWED_SENTENCE_NUMBERS)

    def test_groups_cover_every_row_exactly_once(self):
        grouped = [
            key
            for group in self.payload["groups"]
            for key in group["app_keys"]
        ]
        self.assertEqual(
            sorted(grouped), sorted(row["app_key"] for row in self.rows)
        )
        self.assertEqual(len(grouped), len(set(grouped)))

    def test_csv_round_trips_every_row(self):
        text = app_decision_matrix.csv_text(self.rows)
        parsed = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(parsed), len(self.rows))
        self.assertEqual(
            [row["app_key"] for row in parsed],
            [row["app_key"] for row in self.rows],
        )

    def test_jsonld_describes_the_same_apps_without_inventing_ratings(self):
        payload = app_decision_matrix.jsonld_payload(self.rows, self.modified)
        self.assertEqual(payload["numberOfItems"], len(self.rows))
        self.assertEqual(
            payload["itemListOrder"], "https://schema.org/ItemListUnordered"
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("aggregateRating", serialized)
        self.assertNotIn("reviewCount", serialized)
        for item in payload["itemListElement"]:
            application = item["item"]
            with self.subTest(app=application["name"]):
                self.assertEqual(application["operatingSystem"], "iOS")
                self.assertTrue(application["description"].strip())


class AgentProductFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _snapshot_available():
            raise unittest.SkipTest("no App Store snapshot in this checkout")
        cls.rows, cls.modified = agent_product_feed.build_rows(PAGES)
        cls.details = app_store_storefronts.load_storefront_details(PAGES)

    def test_the_feed_is_not_empty_and_every_id_is_unique(self):
        self.assertTrue(self.rows)
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_row_carries_the_fields_a_shopping_reader_expects(self):
        required = set(agent_product_feed.schema_payload()["required"])
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertTrue(required.issubset(set(row)))

    def test_no_row_offers_a_checkout_this_publisher_does_not_run(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertIs(row["enable_checkout"], False)
                self.assertIs(row["enable_search"], True)
                self.assertIn("apps.apple.com", row["app_store_url"])

    def test_rows_exist_only_where_apples_lookup_confirms_the_sale(self):
        for row in self.rows:
            country = row["shipping_country"].lower()
            detail = self.details.get(country, {}).get(row["app_store_id"])
            with self.subTest(row=row["id"]):
                self.assertIsNotNone(detail)
                self.assertEqual(row["price_value"], str(detail["price"]))
                self.assertEqual(
                    row["price"],
                    f"{row['price_value']} {row['price_currency']}",
                )

    def test_prices_and_languages_use_the_codes_they_claim(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertRegex(row["price_currency"], r"^[A-Z]{3}$")
                self.assertRegex(row["price_value"], r"^\d+(\.\d+)?$")
                self.assertIn(row["content_language"], OFFICIAL_LOCALES)
                self.assertRegex(row["shipping_country"], r"^[A-Z]{2}$")

    def test_every_row_is_readable_on_its_own(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertLessEqual(
                    len(row["title"]), agent_product_feed.TITLE_LIMIT
                )
                self.assertLessEqual(
                    len(row["description"]),
                    agent_product_feed.DESCRIPTION_LIMIT,
                )
                self.assertIn(
                    row["title"].casefold(), row["description"].casefold()
                )
                self.assertTrue(row["link"].startswith("https://"))

    def test_the_feed_makes_no_unsupportable_or_private_claim(self):
        for row in self.rows:
            lowered = row["description"].casefold()
            with self.subTest(row=row["id"]):
                self.assertIsNone(
                    gen_llms.BANNED_CLAIM_RE.search(row["description"])
                )
                for word in FORBIDDEN_WORDS:
                    self.assertNotIn(word, lowered)
                self.assertIs(row["subscription"], False)

    def test_index_counts_match_the_feed_it_indexes(self):
        payload = agent_product_feed.index_payload(self.rows, self.modified)
        self.assertEqual(payload["row_count"], len(self.rows))
        self.assertEqual(
            payload["app_count"],
            len({row["item_group_id"] for row in self.rows}),
        )
        self.assertEqual(
            payload["locale_count"],
            len({row["content_language"] for row in self.rows}),
        )
        self.assertFalse(payload["enable_checkout"])
        self.assertIn("Apple App Store", payload["checkout_note"])

    def test_csv_round_trips_every_row(self):
        parsed = list(
            csv.DictReader(io.StringIO(agent_product_feed.csv_text(self.rows)))
        )
        self.assertEqual(len(parsed), len(self.rows))
        self.assertEqual(
            [row["id"] for row in parsed], [row["id"] for row in self.rows]
        )
        self.assertTrue(
            all(row["enable_checkout"] == "false" for row in parsed)
        )


class PublishedSurfaceTests(unittest.TestCase):
    """llms.txt has to actually point at both surfaces, or nothing reads them."""

    @classmethod
    def setUpClass(cls):
        llms = PAGES / "llms.txt"
        full = PAGES / "llms-full.txt"
        if not llms.exists() or not full.exists():
            raise unittest.SkipTest("llms files not generated in this checkout")
        cls.llms_text = llms.read_text(encoding="utf-8")
        cls.full_text = full.read_text(encoding="utf-8")

    def test_llms_files_link_the_decision_matrix(self):
        for text in (self.llms_text, self.full_text):
            self.assertIn(
                "## Cross-app decision matrix (identical columns, not a ranking)",
                text,
            )
            for url in (
                app_decision_matrix.json_url(),
                app_decision_matrix.jsonl_url(),
                app_decision_matrix.csv_url(),
                app_decision_matrix.schema_url(),
                app_decision_matrix.jsonld_url(),
            ):
                self.assertIn(url, text)

    def test_llms_files_link_the_agent_product_feed(self):
        for text in (self.llms_text, self.full_text):
            self.assertIn("## Agent product feed", text)
            for url in (
                agent_product_feed.index_url(),
                agent_product_feed.feed_url(),
                agent_product_feed.csv_url(),
                agent_product_feed.schema_url(),
            ):
                self.assertIn(url, text)

    def test_the_search_only_nature_of_the_feed_is_stated_not_implied(self):
        self.assertIn("search-only", self.llms_text)
        self.assertIn("enable_checkout is false", self.full_text)

    def test_published_files_exist_and_parse(self):
        matrix = PAGES / app_decision_matrix.JSON_RELATIVE
        index = PAGES / agent_product_feed.INDEX_RELATIVE
        if not matrix.exists() or not index.exists():
            self.skipTest("surfaces not generated in this checkout")
        payload = json.loads(matrix.read_text(encoding="utf-8"))
        self.assertFalse(payload["is_ranking"])
        self.assertEqual(payload["app_count"], len(payload["rows"]))
        feed_index = json.loads(index.read_text(encoding="utf-8"))
        self.assertFalse(feed_index["enable_checkout"])
        lines = (
            (PAGES / agent_product_feed.FEED_RELATIVE)
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertEqual(feed_index["row_count"], len(lines))
        json.loads(lines[0])


if __name__ == "__main__":
    unittest.main()
