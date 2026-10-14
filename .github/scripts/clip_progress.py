#!/usr/bin/env python3
"""Keep the hook-clip section of the promotion page current.

office.cait518.cc renders .github/growth/app-improvements.json; its
summary_md carries one section, "## 鉤子片影片：各社群連結與進度", that
lists every channel's progress and every clip's links. This script rebuilds
that section from:

- .github/growth/clips.json       clips uploaded so far and the posting schedule
- .github/growth/clip-posts.json  what actually went out, with post links
                                  (appended by clip_posts.py after each post)

Run it after the schedule changes or after a post:

    python3 .github/scripts/clip_progress.py
"""
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROWTH = HERE.parent / "growth"
CLIPS = GROWTH / "clips.json"
POSTS = GROWTH / "clip-posts.json"
IMPROVEMENTS = GROWTH / "app-improvements.json"

HEADING = "## 鉤子片影片：各社群連結與進度"
PAGE_TITLE = "# 外宣成效"
TW = dt.timezone(dt.timedelta(hours=8))
# Cron slots (UTC hour) of the posting workflows.
SLOT_TIME = {"telegram": {1: "01:00", 15: "15:00"}, "instagram": {1: "01:20", 15: "15:20"},
             "threads": {1: "01:40", 15: "15:40"}}
CHANNEL_NAME = {"telegram": "Telegram", "instagram": "Instagram", "threads": "Threads"}
# Channels without automation yet: what is true today, shown as-is.
MANUAL_CHANNELS = [
    ("YouTube Shorts", "本機上傳"),
    ("TikTok", "手動"),
]


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def tw_time(date, slot, channel):
    hhmm = SLOT_TIME.get(channel, {}).get(slot, f"{slot:02d}:00")
    utc = dt.datetime.fromisoformat(f"{date}T{hhmm}:00+00:00")
    return utc.astimezone(TW).strftime("%m/%d %H:%M")


def app_names(improvements):
    return {a["key"]: a.get("name", a["key"]) for a in improvements.get("apps", [])}


def build_section(clips, posts, names, now, hook_total=None, notes=(), android=None):
    """Compact, one-screen markdown for the promotion page (heading included)."""
    android = android or {}
    clip_map = clips.get("clips", {})
    schedule = clips.get("schedule", [])
    posted = {(p["channel"], p["clip"]): p for p in posts}
    today = now.date().isoformat()
    apps = sorted({c["app"] for c in clip_map.values()})
    total = f"／{hook_total}" if hook_total else ""
    lines = [HEADING, "", f"更新 {now.astimezone(TW).strftime('%m/%d %H:%M')}（台灣）", ""]
    lines += ["| 項目 | 數字 |", "|---|---|",
              f"| 鉤子片已上傳 | {len(apps)}{total} 款 · {len(clip_map)} 支 |",
              f"| 已排程 | {len(schedule)} 則（到 {schedule[-1]['date'][5:].replace('-', '/') if schedule else '—'}） |",
              f"| 已發出 | {len(posts)} 則 |",
              f"| Android 已上架 | {len(android)} 款（貼文自動附 Google Play） |"]
    lines += [f"| 備註 | {n} |" for n in notes]
    lines += ["", "| 平台 | 狀態 | 已發 | 下一則 |", "|---|---|---|---|"]
    for channel in ("telegram", "instagram", "threads"):
        entries = [e for e in schedule if e["channel"] == channel]
        done = sum(1 for p in posts if p["channel"] == channel)
        upcoming = [e for e in entries if (channel, e["clip"]) not in posted and e["date"] >= today]
        state = "自動 2 支／天" if entries else "等待中"
        nxt = "—"
        if upcoming:
            e = upcoming[0]
            c = clip_map.get(e["clip"], {})
            nxt = f"{tw_time(e['date'], e['slot'], channel)} {names.get(c.get('app'), c.get('app', ''))}"
        lines.append(f"| {CHANNEL_NAME[channel]} | {state} | {done} | {nxt} |")
    for name, state in MANUAL_CHANNELS:
        lines.append(f"| {name} | {state} | — | — |")
    lines += ["", "| App | 影片 | 已發 |", "|---|---|---|"]
    for app in sorted(apps, key=lambda a: names.get(a, a)):
        keys = sorted(k for k, c in clip_map.items() if c["app"] == app)
        vids = " ".join(f"[{clip_map[k]['locale']}]({clip_map[k]['url']})" for k in keys)
        sent = []
        for k in keys:
            for ch in ("telegram", "instagram", "threads"):
                p = posted.get((ch, k))
                if p and p.get("link"):
                    sent.append(f"[{CHANNEL_NAME[ch][0]}]({p['link']})")
        mark = " 🤖" if app in android else ""
        lines.append(f"| {names.get(app, app)}{mark} | {vids} | {' '.join(sent) or '—'} |")
    return "\n".join(lines)


def replace_section(summary, section):
    """Swap the section in summary_md (or append it), keeping everything else."""
    start = summary.find(HEADING)
    if start < 0:
        return summary.rstrip() + "\n\n" + section + "\n"
    end = summary.find("\n## ", start + len(HEADING))
    tail = summary[end:] if end >= 0 else "\n"
    return summary[:start] + section + "\n" + tail


def hook_total(improvements):
    return sum(1 for a in improvements.get("apps", []) for x in a.get("actions", [])
               if x.get("id", "").endswith("-hook7"))


def update_hook_cards(improvements, clips, posts, now):
    """Keep each app's "<key>-hook7" card on the page in step with clips.json."""
    import re
    clip_map = clips.get("clips", {})
    schedule = clips.get("schedule", [])
    posted = {(p["channel"], p["clip"]) for p in posts}
    today = now.date().isoformat()
    for app in improvements.get("apps", []):
        for action in app.get("actions", []):
            if action.get("id") != f"{app['key']}-hook7":
                continue
            have = sorted(c["locale"] for c in clip_map.values() if c["app"] == app["key"])
            if not have:
                continue
            m = re.search(r"：(.+?)）", action.get("title", ""))
            wanted = [x.strip() for x in m.group(1).split("、")] if m else have
            nxt = [e for e in schedule if e["clip"].startswith(app["key"] + "/")
                   and (e["channel"], e["clip"]) not in posted and e["date"] >= today]
            sent = sum(1 for p in posts if p["clip"].startswith(app["key"] + "/"))
            parts = [f"已上傳 {len([x for x in wanted if x in have])}/{len(wanted)} 語"]
            if nxt:
                e = nxt[0]
                parts.append(f"下一則 {CHANNEL_NAME[e['channel']]} {tw_time(e['date'], e['slot'], e['channel'])}")
            parts.append(f"已發 {sent} 則")
            action["detail"] = "；".join(parts)
            if set(wanted) <= set(have):
                if action.get("status") != "done":
                    action["status"] = "done"
                    action["done_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                action["status"] = "in_progress"
                action.pop("done_at", None)


def update(now=None, notes=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    improvements = load_json(IMPROVEMENTS, {})
    clips = load_json(CLIPS, {})
    posts = load_json(POSTS, {}).get("posts", [])
    if notes is None:
        notes = load_json(POSTS, {}).get("notes", [])
    from social_post_common import android_apps
    android = {e["key"]: e["play_url"] for e in android_apps().values()}
    section = build_section(clips, posts, app_names(improvements), now, hook_total(improvements), notes, android)
    update_hook_cards(improvements, clips, posts, now)
    # The page shows one screen: title + this section. Older narrative lives in
    # .github/growth/app-improvements-archive.json.
    improvements["summary_md"] = PAGE_TITLE + "\n\n" + section + "\n"
    improvements["updated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    IMPROVEMENTS.write_text(json.dumps(improvements, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_post(channel, key, link, now=None):
    """Append one post to clip-posts.json and refresh the page section."""
    now = now or dt.datetime.now(dt.timezone.utc)
    log = load_json(POSTS, {"posts": [], "notes": []})
    log.setdefault("posts", []).append({
        "channel": channel, "clip": key, "link": link,
        "posted_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    POSTS.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    update(now)


def merge_log(path):
    """Fold a saved clip-posts.json (from before a rebase) into the current one."""
    mine = load_json(Path(path), {}).get("posts", [])
    log = load_json(POSTS, {"posts": [], "notes": []})
    seen = {(p["channel"], p["clip"], p["posted_at"]) for p in log.get("posts", [])}
    log.setdefault("posts", []).extend(p for p in mine if (p["channel"], p["clip"], p["posted_at"]) not in seen)
    log["posts"].sort(key=lambda p: p["posted_at"])
    POSTS.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge-log", help="clip-posts.json saved before resetting to origin/main")
    args = ap.parse_args()
    if args.merge_log:
        merge_log(args.merge_log)
    update()
