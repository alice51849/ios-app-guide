#!/usr/bin/env python3
"""The Threads account cap, shared by every Guide path that publishes a top-level Threads post.

Owner rule: "Threads 每天最多 3 則" for the whole @hourstag.app account. threads-autopilot posts to the
same account and holds the same cap (its cloud_post.py ACCOUNT_DAILY_CAP / _account_full), so the count
must cover every pipeline: Threads' own publishing limit (GET <user>/threads_publishing_limit,
quota_usage) counts every top-level post of the last 24 hours, whoever made it. Replies (the first-reply
download link, link_backfill.py) are not top-level posts and are never held here.

Call account_status() right before each top-level publish:
  ROOM     under the cap: post.
  FULL     at or over it: skip. A skip is not a failure: it prints the ⏸ line, never ::error::.
  UNKNOWN  the count could not be read: post nothing (a missing post is safer than a 4th) and say so
           with ::warning::.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = "https://graph.threads.net/v1.0"
ACCOUNT_DAILY_CAP = 3  # top-level Threads posts in any 24 hours, every pipeline on the account included

ROOM, FULL, UNKNOWN = "room", "full", "unknown"

# A slot that finds the account FULL is not done yet (2026-11-08..14: about 10 slots were skipped because the day
# before's post at the same slot was still inside Threads' rolling 24 hours, a few minutes short of falling out).
# Inside RETRY_GRACE after the slot's fire time the run ends green but leaves the slot open: it runs the step named
# OPEN_STEP, which social_slot_gate.py and threads_backfill.py read back, so the next clip-backup.yml run
# (threads_backfill.py) dispatches the slot again. Only when no backup run falls inside the grace any more is the
# slot recorded as a cap skip, with a receipt (.github/growth/threads-cap-skips.json). Every retry still goes
# through account_status(): the cap itself is never loosened.
RETRY, SKIP = "retry", "skip"
RETRY_GRACE = dt.timedelta(hours=2)
OPEN_STEP = "Threads cap full: slot left open for a retry"
SLOT_FIRE_MINUTE = {1: 40, 3: 0, 13: 0}  # threads-post.yml crons
# clip-backup.yml crons (UTC hour, minute): each one runs threads_backfill.py. test_threads_cap.py keeps them in sync.
BACKUP_TIMES = ((0, 47), (3, 47), (11, 47), (14, 47), (17, 47), (20, 47))
BACKUP_MARGIN = dt.timedelta(minutes=5)  # a backup this close sees the deferred run still running and skips it
SKIPS_FILE = Path(__file__).resolve().parents[1] / "growth" / "threads-cap-skips.json"
SKIPS_KEEP = 120
TW = dt.timezone(dt.timedelta(hours=8))


def _utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def next_backup(now):
    """First clip-backup.yml run at least BACKUP_MARGIN after now."""
    earliest = _utc(now) + BACKUP_MARGIN
    for days in (0, 1):
        day = earliest.date() + dt.timedelta(days=days)
        for hour, minute in BACKUP_TIMES:
            at = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=dt.timezone.utc)
            if at >= earliest:
                return at
    raise AssertionError("no backup time")  # pragma: no cover


def full_slot_action(slot, now):
    """RETRY or SKIP for a slot (its UTC hour start) that found the account FULL at ``now``.

    RETRY only while a backup run that fills this slot (same Taiwan day, threads_backfill.py) still comes before
    the grace ends; otherwise SKIP, so the skip is recorded once instead of the slot staying open forever."""
    slot, now = _utc(slot), _utc(now)
    deadline = slot + dt.timedelta(minutes=SLOT_FIRE_MINUTE.get(slot.hour, 0)) + RETRY_GRACE
    if now >= deadline:
        return SKIP
    backup = next_backup(now)
    if backup < deadline and backup.astimezone(TW).date() == slot.astimezone(TW).date():
        return RETRY
    return SKIP


def skip_receipt(slot, now, label="threads-post"):
    slot, now = _utc(slot), _utc(now)
    return {
        "slot": slot.isoformat(),
        "decided_at": now.replace(microsecond=0).isoformat(),
        "reason": "cap_full_after_grace",
        "cap": ACCOUNT_DAILY_CAP,
        "grace_minutes": int(RETRY_GRACE.total_seconds() // 60),
        "workflow": label,
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    }


def merge_skip(receipt_path, skips_path=SKIPS_FILE):
    """Fold one receipt into the skips file (one entry per slot, newest last, last SKIPS_KEEP kept)."""
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    try:
        rows = json.loads(Path(skips_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        rows = []
    rows = [row for row in rows if isinstance(row, dict) and row.get("slot") != receipt["slot"]] + [receipt]
    rows.sort(key=lambda row: row.get("slot", ""))
    Path(skips_path).write_text(json.dumps(rows[-SKIPS_KEEP:], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return rows[-SKIPS_KEEP:]


def full_slot(slot, now, receipt_path="", output_path=""):
    """The room check found the account FULL: leave the slot open (RETRY) or record a cap skip (SKIP)."""
    action = full_slot_action(slot, now)
    if action == RETRY:
        deadline = _utc(slot) + dt.timedelta(minutes=SLOT_FIRE_MINUTE.get(_utc(slot).hour, 0)) + RETRY_GRACE
        print(f"⏸ Threads 帳號已滿 {ACCOUNT_DAILY_CAP} 則：這格（{_utc(slot).isoformat()}）不記完成，"
              f"{next_backup(now).strftime('%H:%M')} 世界時的補發再試（寬限到 {deadline.strftime('%H:%M')}）")
    else:
        receipt = skip_receipt(slot, now)
        if receipt_path:
            Path(receipt_path).write_text(json.dumps(receipt, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"::notice::Threads 帳號已滿 {ACCOUNT_DAILY_CAP} 則，寬限 2 小時內沒有空位：這格"
              f"（{_utc(slot).isoformat()}）記為滿額跳過")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as out:
            out.write(f"retry={'true' if action == RETRY else 'false'}\n")
            out.write(f"capskip={'true' if action == SKIP else 'false'}\n")
    return action


class QuotaUnknown(Exception):
    """The publishing-limit count could not be read (the message never carries the token or the URL)."""


def _note(error):
    status = getattr(error, "code", None) or getattr(error, "status", None)
    return f"{error.__class__.__name__}{f' {status}' if status else ''}"


def quota_usage(token, user_id=None, opener=None):
    """Top-level posts the account published in the last 24 hours, by Threads' own count.
    Raises QuotaUnknown when the call fails or answers something that is not a count."""
    query = urllib.parse.urlencode({"fields": "quota_usage,config", "access_token": token})
    url = f"{GRAPH}/{user_id or 'me'}/threads_publishing_limit?{query}"
    try:
        with (opener or urllib.request.urlopen)(url, timeout=30) as response:
            row = json.loads(response.read())["data"][0]
        used = int(row["quota_usage"])
        total = int(row["config"]["quota_total"])
    except Exception as error:
        raise QuotaUnknown(_note(error)) from None
    if used < 0 or total <= 0 or used > total:
        raise QuotaUnknown(f"invalid publishing limit {used}/{total}")
    return used


def account_status(token, user_id=None, *, label="Threads", opener=None):
    """ROOM, FULL or UNKNOWN for one top-level post about to go out (see the module docstring)."""
    try:
        used = quota_usage(token, user_id, opener)
    except QuotaUnknown as error:
        print(f"::warning::{label}: 讀不到 Threads 帳號近 24 小時的發文數（{error}），"
              f"為免超過每天 {ACCOUNT_DAILY_CAP} 則上限，本次不發")
        return UNKNOWN
    if used >= ACCOUNT_DAILY_CAP:
        print(f"⏸ Threads 帳號近 24 小時已發 {used} 則（上限 {ACCOUNT_DAILY_CAP}），本次不發（{label}）")
        return FULL
    print(f"{label}: Threads 帳號近 24 小時已發 {used} 則（上限 {ACCOUNT_DAILY_CAP}），可以發")
    return ROOM


def main(argv=None):
    parser = argparse.ArgumentParser(description="Threads cap: what a slot does when the account is full")
    sub = parser.add_subparsers(dest="command", required=True)
    full = sub.add_parser("full", help="the room check found the account full: retry later or record a skip")
    full.add_argument("--slot", required=True, help="UTC slot start (social_slot_gate.py slot output)")
    full.add_argument("--now", default="", help="tests only: the current UTC time")
    full.add_argument("--receipt", default="", help="where to write the skip receipt")
    merge = sub.add_parser("merge-skip", help="fold a skip receipt into .github/growth/threads-cap-skips.json")
    merge.add_argument("receipt")
    args = parser.parse_args(argv)
    if args.command == "full":
        now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
        full_slot(dt.datetime.fromisoformat(args.slot), now, args.receipt, os.environ.get("GITHUB_OUTPUT", ""))
        return 0
    merge_skip(args.receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
