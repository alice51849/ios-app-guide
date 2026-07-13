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
