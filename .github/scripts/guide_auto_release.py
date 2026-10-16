"""Automatic paired release of the Guide site, plus the stale-deploy alarm.

Why: pages.yml only uploads on a paired ``workflow_dispatch``
(owned_feed_release + incremental_high_intent with exact Guide/Growth SHAs).
Pushes and Daily GEO runs only preflight. From 2026-10-13 13:56 to 10-16
nobody dispatched, so three days of new pages stayed 404 while Actions was
green. This job removes the human step:

1. If main has deployable commits the live site lacks, bind 00_GrowthEngine
   ``geo/pages`` to the checked-out Guide main and dispatch exactly one paired
   release (never while another paired release is queued or running, never a
   third try for the same Guide SHA after two failed ones).
2. If that content has waited more than ``--stale-hours``, keep one
   ``guide-deploy-stale`` issue open that mentions the owner; close it with a
   comment once the site has caught up.

Inputs never include secrets: the Growth checkout is already authenticated
by the workflow's deploy key, ``gh`` uses the job's GITHUB_TOKEN.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import guide_release as gr  # noqa: E402
from line_watchdog import Gh, _http_get  # noqa: E402

STALE_LABEL = "guide-deploy-stale"
STALE_TITLE = "指南站部署落後（guide-deploy-stale）"
OWNER_MENTION = "@alice51849"
MAX_FAILED_PAIRED_PER_SHA = 2
PAIRED_TITLE_PREFIX = "配對發布（會上線）"
GITLINK_PATH = "geo/pages"


def paired_title(guide_sha: str) -> str:
    return f"{PAIRED_TITLE_PREFIX} {guide_sha}"


def paired_runs(gh: Gh) -> list[dict]:
    runs = gh.runs("pages.yml", per_page=50, event="workflow_dispatch")
    return [run for run in runs if str(run.get("display_title") or "").startswith(PAIRED_TITLE_PREFIX)]


def decide(pending: list[gr.Pending], runs: list[dict], guide_sha: str, *, trigger_ok: bool) -> str:
    """Return ``up_to_date``, ``dispatch`` or a ``hold: <reason>`` string."""
    if not pending:
        return "up_to_date"
    if any(run.get("status") in {"queued", "in_progress", "waiting", "requested", "pending"} for run in runs):
        return "hold: a paired release is already queued or running"
    failed = [
        run for run in runs
        if run.get("display_title") == paired_title(guide_sha)
        and run.get("status") == "completed" and run.get("conclusion") != "success"
    ]
    if len(failed) >= MAX_FAILED_PAIRED_PER_SHA:
        return f"hold: {len(failed)} paired releases of {guide_sha[:12]} already failed"
    if not trigger_ok:
        return "hold: the triggering preflight did not succeed"
    return "dispatch"


def git(engine: Path, *argv: str, runner: Callable[..., str] | None = None) -> str:
    if runner is not None:
        return runner(["git", "-C", str(engine), *argv])
    done = subprocess.run(["git", "-C", str(engine), *argv], capture_output=True, text=True, timeout=180)
    if done.returncode != 0:
        raise gr.ReleaseError(f"git {argv[0]} failed: {done.stderr.strip()[:300]}")
    return done.stdout.strip()


def bind_gitlink(engine: Path, guide_sha: str, runner: Callable[..., str] | None = None) -> str:
    """Make 00_GrowthEngine main pin ``geo/pages`` to ``guide_sha``; return that Growth SHA."""
    for attempt in range(3):
        git(engine, "fetch", "-q", "--depth=1", "origin", "main", runner=runner)
        git(engine, "checkout", "-q", "--detach", "FETCH_HEAD", runner=runner)
        listed = git(engine, "ls-tree", "HEAD", GITLINK_PATH, runner=runner).split()
        if len(listed) >= 3 and listed[2] == guide_sha:
            return git(engine, "rev-parse", "HEAD", runner=runner)
        git(engine, "update-index", "--cacheinfo", f"160000,{guide_sha},{GITLINK_PATH}", runner=runner)
        git(engine, "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898299+github-actions[bot]@users.noreply.github.com",
            "commit", "-q", "-m", f"配對發布（自動）：geo/pages gitlink 綁到 Guide main {guide_sha[:12]}",
            runner=runner)
        try:
            git(engine, "push", "-q", "origin", "HEAD:main", runner=runner)
            return git(engine, "rev-parse", "HEAD", runner=runner)
        except gr.ReleaseError:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise gr.ReleaseError("could not bind the gitlink")  # pragma: no cover


def notification_hold(guide_root: Path) -> bool:
    policy = json.loads((guide_root / "_engine/geo/notification_policy.json").read_text(encoding="utf-8"))
    return bool(policy["notification_release_hold"])


def dispatch_paired(gh: Gh, guide_sha: str, growth_sha: str, live_sha: str, hold: bool) -> None:
    gh.dispatch("pages.yml", {
        "owned_feed_release": "true",
        "incremental_high_intent": "true",
        "notification_release_hold": "true" if hold else "false",
        "expected_guide_sha": guide_sha,
        "expected_growth_sha": growth_sha,
        "previous_guide_revision": live_sha,
    })


def stale_issue(gh: Gh) -> dict | None:
    text = gh.runner(["gh", "issue", "list", "--repo", gh.repo, "--label", STALE_LABEL,
                      "--state", "open", "--json", "number,title", "--limit", "5"])
    for item in json.loads(text or "[]"):
        if item.get("title") == STALE_TITLE:
            return item
    return None


def stale_body(live_sha: str, guide_sha: str, pending: list[gr.Pending], lag: float, action: str) -> str:
    oldest = dt.datetime.fromtimestamp(pending[0].committed_at, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return "\n".join([
        f"{OWNER_MENTION} 指南站線上版本落後 main **{lag:.1f} 小時**（門檻 6 小時）。",
        "",
        f"- 線上 source_commit：`{live_sha}`",
        f"- Guide main：`{guide_sha}`",
        f"- 尚未上線的內容 commit：{len(pending)} 個，最早 `{pending[0].sha[:12]}`（{oldest}）",
        f"- 自動配對發布：{action}",
        "",
        "push 觸發的 Pages run 只做 preflight，綠燈不代表上線；只有「配對發布（會上線）」的 run 會上傳。",
        "恢復後這張 issue 會自動留言並關閉（guide-auto-release.yml）。",
    ])


def reconcile_stale(gh: Gh, body: str | None) -> str:
    existing = stale_issue(gh)
    if body is None:
        if existing:
            gh.runner(["gh", "issue", "comment", str(existing["number"]), "--repo", gh.repo,
                       "--body", "已恢復：線上版本已包含 main 上所有內容 commit。"])
            gh.runner(["gh", "issue", "close", str(existing["number"]), "--repo", gh.repo])
            return "issue_closed"
        return "no_issue"
    if existing:
        gh.runner(["gh", "issue", "edit", str(existing["number"]), "--repo", gh.repo, "--body", body])
        return "issue_updated"
    gh.runner(["gh", "label", "create", STALE_LABEL, "--repo", gh.repo, "--force",
               "--color", "B60205", "--description", "Guide site lags main (auto-managed)"])
    gh.runner(["gh", "issue", "create", "--repo", gh.repo, "--title", STALE_TITLE,
               "--label", STALE_LABEL, "--body", body])
    return "issue_created"


def run(*, gh: Gh, fetch: Callable[[str], bytes], site: str, guide_root: Path, guide_sha: str,
        engine: Path | None, now: float, stale_hours: float, trigger_ok: bool,
        dry_run: bool, git_runner: Callable[..., str] | None = None) -> dict:
    live_sha = gr.live_source_commit(fetch, site)
    pending = gr.undeployed(gh.api, gh.repo, live_sha)
    lag = gr.lag_hours(pending, now)
    action = decide(pending, paired_runs(gh), guide_sha, trigger_ok=trigger_ok)
    growth_sha = None
    if action == "dispatch":
        if dry_run:
            action = "dispatch (dry run)"
        else:
            if engine is None:
                raise gr.ReleaseError("--engine-dir is required to dispatch")
            growth_sha = bind_gitlink(engine, guide_sha, runner=git_runner)
            dispatch_paired(gh, guide_sha, growth_sha, live_sha, notification_hold(guide_root))
            action = "dispatched"
    body = stale_body(live_sha, guide_sha, pending, lag, action) if pending and lag > stale_hours else None
    issue = "skipped (dry run)" if dry_run else reconcile_stale(gh, body)
    return {"live": live_sha, "guide": guide_sha, "growth": growth_sha, "pending": len(pending),
            "lag_hours": round(lag, 2), "action": action, "issue": issue}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--site", default="https://alice51849.github.io/ios-app-guide")
    parser.add_argument("--guide-root", type=Path, default=Path("."))
    parser.add_argument("--engine-dir", type=Path)
    parser.add_argument("--stale-hours", type=float, default=6.0)
    parser.add_argument("--trigger-conclusion", default="success",
                        help="conclusion of the triggering workflow_run ('success' for schedule/dispatch)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    guide_sha = subprocess.run(["git", "-C", str(args.guide_root), "rev-parse", "HEAD"],
                               capture_output=True, text=True, check=True).stdout.strip()
    result = run(gh=Gh(args.repo), fetch=_http_get, site=args.site, guide_root=args.guide_root,
                 guide_sha=guide_sha, engine=args.engine_dir,
                 now=dt.datetime.now(dt.timezone.utc).timestamp(), stale_hours=args.stale_hours,
                 trigger_ok=args.trigger_conclusion in {"success", ""}, dry_run=args.dry_run)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"## 指南站自動配對發布\n\n```json\n{text}\n```\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
