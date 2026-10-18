"""Unit tests for ta_finder_notice.py: Finder changes that threads-autopilot syncs are flagged, never blocking."""
from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ta_finder_notice as tn  # noqa: E402


def app(key, summary):
    return {"key": key, "name": key.title(), "category": "travel", "purchase_model": "paid_upfront",
            "app_store_id": "1", "canonical_app_store_url": "https://apps.apple.com/app/id1",
            "one_time_option": True, "verified_live": True,
            "summaries": {"en": summary, "ja": "旅"}, "purchase_labels": {"en": "One-time purchase"},
            "features": ["Offline"], "keywords": ["trip", "plan", "travel"],
            "capabilities": {"offline": True}, "page_url": "https://x/tripbee/"}


def catalog(*apps, generated_at="2026-10-17T16:54:57Z"):
    return {"record_count": len(apps), "publisher_disclosure": "First-party.", "generated_at": generated_at,
            "document_digest": generated_at, "apps": list(apps)}


class NoticeTests(unittest.TestCase):
    def test_summary_change_is_flagged_with_app_and_field(self):
        before = catalog(app("tripbee", "Old clipped summary"), app("caldaily", "Same"))
        after = catalog(app("tripbee", "Plan every trip day by day."), app("caldaily", "Same"))
        rows = tn.changes(before, after)
        self.assertEqual([("tripbee", ["summaries.en"])], rows)
        warning, trailer = tn.notice(rows)
        self.assertTrue(warning.startswith("::warning title=TA 需要排重封::data/verified-ios-app-finder-catalog.json"))
        for needle in ("tripbee summaries.en", "PUBLISHER_REVIEWED_SOURCE_DIGEST", "TA 需要重封", "不擋 Guide 發布"):
            self.assertIn(needle, warning)
        self.assertTrue(trailer.startswith("TA-reseal: "))

    def test_fields_threads_autopilot_does_not_read_stay_quiet(self):
        before = catalog(app("tripbee", "Same"))
        after = copy.deepcopy(catalog(app("tripbee", "Same"), generated_at="2026-10-18T00:00:00Z"))
        after["apps"][0]["summaries"]["ja"] = "別の要約"
        after["apps"][0]["page_url"] = "https://y/tripbee/"
        self.assertEqual([], tn.changes(before, after))

    def test_added_and_removed_apps_are_flagged(self):
        rows = tn.changes(catalog(app("tripbee", "A")), catalog(app("caldaily", "B")))
        self.assertEqual([("caldaily", ["(新增)"]), ("tripbee", ["(移除)"])], rows)

    def test_staged_change_writes_the_commit_paragraph_and_exits_zero(self):
        root = Path(tempfile.mkdtemp())
        git = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)  # noqa: E731
        git("init", "-q")
        git("config", "user.email", "t@example.invalid")
        git("config", "user.name", "t")
        (root / "data").mkdir()
        path = root / tn.FINDER
        path.write_text(json.dumps(catalog(app("tripbee", "Old"))), encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", "base")
        path.write_text(json.dumps(catalog(app("tripbee", "New"))), encoding="utf-8")
        git("add", "-A")
        trailer = root / "trailer.txt"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(0, tn.main(["--root", str(root), "--staged", "--trailer-file", str(trailer)]))
        self.assertIn("::warning title=TA 需要排重封::", out.getvalue())
        self.assertIn("tripbee summaries.en", trailer.read_text(encoding="utf-8"))
        git("commit", "-qm", "new")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(0, tn.main(["--root", str(root), "--staged", "--trailer-file", str(trailer)]))
        self.assertEqual("", trailer.read_text(encoding="utf-8"))
        self.assertNotIn("::warning", out.getvalue())

    def test_a_broken_catalogue_never_blocks_the_publish(self):
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        (root / "data").mkdir()
        (root / tn.FINDER).write_text("{not json", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(0, tn.main(["--root", str(root), "--staged"]))
        self.assertIn("::warning title=TA finder 提醒失敗::", out.getvalue())

    def test_geo_daily_runs_the_notice_in_both_commit_steps_without_failing_them(self):
        workflow = (HERE.parent / "workflows" / "geo-daily.yml").read_text(encoding="utf-8")
        for step, message in (("Commit English content first", "Daily GEO content: new answer pages + refreshed sitemaps"),
                              ("Commit localized pages if any", "Daily GEO content: localized answer pages")):
            body = workflow.split(f"- name: {step}", 1)[1].split("\n      - name:", 1)[0]
            notice = body.index("if ! python3 .github/scripts/ta_finder_notice.py --staged")
            self.assertLess(body.index("git add -A"), notice)
            self.assertIn('echo "::warning title=TA finder 提醒失敗::', body[notice:])  # a crash still publishes
            self.assertIn(f'git commit -m "{message}" ${{ta_trailer:+-m "$ta_trailer"}}', body)


if __name__ == "__main__":
    unittest.main()
