#!/usr/bin/env python3
"""Add the app's direct download link to our own Dev.to articles that have none (self-healing sweeper).

Owner rule (2026-10-17): every promo text carries the app's direct download link. A Dev.to article can be
edited, so unlike an Instagram caption the text itself is fixed: one short block with the App Store link
(plus the Google Play link when the app is on Android) is appended to the article body.

- audit: list our articles (published or not), resolve the app each one is about (link_backfill.AppFinder:
  several proofs must agree, else the article is only listed), report which have / lack the link.
- apply: append the block to the articles that lack any App Store link, newest first, a few per run, then read
  the article back and keep the receipt. An article is only ever edited once.

An article that links its App Store page but not the Google Play page of an app that is live on Android
(the Play link was only added to the rule afterwards) gets the missing Google Play link too, once: a single-app
article a closing block with both store links, a lineup of several apps the Google Play link at the end of each
app's own list line. An article that has every link it owes is left alone. The API key is read from the
environment and never printed.

    python3 devto_link_fix.py audit
    python3 devto_link_fix.py apply --max-new 3
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

import clip_posts as CP
import download_links as DL
import link_backfill as B
import own_posts as OP
from social_post_common import android_apps, campaign_app_store_url, play_store_url

API = "https://dev.to/api"
STATE = OP.GROWTH / "devto-link-fix.json"
REPORT = OP.GROWTH / "devto-link-fix-report.json"
CT = "bf_dv"
GAP = 10          # seconds between two edits
PAGES = 10        # 10 x 100 articles
UA = "lumi-devto-links/1.0"


def request(method, path, key, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
        "api-key": key, "Accept": "application/vnd.forem.api-v1+json", "Content-Type": "application/json",
        "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as exc:   # the reason, never the key
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}") from None


def my_articles(key, call=request, pages=PAGES):
    out = []
    for page in range(1, pages + 1):
        rows = call("GET", f"/articles/me/all?per_page=100&page={page}", key) or []
        out += rows
        if len(rows) < 100:
            break
    return out


def full_article(key, article_id, call=request):
    return call("GET", f"/articles/{article_id}", key) or {}


def link_block(locale, store, play):
    t = CP.text_for(locale or "en")
    parts = [f"[{t['button']}]({store})"]
    if play:
        label = CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get((locale or "en").split("-")[0]) or CP.PLAY_LINE["en"]
        parts.append(f"[{label}]({play})")
    return "\n\n---\n\n" + " | ".join(parts) + "\n"


def play_gaps(text, ios_ids):
    """{iOS id: Google Play URL} of the apps `text` links on the App Store that are live on Android but whose
    Google Play link is not in `text` (an unreadable Android snapshot raises ValueError: never half a decision)."""
    gaps = {}
    for ios in sorted(ios_ids):
        play = play_store_url(ios, CT)
        if play and not DL.has_play_link(text, play):
            gaps[ios] = play
    return gaps


def with_play_links(body, gaps, locale, ios_ids):
    """`body` with the Google Play link(s) of `gaps` ({iOS id: URL}) added. One app (the usual article): a closing
    block with both store links, like a fresh backfill, so a trailing "the App Store link:" has something under
    it. Several apps (a lineup): ' · [Google Play](url)' at the end of each app's own App Store list line, next
    to the link it belongs with; an app without such a line goes into a closing block."""
    if len(ios_ids) == 1:
        ios = next(iter(gaps))
        return body.rstrip() + link_block(locale, campaign_app_store_url(f"https://apps.apple.com/app/id{ios}", CT),
                                          gaps[ios])
    placed, lines = set(), []
    for line in body.split("\n"):
        for ios, play in gaps.items():
            if ios not in placed and "apps.apple.com" in line and f"/id{ios}" in line:
                line = f"{line.rstrip()} · [Google Play]({play})"
                placed.add(ios)
                break
        lines.append(line)
    text = "\n".join(lines)
    rest = [play for ios, play in gaps.items() if ios not in placed]
    if rest:
        label = CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get((locale or "en").split("-")[0]) or CP.PLAY_LINE["en"]
        text = text.rstrip() + "\n\n---\n\n" + " | ".join(f"[{label}]({play})" for play in rest) + "\n"
    return text


def classify(article, finder, state, key, call=request):
    """(row, todo): what this article is about and whether it already links its App Store page."""
    aid = str(article["id"])
    body = article.get("body_markdown")
    if body is None:
        body = full_article(key, aid, call).get("body_markdown") or ""
    text = f"{article.get('title', '')}\n{article.get('description', '')}\n{body}"
    row = {"channel": "devto", "id": aid, "permalink": article.get("url", ""),
           "date": (article.get("published_at") or article.get("created_at") or "")[:10], "app": "", "status": "",
           "text": " ".join(article.get("title", "").split())[:140]}
    if article.get("published") is False:   # a draft goes through the posting guards when it is published
        row["status"] = "draft_skipped"
        return row, None
    ids = DL.store_ids_in(text)
    if ids:   # it links an App Store page (the app it is about): only a Google Play link can still be missing
        gaps = play_gaps(text, ids)
        if not gaps:
            row["status"] = "ok_caption"
            return row, None
        row.update(app=",".join(gaps), ios_id=",".join(gaps))
        if state["done"].get("devto_play", {}).get(aid):
            row["status"] = "ok_backfilled_earlier"
            return row, None
        row.update(locale=OP.detect_language(text) or "en", status="missing_play")
        return row, {"kind": "play", "body": body, "gaps": gaps, "ids": sorted(ids)}
    post = finder.resolve("devto", {"id": aid, "permalink": article.get("url", ""), "caption": text})
    ios = B.ios_id_for(finder.catalog, post)
    row["app"], row["why"] = (post or {}).get("app", ""), (post or {}).get("why", "")
    if not ios:
        row["status"] = "unknown_app"
        return row, None
    if state["done"].get("devto", {}).get(aid):
        row["status"] = "ok_backfilled_earlier"
        return row, None
    store = campaign_app_store_url(f"https://apps.apple.com/app/id{ios}", CT)
    play = play_store_url(ios, CT)
    row.update(ios_id=ios, locale=(post or {}).get("locale") or OP.detect_language(text) or "en", status="missing")
    return row, {"kind": "store", "body": body, "store": store, "play": play}


def run(key, finder, state, *, apply=False, max_new=3, only=None, call=request, sleeper=time.sleep, gap=GAP,
        log=print, save=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        articles = my_articles(key, call)
    except Exception as exc:
        log(f"::warning::devto: listing our articles failed, skipped ({str(exc)[:100]})")
        return [{"channel": "devto", "id": "", "status": "list_failed"}]
    rows, attempts = [], 0
    for article in sorted(articles, key=lambda a: a.get("published_at") or a.get("created_at") or "", reverse=True):
        if only and str(article["id"]) not in only:
            continue
        if apply and attempts >= max_new:
            break
        try:
            row, todo = classify(article, finder, state, key, call)
        except Exception as exc:
            rows.append({"channel": "devto", "id": str(article.get("id")), "status": f"read_failed:{str(exc)[:40]}"})
            continue
        rows.append(row)
        if not todo or not apply:
            continue
        if not android_apps():   # the Play link could not be decided: never write half a link
            row["status"] = "snapshot_missing"
            log("::error::devto: the Android snapshot is empty; nothing is edited")
            break
        attempts += 1
        if todo["kind"] == "play":
            text = with_play_links(todo["body"], todo["gaps"], row["locale"], todo["ids"])
            done_key = "devto_play"
        else:
            text = todo["body"].rstrip() + link_block(row["locale"], todo["store"], todo["play"])
            done_key = "devto"
        try:
            call("PUT", f"/articles/{row['id']}", key, {"article": {"body_markdown": text}})
        except Exception as exc:
            row["status"] = "write_failed"
            row["error"] = str(exc)[:160]
            log(f"::warning::devto: editing article {row['id']} failed ({str(exc)[:100]}); stopping")
            break
        receipt = state["done"].setdefault(done_key, {})[row["id"]] = {
            "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "app": row["app"], "verified": False}
        if save:
            save(state)
        try:   # read it back: the article now holds the link
            after = full_article(key, row["id"], call).get("body_markdown") or ""
            if todo["kind"] == "play":
                receipt["verified"] = all(DL.has_play_link(after, play) for play in todo["gaps"].values())
            else:
                receipt["verified"] = DL.has_download_link(after, todo["store"], todo["play"])
        except Exception as exc:
            log(f"::warning::devto: read-back of article {row['id']} failed ({str(exc)[:100]})")
        if save:
            save(state)
        row["status"] = "backfilled" if receipt["verified"] else "backfilled_unverified"
        log(f"devto: link added to article {row['id']} ({row['app']}) verified={receipt['verified']}")
        sleeper(gap)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit", "apply"])
    ap.add_argument("--max-new", type=int, default=3)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)
    key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not key:
        print("devto_link_fix: DEVTO_API_KEY not set, skipped")
        return 0
    if not android_apps():
        print("::error::devto_link_fix: the Android snapshot is empty or unreadable; the Play link cannot be decided, stopping")
        return 1
    apply = args.cmd == "apply"
    state = B.load_state(STATE)
    rows = run(key, B.AppFinder(OP.Catalog()), state, apply=apply, max_new=args.max_new,
               only=set(args.only) if args.only else None, save=lambda st: B.save_state(st, STATE))
    previous = (OP.load_json(args.report, {}) or {}).get("rows", [])
    full_scan = not apply and not args.only
    merged = rows if full_scan else B.merge_rows(previous, rows)
    counts = B.summarize(merged)
    if full_scan or merged != previous:   # a sweep that found nothing new leaves the report (and git) alone
        report = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": args.cmd,
                  "counts": counts, "rows": merged}
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    B.save_state(state, STATE)
    print(f"devto_link_fix {args.cmd}: {counts}")
    for r in rows:
        if r["status"] in ("missing", "missing_play", "unknown_app") or r["status"].startswith(("write_failed", "backfilled_unverified")):
            print(f"  devto {r['id']} {r.get('date', '')} {r.get('app', '')} {r['status']} {r.get('text', '')[:60]}")
    return 1 if any(r["status"].startswith("write_failed") or r["status"] == "snapshot_missing" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
