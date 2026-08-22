#!/usr/bin/env python3
"""Keep sitemap lastmod dates tied to real content changes."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
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


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = "https://alice51849.github.io/ios-app-guide"
STATE_RELATIVE_PATH = Path("_engine/geo/sitemap_lastmod_state.json")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
DATE_MODIFIED_RE = re.compile(
    r'"dateModified"\s*:\s*"(?P<value>\d{4}-\d{2}-\d{2})"'
)
PUBLISHER_VISUAL_SITEMAP = Path("sitemap_intent_visuals.xml")
PUBLISHER_VISUAL_MANIFEST = Path(
    "data/lumi-studio-publisher-intent-visuals.json"
)
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
) -> dict[str, str]:
    if not wanted:
        return {}
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
            try:
                commit_date = datetime.fromtimestamp(
                    int(candidate),
                    timezone.utc,
                ).date().isoformat()
            except (OSError, OverflowError, ValueError):
                commit_date = None
            continue
        path = line.strip()
        if commit_date and path in wanted and path not in dates:
            dates[path] = commit_date
            if len(dates) == len(wanted):
                break
    return dates


def _load_state(path: Path, today: str) -> dict[str, Any]:
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
                or not _valid_date(record.get("lastmod"), today=today)
            ):
                raise ValueError(
                    f"Invalid sitemap lastmod state record: {section}/{url}"
                )
    return state


def _publisher_visual_lastmod(
    sitemap: Path,
    pages: Path,
    locations: list[str],
    targets: dict[str, Path],
    url_records: dict[str, dict[str, str]],
    today: str,
) -> str | None:
    if _relative_path(sitemap, pages) != PUBLISHER_VISUAL_SITEMAP.as_posix():
        return None
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
    if (
        not _valid_date(modified, today=today)
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
        or locale_count <= 0
        or not isinstance(image_count, int)
        or image_count != len(records)
        or image_count != app_count * locale_count
        or not isinstance(gallery_count, int)
        or gallery_count != locale_count + 1
        or gallery_count != len(locations)
        or len(set(locations)) != len(locations)
    ):
        raise ValueError("Invalid publisher visual manifest contract")

    for location in locations:
        target = targets.get(location)
        record = url_records.get(location)
        if target is None or record is None:
            raise ValueError(
                f"Publisher visual sitemap has an unmanaged URL: {location}"
            )
        relative = _relative_path(target, pages)
        parts = Path(relative).parts
        if not (
            relative == "visuals/index.html"
            or (
                len(parts) == 3
                and parts[1:] == ("visuals", "index.html")
            )
        ):
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
        if record["lastmod"] > modified:
            raise ValueError(
                "Publisher visual manifest is older than gallery content: "
                f"{relative} ({modified} < {record['lastmod']})"
            )
    return modified


def _record_for(
    url: str,
    target: Path,
    pages: Path,
    previous: dict[str, Any] | None,
    history_dates: dict[str, str],
    dirty_paths: set[str],
    today: str,
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
        lastmod = today
    else:
        lastmod = history_dates.get(relative)
        if lastmod is None:
            raise ValueError(
                "No Git history date for clean sitemap target: "
                f"{url} ({relative})"
            )
    if not _valid_date(lastmod, today=today):
        raise ValueError(f"Invalid derived lastmod for {url}: {lastmod}")
    return {
        "path": relative,
        "sha256": digest,
        "lastmod": lastmod,
    }


def generate(
    pages: Path = PAGES,
    *,
    site: str = SITE,
    state_path: Path | None = None,
    today: str | None = None,
    history_dates: dict[str, str] | None = None,
    dirty_paths: set[str] | None = None,
) -> dict[str, int]:
    pages = pages.resolve()
    _resolved_directory.cache_clear()
    site = site.rstrip("/")
    today = today or datetime.now(timezone.utc).date().isoformat()
    if not _valid_date(today, today=today):
        raise ValueError(f"Invalid --today date: {today}")
    state_path = (
        state_path.resolve()
        if state_path is not None
        else pages / STATE_RELATIVE_PATH
    )
    state = _load_state(state_path, today)

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
                url not in state["urls"]
                or state["urls"][url]["sha256"] != target_digests[path]
            )
        }
        if index_document is not None:
            missing_history.update(
                _relative_path(target, pages)
                for url, target in index_document[3].items()
                if _relative_path(target, pages) not in dirty_paths
                and (
                    url not in state["sitemaps"]
                    or state["sitemaps"][url]["sha256"]
                    != target_digests[_relative_path(target, pages)]
                )
            )
        history_dates = git_history_dates(pages, missing_history)
    for path, value in history_dates.items():
        if path in wanted_paths and not _valid_date(value, today=today):
            raise ValueError(f"Invalid Git history date for {path}: {value}")

    url_records = {
        url: _record_for(
            url,
            target,
            pages,
            state["urls"].get(url),
            history_dates,
            dirty_paths,
            today,
            target_digests[_relative_path(target, pages)],
        )
        for url, target in sorted(targets.items())
    }

    changed_sitemaps: set[str] = set()
    changed_dates = 0
    for sitemap, source, blocks, locations in documents:
        managed_lastmod = _publisher_visual_lastmod(
            sitemap,
            pages,
            locations,
            targets,
            url_records,
            today,
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
                managed_lastmod or record["lastmod"],
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
            previous = state["sitemaps"].get(location)
            record = _record_for(
                location,
                target,
                pages,
                previous,
                history_dates,
                dirty_paths | changed_sitemaps,
                today,
                (
                    _sha256(target)
                    if relative in changed_sitemaps
                    else target_digests[relative]
                ),
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
    parser.add_argument("--today")
    args = parser.parse_args()
    stats = generate(
        args.pages,
        site=args.site,
        state_path=args.state,
        today=args.today,
    )
    print(
        "Truthful sitemap lastmod: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
