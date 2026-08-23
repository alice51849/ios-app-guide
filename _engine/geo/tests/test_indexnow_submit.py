#!/usr/bin/env python3
"""Tests for strict IndexNow sitemap delivery."""

from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "indexnow_submit.py"


def _site_workflow(name: str) -> str:
    """Read a pages-repo workflow from either engine layout.

    Cloud runs execute this file as ``<site>/_engine/geo/tests/...`` so the
    workflows sit three levels up; the 00_GrowthEngine checkout keeps the site
    in ``geo/pages`` — which is also the path the GEO workflow symlinks
    ``_engine/geo/pages`` to. Probing both keeps one copy of this file valid
    on both sides of the mirror.
    """
    here = Path(__file__).resolve()
    configured = os.environ.get("GEO_GUIDE_ROOT", "").strip()
    candidates = (
        *((Path(configured).expanduser().resolve(),) if configured else ()),
        here.parents[3],
        here.parents[1] / "pages",
    )
    for candidate in candidates:
        path = candidate / ".github" / "workflows" / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise unittest.SkipTest(f"{name} is not reachable from this checkout")
SPEC = importlib.util.spec_from_file_location("indexnow_submit", MODULE_PATH)
indexnow = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(indexnow)


def sitemap(*urls: str) -> str:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<?xml version="1.0"?><urlset>{entries}</urlset>'


class Response:
    def __init__(self, status: int = 200, body: bytes = b"") -> None:
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.body


class IndexNowTests(unittest.TestCase):
    def test_reads_every_unique_subsitemap_url(self) -> None:
        site = "https://example.com/apps"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sitemap_index.xml").write_text(
                sitemap(
                    f"{site}/sitemap-a.xml",
                    f"{site}/sitemap-b.xml",
                ),
                encoding="utf-8",
            )
            (root / "sitemap-a.xml").write_text(
                sitemap(f"{site}/", f"{site}/one.html"),
                encoding="utf-8",
            )
            (root / "sitemap-b.xml").write_text(
                sitemap(f"{site}/one.html", f"{site}/two.html"),
                encoding="utf-8",
            )
            urls = indexnow.read_urls(root, site)
        self.assertEqual(
            [f"{site}/", f"{site}/one.html", f"{site}/two.html"],
            urls,
        )

    def test_reads_localized_sitemaps_even_when_not_in_index(self) -> None:
        site = "https://example.com/apps"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sitemap_index.xml").write_text(
                sitemap(f"{site}/sitemap.xml"),
                encoding="utf-8",
            )
            (root / "sitemap.xml").write_text(
                sitemap(f"{site}/root.html"),
                encoding="utf-8",
            )
            localized = root / "ja"
            localized.mkdir()
            (localized / "sitemap.xml").write_text(
                sitemap(f"{site}/ja/localized.html"),
                encoding="utf-8",
            )
            urls = indexnow.read_urls(root, site)
        self.assertEqual(
            [f"{site}/root.html", f"{site}/ja/localized.html"],
            urls,
        )

    def test_collects_registered_decision_route_sitemap_inventory(self) -> None:
        site = "https://example.com/apps"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decision_urls = [
                f"{site}/apps/app-{number}/decision/l/en-US/index.html"
                for number in range(1600)
            ]
            asset_urls = [
                f"{site}/data/app-install-decision-routes.json",
                f"{site}/data/app-install-decision-routes.schema.json",
                *[
                    f"{site}/data/app-install-decision-routes/locales/"
                    f"locale-{number}.json"
                    for number in range(50)
                ],
            ]
            (root / "sitemap_index.xml").write_text(
                sitemap(
                    f"{site}/sitemap.xml",
                    f"{site}/sitemap_app_install_decisions.xml",
                ),
                encoding="utf-8",
            )
            baseline = [
                f"{site}/existing/{number}.html" for number in range(14_891)
            ]
            (root / "sitemap.xml").write_text(
                sitemap(*baseline),
                encoding="utf-8",
            )
            (root / "sitemap_app_install_decisions.xml").write_text(
                sitemap(*decision_urls, *asset_urls),
                encoding="utf-8",
            )
            urls = indexnow.read_urls(root, site)
        self.assertEqual(14_891 + 1_600 + 52, len(urls))
        self.assertEqual(1_600, sum("/decision/l/" in url for url in urls))
        self.assertEqual(
            52,
            sum(
                "app-install-decision-routes" in url and "/decision/l/" not in url
                for url in urls
            ),
        )
        self.assertEqual(decision_urls[0], urls[14_891])
        self.assertEqual(asset_urls[-1], urls[-1])

    def test_rejects_foreign_or_tracking_urls(self) -> None:
        site = "https://example.com/apps"
        for url in (
            "https://other.example/apps/one.html",
            "https://example.com/apps/one.html?tracking=1",
            "https://example.com/outside.html",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                indexnow.validate_public_url(url, site)

    def test_excludes_and_reports_same_host_url_outside_key_scope(self) -> None:
        site = "https://example.com/apps"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sitemap.xml").write_text(
                sitemap(
                    f"{site}/one.html",
                    "https://example.com/.well-known/resourcesync",
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with mock.patch("sys.stdout", output):
                urls = indexnow.read_urls(root, site)
        self.assertEqual([f"{site}/one.html"], urls)
        self.assertIn("excluded_out_of_scope=1", output.getvalue())

    def test_foreign_sitemap_url_still_fails(self) -> None:
        site = "https://example.com/apps"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sitemap.xml").write_text(
                sitemap(
                    f"{site}/one.html",
                    "https://other.example/apps/two.html",
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                indexnow.read_urls(root, site)

    def test_reads_net_change_set_from_first_parent_baseline(self) -> None:
        runner = mock.Mock(
            side_effect=[
                SimpleNamespace(stdout="base-sha\n"),
                SimpleNamespace(
                    stdout=(
                        "one.html\0"
                        "nested/two.html\0"
                        "one.html\0"
                        "gone.html\0"
                    )
                ),
            ]
        )
        baseline, paths = indexnow.git_change_set(
            Path("/tmp/site"),
            "25 hours ago",
            runner=runner,
        )
        self.assertEqual("base-sha", baseline)
        self.assertEqual(
            [
                Path("gone.html"),
                Path("nested/two.html"),
                Path("one.html"),
            ],
            paths,
        )
        baseline_command = runner.call_args_list[0].args[0]
        self.assertIn("--first-parent", baseline_command)
        self.assertIn("--before=25 hours ago", baseline_command)
        diff_command = runner.call_args_list[1].args[0]
        self.assertIn("base-sha..HEAD", diff_command)
        self.assertIn("--no-renames", diff_command)

    def test_changed_urls_include_only_indexed_files_and_public_deletions(
        self,
    ) -> None:
        site = "https://example.com/apps"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / ".well-known").mkdir()
            (root / "one.html").write_text("one", encoding="utf-8")
            (root / ".well-known" / "api-catalog").write_text(
                "catalog",
                encoding="utf-8",
            )
            (root / "nested" / "index.html").write_text(
                "nested",
                encoding="utf-8",
            )
            (root / "unlisted.html").write_text("private", encoding="utf-8")
            (root / "sitemap.xml").write_text(
                sitemap(
                    f"{site}/.well-known/api-catalog",
                    f"{site}/one.html",
                    f"{site}/nested/",
                ),
                encoding="utf-8",
            )
            urls = indexnow.changed_urls(
                root,
                site,
                [
                    Path(".github/workflows/deploy.yml"),
                    Path("_engine/private.py"),
                    Path(".well-known/api-catalog"),
                    Path("archive.zip"),
                    Path("gone.jsonld"),
                    Path("nested/index.html"),
                    Path("one.html"),
                    Path("styles.css"),
                    Path("unlisted.html"),
                ],
                previous_urls=[
                    f"{site}/archive.zip",
                    f"{site}/gone.jsonld",
                ],
            )
        self.assertEqual(
            [
                f"{site}/.well-known/api-catalog",
                f"{site}/archive.zip",
                f"{site}/gone.jsonld",
                f"{site}/nested/",
                f"{site}/one.html",
            ],
            urls,
        )

    def test_incremental_reader_reports_empty_public_change_set(self) -> None:
        site = "https://example.com/apps"
        runner = mock.Mock(
            side_effect=[
                SimpleNamespace(stdout="base-sha\n"),
                SimpleNamespace(stdout="_engine/private.py\0"),
                SimpleNamespace(
                    stdout=f"<loc>{site}/one.html</loc>\n",
                    stderr="",
                    returncode=0,
                    args=["git", "grep"],
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sitemap.xml").write_text(
                sitemap(f"{site}/one.html"),
                encoding="utf-8",
            )
            urls = indexnow.read_changed_urls(
                root,
                site,
                "25 hours ago",
                runner=runner,
            )
        self.assertEqual([], urls)

    def test_successful_sha_is_durable_and_same_sha_replay_is_zero(self) -> None:
        site = "https://example.com/apps"
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key_file = root / "indexnow-key.txt"
            key_file.write_text("valid-key-123", encoding="utf-8")
            state_file = root / "state" / "last-submitted-sha"
            runner = mock.Mock(
                return_value=SimpleNamespace(stdout=f"{sha}\n")
            )
            sender = mock.Mock()
            with mock.patch.object(
                indexnow,
                "read_changed_urls",
                return_value=[f"{site}/one.html"],
            ):
                accepted = indexnow.run(
                    root,
                    site,
                    key_file,
                    git_since="25 hours ago",
                    state_file=state_file,
                    runner=runner,
                    sender=sender,
                )
            self.assertEqual(1, accepted)
            self.assertEqual(2, sender.call_count)
            self.assertEqual(sha, state_file.read_text(encoding="utf-8").strip())

            sender.reset_mock()
            output = io.StringIO()
            with mock.patch("sys.stdout", output):
                accepted = indexnow.run(
                    root,
                    site,
                    key_file,
                    git_since="25 hours ago",
                    state_file=state_file,
                    runner=runner,
                    sender=sender,
                )
        self.assertEqual(0, accepted)
        sender.assert_not_called()
        self.assertIn("changed_public_urls=0", output.getvalue())
        self.assertIn("nothing to submit", output.getvalue())

    def test_durable_sha_replaces_the_time_window_baseline(self) -> None:
        site = "https://example.com/apps"
        previous_sha = "a" * 40
        current_sha = "b" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "state" / "last-submitted-sha"
            indexnow.write_last_submitted_sha(state_file, previous_sha)
            reader = mock.Mock(return_value=[])
            runner = mock.Mock(
                return_value=SimpleNamespace(stdout=f"{current_sha}\n")
            )
            with mock.patch.object(indexnow, "read_changed_urls", reader):
                accepted = indexnow.run(
                    root,
                    site,
                    root / "unused-key.txt",
                    git_since="25 hours ago",
                    state_file=state_file,
                    runner=runner,
                )
            self.assertEqual(
                current_sha,
                state_file.read_text(encoding="utf-8").strip(),
            )
        self.assertEqual(0, accepted)
        reader.assert_called_once_with(
            root,
            site,
            "25 hours ago",
            baseline_sha=previous_sha,
            runner=runner,
        )

    def test_failed_delivery_does_not_advance_submission_sha(self) -> None:
        site = "https://example.com/apps"
        sha = "b" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key_file = root / "indexnow-key.txt"
            key_file.write_text("valid-key-123", encoding="utf-8")
            state_file = root / "state" / "last-submitted-sha"
            with (
                mock.patch.object(
                    indexnow,
                    "read_changed_urls",
                    return_value=[f"{site}/one.html"],
                ),
                self.assertRaises(indexnow.SubmissionError),
            ):
                indexnow.run(
                    root,
                    site,
                    key_file,
                    git_since="25 hours ago",
                    state_file=state_file,
                    runner=mock.Mock(
                        return_value=SimpleNamespace(stdout=f"{sha}\n")
                    ),
                    sender=mock.Mock(
                        side_effect=indexnow.SubmissionError("offline")
                    ),
                )
            self.assertFalse(state_file.exists())

    def test_workflow_waits_for_exact_pages_deployment(self) -> None:
        workflow = _site_workflow("indexnow-daily.yml")
        pages_workflow = _site_workflow("pages.yml")
        self.assertIn(
            'workflows: ["Deploy static site to Pages"]',
            workflow,
        )
        self.assertIn(
            "github.event.workflow_run.conclusion == 'success'",
            workflow,
        )
        self.assertIn(".well-known/deployment.json", workflow)
        self.assertIn('git checkout --detach "$deployed_sha"', workflow)
        self.assertIn("live_app_guard.py --site-root .", workflow)
        self.assertIn("actions/cache/restore@v4", workflow)
        self.assertIn("actions/cache/save@v4", workflow)
        self.assertIn('--state-file "$state_file"', workflow)
        self.assertIn("Write immutable deployment manifest", pages_workflow)
        self.assertIn("Verify exact deployment is live", pages_workflow)
        self.assertIn("steps.verify_live.outcome == 'success'", pages_workflow)

    def test_local_burst_refuses_unpublished_or_dirty_tree(self) -> None:
        script = MODULE_PATH.with_name("promo_burst.sh")
        if not script.is_file():
            raise unittest.SkipTest("promo_burst.sh is canonical-only")
        source = script.read_text(encoding="utf-8")
        self.assertIn("LIVE_SHA", source)
        self.assertIn("unsafe unpublished tree", source)
        self.assertIn('--pages-dir "$PAGES"', source)

    def test_submit_all_requires_every_endpoint_and_chunks_safely(self) -> None:
        calls: list[tuple[str, int]] = []

        def sender(endpoint: str, payload: bytes) -> None:
            calls.append((endpoint, len(payload)))

        urls = [
            f"https://example.com/apps/{number}.html"
            for number in range(2501)
        ]
        accepted = indexnow.submit_all(
            urls,
            "abcdefgh",
            "https://example.com/apps",
            batch_size=1000,
            endpoints=("first", "second"),
            sender=sender,
        )
        self.assertEqual(2501, accepted)
        self.assertEqual(
            ["first", "second"] * 3,
            [endpoint for endpoint, _ in calls],
        )

    def test_default_batch_covers_portfolio_in_two_requests_per_endpoint(
        self,
    ) -> None:
        calls = []

        def sender(endpoint: str, _payload: bytes) -> None:
            calls.append(endpoint)

        urls = [
            f"https://example.com/apps/{number}.html"
            for number in range(14_891)
        ]
        accepted = indexnow.submit_all(
            urls,
            "abcdefgh",
            "https://example.com/apps",
            endpoints=("first", "second"),
            sender=sender,
        )

        self.assertEqual(len(urls), accepted)
        self.assertEqual(["first", "second"] * 2, calls)

    def test_endpoint_request_timeout_is_bounded(self) -> None:
        opener = mock.Mock(return_value=Response(202))

        indexnow.submit_endpoint(
            "https://api.example",
            b"{}",
            opener=opener,
            sleeper=lambda _delay: None,
        )

        self.assertEqual(
            indexnow.REQUEST_TIMEOUT_SECONDS,
            opener.call_args.kwargs["timeout"],
        )
        self.assertEqual(30, indexnow.REQUEST_TIMEOUT_SECONDS)

    def test_nonretryable_http_error_fails_immediately_with_body(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.example",
            422,
            "Unprocessable",
            {},
            io.BytesIO(b"invalid URL"),
        )
        opener = mock.Mock(side_effect=error)
        with self.assertRaisesRegex(
            indexnow.SubmissionError, "422: invalid URL"
        ):
            indexnow.submit_endpoint(
                "https://api.example",
                b"{}",
                opener=opener,
                sleeper=lambda _delay: None,
            )
        self.assertEqual(1, opener.call_count)

    def test_transient_http_error_retries_then_succeeds(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.example",
            503,
            "Unavailable",
            {},
            io.BytesIO(b"retry"),
        )
        opener = mock.Mock(side_effect=[error, Response(202)])
        indexnow.submit_endpoint(
            "https://api.example",
            b"{}",
            opener=opener,
            sleeper=lambda _delay: None,
        )
        self.assertEqual(2, opener.call_count)

    def test_compatibility_submit_tries_every_endpoint(self) -> None:
        calls = []

        def sender(endpoint: str, _payload: bytes) -> None:
            calls.append(endpoint)
            raise indexnow.SubmissionError("offline")

        accepted = indexnow.submit(
            ["https://example.com/apps/one.html"],
            "abcdefgh",
            "https://example.com/apps",
            endpoints=("first", "second"),
            sender=sender,
        )
        self.assertFalse(accepted)
        self.assertEqual(["first", "second"], calls)


if __name__ == "__main__":
    unittest.main()
