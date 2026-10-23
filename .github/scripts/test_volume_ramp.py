#!/usr/bin/env python3
"""Tests for volume_ramp.py (no network)."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import volume_ramp as R  # noqa: E402


def ramp(**channels):
    base = {"schema": R.SCHEMA, "stage_days": 3, "hold_days": 7, "channels": {}}
    for name, cfg in channels.items():
        base["channels"][name] = dict({"start": "2026-10-17", "ceiling": None, "ceiling_until": None, "events": []}, **cfg)
    return base


IG = {"stages": [2, 3, 4, 5, 6], "slots": [1, 15, 12, 22, 9, 18]}


class StageTest(unittest.TestCase):
    def test_climbs_one_stage_every_stage_days_and_stays_at_the_top(self):
        r = ramp(instagram=IG)
        days = [dt.date(2026, 10, 16) + dt.timedelta(days=i) for i in range(16)]
        got = [R.allowance(r, "instagram", d) for d in days]
        self.assertEqual(got, [2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6])
        self.assertEqual(R.slots(r, "instagram", dt.date(2026, 10, 20)), [1, 12, 15])
        self.assertEqual(R.slots(r, "instagram", dt.date(2026, 10, 29)), [1, 9, 12, 15, 18, 22])
        self.assertIsNone(R.allowance(r, "bluesky", days[0]))  # not ramped: old pacing
        self.assertIsNone(R.slots({}, "instagram", days[0]))

    def test_throttle_drops_one_stage_holds_then_climbs_again_from_the_ceiling(self):
        r = ramp(instagram=IG)
        day = dt.date(2026, 10, 26)  # stage 3 (5 a day)
        self.assertEqual(R.stage(r, "instagram", day), 3)
        event = R.throttle(r, "instagram", "HTTP 429: too many requests", day=day, path=None,
                           now=dt.datetime(2026, 10, 26, 12, tzinfo=dt.timezone.utc))
        self.assertEqual((event["from_per_day"], event["to_per_day"], event["hold_until"]), (5, 4, "2026-11-02"))
        self.assertEqual(R.allowance(r, "instagram", day), 4)
        self.assertEqual(R.allowance(r, "instagram", dt.date(2026, 11, 2)), 4)   # held
        self.assertEqual(R.allowance(r, "instagram", dt.date(2026, 11, 3)), 5)   # climbs again, one stage
        self.assertEqual(R.allowance(r, "instagram", dt.date(2026, 11, 5)), 5)
        self.assertEqual(R.allowance(r, "instagram", dt.date(2026, 11, 6)), 6)
        self.assertEqual(r["channels"]["instagram"]["events"][-1]["reason"], "HTTP 429: too many requests")
        again = R.throttle(r, "instagram", "spam", day=dt.date(2026, 10, 28), path=None)
        self.assertEqual(again["to_per_day"], 3)  # a second hit during the hold goes one lower
        self.assertEqual(R.allowance(r, "instagram", dt.date(2026, 10, 28)), 3)

    def test_throttle_at_the_bottom_stays_at_the_bottom(self):
        r = ramp(telegram={"stages": [2, 4, 6], "slots": [1, 15, 12, 22, 9, 18]})
        event = R.throttle(r, "telegram", "flood", day=dt.date(2026, 10, 17), path=None)
        self.assertEqual((event["from_per_day"], event["to_per_day"]), (2, 2))
        self.assertIsNone(R.throttle(r, "bluesky", "x", path=None))

    def test_file_round_trip_and_foreign_schema_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ramp.json"
            R.save(ramp(instagram=IG), path)
            r = R.load(path)
            R.throttle(r, "instagram", "blocked", day=dt.date(2026, 10, 20), path=path)
            self.assertEqual(R.load(path)["channels"]["instagram"]["ceiling"], 0)
            path.write_text(json.dumps({"schema": "other"}))
            self.assertEqual(R.load(path), {})
            self.assertEqual(R.load(Path(tmp) / "missing.json"), {})

    def test_committed_ramp_keeps_threads_at_the_owner_cap_and_names_known_slots(self):
        r = R.load()
        self.assertEqual(r["schema"], R.SCHEMA)
        self.assertEqual(r["channels"]["threads"]["stages"], [2])
        self.assertEqual(r["channels"]["threads"]["slots"], [1, 15])
        for name, cfg in r["channels"].items():
            self.assertEqual(cfg["stages"], sorted(cfg["stages"]), name)  # a ramp only climbs
            self.assertGreaterEqual(len(cfg["slots"]), max(cfg["stages"]), name)
            self.assertEqual(len(set(cfg["slots"])), len(cfg["slots"]), name)
        self.assertLessEqual(max(r["channels"]["instagram"]["stages"]) + max(r["channels"]["instagram_feed"]["stages"]) + 2, 10)


class MergeTest(unittest.TestCase):
    def test_a_saved_throttle_survives_the_rebase_merge(self):
        current = ramp(instagram=IG)
        saved = ramp(instagram=IG)
        R.throttle(saved, "instagram", "HTTP 429", day=dt.date(2026, 10, 26), path=None)
        merged = R.merge(json.loads(json.dumps(saved)), json.loads(json.dumps(current)))
        self.assertEqual(merged["channels"]["instagram"]["ceiling"], 2)
        self.assertEqual(len(merged["channels"]["instagram"]["events"]), 1)
        merged = R.merge(json.loads(json.dumps(saved)), merged)  # again: no duplicate event, same ceiling
        self.assertEqual(len(merged["channels"]["instagram"]["events"]), 1)
        lower = ramp(instagram=dict(IG, ceiling=0, ceiling_until="2026-11-30"))
        self.assertEqual(R.merge(saved, lower)["channels"]["instagram"]["ceiling"], 0)  # the lower ceiling wins
        self.assertEqual(R.merge({}, current), current)


class PostedTest(unittest.TestCase):
    def test_room_counts_only_todays_clips_of_the_channel(self):
        posts = [{"channel": "instagram", "clip": "a/en", "posted_at": "2026-10-20T01:21:00Z"},
                 {"channel": "instagram", "clip": "utility/word-x", "posted_at": "2026-10-20T05:11:00Z"},
                 {"channel": "instagram", "clip": "b/en", "posted_at": "2026-10-19T15:21:00Z"},
                 {"channel": "telegram", "clip": "c/en", "posted_at": "2026-10-20T01:01:00Z"},
                 {"channel": "instagram_feed", "clip": "feed/mochi/zh-Hant", "posted_at": "2026-10-20T07:21:00Z"}]
        r = ramp(instagram=IG, instagram_feed={"stages": [1, 1, 2], "slots": [7, 19]})
        day = dt.date(2026, 10, 20)
        self.assertEqual(R.room(r, "instagram", day, posts), (3, 1, 2))
        self.assertEqual(R.room(r, "instagram_feed", day, posts), (1, 1, 0))
        self.assertEqual(R.room(r, "telegram", day, posts), (None, 1, None))

    def test_a_priority_extra_listing_posts_on_top_of_the_stage_and_never_takes_another_apps_place(self):
        r = ramp(instagram={"stages": [1], "slots": [1, 18]}, telegram={"stages": [1], "slots": [1, 22]})
        r["priority_extra"] = {"apps": ["mochi"], "channels": ["instagram"], "per_day": 1}
        day = dt.date(2026, 10, 21)
        posts = [{"channel": "instagram", "clip": "zipbox/zh-Hant", "posted_at": "2026-10-21T01:35:00Z"},
                 {"channel": "telegram", "clip": "lumiweather/zh-Hant", "posted_at": "2026-10-21T04:00:00Z"}]
        self.assertEqual(R.room(r, "instagram", day, posts), (1, 1, 0))                      # stage used up
        self.assertEqual(R.room(r, "instagram", day, posts, clip="mochi_b/en"), (1, 1, 1))   # the extra Mochi post
        self.assertEqual(R.room(r, "instagram", day, posts, clip="mochidonestamp/en")[2], 0)  # another listing
        self.assertEqual(R.room(r, "telegram", day, posts, clip="mochi/en")[2], 0)           # channel not listed
        posts.append({"channel": "instagram", "clip": "mochi_b/en", "posted_at": "2026-10-21T18:21:00Z"})
        self.assertEqual(R.room(r, "instagram", day, posts, clip="mochi/de")[2], 0)          # one extra a day
        # Mochi first: its post does not use the stage, so the other app still gets its slot.
        early = [{"channel": "instagram", "clip": "mochi/en", "posted_at": "2026-10-21T01:21:00Z"}]
        self.assertEqual(R.room(r, "instagram", day, early, clip="zipbox/en")[2], 1)
        held = json.loads(json.dumps(r))
        held["channels"]["instagram"].update(ceiling=0, ceiling_until="2026-10-25")
        self.assertEqual(R.room(held, "instagram", day, posts[:1], clip="mochi_b/en")[2], 0)  # throttled: no extra
        r["priority_extra"]["per_day"] = "x"
        self.assertEqual(R.priority_extra(r, "instagram"), ((), 0))

    def test_the_account_cap_counts_every_kind_of_post_and_a_throttle_slows_every_channel_on_it(self):
        day = dt.date(2026, 10, 29)
        posts = [{"channel": "instagram", "clip": f"c{i}/en", "posted_at": "2026-10-29T01:21:00Z"} for i in range(5)]
        posts += [{"channel": "instagram", "clip": "utility/x", "posted_at": "2026-10-29T05:11:00Z"},
                  {"channel": "instagram", "clip": "countdown/x", "posted_at": "2026-10-29T03:11:00Z"},
                  {"channel": "instagram_feed", "clip": "feed/a/en", "posted_at": "2026-10-29T07:21:00Z"},
                  {"channel": "instagram_feed", "clip": "feed/b/en", "posted_at": "2026-10-29T19:21:00Z"}]
        r = ramp(instagram=IG, instagram_feed={"stages": [1, 1, 2, 2, 2], "slots": [7, 19]})
        self.assertEqual(R.room(r, "instagram", day, posts), (6, 5, 1))  # 9 of 10 on the account: one left
        posts.append({"channel": "instagram", "clip": "c9/en", "posted_at": "2026-10-29T12:21:00Z"})
        self.assertEqual(R.room(r, "instagram", day, posts)[2], 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ramp.json"
            R.save(r, path)
            with mock.patch.object(R, "notify", return_value=None):
                ev = R.handle_error("instagram_feed", "HTTP 429", path=path, day=day)
            saved = R.load(path)
        self.assertEqual(ev["channel"], "instagram")
        self.assertEqual(saved["channels"]["instagram"]["ceiling"], 3)
        self.assertEqual(saved["channels"]["instagram_feed"]["ceiling"], 3)


class ErrorTest(unittest.TestCase):
    def test_platform_slow_down_answers_are_recognised(self):
        yes = ["HTTP 429: Too Many Requests",
               'HTTP 400: {"error":{"message":"(#4) Application request limit reached","code":4}}',
               'HTTP 400: {"error":{"message":"x","code":100,"error_subcode":2207051}}',
               'HTTP 403: {"error":{"message":"Your account has been temporarily blocked for policies violations","code":368}}',
               '{"ok":false,"error_code":429,"description":"Too Many Requests: retry after 5"}',
               'HTTP 400: {"error":"RateLimitExceeded","message":"Rate Limit Exceeded"}',
               "<HttpError 403 ... quotaExceeded>", "uploadLimitExceeded: The user has exceeded the number of videos they may upload"]
        for text in yes:
            self.assertTrue(R.is_throttle_error(text), text)
        no = ["HTTP 400: {\"error\":{\"message\":\"Invalid parameter\",\"code\":100}}", "Instagram processing timed out",
              "HTTP 401 unconfirmed_email", "", None, "Telegram sendVideo failed: {'ok': False, 'description': 'Bad Request: wrong file'}"]
        for text in no:
            self.assertFalse(R.is_throttle_error(text), text)

    def test_handle_error_throttles_and_notifies_only_on_slow_down_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ramp.json"
            R.save(ramp(instagram=IG), path)
            with mock.patch.object(R, "notify", return_value="https://github.com/x/y/issues/1") as n:
                self.assertIsNone(R.handle_error("instagram", "Invalid parameter", path=path, day=dt.date(2026, 10, 20)))
                n.assert_not_called()
                ev = R.handle_error("instagram", "HTTP 429", path=path, day=dt.date(2026, 10, 20))
            self.assertEqual(ev["to_per_day"], 2)
            n.assert_called_once()
            self.assertEqual(R.load(path)["channels"]["instagram"]["ceiling"], 0)

    def test_notify_opens_an_issue_once_then_comments(self):
        calls = []

        def gh(method, path, token, body=None):
            calls.append((method, path, body))
            if path.startswith("/search/issues"):
                return {"items": [] if len(calls) == 1 else [{"number": 7, "title": R.ISSUE_TITLE.format(channel="instagram"), "html_url": "u7"}]}
            if path == "/repos/o/r/issues":
                return {"html_url": "u1"}
            return {}

        event = {"at": "2026-10-20T01:21:00Z", "channel": "instagram", "from_stage": 2, "to_stage": 1, "from_per_day": 4,
                 "to_per_day": 3, "hold_until": "2026-10-27", "reason": "HTTP 429"}
        self.assertEqual(R.notify(event, "o/r", "t", run_url="run", gh=gh), "u1")
        self.assertEqual(calls[1][0:2], ("POST", "/repos/o/r/issues"))
        self.assertEqual(calls[1][2]["labels"], [R.LABEL])
        self.assertIn("run", calls[1][2]["body"])
        self.assertEqual(R.notify(event, "o/r", "t", gh=gh), "u7")
        self.assertEqual(calls[-1][1], "/repos/o/r/issues/7/comments")
        # local run: nothing to notify. CI 的 GITHUB_TOKEN／GITHUB_REPOSITORY 會被 notify 當後備讀到，這裡清掉才是真的「本機」。
        with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""}):
            self.assertIsNone(R.notify(event, "", "", gh=gh))


if __name__ == "__main__":
    unittest.main()
