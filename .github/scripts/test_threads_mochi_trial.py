#!/usr/bin/env python3
"""The Threads Mochi top-10 trial (threads_post.py TRIAL_PATH): each listed date (2026-10-20 .. 2026-11-02) owes its
entry, posted in the day's first slot with room; after the last date, each day owes the next entry of the file's
daily_after_end list (without that list, the usual logic runs again); the entry's link reply carries the App Store
link with its own ct; the account cap and the link checks still hold it."""
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("POST_QA_OFFLINE", "1")  # the pre-post QA gate makes no network calls in tests

import channel_rotation as CR  # noqa: E402
import download_links as DL  # noqa: E402
import social_post_common as common  # noqa: E402
import threads_cap  # noqa: E402
import threads_post  # noqa: E402

MOCHI = "6785004775"  # the cute to-do list (apps.json "Mochi"), on Google Play too
TRIAL = threads_post.load_trial()
POSTS = TRIAL.get("posts") or []
# The file as it stood before 2026-10-21 (10-21 empty as the 10-20 entry's make-up day, no daily cycle after the
# last date): the make-up and end-of-trial rules are still tested on it.
LEGACY = {k: v for k, v in TRIAL.items() if k != "daily_after_end"}
LEGACY["posts"] = [p for p in POSTS if p.get("date") != "2026-10-21"]
CYCLE = (TRIAL.get("daily_after_end") or {}).get("cts") or []
START, END = dt.date(2026, 10, 19), dt.date(2026, 11, 2)
# Words that name a price or a paid tier the trial copy must not carry (owner's video rule (b), same for text).
PRICE_WORDS = re.compile(r"[$€£¥￥₩]|\d+\s?(?:元|円|원|usd|dollars?)|\bfree\b|\bpro\b|\bpremium\b|免費|免费|進階|付費|"
                         r"無料|有料|プロ|무료|유료|프로|프리미엄", re.I)


class TrialFileTests(unittest.TestCase):
    def test_an_entry_every_day_from_10_20_inside_the_trial(self):
        # 2026-10-20 (GE ops/company/mochi_no1_strategy.md C.1): one of the 3 Threads posts a day goes to Mochi.
        # 2026-10-21: 10-21 filled too (the 10-20 entry went out on its day), so every day from 10-20 to 11-02.
        self.assertEqual("mochi", TRIAL.get("app_key"))
        self.assertEqual(MOCHI, DL.app_store_id(TRIAL.get("app_store")))
        days = sorted(dt.date.fromisoformat(p["date"]) for p in POSTS)
        self.assertEqual(14, len(days))
        self.assertEqual(sorted(set(days)), days)
        self.assertTrue(all(START <= d <= END for d in days), days)
        self.assertEqual(dt.date(2026, 10, 20), days[0])
        self.assertEqual(END, days[-1])
        self.assertTrue(all((b - a).days == 1 for a, b in zip(days, days[1:])), days)

    def test_the_daily_cycle_lists_only_evergreen_entries_of_the_file(self):
        # After 11-02 the trial goes on daily from this list: no season copy (Halloween, fall, year end).
        by_ct = {p["ct"]: p for p in POSTS}
        self.assertGreaterEqual(len(CYCLE), 7)
        self.assertEqual(len(set(CYCLE)), len(CYCLE))
        self.assertTrue(set(CYCLE) <= set(by_ct), set(CYCLE) - set(by_ct))
        seasonal = re.compile(r"halloween|fall|autumn|christmas|年底|萬聖|秋|聖誕|ハロウィン|핼러윈", re.I)
        for ct in CYCLE:
            with self.subTest(ct=ct):
                self.assertIsNone(seasonal.search(by_ct[ct]["text"]), ct)

    def test_each_entry_is_ready_to_post(self):
        seen = set()
        for p in POSTS:
            with self.subTest(ct=p["ct"]):
                self.assertIn(p["lang"], ("en-US", "ja", "ko", "zh-Hant"))
                self.assertRegex(p["ct"], r"^th_mochi_(en|ja|ko|zh)_\d{2}$")
                self.assertTrue(p["ct"].startswith(f"th_mochi_{p['lang'][:2]}_"))
                self.assertIsNotNone(common.APP_STORE_CAMPAIGN_RE.fullmatch(p["ct"]))
                self.assertNotIn(p["ct"], seen)
                seen.add(p["ct"])
                self.assertEqual(1, p["reply"].count("{link}"))
                self.assertNotRegex(p["text"], r"https?://|apps\.apple\.com|\{link\}")
                self.assertIsNone(PRICE_WORDS.search(p["text"] + "\n" + p["reply"]), p["ct"])
                self.assertLessEqual(len(p["text"]), threads_post.MAX_POST_CHARS)

    def test_every_entry_passes_the_pre_post_qa(self):
        for p in POSTS:
            with self.subTest(ct=p["ct"]):
                self.assertEqual([], threads_post.trial_problems(TRIAL, p))

    def test_the_qa_refuses_a_claim_the_store_page_does_not_make(self):
        bad = dict(POSTS[0], text="The best free checklist app, no ads at all.")
        self.assertTrue(threads_post.trial_problems(TRIAL, bad))
        linked = dict(POSTS[0], text="Cute list https://apps.apple.com/app/id" + MOCHI)
        self.assertTrue(threads_post.trial_problems(TRIAL, linked))


class TrialDayTests(unittest.TestCase):
    def test_only_the_listed_dates_are_trial_days(self):
        listed = {p["date"] for p in POSTS}
        day = dt.date(2026, 10, 1)
        while day <= dt.date(2026, 12, 31):
            entry = threads_post.trial_post(day, TRIAL)
            self.assertEqual(day.isoformat() in listed, entry is not None, day)
            if entry:
                self.assertEqual(day.isoformat(), entry["date"])
            day += dt.timedelta(days=1)
        self.assertIsNone(threads_post.trial_post(dt.date(2026, 11, 3), TRIAL))
        self.assertIsNone(threads_post.trial_post(None, TRIAL))

    def test_a_missing_or_broken_file_means_no_trial(self):
        self.assertEqual({}, threads_post.load_trial("/nonexistent/threads_mochi_trial.json"))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{not json")
        self.addCleanup(os.unlink, handle.name)
        self.assertEqual({}, threads_post.load_trial(handle.name))
        self.assertIsNone(threads_post.trial_post(dt.date(2026, 10, 20), {}))


class TrialLinkTests(unittest.TestCase):
    def test_the_reply_carries_the_entry_ct_on_both_stores(self):
        for p in POSTS:
            with self.subTest(ct=p["ct"]):
                reply = threads_post.trial_reply(TRIAL, p)
                self.assertNotIn("{link}", reply)
                self.assertIn(f"https://apps.apple.com/app/id{MOCHI}?pt=118326163&ct={p['ct']}&mt=8", reply)
                self.assertIn("play.google.com/store/apps/details?id=", reply)
                self.assertIn(f"utm_source%3D{p['ct']}", reply)
                self.assertEqual([], DL.threads_reply_problems(reply, *threads_post.trial_link_urls(TRIAL, p)))
                self.assertEqual([], DL.fine_campaigns(reply))   # the ct leaves as it is, never merged
                self.assertEqual(p["ct"], DL.coarse_campaign(p["ct"]))
                self.assertEqual(p["ct"], DL.app_campaign(p["ct"], MOCHI))

    def test_a_reply_template_without_one_link_slot_is_refused(self):
        for bad in ("Mochi", "Mochi {link} {link}"):
            with self.assertRaises(ValueError):
                threads_post.trial_reply(TRIAL, dict(POSTS[0], reply=bad))


class MainHarness(unittest.TestCase):
    """threads_post.main() on a slot (default: the picture slot, 03:00 UTC = 11:00 Taiwan, the same date)."""

    QUEUED = {"date": "", "app": "x", "app_id": MOCHI, "ct": "bm_mochi_us_th", "task": "t",
              "text": "Queued pain line, no URL."}

    def setUp(self):
        handle, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(handle)
        self.addCleanup(os.unlink, self.log_path)
        for patcher in (mock.patch.dict(os.environ, {"LINK_GUARD_LOG": self.log_path}),
                        mock.patch.object(CR, "paused_notice", return_value=False),
                        mock.patch.object(threads_post, "find_own_link_reply", return_value=None),
                        mock.patch.object(urllib.request, "urlopen", side_effect=OSError("offline")),
                        mock.patch("countdown_cards.due", return_value=False),
                        mock.patch("time.sleep"),
                        mock.patch("sys.stderr", new_callable=io.StringIO)):
            patcher.start()
            self.addCleanup(patcher.stop)
        out = mock.patch("sys.stdout", new_callable=io.StringIO)
        self.out = out.start()
        self.addCleanup(out.stop)

    def run_main(self, day, *, used=0, publish=("m1", "r1"), find=None, queued=True, up=None, hour="03:00",
                 argv=()):
        """`up`: what find_trial_post answers (None = the owed entry is not up; (id, UTC time) = it is up)."""
        env = {"THREADS_TOKEN": "tok", "THREADS_USER_ID": "uid", "THREADS_SLOT": f"{day}T{hour}:00+00:00"}
        quota = (mock.patch.object(threads_cap, "quota_usage", side_effect=used) if isinstance(used, Exception)
                 else mock.patch.object(threads_cap, "quota_usage", return_value=used))
        queued_post = dict(self.QUEUED, date=day) if queued else None
        with (
            mock.patch.dict(os.environ, env),
            quota,
            mock.patch.object(threads_post, "queued_today", return_value=queued_post) as queue,
            mock.patch.object(threads_post, "find_own_post", return_value=find),
            mock.patch.object(threads_post, "find_trial_post",
                              **({"side_effect": up} if isinstance(up, Exception) else {"return_value": up})),
            mock.patch.object(threads_post, "publish_post", side_effect=list(publish)) as posted,
        ):
            return threads_post.main(list(argv)), posted, queue



class TrialMainTests(MainHarness):
    def test_a_trial_day_posts_the_trial_entry_and_its_link_reply(self):
        for p in POSTS:
            with self.subTest(day=p["date"]):
                rc, posted, queue = self.run_main(p["date"])
                self.assertEqual(0, rc)
                queue.assert_not_called()   # the slot goes to the trial, the queue is not read
                main_call, reply_call = posted.call_args_list
                self.assertEqual(p["text"], main_call.args[2])
                self.assertNotIn("http", main_call.args[2])
                self.assertNotIn("reply_to", main_call.kwargs)
                self.assertIsNone(main_call.kwargs.get("image_url"))
                self.assertEqual("m1", reply_call.kwargs["reply_to"])
                self.assertIn(f"ct={p['ct']}&", reply_call.args[2])
                self.assertIn("play.google.com", reply_call.args[2])

    def test_a_day_off_the_trial_runs_the_usual_logic(self):
        earlier = ("m-old", dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc))  # the owed entry went out already
        for day in ("2026-10-19", "2026-10-21", "2026-10-31", "2026-11-02", "2026-11-03", "2026-11-04"):
            with self.subTest(day=day):
                rc, posted, queue = self.run_main(day, up=earlier)
                self.assertEqual(0, rc)
                queue.assert_called_once()
                self.assertEqual(self.QUEUED["text"], posted.call_args_list[0].args[2])
                self.assertIn("ct=threads&", posted.call_args_list[1].args[2])  # the queue line's channel ct
                self.assertNotIn("th_mochi_", posted.call_args_list[1].args[2])

    def test_the_trial_is_held_by_the_account_cap(self):
        rc, posted, queue = self.run_main("2026-10-20", used=threads_cap.ACCOUNT_DAILY_CAP)
        self.assertEqual(0, rc)          # full: a skip, green, nothing posted, nothing else posted instead
        posted.assert_not_called()
        queue.assert_not_called()
        self.assertIn("⏸", self.out.getvalue())
        rc, posted, _ = self.run_main("2026-10-20", used=threads_cap.QuotaUnknown("down"))
        self.assertEqual(1, rc)          # count unknown: nothing posted, red
        posted.assert_not_called()
        self.assertIn("::warning::", self.out.getvalue())

    def test_a_rerun_adds_only_the_missing_link_reply(self):
        this_slot = ("m-existing", dt.datetime(2026, 10, 22, 3, 5, tzinfo=dt.timezone.utc))
        rc, posted, _ = self.run_main("2026-10-22", publish=("r1",), find="m-existing", up=this_slot)
        self.assertEqual(0, rc)
        posted.assert_called_once()
        self.assertEqual("m-existing", posted.call_args.kwargs["reply_to"])
        self.assertIn("ct=th_mochi_ko_01&", posted.call_args.args[2])

    def test_an_entry_the_qa_refuses_posts_nothing_and_ends_red(self):
        bad = dict(TRIAL, posts=[dict(POSTS[0], text="The best free checklist app.")])
        with mock.patch.object(threads_post, "load_trial", return_value=bad):
            rc, posted, queue = self.run_main(POSTS[0]["date"])
        self.assertEqual(1, rc)
        posted.assert_not_called()
        queue.assert_not_called()
        self.assertIn("::error::", self.out.getvalue())

    def test_a_reply_that_keeps_failing_ends_red_without_reposting(self):
        failures = [common.RequestError("down")] * threads_post.LINK_REPLY_TRIES
        rc, posted, _ = self.run_main("2026-10-24", publish=("m1", *failures))
        self.assertEqual(1, rc)
        self.assertEqual(1, sum(1 for c in posted.call_args_list if "reply_to" not in c.kwargs))
        self.assertIn("::error::", self.out.getvalue())


class TrialSlotTests(MainHarness):
    """The trial takes the day's first slot with room (01:40 UTC, `threads_post.py trial`), is made up once by the
    next slot with room when it was missed (cap full), with the same ct, and never goes out twice."""

    def run_trial(self, day, hour, **kw):
        handle, out = tempfile.mkstemp()
        os.close(handle)
        self.addCleanup(os.unlink, out)
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": out}):
            rc, posted, queue = self.run_main(day, hour=hour, argv=("trial",), **kw)
        return rc, posted, queue, Path(out).read_text()

    def test_a_trial_day_posts_the_entry_in_the_first_slot(self):
        rc, posted, queue, out = self.run_trial("2026-10-20", "01:40")
        self.assertEqual(0, rc)
        self.assertIn("took=true", out)
        queue.assert_not_called()
        main_call, reply_call = posted.call_args_list
        self.assertEqual(POSTS[0]["text"], main_call.args[2])
        self.assertIn("ct=th_mochi_en_01&", reply_call.args[2])

    def test_the_picture_slot_after_the_first_slot_runs_its_usual_post(self):
        first_slot = ("m1", dt.datetime(2026, 10, 20, 1, 45, tzinfo=dt.timezone.utc))
        rc, posted, queue = self.run_main("2026-10-20", up=first_slot)
        self.assertEqual(0, rc)
        queue.assert_called_once()   # no second copy of the trial; the 11:00 slot is the picture slot again
        self.assertEqual(self.QUEUED["text"], posted.call_args_list[0].args[2])
        self.assertTrue(all("th_mochi_" not in str(c.args[2]) for c in posted.call_args_list))

    def test_cap_full_posts_nothing_and_the_next_slot_makes_it_up_with_the_same_ct(self):
        # On the pre-10-21 file, where 10-20's entry owned 10-21 too.
        legacy = mock.patch.object(threads_post, "load_trial", return_value=LEGACY)
        legacy.start()
        self.addCleanup(legacy.stop)
        rc, posted, _q, out = self.run_trial("2026-10-20", "01:40", used=threads_cap.ACCOUNT_DAILY_CAP)
        self.assertEqual(0, rc)
        posted.assert_not_called()   # held by the account cap: nothing goes out, nothing else instead
        self.assertIn("took=true", out)
        for day, hour in (("2026-10-20", "13:00"), ("2026-10-21", "01:40")):
            with self.subTest(day=day, hour=hour):
                rc, posted, _q, out = self.run_trial(day, hour, used=1)
                self.assertEqual(0, rc)
                self.assertIn("took=true", out)
                main_call, reply_call = posted.call_args_list
                self.assertEqual(POSTS[0]["text"], main_call.args[2])
                self.assertIn("ct=th_mochi_en_01&", reply_call.args[2])
        self.assertIn("made up now", self.out.getvalue())   # the day after: a make-up of the 10-20 entry
        rc, posted, queue = self.run_main("2026-10-21", used=1)   # the 11:00 slot of the day after makes it up too
        self.assertEqual(0, rc)
        queue.assert_not_called()
        self.assertIn("ct=th_mochi_en_01&", posted.call_args_list[1].args[2])

    def test_the_make_up_goes_out_only_once(self):
        made_up = ("m-late", dt.datetime(2026, 10, 20, 13, 2, tzinfo=dt.timezone.utc))
        for day, hour in (("2026-10-21", "01:40"), ("2026-10-21", "13:00")):
            with self.subTest(day=day, hour=hour):
                rc, posted, _q, out = self.run_trial(day, hour, up=made_up)
                self.assertEqual(0, rc)
                self.assertIn("took=false", out)   # the slot runs its usual content
                posted.assert_not_called()
        rc, posted, queue = self.run_main("2026-10-21", up=made_up)
        self.assertEqual(0, rc)
        queue.assert_called_once()

    def test_a_missed_entry_is_not_made_up_after_its_window(self):
        days = {threads_post.trial_window_post(dt.date(2026, 10, 20) + dt.timedelta(days=i), LEGACY)["ct"]
                for i in range(2)}
        self.assertEqual({"th_mochi_en_01"}, days)
        self.assertEqual("th_mochi_ko_01", threads_post.trial_window_post(dt.date(2026, 10, 22), LEGACY)["ct"])
        self.assertEqual("th_mochi_en_03", threads_post.trial_window_post(dt.date(2026, 11, 1), LEGACY)["ct"])
        self.assertEqual("th_mochi_zh_02", threads_post.trial_window_post(dt.date(2026, 10, 23), LEGACY)["ct"])
        self.assertEqual("th_mochi_zh_03", threads_post.trial_window_post(dt.date(2026, 11, 3), LEGACY)["ct"])
        self.assertIsNone(threads_post.trial_window_post(dt.date(2026, 11, 4), LEGACY))
        self.assertIsNone(threads_post.trial_window_post(dt.date(2026, 10, 19), LEGACY))
        self.assertIsNone(threads_post.trial_window_post(None, LEGACY))
        # The current file: 10-21 has its own entry; 11-02's entry owns only its day, the daily cycle follows.
        self.assertEqual("th_mochi_en_01", threads_post.trial_window_post(dt.date(2026, 10, 20), TRIAL)["ct"])
        self.assertEqual("th_mochi_en_06", threads_post.trial_window_post(dt.date(2026, 10, 21), TRIAL)["ct"])
        self.assertEqual("th_mochi_zh_03", threads_post.trial_window_post(dt.date(2026, 11, 2), TRIAL)["ct"])
        self.assertEqual(CYCLE[0], threads_post.trial_window_post(dt.date(2026, 11, 3), TRIAL)["ct"])
        self.assertIsNone(threads_post.trial_window_post(dt.date(2026, 10, 19), TRIAL))

    def test_after_the_last_date_every_day_owes_the_next_cycle_entry_dated_that_day(self):
        by_ct = {p["ct"]: p for p in POSTS}
        day = dt.date(2026, 11, 3)
        for i in range(400):
            with self.subTest(day=day):
                entry = threads_post.trial_window_post(day, TRIAL)
                self.assertEqual(CYCLE[i % len(CYCLE)], entry["ct"])
                self.assertEqual(day.isoformat(), entry["date"])   # the rerun lookup starts that day
                self.assertEqual(by_ct[entry["ct"]]["text"], entry["text"])
            day += dt.timedelta(days=1)
        self.assertEqual("2026-11-02", by_ct["th_mochi_zh_03"]["date"])   # the file's own entries stay as they are

    def test_a_cycle_ct_the_file_does_not_hold_is_skipped_and_an_empty_cycle_ends_the_trial(self):
        odd = dict(TRIAL, daily_after_end={"cts": ["th_mochi_xx_99", "th_mochi_ja_01"]})
        self.assertEqual("th_mochi_ja_01", threads_post.trial_window_post(dt.date(2026, 11, 3), odd)["ct"])
        self.assertEqual("th_mochi_ja_01", threads_post.trial_window_post(dt.date(2026, 11, 9), odd)["ct"])
        for cfg in ({"cts": []}, {"cts": ["th_mochi_xx_99"]}, [], "on"):
            with self.subTest(cfg=cfg):
                off = dict(TRIAL, daily_after_end=cfg)
                self.assertIsNone(threads_post.trial_window_post(dt.date(2026, 11, 4), off))

    def test_a_cycle_day_posts_its_entry_in_the_first_slot_with_its_own_ct(self):
        rc, posted, queue, out = self.run_trial("2026-11-05", "01:40")
        self.assertEqual(0, rc)
        self.assertIn("took=true", out)
        queue.assert_not_called()
        ct = CYCLE[2 % len(CYCLE)]
        main_call, reply_call = posted.call_args_list
        self.assertEqual(next(p["text"] for p in POSTS if p["ct"] == ct), main_call.args[2])
        self.assertIn(f"ct={ct}&", reply_call.args[2])
        self.assertNotIn("made up now", self.out.getvalue())   # a cycle entry is dated its own day

    def test_a_lookup_failure_posts_no_trial_and_leaves_the_slot_its_usual_content(self):
        rc, posted, _q, out = self.run_trial("2026-10-20", "01:40", up=threads_post.LookupFailed("down"))
        self.assertEqual(0, rc)
        self.assertIn("took=false", out)
        posted.assert_not_called()
        self.assertIn("::warning::", self.out.getvalue())

    def test_find_trial_post_reads_the_window_and_matches_the_text(self):
        post = POSTS[0]
        rows = {"data": [{"id": "x", "text": "other", "timestamp": "2026-10-20T02:00:00+0000"},
                         {"id": "m9", "text": post["text"], "timestamp": "2026-10-20T13:01:00+0000"}]}
        opener = mock.MagicMock()
        opener.return_value.__enter__.return_value.read.return_value = json.dumps(rows).encode()
        got = threads_post.find_trial_post("tok", post, dt.date(2026, 10, 21), opener=opener)
        self.assertEqual(("m9", dt.datetime(2026, 10, 20, 13, 1, tzinfo=dt.timezone.utc)), got)
        rows["data"] = rows["data"][:1]
        opener.return_value.__enter__.return_value.read.return_value = json.dumps(rows).encode()
        self.assertIsNone(threads_post.find_trial_post("tok", post, dt.date(2026, 10, 21), opener=opener))
        with self.assertRaises(threads_post.LookupFailed):
            threads_post.find_trial_post("tok", post, dt.date(2026, 10, 21), opener=mock.Mock(side_effect=OSError))


if __name__ == "__main__":
    unittest.main()
