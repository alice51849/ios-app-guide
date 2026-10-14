#!/usr/bin/env python3
"""Put the Mac's YouTube Shorts uploads on the promotion page (zero tokens, no network).

The Mac (00_GrowthEngine hook-shorts-youtube.yml) uploads the hook clips as
Shorts and records each upload in the private Growth Engine's
shorts/youtube-posted.json ({"posted": {clip key: {"at", "videoId", "url"}}}).
It cannot push here, so clip-replan.yml (which already checks out the Growth
Engine's shorts/ read-only) runs this: every upload not yet in
.github/growth/clip-posts.json is appended as a "youtube" post, and the
clips section on office.cait518.cc shows its [YT] link next to the clip.

    python3 youtube_links.py --posted .engine/shorts/youtube-posted.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clip_progress  # noqa: E402

CHANNEL = "youtube"
SHORTS_URL = re.compile(r"^https://(?:www\.)?youtube\.com/shorts/[A-Za-z0-9_-]{6,20}$")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def uploads(posted):
    """(key, url, at, video id) for every well-formed upload record, oldest first."""
    out = []
    for key, rec in ((posted or {}).get("posted") or {}).items():
        if not isinstance(rec, dict):
            continue
        url, at = str(rec.get("url") or ""), str(rec.get("at") or "")
        if "/" in key and SHORTS_URL.match(url) and STAMP.match(at):
            out.append((key, url, at, str(rec.get("videoId") or url.rsplit("/", 1)[-1])))
    return sorted(out, key=lambda u: (u[2], u[0]))


def merge(posted, log):
    """Append uploads missing from the post log; returns how many were added."""
    have = {(p.get("channel"), p.get("clip")) for p in log.get("posts", [])}
    added = 0
    for key, url, at, vid in uploads(posted):
        if (CHANNEL, key) in have:
            continue
        log.setdefault("posts", []).append({"channel": CHANNEL, "clip": key, "link": url, "posted_at": at,
                                            "id": vid})
        have.add((CHANNEL, key))
        added += 1
    log["posts"].sort(key=lambda p: p.get("posted_at", ""))
    return added


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--posted", required=True, help="the Growth Engine's shorts/youtube-posted.json")
    args = ap.parse_args(argv)
    try:
        posted = json.loads(Path(args.posted).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"youtube-links: {args.posted} unreadable ({exc.__class__.__name__}); page unchanged")
        return 0
    log = clip_progress.load_json(clip_progress.POSTS, {"posts": [], "notes": []})
    added = merge(posted, log)
    if added:
        clip_progress.POSTS.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"youtube-links: {added} new YouTube Shorts link(s) on the promotion page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
