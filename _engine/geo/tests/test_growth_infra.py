#!/usr/bin/env python3
"""Regression tests for App Store availability and AI outreach generation."""
from __future__ import annotations

import copy
import csv
import datetime as dt
import email.utils
import hashlib
import io
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image

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
import gen_guide_design
import gen_hubs
import gen_image_sitemap
import gen_linkset
import gen_llms
import gen_mobile_store_ctas
import gen_roundups
import gen_social_previews
import gen_smart_app_banners
import indexnow_submit
import notify_rsscloud
import notify_websub
import outreach_scorecard
import prioritize_trip_planet_resources
import rsscloud_config
import static_api_catalog
import zhuyin_grandparent_call_kit
import zhuyin_grade1_guide
import zhuyin_grade1_summer_calendar
import zhuyin_anki_deck
import zhuyin_croissant_dataset
import zhuyin_csvw_metadata
import zhuyin_bagit_package
import zhuyin_ocfl_object
import zhuyin_dcat_catalog
import zhuyin_epub_opds
import zhuyin_frictionless_package
import zhuyin_iiif_presentation
import zhuyin_heritage_lesson_plan
import zhuyin_library_storytime_kit
import zhuyin_library_catalog
import zhuyin_ldes_event_stream
import zhuyin_lms_assessment_bank
import zhuyin_mets_premis_package
import zhuyin_oer_metadata
import zhuyin_ore_resource_map
import zhuyin_parent_teacher_handoff_kit
import zhuyin_picture_book_club_kit
import zhuyin_readiness_tool
import zhuyin_resourcesync
import zhuyin_ro_crate
import zhuyin_skos_vocabulary
import zhuyin_static_api
import websub_config
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

    def test_image_sitemap_maps_every_canonical_story_to_its_owned_poster(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            images = pages / "stories" / "img"
            images.mkdir(parents=True)
            for key in ("alpha", "beta"):
                (images / f"{key}-poster.jpg").write_bytes(f"{key}-image".encode())
                (pages / "stories" / f"{key}.html").write_text(
                    '<link rel="canonical" href="'
                    f'{gen_image_sitemap.SITE}/stories/{key}.html">'
                    '<amp-story poster-portrait-src="'
                    f'{gen_image_sitemap.SITE}/stories/img/{key}-poster.jpg">',
                    encoding="utf-8",
                )
            (pages / "stories" / "index.html").write_text(
                "<html></html>", encoding="utf-8"
            )

            count, changed = gen_image_sitemap.generate(pages)
            output = pages / "sitemap_images.xml"
            first_mtime = output.stat().st_mtime_ns
            second_count, second_changed = gen_image_sitemap.generate(pages)

            self.assertEqual((2, True), (count, changed))
            self.assertEqual((2, False), (second_count, second_changed))
            self.assertEqual(first_mtime, output.stat().st_mtime_ns)
            root = ET.parse(output).getroot()
            sitemap = f"{{{gen_image_sitemap.SITEMAP_NS}}}"
            image = f"{{{gen_image_sitemap.IMAGE_NS}}}"
            urls = root.findall(f"{sitemap}url")
            self.assertEqual(
                [
                    f"{gen_image_sitemap.SITE}/stories/alpha.html",
                    f"{gen_image_sitemap.SITE}/stories/beta.html",
                ],
                [item.findtext(f"{sitemap}loc") for item in urls],
            )
            self.assertEqual(
                [
                    f"{gen_image_sitemap.SITE}/stories/img/alpha-poster.jpg",
                    f"{gen_image_sitemap.SITE}/stories/img/beta-poster.jpg",
                ],
                [
                    item.find(f"{image}image").findtext(f"{image}loc")
                    for item in urls
                ],
            )
            text = output.read_text(encoding="utf-8")
            for deprecated in ("image:caption", "image:title", "image:license"):
                self.assertNotIn(deprecated, text)
            self.assertIn("sitemap_images.xml", gen_llms.build_robots())
            with mock.patch.object(gen_llms, "PAGES", str(pages)):
                self.assertIn("sitemap_images.xml", gen_llms.build_sitemap_index())

    def test_image_sitemap_rejects_missing_or_unowned_posters(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            stories = pages / "stories"
            stories.mkdir()
            story = stories / "alpha.html"
            story.write_text(
                '<link rel="canonical" href="'
                f'{gen_image_sitemap.SITE}/stories/alpha.html">'
                '<amp-story poster-portrait-src="https://example.com/poster.jpg">',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not a stable owned URL"):
                gen_image_sitemap.generate(pages)

            story.write_text(
                '<link rel="canonical" href="'
                f'{gen_image_sitemap.SITE}/stories/alpha.html">'
                '<amp-story poster-portrait-src="'
                f'{gen_image_sitemap.SITE}/stories/img/missing.jpg">',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileNotFoundError, "missing or empty"):
                gen_image_sitemap.generate(pages)

    def test_rfc9264_linkset_covers_app_relations_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            guide = pages / "guides" / "lumibopomofo.html"
            localized = pages / "zh-Hant" / "guides" / "lumibopomofo.html"
            story = pages / "stories" / "lumibopomofo.html"
            poster = pages / "stories" / "img" / "lumibopomofo-poster.jpg"
            hub = pages / "hubs" / "lumibopomofo.html"
            for path in (guide, localized, story, poster, hub):
                path.parent.mkdir(parents=True, exist_ok=True)
            site = gen_linkset.SITE
            guide.write_text(
                "<head>"
                f'<link rel="canonical" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="en" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="x-default" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="zh-Hant" href="{site}/zh-Hant/guides/lumibopomofo.html">'
                f'<link rel="linkset" href="{site}/old-linkset.json">'
                "<!-- social-preview:start --><meta property=\"og:title\" content=\"old\">"
                "<!-- social-preview:end -->"
                f'<link rel="alternate" type="application/atom+xml" href="{site}/feed.xml">'
                "</head>",
                encoding="utf-8",
            )
            localized.write_text("<head></head>", encoding="utf-8")
            story.write_text(
                "<head>"
                f'<link rel="canonical" href="{site}/stories/lumibopomofo.html">'
                "</head><body>"
                f'<amp-story poster-portrait-src="{site}/stories/img/lumibopomofo-poster.jpg">',
                encoding="utf-8",
            )
            poster.write_bytes(b"poster")
            hub.write_text("<head></head>", encoding="utf-8")
            (pages / "index.html").write_text(
                f'<head><link rel="canonical" href="{site}/index.html"></head>',
                encoding="utf-8",
            )
            for relative in (
                "feed.xml",
                "rss.xml",
                "feed.json",
                "llms-full.txt",
                "apps/index.html",
            ):
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("resource", encoding="utf-8")

            first = gen_linkset.generate(pages, {"lumibopomofo"})
            tracked = [
                pages / "linkset.json",
                pages / "sitemap_linkset.xml",
                pages / "index.html",
                guide,
            ]
            mtimes = {path: path.stat().st_mtime_ns for path in tracked}
            second = gen_linkset.generate(pages, {"lumibopomofo"})

            self.assertEqual(
                {
                    "apps": 1,
                    "contexts": 2,
                    "discovery_pages": 2,
                    "changed_files": 4,
                },
                first,
            )
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(mtimes, {path: path.stat().st_mtime_ns for path in tracked})
            document = json.loads(
                (pages / "linkset.json").read_text(encoding="utf-8")
            )
            self.assertEqual(["linkset"], list(document))
            root, app = document["linkset"]
            self.assertEqual(f"{site}/index.html", root["anchor"])
            self.assertEqual(
                f"{site}/guides/lumibopomofo.html", root["item"][0]["href"]
            )
            self.assertEqual(
                [{"value": "Lumi Bopomofo", "language": "en"}],
                root["item"][0]["title*"],
            )
            self.assertEqual(
                f"{site}/guides/lumibopomofo.html", app["anchor"]
            )
            self.assertEqual(
                [
                    f"{site}/guides/lumibopomofo.html",
                    f"{site}/zh-Hant/guides/lumibopomofo.html",
                ],
                [target["href"] for target in app["alternate"]],
            )
            self.assertEqual(
                ["en", "x-default"], app["alternate"][0]["hreflang"]
            )
            related = [target["href"] for target in app["related"]]
            self.assertEqual(
                "https://apps.apple.com/app/id6773017109?ct=iag_linkset",
                related[0],
            )
            self.assertEqual(
                [
                    {
                        "value": "Lumi Bopomofo on the App Store",
                        "language": "en",
                    }
                ],
                app["related"][0]["title*"],
            )
            self.assertEqual(f"{site}/stories/lumibopomofo.html", related[1])
            self.assertEqual(
                f"{site}/stories/img/lumibopomofo-poster.jpg",
                app["preview"][0]["href"],
            )
            for context in document["linkset"]:
                self.assertTrue(context["anchor"].startswith("https://"))
                for relation, targets in context.items():
                    if relation == "anchor":
                        continue
                    for target in targets:
                        self.assertTrue(target["href"].startswith("https://"))

            discovery = gen_linkset.discovery_link()
            self.assertEqual(1, guide.read_text(encoding="utf-8").count(discovery))
            self.assertLess(
                guide.read_text(encoding="utf-8").index(discovery),
                guide.read_text(encoding="utf-8").index(
                    "<!-- social-preview:start -->"
                ),
            )
            self.assertLess(
                guide.read_text(encoding="utf-8").index(
                    "<!-- social-preview:end -->"
                ),
                guide.read_text(encoding="utf-8").index("application/atom+xml"),
            )
            self.assertEqual(
                1,
                (pages / "index.html").read_text(encoding="utf-8").count(discovery),
            )
            self.assertNotIn(
                "rel=\"linkset\"", localized.read_text(encoding="utf-8")
            )
            sitemap = ET.parse(pages / "sitemap_linkset.xml").getroot()
            self.assertEqual(
                f"{site}/linkset.json",
                sitemap.findtext(f"{{{gen_linkset.SITEMAP_NS}}}url/"
                                 f"{{{gen_linkset.SITEMAP_NS}}}loc"),
            )
            self.assertIn("sitemap_linkset.xml", gen_llms.build_robots())
            with mock.patch.object(gen_llms, "PAGES", str(pages)):
                self.assertIn(
                    "sitemap_linkset.xml", gen_llms.build_sitemap_index()
                )

    def test_rfc9264_linkset_rejects_story_and_public_app_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            stories = pages / "stories"
            images = stories / "img"
            images.mkdir(parents=True)
            (stories / "lumibopomofo.html").write_text(
                '<link rel="canonical" href="'
                f'{gen_linkset.SITE}/stories/lumibopomofo.html">'
                '<amp-story poster-portrait-src="'
                f'{gen_linkset.SITE}/stories/img/lumibopomofo-poster.jpg">',
                encoding="utf-8",
            )
            (images / "lumibopomofo-poster.jpg").write_bytes(b"poster")
            with self.assertRaisesRegex(ValueError, "missing=.*lumibopomofopro"):
                gen_linkset.build_document(
                    pages, {"lumibopomofo", "lumibopomofopro"}
                )

    def test_social_previews_generate_cards_oembed_and_stable_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            guide = pages / "guides" / "lumibopomofo.html"
            localized = pages / "zh-Hant" / "guides" / "lumibopomofo.html"
            story = pages / "stories" / "lumibopomofo.html"
            poster = pages / "stories" / "img" / "lumibopomofo-poster.jpg"
            hub = pages / "hubs" / "lumibopomofo.html"
            for path in (guide, localized, story, poster, hub):
                path.parent.mkdir(parents=True, exist_ok=True)
            site = gen_social_previews.SITE
            guide.write_text(
                "<head><title>Lumi Bopomofo — Zhuyin for Kids</title>"
                '<meta name="description" content="A private, playful Zhuyin guide.">'
                f'<link rel="canonical" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="en" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="zh-Hant" href="{site}/zh-Hant/guides/lumibopomofo.html">'
                f'<link rel="linkset" type="application/linkset+json" href="{site}/linkset.json">'
                f'<link rel="alternate" type="application/atom+xml" href="{site}/feed.xml">'
                "</head><body><main>"
                "<h1>Lumi Bopomofo — Zhuyin for Kids</h1>"
                "<p>Guide introduction.</p></main></body>",
                encoding="utf-8",
            )
            localized.write_text("<head></head>", encoding="utf-8")
            story.write_text(
                "<head>"
                f'<link rel="canonical" href="{site}/stories/lumibopomofo.html">'
                "</head><body>"
                f'<amp-story poster-portrait-src="{site}/stories/img/lumibopomofo-poster.jpg">',
                encoding="utf-8",
            )
            Image.new("RGB", (720, 960), (91, 95, 242)).save(poster, "JPEG")
            hub.write_text("<head></head>", encoding="utf-8")
            (pages / "index.html").write_text(
                f'<head><link rel="canonical" href="{site}/index.html"></head>',
                encoding="utf-8",
            )
            for relative in (
                "feed.xml",
                "rss.xml",
                "feed.json",
                "llms-full.txt",
                "apps/index.html",
            ):
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("resource", encoding="utf-8")
            stale_card = pages / "social" / "img" / "stale-share.jpg"
            stale_oembed = pages / "oembed" / "stale.json"
            stale_card.parent.mkdir(parents=True)
            stale_oembed.parent.mkdir(parents=True)
            stale_card.write_bytes(b"stale")
            stale_oembed.write_text("{}", encoding="utf-8")
            stale_guide = pages / "guides" / "stale.html"
            stale_guide.write_text(
                "<head><!-- social-preview:start -->old"
                "<!-- social-preview:end --></head><body><main><h1>Stale</h1>"
                "<!-- app-preview-hero:start -->old"
                "<!-- app-preview-hero:end --></main></body>",
                encoding="utf-8",
            )

            first = gen_social_previews.generate(pages, {"lumibopomofo"})
            tracked = [
                guide,
                pages / "social" / "img" / "lumibopomofo-share.jpg",
                pages / "oembed" / "lumibopomofo.json",
                pages / "sitemap_oembed.xml",
            ]
            mtimes = {path: path.stat().st_mtime_ns for path in tracked}
            second = gen_social_previews.generate(pages, {"lumibopomofo"})

            self.assertEqual(
                {
                    "apps": 1,
                    "cards": 1,
                    "oembed": 1,
                    "metadata_pages": 1,
                    "hero_pages": 1,
                    "changed_files": 7,
                },
                first,
            )
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(mtimes, {path: path.stat().st_mtime_ns for path in tracked})
            self.assertFalse(stale_card.exists())
            self.assertFalse(stale_oembed.exists())
            stale_source = stale_guide.read_text(encoding="utf-8")
            self.assertNotIn(gen_social_previews.BLOCK_START, stale_source)
            self.assertNotIn(gen_social_previews.HERO_START, stale_source)
            with Image.open(tracked[1]) as card:
                self.assertEqual("JPEG", card.format)
                self.assertEqual(gen_social_previews.CARD_SIZE, card.size)
                extrema = card.convert("L").getextrema()
                self.assertGreater(extrema[1] - extrema[0], 10)

            embed = json.loads(tracked[2].read_text(encoding="utf-8"))
            self.assertEqual("1.0", embed["version"])
            self.assertEqual("link", embed["type"])
            self.assertEqual("Lumi Bopomofo — Zhuyin for Kids", embed["title"])
            self.assertEqual(1200, embed["thumbnail_width"])
            self.assertEqual(675, embed["thumbnail_height"])
            source = guide.read_text(encoding="utf-8")
            self.assertEqual(1, source.count(gen_social_previews.BLOCK_START))
            self.assertEqual(1, source.count('property="og:title"'))
            self.assertEqual(1, source.count('name="robots"'))
            self.assertIn(
                f'name="robots" content="{gen_social_previews.ROBOTS_DIRECTIVE}"',
                source,
            )
            self.assertIn('name="twitter:card" content="summary_large_image"', source)
            self.assertIn('type="application/json+oembed"', source)
            self.assertEqual(1, source.count(gen_social_previews.HERO_START))
            self.assertEqual(1, source.count('class="iag-app-preview__image"'))
            self.assertIn(
                'href="https://apps.apple.com/app/id6773017109?ct=iag_hero"',
                source,
            )
            self.assertIn(
                'src="https://alice51849.github.io/ios-app-guide/social/img/'
                'lumibopomofo-share.jpg"',
                source,
            )
            self.assertIn(
                'alt="Lumi Bopomofo iOS app guide preview" '
                'width="1200" height="675" loading="eager" '
                'decoding="async" fetchpriority="high"',
                source,
            )
            self.assertIn("width:100%;height:auto;aspect-ratio:16/9", source)
            self.assertLess(
                source.index("</h1>"), source.index(gen_social_previews.HERO_START)
            )
            self.assertLess(
                source.index(gen_social_previews.HERO_END),
                source.index("<p>Guide introduction.</p>"),
            )
            self.assertNotIn(
                gen_social_previews.HERO_START,
                localized.read_text(encoding="utf-8"),
            )
            schemas = [
                json.loads(payload)
                for payload in re.findall(
                    r'<script type="application/ld\+json" '
                    r'data-iag="primary-image">\s*(.*?)\s*</script>',
                    source,
                    re.DOTALL,
                )
            ]
            self.assertEqual(1, len(schemas))
            schema = schemas[0]
            self.assertEqual("WebPage", schema["@type"])
            self.assertEqual(
                f"{site}/guides/lumibopomofo.html#webpage", schema["@id"]
            )
            primary = schema["primaryImageOfPage"]
            self.assertEqual("ImageObject", primary["@type"])
            self.assertEqual(
                f"{site}/social/img/lumibopomofo-share.jpg",
                primary["contentUrl"],
            )
            self.assertEqual((1200, 675), (primary["width"], primary["height"]))
            self.assertEqual("image/jpeg", primary["encodingFormat"])
            self.assertTrue(primary["representativeOfPage"])
            from rdflib import Graph

            self.assertGreater(
                len(Graph().parse(data=json.dumps(schema), format="json-ld")), 0
            )
            self.assertIn(
                "url=https%3A%2F%2Falice51849.github.io%2Fios-app-guide"
                "%2Fguides%2Flumibopomofo.html&amp;format=json",
                source,
            )
            self.assertLess(source.index('rel="linkset"'), source.index(gen_social_previews.BLOCK_START))
            self.assertLess(source.index(gen_social_previews.BLOCK_END), source.index("application/atom+xml"))
            sitemap = ET.parse(pages / "sitemap_oembed.xml").getroot()
            self.assertEqual(
                f"{site}/oembed/lumibopomofo.json",
                sitemap.findtext(
                    f"{{{gen_social_previews.SITEMAP_NS}}}url/"
                    f"{{{gen_social_previews.SITEMAP_NS}}}loc"
                ),
            )
            self.assertIn("sitemap_oembed.xml", gen_llms.build_robots())
            with mock.patch.object(gen_llms, "PAGES", str(pages)):
                self.assertIn(
                    "sitemap_oembed.xml", gen_llms.build_sitemap_index()
                )
            conflicting = pages / "guides" / "conflicting.html"
            conflicting.write_text(
                "<head><title>Conflict</title>"
                '<meta name="description" content="Conflict">'
                '<meta name="robots" content="noindex, noimageindex">'
                f'<link rel="canonical" href="{site}/guides/conflicting.html">'
                "</head>",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "conflicting robots"):
                gen_social_previews._guide_metadata(
                    conflicting, f"{site}/guides/conflicting.html"
                )
            duplicate_schema = pages / "guides" / "duplicate-schema.html"
            duplicate_schema.write_text(
                "<head><script type=\"application/ld+json\">"
                '{"@context":"https://schema.org","@type":"WebPage",'
                '"primaryImageOfPage":"https://example.com/image.jpg"}'
                "</script></head><body><h1>Duplicate</h1></body>",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "already declares"):
                gen_social_previews.ensure_guide(
                    duplicate_schema,
                    gen_social_previews.metadata_block(
                        "duplicate-schema",
                        "Duplicate",
                        "Duplicate",
                        f"{site}/guides/duplicate-schema.html",
                        "Duplicate",
                    ),
                    gen_social_previews.hero_block(
                        "duplicate-schema",
                        "Duplicate",
                        "https://apps.apple.com/app/id123456789?ct=iag_linkset",
                    ),
                )

    def test_smart_app_banners_cover_guides_and_buyer_intent_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pages = workspace / "site"
            pages.mkdir()
            linked_pages = workspace / "linked-site"
            linked_pages.symlink_to(pages, target_is_directory=True)
            guide = pages / "guides" / "lumibopomofo.html"
            localized = pages / "zh-Hant" / "guides" / "lumibopomofo.html"
            story = pages / "stories" / "lumibopomofo.html"
            poster = pages / "stories" / "img" / "lumibopomofo-poster.jpg"
            hub = pages / "hubs" / "lumibopomofo.html"
            stale = pages / "fr-FR" / "guides" / "stale.html"
            answer = pages / "answers" / "best-bopomofo-app.html"
            localized_answer = (
                pages / "zh-Hant" / "answers" / "best-bopomofo-app.html"
            )
            stale_answer = pages / "fr-FR" / "answers" / "stale.html"
            ambiguous_answer = pages / "answers" / "compare-apps.html"
            for path in (
                guide,
                localized,
                story,
                poster,
                hub,
                stale,
                answer,
                localized_answer,
                stale_answer,
                ambiguous_answer,
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
            site = gen_smart_app_banners.SITE
            guide.write_text(
                "<head>"
                f'<link rel="canonical" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="en" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="zh-Hant" href="{site}/zh-Hant/guides/lumibopomofo.html">'
                f'<link rel="linkset" type="application/linkset+json" href="{site}/linkset.json">'
                "<!-- social-preview:start --><meta property=\"og:title\" content=\"Lumi\">"
                "<!-- social-preview:end -->"
                f'<link rel="alternate" type="application/atom+xml" href="{site}/feed.xml">'
                "</head>",
                encoding="utf-8",
            )
            localized.write_text("<head></head>", encoding="utf-8")
            story.write_text(
                "<head>"
                f'<link rel="canonical" href="{site}/stories/lumibopomofo.html">'
                "</head><body>"
                f'<amp-story poster-portrait-src="{site}/stories/img/lumibopomofo-poster.jpg">',
                encoding="utf-8",
            )
            poster.write_bytes(b"poster")
            hub.write_text("<head></head>", encoding="utf-8")
            stale.write_text(
                "<head>"
                f"{gen_smart_app_banners.BLOCK_START}"
                '<meta name="apple-itunes-app" content="app-id=1">'
                f"{gen_smart_app_banners.BLOCK_END}"
                "</head>",
                encoding="utf-8",
            )
            answer.write_text(
                "<head></head><body>"
                '<a href="https://apps.apple.com/app/id6773017109?ct=iag_ans">'
                "Get the app</a></body>",
                encoding="utf-8",
            )
            localized_answer.write_text(
                "<head></head><body>"
                '<a href="https://apps.apple.com/app/id6773017109?ct=iag_ans">'
                "Get the app</a></body>",
                encoding="utf-8",
            )
            stale_answer.write_text(
                "<head>"
                f"{gen_smart_app_banners.BLOCK_START}"
                '<meta name="apple-itunes-app" content="app-id=1">'
                f"{gen_smart_app_banners.BLOCK_END}"
                "</head><body>No live app link</body>",
                encoding="utf-8",
            )
            ambiguous_answer.write_text(
                "<head></head><body>"
                "https://apps.apple.com/app/id6773017109 "
                "https://apps.apple.com/app/id1234567890"
                "</body>",
                encoding="utf-8",
            )
            (pages / "index.html").write_text(
                f'<head><link rel="canonical" href="{site}/index.html"></head>',
                encoding="utf-8",
            )
            for relative in (
                "feed.xml",
                "rss.xml",
                "feed.json",
                "llms-full.txt",
                "apps/index.html",
            ):
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("resource", encoding="utf-8")

            first = gen_smart_app_banners.generate(
                linked_pages, {"lumibopomofo"}
            )
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (
                    guide,
                    localized,
                    stale,
                    answer,
                    localized_answer,
                    stale_answer,
                    ambiguous_answer,
                )
            }
            second = gen_smart_app_banners.generate(
                linked_pages, {"lumibopomofo"}
            )

            self.assertEqual(
                {
                    "apps": 1,
                    "guide_pages": 2,
                    "answer_pages": 2,
                    "languages": 2,
                    "changed_files": 6,
                },
                first,
            )
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(
                mtimes,
                {
                    path: path.stat().st_mtime_ns
                    for path in (
                        guide,
                        localized,
                        stale,
                        answer,
                        localized_answer,
                        stale_answer,
                        ambiguous_answer,
                    )
                },
            )
            banner = gen_smart_app_banners.banner_block("6773017109")
            for path in (guide, localized, answer, localized_answer):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(1, source.count(banner))
                self.assertNotIn("app-argument", source)
            source = guide.read_text(encoding="utf-8")
            self.assertLess(
                source.index(gen_smart_app_banners.BLOCK_START),
                source.index('rel="linkset"'),
            )
            self.assertLess(
                source.index('rel="linkset"'),
                source.index("<!-- social-preview:start -->"),
            )
            self.assertNotIn(
                gen_smart_app_banners.BLOCK_START,
                stale.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                gen_smart_app_banners.BLOCK_START,
                stale_answer.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                gen_smart_app_banners.BLOCK_START,
                ambiguous_answer.read_text(encoding="utf-8"),
            )
            with self.assertRaisesRegex(ValueError, "app ID"):
                gen_smart_app_banners.banner_block("not-an-id")

    def test_mobile_store_ctas_reuse_localized_links_and_prune_stale_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary.html"
            ghost = root / "ghost.html"
            plain = root / "plain.html"
            stale = root / "stale.html"
            invalid = root / "invalid.html"
            primary.write_text(
                "<body><main>"
                '<a href="https://apps.apple.com/app/id6773017109?ct=plain">'
                "Plain link</a>"
                '<section class="hero"><a class="cta" '
                'href="https://apps.apple.com/app/id6773017109?ct=hero&amp;mt=8">'
                "Get the app</a></section></main></body>",
                encoding="utf-8",
            )
            ghost.write_text(
                "<body><main><section class=\"hero\">"
                "<a class='cta ghost' "
                "href='https://apps.apple.com/app/id6773017109?ct=localized'>"
                "Localized App Store label</a></section></main></body>",
                encoding="utf-8",
            )
            plain.write_text(
                "<body><main>"
                '<a href="https://apps.apple.com/app/id6773017109?ct=fallback">'
                "<span>Fallback</span> label</a></main></body>",
                encoding="utf-8",
            )
            stale.write_text(
                "<body><main>No direct link</main>"
                f"{gen_mobile_store_ctas.BLOCK_START}"
                '<a href="https://apps.apple.com/app/id6773017109?ct=stale">'
                "Stale generated link</a>"
                f"{gen_mobile_store_ctas.BLOCK_END}</body>",
                encoding="utf-8",
            )
            invalid.write_text("<main>No body</main>", encoding="utf-8")

            for path in (primary, ghost, plain):
                self.assertTrue(
                    gen_mobile_store_ctas.ensure_mobile_cta(
                        path, "6773017109"
                    )
                )
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (primary, ghost, plain)
            }
            for path in (primary, ghost, plain):
                self.assertFalse(
                    gen_mobile_store_ctas.ensure_mobile_cta(
                        path, "6773017109"
                    )
                )
            self.assertEqual(
                mtimes,
                {
                    path: path.stat().st_mtime_ns
                    for path in (primary, ghost, plain)
                },
            )

            primary_source = primary.read_text(encoding="utf-8")
            self.assertEqual(
                1, primary_source.count(gen_mobile_store_ctas.BLOCK_START)
            )
            generated = gen_mobile_store_ctas.BLOCK_RE.search(primary_source)
            self.assertIsNotNone(generated)
            generated_source = generated.group(0)
            self.assertIn("Get the app", generated_source)
            self.assertNotIn("Plain link", generated_source)
            self.assertIn("ct=hero&amp;mt=8", generated_source)
            self.assertIn(
                'src="/ios-app-guide/assets/mobile-store-cta-v1.js"',
                generated_source,
            )
            self.assertIn("defer", generated_source)
            self.assertIn("white-space:nowrap", gen_mobile_store_ctas.SCRIPT)
            self.assertIn("min-height:48px", gen_mobile_store_ctas.SCRIPT)
            self.assertIn(
                "safe-area-inset-bottom", gen_mobile_store_ctas.SCRIPT
            )
            self.assertIn(
                "prefers-reduced-motion:reduce",
                gen_mobile_store_ctas.SCRIPT,
            )
            self.assertIn("IntersectionObserver", gen_mobile_store_ctas.SCRIPT)
            self.assertIn(
                "window.scrollY >= threshold", gen_mobile_store_ctas.SCRIPT
            )
            self.assertNotIn("fetch(", gen_mobile_store_ctas.SCRIPT)
            self.assertNotIn("sendBeacon", gen_mobile_store_ctas.SCRIPT)

            self.assertIn(
                "Localized App Store label",
                ghost.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Fallback label",
                plain.read_text(encoding="utf-8"),
            )
            self.assertTrue(
                gen_mobile_store_ctas.ensure_mobile_cta(
                    stale, "6773017109"
                )
            )
            self.assertNotIn(
                gen_mobile_store_ctas.BLOCK_START,
                stale.read_text(encoding="utf-8"),
            )
            with self.assertRaisesRegex(ValueError, "closing body"):
                gen_mobile_store_ctas.ensure_mobile_cta(
                    invalid, "6773017109"
                )
            self.assertEqual(
                "/ios-app-guide/assets/mobile-store-cta-v1.js",
                gen_mobile_store_ctas.asset_href(),
            )
            with self.assertRaisesRegex(ValueError, "site URL"):
                gen_mobile_store_ctas.asset_href("javascript:alert(1)")
            with self.assertRaisesRegex(ValueError, "asset URL"):
                gen_mobile_store_ctas.mobile_cta_block(
                    "https://apps.apple.com/app/id6773017109",
                    "Get the app",
                    '"><script>',
                )

    def test_premium_guide_design_covers_public_locales_and_prunes_stale_links(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pages = workspace / "site"
            pages.mkdir()
            linked_pages = workspace / "linked-site"
            linked_pages.symlink_to(pages, target_is_directory=True)
            guide = pages / "guides" / "lumibopomofo.html"
            localized = pages / "zh-Hant" / "guides" / "lumibopomofo.html"
            story = pages / "stories" / "lumibopomofo.html"
            poster = pages / "stories" / "img" / "lumibopomofo-poster.jpg"
            hub = pages / "hubs" / "lumibopomofo.html"
            stale = pages / "fr-FR" / "guides" / "stale.html"
            for path in (guide, localized, story, poster, hub, stale):
                path.parent.mkdir(parents=True, exist_ok=True)
            site = gen_guide_design.SITE
            viewport = (
                '<meta name="viewport" '
                'content="width=device-width, initial-scale=1">'
            )
            guide.write_text(
                "<head>"
                f"{viewport}"
                "<title>Lumi Bopomofo</title>"
                f'<link rel="canonical" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="en" href="{site}/guides/lumibopomofo.html">'
                f'<link rel="alternate" hreflang="zh-Hant" href="{site}/zh-Hant/guides/lumibopomofo.html">'
                "</head><body><main><h1>Lumi Bopomofo</h1>"
                "<p>Guide introduction.</p></main></body>",
                encoding="utf-8",
            )
            localized.write_text(
                f"<head>{viewport}<title>注音</title></head>"
                "<body><main><h1>注音</h1></main></body>",
                encoding="utf-8",
            )
            story.write_text(
                "<head>"
                f'<link rel="canonical" href="{site}/stories/lumibopomofo.html">'
                "</head><body>"
                f'<amp-story poster-portrait-src="{site}/stories/img/lumibopomofo-poster.jpg">',
                encoding="utf-8",
            )
            poster.write_bytes(b"poster")
            hub.write_text("<head></head>", encoding="utf-8")
            stale.write_text(
                "<head>"
                f"{gen_guide_design.BLOCK_START}"
                '<link rel="stylesheet" href="/old/guide-premium-v1.css">'
                f"{gen_guide_design.BLOCK_END}"
                "</head><body>Stale</body>",
                encoding="utf-8",
            )
            (pages / "index.html").write_text(
                f'<head><link rel="canonical" href="{site}/index.html"></head>',
                encoding="utf-8",
            )
            for relative in (
                "feed.xml",
                "rss.xml",
                "feed.json",
                "llms-full.txt",
                "apps/index.html",
            ):
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("resource", encoding="utf-8")

            with mock.patch.object(
                gen_guide_design,
                "live_app_keys",
                return_value={"lumibopomofo"},
            ) as live_lookup:
                first = gen_guide_design.generate(linked_pages)
                asset = pages / gen_guide_design.ASSET_RELATIVE
                tracked = (guide, localized, stale, asset)
                mtimes = {path: path.stat().st_mtime_ns for path in tracked}
                second = gen_guide_design.generate(linked_pages)

            self.assertEqual(
                {
                    "apps": 1,
                    "guide_pages": 2,
                    "languages": 2,
                    "changed_files": 4,
                },
                first,
            )
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(2, live_lookup.call_count)
            live_lookup.assert_called_with(
                gen_guide_design.APPSTORE, str(linked_pages), refresh=False
            )
            self.assertEqual(
                mtimes, {path: path.stat().st_mtime_ns for path in tracked}
            )
            href = gen_guide_design.stylesheet_href(site)
            block = gen_guide_design.design_block(href)
            for path in (guide, localized):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(1, source.count(block))
                self.assertLess(
                    source.index(viewport) + len(viewport),
                    source.index(gen_guide_design.BLOCK_START),
                )
            self.assertIn(
                "<p>Guide introduction.</p>",
                guide.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                gen_guide_design.BLOCK_START,
                stale.read_text(encoding="utf-8"),
            )
            css = asset.read_text(encoding="utf-8")
            self.assertEqual(gen_guide_design.STYLESHEET, css)
            for feature in (
                "margin-inline",
                "padding-inline",
                "text-align: center",
                "white-space: nowrap",
                "text-overflow: ellipsis",
                "unicode-bidi: plaintext",
                ":focus-visible",
                "@media screen and (prefers-color-scheme: dark)",
                "prefers-reduced-motion: reduce",
                "@media print",
            ):
                self.assertIn(feature, css)
            print_css = css.split("@media print", 1)[1]
            self.assertIn(
                'main p > a[href^="https://apps.apple.com/app/id"]:visited',
                print_css,
            )
            self.assertNotIn(".iag-app-preview__link", css)
            self.assertNotIn("javascript", css.lower())

            conflicting = pages / "guides" / "conflicting.html"
            conflicting.write_text(
                f"<head>{viewport}"
                '<link rel="stylesheet" '
                'href="/wrong/guide-premium-v1.css"></head>',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                gen_guide_design.ensure_design(conflicting, href)

            duplicate_viewport = pages / "guides" / "duplicate-viewport.html"
            duplicate_viewport.write_text(
                f"<head>{viewport}{viewport}</head>", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "one viewport"):
                gen_guide_design.ensure_design(duplicate_viewport, href)

    def test_published_public_guides_share_one_premium_stylesheet(self):
        pages = Path(GEO) / "pages"
        live_keys = set(
            gen_guide_design.live_app_keys(
                gen_guide_design.APPSTORE, str(pages), refresh=False
            )
        )
        targets, app_count = gen_smart_app_banners.build_targets(
            pages, live_keys, gen_guide_design.SITE
        )
        self.assertGreaterEqual(app_count, 24)
        self.assertGreaterEqual(len(targets), app_count)
        self.assertEqual(
            gen_guide_design.STYLESHEET,
            (pages / gen_guide_design.ASSET_RELATIVE).read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(
            gen_mobile_store_ctas.SCRIPT,
            (pages / gen_mobile_store_ctas.ASSET_RELATIVE).read_text(
                encoding="utf-8"
            ),
        )
        block = gen_guide_design.design_block(
            gen_guide_design.stylesheet_href()
        )
        linked = set()
        guide_pages = gen_smart_app_banners._guide_pages(pages)
        for path in guide_pages:
            source = path.read_text(encoding="utf-8")
            if gen_guide_design.BLOCK_START in source:
                linked.add(path)
                self.assertEqual(1, source.count(block))
                self.assertEqual(
                    1, len(gen_guide_design.VIEWPORT_RE.findall(source))
                )
            if path in targets:
                cta = gen_mobile_store_ctas.app_store_cta(
                    source, targets[path]
                )
                self.assertIsNotNone(cta)
                self.assertEqual(
                    1,
                    source.count(
                        gen_mobile_store_ctas.mobile_cta_block(*cta)
                    ),
                )
        self.assertEqual(set(targets) & guide_pages, linked)

        answer_pages = gen_smart_app_banners._answer_pages(pages)
        answer_targets = set(targets) & answer_pages
        self.assertGreater(len(answer_targets), 0)
        for path in answer_targets:
            source = path.read_text(encoding="utf-8")
            self.assertEqual(
                1,
                source.count(
                    gen_smart_app_banners.banner_block(targets[path])
                ),
            )
            cta = gen_mobile_store_ctas.app_store_cta(
                source, targets[path]
            )
            self.assertIsNotNone(cta)
            self.assertEqual(
                1,
                source.count(gen_mobile_store_ctas.mobile_cta_block(*cta)),
            )

    def test_atom_feed_keeps_guides_and_free_tools_within_the_item_cap(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_feed, "PAGES", directory
        ):
            root = Path(directory)
            for subdir in ("answers", "guides", "alternatives", "tools", "data"):
                (root / subdir).mkdir()
            for index in range(gen_feed.MAX_ITEMS + 5):
                (root / "answers" / f"recent-{index:02d}.html").write_text(
                    '<title>Recent answer</title>'
                    '<script type="application/ld+json">'
                    '{"dateModified":"2026-07-12"}</script>',
                    encoding="utf-8",
                )
            owned_answer = root / "answers" / "owned-resource.html"
            owned_answer.write_text(
                "<title>Owned resource</title>"
                f'<a class="cta" href="{gen_feed.SITE}/tools/owned.html">'
                "Open resource</a>"
                '<script type="application/ld+json">'
                '{"dateModified":"2020-01-01"}</script>',
                encoding="utf-8",
            )
            for name in ("app-one", "app-two"):
                (root / "guides" / f"{name}.html").write_text(
                    f"<title>{name}</title>"
                    '<script type="application/ld+json">'
                    '{"dateModified":"2020-01-01"}</script>',
                    encoding="utf-8",
                )
            for index in range(25):
                (root / "tools" / f"tool-{index:02d}.html").write_text(
                    f"<title>tool-{index:02d}</title>"
                    '<script type="application/ld+json">'
                    '{"dateModified":"2026-07-14"}</script>',
                    encoding="utf-8",
                )
            for index in range(10):
                (root / "data" / f"dataset-{index:02d}.html").write_text(
                    f"<title>dataset-{index:02d}</title>"
                    '<script type="application/ld+json">'
                    '{"dateModified":"2026-07-15"}</script>',
                    encoding="utf-8",
                )
            required_data = root / gen_feed.REQUIRED_RELATIVE_PATHS[0]
            required_data.write_text(
                "<title>Required authority dataset</title>"
                '<script type="application/ld+json">'
                '{"dateModified":"2020-01-01"}</script>',
                encoding="utf-8",
            )
            items = gen_feed.collect()
        self.assertEqual(gen_feed.MAX_ITEMS, len(items))
        urls = {url for _, url, _ in items}
        self.assertTrue(
            {
                f"{gen_feed.SITE}/guides/app-one.html",
                f"{gen_feed.SITE}/guides/app-two.html",
                f"{gen_feed.SITE}/answers/owned-resource.html",
                f"{gen_feed.SITE}/{gen_feed.REQUIRED_RELATIVE_PATHS[0]}",
            }
            <= urls
        )
        for subdir, limit in gen_feed.RESERVED_SUBDIR_LIMITS:
            self.assertEqual(
                limit,
                sum(f"/{subdir}/" in url for url in urls),
            )

    def test_syndication_feed_serializers_share_one_valid_item_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = []
            for index in range(2):
                page = root / f"item-{index}.html"
                page.write_text(
                    f"<title>Item {index}</title>"
                    f'<meta name="description" content="Summary {index}.">',
                    encoding="utf-8",
                )
                items.append(
                    (
                        dt.datetime(
                            2026,
                            7,
                            12,
                            index,
                            tzinfo=dt.timezone.utc,
                        ).timestamp(),
                        f"https://example.com/item-{index}",
                        str(page),
                    )
                )
            newest = items[-1][0]
            atom = ET.fromstring(gen_feed.render_atom(items, gen_feed.iso(newest)))
            rss = ET.fromstring(gen_feed.render_rss(items, newest))
            json_feed = json.loads(gen_feed.render_json_feed(items))

        atom_ns = "{http://www.w3.org/2005/Atom}"
        atom_ids = {
            entry.find(atom_ns + "id").text
            for entry in atom.findall(atom_ns + "entry")
        }
        self.assertEqual(
            "2.0",
            rss.attrib["version"],
        )
        channel = rss.find("channel")
        self.assertIsNotNone(channel.find("title"))
        self.assertIsNotNone(channel.find("link"))
        self.assertIsNotNone(channel.find("description"))
        self.assertEqual(
            list(gen_feed.WEBSUB_HUBS),
            [
                link.attrib["href"]
                for link in atom.findall(f"{atom_ns}link[@rel='hub']")
            ],
        )
        self.assertEqual(
            [
                *gen_feed.WEBSUB_HUBS,
                rsscloud_config.RSSCLOUD_WEBSUB_HUB,
            ],
            [
                link.attrib["href"]
                for link in channel.findall(f"{atom_ns}link[@rel='hub']")
            ],
        )
        cloud = channel.find("cloud")
        self.assertEqual(
            {
                "domain": rsscloud_config.RSSCLOUD_DOMAIN,
                "port": rsscloud_config.RSSCLOUD_PORT,
                "path": rsscloud_config.RSSCLOUD_NOTIFY_PATH,
                "registerProcedure": "",
                "protocol": rsscloud_config.RSSCLOUD_PROTOCOL,
            },
            cloud.attrib,
        )
        source_ns = f"{{{rsscloud_config.RSSCLOUD_SOURCE_NAMESPACE}}}"
        self.assertEqual(
            rsscloud_config.RSSCLOUD_NOTIFY_URL,
            channel.findtext(f"{source_ns}cloud"),
        )
        rss_items = channel.findall("item")
        rss_ids = {item.find("guid").text for item in rss_items}
        for item in rss_items:
            self.assertEqual("true", item.find("guid").attrib["isPermaLink"])
            self.assertEqual(
                dt.timezone.utc,
                email.utils.parsedate_to_datetime(
                    item.find("pubDate").text
                ).tzinfo,
            )
        self.assertEqual(
            "https://jsonfeed.org/version/1.1",
            json_feed["version"],
        )
        self.assertEqual(f"{gen_feed.SITE}/feed.json", json_feed["feed_url"])
        self.assertEqual(
            [
                {"type": "WebSub", "url": hub}
                for hub in gen_feed.WEBSUB_HUBS
            ],
            json_feed["hubs"],
        )
        json_ids = {item["id"] for item in json_feed["items"]}
        for item in json_feed["items"]:
            self.assertTrue(item["content_text"])
            self.assertRegex(
                item["date_modified"],
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
            )
        self.assertEqual(atom_ids, rss_ids)
        self.assertEqual(atom_ids, json_ids)

    def test_syndication_feeds_attach_verified_app_preview_images(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_feed, "PAGES", directory
        ):
            root = Path(directory)
            guide = root / "guides" / "sample-app.html"
            card = root / "social" / "img" / "sample-app-share.jpg"
            guide.parent.mkdir(parents=True)
            card.parent.mkdir(parents=True)
            image_url = (
                f"{gen_feed.SITE}/social/img/sample-app-share.jpg"
            )
            guide.write_text(
                "<title>Sample App Guide</title>"
                '<meta name="description" content="A visual app guide.">'
                f'<meta property="og:image" content="{image_url}">',
                encoding="utf-8",
            )
            Image.new("RGB", gen_feed.PREVIEW_SIZE, "#0d6b50").save(
                card, "JPEG", progressive=True
            )
            item_url = f"{gen_feed.SITE}/guides/sample-app.html"
            items = [(1_720_742_400, item_url, str(guide))]
            atom = ET.fromstring(
                gen_feed.render_atom(items, gen_feed.iso(items[0][0]))
            )
            rss = ET.fromstring(gen_feed.render_rss(items, items[0][0]))
            json_feed = json.loads(gen_feed.render_json_feed(items))

            atom_ns = "{http://www.w3.org/2005/Atom}"
            enclosure = atom.find(
                f"{atom_ns}entry/{atom_ns}link[@rel='enclosure']"
            )
            self.assertEqual(image_url, enclosure.attrib["href"])
            self.assertEqual("image/jpeg", enclosure.attrib["type"])
            self.assertEqual(str(card.stat().st_size), enclosure.attrib["length"])

            media_ns = f"{{{gen_feed.MEDIA_NS}}}"
            rss_item = rss.find("channel/item")
            content = rss_item.find(f"{media_ns}content")
            thumbnail = rss_item.find(f"{media_ns}thumbnail")
            self.assertEqual(
                {
                    "url": image_url,
                    "fileSize": str(card.stat().st_size),
                    "type": "image/jpeg",
                    "medium": "image",
                    "isDefault": "true",
                    "expression": "full",
                    "width": "1200",
                    "height": "675",
                },
                content.attrib,
            )
            self.assertEqual(
                {"url": image_url, "width": "1200", "height": "675"},
                thumbnail.attrib,
            )
            self.assertEqual(
                "Sample App Guide preview image",
                content.findtext(f"{media_ns}title"),
            )
            self.assertEqual(image_url, json_feed["items"][0]["image"])
            self.assertEqual(image_url, json_feed["items"][0]["banner_image"])

            Image.new("RGB", (600, 338), "#0d6b50").save(card, "JPEG")
            with self.assertRaisesRegex(ValueError, "must be JPEG 1200x675"):
                gen_feed.render_rss(items, items[0][0])
            Image.new("RGB", gen_feed.PREVIEW_SIZE, "#0d6b50").save(
                card, "JPEG"
            )
            guide.write_text(
                "<title>Sample App Guide</title>"
                '<meta property="og:image" '
                'content="https://example.com/unowned.jpg">',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unowned or mismatched"):
                gen_feed.render_json_feed(items)

    def test_syndication_generator_writes_three_idempotent_feeds(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            gen_feed,
            "PAGES",
            directory,
        ), mock.patch.object(
            gen_feed,
            "_git_modified_times",
            return_value={},
        ):
            root = Path(directory)
            for subdir in ("answers", "guides", "alternatives", "tools", "data"):
                (root / subdir).mkdir()
            page = root / "guides" / "sample-app.html"
            page.write_text(
                "<html><head><title>Sample App Guide</title>"
                '<meta name="description" content="A stable app guide.">'
                '<script type="application/ld+json">'
                '{"dateModified":"2026-07-12"}</script></head><body></body></html>',
                encoding="utf-8",
            )
            gen_feed.main()
            outputs = tuple(
                root / filename
                for filename in ("feed.xml", "rss.xml", "feed.json")
            )
            self.assertTrue(all(path.is_file() for path in outputs))
            tracked = (*outputs, page)
            mtimes = {path: path.stat().st_mtime_ns for path in tracked}
            page_content = page.read_text(encoding="utf-8")
            for media_type in (
                "application/atom+xml",
                "application/rss+xml",
                "application/feed+json",
            ):
                self.assertEqual(1, page_content.count(f'type="{media_type}"'))
            gen_feed.main()
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in tracked},
            )

    def test_feed_autodiscovery_advertises_atom_rss_and_json_feed(self):
        links = build_pages_i18n.feed_discovery_links()
        for media_type, filename in (
            ("application/atom+xml", "feed.xml"),
            ("application/rss+xml", "rss.xml"),
            ("application/feed+json", "feed.json"),
        ):
            self.assertIn(f'type="{media_type}"', links)
            self.assertIn(f'href="{build_pages_i18n.SITE}/{filename}"', links)

    def test_published_syndication_feeds_cover_every_app_guide(self):
        pages = Path(GEO) / "pages"
        atom_ns = "{http://www.w3.org/2005/Atom}"
        atom = ET.parse(pages / "feed.xml").getroot()
        rss = ET.parse(pages / "rss.xml").getroot()
        json_feed = json.loads((pages / "feed.json").read_text(encoding="utf-8"))
        atom_ids = [
            entry.find(atom_ns + "id").text
            for entry in atom.findall(atom_ns + "entry")
        ]
        rss_ids = [
            item.find("guid").text
            for item in rss.find("channel").findall("item")
        ]
        json_ids = [item["id"] for item in json_feed["items"]]
        self.assertEqual(gen_feed.MAX_ITEMS, len(atom_ids))
        self.assertEqual(atom_ids, rss_ids)
        self.assertEqual(atom_ids, json_ids)
        atom_entries = {
            entry.findtext(atom_ns + "id"): entry
            for entry in atom.findall(atom_ns + "entry")
        }
        rss_items = {
            item.findtext("guid"): item
            for item in rss.find("channel").findall("item")
        }
        json_items = {item["id"]: item for item in json_feed["items"]}
        media_ns = f"{{{gen_feed.MEDIA_NS}}}"
        preview_keys = {
            path.name.removesuffix("-share.jpg")
            for path in (pages / "social" / "img").glob("*-share.jpg")
        }
        expected_preview_ids = {
            f"{gen_feed.SITE}/guides/{key}.html" for key in preview_keys
        }
        self.assertGreaterEqual(len(expected_preview_ids), 24)
        self.assertTrue(expected_preview_ids <= set(atom_ids))
        for item_id in atom_ids:
            enclosure = atom_entries[item_id].find(
                f"{atom_ns}link[@rel='enclosure']"
            )
            media_content = rss_items[item_id].find(f"{media_ns}content")
            media_thumbnail = rss_items[item_id].find(f"{media_ns}thumbnail")
            json_item = json_items[item_id]
            if item_id in expected_preview_ids:
                key = item_id.rsplit("/", 1)[-1].removesuffix(".html")
                image_url = (
                    f"{gen_feed.SITE}/social/img/{key}-share.jpg"
                )
                card = pages / "social" / "img" / f"{key}-share.jpg"
                self.assertEqual(image_url, enclosure.attrib["href"])
                self.assertEqual("image/jpeg", enclosure.attrib["type"])
                self.assertEqual(
                    str(card.stat().st_size), enclosure.attrib["length"]
                )
                self.assertEqual(image_url, media_content.attrib["url"])
                self.assertEqual("image", media_content.attrib["medium"])
                self.assertEqual("1200", media_content.attrib["width"])
                self.assertEqual("675", media_content.attrib["height"])
                self.assertEqual(image_url, media_thumbnail.attrib["url"])
                self.assertEqual(image_url, json_item["image"])
                self.assertEqual(image_url, json_item["banner_image"])
                with Image.open(card) as image:
                    self.assertEqual("JPEG", image.format)
                    self.assertEqual(gen_feed.PREVIEW_SIZE, image.size)
            else:
                self.assertIsNone(enclosure)
                self.assertIsNone(media_content)
                self.assertIsNone(media_thumbnail)
                self.assertNotIn("image", json_item)
                self.assertNotIn("banner_image", json_item)
        expected_guides = {
            f"{gen_feed.SITE}/guides/{path.name}"
            for path in (pages / "guides").glob("*.html")
            if path.name != "index.html"
        }
        self.assertTrue(expected_guides <= set(atom_ids))
        expected_resource_answers = set()
        for path in (pages / "answers").glob("*.html"):
            if path.name == "index.html":
                continue
            content = path.read_text(encoding="utf-8")
            match = gen_feed.CTA_RE.search(content[:32_000])
            if match and match.group(1).startswith(f"{gen_feed.SITE}/"):
                expected_resource_answers.add(
                    f"{gen_feed.SITE}/answers/{path.name}"
                )
        self.assertGreater(len(expected_resource_answers), 10)
        self.assertTrue(expected_resource_answers <= set(atom_ids))
        self.assertEqual(
            gen_feed.RESERVED_SUBDIR_LIMITS[0][1],
            sum("/tools/" in url for url in atom_ids),
        )
        self.assertEqual(
            "https://jsonfeed.org/version/1.1",
            json_feed["version"],
        )
        self.assertLess((pages / "feed.json").stat().st_size, 100_000)
        for url in atom_ids:
            prefix = f"{gen_feed.SITE}/"
            if not url.startswith(prefix) or not url.endswith(".html"):
                continue
            content = (pages / url[len(prefix):]).read_text(encoding="utf-8")
            for media_type, filename in (
                ("application/atom+xml", "feed.xml"),
                ("application/rss+xml", "rss.xml"),
                ("application/feed+json", "feed.json"),
            ):
                self.assertEqual(1, content.count(f'type="{media_type}"'))
                self.assertIn(f'href="{gen_feed.SITE}/{filename}"', content)

        discovery_pages = []
        for page in (pages / "index.html", *pages.glob("*/*.html")):
            content = page.read_text(encoding="utf-8")
            if 'type="application/atom+xml"' in content:
                discovery_pages.append(content)
        self.assertGreater(len(discovery_pages), 1_000)
        for content in discovery_pages:
            for media_type, filename in (
                ("application/atom+xml", "feed.xml"),
                ("application/rss+xml", "rss.xml"),
                ("application/feed+json", "feed.json"),
            ):
                self.assertEqual(1, content.count(f'type="{media_type}"'))
                self.assertIn(f'href="{gen_feed.SITE}/{filename}"', content)

        llms = (pages / "llms.txt").read_text(encoding="utf-8")
        llms_full = (pages / "llms-full.txt").read_text(encoding="utf-8")
        for content in (llms, llms_full):
            self.assertIn(f"{gen_feed.SITE}/feed.xml", content)
            self.assertIn(f"{gen_feed.SITE}/rss.xml", content)
            self.assertIn(f"{gen_feed.SITE}/feed.json", content)
            for hub in gen_feed.WEBSUB_HUBS:
                self.assertIn(hub, content)
            self.assertIn(rsscloud_config.RSSCLOUD_NOTIFY_URL, content)
            self.assertIn(rsscloud_config.RSSCLOUD_WEBSUB_HUB, content)

    def test_websub_hub_configuration_is_unique_https_and_shared(self):
        self.assertEqual(
            websub_config.DEFAULT_WEBSUB_HUBS,
            gen_feed.WEBSUB_HUBS,
        )
        self.assertEqual(gen_feed.WEBSUB_HUBS, notify_websub.WEBSUB_HUBS)
        self.assertEqual(2, len(gen_feed.WEBSUB_HUBS))
        with self.assertRaisesRegex(ValueError, "unique"):
            websub_config.configured_hubs(
                "https://example.com/,https://example.com/"
            )
        with self.assertRaisesRegex(ValueError, "invalid"):
            websub_config.configured_hubs("http://example.com/")

    def test_websub_notifier_verifies_deployment_and_retries_publish(self):
        class Response:
            def __init__(self, body=b"", status=200):
                self.body = body
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bodies = []
            for filename in notify_websub.FEED_FILES:
                body = f"deployed {filename}".encode()
                (root / filename).write_bytes(body)
                bodies.append(body)
            with mock.patch.object(
                notify_websub.urllib.request,
                "urlopen",
                side_effect=[Response(body) for body in bodies],
            ) as urlopen:
                notify_websub.wait_until_deployed(
                    root, attempts=1, timeout=7
                )
            self.assertEqual(len(notify_websub.TOPICS), urlopen.call_count)
            self.assertTrue(
                all(call.kwargs["timeout"] == 7 for call in urlopen.call_args_list)
            )

        with mock.patch.object(
            notify_websub.urllib.request,
            "urlopen",
            side_effect=[OSError("offline"), Response(status=204)],
        ) as urlopen, mock.patch.object(notify_websub.time, "sleep") as sleep:
            self.assertEqual(
                204,
                notify_websub.notify(attempts=2, timeout=9, delay=1),
            )
        self.assertEqual(2, urlopen.call_count)
        sleep.assert_called_once_with(1)
        request = urlopen.call_args_list[-1].args[0]
        payload = urllib.parse.parse_qs(request.data.decode("ascii"))
        self.assertEqual(["publish"], payload["hub.mode"])
        self.assertEqual(list(notify_websub.TOPICS), payload["hub.url"])
        self.assertEqual(
            "application/x-www-form-urlencoded; charset=utf-8",
            request.get_header("Content-type"),
        )

    def test_websub_notifier_attempts_every_hub_before_failing(self):
        first, second = notify_websub.WEBSUB_HUBS
        with mock.patch.object(
            notify_websub,
            "notify",
            side_effect=[RuntimeError("first unavailable"), 204],
        ) as notify:
            with self.assertRaisesRegex(RuntimeError, first):
                notify_websub.notify_all(attempts=1)
        self.assertEqual(
            [first, second],
            [call.kwargs["hub"] for call in notify.call_args_list],
        )

    def test_websub_notifier_surfaces_total_failure(self):
        with mock.patch.object(
            notify_websub.urllib.request,
            "urlopen",
            side_effect=OSError("offline"),
        ) as urlopen, mock.patch.object(notify_websub.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "after 3 attempts"):
                notify_websub.notify(attempts=3, delay=0)
        self.assertEqual(3, urlopen.call_count)

    def test_rsscloud_notifier_verifies_bytes_and_parses_json_or_xml(self):
        class Response:
            def __init__(self, body=b"", status=200):
                self.body = body
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        with tempfile.TemporaryDirectory() as directory:
            body = b"deployed rss"
            Path(directory, notify_rsscloud.RSS_FILE).write_bytes(body)
            with mock.patch.object(
                notify_rsscloud.urllib.request,
                "urlopen",
                return_value=Response(body),
            ) as urlopen:
                notify_rsscloud.wait_until_deployed(
                    directory, attempts=1, timeout=7
                )
            self.assertEqual(7, urlopen.call_args.kwargs["timeout"])

        responses = (
            b'{"success":true,"msg":"Thanks for the ping."}',
            b'<result success="true" msg="Thanks again."/>',
        )
        for body in responses:
            with self.subTest(body=body), mock.patch.object(
                notify_rsscloud.urllib.request,
                "urlopen",
                return_value=Response(body),
            ) as urlopen:
                self.assertTrue(notify_rsscloud.ping(attempts=1))
                request = urlopen.call_args.args[0]
                payload = urllib.parse.parse_qs(
                    request.data.decode("ascii")
                )
                self.assertEqual([notify_rsscloud.TOPIC], payload["url"])
                self.assertEqual(
                    "application/x-www-form-urlencoded; charset=utf-8",
                    request.get_header("Content-type"),
                )

    def test_rsscloud_notifier_retries_and_surfaces_rejection(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"success":false,"msg":"Feed unavailable"}'

        with mock.patch.object(
            notify_rsscloud.urllib.request,
            "urlopen",
            side_effect=[OSError("offline"), Response()],
        ) as urlopen, mock.patch.object(
            notify_rsscloud.time, "sleep"
        ) as sleep:
            with self.assertRaisesRegex(RuntimeError, "Feed unavailable"):
                notify_rsscloud.ping(attempts=2, delay=1)
        self.assertEqual(2, urlopen.call_count)
        sleep.assert_called_once_with(1)

    def test_pages_deploy_notifies_syndication_only_after_success(self):
        workflow = (
            Path(GEO) / "pages" / ".github" / "workflows" / "pages.yml"
        ).read_text(encoding="utf-8")
        preserve = workflow.index("cp _engine/geo/notify_websub.py")
        preserve_config = workflow.index("cp _engine/geo/websub_config.py")
        preserve_rsscloud = workflow.index("cp _engine/geo/notify_rsscloud.py")
        preserve_rsscloud_config = workflow.index(
            "cp _engine/geo/rsscloud_config.py"
        )
        prune = workflow.index("rm -rf _engine")
        deploy = workflow.index("uses: actions/deploy-pages@v4")
        notify = workflow.rindex('python3 \"$RUNNER_TEMP/notify_websub.py\"')
        notify_rsscloud = workflow.rindex(
            'python3 \"$RUNNER_TEMP/notify_rsscloud.py\"'
        )
        enforce = workflow.index("Enforce syndication notification results")
        self.assertLess(preserve, prune)
        self.assertLess(preserve_config, prune)
        self.assertLess(preserve_rsscloud, prune)
        self.assertLess(preserve_rsscloud_config, prune)
        self.assertLess(prune, deploy)
        self.assertLess(deploy, notify)
        self.assertLess(notify, notify_rsscloud)
        self.assertLess(notify_rsscloud, enforce)
        self.assertIn("--feed-dir \"$GITHUB_WORKSPACE\"", workflow)
        self.assertIn("timeout-minutes: 6", workflow)
        self.assertIn(
            'test "${{ steps.notify_websub.outcome }}" = "success"',
            workflow,
        )
        self.assertIn(
            'test "${{ steps.notify_rsscloud.outcome }}" = "success"',
            workflow,
        )

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

    def _seed_zhuyin_csvw_pages(self, pages):
        data = pages / "data"
        data.mkdir(parents=True)
        catalog = {
            "@context": "https://schema.org",
            "@type": "DataCatalog",
            "dataset": [
                {
                    "@type": "Dataset",
                    "url": zhuyin_csvw_metadata.CROISSANT_PAGE,
                }
            ],
        }
        (data / "index.html").write_text(
            '<script type="application/ld+json">'
            + json.dumps(catalog)
            + '</script><main><a class="item" href="'
            + zhuyin_csvw_metadata.CROISSANT_PAGE
            + '"><h2>Croissant dataset</h2></a>'
            + '<p class="foot">Footer</p></main>',
            encoding="utf-8",
        )
        (data / zhuyin_csvw_metadata.CSV_FILENAME).write_text(
            zhuyin_croissant_dataset.render_csv(
                zhuyin_croissant_dataset.records()
            ),
            encoding="utf-8",
        )

    def test_zhuyin_csvw_metadata_is_complete_deterministic_and_discoverable(self):
        rows = zhuyin_croissant_dataset.records()
        first = zhuyin_csvw_metadata.make_artifacts(
            zhuyin_csvw_metadata.INITIAL_DATE
        )
        second = zhuyin_csvw_metadata.make_artifacts(
            zhuyin_csvw_metadata.INITIAL_DATE
        )
        self.assertEqual(
            {
                key: value["bytes"]
                for key, value in first.items()
                if "bytes" in value
            },
            {
                key: value["bytes"]
                for key, value in second.items()
                if "bytes" in value
            },
        )
        zhuyin_csvw_metadata.validate_artifacts(rows, first)
        metadata = json.loads(first["csvw"]["bytes"])
        self.assertEqual(
            [
                zhuyin_csvw_metadata.CSVW_CONTEXT,
                {"@language": "en"},
            ],
            metadata["@context"],
        )
        self.assertEqual(
            zhuyin_csvw_metadata.CSV_FILENAME,
            metadata["url"],
        )
        schema = metadata["tableSchema"]
        self.assertEqual("symbol_id", schema["primaryKey"])
        self.assertEqual(
            list(zhuyin_croissant_dataset.FIELD_NAMES),
            [column["name"] for column in schema["columns"]],
        )
        self.assertTrue(all(column["required"] for column in schema["columns"]))
        self.assertEqual(
            set(zhuyin_csvw_metadata.CSVW_RECOMMENDATIONS),
            {
                item["@id"]
                for item in metadata["dc:conformsTo"]
            },
        )
        self.assertEqual(
            "application/csvm+json",
            first["csvw"]["media_type"],
        )
        self.assertEqual(
            37,
            len(
                list(
                    csv.DictReader(
                        first["csv"]["bytes"].decode("utf-8").splitlines()
                    )
                )
            ),
        )
        with zipfile.ZipFile(io.BytesIO(first["bundle"]["bytes"])) as archive:
            self.assertEqual(sorted(archive.namelist()), archive.namelist())
            self.assertEqual(
                {
                    zhuyin_csvw_metadata.CSV_FILENAME,
                    zhuyin_csvw_metadata.CSVW_FILENAME,
                    zhuyin_csvw_metadata.README_FILENAME,
                    zhuyin_csvw_metadata.LICENSE_FILENAME,
                    zhuyin_csvw_metadata.CHECKSUM_FILENAME,
                },
                set(archive.namelist()),
            )
            self.assertTrue(
                all(
                    info.date_time == zhuyin_csvw_metadata.ZIP_TIMESTAMP
                    for info in archive.infolist()
                )
            )
        with mock.patch.object(
            zhuyin_csvw_metadata,
            "render_readme",
            return_value=b"https://apps.apple.com/app/id6773017109\n",
        ):
            contaminated = zhuyin_csvw_metadata.make_artifacts(
                zhuyin_csvw_metadata.INITIAL_DATE
            )
        with self.assertRaises(ValueError):
            zhuyin_csvw_metadata.validate_artifacts(rows, contaminated)

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_csvw_pages(pages)
            urls = zhuyin_csvw_metadata.build(
                pages,
                app_public=False,
            )
            expected = [
                pages / zhuyin_csvw_metadata.PACKAGE_PATH / "index.html",
                pages
                / "zh-Hant"
                / zhuyin_csvw_metadata.PACKAGE_PATH
                / "index.html",
                pages / "data" / zhuyin_csvw_metadata.CSVW_FILENAME,
                pages
                / zhuyin_csvw_metadata.PACKAGE_PATH
                / zhuyin_csvw_metadata.BUNDLE_FILENAME,
                pages
                / zhuyin_csvw_metadata.PACKAGE_PATH
                / zhuyin_csvw_metadata.CHECKSUM_FILENAME,
                pages
                / zhuyin_csvw_metadata.PACKAGE_PATH
                / zhuyin_csvw_metadata.MANIFEST_FILENAME,
                pages / "sitemap_csvw.xml",
            ]
            self.assertEqual(7, len(urls))
            self.assertTrue(all(path.exists() for path in expected))
            english = expected[0].read_text(encoding="utf-8")
            traditional = expected[1].read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn('hreflang="en"', page)
                self.assertIn('hreflang="zh-Hant"', page)
                self.assertIn(zhuyin_csvw_metadata.CSVW_FILENAME, page)
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn('"SoftwareApplication"', page)
            self.assertIn("Bopomofo CSVW Metadata", english)
            self.assertIn("完整 37 注音符號 CSVW", traditional)
            self.assertIn("<td>聲母</td>", traditional)
            public = zhuyin_csvw_metadata.render_page(
                "en",
                first,
                app_public=True,
            )
            self.assertIn(zhuyin_csvw_metadata.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            index = (pages / "data" / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                1,
                index.count(
                    f'href="{zhuyin_csvw_metadata.PACKAGE_URL}"'
                ),
            )
            catalog = json.loads(
                re.search(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    index,
                    re.DOTALL,
                ).group(1)
            )
            entry = next(
                item
                for item in catalog["dataset"]
                if item.get("url") == zhuyin_csvw_metadata.PACKAGE_URL
            )
            self.assertEqual(5, len(entry["distribution"]))
            sitemap = expected[-1].read_text(encoding="utf-8")
            for url in urls[:-1]:
                self.assertIn(url, sitemap)

            with mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(pages / "data"),
            ), mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("Bopomofo CSVW table metadata", content)
                self.assertIn(zhuyin_csvw_metadata.CSVW_URL, content)
                self.assertIn(zhuyin_csvw_metadata.BUNDLE_URL, content)
            for content in (robots, sitemap_index):
                self.assertIn("sitemap_csvw.xml", content)

            deep_items = json.loads(
                (
                    Path(GEO)
                    / "deep_items"
                    / "lumibopomofo.json"
                ).read_text(encoding="utf-8")
            )
            deep_item = next(
                item
                for item in deep_items
                if item["kind"] == "csvw_tabular_metadata"
            )
            self.assertEqual(
                zhuyin_csvw_metadata.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            self.assertIn("37 data rows and 12 columns", deep_item["detail"])
            self.assertIn(
                "does not certify this package",
                deep_item["detail"],
            )
            translations = json.loads(
                (
                    Path(GEO) / "i18n_trans" / "zh-Hant.json"
                ).read_text(encoding="utf-8")
            )

            def translated_strings(value, parent_key=""):
                if isinstance(value, str):
                    if parent_key not in {
                        "app_key",
                        "kind",
                        "match",
                        "primary_resource_url",
                        "url",
                    }:
                        yield value
                elif isinstance(value, list):
                    for child in value:
                        yield from translated_strings(child, parent_key)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        yield from translated_strings(child, key)

            missing = [
                value
                for value in translated_strings(deep_item)
                if value not in translations
            ]
            self.assertEqual([], missing)
            self.assertIn(
                "如何選擇：",
                translations[
                    "How to choose: " + deep_item["query"]
                ],
            )

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in [*expected, pages / "data" / "index.html"]
            }
            zhuyin_csvw_metadata.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    @unittest.skipUnless(
        importlib.util.find_spec("csvw"),
        "Official CSVW validation dependency is installed in CI",
    )
    def test_zhuyin_csvw_metadata_validates_with_official_processor(self):
        from csvw.metadata import Table

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_csvw_pages(pages)
            zhuyin_csvw_metadata.build(pages, app_public=False)
            metadata_path = (
                pages / "data" / zhuyin_csvw_metadata.CSVW_FILENAME
            )
            table = Table.from_file(metadata_path)
            loaded = list(table)
            self.assertEqual(37, len(loaded))
            self.assertEqual(
                list(zhuyin_croissant_dataset.FIELD_NAMES),
                list(loaded[0]),
            )
            self.assertEqual(list(range(1, 38)), [row["order"] for row in loaded])
            self.assertEqual(37, len({row["symbol_id"] for row in loaded}))

    def _seed_zhuyin_bagit_pages(self, pages):
        data = pages / "data"
        data.mkdir(parents=True)
        with mock.patch.object(
            gen_data_hub,
            "PAGES",
            str(pages),
        ), mock.patch.object(
            gen_data_hub,
            "DATA",
            str(data),
        ):
            gen_data_hub.build_zhuyin_page()
        (data / "index.html").write_text(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"DataCatalog",'
            '"dataset":[]}</script><main><a class="item" href="'
            f'{zhuyin_skos_vocabulary.SOURCE_PAGE}">'
            '<h2>Source dataset</h2></a>'
            '<p class="foot">Footer</p></main>',
            encoding="utf-8",
        )
        zhuyin_skos_vocabulary.build(pages, app_public=False)
        zhuyin_croissant_dataset.build(pages, app_public=False)
        zhuyin_csvw_metadata.build(pages, app_public=False)

    def test_zhuyin_bagit_package_is_complete_deterministic_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_bagit_pages(pages)
            payload, descriptions = zhuyin_bagit_package.load_payload(pages)
            first = zhuyin_bagit_package.make_artifacts(
                payload,
                descriptions,
                zhuyin_bagit_package.INITIAL_DATE,
            )
            second = zhuyin_bagit_package.make_artifacts(
                payload,
                descriptions,
                zhuyin_bagit_package.INITIAL_DATE,
            )
            self.assertEqual(
                {
                    key: value["bytes"]
                    for key, value in first.items()
                    if isinstance(value, dict) and "bytes" in value
                },
                {
                    key: value["bytes"]
                    for key, value in second.items()
                    if isinstance(value, dict) and "bytes" in value
                },
            )
            self.assertEqual(first["_bag_files"], second["_bag_files"])
            zhuyin_bagit_package.validate_artifacts(first)
            self.assertEqual(10, len(payload))
            self.assertEqual(
                f"{sum(len(value) for value in payload.values())}.10",
                zhuyin_bagit_package.payload_oxum(payload),
            )
            for algorithm in ("sha256", "sha512"):
                payload_manifest = zhuyin_bagit_package._manifest_entries(
                    first["_bag_files"][f"manifest-{algorithm}.txt"]
                )
                tag_manifest = zhuyin_bagit_package._manifest_entries(
                    first["_bag_files"][f"tagmanifest-{algorithm}.txt"]
                )
                self.assertEqual(set(payload), set(payload_manifest))
                self.assertEqual(
                    {
                        "bagit.txt",
                        "bag-info.txt",
                        "manifest-sha256.txt",
                        "manifest-sha512.txt",
                    },
                    set(tag_manifest),
                )
            with zipfile.ZipFile(io.BytesIO(first["bundle"]["bytes"])) as archive:
                self.assertEqual(sorted(archive.namelist()), archive.namelist())
                self.assertTrue(
                    all(
                        name.startswith(
                            zhuyin_bagit_package.BAG_ROOT + "/"
                        )
                        for name in archive.namelist()
                    )
                )
                self.assertTrue(
                    all(
                        info.date_time == zhuyin_bagit_package.ZIP_TIMESTAMP
                        and info.compress_type == zipfile.ZIP_STORED
                        for info in archive.infolist()
                    )
                )
            metadata = json.loads(first["metadata"]["bytes"])
            self.assertEqual(
                zhuyin_bagit_package.RFC_URL,
                metadata["conformsTo"],
            )
            self.assertEqual(10, len(metadata["hasPart"]))
            self.assertEqual(
                zhuyin_bagit_package.payload_oxum(payload),
                metadata["size"],
            )
            with mock.patch.object(
                zhuyin_bagit_package,
                "render_readme",
                return_value=b"https://apps.apple.com/app/id6773017109\n",
            ):
                contaminated_payload, contaminated_descriptions = (
                    zhuyin_bagit_package.load_payload(pages)
                )
            contaminated = zhuyin_bagit_package.make_artifacts(
                contaminated_payload,
                contaminated_descriptions,
                zhuyin_bagit_package.INITIAL_DATE,
            )
            with self.assertRaises(ValueError):
                zhuyin_bagit_package.validate_artifacts(contaminated)

            urls = zhuyin_bagit_package.build(pages, app_public=False)
            expected = (
                pages
                / zhuyin_bagit_package.PACKAGE_PATH
                / zhuyin_bagit_package.BUNDLE_FILENAME,
                pages
                / zhuyin_bagit_package.PACKAGE_PATH
                / zhuyin_bagit_package.CHECKSUM_FILENAME,
                pages
                / zhuyin_bagit_package.PACKAGE_PATH
                / zhuyin_bagit_package.METADATA_FILENAME,
                pages / zhuyin_bagit_package.PACKAGE_PATH / "index.html",
                pages
                / "zh-Hant"
                / zhuyin_bagit_package.PACKAGE_PATH
                / "index.html",
                pages / "sitemap_bagit.xml",
            )
            self.assertEqual(6, len(urls))
            self.assertTrue(all(path.exists() for path in expected))
            for page in expected[3:5]:
                content = page.read_text(encoding="utf-8")
                self.assertIn("RFC 8493", content)
                self.assertIn("Payload-Oxum", content)
                self.assertNotIn("apps.apple.com", content)
                self.assertNotIn('"SoftwareApplication"', content)
            public = zhuyin_bagit_package.render_page(
                "en",
                first,
                app_public=True,
            )
            self.assertIn(zhuyin_bagit_package.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            sitemap = expected[-1].read_text(encoding="utf-8")
            for url in urls[:-1]:
                self.assertIn(url, sitemap)
            index = (pages / "data" / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                1,
                index.count(
                    f'href="{zhuyin_bagit_package.PACKAGE_URL}"'
                ),
            )

            with mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(pages / "data"),
            ), mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("RFC 8493 BagIt", content)
                self.assertIn(zhuyin_bagit_package.BUNDLE_URL, content)
                self.assertIn(zhuyin_bagit_package.METADATA_URL, content)
            for content in (robots, sitemap_index):
                self.assertIn("sitemap_bagit.xml", content)

            deep_items = json.loads(
                (
                    Path(GEO)
                    / "deep_items"
                    / "lumibopomofo.json"
                ).read_text(encoding="utf-8")
            )
            deep_item = next(
                item
                for item in deep_items
                if item["kind"] == "bagit_digital_preservation"
            )
            self.assertEqual(
                zhuyin_bagit_package.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            self.assertIn("ten payload files", deep_item["detail"])
            self.assertIn(
                "does not define a ZIP serialization",
                deep_item["detail"],
            )
            translations = json.loads(
                (
                    Path(GEO) / "i18n_trans" / "zh-Hant.json"
                ).read_text(encoding="utf-8")
            )

            def translated_strings(value, parent_key=""):
                if isinstance(value, str):
                    if parent_key not in {
                        "app_key",
                        "kind",
                        "match",
                        "primary_resource_url",
                        "url",
                    }:
                        yield value
                elif isinstance(value, list):
                    for child in value:
                        yield from translated_strings(child, parent_key)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        yield from translated_strings(child, key)

            self.assertEqual(
                [],
                [
                    value
                    for value in translated_strings(deep_item)
                    if value not in translations
                ],
            )
            self.assertIn(
                "如何選擇：",
                translations[
                    "How to choose: " + deep_item["query"]
                ],
            )

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (*expected, pages / "data" / "index.html")
            }
            zhuyin_bagit_package.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    @unittest.skipUnless(
        importlib.util.find_spec("bagit"),
        "Library of Congress BagIt validator is installed in CI",
    )
    def test_zhuyin_bagit_package_validates_with_independent_processor(self):
        import bagit

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory) / "site"
            extracted = Path(directory) / "extracted"
            self._seed_zhuyin_bagit_pages(pages)
            zhuyin_bagit_package.build(pages, app_public=False)
            bundle = (
                pages
                / zhuyin_bagit_package.PACKAGE_PATH
                / zhuyin_bagit_package.BUNDLE_FILENAME
            )
            with zipfile.ZipFile(bundle) as archive:
                archive.extractall(extracted)
            bag = bagit.Bag(
                extracted / zhuyin_bagit_package.BAG_ROOT
            )
            bag.validate()
            self.assertTrue(bag.is_valid())

    def _seed_zhuyin_ocfl_pages(self, pages):
        self._seed_zhuyin_bagit_pages(pages)
        zhuyin_bagit_package.build(pages, app_public=False)

    def test_zhuyin_ocfl_object_is_versioned_deterministic_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_ocfl_pages(pages)
            payload, descriptions = zhuyin_ocfl_object.load_payload(pages)
            first = zhuyin_ocfl_object.make_artifacts(
                payload,
                descriptions,
                zhuyin_ocfl_object.INITIAL_DATE,
            )
            second = zhuyin_ocfl_object.make_artifacts(
                payload,
                descriptions,
                zhuyin_ocfl_object.INITIAL_DATE,
            )
            self.assertEqual(
                {
                    key: value["bytes"]
                    for key, value in first.items()
                    if isinstance(value, dict) and "bytes" in value
                },
                {
                    key: value["bytes"]
                    for key, value in second.items()
                    if isinstance(value, dict) and "bytes" in value
                },
            )
            self.assertEqual(first["_object_files"], second["_object_files"])
            zhuyin_ocfl_object.validate_artifacts(first)

            object_files = first["_object_files"]
            inventory_bytes = object_files["inventory.json"]
            inventory = json.loads(inventory_bytes)
            self.assertEqual(10, len(payload))
            self.assertEqual("v1", inventory["head"])
            self.assertEqual(
                zhuyin_ocfl_object.INVENTORY_TYPE,
                inventory["type"],
            )
            self.assertEqual("sha512", inventory["digestAlgorithm"])
            self.assertEqual(
                inventory_bytes,
                object_files["v1/inventory.json"],
            )
            self.assertEqual(
                zhuyin_ocfl_object._sidecar(inventory_bytes),
                object_files["inventory.json.sha512"],
            )
            self.assertEqual(
                object_files["inventory.json.sha512"],
                object_files["v1/inventory.json.sha512"],
            )
            self.assertEqual(
                zhuyin_ocfl_object._state_for_payload(payload),
                inventory["versions"]["v1"]["state"],
            )
            self.assertEqual(
                zhuyin_ocfl_object.INITIAL_TIMESTAMP,
                inventory["versions"]["v1"]["created"],
            )
            created = dt.datetime.fromisoformat(
                inventory["versions"]["v1"]["created"].replace("Z", "+00:00")
            )
            self.assertLessEqual(created, dt.datetime.now(dt.timezone.utc))
            manifest_paths = {
                path
                for paths in inventory["manifest"].values()
                for path in paths
            }
            fixity_paths = {
                path
                for paths in inventory["fixity"]["sha256"].values()
                for path in paths
            }
            self.assertEqual(manifest_paths, fixity_paths)
            self.assertEqual(10, len(manifest_paths))

            changed = dict(payload)
            changed_path = "data/README.md"
            changed[changed_path] += b"\nVersioning regression fixture.\n"
            versioned_files = zhuyin_ocfl_object.make_object_files(
                changed,
                "2026-07-13T00:00:00Z",
                object_files,
            )
            zhuyin_ocfl_object.validate_object_files(
                versioned_files,
                changed,
            )
            versioned = json.loads(versioned_files["inventory.json"])
            self.assertEqual("v2", versioned["head"])
            self.assertEqual({"v1", "v2"}, set(versioned["versions"]))
            for path, content in object_files.items():
                if path not in {"inventory.json", "inventory.json.sha512"}:
                    self.assertEqual(content, versioned_files[path])
            new_content_paths = [
                path for path in versioned_files if path.startswith("v2/content/")
            ]
            self.assertEqual([f"v2/content/{changed_path}"], new_content_paths)
            self.assertEqual(
                "Preservation update after a logical-state change.",
                versioned["versions"]["v2"]["message"],
            )
            versioned_artifacts = zhuyin_ocfl_object.make_artifacts(
                changed,
                descriptions,
                "2026-07-13",
                object_files,
                "2026-07-13T00:00:00Z",
            )
            versioned_page = zhuyin_ocfl_object.render_page(
                "en",
                versioned_artifacts,
                app_public=False,
            )
            self.assertIn(
                "object root and head-version directory",
                versioned_page,
            )
            self.assertIn("└── v2/ (inventory + sidecar + content/)", versioned_page)
            self.assertNotIn("object root and v1 directory", versioned_page)

            renamed = dict(payload)
            renamed["data/PRESERVATION.md"] = renamed.pop("data/README.md")
            renamed_files = zhuyin_ocfl_object.make_object_files(
                renamed,
                "2026-07-13T00:00:00Z",
                object_files,
            )
            zhuyin_ocfl_object.validate_object_files(renamed_files, renamed)
            renamed_inventory = json.loads(renamed_files["inventory.json"])
            self.assertEqual(
                "Preservation update after a logical-state change.",
                renamed_inventory["versions"]["v2"]["message"],
            )
            self.assertFalse(
                any(path.startswith("v2/content/") for path in renamed_files)
            )

            with mock.patch.object(
                zhuyin_ocfl_object,
                "render_readme",
                return_value=b"https://apps.apple.com/app/id6773017109\n",
            ):
                contaminated_payload, contaminated_descriptions = (
                    zhuyin_ocfl_object.load_payload(pages)
                )
            contaminated = zhuyin_ocfl_object.make_artifacts(
                contaminated_payload,
                contaminated_descriptions,
                zhuyin_ocfl_object.INITIAL_DATE,
            )
            with self.assertRaises(ValueError):
                zhuyin_ocfl_object.validate_artifacts(contaminated)

            urls = zhuyin_ocfl_object.build(pages, app_public=False)
            expected = (
                pages
                / zhuyin_ocfl_object.PACKAGE_PATH
                / zhuyin_ocfl_object.BUNDLE_FILENAME,
                pages
                / zhuyin_ocfl_object.PACKAGE_PATH
                / zhuyin_ocfl_object.CHECKSUM_FILENAME,
                pages
                / zhuyin_ocfl_object.PACKAGE_PATH
                / zhuyin_ocfl_object.METADATA_FILENAME,
                pages / zhuyin_ocfl_object.PACKAGE_PATH / "index.html",
                pages
                / "zh-Hant"
                / zhuyin_ocfl_object.PACKAGE_PATH
                / "index.html",
                pages / "sitemap_ocfl.xml",
            )
            self.assertEqual(6, len(urls))
            self.assertTrue(all(path.exists() for path in expected))
            built_metadata = json.loads(expected[2].read_text(encoding="utf-8"))
            self.assertEqual(
                zhuyin_ocfl_object.INITIAL_TIMESTAMP,
                built_metadata["dateModified"],
            )
            for page in expected[3:5]:
                content = page.read_text(encoding="utf-8")
                self.assertIn("OCFL 1.1", content)
                self.assertIn("ocfl-validate.py", content)
                self.assertNotIn("apps.apple.com", content)
                self.assertNotIn('"SoftwareApplication"', content)
            public = zhuyin_ocfl_object.render_page(
                "en",
                first,
                app_public=True,
            )
            self.assertIn(zhuyin_ocfl_object.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)

            with mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(pages / "data"),
            ), mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("OCFL 1.1", content)
                self.assertIn(zhuyin_ocfl_object.BUNDLE_URL, content)
                self.assertIn(zhuyin_ocfl_object.METADATA_URL, content)
            for content in (robots, sitemap_index):
                self.assertIn("sitemap_ocfl.xml", content)

            deep_items = json.loads(
                (
                    Path(GEO)
                    / "deep_items"
                    / "lumibopomofo.json"
                ).read_text(encoding="utf-8")
            )
            deep_item = next(
                item
                for item in deep_items
                if item["kind"] == "ocfl_digital_preservation"
            )
            self.assertEqual(
                zhuyin_ocfl_object.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            self.assertIn("ten portable logical paths", deep_item["detail"])
            self.assertIn(
                "not a ZIP transfer serialization",
                deep_item["detail"],
            )
            translations = json.loads(
                (
                    Path(GEO) / "i18n_trans" / "zh-Hant.json"
                ).read_text(encoding="utf-8")
            )

            def translated_strings(value, parent_key=""):
                if isinstance(value, str):
                    if parent_key not in {
                        "app_key",
                        "kind",
                        "match",
                        "primary_resource_url",
                        "url",
                    }:
                        yield value
                elif isinstance(value, list):
                    for child in value:
                        yield from translated_strings(child, parent_key)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        yield from translated_strings(child, key)

            self.assertEqual(
                [],
                [
                    value
                    for value in translated_strings(deep_item)
                    if value not in translations
                ],
            )
            self.assertIn(
                "How to choose: " + deep_item["query"],
                translations,
            )
            for truncated in (
                "Download the ZIP, checksums-sha256.txt and metadata.jsonld "
                "from the object guide",
                "Run shasum -a 256 -c checksums-sha256.txt before extracting "
                "the transfer wrapper",
                "Extract the ZIP and confirm it creates only the "
                "bopomofo-37-symbols-ocfl object ",
                "Confirm the inventory id and local retention policy before "
                "staging repository in",
            ):
                self.assertIn(truncated, translations)
            self.assertIn(
                deep_item["primary_resource_label"] + " →",
                translations,
            )
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (*expected, pages / "data" / "index.html")
            }
            zhuyin_ocfl_object.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    @unittest.skipUnless(
        importlib.util.find_spec("ocfl"),
        "Independent ocfl-py validator is installed in CI",
    )
    def test_zhuyin_ocfl_object_validates_with_independent_processor(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory) / "site"
            extracted = Path(directory) / "extracted"
            self._seed_zhuyin_ocfl_pages(pages)
            zhuyin_ocfl_object.build(pages, app_public=False)
            bundle = (
                pages
                / zhuyin_ocfl_object.PACKAGE_PATH
                / zhuyin_ocfl_object.BUNDLE_FILENAME
            )
            with zipfile.ZipFile(bundle) as archive:
                archive.extractall(extracted)
            validator = Path(sys.executable).with_name("ocfl-validate.py")
            result = subprocess.run(
                [
                    str(validator),
                    "--very-quiet",
                    str(extracted / zhuyin_ocfl_object.OBJECT_ROOT),
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
            self.assertIn("is VALID", result.stdout + result.stderr)

    def test_zhuyin_iiif_resource_is_complete_safe_and_deterministic(self):
        rows = zhuyin_croissant_dataset.records()
        first = zhuyin_iiif_presentation.make_artifacts(rows)
        second = zhuyin_iiif_presentation.make_artifacts(rows)
        zhuyin_iiif_presentation.validate_artifacts(first)
        self.assertEqual(
            {
                key: item["bytes"]
                for key, item in first.items()
                if isinstance(item, dict) and "bytes" in item
            },
            {
                key: item["bytes"]
                for key, item in second.items()
                if isinstance(item, dict) and "bytes" in item
            },
        )
        self.assertEqual(
            {
                symbol_id: item["bytes"]
                for symbol_id, item in first["images"].items()
            },
            {
                symbol_id: item["bytes"]
                for symbol_id, item in second["images"].items()
            },
        )

        collection = json.loads(first["collection"]["bytes"])
        manifest = json.loads(first["manifest"]["bytes"])
        self.assertEqual(
            zhuyin_iiif_presentation.IIIF_CONTEXT,
            collection["@context"],
        )
        self.assertEqual(
            zhuyin_iiif_presentation.IIIF_CONTEXT,
            manifest["@context"],
        )
        self.assertIsInstance(manifest["@context"], str)
        self.assertEqual("Collection", collection["type"])
        self.assertEqual("Manifest", manifest["type"])
        self.assertEqual("application/json", first["collection"]["media_type"])
        self.assertEqual("application/json", first["manifest"]["media_type"])
        self.assertEqual(
            [
                {
                    "id": zhuyin_iiif_presentation.MANIFEST_URL,
                    "type": "Manifest",
                    "label": collection["items"][0]["label"],
                    "thumbnail": collection["items"][0]["thumbnail"],
                }
            ],
            collection["items"],
        )
        self.assertNotIn("items", collection["items"][0])
        self.assertEqual(
            zhuyin_iiif_presentation.NAV_DATE,
            manifest["navDate"],
        )
        self.assertLessEqual(
            dt.datetime.fromisoformat(
                manifest["navDate"].replace("Z", "+00:00")
            ),
            dt.datetime.now(dt.timezone.utc),
        )
        self.assertEqual(
            zhuyin_iiif_presentation.IIIF_RIGHTS,
            manifest["rights"],
        )
        self.assertEqual(
            [
                zhuyin_croissant_dataset.CSV_URL,
                zhuyin_croissant_dataset.METADATA_URL,
                zhuyin_iiif_presentation.SKOS_JSONLD_URL,
            ],
            [item["id"] for item in manifest["seeAlso"]],
        )
        self.assertEqual(
            zhuyin_iiif_presentation.BUNDLE_URL,
            manifest["rendering"][0]["id"],
        )
        self.assertEqual(37, len(manifest["items"]))

        language_maps = []
        for node in zhuyin_iiif_presentation._walk(manifest):
            if isinstance(node, dict) and set(node) == {"en", "zh-Hant"}:
                language_maps.append(node)
        self.assertTrue(language_maps)
        self.assertTrue(
            all(
                all(
                    isinstance(values, list)
                    and values
                    and all(isinstance(value, str) and value for value in values)
                    for values in language_map.values()
                )
                for language_map in language_maps
            )
        )

        glyph_document, glyphs = zhuyin_iiif_presentation.load_glyph_paths()
        self.assertEqual(
            [row["symbol_id"] for row in rows],
            [glyph["symbol_id"] for glyph in glyph_document["glyphs"]],
        )
        namespace = "{http://www.w3.org/2000/svg}"
        for row, canvas in zip(rows, manifest["items"], strict=True):
            expected_canvas = zhuyin_iiif_presentation.canvas_id(
                row["symbol_id"]
            )
            self.assertEqual(expected_canvas, canvas["id"])
            self.assertEqual("Canvas", canvas["type"])
            self.assertEqual(
                (
                    zhuyin_iiif_presentation.CARD_SIZE,
                    zhuyin_iiif_presentation.CARD_SIZE,
                ),
                (canvas["width"], canvas["height"]),
            )
            self.assertEqual(6, len(canvas["metadata"]))
            page = canvas["items"][0]
            self.assertEqual([f"{expected_canvas}/page"], [page["id"]])
            self.assertEqual("AnnotationPage", page["type"])
            self.assertEqual(1, len(page["items"]))
            annotation = page["items"][0]
            self.assertEqual(f"{expected_canvas}/annotation", annotation["id"])
            self.assertEqual("painting", annotation["motivation"])
            self.assertEqual(expected_canvas, annotation["target"])
            body = annotation["body"]
            self.assertEqual(
                zhuyin_iiif_presentation.image_url(row["symbol_id"]),
                body["id"],
            )
            self.assertEqual("Image", body["type"])
            self.assertEqual("image/svg+xml", body["format"])
            self.assertEqual(
                (
                    zhuyin_iiif_presentation.CARD_SIZE,
                    zhuyin_iiif_presentation.CARD_SIZE,
                ),
                (body["width"], body["height"]),
            )
            self.assertNotIn("service", body)

            svg = first["images"][row["symbol_id"]]["bytes"]
            root = ET.fromstring(svg)
            self.assertEqual("1200", root.get("width"))
            self.assertEqual("1200", root.get("height"))
            title = root.find(f"{namespace}title")
            path = root.find(f"{namespace}path")
            self.assertIsNotNone(title)
            self.assertIn(row["symbol"], title.text)
            self.assertIsNotNone(path)
            self.assertEqual(glyphs[row["symbol_id"]]["path"], path.get("d"))
            self.assertEqual(
                zhuyin_iiif_presentation._glyph_transform(
                    glyphs[row["symbol_id"]]
                ),
                path.get("transform"),
            )
            self.assertTrue(
                all(
                    (element.text or "").isascii()
                    for element in root.findall(f"{namespace}text")
                )
            )

        self.assertFalse(
            any(
                isinstance(node, dict) and "service" in node
                for node in zhuyin_iiif_presentation._walk(manifest)
            )
        )
        machine_bytes = [
            first["collection"]["bytes"],
            first["manifest"]["bytes"],
            *[item["bytes"] for item in first["images"].values()],
            first["bundle"]["bytes"],
            first["checksums"]["bytes"],
            first["metadata"]["bytes"],
        ]
        for raw in machine_bytes:
            for marker in zhuyin_iiif_presentation.FORBIDDEN_MACHINE_MARKERS:
                self.assertNotIn(marker.lower(), raw.lower())

        expected_zip_names = [
            f"{zhuyin_iiif_presentation.ZIP_ROOT}/{relative}"
            for relative, _content in first["_zip_members"]
        ]
        with zipfile.ZipFile(io.BytesIO(first["bundle"]["bytes"])) as archive:
            self.assertEqual(expected_zip_names, archive.namelist())
            for info in archive.infolist():
                self.assertEqual(
                    zhuyin_iiif_presentation.ZIP_TIMESTAMP,
                    info.date_time,
                )
                self.assertEqual(zipfile.ZIP_STORED, info.compress_type)
                self.assertEqual(0o644, (info.external_attr >> 16) & 0o777)
            for relative, content in first["_zip_members"]:
                self.assertEqual(
                    content,
                    archive.read(
                        f"{zhuyin_iiif_presentation.ZIP_ROOT}/{relative}"
                    ),
                )

        checksum_lines = first["checksums"]["bytes"].decode("ascii").splitlines()
        self.assertEqual(40, len(checksum_lines))
        checksum_entries = {
            path: digest
            for digest, path in (
                line.split("  ", 1) for line in checksum_lines
            )
        }
        self.assertNotIn(
            zhuyin_iiif_presentation.CHECKSUM_FILENAME,
            checksum_entries,
        )
        self.assertNotIn(
            zhuyin_iiif_presentation.METADATA_FILENAME,
            checksum_entries,
        )
        for artifact in first["_checksum_members"]:
            self.assertEqual(
                hashlib.sha256(artifact["bytes"]).hexdigest(),
                checksum_entries[artifact["path"]],
            )

        metadata = json.loads(first["metadata"]["bytes"])
        self.assertEqual(37, metadata["numberOfItems"])
        self.assertEqual(
            zhuyin_iiif_presentation.NAV_DATE,
            metadata["dateModified"],
        )
        self.assertEqual(
            zhuyin_iiif_presentation.IIIF_SPEC_URL,
            metadata["conformsTo"],
        )
        distributions = {
            item["contentUrl"]: item for item in metadata["distribution"]
        }
        for key in (
            "collection",
            "manifest",
            "bundle",
            "checksums",
        ):
            artifact = first[key]
            self.assertEqual(
                artifact["sha256"],
                distributions[artifact["url"]]["sha256"],
            )
            self.assertEqual(
                f"{len(artifact['bytes'])} B",
                distributions[artifact["url"]]["contentSize"],
            )
        self.assertEqual(
            set(first["images"]),
            {item["identifier"] for item in metadata["hasPart"]},
        )

        zhuyin_iiif_presentation.validate_reference_pins()
        self.assertEqual(
            "864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f",
            zhuyin_iiif_presentation.FONT_SHA256,
        )
        self.assertEqual(
            "ef9b2a76efe7eaa812502d3315a114255930914a5fa28c414f3584fda550b643",
            zhuyin_iiif_presentation.GLYPH_PATHS_SHA256,
        )
        contaminated = copy.deepcopy(manifest)
        contaminated["summary"]["en"] = [
            "https://apps.apple.com/app/id6773017109"
        ]
        with self.assertRaises(ValueError):
            zhuyin_iiif_presentation.validate_manifest(contaminated, rows)
        unsafe_svg = first["images"][rows[0]["symbol_id"]]["bytes"].replace(
            b"</svg>",
            b"<script>alert(1)</script></svg>",
        )
        with self.assertRaises(ValueError):
            zhuyin_iiif_presentation.validate_svg(
                unsafe_svg,
                rows[0],
                glyphs[rows[0]["symbol_id"]],
            )

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            catalog = {
                "@context": "https://schema.org",
                "@type": "DataCatalog",
                "dataset": [],
            }
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                f"{json.dumps(catalog)}</script><main>"
                '<p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            urls = zhuyin_iiif_presentation.build(
                pages,
                app_public=False,
            )
            resource = pages / zhuyin_iiif_presentation.RESOURCE_PATH
            expected = [
                data
                / f"{zhuyin_iiif_presentation.LANDING_SLUG}.html",
                pages
                / "zh-Hant"
                / "data"
                / f"{zhuyin_iiif_presentation.LANDING_SLUG}.html",
                resource / zhuyin_iiif_presentation.COLLECTION_FILENAME,
                resource / zhuyin_iiif_presentation.MANIFEST_FILENAME,
                *[
                    resource / "images" / f"{row['symbol_id']}.svg"
                    for row in rows
                ],
                resource / zhuyin_iiif_presentation.BUNDLE_FILENAME,
                resource / zhuyin_iiif_presentation.CHECKSUM_FILENAME,
                resource / zhuyin_iiif_presentation.METADATA_FILENAME,
                pages / "sitemap_iiif.xml",
            ]
            self.assertTrue(all(path.exists() for path in expected))
            self.assertEqual(len(expected), len(urls))
            for landing in expected[:2]:
                page = landing.read_text(encoding="utf-8")
                self.assertIn("IIIF Presentation API 3", page)
                self.assertIn(zhuyin_iiif_presentation.MANIFEST_URL, page)
                self.assertIn(zhuyin_iiif_presentation.BUNDLE_URL, page)
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn('"SoftwareApplication"', page)
            public = zhuyin_iiif_presentation.render_page(
                "en",
                first,
                app_public=True,
            )
            self.assertIn(zhuyin_iiif_presentation.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            self.assertGreater(
                public.index('id="optional-app"'),
                public.index(zhuyin_iiif_presentation.COPY["en"]["sources"]),
            )
            sitemap = (pages / "sitemap_iiif.xml").read_text(
                encoding="utf-8"
            )
            for url in urls[:-1]:
                self.assertIn(url, sitemap)
            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                index.count(
                    f'href="{zhuyin_iiif_presentation.LANDING_URL}"'
                ),
            )
            schema_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                index,
                re.DOTALL,
            )
            data_catalog = json.loads(schema_match.group(1))
            self.assertEqual(
                1,
                sum(
                    item.get("url") == zhuyin_iiif_presentation.LANDING_URL
                    for item in data_catalog["dataset"]
                ),
            )
            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (*expected, data / "index.html")
            }
            zhuyin_iiif_presentation.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    @unittest.skipUnless(
        shutil.which("iiif-validator"),
        "Pinned IIIF validator is installed in an isolated environment",
    )
    def test_zhuyin_iiif_validates_with_official_cli(self):
        artifacts = zhuyin_iiif_presentation.make_artifacts()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for key in ("collection", "manifest"):
                path = root / artifacts[key]["filename"]
                path.write_bytes(artifacts[key]["bytes"])
                paths.append(path)
            for path in paths:
                result = subprocess.run(
                    [
                        shutil.which("iiif-validator"),
                        "validate",
                        "--version",
                        "3.0",
                        str(path),
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
                report = json.loads(result.stdout)
                self.assertEqual(
                    1,
                    report["okay"],
                    json.dumps(report, ensure_ascii=False, indent=2),
                )

    def test_zhuyin_ro_crate_is_complete_deterministic_and_discoverable(self):
        from rdflib import Graph

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            tools = pages / "tools"
            data.mkdir(parents=True)
            tools.mkdir()
            with mock.patch.object(
                gen_data_hub, "PAGES", str(pages)
            ), mock.patch.object(
                gen_data_hub, "DATA", str(data)
            ):
                gen_data_hub.build_zhuyin_page()
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"DataCatalog",'
                '"dataset":[]}</script><main><a class="item" href="'
                f'{zhuyin_skos_vocabulary.SOURCE_PAGE}">'
                '<h2>Source dataset</h2></a>'
                '<p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            zhuyin_skos_vocabulary.build(pages, app_public=False)
            zhuyin_croissant_dataset.build(pages, app_public=False)
            zhuyin_csvw_metadata.build(pages, app_public=False)

            first = zhuyin_ro_crate.make_artifacts(
                pages, zhuyin_ro_crate.INITIAL_DATE
            )
            second = zhuyin_ro_crate.make_artifacts(
                pages, zhuyin_ro_crate.INITIAL_DATE
            )
            self.assertEqual(first, second)
            zhuyin_ro_crate.validate_artifacts(
                first, zhuyin_ro_crate.INITIAL_DATE
            )

            context_bytes = zhuyin_ro_crate.CONTEXT_PATH.read_bytes()
            self.assertEqual(196942, len(context_bytes))
            self.assertEqual(
                zhuyin_ro_crate.CONTEXT_SHA256,
                hashlib.sha256(context_bytes).hexdigest(),
            )
            sources = json.loads(
                zhuyin_ro_crate.SOURCES_PATH.read_text(encoding="utf-8")
            )
            self.assertEqual(
                "1.3.0",
                sources["context"]["version"],
            )
            self.assertEqual(
                zhuyin_ro_crate.SPEC_COMMIT,
                sources["specification"]["commit"],
            )

            metadata = json.loads(first[zhuyin_ro_crate.METADATA_FILENAME])
            self.assertEqual(zhuyin_ro_crate.CONTEXT, metadata["@context"])
            entities = {entity["@id"]: entity for entity in metadata["@graph"]}
            self.assertEqual(
                {
                    "@id": zhuyin_ro_crate.METADATA_FILENAME,
                    "@type": "CreativeWork",
                    "about": {"@id": zhuyin_ro_crate.ROOT_ID},
                    "conformsTo": {"@id": zhuyin_ro_crate.PROFILE},
                },
                entities[zhuyin_ro_crate.METADATA_FILENAME],
            )
            root = entities[zhuyin_ro_crate.ROOT_ID]
            self.assertIn("Dataset", root["@type"])
            self.assertEqual(
                {"@id": zhuyin_ro_crate.MOE_PUBLISHER_ID},
                entities[zhuyin_ro_crate.MOE_REFERENCE_ID]["publisher"],
            )
            self.assertEqual(
                "Organization",
                entities[zhuyin_ro_crate.MOE_PUBLISHER_ID]["@type"],
            )
            self.assertEqual(
                {
                    zhuyin_ro_crate.README_FILENAME,
                    zhuyin_ro_crate.LICENSE_FILENAME,
                    *(spec.crate_path for spec in zhuyin_ro_crate.PAYLOAD_SPECS),
                },
                {part["@id"] for part in root["hasPart"]},
            )
            self.assertEqual(7, len(root["hasPart"]))
            for part in root["hasPart"]:
                relative = part["@id"]
                self.assertFalse(Path(relative).is_absolute())
                self.assertNotIn("..", Path(relative).parts)
                entity = entities[relative]
                self.assertEqual(
                    str(len(first[relative])),
                    entity["contentSize"],
                )
                self.assertEqual(
                    hashlib.sha256(first[relative]).hexdigest(),
                    entity["sha256"],
                )

            csv_rows = list(
                csv.DictReader(
                    io.StringIO(
                        first["data/zhuyin-bopomofo-ml-dataset.csv"].decode(
                            "utf-8"
                        )
                    )
                )
            )
            jsonl_rows = [
                json.loads(line)
                for line in first[
                    "data/zhuyin-bopomofo-ml-dataset.jsonl"
                ]
                .decode("utf-8")
                .splitlines()
            ]
            self.assertEqual(37, len(csv_rows))
            self.assertEqual(37, len(jsonl_rows))
            self.assertEqual(
                [row["symbol_id"] for row in csv_rows],
                [row["symbol_id"] for row in jsonl_rows],
            )

            local_metadata = copy.deepcopy(metadata)
            local_metadata["@context"] = json.loads(context_bytes)["@context"]
            graph = Graph().parse(
                data=json.dumps(local_metadata, ensure_ascii=False),
                format="json-ld",
                publicID=zhuyin_ro_crate.ROOT_ID,
            )
            self.assertGreaterEqual(len(graph), 80)

            expected_members = [
                zhuyin_ro_crate.METADATA_FILENAME,
                zhuyin_ro_crate.PREVIEW_FILENAME,
                zhuyin_ro_crate.README_FILENAME,
                zhuyin_ro_crate.LICENSE_FILENAME,
                *(
                    spec.crate_path
                    for spec in zhuyin_ro_crate.PAYLOAD_SPECS
                ),
                zhuyin_ro_crate.CHECKSUM_FILENAME,
            ]
            with zipfile.ZipFile(
                io.BytesIO(first[zhuyin_ro_crate.BUNDLE_FILENAME])
            ) as archive:
                self.assertEqual(expected_members, archive.namelist())
                for info in archive.infolist():
                    self.assertEqual(
                        zhuyin_ro_crate.ZIP_TIMESTAMP,
                        info.date_time,
                    )
                    self.assertEqual(
                        zipfile.ZIP_DEFLATED,
                        info.compress_type,
                    )
                    self.assertEqual(0o100644, info.external_attr >> 16)
                    self.assertEqual(first[info.filename], archive.read(info))
            checksum_entries = {
                path: digest
                for digest, path in (
                    line.split("  ", 1)
                    for line in first[zhuyin_ro_crate.CHECKSUM_FILENAME]
                    .decode("ascii")
                    .splitlines()
                )
            }
            self.assertEqual(set(expected_members[:-1]), set(checksum_entries))
            for path, digest in checksum_entries.items():
                self.assertEqual(
                    hashlib.sha256(first[path]).hexdigest(),
                    digest,
                )
            for path in expected_members:
                raw = first[path]
                for forbidden in (
                    b"apps.apple.com",
                    zhuyin_ro_crate.APP_ID.encode("ascii"),
                    zhuyin_ro_crate.APP_NAME.encode("utf-8"),
                    b"SoftwareApplication",
                ):
                    self.assertNotIn(forbidden.lower(), raw.lower())
            self.assertNotIn(
                b"<script",
                first[zhuyin_ro_crate.PREVIEW_FILENAME].lower(),
            )

            urls = zhuyin_ro_crate.build(pages, app_public=False)
            self.assertEqual(14, len(urls))
            package = pages / zhuyin_ro_crate.PACKAGE_PATH
            expected_paths = [
                *(package / path for path in first),
                package / "index.html",
                pages
                / "zh-Hant"
                / zhuyin_ro_crate.PACKAGE_PATH
                / "index.html",
                pages / zhuyin_ro_crate.SITEMAP_PATH,
                data / "index.html",
            ]
            self.assertTrue(all(path.is_file() for path in expected_paths))
            for landing in expected_paths[-4:-2]:
                content = landing.read_text(encoding="utf-8")
                self.assertIn("RO-Crate 1.3", content)
                self.assertIn(zhuyin_ro_crate.BUNDLE_URL, content)
                self.assertNotIn("apps.apple.com", content)
                self.assertNotIn('"SoftwareApplication"', content)
                for part in root["hasPart"]:
                    self.assertIn(
                        f'href="{zhuyin_ro_crate.PACKAGE_URL}{part["@id"]}"',
                        content,
                    )
            public = zhuyin_ro_crate.render_page(
                "en",
                first,
                zhuyin_ro_crate.INITIAL_DATE,
                app_public=True,
            )
            self.assertIn(zhuyin_ro_crate.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            self.assertGreater(
                public.index(zhuyin_ro_crate.COPY["en"]["app_title"]),
                public.index(zhuyin_ro_crate.COPY["en"]["sources"]),
            )

            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count(zhuyin_ro_crate.CARD_START))
            self.assertIn(zhuyin_ro_crate.PACKAGE_URL, index)
            schema_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                index,
                re.DOTALL,
            )
            catalog = json.loads(schema_match.group(1))
            crate_entries = [
                item
                for item in catalog["dataset"]
                if item.get("url") == zhuyin_ro_crate.PACKAGE_URL
            ]
            self.assertEqual(1, len(crate_entries))
            self.assertEqual(4, len(crate_entries[0]["distribution"]))
            sitemap = (pages / zhuyin_ro_crate.SITEMAP_PATH).read_text(
                encoding="utf-8"
            )
            for relative in expected_members:
                self.assertIn(
                    f"{zhuyin_ro_crate.PACKAGE_URL}{relative}",
                    sitemap,
                )

            with mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ), mock.patch.object(
                gen_llms, "DATA_DIR", str(data)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("Bopomofo RO-Crate 1.3 research object", content)
                self.assertIn(zhuyin_ro_crate.METADATA_URL, content)
            for content in (robots, sitemap_index):
                self.assertIn(
                    zhuyin_ro_crate.SITEMAP_PATH.as_posix(),
                    content,
                )

            deep_item = next(
                item
                for item in answer_deep.DEEP_ITEMS
                if item.get("kind") == "ro_crate_research_object"
                and item.get("app_key") == "lumibopomofo"
            )
            self.assertEqual(
                zhuyin_ro_crate.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            self.assertNotIn("DOI", deep_item["lead"])
            self.assertNotIn("certified", deep_item["lead"].lower())

            mtimes = {
                path: path.stat().st_mtime_ns for path in expected_paths
            }
            zhuyin_ro_crate.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in expected_paths},
            )

    def test_zhuyin_mets_premis_package_is_valid_deterministic_and_discoverable(
        self,
    ):
        from lxml import etree

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            tools = pages / "tools"
            data.mkdir(parents=True)
            tools.mkdir()
            with mock.patch.object(
                gen_data_hub, "PAGES", str(pages)
            ), mock.patch.object(
                gen_data_hub, "DATA", str(data)
            ):
                gen_data_hub.build_zhuyin_page()
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"DataCatalog",'
                '"dataset":[]}</script><main><a class="item" href="'
                f'{zhuyin_skos_vocabulary.SOURCE_PAGE}">'
                '<h2>Source dataset</h2></a>'
                '<p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            (tools / "index.html").write_text(
                '<main><section class="wrap grid"></section></main>',
                encoding="utf-8",
            )
            zhuyin_skos_vocabulary.build(pages, app_public=False)
            zhuyin_croissant_dataset.build(pages, app_public=False)
            zhuyin_csvw_metadata.build(pages, app_public=False)

            package_module = zhuyin_mets_premis_package
            generated_at = "2026-07-11T19:41:27Z"
            first = package_module.make_artifacts(
                pages, generated_at
            )
            second = package_module.make_artifacts(
                pages, generated_at
            )
            self.assertEqual(first, second)
            package_module.validate_artifacts(
                first, generated_at
            )

            sources = json.loads(
                package_module.SOURCES_PATH.read_text(encoding="utf-8")
            )
            for key, path, size, digest, commit in (
                (
                    "mets",
                    package_module.METS_SCHEMA_PATH,
                    88391,
                    package_module.METS_SCHEMA_SHA256,
                    package_module.METS_COMMIT,
                ),
                (
                    "premis",
                    package_module.PREMIS_SCHEMA_PATH,
                    52845,
                    package_module.PREMIS_SCHEMA_SHA256,
                    package_module.PREMIS_COMMIT,
                ),
            ):
                content = path.read_bytes()
                self.assertEqual(size, len(content))
                self.assertEqual(digest, hashlib.sha256(content).hexdigest())
                self.assertEqual(commit, sources[key]["commit"])
                self.assertEqual(size, sources[key]["bytes"])
                self.assertEqual(digest, sources[key]["sha256"])
            self.assertEqual("CC0-1.0", sources["mets"]["license"])
            self.assertNotIn("license", sources["premis"])
            self.assertIn("no SPDX", sources["premis"]["license_note"])

            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            mets = etree.fromstring(first[package_module.METS_FILENAME], parser)
            premis = etree.fromstring(
                first[package_module.PREMIS_FILENAME], parser
            )
            namespaces = {
                "mets": package_module.METS_NS,
                "premis": package_module.PREMIS_NS,
            }
            self.assertEqual(
                f"{{{package_module.METS_NS}}}mets",
                mets.tag,
            )
            self.assertNotIn(
                "xlink",
                first[package_module.METS_FILENAME].decode("utf-8").lower(),
            )
            mets_header = mets.find("mets:metsHdr", namespaces)
            self.assertEqual(generated_at, mets_header.get("CREATEDATE"))
            self.assertEqual(generated_at, mets_header.get("LASTMODDATE"))
            md_ref = mets.find("mets:mdSec/mets:md/mets:mdRef", namespaces)
            self.assertEqual(package_module.PREMIS_FILENAME, md_ref.get("LOCREF"))
            self.assertEqual("PREMIS", md_ref.get("MDTYPE"))
            self.assertEqual("3.0", md_ref.get("MDTYPEVERSION"))
            self.assertEqual(
                hashlib.sha256(
                    first[package_module.PREMIS_FILENAME]
                ).hexdigest(),
                md_ref.get("CHECKSUM"),
            )

            files = mets.findall(
                "mets:fileSec/mets:fileGrp/mets:file",
                namespaces,
            )
            self.assertEqual(7, len(files))
            self.assertEqual(
                {"DATA", "DOCUMENTATION"},
                {
                    group.get("USE")
                    for group in mets.findall(
                        "mets:fileSec/mets:fileGrp",
                        namespaces,
                    )
                },
            )
            file_ids = set()
            for element, spec in zip(files, package_module.PAYLOAD_SPECS):
                content = first[spec.package_path]
                location = element.find("mets:FLocat", namespaces)
                file_ids.add(element.get("ID"))
                self.assertEqual(spec.package_path, location.get("LOCREF"))
                self.assertEqual(spec.media_type, element.get("MIMETYPE"))
                self.assertEqual(str(len(content)), element.get("SIZE"))
                self.assertEqual(
                    hashlib.sha256(content).hexdigest(),
                    element.get("CHECKSUM"),
                )
            jsonl_file = next(
                element
                for element in files
                if element.find("mets:FLocat", namespaces).get(
                    "LOCREF"
                ).endswith(".jsonl")
            )
            self.assertEqual("text/plain", jsonl_file.get("MIMETYPE"))
            self.assertEqual(
                file_ids,
                {
                    pointer.get("FILEID")
                    for pointer in mets.findall(
                        ".//mets:structMap//mets:fptr",
                        namespaces,
                    )
                },
            )

            objects = premis.findall("premis:object", namespaces)
            events = premis.findall("premis:event", namespaces)
            agents = premis.findall("premis:agent", namespaces)
            rights = premis.findall("premis:rights", namespaces)
            self.assertEqual((7, 1, 2, 1), tuple(
                len(group) for group in (objects, events, agents, rights)
            ))
            object_identifiers = {
                (
                    obj.findtext(
                        "premis:objectIdentifier/"
                        "premis:objectIdentifierType",
                        namespaces=namespaces,
                    ),
                    obj.findtext(
                        "premis:objectIdentifier/"
                        "premis:objectIdentifierValue",
                        namespaces=namespaces,
                    ),
                )
                for obj in objects
            }
            for obj, spec in zip(objects, package_module.PAYLOAD_SPECS):
                content = first[spec.package_path]
                self.assertEqual(
                    spec.package_path,
                    obj.findtext("premis:originalName", namespaces=namespaces),
                )
                self.assertEqual(
                    str(len(content)),
                    obj.findtext(
                        "premis:objectCharacteristics/premis:size",
                        namespaces=namespaces,
                    ),
                )
                self.assertEqual(
                    hashlib.sha256(content).hexdigest(),
                    obj.findtext(
                        "premis:objectCharacteristics/premis:fixity/"
                        "premis:messageDigest",
                        namespaces=namespaces,
                    ),
                )
            event = events[0]
            self.assertEqual(
                generated_at,
                event.findtext(
                    "premis:eventDateTime",
                    namespaces=namespaces,
                ),
            )
            self.assertEqual(
                "metadata creation",
                event.findtext("premis:eventType", namespaces=namespaces),
            )
            self.assertEqual(
                "success",
                event.findtext(
                    "premis:eventOutcomeInformation/premis:eventOutcome",
                    namespaces=namespaces,
                ),
            )
            self.assertEqual(
                object_identifiers,
                {
                    (
                        link.findtext(
                            "premis:linkingObjectIdentifierType",
                            namespaces=namespaces,
                        ),
                        link.findtext(
                            "premis:linkingObjectIdentifierValue",
                            namespaces=namespaces,
                        ),
                    )
                    for link in event.findall(
                        "premis:linkingObjectIdentifier",
                        namespaces,
                    )
                },
            )
            statement = rights[0].find(
                "premis:rightsStatement",
                namespaces,
            )
            self.assertEqual(
                "license",
                statement.findtext(
                    "premis:rightsBasis",
                    namespaces=namespaces,
                ),
            )
            self.assertEqual(
                {"replicate", "migrate", "disseminate", "modify"},
                {
                    grant.findtext("premis:act", namespaces=namespaces)
                    for grant in statement.findall(
                        "premis:rightsGranted",
                        namespaces,
                    )
                },
            )
            self.assertEqual(
                object_identifiers,
                {
                    (
                        link.findtext(
                            "premis:linkingObjectIdentifierType",
                            namespaces=namespaces,
                        ),
                        link.findtext(
                            "premis:linkingObjectIdentifierValue",
                            namespaces=namespaces,
                        ),
                    )
                    for link in statement.findall(
                        "premis:linkingObjectIdentifier",
                        namespaces,
                    )
                },
            )

            expected_members = [
                package_module.METS_FILENAME,
                package_module.PREMIS_FILENAME,
                package_module.README_FILENAME,
                package_module.LICENSE_FILENAME,
                *(
                    spec.package_path
                    for spec in package_module.PAYLOAD_SPECS
                    if spec.group == "DATA"
                ),
                package_module.CHECKSUM_FILENAME,
            ]
            with zipfile.ZipFile(
                io.BytesIO(first[package_module.BUNDLE_FILENAME])
            ) as archive:
                self.assertEqual(expected_members, archive.namelist())
                for info in archive.infolist():
                    self.assertEqual(package_module.ZIP_TIMESTAMP, info.date_time)
                    self.assertEqual(zipfile.ZIP_DEFLATED, info.compress_type)
                    self.assertEqual(0o100644, info.external_attr >> 16)
                    self.assertEqual(first[info.filename], archive.read(info))
            checksum_entries = {
                path: digest
                for digest, path in (
                    line.split("  ", 1)
                    for line in first[package_module.CHECKSUM_FILENAME]
                    .decode("ascii")
                    .splitlines()
                )
            }
            self.assertEqual(set(expected_members[:-1]), set(checksum_entries))
            for path, digest in checksum_entries.items():
                self.assertEqual(
                    hashlib.sha256(first[path]).hexdigest(),
                    digest,
                )
            for path in expected_members:
                for forbidden in (
                    b"apps.apple.com",
                    package_module.APP_ID.encode("ascii"),
                    package_module.APP_NAME.encode("utf-8"),
                    b"SoftwareApplication",
                ):
                    self.assertNotIn(forbidden.lower(), first[path].lower())

            generated_time = dt.datetime(
                2026,
                7,
                11,
                19,
                41,
                27,
                tzinfo=dt.timezone.utc,
            )
            with mock.patch.object(
                package_module,
                "_utc_now",
                return_value=generated_time,
            ):
                urls = package_module.build(pages, app_public=False)
            self.assertEqual(14, len(urls))
            package = pages / package_module.PACKAGE_PATH
            expected_paths = [
                *(package / path for path in first),
                package / package_module.METADATA_FILENAME,
                package / "index.html",
                pages
                / "zh-Hant"
                / package_module.PACKAGE_PATH
                / "index.html",
                pages / package_module.SITEMAP_PATH,
                data / "index.html",
            ]
            self.assertTrue(all(path.is_file() for path in expected_paths))
            for landing in expected_paths[-4:-2]:
                content = landing.read_text(encoding="utf-8")
                self.assertIn("METS 2.0", content)
                self.assertIn("PREMIS 3.0", content)
                self.assertIn(package_module.BUNDLE_URL, content)
                self.assertNotIn("apps.apple.com", content)
                self.assertNotIn('"SoftwareApplication"', content)
            public = package_module.render_page(
                "en",
                first,
                generated_at,
                package_module.INITIAL_DATE,
                app_public=True,
            )
            self.assertIn(package_module.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            self.assertGreater(
                public.index(package_module.COPY["en"]["app_title"]),
                public.index(package_module.COPY["en"]["sources"]),
            )

            metadata = json.loads(
                (
                    package / package_module.METADATA_FILENAME
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(4, len(metadata["distribution"]))
            self.assertEqual(7, len(metadata["hasPart"]))
            self.assertEqual(generated_at, metadata["dateModified"])
            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count(package_module.CARD_START))
            self.assertIn(package_module.PACKAGE_URL, index)
            sitemap = (pages / package_module.SITEMAP_PATH).read_text(
                encoding="utf-8"
            )
            for relative in (
                *expected_members,
                package_module.METADATA_FILENAME,
                package_module.BUNDLE_FILENAME,
            ):
                self.assertIn(
                    f"{package_module.PACKAGE_URL}{relative}",
                    sitemap,
                )

            with mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ), mock.patch.object(
                gen_llms, "DATA_DIR", str(data)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn(
                    "Bopomofo METS 2.0 + PREMIS 3.0 preservation package",
                    content,
                )
                self.assertIn(package_module.METS_URL, content)
                self.assertIn(package_module.PREMIS_URL, content)
            for content in (robots, sitemap_index):
                self.assertIn(package_module.SITEMAP_PATH.as_posix(), content)

            deep_item = next(
                item
                for item in answer_deep.DEEP_ITEMS
                if item.get("kind") == "mets_premis_preservation_package"
                and item.get("app_key") == "lumibopomofo"
            )
            self.assertEqual(
                package_module.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            self.assertNotIn("certified", deep_item["lead"].lower())
            answer_slug = (
                "where-can-a-digital-repository-download-a-mets-2-0-and-"
                "premis-3-0-package-for-bopomofo-data.html"
            )
            for answer, package_url in (
                (
                    Path(GEO) / "pages" / "answers" / answer_slug,
                    package_module.PACKAGE_URL,
                ),
                (
                    Path(GEO) / "pages" / "zh-Hant" / "answers" / answer_slug,
                    package_module.ZH_PACKAGE_URL,
                ),
            ):
                content = answer.read_text(encoding="utf-8")
                self.assertIn("METS 2.0", content)
                self.assertIn("PREMIS 3.0", content)
                self.assertIn(package_url, content)
            feed = (Path(GEO) / "pages" / "feed.xml").read_text(
                encoding="utf-8"
            )
            self.assertIn(answer_slug, feed)
            self.assertIn(
                "sixteen verified Bopomofo datasets and 80 exact "
                "distributions",
                feed,
            )

            mtimes = {
                path: path.stat().st_mtime_ns for path in expected_paths
            }
            package_module.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in expected_paths},
            )

    def _seed_zhuyin_ore_pages(self, pages):
        data = pages / "data"
        tools = pages / "tools"
        data.mkdir(parents=True)
        tools.mkdir()
        with mock.patch.object(
            gen_data_hub, "PAGES", str(pages)
        ), mock.patch.object(
            gen_data_hub, "DATA", str(data)
        ):
            gen_data_hub.build_zhuyin_page()
        (data / "index.html").write_text(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"DataCatalog",'
            '"dataset":[]}</script><main><a class="item" href="'
            f'{zhuyin_skos_vocabulary.SOURCE_PAGE}">'
            '<h2>Source dataset</h2></a>'
            '<p class="foot">Footer</p></main>',
            encoding="utf-8",
        )
        (tools / "index.html").write_text(
            '<main><section class="wrap grid"></section></main>',
            encoding="utf-8",
        )
        zhuyin_skos_vocabulary.build(pages, app_public=False)
        zhuyin_croissant_dataset.build(pages, app_public=False)
        zhuyin_frictionless_package.build(pages, app_public=False)
        zhuyin_csvw_metadata.build(pages, app_public=False)
        zhuyin_static_api.build(pages, app_public=False)
        zhuyin_ldes_event_stream.build(pages, app_public=False)

    def test_zhuyin_ldes_event_stream_is_complete_immutable_and_discoverable(
        self,
    ):
        from rdflib import Graph, Literal, RDF, URIRef

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_ore_pages(pages)
            package_module = zhuyin_ldes_event_stream
            package = pages / package_module.PACKAGE_PATH
            modified = package_module._prior_timestamp(
                package / package_module.METADATA_FILENAME
            )
            first = package_module.make_artifacts(pages, modified)
            second = package_module.make_artifacts(pages, modified)
            self.assertEqual(first, second)
            package_module.validate_artifacts(pages, first, modified)
            self.assertEqual(
                [
                    package_module.STREAM_JSONLD_FILENAME,
                    package_module.STREAM_TURTLE_FILENAME,
                    *(node.filename for node in package_module.NODE_SPECS),
                    package_module.SHAPE_FILENAME,
                    package_module.README_FILENAME,
                    package_module.LICENSE_FILENAME,
                    package_module.CHECKSUM_FILENAME,
                    package_module.BUNDLE_FILENAME,
                ],
                list(first),
            )

            stream = URIRef(package_module.STREAM_URL)
            entry_json = Graph().parse(
                data=first[package_module.STREAM_JSONLD_FILENAME],
                format="json-ld",
            )
            entry_ttl = Graph().parse(
                data=first[package_module.STREAM_TURTLE_FILENAME],
                format="turtle",
            )
            self.assertIn(
                (
                    stream,
                    RDF.type,
                    URIRef(package_module.LDES_NS + "EventStream"),
                ),
                entry_json,
            )
            self.assertEqual(
                {stream},
                set(
                    entry_json.objects(
                        stream,
                        URIRef(package_module.TREE_NS + "view"),
                    )
                ),
            )
            self.assertEqual(
                6,
                len(
                    set(
                        entry_json.objects(
                            stream,
                            URIRef(package_module.TREE_NS + "relation"),
                        )
                    )
                ),
            )
            self.assertEqual(
                {stream},
                set(
                    entry_ttl.objects(
                        URIRef(package_module.STREAM_TURTLE_URL),
                        URIRef(package_module.TREE_NS + "view"),
                    )
                ),
            )

            members = set()
            concepts = set()
            for node in package_module.NODE_SPECS:
                graph = Graph().parse(data=first[node.filename], format="json-ld")
                node_uri = URIRef(node.url)
                self.assertIn(
                    (
                        node_uri,
                        URIRef(package_module.LDES_NS + "immutable"),
                        Literal(True),
                    ),
                    graph,
                )
                node_members = set(
                    graph.objects(
                        stream,
                        URIRef(package_module.TREE_NS + "member"),
                    )
                )
                self.assertEqual(node.stop - node.start, len(node_members))
                self.assertFalse(members & node_members)
                members |= node_members
                for member in node_members:
                    created = list(
                        graph.objects(
                            member,
                            URIRef(package_module.DCTERMS_NS + "created"),
                        )
                    )
                    version_of = list(
                        graph.objects(
                            member,
                            URIRef(package_module.DCTERMS_NS + "isVersionOf"),
                        )
                    )
                    self.assertEqual(1, len(created))
                    self.assertEqual(
                        URIRef(package_module.XSD_NS + "dateTime"),
                        created[0].datatype,
                    )
                    self.assertEqual(1, len(version_of))
                    concepts.add(version_of[0])
            self.assertEqual(37, len(members))
            self.assertEqual(37, len(concepts))

            with zipfile.ZipFile(
                io.BytesIO(first[package_module.BUNDLE_FILENAME])
            ) as archive:
                self.assertEqual(
                    sorted(first.keys() - {package_module.BUNDLE_FILENAME}),
                    archive.namelist(),
                )
                for info in archive.infolist():
                    self.assertEqual(package_module.ZIP_TIMESTAMP, info.date_time)
                    self.assertEqual(zipfile.ZIP_DEFLATED, info.compress_type)
                    self.assertEqual(0o100644, info.external_attr >> 16)
                    self.assertEqual(first[info.filename], archive.read(info.filename))
            for content in first.values():
                for forbidden in (
                    b"apps.apple.com",
                    package_module.APP_ID.encode("ascii"),
                    package_module.APP_NAME.encode("utf-8"),
                    b"SoftwareApplication",
                ):
                    self.assertNotIn(forbidden.lower(), content.lower())

            urls = package_module.build(pages, app_public=False)
            self.assertEqual(12, len(urls))
            metadata = json.loads(
                (package / package_module.METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(37, metadata["numberOfItems"])
            self.assertEqual(8, len(metadata["distribution"]))
            self.assertEqual(
                package_module.ORE_AGGREGATION_URI,
                metadata["isPartOf"],
            )
            expected_paths = [
                *(package / filename for filename in first),
                package / package_module.METADATA_FILENAME,
                package / "index.html",
                pages
                / "zh-Hant"
                / package_module.PACKAGE_PATH
                / "index.html",
                pages / package_module.SITEMAP_PATH,
                pages / "data" / "index.html",
            ]
            self.assertTrue(all(path.is_file() for path in expected_paths))
            for landing in expected_paths[-4:-2]:
                content = landing.read_text(encoding="utf-8")
                self.assertIn("LDES 1.0", content)
                self.assertIn(package_module.STREAM_URL, content)
                self.assertNotIn("apps.apple.com", content)
                self.assertNotIn('"SoftwareApplication"', content)

            with mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ), mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(pages / "data"),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn(
                    "Bopomofo LDES 1.0 + TREE event stream",
                    content,
                )
                self.assertIn(package_module.STREAM_URL, content)
            for content in (robots, sitemap_index):
                self.assertIn(package_module.SITEMAP_PATH.as_posix(), content)

            deep_item = next(
                item
                for item in answer_deep.DEEP_ITEMS
                if item.get("kind") == "ldes_tree_event_stream"
                and item.get("app_key") == "lumibopomofo"
            )
            self.assertEqual(
                package_module.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            translations = json.loads(
                (
                    Path(GEO) / "i18n_trans" / "zh-Hant.json"
                ).read_text(encoding="utf-8")
            )

            def translated_strings(value, parent_key=""):
                if isinstance(value, str):
                    if parent_key not in {
                        "app_key",
                        "kind",
                        "match",
                        "primary_resource_url",
                        "url",
                    }:
                        yield value
                elif isinstance(value, list):
                    for child in value:
                        yield from translated_strings(child, parent_key)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        yield from translated_strings(child, key)

            self.assertEqual(
                [],
                [
                    value
                    for value in translated_strings(deep_item)
                    if value not in translations
                ],
            )
            self.assertIn(
                "How to choose: " + deep_item["query"],
                translations,
            )
            self.assertIn(
                deep_item["primary_resource_label"] + " →",
                translations,
            )
            answer_slug = (
                "where-can-a-linked-data-client-replicate-bopomofo-as-an-"
                "ldes-1-0-and-tree-event-stream.html"
            )
            english_answer = (
                Path(GEO) / "pages" / "answers" / answer_slug
            ).read_text(encoding="utf-8")
            localized_answer = (
                Path(GEO) / "pages" / "zh-Hant" / "answers" / answer_slug
            ).read_text(encoding="utf-8")
            for content, package_url in (
                (english_answer, package_module.PACKAGE_URL),
                (localized_answer, package_module.ZH_PACKAGE_URL),
            ):
                self.assertIn("LDES 1.0", content)
                self.assertIn(package_url, content)
            answer_strings, _, _ = aeo_answers_i18n.extract_strings(
                english_answer
            )
            self.assertEqual(
                [],
                [value for value in answer_strings if value not in translations],
            )
            self.assertIn(
                translations[deep_item["page_title"]],
                localized_answer,
            )
            self.assertNotIn(deep_item["page_title"], localized_answer)
            feed = (Path(GEO) / "pages" / "feed.xml").read_text(
                encoding="utf-8"
            )
            self.assertIn(answer_slug, feed)

    def test_zhuyin_ore_resource_map_is_complete_deterministic_and_discoverable(
        self,
    ):
        from rdflib import Graph, Literal, RDF, URIRef

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_ore_pages(pages)
            data = pages / "data"
            package_module = zhuyin_ore_resource_map
            modified = "2026-07-11T20:47:13Z"
            first = package_module.make_artifacts(pages, modified)
            second = package_module.make_artifacts(pages, modified)
            self.assertEqual(first, second)
            package_module.validate_artifacts(pages, first, modified)
            self.assertEqual(
                [
                    package_module.RDFXML_FILENAME,
                    package_module.TURTLE_FILENAME,
                    package_module.JSONLD_FILENAME,
                    package_module.README_FILENAME,
                    package_module.LICENSE_FILENAME,
                    package_module.CHECKSUM_FILENAME,
                    package_module.BUNDLE_FILENAME,
                ],
                list(first),
            )
            self.assertEqual(
                f"{package_module.RDFXML_URL}#aggregation",
                package_module.AGGREGATION_URI,
            )
            self.assertEqual(3, len(set(package_module.RESOURCE_MAP_URLS)))

            sources = package_module._source_entries(pages)
            expected_members = {
                URIRef(package_module._source_url(spec))
                for spec in package_module.SOURCE_SPECS
            }
            graph_cores = []
            for filename, map_url, _, _, format_name in package_module.MAP_SPECS:
                graph = Graph().parse(data=first[filename], format=format_name)
                resource_map = URIRef(map_url)
                aggregation = URIRef(package_module.AGGREGATION_URI)
                self.assertEqual(165, len(graph))
                self.assertIn(
                    (resource_map, RDF.type, package_module.ORE.ResourceMap),
                    graph,
                )
                self.assertEqual(
                    {aggregation},
                    set(
                        graph.objects(
                            resource_map,
                            package_module.ORE.describes,
                        )
                    ),
                )
                self.assertEqual(
                    {resource_map},
                    set(
                        graph.subjects(
                            package_module.ORE.describes,
                            aggregation,
                        )
                    ),
                )
                self.assertEqual(
                    expected_members,
                    set(
                        graph.objects(
                            aggregation,
                            package_module.ORE.aggregates,
                        )
                    ),
                )
                self.assertEqual(
                    {
                        URIRef(url)
                        for url in package_module.RESOURCE_MAP_URLS
                    },
                    set(
                        graph.objects(
                            aggregation,
                            package_module.ORE.isDescribedBy,
                        )
                    ),
                )
                self.assertEqual(
                    {
                        Literal(
                            f"{package_module.INITIAL_DATE}T00:00:00Z",
                            datatype=package_module.XSD.dateTime,
                        )
                    },
                    set(
                        graph.objects(
                            resource_map,
                            package_module.DCTERMS.created,
                        )
                    ),
                )
                self.assertEqual(
                    {
                        Literal(
                            modified,
                            datatype=package_module.XSD.dateTime,
                        )
                    },
                    set(
                        graph.objects(
                            resource_map,
                            package_module.DCTERMS.modified,
                        )
                    ),
                )
                for spec, content in sources.items():
                    resource = URIRef(package_module._source_url(spec))
                    checksum = URIRef(package_module._checksum_uri(spec))
                    self.assertEqual(
                        {aggregation},
                        set(
                            graph.objects(
                                resource,
                                package_module.ORE.isAggregatedBy,
                            )
                        ),
                    )
                    self.assertEqual(
                        {Literal(spec.media_type)},
                        set(
                            graph.objects(
                                resource,
                                package_module.DCTERMS["format"],
                            )
                        ),
                    )
                    self.assertEqual(
                        {
                            Literal(
                                str(len(content)),
                                datatype=package_module.XSD.decimal,
                            )
                        },
                        set(
                            graph.objects(
                                resource,
                                package_module.DCAT.byteSize,
                            )
                        ),
                    )
                    self.assertEqual(
                        {
                            Literal(
                                hashlib.sha256(content).hexdigest(),
                                datatype=package_module.XSD.hexBinary,
                            )
                        },
                        set(
                            graph.objects(
                                checksum,
                                package_module.SPDX.checksumValue,
                            )
                        ),
                    )
                graph_cores.append(
                    {
                        triple
                        for triple in graph
                        if triple[0] != resource_map
                    }
                )
            self.assertTrue(
                all(core == graph_cores[0] for core in graph_cores[1:])
            )

            checksum_rows = (
                first[package_module.CHECKSUM_FILENAME]
                .decode("utf-8")
                .splitlines()
            )
            self.assertEqual(5, len(checksum_rows))
            with zipfile.ZipFile(
                io.BytesIO(first[package_module.BUNDLE_FILENAME])
            ) as archive:
                expected_zip_members = [
                    package_module.RDFXML_FILENAME,
                    package_module.TURTLE_FILENAME,
                    package_module.JSONLD_FILENAME,
                    package_module.README_FILENAME,
                    package_module.LICENSE_FILENAME,
                    package_module.CHECKSUM_FILENAME,
                ]
                self.assertEqual(expected_zip_members, archive.namelist())
                for info in archive.infolist():
                    self.assertEqual(package_module.ZIP_TIMESTAMP, info.date_time)
                    self.assertEqual(zipfile.ZIP_DEFLATED, info.compress_type)
                    self.assertEqual(0o100644, info.external_attr >> 16)
                    self.assertEqual(first[info.filename], archive.read(info))
            for content in first.values():
                for forbidden in (
                    b"apps.apple.com",
                    package_module.APP_ID.encode("ascii"),
                    package_module.APP_NAME.encode("utf-8"),
                    b"SoftwareApplication",
                ):
                    self.assertNotIn(forbidden.lower(), content.lower())

            tampered_spec = package_module.SOURCE_SPECS[0]
            tampered_path = pages / tampered_spec.path
            original = tampered_path.read_bytes()
            tampered_path.write_bytes(original + b"\n")
            with self.assertRaisesRegex(
                ValueError,
                "byte size mismatch|SHA-256 mismatch",
            ):
                package_module.validate_artifacts(pages, first, modified)
            tampered_path.write_bytes(original)

            with mock.patch.object(
                package_module,
                "_new_timestamp",
                return_value=modified,
            ):
                urls = package_module.build(pages, app_public=False)
            self.assertEqual(12, len(urls))
            package = pages / package_module.PACKAGE_PATH
            expected_paths = [
                *(package / filename for filename in first),
                package / package_module.METADATA_FILENAME,
                package / "index.html",
                pages
                / "zh-Hant"
                / package_module.PACKAGE_PATH
                / "index.html",
                pages / package_module.SITEMAP_PATH,
                data / "index.html",
            ]
            self.assertTrue(all(path.is_file() for path in expected_paths))
            metadata = json.loads(
                (
                    package / package_module.METADATA_FILENAME
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(package_module.AGGREGATION_URI, metadata["@id"])
            self.assertEqual(7, len(metadata["distribution"]))
            self.assertEqual(16, len(metadata["hasPart"]))
            self.assertEqual(modified, metadata["dateModified"])
            for landing in expected_paths[-4:-2]:
                content = landing.read_text(encoding="utf-8")
                self.assertIn("OAI-ORE 1.0", content)
                self.assertIn(package_module.AGGREGATION_URI, content)
                self.assertIn('rel="resourcemap"', content)
                self.assertNotIn("apps.apple.com", content)
                self.assertNotIn('"SoftwareApplication"', content)
            public = package_module.render_page(
                "en",
                first,
                sources,
                modified,
                package_module.INITIAL_DATE,
                app_public=True,
            )
            self.assertIn(package_module.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            self.assertGreater(
                public.index(package_module.COPY["en"]["app_title"]),
                public.index(package_module.COPY["en"]["sources"]),
            )
            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count(package_module.CARD_START))
            self.assertIn(package_module.PACKAGE_URL, index)
            sitemap = (pages / package_module.SITEMAP_PATH).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("#aggregation</loc>", sitemap)
            for filename in (
                *first,
                package_module.METADATA_FILENAME,
            ):
                self.assertIn(
                    f"{package_module.PACKAGE_URL}{filename}",
                    sitemap,
                )

            with mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ), mock.patch.object(
                gen_llms, "DATA_DIR", str(data)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn(
                    "Bopomofo OAI-ORE 1.0 compound-object Resource Map",
                    content,
                )
                self.assertIn(package_module.RDFXML_URL, content)
                self.assertIn(package_module.AGGREGATION_URI, content)
            for content in (robots, sitemap_index):
                self.assertIn(package_module.SITEMAP_PATH.as_posix(), content)

            deep_item = next(
                item
                for item in answer_deep.DEEP_ITEMS
                if item.get("kind") == "oai_ore_resource_map"
                and item.get("app_key") == "lumibopomofo"
            )
            self.assertEqual(
                package_module.PACKAGE_URL,
                deep_item["primary_resource_url"],
            )
            translations = json.loads(
                (
                    Path(GEO) / "i18n_trans" / "zh-Hant.json"
                ).read_text(encoding="utf-8")
            )

            def translated_strings(value, parent_key=""):
                if isinstance(value, str):
                    if parent_key not in {
                        "app_key",
                        "kind",
                        "match",
                        "primary_resource_url",
                        "url",
                    }:
                        yield value
                elif isinstance(value, list):
                    for child in value:
                        yield from translated_strings(child, parent_key)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        yield from translated_strings(child, key)

            self.assertEqual(
                [],
                [
                    value
                    for value in translated_strings(deep_item)
                    if value not in translations
                ],
            )
            self.assertIn(
                "How to choose: " + deep_item["query"],
                translations,
            )
            self.assertIn(
                deep_item["primary_resource_label"] + " →",
                translations,
            )
            answer_slug = (
                "where-can-a-repository-harvest-an-oai-ore-resource-map-for-"
                "bopomofo-data.html"
            )
            for answer, package_url in (
                (
                    Path(GEO) / "pages" / "answers" / answer_slug,
                    package_module.PACKAGE_URL,
                ),
                (
                    Path(GEO)
                    / "pages"
                    / "zh-Hant"
                    / "answers"
                    / answer_slug,
                    package_module.ZH_PACKAGE_URL,
                ),
            ):
                content = answer.read_text(encoding="utf-8")
                self.assertIn("OAI-ORE", content)
                self.assertIn(package_url, content)
                self.assertIn("#aggregation", content)
            localized_answer = (
                Path(GEO) / "pages" / "zh-Hant" / "answers" / answer_slug
            ).read_text(encoding="utf-8")
            self.assertIn("採集注音資料的 OAI-ORE Resource Map", localized_answer)
            self.assertNotIn(
                "Harvest an OAI-ORE Resource Map for Bopomofo Data",
                localized_answer,
            )
            feed = (Path(GEO) / "pages" / "feed.xml").read_text(
                encoding="utf-8"
            )
            self.assertIn(answer_slug, feed)
            self.assertIn(
                "sixteen verified Bopomofo datasets and 80 exact "
                "distributions",
                feed,
            )

            mtimes = {
                path: path.stat().st_mtime_ns for path in expected_paths
            }
            package_module.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in expected_paths},
            )

    def test_zhuyin_lms_question_bank_is_complete_and_portable(self):
        rows = zhuyin_croissant_dataset.records()
        first = zhuyin_lms_assessment_bank.make_core_artifacts(rows)
        second = zhuyin_lms_assessment_bank.make_core_artifacts(rows)
        self.assertEqual(
            {key: item["bytes"] for key, item in first.items()},
            {key: item["bytes"] for key, item in second.items()},
        )

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            catalog = {
                "@context": "https://schema.org",
                "@type": "DataCatalog",
                "dataset": [],
            }
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                + json.dumps(catalog)
                + '</script><main><p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            urls = zhuyin_lms_assessment_bank.build(
                pages, app_public=False
            )
            package = pages / zhuyin_lms_assessment_bank.PACKAGE_PATH
            expected = [
                pages / zhuyin_lms_assessment_bank.LANDING_PATH,
                pages / zhuyin_lms_assessment_bank.ZH_LANDING_PATH,
                pages / zhuyin_lms_assessment_bank.SITEMAP_PATH,
                data / "index.html",
                *[
                    package / artifact["filename"]
                    for artifact in {
                        **first,
                        "metadata": {
                            "filename": (
                                zhuyin_lms_assessment_bank.METADATA_FILENAME
                            )
                        },
                    }.values()
                ],
            ]
            self.assertEqual(9, len(urls))
            self.assertTrue(all(path.exists() for path in expected))

            artifacts = {
                key: {
                    **artifact,
                    "bytes": (package / artifact["filename"]).read_bytes(),
                }
                for key, artifact in {
                    **first,
                    "metadata": {
                        "filename": (
                            zhuyin_lms_assessment_bank.METADATA_FILENAME
                        ),
                        "label": "Schema.org JSON-LD metadata",
                        "media_type": "application/ld+json",
                        "locale": "en",
                        "url": zhuyin_lms_assessment_bank.METADATA_URL,
                    },
                }.items()
            }
            zhuyin_lms_assessment_bank.validate_artifacts(rows, artifacts)
            with zipfile.ZipFile(
                io.BytesIO(first["qti_en"]["bytes"])
            ) as archive:
                manifest = archive.read("imsmanifest.xml").decode("utf-8")
            self.assertIn(
                "qtiv2p1_imscpv1p2_v1p0.xsd",
                manifest,
            )
            self.assertIn(
                "<schema>QTIv2.1 Package</schema>",
                manifest,
            )
            self.assertIn(
                "<schemaversion>"
                + zhuyin_lms_assessment_bank.QTI_PACKAGE_SCHEMA_VERSION
                + "</schemaversion>",
                manifest,
            )
            metadata = json.loads(
                (package / "metadata.jsonld").read_text(encoding="utf-8")
            )
            self.assertEqual(5, len(metadata["distribution"]))
            for distribution in metadata["distribution"]:
                local = package / Path(distribution["contentUrl"]).name
                self.assertEqual(
                    distribution["sha256"],
                    hashlib.sha256(local.read_bytes()).hexdigest(),
                )

            english = (
                pages / zhuyin_lms_assessment_bank.LANDING_PATH
            ).read_text(encoding="utf-8")
            traditional = (
                pages / zhuyin_lms_assessment_bank.ZH_LANDING_PATH
            ).read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn('rel="resourcesync"', page)
                self.assertIn('hreflang="en"', page)
                self.assertIn('hreflang="zh-Hant"', page)
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn('"SoftwareApplication"', page)
            public = zhuyin_lms_assessment_bank.render_page(
                "zh-Hant",
                rows,
                artifacts,
                zhuyin_lms_assessment_bank.INITIAL_DATE,
                app_public=True,
            )
            self.assertIn(zhuyin_lms_assessment_bank.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            self.assertNotIn('"offers"', public)

            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1, index.count(zhuyin_lms_assessment_bank.CARD_START)
            )
            self.assertIn(
                zhuyin_lms_assessment_bank.LANDING_URL, index
            )
            with mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ), mock.patch.object(
                gen_llms, "DATA_DIR", str(data)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for generated in (llms, full):
                self.assertIn("Bopomofo LMS question bank", generated)
                self.assertIn(
                    zhuyin_lms_assessment_bank.METADATA_URL, generated
                )
            self.assertIn("sitemap_lms.xml", robots)
            self.assertIn("sitemap_lms.xml", sitemap_index)

            mtimes = {
                path: path.stat().st_mtime_ns for path in expected
            }
            zhuyin_lms_assessment_bank.build(
                pages, app_public=False
            )
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in expected},
            )

    def test_zhuyin_epub_opds_is_complete_accessible_and_portable(self):
        rows = zhuyin_croissant_dataset.records()
        first = zhuyin_epub_opds.make_epub_artifacts(rows)
        second = zhuyin_epub_opds.make_epub_artifacts(rows)
        self.assertEqual(
            {locale: item["bytes"] for locale, item in first.items()},
            {locale: item["bytes"] for locale, item in second.items()},
        )

        for locale, artifact in first.items():
            zhuyin_epub_opds.validate_epub(
                rows, locale, artifact["bytes"]
            )
            with zipfile.ZipFile(io.BytesIO(artifact["bytes"])) as archive:
                infos = archive.infolist()
                self.assertEqual("mimetype", infos[0].filename)
                self.assertEqual(zipfile.ZIP_STORED, infos[0].compress_type)
                self.assertEqual(
                    zhuyin_epub_opds.EPUB_MEDIA_TYPE.encode("ascii"),
                    archive.read("mimetype"),
                )
                self.assertEqual(
                    (1980, 1, 1, 0, 0, 0),
                    infos[0].date_time,
                )
                package = archive.read("EPUB/package.opf").decode("utf-8")
                self.assertIn(
                    "<meta property=\"schema:accessMode\">textual</meta>",
                    package,
                )
                self.assertIn(
                    "noFlashingHazard",
                    package,
                )
                self.assertNotIn("certifiedBy", package)

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            catalog = {
                "@context": "https://schema.org",
                "@type": "DataCatalog",
                "dataset": [],
            }
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                + json.dumps(catalog)
                + '</script><main><p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            urls = zhuyin_epub_opds.build(
                pages,
                app_public=False,
            )
            self.assertEqual(10, len(urls))

            manifests = {}
            for locale, artifact in first.items():
                epub_path = (
                    pages
                    / zhuyin_epub_opds.PACKAGE_PATH
                    / artifact["filename"]
                )
                self.assertEqual(artifact["bytes"], epub_path.read_bytes())
                directory_path = pages / zhuyin_epub_opds.web_path(locale)
                manifest_path = directory_path / "manifest.json"
                manifest_bytes = manifest_path.read_bytes()
                manifest = json.loads(manifest_bytes)
                web_files = {
                    path.name: path.read_bytes()
                    for path in directory_path.iterdir()
                    if path.name != "manifest.json"
                }
                zhuyin_epub_opds.validate_web_manifest(
                    locale,
                    manifest,
                    artifact,
                    web_files,
                )
                self.assertEqual(
                    len(zhuyin_epub_opds.CONTENT_ORDER),
                    len(manifest["readingOrder"]),
                )
                epub_link = next(
                    link
                    for link in manifest["links"]
                    if link.get("type")
                    == zhuyin_epub_opds.EPUB_MEDIA_TYPE
                )
                self.assertEqual(
                    len(artifact["bytes"]),
                    epub_link["size"],
                )
                self.assertNotIn("length", epub_link)
                manifests[locale] = {
                    "bytes": manifest_bytes,
                    "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                    "url": zhuyin_epub_opds.manifest_url(locale),
                }

            opds2 = json.loads(
                (pages / zhuyin_epub_opds.OPDS2_PATH).read_text(
                    encoding="utf-8"
                )
            )
            opds1 = (pages / zhuyin_epub_opds.OPDS1_PATH).read_text(
                encoding="utf-8"
            )
            zhuyin_epub_opds.validate_catalogs(opds2, opds1, first)
            self.assertEqual(2, len(opds2["publications"]))
            for publication in opds2["publications"]:
                acquisition = next(
                    link
                    for link in publication["links"]
                    if link.get("rel")
                    == zhuyin_epub_opds.OPEN_ACCESS_REL
                )
                self.assertIn("size", acquisition)
                self.assertNotIn("length", acquisition)

            metadata = json.loads(
                (
                    pages
                    / zhuyin_epub_opds.PACKAGE_PATH
                    / zhuyin_epub_opds.METADATA_FILENAME
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(4, len(metadata["encoding"]))
            self.assertEqual(
                zhuyin_epub_opds.EPUB_SPEC,
                metadata["conformsTo"],
            )
            self.assertEqual(
                {
                    zhuyin_epub_opds.WEBPUB_SPEC,
                    zhuyin_epub_opds.OPDS2_SPEC,
                    zhuyin_epub_opds.OPDS1_SPEC,
                },
                set(metadata["citation"]),
            )
            local_by_url = {
                artifact["url"]: (
                    pages
                    / zhuyin_epub_opds.PACKAGE_PATH
                    / artifact["filename"]
                )
                for artifact in first.values()
            }
            local_by_url.update(
                {
                    zhuyin_epub_opds.manifest_url(locale): (
                        pages
                        / zhuyin_epub_opds.web_path(locale)
                        / "manifest.json"
                    )
                    for locale in zhuyin_epub_opds.COPY
                }
            )
            for encoding in metadata["encoding"]:
                local = local_by_url[encoding["contentUrl"]]
                self.assertEqual(
                    encoding["sha256"],
                    hashlib.sha256(local.read_bytes()).hexdigest(),
                )
                self.assertEqual(
                    int(encoding["contentSize"].split()[0]),
                    local.stat().st_size,
                )

            english = (
                pages / zhuyin_epub_opds.LANDING_PATH
            ).read_text(encoding="utf-8")
            traditional = (
                pages / zhuyin_epub_opds.ZH_LANDING_PATH
            ).read_text(encoding="utf-8")
            for page in (english, traditional):
                self.assertIn('rel="resourcesync"', page)
                self.assertIn(zhuyin_epub_opds.OPDS2_URL, page)
                self.assertIn(zhuyin_epub_opds.OPDS1_URL, page)
                self.assertIn("HTTP Content-Type", page)
                self.assertIn('manifest.json" download', page)
                self.assertIn(
                    f'href="{zhuyin_epub_opds.OPDS2_URL}" download',
                    page,
                )
                self.assertNotIn("apps.apple.com", page)
                self.assertNotIn('"SoftwareApplication"', page)
            public = zhuyin_epub_opds.render_page(
                "zh-Hant",
                first,
                manifests,
                zhuyin_epub_opds.INITIAL_TIMESTAMP,
                app_public=True,
                page_modified="2026-07-12",
            )
            self.assertIn(zhuyin_epub_opds.APP_ID, public)
            self.assertIn('"SoftwareApplication"', public)
            self.assertNotIn('"offers"', public)
            schema = next(
                json.loads(raw)
                for raw in re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    public,
                    re.DOTALL,
                )
                if '"@graph"' in raw
            )
            web_page = next(
                item
                for item in schema["@graph"]
                if item.get("@type") == "WebPage"
            )
            book = next(
                item
                for item in schema["@graph"]
                if "Book" in item.get("@type", [])
            )
            self.assertEqual("2026-07-12", web_page["dateModified"])
            self.assertEqual(
                zhuyin_epub_opds.INITIAL_TIMESTAMP,
                book["dateModified"],
            )

            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1, index.count(zhuyin_epub_opds.CARD_START)
            )
            self.assertIn(zhuyin_epub_opds.LANDING_URL, index)
            with mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ), mock.patch.object(
                gen_llms, "DATA_DIR", str(data)
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for generated in (llms, full):
                self.assertIn("Bopomofo EPUB", generated)
                self.assertIn(zhuyin_epub_opds.OPDS2_URL, generated)
            self.assertIn("sitemap_epub.xml", robots)
            self.assertIn("sitemap_epub.xml", sitemap_index)

            generated_files = [
                path for path in pages.rglob("*") if path.is_file()
            ]
            mtimes = {
                path: path.stat().st_mtime_ns for path in generated_files
            }
            zhuyin_epub_opds.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in generated_files},
            )

            changed_copy = copy.deepcopy(zhuyin_epub_opds.COPY)
            changed_copy["en"]["description"] += " Revised."
            with mock.patch.object(
                zhuyin_epub_opds,
                "COPY",
                changed_copy,
            ), mock.patch.object(
                zhuyin_epub_opds,
                "TODAY",
                "2026-07-11",
            ), mock.patch.object(
                zhuyin_epub_opds,
                "NOW",
                "2026-07-11T12:34:56Z",
            ):
                zhuyin_epub_opds.build(pages, app_public=False)
                expected_date = "2026-07-11"
                expected_timestamp = "2026-07-11T12:34:56Z"
                for locale, filename in (
                    (
                        "en",
                        "bopomofo-37-symbol-reference-en.epub",
                    ),
                    (
                        "zh-Hant",
                        "bopomofo-37-symbol-reference-zh-hant.epub",
                    ),
                ):
                    epub_path = (
                        pages
                        / zhuyin_epub_opds.PACKAGE_PATH
                        / filename
                    )
                    with zipfile.ZipFile(epub_path) as archive:
                        package = archive.read(
                            "EPUB/package.opf"
                        ).decode("utf-8")
                        title = archive.read(
                            "EPUB/title.xhtml"
                        ).decode("utf-8")
                    self.assertIn(expected_timestamp, package)
                    self.assertIn(
                        f'content="{expected_timestamp}"',
                        title,
                    )
                    manifest = json.loads(
                        (
                            pages
                            / zhuyin_epub_opds.web_path(locale)
                            / "manifest.json"
                        ).read_text(encoding="utf-8")
                    )
                    self.assertEqual(
                        expected_timestamp,
                        manifest["metadata"]["modified"],
                    )
                opds = json.loads(
                    (pages / zhuyin_epub_opds.OPDS2_PATH).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(
                    expected_timestamp,
                    opds["metadata"]["modified"],
                )
                metadata = json.loads(
                    (
                        pages
                        / zhuyin_epub_opds.PACKAGE_PATH
                        / zhuyin_epub_opds.METADATA_FILENAME
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    expected_timestamp,
                    metadata["dateModified"],
                )
                changed_files = [
                    path for path in pages.rglob("*") if path.is_file()
                ]
                changed_mtimes = {
                    path: path.stat().st_mtime_ns
                    for path in changed_files
                }
                zhuyin_epub_opds.build(pages, app_public=False)
                self.assertEqual(
                    changed_mtimes,
                    {
                        path: path.stat().st_mtime_ns
                        for path in changed_files
                    },
                )

    def test_lms_question_bank_answer_is_resource_first_and_bounded(self):
        question = (
            "Where can I download a free Bopomofo QTI question bank "
            "for Canvas or Moodle?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(
            question, "lumibopomofo", content
        )
        self.assertEqual(
            zhuyin_lms_assessment_bank.LANDING_URL,
            content["primary_resource_url"],
        )
        self.assertIn("QTI 2.1", page)
        self.assertIn("Moodle XML", page)
        self.assertIn("staging course", page)
        self.assertIn("not a standardized test", page)
        self.assertLess(
            page.index("Download the free Bopomofo LMS question bank"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )
        mapping = json.loads(
            (
                Path(GEO)
                / "i18n_trans"
                / "zh-Hant.json"
            ).read_text(encoding="utf-8")
        )
        strings, _, _ = aeo_answers_i18n.extract_strings(page)
        self.assertEqual(
            [], [string for string in strings if string not in mapping]
        )
        localized = aeo_answers_i18n.render_localized(
            page,
            "zh-Hant",
            aeo_answers.slugify(question),
            {string: mapping[string] for string in strings},
        )
        self.assertIn(
            "<title>免費注音 QTI 2.1 與 Moodle XML 題庫</title>",
            localized,
        )
        self.assertIn(
            zhuyin_lms_assessment_bank.ZH_LANDING_URL,
            localized,
        )
        self.assertNotIn(
            "The open CC BY 4.0 bank provides",
            localized,
        )

    def test_epub_answer_is_resource_first_bilingual_and_bounded(self):
        question = (
            "Where can I download a free Bopomofo EPUB for e-readers?"
        )
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "lumibopomofo"),
            question,
            "lumibopomofo",
        )
        page = aeo_answers.render_page(
            question, "lumibopomofo", content
        )
        self.assertEqual(
            zhuyin_epub_opds.LANDING_URL,
            content["primary_resource_url"],
        )
        for text in (
            "EPUB 3.3",
            "OPDS 2.0",
            "OPDS 1.2",
            "all 37 Bopomofo symbols",
            "no scripts, images, tracking",
            "not audio instruction",
        ):
            self.assertIn(text, page)
        self.assertLess(
            page.index("Download the free Bopomofo EPUB"),
            page.index("Get Lumi Bopomofo on the App Store"),
        )

        mapping = json.loads(
            (
                Path(GEO)
                / "i18n_trans"
                / "zh-Hant.json"
            ).read_text(encoding="utf-8")
        )
        strings, _, _ = aeo_answers_i18n.extract_strings(page)
        self.assertEqual(
            [], [string for string in strings if string not in mapping]
        )
        localized = aeo_answers_i18n.render_localized(
            page,
            "zh-Hant",
            aeo_answers.slugify(question),
            {string: mapping[string] for string in strings},
        )
        self.assertIn(
            "<title>免費無障礙注音 EPUB 3.3 與 OPDS 目錄</title>",
            localized,
        )
        self.assertIn(zhuyin_epub_opds.ZH_LANDING_URL, localized)
        self.assertIn("下載免費注音 EPUB", localized)
        self.assertIn("不具診斷用途", localized)
        self.assertNotIn(
            "Each CC BY 4.0 EPUB 3.3 edition",
            localized,
        )

    def test_answer_index_preserves_existing_locale_alternates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            answers = root / "pages" / "answers"
            answers.mkdir(parents=True)
            (answers / "sample.html").write_text(
                '<h1>Sample answer</h1><script type="application/ld+json">'
                '{"@type":"SoftwareApplication","name":"Sample App"}'
                "</script>",
                encoding="utf-8",
            )
            for locale in ("ja", "zh-Hant"):
                localized = root / "pages" / locale / "answers" / "index.html"
                localized.parent.mkdir(parents=True)
                localized.write_text("localized", encoding="utf-8")
            with mock.patch.object(
                aeo_answers,
                "ROOT",
                root,
            ), mock.patch.object(
                aeo_answers,
                "ANSWERS_DIR",
                answers,
            ):
                aeo_answers.regenerate_index()
            index = (answers / "index.html").read_text(encoding="utf-8")
            self.assertIn('hreflang="en"', index)
            self.assertIn('hreflang="ja"', index)
            self.assertIn('hreflang="zh-Hant"', index)
            self.assertIn('hreflang="x-default"', index)
            self.assertNotIn('hreflang="de-DE"', index)

    def test_zhuyin_library_catalog_is_complete_verifiable_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            catalog = {
                "@context": "https://schema.org",
                "@type": "DataCatalog",
                "dataset": [],
            }
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                + json.dumps(catalog)
                + '</script><main><p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            zhuyin_epub_opds.build(pages, app_public=False)
            urls = zhuyin_library_catalog.build(
                pages,
                app_public=False,
            )
            self.assertEqual(9, len(urls))

            package_dir = pages / zhuyin_library_catalog.PACKAGE_PATH
            expected = tuple(
                package_dir / filename
                for filename in zhuyin_library_catalog.DOWNLOAD_FILENAMES
            ) + (
                pages / zhuyin_library_catalog.LANDING_PATH,
                pages / zhuyin_library_catalog.ZH_LANDING_PATH,
                pages / zhuyin_library_catalog.SITEMAP_PATH,
            )
            self.assertTrue(all(path.exists() for path in expected))

            raw = b"\n".join(
                (package_dir / filename).read_bytes()
                for filename in zhuyin_library_catalog.DOWNLOAD_FILENAMES
            )
            for forbidden in (
                b"apps.apple.com",
                zhuyin_library_catalog.APP_ID.encode("ascii"),
                zhuyin_library_catalog.APP_NAME.encode("utf-8"),
                b"SoftwareApplication",
            ):
                self.assertNotIn(forbidden, raw)

            marc = ET.parse(package_dir / zhuyin_library_catalog.MARC_FILENAME)
            records = marc.getroot().findall(
                f"{{{zhuyin_library_catalog.MARC_NS}}}record"
            )
            self.assertEqual(2, len(records))
            source_urls = set()
            for record in records:
                fields = record.findall(
                    f"{{{zhuyin_library_catalog.MARC_NS}}}datafield"
                )
                tags = {field.attrib["tag"] for field in fields}
                self.assertTrue(
                    {
                        "041",
                        "245",
                        "264",
                        "300",
                        "336",
                        "337",
                        "338",
                        "500",
                        "506",
                        "520",
                        "538",
                        "540",
                        "546",
                        "650",
                        "655",
                        "856",
                    }.issubset(tags)
                )
                leader = record.findtext(
                    f"{{{zhuyin_library_catalog.MARC_NS}}}leader"
                )
                self.assertEqual(24, len(leader))
                fixed = next(
                    field.text
                    for field in record.findall(
                        f"{{{zhuyin_library_catalog.MARC_NS}}}controlfield"
                    )
                    if field.attrib["tag"] == "008"
                )
                self.assertEqual(40, len(fixed))
                for field in fields:
                    if field.attrib["tag"] != "856":
                        continue
                    for subfield in field:
                        if (
                            subfield.attrib["code"] == "u"
                            and "packages/zhuyin-bopomofo-epub"
                            in (subfield.text or "")
                        ):
                            source_urls.add(subfield.text)
            self.assertEqual(
                {
                    zhuyin_epub_opds.epub_url("en"),
                    zhuyin_epub_opds.epub_url("zh-Hant"),
                },
                source_urls,
            )

            mods = ET.parse(package_dir / zhuyin_library_catalog.MODS_FILENAME)
            mods_records = mods.getroot().findall(
                f"{{{zhuyin_library_catalog.MODS_NS}}}mods"
            )
            self.assertEqual(2, len(mods_records))
            self.assertEqual(
                {"3.8"},
                {record.attrib["version"] for record in mods_records},
            )
            for record in mods_records:
                self.assertIsNotNone(
                    record.find(
                        f"{{{zhuyin_library_catalog.MODS_NS}}}titleInfo/"
                        f"{{{zhuyin_library_catalog.MODS_NS}}}title"
                    )
                )
                self.assertEqual(
                    2,
                    len(
                        record.findall(
                            f"{{{zhuyin_library_catalog.MODS_NS}}}identifier"
                        )
                    ),
                )

            metadata = json.loads(
                (package_dir / zhuyin_library_catalog.METADATA_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(5, len(metadata["distribution"]))
            self.assertEqual(
                {
                    zhuyin_library_catalog.MARC_SCHEMA,
                    zhuyin_library_catalog.MODS_SCHEMA,
                    zhuyin_library_catalog.BIBFRAME_VOCABULARY,
                    zhuyin_library_catalog.BIBFRAME_MODEL,
                },
                set(metadata["conformsTo"]),
            )
            for distribution in metadata["distribution"]:
                filename = Path(
                    distribution["contentUrl"].split("?", 1)[0]
                ).name
                local = package_dir / filename
                self.assertEqual(
                    local.stat().st_size,
                    int(distribution["contentSize"].split()[0]),
                )
                self.assertEqual(
                    hashlib.sha256(local.read_bytes()).hexdigest(),
                    distribution["sha256"],
                )

            with zipfile.ZipFile(
                package_dir / zhuyin_library_catalog.BUNDLE_FILENAME
            ) as archive:
                self.assertEqual(
                    {
                        *zhuyin_library_catalog.PRIMARY_FILENAMES,
                        "README.txt",
                        "checksums.sha256",
                    },
                    set(archive.namelist()),
                )
                for filename in zhuyin_library_catalog.PRIMARY_FILENAMES:
                    self.assertEqual(
                        (package_dir / filename).read_bytes(),
                        archive.read(filename),
                    )

            english = (
                pages / zhuyin_library_catalog.LANDING_PATH
            ).read_text(encoding="utf-8")
            traditional = (
                pages / zhuyin_library_catalog.ZH_LANDING_PATH
            ).read_text(encoding="utf-8")
            for landing in (english, traditional):
                self.assertIn("MARCXML", landing)
                self.assertIn("MODS 3.8", landing)
                self.assertIn("BIBFRAME 2.0", landing)
                self.assertIn("Content-Type", landing)
                self.assertNotIn("apps.apple.com", landing)
                self.assertNotIn('"SoftwareApplication"', landing)

            package_info = {
                filename: zhuyin_library_catalog._artifact(
                    filename,
                    (package_dir / filename).read_bytes(),
                )
                for filename in zhuyin_library_catalog.DOWNLOAD_FILENAMES
            }
            public = zhuyin_library_catalog.render_landing(
                "en",
                package_info,
                metadata["dateModified"],
                zhuyin_library_catalog.INITIAL_DATE,
                True,
            )
            self.assertIn("apps.apple.com", public)
            self.assertIn('"SoftwareApplication"', public)

            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                index.count(zhuyin_library_catalog.CARD_START),
            )
            self.assertIn(zhuyin_library_catalog.LANDING_URL, index)
            sitemap = (
                pages / zhuyin_library_catalog.SITEMAP_PATH
            ).read_text(encoding="utf-8")
            for filename in zhuyin_library_catalog.DOWNLOAD_FILENAMES:
                self.assertIn(f"{zhuyin_library_catalog.PACKAGE_URL}/{filename}", sitemap)

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (*expected, data / "index.html")
            }
            zhuyin_library_catalog.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {
                    path: path.stat().st_mtime_ns
                    for path in (*expected, data / "index.html")
                },
            )

    @unittest.skipUnless(
        importlib.util.find_spec("lxml")
        and importlib.util.find_spec("rdflib"),
        "XML and RDF validation dependencies are installed in CI",
    )
    def test_zhuyin_library_catalog_matches_official_schemas_and_vocabulary(self):
        from lxml import etree
        from rdflib import Graph, RDF, URIRef
        from rdflib.compare import isomorphic

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"DataCatalog",'
                '"dataset":[]}</script><p class="foot">Footer</p>',
                encoding="utf-8",
            )
            zhuyin_epub_opds.build(pages, app_public=False)
            zhuyin_library_catalog.build(pages, app_public=False)
            package = pages / zhuyin_library_catalog.PACKAGE_PATH
            specifications = (
                Path(GEO)
                / "reference_datasets"
                / "library-catalog"
            )
            sources = json.loads(
                (specifications / "sources.json").read_text(encoding="utf-8")
            )
            for source in sources["files"]:
                self.assertEqual(
                    source["sha256"],
                    hashlib.sha256(
                        (specifications / source["filename"]).read_bytes()
                    ).hexdigest(),
                )

            class LocalSchemaResolver(etree.Resolver):
                def resolve(self, url, public_id, context):
                    if url.endswith("/mods/xml.xsd"):
                        return self.resolve_filename(
                            str((specifications / "xml.xsd").resolve()),
                            context,
                        )
                    if url.endswith("/standards/xlink/xlink.xsd"):
                        return self.resolve_filename(
                            str((specifications / "xlink.xsd").resolve()),
                            context,
                        )
                    return None

            parser = etree.XMLParser(no_network=True)
            parser.resolvers.add(LocalSchemaResolver())
            for schema_name, filename in (
                ("MARC21slim.xsd", zhuyin_library_catalog.MARC_FILENAME),
                ("mods-3-8.xsd", zhuyin_library_catalog.MODS_FILENAME),
            ):
                schema = etree.XMLSchema(
                    etree.parse(str(specifications / schema_name), parser)
                )
                schema.assertValid(
                    etree.parse(str(package / filename), parser)
                )

            json_graph = Graph().parse(
                package / zhuyin_library_catalog.BIBFRAME_JSONLD_FILENAME,
                format="json-ld",
            )
            turtle_graph = Graph().parse(
                package / zhuyin_library_catalog.BIBFRAME_TURTLE_FILENAME,
                format="turtle",
            )
            self.assertTrue(isomorphic(json_graph, turtle_graph))
            self.assertEqual(94, len(json_graph))
            bf = zhuyin_library_catalog.BF
            self.assertEqual(
                2,
                len(set(json_graph.subjects(RDF.type, URIRef(bf + "Work")))),
            )
            self.assertEqual(
                2,
                len(
                    set(
                        json_graph.subjects(
                            RDF.type,
                            URIRef(bf + "Instance"),
                        )
                    )
                ),
            )
            ontology = Graph().parse(
                specifications / "bibframe.rdf",
                format="xml",
            )
            declared = set(ontology.subjects())
            used = {
                term
                for triple in json_graph
                for term in triple
                if isinstance(term, URIRef) and str(term).startswith(bf)
            }
            self.assertFalse(used - declared)

    def test_zhuyin_oer_metadata_is_complete_verifiable_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            catalog = {
                "@context": "https://schema.org",
                "@type": "DataCatalog",
                "dataset": [],
            }
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                + json.dumps(catalog)
                + '</script><main><p class="foot">Footer</p></main>',
                encoding="utf-8",
            )
            zhuyin_epub_opds.build(pages, app_public=False)
            urls = zhuyin_oer_metadata.build(pages, app_public=False)
            self.assertEqual(9, len(urls))

            package_dir = pages / zhuyin_oer_metadata.PACKAGE_PATH
            expected = tuple(
                package_dir / filename
                for filename in zhuyin_oer_metadata.DOWNLOAD_FILENAMES
            ) + (
                pages / zhuyin_oer_metadata.LANDING_PATH,
                pages / zhuyin_oer_metadata.ZH_LANDING_PATH,
                pages / zhuyin_oer_metadata.SITEMAP_PATH,
            )
            self.assertTrue(all(path.exists() for path in expected))

            raw = b"\n".join(
                (package_dir / filename).read_bytes()
                for filename in zhuyin_oer_metadata.DOWNLOAD_FILENAMES
            )
            for forbidden in (
                b"apps.apple.com",
                zhuyin_oer_metadata.APP_ID.encode("ascii"),
                zhuyin_oer_metadata.APP_NAME.encode("utf-8"),
                b"SoftwareApplication",
                b"imsmd",
            ):
                self.assertNotIn(forbidden, raw)

            source = json.loads(
                (
                    pages
                    / zhuyin_oer_metadata.SOURCE_METADATA_PATH
                ).read_text(encoding="utf-8")
            )
            source_editions = {
                item["inLanguage"]: item
                for item in source["encoding"]
                if item["encodingFormat"] == "application/epub+zip"
            }
            oai_files = (
                ("en", zhuyin_oer_metadata.OAI_DC_EN_FILENAME),
                ("zh-Hant", zhuyin_oer_metadata.OAI_DC_ZH_FILENAME),
            )
            for locale, filename in oai_files:
                root = ET.parse(package_dir / filename).getroot()
                self.assertEqual(
                    f"{{{zhuyin_oer_metadata.OAI_DC_NS}}}dc",
                    root.tag,
                )
                identifiers = {
                    item.text
                    for item in root.findall(
                        f"{{{zhuyin_oer_metadata.DC_ELEMENTS}}}identifier"
                    )
                }
                self.assertIn(
                    source_editions[locale]["contentUrl"],
                    identifiers,
                )
                self.assertIn(
                    f"urn:sha256:{source_editions[locale]['sha256']}",
                    identifiers,
                )
                self.assertFalse(
                    root.findall(
                        f"{{{zhuyin_oer_metadata.DC_ELEMENTS}}}source"
                    )
                )
                relations = {
                    item.text
                    for item in root.findall(
                        f"{{{zhuyin_oer_metadata.DC_ELEMENTS}}}relation"
                    )
                }
                self.assertIn(
                    zhuyin_oer_metadata.SOURCE_METADATA_URL,
                    relations,
                )
                self.assertIn(
                    zhuyin_oer_metadata.EPUB_LANDING_URL,
                    relations,
                )

            for filename, modified_key in (
                (
                    zhuyin_oer_metadata.DCMI_FILENAME,
                    "dcterms:modified",
                ),
                (
                    zhuyin_oer_metadata.LRMI_FILENAME,
                    "schema:dateModified",
                ),
            ):
                document = json.loads(
                    (package_dir / filename).read_text(encoding="utf-8")
                )
                self.assertIsInstance(document["@context"], dict)
                resources = {
                    node["@id"]: node
                    for node in document["@graph"]
                    if node.get("@id") in {
                        source_editions["en"]["contentUrl"],
                        source_editions["zh-Hant"]["contentUrl"],
                    }
                }
                self.assertEqual(
                    {
                        source_editions["en"]["contentUrl"],
                        source_editions["zh-Hant"]["contentUrl"],
                    },
                    set(resources),
                )
                for node in resources.values():
                    self.assertEqual(
                        source["dateModified"],
                        node[modified_key]["@value"],
                    )

            metadata = json.loads(
                (
                    package_dir / zhuyin_oer_metadata.METADATA_FILENAME
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(5, len(metadata["distribution"]))
            self.assertIn(
                zhuyin_oer_metadata.OAI_DC_SCHEMA,
                metadata["conformsTo"],
            )
            self.assertIn(
                zhuyin_oer_metadata.DCMI_TERMS_SPEC,
                metadata["conformsTo"],
            )
            self.assertIn(
                zhuyin_oer_metadata.LRMI_TERMS_SPEC,
                metadata["conformsTo"],
            )
            for distribution in metadata["distribution"]:
                filename = Path(distribution["contentUrl"]).name
                local = package_dir / filename
                self.assertEqual(
                    local.stat().st_size,
                    int(distribution["contentSize"].split()[0]),
                )
                self.assertEqual(
                    hashlib.sha256(local.read_bytes()).hexdigest(),
                    distribution["sha256"],
                )

            with zipfile.ZipFile(
                package_dir / zhuyin_oer_metadata.BUNDLE_FILENAME
            ) as archive:
                self.assertEqual(
                    {
                        *zhuyin_oer_metadata.PRIMARY_FILENAMES,
                        "README.txt",
                        "checksums.sha256",
                    },
                    set(archive.namelist()),
                )
                for filename in zhuyin_oer_metadata.PRIMARY_FILENAMES:
                    self.assertEqual(
                        (package_dir / filename).read_bytes(),
                        archive.read(filename),
                    )

            english = (
                pages / zhuyin_oer_metadata.LANDING_PATH
            ).read_text(encoding="utf-8")
            traditional = (
                pages / zhuyin_oer_metadata.ZH_LANDING_PATH
            ).read_text(encoding="utf-8")
            for landing in (english, traditional):
                self.assertIn("OAI-DC", landing)
                self.assertIn("DCMI Terms", landing)
                self.assertIn("LRMI", landing)
                self.assertIn("OAI-PMH", landing)
                self.assertNotIn("apps.apple.com", landing)
                self.assertNotIn('"SoftwareApplication"', landing)

            package_info = {
                filename: zhuyin_oer_metadata._artifact(
                    filename,
                    (package_dir / filename).read_bytes(),
                )
                for filename in zhuyin_oer_metadata.DOWNLOAD_FILENAMES
            }
            public = zhuyin_oer_metadata.render_landing(
                "en",
                package_info,
                metadata["dateModified"],
                zhuyin_oer_metadata.INITIAL_DATE,
                True,
            )
            self.assertIn("apps.apple.com", public)
            self.assertIn('"SoftwareApplication"', public)

            index = (data / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                index.count(zhuyin_oer_metadata.CARD_START),
            )
            self.assertIn(zhuyin_oer_metadata.LANDING_URL, index)
            sitemap = (
                pages / zhuyin_oer_metadata.SITEMAP_PATH
            ).read_text(encoding="utf-8")
            for filename in zhuyin_oer_metadata.DOWNLOAD_FILENAMES:
                self.assertIn(
                    f"{zhuyin_oer_metadata.PACKAGE_URL}/{filename}",
                    sitemap,
                )

            with mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ), mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(data),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("Bopomofo OER repository metadata", content)
                self.assertIn(
                    zhuyin_oer_metadata.LRMI_FILENAME,
                    content,
                )
            for content in (robots, sitemap_index):
                self.assertIn(
                    "sitemap_oer_metadata.xml",
                    content,
                )

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (*expected, data / "index.html")
            }
            zhuyin_oer_metadata.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {
                    path: path.stat().st_mtime_ns
                    for path in (*expected, data / "index.html")
                },
            )

    @unittest.skipUnless(
        importlib.util.find_spec("lxml")
        and importlib.util.find_spec("rdflib"),
        "XML and RDF validation dependencies are installed in CI",
    )
    def test_zhuyin_oer_metadata_matches_official_schemas_and_vocabularies(self):
        from lxml import etree
        from rdflib import Graph, Literal, RDF, URIRef, XSD

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            data = pages / "data"
            data.mkdir(parents=True)
            (data / "index.html").write_text(
                '<script type="application/ld+json">'
                '{"@context":"https://schema.org","@type":"DataCatalog",'
                '"dataset":[]}</script><p class="foot">Footer</p>',
                encoding="utf-8",
            )
            zhuyin_epub_opds.build(pages, app_public=False)
            zhuyin_oer_metadata.build(pages, app_public=False)
            package = pages / zhuyin_oer_metadata.PACKAGE_PATH
            specifications = (
                Path(GEO)
                / "reference_datasets"
                / "oer-metadata"
            )
            sources = json.loads(
                (specifications / "sources.json").read_text(encoding="utf-8")
            )
            self.assertIn("IMS", sources["excluded"][0]["name"])
            for source in sources["files"]:
                self.assertEqual(
                    source["sha256"],
                    hashlib.sha256(
                        (specifications / source["filename"]).read_bytes()
                    ).hexdigest(),
                )
            notice = " ".join(
                (
                    specifications / sources["notice"]["filename"]
                ).read_text(encoding="utf-8").split()
            )
            self.assertIn(
                "Portions of this software may use XML and RDF schemas "
                "Copyright © 2011 DCMI, the Dublin Core™ Metadata Initiative.",
                notice,
            )
            self.assertIn(sources["notice"]["license"], notice)

            class LocalSchemaResolver(etree.Resolver):
                def resolve(self, url, public_id, context):
                    if url.endswith("simpledc20021212.xsd"):
                        return self.resolve_filename(
                            str(
                                (
                                    specifications
                                    / "simpledc20021212.xsd"
                                ).resolve()
                            ),
                            context,
                        )
                    if url.endswith("xml.xsd"):
                        return self.resolve_filename(
                            str((specifications / "xml.xsd").resolve()),
                            context,
                        )
                    return None

            parser = etree.XMLParser(no_network=True)
            parser.resolvers.add(LocalSchemaResolver())
            schema = etree.XMLSchema(
                etree.parse(
                    str(specifications / "oai_dc.xsd"),
                    parser,
                )
            )
            for filename in (
                zhuyin_oer_metadata.OAI_DC_EN_FILENAME,
                zhuyin_oer_metadata.OAI_DC_ZH_FILENAME,
            ):
                schema.assertValid(
                    etree.parse(str(package / filename), parser)
                )

            dcmi_graph = Graph().parse(
                package / zhuyin_oer_metadata.DCMI_FILENAME,
                format="json-ld",
            )
            lrmi_graph = Graph().parse(
                package / zhuyin_oer_metadata.LRMI_FILENAME,
                format="json-ld",
            )
            manifest_graph = Graph().parse(
                package / zhuyin_oer_metadata.METADATA_FILENAME,
                format="json-ld",
            )
            landing = (
                pages / zhuyin_oer_metadata.LANDING_PATH
            ).read_text(encoding="utf-8")
            landing_schema = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                landing,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(landing_schema)
            landing_graph = Graph().parse(
                data=landing_schema.group(1),
                format="json-ld",
            )
            self.assertEqual(102, len(dcmi_graph))
            self.assertEqual(174, len(lrmi_graph))
            schema = zhuyin_oer_metadata.SCHEMA
            for graph, predicates in (
                (
                    manifest_graph,
                    ("url", "license", "contentUrl", "conformsTo"),
                ),
                (
                    landing_graph,
                    (
                        "url",
                        "license",
                        "contentUrl",
                        "isBasedOn",
                        "conformsTo",
                    ),
                ),
            ):
                for predicate in predicates:
                    values = list(
                        graph.objects(
                            predicate=URIRef(f"{schema}{predicate}")
                        )
                    )
                    self.assertTrue(values, predicate)
                    self.assertTrue(
                        all(isinstance(value, URIRef) for value in values),
                        (predicate, values),
                    )
            source_metadata = json.loads(
                (
                    pages / zhuyin_oer_metadata.SOURCE_METADATA_PATH
                ).read_text(encoding="utf-8")
            )
            source_modified = Literal(
                source_metadata["dateModified"],
                datatype=XSD.dateTime,
            )
            dcmi_record = URIRef(
                f"{zhuyin_oer_metadata.PACKAGE_URL}/"
                f"{zhuyin_oer_metadata.DCMI_FILENAME}"
            )
            lrmi_record = URIRef(
                f"{zhuyin_oer_metadata.PACKAGE_URL}/"
                f"{zhuyin_oer_metadata.LRMI_FILENAME}"
            )
            source_manifest = URIRef(
                zhuyin_oer_metadata.SOURCE_METADATA_URL
            )
            self.assertIn(
                source_manifest,
                dcmi_graph.objects(
                    dcmi_record,
                    URIRef(zhuyin_oer_metadata.DCTERMS + "source"),
                ),
            )
            self.assertIn(
                source_manifest,
                lrmi_graph.objects(
                    lrmi_record,
                    URIRef(zhuyin_oer_metadata.SCHEMA + "isBasedOn"),
                ),
            )
            for edition in source_metadata["encoding"]:
                if edition["encodingFormat"] != "application/epub+zip":
                    continue
                resource = URIRef(edition["contentUrl"])
                self.assertIn(
                    source_modified,
                    dcmi_graph.objects(
                        resource,
                        URIRef(
                            zhuyin_oer_metadata.DCTERMS + "modified"
                        ),
                    ),
                )
                self.assertFalse(
                    list(
                        dcmi_graph.objects(
                            resource,
                            URIRef(
                                zhuyin_oer_metadata.DCTERMS + "source"
                            ),
                        )
                    )
                )
                self.assertFalse(
                    list(
                        dcmi_graph.objects(
                            resource,
                            URIRef(
                                zhuyin_oer_metadata.DCTERMS + "isPartOf"
                            ),
                        )
                    )
                )
                self.assertIn(
                    dcmi_record,
                    dcmi_graph.objects(
                        resource,
                        URIRef(
                            zhuyin_oer_metadata.DCTERMS
                            + "isReferencedBy"
                        ),
                    ),
                )
                for predicate in ("isBasedOn", "isPartOf"):
                    self.assertFalse(
                        list(
                            lrmi_graph.objects(
                                resource,
                                URIRef(
                                    zhuyin_oer_metadata.SCHEMA + predicate
                                ),
                            )
                        )
                    )
                self.assertIn(
                    URIRef(zhuyin_oer_metadata.EPUB_LANDING_URL),
                    lrmi_graph.objects(
                        resource,
                        URIRef(
                            zhuyin_oer_metadata.SCHEMA
                            + "mainEntityOfPage"
                        ),
                    ),
                )
                self.assertIn(
                    lrmi_record,
                    lrmi_graph.objects(
                        resource,
                        URIRef(
                            zhuyin_oer_metadata.SCHEMA + "subjectOf"
                        ),
                    ),
                )
                self.assertIn(
                    source_modified,
                    lrmi_graph.objects(
                        resource,
                        URIRef(
                            zhuyin_oer_metadata.SCHEMA + "dateModified"
                        ),
                    ),
                )
            dcmi_vocabulary = Graph().parse(
                specifications / "dcmi-terms.ttl",
                format="turtle",
            )
            lrmi_vocabulary = Graph().parse(
                specifications / "lrmi-terms.ttl",
                format="turtle",
            )
            resource_types = Graph().parse(
                specifications / "learningResourceType.ttl",
                format="turtle",
            )
            educational_uses = Graph().parse(
                specifications / "educationalUse.ttl",
                format="turtle",
            )
            used_dcmi = {
                term
                for triple in dcmi_graph
                for term in triple
                if isinstance(term, URIRef)
                and str(term).startswith(zhuyin_oer_metadata.DCTERMS)
            }
            used_lrmi = {
                term
                for triple in lrmi_graph
                for term in triple
                if isinstance(term, URIRef)
                and str(term).startswith(zhuyin_oer_metadata.LRMI)
            }
            self.assertFalse(used_dcmi - set(dcmi_vocabulary.subjects()))
            self.assertFalse(used_lrmi - set(lrmi_vocabulary.subjects()))
            self.assertIn(
                URIRef(
                    zhuyin_oer_metadata.LRMI_RESOURCE_TYPE
                    + "supportingDocument"
                ),
                set(resource_types.subjects()),
            )
            self.assertIn(
                URIRef(
                    zhuyin_oer_metadata.LRMI_EDUCATIONAL_USE
                    + "instruction"
                ),
                set(educational_uses.subjects()),
            )
            self.assertEqual(
                2,
                len(
                    set(
                        lrmi_graph.subjects(
                            RDF.type,
                            URIRef(
                                zhuyin_oer_metadata.LRMI
                                + "LearningResource"
                            ),
                        )
                    )
                ),
            )
            self.assertNotIn(
                URIRef(zhuyin_oer_metadata.LRMI + "typicalAgeRange"),
                set(lrmi_graph.predicates()),
            )

    def _seed_zhuyin_dcat_pages(self, pages):
        data = pages / "data"
        tools = pages / "tools"
        data.mkdir(parents=True)
        tools.mkdir()
        with mock.patch.object(
            gen_data_hub,
            "PAGES",
            str(pages),
        ), mock.patch.object(
            gen_data_hub,
            "DATA",
            str(data),
        ):
            gen_data_hub.build_zhuyin_page()
        (data / "index.html").write_text(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"DataCatalog",'
            '"dataset":[]}</script><main><a class="item" href="'
            f'{zhuyin_skos_vocabulary.SOURCE_PAGE}">'
            '<h2>Source dataset</h2></a>'
            '<p class="foot">Footer</p></main>',
            encoding="utf-8",
        )
        (tools / "index.html").write_text(
            '<main><section class="wrap grid"></section></main>',
            encoding="utf-8",
        )
        zhuyin_anki_deck.build(pages, app_public=False)
        zhuyin_skos_vocabulary.build(pages, app_public=False)
        zhuyin_croissant_dataset.build(pages, app_public=False)
        zhuyin_frictionless_package.build(pages, app_public=False)
        zhuyin_csvw_metadata.build(pages, app_public=False)
        zhuyin_bagit_package.build(pages, app_public=False)
        zhuyin_ocfl_object.build(pages, app_public=False)
        zhuyin_iiif_presentation.build(pages, app_public=False)
        zhuyin_ro_crate.build(pages, app_public=False)
        zhuyin_mets_premis_package.build(pages, app_public=False)
        zhuyin_static_api.build(pages, app_public=False)
        zhuyin_ldes_event_stream.build(pages, app_public=False)
        zhuyin_ore_resource_map.build(pages, app_public=False)
        zhuyin_lms_assessment_bank.build(pages, app_public=False)
        zhuyin_epub_opds.build(pages, app_public=False)
        zhuyin_library_catalog.build(pages, app_public=False)
        zhuyin_oer_metadata.build(pages, app_public=False)

    def test_zhuyin_dcat_catalog_is_complete_verifiable_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            with mock.patch.object(
                zhuyin_mets_premis_package,
                "_utc_now",
                return_value=dt.datetime(
                    2026,
                    7,
                    11,
                    20,
                    33,
                    13,
                    tzinfo=dt.timezone.utc,
                ),
            ):
                self._seed_zhuyin_dcat_pages(pages)
            urls = zhuyin_dcat_catalog.build(pages, app_public=False)
            self.assertEqual(7, len(urls))

            package_dir = pages / zhuyin_dcat_catalog.PACKAGE_PATH
            expected = tuple(
                package_dir / filename
                for filename in zhuyin_dcat_catalog.DOWNLOAD_FILENAMES
            ) + (
                pages / zhuyin_dcat_catalog.LANDING_PATH,
                pages / zhuyin_dcat_catalog.ZH_LANDING_PATH,
                pages / zhuyin_dcat_catalog.SITEMAP_PATH,
            )
            self.assertTrue(all(path.exists() for path in expected))

            metadata = json.loads(
                (
                    package_dir / zhuyin_dcat_catalog.METADATA_FILENAME
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(16, metadata["numberOfItems"])
            self.assertEqual(16, len(metadata["dataset"]))
            self.assertEqual(3, len(metadata["distribution"]))
            self.assertEqual(
                zhuyin_dcat_catalog.DCAT_SPEC,
                metadata["conformsTo"],
            )
            for distribution in metadata["distribution"]:
                filename = Path(distribution["contentUrl"]).name
                local = package_dir / filename
                self.assertEqual(
                    local.stat().st_size,
                    int(distribution["contentSize"].split()[0]),
                )
                self.assertEqual(
                    hashlib.sha256(local.read_bytes()).hexdigest(),
                    distribution["sha256"],
                )

            raw_parts = [
                (package_dir / filename).read_bytes()
                for filename in (
                    *zhuyin_dcat_catalog.PRIMARY_FILENAMES,
                    zhuyin_dcat_catalog.METADATA_FILENAME,
                )
            ]
            with zipfile.ZipFile(
                package_dir / zhuyin_dcat_catalog.BUNDLE_FILENAME
            ) as archive:
                self.assertEqual(
                    {
                        *zhuyin_dcat_catalog.PRIMARY_FILENAMES,
                        "README.txt",
                        "checksums.sha256",
                    },
                    set(archive.namelist()),
                )
                self.assertEqual(
                    sorted(archive.namelist()),
                    archive.namelist(),
                )
                stamp = zhuyin_dcat_catalog._timestamp(
                    metadata["dateModified"]
                )
                expected_date = (
                    max(1980, stamp.year),
                    stamp.month,
                    stamp.day,
                    stamp.hour,
                    stamp.minute,
                    stamp.second - stamp.second % 2,
                )
                for info in archive.infolist():
                    self.assertEqual(expected_date, info.date_time)
                    self.assertEqual(0o100644, info.external_attr >> 16)
                    raw_parts.append(archive.read(info.filename))
                for filename in zhuyin_dcat_catalog.PRIMARY_FILENAMES:
                    self.assertEqual(
                        (package_dir / filename).read_bytes(),
                        archive.read(filename),
                    )

            raw = b"\n".join(raw_parts)
            for forbidden in (
                b"apps.apple.com",
                zhuyin_dcat_catalog.APP_ID.encode("ascii"),
                zhuyin_dcat_catalog.APP_NAME.encode("utf-8"),
                b"SoftwareApplication",
            ):
                self.assertNotIn(forbidden, raw)

            english = (
                pages / zhuyin_dcat_catalog.LANDING_PATH
            ).read_text(encoding="utf-8")
            traditional = (
                pages / zhuyin_dcat_catalog.ZH_LANDING_PATH
            ).read_text(encoding="utf-8")
            for landing in (english, traditional):
                self.assertIn("DCAT 3", landing)
                self.assertIn("SPDX", landing)
                self.assertIn("71", landing)
                self.assertIn("IIIF", landing)
                self.assertIn("RO-Crate", landing)
                self.assertIn("METS", landing)
                self.assertIn("PREMIS", landing)
                self.assertIn("OAI-ORE", landing)
                self.assertNotIn("apps.apple.com", landing)
                self.assertNotIn('"SoftwareApplication"', landing)

            package_info = {
                filename: zhuyin_dcat_catalog._artifact(
                    filename,
                    (package_dir / filename).read_bytes(),
                )
                for filename in zhuyin_dcat_catalog.DOWNLOAD_FILENAMES
            }
            public = zhuyin_dcat_catalog.render_landing(
                "en",
                package_info,
                metadata["dateModified"],
                zhuyin_dcat_catalog.INITIAL_DATE,
                True,
            )
            self.assertIn("apps.apple.com", public)
            self.assertIn('"SoftwareApplication"', public)

            index = (pages / "data" / "index.html").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                1,
                index.count(zhuyin_dcat_catalog.CARD_START),
            )
            self.assertIn(zhuyin_dcat_catalog.LANDING_URL, index)
            sitemap = (
                pages / zhuyin_dcat_catalog.SITEMAP_PATH
            ).read_text(encoding="utf-8")
            for filename in zhuyin_dcat_catalog.DOWNLOAD_FILENAMES:
                self.assertIn(
                    f"{zhuyin_dcat_catalog.PACKAGE_URL}/{filename}",
                    sitemap,
                )

            with mock.patch.object(
                gen_llms,
                "PAGES",
                str(pages),
            ), mock.patch.object(
                gen_llms,
                "DATA_DIR",
                str(pages / "data"),
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("Bopomofo DCAT 3 open-data catalog", content)
                self.assertIn(
                    zhuyin_dcat_catalog.JSONLD_FILENAME,
                    content,
                )
            for content in (robots, sitemap_index):
                self.assertIn("sitemap_dcat.xml", content)

            published_answers = (
                Path(GEO)
                / "pages"
                / "answers"
                / (
                    "where-can-an-open-data-catalog-harvest-a-bopomofo-"
                    "dataset-in-dcat-3.html"
                ),
                Path(GEO)
                / "pages"
                / "zh-Hant"
                / "answers"
                / (
                    "where-can-an-open-data-catalog-harvest-a-bopomofo-"
                    "dataset-in-dcat-3.html"
                ),
            )
            for answer in published_answers:
                content = answer.read_text(encoding="utf-8")
                self.assertIn("80", content)
                self.assertIn("IIIF", content)
                self.assertIn("BagIt", content)
                self.assertIn("RO-Crate", content)
                self.assertIn("METS", content)
                self.assertIn("PREMIS", content)
                self.assertIn("OAI-ORE", content)
                self.assertIn("LDES", content)
                self.assertNotIn("56 exact distributions", content)
                self.assertNotIn("56 個精確", content)

            translations = json.loads(
                (
                    Path(GEO) / "i18n_trans" / "zh-Hant.json"
                ).read_text(encoding="utf-8")
            )
            detail_source = next(
                source
                for source in translations
                if source.startswith(
                    "The catalog covers the 37-symbol reference data"
                )
            )
            detail_translation = translations[detail_source]
            self.assertIn(
                zhuyin_dcat_catalog.ZH_LANDING_URL,
                detail_translation,
            )
            self.assertNotIn(
                zhuyin_dcat_catalog.LANDING_URL + " 下載",
                detail_translation,
            )

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (*expected, pages / "data" / "index.html")
            }
            zhuyin_dcat_catalog.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {
                    path: path.stat().st_mtime_ns
                    for path in (*expected, pages / "data" / "index.html")
                },
            )

    @unittest.skipUnless(
        importlib.util.find_spec("rdflib"),
        "RDF validation dependency is installed in CI",
    )
    def test_zhuyin_dcat_catalog_matches_official_vocabulary_and_files(self):
        from rdflib import Graph, RDF, URIRef, XSD
        from rdflib.compare import isomorphic

        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_dcat_pages(pages)
            zhuyin_dcat_catalog.build(pages, app_public=False)
            package = pages / zhuyin_dcat_catalog.PACKAGE_PATH

            json_graph = Graph().parse(
                package / zhuyin_dcat_catalog.JSONLD_FILENAME,
                format="json-ld",
            )
            turtle_graph = Graph().parse(
                package / zhuyin_dcat_catalog.TURTLE_FILENAME,
                format="turtle",
            )
            self.assertTrue(isomorphic(json_graph, turtle_graph))
            self.assertEqual(1664, len(json_graph))

            dcat = zhuyin_dcat_catalog.DCAT
            dcterms = zhuyin_dcat_catalog.DCTERMS
            foaf = zhuyin_dcat_catalog.FOAF
            spdx = zhuyin_dcat_catalog.SPDX
            catalogs = set(
                json_graph.subjects(RDF.type, URIRef(dcat + "Catalog"))
            )
            records = set(
                json_graph.subjects(
                    RDF.type,
                    URIRef(dcat + "CatalogRecord"),
                )
            )
            datasets = set(
                json_graph.subjects(RDF.type, URIRef(dcat + "Dataset"))
            )
            distributions = set(
                json_graph.subjects(
                    RDF.type,
                    URIRef(dcat + "Distribution"),
                )
            )
            services = set(
                json_graph.subjects(
                    RDF.type,
                    URIRef(dcat + "DataService"),
                )
            )
            self.assertEqual(
                {URIRef(zhuyin_dcat_catalog.CATALOG_ID)},
                catalogs,
            )
            self.assertEqual(16, len(records))
            self.assertEqual(16, len(datasets))
            self.assertEqual(80, len(distributions))
            self.assertEqual(
                {URIRef(zhuyin_dcat_catalog.API_SERVICE)},
                services,
            )

            catalog = next(iter(catalogs))
            self.assertEqual(
                datasets,
                set(json_graph.objects(catalog, URIRef(dcat + "dataset"))),
            )
            self.assertEqual(
                records,
                set(json_graph.objects(catalog, URIRef(dcat + "record"))),
            )
            catalog_modified = list(
                json_graph.objects(
                    catalog,
                    URIRef(dcterms + "modified"),
                )
            )
            self.assertEqual(1, len(catalog_modified))
            for record in records:
                primary_topics = list(
                    json_graph.objects(
                        record,
                        URIRef(foaf + "primaryTopic"),
                    )
                )
                self.assertEqual(1, len(primary_topics))
                self.assertIn(primary_topics[0], datasets)
                self.assertEqual(
                    catalog_modified,
                    list(
                        json_graph.objects(
                            record,
                            URIRef(dcterms + "modified"),
                        )
                    ),
                )
            self.assertTrue(
                any(
                    catalog_modified[0]
                    not in set(
                        json_graph.objects(
                            dataset,
                            URIRef(dcterms + "modified"),
                        )
                    )
                    for dataset in datasets
                )
            )
            epub_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-epub"
            )
            epub_standards = set(
                json_graph.objects(
                    epub_dataset,
                    URIRef(dcterms + "conformsTo"),
                )
            )
            self.assertTrue(
                {
                    URIRef(zhuyin_dcat_catalog.WEBPUB_SPEC),
                    URIRef(zhuyin_dcat_catalog.OPDS2_SPEC),
                    URIRef(zhuyin_dcat_catalog.OPDS1_SPEC),
                }
                <= epub_standards
            )
            croissant_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-croissant"
            )
            csvw_standards = set(
                json_graph.objects(
                    croissant_dataset,
                    URIRef(dcterms + "conformsTo"),
                )
            )
            self.assertTrue(
                {
                    URIRef(value)
                    for value in zhuyin_csvw_metadata.CSVW_RECOMMENDATIONS
                }
                <= csvw_standards
            )
            bagit_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-bagit"
            )
            self.assertEqual(
                {URIRef(zhuyin_bagit_package.RFC_URL)},
                set(
                    json_graph.objects(
                        bagit_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )
            ocfl_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-ocfl"
            )
            self.assertEqual(
                {URIRef(zhuyin_ocfl_object.SPEC_URL)},
                set(
                    json_graph.objects(
                        ocfl_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )
            iiif_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-iiif"
            )
            self.assertEqual(
                {URIRef(zhuyin_iiif_presentation.IIIF_SPEC_URL)},
                set(
                    json_graph.objects(
                        iiif_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )
            ro_crate_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-ro-crate"
            )
            self.assertEqual(
                {URIRef(zhuyin_ro_crate.PROFILE)},
                set(
                    json_graph.objects(
                        ro_crate_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )
            mets_premis_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-mets-premis"
            )
            self.assertEqual(
                {
                    URIRef(zhuyin_mets_premis_package.METS_SCHEMA_URL),
                    URIRef(zhuyin_mets_premis_package.PREMIS_GUIDE_URL),
                },
                set(
                    json_graph.objects(
                        mets_premis_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )
            ore_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-oai-ore"
            )
            self.assertEqual(
                {
                    URIRef(zhuyin_ore_resource_map.ORE_MODEL),
                    URIRef(zhuyin_ore_resource_map.ORE_VOCABULARY),
                    URIRef(zhuyin_ore_resource_map.ORE_RDFXML),
                },
                set(
                    json_graph.objects(
                        ore_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )
            ldes_dataset = URIRef(
                f"{zhuyin_dcat_catalog.LANDING_URL}#dataset-ldes"
            )
            self.assertEqual(
                {
                    URIRef(zhuyin_ldes_event_stream.LDES_SPEC),
                    URIRef(zhuyin_ldes_event_stream.TREE_SPEC),
                    URIRef(zhuyin_ldes_event_stream.SHACL_SPEC),
                },
                set(
                    json_graph.objects(
                        ldes_dataset,
                        URIRef(dcterms + "conformsTo"),
                    )
                ),
            )

            checksum_nodes = set()
            unregistered_media_types = {
                "https://www.iana.org/assignments/media-types/application/jsonl",
                "https://www.iana.org/assignments/media-types/application/schema+json",
                "https://www.iana.org/assignments/media-types/application/webpub+json",
                "https://www.iana.org/assignments/media-types/application/opds+json",
            }
            site_prefix = f"{zhuyin_dcat_catalog.SITE}/"
            for distribution in distributions:
                download_urls = list(
                    json_graph.objects(
                        distribution,
                        URIRef(dcat + "downloadURL"),
                    )
                )
                access_urls = list(
                    json_graph.objects(
                        distribution,
                        URIRef(dcat + "accessURL"),
                    )
                )
                media_types = list(
                    json_graph.objects(
                        distribution,
                        URIRef(dcat + "mediaType"),
                    )
                )
                byte_sizes = list(
                    json_graph.objects(
                        distribution,
                        URIRef(dcat + "byteSize"),
                    )
                )
                checksums = list(
                    json_graph.objects(
                        distribution,
                        URIRef(spdx + "checksum"),
                    )
                )
                self.assertEqual(1, len(download_urls))
                self.assertEqual(download_urls, access_urls)
                self.assertEqual(1, len(media_types))
                self.assertTrue(
                    str(media_types[0]).startswith(
                        "https://www.iana.org/assignments/media-types/"
                    )
                )
                self.assertNotIn(
                    str(media_types[0]),
                    unregistered_media_types,
                )
                self.assertEqual(1, len(byte_sizes))
                self.assertEqual(XSD.nonNegativeInteger, byte_sizes[0].datatype)
                self.assertEqual(
                    [URIRef(zhuyin_dcat_catalog.LICENSE)],
                    list(
                        json_graph.objects(
                            distribution,
                            URIRef(dcterms + "license"),
                        )
                    ),
                )
                self.assertEqual(1, len(checksums))
                checksum = checksums[0]
                checksum_nodes.add(checksum)
                self.assertIn(
                    (checksum, RDF.type, URIRef(spdx + "Checksum")),
                    json_graph,
                )
                self.assertEqual(
                    [URIRef(spdx + "checksumAlgorithm_sha256")],
                    list(
                        json_graph.objects(
                            checksum,
                            URIRef(spdx + "algorithm"),
                        )
                    ),
                )
                values = list(
                    json_graph.objects(
                        checksum,
                        URIRef(spdx + "checksumValue"),
                    )
                )
                self.assertEqual(1, len(values))
                self.assertEqual(XSD.hexBinary, values[0].datatype)

                url = str(download_urls[0])
                self.assertTrue(url.startswith(site_prefix))
                if url.endswith("/opds/bopomofo-37-symbol-reference.xml"):
                    self.assertEqual(
                        [
                            URIRef(
                                "https://www.iana.org/assignments/"
                                "media-types/application/atom+xml"
                            )
                        ],
                        media_types,
                    )
                elif url.endswith(
                    "/data/zhuyin-bopomofo-ml-dataset.jsonl"
                ):
                    self.assertEqual(
                        [
                            URIRef(
                                "https://www.iana.org/assignments/"
                                "media-types/text/plain"
                            )
                        ],
                        media_types,
                    )
                elif url.endswith(
                    (
                        "/iiif/3/bopomofo/collection.json",
                        "/iiif/3/bopomofo/manifest.json",
                    )
                ):
                    self.assertEqual(
                        [
                            URIRef(
                                "https://www.iana.org/assignments/"
                                "media-types/application/json"
                            )
                        ],
                        media_types,
                    )
                elif url.endswith("/bopomofo-resource-map.ore.rdf"):
                    self.assertEqual(
                        [
                            URIRef(
                                "https://www.iana.org/assignments/"
                                "media-types/application/rdf+xml"
                            )
                        ],
                        media_types,
                    )
                elif (
                    url.endswith("/table-schema.json")
                    or "/publications/bopomofo-37-symbol-reference/"
                    in url
                    and url.endswith("/manifest.json")
                    or url.endswith(
                        "/opds/bopomofo-37-symbol-reference.json"
                    )
                ):
                    self.assertEqual(
                        [
                            URIRef(
                                "https://www.iana.org/assignments/"
                                "media-types/application/json"
                            )
                        ],
                        media_types,
                    )
                local = pages / url.removeprefix(site_prefix)
                self.assertTrue(local.is_file(), url)
                content = local.read_bytes()
                self.assertEqual(len(content), int(str(byte_sizes[0])))
                self.assertEqual(
                    hashlib.sha256(content).hexdigest(),
                    str(values[0]),
                )
            self.assertEqual(80, len(checksum_nodes))
            self.assertEqual(
                1,
                len(
                    set(
                        json_graph.subjects(
                            URIRef(dcat + "mediaType"),
                            URIRef(
                                "https://www.iana.org/assignments/"
                                "media-types/application/csvm+json"
                            ),
                        )
                    )
                ),
            )

            service = next(iter(services))
            self.assertEqual(
                [URIRef(zhuyin_dcat_catalog.API_INDEX)],
                list(
                    json_graph.objects(
                        service,
                        URIRef(dcat + "endpointURL"),
                    )
                ),
            )
            self.assertEqual(
                [URIRef(zhuyin_dcat_catalog.API_OPENAPI)],
                list(
                    json_graph.objects(
                        service,
                        URIRef(dcat + "endpointDescription"),
                    )
                ),
            )

            specifications = (
                Path(GEO) / "reference_datasets" / "dcat3"
            )
            sources = json.loads(
                (specifications / "sources.json").read_text(encoding="utf-8")
            )
            for source in sources["files"]:
                self.assertEqual(
                    source["sha256"],
                    hashlib.sha256(
                        (specifications / source["filename"]).read_bytes()
                    ).hexdigest(),
                )
            notice = (
                specifications / sources["notice"]["filename"]
            ).read_text(encoding="utf-8")
            self.assertIn("W3C Document License", notice)
            self.assertIn(
                "https://www.w3.org/copyright/document-license-2023/",
                notice,
            )
            vocabulary = Graph().parse(
                specifications / "dcat3.ttl",
                format="turtle",
            )
            declared = set(vocabulary.subjects())
            used_dcat = {
                term
                for triple in json_graph
                for term in triple
                if isinstance(term, URIRef) and str(term).startswith(dcat)
            }
            self.assertFalse(used_dcat - declared)

            metadata_graph = Graph().parse(
                package / zhuyin_dcat_catalog.METADATA_FILENAME,
                format="json-ld",
            )
            schema = "https://schema.org/"
            for predicate in (
                "url",
                "license",
                "contentUrl",
                "conformsTo",
            ):
                values = list(
                    metadata_graph.objects(
                        predicate=URIRef(schema + predicate)
                    )
                )
                self.assertTrue(values, predicate)
                self.assertTrue(
                    all(isinstance(value, URIRef) for value in values),
                    (predicate, values),
                )

    def _seed_zhuyin_resourcesync_pages(self, pages):
        self._seed_zhuyin_dcat_pages(pages)
        for generator in (
            zhuyin_readiness_tool,
            zhuyin_grandparent_call_kit,
            zhuyin_picture_book_club_kit,
            zhuyin_parent_teacher_handoff_kit,
            zhuyin_library_storytime_kit,
            zhuyin_grade1_summer_calendar,
        ):
            generator.build(pages)
        for filename in (
            "zhuyin-bingo.html",
            "zhuyin-bopomofo-chart.html",
            "zhuyin-flashcards.html",
            "zhuyin-practice-sheet.html",
        ):
            (pages / "tools" / filename).write_text(
                '<meta name="content-modified" content="2026-07-10">fixture',
                encoding="utf-8",
            )
        zhuyin_dcat_catalog.build(pages, app_public=False)

    def test_zhuyin_resourcesync_is_complete_verifiable_and_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_resourcesync_pages(pages)
            urls = zhuyin_resourcesync.build(pages, app_public=False)

            expected = (
                pages / zhuyin_resourcesync.SOURCE_DESCRIPTION_COPY_PATH,
                pages / zhuyin_resourcesync.CAPABILITY_LIST_PATH,
                pages / zhuyin_resourcesync.RESOURCE_LIST_PATH,
                pages / zhuyin_resourcesync.COLLECTION_PATH,
                pages / zhuyin_resourcesync.STATE_PATH,
                pages / zhuyin_resourcesync.LANDING_PATH,
                pages / zhuyin_resourcesync.ZH_LANDING_PATH,
                pages / zhuyin_resourcesync.SITEMAP_PATH,
            )
            self.assertEqual(7, len(urls))
            self.assertTrue(all(path.exists() for path in expected))
            self.assertEqual(
                "https://alice51849.github.io/.well-known/resourcesync",
                zhuyin_resourcesync.SOURCE_DESCRIPTION_URL,
            )

            sitemap_ns = zhuyin_resourcesync.SITEMAP_NAMESPACE
            rs_ns = zhuyin_resourcesync.RS_NAMESPACE
            source = ET.parse(expected[0]).getroot()
            capability = ET.parse(expected[1]).getroot()
            resource_list = ET.parse(expected[2]).getroot()
            self.assertEqual(
                "description",
                source.find(f"{{{rs_ns}}}md").attrib["capability"],
            )
            self.assertEqual(
                "capabilitylist",
                capability.find(f"{{{rs_ns}}}md").attrib["capability"],
            )
            root_metadata = resource_list.find(f"{{{rs_ns}}}md")
            self.assertEqual("resourcelist", root_metadata.attrib["capability"])
            self.assertRegex(
                root_metadata.attrib["at"],
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
            )

            resources = zhuyin_resourcesync.discover_resources(pages)
            entries = resource_list.findall(f"{{{sitemap_ns}}}url")
            self.assertEqual(252, len(resources))
            self.assertEqual(len(resources), len(entries))
            resources_by_path = {
                resource.relative_path.as_posix(): resource
                for resource in resources
            }
            self.assertEqual(
                "application/atom+xml",
                resources_by_path[
                    "opds/bopomofo-37-symbol-reference.xml"
                ].media_type,
            )
            self.assertEqual(
                "text/plain",
                resources_by_path[
                    "data/zhuyin-bopomofo-ml-dataset.jsonl"
                ].media_type,
            )
            for relative in (
                "iiif/3/bopomofo/collection.json",
                "iiif/3/bopomofo/manifest.json",
            ):
                self.assertEqual(
                    "application/json",
                    resources_by_path[relative].media_type,
                )
            for relative in zhuyin_resourcesync.RO_CRATE_REQUIRED_PATHS:
                self.assertIn(relative.as_posix(), resources_by_path)
            for relative in zhuyin_resourcesync.METS_PREMIS_REQUIRED_PATHS:
                self.assertIn(relative.as_posix(), resources_by_path)
            for relative in zhuyin_resourcesync.ORE_REQUIRED_PATHS:
                self.assertIn(relative.as_posix(), resources_by_path)
            for relative in zhuyin_resourcesync.LDES_REQUIRED_PATHS:
                self.assertIn(relative.as_posix(), resources_by_path)
            self.assertEqual(
                "application/zip",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-ro-crate/"
                        "bopomofo-37-symbols-ro-crate-1.3.zip"
                    )
                ].media_type,
            )
            self.assertEqual(
                "application/ld+json",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-ldes/"
                        "bopomofo-event-stream.jsonld"
                    )
                ].media_type,
            )
            self.assertEqual(
                "text/turtle",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-ldes/"
                        "bopomofo-event-stream.ttl"
                    )
                ].media_type,
            )
            self.assertEqual(
                "application/zip",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-ldes/"
                        "bopomofo-37-symbols-ldes-tree.zip"
                    )
                ].media_type,
            )
            self.assertEqual(
                "application/ld+json",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-ro-crate/"
                        "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld"
                    )
                ].media_type,
            )
            self.assertEqual(
                "application/zip",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-mets2-premis3/"
                        "bopomofo-37-symbols-mets2-premis3.zip"
                    )
                ].media_type,
            )
            for filename in ("mets.xml", "premis.xml"):
                self.assertEqual(
                    "application/xml",
                    resources_by_path[
                        (
                            "data/packages/zhuyin-bopomofo-mets2-premis3/"
                            + filename
                        )
                    ].media_type,
                )
            self.assertEqual(
                "application/rdf+xml",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-oai-ore/"
                        "bopomofo-resource-map.ore.rdf"
                    )
                ].media_type,
            )
            self.assertEqual(
                "application/zip",
                resources_by_path[
                    (
                        "data/packages/zhuyin-bopomofo-oai-ore/"
                        "bopomofo-37-symbols-oai-ore-bundle.zip"
                    )
                ].media_type,
            )
            self.assertEqual(
                37,
                sum("/symbols/" in resource.url for resource in resources),
            )
            self.assertEqual(
                37,
                sum(
                    "/iiif/3/bopomofo/images/" in resource.url
                    for resource in resources
                ),
            )
            by_url = {resource.url: resource for resource in resources}
            for entry in entries:
                url = entry.find(f"{{{sitemap_ns}}}loc").text
                metadata = entry.find(f"{{{rs_ns}}}md").attrib
                resource = by_url[url]
                self.assertEqual(
                    f"sha-256:{resource.sha256}",
                    metadata["hash"],
                )
                self.assertEqual(str(resource.byte_length), metadata["length"])
                self.assertEqual(resource.media_type, metadata["type"])
                local = pages / resource.relative_path
                self.assertEqual(
                    resource.sha256,
                    hashlib.sha256(local.read_bytes()).hexdigest(),
                )

            raw_controls = "\n".join(
                path.read_text(encoding="utf-8") for path in expected[:4]
            )
            self.assertNotIn("apps.apple.com", raw_controls)
            self.assertNotIn(zhuyin_resourcesync.APP_ID, raw_controls)
            self.assertNotIn(zhuyin_resourcesync.APP_NAME, raw_controls)
            self.assertNotIn("SoftwareApplication", raw_controls)
            collection = json.loads(expected[3].read_text(encoding="utf-8"))
            self.assertEqual(zhuyin_resourcesync.SPEC, collection["conformsTo"])
            self.assertEqual(
                f"{len(resources)} resources",
                collection["size"],
            )
            index = (pages / "data" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count(zhuyin_resourcesync.CARD_START))
            self.assertIn(zhuyin_resourcesync.LANDING_URL, index)

            with mock.patch.object(
                gen_llms, "PAGES", str(pages)
            ), mock.patch.object(
                gen_llms, "DATA_DIR", str(pages / "data")
            ):
                llms = gen_llms.build_llms({}, set())
                full = gen_llms.build_llms_full({}, set())
                robots = gen_llms.build_robots()
                sitemap_index = gen_llms.build_sitemap_index()
            for content in (llms, full):
                self.assertIn("Bopomofo ResourceSync", content)
                self.assertIn(zhuyin_resourcesync.RESOURCE_LIST_URL, content)
            self.assertIn(zhuyin_resourcesync.RESOURCE_LIST_URL, robots)
            self.assertIn(
                zhuyin_resourcesync.RESOURCE_LIST_URL,
                sitemap_index,
            )

            mtimes = {path: path.stat().st_mtime_ns for path in expected}
            zhuyin_resourcesync.build(pages, app_public=False)
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in expected},
            )

    def test_zhuyin_resourcesync_snapshot_changes_only_with_resource_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            self._seed_zhuyin_resourcesync_pages(pages)
            first_revision = dt.datetime(
                2026,
                7,
                11,
                8,
                30,
                tzinfo=dt.timezone.utc,
            )
            with mock.patch.object(
                zhuyin_resourcesync,
                "_utc_now",
                return_value=first_revision,
            ):
                zhuyin_resourcesync.build(pages, app_public=False)
            state_path = pages / zhuyin_resourcesync.STATE_PATH
            first = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                zhuyin_resourcesync.STATE_VERSION,
                first["stateVersion"],
            )
            self.assertEqual("2026-07-11T08:30:00Z", first["at"])

            with mock.patch.object(
                zhuyin_resourcesync,
                "_utc_now",
                return_value=first_revision + dt.timedelta(minutes=10),
            ):
                zhuyin_resourcesync.build(pages, app_public=False)
            unchanged = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(first, unchanged)

            canonical = pages / "data" / "zhuyin-bopomofo.json"
            canonical.write_text('{"fixture":"changed"}\n', encoding="utf-8")
            with mock.patch.object(
                zhuyin_resourcesync,
                "_utc_now",
                return_value=first_revision,
            ):
                zhuyin_resourcesync.build(pages, app_public=False)
            changed = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertNotEqual(first["fingerprint"], changed["fingerprint"])
            self.assertEqual("2026-07-11T08:30:01Z", changed["at"])

    def test_zhuyin_resourcesync_landing_page_gates_optional_app_layer(self):
        private = zhuyin_resourcesync.render_page(
            "zh-Hant", 80, app_public=False
        )
        public = zhuyin_resourcesync.render_page(
            "zh-Hant", 80, app_public=True
        )
        self.assertIn('hreflang="en"', private)
        self.assertIn('hreflang="zh-Hant"', private)
        self.assertIn('rel="resourcesync"', private)
        self.assertIn(zhuyin_resourcesync.SOURCE_DESCRIPTION_URL, private)
        self.assertNotIn("apps.apple.com", private)
        self.assertNotIn('"SoftwareApplication"', private)
        self.assertIn(zhuyin_resourcesync.APP_ID, public)
        self.assertIn('"SoftwareApplication"', public)
        self.assertNotIn('"offers"', public)

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

    def test_answer_localizer_updates_jsonld_language_semantically(self):
        source = (
            '<html lang="en"><head><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Article",'
            '"headline":"Sample headline","inLanguage":"en"}'
            "</script></head><body><h1>Sample headline</h1></body></html>"
        )
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        self.assertNotIn("en", strings)
        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            "sample",
            {"Sample headline": "範例標題"},
        )
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            localized,
            re.S,
        )
        self.assertIsNotNone(match)
        metadata = json.loads(match.group(1))
        self.assertEqual("zh-Hant", metadata["inLanguage"])
        self.assertEqual("範例標題", metadata["headline"])

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
            redirect = (
                '<meta http-equiv="refresh" content="0;url='
                "https://alice51849.github.io/ios-app-guide/tools/helper.html"
                '">'
            )
            self.assertIn(
                "content=\"0;url=https://alice51849.github.io/"
                "ios-app-guide/zh-Hant/tools/helper.html\"",
                aeo_answers_i18n.localize_body_links(
                    redirect,
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
        self.assertIn("zhuyin_csvw_metadata.py", workflow)
        self.assertIn("zhuyin_bagit_package.py", workflow)
        self.assertIn("zhuyin_ocfl_object.py", workflow)
        self.assertIn("zhuyin_iiif_presentation.py", workflow)
        self.assertIn("zhuyin_ro_crate.py", workflow)
        self.assertIn("zhuyin_mets_premis_package.py", workflow)
        self.assertIn("zhuyin_ldes_event_stream.py", workflow)
        self.assertIn("zhuyin_ore_resource_map.py", workflow)
        self.assertIn("requirements-iiif-validation.txt", workflow)
        self.assertIn("iiif-validator-bin", workflow)
        self.assertNotIn(
            'echo "$RUNNER_TEMP/iiif-validator/bin" >> "$GITHUB_PATH"',
            workflow,
        )
        self.assertIn("zhuyin_static_api.py", workflow)
        self.assertIn("zhuyin_lms_assessment_bank.py", workflow)
        self.assertIn("zhuyin_epub_opds.py", workflow)
        self.assertIn("zhuyin_library_catalog.py", workflow)
        self.assertIn("zhuyin_oer_metadata.py", workflow)
        self.assertIn("zhuyin_dcat_catalog.py", workflow)
        self.assertIn("zhuyin_resourcesync.py", workflow)
        self.assertIn("family_travel_mission_cards.py", workflow)
        self.assertIn("family_travel_observation_passport.py", workflow)
        self.assertIn("family_travel_opds_catalog.py", workflow)
        self.assertIn("family_travel_ro_crate.py", workflow)
        self.assertIn("prioritize_trip_planet_resources.py", workflow)
        refresh_block = workflow.split(
            "- name: Refresh AI indexes + hubs", 1
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
            "zhuyin_csvw_metadata.py",
            "zhuyin_bagit_package.py",
            "zhuyin_ocfl_object.py",
            "zhuyin_iiif_presentation.py",
            "zhuyin_ro_crate.py",
            "zhuyin_mets_premis_package.py",
            "zhuyin_static_api.py",
            "zhuyin_ldes_event_stream.py",
            "zhuyin_ore_resource_map.py",
            "zhuyin_lms_assessment_bank.py",
            "zhuyin_epub_opds.py",
            "zhuyin_library_catalog.py",
            "zhuyin_oer_metadata.py",
            "zhuyin_dcat_catalog.py",
            "prioritize_trip_planet_resources.py",
            "add_related_tools.py",
            "gen_hubs.py",
            "gen_app_catalog.py",
            "cleanup_localized_assets.py --cached-live",
            "zhuyin_resourcesync.py",
        )
        workflow_positions = [refresh_block.index(item) for item in workflow_chain]
        self.assertEqual(sorted(workflow_positions), workflow_positions)
        self.assertLess(
            refresh_block.index("cleanup_localized_assets.py --cached-live"),
            refresh_block.rindex("zhuyin_resourcesync.py"),
        )
        self.assertEqual(2, workflow.count("zhuyin_resourcesync.py"))
        final_cleanup_block = workflow.split(
            "- name: Final link and availability cleanup", 1
        )[1].split("- name: Unlink site dir", 1)[0]
        final_chain = (
            "cleanup_localized_assets.py --cached-live",
            "zhuyin_resourcesync.py",
            "gen_image_sitemap.py",
            "gen_linkset.py",
            "gen_social_previews.py",
            "gen_smart_app_banners.py",
            "gen_mobile_store_ctas.py",
            "gen_guide_design.py",
            "gen_llms.py --cached-live",
            "gen_feed.py",
        )
        final_positions = [final_cleanup_block.index(item) for item in final_chain]
        self.assertEqual(sorted(final_positions), final_positions)
        self.assertIn("--refresh-slug \"$SUMMER_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$OBSERVATION_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$EPUB_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$LIBRARY_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$OER_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$DCAT_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$CSVW_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$BAGIT_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$OCFL_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$IIIF_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$RO_CRATE_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$METS_PREMIS_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$ORE_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$LDES_SLUG\"", workflow)
        self.assertIn("--refresh-slug \"$TRIP_SLUG\"", workflow)
        self.assertIn('"lumibopomofo" in live_app_keys', workflow)
        self.assertIn('"tripplanet" in live_app_keys', workflow)
        self.assertIn("aeo_answers.py --cached-live --limit 0", workflow)
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
        self.assertIn("zhuyin_csvw_metadata.py", publish)
        self.assertIn("zhuyin_bagit_package.py", publish)
        self.assertIn("zhuyin_ocfl_object.py", publish)
        self.assertIn("zhuyin_iiif_presentation.py", publish)
        self.assertIn("zhuyin_ro_crate.py", publish)
        self.assertIn("zhuyin_mets_premis_package.py", publish)
        self.assertIn("zhuyin_ldes_event_stream.py", publish)
        self.assertIn("zhuyin_ore_resource_map.py", publish)
        self.assertIn("zhuyin_static_api.py", publish)
        self.assertIn("zhuyin_lms_assessment_bank.py", publish)
        self.assertIn("zhuyin_epub_opds.py", publish)
        self.assertIn("zhuyin_library_catalog.py", publish)
        self.assertIn("zhuyin_oer_metadata.py", publish)
        self.assertIn("zhuyin_dcat_catalog.py", publish)
        self.assertIn("zhuyin_resourcesync.py", publish)
        self.assertIn("gen_image_sitemap.py", publish)
        self.assertIn("gen_linkset.py", publish)
        self.assertIn("gen_social_previews.py", publish)
        self.assertIn("gen_smart_app_banners.py", publish)
        self.assertIn("gen_mobile_store_ctas.py", publish)
        self.assertIn("gen_guide_design.py", publish)
        self.assertIn("family_travel_mission_cards.py", publish)
        self.assertIn("family_travel_observation_passport.py", publish)
        self.assertIn("family_travel_opds_catalog.py", publish)
        self.assertIn("family_travel_ro_crate.py", publish)
        self.assertIn("gen_data_hub.py", publish)
        self.assertIn("family_travel_static_api.py", publish)
        self.assertIn("prioritize_trip_planet_resources.py", publish)
        self.assertIn('gen_llms.py"), "--cached-live"', publish)
        self.assertIn("gen_feed.py", publish)
        self.assertEqual(1, publish.count("zhuyin_resourcesync.py"))
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
            "zhuyin_csvw_metadata.py",
            "zhuyin_bagit_package.py",
            "zhuyin_ocfl_object.py",
            "zhuyin_iiif_presentation.py",
            "zhuyin_ro_crate.py",
            "zhuyin_mets_premis_package.py",
            "zhuyin_static_api.py",
            "zhuyin_ldes_event_stream.py",
            "zhuyin_ore_resource_map.py",
            "zhuyin_lms_assessment_bank.py",
            "zhuyin_epub_opds.py",
            "zhuyin_library_catalog.py",
            "zhuyin_oer_metadata.py",
            "zhuyin_dcat_catalog.py",
            "prioritize_trip_planet_resources.py",
            "add_related_answers.py",
            "add_related_tools.py",
            "fix_en_hreflang.py",
            "zhuyin_resourcesync.py",
            "gen_image_sitemap.py",
            "gen_linkset.py",
            "gen_social_previews.py",
            "gen_smart_app_banners.py",
            "gen_mobile_store_ctas.py",
            "gen_guide_design.py",
            "gen_llms.py",
            "gen_feed.py",
        )
        publish_positions = [publish.index(item) for item in publish_chain]
        self.assertEqual(sorted(publish_positions), publish_positions)
        self.assertLess(
            publish.rindex("zhuyin_resourcesync.py"),
            publish.rindex("gen_llms.py"),
        )
        self.assertIn("--refresh-slug", publish)
        self.assertIn(
            "where-can-a-linked-data-client-replicate-bopomofo-as-an-ldes-1-0-",
            publish,
        )
        self.assertIn("and-tree-event-stream", publish)
        self.assertIn("aeo_answers_i18n.py", publish)
        self.assertIn('"lumibopomofo" in live', publish)
        self.assertIn('"cleanup_localized_assets.py"', publish)
        self.assertIn('"0"', publish)
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
