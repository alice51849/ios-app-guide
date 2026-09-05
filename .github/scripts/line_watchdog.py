#!/usr/bin/env python3
"""Daily line watchdog: judge every growth line by real evidence, then heal or alert.

A green workflow run is not success. Each line is judged by (a) a recent
successful run *and* (b) fresh delivery evidence (platform IDs in the durable
state files, or the live deployment record / Telegram message_id for the
Guide). Stale lines are re-triggered at most twice per 24 hours through
``gh workflow run``; anything still red is written to a single ``line-health``
GitHub Issue. Nothing here ever types into a session, messages another
agent, touches Mastodon (permanently retired) or calls an LLM API.

The same file is committed to threads-autopilot and ios-app-guide; the
``--profile`` flag selects the repository contract. Only the repository's own
``GITHUB_TOKEN`` is needed (actions: write, issues: write, contents: read).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable

HOUR = 3600.0
MAX_RETRIGGERS_PER_DAY = 2
ISSUE_TITLE = "line-health"
ISSUE_LABEL = "line-health"

# Workflows that must succeed at least once inside ``max_age_hours``. Manual-only,
# weekly-or-slower and manually disabled workflows are deliberately absent or
# carry a wide window; Mastodon has no workflow and is retired (capacity 0).
PROFILES: dict[str, dict] = {
    "threads-autopilot": {
        "workflows": {
            "post.yml": 24,
            "multi.yml": 24,
            "nostr.yml": 24,
            "devto.yml": 30,
            "frontpage.yml": 30,
            "standard_site.yml": 30,
            "passive_appviews.yml": 30,
            "threads-token-maintenance.yml": 30,
            "bluesky-profile.yml": 8 * 24,
        },
        "evidence": ["threads_receipts", "bluesky_receipts", "nostr_receipts"],
    },
    "ios-app-guide": {
        "workflows": {
            "geo-daily.yml": 24,
            "pages.yml": 48,
            "indexnow-daily.yml": 30,
            "portfolio-daily.yml": 30,
            "telegram-daily.yml": 30,
            "arquivo-pt-daily.yml": 30,
            "software-heritage-daily.yml": 30,
            "sov-weekly.yml": 8 * 24,
        },
        "evidence": ["guide_deployment", "telegram_message_id"],
    },
}
EVIDENCE_MAX_AGE_HOURS = {
    "threads_receipts": 24,
    "bluesky_receipts": 24,
    "nostr_receipts": 24,
    "guide_deployment": 48,
    "telegram_message_id": 30,
}


class WatchdogError(RuntimeError):
    """Raised when the watchdog itself cannot judge (never silently green)."""


def parse_time(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.timestamp()


def iso(ts: float | None) -> str:
    if ts is None:
        return "never"
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Gh:
    """Thin ``gh`` CLI wrapper; ``runner`` is injectable for tests."""

    def __init__(self, repo: str, runner: Callable[[list[str]], str] | None = None):
        self.repo = repo
        self.runner = runner or self._run

    @staticmethod
    def _run(argv: list[str]) -> str:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        if completed.returncode != 0:
            raise WatchdogError(f"{' '.join(argv[:3])} failed: {completed.stderr.strip()[:300]}")
        return completed.stdout

    def api(self, path: str, *, paginate: bool = False) -> object:
        argv = ["gh", "api", path]
        if paginate:
            argv += ["--paginate", "--slurp"]
        text = self.runner(argv)
        return json.loads(text) if text.strip() else None

    def workflows(self) -> dict[str, dict]:
        payload = self.api(f"repos/{self.repo}/actions/workflows?per_page=100")
        result = {}
        for item in payload.get("workflows", []):
            name = item["path"].rsplit("/", 1)[-1]
            result[name] = {"id": item["id"], "state": item["state"], "name": item["name"]}
        return result

    def runs(self, workflow_file: str, *, per_page: int = 30, **params: str) -> list[dict]:
        query = "&".join([f"per_page={per_page}", *(f"{k}={v}" for k, v in params.items())])
        payload = self.api(f"repos/{self.repo}/actions/workflows/{workflow_file}/runs?{query}")
        return list((payload or {}).get("workflow_runs", []))

    def dispatch(self, workflow_file: str) -> None:
        self.runner(["gh", "workflow", "run", workflow_file, "--repo", self.repo])

    def run_log(self, run_id: int) -> str:
        return self.runner(["gh", "run", "view", str(run_id), "--repo", self.repo, "--log"])

    def is_ancestor_of_main(self, sha: str) -> bool:
        payload = self.api(f"repos/{self.repo}/compare/{sha}...main")
        return payload.get("status") in {"identical", "ahead"}

    def open_issue(self) -> dict | None:
        text = self.runner([
            "gh", "issue", "list", "--repo", self.repo, "--label", ISSUE_LABEL,
            "--state", "open", "--json", "number,title", "--limit", "5",
        ])
        for item in json.loads(text or "[]"):
            if item.get("title") == ISSUE_TITLE:
                return item
        return None

    def ensure_label(self) -> None:
        self.runner([
            "gh", "label", "create", ISSUE_LABEL, "--repo", self.repo, "--force",
            "--color", "B60205", "--description", "Growth line watchdog (auto-managed)",
        ])

    def create_issue(self, body: str) -> None:
        self.runner([
            "gh", "issue", "create", "--repo", self.repo, "--title", ISSUE_TITLE,
            "--label", ISSUE_LABEL, "--body", body,
        ])

    def edit_issue(self, number: int, body: str) -> None:
        self.runner(["gh", "issue", "edit", str(number), "--repo", self.repo, "--body", body])

    def comment_and_close(self, number: int, body: str) -> None:
        self.runner(["gh", "issue", "comment", str(number), "--repo", self.repo, "--body", body])
        self.runner(["gh", "issue", "close", str(number), "--repo", self.repo])


# --------------------------------------------------------------------------- #
# Workflow freshness
# --------------------------------------------------------------------------- #
def judge_workflow(gh: Gh, workflow_file: str, max_age_hours: float, now: float,
                   *, dispatch: bool) -> dict:
    runs = gh.runs(workflow_file)
    latest_success = max(
        (parse_time(run.get("updated_at") or run.get("created_at")) or 0.0
         for run in runs if run.get("conclusion") == "success"),
        default=None,
    )
    if latest_success == 0.0:
        latest_success = None
    in_progress = any(run.get("status") in {"in_progress", "queued", "waiting", "pending"} for run in runs)
    fresh = latest_success is not None and now - latest_success <= max_age_hours * HOUR
    row = {
        "line": workflow_file, "kind": "workflow", "fresh": fresh,
        "last_success": iso(latest_success), "max_age_hours": max_age_hours,
        "in_progress": in_progress, "action": "none", "note": "",
    }
    if fresh:
        return row
    latest = runs[0] if runs else None
    if latest is not None:
        row["note"] = f"latest run {latest.get('status')}/{latest.get('conclusion')} at {latest.get('updated_at')}"
    if in_progress:
        row["action"] = "wait_in_progress"
        return row
    since = iso(now - 24 * HOUR)
    recent_dispatches = [
        run for run in gh.runs(workflow_file, event="workflow_dispatch", created=f">={since}")
        if (run.get("actor") or {}).get("login") == "github-actions[bot]"
    ]
    row["auto_retriggers_24h"] = len(recent_dispatches)
    if len(recent_dispatches) >= MAX_RETRIGGERS_PER_DAY:
        row["action"] = "retrigger_budget_exhausted"
        return row
    if dispatch:
        gh.dispatch(workflow_file)
        row["action"] = "retriggered"
    else:
        row["action"] = "would_retrigger"
    return row


# --------------------------------------------------------------------------- #
# Delivery evidence (real platform IDs, never queued/outbox counters)
# --------------------------------------------------------------------------- #
def _load(root: Path, name: str) -> dict:
    path = root / name
    if not path.is_file():
        raise WatchdogError(f"missing durable state {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def threads_receipts(root: Path) -> tuple[float | None, int]:
    state = _load(root, "state.json")
    stamps = [
        parse_time(item.get("published_at"))
        for item in (state.get("delivery_receipts") or {}).values()
        if isinstance(item, dict) and item.get("post_id") and item.get("permalink")
    ]
    stamps = [s for s in stamps if s]
    return (max(stamps) if stamps else None), len(stamps)


def bluesky_receipts(root: Path) -> tuple[float | None, int]:
    state = _load(root, "state_bluesky.json")
    stamps = [
        parse_time(item.get("published_at"))
        for item in (state.get("delivery_receipts") or {}).values()
        if isinstance(item, dict) and str(item.get("uri", "")).startswith("at://") and item.get("cid")
    ]
    stamps = [s for s in stamps if s]
    return (max(stamps) if stamps else None), len(stamps)


def nostr_receipts(root: Path) -> tuple[float | None, int]:
    state = _load(root, "state_nostr.json")
    stamps = []
    for item in (state.get("relay_attempts") or {}).values():
        if not isinstance(item, dict) or item.get("status") != "acknowledged":
            continue
        acked = item.get("acknowledged_relays") or []
        required = int(item.get("required_acknowledgements") or 1)
        event_id = str(item.get("event_id", ""))
        if len(acked) >= required and len(event_id) == 64:
            stamp = parse_time(item.get("updated_at"))
            if stamp:
                stamps.append(stamp)
    return (max(stamps) if stamps else None), len(stamps)


def guide_deployment(gh: Gh, fetch: Callable[[str], bytes], site: str) -> tuple[float | None, str]:
    url = f"{site.rstrip('/')}/.well-known/deployment.json"
    payload = json.loads(fetch(url).decode("utf-8"))
    generation = payload.get("generation") or {}
    stamp = parse_time(generation.get("generated_at") or payload.get("generated_at"))
    source = str(payload.get("source_commit") or generation.get("pages_source_sha") or "")
    if len(source) < 7:
        raise WatchdogError("live deployment.json has no source commit")
    if not gh.is_ancestor_of_main(source):
        return None, f"live source {source[:8]} is not an ancestor of main"
    return stamp, f"live source {source[:8]} is on main"


def telegram_message_id(gh: Gh) -> tuple[float | None, str]:
    runs = [run for run in gh.runs("telegram-daily.yml") if run.get("conclusion") == "success"]
    if not runs:
        return None, "no successful telegram-daily run"
    latest = runs[0]
    log = gh.run_log(int(latest["id"]))
    if "message_id" not in log:
        return None, f"run {latest['id']} succeeded without a Telegram message_id"
    return parse_time(latest.get("updated_at") or latest.get("created_at")), f"run {latest['id']} carries message_id"


def judge_evidence(name: str, stamp: float | None, note: str, now: float) -> dict:
    max_age = EVIDENCE_MAX_AGE_HOURS[name]
    fresh = stamp is not None and now - stamp <= max_age * HOUR
    return {
        "line": name, "kind": "evidence", "fresh": fresh, "last_success": iso(stamp),
        "max_age_hours": max_age, "in_progress": False, "action": "none", "note": note,
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def render_table(rows: list[dict], now: float) -> str:
    lines = [
        f"Judged at {iso(now)} by evidence, not by green runs.",
        "",
        "| line | kind | status | last real success | window (h) | action | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        status = "🟢 fresh" if row["fresh"] else "🔴 stale"
        lines.append(
            f"| {row['line']} | {row['kind']} | {status} | {row['last_success']} | "
            f"{row['max_age_hours']} | {row['action']} | {row['note'] or ''} |"
        )
    lines += [
        "",
        "Root-cause hints: a stale *workflow* with a fresh *evidence* row means the schedule "
        "slipped but delivery is fine; fresh workflow + stale evidence means green runs are "
        "not delivering (check receipts/platform IDs, not run conclusions). Mastodon is "
        "permanently retired (capacity 0) and is never counted here.",
    ]
    return "\n".join(lines)


def reconcile_issue(gh: Gh, rows: list[dict], now: float) -> str:
    red = [row for row in rows if not row["fresh"]]
    body = render_table(rows, now)
    existing = gh.open_issue()
    if red:
        gh.ensure_label()
        if existing:
            gh.edit_issue(int(existing["number"]), body)
            return "issue_updated"
        gh.create_issue(body)
        return "issue_created"
    if existing:
        gh.comment_and_close(int(existing["number"]), "healed: every line is fresh again.\n\n" + body)
        return "issue_closed"
    return "all_fresh"


def telegram_alert(rows: list[dict], now: float, token: str, chat_id: str,
                   post: Callable[[str, dict], None]) -> bool:
    red = [row for row in rows if not row["fresh"]]
    if not red or not token or not chat_id:
        return False
    text = "line-health 🔴 " + iso(now) + "\n" + "\n".join(
        f"- {row['line']}: last {row['last_success']} ({row['action']})" for row in red
    )
    post(f"https://api.telegram.org/bot{token}/sendMessage", {"chat_id": chat_id, "text": text[:3900]})
    return True


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "line-watchdog"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(2_000_000)


def _http_post(url: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read(10_000)


def run(profile_name: str, repo: str, root: Path, *, now: float, gh: Gh,
        dispatch: bool, fetch: Callable[[str], bytes] = _http_get,
        site: str = "https://open.cait518.cc/ios-app-guide") -> list[dict]:
    profile = PROFILES[profile_name]
    known = gh.workflows()
    rows: list[dict] = []
    for workflow_file, max_age in profile["workflows"].items():
        meta = known.get(workflow_file)
        if meta is None or meta["state"] != "active":
            rows.append({
                "line": workflow_file, "kind": "workflow", "fresh": True, "last_success": "n/a",
                "max_age_hours": max_age, "in_progress": False, "action": "skipped",
                "note": f"workflow {meta['state'] if meta else 'missing'} (not judged)",
            })
            continue
        rows.append(judge_workflow(gh, workflow_file, max_age, now, dispatch=dispatch))
    for name in profile["evidence"]:
        if name == "threads_receipts":
            stamp, count = threads_receipts(root); note = f"{count} confirmed Threads receipts"
        elif name == "bluesky_receipts":
            stamp, count = bluesky_receipts(root); note = f"{count} dated uri+cid receipts"
        elif name == "nostr_receipts":
            stamp, count = nostr_receipts(root); note = f"{count} quorum-acknowledged events"
        elif name == "guide_deployment":
            stamp, note = guide_deployment(gh, fetch, site)
        elif name == "telegram_message_id":
            stamp, note = telegram_message_id(gh)
        else:  # pragma: no cover
            raise WatchdogError(f"unknown evidence {name}")
        rows.append(judge_evidence(name, stamp, note, now))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--repo", required=True, help="owner/name of this repository")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, default=Path("line-health.json"))
    parser.add_argument("--no-dispatch", action="store_true", help="judge only, never gh workflow run")
    parser.add_argument("--no-issue", action="store_true", help="judge only, never touch issues")
    parser.add_argument("--telegram", action="store_true",
                        help="send a Telegram alert on red using TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID")
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    gh = Gh(args.repo)
    rows = run(args.profile, args.repo, args.root, now=now, gh=gh, dispatch=not args.no_dispatch)
    issue = "skipped" if args.no_issue else reconcile_issue(gh, rows, now)
    alerted = False
    if args.telegram:
        try:
            alerted = telegram_alert(
                rows, now, os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
                os.environ.get("TELEGRAM_CHAT_ID", "").strip(), _http_post,
            )
        except Exception as error:  # alerting must never turn the watchdog itself red
            print(f"telegram alert failed: {error}", file=sys.stderr)
    red = [row["line"] for row in rows if not row["fresh"]]
    report = {"judged_at": iso(now), "profile": args.profile, "repo": args.repo,
              "rows": rows, "red": red, "issue": issue, "telegram_alerted": alerted}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(render_table(rows, now) + "\n")
    print(render_table(rows, now))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
