"""檔期意圖頁（2026-10-23 預製）：下載連結、追蹤碼、禁用字、內容長度、sitemap 合併（離線）。"""

from __future__ import annotations

import html
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_seasonal_peaks_2026 as gen  # noqa: E402
import gw_campaign  # noqa: E402
from app_store_storefronts import validated_app_store_url  # noqa: E402


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = gen.store_names()
        cls.pages = gen.build({}, names=cls.names)

    def test_every_event_has_pages_and_slugs_are_unique(self):
        self.assertEqual(len(self.pages), len(gen.PAGE_SPECS))
        events = {spec["event"] for spec in gen.PAGE_SPECS}
        for event in ("halloween", "singles_day", "suneung", "thanksgiving", "black_friday"):
            self.assertIn(event, events)

    def test_every_card_links_to_its_own_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[gen.page_relative(spec)]
            info = gen.LANGS[spec["lang"]]
            cards = re.findall(r'<article class="app" id="app-([a-z0-9]+)">(.*?)</article>', source, re.S)
            self.assertEqual([key for key, _ in spec["cards"]], [key for key, _ in cards])
            for key, body in cards:
                href = html.unescape(re.search(r'class="dl" href="([^"]+)"', body).group(1))
                validated_app_store_url(href, gen.APP_IDS[key], expected_locale=info["store"], require_campaign=True)
                query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(href).query))
                self.assertEqual(query["pt"], gen.PROVIDER_TOKEN)
                self.assertEqual(query["ct"], gw_campaign.campaign(key, "ss", info["cc"]))
                self.assertLessEqual(len(query["ct"]), gen.MAX_CT)
            self.assertIn(gw_campaign.meta_tag("ss"), source)  # 每日改寫照這個詞群標記保留 gw 碼

    def test_campaign_is_the_gw_ladder_code_without_a_date(self):
        for key, event, cc in (("mochi", "halloween", "us"), ("countdaysnow", "suneung", "kr"),
                               ("hourstaglite", "singles_day", "id")):
            token = gen.campaign(key, event, cc)
            self.assertEqual(gw_campaign.campaign(key, "ss", cc), token)
            self.assertRegex(token, rf"^ln_{key}_(ss|all)_({cc}|ww)_gw$")
        with self.assertRaises(KeyError):
            gen.campaign("mochi", "no_such_event", "us")

    def test_no_price_free_or_pro_wording_outside_store_names(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[gen.page_relative(spec)]
            self.assertEqual([], [p for p in gen.page_problems(spec, source, names=self.names) if "banned" in p])

    def test_banned_wording_is_caught(self):
        spec = dict(gen.PAGE_SPECS[0], intro=["Totally free for everyone."])
        source = gen.render(spec, self.names)
        self.assertTrue(any("banned" in p for p in gen.page_problems(spec, source, names=self.names)))
        spec = dict(gen.PAGE_SPECS[0], intro=["Get the Pro version."])
        source = gen.render(spec, self.names)
        self.assertTrue(any("banned" in p for p in gen.page_problems(spec, source, names=self.names)))

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[gen.page_relative(spec)]
            self.assertGreaterEqual(gen.dedicated_size(spec["lang"], gen.visible_text(source)),
                                    gen.FLOORS[spec["lang"]], spec["slug"])

    def test_title_or_h1_uses_the_lead_search_term(self):
        for spec in gen.PAGE_SPECS:
            lead_term = spec["terms"][0].replace(" ", "").casefold()
            joined = (spec["title"] + spec["h1"] + spec["desc"]).replace(" ", "").casefold()
            self.assertIn(lead_term, joined, spec["slug"])

    def test_launch_rows_cover_every_card(self):
        rows = gen.launches()
        self.assertEqual(len(rows), sum(len(spec["cards"]) for spec in gen.PAGE_SPECS))
        for row in rows:
            self.assertTrue(row["url"].startswith(gen.SITE + "/"))
            self.assertIn("ct=ln_", row["store_url"])


class SitemapTests(unittest.TestCase):
    def test_merge_adds_missing_rows_once(self):
        base = '<?xml version="1.0"?>\n<urlset>\n<url><loc>https://x/a.html</loc></url>\n</urlset>\n'
        merged = gen.merge_sitemap(base, ["https://x/a.html", "https://x/b.html"])
        self.assertEqual(merged.count("<loc>https://x/b.html</loc>"), 1)
        self.assertEqual(gen.merge_sitemap(merged, ["https://x/b.html"]), merged)


if __name__ == "__main__":
    unittest.main()
