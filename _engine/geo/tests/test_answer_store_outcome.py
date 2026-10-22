#!/usr/bin/env python3
"""答案頁的一句話定位用線上商店原文(2026-10-17 稽核)。

registry 的 sub 同時餵 App 查找器目錄指紋與 threads-autopilot 封印,不能為了
答案頁直接改;商店已改版的款(Aim990:舊 sub「score tracking toward 990」商店
沒有)由 answer_text.STORE_ALIGNED_OUTCOME 覆寫,答案頁產生器一律經
answer_outcome() 取定位。
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for path in (str(HERE), str(HERE.parent / "social")):
    if path not in sys.path:
        sys.path.insert(0, path)

import aeo_answers as A  # noqa: E402
import gen_roundups as R  # noqa: E402
from answer_text import STORE_ALIGNED_OUTCOME, answer_outcome  # noqa: E402
from videogen.registry import APPS  # noqa: E402

AIM_STORE = (
    "An 8-minute diagnosis finds your 3 weakest skills, drills them daily "
    "and rechecks on Day 30"
)


class AnswerStoreOutcomeTest(unittest.TestCase):
    def test_aim990_uses_store_wording(self):
        self.assertEqual(answer_outcome(APPS["aim990"]), AIM_STORE)
        self.assertNotIn("score tracking", answer_outcome(APPS["aim990"]).lower())

    def test_other_apps_keep_registry_sub(self):
        for key, app in APPS.items():
            if app.get("name") in STORE_ALIGNED_OUTCOME:
                continue
            self.assertEqual(answer_outcome(app), str(app.get("sub") or ""), key)

    def test_overrides_name_real_apps(self):
        names = {app.get("name") for app in APPS.values()}
        for name in STORE_ALIGNED_OUTCOME:
            self.assertIn(name, names)

    def test_answer_page_carries_store_outcome(self):
        q = "How to study for the TOEIC Listening and Reading test in 30 days"
        content = A.normalized_content(A.default_content(q, "aim990"), q, "aim990")
        text = json.dumps(content, ensure_ascii=False)
        self.assertIn(AIM_STORE, text)
        self.assertNotIn("score tracking toward 990", text)

    def test_roundup_uses_answer_outcome(self):
        import inspect

        self.assertIn("answer_outcome(a)", inspect.getsource(R.build))


if __name__ == "__main__":
    unittest.main()
