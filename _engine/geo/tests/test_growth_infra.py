#!/usr/bin/env python3
"""Regression tests for App Store availability and AI outreach generation."""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
if GEO not in sys.path:
    sys.path.insert(0, GEO)

import aeo_answers
import aeo_answers_i18n
import aeo_guide_i18n
import aeo_pages
import add_related_tools
import answer_deep
import appstore_live
import build_pages
import build_pages_i18n
import cleanup_localized_assets
import family_travel_dataset
import family_travel_mission_cards
import family_travel_observation_passport
import family_travel_opds_catalog
import family_travel_ro_crate
import family_travel_static_api
import gen_app_catalog
import gen_calculator
import gen_cost_compare
import gen_data_hub
import gen_feed
import gen_hubs
import gen_llms
import gen_roundups
import indexnow_submit
import outreach_scorecard
import prioritize_trip_planet_resources
import static_api_catalog
import zhuyin_grandparent_call_kit
import zhuyin_grade1_guide
import zhuyin_grade1_summer_calendar
import zhuyin_anki_deck
import zhuyin_croissant_dataset
import zhuyin_frictionless_package
import zhuyin_heritage_lesson_plan
import zhuyin_library_storytime_kit
import zhuyin_parent_teacher_handoff_kit
import zhuyin_picture_book_club_kit
import zhuyin_readiness_tool
import zhuyin_skos_vocabulary
import zhuyin_static_api
from videogen.registry import (  # noqa: E402
    APPS,
    VALID_PURCHASE_MODELS,
    classify_purchase_model,
)


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
    def test_answer_style_falls_back_when_the_named_template_is_pruned(self):
        with tempfile.TemporaryDirectory() as directory:
            answers = Path(directory)
            fallback = answers / "available-answer.html"
            fallback.write_text(
                "<html><style>\nbody{color:#123}\n</style></html>",
                encoding="utf-8",
            )
            with mock.patch.object(
                aeo_answers, "ANSWERS_DIR", answers
            ), mock.patch.object(
                aeo_answers, "TEMPLATE", answers / "missing-answer.html"
            ):
                self.assertEqual("body{color:#123}", aeo_answers.extract_style())

    def test_atom_feed_discovers_new_free_tools_and_open_data(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_feed, "PAGES", directory
        ):
            for subdir in ("answers", "guides", "alternatives", "tools", "data"):
                path = Path(directory) / subdir
                path.mkdir()
                (path / "index.html").write_text("<html></html>", encoding="utf-8")
            tool = Path(directory) / "tools" / "private-travel-tool.html"
            tool.write_text(
                '<title>Private Travel Tool</title>'
                '<meta name="description" content="Private printable prompts.">',
                encoding="utf-8",
            )
            dataset = Path(directory) / "data" / "family-travel-missions.html"
            dataset.write_text(
                '<title>Family Travel Missions</title>'
                '<meta name="description" content="Bilingual open data.">',
                encoding="utf-8",
            )
            api_docs = (
                Path(directory)
                / "api"
                / "v1"
                / "family-travel-missions"
                / "index.html"
            )
            api_docs.parent.mkdir(parents=True)
            api_docs.write_text(
                '<title>Family Travel API</title>'
                '<meta name="description" content="Versioned static API.">'
                '<script type="application/ld+json">'
                '{"dateModified":"2026-07-11"}</script>',
                encoding="utf-8",
            )
            items = gen_feed.collect()
        self.assertTrue(
            any(url.endswith("/tools/private-travel-tool.html") for _, url, _ in items)
        )
        self.assertTrue(
            any(url.endswith("/data/family-travel-missions.html") for _, url, _ in items)
        )
        self.assertTrue(
            any(url.endswith("/api/v1/family-travel-missions/") for _, url, _ in items)
        )

    def test_atom_feed_uses_semantic_date_and_avoids_unchanged_rewrites(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text(
                '<script type="application/ld+json">'
                '{"dateModified":"2026-07-11"}</script>',
                encoding="utf-8",
            )
            timestamp = gen_feed._content_modified(str(page), {})
            self.assertEqual("2026-07-11T00:00:00Z", gen_feed.iso(timestamp))
            output = Path(directory) / "feed.xml"
            self.assertTrue(gen_feed._write_if_changed(str(output), "stable"))
            modified = output.stat().st_mtime_ns
            self.assertFalse(gen_feed._write_if_changed(str(output), "stable"))
            self.assertEqual(modified, output.stat().st_mtime_ns)

    def test_data_hub_preserves_date_until_dataset_content_changes(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_data_hub, "DATA", directory
        ):
            existing = {"dateModified": "2026-07-10", "records": [1]}
            Path(directory, "sample.json").write_text(
                json.dumps(existing), encoding="utf-8"
            )
            unchanged = gen_data_hub.preserve_modified_date(
                "sample", {"dateModified": "2026-07-11", "records": [1]}
            )
            changed = gen_data_hub.preserve_modified_date(
                "sample", {"dateModified": "2026-07-11", "records": [1, 2]}
            )
            self.assertEqual("2026-07-10", unchanged["dateModified"])
            self.assertEqual("2026-07-11", changed["dateModified"])

    def test_family_travel_dataset_matches_card_generator_source(self):
        dataset = family_travel_dataset.load_dataset()
        self.assertEqual(12, len(dataset["scenarios"]))
        self.assertEqual(84, sum(len(item["targets"]) for item in dataset["scenarios"]))
        self.assertEqual(3, len(dataset["participationModes"]))
        for locale in ("en", "zh-Hant"):
            source_scenarios = family_travel_mission_cards.SCENARIOS[locale]
            self.assertEqual(
                [item["id"] for item in source_scenarios],
                [item["id"] for item in dataset["scenarios"]],
            )
            for source, published in zip(source_scenarios, dataset["scenarios"]):
                self.assertEqual(source["name"], published["name"][locale])
                self.assertEqual(source["boundary"], published["safetyBoundary"][locale])
                self.assertEqual(
                    list(source["targets"]),
                    [target["text"][locale] for target in published["targets"]],
                )
                self.assertTrue(published["stationaryRequired"])
                self.assertFalse(published["photoTaskAllowed"])
                self.assertFalse(published["driverInteractionAllowed"])
                self.assertTrue(published["adultSupervisionRequired"])
                self.assertTrue(published["skipAllowed"])
            source_modes = family_travel_mission_cards.COPY[locale]["styles"]
            for source, published in zip(source_modes, dataset["participationModes"]):
                self.assertEqual(source["id"], published["id"])
                self.assertEqual(source["name"], published["name"][locale])
                self.assertEqual(source["template"], published["promptTemplate"][locale])
                self.assertIsNone(published["ageBand"])
                self.assertIsNone(published["abilityLevel"])

    def test_family_travel_dataset_distributions_are_symmetric_and_unique(self):
        dataset = family_travel_dataset.load_dataset()
        source = family_travel_dataset.SOURCE_DIR
        schema = json.loads(
            (source / "family-travel-missions.schema.json").read_text(encoding="utf-8")
        )
        csvw = json.loads(
            (source / "family-travel-missions.csv-metadata.json").read_text(
                encoding="utf-8"
            )
        )
        dcat = json.loads(
            (source / "family-travel-missions.dcat.jsonld").read_text(
                encoding="utf-8"
            )
        )
        with (source / "family-travel-missions.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            records = list(csv.DictReader(handle))
        self.assertEqual(dataset["scope"]["flatRecordCount"], len(records))
        keys = {
            (
                row["scenario_id"],
                row["target_id"],
                row["participation_mode_id"],
            )
            for row in records
        }
        self.assertEqual(252, len(keys))
        self.assertTrue(
            all(row["photo_task_allowed"] == "false" for row in records)
        )
        self.assertTrue(
            all(row["driver_interaction_allowed"] == "false" for row in records)
        )
        self.assertEqual(
            list(records[0]),
            [column["name"] for column in csvw["tableSchema"]["columns"]],
        )
        self.assertEqual(
            ["scenario_id", "target_id", "participation_mode_id"],
            csvw["tableSchema"]["primaryKey"],
        )
        csvw_columns = {
            column["name"]: column for column in csvw["tableSchema"]["columns"]
        }
        self.assertEqual("en", csvw_columns["prompt_en"]["lang"])
        self.assertEqual("zh-Hant", csvw_columns["prompt_zh_hant"]["lang"])
        self.assertEqual("dcat:Dataset", dcat["@type"])
        self.assertEqual(
            {
                "https://www.iana.org/assignments/media-types/application/json",
                "https://www.iana.org/assignments/media-types/text/csv",
            },
            {
                item["dcat:mediaType"]["@id"]
                for item in dcat["dcat:distribution"]
            },
        )
        scenario_schema = schema["$defs"]["scenario"]["properties"]
        self.assertFalse(scenario_schema["photoTaskAllowed"]["const"])
        self.assertFalse(scenario_schema["driverInteractionAllowed"]["const"])

    def test_family_travel_dataset_page_gates_optional_app_layer(self):
        dataset = family_travel_dataset.load_dataset()
        for locale in ("en", "zh-Hant"):
            private_page = family_travel_dataset.render_page(
                dataset, locale, app_public=False
            )
            self.assertIn('"@type":"Dataset"', private_page)
            self.assertEqual(12, private_page.count('<details class="scenario">'))
            self.assertIn('hreflang="en"', private_page)
            self.assertIn('hreflang="zh-Hant"', private_page)
            self.assertIn("family-travel-missions.csv", private_page)
            self.assertIn("family-travel-missions.schema.json", private_page)
            self.assertIn("family-travel-missions.csv-metadata.json", private_page)
            self.assertIn("family-travel-missions.dcat.jsonld", private_page)
            self.assertIn("/api/v1/family-travel-missions/", private_page)
            expected_passport = (
                "/zh-Hant/tools/family-travel-observation-passport.html"
                if locale == "zh-Hant"
                else "/tools/family-travel-observation-passport.html"
            )
            self.assertIn(expected_passport, private_page)
            self.assertNotIn("apps.apple.com", private_page)
            self.assertNotIn('"@type":"SoftwareApplication"', private_page)
        public_page = family_travel_dataset.render_page(
            dataset, "en", app_public=True
        )
        self.assertIn(f"id{family_travel_mission_cards.APP_ID}", public_page)
        self.assertIn('"@type":"SoftwareApplication"', public_page)
        self.assertNotIn('"offers"', public_page)
        self.assertLess(
            public_page.index("Free companion resources"),
            public_page.index("Optional digital travel layer"),
        )

    def test_family_travel_dataset_builds_bilingual_pages_files_and_sitemap(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            slug = family_travel_dataset.build(pages, app_public=False)
            self.assertEqual(family_travel_dataset.SLUG, slug)
            for filename in family_travel_dataset.FILES:
                self.assertEqual(
                    (family_travel_dataset.SOURCE_DIR / filename).read_bytes(),
                    (pages / "data" / filename).read_bytes(),
                )
            self.assertTrue((pages / "data" / f"{slug}.html").exists())
            self.assertTrue(
                (pages / "zh-Hant" / "data" / f"{slug}.html").exists()
            )
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (
                    pages / "data" / f"{slug}.html",
                    pages / "zh-Hant" / "data" / f"{slug}.html",
                    *(pages / "data" / filename for filename in family_travel_dataset.FILES),
                )
            }
            family_travel_dataset.build(pages, app_public=False)
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in mtimes}
            )
            with mock.patch.object(
                gen_data_hub, "PAGES", str(pages)
            ), mock.patch.object(gen_data_hub, "DATA", str(pages / "data")):
                urls = gen_data_hub.build_sitemap(
                    [{"slug": slug, "localized": True}]
                )
            self.assertEqual(
                [
                    f"{gen_data_hub.SITE}/data/",
                    f"{gen_data_hub.SITE}/data/{slug}.html",
                    f"{gen_data_hub.SITE}/zh-Hant/data/{slug}.html",
                ],
                urls,
            )

    def test_family_travel_static_api_matches_canonical_dataset(self):
        dataset = family_travel_static_api.load_dataset()
        index = family_travel_static_api.api_index(dataset)
        scenarios = {
            scenario["id"]: family_travel_static_api.scenario_payload(
                dataset, scenario
            )
            for scenario in dataset["scenarios"]
        }
        openapi = family_travel_static_api.openapi_document(dataset)
        canonical_schema = json.loads(
            (
                family_travel_static_api.SOURCE_DIR
                / "family-travel-missions.schema.json"
            ).read_text(encoding="utf-8")
        )
        index_schema = family_travel_static_api.index_schema(
            dataset, canonical_schema
        )
        scenario_schema = family_travel_static_api.scenario_schema(
            dataset, canonical_schema
        )
        family_travel_static_api.validate_artifacts(
            dataset,
            index,
            scenarios,
            openapi,
            index_schema,
            scenario_schema,
        )
        self.assertEqual(12, len(index["scenarios"]))
        self.assertEqual(12, len(scenarios))
        self.assertEqual(13, len(openapi["paths"]))
        self.assertEqual("3.1.0", openapi["openapi"])
        self.assertEqual([], openapi["security"])
        for payload in scenarios.values():
            self.assertEqual(7, len(payload["scenario"]["targets"]))
            self.assertEqual(3, len(payload["participationModes"]))
        encoded = json.dumps(
            {"index": index, "scenarios": scenarios, "openapi": openapi}
        )
        self.assertNotIn("apps.apple.com", encoded)
        self.assertNotIn("SoftwareApplication", encoded)
        self.assertNotIn(family_travel_static_api.APP_NAME, encoded)
        contaminated = copy.deepcopy(scenarios)
        contaminated["airport"]["scenario"]["targets"][0]["text"][
            "en"
        ] = "Lumi Trip Planet id6787193643"
        with self.assertRaises(ValueError):
            family_travel_static_api.validate_artifacts(
                dataset,
                index,
                contaminated,
                openapi,
                index_schema,
                scenario_schema,
            )

    def test_family_travel_static_api_docs_gate_optional_app_layer(self):
        dataset = family_travel_static_api.load_dataset()
        for locale in ("en", "zh-Hant"):
            private_page = family_travel_static_api.render_docs(
                dataset, locale, app_public=False
            )
            self.assertIn("openapi.json", private_page)
            self.assertIn("index.schema.json", private_page)
            self.assertIn('hreflang="en"', private_page)
            self.assertIn('hreflang="zh-Hant"', private_page)
            self.assertNotIn("apps.apple.com", private_page)
            self.assertNotIn('"@type":"SoftwareApplication"', private_page)
        public_page = family_travel_static_api.render_docs(
            dataset, "en", app_public=True
        )
        self.assertIn(f"id{family_travel_mission_cards.APP_ID}", public_page)
        self.assertIn('"@type":"SoftwareApplication"', public_page)
        self.assertNotIn('"offers"', public_page)

    def test_cleanup_preserves_api_namespace_and_cross_project_links(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "api").mkdir()
            (pages / "en-US").mkdir()
            self.assertEqual(
                ["en-US"],
                [path.name for path in cleanup_localized_assets.locale_dirs(pages)],
            )
            cross_project = (
                '<a href="https://alice51849.github.io/'
                'awesome-family-travel-missions/">Curated resources</a>'
            )
            self.assertEqual(
                cross_project,
                cleanup_localized_assets.remove_missing_html_links(
                    pages / "data" / "family-travel-missions.html",
                    cross_project,
                    pages,
                ),
            )
            api_page = (
                '<link rel="canonical" href="'
                'https://alice51849.github.io/ios-app-guide/api/">'
            )
            self.assertEqual(
                api_page,
                cleanup_localized_assets.repair_html_hreflang(
                    pages / "api" / "index.html",
                    api_page,
                    pages,
                    {"en-US"},
                ),
            )

    def test_family_travel_static_api_builds_stable_versioned_surface(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            urls = family_travel_static_api.build(pages, app_public=False)
            api = pages / family_travel_static_api.API_PATH
            self.assertEqual(19, len(urls))
            for filename in (
                "index.html",
                "index.json",
                "index.schema.json",
                "scenario.schema.json",
                "openapi.json",
            ):
                self.assertTrue((api / filename).exists())
            scenario_files = sorted((api / "scenarios").glob("*.json"))
            self.assertEqual(12, len(scenario_files))
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / family_travel_static_api.API_PATH
                    / "index.html"
                ).exists()
            )
            self.assertTrue((pages / "api" / "index.html").exists())
            self.assertIn(
                family_travel_static_api.api_url(),
                (pages / "sitemap_api.xml").read_text(encoding="utf-8"),
            )
            generated = [
                *api.rglob("*"),
                pages / "zh-Hant" / family_travel_static_api.API_PATH / "index.html",
                pages / "api" / "index.html",
                pages / "sitemap_api.xml",
            ]
            mtimes = {
                path: path.stat().st_mtime_ns for path in generated if path.is_file()
            }
            family_travel_static_api.build(pages, app_public=False)
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in mtimes}
            )
            self.assertIn("sitemap_api.xml", gen_llms.build_robots())
            with mock.patch.object(gen_llms, "PAGES", str(pages)):
                self.assertIn(
                    "sitemap_api.xml", gen_llms.build_sitemap_index()
                )

    @unittest.skipUnless(
        importlib.util.find_spec("jsonschema")
        and importlib.util.find_spec("openapi_spec_validator"),
        "validation dependencies are installed in CI",
    )
    def test_family_travel_static_api_passes_published_specifications(self):
        from jsonschema import Draft202012Validator, FormatChecker
        from openapi_spec_validator import validate_url

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            family_travel_static_api.build(pages, app_public=False)
            api = pages / family_travel_static_api.API_PATH
            index_schema = json.loads(
                (api / "index.schema.json").read_text(encoding="utf-8")
            )
            scenario_schema = json.loads(
                (api / "scenario.schema.json").read_text(encoding="utf-8")
            )
            Draft202012Validator.check_schema(index_schema)
            Draft202012Validator.check_schema(scenario_schema)
            Draft202012Validator(
                index_schema, format_checker=FormatChecker()
            ).validate(
                json.loads((api / "index.json").read_text(encoding="utf-8"))
            )
            scenario_validator = Draft202012Validator(
                scenario_schema, format_checker=FormatChecker()
            )
            for path in sorted((api / "scenarios").glob("*.json")):
                scenario_validator.validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            validate_url((api / "openapi.json").as_uri())

    def test_zhuyin_static_api_matches_croissant_source(self):
        rows = zhuyin_croissant_dataset.records()
        index = zhuyin_static_api.api_index(rows)
        payloads = {
            row["symbol_id"]: zhuyin_static_api.symbol_payload(row)
            for row in rows
        }
        openapi = zhuyin_static_api.openapi_document(rows)
        index_schema = zhuyin_static_api.index_schema(rows)
        symbol_schema = zhuyin_static_api.symbol_schema(rows)
        zhuyin_static_api.validate_artifacts(
            rows,
            index,
            payloads,
            openapi,
            index_schema,
            symbol_schema,
        )
        self.assertEqual(37, len(index["symbols"]))
        self.assertEqual(37, len(payloads))
        self.assertEqual(38, len(openapi["paths"]))
        self.assertEqual("3.1.1", openapi["openapi"])
        self.assertEqual([], openapi["security"])
        endpoint_pattern = index_schema["$defs"]["endpoint"]["properties"][
            "url"
        ]["pattern"]
        self.assertNotIn(r"\-", endpoint_pattern)
        self.assertTrue(endpoint_pattern.startswith(
            r"^https://alice51849\.github\.io/ios-app-guide/"
        ))
        self.assertEqual(
            {"symbolCount": 37, "initialCount": 21, "medialCount": 3,
             "finalCount": 13, "unicodeRange": "U+3105-U+3129"},
            index["scope"],
        )
        for row in rows:
            self.assertEqual(row, payloads[row["symbol_id"]]["symbol"])
        encoded = json.dumps(
            {"index": index, "payloads": payloads, "openapi": openapi}
        )
        self.assertNotIn("apps.apple.com", encoded)
        self.assertNotIn(zhuyin_static_api.APP_NAME, encoded)
        contaminated = copy.deepcopy(openapi)
        contaminated["info"]["description"] = (
            f"{zhuyin_static_api.APP_NAME} id{zhuyin_static_api.APP_ID}"
        )
        with self.assertRaises(ValueError):
            zhuyin_static_api.validate_artifacts(
                rows,
                index,
                payloads,
                contaminated,
                index_schema,
                symbol_schema,
            )

    def test_zhuyin_static_api_docs_gate_optional_app_layer(self):
        rows = zhuyin_croissant_dataset.records()
        for locale in ("en", "zh-Hant"):
            private_page = zhuyin_static_api.render_docs(
                rows, locale, app_public=False
            )
            self.assertIn('rel="service-desc"', private_page)
            self.assertIn("openapi.json", private_page)
            self.assertIn("symbol.schema.json", private_page)
            self.assertIn('hreflang="en"', private_page)
            self.assertIn('hreflang="zh-Hant"', private_page)
            self.assertNotIn("apps.apple.com", private_page)
            self.assertNotIn('"@type":"SoftwareApplication"', private_page)
        public_page = zhuyin_static_api.render_docs(
            rows, "en", app_public=True
        )
        self.assertIn(f"id{zhuyin_static_api.APP_ID}", public_page)
        self.assertIn('"@type":"SoftwareApplication"', public_page)
        self.assertNotIn('"offers"', public_page)

    def test_static_api_catalog_preserves_both_api_surfaces(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            urls = zhuyin_static_api.build(pages, app_public=False)
            api = pages / zhuyin_static_api.API_PATH
            self.assertEqual(44, len(urls))
            for filename in (
                "index.html",
                "index.json",
                "index.schema.json",
                "symbol.schema.json",
                "openapi.json",
            ):
                self.assertTrue((api / filename).exists())
            self.assertEqual(
                37, len(list((api / "symbols").glob("*.json")))
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / zhuyin_static_api.API_PATH
                    / "index.html"
                ).exists()
            )
            catalog = (pages / "api" / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertIn("Bopomofo Symbols API v1", catalog)
            sitemap = (pages / "sitemap_api.xml").read_text(encoding="utf-8")
            self.assertEqual(37, sitemap.count("/symbols/"))
            self.assertIn(
                zhuyin_static_api.api_url("openapi.json"), sitemap
            )
            generated = [
                *api.rglob("*"),
                pages / "zh-Hant" / zhuyin_static_api.API_PATH / "index.html",
                pages / "api" / "index.html",
                pages / "sitemap_api.xml",
            ]
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in generated
                if path.is_file()
            }
            zhuyin_static_api.build(pages, app_public=False)
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in mtimes}
            )

            family_travel_static_api.build(pages, app_public=False)
            catalog = (pages / "api" / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertIn("Bopomofo Symbols API v1", catalog)
            self.assertIn("Family Travel Missions API v1", catalog)
            sitemap = (pages / "sitemap_api.xml").read_text(encoding="utf-8")
            self.assertIn(zhuyin_static_api.api_url(), sitemap)
            self.assertIn(family_travel_static_api.api_url(), sitemap)
            self.assertEqual(37, sitemap.count("/symbols/"))
            self.assertEqual(12, sitemap.count("/scenarios/"))
            self.assertEqual(
                ["family-travel-missions", "bopomofo-symbols"],
                [
                    item["slug"]
                    for item in static_api_catalog.discovered_apis(pages)
                ],
            )

    @unittest.skipUnless(
        importlib.util.find_spec("jsonschema")
        and importlib.util.find_spec("openapi_spec_validator"),
        "validation dependencies are installed in CI",
    )
    def test_zhuyin_static_api_passes_published_specifications(self):
        from jsonschema import Draft202012Validator, FormatChecker
        from openapi_spec_validator import validate_url

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            zhuyin_static_api.build(pages, app_public=False)
            api = pages / zhuyin_static_api.API_PATH
            index_schema = json.loads(
                (api / "index.schema.json").read_text(encoding="utf-8")
            )
            symbol_schema = json.loads(
                (api / "symbol.schema.json").read_text(encoding="utf-8")
            )
            Draft202012Validator.check_schema(index_schema)
            Draft202012Validator.check_schema(symbol_schema)
            Draft202012Validator(
                index_schema, format_checker=FormatChecker()
            ).validate(
                json.loads((api / "index.json").read_text(encoding="utf-8"))
            )
            symbol_validator = Draft202012Validator(
                symbol_schema, format_checker=FormatChecker()
            )
            for path in sorted((api / "symbols").glob("*.json")):
                symbol_validator.validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            validate_url((api / "openapi.json").as_uri())

    def test_verified_app_gate_updates_page_freshness_once(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            family_travel_dataset.build(pages, app_public=False)
            family_travel_static_api.build(pages, app_public=False)
            with mock.patch.object(
                family_travel_dataset, "TODAY", "2026-07-12"
            ), mock.patch.object(
                family_travel_static_api, "TODAY", "2026-07-12"
            ):
                family_travel_dataset.build(pages, app_public=True)
                family_travel_static_api.build(pages, app_public=True)
            dataset_page = (
                pages / "data" / "family-travel-missions.html"
            )
            api_page = pages / family_travel_static_api.API_PATH / "index.html"
            for page in (dataset_page, api_page):
                content = page.read_text(encoding="utf-8")
                self.assertIn(
                    '<meta name="content-modified" content="2026-07-12">',
                    content,
                )
                self.assertIn('"@type":"SoftwareApplication"', content)
            self.assertIn(
                "<lastmod>2026-07-12</lastmod>",
                (pages / "sitemap_api.xml").read_text(encoding="utf-8"),
            )
            with mock.patch.object(
                gen_data_hub, "PAGES", str(pages)
            ), mock.patch.object(
                gen_data_hub, "DATA", str(pages / "data")
            ):
                gen_data_hub.build_sitemap(
                    [
                        {
                            "slug": "family-travel-missions",
                            "localized": True,
                        }
                    ]
                )
            self.assertIn(
                "<lastmod>2026-07-12</lastmod>",
                (pages / "sitemap_data.xml").read_text(encoding="utf-8"),
            )
            mtimes = {
                page: page.stat().st_mtime_ns for page in (dataset_page, api_page)
            }
            with mock.patch.object(
                family_travel_dataset, "TODAY", "2026-07-13"
            ), mock.patch.object(
                family_travel_static_api, "TODAY", "2026-07-13"
            ):
                family_travel_dataset.build(pages, app_public=True)
                family_travel_static_api.build(pages, app_public=True)
            self.assertEqual(
                mtimes, {page: page.stat().st_mtime_ns for page in mtimes}
            )

    def test_family_travel_cards_are_bilingual_private_and_safety_bounded(self):
        english = family_travel_mission_cards.render_page("en", app_public=False)
        traditional = family_travel_mission_cards.render_page(
            "zh-Hant", app_public=False
        )
        self.assertEqual(12, len(family_travel_mission_cards.SCENARIOS["en"]))
        self.assertEqual(
            12, len(family_travel_mission_cards.SCENARIOS["zh-Hant"])
        )
        for page in (english, traditional):
            self.assertIn('"WebApplication","LearningResource"', page)
            self.assertIn('"@type":"HowTo"', page)
            self.assertIn('"@type":"FAQPage"', page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn(family_travel_mission_cards.TSA_PHOTOS, page)
            self.assertIn(family_travel_mission_cards.FAA_CHILD_SAFETY, page)
            self.assertIn(family_travel_mission_cards.NHTSA_CHILD_PASSENGER, page)
            self.assertEqual(12, page.count("data-scene="))
            self.assertEqual(3, page.count("data-style="))
            self.assertIn('id="print-boundary"', page)
            self.assertNotIn(f"id{family_travel_mission_cards.APP_ID}", page)
            self.assertNotIn('"@type":"SoftwareApplication"', page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("getUserMedia", page)
            self.assertNotIn("<input", page)
            self.assertNotIn("<form", page)
            schemas = [
                json.loads(block)
                for block in re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    page,
                    re.S,
                )
            ]
            howto = next(
                schema for schema in schemas if schema.get("@type") == "HowTo"
            )
            self.assertEqual(5, len(howto["step"]))
        self.assertIn("The driver never reads, answers or operates", english)
        self.assertIn("These cards never ask for photos", english)
        self.assertIn("not ages, levels or ability rankings", english)
        self.assertIn("never ask a driver to look", english)
        self.assertIn("non-driving companion", english)
        self.assertNotIn("Tell your adult", english)
        self.assertNotIn("With your adult, invent", english)
        self.assertIn("駕駛絕不閱讀、回答或操作", traditional)
        self.assertIn("完全沒有拍照任務", traditional)
        self.assertIn("不是年齡、程度或能力排名", traditional)
        self.assertIn("絕不要求駕駛查看", traditional)
        self.assertIn("非駕駛同行者", traditional)
        for locale_scenarios in family_travel_mission_cards.SCENARIOS.values():
            for scenario in locale_scenarios:
                self.assertFalse(
                    any("photo" in target.lower() for target in scenario["targets"])
                )
                self.assertFalse(
                    any("拍照" in target for target in scenario["targets"])
                )

    def test_family_travel_cards_gate_app_link_on_verified_availability(self):
        private_page = family_travel_mission_cards.render_page(
            "en", app_public=False
        )
        public_page = family_travel_mission_cards.render_page("en", app_public=True)
        self.assertNotIn(f"id{family_travel_mission_cards.APP_ID}", private_page)
        self.assertIn(f"id{family_travel_mission_cards.APP_ID}", public_page)
        schemas = [
            json.loads(block)
            for block in re.findall(
                r'<script type="application/ld\+json">(.*?)</script>',
                public_page,
                re.S,
            )
        ]
        software = next(
            schema
            for schema in schemas
            if schema.get("@type") == "SoftwareApplication"
        )
        self.assertEqual(family_travel_mission_cards.APP_NAME, software["name"])
        self.assertNotIn("offers", software)
        self.assertNotIn("price", software)
        main = public_page.split("<main>", 1)[1]
        self.assertLess(main.index('id="generator"'), main.index(f"id{family_travel_mission_cards.APP_ID}"))

    def test_family_travel_observation_passport_is_open_private_and_bilingual(self):
        dataset = family_travel_observation_passport.load_dataset()
        artifacts = family_travel_observation_passport.make_pdf_artifacts(dataset)
        for locale in ("en", "zh-Hant"):
            page = family_travel_observation_passport.render_page(
                dataset,
                locale,
                artifacts[locale],
                app_public=False,
                modified="2026-07-11",
            )
            self.assertEqual(14, page.count('class="passport-sheet'))
            self.assertEqual(36, page.count('class="prompt-card'))
            self.assertIn('"@type":"LearningResource"', page)
            self.assertIn('"accessModeSufficient"', page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("application/ld+json", page)
            self.assertIn(f"{family_travel_observation_passport.SLUG}.metadata.json", page)
            self.assertIn(family_travel_observation_passport.OPDS2_URL, page)
            self.assertIn(family_travel_observation_passport.OPDS1_URL, page)
            self.assertIn('type="application/opds+json"', page)
            self.assertIn(
                'type="application/atom+xml;profile=opds-catalog;kind=acquisition"',
                page,
            )
            self.assertNotIn("apps.apple.com", page)
            self.assertNotIn('"@type":"SoftwareApplication"', page)
            self.assertNotIn("<form", page)
            self.assertNotIn("<input", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            for artifact in artifacts[locale].values():
                self.assertTrue(artifact["bytes"].startswith(b"%PDF-"))
                self.assertGreater(len(artifact["bytes"]), 20_000)
                self.assertIn(artifact["sha256"], page)
        english = family_travel_observation_passport.render_page(
            dataset, "en", artifacts["en"], app_public=False
        )
        self.assertIn("No names · No destinations · No photos", english)
        traditional = family_travel_observation_passport.render_page(
            dataset, "zh-Hant", artifacts["zh-Hant"], app_public=False
        )
        self.assertIn("不填姓名 · 不填目的地 · 不拍照", traditional)
        self.assertIn("駕駛絕不閱讀、回答或操作", traditional)

        metadata = family_travel_observation_passport.metadata_graph(
            dataset, "2026-07-11", artifacts
        )
        family_travel_observation_passport.validate_metadata(metadata)
        encoded = json.dumps(metadata, ensure_ascii=False)
        self.assertNotIn("apps.apple.com", encoded)
        self.assertNotIn("SoftwareApplication", encoded)
        self.assertNotIn(family_travel_observation_passport.APP_ID, encoded)
        self.assertEqual(2, len(metadata["@graph"]))
        for resource in metadata["@graph"]:
            self.assertEqual(
                ["textual"],
                resource["accessModeSufficient"]["itemListElement"],
            )
            self.assertEqual(2, len(resource["encoding"]))

    def test_family_travel_observation_passport_app_layer_is_verified_and_optional(self):
        dataset = family_travel_observation_passport.load_dataset()
        artifacts = family_travel_observation_passport.make_pdf_artifacts(dataset)
        private_page = family_travel_observation_passport.render_page(
            dataset, "en", artifacts["en"], app_public=False
        )
        public_page = family_travel_observation_passport.render_page(
            dataset, "en", artifacts["en"], app_public=True
        )
        self.assertNotIn(family_travel_observation_passport.APP_ID, private_page)
        self.assertIn(family_travel_observation_passport.APP_ID, public_page)
        self.assertIn('"@type":"SoftwareApplication"', public_page)
        main = public_page.split("<main>", 1)[1]
        self.assertLess(
            main.index('id="passport"'),
            main.index(family_travel_observation_passport.APP_ID),
        )

    def test_family_travel_opds_catalogs_are_symmetric_private_and_stable(self):
        dataset = family_travel_observation_passport.load_dataset()
        artifacts = family_travel_observation_passport.make_pdf_artifacts(dataset)
        json_text, xml_text = family_travel_opds_catalog.render_catalogs(
            dataset, "2026-07-11", artifacts
        )
        catalog = json.loads(json_text)
        json_acquisitions = family_travel_opds_catalog.validate_opds2(
            catalog, artifacts
        )
        xml_acquisitions = family_travel_opds_catalog.validate_opds1(
            xml_text, "2026-07-11T00:00:00Z", artifacts
        )
        self.assertEqual(json_acquisitions, xml_acquisitions)
        self.assertEqual(2, len(catalog["publications"]))
        self.assertEqual(4, len(json_acquisitions))
        self.assertEqual(
            family_travel_opds_catalog.OPDS2_MEDIA_TYPE,
            next(
                link["type"]
                for link in catalog["links"]
                if link["rel"] == "self"
            ),
        )
        encoded = json_text + xml_text
        self.assertNotIn("apps.apple.com", encoded)
        self.assertNotIn("SoftwareApplication", encoded)
        self.assertNotIn(family_travel_opds_catalog.APP_ID, encoded)
        self.assertNotIn(family_travel_opds_catalog.APP_NAME, encoded)
        self.assertIn("No PDF/UA conformance is claimed", encoded)
        self.assertNotIn('"conformsTo"', encoded)
        self.assertNotIn("taggedPDF", encoded)
        for publication in catalog["publications"]:
            self.assertEqual(
                ["textual"],
                publication["metadata"]["accessibility"]["accessModeSufficient"],
            )
            acquisitions = [
                link
                for link in publication["links"]
                if link["rel"] == family_travel_opds_catalog.OPEN_ACCESS_REL
            ]
            self.assertEqual(2, len(acquisitions))
            self.assertTrue(
                all(link["type"] == "application/pdf" for link in acquisitions)
            )

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            family_travel_observation_passport.build(pages, app_public=False)
            urls = family_travel_opds_catalog.build(pages, artifacts)
            outputs = [
                pages
                / "opds"
                / f"{family_travel_observation_passport.SLUG}.json",
                pages
                / "opds"
                / f"{family_travel_observation_passport.SLUG}.xml",
                pages / "sitemap_opds.xml",
            ]
            self.assertEqual(
                [
                    family_travel_observation_passport.OPDS2_URL,
                    family_travel_observation_passport.OPDS1_URL,
                    family_travel_opds_catalog.SITEMAP_URL,
                ],
                urls,
            )
            self.assertTrue(all(path.exists() for path in outputs))
            mtimes = {path: path.stat().st_mtime_ns for path in outputs}
            family_travel_opds_catalog.build(pages, artifacts)
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in outputs}
            )

    def test_family_travel_ro_crate_is_complete_private_and_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            dataset = family_travel_dataset.load_dataset()
            artifacts = family_travel_observation_passport.make_pdf_artifacts(dataset)
            family_travel_dataset.build(pages, app_public=False)
            family_travel_static_api.build(pages, app_public=False)
            with mock.patch.object(
                family_travel_observation_passport,
                "make_pdf_artifacts",
                return_value=artifacts,
            ):
                family_travel_observation_passport.build(
                    pages, app_public=False
                )
            family_travel_opds_catalog.build(pages, artifacts)
            urls = family_travel_ro_crate.build(pages)
            metadata_path = pages / "data" / family_travel_ro_crate.FILENAME
            sitemap_path = pages / "sitemap_ro_crate.xml"
            self.assertEqual(
                [
                    family_travel_ro_crate.METADATA_URL,
                    family_travel_ro_crate.SITEMAP_URL,
                ],
                urls,
            )
            crate = json.loads(metadata_path.read_text(encoding="utf-8"))
            family_travel_ro_crate.validate_crate(crate, pages)
            entities = {entity["@id"]: entity for entity in crate["@graph"]}
            descriptor = entities["ro-crate-metadata.json"]
            self.assertEqual(
                {"@id": family_travel_ro_crate.ROOT_ID},
                descriptor["about"],
            )
            self.assertEqual(
                {"@id": family_travel_ro_crate.PROFILE},
                descriptor["conformsTo"],
            )
            root = entities[family_travel_ro_crate.ROOT_ID]
            self.assertIn("Dataset", root["@type"])
            self.assertEqual(dataset["dateCreated"], root["datePublished"])
            self.assertEqual(
                {"@id": family_travel_ro_crate.LICENSE}, root["license"]
            )
            self.assertEqual(
                {spec.url for spec in family_travel_ro_crate.FILE_SPECS},
                {item["@id"] for item in root["hasPart"]},
            )
            self.assertNotIn(
                family_travel_ro_crate.METADATA_URL,
                {item["@id"] for item in root["hasPart"]},
            )
            encoded = json.dumps(crate, ensure_ascii=False)
            self.assertNotIn("apps.apple.com", encoded)
            self.assertNotIn("SoftwareApplication", encoded)
            self.assertNotIn(family_travel_ro_crate.APP_ID, encoded)
            self.assertNotIn(family_travel_ro_crate.APP_NAME, encoded)
            self.assertNotIn(family_travel_ro_crate.APP_SHORT_NAME, encoded)
            for spec in family_travel_ro_crate.FILE_SPECS:
                self.assertTrue(spec.url.startswith("https://"))
                self.assertIn("File", family_travel_ro_crate._types(entities[spec.url]))
            for relative_page in (
                "data/family-travel-missions.html",
                "zh-Hant/data/family-travel-missions.html",
                "tools/family-travel-observation-passport.html",
                "zh-Hant/tools/family-travel-observation-passport.html",
            ):
                page = (pages / relative_page).read_text(encoding="utf-8")
                self.assertIn(family_travel_ro_crate.METADATA_URL, page)
                self.assertNotIn("apps.apple.com", page)
            self.assertIn(
                family_travel_ro_crate.METADATA_URL,
                sitemap_path.read_text(encoding="utf-8"),
            )
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (metadata_path, sitemap_path)
            }
            family_travel_ro_crate.build(pages)
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in mtimes}
            )
            self.assertIn("sitemap_ro_crate.xml", gen_llms.build_robots())
            with mock.patch.object(gen_llms, "PAGES", str(pages)):
                self.assertIn(
                    "sitemap_ro_crate.xml", gen_llms.build_sitemap_index()
                )

    def test_zhuyin_anki_decks_are_complete_official_two_field_imports(self):
        artifacts = zhuyin_anki_deck.make_artifacts()
        self.assertEqual({"en", "zh-Hant"}, set(artifacts))
        eh_record = next(
            record for record in gen_data_hub.ZHUYIN if record[0] == "ㄝ"
        )
        self.assertEqual(("ê", "final", "誒", "ề", "hey (interjection)"), eh_record[1:])
        expected_symbols = [record[0] for record in gen_data_hub.ZHUYIN]
        for locale, artifact in artifacts.items():
            content = artifact["content"]
            self.assertEqual(content, artifact["bytes"].decode("utf-8"))
            self.assertFalse(content.startswith("\ufeff"))
            lines = content.splitlines()
            self.assertEqual("#separator:Tab", lines[0])
            self.assertEqual("#html:false", lines[1])
            self.assertTrue(lines[2].startswith("#tags:"))
            self.assertTrue(lines[3].startswith("#deck:"))
            self.assertEqual("#columns:Front\tBack", lines[4])
            rows = lines[5:]
            self.assertEqual(37, len(rows))
            fields = [row.split("\t") for row in rows]
            self.assertTrue(all(len(row) == 2 for row in fields))
            self.assertEqual(expected_symbols, [row[0] for row in fields])
            self.assertEqual(37, len({row[0] for row in fields}))
            self.assertTrue(
                all(gen_data_hub.ZHUYIN_IPA[row[0]] in row[1] for row in fields)
            )
            self.assertNotIn("#guid", content)
            self.assertNotIn("apps.apple.com", content)
            self.assertNotIn(zhuyin_anki_deck.APP_ID, content)
            zhuyin_anki_deck.validate_tsv(locale, content)

    def test_zhuyin_anki_build_is_bilingual_versioned_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            urls = zhuyin_anki_deck.build(pages, app_public=False)
            self.assertEqual(6, len(urls))
            artifacts = zhuyin_anki_deck.make_artifacts()
            expected_paths = [
                tools / zhuyin_anki_deck.DECKS["en"]["filename"],
                tools / zhuyin_anki_deck.DECKS["zh-Hant"]["filename"],
                tools / zhuyin_anki_deck.METADATA_FILENAME,
                tools / f"{zhuyin_anki_deck.SLUG}.html",
                pages / "zh-Hant" / "tools" / f"{zhuyin_anki_deck.SLUG}.html",
                pages / "sitemap_anki.xml",
            ]
            self.assertTrue(all(path.exists() for path in expected_paths))
            english = expected_paths[3].read_text(encoding="utf-8")
            traditional = expected_paths[4].read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn('"LearningResource"', page)
                self.assertIn('"FAQPage"', page)
                self.assertIn('hreflang="en"', page)
                self.assertIn('hreflang="zh-Hant"', page)
                self.assertIn('type="text/tab-separated-values"', page)
                self.assertIn(zhuyin_anki_deck.METADATA_URL, page)
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn(zhuyin_anki_deck.APP_ID, page)
                self.assertNotIn('"SoftwareApplication"', page)
            self.assertIn("Free Bopomofo Anki Deck", english)
            self.assertIn("免費注音 Anki 牌組", traditional)
            public = zhuyin_anki_deck.render_page(
                "en", artifacts, app_public=True
            )
            self.assertIn(zhuyin_anki_deck.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)

            metadata = json.loads(expected_paths[2].read_text(encoding="utf-8"))
            zhuyin_anki_deck.validate_metadata(metadata, artifacts)
            encoded_metadata = json.dumps(metadata, ensure_ascii=False)
            self.assertNotIn("apps.apple.com", encoded_metadata)
            resources = {
                resource["inLanguage"]: resource
                for resource in metadata["@graph"]
            }
            for locale, artifact in artifacts.items():
                encoding = resources[locale]["encoding"]
                self.assertEqual(artifact["sha256"], encoding["sha256"])
                self.assertEqual(
                    f"{len(artifact['bytes'])} bytes",
                    encoding["contentSize"],
                )
                self.assertEqual(37, resources[locale]["numberOfItems"])
            sitemap = expected_paths[5].read_text(encoding="utf-8")
            for url in urls[:-1]:
                self.assertIn(url, sitemap)
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count(f"{zhuyin_anki_deck.SLUG}.html"))

            with mock.patch.object(gen_llms, "TOOLS", str(tools)), mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                sitemap_index = gen_llms.build_sitemap_index()
            for generated_index in (llms, full):
                self.assertIn("Open Bopomofo flashcard imports", generated_index)
                self.assertIn(zhuyin_anki_deck.METADATA_URL, generated_index)
                self.assertIn(artifacts["en"]["url"], generated_index)
                self.assertIn(artifacts["zh-Hant"]["url"], generated_index)
            self.assertIn("sitemap_anki.xml", sitemap_index)
            self.assertIn("sitemap_anki.xml", gen_llms.build_robots())

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in [*expected_paths, tools / "index.html"]
            }
            zhuyin_anki_deck.build(pages, app_public=False)
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in mtimes}
            )

    def test_zhuyin_skos_graph_is_complete_and_app_independent(self):
        triples, artifacts = zhuyin_skos_vocabulary.make_graph_artifacts(
            zhuyin_skos_vocabulary.INITIAL_DATE
        )
        self.assertEqual(740, len(triples))
        self.assertEqual(
            {"jsonld", "turtle", "ntriples", "shacl"},
            set(artifacts),
        )
        jsonld = json.loads(artifacts["jsonld"]["content"])
        self.assertEqual(1.1, jsonld["@context"]["@version"])
        graph_ids = {
            node["@id"] for node in jsonld["@graph"] if "@id" in node
        }
        expected_ids = {
            f"zhuyin:u{ord(record[0]):04X}" for record in gen_data_hub.ZHUYIN
        }
        self.assertTrue(expected_ids.issubset(graph_ids))
        self.assertEqual(37, len(expected_ids))
        self.assertEqual(
            set(range(0x3105, 0x312A)),
            {ord(record[0]) for record in gen_data_hub.ZHUYIN},
        )
        ntriples = artifacts["ntriples"]["content"]
        for value in re.findall(r"<([^>]+)>", ntriples):
            value.encode("ascii")
        for artifact in artifacts.values():
            content = artifact["content"]
            self.assertNotIn("apps.apple.com", content)
            self.assertNotIn(zhuyin_skos_vocabulary.APP_ID, content)
            self.assertNotIn(zhuyin_skos_vocabulary.APP_NAME, content)
            self.assertEqual(
                hashlib.sha256(artifact["bytes"]).hexdigest(),
                artifact["sha256"],
            )
        zhuyin_skos_vocabulary.validate_triples(triples)
        zhuyin_skos_vocabulary.validate_graph_artifacts(artifacts)
        metadata = zhuyin_skos_vocabulary.metadata_graph(
            triples,
            artifacts,
            zhuyin_skos_vocabulary.INITIAL_DATE,
        )
        zhuyin_skos_vocabulary.validate_metadata(
            metadata,
            triples,
            artifacts,
        )
        dataset = metadata["@graph"][0]
        self.assertEqual(740, dataset["void:triples"])
        self.assertEqual(46, dataset["void:entities"])
        self.assertEqual(
            40,
            dataset["void:classPartition"]["void:entities"],
        )
        self.assertEqual(4, len(dataset["dcat:distribution"]))

    @unittest.skipUnless(
        importlib.util.find_spec("rdflib")
        and importlib.util.find_spec("pyshacl"),
        "RDF validation dependencies are installed in CI",
    )
    def test_zhuyin_skos_serializations_are_isomorphic_and_shacl_valid(self):
        from pyshacl import validate
        from rdflib import Graph, Literal, URIRef
        from rdflib.compare import to_isomorphic

        triples, artifacts = zhuyin_skos_vocabulary.make_graph_artifacts(
            zhuyin_skos_vocabulary.INITIAL_DATE
        )
        graphs = []
        for key, rdf_format in (
            ("jsonld", "json-ld"),
            ("turtle", "turtle"),
            ("ntriples", "nt"),
        ):
            graph = Graph()
            graph.parse(data=artifacts[key]["content"], format=rdf_format)
            self.assertEqual(len(triples), len(graph))
            graphs.append(graph)
        self.assertEqual(
            to_isomorphic(graphs[0]),
            to_isomorphic(graphs[1]),
        )
        self.assertEqual(
            to_isomorphic(graphs[0]),
            to_isomorphic(graphs[2]),
        )
        shapes = Graph()
        shapes.parse(data=artifacts["shacl"]["content"], format="turtle")
        conforms, _results, report = validate(
            graphs[0],
            shacl_graph=shapes,
            inference="none",
        )
        self.assertTrue(conforms, report)

        invalid = Graph()
        for triple in graphs[0]:
            invalid.add(triple)
        invalid.add(
            (
                URIRef(zhuyin_skos_vocabulary.concept_uri("ㄅ")),
                URIRef(zhuyin_skos_vocabulary.SKOS_PREF_LABEL),
                Literal("Duplicate English label", lang="en"),
            )
        )
        conforms, _results, _report = validate(
            invalid,
            shacl_graph=shapes,
            inference="none",
        )
        self.assertFalse(conforms)

    def test_zhuyin_skos_build_is_bilingual_versioned_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir()
            source_card = (
                f'<a class="item" href="{zhuyin_skos_vocabulary.SITE}/data/'
                'zhuyin-bopomofo.html"><h2>Source dataset</h2></a>'
            )
            catalog_schema = json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "DataCatalog",
                    "dataset": [
                        {
                            "@type": "Dataset",
                            "url": zhuyin_skos_vocabulary.SOURCE_PAGE,
                        }
                    ],
                }
            )
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                f"{catalog_schema}</script><main>{source_card}"
                '<p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            urls = zhuyin_skos_vocabulary.build(pages, app_public=False)
            self.assertEqual(8, len(urls))
            triples, downloads, _modified = (
                zhuyin_skos_vocabulary.write_versioned_artifacts(data)
            )
            expected_paths = [
                data / f"{zhuyin_skos_vocabulary.SLUG}.html",
                pages
                / "zh-Hant"
                / "data"
                / f"{zhuyin_skos_vocabulary.SLUG}.html",
                *[
                    data / artifact["filename"]
                    for artifact in downloads.values()
                ],
                pages / "sitemap_vocab.xml",
            ]
            self.assertEqual(8, len(expected_paths))
            self.assertTrue(all(path.exists() for path in expected_paths))
            english = expected_paths[0].read_text(encoding="utf-8")
            traditional = expected_paths[1].read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn('"Dataset","DefinedTermSet"', page)
                self.assertIn('"FAQPage"', page)
                self.assertIn('hreflang="en"', page)
                self.assertIn('hreflang="zh-Hant"', page)
                self.assertIn('type="application/ld+json"', page)
                self.assertIn('type="text/turtle"', page)
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn(zhuyin_skos_vocabulary.APP_ID, page)
                self.assertNotIn('"SoftwareApplication"', page)
            self.assertIn("Bopomofo SKOS Vocabulary", english)
            self.assertIn("注音符號 SKOS 詞彙", traditional)
            public = zhuyin_skos_vocabulary.render_page(
                "en",
                downloads,
                app_public=True,
            )
            self.assertIn(zhuyin_skos_vocabulary.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)

            metadata = json.loads(
                (data / zhuyin_skos_vocabulary.METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            graph_artifacts = {
                key: artifact
                for key, artifact in downloads.items()
                if key != "metadata"
            }
            zhuyin_skos_vocabulary.validate_metadata(
                metadata,
                triples,
                graph_artifacts,
            )
            encoded_metadata = json.dumps(metadata, ensure_ascii=False)
            self.assertNotIn("apps.apple.com", encoded_metadata)
            distributions = {
                node["@id"]: node
                for node in metadata["@graph"]
                if node.get("@type") == "dcat:Distribution"
            }
            for key, artifact in graph_artifacts.items():
                distribution = distributions[
                    f"{zhuyin_skos_vocabulary.DATASET_URI}-{key}"
                ]
                self.assertEqual(
                    artifact["sha256"],
                    distribution["schema:sha256"],
                )
                self.assertEqual(
                    len(artifact["bytes"]),
                    distribution["dcat:byteSize"],
                )

            sitemap = expected_paths[-1].read_text(encoding="utf-8")
            for url in urls[:-1]:
                self.assertIn(url, sitemap)
            index = (data / "index.html").read_text(encoding="utf-8")
            target = f"{zhuyin_skos_vocabulary.SLUG}.html"
            self.assertEqual(
                1,
                index.count(
                    f'href="{zhuyin_skos_vocabulary.LANDING_URL}"'
                ),
            )
            self.assertLess(index.index("zhuyin-bopomofo.html"), index.index(target))
            catalog_schema = json.loads(
                re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    index,
                    re.DOTALL,
                ).group(1)
            )
            catalog_entries = [
                dataset
                for dataset in catalog_schema["dataset"]
                if dataset.get("url") == zhuyin_skos_vocabulary.LANDING_URL
            ]
            self.assertEqual(1, len(catalog_entries))
            self.assertEqual(5, len(catalog_entries[0]["distribution"]))

            with mock.patch.object(
                gen_llms, "DATA_DIR", str(data)
            ), mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                sitemap_index = gen_llms.build_sitemap_index()
            for generated_index in (llms, full):
                self.assertIn("Bopomofo linked open vocabulary", generated_index)
                self.assertIn(
                    downloads["jsonld"]["url"],
                    generated_index,
                )
                self.assertIn(
                    downloads["metadata"]["url"],
                    generated_index,
                )
            self.assertNotRegex(
                llms,
                re.escape(
                    f"{zhuyin_skos_vocabulary.SITE}/data/"
                    f"{zhuyin_skos_vocabulary.SLUG}.json"
                )
                + r"(?:\s|$)",
            )
            self.assertIn("sitemap_vocab.xml", sitemap_index)
            self.assertIn("sitemap_vocab.xml", gen_llms.build_robots())

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in [*expected_paths, data / "index.html"]
            }
            zhuyin_skos_vocabulary.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    def test_zhuyin_croissant_records_are_complete_and_app_independent(self):
        rows = zhuyin_croissant_dataset.records()
        zhuyin_croissant_dataset.validate_records(rows)
        self.assertEqual(37, len(rows))
        self.assertEqual(
            set(range(0x3105, 0x312A)),
            {ord(row["symbol"]) for row in rows},
        )
        self.assertEqual(
            list(range(1, 38)),
            [row["order"] for row in rows],
        )
        self.assertEqual(
            list(zhuyin_croissant_dataset.FIELD_NAMES),
            list(rows[0]),
        )
        eh_record = next(row for row in rows if row["symbol"] == "ㄝ")
        self.assertEqual("ề", eh_record["example_pinyin"])
        self.assertEqual(
            zhuyin_skos_vocabulary.concept_uri("ㄝ"),
            eh_record["concept_uri"],
        )
        artifacts = zhuyin_croissant_dataset.make_data_artifacts(rows)
        self.assertEqual({"csv", "jsonl"}, set(artifacts))
        for artifact in artifacts.values():
            self.assertEqual(
                hashlib.sha256(artifact["bytes"]).hexdigest(),
                artifact["sha256"],
            )
            self.assertFalse(artifact["content"].startswith("\ufeff"))
            self.assertNotIn("apps.apple.com", artifact["content"])
            self.assertNotIn(
                zhuyin_croissant_dataset.APP_ID,
                artifact["content"],
            )
            self.assertNotIn(
                zhuyin_croissant_dataset.APP_NAME,
                artifact["content"],
            )

    @unittest.skipUnless(
        importlib.util.find_spec("mlcroissant"),
        "Official Croissant validation dependency is installed in CI",
    )
    def test_zhuyin_croissant_validates_and_loads_with_official_reader(self):
        import mlcroissant

        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            rows, metadata, downloads, _modified = (
                zhuyin_croissant_dataset.write_versioned_artifacts(data)
            )
            metadata_path = (
                data / zhuyin_croissant_dataset.METADATA_FILENAME
            )
            csv_path = data / zhuyin_croissant_dataset.CSV_FILENAME
            dataset = mlcroissant.Dataset(
                jsonld=metadata_path,
                mapping={
                    zhuyin_croissant_dataset.CSV_FILENAME: csv_path,
                },
            )
            loaded = list(dataset.records(record_set="symbols"))
            self.assertEqual(37, len(loaded))
            self.assertEqual(1, loaded[0]["symbols/order"])
            self.assertEqual(
                rows[0]["symbol"].encode("utf-8"),
                loaded[0]["symbols/symbol"],
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
            self.assertIn("Done.", result.stdout + result.stderr)
            self.assertEqual(
                zhuyin_croissant_dataset.CROISSANT_SPEC,
                metadata["conformsTo"],
            )
            self.assertEqual(3, len(downloads))

    def test_zhuyin_croissant_build_is_bilingual_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir()
            source_card = (
                f'<a class="item" href="{zhuyin_croissant_dataset.SOURCE_PAGE}">'
                "<h2>Source dataset</h2></a>"
            )
            catalog_schema = json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "DataCatalog",
                    "dataset": [
                        {
                            "@type": "Dataset",
                            "url": zhuyin_croissant_dataset.SOURCE_PAGE,
                        }
                    ],
                }
            )
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                f"{catalog_schema}</script><main>{source_card}"
                '<p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            urls = zhuyin_croissant_dataset.build(
                pages,
                app_public=False,
            )
            self.assertEqual(6, len(urls))
            expected_paths = [
                data / f"{zhuyin_croissant_dataset.SLUG}.html",
                pages
                / "zh-Hant"
                / "data"
                / f"{zhuyin_croissant_dataset.SLUG}.html",
                data / zhuyin_croissant_dataset.CSV_FILENAME,
                data / zhuyin_croissant_dataset.JSONL_FILENAME,
                data / zhuyin_croissant_dataset.METADATA_FILENAME,
                pages / "sitemap_croissant.xml",
            ]
            self.assertTrue(all(path.exists() for path in expected_paths))
            english = expected_paths[0].read_text(encoding="utf-8")
            traditional = expected_paths[1].read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn(
                    zhuyin_croissant_dataset.CROISSANT_SPEC,
                    page,
                )
                self.assertIn('"cr:RecordSet"', page)
                self.assertIn('hreflang="en"', page)
                self.assertIn('hreflang="zh-Hant"', page)
                self.assertIn('type="text/csv"', page)
                self.assertIn('rel="service-desc"', page)
                self.assertIn(
                    zhuyin_croissant_dataset.API_OPENAPI,
                    page,
                )
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn(
                    zhuyin_croissant_dataset.APP_ID,
                    page,
                )
                self.assertNotIn('"SoftwareApplication"', page)
            self.assertIn("Bopomofo ML Dataset", english)
            self.assertIn("Limitations and non-uses", english)
            self.assertIn("注音符號 ML 資料集", traditional)
            self.assertIn("限制與不適用情境", traditional)
            self.assertIn(
                zhuyin_croissant_dataset.FRICTIONLESS_PAGE,
                english,
            )
            self.assertIn(
                zhuyin_croissant_dataset.ZH_FRICTIONLESS_PAGE,
                traditional,
            )

            rows, metadata, downloads, _modified = (
                zhuyin_croissant_dataset.write_versioned_artifacts(data)
            )
            zhuyin_croissant_dataset.validate_metadata(
                metadata,
                rows,
                {key: value for key, value in downloads.items() if key != "metadata"},
            )
            public = zhuyin_croissant_dataset.render_page(
                "en",
                rows,
                metadata,
                downloads,
                app_public=True,
            )
            self.assertIn(zhuyin_croissant_dataset.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            raw_metadata = expected_paths[4].read_text(encoding="utf-8")
            self.assertNotIn("apps.apple.com", raw_metadata)
            self.assertNotIn(
                zhuyin_croissant_dataset.APP_ID,
                raw_metadata,
            )

            sitemap = expected_paths[-1].read_text(encoding="utf-8")
            for url in urls[:-1]:
                self.assertIn(url, sitemap)
            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                index.count(
                    f'href="{zhuyin_croissant_dataset.LANDING_URL}"'
                ),
            )
            catalog = json.loads(
                re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    index,
                    re.DOTALL,
                ).group(1)
            )
            entries = [
                dataset
                for dataset in catalog["dataset"]
                if dataset.get("url")
                == zhuyin_croissant_dataset.LANDING_URL
            ]
            self.assertEqual(1, len(entries))
            self.assertEqual(3, len(entries[0]["distribution"]))

            with mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(data),
            ), mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                sitemap_index = gen_llms.build_sitemap_index()
                robots = gen_llms.build_robots()
            for generated_index in (llms, full):
                self.assertIn("Bopomofo AI/ML dataset", generated_index)
                self.assertIn(
                    zhuyin_croissant_dataset.METADATA_URL,
                    generated_index,
                )
                self.assertIn(
                    zhuyin_croissant_dataset.CSV_URL,
                    generated_index,
                )
            self.assertIn("sitemap_croissant.xml", sitemap_index)
            self.assertIn("sitemap_croissant.xml", robots)

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in [*expected_paths, data / "index.html"]
            }
            zhuyin_croissant_dataset.build(
                pages,
                app_public=False,
            )
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    def test_zhuyin_frictionless_package_is_complete_and_app_independent(self):
        rows = zhuyin_croissant_dataset.records()
        artifacts = zhuyin_frictionless_package.make_artifacts(rows)
        zhuyin_frictionless_package.validate_artifacts(rows, artifacts)
        descriptor = json.loads(artifacts["descriptor"]["content"])
        schema = json.loads(artifacts["schema"]["content"])
        resource = descriptor["resources"][0]

        self.assertEqual(
            zhuyin_frictionless_package.DATA_PACKAGE_PROFILE,
            descriptor["$schema"],
        )
        self.assertEqual(
            zhuyin_frictionless_package.TABLE_SCHEMA_PROFILE,
            schema["$schema"],
        )
        self.assertNotIn("fieldsMatch", schema)
        self.assertEqual(["symbol_id"], schema["primaryKey"])
        self.assertEqual(
            list(zhuyin_croissant_dataset.FIELD_NAMES),
            [field["name"] for field in schema["fields"]],
        )
        self.assertEqual("symbols.csv", resource["path"])
        self.assertEqual("table-schema.json", resource["schema"])
        self.assertEqual(
            len(artifacts["csv"]["content"].encode("utf-8")),
            resource["bytes"],
        )
        self.assertEqual(
            f"sha256:{artifacts['csv']['sha256']}",
            resource["hash"],
        )
        csv_rows = list(
            csv.DictReader(artifacts["csv"]["content"].splitlines())
        )
        self.assertEqual(37, len(csv_rows))
        self.assertEqual(
            list(zhuyin_croissant_dataset.FIELD_NAMES),
            list(csv_rows[0]),
        )
        raw = "\n".join(artifact["content"] for artifact in artifacts.values())
        self.assertNotIn("apps.apple.com", raw)
        self.assertNotIn(zhuyin_frictionless_package.APP_ID, raw)
        self.assertNotIn(zhuyin_frictionless_package.APP_NAME, raw)
        self.assertNotIn("SoftwareApplication", raw)

        contaminated = copy.deepcopy(artifacts)
        package = json.loads(contaminated["descriptor"]["content"])
        package["description"] = zhuyin_frictionless_package.APP_NAME
        contaminated["descriptor"]["content"] = json.dumps(package)
        with self.assertRaises(ValueError):
            zhuyin_frictionless_package.validate_artifacts(rows, contaminated)

    @unittest.skipUnless(
        importlib.util.find_spec("frictionless"),
        "Official Frictionless validation dependency is installed in CI",
    )
    def test_zhuyin_frictionless_package_validates_and_loads_officially(self):
        from frictionless import Package, Schema, validate

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            zhuyin_frictionless_package.build(pages, app_public=False)
            package_path = (
                pages
                / zhuyin_frictionless_package.PACKAGE_PATH
                / zhuyin_frictionless_package.DESCRIPTOR_FILENAME
            )
            schema_path = (
                pages
                / zhuyin_frictionless_package.PACKAGE_PATH
                / zhuyin_frictionless_package.SCHEMA_FILENAME
            )
            validation = validate(str(package_path))
            package = Package(str(package_path))
            package_validation = package.validate()
            schema_validation = Schema.validate_descriptor(
                json.loads(schema_path.read_text(encoding="utf-8"))
            )
            self.assertTrue(
                validation.valid,
                validation.flatten(["type", "note"]),
            )
            self.assertTrue(
                package_validation.valid,
                package_validation.flatten(["type", "note"]),
            )
            self.assertTrue(
                schema_validation.valid,
                schema_validation.flatten(["type", "note"]),
            )
            loaded = [
                row.to_dict()
                for row in package.get_resource("symbols").read_rows()
            ]
            self.assertEqual(zhuyin_croissant_dataset.records(), loaded)

    def test_zhuyin_frictionless_build_is_bilingual_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir()
            croissant_card = (
                f'<a class="item" href="'
                f'{zhuyin_frictionless_package.CROISSANT_PAGE}">'
                "<h2>Croissant dataset</h2></a>"
            )
            catalog_schema = json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "DataCatalog",
                    "dataset": [
                        {
                            "@type": "Dataset",
                            "url": zhuyin_frictionless_package.CROISSANT_PAGE,
                        }
                    ],
                }
            )
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                f"{catalog_schema}</script><main>{croissant_card}"
                '<p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            urls = zhuyin_frictionless_package.build(
                pages,
                app_public=False,
            )
            package = pages / zhuyin_frictionless_package.PACKAGE_PATH
            expected_paths = [
                package / "index.html",
                pages
                / "zh-Hant"
                / zhuyin_frictionless_package.PACKAGE_PATH
                / "index.html",
                package / zhuyin_frictionless_package.DESCRIPTOR_FILENAME,
                package / zhuyin_frictionless_package.SCHEMA_FILENAME,
                package / zhuyin_frictionless_package.CSV_FILENAME,
                pages / "sitemap_datapackage.xml",
            ]
            self.assertEqual(6, len(urls))
            self.assertTrue(all(path.exists() for path in expected_paths))
            english = expected_paths[0].read_text(encoding="utf-8")
            traditional = expected_paths[1].read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn('hreflang="en"', page)
                self.assertIn('hreflang="zh-Hant"', page)
                self.assertIn("datapackage.json", page)
                self.assertIn("table-schema.json", page)
                self.assertIn("symbols.csv", page)
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn(zhuyin_frictionless_package.APP_ID, page)
                self.assertNotIn('"SoftwareApplication"', page)
            self.assertIn("Bopomofo Frictionless Data Package 2.0", english)
            self.assertIn(
                "注音符號 Frictionless Data Package 2.0",
                traditional,
            )
            self.assertIn("<th>順序</th>", traditional)
            self.assertIn("<td>聲母</td>", traditional)
            self.assertIn(
                zhuyin_frictionless_package.ZH_CROISSANT_PAGE,
                traditional,
            )
            self.assertIn(
                zhuyin_frictionless_package.ZH_SKOS_PAGE,
                traditional,
            )
            public = zhuyin_frictionless_package.render_page(
                "en",
                zhuyin_croissant_dataset.records(),
                zhuyin_frictionless_package.make_artifacts(
                    zhuyin_croissant_dataset.records()
                ),
                app_public=True,
            )
            self.assertIn(zhuyin_frictionless_package.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)

            sitemap = expected_paths[-1].read_text(encoding="utf-8")
            for url in urls[:-1]:
                self.assertIn(url, sitemap)
            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                index.count(
                    f'href="{zhuyin_frictionless_package.PACKAGE_URL}"'
                ),
            )
            self.assertLess(
                index.index(zhuyin_frictionless_package.CROISSANT_PAGE),
                index.index(zhuyin_frictionless_package.PACKAGE_URL),
            )
            catalog = json.loads(
                re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    index,
                    re.DOTALL,
                ).group(1)
            )
            entries = [
                dataset
                for dataset in catalog["dataset"]
                if dataset.get("url")
                == zhuyin_frictionless_package.PACKAGE_URL
            ]
            self.assertEqual(1, len(entries))
            self.assertEqual(3, len(entries[0]["distribution"]))

            with mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(data),
            ), mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                sitemap_index = gen_llms.build_sitemap_index()
                robots = gen_llms.build_robots()
            for generated_index in (llms, full):
                self.assertIn(
                    "Bopomofo portable Data Package",
                    generated_index,
                )
                self.assertIn(
                    zhuyin_frictionless_package.DESCRIPTOR_URL,
                    generated_index,
                )
                self.assertIn(
                    zhuyin_frictionless_package.CSV_URL,
                    generated_index,
                )
            self.assertIn("sitemap_datapackage.xml", sitemap_index)
            self.assertIn("sitemap_datapackage.xml", robots)

            (
                croissant_rows,
                croissant_metadata,
                croissant_downloads,
            ) = zhuyin_croissant_dataset._candidates(
                zhuyin_croissant_dataset.INITIAL_DATE
            )
            croissant_page = zhuyin_croissant_dataset.render_page(
                "en",
                croissant_rows,
                croissant_metadata,
                croissant_downloads,
                app_public=False,
            )
            self.assertIn(
                zhuyin_croissant_dataset.FRICTIONLESS_PAGE,
                croissant_page,
            )
            with mock.patch.object(
                gen_data_hub,
                "DATA",
                str(data),
            ):
                gen_data_hub.build_zhuyin_page()
            source_page = (data / "zhuyin-bopomofo.html").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                zhuyin_frictionless_package.PACKAGE_URL,
                source_page,
            )

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in [*expected_paths, data / "index.html"]
            }
            zhuyin_frictionless_package.build(
                pages,
                app_public=False,
            )
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    def test_family_travel_observation_passport_build_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            urls = family_travel_observation_passport.build(
                pages, app_public=False
            )
            outputs = [
                tools / f"{family_travel_observation_passport.SLUG}.html",
                pages
                / "zh-Hant"
                / "tools"
                / f"{family_travel_observation_passport.SLUG}.html",
                tools
                / f"{family_travel_observation_passport.SLUG}.metadata.json",
                *sorted(tools.glob(f"{family_travel_observation_passport.SLUG}-*.pdf")),
            ]
            self.assertEqual(7, len(urls))
            self.assertEqual(7, len(outputs))
            self.assertTrue(all(path.exists() for path in outputs))
            self.assertTrue(all(path.stat().st_size > 20_000 for path in outputs[-4:]))
            mtimes = {path: path.stat().st_mtime_ns for path in outputs}
            family_travel_observation_passport.build(
                pages, app_public=False
            )
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in outputs}
            )
            self.assertEqual(
                1,
                (tools / "index.html")
                .read_text(encoding="utf-8")
                .count(f"{family_travel_observation_passport.SLUG}.html"),
            )

    def test_trip_planet_resources_remain_first_and_unique(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            other = (
                '<article class="card third"><h2><a href="other.html">'
                "Other</a></h2><p>Other tool.</p></article>"
            )
            index = tools / "index.html"
            index.write_text(
                "<main>"
                + prioritize_trip_planet_resources.GRID_MARKER
                + other
                + "</section></main>",
                encoding="utf-8",
            )

            index_mutators = (
                family_travel_observation_passport.update_tools_index,
                family_travel_mission_cards.update_tools_index,
                zhuyin_readiness_tool.update_tools_index,
                zhuyin_grandparent_call_kit.update_tools_index,
                zhuyin_picture_book_club_kit.update_tools_index,
                zhuyin_parent_teacher_handoff_kit.update_tools_index,
                zhuyin_library_storytime_kit.update_tools_index,
                zhuyin_grade1_summer_calendar.update_tools_index,
                zhuyin_anki_deck.update_tools_index,
            )

            def run_complete_tool_sequence() -> None:
                for mutate in index_mutators:
                    mutate(pages)
                prioritize_trip_planet_resources.prioritize(pages)

            run_complete_tool_sequence()
            prioritized = index.read_text(encoding="utf-8")
            mission_href = prioritize_trip_planet_resources.PRIORITY_HREFS[0]
            passport_href = prioritize_trip_planet_resources.PRIORITY_HREFS[1]
            self.assertLess(
                prioritized.index(mission_href), prioritized.index(passport_href)
            )
            self.assertLess(prioritized.index(passport_href), prioritized.index(other))
            self.assertLess(
                prioritized.index(passport_href),
                prioritized.index(f"{zhuyin_anki_deck.SLUG}.html"),
            )
            self.assertLess(
                prioritized.index(f"{zhuyin_anki_deck.SLUG}.html"),
                prioritized.index(other),
            )
            for href in prioritize_trip_planet_resources.PRIORITY_HREFS:
                self.assertEqual(1, prioritized.count(href))
            mtime = index.stat().st_mtime_ns
            self.assertFalse(prioritize_trip_planet_resources.prioritize(pages))
            self.assertEqual(mtime, index.stat().st_mtime_ns)
            run_complete_tool_sequence()
            self.assertEqual(prioritized, index.read_text(encoding="utf-8"))

    def test_family_travel_cards_build_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            urls = family_travel_mission_cards.build(pages, app_public=False)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{family_travel_mission_cards.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{family_travel_mission_cards.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                index.count(
                    f"{family_travel_mission_cards.SLUG}.html"
                ),
            )

    def test_family_travel_answer_leads_with_free_private_generator(self):
        question = (
            "How can I make printable travel missions for kids without sharing "
            "their data?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "tripplanet"),
            question,
            "tripplanet",
        )
        page = aeo_answers.render_page(question, "tripplanet", content)
        self.assertEqual(
            f"{family_travel_mission_cards.SITE}/tools/"
            f"{family_travel_mission_cards.SLUG}.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>Free Private Printable Travel Mission Card Generator</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free private travel mission-card generator"),
            page.index("Get Lumi Trip Planet on the App Store"),
        )
        self.assertIn("Airport cards contain no photo tasks", page)
        self.assertIn("driver never reads, answers or operates", page)
        hero = page.split('<section class="hero', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("apps.apple.com", hero)

    def test_family_travel_answer_has_complete_resource_first_zh_hant_version(
        self,
    ):
        question = (
            "How can I make printable travel missions for kids without sharing "
            "their data?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "tripplanet"),
            question,
            "tripplanet",
        )
        source = aeo_answers.render_page(question, "tripplanet", content)
        mapping_path = Path(GEO) / "i18n_trans" / "zh-Hant.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [string for string in strings if string not in mapping]
        self.assertEqual([], missing)

        slug = (
            "how-can-i-make-printable-travel-missions-for-kids-without-"
            "sharing-their-data"
        )
        with tempfile.TemporaryDirectory() as directory:
            localized_tool = (
                Path(directory)
                / "zh-Hant"
                / "tools"
                / f"{family_travel_mission_cards.SLUG}.html"
            )
            localized_tool.parent.mkdir(parents=True)
            localized_tool.write_text("<html></html>", encoding="utf-8")
            with mock.patch.object(
                aeo_answers_i18n, "ROOT", Path(directory)
            ):
                localized = aeo_answers_i18n.render_localized(
                    source,
                    "zh-Hant",
                    slug,
                    {string: mapping[string] for string in strings},
                )
        resource_url = (
            f"{family_travel_mission_cards.SITE}/zh-Hant/tools/"
            f"{family_travel_mission_cards.SLUG}.html"
        )
        app_url = (
            f"https://apps.apple.com/app/id{family_travel_mission_cards.APP_ID}"
            "?ct=iag_ans"
        )
        main = localized.split("<main>", 1)[1]
        self.assertIn(
            "<title>免費私密可列印旅行任務卡產生器</title>",
            localized,
        )
        self.assertLess(main.index(resource_url), main.index(app_url))
        self.assertIn("機場卡沒有拍照任務", localized)
        self.assertIn("駕駛在行車時絕不閱讀、回答或操作", localized)
        self.assertNotIn(
            "How can I make printable travel missions",
            localized,
        )

    def test_grade1_guide_is_resource_first_and_makes_no_readiness_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            localized_guides = pages / "zh-Hant" / "guides"
            localized_guides.mkdir(parents=True)
            (localized_guides / "existing.html").write_text(
                "<html></html>", encoding="utf-8"
            )
            url = zhuyin_grade1_guide.build(pages)
            page = (
                pages / "guides" / f"{zhuyin_grade1_guide.SLUG}.html"
            ).read_text(encoding="utf-8")
            sitemap = (pages / "sitemap_guides.xml").read_text(
                encoding="utf-8"
            )

        calendar_url = zhuyin_grade1_guide.CALENDAR_URL
        self.assertEqual(
            f"{zhuyin_grade1_guide.SITE}/guides/"
            f"{zhuyin_grade1_guide.SLUG}.html",
            url,
        )
        self.assertLess(page.index(calendar_url), page.index("id6773017109"))
        self.assertIn("尚未經研究評估", page)
        self.assertIn("不教完或評量全部 37 個符號", page)
        self.assertIn('"@type": "LearningResource"', page)
        self.assertNotIn('"price": "0"', page)
        self.assertNotIn("前十週", page)
        self.assertNotIn("不會落後", page)
        self.assertNotIn("黃金期", page)
        self.assertIn("/zh-Hant/tools/", page)
        self.assertIn("/zh-Hant/guides/existing.html", sitemap)

    def test_grade1_summer_calendar_is_bilingual_private_and_non_scored(self):
        english = zhuyin_grade1_summer_calendar.render_page("en")
        traditional = zhuyin_grade1_summer_calendar.render_page("zh-Hant")
        for page in (english, traditional):
            self.assertIn('"WebApplication", "LearningResource"', page)
            self.assertIn('"@type": "HowTo"', page)
            self.assertIn('"@type": "FAQPage"', page)
            self.assertIn("creativecommons.org/licenses/by/4.0/", page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("html_ch/index.html", page)
            self.assertIn("phonetic.jsp?la=0", page)
            self.assertIn("id6773017109", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("getUserMedia", page)
            self.assertNotIn("<input", page)
            schemas = [
                json.loads(block)
                for block in re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    page,
                    re.S,
                )
            ]
            howto = next(
                schema for schema in schemas if schema.get("@type") == "HowTo"
            )
            self.assertEqual(14, len(howto["step"]))
        self.assertIn("does not teach or assess all 37 symbols", english)
        self.assertIn("has not been evaluated in a study", english)
        self.assertIn("No completion tracking", english)
        self.assertIn("不教完或評量全部 37 個符號", traditional)
        self.assertIn("尚未經研究評估", traditional)
        self.assertIn("沒有完成度追蹤", traditional)
        for page in (english, traditional):
            main = page.split("<main>", 1)[1]
            self.assertLess(
                main.index("zhuyin-readiness-check.html"),
                main.index("id6773017109"),
            )

    def test_answer_force_refresh_overwrites_an_existing_curated_page(self):
        question = (
            "How can my child prepare for grade 1 Bopomofo over the summer "
            "before school starts?"
        )
        slug = aeo_answers.slugify(question)
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            aeo_answers, "ANSWERS_DIR", Path(directory)
        ):
            path = Path(directory) / f"{slug}.html"
            path.write_text("stale", encoding="utf-8")
            refreshed = aeo_answers.create_page(
                "lumibopomofo", question, force=True
            )
            output = path.read_text(encoding="utf-8")
        self.assertEqual(slug, refreshed)
        self.assertNotEqual("stale", output)
        self.assertIn("Free 14-Day Grade 1 Zhuyin", output)

    def test_grade1_summer_calendar_builds_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            urls = zhuyin_grade1_summer_calendar.build(pages)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{zhuyin_grade1_summer_calendar.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{zhuyin_grade1_summer_calendar.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1, index.count("zhuyin-grade1-14-day-summer-calendar.html")
            )

    def test_grade1_summer_answer_leads_with_free_calendar(self):
        question = (
            "How can my child prepare for grade 1 Bopomofo over the summer "
            "before school starts?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(question, "lumibopomofo", content)
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/"
            "tools/zhuyin-grade1-14-day-summer-calendar.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>Free 14-Day Grade 1 Zhuyin Summer Warm-Up Calendar</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free 14-day summer calendar"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        self.assertIn("has not been evaluated in a study", page)
        self.assertIn("does not teach or assess all 37 symbols", page)
        self.assertNotIn("first ten weeks", page)
        self.assertNotIn("far less stressed", page)
        hero = page.split('<section class="hero', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("apps.apple.com", hero)

    def test_grade1_summer_answer_has_complete_resource_first_zh_hant_version(
        self,
    ):
        question = (
            "How can my child prepare for grade 1 Bopomofo over the summer "
            "before school starts?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        source = aeo_answers.render_page(question, "lumibopomofo", content)
        mapping_path = Path(GEO) / "i18n_trans" / "zh-Hant.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [string for string in strings if string not in mapping]
        self.assertEqual([], missing)

        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            "how-can-my-child-prepare-for-grade-1-bopomofo-over-the-summer-"
            "before-school-starts",
            {string: mapping[string] for string in strings},
        )
        calendar_url = (
            "https://alice51849.github.io/ios-app-guide/zh-Hant/tools/"
            "zhuyin-grade1-14-day-summer-calendar.html"
        )
        app_url = "https://apps.apple.com/app/id6773017109?ct=iag_ans"
        main = localized.split("<main>", 1)[1]
        self.assertIn(
            "<title>免費小一入學前 14 天注音暖身日曆</title>",
            localized,
        )
        self.assertLess(main.index(calendar_url), main.index(app_url))
        self.assertIn("尚未經研究評估", localized)
        self.assertIn("不教完或評量全部 37 個符號", localized)
        self.assertNotIn("前十週", localized)
        self.assertNotIn("不會落後", localized)

    def test_library_storytime_is_bilingual_private_and_rights_safe(self):
        english = zhuyin_library_storytime_kit.render_page("en")
        traditional = zhuyin_library_storytime_kit.render_page("zh-Hant")
        for page in (english, traditional):
            self.assertIn('"WebApplication", "LearningResource"', page)
            self.assertIn('"@type": "HowTo"', page)
            self.assertIn('"@type": "FAQPage"', page)
            self.assertIn("creativecommons.org/licenses/by/4.0/", page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("centaur.reading.ac.uk/80756", page)
            self.assertIn("id6773017109", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("getUserMedia", page)
            self.assertNotIn("<input", page)
        self.assertIn("grants no right to perform", english)
        self.assertIn("did not test group library storytime", english)
        self.assertIn("no registration, name field, attendance form", english)
        self.assertIn("不授予朗讀、展示、錄影、直播", traditional)
        self.assertIn("沒有測試圖書館團體故事時間", traditional)
        self.assertIn("一次性永久解鎖", traditional)

    def test_library_storytime_builds_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            urls = zhuyin_library_storytime_kit.build(pages)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{zhuyin_library_storytime_kit.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{zhuyin_library_storytime_kit.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count("zhuyin-library-storytime-kit.html"))

    def test_library_storytime_answer_leads_with_free_kit(self):
        question = "How can a library run a Zhuyin storytime for families?"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(question, "lumibopomofo", content)
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/"
            "tools/zhuyin-library-storytime-kit.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>Free Zhuyin Library Storytime Kit for Families</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free library storytime kit"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        self.assertIn("grants no right to perform", page)
        self.assertIn("did not test group library storytime", page)
        self.assertIn("d = 0.41", page)
        self.assertIn("d = 0.26", page)
        self.assertIn("d = 1.01", page)
        schemas = [
            json.loads(block)
            for block in re.findall(
                r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
                page,
                re.S,
            )
        ]
        software = next(
            schema for schema in schemas if schema.get("@type") == "SoftwareApplication"
        )
        resource = next(
            schema for schema in schemas if schema.get("@type") == "LearningResource"
        )
        self.assertEqual(content["where_app_fits"], software["description"])
        self.assertEqual(content["primary_resource_url"], resource["url"])
        self.assertNotEqual(content["meta_description"], software["description"])

    def test_library_storytime_answer_has_complete_resource_first_zh_hant_version(
        self,
    ):
        question = "How can a library run a Zhuyin storytime for families?"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        source = aeo_answers.render_page(question, "lumibopomofo", content)
        mapping_path = Path(GEO) / "i18n_trans" / "zh-Hant.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [string for string in strings if string not in mapping]
        self.assertEqual([], missing)

        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            "how-can-a-library-run-a-zhuyin-storytime-for-families",
            {string: mapping[string] for string in strings},
        )
        kit_url = (
            "https://alice51849.github.io/ios-app-guide/zh-Hant/"
            "tools/zhuyin-library-storytime-kit.html"
        )
        app_url = "https://apps.apple.com/app/id6773017109?ct=iag_ans"
        main = localized.split("<main>", 1)[1]
        self.assertIn("<title>免費圖書館注音親子故事時間包</title>", localized)
        self.assertLess(main.index(kit_url), main.index(app_url))
        self.assertIn("不授予朗讀、展示、錄影或散布書籍的權利", localized)
        self.assertIn("沒有測試圖書館團體故事時間", localized)
        self.assertIn("d = 0.41", localized)
        self.assertNotIn("對第一次學注音的孩子", localized)
        schemas = [
            json.loads(block)
            for block in re.findall(
                r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
                localized,
                re.S,
            )
        ]
        breadcrumb = next(
            schema for schema in schemas if schema.get("@type") == "BreadcrumbList"
        )
        software = next(
            schema for schema in schemas if schema.get("@type") == "SoftwareApplication"
        )
        resource = next(
            schema for schema in schemas if schema.get("@type") == "LearningResource"
        )
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/zh-Hant/answers/"
            "how-can-a-library-run-a-zhuyin-storytime-for-families.html",
            breadcrumb["itemListElement"][-1]["item"],
        )
        self.assertEqual(kit_url, resource["url"])
        self.assertIn("選用的家庭練習層", software["description"])

    def test_parent_teacher_handoff_is_bilingual_private_and_non_scored(self):
        english = zhuyin_parent_teacher_handoff_kit.render_page("en")
        traditional = zhuyin_parent_teacher_handoff_kit.render_page("zh-Hant")
        for page in (english, traditional):
            self.assertIn('"WebApplication", "LearningResource"', page)
            self.assertIn('"@type": "HowTo"', page)
            self.assertIn("creativecommons.org/licenses/by/4.0/", page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("phoneticWrite.jsp", page)
            self.assertIn("id6773017109", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("getUserMedia", page)
            self.assertNotIn("<input", page)
        self.assertIn("has not been evaluated in a trial", english)
        self.assertIn("records participation, not correctness", english)
        self.assertIn("尚未經試驗評估", traditional)
        self.assertIn("不標對錯，也不給分", traditional)
        self.assertIn("optional one-time lifetime unlock", english)
        self.assertIn("一次性永久解鎖", traditional)

    def test_parent_teacher_handoff_builds_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            urls = zhuyin_parent_teacher_handoff_kit.build(pages)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{zhuyin_parent_teacher_handoff_kit.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{zhuyin_parent_teacher_handoff_kit.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1, index.count("zhuyin-parent-teacher-handoff-kit.html")
            )

    def test_bopomofo_tools_are_shared_with_lite_and_pro_answers(self):
        self.assertEqual(
            add_related_tools.BOPOMOFO_APP_IDS,
            add_related_tools.related_app_ids(
                "6773017109", "zhuyin-parent-teacher-handoff-kit"
            ),
        )
        self.assertEqual(
            add_related_tools.BOPOMOFO_APP_IDS,
            add_related_tools.related_app_ids(
                "6775773117", "zhuyin-parent-teacher-handoff-kit"
            ),
        )
        self.assertEqual(
            add_related_tools.BOPOMOFO_APP_IDS,
            add_related_tools.related_app_ids(
                "6773017109", "zhuyin-grade1-14-day-summer-calendar"
            ),
        )
        self.assertEqual(
            ("6773017109",),
            add_related_tools.related_app_ids("6773017109", "screen-time-calculator"),
        )

    def test_weekend_school_answer_leads_with_free_handoff_kit(self):
        question = "App to reinforce weekend Chinese school Bopomofo lessons at home"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(question, "lumibopomofo", content)
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/"
            "tools/zhuyin-parent-teacher-handoff-kit.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>Free Zhuyin Parent-Teacher Handoff Kit for "
            "Weekend Chinese School</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free parent-teacher handoff kit"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        self.assertIn("has not been evaluated in a trial", page)
        self.assertIn("records participation rather than correctness", page)
        self.assertIn("not endorsements of this kit", page)

    def test_weekend_school_answer_has_complete_resource_first_zh_hant_version(self):
        question = "App to reinforce weekend Chinese school Bopomofo lessons at home"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        source = aeo_answers.render_page(question, "lumibopomofo", content)
        mapping_path = Path(GEO) / "i18n_trans" / "zh-Hant.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [string for string in strings if string not in mapping]
        self.assertEqual([], missing)

        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            "app-to-reinforce-weekend-chinese-school-bopomofo-lessons-at-home",
            {string: mapping[string] for string in strings},
        )
        kit_url = (
            "https://alice51849.github.io/ios-app-guide/zh-Hant/"
            "tools/zhuyin-parent-teacher-handoff-kit.html"
        )
        app_url = "https://apps.apple.com/app/id6773017109?ct=iag_ans"
        main = localized.split("<main>", 1)[1]
        self.assertIn("<title>免費注音家庭—教師交接包</title>", localized)
        self.assertLess(main.index(kit_url), main.index(app_url))
        self.assertIn("尚未經試驗評估", localized)
        self.assertIn("記錄參與方式，而不是對錯", localized)
        self.assertNotIn("對幼兒來說,一款專注的 App 勝過練習表", localized)

    def test_picture_book_club_is_bilingual_private_and_copyright_safe(self):
        english = zhuyin_picture_book_club_kit.render_page("en")
        traditional = zhuyin_picture_book_club_kit.render_page("zh-Hant")
        for page in (english, traditional):
            self.assertIn('"WebApplication", "LearningResource"', page)
            self.assertIn('"@type": "HowTo"', page)
            self.assertIn("creativecommons.org/licenses/by/4.0/", page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("centaur.reading.ac.uk/80756", page)
            self.assertIn("dict.mini.moe.edu.tw", page)
            self.assertIn("id6773017109", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("getUserMedia", page)
            self.assertNotIn("<input", page)
        self.assertIn("does not host, reproduce", english)
        self.assertIn("did not test Zhuyin", english)
        self.assertIn("不託管、不重製", traditional)
        self.assertIn("沒有測試注音", traditional)
        self.assertIn("one-time lifetime unlock", english)
        self.assertIn("一次性永久解鎖", traditional)

    def test_picture_book_club_builds_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            urls = zhuyin_picture_book_club_kit.build(pages)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{zhuyin_picture_book_club_kit.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{zhuyin_picture_book_club_kit.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1, index.count("zhuyin-family-picture-book-club-kit.html")
            )

    def test_picture_book_answer_leads_with_free_club_kit(self):
        question = "Help my child read Taiwanese picture books with Zhuyin annotations"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(question, "lumibopomofo", content)
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/"
            "tools/zhuyin-family-picture-book-club-kit.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>Free 4-Week Zhuyin Picture-Book Club Kit for Families</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free family picture-book club kit"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        self.assertIn("did not test Zhuyin", page)
        self.assertIn("does not host or link to unauthorized book copies", page)
        self.assertIn("d = 0.41", page)
        self.assertIn("d = 0.26", page)
        self.assertIn("d = 1.01", page)

    def test_picture_book_answer_has_complete_resource_first_zh_hant_version(self):
        question = "Help my child read Taiwanese picture books with Zhuyin annotations"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        source = aeo_answers.render_page(question, "lumibopomofo", content)
        mapping_path = Path(GEO) / "i18n_trans" / "zh-Hant.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [string for string in strings if string not in mapping]
        self.assertEqual([], missing)

        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            "help-my-child-read-taiwanese-picture-books-with-zhuyin-annotations",
            {string: mapping[string] for string in strings},
        )
        kit_url = (
            "https://alice51849.github.io/ios-app-guide/zh-Hant/"
            "tools/zhuyin-family-picture-book-club-kit.html"
        )
        app_url = "https://apps.apple.com/app/id6773017109?ct=iag_ans"
        main = localized.split("<main>", 1)[1]
        self.assertIn("<title>免費四週家庭注音繪本共讀包</title>", localized)
        self.assertLess(main.index(kit_url), main.index(app_url))
        self.assertIn("該回顧沒有測試注音", localized)
        self.assertIn("不託管或連結未授權的繪本副本", localized)
        self.assertIn("d = 0.41", localized)
        self.assertIn("d = 0.26", localized)
        self.assertIn("d = 1.01", localized)
        self.assertNotIn("對第一次學注音的孩子", localized)

    def test_grandparent_call_kit_is_bilingual_private_and_evidence_limited(self):
        english = zhuyin_grandparent_call_kit.render_page("en")
        traditional = zhuyin_grandparent_call_kit.render_page("zh-Hant")
        for page in (english, traditional):
            self.assertIn('"WebApplication", "LearningResource"', page)
            self.assertIn("creativecommons.org/licenses/by/4.0/", page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("PMC9539353", page)
            self.assertIn("id6773017109", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("getUserMedia", page)
        self.assertIn("did not test Zhuyin learning or this kit", english)
        self.assertIn("沒有測試注音學習，也沒有測試本工具", traditional)
        self.assertIn("one-time lifetime unlock", english)
        self.assertIn("一次性永久解鎖", traditional)

    def test_grandparent_call_kit_builds_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            urls = zhuyin_grandparent_call_kit.build(pages)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{zhuyin_grandparent_call_kit.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{zhuyin_grandparent_call_kit.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1, index.count("zhuyin-grandparent-video-call-kit.html")
            )

    def test_grandparent_answer_leads_with_free_call_kit(self):
        question = (
            "How can grandparents in Taiwan help a child abroad learn "
            "Bopomofo over video call?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(question, "lumibopomofo", content)
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/"
            "tools/zhuyin-grandparent-video-call-kit.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>Free Zhuyin Video-Call Kit for Grandparents and Kids</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free grandparent video-call kit"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        self.assertIn("did not test Zhuyin or this kit", page)

    def test_grandparent_answer_has_complete_resource_first_zh_hant_version(self):
        question = (
            "How can grandparents in Taiwan help a child abroad learn "
            "Bopomofo over video call?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        source = aeo_answers.render_page(question, "lumibopomofo", content)
        mapping_path = Path(GEO) / "i18n_trans" / "zh-Hant.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [string for string in strings if string not in mapping]
        self.assertEqual([], missing)

        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            "how-can-grandparents-in-taiwan-help-a-child-abroad-"
            "learn-bopomofo-over-video-call",
            {string: mapping[string] for string in strings},
        )
        kit_url = (
            "https://alice51849.github.io/ios-app-guide/zh-Hant/"
            "tools/zhuyin-grandparent-video-call-kit.html"
        )
        app_url = "https://apps.apple.com/app/id6773017109?ct=iag_ans"
        main = localized.split("<main>", 1)[1]
        self.assertIn("<title>免費祖孫注音視訊遊戲包</title>", localized)
        self.assertLess(main.index(kit_url), main.index(app_url))
        self.assertIn("該研究並未測試注音或這套工具", localized)
        self.assertNotIn("對第一次學注音的孩子", localized)

    def test_zhuyin_observation_guide_is_private_non_scored_and_non_diagnostic(self):
        english = zhuyin_readiness_tool.render_page("en")
        traditional = zhuyin_readiness_tool.render_page("zh-Hant")
        for tasks in zhuyin_readiness_tool.TASKS.values():
            for task in tasks:
                self.assertTrue(all(len(option) == 2 for option in task["options"]))
        for page in (english, traditional):
            self.assertIn('"WebApplication", "LearningResource"', page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn("id=\"skills-form\"", page)
            self.assertIn("id=\"result\"", page)
            self.assertIn("id6773017109", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn('id="stage-name"', page)
            self.assertNotIn("cfg.stages", page)
            self.assertNotIn("value*50", page)
            self.assertNotIn(" / 2", page)
            self.assertNotIn('value="0"', page)
            main = page.split("<main>", 1)[1]
            self.assertLess(
                main.index("14-day" if page is english else "14 天"),
                main.index("id6773017109"),
            )
        self.assertIn("not a school assessment", english)
        self.assertIn("cannot determine school readiness", english)
        self.assertIn("without a total, score or level", english)
        self.assertIn("不是學校評量", traditional)
        self.assertIn("不是官方評量", traditional)
        self.assertIn("不產生總分或分級", traditional)
        self.assertIn("one-time lifetime unlock", english)
        self.assertIn("一次性永久解鎖", traditional)

    def test_zhuyin_skills_check_builds_both_pages_and_index_card(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            tools = pages / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            urls = zhuyin_readiness_tool.build(pages)
            self.assertEqual(2, len(urls))
            self.assertTrue(
                (tools / f"{zhuyin_readiness_tool.SLUG}.html").exists()
            )
            self.assertTrue(
                (
                    pages
                    / "zh-Hant"
                    / "tools"
                    / f"{zhuyin_readiness_tool.SLUG}.html"
                ).exists()
            )
            index = (tools / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count("zhuyin-readiness-check.html"))

    def test_zhuyin_skills_answer_leads_with_free_resource(self):
        question = (
            "How can I check my child's Zhuyin skills at home in three minutes?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(question, "lumibopomofo", content)
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/"
            "tools/zhuyin-readiness-check.html",
            content["primary_resource_url"],
        )
        self.assertIn(
            "<title>3-Minute Zhuyin Observation Guide | "
            "Free Private Parent Tool</title>",
            page,
        )
        self.assertLess(
            page.index("Open the free 3-minute observation guide"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        hero = page.split('<section class="hero', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("apps.apple.com", hero)
        mapping = json.loads(
            (
                Path(GEO) / "i18n_trans" / "zh-Hant.json"
            ).read_text(encoding="utf-8")
        )
        strings, _, _ = aeo_answers_i18n.extract_strings(page)
        self.assertEqual([], [string for string in strings if string not in mapping])
        localized = aeo_answers_i18n.render_localized(
            page,
            "zh-Hant",
            "how-can-i-check-my-child-s-zhuyin-skills-at-home-in-three-minutes",
            {string: mapping[string] for string in strings},
        )
        localized_main = localized.split("<main>", 1)[1]
        self.assertLess(
            localized_main.index(
                "/zh-Hant/tools/zhuyin-readiness-check.html"
            ),
            localized_main.index("id6773017109"),
        )
        self.assertIn("不產生總分、分數、階段或分級", localized)
        self.assertIn("Sources and resources", page)

    def test_i18n_force_requires_an_explicit_answer_slug(self):
        argv = [
            "aeo_answers_i18n.py",
            "--langs",
            "zh-Hant",
            "--trans",
            "i18n_trans",
            "--force",
        ]
        with mock.patch.object(sys, "argv", argv), mock.patch(
            "sys.stderr"
        ), self.assertRaises(SystemExit) as raised:
            aeo_answers_i18n.main()
        self.assertEqual(2, raised.exception.code)

    def test_heritage_lesson_plan_is_bilingual_and_honest(self):
        english = zhuyin_heritage_lesson_plan.render_page("en")
        traditional = zhuyin_heritage_lesson_plan.render_page("zh-Hant")
        for page in (english, traditional):
            self.assertIn('"@type": "LearningResource"', page)
            self.assertIn("creativecommons.org/licenses/by/4.0/", page)
            self.assertIn('hreflang="en"', page)
            self.assertIn('hreflang="zh-Hant"', page)
            self.assertIn(
                "https://language.moe.gov.tw/001/Upload/files/site_content/"
                "M0001/juyin/index.html",
                page,
            )
        self.assertIn("Ministry of Education", english)
        self.assertIn("台灣教育部", traditional)
        self.assertIn("does not claim to teach all 37", english)
        self.assertIn("不宣稱五天就能學完全部 37 個注音", traditional)
        self.assertIn("one-time lifetime unlock", english)
        self.assertNotIn("subscription option", english)

    def test_heritage_lesson_plan_builds_both_pages_and_sitemap(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            urls = zhuyin_heritage_lesson_plan.build(pages)
            self.assertEqual(2, len(urls))
            for locale in ("", "zh-Hant/"):
                target = (
                    pages
                    / locale
                    / "guides"
                    / f"{zhuyin_heritage_lesson_plan.SLUG}.html"
                )
                self.assertTrue(target.exists())
            sitemap = (pages / "sitemap_guides.xml").read_text(encoding="utf-8")
            self.assertIn(urls[0], sitemap)
            self.assertIn(urls[1], sitemap)

    def test_answer_localizer_keeps_alternative_links_canonical(self):
        url = (
            "https://alice51849.github.io/ios-app-guide/"
            "alternatives/aim990-free-to-start.html"
        )
        self.assertEqual(url, aeo_answers_i18n.localize_url(url, "zh-Hant"))
        self.assertEqual(
            "https://alice51849.github.io/ios-app-guide/zh-Hant/guides/aim990.html",
            aeo_answers_i18n.localize_url(
                "https://alice51849.github.io/ios-app-guide/guides/aim990.html",
                "zh-Hant",
            ),
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            aeo_answers_i18n, "ROOT", Path(directory)
        ):
            localized = Path(directory) / "zh-Hant" / "tools"
            localized.mkdir(parents=True)
            (localized / "helper.html").write_text("")
            self.assertEqual(
                "https://alice51849.github.io/ios-app-guide/"
                "zh-Hant/tools/helper.html?x=1#result",
                aeo_answers_i18n.localize_url(
                    "https://alice51849.github.io/ios-app-guide/"
                    "tools/helper.html?x=1#result",
                    "zh-Hant",
                ),
            )
            missing = (
                "https://alice51849.github.io/ios-app-guide/"
                "tools/missing.html"
            )
            self.assertEqual(
                missing, aeo_answers_i18n.localize_url(missing, "zh-Hant")
            )

    def test_multilingual_pricing_copy_uses_accurate_profiles(self):
        self.assertIn(
            "一次性購買",
            build_pages_i18n.pricing_text_for("aim990", "zh-Hant"),
        )
        self.assertIn(
            "定期課金はありません",
            build_pages_i18n.pricing_text_for("lumibopomofo", "ja"),
        )
        verified = build_pages_i18n.pricing_text_for("snapport", "en-US").lower()
        self.assertIn("paid download", verified)
        self.assertIn("no subscription", verified)
        self.assertNotIn("free to download", verified)
        aim_description = build_pages_i18n.load_app_locales("aim990")[
            "zh-Hant"
        ]["description"]
        sanitized = build_pages_i18n.sanitize_description(
            "aim990", "zh-Hant", aim_description
        )
        self.assertIn("無需訂閱", sanitized)
        self.assertNotIn("可選訂閱方案", sanitized)
        en_gb = build_pages_i18n.load_app_locales("aim990")[
            "en-GB"
        ]["description"]
        sanitized_en_gb = build_pages_i18n.sanitize_description(
            "aim990", "en-GB", en_gb
        )
        self.assertIn("without a subscription", sanitized_en_gb.lower())
        self.assertNotIn("optional subscription", sanitized_en_gb.lower())
        mochi_pricing = build_pages_i18n.pricing_text_for(
            "mochi", "en-US"
        )
        self.assertIn("Free to download", mochi_pricing)
        self.assertIn("one-time purchase", mochi_pricing)
        self.assertIn("Paid download", build_pages.pricing_copy("snapport"))
        aim_pricing = build_pages.pricing_copy("aim990")
        self.assertIn("Free to download", aim_pricing)
        self.assertIn("no recurring subscription", aim_pricing)
        self.assertNotIn("or subscription", aim_pricing)
        paid_description = (
            "A calm routine app.\n"
            "• Free to download, one-time unlock\n"
            "Built for families."
        )
        sanitized_paid = build_pages_i18n.sanitize_description(
            "lumimissionpro", "en-AU", paid_description
        )
        self.assertNotIn("Free to download", sanitized_paid)
        self.assertIn("Paid download", sanitized_paid)

    def test_registry_only_apps_get_complete_english_landing_pages(self):
        name, sub, desc, keywords = build_pages_i18n._meta_from(
            {}, APPS["mochi"]
        )
        self.assertEqual("Mochi", name)
        self.assertTrue(sub)
        self.assertTrue(desc)
        self.assertTrue(keywords)
        self.assertEqual(["en-US"], build_pages_i18n.all_locales_for("mochi"))
        locales = build_pages_i18n.master_locales_for(
            ["mochi", "snapport"]
        )
        self.assertIn("zh-Hant", locales)
        self.assertEqual(
            locales,
            build_pages_i18n.master_locales_for(["snapport", "mochi"]),
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            build_pages_i18n, "PAGES", directory
        ):
            output = build_pages_i18n.build_one(
                "mochi", "en-US", ["en-US"]
            )
            page = Path(output).read_text(encoding="utf-8")
        self.assertIn(APPS["mochi"]["sub"], page)
        self.assertIn("Free to download", page)
        self.assertNotIn("<meta name=\"description\" content=\"\">", page)

    def test_registry_purchase_models_are_explicit_and_verified(self):
        paid_upfront = {
            "snapport",
            "gmoney",
            "hourstag",
            "lumiletterspro",
            "lumimathpro",
            "lumimissionpro",
            "lumibopomofopro",
            "tripbee",
        }
        free_with_unlock = {
            "sononote",
            "cvdesk",
            "picclear",
            "scanto",
            "cyca",
            "lockhour",
            "unblurry",
            "photocream",
            "lumiletters",
            "lumimath",
            "lumimission",
            "lumiweather",
            "lumibopomofo",
            "zodira",
            "aim990",
            "mochi",
            "zafe",
            "tripplanet",
            "sereno",
        }
        self.assertEqual(paid_upfront | free_with_unlock, set(APPS))
        for key in paid_upfront:
            self.assertEqual("paid_upfront", APPS[key]["purchase_model"])
        for key in free_with_unlock:
            self.assertEqual(
                "free_with_lifetime_unlock", APPS[key]["purchase_model"]
            )
        self.assertTrue(
            all(
                app["purchase_model"] in VALID_PURCHASE_MODELS
                for app in APPS.values()
            )
        )

    def test_purchase_model_classifier_is_conservative(self):
        self.assertEqual(
            "paid_upfront", classify_purchase_model(4.99, [], False)
        )
        self.assertEqual(
            "free_with_lifetime_unlock",
            classify_purchase_model(0, ["NON_CONSUMABLE"], False),
        )
        self.assertEqual("free", classify_purchase_model(0, [], False))
        self.assertEqual(
            "neutral",
            classify_purchase_model(0, ["NON_CONSUMABLE"], True),
        )
        self.assertEqual(
            "neutral", classify_purchase_model(0, ["CONSUMABLE"], False)
        )
        self.assertEqual(
            "neutral", classify_purchase_model(None, ["NON_CONSUMABLE"], False)
        )

    def test_unknown_pricing_never_infers_claims_from_marketing_copy(self):
        unknown = {
            "name": "Unknown",
            "category": "productivity",
            "tag": "Pay once · No subscription",
            "cta_bullets": ["Pay once", "No subscription"],
            "purchase_model": "neutral",
        }
        with mock.patch.dict(aeo_pages.APPS, {"unknown": unknown}):
            self.assertEqual("neutral", aeo_pages.pricing_profile("unknown"))
            self.assertFalse(aeo_pages.has_one_time_access("unknown"))
            attrs = aeo_pages.app_attrs("unknown")
            self.assertFalse(attrs["Pay once"])
            self.assertFalse(attrs["No subscription"])

    def test_localized_cleanup_removes_stale_pricing_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            root_alt = pages / "alternatives"
            localized = pages / "zh-Hant"
            localized_alt = localized / "alternatives"
            localized_answers = localized / "answers"
            root_alt.mkdir()
            localized_alt.mkdir(parents=True)
            localized_answers.mkdir()
            root_tools = pages / "tools"
            root_tools.mkdir()
            (root_tools / "helper.html").write_text("tool", encoding="utf-8")
            (root_alt / "snapport-no-subscription.html").write_text("")
            (root_alt / "gmoney-no-subscription.html").write_text("")
            (root_alt / "index.html").write_text("")
            (localized_alt / "snapport-private-alternative.html").write_text(
                "stale pricing", encoding="utf-8"
            )
            (localized_alt / "gmoney-no-subscription.html").write_text(
                "accurate pricing", encoding="utf-8"
            )
            (localized / "zodira.html").write_text("unlisted", encoding="utf-8")
            localized_guides = localized / "guides"
            localized_guides.mkdir()
            localized_guide = localized_guides / "snapport.html"
            localized_guide.write_text(
                '<script type="application/ld+json">{"description":"x",'
                '"offers":{"@type":"Offer","price":"0",'
                '"priceCurrency":"USD"}}</script>',
                encoding="utf-8",
            )
            answer = localized_answers / "passport.html"
            answer.write_text(
                f'<a href="{cleanup_localized_assets.SITE}/zh-Hant/'
                'alternatives/snapport-private-alternative.html">guide</a>'
                f'<a href="{cleanup_localized_assets.SITE}/alternatives/'
                'zafe-no-subscription.html">old app</a>'
                f'<a href="{cleanup_localized_assets.SITE}/zh-Hant/'
                'tools/helper.html">localized tool fallback</a>'
                f'<link rel="alternate" hreflang="en" href="'
                f'{cleanup_localized_assets.SITE}/answers/passport.html">'
                f'<link rel="alternate" hreflang="zh" href="'
                f'{cleanup_localized_assets.SITE}/zh-Hant/answers/passport.html">'
                f'<link rel="alternate" hreflang="ja" href="'
                f'{cleanup_localized_assets.SITE}/ja/answers/passport.html">'
                f'<li><a href="{cleanup_localized_assets.SITE}/zh-Hant/'
                'answers/missing.html">dead related answer</a></li>'
                '<script type="application/ld+json">{"description":"x",'
                '"offers":{"@type":"Offer","price":"0",'
                '"priceCurrency":"USD"},"featureList":[]}</script>',
                encoding="utf-8",
            )
            (pages / "answers").mkdir()
            (pages / "answers" / "passport.html").write_text("")
            guides = pages / "guides"
            guides.mkdir()
            snapport_guide = guides / "snapport.html"
            snapport_guide.write_text(
                '<script type="application/ld+json">{"description":"x",'
                '"offers":{"@type":"Offer","price":"0",'
                '"priceCurrency":"USD"},"featureList":[]}</script>',
                encoding="utf-8",
            )
            (guides / "zodira.html").write_text(
                "unlisted guide", encoding="utf-8"
            )
            unlisted_answer = pages / "answers" / "unlisted.html"
            unlisted_id = cleanup_localized_assets.APPSTORE["zodira"]
            unlisted_answer.write_text(
                f"https://apps.apple.com/app/id{unlisted_id} "
                f"https://apps.apple.com/app/id{unlisted_id}",
                encoding="utf-8",
            )
            unlisted_schema_answer = pages / "answers" / "astrology.html"
            unlisted_schema_answer.write_text(
                '<script type="application/ld+json">'
                '{"@type":"SoftwareApplication","name":"Zodira"}'
                "</script>",
                encoding="utf-8",
            )
            stale_roundup = (
                localized_answers
                / "best-pay-once-to-do-list-checklist-app-2026.html"
            )
            stale_roundup.write_text("stale pricing", encoding="utf-8")
            root_answer = pages / "answers" / "old-app.html"
            root_answer.write_text(
                f'<a href="{cleanup_localized_assets.SITE}/alternatives/'
                'zafe-no-subscription.html">old app</a>',
                encoding="utf-8",
            )
            (localized_alt / "index.html").write_text(
                '<ul><li><a href="snapport-no-subscription.html">Snapport</a></li>'
                '<li><a href="gmoney-no-subscription.html">G+Money</a></li></ul>',
                encoding="utf-8",
            )
            (localized / "index.html").write_text(
                '<ul><li><a href="zodira.html">Zodira</a></li></ul>',
                encoding="utf-8",
            )
            (pages / "sitemap.xml").write_text(
                '<?xml version="1.0"?><urlset>'
                f"<url><loc>{cleanup_localized_assets.SITE}/zh-Hant/zodira.html</loc></url>"
                f"<url><loc>{cleanup_localized_assets.SITE}/zh-Hant/answers/passport.html</loc></url>"
                "</urlset>",
                encoding="utf-8",
            )

            live = set(cleanup_localized_assets.APPSTORE) - {"zodira"}
            stats = cleanup_localized_assets.cleanup(pages, live)

            self.assertFalse(
                (localized_alt / "snapport-private-alternative.html").exists()
            )
            self.assertTrue((localized_alt / "gmoney-no-subscription.html").exists())
            self.assertFalse((localized / "zodira.html").exists())
            self.assertFalse(stale_roundup.exists())
            self.assertFalse(unlisted_answer.exists())
            self.assertFalse(unlisted_schema_answer.exists())
            self.assertIn(
                "/alternatives/snapport-no-subscription.html",
                answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "/zh-Hant/alternatives/",
                answer.read_text(encoding="utf-8"),
            )
            self.assertIn(
                f"{cleanup_localized_assets.SITE}/tools/helper.html",
                answer.read_text(encoding="utf-8"),
            )
            self.assertIn(
                'hreflang="zh-Hant"',
                answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                'hreflang="ja"',
                answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "dead related answer",
                answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                '"offers"',
                answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                '"offers"',
                snapport_guide.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                '"offers"',
                localized_guide.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "/alternatives/index.html",
                answer.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "/alternatives/index.html",
                root_answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "snapport-private-alternative",
                (localized_alt / "index.html").read_text(encoding="utf-8"),
            )
            self.assertEqual(2, stats["removed_unlisted_pages"])
            self.assertEqual(2, stats["removed_unlisted_answers"])
            self.assertEqual(1, stats["removed_stale_roundups"])
            self.assertEqual(1, stats["removed_sitemap_urls"])

    def test_cleanup_removes_legacy_nested_alternative_locales(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            legacy = pages / "alternatives" / "ja"
            legacy.mkdir(parents=True)
            (legacy / "old.html").write_text("legacy", encoding="utf-8")
            stats = cleanup_localized_assets.cleanup(pages, set(APPS))
            self.assertFalse(legacy.exists())
            self.assertEqual(1, stats["removed_alternatives"])

    def test_aim990_guide_claims_include_free_download(self):
        old = (
            '<p itemprop="text">Aim990是一款一次性購買的應用程式，'
            "無需訂閱。</p>"
        )
        updated, count = cleanup_localized_assets.sanitize_known_aim990_claims(
            old, "zh-Hant"
        )
        self.assertEqual(1, count)
        self.assertNotIn("無需訂閱", updated)
        self.assertIn("免費下載", updated)
        self.assertNotIn("可選訂閱方案", updated)
        optional = (
            "Aim990 offers both a one-time unlock option and subscription "
            "plans. Check the App Store for current pricing."
        )
        sanitized, count = (
            cleanup_localized_assets.sanitize_aim990_optional_claims(
                optional, "en-US"
            )
        )
        self.assertGreater(count, 0)
        self.assertNotIn("subscription plans", sanitized)
        self.assertIn("no subscription", sanitized)
        ja_bad = "買い切りアンロックオプションとサブスクリプションオプション"
        ja_sanitized, count = (
            cleanup_localized_assets.sanitize_aim990_optional_claims(
                f"Aim990: {ja_bad}", "ja"
            )
        )
        self.assertGreater(count, 0)
        self.assertNotIn(ja_bad, ja_sanitized)
        model_claim = (
            "Aim990 offers both a one-time unlock and subscription models. "
            "Flexible payment options including one-time purchase and "
            "subscriptions."
        )
        sanitized, count = (
            cleanup_localized_assets.sanitize_aim990_optional_claims(
                model_claim, "en-US"
            )
        )
        self.assertEqual(2, count)
        self.assertNotIn("subscription models", sanitized)
        self.assertNotIn("Flexible payment options", sanitized)
        pa_bad = (
            "Aim990: ਇੱਕ ਵਾਰੀ ਖੋਲ੍ਹਣ ਦਾ ਵਿਕਲਪ ਅਤੇ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਵਿਕਲਪ"
        )
        sanitized, count = (
            cleanup_localized_assets.sanitize_known_aim990_claims(
                pa_bad, "pa-IN"
            )
        )
        self.assertEqual(1, count)
        self.assertNotIn("ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਵਿਕਲਪ", sanitized)

    def test_cleanup_prunes_unlisted_public_surfaces(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            locale = pages / "en-US"
            for path in (
                locale,
                pages / "alternatives",
                pages / "answers",
                pages / "guides",
                pages / "hubs",
                pages / "stories" / "img",
                pages / "tools",
            ):
                path.mkdir(parents=True, exist_ok=True)

            tripplanet_id = cleanup_localized_assets.APPSTORE["tripplanet"]
            inactive_paths = [
                locale / "tripplanet.html",
                pages / "answers" / "best-tripplanet-app.html",
                pages / "guides" / "tripplanet.html",
                pages / "hubs" / "tripplanet.html",
                pages / "stories" / "tripplanet.html",
                pages / "stories" / "img" / "tripplanet-poster.jpg",
                pages / "alternatives" / "tripplanet-no-subscription.html",
                locale / "stories" / "tripplanet.html",
            ]
            for path in inactive_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Lumi Trip Planet", encoding="utf-8")
            inactive_paths[1].write_text(
                f"/id{tripplanet_id} /id{tripplanet_id}", encoding="utf-8"
            )

            (locale / "index.html").write_text(
                '<ul><li><a href="tripplanet.html">Lumi Trip Planet</a> — pending</li>'
                '<li><a href="snapport.html">Snapport</a> — public</li></ul>',
                encoding="utf-8",
            )
            (locale / "snapport.html").write_text("public", encoding="utf-8")
            zodira_id = cleanup_localized_assets.APPSTORE["zodira"]
            tool = pages / "tools" / "zodiac-compatibility-checker.html"
            tool.write_text(
                '<script type="application/ld+json">{"@type":'
                f'"SoftwareApplication","name":"Zodira","url":"/id{zodira_id}"'
                "}</script>"
                f'<p><a href="https://apps.apple.com/app/id{zodira_id}">'
                "Download Zodira</a></p>"
                "<p>Generic zodiac tool remains useful.</p>"
                "<ul><li>Zodira comparison</li><li>Other resource</li></ul>"
                "<aside><h2>Why download Zodira?</h2></aside>",
                encoding="utf-8",
            )
            (pages / "apps.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "Zodira",
                            "appStoreUrl": f"/id{zodira_id}",
                            "guideUrl": "/en-US/zodira.html",
                        },
                        {
                            "name": "Snapport",
                            "appStoreUrl": "/id6780575828",
                            "guideUrl": "/en-US/snapport.html",
                            "resources": [
                                f"{cleanup_localized_assets.SITE}/alternatives/"
                                "snapport-private-alternative.html"
                            ],
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (pages / "find-app.html").write_text(
                '<script type="application/ld+json">'
                + json.dumps(
                    {
                        "@type": "ItemList",
                        "itemListElement": [
                            {
                                "@type": "ListItem",
                                "position": 1,
                                "name": "Zodira",
                                "url": "/en-US/zodira.html",
                            },
                            {
                                "@type": "ListItem",
                                "position": 2,
                                "name": "Snapport",
                                "url": "/en-US/snapport.html",
                            },
                        ],
                    }
                )
                + "</script>"
                '<a href="#zodira">Zodira</a>'
                '<article id="zodira">Zodira app</article>'
                "<p><strong>Astrology:</strong> Zodira. "
                "<strong>Photos:</strong> Snapport.</p>",
                encoding="utf-8",
            )
            (pages / "sitemap_guides.xml").write_text(
                "<?xml version=\"1.0\"?><urlset>"
                f"<url><loc>{cleanup_localized_assets.SITE}/guides/tripplanet.html"
                "</loc></url>"
                f"<url><loc>{cleanup_localized_assets.SITE}/tools/"
                "zodiac-compatibility-checker.html</loc></url>"
                "</urlset>",
                encoding="utf-8",
            )

            live = set(cleanup_localized_assets.APPSTORE) - {
                "zodira",
                "tripplanet",
            }
            cleanup_localized_assets.cleanup(pages, live)

            self.assertTrue(all(not path.exists() for path in inactive_paths))
            self.assertNotIn(
                "Trip Planet",
                (locale / "index.html").read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "tripplanet",
                (pages / "sitemap_guides.xml").read_text(encoding="utf-8"),
            )
            tool_text = tool.read_text(encoding="utf-8")
            self.assertIn("Generic zodiac tool remains useful.", tool_text)
            self.assertNotIn("Zodira", tool_text)
            self.assertNotIn(zodira_id, tool_text)
            apps = json.loads((pages / "apps.json").read_text(encoding="utf-8"))
            self.assertEqual(["Snapport"], [item["name"] for item in apps])
            self.assertIn(
                "snapport-no-subscription",
                apps[0]["resources"][0],
            )
            finder = (pages / "find-app.html").read_text(encoding="utf-8")
            self.assertNotIn("Zodira", finder)
            self.assertIn("Snapport", finder)

    def test_sitemap_only_declares_existing_app_locales(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            build_pages_i18n, "PAGES", directory
        ):
            pages = Path(directory)
            for locale in ("en-US", "zh-Hant"):
                (pages / locale).mkdir()
                (pages / locale / "index.html").write_text("")
            (pages / "en-US" / "snapport.html").write_text("")
            (pages / "zh-Hant" / "snapport.html").write_text("")
            (pages / "en-US" / "scanto.html").write_text("")

            count = build_pages_i18n.build_sitemap(
                ["snapport", "scanto"], ["en-US", "zh-Hant"]
            )
            sitemap = (pages / "sitemap.xml").read_text(encoding="utf-8")

            self.assertEqual(6, count)
            self.assertIn("/zh-Hant/snapport.html", sitemap)
            self.assertIn("/en-US/scanto.html", sitemap)
            self.assertNotIn("/zh-Hant/scanto.html", sitemap)

    def test_profile_aware_roundups_and_cost_assets(self):
        self.assertTrue(set(gen_roundups.TOPICS) <= set(gen_roundups.APPS))
        lifetime_unlock = gen_roundups.roundup_copy(
            "aim990", gen_roundups.TOPICS["aim990"]
        )
        self.assertIn("free-to-start", lifetime_unlock["title"])
        self.assertIn("one-time unlock", lifetime_unlock["access"])
        self.assertNotIn("optional subscription", lifetime_unlock["access"])

        free_to_start = gen_roundups.roundup_copy(
            "mochi", gen_roundups.TOPICS["mochi"]
        )
        self.assertIn("free-to-start", free_to_start["title"])
        self.assertIn("one-time unlock", free_to_start["access"])

        verified_pay_once = gen_roundups.roundup_copy(
            "snapport", gen_roundups.TOPICS["snapport"]
        )
        self.assertIn("pay-once", verified_pay_once["title"])
        self.assertIn("One-time", verified_pay_once["access"])

        self.assertEqual("pay_once", aeo_pages.pricing_profile("snapport"))
        cards = gen_calculator.app_cards(
            {"snapport", "cyca", "picclear", "sononote", "gmoney"}
        )
        self.assertIn("G+Money", cards)
        self.assertIn("Snapport", cards)
        self.assertIn("Cyca", cards)
        self.assertIn("PicClear", cards)
        self.assertIn("Sono Note", cards)

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_cost_compare, "PAGES", Path(directory)
        ):
            (Path(directory) / "answers").mkdir()
            cyca_slug = gen_cost_compare.build("cyca")
            cyca = (
                Path(directory) / "answers" / f"{cyca_slug}.html"
            ).read_text(encoding="utf-8")
            self.assertIn("free to download", cyca.lower())
            self.assertIn("one-time lifetime unlock", cyca.lower())
            self.assertNotIn("paid download", cyca.lower())

            snapport_slug = gen_cost_compare.build("snapport")
            snapport = (
                Path(directory) / "answers" / f"{snapport_slug}.html"
            ).read_text(encoding="utf-8")
            self.assertIn("paid download", snapport.lower())
            self.assertNotIn("free to download", snapport.lower())

    def test_calculator_is_added_to_tools_index_and_sitemap(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_calculator, "PAGES", Path(directory)
        ):
            tools = Path(directory) / "tools"
            tools.mkdir()
            (tools / "index.html").write_text(
                "<main><section></section></main>", encoding="utf-8"
            )
            gen_calculator.build(set())
            self.assertTrue(gen_calculator.update_tools_index())
            self.assertFalse(gen_calculator.update_tools_index())
            count = gen_calculator.write_tools_sitemap()
            index = (tools / "index.html").read_text(encoding="utf-8")
            sitemap = (
                Path(directory) / "sitemap_tools.xml"
            ).read_text(encoding="utf-8")
            self.assertIn("subscription-cost-calculator.html", index)
            self.assertIn("subscription-cost-calculator.html", sitemap)
            self.assertEqual(2, count)

    def test_redirect_pages_stay_out_of_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            redirect = pages / "answers" / "old.html"
            redirect.parent.mkdir()
            redirect.write_text(
                gen_roundups.redirect_page(
                    "https://example.com/answers/current.html"
                ),
                encoding="utf-8",
            )
            self.assertTrue(aeo_answers.is_redirect_page(redirect))
            cleaned = cleanup_localized_assets.repair_html_hreflang(
                redirect,
                redirect.read_text(encoding="utf-8"),
                pages,
                set(),
            )
            self.assertNotIn('rel="alternate"', cleaned)

    def test_cleanup_builds_reciprocal_hreflang_for_story_and_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            for relative in (
                "stories/app.html",
                "zh-Hant/stories/app.html",
                "index.html",
                "zh-Hant/index.html",
            ):
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    '<link rel="canonical" href="'
                    f'{cleanup_localized_assets.SITE}/{relative}">',
                    encoding="utf-8",
                )

            story = pages / "stories" / "app.html"
            repaired_story = cleanup_localized_assets.repair_html_hreflang(
                story,
                story.read_text(encoding="utf-8"),
                pages,
                {"zh-Hant"},
            )
            self.assertIn('hreflang="zh-Hant"', repaired_story)

            localized_index = pages / "zh-Hant" / "index.html"
            repaired_index = cleanup_localized_assets.repair_html_hreflang(
                localized_index,
                localized_index.read_text(encoding="utf-8"),
                pages,
                {"zh-Hant"},
            )
            self.assertIn(
                f'href="{cleanup_localized_assets.SITE}/index.html"',
                repaired_index,
            )

    def test_cleanup_removes_false_free_offer_for_paid_upfront_app(self):
        schema = (
            '<script type="application/ld+json">'
            '{"@type":"SoftwareApplication","name":"Snapport",'
            '"offers":{"@type":"Offer","price":"0"}}'
            "</script>"
        )
        cleaned = cleanup_localized_assets.scrub_inaccurate_paid_app_offers(
            schema
        )
        self.assertNotIn('"offers"', cleaned)

    def test_generators_import_with_clean_home(self):
        env = os.environ.copy()
        env["HOME"] = "/tmp/copilot-empty-home"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import gen_roundups, gen_cost_compare, gen_calculator",
            ],
            cwd=GEO,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_daily_workflow_refreshes_app_availability_only_once(self):
        workflow = (
            Path(GEO) / "pages" / ".github" / "workflows" / "geo-daily.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(1, workflow.count("refresh=True"))
        self.assertIn("aeo_answers.py --cached-live", workflow)
        self.assertIn("aeo_pages.py --cached-live", workflow)
        self.assertIn("gen_llms.py --cached-live", workflow)
        self.assertIn("zhuyin_picture_book_club_kit.py", workflow)
        self.assertIn("zhuyin_parent_teacher_handoff_kit.py", workflow)
        self.assertIn("zhuyin_library_storytime_kit.py", workflow)
        self.assertIn("zhuyin_grade1_summer_calendar.py", workflow)
        self.assertIn("zhuyin_grade1_guide.py", workflow)
        self.assertIn("zhuyin_anki_deck.py", workflow)
        self.assertIn("zhuyin_skos_vocabulary.py", workflow)
        self.assertIn("zhuyin_croissant_dataset.py", workflow)
        self.assertIn("zhuyin_frictionless_package.py", workflow)
        self.assertIn("zhuyin_static_api.py", workflow)
        self.assertIn("family_travel_mission_cards.py", workflow)
        self.assertIn("family_travel_observation_passport.py", workflow)
        self.assertIn("family_travel_opds_catalog.py", workflow)
        self.assertIn("family_travel_ro_crate.py", workflow)
        self.assertIn("prioritize_trip_planet_resources.py", workflow)
        refresh_block = workflow.split(
            "- name: Refresh AI indexes + hubs + Atom feed", 1
        )[1].split("- name: Commit English content first", 1)[0]
        workflow_chain = (
            "gen_data_hub.py",
            "family_travel_static_api.py",
            "family_travel_observation_passport.py",
            "family_travel_opds_catalog.py",
            "family_travel_ro_crate.py",
            "family_travel_mission_cards.py",
            "zhuyin_heritage_lesson_plan.py",
            "zhuyin_readiness_tool.py",
            "zhuyin_grandparent_call_kit.py",
            "zhuyin_picture_book_club_kit.py",
            "zhuyin_parent_teacher_handoff_kit.py",
            "zhuyin_library_storytime_kit.py",
            "zhuyin_grade1_summer_calendar.py",
            "zhuyin_grade1_guide.py",
            "zhuyin_anki_deck.py",
            "zhuyin_skos_vocabulary.py",
            "zhuyin_croissant_dataset.py",
            "zhuyin_frictionless_package.py",
            "zhuyin_static_api.py",
            "prioritize_trip_planet_resources.py",
            "add_related_tools.py",
            "gen_hubs.py",
            "gen_app_catalog.py",
            "cleanup_localized_assets.py --cached-live",
            "gen_llms.py --cached-live",
            "gen_feed.py",
        )
        workflow_positions = [refresh_block.index(item) for item in workflow_chain]
        self.assertEqual(sorted(workflow_positions), workflow_positions)
        self.assertIn("--refresh-slug \"$SUMMER_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$OBSERVATION_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$TRIP_SLUG\"", workflow)
        self.assertIn('"tripplanet" in live_app_keys', workflow)
        self.assertIn("--trans i18n_trans --force", workflow)
        self.assertGreaterEqual(
            workflow.count("cleanup_localized_assets.py --cached-live"), 3
        )
        publish = (Path(GEO) / "publish.py").read_text(encoding="utf-8")
        self.assertNotIn("reset --hard", publish)
        self.assertIn("zhuyin_picture_book_club_kit.py", publish)
        self.assertIn("zhuyin_parent_teacher_handoff_kit.py", publish)
        self.assertIn("zhuyin_library_storytime_kit.py", publish)
        self.assertIn("zhuyin_grade1_summer_calendar.py", publish)
        self.assertIn("zhuyin_grade1_guide.py", publish)
        self.assertIn("zhuyin_anki_deck.py", publish)
        self.assertIn("zhuyin_skos_vocabulary.py", publish)
        self.assertIn("zhuyin_croissant_dataset.py", publish)
        self.assertIn("zhuyin_frictionless_package.py", publish)
        self.assertIn("zhuyin_static_api.py", publish)
        self.assertIn("family_travel_mission_cards.py", publish)
        self.assertIn("family_travel_observation_passport.py", publish)
        self.assertIn("family_travel_opds_catalog.py", publish)
        self.assertIn("family_travel_ro_crate.py", publish)
        self.assertIn("gen_data_hub.py", publish)
        self.assertIn("family_travel_static_api.py", publish)
        self.assertIn("prioritize_trip_planet_resources.py", publish)
        self.assertIn('gen_llms.py"), "--cached-live"', publish)
        publish_chain = (
            "build_pages_i18n.py",
            "gen_data_hub.py",
            "family_travel_static_api.py",
            "family_travel_observation_passport.py",
            "family_travel_opds_catalog.py",
            "family_travel_ro_crate.py",
            "family_travel_mission_cards.py",
            "zhuyin_heritage_lesson_plan.py",
            "zhuyin_readiness_tool.py",
            "zhuyin_grandparent_call_kit.py",
            "zhuyin_picture_book_club_kit.py",
            "zhuyin_parent_teacher_handoff_kit.py",
            "zhuyin_library_storytime_kit.py",
            "zhuyin_grade1_summer_calendar.py",
            "zhuyin_grade1_guide.py",
            "zhuyin_anki_deck.py",
            "zhuyin_skos_vocabulary.py",
            "zhuyin_croissant_dataset.py",
            "zhuyin_frictionless_package.py",
            "zhuyin_static_api.py",
            "prioritize_trip_planet_resources.py",
            "add_related_answers.py",
            "add_related_tools.py",
            "fix_en_hreflang.py",
            "gen_llms.py",
        )
        publish_positions = [publish.index(item) for item in publish_chain]
        self.assertEqual(sorted(publish_positions), publish_positions)
        self.assertIn("--refresh-slug", publish)
        self.assertIn("aeo_answers_i18n.py", publish)
        self.assertIn("add_related_answers.py", publish)
        self.assertIn("fix_en_hreflang.py", publish)

    def test_indexnow_retries_and_surfaces_total_failure(self):
        with mock.patch.object(
            indexnow_submit.urllib.request,
            "urlopen",
            side_effect=OSError("offline"),
        ) as urlopen, mock.patch.object(indexnow_submit.time, "sleep"):
            self.assertFalse(
                indexnow_submit.submit(
                    ["https://example.com/page"], "public-key"
                )
            )
        self.assertEqual(
            len(indexnow_submit.ENDPOINTS) * 3,
            urlopen.call_count,
        )

    def test_answer_schema_and_aim990_truth_use_verified_model(self):
        content = aeo_answers.default_content(
            "best TOEIC study app with no subscription", "aim990"
        )
        page = aeo_answers.render_page(
            "best TOEIC study app with no subscription",
            "aim990",
            content,
        )
        self.assertNotIn('"offers"', page)
        self.assertIn("No subscription", page)
        self.assertNotIn("subscription options", page)
        aeo_answers.normalized_content(content, "TOEIC study app", "aim990")
        unsafe = dict(content)
        unsafe["lead"] = "Aim990 offers optional subscriptions."
        with self.assertRaisesRegex(ValueError, "optional-subscription"):
            aeo_answers.normalized_content(
                unsafe, "TOEIC study app", "aim990"
            )

    def test_answer_generation_can_reuse_verified_availability_snapshot(self):
        with mock.patch.object(
            aeo_answers, "live_app_keys", return_value={"snapport"}
        ) as lookup:
            plan = aeo_answers.question_plan(
                ["snapport"], refresh_live=False
            )
        self.assertTrue(plan)
        lookup.assert_called_once_with(
            aeo_answers.APPSTORE,
            aeo_answers.ROOT / "pages",
            refresh=False,
        )

    def test_llms_omits_unavailable_apps_and_uses_verified_aim990_claim(self):
        text = gen_llms.build_llms({}, {"aim990", "lumibopomofo"})
        self.assertNotIn("Zafe", text)
        aim_line = gen_llms.app_line("aim990", ["Competitor"], {"aim990"})
        self.assertIn("pay-once alternative", aim_line.lower())
        self.assertNotIn("optional subscription", aim_line.lower())
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
        self.assertEqual("aim990-free-to-start", slug)
        self.assertEqual(slug, aeo_pages.alternative_hub_slug("aim990"))
        self.assertIn("one-time lifetime unlock", page)
        self.assertIn("free to download", page)
        self.assertIn("no recurring subscription", page)
        self.assertNotIn("optional subscription plans", page)
        _slug, comparison = aeo_pages.alt_page("aim990", "magoosh", [])
        self.assertIn("no subscription", comparison.lower())
        expected_profiles = {
            "mochi": ("free_to_start", "mochi-free-to-start"),
            "lumibopomofo": ("free_to_start", "lumibopomofo-free-to-start"),
            "snapport": ("pay_once", "snapport-no-subscription"),
            "picclear": ("free_to_start", "picclear-free-to-start"),
            "cyca": ("free_to_start", "cyca-free-to-start"),
            "sononote": ("free_to_start", "sononote-free-to-start"),
            "cvdesk": ("free_to_start", "cvdesk-free-to-start"),
            "scanto": ("free_to_start", "scanto-free-to-start"),
            "lockhour": ("free_to_start", "lockhour-free-to-start"),
            "unblurry": ("free_to_start", "unblurry-free-to-start"),
            "photocream": ("free_to_start", "photocream-free-to-start"),
            "lumiletters": ("free_to_start", "lumiletters-free-to-start"),
            "lumimath": ("free_to_start", "lumimath-free-to-start"),
            "lumimission": ("free_to_start", "lumimission-free-to-start"),
            "lumiweather": ("free_to_start", "lumiweather-free-to-start"),
            "zodira": ("free_to_start", "zodira-free-to-start"),
            "aim990": ("free_to_start", "aim990-free-to-start"),
            "zafe": ("free_to_start", "zafe-free-to-start"),
            "tripplanet": ("free_to_start", "tripplanet-free-to-start"),
            "sereno": ("free_to_start", "sereno-free-to-start"),
            "gmoney": ("pay_once", "gmoney-no-subscription"),
            "hourstag": ("pay_once", "hourstag-no-subscription"),
            "lumiletterspro": ("pay_once", "lumiletterspro-no-subscription"),
            "lumimathpro": ("pay_once", "lumimathpro-no-subscription"),
            "lumimissionpro": ("pay_once", "lumimissionpro-no-subscription"),
            "lumibopomofopro": (
                "pay_once",
                "lumibopomofopro-no-subscription",
            ),
            "tripbee": ("pay_once", "tripbee-no-subscription"),
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
                if profile == "pay_once":
                    self.assertIn("pay once", actual_page.lower())
                elif profile == "free_to_start":
                    self.assertIn("free to download", actual_page.lower())
                    self.assertIn(
                        "one-time lifetime unlock", actual_page.lower()
                    )
                else:
                    self.assertNotIn("pay once", actual_page.lower())

    def test_alternatives_prune_stale_or_unlisted_app_pages(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            aeo_pages, "ALT", directory
        ):
            keep = {
                "aim990-free-to-start.html",
                "snapport-no-subscription.html",
            }
            stale = {
                "aim990-flexible-unlock.html",
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

    def test_legacy_lifetime_unlock_slugs_map_to_current_pages(self):
        for old, current in {
            "aim990-no-subscription": "aim990-free-to-start",
            "cvdesk-no-subscription": "cvdesk-free-to-start",
            "scanto-no-subscription": "scanto-free-to-start",
            "lockhour-no-subscription": "lockhour-free-to-start",
            "unblurry-no-subscription": "unblurry-free-to-start",
            "photocream-no-subscription": "photocream-free-to-start",
            "lumiletters-no-subscription": "lumiletters-free-to-start",
            "lumimath-no-subscription": "lumimath-free-to-start",
            "lumimission-no-subscription": "lumimission-free-to-start",
            "lumiweather-no-subscription": "lumiweather-free-to-start",
            "sereno-no-subscription": "sereno-free-to-start",
            "picclear-private-alternative": "picclear-free-to-start",
            "cyca-private-alternative": "cyca-free-to-start",
            "sononote-no-subscription": "sononote-free-to-start",
        }.items():
            self.assertEqual(
                current,
                cleanup_localized_assets.LEGACY_ALT_SLUGS[old],
            )

    def test_guide_localizer_reconciles_hreflang_before_publish(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            aeo_guide_i18n, "PAGES", directory
        ):
            pages = Path(directory)
            english = pages / "guides" / "snapport.html"
            localized = pages / "zh-Hant" / "guides" / "snapport.html"
            english.parent.mkdir(parents=True)
            localized.parent.mkdir(parents=True)
            english.write_text(
                '<link rel="canonical" href="'
                f'{aeo_guide_i18n.SITE}/guides/snapport.html">',
                encoding="utf-8",
            )
            localized.write_text(
                '<link rel="canonical" href="'
                f'{aeo_guide_i18n.SITE}/zh-Hant/guides/snapport.html">',
                encoding="utf-8",
            )

            self.assertEqual(
                2, aeo_guide_i18n.reconcile_hreflang(["snapport"])
            )
            for page in (english, localized):
                text = page.read_text(encoding="utf-8")
                self.assertIn('hreflang="en"', text)
                self.assertIn('hreflang="zh-Hant"', text)

    def test_alternative_pruning_never_manages_public_apps_missing_sov(self):
        public = {"snapport", "mochi"}
        keys, managed = aeo_pages.generation_scope(
            [],
            {"snapport": {"key": "snapport"}},
            public,
        )
        self.assertEqual(["snapport"], keys)
        self.assertIn("snapport", managed)
        self.assertNotIn("mochi", managed)

        keys, managed = aeo_pages.generation_scope(
            ["mochi"],
            {"snapport": {"key": "snapport"}},
            public,
        )
        self.assertEqual([], keys)
        self.assertEqual(set(), managed)

        keys, managed = aeo_pages.generation_scope(
            ["zafe"],
            {"snapport": {"key": "snapport"}},
            public,
        )
        self.assertEqual([], keys)
        self.assertEqual({"zafe"}, managed)

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
