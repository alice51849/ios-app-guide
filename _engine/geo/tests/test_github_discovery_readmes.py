#!/usr/bin/env python3
"""Regression tests for GitHub-native localized App discovery READMEs."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import parse_qs, urlparse


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_github_discovery_readmes as discovery
from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog as catalog


class GitHubDiscoveryContractTests(unittest.TestCase):
    def test_campaign_tokens_are_unique_and_app_store_safe(self) -> None:
        tokens = [
            discovery.campaign_token(locale)
            for locale in OFFICIAL_LOCALES
        ]
        self.assertEqual(len(tokens), len(set(tokens)))
        for token in tokens:
            self.assertLessEqual(len(token), 30)
            self.assertRegex(token, r"^[a-z0-9_]+$")


class GitHubDiscoveryOutputTests(unittest.TestCase):
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
        cls.payload = json.loads(
            (
                cls.pages
                / "data"
                / f"{catalog.SLUG}.json"
            ).read_text(encoding="utf-8")
        )
        cls.records = discovery.validate_dataset(cls.payload)

    def test_root_and_all_locale_readmes_exist(self) -> None:
        expected = {
            self.pages / "README.md",
            *{
                self.pages / locale / "README.md"
                for locale in OFFICIAL_LOCALES
            },
        }
        self.assertTrue(all(path.is_file() for path in expected))
        self.assertEqual(
            {path for path in self.pages.glob("*/README.md")},
            expected - {self.pages / "README.md"},
        )

    def test_every_readme_exposes_the_public_mcp_distribution(self) -> None:
        paths = [
            self.pages / "README.md",
            *[
                self.pages / locale / "README.md"
                for locale in OFFICIAL_LOCALES
            ],
        ]
        for path in paths:
            with self.subTest(path=path):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(
                    1,
                    source.count(
                        f"[MCP Registry]({discovery.MCP_REGISTRY_URL})"
                    ),
                )
                self.assertEqual(
                    1,
                    source.count(f"[GitHub]({discovery.MCP_REPOSITORY_URL})"),
                )
                self.assertEqual(
                    1,
                    source.count(f"[MCPB]({discovery.MCP_BUNDLE_URL})"),
                )

    def test_every_readme_has_complete_native_buyer_intent_rows(self) -> None:
        for locale in OFFICIAL_LOCALES:
            with self.subTest(locale=locale):
                source = (
                    self.pages / locale / "README.md"
                ).read_text(encoding="utf-8")
                records = [
                    record
                    for record in self.records
                    if record["locale"] == locale
                ]
                self.assertTrue(source.startswith(discovery.GENERATED_MARKER))
                table_lines = [
                    line for line in source.splitlines() if line.startswith("| ")
                ]
                self.assertEqual(
                    catalog.EXPECTED_APP_COUNT + 2,
                    len(table_lines),
                )
                for record in records:
                    self.assertIn(
                        discovery._markdown_text(record["app_name"]),
                        source,
                    )
                    self.assertIn(
                        discovery._markdown_text(record["publisher_query"]),
                        source,
                    )
                    self.assertIn(
                        discovery._markdown_text(record["decision_context"]),
                        source,
                    )
                for option in OFFICIAL_LOCALES:
                    if option == locale:
                        self.assertIn(f"**{option}**", source)
                    else:
                        self.assertIn(f"[{option}](../{option}/)", source)

    def test_store_links_preserve_verified_routes_and_use_github_campaigns(
        self,
    ) -> None:
        source_by_pair = {
            (record["locale"], record["app_store_id"]): record
            for record in self.records
        }
        seen_pairs = set()
        generic = 0
        for locale in OFFICIAL_LOCALES:
            source = (
                self.pages / locale / "README.md"
            ).read_text(encoding="utf-8")
            urls = re.findall(
                r"https://apps\.apple\.com/"
                r"(?:[a-z]{2}/)?app/id[0-9]{9,12}\?[^)\s]+",
                source,
            )
            self.assertEqual(catalog.EXPECTED_APP_COUNT, len(urls))
            for url in urls:
                parsed = urlparse(url)
                app_id_match = re.search(r"/app/id([0-9]{9,12})$", parsed.path)
                self.assertIsNotNone(app_id_match)
                app_id = app_id_match.group(1)
                record = source_by_pair[(locale, app_id)]
                expected_path = urlparse(record["app_store_url"]).path
                self.assertEqual(expected_path, parsed.path)
                self.assertEqual(
                    [discovery.campaign_token(locale)],
                    parse_qs(parsed.query).get("ct"),
                )
                self.assertEqual(
                    parse_qs(urlparse(record["app_store_url"]).query).get("pt"),
                    parse_qs(parsed.query).get("pt"),
                )
                generic += parsed.path == f"/app/id{app_id}"
                seen_pairs.add((locale, app_id))
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(seen_pairs))
        self.assertEqual(
            sum(
                urlparse(record["app_store_url"]).path
                == f"/app/id{record['app_store_id']}"
                for record in self.records
            ),
            generic,
        )

    def test_root_readme_is_an_english_full_portfolio_landing(self) -> None:
        source = (self.pages / "README.md").read_text(encoding="utf-8")
        self.assertTrue(source.startswith(discovery.GENERATED_MARKER))
        self.assertEqual(
            catalog.EXPECTED_APP_COUNT + 2,
            len(
                [
                    line
                    for line in source.splitlines()
                    if line.startswith("| ")
                ]
            ),
        )
        for locale in OFFICIAL_LOCALES:
            self.assertIn(f"[{locale}](./{locale}/)", source)
        for record in self.records:
            if record["locale"] == "en-US":
                self.assertIn(record["publisher_query"], source)

    def test_generation_is_idempotent(self) -> None:
        self.assertEqual((), discovery.build(self.pages))


if __name__ == "__main__":
    unittest.main()
