#!/usr/bin/env python3
"""Validate the Standard.site Guide contract and reconcile HTML link hints."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import stat
import sys
import time
from typing import Callable, Iterator, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
PUBLICATION_URL = "https://alice51849.github.io/ios-app-guide"
EXPECTED_DID = "did:plc:kboucnzkxzmqmatvhes4xlt4"
PUBLICATION_COLLECTION = "site.standard.publication"
DOCUMENT_COLLECTION = "site.standard.document"
WELL_KNOWN_PATH = "/.well-known/site.standard.publication/ios-app-guide"
WELL_KNOWN_URL = f"https://alice51849.github.io{WELL_KNOWN_PATH}"
DEFAULT_STATE_RELATIVE = Path("_engine/geo/standard_site_sync_state.json")
MAX_CONTRACT_BYTES = 2 * 1024 * 1024
MAX_DOCUMENTS = 5_000
STATE_VERSION = 1
TRANSACTION_NAME = ".standard-site-sync-transaction"
LOCK_NAME = ".standard-site-sync.lock"

TID_RE = re.compile(r"[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}")
AT_URI_RE = re.compile(
    r"at://(?P<did>did:[a-z0-9]+:[A-Za-z0-9._:%-]+)/"
    r"(?P<collection>site\.standard\.(?:publication|document))/"
    r"(?P<rkey>[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12})"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
APP_KEY_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,127}")
PATH_SEGMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]*")
HEAD_BLOCK_RE = re.compile(
    r"(?P<open><head(?:\s[^>]*)?>)(?P<body>.*?)(?P<close></head\s*>)",
    flags=re.IGNORECASE | re.DOTALL,
)
HEAD_OPEN_RE = re.compile(r"<head(?:\s[^>]*)?>", flags=re.IGNORECASE)
HEAD_CLOSE_RE = re.compile(r"</head\s*>", flags=re.IGNORECASE)
LINK_TAG_RE = re.compile(r"<link\b[^>]*>", flags=re.IGNORECASE | re.DOTALL)
REL_ATTRIBUTE_RE = re.compile(
    r"\brel\s*=\s*(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)'|"
    r"(?P<bare>[^\s\"'=<>`]+))",
    flags=re.IGNORECASE,
)
MANAGED_RELATIONS = {PUBLICATION_COLLECTION, DOCUMENT_COLLECTION}


class SyncError(RuntimeError):
    """The contract or local site cannot be reconciled safely."""


class ContractUnavailable(SyncError):
    """The configured remote contract could not be downloaded."""


@dataclass(frozen=True)
class DocumentLink:
    canonical_url: str
    app_key: str
    at_uri: str
    link_tag: str
    relative_path: str


@dataclass(frozen=True)
class ValidatedContract:
    publication_at_uri: str
    publication_link_tag: str
    well_known_sha256: str
    documents: tuple[DocumentLink, ...]
    managed_sha256: str

    @property
    def documents_by_path(self) -> Mapping[str, DocumentLink]:
        return {document.relative_path: document for document in self.documents}


@dataclass(frozen=True)
class PendingWrite:
    original_sha256: str | None
    replacement: bytes
    mode: int


@dataclass(frozen=True)
class SyncResult:
    status: str
    html_files: int = 0
    html_changed: int = 0
    state_changed: bool = False


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SyncError(f"Contract contains a duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(payload: bytes, *, label: str) -> object:
    if len(payload) > MAX_CONTRACT_BYTES:
        raise SyncError(f"{label} exceeds {MAX_CONTRACT_BYTES} bytes")
    try:
        text = payload.decode("utf-8")
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SyncError(f"{label} is not valid UTF-8 JSON: {error}") from error


def _require_exact_keys(
    value: Mapping[str, object], expected: set[str], *, label: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SyncError(
            f"{label} fields are inconsistent; missing={missing}, extra={extra}"
        )


def _validate_timestamp(value: object) -> None:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise SyncError("Contract generated_at must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SyncError("Contract generated_at is not an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise SyncError("Contract generated_at must include a timezone")


def _validate_at_uri(value: object, collection: str) -> str:
    if not isinstance(value, str):
        raise SyncError(f"{collection} AT-URI must be a string")
    match = AT_URI_RE.fullmatch(value)
    if (
        not match
        or match.group("did") != EXPECTED_DID
        or match.group("collection") != collection
        or not TID_RE.fullmatch(match.group("rkey"))
    ):
        raise SyncError(f"Invalid {collection} AT-URI")
    return value


def _canonical_relative_path(canonical_url: object, site_root: Path) -> str:
    if not isinstance(canonical_url, str) or len(canonical_url) > 2_048:
        raise SyncError("Document canonical_url must be a bounded string")
    parsed = urlsplit(canonical_url)
    expected = urlsplit(PUBLICATION_URL)
    if (
        parsed.scheme != "https"
        or parsed.netloc != expected.netloc
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port is not None
        or "%" in parsed.path
        or "\\" in parsed.path
        or "//" in parsed.path
    ):
        raise SyncError(f"Document canonical_url is outside the Guide: {canonical_url}")
    prefix = expected.path.rstrip("/") + "/"
    if not parsed.path.startswith(prefix):
        raise SyncError(f"Document canonical_url is outside the Guide: {canonical_url}")
    relative = parsed.path[len(prefix) :]
    if not relative.endswith(".html"):
        raise SyncError(f"Document canonical_url is not an HTML file: {canonical_url}")
    segments = relative.split("/")
    if not segments or any(
        not segment or not PATH_SEGMENT_RE.fullmatch(segment) for segment in segments
    ):
        raise SyncError(f"Document canonical_url has an unsafe path: {canonical_url}")
    pure = PurePosixPath(*segments)
    if pure.is_absolute() or any(part in {".", ".."} for part in pure.parts):
        raise SyncError(f"Document canonical_url has an unsafe path: {canonical_url}")

    candidate = site_root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise SyncError(
            f"Document canonical_url has no physical HTML file: {canonical_url}"
        ) from error
    if resolved != candidate or not stat.S_ISREG(candidate.lstat().st_mode):
        raise SyncError(
            f"Document canonical_url must map to a regular Guide file: {canonical_url}"
        )
    if candidate.stat().st_size <= 0:
        raise SyncError(f"Document HTML file is empty: {canonical_url}")
    return pure.as_posix()


def validate_contract(payload: bytes, site_root: Path) -> ValidatedContract:
    parsed = _parse_json(payload, label="Standard.site Guide contract")
    if not isinstance(parsed, dict):
        raise SyncError("Standard.site Guide contract must be a JSON object")
    _require_exact_keys(
        parsed,
        {"contract_version", "generated_at", "publication", "documents"},
        label="Contract",
    )
    if type(parsed["contract_version"]) is not int or parsed["contract_version"] != 1:
        raise SyncError("Unsupported Standard.site Guide contract version")
    _validate_timestamp(parsed["generated_at"])

    publication = parsed["publication"]
    if not isinstance(publication, dict):
        raise SyncError("Contract publication must be an object")
    _require_exact_keys(
        publication,
        {"url", "at_uri", "well_known", "discovery_link_tag"},
        label="Contract publication",
    )
    if publication["url"] != PUBLICATION_URL:
        raise SyncError("Contract publication URL does not match the Guide")
    publication_at_uri = _validate_at_uri(
        publication["at_uri"], PUBLICATION_COLLECTION
    )
    expected_publication_tag = (
        f'<link rel="{PUBLICATION_COLLECTION}" href="{publication_at_uri}">'
    )
    if publication["discovery_link_tag"] != expected_publication_tag:
        raise SyncError("Contract publication discovery link is inconsistent")

    well_known = publication["well_known"]
    if not isinstance(well_known, dict):
        raise SyncError("Contract publication well_known must be an object")
    _require_exact_keys(
        well_known,
        {
            "request_url",
            "request_path",
            "content_type",
            "body",
            "sha256",
            "deploy_at_origin_root",
        },
        label="Contract publication well_known",
    )
    expected_body = publication_at_uri + "\n"
    if (
        well_known["request_url"] != WELL_KNOWN_URL
        or well_known["request_path"] != WELL_KNOWN_PATH
        or well_known["content_type"] != "text/plain; charset=utf-8"
        or well_known["body"] != expected_body
        or well_known["sha256"] != _sha256(expected_body.encode("utf-8"))
        or well_known["deploy_at_origin_root"] is not True
    ):
        raise SyncError("Contract origin-root well-known artifact is inconsistent")

    raw_documents = parsed["documents"]
    if not isinstance(raw_documents, list) or len(raw_documents) > MAX_DOCUMENTS:
        raise SyncError("Contract documents must be a bounded array")
    documents: list[DocumentLink] = []
    seen_urls: set[str] = set()
    seen_uris: set[str] = set()
    for index, raw_document in enumerate(raw_documents):
        if not isinstance(raw_document, dict):
            raise SyncError(f"Contract document {index} must be an object")
        _require_exact_keys(
            raw_document,
            {"canonical_url", "app_key", "at_uri", "link_tag"},
            label=f"Contract document {index}",
        )
        canonical_url = raw_document["canonical_url"]
        if not isinstance(canonical_url, str) or canonical_url in seen_urls:
            raise SyncError("Contract document canonical URLs must be unique strings")
        app_key = raw_document["app_key"]
        if not isinstance(app_key, str) or not APP_KEY_RE.fullmatch(app_key):
            raise SyncError(f"Contract document has an invalid app_key: {app_key!r}")
        at_uri = _validate_at_uri(raw_document["at_uri"], DOCUMENT_COLLECTION)
        expected_link = f'<link rel="{DOCUMENT_COLLECTION}" href="{at_uri}">'
        if raw_document["link_tag"] != expected_link:
            raise SyncError("Contract document verification link is inconsistent")
        if at_uri in seen_uris:
            raise SyncError("Contract document AT-URIs must be unique")
        relative_path = _canonical_relative_path(canonical_url, site_root)
        seen_urls.add(canonical_url)
        seen_uris.add(at_uri)
        documents.append(
            DocumentLink(
                canonical_url=canonical_url,
                app_key=app_key,
                at_uri=at_uri,
                link_tag=expected_link,
                relative_path=relative_path,
            )
        )
    semantic = {
        "publication_url": PUBLICATION_URL,
        "publication_at_uri": publication_at_uri,
        "well_known_sha256": well_known["sha256"],
        "documents": sorted(
            [
            {
                "canonical_url": item.canonical_url,
                "app_key": item.app_key,
                "at_uri": item.at_uri,
            }
                for item in documents
            ],
            key=lambda item: item["canonical_url"],
        ),
    }
    semantic_bytes = json.dumps(
        semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return ValidatedContract(
        publication_at_uri=publication_at_uri,
        publication_link_tag=expected_publication_tag,
        well_known_sha256=str(well_known["sha256"]),
        documents=tuple(documents),
        managed_sha256=_sha256(semantic_bytes),
    )


def _source_url(url: str, *, resolve_host: bool = True) -> str:
    if not isinstance(url, str) or len(url) > 2_048:
        raise SyncError("Contract URL must be a bounded HTTPS URL")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.fragment
    ):
        raise SyncError("Contract URL must be a clean HTTPS URL")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".local"):
        raise SyncError("Contract URL cannot target a local host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if resolve_host:
            try:
                addresses = {
                    ipaddress.ip_address(item[4][0])
                    for item in socket.getaddrinfo(
                        hostname, 443, type=socket.SOCK_STREAM
                    )
                }
            except socket.gaierror as error:
                raise SyncError("Contract URL hostname cannot be resolved") from error
            if not addresses or any(not address.is_global for address in addresses):
                raise SyncError(
                    "Contract URL cannot resolve to a non-public IP address"
                )
    else:
        if not address.is_global:
            raise SyncError("Contract URL cannot target a non-public IP address")
    return url


def fetch_contract(
    url: str,
    *,
    timeout: float = 10.0,
    retries: int = 3,
    retry_delay: float = 1.0,
    opener: Callable[..., object] = urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> bytes | None:
    _source_url(url)
    if not 0.1 <= timeout <= 60:
        raise SyncError("Contract fetch timeout must be between 0.1 and 60 seconds")
    if not 0 <= retries <= 10:
        raise SyncError("Contract fetch retries must be between 0 and 10")
    if not 0 <= retry_delay <= 30:
        raise SyncError("Contract retry delay must be between 0 and 30 seconds")
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ios-app-guide-standard-site-sync/1",
        },
    )
    for attempt in range(retries + 1):
        try:
            with opener(request, timeout=timeout) as response:
                final_url = response.geturl() if hasattr(response, "geturl") else url
                _source_url(str(final_url), resolve_host=False)
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError as error:
                        raise SyncError(
                            "Remote contract has an invalid Content-Length"
                        ) from error
                    if declared_size < 0 or declared_size > MAX_CONTRACT_BYTES:
                        raise SyncError("Remote Standard.site contract is too large")
                payload = response.read(MAX_CONTRACT_BYTES + 1)
                if len(payload) > MAX_CONTRACT_BYTES:
                    raise SyncError("Remote Standard.site contract is too large")
                return payload
        except HTTPError as error:
            if error.code == 404:
                return None
            retryable = error.code == 429 or 500 <= error.code <= 599
            if not retryable or attempt >= retries:
                raise ContractUnavailable(
                    f"Contract fetch failed with HTTP {error.code}"
                ) from error
        except SyncError:
            raise
        except (TimeoutError, socket.timeout, URLError, OSError, ValueError) as error:
            if attempt >= retries:
                raise ContractUnavailable(
                    f"Contract fetch failed after {attempt + 1} attempts"
                ) from error
        sleeper(retry_delay * (2**attempt))
    raise AssertionError("unreachable")


def read_contract_file(path: Path) -> bytes:
    try:
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise SyncError("Local contract fixture must be a regular file")
        if path.stat().st_size > MAX_CONTRACT_BYTES:
            raise SyncError("Local Standard.site contract is too large")
        return path.read_bytes()
    except FileNotFoundError as error:
        raise SyncError(f"Local contract fixture does not exist: {path}") from error
    except OSError as error:
        raise SyncError(f"Cannot read local contract fixture: {path}") from error


def _managed_relation(tag: str) -> str | None:
    matches = list(REL_ATTRIBUTE_RE.finditer(tag))
    values: list[str] = []
    for match in matches:
        value = match.group("double") or match.group("single") or match.group("bare")
        values.extend(value.lower().split())
    managed = MANAGED_RELATIONS.intersection(values)
    if not managed:
        return None
    if len(matches) != 1 or len(managed) != 1 or set(values) != managed:
        raise SyncError("Managed Standard.site link has ambiguous rel attributes")
    return next(iter(managed))


def _expanded_removal_span(source: str, start: int, end: int) -> tuple[int, int]:
    line_start = source.rfind("\n", 0, start) + 1
    next_newline = source.find("\n", end)
    line_end = len(source) if next_newline < 0 else next_newline + 1
    if not source[line_start:start].strip() and not source[end:line_end].strip():
        return line_start, line_end
    return start, end


def _without_spans(source: str, spans: Sequence[tuple[int, int]]) -> str:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    result = source
    for start, end in reversed(merged):
        result = result[:start] + result[end:]
    return result


def _render_head(body: str, desired_tags: Sequence[tuple[str, str]]) -> str:
    managed: list[tuple[re.Match[str], str, str]] = []
    for match in LINK_TAG_RE.finditer(body):
        raw = match.group(0)
        relation = _managed_relation(raw)
        if relation:
            managed.append((match, relation, raw))
    current = [(relation, raw) for _, relation, raw in managed]
    if current == list(desired_tags):
        return body

    spans = [
        _expanded_removal_span(body, match.start(), match.end())
        for match, _, _ in managed
    ]
    cleaned = _without_spans(body, spans)
    newline_match = re.search(r"\r\n|\n|\r", body)
    newline = newline_match.group(0) if newline_match else "\n"
    if not cleaned.endswith(("\n", "\r")):
        cleaned += newline
    return cleaned + newline.join(tag for _, tag in desired_tags) + newline


def render_html(
    source: str,
    *,
    publication_link_tag: str,
    document_link_tag: str | None,
    label: str,
) -> str:
    heads = list(HEAD_BLOCK_RE.finditer(source))
    if (
        not heads
        or len(heads) != len(HEAD_OPEN_RE.findall(source))
        or len(heads) != len(HEAD_CLOSE_RE.findall(source))
    ):
        raise SyncError(f"HTML file has an invalid head structure: {label}")
    for link in LINK_TAG_RE.finditer(source):
        if _managed_relation(link.group(0)) and not any(
            head.start() <= link.start() and link.end() <= head.end()
            for head in heads
        ):
            raise SyncError(f"Managed Standard.site link is outside head: {label}")

    desired: list[tuple[str, str]] = [
        (PUBLICATION_COLLECTION, publication_link_tag)
    ]
    if document_link_tag:
        desired.append((DOCUMENT_COLLECTION, document_link_tag))
    chunks: list[str] = []
    cursor = 0
    for head in heads:
        chunks.append(source[cursor : head.start()])
        chunks.append(head.group("open"))
        chunks.append(_render_head(head.group("body"), desired))
        chunks.append(head.group("close"))
        cursor = head.end()
    chunks.append(source[cursor:])
    return "".join(chunks)


def preserve_managed_links(
    original: str,
    rendered: str,
    *,
    label: str,
) -> str:
    """Carry verified Standard.site discovery links across page regeneration."""
    managed: dict[str, str] = {}
    for match in LINK_TAG_RE.finditer(original):
        raw = match.group(0)
        relation = _managed_relation(raw)
        if not relation:
            continue
        if relation in managed:
            raise SyncError(f"Duplicate {relation} discovery link: {label}")
        managed[relation] = raw
    if not managed:
        return rendered
    publication = managed.get(PUBLICATION_COLLECTION)
    if publication is None:
        raise SyncError(
            f"Standard.site document link lacks publication link: {label}"
        )
    return render_html(
        rendered,
        publication_link_tag=publication,
        document_link_tag=managed.get(DOCUMENT_COLLECTION),
        label=label,
    )


def _discover_html(site_root: Path) -> list[Path]:
    paths: list[Path] = []
    for current, directories, files in os.walk(site_root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in {".git", TRANSACTION_NAME}
            and not (current_path / directory).is_symlink()
        )
        for filename in sorted(files):
            if not filename.endswith(".html"):
                continue
            path = current_path / filename
            if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
                raise SyncError(f"Guide HTML must be a regular file: {path}")
            paths.append(path)
    if not paths:
        raise SyncError("Guide contains no HTML files")
    return sorted(paths, key=lambda path: path.relative_to(site_root).as_posix())


def _state_document(contract: ValidatedContract) -> bytes:
    state = {
        "version": STATE_VERSION,
        "publication_url": PUBLICATION_URL,
        "publication_at_uri": contract.publication_at_uri,
        "managed_sha256": contract.managed_sha256,
        "document_count": len(contract.documents),
    }
    return (json.dumps(state, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_state(path: Path) -> tuple[dict[str, object] | None, bytes | None]:
    if not path.exists():
        return None, None
    if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        raise SyncError("Standard.site sync state must be a regular file")
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise SyncError("Cannot read Standard.site sync state") from error
    parsed = _parse_json(payload, label="Standard.site sync state")
    if not isinstance(parsed, dict):
        raise SyncError("Standard.site sync state must be an object")
    _require_exact_keys(
        parsed,
        {
            "version",
            "publication_url",
            "publication_at_uri",
            "managed_sha256",
            "document_count",
        },
        label="Standard.site sync state",
    )
    if type(parsed["version"]) is not int or parsed["version"] != STATE_VERSION:
        raise SyncError("Unsupported Standard.site sync state version")
    if parsed["publication_url"] != PUBLICATION_URL:
        raise SyncError("Standard.site sync state belongs to another publication")
    _validate_at_uri(parsed["publication_at_uri"], PUBLICATION_COLLECTION)
    if not isinstance(parsed["managed_sha256"], str) or not SHA256_RE.fullmatch(
        parsed["managed_sha256"]
    ):
        raise SyncError("Standard.site sync state has an invalid managed hash")
    if (
        type(parsed["document_count"]) is not int
        or not 0 <= parsed["document_count"] <= MAX_DOCUMENTS
    ):
        raise SyncError("Standard.site sync state has an invalid document count")
    return parsed, payload


def _normalise_root_and_state(
    site_root: Path, state_path: Path | None
) -> tuple[Path, Path]:
    try:
        root = site_root.resolve(strict=True)
    except OSError as error:
        raise SyncError(f"Guide site root does not exist: {site_root}") from error
    if not root.is_dir():
        raise SyncError(f"Guide site root is not a directory: {root}")
    raw_state = state_path or (root / DEFAULT_STATE_RELATIVE)
    if not raw_state.is_absolute():
        raw_state = root / raw_state
    resolved_state = raw_state.resolve(strict=False)
    try:
        resolved_state.relative_to(root)
    except ValueError as error:
        raise SyncError("Standard.site sync state must stay inside the Guide") from error
    if resolved_state.suffix != ".json":
        raise SyncError("Standard.site sync state must be a JSON file")
    relative_state = resolved_state.relative_to(root)
    current = root
    for part in relative_state.parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise SyncError("Standard.site sync state cannot use symbolic directories")
    return root, resolved_state


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    temporary = path.with_name(path.name + ".new")
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _exclusive_lock(state_path: Path) -> Iterator[None]:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.parent / LOCK_NAME
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SyncError("Another Standard.site sync is already running") from error
        acquired = True
        yield
    finally:
        if acquired:
            try:
                descriptor_stat = os.fstat(descriptor)
                path_stat = os.stat(lock_path, follow_symlinks=False)
                if (
                    descriptor_stat.st_dev == path_stat.st_dev
                    and descriptor_stat.st_ino == path_stat.st_ino
                ):
                    lock_path.unlink()
            except FileNotFoundError:
                pass
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _safe_relative_target(site_root: Path, relative: object) -> Path:
    if not isinstance(relative, str):
        raise SyncError("Transaction target path is invalid")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        raise SyncError("Transaction target escapes the Guide")
    target = site_root.joinpath(*pure.parts)
    if target.resolve(strict=False) != target:
        raise SyncError("Transaction target uses a symbolic link")
    return target


def _read_journal(transaction: Path) -> dict[str, object]:
    journal_path = transaction / "journal.json"
    if not journal_path.is_file():
        if transaction.is_dir() and not any(transaction.iterdir()):
            transaction.rmdir()
            return {}
        raise SyncError("Incomplete Standard.site transaction has no journal")
    parsed = _parse_json(journal_path.read_bytes(), label="Standard.site transaction")
    if not isinstance(parsed, dict):
        raise SyncError("Standard.site transaction journal is invalid")
    return parsed


def _validate_journal_entries(
    site_root: Path, transaction: Path, entries: Sequence[object]
) -> list[tuple[dict[str, object], Path, Path, Path]]:
    validated: list[tuple[dict[str, object], Path, Path, Path]] = []
    seen_targets: set[Path] = set()
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            raise SyncError("Standard.site transaction entry is invalid")
        _require_exact_keys(
            raw_entry,
            {
                "target",
                "stage",
                "backup",
                "existed",
                "original_sha256",
                "replacement_sha256",
            },
            label="Standard.site transaction entry",
        )
        target = _safe_relative_target(site_root, raw_entry["target"])
        if target in seen_targets:
            raise SyncError("Standard.site transaction has duplicate targets")
        seen_targets.add(target)
        expected_stage = f"staged/{index:06d}"
        expected_backup = f"backup/{index:06d}"
        if (
            raw_entry["stage"] != expected_stage
            or raw_entry["backup"] != expected_backup
            or type(raw_entry["existed"]) is not bool
            or not isinstance(raw_entry["replacement_sha256"], str)
            or not SHA256_RE.fullmatch(raw_entry["replacement_sha256"])
            or (
                raw_entry["existed"]
                and (
                    not isinstance(raw_entry["original_sha256"], str)
                    or not SHA256_RE.fullmatch(raw_entry["original_sha256"])
                )
            )
            or (
                not raw_entry["existed"]
                and raw_entry["original_sha256"] is not None
            )
        ):
            raise SyncError("Standard.site transaction entry is inconsistent")
        stage = transaction / expected_stage
        backup = transaction / expected_backup
        if stage.parent != transaction / "staged" or backup.parent != transaction / "backup":
            raise SyncError("Standard.site transaction artifact path is invalid")
        validated.append((raw_entry, target, stage, backup))
    return validated


def _cleanup_transaction(transaction: Path) -> None:
    shutil.rmtree(transaction)
    _fsync_directory(transaction.parent)


def _recover_transaction(site_root: Path, transaction: Path) -> None:
    if not transaction.exists():
        return
    journal = _read_journal(transaction)
    if not journal:
        return
    phase = journal.get("phase")
    entries = journal.get("entries")
    if phase not in {
        "preparing",
        "prepared",
        "backups_ready",
        "applying",
        "committed",
    } or not isinstance(entries, list):
        raise SyncError("Standard.site transaction journal is inconsistent")
    validated_entries = _validate_journal_entries(site_root, transaction, entries)

    if phase == "applying":
        for raw_entry, target, stage, backup in validated_entries:
            existed = raw_entry["existed"]
            replacement_sha = raw_entry["replacement_sha256"]
            if existed:
                original_sha = raw_entry["original_sha256"]
                if (
                    not backup.is_file()
                    or _sha256(backup.read_bytes()) != original_sha
                ):
                    raise SyncError("Cannot recover Standard.site transaction backup")
                os.replace(backup, target)
            elif target.exists():
                if stage.exists():
                    raise SyncError(
                        "Cannot determine whether interrupted transaction created file"
                    )
                if (
                    _sha256(target.read_bytes()) != replacement_sha
                ):
                    raise SyncError("Cannot safely remove interrupted transaction file")
                target.unlink()
        _cleanup_transaction(transaction)
        return

    if phase == "committed":
        for raw_entry, target, _, _ in validated_entries:
            replacement_sha = raw_entry["replacement_sha256"]
            if (
                not target.is_file()
                or _sha256(target.read_bytes()) != replacement_sha
            ):
                raise SyncError("Committed Standard.site transaction is incomplete")
        _cleanup_transaction(transaction)
        return

    _cleanup_transaction(transaction)


def _stage_bytes(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, mode)


def _install_stage(stage: Path, target: Path) -> None:
    os.replace(stage, target)


def _transactional_write(
    site_root: Path, state_path: Path, writes: Mapping[Path, PendingWrite]
) -> int:
    if not writes:
        return 0
    transaction = state_path.parent / TRANSACTION_NAME
    if transaction.exists():
        _recover_transaction(site_root, transaction)
    transaction.mkdir(mode=0o700)
    journal: dict[str, object] = {"version": 1, "phase": "preparing", "entries": []}
    _atomic_json(transaction / "journal.json", journal)
    entries: list[dict[str, object]] = []
    try:
        for index, target in enumerate(
            sorted(writes, key=lambda path: path.relative_to(site_root).as_posix())
        ):
            write = writes[target]
            relative = target.relative_to(site_root).as_posix()
            stage_name = f"staged/{index:06d}"
            backup_name = f"backup/{index:06d}"
            stage = transaction / stage_name
            _stage_bytes(stage, write.replacement, write.mode)
            entries.append(
                {
                    "target": relative,
                    "stage": stage_name,
                    "backup": backup_name,
                    "existed": write.original_sha256 is not None,
                    "original_sha256": write.original_sha256,
                    "replacement_sha256": _sha256(write.replacement),
                }
            )
        journal = {"version": 1, "phase": "prepared", "entries": entries}
        _atomic_json(transaction / "journal.json", journal)

        for entry in entries:
            target = _safe_relative_target(site_root, entry["target"])
            original_sha = entry["original_sha256"]
            if original_sha is None:
                if target.exists():
                    raise SyncError(
                        f"Concurrent write created transaction target: {entry['target']}"
                    )
            elif (
                not target.is_file()
                or _sha256(target.read_bytes()) != original_sha
            ):
                raise SyncError(
                    f"Guide file changed during Standard.site sync: {entry['target']}"
                )

        (transaction / "backup").mkdir()
        for entry in entries:
            if entry["existed"]:
                target = _safe_relative_target(site_root, entry["target"])
                os.link(target, transaction / str(entry["backup"]))
        journal["phase"] = "backups_ready"
        _atomic_json(transaction / "journal.json", journal)
        journal["phase"] = "applying"
        _atomic_json(transaction / "journal.json", journal)

        try:
            touched_directories: set[Path] = set()
            for entry in entries:
                target = _safe_relative_target(site_root, entry["target"])
                stage = transaction / str(entry["stage"])
                target.parent.mkdir(parents=True, exist_ok=True)
                _install_stage(stage, target)
                touched_directories.add(target.parent)
            for directory in touched_directories:
                _fsync_directory(directory)
            journal["phase"] = "committed"
            _atomic_json(transaction / "journal.json", journal)
        except Exception:
            _recover_transaction(site_root, transaction)
            raise
        _cleanup_transaction(transaction)
        return len(entries)
    except Exception as error:
        if transaction.exists():
            phase = _read_journal(transaction).get("phase")
            if phase == "applying":
                _recover_transaction(site_root, transaction)
            else:
                _cleanup_transaction(transaction)
        if isinstance(error, SyncError):
            raise
        raise SyncError(f"Atomic Standard.site update failed: {error}") from error


def _prepare_html_writes(
    site_root: Path, contract: ValidatedContract
) -> tuple[list[Path], dict[Path, PendingWrite]]:
    html_paths = _discover_html(site_root)
    documents = contract.documents_by_path
    discovered = {
        path.relative_to(site_root).as_posix(): path for path in html_paths
    }
    missing = sorted(set(documents) - set(discovered))
    if missing:
        raise SyncError(f"Contract document HTML disappeared: {missing[0]}")

    writes: dict[Path, PendingWrite] = {}
    for relative, path in discovered.items():
        try:
            original = path.read_bytes()
            source = original.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise SyncError(f"Cannot read Guide HTML as UTF-8: {relative}") from error
        document = documents.get(relative)
        rendered = render_html(
            source,
            publication_link_tag=contract.publication_link_tag,
            document_link_tag=document.link_tag if document else None,
            label=relative,
        ).encode("utf-8")
        if rendered != original:
            writes[path] = PendingWrite(
                original_sha256=_sha256(original),
                replacement=rendered,
                mode=stat.S_IMODE(path.stat().st_mode),
            )
    return html_paths, writes


def _synchronize_contract_locked(
    contract: ValidatedContract,
    *,
    root: Path,
    resolved_state: Path,
) -> SyncResult:
    transaction = resolved_state.parent / TRANSACTION_NAME
    _recover_transaction(root, transaction)
    _, old_state_payload = _load_state(resolved_state)
    html_paths, writes = _prepare_html_writes(root, contract)
    state_payload = _state_document(contract)
    state_changed = state_payload != old_state_payload
    if state_changed:
        writes[resolved_state] = PendingWrite(
            original_sha256=(
                _sha256(old_state_payload) if old_state_payload is not None else None
            ),
            replacement=state_payload,
            mode=(
                stat.S_IMODE(resolved_state.stat().st_mode)
                if resolved_state.exists()
                else 0o644
            ),
        )
    html_changed = sum(path.suffix == ".html" for path in writes)
    _transactional_write(root, resolved_state, writes)
    return SyncResult(
        status="applied",
        html_files=len(html_paths),
        html_changed=html_changed,
        state_changed=state_changed,
    )


def synchronize_payload(
    payload: bytes,
    *,
    site_root: Path,
    state_path: Path | None = None,
) -> SyncResult:
    root, resolved_state = _normalise_root_and_state(site_root, state_path)
    contract = validate_contract(payload, root)
    with _exclusive_lock(resolved_state):
        return _synchronize_contract_locked(
            contract,
            root=root,
            resolved_state=resolved_state,
        )


def synchronize_source(
    *,
    site_root: Path,
    state_path: Path | None = None,
    contract_url: str | None = None,
    contract_file: Path | None = None,
    allow_initial_404: bool = False,
    timeout: float = 10.0,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> SyncResult:
    if bool(contract_url) == bool(contract_file):
        raise SyncError("Choose exactly one contract URL or local contract fixture")
    root, resolved_state = _normalise_root_and_state(site_root, state_path)
    with _exclusive_lock(resolved_state):
        transaction = resolved_state.parent / TRANSACTION_NAME
        if transaction.exists():
            _recover_transaction(root, transaction)
        state, _ = _load_state(resolved_state)
        if contract_file:
            payload = read_contract_file(contract_file)
        else:
            payload = fetch_contract(
                str(contract_url),
                timeout=timeout,
                retries=retries,
                retry_delay=retry_delay,
            )
            if payload is None:
                if allow_initial_404 and state is None:
                    return SyncResult(status="initial-contract-not-published")
                raise ContractUnavailable(
                    "Standard.site contract returned 404 after initial activation"
                )
        contract = validate_contract(payload, root)
        return _synchronize_contract_locked(
            contract,
            root=root,
            resolved_state=resolved_state,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-root",
        type=Path,
        default=Path(os.environ.get("GEO_PAGES", HERE / "pages")),
    )
    parser.add_argument("--state-file", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--contract-url")
    source.add_argument("--contract-file", type=Path)
    parser.add_argument("--allow-initial-404", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=1.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        result = synchronize_source(
            site_root=arguments.site_root,
            state_path=arguments.state_file,
            contract_url=arguments.contract_url,
            contract_file=arguments.contract_file,
            allow_initial_404=arguments.allow_initial_404,
            timeout=arguments.timeout,
            retries=arguments.retries,
            retry_delay=arguments.retry_delay,
        )
    except SyncError as error:
        print(f"Standard.site sync failed: {error}", file=sys.stderr)
        return 1
    if result.status == "initial-contract-not-published":
        print("Standard.site contract is not published yet (HTTP 404); skipping.")
        return 0
    print(
        "Standard.site sync complete: "
        f"html={result.html_files}, changed={result.html_changed}, "
        f"state_changed={str(result.state_changed).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
