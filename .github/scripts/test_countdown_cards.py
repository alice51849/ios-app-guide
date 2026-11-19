#!/usr/bin/env python3
"""Tests for countdown_cards.py (no network): every countdown post carries the download link."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import countdown_cards as C  # noqa: E402
import threads_cap  # noqa: E402


# pytest does not run unittest's module cleanups, so the module-wide patches below are undone in
# tearDownModule (unittest and pytest both call it); otherwise they leak into the test files run after this one
# in the same process (e.g. clip_source.fetch_clip stays the stand-in for test_clip_source.py).
_MODULE_PATCHES = []


def tearDownModule():
    while _MODULE_PATCHES:
        _MODULE_PATCHES.pop().__exit__(None, None, None)


def setUpModule():
    # threads_cap.py reads the account's 24-hour post count right before each top-level Threads post. These tests
    # are about other things, so the account has room here; test_threads_cap.py covers the cap itself. Entered
    # directly rather than with start(), so a test's mock.patch.stopall cannot undo it for the tests after it.
    room = mock.patch.object(threads_cap, "quota_usage", return_value=0)
    room.__enter__()
    _MODULE_PATCHES.append(room)


def event(locale="zh-Hant"):
    return next(e for e in C.EVENTS if e["locale"] == locale)


def meta(e):
    return {"event": e["id"], "locale": e["locale"], "caption": "學測倒數\n每天一點點\n\n在 App Store 搜尋「CountDaysNow」"}


class CountdownLinksTest(unittest.TestCase):
    def test_instagram_and_telegram_texts_hold_the_full_urls(self):
        for locale in ("zh-Hant", "ko", "ja", "en"):
            e = event(locale)
            text = C.telegram_text(meta(e), e)
            store, _play = C.download_urls(e, "telegram")
            self.assertIn(store, text, locale)
            self.assertIn("ct=" + C.DL.app_campaign("telegram", C.DL.app_store_id(store)) + "&", store)
            self.assertTrue(C.DL.has_download_link(text, store), locale)
            # Instagram (owner 2026-10-17): no URL; the profile-link line and #CountDaysNow instead.
            ig = C.instagram_text(meta(e), e)
            self.assertNotIn("https://", ig, locale)
            self.assertEqual(ig.splitlines()[-1].split()[0], "#CountDaysNow", locale)
            self.assertEqual([], C.DL.instagram_problems(ig, "CountDaysNow", locale=e["locale"]), locale)
        self.assertIn("📲 請到個人檔案（bio）的連結下載", C.instagram_text(meta(event()), event()))

    def test_qa_passes_the_real_texts_and_refuses_bare_ones(self):
        import post_qa
        e = event()
        for channel, missing in (("instagram", "profile-link line"), ("telegram", "download link")):
            self.assertFalse([p for p in C.qa_problems(meta(e), e, channel, online=False)
                              if "download link" in p or "profile-link" in p or "brand hashtag" in p], channel)
            bare = post_qa.card_problems("學測倒數\n連結在 bio", "zh-Hant", channel, store_url=C.store_url(e, "qa"),
                                         name="CountDaysNow", online=False)
            self.assertTrue(any(missing in p for p in bare), channel)

    def test_telegram_send_carries_the_link_in_the_caption_and_the_button(self):
        e = event()
        with mock.patch.object(C, "send_photo") as send:
            C.post_telegram("card.jpg", meta(e), e)
        self.assertIn(C.store_url(e, "tg"), send.call_args[0][1])
        btn = send.call_args[0][2][0]["url"]
        self.assertIn("ct=" + C.DL.app_campaign("telegram", C.DL.app_store_id(btn)) + "&", btn)
        self.assertEqual(send.call_args[1]["guard"][0], C.store_url(e, "tg"))

    def test_the_guard_adds_a_missing_link_and_refuses_when_none_is_known(self):
        e = event()
        text = C.guarded("bare", C.download_urls(e, "instagram"), 2200, "t")
        self.assertIn(C.store_url(e, "ig"), text)
        with self.assertRaises(C.DL.MissingDownloadLink):
            C.guarded("bare", ("", None), 2200, "t")
        self.assertEqual(C.guarded("bare", None, 2200, "t"), "bare")

    def test_a_threads_post_without_its_link_reply_does_not_make_the_run_repost(self):
        e = event()
        C.LINK_FAILURES.clear()
        C.LINK_FAILURES.append("m1")
        with mock.patch.object(sys, "argv", ["c", "post", "--card", "x.jpg"]), \
                mock.patch.object(C.Path, "read_text", return_value='{"event": "%s", "locale": "%s", "caption": "c"}' % (e["id"], e["locale"])), \
                mock.patch.object(C, "qa_problems", return_value=[]), mock.patch.object(C, "post_telegram"), \
                mock.patch.object(C, "post_threads"), mock.patch.object(C, "post_instagram"):
            self.assertEqual(C.main(), 0, "a red run is re-dispatched and posts the card twice")
        C.LINK_FAILURES.clear()


    def test_a_retry_does_not_double_a_reply_that_was_published_after_all(self):
        e = event()
        links = C.link_lines(e, "threads")
        calls = []

        def post(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id") and len([c for c in calls if c.get("reply_to_id")]) == 1:
                raise RuntimeError("timeout")  # published on the platform, but the answer never came back
            return {"id": f"id{len(calls)}"}

        def get(url, timeout=60):
            if "/replies" in url:
                return {"data": [{"text": "\n".join(links), "is_reply_owned_by_me": True}]}
            return {"id": "u"}

        C.LINK_FAILURES.clear()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), mock.patch.object(C, "_get", side_effect=get), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C.time, "sleep"), \
                mock.patch("threads_series.has_room", return_value=True):
            C.threads_image("https://x/card.jpg", "Head", links)
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 1, "no second reply once ours is found")
        self.assertEqual(C.LINK_FAILURES, [])

    def test_a_retry_that_cannot_look_does_not_post_a_second_reply(self):
        e = event()
        links = C.link_lines(e, "threads")
        calls = []

        def post(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id"):
                raise RuntimeError("timeout")
            return {"id": f"id{len(calls)}"}

        def get(url, timeout=60):
            if "/replies" in url:
                raise RuntimeError("down")
            return {"id": "u"}

        C.LINK_FAILURES.clear()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), mock.patch.object(C, "_get", side_effect=get), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C.time, "sleep"), \
                mock.patch("threads_series.has_room", return_value=True), mock.patch("sys.stdout"):
            C.threads_image("https://x/card.jpg", "Head", links)
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 1, "a second reply could double the first")
        self.assertEqual(len(C.LINK_FAILURES), 1, "and the missing link is flagged for the sweeper")
        C.LINK_FAILURES.clear()

    def test_a_failed_publish_publishes_the_same_container_again_after_the_wait(self):
        e = event()
        links = C.link_lines(e, "threads")
        calls, waits = [], []

        def post(url, fields, timeout=60):
            calls.append((url.rsplit("/", 1)[-1], dict(fields)))
            if url.endswith("threads_publish") and fields.get("creation_id") == "reply-1" and sum(
                    1 for u, f in calls if f.get("creation_id") == "reply-1") < 2:
                raise RuntimeError("HTTP 400 (#24) The requested resource does not exist")   # not ready yet
            return {"id": "reply-1" if "reply_to_id" in fields else f"id{len(calls)}"}

        def get(url, timeout=60):
            return {"data": []} if "/replies" in url else {"id": "u"}

        C.LINK_FAILURES.clear()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), mock.patch.object(C, "_get", side_effect=get), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C.time, "sleep", side_effect=waits.append), \
                mock.patch("threads_series.has_room", return_value=True):
            C.threads_image("https://x/card.jpg", "Head", links)
        self.assertEqual(C.LINK_FAILURES, [])
        self.assertEqual(1, len([f for _u, f in calls if f.get("reply_to_id")]), "one container for the reply")
        self.assertEqual(2, len([f for _u, f in calls if f.get("creation_id") == "reply-1"]), "published again")
        self.assertIn(C.REPLY_WAIT, waits)

    def test_an_existing_reply_with_another_campaign_token_still_counts(self):
        e = event()
        links = C.link_lines(e, "threads")
        retargeted = [line.replace("ct=", "ct=other_") for line in links]
        with mock.patch.object(C, "_get", return_value={"data": [{"text": "\n".join(retargeted), "is_reply_owned_by_me": True}]}):
            self.assertTrue(C.own_link_reply_exists("api", "t", "m", links))


class CountdownOnceADayTest(unittest.TestCase):
    """2026-11-19: a second run the same day (rerun, manual dispatch) never posts the card twice; the posted
    receipt decides, channel by channel."""

    DAY = "2026-11-20"

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.receipt = self.tmp / "posted.json"
        self.card = self.tmp / "card.jpg"
        e = event()
        self.card.with_suffix(".json").write_text(
            '{"event": "%s", "locale": "%s", "caption": "c"}' % (e["id"], e["locale"]), encoding="utf-8")

    def run_post(self, results, extra=()):
        """main() post with each channel's poster returning results[channel]; the channels called, in order."""
        import io
        from contextlib import redirect_stdout
        calls = []

        def poster(name):
            def fn(*_a):
                calls.append(name)
                r = results.get(name)
                if isinstance(r, Exception):
                    raise r
                return r
            return fn
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["c", "post", "--card", str(self.card), "--date", self.DAY,
                                             "--receipt", str(self.receipt), *extra]), \
                mock.patch.object(C.CR, "paused_notice", return_value=False), \
                mock.patch.object(C, "qa_problems", return_value=[]), \
                mock.patch.object(C, "post_telegram", side_effect=poster("telegram")), \
                mock.patch.object(C, "post_threads", side_effect=poster("threads")), \
                mock.patch.object(C, "post_instagram", side_effect=poster("instagram")), \
                redirect_stdout(out):
            self.assertEqual(0, C.main())
        return calls, out.getvalue()

    def test_a_second_run_the_same_day_posts_nothing_and_says_why(self):
        calls, _ = self.run_post({"telegram": "11", "threads": "t1", "instagram": "i1"})
        self.assertEqual(["telegram", "threads", "instagram"], calls)
        calls, out = self.run_post({"telegram": "12", "threads": "t2", "instagram": "i2"})
        self.assertEqual([], calls)
        for ch in ("telegram", "threads", "instagram"):
            self.assertIn(f"countdown: {ch} skipped, already posted today ({self.DAY}", out)
        import json
        self.assertEqual({"telegram": "11", "threads": "t1", "instagram": "i1"},
                         json.loads(self.receipt.read_text())["channels"])

    def test_a_rerun_fills_only_the_channels_that_missed(self):
        calls, _ = self.run_post({"telegram": "11", "threads": None, "instagram": RuntimeError("HTTP 500")})
        self.assertEqual(["telegram", "threads", "instagram"], calls)
        calls, _ = self.run_post({"threads": "t1", "instagram": "i1"})
        self.assertEqual(["threads", "instagram"], calls)

    def test_yesterdays_receipt_does_not_hold_today(self):
        import json
        self.receipt.write_text(json.dumps({"date": "2026-11-19", "event": "x",
                                            "channels": {"telegram": "1", "threads": "2", "instagram": "3"}}))
        calls, _ = self.run_post({"telegram": "11", "threads": "t1", "instagram": "i1"})
        self.assertEqual(["telegram", "threads", "instagram"], calls)
        self.assertEqual(self.DAY, json.loads(self.receipt.read_text())["date"])

    def test_an_unreadable_receipt_is_empty_not_a_crash(self):
        self.receipt.write_text("{not json")
        calls, _ = self.run_post({"telegram": "11"}, extra=("--only", "telegram"))
        self.assertEqual(["telegram"], calls)

    def test_done_only_when_every_wanted_channel_is_in_todays_receipt(self):
        import datetime as dt
        import io
        from contextlib import redirect_stdout
        day = dt.date.fromisoformat(self.DAY)
        with redirect_stdout(io.StringIO()):
            self.assertFalse(C.already_done(str(self.receipt), day))  # no receipt yet
            C.record_receipt(str(self.receipt), day, {"event": "e"}, "telegram", "11")
            self.assertFalse(C.already_done(str(self.receipt), day))
            self.assertTrue(C.already_done(str(self.receipt), day, only="telegram"))
            C.record_receipt(str(self.receipt), day, {"event": "e"}, "threads", "t1")
            C.record_receipt(str(self.receipt), day, {"event": "e"}, "instagram", "i1")
            self.assertTrue(C.already_done(str(self.receipt), day))
            self.assertFalse(C.already_done(str(self.receipt), day + dt.timedelta(days=1)))

    def test_without_a_receipt_nothing_changes(self):
        import io
        from contextlib import redirect_stdout
        calls = []
        e = event()
        with mock.patch.object(sys, "argv", ["c", "post", "--card", "x.jpg"]), \
                mock.patch.object(C.Path, "read_text", return_value='{"event": "%s", "locale": "%s", "caption": "c"}' % (e["id"], e["locale"])), \
                mock.patch.object(C.CR, "paused_notice", return_value=False), \
                mock.patch.object(C, "qa_problems", return_value=[]), \
                mock.patch.object(C, "post_telegram", side_effect=lambda *a: calls.append("telegram") or "1"), \
                mock.patch.object(C, "post_threads", side_effect=lambda *a: calls.append("threads") or "2"), \
                mock.patch.object(C, "post_instagram", side_effect=lambda *a: calls.append("instagram") or "3"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(0, C.main())
        self.assertEqual(["telegram", "threads", "instagram"], calls)

    def test_post_telegram_counts_only_a_message_that_went_out(self):
        e = event()
        with mock.patch.object(C, "send_photo", return_value={"ok": True, "result": {"message_id": 77}}):
            self.assertEqual("77", C.post_telegram("x.jpg", meta(e), e))
        for bad in (None, {"ok": False}):
            with mock.patch.object(C, "send_photo", return_value=bad):
                self.assertIsNone(C.post_telegram("x.jpg", meta(e), e))

    def test_the_workflow_reads_and_keeps_the_receipt(self):
        wf = (Path(__file__).resolve().parents[1] / "workflows" / "countdown-daily.yml").read_text()
        self.assertIn("countdown_cards.py done --date", wf)
        self.assertIn('--receipt "$RUNNER_TEMP/posted.json"', wf)
        keep = wf.index("Keep today's posted receipt")
        self.assertLess(wf.index("countdown_cards.py post"), keep)
        self.assertNotIn("--force", wf[keep:], "the receipt push must never overwrite the branch")

    def test_a_failed_receipt_fetch_stops_the_run_unless_the_branch_is_not_there(self):
        wf = (Path(__file__).resolve().parents[1] / "workflows" / "countdown-daily.yml").read_text()
        due = wf[wf.index("id: due"):wf.index("- name: Draw the card")]
        self.assertNotIn("countdown-cards 2>/dev/null", due, "a network failure must not read as no receipt")
        self.assertIn("git ls-remote --exit-code origin countdown-cards", due)
        self.assertIn('if [ "$rc" != 2 ]', due)
        self.assertIn("exit 1", due)

    def test_the_receipt_push_retries_after_a_fetch(self):
        wf = (Path(__file__).resolve().parents[1] / "workflows" / "countdown-daily.yml").read_text()
        keep = wf[wf.index("Keep today's posted receipt"):]
        self.assertIn("for i in 1 2 3", keep)
        self.assertLess(keep.index("git fetch"), keep.index("git push"))
        self.assertIn("sleep $((i * 5))", keep)


if __name__ == "__main__":
    unittest.main()
