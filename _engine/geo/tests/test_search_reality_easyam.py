"""假日鬧鐘（easyam）搜尋實況意圖頁：下載連結、追蹤碼、禁用字、內容長度、語系（離線）。"""

from __future__ import annotations

import html
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_search_reality_easyam as gen  # noqa: E402
import gen_search_reality_g3 as g3  # noqa: E402

PATCHED = ("LANGS", "APP_IDS", "PAGE_SPECS", "BANNED", "dedicated_size")


class EasyamPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {name: getattr(g3, name) for name in PATCHED}
        gen._install()
        cls.pages = g3.build({})

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.saved.items():  # 不污染同一行程裡第 3 組的測試
            setattr(g3, name, value)

    def test_five_native_markets_plus_english(self):
        langs = [spec["lang"] for spec in gen.PAGE_SPECS]
        self.assertEqual(sorted(langs), sorted(["zh-Hant", "ja", "ko", "de-DE", "pt-BR", "en"]))
        self.assertEqual({spec["key"] for spec in gen.PAGE_SPECS}, {"easyam"})
        self.assertEqual(len(self.pages), len(gen.PAGE_SPECS))

    def test_cards_link_to_own_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            source = self.pages[g3.page_relative(spec)]
            cc = gen.LANGS[spec["lang"]]["cc"]
            href = html.unescape(re.search(r'class="dl" href="([^"]+)"', source).group(1))
            self.assertTrue(href.startswith(f"https://apps.apple.com/{cc}/app/id6821790092?"), href)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            self.assertEqual(query["ct"], [f"ln_easyam_sr_{cc}_gw_1023"])
            self.assertEqual(query["pt"], ["118326163"])

    def test_no_price_free_or_pro_wording(self):
        for relative, source in self.pages.items():
            text = g3.visible_text(source) + source.split("</head>", 1)[0]
            self.assertIsNone(gen.BANNED.search(html.unescape(re.sub(r"<script\b.*?</script>", "", text, flags=re.S))),
                              relative)

    def test_banned_catches_other_languages(self):
        for word in ("무료 알람", "Wecker kostenlos", "despertador grátis", "R$ 9,90", "4,99 €"):
            self.assertIsNotNone(gen.BANNED.search(word), word)

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            size = gen.dedicated_size(spec["lang"], g3.visible_text(self.pages[g3.page_relative(spec)]))
            self.assertGreaterEqual(size, 450, spec["slug"])

    def test_shift_mode_always_named_as_in_app_purchase(self):
        markers = {"zh-Hant": "App 內購買", "ja": "App内課金", "ko": "앱 내 구입", "de-DE": "In-App-Kauf",
                   "pt-BR": "compra dentro do app", "en": "in-app purchase"}
        for spec in gen.PAGE_SPECS:
            self.assertIn(markers[spec["lang"]], g3.visible_text(self.pages[g3.page_relative(spec)]), spec["slug"])


if __name__ == "__main__":
    unittest.main()
