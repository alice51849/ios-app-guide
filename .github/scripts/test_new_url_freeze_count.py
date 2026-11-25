"""Unit tests for new_url_freeze_count.py: daily blocked-URL counts land in the repo as numbers only."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import new_url_freeze_count as nc  # noqa: E402

SOURCE = {
    "date": "2026-11-25",
    "frozen": True,
    "blocked_new_urls": 7,
    "stripped_sitemap_url_count": 3,
    "blocked_paths": ["ja/answers/secret-new-page.html"],
    "stripped_sitemap_urls": ["https://open.cait518.cc/ios-app-guide/ja/answers/secret-new-page.html"],
    "allowed_exceptions": ["en-US/kumo.html"],
    "stages": {"gen_link_hubs": {"blocked_new_urls": 7, "stripped_sitemap_urls": 0}},
}


class NewUrlFreezeCountTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / "new_url_freeze.json"
        self.output = self.tmp / "growth" / "new_url_freeze_count.json"
        self.frozen_log = self.tmp / "frozen_answers.log"

    def run_main(self, now, run_id="1", today=None, started_at=None, frozen_log=False):
        args = ["--source", str(self.source), "--output", str(self.output), "--now", now]
        if today:
            args += ["--today", today]
        if started_at:
            args += ["--started-at", started_at]
        if frozen_log:
            args += ["--frozen-log", str(self.frozen_log)]
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": run_id}):
            os.environ.pop("GEO_WORKFLOW_STARTED_AT", None)
            self.assertEqual(nc.main(args), 0)
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_numbers_only_no_urls(self):
        self.source.write_text(json.dumps(SOURCE), encoding="utf-8")
        doc = self.run_main("2026-11-25T02:00:00+00:00")
        text = self.output.read_text(encoding="utf-8")
        self.assertNotIn("secret-new-page", text)
        self.assertNotIn("kumo.html", text)
        self.assertEqual(doc["latest"]["blocked_new_urls"], 7)
        self.assertEqual(doc["latest"]["allowed_exception_count"], 1)
        self.assertEqual(doc["days"][0]["blocked_new_urls_max"], 7)

    def test_same_run_twice_counts_one_run_and_keeps_max(self):
        self.source.write_text(json.dumps(SOURCE), encoding="utf-8")
        self.run_main("2026-11-25T02:00:00+00:00", run_id="9")
        lower = dict(SOURCE, blocked_new_urls=2)
        self.source.write_text(json.dumps(lower), encoding="utf-8")
        doc = self.run_main("2026-11-25T03:00:00+00:00", run_id="9")
        day = doc["days"][0]
        self.assertEqual(day["runs"], 1)
        self.assertEqual(day["blocked_new_urls_max"], 7)
        self.assertEqual(day["blocked_new_urls_last"], 2)
        doc = self.run_main("2026-11-25T08:00:00+00:00", run_id="10")
        self.assertEqual(doc["days"][0]["runs"], 2)

    def test_missing_log_records_no_log(self):
        doc = self.run_main("2026-11-25T02:00:00+00:00")
        self.assertEqual(doc["latest"]["status"], "no_log")
        self.assertIsNone(doc["days"][0]["blocked_new_urls_max"])
        self.assertIsNone(doc["days"][0]["blocked_total_max"])

    def test_cross_midnight_run_uses_run_start_date(self):
        # 台北 11-25 21:30 開跑、11-26 01:00 落檔；守門計數檔已在午夜歸零成 11-26。
        self.source.write_text(json.dumps(dict(SOURCE, date="2026-11-26")), encoding="utf-8")
        doc = self.run_main("2026-11-25T17:00:00+00:00", started_at="2026-11-25T13:30:00Z")
        self.assertEqual(doc["latest"]["date"], "2026-11-25")
        self.assertEqual([d["date"] for d in doc["days"]], ["2026-11-25"])
        self.assertTrue(doc["latest"]["source_date_mismatch"])

    def test_frozen_lines_counted_into_total(self):
        self.source.write_text(json.dumps(SOURCE), encoding="utf-8")
        self.frozen_log.write_text(
            "FROZEN how-to-sleep: new answer URL blocked by new_url_freeze\n"
            "noise https://open.cait518.cc/ios-app-guide/answers/x.html\n"
            "FROZEN best-timer: new answer URL blocked by new_url_freeze\n"
            "FROZEN how-to-sleep: new answer URL blocked by new_url_freeze\n"
            "停新增網址：略過 4 個新比較頁（new_url_freeze）\n",
            encoding="utf-8",
        )
        doc = self.run_main("2026-11-25T02:00:00+00:00", frozen_log=True)
        latest = doc["latest"]
        self.assertEqual(latest["frozen_answer_pages"], 2)
        self.assertEqual(latest["frozen_alternative_pages"], 4)
        self.assertEqual(latest["frozen_new_pages"], 6)
        self.assertEqual(latest["blocked_total"], 13)
        self.assertEqual(doc["days"][0]["blocked_total_max"], 13)
        self.assertEqual(doc["days"][0]["frozen_new_pages_max"], 6)
        text = self.output.read_text(encoding="utf-8")
        self.assertNotIn("http", text)
        self.assertNotIn("how-to-sleep", text)
        self.assertNotIn("best-timer", text)

    def test_frozen_only_without_freeze_log(self):
        self.frozen_log.write_text("FROZEN a: new answer URL blocked\n", encoding="utf-8")
        doc = self.run_main("2026-11-25T02:00:00+00:00", frozen_log=True)
        self.assertEqual(doc["latest"]["status"], "frozen")
        self.assertIsNone(doc["latest"]["blocked_new_urls"])
        self.assertEqual(doc["days"][0]["blocked_total_max"], 1)

    def test_missing_frozen_log_is_null(self):
        self.source.write_text(json.dumps(SOURCE), encoding="utf-8")
        doc = self.run_main("2026-11-25T02:00:00+00:00", frozen_log=True)  # 檔案不存在
        latest = doc["latest"]
        self.assertIsNone(latest["frozen_answer_pages"])
        self.assertIsNone(latest["frozen_new_pages"])
        self.assertEqual(latest["blocked_total"], 7)
        self.assertIsNone(doc["days"][0]["frozen_new_pages_max"])
        doc = self.run_main("2026-11-25T02:00:00+00:00")  # 沒給 --frozen-log
        self.assertIsNone(doc["latest"]["frozen_new_pages"])

    def test_output_never_contains_urls(self):
        self.source.write_text(json.dumps(SOURCE), encoding="utf-8")
        self.run_main("2026-11-25T02:00:00+00:00")
        self.assertNotIn("http", self.output.read_text(encoding="utf-8"))

    def test_history_trimmed(self):
        old = {"days": [{"date": "2026-08-01", "runs": 1, "blocked_new_urls_max": 1}]}
        self.output.parent.mkdir(parents=True)
        self.output.write_text(json.dumps(old), encoding="utf-8")
        self.source.write_text(json.dumps(SOURCE), encoding="utf-8")
        doc = self.run_main("2026-11-25T02:00:00+00:00")
        self.assertEqual([d["date"] for d in doc["days"]], ["2026-11-25"])


if __name__ == "__main__":
    unittest.main()
