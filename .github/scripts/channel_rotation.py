#!/usr/bin/env python3
"""Channel rotation holdout (switchback experiment): which posting channel sits out this UTC week.

The plan is registered once in 00_GrowthEngine (reports/holdout/channel_rotation_plan.json, digest-bound,
never edited) and copied byte for byte to .github/growth/channel_rotation_plan.json. From its first Monday
one channel per week does not post its main posts: threads, bluesky, telegram, instagram or youtube. The
guide site, reply scouting, download-link backfill replies and outreach are never paused.

The reading part is the same algorithm as 00_GrowthEngine reports/channel_rotation.py (_digest, load_plan,
off_channel, is_paused): days are UTC dates and a week is [start, end). A missing, unreadable or altered plan
pauses nothing (the experiment never blocks posting by accident).

    python3 channel_rotation.py status [--day YYYY-MM-DD]     # the channel off today (or "none")
    python3 channel_rotation.py check <channel>               # ::notice:: + paused=true|false to GITHUB_OUTPUT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCHEMA = "channel-rotation/v1"
PLAN_PATH = Path(__file__).resolve().parent.parent / "growth" / "channel_rotation_plan.json"
ROTATION_CHANNELS = ("threads", "bluesky", "telegram", "instagram", "youtube")


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                          .encode()).hexdigest()


def load_plan(path: Path = PLAN_PATH) -> dict:
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in plan.items() if k != "digest"}
    if plan.get("schema") != SCHEMA or plan.get("digest") != _digest(body):
        raise ValueError(f"{path}: rotation plan digest mismatch (the plan was changed after registration)")
    return plan


def off_channel(day: date, plan: dict) -> str | None:
    """The channel that does not post on `day` (UTC), or None outside the experiment."""
    d = day.isoformat()
    for w in plan["weeks"]:
        if w["start"] <= d < w["end"]:
            return w["off"]
    return None


def is_paused(channel: str, day: date, plan: dict | None = None) -> bool:
    """For publishers: True when `channel` sits out its registered week. A missing or altered plan pauses
    nothing (the experiment never blocks posting by accident)."""
    if plan is None:
        try:
            plan = load_plan()
        except (OSError, ValueError):
            return False
    return off_channel(day, plan) == channel


# ---------------------------------------------------------------- publisher helpers (fail-open)


def today_utc() -> date:
    import os as _o
    if _o.environ.get("CR_SIM_DAY"):
        return date.fromisoformat(_o.environ["CR_SIM_DAY"])
    return datetime.now(timezone.utc).date()


def paused_week(channel: str, day: date | None = None, plan: dict | None = None) -> dict | None:
    """The registered week in which `channel` is off on `day` (UTC, default today), else None.
    Any problem reading the plan answers None: posting goes on."""
    try:
        if plan is None:
            plan = load_plan()
        day = day or today_utc()
        if not is_paused(channel, day, plan):
            return None
        d = day.isoformat()
        return next(w for w in plan["weeks"] if w["start"] <= d < w["end"])
    except Exception:  # noqa: BLE001 - fail-open by design
        return None


def notice(channel: str, week: dict) -> str:
    return f"::notice::channel rotation holdout: {channel} paused {week['start']}..{week['end']}"


def paused_notice(channel: str, day: date | None = None, plan: dict | None = None) -> bool:
    """Call right before a main post goes to `channel`: True (and the ::notice:: printed) when the channel
    sits out this week, so the caller skips that channel only and stays green."""
    week = paused_week(channel, day, plan)
    if week is None:
        return False
    print(notice(channel, week), flush=True)
    return True


def paused_within(channel: str, now: datetime, hours: float, plan: dict | None = None) -> dict | None:
    """For watchdogs: the week `channel` was off on any UTC day touched by [now - hours, now], else None.
    A delivery-evidence window that reaches into an off week expects no post from that channel."""
    try:
        if plan is None:
            plan = load_plan()
        first = (now - timedelta(hours=hours)).astimezone(timezone.utc).date()
        last = now.astimezone(timezone.utc).date()
        day = first
        while day <= last:
            week = paused_week(channel, day, plan)
            if week is not None:
                return week
            day += timedelta(days=1)
    except Exception:  # noqa: BLE001 - fail-open: the watchdog judges as before
        return None
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status")
    st.add_argument("--day")
    ck = sub.add_parser("check")
    ck.add_argument("channel", choices=ROTATION_CHANNELS)
    args = ap.parse_args(argv)
    if args.cmd == "status":
        day = date.fromisoformat(args.day) if args.day else today_utc()
        try:
            print(off_channel(day, load_plan()) or "none")
        except (OSError, ValueError) as exc:
            print(f"::warning::channel rotation plan unreadable ({exc}); nothing is paused")
            print("none")
        return 0
    paused = paused_notice(args.channel)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"paused={'true' if paused else 'false'}\n")
    print(f"paused={'true' if paused else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
