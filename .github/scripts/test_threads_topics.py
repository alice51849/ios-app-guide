#!/usr/bin/env python3
"""Threads topic tag (threads_topics.py), the review line of the link reply, and the Mochi trial status record."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import download_links as DL  # noqa: E402
import threads_post as T  # noqa: E402
import threads_topics as TT  # noqa: E402
from social_post_common import HTTPStatusError  # noqa: E402

MOCHI = "6785004775"


class CleanTests(unittest.TestCase):
    def test_valid_tags_pass_and_a_hash_is_dropped(self):
        self.assertEqual("Productivity", TT.clean("Productivity"))
        self.assertEqual("ADHD", TT.clean(" #ADHD "))
        self.assertEqual("x" * 50, TT.clean("x" * 50))

    def test_invalid_tags_are_dropped_with_a_warning(self):
        for bad in ("", "#", "x" * 51, "a.b", "R&D", "two\nlines", 5):
            with self.subTest(bad=bad):
                err = io.StringIO()
                with redirect_stderr(err):
                    self.assertIsNone(TT.clean(bad))
                self.assertIn("::warning::", err.getvalue())
        self.assertIsNone(TT.clean(None))


class DefaultTopicTests(unittest.TestCase):
    def test_category_default_in_the_posts_language(self):
        self.assertEqual("Productivity", TT.for_post(MOCHI, "hello", "en-US"))
        self.assertEqual("效率", TT.for_post(MOCHI, "待辦清單"))
        self.assertEqual("생산성", TT.for_post(MOCHI, "할 일"))
        self.assertEqual("仕事効率化", TT.for_post(MOCHI, "やることリスト"))
        self.assertEqual("手帳", TT.for_post(MOCHI, "x", "zh-Hant", "手帳"))
        self.assertIsNone(TT.for_post("1", "hello"))

    def test_every_category_topic_is_valid(self):
        for category, topics in TT.CATEGORY_TOPICS.items():
            for lang, tag in topics.items():
                with self.subTest(category=category, lang=lang):
                    self.assertEqual(tag, TT.clean(tag))

    def test_every_trial_entry_has_a_valid_topic(self):
        trial = T.load_trial()
        # 2026-10-21 audience rotation (00_GrowthEngine ops/company/audience/mochi.md): exam / host / reset in turn.
        by_audience = {"exam": {"공부", "Study"}, "host": {"Holidays", "Productivity"}, "reset": {"Productivity"}}
        before = {"en-US": {"Productivity", "ADHD"}}
        order = ["exam", "host", "reset"]
        rotated = [p for p in trial["posts"] if p.get("audience")]
        self.assertEqual(12, len(rotated))
        for i, post in enumerate(rotated):
            with self.subTest(ct=post["ct"]):
                self.assertEqual(order[i % 3], post["audience"])
                self.assertIn(T.trial_topic(trial, post), by_audience[post["audience"]])
        for post in trial["posts"]:
            if not post.get("audience"):
                self.assertIn(T.trial_topic(trial, post), before[post["lang"]])
        by_ct = {p["ct"]: p for p in trial["posts"]}
        cycle = [by_ct[ct].get("audience") or "reset" for ct in trial["daily_after_end"]["cts"]]
        self.assertEqual([order[i % 3] for i in range(len(cycle))], cycle)


class ReviewTailTests(unittest.TestCase):
    def test_trial_reply_keeps_the_download_link_and_adds_the_review_line(self):
        trial = T.load_trial()
        for post in trial["posts"]:
            with self.subTest(ct=post["ct"]):
                reply = T.trial_reply(trial, post)
                store, play = T.trial_link_urls(trial, post)
                self.assertEqual([], DL.threads_reply_problems(reply, store, play))
                self.assertEqual(1, reply.count(f"https://apps.apple.com/app/id{MOCHI}?action=write-review"))
                self.assertLessEqual(len(reply), T.MAX_POST_CHARS)
                self.assertLess(reply.index("ct=th_mochi"), reply.index("action=write-review"))

    def test_review_link_is_not_counted_as_a_download_link(self):
        only_review = TT.review_tail("App Store: https://example.com", MOCHI, "en-US")
        self.assertEqual(set(), DL.store_ids_in(only_review))

    def test_it_is_left_out_when_it_does_not_fit(self):
        links = "x" * 495
        self.assertEqual(links, TT.review_tail(links, MOCHI, "en-US", limit=500))


class PublishTopicTests(unittest.TestCase):
    def test_topic_is_sent_on_a_top_level_post_only(self):
        calls = []
        def fake(url, data, **_):
            calls.append(dict(data))
            return {"id": "c1"}
        with mock.patch.object(T, "_post", side_effect=fake):
            T.publish_post("t", "u", "hi", sleeper=lambda _s: None, topic_tag="ADHD")
            T.publish_post("t", "u", "hi", sleeper=lambda _s: None, reply_to="m1", topic_tag="ADHD")
        self.assertEqual("ADHD", calls[0].get("topic_tag"))
        self.assertNotIn("topic_tag", calls[2])

    def test_a_refused_topic_posts_without_it(self):
        calls = []
        def fake(url, data, **_):
            calls.append(dict(data))
            if "topic_tag" in data:
                raise HTTPStatusError("Threads container", 400, "bad topic")
            return {"id": "c1"}
        with mock.patch.object(T, "_post", side_effect=fake), redirect_stderr(io.StringIO()):
            self.assertEqual("c1", T.publish_post("t", "u", "hi", sleeper=lambda _s: None, topic_tag="ADHD"))
        self.assertEqual(["ADHD", None, None], [c.get("topic_tag") for c in calls])

    def test_an_invalid_topic_is_not_sent(self):
        calls = []
        with mock.patch.object(T, "_post", side_effect=lambda u, d, **_: calls.append(dict(d)) or {"id": "c"}), \
                redirect_stderr(io.StringIO()):
            T.publish_post("t", "u", "hi", sleeper=lambda _s: None, topic_tag="a.b")
        self.assertNotIn("topic_tag", calls[0])


class TrialStatusTests(unittest.TestCase):
    def test_record_and_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            post = {"ct": "th_mochi_en_06", "date": "2026-10-21"}
            day = dt.date(2026, 10, 21)
            now = dt.datetime(2026, 10, 21, 1, 41, tzinfo=dt.timezone.utc)
            self.assertTrue(T.record_trial_status(post, day, T._linked("p1", True, "r1"), path=out, now=now))
            later = now + dt.timedelta(hours=3)
            T.record_trial_status(post, day, T._linked("p1", True, None), path=out, now=later)
            entry = T._read_status(out)["2026-10-21"]
            self.assertEqual(("p1", "r1", "2026-10-21T01:41:00Z"),
                             (entry["post_id"], entry["link_reply_id"], entry["posted_at"]))
            repo = os.path.join(tmp, "repo.json")
            T._write_status({"2026-10-20": {"post_id": "old"}}, repo)
            T.merge_trial_status(out, path=repo)
            self.assertEqual({"2026-10-20", "2026-10-21"}, set(T._read_status(repo)))

    def test_nothing_is_recorded_from_an_import_or_without_a_post(self):
        with mock.patch.object(T, "_write_status", side_effect=AssertionError("no write")):
            self.assertFalse(T.record_trial_status({"ct": "x"}, dt.date(2026, 10, 21), T.ThreadsResult("p", True)))
            self.assertFalse(T.record_trial_status({"ct": "x"}, dt.date(2026, 10, 21), T.ThreadsResult(None, False),
                                                   path="/nonexistent/x.json"))

    def test_a_failed_write_is_a_warning_only(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertFalse(T.record_trial_status({"ct": "x", "date": "2026-10-21"}, dt.date(2026, 10, 21),
                                                   T.ThreadsResult("p", True), path="/nonexistent/dir/x.json"))
        self.assertIn("::warning::", err.getvalue())

    def test_the_backfilled_record_of_2026_10_20(self):
        entry = T._read_status(T.TRIAL_STATUS_PATH)["2026-10-20"]
        self.assertEqual(("th_mochi_en_01", "18131744458766668"), (entry["ct"], entry["post_id"]))


if __name__ == "__main__":
    unittest.main()
