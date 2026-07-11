#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Syndication feed generator for Atom, RSS 2.0 and JSON Feed 1.1.

無 OpenAI、純走訪站台檔案。三種格式共用同一份穩定選集，可排程每日重生。
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
MAX_ITEMS = 60
REQUIRED_SUBDIRS = ("guides",)
REQUIRED_RELATIVE_PATHS = (
    "data/zhuyin-bopomofo-dcat3-open-data-catalog.html",
)
RESERVED_SUBDIR_LIMITS = (("tools", 10), ("data", 3))
FEED_TITLE = "iOS App Guide — latest answers &amp; guides"
DATE_MODIFIED_RE = re.compile(
    r'"dateModified"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[^"]+)?)"'
)
CTA_RE = re.compile(r'<a class="cta" href="([^"]+)"')
FEED_LINK_RE = re.compile(
    r'<link rel="alternate" type="application/'
    r'(?:atom\+xml|rss\+xml|feed\+json)"[^>]*>'
)


def feed_discovery_links():
    return "\n".join(
        (
            f'<link rel="alternate" type="application/atom+xml" '
            f'title="{FEED_TITLE} (Atom)" href="{SITE}/feed.xml">',
            f'<link rel="alternate" type="application/rss+xml" '
            f'title="{FEED_TITLE} (RSS 2.0)" href="{SITE}/rss.xml">',
            f'<link rel="alternate" type="application/feed+json" '
            f'title="{FEED_TITLE} (JSON Feed 1.1)" href="{SITE}/feed.json">',
        )
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
                "api",
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


def _has_owned_resource_cta(path):
    if os.path.basename(os.path.dirname(path)) != "answers":
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            match = CTA_RE.search(handle.read(32_000))
    except OSError:
        return False
    return bool(match and match.group(1).startswith(f"{SITE}/"))


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


def ensure_feed_discovery(path):
    try:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
    except OSError:
        return False
    if "</head>" not in source:
        return False
    cleaned = FEED_LINK_RE.sub("", source)
    head_index = cleaned.index("</head>")
    updated = (
        cleaned[:head_index].rstrip()
        + "\n"
        + feed_discovery_links()
        + "\n"
        + cleaned[head_index:]
    )
    return _write_if_changed(path, updated)


def collect():
    """英文內容頁與 API 文件,取可驗證的最近更新時間。"""
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
    for relative, url in (
        ("api/index.html", f"{SITE}/api/"),
        (
            "api/v1/family-travel-missions/index.html",
            f"{SITE}/api/v1/family-travel-missions/",
        ),
    ):
        path = os.path.join(PAGES, relative)
        if os.path.exists(path):
            items.append((_content_modified(path, git_modified), url, path))
    items.sort(reverse=True)
    required = [
        item
        for item in items
        if (
            any(f"/{subdir}/" in item[1] for subdir in REQUIRED_SUBDIRS)
            or any(
                item[1] == f"{SITE}/{relative}"
                for relative in REQUIRED_RELATIVE_PATHS
            )
            or _has_owned_resource_cta(item[2])
        )
    ]
    if len(required) >= MAX_ITEMS:
        return required[:MAX_ITEMS]
    selected = list(required)
    selected_urls = {item[1] for item in selected}
    for subdir, limit in RESERVED_SUBDIR_LIMITS:
        added = sum(f"/{subdir}/" in item[1] for item in selected)
        for item in items:
            if len(selected) >= MAX_ITEMS or added >= limit:
                break
            if f"/{subdir}/" in item[1] and item[1] not in selected_urls:
                selected.append(item)
                selected_urls.add(item[1])
                added += 1
    reserved_paths = tuple(f"/{subdir}/" for subdir, _ in RESERVED_SUBDIR_LIMITS)
    for item in items:
        if len(selected) >= MAX_ITEMS:
            break
        if (
            item[1] not in selected_urls
            and not any(path in item[1] for path in reserved_paths)
        ):
            selected.append(item)
            selected_urls.add(item[1])
    for item in items:
        if len(selected) >= MAX_ITEMS:
            break
        if item[1] not in selected_urls:
            selected.append(item)
            selected_urls.add(item[1])
    selected.sort(reverse=True)
    return selected


def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def rss_date(ts):
    return email.utils.formatdate(ts, usegmt=True)


def render_atom(items, now):
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
    return feed


def render_rss(items, now):
    e = html.escape
    entries = []
    for ts, url, path in items:
        entries.append(
            "    <item>\n"
            f"      <title>{e(_title(path))}</title>\n"
            f"      <link>{e(url)}</link>\n"
            f"      <description>{e(_desc(path) or _title(path))}</description>\n"
            f'      <guid isPermaLink="true">{e(url)}</guid>\n'
            f"      <pubDate>{rss_date(ts)}</pubDate>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>iOS App Guide — latest answers, guides, tools &amp; data</title>\n"
        f"    <link>{SITE}/</link>\n"
        "    <description>Fresh independent iOS app guides, answers, free tools "
        "and open datasets.</description>\n"
        "    <language>en</language>\n"
        f"    <lastBuildDate>{rss_date(now)}</lastBuildDate>\n"
        "    <generator>iOS App Guide static syndication generator</generator>\n"
        "    <docs>https://www.rssboard.org/rss-specification</docs>\n"
        "    <ttl>360</ttl>\n"
        f'    <atom:link href="{SITE}/rss.xml" rel="self" '
        'type="application/rss+xml"/>\n'
        f'    <atom:link href="{SITE}/feed.xml" rel="alternate" '
        'type="application/atom+xml"/>\n'
        f'    <atom:link href="{SITE}/feed.json" rel="alternate" '
        'type="application/feed+json"/>\n'
        + "\n".join(entries)
        + "\n  </channel>\n</rss>\n"
    )


def render_json_feed(items):
    records = []
    for ts, url, path in items:
        description = _desc(path) or _title(path)
        records.append(
            {
                "id": url,
                "url": url,
                "title": _title(path),
                "content_text": description,
                "summary": description,
                "date_modified": iso(ts),
                "language": "en",
            }
        )
    return (
        json.dumps(
            {
                "version": "https://jsonfeed.org/version/1.1",
                "title": "iOS App Guide — latest answers, guides, tools & data",
                "home_page_url": f"{SITE}/",
                "feed_url": f"{SITE}/feed.json",
                "description": (
                    "Fresh independent iOS app guides, answers, free tools "
                    "and open datasets."
                ),
                "language": "en",
                "items": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main():
    items = collect()
    for _, _, path in items:
        ensure_feed_discovery(path)
    newest = items[0][0] if items else time.time()
    feeds = {
        "feed.xml": render_atom(items, iso(newest)),
        "rss.xml": render_rss(items, newest),
        "feed.json": render_json_feed(items),
    }
    for filename, content in feeds.items():
        out = os.path.join(PAGES, filename)
        _write_if_changed(out, content)
        print(f"\u2713 {filename} {len(items)} entries \u2192 {out}")


if __name__ == "__main__":
    main()
