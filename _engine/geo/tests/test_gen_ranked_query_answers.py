#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_ranked_query_answers 的閘門與 en-US 供體退路。

守三件事:
1. 付費款只有明寫 ``paid_context: pay_once`` 才可以不走免費門;未知的語境值直接炸。
2. 資料檔每個語系都有區塊標題(新增語系忘了 LABELS 會在產生時才 KeyError)。
3. en-US 供體正規化成根目錄英文頁:不留 /en-US/ 網址、lang、inLanguage、noindex。
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
ROOT = os.path.dirname(GEO)
sys.path.insert(0, GEO)
sys.path.insert(0, os.path.join(ROOT, "social"))

import gen_ranked_query_answers as gen  # noqa: E402
from app_pairs import free_first_key  # noqa: E402


class DataContractTests(unittest.TestCase):
    def setUp(self):
        self.entries = json.loads(gen.DATA.read_text(encoding="utf-8"))

    def test_every_locale_has_labels(self):
        for entry in self.entries:
            self.assertIn(entry["locale"], gen.LABELS, entry["slug"])

    def test_paid_keys_need_an_explicit_pay_once_context(self):
        for entry in self.entries:
            context = entry.get("paid_context")
            if context is not None:
                self.assertIn(context, gen.PAID_CONTEXTS, entry["slug"])
            if entry["key"] != free_first_key(entry["key"]):
                self.assertEqual("pay_once", context, entry["slug"])

    def test_slugs_are_unique(self):
        slugs = [entry["slug"] for entry in self.entries]
        self.assertEqual(len(slugs), len(set(slugs)))


class EnFallbackNormalizationTests(unittest.TestCase):
    def test_en_us_donor_becomes_root_english(self):
        site = gen.SITE
        donor = (
            '<html lang="en-US"><head>'
            '<meta name="robots" content="noindex,follow">'
            f'<link rel="canonical" href="{site}/en-US/answers/x.html">'
            '<script type="application/ld+json">{"inLanguage": "en-US"}</script>'
            f'</head><body><a href="{site}/en-US/tools/a.html">t</a></body></html>'
        )
        out = gen.normalize_en_fallback(donor)
        self.assertNotIn("en-US", out)
        self.assertNotIn("noindex", out)
        self.assertIn('lang="en"', out)
        self.assertIn('"inLanguage": "en"', out)
        self.assertIn(f"{site}/answers/x.html", out)
        self.assertIn(gen.INDEXABLE_ROBOTS, out)


if __name__ == "__main__":
    unittest.main()
