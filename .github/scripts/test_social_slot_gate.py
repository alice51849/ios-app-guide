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
                "should_post=true\nslot=2026-07-19T15:00:00+00:00\n",
                path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
