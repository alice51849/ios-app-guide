#!/usr/bin/env python3
"""Post ONE correction comment under each of OUR OWN Instagram posts listed in a correction batch file.

Why: some carousels showed store screenshots with demo dates that had already passed (00_GrowthEngine
reports/outreach_scale/pain_carousel_factcheck_2026-11-25.md). Deleting needs a Facebook Login token the Guide does
not have (ig_delete_media_1126/result_1126.md), so the fallback is a short correction comment in the post's language.

Batch file (.github/growth/ig-correction-1126.json, copied from 00 reports/outreach_scale/drafts/): items with
media_id, shortcode, locale, text and review.status. A text is only posted when:
- review.status == "pass" (the in-locale review was done);
- it carries no URL (Instagram texts carry none, owner 2026-10-17) and ends with the localized
  "download via the link in bio" line (download_links.instagram_cta);
- the media read back with the token is ours (username = the token owner) and its permalink is exactly
  https://www.instagram.com/p|reel|tv/<shortcode>/.
Once per post: a receipt in .github/growth/ig-correction.json (saved atomically right after the write) is never
written twice. Read-back: the comment id can be fetched and the post's comments_count went up (the comment list of
a post hides the account's own comments, link_backfill.comments_count). At most --max-new writes per run, GAP
seconds apart, DAILY_CAP in any 24 hours; the first throttle / write error stops the run.

    python3 ig_correction.py check  --batch .github/growth/ig-correction-1126.json   # read only
    python3 ig_correction.py apply  --batch .github/growth/ig-correction-1126.json --max-new 8
The token (IG_ACCESS_TOKEN) is read from the environment and never printed.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

import download_links as DL
import link_backfill as LB
import own_posts as OP

STATE = OP.GROWTH / "ig-correction.json"
GAP = 45          # seconds between two comments
DAILY_CAP = 8     # correction comments in any 24 hours
URL = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(?:com|cc|net|org|io|app|me|ly)\b", re.I)


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def stamp(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def text_problems(item):
    """Why this item may not be posted ([] = fine). Pure: no network."""
    out = []
    mid, sc, loc, text = (str(item.get(k) or "") for k in ("media_id", "shortcode", "locale", "text"))
    if not re.fullmatch(r"\d{6,25}", mid):
        out.append("media_id must be digits")
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,20}", sc):
        out.append("shortcode looks wrong")
    if not text.strip():
        out.append("empty text")
    if len(text) > 2000:
        out.append("text too long")
    if URL.search(text):
        out.append("a URL in an Instagram text")
    if text.count("#") > 3 or text.count("@") > 0:
        out.append("hashtags / mentions not allowed in a correction")
    if not DL.has_instagram_cta(text, loc):
        out.append(f"no '{DL.instagram_cta(loc)}' line for {loc}")
    if ((item.get("review") or {}).get("status")) != "pass":
        out.append("in-locale review not passed")
    return out


def load_batch(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("batch: items missing")
    ids = [str(i.get("media_id")) for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError("batch: a media_id is listed twice")
    codes = [str(i.get("shortcode")) for i in items]
    if len(set(codes)) != len(codes):
        raise ValueError("batch: a shortcode is listed twice")
    return data.get("batch") or Path(path).stem, items


def load_state(path=STATE):
    state = OP.load_json(path, {}) or {}
    state.setdefault("done", {})
    state.setdefault("failed", {})
    return state


def writes_last_day(state, now):
    n = 0
    for r in state["done"].values():
        try:
            when = dt.datetime.strptime(r.get("at", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        n += (now - when) < dt.timedelta(hours=24)
    return n


def media_problems(client, item):
    """([] or why not, media row). Reads the post: ours, and the permalink is exactly the shortcode's."""
    try:
        m = client._get(str(item["media_id"]), fields="id,permalink,username,comments_count")
    except OP.ApiError as exc:
        if LB.is_throttle(exc):
            raise
        return [f"cannot read the media ({str(exc)[:120]})"], {}
    out = []
    me = (client.username or "").strip().lower()
    if not me:
        out.append("the token owner's username is unknown")   # fail closed: "" == "" must not pass as ours
    elif (m.get("username") or "").strip().lower() != me:
        out.append("the media is not the token owner's")
    if not re.fullmatch(r"https://www\.instagram\.com/(p|reel|tv)/" + re.escape(item["shortcode"]) + r"/?",
                        (m.get("permalink") or "").strip()):
        out.append(f"permalink is not /p/{item['shortcode']}/")
    return out, m


def run(client, batch, items, state, *, apply=False, max_new=8, gap=GAP, sleeper=time.sleep, save=None, log=print,
        now=now_utc):
    rows, written = [], 0
    for item in items:
        mid = str(item.get("media_id"))
        row = {"media_id": mid, "shortcode": item.get("shortcode"), "locale": item.get("locale"), "card": item.get("card")}
        rows.append(row)
        if mid in state["done"]:
            row["status"] = "done_before"
            continue
        bad = text_problems(item)
        if bad:
            row["status"] = "refused: " + "; ".join(bad)
            continue
        try:
            bad, media = media_problems(client, item)
        except OP.ApiError as exc:
            row["status"] = f"throttled: {str(exc)[:120]}"
            log(f"::warning::ig_correction: throttle on read ({str(exc)[:120]}); stopping")
            break
        if bad:
            row["status"] = "refused: " + "; ".join(bad)
            continue
        if not apply:
            row["status"] = "ready"
            continue
        if written >= max_new:
            row["status"] = "waits: max_new reached"
            continue
        if writes_last_day(state, now()) >= DAILY_CAP:
            row["status"] = "waits: daily cap"
            continue
        if written:
            sleeper(gap)
        before = LB.comments_count(client, mid)
        try:
            cid = client._post(f"{mid}/comments", message=item["text"]).get("id")
        except OP.ApiError as exc:
            f = state["failed"].setdefault(mid, {"n": 0})
            f.update(n=f["n"] + 1, at=stamp(now()), why=str(exc)[:160])
            row["status"] = f"write_failed: {str(exc)[:120]}"
            log(f"::error::ig_correction: comment on {item.get('shortcode')} failed; stopping the run")
            if save:
                save(state)
            break
        except Exception as exc:   # noqa: BLE001 - timeout / network: the comment may have landed, never post again
            state["done"][mid] = {"at": stamp(now()), "comment_id": None, "shortcode": item["shortcode"],
                                  "locale": item.get("locale"), "card": item.get("card"), "batch": batch,
                                  "text": item["text"], "verified": False, "uncertain": exc.__class__.__name__}
            row["status"] = f"commented_unverified: write answer lost ({exc.__class__.__name__})"
            log(f"::error::ig_correction: no answer for the comment on {item.get('shortcode')}; check it by hand; stopping")
            if save:
                save(state)
            break
        written += 1
        receipt = state["done"][mid] = {"at": stamp(now()), "comment_id": cid, "shortcode": item["shortcode"],
                                        "locale": item.get("locale"), "card": item.get("card"), "batch": batch,
                                        "text": item["text"], "verified": False}
        if save:
            save(state)   # the receipt is on disk before the read-back: a post is never commented twice
        try:
            after = LB.comments_count(client, mid)
            exists = LB.comment_exists(client, cid)
        except OP.ApiError as exc:   # throttled on the read-back: the receipt stays (unverified), stop the run
            receipt["readback"] = {"error": str(exc)[:120], "count_before": before}
            if save:
                save(state)
            row.update(status=f"commented_unverified: read-back throttled ({str(exc)[:80]})", comment_id=cid)
            log("::warning::ig_correction: throttle on the read-back; stopping")
            break
        receipt["verified"] = bool(cid and exists and (before is None or (after or 0) > before))
        receipt["readback"] = {"comment_found": exists, "count_before": before, "count_after": after}
        if save:
            save(state)
        row.update(status="commented" if receipt["verified"] else "commented_unverified", comment_id=cid)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "apply"])
    ap.add_argument("--batch", required=True)
    ap.add_argument("--max-new", type=int, default=8)
    a = ap.parse_args(argv)
    batch, items = load_batch(a.batch)
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        print("::error::ig_correction: IG_ACCESS_TOKEN not set")
        return 1
    client = OP.InstagramClient(token).me()
    state = load_state()
    rows = run(client, batch, items, state, apply=a.cmd == "apply", max_new=a.max_new,
               save=(lambda s: LB.save_state(s, STATE)) if a.cmd == "apply" else None)
    for r in rows:
        print(f"  {r['shortcode']} {r['locale']} {r['card']} {r['status']}" + (f" comment {r['comment_id']}" if r.get("comment_id") else ""))
    counts = {}
    for r in rows:
        k = r["status"].split(":")[0]
        counts[k] = counts.get(k, 0) + 1
    print(f"ig_correction {a.cmd}: {counts}")
    if a.cmd == "check":
        print("CHECK OK" if counts.get("ready", 0) + counts.get("done_before", 0) == len(rows) else "CHECK: see refused rows")
    bad = [r for r in rows if r["status"].startswith(("write_failed", "refused", "throttled", "commented_unverified"))]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
