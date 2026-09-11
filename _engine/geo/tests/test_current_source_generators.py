from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "geo"), str(ROOT / "social")]
import alternatives_i18n
import app_install_decision_routes
import build_pages_i18n
import current_source
import gen_hubs
from answer_personas import PERSONAS
from videogen.registry import APPS, APPSTORE

PAGES = Path(os.environ.get("GEO_PAGES", ROOT / "geo" / "pages"))
INVENTORY = PAGES / "data" / "verified-ios-app-finder-catalog.json"


class CurrentSourceGeneratorTests(unittest.TestCase):
    def test_all_five_families_use_the_exact_47_by_50_eligibility(self):
        source = current_source.load_source()
        expected = set(current_source.campaign_pairs())
        app_pairs = {
            (key, locale) for key in APPSTORE
            for locale in build_pages_i18n.all_locales_for(key)
        }
        hubs = gen_hubs.authority_apps()
        _, decisions = app_install_decision_routes.build_records(PAGES)
        alternatives = alternatives_i18n.load_inventory(
            INVENTORY, alternatives_i18n.load_manifest(),
        )
        families = {
            "app": set(APPS), "hub": set(hubs), "decision": set(decisions),
            "alternatives": set(alternatives), "persona": set(PERSONAS),
        }
        self.assertEqual(expected, app_pairs)
        for family, keys in families.items():
            with self.subTest(family=family):
                self.assertEqual(set(source["apps"]), keys)
                self.assertEqual(
                    expected, {(key, locale) for key in keys for locale in source["locales"]},
                )
                self.assertTrue({"zipbox", "battai"} <= keys)
                self.assertFalse({"zodira", "zafe"} & keys)

    def test_decision_generator_emits_all_2350_pairs_without_writing_content(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("No network")):
            with mock.patch.dict(os.environ, {"APP_STORE_PROVIDER_TOKEN": "123456"}):
                records, _ = app_install_decision_routes.build_records(PAGES)
        pairs = {(record["app_key"], record["locale"]) for record in records}
        self.assertEqual(2350, len(records))
        self.assertEqual(set(current_source.campaign_pairs()), pairs)
        for key in ("zipbox", "battai"):
            self.assertEqual(50, sum(app == key for app, _ in pairs))

    def test_zipbox_and_battai_materialize_native_app_and_hub_pages_for_every_locale(self):
        locales = current_source.load_source()["locales"]
        with ExitStack() as stack:
            stage = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            stack.enter_context(mock.patch.object(build_pages_i18n, "PAGES", str(stage)))
            stack.enter_context(mock.patch.object(gen_hubs, "PAGES", str(stage)))
            stack.enter_context(mock.patch.dict(os.environ, {"APP_STORE_PROVIDER_TOKEN": "123456"}))
            stack.enter_context(mock.patch("urllib.request.urlopen", side_effect=AssertionError("No network")))
            for key in ("zipbox", "battai"):
                for locale in locales:
                    with self.subTest(app=key, locale=locale):
                        build_pages_i18n.build_one(key, locale, locales)
                        page = (stage / locale / f"{key}.html").read_text()
                        self.assertIn(f'lang="{locale}"', page)
                        self.assertIn(APPSTORE[key], page)
                        self.assertNotIn('content="true" name="iag-nonlive"', page)
                        hub = gen_hubs.build_localized_hub(key, locale, availability={})
                        self.assertIn(f'lang="{locale}"', hub)
                        self.assertIn(APPSTORE[key], hub)
                        self.assertIn(f"/{locale}/{key}.html", hub)


if __name__ == "__main__":
    unittest.main()
