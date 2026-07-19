#!/usr/bin/env python3
"""Prevent delayed and manual cloud runs from publishing the same UTC slot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
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


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("workflow run has no created_at timestamp")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def should_post(runs, current_run_id, slots, now):
    current_slot = slot_start(now, slots)
    for run in runs:
        if (
            not isinstance(run, dict)
            or str(run.get("id")) == str(current_run_id)
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
        ):
            continue
        if slot_start(parse_timestamp(run.get("created_at")), slots) == current_slot:
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--slots", required=True)
    args = parser.parse_args()
    slots = parse_slots(args.slots)
    now = dt.datetime.now(dt.timezone.utc)
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
    )
    write_output(os.environ.get("GITHUB_OUTPUT", ""), allowed, slot)
    print(
        f"cloud social slot {slot.isoformat()}: "
        f"{'publish' if allowed else 'already completed; skip'}"
    )


if __name__ == "__main__":
    main()
