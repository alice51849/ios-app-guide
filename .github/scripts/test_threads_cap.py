#!/usr/bin/env python3
"""The Threads account cap (threads_cap.py): at most 3 top-level posts in 24 hours on @hourstag.app, every
pipeline included, checked right before each top-level publish. Replies are never held. HTTP is mocked."""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")  # the pre-post QA gate makes no network calls in tests

import channel_rotation  # noqa: E402
import threads_cap  # noqa: E402
import threads_post  # noqa: E402


# pytest does not run unittest's module cleanups, so the module-wide patches below are undone in
# tearDownModule (unittest and pytest both call it); otherwise they leak into the test files run after this one
# in the same process (e.g. clip_source.fetch_clip stays the stand-in for test_clip_source.py).
_MODULE_PATCHES = []


def tearDownModule():
    while _MODULE_PATCHES:
        _MODULE_PATCHES.pop().__exit__(None, None, None)


def setUpModule():
    # threads_post.main() gives the dates of the Mochi trial file to that trial (test_threads_mochi_trial.py); the
    # main() tests here run on the real clock, so they see no trial day and keep testing the usual paths.
    no_trial = mock.patch.object(threads_post, "load_trial", return_value={})
    no_trial.__enter__()
    _MODULE_PATCHES.append(no_trial)
    # The channel rotation holdout (channel_rotation.py) reads the real UTC date: in a week the plan gives
    # to Threads these tests saw "paused" instead of the path they test, and the workflow's Test step
    # went red for the whole week (social-extra 2026-11-15..18: three days without posts or feed.json).
    # These tests are about other things; test_channel_rotation.py covers the holdout itself.
    no_holdout = mock.patch.object(channel_rotation, "paused_notice", return_value=False)
    no_holdout.__enter__()
    _MODULE_PATCHES.append(no_holdout)


MOCHI = "6785004775"  # Android-live App Store id (App Store + Google Play link reply)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def limit(used, total=250):
    return {"data": [{"quota_usage": used, "config": {"quota_total": total, "quota_duration": 86400}}]}


class FakeGraph:
    """urlopen stand-in: the publishing-limit answer (a count, or an exception to raise) and the /me lookup."""

    def __init__(self, used):
        self.used = used
        self.limit_calls = []

    def __call__(self, url, timeout=30):
        url = url.full_url if hasattr(url, "full_url") else url
        if "/threads_publishing_limit" in url:
            self.limit_calls.append(url)
            if isinstance(self.used, BaseException):
                raise self.used
            return FakeResponse(limit(self.used))
        if "/me?" in url:
            return FakeResponse({"id": "uid"})
        raise AssertionError(f"unexpected HTTP call {url.split('?')[0]}")


class _Case(unittest.TestCase):
    def setUp(self):
        handle, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(handle)
        self.addCleanup(os.unlink, self.log_path)
        for patcher in (mock.patch.dict(os.environ, {"LINK_GUARD_LOG": self.log_path, "THREADS_TOKEN": "tok",
                                                     "THREADS_USER_ID": "uid", "THREADS_SLOT": ""}),
                        mock.patch("sys.stderr", new_callable=io.StringIO)):
            patcher.start()
            self.addCleanup(patcher.stop)
        out = mock.patch("sys.stdout", new_callable=io.StringIO)
        self.out = out.start()
        self.addCleanup(out.stop)

    def graph(self, used):
        fake = FakeGraph(used)
        patcher = mock.patch("urllib.request.urlopen", side_effect=fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def assert_skip_line(self, used):
        printed = self.out.getvalue()
        self.assertIn(f"⏸ Threads 帳號近 24 小時已發 {used} 則（上限 3），本次不發", printed)
        self.assertNotIn("::error::", printed)
        self.assertNotIn("::warning::", printed)


class CapTest(_Case):
    def test_the_cap_is_one_shared_constant_of_three(self):
        self.assertEqual(3, threads_cap.ACCOUNT_DAILY_CAP)
        import threads_series
        import utility_cards
        self.assertIs(threads_cap.ACCOUNT_DAILY_CAP, utility_cards.THREADS_CAP)
        self.assertEqual(threads_cap.ACCOUNT_DAILY_CAP, threads_series.load()["daily_cap"])

    def test_the_count_is_read_from_the_publishing_limit_of_the_account(self):
        opener = mock.Mock(return_value=FakeResponse(limit(2)))
        self.assertEqual(2, threads_cap.quota_usage("tok", "uid", opener))
        url = opener.call_args.args[0]
        self.assertTrue(url.startswith("https://graph.threads.net/v1.0/uid/threads_publishing_limit?"))
        self.assertEqual(["quota_usage,config"], urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["fields"])
        threads_cap.quota_usage("tok", "", opener)
        self.assertIn("/v1.0/me/threads_publishing_limit?", opener.call_args.args[0])

    def test_quota_two_leaves_room(self):
        self.graph(2)
        self.assertEqual(threads_cap.ROOM, threads_cap.account_status("tok", "uid"))
        self.assertNotIn("本次不發", self.out.getvalue())

    def test_quota_three_or_more_is_full_and_only_a_skip(self):
        for used in (3, 4):
            with self.subTest(used=used):
                self.graph(used)
                self.assertEqual(threads_cap.FULL, threads_cap.account_status("tok", "uid"))
                self.assert_skip_line(used)

    def test_a_failed_or_odd_count_is_unknown_with_a_warning_and_no_token(self):
        broken = [urllib.error.HTTPError("u", 500, "down", {}, None), urllib.error.URLError("offline"),
                  OSError("reset")]
        for error in broken:
            with self.subTest(error=error.__class__.__name__):
                self.graph(error)
                self.assertEqual(threads_cap.UNKNOWN, threads_cap.account_status("tok-secret", "uid"))
        for payload in ({"data": []}, {"error": {"message": "x"}}, limit(-1), limit(5, total=0), limit(300),
                        {"data": [{"quota_usage": 1}]}, b"not json"):
            with self.subTest(payload=str(payload)[:40]):
                opener = mock.Mock(return_value=FakeResponse(payload))
                self.assertEqual(threads_cap.UNKNOWN, threads_cap.account_status("tok-secret", "uid", opener=opener))
        printed = self.out.getvalue()
        self.assertIn("::warning::", printed)
        self.assertNotIn("::error::", printed)
        self.assertNotIn("tok-secret", printed)


class ThreadsPostGateTest(_Case):
    """threads_post.publish_linked (picture / queued posts, threads_series.py evening posts) and publish_text."""

    def linked(self, find=None):
        post = {"app_id": MOCHI, "ct": "bm_mochi_us_th", "app": "x", "date": "2026-10-20", "text": "Pain line"}
        store, play = threads_post.queued_link_urls(post)
        with mock.patch.object(threads_post, "publish_post", side_effect=["m1", "r1"]) as publish:
            result = threads_post.publish_linked("tok", "uid", post["text"], threads_post.queued_links(post), store,
                                                 play, sleeper=mock.Mock(), find=lambda *_: find,
                                                 find_reply=lambda *_: None)
        return result, publish

    def test_quota_two_posts_the_post_and_its_link_reply(self):
        graph = self.graph(2)
        result, publish = self.linked()
        self.assertEqual(("m1", True), tuple(result))
        self.assertEqual(2, publish.call_count)
        self.assertEqual("m1", publish.call_args_list[1].kwargs["reply_to"])
        self.assertTrue(graph.limit_calls[0].startswith("https://graph.threads.net/v1.0/uid/threads_publishing_limit"))

    def test_quota_three_posts_nothing_and_stays_green(self):
        self.graph(3)
        result, publish = self.linked()
        self.assertEqual((None, True), tuple(result))  # link_ok: nothing is left without its link, no red step
        publish.assert_not_called()
        self.assert_skip_line(3)

    def test_a_failed_quota_call_posts_nothing(self):
        self.graph(urllib.error.URLError("offline"))
        result, publish = self.linked()
        self.assertEqual((None, False), tuple(result))
        publish.assert_not_called()
        self.assertIn("::warning::", self.out.getvalue())

    def test_main_skip_exits_zero(self):
        self.graph(3)
        queued = {"date": "2026-10-20", "app": "x", "app_id": MOCHI, "ct": "bm_mochi_us_th", "task": "t",
                  "text": "Pain line, no URL."}
        with mock.patch.object(threads_post, "queued_today", return_value=queued), \
                mock.patch.object(threads_post, "find_own_post", return_value=None), \
                mock.patch.object(threads_post, "publish_post") as publish, mock.patch("time.sleep"):
            self.assertEqual(0, threads_post.main())
        publish.assert_not_called()
        self.assert_skip_line(3)

    def test_series_evening_skip_exits_zero_without_a_clip_on_top(self):
        import threads_series as T
        self.graph(3)
        chosen = {"series": "CONV", "app": "x", "app_id": MOCHI, "ct": "bm_x_us_th", "locale": "en",
                  "text": "Pain line", "image_url": None}
        with mock.patch.object(T, "has_room", return_value=True), mock.patch.object(T, "plan", return_value=chosen), \
                mock.patch.object(T, "planned_clip", return_value=None), \
                mock.patch.object(threads_post, "find_own_post", return_value=None), \
                mock.patch.object(threads_post, "publish_post") as publish, mock.patch("time.sleep"):
            self.assertEqual(0, T.main(["evening", "--date", "2026-10-20", "--offline"]))
        publish.assert_not_called()
        self.assertIn("fallback=none", self.out.getvalue())
        self.assert_skip_line(3)

    def test_publish_text_is_held_too(self):
        for used, posts in ((2, 1), (3, 0), (urllib.error.URLError("offline"), 0)):
            with self.subTest(used=str(used)):
                self.graph(used)
                with mock.patch.object(threads_post, "publish_post", return_value="p1") as publish:
                    got = threads_post.publish_text("tok", "uid", "text")
                self.assertEqual("p1" if posts else None, got)
                self.assertEqual(posts, publish.call_count)


class RepliesAreNotGatedTest(_Case):
    """The first-reply download link and link_backfill.py's replies are not top-level posts."""

    def test_the_link_reply_goes_out_at_a_full_account(self):
        graph = self.graph(3)
        post = {"app_id": MOCHI, "ct": "bm_mochi_us_th"}
        store, play = threads_post.queued_link_urls(post)
        with mock.patch.object(threads_post, "publish_post", return_value="r1") as publish:
            got = threads_post.publish_link_reply("tok", "uid", "m1", threads_post.queued_links(post), store, play,
                                                  sleeper=mock.Mock())
        self.assertEqual("r1", got)
        self.assertEqual("m1", publish.call_args.kwargs["reply_to"])
        self.assertEqual([], graph.limit_calls)

    def test_a_rerun_adds_the_missing_reply_under_the_post_that_is_up_even_at_a_full_account(self):
        graph = self.graph(3)
        post = {"app_id": MOCHI, "ct": "bm_mochi_us_th", "text": "Pain line"}
        store, play = threads_post.queued_link_urls(post)
        with mock.patch.object(threads_post, "publish_post", return_value="r1") as publish:
            result = threads_post.publish_linked("tok", "uid", post["text"], threads_post.queued_links(post), store,
                                                 play, sleeper=mock.Mock(), find=lambda *_: "m-up",
                                                 find_reply=lambda *_: None)
        self.assertEqual(("m-up", True), tuple(result))
        self.assertEqual("m-up", publish.call_args.kwargs["reply_to"])
        self.assertEqual([], graph.limit_calls)

    def test_link_backfill_replies_never_read_the_cap(self):
        import own_posts
        graph = self.graph(3)
        client = own_posts.ThreadsClient("tok")
        client.user_id = "uid"
        with mock.patch.object(client, "_post", side_effect=[{"id": "c1"}, {"id": "r1"}]) as post:
            self.assertEqual("r1", client.reply("m1", "App Store: https://apps.apple.com/app/id1", sleeper=mock.Mock()))
        self.assertEqual("m1", post.call_args_list[0].kwargs["reply_to_id"])
        self.assertEqual([], graph.limit_calls)


class ClipGateTest(_Case):
    CLIP = {"app": "mochi", "locale": "en", "url": "https://files.catbox.moe/mochi_en.mp4",
            "store_url": f"https://apps.apple.com/us/app/id{MOCHI}?pt=118326163&ct=h7_mochi_en&mt=8",
            "hook": "hook", "name": "Mochi", "search": "mochi"}

    def post(self, used):
        import clip_posts as C
        self.graph(used)
        calls = []

        def fake_post(url, fields, timeout=60):
            calls.append((url.rsplit("/", 1)[-1], fields))
            return {"id": f"id{len(calls)}"}

        def fake_get(url, timeout=60):
            if "/replies" in url:
                return {"data": []}
            return {"id": "uid", "status": "FINISHED", "permalink": "https://www.threads.net/@x/post/1"}

        with mock.patch.object(C, "_post", side_effect=fake_post), mock.patch.object(C, "_get", side_effect=fake_get), \
                mock.patch.object(C, "caption", return_value="hook caption"), mock.patch.object(C.time, "sleep"):
            try:
                return C.post_threads(dict(self.CLIP)), calls
            except threads_cap.QuotaUnknown as error:
                return error, calls

    def published(self, calls):
        return [f for name, f in calls if name == "threads_publish"]

    def test_quota_two_publishes_the_video_and_its_link_reply(self):
        out, calls = self.post(2)
        self.assertEqual("id2", out["id"])
        self.assertTrue(out["link_reply"])
        self.assertEqual(2, len(self.published(calls)))

    def test_quota_three_skips_the_video(self):
        out, calls = self.post(3)
        self.assertIsNone(out)
        self.assertEqual([], self.published(calls))
        self.assert_skip_line(3)

    def test_a_failed_quota_call_posts_nothing_and_the_run_ends_red(self):
        out, calls = self.post(urllib.error.URLError("offline"))
        self.assertIsInstance(out, threads_cap.QuotaUnknown)
        self.assertEqual([], self.published(calls))
        import clip_posts as C
        args = ["clip_posts.py", "threads", "--slot", "1", "--date", "2026-10-20"]
        with mock.patch.object(sys, "argv", args), mock.patch.object(C, "scheduled", return_value=dict(self.CLIP)), \
                mock.patch.object(C, "yields_to_evening", return_value=None), \
                mock.patch.object(C.volume_ramp, "room", return_value=(3, 0, 3)), \
                mock.patch.object(C, "qa_variant", return_value=({"id": "h1"}, [])), \
                mock.patch.object(C, "post_threads", side_effect=threads_cap.QuotaUnknown("x")), \
                mock.patch.object(C.volume_ramp, "handle_error") as throttle, \
                mock.patch.object(C.clip_progress, "record_post") as record:
            self.assertEqual(1, C.main())
        throttle.assert_not_called()  # not a "slow down" answer: the ramp stays where it is
        record.assert_not_called()


class CardGateTest(_Case):
    """countdown_cards.threads_image, also used by utility_cards.post_threads."""

    def image(self, used):
        import countdown_cards as C
        import threads_series
        self.graph(used)
        calls = []

        def fake_post(url, fields, timeout=60):
            calls.append((url.rsplit("/", 1)[-1], fields))
            return {"id": f"id{len(calls)}"}

        def fake_get(url, timeout=60):
            return {"data": []} if "/replies" in url else {"id": "uid"}

        with mock.patch.object(C, "_post", side_effect=fake_post), mock.patch.object(C, "_get", side_effect=fake_get), \
                mock.patch.object(threads_series, "has_room", return_value=True), mock.patch.object(C.time, "sleep"):
            media = C.threads_image("https://x/card.jpg", "Head", ["App Store: https://apps.apple.com/app/id1"])
        return media, [f for name, f in calls if name == "threads_publish"]

    def test_quota_two_posts_the_card_and_its_link_reply(self):
        media, published = self.image(2)
        self.assertEqual("id2", media)
        self.assertEqual(2, len(published))

    def test_quota_three_skips_the_card(self):
        media, published = self.image(3)
        self.assertIsNone(media)
        self.assertEqual([], published)
        self.assert_skip_line(3)

    def test_a_failed_quota_call_posts_nothing(self):
        media, published = self.image(urllib.error.HTTPError("u", 400, "bad", {}, None))
        self.assertIsNone(media)
        self.assertEqual([], published)
        self.assertIn("::warning::", self.out.getvalue())


class FullSlotRetryTest(unittest.TestCase):
    """2026-11-08..14: a full account at the slot's time is often the day before's post a few minutes short of
    leaving Threads' rolling 24 hours. The slot is not done then: it stays open for 2 hours, then is a cap skip."""

    import datetime as _dt
    UTC = _dt.timezone.utc

    def at(self, day, hour, minute=0):
        return self._dt.datetime(2026, 11, day, hour, minute, tzinfo=self.UTC)

    def run_full(self, slot, now):
        handle, receipt = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        os.unlink(receipt)
        handle, output = tempfile.mkstemp()
        os.close(handle)
        self.addCleanup(lambda: [os.path.exists(f) and os.unlink(f) for f in (receipt, output)])
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            action = threads_cap.full_slot(slot, now, receipt, output)
        outputs = dict(line.split("=", 1) for line in Path(output).read_text().split())
        body = Path(receipt).read_text() if os.path.exists(receipt) else ""
        return action, outputs, body, out.getvalue()

    def test_full_at_the_slot_is_not_done_and_retries_inside_the_grace(self):
        for slot, now in ((self.at(14, 3), self.at(14, 3, 2)), (self.at(12, 13), self.at(12, 13, 4))):
            action, outputs, receipt, printed = self.run_full(slot, now)
            self.assertEqual(threads_cap.RETRY, action)
            self.assertEqual({"retry": "true", "capskip": "false"}, outputs)
            self.assertEqual("", receipt)  # no skip recorded yet
            self.assertNotIn("::error::", printed)

    def test_the_next_backup_inside_the_grace_is_the_retry(self):
        self.assertEqual(self.at(14, 3, 47), threads_cap.next_backup(self.at(14, 3, 2)))
        self.assertEqual(self.at(12, 14, 47), threads_cap.next_backup(self.at(12, 13, 4)))

    def test_after_the_last_retry_inside_the_grace_the_slot_is_a_cap_skip_with_a_receipt(self):
        # 03:47 backup for 03:00 (next backup 11:47 > 05:00) and 14:47 for 13:00 (next 17:47 > 15:00).
        for slot, now in ((self.at(14, 3), self.at(14, 3, 48)), (self.at(12, 13), self.at(12, 14, 48)),
                          (self.at(12, 13), self.at(12, 15, 30))):
            action, outputs, receipt, printed = self.run_full(slot, now)
            self.assertEqual(threads_cap.SKIP, action)
            self.assertEqual({"retry": "false", "capskip": "true"}, outputs)
            row = json.loads(receipt)
            self.assertEqual(slot.isoformat(), row["slot"])
            self.assertEqual("cap_full_after_grace", row["reason"])
            self.assertEqual(3, row["cap"])
            self.assertIn("滿額跳過", printed)

    def test_a_backup_too_close_to_catch_the_run_finished_is_not_counted(self):
        # 03:45: the 03:47 backup would still see this run running, so the next one (11:47) is past the grace.
        self.assertEqual(threads_cap.SKIP, threads_cap.full_slot_action(self.at(14, 3), self.at(14, 3, 45)))

    def test_backup_times_match_clip_backup_crons(self):
        import re
        text = (Path(__file__).resolve().parents[1] / "workflows" / "clip-backup.yml").read_text(encoding="utf-8")
        crons = re.findall(r"- cron: '(\d+) (\d+) \* \* \*'", text)
        self.assertEqual(sorted((int(h), int(m)) for m, h in crons), sorted(threads_cap.BACKUP_TIMES))

    def test_the_open_step_name_is_the_workflow_step_and_the_gate_flag(self):
        text = (Path(__file__).resolve().parents[1] / "workflows" / "threads-post.yml").read_text(encoding="utf-8")
        self.assertIn(f'- name: "{threads_cap.OPEN_STEP}"', text)
        self.assertIn(f'--open-step "{threads_cap.OPEN_STEP}"', text)
        self.assertIn("if: steps.room.outputs.retry == 'true'", text)

    def test_merge_skip_keeps_one_row_per_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            skips, receipt = Path(tmp, "skips.json"), Path(tmp, "r.json")
            for minute in (48, 50):
                receipt.write_text(json.dumps(threads_cap.skip_receipt(self.at(14, 3), self.at(14, 3, minute))))
                rows = threads_cap.merge_skip(receipt, skips)
            self.assertEqual(1, len(rows))
            self.assertEqual(json.loads(skips.read_text()), rows)

    def test_a_retry_never_lifts_the_cap(self):
        # The retried run reads the same count: still 3 is still a skip, so no 4th post in any 24 hours.
        self.assertEqual(3, threads_cap.ACCOUNT_DAILY_CAP)
        fake = FakeGraph(3)
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(threads_cap.FULL, threads_cap.account_status("tok", opener=fake))
            self.assertEqual(threads_cap.ROOM, threads_cap.account_status("tok", opener=FakeGraph(2)))


if __name__ == "__main__":
    unittest.main()
