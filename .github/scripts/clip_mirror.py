#!/usr/bin/env python3
"""Mirror the hook clips from files.catbox.moe to the clips-mirror GitHub release.

Why: catbox stopped answering on 2026-10-21 (Telegram, Instagram and YouTube all fetch the
clip from clips.json "url"). The posters only read that url, so pointing it at a release
asset of this public repo brings every channel back without touching posting logic.

  clip_mirror.py mirror  [--results mirror-results.json] [--jobs 6] [--limit N]
      download each catbox clip, check it is a real mp4, upload it to the release as
      <catbox id>.mp4 (--clobber), then read the release back: only an asset that is there
      with the same byte size counts as mirrored.
  clip_mirror.py recover [--results mirror-results.json] --published PUBLISHED.json --history CLIPS_OUT_CLONE
      (without a results file: every clip clips.json still has on catbox)
      for the clips catbox no longer serves (empty or missing file), take the render from the
      Growth Engine's clips-out branch history: the blob whose sha256 (first 16 hex) equals the
      sha recorded in shorts/published.json, so it is byte for byte what was once uploaded.
      Upload it under the same catbox id and mark it mirrored.
  clip_mirror.py rewrite [--results mirror-results.json]
      in clips.json, swap the catbox url of every mirrored clip for the release url. Plain
      text replacement of the quoted url, so the file's formatting stays byte for byte, and
      idempotent, so it can be re-run on a newer clips.json after a rebase.
  clip_mirror.py order
      print the upload order (id, key) and exit.

Upload order: the cute checklist app (mochi and its mochi_* cuts) first, then the clips the
schedule posts between 2026-10-22 and 2026-10-26, then the rest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIPS = ROOT / ".github" / "growth" / "clips.json"
REPO = "alice51849/ios-app-guide"
TAG = "clips-mirror"
NEW_BASE = f"https://github.com/{REPO}/releases/download/{TAG}/"
CATBOX_RE = re.compile(r"^https://files\.catbox\.moe/([A-Za-z0-9]+)\.mp4$")
WINDOW = ("2026-10-22", "2026-10-26")
MIN_BYTES = 20_000          # a real clip is megabytes; anything below is an error page
MAX_BYTES = 1_900_000_000   # release assets are capped at 2 GB
GIVE_UP_AFTER = 8           # this many finished clips with none good = catbox unreachable from here


def is_mochi(app: str) -> bool:
    return app == "mochi" or app.startswith("mochi_")


def ordered(data: dict) -> list[tuple[str, str, str]]:
    """[(catbox id, clip key, catbox url)] in upload order, each id once."""
    clips = data["clips"]
    lo, hi = WINDOW
    sched = sorted((e for e in data.get("schedule", []) if lo <= e["date"] <= hi),
                   key=lambda e: (e["date"], e["slot"]))
    rank: dict[str, tuple] = {}
    for key, c in clips.items():
        if is_mochi(c.get("app", "")):
            rank[key] = (0, 0, key)
    for i, e in enumerate(sched):
        rank.setdefault(e["clip"], (1, i, e["clip"]))
    out, seen = [], set()
    for key in sorted(clips, key=lambda k: rank.get(k, (2, 0, k))):
        m = CATBOX_RE.match(clips[key].get("url", ""))
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((m.group(1), key, clips[key]["url"]))
    return out


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def head_info(url: str) -> tuple[int | None, str]:
    """Content-Length and Content-Type of the final response, (None, '') when unknown."""
    r = run(["curl", "-sSIL", "--connect-timeout", "20", "--max-time", "60", url])
    if r.returncode != 0:
        return None, ""
    blocks = [b for b in re.split(r"\r?\n\r?\n", r.stdout) if b.strip().startswith("HTTP/")]
    if not blocks:
        return None, ""
    last = blocks[-1]
    length = re.search(r"(?im)^content-length:\s*(\d+)", last)
    ctype = re.search(r"(?im)^content-type:\s*([^\r\n;]+)", last)
    return (int(length.group(1)) if length else None), (ctype.group(1).strip().lower() if ctype else "")


def looks_like_mp4(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(12)
    except OSError:
        return False
    return len(head) >= 12 and head[4:8] == b"ftyp"


def fetch_whole(url: str, dest: Path) -> str:
    """One curl with its own retries. '' on success, else the reason."""
    r = run(["curl", "-sSL", "--fail", "--retry", "4", "--retry-delay", "3", "--retry-all-errors",
             "--connect-timeout", "20", "--max-time", "300", "-o", str(dest), url])
    return "" if r.returncode == 0 else f"curl {r.returncode}: {r.stderr.strip()[-160:]}"


def fetch_ranges(url: str, dest: Path, total: int, chunk: int = 1_000_000) -> str:
    """Download in Range pieces and join them, for a link that keeps dropping a long transfer."""
    with dest.open("wb") as out:
        pos = 0
        while pos < total:
            end = min(pos + chunk, total) - 1
            piece = dest.with_suffix(f".part{pos}")
            err = ""
            for attempt in range(5):
                r = run(["curl", "-sSL", "--fail", "--connect-timeout", "20", "--max-time", "120",
                         "-r", f"{pos}-{end}", "-o", str(piece), url])
                if r.returncode == 0 and piece.exists() and piece.stat().st_size == end - pos + 1:
                    err = ""
                    break
                err = f"range {pos}-{end} curl {r.returncode}: {r.stderr.strip()[-120:]}"
                time.sleep(2 * (attempt + 1))
            if err:
                piece.unlink(missing_ok=True)
                return err
            out.write(piece.read_bytes())
            piece.unlink(missing_ok=True)
            pos = end + 1
    return ""


def download(url: str, dest: Path) -> str:
    """Download url to dest and check it. '' on success, else the reason."""
    size, ctype = head_info(url)
    if ctype and not (ctype.startswith("video/") or ctype == "application/octet-stream"):
        return f"content-type {ctype}"
    err = fetch_whole(url, dest)
    bad = ""
    if not err:
        bad = _check(dest, size)
    if (err or bad) and size and size >= MIN_BYTES:
        dest.unlink(missing_ok=True)
        err = fetch_ranges(url, dest, size)
        bad = "" if err else _check(dest, size)
    return err or bad


def _check(path: Path, expected: int | None) -> str:
    n = path.stat().st_size if path.exists() else 0
    if n < MIN_BYTES:
        return f"too small ({n} bytes)"
    if n > MAX_BYTES:
        return f"too large ({n} bytes)"
    if expected and n != expected:
        return f"size {n} != content-length {expected}"
    if not looks_like_mp4(path):
        return "not an mp4 (no ftyp box)"
    return ""


def release_assets() -> dict[str, int]:
    r = run(["gh", "release", "view", TAG, "-R", REPO, "--json", "assets",
             "-q", ".assets[] | [.name, .size] | @tsv"])
    if r.returncode != 0:
        raise SystemExit(f"::error::cannot read release {TAG}: {r.stderr.strip()[-200:]}")
    out = {}
    for line in r.stdout.splitlines():
        name, _, size = line.partition("\t")
        if name and size.isdigit():
            out[name] = int(size)
    return out


def upload(path: Path) -> str:
    err = ""
    for attempt in range(4):
        r = run(["gh", "release", "upload", TAG, str(path), "-R", REPO, "--clobber"])
        if r.returncode == 0:
            return ""
        err = f"gh upload {r.returncode}: {r.stderr.strip()[-160:]}"
        time.sleep(4 * (attempt + 1))
    return err


def verify(results: dict[str, dict]) -> int:
    """Read the release back: a clip counts only when its asset is there at the size we sent.
    Marks the rest not ok and returns how many are mirrored."""
    final = release_assets()
    good = 0
    for cid, r in results.items():
        if r["ok"]:
            if final.get(f"{cid}.mp4", 0) >= MIN_BYTES and final[f"{cid}.mp4"] == r.get("bytes"):
                good += 1
            else:
                r.update(ok=False, err="asset missing or wrong size after upload")
    return good


def cmd_mirror(args) -> int:
    data = json.loads(CLIPS.read_text())
    todo = ordered(data)
    if args.limit:
        todo = todo[: args.limit]
    have = release_assets()
    results: dict[str, dict] = {}
    lock = threading.Lock()
    state = {"ok": 0, "fail": 0, "abort": False}
    work = Path(tempfile.mkdtemp(prefix="clip-mirror-"))

    def one(item):
        cid, key, url = item
        name = f"{cid}.mp4"
        if state["abort"]:
            with lock:
                results[cid] = {"key": key, "ok": False, "err": "skipped: catbox unreachable"}
            return
        if have.get(name, 0) >= MIN_BYTES:
            with lock:
                results[cid] = {"key": key, "ok": True, "bytes": have[name], "note": "already in release"}
                state["ok"] += 1
            return
        dest = work / name
        err = download(url, dest)
        size = dest.stat().st_size if dest.exists() else 0
        if not err:
            err = upload(dest)
        dest.unlink(missing_ok=True)
        with lock:
            if err:
                results[cid] = {"key": key, "ok": False, "err": err}
                state["fail"] += 1
                print(f"FAIL {cid} {key}: {err}", flush=True)
            else:
                results[cid] = {"key": key, "ok": True, "bytes": size}
                state["ok"] += 1
                print(f"ok   {cid} {key} {size}", flush=True)
            if state["ok"] == 0 and state["fail"] >= GIVE_UP_AFTER:
                state["abort"] = True

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(one, todo))

    good = verify(results)
    Path(args.results).write_text(json.dumps(results, indent=1, sort_keys=True))
    failed = [c for c, r in results.items() if not r["ok"]]
    print(f"mirrored {good} / {len(todo)}; failed {len(failed)}", flush=True)
    if state["abort"]:
        print("::error::catbox did not answer from this runner (first clips all failed); nothing to commit")
        return 3
    return 0 if good else 1


def git_bytes(repo: Path, *a: str) -> tuple[int, bytes]:
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return r.returncode, r.stdout


def from_history(repo: Path, path: str, sha16: str, dest: Path) -> str:
    """Write to dest the version of path in repo's history whose sha256[:16] is sha16. '' on success."""
    code, out = git_bytes(repo, "log", "--format=%H", "--", path)
    if code != 0:
        return "git log failed"
    seen: set[str] = set()
    for commit in out.decode().split():
        code, blob = git_bytes(repo, "rev-parse", f"{commit}:{path}")
        blob_id = blob.decode().strip()
        if code != 0 or not blob_id or blob_id in seen:  # the commit that removed the file has no blob
            continue
        seen.add(blob_id)
        code, data = git_bytes(repo, "cat-file", "blob", blob_id)
        if code == 0 and hashlib.sha256(data).hexdigest()[:16] == sha16:
            dest.write_bytes(data)
            return ""
    return f"no version of {path} in clips-out matches sha {sha16} ({len(seen)} checked)"


def cmd_recover(args) -> int:
    rp = Path(args.results)
    if rp.exists():
        results = json.loads(rp.read_text())
    else:  # no results file: every clip clips.json still has on catbox is one to recover
        results = {cid: {"key": key, "ok": False, "err": "still on catbox"}
                   for cid, key, _url in ordered(json.loads(CLIPS.read_text()))}
    published = json.loads(Path(args.published).read_text())
    hist = Path(args.history)
    work = Path(tempfile.mkdtemp(prefix="clip-recover-"))
    todo = [(cid, r["key"]) for cid, r in results.items() if not r["ok"]]
    print(f"recovering {len(todo)} clips from clips-out history", flush=True)
    for cid, key in todo:
        app, _, locale = key.partition("/")
        sha16 = ((published.get(app) or {}).get(locale) or {}).get("sha")
        dest = work / f"{cid}.mp4"
        if not sha16:
            err = "no sha in published.json"
        else:
            err = from_history(hist, f"{app}/{app}_{locale}.mp4", sha16, dest)
        if not err:
            err = _check(dest, None) or upload(dest)
        size = dest.stat().st_size if dest.exists() else 0
        dest.unlink(missing_ok=True)
        if err:
            results[cid]["err"] = f"{results[cid].get('err', '')} | clips-out: {err}"[-300:]
            print(f"FAIL {cid} {key}: {err}", flush=True)
        else:
            results[cid] = {"key": key, "ok": True, "bytes": size, "note": "from clips-out"}
            print(f"ok   {cid} {key} {size} (clips-out)", flush=True)
    good = verify(results)
    Path(args.results).write_text(json.dumps(results, indent=1, sort_keys=True))
    left = [r["key"] for r in results.values() if not r["ok"]]
    print(f"mirrored {good} / {len(results)}; still missing {len(left)}: {', '.join(left[:20])}", flush=True)
    return 0


def rewrite_text(text: str, mirrored: set[str]) -> tuple[str, int]:
    n = 0
    for cid in mirrored:
        old = f'"https://files.catbox.moe/{cid}.mp4"'
        if old in text:
            n += text.count(old)
            text = text.replace(old, f'"{NEW_BASE}{cid}.mp4"')
    return text, n


def cmd_rewrite(args) -> int:
    results = json.loads(Path(args.results).read_text())
    mirrored = {c for c, r in results.items() if r.get("ok")}
    text = CLIPS.read_text()
    new, n = rewrite_text(text, mirrored)
    if new != text:
        CLIPS.write_text(new)
    left = len(re.findall(r"https://files\.catbox\.moe/", new))
    print(f"rewrote {n} urls ({len(mirrored)} clips mirrored); {left} catbox urls left")
    return 0


def cmd_order(_args) -> int:
    for i, (cid, key, _url) in enumerate(ordered(json.loads(CLIPS.read_text()))):
        print(i, cid, key)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mirror")
    m.add_argument("--results", default="mirror-results.json")
    m.add_argument("--jobs", type=int, default=6)
    m.add_argument("--limit", type=int, default=0)
    m.set_defaults(fn=cmd_mirror)
    rc = sub.add_parser("recover")
    rc.add_argument("--results", default="mirror-results.json")
    rc.add_argument("--published", required=True)
    rc.add_argument("--history", required=True)
    rc.set_defaults(fn=cmd_recover)
    w = sub.add_parser("rewrite")
    w.add_argument("--results", default="mirror-results.json")
    w.set_defaults(fn=cmd_rewrite)
    o = sub.add_parser("order")
    o.set_defaults(fn=cmd_order)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
