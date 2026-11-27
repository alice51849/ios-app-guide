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
# After its grace (slot_deadline) a slot that an earlier green run left open for a retry never posts, even with
# room (2.7 review 2026-11-27): a late retry (a dropped 04:47 backup, then the 11:47 backup, the watchdog or a
# delayed schedule) would hold the account's 3rd share until the same time tomorrow and push the 13:00 evening
# slot into a cap skip. threads-post.yml checks it after the room check (threads_cap.py within, only when
# social_slot_gate.py says retried=true) and records a skip receipt instead; threads_backfill.py does not dispatch
# a left-open slot again once its grace is over. A slot no run ever started still posts late with room, as before
# (on a day the Mac dispatcher is down a late GitHub schedule can be the account's only post).
PAST_GRACE_EXIT = 3
RETRY_GRACE = dt.timedelta(hours=2)
# Per-slot grace overrides (UTC slot hour -> grace). 2026-11-27 (also 11-20): the 03:00 slot found the account full
# because the day before's post went out at 04:05:07; the 03:47 backup's run checked at 04:01, 3.5 minutes short, and
# with the grace ending at 05:00 the next backup (11:47) was past it, so the slot was a cap skip. 03:00 gets 3 hours
# (to 06:00) and a 04:47 backup (BACKUP_TIMES) that falls inside it. Every other slot keeps RETRY_GRACE.
SLOT_RETRY_GRACE = {3: dt.timedelta(hours=3)}
OPEN_STEP = "Threads cap full: slot left open for a retry"
SLOT_FIRE_MINUTE = {1: 40, 3: 0, 13: 0}  # threads-post.yml crons
# Per-slot shares (coordinator ruling 2026-11-27 00:5x Taipei, option 乙): the 3-in-24-hours cap is unchanged,
# but a slot's retry grace must not run into the next slot's share. 2026-11-26 the 13:00 slot found the account
# full at 13:11, was retried by the 14:47 backup and posted at 15:01:47, which took the share of
# threads-autopilot's 15 UTC slot (Taiwan 23:00; its post.yml publishes up to 3 hours after the slot start,
# cloud_post.THREADS_SLOT_MAX_DELAY_SECONDS), so that slot found 3 posts and skipped twice.
#   SLOT_CUTOFF_UTC   the latest UTC time of day a slot's retry may still post (same UTC day as the slot).
#   RESERVED_UTC      [start, end) UTC times of day that belong to threads-autopilot's 15 UTC slot: no Guide
#                     path publishes a top-level Threads post inside them (account_status answers FULL).
# The other neighbours do not overlap: 03:00 + 3 hours (SLOT_RETRY_GRACE) ends at 06:00, long before 13:00 (and
# threads-autopilot leaves every slot but 15 UTC to the Guide), and the 15 UTC slot ends by 18:00, long before the
# next day's 01:40 / 03:00.
SLOT_CUTOFF_UTC = {13: dt.time(14, 30)}
RESERVED_UTC = ((dt.time(14, 30), dt.time(18, 0)),)
# clip-backup.yml crons (UTC hour, minute): each one runs threads_backfill.py. test_threads_cap.py keeps them in sync.
BACKUP_TIMES = ((0, 47), (3, 47), (4, 47), (11, 47), (14, 47), (17, 47), (20, 47))
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


def slot_grace(slot):
    """The retry grace of a slot: SLOT_RETRY_GRACE for its UTC hour, else RETRY_GRACE."""
    return SLOT_RETRY_GRACE.get(_utc(slot).hour, RETRY_GRACE)


def slot_deadline(slot):
    """The end of a slot's retry grace: fire time + slot_grace(), cut at SLOT_CUTOFF_UTC for that slot."""
    slot = _utc(slot)
    deadline = slot + dt.timedelta(minutes=SLOT_FIRE_MINUTE.get(slot.hour, 0)) + slot_grace(slot)
    cutoff = SLOT_CUTOFF_UTC.get(slot.hour)
    if cutoff is not None:
        deadline = min(deadline, dt.datetime.combine(slot.date(), cutoff, tzinfo=dt.timezone.utc))
    return deadline


def in_reserved(now):
    """True inside a RESERVED_UTC window (threads-autopilot's 15 UTC slot): no Guide top-level post.

    On by default. Only the unit tests of the publishing paths set THREADS_RESERVED_WINDOWS=off (their
    module top), so their wall-clock-free cases do not change with the hour they happen to run at."""
    if os.environ.get("THREADS_RESERVED_WINDOWS", "on").strip().lower() == "off":
        return False
    clock = _utc(now).time()
    return any(start <= clock < end for start, end in RESERVED_UTC)


def full_slot_action(slot, now):
    """RETRY or SKIP for a slot (its UTC hour start) that found the account FULL at ``now``.

    RETRY only while a backup run that fills this slot (same Taiwan day, threads_backfill.py) still comes before
    the grace ends; otherwise SKIP, so the skip is recorded once instead of the slot staying open forever."""
    slot, now = _utc(slot), _utc(now)
    deadline = slot_deadline(slot)
    if now >= deadline:
        return SKIP
    backup = next_backup(now)
    if backup < deadline and backup.astimezone(TW).date() == slot.astimezone(TW).date():
        return RETRY
    return SKIP


def past_grace(slot, now):
    """True once ``now`` is at or after the slot's retry grace end (slot_deadline): the slot no longer posts."""
    return _utc(now) >= slot_deadline(slot)


def within_grace(slot, now, receipt_path="", output_path=""):
    """The room check found room: post only inside the slot's grace. Past it, record a skip (receipt) instead.

    Returns True inside the grace. Past it, writes the receipt (reason past_grace) and capskip=true."""
    if not past_grace(slot, now):
        return True
    receipt = skip_receipt(slot, now, reason="past_grace")
    if receipt_path:
        Path(receipt_path).write_text(json.dumps(receipt, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"::notice::這格（{_utc(slot).isoformat()}）的寬限到 {slot_deadline(slot).strftime('%H:%M')} 世界時已過："
          f"帳號雖有空位也不發（免得佔到後面那格的額度），記為過期跳過")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as out:
            out.write("retry=false\ncapskip=true\n")
    return False


def skip_receipt(slot, now, label="threads-post", reason="cap_full_after_grace"):
    slot, now = _utc(slot), _utc(now)
    return {
        "slot": slot.isoformat(),
        "decided_at": now.replace(microsecond=0).isoformat(),
        "reason": reason,
        "cap": ACCOUNT_DAILY_CAP,
        "grace_minutes": int(slot_grace(slot).total_seconds() // 60),
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
        deadline = slot_deadline(slot)
        print(f"⏸ Threads 帳號已滿 {ACCOUNT_DAILY_CAP} 則：這格（{_utc(slot).isoformat()}）不記完成，"
              f"{next_backup(now).strftime('%H:%M')} 世界時的補發再試（寬限到 {deadline.strftime('%H:%M')}）")
    else:
        receipt = skip_receipt(slot, now)
        if receipt_path:
            Path(receipt_path).write_text(json.dumps(receipt, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"::notice::Threads 帳號已滿 {ACCOUNT_DAILY_CAP} 則，寬限內（到 {slot_deadline(slot).strftime('%H:%M')} 世界時）沒有空位：這格"
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


def account_status(token, user_id=None, *, label="Threads", opener=None, now=None):
    """ROOM, FULL or UNKNOWN for one top-level post about to go out (see the module docstring).

    Inside RESERVED_UTC (threads-autopilot's 15 UTC slot) the answer is FULL without reading the count."""
    if in_reserved(now or dt.datetime.now(dt.timezone.utc)):
        print(f"⏸ 世界時 {RESERVED_UTC[0][0].strftime('%H:%M')}–{RESERVED_UTC[0][1].strftime('%H:%M')} "
              f"是 threads-autopilot 15 UTC（台北 23:00）那格的額度，指南站不發主貼文（{label}）")
        return FULL
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
    within = sub.add_parser("within", help="the room check found room: exit 0 inside the slot's grace, "
                            f"{PAST_GRACE_EXIT} (and a skip receipt) once it is over")
    within.add_argument("--slot", required=True, help="UTC slot start (social_slot_gate.py slot output)")
    within.add_argument("--now", default="", help="tests only: the current UTC time")
    within.add_argument("--receipt", default="", help="where to write the skip receipt")
    merge = sub.add_parser("merge-skip", help="fold a skip receipt into .github/growth/threads-cap-skips.json")
    merge.add_argument("receipt")
    args = parser.parse_args(argv)
    if args.command == "full":
        now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
        full_slot(dt.datetime.fromisoformat(args.slot), now, args.receipt, os.environ.get("GITHUB_OUTPUT", ""))
        return 0
    if args.command == "within":
        now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
        inside = within_grace(dt.datetime.fromisoformat(args.slot), now, args.receipt,
                              os.environ.get("GITHUB_OUTPUT", ""))
        return 0 if inside else PAST_GRACE_EXIT
    merge_skip(args.receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
