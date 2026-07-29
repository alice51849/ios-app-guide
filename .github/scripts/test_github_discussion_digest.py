#!/usr/bin/env python3
"""Tests for the locked GitHub Discussion digest publisher."""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import pathlib
import sys
import unittest
import urllib.error
from unittest import mock


HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import github_discussion_digest as digest


SOURCE_SHA = "a" * 40
OLD_SOURCE_SHA = "b" * 40


def item(
    path: str,
    *,
    title: str | None = None,
    summary: str | None = None,
    **extra: object,
) -> dict[str, object]:
    url = f"{digest.SITE_ORIGIN}{path}"
    return {
        "id": url,
        "url": url,
        "title": title or f"Resource {path}",
        "summary": summary or f"Practical material for {path}.",
        "date_modified": "2026-07-29T00:00:00Z",
        **extra,
    }


def feed(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "home_page_url": digest.SITE_HOME,
        "feed_url": digest.SITE_FEED,
        "items": items,
    }


def html_loader(path: str) -> str:
    return f"<html><head><title>{path}</title></head><body>Useful</body></html>"


def discussion(
    rendered: digest.RenderedDigest,
    *,
    source_sha: str | None = None,
    locked: bool = True,
    updated_at: str = "2026-06-01T00:00:00Z",
) -> dict[str, object]:
    canonical = (
        rendered
        if source_sha is None
        else digest.render_digest(rendered.resources, source_sha)
    )
    return {
        "id": "D_kwDOExample",
        "number": 1,
        "title": digest.DISCUSSION_TITLE,
        "body": canonical.body,
        "url": "https://github.com/alice51849/ios-app-guide/discussions/1",
        "locked": locked,
        "updatedAt": updated_at,
        "author": {"login": "github-actions[bot]"},
        "viewerCanUpdate": True,
        "category": {
            "id": "DIC_kwDOAnnouncements",
            "name": digest.CATEGORY_NAME,
            "slug": digest.CATEGORY_SLUG,
            "isAnswerable": False,
        },
        "comments": {"totalCount": 0},
    }


def state(*managed: dict[str, object]) -> digest.RepositoryState:
    return digest.RepositoryState(
        repository_id="R_kwDORepository",
        category_id="DIC_kwDOAnnouncements",
        managed=tuple(managed),
    )


class FeedSelectionTests(unittest.TestCase):
    def test_only_allowlisted_same_site_html_paths_are_selected(self):
        for path in (
            "/ios-app-guide/tools/tool.html",
            "/ios-app-guide/data/data.html",
            "/ios-app-guide/guides/guide.html",
            "/ios-app-guide/apps/app.html",
        ):
            with self.subTest(path=path):
                resources = digest.select_resources(
                    feed([item(path)]),
                    html_loader=html_loader,
                )
                self.assertEqual([f"{digest.SITE_ORIGIN}{path}"], [r.url for r in resources])

        rejected = (
            "http://alice51849.github.io/ios-app-guide/tools/tool.html",
            "https://example.com/ios-app-guide/tools/tool.html",
            f"{digest.SITE_ORIGIN}/ios-app-guide/answers/answer.html",
            f"{digest.SITE_ORIGIN}/ios-app-guide/tools/not-html.json",
            f"{digest.SITE_ORIGIN}/other/tools/tool.html",
        )
        valid = item("/ios-app-guide/tools/valid.html")
        for url in rejected:
            invalid = item("/ios-app-guide/tools/ignored.html")
            invalid["id"] = url
            invalid["url"] = url
            with self.subTest(url=url):
                resources = digest.select_resources(
                    feed([invalid, valid]),
                    html_loader=html_loader,
                )
                self.assertEqual([valid["url"]], [r.url for r in resources])

    def test_query_fragment_and_redirect_documents_are_rejected(self):
        query = item("/ios-app-guide/tools/query.html")
        query["id"] = f"{query['id']}?utm_source=test"
        query["url"] = query["id"]
        fragment = item("/ios-app-guide/guides/fragment.html")
        fragment["id"] = f"{fragment['id']}#section"
        fragment["url"] = fragment["id"]
        redirect = item("/ios-app-guide/data/redirect.html")
        valid = item("/ios-app-guide/apps/valid.html")

        def loader(path: str) -> str:
            if path.endswith("/redirect.html"):
                return '<meta http-equiv="refresh" content="0; url=/elsewhere">'
            return html_loader(path)

        resources = digest.select_resources(
            feed([query, fragment, redirect, valid]),
            html_loader=loader,
        )
        self.assertEqual([valid["url"]], [r.url for r in resources])

    def test_feed_order_deduplication_and_three_item_limit(self):
        first = item("/ios-app-guide/tools/one.html")
        duplicate = copy.deepcopy(first)
        duplicate["title"] = "Duplicate title must not replace first"
        candidates = [
            first,
            duplicate,
            item("/ios-app-guide/data/two.html"),
            item("/ios-app-guide/guides/three.html"),
            item("/ios-app-guide/apps/four.html"),
        ]
        resources = digest.select_resources(
            feed(candidates),
            html_loader=html_loader,
        )
        self.assertEqual(
            [candidates[0]["url"], candidates[2]["url"], candidates[3]["url"]],
            [resource.url for resource in resources],
        )
        self.assertEqual(candidates[0]["title"], resources[0].title)

    def test_timestamp_and_geo_rebuild_fields_do_not_change_digest(self):
        original = feed(
            [
                item(
                    "/ios-app-guide/tools/stable.html",
                    title="Stable title",
                    summary="Stable summary",
                    language="en",
                )
            ]
        )
        rebuilt = copy.deepcopy(original)
        rebuilt["items"][0]["date_modified"] = "2099-01-01T00:00:00Z"
        rebuilt["items"][0]["language"] = "zh-Hant"
        rebuilt["items"][0]["image"] = "https://example.invalid/rebuilt.png"
        first = digest.select_resources(original, html_loader=html_loader)
        second = digest.select_resources(rebuilt, html_loader=html_loader)
        self.assertEqual(digest.content_digest(first), digest.content_digest(second))


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.resources = digest.select_resources(
            feed(
                [
                    item("/ios-app-guide/tools/one.html"),
                    item("/ios-app-guide/data/two.html"),
                    item("/ios-app-guide/guides/three.html"),
                ]
            ),
            html_loader=html_loader,
        )

    def test_sentinel_metadata_round_trip_and_disclosures(self):
        rendered = digest.render_digest(self.resources, SOURCE_SHA)
        metadata = digest.parse_metadata(rendered.body)
        self.assertEqual(digest.FORMAT_VERSION, metadata.version)
        self.assertEqual(rendered.digest, metadata.digest)
        self.assertEqual(SOURCE_SHA, metadata.source_sha)
        self.assertEqual(1, rendered.body.count(digest.SENTINEL))
        self.assertEqual(3, rendered.body.count("https://"))
        self.assertIn("First-party publisher notice", rendered.body)
        self.assertIn("not an independent review", rendered.body)
        self.assertIn("not", rendered.body)
        self.assertIn("ranking", rendered.body)
        self.assertIn("automation", rendered.body)
        self.assertNotIn("@", rendered.body)

    def test_malformed_or_duplicate_sentinel_is_rejected(self):
        rendered = digest.render_digest(self.resources, SOURCE_SHA)
        with self.assertRaises(digest.PublisherError):
            digest.parse_metadata(rendered.body + rendered.body.splitlines()[-1])
        with self.assertRaises(digest.PublisherError):
            digest.parse_metadata(rendered.body.replace("version=1", "version=2"))


class PublisherDecisionTests(unittest.TestCase):
    def setUp(self):
        resources = digest.select_resources(
            feed([item("/ios-app-guide/tools/stable.html")]),
            html_loader=html_loader,
        )
        self.rendered = digest.render_digest(resources, SOURCE_SHA)

    def test_same_digest_is_a_zero_mutation_no_op(self):
        existing = discussion(self.rendered, source_sha=OLD_SOURCE_SHA)
        with (
            mock.patch.object(
                digest,
                "load_repository_state",
                return_value=state(existing),
            ) as load_state,
            mock.patch.object(digest, "_create_discussion") as create,
            mock.patch.object(digest, "_lock_discussion") as lock,
            mock.patch.object(digest, "_update_discussion") as update,
        ):
            result = digest.publish(mock.sentinel.client, self.rendered, bootstrap=False)
        self.assertEqual("no-op", result.action)
        self.assertEqual(1, load_state.call_count)
        create.assert_not_called()
        lock.assert_not_called()
        update.assert_not_called()

    def test_changed_digest_is_deferred_inside_twenty_eight_days(self):
        old_resources = digest.select_resources(
            feed([item("/ios-app-guide/data/old.html")]),
            html_loader=html_loader,
        )
        old = digest.render_digest(old_resources, OLD_SOURCE_SHA)
        existing = discussion(old, updated_at="2026-07-15T00:00:00Z")
        now = dt.datetime(2026, 7, 29, tzinfo=dt.timezone.utc)
        with (
            mock.patch.object(
                digest,
                "load_repository_state",
                return_value=state(existing),
            ),
            mock.patch.object(digest, "_update_discussion") as update,
        ):
            result = digest.publish(
                mock.sentinel.client,
                self.rendered,
                bootstrap=False,
                now=now,
            )
        self.assertEqual("deferred", result.action)
        update.assert_not_called()

    def test_schedule_can_never_request_bootstrap(self):
        with self.assertRaisesRegex(digest.PublisherError, "workflow_dispatch"):
            digest.parse_bootstrap("schedule", "true")
        self.assertFalse(digest.parse_bootstrap("schedule", "false"))
        self.assertTrue(digest.parse_bootstrap("workflow_dispatch", "true"))
        with self.assertRaisesRegex(digest.PublisherError, "explicit boolean"):
            digest.parse_bootstrap("workflow_dispatch", "yes")


class GraphQLSafetyTests(unittest.TestCase):
    class Response:
        status = 200

        def __init__(self, payload: dict[str, object]):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self, _limit: int) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    @staticmethod
    def repository_payload(permission: object) -> dict[str, object]:
        return {
            "repository": {
                "id": "R_kwDORepository",
                "nameWithOwner": digest.NAME_WITH_OWNER,
                "visibility": "PUBLIC",
                "isPrivate": False,
                "isArchived": False,
                "isDisabled": False,
                "hasDiscussionsEnabled": True,
                "viewerPermission": permission,
                "discussionCategories": {
                    "totalCount": 1,
                    "pageInfo": {"hasNextPage": False},
                    "nodes": [
                        {
                            "id": "DIC_kwDOAnnouncements",
                            "name": digest.CATEGORY_NAME,
                            "slug": digest.CATEGORY_SLUG,
                            "isAnswerable": False,
                        }
                    ],
                },
                "discussions": {
                    "totalCount": 0,
                    "pageInfo": {"hasNextPage": False},
                    "nodes": [],
                },
            },
            "rateLimit": {"remaining": 5_000},
        }

    def test_granular_actions_token_read_repository_permission_is_valid(self):
        client = mock.Mock()
        client.execute.return_value = self.repository_payload("READ")
        loaded = digest.load_repository_state(client)
        self.assertEqual("R_kwDORepository", loaded.repository_id)
        self.assertEqual((), loaded.managed)

    def test_null_granular_actions_permission_is_valid(self):
        client = mock.Mock()
        client.execute.return_value = self.repository_payload(None)
        loaded = digest.load_repository_state(client)
        self.assertEqual("R_kwDORepository", loaded.repository_id)

    def test_abnormal_repository_permission_fails_closed(self):
        client = mock.Mock()
        client.execute.return_value = self.repository_payload("OWNER")
        with self.assertRaisesRegex(digest.PublisherError, "viewerPermission"):
            digest.load_repository_state(client)

    def test_mutation_transport_uncertainty_is_never_retried(self):
        rate_limit = self.Response(
            {"data": {"rateLimit": {"remaining": 5_000}}}
        )
        opener = mock.Mock(
            side_effect=(rate_limit, urllib.error.URLError("connection reset"))
        )
        client = digest.GraphQLClient("workflow-token", opener=opener)
        with self.assertRaisesRegex(
            digest.MutationUncertainError,
            "not retried",
        ):
            client.execute(
                "mutation Test { test }",
                {},
                mutation=True,
            )
        self.assertEqual(2, opener.call_count)
        requests = [
            json.loads(call.args[0].data)
            for call in opener.call_args_list
        ]
        self.assertEqual(
            1,
            sum("mutation Test" in request["query"] for request in requests),
        )

    def test_mutation_is_not_sent_at_the_rate_limit_floor(self):
        opener = mock.Mock(
            return_value=self.Response(
                {"data": {"rateLimit": {"remaining": digest.MIN_RATE_LIMIT}}}
            )
        )
        client = digest.GraphQLClient("workflow-token", opener=opener)
        with self.assertRaisesRegex(digest.PublisherError, "reserve was too low"):
            client.execute("mutation Test { test }", {}, mutation=True)
        self.assertEqual(1, opener.call_count)


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (
            HERE.parent.joinpath("workflows", "github-discussion-digest.yml")
            .read_text(encoding="utf-8")
        )

    def test_permissions_concurrency_timeout_and_token_are_fail_closed(self):
        self.assertIn("contents: read", self.workflow)
        self.assertIn("discussions: write", self.workflow)
        self.assertIn("concurrency:", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertIn("timeout-minutes:", self.workflow)
        self.assertIn("${{ github.token }}", self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        self.assertNotRegex(self.workflow.upper(), r"\bPAT\b")

    def test_monthly_cadence_boolean_bootstrap_and_buffered_tests(self):
        cron_lines = [
            line.strip()
            for line in self.workflow.splitlines()
            if "cron:" in line
        ]
        self.assertEqual(['- cron: "17 4 3 * *"'], cron_lines)
        self.assertIn("type: boolean", self.workflow)
        self.assertIn("required: true", self.workflow)
        test_command = (
            "python3 .github/scripts/test_github_discussion_digest.py -q -b"
        )
        publish_command = (
            "python3 .github/scripts/github_discussion_digest.py"
        )
        self.assertIn(test_command, self.workflow)
        self.assertLess(
            self.workflow.index(test_command),
            self.workflow.index(publish_command),
        )


if __name__ == "__main__":
    unittest.main()
