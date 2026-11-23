"""K1 停新增網址守門：新網址 0、網站地圖不增、既有頁照產、14 天新款 en-* 例外。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import new_url_freeze  # noqa: E402

SITE = "https://open.cait518.cc/ios-app-guide"
TODAY = date(2026, 11, 23)


def sitemap(*paths: str) -> str:
    body = "".join(
        f"\n  <url>\n    <loc>{SITE}/{p}</loc>\n    <lastmod>2026-11-20</lastmod>\n  </url>"
        for p in paths
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}\n</urlset>\n"
    )


def locs(path: Path) -> set[str]:
    return set(new_url_freeze._LOC_RE.findall(path.read_text(encoding="utf-8")))


class NewUrlFreezeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.pages = root / "site"
        self.pages.mkdir()
        self.flag = root / "flag.json"
        self.flag.write_text(json.dumps({"freeze_new_urls": True}), encoding="utf-8")
        self.launch = root / "launch.json"
        self.launch.write_text(
            json.dumps({"apps": [
                {"key": "jellyday", "上架": "2026-11-21"},
                {"key": "oldapp", "上架": "2026-10-01"},
            ]}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.log = root / "freeze_log.json"
        (self.pages / "en-US").mkdir()
        (self.pages / "ja").mkdir()
        (self.pages / "en-US" / "snapport.html").write_text("<p>v1</p>", encoding="utf-8")
        (self.pages / "sitemap.xml").write_text(sitemap("en-US/snapport.html"), encoding="utf-8")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q"], cwd=self.pages, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.pages, check=True)
        subprocess.run([*git, "commit", "-qm", "base"], cwd=self.pages, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def enforce(self):
        return new_url_freeze.enforce(
            self.pages, stage="test", today=TODAY, flag_path=self.flag,
            launch_list=self.launch, log_path=self.log,
        )

    def test_new_url_blocked_sitemap_unchanged_existing_regenerated(self):
        before = locs(self.pages / "sitemap.xml")
        # 產生器本輪：重產既有頁、新增一頁、網站地圖加一條新網址、多一張新網站地圖
        (self.pages / "en-US" / "snapport.html").write_text("<p>v2</p>", encoding="utf-8")
        (self.pages / "ja" / "brand-new-guide.html").write_text("new", encoding="utf-8")
        (self.pages / "sitemap.xml").write_text(
            sitemap("en-US/snapport.html", "ja/brand-new-guide.html"), encoding="utf-8"
        )
        (self.pages / "sitemap_new.xml").write_text(sitemap("ja/x.html"), encoding="utf-8")
        result = self.enforce()
        # 新網址 0
        self.assertFalse((self.pages / "ja" / "brand-new-guide.html").exists())
        self.assertFalse((self.pages / "sitemap_new.xml").exists())
        self.assertEqual(new_url_freeze.untracked_url_files(self.pages), [])
        # 網站地圖不增
        self.assertEqual(locs(self.pages / "sitemap.xml"), before)
        # 既有頁照常重產
        self.assertEqual(
            (self.pages / "en-US" / "snapport.html").read_text(encoding="utf-8"), "<p>v2</p>"
        )
        self.assertEqual(sorted(result["blocked"]), ["ja/brand-new-guide.html", "sitemap_new.xml"])
        log = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(log["blocked_new_urls"], 2)
        self.assertEqual(log["stripped_sitemap_url_count"], 1)
        # 冪等：再跑一次不再擋任何東西、累計不重複
        again = self.enforce()
        self.assertEqual(again["blocked"], [])
        self.assertEqual(json.loads(self.log.read_text(encoding="utf-8"))["blocked_new_urls"], 2)

    def test_structural_browse_pages_kept(self):
        # gen_link_hubs 在關口之後產生的分頁結構頁不可刪（避免既有頁死連結）
        (self.pages / "videos").mkdir()
        (self.pages / "videos" / "browse.html").write_text("hub", encoding="utf-8")
        (self.pages / "videos" / "browse-2.html").write_text("hub2", encoding="utf-8")
        (self.pages / "sitemap.xml").write_text(
            sitemap("en-US/snapport.html", "videos/browse.html"), encoding="utf-8"
        )
        result = self.enforce()
        self.assertTrue((self.pages / "videos" / "browse.html").exists())
        self.assertTrue((self.pages / "videos" / "browse-2.html").exists())
        self.assertEqual(result["blocked"], [])
        self.assertEqual(sorted(result["structural_kept"]), ["videos/browse-2.html", "videos/browse.html"])
        self.assertIn(f"{SITE}/videos/browse.html", locs(self.pages / "sitemap.xml"))

    def test_pages_not_repo_root_is_skipped(self):
        # 站台目錄是儲存庫子目錄時 git status 路徑會錯位：必須略過、不誤報
        sub = self.pages / "en-US"
        (sub / "new.html").write_text("n", encoding="utf-8")
        result = new_url_freeze.enforce(
            sub, stage="test", today=TODAY, flag_path=self.flag,
            launch_list=self.launch, log_path=self.log,
        )
        self.assertTrue(result.get("skipped"))
        self.assertTrue((sub / "new.html").exists())

    def test_new_app_exception_only_en_locales(self):
        self.assertTrue(new_url_freeze.allow_new_url(
            "en-US/jellyday.html", TODAY, flag_path=self.flag, launch_list=self.launch))
        self.assertTrue(new_url_freeze.allow_new_url(
            f"{SITE}/en-AU/jellyday.html", TODAY, flag_path=self.flag, launch_list=self.launch))
        self.assertFalse(new_url_freeze.allow_new_url(
            "ja/jellyday.html", TODAY, flag_path=self.flag, launch_list=self.launch))
        self.assertFalse(new_url_freeze.allow_new_url(
            "en-US/oldapp.html", TODAY, flag_path=self.flag, launch_list=self.launch))
        # 實際產生：en-US 留、ja 擋；網站地圖只多 en-US 那條
        for locale in ("en-US", "ja"):
            (self.pages / locale / "jellyday.html").write_text("j", encoding="utf-8")
        (self.pages / "sitemap.xml").write_text(
            sitemap("en-US/snapport.html", "en-US/jellyday.html", "ja/jellyday.html"),
            encoding="utf-8",
        )
        self.enforce()
        self.assertTrue((self.pages / "en-US" / "jellyday.html").exists())
        self.assertFalse((self.pages / "ja" / "jellyday.html").exists())
        self.assertEqual(
            locs(self.pages / "sitemap.xml"),
            {f"{SITE}/en-US/snapport.html", f"{SITE}/en-US/jellyday.html"},
        )
        # 滿 14 天後例外失效
        self.assertFalse(new_url_freeze.allow_new_url(
            "en-US/jellyday.html", date(2026, 12, 6), flag_path=self.flag,
            launch_list=self.launch))

    def test_flag_off_is_noop(self):
        self.flag.write_text(json.dumps({"freeze_new_urls": False}), encoding="utf-8")
        (self.pages / "ja" / "brand-new-guide.html").write_text("new", encoding="utf-8")
        self.assertEqual(self.enforce(), {"frozen": False})
        self.assertTrue((self.pages / "ja" / "brand-new-guide.html").exists())
        self.assertTrue(new_url_freeze.allow_new_url(
            "ja/anything.html", TODAY, flag_path=self.flag, launch_list=self.launch))

    def test_repo_flag_is_on(self):
        self.assertTrue(new_url_freeze.is_frozen())


if __name__ == "__main__":
    unittest.main()
