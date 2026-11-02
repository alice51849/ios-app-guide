#!/usr/bin/env python3
"""publish.py 提交前的站址與 sitemap 筆數檢查。

2026-11-02 Guide 355ac05aa9（同 10-19 4bce9c82）：以 origin 站址
https://alice51849.github.io/ios-app-guide 重產 1,083 檔、sitemap_index 由約
590 筆縮成 4 筆就推上指南站，Pages 部署被 canonical 閘門擋下。推送端要先擋。
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "geo"))

import publish  # noqa: E402

PUBLIC = "https://open.cait518.cc/ios-app-guide"
ORIGIN = "https://alice51849.github.io/ios-app-guide"


def _index(site, count):
    rows = "".join(
        f"  <sitemap><loc>{site}/apps/a{i}/sitemap.xml</loc></sitemap>\n"
        for i in range(count)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}</sitemapindex>\n"
    )


def _page(site, path="zh-Hant/snapport.html"):
    return (
        "<!doctype html><html><head>"
        f'<link rel="canonical" href="{site}/{path}">'
        "</head><body>ok</body></html>\n"
    )


class GuideSiteGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.pages = Path(self.temp.name)
        self.git("init", "-q")
        self.write("sitemap_index.xml", _index(PUBLIC, 20))
        self.write("zh-Hant/snapport.html", _page(PUBLIC))
        self.git("add", "-A")
        self.git(
            "-c", "user.name=t", "-c", "user.email=t@example.test",
            "commit", "-q", "-m", "base",
        )

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.pages, check=True,
                       capture_output=True)

    def write(self, name, text):
        path = self.pages / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def stage(self):
        self.git("add", "-A")

    def problems(self):
        return publish.guide_site_problems(str(self.pages), PUBLIC)

    def test_correct_regeneration_passes(self):
        self.write("sitemap_index.xml", _index(PUBLIC, 21))
        self.write("zh-Hant/snapport.html", _page(PUBLIC) + "<!-- new -->")
        self.write("en-US/zodira.html", _page(PUBLIC, "en-US/zodira.html"))
        self.stage()
        self.assertEqual(self.problems(), [])
        publish.require_guide_site_identity(str(self.pages), PUBLIC)

    def test_origin_host_canonical_is_blocked(self):
        self.write("zh-Hant/snapport.html", _page(ORIGIN))
        self.stage()
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("canonical", problems[0])
        self.assertIn("alice51849.github.io", problems[0])

    def test_new_page_with_origin_canonical_is_blocked(self):
        self.write("en-US/zodira.html", _page(ORIGIN, "en-US/zodira.html"))
        self.stage()
        self.assertTrue(any("canonical" in p for p in self.problems()))

    def test_origin_host_sitemap_is_blocked(self):
        self.write("sitemap_index.xml", _index(ORIGIN, 20))
        self.stage()
        self.assertTrue(any("不在" in p and "sitemap_index.xml" in p
                            for p in self.problems()))

    def test_sitemap_collapse_below_half_is_blocked(self):
        # 355ac05aa9: ~590 → 4 entries, even when every loc is on the right host.
        self.write("sitemap_index.xml", _index(PUBLIC, 4))
        self.stage()
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("20", problems[0])
        self.assertIn("4", problems[0])

    def test_sitemap_shrink_to_half_is_allowed(self):
        self.write("sitemap_index.xml", _index(PUBLIC, 10))
        self.stage()
        self.assertEqual(self.problems(), [])

    def test_unstaged_files_are_not_judged(self):
        # Only what will actually be committed is checked.
        self.write("other.txt", "x")
        self.stage()
        self.write("zh-Hant/snapport.html", _page(ORIGIN))
        self.assertEqual(self.problems(), [])

    def test_public_site_equal_to_origin_is_blocked(self):
        self.write("zh-Hant/snapport.html", _page(ORIGIN) + "<!-- x -->")
        self.stage()
        problems = publish.guide_site_problems(str(self.pages), ORIGIN)
        self.assertTrue(any("origin" in p for p in problems))

    def test_require_raises_and_prints_error_annotation(self):
        self.write("sitemap_index.xml", _index(ORIGIN, 4))
        self.write("zh-Hant/snapport.html", _page(ORIGIN))
        self.stage()
        with self.assertRaises(publish.GuideSiteGuardBlocked):
            publish.require_guide_site_identity(str(self.pages), PUBLIC)

    def test_guard_runs_before_commit_in_main(self):
        source = (ROOT / "geo" / "publish.py").read_text(encoding="utf-8")
        main_body = source[source.index("def main():"):]
        guard = main_body.index("require_guide_site_identity(PAGES)")
        commit = main_body.index('"commit", "-m", "Update multilingual GEO pages"')
        push = main_body.index('"push", "-q", "origin", "main"')
        self.assertLess(guard, commit)
        self.assertLess(guard, push)


if __name__ == "__main__":
    unittest.main()
