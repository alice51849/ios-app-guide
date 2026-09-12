"""The paired CEE/Western stack must compose without losing either locale set."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import build_pages_i18n as pages
from cee_locale_copy import CEE_LOCALES
from western_romance_copy import LOCALES as WESTERN_LOCALES
from cee_content_candidates import FIELDS, keys_from_live_ids
from official_locales import OFFICIAL_LOCALES


class LocaleQualityStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        live = json.loads((Path(pages.PAGES) / ".appstore_live_state.json").read_text())
        cls.keys = keys_from_live_ids(live["live_ids"])

    def test_disjoint_20_locale_scope_preserves_exact_source_correction_counts(self):
        self.assertEqual(47, len(self.keys))
        self.assertEqual(set(), set(CEE_LOCALES) & set(WESTERN_LOCALES))
        self.assertEqual(20, len(set(CEE_LOCALES) | set(WESTERN_LOCALES)))
        self.assertEqual(30, len(set(OFFICIAL_LOCALES) - set(CEE_LOCALES) - set(WESTERN_LOCALES)))
        corrections = {"cee": set(), "western": set()}
        cells = {"cee": set(), "western": set()}
        for key in self.keys:
            for locale in OFFICIAL_LOCALES:
                actual = pages.external_localized_values(key, locale)
                with (
                    mock.patch.object(pages, "cee_reviewed_values", side_effect=lambda key, locale, values: values),
                    mock.patch.object(pages.western_romance_copy, "external_values", side_effect=lambda key, locale, values, app: values),
                ):
                    original = pages.external_localized_values(key, locale)
                changed = {field for field in FIELDS if original[field] != actual[field]}
                if locale in CEE_LOCALES:
                    group = "cee"
                elif locale in WESTERN_LOCALES:
                    group = "western"
                else:
                    self.assertEqual(original, actual, (key, locale))
                    continue
                if changed:
                    cells[group].add((key, locale))
                    corrections[group].update((key, locale, field) for field in changed)
        self.assertEqual((107, 431), (len(cells["cee"]), len(corrections["cee"])))
        self.assertEqual((170, 525), (len(cells["western"]), len(corrections["western"])))
        self.assertFalse(corrections["cee"] & corrections["western"])
        self.assertEqual(277, len(cells["cee"] | cells["western"]))
        self.assertEqual(956, len(corrections["cee"] | corrections["western"]))

    def test_each_hook_is_identity_on_the_other_batch(self):
        for key in self.keys:
            for locale in (*CEE_LOCALES, *WESTERN_LOCALES):
                merged = pages.external_localized_values(key, locale)
                patch = (
                    mock.patch.object(pages.western_romance_copy, "external_values", side_effect=lambda key, locale, values, app: values)
                    if locale in CEE_LOCALES else
                    mock.patch.object(pages, "cee_reviewed_values", side_effect=lambda key, locale, values: values)
                )
                with patch:
                    single_batch = pages.external_localized_values(key, locale)
                self.assertEqual(merged, single_batch, (key, locale))


if __name__ == "__main__":
    unittest.main()
