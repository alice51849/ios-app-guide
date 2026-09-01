# -*- coding: utf-8 -*-
"""llms.txt 的 `## Optional` 降級:驗證符合 llmstxt.org 規範且不丟資料。

規範(https://llmstxt.org/):H1 必需;blockquote 摘要;H2 file list 區段,每項為
`[name](url)`;慣例性的 `Optional` 區段代表「需要縮短 context 時可整段跳過」。
"""
import os
import re
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
ROOT = os.path.dirname(GEO)
GEN = os.path.join(GEO, "gen_llms.py")


def _load():
    """只載入 gen_llms 的純函式,避開它匯入整個 GrowthEngine 相依樹。"""
    src = open(GEN, encoding="utf-8").read()
    start = src.index("# llms.txt 規範(https://llmstxt.org/)")
    end = src.index("def build_llms(comp_map, live_keys):")
    mod = types.ModuleType("gen_llms_optional")
    mod.re = re
    exec(compile(src[start:end], GEN, "exec"), mod.__dict__)
    return mod


M = _load()

SAMPLE = "\n".join([
    "# Site",
    "",
    "> Summary line.",
    "",
    "## Apps",
    "- [Mochi](https://apps.apple.com/app/id1): cute checklist",
    "",
    "## Bopomofo RO-Crate 1.3 research object",
    "- [RO-Crate](https://example.com/ro-crate.json): metadata",
    "",
    "## Buyer questions with direct answers",
    "- [Best scanner](https://example.com/a.html): answer",
    "",
    "## Bopomofo digital-preservation package (RFC 8493 BagIt 1.0)",
    "- English guide: https://example.com/bagit/",
    "- SHA-256 checksums: https://example.com/bagit/checksums.txt",
])

URL = re.compile(r"https?://[^\s)]+")


def urls(text):
    return set(URL.findall(text))


class TestOptionalDemotion(unittest.TestCase):
    def test_archival_sections_are_detected(self):
        self.assertTrue(M._is_optional_section("Bopomofo RO-Crate 1.3 research object"))
        self.assertTrue(M._is_optional_section("Accessible Bopomofo EPUB 3.3 reference"))
        self.assertTrue(M._is_optional_section("Bopomofo DCAT 3 open-data catalog"))

    def test_buyer_sections_are_not_optional(self):
        for title in ("Apps", "Buyer questions with direct answers",
                      "App alternatives (comparison pages)",
                      "Open static APIs (versioned, read-only, no API key)",
                      "Sitemaps"):
            self.assertFalse(M._is_optional_section(title), title)

    def test_optional_section_is_appended_last(self):
        out = M.demote_optional_sections(SAMPLE)
        titles = [t for t, _ in M.split_llms_sections(out)[1]]
        self.assertEqual(titles[-1], "Optional")
        self.assertEqual(titles[:3],
                         ["Apps", "Buyer questions with direct answers", "Optional"])

    def test_no_link_is_lost(self):
        self.assertEqual(urls(SAMPLE), urls(M.demote_optional_sections(SAMPLE)))

    def test_bare_url_items_become_spec_compliant_markdown_links(self):
        """規範要求每項是 `[name](url)`;裸 URL 項目要被轉換,且帶上區段脈絡。"""
        out = M.demote_optional_sections(SAMPLE)
        optional = out[out.index("## Optional"):]
        items = [l for l in optional.split("\n") if l.startswith("- ")]
        self.assertTrue(items)
        for item in items:
            self.assertRegex(item, r"^- \[[^\]]+\]\(https?://[^)]+\)")
        self.assertIn(
            "- [Bopomofo digital-preservation package (RFC 8493 BagIt 1.0) — "
            "English guide](https://example.com/bagit/)", items)

    def test_buyer_content_moves_ahead_of_archival_content(self):
        out = M.demote_optional_sections(SAMPLE)
        self.assertLess(out.index("Best scanner"), out.index("RO-Crate"))

    def test_h1_and_blockquote_survive(self):
        out = M.demote_optional_sections(SAMPLE)
        self.assertTrue(out.startswith("# Site"))
        self.assertIn("> Summary line.", out)

    def test_idempotent(self):
        once = M.demote_optional_sections(SAMPLE)
        self.assertEqual(once, M.demote_optional_sections(once))

    def test_noop_without_archival_sections(self):
        plain = "# Site\n\n> S.\n\n## Apps\n- [A](https://e.com): x"
        self.assertEqual(M.demote_optional_sections(plain), plain)

    def test_against_live_llms_txt_if_present(self):
        """對真實線上檔案跑一次:確認不丟連結且 Optional 排在最後。"""
        live = os.path.join(ROOT, "live-llms.txt")
        if not os.path.exists(live):
            self.skipTest("live-llms.txt 不存在")
        text = open(live, encoding="utf-8").read()
        out = M.demote_optional_sections(text)
        self.assertEqual(urls(text), urls(out))
        titles = [t for t, _ in M.split_llms_sections(out)[1]]
        self.assertEqual(titles[-1], "Optional")
        self.assertLess(len(titles), len(M.split_llms_sections(text)[1]))


if __name__ == "__main__":
    unittest.main()
