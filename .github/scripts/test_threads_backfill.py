#!/usr/bin/env python3
"""Tests for the Threads slot backfill (clip-backup.yml -> threads-post.yml)."""

import datetime as dt
import json
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
