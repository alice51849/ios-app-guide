#!/usr/bin/env python3
"""Tests for cloud social slot idempotency."""

import datetime as dt
from pathlib import Path
import tempfile
import unittest

import social_slot_gate as gate


UTC = dt.timezone.utc


class SocialSlotGateTests(unittest.TestCase):
    def test_slot_before_first_hour_uses_previous_day(self):
        slot = gate.slot_start(
            dt.datetime(2026, 7, 20, 0, 30, tzinfo=UTC),
            (3, 7, 14, 19),
        )
        self.assertEqual(
            dt.datetime(2026, 7, 19, 19, tzinfo=UTC),
            slot,
        )

    def test_successful_run_in_same_slot_blocks_duplicate(self):
        now = dt.datetime(2026, 7, 19, 15, 34, tzinfo=UTC)
        runs = [
            {
                "id": 100,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-07-19T15:05:00Z",
            }
        ]
        allowed, slot = gate.should_post(runs, "101", (1, 9, 15), now)
        self.assertFalse(allowed)
        self.assertEqual(dt.datetime(2026, 7, 19, 15, tzinfo=UTC), slot)

    def test_failed_other_slot_and_current_run_do_not_block(self):
        now = dt.datetime(2026, 7, 19, 15, 34, tzinfo=UTC)
        runs = [
            {
                "id": 100,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-07-19T10:00:00Z",
            },
            {
                "id": 101,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-07-19T15:30:00Z",
            },
            {
                "id": 102,
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-07-19T15:10:00Z",
            },
        ]
        allowed, _ = gate.should_post(runs, "101", (1, 9, 15), now)
        self.assertTrue(allowed)

    def test_output_is_valid_for_github_actions(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "output"
            gate.write_output(
                path,
                True,
                dt.datetime(2026, 7, 19, 15, tzinfo=UTC),
            )
            self.assertEqual(
                "should_post=true\nslot=2026-07-19T15:00:00+00:00\n"
                "hour=15\ndate=2026-07-19\n",
                path.read_text(encoding="utf-8"),
            )



THREADS = (1, 3, 13)


def run(run_id, created, title, event="schedule", conclusion="success"):
    return {
        "id": run_id,
        "event": event,
        "status": "completed",
        "conclusion": conclusion,
        "created_at": created,
        "display_title": title,
    }


class ScheduledSlotTests(unittest.TestCase):
    """GitHub started the 01:40 run at 06:26 (run 38703838001's day)."""

    def test_delayed_run_keeps_the_slot_it_was_scheduled_for(self):
        now = dt.datetime(2026, 10, 16, 6, 26, tzinfo=UTC)
        self.assertEqual(
            dt.datetime(2026, 10, 16, 1, tzinfo=UTC),
            gate.resolve_slot(THREADS, now, schedule="40 1 * * *"),
        )

    def test_run_just_after_midnight_belongs_to_yesterdays_evening_slot(self):
        now = dt.datetime(2026, 10, 16, 0, 20, tzinfo=UTC)
        self.assertEqual(
            dt.datetime(2026, 10, 15, 13, tzinfo=UTC),
            gate.resolve_slot(THREADS, now, schedule="0 13 * * *"),
        )

    def test_delayed_slot_one_run_no_longer_takes_the_picture_slot(self):
        late_clip = run(1, "2026-10-16T06:26:00Z", "Threads posts · cron 40 1 * * *")
        now = dt.datetime(2026, 10, 16, 6, 40, tzinfo=UTC)
        slot = gate.resolve_slot(THREADS, now, schedule="0 3 * * *")
        allowed, current = gate.should_post([late_clip], "2", THREADS, now, slot)
        self.assertTrue(allowed)
        self.assertEqual(dt.datetime(2026, 10, 16, 3, tzinfo=UTC), current)

    def test_same_scheduled_slot_still_blocks_a_second_run(self):
        first = run(1, "2026-10-16T06:26:00Z", "Threads posts · cron 40 1 * * *")
        now = dt.datetime(2026, 10, 16, 7, 0, tzinfo=UTC)
        slot = gate.resolve_slot(THREADS, now, schedule="40 1 * * *")
        allowed, _ = gate.should_post([first], "2", THREADS, now, slot)
        self.assertFalse(allowed)

    def test_schedule_outside_the_slots_is_refused(self):
        with self.assertRaises(ValueError):
            gate.resolve_slot(THREADS, dt.datetime(2026, 10, 16, 9, tzinfo=UTC), schedule="0 9 * * *")
        with self.assertRaises(ValueError):
            gate.resolve_slot(THREADS, dt.datetime(2026, 10, 16, 9, tzinfo=UTC), schedule="*/5 * * * *")

    def test_no_flags_keeps_the_actual_run_time_behaviour(self):
        now = dt.datetime(2026, 10, 16, 6, 26, tzinfo=UTC)
        self.assertEqual(
            dt.datetime(2026, 10, 16, 3, tzinfo=UTC),
            gate.resolve_slot(THREADS, now),
        )


class DispatchBackfillTests(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 16, 8, 0, tzinfo=UTC)

    def test_dispatch_fills_a_missed_slot_of_an_earlier_day(self):
        slot = gate.resolve_slot(THREADS, self.NOW, slot_hour="13", slot_date="2026-10-15")
        self.assertEqual(dt.datetime(2026, 10, 15, 13, tzinfo=UTC), slot)
        allowed, _ = gate.should_post([], "9", THREADS, self.NOW, slot)
        self.assertTrue(allowed)

    def test_dispatch_without_date_takes_the_latest_occurrence(self):
        self.assertEqual(
            dt.datetime(2026, 10, 15, 13, tzinfo=UTC),
            gate.resolve_slot(THREADS, self.NOW, slot_hour="13"),
        )
        self.assertEqual(
            dt.datetime(2026, 10, 16, 3, tzinfo=UTC),
            gate.resolve_slot(THREADS, self.NOW, slot_hour="3"),
        )

    def test_dispatch_cannot_post_a_future_or_unknown_slot(self):
        with self.assertRaises(ValueError):
            gate.resolve_slot(THREADS, self.NOW, slot_hour="13", slot_date="2026-10-16")
        with self.assertRaises(ValueError):
            gate.resolve_slot(THREADS, self.NOW, slot_hour="9")
        with self.assertRaises(ValueError):
            gate.resolve_slot(THREADS, self.NOW, slot_date="2026-10-15")

    def test_dispatch_is_blocked_once_the_scheduled_run_posted(self):
        done = run(1, "2026-10-15T13:02:00Z", "Threads posts · cron 0 13 * * *")
        slot = gate.resolve_slot(THREADS, self.NOW, slot_hour="13", slot_date="2026-10-15")
        allowed, _ = gate.should_post([done], "9", THREADS, self.NOW, slot)
        self.assertFalse(allowed)

    def test_late_scheduled_run_is_blocked_after_a_backfill_posted(self):
        backfill = run(
            1, "2026-10-16T03:48:00Z", "Threads posts · post slot 1 2026-10-16",
            event="workflow_dispatch",
        )
        now = dt.datetime(2026, 10, 16, 6, 26, tzinfo=UTC)
        slot = gate.resolve_slot(THREADS, now, schedule="40 1 * * *")
        allowed, _ = gate.should_post([backfill], "2", THREADS, now, slot)
        self.assertFalse(allowed)

    def test_dispatch_without_date_is_matched_by_its_creation_time(self):
        backfill = run(
            1, "2026-10-16T04:00:00Z", "Threads posts · post slot 3 ",
            event="workflow_dispatch",
        )
        self.assertEqual(
            dt.datetime(2026, 10, 16, 3, tzinfo=UTC),
            gate.run_slot(backfill, THREADS),
        )

    def test_whoami_and_failed_runs_never_block(self):
        runs = [
            run(1, "2026-10-16T03:10:00Z", "Threads posts · whoami slot 3 ", event="workflow_dispatch"),
            run(2, "2026-10-16T03:20:00Z", "Threads posts · cron 0 3 * * *", conclusion="failure"),
        ]
        now = dt.datetime(2026, 10, 16, 3, 30, tzinfo=UTC)
        slot = gate.resolve_slot(THREADS, now, schedule="0 3 * * *")
        allowed, _ = gate.should_post(runs, "3", THREADS, now, slot)
        self.assertTrue(allowed)

    def test_runs_without_a_marker_fall_back_to_created_at(self):
        legacy = run(1, "2026-10-16T06:26:00Z", "Threads posts")
        self.assertEqual(
            dt.datetime(2026, 10, 16, 3, tzinfo=UTC),
            gate.run_slot(legacy, THREADS),
        )


if __name__ == "__main__":
    unittest.main()
