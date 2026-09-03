#!/usr/bin/env python3
"""Keep sitemap lastmod dates tied to real content changes."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
from site_config import ORIGIN_HOST, PUBLIC_SITE  # noqa: E402


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = PUBLIC_SITE
STATE_RELATIVE_PATH = Path("_engine/geo/sitemap_lastmod_state.json")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
MAX_CLOCK_SKEW = timedelta(minutes=5)
DATE_MODIFIED_RE = re.compile(
    r'"dateModified"\s*:\s*"(?P<value>\d{4}-\d{2}-\d{2})"'
)
PUBLISHER_VISUAL_SITEMAP = Path("sitemap_intent_visuals.xml")
PUBLISHER_VISUAL_MANIFEST = Path(
    "data/lumi-studio-publisher-intent-visuals.json"
)
PUBLISHER_VISUAL_SOURCE_DATASET = Path(
    "data/lumi-studio-publisher-search-intent-catalog.json"
)
PUBLISHER_VISUAL_LOCALE_COUNT = 50
PUBLISHER_VISUAL_GALLERY_COUNT = PUBLISHER_VISUAL_LOCALE_COUNT + 1
URL_BLOCK_RE = re.compile(
    r"(?P<open><url(?:\s[^>]*)?>)(?P<body>.*?)(?P<close></url>)",
    flags=re.DOTALL,
)
SITEMAP_BLOCK_RE = re.compile(
    r"(?P<open><sitemap(?:\s[^>]*)?>)(?P<body>.*?)(?P<close></sitemap>)",
    flags=re.DOTALL,
)
LOC_RE = re.compile(r"<loc>(?P<value>.*?)</loc>", flags=re.DOTALL)
LASTMOD_RE = re.compile(
    r"<lastmod>(?P<value>.*?)</lastmod>",
    flags=re.DOTALL,
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _valid_date(value: Any, *, today: str | None = None) -> bool:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return today is None or parsed <= date.fromisoformat(today)


def _utc_instant(value: datetime | str, *, label: str) -> datetime:
    if isinstance(value, str):
        if value != value.strip():
            raise ValueError(f"Invalid {label}: {value!r}")
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as error:
            raise ValueError(f"Invalid {label}: {value!r}") from error
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError(f"Invalid {label}: {value!r}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a UTC offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def _validation_reference(
    workflow_started_at: datetime | str | None,
    *,
    validation_time: datetime | str | None = None,
) -> datetime:
    """Use max(trusted workflow start, current validation instant), in UTC."""
    current = (
        _utc_instant(validation_time, label="validation time")
        if validation_time is not None
        else datetime.now(timezone.utc)
    )
    if workflow_started_at is None:
        return current
    started = _utc_instant(
        workflow_started_at,
        label="workflow start time",
    )
    if started - current > MAX_CLOCK_SKEW:
        raise ValueError(
            "Workflow start time exceeds clock-skew contract: "
            f"{started.isoformat()} > {current.isoformat()} + "
            f"{int(MAX_CLOCK_SKEW.total_seconds())}s"
        )
    return max(started, current)


def _sha256(path: Path) -> str:
    with path.open("rb") as source:
        if hasattr(hashlib, "file_digest"):
            return hashlib.file_digest(source, "sha256").hexdigest()
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()


def _write_if_changed(path: Path, content: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _sitemap_paths(pages: Path) -> list[Path]:
    paths = {
        path
        for path in (
            *pages.glob("sitemap*.xml"),
            *pages.glob("*/sitemap.xml"),
        )
        if path.name != "sitemap_index.xml"
    }
    return sorted(paths)


def _xml_blocks(
    path: Path,
    expected_root: str,
    child_name: str,
    pattern: re.Pattern[str],
) -> tuple[str, list[re.Match[str]]]:
    source = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise ValueError(f"Invalid sitemap XML in {path}: {error}") from error
    if _local_name(root.tag) != expected_root:
        raise ValueError(
            f"Unexpected sitemap root in {path}: {_local_name(root.tag)}"
        )
    xml_children = [
        child for child in root if _local_name(child.tag) == child_name
    ]
    blocks = list(pattern.finditer(source))
    if len(blocks) != len(xml_children):
        raise ValueError(
            f"Sitemap block count mismatch in {path}: "
            f"XML={len(xml_children)} text={len(blocks)}"
        )
    return source, blocks


def _block_location(path: Path, body: str) -> str:
    matches = list(LOC_RE.finditer(body))
    if len(matches) != 1:
        raise ValueError(
            f"Sitemap entry must contain one loc in {path}: {len(matches)}"
        )
    value = html.unescape(matches[0].group("value").strip())
    if not value or len(value) > 2048 or any(char.isspace() for char in value):
        raise ValueError(f"Invalid sitemap loc in {path}: {value!r}")
    return value


def _with_lastmod(path: Path, body: str, lastmod: str) -> str:
    if not _valid_date(lastmod):
        raise ValueError(f"Invalid lastmod for {path}: {lastmod}")
    matches = list(LASTMOD_RE.finditer(body))
    if len(matches) > 1:
        raise ValueError(f"Duplicate lastmod in sitemap entry: {path}")
    if matches:
        match = matches[0]
        return (
            body[: match.start("value")]
            + lastmod
            + body[match.end("value") :]
        )
    loc_matches = list(LOC_RE.finditer(body))
    if len(loc_matches) != 1:
        raise ValueError(f"Cannot insert lastmod without one loc: {path}")
    loc = loc_matches[0]
    return (
        body[: loc.end()]
        + f"<lastmod>{lastmod}</lastmod>"
        + body[loc.end() :]
    )


def _render_blocks(
    source: str,
    blocks: list[re.Match[str]],
    replacements: dict[int, str],
) -> str:
    parts: list[str] = []
    cursor = 0
    for index, block in enumerate(blocks):
        parts.append(source[cursor : block.start()])
        body = replacements.get(index, block.group("body"))
        parts.extend((block.group("open"), body, block.group("close")))
        cursor = block.end()
    parts.append(source[cursor:])
    return "".join(parts)


def _site_relative(url: str, site: str) -> str | None:
    parsed = urlsplit(url)
    expected = urlsplit(site.rstrip("/"))
    if (
        parsed.scheme != "https"
        or parsed.query
        or parsed.fragment
        or len(url) > 2048
        or any(char.isspace() for char in url)
    ):
        raise ValueError(f"Invalid sitemap URL: {url}")
    if parsed.netloc != expected.netloc:
        # The Pages origin serves the same bytes under a different name, and a
        # few owned sitemaps still point at root-level resources there (the
        # ResourceSync source description, for one). Those are ours but sit
        # outside this site's path, so they are preserved untouched -- the same
        # answer this function already gives for an in-host, out-of-path URL.
        # Anything on a host we do not own is still a hard failure.
        if parsed.netloc == ORIGIN_HOST:
            return None
        raise ValueError(f"Sitemap URL uses an unowned host: {url}")
    base_path = expected.path.rstrip("/")
    if parsed.path == base_path or parsed.path == f"{base_path}/":
        return ""
    prefix = f"{base_path}/"
    if not parsed.path.startswith(prefix):
        return None
    return unquote(parsed.path[len(prefix) :])


@lru_cache(maxsize=None)
def _resolved_directory(path: Path) -> Path:
    return path.resolve()


def _owned_target(url: str, pages: Path, site: str) -> Path | None:
    relative = _site_relative(url, site)
    if relative is None:
        return None
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Sitemap URL escapes Pages root: {url}")
    if not relative:
        candidates = [pages / "index.html"]
    elif relative.endswith("/"):
        candidates = [pages / relative / "index.html"]
    else:
        candidates = [pages / relative]
        if not Path(relative).suffix:
            candidates.append(pages / relative / "index.html")
    pages_root = pages
    resolved: list[Path] = []
    for candidate in candidates:
        parent = _resolved_directory(candidate.parent)
        target = parent / candidate.name
        if target.is_symlink():
            target = target.resolve()
        try:
            target.relative_to(pages_root)
        except ValueError as error:
            raise ValueError(f"Sitemap URL escapes Pages root: {url}") from error
        if target.is_file() and target.stat().st_size > 0:
            resolved.append(target)
    if len(resolved) != 1:
        raise ValueError(
            f"Sitemap URL must map to exactly one non-empty file: "
            f"{url} ({len(resolved)})"
        )
    return resolved[0]


def _relative_path(path: Path, pages: Path) -> str:
    return path.relative_to(pages).as_posix()


def _run_git(pages: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(pages), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Git metadata command failed: {' '.join(args)}\n"
            f"{result.stderr[-1000:]}"
        )
    return result.stdout


def git_dirty_paths(pages: Path) -> set[str]:
    output = _run_git(
        pages,
        [
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--no-renames",
        ],
    )
    dirty: set[str] = set()
    for record in output.split("\0"):
        if len(record) >= 4:
            dirty.add(record[3:])
    return dirty


def git_history_dates(
    pages: Path,
    wanted: set[str],
    *,
    validation_time: datetime | str | None = None,
) -> dict[str, str]:
    if not wanted:
        return {}
    validation = (
        _utc_instant(validation_time, label="Git validation time")
        if validation_time is not None
        else datetime.now(timezone.utc)
    )
    latest_allowed = validation + MAX_CLOCK_SKEW
    pathspecs = sorted(wanted)
    if len(pathspecs) > 512 or sum(map(len, pathspecs)) > 100000:
        pathspecs = ["."]
    output = _run_git(
        pages,
        [
            "-c",
            "core.quotePath=false",
            "log",
            "--format=@@%ct",
            "--name-only",
            "--no-renames",
            "--",
            *pathspecs,
        ],
    )
    dates: dict[str, str] = {}
    commit_date: str | None = None
    for line in output.splitlines():
        if line.startswith("@@"):
            candidate = line[2:].strip()
            if not re.fullmatch(r"\d+", candidate):
                raise ValueError(
                    f"Malformed Git commit timestamp: {candidate!r}"
                )
            try:
                commit_time = datetime.fromtimestamp(
                    int(candidate),
                    timezone.utc,
                )
            except (OSError, OverflowError, ValueError) as error:
                raise ValueError(
                    f"Malformed Git commit timestamp: {candidate!r}"
                ) from error
            if commit_time > latest_allowed:
                raise ValueError(
                    "Git commit timestamp exceeds clock-skew contract: "
                    f"{commit_time.isoformat()} > {validation.isoformat()} + "
                    f"{int(MAX_CLOCK_SKEW.total_seconds())}s"
                )
            commit_date = commit_time.date().isoformat()
            continue
        path = line.strip()
        if commit_date and path in wanted and path not in dates:
            dates[path] = commit_date
            if len(dates) == len(wanted):
                break
    return dates


def _load_state(path: Path, max_date: str) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "urls": {}, "sitemaps": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid sitemap lastmod state: {error}") from error
    if (
        not isinstance(state, dict)
        or state.get("version") != 1
        or not isinstance(state.get("urls"), dict)
        or not isinstance(state.get("sitemaps"), dict)
    ):
        raise ValueError("Invalid sitemap lastmod state structure")
    for section in ("urls", "sitemaps"):
        for url, record in state[section].items():
            if (
                not isinstance(url, str)
                or not isinstance(record, dict)
                or not isinstance(record.get("path"), str)
                or not SHA256_RE.fullmatch(str(record.get("sha256", "")))
                or not _valid_date(record.get("lastmod"), today=max_date)
            ):
                raise ValueError(
                    f"Invalid sitemap lastmod state record: {section}/{url}"
                )
    return state


def _validate_publisher_visual_sitemap(
    sitemap: Path,
    pages: Path,
    locations: list[str],
    targets: dict[str, Path],
    url_records: dict[str, dict[str, str]],
    site: str,
    max_date: str,
) -> None:
    if _relative_path(sitemap, pages) != PUBLISHER_VISUAL_SITEMAP.as_posix():
        return
    manifest_path = pages / PUBLISHER_VISUAL_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Invalid publisher visual manifest: {error}"
        ) from error
    if not isinstance(manifest, dict):
        raise ValueError("Invalid publisher visual manifest contract")
    modified = manifest.get("dateModified")
    records = manifest.get("records")
    app_count = manifest.get("app_count")
    locale_count = manifest.get("locale_count")
    image_count = manifest.get("image_count")
    gallery_count = manifest.get("gallery_count")
    galleries = manifest.get("galleries")
    source_path = pages / PUBLISHER_VISUAL_SOURCE_DATASET
    if (
        not _valid_date(modified, today=max_date)
        or manifest.get("url") != f"{site}/visuals/"
        or manifest.get("source_dataset")
        != f"{site}/{PUBLISHER_VISUAL_SOURCE_DATASET.as_posix()}"
        or not source_path.is_file()
        or not SHA256_RE.fullmatch(str(manifest.get("source_sha256", "")))
        or not SHA256_RE.fullmatch(
            str(manifest.get("content_digest", ""))
        )
        or not SHA256_RE.fullmatch(
            str(manifest.get("generation_digest", ""))
        )
        or not isinstance(records, list)
        or not isinstance(app_count, int)
        or app_count <= 0
        or not isinstance(locale_count, int)
        or locale_count != PUBLISHER_VISUAL_LOCALE_COUNT
        or not isinstance(image_count, int)
        or image_count != len(records)
        or image_count != app_count * locale_count
        or not isinstance(gallery_count, int)
        or gallery_count != PUBLISHER_VISUAL_GALLERY_COUNT
        or gallery_count != locale_count + 1
        or gallery_count != len(locations)
        or not isinstance(galleries, list)
        or gallery_count != len(galleries)
        or len(set(locations)) != len(locations)
    ):
        raise ValueError("Invalid publisher visual manifest contract")
    if _sha256(source_path) != manifest["source_sha256"]:
        raise ValueError(
            "Publisher visual source digest does not match manifest"
        )

    galleries_by_locale: dict[str, dict[str, str]] = {}
    galleries_by_url: dict[str, dict[str, str]] = {}
    for gallery in galleries:
        if not isinstance(gallery, dict):
            raise ValueError("Invalid publisher visual gallery contract")
        locale = gallery.get("locale")
        gallery_url = gallery.get("gallery_url")
        digest = gallery.get("sha256")
        if (
            not isinstance(locale, str)
            or not locale
            or not isinstance(gallery_url, str)
            or not gallery_url
            or not SHA256_RE.fullmatch(str(digest or ""))
            or locale in galleries_by_locale
            or gallery_url in galleries_by_url
        ):
            raise ValueError("Invalid publisher visual gallery contract")
        normalized = {
            "locale": locale,
            "gallery_url": gallery_url,
            "sha256": str(digest),
        }
        galleries_by_locale[locale] = normalized
        galleries_by_url[gallery_url] = normalized

    root_gallery = galleries_by_locale.get("en")
    localized_locales = set(galleries_by_locale) - {"en"}
    if (
        root_gallery is None
        or root_gallery["gallery_url"] != f"{site}/visuals/"
        or len(localized_locales) != locale_count
        or set(galleries_by_url) != set(locations)
    ):
        raise ValueError("Invalid publisher visual gallery identity")

    record_counts = {locale: 0 for locale in localized_locales}
    record_pairs: set[tuple[str, str]] = set()
    image_urls: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Invalid publisher visual manifest record")
        locale = item.get("locale")
        app_key = item.get("app_key")
        gallery_url = item.get("gallery_url")
        image_url = item.get("image_url")
        image_target: Path | None = None
        if isinstance(image_url, str) and image_url:
            try:
                image_target = _owned_target(image_url, pages, site)
            except ValueError as error:
                raise ValueError(
                    "Invalid publisher visual manifest record"
                ) from error
        required_strings = (
            locale,
            app_key,
            item.get("app_store_id"),
            gallery_url,
            image_url,
            item.get("canonical_guide_url"),
            item.get("app_store_url"),
        )
        if (
            any(
                not isinstance(value, str) or not value
                for value in required_strings
            )
            or locale not in localized_locales
            or gallery_url
            != galleries_by_locale[str(locale)]["gallery_url"]
            or not SHA256_RE.fullmatch(str(item.get("sha256", "")))
            or image_target is None
            or _relative_path(image_target, pages)
            != f"visuals/{locale}/{app_key}.svg"
            or _sha256(image_target) != item["sha256"]
            or (str(locale), str(app_key)) in record_pairs
            or str(image_url) in image_urls
        ):
            raise ValueError("Invalid publisher visual manifest record")
        record_counts[str(locale)] += 1
        record_pairs.add((str(locale), str(app_key)))
        image_urls.add(str(image_url))
    if (
        set(record_counts) != localized_locales
        or any(count != app_count for count in record_counts.values())
        or len(record_pairs) != image_count
        or len(image_urls) != image_count
    ):
        raise ValueError("Invalid publisher visual manifest record coverage")

    for location in locations:
        target = targets.get(location)
        record = url_records.get(location)
        if target is None or record is None:
            raise ValueError(
                f"Publisher visual sitemap has an unmanaged URL: {location}"
            )
        gallery = galleries_by_url[location]
        locale = gallery["locale"]
        relative = _relative_path(target, pages)
        expected_relative = (
            "visuals/index.html"
            if locale == "en"
            else f"{locale}/visuals/index.html"
        )
        if relative != expected_relative:
            raise ValueError(
                f"Publisher visual sitemap has an invalid gallery: {relative}"
            )
        declared_dates = DATE_MODIFIED_RE.findall(
            target.read_text(encoding="utf-8")
        )
        if declared_dates != [modified]:
            raise ValueError(
                "Publisher visual gallery date does not match manifest: "
                f"{relative}"
            )
        if _sha256(target) != gallery["sha256"]:
            raise ValueError(
                "Publisher visual gallery digest does not match manifest: "
                f"{relative}"
            )


def _record_for(
    url: str,
    target: Path,
    pages: Path,
    previous: dict[str, Any] | None,
    history_dates: dict[str, str],
    dirty_paths: set[str],
    content_date: str,
    max_date: str,
    digest: str | None = None,
) -> dict[str, str]:
    relative = _relative_path(target, pages)
    digest = digest or _sha256(target)
    if previous is not None and previous.get("path") != relative:
        raise ValueError(
            f"Sitemap state path changed unexpectedly for {url}: "
            f"{previous.get('path')} -> {relative}"
        )
    if previous is not None and previous.get("sha256") == digest:
        lastmod = str(previous["lastmod"])
    elif relative in dirty_paths:
        lastmod = content_date
    else:
        lastmod = history_dates.get(relative)
        if lastmod is None:
            raise ValueError(
                "No Git history date for clean sitemap target: "
                f"{url} ({relative})"
            )
    if not _valid_date(lastmod, today=max_date):
        raise ValueError(f"Invalid derived lastmod for {url}: {lastmod}")
    return {
        "path": relative,
        "sha256": digest,
        "lastmod": lastmod,
    }


def _select_previous(
    url: str,
    relative: str,
    digest: str,
    primary: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
) -> dict[str, Any] | None:
    for record in (primary, fallback):
        if record is not None and record.get("path") != relative:
            raise ValueError(
                f"Sitemap state path changed unexpectedly for {url}: "
                f"{record.get('path')} -> {relative}"
            )
    for record in (primary, fallback):
        if record is not None and record.get("sha256") == digest:
            return record
    return primary or fallback


def generate(
    pages: Path = PAGES,
    *,
    site: str = SITE,
    state_path: Path | None = None,
    fallback_state_path: Path | None = None,
    today: str | None = None,
    workflow_started_at: datetime | str | None = None,
    validation_time: datetime | str | None = None,
    history_dates: dict[str, str] | None = None,
    dirty_paths: set[str] | None = None,
) -> dict[str, int]:
    pages = pages.resolve()
    _resolved_directory.cache_clear()
    site = site.rstrip("/")
    validation_instant = (
        _utc_instant(validation_time, label="validation time")
        if validation_time is not None
        else datetime.now(timezone.utc)
    )
    reference_time = _validation_reference(
        workflow_started_at,
        validation_time=validation_instant,
    )
    reference_date = reference_time.date().isoformat()
    max_date = (
        validation_instant + MAX_CLOCK_SKEW
    ).date().isoformat()
    # The build date stays deterministic. Git timestamps are bounded once by
    # validation_instant + MAX_CLOCK_SKEW, even when the workflow floor wins.
    today = today or reference_date
    if not _valid_date(today, today=reference_date):
        raise ValueError(
            f"Invalid --today date for {reference_date}: {today}"
        )
    state_path = (
        state_path.resolve()
        if state_path is not None
        else pages / STATE_RELATIVE_PATH
    )
    state = _load_state(state_path, max_date)
    fallback_state = (
        _load_state(fallback_state_path.resolve(), max_date)
        if fallback_state_path is not None
        else {"version": 1, "urls": {}, "sitemaps": {}}
    )

    documents: list[tuple[Path, str, list[re.Match[str]], list[str]]] = []
    targets: dict[str, Path] = {}
    excluded_entries = 0
    total_entries = 0
    for sitemap in _sitemap_paths(pages):
        source, blocks = _xml_blocks(
            sitemap,
            "urlset",
            "url",
            URL_BLOCK_RE,
        )
        locations: list[str] = []
        for block in blocks:
            total_entries += 1
            location = _block_location(sitemap, block.group("body"))
            locations.append(location)
            target = _owned_target(location, pages, site)
            if target is None:
                excluded_entries += 1
                continue
            existing = targets.get(location)
            if existing is not None and existing != target:
                raise ValueError(
                    f"Sitemap URL maps to conflicting files: {location}"
                )
            targets[location] = target
        documents.append((sitemap, source, blocks, locations))

    index_path = pages / "sitemap_index.xml"
    index_document: (
        tuple[str, list[re.Match[str]], list[str], dict[str, Path]]
        | None
    ) = None
    if index_path.is_file():
        index_source, index_blocks = _xml_blocks(
            index_path,
            "sitemapindex",
            "sitemap",
            SITEMAP_BLOCK_RE,
        )
        index_locations: list[str] = []
        index_targets: dict[str, Path] = {}
        for block in index_blocks:
            location = _block_location(index_path, block.group("body"))
            target = _owned_target(location, pages, site)
            if target is None or target.suffix != ".xml":
                raise ValueError(
                    f"Sitemap index URL is not a local XML file: {location}"
                )
            index_locations.append(location)
            index_targets[location] = target
        index_document = (
            index_source,
            index_blocks,
            index_locations,
            index_targets,
        )

    wanted_paths = {
        _relative_path(target, pages) for target in targets.values()
    }
    targets_by_path = {
        _relative_path(target, pages): target
        for target in targets.values()
    }
    index_targets_by_path = (
        {
            _relative_path(target, pages): target
            for target in index_document[3].values()
        }
        if index_document is not None
        else {}
    )
    all_targets_by_path = targets_by_path | index_targets_by_path
    target_digests = {
        path: _sha256(target)
        for path, target in all_targets_by_path.items()
    }
    url_previous = {
        url: _select_previous(
            url,
            _relative_path(target, pages),
            target_digests[_relative_path(target, pages)],
            state["urls"].get(url),
            fallback_state["urls"].get(url),
        )
        for url, target in targets.items()
    }
    sitemap_previous = (
        {
            url: _select_previous(
                url,
                _relative_path(target, pages),
                target_digests[_relative_path(target, pages)],
                state["sitemaps"].get(url),
                fallback_state["sitemaps"].get(url),
            )
            for url, target in index_document[3].items()
        }
        if index_document is not None
        else {}
    )
    if index_document is not None:
        wanted_paths.update(index_targets_by_path)
    if dirty_paths is None:
        dirty_paths = git_dirty_paths(pages)
    if history_dates is None:
        missing_history = {
            path
            for url, target in targets.items()
            for path in (_relative_path(target, pages),)
            if path not in dirty_paths
            and (
                url_previous[url] is None
                or url_previous[url]["sha256"] != target_digests[path]
            )
        }
        if index_document is not None:
            missing_history.update(
                _relative_path(target, pages)
                for url, target in index_document[3].items()
                if _relative_path(target, pages) not in dirty_paths
                and (
                    sitemap_previous[url] is None
                    or sitemap_previous[url]["sha256"]
                    != target_digests[_relative_path(target, pages)]
                )
            )
        history_dates = git_history_dates(
            pages,
            missing_history,
            validation_time=validation_instant,
        )
    for path, value in history_dates.items():
        if path in wanted_paths and not _valid_date(
            value,
            today=max_date,
        ):
            raise ValueError(f"Invalid Git history date for {path}: {value}")

    url_records = {
        url: _record_for(
            url,
            target,
            pages,
            url_previous[url],
            history_dates,
            dirty_paths,
            today,
            max_date,
            target_digests[_relative_path(target, pages)],
        )
        for url, target in sorted(targets.items())
    }

    changed_sitemaps: set[str] = set()
    changed_dates = 0
    for sitemap, source, blocks, locations in documents:
        _validate_publisher_visual_sitemap(
            sitemap,
            pages,
            locations,
            targets,
            url_records,
            site,
            max_date,
        )
        replacements: dict[int, str] = {}
        for index, (block, location) in enumerate(zip(blocks, locations)):
            record = url_records.get(location)
            if record is None:
                continue
            body = block.group("body")
            updated = _with_lastmod(
                sitemap,
                body,
                record["lastmod"],
            )
            if updated != body:
                changed_dates += 1
                replacements[index] = updated
        rendered = _render_blocks(source, blocks, replacements)
        if _write_if_changed(sitemap, rendered):
            changed_sitemaps.add(_relative_path(sitemap, pages))

    index_entries = 0
    sitemap_records: dict[str, dict[str, str]] = {}
    index_changed = False
    if index_document is not None:
        source, blocks, locations, index_targets = index_document
        replacements: dict[int, str] = {}
        for index, (block, location) in enumerate(zip(blocks, locations)):
            index_entries += 1
            target = index_targets[location]
            relative = _relative_path(target, pages)
            current_digest = (
                _sha256(target)
                if relative in changed_sitemaps
                else target_digests[relative]
            )
            previous = _select_previous(
                location,
                relative,
                current_digest,
                state["sitemaps"].get(location),
                fallback_state["sitemaps"].get(location),
            )
            record = _record_for(
                location,
                target,
                pages,
                previous,
                history_dates,
                dirty_paths | changed_sitemaps,
                today,
                max_date,
                current_digest,
            )
            sitemap_records[location] = record
            body = block.group("body")
            updated = _with_lastmod(
                index_path,
                body,
                record["lastmod"],
            )
            if updated != body:
                changed_dates += 1
                replacements[index] = updated
        rendered = _render_blocks(source, blocks, replacements)
        index_changed = _write_if_changed(index_path, rendered)

    new_state = {
        "version": 1,
        "urls": url_records,
        "sitemaps": sitemap_records,
    }
    state_changed = _write_if_changed(
        state_path,
        json.dumps(
            new_state,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return {
        "sitemap_files": len(documents),
        "entries": total_entries,
        "mapped_urls": len(url_records),
        "excluded_entries": excluded_entries,
        "index_entries": index_entries,
        "changed_dates": changed_dates,
        "changed_files": (
            len(changed_sitemaps)
            + int(index_changed)
            + int(state_changed)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--site", default=SITE)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--fallback-state", type=Path)
    parser.add_argument(
        "--today",
        help="Logical build date; must not exceed the validation UTC date.",
    )
    parser.add_argument(
        "--workflow-started-at",
        help=(
            "Trusted offset-aware workflow start. The validation reference is "
            "max(this instant, the current UTC instant)."
        ),
    )
    args = parser.parse_args()
    stats = generate(
        args.pages,
        site=args.site,
        state_path=args.state,
        fallback_state_path=args.fallback_state,
        today=args.today,
        workflow_started_at=args.workflow_started_at,
    )
    print(
        "Truthful sitemap lastmod: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
