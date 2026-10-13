#!/usr/bin/env python3
"""Put today's three ready-to-post Threads posts on the office promotion page.

Zero LLM tokens. It only chooses among posts that were already reviewed:
the chart-push kit of a focus App while its window is open, then
.github/growth/app-posts.json, favouring Apps the latest growth scoreboard
shows closest to #1. Each pick becomes an owner action (oa-today-1..3) in
app-improvements.json whose link opens the Threads composer with the text and a
tracked App Store link already filled in, so posting is one tap.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import growth_scoreboard  # noqa: E402
import portfolio_daily  # noqa: E402

GROWTH_DIR = HERE.parent / "growth"
IMPROVEMENTS = GROWTH_DIR / "app-improvements.json"
PROVIDER_TOKEN = "118326163"
THREADS_LIMIT = 500
PICKS = 3
PICK_PREFIX = "oa-today-"
LINK_PHRASES = ("連結放留言。", "連結在留言。", "App Store 連結放在留言。")


def store_link(app_id, ct, lang):
    country = "tw/" if lang == "zh-Hant" else ""
    return f"https://apps.apple.com/{country}app/id{app_id}?pt={PROVIDER_TOKEN}&ct={ct}&mt=8"


def compose(text, link):
    body = text.strip()
    for phrase in LINK_PHRASES:
        body = body.replace(phrase, "")
    body = body.rstrip()
    full = f"{body}\n\nApp Store：{link}"
    return full if len(full) <= THREADS_LIMIT else None


def focus_candidates(today, growth_dir=GROWTH_DIR):
    """Threads posts from the push kit of each focus App still in its window."""
    path = Path(growth_dir) / "focus.json"
    if not path.is_file():
        return []
    focus = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in focus.get("apps") or []:
        if str(row.get("spotlight_until") or "") < today.isoformat():
            continue
        kit = Path(growth_dir) / "drafts" / str(row.get("key") or "") / "push-kit.json"
        if not kit.is_file():
            continue
        data = json.loads(kit.read_text(encoding="utf-8"))
        for post in data.get("posts") or []:
            # Her Threads audience is in Taiwan, so only the Taiwan-voiced posts rotate here.
            if post.get("channel") == "threads" and post.get("market") == "tw":
                out.append({"app_id": str(data.get("app_id") or row.get("app_id")),
                            "lang": post.get("lang", "zh-Hant"), "ct": post["ct"],
                            "text": post["text"]})
    return out


def post_candidates(live_ids, growth_dir=GROWTH_DIR):
    path = Path(growth_dir) / "app-posts.json"
    if not path.is_file():
        return []
    posts = json.loads(path.read_text(encoding="utf-8")).get("posts") or []
    return [
        {"app_id": str(p.get("app_id")), "lang": p.get("lang"), "ct": p.get("ct"), "text": p.get("text", "")}
        for p in posts
        if str(p.get("app_id")) in live_ids and p.get("ct") and p.get("lang") in ("zh-Hant", "en")
        and "http" not in p.get("text", "")
    ]


def priority_apps(state):
    """App IDs ordered by how close the scoreboard says they are to #1."""
    if not state:
        return []
    order = []
    for _, entry, _ in growth_scoreboard.opportunities(state, {}, limit=60):
        if entry["app_id"] not in order:
            order.append(entry["app_id"])
    return order


def choose(today, live_ids, state, growth_dir=GROWTH_DIR):
    """Up to three (candidate, composed_text) pairs, one App each."""
    day = today.toordinal()
    picks, used_apps = [], set()

    def take(candidates):
        for offset in range(len(candidates)):
            candidate = candidates[(day + offset) % len(candidates)]
            if candidate["app_id"] in used_apps:
                continue
            text = compose(candidate["text"], store_link(candidate["app_id"], candidate["ct"], candidate["lang"]))
            if text:
                used_apps.add(candidate["app_id"])
                picks.append((candidate, text))
                return True
        return False

    focus = [c for c in focus_candidates(today, growth_dir) if c["app_id"] in live_ids]
    if focus:
        take(focus)
    pool = post_candidates(live_ids, growth_dir)
    for app_id in priority_apps(state):
        if len(picks) >= PICKS:
            break
        mine = [c for c in pool if c["app_id"] == app_id]
        # The owner's Threads audience reads Traditional Chinese first.
        mine = [c for c in mine if c["lang"] == "zh-Hant"] or mine
        if mine:
            take(mine)
    while len(picks) < PICKS and pool:
        if not take([c for c in pool if c["app_id"] not in used_apps]):
            break
    return picks


def apply(document, picks, names, now):
    actions = [a for a in document.get("owner_actions", []) if not str(a.get("id", "")).startswith(PICK_PREFIX)]
    fresh = []
    for index, (candidate, text) in enumerate(picks, start=1):
        fresh.append({
            "id": f"{PICK_PREFIX}{index}",
            "title": f"今天發這則（{index}/{len(picks)}）：{names.get(candidate['app_id'], candidate['app_id'])}",
            "url": "https://www.threads.net/intent/post?text=" + urllib.parse.quote(text),
            "how": "按連結開 Threads，內容和追蹤連結都已填好，按「發佈」就好。每天自動換新的 3 則。",
            "status": "todo",
        })
    document["owner_actions"] = fresh + actions
    document["updated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, help="growth scoreboard state.json")
    parser.add_argument("--improvements", type=Path, default=IMPROVEMENTS)
    args = parser.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    apps = portfolio_daily.load_public_apps()
    names = {app.app_id: app.name for app in apps}
    state = None
    if args.state and args.state.is_file():
        state = growth_scoreboard.load_state(args.state)
    picks = choose(now.date(), set(names), state)
    document = json.loads(args.improvements.read_text(encoding="utf-8"))
    apply(document, picks, names, now)
    args.improvements.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"app": names.get(c["app_id"]), "ct": c["ct"]} for c, _ in picks], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
