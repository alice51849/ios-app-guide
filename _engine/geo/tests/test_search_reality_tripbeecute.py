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

PATCHED = ("LANGS", "APP_IDS", "PAGE_SPECS", "BANNED", "dedicated_size", "sitemap_name")


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
        self.assertEqual([spec["lang"] for spec in gen.PAGE_SPECS], ["zh-Hant", "ko", "zh-Hant", "zh-Hant", "zh-Hant", "ja", "en-AU"])
        self.assertEqual({spec["key"] for spec in gen.PAGE_SPECS}, {"tripbeecute"})
        self.assertIn("可愛 旅行手帳", gen.PAGE_SPECS[0]["terms"])
        self.assertIn("다꾸 여행", gen.PAGE_SPECS[1]["terms"])
        self.assertIn("旅行手帳", gen.PAGE_SPECS[2]["terms"])
        self.assertIn("旅行 手帳", gen.PAGE_SPECS[2]["terms"])
        self.assertIn("旅遊手帳", gen.PAGE_SPECS[3]["terms"])
        self.assertIn("旅行 清單", gen.PAGE_SPECS[3]["terms"])
        self.assertIn("旅行手帳", gen.PAGE_SPECS[4]["terms"])
        self.assertIn("旅行 手賬", gen.PAGE_SPECS[4]["terms"])
        self.assertIn("旅行 手帳", gen.PAGE_SPECS[5]["terms"])
        self.assertIn("cute travel journal", gen.PAGE_SPECS[6]["terms"])
        self.assertEqual(len(self.pages), 7)

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
            spec = next(s for s in gen.PAGE_SPECS if g3.page_relative(s) == relative)
            self.assertIsNone(spec.get("banned", gen.BANNED).search(text), relative)
            # 照 2026-11-11 文案修正寫 Cute Pass 的兩頁：只放行說明一次性購買所需的字，試用、價格照擋
            allowed = {"解鎖", "訂閱", "Cute Pass", "內購", "구독", "앱 내 구입"} if spec.get("pass_wording") else set()
            for word in ("解鎖", "試用", "訂閱", "價格", "Cute Pass", "內購", "課金", "体験", "サブスク",
                         "unlock", "trial", "subscription", "in-app purchase",
                         "체험", "구독", "가격", "잠금 해제", "앱 내 구입", "AI 기능", "내장 AI"):
                if word not in allowed:
                    self.assertNotIn(word, text, relative)

    def test_pass_wording_pages_follow_copy_fix_spec(self):
        self.assertEqual([s["slug"] for s in gen.PAGE_SPECS if s.get("pass_wording")],
                         ["keai-lvxing-shouzhang-chuguo-xingchengbiao-daoshu-zhhant",
                          "dakku-yeohaeng-diary-sticker-illust-pyoji",
                          "lvxing-shouzhang-qu-lvxing-xingcheng-guihua-hk",
                          "lvyou-shouzhang-lvxing-qingdan-dabao-xingli-zhhant",
                          "lvxing-shouzhang-aomen-chufa-jiaren-tongxing-mo",
                          "ryoko-techo-app-kawaii-ensei-joshitabi",
                          "cute-travel-journal-app-holiday-countdown-en-au"])
        self.assertIsNotNone(gen.BANNED.search("무료"))
        self.assertIsNone(gen.PASS_BANNED.search("무료"))
        for bad in ("免費", "Free", "NT$90", "3,300원"):
            self.assertIsNotNone(gen.PASS_BANNED.search(bad), bad)
        tw, ko = gen.PAGE_SPECS[0], gen.PAGE_SPECS[1]
        self.assertEqual(tw["faqs"][0][0], "下載前想知道：不購買能做什麼？")
        self.assertEqual(ko["faqs"][0][0], "구매 전에: 무료로 무엇을 할 수 있나요?")
        self.assertIn("不是訂閱", tw["faqs"][0][1])
        self.assertIn("구독이 아니에요", ko["faqs"][0][1])
        self.assertIn("跨年、寒假、春節出國怎麼排", [s[0] for s in tw["sections"]])
        self.assertEqual(len(ko["sections"]), 3)
        for spec, words in ((tw, ("自己的照片當封面", "智慧行李清單", "iCloud 同步與備份", "和朋友一起規劃")),
                            (ko, ("내 사진 표지", "스마트 준비물 리스트", "iCloud 동기화와 백업", "친구와 함께 계획하기"))):
            source = self.pages[g3.page_relative(spec)]
            text = g3.visible_text(source)
            self.assertIn("Cute Pass", text)
            for word in words:
                self.assertIn(word, spec["faqs"][0][1])
            for word in ("免費試用", "57 款", "57종"):
                self.assertNotIn(word, text)
            self.assertIn("id6826987407", source)
        # 付費口徑：分帳不購買就能用，列在台韓兩頁「不購買能做什麼」清單
        self.assertIn("分帳（和旅伴記花費、算清誰該付給誰）", tw["faqs"][0][1])
        self.assertIn("여행 경비 정산", ko["faqs"][0][1])
        # 港澳日澳四頁：共同編輯、同步、智慧行李清單、加購封面標 Cute Pass，不新增 FAQ 題目
        for spec in gen.PAGE_SPECS[2:]:
            if not spec.get("pass_wording"):
                continue
            text = g3.visible_text(self.pages[g3.page_relative(spec)])
            self.assertIn("Cute Pass", text, spec["slug"])
            self.assertIn("51", text, spec["slug"])
            for word in ("免費試用", "57 款", "57"):
                self.assertNotIn(word, text, spec["slug"])
            self.assertEqual(len(spec["faqs"]), 4, spec["slug"])

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
        bad = "https://apps.apple.com/sg/app/id6826987407?pt=118326163&ct=ln_tripbeecute_all_ww_gw&mt=8"
        with self.assertRaises(g3.GenerationError):
            g3.extra_storefront_url(bad, "6826987407", "sg")
        no_ct = "https://apps.apple.com/hk/app/id6826987407?pt=118326163&mt=8"
        with self.assertRaises(g3.GenerationError):
            g3.extra_storefront_url(no_ct, "6826987407", "hk")

    def test_macau_page_uses_mo_storefront_own_slug_and_angle(self):
        mo = gen.PAGE_SPECS[4]
        self.assertEqual(mo["cc"], "mo")
        self.assertTrue(mo["slug"].endswith("-mo"))
        self.assertIn("mo", g3.EXTRA_STOREFRONTS)
        source = self.pages[g3.page_relative(mo)]
        self.assertIn("https://apps.apple.com/mo/app/id6826987407?", html.unescape(source))
        for other in ("tw", "hk"):
            self.assertNotIn(f"apps.apple.com/{other}/", source)
        self.assertTrue(mo["h1"].startswith("旅行手帳"))
        text = g3.visible_text(source)
        for word in ("澳門 App Store", "港珠澳大橋", "澳門國際機場", "家人"):
            self.assertIn(word, text)
        for other in gen.PAGE_SPECS[:4]:
            self.assertNotEqual(mo["slug"], other["slug"])
            self.assertNotEqual(mo["title"], other["title"])
            self.assertNotEqual(mo["lead"], other["lead"])
            self.assertNotEqual(mo["intro"], other["intro"])

    def test_taiwan_list_page_own_slug_storefront_and_angle(self):
        page = gen.PAGE_SPECS[3]
        self.assertNotIn("cc", page)  # 預設台灣店
        slugs = [spec["slug"] for spec in gen.PAGE_SPECS]
        self.assertEqual(len(slugs), len(set(slugs)))
        source = self.pages[g3.page_relative(page)]
        self.assertIn("apps.apple.com/tw/app/id6826987407", source)
        self.assertTrue(page["h1"].startswith("旅遊手帳"))
        self.assertIn("旅行清單", page["title"])
        text = g3.visible_text(source)
        for word in ("行李清單", "打包", "旅伴", "不是記帳 App，但和旅伴的花費可以直接在行程上分帳、算清誰該付給誰"):
            self.assertIn(word, text)
        # 與既有台灣頁、香港頁的標題與開頭不同
        for other in gen.PAGE_SPECS[:3]:
            self.assertNotEqual(page["title"], other["title"])
            self.assertNotEqual(page["lead"], other["lead"])

    def test_taiwan_main_page_adds_cute_itinerary_term_keeping_existing(self):
        page = gen.PAGE_SPECS[0]
        # 只增詞、不拿詞：主詞與既有詞全部保留，新增「可愛 行程」
        self.assertEqual(page["terms"], ["可愛 旅行手帳", "旅行手帳", "出國 行程表", "出國倒數", "可愛 行程"])
        self.assertEqual(page["title"], "可愛旅行手帳怎麼做？把整趟行程排成一本插畫手冊的 5 個重點")
        self.assertEqual(page["h1"], "可愛旅行手帳：出國倒數、航班、每日行程和行李清單收進同一本")
        source = self.pages[g3.page_relative(page)]
        self.assertIn('"keywords": "可愛 旅行手帳, 旅行手帳, 出國 行程表, 出國倒數, 可愛 行程"', source)
        text = g3.visible_text(source)
        for word in ("想要一份可愛的行程表？", "可愛 行程", "逐日分色", "插畫封面", "CSV 範本", "匯入"):
            self.assertIn(word, text)
        # 其他頁不出現新段落
        for other in gen.PAGE_SPECS[1:]:
            self.assertNotIn("想要一份可愛的行程表？", self.pages[g3.page_relative(other)])
            self.assertNotIn("可愛 行程", other["terms"])

    def test_japan_page_uses_jp_store_and_techo_angle(self):
        ja = gen.PAGE_SPECS[5]
        self.assertNotIn("cc", ja)
        self.assertTrue(ja["h1"].startswith("旅行手帳"))
        self.assertNotIn("旅のしおり", ja["terms"])  # 姊妹款 TripBee Lite 的日文頁打這個詞，不搶
        source = html.unescape(self.pages[g3.page_relative(ja)])
        self.assertIn("https://apps.apple.com/jp/app/id6826987407?", source)
        self.assertTrue(g3.page_relative(ja).startswith("ja/seasonal/"))

    def test_australia_page_uses_au_store_and_existing_sitemap(self):
        au = gen.PAGE_SPECS[6]
        self.assertEqual(gen.LANGS["en-AU"]["cc"], "au")
        self.assertEqual(gen.LANGS["en-AU"]["dir"], "en-AU")
        self.assertTrue(g3.page_relative(au).startswith("en-AU/seasonal/"))
        source = html.unescape(self.pages[g3.page_relative(au)])
        self.assertIn("https://apps.apple.com/au/app/id6826987407?", source)
        self.assertIn('lang="en-AU"', source)
        self.assertEqual(g3.sitemap_name("en-AU"), "sitemap_seasonal_en_AU.xml")
        self.assertEqual(g3.sitemap_name("ja"), "sitemap_seasonal_ja.xml")
        for word in ("together through iCloud", "smart packing", "backup", "57"):
            self.assertNotIn(word, source)

    def test_dedicated_text_floor(self):
        for spec in gen.PAGE_SPECS:
            size = g3.dedicated_size(spec["lang"], g3.visible_text(self.pages[g3.page_relative(spec)]))
            self.assertGreaterEqual(size, 450, spec["slug"])


if __name__ == "__main__":
    unittest.main()
