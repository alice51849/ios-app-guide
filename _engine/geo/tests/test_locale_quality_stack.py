"""CEE, Western and CJK must compose without losing reviewed field truth."""
from contextlib import ExitStack
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
from cjk_geo_p002 import TARGET_CELLS, REPAIRED_LOCALES


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
        self.assertFalse(set(REPAIRED_LOCALES) & (set(CEE_LOCALES) | set(WESTERN_LOCALES)))
        corrections = {"cee": set(), "western": set(), "cjk": set()}
        cells = {"cee": set(), "western": set(), "cjk": set()}
        for key in self.keys:
            for locale in OFFICIAL_LOCALES:
                actual = pages.external_localized_values(key, locale)
                with (
                    mock.patch.object(pages, "cee_reviewed_values", side_effect=lambda key, locale, values: values),
                    mock.patch.object(pages.western_romance_copy, "external_values", side_effect=lambda key, locale, values, app: values),
                    mock.patch.object(pages.cjk_geo_p002, "external_values", side_effect=lambda key, locale, values, **facts: values),
                ):
                    original = pages.external_localized_values(key, locale)
                changed = {field for field in FIELDS if original[field] != actual[field]}
                if locale in CEE_LOCALES:
                    group = "cee"
                elif locale in WESTERN_LOCALES:
                    group = "western"
                elif (key, locale) in TARGET_CELLS:
                    group = "cjk"
                    self.assertEqual(changed, {"description"})
                else:
                    self.assertEqual(original, actual, (key, locale))
                    continue
                if changed:
                    cells[group].add((key, locale))
                    corrections[group].update((key, locale, field) for field in changed)
        self.assertEqual((107, 431), (len(cells["cee"]), len(corrections["cee"])))
        self.assertEqual((170, 525), (len(cells["western"]), len(corrections["western"])))
        self.assertEqual((12, 12), (len(cells["cjk"]), len(corrections["cjk"])))
        self.assertEqual(cells["cjk"], TARGET_CELLS)
        self.assertFalse(corrections["cee"] & corrections["western"])
        self.assertFalse(corrections["cjk"] & (corrections["cee"] | corrections["western"]))
        self.assertEqual(277, len(cells["cee"] | cells["western"]))
        self.assertEqual(956, len(corrections["cee"] | corrections["western"]))
        self.assertEqual(289, len(set().union(*cells.values())))
        self.assertEqual(968, len(set().union(*corrections.values())))

    def test_each_hook_is_identity_on_the_other_batch(self):
        targets = {(key, locale) for key in self.keys for locale in (*CEE_LOCALES, *WESTERN_LOCALES)} | TARGET_CELLS
        for key, locale in targets:
            merged = pages.external_localized_values(key, locale)
            with ExitStack() as patches:
                if locale not in CEE_LOCALES:
                    patches.enter_context(mock.patch.object(pages, "cee_reviewed_values", side_effect=lambda key, locale, values: values))
                if locale not in WESTERN_LOCALES:
                    patches.enter_context(mock.patch.object(pages.western_romance_copy, "external_values", side_effect=lambda key, locale, values, app: values))
                if (key, locale) not in TARGET_CELLS:
                    patches.enter_context(mock.patch.object(pages.cjk_geo_p002, "external_values", side_effect=lambda key, locale, values, **facts: values))
                single_batch = pages.external_localized_values(key, locale)
            self.assertEqual(merged, single_batch, (key, locale))


if __name__ == "__main__":
    unittest.main()
