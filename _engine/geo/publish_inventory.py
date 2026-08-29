#!/usr/bin/env python3
"""Build a reversible, allowlisted GitHub Pages publication artifact.

Source content is never deleted. Only pages that are unprotected, unreachable
from the site entrypoint, absent from every sitemap, and either ``noindex`` or
an exact/canonical duplicate are omitted from the staged artifact.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import fnmatch
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
from typing import Iterator
import urllib.parse

from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
DEFAULT_POLICY = HERE / "publish_inventory_policy.json"
# Selection-only digest from the reviewed crawl-budget policy at 7ae93a43.
AUTHORITY_SELECTION_SHA256 = (
    "467098831d8085bedf1defa210146c22164a04e590a269b259274b1f4dab0863"
)
SHA_RE = re.compile(r"[0-9a-f]{40}")
META_RE = re.compile(r"<meta\b[^>]*>", re.I)
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.I)
ATTR_RE = re.compile(
    r"""([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""",
    re.I,
)
SITEMAP_LOC_RE = re.compile(r"<loc>([^<]+)</loc>", re.I)
RESERVED_OUTPUTS = frozenset(
    {
        ".well-known/deployment.json",
        ".well-known/publish-inventory.json",
    }
)
CRAWL_HTML_SUFFIXES = (".html", ".htm")


class InventoryError(RuntimeError):
    """Raised when a publication safety gate fails."""


def canonical_json(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    return (text + "\n").encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("version") != 1:
        raise InventoryError("publish inventory policy version must be 1")
    if not isinstance(policy.get("site"), str):
        raise InventoryError("publish inventory policy requires a site URL")
    selection = {
        key: value for key, value in policy.items() if key != "budgets"
    }
    if sha256_bytes(canonical_json(selection)) != AUTHORITY_SELECTION_SHA256:
        raise InventoryError(
            "publish inventory selection differs from the authoritative "
            "crawl-budget allowlist"
        )
    return policy


def normalized_relative(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if (
        not relative
        or relative.startswith("/")
        or ".." in PurePosixPath(relative).parts
    ):
        raise InventoryError(f"unsafe inventory path: {relative}")
    return relative


def matches_prefix(relative: str, prefixes: list[str]) -> bool:
    return any(
        relative == prefix.rstrip("/") or relative.startswith(prefix)
        for prefix in prefixes
    )


def attributes(tag: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag):
        result[match.group(1).lower()] = html.unescape(
            next(value for value in match.groups()[1:] if value is not None)
        )
    return result


def html_facts(source: str) -> tuple[bool, str | None, tuple[str, ...]]:
    head_end = source.lower().find("</head>")
    head = source if head_end < 0 else source[:head_end]
    noindex = False
    canonical = None
    for match in META_RE.finditer(head):
        attrs = attributes(match.group(0))
        if (
            attrs.get("name", "").lower() == "robots"
            and "noindex" in attrs.get("content", "").lower()
        ):
            noindex = True
    for match in LINK_RE.finditer(head):
        attrs = attributes(match.group(0))
        relations = {
            item.lower() for item in attrs.get("rel", "").split()
        }
        if "canonical" in relations and attrs.get("href"):
            canonical = attrs["href"].strip()
            break
    links = []
    for match in ANCHOR_RE.finditer(source):
        href = attributes(match.group(0)).get("href", "").strip()
        if href:
            links.append(href)
    return noindex, canonical, tuple(links)


def internal_relative(
    raw_url: str,
    *,
    page_relative: str,
    site: str,
) -> str | None:
    raw_url = html.unescape(raw_url.strip())
    if not raw_url or raw_url.startswith(
        ("#", "mailto:", "tel:", "javascript:", "data:")
    ):
        return None
    site_parts = urllib.parse.urlsplit(site.rstrip("/"))
    base_path = site_parts.path.rstrip("/")
    page_url = f"{site.rstrip('/')}/{urllib.parse.quote(page_relative, safe='/')}"
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(page_url, raw_url))
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc != site_parts.netloc:
        return None
    path = urllib.parse.unquote(parsed.path)
    if path == base_path or path == f"{base_path}/":
        return "index.html"
    prefix = f"{base_path}/"
    if not path.startswith(prefix):
        return None
    relative = path[len(prefix) :].lstrip("/")
    if relative.endswith("/"):
        relative += "index.html"
    if not relative:
        relative = "index.html"
    candidate = PurePosixPath(relative)
    if ".." in candidate.parts:
        return None
    return candidate.as_posix()


def is_protected(relative: str, policy: dict) -> bool:
    protected = policy["protected"]
    if relative in protected["exact_paths"]:
        return True
    if matches_prefix(relative, protected["prefixes"]):
        return True
    if relative.split("/", 1)[0] in OFFICIAL_LOCALES:
        return True
    name = PurePosixPath(relative).name
    return any(
        fnmatch.fnmatchcase(name, pattern)
        for pattern in protected["basename_globs"]
    )


def is_allowlisted(relative: str, policy: dict) -> bool:
    if relative in RESERVED_OUTPUTS:
        return False
    if matches_prefix(relative, policy["private_prefixes"]):
        return False
    if is_protected(relative, policy):
        return True
    if relative in policy["allow"]["exact_paths"]:
        return True
    if any(
        part.startswith(".")
        for part in PurePosixPath(relative).parts
    ):
        return False
    return PurePosixPath(relative).suffix.lower() in set(
        policy["allow"]["extensions"]
    )


def legacy_included(relative: str, policy: dict) -> bool:
    return not matches_prefix(
        relative,
        policy["legacy_excluded_prefixes"],
    )


def iter_source_files(
    root: Path,
    *,
    ignored_output: Path | None = None,
) -> list[Path]:
    root = root.resolve()
    ignored = ignored_output.resolve() if ignored_output else None
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        base = Path(directory)
        retained_dirs = []
        for name in sorted(dirnames):
            candidate = (base / name).resolve()
            if name == ".git" or (
                ignored is not None
                and (candidate == ignored or ignored in candidate.parents)
            ):
                continue
            retained_dirs.append(name)
        dirnames[:] = retained_dirs
        for name in sorted(filenames):
            path = base / name
            if ignored is not None:
                resolved = path.resolve()
                if resolved == ignored or ignored in resolved.parents:
                    continue
            files.append(path)
    return sorted(files, key=lambda item: normalized_relative(root, item))


def iter_worktree_items(
    root: Path,
    *,
    ignored_output: Path | None = None,
) -> Iterator[tuple[str, bytes, bool, Path | None]]:
    for path in iter_source_files(root, ignored_output=ignored_output):
        relative = normalized_relative(root, path)
        is_symlink = path.is_symlink()
        try:
            content = path.read_bytes()
        except OSError as error:
            raise InventoryError(
                f"cannot read source file: {relative}"
            ) from error
        yield relative, content, is_symlink, path


def iter_git_tree_items(
    repository: Path,
    tree_ref: str,
) -> Iterator[tuple[str, bytes, bool, Path | None]]:
    if not tree_ref or any(character in tree_ref for character in "\r\n\0"):
        raise InventoryError("git tree ref must be non-empty single-line text")
    process = subprocess.Popen(
        [
            "git",
            "-C",
            str(repository),
            "archive",
            "--format=tar",
            tree_ref,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    stderr = ""
    returncode = 0
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                if member.isdir():
                    continue
                relative = PurePosixPath(member.name).as_posix()
                if (
                    relative.startswith("/")
                    or ".." in PurePosixPath(relative).parts
                ):
                    raise InventoryError(
                        f"unsafe path in git tree: {relative}"
                    )
                is_symlink = member.issym() or member.islnk()
                handle = archive.extractfile(member)
                if handle is None:
                    content = b""
                else:
                    content = handle.read()
                yield relative, content, is_symlink, None
    finally:
        process.stdout.close()
        if process.stderr is not None:
            stderr = process.stderr.read().decode("utf-8", "replace")
            process.stderr.close()
        returncode = process.wait()
    if returncode:
        raise InventoryError(
            f"git archive failed for {tree_ref}: {stderr.strip()}"
        )


def deployment_bytes(source_commit: str) -> bytes:
    if not SHA_RE.fullmatch(source_commit):
        raise InventoryError("source commit must be a lowercase 40-character SHA")
    return (
        f'{{"version":1,"source_commit":"{source_commit}"}}\n'
    ).encode("ascii")


def git_commit(repository: Path, ref: str = "HEAD") -> str | None:
    top_level = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--show-toplevel"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if top_level.returncode or (
        Path(top_level.stdout.strip()).resolve() != repository.resolve()
    ):
        return None
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "rev-parse",
            "--verify",
            f"{ref}^{{commit}}",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode:
        return None
    value = result.stdout.strip().lower()
    if not SHA_RE.fullmatch(value):
        raise InventoryError(f"git ref did not resolve to an exact SHA: {ref}")
    return value


def _entry(path: str, size: int, digest: str) -> dict:
    return {"bytes": size, "path": path, "sha256": digest}


def _stable_manifest_bytes(manifest: dict, content_bytes: int) -> bytes:
    previous = (-1, -1)
    for _ in range(12):
        rendered = canonical_json(manifest)
        current = (len(rendered), content_bytes + len(rendered))
        manifest["publish"]["manifest_bytes"] = current[0]
        manifest["publish"]["bytes"] = current[1]
        if current == previous:
            return rendered
        previous = current
    raise InventoryError("publish manifest size did not converge")


def _duplicate_paths(
    html_records: dict[str, dict],
    *,
    site: str,
) -> set[str]:
    by_digest: dict[str, list[str]] = defaultdict(list)
    duplicates: set[str] = set()
    for relative, record in html_records.items():
        by_digest[record["sha256"]].append(relative)
        canonical = record["canonical"]
        if canonical:
            target = internal_relative(
                canonical,
                page_relative=relative,
                site=site,
            )
            if target in html_records and target != relative:
                duplicates.add(relative)
    for paths in by_digest.values():
        if len(paths) > 1:
            duplicates.update(sorted(paths)[1:])
    return duplicates


def _reachable_html(
    html_records: dict[str, dict],
    entrypoints: list[str],
) -> set[str]:
    reachable = {path for path in entrypoints if path in html_records}
    queue = deque(sorted(reachable))
    while queue:
        relative = queue.popleft()
        for target in html_records[relative]["targets"]:
            if target in html_records and target not in reachable:
                reachable.add(target)
                queue.append(target)
    return reachable


def _safe_exclusions(
    html_records: dict[str, dict],
    *,
    reachable: set[str],
    sitemap_html: set[str],
) -> set[str]:
    candidates = {
        relative
        for relative, record in html_records.items()
        if (
            not record["protected"]
            and relative not in reachable
            and relative not in sitemap_html
            and (record["noindex"] or record["duplicate"])
        )
    }
    while True:
        retained = set(html_records) - candidates
        linked_from_retained = {
            target
            for source in retained
            for target in html_records[source]["targets"]
            if target in candidates
        }
        if not linked_from_retained:
            return candidates
        candidates.difference_update(linked_from_retained)


def _required_violations(
    included: set[str],
    policy: dict,
) -> list[str]:
    required = policy["required"]
    violations = [
        f"missing required publish path: {path}"
        for path in required["exact_paths"]
        if path not in included
    ]
    for prefix in required["nonempty_prefixes"]:
        if not any(path.startswith(prefix) for path in included):
            violations.append(f"empty required publish prefix: {prefix}")
    template = required["localized_feed_template"]
    for locale in OFFICIAL_LOCALES:
        feed = template.format(locale=locale)
        if feed not in included:
            violations.append(f"missing required localized feed: {feed}")
        locale_prefix = f"{locale}/"
        if not any(path.startswith(locale_prefix) for path in included):
            violations.append(f"missing official locale inventory: {locale}")
    return violations


def _budget_violations(manifest: dict, policy: dict) -> list[str]:
    budgets = policy["budgets"]
    publish = manifest["publish"]
    analysis = manifest["analysis"]
    savings = manifest["savings"]
    checks = (
        (
            publish["files"] <= budgets["max_publish_files"],
            f"publish files {publish['files']} exceed "
            f"{budgets['max_publish_files']}",
        ),
        (
            publish["bytes"] <= budgets["max_publish_bytes"],
            f"publish bytes {publish['bytes']} exceed "
            f"{budgets['max_publish_bytes']}",
        ),
        (
            publish["html_files"] <= budgets["max_publish_html_files"],
            f"publish HTML files {publish['html_files']} exceed "
            f"{budgets['max_publish_html_files']}",
        ),
        (
            analysis["indexable_orphans"]
            <= budgets["max_indexable_orphans"],
            f"indexable orphans {analysis['indexable_orphans']} exceed "
            f"{budgets['max_indexable_orphans']}",
        ),
        (
            analysis["broken_internal_html_links"]
            <= budgets["max_broken_internal_html_links"],
            "broken internal HTML links "
            f"{analysis['broken_internal_html_links']} exceed "
            f"{budgets['max_broken_internal_html_links']}",
        ),
        (
            analysis["sitemap_missing_html_targets"]
            <= budgets["max_sitemap_missing_html_targets"],
            "sitemap missing HTML targets "
            f"{analysis['sitemap_missing_html_targets']} exceed "
            f"{budgets['max_sitemap_missing_html_targets']}",
        ),
        (
            analysis["sitemap_noindex_html_targets"]
            <= budgets["max_sitemap_noindex_html_targets"],
            "sitemap noindex HTML targets "
            f"{analysis['sitemap_noindex_html_targets']} exceed "
            f"{budgets['max_sitemap_noindex_html_targets']}",
        ),
        (
            savings["files"] >= budgets["min_saved_files"],
            f"saved files {savings['files']} below "
            f"{budgets['min_saved_files']}",
        ),
        (
            savings["bytes"] >= budgets["min_saved_bytes"],
            f"saved bytes {savings['bytes']} below "
            f"{budgets['min_saved_bytes']}",
        ),
    )
    return [message for passed, message in checks if not passed]


def analyze(
    source: Path,
    *,
    policy: dict,
    source_commit: str,
    output: Path | None = None,
    tree_ref: str | None = None,
) -> tuple[dict, bytes, dict[str, Path]]:
    source = source.resolve()
    if not source.is_dir():
        raise InventoryError(f"source directory does not exist: {source}")
    if tree_ref is not None and output is not None:
        raise InventoryError("git-tree analysis cannot materialize an output")
    actual_commit = git_commit(source, tree_ref or "HEAD")
    if actual_commit is not None and actual_commit != source_commit:
        raise InventoryError(
            f"source commit mismatch: expected {actual_commit}, "
            f"received {source_commit}"
        )
    site = policy["site"].rstrip("/")
    deploy_content = deployment_bytes(source_commit)
    source_paths: dict[str, Path] = {}
    file_entries: dict[str, dict] = {}
    html_records: dict[str, dict] = {}
    sitemap_sources: dict[str, str] = {}
    excluded: dict[str, dict] = {}
    legacy_files = 1
    legacy_bytes = len(deploy_content)
    legacy_html = 0

    items = (
        iter_git_tree_items(source, tree_ref)
        if tree_ref is not None
        else iter_worktree_items(source, ignored_output=output)
    )
    for relative, content, symlink, path in items:
        if relative in RESERVED_OUTPUTS:
            continue
        if symlink:
            raise InventoryError(f"symlinks are not publishable: {relative}")
        size = len(content)
        if legacy_included(relative, policy):
            legacy_files += 1
            legacy_bytes += size
            legacy_html += int(relative.endswith(CRAWL_HTML_SUFFIXES))
        if not is_allowlisted(relative, policy):
            reason = (
                "private"
                if matches_prefix(relative, policy["private_prefixes"])
                else "not_allowlisted"
            )
            excluded[relative] = {
                "bytes": size,
                "path": relative,
                "reasons": [reason],
            }
            continue
        digest = sha256_bytes(content)
        file_entries[relative] = _entry(relative, len(content), digest)
        if path is not None:
            source_paths[relative] = path
        if relative.endswith(CRAWL_HTML_SUFFIXES):
            text = content.decode("utf-8", "replace")
            noindex, canonical, links = html_facts(text)
            targets = {
                target
                for raw in links
                for target in [
                    internal_relative(
                        raw,
                        page_relative=relative,
                        site=site,
                    )
                ]
                if target is not None
            }
            html_records[relative] = {
                "canonical": canonical,
                "duplicate": False,
                "noindex": noindex,
                "protected": is_protected(relative, policy),
                "sha256": digest,
                "targets": targets,
            }
        name = PurePosixPath(relative).name
        if name.startswith("sitemap") and name.endswith(".xml"):
            sitemap_sources[relative] = content.decode(
                "utf-8",
                "replace",
            )

    duplicates = _duplicate_paths(html_records, site=site)
    for relative in duplicates:
        html_records[relative]["duplicate"] = True
    reachable = _reachable_html(html_records, policy["entrypoints"])

    sitemap_html: set[str] = set()
    sitemap_missing: set[str] = set()
    for relative, text in sitemap_sources.items():
        for raw in SITEMAP_LOC_RE.findall(text):
            target = internal_relative(
                raw,
                page_relative=relative,
                site=site,
            )
            if target is None:
                continue
            if target in html_records:
                sitemap_html.add(target)
            elif target.endswith(CRAWL_HTML_SUFFIXES):
                sitemap_missing.add(target)

    safe_exclusions = _safe_exclusions(
        html_records,
        reachable=reachable,
        sitemap_html=sitemap_html,
    )
    for relative in sorted(safe_exclusions):
        record = html_records[relative]
        reasons = ["orphan"]
        if record["noindex"]:
            reasons.append("noindex")
        if record["duplicate"]:
            reasons.append("duplicate")
        entry = file_entries.pop(relative)
        source_paths.pop(relative, None)
        excluded[relative] = {
            "bytes": entry["bytes"],
            "path": relative,
            "reasons": reasons,
        }

    retained_html = set(html_records) - safe_exclusions
    broken_targets = {
        target
        for source_relative in retained_html
        for target in html_records[source_relative]["targets"]
        if (
            target.endswith(CRAWL_HTML_SUFFIXES)
            and target not in retained_html
        )
    }
    indexable_orphans = {
        relative
        for relative, record in html_records.items()
        if (
            relative not in reachable
            and relative not in sitemap_html
            and relative not in safe_exclusions
            and not record["noindex"]
        )
    }
    sitemap_excluded = sitemap_html & safe_exclusions
    sitemap_noindex = {
        path for path in sitemap_html if html_records[path]["noindex"]
    }

    deployment_entry = _entry(
        ".well-known/deployment.json",
        len(deploy_content),
        sha256_bytes(deploy_content),
    )
    file_entries[deployment_entry["path"]] = deployment_entry
    included_entries = [
        file_entries[path] for path in sorted(file_entries)
    ]
    included = set(file_entries)
    violations = _required_violations(included, policy)
    if sitemap_excluded:
        violations.append(
            "sitemaps reference excluded HTML: "
            + ", ".join(sorted(sitemap_excluded)[:10])
        )

    inventory_hasher = hashlib.sha256()
    for entry in included_entries:
        inventory_hasher.update(
            (
                f"{entry['path']}\0{entry['bytes']}\0"
                f"{entry['sha256']}\n"
            ).encode("utf-8")
        )
    policy_digest = sha256_bytes(canonical_json(policy))
    content_bytes = sum(entry["bytes"] for entry in included_entries)
    publish_html = sum(
        path.endswith(CRAWL_HTML_SUFFIXES)
        for path in included
    )
    protected_html = {
        path
        for path in retained_html
        if html_records[path]["protected"]
    }
    manifest = {
        "analysis": {
            "broken_internal_html_links": len(broken_targets),
            "duplicate_html": len(duplicates),
            "excluded_duplicate_html": sum(
                html_records[path]["duplicate"] for path in safe_exclusions
            ),
            "excluded_html": len(safe_exclusions),
            "excluded_noindex_html": sum(
                html_records[path]["noindex"] for path in safe_exclusions
            ),
            "excluded_orphan_html": len(safe_exclusions),
            "indexable_orphans": len(indexable_orphans),
            "noindex_html": sum(
                record["noindex"] for record in html_records.values()
            ),
            "orphan_html": len(set(html_records) - reachable),
            "protected_html": len(protected_html),
            "retained_noindex_html": sum(
                record["noindex"]
                for path, record in html_records.items()
                if path not in safe_exclusions
            ),
            "sitemap_excluded_html_targets": len(sitemap_excluded),
            "sitemap_html_targets": len(sitemap_html),
            "sitemap_missing_html_targets": len(sitemap_missing),
            "sitemap_noindex_html_targets": len(sitemap_noindex),
        },
        "diagnostics": {
            "broken_internal_html_targets": sorted(broken_targets),
            "indexable_orphans": sorted(indexable_orphans),
            "sitemap_excluded_html_targets": sorted(sitemap_excluded),
            "sitemap_missing_html_targets": sorted(sitemap_missing),
            "sitemap_noindex_html_targets": sorted(sitemap_noindex),
        },
        "excluded": [excluded[path] for path in sorted(excluded)],
        "generated": {
            "deployment": deployment_entry,
            "manifest_path": ".well-known/publish-inventory.json",
        },
        "included": [entry["path"] for entry in included_entries],
        "inventory_sha256": inventory_hasher.hexdigest(),
        "legacy": {
            "bytes": legacy_bytes,
            "files": legacy_files,
            "html_files": legacy_html,
        },
        "policy_sha256": policy_digest,
        "publish": {
            "bytes": content_bytes,
            "content_bytes": content_bytes,
            "files": len(included_entries) + 1,
            "html_files": publish_html,
            "manifest_bytes": 0,
        },
        "safety": {
            "excluded_protected_files": 0,
            "source_content_deleted": False,
        },
        "site": site,
        "source_commit": source_commit,
        "version": 1,
        "violations": violations,
    }
    manifest["savings"] = {
        "bytes": legacy_bytes - manifest["publish"]["bytes"],
        "files": legacy_files - manifest["publish"]["files"],
        "html_files": legacy_html - publish_html,
    }
    manifest_bytes = _stable_manifest_bytes(manifest, content_bytes)
    manifest["savings"]["bytes"] = (
        legacy_bytes - manifest["publish"]["bytes"]
    )
    manifest["violations"].extend(_budget_violations(manifest, policy))
    manifest["violations"] = sorted(set(manifest["violations"]))
    manifest_bytes = _stable_manifest_bytes(manifest, content_bytes)
    manifest["savings"]["bytes"] = (
        legacy_bytes - manifest["publish"]["bytes"]
    )
    manifest_bytes = _stable_manifest_bytes(manifest, content_bytes)
    return manifest, manifest_bytes, source_paths


def materialize(
    source: Path,
    output: Path,
    *,
    manifest: dict,
    manifest_bytes: bytes,
    source_paths: dict[str, Path],
) -> None:
    source = source.resolve()
    output = output.resolve()
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise InventoryError("publish output must be outside the source tree")
    if output.exists() and any(output.iterdir()):
        raise InventoryError(f"publish output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for relative in manifest["included"]:
        if relative == ".well-known/deployment.json":
            continue
        source_path = source_paths[relative]
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
    deployment = deployment_bytes(manifest["source_commit"])
    deployment_path = output / ".well-known" / "deployment.json"
    deployment_path.parent.mkdir(parents=True, exist_ok=True)
    deployment_path.write_bytes(deployment)
    manifest_path = output / ".well-known" / "publish-inventory.json"
    manifest_path.write_bytes(manifest_bytes)
    if deployment_path.read_bytes() != deployment:
        raise InventoryError("deployment manifest bytes changed during staging")
    actual_files = sum(1 for path in output.rglob("*") if path.is_file())
    actual_bytes = sum(
        path.stat().st_size for path in output.rglob("*") if path.is_file()
    )
    if actual_files != manifest["publish"]["files"]:
        raise InventoryError(
            f"materialized file count {actual_files} does not match manifest "
            f"{manifest['publish']['files']}"
        )
    if actual_bytes != manifest["publish"]["bytes"]:
        raise InventoryError(
            f"materialized bytes {actual_bytes} do not match manifest "
            f"{manifest['publish']['bytes']}"
        )


def run(
    source: Path,
    *,
    policy_path: Path = DEFAULT_POLICY,
    source_commit: str,
    output: Path | None = None,
    manifest_out: Path | None = None,
    tree_ref: str | None = None,
) -> dict:
    policy = load_policy(policy_path)
    manifest, manifest_bytes, source_paths = analyze(
        source,
        policy=policy,
        source_commit=source_commit,
        output=output,
        tree_ref=tree_ref,
    )
    if manifest_out is not None:
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_bytes(manifest_bytes)
    if manifest["violations"]:
        raise InventoryError(
            "publish inventory blocked: "
            + "; ".join(manifest["violations"])
        )
    if output is not None:
        materialize(
            source,
            output,
            manifest=manifest,
            manifest_bytes=manifest_bytes,
            source_paths=source_paths,
        )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--git-tree",
        help="Analyze this committed tree without expanding a sparse checkout",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only; do not materialize an artifact",
    )
    args = parser.parse_args()
    if args.dry_run and args.output is not None:
        parser.error("--dry-run and --output are mutually exclusive")
    if args.git_tree and not args.dry_run:
        parser.error("--git-tree requires --dry-run")
    if not args.dry_run and args.output is None:
        parser.error("--output is required unless --dry-run is used")
    try:
        manifest = run(
            args.source,
            policy_path=args.policy,
            source_commit=args.source_commit,
            output=args.output,
            manifest_out=args.manifest_out,
            tree_ref=args.git_tree,
        )
    except InventoryError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(
        "publish-inventory "
        f"before_files={manifest['legacy']['files']} "
        f"before_bytes={manifest['legacy']['bytes']} "
        f"before_html={manifest['legacy']['html_files']} "
        f"after_files={manifest['publish']['files']} "
        f"after_bytes={manifest['publish']['bytes']} "
        f"after_html={manifest['publish']['html_files']} "
        f"excluded_html={manifest['analysis']['excluded_html']} "
        f"inventory_sha256={manifest['inventory_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
