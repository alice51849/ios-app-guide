#!/usr/bin/env python3
"""Commit and push only the re-fetched storefront snapshot, ahead of the slow suites.

geo-daily used to commit ``.appstore_storefront_state.json`` together with every
route and derived file, so a red route suite also discarded the snapshot and the
``zero_since`` it had just confirmed: a listing that newly became free restarted
its 12-hour clock every run and never reached the second confirmation (11-25
ruling 2307 item 1).  This step commits that one file alone, right after the
refresh, when (and only when) the snapshot's own checks are green:

* ``tests/test_storefront_price_readback.py`` (the price/readback rule), and
* ``check_storefront_snapshot.py`` (the file's format, against HEAD's copy).

Routes and every other derived file still need the full suite before the later
English/localized commits; nothing here relaxes that.  The one-file commit is
built only in a throwaway worktree on the freshly fetched origin tip: the local
HEAD, index and working tree are never touched.  After a successful push the
later phases merge origin and get the identical bytes back; when the push fails
the run behaves exactly as before this step (the snapshot stays in the working
tree and the later ``git add -A`` carries it as it always did).

Never fails the run: problems are printed as ``::warning::`` and exit 0.  Pushes are bounded (timeout per git call,
fixed attempts, growing sleeps) and never forced; the message carries
``[skip ci]`` so the push itself starts no Pages deploy (the run's normal
completion deploys it).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from app_store_storefronts import STATE_FILE  # noqa: E402

MESSAGE = "Daily GEO content: App Store storefront snapshot [skip ci]"
READBACK_TEST = "test_storefront_price_readback"
TA_NOTICE = Path(".github") / "scripts" / "ta_finder_notice.py"


class SnapshotCommitError(RuntimeError):
    pass


def _warn(title: str, text: str) -> None:
    print(f"::warning title={title}::{text}")


def _git(root: Path, *args: str, timeout: int = 180, check: bool = True):
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise SnapshotCommitError(
            f"git {' '.join(args)} 失敗：{result.stderr.strip()[-400:]}"
        )
    return result


def _blob(root: Path, rev: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{rev}:{STATE_FILE}"],
        cwd=str(root),
        capture_output=True,
        timeout=180,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def _changed(root: Path) -> bool:
    status = _git(root, "status", "--porcelain", "--", STATE_FILE).stdout
    return bool(status.strip())


def run_own_checks(root: Path, *, now: str | None = None) -> list[str]:
    """The snapshot's own gate; returns failure lines (empty = green)."""
    failures: list[str] = []
    tests = HERE / "tests"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-q", READBACK_TEST],
        cwd=str(tests),
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-5:]
        failures.append(f"{READBACK_TEST} 紅燈：" + " | ".join(tail))
    previous = _blob(root, "HEAD")
    with tempfile.TemporaryDirectory() as scratch:
        command = [
            sys.executable,
            str(HERE / "check_storefront_snapshot.py"),
            "--pages",
            str(root),
        ]
        if previous is not None:
            previous_path = Path(scratch) / "previous.json"
            previous_path.write_bytes(previous)
            command += ["--previous", str(previous_path)]
        if now:
            command += ["--now", now]
        result = subprocess.run(
            command, text=True, capture_output=True, timeout=120, check=False
        )
    if result.returncode != 0:
        lines = result.stdout.strip().splitlines()[:5]
        failures.append("快照格式檢查紅燈：" + " | ".join(lines))
    return failures


def _ta_trailer(worktree: Path) -> str:
    notice = worktree / TA_NOTICE
    if not notice.is_file():
        return ""
    with tempfile.TemporaryDirectory() as scratch:
        trailer = Path(scratch) / "ta-finder-trailer.txt"
        result = subprocess.run(
            [sys.executable, str(notice), "--staged", "--trailer-file", str(trailer)],
            cwd=str(worktree),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        print(result.stdout, end="")
        if result.returncode != 0:
            _warn("TA finder 提醒失敗", "ta_finder_notice.py 沒跑完；照常發布")
            return ""
        return trailer.read_text(encoding="utf-8").strip() if trailer.is_file() else ""


def _push_attempt(
    root: Path, remote: str, branch: str, base: bytes | None, timeout: int
) -> bool:
    """One bounded attempt; True when origin now carries this snapshot."""
    _git(root, "fetch", "--no-tags", remote, branch, timeout=timeout)
    tip = _git(root, "rev-parse", "FETCH_HEAD").stdout.strip()
    ours = (root / STATE_FILE).read_bytes()
    remote_copy = _blob(root, tip)
    if remote_copy == ours:
        print("origin 已有同一份快照，不必再推。")
        return True
    if remote_copy != base:
        # Someone else changed the snapshot on main (e.g. a person editing a
        # once-paid listing).  Never overwrite it from here; the later phases
        # merge origin as before.
        raise SnapshotCommitError("origin 上的快照已被別人改過；不覆蓋、本步不推")
    worktree = Path(tempfile.mkdtemp(prefix="snapshot-wt-"))
    shutil.rmtree(worktree)
    _git(root, "worktree", "add", "--detach", str(worktree), tip)
    try:
        (worktree / STATE_FILE).write_bytes(ours)
        _git(worktree, "add", "--", STATE_FILE)
        command = ["commit", "-q", "-m", MESSAGE]
        trailer = _ta_trailer(worktree)
        if trailer:
            command += ["-m", trailer]
        _git(worktree, *command, "--", STATE_FILE)
        pushed = _git(
            worktree,
            "push",
            remote,
            f"HEAD:refs/heads/{branch}",
            timeout=timeout,
            check=False,
        )
        if pushed.returncode != 0:
            print(f"push 被拒（main 移動或推送失敗）：{pushed.stderr.strip()[-200:]}")
        return pushed.returncode == 0
    finally:
        _git(root, "worktree", "remove", "--force", str(worktree), check=False)


def publish(
    root: Path,
    *,
    remote: str = "origin",
    branch: str = "main",
    attempts: int = 5,
    retry_delay: int = 10,
    timeout: int = 180,
    now: str | None = None,
) -> str:
    """Return one of: unchanged, red, pushed, not-pushed.

    Never commits on, stages into or rewrites the caller's checkout.
    """
    if not (root / STATE_FILE).is_file():
        print("沒有快照檔，本步不做事。")
        return "unchanged"
    if not _changed(root):
        print("快照與 HEAD 相同，本步不做事。")
        return "unchanged"
    failures = run_own_checks(root, now=now)
    if failures:
        for line in failures:
            _warn("快照單獨提交略過", line)
        return "red"
    base = _blob(root, "HEAD")
    for attempt in range(1, attempts + 1):
        print(f"snapshot push attempt {attempt}/{attempts}")
        try:
            if _push_attempt(root, remote, branch, base, timeout):
                return "pushed"
        except SnapshotCommitError as error:
            _warn("快照推送略過", str(error))
            return "not-pushed"
        except subprocess.TimeoutExpired:
            print("git 呼叫逾時")
        if attempt < attempts:
            time.sleep(attempt * retry_delay)
    _warn("快照推送略過", f"推送 {attempts} 次都沒成功；快照留在工作樹，照舊由後面的提交步帶")
    return "not-pushed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=os.environ.get("GITHUB_WORKSPACE", str(HERE / "pages")),
        help="指南站 git 根目錄（快照所在處）",
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--retry-delay", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--now", help="格式檢查的判讀時間（ISO，測試用）")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        outcome = publish(
            root,
            remote=args.remote,
            branch=args.branch,
            attempts=args.attempts,
            retry_delay=args.retry_delay,
            timeout=args.timeout,
            now=args.now,
        )
    except (SnapshotCommitError, subprocess.TimeoutExpired, OSError) as error:
        _warn("快照單獨提交失敗", str(error))
        outcome = "error"
    print(f"storefront snapshot commit: {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
