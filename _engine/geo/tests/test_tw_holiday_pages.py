"""台灣連假意圖頁＋ iPhone Duo 滿版清單：宣稱閘門、下載連結、追蹤碼、內容長度（離線、不讀線上清單）。"""

from __future__ import annotations

import html
import json
from pathlib import Path
import re
import sys
import unittest
import urllib.parse

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_tw_holiday_pages as gen  # noqa: E402
from app_store_storefronts import validated_app_store_url  # noqa: E402

# Synthetic ids: every content key gets one; the claim gate is driven by CLAIMABLE only.
IDS = {key: str(6700000000 + number) for number, key in enumerate(sorted(gen.NAMES), 1)}
BADGE = "已針對 iPhone Duo 最佳化，真正滿版。"


def build(claimable_keys):
    claimable = {key: IDS[key] for key in claimable_keys}
    return gen.build(claimable, IDS, {}, badge=BADGE)


def duo_page(pages):
    return pages[gen.page_relative(gen.DUO_SLUG)]


def card_keys(source):
    return re.findall(r'<article class="app" id="app-([a-z0-9]+)"', source)


class ClaimGateTests(unittest.TestCase):
    def test_duo_page_lists_exactly_the_claimable_apps(self):
        claimable = set(gen.DUO_LINES) - {"lockhour", "mochi"}
        page = duo_page(build(claimable))
        self.assertEqual(sorted(card_keys(page)), sorted(claimable))
        self.assertNotIn("app-lockhour", page)
        self.assertNotIn("battai", page.lower())

    def test_scenario_cards_carry_the_claim_only_when_claimable(self):
        pages = build(set(gen.DUO_LINES) - {"mochi"})
        clean = pages[gen.page_relative(gen.CLEAN_SLUG)]
        mochi = re.search(r'<article class="app" id="app-mochi">.*?</article>', clean, re.S).group(0)
        picclear = re.search(r'<article class="app" id="app-picclear">.*?</article>', clean, re.S).group(0)
        self.assertNotIn("iPhone Duo", mochi)
        self.assertIn(BADGE, picclear)

    def test_duo_page_states_the_claim_once(self):
        page = duo_page(build(gen.DUO_LINES))
        self.assertEqual(1, page.count(f'<p class="duo-badge">{BADGE}</p>'))

    def test_every_listed_app_has_a_line_and_one_group(self):
        grouped = [key for _, keys in gen.DUO_GROUPS for key in keys]
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(set(grouped), set(gen.DUO_LINES))
        self.assertLessEqual(set(gen.DUO_LINES), set(gen.NAMES))

    def test_live_version_mismatch_refuses_the_claim(self):
        apps = [{"slug": "mochi", "app_id": "1", "live_version": "1.0.16", "source_key": "M"},
                {"slug": "tripbee", "app_id": "2", "live_version": "1.0.8", "source_key": "T"}]
        claimable, refused = gen.claimable_apps(load=lambda: (apps, [], None),
                                                versions={"1": "1.0.16", "2": "1.0.9"})
        self.assertEqual({"mochi": "1"}, claimable)
        self.assertEqual(["T"], [r["source_key"] for r in refused])

    def test_unreadable_claim_list_stops_generation(self):
        with self.assertRaises(gen.GenerationError):
            gen.claimable_apps(load=lambda: ([], [], "broken"), versions={})


class LinkAndContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build(gen.DUO_LINES)

    def test_every_card_has_a_tracked_taiwan_store_link(self):
        for relative, source in self.pages.items():
            spec = next(s for s in gen.PAGE_SPECS if gen.page_relative(s["slug"]) == relative)
            for card in re.findall(r'<article class="app"[^>]*>.*?</article>', source, re.S):
                hrefs = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', card)
                self.assertEqual(1, len(hrefs), relative)
                url = html.unescape(hrefs[0])
                validated_app_store_url(url, expected_locale="zh-Hant", require_campaign=True)
                ct = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))["ct"]
                self.assertLessEqual(len(ct), gen.MAX_CT)
                self.assertRegex(ct, rf"^ln_[a-z0-9]+_{spec['seg']}_tw_gw(?:_1023)?$")

    def test_campaign_keeps_the_date_when_it_fits(self):
        self.assertEqual("ln_mochi_clean_tw_gw_1023", gen.campaign("mochi", "clean"))
        self.assertEqual("ln_claudeusagemini_study_tw_gw", gen.campaign("claudeusagemini", "study"))

    def test_no_price_or_free_wording_and_enough_dedicated_text(self):
        for relative, source in self.pages.items():
            text = gen.visible_text(source)
            self.assertGreaterEqual(len(gen.CJK.findall(text)), 450, relative)
            self.assertIsNone(gen.BANNED.search(text), relative)
            self.assertEqual([], gen.page_problems(relative, source), relative)

    def test_pages_link_each_other_and_carry_the_trademark_notice_once(self):
        for relative, source in self.pages.items():
            others = [gen.url_for(r) for r in self.pages if r != relative]
            self.assertTrue(any(url in source for url in others), relative)
        self.assertEqual(1, duo_page(self.pages).count(gen.LEGAL))

    def test_structured_data_parses(self):
        for relative, source in self.pages.items():
            block = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', source, re.S)
            data = json.loads(block.group(1))
            self.assertEqual({"BreadcrumbList", "ItemList", "FAQPage"}, {d["@type"] for d in data}, relative)


class SitemapTests(unittest.TestCase):
    def test_merge_adds_missing_rows_once(self):
        base = '<?xml version="1.0"?>\n<urlset>\n<url><loc>https://x/a.html</loc></url>\n</urlset>\n'
        once = gen.merge_sitemap(base, ["https://x/a.html", "https://x/b.html"], "2026-10-22")
        self.assertEqual(1, once.count("https://x/a.html"))
        self.assertIn("<url><loc>https://x/b.html</loc><lastmod>2026-10-22</lastmod></url>", once)
        self.assertEqual(once, gen.merge_sitemap(once, ["https://x/b.html"], "2026-10-23"))


if __name__ == "__main__":
    unittest.main()
