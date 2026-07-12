#!/usr/bin/env python3
"""Archive one public outreach repository with Software Heritage each day."""

from __future__ import annotations

import datetime as dt
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from social_post_common import HTTPStatusError, RequestError, request_json


OWNER = "alice51849"
BASE_DATE = dt.date(2026, 7, 12)
GITHUB_API = "https://api.github.com"
SWH_API = "https://archive.softwareheritage.org/api/1/origin/save/git/url"
USER_AGENT = (
    "CaitlynPublicRepoArchiver/1.0 "
    "(+https://github.com/alice51849/ios-app-guide)"
)
PRIORITY = (
    "awesome-zhuyin-bopomofo-apps",
    "awesome-ios-language-learning",
    "awesome-toeic-pay-once-apps",
    "awesome-ios-kids-learning",
    "awesome-family-travel-missions",
    "awesome-ios-for-students",
    "awesome-ios-productivity",
    "awesome-ios-health-wellness",
    "awesome-ios-money-budgeting",
    "awesome-ios-photo-utilities",
    "awesome-ios-privacy-first",
    "awesome-ios-everyday-utilities",
    "awesome-ios-pay-once",
    "awesome-pay-once-todo-apps",
    "ios-app-guide",
)
ACTIVE_TASKS = frozenset(
    ("not created", "not yet scheduled", "pending", "scheduled", "running")
)
SUCCESSFUL_VISITS = frozenset(("full", "partial"))


def _swh_headers() -> dict[str, str]:
    return {"Accept": "application/json", "User-Agent": USER_AGENT}


def _github_headers() -> dict[str, str]:
    headers = _swh_headers()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    return headers


def _api_json(
    request: urllib.request.Request,
    *,
    label: str,
    attempts: int = 3,
) -> object:
    return request_json(
        request,
        label=label,
        timeout=60,
        attempts=attempts,
        retry_delays=(15, 30),
        extra_transient=lambda status, body: (
            status == 403 and "rate" in body.lower()
        ),
    )


def discover_repositories() -> list[dict[str, object]]:
    payload: list[object] = []
    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {
                "per_page": "100",
                "page": str(page),
                "type": "owner",
                "sort": "full_name",
                "direction": "asc",
            }
        )
        request = urllib.request.Request(
            f"{GITHUB_API}/users/{OWNER}/repos?{query}",
            headers=_github_headers(),
        )
        chunk = _api_json(
            request, label=f"GitHub repository discovery page {page}"
        )
        if not isinstance(chunk, list):
            raise RequestError("GitHub repository discovery returned a non-list")
        payload.extend(chunk)
        if len(chunk) < 100:
            break
    else:
        raise RequestError("GitHub repository discovery exceeded ten pages")
    selected = {
        str(repo["name"]): repo
        for repo in payload
        if isinstance(repo, dict)
        and isinstance(repo.get("name"), str)
        and not repo.get("private")
        and not repo.get("archived")
        and (
            str(repo["name"]).startswith("awesome-")
            or repo["name"] == "ios-app-guide"
        )
    }
    if "ios-app-guide" not in selected:
        request = urllib.request.Request(
            f"{GITHUB_API}/repos/{OWNER}/ios-app-guide",
            headers=_github_headers(),
        )
        guide = _api_json(request, label="GitHub guide repository lookup")
        if not isinstance(guide, dict):
            raise RequestError("GitHub guide repository lookup returned invalid data")
        if guide.get("private") or guide.get("archived"):
            raise RequestError("GitHub guide repository is not public and active")
        selected["ios-app-guide"] = guide
    missing = [name for name in PRIORITY if name not in selected]
    if missing:
        raise RequestError(
            "Expected public outreach repositories are missing: "
            + ", ".join(missing)
        )
    names = [*PRIORITY]
    names.extend(sorted(set(selected) - set(names)))
    return [selected[name] for name in names]


def select_repository(
    repositories: list[dict[str, object]],
    *,
    today: dt.date | None = None,
    override: str = "",
) -> dict[str, object]:
    if not repositories:
        raise ValueError("No public outreach repositories were discovered")
    by_name = {str(repo["name"]): repo for repo in repositories}
    if override:
        if override not in by_name:
            raise ValueError(f"Repository is not in the public outreach pool: {override}")
        return by_name[override]
    today = dt.datetime.now(dt.timezone.utc).date() if today is None else today
    offset = (today - BASE_DATE).days
    if offset < 0:
        raise ValueError(f"Archive schedule predates {BASE_DATE.isoformat()}")
    return repositories[offset % len(repositories)]


def _parse_time(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            dt.timezone.utc
        )
    except ValueError:
        return None


def archive_decision(
    repository: dict[str, object],
    requests: list[dict[str, object]],
) -> tuple[bool, str]:
    for item in requests:
        if (
            item.get("save_request_status") in {"accepted", "pending"}
            and item.get("save_task_status") in ACTIVE_TASKS
        ):
            return False, f"request {item.get('id')} is {item.get('save_task_status')}"
    pushed_at = _parse_time(repository.get("pushed_at"))
    completed = [
        _parse_time(item.get("visit_date"))
        for item in requests
        if item.get("save_task_status") == "succeeded"
        and item.get("visit_status") in SUCCESSFUL_VISITS
    ]
    completed = [value for value in completed if value is not None]
    if pushed_at is not None and completed and max(completed) >= pushed_at:
        return False, "latest successful archive already includes current repository"
    return True, "repository is new or newer than its latest successful archive"


def status_url(origin_url: str) -> str:
    return f"{SWH_API}/{urllib.parse.quote(origin_url, safe=':/')}/"


def load_requests(origin_url: str) -> list[dict[str, object]]:
    request = urllib.request.Request(status_url(origin_url), headers=_swh_headers())
    try:
        payload = _api_json(request, label="Software Heritage status")
    except HTTPStatusError as error:
        if error.status == 404:
            return []
        raise
    if not isinstance(payload, list):
        raise RequestError("Software Heritage status returned a non-list")
    return [item for item in payload if isinstance(item, dict)]


def submit(origin_url: str) -> dict[str, object]:
    request = urllib.request.Request(
        status_url(origin_url),
        data=b"",
        headers=_swh_headers(),
        method="POST",
    )
    payload = _api_json(request, label="Software Heritage save request")
    if not isinstance(payload, dict):
        raise RequestError("Software Heritage save request returned invalid data")
    if payload.get("save_request_status") not in {"accepted", "pending"}:
        raise RequestError(
            "Software Heritage rejected the save request: "
            + str(payload.get("note") or payload)
        )
    return payload


def run(today: dt.date | None = None) -> dict[str, object] | None:
    repositories = discover_repositories()
    repository = select_repository(
        repositories,
        today=today,
        override=os.environ.get("SWH_REPOSITORY", "").strip(),
    )
    origin_url = str(repository["html_url"]).rstrip("/")
    requests = load_requests(origin_url)
    should_submit, reason = archive_decision(repository, requests)
    if not should_submit:
        print(f"Software Heritage: skip {repository['name']} ({reason})")
        return None
    result = submit(origin_url)
    print(
        "Software Heritage: accepted"
        f" repo={repository['name']}"
        f" request={result.get('id')}"
        f" task={result.get('save_task_status')}"
    )
    return result


def main() -> int:
    try:
        run()
        return 0
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Software Heritage archive failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
