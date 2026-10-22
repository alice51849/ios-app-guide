#!/usr/bin/env python3
"""免費門的 answer 頁用免費兄弟版自己的事實產生(2026-10-17 稽核)。

根因:換門只換 id / 名稱 / 分享圖,付費 key 產生的 pill、featureList、
「listed strengths」與主題事實原封跟著換到免費版頁上(G+Money Lite 頁寫著
G+Money 的 `No ads`,DailyMate Lite 頁寫著 DailyMate 的 `Paid download`、
`47 languages`)。會換門的頁改在產生時就用免費版 key;不換門的頁維持付費 key。
"""
import html
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for path in (str(HERE), str(HERE.parent / "social")):
    if path not in sys.path:
        sys.path.insert(0, path)

import aeo_answers as A  # noqa: E402
import gen_free_first_links as F  # noqa: E402
from app_pairs import paid_to_free  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402

CATEGORY_Q = "best currency converter app"


def need_pair(paid):
    free = paid_to_free().get(paid)
    if not free or not APPSTORE.get(free):
        raise unittest.SkipTest(f"{paid} has no published free sibling")
    return free


class AnswerRenderKey(unittest.TestCase):
    def test_category_question_of_a_paid_app_renders_as_the_free_sibling(self):
        free = need_pair("gmoney")
        self.assertEqual(F.answer_render_key(CATEGORY_Q, "gmoney"), free)
        self.assertEqual(A.answer_key(CATEGORY_Q, "gmoney"), free)

    def test_free_and_unpaired_keys_are_unchanged(self):
        free = need_pair("gmoney")
        self.assertEqual(F.answer_render_key(CATEGORY_Q, free), free)
        unpaired = next(k for k in APPSTORE if k not in paid_to_free()
                        and k not in paid_to_free().values())
        self.assertEqual(F.answer_render_key(CATEGORY_Q, unpaired), unpaired)

    def test_paid_context_questions_keep_the_paid_key(self):
        need_pair("gmoney")
        # slug 帶 pro/upgrade、或明確要求零內購:這些頁本來就不換門。
        for question in ("gmoney pro features explained",
                         "travel money app with no in-app purchases"):
            with self.subTest(question=question):
                self.assertEqual(F.answer_render_key(question, "gmoney"), "gmoney")

    def test_paid_copy_answer_pages_keep_the_paid_key(self):
        """付費文案頁(付費事實斷言付費購買模式)不換門,所以也不改用免費 key。"""
        checked = 0
        for slug, paid in F.paid_model_answer_slugs().items():
            for question in A.queries.ALL.get(paid, []):
                if A.slugify(question) == slug:
                    checked += 1
                    self.assertEqual(F.answer_render_key(question, paid), paid, question)
        if not checked:
            self.skipTest("no paid-copy answer pages in the current corpus")


class CreatedFreeDoorPage(unittest.TestCase):
    def setUp(self):
        self.free = need_pair("gmoney")
        self.tmp = tempfile.TemporaryDirectory()
        self.pages = Path(self.tmp.name)
        answers = self.pages / "answers"
        answers.mkdir()
        # extract_style 需要一頁帶 <style> 的範本。
        (answers / "best-offline-document-scanner-app-for-iphone.html").write_text(
            "<html><head><style>body{margin:0}</style></head></html>",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_free_door_page_carries_only_the_free_apps_facts(self):
        slug = A.create_page("gmoney", CATEGORY_Q, pages_root=self.pages)
        self.assertEqual(slug, A.slugify(CATEGORY_Q))
        text = (self.pages / "answers" / f"{slug}.html").read_text(encoding="utf-8")
        self.assertIn(f"id{APPSTORE[self.free]}", text)
        self.assertNotIn(f"id{APPSTORE['gmoney']}", text)
        pills = [html.unescape(p) for p in
                 re.findall(r'<span class="pill">([^<]*)</span>', text)]
        self.assertEqual(pills, A.feature_list(self.free))
        for bullet in A.feature_list("gmoney"):
            if bullet not in A.feature_list(self.free):
                self.assertNotIn(f'<span class="pill">{html.escape(bullet)}</span>', text)


if __name__ == "__main__":
    unittest.main()
