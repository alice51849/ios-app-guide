"""Opt-in Chromium DOM gate; no Simulator or external page requests.

Install requirements-cee-render.txt and Chromium into a project-owned validation
environment, then run ``python -m unittest geo.tests.cee_hebrew_render`` with
TMPDIR and PLAYWRIGHT_BROWSERS_PATH set to project-owned scratch directories.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_pages_i18n as pages
from cee_content_candidates import build_inventory, keys_from_live_ids


class CEEHebrewRenderTests(unittest.TestCase):
    def test_all_47_hebrew_pages_and_plaintext_previews(self):
        live = json.loads((Path(pages.PAGES) / ".appstore_live_state.json").read_text())
        keys = keys_from_live_ids(live["live_ids"])
        rows = {row["app_key"]: row for row in build_inventory(keys) if row["locale"] == "he"}
        self.assertEqual(47, len(rows))
        with (
            tempfile.TemporaryDirectory() as output,
            mock.patch.object(pages, "PAGES", output),
            sync_playwright() as playwright,
        ):
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 430, "height": 932})
                page.route("**/*", lambda route: route.abort())
                for key, row in rows.items():
                    with self.subTest(app=key):
                        candidate = pages.build_one(key, "he", pages.all_locales_for(key))
                        page.set_content(Path(candidate).read_text(), wait_until="domcontentloaded")
                        result = page.evaluate("""() => ({
                            language: document.documentElement.lang,
                            direction: getComputedStyle(document.querySelector('main')).direction,
                            heading: document.querySelector('h1').textContent,
                            isolates: [...document.querySelectorAll('main bdi')].map(node => ({
                                direction: getComputedStyle(node).direction,
                                bidi: getComputedStyle(node).unicodeBidi,
                                text: node.textContent
                            }))
                        })""")
                        self.assertEqual("he", result["language"])
                        self.assertEqual("rtl", result["direction"])
                        self.assertEqual(row["name"], result["heading"])
                        self.assertTrue(result["isolates"])
                        for isolate in result["isolates"]:
                            self.assertEqual("ltr", isolate["direction"])
                            self.assertEqual("isolate", isolate["bidi"])
                            self.assertTrue(isolate["text"])
                        preview = page.evaluate("""text => {
                            const node = document.createElement('p');
                            node.dir = 'auto';
                            node.textContent = text;
                            document.body.append(node);
                            return {direction: getComputedStyle(node).direction, text: node.textContent};
                        }""", row["social_preview"])
                        self.assertEqual("rtl", preview["direction"])
                        self.assertEqual(row["social_preview"], preview["text"])
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
