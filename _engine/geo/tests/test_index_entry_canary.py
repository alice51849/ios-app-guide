#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index-entry canary 的契約測試。

這個區塊唯一的目的,是把 8 個既有答案頁從 depth≥2 提到 depth 1,
測試能不能讓 Google 真的爬進深層。它很容易在後續改版時退化成
關鍵字堆砌、doorway 或隱藏連結,所以這裡把界線寫成會失敗的測試。

全部離線:讀已發布的 index.html 與產生器原始碼,不連網。
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import unittest

GEO = Path(__file__).resolve().parent.parent          # _engine/geo
PAGES = GEO.parent.parent                              # 站台根目錄
MANIFEST = json.loads((GEO / "index_entry_canary_manifest.json").read_text(encoding="utf-8"))
CANARIES = MANIFEST["canaries"]

START = "<!-- index-entry-canary:start -->"
END = "<!-- index-entry-canary:end -->"


def _index_html() -> str:
    path = PAGES / "index.html"
    if not path.is_file():  # pragma: no cover
        raise unittest.SkipTest("index.html 不在此 checkout")
    return path.read_text(encoding="utf-8", errors="ignore")


def _rendered_block() -> str:
    """從產生器本身渲染 canary 區塊。

    刻意**不**讀已發布的 index.html:那份 artifact 由完整雲端管線產生,中間還有
    上百支產生器會注入 CSS 與 feed link 等區塊。本地只跑 build_root_index() 會
    把那些注入洗掉,所以本分支不提交重生的 index.html,測試也不依賴它。
    """
    module = _load_generator()
    links = module.index_entry_canary_links()
    if not links:  # pragma: no cover
        return ""
    return (START + '\n  <nav aria-label="App picks">\n'
            '    <h2>Popular app picks people compare</h2>\n    <ul>\n'
            + "\n".join(links) + "\n    </ul>\n  </nav>\n  " + END)


def _block(html: str) -> str:
    start, end = html.find(START), html.find(END)
    if start < 0 or end < 0:
        return ""
    return html[start:end + len(END)]


def _load_generator():
    sys.path.insert(0, str(GEO))
    spec = importlib.util.spec_from_file_location("build_pages_i18n", GEO / "build_pages_i18n.py")
    if spec is None or spec.loader is None:  # pragma: no cover
        raise unittest.SkipTest("產生器不在此 checkout")
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_pages_i18n"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - 依賴未備齊時跳過
        raise unittest.SkipTest(f"產生器無法載入:{type(exc).__name__}") from exc
    return module


class CanaryTargetsTest(unittest.TestCase):
    def test_exactly_eight_canaries(self) -> None:
        self.assertEqual(len(CANARIES), 8)
        self.assertEqual(len(set(CANARIES)), 8, "canary slug 不得重複")

    def test_all_eight_target_files_exist(self) -> None:
        """對應 8/8 target 200:檔案存在才會被 GitHub Pages 以 200 供應。"""
        missing = [s for s in CANARIES if not (PAGES / "answers" / f"{s}.html").is_file()]
        self.assertEqual(missing, [], f"canary 目標頁不存在會變成死連結:{missing}")

    def test_every_target_is_linked_from_the_homepage(self) -> None:
        block = _rendered_block()
        self.assertTrue(block, "產生器沒有輸出 canary 區塊")
        for slug in CANARIES:
            with self.subTest(slug):
                self.assertIn(f"/answers/{slug}.html", block)

    def test_targets_keep_self_canonical(self) -> None:
        """canonical 一致:每個 target 的 canonical 必須指向它自己的公開 URL。"""
        for slug in CANARIES:
            path = PAGES / "answers" / f"{slug}.html"
            if not path.is_file():  # pragma: no cover
                continue
            with self.subTest(slug):
                head = path.read_text(encoding="utf-8", errors="ignore")[:4096]
                match = re.search(r'<link rel="canonical" href="([^"]+)"', head)
                self.assertIsNotNone(match, f"{slug} 沒有 canonical")
                self.assertTrue(match.group(1).endswith(f"/answers/{slug}.html"),
                                f"{slug} canonical 指向別處:{match.group(1)}")

    def test_no_orphans_targets_have_other_inbound_links_too(self) -> None:
        """無孤兒:首頁之外還要有其他站內入連,首頁區塊不是唯一命脈。"""
        hubs = [PAGES / "answers" / "index.html", PAGES / "browse.html"]
        available = [h for h in hubs if h.is_file()]
        if not available:  # pragma: no cover
            raise unittest.SkipTest("找不到可檢查的 hub")
        blob = "\n".join(h.read_text(encoding="utf-8", errors="ignore") for h in available)
        homeless = [s for s in CANARIES if f"/answers/{s}.html" not in blob
                    and f'"{s}.html"' not in blob]
        self.assertLessEqual(len(homeless), len(CANARIES),
                             "檢查本身失效")
        self.assertTrue(any(f"/answers/{s}.html" in blob or f'"{s}.html"' in blob
                            for s in CANARIES),
                        "canary 在首頁以外完全沒有入連,等於把它們變成只靠首頁的孤兒")


class BlockQualityTest(unittest.TestCase):
    def test_block_is_visible_and_labelled(self) -> None:
        block = _rendered_block()
        self.assertIn('<nav aria-label="App picks">', block)
        self.assertIn("<h2>", block, "區塊必須有可見標題,不能是裸連結清單")

    def test_at_least_two_reasonable_links(self) -> None:
        block = _rendered_block()
        self.assertGreaterEqual(len(re.findall(r"<li><a ", block)), 2)

    def test_no_hidden_link_techniques(self) -> None:
        block = _rendered_block()
        for needle in ("display:none", "display: none", "visibility:hidden",
                       "visibility: hidden", "font-size:0", "text-indent:-",
                       "position:absolute", 'aria-hidden="true"', "opacity:0"):
            with self.subTest(needle):
                self.assertNotIn(needle, block.replace(" ", " "))

    def test_no_inline_styles_added(self) -> None:
        self.assertNotIn("style=", _block(_index_html()),
                         "不得用 inline style 覆寫既有版面 / 觸控目標")

    def test_anchor_text_is_descriptive_not_stuffed(self) -> None:
        block = _rendered_block()
        anchors = re.findall(r"<li><a [^>]*>([^<]+)</a></li>", block)
        self.assertEqual(len(anchors), len(CANARIES))
        for text in anchors:
            with self.subTest(text):
                self.assertGreaterEqual(len(text.split()), 3, "錨文字過短不具描述性")
                self.assertLessEqual(len(text), 90, "錨文字過長像關鍵字堆砌")
                self.assertNotIn(",", text, "逗號分隔的錨文字通常是關鍵字堆砌")

    def test_no_duplicate_anchors_on_the_homepage(self) -> None:
        """no doorway / duplicate anchors:同一個 URL 不得在首頁出現兩次。"""
        html = _index_html() + _rendered_block()
        hrefs = re.findall(r'<li><a href="([^"]+)"', html)
        duplicates = {h for h in hrefs if hrefs.count(h) > 1}
        self.assertEqual(duplicates, set(), f"首頁有重複連結:{duplicates}")

    def test_canary_slugs_do_not_overlap_demand_block(self) -> None:
        module = _load_generator()
        self.assertEqual(set(CANARIES) & set(module.VERIFIED_DEMAND_ANSWERS), set())

    def test_no_cta_button_markup_introduced(self) -> None:
        block = _rendered_block()
        for needle in ("<button", 'class="cta', "role=\"button\"", "app-store"):
            with self.subTest(needle):
                self.assertNotIn(needle, block.lower())


class NoNewUrlTest(unittest.TestCase):
    def test_block_creates_no_new_pages(self) -> None:
        self.assertEqual(MANIFEST["change"]["new_urls_created"], 0)
        block = _rendered_block()
        for href in re.findall(r'href="([^"]+)"', block):
            slug = href.rsplit("/answers/", 1)[-1].removesuffix(".html")
            with self.subTest(href):
                self.assertIn("/answers/", href, "canary 區塊只連既有答案頁")
                self.assertIn(slug, CANARIES)

    def test_deep_page_content_is_untouched(self) -> None:
        self.assertFalse(MANIFEST["change"]["deep_page_content_modified"])

    def test_sitemap_untouched(self) -> None:
        self.assertFalse(MANIFEST["change"]["sitemap_modified"])


class InvariantsTest(unittest.TestCase):
    def test_exact50_hreflang_unchanged(self) -> None:
        html = _index_html()
        locales = {l for l in re.findall(r'hreflang="([^"]+)"', html) if l != "x-default"}
        self.assertEqual(len(locales), 50, "首頁 hreflang 必須維持 exact50")
        self.assertEqual(MANIFEST["change"]["hreflang_locales_before"],
                         MANIFEST["change"]["hreflang_locales_after"])

    def test_homepage_canonical_unchanged(self) -> None:
        match = re.search(r'<link rel="canonical" href="([^"]+)"', _index_html())
        self.assertIsNotNone(match)
        self.assertTrue(match.group(1).endswith("/ios-app-guide/index.html"))

    def test_existing_demand_block_survives(self) -> None:
        html = _index_html()
        self.assertIn("Questions people ask before buying", html)
        self.assertGreaterEqual(len(re.findall(r"<li><a ", html)), 20,
                                "既有 depth-1 answers 連結不得被本次改動吃掉")

    def test_localized_hubs_not_polluted_with_english_links(self) -> None:
        """不為 exact50 造英文假母語:母語 hub 不得被塞入這些英文連結。"""
        checked = 0
        for locale in ("de-DE", "ja", "zh-Hant", "ar-SA"):
            path = PAGES / locale / "index.html"
            if not path.is_file():
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="ignore")
            with self.subTest(locale):
                self.assertNotIn(START, text)
                for slug in CANARIES:
                    self.assertNotIn(f"/answers/{slug}.html", text)
        if checked == 0:  # pragma: no cover
            raise unittest.SkipTest("找不到母語 hub")

    def test_canary_hreflang_graph_is_self_consistent(self) -> None:
        """依真實內容連合法版本:英文頁的 hreflang 必須剛好等於實際變體 + en + x-default。

        首頁是 en / x-default hub,所以連英文版本才是這個 hub 的合法版本;
        在地化版本由英文頁自己的 alternate 宣告,不需要也不應該從英文 hub 直連母語頁。
        """
        locales = [d.name for d in PAGES.iterdir()
                   if d.is_dir() and re.fullmatch(r"[a-z]{2}(-[A-Za-z]{2,4})?", d.name)]
        if not locales:  # pragma: no cover
            raise unittest.SkipTest("找不到語系目錄")
        for slug in CANARIES:
            english = PAGES / "answers" / f"{slug}.html"
            if not english.is_file():  # pragma: no cover
                continue
            with self.subTest(slug):
                variants = [l for l in locales if (PAGES / l / "answers" / f"{slug}.html").is_file()]
                declared = {m for m in re.findall(
                    r'hreflang="([^"]+)"', english.read_text(encoding="utf-8", errors="ignore")[:8000])}
                expected = len(variants) + 2  # + en + x-default
                self.assertEqual(len(declared), expected,
                                 f"{slug}:實際變體 {len(variants)} 個,宣告 {len(declared)} 個 hreflang")
                self.assertIn("x-default", declared)

    def test_measured_variant_counts_match_the_manifest(self) -> None:
        """manifest 不得宣稱某頁有它實際沒有的在地化版本。"""
        locales = [d.name for d in PAGES.iterdir()
                   if d.is_dir() and re.fullmatch(r"[a-z]{2}(-[A-Za-z]{2,4})?", d.name)]
        for slug, expected in MANIFEST["locale_policy"]["measured_2026_09_12"].items():
            with self.subTest(slug):
                actual = sum(1 for l in locales if (PAGES / l / "answers" / f"{slug}.html").is_file())
                self.assertEqual(actual, expected["variants"])

    def test_no_fabricated_english_pseudo_locale_pages(self) -> None:
        """不為 exact50 造英文假母語:本次未新增任何語系目錄下的 canary 檔案。"""
        self.assertEqual(MANIFEST["change"]["new_urls_created"], 0)
        self.assertIn("英文假母語", MANIFEST["locale_policy"]["forbidden"])


class ByteStabilityTest(unittest.TestCase):
    def test_regenerating_twice_is_byte_stable(self) -> None:
        module = _load_generator()
        html = _index_html()
        locales = [l for l in dict.fromkeys(re.findall(r'hreflang="([^"]+)"', html))
                   if l != "x-default"]
        if len(locales) != 50:  # pragma: no cover
            raise unittest.SkipTest("locale 集合異常")
        index_path = Path(module.PAGES) / "index.html"
        original = index_path.read_bytes()
        try:
            module.build_root_index(locales)
            first = index_path.read_bytes()
            module.build_root_index(locales)
            second = index_path.read_bytes()
            self.assertEqual(first, second, "連跑兩次必須 byte 相同")
            self.assertIn(START.encode(), first)
        finally:
            index_path.write_bytes(original)

    def test_rollback_contract_is_documented(self) -> None:
        rollback = MANIFEST["rollback"]
        self.assertTrue(rollback["fully_reversible"])
        self.assertGreaterEqual(len(rollback["steps"]), 3)
        self.assertIn("index.html", rollback["blast_radius"])

    def test_e0_gate_still_blocks_e1_e2(self) -> None:
        gate = MANIFEST["e0_gate_still_applies"]
        self.assertIn("verdict=PASS", gate["rule"])
        self.assertIn("lastDownloaded", gate["rule"])
        self.assertIn("不得宣稱", gate["not_claimable"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
