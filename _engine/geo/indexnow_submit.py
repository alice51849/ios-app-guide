#!/usr/bin/env python3
"""Submit every public GEO sitemap URL to IndexNow with strict delivery checks."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE  # noqa: E402


DEFAULT_SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
ENDPOINTS = (
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
)
ACCEPTED_STATUSES = {200, 202}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
KEY_RE = re.compile(r"[A-Za-z0-9_-]{8,128}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
DEFAULT_BATCH_SIZE = 10_000
REQUEST_TIMEOUT_SECONDS = 30
PRIVATE_TOP_LEVEL_PATHS = {"_engine", ".git", ".github"}
FINDER_CATALOG_PATH = Path("data/verified-ios-app-finder-catalog.json")


class SubmissionError(RuntimeError):
    """Raised when an IndexNow endpoint does not accept a batch."""


def sitemap_locations(path: Path) -> list[str]:
    if not path.is_file():
        raise ValueError(f"Missing sitemap: {path}")
    content = path.read_text(encoding="utf-8")
    return [
        html.unescape(value.strip())
        for value in re.findall(r"<loc>([^<]+)</loc>", content)
        if value.strip()
    ]


def validate_public_url(url: str, site: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(site)
    base_path = expected.path.rstrip("/") + "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != expected.netloc
        or not parsed.path.startswith(base_path)
        or parsed.query
        or parsed.fragment
        or len(url) > 2048
        or any(character.isspace() for character in url)
    ):
        raise ValueError(f"Invalid IndexNow URL for {site}: {url}")


def is_same_host_out_of_scope(url: str, site: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(site)
    base_path = expected.path.rstrip("/") + "/"
    return (
        parsed.scheme == "https"
        and parsed.netloc == expected.netloc
        and not parsed.path.startswith(base_path)
        and not parsed.query
        and not parsed.fragment
        and len(url) <= 2048
        and not any(character.isspace() for character in url)
    )


def read_urls(pages_dir: Path, site: str) -> list[str]:
    sitemap_index = pages_dir / "sitemap_index.xml"
    sitemap_paths: list[Path] = []
    if sitemap_index.is_file():
        for location in sitemap_locations(sitemap_index):
            validate_public_url(location, site)
            name = Path(urllib.parse.urlsplit(location).path).name
            candidate = pages_dir / name
            if name.endswith(".xml") and candidate.is_file():
                sitemap_paths.append(candidate)
    localized_sitemaps = sorted(
        path for path in pages_dir.glob("*/sitemap.xml") if path.is_file()
    )
    for path in localized_sitemaps:
        if path not in sitemap_paths:
            sitemap_paths.append(path)
    if not sitemap_paths:
        sitemap_paths = [pages_dir / "sitemap.xml"]

    urls: list[str] = []
    seen: set[str] = set()
    excluded_out_of_scope = 0
    for sitemap_path in sitemap_paths:
        for url in sitemap_locations(sitemap_path):
            try:
                validate_public_url(url, site)
            except ValueError:
                if is_same_host_out_of_scope(url, site):
                    excluded_out_of_scope += 1
                    continue
                raise
            if url not in seen:
                seen.add(url)
                urls.append(url)
    print(f"excluded_out_of_scope={excluded_out_of_scope}")
    if not urls:
        raise ValueError("IndexNow sitemap collection returned zero URLs")
    return urls


def git_head_sha(
    pages_dir: Path,
    *,
    runner=subprocess.run,
) -> str:
    result = runner(
        [
            "git",
            "-C",
            str(pages_dir),
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    sha = result.stdout.strip().lower()
    if not SHA_RE.fullmatch(sha):
        raise ValueError("IndexNow HEAD must resolve to a full commit hash")
    return sha


def read_last_submitted_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    sha = path.read_text(encoding="utf-8").strip().lower()
    if not SHA_RE.fullmatch(sha):
        raise ValueError("IndexNow last-submitted SHA is invalid")
    return sha


def write_last_submitted_sha(path: Path, sha: str) -> None:
    normalized = sha.strip().lower()
    if not SHA_RE.fullmatch(normalized):
        raise ValueError("IndexNow last-submitted SHA is invalid")
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.new")
    pending.write_text(f"{normalized}\n", encoding="utf-8")
    pending.replace(path)


def write_private_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    finally:
        temporary_path.unlink(missing_ok=True)


def url_set_digest(urls: list[str]) -> str:
    payload = json.dumps(
        sorted(set(urls)),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def app_url_acceptances(
    pages_dir: Path,
    site: str,
    submitted_urls: list[str],
) -> list[dict]:
    catalog_path = pages_dir / FINDER_CATALOG_PATH
    try:
        document = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as error:
        raise ValueError(
            f"Unable to read verified App catalog: {catalog_path}"
        ) from error
    records = document.get("apps")
    if not isinstance(records, list):
        raise ValueError("Verified App catalog must contain an apps array")

    submitted = set(submitted_urls)
    identities: set[tuple[str, str]] = set()
    acceptances = []
    for record in records:
        if not isinstance(record, dict) or record.get("verified_live") is False:
            continue
        key = str(record.get("key") or "").strip()
        app_store_id = str(record.get("app_store_id") or "").strip()
        identity = (key, app_store_id)
        if (
            not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", key)
            or not app_store_id.isdigit()
            or identity in identities
        ):
            raise ValueError("Verified App catalog has an invalid identity")
        identities.add(identity)
        expected_urls = [
            f"{site.rstrip('/')}/{locale}/{key}.html"
            for locale in OFFICIAL_LOCALES
        ]
        accepted_urls = sorted(set(expected_urls) & submitted)
        if not accepted_urls:
            continue
        acceptances.append(
            {
                "key": key,
                "app_store_id": app_store_id,
                "required_url_count": len(expected_urls),
                "accepted_url_count": len(accepted_urls),
                "complete": len(accepted_urls) == len(expected_urls),
                "required_url_set_sha256": url_set_digest(expected_urls),
                "accepted_url_set_sha256": url_set_digest(accepted_urls),
            }
        )
    return acceptances


def submission_receipt(
    *,
    pages_dir: Path,
    site: str,
    pages_sha: str,
    baseline_sha: str | None,
    urls: list[str],
    endpoint_batches: dict[str, list[dict]],
    accepted_at: str,
) -> dict:
    return {
        "version": 1,
        "kind": "indexnow_submission_receipt",
        "semantics": "accepted_by_endpoints_not_indexed",
        "site": site.rstrip("/"),
        "pages_sha": pages_sha,
        "processed_through_sha": pages_sha,
        "baseline_sha": baseline_sha,
        "accepted_at": accepted_at,
        "disposition": "accepted" if urls else "no_changed_public_urls",
        "url_count": len(urls),
        "url_set_sha256": url_set_digest(urls),
        "endpoints": [
            {
                "url": endpoint,
                "accepted_batch_count": len(batches),
                "batches": batches,
            }
            for endpoint, batches in endpoint_batches.items()
        ],
        "app_acceptances": app_url_acceptances(
            pages_dir,
            site,
            urls,
        ),
    }


def carry_receipt_through_noop(
    path: Path,
    *,
    pages_sha: str,
    processed_at: str,
) -> dict | None:
    if not path.is_file():
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"Invalid existing IndexNow receipt: {path}") from error
    if (
        not isinstance(receipt, dict)
        or receipt.get("version") != 1
        or receipt.get("kind") != "indexnow_submission_receipt"
        or receipt.get("semantics") != "accepted_by_endpoints_not_indexed"
        or not SHA_RE.fullmatch(str(receipt.get("pages_sha") or ""))
    ):
        raise ValueError(f"Invalid existing IndexNow receipt: {path}")
    receipt["processed_through_sha"] = pages_sha
    receipt["last_noop_at"] = processed_at
    return receipt


def git_changed_paths(
    pages_dir: Path,
    baseline: str | None,
    *,
    runner=subprocess.run,
) -> list[Path]:
    if baseline is not None and (
        not baseline or any(character in baseline for character in "\r\n\0")
    ):
        raise ValueError("IndexNow git baseline must be single-line text")
    command = (
        [
            "git",
            "-C",
            str(pages_dir),
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            f"{baseline}..HEAD",
        ]
        if baseline
        else [
            "git",
            "-C",
            str(pages_dir),
            "ls-files",
            "-z",
        ]
    )
    result = runner(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    paths: set[Path] = set()
    for raw_path in result.stdout.split("\0"):
        if not raw_path:
            continue
        path = Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe changed path from git: {raw_path}")
        paths.add(path)
    return sorted(paths, key=lambda path: path.as_posix())


def git_change_set(
    pages_dir: Path,
    since: str,
    *,
    runner=subprocess.run,
) -> tuple[str | None, list[Path]]:
    if not since.strip() or any(character in since for character in "\r\n\0"):
        raise ValueError("IndexNow git since value must be non-empty single-line text")
    baseline_result = runner(
        [
            "git",
            "-C",
            str(pages_dir),
            "rev-list",
            "-1",
            "--first-parent",
            f"--before={since}",
            "HEAD",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    baseline = baseline_result.stdout.strip() or None
    return baseline, git_changed_paths(
        pages_dir,
        baseline,
        runner=runner,
    )


def git_sitemap_urls(
    pages_dir: Path,
    site: str,
    ref: str,
    *,
    runner=subprocess.run,
) -> list[str]:
    if not ref or any(character in ref for character in "\r\n\0"):
        raise ValueError("IndexNow git sitemap ref must be non-empty single-line text")
    result = runner(
        [
            "git",
            "-C",
            str(pages_dir),
            "grep",
            "-h",
            "-o",
            r"<loc>[^<]*</loc>",
            ref,
            "--",
            ":(glob)sitemap*.xml",
            ":(glob)**/sitemap*.xml",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args if hasattr(result, "args") else "git grep",
            output=result.stdout,
            stderr=result.stderr,
        )
    urls: set[str] = set()
    for value in re.findall(r"<loc>([^<]+)</loc>", result.stdout):
        url = html.unescape(value.strip())
        if not url:
            continue
        try:
            validate_public_url(url, site)
        except ValueError:
            if is_same_host_out_of_scope(url, site):
                continue
            raise
        name = Path(urllib.parse.urlsplit(url).path).name
        if name == "sitemap.xml" or (
            name.startswith("sitemap_") and name.endswith(".xml")
        ):
            continue
        urls.add(url)
    return sorted(urls)


def _relative_sitemap_urls(urls: list[str], site: str) -> dict[str, str]:
    prefix = urllib.parse.urlsplit(site).path.rstrip("/") + "/"
    mapped = {}
    for url in urls:
        path = urllib.parse.urlsplit(url).path
        if path.startswith(prefix):
            mapped[urllib.parse.unquote(path[len(prefix) :])] = url
    return mapped


def _public_path(path: Path) -> bool:
    return bool(
        path.parts
        and path.parts[0] not in PRIVATE_TOP_LEVEL_PATHS
    )


def changed_urls(
    pages_dir: Path,
    site: str,
    paths: list[Path],
    previous_urls: list[str] | None = None,
) -> list[str]:
    sitemap_urls = read_urls(pages_dir, site)
    by_relative_path = _relative_sitemap_urls(sitemap_urls, site)
    previous_by_relative_path = _relative_sitemap_urls(
        previous_urls or [],
        site,
    )
    selected: set[str] = set()
    for path in paths:
        if path.is_absolute() or ".." in path.parts or not _public_path(path):
            continue
        relative = path.as_posix()
        candidates = [relative]
        if relative == "index.html":
            candidates.append("")
        elif relative.endswith("/index.html"):
            candidates.append(relative[: -len("index.html")])
        for candidate in candidates:
            url = by_relative_path.get(candidate)
            if url:
                selected.add(url)
        if (pages_dir / path).exists():
            continue
        for candidate in candidates:
            previous_url = previous_by_relative_path.get(candidate)
            if previous_url:
                selected.add(previous_url)
    return sorted(selected)


def read_changed_urls(
    pages_dir: Path,
    site: str,
    since: str,
    *,
    baseline_sha: str | None = None,
    runner=subprocess.run,
) -> list[str]:
    if baseline_sha is None:
        baseline, paths = git_change_set(pages_dir, since, runner=runner)
    else:
        baseline = baseline_sha
        paths = git_changed_paths(pages_dir, baseline, runner=runner)
    previous_urls = (
        git_sitemap_urls(pages_dir, site, baseline, runner=runner)
        if baseline
        else []
    )
    urls = changed_urls(pages_dir, site, paths, previous_urls)
    print(
        f"baseline={baseline or 'empty-tree'} "
        f"changed_paths={len(paths)} changed_public_urls={len(urls)}"
    )
    return urls


def read_key(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"Missing IndexNow key file: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not KEY_RE.fullmatch(key):
        raise ValueError("IndexNow key must be 8-128 URL-safe characters")
    return key


def key_location_for(site: str, key: str, key_location: str | None = None) -> str:
    """Where IndexNow fetches the key file.

    IndexNow accepts a keyLocation anywhere under the submitted host, so the
    default keeps the key beside the site root that is being submitted. An
    explicit ``key_location`` is required to live on that same host, otherwise
    every endpoint would reject the batch.
    """
    site = site.rstrip("/")
    if key_location is None:
        return f"{site}/{key}.txt"
    parsed = urllib.parse.urlsplit(key_location)
    expected = urllib.parse.urlsplit(site)
    if (
        parsed.scheme != expected.scheme
        or parsed.netloc != expected.netloc
        or not parsed.path.endswith(".txt")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            f"IndexNow key location must be a .txt URL on {expected.netloc}: "
            f"{key_location}"
        )
    return key_location


def payload_for(
    urls: list[str],
    key: str,
    site: str,
    key_location: str | None = None,
) -> bytes:
    host = urllib.parse.urlsplit(site).netloc
    return json.dumps(
        {
            "host": host,
            "key": key,
            "keyLocation": key_location_for(site, key, key_location),
            "urlList": urls,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def submit_endpoint(
    endpoint: str,
    payload: bytes,
    *,
    opener=None,
    sleeper=time.sleep,
) -> int:
    opener = urllib.request.urlopen if opener is None else opener
    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "ios-app-guide-indexnow/2.0",
            },
        )
        try:
            with opener(
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                body = response.read(1000).decode("utf-8", "replace").strip()
                if response.status not in ACCEPTED_STATUSES:
                    raise SubmissionError(
                        f"{endpoint} returned HTTP {response.status}: {body}"
                    )
                print(f"  {endpoint} -> HTTP {response.status}")
                return response.status
        except urllib.error.HTTPError as error:
            body = error.read(1000).decode("utf-8", "replace").strip()
            last_error = SubmissionError(
                f"{endpoint} returned HTTP {error.code}: {body}"
            )
            if error.code not in RETRYABLE_STATUSES:
                raise last_error from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
        if attempt < 3:
            sleeper(2 ** (attempt - 1))
    raise SubmissionError(
        f"{endpoint} failed after 3 attempts: {last_error}"
    ) from last_error


def submit(
    urls: list[str],
    key: str,
    site: str = DEFAULT_SITE,
    *,
    endpoints: tuple[str, ...] = ENDPOINTS,
    sender=submit_endpoint,
    key_location: str | None = None,
) -> bool:
    """Compatibility helper that reports failure after trying every endpoint."""
    payload = payload_for(urls, key, site, key_location)
    accepted = True
    for endpoint in endpoints:
        try:
            sender(endpoint, payload)
        except SubmissionError as error:
            print(error)
            accepted = False
    return accepted


def submit_all(
    urls: list[str],
    key: str,
    site: str,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    endpoints: tuple[str, ...] = ENDPOINTS,
    sender=submit_endpoint,
    acceptance_recorder=None,
    key_location: str | None = None,
) -> int:
    if not 1 <= batch_size <= 10_000:
        raise ValueError("IndexNow batch size must be between 1 and 10000")
    accepted = 0
    for offset in range(0, len(urls), batch_size):
        chunk = urls[offset : offset + batch_size]
        print(
            f"batch {offset // batch_size + 1}: "
            f"{len(chunk)} URLs"
        )
        payload = payload_for(chunk, key, site, key_location)
        for endpoint in endpoints:
            status = sender(endpoint, payload)
            if acceptance_recorder is not None:
                acceptance_recorder(
                    endpoint,
                    offset // batch_size + 1,
                    len(chunk),
                    status if isinstance(status, int) else None,
                )
        accepted += len(chunk)
    return accepted


def run(
    pages_dir: Path,
    site: str,
    key_file: Path,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    git_since: str | None = None,
    state_file: Path | None = None,
    receipt_file: Path | None = None,
    limit: int | None = None,
    key_location: str | None = None,
    runner=subprocess.run,
    sender=submit_endpoint,
    clock=lambda: datetime.now(timezone.utc),
) -> int:
    site = site.rstrip("/")
    current_sha = (
        git_head_sha(pages_dir, runner=runner)
        if state_file is not None or receipt_file is not None
        else None
    )
    last_submitted_sha = (
        read_last_submitted_sha(state_file)
        if state_file is not None and git_since
        else None
    )
    if (
        git_since
        and last_submitted_sha is not None
        and last_submitted_sha == current_sha
    ):
        urls: list[str] = []
        print(
            f"baseline={last_submitted_sha} "
            "changed_paths=0 changed_public_urls=0"
        )
    else:
        urls = (
            read_changed_urls(
                pages_dir,
                site,
                git_since,
                baseline_sha=last_submitted_sha,
                runner=runner,
            )
            if git_since
            else read_urls(pages_dir, site)
        )
    complete_change_set = True
    if limit is not None:
        if limit <= 0:
            raise ValueError("IndexNow limit must be positive")
        complete_change_set = len(urls) <= limit
        urls = urls[:limit]
    if not urls:
        if state_file is not None and current_sha is not None:
            write_last_submitted_sha(state_file, current_sha)
        if receipt_file is not None and current_sha is not None:
            processed_at = clock().astimezone(timezone.utc).isoformat()
            receipt = carry_receipt_through_noop(
                receipt_file,
                pages_sha=current_sha,
                processed_at=processed_at,
            )
            if receipt is None:
                receipt = submission_receipt(
                    pages_dir=pages_dir,
                    site=site,
                    pages_sha=current_sha,
                    baseline_sha=last_submitted_sha,
                    urls=[],
                    endpoint_batches={endpoint: [] for endpoint in ENDPOINTS},
                    accepted_at=processed_at,
                )
            write_private_json(
                receipt_file,
                receipt,
            )
        print("No changed public URLs; nothing to submit")
        return 0
    key = read_key(key_file)
    resolved_key_location = key_location_for(site, key, key_location)
    print(
        f"host={urllib.parse.urlsplit(site).netloc} "
        f"key={key[:8]}... keyLocation={resolved_key_location} "
        f"urls={len(urls)}"
    )
    endpoint_batches: dict[str, list[dict]] = {
        endpoint: [] for endpoint in ENDPOINTS
    }

    def record_acceptance(
        endpoint: str,
        batch: int,
        url_count: int,
        status: int | None,
    ) -> None:
        endpoint_batches.setdefault(endpoint, []).append(
            {
                "batch": batch,
                "url_count": url_count,
                "http_status": status,
            }
        )

    accepted = submit_all(
        urls,
        key,
        site,
        batch_size=batch_size,
        sender=sender,
        acceptance_recorder=record_acceptance,
        key_location=resolved_key_location,
    )
    print(f"Accepted {accepted}/{len(urls)} URLs by every IndexNow endpoint")
    if accepted != len(urls):
        raise SubmissionError(
            f"Only {accepted}/{len(urls)} IndexNow URLs were accepted"
        )
    if (
        state_file is not None
        and current_sha is not None
        and complete_change_set
    ):
        write_last_submitted_sha(state_file, current_sha)
    if receipt_file is not None:
        if current_sha is None:
            raise SubmissionError(
                "IndexNow receipt requires a resolved Pages commit"
            )
        write_private_json(
            receipt_file,
            submission_receipt(
                pages_dir=pages_dir,
                site=site,
                pages_sha=current_sha,
                baseline_sha=last_submitted_sha,
                urls=urls,
                endpoint_batches=endpoint_batches,
                accepted_at=clock().astimezone(timezone.utc).isoformat(),
            ),
        )
    return accepted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=HERE / "pages")
    parser.add_argument("--site", default=DEFAULT_SITE)
    parser.add_argument(
        "--key-file", type=Path, default=HERE / "indexnow_key.txt"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )
    parser.add_argument(
        "--git-since",
        help=(
            "Submit only public URLs whose repository paths changed since this "
            "git date expression; omit for an explicit full refresh"
        ),
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        help="Durable last successfully processed git SHA.",
    )
    parser.add_argument(
        "--receipt-file",
        type=Path,
        help=(
            "Owner-only JSON receipt for accepted endpoint batches. "
            "Acceptance does not mean indexed."
        ),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--key-location",
        help=(
            "Absolute URL of the key file on the submitted host; defaults to "
            "<site>/<key>.txt"
        ),
    )
    args = parser.parse_args()

    run(
        args.pages_dir,
        args.site,
        args.key_file,
        batch_size=args.batch_size,
        git_since=args.git_since,
        state_file=args.state_file,
        receipt_file=args.receipt_file,
        limit=args.limit,
        key_location=args.key_location,
    )


if __name__ == "__main__":
    main()
