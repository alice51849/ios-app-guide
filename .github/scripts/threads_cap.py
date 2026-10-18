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
import json
import urllib.parse
import urllib.request

GRAPH = "https://graph.threads.net/v1.0"
ACCOUNT_DAILY_CAP = 3  # top-level Threads posts in any 24 hours, every pipeline on the account included

ROOM, FULL, UNKNOWN = "room", "full", "unknown"


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
