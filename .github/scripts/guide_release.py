"""Guide site release lag: which commits on main the live site does not carry yet.

The live site is whatever the last *paired* release uploaded
(``.well-known/deployment.json`` ``source_commit``). A push to main only runs
the Pages preflight, so "green Actions" never meant "online" (2026-10-13 to
10-16 nothing was uploaded for three days while every run was green).

This module answers one question for both the auto release and the
watchdog: how long has deployable content been waiting on main?
Deployable means any path outside ``.github/``, ``.claude/`` and
``_engine/`` (automation, agent settings and the engine mirror are never
served as site content).
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from typing import Callable

NON_DEPLOYABLE_PREFIXES = (".github/", ".claude/", "_engine/")
MAX_COMMITS_SCANNED = 40
SHA = re.compile(r"^[0-9a-f]{40}$")


class ReleaseError(RuntimeError):
    """Raised when the lag cannot be judged (never silently up to date)."""


@dataclass(frozen=True)
class Pending:
    sha: str
    committed_at: float


def is_deployable(path: str) -> bool:
    return not any(path.startswith(prefix) for prefix in NON_DEPLOYABLE_PREFIXES)


def parse_time(value: object) -> float | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def live_source_commit(fetch: Callable[[str], bytes], site: str) -> str:
    payload = json.loads(fetch(f"{site.rstrip('/')}/.well-known/deployment.json").decode("utf-8"))
    generation = payload.get("generation") or {}
    source = str(payload.get("source_commit") or generation.get("pages_source_sha") or "")
    if not SHA.match(source):
        raise ReleaseError("live deployment.json has no full source commit")
    return source


def undeployed(api: Callable[[str], object], repo: str, live_sha: str, head: str = "main") -> list[Pending]:
    """Deployable commits on ``head`` that the live site lacks, oldest first.

    ``api`` is ``Gh.api`` (``gh api <path>`` parsed as JSON). A live commit
    that is not an ancestor of ``head`` is an error: the release state is
    unknown and must be looked at, not assumed fine.
    """
    compare = api(f"repos/{repo}/compare/{live_sha}...{head}") or {}
    status = compare.get("status")
    if status == "identical":
        return []
    if status != "ahead":
        raise ReleaseError(f"live source {live_sha[:8]} is not an ancestor of {head} ({status})")
    commits = list(compare.get("commits") or [])
    pending: list[Pending] = []
    for commit in commits[:MAX_COMMITS_SCANNED]:
        sha = str(commit.get("sha") or "")
        detail = api(f"repos/{repo}/commits/{sha}") or {}
        if any(is_deployable(str(item.get("filename") or "")) for item in detail.get("files") or []):
            stamp = parse_time(((commit.get("commit") or {}).get("committer") or {}).get("date"))
            if stamp is None:
                raise ReleaseError(f"commit {sha[:8]} has no committer date")
            pending.append(Pending(sha, stamp))
    if not pending and len(commits) > MAX_COMMITS_SCANNED:
        # Too many commits to inspect one by one: fall back to the aggregate
        # file list and date the wait from the last inspected commit.
        if any(is_deployable(str(item.get("filename") or "")) for item in compare.get("files") or []):
            last = commits[MAX_COMMITS_SCANNED - 1]
            stamp = parse_time(((last.get("commit") or {}).get("committer") or {}).get("date"))
            pending.append(Pending(str(last.get("sha") or ""), stamp or 0.0))
    return pending


def lag_hours(pending: list[Pending], now: float) -> float:
    return 0.0 if not pending else max(0.0, (now - pending[0].committed_at) / 3600.0)
