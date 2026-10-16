#!/usr/bin/env python3
"""Dispatch threads-post.yml for a Threads slot GitHub dropped or is still holding.

GitHub delays scheduled runs by hours, or drops them (2026-10-15: the 13:00
UTC Threads run never came). clip-backup.yml runs this after the slots; for
each slot of the current Taiwan day that started at least GRACE ago and that
no threads-post.yml run has completed or is running, it starts
threads-post.yml with ``mode=post slot=<hour> date=<UTC date>``.

Nothing here posts. The dispatched run goes through the same slot gate
(social_slot_gate.py, so a late scheduled run of the same slot then skips)
and the same account cap (threads_series.py room: 3 top-level posts a Taiwan
day, threads-autopilot's posts on the account included). Only slots of the
current Taiwan day are filled, so a backfill never takes the next day's room.

    python3 threads_backfill.py            # dispatch the missing slots
    python3 threads_backfill.py --dry-run  # only print them
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

import social_slot_gate as gate


WORKFLOW = "threads-post.yml"
SLOTS = (1, 3, 13)
# Scheduled minute of each slot in threads-post.yml.
SCHEDULED_MINUTE = {1: 40, 3: 0, 13: 0}
GRACE = dt.timedelta(minutes=30)
TW = dt.timezone(dt.timedelta(hours=8))


def taiwan_day_slots(now):
    """UTC slot starts of the Taiwan day ``now`` falls in, with their fire time."""
    now = gate._utc(now)
    day = now.astimezone(TW).date()
    # Every slot (01-13 UTC) falls on the same calendar date in Taiwan.
    return [
        (
            dt.datetime(day.year, day.month, day.day, hour, tzinfo=dt.timezone.utc),
            dt.datetime(day.year, day.month, day.day, hour, SCHEDULED_MINUTE[hour], tzinfo=dt.timezone.utc),
        )
        for hour in SLOTS
    ]


def covered_slots(runs):
    """Slots a threads-post run already filled (success) or is filling now."""
    covered = set()
    for run in runs:
        if not isinstance(run, dict):
            continue
        status, conclusion = run.get("status"), run.get("conclusion")
        if status == "completed" and conclusion != "success":
            continue
        try:
            slot = gate.run_slot(run, SLOTS)
        except ValueError:
            continue
        if slot is not None:
            covered.add(slot)
    return covered


def missing_slots(runs, now):
    now = gate._utc(now)
    covered = covered_slots(runs)
    return [
        slot
        for slot, fires in taiwan_day_slots(now)
        if fires + GRACE <= now and slot not in covered
    ]


def dispatch(repository, token, slot, ref="main"):
    path = (
        f"/repos/{repository}/actions/workflows/"
        f"{urllib.parse.quote(WORKFLOW, safe='')}/dispatches"
    )
    body = json.dumps({
        "ref": ref,
        "inputs": {
            "mode": "post",
            "slot": str(slot.hour),
            "date": slot.date().isoformat(),
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{gate.API}{path}",
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status not in (200, 204):
            raise ValueError(f"dispatch returned HTTP {response.status}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    now = dt.datetime.now(dt.timezone.utc)
    runs = gate.fetch_runs(repository, WORKFLOW, token)
    missing = missing_slots(runs, now)
    if not missing:
        print("Threads backfill: every due slot of today (Taiwan) is filled or running")
        return 0
    for slot in missing:
        if args.dry_run:
            print(f"Threads backfill: would dispatch slot {slot.isoformat()}")
            continue
        dispatch(repository, token, slot)
        print(f"Threads backfill: dispatched {WORKFLOW} slot {slot.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
