"""answers 頁 </html> 後面不能再有內容。

2026-10-16 稽核：152 頁 answers（含 Wordmate Lite best-home-screen-widget-app 英文母本）
在 </html> 後殘留舊版較長內容的尾巴，在地化產生器把它當內文而拒絕出頁。
gen_smart_app_banners 改成原子寫入；這裡守住整站不再出現。
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_smart_app_banners  # noqa: E402

TAIL_BYTES = 16384


def _pages_root() -> Path | None:
    candidates = []
    configured = os.environ.get("GEO_PAGES")
    if configured:
        candidates.append(Path(configured))
    candidates.extend((GEO / "pages", GEO.parents[1]))
    return next((path for path in candidates if (path / "answers").is_dir()), None)


def trailing_garbage(path: Path) -> bool:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - TAIL_BYTES))
        tail = handle.read().decode("utf-8", errors="replace")
    first = tail.find("</html>")
    return first >= 0 and bool(tail[first + len("</html>"):].strip())


class TrailingGarbageTests(unittest.TestCase):
    def test_detector(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.html"
            bad = Path(tmp) / "bad.html"
            good.write_text("<html><body>x</body></html>\n", encoding="utf-8")
            bad.write_text("<html><body>x</body></html>tail</script>\n</body></html>\n", encoding="utf-8")
            self.assertFalse(trailing_garbage(good))
            self.assertTrue(trailing_garbage(bad))

    def test_write_if_changed_replaces_the_whole_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_text("<html>" + "x" * 500 + "</html>\n", encoding="utf-8")
            os.chmod(page, 0o644)
            self.assertTrue(gen_smart_app_banners._write_if_changed(page, "<html>y</html>\n"))
            self.assertEqual(page.read_text(encoding="utf-8"), "<html>y</html>\n")
            self.assertEqual(page.stat().st_mode & 0o777, 0o644)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["page.html"])
            self.assertFalse(gen_smart_app_banners._write_if_changed(page, "<html>y</html>\n"))

    def test_no_answers_page_has_content_after_html_end(self):
        pages = _pages_root()
        if pages is None:
            self.skipTest("no published pages checkout (set GEO_PAGES)")
        offenders = [
            str(path.relative_to(pages))
            for path in sorted(pages.glob("answers/*.html")) + sorted(pages.glob("*/answers/*.html"))
            if trailing_garbage(path)
        ]
        self.assertEqual(offenders, [], f"{len(offenders)} answers pages have content after </html>")


if __name__ == "__main__":
    unittest.main()
