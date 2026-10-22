"""搜尋實況意圖頁（第 3 組）：下載連結、追蹤碼、禁用字、內容長度、sitemap 合併（離線）。"""

from __future__ import annotations

import html
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_search_reality_g3 as gen  # noqa: E402
from app_store_storefronts import validated_app_store_url  # noqa: E402


def build():
    return gen.build({})


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build()

    def test_one_page_per_app_and_unique_slugs(self):
        keys = [spec["key"] for spec in gen.PAGE_SPECS]
        self.assertEqual(sorted(keys), sorted(gen.APP_IDS))
        self.assertEqual(len(self.pages), len(gen.PAGE_SPECS))

    def test_every_card_links_to_its_own_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[gen.page_relative(spec)]
            info = gen.LANGS[spec["lang"]]
            cards = re.findall(r'<article class="app" id="app-([a-z0-9]+)">(.*?)</article>', source, re.S)
            self.assertTrue(cards)
            for key, body in cards:
                href = html.unescape(re.search(r'class="dl" href="([^"]+)"', body).group(1))
                validated_app_store_url(href, gen.APP_IDS[key], expected_locale=info["store"], require_campaign=True)
                query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(href).query))
                self.assertEqual(query["pt"], gen.PROVIDER_TOKEN)
                self.assertTrue(query["ct"].startswith(f"ln_{key}_sr_{info['cc']}_gw"))
                self.assertLessEqual(len(query["ct"]), gen.MAX_CT)

    def test_campaign_drops_date_only_when_too_long(self):
        self.assertEqual(gen.campaign("gmoney", "tw"), "ln_gmoney_sr_tw_gw_1023")
        self.assertEqual(gen.campaign("claudeusagemini", "us"), "ln_claudeusagemini_sr_us_gw")

    def test_no_price_free_or_pro_wording(self):
        for relative, source in self.pages.items():
            text = gen.visible_text(source) + source.split("</head>", 1)[0]
            text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S)
            self.assertIsNone(gen.BANNED.search(html.unescape(text)), relative)

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[gen.page_relative(spec)]
            floor = gen.MIN_CJK if spec["lang"] in ("zh-Hant", "zh-Hans", "ja") else gen.MIN_WORDS
            self.assertGreaterEqual(gen.dedicated_size(spec["lang"], gen.visible_text(source)), floor)

    def test_banned_wording_is_caught(self):
        spec = dict(gen.PAGE_SPECS[1], intro=["Totally free for everyone."])
        source = gen.render(spec, gen.store_names())
        self.assertTrue(any("banned" in p for p in gen.page_problems(spec, source)))

    def test_title_and_h1_use_search_terms(self):
        for spec in gen.PAGE_SPECS:
            lead_term = spec["terms"][0].replace(" ", "").casefold()
            joined = (spec["title"] + spec["h1"] + spec["desc"]).replace(" ", "").casefold()
            self.assertIn(lead_term, joined, spec["slug"])


class SitemapTests(unittest.TestCase):
    def test_merge_adds_missing_rows_once(self):
        base = '<?xml version="1.0"?>\n<urlset>\n<url><loc>https://x/a.html</loc></url>\n</urlset>\n'
        merged = gen.merge_sitemap(base, ["https://x/a.html", "https://x/b.html"])
        self.assertEqual(merged.count("<loc>https://x/b.html</loc>"), 1)
        self.assertEqual(gen.merge_sitemap(merged, ["https://x/b.html"]), merged)


if __name__ == "__main__":
    unittest.main()
