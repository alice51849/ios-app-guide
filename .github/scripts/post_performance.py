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
- hook_winners: best hook variant (search_caption.py a/b/c) per clip, per
            locale and overall, once each compared variant has enough posts;
            clip_posts / social_extra post the winner two days in three and
            schedule_posts.py copies it into clips.json as hook_best
- allocation: a channel whose median views over its last 14 posts stay under
            PERF_MIN_MEDIAN_VIEWS (default 20) drops to 1 clip a day; the freed
            slot goes to the best channel when its workflow has a spare slot
            (schedule_posts.py CHANNEL_SLOTS / SPARE_SLOTS)
- best_hours: per platform and market (locale), the UTC hour whose posts got
            the most views, once the platform has 20+ posts with insights;
            schedule_posts.py moves a market to that slot when the workflow
            has a cron there, the promotion page shows it either way

Missing insights permissions are logged and skipped; the run never fails on
them. clip_progress.py shows a "成效排行" top-5 / bottom-5 table from it.

    python3 post_performance.py            # IG_ACCESS_TOKEN / THREADS_TOKEN
"""
import datetime as dt
import json
import math
import os
import statistics
import sys

from own_posts import GROWTH, ApiError, Catalog, InstagramClient, ThreadsClient, load_json

PERF = GROWTH / "performance.json"
MEDIA_LIMIT = 50
BOOST_MAX = 5
WINDOW = 14  # last posts per channel the reallocation rule looks at
MIN_MEDIAN_VIEWS = 20  # default; PERF_MIN_MEDIAN_VIEWS overrides
TIMES_MIN_POSTS = 20  # posts a platform needs before its posting hours are compared
HOUR_MIN_POSTS = 2  # posts an hour needs to count in that comparison
VARIANT_MIN_POSTS = {"apps": 1, "locales": 3, "global": 5}  # per compared variant
CHANNEL_NAME = {"instagram": "Instagram", "threads": "Threads", "telegram": "Telegram"}
# Channels whose posting workflow has a spare clip slot (reels-daily.yml 09:20 UTC);
# mirrors SPARE_SLOTS in the Growth Engine's shorts/scripts/schedule_posts.py.
SPARE_CHANNELS = ("instagram",)
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
            "clip": post.get("clip"), "kind": post["kind"], "variant": post.get("variant"),
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
    variants = group([r for r in rows if r.get("variant")], lambda r: r["variant"])
    return {"apps": apps, "locales": locales, "hooks": hooks, "variants": variants}


def hook_winners(rows):
    """Best hook variant per clip, per locale and overall; a level only names a winner when 2+ variants
    each have VARIANT_MIN_POSTS posts there (a clip goes out once per channel, so per-clip data is thin)."""
    rows = [r for r in rows if r.get("variant") and r.get("kind") == "clip"]

    def best(subset, need):
        ranked = [g for g in group(subset, lambda r: r["variant"]) if g["posts"] >= need]
        return ranked[0]["key"] if len(ranked) >= 2 else None

    out = {"apps": {}, "locales": {}, "global": best(rows, VARIANT_MIN_POSTS["global"])}
    for level, key in (("apps", lambda r: r.get("clip") or f"{r['app']}/{r['locale']}"), ("locales", lambda r: r["locale"])):
        for k in sorted({key(r) for r in rows}):
            w = best([r for r in rows if key(r) == k], VARIANT_MIN_POSTS[level])
            if w:
                out[level][k] = w
    return out


def slot_of(posted_at):
    """Workflow slot (UTC hour 1 / 9 / 15) a post went out in."""
    try:
        hour = int(posted_at[11:13])
    except (TypeError, ValueError):
        return None
    return 1 if hour < 8 else 9 if hour < 12 else 15


def threshold():
    try:
        return float(os.environ.get("PERF_MIN_MEDIAN_VIEWS", "") or MIN_MEDIAN_VIEWS)
    except ValueError:
        return MIN_MEDIAN_VIEWS


def allocation(rows, limit=None, window=WINDOW):
    """Channel reallocation: median views of each channel's last `window` clip posts; a channel under
    `limit` drops to 1 post a day (keeping its better slot) and the best channel gets the freed slot."""
    limit = threshold() if limit is None else limit
    channels = {}
    for ch in sorted({r["channel"] for r in rows if r.get("kind") == "clip"}):
        last = sorted((r for r in rows if r["channel"] == ch and r.get("kind") == "clip"),
                      key=lambda r: r.get("posted_at") or "")[-window:]
        views = [r["metrics"].get("views", 0) for r in last]
        by_slot = {}
        for r in last:
            by_slot.setdefault(slot_of(r.get("posted_at")), []).append(r["metrics"].get("views", 0))
        keep = max((s for s in by_slot if s), key=lambda s: (statistics.median(by_slot[s]), -s), default=1)
        channels[ch] = {"posts": len(last), "median_views": statistics.median(views) if views else 0,
                        "keep_slot": keep, "daily": 2}
    full = {ch: c for ch, c in channels.items() if c["posts"] >= window}
    best = max(full, key=lambda ch: full[ch]["median_views"], default=None)
    reduced = [ch for ch, c in full.items() if c["median_views"] < limit and ch != best]
    for ch in reduced:
        channels[ch]["daily"] = 1
    name = lambda ch: CHANNEL_NAME.get(ch, ch)
    if reduced:
        decision = "；".join(f"{name(ch)} 近 {window} 則觀看中位數 {channels[ch]['median_views']:g}＜{limit:g} → 每天 1 則"
                            for ch in reduced)
        decision += (f"，空出的時段給 {name(best)}" if best in SPARE_CHANNELS
                     else f"；{name(best)} 表現最好但沒有空檔時段，只減量")
    elif full:
        decision = f"各通路近 {window} 則觀看中位數皆 ≥ {limit:g} 或已是最佳，維持每天 2 則"
    else:
        have = "、".join(f"{name(ch)} {c['posts']}" for ch, c in channels.items()) or "0"
        decision = f"等資料：每通路需 {window} 則有洞察的鉤子片（目前 {have}）"
    return {"threshold": limit, "window": window, "channels": channels, "best": best if reduced else None,
            "reduced": reduced, "decision": decision}


def best_hours(rows, need=TIMES_MIN_POSTS):
    """({channel: {locale: {hour, avg_views, posts, hours}}}, {channel: status}) from posting hours (UTC)."""
    out, status = {}, {}
    for ch in sorted({r["channel"] for r in rows}):
        mine = [r for r in rows if r["channel"] == ch and (r.get("posted_at") or "")[11:13].isdigit()]
        if len(mine) < need:
            status[ch] = f"{len(mine)}/{need} 則"
            continue
        for loc in sorted({r["locale"] for r in mine}):
            by_hour = {}
            for r in mine:
                if r["locale"] == loc:
                    by_hour.setdefault(int(r["posted_at"][11:13]), []).append(r["metrics"].get("views", 0))
            avg = {h: round(sum(v) / len(v), 1) for h, v in by_hour.items() if len(v) >= HOUR_MIN_POSTS}
            if len(avg) < 2:
                continue  # one hour only: nothing to compare yet
            hour = max(avg, key=lambda h: (avg[h], -h))
            out.setdefault(ch, {})[loc] = {"hour": hour, "avg_views": avg[hour],
                                           "posts": sum(len(v) for v in by_hour.values()),
                                           "hours": {str(h): a for h, a in sorted(avg.items())}}
        if ch not in out:
            status[ch] = "各市場只在單一時段發過，尚無可比較時段"
    return out, status


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
    hours, hours_status = best_hours(rows)
    return {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("Insights of our own IG / Threads posts by .github/scripts/post_performance.py. "
                 "score = views + 3*likes + 5*replies + 8*(saves+shares+reposts). "
                 "boost = best apps, read by 00_GrowthEngine shorts/scripts/schedule_posts.py."),
        "sources": sources,
        "boost": boost,
        "demote": demote,
        "hook_winners": hook_winners(rows),
        "allocation": allocation(rows),
        "best_hours": hours,
        "best_hours_status": hours_status,
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
