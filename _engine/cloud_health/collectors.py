#!/usr/bin/env python3
"""GET-only evidence collectors adapted from the approved cloud-health v3 audit."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import socket
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

from .core import BLOCKED, EXPECTED_COUNT, EXPECTED_DIGEST, PASS, digest_value, iso_z


API = "https://api.github.com"
USER_AGENT = (
    "Lumi-Cloud-Health-Daily/1 "
    "(+https://alice51849.github.io/ios-app-guide/)"
)
MAX_BODY = 20 * 1024 * 1024
OUTREACH_REPOS = {
    "alice51849",
    "alice51849.github.io",
    "awesome-family-travel-missions",
    "awesome-zhuyin-bopomofo-apps",
    "geo-autopilot",
    "growth-agent",
    "ios-app-guide",
    "open-reference-datasets",
    "threads-autopilot",
}
MEASUREMENT_REPOS = {"apple-ads-autopilot"}
HIGH_FREQUENCY = {
    "multi-platform-autopilot",
    "nostr-outreach",
    "threads-autopilot",
}
SOCIAL_STATES = {
    "Threads": ("state.json", "publication_ledger", ("permalink",)),
    "Bluesky": ("state_bluesky.json", "publication_ledger", ("uri", "permalink")),
    "Mastodon": ("state_mastodon.json", "publication_ledger", ("permalink",)),
    "Nostr": ("state_nostr.json", "publication_ledger", ("event_id", "permalink")),
    "Dev.to": ("devto_state.json", "posted", ("url", "canonical_url")),
    "Frontpage": ("frontpage_state.json", "posts", ("at_uri", "appview_url")),
    "Standard.site": ("standard_site_state.json", "documents", ("at_uri",)),
}
SECRET_RE = re.compile(
    r"(?i)(authorization|bearer|token|secret|password)([=: ]+)(\S+)"
)


class EvidenceError(RuntimeError):
    """A current source could not be obtained or parsed."""


@dataclass(frozen=True)
class RawResponse:
    status: int
    body: bytes
    headers: dict[str, str]
    final_url: str


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(
            request, fp, code, msg, headers, newurl
        )
        if (
            redirected is not None
            and urlsplit(request.full_url).netloc
            != urlsplit(newurl).netloc
        ):
            redirected.remove_header("Authorization")
        return redirected


def _default_transport(url: str, headers: dict[str, str], timeout: float) -> RawResponse:
    request = Request(url, method="GET", headers=headers)
    opener = build_opener(_SafeRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                raise EvidenceError(f"GET response exceeds {MAX_BODY} bytes")
            return RawResponse(
                status=int(response.status),
                body=body,
                headers={key.lower(): value for key, value in response.headers.items()},
                final_url=response.geturl(),
            )
    except HTTPError as error:
        return RawResponse(
            status=int(error.code),
            body=error.read(512_000),
            headers={key.lower(): value for key, value in error.headers.items()},
            final_url=error.geturl(),
        )


class GetClient:
    """HTTP client whose transport cannot issue any verb other than GET."""

    def __init__(
        self,
        *,
        transport: Callable[[str, dict[str, str], float], RawResponse] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        attempts: int = 3,
        timeout: float = 30,
        github_token: str | None = None,
    ) -> None:
        self.transport = transport or _default_transport
        self.sleep = sleep
        self.attempts = attempts
        self.timeout = timeout
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

    @staticmethod
    def _safe_url(url: str) -> str:
        parsed = urlsplit(url)
        safe_query = []
        for pair in parsed.query.split("&") if parsed.query else []:
            key = pair.split("=", 1)[0]
            sensitive = {
                "authorization",
                "auth",
                "credential",
                "key",
                "sig",
                "signature",
                "token",
            }
            safe_query.append(
                f"{key}=[REDACTED]"
                if any(marker in key.lower() for marker in sensitive)
                else pair
            )
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, "&".join(safe_query), "")
        )

    def get(
        self,
        url: str,
        *,
        accept: str = "application/json",
        github_auth: bool = False,
    ) -> tuple[RawResponse, dict[str, Any]]:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise EvidenceError("only absolute HTTPS GET sources are allowed")
        headers = {
            "Accept": accept,
            "Cache-Control": "no-cache",
            "User-Agent": USER_AGENT,
        }
        if github_auth and self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        last: Exception | None = None
        for attempt in range(self.attempts):
            try:
                response = self.transport(url, headers, self.timeout)
                if response.status == 429:
                    retry_after = response.headers.get("retry-after", "1")
                    try:
                        delay = min(30.0, max(0.0, float(retry_after)))
                    except ValueError:
                        delay = float(2**attempt)
                    last = EvidenceError("HTTP 429 rate limited")
                    if attempt + 1 < self.attempts:
                        self.sleep(delay)
                        continue
                elif 500 <= response.status <= 599:
                    last = EvidenceError(f"HTTP {response.status}")
                    if attempt + 1 < self.attempts:
                        self.sleep(float(2**attempt))
                        continue
                receipt = {
                    "url": self._safe_url(url),
                    "final_url": self._safe_url(response.final_url),
                    "status": response.status,
                    "ok": 200 <= response.status < 400,
                    "bytes_read": len(response.body),
                    "sha256": hashlib.sha256(response.body).hexdigest(),
                    "etag": response.headers.get("etag"),
                    "last_modified": response.headers.get("last-modified"),
                    "fetched_at": iso_z(datetime.now(timezone.utc)),
                    "method": "GET",
                }
                return response, receipt
            except (URLError, TimeoutError, socket.timeout, OSError, EvidenceError) as error:
                last = error
                if attempt + 1 < self.attempts:
                    self.sleep(float(2**attempt))
        message = SECRET_RE.sub(r"\1\2[REDACTED]", str(last or "GET failed"))
        raise EvidenceError(message[:500])

    def json(
        self,
        url: str,
        *,
        github_auth: bool = False,
    ) -> tuple[Any, dict[str, Any]]:
        response, receipt = self.get(
            url, accept="application/vnd.github+json", github_auth=github_auth
        )
        if not receipt["ok"]:
            raise EvidenceError(f"GET {receipt['url']} -> HTTP {response.status}")
        try:
            return json.loads(response.body), receipt
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EvidenceError(f"invalid JSON from {receipt['url']}: {error}") from error


class GitHub:
    def __init__(self, client: GetClient) -> None:
        self.client = client

    def json(self, path: str) -> tuple[Any, dict[str, Any]]:
        return self.client.json(f"{API}{path}", github_auth=True)

    def bytes(
        self,
        path: str,
        *,
        accept: str = "application/vnd.github+json",
    ):
        return self.client.get(f"{API}{path}", accept=accept, github_auth=True)

    def pages(self, path: str, key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rows: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []
        page = 1
        while True:
            separator = "&" if "?" in path else "?"
            payload, receipt = self.json(f"{path}{separator}per_page=100&page={page}")
            receipts.append(receipt)
            batch = payload.get(key, []) if isinstance(payload, dict) else payload
            if not isinstance(batch, list):
                raise EvidenceError(f"GitHub pagination key {key} is not an array")
            rows.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return rows, receipts

    def file(self, repo: str, path: str) -> tuple[bytes, dict[str, Any]]:
        response, receipt = self.bytes(
            f"/repos/alice51849/{repo}/contents/{quote(path, safe='/')}",
            accept="application/vnd.github.raw+json",
        )
        if not receipt["ok"]:
            raise EvidenceError(f"GitHub file GET failed: {repo}/{path}")
        return response.body, receipt

    def file_json(self, repo: str, path: str) -> tuple[Any, dict[str, Any]]:
        body, receipt = self.file(repo, path)
        try:
            return json.loads(body), receipt
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EvidenceError(f"invalid {repo}/{path}: {error}") from error


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def _source(
    name: str,
    status: str,
    observed_at: str,
    payload: Any,
    *,
    run_id: int | str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    row = {
        "source": name,
        "status": status,
        "observed_at": observed_at,
        "run_id": run_id,
        "sha256": digest_value(payload),
    }
    if error:
        row["error"] = SECRET_RE.sub(r"\1\2[REDACTED]", error)[:500]
    return row


def cron_values(expression: str, minimum: int, maximum: int) -> set[int]:
    values: set[int] = set()
    for part in expression.split(","):
        part = part.strip()
        if not part:
            continue
        base, slash, raw_step = part.partition("/")
        step = int(raw_step) if slash else 1
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            start, end = map(int, base.split("-", 1))
        else:
            start = end = int(base)
        values.update(range(start, end + 1, step))
    return {item for item in values if minimum <= item <= maximum}


def cron_matches(expression: str, value: datetime) -> bool:
    fields = expression.split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    if value.minute not in cron_values(minute, 0, 59):
        return False
    if value.hour not in cron_values(hour, 0, 23):
        return False
    if value.month not in cron_values(month, 1, 12):
        return False
    dom_match = value.day in cron_values(dom, 1, 31)
    github_dow = (value.weekday() + 1) % 7
    dows = {0 if item == 7 else item for item in cron_values(dow, 0, 7)}
    dow_match = github_dow in dows
    if dom != "*" and dow != "*":
        return dom_match or dow_match
    return dom_match and dow_match


def expected_cron_count(
    expressions: list[str], start: datetime, end: datetime, created_at: datetime | None
) -> int:
    cursor = max(start, created_at or start).replace(second=0, microsecond=0)
    if cursor < max(start, created_at or start):
        cursor += timedelta(minutes=1)
    until = end.replace(second=0, microsecond=0)
    count = 0
    while cursor <= until:
        if any(cron_matches(expression, cursor) for expression in expressions):
            count += 1
        cursor += timedelta(minutes=1)
    return count


def schedule_crons(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.findall(
            r"^\s*-\s*cron:\s*[\"']?([^\"'\n#]+)",
            text,
            flags=re.MULTILINE,
        )
    ]


def classify(repo: str, name: str, path: str) -> str:
    if repo in MEASUREMENT_REPOS:
        return "measurement" if "app-report" in path else "excluded"
    if repo not in OUTREACH_REPOS:
        return "excluded"
    if repo == "open-reference-datasets":
        return "supporting_authority"
    if name == "Threads token maintenance":
        return "outreach_infrastructure"
    if repo == "geo-autopilot":
        return "legacy_outreach"
    return "outreach"


def aggregate_workflows(workflows: list[dict[str, Any]]) -> dict[str, Any]:
    conclusions: Counter[str] = Counter()
    expected = actual = dispatch = 0
    errors = []
    for row in workflows:
        expected += int(row.get("expected_schedule_count", 0))
        actual += int(row.get("actual_schedule_root_count", 0))
        conclusions.update(row.get("root_conclusions", {}))
        dispatch += int(row.get("event_counts", {}).get("workflow_dispatch", 0))
        if row.get("error"):
            errors.append(f"{row.get('repo')}:{row.get('path')}")
    return {
        "workflow_count": len(workflows),
        "nominal_cron_roots": expected,
        "actual_natural_schedule_roots": actual,
        "natural_root_conclusions": dict(conclusions),
        "workflow_dispatch_runs": dispatch,
        "collection_errors": errors,
    }


def _compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "run_attempt": run.get("run_attempt"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "head_sha": run.get("head_sha"),
        "html_url": run.get("html_url"),
    }


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.heading = ""
        self.heading_parts: list[str] | None = None
        self.tables: list[dict[str, Any]] = []
        self.table: dict[str, Any] | None = None
        self.row: list[dict[str, Any]] | None = None
        self.cell: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip += 1
        elif not self.skip and tag in {"h1", "h2"}:
            self.heading_parts = []
        elif not self.skip and tag == "table":
            self.table = {"heading": self.heading, "rows": []}
            self.tables.append(self.table)
        elif not self.skip and tag == "tr" and self.table is not None:
            self.row = []
        elif not self.skip and tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": "", "hrefs": []}
            self.row.append(self.cell)
        elif not self.skip and tag == "a" and self.cell is not None:
            self.cell["hrefs"].extend(
                value for key, value in attrs if key == "href" and value
            )

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in {"h1", "h2"} and self.heading_parts is not None:
            self.heading = re.sub(r"\s+", " ", " ".join(self.heading_parts)).strip()
            self.heading_parts = None
        elif not self.skip and tag in {"td", "th"}:
            self.cell = None
        elif not self.skip and tag == "tr" and self.table is not None and self.row:
            for cell in self.row:
                cell["text"] = re.sub(r"\s+", " ", cell["text"]).strip()
            self.table["rows"].append(self.row)
            self.row = None
        elif not self.skip and tag == "table":
            self.table = None

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.heading_parts is not None:
            self.heading_parts.append(data)
        if self.cell is not None:
            self.cell["text"] += data


def _app_id(cell: dict[str, Any]) -> str | None:
    for href in cell.get("hrefs", []):
        match = re.search(r"/id(\d+)", href)
        if match:
            return match.group(1)
    return None


def _integer(value: str) -> int | None:
    match = re.search(r"-?\d[\d,]*", value)
    return int(match.group(0).replace(",", "")) if match else None


def parse_asc_report(
    body: bytes, run_created_at: str, canonical_by_id: dict[str, str]
) -> dict[str, Any]:
    parser = ReportParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    tables = []
    for table in parser.tables:
        rows = table.get("rows", [])
        tables.append(
            {
                "heading": table.get("heading", ""),
                "rows": [
                    {"app_id": _app_id(row[0]), "cells": [cell["text"] for cell in row]}
                    for row in rows[1:]
                    if row
                ],
            }
        )
    daily = next((row for row in tables if row["heading"].startswith("📅")), None)
    month = next((row for row in tables if row["heading"].startswith("📈")), None)
    live = next((row for row in tables if row["heading"].startswith("✅")), None)
    if not daily or not month or not live:
        raise EvidenceError("ASC artifact lacks daily, MTD, or live-roster table")
    year = datetime.fromisoformat(run_created_at.replace("Z", "+00:00")).year
    match = re.search(r"（(\d{1,2})/(\d{1,2}) 當天）", daily["heading"])
    if not match:
        raise EvidenceError("ASC daily heading has no snapshot date")
    snapshot = date(year, int(match.group(1)), int(match.group(2)))

    def metrics(table: dict[str, Any], daily_mode: bool) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for row in table["rows"]:
            identity = row.get("app_id")
            cells = row.get("cells", [])
            if identity not in canonical_by_id or len(cells) < 5:
                continue
            result[canonical_by_id[identity]] = {
                "first_downloads": _integer(cells[1]) or 0,
                "iap_units": _integer(cells[2 if daily_mode else 3]) or 0,
            }
        return result

    return {
        "snapshot_date": snapshot.isoformat(),
        "daily_heading": daily["heading"],
        "daily": metrics(daily, True),
        "month_heading": month["heading"],
        "month": metrics(month, False),
        "live_keys": sorted(
            canonical_by_id[row["app_id"]]
            for row in live["rows"]
            if row.get("app_id") in canonical_by_id
        ),
        "report_sha256": hashlib.sha256(body).hexdigest(),
    }


class LiveCollector:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        client: GetClient | None = None,
        now: datetime | None = None,
    ) -> None:
        self.config = config
        self.client = client or GetClient()
        self.github = GitHub(self.client)
        self.now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(
            microsecond=0
        )
        self.since = self.now - timedelta(days=7)
        self.observed_at = iso_z(self.now)
        self.sources: list[dict[str, Any]] = []
        self._threads_apps: dict[str, Any] = {}
        self._guide_apps: list[dict[str, Any]] = []
        self._workflows: list[dict[str, Any]] = []

    def _record(
        self,
        name: str,
        status: str,
        payload: Any,
        *,
        run_id: int | str | None = None,
        error: str | None = None,
    ) -> None:
        self.sources.append(
            _source(
                name,
                status,
                self.observed_at,
                payload,
                run_id=run_id,
                error=error,
            )
        )

    def _blocked(self, name: str, error: Exception) -> None:
        self._record(name, BLOCKED, {"error": str(error)}, error=str(error))

    def collect_canonical(self) -> dict[str, Any]:
        expected_keys = sorted(self.config["live_dates"])
        result = {
            "keys": expected_keys,
            "threads_digest": None,
            "guide_digest": None,
            "public_digest": None,
            "asc_digest": None,
            "missing_live_apps": [],
            "unknown_live_apps": [],
        }
        try:
            threads, _ = self.github.file_json("threads-autopilot", "apps.json")
            guide, _ = self.github.file_json("ios-app-guide", "apps.json")
            public, _ = self.client.json(
                "https://alice51849.github.io/ios-app-guide/apps.json"
            )
            self._threads_apps = threads
            self._guide_apps = guide
            guide_keys = sorted(
                re.sub(r"\.html$", "", row["guideUrl"].rstrip("/").split("/")[-1])
                for row in guide
            )
            public_keys = sorted(
                re.sub(r"\.html$", "", row["guideUrl"].rstrip("/").split("/")[-1])
                for row in public
            )
            result.update(
                {
                    "keys": sorted(threads),
                    "threads_digest": digest_value(sorted(threads)),
                    "guide_digest": digest_value(guide_keys),
                    "public_digest": digest_value(public_keys),
                }
            )
            # v3 canonical digest used compact JSON without sort_keys on the object.
            for field, keys in [
                ("threads_digest", sorted(threads)),
                ("guide_digest", guide_keys),
                ("public_digest", public_keys),
            ]:
                result[field] = hashlib.sha256(
                    json.dumps(keys, separators=(",", ":")).encode()
                ).hexdigest()
            self._record("canonical", PASS, result)
        except Exception as error:
            self._blocked("canonical", error)
        return result

    def _attempt_one(self, repo: str, run: dict[str, Any]) -> dict[str, Any]:
        if int(run.get("run_attempt") or 1) <= 1:
            return {
                "attempt": 1,
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "updated_at": run.get("updated_at"),
            }
        payload, _ = self.github.json(
            f"/repos/alice51849/{repo}/actions/runs/{run['id']}/attempts/1"
        )
        return {
            "attempt": 1,
            "status": payload.get("status"),
            "conclusion": payload.get("conclusion"),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
        }

    def collect_schedule(self) -> dict[str, Any]:
        workflows: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        try:
            for repo in sorted(OUTREACH_REPOS | MEASUREMENT_REPOS):
                try:
                    listing, _ = self.github.json(
                        f"/repos/alice51849/{repo}/actions/workflows?per_page=100"
                    )
                    for item in listing.get("workflows", []):
                        path = item.get("path", "")
                        if not path.startswith(".github/workflows/"):
                            continue
                        body, _ = self.github.file(repo, path)
                        crons = schedule_crons(body.decode("utf-8", errors="replace"))
                        if not crons:
                            continue
                        scope = classify(repo, item.get("name") or "", path)
                        created = parse_time(item.get("created_at"))
                        expected = expected_cron_count(
                            crons, self.since, self.now, created
                        )
                        query = urlencode({"created": f">={iso_z(self.since)}"})
                        runs, _ = self.github.pages(
                            (
                                f"/repos/alice51849/{repo}/actions/workflows/"
                                f"{item['id']}/runs?{query}"
                            ),
                            "workflow_runs",
                        )
                        compact = [_compact_run(run) for run in runs]
                        natural = [run for run in compact if run.get("event") == "schedule"]
                        conclusions: Counter[str] = Counter()
                        for run in natural:
                            root = self._attempt_one(repo, run)
                            run["natural_root_attempt"] = root
                            conclusions[root.get("conclusion") or root.get("status") or "unknown"] += 1
                        events = Counter(run.get("event") or "unknown" for run in compact)
                        row = {
                            "repo": repo,
                            "name": item.get("name"),
                            "path": path,
                            "workflow_id": item.get("id"),
                            "scope": scope,
                            "state": item.get("state"),
                            "crons": crons,
                            "expected_schedule_count": expected,
                            "actual_schedule_root_count": len(natural),
                            "root_conclusions": dict(conclusions),
                            "event_counts": dict(events),
                            "runs": natural,
                        }
                        workflows.append(row)
                except Exception as error:
                    failures.append({"repo": repo, "error": str(error)[:300]})
            self._workflows = workflows
            scoped = [
                row
                for row in workflows
                if row["scope"]
                in {
                    "outreach",
                    "legacy_outreach",
                    "outreach_infrastructure",
                    "supporting_authority",
                }
            ]
            social = [row for row in scoped if row["repo"] == "threads-autopilot"]
            high = [row for row in social if row["name"] in HIGH_FREQUENCY]
            result = {
                "all_outreach": aggregate_workflows(scoped)
                | {"collection_errors": failures},
                "social": aggregate_workflows(social),
                "high_frequency_social": aggregate_workflows(high),
                "workflows": workflows,
            }
            self._record(
                "github_actions",
                PASS if not failures else BLOCKED,
                result,
                run_id=max(
                    (
                        run["id"]
                        for row in scoped
                        for run in row.get("runs", [])
                        if run.get("id")
                    ),
                    default=None,
                ),
                error=json.dumps(failures) if failures else None,
            )
            return result
        except Exception as error:
            self._blocked("github_actions", error)
            return {
                "all_outreach": {"collection_errors": [str(error)]},
                "social": {},
                "high_frequency_social": {},
                "workflows": workflows,
            }

    def collect_digest_gate(self) -> dict[str, Any]:
        failures: list[dict[str, Any]] = []
        unread: list[int] = []
        try:
            high_workflows = [
                row
                for row in self._workflows
                if row["repo"] == "threads-autopilot"
                and row["name"] in HIGH_FREQUENCY
            ]
            if not high_workflows or not any(
                row.get("runs") for row in high_workflows
            ):
                raise EvidenceError("no fresh high-frequency natural roots")
            candidates = [
                (row, run)
                for row in high_workflows
                for run in row.get("runs", [])
                if run.get("natural_root_attempt", {}).get("conclusion") != "success"
            ]
            for workflow, run in sorted(
                candidates, key=lambda pair: pair[1].get("created_at") or "", reverse=True
            )[:12]:
                response, receipt = self.github.bytes(
                    f"/repos/alice51849/threads-autopilot/actions/runs/{run['id']}/logs"
                )
                if not receipt["ok"]:
                    unread.append(int(run["id"]))
                    continue
                texts = []
                try:
                    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
                        texts = [
                            archive.read(name).decode("utf-8", errors="replace")
                            for name in archive.namelist()
                        ]
                except zipfile.BadZipFile:
                    texts = [response.body.decode("utf-8", errors="replace")]
                matches = sorted(
                    {
                        line.strip()[-500:]
                        for text in texts
                        for line in text.splitlines()
                        if "Publisher-reviewed source digest mismatch" in line
                    }
                )
                if matches:
                    failures.append(
                        {
                            "repo": workflow["repo"],
                            "workflow": workflow["name"],
                            "run_id": run["id"],
                            "created_at": run.get("created_at"),
                            "matching_lines": matches,
                            "log_sha256": receipt["sha256"],
                        }
                    )
            result = {"fresh": not unread, "failures": failures, "unread_logs": unread}
            self._record(
                "digest_gate",
                PASS if not unread else BLOCKED,
                result,
                run_id=failures[0]["run_id"] if failures else None,
                error=f"unread run logs: {unread}" if unread else None,
            )
            return result
        except Exception as error:
            self._blocked("digest_gate", error)
            return {"fresh": False, "failures": [{"error": str(error)[:300]}]}

    def _parallel_get(
        self, targets: list[tuple[str, str]], *, maximum_workers: int = 8
    ) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=maximum_workers) as executor:
            futures = {
                executor.submit(self.client.get, url, accept="*/*"): key
                for key, url in targets
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    _, receipt = future.result()
                    receipts.append({"key": key, **receipt})
                except Exception as error:
                    receipts.append(
                        {
                            "key": key,
                            "url": dict(targets)[key],
                            "ok": False,
                            "status": None,
                            "error": str(error)[:300],
                            "method": "GET",
                            "fetched_at": self.observed_at,
                            "sha256": digest_value({"key": key, "error": str(error)}),
                        }
                    )
        return sorted(receipts, key=lambda row: row["key"])

    def collect_pages(self) -> dict[str, Any]:
        result = {
            "pages_get_total": 0,
            "pages_get_ok": 0,
            "guide_get_total": EXPECTED_COUNT,
            "guide_get_ok": 0,
            "app_store_get_total": EXPECTED_COUNT,
            "app_store_get_ok": 0,
            "recent_deployments": 0,
            "recent_deployment_successes": 0,
            "receipts": [],
        }
        try:
            repos, _ = self.github.pages(
                "/users/alice51849/repos?type=owner&sort=full_name", ""
            )
            page_repos = [
                row for row in repos if row.get("has_pages") and not row.get("archived")
            ]
            page_targets = []
            for repo in page_repos:
                name = repo["name"]
                try:
                    page, _ = self.github.json(f"/repos/alice51849/{name}/pages")
                    url = page.get("html_url") or repo.get("homepage")
                    if url:
                        page_targets.append((name, url))
                    deployments, _ = self.github.pages(
                        (
                            f"/repos/alice51849/{name}/deployments?"
                            + urlencode(
                                {
                                    "environment": "github-pages",
                                    "created": f">={iso_z(self.since)}",
                                }
                            )
                        ),
                        "",
                    )
                    if deployments:
                        result["recent_deployments"] += 1
                        statuses, _ = self.github.pages(
                            f"/repos/alice51849/{name}/deployments/{deployments[0]['id']}/statuses",
                            "",
                        )
                        if statuses and statuses[0].get("state") == "success":
                            result["recent_deployment_successes"] += 1
                except Exception:
                    page_targets.append((name, repo.get("homepage") or ""))
            page_targets = [(key, url) for key, url in page_targets if url.startswith("https://")]
            page_receipts = self._parallel_get(page_targets)
            guide_targets = []
            store_targets = []
            for row in self._guide_apps:
                slug = re.sub(r"\.html$", "", row["guideUrl"].rstrip("/").split("/")[-1])
                guide_targets.append((slug, row["guideUrl"]))
                store_targets.append((slug, row["appStoreUrl"]))
            guide_receipts = self._parallel_get(guide_targets)
            store_receipts = self._parallel_get(store_targets)
            result.update(
                {
                    "pages_get_total": len(page_receipts),
                    "pages_get_ok": sum(bool(row.get("ok")) for row in page_receipts),
                    "guide_get_total": len(guide_receipts),
                    "guide_get_ok": sum(bool(row.get("ok")) for row in guide_receipts),
                    "app_store_get_total": len(store_receipts),
                    "app_store_get_ok": sum(
                        bool(row.get("ok")) for row in store_receipts
                    ),
                    "receipts": page_receipts + guide_receipts + store_receipts,
                }
            )
            ok = all(
                row.get("ok")
                for row in result["receipts"]
            )
            self._record("pages_deployments", PASS, result)
            self._record("public_get", PASS if ok else BLOCKED, result)
        except Exception as error:
            self._blocked("pages_deployments", error)
            self._blocked("public_get", error)
        return result

    @staticmethod
    def _ledger(
        state: dict[str, Any],
        ledger_key: str,
        identities: tuple[str, ...],
        since: datetime,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        ledger = state.get(ledger_key, {})
        entries = list(ledger.items()) if isinstance(ledger, dict) else list(enumerate(ledger))
        unique: dict[str, dict[str, Any]] = {}
        for raw_key, entry in entries:
            if not isinstance(entry, dict):
                continue
            identity = next(
                (str(entry[key]) for key in identities if entry.get(key)),
                str(raw_key),
            )
            timestamp = next(
                (
                    parse_time(entry[key])
                    for key in ("published_at", "posted_at", "created_at", "date")
                    if entry.get(key)
                ),
                None,
            )
            app = entry.get("app") or entry.get("app_key")
            if not app and ":" in str(raw_key):
                app = str(raw_key).split(":", 1)[1]
            receipt = {
                **entry,
                "identity": identity,
                "app": app,
                "timestamp": iso_z(timestamp) if timestamp else None,
                "timestamp_epoch": timestamp.timestamp() if timestamp else None,
            }
            previous = unique.get(identity)
            if previous is None or (receipt["timestamp_epoch"] or 0) > (
                previous["timestamp_epoch"] or 0
            ):
                unique[identity] = receipt
        ordered = sorted(
            unique.values(), key=lambda row: row.get("timestamp_epoch") or 0, reverse=True
        )
        recent = [
            row
            for row in ordered
            if row.get("timestamp_epoch")
            and datetime.fromtimestamp(row["timestamp_epoch"], timezone.utc) >= since
        ]
        apps = sorted({row["app"] for row in recent if row.get("app")})
        return (
            {
                "raw_entry_count": len(entries),
                "unique_receipt_count": len(ordered),
                "last_7d_unique_receipts": len(recent),
                "last_7d_apps": apps,
                "latest_receipt_at": ordered[0]["timestamp"] if ordered else None,
            },
            ordered,
        )

    def _public_sample(self, channel: str, receipts: list[dict[str, Any]]) -> dict[str, Any]:
        targets = []
        for index, row in enumerate(receipts[:5]):
            identity = row.get("identity", "")
            if channel == "Nostr" and identity:
                url = f"https://njump.me/{identity}"
            elif channel == "Bluesky" and "/app.bsky.feed.post/" in identity:
                did, rkey = identity.split("/app.bsky.feed.post/", 1)
                url = f"https://bsky.app/profile/{did.removeprefix('at://')}/post/{rkey}"
            else:
                url = identity
            if isinstance(url, str) and url.startswith("https://"):
                targets.append((f"{channel}-{index}", url))
        rows = self._parallel_get(targets, maximum_workers=5) if targets else []
        return {
            "count": len(rows),
            "ok_count": sum(bool(row.get("ok")) for row in rows),
            "statuses": sorted(Counter(str(row.get("status")) for row in rows).items()),
            "receipts": rows,
        }

    def collect_social_and_owned(self) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
        channels: list[dict[str, Any]] = []
        owned = {
            "guide_count": len(self._guide_apps),
            "publisher_count": 0,
            "profile_count": 0,
            "publisher_missing": sorted(self.config["live_dates"]),
            "profile_missing": sorted(self.config["live_dates"]),
        }
        click: dict[str, Any] = {"known": False, "apps_with_click": []}
        try:
            states: dict[str, dict[str, Any]] = {}
            receipts_by_channel: dict[str, list[dict[str, Any]]] = {}
            for channel, (filename, ledger_key, identities) in SOCIAL_STATES.items():
                state, _ = self.github.file_json("threads-autopilot", filename)
                states[channel] = state
                summary, receipts = self._ledger(
                    state, ledger_key, identities, self.since
                )
                receipts_by_channel[channel] = receipts
                sample = self._public_sample(channel, receipts)
                row = {
                    "channel": channel,
                    "status": BLOCKED,
                    "deduplicated_public_receipts_7d": summary[
                        "last_7d_unique_receipts"
                    ],
                    "apps_with_receipt_7d": len(summary["last_7d_apps"]),
                    "missing_apps_7d": sorted(
                        set(self.config["live_dates"]) - set(summary["last_7d_apps"])
                    ),
                    "latest_receipt_at": summary["latest_receipt_at"],
                    "public_get_sample": sample,
                }
                if channel == "Nostr":
                    recent_ids = {
                        receipt["identity"]
                        for receipt in receipts
                        if receipt.get("timestamp_epoch")
                        and datetime.fromtimestamp(
                            receipt["timestamp_epoch"], timezone.utc
                        )
                        >= self.since
                    }
                    attempts = [
                        value
                        for value in state.get("relay_attempts", {}).values()
                        if isinstance(value, dict) and value.get("event_id") in recent_ids
                    ]
                    row.update(
                        {
                            "relay_attempts_7d": len(attempts),
                            "relay_acknowledged_7d": sum(
                                value.get("status") == "acknowledged"
                                for value in attempts
                            ),
                            "counts_as_public_exposure": False,
                            "public_get_verified_sample_count": sample["ok_count"],
                        }
                    )
                row["status"] = (
                    PASS
                    if row["apps_with_receipt_7d"] == EXPECTED_COUNT
                    and sample["count"] > 0
                    and sample["ok_count"] == sample["count"]
                    else BLOCKED
                )
                channels.append(row)

            threads_state = states["Threads"]
            insights = threads_state.get("click_insights")
            if isinstance(insights, dict) and isinstance(insights.get("apps"), dict):
                apps = insights["apps"]
                click = {
                    "known": True,
                    "window_days": insights.get("window_days"),
                    "date": insights.get("date"),
                    "total_clicks": sum(
                        int(value.get("clicks", 0)) if isinstance(value, dict) else int(value)
                        for value in apps.values()
                    ),
                    "apps_with_click": sorted(
                        key
                        for key, value in apps.items()
                        if (
                            int(value.get("clicks", 0))
                            if isinstance(value, dict)
                            else int(value)
                        )
                        > 0
                    ),
                    "zero_click_apps": sorted(
                        set(self.config["live_dates"])
                        - {
                            key
                            for key, value in apps.items()
                            if (
                                int(value.get("clicks", 0))
                                if isinstance(value, dict)
                                else int(value)
                            )
                            > 0
                        }
                    ),
                    "non_threads_clicks": "UNKNOWN",
                }

            canonical_by_id = {}
            for key, row in self._threads_apps.items():
                match = re.search(r"/id(\d+)", row.get("url", ""))
                if match:
                    canonical_by_id[match.group(1)] = key
            tree, _ = self.github.json(
                "/repos/alice51849/alice51849.github.io/git/trees/main?recursive=1"
            )
            slugs = sorted(
                {
                    parts[1]
                    for entry in tree.get("tree", [])
                    if len(parts := entry.get("path", "").split("/")) == 3
                    and parts[0] == "app"
                    and parts[2] == "index.html"
                }
            )
            publisher_receipts = self._parallel_get(
                [
                    (slug, f"https://alice51849.github.io/app/{slug}/")
                    for slug in slugs
                ]
            )
            found: set[str] = set()
            for row in publisher_receipts:
                if not row.get("ok"):
                    continue
                response, _ = self.client.get(row["url"], accept="text/html")
                for identity in re.findall(rb"apps\.apple\.com/[^\"'<>\s]*?id(\d+)", response.body):
                    key = canonical_by_id.get(identity.decode())
                    if key:
                        found.add(key)
            profile_body, _ = self.github.file("alice51849", "README.md")
            profile_ids = {
                identity.decode()
                for identity in re.findall(
                    rb"apps\.apple\.com/[^\"'<>\s]*?id(\d+)", profile_body
                )
            }
            profile_apps = {
                canonical_by_id[identity]
                for identity in profile_ids
                if identity in canonical_by_id
            }
            expected = set(self.config["live_dates"])
            owned.update(
                {
                    "publisher_count": len(found),
                    "profile_count": len(profile_apps),
                    "publisher_missing": sorted(expected - found),
                    "profile_missing": sorted(expected - profile_apps),
                    "publisher_public_get": {
                        "count": len(publisher_receipts),
                        "ok_count": sum(
                            bool(row.get("ok")) for row in publisher_receipts
                        ),
                    },
                }
            )
            self._record("publisher", PASS, owned)
            self._record("social_receipts", PASS, channels)
            self._record(
                "standard",
                PASS,
                next(
                    (row for row in channels if row["channel"] == "Standard.site"),
                    {},
                ),
            )
            self._record("click", PASS, click)
        except Exception as error:
            self._blocked("publisher", error)
            self._blocked("social_receipts", error)
            self._blocked("standard", error)
            self._blocked("click", error)
        return channels, owned, click

    def collect_crawler(self, channels: list[dict[str, Any]]) -> dict[str, Any]:
        result = {
            "sitemap_get_ok": False,
            "robots_get_ok": False,
            "guide_apps_in_sitemap": 0,
            "standard_reader_verified": False,
            "search_index_presence": False,
            "indexnow_acceptance_is_index_presence": False,
        }
        try:
            sitemap_response, sitemap_receipt = self.client.get(
                "https://alice51849.github.io/ios-app-guide/sitemap.xml",
                accept="application/xml",
            )
            _, robots_receipt = self.client.get(
                "https://alice51849.github.io/ios-app-guide/robots.txt",
                accept="text/plain",
            )
            sitemap = sitemap_response.body.decode("utf-8", errors="replace")
            guide_urls = {
                row["guideUrl"].rstrip("/") for row in self._guide_apps
            }
            sitemap_urls = {
                value.rstrip("/")
                for value in re.findall(r"<loc>([^<]+)</loc>", sitemap)
            }
            result.update(
                {
                    "sitemap_get_ok": sitemap_receipt["ok"],
                    "robots_get_ok": robots_receipt["ok"],
                    "guide_apps_in_sitemap": len(guide_urls & sitemap_urls),
                    "missing_guide_apps": sorted(guide_urls - sitemap_urls),
                    "sitemap_receipt": sitemap_receipt,
                    "robots_receipt": robots_receipt,
                }
            )
            standard_state, _ = self.github.file_json(
                "threads-autopilot", "standard_site_state.json"
            )
            publication = standard_state.get("publication", {})
            at_uri = publication.get("at_uri")
            did = publication.get("did")
            published = {
                entry.get("at_uri")
                for entry in standard_state.get("documents", {}).values()
                if isinstance(entry, dict)
                and entry.get("published") is True
                and entry.get("at_uri")
            }
            public_uris: set[str] = set()
            public_counts: dict[str, int | None] = {
                "reader": None,
                "pub_search": None,
                "heron": None,
            }
            if at_uri:
                url = (
                    "https://standard-reader.app/xrpc/"
                    "app.standard-reader.getPublication?"
                    + urlencode({"publication": at_uri})
                )
                payload, receipt = self.client.json(url)
                result["standard_reader_receipt"] = receipt
                publication_payload = payload.get("publication") or {}
                result["standard_reader_verified"] = (
                    publication_payload.get("verified") is True
                )
                public_counts["reader"] = (
                    payload.get("documentCount")
                    or publication_payload.get("documentCount")
                )
            if did:
                search_url = (
                    "https://leaflet-search-backend.fly.dev/search?"
                    + urlencode(
                        {"author": did, "format": "v2", "limit": 100, "offset": 0}
                    )
                )
                search_payload, search_receipt = self.client.json(search_url)
                search_rows = search_payload.get("results", [])
                result["standard_search_receipt"] = search_receipt
                public_counts["pub_search"] = len(search_rows)
                public_uris.update(
                    row.get("uri")
                    for row in search_rows
                    if isinstance(row, dict) and row.get("uri")
                )
                heron_url = (
                    "https://heron.tunji.dev/xrpc/site.standard.heron.getDocuments?"
                    + urlencode(
                        {"publication": at_uri, "author": did, "limit": 100}
                    )
                )
                heron_payload, heron_receipt = self.client.json(heron_url)
                heron_rows = heron_payload.get("documents", [])
                result["standard_heron_receipt"] = heron_receipt
                public_counts["heron"] = len(heron_rows)
                public_uris.update(
                    row.get("uri")
                    for row in heron_rows
                    if isinstance(row, dict) and row.get("uri")
                )
            standard_channel = next(
                (row for row in channels if row["channel"] == "Standard.site"), {}
            )
            result["standard_site"] = {
                "state_derived_published_app_count": standard_channel.get(
                    "apps_with_receipt_7d", 0
                ),
                "state_derived_published_document_count": len(published),
                "public_index_document_count": max(
                    (value for value in public_counts.values() if isinstance(value, int)),
                    default=None,
                ),
                "public_index_counts_by_service": public_counts,
                "public_index_missing_state_uris": sorted(published - public_uris),
                "public_index_unknown_uris": sorted(public_uris - published),
                "app_count_and_document_count_are_same_unit": False,
                "counts_as_public_exposure": False,
            }
            result["search_index_presence"] = (
                result["standard_reader_verified"]
                and bool(public_uris)
                and not (published - public_uris)
            )
            self._record("crawler", PASS, result)
        except Exception as error:
            self._blocked("crawler", error)
        return result

    def collect_asc(self, canonical: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "fresh": False,
            "aggregate_semantics": "exact",
            "analytics_privacy_suppression_applied": False,
            "live_roster_count": 0,
            "windows_complete": False,
            "window_counts": {},
            "eligible_days": {},
            "unknown_no_row": [],
            "all_zero_rows": [],
            "excluded_population_reports": [],
            "raw_reconstruction_counts_are_floor_truth": False,
        }
        try:
            canonical_by_id = {}
            for key, row in self._threads_apps.items():
                match = re.search(r"/id(\d+)", row.get("url", ""))
                if match:
                    canonical_by_id[match.group(1)] = key
            artifact_by_id: dict[int, dict[str, Any]] = {}
            for artifact_name in ("app-report-html", "app-report-watchdog-html"):
                payload, _ = self.github.json(
                    "/repos/alice51849/apple-ads-autopilot/actions/artifacts?"
                    + urlencode({"name": artifact_name, "per_page": 100})
                )
                for artifact in payload.get("artifacts", []):
                    if not artifact.get("expired") and artifact.get("id"):
                        artifact_by_id[int(artifact["id"])] = artifact
            observations = []
            for artifact in sorted(
                artifact_by_id.values(),
                key=lambda row: row.get("created_at") or "",
                reverse=True,
            )[:30]:
                run_id = (artifact.get("workflow_run") or {}).get("id")
                if not run_id:
                    continue
                run, _ = self.github.json(
                    f"/repos/alice51849/apple-ads-autopilot/actions/runs/{run_id}"
                )
                if run.get("conclusion") != "success":
                    continue
                response, receipt = self.github.bytes(
                    f"/repos/alice51849/apple-ads-autopilot/actions/artifacts/{artifact['id']}/zip"
                )
                if not receipt["ok"]:
                    continue
                try:
                    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
                        name = next(
                            item
                            for item in archive.namelist()
                            if item.rsplit("/", 1)[-1] == "report.html"
                        )
                        parsed = parse_asc_report(
                            archive.read(name), run["created_at"], canonical_by_id
                        )
                except (zipfile.BadZipFile, StopIteration) as error:
                    raise EvidenceError(f"invalid ASC report artifact: {error}") from error
                observations.append(
                    {
                        **parsed,
                        "run_id": run_id,
                        "run_created_at": run["created_at"],
                        "run_event": run.get("event"),
                        "run_attempt": run.get("run_attempt"),
                        "artifact_name": artifact.get("name"),
                        "artifact_id": artifact["id"],
                        "artifact_sha256": receipt["sha256"],
                        "expected_live_keys": sorted(
                            key
                            for key, live_date in self.config["live_dates"].items()
                            if date.fromisoformat(live_date)
                            <= date.fromisoformat(parsed["snapshot_date"])
                        ),
                    }
                )
                observations[-1]["population_authority"] = (
                    observations[-1]["live_keys"]
                    == observations[-1]["expected_live_keys"]
                )
            authoritative = [
                row for row in observations if row["population_authority"] is True
            ]
            if not authoritative:
                raise EvidenceError("no exact46 ASC population report in current window")
            latest = max(authoritative, key=lambda row: row["snapshot_date"])
            as_of = date.fromisoformat(latest["snapshot_date"])
            selected_by_date = {
                row["snapshot_date"]: row
                for row in sorted(authoritative, key=lambda row: row["run_created_at"])
            }
            selected_dates = [
                (as_of - timedelta(days=offset)).isoformat()
                for offset in range(6, -1, -1)
            ]
            selected = [selected_by_date.get(day) for day in selected_dates]
            windows_complete = all(selected)
            keys = sorted(self.config["live_dates"])

            def count_latest(metric: str) -> int:
                return sum(
                    latest["daily"].get(key, {}).get(metric, 0) >= 1 for key in keys
                )

            def count_rolling(metric: str) -> int:
                if not windows_complete:
                    return 0
                return sum(
                    sum(
                        row["daily"].get(key, {}).get(metric, 0)
                        for row in selected
                        if row is not None
                        and date.fromisoformat(row["snapshot_date"])
                        >= date.fromisoformat(self.config["live_dates"][key])
                    )
                    >= 1
                    for key in keys
                )

            month_unknown = sorted(set(keys) - set(latest["month"]))
            mtd_known = sorted(set(keys) & set(latest["month"]))
            mtd_downloads = sum(
                latest["month"][key]["first_downloads"] >= 1 for key in mtd_known
            )
            mtd_iap = sum(latest["month"][key]["iap_units"] >= 1 for key in mtd_known)
            all_zero = []
            for key in keys:
                if key in month_unknown:
                    continue
                eligible = [
                    row
                    for row in selected
                    if row is not None
                    and date.fromisoformat(row["snapshot_date"])
                    >= date.fromisoformat(self.config["live_dates"][key])
                ]
                if (
                    latest["month"][key]["first_downloads"] == 0
                    and latest["month"][key]["iap_units"] == 0
                    and all(
                        row["daily"].get(key, {}).get("first_downloads", 0) == 0
                        and row["daily"].get(key, {}).get("iap_units", 0) == 0
                        for row in eligible
                    )
                ):
                    all_zero.append(key)
            eligible_days = {}
            for key in keys:
                live = date.fromisoformat(self.config["live_dates"][key])
                dates = [
                    day for day in selected_dates if date.fromisoformat(day) >= live
                ]
                eligible_days[key] = {
                    "live_date": live.isoformat(),
                    "live_date_source": "approved v3 exact46 contract",
                    "eligible_dates": dates,
                    "eligible_days": len(dates),
                }
            result.update(
                {
                    "as_of": as_of.isoformat(),
                    "fresh": (self.now.date() - as_of).days <= 2,
                    "live_roster_count": len(latest["live_keys"]),
                    "windows_complete": windows_complete,
                    "source_run_id": latest["run_id"],
                    "snapshot": latest["daily_heading"],
                    "daily_first_downloads": sum(
                        row["first_downloads"] for row in latest["daily"].values()
                    ),
                    "month_to_date_first_downloads": sum(
                        row["first_downloads"] for row in latest["month"].values()
                    ),
                    "window_counts": {
                        "latest_daily_downloads": {
                            "apps_ge_1": count_latest("first_downloads"),
                            "known": EXPECTED_COUNT,
                            "unknown": 0,
                            "unknown_no_row": [],
                        },
                        "latest_daily_iap": {
                            "apps_ge_1": count_latest("iap_units"),
                            "known": EXPECTED_COUNT,
                            "unknown": 0,
                            "unknown_no_row": [],
                        },
                        "rolling_7d_downloads": {
                            "apps_ge_1": count_rolling("first_downloads"),
                            "known": EXPECTED_COUNT if windows_complete else 0,
                            "unknown": 0 if windows_complete else EXPECTED_COUNT,
                            "unknown_no_row": [] if windows_complete else keys,
                        },
                        "rolling_7d_iap": {
                            "apps_ge_1": count_rolling("iap_units"),
                            "known": EXPECTED_COUNT if windows_complete else 0,
                            "unknown": 0 if windows_complete else EXPECTED_COUNT,
                            "unknown_no_row": [] if windows_complete else keys,
                        },
                        "month_to_date_downloads": {
                            "apps_ge_1": mtd_downloads,
                            "known": len(mtd_known),
                            "unknown": len(month_unknown),
                            "unknown_no_row": month_unknown,
                        },
                        "month_to_date_iap": {
                            "apps_ge_1": mtd_iap,
                            "known": len(mtd_known),
                            "unknown": len(month_unknown),
                            "unknown_no_row": month_unknown,
                        },
                    },
                    "eligible_days": eligible_days,
                    "unknown_no_row": month_unknown,
                    "all_zero_rows": all_zero,
                    "excluded_population_reports": [
                        {
                            "run_id": row["run_id"],
                            "snapshot_date": row["snapshot_date"],
                            "report_sha256": row["report_sha256"],
                            "population_authority": False,
                            "reason": (
                                f"live roster {len(row['live_keys'])}/"
                                f"{len(row['expected_live_keys'])} is degraded"
                            ),
                        }
                        for row in observations
                        if row["population_authority"] is False
                        and date.fromisoformat(row["snapshot_date"])
                        >= as_of - timedelta(days=6)
                    ],
                    "raw_reconstruction_counts_are_floor_truth": True,
                }
            )
            asc_keys = sorted(latest["live_keys"])
            canonical["asc_digest"] = hashlib.sha256(
                json.dumps(asc_keys, separators=(",", ":")).encode()
            ).hexdigest()
            self._record(
                "asc",
                PASS if result["fresh"] and windows_complete else BLOCKED,
                {
                    "result": result,
                    "selected_sources": [
                        {
                            "run_id": row["run_id"],
                            "snapshot_date": row["snapshot_date"],
                            "report_sha256": row["report_sha256"],
                        }
                        for row in selected
                        if row
                    ],
                },
                run_id=latest["run_id"],
            )
        except Exception as error:
            self._blocked("asc", error)
        return result

    def collect(self) -> dict[str, Any]:
        canonical = self.collect_canonical()
        schedule = self.collect_schedule()
        digest_gate = self.collect_digest_gate()
        pages = self.collect_pages()
        channels, owned, click = self.collect_social_and_owned()
        crawler = self.collect_crawler(channels)
        asc = self.collect_asc(canonical)
        required = {
            "canonical",
            "github_actions",
            "digest_gate",
            "pages_deployments",
            "public_get",
            "publisher",
            "social_receipts",
            "standard",
            "crawler",
            "click",
            "asc",
        }
        present = {row["source"] for row in self.sources}
        for name in sorted(required - present):
            self._record(
                name,
                BLOCKED,
                {"error": "collector did not produce current evidence"},
                error="collector did not produce current evidence",
            )
        return {
            "observed_at": self.observed_at,
            "source_evidence": self.sources,
            "canonical": canonical,
            "schedule": schedule,
            "digest_gate": digest_gate,
            "pages": pages,
            "owned_surfaces": owned,
            "social_channels": channels,
            "crawler": crawler,
            "click": click,
            "asc": asc,
        }


def load_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    keys = sorted(value.get("live_dates", {}))
    digest = hashlib.sha256(
        json.dumps(keys, separators=(",", ":")).encode()
    ).hexdigest()
    if len(keys) != EXPECTED_COUNT or digest != EXPECTED_DIGEST:
        raise EvidenceError("config live_dates does not match approved exact46 digest")
    return value
