#!/usr/bin/env python3
"""Daily performance loop for our Instagram and Threads clip / picture posts.

Reads insights of OUR OWN recent posts (IG: views, reach, likes, saves,
shares, comments; Threads: views, likes, replies, reposts), maps each post to
the app / locale / hook it promotes (own_posts.Catalog: clip-posts.json,
clips.json, app names on the promotion page) and writes
.github/growth/performance.json:

- posts:    one row per post with its latest metrics and score
- ranking:  apps / locales / hooks by average score
- boost:    app keys that perform best (read by the Growth Engine planner,
            shorts/scripts/schedule_posts.py, to move them earlier in
            PRIORITY; clip-replan.yml re-plans every day)
- demote:   the weakest apps (informational)

Missing insights permissions are logged and skipped; the run never fails on
them. clip_progress.py shows a "成效排行" top-5 / bottom-5 table from it.

    python3 post_performance.py            # IG_ACCESS_TOKEN / THREADS_TOKEN
"""
import datetime as dt
import json
import math
import os
import sys

from own_posts import GROWTH, ApiError, Catalog, InstagramClient, ThreadsClient, load_json

PERF = GROWTH / "performance.json"
MEDIA_LIMIT = 50
BOOST_MAX = 5
# Saves, shares and reposts say "I want this" far more than a passing view.
WEIGHTS = {"views": 1, "likes": 3, "replies": 5, "saves": 8, "shares": 8, "reposts": 8}


def score(metrics):
    return sum(w * metrics.get(k, 0) for k, w in WEIGHTS.items())


def collect(client, catalog, log=print):
    """(rows, status) for one platform; permission problems only change status."""
    try:
        client.me()
        media = client.media(limit=MEDIA_LIMIT)
    except ApiError as exc:
        log(f"{client.channel}: cannot list our posts, skipped ({exc})")
        return [], f"skipped: {exc.message[:80]}"
    rows = []
    for m in media:
        post = catalog.resolve(client.channel, m)
        if not post:
            continue
        try:
            metrics = client.insights(m["id"])
        except ApiError as exc:
            if exc.permission:
                log(f"{client.channel}: no insights permission, skipped ({exc})")
                return rows, "skipped: no insights permission"
            log(f"{client.channel}: insights of {m['id']} skipped ({exc})")
            continue
        rows.append({
            "channel": client.channel, "id": m["id"], "link": m.get("permalink"),
            "posted_at": (m.get("timestamp") or post.get("posted_at") or "")[:19],
            "app": post["app"], "locale": post["locale"], "hook": post["hook"],
            "clip": post.get("clip"), "kind": post["kind"],
            "metrics": metrics, "score": score(metrics),
        })
    return rows, f"ok: {len(rows)} posts"


def group(rows, key):
    out = {}
    for r in rows:
        k = key(r)
        g = out.setdefault(k, {"posts": 0, "views": 0, "engagement": 0, "score": 0})
        g["posts"] += 1
        g["views"] += r["metrics"].get("views", 0)
        g["engagement"] += sum(v for n, v in r["metrics"].items() if n not in ("views", "reach"))
        g["score"] += r["score"]
    ranked = []
    for k, g in out.items():
        g["avg_score"] = round(g["score"] / g["posts"], 1)
        ranked.append(dict(k if isinstance(k, dict) else {"key": k}, **g))
    ranked.sort(key=lambda g: (-g["avg_score"], -g["views"]))
    return ranked


def rank(rows):
    apps = group(rows, lambda r: r["app"])
    locales = group(rows, lambda r: r["locale"])
    hooks = group(rows, lambda r: (r["app"], r["locale"], r["hook"]))
    hooks = [dict({"app": h["key"][0], "locale": h["key"][1], "hook": h["key"][2]},
                  **{k: v for k, v in h.items() if k != "key"}) for h in hooks]
    return {"apps": apps, "locales": locales, "hooks": hooks}


def boost_lists(app_ranking):
    """Top third of apps (<= 5) to post earlier, bottom third as demote.
    Needs 3+ apps with data so one lucky post doesn't reorder everything."""
    n = len(app_ranking)
    if n < 3:
        return [], []
    k = min(BOOST_MAX, math.ceil(n / 3))
    keys = [a["key"] for a in app_ranking]
    return keys[:k], [x for x in keys[-k:] if x not in keys[:k]]


def merge(previous, fresh):
    """Keep older posts that dropped out of the API listing; refresh the rest."""
    rows = {(r["channel"], r["id"]): r for r in previous}
    rows.update({(r["channel"], r["id"]): r for r in fresh})
    return sorted(rows.values(), key=lambda r: (r.get("posted_at") or "", r["id"]))


def build(previous, fresh, sources, now):
    rows = merge(previous.get("posts", []), fresh)
    ranking = rank(rows)
    boost, demote = boost_lists(ranking["apps"])
    return {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("Insights of our own IG / Threads posts by .github/scripts/post_performance.py. "
                 "score = views + 3*likes + 5*replies + 8*(saves+shares+reposts). "
                 "boost = best apps, read by 00_GrowthEngine shorts/scripts/schedule_posts.py."),
        "sources": sources,
        "boost": boost,
        "demote": demote,
        "ranking": ranking,
        "posts": rows,
    }


def main():
    now = dt.datetime.now(dt.timezone.utc)
    catalog = Catalog()
    sources, fresh = {}, []
    for env, cls in (("IG_ACCESS_TOKEN", InstagramClient), ("THREADS_TOKEN", ThreadsClient)):
        token = os.environ.get(env, "").strip()
        if not token:
            sources[cls.channel] = "skipped: no token"
            continue
        try:
            rows, status = collect(cls(token), catalog)
        except (OSError, ValueError, KeyError) as exc:  # network trouble: log, keep going
            rows, status = [], f"skipped: {exc.__class__.__name__}"
        print(f"{cls.channel}: {status}")
        sources[cls.channel] = status
        fresh += rows
    previous = load_json(PERF, {})
    if not fresh and not previous.get("posts"):
        print("performance: no insights yet, nothing written")
        return 0
    data = build(previous, fresh, sources, now)
    PERF.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"performance: {len(data['posts'])} posts, boost {data['boost']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
