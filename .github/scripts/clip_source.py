#!/usr/bin/env python3
"""Get a hook clip onto the runner as a whole, checked mp4 before any platform sees it.

Why (2026-10-22): the posters handed clips.json "url" to the platform (Telegram sendVideo video=<url>,
Instagram Reels video_url) and let the platform fetch it. files.catbox.moe stopped answering on 10-21, and the
clips-mirror release that replaced it answers a GET with a 302 to a signed download host, serves
application/octet-stream and refuses HEAD: Telegram answered "failed to get HTTP URL content". Now the runner
fetches the clip itself first: Telegram gets the bytes (multipart sendVideo), YouTube uploads them as before,
and Instagram (Instagram Login has no byte upload; resumable upload is for Facebook Login apps only) gets the
url that just served the checked clip, with the redirect already followed.

  fetch_clip(url, dest_dir, label)      -> Path of a checked mp4, or ClipUnavailable
  fetch_clip_url(url, dest_dir, label)  -> (Path, the final url that served it, redirects followed)
      sources: the clips-mirror release first, catbox second (same id), any other url as it is;
      each source: redirects followed, a dropped transfer resumed with Range, retried with backoff;
      the file must be an ISO-BMFF mp4 whose top-level boxes start with ftyp, hold moov and mdat and end
      exactly at the end of the file (a truncated or HTML answer never goes out).

ios-app-guide .github/scripts/clip_source.py and 00_GrowthEngine shorts/scripts/clip_source.py are the same
file byte for byte; change both together.
"""
from __future__ import annotations

import http.client
import re
import struct
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MIRROR = "https://github.com/alice51849/ios-app-guide/releases/download/clips-mirror/"
CATBOX = "https://files.catbox.moe/"
CLIP_ID = re.compile(r"^https://(?:github\.com/alice51849/ios-app-guide/releases/download/clips-mirror"
                     r"|files\.catbox\.moe)/([A-Za-z0-9]+)\.mp4$")
UA = "lumi-clip-fetch/1.0"
MIN_BYTES = 20_000          # a real 7-second clip is megabytes; anything smaller is an error page or a stub
MAX_BYTES = 50_000_000      # the Telegram Bot API's upload cap; the hook clips are far below it
LASTING = {400, 401, 403, 404, 410, 451}  # this source will not serve it: go on to the next source
CHUNK = 1 << 16


class ClipUnavailable(RuntimeError):
    """No source gave a whole mp4: nothing was sent to any platform."""


class Upload:
    """A local file a poster sends as bytes (a multipart field, a resumable upload body), never as a URL."""

    def __init__(self, path, content_type="video/mp4", filename="clip.mp4"):
        self.path = Path(path)
        self.content_type = content_type
        self.filename = filename

    @property
    def size(self):
        return self.path.stat().st_size

    def read(self):
        return self.path.read_bytes()

    def __repr__(self):
        return f"Upload({self.filename}, {self.content_type})"


def is_clip(url):
    """True for a hook clip url (the clips-mirror release, catbox or any other .mp4)."""
    return bool(CLIP_ID.match(url or "")) or urllib.parse.urlsplit(url or "").path.lower().endswith(".mp4")


def sources(url):
    """Where to fetch the clip from, in order: the clips-mirror release first, catbox second."""
    m = CLIP_ID.match(url or "")
    if not m:
        return [url] if url else []
    return [f"{MIRROR}{m.group(1)}.mp4", f"{CATBOX}{m.group(1)}.mp4"]


def mp4_problem(path):
    """'' for a whole mp4, else why not."""
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError:
        return "no file"
    if size < MIN_BYTES:
        return f"too small ({size} bytes)"
    if size > MAX_BYTES:
        return f"too large ({size} bytes)"
    kinds, pos = [], 0
    with path.open("rb") as f:
        while pos < size:
            if len(kinds) > 10_000:
                return "too many boxes"
            f.seek(pos)
            head = f.read(16)
            if len(head) < 8:
                return f"truncated box header at byte {pos}"
            box, kind = struct.unpack(">I", head[:4])[0], head[4:8]
            if not pos and kind != b"ftyp":
                return "not an mp4 (no ftyp box first)"
            if box == 1:  # 64-bit size
                if len(head) < 16:
                    return f"truncated box header at byte {pos}"
                box = struct.unpack(">Q", head[8:16])[0]
            elif box == 0:  # runs to the end of the file
                box = size - pos
            if box < 8 or pos + box > size:
                return f"box {kind!r} at byte {pos} runs past the end (truncated)"
            kinds.append(kind)
            pos += box
    for need in (b"moov", b"mdat"):
        if need not in kinds:
            return f"not a playable mp4 (no {need.decode()} box)"
    return ""


def _open(url, start, timeout):
    headers = {"User-Agent": UA, "Accept": "video/mp4,*/*"}
    if start:
        headers["Range"] = f"bytes={start}-"
    # urllib follows the 302 to the signed download host and keeps the Range header on the way.
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def fetch(url, dest, tries=4, timeout=60, sleep=time.sleep, info=None):
    """Download url to dest: '' when the whole body arrived, else the reason (no url, no secret in it).
    info (a dict), when given, gets "url": the address that served the last answer, after redirects."""
    dest = Path(dest)
    info = {} if info is None else info
    dest.write_bytes(b"")
    have, total, last = 0, None, "no answer"
    for attempt in range(tries):
        if attempt:
            sleep(min(3 * 2 ** (attempt - 1), 20))
        try:
            with _open(url, have, timeout) as r:
                status = getattr(r, "status", None) or r.getcode()
                mode = "wb"
                if have and status == 206:
                    m = re.match(r"bytes (\d+)-\d+/(\d+|\*)", r.headers.get("Content-Range", ""))
                    if not m or int(m.group(1)) != have:
                        have, total, last = 0, None, "the resumed range did not match; starting over"
                        continue
                    total = int(m.group(2)) if m.group(2) != "*" else total
                    mode = "ab"
                else:  # 200: the whole file (also when the server ignored Range)
                    have = 0
                    length = r.headers.get("Content-Length", "")
                    total = int(length) if length.isdigit() else None
                if total is not None and total > MAX_BYTES:
                    return f"too large ({total} bytes)"
                info["url"] = r.geturl()
                with dest.open(mode) as out:
                    while True:
                        chunk = r.read(CHUNK)
                        if not chunk:
                            break
                        out.write(chunk)
                        have += len(chunk)
                        if have > MAX_BYTES:
                            return f"too large (over {MAX_BYTES} bytes)"
            if total is None or have == total:
                return ""
            last = f"stopped at {have} of {total} bytes"
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and total is not None and have == total:
                return ""
            last = f"HTTP {exc.code}"
            if exc.code in LASTING:
                return last
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            reason = getattr(exc, "reason", None) or exc
            last = f"{exc.__class__.__name__}: {str(reason)[:120]}"
    return last


def fetch_clip(url, dest_dir=None, label="clip", tries=4, sleep=time.sleep):
    """The clip as a checked local mp4 (Path); ClipUnavailable when no source gives one."""
    return fetch_clip_url(url, dest_dir, label, tries, sleep)[0]


def fetch_clip_url(url, dest_dir=None, label="clip", tries=4, sleep=time.sleep):
    """(checked local mp4, the url that served it after redirects); ClipUnavailable when no source gives one.
    The served url of the clips-mirror release is a signed download address that lasts about an hour."""
    dest_dir = Path(dest_dir) if dest_dir else Path(tempfile.mkdtemp(prefix="clip-src-"))
    dest_dir.mkdir(parents=True, exist_ok=True)
    reasons = []
    for i, src in enumerate(sources(url)):
        dest = dest_dir / f"clip-{i}.mp4"
        host = urllib.parse.urlsplit(src).hostname or "?"
        info = {}
        err = fetch(src, dest, tries=tries, sleep=sleep, info=info) or mp4_problem(dest)
        if not err:
            print(f"clip: {label} video fetched from {host} ({dest.stat().st_size} bytes, mp4 checked)")
            return dest, info.get("url") or src
        reasons.append(f"{host}: {err}")
        dest.unlink(missing_ok=True)
    raise ClipUnavailable(f"{label}: no source gave a whole mp4 ({'; '.join(reasons) or 'no clip url'})")
