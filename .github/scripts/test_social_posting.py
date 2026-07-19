#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the social posting automations."""

import base64
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
import portfolio_daily
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


def linkset_payload(*apps):
    root = {
        "anchor": f"{portfolio_daily.SITE_URL}/index.html",
        "item": [],
    }
    entries = [root]
    for slug, name, app_id in apps:
        guide_url = f"{portfolio_daily.SITE_URL}/guides/{slug}.html"
        root["item"].append(
            {
                "href": guide_url,
                "title*": [{"value": name, "language": "en"}],
            }
        )
        entries.append(
            {
                "anchor": guide_url,
                "related": [
                    {
                        "href": (
                            f"https://apps.apple.com/app/id{app_id}"
                            "?ct=iag_linkset"
                        )
                    }
                ],
            }
        )
    return {"linkset": entries}


class RotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(
            os.path.join(HERE, "telegram_posts.json"), encoding="utf-8"
        ) as pool_file:
            json.load(pool_file)
        cls.pool = telegram_post.load_pool()

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
            (threads_post.pick, 7, threads_post.TZ_LANGS["eu_me2"]),
            (threads_post.pick, 14, threads_post.TZ_LANGS["west"]),
            (threads_post.pick, 19, threads_post.TZ_LANGS["americas"]),
        )
        expected_ids = {common.app_key(item) for item in self.pool}
        for picker, hour, languages in routes:
            with self.subTest(hour=hour, expected_size=len(expected_ids)):
                picks = [
                    picker(self.pool, self._at(day, hour))
                    for day in range(len(expected_ids))
                ]
                self.assertEqual(
                    expected_ids, {common.app_key(item) for item in picks}
                )
                for item in picks:
                    has_localized_copy = any(
                        common.app_key(candidate) == common.app_key(item)
                        and candidate.get("lang") in languages
                        for candidate in self.pool
                    )
                    if has_localized_copy:
                        self.assertIn(item["lang"], languages)

    def test_all_channels_choose_different_apps_on_the_same_day(self):
        for day in range(1000):
            picks = (
                telegram_post.pick(self.pool, self._at(day, 1)),
                threads_post.pick(self.pool, self._at(day, 3)),
                threads_post.pick(self.pool, self._at(day, 7)),
                telegram_post.pick(self.pool, self._at(day, 9)),
                threads_post.pick(self.pool, self._at(day, 14)),
                telegram_post.pick(self.pool, self._at(day, 15)),
                threads_post.pick(self.pool, self._at(day, 19)),
            )
            self.assertEqual(7, len({common.app_key(item) for item in picks}))

    def test_combined_channels_cover_every_app_within_four_days(self):
        expected = {common.app_key(item) for item in self.pool}
        observed = set()
        for day in range(4):
            observed.update(
                common.app_key(item)
                for item in (
                    telegram_post.pick(self.pool, self._at(day, 1)),
                    threads_post.pick(self.pool, self._at(day, 3)),
                    threads_post.pick(self.pool, self._at(day, 7)),
                    telegram_post.pick(self.pool, self._at(day, 9)),
                    threads_post.pick(self.pool, self._at(day, 14)),
                    telegram_post.pick(self.pool, self._at(day, 15)),
                    threads_post.pick(self.pool, self._at(day, 19)),
                )
            )
        self.assertEqual(expected, observed)

    def test_all_50_locales_are_published_within_13_days(self):
        routes = (
            (telegram_post.pick, 1),
            (threads_post.pick, 3),
            (threads_post.pick, 7),
            (telegram_post.pick, 9),
            (threads_post.pick, 14),
            (telegram_post.pick, 15),
            (threads_post.pick, 19),
        )
        launch = dt.datetime.combine(
            common.FULL_LOCALE_SOCIAL_LAUNCH_DATE,
            dt.time(),
            tzinfo=dt.timezone.utc,
        )
        selected = []
        for day in range(common.FULL_LOCALE_SOCIAL_LAUNCH_DAYS):
            selected.extend(
                picker(
                    self.pool,
                    (launch + dt.timedelta(days=day)).replace(hour=hour),
                )
                for picker, hour in routes
            )
        self.assertEqual(
            set(common.OFFICIAL_SOCIAL_LOCALES),
            {item["lang"] for item in selected},
        )
        self.assertTrue(
            all(
                item.get("source") == "publisher_intent_catalog"
                for item in selected
            )
        )

    def test_every_app_locale_pair_rotates_within_366_days_after_launch(self):
        routes = (
            (telegram_post.pick, 1),
            (threads_post.pick, 3),
            (threads_post.pick, 7),
            (telegram_post.pick, 9),
            (threads_post.pick, 14),
            (telegram_post.pick, 15),
            (threads_post.pick, 19),
        )
        launch = dt.datetime.combine(
            common.FULL_LOCALE_SOCIAL_LAUNCH_DATE,
            dt.time(),
            tzinfo=dt.timezone.utc,
        )
        observed = set()
        for day in range(366):
            for picker, hour in routes:
                item = picker(
                    self.pool,
                    (launch + dt.timedelta(days=day)).replace(hour=hour),
                )
                if item.get("source") == "publisher_intent_catalog":
                    observed.add((str(item["app"]), item["lang"]))
        expected = {
            (common.app_key(item), item["lang"])
            for item in self.pool
            if item.get("source") == "publisher_intent_catalog"
        }
        self.assertEqual(expected, observed)

    def test_private_asc_signal_reorders_only_post_launch_locale_cycle(self):
        app_id = "7000000000"
        pool = [
            {
                "lang": locale,
                "app": app_id,
                "app_key": "alpha",
                "text": locale,
                "url": f"https://apps.apple.com/app/id{app_id}",
            }
            for locale in common.ASIA_LOCALES
        ]
        launch_day = (
            common.FULL_LOCALE_SOCIAL_LAUNCH_DATE - common.BASE_DATE
        ).days
        with mock.patch.object(
            common,
            "ASC_MARKET_LOCALES",
            {"alpha": ("ko", "ja")},
        ):
            launch_signal = common._copy_candidates(
                pool,
                "telegram:asia",
                launch_day,
                app_index=0,
                app_count=28,
            )[0]["lang"]
            post_launch_signal = [
                (
                    day,
                    common._copy_candidates(
                        pool,
                        "telegram:asia",
                        day,
                        app_index=0,
                        app_count=28,
                    )[0]["lang"],
                )
                for day in range(launch_day + 13, launch_day + 200)
            ]
        with mock.patch.object(common, "ASC_MARKET_LOCALES", {}):
            launch_default = common._copy_candidates(
                pool,
                "telegram:asia",
                launch_day,
                app_index=0,
                app_count=28,
            )[0]["lang"]
            changed = next(
                (
                    day,
                    locale,
                    common._copy_candidates(
                        pool,
                        "telegram:asia",
                        day,
                        app_index=0,
                        app_count=28,
                    )[0]["lang"],
                )
                for day, locale in post_launch_signal
                if locale == "ko"
                and common._copy_candidates(
                    pool,
                    "telegram:asia",
                    day,
                    app_index=0,
                    app_count=28,
                )[0]["lang"]
                != locale
            )
        self.assertEqual(launch_default, launch_signal)
        self.assertEqual("ko", changed[1])
        self.assertNotEqual(changed[1], changed[2])

    def test_uneven_copy_counts_cannot_bias_app_rotation(self):
        pool = []
        for app_index in range(7):
            app_id = str(7_000_000_000 + app_index)
            for copy_index in range(30 if app_index == 0 else 1):
                pool.append(
                    {
                        "lang": "en",
                        "app": app_id,
                        "text": f"app {app_index} copy {copy_index}",
                        "url": f"https://apps.apple.com/app/id{app_id}",
                    }
                )
        expected = {str(7_000_000_000 + index) for index in range(7)}
        for channel in common.CHANNEL_ORDER:
            picks = {
                common.app_key(
                    common.channel_candidates(
                        pool, channel, self._at(day, 15)
                    )[0]
                )
                for day in range(7)
            }
            self.assertEqual(expected, picks)


class FooterAndSelectionTests(unittest.TestCase):
    def test_private_asc_signal_is_validated_without_exposing_metrics(self):
        raw = json.dumps(
            {
                "version": 1,
                "generated_at": "2026-07-19T11:26:27+00:00",
                "valid_until": "2026-07-22",
                "app_count": 2,
                "apps": {
                    "alpha": {
                        "action": "SCALE",
                        "locales": ["zh-Hant", "en-US"],
                    },
                    "beta": {
                        "action": "DOWNLOAD_CONVERT",
                        "locales": [],
                    },
                },
            }
        )
        locales, actions = common._load_asc_growth_signals(
            raw,
            today=dt.date(2026, 7, 20),
        )
        self.assertEqual(
            {"alpha": ("zh-Hant", "en-US"), "beta": ()},
            locales,
        )
        self.assertEqual(
            {"alpha": "SCALE", "beta": "DOWNLOAD_CONVERT"},
            actions,
        )
        with mock.patch.dict(
            os.environ,
            {
                "ASC_GROWTH_SIGNALS_B64": base64.b64encode(
                    raw.encode("utf-8")
                ).decode("ascii")
            },
            clear=False,
        ):
            self.assertEqual(
                (locales, actions),
                common._load_asc_growth_signals(
                    today=dt.date(2026, 7, 20)
                ),
            )

    def test_expired_private_asc_signal_keeps_deterministic_rotation(self):
        warning = io.StringIO()
        raw = json.dumps(
            {
                "version": 1,
                "generated_at": "2026-07-15T00:00:00+00:00",
                "valid_until": "2026-07-18",
                "app_count": 0,
                "apps": {},
            }
        )
        with mock.patch.object(common.sys, "stderr", warning):
            locales, actions = common._load_asc_growth_signals(
                raw,
                today=dt.date(2026, 7, 20),
            )
        self.assertEqual(({}, {}), (locales, actions))
        self.assertIn("signals expired", warning.getvalue())

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
                    "app": "7000000000",
                    "url": "https://apps.apple.com/app/id7000000000",
                }
                footer = common.footer_for(lang)
                self.assertTrue(telegram_post.compose_text(item).endswith(footer))
                self.assertTrue(threads_post.compose_text(item).endswith(footer))
                if not lang.startswith("zh-"):
                    self.assertNotIn("獨立開發者", footer)
                    self.assertNotIn("買斷", footer)
                    self.assertNotIn("訂閱", footer)

    def test_official_locale_partition_is_complete_and_disjoint(self):
        locales = (
            *common.ASIA_LOCALES,
            *common.EUROPE_MIDDLE_EAST_LOCALES,
            *common.AMERICAS_LOCALES,
        )
        self.assertEqual(50, len(locales))
        self.assertEqual(50, len(set(locales)))
        self.assertEqual(
            set(common.OFFICIAL_SOCIAL_LOCALES),
            set(locales),
        )

    def test_single_post_selection_does_not_probe_every_app_store_url(self):
        now = dt.datetime(2026, 1, 1, 1, tzinfo=dt.timezone.utc)
        pool = [
            {
                "lang": "zh-Hant",
                "app": str(7_000_000_000 + index),
                "text": f"post {index}",
                "url": f"https://apps.apple.com/app/id{7_000_000_000 + index}",
            }
            for index in range(8)
        ]
        expected = telegram_post.candidates(pool, now)[0]
        with mock.patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("selection must not make HTTP requests"),
        ) as opener:
            selected = telegram_post.pick_postable(pool, now)
        self.assertEqual(
            common.item_key(expected),
            common.item_key(selected),
        )
        opener.assert_not_called()

    def test_dead_apps_preserve_unique_cross_channel_assignments(self):
        pool = [
            {
                "lang": "en",
                "app": str(7_000_000_000 + index),
                "text": f"post {index}",
                "url": f"https://apps.apple.com/app/id{7_000_000_000 + index}",
            }
            for index in range(9)
        ]
        live_pool = common.filter_reachable_pool(
            pool,
            validator=lambda url: not (
                url.endswith("7000000000") or url.endswith("7000000001")
            ),
        )
        picks = [
            common.channel_candidates(
                live_pool, channel, dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
            )[0]
            for channel in common.CHANNEL_ORDER
        ]
        self.assertEqual(7, len({common.app_key(item) for item in picks}))

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
            "app": "7000000000",
            "text": "x" * 500,
            "url": "https://apps.apple.com/app/id7000000000",
        }
        short_item = {
            "lang": "en",
            "app": "7000000001",
            "text": "Complete, polished copy.",
            "url": "https://apps.apple.com/app/id7000000001",
        }
        with (
            mock.patch.object(
                threads_post, "candidates", return_value=[long_item, short_item]
            ),
            mock.patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError(
                    "selection must not make HTTP requests"
                ),
            ) as opener,
        ):
            selected, text = threads_post.pick_postable([long_item, short_item])
        self.assertIs(selected, short_item)
        self.assertIn(short_item["text"], text)
        self.assertLessEqual(len(text), threads_post.MAX_POST_CHARS)
        opener.assert_not_called()


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

    def test_threads_image_post_uses_public_jpeg(self):
        image_url = (
            "https://alice51849.github.io/ios-app-guide/"
            "social/img/aim990-share.jpg"
        )
        with mock.patch.object(
            threads_post,
            "_post",
            side_effect=({"id": "container"}, {"id": "post"}),
        ) as post:
            result = threads_post.publish_post(
                "token",
                "user",
                "Buyer-intent copy",
                image_url=image_url,
                sleeper=mock.Mock(),
            )
        self.assertEqual("post", result)
        payload = post.call_args_list[0].args[1]
        self.assertEqual("IMAGE", payload["media_type"])
        self.assertEqual(image_url, payload["image_url"])
        self.assertEqual("Buyer-intent copy", payload["text"])

    def test_telegram_photo_uses_public_jpeg_and_caption(self):
        image_url = (
            "https://alice51849.github.io/ios-app-guide/"
            "social/img/aim990-share.jpg"
        )
        with mock.patch.object(
            telegram_post,
            "request_json",
            return_value={"ok": True, "result": {"message_id": 1}},
        ) as request:
            telegram_post._send_photo(
                "token",
                "chat",
                "Buyer-intent copy",
                image_url,
            )
        sent = urllib.parse.parse_qs(
            request.call_args.args[0].data.decode("utf-8")
        )
        self.assertIn("/sendPhoto", request.call_args.args[0].full_url)
        self.assertEqual([image_url], sent["photo"])
        self.assertEqual(["Buyer-intent copy"], sent["caption"])


class DailyPortfolioCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = portfolio_daily.load_public_apps()

    def test_current_live_registry_is_covered_without_a_static_post_pool(self):
        selected_ids = {app.app_id for app in self.apps}
        self.assertEqual(
            selected_ids,
            {app.app_id for app in portfolio_daily.load_public_apps()},
        )
        pool = telegram_post.load_pool()
        self.assertEqual(
            selected_ids,
            {str(item["app"]) for item in pool},
        )
        for item in pool:
            expected = f"https://apps.apple.com/app/id{item['app']}"
            self.assertEqual(expected, item["url"])
        for app_id in selected_ids:
            languages = {
                item["lang"]
                for item in pool
                if str(item["app"]) == app_id
            }
            for channel, spec in common.CHANNEL_SPECS.items():
                with self.subTest(app_id=app_id, channel=channel):
                    self.assertTrue(languages.intersection(spec["langs"]))

    def test_intent_pool_covers_every_live_app_in_all_50_locales(self):
        pool = [
            item
            for item in telegram_post.load_pool()
            if item.get("source") == "publisher_intent_catalog"
        ]
        selected_ids = {app.app_id for app in self.apps}
        self.assertEqual(len(selected_ids) * 50, len(pool))
        self.assertEqual(
            {
                (app_id, locale)
                for app_id in selected_ids
                for locale in common.OFFICIAL_SOCIAL_LOCALES
            },
            {(str(item["app"]), item["lang"]) for item in pool},
        )
        for item in pool:
            self.assertLessEqual(
                len(threads_post.compose_text(item)),
                threads_post.MAX_POST_CHARS,
            )
            self.assertEqual(
                item["image_url"],
                common.item_image_url(item),
            )
            self.assertTrue(item["footer"].startswith("— Lumi Studio · "))

    def test_linkset_discovers_unknown_new_live_apps(self):
        selected = portfolio_daily.parse_public_apps(
            linkset_payload(
                ("known", "Current App", "7000000001"),
                ("brand-new", "Brand New App", "7000000002"),
            ),
            apps={
                "known": {
                    "name": "Registry Name",
                    "category": "productivity",
                }
            },
            appstore={"known": "7000000001"},
        )
        by_id = {app.app_id: app for app in selected}
        self.assertEqual({"7000000001", "7000000002"}, set(by_id))
        self.assertEqual("Current App", by_id["7000000001"].name)
        self.assertEqual("productivity", by_id["7000000001"].category)
        self.assertEqual("Brand New App", by_id["7000000002"].name)
        self.assertEqual("other", by_id["7000000002"].category)
        self.assertEqual("brand-new", by_id["7000000002"].key)

    def test_live_app_without_a_unique_context_fails_loudly(self):
        payload = linkset_payload(("known", "Known", "7000000001"))
        payload["linkset"] = payload["linkset"][:1]
        with self.assertRaisesRegex(
            portfolio_daily.CoverageError, "exactly one linkset context"
        ):
            portfolio_daily.parse_public_apps(
                payload,
                apps={},
                appstore={},
            )

    def test_confirmed_dead_daily_link_is_excluded(self):
        validator = mock.Mock(side_effect=(True, False))
        reachable = portfolio_daily.filter_reachable_apps(
            self.apps[:2], validator=validator, max_workers=1
        )
        self.assertEqual([self.apps[0]], reachable)
        self.assertEqual(2, validator.call_count)

    def test_transient_daily_link_failure_blocks_publication(self):
        validator = mock.Mock(side_effect=common.RequestError("offline"))
        with self.assertRaisesRegex(common.RequestError, "offline"):
            portfolio_daily.filter_reachable_apps(
                self.apps[:1], validator=validator, max_workers=1
            )

    def test_each_platform_covers_every_live_app_exactly_once(self):
        for platform, builder, limit in (
            (
                "telegram",
                portfolio_daily.telegram_messages,
                portfolio_daily.TELEGRAM_LIMIT,
            ),
            (
                "threads",
                portfolio_daily.threads_messages,
                portfolio_daily.THREADS_LIMIT,
            ),
        ):
            with self.subTest(platform=platform):
                messages = builder(self.apps)
                portfolio_daily.validate_coverage(platform, self.apps, messages)
                combined = "\n".join(message.text for message in messages)
                for app in self.apps:
                    self.assertIn(app.name, combined)
                    self.assertEqual(
                        1, combined.count(app.appstore_url())
                    )
                self.assertNotIn("?ct=", combined)
                self.assertTrue(all(len(message.text) <= limit for message in messages))
                if platform == "threads":
                    self.assertTrue(
                        all(
                            len(message.app_ids)
                            <= portfolio_daily.THREADS_LINK_LIMIT
                            for message in messages
                        )
                    )
                    self.assertTrue(
                        all(
                            message.text.count("https://") <= 5
                            for message in messages
                        )
                    )
                    self.assertNotIn(
                        portfolio_daily.DEVELOPER_URL, combined
                    )

    def test_large_portfolio_splits_without_losing_coverage(self):
        apps = [
            portfolio_daily.PublicApp(
                key=f"app-{index}",
                app_id=str(index),
                name=f"Portfolio Utility {index:03d}",
                category="productivity",
            )
            for index in range(120)
        ]
        for platform, builder in (
            ("telegram", portfolio_daily.telegram_messages),
            ("threads", portfolio_daily.threads_messages),
        ):
            messages = builder(apps)
            self.assertGreater(len(messages), 1)
            portfolio_daily.validate_coverage(platform, apps, messages)

    def test_same_day_platform_success_prevents_duplicate_digest(self):
        now = dt.datetime(
            2026, 7, 13, 13, 0, tzinfo=dt.timezone.utc
        )
        calls = []

        def fetcher(url, token):
            calls.append((url, token))
            if "/workflows/" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 100,
                            "created_at": "2026-07-13T04:30:00Z",
                        },
                        {
                            "id": 200,
                            "created_at": "2026-07-13T12:00:00Z",
                        },
                    ]
                }
            if "/runs/100/jobs" in url:
                return {
                    "jobs": [
                        {
                            "name": "telegram",
                            "conclusion": "success",
                            "completed_at": "2026-07-13T07:46:14Z",
                        },
                        {
                            "name": "threads",
                            "conclusion": "failure",
                            "completed_at": "2026-07-13T07:46:48Z",
                        },
                    ]
                }
            raise AssertionError(f"unexpected URL: {url}")

        self.assertTrue(
            portfolio_daily.already_published_today(
                "telegram",
                now=now,
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                token="test-token",
                fetcher=fetcher,
            )
        )
        calls.clear()
        self.assertFalse(
            portfolio_daily.already_published_today(
                "threads",
                now=now,
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                token="test-token",
                fetcher=fetcher,
            )
        )
        self.assertTrue(
            all(token == "test-token" for _, token in calls)
        )
        self.assertTrue(
            any("jobs?filter=all&per_page=100" in url for url, _ in calls)
        )

    def test_previous_day_success_does_not_skip_today(self):
        def fetcher(url, _token):
            if "/workflows/" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 100,
                            "created_at": "2026-07-12T04:30:00Z",
                        }
                    ]
                }
            return {
                "jobs": [
                    {
                        "name": "threads",
                        "conclusion": "success",
                        "completed_at": "2026-07-12T04:31:00Z",
                    }
                ]
            }

        self.assertFalse(
            portfolio_daily.already_published_today(
                "threads",
                now=dt.datetime(
                    2026, 7, 13, 0, 1, tzinfo=dt.timezone.utc
                ),
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                fetcher=fetcher,
            )
        )

    def test_ambiguous_success_timestamp_blocks_duplicate(self):
        def fetcher(url, _token):
            if "/workflows/" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 100,
                            "created_at": "2026-07-13T04:30:00Z",
                        }
                    ]
                }
            return {
                "jobs": [
                    {
                        "name": "threads",
                        "conclusion": "success",
                        "completed_at": None,
                    }
                ]
            }

        with self.assertRaisesRegex(
            portfolio_daily.CoverageError, "valid completed_at"
        ):
            portfolio_daily.already_published_today(
                "threads",
                now=dt.datetime(
                    2026, 7, 13, 13, 0, tzinfo=dt.timezone.utc
                ),
                repository="alice51849/ios-app-guide",
                current_run_id="200",
                fetcher=fetcher,
            )

    def test_daily_workflow_runs_both_platforms(self):
        workflow = os.path.join(
            portfolio_daily.REPO_ROOT,
            ".github",
            "workflows",
            "portfolio-daily.yml",
        )
        with open(workflow, encoding="utf-8") as workflow_file:
            text = workflow_file.read()
        self.assertIn('cron: "30 4 * * *"', text)
        self.assertIn('workflows: ["Daily GEO content"]', text)
        self.assertIn(
            "github.event.workflow_run.conclusion == 'success'", text
        )
        self.assertIn("actions: read", text)
        self.assertEqual(2, text.count("GITHUB_TOKEN:"))
        self.assertIn("--platform telegram", text)
        self.assertIn("--platform threads", text)

    def test_geo_workflow_generates_new_app_surfaces_before_linkset(self):
        workflow = os.path.join(
            portfolio_daily.REPO_ROOT,
            ".github",
            "workflows",
            "geo-daily.yml",
        )
        with open(workflow, encoding="utf-8") as workflow_file:
            text = workflow_file.read()
        commands = (
            "python3 ensure_live_guides.py",
            "python3 gen_webstories.py",
            "python3 gen_image_sitemap.py",
            "python3 gen_linkset.py",
        )
        positions = [text.index(command) for command in commands]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            positions[-1],
            text.index("python3 -m unittest discover"),
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
