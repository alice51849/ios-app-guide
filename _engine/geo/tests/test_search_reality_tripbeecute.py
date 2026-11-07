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

    def test_taiwan_korea_and_hong_kong_native_pages(self):
        self.assertEqual([spec["lang"] for spec in gen.PAGE_SPECS], ["zh-Hant", "ko", "zh-Hant"])
        self.assertEqual({spec["key"] for spec in gen.PAGE_SPECS}, {"tripbeecute"})
        self.assertIn("可愛 旅行手帳", gen.PAGE_SPECS[0]["terms"])
        self.assertIn("다꾸 여행", gen.PAGE_SPECS[1]["terms"])
        self.assertIn("旅行手帳", gen.PAGE_SPECS[2]["terms"])
        self.assertIn("旅行 手帳", gen.PAGE_SPECS[2]["terms"])
        self.assertEqual(len(self.pages), 3)

    def test_card_links_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            cc = spec.get("cc") or gen.LANGS[spec["lang"]]["cc"]
            source = self.pages[g3.page_relative(spec)]
            href = html.unescape(re.search(r'class="dl" href="([^"]+)"', source).group(1))
            self.assertTrue(href.startswith(f"https://apps.apple.com/{cc}/app/id6826987407?"), href)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            self.assertEqual(query["ct"], [gw_campaign.campaign("tripbeecute", "sr", cc)])
            self.assertEqual(query["pt"], ["118326163"])
            self.assertIn(gw_campaign.meta_tag("sr"), source)

    def test_no_price_free_pro_or_unlock_wording(self):
        for relative, source in self.pages.items():
            text = html.unescape(re.sub(r"<script\b.*?</script>", "", g3.visible_text(source)
                                        + source.split("</head>", 1)[0], flags=re.S))
            self.assertIsNone(gen.BANNED.search(text), relative)
            for word in ("解鎖", "試用", "訂閱", "價格", "Cute Pass", "內購",
                         "체험", "구독", "가격", "잠금 해제", "앱 내 구입", "AI 기능", "내장 AI"):
                self.assertNotIn(word, text, relative)

    def test_hong_kong_page_uses_hk_storefront_and_own_slug(self):
        hk = gen.PAGE_SPECS[2]
        self.assertEqual(hk["cc"], "hk")
        self.assertNotEqual(hk["slug"], gen.PAGE_SPECS[0]["slug"])
        source = self.pages[g3.page_relative(hk)]
        self.assertIn("https://apps.apple.com/hk/app/id6826987407?", html.unescape(source))
        self.assertNotIn("apps.apple.com/tw/", source)
        self.assertTrue(hk["h1"].startswith("旅行手帳"))
        self.assertIn("香港 App Store", g3.visible_text(source))
        # 台灣頁不受影響：仍連台灣店
        self.assertIn("apps.apple.com/tw/app/id6826987407", self.pages[g3.page_relative(gen.PAGE_SPECS[0])])

    def test_hong_kong_link_rejected_without_extra_storefront(self):
        bad = "https://apps.apple.com/mo/app/id6826987407?pt=118326163&ct=ln_tripbeecute_all_ww_gw&mt=8"
        with self.assertRaises(g3.GenerationError):
            g3.extra_storefront_url(bad, "6826987407", "mo")
        no_ct = "https://apps.apple.com/hk/app/id6826987407?pt=118326163&mt=8"
        with self.assertRaises(g3.GenerationError):
            g3.extra_storefront_url(no_ct, "6826987407", "hk")

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            size = g3.dedicated_size(spec["lang"], g3.visible_text(self.pages[g3.page_relative(spec)]))
            self.assertGreaterEqual(size, 450, spec["slug"])


if __name__ == "__main__":
    unittest.main()
