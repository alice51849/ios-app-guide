#!/usr/bin/env python3
"""Posting-volume ramp per channel, with automatic throttling (zero network except the issue).

.github/growth/volume-ramp.json says how many posts a day each channel makes:
``stages`` is the list of daily counts, the channel climbs one stage every
``stage_days`` from ``start`` and stays at the last stage. ``slots`` lists the
UTC posting hours in the order they are switched on (the first N for a stage
of N posts). The Growth Engine planner (00_GrowthEngine
shorts/scripts/schedule_posts.py) reads the same file to plan the clip slots,
and the posting scripts call ``allowance`` before posting, so a plan written
before a throttle can never post more than the ramp allows today.

Auto-throttle: when a platform answers with a rate limit, a spam warning or an
action block (``is_throttle_error``), ``throttle`` drops the channel one stage
below the stage it was at (``ceiling``) for ``hold_days``, appends the event to
``events`` and the workflow commits the file; after the hold the channel climbs
again one stage per ``stage_days`` from the ceiling. ``notify`` opens (or
updates) a GitHub issue labelled ``volume-throttle`` with the built-in
GITHUB_TOKEN, the same no-secret path as conversion-guard's sales-health
issues, so the owner gets the mail.

    python3 volume_ramp.py                 # today's allowance and slots per channel
    python3 volume_ramp.py --date 2026-11-01
"""
import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAMP = HERE.parent / "growth" / "volume-ramp.json"
SCHEMA = "lumi.volume-ramp/v1"
LABEL = "volume-throttle"
ISSUE_TITLE = "外宣發文量自動降速：{channel}"
MAX_EVENTS = 50
UA = "lumi-volume-ramp/1.0"

# Platform answers that mean "slow down" (Instagram / Threads Graph API, Telegram Bot API, Bluesky, YouTube).
THROTTLE_CODES = {4, 17, 32, 613, 368, 9, 80001, 80002, 80003, 80004, 80005, 80006, 80007, 80008}
THROTTLE_SUBCODES = {2207051, 2207042}  # API-published posts limit / media publish limit
THROTTLE_WORDS = ("rate limit", "ratelimit", "request limit", "limit of api-published", "publishing limit",
                  "too many requests", "too many", "retry after", "retry_after", "flood", "spam",
                  "action block", "action_block", "blocked", "restricted", "temporarily", "quotaexceeded",
                  "quota exceeded", "uploadlimitexceeded", "upload limit", "accountsuspended", "suspended",
                  "exceeded the number", "please wait", "slow down", "feedback_required")


def load(path=RAMP):
    """The committed ramp ({} when missing, unreadable or another schema: callers fall back to their old pacing)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else {}


def save(ramp, path=RAMP):
    Path(path).write_text(json.dumps(ramp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _date(value, default=None):
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def channel(ramp, name):
    cfg = ((ramp or {}).get("channels") or {}).get(name)
    return cfg if isinstance(cfg, dict) and isinstance(cfg.get("stages"), list) and cfg["stages"] else None


def stage(ramp, name, day):
    """Stage index of `name` on `day`: the climb from start, capped by a throttle ceiling (during its hold)
    and by the resumed climb after the hold. None when the channel is not in the ramp."""
    cfg = channel(ramp, name)
    if cfg is None:
        return None
    stage_days = max(int(ramp.get("stage_days") or 3), 1)
    start = _date(cfg.get("start"), day)
    last = len(cfg["stages"]) - 1
    idx = min(max((day - start).days // stage_days, 0), last) if day >= start else 0
    ceiling, until = cfg.get("ceiling"), _date(cfg.get("ceiling_until"))
    if isinstance(ceiling, int) and until is not None:
        ceiling = min(max(ceiling, 0), last)
        if day <= until:
            idx = min(idx, ceiling)
        else:  # the hold is over: climb again from the ceiling, one stage per stage_days
            idx = min(idx, ceiling + 1 + (day - until - dt.timedelta(days=1)).days // stage_days)
    return idx


def allowance(ramp, name, day):
    """Posts allowed on `day` (None: channel not ramped, keep the old pacing)."""
    idx = stage(ramp, name, day)
    if idx is None:
        return None
    try:
        return max(int(channel(ramp, name)["stages"][idx]), 0)
    except (TypeError, ValueError):
        return None


def slots(ramp, name, day):
    """UTC slot hours planned on `day`: the first `allowance` of the channel's slot order, sorted."""
    cfg = channel(ramp, name)
    n = allowance(ramp, name, day)
    if cfg is None or n is None:
        return None
    hours = [int(h) for h in cfg.get("slots") or [] if str(h).isdigit() or isinstance(h, int)]
    return sorted(hours[:n])


# Channels that post on one platform account: a "slow down" from the platform throttles all of them, and the
# account's posts of every kind stay under ACCOUNT_DAILY_MAX a day (cards included), whatever the stages say.
ACCOUNT_CHANNELS = {"instagram": ("instagram", "instagram_feed")}
ACCOUNT_DAILY_MAX = {"instagram": 10}
CARD_PREFIXES = ("utility/", "countdown/", "feed/")


def account_of(name):
    return next((acc for acc, members in ACCOUNT_CHANNELS.items() if name in members), None)


def account_posts_today(posts, name, day):
    """Every post the channel's platform account made on `day` (all channels on it, cards included)."""
    members = ACCOUNT_CHANNELS.get(account_of(name) or "", (name,))
    return sum(posted_today(posts, m, day, exclude_prefixes=()) for m in members)


def posted_today(posts, name, day, exclude_prefixes=CARD_PREFIXES):
    """Posts of channel `name` logged on `day` (clip-posts.json), minus the card namespaces when counting clips."""
    n = 0
    for p in posts or []:
        if p.get("channel") != name or not str(p.get("posted_at", "")).startswith(day.isoformat()):
            continue
        if exclude_prefixes and str(p.get("clip", "")).startswith(tuple(exclude_prefixes)):
            continue
        n += 1
    return n


def priority_extra(ramp, name):
    """(listings, per_day): the listings that get `per_day` posts a day on channel `name` on top of the stage
    (ramp "priority_extra", owner 2026-10-21: 可愛待辦清單 every day on Instagram and Telegram, added slots that never
    take another app's place). ((), 0) when the channel has none. The planner (00_GrowthEngine
    shorts/scripts/schedule_posts.py DAILY_EXTRA) plans the extra slot; this only lets it post."""
    cfg = (ramp or {}).get("priority_extra")
    if not isinstance(cfg, dict) or name not in (cfg.get("channels") or []):
        return (), 0
    apps = tuple(a for a in cfg.get("apps") or [] if isinstance(a, str) and a)
    try:
        per_day = max(int(cfg.get("per_day") or 0), 0)
    except (TypeError, ValueError):
        per_day = 0
    return (apps, per_day) if apps and per_day else ((), 0)


def listing_of(clip_key):
    """The listing a clip key promotes: "mochi_b/en" -> "mochi" (a hook variant counts as its listing)."""
    return re.sub(r"_[a-z]$", "", str(clip_key or "").split("/")[0])


def room(ramp, name, day, posts, clip=None):
    """(allowed, posted, room) for today; room is None when the channel is not ramped.

    A priority_extra listing's posts (up to its per_day) do not use the stage's allowance, so the extra post never
    takes another app's place; `clip` (the clip key about to go out) of such a listing also gets the unused extra."""
    allowed = allowance(ramp, name, day)
    if allowed is None:
        return None, posted_today(posts, name, day), None
    done = posted_today(posts, name, day, exclude_prefixes=() if name == "instagram_feed" else CARD_PREFIXES)
    apps, extra = priority_extra(ramp, name)
    cfg = channel(ramp, name) or {}
    until = _date(cfg.get("ceiling_until"))
    if isinstance(cfg.get("ceiling"), int) and until is not None and day <= until:
        apps, extra = (), 0   # the platform said "slow down": no added post until the hold is over
    used_extra = min(sum(1 for p in posts or [] if p.get("channel") == name
                         and str(p.get("posted_at", "")).startswith(day.isoformat())
                         and not str(p.get("clip", "")).startswith(CARD_PREFIXES)
                         and listing_of(p.get("clip")) in apps), extra) if apps else 0
    left = max(allowed - (done - used_extra), 0)
    if clip is not None and listing_of(clip) in apps:
        left += extra - used_extra
    acc = account_of(name)
    if acc in ACCOUNT_DAILY_MAX:
        left = min(left, max(ACCOUNT_DAILY_MAX[acc] - account_posts_today(posts, name, day), 0))
    return allowed, done, left


# ---------------------------------------------------------------- throttling

def _error_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def is_throttle_error(error):
    """True when a platform's answer means we post too much or too fast (HTTP 429, Graph API rate-limit / block
    codes, Telegram flood control, YouTube quota, Bluesky rate limit or account restriction)."""
    text = str(error or "")
    low = text.lower()
    if re.search(r"\b429\b", low):
        return True
    data = _error_json(text)
    err = data.get("error") if isinstance(data.get("error"), dict) else data
    try:
        if int(err.get("code") or err.get("error_code") or 0) in THROTTLE_CODES:
            return True
        if int(err.get("error_subcode") or 0) in THROTTLE_SUBCODES:
            return True
    except (TypeError, ValueError, AttributeError):
        pass
    if isinstance(err, dict) and str(err.get("error", "")).lower() in {"ratelimitexceeded", "accountsuspended", "accounttakedown"}:
        return True
    return any(w in low for w in THROTTLE_WORDS)


def throttle(ramp, name, reason, day=None, path=RAMP, now=None):
    """Drop `name` one stage below today's stage for hold_days, record the event and save. Returns the event
    (None when the channel is not ramped or already at stage 0 during a hold: nothing lower to go)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    day = day or now.date()
    cfg = channel(ramp, name)
    if cfg is None:
        return None
    current = stage(ramp, name, day)
    hold = max(int(ramp.get("hold_days") or 7), 1)
    new = max(current - 1, 0)
    event = {"at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "channel": name, "from_stage": current, "to_stage": new,
             "from_per_day": cfg["stages"][current], "to_per_day": cfg["stages"][new],
             "hold_until": (day + dt.timedelta(days=hold)).isoformat(), "reason": str(reason)[:300]}
    cfg["ceiling"], cfg["ceiling_until"] = new, event["hold_until"]
    cfg["events"] = (cfg.get("events") or [])[-(MAX_EVENTS - 1):] + [event]
    if path:
        save(ramp, path)
    return event


def issue_body(event, run_url=None):
    lines = [f"**{event['channel']}** 收到平台限流／垃圾訊息警告／action block，發文量自動降一階。", "",
             f"- 時間：{event['at']}",
             f"- 由每天 {event['from_per_day']} 則（第 {event['from_stage']} 階）退回每天 {event['to_per_day']} 則（第 {event['to_stage']} 階）",
             f"- 維持到 {event['hold_until']}，之後每 3 天再升一階",
             f"- 平台回覆：`{event['reason']}`", ""]
    if run_url:
        lines.append(f"本次 run：{run_url}")
    lines += ["", "設定與事件紀錄：`.github/growth/volume-ramp.json`（volume_ramp.py）。",
              "要提早恢復：把該通路的 `ceiling` 與 `ceiling_until` 改回 null 並 commit。"]
    return "\n".join(lines)


def _gh(method, path, token, body=None):
    req = urllib.request.Request(f"https://api.github.com{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def notify(event, repo=None, token=None, run_url=None, gh=_gh):
    """Open a volume-throttle issue for the channel, or comment on the open one. Returns the issue URL, or
    None when no repository / token is available (a local run) or the API refuses (printed, never raised)."""
    repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
    token = token or os.environ.get("GITHUB_TOKEN", "")
    if not event or not repo or not token:
        return None
    title = ISSUE_TITLE.format(channel=event["channel"])
    body = issue_body(event, run_url or _run_url())
    try:
        q = urllib.parse.quote(f'repo:{repo} is:issue is:open label:{LABEL} in:title "{title}"')
        found = gh("GET", f"/search/issues?q={q}&per_page=5", token).get("items") or []
        found = [i for i in found if i.get("title") == title]
        if found:
            number = found[0]["number"]
            gh("POST", f"/repos/{repo}/issues/{number}/comments", token, {"body": body})
            return found[0].get("html_url")
        made = gh("POST", f"/repos/{repo}/issues", token, {"title": title, "body": body, "labels": [LABEL]})
        return made.get("html_url")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        print(f"::warning::volume ramp: could not open the {LABEL} issue ({exc.__class__.__name__}: {exc})")
        return None


def _run_url():
    repo, run_id = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    if not repo or not run_id:
        return None
    return f"{os.environ.get('GITHUB_SERVER_URL') or 'https://github.com'}/{repo}/actions/runs/{run_id}"


def handle_error(name, error, ramp=None, path=RAMP, day=None, now=None):
    """Called by a poster when a post failed: if the platform told us to slow down, throttle + notify.
    Returns the event or None."""
    if not is_throttle_error(error):
        return None
    ramp = load(path) if ramp is None else ramp
    first = None
    for member in ACCOUNT_CHANNELS.get(account_of(name) or "", (name,)):  # one account: every channel on it slows
        event = throttle(ramp, member, error, day=day, path=path, now=now)
        if not event:
            continue
        first = first or event
        print(f"::warning::volume ramp: {member} throttled to {event['to_per_day']} a day until {event['hold_until']} "
              f"({event['reason'][:120]})")
        url = notify(event)
        if url:
            print(f"volume ramp: issue {url}")
    return first


def merge(saved, current):
    """Fold a ramp saved before a `git reset --hard` (a throttle this run wrote) into the current one: the lower
    ceiling with its hold wins, events are united by time. Returns the merged ramp (current when `saved` is
    empty or foreign)."""
    if not saved or saved.get("schema") != SCHEMA or not current:
        return current or saved
    for name, mine in (saved.get("channels") or {}).items():
        theirs = (current.setdefault("channels", {})).get(name)
        if not isinstance(theirs, dict) or not isinstance(mine, dict):
            continue
        seen = {e.get("at") for e in theirs.get("events") or []}
        theirs["events"] = (theirs.get("events") or []) + [e for e in mine.get("events") or [] if e.get("at") not in seen]
        theirs["events"] = sorted(theirs["events"], key=lambda e: e.get("at", ""))[-MAX_EVENTS:]
        if isinstance(mine.get("ceiling"), int) and (not isinstance(theirs.get("ceiling"), int)
                                                    or mine["ceiling"] < theirs["ceiling"]
                                                    or (mine["ceiling"] == theirs["ceiling"]
                                                        and (mine.get("ceiling_until") or "") > (theirs.get("ceiling_until") or ""))):
            theirs["ceiling"], theirs["ceiling_until"] = mine["ceiling"], mine.get("ceiling_until")
    return current


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default today UTC)")
    ap.add_argument("--ramp", default=str(RAMP))
    ap.add_argument("--merge", help="fold this saved ramp file (a throttle written before a rebase) into --ramp")
    args = ap.parse_args(argv)
    day = _date(args.date) or dt.datetime.now(dt.timezone.utc).date()
    if args.merge:
        merged = merge(load(args.merge), load(args.ramp))
        if merged:
            save(merged, args.ramp)
        print(f"merged {args.merge} into {args.ramp}")
        return 0
    ramp = load(args.ramp)
    if not ramp:
        print("no ramp file; channels keep their old pacing")
        return 0
    for name in ramp.get("channels") or {}:
        idx = stage(ramp, name, day)
        print(f"{name}: stage {idx} -> {allowance(ramp, name, day)} a day, slots {slots(ramp, name, day)} UTC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
