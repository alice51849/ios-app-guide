"""TripBee Cute（tripbeecute）搜尋實況意圖頁：下載連結、追蹤碼、禁用字、內容長度（離線）。"""

from __future__ import annotations

import html
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_search_reality_tripbeecute as gen  # noqa: E402
import gen_search_reality_g3 as g3  # noqa: E402
import gw_campaign  # noqa: E402

PATCHED = ("LANGS", "APP_IDS", "PAGE_SPECS", "BANNED", "dedicated_size")


class TripBeeCutePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {name: getattr(g3, name) for name in PATCHED}
        gen._install()
        cls.pages = g3.build({})

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.saved.items():  # 不污染同一行程裡其他產生器的測試
            setattr(g3, name, value)

    def test_one_native_taiwan_page(self):
        self.assertEqual([spec["lang"] for spec in gen.PAGE_SPECS], ["zh-Hant"])
        self.assertEqual({spec["key"] for spec in gen.PAGE_SPECS}, {"tripbeecute"})
        self.assertIn("可愛 旅行手帳", gen.PAGE_SPECS[0]["terms"])
        self.assertEqual(len(self.pages), 1)

    def test_card_links_taiwan_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[g3.page_relative(spec)]
            href = html.unescape(re.search(r'class="dl" href="([^"]+)"', source).group(1))
            self.assertTrue(href.startswith("https://apps.apple.com/tw/app/id6826987407?"), href)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            self.assertEqual(query["ct"], [gw_campaign.campaign("tripbeecute", "sr", "tw")])
            self.assertEqual(query["pt"], ["118326163"])
            self.assertIn(gw_campaign.meta_tag("sr"), source)

    def test_no_price_free_pro_or_unlock_wording(self):
        for relative, source in self.pages.items():
            text = html.unescape(re.sub(r"<script\b.*?</script>", "", g3.visible_text(source)
                                        + source.split("</head>", 1)[0], flags=re.S))
            self.assertIsNone(gen.BANNED.search(text), relative)
            for word in ("解鎖", "試用", "訂閱", "價格", "Cute Pass", "內購"):
                self.assertNotIn(word, text, relative)

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            size = g3.dedicated_size(spec["lang"], g3.visible_text(self.pages[g3.page_relative(spec)]))
            self.assertGreaterEqual(size, 450, spec["slug"])


if __name__ == "__main__":
    unittest.main()
