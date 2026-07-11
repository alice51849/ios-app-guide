#!/usr/bin/env python3
"""Regression tests for App Store availability and AI outreach generation."""
from __future__ import annotations

import csv
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
import zhuyin_grandparent_call_kit
import zhuyin_grade1_guide
import zhuyin_grade1_summer_calendar
import zhuyin_heritage_lesson_plan
import zhuyin_library_storytime_kit
import zhuyin_parent_teacher_handoff_kit
import zhuyin_picture_book_club_kit
import zhuyin_readiness_tool


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
            items = gen_feed.collect()
        self.assertTrue(
            any(url.endswith("/tools/private-travel-tool.html") for _, url, _ in items)
        )
        self.assertTrue(
            any(url.endswith("/data/family-travel-missions.html") for _, url, _ in items)
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
            (root_alt / "cvdesk-no-subscription.html").write_text("")
            (root_alt / "index.html").write_text("")
            (localized_alt / "snapport-private-alternative.html").write_text(
                "stale pricing", encoding="utf-8"
            )
            (localized_alt / "cvdesk-no-subscription.html").write_text(
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
                '<li><a href="cvdesk-no-subscription.html">CV Desk</a></li></ul>',
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
            self.assertTrue((localized_alt / "cvdesk-no-subscription.html").exists())
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
        self.assertIn("family_travel_mission_cards.py", workflow)
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
        self.assertIn("family_travel_mission_cards.py", publish)
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
