import html
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import android_play  # noqa: E402
import gen_store_attribution as attribution  # noqa: E402
import web_tools_pilot as pilot  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PROVIDER = "118326163"
INDEX = '<html><body><section class="wrap grid"><article class="card third"><h2><a href="x.html">X</a></h2></article></section></body></html>'
NETWORK_RE = re.compile(r"\bfetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|<form\b|\.submit\(")
PRICE_WORDS_RE = re.compile(r"\bfree\b|免費|無料|\bpro\b|\$\s?\d|NT\$|¥|\d\s?円", re.IGNORECASE)


def visible_text(page: str) -> str:
    body = page.split("<body>", 1)[1]
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


class WebToolsPilotTest(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.get("APP_STORE_PROVIDER_TOKEN")
        os.environ["APP_STORE_PROVIDER_TOKEN"] = PROVIDER

    def tearDown(self):
        if self._env is None:
            os.environ.pop("APP_STORE_PROVIDER_TOKEN", None)
        else:
            os.environ["APP_STORE_PROVIDER_TOKEN"] = self._env

    def build(self, live=("duowallpaperstudio", "snapport"), android=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pages = Path(tmp.name)
        for locale in pilot.LOCALES:
            index = pages / ("" if locale == "en" else locale) / "tools" / "index.html"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(INDEX, encoding="utf-8")
        outputs = pilot.build(pages, live_keys=set(live), android_apps=android)
        return pages, outputs

    def pages(self, root):
        for tool in pilot.TOOLS:
            for locale in pilot.LOCALES:
                yield tool, locale, (root / pilot.page_path(tool["slug"], locale)).read_text(encoding="utf-8")

    def test_two_tools_three_locales_indexable_under_public_site(self):
        root, outputs = self.build()
        self.assertEqual(6, len(outputs))
        self.assertEqual(("en", "zh-Hant", "ja"), pilot.LOCALES)
        for tool, locale, page in self.pages(root):
            url = pilot.canonical(tool["slug"], locale)
            self.assertTrue(url.startswith(PUBLIC_SITE.rstrip("/") + "/"))
            self.assertIn(f'<link rel="canonical" href="{url}">', page)
            self.assertIn('<meta name="robots" content="index,follow">', page)
            self.assertNotIn("noindex", page)
            self.assertIn(f'<html lang="{locale}">', page)
            for code in pilot.LOCALES:
                self.assertIn(
                    f'hreflang="{code}" href="{pilot.canonical(tool["slug"], code)}"', page
                )
            self.assertIn('hreflang="x-default"', page)

    def test_pages_never_send_images_anywhere(self):
        root, _ = self.build()
        for _tool, _locale, page in self.pages(root):
            scripts = "".join(re.findall(r"<script>(.*?)</script>", page, flags=re.S))
            self.assertTrue(scripts)
            self.assertIsNone(NETWORK_RE.search(page))
            self.assertIn("createObjectURL", scripts)

    def test_no_price_free_or_pro_wording(self):
        root, _ = self.build()
        for _tool, _locale, page in self.pages(root):
            self.assertIsNone(PRICE_WORDS_RE.search(visible_text(page)))
            self.assertNotIn('"offers"', page)
            self.assertNotIn("isAccessibleForFree", page)

    def test_passport_pages_state_photo_only_disclaimer(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            if tool is not pilot.PASSPORT:
                continue
            self.assertIn(html.escape(tool["copy"][locale]["disclaimer"], quote=True), page)
            for key in ("us", "tw", "jp"):
                self.assertIn(f'<option value="{key}">', page)
        presets = pilot.PASSPORT_PRESETS
        self.assertEqual((50.8, 50.8), (presets["us"]["w"], presets["us"]["h"]))
        self.assertEqual((35.0, 45.0), (presets["tw"]["w"], presets["tw"]["h"]))
        self.assertEqual((35.0, 45.0), (presets["jp"]["w"], presets["jp"]["h"]))

    def test_app_store_cta_keeps_app_bound_campaign(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            token = f'{tool["campaign"]}_{locale.replace("-", "_").lower()}'
            app_id = attribution.APP_BOUND_CAMPAIGNS[token]
            self.assertTrue(attribution.app_bound_campaign(token, app_id))
            links = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', page)
            self.assertEqual(1, len(links))
            link = html.unescape(links[0])
            self.assertIn(f"/id{app_id}?", link)
            self.assertIn(f"ct={token}", link)
            again = attribution.final_store_url(
                link, "geo_learn", PROVIDER, locale=pilot.STAMP_LOCALE[locale], app_id=app_id
            )
            self.assertIn(f"ct={token}", again)
        self.assertFalse(attribution.app_bound_campaign("tool_duo_pair_en", "6780575828"))

    def test_cta_hidden_when_app_not_live(self):
        root, _ = self.build(live=())
        for _tool, _locale, page in self.pages(root):
            self.assertNotIn("apps.apple.com", page)

    def test_google_play_link_added_with_matching_referrer(self):
        android = android_play.load_snapshot()
        self.assertIn("duowallpaperstudio", android)
        root, _ = self.build(android=android)
        for tool, locale, page in self.pages(root):
            if tool["app"] not in android:
                continue
            token = f'{tool["campaign"]}_{locale.replace("-", "_").lower()}'
            self.assertIn(android[tool["app"]]["package"], page)
            self.assertIn(f"utm_source%3D{token}", page)

    def test_tools_index_cards_are_idempotent(self):
        root, _ = self.build()
        pilot.build(root, live_keys={"duowallpaperstudio", "snapport"})
        for locale in pilot.LOCALES:
            index = (root / ("" if locale == "en" else locale) / "tools" / "index.html").read_text(encoding="utf-8")
            for tool in pilot.TOOLS:
                self.assertEqual(1, index.count(f'href="{tool["slug"]}.html"'))

    def test_duo_samples_are_relative_same_site_files(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            if tool is not pilot.DUO:
                continue
            depth = "../" if locale == "en" else "../../"
            for key in pilot.SAMPLES:
                self.assertIn(f'"{depth}{pilot.SAMPLE_DIR}/{key}-outer.jpg"', page)


if __name__ == "__main__":
    unittest.main()
