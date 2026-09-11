"""Offline contracts that must pass before daily GEO materialization."""

from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import build_pages_i18n as directories
import high_intent_decision_routes as routes
import live_app_manifest
from official_locales import OFFICIAL_LOCALES


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.alternates = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link" and values.get("rel") == "alternate":
            locale = values.get("hreflang")
            if locale in self.alternates:
                raise AssertionError(f"Duplicate hreflang: {locale}")
            self.alternates[locale] = values.get("href")


class PublicationSourcePreflightTests(unittest.TestCase):
    def test_committed_sync_contract_matches_every_current_generator(self):
        contract = routes.validate_sync_contract()
        self.assertEqual(routes.build_sync_contract(), contract)

    def test_canonical_roster_matches_registered_identities_before_lookup(self):
        roster = live_app_manifest.canonical_manifest()["apps"]
        appstore, registry = live_app_manifest._registry()
        self.assertEqual(47, len(roster))
        for key, app in roster.items():
            with self.subTest(app=key):
                self.assertEqual(app["app_id"], str(appstore[key]))
                self.assertEqual(app["name"], registry[key]["name"])

    def test_directory_hreflang_uses_exact_official_50(self):
        head = Head(directories.directory_hreflang_block(OFFICIAL_LOCALES))
        self.assertEqual(set(OFFICIAL_LOCALES) | {"x-default"}, set(head.alternates))
        for locale in OFFICIAL_LOCALES:
            self.assertEqual(
                f"{directories.SITE}/{locale}/index.html", head.alternates[locale],
            )
        self.assertEqual(f"{directories.SITE}/index.html", head.alternates["x-default"])

    def test_noncanonical_aliases_and_duplicates_cannot_be_generated(self):
        for locales in (
            (), ("da-DK",), ("fi-FI",), ("ja-JP",), ("nb-NO",),
            ("zh-CN",), ("da", "da"), (*OFFICIAL_LOCALES, "da-DK"),
        ):
            with self.subTest(locales=locales), self.assertRaisesRegex(
                ValueError, "unique official locales",
            ):
                directories.directory_hreflang_block(locales)

    def test_regenerating_root_replaces_legacy_aliases_without_touching_app_pages(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            old_root = pages / "index.html"
            old_root.write_text(
                '<html><head><link rel="alternate" hreflang="da-DK" '
                'href="da-DK/index.html"></head><body>Legacy directory</body></html>',
            )
            app = pages / "da/mochi.html"
            app.parent.mkdir()
            app.write_text("Existing localized app content")
            with mock.patch.object(directories, "PAGES", str(pages)):
                directories.build_root_index(OFFICIAL_LOCALES)
                first = old_root.read_bytes()
                directories.build_root_index(OFFICIAL_LOCALES)
            self.assertEqual(first, old_root.read_bytes())
            self.assertEqual("Existing localized app content", app.read_text())
            head = Head(old_root.read_text())
            self.assertEqual(set(OFFICIAL_LOCALES) | {"x-default"}, set(head.alternates))
            self.assertNotIn("da-DK", old_root.read_text())
            self.assertEqual(f"{directories.SITE}/da/index.html", head.alternates["da"])


if __name__ == "__main__":
    unittest.main()
