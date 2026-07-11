#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atom feed generator — 把最近更新的頁做成 feed.xml(聚合器 + AI 爬蟲的 freshness/發現面)。

無 OpenAI、純走訪站台檔案。輸出 geo/pages/feed.xml。可排程(每日 job 呼叫)。
"""
import datetime as dt
import html
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
MAX_ITEMS = 60
DATE_MODIFIED_RE = re.compile(
    r'"dateModified"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[^"]+)?)"'
)


def _title(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(4000)
        m = re.search(r"<title>([^<]+)</title>", head)
        return html.unescape(m.group(1)).strip() if m else os.path.basename(path)
    except OSError:
        return os.path.basename(path)


def _desc(path):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(6000)
        m = re.search(r'<meta name="description" content="([^"]*)"', head)
        return html.unescape(m.group(1)).strip() if m else ""
    except OSError:
        return ""


def _git_modified_times():
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                PAGES,
                "log",
                "--format=%x1e%ct",
                "--name-only",
                "--",
                "answers",
                "guides",
                "alternatives",
                "tools",
                "data",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {}
    modified = {}
    for record in result.stdout.split("\x1e"):
        lines = [line.strip() for line in record.splitlines() if line.strip()]
        if not lines or not lines[0].isdigit():
            continue
        timestamp = float(lines[0])
        for relative in lines[1:]:
            modified.setdefault(os.path.join(PAGES, relative), timestamp)
    return modified


def _content_modified(path, git_modified):
    try:
        with open(path, encoding="utf-8") as handle:
            head = handle.read(80000)
        match = DATE_MODIFIED_RE.search(head)
        if match:
            value = match.group(1).replace("Z", "+00:00")
            parsed = dt.datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.timestamp()
    except (OSError, ValueError):
        pass
    return git_modified.get(path, os.path.getmtime(path))


def _write_if_changed(path, content):
    try:
        with open(path, encoding="utf-8") as handle:
            if handle.read() == content:
                return False
    except FileNotFoundError:
        pass
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


def collect():
    """英文內容頁(answers/guides/alternatives/tools/data),取最近更新。"""
    items = []
    git_modified = _git_modified_times()
    for sub in ("answers", "guides", "alternatives", "tools", "data"):
        d = os.path.join(PAGES, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".html") or name == "index.html":
                continue
            p = os.path.join(d, name)
            items.append(
                (_content_modified(p, git_modified), f"{SITE}/{sub}/{name}", p)
            )
    items.sort(reverse=True)
    return items[:MAX_ITEMS]


def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def main():
    items = collect()
    now = iso(items[0][0] if items else time.time())
    e = html.escape
    entries = []
    for ts, url, path in items:
        entries.append(
            "  <entry>\n"
            f"    <title>{e(_title(path))}</title>\n"
            f'    <link href="{e(url)}"/>\n'
            f"    <id>{e(url)}</id>\n"
            f"    <updated>{iso(ts)}</updated>\n"
            f"    <summary>{e(_desc(path))}</summary>\n"
            "  </entry>"
        )
    feed = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        "  <title>iOS App Guide — latest answers, guides, tools &amp; data</title>\n"
        f'  <link href="{SITE}/"/>\n'
        f'  <link rel="self" href="{SITE}/feed.xml"/>\n'
        f"  <id>{SITE}/</id>\n"
        f"  <updated>{now}</updated>\n"
        + "\n".join(entries)
        + "\n</feed>\n"
    )
    out = os.path.join(PAGES, "feed.xml")
    _write_if_changed(out, feed)
    print(f"\u2713 feed.xml {len(items)} entries \u2192 {out}")


if __name__ == "__main__":
    main()
