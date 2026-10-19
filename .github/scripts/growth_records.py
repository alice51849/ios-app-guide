#!/usr/bin/env python3
"""Hold the bots' .github/growth record commits off main while geo-daily runs.

geo-daily.yml (about five hours, group ios-app-guide-main-writer) compares the
whole tree before it pushes; any commit that lands on main meanwhile makes it
redo the localisation reconcile (about 55 minutes) and it keeps hitting its
time limit. The posting bots only ever write records under .github/growth/, so
while geo-daily is queued or running their record commits go to the
growth-records-pending branch instead, and the first record push after it ends
merges that branch into main (a merge commit; history is never rewritten).

Subcommands:
  overlay        right after actions/checkout: when growth-records-pending holds
                 commits main lacks, fold its .github/growth records into the
                 working tree (as one local commit, so `git status` stays clean
                 and the "nothing posted" checks keep working). Dedupe reads
                 (link_backfill.py, comment_replies.py, clip_posts.py ...) then
                 see every record, wherever it waits.
  prepare        start of each push attempt, in place of
                 `git fetch origin main && git reset --hard origin/main`.
                 Prints the branch to push to (main or growth-records-pending)
                 and leaves the tree on that branch's tip with the pending
                 records folded in. When pending must be merged, a merge is left
                 open (MERGE_HEAD), so the workflow's own `git commit` records it.
  push BRANCH    `git push origin HEAD:BRANCH`; exit 1 when the push is refused
                 (the workflow's retry loop and its red light stay as they were).

geo-daily status comes from the Actions API (GITHUB_TOKEN, `actions: read`).
When that lookup fails the records go to main as before, with a ::warning::.
Pushes to growth-records-pending trigger nothing: every on.push in
.github/workflows is limited to main.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

PENDING = "growth-records-pending"
GROWTH = ".github/growth"
GEO_WORKFLOW = "geo-daily.yml"
ACTIVE = {"in_progress", "queued", "waiting", "requested", "pending"}
MAIN_REF = "refs/remotes/origin/main"
PENDING_REF = f"refs/remotes/origin/{PENDING}"
BOT = ["-c", "user.name=github-actions[bot]",
       "-c", "user.email=41898299+github-actions[bot]@users.noreply.github.com"]


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


class GitError(RuntimeError):
    pass


def git(*args: str, check: bool = True, data: bytes | None = None) -> str:
    p = subprocess.run(["git", *args], input=data, capture_output=True)
    if check and p.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout.decode(errors="replace").strip()


def ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True).returncode == 0


def blob(ref: str, path: str) -> bytes | None:
    p = subprocess.run(["git", "cat-file", "blob", f"{ref}:{path}"], capture_output=True)
    return p.stdout if p.returncode == 0 else None


# ---- remote state ---------------------------------------------------------

def fetch(attempts: int = 3) -> bool:
    """Refresh origin/main and origin/growth-records-pending; True when pending exists."""
    for i in range(attempts):
        try:
            git("fetch", "-q", "origin", f"+refs/heads/main:{MAIN_REF}")
            heads = git("ls-remote", "--heads", "origin", PENDING)
            if heads:
                git("fetch", "-q", *_history_window(), "origin", f"+refs/heads/{PENDING}:{PENDING_REF}")
            elif ok("rev-parse", "-q", "--verify", PENDING_REF):
                git("update-ref", "-d", PENDING_REF)
            _ensure_base(bool(heads))
            return bool(heads)
        except GitError as e:
            if i == attempts - 1:
                raise
            log(f"fetch failed ({e}); retrying")
            time.sleep(3 * (i + 1))
    return False


def _history_window() -> tuple[str, ...]:
    """Fetch flags that keep a shallow runner checkout from pulling the site's whole history.

    The guide checkout is depth 1, so fetching pending unbounded walks every commit down to the
    first one (2026-10-19 run 39269858414 spent 13.5 minutes in overlay). Bound it to 50 commits
    and leave file contents on the server (a promisor remote hands over the few record blobs
    merged_records reads, on demand)."""
    if git("rev-parse", "--is-shallow-repository") != "true":
        return ()
    git("config", "extensions.partialClone", "origin")
    git("config", "remote.origin.promisor", "true")
    git("config", "remote.origin.partialclonefilter", "blob:none")
    return ("--depth=50", "--filter=blob:none")


def _ensure_base(has_pending: bool) -> None:
    """A shallow checkout may not reach main and pending's fork point; deepen until it does."""
    if not has_pending or ok("merge-base", MAIN_REF, PENDING_REF):
        return
    for deepen in ("--deepen=50", "--deepen=500", "--unshallow"):
        if git("rev-parse", "--is-shallow-repository") != "true":
            break
        git("fetch", "-q", deepen, "--filter=blob:none", "origin",
            f"+refs/heads/main:{MAIN_REF}", f"+refs/heads/{PENDING}:{PENDING_REF}")
        if ok("merge-base", MAIN_REF, PENDING_REF):
            return
    if not ok("merge-base", MAIN_REF, PENDING_REF):
        raise GitError(f"{PENDING} shares no history with main")


def pending_ahead(has_pending: bool) -> bool:
    """growth-records-pending holds commits main lacks (an already merged branch is ignored)."""
    return has_pending and not ok("merge-base", "--is-ancestor", PENDING_REF, MAIN_REF)


def geo_daily_active() -> bool | None:
    """True while geo-daily is queued or running, False when idle, None when the API can't tell."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        log("::warning::growth_records: no GITHUB_TOKEN/GITHUB_REPOSITORY, cannot see geo-daily; records go to main")
        return None
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    url = f"{api}/repos/{repo}/actions/workflows/{GEO_WORKFLOW}/runs?per_page=10"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            runs = json.load(r).get("workflow_runs")
        if not isinstance(runs, list):
            raise ValueError("no workflow_runs in the reply")
    except Exception as e:  # noqa: BLE001 - any failure means "unknown", reported below
        log(f"::warning::growth_records: geo-daily status lookup failed ({e}); records go to main")
        return None
    return any(r.get("status") in ACTIVE for r in runs)


# ---- merging pending's records into main's ----------------------------------

MISSING = object()


def _key(v) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def merge_json(base, ours, theirs):
    """Three-way merge of two JSON documents; keeps both sides' additions, theirs wins scalar clashes."""
    if ours is MISSING and theirs is MISSING:
        return MISSING
    if ours is MISSING or theirs is MISSING:
        return theirs if ours is MISSING else ours  # one side removed, the other changed: keep the data
    if _key(ours) == _key(theirs):
        return ours
    if base is not MISSING and _key(ours) == _key(base):
        return theirs
    if base is not MISSING and _key(theirs) == _key(base):
        return ours
    if isinstance(ours, dict) and isinstance(theirs, dict):
        b = base if isinstance(base, dict) else {}
        out = {}
        for k in list(ours) + [k for k in theirs if k not in ours]:
            bv = b.get(k, MISSING)
            ov, tv = ours.get(k, MISSING), theirs.get(k, MISSING)
            if ov is MISSING and bv is not MISSING and _key(tv) == _key(bv):
                continue  # ours removed it
            if tv is MISSING and bv is not MISSING and _key(ov) == _key(bv):
                continue  # theirs removed it
            v = merge_json(bv, ov, tv)
            if v is not MISSING:
                out[k] = v
        return out
    if isinstance(ours, list) and isinstance(theirs, list):
        b = {_key(x) for x in base} if isinstance(base, list) else set()
        o = {_key(x) for x in ours}
        t = {_key(x) for x in theirs}
        out = [x for x in ours if not (_key(x) in b and _key(x) not in t)]
        seen = {_key(x) for x in out}
        for x in theirs:
            k = _key(x)
            if k in seen or (k in b and k not in o):
                continue
            out.append(x)
            seen.add(k)
        return out
    return theirs


def _dump_like(doc, sample: bytes | None) -> bytes:
    text = (sample or b"").decode("utf-8", errors="replace")
    sort = False
    try:
        top = json.loads(text)
        sort = isinstance(top, dict) and list(top) == sorted(top) and len(top) > 1
    except ValueError:
        pass
    return (json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=sort) + "\n").encode("utf-8")


def merge_file(path: str, base: bytes | None, ours: bytes | None, theirs: bytes | None) -> bytes | None:
    if ours is None or theirs is None:
        return theirs if ours is None else ours  # deleted on one side, edited on the other: keep it
    if path.endswith(".json"):
        try:
            b = json.loads(base) if base is not None else MISSING
            return _dump_like(merge_json(b, json.loads(ours), json.loads(theirs)), theirs)
        except ValueError:
            pass
    with tempfile.TemporaryDirectory() as d:
        names = []
        for n, data in (("ours", ours), ("base", base or b""), ("theirs", theirs)):
            p = os.path.join(d, n)
            with open(p, "wb") as f:
                f.write(data)
            names.append(p)
        r = subprocess.run(["git", "merge-file", "-p", *names], capture_output=True)
        return r.stdout if r.returncode == 0 else theirs


def merged_records(ours: str = MAIN_REF, theirs: str = PENDING_REF) -> dict[str, bytes | None]:
    """{path: content or None (delete)} that folds theirs' .github/growth changes into ours."""
    base = git("merge-base", ours, theirs)
    out: dict[str, bytes | None] = {}
    for line in git("diff", "--no-renames", "--name-only", "-z", base, theirs, "--", GROWTH).split("\0"):
        path = line.strip()
        if not path:
            continue
        b, o, t = blob(base, path), blob(ours, path), blob(theirs, path)
        if o == t:
            continue
        out[path] = t if o == b else merge_file(path, b, o, t)
    return out


def write_records(files: dict[str, bytes | None]) -> None:
    for path, data in files.items():
        if data is None:
            if os.path.exists(path):
                git("rm", "-q", "-f", "--", path)
            continue
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        git("add", "--", path)


# ---- subcommands -------------------------------------------------------------

def overlay() -> int:
    if not pending_ahead(fetch()):
        log(f"growth_records: no records waiting on {PENDING}")
        return 0
    files = merged_records()
    write_records(files)
    if not ok("diff", "--cached", "--quiet"):
        git(*BOT, "commit", "-q", "--no-verify", "-m", f"(local only) records waiting on {PENDING}")
    log(f"::notice::growth_records: read {len(files)} record file(s) still waiting on {PENDING}")
    return 0


def prepare() -> str:
    has_pending = fetch()
    active = geo_daily_active()
    ahead = pending_ahead(has_pending)
    if active:
        target = PENDING
        if ahead:
            git("reset", "-q", "--hard", PENDING_REF)
            if not ok("merge-base", "--is-ancestor", MAIN_REF, PENDING_REF):
                # main moved on since pending forked: carry main's tree, with pending's records on top
                git(*BOT, "merge", "-q", "--no-ff", "--no-commit", "-s", "ours", MAIN_REF)
                git("read-tree", "-u", "--reset", MAIN_REF)
                write_records(merged_records())
        else:
            git("reset", "-q", "--hard", MAIN_REF)
        log(f"growth_records: geo-daily is running; records go to {PENDING}")
    else:
        target = "main"
        git("reset", "-q", "--hard", MAIN_REF)
        if ahead:
            git(*BOT, "merge", "-q", "--no-ff", "--no-commit", "-s", "ours", PENDING_REF)
            write_records(merged_records())
            log(f"growth_records: merging the records waiting on {PENDING} into main")
    return target


def push(target: str) -> int:
    if target not in ("main", PENDING):
        log(f"::error::growth_records: refusing to push to {target}")
        return 2
    p = subprocess.run(["git", "push", "-q", "origin", f"HEAD:refs/heads/{target}"])
    return 0 if p.returncode == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else ""
    try:
        if cmd == "overlay":
            return overlay()
        if cmd == "prepare":
            print(prepare())
            return 0
        if cmd == "push" and len(args) == 2:
            return push(args[1])
    except GitError as e:
        log(f"::error::growth_records {cmd}: {e}")
        return 1
    log("usage: growth_records.py overlay | prepare | push <main|growth-records-pending>")
    return 2


if __name__ == "__main__":
    sys.exit(main())
