#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Threads 自動發文 — 在地化每日輪播與可靠兩階段發布。"""
import datetime as _dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import NamedTuple, Optional

import channel_rotation as CR
import download_links as DL
import duo_line
import threads_cap
import threads_topics
from social_post_common import (
    AMERICAS_LOCALES,
    ASIA_LOCALES,
    EUROPE_MIDDLE_EAST_LOCALES,
    HTTPStatusError,
    RequestError,
    campaign_app_store_url,
    play_store_url,
    canonical_app_store_url,
    canonical_social_image_url,
    channel_candidates,
    item_footer,
    item_image_url,
    request_json,
)
import telegram_post

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Lumi Apps poster)"
MAX_POST_CHARS = 500
# Owner rule 2026-10-17: every promo post carries the app's direct download link. Threads keeps the link
# out of the main text (the account was limited for posting a link in every post) and puts it in the first
# reply, so that reply is checked, retried and - when it still fails - reported loudly, never dropped.
LINK_REPLY_TRIES = 3
LINK_REPLY_BACKOFF = (15, 45)  # seconds waited before the 2nd and the 3rd attempt


def _threads_transient(_status, body):
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    marked_transient = (
        bool(error.get("is_transient")) if isinstance(error, dict) else False
    )
    return marked_transient or "transient" in body.lower()


def _post(url, data, *, label, retry_delays=(2, 4)):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"User-Agent": UA},
    )
    return request_json(
        req,
        label=label,
        timeout=30,
        attempts=3,
        retry_delays=retry_delays,
        extra_transient=_threads_transient,
    )


# Threads 四個排程時段各發對應時區語言，且同日不重複 App。
TZ_LANGS = {
    "asia": list(ASIA_LOCALES),
    "eu_me2": list(EUROPE_MIDDLE_EAST_LOCALES),
    "west": list(EUROPE_MIDDLE_EAST_LOCALES),
    "americas": list(AMERICAS_LOCALES),
}


def _zone(hour_utc):
    if 6 <= hour_utc < 9:
        return "eu_me2"
    if 9 <= hour_utc < 17:
        return "west"
    if 17 <= hour_utc < 21:
        return "americas"
    return "asia"


def candidates(pool, now=None):
    now = (
        _dt.datetime.now(_dt.timezone.utc)
        if now is None
        else now
    )
    zone = _zone(
        now.hour if now.tzinfo is None else now.astimezone(_dt.timezone.utc).hour
    )
    return channel_candidates(pool, f"threads:{zone}", now)


def pick(pool, now=None):
    return candidates(pool, now)[0]


def compose_text(item):
    url = campaign_app_store_url(item.get("url"), "soc_th_guide")
    text = f"{item['text']}\n\n{url}\n\n{item_footer(item)}"
    play = play_store_url(item.get("app"), "soc_th_guide")
    with_play = f"{item['text']}\n\n{url}\nGoogle Play: {play}\n\n{item_footer(item)}" if play else text
    return with_play if len(with_play) <= MAX_POST_CHARS else text


def with_duo(text, app, lang, rest=""):
    """The main text with the iPhone Duo line after it (duo_line.py, copy of 00_GrowthEngine aso/duo/duo_line.py:
    only an App duo_list.load() can claim, the reviewed social_line of its language, live version re-read). Left as
    it is when the post (with `rest`, the part that follows) would pass 500 characters, when the text is shorter than
    the 40 characters a rerun needs to find the post by its first 80 (find_own_post / find_trial_post), or on any
    error: no Duo line rather than a failed post. No URL in it, so the link stays in the first reply."""
    try:
        if len(_norm(text)) < 40:
            return text
        return duo_line.append(text, app, lang, MAX_POST_CHARS - len(rest))
    except Exception as error:  # noqa: BLE001
        print(f"Threads: iPhone Duo line skipped ({error.__class__.__name__})", file=sys.stderr)
        return text


def compose_body(item):
    """Post body without links: links go in the first reply (accounts posting a
    link in every post get limited)."""
    footer = f"\n\n{item_footer(item)}"
    return f"{with_duo(item['text'], item.get('app'), item.get('lang'), footer)}{footer}"


def compose_links(item):
    url = campaign_app_store_url(item.get("url"), "soc_th_guide")
    play = play_store_url(item.get("app"), "soc_th_guide")
    links = f"App Store: {url}" + (f"\nGoogle Play: {play}" if play else "")
    return threads_topics.review_tail(links, item.get("app"), item.get("lang"), item.get("text") or "", MAX_POST_CHARS)


def item_topic(item):
    """The picture post's topic tag: the item's own "topic_tag", else its app category's default (or None)."""
    return threads_topics.for_post(item.get("app"), item.get("text") or "", item.get("lang"), item.get("topic_tag"))


def item_link_urls(item):
    """(App Store URL, Google Play URL or None) of the app a pool item promotes, as the link reply must
    carry them. The store URL is built from the app id, so a reply linking another app fails the check."""
    return f"https://apps.apple.com/app/id{item['app']}", play_store_url(item.get("app"), "soc_th_guide")


def pick_postable(pool, now=None):
    # load_pool() is already built from the verified live linkset. Rechecking
    # every App Store URL here creates a burst of HEAD requests and triggers
    # Apple's 429 rate limit before a single post can be published.
    for item in candidates(pool, now):
        try:
            text = compose_text(item)
        except ValueError as error:
            print(f"Threads: skipping invalid URL ({error})", file=sys.stderr)
            continue
        if len(text) > MAX_POST_CHARS:
            print(
                f"Threads: skipping overlong item ({len(text)} chars, "
                f"lang={item.get('lang')}, app={item.get('app')})",
                file=sys.stderr,
            )
            continue
        return item, text
    raise RequestError(
        "Threads: no live item of 500 characters or fewer remains in this channel"
    )


def publish_text(token, user_id, text, sleeper=time.sleep):
    """A top-level text post (portfolio_daily.py). The post id, or None when the account cap held it
    (threads_cap.py printed why: the ⏸ line when full, ::warning:: when the count could not be read).
    In the Threads week of the channel rotation holdout nothing is posted either (None, the ::notice:: says why)."""
    if CR.paused_notice("threads"):
        return None
    if threads_cap.account_status(token, user_id, label="Threads text post") != threads_cap.ROOM:
        return None
    return publish_post(token, user_id, text, sleeper=sleeper)


def publish_post(
    token,
    user_id,
    text,
    image_url=None,
    sleeper=time.sleep,
    reply_to=None,
    topic_tag=None,
):
    """Create and publish one Threads post. `topic_tag` (top-level posts only) is checked first
    (threads_topics.clean: an invalid one is dropped with a warning); when Threads refuses the container
    with the topic, it is created once more without it, so a topic never stops a post."""
    if len(text) > MAX_POST_CHARS:
        raise ValueError(
            f"Threads post exceeds {MAX_POST_CHARS} characters: {len(text)}"
        )
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": token,
    }
    if reply_to is not None:
        payload["reply_to_id"] = reply_to
    if image_url is not None:
        image_url = canonical_social_image_url(image_url)
        payload["media_type"] = "IMAGE"
        payload["image_url"] = image_url
    topic = threads_topics.clean(topic_tag) if reply_to is None else None
    container = None
    if topic:
        try:
            container = _post(
                f"https://graph.threads.net/v1.0/{user_id}/threads",
                dict(payload, topic_tag=topic),
                label="Threads container",
            )
        except HTTPStatusError as error:  # a container is not a post yet: try once more without the topic
            print(f"::warning::Threads refused the topic tag {topic!r} ({error.__class__.__name__}); "
                  "posted without a topic", file=sys.stderr)
    if container is None:
        container = _post(
            f"https://graph.threads.net/v1.0/{user_id}/threads",
            payload,
            label="Threads container",
        )
    container_id = container.get("id")
    if not container_id:
        raise RequestError("Threads container returned no id")
    sleeper(35)
    published = _post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        {"creation_id": container_id, "access_token": token},
        label="Threads publish",
        retry_delays=(25, 25),
    )
    post_id = published.get("id")
    if not post_id:
        raise RequestError("Threads publish returned no id")
    return post_id


def _failure_note(error):
    """Class name (and HTTP status) of a failure: never the message, which can carry a URL with the token."""
    status = getattr(error, "status", "")
    return f"{error.__class__.__name__}{f' {status}' if status else ''}"


class LookupFailed(Exception):
    """The platform could not tell whether a reply / post is already up: nothing is posted on a guess."""


def find_own_link_reply(token, media_id, app_store_url, play_url=None, opener=urllib.request.urlopen):
    """The id of our own reply under `media_id` that already carries the app's download link(s), or None.
    A retry looks first: the platform may have published the reply although its answer never came back.
    Raises LookupFailed when the look itself failed (a second reply could double the first)."""
    query = urllib.parse.urlencode({"fields": "id,text,is_reply_owned_by_me", "limit": 50, "access_token": token})
    try:
        with opener(f"https://graph.threads.net/v1.0/{media_id}/replies?{query}", timeout=30) as r:
            rows = json.loads(r.read()).get("data", [])
    except Exception as error:
        print(f"Threads: could not look for an earlier link reply ({_failure_note(error)})", file=sys.stderr)
        raise LookupFailed(_failure_note(error)) from None
    mine = [row for row in rows if isinstance(row, dict) and row.get("is_reply_owned_by_me")]
    text = " ".join(str(row.get("text") or "") for row in mine)
    if mine and DL.has_download_link(text, app_store_url, play_url):
        return str(mine[0].get("id") or "existing")
    return None


def publish_link_reply(token, user_id, media_id, links_text, app_store_url, play_url=None, *,
                       sleeper=None, tries=LINK_REPLY_TRIES, label="Threads", find_reply=None):
    """The first reply under a Threads post: the app's direct download link(s). The reply id, or None.

    The text is checked first (threads_reply_problems: this app's App Store link, plus its Google Play link
    when it is on Android). A failed attempt is retried `tries` times with a growing wait; when it still
    fails the post is already up, so nothing is re-posted: the failure is reported with download_links.refuse
    (::error:: and the LINK_GUARD_LOG line) and None comes back so the caller ends the step red.
    link_backfill.py later adds the link under a post that stays without it.
    """
    problems = DL.threads_reply_problems(links_text, app_store_url, play_url)
    if problems:
        DL.refuse(label, problems)
        return None
    sleeper = sleeper or time.sleep
    for attempt in range(1, tries + 1):
        if attempt > 1:
            try:
                existing = (find_reply or find_own_link_reply)(token, media_id, app_store_url, play_url)
            except LookupFailed:   # cannot tell whether an earlier try went through: no second reply
                break
            if existing:
                print(f"{label}: the link reply is already up (id {existing}); not posted twice")
                return existing
        try:
            return publish_post(token, user_id, links_text, sleeper=sleeper, reply_to=media_id)
        except ValueError as error:  # e.g. over the length limit: another attempt cannot change that
            print(f"{label}: link reply cannot be posted ({error.__class__.__name__})", file=sys.stderr)
            break
        except Exception as error:  # network, platform answer: the post is up, so try again
            print(f"{label}: link reply attempt {attempt}/{tries} failed ({_failure_note(error)})", file=sys.stderr)
            if attempt < tries:
                sleeper(LINK_REPLY_BACKOFF[min(attempt, len(LINK_REPLY_BACKOFF)) - 1])
    DL.refuse(label, [f"the Threads post {media_id} is up but its download link reply was not posted "
                      "(link_backfill.py adds it)"])
    return None


QUEUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "growth", "threads-queue.json")


TW = _dt.timezone(_dt.timedelta(hours=8))


def slot_time(value):
    """The UTC slot start social_slot_gate.py wrote, or None when unset."""
    if not value:
        return None
    stamp = _dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=_dt.timezone.utc)
    return stamp.astimezone(_dt.timezone.utc)


class ThreadsResult(NamedTuple):
    post_id: Optional[str]  # the main post's id; None when nothing was posted
    link_ok: bool           # the reply with the download link(s) is up


class _LinkedResult(ThreadsResult):
    """A ThreadsResult (still the 2-tuple) that also knows the link reply's id (`reply_id`, None when unknown)."""
    reply_id = None


def _linked(post_id, link_ok, reply_id):
    result = _LinkedResult(post_id, link_ok)
    result.reply_id = str(reply_id) if reply_id else None
    return result


def _norm(text):
    return " ".join(str(text or "").split())


def find_own_post(token, text, day=None, opener=urllib.request.urlopen):
    """The id of our own top-level post of Taiwan day `day` (default: today) whose text is `text`, or None.
    A rerun of a slot that ended red because only its link reply failed uses it to add the reply under the
    post that is already up instead of posting the same text twice. Spacing is ignored, and a long text
    that the platform returns cut off still matches by its first 80 characters. Only a post stamped inside
    that Taiwan day counts: the series repeats a text after a day or more, and the platform's `since` is not
    trusted to cut the older copies off, so yesterday's post must never stand in for today's (a green step
    with nothing posted). Raises LookupFailed when the look itself failed, or when a copy of this text has
    no readable timestamp (today's post cannot be told from an older one): the caller then posts nothing
    (a second copy of the post is worse than a late one, and a missing one ends the step red)."""
    day = day or _dt.datetime.now(TW).date()
    start = _dt.datetime.combine(day, _dt.time(), TW)
    end = start + _dt.timedelta(days=1)
    query = urllib.parse.urlencode({"fields": "id,text,timestamp", "since": int(start.timestamp()),
                                    "limit": 50, "access_token": token})
    try:
        with opener(f"https://graph.threads.net/v1.0/me/threads?{query}", timeout=30) as r:
            rows = json.loads(r.read()).get("data", [])
    except Exception as error:
        print(f"Threads: could not look for an earlier copy of this post ({_failure_note(error)})", file=sys.stderr)
        raise LookupFailed(_failure_note(error)) from None
    want = _norm(text)
    for row in rows:
        if not (isinstance(row, dict) and row.get("id")):
            continue
        got = _norm(row.get("text"))
        if not (got == want or (len(want) >= 40 and len(got) >= 40 and got[:80] == want[:80])):
            continue
        try:
            when = _dt.datetime.strptime(str(row.get("timestamp") or ""), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            print("Threads: a post with this text has no readable timestamp; cannot tell whether it is today's",
                  file=sys.stderr)
            raise LookupFailed("no readable timestamp") from None
        if start <= when < end:
            return str(row["id"])
    return None


def publish_linked(token, user_id, text, links_text, app_store_url, play_url=None, *, image_url=None, day=None,
                   sleeper=None, label="Threads", find=None, find_reply=None, topic_tag=None):
    """One Threads post with its download link: the main `text` (no URL in it), then the link reply.

    Nothing is posted when `links_text` does not carry this app's link (a promo post without its download
    link must not go out). A rerun of a slot (the watchdog re-dispatches a red one) first looks for the
    post and, when it is up, for its link reply: only a missing reply is added, and when either look fails
    nothing is posted on a guess (the lookups are tri-state, see LookupFailed). Errors of the main post
    propagate as before; a link reply that still fails after its retries comes back as link_ok=False, the
    post already recorded as up, so the caller ends the step red without re-posting.

    A new top-level post first passes the account cap (threads_cap.py: at most 3 top-level posts in 24 hours,
    threads-autopilot's included). Full: nothing is posted and link_ok stays True (a skip is not a failure, the
    step stays green). Count unknown: nothing is posted and link_ok is False, so the step ends red and the
    watchdog / threads_backfill.py run the slot again later the same Taiwan day. Adding only the link reply
    under a post that is already up is a reply, never held by the cap.
    """
    problems = DL.threads_reply_problems(links_text, app_store_url, play_url)
    if problems:
        DL.refuse(f"{label} (nothing was posted)", problems)
        return ThreadsResult(None, False)
    sleeper = sleeper or time.sleep
    try:
        post_id = (find or find_own_post)(token, text, day)
    except LookupFailed:   # cannot tell whether this slot's post is already up: no second copy on a guess
        DL.refuse(label, ["could not tell whether this slot's post is already up, so nothing was posted "
                          "(the watchdog runs the slot again)"])
        return ThreadsResult(None, False)
    if post_id:
        try:   # the post is up: a link reply may be up too (an earlier run, or link_backfill.py added it)
            existing = (find_reply or find_own_link_reply)(token, post_id, app_store_url, play_url)
        except LookupFailed:
            DL.refuse(label, [f"the Threads post {post_id} is up but it could not be checked whether its link reply "
                              "is up too, so none was posted (the next run or link_backfill.py settles it)"])
            return ThreadsResult(post_id, False)
        if existing:
            print(f"{label}: this post and its link reply are already up (post {post_id}, reply {existing}); nothing to post")
            return _linked(post_id, True, existing)
        print(f"{label}: this post is already up (id {post_id}); only its link reply is added")
    else:
        if CR.paused_notice("threads"):  # channel rotation holdout week: no new top-level post, a skip
            return ThreadsResult(None, True)
        status = threads_cap.account_status(token, user_id, label=label)
        if status != threads_cap.ROOM:
            return ThreadsResult(None, status == threads_cap.FULL)
        if topic_tag is None:
            post_id = publish_post(token, user_id, text, image_url=image_url, sleeper=sleeper)
        else:
            post_id = publish_post(token, user_id, text, image_url=image_url, sleeper=sleeper, topic_tag=topic_tag)
    reply_id = publish_link_reply(token, user_id, post_id, links_text, app_store_url, play_url,
                                  sleeper=sleeper, label=label, find_reply=find_reply)
    return _linked(post_id, reply_id is not None, reply_id)


def queued_today(day=None):
    """The post queued for today (Taiwan date) in growth/threads-queue.json, or None."""
    import datetime as _d
    day = day or _d.datetime.now(_d.timezone(_d.timedelta(hours=8))).date()
    try:
        with open(QUEUE, encoding="utf-8") as f:
            posts = json.load(f).get("posts", [])
    except (OSError, ValueError):
        return None
    return next((p for p in posts if p.get("date") == day.isoformat()), None)


def queued_campaign(post):
    """Every queued / series post goes out on Threads, so its links carry the Threads campaign: a BM series
    token (bm_*, even one named after another platform) or a per-post token stays in the queue and post log,
    because Apple reveals a campaign only past its privacy threshold (download_links.coarse_campaign)."""
    return "threads"


def queued_link_urls(post):
    """(App Store URL, Google Play URL or None) of the app a queued / series post promotes."""
    return f"https://apps.apple.com/app/id{post['app_id']}", play_store_url(post["app_id"], queued_campaign(post))


def queued_links(post):
    ct = queued_campaign(post)
    url = campaign_app_store_url(f"https://apps.apple.com/app/id{post['app_id']}", ct)
    play = play_store_url(post["app_id"], ct)
    links = f"App Store: {url}" + (f"\nGoogle Play: {play}" if play else "")
    return threads_topics.review_tail(links, post["app_id"], post.get("lang"), post.get("text") or "", MAX_POST_CHARS)


def queued_topic(post):
    """A queued / series post's topic tag: its own "topic_tag", else its app category's default (or None)."""
    return threads_topics.for_post(post.get("app_id"), post.get("text") or "", post.get("lang"), post.get("topic_tag"))


# Mochi top-10 trial (decided 2026-10-19, copy from 00_GrowthEngine outreach/threads/mochi_top10_2026-10-19.json
# at 07ded37a): on each date the file lists (Taiwan date, 2026-10-20 .. 2026-11-01, every other day) the picture
# slot - the day's post of this script - goes to that entry instead of the queued / countdown / picture post. It
# takes the slot, never adds one: the slot gate, the account cap and every link check stay as they are. A date the
# file does not list (any day after 2026-11-02 included) runs the usual logic, with no code change needed.
# 2026-10-20 change (run 39362861445: the 11:00 slot found the account cap already used up and the entry was lost):
# the entry gets the day's FIRST slot that posts (01:40 UTC hook-clip slot, `threads_post.py trial`), not the
# leftover. A slot that finds the entry already up (an earlier slot posted it) runs its usual content; a missed
# entry (cap full, lookup down) is made up once by the next slot that has room, until the next entry's date (the
# last entry: one day after its date), with the same ct. Still one slot, one post, the same account cap.
TRIAL_PATH = os.path.join(HERE, "threads_mochi_trial.json")
# What each trial entry posted (post id, first seen up, link reply id), keyed by the entry's Taiwan date. A record, never a
# dedupe source: whether an entry is up is always read from the account (find_trial_post), so a record that could
# not be written or pushed never makes a second copy. The workflow commits it through growth_records.py
# (.github/growth only), so it lives beside the other bot records, not in the reviewed trial file.
TRIAL_STATUS_PATH = os.path.join(HERE, "..", "growth", "threads-mochi-trial-status.json")
TRIAL_STATUS_SCHEMA = "lumi.threads-mochi-trial-status/v1"
RECORD_TRIAL_STATUS = False  # set by the command line run only: an imported module (the tests) writes no record
TRIAL_APP_NAME = "Mochi"


def load_trial(path=TRIAL_PATH):
    """The trial file as a dict ({} when it is missing or unreadable: the usual logic then runs)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def trial_post(day, trial=None):
    """The trial entry dated `day` (a Taiwan date), or None on any other day."""
    trial = load_trial() if trial is None else trial
    if not day:
        return None
    return next((p for p in trial.get("posts") or [] if isinstance(p, dict) and p.get("date") == day.isoformat()), None)


def trial_window_post(day, trial=None):
    """The entry a slot of Taiwan day `day` owes: the one whose window holds `day` (its date up to the next
    entry's date, the last entry: its date and the day after), or None. A missed entry is made up only there."""
    trial = load_trial() if trial is None else trial
    if not day:
        return None
    posts = sorted((p for p in trial.get("posts") or [] if isinstance(p, dict) and p.get("date")),
                   key=lambda p: p["date"])
    pool = trial_cycle_pool(trial)
    for i, post in enumerate(posts):
        try:
            start = _dt.date.fromisoformat(post["date"])
            end = (_dt.date.fromisoformat(posts[i + 1]["date"]) if i + 1 < len(posts)
                   else start + _dt.timedelta(days=1 if pool else 2))
        except ValueError:
            continue
        if start <= day < end:
            return post
    return trial_cycle_post(day, posts, pool)


# 2026-10-21 (00_GrowthEngine ops/company/mochi_no1_strategy.md C.1, owner 10-21 "every day"): after the last dated
# entry the trial does not end. With "daily_after_end": {"cts": [...]} in the file, each later Taiwan day owes one
# entry of that list, in turn (day 1 after the last date: the first ct), dated that day: same slot rule, same cap,
# same QA and links, its own ct. Only evergreen entries go in the list (no dated season copy). A missed day is not
# carried to the next day (that day owes its own). New dated entries appended to "posts" push the cycle later.
def trial_cycle_pool(trial):
    """The entries "daily_after_end" cycles through (in its order), or [] when the file sets no cycle."""
    cfg = trial.get("daily_after_end")
    if not isinstance(cfg, dict):
        return []
    by_ct = {p.get("ct"): p for p in trial.get("posts") or [] if isinstance(p, dict) and p.get("ct")}
    return [by_ct[ct] for ct in cfg.get("cts") or [] if isinstance(ct, str) and ct in by_ct]


def trial_cycle_post(day, posts, pool):
    """The cycle entry Taiwan day `day` owes (a copy dated `day`), or None before / without a cycle."""
    if not pool or not posts:
        return None
    try:
        last = max(_dt.date.fromisoformat(p["date"]) for p in posts)
    except ValueError:
        return None
    if day <= last:
        return None
    entry = dict(pool[((day - last).days - 1) % len(pool)])
    entry["date"] = day.isoformat()
    return entry


def find_trial_post(token, post, day, opener=urllib.request.urlopen):
    """(id, UTC timestamp) of our own top-level post of the trial entry `post` made between its date and the end of
    Taiwan day `day`, or None when it is not up. Raises LookupFailed when the look failed or a copy of the text has
    no readable timestamp (nothing is posted on a guess)."""
    start = _dt.datetime.combine(_dt.date.fromisoformat(post["date"]), _dt.time(), TW)
    end = _dt.datetime.combine(day, _dt.time(), TW) + _dt.timedelta(days=1)
    query = urllib.parse.urlencode({"fields": "id,text,timestamp", "since": int(start.timestamp()),
                                    "limit": 50, "access_token": token})
    try:
        with opener(f"https://graph.threads.net/v1.0/me/threads?{query}", timeout=30) as r:
            rows = json.loads(r.read()).get("data", [])
    except Exception as error:
        print(f"Threads: could not look for the Mochi trial post ({_failure_note(error)})", file=sys.stderr)
        raise LookupFailed(_failure_note(error)) from None
    want = _norm(post.get("text"))
    for row in rows:
        if not (isinstance(row, dict) and row.get("id")):
            continue
        got = _norm(row.get("text"))
        if not (got == want or (len(want) >= 40 and len(got) >= 40 and got[:80] == want[:80])):
            continue
        try:
            when = _dt.datetime.strptime(str(row.get("timestamp") or ""), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            raise LookupFailed("no readable timestamp") from None
        if start <= when < end:
            return str(row["id"]), when.astimezone(_dt.timezone.utc)
    return None


def trial_state(token, day, slot, trial, find=None):
    """(state, entry) for a slot of Taiwan day `day` starting at UTC `slot`:
    ("post", e)  the entry is owed and not up: this slot posts it (first post of a trial day, or the make-up);
    ("rerun", e) this slot already posted it (a rerun): publish_linked adds only a missing link reply;
    ("done", e)  an earlier slot posted it: this slot runs its usual content (never a second copy);
    (None, None) no entry owed. LookupFailed propagates."""
    entry = trial_window_post(day, trial)
    if not entry:
        return None, None
    up = (find or find_trial_post)(token, entry, day)
    if not up:
        return "post", entry
    _post_id, when = up
    if slot is not None and when >= slot:
        return "rerun", entry
    return "done", entry


def run_trial(tok, uid, slot, day, trial=None):
    """(took, rc): took is True when the trial entry takes this slot (posted, held by the cap, refused by the QA,
    or a rerun of its own slot); the slot then posts nothing else. rc 0 green, 1 red."""
    trial = load_trial() if trial is None else trial
    try:
        state, entry = trial_state(tok, day, slot, trial)
    except LookupFailed as error:
        print(f"::warning::Threads Mochi trial: could not tell whether the entry is up ({error}); it waits for a "
              "later slot, this slot runs its usual content")
        return False, 0
    if state == "done":
        print(f"Threads Mochi trial {entry.get('ct')} is already up (an earlier slot); usual content")
    if state not in ("post", "rerun"):
        return False, 0
    if entry.get("date") != day.isoformat():
        print(f"Threads Mochi trial {entry.get('ct')} ({entry.get('date')}) was not posted on its day; made up now")
    try:
        return True, post_trial(tok, uid, trial, entry, day)
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Threads Mochi trial post failed: {error}", file=sys.stderr)
        return True, 1


def trial_store_url(trial):
    """The trial app's canonical App Store link (https://apps.apple.com/app/id<digits>)."""
    app_id = DL.app_store_id(trial.get("app_store") or "")
    if not app_id:
        raise ValueError("trial file has no App Store link")
    return f"https://apps.apple.com/app/id{app_id}"


def trial_link_urls(trial, post):
    """(App Store URL, Google Play URL or None) the trial reply must carry; Play only when the app is on Android."""
    store = trial_store_url(trial)
    return store, play_store_url(DL.app_store_id(store), post["ct"])


def trial_links(trial, post):
    """The link block that replaces {link}: the App Store link with the entry's own ct (th_mochi_<lang>_<nn>,
    kept as is by download_links._CAMPAIGN_KEEP), plus the Google Play link when the app is on Android."""
    store, _play = trial_link_urls(trial, post)
    url = campaign_app_store_url(store, post["ct"])
    play = play_store_url(DL.app_store_id(store), post["ct"])
    return url + (f"\nGoogle Play: {play}" if play else "")


def trial_reply(trial, post):
    template = str(post.get("reply") or "")
    if template.count("{link}") != 1:
        raise ValueError(f"trial reply {post.get('ct')} must hold {{link}} exactly once")
    reply = template.replace("{link}", trial_links(trial, post))
    return threads_topics.review_tail(reply, DL.app_store_id(trial_store_url(trial)), post.get("lang"),
                                      post.get("text") or "", MAX_POST_CHARS)


def trial_topic(trial, post):
    """The trial entry's own "topic_tag" (checked; None when it has none or it is not valid)."""
    return threads_topics.clean(post.get("topic_tag"))


def trial_problems(trial, post):
    """post_qa's checks of the main text (length, hook line, language, claims and counts against the live product
    page) and of the reply's words; download_links checks the reply's links again in publish_linked."""
    import post_qa

    store = trial_store_url(trial)
    facts, price = post_qa.product_facts(store, (TRIAL_APP_NAME,))
    text = str(post.get("text") or "")
    out = post_qa.text_problems(text, post.get("lang") or "en-US", "threads", allowed=(TRIAL_APP_NAME,),
                                facts=facts, price=price)
    if post_qa.URL.search(text):
        out.append("the main text carries a URL (Threads keeps links in the first reply)")
    reply = trial_reply(trial, post)
    out += post_qa.claim_problems(reply, (TRIAL_APP_NAME,), facts, price)
    out += post_qa.link_problems(store)
    return out


def _read_status(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    entries = data.get("entries") if isinstance(data, dict) else None
    return entries if isinstance(entries, dict) else {}


def _write_status(entries, path):
    data = {"schema": TRIAL_STATUS_SCHEMA,
            "note": "threads_post.py: what each Mochi trial day posted (Taiwan date). A record only; "
                    "whether an entry is up is read from the account, never from this file.",
            "entries": dict(sorted(entries.items()))}
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def record_trial_status(post, day, result, path=None, now=None):
    """Write the trial day's post id / link reply id. Never raises: a failed write is a ::warning:: only."""
    if not result.post_id or not day or (path is None and not RECORD_TRIAL_STATUS):
        return False
    # The workflow sets TRIAL_STATUS_OUT (a file under $RUNNER_TEMP): growth_records.py prepare resets the tree
    # before a record step commits, so the record waits outside it and merge-trial-status folds it in.
    path = path or os.environ.get("TRIAL_STATUS_OUT", "").strip() or TRIAL_STATUS_PATH
    try:
        entries = dict(_read_status(TRIAL_STATUS_PATH), **_read_status(path))
        key = str(post.get("date") or day.isoformat())  # the entry (the trial day it fills)
        old = entries.get(key) if isinstance(entries.get(key), dict) else {}
        same = old.get("post_id") == str(result.post_id)
        stamp = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries[key] = {
            "ct": post.get("ct"),
            "posted_day": old.get("posted_day") if same and old.get("posted_day") else day.isoformat(),
            "post_id": str(result.post_id),
            "posted_at": old.get("posted_at") if same and old.get("posted_at") else stamp,
            "link_reply_id": (str(getattr(result, "reply_id", None)) if getattr(result, "reply_id", None)
                              else (old.get("link_reply_id") if same else None)),
            "link_ok": bool(result.link_ok),
        }
        _write_status(entries, path)
        return True
    except Exception as error:  # the post is up either way; the record is not worth a red step
        print(f"::warning::Threads Mochi trial: status record not written ({error.__class__.__name__})",
              file=sys.stderr)
        return False


def merge_trial_status(src, path=None):
    """Fold the records of `src` (this run's copy, saved before growth_records.py prepare) into `path`."""
    path = path or TRIAL_STATUS_PATH
    entries = _read_status(path)
    entries.update({k: v for k, v in _read_status(src).items() if isinstance(v, dict)})
    _write_status(entries, path)


def post_trial(tok, uid, trial, post, day):
    """Publish one trial entry: main text without a link, then the reply with the link (publish_linked: the
    account cap, the rerun lookups and the reply check all apply). 0 when green, 1 when red."""
    import post_qa

    label = f"Threads Mochi trial {post.get('ct')} {post.get('date')}"
    if not post_qa.gate(trial_problems(trial, post), label):
        return 1
    store, play = trial_link_urls(trial, post)
    result = publish_linked(tok, uid, with_duo(post["text"], store, post.get("lang")), trial_reply(trial, post),
                            store, play, day=day, label=label,
                            topic_tag=trial_topic(trial, post))
    if result.post_id:
        print("threads Mochi trial post ok, id:", result.post_id, "| ct:", post.get("ct"))
        record_trial_status(post, day, result)
    return 0 if result.link_ok else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["merge-trial-status"] and len(argv) == 2:
        merge_trial_status(argv[1])
        return 0
    tok = os.environ.get("THREADS_TOKEN", "").strip()
    uid = os.environ.get("THREADS_USER_ID", "").strip()
    if not tok or not uid:
        print("missing THREADS_TOKEN / THREADS_USER_ID", file=sys.stderr)
        return 1
    # Post as the token's own account: the THREADS_USER_ID secret pointed at an
    # old account (Threads answered "object does not exist", code 100/33).
    try:
        import urllib.request as _u
        with _u.urlopen(f"https://graph.threads.net/v1.0/me?fields=id&access_token={tok}", timeout=30) as r:
            uid = json.loads(r.read()).get("id") or uid
    except Exception as error:  # keep the secret as a fallback
        print(f"Threads: could not resolve the token's account ({error.__class__.__name__})", file=sys.stderr)
    # THREADS_SLOT (social_slot_gate.py's slot) keeps a run GitHub delayed, or
    # a backfill, on the content and audience of the slot it fills.
    slot = slot_time(os.environ.get("THREADS_SLOT", ""))
    day = slot.astimezone(TW).date() if slot else _dt.datetime.now(TW).date()
    took, rc = run_trial(tok, uid, slot, day)
    if argv[:1] == ["trial"]:
        # The 01:40 / 13:00 slots: the trial entry first; took=true tells the workflow the slot is taken.
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write(f"took={'true' if took else 'false'}\n")
        print(f"Threads Mochi trial: {'this slot is taken by the trial' if took else 'no trial post in this slot'}")
        return rc
    if took:
        return rc
    post = queued_today(slot.astimezone(TW).date() if slot else None)
    if post:
        try:
            store, play = queued_link_urls(post)
            result = publish_linked(tok, uid, with_duo(post["text"], post.get("app_id"), post.get("lang")),
                                    queued_links(post), store, play,
                                    day=slot.astimezone(TW).date() if slot else None,
                                    label=f"Threads queued {post.get('app')} {post.get('date')}",
                                    topic_tag=queued_topic(post))
        except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
            print(f"Threads queued post failed: {error}", file=sys.stderr)
            return 1
        if result.post_id:
            print("threads queued post ok, id:", result.post_id, "| task:", post.get("task"))
        # A post without its download link ends the step red (the post, if it went out, is not re-posted).
        return 0 if result.link_ok else 1
    import countdown_cards
    if countdown_cards.due(slot.astimezone(TW).date() if slot else countdown_cards.today_tw()):
        print("countdown card today (countdown-daily.yml); picture post skipped")
        return 0
    try:
        pool = telegram_post.load_pool()
        item, _ = pick_postable(pool, slot)
        store, play = item_link_urls(item)
        result = publish_linked(
            tok,
            uid,
            compose_body(item),
            compose_links(item),
            store,
            play,
            image_url=item_image_url(item),
            day=slot.astimezone(TW).date() if slot else None,
            label=f"Threads {item.get('app')}/{item.get('lang')}",
            topic_tag=item_topic(item),
        )
        if result.post_id:
            print("threads posted ok, id:", result.post_id, "| app:", item.get("app"))
        return 0 if result.link_ok else 1
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Threads post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    RECORD_TRIAL_STATUS = True
    sys.exit(main())
