#!/usr/bin/env python3
"""Alert fallback for the line watchdog: one GitHub issue when no private Telegram alert chat exists.

``line_alert.py`` sends internal alerts only to ``TELEGRAM_ALERT_CHAT_ID`` and
never falls back to the public promo chat (that rule stays in
``telegram_alert_guard.py``). On 2026-10-18 that secret was not set, so seven
red lines -- the self-hosted runners down for about an hour, jobs queued
04-14 UTC -- reached nobody (``alert_chat_missing``). This script is the free
fallback that needs no owner step: GitHub e-mails / pushes the repository
owner when an issue is opened or commented on.

While the private alert chat is missing (or refused as invalid / public):

* red lines and no open alert issue -> open ``外宣線紅燈警報`` (label ``alert``);
* the issue is open and a line turned red that the issue did not list yet ->
  one comment naming only the new lines, and the body is updated;
* the same red lines again -> nothing (no duplicate comment, no edit);
* every line fresh again -> one "全部恢復" comment and the issue is closed.

The red-line set lives in a hidden marker in the issue body, so no other state
is needed. ``--scope`` lets a partial judge (``runner-domain-probe.yml``,
two lines every 3 hours) update only its own lines: red lines outside the scope
are kept from the issue as they were. When the private chat is configured the
issue is never opened, but an open one is still closed once everything is
fresh. The workflow passes ``TELEGRAM_ALERT_CHAT_ID`` only so its presence can
be checked; it is never printed. The same file is committed to
00_GrowthEngine, ios-app-guide and threads-autopilot.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import line_alert  # noqa: E402
import telegram_alert_guard as guard  # noqa: E402

ISSUE_TITLE = "外宣線紅燈警報"
ISSUE_LABEL = "alert"
LABEL_COLOR = "B60205"
LABEL_DESCRIPTION = "外宣線看門狗紅燈警報（自動開關）"
MARKER_RE = re.compile(r"<!-- alert-red-lines: (\[.*?\]) -->")
MAX_BODY = 60000

Runner = Callable[[list[str]], str]


def _run(argv: list[str]) -> str:
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        raise RuntimeError(f"{' '.join(argv[:3])} failed: {completed.stderr.strip()[:300]}")
    return completed.stdout


def marker(lines: list[str]) -> str:
    return f"<!-- alert-red-lines: {json.dumps(sorted(lines), ensure_ascii=False)} -->"


def listed_lines(body: str) -> list[str]:
    match = MARKER_RE.search(body or "")
    if not match:
        return []
    try:
        value = json.loads(match.group(1))
    except ValueError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def merged_red(report: dict | None, previous: list[str], scope: tuple[str, ...]) -> tuple[list[str], dict]:
    """Red lines after this judge: the report's own, plus (with a scope) earlier ones outside it."""
    rows = {str(row["line"]): row for row in line_alert.red_rows(report)}
    if scope:
        owned = set(scope) | {line_alert.SELF_LINE}
        kept = [line for line in previous if line not in owned and line not in rows]
    else:
        kept = []
    return sorted(set(rows) | set(kept)), rows


def render(lines: list[str], rows: dict, now: float, *, label: str, run_url: str) -> str:
    parts = [f"🔴 外宣線紅燈（{label}）：目前 {len(lines)} 條", ""]
    for line in lines:
        row = rows.get(line)
        parts.append(line_alert.describe(row, now) if row else f"• {line}：前一次判定為紅，這一輪沒有重新判定")
    parts += [
        "",
        "這張 issue 是私人 Telegram 警報頻道（TELEGRAM_ALERT_CHAT_ID）沒設定時的備援；"
        "同一條紅線不會重複留言，全部恢復時會自動關閉。",
        f"更新時間 {line_alert.iso(now)}（UTC）" + (f"\nrun：{run_url}" if run_url else ""),
        "",
        marker(lines),
    ]
    body = "\n".join(parts)
    if len(body) > MAX_BODY:
        body = body[: MAX_BODY - len(marker(lines)) - 2] + "…\n" + marker(lines)
    return body


def open_issue(run: Runner, repo: str, title: str) -> dict | None:
    text = run(["gh", "issue", "list", "--repo", repo, "--label", ISSUE_LABEL, "--state", "open",
                "--json", "number,title,body", "--limit", "50"])
    for item in json.loads(text or "[]"):
        if item.get("title") == title:
            return item
    return None


def fallback_active(chat_id: str, public_chat_ids: tuple[str, ...]) -> bool:
    """True while internal Telegram alerts cannot go out (chat missing, invalid or public)."""
    return guard.alert_target_problem(chat_id, public_chat_ids) is not None


def reconcile(report: dict | None, *, repo: str, label: str, run_url: str, now: float, active: bool,
              scope: tuple[str, ...] = (), title: str = ISSUE_TITLE, run: Runner = _run) -> str:
    existing = open_issue(run, repo, title)
    previous = listed_lines(existing.get("body", "")) if existing else []
    lines, rows = merged_red(report, previous, scope)
    if not lines:
        if existing:
            run(["gh", "issue", "comment", str(existing["number"]), "--repo", repo, "--body",
                 f"🟢 外宣線全部恢復新鮮（{label}），自動關閉。\n判定時間 {line_alert.iso(now)}（UTC）"
                 + (f"\nrun：{run_url}" if run_url else "")])
            run(["gh", "issue", "close", str(existing["number"]), "--repo", repo])
            return "closed"
        return "all_fresh"
    if not active:
        return "telegram_configured"
    body = render(lines, rows, now, label=label, run_url=run_url)
    if not existing:
        run(["gh", "label", "create", ISSUE_LABEL, "--repo", repo, "--force",
             "--color", LABEL_COLOR, "--description", LABEL_DESCRIPTION])
        run(["gh", "issue", "create", "--repo", repo, "--title", title, "--label", ISSUE_LABEL, "--body", body])
        return "created"
    if sorted(previous) == lines:
        return "unchanged"
    new = [line for line in lines if line not in previous]
    run(["gh", "issue", "edit", str(existing["number"]), "--repo", repo, "--body", body])
    if not new:
        return "updated"  # some lines recovered, none newly red: body only, no notification
    comment = [f"🔴 新增紅線（{label}）：{len(new)} 條", ""]
    comment += [line_alert.describe(rows[line], now) for line in new if line in rows]
    comment += ["", f"判定時間 {line_alert.iso(now)}（UTC）" + (f"\nrun：{run_url}" if run_url else "")]
    run(["gh", "issue", "comment", str(existing["number"]), "--repo", repo, "--body", "\n".join(comment)[:MAX_BODY]])
    return "commented"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", type=Path, required=True, help="line-health.json written by line_watchdog.py")
    parser.add_argument("--repo", required=True, help="owner/name of this repository")
    parser.add_argument("--label", required=True, help="repository label shown in the issue")
    parser.add_argument("--scope", default="", help="comma-separated lines this judge owns (partial probe)")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args(argv)
    active = fallback_active(os.environ.get(guard.ALERT_CHAT_ENV, "").strip(), guard.public_chat_ids_from_env())
    scope = tuple(part.strip() for part in args.scope.split(",") if part.strip())
    try:
        status = reconcile(line_alert.load_json(args.report), repo=args.repo, label=args.label,
                           run_url=args.run_url, now=dt.datetime.now(dt.timezone.utc).timestamp(),
                           active=active, scope=scope)
    except Exception as error:  # noqa: BLE001 - surface it, but never hide the watchdog's own result
        print(f"::error::alert issue fallback failed: {type(error).__name__}: {str(error)[:300]}")
        return 1
    print(f"alert issue fallback: {status} (private Telegram alert chat "
          f"{'missing or refused' if active else 'configured'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
