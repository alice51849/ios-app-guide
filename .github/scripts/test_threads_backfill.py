#!/usr/bin/env python3
"""Tests for the Threads slot backfill (clip-backup.yml -> threads-post.yml)."""

import datetime as dt
import io
import json
import os
import unittest
from unittest import mock

import threads_backfill as B


UTC = dt.timezone.utc


def run(created, title, status="completed", conclusion="success", event="schedule"):
    return {
        "id": created,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "display_title": title,
    }


class MissingSlotsTests(unittest.TestCase):
    def test_dropped_evening_slot_is_dispatched_before_taiwan_midnight(self):
        # 2026-10-15: the 13:00 run never came; the 14:47 backup fills it.
        runs = [
            run("2026-10-15T01:41:00Z", "Threads posts · cron 40 1 * * *"),
            run("2026-10-15T03:01:00Z", "Threads posts · cron 0 3 * * *"),
        ]
        now = dt.datetime(2026, 10, 15, 14, 50, tzinfo=UTC)
        self.assertEqual(
            [dt.datetime(2026, 10, 15, 13, tzinfo=UTC)],
            B.missing_slots(runs, now),
        )

    def test_after_taiwan_midnight_yesterdays_slots_are_never_refilled(self):
        now = dt.datetime(2026, 10, 15, 17, 50, tzinfo=UTC)  # 01:50 Taiwan, 10/16
        self.assertEqual([], B.missing_slots([], now))

    def test_slots_not_yet_due_or_inside_the_grace_are_left_to_the_schedule(self):
        now = dt.datetime(2026, 10, 16, 3, 20, tzinfo=UTC)
        self.assertEqual(
            [dt.datetime(2026, 10, 16, 1, tzinfo=UTC)],
            B.missing_slots([], now),
        )

    def test_running_or_queued_runs_cover_their_slot(self):
        runs = [
            run("2026-10-16T01:40:00Z", "Threads posts · cron 40 1 * * *", status="in_progress", conclusion=None),
            run("2026-10-16T03:00:00Z", "Threads posts · cron 0 3 * * *", status="queued", conclusion=None),
        ]
        now = dt.datetime(2026, 10, 16, 3, 47, tzinfo=UTC)
        self.assertEqual([], B.missing_slots(runs, now))

    def test_failed_or_cancelled_runs_and_whoami_do_not_cover(self):
        runs = [
            run("2026-10-16T01:40:00Z", "Threads posts · cron 40 1 * * *", conclusion="failure"),
            run("2026-10-16T03:10:00Z", "Threads posts · post slot 3 2026-10-16",
                conclusion="cancelled", event="workflow_dispatch"),
            run("2026-10-16T03:20:00Z", "Threads posts · whoami slot 1 ", event="workflow_dispatch"),
        ]
        now = dt.datetime(2026, 10, 16, 3, 47, tzinfo=UTC)
        self.assertEqual(
            [dt.datetime(2026, 10, 16, 1, tzinfo=UTC), dt.datetime(2026, 10, 16, 3, tzinfo=UTC)],
            B.missing_slots(runs, now),
        )

    def test_delayed_run_fills_its_own_slot_not_the_next(self):
        # 10/16: the 01:40 run started at 06:26. It covers slot 1 only.
        runs = [run("2026-10-16T06:26:00Z", "Threads posts · cron 40 1 * * *")]
        now = dt.datetime(2026, 10, 16, 6, 40, tzinfo=UTC)
        self.assertEqual(
            [dt.datetime(2026, 10, 16, 3, tzinfo=UTC)],
            B.missing_slots(runs, now),
        )


class DispatchTests(unittest.TestCase):
    def test_dispatch_asks_threads_post_for_the_slot_and_date(self):
        seen = {}

        class Response:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=30):
            seen["url"] = request.full_url
            seen["method"] = request.get_method()
            seen["body"] = json.loads(request.data)
            return Response()

        with mock.patch.object(B.urllib.request, "urlopen", fake_urlopen):
            B.dispatch("o/r", "t", dt.datetime(2026, 10, 15, 13, tzinfo=UTC))
        self.assertEqual("POST", seen["method"])
        self.assertTrue(seen["url"].endswith("/repos/o/r/actions/workflows/threads-post.yml/dispatches"))
        self.assertEqual(
            {"ref": "main", "inputs": {"mode": "post", "slot": "13", "date": "2026-10-15"}},
            seen["body"],
        )

    def test_dry_run_dispatches_nothing(self):
        with mock.patch.object(B.gate, "fetch_runs", return_value=[]), \
                mock.patch.object(B, "dispatch") as dispatch, \
                mock.patch.dict("os.environ", {"GITHUB_REPOSITORY": "o/r", "GITHUB_TOKEN": "t"}):
            self.assertEqual(0, B.main(["--dry-run"]))
        dispatch.assert_not_called()



class LinkReplyRerunTests(unittest.TestCase):
    """threads_post.py ends the step red when a post's download-link reply cannot be posted. A failed run
    does not cover its slot, so this backfill dispatches the slot again: the rerun must add the missing
    reply under the post that is already up, never post the same text a second time."""

    MOCHI = "6785004775"

    def test_a_red_slot_is_dispatched_again(self):
        runs = [run("2026-10-16T03:00:00Z", "Threads posts · cron 0 3 * * *", conclusion="failure")]
        now = dt.datetime(2026, 10, 16, 3, 47, tzinfo=UTC)
        self.assertIn(dt.datetime(2026, 10, 16, 3, tzinfo=UTC), B.missing_slots(runs, now))

    def test_the_rerun_only_adds_the_reply_to_the_post_of_that_slot_day(self):
        import threads_post
        queued = {"date": "2026-10-16", "app": "mochi", "app_id": self.MOCHI, "ct": "bm_mochi_us_th",
                  "task": "t", "text": "Pain line without any URL."}
        env = {"THREADS_TOKEN": "tok", "THREADS_USER_ID": "uid", "THREADS_SLOT": "2026-10-16T03:00:00+00:00"}
        find = mock.Mock(return_value="m-existing")
        look = mock.Mock(return_value=None)   # the look for an earlier link reply worked: there is none yet
        with (
            mock.patch.dict(os.environ, env),
            mock.patch("urllib.request.urlopen", side_effect=OSError("offline")),
            mock.patch("sys.stdout", new_callable=io.StringIO),
            mock.patch("sys.stderr", new_callable=io.StringIO),
            mock.patch.object(threads_post, "queued_today", return_value=queued) as today,
            mock.patch.object(threads_post, "find_own_post", find),
            mock.patch.object(threads_post, "find_own_link_reply", look),
            mock.patch.object(threads_post, "publish_post", return_value="r1") as posted,
        ):
            self.assertEqual(0, threads_post.main())
        self.assertEqual(dt.date(2026, 10, 16), today.call_args.args[0])
        self.assertEqual(dt.date(2026, 10, 16), find.call_args.args[2])  # looked for in the slot's Taiwan day
        self.assertEqual("m-existing", look.call_args.args[1])           # and for a reply under that post
        posted.assert_called_once()
        self.assertEqual("m-existing", posted.call_args.kwargs["reply_to"])
        self.assertIn("apps.apple.com/app/id" + self.MOCHI, posted.call_args.args[2])

    def test_the_rerun_posts_nothing_when_the_reply_is_already_up(self):
        import threads_post
        queued = {"date": "2026-10-16", "app": "mochi", "app_id": self.MOCHI, "ct": "bm_mochi_us_th",
                  "task": "t", "text": "Pain line without any URL."}
        env = {"THREADS_TOKEN": "tok", "THREADS_USER_ID": "uid", "THREADS_SLOT": "2026-10-16T03:00:00+00:00"}
        with (
            mock.patch.dict(os.environ, env),
            mock.patch("urllib.request.urlopen", side_effect=OSError("offline")),
            mock.patch("sys.stdout", new_callable=io.StringIO),
            mock.patch("sys.stderr", new_callable=io.StringIO),
            mock.patch.object(threads_post, "queued_today", return_value=queued),
            mock.patch.object(threads_post, "find_own_post", return_value="m-existing"),
            mock.patch.object(threads_post, "find_own_link_reply", return_value="r-existing"),
            mock.patch.object(threads_post, "publish_post") as posted,
        ):
            self.assertEqual(0, threads_post.main())   # green: post and reply are both up
        posted.assert_not_called()


class PicturePostSlotTests(unittest.TestCase):
    def test_delayed_picture_post_keeps_its_slot_audience_and_day(self):
        import threads_post
        slot = threads_post.slot_time("2026-10-16T03:00:00+00:00")
        self.assertEqual(dt.datetime(2026, 10, 16, 3, tzinfo=UTC), slot)
        self.assertIsNone(threads_post.slot_time(""))
        # 03:00 UTC is the Asia audience even when GitHub runs it at 08:00.
        self.assertEqual("asia", threads_post._zone(slot.hour))
        self.assertEqual("eu_me2", threads_post._zone(8))
        self.assertEqual(dt.date(2026, 10, 16), slot.astimezone(threads_post.TW).date())


if __name__ == "__main__":
    unittest.main()
