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
from videogen.registry import APPS, APPSTORE


EXPECTED_LOCALES = {
    "mochi": {"en-US", "ja", "zh-Hant", "ko", "hi", "nl-NL"},
    "sereno": {"en-US", "zh-Hant"},
    "tripbee": {"en-US", "zh-Hant"},
    "tripplanet": {"en-US", "zh-Hant"},
}


class ExternalAppLocaleTests(unittest.TestCase):
    def test_curated_guides_cover_new_live_app_buyer_languages(self):
        self.assertEqual(set(EXTERNAL_APP_LOCALES), set(EXPECTED_LOCALES))
        for key, expected in EXPECTED_LOCALES.items():
            locales = pages.load_app_locales(key)
            self.assertEqual(expected, set(locales))
            for locale, content in locales.items():
                with self.subTest(key=key, locale=locale):
                    minimum = 160 if locale in {"ja", "zh-Hant", "ko"} else 240
                    self.assertGreaterEqual(len(content["description"]), minimum)
                    self.assertGreaterEqual(
                        content["description"].count("\n\n"), 2
                    )
                    self.assertGreaterEqual(
                        len(pages.split_keywords(content["keywords"])), 8
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
                all_locales = list(pages.load_app_locales(key))
                for locale in all_locales:
                    output = pages.build_one(key, locale, all_locales)
                    content = Path(output).read_text(encoding="utf-8")
                    localized = EXTERNAL_APP_LOCALES[key][locale]
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
                        if locale != "en-US":
                            self.assertNotIn(APPS[key]["sub"], content)

    def test_external_categories_have_specific_schema_types(self):
        self.assertEqual(
            "LifestyleApplication", pages.SCHEMA_CAT["sleep-sound"]
        )
        self.assertEqual("TravelApplication", pages.SCHEMA_CAT["travel"])


if __name__ == "__main__":
    unittest.main()
