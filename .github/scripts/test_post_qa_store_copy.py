#!/usr/bin/env python3
"""post_qa 的倉儲文案守門（2026-10-23 稽核 S7）：紅燈款的社群文不可宣稱線上商店已不列的功能。"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import post_qa  # noqa: E402

sys.path.insert(0, str(post_qa.ENGINE_GEO))
import store_copy_drift as SCD  # noqa: E402

BATTAI = SCD.roster_ids()["battai"]
STORE = f"https://apps.apple.com/jp/app/id{BATTAI}?pt=118326163&ct=geo_pick&mt=8"


def report(status):
    return {"schema": SCD.SCHEMA, "apps": {"battai": {
        "status": status, "brands": ["BattAI"], "locales": {},
        "blocked_terms": ["サイクル", "充放電回数", "cycle"] if status == "red" else []}}}


class StaleClaimGateTests(unittest.TestCase):
    def check(self, text, status):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drift.json"
            path.write_text(json.dumps(report(status), ensure_ascii=False), encoding="utf-8")
            return post_qa.stale_claim_problems(text, STORE, report_path=path)

    def test_red_app_post_with_a_dropped_claim_is_refused_on_any_line(self):
        card = "バッテリー最大容量 いつ80%を切る？\n✓ 最大容量の推移と サイクル数\nApp Store で「BattAI」を検索"
        problems = self.check(card, "red")
        self.assertEqual(1, len(problems))
        self.assertIn("サイクル", problems[0])

    def test_green_app_or_missing_report_passes(self):
        card = "✓ 最大容量の推移と サイクル数"
        self.assertEqual([], self.check(card, "green"))
        self.assertEqual([], post_qa.stale_claim_problems(card, STORE, report_path="/nonexistent/drift.json"))
        self.assertEqual([], self.check("✓ 最大容量の推移 ✓ 電池レポート", "red"))


if __name__ == "__main__":
    unittest.main()
