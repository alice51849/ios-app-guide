#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""倉儲商店文案 × 線上商店頁 每日比對與「商店已不列宣稱」守門（離線，假的 Lookup）。

背景：2026-10-23 一億品質監督第 1 次報告 S7（電池健康分數、睡眠音效倉儲沒同步，意圖頁宣稱商店已不列的功能）。
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import store_copy_drift as drift  # noqa: E402

REPO = {
    "en-US": {"name": "BattAI: Battery health score", "description": (
        "BattAI\n\nHealth\n• Battery health score\n• Maximum capacity over time\n• Maximum capacity\n• Cycles\n\n"
        "Export data\n• Create a file on this device. Nothing is uploaded.")},
    "ja": {"name": "BattAI: バッテリー状態", "description": "状態\n• 最大容量の推移\n• 充放電回数\n\nデータを書き出す"},
}
LIVE = {
    "en-US": {"description": "BattAI\n\nHealth\n• Battery health score\n• Maximum capacity over time\n\nReports\n"
                             "• The same report saved as a PNG", "version": "1.1.7",
              "currentVersionReleaseDate": "2026-10-20T07:00:00Z"},
    "ja": {"description": "状態\n• 最大容量の推移\n\nレポート\n• すべてのデータをテキストの表に", "version": "1.1.7"},
}
CURATED = {"battai": {"terms": ["export", "書き出", "Maximum capacity over time"]}}


class CompareTests(unittest.TestCase):
    def test_drifted_app_is_red_with_dropped_claims_as_blocked_terms(self):
        app = drift.compare_app("battai", REPO, LIVE, CURATED)
        self.assertEqual("red", app["status"])
        self.assertEqual(["BattAI"], app["brands"])
        self.assertIn("Cycles", app["blocked_terms"])
        self.assertIn("充放電回数", app["blocked_terms"])
        self.assertIn("export", app["blocked_terms"])          # 人工補的詞
        self.assertIn("Export data", app["blocked_terms"])
        # 線上還有的說法不擋（人工詞也一樣）；只是改寫的條列（同字頭）不自動擋
        self.assertNotIn("Maximum capacity over time", app["blocked_terms"])
        self.assertNotIn("Maximum capacity", app["blocked_terms"])
        self.assertNotIn("データを書き出す", app["blocked_terms"])   # 同字頭「データ」線上還有 → 不自動擋，但人工詞「書き出」會擋
        self.assertIn("Cycles", app["locales"]["en-US"]["dropped"])
        self.assertIn("Reports", app["locales"]["en-US"]["added"])
        self.assertEqual("1.1.7", app["live_version"])

    def test_identical_copy_is_green_and_blocks_nothing(self):
        same = {loc: {"name": "BattAI: x", "description": rec["description"]} for loc, rec in LIVE.items()}
        app = drift.compare_app("battai", same, LIVE, CURATED)
        self.assertEqual("green", app["status"])
        self.assertEqual([], app["blocked_terms"])
        self.assertEqual([], drift.claim_problems(app, "BattAI shows cycles and export files."))

    def test_unknown_when_nothing_could_be_compared(self):
        self.assertEqual("unknown", drift.compare_app("battai", REPO, {}, CURATED)["status"])


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.app = drift.compare_app("battai", REPO, LIVE, CURATED)

    def test_sentence_with_brand_and_dropped_claim_is_blocked(self):
        problems = drift.claim_problems(self.app, "BattAIは最大容量の推移と充放電回数を表示します。")
        self.assertEqual(1, len(problems))
        self.assertIn("充放電回数", problems[0])
        self.assertTrue(drift.claim_problems(self.app, "Track trends.\nBattAI can export the data as a file."))

    def test_general_advice_without_the_brand_passes(self):
        text = ("iPhone 15 以降は設定で充放電回数を確認できます。\n"
                "BattAI shows maximum capacity over time and a battery report as a PNG.")
        self.assertEqual([], drift.claim_problems(self.app, text))

    def test_latin_terms_match_whole_words_and_single_app_posts_check_every_line(self):
        entry = dict(self.app, blocked_terms=["Sereno Pro", "cycle"], brands=["Sereno", "BattAI"])
        self.assertEqual([], drift.claim_problems(entry, "Sereno promění váš telefon."))
        self.assertTrue(drift.claim_problems(entry, "BattAI tracks cycles."))
        card = "When will battery health hit 80%?\n✓ Max capacity trend and cycle count\nSearch BattAI"
        self.assertEqual([], drift.claim_problems(entry, card))
        self.assertTrue(drift.claim_problems(entry, card, whole=True))

    def test_page_problems_without_a_report_lets_content_through(self):
        self.assertEqual([], drift.page_problems("BattAI shows cycles.", ["battai"], report={}))
        report = {"schema": drift.SCHEMA, "apps": {"battai": self.app}}
        self.assertTrue(drift.page_problems("BattAI shows cycles.", ["battai", "mochi"], report))


class GeneratorHookTests(unittest.TestCase):
    def test_html_page_checks_every_linked_app_including_meta_descriptions(self):
        battai = drift.roster_ids()["battai"]
        report = {"schema": drift.SCHEMA, "apps": {"battai": drift.compare_app("battai", REPO, LIVE, CURATED)}}
        page = (f'<html><head><meta name="description" content="BattAIは充放電回数を表示します。"></head><body>'
                f'<p>BattAI shows maximum capacity over time.</p>'
                f'<a href="https://apps.apple.com/jp/app/id{battai}?pt=1&amp;ct=x&amp;mt=8">DL</a></body></html>')
        problems = drift.html_page_problems(page, report, label="ja/x.html: ")
        self.assertEqual(1, len(problems))
        self.assertTrue(problems[0].startswith("ja/x.html: battai"))
        unlinked = page.replace(f"id{battai}", "id1234567890")
        self.assertEqual([], drift.html_page_problems(unlinked, report))


class ReportTests(unittest.TestCase):
    def test_fetch_live_batches_by_country_and_maps_track_ids(self):
        calls = []

        def fake(url):
            calls.append(url)
            if "country=jp" in url:
                raise OSError("down")
            return {"results": [{"trackId": 111, "description": "x", "version": "1"},
                                {"trackId": 999, "description": "not ours"}]}

        live, errors = drift.fetch_live({"battai": "111", "mochi": "222"}, fetch=fake, pause=0)
        self.assertEqual(len(drift.COUNTRY_LOCALES), len(calls))
        self.assertIn("id=111,222", calls[0])
        self.assertEqual({"description": "x", "version": "1", "currentVersionReleaseDate": None, "trackName": None},
                         live["battai"]["en-US"])
        self.assertNotIn("ja", live["battai"])
        self.assertEqual({}, live["mochi"])
        self.assertTrue(errors and errors[0].startswith("jp:"))

    def test_build_report_and_markdown_mark_red_apps(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "battai_full.json").write_text(json.dumps(REPO, ensure_ascii=False), encoding="utf-8")
            report = drift.build_report(Path(tmp), {"battai": "111", "mochi": "222"}, {"battai": LIVE},
                                        [], dt.datetime(2026, 10, 23, tzinfo=dt.timezone.utc), CURATED)
        self.assertEqual({"red": 1, "green": 0, "unknown": 1}, report["counts"])
        md = drift.render_md(report)
        self.assertIn("🔴 battai", md)
        self.assertIn("充放電回数", md)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(report, drift.load_report(path))

    def test_curated_terms_file_is_valid(self):
        curated = drift.load_curated()
        for key in ("battai", "sereno"):
            self.assertTrue(curated[key]["terms"])
            for term in curated[key]["terms"]:
                self.assertTrue(drift.usable_term(term), term)


if __name__ == "__main__":
    unittest.main()
