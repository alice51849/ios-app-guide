#!/usr/bin/env python3
"""Sync searchable GitHub metadata for repositories representing live apps."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))

from videogen.registry import APPS, APPSTORE  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402

OWNER = "alice51849"
PAGES = os.path.join(HERE, "pages")
TOPIC_LIMIT = 15
TOPIC_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BASE_TOPICS = ("ios", "iphone", "ios-app", "app-support", "privacy")
REPO_OVERRIDES = {
    "lumibopomofo": "lumi-support",
    "lumibopomofopro": "lumi-support",
    "lumiletters": "lumi-letters-support",
    "lumiletterspro": "lumi-letters-support",
    "lumimath": "lumi-math-support",
    "lumimathpro": "lumi-math-support",
    "lumimission": "lumi-mission-support",
    "lumimissionpro": "lumi-mission-support",
    "lumiweather": "lumi-weather-support",
    "mochi": "mochitodo-support",
    "sononote": "sono-note-support",
}
KEYWORD_DISPLAY = {
    "abc for kids": "ABC learning for kids",
    "ai upscale": "AI upscaling",
    "ats resume": "ATS resume",
    "bopomofo": "Bopomofo",
    "cv maker": "CV maker",
    "id photo": "ID photo",
    "learn chinese for kids": "Chinese learning for kids",
    "pdf scanner": "PDF scanner",
    "toeic": "TOEIC",
    "toeic lr": "TOEIC L&R",
    "toeic prep": "TOEIC prep",
    "zhuyin": "Zhuyin",
}
GUIDE_REPOSITORY = "ios-app-guide"
GUIDE_METADATA = {
    "description": (
        "Independent iOS app guides, comparisons, practical tools and open "
        "datasets for kids learning, productivity, photo, travel and privacy."
    ),
    "homepage": "https://alice51849.github.io/ios-app-guide/",
    "topics": (
        "ios",
        "iphone",
        "ios-apps",
        "app-directory",
        "app-guides",
        "privacy",
        "kids-learning",
        "productivity",
        "photo-tools",
        "travel-apps",
        "bopomofo",
        "zhuyin",
    ),
}


def topic_slug(value):
    normalized = unicodedata.normalize("NFKD", value).encode(
        "ascii", "ignore"
    ).decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized[:50].rstrip("-")


def repository_for_app(key):
    return REPO_OVERRIDES.get(key, f"{topic_slug(key)}-support")


def group_apps_by_repository(live_keys):
    live_keys = set(live_keys)
    unknown = live_keys - set(APPS)
    if unknown:
        raise ValueError(f"live apps missing from registry: {sorted(unknown)}")
    grouped = defaultdict(list)
    for key in sorted(live_keys):
        grouped[repository_for_app(key)].append(key)
    return dict(sorted(grouped.items()))


def _round_robin_keywords(keys):
    keyword_lists = [APPS[key].get("keywords", ()) for key in keys]
    for index in range(max((len(items) for items in keyword_lists), default=0)):
        for items in keyword_lists:
            if index < len(items):
                yield items[index]


def topics_for_apps(keys):
    topics = []
    candidates = [
        *BASE_TOPICS,
        *(APPS[key]["category"] for key in keys),
        *_round_robin_keywords(keys),
    ]
    for candidate in candidates:
        topic = topic_slug(candidate)
        if topic and topic not in topics:
            if not TOPIC_PATTERN.fullmatch(topic):
                raise ValueError(f"invalid GitHub topic: {topic}")
            topics.append(topic)
        if len(topics) >= TOPIC_LIMIT:
            break
    return tuple(topics)


def description_for_apps(keys):
    names = [APPS[key]["name"] for key in keys]
    if len(names) == 1:
        subject = names[0]
    else:
        subject = ", ".join(names[:-1]) + f" and {names[-1]}"
    keywords = []
    for value in _round_robin_keywords(keys):
        if value not in keywords:
            keywords.append(value)
        if len(keywords) == 3:
            break
    keywords = [KEYWORD_DISPLAY.get(value, value) for value in keywords]
    if len(keywords) == 1:
        detail = keywords[0]
    elif len(keywords) == 2:
        detail = " and ".join(keywords)
    else:
        detail = ", ".join(keywords[:-1]) + f", and {keywords[-1]}"
    description = (
        f"Official support and privacy resources for {subject}, covering "
        f"{detail}."
    )
    if len(description) > 350:
        raise ValueError(f"repository description is too long: {description}")
    return description


def desired_repositories(live_keys):
    desired = {GUIDE_REPOSITORY: GUIDE_METADATA}
    for repository, keys in group_apps_by_repository(live_keys).items():
        desired[repository] = {
            "description": description_for_apps(keys),
            "homepage": f"https://{OWNER}.github.io/{repository}/",
            "topics": topics_for_apps(keys),
        }
    return dict(sorted(desired.items()))


def metadata_changes(current, desired):
    changes = {}
    for field in ("description", "homepage"):
        if (current.get(field) or "") != desired[field]:
            changes[field] = desired[field]
    if set(current.get("topics") or ()) != set(desired["topics"]):
        changes["topics"] = tuple(desired["topics"])
    return changes


def gh_api(arguments, payload=None):
    command = ["gh", "api", *arguments]
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"{' '.join(command)} failed: {result.stderr.strip()}"
        )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def sync_repositories(desired, apply=False):
    changed = 0
    for repository, metadata in desired.items():
        endpoint = f"repos/{OWNER}/{repository}"
        current = gh_api([endpoint])
        if current.get("private") or current.get("archived"):
            raise RuntimeError(
                f"refusing non-public or archived repository: {repository}"
            )
        changes = metadata_changes(current, metadata)
        if not changes:
            print(f"= {repository}: already current")
            continue
        changed += 1
        print(
            f"{'~' if apply else '?'} {repository}: "
            + ", ".join(sorted(changes))
        )
        if not apply:
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
            continue
        if "description" in changes or "homepage" in changes:
            gh_api(
                [
                    "--method",
                    "PATCH",
                    endpoint,
                    "-f",
                    f"description={metadata['description']}",
                    "-f",
                    f"homepage={metadata['homepage']}",
                ]
            )
        if "topics" in changes:
            gh_api(
                [
                    "--method",
                    "PUT",
                    f"{endpoint}/topics",
                    "--input",
                    "-",
                ],
                {"names": list(metadata["topics"])},
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
    desired = desired_repositories(live_keys)
    changed = sync_repositories(desired, apply=args.apply)
    mode = "updated" if args.apply else "would update"
    print(
        f"GitHub repository metadata: {len(live_keys)} live apps, "
        f"{len(desired)} repositories, {changed} {mode}"
    )


if __name__ == "__main__":
    main()
