"""K1 停新增網址源頭擋：產生器不產新頁、列頁只列 HEAD 已有或准的頁（審核員退回 11-23）。"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import new_url_freeze  # noqa: E402

APP_ID = "1234567890"


def page(h1: str) -> str:
    return (
        f"<!doctype html><html lang=\"en\"><head><title>{h1}</title><style>body{{margin:0}}</style></head><body><main>"
        f"<h1>{h1}</h1><a href=\"https://apps.apple.com/app/id{APP_ID}\">get</a>"
        "</main></body></html>"
    )


class SiteFixture(unittest.TestCase):
    frozen = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name) / "site"
        (self.site / "answers").mkdir(parents=True)
        (self.site / "alternatives").mkdir()
        (self.site / "guides").mkdir()
        (self.site / "en-GB").mkdir()
        for rel, h1 in {
            "answers/old-scanner-answer.html": "Old scanner answer",
            "answers/old-scanner-tips.html": "Old scanner tips",
            "alternatives/snap-vs-old.html": "Snap vs old",
            "guides/snap.html": "Snap guide",
            "en-GB/snap.html": "Snap en-GB",
        }.items():
            (self.site / rel).write_text(page(h1), encoding="utf-8")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q"], cwd=self.site, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.site, check=True)
        subprocess.run([*git, "commit", "-qm", "base"], cwd=self.site, check=True)
        # 本輪別的產生器新產、HEAD 沒有的頁
        for rel, h1 in {
            "answers/new-scanner-answer.html": "New scanner answer",
            "alternatives/snap-vs-new.html": "Snap vs new",
            "guides/newapp.html": "New guide",
            "en-GB/newapp.html": "New en-GB",
        }.items():
            (self.site / rel).write_text(page(h1), encoding="utf-8")
        self.stack = ExitStack()
        frozen = self.frozen
        self.stack.enter_context(
            mock.patch.object(new_url_freeze, "is_frozen", lambda *a, **k: frozen)
        )
        self.stack.enter_context(
            mock.patch.object(new_url_freeze, "exception_paths", lambda *a, **k: set())
        )
        try:
            import aeo_answers
        except ImportError:  # pragma: no cover
            aeo_answers = None
        if aeo_answers is not None:
            # 微格式重整與本守門無關，測試頁不是完整答案頁
            self.stack.enter_context(mock.patch.object(
                aeo_answers, "reconcile_answer_microformats", lambda path: False))
        new_url_freeze.reset_listing_cache()

    def tearDown(self):
        self.stack.close()
        new_url_freeze.reset_listing_cache()
        self.tmp.cleanup()


class IsListableTest(SiteFixture):
    def test_tracked_listed_untracked_not(self):
        s = self.site
        self.assertTrue(new_url_freeze.is_listable("answers/old-scanner-answer.html", s))
        self.assertTrue(new_url_freeze.is_listable(s / "answers" / "old-scanner-answer.html", s))
        self.assertFalse(new_url_freeze.is_listable("answers/new-scanner-answer.html", s))
        self.assertFalse(new_url_freeze.is_listable(s / "answers" / "new-scanner-answer.html", s))
        self.assertFalse(new_url_freeze.is_listable(
            "https://example.invalid/ios-app-guide/answers/new-scanner-answer.html", s))
        self.assertTrue(new_url_freeze.is_listable(
            "https://example.invalid/ios-app-guide/answers/old-scanner-answer.html", s))
        # 結構頁、資料檔、目錄與 enforce 一致不擋
        self.assertTrue(new_url_freeze.is_listable("browse-2.html", s))
        self.assertTrue(new_url_freeze.is_listable("data/new.json", s))
        self.assertTrue(new_url_freeze.is_listable("data/packages/x/", s))

    def test_exception_allowed(self):
        with mock.patch.object(new_url_freeze, "exception_paths",
                               lambda *a, **k: {"en-GB/newapp.html"}):
            new_url_freeze.reset_listing_cache()
            self.assertTrue(new_url_freeze.is_listable("en-GB/newapp.html", self.site))

    def test_non_repo_root_not_judged(self):
        sub = self.site / "answers"
        self.assertTrue(new_url_freeze.is_listable("new-scanner-answer.html", sub))


class AeoAnswersTest(SiteFixture):
    def test_no_new_page_and_index_sitemap_skip_new_slug(self):
        import aeo_answers

        created = aeo_answers.create_page(
            "anykey", "Brand new frozen question for iPhone?", pages_root=self.site
        )
        self.assertIsNone(created)
        slug = aeo_answers.slugify("Brand new frozen question for iPhone?")
        self.assertFalse((self.site / "answers" / f"{slug}.html").exists())
        aeo_answers.regenerate_index(self.site)
        index = (self.site / "answers" / "index.html").read_text(encoding="utf-8")
        self.assertIn("answers/old-scanner-answer.html", index)
        self.assertNotIn("new-scanner-answer", index)
        aeo_answers.write_sitemap(self.site)
        sitemap = (self.site / "sitemap_answers.xml").read_text(encoding="utf-8")
        self.assertIn("answers/old-scanner-answer.html", sitemap)
        self.assertNotIn("new-scanner-answer", sitemap)

    def test_existing_page_refresh_not_blocked(self):
        import aeo_answers

        with mock.patch.object(aeo_answers, "slugify", lambda q: "old-scanner-answer"), \
             mock.patch.object(aeo_answers, "answer_key", lambda q, k: k), \
             mock.patch.object(aeo_answers, "default_content", lambda q, k: {}), \
             mock.patch.object(aeo_answers, "normalized_content", lambda r, q, k: {}), \
             mock.patch.object(aeo_answers, "render_page", lambda *a, **k: page("Refreshed")):
            slug = aeo_answers.create_page("k", "q", force=True, pages_root=self.site)
        self.assertEqual(slug, "old-scanner-answer")
        self.assertIn("Refreshed", (self.site / "answers" / "old-scanner-answer.html").read_text())


class ListersTest(SiteFixture):
    def test_related_answers_skip_untracked(self):
        import add_related_answers

        with mock.patch.object(add_related_answers, "ROOT", str(self.site)), \
             mock.patch.object(add_related_answers, "ANS", str(self.site / "answers")), \
             mock.patch.object(sys, "argv", ["add_related_answers.py"]):
            add_related_answers.main()
        old = (self.site / "answers" / "old-scanner-answer.html").read_text(encoding="utf-8")
        self.assertIn("related-answers", old)
        self.assertIn("old-scanner-tips.html", old)
        self.assertNotIn("new-scanner-answer", old)

    def test_gen_llms_lists_only_tracked(self):
        import gen_llms

        with mock.patch.object(gen_llms, "PAGES", str(self.site)):
            rows = gen_llms._resource_files(str(self.site / "guides"), {"snap", "newapp"}, "guides")
            urls = [url for _, url in rows]
            self.assertTrue(any(u.endswith("/guides/snap.html") for u in urls))
            self.assertFalse(any("newapp" in u for u in urls))
            alts = [u for _, u in gen_llms._resource_files(
                str(self.site / "alternatives"), {"snap"}, "alternatives")]
            self.assertTrue(any("snap-vs-old" in u for u in alts))
            self.assertFalse(any("snap-vs-new" in u for u in alts))
            self.assertEqual([loc for loc, _ in gen_llms._localized_app_guides("snap")], ["en-GB"])
            self.assertEqual(gen_llms._localized_app_guides("newapp"), [])

    def test_gen_hubs_exists_only_tracked(self):
        import gen_hubs

        with mock.patch.object(gen_hubs, "PAGES", str(self.site)):
            self.assertTrue(gen_hubs.exists("answers/old-scanner-answer.html"))
            self.assertFalse(gen_hubs.exists("answers/new-scanner-answer.html"))
            self.assertFalse(gen_hubs.exists("answers/missing.html"))


class AeoPagesTest(SiteFixture):
    def test_new_alternative_not_written_index_lists_tracked(self):
        import aeo_pages

        with mock.patch.object(aeo_pages, "PAGES", str(self.site)), \
             mock.patch.object(aeo_pages, "ALT", str(self.site / "alternatives")):
            self.assertFalse(aeo_pages.write_alternative("snap-vs-brandnew", "<h1>x</h1>"))
            self.assertFalse((self.site / "alternatives" / "snap-vs-brandnew.html").exists())
            self.assertTrue(aeo_pages.write_alternative("snap-vs-old", page("Snap vs old v2")))
            self.assertIn("v2", (self.site / "alternatives" / "snap-vs-old.html").read_text())
            self.assertEqual(aeo_pages.listable_alternatives(), ["snap-vs-old.html"])


class UnfrozenTest(SiteFixture):
    frozen = False

    def test_unfrozen_behaviour_unchanged(self):
        import aeo_answers
        import gen_hubs
        import gen_llms

        self.assertTrue(new_url_freeze.is_listable("answers/new-scanner-answer.html", self.site))
        aeo_answers.regenerate_index(self.site)
        index = (self.site / "answers" / "index.html").read_text(encoding="utf-8")
        self.assertIn("new-scanner-answer", index)
        with mock.patch.object(gen_hubs, "PAGES", str(self.site)):
            self.assertTrue(gen_hubs.exists("answers/new-scanner-answer.html"))
        with mock.patch.object(gen_llms, "PAGES", str(self.site)):
            rows = gen_llms._resource_files(str(self.site / "guides"), {"snap", "newapp"}, "guides")
            self.assertTrue(any("newapp" in u for _, u in rows))
        import aeo_pages

        with mock.patch.object(aeo_pages, "PAGES", str(self.site)), \
             mock.patch.object(aeo_pages, "ALT", str(self.site / "alternatives")):
            self.assertTrue(aeo_pages.write_alternative("snap-vs-brandnew", "<h1>x</h1>"))
            self.assertEqual(len(aeo_pages.listable_alternatives()), 3)


class FreezeCheckScriptTest(SiteFixture):
    def test_flags_untracked_answer_links(self):
        import new_url_freeze_check

        (self.site / "llms.txt").write_text(
            "- [old](https://example.invalid/ios-app-guide/answers/old-scanner-answer.html)\n",
            encoding="utf-8",
        )
        self.assertEqual(new_url_freeze_check.main([str(self.site)]), 0)
        (self.site / "answers" / "index.html").write_text(
            '<a href="https://example.invalid/ios-app-guide/answers/new-scanner-answer.html">n</a>'
            '<a href="https://example.invalid/ios-app-guide/en-GB/answers/x.html">x</a>',
            encoding="utf-8",
        )
        problems = new_url_freeze_check.check(self.site)
        self.assertEqual(
            problems, {"answers/index.html": ["answers/new-scanner-answer.html", "en-GB/answers/x.html"]}
        )
        self.assertEqual(new_url_freeze_check.main([str(self.site)]), 1)


if __name__ == "__main__":
    unittest.main()
