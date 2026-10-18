#!/usr/bin/env python3
"""Loud reminder when a Guide commit moves Finder fields that threads-autopilot syncs.

threads-autopilot's ``sync_live_apps.py`` reads ``data/verified-ios-app-finder-catalog.json``
from the live Guide and turns every App's English summary, purchase label, features,
keywords, capabilities, category and purchase model into its ``apps.json``; the TA content
seal (``PUBLISHER_REVIEWED_SOURCE_DIGEST`` in verified_content.py) covers what that
produces. On 10-17 Guide 4e6b15afc0 regenerated the catalogue, 5 Apps' summaries moved,
the seal no longer matched and Threads missed the 23 and 01 UTC slots unnoticed.

This compares exactly those fields between two versions of the catalogue (HEAD against the
staged index by default), prints a ``::warning::`` naming the Apps and fields, and can
write a commit-message paragraph. Not every moved field changes the seal; threads-autopilot's
seal-watch job (multi.yml, every ~30 min) confirms and opens the issue "TA 需要重封".
It never blocks the Guide publish: every failure is reported and the exit code is 0.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FINDER = "data/verified-ios-app-finder-catalog.json"
# Mirrors threads-autopilot sync_live_apps._parse_finder_profiles (keep in step with it).
TA_FIELDS = (
    "name", "category", "purchase_model", "app_store_id", "canonical_app_store_url",
    "one_time_option", "verified_live", "summaries.en", "purchase_labels.en",
    "features", "keywords", "capabilities",
)
TA_CATALOG_FIELDS = ("record_count", "publisher_disclosure")


def _get(item: object, dotted: str) -> object:
    for part in dotted.split("."):
        item = item.get(part) if isinstance(item, dict) else None
    return item


def projection(document: object) -> dict[str, dict[str, object]]:
    """What threads-autopilot reads from the catalogue, per App key (plus ``_catalog``)."""
    if not isinstance(document, dict):
        return {}
    out: dict[str, dict[str, object]] = {"_catalog": {field: document.get(field) for field in TA_CATALOG_FIELDS}}
    for item in document.get("apps") or []:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            out[item["key"]] = {field: _get(item, field) for field in TA_FIELDS}
    return out


def changes(before: object, after: object) -> list[tuple[str, list[str]]]:
    old, new = projection(before), projection(after)
    rows = []
    for key in [*new, *[key for key in old if key not in new]]:
        if key not in old:
            rows.append((key, ["(新增)"]))
        elif key not in new:
            rows.append((key, ["(移除)"]))
        else:
            fields = [field for field in old[key] if old[key].get(field) != new[key].get(field)]
            if fields:
                rows.append((key, fields))
    return rows


def describe(rows: list[tuple[str, list[str]]], limit: int = 12) -> str:
    text = "、".join(f"{key} {'/'.join(fields)}" for key, fields in rows[:limit])
    return text + (f" 等 {len(rows)} 款" if len(rows) > limit else "")


def notice(rows: list[tuple[str, list[str]]]) -> tuple[str, str]:
    """(::warning:: line for the log, paragraph for the commit message)."""
    apps = describe(rows)
    warning = (
        f"::warning title=TA 需要排重封::{FINDER} 改了 threads-autopilot 會同步的欄位（{apps}）。"
        "上線後 TA 的 sync_live_apps.py 會把它帶進 apps.json；內容封印 PUBLISHER_REVIEWED_SOURCE_DIGEST "
        "對不上時 Threads／Bluesky／Nostr 整天發不出去，請排 TA 重封（第二模型複審後才重釘）。"
        "TA multi.yml 的 seal-watch 每 30 分鐘比對，對不上會開 issue「TA 需要重封」並發 Telegram。"
        "這只是提醒，不擋 Guide 發布。"
    )
    trailer = (
        f"TA-reseal: 這個 commit 改了 threads-autopilot 會同步的 finder 欄位（{apps}）；"
        "上線後要排 TA 重封（threads-autopilot seal-watch 會開 issue「TA 需要重封」）。"
    )
    return warning, trailer


def git_json(root: Path, spec: str) -> object | None:
    done = subprocess.run(["git", "-C", str(root), "show", spec], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=60)
    if done.returncode != 0:
        return None
    return json.loads(done.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--staged", action="store_true", help="compare HEAD with the staged index (default)")
    parser.add_argument("--from-rev", help="compare this revision ...")
    parser.add_argument("--to-rev", help="... with this one")
    parser.add_argument("--trailer-file", type=Path, help="write the commit-message paragraph here (empty when none)")
    args = parser.parse_args(argv)
    trailer = ""
    try:
        if args.from_rev and args.to_rev:
            before, after = git_json(args.root, f"{args.from_rev}:{FINDER}"), git_json(args.root, f"{args.to_rev}:{FINDER}")
        else:
            before, after = git_json(args.root, f"HEAD:{FINDER}"), git_json(args.root, f":{FINDER}")
        rows = changes(before, after) if after is not None else []
        if rows:
            warning, trailer = notice(rows)
            print(warning)
        else:
            print(f"ta-finder-notice: {FINDER} 沒有改到 threads-autopilot 會同步的欄位")
    except Exception as error:  # noqa: BLE001 - a reminder must never block the Guide publish
        print(f"::warning title=TA finder 提醒失敗::{type(error).__name__}: {error}"[:300])
    if args.trailer_file:
        try:
            args.trailer_file.write_text(trailer, encoding="utf-8")
        except OSError as error:
            print(f"::warning title=TA finder 提醒失敗::{type(error).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
