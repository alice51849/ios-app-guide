#!/usr/bin/env python3
"""Tests for threads_series.py (Threads evening slot: BM-11 / BM-17 / BM-22)."""
import copy
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_links as DL  # noqa: E402
import threads_series as T  # noqa: E402
import threads_cap  # noqa: E402


def setUpModule():
    # threads_cap.py reads the account's 24-hour post count right before each top-level Threads post. These tests
    # are about other things, so the account has room here; test_threads_cap.py covers the cap itself. Entered
    # directly rather than with start(), so a test's mock.patch.stopall cannot undo it for the tests after it.
    room = mock.patch.object(threads_cap, "quota_usage", return_value=0)
    room.__enter__()
    unittest.addModuleCleanup(room.__exit__, None, None, None)


WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"
DAY = dt.date(2026, 10, 20)
MILD = {"台北": {"min": 22, "max": 27, "rain": 0.0}, "台中": {"min": 22, "max": 28, "rain": 0.0},
        "高雄": {"min": 24, "max": 29, "rain": 0.0}}
COLD = {"台北": {"min": 13, "max": 17, "rain": 4.2}, "台中": {"min": 15, "max": 20, "rain": 0.0},
        "高雄": {"min": 19, "max": 24, "rain": 1.5}}


def live_event(data, day=DAY):
    data = copy.deepcopy(data)
    un = data["series"]["usagenow_policy"]
    un["status"] = "live"
    un["events"] = [{"date": day.isoformat(), "headline": "the weekly limit now resets on Mondays",
                     "impact_1": "plan long Claude Code runs early in the week",
                     "impact_2": "the 5-hour session limit is unchanged",
                     "source_name": "Anthropic Help Center", "source_date": "2026-10-20",
                     "source_url": "https://support.anthropic.com/"}]
    return data


class DataTest(unittest.TestCase):
    def test_data_file_is_valid(self):
        self.assertEqual([], T.validate())

    def test_series_use_the_checklist_ct_codes(self):
        s = T.load()["series"]
        self.assertEqual(s["usagenow_policy"]["ct"], "bm_usagenow_us_x")
        self.assertEqual(s["mochi_checklist"]["ct"], "bm_mochi_us_th")
        self.assertEqual(s["lumiweather_tomorrow"]["ct"], "bm_lumiweather_tw_th")

    def test_account_cap_is_three(self):
        self.assertEqual(3, T.load()["daily_cap"])


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.data = T.load()
        # The live conversion queue (threads-evening-queue.json) has dated posts; the
        # series rules are tested without it (EveningQueueTest covers the queue).
        self._queue_path = T.EVENING_QUEUE
        T.EVENING_QUEUE = Path("/nonexistent/threads-evening-queue.json")

    def tearDown(self):
        T.EVENING_QUEUE = self._queue_path

    def test_held_usagenow_never_posts(self):
        data = live_event(self.data)
        data["series"]["usagenow_policy"]["status"] = "held"
        chosen = T.plan(DAY, data, MILD)
        self.assertNotEqual("BM-11", chosen and chosen["series"])

    def test_live_usagenow_event_takes_the_slot(self):
        chosen = T.plan(DAY, live_event(self.data), COLD)
        self.assertEqual("BM-11", chosen["series"])
        self.assertLessEqual(len(chosen["text"]), T.MAX_POST_CHARS)
        self.assertNotIn("http", chosen["text"])
        self.assertEqual("bm_usagenow_us_x", chosen["ct"])  # the series label stays on the plan / post log
        # ...but the post goes out on Threads, so its link carries the Threads campaign
        self.assertIn("ct=" + DL.app_campaign("threads", chosen["app_id"]) + "&", __import__("threads_post").queued_links(chosen))

    def test_queued_posts_send_the_threads_campaign_whatever_their_label(self):
        tp = __import__("threads_post")
        for ct in ("bm_mochi_us_th", "bm_usagenow_us_x", "aim990_zhHant_1", "un_tw_threads_4", "", None):
            self.assertEqual("threads", tp.queued_campaign({"ct": ct}))
        self.assertIn("ct=" + DL.app_campaign("threads", "6784974530") + "&", tp.queued_links({"app_id": "6784974530", "ct": "aim990_zhHant_1"}))

    def test_overlong_event_is_skipped(self):
        data = live_event(self.data)
        data["series"]["usagenow_policy"]["events"][0]["headline"] = "x" * 200
        self.assertNotEqual("BM-11", T.plan(DAY, data, MILD)["series"])

    def test_usagenow_clip_keeps_its_slot(self):
        self.assertIsNone(T.plan(DAY, self.data, COLD, clip="claudeusagemini/en"))
        self.assertIsNotNone(T.plan(DAY, self.data, COLD, clip="maskmyfile/cs"))

    def test_weather_on_cold_or_rainy_days(self):
        for day in (DAY, DAY + dt.timedelta(days=1)):
            chosen = T.plan(day, self.data, COLD)
            self.assertEqual("BM-22", chosen["series"])
            self.assertIn("台北 13–17°C", chosen["text"])
            self.assertIn("台北、高雄明天可能下雨", chosen["text"])
            self.assertIn("偏冷", chosen["text"])

    def test_mild_days_alternate_weather_and_mochi(self):
        picks = {T.plan(DAY + dt.timedelta(days=i), self.data, MILD)["series"] for i in range(2)}
        self.assertEqual({"BM-17", "BM-22"}, picks)

    def test_no_forecast_falls_back_to_mochi(self):
        for i in range(4):
            self.assertEqual("BM-17", T.plan(DAY + dt.timedelta(days=i), self.data, None)["series"])

    def test_mochi_days_cycle_through_every_list(self):
        lists = self.data["series"]["mochi_checklist"]["lists"]
        mochi_days = [DAY + dt.timedelta(days=i) for i in range(4 * len(lists))
                      if T.plan(DAY + dt.timedelta(days=i), self.data, MILD)["series"] == "BM-17"]
        titles = {T.compose_mochi(self.data["series"]["mochi_checklist"], d).split("\n")[0] for d in mochi_days}
        self.assertEqual(len(lists), len(titles))

    def test_mochi_post_matches_the_free_tier(self):
        text = T.plan(DAY, self.data, None)["text"]
        self.assertIn("#MochiChecklist", text)
        self.assertEqual(4, text.count("○ "))
        self.assertIn("2 lists, up to 4 tasks each", text)

    def test_nothing_live_falls_back_to_clip(self):
        data = copy.deepcopy(self.data)
        for s in data["series"].values():
            s["status"] = "held"
        self.assertIsNone(T.plan(DAY, data, COLD))


QUEUED = {"date": DAY.isoformat(), "app": "cyca", "app_id": "6782251621", "ct": "bm_cyca_us_th",
          "locale": "en-US", "task": "cyca-conv-1", "source": "conv_us_1",
          "text": "Irregular cycle, PCOS or trying to conceive: Cyca keeps the log on your phone. Link in the reply."}


class EveningQueueTest(unittest.TestCase):
    """Dated conversion posts (growth/threads-evening-queue.json) for audiences awake at 13:00 UTC."""

    def setUp(self):
        self.data = T.load()

    def test_queued_post_takes_the_slot_on_its_date(self):
        chosen = T.plan(DAY, self.data, MILD, queue=[QUEUED])
        self.assertEqual("CONV", chosen["series"])
        self.assertEqual("bm_cyca_us_th", chosen["ct"])  # the series label stays on the plan / post log
        self.assertIn("ct=" + DL.app_campaign("threads", chosen["app_id"]) + "&", __import__("threads_post").queued_links(chosen))
        self.assertNotIn("http", chosen["text"])

    def test_other_days_keep_the_rotation(self):
        chosen = T.plan(DAY + dt.timedelta(days=1), self.data, MILD, queue=[QUEUED])
        self.assertIn(chosen["series"], ("BM-17", "BM-22"))

    def test_usagenow_event_and_weather_alert_still_win(self):
        self.assertEqual("BM-11", T.plan(DAY, live_event(self.data), MILD, queue=[QUEUED])["series"])
        self.assertEqual("BM-22", T.plan(DAY, self.data, COLD, queue=[QUEUED])["series"])
        self.assertIsNone(T.plan(DAY, self.data, MILD, clip="claudeusagemini/en", queue=[QUEUED]))

    def test_bad_entries_are_reported_and_never_posted(self):
        bad = [dict(QUEUED, ct="un_tw_threads_1"), dict(QUEUED, text="x" * 501),
               dict(QUEUED, text="see https://example.com"), dict(QUEUED, text="the best tracker"),
               {k: v for k, v in QUEUED.items() if k != "locale"}]
        for entry in bad:
            self.assertTrue(T.evening_queue_problems([entry]), entry)
            self.assertNotEqual("CONV", (T.plan(DAY, self.data, MILD, queue=[entry]) or {}).get("series"), entry)
        self.assertTrue(T.evening_queue_problems([QUEUED, dict(QUEUED, app="mochi")]))  # one date, two posts
        self.assertEqual([], T.evening_queue_problems([QUEUED]))

    def test_live_queue_file_is_valid_and_one_post_per_date(self):
        queue = T.load_evening_queue()
        self.assertEqual([], T.evening_queue_problems(queue))
        self.assertEqual(len(queue), len({p["date"] for p in queue}))
        for p in queue:
            self.assertTrue(p["ct"].startswith("bm_") and p["ct"].endswith("_th"), p["ct"])
            self.assertLessEqual(len(p["text"]), 480, p["date"])

    def test_missing_queue_file_is_empty(self):
        self.assertEqual([], T.load_evening_queue(Path("/nonexistent/queue.json")))


class ForecastTest(unittest.TestCase):
    def forecast(self, day):
        steps = []
        start = dt.datetime.combine(day, dt.time(), T.TW).astimezone(dt.timezone.utc)
        for h in range(30):
            t = start + dt.timedelta(hours=h)
            steps.append({"time": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "data": {
                "instant": {"details": {"air_temperature": 15 + (h % 24) / 2}},
                "next_1_hours": {"details": {"precipitation_amount": 0.1}}}})
        return {"properties": {"timeseries": steps}}

    def test_summarize_uses_the_taiwan_day(self):
        s = T.summarize(self.forecast(DAY), DAY)
        self.assertEqual({"min": 15, "max": 26, "rain": 2.4}, s)

    def test_failed_city_means_no_weather(self):
        def boom(lat, lon):
            raise OSError("down")
        self.assertIsNone(T.tomorrow_weather(T.load()["series"]["lumiweather_tomorrow"], DAY, fetch=boom))

    def test_tomorrow_weather_for_every_city(self):
        target = DAY + dt.timedelta(days=1)
        w = T.tomorrow_weather(T.load()["series"]["lumiweather_tomorrow"], DAY, fetch=lambda la, lo: self.forecast(target))
        self.assertEqual(["台北", "台中", "高雄"], list(w))


class CapTest(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 20, 13, 1, tzinfo=dt.timezone.utc)  # Taiwan 21:01

    def opener(self, stamps):
        def fake(url, timeout=30):
            self.url = url
            return io.BytesIO(json.dumps({"data": [{"id": str(i), "timestamp": s} for i, s in enumerate(stamps)]}).encode())
        return fake

    def test_counts_posts_since_taiwan_midnight(self):
        stamps = ["2026-10-20T01:41:00+0000", "2026-10-20T03:02:00+0000", "2026-10-19T15:59:00+0000"]
        self.assertEqual(2, T.posts_today("tok", self.NOW, self.opener(stamps)))
        self.assertIn("since=1792425600", self.url)
        self.assertTrue(T.has_room("tok", 3, self.NOW, self.opener(stamps)))

    def test_full_account_holds(self):
        stamps = ["2026-10-20T01:41:00+0000", "2026-10-20T03:02:00+0000", "2026-10-20T05:12:00+0000"]
        self.assertFalse(T.has_room("tok", 3, self.NOW, self.opener(stamps)))

    def test_unknown_count_holds(self):
        def boom(url, timeout=30):
            raise OSError("down")
        self.assertFalse(T.has_room("tok", 3, self.NOW, boom))

    def test_room_status_tells_full_from_unknown(self):
        def boom(url, timeout=30):
            raise OSError("down")
        two = ["2026-10-20T01:41:00+0000", "2026-10-20T03:02:00+0000"]
        three = two + ["2026-10-20T05:12:00+0000"]
        self.assertEqual("room", T.room_status("tok", 3, self.NOW, self.opener(two)))
        self.assertEqual("full", T.room_status("tok", 3, self.NOW, self.opener(three)))
        self.assertEqual("unknown", T.room_status("tok", 3, self.NOW, boom))

    def test_room_command_exit_codes(self):
        from unittest import mock
        with mock.patch.dict("os.environ", {"THREADS_TOKEN": "tok"}):
            for status, code in (("room", 0), ("full", 1), ("unknown", 2)):
                with mock.patch.object(T, "room_status", return_value=status):
                    self.assertEqual(code, T.main(["room"]))
        with mock.patch.dict("os.environ", {"THREADS_TOKEN": ""}):
            self.assertEqual(2, T.main(["room"]))


class EveningLinkReplyTest(unittest.TestCase):
    """Owner rule 2026-10-17: the evening post gets its app's direct download link in the first reply
    (App Store, plus Google Play for an Android app). The reply is checked before anything is posted,
    retried when it fails, and a final failure ends the step red - the post is never re-posted for it."""

    MOCHI, IOS_ONLY = "6785004775", "1000000001"  # Android-live / iOS-only App Store ids

    def setUp(self):
        import threads_post
        self.tp = threads_post
        handle, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(handle)
        self.addCleanup(os.unlink, self.log_path)
        for patcher in (mock.patch.dict(os.environ, {"LINK_GUARD_LOG": self.log_path, "THREADS_TOKEN": "tok",
                                                     "THREADS_USER_ID": "uid"}),
                        mock.patch("sys.stderr", new_callable=io.StringIO)):
            patcher.start()
            self.addCleanup(patcher.stop)
        out = mock.patch("sys.stdout", new_callable=io.StringIO)
        self.out = out.start()
        self.addCleanup(out.stop)

    def post(self, app, text="Pain line without any URL."):
        return {"series": "CONV", "app": "x", "app_id": app, "ct": "bm_x_us_th", "locale": "en", "text": text,
                "image_url": None}

    def evening(self, chosen, publish, find=None):
        with (
            mock.patch.object(T, "has_room", return_value=True),
            mock.patch.object(T, "plan", return_value=chosen),
            mock.patch.object(T, "planned_clip", return_value=None),
            mock.patch.object(T.urllib.request, "urlopen", side_effect=OSError("offline")),
            mock.patch.object(self.tp, "find_own_post", return_value=find),
            mock.patch.object(self.tp, "find_own_link_reply", return_value=None),   # the look worked: no reply yet
            mock.patch.object(self.tp, "publish_post", side_effect=publish) as posted,
            mock.patch("time.sleep") as slept,
        ):
            return T.main(["evening", "--date", "2026-10-20", "--offline"]), posted, slept

    def refusals(self):
        with open(self.log_path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_the_reply_carries_the_app_store_link_and_play_for_an_android_app(self):
        rc, posted, _ = self.evening(self.post(self.MOCHI), ["m1", "r1"])
        self.assertEqual(0, rc)
        main_call, reply_call = posted.call_args_list
        self.assertNotIn("http", main_call.args[2])
        self.assertEqual("m1", reply_call.kwargs["reply_to"])
        self.assertIn("apps.apple.com/app/id" + self.MOCHI, reply_call.args[2])
        self.assertIn("ct=threads&", reply_call.args[2])
        self.assertIn("play.google.com/store/apps/details?id=", reply_call.args[2])
        self.assertIn("fallback=none", self.out.getvalue())
        rc, posted, _ = self.evening(self.post(self.IOS_ONLY), ["m2", "r2"])
        self.assertEqual(0, rc)
        self.assertNotIn("play.google.com", posted.call_args_list[1].args[2])
        self.assertEqual([], self.refusals())

    def test_a_failed_reply_is_retried_and_the_run_goes_through(self):
        rc, posted, slept = self.evening(self.post(self.MOCHI), ["m1", self.tp.RequestError("down"), "r1"])
        self.assertEqual(0, rc)
        self.assertEqual(3, posted.call_count)
        self.assertEqual([mock.call(15)], slept.call_args_list)
        self.assertEqual([], self.refusals())

    def test_a_reply_that_never_posts_ends_red_and_does_not_repost_the_main_post(self):
        failures = [self.tp.RequestError("down")] * self.tp.LINK_REPLY_TRIES
        rc, posted, _ = self.evening(self.post(self.MOCHI), ["m1", *failures])
        self.assertEqual(1, rc)
        self.assertEqual(1, sum(1 for c in posted.call_args_list if "reply_to" not in c.kwargs))
        self.assertIn("::error::", self.out.getvalue())
        self.assertIn("fallback=none", self.out.getvalue())  # no hook clip on top of a slot that is taken
        self.assertEqual(1, len(self.refusals()))

    def test_nothing_is_posted_when_the_apps_link_cannot_be_built(self):
        for bad in ("abc", "", None):
            with self.subTest(app_id=bad):
                rc, posted, _ = self.evening(self.post(bad), ["m1", "r1"])
                self.assertEqual(1, rc)
                posted.assert_not_called()
                self.assertIn("::error::", self.out.getvalue())

    def test_a_rerun_of_a_red_slot_adds_the_reply_under_the_post_that_is_up(self):
        rc, posted, _ = self.evening(self.post(self.MOCHI), ["r1"], find="m-existing")
        self.assertEqual(0, rc)
        posted.assert_called_once()
        self.assertEqual("m-existing", posted.call_args.kwargs["reply_to"])

    def test_every_series_and_queued_post_has_a_checked_link_reply(self):
        data = T.load()
        posts = [{"app_id": s["app_id"], "ct": s["ct"], "app": s["app"]} for s in data["series"].values()]
        posts += [T.queue_post(p) for p in T.load_evening_queue(T.EVENING_QUEUE)]
        self.assertGreater(len(posts), len(data["series"]))
        for post in posts:
            with self.subTest(app=post["app"], ct=post["ct"]):
                store, play = self.tp.queued_link_urls(post)
                self.assertEqual([], DL.threads_reply_problems(self.tp.queued_links(post), store, play))


class WorkflowTest(unittest.TestCase):
    def test_threads_post_has_three_slots(self):
        text = (WORKFLOWS / "threads-post.yml").read_text(encoding="utf-8")
        crons = [line.split('"')[1] for line in text.splitlines() if line.strip().startswith("- cron:")]
        self.assertEqual(["40 1 * * *", "0 3 * * *", "0 13 * * *"], crons)
        self.assertIn("--slots 1,3,13", text)
        self.assertIn("threads_series.py evening", text)
        self.assertIn("steps.series.outputs.fallback == 'clip'", text)

    def test_threads_post_slot_comes_from_the_schedule_and_dispatch_can_fill_it(self):
        text = (WORKFLOWS / "threads-post.yml").read_text(encoding="utf-8")
        gate = text.split("- name: Prevent duplicate UTC slot", 1)[1].split("- name:", 1)[0]
        self.assertIn("SLOT_SCHEDULE: ${{ github.event.schedule }}", gate)
        self.assertIn('--schedule "$SLOT_SCHEDULE"', gate)
        self.assertIn('--slot-hour "$SLOT_HOUR"', gate)
        self.assertIn("inputs.mode == 'post'", text)
        self.assertIn("format('Threads posts · cron {0}', github.event.schedule)", text)
        # No post step keys off the run's actual start time any more.
        steps = text.split("jobs:", 1)[1]
        self.assertNotIn("github.event.schedule ==", steps)

    def test_every_threads_post_step_waits_for_the_account_cap(self):
        text = (WORKFLOWS / "threads-post.yml").read_text(encoding="utf-8")
        post = text.split("\n  post:", 1)[1]
        steps = post.split("      - name: ")[1:]
        posting = [s for s in steps if "THREADS_USER_ID" in s]
        self.assertEqual(5, len(posting))  # picture, Mochi trial (01:40 / 21:00), hook clip, series, slot-15 clip
        for step in posting:
            self.assertIn("steps.room.outputs.ok == 'true'", step)
        self.assertIn("threads_series.py room", post)

    def test_clip_backup_never_refills_the_evening_threads_slot_after_taiwan_midnight(self):
        text = (WORKFLOWS / "clip-backup.yml").read_text(encoding="utf-8")
        threads = text.split("- name: Threads", 1)[1].split("- name:", 1)[0]
        # clip-backup never posts to Threads itself: threads_backfill.py only
        # dispatches threads-post.yml (slot gate + daily cap) for today's
        # Taiwan slots, so the 17:47 backup finds nothing to fill.
        self.assertIn("threads_backfill.py", threads)
        self.assertNotIn("clip_posts.py threads", threads)
        self.assertNotIn("THREADS_TOKEN", threads)
        import threads_backfill
        import datetime as _dt
        late = _dt.datetime(2026, 10, 15, 17, 47, tzinfo=_dt.timezone.utc)
        self.assertEqual([], threads_backfill.missing_slots([], late))


if __name__ == "__main__":
    unittest.main()
