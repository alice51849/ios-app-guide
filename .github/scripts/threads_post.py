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

import download_links as DL
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


def compose_body(item):
    """Post body without links: links go in the first reply (accounts posting a
    link in every post get limited)."""
    return f"{item['text']}\n\n{item_footer(item)}"


def compose_links(item):
    url = campaign_app_store_url(item.get("url"), "soc_th_guide")
    play = play_store_url(item.get("app"), "soc_th_guide")
    return f"App Store: {url}" + (f"\nGoogle Play: {play}" if play else "")


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
    return publish_post(token, user_id, text, sleeper=sleeper)


def publish_post(
    token,
    user_id,
    text,
    image_url=None,
    sleeper=time.sleep,
    reply_to=None,
):
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
                   sleeper=None, label="Threads", find=None, find_reply=None):
    """One Threads post with its download link: the main `text` (no URL in it), then the link reply.

    Nothing is posted when `links_text` does not carry this app's link (a promo post without its download
    link must not go out). A rerun of a slot (the watchdog re-dispatches a red one) first looks for the
    post and, when it is up, for its link reply: only a missing reply is added, and when either look fails
    nothing is posted on a guess (the lookups are tri-state, see LookupFailed). Errors of the main post
    propagate as before; a link reply that still fails after its retries comes back as link_ok=False, the
    post already recorded as up, so the caller ends the step red without re-posting.
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
            return ThreadsResult(post_id, True)
        print(f"{label}: this post is already up (id {post_id}); only its link reply is added")
    else:
        post_id = publish_post(token, user_id, text, image_url=image_url, sleeper=sleeper)
    reply_id = publish_link_reply(token, user_id, post_id, links_text, app_store_url, play_url,
                                  sleeper=sleeper, label=label, find_reply=find_reply)
    return ThreadsResult(post_id, reply_id is not None)


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
    return f"App Store: {url}" + (f"\nGoogle Play: {play}" if play else "")


def main():
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
    post = queued_today(slot.astimezone(TW).date() if slot else None)
    if post:
        try:
            store, play = queued_link_urls(post)
            result = publish_linked(tok, uid, post["text"], queued_links(post), store, play,
                                    day=slot.astimezone(TW).date() if slot else None,
                                    label=f"Threads queued {post.get('app')} {post.get('date')}")
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
        )
        if result.post_id:
            print("threads posted ok, id:", result.post_id, "| app:", item.get("app"))
        return 0 if result.link_ok else 1
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Threads post failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
