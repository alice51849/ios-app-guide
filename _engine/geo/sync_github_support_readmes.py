#!/usr/bin/env python3
"""Keep direct App Store links visible on public support repositories."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))

from videogen.registry import APPS, APPSTORE  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
import sync_github_repo_metadata as metadata  # noqa: E402

OWNER = metadata.OWNER
PAGES = os.path.join(HERE, "pages")
SITE = metadata.SITE
START_MARKER = "<!-- BEGIN MANAGED APP STORE LINKS -->"
END_MARKER = "<!-- END MANAGED APP STORE LINKS -->"
README_PATH = "README.md"
COMMIT_MESSAGE = """Add direct App Store links to support README

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
Copilot-Session: 56b03b63-e910-42f2-bb48-3d22fbc5c8b1"""
REMOVE_MESSAGE = """Remove stale App Store links from support README

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
Copilot-Session: 56b03b63-e910-42f2-bb48-3d22fbc5c8b1"""
REPOSITORY_TITLES = {
    "lumi-support": "Lumi Bopomofo",
    "lumi-letters-support": "Lumi Letters",
    "lumi-math-support": "Lumi Math",
    "lumi-mission-support": "Lumi Mission Planet",
}


def _joined_names(keys):
    names = [APPS[key]["name"] for key in keys]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _sentence(value):
    value = " ".join(str(value).split())
    if value and value[-1] not in ".!?":
        value += "."
    return value


def app_store_url(key):
    app_id = str(APPSTORE.get(key) or "")
    if not re.fullmatch(r"\d{10}", app_id):
        raise ValueError(f"invalid App Store ID for {key}: {app_id!r}")
    return f"https://apps.apple.com/app/id{app_id}"


def render_managed_block(repository, keys):
    keys = sorted(keys)
    if not keys:
        raise ValueError("cannot render a README block without apps")
    title = REPOSITORY_TITLES.get(repository, APPS[keys[0]]["name"])
    lines = [
        START_MARKER,
        f"# {title} - Official Support",
        "",
        (
            "Official support resources and verified App Store links for "
            f"**{_joined_names(keys)}**."
        ),
        "",
        "## Get the app" if len(keys) == 1 else "## Apps",
        "",
    ]
    for key in keys:
        name = APPS[key]["name"]
        if len(keys) > 1:
            lines.extend([f"### {name}", ""])
        lines.extend(
            [
                _sentence(APPS[key].get("sub", "")),
                "",
                f"- **[View {name} on the App Store]({app_store_url(key)})**",
                f"- [Read the product guide]({SITE}/guides/{key}.html)",
                "",
            ]
        )
    lines.extend(
        [
            "## Support and privacy",
            "",
            (
                f"- [Open the official support site]"
                f"(https://{OWNER}.github.io/{repository}/)"
            ),
            "",
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def _marker_bounds(content):
    starts = content.count(START_MARKER)
    ends = content.count(END_MARKER)
    if starts != ends or starts > 1:
        raise ValueError("README contains malformed managed markers")
    if not starts:
        return None
    start = content.index(START_MARKER)
    end_start = content.index(END_MARKER)
    if end_start < start:
        raise ValueError("README contains malformed managed markers")
    end = end_start + len(END_MARKER)
    return start, end


def merge_managed_block(content, block):
    bounds = _marker_bounds(content)
    if bounds is None:
        if not content.strip():
            return block + "\n"
        return content.rstrip() + "\n\n" + block + "\n"
    start, end = bounds
    return content[:start] + block + content[end:]


def remove_managed_block(content):
    bounds = _marker_bounds(content)
    if bounds is None:
        return content
    start, end = bounds
    before = content[:start].rstrip()
    after = content[end:].strip()
    remaining = "\n\n".join(part for part in (before, after) if part)
    return remaining + ("\n" if remaining else "")


def desired_blocks(live_keys):
    grouped = metadata.group_apps_by_repository(live_keys)
    return {
        repository: render_managed_block(repository, keys)
        for repository, keys in grouped.items()
    }


def known_repositories():
    return sorted(
        {
            metadata.repository_for_app(key)
            for key in APPS
        }
        | set(metadata.REPO_OVERRIDES.values())
    )


def gh_api(arguments, payload=None, allow_not_found=False):
    command = ["gh", "api", *arguments]
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        error = result.stderr.strip() or result.stdout.strip()
        if allow_not_found and "HTTP 404" in error:
            return None
        raise RuntimeError(f"{' '.join(command)} failed: {error}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def read_readme(repository, branch):
    endpoint = f"repos/{OWNER}/{repository}/readme?ref={quote(branch)}"
    result = gh_api([endpoint], allow_not_found=True)
    if result is None:
        return None
    if result.get("encoding") != "base64":
        raise RuntimeError(f"unsupported README encoding in {repository}")
    try:
        content = base64.b64decode(
            "".join(result["content"].split()), validate=True
        ).decode("utf-8")
    except (KeyError, UnicodeDecodeError, ValueError) as error:
        raise RuntimeError(f"invalid README content in {repository}") from error
    return {
        "content": content,
        "path": result["path"],
        "sha": result["sha"],
    }


def put_readme(
    repository,
    branch,
    path,
    content,
    sha=None,
    *,
    message=COMMIT_MESSAGE,
):
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    gh_api(
        [
            "--method",
            "PUT",
            f"repos/{OWNER}/{repository}/contents/{quote(path, safe='/')}",
            "--input",
            "-",
        ],
        payload,
    )


def delete_readme(repository, branch, path, sha):
    gh_api(
        [
            "--method",
            "DELETE",
            f"repos/{OWNER}/{repository}/contents/{quote(path, safe='/')}",
            "--input",
            "-",
        ],
        {"message": REMOVE_MESSAGE, "sha": sha, "branch": branch},
    )


def sync_readmes(live_keys, apply=False):
    blocks = desired_blocks(live_keys)
    changed = 0
    for repository in known_repositories():
        info = gh_api(
            [f"repos/{OWNER}/{repository}"],
            allow_not_found=True,
        )
        if info is None:
            if repository in blocks:
                raise RuntimeError(
                    f"live apps map to missing repository: {repository}"
                )
            continue
        if info.get("private") or info.get("archived"):
            if repository in blocks:
                raise RuntimeError(
                    f"refusing live non-public repository: {repository}"
                )
            continue
        branch = info["default_branch"]
        current = read_readme(repository, branch)
        if repository in blocks:
            existing = current["content"] if current else ""
            desired = merge_managed_block(existing, blocks[repository])
            if desired == existing:
                print(f"= {repository}: already current")
                continue
            changed += 1
            print(f"{'~' if apply else '?'} {repository}: update README")
            if apply:
                put_readme(
                    repository,
                    branch,
                    current["path"] if current else README_PATH,
                    desired,
                    current["sha"] if current else None,
                )
            continue
        if current is None:
            continue
        desired = remove_managed_block(current["content"])
        if desired == current["content"]:
            continue
        changed += 1
        print(f"{'~' if apply else '?'} {repository}: remove stale block")
        if apply:
            if desired:
                put_readme(
                    repository,
                    branch,
                    current["path"],
                    desired,
                    current["sha"],
                    message=REMOVE_MESSAGE,
                )
            else:
                delete_readme(
                    repository,
                    branch,
                    current["path"],
                    current["sha"],
                )
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes; without this flag the command is a dry run",
    )
    parser.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the last verified App Store live snapshot",
    )
    args = parser.parse_args()
    live_keys = live_app_keys(
        APPSTORE,
        PAGES,
        refresh=not args.cached_live,
    )
    changed = sync_readmes(live_keys, apply=args.apply)
    mode = "updated" if args.apply else "would update"
    print(
        f"GitHub support READMEs: {len(live_keys)} live apps, "
        f"{len(desired_blocks(live_keys))} repositories, {changed} {mode}"
    )


if __name__ == "__main__":
    main()
