#!/usr/bin/env python3
"""Regression tests for localized app VideoObject lessons."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_video_lessons as lessons
import publisher_intent_catalog


class AppVideoLessonSourceTests(unittest.TestCase):
    def test_sanitized_sources_are_unique_and_verified_media_profile(self) -> None:
        payload = lessons.load_sources()
        records = payload["records"]

        self.assertEqual(44, len(records))
        self.assertEqual(19, len({record["app_key"] for record in records}))
        self.assertEqual(14, len({record["locale"] for record in records}))
        self.assertEqual(44, len({record["video_url"] for record in records}))
        self.assertEqual(
            {
                "encoding_format": "video/mp4",
                "codec": "h264",
                "width": 886,
                "height": 1920,
            },
            payload["media_profile"],
        )
        for record in records:
            parsed = urllib.parse.urlsplit(record["video_url"])
            self.assertEqual("https", parsed.scheme)
            self.assertEqual("files.catbox.moe", parsed.netloc)
            self.assertTrue(parsed.path.endswith(".mp4"))
            self.assertGreater(record["duration_seconds"], 0)

    def test_i18n_has_no_fallback_for_represented_locales(self) -> None:
        sources = lessons.load_sources()
        represented = {record["locale"] for record in sources["records"]}
        localizations = lessons.load_i18n(represented)

        self.assertTrue(represented.issubset(localizations))
        for locale in represented:
            self.assertEqual(set(lessons.UI_STRINGS), set(localizations[locale]))
            self.assertTrue(all(localizations[locale].values()))

    def test_campaign_tokens_are_unique_and_app_store_safe(self) -> None:
        locales = {record["locale"] for record in lessons.load_sources()["records"]}
        tokens = [lessons._campaign_token(locale) for locale in locales]
        self.assertEqual(len(tokens), len(set(tokens)))
        self.assertTrue(all(len(token) <= 30 for token in tokens))

    def test_store_url_ignores_embedded_provider_without_environment_token(
        self,
    ) -> None:
        intent = {
            "app_store_id": "1234567890",
            "app_store_url": (
                "https://apps.apple.com/us/app/id1234567890"
                "?pt=123&ct=legacy&mt=8"
            ),
        }
        with mock.patch.dict(
            os.environ,
            {lessons.PROVIDER_TOKEN_ENV: ""},
            clear=False,
        ):
            direct = lessons._store_url(intent, "en-US")
        self.assertEqual("", urllib.parse.urlsplit(direct).query)

        with mock.patch.dict(
            os.environ,
            {lessons.PROVIDER_TOKEN_ENV: "987654321"},
            clear=False,
        ):
            attributed = lessons._store_url(intent, "en-US")
        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(attributed).query
        )
        self.assertEqual(["987654321"], query["pt"])
        self.assertEqual(["iag_video_en_us"], query["ct"])
        self.assertEqual(["8"], query["mt"])

    def test_calendar_dates_are_strictly_validated(self) -> None:
        self.assertEqual(
            "2026-07-24T00:00:00+00:00",
            lessons._published_at("2026-07-24"),
        )
        with self.assertRaisesRegex(ValueError, "publication date"):
            lessons._published_at("2026-02-31")


class AppVideoLessonBuildTests(unittest.TestCase):
    def _fixture(self, directory: str) -> tuple[Path, Path]:
        pages = Path(directory)
        (pages / "data").mkdir(parents=True)
        (pages / "social" / "img").mkdir(parents=True)
        (pages / "social" / "img" / "sample-share.jpg").write_bytes(b"jpeg")
        intent = {
            "locale": "en-US",
            "app_key": "sample",
            "app_name": "Sample App",
            "app_store_id": "1234567890",
            "publisher_query": "A private sample app walkthrough",
            "decision_context": "See the real app workflow before you install.",
            "canonical_guide_url": f"{lessons.SITE}/en-US/sample.html",
            "canonical_app_store_url": (
                "https://apps.apple.com/app/id1234567890"
            ),
            "app_store_url": (
                "https://apps.apple.com/us/app/id1234567890"
                "?pt=123&ct=iag_data_en_us&mt=8"
            ),
            "app_store_cta_label": "Get it on the App Store",
            "publisher_disclosure": (
                "Published by Lumi Studio, the developer of Sample App."
            ),
            "verified_live": True,
        }
        catalog = {
            "app_count": 32,
            "records": [intent],
        }
        (pages / "data" / f"{publisher_intent_catalog.SLUG}.json").write_text(
            json.dumps(catalog),
            encoding="utf-8",
        )
        source = pages / "source.json"
        source.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_repository": "alice51849/threads-autopilot",
                    "source_document": "queue.json",
                    "media_profile": {
                        "encoding_format": "video/mp4",
                        "codec": "h264",
                        "width": 886,
                        "height": 1920,
                    },
                    "records": [
                        {
                            "app_key": "sample",
                            "locale": "en-US",
                            "video_url": "https://files.catbox.moe/sample1.mp4",
                            "duration_seconds": 16.0,
                            "published_on": "2026-07-24",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return pages, source

    def _build(
        self,
        pages: Path,
        source: Path,
        today: str,
    ) -> list[dict[str, object]]:
        with mock.patch.dict(
            os.environ,
            {lessons.PROVIDER_TOKEN_ENV: ""},
            clear=False,
        ):
            return lessons.build(
                pages,
                source_path=source,
                today=today,
            )

    def test_build_emits_videoobject_sitemap_markdown_and_hubs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages, source = self._fixture(directory)
            records = self._build(pages, source, "2026-07-24")

            self.assertEqual(1, len(records))
            record = records[0]
            self.assertEqual("PT16S", record["duration"])
            self.assertEqual(
                "",
                urllib.parse.urlsplit(record["app_store_url"]).query,
            )
            manifest = json.loads(
                (pages / lessons.DATA_RELATIVE).read_text(encoding="utf-8")
            )
            self.assertEqual(32, manifest["portfolio_app_count"])
            self.assertEqual(1, manifest["app_count"])
            self.assertEqual(1, manifest["locale_count"])
            self.assertEqual(1, manifest["video_count"])
            self.assertEqual(
                "incremental_publisher_video_archive",
                manifest["coverage_status"],
            )
            self.assertFalse(manifest["campaign_link_attribution_ready"])

            page = (
                pages / lessons.page_relative("sample", "en-US")
            ).read_text(encoding="utf-8")
            self.assertIn('preload="none"', page)
            self.assertIn('type="application/ld+json"', page)
            self.assertIn('type="text/markdown"', page)
            self.assertIn('type="video/mp4"', page)
            schema_text = page.split(
                '<script type="application/ld+json">', 1
            )[1].split("</script>", 1)[0]
            schema = json.loads(schema_text)
            self.assertEqual("VideoObject", schema["@type"])
            self.assertEqual("PT16S", schema["duration"])
            self.assertTrue(schema["isAccessibleForFree"])
            self.assertTrue(schema["isFamilyFriendly"])
            self.assertEqual(record["video_url"], schema["contentUrl"])

            markdown = (
                pages / lessons.markdown_relative("sample", "en-US")
            ).read_text(encoding="utf-8")
            self.assertIn(record["video_url"], markdown)
            self.assertIn(record["app_store_url"], markdown)
            self.assertTrue((pages / lessons.hub_relative()).is_file())
            self.assertTrue((pages / lessons.hub_relative("en-US")).is_file())
            localized_hub = (
                pages / lessons.hub_relative("en-US")
            ).read_text(encoding="utf-8")
            self.assertIn(f'href="{lessons.hub_url()}"', localized_hub)

            sitemap = ET.parse(pages / lessons.SITEMAP_NAME).getroot()
            sitemap_ns = f"{{{lessons.SITEMAP_NS}}}"
            video_ns = f"{{{lessons.VIDEO_NS}}}"
            urls = sitemap.findall(f"{sitemap_ns}url")
            self.assertEqual(3, len(urls))
            self.assertEqual(
                {lessons.hub_url(), lessons.hub_url("en-US")},
                {
                    item.findtext(f"{sitemap_ns}loc")
                    for item in urls
                    if item.find(f"{video_ns}video") is None
                },
            )
            video_entries = [
                item.find(f"{video_ns}video")
                for item in urls
                if item.find(f"{video_ns}video") is not None
            ]
            self.assertEqual(1, len(video_entries))
            video = video_entries[0]
            self.assertIsNotNone(video)
            self.assertEqual(
                record["video_url"],
                video.findtext(f"{video_ns}content_loc"),
            )
            self.assertEqual(
                record["thumbnail_url"],
                video.findtext(f"{video_ns}thumbnail_loc"),
            )
            self.assertEqual("16", video.findtext(f"{video_ns}duration"))

    def test_unchanged_build_preserves_modified_date_and_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages, source = self._fixture(directory)
            self._build(pages, source, "2026-07-24")
            output = pages / lessons.DATA_RELATIVE
            first = output.read_bytes()
            first_mtime = output.stat().st_mtime_ns

            self._build(pages, source, "2026-07-25")

            self.assertEqual(first, output.read_bytes())
            self.assertEqual(first_mtime, output.stat().st_mtime_ns)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("2026-07-24", payload["dateModified"])

    def test_build_rejects_invalid_source_and_build_dates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages, source = self._fixture(directory)
            payload = json.loads(source.read_text(encoding="utf-8"))
            payload["records"][0]["published_on"] = "2026-02-31"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "publication date"):
                lessons.load_sources(source)

            _, valid_source = self._fixture(f"{directory}/valid")
            with self.assertRaisesRegex(ValueError, "build date"):
                self._build(Path(f"{directory}/valid"), valid_source, "2026-02-31")


class AppVideoLessonPublishedOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidates = []
        configured = os.environ.get("GEO_PAGES")
        if configured:
            candidates.append(Path(configured))
        candidates.extend((GEO / "pages", GEO.parents[1]))
        cls.pages = next(
            (
                path
                for path in candidates
                if (path / lessons.DATA_RELATIVE).is_file()
            ),
            None,
        )
        if cls.pages is None:
            raise unittest.SkipTest("Generated video lesson manifest is absent")
        cls.manifest = json.loads(
            (cls.pages / lessons.DATA_RELATIVE).read_text(encoding="utf-8")
        )
        cls.records = cls.manifest["records"]

    def test_manifest_matches_sanitized_sources_and_declares_partial_scope(
        self,
    ) -> None:
        sources = lessons.load_sources()["records"]
        source_pairs = {
            (record["locale"], record["app_key"], record["video_url"])
            for record in sources
        }
        output_pairs = {
            (record["locale"], record["app_key"], record["video_url"])
            for record in self.records
        }

        self.assertEqual(source_pairs, output_pairs)
        self.assertEqual(len(sources), self.manifest["video_count"])
        self.assertEqual(
            len({record["app_key"] for record in sources}),
            self.manifest["app_count"],
        )
        self.assertEqual(
            len({record["locale"] for record in sources}),
            self.manifest["locale_count"],
        )
        self.assertEqual(
            "incremental_publisher_video_archive",
            self.manifest["coverage_status"],
        )
        self.assertFalse(self.manifest["campaign_link_attribution_ready"])
        self.assertEqual(
            "clean_direct_until_provider_token_available",
            self.manifest["app_store_link_policy"],
        )
        self.assertLess(
            self.manifest["app_count"],
            self.manifest["portfolio_app_count"],
        )
        self.assertLess(
            self.manifest["locale_count"],
            self.manifest["official_apple_locale_count"],
        )
        self.assertTrue(all(record["verified_live"] for record in self.records))
        self.assertTrue(
            all(record["uses_real_app_screens"] for record in self.records)
        )

    def test_every_video_has_a_static_player_videoobject_and_markdown(self) -> None:
        for record in self.records:
            html_path = self.pages / lessons.page_relative(
                record["app_key"],
                record["locale"],
            )
            markdown_path = self.pages / lessons.markdown_relative(
                record["app_key"],
                record["locale"],
            )
            source = html_path.read_text(encoding="utf-8")
            self.assertIn('preload="none"', source)
            self.assertNotIn("autoplay", source)
            self.assertIn(record["video_url"], source)
            self.assertIn(record["thumbnail_url"], source)
            schema_text = source.split(
                '<script type="application/ld+json">', 1
            )[1].split("</script>", 1)[0]
            schema = json.loads(schema_text)
            self.assertEqual("VideoObject", schema["@type"])
            self.assertEqual(record["video_url"], schema["contentUrl"])
            self.assertEqual(record["duration"], schema["duration"])
            self.assertEqual(record["published_at"], schema["uploadDate"])
            self.assertTrue(schema["isAccessibleForFree"])
            self.assertTrue(schema["isFamilyFriendly"])
            store = urllib.parse.urlsplit(record["app_store_url"])
            self.assertEqual("apps.apple.com", store.netloc)
            if self.manifest["campaign_link_attribution_ready"]:
                query = urllib.parse.parse_qs(store.query)
                self.assertTrue(query.get("pt"))
                self.assertTrue(query["ct"][0].startswith("iag_video_"))
                self.assertEqual(["8"], query.get("mt"))
            else:
                self.assertEqual("", store.query)
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn(record["video_url"], markdown)
            self.assertIn(record["app_store_url"], markdown)

    def test_video_sitemap_and_discovery_cover_every_published_video(self) -> None:
        root = ET.parse(self.pages / lessons.SITEMAP_NAME).getroot()
        sitemap_ns = f"{{{lessons.SITEMAP_NS}}}"
        video_ns = f"{{{lessons.VIDEO_NS}}}"
        urls = root.findall(f"{sitemap_ns}url")
        self.assertEqual(
            self.manifest["video_count"] + self.manifest["locale_count"] + 1,
            len(urls),
        )
        video_entries = [
            item
            for item in urls
            if item.find(f"{video_ns}video") is not None
        ]
        self.assertEqual(self.manifest["video_count"], len(video_entries))
        content_urls = {
            item.find(f"{video_ns}video").findtext(f"{video_ns}content_loc")
            for item in video_entries
        }
        self.assertEqual(
            {record["video_url"] for record in self.records},
            content_urls,
        )
        hub_urls = {
            lessons.hub_url(),
            *(lessons.hub_url(locale) for locale in self.manifest["locales"]),
        }
        self.assertTrue(
            hub_urls.issubset(
                {item.findtext(f"{sitemap_ns}loc") for item in urls}
            )
        )
        for locale in self.manifest["locales"]:
            source = (
                self.pages / lessons.hub_relative(locale)
            ).read_text(encoding="utf-8")
            self.assertIn(f'href="{lessons.hub_url()}"', source)
        for relative in (
            "llms.txt",
            "llms-full.txt",
            "robots.txt",
            "sitemap_index.xml",
        ):
            source = (self.pages / relative).read_text(encoding="utf-8")
            self.assertIn(lessons.SITEMAP_NAME, source)


if __name__ == "__main__":
    unittest.main()
