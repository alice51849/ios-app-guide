#!/usr/bin/env python3
"""Maintain one locked, first-party GitHub Discussion resource digest."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any


OWNER = "alice51849"
REPOSITORY = "ios-app-guide"
NAME_WITH_OWNER = f"{OWNER}/{REPOSITORY}"
# The Guide's public host. The GitHub Pages origin still serves the same
# bytes, but every URL these scripts hand out or accept is the owned host.
SITE_ORIGIN = "https://open.cait518.cc"
SITE_HOME = f"{SITE_ORIGIN}/ios-app-guide/"
SITE_FEED = f"{SITE_HOME}feed.json"
ALLOWED_PATH_PREFIXES = (
    "/ios-app-guide/tools/",
    "/ios-app-guide/data/",
    "/ios-app-guide/guides/",
    "/ios-app-guide/apps/",
)
DISCUSSION_TITLE = "Official iOS App Guide updates and practical resources"
CATEGORY_NAME = "Announcements"
CATEGORY_SLUG = "announcements"
SENTINEL = "ios-app-guide-official-discussion"
FORMAT_VERSION = 1
MAX_RESOURCES = 3
MIN_RATE_LIMIT = 500
MIN_UPDATE_INTERVAL = dt.timedelta(days=28)
APPROVED_AUTHORS = frozenset((f"{OWNER}", "github-actions", "github-actions[bot]"))
GRAPHQL_URL = "https://api.github.com/graphql"
GRAPHQL_TIMEOUT = 20
MAX_RESPONSE_BYTES = 1_000_000
MAX_HTML_PROBE_BYTES = 65_536

METADATA_RE = re.compile(
    rf"\n<!-- {re.escape(SENTINEL)}; version=(\d+); "
    r"digest=sha256:([0-9a-f]{64}); source=([0-9a-f]{40}) -->\n?\Z"
)
REDIRECT_RE = re.compile(
    r"""(?ix)
    <meta[^>]+http-equiv\s*=\s*["']?\s*refresh\b
    |window\.location(?:\.href)?\s*=
    |(?:window\.)?location\.replace\s*\(
    """
)
HTML_DOCUMENT_RE = re.compile(r"(?i)<(?:!doctype\s+html|html)\b")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URLISH_RE = re.compile(r"(?i)(?:https?://|www\.)")


REPOSITORY_QUERY = """
query ManagedDiscussion($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    nameWithOwner
    visibility
    isPrivate
    isArchived
    isDisabled
    hasDiscussionsEnabled
    viewerPermission
    discussionCategories(first: 100) {
      totalCount
      pageInfo { hasNextPage }
      nodes { id name slug isAnswerable }
    }
    discussions(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      pageInfo { hasNextPage }
      nodes {
        id
        number
        title
        body
        url
        locked
        updatedAt
        author { login }
        viewerCanUpdate
        category { id name slug isAnswerable }
        comments { totalCount }
      }
    }
  }
  rateLimit { remaining }
}
"""

RATE_LIMIT_QUERY = """
query PublisherRateLimit {
  rateLimit { remaining }
}
"""

CREATE_DISCUSSION_MUTATION = """
mutation CreateManagedDiscussion(
  $repositoryId: ID!
  $categoryId: ID!
  $title: String!
  $body: String!
) {
  createDiscussion(input: {
    repositoryId: $repositoryId
    categoryId: $categoryId
    title: $title
    body: $body
  }) {
    discussion {
      id
      title
      body
      url
      locked
      author { login }
      viewerCanUpdate
      category { id name slug isAnswerable }
      comments { totalCount }
    }
  }
}
"""

LOCK_DISCUSSION_MUTATION = """
mutation LockManagedDiscussion($id: ID!) {
  lockLockable(input: {lockableId: $id}) {
    lockedRecord {
      ... on Discussion {
        id
        locked
        url
      }
    }
  }
}
"""

UPDATE_DISCUSSION_MUTATION = """
mutation UpdateManagedDiscussion($id: ID!, $body: String!) {
  updateDiscussion(input: {discussionId: $id, body: $body}) {
    discussion {
      id
      title
      body
      url
      locked
      author { login }
      viewerCanUpdate
      category { id name slug isAnswerable }
      comments { totalCount }
    }
  }
}
"""


class PublisherError(RuntimeError):
    """A fail-closed publisher error."""


class MutationUncertainError(PublisherError):
    """A mutation transport failed, so its remote outcome is uncertain."""


@dataclasses.dataclass(frozen=True)
class Resource:
    title: str
    url: str
    summary: str


@dataclasses.dataclass(frozen=True)
class Metadata:
    version: int
    digest: str
    source_sha: str


@dataclasses.dataclass(frozen=True)
class RenderedDigest:
    resources: tuple[Resource, ...]
    digest: str
    source_sha: str
    body: str


@dataclasses.dataclass(frozen=True)
class RepositoryState:
    repository_id: str
    category_id: str
    managed: tuple[dict[str, Any], ...]


@dataclasses.dataclass(frozen=True)
class PublicationResult:
    action: str
    digest: str
    url: str | None
    reason: str


def _normalized_text(value: object, *, maximum: int) -> str | None:
    if not isinstance(value, str) or CONTROL_RE.search(value):
        return None
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > maximum:
        return None
    return normalized


def _valid_resource_url(value: object) -> str | None:
    if not isinstance(value, str) or CONTROL_RE.search(value) or "%" in value:
        return None
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname != "open.cait518.cc"
        or parsed.netloc != "open.cait518.cc"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith(".html")
        or not any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)
        or "/answers/" in parsed.path
    ):
        return None
    if urllib.parse.urlunsplit(parsed) != value:
        return None
    return value


def _default_html_loader(repository_root: pathlib.Path, path: str) -> str | None:
    site_prefix = "/ios-app-guide/"
    if not path.startswith(site_prefix):
        return None
    relative = pathlib.PurePosixPath(path.removeprefix(site_prefix))
    if relative.is_absolute() or ".." in relative.parts:
        return None
    candidate = repository_root.joinpath(*relative.parts)
    if candidate.is_symlink() or not candidate.is_file():
        return None
    try:
        with candidate.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(MAX_HTML_PROBE_BYTES)
    except OSError as error:
        raise PublisherError(f"Unable to inspect feed resource {relative}: {error}") from error


def select_resources(
    feed: Mapping[str, object],
    *,
    repository_root: pathlib.Path | None = None,
    html_loader: Callable[[str], str | None] | None = None,
) -> tuple[Resource, ...]:
    """Select at most three canonical resources, preserving feed order."""

    if feed.get("home_page_url") != SITE_HOME or feed.get("feed_url") != SITE_FEED:
        raise PublisherError("feed.json does not declare the exact allowlisted site")
    raw_items = feed.get("items")
    if not isinstance(raw_items, list):
        raise PublisherError("feed.json items must be a list")
    if html_loader is None:
        if repository_root is None:
            raise PublisherError("A repository root is required for HTML validation")
        html_loader = lambda path: _default_html_loader(repository_root, path)

    selected: list[Resource] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        if any(
            value
            for key, value in raw_item.items()
            if "redirect" in str(key).lower()
        ) or raw_item.get("external_url") is not None:
            continue
        url = _valid_resource_url(raw_item.get("url"))
        if url is None or raw_item.get("id") != url or url in seen:
            continue
        title = _normalized_text(raw_item.get("title"), maximum=180)
        summary = _normalized_text(raw_item.get("summary"), maximum=600)
        if title is None or summary is None:
            continue
        if URLISH_RE.search(title) or URLISH_RE.search(summary):
            continue
        parsed = urllib.parse.urlsplit(url)
        html = html_loader(parsed.path)
        if (
            html is None
            or not HTML_DOCUMENT_RE.search(html)
            or REDIRECT_RE.search(html)
        ):
            continue
        seen.add(url)
        selected.append(Resource(title=title, url=url, summary=summary))
        if len(selected) == MAX_RESOURCES:
            break
    if not selected:
        raise PublisherError("feed.json contains no eligible practical resources")
    return tuple(selected)


def content_digest(resources: tuple[Resource, ...]) -> str:
    material = [
        {"title": item.title, "url": item.url, "summary": item.summary}
        for item in resources
    ]
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _markdown_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in "`*_{}[]<>()#+-.!|":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("@", "&#64;")


def render_digest(resources: tuple[Resource, ...], source_sha: str) -> RenderedDigest:
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise PublisherError("Source SHA must be exactly 40 lowercase hexadecimal characters")
    if not 1 <= len(resources) <= MAX_RESOURCES:
        raise PublisherError("The digest must contain between one and three resources")
    digest = content_digest(resources)
    lines = [
        f"# {DISCUSSION_TITLE}",
        "",
        (
            "**First-party publisher notice:** Lumi Studio maintains this official "
            "resource index for its own iOS app guide."
        ),
        "",
        (
            "This is publisher-authored material, not an independent review, "
            "comparison, ranking, endorsement, or measured popularity claim."
        ),
        "",
        (
            "The locked announcement is maintained by automation only when the "
            "selected practical content materially changes, and never more often "
            "than once every 28 days. It does not accept comments or mentions."
        ),
        "",
        "## Current practical resources",
        "",
    ]
    for index, resource in enumerate(resources, start=1):
        lines.extend(
            (
                f"{index}. [{_markdown_text(resource.title)}]({resource.url})",
                f"   {_markdown_text(resource.summary)}",
            )
        )
    lines.extend(
        (
            "",
            (
                "For product help, use the relevant app's in-app support route or "
                "the repository's SUPPORT document."
            ),
            "",
            (
                f"<!-- {SENTINEL}; version={FORMAT_VERSION}; "
                f"digest=sha256:{digest}; source={source_sha} -->"
            ),
        )
    )
    body = "\n".join(lines) + "\n"
    if body.count("https://") != len(resources) or len(resources) > MAX_RESOURCES:
        raise PublisherError("Rendered body exceeded the external-link allowlist")
    if "@" in body:
        raise PublisherError("Rendered body contained a prohibited mention marker")
    metadata = parse_metadata(body)
    if metadata.digest != digest or metadata.source_sha != source_sha:
        raise PublisherError("Rendered metadata did not round-trip exactly")
    return RenderedDigest(
        resources=resources,
        digest=digest,
        source_sha=source_sha,
        body=body,
    )


def parse_metadata(body: object) -> Metadata:
    if not isinstance(body, str) or body.count(SENTINEL) != 1:
        raise PublisherError("Managed Discussion sentinel is missing or duplicated")
    match = METADATA_RE.search(body)
    if match is None:
        raise PublisherError("Managed Discussion metadata is malformed")
    metadata = Metadata(
        version=int(match.group(1)),
        digest=match.group(2),
        source_sha=match.group(3),
    )
    if metadata.version != FORMAT_VERSION:
        raise PublisherError(
            f"Unsupported managed Discussion format version: {metadata.version}"
        )
    return metadata


def load_feed(path: pathlib.Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublisherError(f"Unable to load feed.json: {error}") from error
    if not isinstance(payload, dict):
        raise PublisherError("feed.json root must be an object")
    return payload


class GraphQLClient:
    """Single-attempt GitHub GraphQL client."""

    def __init__(
        self,
        token: str,
        *,
        opener: Callable[..., Any] | None = None,
        timeout: int = GRAPHQL_TIMEOUT,
    ) -> None:
        if not token.strip():
            raise PublisherError("GITHUB_TOKEN is required")
        self._token = token
        self._opener = opener
        self._timeout = timeout

    def execute(
        self,
        query: str,
        variables: Mapping[str, object],
        *,
        mutation: bool,
        mutation_reserve: int = 0,
    ) -> dict[str, Any]:
        if mutation:
            if (
                not isinstance(mutation_reserve, int)
                or isinstance(mutation_reserve, bool)
                or mutation_reserve < 0
            ):
                raise PublisherError("Mutation rate-limit reserve was invalid")
            limit_data = self._execute_once(
                RATE_LIMIT_QUERY,
                {},
                mutation=False,
                require_rate_limit=True,
            )
            remaining = limit_data["rateLimit"]["remaining"]
            required = MIN_RATE_LIMIT + 1 + mutation_reserve
            if remaining < required:
                raise PublisherError(
                    "Mutation was stopped before execution because the rate-limit "
                    f"reserve was too low ({remaining} < {required})"
                )
        return self._execute_once(
            query,
            variables,
            mutation=mutation,
            require_rate_limit=not mutation,
        )

    def _execute_once(
        self,
        query: str,
        variables: Mapping[str, object],
        *,
        mutation: bool,
        require_rate_limit: bool,
    ) -> dict[str, Any]:
        encoded = json.dumps(
            {"query": query, "variables": dict(variables)},
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            GRAPHQL_URL,
            data=encoded,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "User-Agent": f"{NAME_WITH_OWNER}-discussion-digest/1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        opener = self._opener or urllib.request.urlopen
        try:
            with opener(request, timeout=self._timeout) as response:
                status = getattr(response, "status", 200)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout) as error:
            if mutation:
                raise MutationUncertainError(
                    f"Mutation transport failed; outcome is uncertain and was not retried: {error}"
                ) from error
            raise PublisherError(f"GraphQL transport failed: {error}") from error
        if status != 200:
            message = f"GraphQL returned unexpected HTTP status {status}"
            if mutation:
                raise MutationUncertainError(f"{message}; mutation was not retried")
            raise PublisherError(message)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PublisherError("GraphQL response exceeded the fail-closed size limit")
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            if mutation:
                raise MutationUncertainError(
                    "Mutation returned invalid JSON; outcome is uncertain and was not retried"
                ) from error
            raise PublisherError("GraphQL returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise PublisherError("GraphQL response root was not an object")
        if "errors" in payload:
            raise PublisherError(f"GraphQL returned errors: {payload['errors']!r}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PublisherError("GraphQL data was null or malformed")
        if require_rate_limit:
            rate_limit = data.get("rateLimit")
            if not isinstance(rate_limit, dict):
                raise PublisherError("GraphQL rateLimit data was missing")
            remaining = rate_limit.get("remaining")
            if (
                not isinstance(remaining, int)
                or isinstance(remaining, bool)
                or remaining < MIN_RATE_LIMIT
            ):
                raise PublisherError(
                    "GraphQL rate limit below required floor "
                    f"({remaining!r} < {MIN_RATE_LIMIT})"
                )
        return data


def _connection_nodes(connection: object, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(connection, dict):
        raise PublisherError(f"{label} connection was missing")
    total = connection.get("totalCount")
    nodes = connection.get("nodes")
    page_info = connection.get("pageInfo")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or total < 0
        or not isinstance(nodes, list)
        or not isinstance(page_info, dict)
        or page_info.get("hasNextPage") is not False
        or total != len(nodes)
        or any(not isinstance(node, dict) for node in nodes)
    ):
        raise PublisherError(f"{label} connection was incomplete or paginated")
    return nodes


def _valid_node_id(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or CONTROL_RE.search(value):
        raise PublisherError(f"{label} node ID was invalid")
    return value


def _validate_category(node: object, expected_id: str) -> None:
    if not isinstance(node, dict) or (
        node.get("id"),
        node.get("name"),
        node.get("slug"),
        node.get("isAnswerable"),
    ) != (expected_id, CATEGORY_NAME, CATEGORY_SLUG, False):
        raise PublisherError("Managed Discussion category left the exact allowlist")


def load_repository_state(client: GraphQLClient) -> RepositoryState:
    data = client.execute(
        REPOSITORY_QUERY,
        {"owner": OWNER, "name": REPOSITORY},
        mutation=False,
    )
    repository = data.get("repository")
    if not isinstance(repository, dict):
        raise PublisherError("Allowlisted repository was not found")
    if (
        repository.get("nameWithOwner") != NAME_WITH_OWNER
        or repository.get("visibility") != "PUBLIC"
        or repository.get("isPrivate") is not False
        or repository.get("isArchived") is not False
        or repository.get("isDisabled") is not False
        or repository.get("hasDiscussionsEnabled") is not True
    ):
        raise PublisherError(
            "Repository identity, public state, or Discussions state is unsafe: "
            f"nameWithOwner={repository.get('nameWithOwner')!r}, "
            f"visibility={repository.get('visibility')!r}, "
            f"isPrivate={repository.get('isPrivate')!r}, "
            f"isArchived={repository.get('isArchived')!r}, "
            f"isDisabled={repository.get('isDisabled')!r}, "
            f"hasDiscussionsEnabled={repository.get('hasDiscussionsEnabled')!r}"
        )
    permission = repository.get("viewerPermission")
    # Granular GITHUB_TOKEN permissions can make this legacy aggregate field null.
    # Existing posts still require viewerCanUpdate; bootstrap is authorized by its
    # single-attempt mutation and fails before creating anything if denied.
    if permission is not None and permission not in {
        "READ",
        "TRIAGE",
        "WRITE",
        "MAINTAIN",
        "ADMIN",
    }:
        raise PublisherError(
            f"Repository viewerPermission was abnormal: {permission!r}"
        )
    repository_id = _valid_node_id(repository.get("id"), label="Repository")
    categories = _connection_nodes(
        repository.get("discussionCategories"),
        label="Discussion categories",
    )
    announcements = [
        node
        for node in categories
        if node.get("name") == CATEGORY_NAME and node.get("slug") == CATEGORY_SLUG
    ]
    if len(announcements) != 1 or announcements[0].get("isAnswerable") is not False:
        raise PublisherError("Exactly one non-answerable Announcements category is required")
    category_id = _valid_node_id(
        announcements[0].get("id"),
        label="Announcements category",
    )

    discussions = _connection_nodes(
        repository.get("discussions"),
        label="Discussions",
    )
    managed: list[dict[str, Any]] = []
    for discussion in discussions:
        title = discussion.get("title")
        body = discussion.get("body")
        has_title = title == DISCUSSION_TITLE
        has_sentinel = isinstance(body, str) and SENTINEL in body
        if not (has_title or has_sentinel):
            continue
        if not has_title or not has_sentinel:
            raise PublisherError(
                "A Discussion partially matched the managed title/sentinel allowlist"
            )
        parse_metadata(body)
        _validate_category(discussion.get("category"), category_id)
        managed.append(discussion)
    if len(managed) > 1:
        raise PublisherError("More than one managed Discussion exists")
    return RepositoryState(
        repository_id=repository_id,
        category_id=category_id,
        managed=tuple(managed),
    )


def _discussion_url(value: object) -> str:
    if not isinstance(value, str):
        raise PublisherError("Managed Discussion URL was missing")
    parsed = urllib.parse.urlsplit(value)
    expected_prefix = f"/{OWNER}/{REPOSITORY}/discussions/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or not parsed.path.startswith(expected_prefix)
        or not parsed.path.removeprefix(expected_prefix).isdigit()
        or parsed.query
        or parsed.fragment
    ):
        raise PublisherError("Managed Discussion URL left the exact repository allowlist")
    return value


def _comment_count(discussion: Mapping[str, object]) -> int:
    comments = discussion.get("comments")
    if not isinstance(comments, dict):
        raise PublisherError("Managed Discussion comment count was missing")
    total = comments.get("totalCount")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise PublisherError("Managed Discussion comment count was malformed")
    return total


def _author_login(discussion: Mapping[str, object]) -> str:
    author = discussion.get("author")
    login = author.get("login") if isinstance(author, dict) else None
    if login not in APPROVED_AUTHORS:
        raise PublisherError(f"Managed Discussion author is not approved: {login!r}")
    return str(login)


def _validate_existing(
    discussion: Mapping[str, object],
    *,
    category_id: str,
    require_locked: bool,
    require_viewer_update: bool = True,
) -> Metadata:
    _valid_node_id(discussion.get("id"), label="Discussion")
    if discussion.get("title") != DISCUSSION_TITLE:
        raise PublisherError("Managed Discussion title changed")
    _validate_category(discussion.get("category"), category_id)
    _discussion_url(discussion.get("url"))
    _author_login(discussion)
    viewer_can_update = discussion.get("viewerCanUpdate")
    if require_viewer_update and viewer_can_update is not True:
        raise PublisherError("Workflow viewer cannot update the managed Discussion")
    if (
        not require_viewer_update
        and viewer_can_update is not True
        and viewer_can_update is not False
    ):
        raise PublisherError("Managed Discussion viewerCanUpdate was malformed")
    if discussion.get("locked") is not require_locked:
        expected = "locked" if require_locked else "unlocked"
        raise PublisherError(f"Managed Discussion is not {expected}")
    if _comment_count(discussion) != 0:
        raise PublisherError("Managed Discussion must not contain comments")
    return parse_metadata(discussion.get("body"))


def _parse_updated_at(value: object) -> dt.datetime:
    if not isinstance(value, str):
        raise PublisherError("Managed Discussion updatedAt was missing")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PublisherError("Managed Discussion updatedAt was malformed") from error
    if parsed.tzinfo is None:
        raise PublisherError("Managed Discussion updatedAt lacked a timezone")
    return parsed.astimezone(dt.timezone.utc)


def _create_discussion(
    client: GraphQLClient,
    state: RepositoryState,
    rendered: RenderedDigest,
) -> dict[str, Any]:
    data = client.execute(
        CREATE_DISCUSSION_MUTATION,
        {
            "repositoryId": state.repository_id,
            "categoryId": state.category_id,
            "title": DISCUSSION_TITLE,
            "body": rendered.body,
        },
        mutation=True,
        mutation_reserve=2,
    )
    payload = data.get("createDiscussion")
    discussion = payload.get("discussion") if isinstance(payload, dict) else None
    if not isinstance(discussion, dict):
        raise PublisherError("createDiscussion returned null or malformed data")
    if discussion.get("body") != rendered.body:
        raise PublisherError("createDiscussion did not preserve the exact managed body")
    _validate_existing(
        discussion,
        category_id=state.category_id,
        require_locked=False,
        require_viewer_update=False,
    )
    return discussion


def _lock_discussion(client: GraphQLClient, discussion_id: str) -> None:
    data = client.execute(
        LOCK_DISCUSSION_MUTATION,
        {"id": discussion_id},
        mutation=True,
    )
    payload = data.get("lockLockable")
    locked = payload.get("lockedRecord") if isinstance(payload, dict) else None
    if (
        not isinstance(locked, dict)
        or locked.get("id") != discussion_id
        or locked.get("locked") is not True
    ):
        raise PublisherError("lockLockable did not confirm the exact Discussion lock")
    _discussion_url(locked.get("url"))


def _update_discussion(
    client: GraphQLClient,
    discussion_id: str,
    rendered: RenderedDigest,
    category_id: str,
) -> None:
    data = client.execute(
        UPDATE_DISCUSSION_MUTATION,
        {"id": discussion_id, "body": rendered.body},
        mutation=True,
    )
    payload = data.get("updateDiscussion")
    discussion = payload.get("discussion") if isinstance(payload, dict) else None
    if not isinstance(discussion, dict) or discussion.get("body") != rendered.body:
        raise PublisherError("updateDiscussion returned null or an unexpected body")
    _validate_existing(
        discussion,
        category_id=category_id,
        require_locked=True,
    )


def _verify_rendered_discussion(
    discussion: Mapping[str, object],
    *,
    rendered: RenderedDigest,
    category_id: str,
    require_viewer_update: bool = True,
) -> str:
    metadata = _validate_existing(
        discussion,
        category_id=category_id,
        require_locked=True,
        require_viewer_update=require_viewer_update,
    )
    if (
        metadata.digest != rendered.digest
        or metadata.source_sha != rendered.source_sha
        or discussion.get("body") != rendered.body
    ):
        raise PublisherError("Managed Discussion post-mutation verification failed")
    return _discussion_url(discussion.get("url"))


def _lock_failure_details(client: GraphQLClient, original: BaseException) -> PublisherError:
    try:
        state = load_repository_state(client)
        if len(state.managed) == 1:
            discussion = state.managed[0]
            return PublisherError(
                "Lock mutation failed and was not retried; "
                f"managed Discussion is locked={discussion.get('locked')!r}, "
                f"url={discussion.get('url')!r}. Original error: {original}"
            )
        return PublisherError(
            "Lock mutation failed and was not retried; follow-up found "
            f"{len(state.managed)} managed Discussions. Original error: {original}"
        )
    except PublisherError as inspection_error:
        return PublisherError(
            "Lock mutation failed and was not retried; follow-up inspection also "
            f"failed ({inspection_error}). Original error: {original}"
        )


def publish(
    client: GraphQLClient,
    rendered: RenderedDigest,
    *,
    bootstrap: bool,
    now: dt.datetime | None = None,
) -> PublicationResult:
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise PublisherError("Publisher clock must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)
    state = load_repository_state(client)

    if not state.managed:
        if not bootstrap:
            raise PublisherError(
                "Managed Discussion is missing; scheduled/general runs cannot bootstrap"
            )
        created = _create_discussion(client, state, rendered)
        discussion_id = _valid_node_id(created.get("id"), label="Created Discussion")
        try:
            _lock_discussion(client, discussion_id)
        except PublisherError as error:
            raise _lock_failure_details(client, error) from error
        verified = load_repository_state(client)
        if len(verified.managed) != 1:
            raise PublisherError("Bootstrap verification did not find exactly one Discussion")
        url = _verify_rendered_discussion(
            verified.managed[0],
            rendered=rendered,
            category_id=verified.category_id,
            require_viewer_update=False,
        )
        return PublicationResult(
            action="created-and-locked",
            digest=rendered.digest,
            url=url,
            reason="explicit workflow_dispatch bootstrap",
        )

    discussion = state.managed[0]
    if discussion.get("locked") is False and bootstrap:
        metadata = _validate_existing(
            discussion,
            category_id=state.category_id,
            require_locked=False,
            require_viewer_update=False,
        )
        expected = render_digest(rendered.resources, metadata.source_sha)
        if metadata.digest != rendered.digest or discussion.get("body") != expected.body:
            raise PublisherError(
                "Explicit bootstrap cannot lock an existing Discussion with different content"
            )
        discussion_id = _valid_node_id(discussion.get("id"), label="Discussion")
        try:
            _lock_discussion(client, discussion_id)
        except PublisherError as error:
            raise _lock_failure_details(client, error) from error
        verified = load_repository_state(client)
        if len(verified.managed) != 1:
            raise PublisherError("Lock recovery did not find exactly one Discussion")
        expected_locked = render_digest(rendered.resources, metadata.source_sha)
        url = _verify_rendered_discussion(
            verified.managed[0],
            rendered=expected_locked,
            category_id=verified.category_id,
            require_viewer_update=False,
        )
        return PublicationResult(
            action="locked-existing",
            digest=rendered.digest,
            url=url,
            reason="explicit workflow_dispatch lock recovery",
        )

    metadata = _validate_existing(
        discussion,
        category_id=state.category_id,
        require_locked=True,
        require_viewer_update=False,
    )
    url = _discussion_url(discussion.get("url"))
    if metadata.digest == rendered.digest:
        expected = render_digest(rendered.resources, metadata.source_sha)
        if discussion.get("body") != expected.body:
            raise PublisherError(
                "Stored digest matched, but the managed Discussion body was not canonical"
            )
        return PublicationResult(
            action="no-op",
            digest=rendered.digest,
            url=url,
            reason="substantive digest is unchanged",
        )

    updated_at = _parse_updated_at(discussion.get("updatedAt"))
    elapsed = now - updated_at
    if elapsed < dt.timedelta(0):
        raise PublisherError("Managed Discussion updatedAt is in the future")
    if elapsed < MIN_UPDATE_INTERVAL:
        return PublicationResult(
            action="deferred",
            digest=rendered.digest,
            url=url,
            reason=(
                "substantive digest changed, but the 28-day minimum update interval "
                "has not elapsed"
            ),
        )

    _validate_existing(
        discussion,
        category_id=state.category_id,
        require_locked=True,
    )
    discussion_id = _valid_node_id(discussion.get("id"), label="Discussion")
    _update_discussion(
        client,
        discussion_id,
        rendered,
        state.category_id,
    )
    verified = load_repository_state(client)
    if len(verified.managed) != 1:
        raise PublisherError("Update verification did not find exactly one Discussion")
    verified_url = _verify_rendered_discussion(
        verified.managed[0],
        rendered=rendered,
        category_id=verified.category_id,
    )
    return PublicationResult(
        action="updated",
        digest=rendered.digest,
        url=verified_url,
        reason="substantive digest changed after the 28-day interval",
    )


def parse_bootstrap(event_name: str, raw_value: str) -> bool:
    if raw_value not in {"true", "false"}:
        raise PublisherError("Bootstrap input must be an explicit boolean")
    requested = raw_value == "true"
    if requested and event_name != "workflow_dispatch":
        raise PublisherError("Only workflow_dispatch may request bootstrap")
    if event_name not in {"schedule", "workflow_dispatch"}:
        raise PublisherError(f"Unsupported workflow event: {event_name!r}")
    return requested


def source_sha(repository_root: pathlib.Path) -> str:
    candidate = os.environ.get("GITHUB_SHA", "").strip().lower()
    if not candidate:
        try:
            completed = subprocess.run(
                ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise PublisherError(f"Unable to determine source SHA: {error}") from error
        candidate = completed.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise PublisherError("GITHUB_SHA/source SHA was not a full commit hash")
    return candidate


def build_rendered_digest(repository_root: pathlib.Path) -> RenderedDigest:
    feed = load_feed(repository_root / "feed.json")
    resources = select_resources(feed, repository_root=repository_root)
    return render_digest(resources, source_sha(repository_root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate locally without calling GitHub",
    )
    args = parser.parse_args(argv)
    repository_root = pathlib.Path(__file__).resolve().parents[2]
    try:
        rendered = build_rendered_digest(repository_root)
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "action": "dry-run",
                        "digest": rendered.digest,
                        "resource_count": len(rendered.resources),
                        "resources": [item.url for item in rendered.resources],
                        "source_sha": rendered.source_sha,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if os.environ.get("GITHUB_REPOSITORY") != NAME_WITH_OWNER:
            raise PublisherError("GITHUB_REPOSITORY left the exact allowlist")
        bootstrap = parse_bootstrap(
            os.environ.get("GITHUB_EVENT_NAME", ""),
            os.environ.get("DISCUSSION_BOOTSTRAP", ""),
        )
        client = GraphQLClient(os.environ.get("GITHUB_TOKEN", ""))
        result = publish(client, rendered, bootstrap=bootstrap)
        print(
            json.dumps(
                dataclasses.asdict(result),
                sort_keys=True,
            )
        )
        return 0
    except PublisherError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
