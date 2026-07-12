#!/usr/bin/env python3
"""Regression tests for Software Heritage repository archiving."""

import datetime as dt
import os
import sys
import unittest
from unittest import mock


HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import software_heritage_archive as archive


def repository(name="awesome-zhuyin-bopomofo-apps", pushed_at="2026-07-12T00:00:00Z"):
    return {
        "name": name,
        "html_url": f"https://github.com/alice51849/{name}",
        "pushed_at": pushed_at,
    }


class RotationTests(unittest.TestCase):
    def test_github_token_is_never_sent_to_software_heritage(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            self.assertEqual(
                "Bearer test-token",
                archive._github_headers()["Authorization"],
            )
            self.assertNotIn("Authorization", archive._swh_headers())

    def test_priority_rotation_starts_with_bopomofo(self):
        repos = [repository(name) for name in archive.PRIORITY]
        selected = archive.select_repository(repos, today=archive.BASE_DATE)
        self.assertEqual("awesome-zhuyin-bopomofo-apps", selected["name"])
        selected = archive.select_repository(
            repos, today=archive.BASE_DATE + dt.timedelta(days=1)
        )
        self.assertEqual("awesome-ios-language-learning", selected["name"])

    def test_override_must_be_in_public_outreach_pool(self):
        repos = [repository("awesome-ios-language-learning")]
        with self.assertRaisesRegex(ValueError, "not in the public outreach pool"):
            archive.select_repository(repos, override="private-app")


class DecisionTests(unittest.TestCase):
    def test_active_request_is_not_duplicated(self):
        should_submit, reason = archive.archive_decision(
            repository(),
            [
                {
                    "id": 123,
                    "save_request_status": "accepted",
                    "save_task_status": "running",
                }
            ],
        )
        self.assertFalse(should_submit)
        self.assertIn("123", reason)

    def test_not_yet_scheduled_request_is_not_duplicated(self):
        should_submit, _ = archive.archive_decision(
            repository(),
            [
                {
                    "id": 124,
                    "save_request_status": "accepted",
                    "save_task_status": "not yet scheduled",
                }
            ],
        )
        self.assertFalse(should_submit)

    def test_current_successful_visit_is_not_duplicated(self):
        should_submit, _ = archive.archive_decision(
            repository(pushed_at="2026-07-12T00:00:00Z"),
            [
                {
                    "save_task_status": "succeeded",
                    "visit_status": "full",
                    "visit_date": "2026-07-12T00:00:01Z",
                }
            ],
        )
        self.assertFalse(should_submit)

    def test_repository_update_after_visit_is_submitted(self):
        should_submit, _ = archive.archive_decision(
            repository(pushed_at="2026-07-12T00:00:01Z"),
            [
                {
                    "save_task_status": "succeeded",
                    "visit_status": "full",
                    "visit_date": "2026-07-12T00:00:00Z",
                }
            ],
        )
        self.assertTrue(should_submit)


class RunTests(unittest.TestCase):
    def test_discovery_reads_every_repository_page(self):
        first_page = [
            {
                "name": f"repo-{index:03}",
                "private": False,
                "archived": False,
            }
            for index in range(100)
        ]
        second_page = [
            {
                **repository(name),
                "private": False,
                "archived": False,
            }
            for name in archive.PRIORITY
        ]
        second_page.append(
            {
                **repository("awesome-new-channel"),
                "private": False,
                "archived": False,
            }
        )
        with mock.patch.object(
            archive,
            "_api_json",
            side_effect=(first_page, second_page),
        ) as api:
            discovered = archive.discover_repositories()
        self.assertEqual(2, api.call_count)
        self.assertIn(
            "awesome-new-channel",
            {str(repo["name"]) for repo in discovered},
        )

    def test_archived_guide_fallback_is_rejected(self):
        archived_guide = {
            "name": "ios-app-guide",
            "private": False,
            "archived": True,
        }
        with (
            mock.patch.object(
                archive,
                "_api_json",
                side_effect=([], archived_guide),
            ),
            self.assertRaisesRegex(
                archive.RequestError, "not public and active"
            ),
        ):
            archive.discover_repositories()

    def test_run_submits_only_the_selected_repository(self):
        repos = [
            repository("awesome-zhuyin-bopomofo-apps"),
            repository("awesome-ios-language-learning"),
        ]
        with (
            mock.patch.object(archive, "discover_repositories", return_value=repos),
            mock.patch.object(archive, "load_requests", return_value=[]),
            mock.patch.object(
                archive,
                "submit",
                return_value={
                    "id": 456,
                    "save_request_status": "accepted",
                    "save_task_status": "pending",
                },
            ) as submit,
        ):
            result = archive.run(today=archive.BASE_DATE)
        self.assertEqual(456, result["id"])
        submit.assert_called_once_with(
            "https://github.com/alice51849/awesome-zhuyin-bopomofo-apps"
        )


if __name__ == "__main__":
    unittest.main()
