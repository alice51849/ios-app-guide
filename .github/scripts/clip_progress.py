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
TW = dt.timezone(dt.timedelta(hours=8))
# Cron slots (UTC hour) of the posting workflows.
SLOT_TIME = {"telegram": {1: "01:00", 15: "15:00"}, "instagram": {1: "01:20", 15: "15:20"},
             "threads": {1: "01:40", 15: "15:40"}}
CHANNEL_NAME = {"telegram": "Telegram", "instagram": "Instagram", "threads": "Threads"}
# Channels without automation yet: what is true today, shown as-is.
MANUAL_CHANNELS = [
    ("YouTube Shorts", "Mac 本機上傳（本機待辦「7 秒鉤子片」第 4 步，每天最多 3 支）；上傳後的網址在本機回報"),
    ("Bluesky", "尚未設定（帳號與金鑰都沒有）"),
    ("TikTok", "手動配熱門音樂；無聲版在 Mac 的 shorts/out/，尚未上傳"),
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
    """Markdown for the hook-clip section (heading included).

    android: {app_key: Google Play URL}; posts link both stores when present.
    """
    android = android or {}
    clip_map = clips.get("clips", {})
    schedule = clips.get("schedule", [])
    posted = {(p["channel"], p["clip"]): p for p in posts}
    today = now.date().isoformat()

    lines = [HEADING, "", f"更新：{now.astimezone(TW).strftime('%Y-%m-%d %H:%M')}（台灣）", ""]
    apps = sorted({c["app"] for c in clip_map.values()})
    total = f"／{hook_total} 款" if hook_total else ""
    lines.append(f"- 已上傳：{len(apps)} 款{total}、{len(clip_map)} 支影片。")
    if android:
        listed = "、".join(sorted(names.get(k, k) for k in android))
        lines.append(f"- Android：{len(android)} 款已在 Google Play 上線（{listed}）。"
                     "Mac 每 30 分鐘掃一次 Google Play，新上架的 App 自動加進所有宣傳："
                     "Telegram／Threads 貼文加 Google Play 連結、鉤子片 Telegram 加 Google Play 按鈕、IG 文案註明、"
                     "新渲染的影片結尾寫「App Store／Google Play 搜尋」、官網頁面加 Google Play 按鈕。")
    lines += [f"- {n}" for n in notes]
    lines += ["", "| 平台 | 進度 | 已發 | 下一支（台灣時間） |", "|---|---|---|---|"]
    for channel in ("telegram", "instagram", "threads"):
        entries = [e for e in schedule if e["channel"] == channel]
        done = [p for p in posts if p["channel"] == channel]
        upcoming = [e for e in entries if (channel, e["clip"]) not in posted and e["date"] >= today]
        if channel == "instagram" and not entries:
            state = "等 IG_ACCESS_TOKEN 設好才開始"
        elif channel == "instagram":
            state = "自動，前兩週每天 1 支，之後每天 2 支"
        elif channel == "threads" and not entries:
            state = "準備中（確認帳號後開始）"
        elif channel == "threads":
            state = "自動，每天 1 支影片（連結放留言）＋ 2 則圖文"
        else:
            state = "自動，每天 1 支（影片＋App Store 下載按鈕）"
        nxt = "—"
        if upcoming:
            e = upcoming[0]
            c = clip_map.get(e["clip"], {})
            nxt = f"{tw_time(e['date'], e['slot'], channel)} {names.get(c.get('app'), c.get('app', ''))} {c.get('locale', '')}"
        lines.append(f"| {CHANNEL_NAME[channel]} | {state}；已排 {len(entries)} 支 | {len(done)} | {nxt} |")
    for name, state in MANUAL_CHANNELS:
        lines.append(f"| {name} | {state} | — | — |")

    lines += ["", "| App | 語言 | 影片 | Telegram | Instagram | Threads | Android |", "|---|---|---|---|---|---|---|"]

    def cell(channel, key):
        p = posted.get((channel, key))
        if p:
            when = p["posted_at"][5:10].replace("-", "/")
            return f"[已發 {when}]({p['link']})" if p.get("link") else f"已發 {when}"
        for e in schedule:
            if e["channel"] == channel and e["clip"] == key:
                return f"排定 {tw_time(e['date'], e['slot'], channel)}"
        return "—"

    for key in sorted(clip_map, key=lambda k: (names.get(clip_map[k]["app"], k), k)):
        c = clip_map[key]
        play = android.get(c["app"])
        lines.append(f"| {names.get(c['app'], c['app'])} | {c['locale']} | [影片]({c['url']}) | "
                     f"{cell('telegram', key)} | {cell('instagram', key)} | {cell('threads', key)} | "
                     f"{f'[Google Play]({play})' if play else '尚未上架'} |")
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
            parts = [f"已上傳 {len([x for x in wanted if x in have])}/{len(wanted)} 語（{'、'.join(have)}）"]
            if nxt:
                e = nxt[0]
                parts.append(f"下一則 {CHANNEL_NAME[e['channel']]} {tw_time(e['date'], e['slot'], e['channel'])}"
                             f"（{e['clip'].split('/')[1]}）")
            parts.append(f"已發 {sent} 則")
            action["detail"] = "；".join(parts) + "。影片與貼文連結見總覽「鉤子片影片：各社群連結與進度」。"
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
    improvements["summary_md"] = replace_section(improvements.get("summary_md", ""), section)
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
