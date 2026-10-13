#!/usr/bin/env python3
"""Schema guard for .github/growth/app-improvements.json.

office.cait518.cc renders this file on its promotion page and the daily
patrol rewrites it, so every update must keep the exact shape below.
"""

import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import portfolio_daily  # noqa: E402

PATH = HERE.parent / "growth" / "app-improvements.json"
OWNERS = {"claude", "local", "you"}
STATUSES = {"todo", "in_progress", "done"}
PRIORITIES = {"high", "medium", "low"}
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def validate(document, live_ids):
    problems = []
    if document.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    if not STAMP.fullmatch(str(document.get("updated_at", ""))):
        problems.append("updated_at must be UTC ISO-8601 with Z")
    action_ids = set()

    def check_action(action, where, owner_field=True):
        for field in ("id", "title", "status"):
            if not str(action.get(field) or "").strip():
                problems.append(f"{where}: missing {field}")
        if action.get("id") in action_ids:
            problems.append(f"{where}: duplicate id {action.get('id')}")
        action_ids.add(action.get("id"))
        if action.get("status") not in STATUSES:
            problems.append(f"{where}: bad status {action.get('status')!r}")
        if action.get("status") == "done" and not STAMP.fullmatch(str(action.get("done_at") or "")):
            problems.append(f"{where}: done items need done_at")
        if owner_field and action.get("owner") not in OWNERS:
            problems.append(f"{where}: bad owner {action.get('owner')!r}")
        url = action.get("url")
        if url and not str(url).startswith("https://"):
            problems.append(f"{where}: url must be https")

    for index, action in enumerate(document.get("owner_actions", [])):
        check_action(action, f"owner_actions[{index}]", owner_field=False)
    seen_apps = set()
    for app in document.get("apps", []):
        key = app.get("key")
        where = f"apps[{key}]"
        if key in seen_apps:
            problems.append(f"{where}: duplicate app")
        seen_apps.add(key)
        if str(app.get("app_store_id")) not in live_ids:
            problems.append(f"{where}: app_store_id is not live")
        if app.get("priority") not in PRIORITIES:
            problems.append(f"{where}: bad priority")
        if not str(app.get("headline") or "").strip():
            problems.append(f"{where}: missing headline")
        report = app.get("report_path")
        if report and not (HERE.parents[1] / report).is_file():
            problems.append(f"{where}: report_path missing on disk")
        for index, action in enumerate(app.get("actions", [])):
            check_action(action, f"{where}.actions[{index}]")
    return problems


class AppImprovementsTests(unittest.TestCase):
    def test_validator_rejects_broken_rows(self):
        live = {"6785004775"}
        broken = {
            "schema_version": 1, "updated_at": "2026-10-13T05:00:00Z",
            "owner_actions": [{"id": "a", "title": "x", "status": "done"}],
            "apps": [{"key": "mochi", "app_store_id": "1", "priority": "top", "headline": "",
                      "actions": [{"id": "a", "title": "y", "status": "maybe", "owner": "bot"}]}],
        }
        problems = validate(broken, live)
        for needle in ("done items need done_at", "not live", "bad priority", "missing headline",
                       "duplicate id", "bad status", "bad owner"):
            self.assertTrue(any(needle in p for p in problems), needle)

    def test_published_file_is_valid_when_present(self):
        if not PATH.is_file():
            self.skipTest("app-improvements.json not generated yet")
        live = {app.app_id for app in portfolio_daily.load_public_apps()}
        document = json.loads(PATH.read_text(encoding="utf-8"))
        self.assertEqual([], validate(document, live))


if __name__ == "__main__":
    unittest.main()
