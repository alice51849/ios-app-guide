#!/usr/bin/env python3
"""Add the missing direct download link under OUR OWN Instagram / Threads posts (self-healing sweeper).

Owner rule (2026-10-17): every promo post carries the app's direct download link. Posts that went out
without one (Instagram Reels captions had "Link in bio" only; a Threads link reply that failed; the August
Threads listing posts) cannot be edited through the API, so the link goes in a comment / reply under our
own post:

- audit: list our posts, resolve the app each one promotes (clips.json + clip-posts.json, the App Store id
  in the text, then the app names in the text), and write a report of which posts have the link (caption,
  or our own comment / reply) and which do not. Writes nothing to the platforms.
- apply: add ONE comment (Instagram) or reply (Threads) per post that lacks it - "<Get it on the App
  Store>: <App Store URL>" plus the Google Play URL when the app is on Android - then read the comments
  back and keep the receipt. A post is only ever done once (state + a look at our own comments first).

Safety, because the Threads account was limited once for posting many linked posts:
- the newest posts come first, at most --max-new writes per channel per run, GAP seconds between writes;
- every write attempt counts (a failing one too); the first write error stops the channel for the run, and
  a post that failed MAX_FAILS times is set aside so one bad post cannot block the rest;
- a rate-limit / block answer (volume_ramp.is_throttle_error) stops the channel, nothing is forced;
- reads are paced (READ_GAP) and capped per run (--max-reads); a post whose app cannot be told is listed,
  never guessed; no write happens when the Android snapshot is missing (the Play link could not be decided);
- each receipt is saved the moment the write succeeds (atomic file replace), before the read-back.

Only the token owner's media is ever listed or written to (own_posts.py clients). Tokens are read from the
environment and never printed or written.

    python3 link_backfill.py audit                          # report only
    python3 link_backfill.py apply --max-new 3 --only 17995101140842399
    python3 link_backfill.py apply --max-new 10 --channels instagram threads
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import clip_posts as CP
import download_links as DL
import own_posts as OP
import volume_ramp
from social_post_common import android_apps, campaign_app_store_url, play_store_url

GROWTH = OP.GROWTH
STATE = GROWTH / "link-backfill.json"
REPORT = GROWTH / "link-backfill-report.json"
CT = {"instagram": "bf_ig", "threads": "bf_th"}   # reply-style attribution, one token per channel
GAP = 20          # seconds between two writes
READ_GAP = 1.0    # seconds between two comment reads
PAGES = 40        # 40 x 50 = the 2000 newest posts of a channel (the whole history of these accounts)
AUDIT_READS = 2000   # comment reads per channel in an audit run
APPLY_READS = 150    # ... and in an apply run (it stops at --max-new writes anyway)
MAX_FAILS = 2     # a post whose comment failed this often is set aside
SKIP_TYPES = {"REPOST_FACADE"}   # a repost shell is not our own post


def load_state(path=STATE):
    state = OP.load_json(path, {})
    for key in ("done", "checked", "failed"):
        state.setdefault(key, {})
    return state


def save_state(state, path=STATE):
    """Atomic: a crash in the middle never leaves half a receipt file."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


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
            if row.get("media_type") in SKIP_TYPES:
                continue
            out.append(dict(row, caption=row.get("caption") or row.get("text") or ""))
        after = ((resp.get("paging") or {}).get("cursors") or {}).get("after")
        if not after or not (resp.get("paging") or {}).get("next"):
            break
    return out


# ---------------------------------------------------------------- which app does a post promote

SPLIT = re.compile(r"[:：（）()\-–—・|／/·,，]")
QUALIFIERS = {"pro", "plus", "lite", "max", "mini", "premium", "free", "ultra"}


def brands(name):
    """Names a post may use for the app: the full store name, its leading Latin run and its delimited parts."""
    out = {name.strip()}
    lead = re.match(r"^[A-Za-z0-9+&' ]+", name)
    if lead and len(lead.group(0).strip()) >= 5:
        out.add(lead.group(0).strip())
    for part in SPLIT.split(name):
        part = part.strip()
        if len(part) >= 4 and re.search(r"[A-Za-z一-鿿]", part):
            out.add(part)
    return out


class AppFinder:
    """Resolves the app a post promotes. Order: the post ledger / hook text / full app name (own_posts.Catalog),
    the App Store id in the text, then exactly one of our brands somewhere in the text (a store listing post
    starts with it). A text that names no brand, two different apps, or "<brand> Plus" (a product we do not
    know) stays unknown - it is listed, never guessed."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.by_id = {str(ios): (key, name) for name, key, ios in catalog.apps if ios}
        self.brands = []
        for name, key, ios in catalog.apps:
            for b in brands(name):
                self.brands.append((b.casefold(), key, ios))
        self.brands.sort(key=lambda x: -len(x[0]))

    def resolve(self, channel, media):
        post = self.catalog.resolve(channel, media)
        if post and ios_id_for(self.catalog, post):
            return post
        text = media.get("caption") or ""
        found = self._by_url(text) or self._by_brand(text)
        if not found:
            return None
        key, ios = found
        first = next((line for line in text.splitlines() if line.strip()), "")
        return {"app": key, "locale": OP.detect_language(text) or "en", "hook": first[:60], "ios_id": ios,
                "kind": "image", "clip": None}

    def _by_url(self, text):
        known = {self.by_id[i][0]: i for i in DL.store_ids_in(text) if i in self.by_id}
        return next(iter(known.items())) if len(known) == 1 else None

    def _hits(self, text):
        out = []
        for b, key, ios in self.brands:
            start = 0
            while True:
                i = text.find(b, start)
                if i < 0:
                    break
                j = i + len(b)
                before = i == 0 or not (b[0].isascii() and b[0].isalnum() and text[i - 1].isascii() and text[i - 1].isalnum())
                after = j >= len(text) or not (b[-1].isascii() and b[-1].isalnum() and text[j].isascii() and text[j].isalnum())
                if before and after:
                    rest = text[j:].lstrip(" :：-")
                    word = re.split(r"[\s:：,，.。]", rest, maxsplit=1)[0] if rest else ""
                    if word not in QUALIFIERS:
                        out.append((i, j, key, ios))
                start = i + 1
        return out

    def _by_brand(self, text):
        low = re.sub(r"^[\W_]+", "", text.strip(), flags=re.U).casefold()
        hits = self._hits(low)
        # a brand inside a longer brand ("Mochi" in "Mochi DoneStamp") is not a second app
        keep = [h for h in hits if not any(o[0] <= h[0] and h[1] <= o[1] and (o[1] - o[0]) > (h[1] - h[0]) for o in hits)]
        keys = {(h[2], h[3]) for h in keep}
        return next(iter(keys)) if len(keys) == 1 else None


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


# ---------------------------------------------------------------- links and comments

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
    """The platform says slow down / blocked (also volume_ramp's wider list of words and codes)."""
    if isinstance(exc, OP.ApiError) and (exc.code in volume_ramp.THROTTLE_CODES or exc.status == 429):
        return True
    return volume_ramp.is_throttle_error(exc)


def write_link(client, media_id, text):
    if client.channel == "instagram":
        return client._post(f"{media_id}/comments", message=text).get("id")
    return client.reply(media_id, text)


def has_link_now(client, media, store, play):
    """(carries the link, text we looked at): the caption (Instagram) plus our own comments / replies."""
    mine = own_comments(client, media["id"])
    text = " ".join(c.get("text", "") for c in mine) + "\n" + (media.get("caption") or "")
    return DL.has_download_link(text, store, play), text


def _short(text, n):
    return " ".join((text or "").split())[:n]


def classify(client, media, finder, state, reads=None, read_gap=0, sleeper=time.sleep):
    """One audit row: what this post promotes and whether it already carries the link.
    `reads` = {"n": comment reads so far, "max": budget}; a read that would exceed it leaves the post unchecked."""
    channel, pid = client.channel, str(media["id"])
    text = media.get("caption") or ""
    row = {"channel": channel, "id": pid, "permalink": media.get("permalink", ""),
           "date": (media.get("timestamp") or "")[:10], "app": "", "status": "", "text": _short(text, 140)}
    post = finder.resolve(channel, media)
    ios = ios_id_for(finder.catalog, post)
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
    done = state["done"].get(channel, {}).get(pid)
    cached = state["checked"].get(channel, {}).get(pid)
    if cached and not done:
        row["status"] = cached
        return row, None
    failed = state["failed"].get(channel, {}).get(pid) or {}
    if failed.get("n", 0) >= MAX_FAILS and not done:
        row["status"] = "write_failed_skipped"
        row["error"] = failed.get("last", "")
        return row, None
    if done and done.get("verified"):
        row["status"] = "ok_backfilled_earlier"
        return row, None
    if reads is not None and reads["n"] >= reads["max"]:
        row["status"] = "not_checked"
        return row, None
    if reads is not None:
        reads["n"] += 1
    mine = own_comments(client, media["id"])
    if read_gap:
        sleeper(read_gap)
    seen = " ".join(c.get("text", "") for c in mine) + "\n" + text
    if DL.has_download_link(seen, store, play):
        if done:  # the comment we wrote is there: verified now
            done["verified"] = True
            row["status"] = "ok_backfilled_earlier"
        else:
            row["status"] = "ok_comment" if channel == "instagram" else "ok_reply"
            state["checked"].setdefault(channel, {})[pid] = row["status"]  # never read this post again
        return row, None
    if done:  # written earlier but not visible (yet): never write a second one
        row["status"] = "backfilled_unverified"
        return row, None
    row["status"] = "missing"
    row["own_replies"] = [_short(c.get("text", ""), 100) for c in mine][:3]
    return row, {"store": store, "play": play, "missing_store": not DL.has_app_store_link(seen, store),
                 "missing_play": bool(play) and not DL.has_play_link(seen, play)}


def run(client, catalog, state, *, apply=False, max_new=5, only=None, sleeper=time.sleep, gap=GAP, read_gap=0,
        log=print, pages=PAGES, now=None, max_reads=None, save=None):
    """Audit (and with apply=True fix) one channel. Returns the report rows."""
    channel = client.channel
    now = now or dt.datetime.now(dt.timezone.utc)
    finder = catalog if isinstance(catalog, AppFinder) else AppFinder(catalog)
    reads = {"n": 0, "max": max_reads if max_reads is not None else (APPLY_READS if apply else AUDIT_READS)}

    def persist():
        if save:
            save(state)

    try:
        client.me()
        media = list_media(client, pages=pages)
    except Exception as exc:
        log(f"::warning::{channel}: listing our posts failed, skipped ({exc})")
        return [{"channel": channel, "id": "", "status": f"list_failed:{getattr(exc, 'code', 'x')}"}]
    rows, attempts = [], 0
    for m in media:
        if only and str(m["id"]) not in only:
            continue
        if apply and attempts >= max_new:
            break  # the batch is used up: the rest keeps its previous status
        try:
            row, todo = classify(client, m, finder, state, reads, read_gap=read_gap, sleeper=sleeper)
        except Exception as exc:
            if is_throttle(exc):
                log(f"::warning::{channel}: the platform says slow down ({exc}); stopping here")
                rows.append({"channel": channel, "id": str(m.get("id")), "status": "throttled"})
                break
            row, todo = {"channel": channel, "id": str(m.get("id")), "status": f"read_failed:{getattr(exc, 'code', 'x')}"}, None
            if isinstance(exc, OP.ApiError) and exc.permission:
                log(f"::warning::{channel}: cannot read comments ({exc}); stopping here")
                rows.append(row)
                break
        rows.append(row)
        if not todo or not apply:
            continue
        if not android_apps():  # the Play link could not be decided: never write half a link
            row["status"] = "snapshot_missing"
            log(f"::error::{channel}: the Android snapshot is empty; nothing is written")
            break
        attempts += 1
        text = comment_text(row.get("locale"), todo["store"], todo["play"] if todo["missing_play"] else None,
                            todo["missing_store"])
        try:
            new_id = write_link(client, row["id"], text)
        except Exception as exc:
            row["status"] = f"write_failed:{getattr(exc, 'code', 'x')}"
            row["error"] = str(exc)[:160]
            fail = state["failed"].setdefault(channel, {}).setdefault(row["id"], {"n": 0})
            fail["n"] += 1
            fail["last"] = row["status"]
            fail["at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            persist()
            log(f"::warning::{channel}: writing under {row['id']} failed ({str(exc)[:120]}); stopping this channel for now")
            break
        at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt = state["done"].setdefault(channel, {})[row["id"]] = {
            "at": at, "comment_id": str(new_id or ""), "app": row["app"], "verified": False}
        persist()  # the receipt is safe on disk before the read-back
        verified = False
        try:
            for _ in range(3):  # read it back: the link must really be under the post
                sleeper(5)
                verified, _seen = has_link_now(client, m, todo["store"], todo["play"])
                if verified:
                    break
        except Exception as exc:
            log(f"::warning::{channel}: read-back of {row['id']} failed ({str(exc)[:100]}); checked again on the next sweep")
        receipt["verified"] = verified
        persist()
        row.update(status="backfilled" if verified else "backfilled_unverified", comment_id=receipt["comment_id"],
                   at=at, verified=verified)
        log(f"{channel}: link added under {row['id']} ({row['app']}) verified={verified}")
        sleeper(gap)
    persist()
    return rows


def merge_state(saved_path, path=STATE):
    """Fold a run's state into the current file (the workflow resets to origin/main before it commits)."""
    saved, state = OP.load_json(saved_path, {}), load_state(path)
    for section in ("done", "checked", "failed"):
        for channel, rows in (saved.get(section) or {}).items():
            state[section].setdefault(channel, {}).update(rows)
    save_state(state, path)


def merge_rows(previous, new):
    """The newest status of every post: this run's rows over the previous report's."""
    merged = {(r.get("channel"), r.get("id")): r for r in previous if r.get("id")}
    for r in new:
        if r.get("id"):
            merged[(r["channel"], r["id"])] = r
    markers = [r for r in new if not r.get("id")]  # list_failed markers
    return sorted(merged.values(), key=lambda r: (r["channel"], r.get("date", ""), r["id"]), reverse=True) + markers


def summarize(rows):
    counts = {}
    for r in rows:
        key = r["status"].split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit", "apply", "merge", "diag"])
    ap.add_argument("--state-from", help="merge: the state file a run saved")
    ap.add_argument("--channels", nargs="+", default=["instagram", "threads"], choices=["instagram", "threads"])
    ap.add_argument("--max-new", type=int, default=5, help="links added per channel per run")
    ap.add_argument("--max-reads", type=int, default=None, help="comment reads per channel per run")
    ap.add_argument("--only", nargs="*", default=None, help="only these post ids (a small first batch)")
    ap.add_argument("--pages", type=int, default=PAGES)
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)
    if args.cmd == "merge":
        merge_state(args.state_from)
        return 0
    if not android_apps():
        print("::error::link_backfill: the Android snapshot is empty or unreadable; the Play link cannot be decided, stopping")
        return 1
    apply = args.cmd == "apply"
    finder = AppFinder(OP.Catalog())
    state = load_state()
    tokens = {"instagram": os.environ.get("IG_ACCESS_TOKEN", "").strip(), "threads": os.environ.get("THREADS_TOKEN", "").strip()}
    clients = {"instagram": OP.InstagramClient, "threads": OP.ThreadsClient}
    if args.cmd == "diag":   # read-only: what the platform answers as the comments of the given posts (public text only)
        for channel in args.channels:
            if not tokens[channel]:
                continue
            client = clients[channel](tokens[channel]).me()
            for pid in args.only or []:
                try:
                    raw = client._get(f"{pid}/comments" if channel == "instagram" else f"{pid}/replies",
                                      fields="id,text,username,timestamp" + (",hidden" if channel == "instagram" else ""),
                                      limit=50).get("data", [])
                except Exception as exc:
                    print(f"diag {channel} {pid}: read failed ({str(exc)[:160]})")
                    continue
                print(f"diag {channel} {pid}: {len(raw)} comments seen, token owner = {client.username}")
                for c in raw[:12]:
                    print(f"  {c.get('id')} user={c.get('username')} hidden={c.get('hidden')} text={_short(c.get('text'), 100)}")
        return 0
    rows = []
    for channel in args.channels:
        if not tokens[channel]:
            print(f"link_backfill: {channel} token not set, skipped")
            continue
        rows += run(clients[channel](tokens[channel]), finder, state, apply=apply, max_new=args.max_new,
                    only=set(args.only) if args.only else None, pages=args.pages, max_reads=args.max_reads,
                    read_gap=READ_GAP, save=save_state if apply else None)
    full_scan = not apply and not args.only and set(args.channels) == {"instagram", "threads"}
    previous = (OP.load_json(args.report, {}) or {}).get("rows", [])
    merged = rows if full_scan else merge_rows(previous, rows)
    counts = summarize(merged)
    if full_scan or merged != previous:   # a sweep that found nothing new leaves the report (and git) alone
        report = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": args.cmd,
                  "counts": counts, "rows": merged}
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    save_state(state)   # receipts, plus the posts an audit found already linked (never read again)
    print(f"link_backfill {args.cmd}: {counts}")
    todo = [r for r in rows if r["status"] in ("missing", "unknown_app", "not_checked")
            or r["status"].startswith(("write_failed", "backfilled_unverified"))]
    for r in todo[:40]:
        print(f"  {r['channel']} {r['id']} {r.get('date', '')} {r.get('app', '')} {r['status']}")
    failed = [r for r in rows if r["status"].startswith("write_failed:") or r["status"] == "snapshot_missing"]
    return 1 if failed else 0   # a write error is an alert (the sweeper itself is the auto-fix); a throttle is not


if __name__ == "__main__":
    sys.exit(main())
