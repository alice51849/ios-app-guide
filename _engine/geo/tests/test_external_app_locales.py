#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
if GEO not in sys.path:
    sys.path.insert(0, GEO)

import build_pages_i18n as pages
from external_app_locales import EXTERNAL_APP_LOCALES
from official_locales import OFFICIAL_LOCALE_SET
from videogen.registry import APPSTORE


EXPECTED_LOCALES = {
    "mochi": {"en-US", "ja", "zh-Hant", "ko", "hi", "nl-NL", "sk"},
    "sereno": {"en-US", "zh-Hant", "sk"},
    "tripbee": {"en-US", "zh-Hant", "sk"},
    "tripplanet": {"en-US", "zh-Hant", "sk"},
}


class ExternalAppLocaleTests(unittest.TestCase):
    def test_metadata_excerpts_do_not_cut_slovak_words(self):
        source = (
            "Offline cestovateľské hry a balenie pre deti od 4 do 10 rokov"
        )
        excerpt = pages._word_bounded_excerpt(source, 60)
        self.assertLessEqual(len(excerpt), 60)
        self.assertTrue(source.startswith(excerpt))
        self.assertTrue(source[len(excerpt)].isspace())

    def test_metadata_excerpts_do_not_split_unicode_clusters(self):
        thai = "ภาพถ่ายที่มืดจะดูสว่างขึ้นอย่างเป็นธรรมชาติ"
        thai_limit = thai.index("ึ")
        thai_excerpt = pages._word_bounded_excerpt(thai, thai_limit)
        self.assertEqual(thai[:thai.index("ข")], thai_excerpt)

        marathi = "फोटोची पार्श्वभूमी स्वच्छ आणि नैसर्गिक दिसते"
        marathi_limit = marathi.index("्")
        marathi_excerpt = pages._word_bounded_excerpt(
            marathi, marathi_limit
        )
        self.assertEqual("फोटोची", marathi_excerpt)

        family = "abc👩‍👩‍👧‍👦xyz"
        family_excerpt = pages._word_bounded_excerpt(family, 4)
        self.assertEqual("abc", family_excerpt)

    def test_metadata_excerpts_keep_complete_words_at_safe_boundaries(self):
        punctuation = "Mochi keeps every task easy to scan, even on busy days"
        punctuation_limit = punctuation.index(",")
        self.assertEqual(
            "Mochi keeps every task easy to scan",
            pages._word_bounded_excerpt(punctuation, punctuation_limit),
        )

        whitespace = "काम पूर्ण म्हणून चिह्नित करा"
        whitespace_limit = whitespace.index(" ", whitespace.index("चिह्नित"))
        self.assertEqual(
            "काम पूर्ण म्हणून चिह्नित",
            pages._word_bounded_excerpt(whitespace, whitespace_limit),
        )

    def test_curated_guides_cover_new_live_app_buyer_languages(self):
        self.assertEqual(set(EXTERNAL_APP_LOCALES), set(EXPECTED_LOCALES))
        for key, expected in EXPECTED_LOCALES.items():
            locales = pages.load_app_locales(key)
            self.assertEqual(OFFICIAL_LOCALE_SET, set(locales))
            self.assertTrue(expected.issubset(locales))
            for locale, content in locales.items():
                with self.subTest(key=key, locale=locale):
                    minimum = 160 if locale in {"ja", "zh-Hant", "ko"} else 240
                    self.assertGreaterEqual(len(content["description"]), minimum)
                    self.assertGreaterEqual(
                        content["description"].count("\n\n"), 2
                    )
                    self.assertGreaterEqual(
                        len(pages.split_keywords(content["keywords"])),
                        8 if locale in expected else 5,
                    )
                    self.assertTrue(content["name"].strip())
                    self.assertTrue(content["subtitle"].strip())

    def test_curated_copy_never_overrides_future_full_locale_data(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "mochi_full.json").write_text(
                json.dumps(
                    {
                        "ja": {
                            "name": "Future official name",
                            "description": "Future full description",
                        }
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(pages, "DATA", directory), mock.patch.dict(
                pages.KEY2DATA, {"mochi": "mochi_full.json"}
            ):
                locales = pages.load_app_locales("mochi")
        self.assertEqual("Future official name", locales["ja"]["name"])
        self.assertEqual(
            "Future full description", locales["ja"]["description"]
        )
        self.assertEqual(
            EXTERNAL_APP_LOCALES["mochi"]["ja"]["subtitle"],
            locales["ja"]["subtitle"],
        )
        self.assertIn("zh-Hant", locales)

    def test_generated_pages_are_native_linked_and_direct(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            pages, "PAGES", directory
        ):
            for key, expected in EXPECTED_LOCALES.items():
                localizations = pages.load_app_locales(key)
                all_locales = list(localizations)
                for locale in all_locales:
                    output = pages.build_one(key, locale, all_locales)
                    content = Path(output).read_text(encoding="utf-8")
                    localized = pages.external_localized_values(
                        key,
                        locale,
                        localizations,
                    )
                    with self.subTest(key=key, locale=locale):
                        self.assertIn(f'<html lang="{locale}"', content)
                        self.assertIn(
                            localized["subtitle"].replace("&", "&amp;"),
                            content,
                        )
                        self.assertIn(
                            f"https://apps.apple.com/app/id{APPSTORE[key]}",
                            content,
                        )
                        self.assertEqual(
                            len(all_locales),
                            content.count(
                                '<link rel="alternate" hreflang="'
                            )
                            - 1,
                        )
                        self.assertIn('hreflang="x-default"', content)
                        if locale == "sk":
                            self.assertIn("<h2>Hlavné funkcie</h2>", content)
                            self.assertIn("<h2>Časté otázky</h2>", content)
                            self.assertIn("<h2>Stiahnuť</h2>", content)
                            self.assertIn('"@type": "FAQPage"', content)

    def test_slovak_directory_is_native_and_feed_discoverable(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(pages, "PAGES", directory),
            mock.patch.object(
                pages,
                "directory_icon_url",
                return_value=(
                    f"{pages.SITE}/stories/img/mochi-icon.jpg"
                ),
            ),
        ):
            pages.build_locale_index("sk", ["mochi"], ["sk"])
            content = Path(directory, "sk", "index.html").read_text(
                encoding="utf-8"
            )
        self.assertIn("<title>Katalóg aplikácií | iOS</title>", content)
        self.assertIn("<h1>Katalóg aplikácií</h1>", content)
        self.assertIn('type="application/atom+xml"', content)
        self.assertIn('type="application/rss+xml"', content)
        self.assertIn('type="application/feed+json"', content)

    def test_external_categories_have_specific_schema_types(self):
        self.assertEqual(
            "LifestyleApplication", pages.SCHEMA_CAT["sleep-sound"]
        )
        self.assertEqual("TravelApplication", pages.SCHEMA_CAT["travel"])


if __name__ == "__main__":
    unittest.main()
