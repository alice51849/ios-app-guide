#!/usr/bin/env python3
"""Prevent delayed and manual cloud runs from publishing the same UTC slot.

Without slot flags the slot is the latest slot hour at or before the actual
run time (the original behaviour, still used by Telegram, Reels and the
utility posts).

A workflow can instead name its slot: ``--schedule "$SCHEDULE"`` (the cron
of ``github.event.schedule``) keeps a run GitHub delayed by hours in the slot
it was scheduled for, and ``--slot-hour``/``--slot-date`` let a
workflow_dispatch run fill a missed slot. Such a workflow records its slot in
its ``run-name`` (``... cron 40 1 * * *`` or ``... post slot 13 2026-10-15``)
so later runs can tell which slot an earlier run used; a run-name marked with
any other dispatch mode (``whoami slot ...``) never blocks a slot. Runs from
before the run-name markers fall back to their created_at time.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

from social_post_common import request_json


API = "https://api.github.com"


def parse_slots(value):
    try:
        slots = tuple(sorted({int(part) for part in value.split(",")}))
    except ValueError as error:
        raise ValueError("slots must be comma-separated UTC hours") from error
    if not slots or any(hour < 0 or hour > 23 for hour in slots):
        raise ValueError("slots must contain UTC hours from 0 through 23")
    return slots


def slot_start(now, slots):
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)
    candidates = [
        now.replace(hour=hour, minute=0, second=0, microsecond=0)
        for hour in slots
        if hour <= now.hour
    ]
    if candidates:
        return candidates[-1]
    yesterday = now - dt.timedelta(days=1)
    return yesterday.replace(
        hour=slots[-1],
        minute=0,
        second=0,
        microsecond=0,
    )


CRON = re.compile(r"^\s*(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*\s*$")
TITLE_CRON = re.compile(r"\bcron (\d{1,2}) (\d{1,2}) \* \* \*")
TITLE_DISPATCH = re.compile(
    r"\b([a-z]+) slot (\d{1,2})?(?: (\d{4}-\d{2}-\d{2}))?\s*$"
)


def parse_schedule(value):
    """(minute, hour) of a daily cron such as ``40 1 * * *``."""
    match = CRON.match(value or "")
    if not match:
        raise ValueError(f"schedule must be a daily 'M H * * *' cron, got {value!r}")
    minute, hour = int(match.group(1)), int(match.group(2))
    if minute > 59 or hour > 23:
        raise ValueError(f"schedule out of range: {value!r}")
    return minute, hour


def _utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def latest_occurrence(now, hour, minute=0):
    """Start of the UTC hour slot whose daily time hour:minute last passed."""
    now = _utc(now)
    fired = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if fired > now:
        fired -= dt.timedelta(days=1)
    return fired.replace(minute=0)


def scheduled_slot(schedule, slots, now):
    """Slot a scheduled run belongs to, however late GitHub started it."""
    minute, hour = parse_schedule(schedule)
    if hour not in slots:
        raise ValueError(f"schedule {schedule!r} is not one of the slots {slots}")
    return latest_occurrence(now, hour, minute)


def requested_slot(hour, date, slots, now):
    """Slot a workflow_dispatch backfill asks for (date defaults to the latest)."""
    try:
        hour = int(hour)
    except (TypeError, ValueError) as error:
        raise ValueError(f"slot hour must be one of {slots}, got {hour!r}") from error
    if hour not in slots:
        raise ValueError(f"slot hour must be one of {slots}, got {hour}")
    if not date:
        return latest_occurrence(now, hour)
    day = dt.date.fromisoformat(date)
    slot = dt.datetime(day.year, day.month, day.day, hour, tzinfo=dt.timezone.utc)
    if slot > _utc(now):
        raise ValueError(f"slot {slot.isoformat()} has not started yet")
    return slot


def resolve_slot(slots, now, schedule="", slot_hour="", slot_date=""):
    if schedule:
        return scheduled_slot(schedule, slots, now)
    if slot_hour not in ("", None):
        return requested_slot(slot_hour, slot_date, slots, now)
    if slot_date:
        raise ValueError("--slot-date needs --slot-hour")
    return slot_start(now, slots)


def run_slot(run, slots):
    """Slot an earlier run used, or None when it never claims a slot."""
    created = parse_timestamp(run.get("created_at"))
    title = run.get("display_title") or run.get("name") or ""
    if not isinstance(title, str):
        title = ""
    match = TITLE_CRON.search(title)
    if match:
        minute, hour = int(match.group(1)), int(match.group(2))
        if hour in slots and minute <= 59:
            return latest_occurrence(created, hour, minute)
    match = TITLE_DISPATCH.search(title)
    if match:
        if match.group(1) != "post":
            return None  # e.g. whoami: never posts
        try:
            return requested_slot(match.group(2), match.group(3), slots, created)
        except ValueError:
            return None  # a dispatch the gate refused never posted
    return slot_start(created, slots)


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("workflow run has no created_at timestamp")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def should_post(runs, current_run_id, slots, now, current_slot=None):
    if current_slot is None:
        current_slot = slot_start(now, slots)
    for run in runs:
        if (
            not isinstance(run, dict)
            or str(run.get("id")) == str(current_run_id)
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
        ):
            continue
        if run_slot(run, slots) == current_slot:
            return False, current_slot
    return True, current_slot


def fetch_runs(repository, workflow, token):
    if (
        not repository
        or "/" not in repository
        or not workflow
        or not token
    ):
        raise ValueError("GitHub repository, workflow, and token are required")
    path = (
        f"/repos/{repository}/actions/workflows/"
        f"{urllib.parse.quote(workflow, safe='')}/runs?per_page=100"
    )
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    payload = request_json(
        request,
        label="GitHub social slot gate",
        timeout=30,
    )
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list):
        raise ValueError("GitHub social slot gate returned no workflow_runs")
    return runs


def write_output(path, allowed, slot):
    if not path:
        raise ValueError("GITHUB_OUTPUT is required")
    with Path(path).open("a", encoding="utf-8") as output:
        output.write(f"should_post={'true' if allowed else 'false'}\n")
        output.write(f"slot={slot.isoformat()}\n")
        output.write(f"hour={slot.hour}\n")
        output.write(f"date={slot.date().isoformat()}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--slots", required=True)
    parser.add_argument(
        "--schedule",
        default="",
        help="github.event.schedule: the slot is the one this cron was for",
    )
    parser.add_argument(
        "--slot-hour",
        default="",
        help="workflow_dispatch backfill: UTC slot hour to fill",
    )
    parser.add_argument(
        "--slot-date",
        default="",
        help="workflow_dispatch backfill: UTC date YYYY-MM-DD (default latest)",
    )
    args = parser.parse_args()
    slots = parse_slots(args.slots)
    now = dt.datetime.now(dt.timezone.utc)
    current = resolve_slot(
        slots, now, args.schedule.strip(), args.slot_hour.strip(),
        args.slot_date.strip(),
    )
    runs = fetch_runs(
        os.environ.get("GITHUB_REPOSITORY", ""),
        args.workflow,
        os.environ.get("GITHUB_TOKEN", ""),
    )
    allowed, slot = should_post(
        runs,
        os.environ.get("GITHUB_RUN_ID", ""),
        slots,
        now,
        current,
    )
    write_output(os.environ.get("GITHUB_OUTPUT", ""), allowed, slot)
    print(
        f"cloud social slot {slot.isoformat()}: "
        f"{'publish' if allowed else 'already completed; skip'}"
    )


if __name__ == "__main__":
    main()
