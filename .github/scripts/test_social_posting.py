#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the social posting automations."""

import datetime as dt
import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import devto_post
import social_post_common as common
import telegram_post
import threads_post


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def http_error(status, body=b""):
    return urllib.error.HTTPError(
        "https://example.com/item",
        status,
        "error",
        {},
        io.BytesIO(body),
    )


class RotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(
            os.path.join(HERE, "telegram_posts.json"), encoding="utf-8"
        ) as pool_file:
            cls.pool = json.load(pool_file)

    def _at(self, day, hour):
        return dt.datetime(2026, 1, 1, hour, tzinfo=dt.timezone.utc) + dt.timedelta(
            days=day
        )

    def test_every_route_completes_its_full_daily_cycle(self):
        routes = (
            (telegram_post.pick, 1, telegram_post.TZ_LANGS["asia"]),
            (telegram_post.pick, 9, telegram_post.TZ_LANGS["eu_me"]),
            (telegram_post.pick, 15, telegram_post.TZ_LANGS["americas"]),
            (threads_post.pick, 3, threads_post.TZ_LANGS["asia"]),
            (threads_post.pick, 14, threads_post.TZ_LANGS["west"]),
        )
        for picker, hour, languages in routes:
            expected_size = sum(
                item.get("lang") in languages for item in self.pool
            )
            with self.subTest(hour=hour, expected_size=expected_size):
                picks = [
                    picker(self.pool, self._at(day, hour))
                    for day in range(expected_size)
                ]
                self.assertEqual(
                    expected_size,
                    len({common.item_key(item) for item in picks}),
                )
                self.assertTrue(all(item["lang"] in languages for item in picks))

    def test_all_channels_choose_different_items_on_the_same_day(self):
        for day in range(400):
            picks = (
                telegram_post.pick(self.pool, self._at(day, 1)),
                threads_post.pick(self.pool, self._at(day, 3)),
                telegram_post.pick(self.pool, self._at(day, 9)),
                threads_post.pick(self.pool, self._at(day, 14)),
                telegram_post.pick(self.pool, self._at(day, 15)),
            )
            self.assertEqual(5, len({common.item_key(item) for item in picks}))


class FooterAndSelectionTests(unittest.TestCase):
    def test_every_supported_language_has_its_own_footer(self):
        expected_languages = {
            "en",
            "zh-Hant",
            "zh-Hans",
            "ja",
            "ko",
            "ms",
            "de",
            "fr",
            "es",
            "pt-BR",
            "ru",
            "ar",
            "pl",
        }
        self.assertEqual(expected_languages, set(common.FOOTERS))
        self.assertEqual(len(common.FOOTERS), len(set(common.FOOTERS.values())))
        for lang in expected_languages:
            with self.subTest(lang=lang):
                item = {
                    "lang": lang,
                    "text": "Quality copy",
                    "url": "https://example.com/app",
                }
                footer = common.footer_for(lang)
                self.assertTrue(telegram_post.compose_text(item).endswith(footer))
                self.assertTrue(threads_post.compose_text(item).endswith(footer))
                if not lang.startswith("zh-"):
                    self.assertNotIn("獨立開發者", footer)
                    self.assertNotIn("買斷", footer)
                    self.assertNotIn("訂閱", footer)

    def test_confirmed_404_skips_to_the_next_telegram_item(self):
        now = dt.datetime(2026, 1, 1, 1, tzinfo=dt.timezone.utc)
        candidates = telegram_post.candidates(
            [
                {
                    "lang": "zh-Hant",
                    "app": str(index),
                    "text": f"post {index}",
                    "url": f"https://example.com/{index}",
                }
                for index in range(8)
            ],
            now,
        )
        with mock.patch.object(
            telegram_post, "validate_url", side_effect=(False, True)
        ) as validator:
            selected = telegram_post.pick_postable(candidates, now)
        self.assertEqual(
            common.item_key(telegram_post.candidates(candidates, now)[1]),
            common.item_key(selected),
        )
        self.assertEqual(2, validator.call_count)

    def test_url_validator_classifies_404_without_retry(self):
        opener = mock.Mock(side_effect=http_error(404))
        sleeper = mock.Mock()
        self.assertFalse(
            common.validate_url(
                "https://example.com/missing",
                opener=opener,
                sleeper=sleeper,
            )
        )
        self.assertEqual(1, opener.call_count)
        sleeper.assert_not_called()

    def test_threads_skips_overlong_copy_without_truncating(self):
        long_item = {
            "lang": "en",
            "app": "long",
            "text": "x" * 500,
            "url": "https://example.com/long",
        }
        short_item = {
            "lang": "en",
            "app": "short",
            "text": "Complete, polished copy.",
            "url": "https://example.com/short",
        }
        with (
            mock.patch.object(
                threads_post, "candidates", return_value=[long_item, short_item]
            ),
            mock.patch.object(threads_post, "validate_url", return_value=True),
        ):
            selected, text = threads_post.pick_postable([long_item, short_item])
        self.assertIs(selected, short_item)
        self.assertIn(short_item["text"], text)
        self.assertLessEqual(len(text), threads_post.MAX_POST_CHARS)


class RetryTests(unittest.TestCase):
    def test_transient_api_error_retries_at_most_three_times(self):
        opener = mock.Mock(
            side_effect=(
                urllib.error.URLError("temporary"),
                http_error(599, b"busy"),
                FakeResponse(b'{"ok": true}'),
            )
        )
        sleeper = mock.Mock()
        result = common.request_json(
            urllib.request.Request("https://example.com/api"),
            label="test API",
            timeout=1,
            opener=opener,
            sleeper=sleeper,
        )
        self.assertEqual({"ok": True}, result)
        self.assertEqual(3, opener.call_count)
        self.assertEqual([mock.call(1), mock.call(2)], sleeper.call_args_list)

    def test_transient_url_failure_is_not_treated_as_a_dead_link(self):
        opener = mock.Mock(side_effect=urllib.error.URLError("offline"))
        with self.assertRaisesRegex(common.RequestError, "after 3 attempts"):
            common.validate_url(
                "https://example.com/app",
                opener=opener,
                sleeper=mock.Mock(),
            )
        self.assertEqual(3, opener.call_count)

    def test_threads_platform_transient_marker_is_recognized(self):
        self.assertTrue(
            threads_post._threads_transient(
                400, '{"error":{"is_transient":true}}'
            )
        )


class DevToGateTests(unittest.TestCase):
    POOL = (
        {"title": "First", "body": "one"},
        {"title": "Second", "body": "two"},
    )

    def test_72_hour_gate_across_a_month_boundary(self):
        published = (
            {
                "title": "First",
                "published_at": "2026-01-30T10:00:00Z",
            },
        )
        before = dt.datetime(2026, 2, 2, 9, 59, 59, tzinfo=dt.timezone.utc)
        boundary = dt.datetime(2026, 2, 2, 10, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(devto_post.publication_due(self.POOL, published, before))
        self.assertTrue(devto_post.publication_due(self.POOL, published, boundary))
        self.assertEqual(
            "Second",
            devto_post.next_unpublished(self.POOL, published)["title"],
        )

    def test_unrelated_recent_article_does_not_delay_pool(self):
        published = (
            {
                "title": "First",
                "published_at": "2026-02-01T00:00:00Z",
            },
            {
                "title": "Unrelated",
                "published_at": "2026-02-04T07:00:00Z",
            },
        )
        now = dt.datetime(2026, 2, 4, 8, 0, tzinfo=dt.timezone.utc)
        self.assertTrue(devto_post.publication_due(self.POOL, published, now))

    def test_dead_article_url_is_skipped_until_it_becomes_live(self):
        pool = (
            {
                "title": "Unavailable",
                "body": "Download https://example.com/missing",
            },
            {
                "title": "Ready",
                "body": "Read https://example.com/live",
            },
        )
        with mock.patch.object(
            devto_post, "validate_url", side_effect=(False, True)
        ):
            selected = devto_post.next_publishable(pool, ())
        self.assertEqual("Ready", selected["title"])

    def test_profile_read_403_is_an_explicit_failure(self):
        error = common.HTTPStatusError("Dev.to profile read", 403)
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "test-key"}),
            mock.patch.object(devto_post, "me", side_effect=error),
        ):
            self.assertEqual(1, devto_post.main())

    def test_main_calculates_latest_pool_publication_once(self):
        latest = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        with (
            mock.patch.dict(os.environ, {"DEVTO_API_KEY": "test-key"}),
            mock.patch.object(
                devto_post, "me", return_value={"username": "tester"}
            ),
            mock.patch.object(devto_post, "published_articles", return_value=[]),
            mock.patch.object(
                devto_post, "next_unpublished", return_value={"title": "Ready"}
            ),
            mock.patch.object(
                devto_post,
                "latest_pool_publication",
                return_value=latest,
            ) as latest_publication,
        ):
            self.assertEqual(0, devto_post.main())
        latest_publication.assert_called_once()


if __name__ == "__main__":
    unittest.main()
