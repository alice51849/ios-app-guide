#!/usr/bin/env python3
"""The Threads Mochi top-10 trial (threads_post.py TRIAL_PATH, 2026-10-20 .. 2026-11-01): the picture slot of each
listed date goes to that entry; every other day, and every day after the trial, runs the usual logic; the entry's
link reply carries the App Store link with its own ct; the account cap and the link checks still hold it."""
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
START, END = dt.date(2026, 10, 19), dt.date(2026, 11, 2)
# Words that name a price or a paid tier the trial copy must not carry (owner's video rule (b), same for text).
PRICE_WORDS = re.compile(r"[$€£¥￥₩]|\d+\s?(?:元|円|원|usd|dollars?)|\bfree\b|\bpro\b|\bpremium\b|免費|免费|進階|付費|"
                         r"無料|有料|プロ|무료|유료|프로|프리미엄", re.I)


class TrialFileTests(unittest.TestCase):
    def test_seven_entries_every_other_day_inside_the_trial(self):
        self.assertEqual("mochi", TRIAL.get("app_key"))
        self.assertEqual(MOCHI, DL.app_store_id(TRIAL.get("app_store")))
        days = [dt.date.fromisoformat(p["date"]) for p in POSTS]
        self.assertEqual(7, len(days))
        self.assertEqual(sorted(set(days)), days)
        self.assertTrue(all(START <= d <= END for d in days), days)
        self.assertTrue(all((b - a).days == 2 for a, b in zip(days, days[1:])), days)

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


class TrialMainTests(unittest.TestCase):
    """threads_post.main() on the picture slot (03:00 UTC = 11:00 Taiwan, the same date)."""

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

    def run_main(self, day, *, used=0, publish=("m1", "r1"), find=None, queued=True):
        env = {"THREADS_TOKEN": "tok", "THREADS_USER_ID": "uid", "THREADS_SLOT": f"{day}T03:00:00+00:00"}
        quota = (mock.patch.object(threads_cap, "quota_usage", side_effect=used) if isinstance(used, Exception)
                 else mock.patch.object(threads_cap, "quota_usage", return_value=used))
        queued_post = dict(self.QUEUED, date=day) if queued else None
        with (
            mock.patch.dict(os.environ, env),
            quota,
            mock.patch.object(threads_post, "queued_today", return_value=queued_post) as queue,
            mock.patch.object(threads_post, "find_own_post", return_value=find),
            mock.patch.object(threads_post, "publish_post", side_effect=list(publish)) as posted,
        ):
            return threads_post.main(), posted, queue

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
        for day in ("2026-10-19", "2026-10-21", "2026-10-31", "2026-11-02", "2026-11-03", "2026-11-04"):
            with self.subTest(day=day):
                rc, posted, queue = self.run_main(day)
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
        rc, posted, _ = self.run_main("2026-10-22", publish=("r1",), find="m-existing")
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


if __name__ == "__main__":
    unittest.main()
