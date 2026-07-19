#!/usr/bin/env python3
"""Regression tests for the first-party publisher intent catalog."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import unittest
import unicodedata
from urllib.parse import parse_qs, urlparse


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import publisher_intent_catalog as catalog
from aeo_answers_i18n import require_translation_quality
from official_locales import OFFICIAL_LOCALES


def normalized_digits(value: str) -> str:
    result = ""
    for char in value:
        try:
            result += str(unicodedata.digit(char))
        except (TypeError, ValueError):
            continue
    return result


class PublisherIntentLocalizationTests(unittest.TestCase):
    def test_ui_localizations_cover_all_official_locales(self) -> None:
        payload = json.loads(catalog.I18N_PATH.read_text(encoding="utf-8"))
        localizations = catalog.load_ui_i18n()
        ordinary_english = (
            "first-party",
            "publisher",
            "locale",
            "locales",
            "live",
            "listing",
            "unlock",
            "flexible",
            "query",
            "queries",
            "search",
            "intent",
            "catalog",
            "decision",
            "context",
            "download",
            "records",
            "paid",
            "check",
            "current",
            "ranking",
            "rankings",
            "review",
            "reviews",
            "endorsement",
            "endorsements",
            "persona",
        )
        self.assertEqual(set(OFFICIAL_LOCALES), set(localizations))
        self.assertEqual(50, len(localizations))
        self.assertEqual(34, len(payload["strings"]))
        for locale, mapping in localizations.items():
            self.assertEqual(set(payload["strings"]), set(mapping))
            for source, target in mapping.items():
                self.assertEqual(target, target.strip())
                self.assertNotRegex(target, r"[\r\n]")
                for token in (
                    "Lumi Studio",
                    "iOS",
                    "App Store",
                    "Apple",
                    "JSON",
                    "JSONL",
                    "CSV",
                    "CC BY 4.0",
                ):
                    if token in source:
                        self.assertIn(token, target, (locale, source))
                digits = normalized_digits(target)
                for number in ("26", "50", "1300"):
                    if number in source.replace(",", ""):
                        self.assertIn(number, digits, (locale, source))
                if not locale.startswith("en-"):
                    for word in ordinary_english:
                        self.assertNotRegex(
                            target,
                            (
                                rf"(?i)(?<![A-Za-z])"
                                rf"{re.escape(word)}"
                                rf"(?![A-Za-z])"
                            ),
                            (locale, source),
                        )
            if not locale.startswith("en-"):
                long_sources = [
                    source
                    for source in payload["strings"]
                    if len(source) >= 12
                    and not source.startswith(("JSON,", "CC BY"))
                ]
                require_translation_quality(
                    long_sources,
                    {source: mapping[source] for source in long_sources},
                    "publisher-intent-ui",
                    locale,
                )

    def test_campaign_tokens_are_unique_and_app_store_safe(self) -> None:
        tokens = [catalog.campaign_token(locale) for locale in OFFICIAL_LOCALES]
        self.assertEqual(len(tokens), len(set(tokens)))
        for token in tokens:
            self.assertLessEqual(len(token), 30)
            self.assertRegex(token, r"^[a-z0-9_]+$")

    def test_dynamic_counts_preserve_localized_numerals(self) -> None:
        arabic_digits = str.maketrans("0123456789,", "٠١٢٣٤٥٦٧٨٩٬")
        record_count = f"{catalog.EXPECTED_RECORD_COUNT:,}".translate(
            arabic_digits
        )
        app_count = str(catalog.EXPECTED_APP_COUNT).translate(arabic_digits)
        self.assertEqual(
            f"{record_count} سجل: {app_count} تطبيقًا × ٥٠ إعدادًا.",
            catalog._replace_localized_number(
                catalog._replace_localized_number(
                    "١٬٣٠٠ سجل: ٢٦ تطبيقًا × ٥٠ إعدادًا.",
                    1300,
                    catalog.EXPECTED_RECORD_COUNT,
                ),
                26,
                catalog.EXPECTED_APP_COUNT,
            ),
        )


class PublisherIntentOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        possible_pages = [
            GEO / "pages",
            GEO.parents[1],
        ]
        cls.pages = next(
            (
                path
                for path in possible_pages
                if (
                    path
                    / "data"
                    / f"{catalog.SLUG}.json"
                ).exists()
            ),
            None,
        )
        if cls.pages is None:
            raise unittest.SkipTest("Generated Pages catalog is not present")
        cls.data_dir = cls.pages / "data"
        cls.payload = json.loads(
            (
                cls.data_dir
                / f"{catalog.SLUG}.json"
            ).read_text(encoding="utf-8")
        )
        cls.records = cls.payload["records"]
        cls.availability = catalog.load_storefront_availability(cls.pages)

    def test_records_cover_every_app_and_locale_truthfully(self) -> None:
        self.assertEqual(
            catalog.EXPECTED_APP_COUNT,
            self.payload["app_count"],
        )
        self.assertEqual(50, self.payload["locale_count"])
        self.assertEqual(
            catalog.EXPECTED_RECORD_COUNT,
            self.payload["record_count"],
        )
        self.assertEqual(list(OFFICIAL_LOCALES), self.payload["locales"])
        self.assertFalse(self.payload["measured_search_volume"])
        self.assertFalse(self.payload["is_ranking"])
        self.assertIn("Lumi Studio", self.payload["publisher_disclosure"])

        finder = json.loads(
            (
                self.data_dir
                / catalog.FINDER_DATASET
            ).read_text(encoding="utf-8")
        )
        expected_ids = {
            app["key"]: str(app["app_store_id"])
            for app in finder["apps"]
        }
        self.assertEqual(catalog.EXPECTED_APP_COUNT, len(expected_ids))
        per_app: dict[str, set[str]] = {
            key: set() for key in expected_ids
        }
        record_ids: set[str] = set()
        for record in self.records:
            record_ids.add(record["record_id"])
            key = record["app_key"]
            locale = record["locale"]
            per_app[key].add(locale)
            app_id = expected_ids[key]
            self.assertEqual(app_id, record["app_store_id"])
            self.assertEqual(
                f"https://apps.apple.com/app/id{app_id}",
                record["canonical_app_store_url"],
            )
            parsed = urlparse(record["app_store_url"])
            self.assertEqual("apps.apple.com", parsed.netloc)
            expected_store = catalog.verified_app_store_url(
                record["canonical_app_store_url"],
                locale,
                self.availability,
            )
            self.assertEqual(urlparse(expected_store).path, parsed.path)
            self.assertEqual(
                [catalog.campaign_token(locale)],
                parse_qs(parsed.query).get("ct"),
            )
            self.assertNotIn("pt", parse_qs(parsed.query))
            self.assertFalse(record["measured_search_volume"])
            self.assertFalse(record["is_ranking"])
            self.assertTrue(record["verified_live"])
            self.assertEqual(
                "publisher_authored_editorially_localized",
                record["query_origin"],
            )
            self.assertGreaterEqual(
                len(record["publisher_disclosure"]),
                20,
            )
            self.assertNotRegex(
                " ".join(
                    str(record[field])
                    for field in (
                        "app_name",
                        "publisher_query",
                        "decision_context",
                        "publisher_disclosure",
                    )
                ),
                r"[\r\n]",
            )
            guide_path = self.pages / urlparse(
                record["canonical_guide_url"]
            ).path.removeprefix("/ios-app-guide/")
            self.assertTrue(guide_path.is_file(), guide_path)
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(record_ids))
        for locales in per_app.values():
            self.assertEqual(set(OFFICIAL_LOCALES), locales)

    def test_json_jsonl_and_csv_have_the_same_records(self) -> None:
        jsonl_records = [
            json.loads(line)
            for line in (
                self.data_dir / f"{catalog.SLUG}.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertEqual(self.records, jsonl_records)

        with (
            self.data_dir / f"{catalog.SLUG}.csv"
        ).open(encoding="utf-8", newline="") as handle:
            csv_records = list(csv.DictReader(handle))
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(csv_records))
        self.assertEqual(
            [record["record_id"] for record in self.records],
            [record["record_id"] for record in csv_records],
        )
        for source, exported in zip(self.records, csv_records):
            for field in catalog.CSV_FIELDS:
                expected = (
                    str(source[field]).lower()
                    if isinstance(source[field], bool)
                    else str(source[field])
                )
                self.assertEqual(expected, exported[field])

    def test_schema_declares_non_ranking_non_measured_contract(self) -> None:
        from jsonschema import Draft202012Validator, FormatChecker

        schema = json.loads(
            (
                self.data_dir / f"{catalog.SLUG}.schema.json"
            ).read_text(encoding="utf-8")
        )
        properties = schema["properties"]
        self.assertEqual(False, properties["measured_search_volume"]["const"])
        self.assertEqual(False, properties["is_ranking"]["const"])
        self.assertEqual(
            catalog.EXPECTED_APP_COUNT,
            properties["app_count"]["const"],
        )
        self.assertEqual(50, properties["locale_count"]["const"])
        self.assertEqual(
            catalog.EXPECTED_RECORD_COUNT,
            properties["record_count"]["const"],
        )
        record_properties = properties["records"]["items"]["properties"]
        self.assertEqual(
            False,
            record_properties["measured_search_volume"]["const"],
        )
        self.assertEqual(False, record_properties["is_ranking"]["const"])
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(self.payload)

    def test_root_and_all_localized_landings_are_complete(self) -> None:
        pages = [
            ("en", self.data_dir / f"{catalog.SLUG}.html"),
            *[
                (
                    locale,
                    self.pages
                    / locale
                    / "data"
                    / f"{catalog.SLUG}.html",
                )
                for locale in OFFICIAL_LOCALES
            ],
        ]
        self.assertEqual(51, len(pages))
        for locale, path in pages:
            source = path.read_text(encoding="utf-8")
            self.assertIn('white-space:nowrap', source)
            self.assertEqual(
                52,
                len(re.findall(r'<link rel="alternate" hreflang=', source)),
            )
            for media_type in (
                "application/atom+xml",
                "application/rss+xml",
                "application/feed+json",
            ):
                self.assertIn(
                    f'<link rel="alternate" type="{media_type}"',
                    source,
                )
            table_body = re.search(
                r"<tbody>(.*?)</tbody>",
                source,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(table_body)
            self.assertEqual(
                catalog.EXPECTED_APP_COUNT,
                table_body.group(1).count("<tr>"),
            )
            store_urls = re.findall(
                r'href="(https://apps\.apple\.com/'
                r'(?:[a-z]{2}/)?app/id[0-9]+\?ct=[^"]+)"',
                table_body.group(1),
            )
            self.assertEqual(catalog.EXPECTED_APP_COUNT, len(store_urls))
            expected_campaign = catalog.campaign_token(
                "en-US" if locale == "en" else locale
            )
            self.assertTrue(
                all(
                    parse_qs(urlparse(url).query).get("ct")
                    == [expected_campaign]
                    for url in store_urls
                )
            )
            if locale in catalog.RTL_LOCALES:
                self.assertRegex(
                    source,
                    rf'<html lang="{re.escape(locale)}" dir="rtl">',
                )
            schema_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                source,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(schema_match)
            schema = json.loads(html.unescape(schema_match.group(1)))
            self.assertEqual("Dataset", schema["@type"])
            self.assertEqual("Lumi Studio", schema["creator"]["name"])
            mcp = schema["subjectOf"]
            self.assertEqual("SoftwareApplication", mcp["@type"])
            self.assertEqual(catalog.MCP_REPOSITORY_URL, mcp["url"])
            self.assertEqual(catalog.MCP_REGISTRY_URL, mcp["sameAs"])
            self.assertEqual(catalog.MCP_BUNDLE_URL, mcp["downloadUrl"])
            self.assertIn(
                f'href="{catalog.MCP_REGISTRY_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_REPOSITORY_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_BUNDLE_URL}"',
                source,
            )
            self.assertEqual(3, len(schema["distribution"]))
            self.assertEqual(
                {
                    "application/json",
                    "application/x-ndjson",
                    "text/csv",
                },
                {
                    distribution["encodingFormat"]
                    for distribution in schema["distribution"]
                },
            )

    def test_data_hub_and_sitemap_discover_every_landing(self) -> None:
        index = (self.data_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn(catalog.NAME, index)
        self.assertIn(f"{catalog.SLUG}.jsonl", index)
        self.assertIn(f"{catalog.SLUG}.csv", index)
        self.assertIn("white-space:nowrap", index)
        sitemap = (self.pages / "sitemap_data.xml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(51, sitemap.count(f"/{catalog.SLUG}.html"))
        feed = json.loads(
            (self.pages / "feed.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            f"{catalog.SITE}/data/{catalog.SLUG}.html",
            {item["url"] for item in feed["items"]},
        )
        self.assertIn(
            "publisher-disclosed",
            feed["description"],
        )
        for filename in ("llms.txt", "llms-full.txt"):
            llms = (self.pages / filename).read_text(encoding="utf-8")
            self.assertIn(f"{catalog.SLUG}.json", llms)
            self.assertIn(f"{catalog.SLUG}.jsonl", llms)
            self.assertIn(f"{catalog.SLUG}.csv", llms)
            self.assertIn(f"{catalog.SLUG}.schema.json", llms)

    def test_generated_outputs_are_content_stable(self) -> None:
        digest = hashlib.sha256(
            json.dumps(
                self.records,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(digest, self.payload["content_digest"])
        rebuilt, _ = catalog.build_records(self.pages)
        self.assertEqual(self.records, rebuilt)


if __name__ == "__main__":
    unittest.main()
