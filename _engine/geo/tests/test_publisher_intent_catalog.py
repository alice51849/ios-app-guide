#!/usr/bin/env python3
"""Regression tests for the first-party publisher intent catalog."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from unittest import mock
from urllib.parse import urlparse


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

    def test_live_mcp_distribution_is_exact_and_hash_verified(self) -> None:
        version = "9.8.7"
        mcpb = b"verified mcpb"
        npx = b"verified npx"
        mcpb_sha256 = hashlib.sha256(mcpb).hexdigest()
        npx_sha256 = hashlib.sha256(npx).hexdigest()
        release_base = (
            f"{catalog.MCP_REPOSITORY_URL}/releases/download/v{version}"
        )
        registry = {
            "server": {
                "name": catalog.MCP_SERVER_NAME,
                "version": version,
                "repository": {
                    "url": catalog.MCP_REPOSITORY_URL,
                    "source": "github",
                },
                "packages": [
                    {
                        "registryType": "mcpb",
                        "identifier": (
                            f"{release_base}/lumi-app-finder.mcpb"
                        ),
                        "fileSha256": mcpb_sha256,
                        "transport": {"type": "stdio"},
                    }
                ],
            },
            "_meta": {
                "io.modelcontextprotocol.registry/official": {
                    "status": "active",
                    "isLatest": True,
                }
            },
        }
        checksums = (
            f"{mcpb_sha256}  lumi-app-finder.mcpb\n"
            f"{npx_sha256}  lumi-app-finder-npx.tgz\n"
        ).encode("ascii")
        responses = {
            catalog.MCP_REGISTRY_LATEST_URL: json.dumps(
                registry
            ).encode("utf-8"),
            f"{release_base}/SHA256SUMS": checksums,
            f"{release_base}/lumi-app-finder.mcpb": mcpb,
            f"{release_base}/lumi-app-finder-npx.tgz": npx,
        }
        original = dict(catalog.MCP_DISTRIBUTION)
        self.addCleanup(catalog._configure_mcp_distribution, original)
        with tempfile.TemporaryDirectory() as directory:
            state_path = (
                Path(directory)
                / "data"
                / catalog.MCP_DISTRIBUTION_STATE_FILENAME
            )
            state_path.parent.mkdir(parents=True)
            state_path.write_text('{"truncated":', encoding="utf-8")
            with mock.patch.object(
                catalog,
                "_fetch_bytes",
                side_effect=lambda url, _limit: responses[url],
            ) as fetch:
                distribution = catalog.refresh_live_mcp_distribution(
                    Path(directory)
                )
            self.assertEqual(4, fetch.call_count)
            self.assertEqual(version, distribution["version"])
            self.assertEqual(
                f"{catalog.MCP_REGISTRY_BASE_URL}/{version}",
                distribution["registry_url"],
            )
            self.assertEqual(npx_sha256, distribution["npx_sha256"])
            self.assertEqual(version, catalog.MCP_VERSION)
            self.assertNotIn("/latest/", catalog.MCP_NPX_URL)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(distribution, state)
            self.assertEqual(
                [],
                list(
                    state_path.parent.glob(
                        f".{state_path.name}.*.tmp"
                    )
                ),
            )
            responses[
                f"{release_base}/lumi-app-finder-npx.tgz"
            ] = b"tampered"
            with mock.patch.object(
                catalog,
                "_fetch_bytes",
                side_effect=lambda url, _limit: responses[url],
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "asset hash mismatch",
                ):
                    catalog.refresh_live_mcp_distribution(Path(directory))
            self.assertEqual(
                distribution,
                json.loads(state_path.read_text(encoding="utf-8")),
            )

    def test_frozen_mcp_distribution_rejects_corrupt_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "data"
                / catalog.MCP_DISTRIBUTION_STATE_FILENAME
            )
            path.parent.mkdir(parents=True)
            path.write_text('{"truncated":', encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "run publisher_intent_catalog.py first",
            ):
                catalog.use_frozen_mcp_distribution(Path(directory))


class PublisherIntentOutputTests(unittest.TestCase):
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
            self.assertEqual("", parsed.query)
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

    def test_mcp_distribution_state_matches_exact_generated_links(self) -> None:
        state = json.loads(
            (
                self.data_dir
                / catalog.MCP_DISTRIBUTION_STATE_FILENAME
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(catalog.MCP_DISTRIBUTION, state)
        self.assertEqual(catalog.MCP_VERSION, state["version"])
        self.assertEqual(catalog.MCP_REGISTRY_URL, state["registry_url"])
        self.assertEqual(catalog.MCP_BUNDLE_URL, state["mcpb_url"])
        self.assertEqual(catalog.MCP_NPX_URL, state["npx_url"])
        self.assertNotIn("/latest/", state["mcpb_url"])
        self.assertNotIn("/latest/", state["npx_url"])

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

    def test_croissant_metadata_exposes_all_locales_and_direct_store_fields(
        self,
    ) -> None:
        path = self.data_dir / catalog.CROISSANT_FILENAME
        metadata = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(catalog.CROISSANT_CONTEXT, metadata["@context"])
        self.assertEqual("sc:Dataset", metadata["@type"])
        self.assertEqual(catalog.CROISSANT_SPEC, metadata["conformsTo"])
        self.assertEqual(set(OFFICIAL_LOCALES), set(metadata["name"]))
        self.assertEqual(set(OFFICIAL_LOCALES), set(metadata["description"]))
        self.assertEqual(list(OFFICIAL_LOCALES), metadata["inLanguage"])
        self.assertFalse(metadata["isLiveDataset"])
        self.assertTrue(metadata["isAccessibleForFree"])

        distributions = {
            item["@id"]: item for item in metadata["distribution"]
        }
        expected_files = {
            f"{catalog.SLUG}.json",
            f"{catalog.SLUG}.jsonl",
            f"{catalog.SLUG}.csv",
        }
        self.assertEqual(expected_files, set(distributions))
        for filename, distribution in distributions.items():
            source = self.data_dir / filename
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(),
                distribution["sha256"],
            )
            self.assertEqual(
                f"{source.stat().st_size} B",
                distribution["contentSize"],
            )

        record_set = metadata["recordSet"][0]
        self.assertEqual("publisher_intents", record_set["@id"])
        self.assertEqual(
            {"@id": "publisher_intents/record_id"},
            record_set["key"],
        )
        expected_examples = [
            {
                f"publisher_intents/{field}": record[field]
                for field in catalog.CSV_FIELDS
            }
            for record in self.records[:2]
        ]
        self.assertEqual(expected_examples, record_set["examples"])
        self.assertNotIn(
            "publisher_intents/app_store_cta_label",
            record_set["examples"][0],
        )
        fields = {
            field["name"]: field for field in record_set["field"]
        }
        self.assertEqual(set(catalog.CSV_FIELDS), set(fields))
        self.assertEqual(
            "sc:URL",
            fields["app_store_url"]["dataType"],
        )
        self.assertEqual(
            "https://schema.org/downloadUrl",
            fields["app_store_url"]["equivalentProperty"],
        )
        for field in fields.values():
            self.assertEqual(
                {"@id": f"{catalog.SLUG}.csv"},
                field["source"]["fileObject"],
            )
            self.assertEqual(
                {"column": field["name"]},
                field["source"]["extract"],
            )

    @unittest.skipUnless(
        importlib.util.find_spec("mlcroissant"),
        "Official Croissant validation dependency is installed in CI",
    )
    def test_croissant_loads_all_records_with_official_reader(self) -> None:
        import mlcroissant

        metadata_path = self.data_dir / catalog.CROISSANT_FILENAME
        dataset = mlcroissant.Dataset(
            jsonld=metadata_path,
            mapping={
                f"{catalog.SLUG}.csv": (
                    self.data_dir / f"{catalog.SLUG}.csv"
                ),
            },
        )
        loaded = list(dataset.records(record_set="publisher_intents"))
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(loaded))
        self.assertEqual(
            {
                f"publisher_intents/{field}"
                for field in catalog.CSV_FIELDS
            },
            set(loaded[0]),
        )
        validator = Path(sys.executable).with_name("mlcroissant")
        result = subprocess.run(
            [
                str(validator),
                "validate",
                "--jsonld",
                str(metadata_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            result.stdout + result.stderr,
        )

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
                r'(?:[a-z]{2}/)?app/id[0-9]+)"',
                table_body.group(1),
            )
            self.assertEqual(catalog.EXPECTED_APP_COUNT, len(store_urls))
            self.assertTrue(
                all(not urlparse(url).query for url in store_urls)
            )
            visual_locale = "" if locale == "en" else f"/{locale}"
            self.assertEqual(
                1,
                source.count(
                    f'href="{catalog.SITE}{visual_locale}/visuals/"'
                ),
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
            self.assertEqual(catalog.CROISSANT_SPEC, schema["conformsTo"])
            self.assertEqual("Lumi Studio", schema["creator"]["name"])
            mcp = schema["subjectOf"]
            self.assertEqual("SoftwareApplication", mcp["@type"])
            self.assertEqual(catalog.MCP_REPOSITORY_URL, mcp["url"])
            self.assertEqual(catalog.MCP_REGISTRY_URL, mcp["sameAs"])
            self.assertEqual(catalog.MCP_BUNDLE_URL, mcp["downloadUrl"])
            self.assertEqual(catalog.MCP_NPX_URL, mcp["installUrl"])
            self.assertEqual(catalog.MCP_VERSION, mcp["softwareVersion"])
            self.assertEqual(
                {
                    "Install in VS Code": catalog.MCP_VSCODE_INSTALL_URL,
                    "Install in Cursor": catalog.MCP_CURSOR_INSTALL_URL,
                },
                {
                    action["name"]: action["target"]
                    for action in mcp["potentialAction"]
                    if action["@type"] == "InstallAction"
                },
            )
            self.assertIn(
                f'href="{html.escape(catalog.MCP_REGISTRY_URL, quote=True)}"',
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
            self.assertIn(
                (
                    f'href="{html.escape(catalog.MCP_VSCODE_INSTALL_URL, quote=True)}"'
                ),
                source,
            )
            self.assertIn(
                (
                    f'href="{html.escape(catalog.MCP_CURSOR_INSTALL_URL, quote=True)}"'
                ),
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_CHECKSUMS_URL}"',
                source,
            )
            self.assertEqual(4, len(schema["distribution"]))
            self.assertEqual(
                {
                    "application/json",
                    "application/x-ndjson",
                    "text/csv",
                    catalog.CROISSANT_MEDIA_TYPE,
                },
                {
                    distribution["encodingFormat"]
                    for distribution in schema["distribution"]
                },
            )
            self.assertIn(
                f'rel="describedby" type="application/ld+json" '
                f'href="{catalog.CROISSANT_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.CROISSANT_URL}">Croissant 1.1</a>',
                source,
            )

    def test_data_hub_and_sitemap_discover_every_landing(self) -> None:
        index = (self.data_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn(catalog.NAME, index)
        self.assertIn(f"{catalog.SLUG}.jsonl", index)
        self.assertIn(f"{catalog.SLUG}.csv", index)
        self.assertIn(catalog.CROISSANT_FILENAME, index)
        self.assertIn("white-space:nowrap", index)
        sitemap = (self.pages / "sitemap_data.xml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(51, sitemap.count(f"/{catalog.SLUG}.html"))
        self.assertIn(catalog.CROISSANT_URL, sitemap)
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
            self.assertIn(catalog.CROISSANT_FILENAME, llms)

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
