#!/usr/bin/env python3
"""Regression tests for daily Arquivo.pt live guide archiving."""

import datetime as dt
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock


HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import arquivo_pt_archive as archive


def candidate(slug: str) -> dict[str, str]:
    return {
        "slug": slug,
        "name": slug.title(),
        "canonical_url": f"{archive.SITE}/guides/{slug}.html",
        "archive_url": f"{archive.SITE}/guides/{slug}.html",
    }


class FakeResponse:
    def __init__(self, body: str, url: str):
        self.body = body.encode()
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int) -> bytes:
        return self.body[:limit]

    def geturl(self) -> str:
        return self.url


class CandidateTests(unittest.TestCase):
    def test_repository_linkset_is_fully_represented(self):
        with archive.LINKSET_PATH.open(encoding="utf-8") as handle:
            source = archive._guide_entry(json.load(handle))["item"]
        candidates = archive.load_candidates()
        self.assertEqual(len(source), len(candidates))
        self.assertEqual(len(candidates), len({item["slug"] for item in candidates}))

    def test_portuguese_guide_is_preferred_with_english_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "guides").mkdir()
            (root / "pt-BR" / "guides").mkdir(parents=True)
            for slug in ("local", "fallback"):
                (root / "guides" / f"{slug}.html").write_text("", encoding="utf-8")
            (root / "pt-BR" / "guides" / "local.html").write_text(
                "", encoding="utf-8"
            )
            payload = {
                "linkset": [
                    {
                        "anchor": f"{archive.SITE}/index.html",
                        "item": [
                            {
                                "href": f"{archive.SITE}/guides/{slug}.html",
                                "title*": [{"value": slug.title(), "language": "en"}],
                            }
                            for slug in ("local", "fallback")
                        ],
                    }
                ]
            }
            linkset = root / "linkset.json"
            linkset.write_text(json.dumps(payload), encoding="utf-8")
            candidates = archive.load_candidates(
                linkset_path=linkset,
                root=root,
            )
        self.assertIn("/pt-BR/", candidates[0]["archive_url"])
        self.assertEqual(candidates[1]["canonical_url"], candidates[1]["archive_url"])

    def test_external_guide_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            linkset = root / "linkset.json"
            linkset.write_text(
                json.dumps(
                    {
                        "linkset": [
                            {
                                "anchor": f"{archive.SITE}/",
                                "item": [
                                    {
                                        "href": "https://example.com/guide.html",
                                        "title*": [{"value": "External"}],
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "outside the public guide"):
                archive.load_candidates(linkset_path=linkset, root=root)

    def test_rotation_is_fair_and_repeats_after_full_cycle(self):
        candidates = [candidate(slug) for slug in ("one", "two", "three")]
        selected = [
            archive.select_candidate(
                candidates,
                today=archive.BASE_DATE + dt.timedelta(days=offset),
            )["slug"]
            for offset in range(4)
        ]
        self.assertEqual(["one", "two", "three", "one"], selected)

    def test_override_must_be_a_live_app(self):
        with self.assertRaisesRegex(ValueError, "not in the live guide pool"):
            archive.select_candidate([candidate("live")], override="retired")


class CaptureTests(unittest.TestCase):
    def test_recent_successful_capture_is_detected(self):
        body = "\n".join(
            (
                json.dumps(
                    {
                        "timestamp": "20260711010203",
                        "status": "200",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "20260712010203",
                        "status": "404",
                    }
                ),
            )
        )
        response = FakeResponse(body, archive.CDX_API)
        latest = archive.recent_capture(
            f"{archive.SITE}/guides/live.html",
            today=dt.date(2026, 7, 12),
            opener=mock.Mock(return_value=response),
            sleeper=mock.Mock(),
        )
        self.assertEqual("2026-07-11T01:02:03+00:00", latest.isoformat())

    def test_invalid_cdx_line_fails_closed(self):
        with self.assertRaisesRegex(archive.RequestError, "invalid NDJSON"):
            archive._parse_cdx("{invalid")

    def test_capture_response_must_identify_target(self):
        response = FakeResponse("unexpected page", archive.CAPTURE_API)
        with self.assertRaisesRegex(archive.RequestError, "identify the target"):
            archive.capture_page(
                f"{archive.SITE}/guides/live.html",
                opener=mock.Mock(return_value=response),
                sleeper=mock.Mock(),
            )

    def test_transient_capture_error_is_retried(self):
        target = f"{archive.SITE}/guides/live.html"
        error = urllib.error.HTTPError(
            archive.CAPTURE_API,
            429,
            "rate limited",
            {},
            io.BytesIO(b"rate limited"),
        )
        response = FakeResponse(target, archive.CAPTURE_API + target)
        opener = mock.Mock(side_effect=(error, response))
        sleeper = mock.Mock()
        result = archive.capture_page(target, opener=opener, sleeper=sleeper)
        self.assertTrue(result.startswith(archive.CAPTURE_API))
        self.assertEqual(2, opener.call_count)
        sleeper.assert_called_once_with(20)

    def test_run_skips_recent_capture(self):
        live = candidate("live")
        with (
            mock.patch.object(archive, "load_candidates", return_value=[live]),
            mock.patch.object(
                archive,
                "recent_capture",
                return_value=dt.datetime(2026, 7, 12, tzinfo=dt.timezone.utc),
            ),
            mock.patch.object(archive, "validate_url") as validate,
            mock.patch.object(archive, "capture_page") as capture,
        ):
            result = archive.run(today=archive.BASE_DATE)
        self.assertIsNone(result)
        validate.assert_not_called()
        capture.assert_not_called()

    def test_cooldown_never_blocks_the_next_full_rotation(self):
        candidates = [candidate(slug) for slug in ("one", "two", "three")]
        with (
            mock.patch.object(archive, "load_candidates", return_value=candidates),
            mock.patch.object(archive, "recent_capture", return_value=None) as recent,
            mock.patch.object(archive, "validate_url", return_value=True),
            mock.patch.object(
                archive,
                "capture_page",
                return_value=archive.CAPTURE_API,
            ),
        ):
            archive.run(today=archive.BASE_DATE)
        recent.assert_called_once_with(
            candidates[0]["archive_url"],
            today=archive.BASE_DATE,
            cooldown_days=2,
        )

    def test_run_validates_then_captures_selected_guide(self):
        live = candidate("live")
        with (
            mock.patch.object(archive, "load_candidates", return_value=[live]),
            mock.patch.object(archive, "recent_capture", return_value=None),
            mock.patch.object(archive, "validate_url", return_value=True) as validate,
            mock.patch.object(
                archive,
                "capture_page",
                return_value=archive.CAPTURE_API + live["archive_url"],
            ) as capture,
        ):
            result = archive.run(today=archive.BASE_DATE)
        self.assertIsNotNone(result)
        validate.assert_called_once_with(
            live["archive_url"],
            timeout=30,
            attempts=3,
            retry_delays=(10, 30),
        )
        capture.assert_called_once_with(live["archive_url"])


if __name__ == "__main__":
    unittest.main()
