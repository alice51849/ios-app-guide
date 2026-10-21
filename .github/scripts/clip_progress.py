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
PERFORMANCE = GROWTH / "performance.json"  # written daily by post_performance.py

HEADING = "## 鉤子片影片：各社群連結與進度"
PERF_HEADING = "## 成效排行"
PAGE_TITLE = "# 外宣成效"
TW = dt.timezone(dt.timedelta(hours=8))
# Cron slots (UTC hour) of the posting workflows.
SLOT_TIME = {"telegram": {1: "01:00", 9: "09:00", 12: "12:30", 15: "15:00", 18: "18:30", 22: "22:30"},
             "instagram": {1: "01:20", 9: "09:20", 12: "12:20", 15: "15:20", 18: "18:20", 22: "22:20"},
             "threads": {1: "01:40", 15: "15:40"}}
CHANNEL_NAME = {"telegram": "Telegram", "instagram": "Instagram", "threads": "Threads"}
# Daily utility cards share the post log under this key prefix.
UTILITY_PREFIX = "utility/"
UTILITY_LABEL = {"telegram": "TG", "instagram": "IG", "threads": "Th"}
UTILITY_TYPE = {"word": "英文單字", "zhuyin": "注音", "photo": "證件照尺寸", "letter": "今日字母", "count": "今日數一數",
                "bedtime": "睡前 5 步", "ledger": "專案損益算式", "chore": "上次做是幾天前",
                "checklist": "今日 4 件事清單"}
# Channels without automation yet: what is true today, shown as-is.
MANUAL_CHANNELS = [
    ("TikTok", "手動"),
]
# Platforms another repo posts from social_extra.py's feed (social-feed branch),
# because those accounts' secrets live there; their posts are not logged here.
# Bluesky and YouTube Shorts are back on since the owner's 2026-10-14 decision
# (threads-autopilot channels_enabled.json / 00_GrowthEngine shorts/channels_enabled.json;
# a repo variable set to "off" still stops them). The Mac's YouTube uploads come in
# through youtube_links.py (clip-replan.yml), so their links show per clip.
# Mastodon stays locked (account suspended, stop-loss).
SERVED_ELSEWHERE = {"bluesky": "自動（threads-autopilot，媒體每天 2→5 則爬坡）", "youtube": "自動（Mac，每天 2→4 支爬坡）"}
SERVED_ROWS = [("Mastodon", "停權冷卻（鎖定）")]
# Platforms posted by social_extra.py (social-extra.yml): "未設定" until the first post.
EXTRA_CHANNELS = {"instagram_feed": ("Instagram 圖文輪播", "IGf"),
                  "facebook": ("Facebook", "FB"), "bluesky": ("Bluesky", "Bs"), "youtube": ("YouTube Shorts", "YT"),
                  "pinterest": ("Pinterest", "Pin"), "tumblr": ("Tumblr", "Tb"), "naver": ("Naver Blog", "Nv"),
                  "plurk": ("Plurk", "Pk"), "dailymotion": ("Dailymotion", "DM")}


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def tw_time(date, slot, channel):
    hhmm = SLOT_TIME.get(channel, {}).get(slot, f"{slot:02d}:00")
    utc = dt.datetime.fromisoformat(f"{date}T{hhmm}:00+00:00")
    return utc.astimezone(TW).strftime("%m/%d %H:%M")


def app_names(improvements):
    return {a["key"]: a.get("name", a["key"]) for a in improvements.get("apps", [])}


def build_section(clips, posts, names, now, hook_total=None, notes=(), android=None, allocation=None):
    """Compact, one-screen markdown for the promotion page (heading included)."""
    android = android or {}
    daily = {ch: info.get("daily") for ch, info in ((allocation or {}).get("channels") or {}).items()}
    utility = [p for p in posts if p["clip"].startswith(UTILITY_PREFIX)]
    posts = [p for p in posts if not p["clip"].startswith(UTILITY_PREFIX)]
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
    lines.append(utility_row(utility))
    lines += [f"| 備註 | {n} |" for n in notes]
    lines += ["", "| 平台 | 狀態 | 已發 | 下一則 |", "|---|---|---|---|"]
    for channel in ("telegram", "instagram", "threads"):
        entries = [e for e in schedule if e["channel"] == channel]
        done = sum(1 for p in posts if p["channel"] == channel)
        upcoming = [e for e in entries if (channel, e["clip"]) not in posted and e["date"] >= today]
        state = f"自動 {daily.get(channel) or 2} 支／天" if entries else "等待中"
        nxt = "—"
        if upcoming:
            e = upcoming[0]
            c = clip_map.get(e["clip"], {})
            nxt = f"{tw_time(e['date'], e['slot'], channel)} {names.get(c.get('app'), c.get('app', ''))}"
        lines.append(f"| {CHANNEL_NAME[channel]} | {state} | {done} | {nxt} |")
    for channel, (name, _) in EXTRA_CHANNELS.items():
        done = sum(1 for p in posts + utility if p["channel"] == channel)
        state = "自動" if done else SERVED_ELSEWHERE.get(channel, "未設定")
        lines.append(f"| {name} | {state} | {done or '—'} | — |")
    for name, state in SERVED_ROWS + MANUAL_CHANNELS:
        lines.append(f"| {name} | {state} | — | — |")
    lines += ["", "| App | 影片 | 已發 |", "|---|---|---|"]
    for app in sorted(apps, key=lambda a: names.get(a, a)):
        keys = sorted(k for k, c in clip_map.items() if c["app"] == app)
        vids = " ".join(f"[{clip_map[k]['locale']}]({clip_map[k]['url']})" for k in keys)
        sent = []
        for k in keys:
            for ch in ("telegram", "instagram", "threads", *EXTRA_CHANNELS):
                p = posted.get((ch, k))
                if p and p.get("link") and not p.get("taken_down"):   # a taken-down post's link is not shown
                    label = EXTRA_CHANNELS[ch][1] if ch in EXTRA_CHANNELS else CHANNEL_NAME[ch][0]
                    sent.append(f"[{label}]({p['link']})")
        mark = " 🤖" if app in android else ""
        lines.append(f"| {names.get(app, app)}{mark} | {vids} | {' '.join(sent) or '—'} |")
    return "\n".join(lines)


def build_performance(perf, names, top=5):
    """Compact top-5 / bottom-5 hooks by score (empty when no insights yet)."""
    hooks = perf.get("ranking", {}).get("hooks", [])
    if not hooks:
        return ""
    lines = [PERF_HEADING, "", f"更新 {perf.get('updated_at', '')[5:10].replace('-', '/')} · "
             "分數＝觀看＋3×讚＋5×留言＋8×（收藏＋分享＋轉發）", "",
             "| # | App | 語言 | 鉤子 | 觀看 | 分數 |", "|---|---|---|---|---|---|"]
    shown = list(enumerate(hooks[:top], 1))
    shown += [(i, h) for i, h in enumerate(hooks, 1) if i > max(top, len(hooks) - top)]
    for i, h in shown:
        hook = h.get("hook", "")
        hook = hook if len(hook) <= 18 else hook[:17] + "…"
        lines.append(f"| {i} | {names.get(h['app'], h['app'])} | {h['locale']} | {hook} | {h['views']} | {h['avg_score']:g} |")
    if perf.get("boost"):
        lines.append(f"\n加碼排程：{'、'.join(names.get(a, a) for a in perf['boost'])}")
    for line in (variant_line(perf), allocation_line(perf), hours_line(perf)):
        if line:
            lines.append(f"\n{line}")
    skipped = [f"{CHANNEL_NAME.get(c, c)} {s.split(': ', 1)[-1]}" for c, s in perf.get("sources", {}).items()
               if s.startswith("skipped") and "no token" not in s]
    if skipped:
        lines.append(f"\n洞察未取得：{'；'.join(skipped)}")
    return "\n".join(lines)


VARIANT_NAME = {"a": "問題開頭", "b": "好處開頭", "c": "功能開頭"}


def variant_line(perf):
    """One line: average score per hook variant (post_performance.py ranking.variants)."""
    rows = (perf.get("ranking") or {}).get("variants") or []
    rows = [r for r in rows if r.get("key")]
    if not rows:
        return ""
    best = (perf.get("hook_winners") or {}).get("global")
    parts = [f"{r['key']} {VARIANT_NAME.get(r['key'], '')} {r['avg_score']:g}（{r['posts']} 則）" for r in rows]
    return "鉤子版本：" + " · ".join(parts) + (f"；目前優先 {best}" if best else "")


def allocation_line(perf):
    """One line: the channel reallocation decision (post_performance.py allocation)."""
    alloc = perf.get("allocation") or {}
    return f"通路調整：{alloc['decision']}" if alloc.get("decision") else ""


def hours_line(perf):
    """One line: recommended posting hour per platform and market (Taiwan time), or what is still missing."""
    hours = perf.get("best_hours") or {}
    parts = []
    for ch, markets in hours.items():
        if not isinstance(markets, dict):
            continue
        for loc, rec in sorted(markets.items()):
            if isinstance(rec, dict) and rec.get("hour") is not None:
                tw = (rec["hour"] + 8) % 24
                parts.append(f"{CHANNEL_NAME.get(ch, ch)} {loc} {tw:02d}:00")
    status = perf.get("best_hours_status") or {}
    if parts:
        return "建議時段（台灣）：" + "、".join(parts)
    waiting = [f"{CHANNEL_NAME.get(c, c)} {s}" for c, s in status.items()]
    return "建議時段：" + "；".join(waiting) if waiting else ""


def utility_row(utility):
    """One summary row for the daily utility cards (utility_cards.py): count + latest links."""
    latest = ""
    if utility:
        day = utility[-1]["posted_at"][:10]
        links = [f"[{UTILITY_LABEL.get(p['channel'], p['channel'])}]({p['link']})"
                 for p in utility if p["posted_at"][:10] == day and p.get("link")]
        latest = f" · 最新 {day[5:].replace('-', '/')} {UTILITY_TYPE.get(utility[-1]['clip'].split('/')[1], '')}" + (f" {' '.join(links)}" if links else "")
    return f"| 每日實用卡 | 已發 {len(utility)} 則{latest} |"


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
    posted = {(p["channel"], p["clip"]) for p in posts if not p.get("taken_down")}   # a taken-down cut can go out again
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
    perf_data = load_json(PERFORMANCE, {})
    section = build_section(clips, posts, app_names(improvements), now, hook_total(improvements), notes, android,
                            perf_data.get("allocation"))
    update_hook_cards(improvements, clips, posts, now)
    # The page shows one screen: title + this section. Older narrative lives in
    # .github/growth/app-improvements-archive.json.
    perf = build_performance(perf_data, app_names(improvements))
    improvements["summary_md"] = PAGE_TITLE + "\n\n" + section + "\n" + (f"\n{perf}\n" if perf else "")
    improvements["updated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    IMPROVEMENTS.write_text(json.dumps(improvements, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_post(channel, key, link, now=None, media_id=None, variant=None, ig_trial=None):
    """Append one post to clip-posts.json and refresh the page section."""
    now = now or dt.datetime.now(dt.timezone.utc)
    log = load_json(POSTS, {"posts": [], "notes": []})
    entry = {"channel": channel, "clip": key, "link": link, "posted_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
    if media_id:  # post_performance.py reads insights by this id
        entry["id"] = str(media_id)
    if variant:  # hook variant (search_caption.choose), ranked by post_performance.py
        entry["variant"] = variant
    if ig_trial:  # Trial Reel try (clip_posts.trial_plan): {"graduation_strategy", "result": trial|fallback, ...}
        entry["ig_trial"] = ig_trial
    log.setdefault("posts", []).append(entry)
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


def section_body(summary_md):
    """The hook-clip section and everything after it, minus its timestamp line.

    android-promo-sync.yml compares this before and after a refresh, so a run
    that only moves the "更新 …（台灣）" clock commits nothing. Accepts the
    current "更新 10/15 13:47" line and the older "更新：…" form; returns ""
    when the page has no hook section yet (so the first refresh always lands).
    """
    marker = HEADING.split("：")[0]  # "## 鉤子片影片"
    if marker not in summary_md:
        return ""
    rest = summary_md.split(marker, 1)[1]
    lines = rest.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("更新"):
            del lines[i]
            break
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge-log", help="clip-posts.json saved before resetting to origin/main")
    ap.add_argument("--print-section-body", action="store_true",
                    help="print the hook section without its timestamp line, change nothing")
    args = ap.parse_args()
    if args.print_section_body:
        print(section_body(load_json(IMPROVEMENTS, {}).get("summary_md", "")))
        raise SystemExit(0)
    if args.merge_log:
        merge_log(args.merge_log)
    update()
