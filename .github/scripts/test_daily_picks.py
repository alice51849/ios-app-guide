#!/usr/bin/env python3
"""Offline tests for daily_picks.py (no network)."""

import datetime as dt
import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import daily_picks  # noqa: E402
import growth_scoreboard as gs  # noqa: E402
from test_app_improvements import validate  # noqa: E402

TODAY = dt.date(2026, 10, 14)
FOCUS, NEAR, OTHER = "6818607603", "6785004775", "6802166527"


def _growth(tmp):
    root = Path(tmp)
    (root / "drafts" / "focusapp").mkdir(parents=True)
    (root / "focus.json").write_text(json.dumps({"apps": [
        {"key": "focusapp", "app_id": FOCUS, "spotlight_until": "2026-10-27"}]}), encoding="utf-8")
    (root / "drafts" / "focusapp" / "push-kit.json").write_text(json.dumps({"app_id": FOCUS, "posts": [
        {"channel": "threads", "market": "tw", "lang": "zh-Hant", "ct": "un_tw_threads_1", "text": "衝榜貼文一。連結放留言。"},
        {"channel": "x", "market": "jp", "lang": "ja", "ct": "un_jp_x_1", "text": "X 貼文"},
    ]}), encoding="utf-8")
    (root / "app-posts.json").write_text(json.dumps({"posts": [
        {"app_id": OTHER, "lang": "zh-Hant", "ct": "other_1", "text": "其他 App 貼文"},
        {"app_id": NEAR, "lang": "en", "ct": "near_en", "text": "Near post in English"},
        {"app_id": NEAR, "lang": "zh-Hant", "ct": "near_tw", "text": "最接近第一名的 App"},
        {"app_id": NEAR, "lang": "ja", "ct": "near_ja", "text": "日本語"},
        {"app_id": OTHER, "lang": "zh-Hant", "ct": "too_long", "text": "長" * 600},
        {"app_id": "1", "lang": "zh-Hant", "ct": "gone", "text": "下架 App"},
    ]}), encoding="utf-8")
    return root


def _state():
    state = gs.empty_state()
    state["search"]["x"] = {"app_id": NEAR, "locale": "cs", "country": "cz", "keyword": "k",
                            "rank": 2, "top": {"ratings": 0}}
    return state


class DailyPicksTests(unittest.TestCase):
    def test_focus_first_then_closest_to_first_one_app_each(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _growth(tmp)
            picks = daily_picks.choose(TODAY, {FOCUS, NEAR, OTHER}, _state(), root)
        self.assertEqual([FOCUS, NEAR, OTHER], [c["app_id"] for c, _ in picks])
        self.assertEqual(["un_tw_threads_1", "near_tw", "other_1"], [c["ct"] for c, _ in picks])
        first = picks[0][1]
        self.assertNotIn("連結放留言", first)
        self.assertIn("https://apps.apple.com/tw/app/id6818607603?pt=118326163&ct=un_tw_threads_1&mt=8", first)
        self.assertTrue(all(len(text) <= daily_picks.THREADS_LIMIT for _, text in picks))

    def test_focus_window_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _growth(tmp)
            picks = daily_picks.choose(dt.date(2026, 10, 28), {FOCUS, NEAR, OTHER}, None, root)
        self.assertNotIn(FOCUS, [c["app_id"] for c, _ in picks])
        self.assertEqual(2, len(picks))

    def test_apply_replaces_yesterdays_picks_and_stays_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _growth(tmp)
            picks = daily_picks.choose(TODAY, {FOCUS, NEAR, OTHER}, _state(), root)
        document = {
            "schema_version": 1, "updated_at": "2026-10-13T00:00:00Z",
            "owner_actions": [
                {"id": "oa-today-1", "title": "old", "status": "todo"},
                {"id": "oa-keep", "title": "keep", "status": "todo"},
            ],
            "apps": [],
        }
        now = dt.datetime(2026, 10, 14, 3, 0, tzinfo=dt.timezone.utc)
        daily_picks.apply(document, picks, {FOCUS: "UsageNow"}, now)
        ids = [a["id"] for a in document["owner_actions"]]
        self.assertEqual(["oa-today-1", "oa-today-2", "oa-today-3", "oa-keep"], ids)
        self.assertIn("UsageNow", document["owner_actions"][0]["title"])
        url = document["owner_actions"][0]["url"]
        self.assertTrue(url.startswith("https://www.threads.net/intent/post?text="))
        self.assertIn("衝榜貼文一", urllib.parse.unquote(url))
        self.assertEqual("2026-10-14T03:00:00Z", document["updated_at"])
        self.assertEqual([], validate(document, set()))


if __name__ == "__main__":
    unittest.main()
