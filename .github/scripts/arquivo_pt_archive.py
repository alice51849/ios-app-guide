#!/usr/bin/env python3
"""Archive one live app guide with Arquivo.pt each day."""

from __future__ import annotations

import datetime as dt
import http.client
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from social_post_common import (
    HTTPStatusError,
    RequestError,
    is_transient_status,
    validate_url,
)


BASE_DATE = dt.date(2026, 7, 12)
COOLDOWN_DAYS = 21
SITE = "https://alice51849.github.io/ios-app-guide"
CAPTURE_API = "https://arquivo.pt/save/now/record/"
CDX_API = "https://arquivo.pt/wayback/cdx"
USER_AGENT = (
    "CaitlynPublicPageArchiver/1.0 "
    "(+https://github.com/alice51849/ios-app-guide)"
)
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LINKSET_PATH = ROOT / "linkset.json"
SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def _error_body(error: urllib.error.HTTPError) -> str:
    try:
        raw = error.read(2048)
    except Exception:
        return ""
    finally:
        error.close()
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace").strip()
    return str(raw).strip()


def _request_text(
    request: urllib.request.Request,
    *,
    label: str,
    timeout: int = 90,
    attempts: int = 3,
    opener=None,
    sleeper=None,
    retry_delays: tuple[int, ...] = (20, 60),
    limit: int = 512 * 1024,
) -> tuple[str, str]:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    opener = urllib.request.urlopen if opener is None else opener
    sleeper = time.sleep if sleeper is None else sleeper

    for attempt in range(attempts):
        try:
            with opener(request, timeout=timeout) as response:
                raw = response.read(limit)
                final_url = response.geturl()
            return raw.decode("utf-8", errors="replace"), final_url
        except urllib.error.HTTPError as error:
            body = _error_body(error)
            if not is_transient_status(error.code):
                raise HTTPStatusError(label, error.code, body) from error
            if attempt == attempts - 1:
                raise HTTPStatusError(label, error.code, body, attempts) from error
            delay = retry_delays[min(attempt, len(retry_delays) - 1)]
            print(
                f"{label}: transient HTTP {error.code}; retrying in {delay}s",
                file=sys.stderr,
            )
            sleeper(delay)
        except (
            urllib.error.URLError,
            OSError,
            http.client.HTTPException,
        ) as error:
            if attempt == attempts - 1:
                raise RequestError(
                    f"{label} failed after {attempts} attempts: {error}"
                ) from error
            delay = retry_delays[min(attempt, len(retry_delays) - 1)]
            print(
                f"{label}: transient {type(error).__name__}; retrying in {delay}s",
                file=sys.stderr,
            )
            sleeper(delay)
    raise RequestError(f"{label} failed unexpectedly")


def _guide_entry(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict) or not isinstance(payload.get("linkset"), list):
        raise ValueError("linkset.json has an invalid top-level structure")
    anchors = {f"{SITE}/", f"{SITE}/index.html"}
    entries = [
        entry
        for entry in payload["linkset"]
        if isinstance(entry, dict)
        and entry.get("anchor") in anchors
        and isinstance(entry.get("item"), list)
    ]
    if len(entries) != 1:
        raise ValueError("linkset.json must contain one portfolio guide entry")
    return entries[0]


def _title(item: dict[str, object]) -> str:
    titles = item.get("title*")
    if not isinstance(titles, list):
        raise ValueError("live guide is missing title metadata")
    for title in titles:
        if isinstance(title, dict) and isinstance(title.get("value"), str):
            value = title["value"].strip()
            if value:
                return value
    raise ValueError("live guide has an empty title")


def load_candidates(
    *,
    linkset_path: pathlib.Path = LINKSET_PATH,
    root: pathlib.Path = ROOT,
) -> list[dict[str, str]]:
    try:
        with linkset_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read live app linkset: {error}") from error

    entry = _guide_entry(payload)
    site = urllib.parse.urlsplit(SITE)
    guide_prefix = f"{site.path.rstrip('/')}/guides/"
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in entry["item"]:
        if not isinstance(item, dict) or not isinstance(item.get("href"), str):
            raise ValueError("live guide entry contains an invalid item")
        href = item["href"]
        parsed = urllib.parse.urlsplit(href)
        if (
            parsed.scheme != "https"
            or parsed.netloc != site.netloc
            or not parsed.path.startswith(guide_prefix)
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"live guide URL is outside the public guide: {href}")
        relative = parsed.path[len(guide_prefix) :]
        if "/" in relative or not relative.endswith(".html"):
            raise ValueError(f"live guide URL has an invalid path: {href}")
        slug = relative[:-5]
        if not SLUG_RE.fullmatch(slug):
            raise ValueError(f"live guide has an invalid slug: {slug}")
        if slug in seen:
            raise ValueError(f"live guide is duplicated: {slug}")
        if not (root / "guides" / relative).is_file():
            raise ValueError(f"live guide file is missing: guides/{relative}")

        localized_file = root / "pt-BR" / "guides" / relative
        archive_url = (
            f"{SITE}/pt-BR/guides/{relative}" if localized_file.is_file() else href
        )
        candidates.append(
            {
                "slug": slug,
                "name": _title(item),
                "canonical_url": href,
                "archive_url": archive_url,
            }
        )
        seen.add(slug)
    if not candidates:
        raise ValueError("live app linkset contains no guides")
    return candidates


def select_candidate(
    candidates: list[dict[str, str]],
    *,
    today: dt.date | None = None,
    override: str = "",
) -> dict[str, str]:
    if not candidates:
        raise ValueError("live app guide pool is empty")
    by_slug = {candidate["slug"]: candidate for candidate in candidates}
    if override:
        if override not in by_slug:
            raise ValueError(f"app is not in the live guide pool: {override}")
        return by_slug[override]
    today = dt.datetime.now(dt.timezone.utc).date() if today is None else today
    offset = (today - BASE_DATE).days
    if offset < 0:
        raise ValueError(f"archive schedule predates {BASE_DATE.isoformat()}")
    return candidates[offset % len(candidates)]


def _parse_cdx(text: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise RequestError(
                f"Arquivo.pt CDX returned invalid NDJSON on line {line_number}"
            ) from error
        if not isinstance(item, dict):
            raise RequestError(
                f"Arquivo.pt CDX returned a non-object on line {line_number}"
            )
        records.append(item)
    return records


def recent_capture(
    target_url: str,
    *,
    today: dt.date,
    cooldown_days: int = COOLDOWN_DAYS,
    opener=None,
    sleeper=None,
) -> dt.datetime | None:
    if cooldown_days < 0:
        raise ValueError("cooldown_days cannot be negative")
    cutoff = today - dt.timedelta(days=cooldown_days)
    query = urllib.parse.urlencode(
        {
            "url": target_url,
            "output": "json",
            "from": cutoff.strftime("%Y%m%d"),
        }
    )
    request = urllib.request.Request(
        f"{CDX_API}?{query}",
        headers={"Accept": "application/x-ndjson", "User-Agent": USER_AGENT},
    )
    text, _ = _request_text(
        request,
        label="Arquivo.pt CDX lookup",
        timeout=45,
        opener=opener,
        sleeper=sleeper,
    )
    captures = []
    for item in _parse_cdx(text):
        timestamp = item.get("timestamp")
        if str(item.get("status")) != "200" or not isinstance(timestamp, str):
            continue
        try:
            captures.append(
                dt.datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(
                    tzinfo=dt.timezone.utc
                )
            )
        except ValueError:
            raise RequestError(
                f"Arquivo.pt CDX returned an invalid timestamp: {timestamp}"
            )
    return max(captures) if captures else None


def capture_page(
    target_url: str,
    *,
    opener=None,
    sleeper=None,
) -> str:
    capture_url = CAPTURE_API + urllib.parse.quote(target_url, safe=":/")
    request = urllib.request.Request(
        capture_url,
        headers={"Accept": "text/html", "User-Agent": USER_AGENT},
    )
    body, final_url = _request_text(
        request,
        label="Arquivo.pt capture",
        opener=opener,
        sleeper=sleeper,
    )
    if target_url not in body:
        raise RequestError("Arquivo.pt capture response did not identify the target URL")
    if not final_url.startswith(CAPTURE_API):
        raise RequestError(
            f"Arquivo.pt capture redirected outside the recorder: {final_url}"
        )
    return final_url


def run(today: dt.date | None = None) -> str | None:
    today = dt.datetime.now(dt.timezone.utc).date() if today is None else today
    candidates = load_candidates()
    candidate = select_candidate(
        candidates,
        today=today,
        override=os.environ.get("ARQUIVO_APP", "").strip(),
    )
    target_url = candidate["archive_url"]
    cooldown_days = min(COOLDOWN_DAYS, max(0, len(candidates) - 1))
    latest = recent_capture(
        target_url,
        today=today,
        cooldown_days=cooldown_days,
    )
    if latest is not None:
        print(
            "Arquivo.pt: skip"
            f" app={candidate['slug']}"
            f" captured={latest.isoformat()}"
        )
        return None
    if not validate_url(
        target_url,
        timeout=30,
        attempts=3,
        retry_delays=(10, 30),
    ):
        raise RequestError(f"live guide returned 404/410: {target_url}")
    result = capture_page(target_url)
    print(
        "Arquivo.pt: captured"
        f" app={candidate['slug']}"
        f" locale={'pt-BR' if '/pt-BR/' in target_url else 'en'}"
        f" url={target_url}"
    )
    return result


def main() -> int:
    try:
        run()
        return 0
    except (HTTPStatusError, RequestError, ValueError, KeyError) as error:
        print(f"Arquivo.pt archive failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
