#!/usr/bin/env python3
"""Offline regression tests for the public App Store growth scoreboard."""

import datetime as dt
import io
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import growth_scoreboard as gs  # noqa: E402
from portfolio_daily import PublicApp  # noqa: E402

NOW = dt.datetime(2026, 10, 13, 2, 40, tzinfo=dt.timezone.utc)
APPS = [
    PublicApp(key="mochi", app_id="6785004775", name="Mochi", category="productivity"),
    PublicApp(key="cyca", app_id="6782251621", name="Cyca", category="health"),
]
STOREFRONTS = {"en-US": "us", "ja": "jp", "sl-SI": "si"}
KEYWORDS = {
    "mochi": {"en-US": ["to do list", "tasks"], "ja": ["タスク"], "sl-SI": ["opravila"]},
    "cyca": {"en-US": ["period tracker"], "ja": ["生理"], "sl-SI": ["menstruacija"]},
}


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, "fixture", {}, io.BytesIO(b""))


class FakeApple:
    """Routes lookup/search/chart URLs to fixture payloads."""

    def __init__(self, *, rate_limit_after=None, chart_status=None):
        self.calls = []
        self.rate_limit_after = rate_limit_after
        self.chart_status = chart_status
        self.searches = 0

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.calls.append(url)
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        if parsed.path == "/lookup":
            country = query["country"]
            counts = {"us": (19, 4.1), "jp": (0, 0), "si": (2, 5.0)}[country]
            return _Response(json.dumps({"results": [
                {"trackId": 6785004775, "userRatingCount": counts[0],
                 "averageUserRating": counts[1], "primaryGenreId": 6007,
                 "primaryGenreName": "Productivity", "price": 0},
                {"trackId": 6782251621, "userRatingCount": 1,
                 "averageUserRating": 5, "primaryGenreId": 6013,
                 "primaryGenreName": "Health & Fitness", "price": 0},
                {"trackId": 999, "userRatingCount": 10**6},
            ]}).encode())
        if parsed.path == "/search":
            self.searches += 1
            if self.rate_limit_after is not None and self.searches > self.rate_limit_after:
                raise _http_error(url, 429)
            term = query["term"]
            if term == "opravila":
                results = [{"trackId": 6785004775, "trackName": "Mochi", "userRatingCount": 2}]
            elif term == "to do list":
                results = [{"trackId": 111, "trackName": "Big Todo", "userRatingCount": 90000}] + [
                    {"trackId": 200 + i, "trackName": f"x{i}", "userRatingCount": 5} for i in range(5)
                ] + [{"trackId": 6785004775, "trackName": "Mochi", "userRatingCount": 19}]
            elif term == "menstruacija":
                results = [{"trackId": 333, "trackName": "Small Cycle", "userRatingCount": 12},
                           {"trackId": 6782251621, "trackName": "Cyca", "userRatingCount": 0}]
            else:
                results = [{"trackId": 444, "trackName": "Other", "userRatingCount": 7}]
            return _Response(json.dumps({"results": results}).encode())
        if "/rss/" in parsed.path:
            if self.chart_status:
                raise _http_error(url, self.chart_status)
            entries = [{"id": {"attributes": {"im:id": "555"}}},
                       {"id": {"attributes": {"im:id": "6785004775"}}}]
            return _Response(json.dumps({"feed": {"entry": entries}}).encode())
        raise AssertionError(f"unexpected URL {url}")


def _fetcher(fake):
    return gs.Fetcher(delay=0, opener=fake, sleeper=lambda _seconds: None)


class SourceTests(unittest.TestCase):
    def test_split_keywords_dedupes_and_respects_native_separators(self):
        self.assertEqual(["タスク", "ToDo", "メモ"], gs.split_keywords("タスク, ToDo、todo，メモ,習慣"))
        self.assertEqual([], gs.split_keywords(""))

    def test_engine_key_map_is_read_without_import(self):
        mapping = gs.load_key2data()
        self.assertEqual("weather_full.json", mapping["lumiweather"])
        self.assertEqual("mochi_full.json", mapping["mochi"])

    def test_every_live_app_has_native_keywords_in_every_locale(self):
        apps, storefronts, keywords, _challenge = gs.load_inputs()
        self.assertEqual(50, len(storefronts))
        for app in apps:
            with self.subTest(app=app.key):
                self.assertEqual(set(storefronts), set(keywords[app.key]))

    def test_first_pass_covers_top_keyword_everywhere_before_second(self):
        tasks = gs.build_tasks(APPS, STOREFRONTS, KEYWORDS)
        self.assertEqual(7, len(tasks))
        self.assertEqual({"to do list", "タスク", "opravila", "period tracker", "生理", "menstruacija"},
                         {t["keyword"] for t in tasks[:6]})
        self.assertEqual("tasks", tasks[-1]["keyword"])

    def test_challenge_terms_are_measured_first_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "challenge-terms.json"
            path.write_text(json.dumps({"apps": {
                "mochi": {"en-US": ["cute to do list", "To Do List", "to do list"], "xx": ["ignored"]},
            }}), encoding="utf-8")
            challenge = gs.load_challenge_terms(path)
        self.assertEqual({"mochi": {"en-US": ["cute to do list", "To Do List"], "xx": ["ignored"]}}, challenge)
        tasks = gs.build_tasks(APPS, STOREFRONTS, KEYWORDS, challenge)
        self.assertEqual(["cute to do list", "To Do List"], [t["keyword"] for t in tasks[:2]])
        self.assertEqual({"challenge"}, {t["source"] for t in tasks[:2]})
        self.assertEqual(9, len(tasks))
        self.assertNotIn("ignored", {t["keyword"] for t in tasks})

    def test_rotation_wraps_and_returns_next_cursor(self):
        self.assertEqual((["c", "a"], 1), gs.take_rotation(["a", "b", "c"], 2, 2))
        self.assertEqual((["a", "b", "c"], 0), gs.take_rotation(["a", "b", "c"], 0, 9))
        self.assertEqual(([], 5), gs.take_rotation([], 5, 3))


class RunTests(unittest.TestCase):
    def test_full_run_records_ratings_ranks_leader_and_charts(self):
        state = gs.empty_state()
        outcome = gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple()),
                         now=NOW, search_budget=100, chart_budget=100, log=lambda *_: None)
        self.assertEqual((3, 7, None), (outcome["lookups"], outcome["searches"], outcome["rate_limited"]))
        self.assertEqual(19, state["ratings"]["6785004775"]["us"]["count"])
        self.assertNotIn("999", state["ratings"])
        si = state["search"]["6785004775|sl-SI|opravila"]
        self.assertEqual(1, si["rank"])
        todo = state["search"]["6785004775|en-US|to do list"]
        self.assertEqual((7, 90000), (todo["rank"], todo["top"]["ratings"]))
        self.assertEqual(2, state["charts"]["us|6007|free"]["positions"]["6785004775"])
        self.assertEqual([{"date": "2026-10-13", "total": 19 + 2 + 3}], state["ratings_history"])
        self.assertEqual(0, state["cursor"])

    def test_rate_limit_stops_early_and_keeps_exact_progress(self):
        state = gs.empty_state()
        state["cursor"] = 1
        state["tasks_digest"] = gs.tasks_digest(gs.build_tasks(APPS, STOREFRONTS, KEYWORDS))
        outcome = gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple(rate_limit_after=2)),
                         now=NOW, search_budget=100, chart_budget=0, log=lambda *_: None)
        self.assertIn("429", outcome["rate_limited"])
        self.assertEqual(2, outcome["searches"])
        self.assertEqual(3, state["cursor"])
        self.assertEqual(1, len(state["ratings_history"]))

    def test_changed_task_list_restarts_rotation(self):
        state = gs.empty_state()
        gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple()),
               now=NOW, search_budget=3, chart_budget=0, log=lambda *_: None)
        self.assertEqual(3, state["cursor"])
        gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple()),
               now=NOW, search_budget=2, chart_budget=0, log=lambda *_: None)
        self.assertEqual(5, state["cursor"])
        challenge = {"mochi": {"ja": ["かわいい todo"]}}
        gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple()),
               now=NOW, search_budget=1, chart_budget=0, log=lambda *_: None, challenge_terms=challenge)
        self.assertEqual(1, state["cursor"])
        self.assertIn("6785004775|ja|かわいい todo", state["search"])

    def test_unavailable_charts_do_not_block_search_measurement(self):
        state = gs.empty_state()
        outcome = gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple(chart_status=404)),
                         now=NOW, search_budget=3, chart_budget=10, log=lambda *_: None)
        self.assertTrue(outcome["charts_unavailable"])
        self.assertEqual(3, outcome["searches"])
        self.assertEqual(3, state["cursor"])

    def test_fetcher_retries_transient_then_gives_up_on_permanent(self):
        responses = [_http_error("u", 503), _Response(b'{"ok": 1}')]

        def opener(request, timeout=None):
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        self.assertEqual({"ok": 1}, _fetcher(opener).get_json("https://itunes.apple.com/x"))

        def missing(request, timeout=None):
            raise _http_error(request.full_url, 404)

        with self.assertRaises(gs.FetchError):
            _fetcher(missing).get_json("https://itunes.apple.com/y")


class ReportTests(unittest.TestCase):
    def _state(self):
        state = gs.empty_state()
        gs.run(APPS, STOREFRONTS, KEYWORDS, state, _fetcher(FakeApple()),
               now=NOW, search_budget=100, chart_budget=100, log=lambda *_: None)
        return state

    def test_report_names_firsts_reachable_opportunities_and_charts(self):
        state = self._state()
        state["ratings_history"].insert(0, {"date": "2026-10-12", "total": 20})
        report = gs.build_report(APPS, state, {"searches": 7, "tasks_total": 7}, now=NOW)
        self.assertIn("評分總數：**24**（較上次 +4）", report)
        self.assertIn("| Mochi | SI | sl-SI | opravila |", report)
        self.assertIn("| Cyca | SI (sl-SI) | menstruacija | 2 | Small Cycle | 12 |", report)
        self.assertIn("| Mochi | US | Productivity | 免費 | 2 |", report)
        self.assertNotIn("999", report)

    def test_opportunities_prefer_small_leaders(self):
        state = self._state()
        rows = gs.opportunities(state, {app.app_id: app.name for app in APPS})
        self.assertEqual("menstruacija", rows[0][1]["keyword"])
        self.assertEqual("to do list", rows[-1][1]["keyword"])

    def test_report_is_truncated_for_issue_body(self):
        state = self._state()
        for index in range(4000):
            state["search"][f"x{index}"] = {
                "app_id": "6785004775", "locale": "ja", "country": "jp",
                "keyword": f"kw{index}", "rank": 1, "top": None, "observed_at": "t",
            }
        report = gs.build_report(APPS, state, {"searches": 0, "tasks_total": 7}, now=NOW)
        self.assertLessEqual(len(report), gs.ISSUE_BODY_LIMIT)


class IssueTests(unittest.TestCase):
    def _opener(self, existing):
        calls = []

        def opener(request, timeout=None):
            calls.append((request.get_method(), request.full_url, request.data))
            if request.get_method() == "GET":
                return _Response(json.dumps(existing).encode())
            return _Response(json.dumps({"number": 42}).encode())

        return opener, calls

    def test_existing_issue_is_updated_in_place(self):
        opener, calls = self._opener([{"number": 9, "title": gs.ISSUE_TITLE}])
        self.assertEqual(9, gs.publish_issue("body", "t", opener=opener))
        self.assertEqual("PATCH", calls[-1][0])
        self.assertTrue(calls[-1][1].endswith("/issues/9"))

    def test_missing_issue_is_created_with_label(self):
        opener, calls = self._opener([])
        self.assertEqual(42, gs.publish_issue("body", "t", opener=opener))
        self.assertEqual(["growth-scoreboard"], json.loads(calls[-1][2])["labels"])


class StateTests(unittest.TestCase):
    def test_state_round_trip_and_schema_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s" / "state.json"
            state = gs.empty_state()
            state["cursor"] = 7
            gs.save_state(path, state)
            self.assertEqual(7, gs.load_state(path)["cursor"])
            path.write_text(json.dumps({"schema_version": 99, "cursor": 3}))
            self.assertEqual(0, gs.load_state(path)["cursor"])


if __name__ == "__main__":
    unittest.main()
