"""千萬作戰小組 D 搜尋實況母語意圖頁（第一批德／日／泰 8 頁＋第二批日／英 10 頁）：下載連結、追蹤碼、禁用字、內容長度（離線）。"""

from __future__ import annotations

import html
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_search_reality_squadd as gen  # noqa: E402
import gen_search_reality_g3 as g3  # noqa: E402
import gw_campaign  # noqa: E402

PATCHED = ("LANGS", "APP_IDS", "PAGE_SPECS", "BANNED", "dedicated_size")
EXPECTED = {
    ("maskmyfile", "de-DE"): "pdf schwärzen",
    ("picclear", "ja"): "容量を軽くするアプリ",
    ("qrcodehalo", "de-DE"): "qr code prüfen",
    ("mochidonestamp", "th"): "บันทึกครั้งล่าสุด",
    ("notesstudio100", "th"): "จดโน้ตด้วยลายมือ",
    ("photocream", "th"): "ฟิลเตอร์ฟิล์ม",
    ("moneytag", "de-DE"): "nebenjob einnahmen",
    ("onepageppt", "th"): "สรุปหน้าเดียว",
    # 第二批：每款第二個市場
    ("mochi", "ja"): "todoリスト",
    ("metrotimehelper", "en"): "taipei mrt",
    ("maskmyfile", "ja"): "pdf 黒塗り",
    ("picclear", "en"): "photo cleaner",
    ("qrcodehalo", "en"): "safe qr scanner",
    ("mochidonestamp", "ja"): "いつやった",
    ("moneytag", "en"): "side hustle tracker",
    ("notesstudio100", "ja"): "手書きノート",
    ("onepageppt", "en"): "one page summary",
    ("photocream", "ja"): "フィルムカメラ 加工",
}


class SquadDPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {name: getattr(g3, name) for name in PATCHED}
        gen._install()
        cls.pages = g3.build({})

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.saved.items():  # 不污染同一行程裡其他產生器的測試
            setattr(g3, name, value)

    def test_native_pages_with_measured_terms(self):
        got = {(spec["key"], spec["lang"]): spec["terms"][0] for spec in gen.PAGE_SPECS}
        self.assertEqual(got, EXPECTED)
        self.assertEqual(len(self.pages), 18)

    def test_no_duplicate_of_g3_pages(self):
        g3_pairs = {(spec["key"], spec["lang"]) for spec in self.saved["PAGE_SPECS"]}
        self.assertFalse(g3_pairs & set(EXPECTED))
        import gen_search_reality_metrotimehelper as metro  # 部門 12 的捷運頁不重做
        self.assertFalse({(spec["key"], spec["lang"]) for spec in metro.PAGE_SPECS} & set(EXPECTED))

    def test_card_links_storefront_with_campaign(self):
        for spec in gen.PAGE_SPECS:
            cc = gen.LANGS[spec["lang"]]["cc"]
            source = self.pages[g3.page_relative(spec)]
            href = html.unescape(re.search(r'class="dl" href="([^"]+)"', source).group(1))
            self.assertTrue(href.startswith(f"https://apps.apple.com/{cc}/app/id{gen.APP_IDS[spec['key']]}?"), href)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            self.assertEqual(query["ct"], [gw_campaign.campaign(spec["key"], "sr", cc)])
            self.assertEqual(query["pt"], ["118326163"])
            self.assertIn(gw_campaign.meta_tag("sr"), source)

    def test_no_price_free_pro_trial_or_fold_claims(self):
        for relative, source in self.pages.items():
            text = html.unescape(re.sub(r"<script\b.*?</script>", "", g3.visible_text(source)
                                        + source.split("</head>", 1)[0], flags=re.S))
            self.assertIsNone(gen.BANNED.search(text), relative)
            for word in ("Testversion", "Abo", "Preis", "お試し", "サブスク", "価格", "購入", "買い切り", "ทดลอง", "ราคา", "สมาชิก",
                         "trial", "subscription", "price", "purchase", "Lifetime"):
                self.assertNotIn(word, text, relative)
            self.assertIsNone(re.search(r"折りたた|พับ|klapp|\bDuo\b", text, re.I), relative)

    def test_banned_catches_pro_but_not_store_brand(self):
        for word in ("Lifetime Pro", "pro Monat", "ใช้ฟรี", "kostenlos", "ทดลองใช้", "99 บาท"):
            self.assertIsNotNone(gen.BANNED.search(word), word)
        for name in ("PicClear Pro：写真整理", "PhotoCream Pro: ฟิลเตอร์ฟิล์ม"):
            self.assertIsNone(gen.BANNED.search(name), name)

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            size = g3.dedicated_size(spec["lang"], g3.visible_text(self.pages[g3.page_relative(spec)]))
            self.assertGreaterEqual(size, 450, spec["slug"])


if __name__ == "__main__":
    unittest.main()
