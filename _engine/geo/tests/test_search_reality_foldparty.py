"""喵喵派對（foldparty）搜尋實況意圖頁：下載連結、追蹤碼、禁用字、內容長度（離線）。"""

from __future__ import annotations

import html
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_search_reality_foldparty as gen  # noqa: E402
import gen_search_reality_g3 as g3  # noqa: E402
import gw_campaign  # noqa: E402

PATCHED = ("LANGS", "APP_IDS", "PAGE_SPECS", "BANNED", "dedicated_size")


class FoldPartyPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {name: getattr(g3, name) for name in PATCHED}
        gen._install()
        cls.pages = g3.build({})

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.saved.items():  # 不污染同一行程裡其他產生器的測試
            setattr(g3, name, value)

    def test_taiwan_korea_and_macau_native_pages(self):
        self.assertEqual([spec["lang"] for spec in gen.PAGE_SPECS], ["zh-Hant", "ko", "zh-Hant", "zh-Hant"])
        self.assertEqual(gen.PAGE_SPECS[2].get("cc"), "mo")
        self.assertIn("貓咪派對", gen.PAGE_SPECS[2]["terms"])
        self.assertEqual({spec["key"] for spec in gen.PAGE_SPECS}, {"foldparty"})
        self.assertIn("雙人遊戲", gen.PAGE_SPECS[0]["terms"])
        self.assertIn("2인용 게임", gen.PAGE_SPECS[1]["terms"])
        self.assertIsNone(gen.PAGE_SPECS[3].get("cc"))  # 台灣店
        self.assertTrue(gen.PAGE_SPECS[3]["slug"].startswith("maomi-paidui-taiwan"))
        self.assertIn("貓咪派對", gen.PAGE_SPECS[3]["terms"])
        self.assertEqual(len(self.pages), 4)

    def test_taiwan_two_player_page_links_taiwan_cat_page(self):
        source = self.pages[g3.page_relative(gen.PAGE_SPECS[0])]
        self.assertIn(gen.PAGE_SPECS[3]["slug"] + ".html", source)

    def test_macau_cat_page_links_taiwan_cat_page(self):
        source = self.pages[g3.page_relative(gen.PAGE_SPECS[2])]
        self.assertIn(gen.PAGE_SPECS[3]["slug"] + ".html", source)

    def test_card_links_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            cc = spec.get("cc") or gen.LANGS[spec["lang"]]["cc"]
            source = self.pages[g3.page_relative(spec)]
            href = html.unescape(re.search(r'class="dl" href="([^"]+)"', source).group(1))
            self.assertTrue(href.startswith(f"https://apps.apple.com/{cc}/app/id6829184924?"), href)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            self.assertEqual(query["ct"], [gw_campaign.campaign("foldparty", "sr", cc)])
            self.assertEqual(query["pt"], ["118326163"])
            self.assertIn(gw_campaign.meta_tag("sr"), source)

    def test_no_price_free_pro_trial_or_unverified_fold_claims(self):
        for relative, source in self.pages.items():
            text = html.unescape(re.sub(r"<script\b.*?</script>", "", g3.visible_text(source)
                                        + source.split("</head>", 1)[0], flags=re.S))
            self.assertIsNone(gen.BANNED.search(text), relative)
            for word in ("試用", "訂閱", "價格", "內購", "체험", "구독", "가격"):
                self.assertNotIn(word, text, relative)
            # 摺疊／Duo 宣稱尚未實機驗證：意圖頁一律不寫
            self.assertIsNone(re.search(r"摺|折疊|폴더블|접기|접힌|접으|접었|\bDuo\b", text, re.I), relative)

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            size = g3.dedicated_size(spec["lang"], g3.visible_text(self.pages[g3.page_relative(spec)]))
            self.assertGreaterEqual(size, 450, spec["slug"])


if __name__ == "__main__":
    unittest.main()
