#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""連結圖的兩條防線:browse 頁的生命週期,以及發布前的可索引孤兒閘門。

背景(2026-08-12):`gen_link_hubs.py` 是「把受管理區塊注入既有頁面」,但
`build_pages_i18n.py` 之類的產生器會整份重寫語系首頁。只要有一支跑在它後面
把區塊洗掉,整個語系的子樹就會變成孤兒 —— 2026-08-10 就這樣上線過:全站語系
首頁都沒有 hub 導覽,4,413 個**可索引**頁零入連,而且當時的稽核因為只讀檔案
前 4KB 判斷 noindex,把這件事報成 0。

這裡守的是:
1. browse 頁一定帶擁有者記號、一定是 noindex,follow(薄頁不該進索引);
2. 不再產生的 browse 頁會被刪掉,別人的同名檔案不會被誤刪;
3. `audit_link_depth.py` 以**可索引頁**為主要分母,noindex 頁分開列;
4. `--max-indexable-orphans` 真的會擋下來,而且 publish.py 有把它接上。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
sys.path.insert(0, GEO)

import audit_link_depth  # noqa: E402
import build_pages_i18n  # noqa: E402
import gen_link_hubs  # noqa: E402

SITE = "https://example.test/site"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def page(body, noindex=False, filler=0):
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    # robots 標籤刻意塞在很後面:整份讀才找得到,只讀前 4KB 會漏判。
    pad = "<!--" + ("x" * filler) + "-->" if filler else ""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>t</title>{pad}{robots}</head><body><main>{body}</main>"
        "</body></html>"
    )


class BrowsePageLifecycleTests(unittest.TestCase):
    def test_browse_pages_are_marked_and_kept_out_of_the_index(self):
        out = gen_link_hubs.render_browse(
            "ko", "ko", [("", [("a.html", "A")])], 1,
            [f"{gen_link_hubs.SITE}/ko/browse.html"],
            f"{gen_link_hubs.SITE}/ko/index.html",
        )
        self.assertIn(gen_link_hubs.BROWSE_MARKER, out)
        self.assertIn('name="robots" content="noindex,follow"', out)

    def test_cleanup_removes_only_our_own_unwanted_browse_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = os.path.join(tmp, "pages")
            keep = os.path.join(pages, "ko", "browse.html")
            drop = os.path.join(pages, "api", "browse.html")
            drop2 = os.path.join(pages, "api", "browse-2.html")
            foreign = os.path.join(pages, "hand", "browse.html")
            write(keep, gen_link_hubs.BROWSE_MARKER + "<html></html>")
            write(drop, gen_link_hubs.BROWSE_MARKER + "<html></html>")
            write(drop2, gen_link_hubs.BROWSE_MARKER + "<html></html>")
            write(foreign, "<html>somebody else wrote this</html>")

            old_pages = gen_link_hubs.PAGES
            gen_link_hubs.PAGES = pages
            try:
                state = {
                    "check": False,
                    "changed": [],
                    "kept": {os.path.abspath(keep)},
                }
                gen_link_hubs.cleanup_stale_browse(state)
            finally:
                gen_link_hubs.PAGES = old_pages

            self.assertTrue(os.path.exists(keep))
            self.assertTrue(os.path.exists(foreign), "不可誤刪別人的檔案")
            self.assertFalse(os.path.exists(drop))
            self.assertFalse(os.path.exists(drop2))
            self.assertEqual(
                sorted(state["changed"]),
                ["- api/browse-2.html", "- api/browse.html"],
            )

    def test_check_mode_reports_without_deleting(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = os.path.join(tmp, "pages")
            drop = os.path.join(pages, "api", "browse.html")
            write(drop, gen_link_hubs.BROWSE_MARKER + "<html></html>")
            old_pages = gen_link_hubs.PAGES
            gen_link_hubs.PAGES = pages
            try:
                state = {"check": True, "changed": [], "kept": set()}
                gen_link_hubs.cleanup_stale_browse(state)
            finally:
                gen_link_hubs.PAGES = old_pages
            self.assertTrue(os.path.exists(drop))
            self.assertEqual(state["changed"], ["- api/browse.html"])


class RewriteSurvivalTests(unittest.TestCase):
    """語系首頁被整份重寫時,hub 導覽必須活下來。

    2026-08-12 實測:還原導覽後單獨跑一次 build_pages_i18n.py,57 個語系首頁
    只剩 6 個還留著導覽 —— 而它排在 publish.py 的第 2 步,gen_link_hubs 排在
    第 120 步。中間任何一支產生器失敗,發布就會停在孤兒狀態。
    """

    NAV = (
        "\n<!--iag-link-hub-nav-->\n"
        '<nav class="wrap link-hub-nav"><ul>'
        '<li><a href="https://x/ko/browse.html">All pages</a></li>'
        "</ul></nav>\n<!--/iag-link-hub-nav-->\n"
    )

    def test_managed_block_survives_a_full_rewrite_at_the_same_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "index.html")
            write(dest, "<html><body><main>old</main>" + self.NAV + "</body></html>")
            fresh = "<html><body><main>new</main></body></html>"
            out = build_pages_i18n.carry_over_link_hub_blocks(dest, fresh)
            self.assertIn("iag-link-hub-nav", out)
            self.assertIn("ko/browse.html", out)
            # 落點必須與 gen_link_hubs.splice() 一致,否則兩支會每輪互相翻頁。
            self.assertEqual(gen_link_hubs.splice(fresh, self.NAV), out)

    def test_missing_or_blockless_pages_are_returned_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = "<html><body><main>new</main></body></html>"
            missing = os.path.join(tmp, "nope.html")
            self.assertEqual(
                fresh, build_pages_i18n.carry_over_link_hub_blocks(missing, fresh)
            )
            plain = os.path.join(tmp, "plain.html")
            write(plain, "<html><body><main>old</main></body></html>")
            self.assertEqual(
                fresh, build_pages_i18n.carry_over_link_hub_blocks(plain, fresh)
            )

    def test_carry_over_is_read_before_truncate(self):
        """Read the old hub blocks before the idempotent write decision."""
        source = inspect_source(build_pages_i18n, "build_locale_index")
        carry = source.index("carry_over_link_hub_blocks(dest")
        write = source.index("write_text_if_changed(dest")
        self.assertLess(carry, write)


def inspect_source(module, func_name):
    import inspect

    return inspect.getsource(getattr(module, func_name))


class IndexableOrphanGateTests(unittest.TestCase):
    """在合成的小站上跑真正的稽核腳本(子行程,連 CLI 一起驗)。"""

    def build_site(self, tmp):
        pages = os.path.join(tmp, "pages")
        write(
            os.path.join(pages, "index.html"),
            page('<a href="/site/linked.html">linked</a>'),
        )
        write(os.path.join(pages, "linked.html"), page("reachable"))
        # 孤兒 1:可索引 —— 這一頁就是閘門要擋的東西。
        write(os.path.join(pages, "orphan.html"), page("orphan"))
        # 孤兒 2:刻意 noindex,而且 robots 標籤遠在 4KB 之後。
        write(
            os.path.join(pages, "stopped.html"),
            page("stopped", noindex=True, filler=12000),
        )
        return pages

    def run_audit(self, tmp, pages, *extra):
        reports = os.path.join(tmp, "reports")
        env = dict(
            os.environ, GEO_PAGES=pages, GEO_SITE=SITE, GEO_REPORTS=reports
        )
        proc = subprocess.run(
            [sys.executable, os.path.join(GEO, "audit_link_depth.py"), *extra],
            capture_output=True, text=True, env=env,
        )
        with open(os.path.join(reports, "link_depth.json"), encoding="utf-8") as fh:
            return proc, json.load(fh)

    def test_indexable_pages_are_the_primary_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = self.build_site(tmp)
            proc, summary = self.run_audit(tmp, pages)
            self.assertEqual(0, proc.returncode)
            self.assertEqual(4, summary["total_pages"])
            # noindex 頁不算進可索引母體,即使它的 robots 在第 12,000 byte。
            self.assertEqual(3, summary["indexable_pages"])
            self.assertEqual(1, summary["noindex_pages"])
            self.assertEqual(1, summary["indexable_orphans"])
            self.assertEqual(1, summary["noindex_orphans"])
            self.assertEqual(2, summary["indexable_reachable"])
            with open(
                os.path.join(tmp, "reports", "link_depth.md"), encoding="utf-8"
            ) as fh:
                md = fh.read()
            self.assertIn("母體=**可索引頁**", md)
            self.assertIn("刻意 noindex 的頁(分開列)", md)

    def test_equal_sized_sections_have_stable_report_order(self):
        urls = {
            f"{audit_link_depth.SITE}/zeta/one.html": "/dev/null",
            f"{audit_link_depth.SITE}/alpha/one.html": "/dev/null",
        }
        summary = audit_link_depth.summarize(
            {
                "url_to_path": urls,
                "depth": {url: 1 for url in urls},
                "noindex": set(),
                "broken": {"zeta": 1, "alpha": 1},
                "broken_samples": {
                    "zeta": {"z"},
                    "alpha": {"a"},
                },
                "read_mb": 0,
            }
        )

        self.assertEqual(
            ["alpha", "zeta"],
            list(summary["top_level"]),
        )
        self.assertEqual(
            ["alpha", "zeta"],
            list(summary["broken_links_by_section"]),
        )

    def test_broken_samples_are_selected_before_truncation_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = [
                f"{audit_link_depth.SITE}/missing-{index}.html"
                for index in range(8, 0, -1)
            ]
            body = "".join(
                f'<a href="{target}">missing</a>'
                for target in targets
            )
            write(os.path.join(tmp, "index.html"), page(body))
            with mock.patch.object(audit_link_depth, "PAGES", tmp):
                summary = audit_link_depth.summarize(
                    audit_link_depth.crawl()
                )

        self.assertEqual(
            sorted(targets)[:5],
            summary["broken_samples"]["root"],
        )

    def test_gate_fails_on_indexable_orphans_and_passes_without_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = self.build_site(tmp)
            proc, _ = self.run_audit(tmp, pages, "--max-indexable-orphans", "0")
            self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("可索引孤兒", proc.stderr)

            # 把孤兒接回首頁後,同一個閘門必須放行。
            write(
                os.path.join(pages, "index.html"),
                page(
                    '<a href="/site/linked.html">a</a>'
                    '<a href="/site/orphan.html">b</a>'
                ),
            )
            proc, summary = self.run_audit(
                tmp, pages, "--max-indexable-orphans", "0"
            )
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            self.assertEqual(0, summary["indexable_orphans"])
            # noindex 的孤兒不該讓閘門誤擋:它本來就不進索引。
            self.assertEqual(1, summary["noindex_orphans"])

    def test_orphan_sections_are_listed_without_a_page_count_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = self.build_site(tmp)
            _, summary = self.run_audit(tmp, pages)
            sections = {
                row["section"] for row in summary["indexable_orphan_sections"]
            }
            self.assertIn("root", sections)
            self.assertEqual(1, summary["indexable_orphan_section_count"])


class PipelineWiringTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(GEO, "publish.py"), encoding="utf-8") as fh:
            self.publish = fh.read()

    def test_publish_gates_on_zero_indexable_orphans_before_pushing(self):
        self.assertIn("audit_link_depth.py", self.publish)
        self.assertIn("--max-indexable-orphans", self.publish)
        gate = self.publish.index("--max-indexable-orphans")
        push = self.publish.index('"--no-push" in sys.argv:\n        print')
        self.assertLess(gate, push, "閘門必須跑在 commit/push 之前")

    def test_link_hubs_runs_again_after_the_generators_that_rewrite_pages(self):
        runs = [
            i for i in range(len(self.publish))
            if self.publish.startswith("gen_link_hubs.py", i)
        ]
        self.assertGreaterEqual(
            len(runs), 2, "gen_link_hubs 必須在管線尾段再跑一次才不會被洗掉"
        )
        dedupe = self.publish.index("dedupe_locale_meta.py")
        self.assertTrue(
            any(i > dedupe for i in runs),
            "第二趟要跑在 dedupe_locale_meta 之後(它會改頁面的 noindex 狀態)",
        )


if __name__ == "__main__":
    unittest.main()
