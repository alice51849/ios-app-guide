#!/usr/bin/env python3
"""Add the missing direct download link under OUR OWN Instagram / Threads posts (self-healing sweeper).

Owner rule (2026-10-17): every promo post carries the app's direct download link. Posts that went out
without one (Instagram Reels captions had "Link in bio" only; a Threads link reply that failed) cannot
be edited through the API, so the link goes in a comment / reply under our own post:

- audit: list our posts, resolve the app each one promotes (clips.json + clip-posts.json, then the app
  names in the text), and write a report of which posts have the link (caption, or our own comment /
  reply) and which do not. Writes nothing to the platforms.
- apply: add ONE comment (Instagram) or reply (Threads) per post that lacks it - "<Get it on the App
  Store>: <App Store URL>" plus the Google Play URL when the app is on Android - then read the comments
  back and keep the receipt. A post is only ever done once (state + a look at our own comments first).

Only the token owner's media is ever listed or written to (own_posts.py clients). A rate-limit / block
answer from the platform stops the run for that channel (nothing is forced). Tokens are read from the
environment and never printed or written.

    python3 link_backfill.py audit                          # report only
    python3 link_backfill.py apply --max-new 3 --only 17995101140842399
    python3 link_backfill.py apply --max-new 10 --channels instagram threads
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import clip_posts as CP
import download_links as DL
import own_posts as OP
from social_post_common import campaign_app_store_url, play_store_url

GROWTH = OP.GROWTH
STATE = GROWTH / "link-backfill.json"
REPORT = GROWTH / "link-backfill-report.json"
CT = {"instagram": "bf_ig", "threads": "bf_th"}   # reply-style attribution, one token per channel
THROTTLE_CODES = {4, 17, 32, 341, 368, 613, 80001, 80002, 80006}
GAP = 20       # seconds between two writes
PAGES = 40     # 40 x 50 = the 2000 newest posts of a channel (the whole history of these accounts)


class Throttled(Exception):
    pass


def load_state(path=STATE):
    state = OP.load_json(path, {})
    state.setdefault("done", {})
    return state


def save_state(state, path=STATE):
    Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def list_media(client, pages=PAGES, limit=50):
    """Our own newest posts (id, text/caption, permalink, timestamp), paged."""
    path = f"{client.user_id}/media" if client.channel == "instagram" else f"{client.user_id}/threads"
    fields = ("id,caption,permalink,timestamp,media_type" if client.channel == "instagram"
              else "id,text,permalink,timestamp,media_type")
    out, after = [], None
    for _ in range(pages):
        params = {"fields": fields, "limit": limit}
        if after:
            params["after"] = after
        resp = client._get(path, **params)
        for row in resp.get("data", []):
            out.append(dict(row, caption=row.get("caption") or row.get("text") or ""))
        after = ((resp.get("paging") or {}).get("cursors") or {}).get("after")
        if not after or not (resp.get("paging") or {}).get("next"):
            break
    return out


def ios_id_for(catalog, post):
    """The iOS app id a resolved post promotes ('' when unknown)."""
    if not post:
        return ""
    if post.get("ios_id"):
        return str(post["ios_id"])
    key = post.get("app")
    for _name, app_key, ios in catalog.apps:
        if app_key == key and ios:
            return str(ios)
    return ""


def links_for(channel, ios_id):
    ct = CT[channel]
    return campaign_app_store_url(f"https://apps.apple.com/app/id{ios_id}", ct), play_store_url(ios_id, ct)


def comment_text(locale, store, play, missing_store=True):
    t = CP.text_for(locale or "en")
    lines = []
    if missing_store:
        lines.append(f"{t['button']}: {store}")
    if play:
        lines.append(f"{CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get((locale or 'en').split('-')[0]) or CP.PLAY_LINE['en']}: {play}")
    return "\n".join(lines)


def own_comments(client, media_id):
    rows = client.comments(media_id)
    me = (client.username or "").lower()
    return [r for r in rows if r.get("own") or (r.get("user") or "").lower() == me]


def is_throttle(exc):
    return isinstance(exc, OP.ApiError) and (exc.code in THROTTLE_CODES or exc.status == 429)


def write_link(client, media_id, text):
    if client.channel == "instagram":
        return client._post(f"{media_id}/comments", message=text).get("id")
    return client.reply(media_id, text)


def has_link_now(client, media, store, play):
    """(carries the link, text we looked at): the caption (Instagram) plus our own comments / replies."""
    mine = own_comments(client, media["id"])
    text = " ".join(c.get("text", "") for c in mine) + "\n" + (media.get("caption") or "")
    return DL.has_download_link(text, store, play), text


def classify(client, media, catalog, state):
    """One audit row: what this post promotes and whether it already carries the link."""
    channel = client.channel
    text = media.get("caption") or ""
    row = {"channel": channel, "id": str(media["id"]), "permalink": media.get("permalink", ""),
           "date": (media.get("timestamp") or "")[:10], "app": "", "status": "", "text": " ".join(text.split())[:140]}
    post = catalog.resolve(channel, media)
    ios = ios_id_for(catalog, post)
    row["app"] = (post or {}).get("app", "")
    if not ios:
        row["status"] = "unknown_app"
        return row, None
    store, play = links_for(channel, ios)
    row["ios_id"] = ios
    row["locale"] = (post or {}).get("locale") or OP.detect_language(text) or "en"
    # Instagram carries the links in the caption; Threads keeps them in the first reply on purpose (but a
    # Threads text that holds them itself - older posts, autopilot posts - is complete too).
    if DL.has_download_link(text, store, play):
        row["status"] = "ok_caption"
        return row, None
    if str(media["id"]) in state.get("done", {}).get(channel, {}):
        row["status"] = "ok_backfilled_earlier"
        return row, None
    mine = own_comments(client, media["id"])
    seen = " ".join(c.get("text", "") for c in mine) + "\n" + text
    if DL.has_download_link(seen, store, play):
        row["status"] = "ok_comment" if channel == "instagram" else "ok_reply"
        return row, None
    row["status"] = "missing"
    row["own_replies"] = [" ".join(c.get("text", "").split())[:100] for c in mine][:3]
    return row, {"store": store, "play": play, "missing_store": not DL.has_app_store_link(seen, store),
                 "missing_play": bool(play) and not DL.has_play_link(seen, play)}


def run(client, catalog, state, *, apply=False, max_new=5, only=None, sleeper=time.sleep, gap=GAP, log=print,
        pages=PAGES, now=None):
    """Audit (and with apply=True fix) one channel. Returns the report rows."""
    channel = client.channel
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        client.me()
        media = list_media(client, pages=pages)
    except OP.ApiError as exc:
        log(f"::warning::{channel}: listing our posts failed, skipped ({exc})")
        return [{"channel": channel, "id": "", "status": f"list_failed:{exc.code}"}]
    rows, added, throttled = [], 0, False
    for m in media:
        try:
            row, todo = classify(client, m, catalog, state)
        except OP.ApiError as exc:
            if is_throttle(exc):
                log(f"::warning::{channel}: the platform says slow down ({exc}); stopping here")
                throttled = True
                break
            row, todo = {"channel": channel, "id": str(m.get("id")), "status": f"read_failed:{exc.code}"}, None
            if exc.permission:
                log(f"::warning::{channel}: cannot read comments ({exc}); stopping here")
                rows.append(row)
                break
        rows.append(row)
        if not todo or not apply or throttled:
            continue
        if only and row["id"] not in only:
            continue
        if added >= max_new:
            row["status"] = "missing_queued"
            continue
        text = comment_text(row.get("locale"), todo["store"], todo["play"] if todo["missing_play"] else None,
                            todo["missing_store"])
        try:
            new_id = write_link(client, row["id"], text)
            verified = False
            for _ in range(3):  # read it back: the link must really be under the post
                sleeper(5)
                verified, _seen = has_link_now(client, m, todo["store"], todo["play"])
                if verified:
                    break
        except OP.ApiError as exc:
            row["status"] = f"write_failed:{exc.code}"
            row["error"] = str(exc)[:160]
            if is_throttle(exc):
                log(f"::warning::{channel}: the platform says slow down ({exc}); stopping here")
                throttled = True
            elif exc.permission:
                log(f"::warning::{channel}: no permission to comment ({exc}); stopping here")
                throttled = True
            continue
        row.update(status="backfilled" if verified else "backfilled_unverified", comment_id=str(new_id or ""),
                   at=now.strftime("%Y-%m-%dT%H:%M:%SZ"), verified=verified)
        state.setdefault("done", {}).setdefault(channel, {})[row["id"]] = {
            "at": row["at"], "comment_id": row["comment_id"], "app": row["app"], "verified": verified}
        added += 1
        log(f"{channel}: link added under {row['id']} ({row['app']}) verified={verified}")
        sleeper(gap)
    return rows


def merge_state(saved_path, path=STATE):
    """Fold a run's state into the current file (the workflow resets to origin/main before it commits)."""
    saved, state = OP.load_json(saved_path, {}), load_state(path)
    for channel, rows in (saved.get("done") or {}).items():
        state["done"].setdefault(channel, {}).update(rows)
    save_state(state, path)


def summarize(rows):
    counts = {}
    for r in rows:
        key = r["status"].split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit", "apply", "merge"])
    ap.add_argument("--state-from", help="merge: the state file a run saved")
    ap.add_argument("--channels", nargs="+", default=["instagram", "threads"], choices=["instagram", "threads"])
    ap.add_argument("--max-new", type=int, default=5, help="links added per channel per run")
    ap.add_argument("--only", nargs="*", default=None, help="only these post ids (a small first batch)")
    ap.add_argument("--pages", type=int, default=PAGES)
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)
    if args.cmd == "merge":
        merge_state(args.state_from)
        return 0
    catalog = OP.Catalog()
    state = load_state()
    tokens = {"instagram": os.environ.get("IG_ACCESS_TOKEN", "").strip(), "threads": os.environ.get("THREADS_TOKEN", "").strip()}
    clients = {"instagram": OP.InstagramClient, "threads": OP.ThreadsClient}
    rows = []
    for channel in args.channels:
        if not tokens[channel]:
            print(f"link_backfill: {channel} token not set, skipped")
            continue
        rows += run(clients[channel](tokens[channel]), catalog, state, apply=args.cmd == "apply",
                    max_new=args.max_new, only=set(args.only) if args.only else None, pages=args.pages)
    report = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": args.cmd,
              "counts": summarize(rows), "rows": rows}
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if args.cmd == "apply":
        save_state(state)
    print(f"link_backfill {args.cmd}: {report['counts']}")
    missing = [r for r in rows if r["status"] in ("missing", "missing_queued", "unknown_app") or r["status"].startswith(("write_failed", "backfilled_unverified"))]
    for r in missing[:40]:
        print(f"  {r['channel']} {r['id']} {r.get('date', '')} {r.get('app', '')} {r['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
