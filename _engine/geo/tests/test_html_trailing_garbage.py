"""answers 頁 </html> 後面不能再有內容。

2026-10-16 稽核：152 頁 answers（含 Wordmate Lite best-home-screen-widget-app 英文母本）
在 </html> 後殘留舊版較長內容的尾巴，在地化產生器把它當內文而拒絕出頁。
gen_smart_app_banners 改成原子寫入；這裡守住整站不再出現。

同日清殘骸時，3 個 slug（19 個語系目錄共 57 頁）的 answer-microformat:end 剛好落在
</html> 後的殘骸裡，跟著被切掉，h-entry 外框 <div> 沒有收尾；geo-daily 的
reconcile_answer_microformats 因此拋 Incomplete answer microformat wrapper。
這裡也守住每頁的 microformat 外框標記成對且順序正確。
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


WRAPPER_MARKERS = (
    "<!-- answer-microformat:start -->",
    "<!-- answer-content:start -->",
    "<!-- answer-content:end -->",
    "<!-- answer-microformat:end -->",
)


def answer_wrapper_defect(text: str) -> bool:
    """Wrapper markers present but not exactly once each, in nesting order."""
    counts = [text.count(marker) for marker in WRAPPER_MARKERS]
    if not any(counts):
        return False
    if counts != [1, 1, 1, 1]:
        return True
    positions = [text.find(marker) for marker in WRAPPER_MARKERS]
    return positions != sorted(positions)


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

    def test_wrapper_detector(self):
        start, content_start, content_end, end = WRAPPER_MARKERS
        whole = f"<body>{start}<div>{content_start}<main></main>{content_end}</div>{end}</body>"
        self.assertFalse(answer_wrapper_defect("<body><main></main></body>"))
        self.assertFalse(answer_wrapper_defect(whole))
        self.assertTrue(answer_wrapper_defect(whole.replace(end, "")))
        self.assertTrue(answer_wrapper_defect(whole + end))
        self.assertTrue(answer_wrapper_defect(
            f"<body>{start}<div>{content_end}<main></main>{content_start}</div>{end}</body>"
        ))

    def test_every_answers_page_has_a_complete_microformat_wrapper(self):
        pages = _pages_root()
        if pages is None:
            self.skipTest("no published pages checkout (set GEO_PAGES)")
        offenders = [
            str(path.relative_to(pages))
            for path in sorted(pages.glob("answers/*.html")) + sorted(pages.glob("*/answers/*.html"))
            if answer_wrapper_defect(path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            offenders,
            [],
            f"{len(offenders)} answers pages have an incomplete answer microformat wrapper: {offenders[:10]}",
        )


if __name__ == "__main__":
    unittest.main()
