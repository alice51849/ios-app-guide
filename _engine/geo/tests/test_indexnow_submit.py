#!/usr/bin/env python3
"""Tests for strict IndexNow sitemap delivery."""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "indexnow_submit.py"
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
