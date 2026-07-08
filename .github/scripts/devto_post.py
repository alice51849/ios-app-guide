#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev.to 自動發文 — 零成本,發自己的高品質文章(主打自家 app、valid tags、無 canonical 指回弱站)。
防重複:先抓已發佈標題,只發「還沒發過」的那篇;帳號未解鎖(403)時優雅略過不讓 workflow 紅燈。
key 來自環境變數 DEVTO_API_KEY(GitHub Secret)。
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Lumi Apps poster)"


def existing_titles(username):
    try:
        req = urllib.request.Request(
            f"https://dev.to/api/articles?username={username}&per_page=100",
            headers={"User-Agent": UA})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        return {a.get("title", "").strip() for a in d}
    except Exception:
        return set()


def me(key):
    req = urllib.request.Request("https://dev.to/api/users/me",
                                 headers={"api-key": key, "User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=25))


def main():
    key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not key:
        print("missing DEVTO_API_KEY", file=sys.stderr); sys.exit(1)
    try:
        username = me(key).get("username", "")
    except Exception as e:  # noqa: BLE001
        print("cannot read profile:", e, file=sys.stderr); sys.exit(1)
    arts = json.load(open(os.path.join(HERE, "devto_articles.json"), encoding="utf-8"))
    done = existing_titles(username)
    nxt = next((a for a in arts if a["title"].strip() not in done), None)
    if not nxt:
        print("all pool articles already published — nothing to do."); return
    payload = {"article": {"title": nxt["title"], "published": True,
                           "body_markdown": nxt["body"], "tags": nxt.get("tags", [])[:4]}}
    req = urllib.request.Request("https://dev.to/api/articles",
                                 data=json.dumps(payload).encode(),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "User-Agent": UA})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=40))
        print("published ok:", d.get("url"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("Dev.to API still gated (403 — account-age anti-spam). "
                  "Will succeed automatically once unlocked. Skipping this run.")
            return  # 優雅略過,不讓排程紅燈
        print("Dev.to HTTPError:", e.code, e.read().decode()[:200], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
